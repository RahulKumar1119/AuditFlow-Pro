# Amplify Setup Verification Guide

This guide explains how to use the `verify-amplify-setup.sh` script to validate your AWS Amplify deployment according to Task 22 requirements.

## Quick Start

```bash
# Navigate to project directory
cd auditflow-pro

# Run verification for development environment
./verify-amplify-setup.sh -e dev

# Run verification for production
./verify-amplify-setup.sh -e prod -v
```

## What Gets Verified

The script validates all requirements from **Task 22** in `tasks.md`:

### Task 22.1: Amplify Hosting Configuration
- ✓ Amplify app exists and is properly configured
- ✓ Git repository is connected
- ✓ Build settings are correct (amplify.yml)
- ✓ Environment variables are configured
- ✓ Branch configuration is correct
- ✓ Automatic builds are enabled

**Requirements validated:** 15.1, 15.2

### Task 22.2: Custom Domain and HTTPS
- ✓ Custom domain is configured (auditflowpro.online)
- ✓ DNS records are properly set
- ✓ SSL/TLS certificate is issued and valid
- ✓ HTTPS is enabled with TLS 1.2+
- ✓ HTTP redirects to HTTPS
- ✓ Security headers are configured

**Requirements validated:** 15.4, 15.5, 16.2

### Task 22.3: Automatic Deployments
- ✓ Recent deployments exist
- ✓ Latest deployment was successful
- ✓ Deployment completes within 10 minutes
- ✓ Automatic builds trigger on Git push
- ✓ Build notifications are configured

**Requirements validated:** 15.2, 15.3, 15.6

### Task 22.4: Performance Optimization
- ✓ Page load time < 3 seconds
- ✓ Caching headers are configured
- ✓ Code splitting is implemented
- ✓ Bundle size is optimized

**Requirements validated:** 15.7, 19.7

## Usage Examples

### Basic Verification
```bash
# Verify development environment
./verify-amplify-setup.sh -e dev

# Verify production environment
./verify-amplify-setup.sh -e prod
```

### Verbose Mode
Get detailed information about each check:
```bash
./verify-amplify-setup.sh -e prod -v
```

### Skip Performance Tests
For faster validation (useful during development):
```bash
./verify-amplify-setup.sh -e dev -s
```

### Custom Configuration File
Use a specific configuration file:
```bash
./verify-amplify-setup.sh -c /path/to/custom.env
```

## Prerequisites

Before running the script, ensure you have:

1. **AWS CLI installed and configured**
   ```bash
   aws --version
   aws configure
   ```

2. **Required tools installed**
   - curl (for HTTP testing)
   - jq (for JSON parsing)
   - openssl (optional, for TLS testing)
   - dig (optional, for DNS testing)
   - bc (for calculations)

3. **Configuration file**
   - File: `config/dev.env` or `config/prod.env`
   - Must contain required environment variables

4. **AWS permissions**
   - Amplify read access
   - Cognito read access
   - CloudWatch read access

## Configuration File Format

Your `config/{environment}.env` file should contain:

```bash
# AWS Configuration
AWS_REGION=ap-south-1
ACCOUNT_ID=123456789012

# Amplify Configuration
AMPLIFY_APP_NAME=AuditFlow-Pro
CUSTOM_DOMAIN_NAME=auditflowpro.online

# Frontend Environment Variables
VITE_API_GATEWAY_URL=https://api.auditflowpro.online
VITE_AWS_REGION=ap-south-1
VITE_COGNITO_USER_POOL_ID=ap-south-1_XXXXXXXXX
VITE_COGNITO_CLIENT_ID=XXXXXXXXXXXXXXXXXXXXXXXXXX
VITE_S3_BUCKET_NAME=auditflow-pro-documents

# Optional
USER_POOL_ID=ap-south-1_XXXXXXXXX
API_GATEWAY_URL=https://api.auditflowpro.online
```

## Understanding the Output

### Success Output
```
========================================
Validation Summary
========================================
Total Checks: 45
Passed: 45
Warnings: 0
Failed: 0

Success Rate: 100%

[✓] All critical checks passed!

✓ Amplify setup is ready for production!
```

### Warning Output
```
[⚠] Build notifications not enabled
[⚠] TLS 1.3 not supported (TLS 1.2 is sufficient)
```
Warnings indicate optional features that could be improved but don't block deployment.

### Error Output
```
[✗] Amplify app not found: AuditFlow-Pro
[✗] Custom domain not configured: auditflowpro.online
```
Errors indicate critical issues that must be fixed before deployment.

## Troubleshooting

### Error: "Configuration file not found"
```bash
# Create the configuration file
mkdir -p config
cp config/dev.env.example config/dev.env
# Edit config/dev.env with your values
```

### Error: "AWS credentials invalid"
```bash
# Configure AWS CLI
aws configure

# Verify credentials
aws sts get-caller-identity
```

### Error: "Amplify app not found"
Check that:
1. Amplify app is created in AWS Console
2. App name matches `AMPLIFY_APP_NAME` in config
3. You have correct AWS region configured

### Error: "jq: command not found"
```bash
# Install jq
# Ubuntu/Debian:
sudo apt-get install jq

# macOS:
brew install jq

# CentOS/RHEL:
sudo yum install jq
```

### Warning: "DNS not resolving"
This is normal if:
- Domain was just configured (DNS propagation takes time)
- You're testing before DNS records are updated

Wait 5-60 minutes and re-run the script.

### Warning: "Page load time exceeds 3 second target"
Possible causes:
- Network latency
- Large bundle size
- Missing code splitting
- Caching not configured

See Task 22.4 in `AMPLIFY_DEPLOYMENT.md` for optimization steps.

## Integration with CI/CD

You can integrate this script into your CI/CD pipeline:

```yaml
# Example GitHub Actions workflow
name: Verify Amplify Deployment

on:
  push:
    branches: [main]
  workflow_dispatch:

jobs:
  verify:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ap-south-1
      
      - name: Install dependencies
        run: |
          sudo apt-get update
          sudo apt-get install -y jq bc
      
      - name: Verify Amplify setup
        run: |
          cd auditflow-pro
          ./verify-amplify-setup.sh -e prod -v
```

## Next Steps

After successful verification:

1. **Run end-to-end tests** (Task 22.5)
   ```bash
   cd frontend
   npm run test:e2e
   ```

2. **Monitor performance** in production
   - Check CloudWatch metrics
   - Review Amplify Console analytics
   - Run Lighthouse audits regularly

3. **Set up monitoring alerts**
   - Configure CloudWatch alarms
   - Set up SNS notifications
   - Monitor error rates

4. **Document deployment**
   - Update deployment documentation
   - Record resource identifiers
   - Document any custom configurations

## Related Documentation

- **AMPLIFY_DEPLOYMENT.md** - Detailed deployment guide for Task 22
- **tasks.md** - Complete implementation plan
- **requirements.md** - System requirements and acceptance criteria
- **validate-deployment.sh** - Backend infrastructure validation

## Support

If you encounter issues:

1. Check the troubleshooting section above
2. Review AWS Amplify Console logs
3. Verify AWS permissions
4. Check configuration file values
5. Consult `AMPLIFY_DEPLOYMENT.md` for detailed setup instructions

## Script Options Reference

```
Usage: ./verify-amplify-setup.sh [OPTIONS]

OPTIONS:
    -e, --environment ENV    Environment to validate (dev, staging, prod)
    -c, --config FILE        Path to configuration file
    -v, --verbose            Enable verbose output
    -s, --skip-performance   Skip performance tests
    -h, --help               Show help message
```

## Exit Codes

- **0** - All checks passed
- **1** - One or more critical checks failed

Use exit codes in scripts:
```bash
if ./verify-amplify-setup.sh -e prod; then
    echo "Deployment verified successfully"
else
    echo "Deployment verification failed"
    exit 1
fi
```
