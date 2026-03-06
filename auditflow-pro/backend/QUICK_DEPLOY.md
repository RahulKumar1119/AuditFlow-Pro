# Quick Deployment Guide

## Current Status
All code fixes are complete. The validator now handles multiple document structure formats and logs the actual structure received for debugging.

## One-Command Deployment

```bash
cd auditflow-pro/backend && \
bash build_lambda_packages.sh && \
cd .. && \
aws lambda update-function-code \
  --function-name AuditFlow-Validator \
  --zip-file fileb://backend/functions/validator/deployment_package.zip \
  --region ap-south-1 && \
echo "✓ Validator deployed successfully"
```

## Step-by-Step Deployment

### 1. Rebuild Validator Package
```bash
cd auditflow-pro/backend
bash build_lambda_packages.sh
```

### 2. Deploy Validator Lambda
```bash
aws lambda update-function-code \
  --function-name AuditFlow-Validator \
  --zip-file fileb://auditflow-pro/backend/functions/validator/deployment_package.zip \
  --region ap-south-1
```

### 3. Redeploy Step Function (if not already done)
```bash
cd auditflow-pro
bash infrastructure/step_functions_deploy.sh
```

## Test Execution

```bash
aws stepfunctions start-execution \
  --state-machine-arn arn:aws:states:ap-south-1:438097524343:stateMachine:AuditFlowDocumentProcessing \
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

## Monitor Logs

```bash
# Watch validator logs
aws logs tail /aws/lambda/AuditFlow-Validator --follow --region ap-south-1

# Watch Step Function logs
aws logs tail /aws/vendedlogs/states/AuditFlowDocumentProcessing --follow --region ap-south-1
```

## What to Expect

1. **Map state processes documents** - Classifies and extracts data
2. **Documents saved to DynamoDB** - SaveDocumentMetadata state
3. **Validator loads documents** - Logs show document structure
4. **Validation completes** - Inconsistencies detected
5. **Risk scoring** - Risk assessment calculated
6. **Report generated** - Final audit report

## Troubleshooting

### If validator still fails:
1. Check CloudWatch logs for actual document structure
2. Verify documents were saved to DynamoDB
3. Confirm document_id field exists in documents

### If DynamoDB save fails:
1. Verify IAM permissions: `bash infrastructure/fix_stepfunctions_role.sh`
2. Check table exists: `aws dynamodb describe-table --table-name AuditFlow-Documents --region ap-south-1`

### If Step Function doesn't update:
1. Redeploy: `bash infrastructure/step_functions_deploy.sh`
2. Wait 30 seconds for propagation
3. Start new execution

## Files Modified

- `auditflow-pro/backend/functions/validator/app.py` - Enhanced document ID extraction with logging
- `auditflow-pro/backend/build_lambda_packages.sh` - Builds deployment packages
- `auditflow-pro/backend/step_functions/state_machine.asl.json` - Updated state machine

## Success Indicators

✅ Validator Lambda deployed
✅ Step Function redeployed
✅ Test execution started
✅ CloudWatch logs show document structure
✅ Validator extracts document IDs
✅ Documents loaded from DynamoDB
✅ Validation completes
✅ Risk scoring proceeds
✅ Report generated

## Next Steps

1. Deploy validator: `aws lambda update-function-code ...`
2. Start test execution
3. Monitor CloudWatch logs
4. Verify end-to-end flow
5. Deploy to production
