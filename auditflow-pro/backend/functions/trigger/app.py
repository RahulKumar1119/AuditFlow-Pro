# -*- coding: utf-8 -*-
# backend/functions/trigger/app.py
# Task 13.2: S3 Event Handler Lambda Function
# Requirements: 1.4, 10.2, 10.3, 10.4

import os
import json
import urllib.parse
import logging
import boto3
from botocore.exceptions import ClientError
from datetime import datetime

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
sfn_client = boto3.client('stepfunctions', region_name=os.environ.get('AWS_REGION', 'ap-south-1'))
s3_client = boto3.client('s3', region_name=os.environ.get('AWS_REGION', 'ap-south-1'))
STATE_MACHINE_ARN = os.environ.get('STATE_MACHINE_ARN')

# Requirement 1.4 & 10.3: Reject files > 50MB
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024

# Supported file formats (Requirement 1.3)
SUPPORTED_EXTENSIONS = {'.pdf', '.jpeg', '.jpg', '.png', '.tiff', '.tif'} 

def validate_file_format(key):
    """
    Validate that the file has a supported extension.
    Requirement 1.3: Support PDF, JPEG, PNG, and TIFF file formats
    """
    file_ext = os.path.splitext(key)[1].lower()
    return file_ext in SUPPORTED_EXTENSIONS


def extract_document_metadata(s3_record, context):
    """
    Task 13.2: Extract document metadata from S3 event notification.
    Returns: dict with bucket, key, size, and other metadata
    """
    bucket = s3_record['s3']['bucket']['name']
    # Decode URL-encoded keys (e.g., spaces converted to '+')
    key = urllib.parse.unquote_plus(s3_record['s3']['object']['key'], encoding='utf-8')
    size = s3_record['s3']['object']['size']
    event_time = s3_record.get('eventTime', datetime.utcnow().isoformat() + 'Z')
    
    # Extract loan application ID from S3 key path
    # Expected format: uploads/{loan_id}/{filename}
    parts = key.split('/')
    loan_app_id = parts[1] if len(parts) > 1 else "unknown-loan"
    
    # Generate unique document ID
    document_id = f"doc-{context.aws_request_id[:8]}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    
    return {
        'bucket': bucket,
        'key': key,
        'size': size,
        'loan_app_id': loan_app_id,
        'document_id': document_id,
        'event_time': event_time
    }


def validate_file_size(size, key):
    """
    Task 13.2: Validate file size (reject files > 50MB).
    Requirement 1.4: Display file size error for files exceeding 50MB
    """
    if size > MAX_FILE_SIZE_BYTES:
        size_mb = size / (1024 * 1024)
        logger.error(
            f"Validation Failed: File {key} exceeds 50MB limit "
            f"(size: {size_mb:.2f}MB). Rejecting."
        )
        return False
    return True


def initiate_workflow(metadata):
    """
    Task 13.2: Initiate Step Functions workflow execution.
    Requirement 10.3: Lambda function initiates document processing workflow
    """
    # Construct payload for Step Functions
    # Package single document into array to match expected schema from Task 11
    workflow_payload = {
        "loan_application_id": metadata['loan_app_id'],
        "documents": [{
            "document_id": metadata['document_id'],
            "s3_bucket": metadata['bucket'],
            "s3_key": metadata['key'],
            "file_size_bytes": metadata['size'],
            "upload_timestamp": metadata['event_time']
        }]
    }
    
    # Generate unique execution name
    execution_name = f"{metadata['loan_app_id']}-{metadata['document_id']}"
    
    # Start Step Functions execution
    response = sfn_client.start_execution(
        stateMachineArn=STATE_MACHINE_ARN,
        name=execution_name,
        input=json.dumps(workflow_payload)
    )
    
    logger.info(
        f"Successfully started workflow {execution_name}. "
        f"Execution ARN: {response['executionArn']}"
    )
    
    return response


def lambda_handler(event, context):
    """
    Task 13.2: S3 Event Handler Lambda Function
    
    Parse S3 events (routed via SQS for concurrency control),
    extract document metadata, validate file size and format,
    and initiate Step Functions workflow execution.
    
    Requirements:
    - 1.4: Validate file size (reject > 50MB)
    - 10.2: Event trigger invokes Lambda within 5 seconds
    - 10.3: Lambda initiates document processing workflow
    - 10.4: Process documents in upload order
    """
    logger.info(f"Received event with {len(event.get('Records', []))} SQS records.")
    
    processed_count = 0
    failed_count = 0
    batch_item_failures = []
    
    for sqs_record in event.get('Records', []):
        message_id = sqs_record.get('messageId')
        
        try:
            # Parse the SQS body to get the underlying S3 event notification
            s3_event = json.loads(sqs_record['body'])
            
            # Handle S3 test events
            if 'Event' in s3_event and s3_event['Event'] == 's3:TestEvent':
                logger.info("Received S3 Test Event. Skipping.")
                processed_count += 1
                continue

            # Process each S3 record in the event
            for s3_record in s3_event.get('Records', []):
                try:
                    # Extract document metadata
                    metadata = extract_document_metadata(s3_record, context)
                    
                    logger.info(
                        f"Processing document: {metadata['key']} "
                        f"(size: {metadata['size']} bytes, loan: {metadata['loan_app_id']})"
                    )
                    
                    # Validate file format
                    if not validate_file_format(metadata['key']):
                        logger.warning(
                            f"Unsupported file format: {metadata['key']}. "
                            f"Supported formats: {', '.join(SUPPORTED_EXTENSIONS)}"
                        )
                        processed_count += 1
                        continue
                    
                    # Validate file size
                    if not validate_file_size(metadata['size'], metadata['key']):
                        processed_count += 1
                        continue
                    
                    # Initiate Step Functions workflow
                    initiate_workflow(metadata)
                    processed_count += 1
                    
                except Exception as e:
                    logger.error(
                        f"Error processing S3 record for key {metadata.get('key', 'unknown')}: {str(e)}"
                    )
                    # Mark this SQS message as failed for retry
                    batch_item_failures.append({"itemIdentifier": message_id})
                    failed_count += 1

        except Exception as e:
            logger.error(f"Error processing SQS record {message_id}: {str(e)}")
            # Mark this SQS message as failed for retry
            batch_item_failures.append({"itemIdentifier": message_id})
            failed_count += 1
    
    logger.info(
        f"Batch processing complete. Processed: {processed_count}, Failed: {failed_count}"
    )
    
    # Return batch item failures for SQS to retry
    # Requirement 10.4: Process documents in upload order (failed messages will be retried)
    return {
        "batchItemFailures": batch_item_failures
    }
