#!/bin/bash
# infrastructure/deploy_api_handler.sh
# Deploys the API Handler Lambda function for API Gateway integration
# Task 15: API Gateway implementation

set -e

REGION="${AWS_REGION:-ap-south-1}"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
FUNCTION_NAME="AuditFlowAPIHandler"

echo "Deploying API Handler Lambda function..."
echo "Region: $REGION"
echo "Account ID: $ACCOUNT_ID"
echo ""

# Get S3 bucket name
BUCKET_NAME="auditflow-documents-${REGION}-${ACCOUNT_ID}"

# Get DynamoDB table names
AUDIT_TABLE="AuditFlow-AuditRecords"
DOCUMENTS_TABLE="AuditFlow-Documents"

# Get KMS key ARN
KMS_KEY_ARN=$(aws kms list-aliases --region $REGION --query "Aliases[?AliasName=='alias/auditflow-key'].TargetKeyId" --output text 2>/dev/null || echo "")

if [ -z "$KMS_KEY_ARN" ]; then
    echo "Warning: KMS key not found. Encryption features may not work."
    KMS_KEY_ARN="arn:aws:kms:${REGION}:${ACCOUNT_ID}:alias/auditflow-key"
fi

# 1. Create IAM role for Lambda function
echo "Creating IAM role for API Handler Lambda..."
ROLE_NAME="AuditFlowAPIHandlerRole"

aws iam create-role \
    --role-name $ROLE_NAME \
    --assume-role-policy-document '{
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"Service": "lambda.amazonaws.com"},
            "Action": "sts:AssumeRole"
        }]
    }' 2>/dev/null || echo "  (Role already exists)"

echo "✓ IAM role created: $ROLE_NAME"

# 2. Attach policies to Lambda role
echo "Attaching policies to Lambda role..."

# Basic Lambda execution policy
aws iam attach-role-policy \
    --role-name $ROLE_NAME \
    --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole 2>/dev/null || echo "  (Policy already attached)"

# Custom policy for S3, DynamoDB, and KMS access
aws iam put-role-policy \
    --role-name $ROLE_NAME \
    --policy-name APIHandlerAccessPolicy \
    --policy-document "{
        \"Version\": \"2012-10-17\",
        \"Statement\": [
            {
                \"Effect\": \"Allow\",
                \"Action\": [
                    \"s3:GetObject\",
                    \"s3:PutObject\",
                    \"s3:ListBucket\"
                ],
                \"Resource\": [
                    \"arn:aws:s3:::${BUCKET_NAME}\",
                    \"arn:aws:s3:::${BUCKET_NAME}/*\"
                ]
            },
            {
                \"Effect\": \"Allow\",
                \"Action\": [
                    \"dynamodb:GetItem\",
                    \"dynamodb:PutItem\",
                    \"dynamodb:Query\",
                    \"dynamodb:Scan\",
                    \"dynamodb:UpdateItem\"
                ],
                \"Resource\": [
                    \"arn:aws:dynamodb:${REGION}:${ACCOUNT_ID}:table/${AUDIT_TABLE}\",
                    \"arn:aws:dynamodb:${REGION}:${ACCOUNT_ID}:table/${AUDIT_TABLE}/index/*\",
                    \"arn:aws:dynamodb:${REGION}:${ACCOUNT_ID}:table/${DOCUMENTS_TABLE}\",
                    \"arn:aws:dynamodb:${REGION}:${ACCOUNT_ID}:table/${DOCUMENTS_TABLE}/index/*\"
                ]
            },
            {
                \"Effect\": \"Allow\",
                \"Action\": [
                    \"kms:Decrypt\",
                    \"kms:Encrypt\",
                    \"kms:GenerateDataKey\"
                ],
                \"Resource\": \"${KMS_KEY_ARN}\"
            },
            {
                \"Effect\": \"Allow\",
                \"Action\": [
                    \"logs:CreateLogGroup\",
                    \"logs:CreateLogStream\",
                    \"logs:PutLogEvents\"
                ],
                \"Resource\": \"arn:aws:logs:${REGION}:${ACCOUNT_ID}:log-group:/aws/lambda/${FUNCTION_NAME}:*\"
            }
        ]
    }"

echo "✓ Policies attached"

# Wait for role to be available
echo "Waiting for IAM role to propagate..."
sleep 10

# 3. Package Lambda function
echo "Packaging Lambda function..."

# Get the script directory and project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

cd "$PROJECT_ROOT/backend/functions/api_handler"

# Create deployment package
if [ -f "deployment.zip" ]; then
    rm deployment.zip
fi

zip -q deployment.zip app.py

echo "✓ Lambda function packaged"

cd "$PROJECT_ROOT"

# 4. Create or update Lambda function
echo "Deploying Lambda function..."

ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/${ROLE_NAME}"
ZIP_FILE="$PROJECT_ROOT/backend/functions/api_handler/deployment.zip"

# Try to create the function
aws lambda create-function \
    --function-name $FUNCTION_NAME \
    --runtime python3.11 \
    --role $ROLE_ARN \
    --handler app.lambda_handler \
    --zip-file fileb://$ZIP_FILE \
    --timeout 30 \
    --memory-size 512 \
    --environment "Variables={
        UPLOAD_BUCKET=${BUCKET_NAME},
        AUDIT_TABLE=${AUDIT_TABLE},
        DOCUMENTS_TABLE=${DOCUMENTS_TABLE},
        KMS_KEY_ARN=${KMS_KEY_ARN}
    }" \
    --region $REGION 2>/dev/null && echo "✓ Lambda function created" || {
        # Function exists, update it
        echo "  Function exists, updating code..."
        aws lambda update-function-code \
            --function-name $FUNCTION_NAME \
            --zip-file fileb://$ZIP_FILE \
            --region $REGION > /dev/null
        
        aws lambda wait function-updated --function-name $FUNCTION_NAME --region $REGION
        
        echo "  Updating configuration..."
        aws lambda update-function-configuration \
            --function-name $FUNCTION_NAME \
            --timeout 30 \
            --memory-size 512 \
            --environment "Variables={
                UPLOAD_BUCKET=${BUCKET_NAME},
                AUDIT_TABLE=${AUDIT_TABLE},
                DOCUMENTS_TABLE=${DOCUMENTS_TABLE},
                KMS_KEY_ARN=${KMS_KEY_ARN}
            }" \
            --region $REGION > /dev/null
        
        echo "✓ Lambda function updated"
    }

# Clean up
rm -f "$PROJECT_ROOT/backend/functions/api_handler/deployment.zip"


# 5. Configure CloudWatch Logs retention
echo "Configuring CloudWatch Logs retention..."
aws logs put-retention-policy \
    --log-group-name "/aws/lambda/${FUNCTION_NAME}" \
    --retention-in-days 365 \
    --region $REGION 2>/dev/null || echo "  (Log group will be created on first invocation)"

echo "✓ CloudWatch Logs configured (1 year retention)"

# Get Lambda ARN
LAMBDA_ARN=$(aws lambda get-function --function-name $FUNCTION_NAME --region $REGION --query 'Configuration.FunctionArn' --output text)

echo ""
echo "================================================"
echo "✓ API Handler Lambda deployed successfully!"
echo "================================================"
echo ""
echo "Configuration Details:"
echo "  Function Name: $FUNCTION_NAME"
echo "  Function ARN: $LAMBDA_ARN"
echo "  Runtime: Python 3.11"
echo "  Timeout: 30 seconds"
echo "  Memory: 512 MB"
echo "  Region: $REGION"
echo ""
echo "Environment Variables:"
echo "  UPLOAD_BUCKET: $BUCKET_NAME"
echo "  AUDIT_TABLE: $AUDIT_TABLE"
echo "  DOCUMENTS_TABLE: $DOCUMENTS_TABLE"
echo "  KMS_KEY_ARN: $KMS_KEY_ARN"
echo ""
echo "IAM Role: $ROLE_ARN"
echo "  ✓ S3 read/write access"
echo "  ✓ DynamoDB read/write access"
echo "  ✓ KMS encryption/decryption"
echo "  ✓ CloudWatch Logs access"
echo ""
echo "================================================"
echo "Next Steps:"
echo "================================================"
echo "1. Set up API Gateway integration:"
echo "   ./infrastructure/api_gateway_setup.sh"
echo ""
echo "2. Test the Lambda function:"
echo "   aws lambda invoke \\"
echo "     --function-name $FUNCTION_NAME \\"
echo "     --payload '{\"httpMethod\":\"GET\",\"resource\":\"/audits\"}' \\"
echo "     --region $REGION \\"
echo "     response.json"
echo ""
echo "3. View logs:"
echo "   aws logs tail /aws/lambda/${FUNCTION_NAME} --follow --region $REGION"
echo ""
echo "================================================"
