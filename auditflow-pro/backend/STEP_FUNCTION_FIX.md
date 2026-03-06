# Step Function Input Mapping Fix

## Problem

The Step Function was failing at the `ValidateDocuments` state with error:
```
"message":"document_ids list cannot be empty"
```

## Root Cause

The Step Function was passing the wrong parameter to the validator Lambda:

**Before (Incorrect)**:
```json
"Payload": {
  "loan_application_id.$": "$.loan_application_id",
  "documents.$": "$.processed_documents"
}
```

The validator expects `document_ids` (array of document IDs), but was receiving `documents` (full document objects).

## Solution

Updated the `ValidateDocuments` state to extract document IDs from the processed documents:

**After (Correct)**:
```json
"Payload": {
  "loan_application_id.$": "$.loan_application_id",
  "document_ids.$": "$.processed_documents[*].document_id"
}
```

This uses JSONPath `[*].document_id` to extract only the document IDs from the processed documents array.

## Changes Made

**File**: `auditflow-pro/backend/step_functions/state_machine.asl.json`

**State**: `ValidateDocuments`

**Change**: 
- Removed: `"documents.$": "$.processed_documents"`
- Added: `"document_ids.$": "$.processed_documents[*].document_id"`

## How It Works

1. The `ProcessAllDocuments` Map state outputs an array of processed documents
2. Each document has a `document_id` field
3. The JSONPath `$.processed_documents[*].document_id` extracts all document IDs into an array
4. This array is passed as `document_ids` to the validator Lambda
5. The validator loads each document from DynamoDB using these IDs

## Validator Lambda Input

Now receives:
```json
{
  "loan_application_id": "loan-123",
  "document_ids": ["doc-1", "doc-2", "doc-3"]
}
```

Instead of:
```json
{
  "loan_application_id": "loan-123",
  "documents": [
    {
      "document_id": "doc-1",
      "document_type": "W2",
      ...
    },
    ...
  ]
}
```

## Deployment

1. Update the Step Function state machine in AWS:
   ```bash
   aws stepfunctions update-state-machine \
     --state-machine-arn arn:aws:states:ap-south-1:ACCOUNT:stateMachine:AuditFlowPipeline \
     --definition file://auditflow-pro/backend/step_functions/state_machine.asl.json \
     --role-arn arn:aws:iam::ACCOUNT:role/StepFunctionRole
   ```

2. Or use Amplify:
   ```bash
   amplify push
   ```

## Testing

After deployment, test the Step Function with sample input:
```json
{
  "loan_application_id": "loan-test-123",
  "documents": [
    {
      "document_id": "doc-1",
      "s3_bucket": "auditflow-documents",
      "s3_key": "uploads/loan-test-123/doc-1_w2.pdf",
      "loan_application_id": "loan-test-123"
    }
  ]
}
```

## Expected Result

The Step Function should now:
1. ✅ Process all documents in parallel
2. ✅ Extract document IDs correctly
3. ✅ Pass document IDs to validator
4. ✅ Validator loads documents from DynamoDB
5. ✅ Validation completes successfully
6. ✅ Risk scoring and reporting proceed

## Related Files

- `auditflow-pro/backend/step_functions/state_machine.asl.json` - Updated
- `auditflow-pro/backend/functions/validator/app.py` - No changes needed
- `auditflow-pro/backend/LAMBDA_DEPLOYMENT_FIX.md` - Deployment packages
- `auditflow-pro/backend/VALIDATOR_CODE_REVIEW.md` - Code review

## Summary

The validator Lambda code was correct. The issue was in the Step Function input mapping. By extracting document IDs from the processed documents array, the validator now receives the correct input format and can successfully load and validate documents.
