# AWS Region Update Summary

## Overview
All AWS region references have been updated from `ap-south-1` (US East - N. Virginia) to `ap-south-1` (Asia Pacific - Mumbai).

## Files Updated

### Configuration Files
1. **`auditflow-pro/.env`**
   - `AWS_REGION=ap-south-1`

2. **`auditflow-pro/frontend/.env.template`**
   - `VITE_AWS_REGION=ap-south-1`

### Documentation Files
3. **`auditflow-pro/DEPLOYMENT_QUICKSTART.md`**
   - Environment variables updated to `ap-south-1`
   - Cognito User Pool ID format: `ap-south-1_XXXXXXXXX`
   - SNS topic ARN: `arn:aws:sns:ap-south-1:ACCOUNT_ID:...`

4. **`auditflow-pro/AMPLIFY_DEPLOYMENT.md`**
   - Environment variables table updated
   - SNS subscription command updated
   - All region references changed to `ap-south-1`

5. **`auditflow-pro/QUICKSTART.md`**
   - AWS region configuration updated
   - Cognito pool IDs updated
   - Identity Pool ID format: `ap-south-1:XXXXXXXX-...`
   - AWS CLI default region example updated

### Frontend Files
6. **`auditflow-pro/frontend/src/main.tsx`**
   - Cognito userPoolId: `ap-south-1_xxxxxxxxx`

### Backend Lambda Functions
7. **`auditflow-pro/backend/functions/trigger/app.py`**
   - Step Functions client: `region_name='ap-south-1'`

8. **`auditflow-pro/backend/functions/classifier/app.py`**
   - Textract client: `region_name='ap-south-1'`

9. **`auditflow-pro/backend/functions/extractor/app.py`**
   - Textract client: `region_name='ap-south-1'`
   - Comprehend client: `region_name='ap-south-1'`

10. **`auditflow-pro/backend/functions/validator/rules.py`**
    - Bedrock Runtime client: `region_name='ap-south-1'`

11. **`auditflow-pro/backend/functions/reporter/app.py`**
    - Default region: `aws_region = os.environ.get('AWS_REGION', 'ap-south-1')`

### Backend Shared Libraries
12. **`auditflow-pro/backend/shared/storage.py`**
    - S3 client: `region_name='ap-south-1'`

### Test Files
13. **`auditflow-pro/backend/tests/test_storage.py`**
    - `AWS_DEFAULT_REGION='ap-south-1'`
    - S3 mock client: `region_name='ap-south-1'`

14. **`auditflow-pro/backend/tests/test_repositories.py`**
    - `AWS_DEFAULT_REGION='ap-south-1'`
    - DynamoDB mock: `region_name='ap-south-1'`

15. **`auditflow-pro/backend/tests/test_reporter.py`**
    - `AWS_DEFAULT_REGION='ap-south-1'`
    - DynamoDB mock: `region_name='ap-south-1'`
    - SNS mock: `region_name='ap-south-1'`

16. **`auditflow-pro/backend/tests/integration/test_trigger.py`**
    - `AWS_DEFAULT_REGION='ap-south-1'`
    - State Machine ARN: `arn:aws:states:ap-south-1:...`
    - Step Functions client: `region_name='ap-south-1'`

17. **`auditflow-pro/backend/tests/integration/test_workflow.py`**
    - State Machine ARN: `arn:aws:states:ap-south-1:...`
    - Step Functions client: `region_name='ap-south-1'`

## Services Affected

The following AWS services will now operate in the `ap-south-1` region:

1. **AWS Amplify** - Frontend hosting
2. **Amazon Cognito** - User authentication
3. **Amazon S3** - Document storage
4. **Amazon DynamoDB** - Database
5. **AWS Lambda** - Serverless functions
6. **AWS Step Functions** - Workflow orchestration
7. **Amazon Textract** - Document analysis
8. **Amazon Comprehend** - PII detection
9. **Amazon Bedrock** - AI/ML inference
10. **Amazon SNS** - Notifications
11. **AWS API Gateway** - REST API

## Important Notes

### 1. Cognito User Pool Format
- Old: `ap-south-1_XXXXXXXXX`
- New: `ap-south-1_XXXXXXXXX`

### 2. Identity Pool Format
- Old: `ap-south-1:XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX`
- New: `ap-south-1:XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX`

### 3. ARN Format
- Old: `arn:aws:service:ap-south-1:ACCOUNT_ID:resource`
- New: `arn:aws:service:ap-south-1:ACCOUNT_ID:resource`

### 4. Service Availability
Ensure all required services are available in `ap-south-1`:
- ✅ Amplify
- ✅ Cognito
- ✅ S3
- ✅ DynamoDB
- ✅ Lambda
- ✅ Step Functions
- ✅ Textract
- ✅ Comprehend
- ✅ Bedrock (verify model availability)
- ✅ SNS
- ✅ API Gateway

### 5. Bedrock Model Availability
**IMPORTANT**: Verify that Claude Sonnet 4 (`anthropic.claude-sonnet-4-20250514-v1:0`) is available in `ap-south-1`. If not, you may need to:
- Use a different region for Bedrock calls
- Use a different model available in `ap-south-1`
- Request access to the model in this region

Check model availability:
```bash
aws bedrock list-foundation-models --region ap-south-1 --query 'modelSummaries[?contains(modelId, `claude`)]'
```

### 6. Data Residency
All data will now be stored and processed in the Asia Pacific (Mumbai) region, which may have implications for:
- Data residency requirements
- Compliance regulations
- Latency for users in different geographic locations

### 7. Pricing
Pricing may differ between regions. Review AWS pricing for `ap-south-1`:
- https://aws.amazon.com/pricing/

## Migration Checklist

If you have existing resources in `ap-south-1`, you'll need to:

- [ ] Create new Cognito User Pool in `ap-south-1`
- [ ] Create new S3 buckets in `ap-south-1`
- [ ] Create new DynamoDB tables in `ap-south-1`
- [ ] Deploy Lambda functions to `ap-south-1`
- [ ] Create Step Functions state machine in `ap-south-1`
- [ ] Set up API Gateway in `ap-south-1`
- [ ] Configure Amplify app for `ap-south-1`
- [ ] Migrate existing data (if any)
- [ ] Update DNS records if needed
- [ ] Test all functionality in new region
- [ ] Update monitoring and alarms

## Testing

After updating the region, test the following:

1. **Frontend**
   ```bash
   cd auditflow-pro/frontend
   npm test
   ```

2. **Backend**
   ```bash
   cd auditflow-pro/backend
   python3 -m pytest tests/ -v
   ```

3. **Integration**
   - Test document upload
   - Test authentication
   - Test API endpoints
   - Test Step Functions workflow

## Rollback

If you need to rollback to `ap-south-1`, you can use git to revert:

```bash
git diff HEAD -- '*.py' '*.md' '*.env*' '*.tsx'
git checkout HEAD -- <files-to-revert>
```

Or manually change all occurrences of `ap-south-1` back to `ap-south-1`.

## Support

For region-specific issues:
- AWS Support: https://console.aws.amazon.com/support/
- AWS Regional Services: https://aws.amazon.com/about-aws/global-infrastructure/regional-product-services/

## Verification Commands

```bash
# Verify environment variables
grep -r "ap-south-1" auditflow-pro/

# Check for any remaining ap-south-1 references
grep -r "ap-south-1" auditflow-pro/ --exclude-dir=node_modules --exclude-dir=package

# Test AWS CLI with new region
aws sts get-caller-identity --region ap-south-1

# List available Bedrock models
aws bedrock list-foundation-models --region ap-south-1
```

---

**Region update completed successfully!** All references to `ap-south-1` have been changed to `ap-south-1`.
