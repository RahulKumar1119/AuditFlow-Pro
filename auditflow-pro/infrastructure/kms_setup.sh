#!/bin/bash
# infrastructure/kms_setup.sh
# Configure AWS KMS encryption keys for AuditFlow-Pro

set -e

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION="ap-south-1"

echo "Setting up KMS encryption keys for AuditFlow-Pro"
echo "=================================================="

# Check if KMS key alias already exists
if aws kms describe-key --key-id alias/auditflow-s3-encryption 2>/dev/null; then
    echo "KMS key alias/auditflow-s3-encryption already exists"
    KMS_KEY_ID=$(aws kms describe-key --key-id alias/auditflow-s3-encryption --query 'KeyMetadata.KeyId' --output text)
    echo "Using existing KMS Key: $KMS_KEY_ID"
else
    # Create KMS Key for S3 Encryption
    echo "Creating KMS key for S3 encryption..."
    
    # Create policy file
    cat > /tmp/s3-kms-policy.json << EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "Enable IAM User Permissions",
            "Effect": "Allow",
            "Principal": {
                "AWS": "arn:aws:iam::${ACCOUNT_ID}:root"
            },
            "Action": "kms:*",
            "Resource": "*"
        },
        {
            "Sid": "Allow S3 to use the key",
            "Effect": "Allow",
            "Principal": {
                "Service": "s3.amazonaws.com"
            },
            "Action": [
                "kms:Decrypt",
                "kms:GenerateDataKey",
                "kms:DescribeKey"
            ],
            "Resource": "*"
        },
        {
            "Sid": "Allow Lambda to use the key",
            "Effect": "Allow",
            "Principal": {
                "AWS": "arn:aws:iam::${ACCOUNT_ID}:role/AuditFlowLambdaExecutionRole"
            },
            "Action": [
                "kms:Decrypt",
                "kms:GenerateDataKey",
                "kms:DescribeKey"
            ],
            "Resource": "*"
        },
        {
            "Sid": "Allow CloudWatch Logs",
            "Effect": "Allow",
            "Principal": {
                "Service": "logs.${REGION}.amazonaws.com"
            },
            "Action": [
                "kms:Encrypt",
                "kms:Decrypt",
                "kms:ReEncrypt*",
                "kms:GenerateDataKey*",
                "kms:CreateGrant",
                "kms:DescribeKey"
            ],
            "Resource": "*",
            "Condition": {
                "ArnLike": {
                    "kms:EncryptionContext:aws:logs:arn": "arn:aws:logs:${REGION}:${ACCOUNT_ID}:*"
                }
            }
        }
    ]
}
EOF

    KMS_KEY_ID=$(aws kms create-key \
        --description "AuditFlow-Pro S3 Document Encryption Key - Created $(date +%Y-%m-%d)" \
        --key-usage ENCRYPT_DECRYPT \
        --origin AWS_KMS \
        --policy file:///tmp/s3-kms-policy.json \
        --query 'KeyMetadata.KeyId' \
        --output text)
    
    rm -f /tmp/s3-kms-policy.json

    echo "✓ KMS Key created: $KMS_KEY_ID"

    # Create alias for the KMS key
    aws kms create-alias \
        --alias-name alias/auditflow-s3-encryption \
        --target-key-id $KMS_KEY_ID

    echo "✓ KMS Key alias created: alias/auditflow-s3-encryption"
fi

# Enable automatic key rotation (annual rotation)
echo "Enabling automatic key rotation..."
aws kms enable-key-rotation --key-id $KMS_KEY_ID
echo "✓ Automatic key rotation enabled (annual)"

# Add tags to the key
echo "Adding tags to KMS key..."
aws kms tag-resource \
    --key-id $KMS_KEY_ID \
    --tags \
        TagKey=Project,TagValue=AuditFlow-Pro \
        TagKey=Purpose,TagValue=S3-Document-Encryption \
        TagKey=Environment,TagValue=Production

echo "✓ Tags added"

# Create KMS key for DynamoDB encryption (if needed)
if aws kms describe-key --key-id alias/auditflow-dynamodb-encryption 2>/dev/null; then
    echo "KMS key alias/auditflow-dynamodb-encryption already exists"
    DYNAMODB_KEY_ID=$(aws kms describe-key --key-id alias/auditflow-dynamodb-encryption --query 'KeyMetadata.KeyId' --output text)
    echo "Using existing DynamoDB KMS Key: $DYNAMODB_KEY_ID"
else
    echo "Creating KMS key for DynamoDB encryption..."
    
    # Create policy file
    cat > /tmp/dynamodb-kms-policy.json << EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "Enable IAM User Permissions",
            "Effect": "Allow",
            "Principal": {
                "AWS": "arn:aws:iam::${ACCOUNT_ID}:root"
            },
            "Action": "kms:*",
            "Resource": "*"
        },
        {
            "Sid": "Allow DynamoDB to use the key",
            "Effect": "Allow",
            "Principal": {
                "Service": "dynamodb.amazonaws.com"
            },
            "Action": [
                "kms:Decrypt",
                "kms:GenerateDataKey",
                "kms:CreateGrant",
                "kms:DescribeKey"
            ],
            "Resource": "*"
        }
    ]
}
EOF

    DYNAMODB_KEY_ID=$(aws kms create-key \
        --description "AuditFlow-Pro DynamoDB Encryption Key - Created $(date +%Y-%m-%d)" \
        --key-usage ENCRYPT_DECRYPT \
        --origin AWS_KMS \
        --policy file:///tmp/dynamodb-kms-policy.json \
        --query 'KeyMetadata.KeyId' \
        --output text)
    
    rm -f /tmp/dynamodb-kms-policy.json

    echo "✓ DynamoDB KMS Key created: $DYNAMODB_KEY_ID"

    # Create alias for the DynamoDB KMS key
    aws kms create-alias \
        --alias-name alias/auditflow-dynamodb-encryption \
        --target-key-id $DYNAMODB_KEY_ID

    echo "✓ DynamoDB KMS Key alias created: alias/auditflow-dynamodb-encryption"

    # Enable automatic key rotation
    aws kms enable-key-rotation --key-id $DYNAMODB_KEY_ID
    echo "✓ Automatic key rotation enabled for DynamoDB key"

    # Add tags
    aws kms tag-resource \
        --key-id $DYNAMODB_KEY_ID \
        --tags \
            TagKey=Project,TagValue=AuditFlow-Pro \
            TagKey=Purpose,TagValue=DynamoDB-Encryption \
            TagKey=Environment,TagValue=Production
fi

# ==========================================
# Enable CloudWatch Logging for KMS Key Usage
# ==========================================
echo ""
echo "Configuring CloudWatch logging for KMS key operations..."

# Create CloudWatch log group for KMS events
LOG_GROUP_NAME="/aws/kms/auditflow-encryption"
aws logs create-log-group --log-group-name "$LOG_GROUP_NAME" --region "$REGION" 2>/dev/null || echo "Log group already exists"

# Set retention policy (1 year)
aws logs put-retention-policy \
    --log-group-name "$LOG_GROUP_NAME" \
    --retention-in-days 365 \
    --region "$REGION" 2>/dev/null || echo "Retention policy already set"

echo "✓ CloudWatch log group created: $LOG_GROUP_NAME"
echo "✓ Log retention: 365 days (1 year)"

# Note: KMS key usage is automatically logged to CloudTrail
# CloudTrail must be enabled separately to capture KMS events
echo ""
echo "Note: KMS key operations are logged to AWS CloudTrail"
echo "Ensure CloudTrail is enabled to track encryption/decryption events"

echo ""
echo "=================================================="
echo "KMS setup complete!"
echo "S3 Encryption Key: $KMS_KEY_ID"
echo "S3 Key Alias: alias/auditflow-s3-encryption"
echo "DynamoDB Encryption Key: $DYNAMODB_KEY_ID"
echo "DynamoDB Key Alias: alias/auditflow-dynamodb-encryption"
echo "Key Rotation: Enabled (Annual)"
echo "CloudWatch Logging: Configured"
echo "=================================================="

# Export key IDs for use in other scripts
echo "export AUDITFLOW_S3_KMS_KEY_ID=$KMS_KEY_ID" > /tmp/auditflow_kms_keys.env
echo "export AUDITFLOW_DYNAMODB_KMS_KEY_ID=$DYNAMODB_KEY_ID" >> /tmp/auditflow_kms_keys.env
echo ""
echo "Key IDs exported to /tmp/auditflow_kms_keys.env"
