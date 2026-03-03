# Backend Deployment Guide - AuditFlow-Pro

## Overview

This guide walks you through deploying all backend services for AuditFlow-Pro in the correct order. The frontend (Amplify) is already deployed, and now we need to set up the backend infrastructure and services.

## Architecture Components

### Backend Services
- **Lambda Functions**: 8 functions (Trigger, Classifier, Extractor, Validator, Risk Scorer, Reporter, API Handler, Auth Logger)
- **Step Functions**: Workflow orchestration
- **Storage**: S3 (documents), DynamoDB (audit records)
- **AI Services**: Textract, Bedrock, Comprehend
- **Security**: Cognito, KMS, IAM
- **API**: API Gateway

## Prerequisites

Before starting deployment:

```bash
# 1. Verify AWS CLI is configured
aws sts get-caller-identity

# 2. Verify you're in the correct directory
cd auditflow-pro

# 3. Verify backend code exists
ls -la backend/functions/

# 4. Verify infrastructure scripts exist
ls -la infrastructure/
```

## Deployment Order

Follow this exact order to avoid dependency issues:

### Phase 1: Security Foundation (15 minutes)
### Phase 2: Storage Layer (10 minutes)
### Phase 3: Lambda Functions (20 minutes)
### Phase 4: Workflow Orchestration (10 minutes)
### Phase 5: API Gateway (10 minutes)
### Phase 6: Verification (10 minutes)

**Total Time: ~75 minutes**

---

## Phase 1: Security Foundation

### Step 1.1: Configure KMS Encryption Keys
```bash
cd infrastructure
./kms_setup.sh
```

**What this does:**
- Creates KMS keys for S3 and DynamoDB encryption
- Enables automatic key rotation
- Sets up key policies

**Verify:**
```bash
aws kms list-aliases --region ap-south-1 | grep auditflow
```

### Step 1.2: Set Up IAM Roles and Policies
```bash
./iam_policies.sh
```

**What this does:**
- Creates Lambda execution roles
- Creates Step Functions execution role
- Creates API Gateway role
- Sets up least-privilege policies

**Verify:**
```bash
aws iam list-roles | grep AuditFlow
```

### Step 1.3: Configure Cognito Authentication
```bash
./cognito_setup.sh
```

**What this does:**
- Creates User Pool with email/password auth
- Creates Identity Pool
- Sets up user groups (Loan Officer, Administrator)
- Configures MFA and password policies

**Verify:**
```bash
aws cognito-idp list-user-pools --max-results 60 --region ap-south-1 | grep AuditFlow
```

### Step 1.4: Configure Account Lockout
```bash
./cognito_account_lockout.sh
```

**What this does:**
- Implements account lockout after 3 failed attempts
- Sets lockout duration to 15 minutes

### Step 1.5: Enable Authentication Logging
```bash
./cognito_logging.sh
```

**What this does:**
- Logs all authentication events to CloudWatch
- Redacts PII from logs

---

## Phase 2: Storage Layer

### Step 2.1: Create S3 Bucket
```bash
./s3_config.sh
```

**What this does:**
- Creates encrypted S3 bucket for documents
- Enables versioning
- Configures lifecycle policies (Glacier after 90 days)
- Sets up CORS for frontend access

**Verify:**
```bash
aws s3 ls | grep auditflow
```

### Step 2.2: Configure S3 Bucket Policies
```bash
./s3_bucket_policy.sh
```

**What this does:**
- Blocks public access
- Grants Lambda read/write access
- Enforces encryption

### Step 2.3: Create DynamoDB Tables
```bash
./create_dynamodb_tables.sh
```

**What this does:**
- Creates Documents table
- Creates AuditRecords table
- Sets up GSIs for querying
- Enables encryption at rest
- Configures TTL

**Verify:**
```bash
aws dynamodb list-tables --region ap-south-1
```

---

## Phase 3: Lambda Functions

### Step 3.1: Deploy Trigger Lambda
```bash
./deploy_trigger_lambda.sh
```

**What this does:**
- Deploys S3 event trigger Lambda
- Configures S3 event notifications
- Sets concurrency limits

**Verify:**
```bash
aws lambda get-function --function-name AuditFlow-Trigger --region ap-south-1
```

### Step 3.2: Deploy All Processing Lambdas
```bash
./deploy.sh
```

**What this does:**
- Deploys Classifier Lambda
- Deploys Extractor Lambda
- Deploys Validator Lambda
- Deploys Risk Scorer Lambda
- Deploys Reporter Lambda
- Packages dependencies
- Sets environment variables

**Verify:**
```bash
aws lambda list-functions --region ap-south-1 | grep AuditFlow
```

### Step 3.3: Deploy API Handler Lambda
```bash
./deploy_api_handler.sh
```

**What this does:**
- Deploys API Gateway integration Lambda
- Handles document upload, audit queries, document viewing

### Step 3.4: Deploy Auth Logger Lambda
```bash
./deploy_auth_logger.sh
```

**What this does:**
- Deploys authentication logging Lambda
- Connects to Cognito triggers

### Step 3.5: Configure Lambda Concurrency
```bash
./lambda_concurrency_setup.sh
```

**What this does:**
- Sets max concurrent executions (10 for Trigger, 100 for others)
- Implements queuing for excess requests

---

## Phase 4: Workflow Orchestration

### Step 4.1: Deploy Step Functions State Machine
```bash
./step_functions_deploy.sh
```

**What this does:**
- Creates Step Functions state machine
- Configures workflow stages
- Sets up retry policies
- Enables CloudWatch logging

**Verify:**
```bash
aws stepfunctions list-state-machines --region ap-south-1 | grep AuditFlow
```

### Step 4.2: Configure S3 Event Triggers
```bash
./s3_event_trigger_setup.sh
```

**What this does:**
- Connects S3 uploads to Trigger Lambda
- Filters for supported file formats (PDF, JPEG, PNG, TIFF)
- Initiates Step Functions workflow

---

## Phase 5: API Gateway

### Step 5.1: Create API Gateway
```bash
./api_gateway_setup.sh
```

**What this does:**
- Creates REST API
- Configures Cognito authorizer
- Creates endpoints:
  - POST /documents (upload)
  - GET /audits (list audits)
  - GET /audits/{id} (get audit details)
  - GET /documents/{id}/view (view document)
- Enables CORS
- Enforces TLS 1.2+

**Verify:**
```bash
aws apigateway get-rest-apis --region ap-south-1 | grep AuditFlow
```

### Step 5.2: Deploy API to Stage
```bash
# Get API ID
API_ID=$(aws apigateway get-rest-apis --region ap-south-1 --query "items[?name=='AuditFlowAPI'].id" --output text)

# Deploy to prod stage
aws apigateway create-deployment \
  --rest-api-id $API_ID \
  --stage-name prod \
  --region ap-south-1
```

### Step 5.3: Get API Endpoint
```bash
echo "API Endpoint: https://${API_ID}.execute-api.ap-south-1.amazonaws.com/prod"
```

**Save this endpoint** - you'll need it for frontend configuration!

---

## Phase 6: Verification

### Step 6.1: Run Backend Validation
```bash
cd ..
./validate-deployment.sh -e prod -v
```

**What this checks:**
- AWS credentials
- KMS keys
- S3 bucket configuration
- DynamoDB tables
- IAM roles
- Lambda functions
- Step Functions
- API Gateway
- Cognito
- CloudWatch logs

### Step 6.2: Test End-to-End Flow
```bash
# 1. Upload a test document
aws s3 cp backend/tests/fixtures/sample_w2.pdf \
  s3://auditflow-documents-prod-$(aws sts get-caller-identity --query Account --output text)/test/

# 2. Check Step Functions execution
aws stepfunctions list-executions \
  --state-machine-arn arn:aws:states:ap-south-1:ACCOUNT_ID:stateMachine:AuditFlowWorkflow \
  --region ap-south-1

# 3. Check DynamoDB for audit record
aws dynamodb scan \
  --table-name AuditFlow-Documents \
  --limit 5 \
  --region ap-south-1
```

---

## Post-Deployment Configuration

### Update Frontend Environment Variables

After deployment, update Amplify with the API Gateway endpoint:

```bash
# Get API Gateway URL
API_ID=$(aws apigateway get-rest-apis --region ap-south-1 --query "items[?name=='AuditFlowAPI'].id" --output text)
API_URL="https://${API_ID}.execute-api.ap-south-1.amazonaws.com/prod"

# Get Cognito User Pool ID
USER_POOL_ID=$(aws cognito-idp list-user-pools --max-results 60 --region ap-south-1 --query "UserPools[?Name=='AuditFlowUserPool'].Id" --output text)

# Get Cognito Client ID
CLIENT_ID=$(aws cognito-idp list-user-pool-clients --user-pool-id $USER_POOL_ID --region ap-south-1 --query "UserPoolClients[0].ClientId" --output text)

# Get S3 Bucket Name
BUCKET_NAME=$(aws s3 ls | grep auditflow-documents | awk '{print $3}')

echo "Update Amplify with these values:"
echo "VITE_API_GATEWAY_URL=$API_URL"
echo "VITE_COGNITO_USER_POOL_ID=$USER_POOL_ID"
echo "VITE_COGNITO_CLIENT_ID=$CLIENT_ID"
echo "VITE_S3_BUCKET_NAME=$BUCKET_NAME"
```

**Update in Amplify Console:**
1. Go to AWS Amplify Console
2. Select your app
3. Go to App Settings > Environment variables
4. Update the values above
5. Redeploy the frontend

---

## Quick Deployment Script

For automated deployment, use the master script:

```bash
cd auditflow-pro
./deploy-master.sh
```

This runs all deployment steps in order.

---

## Troubleshooting

### Issue: KMS Key Creation Fails
```bash
# Check if keys already exist
aws kms list-aliases --region ap-south-1 | grep auditflow

# If they exist, skip kms_setup.sh
```

### Issue: Lambda Deployment Fails
```bash
# Check if deployment package exists
ls -lh backend/deployment_package.zip

# If missing, rebuild:
cd backend
bash setup.sh
```

### Issue: DynamoDB Table Already Exists
```bash
# Check existing tables
aws dynamodb list-tables --region ap-south-1

# If tables exist, skip create_dynamodb_tables.sh
```

### Issue: API Gateway Deployment Fails
```bash
# Check API Gateway logs
aws logs tail /aws/apigateway/AuditFlowAPI --follow --region ap-south-1
```

### Issue: Step Functions Execution Fails
```bash
# Get execution ARN
EXECUTION_ARN=$(aws stepfunctions list-executions \
  --state-machine-arn arn:aws:states:ap-south-1:ACCOUNT_ID:stateMachine:AuditFlowWorkflow \
  --max-results 1 \
  --query 'executions[0].executionArn' \
  --output text \
  --region ap-south-1)

# Get execution history
aws stepfunctions get-execution-history \
  --execution-arn $EXECUTION_ARN \
  --region ap-south-1
```

---

## Next Steps After Deployment

1. ✅ **Update Frontend** - Configure Amplify with API endpoint
2. 🧪 **Test Integration** - Upload test documents
3. 📊 **Set Up Monitoring** - Task 24 (CloudWatch dashboards, alerts)
4. 📁 **Configure Archival** - Task 25 (S3 lifecycle, DynamoDB TTL)
5. ⚡ **Optimize Performance** - Task 26 (Lambda tuning, DynamoDB scaling)
6. 🧪 **Run E2E Tests** - Task 30 (End-to-end integration tests)

---

## Resource Identifiers

After deployment, save these for reference:

```bash
# Get all resource IDs
./infrastructure/get_resource_ids.sh > resource_ids.txt
```

---

## Support

- **Deployment Issues**: Check `infrastructure/README.md`
- **Lambda Issues**: Check `backend/functions/*/README.md`
- **API Issues**: Check `infrastructure/API_GATEWAY.md`
- **Security Issues**: Check `infrastructure/SECURITY.md`

---

## Deployment Checklist

- [ ] Phase 1: Security Foundation
  - [ ] KMS keys created
  - [ ] IAM roles created
  - [ ] Cognito configured
  - [ ] Account lockout enabled
  - [ ] Authentication logging enabled

- [ ] Phase 2: Storage Layer
  - [ ] S3 bucket created
  - [ ] Bucket policies configured
  - [ ] DynamoDB tables created

- [ ] Phase 3: Lambda Functions
  - [ ] Trigger Lambda deployed
  - [ ] Processing Lambdas deployed
  - [ ] API Handler deployed
  - [ ] Auth Logger deployed
  - [ ] Concurrency configured

- [ ] Phase 4: Workflow Orchestration
  - [ ] Step Functions deployed
  - [ ] S3 event triggers configured

- [ ] Phase 5: API Gateway
  - [ ] API Gateway created
  - [ ] API deployed to stage
  - [ ] Endpoint URL obtained

- [ ] Phase 6: Verification
  - [ ] Backend validation passed
  - [ ] End-to-end test successful

- [ ] Post-Deployment
  - [ ] Frontend environment variables updated
  - [ ] Frontend redeployed
  - [ ] Integration tested

---

**Ready to deploy?** Start with Phase 1: `cd infrastructure && ./kms_setup.sh`
