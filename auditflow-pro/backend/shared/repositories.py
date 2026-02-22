import os
import logging
import boto3
from botocore.exceptions import ClientError
from typing import List, Optional, Dict, Any
from .models import DocumentMetadata, AuditRecord

# Configure logging for audit trails and errors
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class DocumentRepository:
    def __init__(self, dynamodb_resource=None):
        self.dynamodb = dynamodb_resource or boto3.resource('dynamodb')
        self.table_name = os.environ.get('DOCUMENTS_TABLE', 'AuditFlow-Documents')
        self.table = self.dynamodb.Table(self.table_name)

    def save_document(self, document: DocumentMetadata) -> bool:
        """Saves a new document record or overwrites an existing one."""
        try:
            self.table.put_item(Item=document.to_dict())
            logger.info(f"Successfully saved document {document.document_id}")
            return True
        except ClientError as e:
            logger.error(f"Failed to save document {document.document_id}: {e.response['Error']['Message']}")
            raise

    def get_document(self, document_id: str) -> Optional[DocumentMetadata]:
        """Retrieves a document by its ID."""
        try:
            response = self.table.get_item(Key={'document_id': document_id})
            item = response.get('Item')
            if item:
                return DocumentMetadata(**item)
            return None
        except ClientError as e:
            logger.error(f"Error retrieving document {document_id}: {e.response['Error']['Message']}")
            raise

    def update_document_status(self, document_id: str, new_status: str) -> bool:
        """Atomically updates the processing status of a document."""
        try:
            self.table.update_item(
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

    def get_documents_by_loan(self, loan_application_id: str) -> List[DocumentMetadata]:
        """Queries all documents belonging to a specific loan application."""
        try:
            response = self.table.query(
                IndexName='loan_application_id-upload_timestamp-index',
                KeyConditionExpression=boto3.dynamodb.conditions.Key('loan_application_id').eq(loan_application_id)
            )
            return [DocumentMetadata(**item) for item in response.get('Items', [])]
        except ClientError as e:
            logger.error(f"Error querying documents for loan {loan_application_id}: {e.response['Error']['Message']}")
            raise

class AuditRecordRepository:
    def __init__(self, dynamodb_resource=None):
        self.dynamodb = dynamodb_resource or boto3.resource('dynamodb')
        self.table_name = os.environ.get('AUDIT_RECORDS_TABLE', 'AuditFlow-AuditRecords')
        self.table = self.dynamodb.Table(self.table_name)

    def save_audit_record(self, record: AuditRecord) -> bool:
        """Saves the completed audit record."""
        try:
            self.table.put_item(Item=record.to_dict())
            logger.info(f"Successfully saved audit record {record.audit_record_id}")
            return True
        except ClientError as e:
            logger.error(f"Failed to save audit record {record.audit_record_id}: {e.response['Error']['Message']}")
            raise

    def get_audit_record(self, audit_record_id: str) -> Optional[AuditRecord]:
        """Retrieves a specific audit record."""
        try:
            response = self.table.get_item(Key={'audit_record_id': audit_record_id})
            item = response.get('Item')
            if item:
                return AuditRecord(**item)
            return None
        except ClientError as e:
            logger.error(f"Error retrieving audit record {audit_record_id}: {e.response['Error']['Message']}")
            raise
