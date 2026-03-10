# SNS Setup Guide for AuditFlow-Pro Alert Notifications

This guide explains how to set up AWS SNS (Simple Notification Service) for AuditFlow-Pro risk alerts.

## Overview

The AuditFlow-Pro system uses SNS to send real-time alerts when loan applications are flagged as high-risk or critical-risk. The Reporter Lambda function (task 10.3) triggers these alerts based on risk scores.

## Alert Thresholds

- **CRITICAL Alert**: Risk Score > 80
- **HIGH Alert**: Risk Score > 50

## Quick Setup

### Option 1: Automated Setup (Recommended)

```bash
cd auditflow-pro/infrastructure

# Set environment variables
export ENVIRONMENT=dev
export AWS_REGION=ap-south-1
export ALERT_EMAIL=your-email@example.com

# Run the setup script
chmod +x sns_setup.sh
./sns_setup.sh
```

### Option 2: Manual Setup

#### Step 1: Create SNS Topic

```bash
# Create the main alerts topic
aws sns create-topic \
    --name AuditFlow-RiskAlerts-dev \
    --region ap-south-1

# Output will include TopicArn, e.g.:
# arn:aws:sns:ap-south-1:123456789012:AuditFlow-RiskAlerts-dev
```

#### Step 2: Subscribe to Alerts

**Email Subscription:**
```bash
aws sns subscribe \
    --topic-arn arn:aws:sns:ap-south-1:123456789012:AuditFlow-RiskAlerts-dev \
    --protocol email \
    --notification-endpoint your-email@example.com \
    --region ap-south-1
```

**SMS Subscription (for critical alerts):**
```bash
# Create a separate topic for critical alerts
aws sns create-topic \
    --name AuditFlow-CriticalAlerts-dev \
    --region ap-south-1

# Subscribe phone number
aws sns subscribe \
    --topic-arn arn:aws:sns:ap-south-1:123456789012:AuditFlow-CriticalAlerts-dev \
    --protocol sms \
    --notification-endpoint +1234567890 \
    --region ap-south-1
```

#### Step 3: Confirm Email Subscription

After subscribing via email, you'll receive a confirmation email. Click the confirmation link to activate the subscription.

## Configuration

### Update Environment Variables

Add the SNS topic ARN to your `.env` file:

```bash
# .env
ALERTS_TOPIC_ARN=arn:aws:sns:ap-south-1:123456789012:AuditFlow-RiskAlerts-dev
CRITICAL_ALERTS_TOPIC_ARN=arn:aws:sns:ap-south-1:123456789012:AuditFlow-CriticalAlerts-dev
```

### Update Lambda Function

Deploy the Reporter Lambda with the SNS topic ARN:

```bash
# Using AWS CLI
aws lambda update-function-configuration \
    --function-name AuditFlow-Reporter-dev \
    --environment Variables={ALERTS_TOPIC_ARN=arn:aws:sns:ap-south-1:123456789012:AuditFlow-RiskAlerts-dev} \
    --region ap-south-1

# Or using the deployment script
./deploy_processing_lambdas.sh
```

### Update IAM Permissions

Ensure the Lambda execution role has SNS publish permissions:

```bash
# Create inline policy for Lambda role
aws iam put-role-policy \
    --role-name AuditFlow-Lambda-Execution-Role \
    --policy-name SNSPublishPolicy \
    --policy-document '{
      "Version": "2012-10-17",
      "Statement": [
        {
          "Effect": "Allow",
          "Action": "sns:Publish",
          "Resource": "arn:aws:sns:ap-south-1:123456789012:AuditFlow-RiskAlerts-dev"
        }
      ]
    }'
```

## Testing SNS Setup

### Test Email Subscription

```bash
# Publish a test message
aws sns publish \
    --topic-arn arn:aws:sns:ap-south-1:123456789012:AuditFlow-RiskAlerts-dev \
    --subject "Test Alert from AuditFlow" \
    --message "This is a test alert. If you receive this, SNS is working correctly." \
    --region ap-south-1
```

### Test Lambda Integration

You can test the Reporter Lambda with a sample event:

```bash
# Create test event
cat > test_event.json << 'EOF'
{
  "loan_application_id": "app-test-123",
  "documents": [
    {
      "document_id": "doc-1",
      "document_type": "W2"
    }
  ],
  "golden_record": {
    "name": {"value": "John Doe"},
    "first_name": {"value": "John"},
    "last_name": {"value": "Doe"}
  },
  "inconsistencies": [],
  "risk_assessment": {
    "risk_score": 85,
    "risk_level": "CRITICAL",
    "risk_factors": []
  }
}
EOF

# Invoke Lambda
aws lambda invoke \
    --function-name AuditFlow-Reporter-dev \
    --payload file://test_event.json \
    --region ap-south-1 \
    response.json

# Check response
cat response.json
```

## Monitoring SNS

### View Topic Metrics

```bash
# Get topic attributes
aws sns get-topic-attributes \
    --topic-arn arn:aws:sns:ap-south-1:123456789012:AuditFlow-RiskAlerts-dev \
    --region ap-south-1

# List subscriptions
aws sns list-subscriptions-by-topic \
    --topic-arn arn:aws:sns:ap-south-1:123456789012:AuditFlow-RiskAlerts-dev \
    --region ap-south-1
```

### CloudWatch Metrics

SNS publishes metrics to CloudWatch:

```bash
# View NumberOfMessagesPublished metric
aws cloudwatch get-metric-statistics \
    --namespace AWS/SNS \
    --metric-name NumberOfMessagesPublished \
    --dimensions Name=TopicName,Value=AuditFlow-RiskAlerts-dev \
    --start-time 2024-01-01T00:00:00Z \
    --end-time 2024-01-02T00:00:00Z \
    --period 3600 \
    --statistics Sum \
    --region ap-south-1
```

## Troubleshooting

### Issue: Lambda can't publish to SNS

**Solution**: Check IAM permissions
```bash
# Verify Lambda execution role has SNS:Publish permission
aws iam get-role-policy \
    --role-name AuditFlow-Lambda-Execution-Role \
    --policy-name SNSPublishPolicy
```

### Issue: Email subscription not confirmed

**Solution**: 
1. Check spam folder for confirmation email
2. Re-subscribe with correct email address
3. Manually confirm subscription in AWS Console

### Issue: No alerts being sent

**Solution**: 
1. Verify ALERTS_TOPIC_ARN environment variable is set
2. Check Lambda logs in CloudWatch
3. Verify risk score calculation (should be > 50 for HIGH, > 80 for CRITICAL)
4. Test with manual SNS publish command above

### Issue: Topic not found error

**Solution**: Verify topic ARN is correct
```bash
# List all SNS topics
aws sns list-topics --region ap-south-1
```

## Advanced Configuration

### Message Filtering

You can set up SNS message filtering to route alerts based on risk level:

```bash
# Subscribe with filter policy
aws sns subscribe \
    --topic-arn arn:aws:sns:ap-south-1:123456789012:AuditFlow-RiskAlerts-dev \
    --protocol email \
    --notification-endpoint critical-alerts@example.com \
    --attributes '{"FilterPolicy":"{\"RiskLevel\":[\"CRITICAL\"]}"}'
```

### Dead Letter Queue

For production, set up a DLQ for failed message deliveries:

```bash
# Create SQS queue for DLQ
aws sqs create-queue --queue-name AuditFlow-AlertsDLQ

# Set SNS redrive policy
aws sns set-topic-attributes \
    --topic-arn arn:aws:sns:ap-south-1:123456789012:AuditFlow-RiskAlerts-dev \
    --attribute-name RedrivePolicy \
    --attribute-value '{"deadLetterTargetArn":"arn:aws:sqs:ap-south-1:123456789012:AuditFlow-AlertsDLQ"}'
```

## Cost Considerations

- **SNS Publish**: $0.50 per million requests
- **Email**: Free for first 1,000 emails/month
- **SMS**: $0.00645 per SMS (varies by region)

For typical usage (100-1000 alerts/month), SNS costs are minimal.

## References

- [AWS SNS Documentation](https://docs.aws.amazon.com/sns/)
- [SNS Message Filtering](https://docs.aws.amazon.com/sns/latest/dg/sns-message-filtering.html)
- [SNS Best Practices](https://docs.aws.amazon.com/sns/latest/dg/best-practices.html)
