#!/bin/bash
# debug-cognito-login.sh
# Comprehensive debugging for Cognito login issues

set -e

REGION="ap-south-1"
USER_POOL_ID="ap-south-1_lIhrnyezu"
CLIENT_ID="7n2nt2p6l7dhifjihhk7eaqjjd"
EMAIL="rahulgood66@gmail.com"

echo "=========================================="
echo "Cognito Login Debugging"
echo "=========================================="
echo ""

# 1. Check User Pool exists
echo "1. Checking User Pool..."
aws cognito-idp describe-user-pool \
  --user-pool-id $USER_POOL_ID \
  --region $REGION \
  --query 'UserPool.{Name:Name,Status:Status,Id:Id}' \
  --output table
echo "✓ User Pool exists"
echo ""

# 2. Check User Pool Client exists
echo "2. Checking User Pool Client..."
aws cognito-idp describe-user-pool-client \
  --user-pool-id $USER_POOL_ID \
  --client-id $CLIENT_ID \
  --region $REGION \
  --query 'UserPoolClient.{ClientId:ClientId,ClientName:ClientName,ExplicitAuthFlows:ExplicitAuthFlows}' \
  --output table
echo "✓ User Pool Client exists"
echo ""

# 3. Check user exists and status
echo "3. Checking user status..."
aws cognito-idp admin-get-user \
  --user-pool-id $USER_POOL_ID \
  --username $EMAIL \
  --region $REGION \
  --query '{Username:Username,UserStatus:UserStatus,Enabled:Enabled,UserAttributes:UserAttributes}' \
  --output json
echo ""

# 4. Check user groups
echo "4. Checking user groups..."
aws cognito-idp admin-list-groups-for-user \
  --user-pool-id $USER_POOL_ID \
  --username $EMAIL \
  --region $REGION \
  --query 'Groups[].GroupName' \
  --output table
echo ""

# 5. Test authentication with AWS CLI
echo "5. Testing authentication..."
echo "Enter password for $EMAIL:"
read -s PASSWORD

echo "Attempting to authenticate..."
AUTH_RESULT=$(aws cognito-idp admin-initiate-auth \
  --user-pool-id $USER_POOL_ID \
  --client-id $CLIENT_ID \
  --auth-flow ADMIN_NO_SRP_AUTH \
  --auth-parameters USERNAME=$EMAIL,PASSWORD=$PASSWORD \
  --region $REGION \
  --output json 2>&1) || true

if echo "$AUTH_RESULT" | grep -q "AccessToken"; then
    echo "✓ Authentication successful!"
    echo ""
    echo "Auth tokens received:"
    echo "$AUTH_RESULT" | jq '.AuthenticationResult | {AccessToken: .AccessToken[:50], IdToken: .IdToken[:50], RefreshToken: .RefreshToken[:50]}'
else
    echo "❌ Authentication failed!"
    echo ""
    echo "Error details:"
    echo "$AUTH_RESULT"
fi

echo ""
echo "=========================================="
echo "Frontend Configuration Check"
echo "=========================================="
echo ""

# 6. Check frontend .env file
echo "6. Checking frontend .env file..."
if [ -f "frontend/.env" ]; then
    echo "✓ .env file exists"
    echo ""
    echo "Contents:"
    cat frontend/.env | grep -v "^#" | grep -v "^$"
else
    echo "❌ .env file not found!"
fi

echo ""
echo "=========================================="
echo "Summary"
echo "=========================================="
echo ""
echo "User Pool ID: $USER_POOL_ID"
echo "Client ID: $CLIENT_ID"
echo "Region: $REGION"
echo "User: $EMAIL"
echo ""
echo "If authentication test succeeded but frontend login fails:"
echo "1. Clear browser cache and cookies"
echo "2. Restart the dev server (npm run dev)"
echo "3. Check browser console for detailed error messages"
echo "4. Verify the frontend is using the correct .env values"
echo ""
