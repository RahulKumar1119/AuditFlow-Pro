#!/bin/bash
# infrastructure/dynamodb_config.sh
# Configures DynamoDB tables with encryption and TTL

set -e

REGION="${AWS_REGION:-ap-south-1}"

echo "Configuring DynamoDB tables..."

# 1. Enable encryption at rest for AuditFlow-Documents table
echo "Enabling encryption for AuditFlow-Documents table..."
aws dynamodb update-table \
    --table-name AuditFlow-Documents \
    --sse-specification Enabled=true,SSEType=KMS \
    --region $REGION 2>/dev/null || echo "Encryption already enabled or table not ready"

# 2. Enable encryption at rest for AuditFlow-AuditRecords table
echo "Enabling encryption for AuditFlow-AuditRecords table..."
aws dynamodb update-table \
    --table-name AuditFlow-AuditRecords \
    --sse-specification Enabled=true,SSEType=KMS \
    --region $REGION 2>/dev/null || echo "Encryption already enabled or table not ready"

# 3. Enable TTL for AuditFlow-AuditRecords (7-year retention)
echo "Enabling TTL for AuditFlow-AuditRecords table..."
aws dynamodb update-time-to-live \
    --table-name AuditFlow-AuditRecords \
    --time-to-live-specification "Enabled=true,AttributeName=ttl" \
    --region $REGION

# 4. Enable Point-in-Time Recovery for both tables
echo "Enabling Point-in-Time Recovery for AuditFlow-Documents..."
aws dynamodb update-continuous-backups \
    --table-name AuditFlow-Documents \
    --point-in-time-recovery-specification PointInTimeRecoveryEnabled=true \
    --region $REGION

echo "Enabling Point-in-Time Recovery for AuditFlow-AuditRecords..."
aws dynamodb update-continuous-backups \
    --table-name AuditFlow-AuditRecords \
    --point-in-time-recovery-specification PointInTimeRecoveryEnabled=true \
    --region $REGION

echo "DynamoDB configuration completed successfully!"
