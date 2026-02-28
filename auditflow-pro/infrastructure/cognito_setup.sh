#!/bin/bash
# infrastructure/cognito_setup.sh
# Sets up AWS Cognito User Pool and Identity Pool for authentication

set -e

REGION="${AWS_REGION:-us-east-1}"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

echo "Setting up AWS Cognito for AuditFlow-Pro..."

# 1. Create Cognito User Pool
echo "Creating Cognito User Pool..."
USER_POOL_ID=$(aws cognito-idp create-user-pool \
    --pool-name AuditFlowUserPool \
    --policies '{
        "PasswordPolicy": {
            "MinimumLength": 12,
            "RequireUppercase": true,
            "RequireLowercase": true,
            "RequireNumbers": true,
            "RequireSymbols": true
        }
    }' \
    --auto-verified-attributes email \
    --mfa-configuration OPTIONAL \
    --user-attribute-update-settings '{"AttributesRequireVerificationBeforeUpdate": ["email"]}' \
    --account-recovery-setting '{
        "RecoveryMechanisms": [
            {"Priority": 1, "Name": "verified_email"}
        ]
    }' \
    --region $REGION \
    --query 'UserPool.Id' \
    --output text 2>/dev/null || echo "User Pool may already exist")

echo "User Pool ID: $USER_POOL_ID"

# 2. Create User Pool Client
echo "Creating User Pool Client..."
CLIENT_ID=$(aws cognito-idp create-user-pool-client \
    --user-pool-id $USER_POOL_ID \
    --client-name AuditFlowWebClient \
    --no-generate-secret \
    --explicit-auth-flows ALLOW_USER_PASSWORD_AUTH ALLOW_REFRESH_TOKEN_AUTH \
    --token-validity-units '{
        "AccessToken": "minutes",
        "IdToken": "minutes",
        "RefreshToken": "days"
    }' \
    --access-token-validity 30 \
    --id-token-validity 30 \
    --refresh-token-validity 30 \
    --region $REGION \
    --query 'UserPoolClient.ClientId' \
    --output text 2>/dev/null || echo "Client may already exist")

echo "User Pool Client ID: $CLIENT_ID"

# 3. Create User Groups
echo "Creating Loan Officer user group..."
aws cognito-idp create-group \
    --user-pool-id $USER_POOL_ID \
    --group-name LoanOfficers \
    --description "Loan officers with document upload and audit viewing permissions" \
    --region $REGION 2>/dev/null || echo "Group may already exist"

echo "Creating Administrator user group..."
aws cognito-idp create-group \
    --user-pool-id $USER_POOL_ID \
    --group-name Administrators \
    --description "Administrators with full system access" \
    --region $REGION 2>/dev/null || echo "Group may already exist"

# 4. Create Identity Pool
echo "Creating Cognito Identity Pool..."
IDENTITY_POOL_ID=$(aws cognito-identity create-identity-pool \
    --identity-pool-name AuditFlowIdentityPool \
    --allow-unauthenticated-identities false \
    --cognito-identity-providers "ProviderName=cognito-idp.${REGION}.amazonaws.com/${USER_POOL_ID},ClientId=${CLIENT_ID}" \
    --region $REGION \
    --query 'IdentityPoolId' \
    --output text 2>/dev/null || echo "Identity Pool may already exist")

echo "Identity Pool ID: $IDENTITY_POOL_ID"

# 5. Create IAM roles for authenticated users
echo "Creating IAM role for authenticated Cognito users..."
aws iam create-role \
    --role-name AuditFlowCognitoAuthRole \
    --assume-role-policy-document "{
        \"Version\": \"2012-10-17\",
        \"Statement\": [{
            \"Effect\": \"Allow\",
            \"Principal\": {
                \"Federated\": \"cognito-identity.amazonaws.com\"
            },
            \"Action\": \"sts:AssumeRoleWithWebIdentity\",
            \"Condition\": {
                \"StringEquals\": {
                    \"cognito-identity.amazonaws.com:aud\": \"${IDENTITY_POOL_ID}\"
                },
                \"ForAnyValue:StringLike\": {
                    \"cognito-identity.amazonaws.com:amr\": \"authenticated\"
                }
            }
        }]
    }" 2>/dev/null || echo "Role may already exist"

# 6. Attach policies to authenticated role
echo "Attaching policies to authenticated role..."
aws iam put-role-policy \
    --role-name AuditFlowCognitoAuthRole \
    --policy-name CognitoAuthPolicy \
    --policy-document '{
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "cognito-identity:GetCredentialsForIdentity"
                ],
                "Resource": "*"
            }
        ]
    }'

# 7. Set Identity Pool roles
echo "Setting Identity Pool roles..."
aws cognito-identity set-identity-pool-roles \
    --identity-pool-id $IDENTITY_POOL_ID \
    --roles authenticated=arn:aws:iam::${ACCOUNT_ID}:role/AuditFlowCognitoAuthRole \
    --region $REGION

echo ""
echo "Cognito setup completed successfully!"
echo "================================================"
echo "User Pool ID: $USER_POOL_ID"
echo "User Pool Client ID: $CLIENT_ID"
echo "Identity Pool ID: $IDENTITY_POOL_ID"
echo "Region: $REGION"
echo "================================================"
echo ""
echo "Add these values to your frontend .env file:"
echo "VITE_USER_POOL_ID=$USER_POOL_ID"
echo "VITE_USER_POOL_CLIENT_ID=$CLIENT_ID"
echo "VITE_IDENTITY_POOL_ID=$IDENTITY_POOL_ID"
echo "VITE_AWS_REGION=$REGION"
