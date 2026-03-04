#!/bin/bash
# Verify all Lambda functions and Step Functions are deployed correctly

REGION="ap-south-1"

echo "=========================================="
echo "Verifying Deployments"
echo "=========================================="
echo ""

# Check Classifier Lambda
echo "1. Checking Classifier Lambda..."
aws lambda get-function --function-name AuditFlow-Classifier --region $REGION --query 'Configuration.LastModified' --output text
echo ""

# Check Extractor Lambda
echo "2. Checking Extractor Lambda..."
aws lambda get-function --function-name AuditFlow-Extractor --region $REGION --query 'Configuration.LastModified' --output text
echo ""

# Check Validator Lambda
echo "3. Checking Validator Lambda..."
aws lambda get-function --function-name AuditFlow-Validator --region $REGION --query 'Configuration.LastModified' --output text
echo ""

# Check Step Functions State Machine
echo "4. Checking Step Functions State Machine..."
STATE_MACHINE_ARN=$(aws stepfunctions list-state-machines --region $REGION --query "stateMachines[?name=='AuditFlowDocumentProcessing'].stateMachineArn" --output text)
if [ -n "$STATE_MACHINE_ARN" ]; then
    echo "State Machine ARN: $STATE_MACHINE_ARN"
    aws stepfunctions describe-state-machine --state-machine-arn "$STATE_MACHINE_ARN" --region $REGION --query 'updateDate' --output text
else
    echo "State Machine not found!"
fi

echo ""
echo "=========================================="
echo "Verification Complete"
echo "=========================================="
