# API Gateway Configuration Guide

## Overview

This document describes the API Gateway REST API implementation for AuditFlow-Pro, providing secure frontend integration with Cognito authentication, CORS support, and comprehensive logging.

**Task**: 15. Implement API Gateway for frontend integration  
**Requirements**: 2.2, 2.8, 16.2, 1.1, 1.3, 1.4, 1.8, 12.4, 13.3, 13.4, 7.5, 7.6, 14.1, 14.2, 18.4, 18.5

## Architecture

```
Frontend (React) → API Gateway → Cognito Authorizer → Lambda (API Handler) → S3/DynamoDB
```

### Components

1. **API Gateway REST API**: Regional endpoint with TLS 1.2+
2. **Cognito Authorizer**: Validates JWT tokens from Cognito User Pool
3. **API Handler Lambda**: Routes requests and implements business logic
4. **CORS Configuration**: Allows frontend domain access
5. **CloudWatch Logging**: Tracks all API requests and responses

## API Endpoints

### Base URL
```
https://{api-id}.execute-api.{region}.amazonaws.com/prod
```

### Endpoints

#### 1. Document Upload
**POST /documents**

Generates a pre-signed S3 URL for direct document upload.

**Authentication**: Required (Cognito JWT token)

**Request Body**:
```json
{
  "file_name": "w2_2023.pdf",
  "content_type": "application/pdf",
  "file_size": 1048576,
  "loan_application_id": "loan-abc123"
}
```

**Supported Content Types**:
- `application/pdf` - PDF documents
- `image/jpeg` - JPEG images
- `image/png` - PNG images
- `image/tiff` - TIFF images

**File Size Limit**: 50 MB (52,428,800 bytes)

**Response** (200 OK):
```json
{
  "upload_url": "https://s3.amazonaws.com/...",
  "upload_fields": {
    "key": "uploads/loan-abc123/doc-uuid_w2_2023.pdf",
    "AWSAccessKeyId": "...",
    "policy": "...",
    "signature": "..."
  },
  "document_id": "550e8400-e29b-41d4-a716-446655440000",
  "loan_application_id": "loan-abc123",
  "s3_key": "uploads/loan-abc123/doc-uuid_w2_2023.pdf",
  "expires_in": 900
}
```

**Error Responses**:
- `400 Bad Request`: Invalid file format, size exceeds limit, missing fields
- `401 Unauthorized`: Missing or invalid authentication token
- `500 Internal Server Error`: Failed to generate upload URL

**Usage Example**:
```javascript
// Step 1: Get pre-signed URL
const response = await fetch(`${API_ENDPOINT}/documents`, {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${idToken}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    file_name: file.name,
    content_type: file.type,
    file_size: file.size,
    loan_application_id: loanId
  })
});

const { upload_url, upload_fields, document_id } = await response.json();

// Step 2: Upload file directly to S3
const formData = new FormData();
Object.entries(upload_fields).forEach(([key, value]) => {
  formData.append(key, value);
});
formData.append('file', file);

await fetch(upload_url, {
  method: 'POST',
  body: formData
});
```

---

#### 2. Document Viewer
**GET /documents/{id}/view**

Generates a pre-signed S3 URL for viewing a document.

**Authentication**: Required (Cognito JWT token)

**Path Parameters**:
- `id` (required): Document UUID

**Query Parameters**:
- `loan_application_id` (optional): Loan application ID for document lookup

**Response** (200 OK):
```json
{
  "view_url": "https://s3.amazonaws.com/...?X-Amz-Signature=...",
  "document_id": "550e8400-e29b-41d4-a716-446655440000",
  "loan_application_id": "loan-abc123",
  "expires_in": 3600
}
```

**URL Expiration**: 1 hour (3600 seconds)

**Error Responses**:
- `400 Bad Request`: Missing document ID or loan application ID
- `401 Unauthorized`: Missing or invalid authentication token
- `404 Not Found`: Document does not exist
- `500 Internal Server Error`: Failed to generate view URL

**Usage Example**:
```javascript
const response = await fetch(
  `${API_ENDPOINT}/documents/${documentId}/view?loan_application_id=${loanId}`,
  {
    headers: {
      'Authorization': `Bearer ${idToken}`
    }
  }
);

const { view_url } = await response.json();

// Open document in new tab or embed in iframe
window.open(view_url, '_blank');
```

---

#### 3. List Audits
**GET /audits**

Retrieves a paginated list of audit records with filtering and sorting.

**Authentication**: Required (Cognito JWT token)

**Query Parameters**:
- `limit` (optional, default: 20, max: 100): Number of items per page
- `last_evaluated_key` (optional): Pagination token from previous response
- `status` (optional): Filter by status (`COMPLETED`, `IN_PROGRESS`, `FAILED`)
- `risk_score_min` (optional): Minimum risk score (0-100)
- `risk_score_max` (optional): Maximum risk score (0-100)
- `sort_by` (optional, default: `audit_timestamp`): Sort field (`audit_timestamp`, `risk_score`)
- `sort_order` (optional, default: `desc`): Sort order (`asc`, `desc`)

**Response** (200 OK):
```json
{
  "items": [
    {
      "audit_record_id": "audit-uuid",
      "loan_application_id": "loan-abc123",
      "applicant_name": "John Doe",
      "audit_timestamp": "2024-01-15T10:35:00Z",
      "status": "COMPLETED",
      "risk_score": 45,
      "risk_level": "MEDIUM",
      "documents": [...],
      "golden_record": {
        "name": {"value": "John Doe", "confidence": 0.98},
        "ssn": {"value": "***-**-1234", "confidence": 0.99}
      },
      "inconsistencies": [...]
    }
  ],
  "count": 20,
  "scanned_count": 20,
  "last_evaluated_key": "{...}",
  "has_more": true
}
```

**PII Masking**:
- **Loan Officers**: SSN masked to `***-**-1234`, DOB masked to `****-**-**`
- **Administrators**: Full PII values visible

**Error Responses**:
- `400 Bad Request`: Invalid pagination token or query parameters
- `401 Unauthorized`: Missing or invalid authentication token
- `500 Internal Server Error`: Failed to retrieve audit records

**Usage Example**:
```javascript
// Fetch high-risk audits
const response = await fetch(
  `${API_ENDPOINT}/audits?risk_score_min=50&sort_by=risk_score&sort_order=desc&limit=50`,
  {
    headers: {
      'Authorization': `Bearer ${idToken}`
    }
  }
);

const { items, has_more, last_evaluated_key } = await response.json();

// Fetch next page if available
if (has_more) {
  const nextPage = await fetch(
    `${API_ENDPOINT}/audits?last_evaluated_key=${encodeURIComponent(last_evaluated_key)}`,
    {
      headers: {
        'Authorization': `Bearer ${idToken}`
      }
    }
  );
}
```

---

#### 4. Get Audit Details
**GET /audits/{id}**

Retrieves detailed information for a specific audit record.

**Authentication**: Required (Cognito JWT token)

**Path Parameters**:
- `id` (required): Audit record UUID

**Response** (200 OK):
```json
{
  "audit_record_id": "audit-uuid",
  "loan_application_id": "loan-abc123",
  "applicant_name": "John Doe",
  "audit_timestamp": "2024-01-15T10:35:00Z",
  "processing_duration_seconds": 45,
  "status": "COMPLETED",
  "documents": [
    {
      "document_id": "doc-uuid-1",
      "document_type": "W2",
      "file_name": "w2_2023.pdf",
      "extracted_data": {
        "employee_name": {"value": "John Doe", "confidence": 0.98},
        "wages": {"value": 75000.00, "confidence": 0.99}
      }
    }
  ],
  "golden_record": {
    "name": {"value": "John Doe", "source_document": "doc-uuid-1", "confidence": 0.98},
    "ssn": {"value": "***-**-1234", "source_document": "doc-uuid-2", "confidence": 0.99}
  },
  "inconsistencies": [
    {
      "inconsistency_id": "inc-uuid",
      "field": "address",
      "severity": "HIGH",
      "expected_value": "123 Main St",
      "actual_value": "456 Oak Ave",
      "source_documents": ["doc-uuid-1", "doc-uuid-2"],
      "description": "Address mismatch detected"
    }
  ],
  "risk_score": 45,
  "risk_level": "MEDIUM",
  "risk_factors": [
    {"factor": "address_mismatch", "points": 20, "description": "Address mismatch detected"},
    {"factor": "low_confidence_extraction", "points": 10, "description": "2 fields below 80% confidence"}
  ]
}
```

**PII Masking**: Same as List Audits endpoint

**Error Responses**:
- `401 Unauthorized`: Missing or invalid authentication token
- `404 Not Found`: Audit record does not exist
- `500 Internal Server Error`: Failed to retrieve audit record

**Usage Example**:
```javascript
const response = await fetch(
  `${API_ENDPOINT}/audits/${auditId}`,
  {
    headers: {
      'Authorization': `Bearer ${idToken}`
    }
  }
);

const auditDetails = await response.json();
```

---

## Authentication

All API endpoints require authentication using Cognito JWT tokens.

### Getting Authentication Token

```javascript
import { Auth } from 'aws-amplify';

// Sign in
const user = await Auth.signIn(email, password);

// Get ID token
const session = await Auth.currentSession();
const idToken = session.getIdToken().getJwtToken();

// Use token in API requests
const response = await fetch(`${API_ENDPOINT}/audits`, {
  headers: {
    'Authorization': `Bearer ${idToken}`
  }
});
```

### Token Expiration

- **Access Token**: 30 minutes
- **ID Token**: 30 minutes
- **Refresh Token**: 30 days

Tokens are automatically refreshed by AWS Amplify when they expire.

### User Groups

- **LoanOfficers**: Can upload documents and view audit results (PII masked)
- **Administrators**: Full system access including unmasked PII

---

## CORS Configuration

CORS is enabled for all endpoints to allow frontend access.

**Allowed Headers**:
- `Content-Type`
- `X-Amz-Date`
- `Authorization`
- `X-Api-Key`
- `X-Amz-Security-Token`

**Allowed Methods**:
- `GET`
- `POST`
- `PUT`
- `DELETE`
- `OPTIONS`

**Allowed Origins**:
- `*` (all origins) - Update to specific domain in production

### Updating CORS for Specific Domain

```bash
# Update CORS to allow only your frontend domain
aws apigateway update-integration-response \
  --rest-api-id ${API_ID} \
  --resource-id ${RESOURCE_ID} \
  --http-method OPTIONS \
  --status-code 200 \
  --patch-operations op=replace,path=/responseParameters/method.response.header.Access-Control-Allow-Origin,value='"https://your-domain.com"'
```

---

## Security Features

### 1. TLS 1.2+ Enforcement
All API traffic is encrypted using TLS 1.2 or higher.

### 2. Cognito Authentication
JWT tokens are validated by Cognito Authorizer before reaching Lambda.

### 3. PII Masking
Sensitive data is masked based on user role:
- SSN: `***-**-1234` (last 4 digits visible)
- DOB: `****-**-**` (fully masked)
- Account numbers: `****1234` (last 4 digits visible)

### 4. Pre-signed URL Expiration
- Upload URLs: 15 minutes
- View URLs: 1 hour

### 5. Request Logging
All API requests are logged to CloudWatch with:
- User ID and email
- User groups (roles)
- Source IP address
- Request method and path
- Response status code
- Timestamp

**PII Redaction**: PII is automatically redacted from CloudWatch logs.

---

## Monitoring and Logging

### CloudWatch Logs

**Log Group**: `/aws/lambda/AuditFlowAPIHandler`

**Retention**: 1 year (365 days)

**Log Format**:
```
API Request | RequestID: abc-123 | User: user-uuid (user@example.com) | Groups: ['LoanOfficers'] | IP: 192.168.1.1 | Method: GET | Path: /audits
API Response | RequestID: abc-123 | User: user-uuid | Status: 200 | Method: GET | Path: /audits
```

### Viewing Logs

```bash
# Tail logs in real-time
aws logs tail /aws/lambda/AuditFlowAPIHandler --follow --region ap-south-1

# Filter logs by user
aws logs filter-log-events \
  --log-group-name /aws/lambda/AuditFlowAPIHandler \
  --filter-pattern "User: user-uuid" \
  --region ap-south-1

# Filter error logs
aws logs filter-log-events \
  --log-group-name /aws/lambda/AuditFlowAPIHandler \
  --filter-pattern "ERROR" \
  --region ap-south-1
```

### CloudWatch Metrics

**Namespace**: `AWS/ApiGateway`

**Key Metrics**:
- `Count`: Total number of API requests
- `4XXError`: Client error count
- `5XXError`: Server error count
- `Latency`: Request latency (ms)
- `IntegrationLatency`: Lambda execution time (ms)

### Creating Alarms

```bash
# Alarm for high error rate
aws cloudwatch put-metric-alarm \
  --alarm-name AuditFlowAPI-HighErrorRate \
  --alarm-description "Alert when API error rate exceeds 5%" \
  --metric-name 5XXError \
  --namespace AWS/ApiGateway \
  --statistic Sum \
  --period 300 \
  --evaluation-periods 1 \
  --threshold 5 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=ApiName,Value=AuditFlowAPI
```

---

## Deployment

### Prerequisites

1. Cognito User Pool configured
2. S3 bucket created
3. DynamoDB tables created
4. KMS key configured

### Deployment Steps

```bash
# 1. Deploy API Handler Lambda
./infrastructure/deploy_api_handler.sh

# 2. Set up API Gateway
./infrastructure/api_gateway_setup.sh

# 3. Test API endpoints
curl -H "Authorization: Bearer ${ID_TOKEN}" \
  https://${API_ID}.execute-api.${REGION}.amazonaws.com/prod/audits
```

### Environment Variables

Add to frontend `.env` file:
```
VITE_API_ENDPOINT=https://{api-id}.execute-api.{region}.amazonaws.com/prod
VITE_USER_POOL_ID={user-pool-id}
VITE_USER_POOL_CLIENT_ID={client-id}
VITE_IDENTITY_POOL_ID={identity-pool-id}
VITE_AWS_REGION={region}
```

---

## Testing

### Manual Testing with cURL

```bash
# Get ID token
ID_TOKEN=$(aws cognito-idp initiate-auth \
  --auth-flow USER_PASSWORD_AUTH \
  --client-id ${CLIENT_ID} \
  --auth-parameters USERNAME=${EMAIL},PASSWORD=${PASSWORD} \
  --query 'AuthenticationResult.IdToken' \
  --output text)

# Test document upload endpoint
curl -X POST https://${API_ID}.execute-api.${REGION}.amazonaws.com/prod/documents \
  -H "Authorization: Bearer ${ID_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "file_name": "test.pdf",
    "content_type": "application/pdf",
    "file_size": 1048576,
    "loan_application_id": "loan-test"
  }'

# Test list audits endpoint
curl https://${API_ID}.execute-api.${REGION}.amazonaws.com/prod/audits \
  -H "Authorization: Bearer ${ID_TOKEN}"

# Test get audit details
curl https://${API_ID}.execute-api.${REGION}.amazonaws.com/prod/audits/${AUDIT_ID} \
  -H "Authorization: Bearer ${ID_TOKEN}"

# Test document viewer
curl https://${API_ID}.execute-api.${REGION}.amazonaws.com/prod/documents/${DOC_ID}/view?loan_application_id=loan-test \
  -H "Authorization: Bearer ${ID_TOKEN}"
```

### Integration Testing

See `backend/tests/integration/test_api_gateway.py` for automated integration tests.

---

## Troubleshooting

### Common Issues

#### 1. 401 Unauthorized
**Cause**: Missing or invalid authentication token

**Solution**:
- Verify token is included in `Authorization` header
- Check token hasn't expired (30-minute lifetime)
- Ensure Cognito User Pool ID matches authorizer configuration

#### 2. 403 Forbidden
**Cause**: User doesn't have permission to access resource

**Solution**:
- Verify user is in correct Cognito group (LoanOfficers or Administrators)
- Check IAM role policies for Identity Pool

#### 3. 500 Internal Server Error
**Cause**: Lambda execution error

**Solution**:
- Check CloudWatch Logs for error details
- Verify environment variables are set correctly
- Ensure Lambda has necessary IAM permissions

#### 4. CORS Errors
**Cause**: CORS not configured correctly

**Solution**:
- Verify OPTIONS method is configured for all resources
- Check `Access-Control-Allow-Origin` header in responses
- Update CORS configuration to allow frontend domain

---

## Performance Optimization

### Caching

Enable API Gateway caching for GET endpoints:

```bash
aws apigateway update-stage \
  --rest-api-id ${API_ID} \
  --stage-name prod \
  --patch-operations \
    op=replace,path=/cacheClusterEnabled,value=true \
    op=replace,path=/cacheClusterSize,value=0.5
```

### Lambda Provisioned Concurrency

For consistent performance, configure provisioned concurrency:

```bash
aws lambda put-provisioned-concurrency-config \
  --function-name AuditFlowAPIHandler \
  --provisioned-concurrent-executions 5 \
  --qualifier prod
```

---

## Cost Optimization

### API Gateway Pricing
- $3.50 per million API calls
- $0.09 per GB data transfer out

### Lambda Pricing
- $0.20 per 1 million requests
- $0.0000166667 per GB-second

### Estimated Monthly Cost
- 1 million API calls: ~$3.50
- Lambda execution (512 MB, 30s avg): ~$10
- **Total**: ~$13.50/month for 1 million requests

---

## Security Best Practices

1. **Use specific CORS origins** in production (not `*`)
2. **Enable AWS WAF** for DDoS protection
3. **Implement rate limiting** using API Gateway usage plans
4. **Rotate KMS keys** annually
5. **Enable CloudTrail** for API Gateway API calls
6. **Use VPC endpoints** for private API access
7. **Implement request validation** at API Gateway level
8. **Enable X-Ray tracing** for performance monitoring

---

## References

- [AWS API Gateway Documentation](https://docs.aws.amazon.com/apigateway/)
- [Cognito User Pool Authorizers](https://docs.aws.amazon.com/apigateway/latest/developerguide/apigateway-integrate-with-cognito.html)
- [Pre-signed URLs](https://docs.aws.amazon.com/AmazonS3/latest/userguide/PresignedUrlUploadObject.html)
- [API Gateway CORS](https://docs.aws.amazon.com/apigateway/latest/developerguide/how-to-cors.html)
