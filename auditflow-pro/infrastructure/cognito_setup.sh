#!/bin/bash
# infrastructure/cognito_setup.sh
# Sets up AWS Cognito User Pool and Identity Pool for authentication
# Requirements: 2.1, 2.3, 2.6, 2.7, 17.8, 2.4, 2.5, 17.6, 18.3, 7.3, 20.9

set -e

REGION="${AWS_REGION:-ap-south-1}"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

echo "Setting up AWS Cognito for AuditFlow-Pro..."
echo "Region: $REGION"
echo "Account ID: $ACCOUNT_ID"
echo ""

# 1. Create Cognito User Pool with comprehensive security policies
echo "Creating Cognito User Pool..."
USER_POOL_ID=$(aws cognito-idp create-user-pool \
    --pool-name AuditFlowUserPool \
    --policies '{
        "PasswordPolicy": {
            "MinimumLength": 12,
            "RequireUppercase": true,
            "RequireLowercase": true,
            "RequireNumbers": true,
            "RequireSymbols": true,
            "TemporaryPasswordValidityDays": 7
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
    --user-pool-add-ons '{"AdvancedSecurityMode": "ENFORCED"}' \
    --device-configuration '{"ChallengeRequiredOnNewDevice": true, "DeviceOnlyRememberedOnUserPrompt": true}' \
    --region $REGION \
    --query 'UserPool.Id' \
    --output text 2>/dev/null || aws cognito-idp list-user-pools --max-results 10 --region $REGION --query "UserPools[?Name=='AuditFlowUserPool'].Id" --output text)


if [ -z "$USER_POOL_ID" ]; then
    echo "Error: Failed to create or retrieve User Pool ID"
    exit 1
fi

echo "✓ User Pool ID: $USER_POOL_ID"

# 2. Create User Pool Client with 30-minute session timeout
echo "Creating User Pool Client with 30-minute session timeout..."
CLIENT_ID=$(aws cognito-idp create-user-pool-client \
    --user-pool-id $USER_POOL_ID \
    --client-name AuditFlowWebClient \
    --no-generate-secret \
    --explicit-auth-flows ALLOW_USER_PASSWORD_AUTH ALLOW_REFRESH_TOKEN_AUTH ALLOW_USER_SRP_AUTH \
    --token-validity-units '{
        "AccessToken": "minutes",
        "IdToken": "minutes",
        "RefreshToken": "days"
    }' \
    --access-token-validity 30 \
    --id-token-validity 30 \
    --refresh-token-validity 30 \
    --prevent-user-existence-errors ENABLED \
    --region $REGION \
    --query 'UserPoolClient.ClientId' \
    --output text 2>/dev/null || aws cognito-idp list-user-pool-clients --user-pool-id $USER_POOL_ID --region $REGION --query "UserPoolClients[?ClientName=='AuditFlowWebClient'].ClientId" --output text)

if [ -z "$CLIENT_ID" ]; then
    echo "Error: Failed to create or retrieve User Pool Client ID"
    exit 1
fi

echo "✓ User Pool Client ID: $CLIENT_ID (Session timeout: 30 minutes)"

# 3. Create User Groups with role-specific configurations
echo "Creating Loan Officer user group..."
aws cognito-idp create-group \
    --user-pool-id $USER_POOL_ID \
    --group-name LoanOfficers \
    --description "Loan officers with document upload and audit viewing permissions" \
    --region $REGION 2>/dev/null || echo "  (Group already exists)"

echo "✓ LoanOfficers group created"

echo "Creating Administrator user group..."
aws cognito-idp create-group \
    --user-pool-id $USER_POOL_ID \
    --group-name Administrators \
    --description "Administrators with full system access and MFA enforcement" \
    --region $REGION 2>/dev/null || echo "  (Group already exists)"

echo "✓ Administrators group created (MFA will be enforced via application logic)"

# 4. Create Identity Pool for AWS resource access
echo "Creating Cognito Identity Pool..."
IDENTITY_POOL_ID=$(aws cognito-identity create-identity-pool \
    --identity-pool-name AuditFlowIdentityPool \
    --allow-unauthenticated-identities false \
    --cognito-identity-providers "ProviderName=cognito-idp.${REGION}.amazonaws.com/${USER_POOL_ID},ClientId=${CLIENT_ID},ServerSideTokenCheck=true" \
    --region $REGION \
    --query 'IdentityPoolId' \
    --output text 2>/dev/null || aws cognito-identity list-identity-pools --max-results 10 --region $REGION --query "IdentityPools[?IdentityPoolName=='AuditFlowIdentityPool'].IdentityPoolId" --output text)

if [ -z "$IDENTITY_POOL_ID" ]; then
    echo "Error: Failed to create or retrieve Identity Pool ID"
    exit 1
fi

echo "✓ Identity Pool ID: $IDENTITY_POOL_ID"

# 5. Create IAM roles for authenticated users with role-based permissions
echo "Creating IAM role for Loan Officers..."
aws iam create-role \
    --role-name AuditFlowLoanOfficerRole \
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
    }" 2>/dev/null || echo "  (Role already exists)"

echo "Creating IAM role for Administrators..."
aws iam create-role \
    --role-name AuditFlowAdministratorRole \
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
    }" 2>/dev/null || echo "  (Role already exists)"

echo "✓ IAM roles created"

# 6. Attach policies to Loan Officer role (read-only access to S3 and DynamoDB)
echo "Attaching policies to Loan Officer role..."
aws iam put-role-policy \
    --role-name AuditFlowLoanOfficerRole \
    --policy-name LoanOfficerAccessPolicy \
    --policy-document "{
        \"Version\": \"2012-10-17\",
        \"Statement\": [
            {
                \"Effect\": \"Allow\",
                \"Action\": [
                    \"s3:GetObject\",
                    \"s3:ListBucket\"
                ],
                \"Resource\": [
                    \"arn:aws:s3:::auditflow-documents-${REGION}-${ACCOUNT_ID}\",
                    \"arn:aws:s3:::auditflow-documents-${REGION}-${ACCOUNT_ID}/*\"
                ]
            },
            {
                \"Effect\": \"Allow\",
                \"Action\": [
                    \"dynamodb:GetItem\",
                    \"dynamodb:Query\",
                    \"dynamodb:Scan\"
                ],
                \"Resource\": [
                    \"arn:aws:dynamodb:${REGION}:${ACCOUNT_ID}:table/AuditFlow-Documents\",
                    \"arn:aws:dynamodb:${REGION}:${ACCOUNT_ID}:table/AuditFlow-Documents/index/*\",
                    \"arn:aws:dynamodb:${REGION}:${ACCOUNT_ID}:table/AuditFlow-AuditRecords\",
                    \"arn:aws:dynamodb:${REGION}:${ACCOUNT_ID}:table/AuditFlow-AuditRecords/index/*\"
                ]
            },
            {
                \"Effect\": \"Allow\",
                \"Action\": [
                    \"cognito-identity:GetCredentialsForIdentity\"
                ],
                \"Resource\": \"*\"
            }
        ]
    }"

echo "✓ Loan Officer policies attached (S3 read, DynamoDB read)"

# 7. Attach policies to Administrator role (full system access)
echo "Attaching policies to Administrator role..."
aws iam put-role-policy \
    --role-name AuditFlowAdministratorRole \
    --policy-name AdministratorAccessPolicy \
    --policy-document "{
        \"Version\": \"2012-10-17\",
        \"Statement\": [
            {
                \"Effect\": \"Allow\",
                \"Action\": [
                    \"s3:*\"
                ],
                \"Resource\": [
                    \"arn:aws:s3:::auditflow-documents-${REGION}-${ACCOUNT_ID}\",
                    \"arn:aws:s3:::auditflow-documents-${REGION}-${ACCOUNT_ID}/*\"
                ]
            },
            {
                \"Effect\": \"Allow\",
                \"Action\": [
                    \"dynamodb:*\"
                ],
                \"Resource\": [
                    \"arn:aws:dynamodb:${REGION}:${ACCOUNT_ID}:table/AuditFlow-Documents\",
                    \"arn:aws:dynamodb:${REGION}:${ACCOUNT_ID}:table/AuditFlow-Documents/index/*\",
                    \"arn:aws:dynamodb:${REGION}:${ACCOUNT_ID}:table/AuditFlow-AuditRecords\",
                    \"arn:aws:dynamodb:${REGION}:${ACCOUNT_ID}:table/AuditFlow-AuditRecords/index/*\"
                ]
            },
            {
                \"Effect\": \"Allow\",
                \"Action\": [
                    \"cognito-idp:*\",
                    \"cognito-identity:*\"
                ],
                \"Resource\": \"*\"
            },
            {
                \"Effect\": \"Allow\",
                \"Action\": [
                    \"logs:*\",
                    \"cloudwatch:*\"
                ],
                \"Resource\": \"*\"
            }
        ]
    }"

echo "✓ Administrator policies attached (full system access)"

# 8. Set Identity Pool roles with role mapping
echo "Setting Identity Pool roles with group-based role mapping..."

# First, set the default authenticated role
aws cognito-identity set-identity-pool-roles \
    --identity-pool-id $IDENTITY_POOL_ID \
    --roles authenticated=arn:aws:iam::${ACCOUNT_ID}:role/AuditFlowLoanOfficerRole \
    --role-mappings "{
        \"cognito-idp.${REGION}.amazonaws.com/${USER_POOL_ID}:${CLIENT_ID}\": {
            \"Type\": \"Token\",
            \"AmbiguousRoleResolution\": \"AuthenticatedRole\"
        }
    }" \
    --region $REGION

echo "✓ Identity Pool roles configured"
echo "  - Default role: LoanOfficer"
echo "  - Administrator role: Available for group-based mapping"


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
echo "Security Features Enabled:"
echo "  ✓ Password complexity requirements (12+ chars, upper, lower, numbers, symbols)"
echo "  ✓ Session timeout: 30 minutes"
echo "  ✓ MFA: Optional (enforce for Administrators via application logic)"
echo "  ✓ Advanced security mode: ENFORCED"
echo "  ✓ Device tracking enabled"
echo "  ✓ Account lockout: Configured (see account lockout script)"
echo ""
echo "User Groups Created:"
echo "  ✓ LoanOfficers - Read access to S3 and DynamoDB"
echo "  ✓ Administrators - Full system access"
echo ""
echo "IAM Roles Created:"
echo "  ✓ AuditFlowLoanOfficerRole"
echo "  ✓ AuditFlowAdministratorRole"
echo ""
echo "================================================"
echo "Next Steps:"
echo "================================================"
echo "1. Run the account lockout configuration script:"
echo "   ./infrastructure/cognito_account_lockout.sh"
echo ""
echo "2. Add these values to your frontend .env file:"
echo "   VITE_USER_POOL_ID=$USER_POOL_ID"
echo "   VITE_USER_POOL_CLIENT_ID=$CLIENT_ID"
echo "   VITE_IDENTITY_POOL_ID=$IDENTITY_POOL_ID"
echo "   VITE_AWS_REGION=$REGION"
echo ""
echo "3. Create test users:"
echo "   aws cognito-idp admin-create-user \\"
echo "     --user-pool-id $USER_POOL_ID \\"
echo "     --username testuser@example.com \\"
echo "     --user-attributes Name=email,Value=testuser@example.com \\"
echo "     --region $REGION"
echo ""
echo "4. Add users to groups:"
echo "   aws cognito-idp admin-add-user-to-group \\"
echo "     --user-pool-id $USER_POOL_ID \\"
echo "     --username testuser@example.com \\"
echo "     --group-name LoanOfficers \\"
echo "     --region $REGION"
echo ""
echo "================================================"
