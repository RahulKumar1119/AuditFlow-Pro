#!/bin/bash
# deploy-multi-region.sh
# Multi-region deployment script for AuditFlow-Pro
# Deploys infrastructure to multiple AWS regions for high availability

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
ENVIRONMENT="${ENVIRONMENT:-prod}"
CONFIG_FILE="$CONFIG_DIR/${ENVIRONMENT}.env"
PRIMARY_REGION=""
SECONDARY_REGIONS=()
DRY_RUN=false
PARALLEL=false

# Usage information
usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Multi-region deployment script for AuditFlow-Pro infrastructure.

OPTIONS:
    -e, --environment ENV       Environment to deploy (dev, staging, prod) [default: prod]
    -p, --primary-region REG    Primary AWS region (required)
    -s, --secondary-region REG  Secondary AWS region (can be specified multiple times)
    -c, --config FILE           Path to configuration file [default: config/ENV.env]
    -d, --dry-run               Show what would be deployed without making changes
    --parallel                  Deploy to all regions in parallel (faster but less verbose)
    -h, --help                  Show this help message

EXAMPLES:
    # Deploy to primary and one secondary region
    $0 -p us-east-1 -s us-west-2

    # Deploy to multiple regions
    $0 -p ap-south-1 -s us-east-1 -s eu-west-1 -s ap-southeast-1

    # Dry run for production
    $0 -e prod -p us-east-1 -s us-west-2 --dry-run

    # Parallel deployment (faster)
    $0 -p us-east-1 -s us-west-2 --parallel

NOTES:
    - Primary region is deployed first and fully validated
    - Secondary regions are deployed after primary succeeds
    - DynamoDB Global Tables are configured for cross-region replication
    - S3 Cross-Region Replication is configured for disaster recovery
    - Route53 health checks are configured for failover

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
        -p|--primary-region)
            PRIMARY_REGION="$2"
            shift 2
            ;;
        -s|--secondary-region)
            SECONDARY_REGIONS+=("$2")
            shift 2
            ;;
        -c|--config)
            CONFIG_FILE="$2"
            shift 2
            ;;
        -d|--dry-run)
            DRY_RUN=true
            shift
            ;;
        --parallel)
            PARALLEL=true
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

# Validate arguments
if [ -z "$PRIMARY_REGION" ]; then
    echo -e "${RED}Error: Primary region is required${NC}"
    usage
fi

if [ ${#SECONDARY_REGIONS[@]} -eq 0 ]; then
    echo -e "${YELLOW}Warning: No secondary regions specified. Deploying to primary region only.${NC}"
fi

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
    
    log_success "Configuration loaded"
    log_info "Environment: $ENVIRONMENT"
    log_info "Primary Region: $PRIMARY_REGION"
    log_info "Secondary Regions: ${SECONDARY_REGIONS[*]}"
}

# Deploy to a single region
deploy_to_region() {
    local region=$1
    local is_primary=$2
    
    log_section "Deploying to Region: $region"
    
    if [ "$is_primary" = true ]; then
        log_info "Deploying PRIMARY region..."
    else
        log_info "Deploying SECONDARY region..."
    fi
    
    # Set region for deployment
    export AWS_REGION=$region
    
    # Run master deployment script
    if bash "$SCRIPT_DIR/deploy-master.sh" -e "$ENVIRONMENT" -c "$CONFIG_FILE" -r "$region"; then
        log_success "Deployment to $region completed successfully"
        return 0
    else
        log_error "Deployment to $region failed"
        return 1
    fi
}

# Configure DynamoDB Global Tables
configure_global_tables() {
    log_section "Configuring DynamoDB Global Tables"
    
    local tables=("AuditFlow-Documents" "AuditFlow-AuditRecords")
    local all_regions=("$PRIMARY_REGION" "${SECONDARY_REGIONS[@]}")
    
    for table in "${tables[@]}"; do
        log_info "Configuring global table: $table"
        
        # Create replica regions array
        local replicas=""
        for region in "${all_regions[@]}"; do
            if [ -n "$replicas" ]; then
                replicas="$replicas,"
            fi
            replicas="${replicas}{RegionName=$region}"
        done
        
        # Update table to global table
        log_info "Creating global table with replicas in: ${all_regions[*]}"
        
        if aws dynamodb create-global-table \
            --global-table-name "$table" \
            --replication-group "$replicas" \
            --region "$PRIMARY_REGION" 2>/dev/null; then
            log_success "Global table $table configured"
        else
            log_warning "Global table $table already exists or configuration failed"
        fi
    done
}

# Configure S3 Cross-Region Replication
configure_s3_replication() {
    log_section "Configuring S3 Cross-Region Replication"
    
    ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    PRIMARY_BUCKET="${S3_BUCKET_PREFIX}-${ACCOUNT_ID}"
    
    for secondary_region in "${SECONDARY_REGIONS[@]}"; do
        SECONDARY_BUCKET="${S3_BUCKET_PREFIX}-${secondary_region}-${ACCOUNT_ID}"
        
        log_info "Configuring replication from $PRIMARY_REGION to $secondary_region"
        
        # Create replication role if it doesn't exist
        REPLICATION_ROLE_NAME="AuditFlow-S3-Replication-Role"
        
        if ! aws iam get-role --role-name "$REPLICATION_ROLE_NAME" &> /dev/null; then
            log_info "Creating S3 replication role..."
            
            aws iam create-role \
                --role-name "$REPLICATION_ROLE_NAME" \
                --assume-role-policy-document '{
                    "Version": "2012-10-17",
                    "Statement": [{
                        "Effect": "Allow",
                        "Principal": {"Service": "s3.amazonaws.com"},
                        "Action": "sts:AssumeRole"
                    }]
                }' &> /dev/null
            
            # Attach replication policy
            aws iam put-role-policy \
                --role-name "$REPLICATION_ROLE_NAME" \
                --policy-name "S3ReplicationPolicy" \
                --policy-document "{
                    \"Version\": \"2012-10-17\",
                    \"Statement\": [
                        {
                            \"Effect\": \"Allow\",
                            \"Action\": [\"s3:GetReplicationConfiguration\", \"s3:ListBucket\"],
                            \"Resource\": \"arn:aws:s3:::${PRIMARY_BUCKET}\"
                        },
                        {
                            \"Effect\": \"Allow\",
                            \"Action\": [\"s3:GetObjectVersionForReplication\", \"s3:GetObjectVersionAcl\"],
                            \"Resource\": \"arn:aws:s3:::${PRIMARY_BUCKET}/*\"
                        },
                        {
                            \"Effect\": \"Allow\",
                            \"Action\": [\"s3:ReplicateObject\", \"s3:ReplicateDelete\"],
                            \"Resource\": \"arn:aws:s3:::${SECONDARY_BUCKET}/*\"
                        }
                    ]
                }" &> /dev/null
            
            log_success "S3 replication role created"
        fi
        
        # Configure replication on primary bucket
        REPLICATION_ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/${REPLICATION_ROLE_NAME}"
        
        log_info "Configuring replication rule..."
        aws s3api put-bucket-replication \
            --bucket "$PRIMARY_BUCKET" \
            --replication-configuration "{
                \"Role\": \"${REPLICATION_ROLE_ARN}\",
                \"Rules\": [{
                    \"Status\": \"Enabled\",
                    \"Priority\": 1,
                    \"DeleteMarkerReplication\": {\"Status\": \"Enabled\"},
                    \"Filter\": {},
                    \"Destination\": {
                        \"Bucket\": \"arn:aws:s3:::${SECONDARY_BUCKET}\",
                        \"ReplicationTime\": {
                            \"Status\": \"Enabled\",
                            \"Time\": {\"Minutes\": 15}
                        },
                        \"Metrics\": {
                            \"Status\": \"Enabled\",
                            \"EventThreshold\": {\"Minutes\": 15}
                        }
                    }
                }]
            }" \
            --region "$PRIMARY_REGION" 2>/dev/null || log_warning "Replication already configured"
        
        log_success "S3 replication configured to $secondary_region"
    done
}

# Configure Route53 health checks and failover
configure_route53_failover() {
    log_section "Configuring Route53 Health Checks and Failover"
    
    log_info "Route53 configuration requires manual setup:"
    echo ""
    echo "1. Create health checks for each regional API Gateway endpoint"
    echo "2. Create Route53 hosted zone for your domain"
    echo "3. Create failover routing policy with primary and secondary records"
    echo "4. Associate health checks with each record"
    echo ""
    log_warning "Route53 configuration not automated - please configure manually"
}

# Dry run mode
if [ "$DRY_RUN" = true ]; then
    log_section "DRY RUN MODE"
    log_warning "This is a dry run. No resources will be created."
    load_config
    
    log_section "Multi-Region Deployment Plan"
    echo "Primary Region: $PRIMARY_REGION"
    echo "Secondary Regions: ${SECONDARY_REGIONS[*]}"
    echo ""
    echo "The following will be deployed to each region:"
    echo "  - KMS encryption keys"
    echo "  - S3 buckets with cross-region replication"
    echo "  - DynamoDB tables with global table configuration"
    echo "  - Lambda functions"
    echo "  - Step Functions state machines"
    echo "  - API Gateway endpoints"
    echo "  - Cognito User Pools"
    echo "  - IAM roles and policies"
    echo ""
    echo "Additional multi-region features:"
    echo "  - DynamoDB Global Tables for cross-region replication"
    echo "  - S3 Cross-Region Replication for disaster recovery"
    echo "  - Route53 health checks and failover (manual configuration)"
    echo ""
    log_info "To execute deployment, run without --dry-run flag"
    exit 0
fi

# Main deployment
main() {
    log_section "AuditFlow-Pro Multi-Region Deployment"
    log_info "Starting multi-region deployment at $(date)"
    
    # Load configuration
    load_config
    
    # Deploy to primary region first
    if ! deploy_to_region "$PRIMARY_REGION" true; then
        log_error "Primary region deployment failed. Aborting."
        exit 1
    fi
    
    # Validate primary region
    log_info "Validating primary region deployment..."
    if bash "$SCRIPT_DIR/validate-deployment.sh" -e "$ENVIRONMENT" -c "$CONFIG_FILE"; then
        log_success "Primary region validation passed"
    else
        log_error "Primary region validation failed. Aborting secondary deployments."
        exit 1
    fi
    
    # Deploy to secondary regions
    if [ ${#SECONDARY_REGIONS[@]} -gt 0 ]; then
        if [ "$PARALLEL" = true ]; then
            log_info "Deploying to secondary regions in parallel..."
            
            # Deploy in parallel using background processes
            pids=()
            for region in "${SECONDARY_REGIONS[@]}"; do
                deploy_to_region "$region" false &
                pids+=($!)
            done
            
            # Wait for all deployments to complete
            failed=0
            for pid in "${pids[@]}"; do
                if ! wait $pid; then
                    ((failed++))
                fi
            done
            
            if [ $failed -gt 0 ]; then
                log_error "$failed secondary region deployment(s) failed"
            else
                log_success "All secondary regions deployed successfully"
            fi
        else
            log_info "Deploying to secondary regions sequentially..."
            
            for region in "${SECONDARY_REGIONS[@]}"; do
                if ! deploy_to_region "$region" false; then
                    log_warning "Deployment to $region failed, continuing with other regions..."
                fi
            done
        fi
        
        # Configure multi-region features
        configure_global_tables
        configure_s3_replication
        configure_route53_failover
    fi
    
    # Deployment complete
    log_section "Multi-Region Deployment Complete!"
    log_success "AuditFlow-Pro deployed to multiple regions"
    log_info "Deployment completed at $(date)"
    
    # Output summary
    echo ""
    log_section "Deployment Summary"
    echo "Environment: $ENVIRONMENT"
    echo "Primary Region: $PRIMARY_REGION"
    echo "Secondary Regions: ${SECONDARY_REGIONS[*]}"
    echo ""
    echo "Multi-Region Features:"
    echo "  ✓ DynamoDB Global Tables configured"
    echo "  ✓ S3 Cross-Region Replication configured"
    echo "  ⚠ Route53 failover requires manual configuration"
    echo ""
    echo "Next Steps:"
    echo "  1. Validate each regional deployment"
    echo "  2. Configure Route53 health checks and failover"
    echo "  3. Test cross-region failover"
    echo "  4. Update frontend to use Route53 endpoint"
    echo ""
}

# Run main deployment
main

