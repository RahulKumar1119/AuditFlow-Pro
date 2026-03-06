# Step Function Pipeline - Complete Deployment Guide

## Summary of Fixes Applied

### 1. Risk Scorer - JSON Parsing Fix
**Issue**: Risk scorer was receiving `golden_record` as JSON string instead of dict, causing `'str' object has no attribute 'get'` error
**Fix**: Added proper JSON parsing with type checking for both string and dict formats in `calculate_extraction_quality_score()`
**File**: `auditflow-pro/backend/functions/risk_scorer/scorer.py`

### 2. Reporter - DynamoDB Float Type Error
**Issue**: Reporter was trying to save floats to DynamoDB, which only accepts Decimal types
**Fix**: Added `convert_floats_to_decimals()` function to recursively convert all floats to Decimal before DynamoDB put_item
**File**: `auditflow-pro/backend/functions/reporter/app.py`

## Deployment Steps

### Step 1: Rebuild Lambda Packages
All Lambda packages have been rebuilt with the latest fixes:
```bash
cd auditflow-pro/backend
bash build_lambda_packages.sh
```

Packages created:
- ✓ `functions/validator/deployment_package.zip`
- ✓ `functions/extractor/deployment_package.zip`
- ✓ `functions/classifier/deployment_package.zip`
- ✓ `functions/risk_scorer/deployment_package.zip`
- ✓ `functions/reporter/deployment_package.zip`

### Step 2: Deploy Lambda Functions

Deploy each Lambda function with the updated code:

```bash
# Deploy Validator
aws lambda update-function-code \
  --function-name AuditFlow-Validator \
  --zip-file fileb://auditflow-pro/backend/functions/validator/deployment_package.zip \
  --region ap-south-1

# Deploy Extractor
aws lambda update-function-code \
  --function-name AuditFlow-Extractor \
  --zip-file fileb://auditflow-pro/backend/functions/extractor/deployment_package.zip \
  --region ap-south-1

# Deploy Classifier
aws lambda update-function-code \
  --function-name AuditFlow-Classifier \
  --zip-file fileb://auditflow-pro/backend/functions/classifier/deployment_package.zip \
  --region ap-south-1

# Deploy Risk Scorer
aws lambda update-function-code \
  --function-name AuditFlow-RiskScorer \
  --zip-file fileb://auditflow-pro/backend/functions/risk_scorer/deployment_package.zip \
  --region ap-south-1

# Deploy Reporter
aws lambda update-function-code \
  --function-name AuditFlow-Reporter \
  --zip-file fileb://auditflow-pro/backend/functions/reporter/deployment_package.zip \
  --region ap-south-1
```

Or use the automated script:
```bash
cd auditflow-pro/backend
bash DEPLOY_FIXES.sh
```

### Step 3: Verify Lambda Deployments

Check that all functions are active:
```bash
aws lambda get-function --function-name AuditFlow-Validator --region ap-south-1 --query 'Configuration.State'
aws lambda get-function --function-name AuditFlow-Extractor --region ap-south-1 --query 'Configuration.State'
aws lambda get-function --function-name AuditFlow-Classifier --region ap-south-1 --query 'Configuration.State'
aws lambda get-function --function-name AuditFlow-RiskScorer --region ap-south-1 --query 'Configuration.State'
aws lambda get-function --function-name AuditFlow-Reporter --region ap-south-1 --query 'Configuration.State'
```

All should return: `"Active"`

### Step 4: Redeploy Step Function

```bash
cd auditflow-pro
bash infrastructure/step_functions_deploy.sh
```

### Step 5: Test the Pipeline

Start a test execution:
```bash
aws stepfunctions start-execution \
  --state-machine-arn arn:aws:states:ap-south-1:438097524343:stateMachine:AuditFlowDocumentProcessing \
  --input '{
    "loan_application_id":"loan-test-'$(date +%s)'",
    "documents":[
      {
        "document_id":"doc-test-'$(date +%s)'",
        "s3_bucket":"auditflow-documents",
        "s3_key":"uploads/test/sample.pdf",
        "file_size_bytes":1024,
        "upload_timestamp":"2026-03-04T16:00:00Z"
      }
    ]
  }' \
  --region ap-south-1
```

### Step 6: Monitor Execution

Watch the Step Function execution:
```bash
# Get execution status
aws stepfunctions describe-execution \
  --execution-arn <execution-arn-from-step-5> \
  --region ap-south-1

# View execution history
aws stepfunctions get-execution-history \
  --execution-arn <execution-arn-from-step-5> \
  --region ap-south-1
```

Monitor Lambda logs:
```bash
# Validator logs
aws logs tail /aws/lambda/AuditFlow-Validator --follow --region ap-south-1

# Risk Scorer logs
aws logs tail /aws/lambda/AuditFlow-RiskScorer --follow --region ap-south-1

# Reporter logs
aws logs tail /aws/lambda/AuditFlow-Reporter --follow --region ap-south-1

# Step Function logs
aws logs tail /aws/vendedlogs/states/AuditFlowDocumentProcessing --follow --region ap-south-1
```

## Expected Flow

```
1. Trigger Lambda (S3 event)
   ↓
2. ProcessAllDocuments (Map state)
   ├─ ClassifyDocument (Lambda) ✓
   ├─ ExtractData (Lambda) ✓
   └─ SaveDocumentMetadata (DynamoDB PutItem) ✓
   ↓
3. ValidateDocuments (Lambda) ✓
   ├─ Load documents from DynamoDB
   ├─ Detect inconsistencies
   └─ Generate golden record
   ↓
4. CalculateRiskScore (Lambda) ✓ FIXED
   ├─ Score inconsistencies
   └─ Calculate risk level
   ↓
5. GenerateReport (Lambda) ✓ FIXED
   ├─ Create audit record
   ├─ Trigger alerts
   └─ Save to DynamoDB
```

## Troubleshooting

### Lambda Still Shows Old Code
- Wait 30-60 seconds for Lambda to finish updating
- Check `LastUpdateStatus` is "Successful"
- Invoke a test to ensure new code is running

### Risk Scorer Still Fails with JSON Error
- Verify `functions/risk_scorer/deployment_package.zip` was rebuilt
- Check that `scorer.py` has the JSON parsing fix
- Redeploy the Lambda function

### Reporter Still Fails with Float Error
- Verify `functions/reporter/deployment_package.zip` was rebuilt
- Check that `app.py` has the `convert_floats_to_decimals()` function
- Redeploy the Lambda function

### DynamoDB Errors
- Verify IAM role has DynamoDB permissions
- Check table names match in environment variables
- Verify tables exist: `AuditFlow-Documents`, `AuditFlow-AuditRecords`

### Step Function Fails at ValidateDocuments
- Check CloudWatch logs for validator errors
- Verify documents are being saved to DynamoDB
- Check that Map state is passing documents correctly

## Files Modified

1. `auditflow-pro/backend/functions/risk_scorer/scorer.py` - Added JSON parsing
2. `auditflow-pro/backend/functions/reporter/app.py` - Added Decimal conversion
3. `auditflow-pro/backend/DEPLOY_FIXES.sh` - Automated deployment script
4. `auditflow-pro/backend/DEPLOYMENT_GUIDE.md` - This file

## Verification Checklist

- [ ] All Lambda packages rebuilt
- [ ] All Lambda functions deployed
- [ ] All Lambda functions show "Active" status
- [ ] Step Function redeployed
- [ ] Test execution started
- [ ] Validator completes successfully
- [ ] Risk Scorer completes successfully
- [ ] Reporter completes successfully
- [ ] Audit record saved to DynamoDB
- [ ] No errors in CloudWatch logs

## Next Steps

1. Deploy all Lambda functions using the commands above
2. Redeploy Step Function
3. Run test execution
4. Monitor CloudWatch logs
5. Verify end-to-end flow completes successfully
6. Deploy to production

## Support

For issues, check:
- CloudWatch Logs: `/aws/lambda/AuditFlow-*`
- Step Functions Logs: `/aws/vendedlogs/states/AuditFlowDocumentProcessing`
- DynamoDB: `AuditFlow-Documents` and `AuditFlow-AuditRecords` tables
