#!/bin/bash
# infrastructure/deploy.sh

REGION="us-east-1"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
BUCKET_NAME="auditflow-documents-prod-${ACCOUNT_ID}"

echo "Deploying AuditFlow-Pro Infrastructure in $REGION..."

# 1. Create S3 Bucket for Document Storage
echo "Creating S3 Bucket: $BUCKET_NAME..."
aws s3api create-bucket \
    --bucket $BUCKET_NAME \
    --region $REGION \
    --create-bucket-configuration LocationConstraint=$REGION

# Enable S3 Server-Side Encryption (AES256)
aws s3api put-bucket-encryption \
    --bucket $BUCKET_NAME \
    --server-side-encryption-configuration '{"Rules": [{"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}]}'

# 2. Create DynamoDB Table: AuditFlow-Documents
echo "Creating DynamoDB Table: AuditFlow-Documents..."
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

# 3. Create DynamoDB Table: AuditFlow-AuditRecords
echo "Creating DynamoDB Table: AuditFlow-AuditRecords..."
aws dynamodb create-table \
    --table-name AuditFlow-AuditRecords \
    --attribute-definitions \
        AttributeName=audit_record_id,AttributeType=S \
        AttributeName=loan_application_id,AttributeType=S \
        AttributeName=audit_timestamp,AttributeType=S \
    --key-schema AttributeName=audit_record_id,KeyType=HASH \
    --global-secondary-indexes \
        "[{\"IndexName\": \"loan_application_id-audit_timestamp-index\",\"KeySchema\":[{\"AttributeName\":\"loan_application_id\",\"KeyType\":\"HASH\"},{\"AttributeName\":\"audit_timestamp\",\"KeyType\":\"RANGE\"}],\"Projection\":{\"ProjectionType\":\"ALL\"}}]" \
    --billing-mode PAY_PER_REQUEST

# 4. Create Base IAM Execution Role for Lambda
echo "Creating Lambda Execution Role..."
aws iam create-role \
    --role-name AuditFlowLambdaExecutionRole \
    --assume-role-policy-document '{
        "Version": "2012-10-17",
        "Statement": [{ "Action": "sts:AssumeRole", "Effect": "Allow", "Principal": { "Service": "lambda.amazonaws.com" } }]
    }'

echo "Infrastructure deployment initiated successfully!"
