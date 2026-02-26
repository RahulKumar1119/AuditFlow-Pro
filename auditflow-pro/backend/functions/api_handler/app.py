# backend/functions/api_handler/app.py

import os
import json
import uuid
import boto3
import logging
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3_client = boto3.client('s3', config=boto3.session.Config(signature_version='s3v4'))
dynamodb = boto3.resource('dynamodb')

BUCKET_NAME = os.environ.get('UPLOAD_BUCKET', 'auditflow-documents')
AUDIT_TABLE = os.environ.get('AUDIT_TABLE', 'AuditFlow-AuditRecords')

def mask_pii(record: dict) -> dict:
    """Task 15.3: Apply PII masking for non-admin users."""
    if 'golden_record' in record:
        if 'ssn' in record['golden_record']:
            record['golden_record']['ssn']['value'] = "***-**-****"
        if 'date_of_birth' in record['golden_record']:
            record['golden_record']['date_of_birth']['value'] = "**/**/****"
    return record

def handle_post_documents(event):
    """Task 15.2: Generate Pre-signed URL for direct S3 upload."""
    body = json.loads(event.get('body', '{}'))
    file_name = body.get('file_name', 'unknown.pdf')
    content_type = body.get('content_type', 'application/pdf')
    
    # 1. Validate file format (Task 15.2)
    allowed_types = ['application/pdf', 'image/jpeg', 'image/png', 'image/tiff']
    if content_type not in allowed_types:
        return {"statusCode": 400, "body": json.dumps({"error": "Unsupported file format."})}

    document_id = str(uuid.uuid4())
    loan_application_id = body.get('loan_application_id', f"loan-{uuid.uuid4().hex[:8]}")
    s3_key = f"uploads/{loan_application_id}/{document_id}_{file_name}"

    try:
        # Generate presigned URL (Enforces 50MB limit natively in S3 conditions)
        presigned_post = s3_client.generate_presigned_post(
            Bucket=BUCKET_NAME,
            Key=s3_key,
            Fields={"Content-Type": content_type},
            Conditions=[
                {"Content-Type": content_type},
                ["content-length-range", 0, 52428800] # 50 MB limit
            ],
            ExpiresIn=3600
        )
        return {
            "statusCode": 200,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps({
                "upload_url_data": presigned_post,
                "document_id": document_id,
                "loan_application_id": loan_application_id
            })
        }
    except ClientError as e:
        logger.error(f"Error generating presigned URL: {e}")
        return {"statusCode": 500, "body": json.dumps({"error": "Internal server error"})}

def handle_get_audits(event, user_groups):
    """Task 15.3: Query audits with pagination and PII masking."""
    table = dynamodb.Table(AUDIT_TABLE)
    path_parameters = event.get('pathParameters') or {}
    
    # Check if fetching specific ID or all audits
    if 'id' in path_parameters:
        response = table.get_item(Key={'audit_record_id': path_parameters['id']})
        item = response.get('Item')
        if not item:
            return {"statusCode": 404, "body": json.dumps({"error": "Audit not found"})}
            
        if 'Administrator' not in user_groups:
            item = mask_pii(item)
            
        return {"statusCode": 200, "headers": {"Access-Control-Allow-Origin": "*"}, "body": json.dumps(item)}
        
    else:
        # Implement Pagination & Scanning (In production, use Query with GSIs)
        query_params = event.get('queryStringParameters') or {}
        limit = int(query_params.get('limit', 20))
        
        scan_kwargs = {'Limit': limit}
        if 'ExclusiveStartKey' in query_params:
            scan_kwargs['ExclusiveStartKey'] = json.loads(query_params['ExclusiveStartKey'])
            
        response = table.scan(**scan_kwargs)
        items = response.get('Items', [])
        
        if 'Administrator' not in user_groups:
            items = [mask_pii(item) for item in items]
            
        return {
            "statusCode": 200,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps({
                "items": items,
                "LastEvaluatedKey": response.get('LastEvaluatedKey')
            })
        }

def handle_get_document_view(event):
    """Task 15.4: Generate pre-signed URL for viewing documents securely."""
    document_id = event['pathParameters']['id']
    query_params = event.get('queryStringParameters') or {}
    loan_id = query_params.get('loan_application_id')
    
    if not loan_id:
        return {"statusCode": 400, "body": json.dumps({"error": "Missing loan_application_id"})}
        
    # In a real scenario, you'd fetch the exact S3 key from DynamoDB using the document_id
    # We simulate the key generation here for brevity
    s3_key = f"uploads/{loan_id}/{document_id}.pdf"
    
    try:
        presigned_url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': BUCKET_NAME, 'Key': s3_key},
            ExpiresIn=900 # 15 minutes
        )
        return {
            "statusCode": 200, 
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"view_url": presigned_url})
        }
    except ClientError as e:
        logger.error(f"Error generating presigned view URL: {e}")
        return {"statusCode": 500, "body": json.dumps({"error": "Could not generate view link"})}

def lambda_handler(event, context):
    """Main Router."""
    http_method = event.get('httpMethod')
    resource = event.get('resource')
    
    # Extract user identity for logging and role-based access
    claims = event.get('requestContext', {}).get('authorizer', {}).get('claims', {})
    user_id = claims.get('sub', 'unknown_user')
    user_groups = claims.get('cognito:groups', '')
    
    logger.info(f"API Request | User: {user_id} | Method: {http_method} | Path: {resource}")
    
    if resource == '/documents' and http_method == 'POST':
        return handle_post_documents(event)
    elif resource == '/documents/{id}/view' and http_method == 'GET':
        return handle_get_document_view(event)
    elif resource.startswith('/audits') and http_method == 'GET':
        return handle_get_audits(event, user_groups)
        
    return {"statusCode": 404, "body": json.dumps({"error": "Route not found"})}
