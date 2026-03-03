# Amplify Setup Verification Checklist

Use this checklist to manually verify your AWS Amplify deployment for AuditFlow-Pro.

## Pre-Verification Setup

- [ ] AWS CLI installed and configured
- [ ] Access to AWS Console with Amplify permissions
- [ ] Configuration file created (`config/dev.env` or `config/prod.env`)
- [ ] Required tools installed (curl, jq, openssl, dig)

## Task 22.1: Amplify Hosting Configuration

### Amplify App Setup
- [ ] Amplify app created in AWS Console
- [ ] App name: `AuditFlow-Pro` (or as configured)
- [ ] Git repository connected successfully
- [ ] Repository URL visible in Amplify Console

### Build Configuration
- [ ] `amplify.yml` file exists in repository root
- [ ] `appRoot: auditflow-pro/frontend` configured in amplify.yml
- [ ] Build commands specified correctly
- [ ] Artifacts configuration correct (`baseDirectory: dist`)

### Environment Variables
- [ ] `VITE_API_GATEWAY_URL` configured
- [ ] `VITE_AWS_REGION` configured
- [ ] `VITE_COGNITO_USER_POOL_ID` configured
- [ ] `VITE_COGNITO_CLIENT_ID` configured
- [ ] `VITE_S3_BUCKET_NAME` configured
- [ ] `NODE_VERSION` set to 20 (or appropriate version)

### Branch Configuration
- [ ] Main branch connected
- [ ] Automatic builds enabled
- [ ] Branch auto-detection configured (optional)

### Initial Deployment
- [ ] First deployment completed successfully
- [ ] Build logs show no errors
- [ ] All build phases completed (Provision, Build, Deploy, Verify)
- [ ] Default Amplify domain accessible
- [ ] Application loads correctly on default domain

**Test:** Visit `https://main.XXXXXX.amplifyapp.com` and verify the app loads

---

## Task 22.2: Custom Domain and HTTPS

### Domain Configuration
- [ ] Custom domain added: `auditflowpro.online`
- [ ] Domain status shows "AVAILABLE" (or "PENDING_VERIFICATION")
- [ ] SSL/TLS certificate requested
- [ ] Certificate status shows "AVAILABLE"

### DNS Configuration
- [ ] DNS records provided by Amplify
- [ ] CNAME/ANAME records added to domain registrar
- [ ] www subdomain configured (optional)
- [ ] DNS propagation completed (may take 5-60 minutes)

**Test DNS:**
```bash
dig auditflowpro.online
nslookup auditflowpro.online
```

### HTTPS Configuration
- [ ] HTTPS endpoint accessible
- [ ] HTTP automatically redirects to HTTPS
- [ ] SSL certificate valid (no browser warnings)
- [ ] Certificate issued by Amazon (AWS Certificate Manager)

**Test HTTPS:**
```bash
curl -I https://auditflowpro.online
```

### TLS Version
- [ ] TLS 1.2 supported
- [ ] TLS 1.3 supported (optional)

**Test TLS:**
```bash
openssl s_client -connect auditflowpro.online:443 -tls1_2
```

### Security Headers
- [ ] `Strict-Transport-Security` header present
- [ ] `X-Frame-Options` header present
- [ ] `X-Content-Type-Options` header present
- [ ] `X-XSS-Protection` header present (optional)

**Test Headers:**
```bash
curl -I https://auditflowpro.online | grep -i "strict-transport\|x-frame\|x-content"
```

---

## Task 22.3: Automatic Deployments

### CI/CD Pipeline
- [ ] Automatic builds trigger on Git push
- [ ] Build notifications configured (email/SNS)
- [ ] Multiple branches configured (main, staging, develop) - optional
- [ ] Preview deployments for pull requests - optional

### Deployment History
- [ ] Recent deployments visible in Amplify Console
- [ ] Latest deployment status: SUCCESS
- [ ] Deployment history accessible
- [ ] Can view logs for each deployment

### Deployment Performance
- [ ] Latest deployment completed in < 10 minutes
- [ ] Build time acceptable
- [ ] No timeout errors

**Check deployment time in Amplify Console:**
- Go to: App Settings > Deployments
- Review latest deployment duration

### Rollback Capability
- [ ] Previous deployments listed
- [ ] Can select previous deployment
- [ ] "Redeploy this version" option available
- [ ] Rollback procedure documented

**Test rollback (optional):**
1. Select a previous successful deployment
2. Click "Redeploy this version"
3. Verify rollback completes successfully

---

## Task 22.4: Performance Optimization

### Code Splitting
- [ ] Multiple JavaScript chunks generated
- [ ] Route-based lazy loading implemented
- [ ] Suspense boundaries configured

**Check build output:**
```bash
cd frontend
npm run build
ls -lh dist/assets/
```

### Bundle Size
- [ ] Initial bundle < 500KB (recommended)
- [ ] Total bundle size optimized
- [ ] No large unnecessary dependencies

### Caching Configuration
- [ ] Cache-Control headers configured
- [ ] HTML files: `no-cache`
- [ ] JS/CSS files: `max-age=31536000, immutable`
- [ ] Static assets cached appropriately

**Test caching:**
```bash
curl -I https://auditflowpro.online | grep -i cache-control
```

### Page Load Performance
- [ ] Page loads in < 3 seconds
- [ ] First Contentful Paint < 1.5s
- [ ] Time to Interactive < 3.0s

**Test with curl:**
```bash
curl -w "@curl-format.txt" -o /dev/null -s https://auditflowpro.online
```

**Test with Lighthouse:**
```bash
lighthouse https://auditflowpro.online --output html
```

### Performance Targets
- [ ] Lighthouse Performance score > 90
- [ ] Lighthouse Accessibility score > 90
- [ ] Lighthouse Best Practices score > 90
- [ ] Lighthouse SEO score > 80

---

## Additional Verification

### Frontend Functionality
- [ ] Login page loads
- [ ] Can navigate between pages
- [ ] API calls work (if backend deployed)
- [ ] Authentication flow works (if Cognito configured)
- [ ] Document upload interface loads
- [ ] Audit queue displays correctly

### Integration with Backend
- [ ] API Gateway endpoint configured
- [ ] CORS configured correctly
- [ ] Authentication tokens passed correctly
- [ ] API calls return expected responses

### Monitoring and Logging
- [ ] CloudWatch logs configured
- [ ] Access logs available
- [ ] Error tracking enabled
- [ ] Performance metrics visible

### Security
- [ ] No sensitive data in environment variables
- [ ] API keys not exposed in frontend code
- [ ] HTTPS enforced everywhere
- [ ] Security headers configured

---

## Automated Verification

Run the automated verification script:

```bash
cd auditflow-pro
./verify-amplify-setup.sh -e prod -v
```

Expected output:
- Total Checks: ~45
- Passed: ~40-45
- Warnings: 0-5 (acceptable)
- Failed: 0 (must be zero)

---

## Final Verification

### Manual Testing
1. [ ] Visit https://auditflowpro.online
2. [ ] Verify page loads without errors
3. [ ] Check browser console for errors
4. [ ] Test navigation between pages
5. [ ] Test responsive design (mobile/desktop)
6. [ ] Verify all images and assets load

### Browser Testing
- [ ] Chrome/Chromium
- [ ] Firefox
- [ ] Safari (if available)
- [ ] Edge (if available)
- [ ] Mobile browsers (iOS Safari, Chrome Mobile)

### Performance Testing
- [ ] Run Lighthouse audit
- [ ] Check Network tab in DevTools
- [ ] Verify resource loading order
- [ ] Check for render-blocking resources

---

## Sign-Off

### Development Environment
- [ ] All checks passed
- [ ] Automated script passed
- [ ] Manual testing completed
- [ ] Ready for staging

**Verified by:** ________________  
**Date:** ________________

### Staging Environment
- [ ] All checks passed
- [ ] Automated script passed
- [ ] Manual testing completed
- [ ] Ready for production

**Verified by:** ________________  
**Date:** ________________

### Production Environment
- [ ] All checks passed
- [ ] Automated script passed
- [ ] Manual testing completed
- [ ] Monitoring configured
- [ ] Alerts configured
- [ ] Documentation updated

**Verified by:** ________________  
**Date:** ________________

---

## Troubleshooting Reference

If any checks fail, refer to:
- `AMPLIFY_DEPLOYMENT.md` - Detailed setup instructions
- `AMPLIFY_VERIFICATION_GUIDE.md` - Troubleshooting guide
- AWS Amplify Console - Build logs and error messages
- CloudWatch Logs - Application logs

---

## Next Steps After Verification

1. [ ] Run end-to-end tests (Task 22.5)
2. [ ] Configure monitoring and alerting (Task 24)
3. [ ] Set up backup and disaster recovery
4. [ ] Document deployment process
5. [ ] Train team on deployment procedures
6. [ ] Schedule regular performance audits

---

## Notes

Use this space to document any issues, workarounds, or custom configurations:

```
[Add your notes here]
```
