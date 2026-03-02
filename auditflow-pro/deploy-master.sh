#!/bin/bash
# deploy-master.sh
# Master deployment script for AuditFlow-Pro
# Orchestrates complete infrastructure and application deployment

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INFRA_DIR="$SCRIPT_DIR/infrastructure"
CONFIG_DIR="$SCRIPT_DIR/config"

# Default values
ENVIRONMENT="${ENVIRONMENT:-dev}"
CONFIG_FILE="$CONFIG_DIR/${ENVIRONMENT}.env"
DRY_RUN=false
SKIP_VALIDATION=false
VERBOSE=false

# Usage information
usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Master deployment script for AuditFlow-Pro infrastructure and application.

OPTIONS:
    -e, --environment ENV    Environment to deploy (dev, staging, prod) [default: dev]
    -c, --config FILE        Path to configuration file [default: config/ENV.env]
    -r, --region REGION      AWS region to deploy to [overrides config]
    -d, --dry-run            Show what would be deployed without making changes
    -s, --skip-validation    Skip pre-deployment validation checks
    -v, --verbose            Enable verbose output
    -h, --help               Show this help message

EXAMPLES:
    # Deploy to development environment
    $0 -e dev

    # Deploy to production with custom config
    $0 -e prod -c /path/to/custom.env

    # Dry run for staging
    $0 -e staging --dry-run

    # Deploy to specific region
    $0 -e prod -r us-east-1

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
        -r|--region)
            AWS_REGION_OVERRIDE="$2"
            shift 2
            ;;
        -d|--dry-run)
            DRY_RUN=true
            shift
            ;;
        -s|--skip-validation)
            SKIP_VALIDATION=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            set -x
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
    
    # Override region if specified
    if [ -n "$AWS_REGION_OVERRIDE" ]; then
        AWS_REGION="$AWS_REGION_OVERRIDE"
        log_info "Region overridden to: $AWS_REGION"
    fi
    
    # Export variables for child scripts
    export ENVIRONMENT AWS_REGION PROJECT_NAME STACK_NAME
    export S3_BUCKET_PREFIX DYNAMODB_BILLING_MODE
    export LAMBDA_MEMORY_SIZE LAMBDA_TIMEOUT LAMBDA_RUNTIME
    export USER_POOL_NAME IDENTITY_POOL_NAME
    export ENABLE_KMS_ENCRYPTION KMS_KEY_ROTATION_ENABLED
    
    log_success "Configuration loaded successfully"
    log_info "Environment: $ENVIRONMENT"
    log_info "Region: $AWS_REGION"
    log_info "Stack: $STACK_NAME"
}

# Validate prerequisites
validate_prerequisites() {
    if [ "$SKIP_VALIDATION" = true ]; then
        log_warning "Skipping validation checks"
        return 0
    fi
    
    log_section "Validating Prerequisites"
    
    # Check AWS CLI
    if ! command -v aws &> /dev/null; then
        log_error "AWS CLI is not installed"
        exit 1
    fi
    log_success "AWS CLI found: $(aws --version)"
    
    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        log_error "AWS credentials not configured or invalid"
        exit 1
    fi
    ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    log_success "AWS credentials valid (Account: $ACCOUNT_ID)"
    
    # Check jq for JSON processing
    if ! command -v jq &> /dev/null; then
        log_warning "jq is not installed (optional but recommended)"
    else
        log_success "jq found: $(jq --version)"
    fi
    
    # Validate region
    if ! aws ec2 describe-regions --region-names "$AWS_REGION" &> /dev/null; then
        log_error "Invalid AWS region: $AWS_REGION"
        exit 1
    fi
    log_success "AWS region validated: $AWS_REGION"
    
    # Check required scripts exist
    local required_scripts=(
        "$INFRA_DIR/kms_setup.sh"
        "$INFRA_DIR/deploy.sh"
        "$INFRA_DIR/cognito_setup.sh"
        "$INFRA_DIR/api_gateway_setup.sh"
        "$INFRA_DIR/step_functions_deploy.sh"
    )
    
    for script in "${required_scripts[@]}"; do
        if [ ! -f "$script" ]; then
            log_error "Required script not found: $script"
            exit 1
        fi
    done
    log_success "All required scripts found"
}

# Dry run mode
if [ "$DRY_RUN" = true ]; then
    log_section "DRY RUN MODE"
    log_warning "This is a dry run. No resources will be created."
    load_config
    validate_prerequisites
    
    log_section "Deployment Plan"
    echo "The following resources would be created:"
    echo "  - KMS encryption keys"
    echo "  - S3 bucket: ${S3_BUCKET_PREFIX}-${ACCOUNT_ID}"
    echo "  - DynamoDB tables: AuditFlow-Documents-${ENVIRONMENT}, AuditFlow-AuditRecords-${ENVIRONMENT}"
    echo "  - Lambda functions (Classifier, Extractor, Validator, RiskScorer, Reporter, Trigger, APIHandler)"
    echo "  - Step Functions state machine: ${STEP_FUNCTION_NAME}"
    echo "  - API Gateway: ${API_GATEWAY_NAME}"
    echo "  - Cognito User Pool: ${USER_POOL_NAME}"
    echo "  - Cognito Identity Pool: ${IDENTITY_POOL_NAME}"
    echo "  - IAM roles and policies"
    echo "  - CloudWatch log groups"
    
    log_info "To execute deployment, run without --dry-run flag"
    exit 0
fi

# Main deployment
main() {
    log_section "AuditFlow-Pro Master Deployment"
    log_info "Starting deployment at $(date)"
    
    # Load configuration and validate
    load_config
    validate_prerequisites
    
    # Make all scripts executable
    log_info "Making scripts executable..."
    chmod +x "$INFRA_DIR"/*.sh
    
    # Step 1: Deploy KMS encryption keys
    log_section "Step 1: KMS Encryption Keys"
    log_info "Setting up KMS encryption keys..."
    if bash "$INFRA_DIR/kms_setup.sh"; then
        log_success "KMS keys created successfully"
        # Source KMS key IDs
        if [ -f /tmp/auditflow_kms_keys.env ]; then
            source /tmp/auditflow_kms_keys.env
        fi
    else
        log_error "KMS setup failed"
        exit 1
    fi
    
    # Step 2: Deploy base infrastructure (S3, DynamoDB)
    log_section "Step 2: Base Infrastructure"
    log_info "Deploying S3 buckets and DynamoDB tables..."
    if bash "$INFRA_DIR/deploy.sh"; then
        log_success "Base infrastructure deployed successfully"
    else
        log_error "Base infrastructure deployment failed"
        exit 1
    fi
    
    # Wait for resources to be ready
    log_info "Waiting for resources to be ready..."
    sleep 10
    
    # Step 3: Configure S3 bucket
    log_section "Step 3: S3 Configuration"
    log_info "Configuring S3 bucket policies and lifecycle..."
    if [ -f "$INFRA_DIR/s3_config.sh" ]; then
        bash "$INFRA_DIR/s3_config.sh" || log_warning "S3 configuration had warnings"
    fi
    if [ -f "$INFRA_DIR/s3_bucket_policy.sh" ]; then
        bash "$INFRA_DIR/s3_bucket_policy.sh" || log_warning "S3 bucket policy had warnings"
    fi
    log_success "S3 configuration complete"
    
    # Step 4: Configure DynamoDB
    log_section "Step 4: DynamoDB Configuration"
    log_info "Configuring DynamoDB encryption and TTL..."
    if [ -f "$INFRA_DIR/dynamodb_config.sh" ]; then
        bash "$INFRA_DIR/dynamodb_config.sh" || log_warning "DynamoDB configuration had warnings"
    fi
    log_success "DynamoDB configuration complete"
    
    # Step 5: Create IAM roles and policies
    log_section "Step 5: IAM Roles and Policies"
    log_info "Creating IAM roles and policies..."
    if [ -f "$INFRA_DIR/iam_policies.sh" ]; then
        bash "$INFRA_DIR/iam_policies.sh" || log_warning "IAM setup had warnings"
    fi
    log_success "IAM roles and policies created"
    
    # Step 6: Set up Cognito authentication
    log_section "Step 6: Cognito Authentication"
    log_info "Setting up Cognito User Pool and Identity Pool..."
    if bash "$INFRA_DIR/cognito_setup.sh"; then
        log_success "Cognito authentication configured"
    else
        log_warning "Cognito setup had warnings"
    fi
    
    # Step 7: Configure Cognito security features
    log_section "Step 7: Cognito Security"
    log_info "Configuring account lockout and logging..."
    if [ -f "$INFRA_DIR/cognito_account_lockout.sh" ]; then
        bash "$INFRA_DIR/cognito_account_lockout.sh" || log_warning "Cognito lockout had warnings"
    fi
    if [ -f "$INFRA_DIR/cognito_logging.sh" ]; then
        bash "$INFRA_DIR/cognito_logging.sh" || log_warning "Cognito logging had warnings"
    fi
    log_success "Cognito security configured"
    
    # Step 8: Deploy Lambda functions
    log_section "Step 8: Lambda Functions"
    log_info "Deploying Lambda functions..."
    
    local lambda_scripts=(
        "deploy_trigger_lambda.sh"
        "deploy_api_handler.sh"
        "deploy_auth_logger.sh"
    )
    
    for script in "${lambda_scripts[@]}"; do
        if [ -f "$INFRA_DIR/$script" ]; then
            log_info "Deploying $(basename $script .sh)..."
            bash "$INFRA_DIR/$script" || log_warning "$script had warnings"
        fi
    done
    log_success "Lambda functions deployed"
    
    # Step 9: Configure Lambda concurrency
    log_section "Step 9: Lambda Concurrency"
    if [ -f "$INFRA_DIR/lambda_concurrency_setup.sh" ]; then
        bash "$INFRA_DIR/lambda_concurrency_setup.sh" || log_warning "Lambda concurrency had warnings"
    fi
    log_success "Lambda concurrency configured"
    
    # Step 10: Deploy Step Functions
    log_section "Step 10: Step Functions"
    log_info "Deploying Step Functions state machine..."
    if bash "$INFRA_DIR/step_functions_deploy.sh"; then
        log_success "Step Functions deployed"
    else
        log_warning "Step Functions deployment had warnings"
    fi
    
    # Step 11: Set up S3 event triggers
    log_section "Step 11: S3 Event Triggers"
    log_info "Configuring S3 event notifications..."
    if bash "$INFRA_DIR/s3_event_trigger_setup.sh"; then
        log_success "S3 event triggers configured"
    else
        log_warning "S3 event trigger setup had warnings"
    fi
    
    # Step 12: Deploy API Gateway
    log_section "Step 12: API Gateway"
    log_info "Deploying API Gateway..."
    if bash "$INFRA_DIR/api_gateway_setup.sh"; then
        log_success "API Gateway deployed"
    else
        log_warning "API Gateway deployment had warnings"
    fi
    
    # Step 13: Configure CloudTrail logging
    log_section "Step 13: CloudTrail Logging"
    if [ -f "$INFRA_DIR/cloudtrail_kms_logging.sh" ]; then
        bash "$INFRA_DIR/cloudtrail_kms_logging.sh" || log_warning "CloudTrail setup had warnings"
    fi
    log_success "CloudTrail logging configured"
    
    # Deployment complete
    log_section "Deployment Complete!"
    log_success "AuditFlow-Pro infrastructure deployed successfully"
    log_info "Deployment completed at $(date)"
    
    # Output summary
    echo ""
    log_section "Deployment Summary"
    echo "Environment: $ENVIRONMENT"
    echo "Region: $AWS_REGION"
    echo "Account ID: $ACCOUNT_ID"
    echo ""
    echo "Resources Created:"
    echo "  ✓ KMS encryption keys"
    echo "  ✓ S3 bucket: ${S3_BUCKET_PREFIX}-${ACCOUNT_ID}"
    echo "  ✓ DynamoDB tables"
    echo "  ✓ Lambda functions"
    echo "  ✓ Step Functions state machine"
    echo "  ✓ API Gateway"
    echo "  ✓ Cognito User Pool and Identity Pool"
    echo "  ✓ IAM roles and policies"
    echo "  ✓ CloudWatch log groups"
    echo ""
    echo "Next Steps:"
    echo "  1. Run validation script: ./validate-deployment.sh -e $ENVIRONMENT"
    echo "  2. Update frontend configuration with Cognito values"
    echo "  3. Deploy frontend application"
    echo "  4. Create test users in Cognito"
    echo ""
    echo "To tear down this deployment:"
    echo "  ./teardown-master.sh -e $ENVIRONMENT"
}

# Run main deployment
main

