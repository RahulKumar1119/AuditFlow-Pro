#!/bin/bash
# infrastructure/deploy_trigger_lambda.sh
# Deploy the S3 Event Trigger Lambda function
# Task 13: Implement S3 event triggers and Lambda integration

set -e

REGION="ap-south-1"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
FUNCTION_NAME="AuditFlow-Trigger"
ROLE_NAME="AuditFlowLambdaExecutionRole"
BUCKET_NAME="auditflow-documents-prod-${ACCOUNT_ID}"

echo "=========================================="
echo "Deploying S3 Event Trigger Lambda Function"
echo "Region: $REGION"
echo "Account: $ACCOUNT_ID"
echo "Function: $FUNCTION_NAME"
echo "=========================================="
echo ""

# Step 1: Get State Machine ARN
echo "Step 1: Retrieving Step Functions State Machine ARN..."
STATE_MACHINE_ARN=$(aws stepfunctions list-state-machines \
    --query "stateMachines[?name=='AuditFlowDocumentProcessing'].stateMachineArn" \
    --output text 2>/dev/null || echo "")

if [ -z "$STATE_MACHINE_ARN" ]; then
    echo "Warning: Step Functions state machine 'AuditFlowDocumentProcessing' not found."
    echo "Please deploy Step Functions first using: bash infrastructure/step_functions_deploy.sh"
    echo ""
    echo "Continuing with deployment, but Lambda will need STATE_MACHINE_ARN environment variable..."
    STATE_MACHINE_ARN="arn:aws:states:$REGION:$ACCOUNT_ID:stateMachine:AuditFlowDocumentProcessing"
fi

echo "State Machine ARN: $STATE_MACHINE_ARN"
echo ""

# Step 2: Get or create IAM role
echo "Step 2: Configuring IAM Role..."
if aws iam get-role --role-name $ROLE_NAME 2>/dev/null; then
    echo "Role $ROLE_NAME already exists"
    ROLE_ARN=$(aws iam get-role --role-name $ROLE_NAME --query 'Role.Arn' --output text)
else
    echo "Creating IAM role..."
    ROLE_ARN=$(aws iam create-role \
        --role-name $ROLE_NAME \
        --assume-role-policy-document '{
            "Version": "2012-10-17",
            "Statement": [{
                "Action": "sts:AssumeRole",
                "Effect": "Allow",
                "Principal": {"Service": "lambda.amazonaws.com"}
            }]
        }' \
        --query 'Role.Arn' \
        --output text)
    echo "✓ Role created: $ROLE_ARN"
fi

# Attach necessary policies
echo "Attaching IAM policies..."

# Basic Lambda execution policy
aws iam attach-role-policy \
    --role-name $ROLE_NAME \
    --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole 2>/dev/null || true

# SQS access policy
aws iam attach-role-policy \
    --role-name $ROLE_NAME \
    --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaSQSQueueExecutionRole 2>/dev/null || true

# Custom policy for S3, Step Functions, and DynamoDB access
POLICY_NAME="AuditFlowTriggerLambdaPolicy"
POLICY_ARN="arn:aws:iam::${ACCOUNT_ID}:policy/${POLICY_NAME}"

# Check if policy exists
if aws iam get-policy --policy-arn $POLICY_ARN 2>/dev/null; then
    echo "Policy $POLICY_NAME already exists"
    
    # Create new policy version
    aws iam create-policy-version \
        --policy-arn $POLICY_ARN \
        --policy-document '{
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "s3:GetObject",
                        "s3:GetObjectMetadata",
                        "s3:ListBucket"
                    ],
                    "Resource": [
                        "arn:aws:s3:::'$BUCKET_NAME'",
                        "arn:aws:s3:::'$BUCKET_NAME'/*"
                    ]
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "states:StartExecution"
                    ],
                    "Resource": "'$STATE_MACHINE_ARN'"
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "logs:CreateLogGroup",
                        "logs:CreateLogStream",
                        "logs:PutLogEvents"
                    ],
                    "Resource": "arn:aws:logs:'$REGION':'$ACCOUNT_ID':log-group:/aws/lambda/'$FUNCTION_NAME':*"
                }
            ]
        }' \
        --set-as-default 2>/dev/null || echo "Policy version may already exist"
else
    echo "Creating custom policy..."
    aws iam create-policy \
        --policy-name $POLICY_NAME \
        --policy-document '{
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "s3:GetObject",
                        "s3:GetObjectMetadata",
                        "s3:ListBucket"
                    ],
                    "Resource": [
                        "arn:aws:s3:::'$BUCKET_NAME'",
                        "arn:aws:s3:::'$BUCKET_NAME'/*"
                    ]
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "states:StartExecution"
                    ],
                    "Resource": "'$STATE_MACHINE_ARN'"
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "logs:CreateLogGroup",
                        "logs:CreateLogStream",
                        "logs:PutLogEvents"
                    ],
                    "Resource": "arn:aws:logs:'$REGION':'$ACCOUNT_ID':log-group:/aws/lambda/'$FUNCTION_NAME':*"
                }
            ]
        }'
    echo "✓ Policy created"
fi

# Attach custom policy to role
aws iam attach-role-policy \
    --role-name $ROLE_NAME \
    --policy-arn $POLICY_ARN 2>/dev/null || true

echo "✓ IAM policies configured"
echo ""

# Wait for IAM role to propagate
echo "Waiting for IAM role to propagate..."
sleep 10

# Step 3: Package Lambda function
echo "Step 3: Packaging Lambda function..."

# Get the script directory and project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

cd "$PROJECT_ROOT/backend/functions/trigger"

# Create deployment package
if [ -f "deployment_package.zip" ]; then
    rm deployment_package.zip
fi

zip -q deployment_package.zip app.py
echo "✓ Lambda function packaged"

cd "$PROJECT_ROOT"
echo ""

# Step 4: Deploy Lambda function
echo "Step 4: Deploying Lambda function..."

if aws lambda get-function --function-name $FUNCTION_NAME 2>/dev/null; then
    echo "Function exists, updating code..."
    aws lambda update-function-code \
        --function-name $FUNCTION_NAME \
        --zip-file fileb://backend/functions/trigger/deployment_package.zip
    
    echo "Waiting for code update to complete..."
    aws lambda wait function-updated --function-name $FUNCTION_NAME
    
    echo "Updating function configuration..."
    aws lambda update-function-configuration \
        --function-name $FUNCTION_NAME \
        --runtime python3.10 \
        --handler app.lambda_handler \
        --role $ROLE_ARN \
        --timeout 300 \
        --memory-size 256 \
        --environment "Variables={STATE_MACHINE_ARN=$STATE_MACHINE_ARN}"
    
    echo "✓ Lambda function updated"
else
    echo "Creating new Lambda function..."
    aws lambda create-function \
        --function-name $FUNCTION_NAME \
        --runtime python3.10 \
        --role $ROLE_ARN \
        --handler app.lambda_handler \
        --zip-file fileb://backend/functions/trigger/deployment_package.zip \
        --timeout 300 \
        --memory-size 256 \
        --environment "Variables={STATE_MACHINE_ARN=$STATE_MACHINE_ARN}" \
        --description "S3 Event Trigger Handler for AuditFlow-Pro document processing"
    
    echo "✓ Lambda function created"
fi

# Wait for function to be active
echo "Waiting for function to be active..."
aws lambda wait function-active --function-name $FUNCTION_NAME

FUNCTION_ARN=$(aws lambda get-function \
    --function-name $FUNCTION_NAME \
    --query 'Configuration.FunctionArn' \
    --output text)

echo "Function ARN: $FUNCTION_ARN"
echo ""

# Step 5: Configure concurrency limits
echo "Step 5: Configuring concurrency limits..."
if [ -f "infrastructure/lambda_concurrency_setup.sh" ]; then
    bash infrastructure/lambda_concurrency_setup.sh || echo "Warning: Could not set concurrency limit (account limit reached). Continuing..."
else
    echo "Setting reserved concurrent executions to 10..."
    aws lambda put-function-concurrency \
        --function-name $FUNCTION_NAME \
        --reserved-concurrent-executions 10 2>/dev/null || echo "Warning: Could not set concurrency limit (account limit reached). Continuing..."
    echo "✓ Concurrency limit set (or skipped if account limit reached)"
fi

echo ""

# Step 6: Configure S3 event triggers
echo "Step 6: Configuring S3 event triggers..."
if [ -f "infrastructure/s3_event_trigger_setup.sh" ]; then
    bash infrastructure/s3_event_trigger_setup.sh
else
    echo "Warning: s3_event_trigger_setup.sh not found"
    echo "Please run: bash infrastructure/s3_event_trigger_setup.sh"
fi

echo ""
echo "=========================================="
echo "Trigger Lambda Deployment Complete!"
echo "=========================================="
echo "Function Details:"
echo "  - Name: $FUNCTION_NAME"
echo "  - ARN: $FUNCTION_ARN"
echo "  - Runtime: python3.10"
echo "  - Timeout: 300 seconds"
echo "  - Memory: 256 MB"
echo "  - Concurrency Limit: 10"
echo ""
echo "Environment Variables:"
echo "  - STATE_MACHINE_ARN: $STATE_MACHINE_ARN"
echo ""
echo "Next Steps:"
echo "  1. Verify S3 event notifications: bash infrastructure/s3_event_trigger_setup.sh"
echo "  2. Test by uploading a document to s3://$BUCKET_NAME/uploads/"
echo "  3. Monitor CloudWatch Logs: /aws/lambda/$FUNCTION_NAME"
echo "=========================================="

