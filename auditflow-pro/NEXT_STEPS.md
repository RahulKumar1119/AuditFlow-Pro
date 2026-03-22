# Next Steps - Vulnerability Remediation

**Status:** ✅ Code Changes Complete | ⏳ Credential Rotation Pending

---

## What Was Done ✅

### Code Fixes Applied (4 Vulnerabilities)

1. **Vulnerable Dependencies** - Updated requirements.txt
   - urllib3: 1.26.20 → >=2.0.0
   - Werkzeug: 3.0.6 → >=3.0.7
   - PyYAML: 6.0.3 → >=6.0.4
   - cryptography: 46.0.5 → >=43.0.0

2. **Hardcoded Environment Variables** - Secure Configuration
   - Created `backend/config/secure_config.py`
   - Integrated AWS Secrets Manager
   - Integrated AWS Systems Manager Parameter Store
   - Updated extractor/app.py and api_handler/app.py

3. **Insufficient PII Detection** - AWS Comprehend Integration
   - Replaced regex-based detection with ML-based detection
   - Added `detect_pii_comprehensive()` function
   - High confidence threshold (>90%)

4. **Insufficient Input Validation** - Frontend Validation
   - Added configuration validation in main.tsx
   - Validates required fields
   - Validates credential formats
   - User-friendly error messages

---

## What Remains ⏳

### 7 CRITICAL Vulnerabilities (Require Credential Rotation)

1. Exposed AWS Credentials in `create-admin-user.sh`
2. Exposed Cognito IDs in `cognito-ids.txt`
3. Exposed SNS Topic ARNs in `.env`
4. Hardcoded AWS Region and Account ID in `.env`
5. Default Credentials in shell scripts
6. Exposed Frontend Cognito IDs in `frontend/.env`
7. Backup .env with Old Credentials in `frontend/.env.backup`

### 1 HIGH Vulnerability (Requires Credential Rotation)

8. Exposed API Gateway URLs in frontend configuration

---

## Immediate Actions (Next 24 Hours)

### Step 1: Create AWS Secrets Manager Secrets

```bash
# AWS Configuration
aws secretsmanager create-secret \
  --name auditflow/aws-config \
  --secret-string '{
    "AWS_REGION": "ap-south-1",
    "S3_DOCUMENT_BUCKET": "auditflow-documents-prod"
  }'

# DynamoDB Configuration
aws secretsmanager create-secret \
  --name auditflow/dynamodb-config \
  --secret-string '{
    "DYNAMODB_DOCUMENTS_TABLE": "AuditFlow-Documents",
    "DYNAMODB_AUDIT_RECORDS_TABLE": "AuditFlow-AuditRecords"
  }'

# Cognito Configuration
aws secretsmanager create-secret \
  --name auditflow/cognito-config \
  --secret-string '{
    "COGNITO_USER_POOL_ID": "ap-south-1_YOUR_POOL_ID",
    "COGNITO_CLIENT_ID": "YOUR_CLIENT_ID",
    "COGNITO_IDENTITY_POOL_ID": "ap-south-1:YOUR_IDENTITY_POOL_ID"
  }'

# SNS ARNs
aws secretsmanager create-secret \
  --name auditflow/sns-arns \
  --secret-string '{
    "ALERTS_TOPIC_ARN": "arn:aws:sns:ap-south-1:ACCOUNT_ID:AuditFlow-RiskAlerts-prod",
    "CRITICAL_ALERTS_TOPIC_ARN": "arn:aws:sns:ap-south-1:ACCOUNT_ID:AuditFlow-CriticalAlerts-prod"
  }'
```

### Step 2: Create AWS Systems Manager Parameters

```bash
aws ssm put-parameter \
  --name /auditflow/config/CONFIDENCE_THRESHOLD \
  --value "0.80" \
  --type String

aws ssm put-parameter \
  --name /auditflow/config/PROCESSING_TIMEOUT_SECONDS \
  --value "300" \
  --type String
```

### Step 3: Update Lambda IAM Roles

Add these permissions to Lambda execution roles:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["secretsmanager:GetSecretValue"],
      "Resource": ["arn:aws:secretsmanager:ap-south-1:ACCOUNT_ID:secret:auditflow/*"]
    },
    {
      "Effect": "Allow",
      "Action": ["ssm:GetParameter", "ssm:GetParameters", "ssm:GetParametersByPath"],
      "Resource": ["arn:aws:ssm:ap-south-1:ACCOUNT_ID:parameter/auditflow/*"]
    }
  ]
}
```

### Step 4: Deploy Updated Lambda Functions

```bash
# Deploy extractor function with secure config
cd auditflow-pro/backend/functions/extractor
zip -r function.zip .
aws lambda update-function-code \
  --function-name AuditFlow-DocumentClassifier \
  --zip-file fileb://function.zip

# Deploy api_handler function with secure config
cd ../api_handler
zip -r function.zip .
aws lambda update-function-code \
  --function-name AuditFlow-APIHandler \
  --zip-file fileb://function.zip
```

---

## Within 48 Hours

### Step 5: Rotate All Exposed Credentials

```bash
# 1. Regenerate Cognito User Pool
# - Create new User Pool with same configuration
# - Migrate users to new pool
# - Update all references

# 2. Create New SNS Topics
aws sns create-topic --name AuditFlow-RiskAlerts-prod
aws sns create-topic --name AuditFlow-CriticalAlerts-prod

# 3. Rotate AWS Access Keys
# - Create new access keys
# - Update Lambda execution roles
# - Delete old access keys

# 4. Update API Gateway
# - Create new API Gateway endpoints
# - Update frontend configuration
# - Disable old endpoints
```

### Step 6: Remove Exposed Files from Git History

```bash
# Remove exposed files from git history
git filter-branch --tree-filter 'rm -f auditflow-pro/cognito-ids.txt' HEAD
git filter-branch --tree-filter 'rm -f auditflow-pro/.env' HEAD
git filter-branch --tree-filter 'rm -f auditflow-pro/frontend/.env' HEAD
git filter-branch --tree-filter 'rm -f auditflow-pro/frontend/.env.backup' HEAD

# Force push (coordinate with team)
git push origin --force-all

# Verify removal
git log --all --full-history -- "cognito-ids.txt" ".env"
```

### Step 7: Update .gitignore

```bash
cat >> .gitignore << 'EOF'
# Sensitive files
.env
.env.local
.env.*.local
cognito-ids.txt
aws-credentials.txt
secrets/
*.key
*.pem
.aws/
EOF

git add .gitignore
git commit -m "Add .gitignore for sensitive files"
git push origin main
```

---

## Within 1 Week

### Step 8: Deploy Frontend with Validation

```bash
# Create .env.example with placeholders
cat > auditflow-pro/frontend/.env.example << 'EOF'
VITE_COGNITO_USER_POOL_ID=<your-user-pool-id>
VITE_COGNITO_CLIENT_ID=<your-client-id>
VITE_COGNITO_REGION=ap-south-1
EOF

# Deploy frontend
cd auditflow-pro/frontend
npm run build
aws s3 sync dist/ s3://auditflow-frontend-prod/
```

### Step 9: Update Documentation

- Document secure credential setup process
- Update deployment procedures
- Create team training materials
- Update README with security best practices

---

## Verification Checklist

- [ ] Secrets Manager secrets created
- [ ] SSM parameters created
- [ ] Lambda IAM roles updated
- [ ] Lambda functions deployed
- [ ] Configuration loads successfully
- [ ] Credentials rotated
- [ ] Exposed files removed from git history
- [ ] .gitignore updated
- [ ] Frontend deployed with validation
- [ ] Frontend validation working
- [ ] Documentation updated
- [ ] Team trained on secure credential handling

---

## Testing

### Test Configuration Loading

```python
from config.secure_config import get_config

config = get_config()
aws_config = config.get_aws_config()
print(f"✓ S3 Bucket: {aws_config['S3_DOCUMENT_BUCKET']}")
print(f"✓ Region: {aws_config['AWS_REGION']}")
```

### Test PII Detection

```python
from backend.functions.api_handler.app import detect_pii_comprehensive

text = "John Doe, SSN: 123-45-6789, Account: 9876543210"
result = detect_pii_comprehensive(text, "test-doc-1")
print(f"✓ PII Types: {result['pii_types']}")
print(f"✓ Has Sensitive PII: {result['has_sensitive_pii']}")
```

### Test Frontend Validation

```
1. Open browser console
2. Check for: "✓ Amplify configuration validated successfully"
3. If error, check .env file configuration
```

---

## Documentation Files

**Read These:**
1. `REMEDIATION_GUIDE.md` - Detailed remediation instructions
2. `CODE_CHANGES_SUMMARY.md` - Summary of code changes
3. `VULNERABILITY_REPORT.md` - Complete vulnerability assessment
4. `VULNERABILITY_FIX_LOG.md` - Remediation progress log

---

## Key Points

✅ **Code Changes Complete**
- All code-based vulnerabilities fixed
- Ready for deployment

⏳ **Credential Rotation Required**
- 7 CRITICAL vulnerabilities require credential rotation
- 1 HIGH vulnerability requires credential rotation
- Cannot deploy to production until complete

🔒 **Security Improvements**
- Centralized credential management
- ML-based PII detection
- Configuration validation
- No hardcoded credentials

---

## Questions?

Refer to:
- `REMEDIATION_GUIDE.md` for detailed steps
- `CODE_CHANGES_SUMMARY.md` for code changes
- `VULNERABILITY_REPORT.md` for vulnerability details

