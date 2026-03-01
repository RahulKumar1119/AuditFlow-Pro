# DynamoDB Table Schemas for AuditFlow-Pro

This document describes the DynamoDB table schemas, indexes, and design decisions for the AuditFlow-Pro loan document auditor system.

## Overview

The system uses two main DynamoDB tables:
1. **AuditFlow-Documents** - Stores document metadata, classification results, and extracted data
2. **AuditFlow-AuditRecords** - Stores complete audit results including risk scores and inconsistencies

Both tables use **PAY_PER_REQUEST** billing mode for automatic scaling and cost optimization with unpredictable workloads.

## Table 1: AuditFlow-Documents

### Purpose
Stores metadata and extracted data for each uploaded document. Tracks processing status and enables querying by loan application or status.

### Primary Key
- **Partition Key**: `document_id` (String) - UUID for even distribution across partitions

### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| document_id | String | Primary key - unique document identifier (UUID) |
| loan_application_id | String | Groups documents by loan application |
| upload_timestamp | String | ISO 8601 timestamp of document upload |
| processing_status | String | PENDING, PROCESSING, COMPLETED, FAILED |
| s3_bucket | String | S3 bucket containing the document |
| s3_key | String | S3 object key for the document |
| uploaded_by | String | User email who uploaded the document |
| file_name | String | Original filename |
| file_size_bytes | Number | File size in bytes |
| file_format | String | PDF, JPEG, PNG, TIFF |
| checksum | String | SHA-256 checksum for integrity verification |
| document_type | String | W2, BANK_STATEMENT, TAX_FORM, DRIVERS_LICENSE, ID_DOCUMENT |
| classification_confidence | Number | Confidence score for classification (0-1) |
| extracted_data | Map | Nested map of extracted fields with confidence scores |
| extraction_timestamp | String | ISO 8601 timestamp when extraction completed |
| page_count | Number | Number of pages in the document |
| low_confidence_fields | List | Field names with confidence < 80% |
| requires_manual_review | Boolean | Flag for manual review requirement |
| pii_detected | List | PII types detected (ssn, dob, account_number, etc.) |
| encryption_key_id | String | KMS key ID used for encryption |
| ttl | Number | Unix timestamp for automatic deletion |

### Global Secondary Indexes (GSI)

#### GSI 1: loan_application_id-upload_timestamp-index
- **Partition Key**: loan_application_id
- **Sort Key**: upload_timestamp
- **Projection**: ALL
- **Use Case**: Query all documents for a specific loan application, sorted by upload time
- **Example Query**: Get all documents for loan application "abc-123" ordered by upload time

#### GSI 2: processing_status-upload_timestamp-index
- **Partition Key**: processing_status
- **Sort Key**: upload_timestamp
- **Projection**: ALL
- **Use Case**: Query documents by processing status for audit queue display
- **Example Query**: Get all "PENDING" documents ordered by upload time

### Encryption
- **At Rest**: KMS encryption enabled (SSE-KMS)
- **In Transit**: TLS 1.2+ for all API calls
- **Field-Level**: PII fields encrypted in application code before storage

### TTL Configuration
- **Enabled**: Yes
- **Attribute**: ttl
- **Policy**: Documents archived to S3 Glacier after 90 days, deleted after 7 years

### Point-in-Time Recovery
- **Enabled**: Yes
- **Retention**: 35 days of continuous backups

---

## Table 2: AuditFlow-AuditRecords

### Purpose
Stores complete audit results for loan applications including risk scores, inconsistencies, golden records, and review status.

### Primary Key
- **Partition Key**: `audit_record_id` (String) - UUID for even distribution

### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| audit_record_id | String | Primary key - unique audit record identifier (UUID) |
| loan_application_id | String | Links audit to loan application |
| audit_timestamp | String | ISO 8601 timestamp when audit completed |
| risk_score | Number | Calculated risk score (0-100) |
| status | String | COMPLETED, IN_PROGRESS, FAILED |
| applicant_name | String | Name of loan applicant from golden record |
| processing_duration_seconds | Number | Total time taken to complete audit |
| documents | List | List of document references included in audit |
| golden_record | Map | Consolidated authoritative applicant data |
| inconsistencies | List | Detected inconsistencies with severity levels |
| risk_level | String | LOW, MEDIUM, HIGH, CRITICAL |
| risk_factors | List | Factors contributing to risk score |
| alerts_triggered | List | Alerts generated during audit |
| reviewed_by | String | User email who reviewed the audit (optional) |
| review_timestamp | String | ISO 8601 timestamp of review (optional) |
| review_notes | String | Notes added during manual review (optional) |
| archived | Boolean | Flag indicating if archived to Glacier |
| archive_timestamp | String | ISO 8601 timestamp when archived (optional) |
| ttl | Number | Unix timestamp for automatic deletion (7 years) |

### Global Secondary Indexes (GSI)

#### GSI 1: loan_application_id-audit_timestamp-index
- **Partition Key**: loan_application_id
- **Sort Key**: audit_timestamp
- **Projection**: ALL
- **Use Case**: Query all audits for a specific loan application, sorted by time
- **Example Query**: Get audit history for loan application "abc-123"

#### GSI 2: risk_score-audit_timestamp-index
- **Partition Key**: status
- **Sort Key**: risk_score
- **Projection**: ALL
- **Use Case**: Query audits by status and filter/sort by risk score (high-risk queue)
- **Example Query**: Get all "COMPLETED" audits with risk_score > 50, sorted by score

#### GSI 3: status-audit_timestamp-index
- **Partition Key**: status
- **Sort Key**: audit_timestamp
- **Projection**: ALL
- **Use Case**: Query audits by status, sorted by timestamp
- **Example Query**: Get all "IN_PROGRESS" audits ordered by time

### Encryption
- **At Rest**: KMS encryption enabled (SSE-KMS)
- **In Transit**: TLS 1.2+ for all API calls
- **Field-Level**: PII fields in golden_record encrypted in application code

### TTL Configuration
- **Enabled**: Yes
- **Attribute**: ttl
- **Policy**: Records retained for 7 years, then automatically deleted for compliance

### Point-in-Time Recovery
- **Enabled**: Yes
- **Retention**: 35 days of continuous backups

---

## Design Decisions

### Partition Key Design
Both tables use UUID-based partition keys to ensure:
- Even distribution of data across partitions
- No hot partitions from sequential IDs
- High write throughput without throttling

### GSI Design Philosophy
GSIs are designed to support common query patterns:
- **By Loan Application**: Group all documents/audits for a loan
- **By Status**: Filter by processing/audit status
- **By Risk Score**: Identify high-risk applications quickly
- **By Timestamp**: Sort results chronologically

All GSIs use **ALL** projection to avoid additional reads from the base table.

### Billing Mode: PAY_PER_REQUEST
Chosen for:
- Unpredictable workload patterns (loan submissions vary)
- Automatic scaling without capacity planning
- Cost optimization (pay only for actual usage)
- Supports up to 1000 requests/second per requirement 19.5

### Encryption Strategy
Three layers of encryption:
1. **Server-Side (KMS)**: All data encrypted at rest in DynamoDB
2. **Field-Level**: PII fields encrypted in application before storage
3. **In-Transit (TLS)**: All API calls use TLS 1.2+

### TTL for Compliance
Automatic deletion using DynamoDB TTL:
- **Documents**: Archived to Glacier after 90 days, deleted after 7 years
- **Audit Records**: Retained for 7 years, then deleted
- Meets compliance requirement 12.5 and 25.1-25.5

### Point-in-Time Recovery
Enabled for disaster recovery:
- 35 days of continuous backups
- Restore to any point in time
- Protection against accidental deletion

---

## Query Patterns

### Pattern 1: Get All Documents for a Loan Application
```python
response = dynamodb.query(
    TableName='AuditFlow-Documents',
    IndexName='loan_application_id-upload_timestamp-index',
    KeyConditionExpression='loan_application_id = :loan_id',
    ExpressionAttributeValues={':loan_id': 'abc-123'}
)
```

### Pattern 2: Get Pending Documents (Audit Queue)
```python
response = dynamodb.query(
    TableName='AuditFlow-Documents',
    IndexName='processing_status-upload_timestamp-index',
    KeyConditionExpression='processing_status = :status',
    ExpressionAttributeValues={':status': 'PENDING'}
)
```

### Pattern 3: Get High-Risk Completed Audits
```python
response = dynamodb.query(
    TableName='AuditFlow-AuditRecords',
    IndexName='risk_score-audit_timestamp-index',
    KeyConditionExpression='status = :status AND risk_score > :threshold',
    ExpressionAttributeValues={
        ':status': 'COMPLETED',
        ':threshold': 50
    }
)
```

### Pattern 4: Get Audit History for Loan Application
```python
response = dynamodb.query(
    TableName='AuditFlow-AuditRecords',
    IndexName='loan_application_id-audit_timestamp-index',
    KeyConditionExpression='loan_application_id = :loan_id',
    ExpressionAttributeValues={':loan_id': 'abc-123'},
    ScanIndexForward=False  # Most recent first
)
```

---

## Capacity Planning

### On-Demand Billing
- **Read Capacity**: Automatically scales to handle load
- **Write Capacity**: Automatically scales to handle load
- **Target**: Support 1000 requests/second (Requirement 19.5)
- **Burst**: Can handle temporary spikes without throttling

### Cost Estimation (Approximate)
- **Write**: $1.25 per million write request units
- **Read**: $0.25 per million read request units
- **Storage**: $0.25 per GB-month
- **Typical Monthly Cost**: $50-200 for moderate usage (1000 audits/month)

---

## Deployment

### Create Tables
```bash
cd infrastructure
./create_dynamodb_tables.sh
```

### Configure Encryption
```bash
./dynamodb_config.sh
```

### Verify Tables
```bash
aws dynamodb list-tables --region ap-south-1
aws dynamodb describe-table --table-name AuditFlow-Documents --region ap-south-1
aws dynamodb describe-table --table-name AuditFlow-AuditRecords --region ap-south-1
```

---

## Monitoring

### CloudWatch Metrics
- **ConsumedReadCapacityUnits**: Monitor read usage
- **ConsumedWriteCapacityUnits**: Monitor write usage
- **UserErrors**: Track client-side errors (validation, throttling)
- **SystemErrors**: Track server-side errors

### Alarms
Set up CloudWatch alarms for:
- High error rates (> 5% over 5 minutes)
- Throttling events (should be rare with on-demand)
- Storage size approaching limits

---

## Security

### IAM Policies
Lambda functions require:
- `dynamodb:PutItem` - Write documents and audit records
- `dynamodb:GetItem` - Read specific items
- `dynamodb:Query` - Query using GSIs
- `dynamodb:UpdateItem` - Update processing status
- `kms:Decrypt` - Decrypt encrypted data
- `kms:Encrypt` - Encrypt data before writing

### Access Control
- **Least Privilege**: Each Lambda has minimal required permissions
- **No Cross-Account**: Access denied by default
- **Audit Logging**: All access logged to CloudWatch

---

## Maintenance

### Backup Strategy
1. **Point-in-Time Recovery**: Enabled (35 days)
2. **On-Demand Backups**: Create before major changes
3. **Cross-Region Replication**: Consider for disaster recovery

### Archival Process
1. Documents older than 90 days: Move to S3 Glacier
2. Audit records older than 7 years: Automatically deleted via TTL
3. Maintain index in DynamoDB for archived records

---

## References

- **Requirements**: 12.1, 12.3, 12.4, 12.6, 16.4
- **Design Document**: Section "Data Models"
- **AWS Documentation**: [DynamoDB Best Practices](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/best-practices.html)
