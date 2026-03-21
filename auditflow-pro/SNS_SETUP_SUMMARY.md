# SNS Setup Summary for Task 10.3 - Alert Triggering

## Overview

Task 10.3 "Implement alert triggering" uses AWS SNS to send notifications when loan applications are flagged as high-risk or critical-risk. This document summarizes the setup process.

## What Was Created

### 1. SNS Setup Script
**File:** `infrastructure/sns_setup.sh`

Automated script that:
- Creates SNS topics for risk alerts
- Configures email subscriptions
- Sets up IAM permissions for Lambda
- Generates configuration files

### 2. Documentation

| File | Purpose |
|------|---------|
| `infrastructure/SNS_SETUP.md` | Comprehensive setup guide with all options |
| `infrastructure/SNS_QUICK_START.md` | 5-minute quick start guide |
| `infrastructure/DEPLOYMENT_WITH_SNS.md` | Full deployment guide with SNS integration |

### 3. Configuration Updates

**File:** `.env`

Added SNS configuration variables:
```bash
ALERTS_TOPIC_ARN=
CRITICAL_ALERTS_TOPIC_ARN=
```

## How Alert Triggering Works

### Code Implementation
**File:** `backend/functions/reporter/app.py`

Function: `trigger_alerts()` (lines 95-130)

```python
def trigger_alerts(record_data: dict) -> list:
    """Task 10.3: Implement alert triggering via SNS."""
    risk_score = record_data.get('risk_score', 0)
    
    if risk_score > 80:
        alert_type = "CRITICAL"
        # Send SNS notification
    elif risk_score > 50:
        alert_type = "HIGH"
        # Send SNS notification
```

### Alert Flow

1. **Document Processing** → Risk score calculated
2. **Reporter Lambda** → Checks risk score
3. **SNS Publish** → Sends alert if score > 50
4. **Email/SMS** → Administrator receives notification
5. **Audit Record** → Alert event recorded

## Quick Setup Steps

### 1. Run Setup Script

```bash
cd auditflow-pro/infrastructure
export ALERT_EMAIL=your-email@example.com
chmod +x sns_setup.sh
./sns_setup.sh
```

### 2. Confirm Email

Check your email and click the AWS SNS confirmation link.

### 3. Update .env

Add the SNS topic ARN from script output:
```bash
ALERTS_TOPIC_ARN=arn:aws:sns:ap-south-1:123456789012:AuditFlow-RiskAlerts-dev
```

### 4. Deploy Lambda

```bash
cd ../backend
./build_lambda_packages.sh
cd ../infrastructure
./deploy_processing_lambdas.sh
```

### 5. Test

Upload a document and verify alerts are sent when risk score > 50.

## Alert Examples

### HIGH RISK Alert (Score 50-79)
```
Subject: AuditFlow Alert: HIGH Risk Detected
Message: HIGH RISK ALERT: Loan Application app-12345 flagged with Risk Score 65. Review recommended.
```

### CRITICAL Alert (Score > 80)
```
Subject: AuditFlow Alert: CRITICAL Risk Detected
Message: CRITICAL ALERT: Loan Application app-12345 flagged with Risk Score 85. Immediate review required.
```

## Configuration Details

### SNS Topics Created

1. **Risk Alerts Topic**
   - Name: `AuditFlow-RiskAlerts-{ENVIRONMENT}`
   - Purpose: All risk alerts (HIGH and CRITICAL)
   - Subscribers: Email, SMS, Lambda, etc.

2. **Critical Alerts Topic** (Optional)
   - Name: `AuditFlow-CriticalAlerts-{ENVIRONMENT}`
   - Purpose: Only CRITICAL alerts (score > 80)
   - Subscribers: SMS, PagerDuty, etc.

### Environment Variables

| Variable | Purpose | Example |
|----------|---------|---------|
| `ALERTS_TOPIC_ARN` | Main alerts topic | `arn:aws:sns:ap-south-1:123456789012:AuditFlow-RiskAlerts-dev` |
| `CRITICAL_ALERTS_TOPIC_ARN` | Critical alerts topic | `arn:aws:sns:ap-south-1:123456789012:AuditFlow-CriticalAlerts-dev` |
| `ALERT_EMAIL` | Email for subscriptions | `admin@example.com` |
| `ALERT_SMS` | Phone for SMS alerts | `+1234567890` |

### IAM Permissions Required

Lambda execution role needs:
```json
{
  "Effect": "Allow",
  "Action": "sns:Publish",
  "Resource": "arn:aws:sns:*:*:AuditFlow-*"
}
```

## Testing

### Test SNS Directly

```bash
aws sns publish \
    --topic-arn arn:aws:sns:ap-south-1:123456789012:AuditFlow-RiskAlerts-dev \
    --subject "Test Alert" \
    --message "This is a test alert" \
    --region ap-south-1
```

### Test Lambda Integration

```bash
# Invoke Reporter Lambda with high-risk event
aws lambda invoke \
    --function-name AuditFlow-Reporter-dev \
    --payload file://test_event.json \
    --region ap-south-1 \
    response.json
```

### Monitor Alerts

```bash
# Watch Lambda logs
aws logs tail /aws/lambda/AuditFlow-Reporter-dev --follow

# Check SNS metrics
aws cloudwatch get-metric-statistics \
    --namespace AWS/SNS \
    --metric-name NumberOfMessagesPublished \
    --dimensions Name=TopicName,Value=AuditFlow-RiskAlerts-dev \
    --start-time 2024-01-01T00:00:00Z \
    --end-time 2024-01-02T00:00:00Z \
    --period 3600 \
    --statistics Sum
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Email not received | Check spam folder, re-subscribe |
| Lambda can't publish | Verify IAM role has `sns:Publish` permission |
| No alerts sent | Check `ALERTS_TOPIC_ARN` is set in Lambda env vars |
| Topic not found | Run `aws sns list-topics` to verify |
| Subscription pending | Confirm email from AWS SNS |

## Cost Estimate

- **SNS Publish**: $0.50 per million requests
- **Email**: Free (first 1,000/month)
- **SMS**: $0.00645 per message

For 100-1000 alerts/month: **< $1/month**

## Next Steps

1. ✅ Review SNS setup documentation
2. ✅ Run `sns_setup.sh` script
3. ✅ Confirm email subscription
4. ✅ Update `.env` with SNS topic ARN
5. ✅ Deploy Lambda functions
6. ✅ Test alert triggering
7. ✅ Monitor alerts in production

## Related Files

- **Code**: `backend/functions/reporter/app.py` (lines 95-130)
- **Setup**: `infrastructure/sns_setup.sh`
- **Docs**: `infrastructure/SNS_SETUP.md`
- **Quick Start**: `infrastructure/SNS_QUICK_START.md`
- **Deployment**: `infrastructure/DEPLOYMENT_WITH_SNS.md`

## References

- [AWS SNS Documentation](https://docs.aws.amazon.com/sns/)
- [SNS Message Filtering](https://docs.aws.amazon.com/sns/latest/dg/sns-message-filtering.html)
- [SNS Best Practices](https://docs.aws.amazon.com/sns/latest/dg/best-practices.html)
- [Task 10.3 Requirements](loan-document-auditor/requirements.md) - Requirements 22.1, 22.2, 22.6
