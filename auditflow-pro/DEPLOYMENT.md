# AuditFlow-Pro Deployment Guide

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start](#quick-start)
3. [Environment Configuration](#environment-configuration)
4. [Deployment Scripts](#deployment-scripts)
5. [Multi-Region Deployment](#multi-region-deployment)
6. [Validation](#validation)
7. [Teardown](#teardown)
8. [Troubleshooting](#troubleshooting)

## Prerequisites

### Required Tools

- **AWS CLI** (v2.0 or higher)
  ```bash
  aws --version
  ```

- **Bash** (v4.0 or higher)
  ```bash
  bash --version
  ```

- **jq** (optional but recommended for JSON processing)
  ```bash
  jq --version
  ```

### AWS Account Requirements

- AWS account with appropriate permissions
- IAM user or role with permissions to create:
  - S3 buckets
  - DynamoDB tables
  - Lambda functions
  - IAM roles and policies
  - Step Functions state machines
  - API Gateway
  - Cognito User Pools and Identity Pools
  - CloudWatch Log Groups
  - KMS keys

### AWS Credentials

Configure AWS credentials before deployment:

```bash
aws configure
# OR
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_DEFAULT_REGION=ap-south-1
```

Verify credentials:
```bash
aws sts get-caller-identity
```


## Quick Start

### 1. Validate Configuration

Before deployment, validate your environment configuration:

```bash
./validate-config.sh -e dev
```

### 2. Deploy Infrastructure

Deploy to development environment:

```bash
./deploy-master.sh -e dev
```

Deploy to production:

```bash
./deploy-master.sh -e prod
```

### 3. Validate Deployment

After deployment, validate all resources:

```bash
./validate-deployment.sh -e dev
```

### 4. Access Resources

The validation script will output all resource identifiers and endpoints.

## Environment Configuration

### Configuration Files

Environment-specific configuration files are located in `config/`:

- `config/dev.env` - Development environment
- `config/staging.env` - Staging environment
- `config/prod.env` - Production environment

### Configuration Parameters

#### Basic Settings
- `ENVIRONMENT` - Environment name (dev, staging, prod)
- `AWS_REGION` - AWS region for deployment
- `PROJECT_NAME` - Project identifier
- `STACK_NAME` - CloudFormation stack name

#### S3 Configuration
- `S3_BUCKET_PREFIX` - Prefix for S3 bucket names
- `ENABLE_S3_VERSIONING` - Enable S3 versioning (true/false)
- `S3_LIFECYCLE_GLACIER_DAYS` - Days before archiving to Glacier
- `S3_LIFECYCLE_EXPIRATION_DAYS` - Days before deletion

#### DynamoDB Configuration
- `DYNAMODB_BILLING_MODE` - Billing mode (PAY_PER_REQUEST or PROVISIONED)
- `ENABLE_POINT_IN_TIME_RECOVERY` - Enable PITR (true/false)
- `TTL_ATTRIBUTE_NAME` - TTL attribute name

#### Lambda Configuration
- `LAMBDA_MEMORY_SIZE` - Memory allocation in MB (128-10240)
- `LAMBDA_TIMEOUT` - Timeout in seconds (3-900)
- `LAMBDA_RUNTIME` - Python runtime version
- `MAX_CONCURRENT_EXECUTIONS` - Max concurrent Lambda executions


#### Security Configuration
- `ENABLE_KMS_ENCRYPTION` - Enable KMS encryption (true/false)
- `KMS_KEY_ROTATION_ENABLED` - Enable automatic key rotation (true/false)
- `TLS_MINIMUM_VERSION` - Minimum TLS version (TLS_1_2 or TLS_1_3)

#### Monitoring Configuration
- `LOG_RETENTION_DAYS` - CloudWatch log retention period
- `ENABLE_CLOUDWATCH_ALARMS` - Enable CloudWatch alarms (true/false)
- `ALERT_EMAIL` - Email address for alerts

### Customizing Configuration

1. Copy an existing environment file:
   ```bash
   cp config/dev.env config/custom.env
   ```

2. Edit the configuration:
   ```bash
   nano config/custom.env
   ```

3. Validate the configuration:
   ```bash
   ./validate-config.sh -c config/custom.env
   ```

4. Deploy with custom configuration:
   ```bash
   ./deploy-master.sh -c config/custom.env
   ```

## Deployment Scripts

### deploy-master.sh

Master deployment script that orchestrates all infrastructure deployment.

**Usage:**
```bash
./deploy-master.sh [OPTIONS]
```

**Options:**
- `-e, --environment ENV` - Environment to deploy (dev, staging, prod)
- `-c, --config FILE` - Path to configuration file
- `-r, --region REGION` - AWS region (overrides config)
- `-d, --dry-run` - Show deployment plan without making changes
- `-s, --skip-validation` - Skip pre-deployment validation
- `-v, --verbose` - Enable verbose output
- `-h, --help` - Show help message

**Examples:**
```bash
# Deploy to development
./deploy-master.sh -e dev

# Deploy to production with verbose output
./deploy-master.sh -e prod -v

# Dry run for staging
./deploy-master.sh -e staging --dry-run

# Deploy to specific region
./deploy-master.sh -e prod -r us-east-1
```


### validate-config.sh

Validates environment configuration before deployment.

**Usage:**
```bash
./validate-config.sh [OPTIONS]
```

**Options:**
- `-e, --environment ENV` - Environment to validate
- `-c, --config FILE` - Path to configuration file
- `-h, --help` - Show help message

**Examples:**
```bash
# Validate development configuration
./validate-config.sh -e dev

# Validate custom configuration
./validate-config.sh -c config/custom.env
```

### validate-deployment.sh

Validates deployed infrastructure and tests connectivity.

**Usage:**
```bash
./validate-deployment.sh [OPTIONS]
```

**Options:**
- `-e, --environment ENV` - Environment to validate
- `-c, --config FILE` - Path to configuration file
- `-v, --verbose` - Enable verbose output
- `-h, --help` - Show help message

**Examples:**
```bash
# Validate development deployment
./validate-deployment.sh -e dev

# Validate with verbose output
./validate-deployment.sh -e prod -v
```

### teardown-master.sh

Safely removes all infrastructure in the correct order.

**Usage:**
```bash
./teardown-master.sh [OPTIONS]
```

**Options:**
- `-e, --environment ENV` - Environment to tear down
- `-c, --config FILE` - Path to configuration file
- `-f, --force` - Skip confirmation prompt
- `-d, --dry-run` - Show what would be deleted
- `-k, --keep-data` - Keep S3 and DynamoDB data
- `-h, --help` - Show help message

**Examples:**
```bash
# Tear down development (with confirmation)
./teardown-master.sh -e dev

# Force tear down without confirmation
./teardown-master.sh -e dev --force

# Dry run to see what would be deleted
./teardown-master.sh -e staging --dry-run

# Keep data, delete only compute resources
./teardown-master.sh -e dev --keep-data
```


## Multi-Region Deployment

### deploy-multi-region.sh

Deploys infrastructure to multiple AWS regions for high availability.

**Usage:**
```bash
./deploy-multi-region.sh [OPTIONS]
```

**Options:**
- `-e, --environment ENV` - Environment to deploy
- `-p, --primary-region REG` - Primary AWS region (required)
- `-s, --secondary-region REG` - Secondary region (can be specified multiple times)
- `-c, --config FILE` - Path to configuration file
- `-d, --dry-run` - Show deployment plan
- `--parallel` - Deploy to all regions in parallel
- `-h, --help` - Show help message

**Examples:**
```bash
# Deploy to primary and one secondary region
./deploy-multi-region.sh -p us-east-1 -s us-west-2

# Deploy to multiple regions
./deploy-multi-region.sh -p ap-south-1 -s us-east-1 -s eu-west-1

# Parallel deployment (faster)
./deploy-multi-region.sh -p us-east-1 -s us-west-2 --parallel
```

### Multi-Region Features

The multi-region deployment configures:

1. **DynamoDB Global Tables** - Cross-region replication for audit records
2. **S3 Cross-Region Replication** - Disaster recovery for documents
3. **Regional Lambda Functions** - Compute in each region
4. **Regional API Gateways** - Low-latency API access
5. **Route53 Health Checks** - Automatic failover (manual configuration required)

### Multi-Region Architecture

```
Primary Region (ap-south-1)
├── All infrastructure components
├── DynamoDB Global Table (primary)
├── S3 bucket with replication
└── API Gateway (primary endpoint)

Secondary Region (us-east-1)
├── All infrastructure components
├── DynamoDB Global Table (replica)
├── S3 bucket (replication target)
└── API Gateway (failover endpoint)
```

### Route53 Failover Configuration

After multi-region deployment, manually configure Route53:

1. Create health checks for each regional API Gateway
2. Create Route53 hosted zone for your domain
3. Create failover routing policy with primary and secondary records
4. Associate health checks with each record


## Validation

### Pre-Deployment Validation

Always validate configuration before deployment:

```bash
./validate-config.sh -e prod
```

This checks:
- Required parameters are set
- Values are within valid ranges
- Environment-specific requirements are met
- Configuration format is correct

### Post-Deployment Validation

After deployment, validate all resources:

```bash
./validate-deployment.sh -e prod
```

This verifies:
- All AWS resources are created
- Encryption is enabled
- IAM policies are correct
- Services can communicate
- Endpoints are accessible

### Validation Output

The validation script provides:
- Resource identifiers (ARNs, IDs)
- Endpoint URLs
- Configuration status
- Connectivity test results
- Summary of passed/failed checks

## Teardown

### Safe Teardown Process

1. **Backup Data** (if needed):
   ```bash
   # Export DynamoDB tables
   aws dynamodb export-table-to-point-in-time \
     --table-arn arn:aws:dynamodb:region:account:table/AuditFlow-Documents \
     --s3-bucket backup-bucket
   
   # Sync S3 bucket
   aws s3 sync s3://auditflow-documents-prod-account backup/
   ```

2. **Dry Run**:
   ```bash
   ./teardown-master.sh -e dev --dry-run
   ```

3. **Execute Teardown**:
   ```bash
   ./teardown-master.sh -e dev
   ```

4. **Verify Cleanup**:
   ```bash
   # Check for remaining resources
   aws resourcegroupstaggingapi get-resources \
     --tag-filters Key=Project,Values=auditflow-pro
   ```

### Partial Teardown

To keep data but remove compute resources:

```bash
./teardown-master.sh -e dev --keep-data
```

This preserves:
- S3 buckets and data
- DynamoDB tables and records
- KMS encryption keys

But removes:
- Lambda functions
- Step Functions
- API Gateway
- Cognito resources
- CloudWatch logs


## Troubleshooting

### Common Issues

#### 1. AWS Credentials Not Configured

**Error:** `Unable to locate credentials`

**Solution:**
```bash
aws configure
# OR
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
```

#### 2. Insufficient Permissions

**Error:** `AccessDenied` or `UnauthorizedOperation`

**Solution:** Ensure your IAM user/role has required permissions. Attach policies:
- `IAMFullAccess`
- `AmazonS3FullAccess`
- `AmazonDynamoDBFullAccess`
- `AWSLambda_FullAccess`
- `AmazonAPIGatewayAdministrator`
- `AmazonCognitoPowerUser`

#### 3. Resource Already Exists

**Error:** `ResourceAlreadyExistsException`

**Solution:** This is usually safe to ignore. The script will use existing resources.

#### 4. Bucket Name Conflict

**Error:** `BucketAlreadyExists`

**Solution:** S3 bucket names must be globally unique. The scripts use account ID suffix to avoid conflicts. If still occurring, modify `S3_BUCKET_PREFIX` in config.

#### 5. Region Not Supported

**Error:** `InvalidRegion` or service not available

**Solution:** Some AWS services are not available in all regions. Use a region that supports all required services:
- Recommended: `us-east-1`, `us-west-2`, `eu-west-1`, `ap-south-1`

#### 6. Lambda Deployment Package Too Large

**Error:** `RequestEntityTooLargeException`

**Solution:** Use Lambda layers for dependencies:
```bash
# Create layer
cd backend/layers
zip -r layer.zip python/
aws lambda publish-layer-version --layer-name auditflow-deps --zip-file fileb://layer.zip
```

#### 7. DynamoDB Throttling

**Error:** `ProvisionedThroughputExceededException`

**Solution:** Increase DynamoDB capacity or use `PAY_PER_REQUEST` billing mode in config.

#### 8. KMS Key Deletion Pending

**Error:** `KMSInvalidStateException`

**Solution:** KMS keys have a 7-30 day waiting period. Cancel deletion:
```bash
aws kms cancel-key-deletion --key-id <KEY_ID>
```

### Debugging Tips

#### Enable Verbose Mode

```bash
./deploy-master.sh -e dev -v
```

#### Check CloudWatch Logs

```bash
aws logs tail /aws/lambda/AuditFlow-Trigger --follow
```

#### Verify Resource Creation

```bash
# List all resources with project tag
aws resourcegroupstaggingapi get-resources \
  --tag-filters Key=Project,Values=auditflow-pro
```

#### Test IAM Permissions

```bash
# Test specific permission
aws iam simulate-principal-policy \
  --policy-source-arn arn:aws:iam::account:role/AuditFlowLambdaExecutionRole \
  --action-names s3:GetObject dynamodb:PutItem
```


### Getting Help

#### Check Deployment Logs

All deployment scripts log to stdout. Redirect to file for analysis:

```bash
./deploy-master.sh -e dev 2>&1 | tee deployment.log
```

#### Validate Step-by-Step

Run individual infrastructure scripts:

```bash
cd infrastructure
bash kms_setup.sh
bash deploy.sh
bash cognito_setup.sh
# etc.
```

#### AWS Service Health

Check AWS service status:
- https://status.aws.amazon.com/

#### Contact Support

For deployment issues:
1. Check this troubleshooting guide
2. Review CloudWatch logs
3. Check AWS service limits
4. Contact AWS Support if needed

## Best Practices

### Security

1. **Use MFA** - Enable MFA for production environments
2. **Rotate Keys** - Enable automatic KMS key rotation
3. **Least Privilege** - Use minimal IAM permissions
4. **Encrypt Everything** - Enable encryption at rest and in transit
5. **Audit Logs** - Enable CloudTrail and CloudWatch logging

### Cost Optimization

1. **Right-Size Lambda** - Use appropriate memory settings
2. **Use PAY_PER_REQUEST** - For variable workloads
3. **Lifecycle Policies** - Archive old data to Glacier
4. **Delete Unused Resources** - Tear down dev/staging when not needed
5. **Monitor Costs** - Set up billing alerts

### High Availability

1. **Multi-Region** - Deploy to multiple regions
2. **Global Tables** - Use DynamoDB Global Tables
3. **S3 Replication** - Enable cross-region replication
4. **Health Checks** - Configure Route53 health checks
5. **Backup Data** - Regular backups and exports

### Monitoring

1. **CloudWatch Alarms** - Set up alerts for errors
2. **Log Aggregation** - Centralize logs for analysis
3. **Metrics Dashboard** - Create CloudWatch dashboards
4. **Regular Validation** - Run validation scripts periodically
5. **Performance Testing** - Test under load

## Next Steps

After successful deployment:

1. **Update Frontend Configuration**
   - Copy Cognito User Pool ID and Client ID
   - Update `frontend/.env` with API Gateway endpoint
   - Deploy frontend to AWS Amplify

2. **Create Test Users**
   ```bash
   aws cognito-idp admin-create-user \
     --user-pool-id <USER_POOL_ID> \
     --username testuser@example.com \
     --user-attributes Name=email,Value=testuser@example.com
   ```

3. **Test End-to-End**
   - Upload a test document
   - Verify processing workflow
   - Check audit results in dashboard

4. **Set Up Monitoring**
   - Configure CloudWatch alarms
   - Set up SNS notifications
   - Create operational dashboards

5. **Documentation**
   - Document custom configurations
   - Create runbooks for operations
   - Train team on deployment process

## References

- [AWS CLI Documentation](https://docs.aws.amazon.com/cli/)
- [AWS Lambda Best Practices](https://docs.aws.amazon.com/lambda/latest/dg/best-practices.html)
- [DynamoDB Best Practices](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/best-practices.html)
- [S3 Security Best Practices](https://docs.aws.amazon.com/AmazonS3/latest/userguide/security-best-practices.html)
- [AuditFlow-Pro Design Document](loan-document-auditor/design.md)
- [AuditFlow-Pro Requirements](loan-document-auditor/requirements.md)

