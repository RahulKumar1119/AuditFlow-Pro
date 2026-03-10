# SNS Visual Setup Guide

## 1. System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    AuditFlow-Pro System                      │
└─────────────────────────────────────────────────────────────┘

Document Upload
    ↓
S3 Bucket
    ↓
Step Functions
    ├─ Classifier Lambda
    ├─ Extractor Lambda
    ├─ Validator Lambda
    └─ Risk Scorer Lambda
        ↓
    Reporter Lambda ◄─── Task 10.3: Alert Triggering
        ├─ Check Risk Score
        ├─ Publish to SNS ◄─── NEW
        └─ Save to DynamoDB
            ↓
        SNS Topic ◄─── NEW
            ├─ Email
            ├─ SMS
            └─ Lambda
                ↓
            Administrator Notifications ◄─── NEW
```

## 2. Setup Flow

```
START
  │
  ├─ Set Environment Variables
  │  ├─ ENVIRONMENT=dev
  │  ├─ AWS_REGION=ap-south-1
  │  └─ ALERT_EMAIL=your@email.com
  │
  ├─ Run Setup Script
  │  └─ ./sns_setup.sh
  │
  ├─ Confirm Email
  │  └─ Click AWS SNS confirmation link
  │
  ├─ Update .env
  │  └─ Add ALERTS_TOPIC_ARN
  │
  ├─ Deploy Lambda
  │  ├─ ./build_lambda_packages.sh
  │  └─ ./deploy_processing_lambdas.sh
  │
  ├─ Test SNS
  │  └─ aws sns publish ...
  │
  └─ Verify Alerts
     └─ Check email for test message
        │
        ✓ COMPLETE
```

## 3. Alert Decision Tree

```
                    Risk Score Calculated
                            │
                            ▼
                    ┌───────────────┐
                    │ Score > 80?   │
                    └───────────────┘
                      │           │
                     YES          NO
                      │           │
                      ▼           ▼
                  CRITICAL    ┌───────────┐
                  ALERT       │Score > 50?│
                      │       └───────────┘
                      │         │       │
                      │        YES      NO
                      │         │       │
                      │         ▼       ▼
                      │       HIGH    NO ALERT
                      │       ALERT
                      │         │
                      └─────────┼─────────┘
                                │
                                ▼
                        Publish to SNS
                                │
                                ▼
                        Send Notifications
                                │
                                ▼
                        Record in Audit
```

## 4. SNS Topic Structure

```
SNS Topic: AuditFlow-RiskAlerts-dev
│
├─ Topic ARN
│  └─ arn:aws:sns:ap-south-1:123456789012:AuditFlow-RiskAlerts-dev
│
├─ Subscriptions
│  ├─ Email
│  │  ├─ Protocol: email
│  │  ├─ Endpoint: admin@example.com
│  │  └─ Status: Confirmed ✓
│  │
│  ├─ SMS (Optional)
│  │  ├─ Protocol: sms
│  │  ├─ Endpoint: +1234567890
│  │  └─ Status: Confirmed ✓
│  │
│  └─ Lambda (Optional)
│     ├─ Protocol: lambda
│     ├─ Endpoint: arn:aws:lambda:...
│     └─ Status: Active ✓
│
└─ Attributes
   ├─ DisplayName: AuditFlow Risk Alerts
   ├─ Encryption: KMS (optional)
   └─ Policy: Lambda can publish
```

## 5. Message Flow Example

```
HIGH RISK DETECTED (Score: 65)
│
├─ Reporter Lambda Receives Event
│  └─ risk_score: 65
│
├─ Check Threshold
│  └─ 65 > 50? YES → HIGH ALERT
│
├─ Create Message
│  ├─ Subject: "AuditFlow Alert: HIGH Risk Detected"
│  ├─ Message: "HIGH RISK ALERT: Loan Application app-12345..."
│  └─ Attributes: RiskLevel=HIGH
│
├─ Publish to SNS
│  └─ sns.publish(TopicArn=..., Message=...)
│
├─ SNS Distributes
│  ├─ Email → admin@example.com
│  ├─ SMS → +1234567890
│  └─ Lambda → Custom handler
│
├─ Save Audit Record
│  └─ alerts_triggered: [{type: HIGH, timestamp: ..., message_id: ...}]
│
└─ Return Success
   └─ statusCode: 200
```

## 6. Configuration Checklist

```
┌─────────────────────────────────────────┐
│ SNS Setup Configuration Checklist       │
├─────────────────────────────────────────┤
│                                         │
│ ☐ AWS CLI installed                    │
│ ☐ AWS credentials configured           │
│ ☐ Email address ready                  │
│ ☐ Environment variables set            │
│ ☐ Setup script executed                │
│ ☐ Email subscription confirmed         │
│ ☐ .env file updated                    │
│ ☐ Lambda deployed                      │
│ ☐ IAM permissions verified             │
│ ☐ SNS topic verified                   │
│ ☐ Test alert received                  │
│ ☐ End-to-end test passed               │
│                                         │
│ ✓ READY FOR PRODUCTION                 │
│                                         │
└─────────────────────────────────────────┘
```

## 7. File Organization

```
auditflow-pro/
│
├─ .env ◄─── UPDATE: Add ALERTS_TOPIC_ARN
│
├─ SNS_SETUP_SUMMARY.md ◄─── START HERE
├─ SNS_IMPLEMENTATION_COMPLETE.md
├─ SNS_FILES_CREATED.md
│
└─ infrastructure/
   │
   ├─ sns_setup.sh ◄─── RUN THIS
   ├─ SNS_QUICK_START.md ◄─── QUICK REFERENCE
   ├─ SNS_SETUP.md ◄─── DETAILED GUIDE
   ├─ SNS_SETUP_CHECKLIST.md ◄─── VERIFICATION
   ├─ DEPLOYMENT_WITH_SNS.md ◄─── FULL DEPLOYMENT
   ├─ SNS_ARCHITECTURE.md ◄─── SYSTEM DESIGN
   └─ SNS_VISUAL_GUIDE.md ◄─── THIS FILE
```

## 8. Quick Command Reference

```
┌─────────────────────────────────────────────────────────┐
│ QUICK COMMAND REFERENCE                                 │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ Setup:                                                  │
│ $ export ALERT_EMAIL=your@email.com                    │
│ $ ./sns_setup.sh                                        │
│                                                         │
│ List Topics:                                            │
│ $ aws sns list-topics --region ap-south-1              │
│                                                         │
│ Test SNS:                                               │
│ $ aws sns publish \                                     │
│   --topic-arn $ALERTS_TOPIC_ARN \                       │
│   --subject "Test" \                                    │
│   --message "Test message" \                            │
│   --region ap-south-1                                   │
│                                                         │
│ Check Lambda Logs:                                      │
│ $ aws logs tail /aws/lambda/AuditFlow-Reporter-dev \   │
│   --follow                                              │
│                                                         │
│ Verify Lambda Config:                                   │
│ $ aws lambda get-function-configuration \              │
│   --function-name AuditFlow-Reporter-dev \             │
│   --region ap-south-1 \                                 │
│   --query 'Environment.Variables'                       │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

## 9. Alert Examples

### HIGH RISK Alert
```
┌─────────────────────────────────────────────────────┐
│ EMAIL NOTIFICATION                                  │
├─────────────────────────────────────────────────────┤
│                                                     │
│ From: AWS Notifications <no-reply@sns.amazonaws>   │
│ Subject: AuditFlow Alert: HIGH Risk Detected       │
│                                                     │
│ HIGH RISK ALERT: Loan Application app-12345        │
│ flagged with Risk Score 65. Review recommended.    │
│                                                     │
│ Timestamp: 2024-01-15T14:30:00Z                    │
│ Message ID: 12345678-1234-1234-1234-123456789012  │
│                                                     │
└─────────────────────────────────────────────────────┘
```

### CRITICAL Alert
```
┌─────────────────────────────────────────────────────┐
│ EMAIL NOTIFICATION                                  │
├─────────────────────────────────────────────────────┤
│                                                     │
│ From: AWS Notifications <no-reply@sns.amazonaws>   │
│ Subject: AuditFlow Alert: CRITICAL Risk Detected   │
│                                                     │
│ CRITICAL ALERT: Loan Application app-12345         │
│ flagged with Risk Score 85. Immediate review       │
│ required.                                           │
│                                                     │
│ Timestamp: 2024-01-15T14:30:00Z                    │
│ Message ID: 12345678-1234-1234-1234-123456789012  │
│                                                     │
└─────────────────────────────────────────────────────┘
```

## 10. Troubleshooting Decision Tree

```
                    SNS Not Working?
                            │
                ┌───────────┴───────────┐
                │                       │
                ▼                       ▼
        Email Not Received?    Lambda Can't Publish?
                │                       │
        ┌───────┴───────┐       ┌───────┴───────┐
        │               │       │               │
        ▼               ▼       ▼               ▼
    Check Spam    Re-subscribe  Check IAM    Check Env Vars
    Folder        Email         Permissions  ALERTS_TOPIC_ARN
        │               │           │           │
        └───────────────┴───────────┴───────────┘
                        │
                        ▼
                    Still Not Working?
                        │
                ┌───────┴───────┐
                │               │
                ▼               ▼
            Check Logs      Verify Topic
            CloudWatch      aws sns list-topics
                │               │
                └───────────────┘
                        │
                        ▼
                    Review SNS_SETUP.md
                    Troubleshooting Section
```

## 11. Timeline

```
Time    Activity                          Duration
────────────────────────────────────────────────────
0:00    Start                             
0:05    Read Quick Start                  5 min
0:07    Set Environment Variables         2 min
0:09    Run Setup Script                  2 min
0:14    Confirm Email Subscription        5 min
0:16    Update .env File                  2 min
0:21    Build Lambda Packages             5 min
0:26    Deploy Lambda Functions           5 min
0:31    Test SNS                          5 min
0:36    Verify Alerts                     5 min
────────────────────────────────────────────────────
       TOTAL TIME: ~36 minutes
```

## 12. Success Indicators

```
✓ Setup Complete When:
  ├─ SNS topic created
  ├─ Email subscription confirmed
  ├─ Lambda deployed with ALERTS_TOPIC_ARN
  ├─ IAM permissions verified
  ├─ Test alert received in email
  ├─ Risk score > 50 triggers HIGH alert
  ├─ Risk score > 80 triggers CRITICAL alert
  └─ Audit record saved with alert events

✓ Production Ready When:
  ├─ All above items complete
  ├─ CloudWatch monitoring configured
  ├─ Team trained on alert system
  ├─ Runbook documented
  ├─ On-call rotation established
  └─ Alerts tested in production
```

## 13. Key Metrics

```
┌──────────────────────────────────────────┐
│ SNS Performance Metrics                  │
├──────────────────────────────────────────┤
│                                          │
│ Publish Latency:        < 100ms          │
│ Delivery Latency:       < 1 second       │
│ Success Rate:           > 99.9%          │
│ Email Delivery:         < 5 minutes      │
│ SMS Delivery:           < 30 seconds     │
│                                          │
│ Cost per 1000 alerts:   $0.50            │
│ Email cost:             Free (1000/mo)   │
│ SMS cost:               $0.00645 each    │
│                                          │
└──────────────────────────────────────────┘
```

## 14. Next Steps

```
1. ✓ Read this guide
   └─ You are here

2. → Read SNS_QUICK_START.md
   └─ 5-minute overview

3. → Run sns_setup.sh
   └─ Automated setup

4. → Confirm email
   └─ Click AWS link

5. → Update .env
   └─ Add SNS topic ARN

6. → Deploy Lambda
   └─ Run deployment script

7. → Test alerts
   └─ Upload document

8. → Monitor
   └─ Check CloudWatch

9. → Document
   └─ Update team docs

10. → Go Live
    └─ Production deployment
```

---

**Visual Guide Complete**  
For detailed information, see: `SNS_SETUP.md`  
For quick setup, see: `SNS_QUICK_START.md`
