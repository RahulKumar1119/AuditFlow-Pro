# DynamoDB Table Creation Guide

## Quick Start

To create the DynamoDB tables for AuditFlow-Pro:

```bash
cd infrastructure
./create_dynamodb_tables.sh
```

This script will:
1. Create `AuditFlow-Documents` table with 2 GSIs
2. Create `AuditFlow-AuditRecords` table with 3 GSIs
3. Enable KMS encryption at rest
4. Enable TTL for automatic deletion
5. Enable Point-in-Time Recovery for backups

## Prerequisites

- AWS CLI installed and configured
- AWS credentials with DynamoDB permissions
- Region set (default: ap-south-1, override with `AWS_REGION` env var)

## Tables Created

### 1. AuditFlow-Documents
**Purpose**: Store document metadata and extracted data

**Primary Key**: `document_id` (String)

**Global Secondary Indexes**:
- `loan_application_id-upload_timestamp-index` - Query documents by loan application
- `processing_status-upload_timestamp-index` - Query documents by status

**Features**:
- KMS encryption at rest
- TTL enabled (90-day archival, 7-year deletion)
- Point-in-Time Recovery (35 days)
- PAY_PER_REQUEST billing

### 2. AuditFlow-AuditRecords
**Purpose**: Store complete audit results with risk scores

**Primary Key**: `audit_record_id` (String)

**Global Secondary Indexes**:
- `loan_application_id-audit_timestamp-index` - Query audits by loan application
- `risk_score-audit_timestamp-index` - Query by status and risk score (high-risk queue)
- `status-audit_timestamp-index` - Query audits by status

**Features**:
- KMS encryption at rest
- TTL enabled (7-year retention)
- Point-in-Time Recovery (35 days)
- PAY_PER_REQUEST billing

## Verification

After running the script, verify tables were created:

```bash
# List all tables
aws dynamodb list-tables --region ap-south-1

# Describe Documents table
aws dynamodb describe-table --table-name AuditFlow-Documents --region ap-south-1

# Describe Audit Records table
aws dynamodb describe-table --table-name AuditFlow-AuditRecords --region ap-south-1
```

## Configuration

The script uses environment variables:
- `AWS_REGION` - AWS region (default: ap-south-1)

Example with custom region:
```bash
AWS_REGION=ap-south-1 ./create_dynamodb_tables.sh
```

## Files

- `create_dynamodb_tables.sh` - Main table creation script
- `dynamodb_config.sh` - Additional configuration (encryption, TTL, PITR)
- `dynamodb_schemas.json` - Complete schema documentation
- `DYNAMODB_SCHEMA.md` - Detailed schema reference
- `../backend/shared/dynamodb_schemas.py` - Programmatic schema definitions

## Troubleshooting

### Table Already Exists
The script checks if tables exist and skips creation. To recreate:
```bash
# Delete existing tables
aws dynamodb delete-table --table-name AuditFlow-Documents --region ap-south-1
aws dynamodb delete-table --table-name AuditFlow-AuditRecords --region ap-south-1

# Wait for deletion
aws dynamodb wait table-not-exists --table-name AuditFlow-Documents --region ap-south-1
aws dynamodb wait table-not-exists --table-name AuditFlow-AuditRecords --region ap-south-1

# Run creation script again
./create_dynamodb_tables.sh
```

### Encryption Configuration Fails
If encryption configuration fails with "table not ready", wait a few seconds and run:
```bash
./dynamodb_config.sh
```

### Permission Errors
Ensure your AWS credentials have these permissions:
- `dynamodb:CreateTable`
- `dynamodb:DescribeTable`
- `dynamodb:UpdateTable`
- `dynamodb:UpdateTimeToLive`
- `dynamodb:UpdateContinuousBackups`
- `kms:CreateKey` (if creating custom KMS key)

## Next Steps

After creating tables:
1. Deploy Lambda functions that use these tables
2. Configure IAM policies for Lambda access
3. Set up CloudWatch alarms for monitoring
4. Test with sample data

## Requirements Satisfied

This implementation satisfies the following requirements:
- **12.1**: Audit results stored in DynamoDB
- **12.3**: Indexed by loan application ID and timestamp
- **12.4**: Queryable by date range, risk score, and document type
- **12.6**: Encryption at rest using KMS
- **16.4**: DynamoDB encryption enabled

## Design References

See `DYNAMODB_SCHEMA.md` for:
- Complete attribute descriptions
- Query patterns and examples
- Capacity planning
- Security configuration
- Monitoring setup
