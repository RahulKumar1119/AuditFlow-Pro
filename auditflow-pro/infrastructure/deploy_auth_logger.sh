#!/bin/bash
# infrastructure/deploy_auth_logger.sh
# Deploys the authentication logger Lambda function and configures Cognito triggers
# Requirements: 18.3, 7.3

set -e

REGION="${AWS_REGION:-ap-south-1}"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

echo "Deploying Authentication Logger Lambda..."
echo "Region: $REGION"
echo "Account ID: $ACCOUNT_ID"
echo ""

# Get User Pool ID
USER_POOL_ID=$(aws cognito-idp list-user-pools --max-results 10 --region $REGION --query "UserPools[?Name=='AuditFlowUserPool'].Id" --output text)

if [ -z "$USER_POOL_ID" ]; then
    echo "Error: User Pool 'AuditFlowUserPool' not found. Please run cognito_setup.sh first."
    exit 1
fi

echo "Found User Pool ID: $USER_POOL_ID"
echo ""

# Create deployment package
echo "Creating deployment package..."
cd backend/functions/auth_logger
zip -q auth_logger.zip app.py
cd ../../..

echo "✓ Deployment package created"
echo ""

# Create IAM role for Lambda
echo "Creating IAM role for Auth Logger Lambda..."
aws iam create-role \
    --role-name AuditFlowAuthLoggerRole \
    --assume-role-policy-document '{
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {
                "Service": "lambda.amazonaws.com"
            },
            "Action": "sts:AssumeRole"
        }]
    }' 2>/dev/null || echo "  (Role already exists)"

# Attach CloudWatch Logs policy
echo "Attaching CloudWatch Logs policy..."
aws iam attach-role-policy \
    --role-name AuditFlowAuthLoggerRole \
    --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

# Wait for role to be available
echo "Waiting for IAM role to propagate..."
sleep 10

echo "✓ IAM role configured"
echo ""

# Create or update Lambda function
echo "Creating/updating Lambda function..."
LAMBDA_ARN=$(aws lambda create-function \
    --function-name AuditFlowAuthLogger \
    --runtime python3.11 \
    --role arn:aws:iam::${ACCOUNT_ID}:role/AuditFlowAuthLoggerRole \
    --handler app.lambda_handler \
    --zip-file fileb://backend/functions/auth_logger/auth_logger.zip \
    --timeout 30 \
    --memory-size 256 \
    --region $REGION \
    --query 'FunctionArn' \
    --output text 2>/dev/null || \
    aws lambda update-function-code \
        --function-name AuditFlowAuthLogger \
        --zip-file fileb://backend/functions/auth_logger/auth_logger.zip \
        --region $REGION \
        --query 'FunctionArn' \
        --output text)

echo "✓ Lambda function deployed: $LAMBDA_ARN"
echo ""

# Grant Cognito permission to invoke Lambda
echo "Granting Cognito permission to invoke Lambda..."
aws lambda add-permission \
    --function-name AuditFlowAuthLogger \
    --statement-id CognitoInvoke \
    --action lambda:InvokeFunction \
    --principal cognito-idp.amazonaws.com \
    --source-arn arn:aws:cognito-idp:${REGION}:${ACCOUNT_ID}:userpool/${USER_POOL_ID} \
    --region $REGION 2>/dev/null || echo "  (Permission already exists)"

echo "✓ Lambda permissions configured"
echo ""

# Configure Cognito triggers
echo "Configuring Cognito triggers..."
aws cognito-idp update-user-pool \
    --user-pool-id $USER_POOL_ID \
    --lambda-config "{
        \"PreAuthentication\": \"${LAMBDA_ARN}\",
        \"PostAuthentication\": \"${LAMBDA_ARN}\",
        \"PreSignUp\": \"${LAMBDA_ARN}\",
        \"PostConfirmation\": \"${LAMBDA_ARN}\",
        \"PreTokenGeneration\": \"${LAMBDA_ARN}\",
        \"CustomMessage\": \"${LAMBDA_ARN}\"
    }" \
    --region $REGION

echo "✓ Cognito triggers configured"
echo ""

# Clean up
rm -f backend/functions/auth_logger/auth_logger.zip

echo "================================================"
echo "✓ Authentication Logger deployment completed!"
echo "================================================"
echo ""
echo "Configuration:"
echo "  Lambda Function: AuditFlowAuthLogger"
echo "  Lambda ARN: $LAMBDA_ARN"
echo "  User Pool ID: $USER_POOL_ID"
echo ""
echo "Configured Triggers:"
echo "  ✓ PreAuthentication - Logs before sign-in"
echo "  ✓ PostAuthentication - Logs successful sign-in"
echo "  ✓ PreSignUp - Logs new user registration"
echo "  ✓ PostConfirmation - Logs user confirmation"
echo "  ✓ PreTokenGeneration - Logs token generation and groups"
echo "  ✓ CustomMessage - Logs password reset requests"
echo ""
echo "All authentication events will be logged to CloudWatch with PII redaction."
echo ""
echo "================================================"
