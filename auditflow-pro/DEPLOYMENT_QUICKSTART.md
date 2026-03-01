# AuditFlow-Pro Deployment Quick Start

## 🚀 Deploy to AWS Amplify in 15 Minutes

This quick start guide will get your AuditFlow-Pro frontend deployed to `auditflowpro.online` with HTTPS.

### Prerequisites Checklist
- [ ] AWS Account with Amplify access
- [ ] Git repository pushed to GitHub/GitLab/Bitbucket
- [ ] Domain `auditflowpro.online` registered
- [ ] DNS access for domain configuration

---

## Step 1: Pre-flight Check (2 minutes)

Run the deployment check script:

```bash
cd auditflow-pro/frontend
./deploy-check.sh
```

This verifies:
- ✓ Node.js version >= 20
- ✓ All tests pass
- ✓ Build succeeds
- ✓ No critical issues

---

## Step 2: Create Amplify App (5 minutes)

### Via AWS Console:

1. **Go to Amplify Console**
   - https://console.aws.amazon.com/amplify/

2. **Create New App**
   - Click "Create new app" → "Host web app"
   - Select your Git provider
   - Authorize AWS Amplify
   - Select repository and branch

3. **Configure Build**
   - App root: `auditflow-pro/frontend`
   - Build command: `npm run build`
   - Output directory: `dist`
   - Amplify will auto-detect `amplify.yml`

4. **Add Environment Variables**
   ```
   VITE_API_GATEWAY_URL=https://api.auditflowpro.online
   VITE_AWS_REGION=us-east-1
   VITE_COGNITO_USER_POOL_ID=us-east-1_XXXXXXXXX
   VITE_COGNITO_CLIENT_ID=XXXXXXXXXXXXXXXXXXXXXXXXXX
   VITE_S3_BUCKET_NAME=auditflow-pro-documents
   NODE_VERSION=20
   ```

5. **Save and Deploy**
   - Click "Save and deploy"
   - Wait 5-10 minutes for first deployment

### Via AWS CLI:

```bash
# Create app
aws amplify create-app \
  --name auditflow-pro \
  --repository https://github.com/YOUR_USERNAME/auditflow-pro \
  --oauth-token YOUR_GITHUB_TOKEN \
  --build-spec "$(cat auditflow-pro/frontend/amplify.yml)"

# Create branch
aws amplify create-branch \
  --app-id YOUR_APP_ID \
  --branch-name main \
  --enable-auto-build

# Add environment variables
aws amplify update-app \
  --app-id YOUR_APP_ID \
  --environment-variables \
    VITE_API_GATEWAY_URL=https://api.auditflowpro.online \
    VITE_AWS_REGION=us-east-1 \
    NODE_VERSION=20

# Start deployment
aws amplify start-job \
  --app-id YOUR_APP_ID \
  --branch-name main \
  --job-type RELEASE
```

---

## Step 3: Configure Custom Domain (5 minutes)

### In Amplify Console:

1. **Add Domain**
   - Go to App Settings → Domain management
   - Click "Add domain"
   - Enter: `auditflowpro.online`
   - Click "Configure domain"

2. **Get DNS Records**
   - Amplify will show DNS records to add
   - Copy the CNAME/ANAME values

### Update DNS:

Add these records at your domain registrar:

```
Type: ANAME (or ALIAS)
Name: @
Value: [provided by Amplify]
TTL: 300

Type: CNAME
Name: www
Value: [provided by Amplify]
TTL: 300
```

### Wait for Verification:
- DNS propagation: 5-30 minutes
- SSL certificate: 5-30 minutes
- Status will show "Available" when ready

---

## Step 4: Verify Deployment (3 minutes)

### Test the Application:

```bash
# Check DNS resolution
dig auditflowpro.online

# Test HTTPS
curl -I https://auditflowpro.online

# Verify security headers
curl -I https://auditflowpro.online | grep -E "(Strict-Transport|X-Frame|X-Content)"
```

### Browser Testing:
1. Visit: https://auditflowpro.online
2. Verify SSL certificate (🔒 in address bar)
3. Test login functionality
4. Test document upload
5. Check responsive design (mobile/desktop)

### Performance Check:

```bash
# Install Lighthouse
npm install -g lighthouse

# Run audit
lighthouse https://auditflowpro.online --view
```

Target scores:
- Performance: > 90
- Accessibility: > 90
- Best Practices: > 90
- SEO: > 90

---

## Step 5: Enable Automatic Deployments (Already Configured!)

Automatic deployments are enabled by default:

- ✓ Push to `main` → Deploys to production
- ✓ Create PR → Creates preview deployment
- ✓ Build notifications via email

### Test Automatic Deployment:

```bash
# Make a small change
echo "// Deployment test" >> src/App.tsx

# Commit and push
git add .
git commit -m "test: Verify automatic deployment"
git push origin main

# Monitor in Amplify Console
# Build should complete in < 10 minutes
```

---

## Troubleshooting

### Build Fails

**Check build logs in Amplify Console:**
```bash
# Common issues:
# 1. Missing environment variables
# 2. Node version mismatch
# 3. Dependency installation failure

# Solution: Verify environment variables and Node version
```

### Domain Not Resolving

**Check DNS propagation:**
```bash
dig auditflowpro.online
nslookup auditflowpro.online

# If not resolving after 1 hour:
# 1. Verify DNS records are correct
# 2. Check domain registrar settings
# 3. Try flushing local DNS cache
```

### SSL Certificate Pending

**Wait 5-30 minutes for validation**
- Amplify automatically validates domain ownership
- Certificate will show "Available" when ready
- If stuck > 1 hour, check DNS records

### Performance Issues

**Run deployment check:**
```bash
cd auditflow-pro/frontend
./deploy-check.sh
```

**Optimize bundle size:**
- Check for large dependencies
- Implement code splitting (already configured)
- Enable compression (already configured)

---

## Quick Commands Reference

```bash
# Pre-flight check
cd auditflow-pro/frontend && ./deploy-check.sh

# Build locally
npm run build

# Test build locally
npm run preview

# Check bundle size
ls -lh dist/assets/

# View Amplify app status
aws amplify get-app --app-id YOUR_APP_ID

# List deployments
aws amplify list-jobs --app-id YOUR_APP_ID --branch-name main

# Trigger manual deployment
aws amplify start-job --app-id YOUR_APP_ID --branch-name main --job-type RELEASE

# Rollback to previous deployment
aws amplify start-job --app-id YOUR_APP_ID --branch-name main --job-type RELEASE --job-id PREVIOUS_JOB_ID
```

---

## Environment Variables Reference

| Variable | Example Value | Required |
|----------|---------------|----------|
| `VITE_API_GATEWAY_URL` | `https://api.auditflowpro.online` | Yes |
| `VITE_AWS_REGION` | `us-east-1` | Yes |
| `VITE_COGNITO_USER_POOL_ID` | `us-east-1_XXXXXXXXX` | Yes |
| `VITE_COGNITO_CLIENT_ID` | `XXXXXXXXXXXXXXXXXXXXXXXXXX` | Yes |
| `VITE_S3_BUCKET_NAME` | `auditflow-pro-documents` | Yes |
| `NODE_VERSION` | `20` | Yes |

---

## Success Checklist

- [ ] Application deployed to Amplify
- [ ] Custom domain `auditflowpro.online` configured
- [ ] HTTPS enabled with valid SSL certificate
- [ ] HTTP redirects to HTTPS
- [ ] Security headers configured
- [ ] Automatic deployments working
- [ ] Performance score > 90
- [ ] Page load time < 3 seconds
- [ ] All tests passing
- [ ] Build time < 10 minutes

---

## Next Steps

After successful deployment:

1. **Monitor Performance**
   - Set up CloudWatch dashboards
   - Configure alerts for errors
   - Monitor user analytics

2. **Security Hardening**
   - Complete Task 23 (Encryption)
   - Review IAM policies
   - Enable WAF rules

3. **Testing**
   - Run end-to-end tests
   - Perform security audit
   - Load testing

4. **Documentation**
   - Update API documentation
   - Create user guides
   - Document deployment process

---

## Support Resources

- **Detailed Guide:** `AMPLIFY_DEPLOYMENT.md`
- **AWS Amplify Docs:** https://docs.aws.amazon.com/amplify/
- **Vite Docs:** https://vitejs.dev/
- **React Docs:** https://react.dev/

---

## Deployment Timeline

| Task | Duration | Status |
|------|----------|--------|
| Pre-flight check | 2 min | ⏳ |
| Create Amplify app | 5 min | ⏳ |
| Configure domain | 5 min | ⏳ |
| Verify deployment | 3 min | ⏳ |
| **Total** | **15 min** | |

*Note: DNS propagation and SSL certificate validation may add 5-30 minutes*

---

**Ready to deploy? Run the pre-flight check and follow the steps above!** 🚀
