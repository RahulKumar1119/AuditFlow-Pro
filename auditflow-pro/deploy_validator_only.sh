#!/bin/bash
# Deploy only the validator Lambda function

set -e

REGION="ap-south-1"
FUNCTION_NAME="AuditFlow-Validator"

echo "=========================================="
echo "Deploying $FUNCTION_NAME"
echo "=========================================="

# Get project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/backend/functions/validator"

# Remove old package
rm -f deployment_package.zip

echo "Step 1: Creating deployment package..."

# Create a temporary directory
TEMP_DIR=$(mktemp -d)
echo "  Using temp directory: $TEMP_DIR"

# Copy all validator Python files
echo "Step 2: Copying validator files..."
cp *.py "$TEMP_DIR/"

# Copy shared directory with __init__.py
echo "Step 3: Copying shared modules..."
mkdir -p "$TEMP_DIR/shared"
cp "$SCRIPT_DIR/backend/shared/"*.py "$TEMP_DIR/shared/"

# Ensure __init__.py exists in shared directory
if [ ! -f "$TEMP_DIR/shared/__init__.py" ]; then
    echo "  Creating __init__.py in shared directory..."
    echo "# Shared modules package" > "$TEMP_DIR/shared/__init__.py"
fi

# Create the zip from the temp directory
echo "Step 4: Creating zip file..."
cd "$TEMP_DIR"
zip -r "$SCRIPT_DIR/backend/functions/validator/deployment_package.zip" . -q

# Verify zip contents
echo "Step 5: Verifying zip contents..."
echo "  Files in deployment package:"
unzip -l "$SCRIPT_DIR/backend/functions/validator/deployment_package.zip" | grep -E "shared/|app\.py|rules\.py|golden_record\.py"

# Go back to validator directory
cd "$SCRIPT_DIR/backend/functions/validator"

# Deploy to Lambda
echo "Step 6: Uploading to Lambda..."
aws lambda update-function-code \
    --function-name "$FUNCTION_NAME" \
    --zip-file fileb://deployment_package.zip \
    --region "$REGION" \
    --output json > /dev/null

# Wait for update to complete
echo "Step 7: Waiting for function update..."
aws lambda wait function-updated \
    --function-name "$FUNCTION_NAME" \
    --region "$REGION"

echo ""
echo "=========================================="
echo "✓ $FUNCTION_NAME deployed successfully!"
echo "=========================================="

# Clean up
rm -rf "$TEMP_DIR"
rm -f deployment_package.zip

echo "Deployment complete!"
echo ""
echo "Test the function with:"
echo "  aws lambda invoke --function-name $FUNCTION_NAME --payload '{}' response.json --region $REGION"
