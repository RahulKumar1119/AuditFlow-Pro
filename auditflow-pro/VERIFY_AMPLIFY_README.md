# Amplify Setup Verification - Quick Start

This directory contains tools to verify your AWS Amplify deployment for AuditFlow-Pro according to Task 22 requirements.

## 🚀 Quick Verification

```bash
# Run automated verification
cd auditflow-pro
./verify-amplify-setup.sh -e prod -v
```

## 📋 Available Resources

### 1. Automated Verification Script
**File:** `verify-amplify-setup.sh`

Comprehensive automated testing of your Amplify setup.

```bash
# Basic usage
./verify-amplify-setup.sh -e dev

# With verbose output
./verify-amplify-setup.sh -e prod -v

# Skip performance tests (faster)
./verify-amplify-setup.sh -e dev -s
```

**What it checks:**
- ✅ Amplify app configuration
- ✅ Git repository connection
- ✅ Build settings and environment variables
- ✅ Custom domain and DNS
- ✅ HTTPS and TLS configuration
- ✅ Security headers
- ✅ Deployment history and performance
- ✅ Page load time and caching
- ✅ Frontend functionality

### 2. Verification Guide
**File:** `AMPLIFY_VERIFICATION_GUIDE.md`

Complete guide with:
- Detailed usage instructions
- Troubleshooting steps
- Configuration examples
- CI/CD integration
- Exit codes and error handling

### 3. Manual Checklist
**File:** `AMPLIFY_VERIFICATION_CHECKLIST.md`

Printable checklist for manual verification:
- Step-by-step verification tasks
- Test commands for each requirement
- Sign-off sections for each environment
- Troubleshooting reference

### 4. Deployment Guide
**File:** `AMPLIFY_DEPLOYMENT.md`

Complete deployment instructions for Task 22:
- Task 22.1: Amplify hosting setup
- Task 22.2: Custom domain configuration
- Task 22.3: CI/CD pipeline setup
- Task 22.4: Performance optimization

## 📊 Verification Coverage

The verification tools validate all Task 22 requirements:

| Task | Description | Requirements | Status |
|------|-------------|--------------|--------|
| 22.1 | Amplify Hosting | 15.1, 15.2 | ✅ Automated |
| 22.2 | Custom Domain & HTTPS | 15.4, 15.5, 16.2 | ✅ Automated |
| 22.3 | Automatic Deployments | 15.2, 15.3, 15.6 | ✅ Automated |
| 22.4 | Performance Optimization | 15.7, 19.7 | ✅ Automated |

## 🔧 Prerequisites

Before running verification:

1. **Install required tools:**
   ```bash
   # Ubuntu/Debian
   sudo apt-get install -y curl jq bc openssl dnsutils
   
   # macOS
   brew install curl jq bc openssl bind
   ```

2. **Configure AWS CLI:**
   ```bash
   aws configure
   ```

3. **Create configuration file:**
   ```bash
   # Copy example configuration
   cp config/dev.env.example config/dev.env
   
   # Edit with your values
   nano config/dev.env
   ```

4. **Ensure Amplify app is deployed:**
   - App created in AWS Amplify Console
   - Git repository connected
   - At least one successful deployment

## 📝 Configuration File

Create `config/{environment}.env` with:

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
```

## 🎯 Verification Workflow

### Step 1: Automated Verification
```bash
./verify-amplify-setup.sh -e prod -v
```

### Step 2: Review Results
- ✅ All checks passed → Proceed to Step 3
- ⚠️ Warnings present → Review and fix if needed
- ❌ Failures present → Fix issues and re-run

### Step 3: Manual Verification
Use `AMPLIFY_VERIFICATION_CHECKLIST.md` to:
- Test functionality in browser
- Verify user experience
- Check responsive design
- Test on multiple browsers

### Step 4: Performance Testing
```bash
# Run Lighthouse audit
lighthouse https://auditflowpro.online --output html

# Check bundle size
cd frontend && npm run build && ls -lh dist/assets/
```

### Step 5: Sign-Off
- Document results in checklist
- Update deployment documentation
- Notify team of successful deployment

## 🐛 Troubleshooting

### Common Issues

**Issue: "Amplify app not found"**
```bash
# List all Amplify apps
aws amplify list-apps --region ap-south-1

# Verify app name matches configuration
```

**Issue: "DNS not resolving"**
```bash
# Check DNS propagation
dig auditflowpro.online
nslookup auditflowpro.online

# Wait 5-60 minutes for propagation
```

**Issue: "Page load time exceeds 3 seconds"**
- Check bundle size: `cd frontend && npm run build`
- Verify code splitting is enabled
- Check caching headers
- Review network tab in DevTools

**Issue: "Environment variables not configured"**
```bash
# Add via AWS CLI
aws amplify update-app \
  --app-id YOUR_APP_ID \
  --environment-variables VITE_API_GATEWAY_URL=https://api.example.com

# Or add via Amplify Console:
# App Settings > Environment variables
```

## 📚 Additional Resources

- **AWS Amplify Documentation:** https://docs.aws.amazon.com/amplify/
- **Task 22 Requirements:** See `../loan-document-auditor/tasks.md`
- **System Requirements:** See `../loan-document-auditor/requirements.md`
- **Backend Validation:** See `validate-deployment.sh`

## 🔄 CI/CD Integration

Add to your GitHub Actions workflow:

```yaml
- name: Verify Amplify Deployment
  run: |
    cd auditflow-pro
    ./verify-amplify-setup.sh -e prod
```

## 📞 Support

If verification fails:

1. Check troubleshooting section in `AMPLIFY_VERIFICATION_GUIDE.md`
2. Review AWS Amplify Console logs
3. Verify AWS permissions
4. Check configuration file values
5. Consult `AMPLIFY_DEPLOYMENT.md` for setup instructions

## ✅ Success Criteria

Verification is successful when:
- ✅ Automated script passes (0 failures)
- ✅ Manual checklist completed
- ✅ Page loads in < 3 seconds
- ✅ Lighthouse score > 90
- ✅ All security headers present
- ✅ HTTPS enforced
- ✅ Deployments complete in < 10 minutes

## 🎉 Next Steps

After successful verification:

1. Run end-to-end tests (Task 22.5)
2. Configure monitoring (Task 24)
3. Set up alerts and notifications
4. Document deployment process
5. Train team on procedures

---

**Ready to verify?** Run: `./verify-amplify-setup.sh -e prod -v`
