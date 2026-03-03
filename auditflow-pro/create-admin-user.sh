#!/bin/bash
# create-admin-user.sh
# Quick script to create an admin user

set -e

REGION="ap-south-1"
USER_POOL_ID="ap-south-1_lIhrnyezu"
EMAIL="${1:-admin@example.com}"
PASSWORD="${2:-Admin@123456}"
NAME="${3:-Admin User}"

echo "Creating admin user: $EMAIL"

# Create user
aws cognito-idp admin-create-user \
    --user-pool-id $USER_POOL_ID \
    --username "$EMAIL" \
    --user-attributes \
        Name=email,Value="$EMAIL" \
        Name=email_verified,Value=true \
        Name=name,Value="$NAME" \
    --temporary-password "$PASSWORD" \
    --message-action SUPPRESS \
    --region $REGION 2>/dev/null || echo "User may already exist"

# Set permanent password
aws cognito-idp admin-set-user-password \
    --user-pool-id $USER_POOL_ID \
    --username "$EMAIL" \
    --password "$PASSWORD" \
    --permanent \
    --region $REGION

# Add to both groups
aws cognito-idp admin-add-user-to-group \
    --user-pool-id $USER_POOL_ID \
    --username "$EMAIL" \
    --group-name Administrators \
    --region $REGION 2>/dev/null || echo "Administrators group not found"

aws cognito-idp admin-add-user-to-group \
    --user-pool-id $USER_POOL_ID \
    --username "$EMAIL" \
    --group-name LoanOfficers \
    --region $REGION 2>/dev/null || echo "LoanOfficers group not found"

echo ""
echo "✓ Admin user created!"
echo "  Email: $EMAIL"
echo "  Password: $PASSWORD"
echo "  Groups: Administrators, LoanOfficers"
echo ""
echo "You can now log in at your Amplify URL"
