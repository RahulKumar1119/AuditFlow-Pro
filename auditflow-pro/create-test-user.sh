#!/bin/bash
# create-test-user.sh
# Creates a test user in Cognito User Pool

set -e

REGION="ap-south-1"
USER_POOL_ID="ap-south-1_lIhrnyezu"

echo "=========================================="
echo "Creating Test User in Cognito"
echo "=========================================="
echo ""

# Prompt for user details
read -p "Enter email address: " EMAIL
read -sp "Enter temporary password (min 8 chars, uppercase, lowercase, number, special char): " PASSWORD
echo ""
read -p "Enter user's full name: " FULL_NAME

echo ""
echo "Creating user..."

# Create user
aws cognito-idp admin-create-user \
    --user-pool-id $USER_POOL_ID \
    --username "$EMAIL" \
    --user-attributes \
        Name=email,Value="$EMAIL" \
        Name=email_verified,Value=true \
        Name=name,Value="$FULL_NAME" \
    --temporary-password "$PASSWORD" \
    --message-action SUPPRESS \
    --region $REGION

echo "✓ User created: $EMAIL"

# Set permanent password
echo "Setting permanent password..."
aws cognito-idp admin-set-user-password \
    --user-pool-id $USER_POOL_ID \
    --username "$EMAIL" \
    --password "$PASSWORD" \
    --permanent \
    --region $REGION

echo "✓ Password set (permanent)"

# Add user to LoanOfficers group (default)
echo "Adding user to LoanOfficers group..."
aws cognito-idp admin-add-user-to-group \
    --user-pool-id $USER_POOL_ID \
    --username "$EMAIL" \
    --group-name LoanOfficers \
    --region $REGION 2>/dev/null || echo "⚠ LoanOfficers group may not exist yet"

echo ""
echo "=========================================="
echo "User Created Successfully!"
echo "=========================================="
echo ""
echo "Login Credentials:"
echo "  Email: $EMAIL"
echo "  Password: [the password you entered]"
echo "  Group: LoanOfficers"
echo ""
echo "You can now log in at your Amplify URL"
echo ""
echo "To create an admin user, run:"
echo "  aws cognito-idp admin-add-user-to-group \\"
echo "    --user-pool-id $USER_POOL_ID \\"
echo "    --username $EMAIL \\"
echo "    --group-name Administrators \\"
echo "    --region $REGION"
echo ""
