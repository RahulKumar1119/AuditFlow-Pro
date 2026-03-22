# Quick Verification Commands - Copy & Paste Ready

**Use these commands to quickly verify Step Functions data flow**

---

## 1. Get State Machine ARN

```bash
# Replace with your AWS account ID and region
STATE_MACHINE_ARN="arn:aws:states:ap-south-1:YOUR_ACCOUNT_ID:stateMachine:AuditFlow-DocumentProcessing"

# Or find it automatically
STATE_MACHINE_ARN=$(aws stepfunctions list-state-machines \
  --query 'stateMachines[?name==`AuditFlow-DocumentProcessing`].stateMachineArn' \
  --output text)

echo "State Machine ARN: $STATE_MACHINE_ARN"
```

---

## 2. Get Most Recent Successful Execution

```bash
EXECUTION_ARN=$(aws stepfunctions list-executions \
  --state-machine-arn $STATE_MACHINE_ARN \
  --status-filter SUCCEEDED \
  --max-items 1 \
  --query 'executions[0].executionArn' \
  --output text)

echo "Execution ARN: $EXECUTION_ARN"
```

---

## 3. Get Execution History

```bash
aws stepfunctions get-execution-history \
  --execution-arn $EXECUTION_ARN \
  --max-items 100 > execution_history.json

echo "Execution history saved to execution_history.json"
```

---

## 4. Check Extractor Output (Has extracted_data?)

```bash
# Extract the Extractor output
EXTRACTOR_OUTPUT=$(cat execution_history.json | jq -r '.events[] | select(.type=="TaskSucceeded" and .stateExitedEventDetails.name=="Extractor") | .stateExitedEventDetails.output' | head -1)

# Display it
echo "=== EXTRACTOR OUTPUT ==="
echo $EXTRACTOR_OUTPUT | jq '.'

# Check for extracted_data
echo ""
echo "=== EXTRACTED DATA ==="
echo $EXTRACTOR_OUTPUT | jq '.extracted_data'

# Check for employee_name
echo ""
echo "=== EMPLOYEE NAME ==="
echo $EXTRACTOR_OUTPUT | jq '.extracted_data.employee_name'
```

---

## 5. Check Validator Input (Received extracted_data?)

```bash
# Extract the Validator input
VALIDATOR_INPUT=$(cat execution_history.json | jq -r '.events[] | select(.type=="TaskStateEntered" and .stateEnteredEventDetails.name=="Validator") | .stateEnteredEventDetails.input' | head -1)

# Display it
echo "=== VALIDATOR INPUT ==="
echo $VALIDATOR_INPUT | jq '.'

# Check for extracted_data in documents
echo ""
echo "=== EXTRACTED DATA IN DOCUMENTS ==="
echo $VALIDATOR_INPUT | jq '.documents[0].extracted_data'
```

---

## 6. Check Validator Output (Golden record with name?)

```bash
# Extract the Validator output
VALIDATOR_OUTPUT=$(cat execution_history.json | jq -r '.events[] | select(.type=="TaskSucceeded" and .stateExitedEventDetails.name=="Validator") | .stateExitedEventDetails.output' | head -1)

# Display it
echo "=== VALIDATOR OUTPUT ==="
echo $VALIDATOR_OUTPUT | jq '.'

# Check for golden_record
echo ""
echo "=== GOLDEN RECORD ==="
echo $VALIDATOR_OUTPUT | jq '.golden_record'

# Check for name field
echo ""
echo "=== NAME FIELD ==="
echo $VALIDATOR_OUTPUT | jq '.golden_record.name'
```

---

## 7. Check CloudWatch Logs - Extractor

```bash
# Check for extraction messages
aws logs filter-log-events \
  --log-group-name /aws/lambda/AuditFlow-DataExtractor \
  --filter-pattern "Extracted employee_name" \
  --start-time $(date -d '1 hour ago' +%s)000 \
  --query 'events[*].message' \
  --output text
```

---

## 8. Check CloudWatch Logs - Validator

```bash
# Check for name extraction
aws logs filter-log-events \
  --log-group-name /aws/lambda/AuditFlow-DocumentValidator \
  --filter-pattern "Extracted name" \
  --start-time $(date -d '1 hour ago' +%s)000 \
  --query 'events[*].message' \
  --output text
```

---

## 9. Check CloudWatch Logs - Errors

```bash
# Check for missing extracted_data errors
aws logs filter-log-events \
  --log-group-name /aws/lambda/AuditFlow-DocumentValidator \
  --filter-pattern "No valid documents loaded" \
  --start-time $(date -d '1 hour ago' +%s)000 \
  --query 'events[*].message' \
  --output text
```

---

## 10. Check DynamoDB for Audit Record

```bash
# Get the loan ID from the execution name
LOAN_ID=$(aws stepfunctions describe-execution \
  --execution-arn $EXECUTION_ARN \
  --query 'name' \
  --output text | cut -d'-' -f1-2)

echo "Loan ID: $LOAN_ID"

# Query DynamoDB
aws dynamodb scan \
  --table-name AuditFlow-AuditRecords \
  --filter-expression "loan_application_id = :loan_id" \
  --expression-attribute-values "{\":loan_id\":{\"S\":\"$LOAN_ID\"}}" \
  --query 'Items[0]' \
  --output json | jq '.'

# Check applicant_name
echo ""
echo "=== APPLICANT NAME ==="
aws dynamodb scan \
  --table-name AuditFlow-AuditRecords \
  --filter-expression "loan_application_id = :loan_id" \
  --expression-attribute-values "{\":loan_id\":{\"S\":\"$LOAN_ID\"}}" \
  --query 'Items[0].applicant_name.S' \
  --output text
```

---

## 11. Upload Test PDF and Monitor

```bash
# Set test loan ID
TEST_LOAN_ID="loan-test-$(date +%s)"

# Upload test PDF
aws s3 cp test-w2.pdf s3://your-bucket/uploads/$TEST_LOAN_ID/w2.pdf

echo "Uploaded to: s3://your-bucket/uploads/$TEST_LOAN_ID/w2.pdf"
echo "Loan ID: $TEST_LOAN_ID"

# Wait for execution
sleep 5

# Get running execution
EXECUTION_ARN=$(aws stepfunctions list-executions \
  --state-machine-arn $STATE_MACHINE_ARN \
  --status-filter RUNNING \
  --max-items 1 \
  --query 'executions[0].executionArn' \
  --output text)

echo "Execution: $EXECUTION_ARN"

# Wait for completion
while true; do
  STATUS=$(aws stepfunctions describe-execution \
    --execution-arn $EXECUTION_ARN \
    --query 'status' \
    --output text)
  
  echo "Status: $STATUS"
  
  if [ "$STATUS" = "SUCCEEDED" ] || [ "$STATUS" = "FAILED" ]; then
    break
  fi
  
  sleep 2
done
```

---

## 12. All-in-One Verification Script

```bash
#!/bin/bash
# Copy this entire script and run it

echo "=========================================="
echo "Step Functions Data Flow Verification"
echo "=========================================="
echo ""

# Get state machine
STATE_MACHINE_ARN=$(aws stepfunctions list-state-machines \
  --query 'stateMachines[?name==`AuditFlow-DocumentProcessing`].stateMachineArn' \
  --output text)

echo "State Machine: $STATE_MACHINE_ARN"
echo ""

# Get execution
EXECUTION_ARN=$(aws stepfunctions list-executions \
  --state-machine-arn $STATE_MACHINE_ARN \
  --status-filter SUCCEEDED \
  --max-items 1 \
  --query 'executions[0].executionArn' \
  --output text)

echo "Execution: $EXECUTION_ARN"
echo ""

# Get history
aws stepfunctions get-execution-history \
  --execution-arn $EXECUTION_ARN \
  --max-items 100 > /tmp/execution_history.json

# Check Extractor
echo "=== EXTRACTOR OUTPUT ==="
EXTRACTOR_OUTPUT=$(cat /tmp/execution_history.json | jq -r '.events[] | select(.type=="TaskSucceeded" and .stateExitedEventDetails.name=="Extractor") | .stateExitedEventDetails.output' | head -1)

if [ -z "$EXTRACTOR_OUTPUT" ]; then
  echo "✗ No Extractor output found"
else
  echo "✓ Extractor output found"
  echo "  - Has extracted_data: $(echo $EXTRACTOR_OUTPUT | jq 'has("extracted_data")')"
  echo "  - Employee name: $(echo $EXTRACTOR_OUTPUT | jq -r '.extracted_data.employee_name.value // "NOT FOUND"')"
fi

echo ""

# Check Validator
echo "=== VALIDATOR INPUT ==="
VALIDATOR_INPUT=$(cat /tmp/execution_history.json | jq -r '.events[] | select(.type=="TaskStateEntered" and .stateEnteredEventDetails.name=="Validator") | .stateEnteredEventDetails.input' | head -1)

if [ -z "$VALIDATOR_INPUT" ]; then
  echo "✗ No Validator input found"
else
  echo "✓ Validator input found"
  echo "  - Has documents: $(echo $VALIDATOR_INPUT | jq 'has("documents")')"
  echo "  - Has extracted_data: $(echo $VALIDATOR_INPUT | jq '.documents[0] | has("extracted_data")')"
fi

echo ""

# Check Validator Output
echo "=== VALIDATOR OUTPUT ==="
VALIDATOR_OUTPUT=$(cat /tmp/execution_history.json | jq -r '.events[] | select(.type=="TaskSucceeded" and .stateExitedEventDetails.name=="Validator") | .stateExitedEventDetails.output' | head -1)

if [ -z "$VALIDATOR_OUTPUT" ]; then
  echo "✗ No Validator output found"
else
  echo "✓ Validator output found"
  echo "  - Has golden_record: $(echo $VALIDATOR_OUTPUT | jq 'has("golden_record")')"
  echo "  - Has name field: $(echo $VALIDATOR_OUTPUT | jq '.golden_record | has("name")')"
  echo "  - Applicant name: $(echo $VALIDATOR_OUTPUT | jq -r '.golden_record.name.value // "NOT FOUND"')"
fi

echo ""
echo "=========================================="
```

---

## Quick Verification Checklist

```bash
# 1. Extractor has extracted_data?
echo $EXTRACTOR_OUTPUT | jq 'has("extracted_data")'
# Expected: true

# 2. Extractor has employee_name?
echo $EXTRACTOR_OUTPUT | jq '.extracted_data | has("employee_name")'
# Expected: true

# 3. Validator received extracted_data?
echo $VALIDATOR_INPUT | jq '.documents[0] | has("extracted_data")'
# Expected: true

# 4. Validator generated golden_record?
echo $VALIDATOR_OUTPUT | jq '.golden_record | has("name")'
# Expected: true

# 5. Golden record has applicant name?
echo $VALIDATOR_OUTPUT | jq '.golden_record.name.value'
# Expected: "John Doe" (or whatever name was extracted)
```

---

## Troubleshooting Commands

### If Extractor output missing extracted_data:

```bash
# Check Extractor logs for errors
aws logs filter-log-events \
  --log-group-name /aws/lambda/AuditFlow-DataExtractor \
  --filter-pattern "error" \
  --start-time $(date -d '1 hour ago' +%s)000 \
  --query 'events[*].message'
```

### If Validator shows "No valid documents loaded":

```bash
# Check Validator logs
aws logs filter-log-events \
  --log-group-name /aws/lambda/AuditFlow-DocumentValidator \
  --filter-pattern "No valid documents" \
  --start-time $(date -d '1 hour ago' +%s)000 \
  --query 'events[*].message'
```

### If DynamoDB missing applicant_name:

```bash
# Check Reporter logs
aws logs filter-log-events \
  --log-group-name /aws/lambda/AuditFlow-ReportGenerator \
  --filter-pattern "applicant_name" \
  --start-time $(date -d '1 hour ago' +%s)000 \
  --query 'events[*].message'
```

---

## Save These Commands

```bash
# Create a file with all commands
cat > verify_commands.sh << 'EOF'
# Paste all commands here
EOF

chmod +x verify_commands.sh
./verify_commands.sh
```

