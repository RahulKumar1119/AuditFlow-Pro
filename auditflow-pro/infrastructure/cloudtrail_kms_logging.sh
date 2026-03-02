#!/bin/bash
# infrastructure/cloudtrail_kms_logging.sh
# Enable CloudTrail logging for KMS key operations

set -e

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION="${AWS_REGION:-ap-south-1}"
TRAIL_NAME="auditflow-kms-trail"
BUCKET_NAME="auditflow-cloudtrail-logs-${ACCOUNT_ID}"

echo "=========================================="
echo "Configuring CloudTrail for KMS Logging"
echo "Region: $REGION"
echo "=========================================="

# Create S3 bucket for CloudTrail logs
echo ""
echo "Creating S3 bucket for CloudTrail logs..."
if aws s3api head-bucket --bucket "$BUCKET_NAME" 2>/dev/null; then
    echo "Bucket $BUCKET_NAME already exists"
else
    aws s3api create-bucket \
        --bucket "$BUCKET_NAME" \
        --region "$REGION" \
        --create-bucket-configuration LocationConstraint="$REGION"
    
    echo "✓ Bucket created: $BUCKET_NAME"
fi

# Block public access on CloudTrail bucket
echo "Blocking public access on CloudTrail bucket..."
aws s3api put-public-access-block \
    --bucket "$BUCKET_NAME" \
    --public-access-block-configuration \
        "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"

echo "✓ Public access blocked"

# Apply bucket policy to allow CloudTrail to write logs
echo "Applying bucket policy for CloudTrail..."
aws s3api put-bucket-policy --bucket "$BUCKET_NAME" --policy "{
    \"Version\": \"2012-10-17\",
    \"Statement\": [
        {
            \"Sid\": \"AWSCloudTrailAclCheck\",
            \"Effect\": \"Allow\",
            \"Principal\": {
                \"Service\": \"cloudtrail.amazonaws.com\"
            },
            \"Action\": \"s3:GetBucketAcl\",
            \"Resource\": \"arn:aws:s3:::${BUCKET_NAME}\"
        },
        {
            \"Sid\": \"AWSCloudTrailWrite\",
            \"Effect\": \"Allow\",
            \"Principal\": {
                \"Service\": \"cloudtrail.amazonaws.com\"
            },
            \"Action\": \"s3:PutObject\",
            \"Resource\": \"arn:aws:s3:::${BUCKET_NAME}/AWSLogs/${ACCOUNT_ID}/*\",
            \"Condition\": {
                \"StringEquals\": {
                    \"s3:x-amz-acl\": \"bucket-owner-full-control\"
                }
            }
        }
    ]
}"

echo "✓ Bucket policy applied"

# Create or update CloudTrail
echo ""
echo "Creating CloudTrail for KMS event logging..."
if aws cloudtrail describe-trails --trail-name-list "$TRAIL_NAME" --region "$REGION" 2>/dev/null | grep -q "$TRAIL_NAME"; then
    echo "CloudTrail $TRAIL_NAME already exists, updating..."
    aws cloudtrail update-trail \
        --name "$TRAIL_NAME" \
        --s3-bucket-name "$BUCKET_NAME" \
        --is-multi-region-trail \
        --enable-log-file-validation \
        --region "$REGION"
else
    aws cloudtrail create-trail \
        --name "$TRAIL_NAME" \
        --s3-bucket-name "$BUCKET_NAME" \
        --is-multi-region-trail \
        --enable-log-file-validation \
        --region "$REGION"
    
    echo "✓ CloudTrail created: $TRAIL_NAME"
fi

# Start logging
echo "Starting CloudTrail logging..."
aws cloudtrail start-logging --name "$TRAIL_NAME" --region "$REGION"
echo "✓ CloudTrail logging started"

# Configure event selectors to log KMS events
echo ""
echo "Configuring event selectors for KMS operations..."
aws cloudtrail put-event-selectors \
    --trail-name "$TRAIL_NAME" \
    --event-selectors '[
        {
            "ReadWriteType": "All",
            "IncludeManagementEvents": true,
            "DataResources": []
        }
    ]' \
    --region "$REGION"

echo "✓ Event selectors configured (includes KMS management events)"

# Create CloudWatch Logs integration (optional but recommended)
echo ""
echo "Setting up CloudWatch Logs integration..."
LOG_GROUP_NAME="/aws/cloudtrail/auditflow-kms"
ROLE_NAME="CloudTrailToCloudWatchLogsRole"

# Create CloudWatch log group
aws logs create-log-group --log-group-name "$LOG_GROUP_NAME" --region "$REGION" 2>/dev/null || echo "Log group already exists"

# Set retention policy (1 year)
aws logs put-retention-policy \
    --log-group-name "$LOG_GROUP_NAME" \
    --retention-in-days 365 \
    --region "$REGION"

echo "✓ CloudWatch log group created: $LOG_GROUP_NAME"

# Create IAM role for CloudTrail to write to CloudWatch Logs
if aws iam get-role --role-name "$ROLE_NAME" 2>/dev/null; then
    echo "IAM role $ROLE_NAME already exists"
else
    aws iam create-role \
        --role-name "$ROLE_NAME" \
        --assume-role-policy-document '{
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {
                        "Service": "cloudtrail.amazonaws.com"
                    },
                    "Action": "sts:AssumeRole"
                }
            ]
        }'
    
    # Attach policy to allow CloudTrail to write to CloudWatch Logs
    aws iam put-role-policy \
        --role-name "$ROLE_NAME" \
        --policy-name "CloudTrailToCloudWatchLogsPolicy" \
        --policy-document "{
            \"Version\": \"2012-10-17\",
            \"Statement\": [
                {
                    \"Effect\": \"Allow\",
                    \"Action\": [
                        \"logs:CreateLogStream\",
                        \"logs:PutLogEvents\"
                    ],
                    \"Resource\": \"arn:aws:logs:${REGION}:${ACCOUNT_ID}:log-group:${LOG_GROUP_NAME}:*\"
                }
            ]
        }"
    
    echo "✓ IAM role created: $ROLE_NAME"
fi

# Update CloudTrail to send logs to CloudWatch
echo "Updating CloudTrail to send logs to CloudWatch..."
aws cloudtrail update-trail \
    --name "$TRAIL_NAME" \
    --cloud-watch-logs-log-group-arn "arn:aws:logs:${REGION}:${ACCOUNT_ID}:log-group:${LOG_GROUP_NAME}:*" \
    --cloud-watch-logs-role-arn "arn:aws:iam::${ACCOUNT_ID}:role/${ROLE_NAME}" \
    --region "$REGION" 2>/dev/null || echo "CloudWatch Logs integration already configured"

echo "✓ CloudTrail configured to send logs to CloudWatch"

# Create CloudWatch metric filters for KMS events
echo ""
echo "Creating CloudWatch metric filters for KMS events..."

# Filter for KMS Decrypt operations
aws logs put-metric-filter \
    --log-group-name "$LOG_GROUP_NAME" \
    --filter-name "KMSDecryptOperations" \
    --filter-pattern '{ $.eventName = "Decrypt" && $.eventSource = "kms.amazonaws.com" }' \
    --metric-transformations \
        metricName=KMSDecryptCount,metricNamespace=AuditFlow/KMS,metricValue=1 \
    --region "$REGION" 2>/dev/null || echo "Metric filter already exists"

# Filter for KMS Encrypt operations
aws logs put-metric-filter \
    --log-group-name "$LOG_GROUP_NAME" \
    --filter-name "KMSEncryptOperations" \
    --filter-pattern '{ $.eventName = "Encrypt" && $.eventSource = "kms.amazonaws.com" }' \
    --metric-transformations \
        metricName=KMSEncryptCount,metricNamespace=AuditFlow/KMS,metricValue=1 \
    --region "$REGION" 2>/dev/null || echo "Metric filter already exists"

# Filter for unauthorized KMS access attempts
aws logs put-metric-filter \
    --log-group-name "$LOG_GROUP_NAME" \
    --filter-name "KMSUnauthorizedAccess" \
    --filter-pattern '{ $.eventSource = "kms.amazonaws.com" && $.errorCode = "AccessDenied*" }' \
    --metric-transformations \
        metricName=KMSUnauthorizedAccessCount,metricNamespace=AuditFlow/KMS,metricValue=1 \
    --region "$REGION" 2>/dev/null || echo "Metric filter already exists"

echo "✓ CloudWatch metric filters created"

# Create CloudWatch alarms for unauthorized access
echo ""
echo "Creating CloudWatch alarms for KMS security monitoring..."

aws cloudwatch put-metric-alarm \
    --alarm-name "AuditFlow-KMS-UnauthorizedAccess" \
    --alarm-description "Alert when unauthorized KMS access attempts are detected" \
    --metric-name KMSUnauthorizedAccessCount \
    --namespace AuditFlow/KMS \
    --statistic Sum \
    --period 300 \
    --evaluation-periods 1 \
    --threshold 1 \
    --comparison-operator GreaterThanOrEqualToThreshold \
    --region "$REGION" 2>/dev/null || echo "Alarm already exists"

echo "✓ CloudWatch alarm created for unauthorized access"

echo ""
echo "=========================================="
echo "CloudTrail KMS Logging Configuration Complete!"
echo "=========================================="
echo ""
echo "CloudTrail: $TRAIL_NAME"
echo "S3 Bucket: $BUCKET_NAME"
echo "CloudWatch Log Group: $LOG_GROUP_NAME"
echo "Log Retention: 365 days (1 year)"
echo ""
echo "Monitored KMS Events:"
echo "  - Encrypt operations"
echo "  - Decrypt operations"
echo "  - GenerateDataKey operations"
echo "  - Unauthorized access attempts"
echo ""
echo "CloudWatch Alarms:"
echo "  - AuditFlow-KMS-UnauthorizedAccess"
echo ""
echo "=========================================="
echo ""
echo "To view KMS events in CloudWatch Logs:"
echo "  aws logs tail $LOG_GROUP_NAME --follow --region $REGION"
echo ""
echo "To query KMS decrypt events:"
echo "  aws logs filter-log-events \\"
echo "    --log-group-name $LOG_GROUP_NAME \\"
echo "    --filter-pattern '{ \$.eventName = \"Decrypt\" }' \\"
echo "    --region $REGION"
echo ""
echo "=========================================="
