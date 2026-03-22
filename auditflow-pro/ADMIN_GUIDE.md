# AuditFlow-Pro Administrator Guide

Complete guide for system administrators on managing users, monitoring, alerting, and maintaining the AuditFlow-Pro system.

## Table of Contents

1. [User Management](#user-management)
2. [Monitoring and Alerting](#monitoring-and-alerting)
3. [Backup and Recovery](#backup-and-recovery)
4. [Security Best Practices](#security-best-practices)
5. [Performance Tuning](#performance-tuning)
6. [Troubleshooting](#troubleshooting)
7. [Maintenance](#maintenance)

---

## User Management

### Creating Users

#### Create Loan Officer
```bash
aws cognito-idp admin-create-user \
  --user-pool-id us-east-1_xxxxx \
  --username officer@example.com \
  --user-attributes \
    Name=email,Value=officer@example.com \
    Name=email_verified,Value=true \
    Name=custom:role,Value=loan_officer \
  --message-action SUPPRESS
```

#### Create Administrator
```bash
aws cognito-idp admin-create-user \
  --user-pool-id us-east-1_xxxxx \
  --username admin@example.com \
  --user-attributes \
    Name=email,Value=admin@example.com \
    Name=email_verified,Value=true \
    Name=custom:role,Value=administrator \
  --message-action SUPPRESS
```

#### Set Permanent Password
```bash
aws cognito-idp admin-set-user-password \
  --user-pool-id us-east-1_xxxxx \
  --username officer@example.com \
  --password TempPassword123! \
  --permanent
```

### Managing User Groups

#### Create Group
```bash
aws cognito-idp create-group \
  --group-name loan-officers \
  --user-pool-id us-east-1_xxxxx \
  --description "Loan Officer group"
```

#### Add User to Group
```bash
aws cognito-idp admin-add-user-to-group \
  --user-pool-id us-east-1_xxxxx \
  --username officer@example.com \
  --group-name loan-officers
```

#### Remove User from Group
```bash
aws cognito-idp admin-remove-user-from-group \
  --user-pool-id us-east-1_xxxxx \
  --username officer@example.com \
  --group-name loan-officers
```

### Disabling Users

#### Disable User Account
```bash
aws cognito-idp admin-disable-user \
  --user-pool-id us-east-1_xxxxx \
  --username officer@example.com
```

#### Enable User Account
```bash
aws cognito-idp admin-enable-user \
  --user-pool-id us-east-1_xxxxx \
  --username officer@example.com
```

#### Delete User
```bash
aws cognito-idp admin-delete-user \
  --user-pool-id us-east-1_xxxxx \
  --username officer@example.com
```

### Resetting Passwords

#### Force Password Reset
```bash
aws cognito-idp admin-set-user-password \
  --user-pool-id us-east-1_xxxxx \
  --username officer@example.com \
  --password NewPassword123! \
  --permanent
```

#### Send Password Reset Email
```bash
aws cognito-idp admin-reset-user-password \
  --user-pool-id us-east-1_xxxxx \
  --username officer@example.com
```

### Viewing User Details
```bash
aws cognito-idp admin-get-user \
  --user-pool-id us-east-1_xxxxx \
  --username officer@example.com
```

### Listing Users
```bash
aws cognito-idp list-users \
  --user-pool-id us-east-1_xxxxx \
  --limit 10
```

---

## Monitoring and Alerting

### CloudWatch Dashboards

#### Create Custom Dashboard
```bash
aws cloudwatch put-dashboard \
  --dashboard-name auditflow-pro \
  --dashboard-body file://dashboard-config.json
```

#### Dashboard Metrics
- **Lambda Invocations** - Number of function calls
- **Lambda Duration** - Average execution time
- **Lambda Errors** - Failed executions
- **DynamoDB Reads** - Read operations
- **DynamoDB Writes** - Write operations
- **API Requests** - API Gateway calls
- **API Latency** - Response time

### CloudWatch Logs

#### View Lambda Logs
```bash
aws logs tail /aws/lambda/auditflow-classifier --follow
```

#### Search Logs
```bash
aws logs start-query \
  --log-group-name /aws/lambda/auditflow-classifier \
  --start-time $(date -d '1 hour ago' +%s) \
  --end-time $(date +%s) \
  --query-string 'fields @timestamp, @message | filter @message like /ERROR/'
```

#### Create Log Insights Query
```bash
# Find errors in last hour
fields @timestamp, @message, @duration
| filter @message like /ERROR/
| stats count() by @message

# Find slow requests
fields @timestamp, @duration
| filter @duration > 5000
| stats avg(@duration), max(@duration) by bin(5m)
```

### Setting Up Alarms

#### Lambda Error Alarm
```bash
aws cloudwatch put-metric-alarm \
  --alarm-name auditflow-lambda-errors \
  --alarm-description "Alert on Lambda errors" \
  --metric-name Errors \
  --namespace AWS/Lambda \
  --statistic Sum \
  --period 300 \
  --threshold 5 \
  --comparison-operator GreaterThanThreshold \
  --alarm-actions arn:aws:sns:us-east-1:123456789:auditflow-alerts
```

#### DynamoDB Throttling Alarm
```bash
aws cloudwatch put-metric-alarm \
  --alarm-name auditflow-dynamodb-throttle \
  --alarm-description "Alert on DynamoDB throttling" \
  --metric-name ConsumedWriteCapacityUnits \
  --namespace AWS/DynamoDB \
  --statistic Sum \
  --period 60 \
  --threshold 1000 \
  --comparison-operator GreaterThanThreshold \
  --alarm-actions arn:aws:sns:us-east-1:123456789:auditflow-alerts
```

#### API Gateway Latency Alarm
```bash
aws cloudwatch put-metric-alarm \
  --alarm-name auditflow-api-latency \
  --alarm-description "Alert on high API latency" \
  --metric-name Latency \
  --namespace AWS/ApiGateway \
  --statistic Average \
  --period 300 \
  --threshold 1000 \
  --comparison-operator GreaterThanThreshold \
  --alarm-actions arn:aws:sns:us-east-1:123456789:auditflow-alerts
```

### SNS Notifications

#### Create SNS Topic
```bash
aws sns create-topic --name auditflow-alerts
```

#### Subscribe to Topic
```bash
# Email subscription
aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:123456789:auditflow-alerts \
  --protocol email \
  --notification-endpoint admin@example.com

# SMS subscription
aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:123456789:auditflow-alerts \
  --protocol sms \
  --notification-endpoint +1234567890
```

#### Publish Test Message
```bash
aws sns publish \
  --topic-arn arn:aws:sns:us-east-1:123456789:auditflow-alerts \
  --subject "Test Alert" \
  --message "This is a test alert"
```

---

## Backup and Recovery

### DynamoDB Backups

#### Enable Point-in-Time Recovery
```bash
aws dynamodb update-continuous-backups \
  --table-name auditflow-documents \
  --point-in-time-recovery-specification PointInTimeRecoveryEnabled=true
```

#### Create On-Demand Backup
```bash
aws dynamodb create-backup \
  --table-name auditflow-documents \
  --backup-name auditflow-documents-backup-$(date +%Y%m%d)
```

#### List Backups
```bash
aws dynamodb list-backups --table-name auditflow-documents
```

#### Restore from Backup
```bash
aws dynamodb restore-table-from-backup \
  --target-table-name auditflow-documents-restored \
  --backup-arn arn:aws:dynamodb:us-east-1:123456789:table/auditflow-documents/backup/01234567890123-abcdef12
```

### S3 Backups

#### Enable Versioning
```bash
aws s3api put-bucket-versioning \
  --bucket auditflow-pro-documents-123456789 \
  --versioning-configuration Status=Enabled
```

#### Enable Cross-Region Replication
```bash
aws s3api put-bucket-replication \
  --bucket auditflow-pro-documents-123456789 \
  --replication-configuration file://replication-config.json
```

#### List Object Versions
```bash
aws s3api list-object-versions \
  --bucket auditflow-pro-documents-123456789
```

#### Restore Deleted Object
```bash
aws s3api get-object \
  --bucket auditflow-pro-documents-123456789 \
  --key document.pdf \
  --version-id abc123def456 \
  document-restored.pdf
```

### Backup Schedule

**Daily Backups**
- Time: 2:00 AM UTC
- Retention: 7 days
- Location: Backup S3 bucket

**Weekly Backups**
- Day: Sunday
- Time: 3:00 AM UTC
- Retention: 4 weeks
- Location: Archive S3 bucket

**Monthly Backups**
- Day: 1st of month
- Time: 4:00 AM UTC
- Retention: 12 months
- Location: Long-term storage

---

## Security Best Practices

### Access Control

#### Principle of Least Privilege
- Grant minimum required permissions
- Review IAM policies quarterly
- Remove unused roles and policies
- Use role-based access control

#### Multi-Factor Authentication
- Require MFA for all users
- Use authenticator apps (not SMS)
- Enforce MFA for administrators
- Backup recovery codes

#### Password Policy
- Minimum 12 characters
- Require uppercase, lowercase, numbers, symbols
- Expire passwords every 90 days
- Prevent password reuse (last 5)
- Account lockout after 3 failed attempts

### Encryption

#### KMS Key Management
```bash
# Enable key rotation
aws kms enable-key-rotation --key-id arn:aws:kms:us-east-1:123456789:key/12345678-1234-1234-1234-123456789012

# View key rotation status
aws kms get-key-rotation-status --key-id arn:aws:kms:us-east-1:123456789:key/12345678-1234-1234-1234-123456789012
```

#### Verify Encryption
```bash
# Check S3 encryption
aws s3api get-bucket-encryption --bucket auditflow-pro-documents-123456789

# Check DynamoDB encryption
aws dynamodb describe-table --table-name auditflow-documents | grep -A 5 SSEDescription
```

### Audit Logging

#### Enable CloudTrail
```bash
aws cloudtrail create-trail \
  --name auditflow-trail \
  --s3-bucket-name auditflow-cloudtrail-logs

aws cloudtrail start-logging --trail-name auditflow-trail
```

#### Query CloudTrail Logs
```bash
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=ResourceName,AttributeValue=auditflow-documents \
  --max-results 10
```

### Network Security

#### VPC Configuration
- Use VPC endpoints for AWS services
- Restrict security group ingress
- Enable VPC Flow Logs
- Use private subnets for Lambda

#### API Security
- Enable API Gateway logging
- Use API keys for rate limiting
- Enable WAF (Web Application Firewall)
- Require HTTPS/TLS 1.2+

---

## Performance Tuning

### Lambda Optimization

#### Memory Configuration
```bash
# Increase memory for faster execution
aws lambda update-function-configuration \
  --function-name auditflow-classifier \
  --memory-size 1024 \
  --timeout 300
```

#### Concurrency Limits
```bash
# Set reserved concurrency
aws lambda put-function-concurrency \
  --function-name auditflow-classifier \
  --reserved-concurrent-executions 100
```

### DynamoDB Optimization

#### Auto-Scaling Configuration
```bash
# Register scalable target
aws application-autoscaling register-scalable-target \
  --service-namespace dynamodb \
  --resource-id table/auditflow-documents \
  --scalable-dimension dynamodb:table:WriteCapacityUnits \
  --min-capacity 10 \
  --max-capacity 100

# Create scaling policy
aws application-autoscaling put-scaling-policy \
  --policy-name auditflow-write-scaling \
  --service-namespace dynamodb \
  --resource-id table/auditflow-documents \
  --scalable-dimension dynamodb:table:WriteCapacityUnits \
  --policy-type TargetTrackingScaling \
  --target-tracking-scaling-policy-configuration file://scaling-policy.json
```

#### Query Optimization
- Use GSI for common queries
- Limit projection attributes
- Use pagination for large result sets
- Monitor consumed capacity

### API Gateway Optimization

#### Caching
```bash
aws apigateway update-stage \
  --rest-api-id abc123 \
  --stage-name prod \
  --cache-cluster-enabled \
  --cache-cluster-size 0.5
```

#### Throttling
```bash
aws apigateway update-stage \
  --rest-api-id abc123 \
  --stage-name prod \
  --throttle-settings BurstLimit=5000,RateLimit=2000
```

---

## Troubleshooting

### Common Issues

#### High Lambda Latency
**Symptoms**: Slow document processing  
**Diagnosis**:
```bash
# Check Lambda duration
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Duration \
  --dimensions Name=FunctionName,Value=auditflow-classifier \
  --start-time 2026-03-22T00:00:00Z \
  --end-time 2026-03-22T23:59:59Z \
  --period 3600 \
  --statistics Average,Maximum
```

**Solutions**:
- Increase Lambda memory
- Optimize code
- Check for cold starts
- Review CloudWatch logs

#### DynamoDB Throttling
**Symptoms**: "ProvisionedThroughputExceededException"  
**Diagnosis**:
```bash
# Check consumed capacity
aws cloudwatch get-metric-statistics \
  --namespace AWS/DynamoDB \
  --metric-name ConsumedWriteCapacityUnits \
  --dimensions Name=TableName,Value=auditflow-documents \
  --start-time 2026-03-22T00:00:00Z \
  --end-time 2026-03-22T23:59:59Z \
  --period 60 \
  --statistics Sum
```

**Solutions**:
- Enable auto-scaling
- Increase provisioned capacity
- Optimize queries
- Use batch operations

#### API Gateway Errors
**Symptoms**: 5xx errors from API  
**Diagnosis**:
```bash
# Check API logs
aws logs tail /aws/apigateway/auditflow-api --follow
```

**Solutions**:
- Check Lambda function logs
- Verify IAM permissions
- Check resource quotas
- Review API configuration

### Debug Commands

```bash
# Check Lambda function configuration
aws lambda get-function-configuration --function-name auditflow-classifier

# Check Step Functions execution
aws stepfunctions describe-execution \
  --execution-arn arn:aws:states:us-east-1:123456789:execution:auditflow-workflow:execution-id

# Check DynamoDB table status
aws dynamodb describe-table --table-name auditflow-documents

# Check S3 bucket configuration
aws s3api get-bucket-versioning --bucket auditflow-pro-documents-123456789

# Check Cognito user pool
aws cognito-idp describe-user-pool --user-pool-id us-east-1_xxxxx
```

---

## Maintenance

### Regular Tasks

#### Daily
- Monitor CloudWatch dashboards
- Check for alerts
- Review error logs
- Verify backups completed

#### Weekly
- Review user access logs
- Check system performance metrics
- Verify all services operational
- Test backup restoration

#### Monthly
- Review security logs
- Update documentation
- Analyze usage trends
- Plan capacity needs

#### Quarterly
- Review IAM policies
- Audit user permissions
- Update security patches
- Performance optimization review

#### Annually
- Security audit
- Disaster recovery drill
- Capacity planning
- License renewal

### Patching and Updates

#### Lambda Runtime Updates
```bash
# Update function runtime
aws lambda update-function-configuration \
  --function-name auditflow-classifier \
  --runtime python3.10
```

#### Dependency Updates
```bash
# Update Python dependencies
pip install --upgrade -r requirements.txt
```

#### AWS Service Updates
- Monitor AWS service announcements
- Test updates in development
- Schedule maintenance windows
- Document changes

### Capacity Planning

#### Monitor Metrics
- Document processing volume
- Storage usage
- API request rate
- Concurrent users

#### Forecast Growth
- Analyze trends
- Plan for peak periods
- Reserve capacity
- Budget for growth

---

**Document Version**: 1.0  
**Last Updated**: 2026-03-22  
**Status**: Production Ready
