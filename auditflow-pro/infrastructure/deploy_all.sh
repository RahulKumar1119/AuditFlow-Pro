#!/bin/bash
# infrastructure/deploy_all.sh
# Master deployment script for AuditFlow-Pro infrastructure

set -e

REGION="${AWS_REGION:-us-east-1}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=========================================="
echo "AuditFlow-Pro Infrastructure Deployment"
echo "=========================================="
echo "Region: $REGION"
echo "Script Directory: $SCRIPT_DIR"
echo ""

# Make all scripts executable
chmod +x "$SCRIPT_DIR"/*.sh

# Step 1: Deploy base infrastructure (S3, DynamoDB)
echo "Step 1: Deploying base infrastructure..."
bash "$SCRIPT_DIR/deploy.sh"
echo "Waiting 10 seconds for resources to be ready..."
sleep 10

# Step 2: Configure S3 bucket (CORS, lifecycle)
echo ""
echo "Step 2: Configuring S3 bucket..."
bash "$SCRIPT_DIR/s3_config.sh"

# Step 3: Configure DynamoDB tables (encryption, TTL)
echo ""
echo "Step 3: Configuring DynamoDB tables..."
bash "$SCRIPT_DIR/dynamodb_config.sh"

# Step 4: Create IAM roles and policies
echo ""
echo "Step 4: Creating IAM roles and policies..."
bash "$SCRIPT_DIR/iam_policies.sh"

# Step 5: Set up Cognito authentication
echo ""
echo "Step 5: Setting up Cognito authentication..."
bash "$SCRIPT_DIR/cognito_setup.sh"

echo ""
echo "=========================================="
echo "Infrastructure Deployment Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Update frontend/.env with Cognito configuration values"
echo "2. Deploy Lambda functions using backend deployment scripts"
echo "3. Create Step Functions state machine"
echo "4. Set up API Gateway"
echo "5. Deploy frontend to AWS Amplify"
echo ""
echo "To tear down all infrastructure, run:"
echo "  bash $SCRIPT_DIR/teardown.sh"
