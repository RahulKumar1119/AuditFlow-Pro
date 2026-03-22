# How to Verify Step Functions Data Flow - Quick Start

**Goal:** Verify that Step Functions is passing `extracted_data` from Extractor to Validator

**Time:** 5-10 minutes

---

## The Simplest Way (AWS Console)

### Step 1: Open AWS Console

1. Go to **AWS Console**
2. Search for **Step Functions**
3. Click **Step Functions**

### Step 2: Find Your State Machine

1. Click **State Machines**
2. Find `AuditFlow-DocumentProcessing` (or similar)
3. Click on it

### Step 3: View Recent Execution

1. Scroll down to **Executions**
2. Click the most recent execution (or upload a test PDF first)

### Step 4: Check the Data Flow

You'll see a visual diagram. Click on each state:

**Extractor State:**
- Click on **Extractor** box
- Look for **Output** tab
- **Should see:** `"extracted_data": { "employee_name": { "value": "John Doe" } }`

**Validator State:**
- Click on **Validator** box
- Look for **Input** tab
- **Should see:** `"documents": [{ "extracted_data": { "employee_name": {...} } }]`

### ✓ Success

If both show `extracted_data`, then Step Functions is working correctly!

### ✗ Failure

If Validator input is missing `extracted_data`, then Step Functions is not configured correctly.

---

## Using AWS CLI (Copy & Paste)

### Step 1: Get State Machine ARN

```bash
STATE_MACHINE_ARN=$(aws stepfunctions list-state-machines \
  --query 'stateMachines[?name==`AuditFlow-DocumentProcessing`].stateMachineArn' \
  --output text)

echo $STATE_MACHINE_ARN
```

### Step 2: Get Recent Execution

```bash
EXECUTION_ARN=$(aws stepfunctions list-executions \
  --state-machine-arn $STATE_MACHINE_ARN \
  --status-filter SUCCEEDED \
  --max-items 1 \
  --query 'executions[0].executionArn' \
  --output text)

echo $EXECUTION_ARN
```

### Step 3: Get Execution History

```bash
aws stepfunctions get-execution-history \
  --execution-arn $EXECUTION_ARN \
  --max-items 100 > execution_history.json
```

### Step 4: Check Extractor Output

```bash
cat execution_history.json | jq '.events[] | select(.type=="TaskSucceeded" and .stateExitedEventDetails.name=="Extractor") | .stateExitedEventDetails.output' | jq '.'
```

**Look for:**
```json
{
  "extracted_data": {
    "employee_name": {
      "value": "John Doe",
      "confidence": 0.95
    }
  }
}
```

### Step 5: Check Validator Input

```bash
cat execution_history.json | jq '.events[] | select(.type=="TaskStateEntered" and .stateEnteredEventDetails.name=="Validator") | .stateEnteredEventDetails.input' | jq '.'
```

**Look for:**
```json
{
  "documents": [
    {
      "extracted_data": {
        "employee_name": {
          "value": "John Doe"
        }
      }
    }
  ]
}
```

### ✓ Success

If both outputs show `extracted_data`, everything is working!

### ✗ Failure

If Validator input is missing `extracted_data`, the Step Functions state machine needs to be fixed.

---

## What to Look For

### ✓ GOOD - Extractor Output

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

### ✓ GOOD - Validator Input

```json
{
  "loan_application_id": "loan-123",
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

### ✗ BAD - Validator Input (Missing extracted_data)

```json
{
  "loan_application_id": "loan-123",
  "documents": [
    {
      "document_id": "doc-123",
      "document_type": "W2"
      // ✗ Missing extracted_data!
    }
  ]
}
```

---

## Quick Checklist

```
□ Extractor output has extracted_data?
  └─ If NO: Check Extractor Lambda logs

□ Validator input has extracted_data?
  └─ If NO: Fix Step Functions state machine

□ Validator output has golden_record.name?
  └─ If NO: Check Validator Lambda logs

□ DynamoDB has applicant_name?
  └─ If NO: Check Reporter Lambda logs

□ applicant_name is not "Unknown Applicant"?
  └─ If NO: Check golden_record is being used
```

---

## If Something is Wrong

### Problem: Validator Input Missing `extracted_data`

**This is the most common issue.**

**Solution:**
1. Check Step Functions state machine definition
2. Look for the Extractor state
3. Verify it has: `"ResultPath": "$.document"`
4. This tells Step Functions to merge the output with the input

**Example Correct Configuration:**
```json
{
  "ExtractData": {
    "Type": "Task",
    "Resource": "arn:aws:lambda:...:function:AuditFlow-DataExtractor",
    "ResultPath": "$.document",
    "Next": "ValidateDocuments"
  }
}
```

### Problem: Extractor Output Missing `extracted_data`

**Check Extractor Lambda logs:**
```bash
aws logs filter-log-events \
  --log-group-name /aws/lambda/AuditFlow-DataExtractor \
  --filter-pattern "error" \
  --start-time $(date -d '1 hour ago' +%s)000
```

### Problem: Validator Logs Show "No valid documents loaded"

**This means extracted_data is not being passed.**

**Check Validator logs:**
```bash
aws logs filter-log-events \
  --log-group-name /aws/lambda/AuditFlow-DocumentValidator \
  --filter-pattern "No valid documents" \
  --start-time $(date -d '1 hour ago' +%s)000
```

---

## Test with Sample PDF

### Step 1: Upload Test PDF

```bash
TEST_LOAN_ID="loan-test-$(date +%s)"

aws s3 cp test-w2.pdf s3://your-bucket/uploads/$TEST_LOAN_ID/w2.pdf

echo "Uploaded to: s3://your-bucket/uploads/$TEST_LOAN_ID/w2.pdf"
```

### Step 2: Wait for Processing

```bash
sleep 10
```

### Step 3: Check Execution

```bash
# Get the execution
EXECUTION=$(aws stepfunctions list-executions \
  --state-machine-arn $STATE_MACHINE_ARN \
  --status-filter SUCCEEDED \
  --max-items 1 \
  --query 'executions[0].executionArn' \
  --output text)

# Get history
aws stepfunctions get-execution-history \
  --execution-arn $EXECUTION \
  --max-items 100 > test_execution.json

# Check Validator input
cat test_execution.json | jq '.events[] | select(.type=="TaskStateEntered" and .stateEnteredEventDetails.name=="Validator") | .stateEnteredEventDetails.input' | jq '.documents[0].extracted_data'
```

### Step 4: Check DynamoDB

```bash
aws dynamodb scan \
  --table-name AuditFlow-AuditRecords \
  --filter-expression "loan_application_id = :loan_id" \
  --expression-attribute-values "{\":loan_id\":{\"S\":\"$TEST_LOAN_ID\"}}" \
  --query 'Items[0].applicant_name.S'
```

**Should show:** The name from the PDF (not "Unknown Applicant")

---

## Summary

**To verify Step Functions is passing data correctly:**

1. **Open AWS Console** → Step Functions → State Machines
2. **Click your state machine** → View recent execution
3. **Check Extractor output** → Should have `extracted_data`
4. **Check Validator input** → Should have `extracted_data` in documents
5. **If both have it** → ✓ Everything is working!
6. **If Validator input missing it** → ✗ Fix Step Functions configuration

**That's it!** If you see `extracted_data` flowing through, the applicant names will display correctly.

---

## Need More Help?

See these detailed guides:

- **VERIFY_STEP_FUNCTIONS_DATA_FLOW.md** - Complete verification guide with all methods
- **QUICK_VERIFICATION_COMMANDS.md** - Copy & paste ready commands
- **STEP_FUNCTIONS_DATA_FLOW_DIAGRAM.md** - Visual diagrams and verification points
- **APPLICANT_NAME_FIX_IMPLEMENTATION.md** - Detailed implementation guide

