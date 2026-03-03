#!/bin/bash
# infrastructure/deploy_processing_lambdas.sh
# Deploy all processing Lambda functions

set -e

REGION="ap-south-1"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ROLE_NAME="AuditFlowLambdaExecutionRole"

# Get script directory and project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

echo "=========================================="
echo "Deploying AuditFlow Processing Lambdas"
echo "Region: $REGION"
echo "Account: $ACCOUNT_ID"
echo "=========================================="
echo ""

# Get IAM role ARN
ROLE_ARN=$(aws iam get-role --role-name $ROLE_NAME --query 'Role.Arn' --output text)
echo "Using IAM Role: $ROLE_ARN"
echo ""

# Function to deploy a Lambda
deploy_lambda() {
    local FUNCTION_NAME=$1
    local FUNCTION_DIR=$2
    local HANDLER=$3
    local DESCRIPTION=$4
    local TIMEOUT=${5:-300}
    local MEMORY=${6:-512}
    
    echo "Deploying $FUNCTION_NAME..."
    echo "  Directory: $FUNCTION_DIR"
    
    cd "$PROJECT_ROOT/$FUNCTION_DIR"
    
    # Create deployment package
    if [ -f "deployment_package.zip" ]; then
        rm deployment_package.zip
    fi
    
    # Package function code
    zip -q deployment_package.zip *.py 2>/dev/null || true
    
    # Check if function exists
    if aws lambda get-function --function-name $FUNCTION_NAME 2>/dev/null; then
        echo "  Updating existing function..."
        aws lambda update-function-code \
            --function-name $FUNCTION_NAME \
            --zip-file fileb://deployment_package.zip > /dev/null
        
        aws lambda wait function-updated --function-name $FUNCTION_NAME
        
        aws lambda update-function-configuration \
            --function-name $FUNCTION_NAME \
            --runtime python3.10 \
            --handler $HANDLER \
            --role $ROLE_ARN \
            --timeout $TIMEOUT \
            --memory-size $MEMORY > /dev/null
    else
        echo "  Creating new function..."
        aws lambda create-function \
            --function-name $FUNCTION_NAME \
            --runtime python3.10 \
            --role $ROLE_ARN \
            --handler $HANDLER \
            --zip-file fileb://deployment_package.zip \
            --timeout $TIMEOUT \
            --memory-size $MEMORY \
            --description "$DESCRIPTION" > /dev/null
    fi
    
    aws lambda wait function-active --function-name $FUNCTION_NAME
    echo "  ✓ $FUNCTION_NAME deployed"
    
    cd "$PROJECT_ROOT"
}

# Deploy all processing Lambdas
deploy_lambda "AuditFlow-Classifier" "backend/functions/classifier" "app.lambda_handler" "Document classification Lambda" 300 512
deploy_lambda "AuditFlow-Extractor" "backend/functions/extractor" "app.lambda_handler" "Data extraction Lambda" 300 1024
deploy_lambda "AuditFlow-Validator" "backend/functions/validator" "app.lambda_handler" "Data validation Lambda" 300 512
deploy_lambda "AuditFlow-RiskScorer" "backend/functions/risk_scorer" "app.lambda_handler" "Risk scoring Lambda" 300 512
deploy_lambda "AuditFlow-Reporter" "backend/functions/reporter" "app.lambda_handler" "Report generation Lambda" 300 1024

echo ""
echo "=========================================="
echo "All Processing Lambdas Deployed!"
echo "=========================================="
echo "Deployed Functions:"
echo "  - AuditFlow-Classifier"
echo "  - AuditFlow-Extractor"
echo "  - AuditFlow-Validator"
echo "  - AuditFlow-RiskScorer"
echo "  - AuditFlow-Reporter"
echo "=========================================="
