# API Handler Lambda Function

## Overview

The API Handler Lambda function serves as the backend for the AuditFlow-Pro API Gateway, providing secure REST API endpoints for frontend integration. It handles document uploads, audit queries, document viewing, and implements role-based PII masking.

**Task**: 15. Implement API Gateway for frontend integration  
**Requirements**: 2.2, 2.8, 16.2, 1.1, 1.3, 1.4, 1.8, 12.4, 13.3, 13.4, 7.5, 7.6, 14.1, 14.2, 18.4, 18.5

## Features

### 1. Document Upload (POST /documents)
- Generates pre-signed S3 URLs for direct client-side uploads
- Validates file format (PDF, JPEG, PNG, TIFF)
- Enforces 50MB file size limit
- Returns document ID and upload URL with 15-minute expiration
- Requires KMS encryption for all uploads

### 2. Audit Queries (GET /audits, GET /audits/{id})
- Lists audit records with pagination (max 100 per page)
- Filters by status, risk score range
- Sorts by timestamp or risk score
- Retrieves detailed audit records by ID
- Applies PII masking based on user role

### 3. Document Viewer (GET /documents/{id}/view)
- Generates pre-signed S3 URLs for document viewing
- 1-hour URL expiration
- Access control based on user permissions
- Fetches document metadata from DynamoDB

### 4. PII Masking
- **Loan Officers**: SSN masked to `***-**-1234`, DOB fully masked
- **Administrators**: Full PII access
- Masks SSN, DOB, and account numbers in audit records and documents

### 5. Logging and Monitoring
- Logs all API requests with user ID, email, groups, and IP
- Logs response status codes
- Logs errors with stack traces
- PII redacted from logs
- CloudWatch metrics enabled

## Architecture

```
API Gateway → Cognito Authorizer → Lambda (API Handler) → S3/DynamoDB
```

### Request Flow

1. Client sends request with JWT token in Authorization header
2. API Gateway validates token with Cognito Authorizer
3. Lambda extracts user identity and groups from claims
4. Lambda routes request to appropriate handler
5. Handler applies business logic and PII masking
6. Response returned with CORS headers

## Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `UPLOAD_BUCKET` | S3 bucket for document storage | `auditflow-documents-ap-south-1-123456789` |
| `AUDIT_TABLE` | DynamoDB table for audit records | `AuditFlow-AuditRecords` |
| `DOCUMENTS_TABLE` | DynamoDB table for document metadata | `AuditFlow-Documents` |
| `KMS_KEY_ARN` | KMS key ARN for encryption | `arn:aws:kms:...` |

## IAM Permissions

The Lambda function requires the following permissions:

- **S3**: `GetObject`, `PutObject`, `ListBucket`
- **DynamoDB**: `GetItem`, `PutItem`, `Query`, `Scan`, `UpdateItem`
- **KMS**: `Decrypt`, `Encrypt`, `GenerateDataKey`
- **CloudWatch Logs**: `CreateLogGroup`, `CreateLogStream`, `PutLogEvents`

## API Endpoints

### POST /documents

Generate pre-signed URL for document upload.

**Request**:
```json
{
  "file_name": "w2_2023.pdf",
  "content_type": "application/pdf",
  "file_size": 1048576,
  "loan_application_id": "loan-abc123"
}
```

**Response**:
```json
{
  "upload_url": "https://s3.amazonaws.com/...",
  "upload_fields": {...},
  "document_id": "550e8400-e29b-41d4-a716-446655440000",
  "loan_application_id": "loan-abc123",
  "s3_key": "uploads/loan-abc123/doc-uuid_w2_2023.pdf",
  "expires_in": 900
}
```

### GET /audits

List audit records with filtering and pagination.

**Query Parameters**:
- `limit` (optional, default: 20, max: 100)
- `last_evaluated_key` (optional, pagination token)
- `status` (optional, filter by status)
- `risk_score_min` (optional, minimum risk score)
- `risk_score_max` (optional, maximum risk score)
- `sort_by` (optional, default: `audit_timestamp`)
- `sort_order` (optional, default: `desc`)

**Response**:
```json
{
  "items": [...],
  "count": 20,
  "scanned_count": 20,
  "last_evaluated_key": "{...}",
  "has_more": true
}
```

### GET /audits/{id}

Get detailed audit record by ID.

**Response**:
```json
{
  "audit_record_id": "audit-uuid",
  "loan_application_id": "loan-abc123",
  "applicant_name": "John Doe",
  "status": "COMPLETED",
  "risk_score": 45,
  "risk_level": "MEDIUM",
  "documents": [...],
  "golden_record": {...},
  "inconsistencies": [...]
}
```

### GET /documents/{id}/view

Generate pre-signed URL for document viewing.

**Query Parameters**:
- `loan_application_id` (optional, for document lookup)

**Response**:
```json
{
  "view_url": "https://s3.amazonaws.com/...?X-Amz-Signature=...",
  "document_id": "550e8400-e29b-41d4-a716-446655440000",
  "loan_application_id": "loan-abc123",
  "expires_in": 3600
}
```

## Error Handling

All errors return JSON responses with appropriate HTTP status codes:

- `400 Bad Request`: Invalid input, validation errors
- `401 Unauthorized`: Missing or invalid authentication token
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Resource not found
- `500 Internal Server Error`: Server-side errors

**Error Response Format**:
```json
{
  "error": "Error message describing the issue",
  "request_id": "abc-123"
}
```

## Security

### Authentication
- All endpoints require Cognito JWT token
- Token validated by API Gateway Cognito Authorizer
- User identity extracted from token claims

### Authorization
- Role-based access control using Cognito groups
- LoanOfficers: Read access with PII masking
- Administrators: Full access including unmasked PII

### Encryption
- All S3 uploads require KMS encryption
- Pre-signed URLs enforce encryption conditions
- Data at rest encrypted in S3 and DynamoDB

### PII Protection
- SSN masked to `***-**-1234` for Loan Officers
- DOB fully masked to `****-**-**`
- Account numbers masked to `****1234`
- PII redacted from CloudWatch logs

## Deployment

### Prerequisites
1. S3 bucket created
2. DynamoDB tables created
3. KMS key configured
4. Cognito User Pool set up

### Deploy Lambda Function

```bash
./infrastructure/deploy_api_handler.sh
```

This script:
1. Creates IAM role with necessary permissions
2. Packages Lambda function code
3. Creates or updates Lambda function
4. Configures environment variables
5. Sets CloudWatch Logs retention to 1 year

### Deploy API Gateway

```bash
./infrastructure/api_gateway_setup.sh
```

This script:
1. Creates REST API with regional endpoint
2. Creates Cognito Authorizer
3. Defines API resources and methods
4. Configures CORS for all endpoints
5. Integrates with Lambda function
6. Deploys to production stage

## Testing

### Unit Tests

Run unit tests for individual functions:

```bash
python3 -m pytest backend/tests/test_api_handler.py -v
```

### Integration Tests

Run integration tests with mocked AWS services:

```bash
python3 -m pytest backend/tests/integration/test_api_gateway.py -v
```

Test coverage includes:
- Document upload validation
- Audit query filtering and pagination
- PII masking for different roles
- Document viewer URL generation
- Error handling and validation
- Authentication and authorization

### Manual Testing

```bash
# Get authentication token
ID_TOKEN=$(aws cognito-idp initiate-auth \
  --auth-flow USER_PASSWORD_AUTH \
  --client-id ${CLIENT_ID} \
  --auth-parameters USERNAME=${EMAIL},PASSWORD=${PASSWORD} \
  --query 'AuthenticationResult.IdToken' \
  --output text)

# Test document upload
curl -X POST ${API_ENDPOINT}/documents \
  -H "Authorization: Bearer ${ID_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "file_name": "test.pdf",
    "content_type": "application/pdf",
    "file_size": 1048576,
    "loan_application_id": "loan-test"
  }'

# Test list audits
curl ${API_ENDPOINT}/audits?limit=10&risk_score_min=50 \
  -H "Authorization: Bearer ${ID_TOKEN}"

# Test get audit details
curl ${API_ENDPOINT}/audits/${AUDIT_ID} \
  -H "Authorization: Bearer ${ID_TOKEN}"

# Test document viewer
curl "${API_ENDPOINT}/documents/${DOC_ID}/view?loan_application_id=loan-test" \
  -H "Authorization: Bearer ${ID_TOKEN}"
```

## Monitoring

### CloudWatch Logs

**Log Group**: `/aws/lambda/AuditFlowAPIHandler`

View logs:
```bash
aws logs tail /aws/lambda/AuditFlowAPIHandler --follow --region ap-south-1
```

Filter by user:
```bash
aws logs filter-log-events \
  --log-group-name /aws/lambda/AuditFlowAPIHandler \
  --filter-pattern "User: user-uuid" \
  --region ap-south-1
```

### CloudWatch Metrics

Key metrics:
- Request count
- Error rate (4XX, 5XX)
- Latency
- Integration latency

Create alarm for high error rate:
```bash
aws cloudwatch put-metric-alarm \
  --alarm-name AuditFlowAPI-HighErrorRate \
  --metric-name 5XXError \
  --namespace AWS/ApiGateway \
  --statistic Sum \
  --period 300 \
  --evaluation-periods 1 \
  --threshold 5 \
  --comparison-operator GreaterThanThreshold
```

## Troubleshooting

### Common Issues

**401 Unauthorized**
- Verify token is included in Authorization header
- Check token hasn't expired (30-minute lifetime)
- Ensure Cognito User Pool ID matches authorizer

**403 Forbidden**
- Verify user is in correct Cognito group
- Check IAM role policies for Identity Pool

**500 Internal Server Error**
- Check CloudWatch Logs for error details
- Verify environment variables are set
- Ensure Lambda has necessary IAM permissions

**CORS Errors**
- Verify OPTIONS method is configured
- Check Access-Control-Allow-Origin header
- Update CORS configuration for frontend domain

## Performance

### Optimization Tips

1. **Enable API Gateway caching** for GET endpoints
2. **Use provisioned concurrency** for consistent performance
3. **Optimize DynamoDB queries** with GSIs
4. **Implement connection pooling** for boto3 clients
5. **Use Lambda layers** for shared dependencies

### Estimated Costs

For 1 million requests/month:
- API Gateway: ~$3.50
- Lambda execution: ~$10
- **Total**: ~$13.50/month

## References

- [API Gateway Documentation](../../infrastructure/API_GATEWAY.md)
- [Cognito Setup](../../infrastructure/COGNITO_AUTHENTICATION.md)
- [DynamoDB Schema](../../infrastructure/DYNAMODB_SCHEMA.md)
- [S3 Configuration](../../infrastructure/S3_CONFIGURATION.md)
