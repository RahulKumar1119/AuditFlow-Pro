# Deployment Troubleshooting Guide

## Common Issues and Solutions

### Issue 1: KMS Setup - "Unknown options: --key-policy"

**Error:**
```
Unknown options: --key-policy, {
```

**Cause:** JSON policy format issue with inline shell variables

**Solution:** ✅ FIXED
The kms_setup.sh script has been updated to use temporary policy files instead of inline JSON.

**Verify the fix:**
```bash
cd infrastructure
./kms_setup.sh
```

---

### Issue 2: AWS CLI Not Configured

**Error:**
```
Unable to locate credentials
```

**Solution:**
```bash
# Configure AWS CLI
aws configure

# Enter:
# - AWS Access Key ID
# - AWS Secret Access Key
# - Default region: ap-south-1
# - Default output format: json

# Verify
aws sts get-caller-identity
```

---

### Issue 3: Insufficient Permissions

**Error:**
```
User: arn:aws:iam::ACCOUNT_ID:user/USERNAME is not authorized to perform: kms:CreateKey
```

**Solution:**
Ensure your IAM user/role has these permissions:
- KMS: CreateKey, CreateAlias, EnableKeyRotation, TagResource
- IAM: CreateRole, AttachRolePolicy, PutRolePolicy
- S3: CreateBucket, PutBucketPolicy, PutBucketEncryption
- DynamoDB: CreateTable, UpdateTable
- Lambda: CreateFunction, UpdateFunctionCode
- API Gateway: CreateRestApi, CreateDeployment
- Cognito: CreateUserPool, CreateIdentityPool

**Quick fix:**
Attach `AdministratorAccess` policy (for development only):
```bash
aws iam attach-user-policy \
  --user-name YOUR_USERNAME \
  --policy-arn arn:aws:iam::aws:policy/AdministratorAccess
```

---

### Issue 4: Resource Already Exists

**Error:**
```
An error occurred (ResourceInUseException): KMS key alias already exists
```

**Solution:**
The script checks for existing resources. If you see this, it means the resource is already created and will be reused.

**To start fresh:**
```bash
# Run teardown script
./teardown-master.sh -e prod

# Then redeploy
./deploy-master.sh -e prod
```

---

### Issue 5: Lambda Deployment Package Missing

**Error:**
```
deployment_package.zip not found
```

**Solution:**
```bash
cd backend
bash setup.sh
cd ..
```

This creates the deployment package with all dependencies.

---

### Issue 6: DynamoDB Table Creation Fails

**Error:**
```
Table already exists: AuditFlow-Documents
```

**Solution:**
Skip the table creation step or delete existing tables:

```bash
# Check existing tables
aws dynamodb list-tables --region ap-south-1

# Delete if needed (WARNING: This deletes data!)
aws dynamodb delete-table --table-name AuditFlow-Documents --region ap-south-1
aws dynamodb delete-table --table-name AuditFlow-AuditRecords --region ap-south-1

# Wait for deletion
aws dynamodb wait table-not-exists --table-name AuditFlow-Documents --region ap-south-1

# Then recreate
cd infrastructure
./create_dynamodb_tables.sh
```

---

### Issue 7: API Gateway Deployment Fails

**Error:**
```
No integration defined for method
```

**Solution:**
Ensure Lambda functions are deployed before API Gateway:

```bash
# Deploy in correct order
cd infrastructure
./deploy.sh                    # Deploy Lambda functions first
./api_gateway_setup.sh         # Then API Gateway
```

---

### Issue 8: Cognito User Pool Already Exists

**Error:**
```
User pool with name AuditFlowUserPool already exists
```

**Solution:**
The script will use the existing pool. To recreate:

```bash
# List user pools
aws cognito-idp list-user-pools --max-results 60 --region ap-south-1

# Delete existing pool
aws cognito-idp delete-user-pool \
  --user-pool-id ap-south-1_XXXXXXXXX \
  --region ap-south-1

# Recreate
./cognito_setup.sh
```

---

### Issue 9: Step Functions State Machine Exists

**Error:**
```
State Machine already exists
```

**Solution:**
```bash
# Delete existing state machine
aws stepfunctions delete-state-machine \
  --state-machine-arn arn:aws:states:ap-south-1:ACCOUNT_ID:stateMachine:AuditFlowWorkflow \
  --region ap-south-1

# Recreate
./step_functions_deploy.sh
```

---

### Issue 10: S3 Bucket Name Conflict

**Error:**
```
Bucket name already exists
```

**Solution:**
S3 bucket names must be globally unique. Update the bucket name:

```bash
# Edit config file
nano config/prod.env

# Change S3_BUCKET_PREFIX to something unique
S3_BUCKET_PREFIX=auditflow-documents-prod-YOUR_UNIQUE_ID

# Redeploy
./s3_config.sh
```

---

### Issue 11: Region Mismatch

**Error:**
```
The security token included in the request is invalid
```

**Solution:**
Ensure all commands use ap-south-1:

```bash
# Check AWS CLI default region
aws configure get region

# Should output: ap-south-1
# If not, set it:
aws configure set region ap-south-1

# Verify all config files
grep -r "AWS_REGION" config/
```

---

### Issue 12: Lambda Function Timeout

**Error:**
```
Task timed out after 300.00 seconds
```

**Solution:**
Increase Lambda timeout in deployment script:

```bash
# Edit infrastructure/deploy.sh
# Change LAMBDA_TIMEOUT from 300 to 600

# Redeploy
./deploy.sh
```

---

### Issue 13: IAM Role Not Found

**Error:**
```
Role AuditFlowLambdaExecutionRole does not exist
```

**Solution:**
Deploy IAM roles first:

```bash
cd infrastructure
./iam_policies.sh
```

---

### Issue 14: Textract/Bedrock Not Available

**Error:**
```
Service Textract is not available in region ap-south-1
```

**Solution:**
Verify service availability:

```bash
# Check Textract
aws textract detect-document-text \
  --document '{"S3Object":{"Bucket":"test","Name":"test.pdf"}}' \
  --region ap-south-1 2>&1 | grep -i "not available"

# If not available, use us-east-1 for AI services only
# Update Lambda environment variables to use cross-region calls
```

**Note:** All services ARE available in ap-south-1, including Textract and Bedrock.

---

### Issue 15: Deployment Takes Too Long

**Symptom:** Deployment hangs or takes > 2 hours

**Solution:**
```bash
# Check CloudWatch logs for stuck operations
aws logs tail /aws/lambda/AuditFlow-Trigger --follow --region ap-south-1

# Check Step Functions executions
aws stepfunctions list-executions \
  --state-machine-arn arn:aws:states:ap-south-1:ACCOUNT_ID:stateMachine:AuditFlowWorkflow \
  --region ap-south-1

# If stuck, cancel and retry
# Press Ctrl+C and rerun the deployment script
```

---

## Debugging Commands

### Check All Resources
```bash
# KMS Keys
aws kms list-aliases --region ap-south-1 | grep auditflow

# IAM Roles
aws iam list-roles | grep AuditFlow

# S3 Buckets
aws s3 ls | grep auditflow

# DynamoDB Tables
aws dynamodb list-tables --region ap-south-1

# Lambda Functions
aws lambda list-functions --region ap-south-1 | grep AuditFlow

# Step Functions
aws stepfunctions list-state-machines --region ap-south-1

# API Gateway
aws apigateway get-rest-apis --region ap-south-1

# Cognito
aws cognito-idp list-user-pools --max-results 60 --region ap-south-1
```

### Check Logs
```bash
# Lambda logs
aws logs tail /aws/lambda/FUNCTION_NAME --follow --region ap-south-1

# Step Functions logs
aws logs tail /aws/states/AuditFlowWorkflow --follow --region ap-south-1

# API Gateway logs
aws logs tail /aws/apigateway/AuditFlowAPI --follow --region ap-south-1
```

### Verify Deployment
```bash
# Run validation script
./validate-deployment.sh -e prod -v

# Check specific service
aws lambda get-function --function-name AuditFlow-Trigger --region ap-south-1
```

---

## Getting Help

### Check Logs First
```bash
# Most recent errors
aws logs filter-log-events \
  --log-group-name /aws/lambda/AuditFlow-Trigger \
  --start-time $(date -d '10 minutes ago' +%s)000 \
  --filter-pattern "ERROR" \
  --region ap-south-1
```

### Verify Configuration
```bash
# Check all environment variables
cat config/prod.env

# Check AWS account
aws sts get-caller-identity

# Check region
aws configure get region
```

### Clean Slate (Nuclear Option)
```bash
# WARNING: This deletes everything!
./teardown-master.sh -e prod

# Wait 5 minutes for resources to be deleted

# Redeploy from scratch
./deploy-master.sh -e prod -v
```

---

## Prevention Tips

1. **Always run validation before deployment:**
   ```bash
   ./validate-deployment.sh -e prod
   ```

2. **Deploy in order:**
   - Security (KMS, IAM, Cognito)
   - Storage (S3, DynamoDB)
   - Compute (Lambda, Step Functions)
   - API (API Gateway)

3. **Check logs immediately after deployment:**
   ```bash
   aws logs tail /aws/lambda/AuditFlow-Trigger --follow --region ap-south-1
   ```

4. **Use dry-run mode:**
   ```bash
   ./deploy-master.sh -e prod --dry-run
   ```

5. **Keep backups:**
   ```bash
   # Export DynamoDB tables before major changes
   aws dynamodb scan --table-name AuditFlow-Documents --region ap-south-1 > backup.json
   ```

---

## Support Resources

- **AWS Documentation**: https://docs.aws.amazon.com/
- **AWS CLI Reference**: https://awscli.amazonaws.com/v2/documentation/api/latest/index.html
- **Project Documentation**: See `BACKEND_DEPLOYMENT_GUIDE.md`
- **Infrastructure Scripts**: See `infrastructure/README.md`

---

**Need more help?** Check the deployment logs and error messages carefully. Most issues are related to:
1. Missing AWS permissions
2. Resources already existing
3. Incorrect region configuration
4. Missing dependencies

Run `./validate-deployment.sh -e prod -v` to diagnose issues automatically.
