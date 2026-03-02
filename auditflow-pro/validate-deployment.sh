#!/bin/bash
# validate-deployment.sh
# Validates AuditFlow-Pro deployment and tests connectivity between services

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
VERBOSE=false

# Counters
TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0
WARNING_CHECKS=0

# Usage information
usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Validates AuditFlow-Pro deployment and tests service connectivity.

OPTIONS:
    -e, --environment ENV    Environment to validate (dev, staging, prod) [default: dev]
    -c, --config FILE        Path to configuration file [default: config/ENV.env]
    -v, --verbose            Enable verbose output
    -h, --help               Show this help message

EXAMPLES:
    # Validate development environment
    $0 -e dev

    # Validate production with verbose output
    $0 -e prod -v

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
        -v|--verbose)
            VERBOSE=true
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
    echo -e "${GREEN}[✓]${NC} $1"
    ((PASSED_CHECKS++))
}

log_warning() {
    echo -e "${YELLOW}[⚠]${NC} $1"
    ((WARNING_CHECKS++))
}

log_error() {
    echo -e "${RED}[✗]${NC} $1"
    ((FAILED_CHECKS++))
}

log_section() {
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

# Check function wrapper
check() {
    local description=$1
    local command=$2
    
    ((TOTAL_CHECKS++))
    
    if [ "$VERBOSE" = true ]; then
        echo -e "${BLUE}Checking:${NC} $description"
        echo -e "${BLUE}Command:${NC} $command"
    fi
    
    if eval "$command" &> /dev/null; then
        log_success "$description"
        return 0
    else
        log_error "$description"
        return 1
    fi
}

# Check with warning
check_warn() {
    local description=$1
    local command=$2
    
    ((TOTAL_CHECKS++))
    
    if [ "$VERBOSE" = true ]; then
        echo -e "${BLUE}Checking:${NC} $description"
    fi
    
    if eval "$command" &> /dev/null; then
        log_success "$description"
        return 0
    else
        log_warning "$description"
        return 1
    fi
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
    
    log_success "Configuration loaded"
    log_info "Environment: $ENVIRONMENT"
    log_info "Region: $AWS_REGION"
}

# Validate AWS credentials
validate_aws() {
    log_section "Validating AWS Credentials"
    
    check "AWS CLI installed" "command -v aws"
    
    if aws sts get-caller-identity &> /dev/null; then
        ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
        log_success "AWS credentials valid (Account: $ACCOUNT_ID)"
    else
        log_error "AWS credentials invalid or not configured"
        exit 1
    fi
    
    check "AWS region accessible" "aws ec2 describe-regions --region-names $AWS_REGION"
}

# Validate KMS keys
validate_kms() {
    log_section "Validating KMS Encryption Keys"
    
    check "S3 KMS key exists" "aws kms describe-key --key-id alias/auditflow-s3-encryption --region $AWS_REGION"
    check "DynamoDB KMS key exists" "aws kms describe-key --key-id alias/auditflow-dynamodb-encryption --region $AWS_REGION"
    
    # Check key rotation
    if aws kms get-key-rotation-status --key-id alias/auditflow-s3-encryption --region $AWS_REGION --query 'KeyRotationEnabled' --output text 2>/dev/null | grep -q "True"; then
        log_success "KMS key rotation enabled"
    else
        log_warning "KMS key rotation not enabled"
    fi
}

# Validate S3 bucket
validate_s3() {
    log_section "Validating S3 Bucket"
    
    BUCKET_NAME="${S3_BUCKET_PREFIX}-${ACCOUNT_ID}"
    
    check "S3 bucket exists" "aws s3api head-bucket --bucket $BUCKET_NAME --region $AWS_REGION"
    
    # Check encryption
    if aws s3api get-bucket-encryption --bucket $BUCKET_NAME --region $AWS_REGION &> /dev/null; then
        log_success "S3 bucket encryption enabled"
    else
        log_error "S3 bucket encryption not enabled"
    fi
    
    # Check versioning
    if aws s3api get-bucket-versioning --bucket $BUCKET_NAME --region $AWS_REGION --query 'Status' --output text 2>/dev/null | grep -q "Enabled"; then
        log_success "S3 bucket versioning enabled"
    else
        log_warning "S3 bucket versioning not enabled"
    fi
    
    # Check public access block
    if aws s3api get-public-access-block --bucket $BUCKET_NAME --region $AWS_REGION &> /dev/null; then
        log_success "S3 public access blocked"
    else
        log_warning "S3 public access block not configured"
    fi
    
    # Check lifecycle policy
    check_warn "S3 lifecycle policy configured" "aws s3api get-bucket-lifecycle-configuration --bucket $BUCKET_NAME --region $AWS_REGION"
}

# Validate DynamoDB tables
validate_dynamodb() {
    log_section "Validating DynamoDB Tables"
    
    local tables=("AuditFlow-Documents" "AuditFlow-AuditRecords")
    
    for table in "${tables[@]}"; do
        check "Table $table exists" "aws dynamodb describe-table --table-name $table --region $AWS_REGION"
        
        # Check encryption
        if aws dynamodb describe-table --table-name $table --region $AWS_REGION --query 'Table.SSEDescription.Status' --output text 2>/dev/null | grep -q "ENABLED"; then
            log_success "Table $table encryption enabled"
        else
            log_warning "Table $table encryption not enabled"
        fi
        
        # Check TTL
        if aws dynamodb describe-time-to-live --table-name $table --region $AWS_REGION --query 'TimeToLiveDescription.TimeToLiveStatus' --output text 2>/dev/null | grep -q "ENABLED"; then
            log_success "Table $table TTL enabled"
        else
            log_warning "Table $table TTL not enabled"
        fi
    done
}

# Validate IAM roles
validate_iam() {
    log_section "Validating IAM Roles and Policies"
    
    local roles=(
        "AuditFlowLambdaExecutionRole"
        "AuditFlowStepFunctionsRole"
        "AuditFlowAPIGatewayRole"
    )
    
    for role in "${roles[@]}"; do
        check "IAM role $role exists" "aws iam get-role --role-name $role"
    done
    
    # Check Lambda role policies
    check "Lambda role has S3 policy" "aws iam get-role-policy --role-name AuditFlowLambdaExecutionRole --policy-name S3DocumentAccess"
    check "Lambda role has DynamoDB policy" "aws iam get-role-policy --role-name AuditFlowLambdaExecutionRole --policy-name DynamoDBAccess"
    check "Lambda role has AI services policy" "aws iam get-role-policy --role-name AuditFlowLambdaExecutionRole --policy-name AIServicesAccess"
}

# Validate Lambda functions
validate_lambda() {
    log_section "Validating Lambda Functions"
    
    local functions=(
        "AuditFlow-Trigger"
        "AuditFlow-APIHandler"
        "AuditFlow-AuthLogger"
    )
    
    for function in "${functions[@]}"; do
        if check_warn "Lambda function $function exists" "aws lambda get-function --function-name $function --region $AWS_REGION"; then
            # Check function configuration
            MEMORY=$(aws lambda get-function-configuration --function-name $function --region $AWS_REGION --query 'MemorySize' --output text 2>/dev/null)
            TIMEOUT=$(aws lambda get-function-configuration --function-name $function --region $AWS_REGION --query 'Timeout' --output text 2>/dev/null)
            
            if [ "$VERBOSE" = true ]; then
                log_info "  Memory: ${MEMORY}MB, Timeout: ${TIMEOUT}s"
            fi
        fi
    done
}

# Validate Step Functions
validate_step_functions() {
    log_section "Validating Step Functions"
    
    STATE_MACHINE_ARN="arn:aws:states:${AWS_REGION}:${ACCOUNT_ID}:stateMachine:${STEP_FUNCTION_NAME}"
    
    check_warn "Step Functions state machine exists" "aws stepfunctions describe-state-machine --state-machine-arn $STATE_MACHINE_ARN --region $AWS_REGION"
}

# Validate API Gateway
validate_api_gateway() {
    log_section "Validating API Gateway"
    
    API_ID=$(aws apigateway get-rest-apis --region $AWS_REGION --query "items[?name=='${API_GATEWAY_NAME}'].id" --output text 2>/dev/null)
    
    if [ -n "$API_ID" ] && [ "$API_ID" != "None" ]; then
        log_success "API Gateway exists (ID: $API_ID)"
        
        # Check if deployed
        if aws apigateway get-stages --rest-api-id $API_ID --region $AWS_REGION &> /dev/null; then
            log_success "API Gateway has stages deployed"
        else
            log_warning "API Gateway not deployed to any stage"
        fi
    else
        log_warning "API Gateway not found"
    fi
}

# Validate Cognito
validate_cognito() {
    log_section "Validating Cognito"
    
    # Check User Pool
    USER_POOL_ID=$(aws cognito-idp list-user-pools --max-results 60 --region $AWS_REGION --query "UserPools[?Name=='${USER_POOL_NAME}'].Id" --output text 2>/dev/null)
    
    if [ -n "$USER_POOL_ID" ] && [ "$USER_POOL_ID" != "None" ]; then
        log_success "Cognito User Pool exists (ID: $USER_POOL_ID)"
        
        # Check MFA configuration
        MFA_CONFIG=$(aws cognito-idp describe-user-pool --user-pool-id $USER_POOL_ID --region $AWS_REGION --query 'UserPool.MfaConfiguration' --output text 2>/dev/null)
        if [ "$MFA_CONFIG" = "OPTIONAL" ] || [ "$MFA_CONFIG" = "ON" ]; then
            log_success "MFA configured: $MFA_CONFIG"
        else
            log_warning "MFA not configured"
        fi
    else
        log_warning "Cognito User Pool not found"
    fi
    
    # Check Identity Pool
    IDENTITY_POOL_ID=$(aws cognito-identity list-identity-pools --max-results 60 --region $AWS_REGION --query "IdentityPools[?IdentityPoolName=='${IDENTITY_POOL_NAME}'].IdentityPoolId" --output text 2>/dev/null)
    
    if [ -n "$IDENTITY_POOL_ID" ] && [ "$IDENTITY_POOL_ID" != "None" ]; then
        log_success "Cognito Identity Pool exists (ID: $IDENTITY_POOL_ID)"
    else
        log_warning "Cognito Identity Pool not found"
    fi
}

# Validate CloudWatch logs
validate_cloudwatch() {
    log_section "Validating CloudWatch Logs"
    
    local log_groups=(
        "/aws/lambda/AuditFlow-Trigger"
        "/aws/lambda/AuditFlow-APIHandler"
        "/aws/states/AuditFlowWorkflow"
    )
    
    for log_group in "${log_groups[@]}"; do
        check_warn "Log group $log_group exists" "aws logs describe-log-groups --log-group-name-prefix $log_group --region $AWS_REGION | grep -q $log_group"
    done
}

# Test connectivity
test_connectivity() {
    log_section "Testing Service Connectivity"
    
    log_info "Testing S3 access..."
    BUCKET_NAME="${S3_BUCKET_PREFIX}-${ACCOUNT_ID}"
    if aws s3 ls "s3://$BUCKET_NAME" --region $AWS_REGION &> /dev/null; then
        log_success "S3 bucket accessible"
    else
        log_error "Cannot access S3 bucket"
    fi
    
    log_info "Testing DynamoDB access..."
    if aws dynamodb scan --table-name AuditFlow-Documents --limit 1 --region $AWS_REGION &> /dev/null; then
        log_success "DynamoDB table accessible"
    else
        log_error "Cannot access DynamoDB table"
    fi
    
    log_info "Testing KMS access..."
    if aws kms describe-key --key-id alias/auditflow-s3-encryption --region $AWS_REGION &> /dev/null; then
        log_success "KMS key accessible"
    else
        log_error "Cannot access KMS key"
    fi
}

# Output resource identifiers
output_resources() {
    log_section "Resource Identifiers and Endpoints"
    
    echo "AWS Account ID: $ACCOUNT_ID"
    echo "Region: $AWS_REGION"
    echo "Environment: $ENVIRONMENT"
    echo ""
    
    echo "S3 Bucket:"
    echo "  Name: ${S3_BUCKET_PREFIX}-${ACCOUNT_ID}"
    echo "  URL: s3://${S3_BUCKET_PREFIX}-${ACCOUNT_ID}"
    echo ""
    
    echo "DynamoDB Tables:"
    echo "  - AuditFlow-Documents"
    echo "  - AuditFlow-AuditRecords"
    echo ""
    
    if [ -n "$USER_POOL_ID" ] && [ "$USER_POOL_ID" != "None" ]; then
        echo "Cognito User Pool:"
        echo "  ID: $USER_POOL_ID"
        echo "  Name: $USER_POOL_NAME"
        echo ""
    fi
    
    if [ -n "$IDENTITY_POOL_ID" ] && [ "$IDENTITY_POOL_ID" != "None" ]; then
        echo "Cognito Identity Pool:"
        echo "  ID: $IDENTITY_POOL_ID"
        echo "  Name: $IDENTITY_POOL_NAME"
        echo ""
    fi
    
    if [ -n "$API_ID" ] && [ "$API_ID" != "None" ]; then
        echo "API Gateway:"
        echo "  ID: $API_ID"
        echo "  Endpoint: https://${API_ID}.execute-api.${AWS_REGION}.amazonaws.com/${API_STAGE_NAME}"
        echo ""
    fi
    
    echo "IAM Roles:"
    echo "  - arn:aws:iam::${ACCOUNT_ID}:role/AuditFlowLambdaExecutionRole"
    echo "  - arn:aws:iam::${ACCOUNT_ID}:role/AuditFlowStepFunctionsRole"
    echo "  - arn:aws:iam::${ACCOUNT_ID}:role/AuditFlowAPIGatewayRole"
    echo ""
}

# Main validation
main() {
    log_section "AuditFlow-Pro Deployment Validation"
    log_info "Starting validation at $(date)"
    
    # Load configuration
    load_config
    
    # Run validations
    validate_aws
    validate_kms
    validate_s3
    validate_dynamodb
    validate_iam
    validate_lambda
    validate_step_functions
    validate_api_gateway
    validate_cognito
    validate_cloudwatch
    test_connectivity
    
    # Output resources
    output_resources
    
    # Summary
    log_section "Validation Summary"
    echo "Total Checks: $TOTAL_CHECKS"
    echo -e "${GREEN}Passed: $PASSED_CHECKS${NC}"
    echo -e "${YELLOW}Warnings: $WARNING_CHECKS${NC}"
    echo -e "${RED}Failed: $FAILED_CHECKS${NC}"
    echo ""
    
    if [ $FAILED_CHECKS -eq 0 ]; then
        log_success "All critical checks passed!"
        if [ $WARNING_CHECKS -gt 0 ]; then
            log_warning "Some optional features are not configured"
        fi
        echo ""
        echo "Deployment is ready for use!"
        exit 0
    else
        log_error "Some critical checks failed"
        echo ""
        echo "Please review the errors above and fix the issues."
        exit 1
    fi
}

# Run main validation
main

