#!/bin/bash
# verify-amplify-setup.sh
# Comprehensive AWS Amplify setup verification script
# Validates Task 22 requirements from tasks.md

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_DIR="$SCRIPT_DIR/config"

# Default values
ENVIRONMENT="${ENVIRONMENT:-dev}"
CONFIG_FILE="$CONFIG_DIR/${ENVIRONMENT}.env"
VERBOSE=false
SKIP_PERFORMANCE=false

# Counters
TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0
WARNING_CHECKS=0

# Usage information
usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Comprehensive AWS Amplify setup verification for AuditFlow-Pro.
Validates all requirements from Task 22 (tasks.md).

OPTIONS:
    -e, --environment ENV    Environment to validate (dev, staging, prod) [default: dev]
    -c, --config FILE        Path to configuration file [default: config/ENV.env]
    -v, --verbose            Enable verbose output
    -s, --skip-performance   Skip performance tests (faster validation)
    -h, --help               Show this help message

EXAMPLES:
    # Validate development environment
    $0 -e dev

    # Validate production with verbose output
    $0 -e prod -v

    # Quick validation (skip performance tests)
    $0 -e prod -s

REQUIREMENTS VALIDATED:
    Task 22.1: Amplify hosting configuration
    Task 22.2: Custom domain and HTTPS setup
    Task 22.3: Automatic deployments and CI/CD
    Task 22.4: Frontend performance optimization

    Requirement 15.1-15.7: Frontend hosting and deployment
    Requirement 16.2: TLS encryption in transit
    Requirement 19.7: Dashboard responsiveness

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
        -s|--skip-performance)
            SKIP_PERFORMANCE=true
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
    echo -e "${CYAN}========================================${NC}"
    echo -e "${CYAN}$1${NC}"
    echo -e "${CYAN}========================================${NC}"
}

log_subsection() {
    echo ""
    echo -e "${BLUE}--- $1 ---${NC}"
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

# Validate prerequisites
validate_prerequisites() {
    log_section "Validating Prerequisites"
    
    check "AWS CLI installed" "command -v aws"
    check "curl installed" "command -v curl"
    check "jq installed (for JSON parsing)" "command -v jq"
    check_warn "openssl installed (for TLS testing)" "command -v openssl"
    check_warn "dig installed (for DNS testing)" "command -v dig"
    
    # Validate AWS credentials
    if aws sts get-caller-identity &> /dev/null; then
        ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
        log_success "AWS credentials valid (Account: $ACCOUNT_ID)"
    else
        log_error "AWS credentials invalid or not configured"
        exit 1
    fi
}

# Task 22.1: Validate Amplify Hosting Configuration
validate_amplify_hosting() {
    log_section "Task 22.1: Amplify Hosting Configuration"
    
    log_subsection "Checking Amplify App"
    
    # Get Amplify app ID
    AMPLIFY_APP_ID=$(aws amplify list-apps --region $AWS_REGION --query "apps[?name=='${AMPLIFY_APP_NAME}'].appId" --output text 2>/dev/null)
    
    if [ -n "$AMPLIFY_APP_ID" ] && [ "$AMPLIFY_APP_ID" != "None" ]; then
        log_success "Amplify app exists (ID: $AMPLIFY_APP_ID)"
        
        # Get app details
        APP_DETAILS=$(aws amplify get-app --app-id $AMPLIFY_APP_ID --region $AWS_REGION 2>/dev/null)
        
        if [ $? -eq 0 ]; then
            # Check repository connection
            REPO_URL=$(echo "$APP_DETAILS" | jq -r '.app.repository' 2>/dev/null)
            if [ -n "$REPO_URL" ] && [ "$REPO_URL" != "null" ]; then
                log_success "Git repository connected: $REPO_URL"
            else
                log_error "Git repository not connected"
            fi
            
            # Check default domain
            DEFAULT_DOMAIN=$(echo "$APP_DETAILS" | jq -r '.app.defaultDomain' 2>/dev/null)
            if [ -n "$DEFAULT_DOMAIN" ] && [ "$DEFAULT_DOMAIN" != "null" ]; then
                log_success "Default Amplify domain: $DEFAULT_DOMAIN"
            fi
        fi
    else
        log_error "Amplify app not found: $AMPLIFY_APP_NAME"
        return 1
    fi
    
    log_subsection "Checking Build Settings"
    
    # Check if amplify.yml exists in repository
    if [ -f "$SCRIPT_DIR/../amplify.yml" ]; then
        log_success "amplify.yml found in repository root"
        
        # Validate amplify.yml structure
        if grep -q "appRoot: auditflow-pro/frontend" "$SCRIPT_DIR/../amplify.yml"; then
            log_success "Build configuration specifies correct appRoot"
        else
            log_warning "appRoot may not be correctly configured in amplify.yml"
        fi
    else
        log_error "amplify.yml not found in repository root"
    fi
    
    log_subsection "Checking Environment Variables"
    
    # Get environment variables from Amplify
    ENV_VARS=$(aws amplify get-app --app-id $AMPLIFY_APP_ID --region $AWS_REGION --query 'app.environmentVariables' --output json 2>/dev/null)
    
    if [ $? -eq 0 ]; then
        # Check required environment variables
        REQUIRED_VARS=("VITE_API_GATEWAY_URL" "VITE_AWS_REGION" "VITE_COGNITO_USER_POOL_ID" "VITE_COGNITO_CLIENT_ID" "VITE_S3_BUCKET_NAME")
        
        for VAR in "${REQUIRED_VARS[@]}"; do
            if echo "$ENV_VARS" | jq -e ".$VAR" &> /dev/null; then
                log_success "Environment variable configured: $VAR"
            else
                log_error "Missing environment variable: $VAR"
            fi
        done
    else
        log_warning "Could not retrieve environment variables"
    fi
    
    log_subsection "Checking Branch Configuration"
    
    # Get branch details
    BRANCH_DETAILS=$(aws amplify get-branch --app-id $AMPLIFY_APP_ID --branch-name main --region $AWS_REGION 2>/dev/null)
    
    if [ $? -eq 0 ]; then
        log_success "Main branch configured"
        
        # Check if auto-build is enabled
        AUTO_BUILD=$(echo "$BRANCH_DETAILS" | jq -r '.branch.enableAutoBuild' 2>/dev/null)
        if [ "$AUTO_BUILD" = "true" ]; then
            log_success "Automatic builds enabled"
        else
            log_warning "Automatic builds not enabled"
        fi
    else
        log_error "Main branch not found"
    fi
}

# Task 22.2: Validate Custom Domain and HTTPS
validate_custom_domain() {
    log_section "Task 22.2: Custom Domain and HTTPS Setup"
    
    log_subsection "Checking Domain Configuration"
    
    # Get domain associations
    DOMAIN_ASSOC=$(aws amplify list-domain-associations --app-id $AMPLIFY_APP_ID --region $AWS_REGION 2>/dev/null)
    
    if [ $? -eq 0 ]; then
        # Check if custom domain is configured
        CUSTOM_DOMAIN=$(echo "$DOMAIN_ASSOC" | jq -r ".domainAssociations[] | select(.domainName==\"${CUSTOM_DOMAIN_NAME}\") | .domainName" 2>/dev/null)
        
        if [ -n "$CUSTOM_DOMAIN" ] && [ "$CUSTOM_DOMAIN" != "null" ]; then
            log_success "Custom domain configured: $CUSTOM_DOMAIN"
            
            # Check domain status
            DOMAIN_STATUS=$(echo "$DOMAIN_ASSOC" | jq -r ".domainAssociations[] | select(.domainName==\"${CUSTOM_DOMAIN_NAME}\") | .domainStatus" 2>/dev/null)
            
            if [ "$DOMAIN_STATUS" = "AVAILABLE" ]; then
                log_success "Domain status: AVAILABLE"
            elif [ "$DOMAIN_STATUS" = "PENDING_VERIFICATION" ]; then
                log_warning "Domain status: PENDING_VERIFICATION (DNS propagation in progress)"
            else
                log_warning "Domain status: $DOMAIN_STATUS"
            fi
            
            # Check SSL certificate
            CERT_STATUS=$(echo "$DOMAIN_ASSOC" | jq -r ".domainAssociations[] | select(.domainName==\"${CUSTOM_DOMAIN_NAME}\") | .certificateVerificationDNSRecord" 2>/dev/null)
            if [ -n "$CERT_STATUS" ] && [ "$CERT_STATUS" != "null" ]; then
                log_success "SSL certificate configured"
            else
                log_warning "SSL certificate status unclear"
            fi
        else
            log_error "Custom domain not configured: $CUSTOM_DOMAIN_NAME"
        fi
    else
        log_error "Could not retrieve domain associations"
    fi
    
    log_subsection "Testing DNS Resolution"
    
    if command -v dig &> /dev/null; then
        # Test DNS resolution
        if dig +short "$CUSTOM_DOMAIN_NAME" | grep -q "."; then
            log_success "DNS resolves for $CUSTOM_DOMAIN_NAME"
            
            if [ "$VERBOSE" = true ]; then
                DNS_RESULT=$(dig +short "$CUSTOM_DOMAIN_NAME")
                log_info "DNS result: $DNS_RESULT"
            fi
        else
            log_warning "DNS not resolving for $CUSTOM_DOMAIN_NAME (may still be propagating)"
        fi
    else
        log_info "Skipping DNS test (dig not installed)"
    fi
    
    log_subsection "Testing HTTPS and TLS Configuration"
    
    # Test HTTPS access
    if curl -s -o /dev/null -w "%{http_code}" "https://$CUSTOM_DOMAIN_NAME" | grep -q "200\|301\|302"; then
        log_success "HTTPS endpoint accessible"
        
        # Check HTTP to HTTPS redirect
        HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "http://$CUSTOM_DOMAIN_NAME")
        if [ "$HTTP_CODE" = "301" ] || [ "$HTTP_CODE" = "302" ]; then
            log_success "HTTP redirects to HTTPS"
        else
            log_warning "HTTP redirect not configured (code: $HTTP_CODE)"
        fi
    else
        log_error "HTTPS endpoint not accessible"
    fi
    
    # Test TLS version
    if command -v openssl &> /dev/null; then
        # Test TLS 1.2
        if echo | openssl s_client -connect "$CUSTOM_DOMAIN_NAME:443" -tls1_2 2>&1 | grep -q "Protocol.*TLSv1.2"; then
            log_success "TLS 1.2 supported"
        else
            log_warning "TLS 1.2 support unclear"
        fi
        
        # Test TLS 1.3
        if echo | openssl s_client -connect "$CUSTOM_DOMAIN_NAME:443" -tls1_3 2>&1 | grep -q "Protocol.*TLSv1.3"; then
            log_success "TLS 1.3 supported"
        else
            log_info "TLS 1.3 not supported (TLS 1.2 is sufficient)"
        fi
    else
        log_info "Skipping TLS test (openssl not installed)"
    fi
    
    log_subsection "Checking Security Headers"
    
    # Get security headers
    HEADERS=$(curl -s -I "https://$CUSTOM_DOMAIN_NAME" 2>/dev/null)
    
    if [ $? -eq 0 ]; then
        # Check for security headers
        if echo "$HEADERS" | grep -qi "strict-transport-security"; then
            log_success "HSTS header present"
        else
            log_warning "HSTS header not found"
        fi
        
        if echo "$HEADERS" | grep -qi "x-frame-options"; then
            log_success "X-Frame-Options header present"
        else
            log_warning "X-Frame-Options header not found"
        fi
        
        if echo "$HEADERS" | grep -qi "x-content-type-options"; then
            log_success "X-Content-Type-Options header present"
        else
            log_warning "X-Content-Type-Options header not found"
        fi
    else
        log_warning "Could not retrieve security headers"
    fi
}

# Task 22.3: Validate Automatic Deployments
validate_automatic_deployments() {
    log_section "Task 22.3: Automatic Deployments and CI/CD"
    
    log_subsection "Checking Recent Deployments"
    
    # Get recent jobs
    RECENT_JOBS=$(aws amplify list-jobs --app-id $AMPLIFY_APP_ID --branch-name main --max-results 5 --region $AWS_REGION 2>/dev/null)
    
    if [ $? -eq 0 ]; then
        JOB_COUNT=$(echo "$RECENT_JOBS" | jq '.jobSummaries | length' 2>/dev/null)
        
        if [ "$JOB_COUNT" -gt 0 ]; then
            log_success "Found $JOB_COUNT recent deployment(s)"
            
            # Get latest job details
            LATEST_JOB=$(echo "$RECENT_JOBS" | jq -r '.jobSummaries[0]' 2>/dev/null)
            LATEST_STATUS=$(echo "$LATEST_JOB" | jq -r '.status' 2>/dev/null)
            LATEST_TYPE=$(echo "$LATEST_JOB" | jq -r '.jobType' 2>/dev/null)
            
            if [ "$LATEST_STATUS" = "SUCCEED" ]; then
                log_success "Latest deployment status: SUCCESS"
            elif [ "$LATEST_STATUS" = "PENDING" ] || [ "$LATEST_STATUS" = "RUNNING" ]; then
                log_info "Latest deployment status: IN PROGRESS"
            else
                log_warning "Latest deployment status: $LATEST_STATUS"
            fi
            
            # Check deployment time
            START_TIME=$(echo "$LATEST_JOB" | jq -r '.startTime' 2>/dev/null)
            END_TIME=$(echo "$LATEST_JOB" | jq -r '.endTime' 2>/dev/null)
            
            if [ -n "$START_TIME" ] && [ -n "$END_TIME" ] && [ "$START_TIME" != "null" ] && [ "$END_TIME" != "null" ]; then
                DURATION=$((END_TIME - START_TIME))
                DURATION_MIN=$((DURATION / 60))
                
                if [ "$VERBOSE" = true ]; then
                    log_info "Latest deployment duration: ${DURATION_MIN} minutes"
                fi
                
                if [ $DURATION_MIN -le 10 ]; then
                    log_success "Deployment completed within 10 minutes (Requirement 15.3)"
                else
                    log_warning "Deployment took ${DURATION_MIN} minutes (target: <10 minutes)"
                fi
            fi
        else
            log_warning "No recent deployments found"
        fi
    else
        log_error "Could not retrieve deployment history"
    fi
    
    log_subsection "Checking Build Configuration"
    
    # Check if auto-build is enabled
    if [ -n "$BRANCH_DETAILS" ]; then
        AUTO_BUILD=$(echo "$BRANCH_DETAILS" | jq -r '.branch.enableAutoBuild' 2>/dev/null)
        if [ "$AUTO_BUILD" = "true" ]; then
            log_success "Automatic builds enabled on push"
        else
            log_error "Automatic builds not enabled"
        fi
        
        # Check notification settings
        NOTIFICATIONS=$(echo "$BRANCH_DETAILS" | jq -r '.branch.enableNotification' 2>/dev/null)
        if [ "$NOTIFICATIONS" = "true" ]; then
            log_success "Build notifications enabled"
        else
            log_warning "Build notifications not enabled"
        fi
    fi
}

# Task 22.4: Validate Performance Optimization
validate_performance() {
    log_section "Task 22.4: Frontend Performance Optimization"
    
    if [ "$SKIP_PERFORMANCE" = true ]; then
        log_info "Skipping performance tests (--skip-performance flag set)"
        return 0
    fi
    
    log_subsection "Testing Page Load Time"
    
    # Measure page load time
    if command -v curl &> /dev/null; then
        log_info "Measuring page load time..."
        
        # Create temporary file for curl timing
        CURL_FORMAT=$(mktemp)
        cat > "$CURL_FORMAT" << 'EOF'
time_namelookup:  %{time_namelookup}s\n
time_connect:  %{time_connect}s\n
time_starttransfer:  %{time_starttransfer}s\n
time_total:  %{time_total}s\n
EOF
        
        # Measure load time
        TIMING=$(curl -w "@$CURL_FORMAT" -o /dev/null -s "https://$CUSTOM_DOMAIN_NAME" 2>&1)
        TOTAL_TIME=$(echo "$TIMING" | grep "time_total" | awk '{print $2}' | sed 's/s//')
        
        rm -f "$CURL_FORMAT"
        
        if [ -n "$TOTAL_TIME" ]; then
            # Convert to milliseconds for comparison
            TOTAL_TIME_MS=$(echo "$TOTAL_TIME * 1000" | bc 2>/dev/null || echo "0")
            
            if [ "$VERBOSE" = true ]; then
                log_info "Page load time: ${TOTAL_TIME}s"
            fi
            
            # Check if under 3 seconds (Requirement 15.7)
            if (( $(echo "$TOTAL_TIME < 3.0" | bc -l) )); then
                log_success "Page load time < 3 seconds (Requirement 15.7, 19.7)"
            else
                log_warning "Page load time ${TOTAL_TIME}s exceeds 3 second target"
            fi
        else
            log_warning "Could not measure page load time"
        fi
    fi
    
    log_subsection "Checking Caching Configuration"
    
    # Check cache headers
    CACHE_HEADERS=$(curl -s -I "https://$CUSTOM_DOMAIN_NAME" 2>/dev/null)
    
    if [ $? -eq 0 ]; then
        if echo "$CACHE_HEADERS" | grep -qi "cache-control"; then
            log_success "Cache-Control headers present"
            
            if [ "$VERBOSE" = true ]; then
                CACHE_VALUE=$(echo "$CACHE_HEADERS" | grep -i "cache-control" | head -1)
                log_info "$CACHE_VALUE"
            fi
        else
            log_warning "Cache-Control headers not found"
        fi
    fi
    
    log_subsection "Checking Code Splitting"
    
    # Check if frontend uses code splitting (look for multiple JS chunks)
    if [ -d "$SCRIPT_DIR/frontend/dist/assets" ]; then
        JS_FILES=$(find "$SCRIPT_DIR/frontend/dist/assets" -name "*.js" 2>/dev/null | wc -l)
        
        if [ "$JS_FILES" -gt 1 ]; then
            log_success "Code splitting detected ($JS_FILES JS files)"
        else
            log_warning "Code splitting may not be configured"
        fi
    else
        log_info "Cannot check code splitting (dist folder not found locally)"
    fi
}

# Additional validation: Frontend functionality
validate_frontend_functionality() {
    log_section "Additional: Frontend Functionality Tests"
    
    log_subsection "Testing API Endpoints"
    
    # Test if frontend can reach API Gateway
    if [ -n "$VITE_API_GATEWAY_URL" ]; then
        API_URL="$VITE_API_GATEWAY_URL"
    elif [ -n "$API_GATEWAY_URL" ]; then
        API_URL="$API_GATEWAY_URL"
    else
        log_warning "API Gateway URL not configured"
        return 0
    fi
    
    # Test API health endpoint (if exists)
    if curl -s -o /dev/null -w "%{http_code}" "$API_URL/health" | grep -q "200"; then
        log_success "API Gateway health check passed"
    else
        log_info "API Gateway health endpoint not accessible (may require authentication)"
    fi
    
    log_subsection "Testing Authentication Integration"
    
    # Check if Cognito User Pool is accessible
    if [ -n "$VITE_COGNITO_USER_POOL_ID" ]; then
        USER_POOL_ID="$VITE_COGNITO_USER_POOL_ID"
    elif [ -n "$USER_POOL_ID" ]; then
        USER_POOL_ID="$USER_POOL_ID"
    else
        log_warning "Cognito User Pool ID not configured"
        return 0
    fi
    
    if aws cognito-idp describe-user-pool --user-pool-id "$USER_POOL_ID" --region $AWS_REGION &> /dev/null; then
        log_success "Cognito User Pool accessible"
    else
        log_warning "Cannot access Cognito User Pool"
    fi
}

# Output resource summary
output_resource_summary() {
    log_section "Resource Summary"
    
    echo "Environment: $ENVIRONMENT"
    echo "AWS Region: $AWS_REGION"
    echo "AWS Account: $ACCOUNT_ID"
    echo ""
    
    if [ -n "$AMPLIFY_APP_ID" ]; then
        echo "Amplify App:"
        echo "  Name: $AMPLIFY_APP_NAME"
        echo "  ID: $AMPLIFY_APP_ID"
        echo "  Default Domain: $DEFAULT_DOMAIN"
        echo ""
    fi
    
    if [ -n "$CUSTOM_DOMAIN" ]; then
        echo "Custom Domain:"
        echo "  Domain: $CUSTOM_DOMAIN_NAME"
        echo "  Status: $DOMAIN_STATUS"
        echo "  URL: https://$CUSTOM_DOMAIN_NAME"
        echo ""
    fi
    
    echo "Configuration:"
    echo "  API Gateway: ${VITE_API_GATEWAY_URL:-Not configured}"
    echo "  Cognito Pool: ${VITE_COGNITO_USER_POOL_ID:-Not configured}"
    echo "  S3 Bucket: ${VITE_S3_BUCKET_NAME:-Not configured}"
    echo ""
}

# Generate detailed report
generate_report() {
    log_section "Detailed Verification Report"
    
    echo "Task 22.1: Amplify Hosting Configuration"
    echo "  ✓ Requirements: 15.1, 15.2"
    echo "  Status: $([ $FAILED_CHECKS -eq 0 ] && echo "PASS" || echo "REVIEW NEEDED")"
    echo ""
    
    echo "Task 22.2: Custom Domain and HTTPS"
    echo "  ✓ Requirements: 15.4, 15.5, 16.2"
    echo "  Status: $([ $FAILED_CHECKS -eq 0 ] && echo "PASS" || echo "REVIEW NEEDED")"
    echo ""
    
    echo "Task 22.3: Automatic Deployments"
    echo "  ✓ Requirements: 15.2, 15.3, 15.6"
    echo "  Status: $([ $FAILED_CHECKS -eq 0 ] && echo "PASS" || echo "REVIEW NEEDED")"
    echo ""
    
    echo "Task 22.4: Performance Optimization"
    echo "  ✓ Requirements: 15.7, 19.7"
    echo "  Status: $([ $FAILED_CHECKS -eq 0 ] && echo "PASS" || echo "REVIEW NEEDED")"
    echo ""
}

# Main validation
main() {
    log_section "AuditFlow-Pro Amplify Setup Verification"
    log_info "Starting verification at $(date)"
    log_info "Environment: $ENVIRONMENT"
    echo ""
    
    # Load configuration
    load_config
    
    # Run validations
    validate_prerequisites
    validate_amplify_hosting
    validate_custom_domain
    validate_automatic_deployments
    validate_performance
    validate_frontend_functionality
    
    # Output summary
    output_resource_summary
    generate_report
    
    # Final summary
    log_section "Validation Summary"
    echo "Total Checks: $TOTAL_CHECKS"
    echo -e "${GREEN}Passed: $PASSED_CHECKS${NC}"
    echo -e "${YELLOW}Warnings: $WARNING_CHECKS${NC}"
    echo -e "${RED}Failed: $FAILED_CHECKS${NC}"
    echo ""
    
    # Calculate success rate
    if [ $TOTAL_CHECKS -gt 0 ]; then
        SUCCESS_RATE=$((PASSED_CHECKS * 100 / TOTAL_CHECKS))
        echo "Success Rate: ${SUCCESS_RATE}%"
        echo ""
    fi
    
    # Final verdict
    if [ $FAILED_CHECKS -eq 0 ]; then
        log_success "All critical checks passed!"
        if [ $WARNING_CHECKS -gt 0 ]; then
            log_warning "Some optional features need attention"
            echo ""
            echo "Next steps:"
            echo "1. Review warnings above"
            echo "2. Configure optional features if needed"
            echo "3. Run end-to-end tests (Task 22.5)"
        fi
        echo ""
        echo "✓ Amplify setup is ready for production!"
        exit 0
    else
        log_error "Some critical checks failed"
        echo ""
        echo "Action required:"
        echo "1. Review failed checks above"
        echo "2. Fix configuration issues"
        echo "3. Re-run this script to verify fixes"
        echo ""
        echo "For help, see: $SCRIPT_DIR/AMPLIFY_DEPLOYMENT.md"
        exit 1
    fi
}

# Run main validation
main
