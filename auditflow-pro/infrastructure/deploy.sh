#!/bin/bash
# infrastructure/deploy.sh
# Main deployment script for AuditFlow-Pro infrastructure

set -e

REGION="ap-south-1"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
BUCKET_NAME="auditflow-documents-prod-${ACCOUNT_ID}"

echo "=========================================="
echo "Deploying AuditFlow-Pro Infrastructure"
echo "Region: $REGION"
echo "Account: $ACCOUNT_ID"
echo "=========================================="
echo ""

# Step 1: Set up KMS encryption keys
echo "Step 1: Setting up KMS encryption keys..."
if [ -f "infrastructure/kms_setup.sh" ]; then
    bash infrastructure/kms_setup.sh
    # Source the KMS key IDs
    if [ -f /tmp/auditflow_kms_keys.env ]; then
        source /tmp/auditflow_kms_keys.env
        echo "Using S3 KMS Key: $AUDITFLOW_S3_KMS_KEY_ID"
    fi
else
    echo "Warning: kms_setup.sh not found, will use inline KMS setup"
    # Inline KMS setup as fallback
    if aws kms describe-key --key-id alias/auditflow-s3-encryption 2>/dev/null; then
        AUDITFLOW_S3_KMS_KEY_ID=$(aws kms describe-key --key-id alias/auditflow-s3-encryption --query 'KeyMetadata.KeyId' --output text)
        echo "Using existing KMS Key: $AUDITFLOW_S3_KMS_KEY_ID"
    else
        echo "Creating new KMS key..."
        AUDITFLOW_S3_KMS_KEY_ID=$(aws kms create-key \
            --description "AuditFlow-Pro S3 Document Encryption Key" \
            --key-policy '{
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Sid": "Enable IAM User Permissions",
                        "Effect": "Allow",
                        "Principal": {"AWS": "arn:aws:iam::'$ACCOUNT_ID':root"},
                        "Action": "kms:*",
                        "Resource": "*"
                    },
                    {
                        "Sid": "Allow S3 to use the key",
                        "Effect": "Allow",
                        "Principal": {"Service": "s3.amazonaws.com"},
                        "Action": ["kms:Decrypt", "kms:GenerateDataKey"],
                        "Resource": "*"
                    }
                ]
            }' \
            --query 'KeyMetadata.KeyId' \
            --output text)
        
        aws kms create-alias \
            --alias-name alias/auditflow-s3-encryption \
            --target-key-id $AUDITFLOW_S3_KMS_KEY_ID
        
        echo "✓ KMS Key created: $AUDITFLOW_S3_KMS_KEY_ID"
    fi
fi

echo ""

# Step 2: Create S3 Bucket for Document Storage
echo "Step 2: Creating S3 Bucket: $BUCKET_NAME..."
if aws s3api head-bucket --bucket $BUCKET_NAME 2>/dev/null; then
    echo "Bucket $BUCKET_NAME already exists"
else
    aws s3api create-bucket \
        --bucket $BUCKET_NAME \
        --region $REGION \
        --create-bucket-configuration LocationConstraint=$REGION
    echo "✓ Bucket created"
fi

# Enable S3 Server-Side Encryption with KMS
if [ -n "$AUDITFLOW_S3_KMS_KEY_ID" ]; then
    echo "Enabling S3 encryption with KMS..."
    aws s3api put-bucket-encryption \
        --bucket $BUCKET_NAME \
        --server-side-encryption-configuration '{
            "Rules": [{
                "ApplyServerSideEncryptionByDefault": {
                    "SSEAlgorithm": "aws:kms",
                    "KMSMasterKeyID": "'$AUDITFLOW_S3_KMS_KEY_ID'"
                },
                "BucketKeyEnabled": true
            }]
        }'
    echo "✓ S3 encryption enabled with KMS"
else
    echo "Warning: KMS Key ID not found, using AES256 encryption"
    aws s3api put-bucket-encryption \
        --bucket $BUCKET_NAME \
        --server-side-encryption-configuration '{
            "Rules": [{
                "ApplyServerSideEncryptionByDefault": {
                    "SSEAlgorithm": "AES256"
                }
            }]
        }'
    echo "✓ S3 encryption enabled with AES256"
fi

echo ""

# Step 3: Configure S3 bucket policies
echo "Step 3: Configuring S3 bucket policies..."
if [ -f "infrastructure/s3_bucket_policy.sh" ]; then
    bash infrastructure/s3_bucket_policy.sh
else
    echo "Warning: s3_bucket_policy.sh not found, skipping bucket policy configuration"
fi

echo ""

# Step 4: Configure S3 CORS and lifecycle policies
echo "Step 4: Configuring S3 CORS and lifecycle policies..."
if [ -f "infrastructure/s3_config.sh" ]; then
    bash infrastructure/s3_config.sh
else
    echo "Warning: s3_config.sh not found, skipping CORS and lifecycle configuration"
fi

echo ""

# Step 5: Create DynamoDB Tables
echo "Step 5: Creating DynamoDB Tables..."

# Create AuditFlow-Documents table
echo "Creating DynamoDB Table: AuditFlow-Documents..."
if aws dynamodb describe-table --table-name AuditFlow-Documents 2>/dev/null; then
    echo "Table AuditFlow-Documents already exists"
else
    aws dynamodb create-table \
        --table-name AuditFlow-Documents \
        --attribute-definitions \
            AttributeName=document_id,AttributeType=S \
            AttributeName=loan_application_id,AttributeType=S \
            AttributeName=upload_timestamp,AttributeType=S \
            AttributeName=processing_status,AttributeType=S \
        --key-schema AttributeName=document_id,KeyType=HASH \
        --global-secondary-indexes \
            "[{\"IndexName\": \"loan_application_id-upload_timestamp-index\",\"KeySchema\":[{\"AttributeName\":\"loan_application_id\",\"KeyType\":\"HASH\"},{\"AttributeName\":\"upload_timestamp\",\"KeyType\":\"RANGE\"}],\"Projection\":{\"ProjectionType\":\"ALL\"}}, \
              {\"IndexName\": \"processing_status-upload_timestamp-index\",\"KeySchema\":[{\"AttributeName\":\"processing_status\",\"KeyType\":\"HASH\"},{\"AttributeName\":\"upload_timestamp\",\"KeyType\":\"RANGE\"}],\"Projection\":{\"ProjectionType\":\"ALL\"}}]" \
        --billing-mode PAY_PER_REQUEST
    echo "✓ Table AuditFlow-Documents created"
fi

# Create AuditFlow-AuditRecords table
echo "Creating DynamoDB Table: AuditFlow-AuditRecords..."
if aws dynamodb describe-table --table-name AuditFlow-AuditRecords 2>/dev/null; then
    echo "Table AuditFlow-AuditRecords already exists"
else
    aws dynamodb create-table \
        --table-name AuditFlow-AuditRecords \
        --attribute-definitions \
            AttributeName=audit_record_id,AttributeType=S \
            AttributeName=loan_application_id,AttributeType=S \
            AttributeName=audit_timestamp,AttributeType=S \
            AttributeName=risk_score,AttributeType=N \
            AttributeName=status,AttributeType=S \
        --key-schema AttributeName=audit_record_id,KeyType=HASH \
        --global-secondary-indexes \
            "[{\"IndexName\": \"loan_application_id-audit_timestamp-index\",\"KeySchema\":[{\"AttributeName\":\"loan_application_id\",\"KeyType\":\"HASH\"},{\"AttributeName\":\"audit_timestamp\",\"KeyType\":\"RANGE\"}],\"Projection\":{\"ProjectionType\":\"ALL\"}}, \
              {\"IndexName\": \"risk_score-audit_timestamp-index\",\"KeySchema\":[{\"AttributeName\":\"status\",\"KeyType\":\"HASH\"},{\"AttributeName\":\"risk_score\",\"KeyType\":\"RANGE\"}],\"Projection\":{\"ProjectionType\":\"ALL\"}}, \
              {\"IndexName\": \"status-audit_timestamp-index\",\"KeySchema\":[{\"AttributeName\":\"status\",\"KeyType\":\"HASH\"},{\"AttributeName\":\"audit_timestamp\",\"KeyType\":\"RANGE\"}],\"Projection\":{\"ProjectionType\":\"ALL\"}}]" \
        --billing-mode PAY_PER_REQUEST
    echo "✓ Table AuditFlow-AuditRecords created"
fi

echo ""

# Step 6: Create IAM Execution Role for Lambda
echo "Step 6: Creating Lambda Execution Role..."
if aws iam get-role --role-name AuditFlowLambdaExecutionRole 2>/dev/null; then
    echo "Role AuditFlowLambdaExecutionRole already exists"
else
    aws iam create-role \
        --role-name AuditFlowLambdaExecutionRole \
        --assume-role-policy-document '{
            "Version": "2012-10-17",
            "Statement": [{ 
                "Action": "sts:AssumeRole", 
                "Effect": "Allow", 
                "Principal": { "Service": "lambda.amazonaws.com" } 
            }]
        }'
    echo "✓ Lambda Execution Role created"
fi

echo ""
echo "=========================================="
echo "Infrastructure deployment complete!"
echo "=========================================="
echo "Resources created:"
echo "  - S3 Bucket: $BUCKET_NAME"
echo "  - KMS Key: $AUDITFLOW_S3_KMS_KEY_ID"
echo "  - DynamoDB Tables: AuditFlow-Documents, AuditFlow-AuditRecords"
echo "  - IAM Role: AuditFlowLambdaExecutionRole"
echo "=========================================="
