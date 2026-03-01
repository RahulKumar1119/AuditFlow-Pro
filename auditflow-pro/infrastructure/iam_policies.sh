#!/bin/bash
# infrastructure/iam_policies.sh
# Creates IAM roles and policies for AuditFlow-Pro Lambda functions

set -e

REGION="${AWS_REGION:-ap-south-1}"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
BUCKET_NAME="auditflow-documents-prod-${ACCOUNT_ID}"

echo "Creating IAM roles and policies for AuditFlow-Pro..."

# 1. Create Lambda Execution Role
echo "Creating Lambda Execution Role..."
aws iam create-role \
    --role-name AuditFlowLambdaExecutionRole \
    --assume-role-policy-document '{
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"Service": "lambda.amazonaws.com"},
            "Action": "sts:AssumeRole"
        }]
    }' 2>/dev/null || echo "Role already exists"

# 2. Attach basic Lambda execution policy
echo "Attaching basic Lambda execution policy..."
aws iam attach-role-policy \
    --role-name AuditFlowLambdaExecutionRole \
    --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

# 3. Create custom policy for S3 access
echo "Creating S3 access policy..."
aws iam put-role-policy \
    --role-name AuditFlowLambdaExecutionRole \
    --policy-name S3DocumentAccess \
    --policy-document "{
        \"Version\": \"2012-10-17\",
        \"Statement\": [
            {
                \"Effect\": \"Allow\",
                \"Action\": [
                    \"s3:GetObject\",
                    \"s3:PutObject\",
                    \"s3:DeleteObject\",
                    \"s3:ListBucket\"
                ],
                \"Resource\": [
                    \"arn:aws:s3:::${BUCKET_NAME}\",
                    \"arn:aws:s3:::${BUCKET_NAME}/*\"
                ]
            }
        ]
    }"

# 4. Create custom policy for DynamoDB access
echo "Creating DynamoDB access policy..."
aws iam put-role-policy \
    --role-name AuditFlowLambdaExecutionRole \
    --policy-name DynamoDBAccess \
    --policy-document '{
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "dynamodb:PutItem",
                    "dynamodb:GetItem",
                    "dynamodb:UpdateItem",
                    "dynamodb:Query",
                    "dynamodb:Scan",
                    "dynamodb:BatchWriteItem"
                ],
                "Resource": [
                    "arn:aws:dynamodb:*:*:table/AuditFlow-Documents",
                    "arn:aws:dynamodb:*:*:table/AuditFlow-Documents/index/*",
                    "arn:aws:dynamodb:*:*:table/AuditFlow-AuditRecords",
                    "arn:aws:dynamodb:*:*:table/AuditFlow-AuditRecords/index/*"
                ]
            }
        ]
    }'

# 5. Create custom policy for AI services (Textract, Bedrock, Comprehend)
echo "Creating AI services access policy..."
aws iam put-role-policy \
    --role-name AuditFlowLambdaExecutionRole \
    --policy-name AIServicesAccess \
    --policy-document '{
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "textract:AnalyzeDocument",
                    "textract:DetectDocumentText",
                    "bedrock:InvokeModel",
                    "comprehend:DetectPiiEntities"
                ],
                "Resource": "*"
            }
        ]
    }'

# 6. Create Step Functions execution role
echo "Creating Step Functions execution role..."
aws iam create-role \
    --role-name AuditFlowStepFunctionsRole \
    --assume-role-policy-document '{
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"Service": "states.amazonaws.com"},
            "Action": "sts:AssumeRole"
        }]
    }' 2>/dev/null || echo "Role already exists"

# 7. Create policy for Step Functions to invoke Lambda
echo "Creating Step Functions Lambda invoke policy..."
aws iam put-role-policy \
    --role-name AuditFlowStepFunctionsRole \
    --policy-name LambdaInvokePolicy \
    --policy-document '{
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "lambda:InvokeFunction"
                ],
                "Resource": "arn:aws:lambda:*:*:function:AuditFlow-*"
            },
            {
                "Effect": "Allow",
                "Action": [
                    "logs:CreateLogGroup",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents"
                ],
                "Resource": "*"
            }
        ]
    }'

# 8. Create API Gateway execution role
echo "Creating API Gateway execution role..."
aws iam create-role \
    --role-name AuditFlowAPIGatewayRole \
    --assume-role-policy-document '{
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"Service": "apigateway.amazonaws.com"},
            "Action": "sts:AssumeRole"
        }]
    }' 2>/dev/null || echo "Role already exists"

# 9. Attach CloudWatch Logs policy to API Gateway role
aws iam attach-role-policy \
    --role-name AuditFlowAPIGatewayRole \
    --policy-arn arn:aws:iam::aws:policy/service-role/AmazonAPIGatewayPushToCloudWatchLogs

echo "IAM roles and policies created successfully!"
echo "Lambda Execution Role ARN: arn:aws:iam::${ACCOUNT_ID}:role/AuditFlowLambdaExecutionRole"
echo "Step Functions Role ARN: arn:aws:iam::${ACCOUNT_ID}:role/AuditFlowStepFunctionsRole"
echo "API Gateway Role ARN: arn:aws:iam::${ACCOUNT_ID}:role/AuditFlowAPIGatewayRole"
