#!/bin/bash
# infrastructure/step_functions_deploy.sh
# Deploy Step Functions state machine for AuditFlow-Pro

set -e

REGION="ap-south-1"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
STATE_MACHINE_NAME="AuditFlowDocumentProcessing"

echo "=========================================="
echo "Deploying Step Functions State Machine"
echo "Region: $REGION"
echo "Account: $ACCOUNT_ID"
echo "=========================================="
echo ""

# Get Lambda function ARNs
echo "Retrieving Lambda function ARNs..."
CLASSIFIER_ARN=$(aws lambda get-function --function-name AuditFlow-Classifier --query 'Configuration.FunctionArn' --output text 2>/dev/null || echo "")
EXTRACTOR_ARN=$(aws lambda get-function --function-name AuditFlow-Extractor --query 'Configuration.FunctionArn' --output text 2>/dev/null || echo "")
VALIDATOR_ARN=$(aws lambda get-function --function-name AuditFlow-Validator --query 'Configuration.FunctionArn' --output text 2>/dev/null || echo "")
RISK_SCORER_ARN=$(aws lambda get-function --function-name AuditFlow-RiskScorer --query 'Configuration.FunctionArn' --output text 2>/dev/null || echo "")
REPORTER_ARN=$(aws lambda get-function --function-name AuditFlow-Reporter --query 'Configuration.FunctionArn' --output text 2>/dev/null || echo "")

if [ -z "$CLASSIFIER_ARN" ] || [ -z "$EXTRACTOR_ARN" ] || [ -z "$VALIDATOR_ARN" ] || [ -z "$RISK_SCORER_ARN" ] || [ -z "$REPORTER_ARN" ]; then
    echo "Error: One or more Lambda functions not found. Please deploy Lambda functions first."
    echo "Missing functions:"
    [ -z "$CLASSIFIER_ARN" ] && echo "  - AuditFlow-Classifier"
    [ -z "$EXTRACTOR_ARN" ] && echo "  - AuditFlow-Extractor"
    [ -z "$VALIDATOR_ARN" ] && echo "  - AuditFlow-Validator"
    [ -z "$RISK_SCORER_ARN" ] && echo "  - AuditFlow-RiskScorer"
    [ -z "$REPORTER_ARN" ] && echo "  - AuditFlow-Reporter"
    exit 1
fi

echo "✓ Lambda function ARNs retrieved"
echo "  Classifier: $CLASSIFIER_ARN"
echo "  Extractor: $EXTRACTOR_ARN"
echo "  Validator: $VALIDATOR_ARN"
echo "  Risk Scorer: $RISK_SCORER_ARN"
echo "  Reporter: $REPORTER_ARN"
echo ""

# Create IAM role for Step Functions if it doesn't exist
echo "Creating Step Functions execution role..."
ROLE_NAME="AuditFlowStepFunctionsRole"

if aws iam get-role --role-name $ROLE_NAME 2>/dev/null; then
    echo "Role $ROLE_NAME already exists"
    ROLE_ARN=$(aws iam get-role --role-name $ROLE_NAME --query 'Role.Arn' --output text)
else
    # Create the role
    ROLE_ARN=$(aws iam create-role \
        --role-name $ROLE_NAME \
        --assume-role-policy-document '{
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Principal": {
                    "Service": "states.amazonaws.com"
                },
                "Action": "sts:AssumeRole"
            }]
        }' \
        --query 'Role.Arn' \
        --output text)
    
    echo "✓ Role created: $ROLE_ARN"
    
    # Attach policy to invoke Lambda functions
    aws iam put-role-policy \
        --role-name $ROLE_NAME \
        --policy-name StepFunctionsLambdaInvokePolicy \
        --policy-document '{
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "lambda:InvokeFunction"
                    ],
                    "Resource": [
                        "'$CLASSIFIER_ARN'",
                        "'$EXTRACTOR_ARN'",
                        "'$VALIDATOR_ARN'",
                        "'$RISK_SCORER_ARN'",
                        "'$REPORTER_ARN'"
                    ]
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "logs:CreateLogDelivery",
                        "logs:GetLogDelivery",
                        "logs:UpdateLogDelivery",
                        "logs:DeleteLogDelivery",
                        "logs:ListLogDeliveries",
                        "logs:PutResourcePolicy",
                        "logs:DescribeResourcePolicies",
                        "logs:DescribeLogGroups"
                    ],
                    "Resource": "*"
                }
            ]
        }'
    
    echo "✓ IAM policies attached"
    
    # Wait for role to be available
    echo "Waiting for IAM role to propagate..."
    sleep 10
fi

echo ""

# Create CloudWatch Log Group for Step Functions
LOG_GROUP_NAME="/aws/vendedlogs/states/AuditFlowDocumentProcessing"
echo "Creating CloudWatch Log Group: $LOG_GROUP_NAME..."

if aws logs describe-log-groups --log-group-name-prefix "$LOG_GROUP_NAME" --query "logGroups[?logGroupName=='$LOG_GROUP_NAME']" --output text | grep -q "$LOG_GROUP_NAME"; then
    echo "Log group already exists"
else
    aws logs create-log-group --log-group-name "$LOG_GROUP_NAME"
    
    # Set retention policy to 1 year (365 days)
    aws logs put-retention-policy \
        --log-group-name "$LOG_GROUP_NAME" \
        --retention-in-days 365
    
    echo "✓ Log group created with 1-year retention"
fi

echo ""

# Substitute Lambda ARNs in state machine definition
echo "Preparing state machine definition..."
STATE_MACHINE_FILE="backend/step_functions/state_machine.asl.json"

if [ ! -f "$STATE_MACHINE_FILE" ]; then
    echo "Error: State machine definition not found at $STATE_MACHINE_FILE"
    exit 1
fi

# Create temporary file with substituted ARNs
TEMP_FILE=$(mktemp)
sed -e "s|\${ClassifierFunctionArn}|$CLASSIFIER_ARN|g" \
    -e "s|\${ExtractorFunctionArn}|$EXTRACTOR_ARN|g" \
    -e "s|\${ValidatorFunctionArn}|$VALIDATOR_ARN|g" \
    -e "s|\${RiskScorerFunctionArn}|$RISK_SCORER_ARN|g" \
    -e "s|\${ReporterFunctionArn}|$REPORTER_ARN|g" \
    "$STATE_MACHINE_FILE" > "$TEMP_FILE"

echo "✓ State machine definition prepared"
echo ""

# Create or update state machine
echo "Deploying state machine: $STATE_MACHINE_NAME..."

STATE_MACHINE_ARN="arn:aws:states:$REGION:$ACCOUNT_ID:stateMachine:$STATE_MACHINE_NAME"

if aws stepfunctions describe-state-machine --state-machine-arn "$STATE_MACHINE_ARN" 2>/dev/null; then
    echo "State machine exists, updating..."
    aws stepfunctions update-state-machine \
        --state-machine-arn "$STATE_MACHINE_ARN" \
        --definition file://"$TEMP_FILE" \
        --role-arn "$ROLE_ARN" \
        --logging-configuration '{
            "level": "ALL",
            "includeExecutionData": true,
            "destinations": [{
                "cloudWatchLogsLogGroup": {
                    "logGroupArn": "arn:aws:logs:'$REGION':'$ACCOUNT_ID':log-group:'$LOG_GROUP_NAME':*"
                }
            }]
        }'
    echo "✓ State machine updated"
else
    echo "Creating new state machine..."
    aws stepfunctions create-state-machine \
        --name "$STATE_MACHINE_NAME" \
        --definition file://"$TEMP_FILE" \
        --role-arn "$ROLE_ARN" \
        --type STANDARD \
        --logging-configuration '{
            "level": "ALL",
            "includeExecutionData": true,
            "destinations": [{
                "cloudWatchLogsLogGroup": {
                    "logGroupArn": "arn:aws:logs:'$REGION':'$ACCOUNT_ID':log-group:'$LOG_GROUP_NAME':*"
                }
            }]
        }'
    echo "✓ State machine created"
fi

# Clean up temporary file
rm "$TEMP_FILE"

echo ""
echo "=========================================="
echo "Step Functions deployment complete!"
echo "=========================================="
echo "State Machine ARN: $STATE_MACHINE_ARN"
echo "Execution Role: $ROLE_ARN"
echo "Log Group: $LOG_GROUP_NAME"
echo ""
echo "To start an execution:"
echo "  aws stepfunctions start-execution \\"
echo "    --state-machine-arn $STATE_MACHINE_ARN \\"
echo "    --input '{\"loan_application_id\":\"test-123\",\"documents\":[{\"document_id\":\"doc-1\",\"s3_bucket\":\"your-bucket\",\"s3_key\":\"path/to/doc.pdf\"}]}'"
echo "=========================================="
