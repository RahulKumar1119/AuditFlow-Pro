# Complete Deployment with SNS Integration

This guide shows how to deploy AuditFlow-Pro with SNS alerts fully configured.

## Prerequisites

- AWS CLI configured with appropriate credentials
- Bash shell
- Email address for receiving alerts
- (Optional) Phone number for SMS alerts

## Step-by-Step Deployment

### Step 1: Set Environment Variables

```bash
export ENVIRONMENT=dev
export AWS_REGION=ap-south-1
export ALERT_EMAIL=your-email@example.com
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
```

### Step 2: Create SNS Topics

```bash
cd auditflow-pro/infrastructure

# Run SNS setup
chmod +x sns_setup.sh
./sns_setup.sh

# This will output:
# ALERTS_TOPIC_ARN=arn:aws:sns:ap-south-1:123456789012:AuditFlow-RiskAlerts-dev
# CRITICAL_ALERTS_TOPIC_ARN=arn:aws:sns:ap-south-1:123456789012:AuditFlow-CriticalAlerts-dev
```

### Step 3: Update Configuration Files

```bash
# Update .env with SNS ARNs
cat >> ../.env << EOF

# SNS Configuration (from Step 2)
ALERTS_TOPIC_ARN=arn:aws:sns:${AWS_REGION}:${AWS_ACCOUNT_ID}:AuditFlow-RiskAlerts-${ENVIRONMENT}
CRITICAL_ALERTS_TOPIC_ARN=arn:aws:sns:${AWS_REGION}:${AWS_ACCOUNT_ID}:AuditFlow-CriticalAlerts-${ENVIRONMENT}
EOF
```

### Step 4: Deploy Infrastructure

```bash
# Create DynamoDB tables
./create_dynamodb_tables.sh

# Create S3 buckets
./s3_config.sh

# Set up KMS encryption
./kms_setup.sh

# Configure security
./security_config.sh
```

### Step 5: Deploy Lambda Functions

```bash
cd ../backend

# Build Lambda packages
./build_lambda_packages.sh

# Deploy all Lambda functions
cd ../infrastructure
./deploy_processing_lambdas.sh

# Deploy API handler
./deploy_api_handler.sh

# Deploy trigger Lambda
./deploy_trigger_lambda.sh
```

### Step 6: Deploy Step Functions

```bash
# Deploy Step Functions workflow
./step_functions_deploy.sh
```

### Step 7: Configure API Gateway

```bash
# Set up API Gateway
./api_gateway_setup.sh
```

### Step 8: Verify SNS Integration

```bash
# Test SNS topic
ALERTS_TOPIC_ARN=$(grep ALERTS_TOPIC_ARN ../.env | cut -d= -f2)

aws sns publish \
    --topic-arn $ALERTS_TOPIC_ARN \
    --subject "AuditFlow Setup Test" \
    --message "SNS is configured correctly!" \
    --region $AWS_REGION

echo "Check your email for the test message"
```

### Step 9: Verify Lambda Configuration

```bash
# Check Reporter Lambda has SNS topic ARN
aws lambda get-function-configuration \
    --function-name AuditFlow-Reporter-${ENVIRONMENT} \
    --region $AWS_REGION \
    --query 'Environment.Variables.ALERTS_TOPIC_ARN'

# Should output the SNS topic ARN
```

## Automated Deployment Script

Create `deploy_with_sns.sh`:

```bash
#!/bin/bash
set -e

ENVIRONMENT=${ENVIRONMENT:-dev}
AWS_REGION=${AWS_REGION:-ap-south-1}
ALERT_EMAIL=${ALERT_EMAIL:-}

if [ -z "$ALERT_EMAIL" ]; then
    echo "Error: ALERT_EMAIL not set"
    echo "Usage: ALERT_EMAIL=your@email.com ./deploy_with_sns.sh"
    exit 1
fi

echo "Deploying AuditFlow-Pro with SNS..."
echo "Environment: $ENVIRONMENT"
echo "Region: $AWS_REGION"
echo "Alert Email: $ALERT_EMAIL"
echo ""

# Step 1: SNS Setup
echo "Step 1: Setting up SNS..."
./sns_setup.sh

# Step 2: Infrastructure
echo "Step 2: Deploying infrastructure..."
./deploy_all.sh

# Step 3: Verify
echo "Step 3: Verifying deployment..."
ALERTS_TOPIC_ARN=$(grep ALERTS_TOPIC_ARN ../.env | cut -d= -f2)

aws sns publish \
    --topic-arn $ALERTS_TOPIC_ARN \
    --subject "AuditFlow Deployment Complete" \
    --message "SNS alerts are now active. Check your email for test messages." \
    --region $AWS_REGION

echo ""
echo "✓ Deployment complete!"
echo "✓ SNS alerts configured"
echo "✓ Check your email for confirmation"
```

Usage:
```bash
chmod +x deploy_with_sns.sh
ALERT_EMAIL=your@email.com ./deploy_with_sns.sh
```

## Post-Deployment Checklist

- [ ] SNS topics created
- [ ] Email subscription confirmed
- [ ] Lambda functions deployed
- [ ] Reporter Lambda has ALERTS_TOPIC_ARN environment variable
- [ ] IAM role has SNS:Publish permission
- [ ] Test alert received in email
- [ ] Step Functions workflow deployed
- [ ] API Gateway configured
- [ ] Frontend deployed

## Testing End-to-End

### 1. Upload Test Document

```bash
# Use the frontend or API to upload a document
# The system will process it through the workflow
```

### 2. Monitor Processing

```bash
# Watch Lambda logs
aws logs tail /aws/lambda/AuditFlow-Reporter-${ENVIRONMENT} --follow

# Watch SNS metrics
aws cloudwatch get-metric-statistics \
    --namespace AWS/SNS \
    --metric-name NumberOfMessagesPublished \
    --dimensions Name=TopicName,Value=AuditFlow-RiskAlerts-${ENVIRONMENT} \
    --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
    --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
    --period 300 \
    --statistics Sum \
    --region $AWS_REGION
```

### 3. Verify Alert Received

Check your email for alerts when:
- Risk Score > 50 (HIGH alert)
- Risk Score > 80 (CRITICAL alert)

## Troubleshooting Deployment

### SNS Topic Not Created

```bash
# Check if topic exists
aws sns list-topics --region $AWS_REGION

# Manually create if needed
aws sns create-topic \
    --name AuditFlow-RiskAlerts-${ENVIRONMENT} \
    --region $AWS_REGION
```

### Lambda Can't Publish to SNS

```bash
# Check IAM role
aws iam get-role-policy \
    --role-name AuditFlow-Lambda-Execution-Role \
    --policy-name SNSPublishPolicy

# Add permission if missing
aws iam put-role-policy \
    --role-name AuditFlow-Lambda-Execution-Role \
    --policy-name SNSPublishPolicy \
    --policy-document '{
      "Version": "2012-10-17",
      "Statement": [{
        "Effect": "Allow",
        "Action": "sns:Publish",
        "Resource": "'$ALERTS_TOPIC_ARN'"
      }]
    }'
```

### Email Not Received

```bash
# Check subscription status
aws sns list-subscriptions-by-topic \
    --topic-arn $ALERTS_TOPIC_ARN \
    --region $AWS_REGION

# Re-subscribe if needed
aws sns subscribe \
    --topic-arn $ALERTS_TOPIC_ARN \
    --protocol email \
    --notification-endpoint $ALERT_EMAIL \
    --region $AWS_REGION
```

## Monitoring and Maintenance

### View Alert History

```bash
# Check CloudWatch logs for alerts
aws logs filter-log-events \
    --log-group-name /aws/lambda/AuditFlow-Reporter-${ENVIRONMENT} \
    --filter-pattern "Triggered.*alert" \
    --region $AWS_REGION
```

### Update Alert Email

```bash
# Unsubscribe old email
OLD_SUBSCRIPTION_ARN=$(aws sns list-subscriptions-by-topic \
    --topic-arn $ALERTS_TOPIC_ARN \
    --region $AWS_REGION \
    --query 'Subscriptions[0].SubscriptionArn' \
    --output text)

aws sns unsubscribe \
    --subscription-arn $OLD_SUBSCRIPTION_ARN \
    --region $AWS_REGION

# Subscribe new email
aws sns subscribe \
    --topic-arn $ALERTS_TOPIC_ARN \
    --protocol email \
    --notification-endpoint new-email@example.com \
    --region $AWS_REGION
```

## References

- [SNS Quick Start](./SNS_QUICK_START.md)
- [SNS Setup Guide](./SNS_SETUP.md)
- [Reporter Lambda](../backend/functions/reporter/app.py)
- [AWS SNS Documentation](https://docs.aws.amazon.com/sns/)
