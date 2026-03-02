#!/bin/bash
# teardown-master.sh
# Master teardown script for AuditFlow-Pro
# Safely removes all infrastructure in the correct order

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_DIR="$SCRIPT_DIR/config"

# Default values
ENVIRONMENT="${ENVIRONMENT:-dev}"
CONFIG_FILE="$CONFIG_DIR/${ENVIRONMENT}.env"
FORCE=false
DRY_RUN=false
KEEP_DATA=false

# Usage information
usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Master teardown script for AuditFlow-Pro infrastructure.
Safely removes all resources in the correct order.

OPTIONS:
    -e, --environment ENV    Environment to tear down (dev, staging, prod) [default: dev]
    -c, --config FILE        Path to configuration file [default: config/ENV.env]
    -f, --force              Skip confirmation prompt
    -d, --dry-run            Show what would be deleted without making changes
    -k, --keep-data          Keep S3 data and DynamoDB tables (delete only compute resources)
    -h, --help               Show this help message

EXAMPLES:
    # Tear down development environment (with confirmation)
    $0 -e dev

    # Force tear down production (no confirmation)
    $0 -e prod --force

    # Dry run to see what would be deleted
    $0 -e staging --dry-run

    # Keep data, delete only compute resources
    $0 -e dev --keep-data

WARNING:
    This script will DELETE all resources in the specified environment.
    This action CANNOT be undone. Make sure you have backups if needed.

EOF
    exit 1
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--environment)
            ENVIRONMENT="$2"
            CONFIG_FILE="$CONFIG_DIR/${ENVIRONMENT}.env"
            shift 2
            ;;
        -c|--config)
            CONFIG_FILE="$2"
            shift 2
            ;;
        -f|--force)
            FORCE=true
            shift
            ;;
        -d|--dry-run)
            DRY_RUN=true
            shift
            ;;
        -k|--keep-data)
            KEEP_DATA=true
            shift
            ;;
        -h|--help)
            usage
            ;;
        *)
            echo -e "${RED}Error: Unknown option $1${NC}"
            usage
            ;;
    esac
done

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_section() {
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

# Load configuration
load_config() {
    log_section "Loading Configuration"
    
    if [ ! -f "$CONFIG_FILE" ]; then
        log_error "Configuration file not found: $CONFIG_FILE"
        exit 1
    fi
    
    log_info "Loading configuration from: $CONFIG_FILE"
    source "$CONFIG_FILE"
    
    ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    
    log_success "Configuration loaded"
    log_info "Environment: $ENVIRONMENT"
    log_info "Region: $AWS_REGION"
    log_info "Account: $ACCOUNT_ID"
}

# Confirmation prompt
confirm_teardown() {
    if [ "$FORCE" = true ]; then
        log_warning "Force mode enabled - skipping confirmation"
        return 0
    fi
    
    log_section "CONFIRMATION REQUIRED"
    echo -e "${RED}WARNING: This will DELETE all AuditFlow-Pro infrastructure!${NC}"
    echo ""
    echo "Environment: $ENVIRONMENT"
    echo "Region: $AWS_REGION"
    echo "Account: $ACCOUNT_ID"
    echo ""
    
    if [ "$KEEP_DATA" = true ]; then
        echo "Mode: Keep data (S3 and DynamoDB will be preserved)"
    else
        echo "Mode: Full teardown (ALL data will be DELETED)"
    fi
    
    echo ""
    read -p "Type 'DELETE' to confirm: " CONFIRM
    
    if [ "$CONFIRM" != "DELETE" ]; then
        log_info "Teardown cancelled"
        exit 0
    fi
    
    log_warning "Teardown confirmed. Starting in 5 seconds..."
    sleep 5
}

# Delete CloudWatch log groups
delete_log_groups() {
    log_section "Deleting CloudWatch Log Groups"
    
    local log_groups=(
        "/aws/lambda/AuditFlow-Classifier"
        "/aws/lambda/AuditFlow-Extractor"
        "/aws/lambda/AuditFlow-Validator"
        "/aws/lambda/AuditFlow-RiskScorer"
        "/aws/lambda/AuditFlow-Reporter"
        "/aws/lambda/AuditFlow-Trigger"
        "/aws/lambda/AuditFlow-APIHandler"
        "/aws/lambda/AuditFlow-AuthLogger"
        "/aws/states/AuditFlowWorkflow"
        "/aws/apigateway/AuditFlowAPI"
        "/aws/cognito/AuditFlowUserPool"
    )
    
    for log_group in "${log_groups[@]}"; do
        log_info "Deleting log group: $log_group"
        aws logs delete-log-group \
            --log-group-name "$log_group" \
            --region "$AWS_REGION" 2>/dev/null || echo "  Log group not found or already deleted"
    done
    
    log_success "CloudWatch log groups deleted"
}

# Delete Lambda functions
delete_lambda_functions() {
    log_section "Deleting Lambda Functions"
    
    local functions=(
        "AuditFlow-Classifier"
        "AuditFlow-Extractor"
        "AuditFlow-Validator"
        "AuditFlow-RiskScorer"
        "AuditFlow-Reporter"
        "AuditFlow-Trigger"
        "AuditFlow-APIHandler"
        "AuditFlow-AuthLogger"
    )
    
    for function in "${functions[@]}"; do
        log_info "Deleting Lambda function: $function"
        aws lambda delete-function \
            --function-name "$function" \
            --region "$AWS_REGION" 2>/dev/null || echo "  Function not found or already deleted"
    done
    
    log_success "Lambda functions deleted"
}

# Delete Step Functions state machine
delete_step_functions() {
    log_section "Deleting Step Functions State Machine"
    
    STATE_MACHINE_ARN="arn:aws:states:${AWS_REGION}:${ACCOUNT_ID}:stateMachine:${STEP_FUNCTION_NAME}"
    
    log_info "Deleting state machine: $STEP_FUNCTION_NAME"
    aws stepfunctions delete-state-machine \
        --state-machine-arn "$STATE_MACHINE_ARN" \
        --region "$AWS_REGION" 2>/dev/null || echo "  State machine not found or already deleted"
    
    log_success "Step Functions state machine deleted"
}

# Delete API Gateway
delete_api_gateway() {
    log_section "Deleting API Gateway"
    
    API_ID=$(aws apigateway get-rest-apis \
        --region "$AWS_REGION" \
        --query "items[?name=='${API_GATEWAY_NAME}'].id" \
        --output text 2>/dev/null)
    
    if [ -n "$API_ID" ] && [ "$API_ID" != "None" ]; then
        log_info "Deleting API Gateway: $API_GATEWAY_NAME (ID: $API_ID)"
        aws apigateway delete-rest-api \
            --rest-api-id "$API_ID" \
            --region "$AWS_REGION" 2>/dev/null || echo "  API Gateway deletion failed"
        log_success "API Gateway deleted"
    else
        log_info "API Gateway not found"
    fi
}

# Delete Cognito resources
delete_cognito() {
    log_section "Deleting Cognito Resources"
    
    # Delete User Pool
    USER_POOL_ID=$(aws cognito-idp list-user-pools \
        --max-results 60 \
        --region "$AWS_REGION" \
        --query "UserPools[?Name=='${USER_POOL_NAME}'].Id" \
        --output text 2>/dev/null)
    
    if [ -n "$USER_POOL_ID" ] && [ "$USER_POOL_ID" != "None" ]; then
        log_info "Deleting Cognito User Pool: $USER_POOL_NAME (ID: $USER_POOL_ID)"
        
        # Delete all users first
        log_info "Deleting all users from User Pool..."
        USERS=$(aws cognito-idp list-users \
            --user-pool-id "$USER_POOL_ID" \
            --region "$AWS_REGION" \
            --query 'Users[].Username' \
            --output text 2>/dev/null)
        
        for user in $USERS; do
            aws cognito-idp admin-delete-user \
                --user-pool-id "$USER_POOL_ID" \
                --username "$user" \
                --region "$AWS_REGION" 2>/dev/null || echo "  Failed to delete user: $user"
        done
        
        # Delete User Pool
        aws cognito-idp delete-user-pool \
            --user-pool-id "$USER_POOL_ID" \
            --region "$AWS_REGION" 2>/dev/null || echo "  User Pool deletion failed"
        log_success "Cognito User Pool deleted"
    else
        log_info "Cognito User Pool not found"
    fi
    
    # Delete Identity Pool
    IDENTITY_POOL_ID=$(aws cognito-identity list-identity-pools \
        --max-results 60 \
        --region "$AWS_REGION" \
        --query "IdentityPools[?IdentityPoolName=='${IDENTITY_POOL_NAME}'].IdentityPoolId" \
        --output text 2>/dev/null)
    
    if [ -n "$IDENTITY_POOL_ID" ] && [ "$IDENTITY_POOL_ID" != "None" ]; then
        log_info "Deleting Cognito Identity Pool: $IDENTITY_POOL_NAME (ID: $IDENTITY_POOL_ID)"
        aws cognito-identity delete-identity-pool \
            --identity-pool-id "$IDENTITY_POOL_ID" \
            --region "$AWS_REGION" 2>/dev/null || echo "  Identity Pool deletion failed"
        log_success "Cognito Identity Pool deleted"
    else
        log_info "Cognito Identity Pool not found"
    fi
}

# Delete S3 bucket
delete_s3_bucket() {
    if [ "$KEEP_DATA" = true ]; then
        log_warning "Skipping S3 bucket deletion (--keep-data flag set)"
        return 0
    fi
    
    log_section "Deleting S3 Bucket"
    
    BUCKET_NAME="${S3_BUCKET_PREFIX}-${ACCOUNT_ID}"
    
    log_info "Emptying S3 bucket: $BUCKET_NAME"
    aws s3 rm "s3://$BUCKET_NAME" \
        --recursive \
        --region "$AWS_REGION" 2>/dev/null || echo "  Bucket already empty or doesn't exist"
    
    log_info "Deleting S3 bucket: $BUCKET_NAME"
    aws s3api delete-bucket \
        --bucket "$BUCKET_NAME" \
        --region "$AWS_REGION" 2>/dev/null || echo "  Bucket doesn't exist or deletion failed"
    
    log_success "S3 bucket deleted"
}

# Delete DynamoDB tables
delete_dynamodb_tables() {
    if [ "$KEEP_DATA" = true ]; then
        log_warning "Skipping DynamoDB table deletion (--keep-data flag set)"
        return 0
    fi
    
    log_section "Deleting DynamoDB Tables"
    
    local tables=("AuditFlow-Documents" "AuditFlow-AuditRecords")
    
    for table in "${tables[@]}"; do
        log_info "Deleting DynamoDB table: $table"
        aws dynamodb delete-table \
            --table-name "$table" \
            --region "$AWS_REGION" 2>/dev/null || echo "  Table not found or already deleted"
        
        # Wait for table deletion
        log_info "Waiting for table deletion to complete..."
        aws dynamodb wait table-not-exists \
            --table-name "$table" \
            --region "$AWS_REGION" 2>/dev/null || echo "  Table already deleted"
    done
    
    log_success "DynamoDB tables deleted"
}

# Delete IAM roles and policies
delete_iam_roles() {
    log_section "Deleting IAM Roles and Policies"
    
    local roles=(
        "AuditFlowLambdaExecutionRole"
        "AuditFlowStepFunctionsRole"
        "AuditFlowAPIGatewayRole"
        "AuditFlowCognitoAuthRole"
        "AuditFlow-S3-Replication-Role"
    )
    
    for role in "${roles[@]}"; do
        log_info "Deleting IAM role: $role"
        
        # Delete inline policies
        POLICIES=$(aws iam list-role-policies \
            --role-name "$role" \
            --query 'PolicyNames' \
            --output text 2>/dev/null)
        
        for policy in $POLICIES; do
            aws iam delete-role-policy \
                --role-name "$role" \
                --policy-name "$policy" 2>/dev/null || echo "  Policy $policy not found"
        done
        
        # Detach managed policies
        ATTACHED_POLICIES=$(aws iam list-attached-role-policies \
            --role-name "$role" \
            --query 'AttachedPolicies[].PolicyArn' \
            --output text 2>/dev/null)
        
        for policy_arn in $ATTACHED_POLICIES; do
            aws iam detach-role-policy \
                --role-name "$role" \
                --policy-arn "$policy_arn" 2>/dev/null || echo "  Policy $policy_arn not attached"
        done
        
        # Delete role
        aws iam delete-role \
            --role-name "$role" 2>/dev/null || echo "  Role not found or already deleted"
    done
    
    log_success "IAM roles deleted"
}

# Delete KMS keys
delete_kms_keys() {
    if [ "$KEEP_DATA" = true ]; then
        log_warning "Skipping KMS key deletion (--keep-data flag set)"
        log_info "Note: KMS keys will be scheduled for deletion (7-30 day waiting period)"
        return 0
    fi
    
    log_section "Scheduling KMS Keys for Deletion"
    
    local key_aliases=(
        "alias/auditflow-s3-encryption"
        "alias/auditflow-dynamodb-encryption"
    )
    
    for alias in "${key_aliases[@]}"; do
        log_info "Scheduling KMS key for deletion: $alias"
        
        KEY_ID=$(aws kms describe-key \
            --key-id "$alias" \
            --region "$AWS_REGION" \
            --query 'KeyMetadata.KeyId' \
            --output text 2>/dev/null)
        
        if [ -n "$KEY_ID" ] && [ "$KEY_ID" != "None" ]; then
            # Delete alias first
            aws kms delete-alias \
                --alias-name "$alias" \
                --region "$AWS_REGION" 2>/dev/null || echo "  Alias not found"
            
            # Schedule key deletion (minimum 7 days)
            aws kms schedule-key-deletion \
                --key-id "$KEY_ID" \
                --pending-window-in-days 7 \
                --region "$AWS_REGION" 2>/dev/null || echo "  Key already scheduled for deletion"
            
            log_success "KMS key scheduled for deletion in 7 days: $KEY_ID"
        else
            log_info "KMS key not found: $alias"
        fi
    done
}

# Delete SNS topics
delete_sns_topics() {
    log_section "Deleting SNS Topics"
    
    SNS_TOPIC_NAME="AuditFlow-SecurityAlerts-${ENVIRONMENT}"
    
    SNS_TOPIC_ARN=$(aws sns list-topics \
        --region "$AWS_REGION" \
        --query "Topics[?contains(TopicArn, '${SNS_TOPIC_NAME}')].TopicArn" \
        --output text 2>/dev/null)
    
    if [ -n "$SNS_TOPIC_ARN" ] && [ "$SNS_TOPIC_ARN" != "None" ]; then
        log_info "Deleting SNS topic: $SNS_TOPIC_NAME"
        aws sns delete-topic \
            --topic-arn "$SNS_TOPIC_ARN" \
            --region "$AWS_REGION" 2>/dev/null || echo "  Topic deletion failed"
        log_success "SNS topic deleted"
    else
        log_info "SNS topic not found"
    fi
}

# Delete CloudWatch alarms
delete_cloudwatch_alarms() {
    log_section "Deleting CloudWatch Alarms"
    
    local alarms=(
        "AuditFlow-UnauthorizedAPICalls-${ENVIRONMENT}"
        "AuditFlow-LambdaErrors-${ENVIRONMENT}"
    )
    
    for alarm in "${alarms[@]}"; do
        log_info "Deleting CloudWatch alarm: $alarm"
        aws cloudwatch delete-alarms \
            --alarm-names "$alarm" \
            --region "$AWS_REGION" 2>/dev/null || echo "  Alarm not found"
    done
    
    log_success "CloudWatch alarms deleted"
}

# Dry run mode
if [ "$DRY_RUN" = true ]; then
    log_section "DRY RUN MODE"
    log_warning "This is a dry run. No resources will be deleted."
    load_config
    
    log_section "Teardown Plan"
    echo "The following resources would be deleted:"
    echo ""
    echo "Compute Resources:"
    echo "  - Lambda functions (8 functions)"
    echo "  - Step Functions state machine"
    echo "  - API Gateway"
    echo "  - Cognito User Pool and Identity Pool"
    echo "  - CloudWatch log groups"
    echo "  - CloudWatch alarms"
    echo "  - SNS topics"
    echo ""
    
    if [ "$KEEP_DATA" = true ]; then
        echo "Data Resources (PRESERVED):"
        echo "  - S3 bucket (kept)"
        echo "  - DynamoDB tables (kept)"
        echo "  - KMS keys (kept)"
    else
        echo "Data Resources (DELETED):"
        echo "  - S3 bucket and all contents"
        echo "  - DynamoDB tables and all data"
        echo "  - KMS keys (scheduled for deletion)"
    fi
    
    echo ""
    echo "IAM Resources:"
    echo "  - IAM roles and policies"
    echo ""
    log_info "To execute teardown, run without --dry-run flag"
    exit 0
fi

# Main teardown
main() {
    log_section "AuditFlow-Pro Master Teardown"
    log_info "Starting teardown at $(date)"
    
    # Load configuration
    load_config
    
    # Confirm teardown
    confirm_teardown
    
    # Delete resources in correct order
    delete_cloudwatch_alarms
    delete_sns_topics
    delete_log_groups
    delete_lambda_functions
    delete_step_functions
    delete_api_gateway
    delete_cognito
    delete_s3_bucket
    delete_dynamodb_tables
    delete_iam_roles
    delete_kms_keys
    
    # Teardown complete
    log_section "Teardown Complete!"
    log_success "AuditFlow-Pro infrastructure removed"
    log_info "Teardown completed at $(date)"
    
    # Summary
    echo ""
    log_section "Teardown Summary"
    echo "Environment: $ENVIRONMENT"
    echo "Region: $AWS_REGION"
    echo ""
    
    if [ "$KEEP_DATA" = true ]; then
        echo "Data Preserved:"
        echo "  - S3 bucket: ${S3_BUCKET_PREFIX}-${ACCOUNT_ID}"
        echo "  - DynamoDB tables: AuditFlow-Documents, AuditFlow-AuditRecords"
        echo ""
        echo "To delete data later, run without --keep-data flag"
    else
        echo "All resources deleted successfully"
        echo ""
        echo "Note: KMS keys are scheduled for deletion (7-day waiting period)"
        echo "To cancel KMS key deletion within 7 days:"
        echo "  aws kms cancel-key-deletion --key-id <KEY_ID>"
    fi
    
    echo ""
}

# Run main teardown
main

