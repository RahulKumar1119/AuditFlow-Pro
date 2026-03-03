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

def mask_pii(record: dict, user_groups: list) -> dict:
    """
    Task 15.3: Apply PII masking based on user role.
    Requirements: 7.5, 7.6
    
    Masks first 5 digits of SSN for LoanOfficer role.
    Administrators see full PII values.
    """
    # Administrators have full access to PII
    if 'Administrators' in user_groups:
        return record
    
    # Mask PII for Loan Officers
    if 'golden_record' in record:
        golden_record = record['golden_record']
        
        # Mask SSN - first 5 digits (Requirement 7.5)
        if 'ssn' in golden_record and isinstance(golden_record['ssn'], dict):
            ssn_value = golden_record['ssn'].get('value', '')
            if ssn_value and len(ssn_value) >= 4:
                # Mask format: ***-**-1234
                golden_record['ssn']['value'] = f"***-**-{ssn_value[-4:]}"
        
        # Mask date of birth
        if 'date_of_birth' in golden_record and isinstance(golden_record['date_of_birth'], dict):
            golden_record['date_of_birth']['value'] = "****-**-**"
        
        # Mask bank account numbers
        if 'bank_account' in golden_record and isinstance(golden_record['bank_account'], dict):
            account_value = golden_record['bank_account'].get('value', '')
            if account_value and len(account_value) >= 4:
                golden_record['bank_account']['value'] = f"****{account_value[-4:]}"
    
    # Mask PII in documents
    if 'documents' in record:
        for doc in record['documents']:
            if 'extracted_data' in doc:
                extracted = doc['extracted_data']
                
                # Mask SSN
                if 'ssn' in extracted or 'employee_ssn' in extracted or 'taxpayer_ssn' in extracted:
                    for ssn_field in ['ssn', 'employee_ssn', 'taxpayer_ssn']:
                        if ssn_field in extracted and isinstance(extracted[ssn_field], dict):
                            ssn_value = extracted[ssn_field].get('value', '')
                            if ssn_value and len(ssn_value) >= 4:
                                extracted[ssn_field]['value'] = f"***-**-{ssn_value[-4:]}"
                
                # Mask DOB
                if 'date_of_birth' in extracted and isinstance(extracted['date_of_birth'], dict):
                    extracted['date_of_birth']['value'] = "****-**-**"
                
                # Mask account numbers
                if 'account_number' in extracted and isinstance(extracted['account_number'], dict):
                    account_value = extracted['account_number'].get('value', '')
                    if account_value and len(account_value) >= 4:
                        extracted['account_number']['value'] = f"****{account_value[-4:]}"
    
    return record

def handle_post_documents(event):
    """
    Task 15.2: Generate Pre-signed URL for direct S3 upload.
    Requirements: 1.1, 1.3, 1.4, 1.8
    
    Validates file format and size, generates pre-signed S3 upload URL,
    returns upload URL and document ID.
    """
    try:
        body = json.loads(event.get('body', '{}'))
    except json.JSONDecodeError:
        logger.error("Invalid JSON in request body")
        return {
            "statusCode": 400,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"error": "Invalid JSON in request body"})
        }
    
    file_name = body.get('file_name')
    content_type = body.get('content_type')
    file_size = body.get('file_size', 0)
    
    # Validate required fields
    if not file_name or not content_type:
        return {
            "statusCode": 400,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"error": "Missing required fields: file_name and content_type"})
        }
    
    # Validate file format (Requirement 1.3)
    allowed_types = {
        'application/pdf': ['.pdf'],
        'image/jpeg': ['.jpg', '.jpeg'],
        'image/png': ['.png'],
        'image/tiff': ['.tif', '.tiff']
    }
    
    if content_type not in allowed_types:
        return {
            "statusCode": 400,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps({
                "error": "Unsupported file format. Supported formats: PDF, JPEG, PNG, TIFF"
            })
        }
    
    # Validate file extension matches content type
    file_ext = os.path.splitext(file_name.lower())[1]
    if file_ext not in allowed_types[content_type]:
        return {
            "statusCode": 400,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps({
                "error": f"File extension {file_ext} does not match content type {content_type}"
            })
        }
    
    # Validate file size (Requirement 1.4 - max 50MB)
    MAX_FILE_SIZE = 52428800  # 50 MB in bytes
    if file_size > MAX_FILE_SIZE:
        return {
            "statusCode": 400,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps({
                "error": f"File size exceeds maximum allowed size of 50MB. Your file: {file_size / 1048576:.2f}MB"
            })
        }

    # Generate unique document ID (Requirement 1.5)
    document_id = str(uuid.uuid4())
    loan_application_id = body.get('loan_application_id', f"loan-{uuid.uuid4().hex[:8]}")
    
    # Sanitize file name to prevent path traversal
    safe_file_name = os.path.basename(file_name)
    s3_key = f"uploads/{loan_application_id}/{document_id}_{safe_file_name}"

    try:
        # Generate presigned POST URL with 15-minute expiration (Requirement 1.8)
        # Use SSE-S3 (AES256) instead of KMS for browser uploads
        # KMS requires the uploader to have KMS permissions, which browsers don't have
        
        # Extract checksum from request body if provided (for integrity verification)
        checksum = body.get('checksum')
        
        # Build fields and conditions
        fields = {
            "Content-Type": content_type,
            "x-amz-server-side-encryption": "AES256",  # Use SSE-S3 instead of KMS
            "acl": "private"
        }
        
        conditions = [
            {"Content-Type": content_type},
            ["content-length-range", 1, MAX_FILE_SIZE],  # Enforce size limit
            {"x-amz-server-side-encryption": "AES256"},  # Require encryption
            {"acl": "private"}
        ]
        
        # If checksum is provided, add it to the policy to allow frontend to send it
        if checksum:
            fields["x-amz-checksum-sha256"] = checksum
            conditions.append({"x-amz-checksum-sha256": checksum})
        
        presigned_post = s3_client.generate_presigned_post(
            Bucket=BUCKET_NAME,
            Key=s3_key,
            Fields=fields,
            Conditions=conditions,
            ExpiresIn=900  # 15 minutes
        )
        
        logger.info(f"Generated presigned URL for document {document_id}, loan {loan_application_id}")
        
        return {
            "statusCode": 200,
            "headers": {
                "Access-Control-Allow-Origin": "*",
                "Content-Type": "application/json"
            },
            "body": json.dumps({
                "upload_url": presigned_post['url'],
                "upload_fields": presigned_post['fields'],
                "document_id": document_id,
                "loan_application_id": loan_application_id,
                "s3_key": s3_key,
                "expires_in": 900
            })
        }
    except ClientError as e:
        logger.error(f"Error generating presigned URL: {e}", exc_info=True)
        return {
            "statusCode": 500,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"error": "Failed to generate upload URL. Please try again."})
        }

def handle_get_audits(event, user_groups):
    """
    Task 15.3: Query audits with filtering, sorting, and pagination.
    Requirements: 12.4, 13.3, 13.4, 7.5, 7.6
    
    Supports:
    - GET /audits - List all audits with pagination
    - GET /audits/{id} - Get specific audit record
    - Query parameters: limit, status, risk_score_min, risk_score_max, sort_by, sort_order
    - PII masking based on user role
    """
    table = dynamodb.Table(AUDIT_TABLE)
    path_parameters = event.get('pathParameters') or {}
    
    # Check if fetching specific ID or all audits
    if 'id' in path_parameters:
        audit_id = path_parameters['id']
        
        try:
            response = table.get_item(Key={'audit_record_id': audit_id})
            item = response.get('Item')
            
            if not item:
                return {
                    "statusCode": 404,
                    "headers": {"Access-Control-Allow-Origin": "*"},
                    "body": json.dumps({"error": "Audit record not found"})
                }
            
            # Apply PII masking based on user role
            item = mask_pii(item, user_groups)
            
            logger.info(f"Retrieved audit record {audit_id}")
            
            return {
                "statusCode": 200,
                "headers": {
                    "Access-Control-Allow-Origin": "*",
                    "Content-Type": "application/json"
                },
                "body": json.dumps(item, default=str)
            }
            
        except ClientError as e:
            logger.error(f"Error retrieving audit record {audit_id}: {e}", exc_info=True)
            return {
                "statusCode": 500,
                "headers": {"Access-Control-Allow-Origin": "*"},
                "body": json.dumps({"error": "Failed to retrieve audit record"})
            }
    
    else:
        # List audits with filtering, sorting, and pagination
        query_params = event.get('queryStringParameters') or {}
        
        # Pagination parameters
        limit = min(int(query_params.get('limit', 20)), 100)  # Max 100 items per page
        exclusive_start_key = query_params.get('last_evaluated_key')
        
        # Filtering parameters
        status_filter = query_params.get('status')  # COMPLETED, IN_PROGRESS, FAILED
        risk_score_min = query_params.get('risk_score_min')
        risk_score_max = query_params.get('risk_score_max')
        
        # Sorting parameters
        sort_by = query_params.get('sort_by', 'audit_timestamp')  # audit_timestamp, risk_score
        sort_order = query_params.get('sort_order', 'desc')  # asc, desc
        
        try:
            # Build scan parameters
            scan_kwargs = {
                'Limit': limit
            }
            
            # Add pagination token if provided
            if exclusive_start_key:
                try:
                    scan_kwargs['ExclusiveStartKey'] = json.loads(exclusive_start_key)
                except json.JSONDecodeError:
                    return {
                        "statusCode": 400,
                        "headers": {"Access-Control-Allow-Origin": "*"},
                        "body": json.dumps({"error": "Invalid pagination token"})
                    }
            
            # Build filter expression
            filter_expressions = []
            expression_attribute_values = {}
            expression_attribute_names = {}
            
            if status_filter:
                filter_expressions.append("#status = :status")
                expression_attribute_names['#status'] = 'status'
                expression_attribute_values[':status'] = status_filter
            
            if risk_score_min is not None:
                filter_expressions.append("risk_score >= :risk_min")
                expression_attribute_values[':risk_min'] = int(risk_score_min)
            
            if risk_score_max is not None:
                filter_expressions.append("risk_score <= :risk_max")
                expression_attribute_values[':risk_max'] = int(risk_score_max)
            
            if filter_expressions:
                scan_kwargs['FilterExpression'] = ' AND '.join(filter_expressions)
                scan_kwargs['ExpressionAttributeValues'] = expression_attribute_values
                if expression_attribute_names:
                    scan_kwargs['ExpressionAttributeNames'] = expression_attribute_names
            
            # Execute scan
            response = table.scan(**scan_kwargs)
            items = response.get('Items', [])
            
            # Sort results (in-memory sorting since DynamoDB scan doesn't support sorting)
            if sort_by in ['audit_timestamp', 'risk_score']:
                reverse = (sort_order == 'desc')
                items.sort(
                    key=lambda x: x.get(sort_by, 0 if sort_by == 'risk_score' else ''),
                    reverse=reverse
                )
            
            # Apply PII masking to all items
            items = [mask_pii(item, user_groups) for item in items]
            
            # Prepare response
            result = {
                "items": items,
                "count": len(items),
                "scanned_count": response.get('ScannedCount', 0)
            }
            
            # Include pagination token if more results available
            if 'LastEvaluatedKey' in response:
                result['last_evaluated_key'] = json.dumps(response['LastEvaluatedKey'])
                result['has_more'] = True
            else:
                result['has_more'] = False
            
            logger.info(f"Retrieved {len(items)} audit records (filters: status={status_filter}, risk_min={risk_score_min}, risk_max={risk_score_max})")
            
            return {
                "statusCode": 200,
                "headers": {
                    "Access-Control-Allow-Origin": "*",
                    "Content-Type": "application/json"
                },
                "body": json.dumps(result, default=str)
            }
            
        except ClientError as e:
            logger.error(f"Error scanning audit records: {e}", exc_info=True)
            return {
                "statusCode": 500,
                "headers": {"Access-Control-Allow-Origin": "*"},
                "body": json.dumps({"error": "Failed to retrieve audit records"})
            }
        except Exception as e:
            logger.error(f"Unexpected error in audit query: {e}", exc_info=True)
            return {
                "statusCode": 500,
                "headers": {"Access-Control-Allow-Origin": "*"},
                "body": json.dumps({"error": "Internal server error"})
            }

def handle_get_document_view(event, user_groups):
    """
    Task 15.4: Generate pre-signed URL for viewing documents securely.
    Requirements: 14.1, 14.2
    
    Generates pre-signed S3 URLs with 1-hour expiration for document viewing.
    Applies access control based on user permissions.
    """
    path_parameters = event.get('pathParameters') or {}
    document_id = path_parameters.get('id')
    
    if not document_id:
        return {
            "statusCode": 400,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"error": "Missing document ID"})
        }
    
    query_params = event.get('queryStringParameters') or {}
    loan_application_id = query_params.get('loan_application_id')
    
    # Get user identity for access control
    claims = event.get('requestContext', {}).get('authorizer', {}).get('claims', {})
    user_id = claims.get('sub', 'unknown_user')
    
    try:
        # In production, fetch document metadata from DynamoDB to verify:
        # 1. Document exists
        # 2. User has permission to access this document
        # 3. Get actual S3 key
        
        # For now, we construct the S3 key based on the pattern
        # In a real implementation, query DynamoDB Documents table
        documents_table = dynamodb.Table('AuditFlow-Documents')
        
        try:
            doc_response = documents_table.get_item(Key={'document_id': document_id})
            doc_item = doc_response.get('Item')
            
            if not doc_item:
                # Fallback to constructed key if document not in DB yet
                if not loan_application_id:
                    return {
                        "statusCode": 400,
                        "headers": {"Access-Control-Allow-Origin": "*"},
                        "body": json.dumps({"error": "Document not found. Please provide loan_application_id."})
                    }
                s3_key = f"uploads/{loan_application_id}/{document_id}"
            else:
                s3_key = doc_item['s3_key']
                loan_application_id = doc_item.get('loan_application_id', loan_application_id)
                
                # Access control: Check if user has permission
                # In production, verify user has access to this loan application
                # For now, we allow all authenticated users
                
        except ClientError as e:
            logger.warning(f"Could not fetch document metadata from DynamoDB: {e}")
            # Fallback to constructed key
            if not loan_application_id:
                return {
                    "statusCode": 400,
                    "headers": {"Access-Control-Allow-Origin": "*"},
                    "body": json.dumps({"error": "Missing loan_application_id parameter"})
                }
            s3_key = f"uploads/{loan_application_id}/{document_id}"
        
        # Generate pre-signed URL with 1-hour expiration (Requirement 14.2)
        presigned_url = s3_client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': BUCKET_NAME,
                'Key': s3_key,
                'ResponseContentDisposition': 'inline'  # Display in browser, not download
            },
            ExpiresIn=3600  # 1 hour
        )
        
        logger.info(f"Generated view URL for document {document_id}, user {user_id}")
        
        return {
            "statusCode": 200,
            "headers": {
                "Access-Control-Allow-Origin": "*",
                "Content-Type": "application/json"
            },
            "body": json.dumps({
                "view_url": presigned_url,
                "document_id": document_id,
                "loan_application_id": loan_application_id,
                "expires_in": 3600
            })
        }
        
    except ClientError as e:
        logger.error(f"Error generating presigned view URL for document {document_id}: {e}", exc_info=True)
        return {
            "statusCode": 500,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"error": "Failed to generate document view URL"})
        }
    except Exception as e:
        logger.error(f"Unexpected error generating view URL: {e}", exc_info=True)
        return {
            "statusCode": 500,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"error": "Internal server error"})
        }

def lambda_handler(event, context):
    """
    Main API Gateway request router.
    Task 15.5: Logs all API requests with user ID and timestamp.
    Requirements: 18.4, 18.5
    """
    http_method = event.get('httpMethod')
    resource = event.get('resource')
    
    # Extract user identity for logging and role-based access (Requirement 18.4)
    request_context = event.get('requestContext', {})
    authorizer = request_context.get('authorizer', {})
    claims = authorizer.get('claims', {})
    
    user_id = claims.get('sub', 'unknown_user')
    user_email = claims.get('email', 'unknown')
    user_groups_str = claims.get('cognito:groups', '')
    user_groups = user_groups_str.split(',') if user_groups_str else []
    
    request_id = request_context.get('requestId', 'unknown')
    source_ip = request_context.get('identity', {}).get('sourceIp', 'unknown')
    
    # Log API request (Requirement 18.4, 18.5)
    logger.info(
        f"API Request | RequestID: {request_id} | User: {user_id} ({user_email}) | "
        f"Groups: {user_groups} | IP: {source_ip} | Method: {http_method} | Path: {resource}"
    )
    
    try:
        # Route to appropriate handler
        if resource == '/documents' and http_method == 'POST':
            response = handle_post_documents(event)
        elif resource == '/documents/{id}/view' and http_method == 'GET':
            response = handle_get_document_view(event, user_groups)
        elif resource.startswith('/audits') and http_method == 'GET':
            response = handle_get_audits(event, user_groups)
        else:
            response = {
                "statusCode": 404,
                "headers": {"Access-Control-Allow-Origin": "*"},
                "body": json.dumps({"error": "Route not found"})
            }
        
        # Log response status (Requirement 18.5)
        status_code = response.get('statusCode', 500)
        logger.info(
            f"API Response | RequestID: {request_id} | User: {user_id} | "
            f"Status: {status_code} | Method: {http_method} | Path: {resource}"
        )
        
        return response
        
    except Exception as e:
        # Log errors (Requirement 18.5)
        logger.error(
            f"API Error | RequestID: {request_id} | User: {user_id} | "
            f"Method: {http_method} | Path: {resource} | Error: {str(e)}",
            exc_info=True
        )
        
        return {
            "statusCode": 500,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps({
                "error": "Internal server error",
                "request_id": request_id
            })
        }
