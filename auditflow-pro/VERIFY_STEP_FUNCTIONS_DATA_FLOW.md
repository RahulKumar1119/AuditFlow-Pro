# Verify Step Functions Data Flow - Complete Guide

**Goal:** Verify that Step Functions is correctly passing `extracted_data` from Extractor to Validator

**Time Required:** 15-30 minutes

---

## Method 1: Check Step Functions Execution History (AWS Console)

### Step 1: Open Step Functions Console

1. Go to **AWS Console** → Search for **Step Functions**
2. Click **Step Functions** service
3. Click **State Machines** in left sidebar
4. Find your state machine (e.g., `AuditFlow-DocumentProcessing`)

### Step 2: View Recent Executions

1. Click on the state machine name
2. Scroll down to **Executions** section
3. Click on the most recent execution (or upload a test PDF first)

### Step 3: Examine Execution Flow

1. You'll see a visual diagram of the workflow
2. Click on each state to see its input/output:
   - **Trigger** → **Classifier** → **Extractor** → **Validator** → **Reporter**

### Step 4: Check Extractor Output

1. Click on the **Extractor** state in the diagram
2. Look for the **Output** tab
3. **Expected output should include:**
   ```json
   {
     "document_id": "doc-123",
     "document_type": "W2",
     "extracted_data": {
       "employee_name": {
         "value": "John Doe",
         "confidence": 0.95
       }
     },
     "processing_status": "COMPLETED"
   }
   ```

### Step 5: Check Validator Input

1. Click on the **Validator** state in the diagram
2. Look for the **Input** tab
3. **Expected input should include:**
   ```json
   {
     "documents": [
       {
         "document_id": "doc-123",
         "document_type": "W2",
         "extracted_data": {
           "employee_name": {
             "value": "John Doe",
             "confidence": 0.95
           }
         }
       }
     ]
   }
   ```

### ✅ Success Criteria

- ✓ Extractor output has `extracted_data` field
- ✓ Validator input has `extracted_data` field in documents
- ✓ `extracted_data` contains `employee_name` with value and confidence

### ❌ Failure Indicators

- ✗ Extractor output missing `extracted_data` field
- ✗ Validator input missing `extracted_data` field
- ✗ `extracted_data` is empty or null
- ✗ `employee_name` is missing from `extracted_data`

---

## Method 2: Use AWS CLI to Check Execution Details

### Step 1: List Recent Executions

```bash
# Get the state machine ARN first
STATE_MACHINE_ARN="arn:aws:states:ap-south-1:ACCOUNT_ID:stateMachine:AuditFlow-DocumentProcessing"

# List recent executions
aws stepfunctions list-executions \
  --state-machine-arn $STATE_MACHINE_ARN \
  --status-filter SUCCEEDED \
  --max-items 5 \
  --query 'executions[0]'
```

**Output:**
```json
{
  "executionArn": "arn:aws:states:ap-south-1:...:execution:...",
  "name": "loan-123-doc-456",
  "status": "SUCCEEDED",
  "startDate": "2026-03-22T10:00:00Z",
  "stopDate": "2026-03-22T10:05:00Z"
}
```

### Step 2: Get Execution History

```bash
EXECUTION_ARN="arn:aws:states:ap-south-1:...:execution:..."

# Get full execution history
aws stepfunctions get-execution-history \
  --execution-arn $EXECUTION_ARN \
  --query 'events[*].[type,stateEnteredEventDetails.name,executionFailedEventDetails.error]'
```

**Output shows each state:**
```
TaskStateEntered    Extractor
TaskSucceeded       Extractor
TaskStateEntered    Validator
TaskSucceeded       Validator
...
```

### Step 3: Get Specific State Output

```bash
# Get full execution history with details
aws stepfunctions get-execution-history \
  --execution-arn $EXECUTION_ARN \
  --max-items 100 > execution_history.json

# View the file
cat execution_history.json | jq '.events[] | select(.type=="TaskSucceeded" and .stateExitedEventDetails.name=="Extractor")'
```

**Look for:**
```json
{
  "type": "TaskSucceeded",
  "stateExitedEventDetails": {
    "name": "Extractor",
    "output": "{\"document_id\":\"doc-123\",\"extracted_data\":{...}}"
  }
}
```

### Step 4: Parse and Verify Output

```bash
# Extract Extractor output
EXTRACTOR_OUTPUT=$(cat execution_history.json | jq -r '.events[] | select(.type=="TaskSucceeded" and .stateExitedEventDetails.name=="Extractor") | .stateExitedEventDetails.output' | head -1)

# Parse JSON
echo $EXTRACTOR_OUTPUT | jq '.'

# Check for extracted_data
echo $EXTRACTOR_OUTPUT | jq '.extracted_data'

# Check for employee_name
echo $EXTRACTOR_OUTPUT | jq '.extracted_data.employee_name'
```

### ✅ Success Criteria

```bash
# Should return non-empty extracted_data
echo $EXTRACTOR_OUTPUT | jq '.extracted_data | length'
# Output: > 0

# Should return employee_name with value
echo $EXTRACTOR_OUTPUT | jq '.extracted_data.employee_name.value'
# Output: "John Doe"
```

---

## Method 3: Check CloudWatch Logs for Data Flow

### Step 1: Check Extractor Logs

```bash
# Search for extraction messages
aws logs filter-log-events \
  --log-group-name /aws/lambda/AuditFlow-DataExtractor \
  --filter-pattern "Extracted employee_name" \
  --start-time $(date -d '1 hour ago' +%s)000 \
  --query 'events[*].message'
```

**Expected output:**
```
[INFO] Extracted employee_name: John Doe (confidence: 0.95)
[INFO] Starting extraction: document_id=doc-123, document_type=W2
```

### Step 2: Check Validator Logs

```bash
# Search for name extraction in validator
aws logs filter-log-events \
  --log-group-name /aws/lambda/AuditFlow-DocumentValidator \
  --filter-pattern "Extracted name" \
  --start-time $(date -d '1 hour ago' +%s)000 \
  --query 'events[*].message'
```

**Expected output:**
```
[INFO] Extracted name 'John Doe' from document doc-123
[INFO] Golden Record generated with X fields
```

### Step 3: Check for Missing Data Errors

```bash
# Search for errors about missing extracted_data
aws logs filter-log-events \
  --log-group-name /aws/lambda/AuditFlow-DocumentValidator \
  --filter-pattern "No valid documents loaded" \
  --start-time $(date -d '1 hour ago' +%s)000 \
  --query 'events[*].message'
```

**If you see this, it means extracted_data is not being passed:**
```
[ERROR] No valid documents loaded for loan application loan-123
[WARNING] Document doc-123 has no extracted data
```

### ✅ Success Criteria

- ✓ Extractor logs show "Extracted employee_name"
- ✓ Validator logs show "Extracted name"
- ✓ No errors about missing extracted_data
- ✓ Golden Record logs show fields were generated

### ❌ Failure Indicators

- ✗ Extractor logs missing extraction messages
- ✗ Validator logs show "No valid documents loaded"
- ✗ Validator logs show "has no extracted data"
- ✗ No "Extracted name" messages in validator logs

---

## Method 4: Upload Test PDF and Monitor

### Step 1: Prepare Test PDF

Create a simple test W2 PDF with:
- Employee Name: "TEST USER"
- Employer: "TEST COMPANY"
- Wages: "50000"

Or use an existing W2 PDF.

### Step 2: Upload to S3

```bash
# Upload test PDF
aws s3 cp test-w2.pdf s3://your-bucket/uploads/loan-test-001/w2.pdf

# Note the loan ID: loan-test-001
```

### Step 3: Monitor Step Functions Execution

```bash
# Wait 5 seconds for processing to start
sleep 5

# Get the execution
EXECUTION=$(aws stepfunctions list-executions \
  --state-machine-arn $STATE_MACHINE_ARN \
  --status-filter RUNNING \
  --max-items 1 \
  --query 'executions[0].executionArn' \
  --output text)

# Monitor execution
while true; do
  STATUS=$(aws stepfunctions describe-execution \
    --execution-arn $EXECUTION \
    --query 'status' \
    --output text)
  
  echo "Status: $STATUS"
  
  if [ "$STATUS" = "SUCCEEDED" ] || [ "$STATUS" = "FAILED" ]; then
    break
  fi
  
  sleep 2
done
```

### Step 4: Check Execution Results

```bash
# Get execution history
aws stepfunctions get-execution-history \
  --execution-arn $EXECUTION \
  --max-items 100 > test_execution.json

# Check Extractor output
cat test_execution.json | jq '.events[] | select(.type=="TaskSucceeded" and .stateExitedEventDetails.name=="Extractor") | .stateExitedEventDetails.output' | jq '.'

# Check Validator output
cat test_execution.json | jq '.events[] | select(.type=="TaskSucceeded" and .stateExitedEventDetails.name=="Validator") | .stateExitedEventDetails.output' | jq '.golden_record.name'
```

### Step 5: Check DynamoDB for Audit Record

```bash
# Query audit records for your test
aws dynamodb scan \
  --table-name AuditFlow-AuditRecords \
  --filter-expression "loan_application_id = :loan_id" \
  --expression-attribute-values '{":loan_id":{"S":"loan-test-001"}}' \
  --query 'Items[0]'
```

**Expected output:**
```json
{
  "applicant_name": {"S": "TEST USER"},
  "golden_record": {
    "M": {
      "name": {
        "M": {
          "value": {"S": "TEST USER"},
          "confidence": {"N": "0.95"}
        }
      }
    }
  }
}
```

### ✅ Success Criteria

- ✓ Execution completes successfully
- ✓ Extractor output has `extracted_data`
- ✓ Validator output has `golden_record.name`
- ✓ DynamoDB record has `applicant_name` populated
- ✓ `applicant_name` matches the extracted name

---

## Method 5: Create Automated Verification Script

### Step 1: Create Verification Script

```bash
#!/bin/bash
# verify_step_functions_data_flow.sh

set -e

STATE_MACHINE_ARN="arn:aws:states:ap-south-1:ACCOUNT_ID:stateMachine:AuditFlow-DocumentProcessing"
LOAN_ID="loan-verify-$(date +%s)"

echo "=========================================="
echo "Step Functions Data Flow Verification"
echo "=========================================="
echo ""

# Step 1: Upload test PDF
echo "[1/5] Uploading test PDF..."
aws s3 cp test-w2.pdf s3://your-bucket/uploads/$LOAN_ID/w2.pdf
echo "✓ PDF uploaded to s3://your-bucket/uploads/$LOAN_ID/w2.pdf"
echo ""

# Step 2: Wait for execution to start
echo "[2/5] Waiting for execution to start..."
sleep 5

# Step 3: Get execution
echo "[3/5] Getting execution details..."
EXECUTION=$(aws stepfunctions list-executions \
  --state-machine-arn $STATE_MACHINE_ARN \
  --status-filter RUNNING \
  --max-items 1 \
  --query 'executions[0].executionArn' \
  --output text)

if [ -z "$EXECUTION" ] || [ "$EXECUTION" = "None" ]; then
  echo "✗ No running execution found"
  exit 1
fi

echo "✓ Execution: $EXECUTION"
echo ""

# Step 4: Wait for completion
echo "[4/5] Waiting for execution to complete..."
while true; do
  STATUS=$(aws stepfunctions describe-execution \
    --execution-arn $EXECUTION \
    --query 'status' \
    --output text)
  
  if [ "$STATUS" = "SUCCEEDED" ]; then
    echo "✓ Execution succeeded"
    break
  elif [ "$STATUS" = "FAILED" ]; then
    echo "✗ Execution failed"
    exit 1
  fi
  
  sleep 2
done
echo ""

# Step 5: Verify data flow
echo "[5/5] Verifying data flow..."

# Get execution history
aws stepfunctions get-execution-history \
  --execution-arn $EXECUTION \
  --max-items 100 > /tmp/execution_history.json

# Check Extractor output
EXTRACTOR_OUTPUT=$(cat /tmp/execution_history.json | jq -r '.events[] | select(.type=="TaskSucceeded" and .stateExitedEventDetails.name=="Extractor") | .stateExitedEventDetails.output' | head -1)

if [ -z "$EXTRACTOR_OUTPUT" ]; then
  echo "✗ No Extractor output found"
  exit 1
fi

# Check for extracted_data
EXTRACTED_DATA=$(echo $EXTRACTOR_OUTPUT | jq '.extracted_data')

if [ "$EXTRACTED_DATA" = "null" ] || [ -z "$EXTRACTED_DATA" ]; then
  echo "✗ Extractor output missing extracted_data"
  exit 1
fi

echo "✓ Extractor output has extracted_data"

# Check for employee_name
EMPLOYEE_NAME=$(echo $EXTRACTOR_OUTPUT | jq -r '.extracted_data.employee_name.value // empty')

if [ -z "$EMPLOYEE_NAME" ]; then
  echo "✗ Extractor output missing employee_name"
  exit 1
fi

echo "✓ Extractor extracted employee_name: $EMPLOYEE_NAME"

# Check Validator input
VALIDATOR_INPUT=$(cat /tmp/execution_history.json | jq -r '.events[] | select(.type=="TaskStateEntered" and .stateEnteredEventDetails.name=="Validator") | .stateEnteredEventDetails.input' | head -1)

if [ -z "$VALIDATOR_INPUT" ]; then
  echo "✗ No Validator input found"
  exit 1
fi

# Check if Validator received extracted_data
VALIDATOR_EXTRACTED_DATA=$(echo $VALIDATOR_INPUT | jq '.documents[0].extracted_data // empty')

if [ -z "$VALIDATOR_EXTRACTED_DATA" ] || [ "$VALIDATOR_EXTRACTED_DATA" = "null" ]; then
  echo "✗ Validator input missing extracted_data in documents"
  exit 1
fi

echo "✓ Validator received extracted_data in documents"

# Check DynamoDB for audit record
echo ""
echo "Checking DynamoDB for audit record..."

AUDIT_RECORD=$(aws dynamodb scan \
  --table-name AuditFlow-AuditRecords \
  --filter-expression "loan_application_id = :loan_id" \
  --expression-attribute-values "{\":loan_id\":{\"S\":\"$LOAN_ID\"}}" \
  --query 'Items[0]' 2>/dev/null || echo "{}")

APPLICANT_NAME=$(echo $AUDIT_RECORD | jq -r '.applicant_name.S // empty')

if [ -z "$APPLICANT_NAME" ]; then
  echo "✗ Audit record missing applicant_name"
  exit 1
fi

echo "✓ Audit record has applicant_name: $APPLICANT_NAME"

echo ""
echo "=========================================="
echo "✓ ALL CHECKS PASSED"
echo "=========================================="
echo ""
echo "Summary:"
echo "  - Extractor returned extracted_data"
echo "  - Extractor extracted employee_name: $EMPLOYEE_NAME"
echo "  - Validator received extracted_data"
echo "  - Audit record has applicant_name: $APPLICANT_NAME"
echo ""
```

### Step 2: Run Verification Script

```bash
chmod +x verify_step_functions_data_flow.sh
./verify_step_functions_data_flow.sh
```

**Expected output:**
```
==========================================
Step Functions Data Flow Verification
==========================================

[1/5] Uploading test PDF...
✓ PDF uploaded to s3://your-bucket/uploads/loan-verify-1711100000/w2.pdf

[2/5] Waiting for execution to start...

[3/5] Getting execution details...
✓ Execution: arn:aws:states:ap-south-1:...:execution:...

[4/5] Waiting for execution to complete...
✓ Execution succeeded

[5/5] Verifying data flow...
✓ Extractor output has extracted_data
✓ Extractor extracted employee_name: TEST USER
✓ Validator received extracted_data in documents
✓ Audit record has applicant_name: TEST USER

==========================================
✓ ALL CHECKS PASSED
==========================================
```

---

## Troubleshooting

### Issue: "No valid documents loaded" Error

**Cause:** Validator is not receiving `extracted_data`

**Solution:**
1. Check Step Functions state machine definition
2. Verify `ResultPath: "$.document"` is used in Extractor state
3. Ensure Validator state receives documents with `extracted_data`

### Issue: Extractor Output Missing `extracted_data`

**Cause:** Extractor Lambda is not returning `extracted_data`

**Solution:**
1. Check Extractor Lambda logs for errors
2. Verify Textract is successfully extracting data
3. Check for low confidence scores that might skip extraction

### Issue: Validator Logs Show "Insufficient names for validation"

**Cause:** Only one document or no names extracted

**Solution:**
1. Upload multiple documents with names
2. Check if PDF quality is good enough for Textract
3. Verify document type is correctly classified

### Issue: DynamoDB Record Missing `applicant_name`

**Cause:** Reporter Lambda not receiving golden record

**Solution:**
1. Check Reporter Lambda logs
2. Verify Validator is returning golden record
3. Check IAM permissions for DynamoDB write

---

## Quick Verification Checklist

Use this checklist to quickly verify data flow:

```
Step Functions Data Flow Verification Checklist
================================================

□ Step 1: Check Extractor Output
  □ Extractor state has output
  □ Output includes extracted_data field
  □ extracted_data has employee_name
  □ employee_name has value and confidence

□ Step 2: Check Validator Input
  □ Validator state has input
  □ Input includes documents array
  □ documents[0] has extracted_data field
  □ extracted_data matches Extractor output

□ Step 3: Check Validator Output
  □ Validator state has output
  □ Output includes golden_record
  □ golden_record has name field
  □ name field has value and confidence

□ Step 4: Check CloudWatch Logs
  □ Extractor logs show "Extracted employee_name"
  □ Validator logs show "Extracted name"
  □ No errors about missing extracted_data
  □ Reporter logs show applicant_name

□ Step 5: Check DynamoDB
  □ Audit record exists
  □ applicant_name field is populated
  □ applicant_name matches extracted name
  □ golden_record.name.value is populated

Result: ✓ PASS or ✗ FAIL
```

---

## Summary

To verify Step Functions is passing data correctly:

1. **Console Method** - View execution history in AWS Console (easiest)
2. **CLI Method** - Use AWS CLI to get execution details
3. **Logs Method** - Check CloudWatch logs for data flow
4. **Test Method** - Upload test PDF and monitor
5. **Script Method** - Run automated verification script

**All methods should show:**
- ✓ Extractor returns `extracted_data`
- ✓ Validator receives `extracted_data`
- ✓ Golden record has applicant name
- ✓ Audit record has applicant name

If any step fails, check the troubleshooting section for solutions.

