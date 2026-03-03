# Cognito Login Troubleshooting Guide

## Current Configuration

- **User Pool ID**: `ap-south-1_lIhrnyezu`
- **Client ID**: `7n2nt2p6l7dhifjihhk7eaqjjd`
- **Region**: `ap-south-1`
- **Test User**: `rahulgood66@gmail.com`

## Quick Diagnostic Steps

### Step 1: Run Debug Script

```bash
cd auditflow-pro
./debug-cognito-login.sh
```

This will test:
- User Pool exists
- Client exists and has correct auth flows
- User exists and is enabled
- Authentication works via AWS CLI

### Step 2: Check Frontend Environment Variables

```bash
cd frontend
cat .env | grep VITE_COGNITO
```

Should show:
```
VITE_COGNITO_REGION=ap-south-1
VITE_COGNITO_USER_POOL_ID=ap-south-1_lIhrnyezu
VITE_COGNITO_CLIENT_ID=7n2nt2p6l7dhifjihhk7eaqjjd
```

### Step 3: Restart Dev Server

**IMPORTANT**: Vite only loads .env variables at startup!

```bash
# Stop the dev server (Ctrl+C)
# Then restart:
npm run dev
```

### Step 4: Clear Browser Cache

1. Open DevTools (F12)
2. Right-click the refresh button
3. Select "Empty Cache and Hard Reload"
4. Or use Incognito/Private mode

### Step 5: Check Browser Console

Open browser console (F12) and look for:
- Amplify configuration logs
- Authentication error messages
- Network requests to cognito-idp.ap-south-1.amazonaws.com

## Common Issues and Solutions

### Issue 1: "User does not exist" or "User pool client does not exist"

**Cause**: Frontend is using old/wrong Cognito IDs

**Solution**:
```bash
cd auditflow-pro/frontend

# Verify .env has correct values
cat .env

# If wrong, update:
echo "VITE_COGNITO_USER_POOL_ID=ap-south-1_lIhrnyezu" >> .env
echo "VITE_COGNITO_CLIENT_ID=7n2nt2p6l7dhifjihhk7eaqjjd" >> .env

# MUST restart dev server
npm run dev
```

### Issue 2: "Incorrect username or password"

**Cause**: Wrong password or user not confirmed

**Solution**:
```bash
# Reset user password
aws cognito-idp admin-set-user-password \
  --user-pool-id ap-south-1_lIhrnyezu \
  --username rahulgood66@gmail.com \
  --password "NewPassword123!" \
  --permanent \
  --region ap-south-1
```

### Issue 3: Environment variables are undefined

**Cause**: Dev server not restarted or .env file not in correct location

**Solution**:
```bash
# Ensure .env is in frontend/ directory
ls -la auditflow-pro/frontend/.env

# Restart dev server (REQUIRED!)
cd auditflow-pro/frontend
npm run dev
```

### Issue 4: "User needs to be authenticated to call this API"

**Cause**: No user created in Cognito yet

**Solution**:
```bash
cd auditflow-pro
./create-admin-user.sh your-email@example.com YourPassword123! "Your Name"
```

### Issue 5: CORS errors

**Cause**: API Gateway not configured or wrong URL

**Solution**: This is expected if backend isn't deployed yet. Login should still work.

## Manual Authentication Test

Test authentication directly with AWS CLI:

```bash
aws cognito-idp admin-initiate-auth \
  --user-pool-id ap-south-1_lIhrnyezu \
  --client-id 7n2nt2p6l7dhifjihhk7eaqjjd \
  --auth-flow ADMIN_NO_SRP_AUTH \
  --auth-parameters USERNAME=rahulgood66@gmail.com,PASSWORD=YourPassword \
  --region ap-south-1
```

If this works, the issue is in the frontend configuration.

## Verify Frontend Configuration at Runtime

Add this to `frontend/src/main.tsx` temporarily:

```typescript
console.log('Cognito Config:', {
  userPoolId: import.meta.env.VITE_COGNITO_USER_POOL_ID,
  clientId: import.meta.env.VITE_COGNITO_CLIENT_ID,
  region: import.meta.env.VITE_COGNITO_REGION
});
```

Check browser console - values should NOT be undefined.

## Check User Status

```bash
aws cognito-idp admin-get-user \
  --user-pool-id ap-south-1_lIhrnyezu \
  --username rahulgood66@gmail.com \
  --region ap-south-1
```

User should be:
- `UserStatus`: `CONFIRMED`
- `Enabled`: `true`

## Reset Everything (Nuclear Option)

If nothing works:

```bash
# 1. Delete user
aws cognito-idp admin-delete-user \
  --user-pool-id ap-south-1_lIhrnyezu \
  --username rahulgood66@gmail.com \
  --region ap-south-1

# 2. Recreate user
cd auditflow-pro
./create-admin-user.sh rahulgood66@gmail.com YourNewPassword123! "Rahul"

# 3. Clear frontend cache
cd frontend
rm -rf node_modules/.vite
rm -rf dist

# 4. Restart dev server
npm run dev

# 5. Clear browser cache and try again
```

## Still Not Working?

Share these details:

1. **Exact error message** from browser console
2. **Network tab** - what's the request/response to cognito-idp?
3. **Output of**:
   ```bash
   cd auditflow-pro/frontend
   cat .env | grep VITE_COGNITO
   ```
4. **Browser console logs** when you try to login

## Contact Support

If issue persists, provide:
- Browser console logs (F12 → Console tab)
- Network logs (F12 → Network tab → Filter: cognito)
- Output of `./debug-cognito-login.sh`
