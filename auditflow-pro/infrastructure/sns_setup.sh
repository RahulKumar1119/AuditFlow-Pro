#!/bin/bash

# SNS Setup Script for AuditFlow-Pro Alert Notifications
# This script creates SNS topics for risk alerts and configures subscriptions

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
ENVIRONMENT=${ENVIRONMENT:-dev}
REGION=${AWS_REGION:-ap-south-1}
ALERT_EMAIL=${ALERT_EMAIL:-}
ALERT_SMS=${ALERT_SMS:-}

echo -e "${GREEN}=== AuditFlow-Pro SNS Setup ===${NC}"
echo "Environment: $ENVIRONMENT"
echo "Region: $REGION"
echo ""

# Validate AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo -e "${RED}Error: AWS CLI is not installed${NC}"
    exit 1
fi

# Validate AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
    echo -e "${RED}Error: AWS credentials not configured${NC}"
    exit 1
fi

# 1. Create SNS Topic for Risk Alerts
echo -e "${YELLOW}Step 1: Creating SNS topic for risk alerts...${NC}"
ALERTS_TOPIC_NAME="AuditFlow-RiskAlerts-${ENVIRONMENT}"
ALERTS_TOPIC_ARN=$(aws sns create-topic \
    --name "$ALERTS_TOPIC_NAME" \
    --region "$REGION" \
    --query 'TopicArn' \
    --output text 2>/dev/null || echo "")

if [ -z "$ALERTS_TOPIC_ARN" ]; then
    # Topic might already exist, try to get it
    ALERTS_TOPIC_ARN=$(aws sns list-topics \
        --region "$REGION" \
        --query "Topics[?contains(TopicArn, '$ALERTS_TOPIC_NAME')].TopicArn" \
        --output text)
fi

if [ -n "$ALERTS_TOPIC_ARN" ]; then
    echo -e "${GREEN}✓ Risk Alerts Topic: $ALERTS_TOPIC_ARN${NC}"
else
    echo -e "${RED}✗ Failed to create/find SNS topic${NC}"
    exit 1
fi

# 2. Create SNS Topic for Critical Alerts (optional, for separate handling)
echo -e "${YELLOW}Step 2: Creating SNS topic for critical alerts...${NC}"
CRITICAL_TOPIC_NAME="AuditFlow-CriticalAlerts-${ENVIRONMENT}"
CRITICAL_TOPIC_ARN=$(aws sns create-topic \
    --name "$CRITICAL_TOPIC_NAME" \
    --region "$REGION" \
    --query 'TopicArn' \
    --output text 2>/dev/null || echo "")

if [ -z "$CRITICAL_TOPIC_ARN" ]; then
    CRITICAL_TOPIC_ARN=$(aws sns list-topics \
        --region "$REGION" \
        --query "Topics[?contains(TopicArn, '$CRITICAL_TOPIC_NAME')].TopicArn" \
        --output text)
fi

if [ -n "$CRITICAL_TOPIC_ARN" ]; then
    echo -e "${GREEN}✓ Critical Alerts Topic: $CRITICAL_TOPIC_ARN${NC}"
else
    echo -e "${RED}✗ Failed to create/find critical alerts topic${NC}"
fi

# 3. Configure Topic Attributes
echo -e "${YELLOW}Step 3: Configuring SNS topic attributes...${NC}"

# Enable content-based message deduplication and FIFO if needed
aws sns set-topic-attributes \
    --topic-arn "$ALERTS_TOPIC_ARN" \
    --attribute-name DisplayName \
    --attribute-value "AuditFlow Risk Alerts" \
    --region "$REGION" 2>/dev/null || true

echo -e "${GREEN}✓ Topic attributes configured${NC}"

# 4. Subscribe Email Endpoint
if [ -n "$ALERT_EMAIL" ]; then
    echo -e "${YELLOW}Step 4: Subscribing email endpoint...${NC}"
    SUBSCRIPTION_ARN=$(aws sns subscribe \
        --topic-arn "$ALERTS_TOPIC_ARN" \
        --protocol email \
        --notification-endpoint "$ALERT_EMAIL" \
        --region "$REGION" \
        --query 'SubscriptionArn' \
        --output text 2>/dev/null || echo "")
    
    if [ -n "$SUBSCRIPTION_ARN" ] && [ "$SUBSCRIPTION_ARN" != "PendingConfirmation" ]; then
        echo -e "${GREEN}✓ Email subscription created: $ALERT_EMAIL${NC}"
        echo -e "${YELLOW}⚠ Check your email and confirm the subscription${NC}"
    else
        echo -e "${YELLOW}⚠ Email subscription pending confirmation${NC}"
    fi
else
    echo -e "${YELLOW}⊘ Skipping email subscription (ALERT_EMAIL not set)${NC}"
fi

# 5. Subscribe SMS Endpoint (optional)
if [ -n "$ALERT_SMS" ]; then
    echo -e "${YELLOW}Step 5: Subscribing SMS endpoint...${NC}"
    SUBSCRIPTION_ARN=$(aws sns subscribe \
        --topic-arn "$CRITICAL_TOPIC_ARN" \
        --protocol sms \
        --notification-endpoint "$ALERT_SMS" \
        --region "$REGION" \
        --query 'SubscriptionArn' \
        --output text 2>/dev/null || echo "")
    
    if [ -n "$SUBSCRIPTION_ARN" ]; then
        echo -e "${GREEN}✓ SMS subscription created: $ALERT_SMS${NC}"
    else
        echo -e "${YELLOW}⚠ SMS subscription failed${NC}"
    fi
else
    echo -e "${YELLOW}⊘ Skipping SMS subscription (ALERT_SMS not set)${NC}"
fi

# 6. Create SNS Topic Policy for Lambda
echo -e "${YELLOW}Step 6: Configuring SNS topic policy for Lambda...${NC}"

POLICY='{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "SNS:Publish",
      "Resource": "'$ALERTS_TOPIC_ARN'"
    }
  ]
}'

aws sns set-topic-attributes \
    --topic-arn "$ALERTS_TOPIC_ARN" \
    --attribute-name Policy \
    --attribute-value "$POLICY" \
    --region "$REGION" 2>/dev/null || true

echo -e "${GREEN}✓ SNS topic policy configured${NC}"

# 7. Save Configuration
echo -e "${YELLOW}Step 7: Saving configuration...${NC}"

CONFIG_FILE="sns_config_${ENVIRONMENT}.env"
cat > "$CONFIG_FILE" << EOF
# SNS Configuration for AuditFlow-Pro
# Generated: $(date)

ALERTS_TOPIC_ARN=$ALERTS_TOPIC_ARN
CRITICAL_ALERTS_TOPIC_ARN=$CRITICAL_TOPIC_ARN
ENVIRONMENT=$ENVIRONMENT
REGION=$REGION
EOF

echo -e "${GREEN}✓ Configuration saved to $CONFIG_FILE${NC}"

# 8. Display Summary
echo ""
echo -e "${GREEN}=== SNS Setup Complete ===${NC}"
echo ""
echo "Configuration Summary:"
echo "  Environment: $ENVIRONMENT"
echo "  Region: $REGION"
echo "  Risk Alerts Topic: $ALERTS_TOPIC_ARN"
echo "  Critical Alerts Topic: $CRITICAL_TOPIC_ARN"
echo ""
echo "Next Steps:"
echo "1. Add the following to your .env file:"
echo "   ALERTS_TOPIC_ARN=$ALERTS_TOPIC_ARN"
echo "   CRITICAL_ALERTS_TOPIC_ARN=$CRITICAL_TOPIC_ARN"
echo ""
echo "2. Update Lambda environment variables:"
echo "   aws lambda update-function-configuration \\"
echo "     --function-name AuditFlow-Reporter-${ENVIRONMENT} \\"
echo "     --environment Variables={ALERTS_TOPIC_ARN=$ALERTS_TOPIC_ARN} \\"
echo "     --region $REGION"
echo ""
if [ -n "$ALERT_EMAIL" ]; then
    echo "3. Confirm email subscription at: $ALERT_EMAIL"
fi
echo ""
echo "Configuration file: $CONFIG_FILE"
echo ""
