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
    KMS_KEY_ID=$(aws kms create-key \
        --description "AuditFlow-Pro S3 Document Encryption Key - Created $(date +%Y-%m-%d)" \
        --key-usage ENCRYPT_DECRYPT \
        --origin AWS_KMS \
        --key-policy '{
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "Enable IAM User Permissions",
                    "Effect": "Allow",
                    "Principal": {
                        "AWS": "arn:aws:iam::'$ACCOUNT_ID':root"
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
                        "AWS": "arn:aws:iam::'$ACCOUNT_ID':role/AuditFlowLambdaExecutionRole"
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
                        "Service": "logs.'$REGION'.amazonaws.com"
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
                            "kms:EncryptionContext:aws:logs:arn": "arn:aws:logs:'$REGION':'$ACCOUNT_ID':*"
                        }
                    }
                }
            ]
        }' \
        --query 'KeyMetadata.KeyId' \
        --output text)

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
    DYNAMODB_KEY_ID=$(aws kms create-key \
        --description "AuditFlow-Pro DynamoDB Encryption Key - Created $(date +%Y-%m-%d)" \
        --key-usage ENCRYPT_DECRYPT \
        --origin AWS_KMS \
        --key-policy '{
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "Enable IAM User Permissions",
                    "Effect": "Allow",
                    "Principal": {
                        "AWS": "arn:aws:iam::'$ACCOUNT_ID':root"
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
        }' \
        --query 'KeyMetadata.KeyId' \
        --output text)

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

echo ""
echo "=================================================="
echo "KMS setup complete!"
echo "S3 Encryption Key: $KMS_KEY_ID"
echo "S3 Key Alias: alias/auditflow-s3-encryption"
echo "DynamoDB Encryption Key: $DYNAMODB_KEY_ID"
echo "DynamoDB Key Alias: alias/auditflow-dynamodb-encryption"
echo "Key Rotation: Enabled (Annual)"
echo "=================================================="

# Export key IDs for use in other scripts
echo "export AUDITFLOW_S3_KMS_KEY_ID=$KMS_KEY_ID" > /tmp/auditflow_kms_keys.env
echo "export AUDITFLOW_DYNAMODB_KMS_KEY_ID=$DYNAMODB_KEY_ID" >> /tmp/auditflow_kms_keys.env
echo ""
echo "Key IDs exported to /tmp/auditflow_kms_keys.env"
