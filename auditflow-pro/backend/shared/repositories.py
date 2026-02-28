import os
import logging
import boto3
from botocore.exceptions import ClientError
from typing import List, Optional, Dict, Any
from decimal import Decimal
import time
import models

# Configure logging for audit trails and errors
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Retry configuration
MAX_RETRIES = 3
INITIAL_BACKOFF = 0.1  # 100ms
MAX_BACKOFF = 2.0  # 2 seconds

class DocumentRepository:
    def __init__(self, dynamodb_resource=None):
        self.dynamodb = dynamodb_resource or boto3.resource('dynamodb')
        self.table_name = os.environ.get('DOCUMENTS_TABLE', 'AuditFlow-Documents')
        self.table = self.dynamodb.Table(self.table_name)

    def _retry_with_backoff(self, operation, *args, **kwargs):
        """Execute operation with exponential backoff retry logic."""
        backoff = INITIAL_BACKOFF
        for attempt in range(MAX_RETRIES):
            try:
                return operation(*args, **kwargs)
            except ClientError as e:
                error_code = e.response['Error']['Code']
                # Retry on throttling and transient errors
                if error_code in ['ProvisionedThroughputExceededException', 'ThrottlingException', 
                                 'RequestLimitExceeded', 'InternalServerError', 'ServiceUnavailable']:
                    if attempt < MAX_RETRIES - 1:
                        logger.warning(f"Retrying after {error_code}, attempt {attempt + 1}/{MAX_RETRIES}")
                        time.sleep(backoff)
                        backoff = min(backoff * 2, MAX_BACKOFF)
                        continue
                raise

    def save_document(self, document: models.DocumentMetadata) -> bool:
        """Saves a new document record or overwrites an existing one."""
        try:
            self._retry_with_backoff(self.table.put_item, Item=document.to_dict())
            logger.info(f"Successfully saved document {document.document_id}")
            return True
        except ClientError as e:
            logger.error(f"Failed to save document {document.document_id}: {e.response['Error']['Message']}")
            raise

    def get_document(self, document_id: str) -> Optional[models.DocumentMetadata]:
        """Retrieves a document by its ID."""
        try:
            response = self._retry_with_backoff(self.table.get_item, Key={'document_id': document_id})
            item = response.get('Item')
            if item:
                return models.DocumentMetadata.from_dict(item)
            return None
        except ClientError as e:
            logger.error(f"Error retrieving document {document_id}: {e.response['Error']['Message']}")
            raise

    def update_document_status(self, document_id: str, new_status: str) -> bool:
        """Atomically updates the processing status of a document."""
        try:
            self._retry_with_backoff(
                self.table.update_item,
                Key={'document_id': document_id},
                UpdateExpression="SET processing_status = :s",
                ConditionExpression="attribute_exists(document_id)",
                ExpressionAttributeValues={':s': new_status}
            )
            logger.info(f"Successfully updated status for {document_id} to {new_status}")
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                logger.warning(f"Document {document_id} does not exist for status update.")
                return False
            logger.error(f"Failed to update status for {document_id}: {e.response['Error']['Message']}")
            raise

    def update_extracted_data(self, document_id: str, extracted_data: Dict[str, Any], 
                             extraction_timestamp: str, low_confidence_fields: List[str]) -> bool:
        """Atomically updates extracted data for a document."""
        try:
            self._retry_with_backoff(
                self.table.update_item,
                Key={'document_id': document_id},
                UpdateExpression="SET extracted_data = :data, extraction_timestamp = :ts, low_confidence_fields = :lcf",
                ConditionExpression="attribute_exists(document_id)",
                ExpressionAttributeValues={
                    ':data': extracted_data,
                    ':ts': extraction_timestamp,
                    ':lcf': low_confidence_fields
                }
            )
            logger.info(f"Successfully updated extracted data for {document_id}")
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                logger.warning(f"Document {document_id} does not exist for data update.")
                return False
            logger.error(f"Failed to update extracted data for {document_id}: {e.response['Error']['Message']}")
            raise

    def update_classification(self, document_id: str, document_type: str, 
                            confidence: float, requires_manual_review: bool) -> bool:
        """Atomically updates document classification."""
        try:
            self._retry_with_backoff(
                self.table.update_item,
                Key={'document_id': document_id},
                UpdateExpression="SET document_type = :dt, classification_confidence = :conf, requires_manual_review = :rmr",
                ConditionExpression="attribute_exists(document_id)",
                ExpressionAttributeValues={
                    ':dt': document_type,
                    ':conf': Decimal(str(confidence)),
                    ':rmr': requires_manual_review
                }
            )
            logger.info(f"Successfully updated classification for {document_id} to {document_type}")
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                logger.warning(f"Document {document_id} does not exist for classification update.")
                return False
            logger.error(f"Failed to update classification for {document_id}: {e.response['Error']['Message']}")
            raise

    def get_documents_by_loan(self, loan_application_id: str) -> List[models.DocumentMetadata]:
        """Queries all documents belonging to a specific loan application."""
        try:
            response = self._retry_with_backoff(
                self.table.query,
                IndexName='loan_application_id-upload_timestamp-index',
                KeyConditionExpression=boto3.dynamodb.conditions.Key('loan_application_id').eq(loan_application_id)
            )
            return [models.DocumentMetadata.from_dict(item) for item in response.get('Items', [])]
        except ClientError as e:
            logger.error(f"Error querying documents for loan {loan_application_id}: {e.response['Error']['Message']}")
            raise

    def get_documents_by_status(self, status: str, limit: Optional[int] = None) -> List[models.DocumentMetadata]:
        """Queries documents by processing status."""
        try:
            query_params = {
                'IndexName': 'processing_status-upload_timestamp-index',
                'KeyConditionExpression': boto3.dynamodb.conditions.Key('processing_status').eq(status)
            }
            if limit:
                query_params['Limit'] = limit
            
            response = self._retry_with_backoff(self.table.query, **query_params)
            return [models.DocumentMetadata.from_dict(item) for item in response.get('Items', [])]
        except ClientError as e:
            logger.error(f"Error querying documents by status {status}: {e.response['Error']['Message']}")
            raise

    def delete_document(self, document_id: str) -> bool:
        """Deletes a document record."""
        try:
            self._retry_with_backoff(
                self.table.delete_item,
                Key={'document_id': document_id},
                ConditionExpression="attribute_exists(document_id)"
            )
            logger.info(f"Successfully deleted document {document_id}")
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                logger.warning(f"Document {document_id} does not exist for deletion.")
                return False
            logger.error(f"Failed to delete document {document_id}: {e.response['Error']['Message']}")
            raise

class AuditRecordRepository:
    def __init__(self, dynamodb_resource=None):
        self.dynamodb = dynamodb_resource or boto3.resource('dynamodb')
        self.table_name = os.environ.get('AUDIT_RECORDS_TABLE', 'AuditFlow-AuditRecords')
        self.table = self.dynamodb.Table(self.table_name)

    def _retry_with_backoff(self, operation, *args, **kwargs):
        """Execute operation with exponential backoff retry logic."""
        backoff = INITIAL_BACKOFF
        for attempt in range(MAX_RETRIES):
            try:
                return operation(*args, **kwargs)
            except ClientError as e:
                error_code = e.response['Error']['Code']
                # Retry on throttling and transient errors
                if error_code in ['ProvisionedThroughputExceededException', 'ThrottlingException', 
                                 'RequestLimitExceeded', 'InternalServerError', 'ServiceUnavailable']:
                    if attempt < MAX_RETRIES - 1:
                        logger.warning(f"Retrying after {error_code}, attempt {attempt + 1}/{MAX_RETRIES}")
                        time.sleep(backoff)
                        backoff = min(backoff * 2, MAX_BACKOFF)
                        continue
                raise

    def save_audit_record(self, record: models.AuditRecord) -> bool:
        """Saves the completed audit record."""
        try:
            self._retry_with_backoff(self.table.put_item, Item=record.to_dict())
            logger.info(f"Successfully saved audit record {record.audit_record_id}")
            return True
        except ClientError as e:
            logger.error(f"Failed to save audit record {record.audit_record_id}: {e.response['Error']['Message']}")
            raise

    def get_audit_record(self, audit_record_id: str) -> Optional[models.AuditRecord]:
        """Retrieves a specific audit record."""
        try:
            response = self._retry_with_backoff(self.table.get_item, Key={'audit_record_id': audit_record_id})
            item = response.get('Item')
            if item:
                return models.AuditRecord.from_dict(item)
            return None
        except ClientError as e:
            logger.error(f"Error retrieving audit record {audit_record_id}: {e.response['Error']['Message']}")
            raise

    def update_audit_status(self, audit_record_id: str, new_status: str) -> bool:
        """Atomically updates the status of an audit record."""
        try:
            self._retry_with_backoff(
                self.table.update_item,
                Key={'audit_record_id': audit_record_id},
                UpdateExpression="SET #status = :s",
                ConditionExpression="attribute_exists(audit_record_id)",
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues={':s': new_status}
            )
            logger.info(f"Successfully updated audit status for {audit_record_id} to {new_status}")
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                logger.warning(f"Audit record {audit_record_id} does not exist for status update.")
                return False
            logger.error(f"Failed to update audit status for {audit_record_id}: {e.response['Error']['Message']}")
            raise

    def update_review_info(self, audit_record_id: str, reviewed_by: str, 
                          review_timestamp: str, review_notes: Optional[str] = None) -> bool:
        """Atomically updates review information for an audit record."""
        try:
            update_expr = "SET reviewed_by = :rb, review_timestamp = :rt"
            expr_values = {':rb': reviewed_by, ':rt': review_timestamp}
            
            if review_notes:
                update_expr += ", review_notes = :rn"
                expr_values[':rn'] = review_notes
            
            self._retry_with_backoff(
                self.table.update_item,
                Key={'audit_record_id': audit_record_id},
                UpdateExpression=update_expr,
                ConditionExpression="attribute_exists(audit_record_id)",
                ExpressionAttributeValues=expr_values
            )
            logger.info(f"Successfully updated review info for {audit_record_id}")
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                logger.warning(f"Audit record {audit_record_id} does not exist for review update.")
                return False
            logger.error(f"Failed to update review info for {audit_record_id}: {e.response['Error']['Message']}")
            raise

    def mark_as_archived(self, audit_record_id: str, archive_timestamp: str) -> bool:
        """Atomically marks an audit record as archived."""
        try:
            self._retry_with_backoff(
                self.table.update_item,
                Key={'audit_record_id': audit_record_id},
                UpdateExpression="SET archived = :a, archive_timestamp = :at",
                ConditionExpression="attribute_exists(audit_record_id) AND archived = :false",
                ExpressionAttributeValues={
                    ':a': True,
                    ':at': archive_timestamp,
                    ':false': False
                }
            )
            logger.info(f"Successfully marked audit record {audit_record_id} as archived")
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                logger.warning(f"Audit record {audit_record_id} does not exist or already archived.")
                return False
            logger.error(f"Failed to mark audit record {audit_record_id} as archived: {e.response['Error']['Message']}")
            raise

    def get_audits_by_loan(self, loan_application_id: str) -> List[models.AuditRecord]:
        """Queries all audit records for a specific loan application."""
        try:
            response = self._retry_with_backoff(
                self.table.query,
                IndexName='loan_application_id-audit_timestamp-index',
                KeyConditionExpression=boto3.dynamodb.conditions.Key('loan_application_id').eq(loan_application_id),
                ScanIndexForward=False  # Most recent first
            )
            return [models.AuditRecord.from_dict(item) for item in response.get('Items', [])]
        except ClientError as e:
            logger.error(f"Error querying audits for loan {loan_application_id}: {e.response['Error']['Message']}")
            raise

    def get_audits_by_status(self, status: str, limit: Optional[int] = None) -> List[models.AuditRecord]:
        """Queries audit records by status."""
        try:
            query_params = {
                'IndexName': 'status-audit_timestamp-index',
                'KeyConditionExpression': boto3.dynamodb.conditions.Key('status').eq(status),
                'ScanIndexForward': False  # Most recent first
            }
            if limit:
                query_params['Limit'] = limit
            
            response = self._retry_with_backoff(self.table.query, **query_params)
            return [models.AuditRecord.from_dict(item) for item in response.get('Items', [])]
        except ClientError as e:
            logger.error(f"Error querying audits by status {status}: {e.response['Error']['Message']}")
            raise

    def get_high_risk_audits(self, min_risk_score: int = 50, limit: Optional[int] = None) -> List[models.AuditRecord]:
        """Queries completed audit records with risk score above threshold."""
        try:
            query_params = {
                'IndexName': 'risk_score-audit_timestamp-index',
                'KeyConditionExpression': boto3.dynamodb.conditions.Key('status').eq('COMPLETED') & 
                                         boto3.dynamodb.conditions.Key('risk_score').gte(min_risk_score),
                'ScanIndexForward': False  # Highest risk first
            }
            if limit:
                query_params['Limit'] = limit
            
            response = self._retry_with_backoff(self.table.query, **query_params)
            return [models.AuditRecord.from_dict(item) for item in response.get('Items', [])]
        except ClientError as e:
            logger.error(f"Error querying high-risk audits: {e.response['Error']['Message']}")
            raise

    def query_audits_by_date_range(self, status: str, start_date: str, end_date: str, 
                                   limit: Optional[int] = None) -> List[models.AuditRecord]:
        """Queries audit records by status within a date range."""
        try:
            query_params = {
                'IndexName': 'status-audit_timestamp-index',
                'KeyConditionExpression': boto3.dynamodb.conditions.Key('status').eq(status) & 
                                         boto3.dynamodb.conditions.Key('audit_timestamp').between(start_date, end_date),
                'ScanIndexForward': False  # Most recent first
            }
            if limit:
                query_params['Limit'] = limit
            
            response = self._retry_with_backoff(self.table.query, **query_params)
            return [models.AuditRecord.from_dict(item) for item in response.get('Items', [])]
        except ClientError as e:
            logger.error(f"Error querying audits by date range: {e.response['Error']['Message']}")
            raise

    def delete_audit_record(self, audit_record_id: str) -> bool:
        """Deletes an audit record."""
        try:
            self._retry_with_backoff(
                self.table.delete_item,
                Key={'audit_record_id': audit_record_id},
                ConditionExpression="attribute_exists(audit_record_id)"
            )
            logger.info(f"Successfully deleted audit record {audit_record_id}")
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                logger.warning(f"Audit record {audit_record_id} does not exist for deletion.")
                return False
            logger.error(f"Failed to delete audit record {audit_record_id}: {e.response['Error']['Message']}")
            raise

    def batch_get_audits(self, audit_record_ids: List[str]) -> List[models.AuditRecord]:
        """Retrieves multiple audit records in a single batch operation."""
        if not audit_record_ids:
            return []
        
        try:
            # DynamoDB batch_get_item has a limit of 100 items
            batch_size = 100
            all_records = []
            
            for i in range(0, len(audit_record_ids), batch_size):
                batch_ids = audit_record_ids[i:i + batch_size]
                keys = [{'audit_record_id': aid} for aid in batch_ids]
                
                response = self._retry_with_backoff(
                    self.dynamodb.batch_get_item,
                    RequestItems={
                        self.table_name: {
                            'Keys': keys
                        }
                    }
                )
                
                items = response.get('Responses', {}).get(self.table_name, [])
                all_records.extend([models.AuditRecord.from_dict(item) for item in items])
                
                # Handle unprocessed keys
                unprocessed = response.get('UnprocessedKeys', {})
                while unprocessed:
                    logger.warning(f"Retrying {len(unprocessed)} unprocessed keys")
                    time.sleep(INITIAL_BACKOFF)
                    response = self._retry_with_backoff(
                        self.dynamodb.batch_get_item,
                        RequestItems=unprocessed
                    )
                    items = response.get('Responses', {}).get(self.table_name, [])
                    all_records.extend([models.AuditRecord.from_dict(item) for item in items])
                    unprocessed = response.get('UnprocessedKeys', {})
            
            return all_records
        except ClientError as e:
            logger.error(f"Error in batch get audits: {e.response['Error']['Message']}")
            raise
