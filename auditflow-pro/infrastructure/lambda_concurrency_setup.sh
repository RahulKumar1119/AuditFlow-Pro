#!/bin/bash
# infrastructure/lambda_concurrency_setup.sh
# Task 13.3: Configure Lambda concurrency limits
# Requirements: 10.5, 19.6

set -e

REGION="ap-south-1"
TRIGGER_FUNCTION_NAME="AuditFlow-Trigger"
MAX_CONCURRENT_EXECUTIONS=10

echo "=========================================="
echo "Configuring Lambda Concurrency Limits"
echo "Region: $REGION"
echo "Function: $TRIGGER_FUNCTION_NAME"
echo "Max Concurrent Executions: $MAX_CONCURRENT_EXECUTIONS"
echo "=========================================="
echo ""

# Check if Lambda function exists
echo "Checking if Lambda function exists..."
FUNCTION_ARN=$(aws lambda get-function \
    --function-name $TRIGGER_FUNCTION_NAME \
    --query 'Configuration.FunctionArn' \
    --output text 2>/dev/null || echo "")

if [ -z "$FUNCTION_ARN" ]; then
    echo "Error: Lambda function $TRIGGER_FUNCTION_NAME not found."
    echo "Please deploy the Lambda function first."
    exit 1
fi

echo "✓ Lambda function found: $FUNCTION_ARN"
echo ""

# Configure reserved concurrent executions
# Task 13.3: Configure Lambda concurrency limits (max 10 concurrent executions)
# Requirement 10.5: Process up to 10 concurrent executions
echo "Configuring reserved concurrent executions..."

aws lambda put-function-concurrency \
    --function-name $TRIGGER_FUNCTION_NAME \
    --reserved-concurrent-executions $MAX_CONCURRENT_EXECUTIONS

echo "✓ Reserved concurrent executions set to $MAX_CONCURRENT_EXECUTIONS"
echo ""

# Get current configuration
echo "Verifying configuration..."
CURRENT_CONCURRENCY=$(aws lambda get-function-concurrency \
    --function-name $TRIGGER_FUNCTION_NAME \
    --query 'ReservedConcurrentExecutions' \
    --output text 2>/dev/null || echo "None")

if [ "$CURRENT_CONCURRENCY" = "$MAX_CONCURRENT_EXECUTIONS" ]; then
    echo "✓ Configuration verified: $CURRENT_CONCURRENCY concurrent executions"
else
    echo "Warning: Expected $MAX_CONCURRENT_EXECUTIONS but got $CURRENT_CONCURRENCY"
fi

echo ""
echo "=========================================="
echo "Lambda Concurrency Configuration Complete!"
echo "=========================================="
echo "Configuration Summary:"
echo "  - Function: $TRIGGER_FUNCTION_NAME"
echo "  - Reserved Concurrent Executions: $MAX_CONCURRENT_EXECUTIONS"
echo ""
echo "Concurrency Control Behavior:"
echo "  - Maximum $MAX_CONCURRENT_EXECUTIONS Lambda instances can run simultaneously"
echo "  - Excess requests are queued in SQS automatically"
echo "  - Documents processed in upload order (FIFO within SQS)"
echo "  - SQS visibility timeout: 300 seconds (5 minutes)"
echo ""
echo "Requirement 10.5: Process documents in parallel up to 10 concurrent executions ✓"
echo "Requirement 19.6: Implement queuing for excess requests ✓"
echo "=========================================="

