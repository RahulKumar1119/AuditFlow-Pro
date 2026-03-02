#!/bin/bash
# validate-config.sh
# Validates environment configuration files before deployment

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

# Validation counters
TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0
WARNING_CHECKS=0

# Usage information
usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Validates environment configuration files before deployment.

OPTIONS:
    -e, --environment ENV    Environment to validate (dev, staging, prod) [default: dev]
    -c, --config FILE        Path to configuration file [default: config/ENV.env]
    -h, --help               Show this help message

EXAMPLES:
    # Validate development configuration
    $0 -e dev

    # Validate custom configuration file
    $0 -c /path/to/custom.env

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

# Validation function
validate_required() {
    local var_name=$1
    local var_value=$2
    local description=$3
    
    ((TOTAL_CHECKS++))
    
    if [ -z "$var_value" ]; then
        log_error "$description is required but not set ($var_name)"
        return 1
    else
        log_success "$description is set: $var_value"
        return 0
    fi
}

# Validation with pattern
validate_pattern() {
    local var_name=$1
    local var_value=$2
    local pattern=$3
    local description=$4
    
    ((TOTAL_CHECKS++))
    
    if [ -z "$var_value" ]; then
        log_error "$description is required but not set ($var_name)"
        return 1
    fi
    
    if [[ ! "$var_value" =~ $pattern ]]; then
        log_error "$description has invalid format: $var_value (expected pattern: $pattern)"
        return 1
    else
        log_success "$description is valid: $var_value"
        return 0
    fi
}

# Validation with range
validate_range() {
    local var_name=$1
    local var_value=$2
    local min=$3
    local max=$4
    local description=$5
    
    ((TOTAL_CHECKS++))
    
    if [ -z "$var_value" ]; then
        log_error "$description is required but not set ($var_name)"
        return 1
    fi
    
    if [ "$var_value" -lt "$min" ] || [ "$var_value" -gt "$max" ]; then
        log_error "$description is out of range: $var_value (expected: $min-$max)"
        return 1
    else
        log_success "$description is valid: $var_value"
        return 0
    fi
}

# Validation with enum
validate_enum() {
    local var_name=$1
    local var_value=$2
    local description=$3
    shift 3
    local valid_values=("$@")
    
    ((TOTAL_CHECKS++))
    
    if [ -z "$var_value" ]; then
        log_error "$description is required but not set ($var_name)"
        return 1
    fi
    
    for valid in "${valid_values[@]}"; do
        if [ "$var_value" = "$valid" ]; then
            log_success "$description is valid: $var_value"
            return 0
        fi
    done
    
    log_error "$description has invalid value: $var_value (expected one of: ${valid_values[*]})"
    return 1
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
    
    log_success "Configuration file loaded"
}

# Validate basic settings
validate_basic() {
    log_section "Validating Basic Settings"
    
    validate_enum "ENVIRONMENT" "$ENVIRONMENT" "Environment" "dev" "staging" "prod"
    validate_pattern "AWS_REGION" "$AWS_REGION" "^[a-z]{2}-[a-z]+-[0-9]$" "AWS Region"
    validate_required "PROJECT_NAME" "$PROJECT_NAME" "Project Name"
    validate_required "STACK_NAME" "$STACK_NAME" "Stack Name"
}

# Validate S3 configuration
validate_s3() {
    log_section "Validating S3 Configuration"
    
    validate_required "S3_BUCKET_PREFIX" "$S3_BUCKET_PREFIX" "S3 Bucket Prefix"
    validate_enum "ENABLE_S3_VERSIONING" "$ENABLE_S3_VERSIONING" "S3 Versioning" "true" "false"
    validate_range "S3_LIFECYCLE_GLACIER_DAYS" "$S3_LIFECYCLE_GLACIER_DAYS" 1 365 "Glacier Transition Days"
    validate_range "S3_LIFECYCLE_EXPIRATION_DAYS" "$S3_LIFECYCLE_EXPIRATION_DAYS" 365 3650 "Expiration Days"
}

# Validate DynamoDB configuration
validate_dynamodb() {
    log_section "Validating DynamoDB Configuration"
    
    validate_enum "DYNAMODB_BILLING_MODE" "$DYNAMODB_BILLING_MODE" "DynamoDB Billing Mode" "PAY_PER_REQUEST" "PROVISIONED"
    validate_enum "ENABLE_POINT_IN_TIME_RECOVERY" "$ENABLE_POINT_IN_TIME_RECOVERY" "Point-in-Time Recovery" "true" "false"
    validate_required "TTL_ATTRIBUTE_NAME" "$TTL_ATTRIBUTE_NAME" "TTL Attribute Name"
}

# Validate Lambda configuration
validate_lambda() {
    log_section "Validating Lambda Configuration"
    
    validate_range "LAMBDA_MEMORY_SIZE" "$LAMBDA_MEMORY_SIZE" 128 10240 "Lambda Memory Size (MB)"
    validate_range "LAMBDA_TIMEOUT" "$LAMBDA_TIMEOUT" 3 900 "Lambda Timeout (seconds)"
    validate_pattern "LAMBDA_RUNTIME" "$LAMBDA_RUNTIME" "^python3\.[0-9]+$" "Lambda Runtime"
    validate_range "MAX_CONCURRENT_EXECUTIONS" "$MAX_CONCURRENT_EXECUTIONS" 1 1000 "Max Concurrent Executions"
}

# Validate Step Functions configuration
validate_step_functions() {
    log_section "Validating Step Functions Configuration"
    
    validate_required "STEP_FUNCTION_NAME" "$STEP_FUNCTION_NAME" "Step Function Name"
}

# Validate API Gateway configuration
validate_api_gateway() {
    log_section "Validating API Gateway Configuration"
    
    validate_required "API_GATEWAY_NAME" "$API_GATEWAY_NAME" "API Gateway Name"
    validate_required "API_STAGE_NAME" "$API_STAGE_NAME" "API Stage Name"
}

# Validate Cognito configuration
validate_cognito() {
    log_section "Validating Cognito Configuration"
    
    validate_required "USER_POOL_NAME" "$USER_POOL_NAME" "User Pool Name"
    validate_required "IDENTITY_POOL_NAME" "$IDENTITY_POOL_NAME" "Identity Pool Name"
    validate_range "SESSION_TIMEOUT_MINUTES" "$SESSION_TIMEOUT_MINUTES" 5 1440 "Session Timeout (minutes)"
    validate_enum "MFA_REQUIRED" "$MFA_REQUIRED" "MFA Required" "true" "false"
    validate_range "ACCOUNT_LOCKOUT_ATTEMPTS" "$ACCOUNT_LOCKOUT_ATTEMPTS" 1 10 "Account Lockout Attempts"
    validate_range "ACCOUNT_LOCKOUT_DURATION_MINUTES" "$ACCOUNT_LOCKOUT_DURATION_MINUTES" 1 60 "Account Lockout Duration (minutes)"
}

# Validate security configuration
validate_security() {
    log_section "Validating Security Configuration"
    
    validate_enum "ENABLE_KMS_ENCRYPTION" "$ENABLE_KMS_ENCRYPTION" "KMS Encryption" "true" "false"
    validate_enum "KMS_KEY_ROTATION_ENABLED" "$KMS_KEY_ROTATION_ENABLED" "KMS Key Rotation" "true" "false"
    validate_enum "TLS_MINIMUM_VERSION" "$TLS_MINIMUM_VERSION" "TLS Minimum Version" "TLS_1_2" "TLS_1_3"
}

# Validate monitoring configuration
validate_monitoring() {
    log_section "Validating Monitoring Configuration"
    
    validate_range "LOG_RETENTION_DAYS" "$LOG_RETENTION_DAYS" 1 3653 "Log Retention Days"
    validate_enum "ENABLE_CLOUDWATCH_ALARMS" "$ENABLE_CLOUDWATCH_ALARMS" "CloudWatch Alarms" "true" "false"
    
    ((TOTAL_CHECKS++))
    if [ -n "$ALERT_EMAIL" ]; then
        if [[ "$ALERT_EMAIL" =~ ^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$ ]]; then
            log_success "Alert Email is valid: $ALERT_EMAIL"
        else
            log_error "Alert Email has invalid format: $ALERT_EMAIL"
        fi
    else
        log_warning "Alert Email is not set (optional)"
    fi
}

# Validate performance configuration
validate_performance() {
    log_section "Validating Performance Configuration"
    
    ((TOTAL_CHECKS++))
    if [ -n "$CONFIDENCE_THRESHOLD" ]; then
        if (( $(echo "$CONFIDENCE_THRESHOLD >= 0.0 && $CONFIDENCE_THRESHOLD <= 1.0" | bc -l) )); then
            log_success "Confidence Threshold is valid: $CONFIDENCE_THRESHOLD"
        else
            log_error "Confidence Threshold is out of range: $CONFIDENCE_THRESHOLD (expected: 0.0-1.0)"
        fi
    else
        log_error "Confidence Threshold is required but not set"
    fi
    
    validate_range "PROCESSING_TIMEOUT_SECONDS" "$PROCESSING_TIMEOUT_SECONDS" 30 900 "Processing Timeout (seconds)"
    validate_range "RISK_SCORE_HIGH_THRESHOLD" "$RISK_SCORE_HIGH_THRESHOLD" 0 100 "Risk Score High Threshold"
    validate_range "RISK_SCORE_CRITICAL_THRESHOLD" "$RISK_SCORE_CRITICAL_THRESHOLD" 0 100 "Risk Score Critical Threshold"
    validate_range "MAX_FILE_SIZE_MB" "$MAX_FILE_SIZE_MB" 1 100 "Max File Size (MB)"
    
    # Validate threshold ordering
    ((TOTAL_CHECKS++))
    if [ "$RISK_SCORE_CRITICAL_THRESHOLD" -le "$RISK_SCORE_HIGH_THRESHOLD" ]; then
        log_error "Critical threshold ($RISK_SCORE_CRITICAL_THRESHOLD) must be greater than high threshold ($RISK_SCORE_HIGH_THRESHOLD)"
    else
        log_success "Risk score thresholds are properly ordered"
    fi
}

# Validate tags
validate_tags() {
    log_section "Validating Tags"
    
    validate_required "TAG_ENVIRONMENT" "$TAG_ENVIRONMENT" "Environment Tag"
    validate_required "TAG_PROJECT" "$TAG_PROJECT" "Project Tag"
    validate_required "TAG_MANAGED_BY" "$TAG_MANAGED_BY" "Managed By Tag"
}

# Environment-specific validations
validate_environment_specific() {
    log_section "Validating Environment-Specific Settings"
    
    if [ "$ENVIRONMENT" = "prod" ]; then
        ((TOTAL_CHECKS++))
        if [ "$MFA_REQUIRED" != "true" ]; then
            log_warning "MFA should be enabled for production environment"
        else
            log_success "MFA is enabled for production"
        fi
        
        ((TOTAL_CHECKS++))
        if [ "$ENABLE_POINT_IN_TIME_RECOVERY" != "true" ]; then
            log_warning "Point-in-Time Recovery should be enabled for production"
        else
            log_success "Point-in-Time Recovery is enabled for production"
        fi
        
        ((TOTAL_CHECKS++))
        if [ "$LOG_RETENTION_DAYS" -lt 365 ]; then
            log_warning "Log retention should be at least 365 days for production (current: $LOG_RETENTION_DAYS)"
        else
            log_success "Log retention is appropriate for production"
        fi
    fi
    
    if [ "$ENVIRONMENT" = "dev" ]; then
        ((TOTAL_CHECKS++))
        if [ "$LAMBDA_MEMORY_SIZE" -gt 1024 ]; then
            log_warning "Lambda memory size is high for development environment (consider reducing for cost savings)"
        else
            log_success "Lambda memory size is appropriate for development"
        fi
    fi
}

# Main validation
main() {
    log_section "AuditFlow-Pro Configuration Validation"
    log_info "Starting validation at $(date)"
    
    # Load configuration
    load_config
    
    # Run validations
    validate_basic
    validate_s3
    validate_dynamodb
    validate_lambda
    validate_step_functions
    validate_api_gateway
    validate_cognito
    validate_security
    validate_monitoring
    validate_performance
    validate_tags
    validate_environment_specific
    
    # Summary
    log_section "Validation Summary"
    echo "Configuration File: $CONFIG_FILE"
    echo "Environment: $ENVIRONMENT"
    echo ""
    echo "Total Checks: $TOTAL_CHECKS"
    echo -e "${GREEN}Passed: $PASSED_CHECKS${NC}"
    echo -e "${YELLOW}Warnings: $WARNING_CHECKS${NC}"
    echo -e "${RED}Failed: $FAILED_CHECKS${NC}"
    echo ""
    
    if [ $FAILED_CHECKS -eq 0 ]; then
        log_success "Configuration validation passed!"
        if [ $WARNING_CHECKS -gt 0 ]; then
            log_warning "Some warnings were found - review them before deployment"
        fi
        echo ""
        echo "Configuration is ready for deployment!"
        exit 0
    else
        log_error "Configuration validation failed"
        echo ""
        echo "Please fix the errors above before deployment."
        exit 1
    fi
}

# Run main validation
main

