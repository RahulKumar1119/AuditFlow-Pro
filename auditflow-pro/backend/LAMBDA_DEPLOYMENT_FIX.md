# Lambda Deployment Fix - Missing Shared Module

## Problem

The Step Function was failing with the error:
```
"Unable to import module 'app': No module named 'models'"
```

This occurred because Lambda functions (classifier, extractor, validator, risk_scorer, reporter) were trying to import from the `shared` module, but the deployment packages didn't include it.

## Root Cause

The Lambda deployment packages were created with only the function's `app.py` and pip dependencies, but excluded the local `shared` module that contains:
- `models.py` - Data models (DocumentMetadata, Inconsistency, etc.)
- `repositories.py` - Database access layer
- `encryption.py` - Encryption utilities
- `storage.py` - S3 storage utilities
- `dynamodb_schemas.py` - DynamoDB schema definitions

## Solution

Created `build_lambda_packages.sh` script that:
1. Creates a temporary build directory for each function
2. Copies the function's `app.py` and any additional Python files
3. **Copies the entire `shared` module** into the package
4. Installs pip dependencies
5. Creates a deployment zip file

## Deployment Packages Created

The following deployment packages have been rebuilt with the shared module included:

- ✓ `functions/classifier/deployment_package.zip`
- ✓ `functions/extractor/deployment_package.zip`
- ✓ `functions/validator/deployment_package.zip`
- ✓ `functions/risk_scorer/deployment_package.zip`
- ✓ `functions/reporter/deployment_package.zip`

## How to Deploy

### Option 1: Using AWS CLI

```bash
# Deploy validator function (example)
aws lambda update-function-code \
  --function-name AuditFlowValidator \
  --zip-file fileb://auditflow-pro/backend/functions/validator/deployment_package.zip \
  --region ap-south-1

# Deploy other functions similarly
aws lambda update-function-code \
  --function-name AuditFlowClassifier \
  --zip-file fileb://auditflow-pro/backend/functions/classifier/deployment_package.zip \
  --region ap-south-1

aws lambda update-function-code \
  --function-name AuditFlowExtractor \
  --zip-file fileb://auditflow-pro/backend/functions/extractor/deployment_package.zip \
  --region ap-south-1

aws lambda update-function-code \
  --function-name AuditFlowRiskScorer \
  --zip-file fileb://auditflow-pro/backend/functions/risk_scorer/deployment_package.zip \
  --region ap-south-1

aws lambda update-function-code \
  --function-name AuditFlowReporter \
  --zip-file fileb://auditflow-pro/backend/functions/reporter/deployment_package.zip \
  --region ap-south-1
```

### Option 2: Using Amplify

If using Amplify for deployment, update your deployment configuration to use the new packages:

```bash
amplify push
```

### Option 3: Using AWS Console

1. Go to AWS Lambda console
2. Select each function (Classifier, Extractor, Validator, Risk Scorer, Reporter)
3. Click "Upload from" → "Upload a .zip file"
4. Select the corresponding `deployment_package.zip` from `functions/{function_name}/`
5. Click "Save"

## Verification

After deployment, verify the functions can import the shared module:

```bash
# Test the validator function
aws lambda invoke \
  --function-name AuditFlowValidator \
  --payload '{"loan_application_id":"test-123","document_ids":["doc-1"]}' \
  --region ap-south-1 \
  response.json

cat response.json
```

Expected response should not contain "Unable to import module" error.

## Rebuilding Packages

If you make changes to the `shared` module or function code, rebuild the packages:

```bash
cd auditflow-pro/backend
./build_lambda_packages.sh
```

Then redeploy using one of the methods above.

## Package Contents

Each deployment package now contains:

```
deployment_package.zip
├── app.py                          # Function handler
├── rules.py                        # Function-specific rules (if exists)
├── golden_record.py                # Function-specific utilities (if exists)
├── shared/                         # Shared module
│   ├── __init__.py
│   ├── models.py                   # Data models
│   ├── repositories.py             # Database layer
│   ├── encryption.py               # Encryption utilities
│   ├── storage.py                  # S3 utilities
│   ├── dynamodb_schemas.py         # DynamoDB schemas
│   └── __pycache__/
└── [pip dependencies]              # boto3, botocore, etc.
```

## Troubleshooting

### Still getting "Unable to import module" error?

1. Verify the zip file contains the `shared` folder:
   ```bash
   unzip -l auditflow-pro/backend/functions/validator/deployment_package.zip | grep shared
   ```

2. Check Lambda function timeout isn't too short (increase to 60+ seconds)

3. Check CloudWatch logs for detailed error:
   ```bash
   aws logs tail /aws/lambda/AuditFlowValidator --follow --region ap-south-1
   ```

### Package size too large?

The packages are ~33MB each due to pip dependencies. This is normal and within Lambda limits (250MB unzipped).

To reduce size, you can:
1. Use Lambda Layers for common dependencies
2. Remove unused dependencies from `requirements.txt`

### Import errors after deployment?

1. Verify Python version compatibility (Lambda uses Python 3.10+)
2. Check that all imports in `shared/models.py` are available
3. Rebuild packages and redeploy

## Next Steps

1. Deploy the new packages to AWS Lambda
2. Test the Step Function workflow
3. Monitor CloudWatch logs for any remaining errors
4. If successful, update your CI/CD pipeline to use `build_lambda_packages.sh`

## References

- [AWS Lambda Deployment Packages](https://docs.aws.amazon.com/lambda/latest/dg/python-package.html)
- [Lambda Layers](https://docs.aws.amazon.com/lambda/latest/dg/chapter-layers.html)
- [Step Functions Documentation](https://docs.aws.amazon.com/step-functions/)
