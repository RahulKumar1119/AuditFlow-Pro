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
Main deployment script that orchestrates all infrastructure setup:
- Creates KMS encryption keys for S3 and DynamoDB
- Creates S3 bucket for document storage with KMS encryption
- Applies S3 bucket policies for security
- Configures S3 CORS and lifecycle policies
- Creates DynamoDB tables (AuditFlow-Documents, AuditFlow-AuditRecords)
- Creates base IAM execution role for Lambda

### 2. kms_setup.sh
Creates and configures KMS encryption keys:
- Creates KMS key for S3 encryption with automatic rotation
- Creates KMS key for DynamoDB encryption
- Sets up key policies for service access (S3, Lambda, CloudWatch)
- Creates key aliases (alias/auditflow-s3-encryption, alias/auditflow-dynamodb-encryption)
- Enables annual automatic key rotation

### 3. s3_bucket_policy.sh
Configures S3 bucket security policies:
- Enforces KMS encryption for all uploads
- Denies insecure transport (requires HTTPS)
- Grants Lambda execution role access
- Enables S3 versioning
- Blocks all public access

### 4. s3_config.sh
Configures S3 bucket CORS and lifecycle policies:
- CORS configuration for frontend access
- Lifecycle policy: Archive to Glacier after 90 days
- Lifecycle policy: Delete after 7 years (2555 days)
- Server access logging configuration
- Cleanup of old object versions

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

For detailed S3 configuration information, see:
- **S3_CONFIGURATION.md**: Comprehensive guide to S3 bucket setup, security, encryption, lifecycle policies, and troubleshooting

For issues or questions, refer to:
- AWS CLI documentation: https://docs.aws.amazon.com/cli/
- AuditFlow-Pro design document: ../loan-document-auditor/design.md
- AuditFlow-Pro requirements: ../loan-document-auditor/requirements.md
