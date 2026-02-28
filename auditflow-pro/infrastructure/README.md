# AuditFlow-Pro Infrastructure

This directory contains AWS infrastructure deployment scripts for the AuditFlow-Pro loan document auditor system.

## Prerequisites

- AWS CLI installed and configured with appropriate credentials
- AWS account with permissions to create:
  - S3 buckets
  - DynamoDB tables
  - Lambda functions
  - IAM roles and policies
  - Step Functions state machines
  - API Gateway
  - Cognito User Pools and Identity Pools
  - CloudWatch Log Groups
- Bash shell environment

## Quick Start

To deploy all infrastructure:

```bash
cd infrastructure
bash deploy_all.sh
```

This will execute all deployment scripts in the correct order.

## Individual Scripts

### 1. deploy.sh
Creates base infrastructure:
- S3 bucket for document storage with encryption
- DynamoDB tables (AuditFlow-Documents, AuditFlow-AuditRecords)
- Base IAM execution role for Lambda

### 2. s3_config.sh
Configures S3 bucket:
- CORS configuration for frontend access
- Lifecycle policy (Glacier after 90 days, delete after 7 years)

### 3. dynamodb_config.sh
Configures DynamoDB tables:
- Encryption at rest using KMS
- TTL for 7-year retention
- Point-in-Time Recovery

### 4. iam_policies.sh
Creates IAM roles and policies:
- Lambda execution role with S3, DynamoDB, and AI services access
- Step Functions execution role
- API Gateway execution role
- Cognito authenticated user role

### 5. cognito_setup.sh
Sets up authentication:
- Cognito User Pool with password policies
- User Pool Client for web application
- User groups (LoanOfficers, Administrators)
- Identity Pool for AWS resource access

### 6. teardown.sh
Deletes all infrastructure (use with caution):
- Empties and deletes S3 bucket
- Deletes DynamoDB tables
- Deletes Lambda functions
- Deletes Step Functions state machine
- Deletes API Gateway
- Deletes Cognito resources
- Deletes IAM roles and policies
- Deletes CloudWatch Log Groups

## Configuration

Set the AWS region before deployment:

```bash
export AWS_REGION=us-east-1
```

Or modify the default in each script.

## Post-Deployment

After running the deployment scripts:

1. **Update Frontend Configuration**
   - Copy Cognito values from cognito_setup.sh output
   - Update `frontend/.env` with:
     - VITE_USER_POOL_ID
     - VITE_USER_POOL_CLIENT_ID
     - VITE_IDENTITY_POOL_ID
     - VITE_AWS_REGION

2. **Deploy Lambda Functions**
   - Package and deploy Lambda functions from backend/functions/
   - Use AWS CLI or SAM for deployment

3. **Create Step Functions State Machine**
   - Deploy state machine definition from backend/step_functions/state_machine.asl.json

4. **Set Up API Gateway**
   - Create REST API
   - Configure endpoints and Cognito authorizer
   - Deploy to stage

5. **Deploy Frontend**
   - Build React application
   - Deploy to AWS Amplify or S3 + CloudFront

## Resource Naming Convention

All resources follow the naming pattern:
- S3: `auditflow-documents-prod-{account-id}`
- DynamoDB: `AuditFlow-{ResourceName}`
- Lambda: `AuditFlow-{FunctionName}`
- IAM Roles: `AuditFlow{ServiceName}Role`

## Security Features

- **Encryption at Rest**: All S3 and DynamoDB data encrypted using KMS
- **Encryption in Transit**: TLS 1.2+ for all communications
- **Least Privilege**: IAM policies grant minimum required permissions
- **MFA Support**: Optional MFA for Cognito users
- **Account Lockout**: 3 failed login attempts = 15-minute lockout
- **Session Timeout**: 30-minute inactivity timeout

## Monitoring

All services log to CloudWatch:
- Lambda functions: `/aws/lambda/AuditFlow-{FunctionName}`
- Step Functions: `/aws/states/AuditFlowWorkflow`
- API Gateway: Configured via API Gateway role

Log retention: 1 year (365 days)

## Cost Optimization

- DynamoDB: Pay-per-request billing mode
- S3: Lifecycle policy moves to Glacier after 90 days
- Lambda: Automatic scaling based on demand
- CloudWatch: 1-year log retention

## Troubleshooting

### "Role already exists" errors
These are expected if re-running scripts. The script will continue.

### "Table not ready" errors
Wait a few minutes for DynamoDB tables to be fully created before running configuration scripts.

### Permission denied errors
Ensure your AWS credentials have sufficient permissions for all operations.

### Region mismatch errors
Verify AWS_REGION environment variable matches your desired region.

## Support

For issues or questions, refer to:
- AWS CLI documentation: https://docs.aws.amazon.com/cli/
- AuditFlow-Pro design document: ../loan-document-auditor/design.md
- AuditFlow-Pro requirements: ../loan-document-auditor/requirements.md
