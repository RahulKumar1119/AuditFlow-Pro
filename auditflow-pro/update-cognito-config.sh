#!/bin/bash
# update-cognito-config.sh
# Updates frontend with correct Cognito IDs from AWS

set -e

REGION="ap-south-1"
FRONTEND_ENV="frontend/.env"

echo "=========================================="
echo "Updating Cognito Configuration"
echo "=========================================="
echo ""

# Get User Pool ID
echo "Getting User Pool ID..."
USER_POOL_ID=$(aws cognito-idp list-user-pools --max-results 60 --region $REGION \
  --query "UserPools[?Name=='AuditFlowUserPool'].Id" --output text)

if [ -z "$USER_POOL_ID" ]; then
    echo "❌ Error: User Pool 'AuditFlowUserPool' not found"
    echo "Run ./infrastructure/cognito_setup_simple.sh first"
    exit 1
fi

echo "✓ User Pool ID: $USER_POOL_ID"

# Get User Pool Client ID
echo "Getting User Pool Client ID..."
CLIENT_ID=$(aws cognito-idp list-user-pool-clients --user-pool-id $USER_POOL_ID \
  --region $REGION --query "UserPoolClients[0].ClientId" --output text)

if [ -z "$CLIENT_ID" ]; then
    echo "❌ Error: User Pool Client not found"
    exit 1
fi

echo "✓ User Pool Client ID: $CLIENT_ID"

# Get Identity Pool ID (optional)
echo "Getting Identity Pool ID..."
IDENTITY_POOL_ID=$(aws cognito-identity list-identity-pools --max-results 60 --region $REGION \
  --query "IdentityPools[?IdentityPoolName=='AuditFlowIdentityPool'].IdentityPoolId" --output text)

if [ -z "$IDENTITY_POOL_ID" ]; then
    echo "⚠ Warning: Identity Pool not found (optional)"
else
    echo "✓ Identity Pool ID: $IDENTITY_POOL_ID"
fi

echo ""
echo "=========================================="
echo "Updating Frontend Configuration"
echo "=========================================="

# Backup existing .env
if [ -f "$FRONTEND_ENV" ]; then
    cp "$FRONTEND_ENV" "${FRONTEND_ENV}.backup"
    echo "✓ Backed up existing .env to ${FRONTEND_ENV}.backup"
fi

# Update frontend .env
cat > "$FRONTEND_ENV" << EOF
# auditflow-pro/frontend/.env
# Updated: $(date)

# Your API Gateway Invoke URL (Make sure there is NO trailing slash at the end)
VITE_API_URL=https://cpeg54bf6i.execute-api.ap-south-1.amazonaws.com/

# Your Cognito details
VITE_COGNITO_REGION=$REGION
VITE_COGNITO_USER_POOL_ID=$USER_POOL_ID
VITE_COGNITO_CLIENT_ID=$CLIENT_ID
EOF

if [ -n "$IDENTITY_POOL_ID" ]; then
    echo "VITE_COGNITO_IDENTITY_POOL_ID=$IDENTITY_POOL_ID" >> "$FRONTEND_ENV"
fi

echo "✓ Updated $FRONTEND_ENV"
echo ""

# Also update Amplify environment variables if needed
echo "=========================================="
echo "Amplify Environment Variables"
echo "=========================================="
echo ""
echo "Update these in AWS Amplify Console:"
echo "  1. Go to: https://console.aws.amazon.com/amplify"
echo "  2. Select your app"
echo "  3. Go to: Environment variables"
echo "  4. Update/Add these variables:"
echo ""
echo "VITE_COGNITO_REGION=$REGION"
echo "VITE_COGNITO_USER_POOL_ID=$USER_POOL_ID"
echo "VITE_COGNITO_CLIENT_ID=$CLIENT_ID"
if [ -n "$IDENTITY_POOL_ID" ]; then
    echo "VITE_COGNITO_IDENTITY_POOL_ID=$IDENTITY_POOL_ID"
fi
echo ""
echo "  5. Redeploy your app"
echo ""

# Save IDs to a file for reference
cat > "cognito-ids.txt" << EOF
Cognito Configuration
=====================
Generated: $(date)

User Pool ID: $USER_POOL_ID
User Pool Client ID: $CLIENT_ID
Identity Pool ID: $IDENTITY_POOL_ID
Region: $REGION

Frontend .env updated: ✓
Amplify Console update needed: Manual step required

Next Steps:
1. Update Amplify Console environment variables (see above)
2. Redeploy frontend in Amplify Console
3. Test login at your Amplify URL
EOF

echo "✓ Saved configuration to cognito-ids.txt"
echo ""
echo "=========================================="
echo "Configuration Update Complete!"
echo "=========================================="
echo ""
echo "Local frontend .env has been updated."
echo "Don't forget to update Amplify Console environment variables!"
