# Deploy the Fix - Unknown Applicant Issue

**Status:** ✅ READY TO DEPLOY

---

## What Was Fixed

The Step Functions state machine was not returning the `extracted_data` from the Map state, causing the Validator Lambda to receive documents without extracted data. This prevented name extraction and golden record generation.

**Fix:** Added `OutputPath: "$"` to the `ReturnProcessedDocument` Pass state to preserve the complete document including extracted_data.

---

## Deployment Steps

### Step 1: Verify the Fix

Check that the state machine file has been updated:

```bash
grep -A 3 "ReturnProcessedDocument" auditflow-pro/backend/step_functions/state_machine.asl.json
```

Expected output:
```json
"ReturnProcessedDocument": {
  "Type": "Pass",
  "Comment": "Return the complete processed document with extracted_data",
  "OutputPath": "$",
```

### Step 2: Get Current State Machine ARN

```bash
aws stepfunctions list-state-machines \
  --query 'stateMachines[?name==`AuditFlowDocumentProcessing`].stateMachineArn' \
  --output text
```

Save the ARN for the next step.

### Step 3: Get IAM Role ARN

```bash
aws iam list-roles \
  --query 'Roles[?RoleName==`AuditFlowStepFunctionsRole`].Arn' \
  --output text
```

Save the role ARN for the next step.

### Step 4: Update the State Machine

```bash
# Set variables
STATE_MACHINE_ARN="arn:aws:states:ap-south-1:438097524343:stateMachine:AuditFlowDocumentProcessing"
ROLE_ARN="arn:aws:iam::438097524343:role/AuditFlowStepFunctionsRole"

# Update the state machine
aws stepfunctions update-state-machine \
  --state-machine-arn $STATE_MACHINE_ARN \
  --definition file://auditflow-pro/backend/step_functions/state_machine.asl.json \
  --role-arn $ROLE_ARN
```

Expected output:
```json
{
  "updateDate": "2026-03-22T14:15:00.000000+00:00"
}
```

### Step 5: Verify Deployment

```bash
# Get the state machine definition to confirm it was updated
aws stepfunctions describe-state-machine \
  --state-machine-arn $STATE_MACHINE_ARN \
  --query 'definition' \
  --output text | jq '.States.ProcessAllDocuments.Iterator.States.ReturnProcessedDocument'
```

Expected output should show:
```json
{
  "Type": "Pass",
  "Comment": "Return the complete processed document with extracted_data",
  "OutputPath": "$",
  "End": true
}
```

---

## Testing the Fix

### Test 1: Upload a New Document

1. Go to AuditFlow-Pro application
2. Upload a test document (PDF with applicant name)
3. Wait for processing to complete
4. Check the audit queue
5. **Verify:** Applicant name displays correctly (not "Unknown" or "-")

### Test 2: Run Verification Script

```bash
cd auditflow-pro
chmod +x STEP_FUNCTIONS_VERIFICATION_CLI.sh
./STEP_FUNCTIONS_VERIFICATION_CLI.sh
```

Expected output:
```
✓ ALL CHECKS PASSED - Data flow is correct!

Summary:
  ✓ ExtractData returned extracted_data
  ✓ ExtractData extracted full_name: [Name]
  ✓ ValidateDocuments received extracted_data
  ✓ ValidateDocuments generated golden_record
  ✓ Golden record has applicant name: [Name]
```

### Test 3: Check CloudWatch Logs

```bash
# Check Validator Lambda logs for name extraction
aws logs tail /aws/lambda/AuditFlow-DocumentValidator --follow

# Look for messages like:
# "Extracted name from document: John Doe"
# "Golden record generated with name: John Doe"
```

### Test 4: Check DynamoDB

```bash
# Get the most recent audit record
aws dynamodb scan \
  --table-name AuditFlow-AuditRecords \
  --limit 1 \
  --query 'Items[0].applicant_name'
```

Expected output:
```json
{
  "S": "John Doe"
}
```

---

## Rollback (If Needed)

If something goes wrong, you can rollback to the previous state machine:

```bash
# Get the previous definition from AWS
aws stepfunctions describe-state-machine \
  --state-machine-arn $STATE_MACHINE_ARN \
  --query 'definition' > previous_definition.json

# Restore it
aws stepfunctions update-state-machine \
  --state-machine-arn $STATE_MACHINE_ARN \
  --definition file://previous_definition.json \
  --role-arn $ROLE_ARN
```

---

## Troubleshooting

### Issue: State Machine Update Fails

**Error:** `ValidationException: Invalid state machine definition`

**Solution:**
1. Validate the JSON syntax:
   ```bash
   jq . auditflow-pro/backend/step_functions/state_machine.asl.json
   ```
2. Check that all Lambda ARNs are correct
3. Ensure the role ARN is correct

### Issue: New Uploads Still Show "Unknown"

**Possible Causes:**
1. State machine not updated (check Step 5 verification)
2. Frontend not rebuilt (run `npm run build`)
3. Browser cache (clear cache and refresh)
4. Old execution still running (wait for it to complete)

**Solution:**
1. Verify state machine was updated
2. Rebuild frontend: `cd auditflow-pro/frontend && npm run build`
3. Clear browser cache
4. Upload a new document and wait for processing

### Issue: Verification Script Shows "MISSING extracted_data"

**Cause:** State machine not updated or old execution

**Solution:**
1. Verify state machine was updated (Step 5)
2. Run verification script again with a new execution
3. Check CloudWatch logs for errors

---

## Deployment Checklist

- [ ] Verified state machine file has the fix
- [ ] Got State Machine ARN
- [ ] Got IAM Role ARN
- [ ] Updated state machine with `update-state-machine` command
- [ ] Verified deployment (Step 5)
- [ ] Uploaded test document
- [ ] Verified applicant name displays correctly
- [ ] Ran verification script
- [ ] Checked CloudWatch logs
- [ ] Checked DynamoDB for applicant_name

---

## Summary

**What Changed:** Step Functions state machine `ReturnProcessedDocument` Pass state now includes `OutputPath: "$"` to preserve extracted_data

**Why:** Ensures the Map state returns complete documents with extracted_data to the Validator Lambda

**Impact:** Applicant names will now flow correctly through the entire workflow

**Status:** ✅ READY FOR PRODUCTION

---

## Next Steps

1. Deploy the fix using the steps above
2. Test with a new document upload
3. Verify applicant names display correctly
4. Monitor CloudWatch logs for any issues
5. If all tests pass, the issue is resolved

