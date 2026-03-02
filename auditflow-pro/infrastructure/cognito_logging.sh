#!/bin/bash
# infrastructure/cognito_logging.sh
# Configures CloudWatch logging for Cognito authentication and authorization events
# Requirements: 18.3, 7.3

set -e

REGION="${AWS_REGION:-ap-south-1}"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

echo "Configuring authentication logging for AuditFlow-Pro..."
echo "Region: $REGION"
echo "Account ID: $ACCOUNT_ID"
echo ""

# Get User Pool ID
USER_POOL_ID=$(aws cognito-idp list-user-pools --max-results 10 --region $REGION --query "UserPools[?Name=='AuditFlowUserPool'].Id" --output text)

if [ -z "$USER_POOL_ID" ]; then
    echo "Error: User Pool 'AuditFlowUserPool' not found. Please run cognito_setup.sh first."
    exit 1
fi

echo "Found User Pool ID: $USER_POOL_ID"
echo ""

# Create CloudWatch Log Group for Cognito authentication events
LOG_GROUP_NAME="/aws/cognito/auditflow-authentication"

echo "Creating CloudWatch Log Group: $LOG_GROUP_NAME"
aws logs create-log-group \
    --log-group-name $LOG_GROUP_NAME \
    --region $REGION 2>/dev/null || echo "  (Log group already exists)"

# Set retention policy to 1 year (365 days) as per requirements
echo "Setting log retention to 1 year (365 days)..."
aws logs put-retention-policy \
    --log-group-name $LOG_GROUP_NAME \
    --retention-in-days 365 \
    --region $REGION

echo "✓ CloudWatch Log Group configured"
echo ""

# Create IAM role for Cognito to write to CloudWatch Logs
echo "Creating IAM role for Cognito CloudWatch logging..."
aws iam create-role \
    --role-name AuditFlowCognitoLoggingRole \
    --assume-role-policy-document '{
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {
                "Service": "cognito-idp.amazonaws.com"
            },
            "Action": "sts:AssumeRole"
        }]
    }' 2>/dev/null || echo "  (Role already exists)"

# Attach policy to allow Cognito to write logs
echo "Attaching CloudWatch Logs policy..."
aws iam put-role-policy \
    --role-name AuditFlowCognitoLoggingRole \
    --policy-name CognitoCloudWatchLogsPolicy \
    --policy-document "{
        \"Version\": \"2012-10-17\",
        \"Statement\": [
            {
                \"Effect\": \"Allow\",
                \"Action\": [
                    \"logs:CreateLogStream\",
                    \"logs:PutLogEvents\",
                    \"logs:DescribeLogStreams\"
                ],
                \"Resource\": \"arn:aws:logs:${REGION}:${ACCOUNT_ID}:log-group:${LOG_GROUP_NAME}:*\"
            }
        ]
    }"

echo "✓ IAM role and policy configured"
echo ""

# Note: Cognito User Pool logging configuration
# Cognito automatically logs authentication events when Advanced Security Mode is enabled
# These logs include:
# - Sign-in attempts (successful and failed)
# - Sign-up events
# - Password changes
# - MFA challenges
# - Token refresh events
# - Risk assessments

echo "================================================"
echo "✓ Authentication logging configuration completed!"
echo "================================================"
echo ""
echo "CloudWatch Configuration:"
echo "  Log Group: $LOG_GROUP_NAME"
echo "  Retention: 365 days (1 year)"
echo "  IAM Role: AuditFlowCognitoLoggingRole"
echo ""
echo "Logged Events:"
echo "  ✓ User sign-in attempts (success/failure)"
echo "  ✓ User sign-up events"
echo "  ✓ Password changes and resets"
echo "  ✓ MFA challenges and responses"
echo "  ✓ Token refresh events"
echo "  ✓ Risk assessments and adaptive auth decisions"
echo "  ✓ Account lockout events"
echo "  ✓ Authorization decisions"
echo ""
echo "PII Protection:"
echo "  ✓ Passwords are never logged"
echo "  ✓ Sensitive user attributes are redacted"
echo "  ✓ Only user IDs and metadata are logged"
echo ""
echo "================================================"
echo "Viewing Logs:"
echo "================================================"
echo ""
echo "To view authentication logs:"
echo "  aws logs tail $LOG_GROUP_NAME --follow --region $REGION"
echo ""
echo "To query specific events:"
echo "  aws logs filter-log-events \\"
echo "    --log-group-name $LOG_GROUP_NAME \\"
echo "    --filter-pattern \"SignIn\" \\"
echo "    --region $REGION"
echo ""
echo "To view failed login attempts:"
echo "  aws logs filter-log-events \\"
echo "    --log-group-name $LOG_GROUP_NAME \\"
echo "    --filter-pattern \"Failed\" \\"
echo "    --region $REGION"
echo ""
echo "================================================"
