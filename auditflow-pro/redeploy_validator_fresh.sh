#!/bin/bash
# Delete and redeploy the validator Lambda function from scratch

set -e

REGION="ap-south-1"
FUNCTION_NAME="AuditFlow-Validator"
ROLE_NAME="AuditFlowLambdaExecutionRole"

echo "=========================================="
echo "Fresh Deployment of $FUNCTION_NAME"
echo "=========================================="
echo ""

# Step 1: Delete existing Lambda function
echo "Step 1: Deleting existing Lambda function..."
if aws lambda get-function --function-name "$FUNCTION_NAME" --region "$REGION" 2>/dev/null; then
    aws lambda delete-function --function-name "$FUNCTION_NAME" --region "$REGION"
    echo "  ✓ Lambda function deleted"
    sleep 5
else
    echo "  Lambda function doesn't exist, skipping deletion"
fi
echo ""

# Step 2: Get IAM role ARN
echo "Step 2: Getting IAM role..."
ROLE_ARN=$(aws iam get-role --role-name "$ROLE_NAME" --query 'Role.Arn' --output text)
echo "  Using IAM Role: $ROLE_ARN"
echo ""

# Step 3: Create deployment package
echo "Step 3: Creating deployment package..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/backend/functions/validator"

# Remove old package
rm -f deployment_package.zip

# Create temp directory
TEMP_DIR=$(mktemp -d)
echo "  Using temp directory: $TEMP_DIR"

# Copy validator files
echo "  Copying validator files..."
cp *.py "$TEMP_DIR/"

# Copy shared directory
echo "  Copying shared modules..."
mkdir -p "$TEMP_DIR/shared"
cp "$SCRIPT_DIR/backend/shared/"*.py "$TEMP_DIR/shared/"

# Ensure __init__.py exists
if [ ! -f "$TEMP_DIR/shared/__init__.py" ]; then
    echo "# Shared modules package" > "$TEMP_DIR/shared/__init__.py"
fi

# Create zip
cd "$TEMP_DIR"
zip -r "$SCRIPT_DIR/backend/functions/validator/deployment_package.zip" . -q

echo "  ✓ Deployment package created"
echo ""

# Step 4: Create new Lambda function
echo "Step 4: Creating new Lambda function..."
cd "$SCRIPT_DIR/backend/functions/validator"

aws lambda create-function \
    --function-name "$FUNCTION_NAME" \
    --runtime python3.10 \
    --role "$ROLE_ARN" \
    --handler app.lambda_handler \
    --zip-file fileb://deployment_package.zip \
    --timeout 300 \
    --memory-size 512 \
    --description "Cross-document validator Lambda" \
    --region "$REGION" \
    > /dev/null

echo "  ✓ Lambda function created"
echo ""

# Step 5: Wait for function to be active
echo "Step 5: Waiting for function to be active..."
aws lambda wait function-active --function-name "$FUNCTION_NAME" --region "$REGION"
echo "  ✓ Function is active"
echo ""

# Clean up
rm -rf "$TEMP_DIR"
rm -f deployment_package.zip

echo "=========================================="
echo "✓ $FUNCTION_NAME deployed successfully!"
echo "=========================================="
echo ""
echo "Function details:"
aws lambda get-function --function-name "$FUNCTION_NAME" --region "$REGION" --query 'Configuration.[FunctionName,Runtime,Handler,LastModified]' --output table
