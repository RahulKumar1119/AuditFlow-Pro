#!/bin/bash
# infrastructure/cognito_setup_simple.sh
# Simplified Cognito setup with step-by-step creation

set -e

REGION="${AWS_REGION:-ap-south-1}"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

echo "Setting up AWS Cognito for AuditFlow-Pro (Simplified)..."
echo "Region: $REGION"
echo "Account ID: $ACCOUNT_ID"
echo ""

# 1. Create User Pool with minimal configuration
echo "Step 1: Creating Cognito User Pool..."
USER_POOL_ID=$(aws cognito-idp list-user-pools --max-results 60 --region $REGION \
    --query "UserPools[?Name=='AuditFlowUserPool'].Id" --output text 2>/dev/null)

if [ -z "$USER_POOL_ID" ]; then
    USER_POOL_ID=$(aws cognito-idp create-user-pool \
        --pool-name AuditFlowUserPool \
        --auto-verified-attributes email \
        --region $REGION \
        --query 'UserPool.Id' \
        --output text)
    echo "✓ User Pool created: $USER_POOL_ID"
else
    echo "✓ User Pool already exists: $USER_POOL_ID"
fi

# 2. Update User Pool with password policy
echo "Step 2: Configuring password policy..."
aws cognito-idp update-user-pool \
    --user-pool-id $USER_POOL_ID \
    --policies "PasswordPolicy={MinimumLength=12,RequireUppercase=true,RequireLowercase=true,RequireNumbers=true,RequireSymbols=true}" \
    --mfa-configuration OPTIONAL \
    --region $REGION 2>/dev/null || echo "  (Already configured)"

echo "✓ Password policy configured"

# 3. Create User Pool Client
echo "Step 3: Creating User Pool Client..."
CLIENT_ID=$(aws cognito-idp list-user-pool-clients --user-pool-id $USER_POOL_ID --region $REGION \
    --query "UserPoolClients[?ClientName=='AuditFlowWebClient'].ClientId" --output text 2>/dev/null)

if [ -z "$CLIENT_ID" ]; then
    CLIENT_ID=$(aws cognito-idp create-user-pool-client \
        --user-pool-id $USER_POOL_ID \
        --client-name AuditFlowWebClient \
        --no-generate-secret \
        --explicit-auth-flows ALLOW_USER_PASSWORD_AUTH ALLOW_REFRESH_TOKEN_AUTH ALLOW_USER_SRP_AUTH \
        --region $REGION \
        --query 'UserPoolClient.ClientId' \
        --output text)
    echo "✓ User Pool Client created: $CLIENT_ID"
else
    echo "✓ User Pool Client already exists: $CLIENT_ID"
fi

# 4. Create User Groups
echo "Step 4: Creating user groups..."
aws cognito-idp create-group \
    --user-pool-id $USER_POOL_ID \
    --group-name LoanOfficers \
    --description "Loan officers with document upload and audit viewing permissions" \
    --region $REGION 2>/dev/null || echo "  LoanOfficers group already exists"

aws cognito-idp create-group \
    --user-pool-id $USER_POOL_ID \
    --group-name Administrators \
    --description "Administrators with full system access" \
    --region $REGION 2>/dev/null || echo "  Administrators group already exists"

echo "✓ User groups created"

# 5. Create Identity Pool
echo "Step 5: Creating Identity Pool..."
IDENTITY_POOL_ID=$(aws cognito-identity list-identity-pools --max-results 60 --region $REGION \
    --query "IdentityPools[?IdentityPoolName=='AuditFlowIdentityPool'].IdentityPoolId" --output text 2>/dev/null)

if [ -z "$IDENTITY_POOL_ID" ]; then
    IDENTITY_POOL_ID=$(aws cognito-identity create-identity-pool \
        --identity-pool-name AuditFlowIdentityPool \
        --no-allow-unauthenticated-identities \
        --cognito-identity-providers ProviderName=cognito-idp.${REGION}.amazonaws.com/${USER_POOL_ID},ClientId=${CLIENT_ID} \
        --region $REGION \
        --query 'IdentityPoolId' \
        --output text)
    echo "✓ Identity Pool created: $IDENTITY_POOL_ID"
else
    echo "✓ Identity Pool already exists: $IDENTITY_POOL_ID"
fi

# 6. Create IAM roles
echo "Step 6: Creating IAM roles..."

# Create assume role policy file
cat > /tmp/cognito-assume-role.json << EOF
{
    "Version": "2012-10-17",
    "Statement": [{
        "Effect": "Allow",
        "Principal": {"Federated": "cognito-identity.amazonaws.com"},
        "Action": "sts:AssumeRoleWithWebIdentity",
        "Condition": {
            "StringEquals": {"cognito-identity.amazonaws.com:aud": "${IDENTITY_POOL_ID}"},
            "ForAnyValue:StringLike": {"cognito-identity.amazonaws.com:amr": "authenticated"}
        }
    }]
}
EOF

aws iam create-role \
    --role-name AuditFlowLoanOfficerRole \
    --assume-role-policy-document file:///tmp/cognito-assume-role.json 2>/dev/null || echo "  LoanOfficer role already exists"

aws iam create-role \
    --role-name AuditFlowAdministratorRole \
    --assume-role-policy-document file:///tmp/cognito-assume-role.json 2>/dev/null || echo "  Administrator role already exists"

rm -f /tmp/cognito-assume-role.json
echo "✓ IAM roles created"

# 7. Attach policies to roles
echo "Step 7: Attaching IAM policies..."

# Loan Officer policy
cat > /tmp/loan-officer-policy.json << EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": ["s3:GetObject", "s3:ListBucket"],
            "Resource": [
                "arn:aws:s3:::auditflow-documents-*",
                "arn:aws:s3:::auditflow-documents-*/*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"],
            "Resource": [
                "arn:aws:dynamodb:${REGION}:${ACCOUNT_ID}:table/AuditFlow-*"
            ]
        }
    ]
}
EOF

aws iam put-role-policy \
    --role-name AuditFlowLoanOfficerRole \
    --policy-name LoanOfficerAccessPolicy \
    --policy-document file:///tmp/loan-officer-policy.json

rm -f /tmp/loan-officer-policy.json

# Administrator policy
cat > /tmp/admin-policy.json << EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": ["s3:*"],
            "Resource": ["arn:aws:s3:::auditflow-documents-*", "arn:aws:s3:::auditflow-documents-*/*"]
        },
        {
            "Effect": "Allow",
            "Action": ["dynamodb:*"],
            "Resource": ["arn:aws:dynamodb:${REGION}:${ACCOUNT_ID}:table/AuditFlow-*"]
        },
        {
            "Effect": "Allow",
            "Action": ["cognito-idp:*", "cognito-identity:*", "logs:*", "cloudwatch:*"],
            "Resource": "*"
        }
    ]
}
EOF

aws iam put-role-policy \
    --role-name AuditFlowAdministratorRole \
    --policy-name AdministratorAccessPolicy \
    --policy-document file:///tmp/admin-policy.json

rm -f /tmp/admin-policy.json
echo "✓ IAM policies attached"

# 8. Set Identity Pool roles
echo "Step 8: Configuring Identity Pool roles..."
aws cognito-identity set-identity-pool-roles \
    --identity-pool-id $IDENTITY_POOL_ID \
    --roles authenticated=arn:aws:iam::${ACCOUNT_ID}:role/AuditFlowLoanOfficerRole \
    --region $REGION

echo "✓ Identity Pool roles configured"

echo ""
echo "================================================"
echo "✓ Cognito setup completed successfully!"
echo "================================================"
echo ""
echo "Configuration Details:"
echo "  User Pool ID: $USER_POOL_ID"
echo "  User Pool Client ID: $CLIENT_ID"
echo "  Identity Pool ID: $IDENTITY_POOL_ID"
echo "  Region: $REGION"
echo ""
echo "Add these to your Amplify environment variables:"
echo "  VITE_COGNITO_USER_POOL_ID=$USER_POOL_ID"
echo "  VITE_COGNITO_CLIENT_ID=$CLIENT_ID"
echo "  VITE_AWS_REGION=$REGION"
echo ""
echo "Create a test user:"
echo "  aws cognito-idp admin-create-user \\"
echo "    --user-pool-id $USER_POOL_ID \\"
echo "    --username admin@example.com \\"
echo "    --user-attributes Name=email,Value=admin@example.com \\"
echo "    --temporary-password 'TempPass123!' \\"
echo "    --region $REGION"
echo ""
echo "Add user to group:"
echo "  aws cognito-idp admin-add-user-to-group \\"
echo "    --user-pool-id $USER_POOL_ID \\"
echo "    --username admin@example.com \\"
echo "    --group-name Administrators \\"
echo "    --region $REGION"
echo ""
echo "================================================"
