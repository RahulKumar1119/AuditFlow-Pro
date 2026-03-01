# Monorepo Configuration Fix

## Issue
AWS Amplify deployment failed with error:
```
CustomerError: Monorepo spec provided without "applications" key
```

## Root Cause
The `amplify.yml` file was located in `auditflow-pro/frontend/` directory and used the standard single-app configuration format. AWS Amplify detected the repository as a monorepo but couldn't find the required monorepo configuration.

## Solution

### 1. Moved amplify.yml to Repository Root
The `amplify.yml` file must be at the repository root for monorepo detection:
```
AuditFlow-Pro/
├── amplify.yml          ← Must be here (root level)
├── auditflow-pro/
│   ├── frontend/
│   │   ├── src/
│   │   ├── package.json
│   │   └── ...
│   └── backend/
└── ...
```

### 2. Updated Configuration Format
Changed from single-app format to monorepo format with `applications` key:

**Before (Single-App Format):**
```yaml
version: 1
frontend:
  phases:
    preBuild:
      commands:
        - cd frontend
        - npm ci
```

**After (Monorepo Format):**
```yaml
version: 1
applications:
  - appRoot: auditflow-pro/frontend
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

### 3. Key Changes

1. **Added `applications` array**: Required for monorepo configuration
2. **Specified `appRoot`**: Points to `auditflow-pro/frontend` directory
3. **Removed `cd` commands**: Amplify automatically navigates to `appRoot`
4. **Adjusted paths**: All paths are now relative to `appRoot`

## Files Modified

1. **Created**: `amplify.yml` (at repository root)
2. **Updated**: `auditflow-pro/AMPLIFY_DEPLOYMENT.md` (documentation)
3. **Kept**: `auditflow-pro/frontend/amplify.yml` (as reference)

## Deployment Instructions

1. **Verify File Location**
   ```bash
   # From repository root
   ls amplify.yml  # Should exist
   ```

2. **Commit and Push**
   ```bash
   git add amplify.yml
   git commit -m "Fix: Configure Amplify for monorepo structure"
   git push origin main
   ```

3. **AWS Amplify Console**
   - Amplify will automatically detect the new configuration
   - No manual build settings changes needed
   - The build will now succeed

## Expected Build Output

```
✓ Provision
✓ Build
  - Installing dependencies in auditflow-pro/frontend
  - Building React TypeScript application
  - Build artifacts created in dist/
✓ Deploy
✓ Verify
```

## References

- [AWS Amplify Monorepo Documentation](https://docs.aws.amazon.com/amplify/latest/userguide/monorepo-configuration.html)
- [Amplify Build Specification](https://docs.aws.amazon.com/amplify/latest/userguide/build-settings.html)
