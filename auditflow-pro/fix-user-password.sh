#!/bin/bash
# fix-user-password.sh
# Sets a permanent password for a user (bypasses NEW_PASSWORD_REQUIRED challenge)

set -e

REGION="ap-south-1"
USER_POOL_ID="ap-south-1_lIhrnyezu"
EMAIL="${1:-rahulgood66@gmail.com}"
PASSWORD="${2}"

if [ -z "$PASSWORD" ]; then
    echo "Usage: ./fix-user-password.sh EMAIL PASSWORD"
    echo ""
    echo "Example:"
    echo "  ./fix-user-password.sh rahulgood66@gmail.com MyNewPassword123!"
    echo ""
    echo "Password requirements:"
    echo "  - At least 8 characters"
    echo "  - At least 1 uppercase letter"
    echo "  - At least 1 lowercase letter"
    echo "  - At least 1 number"
    echo "  - At least 1 special character"
    exit 1
fi

echo "Setting permanent password for: $EMAIL"

# Set permanent password (bypasses NEW_PASSWORD_REQUIRED)
aws cognito-idp admin-set-user-password \
    --user-pool-id $USER_POOL_ID \
    --username "$EMAIL" \
    --password "$PASSWORD" \
    --permanent \
    --region $REGION

echo ""
echo "✓ Password updated successfully!"
echo ""
echo "You can now login with:"
echo "  Email: $EMAIL"
echo "  Password: [the password you just set]"
echo ""
echo "Try logging in again at: http://localhost:5173/login"
