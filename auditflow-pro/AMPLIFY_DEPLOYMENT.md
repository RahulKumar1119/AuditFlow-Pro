# AWS Amplify Deployment Guide

This guide provides step-by-step instructions for deploying the AuditFlow-Pro frontend to AWS Amplify with custom domain configuration.

## Prerequisites

- AWS Account with appropriate permissions
- Git repository (GitHub, GitLab, Bitbucket, or AWS CodeCommit)
- Custom domain: `auditflowpro.online`
- Domain DNS access for configuration

## Task 22.1: Configure Amplify Hosting

### Step 1: Create Amplify App

1. **Navigate to AWS Amplify Console**
   - Go to: https://console.aws.amazon.com/amplify/
   - Click "Create new app"

2. **Connect Git Repository**
   - Select your Git provider (GitHub, GitLab, Bitbucket, or AWS CodeCommit)
   - Authorize AWS Amplify to access your repository
   - Select the repository containing AuditFlow-Pro
   - Select the branch to deploy (e.g., `main` or `production`)

3. **Configure Build Settings**
   - Amplify will auto-detect the `amplify.yml` file in `auditflow-pro/frontend/`
   - Verify the build settings:
     ```yaml
     version: 1
     frontend:
       phases:
         preBuild:
           commands:
             - npm ci
         build:
           commands:
             - npm run build
       artifacts:
         baseDirectory: dist
         files:
           - '**/*'
     ```
   - Set the app root directory: `auditflow-pro/frontend`

4. **Configure Environment Variables**
   
   Add the following environment variables in Amplify Console:
   
   | Variable Name | Value | Description |
   |---------------|-------|-------------|
   | `VITE_API_GATEWAY_URL` | `https://api.auditflowpro.online` | API Gateway endpoint URL |
   | `VITE_AWS_REGION` | `ap-south-1` | AWS region for services |
   | `VITE_COGNITO_USER_POOL_ID` | `ap-south-1_XXXXXXXXX` | Cognito User Pool ID |
   | `VITE_COGNITO_CLIENT_ID` | `XXXXXXXXXXXXXXXXXXXXXXXXXX` | Cognito App Client ID |
   | `VITE_S3_BUCKET_NAME` | `auditflow-pro-documents` | S3 bucket for documents |
   | `NODE_VERSION` | `20` | Node.js version for build |

   **To add environment variables:**
   - In Amplify Console, go to App Settings > Environment variables
   - Click "Manage variables"
   - Add each variable with its value
   - Click "Save"

5. **Review and Deploy**
   - Review all settings
   - Click "Save and deploy"
   - Wait for the initial deployment to complete (typically 5-10 minutes)

### Step 2: Verify Initial Deployment

1. **Check Build Status**
   - Monitor the build progress in Amplify Console
   - Review build logs for any errors
   - Verify all phases complete successfully:
     - Provision
     - Build
     - Deploy
     - Verify

2. **Test Default Domain**
   - Access the auto-generated Amplify domain: `https://main.XXXXXX.amplifyapp.com`
   - Verify the application loads correctly
   - Test basic navigation and functionality

## Task 22.2: Set Up Custom Domain and HTTPS

### Step 1: Add Custom Domain

1. **Navigate to Domain Management**
   - In Amplify Console, go to App Settings > Domain management
   - Click "Add domain"

2. **Configure Domain**
   - Enter your domain: `auditflowpro.online`
   - Amplify will automatically:
     - Request an SSL/TLS certificate from AWS Certificate Manager (ACM)
     - Configure HTTPS with TLS 1.2+
     - Set up CloudFront distribution

3. **Configure Subdomains**
   - Add subdomain configuration:
     - `www.auditflowpro.online` → Redirect to `auditflowpro.online`
     - `auditflowpro.online` → Main application
   - Enable automatic subdomain detection for branch deployments (optional)

### Step 2: Update DNS Records

Amplify will provide DNS records to add to your domain registrar:

1. **Get DNS Configuration**
   - In Domain management, view the DNS records
   - You'll see CNAME or ANAME/ALIAS records

2. **Update DNS at Your Registrar**
   
   Add the following records to your DNS provider for `auditflowpro.online`:

   **Option A: CNAME Records (if supported for apex domain)**
   ```
   Type: CNAME
   Name: auditflowpro.online
   Value: [provided by Amplify, e.g., d1234abcd.cloudfront.net]
   TTL: 300
   ```

   **Option B: ANAME/ALIAS Records (recommended for apex domain)**
   ```
   Type: ANAME or ALIAS
   Name: @
   Value: [provided by Amplify]
   TTL: 300
   ```

   **For www subdomain:**
   ```
   Type: CNAME
   Name: www
   Value: [provided by Amplify]
   TTL: 300
   ```

3. **Wait for DNS Propagation**
   - DNS changes can take 5 minutes to 48 hours to propagate
   - Use `dig` or `nslookup` to verify:
     ```bash
     dig auditflowpro.online
     nslookup auditflowpro.online
     ```

4. **Verify SSL Certificate**
   - Amplify will automatically validate the domain and issue SSL certificate
   - Certificate status will show as "Available" when ready
   - This typically takes 5-30 minutes

### Step 3: Verify HTTPS Configuration

1. **Test HTTPS Access**
   - Visit: `https://auditflowpro.online`
   - Verify the SSL certificate is valid
   - Check that HTTP automatically redirects to HTTPS

2. **Verify TLS Version**
   ```bash
   # Test TLS 1.2 support
   openssl s_client -connect auditflowpro.online:443 -tls1_2
   
   # Test TLS 1.3 support
   openssl s_client -connect auditflowpro.online:443 -tls1_3
   ```

3. **Check Security Headers**
   ```bash
   curl -I https://auditflowpro.online
   ```
   
   Verify the following headers are present:
   - `Strict-Transport-Security: max-age=31536000; includeSubDomains`
   - `X-Frame-Options: DENY`
   - `X-Content-Type-Options: nosniff`
   - `X-XSS-Protection: 1; mode=block`

## Task 22.3: Configure Automatic Deployments

### Step 1: Set Up CI/CD Pipeline

1. **Configure Branch Deployments**
   - In Amplify Console, go to App Settings > Build settings
   - Enable automatic builds for branches:
     - `main` → Production (auditflowpro.online)
     - `staging` → Staging subdomain (staging.auditflowpro.online)
     - `develop` → Development subdomain (dev.auditflowpro.online)

2. **Configure Build Triggers**
   - Automatic builds trigger on:
     - Git push to connected branch
     - Pull request creation (for preview deployments)
   - Configure build notifications:
     - Email notifications for build failures
     - SNS topic for build status updates

3. **Set Up Build Notifications**
   ```bash
   # Create SNS topic for build notifications
   aws sns create-topic --name amplify-build-notifications
   
   # Subscribe email to topic
   aws sns subscribe \
     --topic-arn arn:aws:sns:ap-south-1:ACCOUNT_ID:amplify-build-notifications \
     --protocol email \
     --notification-endpoint admin@auditflowpro.online
   ```

### Step 2: Configure Deployment Rollback

1. **Enable Deployment History**
   - Amplify automatically maintains deployment history
   - Each deployment is versioned and can be rolled back

2. **Rollback Procedure**
   
   **Via Console:**
   - Go to App Settings > Deployments
   - Select a previous successful deployment
   - Click "Redeploy this version"

   **Via CLI:**
   ```bash
   # List deployments
   aws amplify list-jobs --app-id YOUR_APP_ID --branch-name main
   
   # Start rollback to specific job
   aws amplify start-job \
     --app-id YOUR_APP_ID \
     --branch-name main \
     --job-type RELEASE \
     --job-id PREVIOUS_JOB_ID
   ```

3. **Set Up Automated Rollback**
   
   Create a CloudWatch alarm to trigger rollback on errors:
   ```bash
   # Create alarm for 4xx errors
   aws cloudwatch put-metric-alarm \
     --alarm-name amplify-high-4xx-errors \
     --alarm-description "Trigger rollback on high 4xx error rate" \
     --metric-name 4xxErrorRate \
     --namespace AWS/Amplify \
     --statistic Average \
     --period 300 \
     --threshold 10 \
     --comparison-operator GreaterThanThreshold \
     --evaluation-periods 2
   ```

### Step 3: Verify Deployment Performance

1. **Monitor Build Time**
   - Target: Deployment completes within 10 minutes
   - Check build logs for bottlenecks
   - Optimize if needed:
     - Use `npm ci` instead of `npm install` (already configured)
     - Enable build caching (already configured in amplify.yml)
     - Parallelize build steps if possible

2. **Test Deployment Pipeline**
   ```bash
   # Make a test change
   echo "// Test deployment" >> auditflow-pro/frontend/src/App.tsx
   
   # Commit and push
   git add .
   git commit -m "test: Verify automatic deployment"
   git push origin main
   
   # Monitor deployment in Amplify Console
   # Verify deployment completes in < 10 minutes
   ```

## Task 22.4: Optimize Frontend Performance

### Step 1: Implement Code Splitting

The application already uses Vite which provides automatic code splitting. Verify optimization:

1. **Check Bundle Size**
   ```bash
   cd auditflow-pro/frontend
   npm run build
   
   # Analyze bundle size
   ls -lh dist/assets/
   ```

2. **Implement Route-Based Code Splitting**
   
   Update `src/App.tsx` to use lazy loading:
   ```typescript
   import { lazy, Suspense } from 'react';
   
   const Dashboard = lazy(() => import('./pages/Dashboard'));
   const Upload = lazy(() => import('./pages/Upload'));
   const AuditDetailView = lazy(() => import('./components/audit/AuditDetailView'));
   
   // Wrap routes with Suspense
   <Suspense fallback={<div>Loading...</div>}>
     <Routes>
       <Route path="/" element={<Dashboard />} />
       <Route path="/upload" element={<Upload />} />
       <Route path="/audits/:id" element={<AuditDetailView />} />
     </Routes>
   </Suspense>
   ```

### Step 2: Configure Caching Headers

Caching headers are already configured in `amplify.yml`:

- HTML files: `no-cache` (always fetch fresh)
- JS/CSS files: `max-age=31536000, immutable` (cache for 1 year)
- Static assets: `max-age=31536000, immutable` (cache for 1 year)

### Step 3: Verify Performance

1. **Test Page Load Time**
   ```bash
   # Use curl to measure load time
   curl -w "@curl-format.txt" -o /dev/null -s https://auditflowpro.online
   ```

   Create `curl-format.txt`:
   ```
   time_namelookup:  %{time_namelookup}\n
   time_connect:  %{time_connect}\n
   time_starttransfer:  %{time_starttransfer}\n
   time_total:  %{time_total}\n
   ```

2. **Use Lighthouse for Performance Audit**
   ```bash
   # Install Lighthouse CLI
   npm install -g lighthouse
   
   # Run audit
   lighthouse https://auditflowpro.online --output html --output-path ./lighthouse-report.html
   ```

   Target metrics:
   - Performance score: > 90
   - First Contentful Paint: < 1.5s
   - Time to Interactive: < 3.0s
   - Total page load: < 3.0s

3. **Monitor with CloudWatch**
   
   Set up CloudWatch dashboard for performance monitoring:
   - Request count
   - Latency (p50, p95, p99)
   - Error rates (4xx, 5xx)
   - Data transfer

## Verification Checklist

### Task 22.1: Amplify Hosting
- [ ] Amplify app created and connected to Git repository
- [ ] Build settings configured with correct `amplify.yml`
- [ ] Environment variables set for API endpoints and AWS services
- [ ] Initial deployment successful
- [ ] Application accessible via default Amplify domain

### Task 22.2: Custom Domain and HTTPS
- [ ] Custom domain `auditflowpro.online` added to Amplify
- [ ] DNS records updated at domain registrar
- [ ] SSL/TLS certificate issued and validated
- [ ] HTTPS enabled with TLS 1.2+
- [ ] HTTP automatically redirects to HTTPS
- [ ] Security headers configured and verified
- [ ] www subdomain redirects to apex domain

### Task 22.3: Automatic Deployments
- [ ] Automatic builds enabled for main branch
- [ ] Build triggers configured for Git pushes
- [ ] Build notifications set up (email/SNS)
- [ ] Deployment history accessible
- [ ] Rollback procedure tested and documented
- [ ] Deployment completes within 10 minutes

### Task 22.4: Performance Optimization
- [ ] Code splitting implemented for routes
- [ ] Bundle size optimized (< 500KB initial load)
- [ ] Caching headers configured
- [ ] Page load time < 3 seconds verified
- [ ] Lighthouse performance score > 90
- [ ] CloudWatch monitoring configured

## Troubleshooting

### Build Failures

**Issue:** Build fails with "Module not found" error
```bash
# Solution: Ensure all dependencies are in package.json
npm install
npm run build  # Test locally first
```

**Issue:** Build timeout (> 10 minutes)
```bash
# Solution: Optimize build process
# 1. Use npm ci instead of npm install (already configured)
# 2. Enable caching (already configured)
# 3. Check for large dependencies
npm ls --depth=0
```

### DNS Issues

**Issue:** Domain not resolving after DNS update
```bash
# Check DNS propagation
dig auditflowpro.online
nslookup auditflowpro.online

# Clear local DNS cache
# macOS:
sudo dscacheutil -flushcache; sudo killall -HUP mDNSResponder

# Linux:
sudo systemd-resolve --flush-caches

# Windows:
ipconfig /flushdns
```

### SSL Certificate Issues

**Issue:** SSL certificate validation pending
- Wait 5-30 minutes for validation
- Verify DNS records are correct
- Check domain ownership verification email

**Issue:** Certificate shows as invalid
- Verify domain matches exactly (no typos)
- Check that DNS records point to Amplify
- Contact AWS Support if issue persists

### Performance Issues

**Issue:** Page load time > 3 seconds
```bash
# Analyze bundle size
npm run build
ls -lh dist/assets/

# Solutions:
# 1. Implement code splitting (see Task 22.4)
# 2. Optimize images (use WebP format)
# 3. Remove unused dependencies
# 4. Enable compression (already configured in Amplify)
```

## AWS CLI Commands Reference

```bash
# List Amplify apps
aws amplify list-apps

# Get app details
aws amplify get-app --app-id YOUR_APP_ID

# List branches
aws amplify list-branches --app-id YOUR_APP_ID

# Get branch details
aws amplify get-branch --app-id YOUR_APP_ID --branch-name main

# List domains
aws amplify list-domain-associations --app-id YOUR_APP_ID

# Start deployment
aws amplify start-job --app-id YOUR_APP_ID --branch-name main --job-type RELEASE

# List deployments
aws amplify list-jobs --app-id YOUR_APP_ID --branch-name main

# Get deployment status
aws amplify get-job --app-id YOUR_APP_ID --branch-name main --job-id JOB_ID
```

## Security Best Practices

1. **Environment Variables**
   - Never commit sensitive values to Git
   - Use Amplify environment variables for secrets
   - Rotate credentials regularly

2. **Access Control**
   - Limit Amplify Console access to authorized users
   - Use IAM roles with least privilege
   - Enable MFA for AWS accounts

3. **Monitoring**
   - Set up CloudWatch alarms for errors
   - Monitor access logs for suspicious activity
   - Review security headers regularly

4. **Updates**
   - Keep dependencies up to date
   - Monitor for security vulnerabilities
   - Apply patches promptly

## Next Steps

After completing Task 22, proceed to:
- **Task 23:** Implement security and encryption (KMS, field-level encryption)
- **Task 24:** Implement monitoring and alerting (CloudWatch, dashboards)
- **Task 25:** Conduct end-to-end testing in production environment

## Support

For issues or questions:
- AWS Amplify Documentation: https://docs.aws.amazon.com/amplify/
- AWS Support: https://console.aws.amazon.com/support/
- Project Repository: [Your Git repository URL]
