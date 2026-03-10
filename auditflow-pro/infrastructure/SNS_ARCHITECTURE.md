# SNS Alert Architecture for AuditFlow-Pro

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     Document Upload Flow                         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │   S3 Bucket      │
                    │  (Documents)     │
                    └──────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │  Trigger Lambda  │
                    │  (Event Handler) │
                    └──────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │ Step Functions   │
                    │  (Orchestration) │
                    └──────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
   ┌─────────┐          ┌─────────┐          ┌─────────┐
   │Classifier│          │Extractor│          │Validator│
   │ Lambda   │          │ Lambda  │          │ Lambda  │
   └─────────┘          └─────────┘          └─────────┘
        │                     │                     │
        └─────────────────────┼─────────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │ Risk Scorer      │
                    │ Lambda           │
                    └──────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │ Reporter Lambda  │
                    │ (Task 10.3)      │
                    └──────────────────┘
                              │
                ┌─────────────┴─────────────┐
                │                           │
                ▼                           ▼
        ┌──────────────────┐        ┌──────────────────┐
        │ DynamoDB         │        │ SNS Topic        │
        │ (Audit Record)   │        │ (Alert Trigger)  │
        └──────────────────┘        └──────────────────┘
                                            │
                        ┌───────────────────┼───────────────────┐
                        │                   │                   │
                        ▼                   ▼                   ▼
                    ┌────────┐          ┌────────┐          ┌────────┐
                    │ Email  │          │  SMS   │          │Lambda  │
                    │Endpoint│          │Endpoint│          │Endpoint│
                    └────────┘          └────────┘          └────────┘
                        │                   │                   │
                        ▼                   ▼                   ▼
                   ┌──────────┐         ┌──────────┐      ┌──────────┐
                   │Admin     │         │On-Call   │      │Slack/    │
                   │Email     │         │Phone     │      │PagerDuty │
                   └──────────┘         └──────────┘      └──────────┘
```

## Alert Triggering Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    Reporter Lambda Handler                       │
│                      (app.py - Task 10.3)                        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌──────────────────────┐
                    │ Extract Risk Score   │
                    │ from Event           │
                    └──────────────────────┘
                              │
                              ▼
                    ┌──────────────────────┐
                    │ Check Risk Score     │
                    │ Thresholds           │
                    └──────────────────────┘
                              │
                ┌─────────────┼─────────────┐
                │             │             │
                ▼             ▼             ▼
        ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
        │Score > 80?   │ │Score > 50?   │ │Score ≤ 50?   │
        │              │ │              │ │              │
        │ CRITICAL     │ │ HIGH         │ │ NO ALERT     │
        │ ALERT        │ │ ALERT        │ │              │
        └──────────────┘ └──────────────┘ └──────────────┘
                │             │
                └─────────────┬─────────────┘
                              │
                              ▼
                    ┌──────────────────────┐
                    │ Prepare SNS Message  │
                    │ - Alert Type         │
                    │ - Loan App ID        │
                    │ - Risk Score         │
                    │ - Timestamp          │
                    └──────────────────────┘
                              │
                              ▼
                    ┌──────────────────────┐
                    │ Publish to SNS Topic │
                    │ (sns.publish)        │
                    └──────────────────────┘
                              │
                ┌─────────────┴─────────────┐
                │                           │
                ▼                           ▼
        ┌──────────────────┐        ┌──────────────────┐
        │ Success          │        │ Error            │
        │ - Log MessageId  │        │ - Log Error      │
        │ - Record Alert   │        │ - Continue Flow  │
        │ - Save to DB     │        │ - Don't Fail     │
        └──────────────────┘        └──────────────────┘
                │                           │
                └─────────────┬─────────────┘
                              │
                              ▼
                    ┌──────────────────────┐
                    │ Save Audit Record    │
                    │ to DynamoDB          │
                    │ (with alerts_triggered)
                    └──────────────────────┘
                              │
                              ▼
                    ┌──────────────────────┐
                    │ Return Success       │
                    │ Response             │
                    └──────────────────────┘
```

## SNS Topic Configuration

```
┌─────────────────────────────────────────────────────────────────┐
│                    SNS Topic Structure                           │
└─────────────────────────────────────────────────────────────────┘

Topic: AuditFlow-RiskAlerts-{ENVIRONMENT}
├── Topic ARN: arn:aws:sns:ap-south-1:123456789012:AuditFlow-RiskAlerts-dev
├── Display Name: AuditFlow Risk Alerts
├── Encryption: KMS (optional)
│
└── Subscriptions:
    ├── Email Subscription
    │   ├── Protocol: email
    │   ├── Endpoint: admin@example.com
    │   ├── Status: Confirmed
    │   └── Filter Policy: (optional)
    │
    ├── SMS Subscription (optional)
    │   ├── Protocol: sms
    │   ├── Endpoint: +1234567890
    │   └── Status: Confirmed
    │
    ├── Lambda Subscription (optional)
    │   ├── Protocol: lambda
    │   ├── Endpoint: arn:aws:lambda:...
    │   └── Status: Active
    │
    └── SQS Subscription (optional)
        ├── Protocol: sqs
        ├── Endpoint: arn:aws:sqs:...
        └── Status: Active
```

## Message Flow Example

### Scenario: High-Risk Application Detected

```
Time: 2024-01-15 14:30:00 UTC

1. Document Processing Complete
   └─ Risk Score: 65 (HIGH)

2. Reporter Lambda Invoked
   └─ Event contains: risk_score=65, loan_application_id=app-12345

3. trigger_alerts() Function
   └─ Checks: 65 > 50? YES → HIGH ALERT

4. SNS Message Prepared
   ├─ Subject: "AuditFlow Alert: HIGH Risk Detected"
   ├─ Message: "HIGH RISK ALERT: Loan Application app-12345 
   │            flagged with Risk Score 65. Review recommended."
   └─ Attributes: RiskLevel=HIGH

5. SNS Publish
   └─ TopicArn: arn:aws:sns:ap-south-1:123456789012:AuditFlow-RiskAlerts-dev
   └─ MessageId: 12345678-1234-1234-1234-123456789012

6. SNS Distributes to Subscribers
   ├─ Email: admin@example.com
   │  └─ Email received in inbox
   ├─ SMS: +1234567890
   │  └─ SMS received on phone
   └─ Lambda: Custom processor
      └─ Lambda invoked with message

7. Audit Record Saved
   ├─ audit_record_id: audit-abc123
   ├─ risk_score: 65
   ├─ alerts_triggered: [
   │    {
   │      "type": "HIGH",
   │      "timestamp": "2024-01-15T14:30:00Z",
   │      "message_id": "12345678-1234-1234-1234-123456789012"
   │    }
   │  ]
   └─ status: COMPLETED
```

## Data Flow: Event to Alert

```
Step Functions Event
│
├─ loan_application_id: "app-12345"
├─ documents: [...]
├─ golden_record: {...}
├─ inconsistencies: [...]
└─ risk_assessment:
   ├─ risk_score: 65
   ├─ risk_level: "HIGH"
   └─ risk_factors: [...]
        │
        ▼
Reporter Lambda (app.py)
│
├─ Extract risk_score: 65
├─ Check threshold: 65 > 50? YES
├─ Create alert message
└─ Call sns.publish()
        │
        ▼
SNS Topic
│
├─ Validate permissions
├─ Distribute to subscribers
└─ Return MessageId
        │
        ▼
Subscribers Receive Alert
│
├─ Email: admin@example.com
├─ SMS: +1234567890
└─ Lambda: Custom handler
        │
        ▼
Audit Record Saved
│
└─ alerts_triggered: [
     {
       "type": "HIGH",
       "timestamp": "2024-01-15T14:30:00Z",
       "message_id": "12345678-1234-1234-1234-123456789012"
     }
   ]
```

## Error Handling Flow

```
SNS Publish Attempt
│
├─ Success
│  ├─ Log: "Triggered HIGH alert via SNS"
│  ├─ Record: MessageId in audit record
│  └─ Continue: Save audit record
│
└─ Failure
   ├─ Catch: ClientError
   ├─ Log: "Failed to publish SNS alert: {error}"
   ├─ Alert: alerts_triggered remains empty
   └─ Continue: Save audit record anyway
      (Don't fail entire workflow)
```

## Integration Points

### 1. Lambda to SNS
```
Reporter Lambda
    │
    ├─ Environment Variable: ALERTS_TOPIC_ARN
    ├─ IAM Permission: sns:Publish
    └─ boto3 Client: sns.publish()
        │
        ▼
    SNS Topic
```

### 2. SNS to Email
```
SNS Topic
    │
    ├─ Subscription: email
    ├─ Endpoint: admin@example.com
    └─ Protocol: email
        │
        ▼
    AWS SES (Simple Email Service)
        │
        ▼
    Email Provider
        │
        ▼
    Admin Inbox
```

### 3. SNS to SMS
```
SNS Topic
    │
    ├─ Subscription: sms
    ├─ Endpoint: +1234567890
    └─ Protocol: sms
        │
        ▼
    AWS SNS SMS Service
        │
        ▼
    Telecom Provider
        │
        ▼
    Mobile Phone
```

## Monitoring and Observability

```
CloudWatch Metrics
├─ NumberOfMessagesPublished
├─ NumberOfNotificationsFailed
├─ NumberOfNotificationsDelivered
└─ PublishSize

CloudWatch Logs
├─ /aws/lambda/AuditFlow-Reporter-dev
│  └─ "Triggered HIGH alert via SNS"
│  └─ "Failed to publish SNS alert"
└─ /aws/sns/...
   └─ Delivery status logs

CloudWatch Alarms
├─ Alert: PublishFailed > 0
├─ Alert: DeliveryFailed > 0
└─ Alert: HighLatency > 5s
```

## References

- [AWS SNS Architecture](https://docs.aws.amazon.com/sns/latest/dg/sns-architecture.html)
- [SNS Message Filtering](https://docs.aws.amazon.com/sns/latest/dg/sns-message-filtering.html)
- [SNS Best Practices](https://docs.aws.amazon.com/sns/latest/dg/best-practices.html)
