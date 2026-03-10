# SNS Quick Start Guide

## 5-Minute Setup

### 1. Run the Setup Script

```bash
cd auditflow-pro/infrastructure
export ALERT_EMAIL=your-email@example.com
chmod +x sns_setup.sh
./sns_setup.sh
```

### 2. Confirm Email Subscription

Check your email for AWS SNS confirmation and click the link.

### 3. Update .env File

Copy the `ALERTS_TOPIC_ARN` from the script output and add to `.env`:

```bash
ALERTS_TOPIC_ARN=arn:aws:sns:ap-south-1:123456789012:AuditFlow-RiskAlerts-dev
```

### 4. Deploy Lambda

```bash
cd auditflow-pro/backend
./build_lambda_packages.sh
cd ../infrastructure
./deploy_processing_lambdas.sh
```

### 5. Test

Upload a document and check your email for alerts when risk score > 50.

---

## Manual Setup (If Script Fails)

```bash
# 1. Create topic
TOPIC_ARN=$(aws sns create-topic \
    --name AuditFlow-RiskAlerts-dev \
    --region ap-south-1 \
    --query 'TopicArn' \
    --output text)

# 2. Subscribe email
aws sns subscribe \
    --topic-arn $TOPIC_ARN \
    --protocol email \
    --notification-endpoint your-email@example.com \
    --region ap-south-1

# 3. Add to .env
echo "ALERTS_TOPIC_ARN=$TOPIC_ARN" >> .env

# 4. Update Lambda
aws lambda update-function-configuration \
    --function-name AuditFlow-Reporter-dev \
    --environment Variables={ALERTS_TOPIC_ARN=$TOPIC_ARN} \
    --region ap-south-1
```

---

## Verify Setup

```bash
# Test SNS
aws sns publish \
    --topic-arn $TOPIC_ARN \
    --subject "Test" \
    --message "SNS is working!" \
    --region ap-south-1

# Check Lambda logs
aws logs tail /aws/lambda/AuditFlow-Reporter-dev --follow
```

---

## Alert Examples

**HIGH RISK Alert (Score 50-79):**
```
Subject: AuditFlow Alert: HIGH Risk Detected
Message: HIGH RISK ALERT: Loan Application app-12345 flagged with Risk Score 65. Review recommended.
```

**CRITICAL Alert (Score > 80):**
```
Subject: AuditFlow Alert: CRITICAL Risk Detected
Message: CRITICAL ALERT: Loan Application app-12345 flagged with Risk Score 85. Immediate review required.
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Email not received | Check spam folder, re-subscribe |
| Lambda can't publish | Check IAM role has `sns:Publish` permission |
| No alerts sent | Verify `ALERTS_TOPIC_ARN` is set in Lambda env vars |
| Topic not found | Run `aws sns list-topics --region ap-south-1` |

---

## Next Steps

- [Full SNS Setup Guide](./SNS_SETUP.md)
- [Reporter Lambda Code](../backend/functions/reporter/app.py)
- [AWS SNS Docs](https://docs.aws.amazon.com/sns/)
