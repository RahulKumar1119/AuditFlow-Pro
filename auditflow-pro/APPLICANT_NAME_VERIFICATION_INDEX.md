# Applicant Name Issue - Complete Verification Guide Index

**Issue:** Applicant names showing as "Unknown Applicant" instead of actual names

**Status:** ✅ Code is correct. Need to verify Step Functions configuration.

---

## 📚 Documentation Files

### Quick Start (Start Here!)

**[HOW_TO_VERIFY_STEP_FUNCTIONS.md](HOW_TO_VERIFY_STEP_FUNCTIONS.md)** ⭐ START HERE
- 5-10 minute quick verification
- Simplest method using AWS Console
- Copy & paste CLI commands
- What to look for
- Common issues and fixes

### Detailed Guides

**[VERIFY_STEP_FUNCTIONS_DATA_FLOW.md](VERIFY_STEP_FUNCTIONS_DATA_FLOW.md)**
- 5 different verification methods
- Step-by-step instructions for each method
- CloudWatch log analysis
- Automated verification script
- Troubleshooting guide

**[QUICK_VERIFICATION_COMMANDS.md](QUICK_VERIFICATION_COMMANDS.md)**
- Copy & paste ready commands
- All-in-one verification script
- Troubleshooting commands
- Quick checklist

**[STEP_FUNCTIONS_DATA_FLOW_DIAGRAM.md](STEP_FUNCTIONS_DATA_FLOW_DIAGRAM.md)**
- Visual data flow diagram
- Verification points explained
- Common issues & fixes
- Decision tree

### Implementation & Analysis

**[APPLICANT_NAME_FIX_IMPLEMENTATION.md](APPLICANT_NAME_FIX_IMPLEMENTATION.md)**
- Root cause analysis
- Current data flow explanation
- Implementation steps
- Debugging checklist
- Testing procedures

**[APPLICANT_NAME_ISSUE_SUMMARY.md](APPLICANT_NAME_ISSUE_SUMMARY.md)**
- Executive summary
- Code analysis for each component
- Verification results
- What needs to be done

**[FIX_APPLICANT_NAME_DISPLAY.md](FIX_APPLICANT_NAME_DISPLAY.md)**
- Original issue analysis
- Problem breakdown
- Solution overview
- Quick fix checklist

**[CLOUDWATCH_DEBUGGING_GUIDE.md](CLOUDWATCH_DEBUGGING_GUIDE.md)**
- CloudWatch log analysis
- Log search patterns
- Complete debugging workflow
- Troubleshooting guide

### Verification Tools

**[verify_applicant_name_flow.py](verify_applicant_name_flow.py)**
- Python verification script
- Tests complete workflow
- Validates all components
- Run: `python3 verify_applicant_name_flow.py`

---

## 🚀 Quick Start (5 Minutes)

### Option 1: AWS Console (Easiest)

1. Open AWS Console
2. Go to Step Functions
3. Click your state machine
4. View recent execution
5. Check Extractor output → has `extracted_data`?
6. Check Validator input → has `extracted_data`?
7. If both YES → ✓ Working!

### Option 2: AWS CLI (Fastest)

```bash
# Get state machine
STATE_MACHINE_ARN=$(aws stepfunctions list-state-machines \
  --query 'stateMachines[?name==`AuditFlow-DocumentProcessing`].stateMachineArn' \
  --output text)

# Get execution
EXECUTION_ARN=$(aws stepfunctions list-executions \
  --state-machine-arn $STATE_MACHINE_ARN \
  --status-filter SUCCEEDED \
  --max-items 1 \
  --query 'executions[0].executionArn' \
  --output text)

# Get history
aws stepfunctions get-execution-history \
  --execution-arn $EXECUTION_ARN \
  --max-items 100 > execution_history.json

# Check Extractor output
cat execution_history.json | jq '.events[] | select(.type=="TaskSucceeded" and .stateExitedEventDetails.name=="Extractor") | .stateExitedEventDetails.output' | jq '.extracted_data'

# Check Validator input
cat execution_history.json | jq '.events[] | select(.type=="TaskStateEntered" and .stateEnteredEventDetails.name=="Validator") | .stateEnteredEventDetails.input' | jq '.documents[0].extracted_data'
```

---

## 🔍 What to Look For

### ✓ SUCCESS - Data is Flowing

**Extractor Output:**
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

**Validator Input:**
```json
{
  "documents": [{
    "extracted_data": {
      "employee_name": {
        "value": "John Doe"
      }
    }
  }]
}
```

**Result:** ✓ Applicant names will display correctly

### ✗ FAILURE - Data is Not Flowing

**Validator Input (Missing extracted_data):**
```json
{
  "documents": [{
    "document_id": "doc-123",
    "document_type": "W2"
    // ✗ Missing extracted_data!
  }]
}
```

**Result:** ✗ Applicant names will show as "Unknown Applicant"

---

## 🛠️ Verification Methods

### Method 1: AWS Console (Easiest)
- Time: 5 minutes
- Skill: Beginner
- See: HOW_TO_VERIFY_STEP_FUNCTIONS.md

### Method 2: AWS CLI (Fastest)
- Time: 2 minutes
- Skill: Intermediate
- See: QUICK_VERIFICATION_COMMANDS.md

### Method 3: CloudWatch Logs
- Time: 10 minutes
- Skill: Intermediate
- See: CLOUDWATCH_DEBUGGING_GUIDE.md

### Method 4: Test PDF Upload
- Time: 15 minutes
- Skill: Beginner
- See: VERIFY_STEP_FUNCTIONS_DATA_FLOW.md

### Method 5: Automated Script
- Time: 5 minutes
- Skill: Intermediate
- See: VERIFY_STEP_FUNCTIONS_DATA_FLOW.md

---

## 📋 Verification Checklist

```
STEP 1: Check Extractor Output
  □ Extractor state has output
  □ Output includes extracted_data field
  □ extracted_data has employee_name
  □ employee_name has value and confidence

STEP 2: Check Validator Input
  □ Validator state has input
  □ Input includes documents array
  □ documents[0] has extracted_data field
  □ extracted_data matches Extractor output

STEP 3: Check Validator Output
  □ Validator state has output
  □ Output includes golden_record
  □ golden_record has name field
  □ name field has value and confidence

STEP 4: Check CloudWatch Logs
  □ Extractor logs show "Extracted employee_name"
  □ Validator logs show "Extracted name"
  □ No errors about missing extracted_data
  □ Reporter logs show applicant_name

STEP 5: Check DynamoDB
  □ Audit record exists
  □ applicant_name field is populated
  □ applicant_name matches extracted name
  □ golden_record.name.value is populated

RESULT: ✓ PASS or ✗ FAIL
```

---

## 🐛 Troubleshooting

### Problem: Validator Input Missing `extracted_data`

**Cause:** Step Functions not merging Extractor output

**Solution:**
1. Check Step Functions state machine definition
2. Find Extractor state
3. Verify it has: `"ResultPath": "$.document"`
4. This merges output with input

**See:** APPLICANT_NAME_FIX_IMPLEMENTATION.md

### Problem: Extractor Output Missing `extracted_data`

**Cause:** Extractor Lambda not returning data

**Solution:**
1. Check Extractor Lambda logs
2. Verify Textract is extracting data
3. Check for low confidence scores

**See:** CLOUDWATCH_DEBUGGING_GUIDE.md

### Problem: Validator Logs Show "No valid documents loaded"

**Cause:** Validator not receiving `extracted_data`

**Solution:**
1. Verify Step Functions passes `extracted_data`
2. Check Extractor is returning `extracted_data`
3. Verify `ResultPath` configuration

**See:** VERIFY_STEP_FUNCTIONS_DATA_FLOW.md

### Problem: DynamoDB Missing `applicant_name`

**Cause:** Reporter not receiving golden record

**Solution:**
1. Check Reporter Lambda logs
2. Verify Validator returns golden record
3. Check IAM permissions

**See:** CLOUDWATCH_DEBUGGING_GUIDE.md

---

## 📊 Data Flow Summary

```
Trigger
  ↓
Classifier (adds document_type)
  ↓
Extractor (adds extracted_data) ← CRITICAL
  ↓
[Step Functions must pass extracted_data through]
  ↓
Validator (receives extracted_data, generates golden_record)
  ↓
Reporter (uses golden_record to populate applicant_name)
  ↓
DynamoDB (stores audit record with applicant_name)
```

---

## ✅ Success Criteria

**All of these must be true:**

1. ✓ Extractor returns `extracted_data` with employee names
2. ✓ Validator receives `extracted_data` in documents
3. ✓ Validator generates `golden_record` with name field
4. ✓ Reporter uses `golden_record` to populate `applicant_name`
5. ✓ DynamoDB audit record has `applicant_name` populated
6. ✓ `applicant_name` is not "Unknown Applicant"

---

## 📞 Need Help?

### Quick Questions

**Q: Where do I start?**
A: Read HOW_TO_VERIFY_STEP_FUNCTIONS.md (5 minutes)

**Q: How do I check if data is flowing?**
A: Use AWS Console or CLI commands in QUICK_VERIFICATION_COMMANDS.md

**Q: What if Validator input is missing extracted_data?**
A: Fix Step Functions state machine - see APPLICANT_NAME_FIX_IMPLEMENTATION.md

**Q: How do I test with a real PDF?**
A: See VERIFY_STEP_FUNCTIONS_DATA_FLOW.md - Method 4

**Q: Can I automate the verification?**
A: Yes, see VERIFY_STEP_FUNCTIONS_DATA_FLOW.md - Method 5

---

## 📖 Document Guide

| Document | Purpose | Time | Skill |
|----------|---------|------|-------|
| HOW_TO_VERIFY_STEP_FUNCTIONS.md | Quick start | 5 min | Beginner |
| QUICK_VERIFICATION_COMMANDS.md | Copy & paste commands | 2 min | Intermediate |
| VERIFY_STEP_FUNCTIONS_DATA_FLOW.md | Complete guide | 30 min | Intermediate |
| STEP_FUNCTIONS_DATA_FLOW_DIAGRAM.md | Visual diagrams | 10 min | Beginner |
| APPLICANT_NAME_FIX_IMPLEMENTATION.md | Implementation details | 20 min | Advanced |
| APPLICANT_NAME_ISSUE_SUMMARY.md | Executive summary | 10 min | Beginner |
| CLOUDWATCH_DEBUGGING_GUIDE.md | Log analysis | 15 min | Intermediate |
| FIX_APPLICANT_NAME_DISPLAY.md | Original analysis | 10 min | Beginner |

---

## 🎯 Next Steps

1. **Read:** HOW_TO_VERIFY_STEP_FUNCTIONS.md (5 minutes)
2. **Verify:** Use AWS Console or CLI to check data flow
3. **If OK:** ✓ Issue is resolved
4. **If Not OK:** Check troubleshooting section
5. **Test:** Upload test PDF and verify applicant name appears

---

## 📝 Summary

**The Issue:** Applicant names showing as "Unknown Applicant"

**The Cause:** Step Functions not passing `extracted_data` to Validator

**The Solution:** Verify Step Functions configuration is correct

**The Verification:** Check that `extracted_data` flows from Extractor to Validator

**The Result:** Once verified, applicant names will display correctly

---

**Start with:** [HOW_TO_VERIFY_STEP_FUNCTIONS.md](HOW_TO_VERIFY_STEP_FUNCTIONS.md)

