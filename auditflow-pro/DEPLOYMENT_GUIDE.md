# AuditFlow-Pro Deployment Guide

Complete step-by-step instructions for deploying the AuditFlow-Pro Loan Document Auditor system to AWS.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Pre-Deployment Setup](#pre-deployment-setup)
3. [Infrastructure Deployment](#infrastructure-deployment)
4. [Backend Deployment](#backend-deployment)
5. [Frontend Deployment](#frontend-deployment)
6. [Configuration](#configuration)
7. [Verification](#verification)
8. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Tools
- AWS CLI v2 (configured with credentials)
- Python 3.9+
- Node.js 16+ and npm
- Git
- Docker (optional, for local testing)

### AWS Account Requirements
- AWS account with appropriate permissions
- IAM user with AdministratorAccess (for initial setup)
- AWS region: us-east-1 (primary)

### Required AWS Services
- S3 (Simple Storage Service)
- DynamoDB
- Lambda
- Step Functions
- API Gateway
- Cognito
- CloudWatch
- SNS
- KMS
- Textract
- Comprehend
- Bedrock
- Amplify

### Estimated Costs
- **Development**: $50-100/month
- **Production**: $500-1000/month
- **Varies by**: Document volume, storage, API calls

---

## Pre-Deployment Setup

### 1. Clone Repository
```bash
git clone https://github.com/your-org/auditflow-pro.git
cd auditflow-pro
```

### 2. Set Environment Variables
```bash
# Create .env file
cat > .env << EOF
AWS_REGION=us-east-1
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ENVIRONMENT=production
DOMAIN_NAME=auditflowpro.online
EOF

# Load environment
source .env
```

### 3. Install Dependencies
```bash
# Backend dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Frontend dependencies
cd frontend
npm install
cd ..
```

### 4. Create S3 Bucket for Deployment Artifacts
```bash
aws s3 mb s3://auditflow-pro-deployment-${AWS_ACCOUNT_ID} \
  --region ${AWS_REGION}

# Enable versioning
aws s3api put-bucket-versioning \
  --bucket auditflow-pro-deployment-${AWS_ACCOUNT_ID} \
  --versioning-configuration Status=Enabled
```

---

## Infrastructure Deployment

### 1. Create KMS Encryption Key
```bash
# Create customer master key
KMS_KEY_ID=$(aws kms create-key \
  --description "AuditFlow-Pro encryption key" \
  --region ${AWS_REGION} \
  --query 'KeyMetadata.KeyId' \
  --output text)

# Create alias
aws kms create-alias \
  --alias-name alias/auditflow-pro \
  --target-key-id ${KMS_KEY_ID}

# Enable key rotation
aws kms enable-key-rotation --key-id ${KMS_KEY_ID}

echo "KMS_KEY_ID=${KMS_KEY_ID}" >> .env
```

### 2. Create S3 Buckets
```bash
# Documents bucket
aws s3 mb s3://auditflow-pro-documents-${AWS_ACCOUNT_ID} \
  --region ${AWS_REGION}

# Enable encryption
aws s3api put-bucket-encryption \
  --bucket auditflow-pro-documents-${AWS_ACCOUNT_ID} \
  --server-side-encryption-configuration '{
    "Rules": [{
      "ApplyServerSideEncryptionByDefault": {
        "SSEAlgorithm": "aws:kms",
        "KMSMasterKeyID": "'${KMS_KEY_ID}'"
      }
    }]
  }'

# Enable versioning
aws s3api put-bucket-versioning \
  --bucket auditflow-pro-documents-${AWS_ACCOUNT_ID} \
  --versioning-configuration Status=Enabled

# Set lifecycle policy
aws s3api put-bucket-lifecycle-configuration \
  --bucket auditflow-pro-documents-${AWS_ACCOUNT_ID} \
  --lifecycle-configuration file://lifecycle-policy.json
```

### 3. Create DynamoDB Tables
```bash
# Documents table
aws dynamodb create-table \
  --table-name auditflow-documents \
  --attribute-definitions \
    AttributeName=document_id,AttributeType=S \
    AttributeName=loan_application_id,AttributeType=S \
  --key-schema \
    AttributeName=document_id,KeyType=HASH \
  --global-secondary-indexes \
    IndexName=loan-application-index,Keys=[{AttributeName=loan_application_id,KeyType=HASH}],Projection={ProjectionType=ALL},ProvisionedThroughput={ReadCapacityUnits=10,WriteCapacityUnits=10} \
  --billing-mode PAY_PER_REQUEST \
  --region ${AWS_REGION}

# AuditRecords table
aws dynamodb create-table \
  --table-name auditflow-audit-records \
  --attribute-definitions \
    AttributeName=audit_id,AttributeType=S \
    AttributeName=loan_application_id,AttributeType=S \
    AttributeName=risk_score,AttributeType=N \
  --key-schema \
    AttributeName=audit_id,KeyType=HASH \
  --global-secondary-indexes \
    IndexName=loan-application-index,Keys=[{AttributeName=loan_application_id,KeyType=HASH}],Projection={ProjectionType=ALL},ProvisionedThroughput={ReadCapacityUnits=10,WriteCapacityUnits=10} \
    IndexName=risk-score-index,Keys=[{AttributeName=risk_score,KeyType=HASH}],Projection={ProjectionType=ALL},ProvisionedThroughput={ReadCapacityUnits=10,WriteCapacityUnits=10} \
  --billing-mode PAY_PER_REQUEST \
  --region ${AWS_REGION}

# Enable TTL
aws dynamodb update-time-to-live \
  --table-name auditflow-audit-records \
  --time-to-live-specification AttributeName=expiration_time,Enabled=true
```

### 4. Create IAM Roles
```bash
# Lambda execution role
aws iam create-role \
  --role-name auditflow-lambda-role \
  --assume-role-policy-document file://lambda-trust-policy.json

# Attach policies
aws iam attach-role-policy \
  --role-name auditflow-lambda-role \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

# Add custom policy for S3, DynamoDB, KMS
aws iam put-role-policy \
  --role-name auditflow-lambda-role \
  --policy-name auditflow-lambda-policy \
  --policy-document file://lambda-policy.json
```

### 5. Create Cognito User Pool
```bash
# Create user pool
USER_POOL_ID=$(aws cognito-idp create-user-pool \
  --pool-name auditflow-pro \
  --policies file://cognito-policy.json \
  --mfa-configuration ON \
  --query 'UserPool.Id' \
  --output text)

# Create user pool client
CLIENT_ID=$(aws cognito-idp create-user-pool-client \
  --user-pool-id ${USER_POOL_ID} \
  --client-name auditflow-web \
  --explicit-auth-flows ALLOW_USER_PASSWORD_AUTH ALLOW_REFRESH_TOKEN_AUTH \
  --query 'UserPoolClient.ClientId' \
  --output text)

# Create identity pool
IDENTITY_POOL_ID=$(aws cognito-identity create-identity-pool \
  --identity-pool-name auditflow-pro \
  --allow-unauthenticated-identities false \
  --cognito-identity-providers ProviderName=cognito-idp.${AWS_REGION}.amazonaws.com/${USER_POOL_ID},ClientId=${CLIENT_ID} \
  --query 'IdentityPoolId' \
  --output text)

echo "USER_POOL_ID=${USER_POOL_ID}" >> .env
echo "CLIENT_ID=${CLIENT_ID}" >> .env
echo "IDENTITY_POOL_ID=${IDENTITY_POOL_ID}" >> .env
```

---

## Backend Deployment

### 1. Package Lambda Functions
```bash
# Create deployment package
mkdir -p build
cd build

# Copy Lambda functions
cp -r ../lambda/* .

# Install dependencies
pip install -r requirements.txt -t .

# Create zip
zip -r ../lambda-deployment.zip .
cd ..
```

### 2. Deploy Lambda Functions
```bash
# Classifier Lambda
aws lambda create-function \
  --function-name auditflow-classifier \
  --runtime python3.9 \
  --role arn:aws:iam::${AWS_ACCOUNT_ID}:role/auditflow-lambda-role \
  --handler classifier.lambda_handler \
  --zip-file fileb://lambda-deployment.zip \
  --timeout 300 \
  --memory-size 1024 \
  --environment Variables={KMS_KEY_ID=${KMS_KEY_ID}} \
  --region ${AWS_REGION}

# Extractor Lambda
aws lambda create-function \
  --function-name auditflow-extractor \
  --runtime python3.9 \
  --role arn:aws:iam::${AWS_ACCOUNT_ID}:role/auditflow-lambda-role \
  --handler extractor.lambda_handler \
  --zip-file fileb://lambda-deployment.zip \
  --timeout 300 \
  --memory-size 1024 \
  --environment Variables={KMS_KEY_ID=${KMS_KEY_ID}} \
  --region ${AWS_REGION}

# Validator Lambda
aws lambda create-function \
  --function-name auditflow-validator \
  --runtime python3.9 \
  --role arn:aws:iam::${AWS_ACCOUNT_ID}:role/auditflow-lambda-role \
  --handler validator.lambda_handler \
  --zip-file fileb://lambda-deployment.zip \
  --timeout 300 \
  --memory-size 1024 \
  --environment Variables={KMS_KEY_ID=${KMS_KEY_ID}} \
  --region ${AWS_REGION}

# Risk Scorer Lambda
aws lambda create-function \
  --function-name auditflow-risk-scorer \
  --runtime python3.9 \
  --role arn:aws:iam::${AWS_ACCOUNT_ID}:role/auditflow-lambda-role \
  --handler risk_scorer.lambda_handler \
  --zip-file fileb://lambda-deployment.zip \
  --timeout 300 \
  --memory-size 1024 \
  --environment Variables={KMS_KEY_ID=${KMS_KEY_ID}} \
  --region ${AWS_REGION}

# Report Generator Lambda
aws lambda create-function \
  --function-name auditflow-report-generator \
  --runtime python3.9 \
  --role arn:aws:iam::${AWS_ACCOUNT_ID}:role/auditflow-lambda-role \
  --handler report_generator.lambda_handler \
  --zip-file fileb://lambda-deployment.zip \
  --timeout 300 \
  --memory-size 1024 \
  --environment Variables={KMS_KEY_ID=${KMS_KEY_ID}} \
  --region ${AWS_REGION}
```

### 3. Create Step Functions State Machine
```bash
# Create state machine
STATE_MACHINE_ARN=$(aws stepfunctions create-state-machine \
  --name auditflow-workflow \
  --definition file://state-machine-definition.json \
  --role-arn arn:aws:iam::${AWS_ACCOUNT_ID}:role/auditflow-stepfunctions-role \
  --query 'stateMachineArn' \
  --output text)

echo "STATE_MACHINE_ARN=${STATE_MACHINE_ARN}" >> .env
```

### 4. Create API Gateway
```bash
# Create REST API
API_ID=$(aws apigateway create-rest-api \
  --name auditflow-api \
  --description "AuditFlow-Pro API" \
  --query 'id' \
  --output text)

# Create authorizer
AUTHORIZER_ID=$(aws apigateway create-authorizer \
  --rest-api-id ${API_ID} \
  --name cognito-authorizer \
  --type COGNITO_USER_POOLS \
  --provider-arns arn:aws:cognito-idp:${AWS_REGION}:${AWS_ACCOUNT_ID}:userpool/${USER_POOL_ID} \
  --query 'id' \
  --output text)

# Create resources and methods (see API configuration)
# Deploy API
aws apigateway create-deployment \
  --rest-api-id ${API_ID} \
  --stage-name prod

echo "API_ID=${API_ID}" >> .env
```

---

## Frontend Deployment

### 1. Build React Application
```bash
cd frontend
npm run build
cd ..
```

### 2. Deploy to AWS Amplify
```bash
# Initialize Amplify
amplify init --yes

# Add hosting
amplify add hosting

# Configure domain
amplify update hosting

# Deploy
amplify publish
```

### 3. Configure Custom Domain
```bash
# Request SSL certificate
aws acm request-certificate \
  --domain-name auditflowpro.online \
  --validation-method DNS \
  --region ${AWS_REGION}

# Update Route 53 DNS records
# (Manual step: verify domain ownership)

# Associate certificate with Amplify
# (Done through AWS Console)
```

---

## Configuration

### 1. Environment Variables
Create `config.json` in frontend:
```json
{
  "aws_region": "us-east-1",
  "cognito_user_pool_id": "us-east-1_xxxxx",
  "cognito_client_id": "xxxxx",
  "cognito_identity_pool_id": "us-east-1:xxxxx",
  "api_endpoint": "https://api.auditflowpro.online",
  "s3_bucket": "auditflow-pro-documents-xxxxx"
}
```

### 2. Lambda Environment Variables
```bash
# Set for all Lambda functions
aws lambda update-function-configuration \
  --function-name auditflow-classifier \
  --environment Variables={
    KMS_KEY_ID=${KMS_KEY_ID},
    DYNAMODB_TABLE=auditflow-documents,
    S3_BUCKET=auditflow-pro-documents-${AWS_ACCOUNT_ID}
  }
```

### 3. SNS Topics for Alerts
```bash
# Create SNS topic
SNS_TOPIC_ARN=$(aws sns create-topic \
  --name auditflow-alerts \
  --query 'TopicArn' \
  --output text)

# Subscribe email
aws sns subscribe \
  --topic-arn ${SNS_TOPIC_ARN} \
  --protocol email \
  --notification-endpoint admin@example.com

echo "SNS_TOPIC_ARN=${SNS_TOPIC_ARN}" >> .env
```

---

## Verification

### 1. Test Infrastructure
```bash
# Verify S3 buckets
aws s3 ls | grep auditflow-pro

# Verify DynamoDB tables
aws dynamodb list-tables --region ${AWS_REGION}

# Verify Lambda functions
aws lambda list-functions --region ${AWS_REGION} | grep auditflow

# Verify Cognito
aws cognito-idp describe-user-pool --user-pool-id ${USER_POOL_ID}
```

### 2. Test API Endpoints
```bash
# Get authentication token
TOKEN=$(aws cognito-idp admin-initiate-auth \
  --user-pool-id ${USER_POOL_ID} \
  --client-id ${CLIENT_ID} \
  --auth-flow ADMIN_NO_SRP_AUTH \
  --auth-parameters USERNAME=testuser,PASSWORD=TestPassword123! \
  --query 'AuthenticationResult.AccessToken' \
  --output text)

# Test API
curl -H "Authorization: Bearer ${TOKEN}" \
  https://api.auditflowpro.online/audits
```

### 3. Test Document Upload
1. Navigate to https://auditflowpro.online
2. Login with test credentials
3. Upload sample document
4. Verify processing in CloudWatch logs
5. Check audit record in DynamoDB

### 4. Monitor CloudWatch Logs
```bash
# View Lambda logs
aws logs tail /aws/lambda/auditflow-classifier --follow

# View Step Functions logs
aws logs tail /aws/stepfunctions/auditflow-workflow --follow
```

---

## Troubleshooting

### Common Issues

#### Lambda Timeout
**Problem**: Lambda functions timing out  
**Solution**:
```bash
# Increase timeout
aws lambda update-function-configuration \
  --function-name auditflow-classifier \
  --timeout 600
```

#### DynamoDB Throttling
**Problem**: DynamoDB write throttling  
**Solution**:
```bash
# Enable auto-scaling
aws application-autoscaling register-scalable-target \
  --service-namespace dynamodb \
  --resource-id table/auditflow-documents \
  --scalable-dimension dynamodb:table:WriteCapacityUnits \
  --min-capacity 10 \
  --max-capacity 100
```

#### API Gateway CORS Issues
**Problem**: Frontend CORS errors  
**Solution**:
```bash
# Enable CORS on API Gateway
aws apigateway put-integration-response \
  --rest-api-id ${API_ID} \
  --resource-id ${RESOURCE_ID} \
  --http-method OPTIONS \
  --status-code 200 \
  --response-parameters '{"method.response.header.Access-Control-Allow-Headers":"'"'"'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'"'"'","method.response.header.Access-Control-Allow-Methods":"'"'"'GET,POST,PUT,DELETE,OPTIONS'"'"'","method.response.header.Access-Control-Allow-Origin":"'"'"'*'"'"'"}' \
  --response-templates '{"application/json":""}'
```

#### Cognito Authentication Failures
**Problem**: Users unable to login  
**Solution**:
```bash
# Reset user password
aws cognito-idp admin-set-user-password \
  --user-pool-id ${USER_POOL_ID} \
  --username testuser \
  --password NewPassword123! \
  --permanent
```

### Debugging Commands

```bash
# Check Lambda function logs
aws logs get-log-events \
  --log-group-name /aws/lambda/auditflow-classifier \
  --log-stream-name $(aws logs describe-log-streams --log-group-name /aws/lambda/auditflow-classifier --query 'logStreams[0].logStreamName' --output text)

# Check Step Functions execution
aws stepfunctions describe-execution \
  --execution-arn arn:aws:states:${AWS_REGION}:${AWS_ACCOUNT_ID}:execution:auditflow-workflow:execution-id

# Check DynamoDB item
aws dynamodb get-item \
  --table-name auditflow-documents \
  --key '{"document_id":{"S":"doc-123"}}'

# Check S3 object
aws s3 ls s3://auditflow-pro-documents-${AWS_ACCOUNT_ID}/
```

---

## Post-Deployment

### 1. Create Admin User
```bash
aws cognito-idp admin-create-user \
  --user-pool-id ${USER_POOL_ID} \
  --username admin@example.com \
  --user-attributes Name=email,Value=admin@example.com Name=email_verified,Value=true \
  --message-action SUPPRESS

# Set permanent password
aws cognito-idp admin-set-user-password \
  --user-pool-id ${USER_POOL_ID} \
  --username admin@example.com \
  --password AdminPassword123! \
  --permanent
```

### 2. Enable CloudWatch Alarms
```bash
# Lambda error alarm
aws cloudwatch put-metric-alarm \
  --alarm-name auditflow-lambda-errors \
  --alarm-description "Alert on Lambda errors" \
  --metric-name Errors \
  --namespace AWS/Lambda \
  --statistic Sum \
  --period 300 \
  --threshold 5 \
  --comparison-operator GreaterThanThreshold \
  --alarm-actions ${SNS_TOPIC_ARN}
```

### 3. Set Up Backup
```bash
# Enable DynamoDB point-in-time recovery
aws dynamodb update-continuous-backups \
  --table-name auditflow-documents \
  --point-in-time-recovery-specification PointInTimeRecoveryEnabled=true
```

---

**Document Version**: 1.0  
**Last Updated**: 2026-03-22  
**Status**: Production Ready
