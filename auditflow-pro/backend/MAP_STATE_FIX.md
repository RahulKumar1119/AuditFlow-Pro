# Map State Parameters Fix

## Problem

The validator was still receiving an empty `document_ids` list even after previous fixes. The root cause was in the `ProcessAllDocuments` Map state.

Error:
```
"message":"document_ids list cannot be empty"
```

## Root Cause

The `ProcessAllDocuments` Map state was missing a `Parameters` section. Without it:

1. The Map state passes each item directly to the iterator
2. The iterator receives the document object as the root context
3. References like `$.document.document_id` fail because there's no `document` property
4. The `loan_application_id` is lost in the iterator context
5. When documents reach `ValidateDocuments`, the `processed_documents` array is empty or malformed

## Solution

Added a `Parameters` section to the Map state that:
1. Wraps each document item as `$.document`
2. Preserves the `loan_application_id` from the parent context
3. Ensures the iterator receives the correct context structure

## Changes Made

**File**: `auditflow-pro/backend/step_functions/state_machine.asl.json`

**State**: `ProcessAllDocuments`

### Before (Incorrect)
```json
"ProcessAllDocuments": {
  "Type": "Map",
  "ItemsPath": "$.documents",
  "ResultPath": "$.processed_documents",
  "MaxConcurrency": 10,
  "Iterator": { ... }
}
```

### After (Correct)
```json
"ProcessAllDocuments": {
  "Type": "Map",
  "ItemsPath": "$.documents",
  "ResultPath": "$.processed_documents",
  "MaxConcurrency": 10,
  "Parameters": {
    "document.$": "$$.Map.Item.Value",
    "loan_application_id.$": "$.loan_application_id"
  },
  "Iterator": { ... }
}
```

## How It Works

### Input to Map State
```json
{
  "loan_application_id": "loan-123",
  "documents": [
    {
      "document_id": "doc-1",
      "s3_bucket": "bucket",
      "s3_key": "path/doc.pdf"
    },
    {
      "document_id": "doc-2",
      "s3_bucket": "bucket",
      "s3_key": "path/doc2.pdf"
    }
  ]
}
```

### Each Iterator Iteration Receives
```json
{
  "document": {
    "document_id": "doc-1",
    "s3_bucket": "bucket",
    "s3_key": "path/doc.pdf"
  },
  "loan_application_id": "loan-123"
}
```

### Iterator Can Now Access
- `$.document.document_id` ✅
- `$.document.s3_bucket` ✅
- `$.document.s3_key` ✅
- `$.loan_application_id` ✅

### Map State Output
```json
{
  "processed_documents": [
    {
      "document_id": "doc-1",
      "document_type": "W2",
      "extracted_data": {...},
      "processing_status": "COMPLETED",
      "loan_application_id": "loan-123"
    },
    {
      "document_id": "doc-2",
      "document_type": "BANK_STATEMENT",
      "extracted_data": {...},
      "processing_status": "COMPLETED",
      "loan_application_id": "loan-123"
    }
  ]
}
```

### ValidateDocuments Can Now Extract
```
$.processed_documents[*].document_id → ["doc-1", "doc-2"]
```

## JSONPath Explanation

- `$$.Map.Item.Value` - Special syntax to access the current item in a Map state
- `$$` - Refers to the original input to the Map state
- `$.Map.Item.Value` - The current item being processed
- `$.loan_application_id` - Preserved from parent context

## Deployment

1. Update the Step Function:
   ```bash
   cd auditflow-pro
   bash infrastructure/step_functions_deploy.sh
   ```

2. Or manually:
   ```bash
   aws stepfunctions update-state-machine \
     --state-machine-arn arn:aws:states:ap-south-1:ACCOUNT:stateMachine:AuditFlowDocumentProcessing \
     --definition file://backend/step_functions/state_machine.asl.json \
     --role-arn arn:aws:iam::ACCOUNT:role/AuditFlowStepFunctionsRole
   ```

## Testing

After deployment, test with:
```bash
aws stepfunctions start-execution \
  --state-machine-arn arn:aws:states:ap-south-1:ACCOUNT:stateMachine:AuditFlowDocumentProcessing \
  --input '{
    "loan_application_id":"loan-test-123",
    "documents":[
      {
        "document_id":"doc-1",
        "s3_bucket":"auditflow-documents",
        "s3_key":"uploads/loan-test-123/test.pdf",
        "file_size_bytes":1024,
        "upload_timestamp":"2026-03-04T15:00:00Z"
      }
    ]
  }' \
  --region ap-south-1
```

Expected flow:
1. ✅ Map state processes documents with correct context
2. ✅ Classifier receives `$.document.document_id`
3. ✅ Extractor receives full document context
4. ✅ Documents saved to DynamoDB
5. ✅ Validator receives non-empty `document_ids` array
6. ✅ Validation completes successfully

## Related Files

- `auditflow-pro/backend/step_functions/state_machine.asl.json` - Updated
- `auditflow-pro/backend/STEP_FUNCTION_FIX.md` - Input mapping fix
- `auditflow-pro/backend/DYNAMODB_SAVE_FIX.md` - DynamoDB save
- `auditflow-pro/backend/IAM_PERMISSION_FIX.md` - IAM permissions

## Summary

The Map state now correctly passes document context to each iterator iteration, preserving both the document data and the loan application ID. This ensures documents flow through the entire pipeline correctly and reach the validator with proper document IDs.
