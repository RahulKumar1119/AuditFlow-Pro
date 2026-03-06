# DynamoDB Document Save Fix

## Problem

The validator Lambda was failing with error:
```
"No valid documents available for validation"
```

This occurred because extracted documents were not being saved to DynamoDB. The Step Function was:
1. Extracting data from documents
2. Immediately validating without saving to DynamoDB
3. Validator trying to load documents from DynamoDB but finding nothing

## Root Cause

The Step Function pipeline was missing a critical step: **saving extracted document metadata to DynamoDB** after extraction.

The flow was:
```
Classify → Extract → Validate (fails - no docs in DB)
```

Should be:
```
Classify → Extract → Save to DynamoDB → Validate (succeeds)
```

## Solution

Added a new state `SaveDocumentMetadata` in the Step Function that:
1. Runs after document extraction completes
2. Saves document metadata to the `AuditFlow-Documents` DynamoDB table
3. Stores all extracted data, timestamps, and processing status
4. Uses DynamoDB PutItem action (no Lambda needed)

## Changes Made

**File**: `auditflow-pro/backend/step_functions/state_machine.asl.json`

**State**: `ProcessAllDocuments` → `Iterator` → `SaveDocumentMetadata` (new)

### New State Definition

```json
"SaveDocumentMetadata": {
  "Type": "Task",
  "Resource": "arn:aws:states:::dynamodb:putItem",
  "Parameters": {
    "TableName": "AuditFlow-Documents",
    "Item": {
      "document_id": { "S.$": "$.document_id" },
      "loan_application_id": { "S.$": "$.loan_application_id" },
      "document_type": { "S.$": "$.document_type" },
      "s3_bucket": { "S.$": "$.s3_bucket" },
      "s3_key": { "S.$": "$.s3_key" },
      "file_size_bytes": { "N.$": "$.file_size_bytes" },
      "upload_timestamp": { "S.$": "$.upload_timestamp" },
      "extraction_timestamp": { "S.$": "$.extraction_timestamp" },
      "processing_status": { "S.$": "$.processing_status" },
      "extracted_data": { "S.$": "States.JsonToString($.extracted_data)" },
      "low_confidence_fields": { "S.$": "States.JsonToString($.low_confidence_fields)" },
      "pii_detected": { "S.$": "States.JsonToString($.pii_detected)" }
    }
  },
  "Retry": [...],
  "Catch": [...],
  "End": true
}
```

## Updated Flow

```
1. ClassifyDocument
   ↓
2. CheckClassificationConfidence
   ├─ If requires_manual_review → FlagForManualReview (End)
   └─ Else → ExtractData
   ↓
3. ExtractData (Lambda)
   ↓
4. SaveDocumentMetadata (DynamoDB PutItem) ← NEW
   ↓
5. End (document processed and saved)
```

## Data Saved to DynamoDB

Each document now saves:
- `document_id` - Unique document identifier
- `loan_application_id` - Associated loan application
- `document_type` - Classification (W2, TAX_FORM, etc.)
- `s3_bucket` - S3 bucket location
- `s3_key` - S3 object key
- `file_size_bytes` - File size
- `upload_timestamp` - When uploaded
- `extraction_timestamp` - When extracted
- `processing_status` - COMPLETED or FAILED
- `extracted_data` - JSON string of extracted fields
- `low_confidence_fields` - Fields with confidence < 80%
- `pii_detected` - PII types detected

## Validator Now Works

After this fix, the validator can:
1. Receive document IDs from Step Function
2. Load documents from DynamoDB using `DocumentRepository`
3. Access extracted data for validation
4. Detect inconsistencies across documents
5. Generate golden record

## Deployment

1. Update the Step Function state machine:
   ```bash
   cd auditflow-pro
   bash infrastructure/step_functions_deploy.sh
   ```

2. Or manually update via AWS CLI:
   ```bash
   aws stepfunctions update-state-machine \
     --state-machine-arn arn:aws:states:ap-south-1:ACCOUNT:stateMachine:AuditFlowDocumentProcessing \
     --definition file://backend/step_functions/state_machine.asl.json \
     --role-arn arn:aws:iam::ACCOUNT:role/AuditFlowStepFunctionsRole
   ```

## IAM Permissions Required

The Step Functions execution role needs DynamoDB permissions:
```json
{
  "Effect": "Allow",
  "Action": [
    "dynamodb:PutItem"
  ],
  "Resource": "arn:aws:dynamodb:ap-south-1:ACCOUNT:table/AuditFlow-Documents"
}
```

The deployment script (`step_functions_deploy.sh`) should already include this.

## Testing

After deployment, test with sample input:
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

Expected flow:
1. ✅ Document classified
2. ✅ Data extracted
3. ✅ Metadata saved to DynamoDB
4. ✅ Validator loads documents
5. ✅ Validation completes
6. ✅ Risk scoring proceeds

## Related Files

- `auditflow-pro/backend/step_functions/state_machine.asl.json` - Updated
- `auditflow-pro/backend/STEP_FUNCTION_FIX.md` - Input mapping fix
- `auditflow-pro/backend/LAMBDA_DEPLOYMENT_FIX.md` - Lambda deployment
- `auditflow-pro/backend/VALIDATOR_CODE_REVIEW.md` - Validator code review

## Summary

The Step Function now properly saves extracted document metadata to DynamoDB after extraction. This allows the validator to load documents and perform cross-document validation. The fix uses DynamoDB's native PutItem action for efficiency and reliability.
