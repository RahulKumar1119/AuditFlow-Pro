#!/bin/bash
# infrastructure/fix_stepfunctions_role.sh
# Adds DynamoDB permissions to AuditFlowStepFunctionsRole

set -e

REGION="${AWS_REGION:-ap-south-1}"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

echo "Adding DynamoDB permissions to AuditFlowStepFunctionsRole..."
echo "Region: $REGION"
echo "Account: $ACCOUNT_ID"
echo ""

# Add DynamoDB policy to Step Functions role
aws iam put-role-policy \
    --role-name AuditFlowStepFunctionsRole \
    --policy-name DynamoDBAccessPolicy \
    --policy-document '{
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "dynamodb:PutItem",
                    "dynamodb:GetItem",
                    "dynamodb:UpdateItem",
                    "dynamodb:Query",
                    "dynamodb:Scan"
                ],
                "Resource": [
                    "arn:aws:dynamodb:'$REGION':'$ACCOUNT_ID':table/AuditFlow-Documents",
                    "arn:aws:dynamodb:'$REGION':'$ACCOUNT_ID':table/AuditFlow-Documents/index/*",
                    "arn:aws:dynamodb:'$REGION':'$ACCOUNT_ID':table/AuditFlow-AuditRecords",
                    "arn:aws:dynamodb:'$REGION':'$ACCOUNT_ID':table/AuditFlow-AuditRecords/index/*"
                ]
            }
        ]
    }'

echo "✓ DynamoDB policy added to AuditFlowStepFunctionsRole"
echo ""
echo "The Step Functions execution role now has permission to:"
echo "  - dynamodb:PutItem (save documents)"
echo "  - dynamodb:GetItem (load documents)"
echo "  - dynamodb:UpdateItem (update documents)"
echo "  - dynamodb:Query (query documents)"
echo "  - dynamodb:Scan (scan documents)"
echo ""
echo "On tables:"
echo "  - AuditFlow-Documents"
echo "  - AuditFlow-AuditRecords"
echo ""
echo "Fix complete! You can now retry the Step Function execution."
