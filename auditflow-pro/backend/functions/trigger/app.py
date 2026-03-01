# backend/functions/trigger/app.py

import os
import json
import urllib.parse
import logging
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
sfn_client = boto3.client('stepfunctions', region_name=os.environ.get('AWS_REGION', 'ap-south-1'))
STATE_MACHINE_ARN = os.environ.get('STATE_MACHINE_ARN')

# Requirement 1.4 & 10.3: Reject files > 50MB
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024 

def lambda_handler(event, context):
    """
    Task 13.2: Parse S3 events (routed via SQS for concurrency control), 
    validate file size, and initiate Step Functions.
    """
    logger.info(f"Received event with {len(event.get('Records', []))} records.")
    
    for sqs_record in event.get('Records', []):
        try:
            # Parse the SQS body to get the underlying S3 event notification
            s3_event = json.loads(sqs_record['body'])
            
            # S3 test events don't contain 'Records'
            if 'Event' in s3_event and s3_event['Event'] == 's3:TestEvent':
                logger.info("Received S3 Test Event. Skipping.")
                continue

            for s3_record in s3_event.get('Records', []):
                bucket = s3_record['s3']['bucket']['name']
                # Decode URL-encoded keys (e.g., spaces converted to '+')
                key = urllib.parse.unquote_plus(s3_record['s3']['object']['key'], encoding='utf-8')
                size = s3_record['s3']['object']['size']
                
                # 1. Validate File Size (> 50MB)
                if size > MAX_FILE_SIZE_BYTES:
                    logger.error(f"Validation Failed: File {key} exceeds 50MB limit ({size} bytes). Rejecting.")
                    continue # Skip processing this file
                    
                # 2. Extract Loan ID from the S3 Key path (Assuming format: uploads/{loan_id}/{filename})
                parts = key.split('/')
                loan_app_id = parts[1] if len(parts) > 1 else "unknown-loan"
                document_id = f"doc-{context.aws_request_id[:8]}"
                
                # 3. Construct Payload for Step Functions
                # We package the single document into an array to match the expected schema from Task 11
                workflow_payload = {
                    "loan_application_id": loan_app_id,
                    "documents": [{
                        "document_id": document_id,
                        "s3_bucket": bucket,
                        "s3_key": key,
                        "file_size_bytes": size,
                        "upload_timestamp": s3_record['eventTime']
                    }]
                }
                
                # 4. Initiate Step Functions Workflow Execution
                execution_name = f"{loan_app_id}-{document_id}"
                response = sfn_client.start_execution(
                    stateMachineArn=STATE_MACHINE_ARN,
                    name=execution_name,
                    input=json.dumps(workflow_payload)
                )
                
                logger.info(f"Successfully started workflow {execution_name}. Execution ARN: {response['executionArn']}")

        except Exception as e:
            logger.error(f"Error processing SQS record: {str(e)}")
            # Raise exception so SQS knows this message failed and puts it back in the queue for retry
            raise e
            
    return {"statusCode": 200, "message": "Batch processed successfully."}
