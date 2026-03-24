#!/bin/bash
################################################################################
# Step Functions Verification - One-Liner Commands
# 
# Quick CLI commands to verify Step Functions data flow for Unknown Applicant issue
################################################################################

# ============================================================================
# QUICK VERIFICATION (Copy & Paste)
# ============================================================================

# 1. Get State Machine ARN
STATE_MACHINE_ARN=$(aws stepfunctions list-state-machines \
  --query 'stateMachines[?name==`AuditFlowDocumentProcessing`].stateMachineArn' \
  --output text | tr -d ' ')

echo "State Machine: $STATE_MACHINE_ARN"

# 2. Get Recent Execution
EXECUTION_ARN=$(aws stepfunctions list-executions \
  --state-machine-arn $STATE_MACHINE_ARN \
  --status-filter SUCCEEDED \
  --query 'executions[0].executionArn' \
  --output text | tr -d ' ')

echo "Execution: $EXECUTION_ARN"

# 3. Get Execution History
aws stepfunctions get-execution-history \
  --execution-arn $EXECUTION_ARN > /tmp/execution_history.json

# ============================================================================
# VERIFICATION CHECKS
# ============================================================================

# CHECK 1: Extractor has extracted_data?
echo ""
echo "=== CHECK 1: ExtractData Output ==="
EXTRACTOR_OUTPUT=$(cat /tmp/execution_history.json | jq -r '.events[] | select(.type=="TaskSucceeded") | .taskSucceededEventDetails.output' | sed -n '2p' | jq -r '.Payload')

if echo $EXTRACTOR_OUTPUT | jq 'has("extracted_data")' | grep -q true; then
  echo "✓ ExtractData has extracted_data"
  echo "  Full Name: $(echo $EXTRACTOR_OUTPUT | jq -r '.extracted_data.full_name.value // "NOT FOUND"')"
else
  echo "✗ ExtractData MISSING extracted_data"
fi

# CHECK 2: Validator received extracted_data?
echo ""
echo "=== CHECK 2: ValidateDocuments Input ==="
VALIDATOR_INPUT=$(cat /tmp/execution_history.json | jq -r '.events[] | select(.type=="TaskStateEntered" and .stateEnteredEventDetails.name=="ValidateDocuments") | .stateEnteredEventDetails.input' | head -1)

if echo $VALIDATOR_INPUT | jq '.processed_documents[0] | has("extracted_data")' | grep -q true; then
  echo "✓ ValidateDocuments received extracted_data"
else
  echo "✗ ValidateDocuments MISSING extracted_data"
  echo "  PROBLEM: Step Functions not passing data!"
fi

# CHECK 3: Validator generated golden_record?
echo ""
echo "=== CHECK 3: ValidateDocuments Output ==="
VALIDATOR_OUTPUT=$(cat /tmp/execution_history.json | jq -r '.events[] | select(.type=="TaskSucceeded") | .taskSucceededEventDetails.output' | sed -n '4p' | jq -r '.Payload')

if echo $VALIDATOR_OUTPUT | jq '.golden_record | has("name")' | grep -q true; then
  echo "✓ ValidateDocuments generated golden_record with name"
  echo "  Applicant Name: $(echo $VALIDATOR_OUTPUT | jq -r '.golden_record.name.value // "NOT FOUND"')"
else
  echo "✗ ValidateDocuments MISSING golden_record.name"
fi

# ============================================================================
# FULL VERIFICATION SUMMARY
# ============================================================================

echo ""
echo "=== FULL VERIFICATION SUMMARY ==="

# Count checks
CHECKS_PASSED=0

if echo $EXTRACTOR_OUTPUT | jq 'has("extracted_data")' | grep -q true; then
  CHECKS_PASSED=$((CHECKS_PASSED + 1))
fi

if echo $VALIDATOR_INPUT | jq '.processed_documents[0] | has("extracted_data")' | grep -q true; then
  CHECKS_PASSED=$((CHECKS_PASSED + 1))
fi

if echo $VALIDATOR_OUTPUT | jq '.golden_record | has("name")' | grep -q true; then
  CHECKS_PASSED=$((CHECKS_PASSED + 1))
fi

echo "Checks Passed: $CHECKS_PASSED/3"

if [ $CHECKS_PASSED -eq 3 ]; then
  echo "✓ ALL CHECKS PASSED - Data flow is correct!"
  echo "  Applicant names should display correctly"
else
  echo "✗ SOME CHECKS FAILED - Data flow has issues"
  echo "  Check Step Functions configuration"
fi

# ============================================================================
# ALTERNATIVE: Check CloudWatch Logs
# ============================================================================

echo ""
echo "=== CLOUDWATCH LOGS CHECK ==="

# Check Extractor logs
echo "Extractor logs:"
aws logs filter-log-events \
  --log-group-name /aws/lambda/AuditFlow-DataExtractor \
  --filter-pattern "Extracted employee_name" \
  --start-time $(date -d '1 hour ago' +%s)000 \
  --query 'events[*].message' \
  --output text | head -1

# Check Validator logs
echo ""
echo "Validator logs:"
aws logs filter-log-events \
  --log-group-name /aws/lambda/AuditFlow-DocumentValidator \
  --filter-pattern "Extracted name" \
  --start-time $(date -d '1 hour ago' +%s)000 \
  --query 'events[*].message' \
  --output text | head -1

# ============================================================================
# ALTERNATIVE: Check DynamoDB
# ============================================================================

echo ""
echo "=== DYNAMODB CHECK ==="

# Get loan ID from execution
LOAN_ID=$(echo $EXECUTION_ARN | grep -oP 'execution:\K[^-]+' | head -1)

echo "Checking DynamoDB for applicant_name..."
aws dynamodb scan \
  --table-name AuditFlow-AuditRecords \
  --filter-expression "loan_application_id = :loan_id" \
  --expression-attribute-values "{\":loan_id\":{\"S\":\"$LOAN_ID\"}}" \
  --query 'Items[0].applicant_name.S' \
  --output text

echo ""
