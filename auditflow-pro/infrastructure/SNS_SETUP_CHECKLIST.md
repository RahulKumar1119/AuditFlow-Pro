# SNS Setup Checklist

Complete this checklist to ensure SNS alerts are properly configured for Task 10.3.

## Pre-Setup

- [ ] AWS CLI installed and configured
- [ ] AWS credentials have appropriate permissions
- [ ] Email address ready for alerts
- [ ] (Optional) Phone number for SMS alerts
- [ ] Access to auditflow-pro repository

## Automated Setup (Recommended)

- [ ] Navigate to `auditflow-pro/infrastructure`
- [ ] Set environment variables:
  ```bash
  export ENVIRONMENT=dev
  export AWS_REGION=ap-south-1
  export ALERT_EMAIL=your-email@example.com
  ```
- [ ] Make script executable: `chmod +x sns_setup.sh`
- [ ] Run setup script: `./sns_setup.sh`
- [ ] Script completes successfully
- [ ] Note the SNS topic ARN from output

## Email Subscription

- [ ] Check email inbox for AWS SNS confirmation
- [ ] Click confirmation link in email
- [ ] Subscription status changes to "Confirmed"
- [ ] (If not received) Check spam folder
- [ ] (If not received) Re-run setup script

## Configuration

- [ ] Open `auditflow-pro/.env`
- [ ] Add SNS topic ARN:
  ```bash
  ALERTS_TOPIC_ARN=arn:aws:sns:ap-south-1:123456789012:AuditFlow-RiskAlerts-dev
  ```
- [ ] Save `.env` file
- [ ] Verify no syntax errors in `.env`

## Lambda Deployment

- [ ] Navigate to `auditflow-pro/backend`
- [ ] Build Lambda packages: `./build_lambda_packages.sh`
- [ ] Navigate to `infrastructure`
- [ ] Deploy Lambda functions: `./deploy_processing_lambdas.sh`
- [ ] Verify Reporter Lambda deployed successfully
- [ ] Check Lambda environment variables include `ALERTS_TOPIC_ARN`

## IAM Permissions

- [ ] Verify Lambda execution role exists
- [ ] Check role has `sns:Publish` permission
- [ ] Permission includes SNS topic ARN
- [ ] (If missing) Add permission using:
  ```bash
  aws iam put-role-policy \
      --role-name AuditFlow-Lambda-Execution-Role \
      --policy-name SNSPublishPolicy \
      --policy-document '{...}'
  ```

## SNS Topic Verification

- [ ] Topic exists: `aws sns list-topics`
- [ ] Topic ARN matches `.env` file
- [ ] Topic has correct name: `AuditFlow-RiskAlerts-{ENVIRONMENT}`
- [ ] Topic attributes configured
- [ ] Topic policy allows Lambda to publish

## Subscription Verification

- [ ] Email subscription exists
- [ ] Subscription status is "Confirmed"
- [ ] Subscription protocol is "email"
- [ ] Subscription endpoint is correct email
- [ ] (Optional) SMS subscription exists if configured
- [ ] (Optional) SMS subscription status is "Confirmed"

## Testing

### SNS Direct Test
- [ ] Run SNS publish test:
  ```bash
  aws sns publish \
      --topic-arn $ALERTS_TOPIC_ARN \
      --subject "Test Alert" \
      --message "SNS is working!" \
      --region ap-south-1
  ```
- [ ] Test message received in email
- [ ] Email contains correct subject and message

### Lambda Test
- [ ] Create test event with high risk score (> 50)
- [ ] Invoke Reporter Lambda with test event
- [ ] Lambda execution succeeds
- [ ] Lambda logs show "Triggered HIGH alert via SNS"
- [ ] Alert email received
- [ ] Email contains loan application ID and risk score

### End-to-End Test
- [ ] Upload test document via frontend or API
- [ ] Document processes through workflow
- [ ] Risk score calculated
- [ ] If risk score > 50, alert email received
- [ ] Alert email contains:
  - [ ] Correct alert type (HIGH or CRITICAL)
  - [ ] Loan application ID
  - [ ] Risk score value
  - [ ] Appropriate message

## Monitoring Setup

- [ ] CloudWatch log group exists: `/aws/lambda/AuditFlow-Reporter-dev`
- [ ] Log retention configured (365 days)
- [ ] SNS metrics visible in CloudWatch
- [ ] (Optional) CloudWatch alarms configured for failures

## Documentation

- [ ] Read `SNS_SETUP.md` for detailed information
- [ ] Read `SNS_QUICK_START.md` for quick reference
- [ ] Read `SNS_ARCHITECTURE.md` for system design
- [ ] Bookmark troubleshooting section

## Production Deployment

- [ ] Environment set to "prod"
- [ ] SNS topic created for production
- [ ] Production email subscriptions confirmed
- [ ] Lambda functions deployed to production
- [ ] Production `.env` updated with prod SNS topic ARN
- [ ] Production Lambda environment variables updated
- [ ] Production testing completed
- [ ] Production alerts verified

## Troubleshooting

If any step fails:

- [ ] Check AWS CLI is configured: `aws sts get-caller-identity`
- [ ] Check IAM permissions: `aws iam get-role-policy --role-name AuditFlow-Lambda-Execution-Role --policy-name SNSPublishPolicy`
- [ ] Check SNS topic exists: `aws sns list-topics`
- [ ] Check subscriptions: `aws sns list-subscriptions-by-topic --topic-arn $ALERTS_TOPIC_ARN`
- [ ] Check Lambda logs: `aws logs tail /aws/lambda/AuditFlow-Reporter-dev`
- [ ] Review troubleshooting section in `SNS_SETUP.md`

## Sign-Off

- [ ] All checklist items completed
- [ ] SNS alerts working correctly
- [ ] Email notifications received
- [ ] Documentation reviewed
- [ ] Team notified of SNS setup

**Completed By**: ________________  
**Date**: ________________  
**Environment**: ________________  

---

## Quick Reference

### Key Commands

```bash
# List SNS topics
aws sns list-topics --region ap-south-1

# Get topic attributes
aws sns get-topic-attributes \
    --topic-arn $ALERTS_TOPIC_ARN \
    --region ap-south-1

# List subscriptions
aws sns list-subscriptions-by-topic \
    --topic-arn $ALERTS_TOPIC_ARN \
    --region ap-south-1

# Test SNS
aws sns publish \
    --topic-arn $ALERTS_TOPIC_ARN \
    --subject "Test" \
    --message "Test message" \
    --region ap-south-1

# Check Lambda logs
aws logs tail /aws/lambda/AuditFlow-Reporter-dev --follow

# Check Lambda environment
aws lambda get-function-configuration \
    --function-name AuditFlow-Reporter-dev \
    --region ap-south-1 \
    --query 'Environment.Variables'
```

### Important Files

- Setup Script: `infrastructure/sns_setup.sh`
- Setup Guide: `infrastructure/SNS_SETUP.md`
- Quick Start: `infrastructure/SNS_QUICK_START.md`
- Architecture: `infrastructure/SNS_ARCHITECTURE.md`
- Code: `backend/functions/reporter/app.py`
- Config: `.env`

### Support Resources

- [AWS SNS Docs](https://docs.aws.amazon.com/sns/)
- [SNS Troubleshooting](https://docs.aws.amazon.com/sns/latest/dg/troubleshooting.html)
- [Lambda SNS Integration](https://docs.aws.amazon.com/lambda/latest/dg/services-sns.html)
