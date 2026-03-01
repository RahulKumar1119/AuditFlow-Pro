#!/bin/bash
# infrastructure/teardown.sh
# Tears down all AuditFlow-Pro AWS infrastructure

set -e

REGION="${AWS_REGION:-ap-south-1}"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
BUCKET_NAME="auditflow-documents-prod-${ACCOUNT_ID}"

echo "WARNING: This will delete all AuditFlow-Pro infrastructure!"
echo "Region: $REGION"
echo "Account ID: $ACCOUNT_ID"
echo ""
read -p "Are you sure you want to continue? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "Teardown cancelled."
    exit 0
fi

echo "Starting teardown..."

# 1. Delete S3 bucket (must empty first)
echo "Emptying and deleting S3 bucket: $BUCKET_NAME..."
aws s3 rm s3://$BUCKET_NAME --recursive --region $REGION 2>/dev/null || echo "Bucket already empty or doesn't exist"
aws s3api delete-bucket --bucket $BUCKET_NAME --region $REGION 2>/dev/null || echo "Bucket doesn't exist"

# 2. Delete DynamoDB tables
echo "Deleting DynamoDB table: AuditFlow-Documents..."
aws dynamodb delete-table --table-name AuditFlow-Documents --region $REGION 2>/dev/null || echo "Table doesn't exist"

echo "Deleting DynamoDB table: AuditFlow-AuditRecords..."
aws dynamodb delete-table --table-name AuditFlow-AuditRecords --region $REGION 2>/dev/null || echo "Table doesn't exist"

# 3. Delete Lambda functions
echo "Deleting Lambda functions..."
for FUNCTION in AuditFlow-Classifier AuditFlow-Extractor AuditFlow-Validator AuditFlow-RiskScorer AuditFlow-Reporter AuditFlow-Trigger AuditFlow-APIHandler; do
    aws lambda delete-function --function-name $FUNCTION --region $REGION 2>/dev/null || echo "Function $FUNCTION doesn't exist"
done

# 4. Delete Step Functions state machine
echo "Deleting Step Functions state machine..."
STATE_MACHINE_ARN="arn:aws:states:${REGION}:${ACCOUNT_ID}:stateMachine:AuditFlowWorkflow"
aws stepfunctions delete-state-machine --state-machine-arn $STATE_MACHINE_ARN 2>/dev/null || echo "State machine doesn't exist"

# 5. Delete API Gateway
echo "Deleting API Gateway..."
API_ID=$(aws apigateway get-rest-apis --region $REGION --query "items[?name=='AuditFlowAPI'].id" --output text 2>/dev/null)
if [ ! -z "$API_ID" ]; then
    aws apigateway delete-rest-api --rest-api-id $API_ID --region $REGION
fi

# 6. Delete Cognito User Pool
echo "Deleting Cognito User Pool..."
USER_POOL_ID=$(aws cognito-idp list-user-pools --max-results 60 --region $REGION --query "UserPools[?Name=='AuditFlowUserPool'].Id" --output text 2>/dev/null)
if [ ! -z "$USER_POOL_ID" ]; then
    aws cognito-idp delete-user-pool --user-pool-id $USER_POOL_ID --region $REGION
fi

# 7. Delete Cognito Identity Pool
echo "Deleting Cognito Identity Pool..."
IDENTITY_POOL_ID=$(aws cognito-identity list-identity-pools --max-results 60 --region $REGION --query "IdentityPools[?IdentityPoolName=='AuditFlowIdentityPool'].IdentityPoolId" --output text 2>/dev/null)
if [ ! -z "$IDENTITY_POOL_ID" ]; then
    aws cognito-identity delete-identity-pool --identity-pool-id $IDENTITY_POOL_ID --region $REGION
fi

# 8. Delete IAM roles and policies
echo "Deleting IAM roles and policies..."

# Delete inline policies first
for ROLE in AuditFlowLambdaExecutionRole AuditFlowStepFunctionsRole AuditFlowAPIGatewayRole AuditFlowCognitoAuthRole; do
    echo "Deleting policies for role: $ROLE..."
    POLICIES=$(aws iam list-role-policies --role-name $ROLE --query 'PolicyNames' --output text 2>/dev/null)
    for POLICY in $POLICIES; do
        aws iam delete-role-policy --role-name $ROLE --policy-name $POLICY 2>/dev/null || echo "Policy $POLICY doesn't exist"
    done
    
    # Detach managed policies
    ATTACHED_POLICIES=$(aws iam list-attached-role-policies --role-name $ROLE --query 'AttachedPolicies[].PolicyArn' --output text 2>/dev/null)
    for POLICY_ARN in $ATTACHED_POLICIES; do
        aws iam detach-role-policy --role-name $ROLE --policy-arn $POLICY_ARN 2>/dev/null || echo "Policy $POLICY_ARN not attached"
    done
    
    # Delete role
    aws iam delete-role --role-name $ROLE 2>/dev/null || echo "Role $ROLE doesn't exist"
done

# 9. Delete CloudWatch Log Groups
echo "Deleting CloudWatch Log Groups..."
for LOG_GROUP in /aws/lambda/AuditFlow-Classifier /aws/lambda/AuditFlow-Extractor /aws/lambda/AuditFlow-Validator /aws/lambda/AuditFlow-RiskScorer /aws/lambda/AuditFlow-Reporter /aws/lambda/AuditFlow-Trigger /aws/lambda/AuditFlow-APIHandler /aws/states/AuditFlowWorkflow; do
    aws logs delete-log-group --log-group-name $LOG_GROUP --region $REGION 2>/dev/null || echo "Log group $LOG_GROUP doesn't exist"
done

echo ""
echo "Teardown completed successfully!"
echo "All AuditFlow-Pro infrastructure has been deleted."
