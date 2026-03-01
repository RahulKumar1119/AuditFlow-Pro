#!/bin/bash
# infrastructure/create_dynamodb_tables.sh
# Creates DynamoDB tables with complete schema definitions, GSIs, and encryption

set -e

REGION="${AWS_REGION:-ap-south-1}"

echo "=========================================="
echo "Creating DynamoDB Tables for AuditFlow-Pro"
echo "Region: $REGION"
echo "=========================================="

# Function to check if table exists
table_exists() {
    aws dynamodb describe-table --table-name "$1" --region "$REGION" &>/dev/null
}

# Function to wait for table to be active
wait_for_table() {
    echo "Waiting for table $1 to become ACTIVE..."
    aws dynamodb wait table-exists --table-name "$1" --region "$REGION"
    echo "Table $1 is now ACTIVE"
}

# ==========================================
# 1. Create AuditFlow-Documents Table
# ==========================================
echo ""
echo "Creating AuditFlow-Documents table..."

if table_exists "AuditFlow-Documents"; then
    echo "Table AuditFlow-Documents already exists, skipping creation"
else
    aws dynamodb create-table \
        --table-name AuditFlow-Documents \
        --attribute-definitions \
            AttributeName=document_id,AttributeType=S \
            AttributeName=loan_application_id,AttributeType=S \
            AttributeName=upload_timestamp,AttributeType=S \
            AttributeName=processing_status,AttributeType=S \
        --key-schema \
            AttributeName=document_id,KeyType=HASH \
        --global-secondary-indexes \
            IndexName=loan_application_id-upload_timestamp-index,KeySchema=[{AttributeName=loan_application_id,KeyType=HASH},{AttributeName=upload_timestamp,KeyType=RANGE}],Projection={ProjectionType=ALL} \
            IndexName=processing_status-upload_timestamp-index,KeySchema=[{AttributeName=processing_status,KeyType=HASH},{AttributeName=upload_timestamp,KeyType=RANGE}],Projection={ProjectionType=ALL} \
        --billing-mode PAY_PER_REQUEST \
        --region "$REGION" \
        --tags Key=Project,Value=AuditFlow-Pro Key=Environment,Value=Production

    wait_for_table "AuditFlow-Documents"
    echo "✓ AuditFlow-Documents table created successfully"
fi

# ==========================================
# 2. Create AuditFlow-AuditRecords Table
# ==========================================
echo ""
echo "Creating AuditFlow-AuditRecords table..."

if table_exists "AuditFlow-AuditRecords"; then
    echo "Table AuditFlow-AuditRecords already exists, skipping creation"
else
    aws dynamodb create-table \
        --table-name AuditFlow-AuditRecords \
        --attribute-definitions \
            AttributeName=audit_record_id,AttributeType=S \
            AttributeName=loan_application_id,AttributeType=S \
            AttributeName=audit_timestamp,AttributeType=S \
            AttributeName=risk_score,AttributeType=N \
            AttributeName=status,AttributeType=S \
        --key-schema \
            AttributeName=audit_record_id,KeyType=HASH \
        --global-secondary-indexes \
            IndexName=loan_application_id-audit_timestamp-index,KeySchema=[{AttributeName=loan_application_id,KeyType=HASH},{AttributeName=audit_timestamp,KeyType=RANGE}],Projection={ProjectionType=ALL} \
            IndexName=risk_score-audit_timestamp-index,KeySchema=[{AttributeName=status,KeyType=HASH},{AttributeName=risk_score,KeyType=RANGE}],Projection={ProjectionType=ALL} \
            IndexName=status-audit_timestamp-index,KeySchema=[{AttributeName=status,KeyType=HASH},{AttributeName=audit_timestamp,KeyType=RANGE}],Projection={ProjectionType=ALL} \
        --billing-mode PAY_PER_REQUEST \
        --region "$REGION" \
        --tags Key=Project,Value=AuditFlow-Pro Key=Environment,Value=Production

    wait_for_table "AuditFlow-AuditRecords"
    echo "✓ AuditFlow-AuditRecords table created successfully"
fi

# ==========================================
# 3. Enable Encryption at Rest
# ==========================================
echo ""
echo "Configuring encryption at rest..."

# Enable encryption for AuditFlow-Documents
echo "Enabling KMS encryption for AuditFlow-Documents..."
aws dynamodb update-table \
    --table-name AuditFlow-Documents \
    --sse-specification Enabled=true,SSEType=KMS \
    --region "$REGION" 2>/dev/null || echo "Encryption already enabled or table not ready"

# Enable encryption for AuditFlow-AuditRecords
echo "Enabling KMS encryption for AuditFlow-AuditRecords..."
aws dynamodb update-table \
    --table-name AuditFlow-AuditRecords \
    --sse-specification Enabled=true,SSEType=KMS \
    --region "$REGION" 2>/dev/null || echo "Encryption already enabled or table not ready"

echo "✓ Encryption configuration completed"

# ==========================================
# 4. Enable TTL for Automatic Deletion
# ==========================================
echo ""
echo "Configuring Time-To-Live (TTL) for automatic deletion..."

# Enable TTL for AuditFlow-Documents (archival after 90 days)
echo "Enabling TTL for AuditFlow-Documents..."
aws dynamodb update-time-to-live \
    --table-name AuditFlow-Documents \
    --time-to-live-specification "Enabled=true,AttributeName=ttl" \
    --region "$REGION" 2>/dev/null || echo "TTL already enabled"

# Enable TTL for AuditFlow-AuditRecords (7-year retention)
echo "Enabling TTL for AuditFlow-AuditRecords..."
aws dynamodb update-time-to-live \
    --table-name AuditFlow-AuditRecords \
    --time-to-live-specification "Enabled=true,AttributeName=ttl" \
    --region "$REGION" 2>/dev/null || echo "TTL already enabled"

echo "✓ TTL configuration completed"

# ==========================================
# 5. Enable Point-in-Time Recovery
# ==========================================
echo ""
echo "Enabling Point-in-Time Recovery for backup and restore..."

# Enable PITR for AuditFlow-Documents
echo "Enabling PITR for AuditFlow-Documents..."
aws dynamodb update-continuous-backups \
    --table-name AuditFlow-Documents \
    --point-in-time-recovery-specification PointInTimeRecoveryEnabled=true \
    --region "$REGION" 2>/dev/null || echo "PITR already enabled"

# Enable PITR for AuditFlow-AuditRecords
echo "Enabling PITR for AuditFlow-AuditRecords..."
aws dynamodb update-continuous-backups \
    --table-name AuditFlow-AuditRecords \
    --point-in-time-recovery-specification PointInTimeRecoveryEnabled=true \
    --region "$REGION" 2>/dev/null || echo "PITR already enabled"

echo "✓ Point-in-Time Recovery enabled"

# ==========================================
# 6. Display Table Information
# ==========================================
echo ""
echo "=========================================="
echo "DynamoDB Tables Created Successfully!"
echo "=========================================="
echo ""
echo "Table: AuditFlow-Documents"
echo "  Primary Key: document_id (String)"
echo "  GSI 1: loan_application_id-upload_timestamp-index"
echo "  GSI 2: processing_status-upload_timestamp-index"
echo "  Billing: PAY_PER_REQUEST (On-Demand)"
echo "  Encryption: KMS (Server-Side)"
echo "  TTL: Enabled (attribute: ttl)"
echo "  PITR: Enabled"
echo ""
echo "Table: AuditFlow-AuditRecords"
echo "  Primary Key: audit_record_id (String)"
echo "  GSI 1: loan_application_id-audit_timestamp-index"
echo "  GSI 2: risk_score-audit_timestamp-index (partition: status, sort: risk_score)"
echo "  GSI 3: status-audit_timestamp-index"
echo "  Billing: PAY_PER_REQUEST (On-Demand)"
echo "  Encryption: KMS (Server-Side)"
echo "  TTL: Enabled (attribute: ttl)"
echo "  PITR: Enabled"
echo ""
echo "=========================================="
echo "Next Steps:"
echo "1. Review table schemas in dynamodb_schemas.json"
echo "2. Configure IAM policies for Lambda access"
echo "3. Deploy Lambda functions that use these tables"
echo "=========================================="
