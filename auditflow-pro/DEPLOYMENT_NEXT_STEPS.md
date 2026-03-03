# Next Steps: Backend Deployment

## Current Status
✅ **Frontend (Amplify)**: Deployed and verified  
⏳ **Backend Services**: Ready to deploy (code created, scripts ready)

## What You Have

### Backend Code (Already Created)
- ✅ 8 Lambda functions in `backend/functions/`
- ✅ Shared libraries in `backend/shared/`
- ✅ Step Functions workflow in `backend/step_functions/`
- ✅ Test suite in `backend/tests/`
- ✅ Deployment package ready

### Infrastructure Scripts (Already Created)
- ✅ 30+ deployment scripts in `infrastructure/`
- ✅ Configuration files in `config/`
- ✅ Master deployment script `deploy-master.sh`
- ✅ Validation scripts

## Quick Start: Deploy Everything

### Option 1: Automated Deployment (Recommended)
```bash
cd auditflow-pro
./deploy-master.sh -e prod -v
```

This will deploy everything in the correct order (~75 minutes).

### Option 2: Manual Step-by-Step Deployment
Follow the detailed guide:
```bash
# Open the deployment guide
cat BACKEND_DEPLOYMENT_GUIDE.md

# Or follow these quick steps:
cd infrastructure

# Phase 1: Security (15 min)
./kms_setup.sh
./iam_policies.sh
./cognito_setup.sh
./cognito_account_lockout.sh
./cognito_logging.sh

# Phase 2: Storage (10 min)
./s3_config.sh
./s3_bucket_policy.sh
./create_dynamodb_tables.sh

# Phase 3: Lambda Functions (20 min)
./deploy_trigger_lambda.sh
./deploy.sh
./deploy_api_handler.sh
./deploy_auth_logger.sh
./lambda_concurrency_setup.sh

# Phase 4: Workflow (10 min)
./step_functions_deploy.sh
./s3_event_trigger_setup.sh

# Phase 5: API Gateway (10 min)
./api_gateway_setup.sh

# Phase 6: Verify (10 min)
cd ..
./validate-deployment.sh -e prod -v
```

## Deployment Order (Critical!)

```
1. KMS Keys          → Encryption foundation
2. IAM Roles         → Permissions
3. Cognito           → Authentication
4. S3 Bucket         → Document storage
5. DynamoDB Tables   → Audit records
6. Lambda Functions  → Processing logic
7. Step Functions    → Workflow orchestration
8. API Gateway       → Frontend integration
9. Verification      → Validate everything works
```

## After Backend Deployment

### 1. Get Resource IDs
```bash
# Get API Gateway URL
API_ID=$(aws apigateway get-rest-apis --region ap-south-1 \
  --query "items[?name=='AuditFlowAPI'].id" --output text)
echo "API URL: https://${API_ID}.execute-api.ap-south-1.amazonaws.com/prod"

# Get Cognito User Pool ID
aws cognito-idp list-user-pools --max-results 60 --region ap-south-1 \
  --query "UserPools[?Name=='AuditFlowUserPool'].Id" --output text

# Get Cognito Client ID
USER_POOL_ID=$(aws cognito-idp list-user-pools --max-results 60 \
  --region ap-south-1 --query "UserPools[?Name=='AuditFlowUserPool'].Id" \
  --output text)
aws cognito-idp list-user-pool-clients --user-pool-id $USER_POOL_ID \
  --region ap-south-1 --query "UserPoolClients[0].ClientId" --output text
```

### 2. Update Amplify Frontend
```bash
# Update environment variables in Amplify Console:
# - VITE_API_GATEWAY_URL
# - VITE_COGNITO_USER_POOL_ID
# - VITE_COGNITO_CLIENT_ID
# - VITE_S3_BUCKET_NAME

# Then redeploy frontend
```

### 3. Test Integration
```bash
# Upload a test document
aws s3 cp backend/tests/fixtures/sample_w2.pdf \
  s3://auditflow-documents-prod-ACCOUNT_ID/test/

# Check Step Functions execution
aws stepfunctions list-executions \
  --state-machine-arn arn:aws:states:ap-south-1:ACCOUNT_ID:stateMachine:AuditFlowWorkflow \
  --region ap-south-1
```

## Estimated Time

| Phase | Duration | Description |
|-------|----------|-------------|
| Phase 1 | 15 min | Security foundation (KMS, IAM, Cognito) |
| Phase 2 | 10 min | Storage layer (S3, DynamoDB) |
| Phase 3 | 20 min | Lambda functions deployment |
| Phase 4 | 10 min | Workflow orchestration |
| Phase 5 | 10 min | API Gateway setup |
| Phase 6 | 10 min | Verification and testing |
| **Total** | **~75 min** | Complete backend deployment |

## Prerequisites Check

Before deploying, verify:

```bash
# 1. AWS CLI configured
aws sts get-caller-identity

# 2. Correct region
aws configure get region
# Should be: ap-south-1

# 3. Backend code exists
ls -la backend/functions/

# 4. Infrastructure scripts exist
ls -la infrastructure/

# 5. Configuration file exists
cat config/prod.env
```

## What Gets Deployed

### AWS Services
- ✅ **KMS**: 2 encryption keys (S3, DynamoDB)
- ✅ **IAM**: 4 roles (Lambda, Step Functions, API Gateway, Cognito)
- ✅ **Cognito**: User Pool + Identity Pool
- ✅ **S3**: 1 encrypted bucket with lifecycle policies
- ✅ **DynamoDB**: 2 tables (Documents, AuditRecords) with GSIs
- ✅ **Lambda**: 8 functions with dependencies
- ✅ **Step Functions**: 1 state machine with retry policies
- ✅ **API Gateway**: 1 REST API with 4 endpoints
- ✅ **CloudWatch**: Log groups for all services

### Total Resources: ~25 AWS resources

## Troubleshooting

### Common Issues

**Issue: "AWS credentials not configured"**
```bash
aws configure
# Enter your Access Key ID, Secret Access Key, and Region
```

**Issue: "Resource already exists"**
```bash
# Skip that step and continue with next
# Or use teardown script to clean up:
./teardown-master.sh -e dev
```

**Issue: "Lambda deployment fails"**
```bash
# Rebuild deployment package
cd backend
bash setup.sh
cd ..
```

**Issue: "API Gateway not accessible"**
```bash
# Check API Gateway deployment
API_ID=$(aws apigateway get-rest-apis --region ap-south-1 \
  --query "items[?name=='AuditFlowAPI'].id" --output text)
aws apigateway get-stages --rest-api-id $API_ID --region ap-south-1
```

## Verification Commands

After deployment, verify each component:

```bash
# KMS Keys
aws kms list-aliases --region ap-south-1 | grep auditflow

# IAM Roles
aws iam list-roles | grep AuditFlow

# Cognito
aws cognito-idp list-user-pools --max-results 60 --region ap-south-1

# S3 Bucket
aws s3 ls | grep auditflow

# DynamoDB Tables
aws dynamodb list-tables --region ap-south-1

# Lambda Functions
aws lambda list-functions --region ap-south-1 | grep AuditFlow

# Step Functions
aws stepfunctions list-state-machines --region ap-south-1

# API Gateway
aws apigateway get-rest-apis --region ap-south-1
```

## Documentation

- **Detailed Guide**: `BACKEND_DEPLOYMENT_GUIDE.md`
- **Infrastructure README**: `infrastructure/README.md`
- **API Gateway Guide**: `infrastructure/API_GATEWAY.md`
- **Security Guide**: `infrastructure/SECURITY.md`
- **DynamoDB Schema**: `infrastructure/DYNAMODB_SCHEMA.md`
- **Cognito Guide**: `infrastructure/COGNITO_AUTHENTICATION.md`

## Next Tasks After Backend Deployment

Once backend is deployed and verified:

1. **Task 24**: Implement monitoring and alerting
   - CloudWatch dashboards
   - SNS alerts
   - Log queries

2. **Task 25**: Implement data retention and archival
   - S3 lifecycle policies
   - DynamoDB TTL
   - Glacier archival

3. **Task 26**: Performance optimizations
   - Lambda tuning
   - DynamoDB scaling
   - Request queuing

4. **Task 30**: End-to-end integration tests
   - Complete workflow testing
   - Error scenario testing
   - Performance testing

## Quick Reference

```bash
# Deploy everything
./deploy-master.sh -e prod -v

# Verify deployment
./validate-deployment.sh -e prod -v

# Get resource IDs
cd infrastructure && ./get_resource_ids.sh

# Test end-to-end
# (Upload document → Check Step Functions → Check DynamoDB)

# Update Amplify frontend
# (Add API Gateway URL to environment variables)

# Redeploy frontend
# (Trigger build in Amplify Console)
```

## Support

For issues during deployment:
1. Check the detailed guide: `BACKEND_DEPLOYMENT_GUIDE.md`
2. Review logs: `aws logs tail /aws/lambda/FUNCTION_NAME --follow`
3. Check CloudWatch: AWS Console → CloudWatch → Logs
4. Verify IAM permissions: `./infrastructure/verify_iam_policies.sh`

---

**Ready to deploy the backend?**

Run: `./deploy-master.sh -e prod -v`

Or follow the step-by-step guide in `BACKEND_DEPLOYMENT_GUIDE.md`
