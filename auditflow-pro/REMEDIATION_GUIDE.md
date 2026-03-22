# AuditFlow-Pro Vulnerability Remediation Guide

**Date:** March 22, 2026  
**Status:** Code Changes Applied  
**Remaining Actions:** Credential Rotation & AWS Secrets Manager Setup

---

## Code Changes Applied ✅

### 1. Secure Configuration Management

**File Created:** `auditflow-pro/backend/config/secure_config.py`

**What Changed:**
- Eliminated hardcoded environment variables with defaults
- Implemented AWS Secrets Manager integration for all credentials
- Implemented AWS Systems Manager Parameter Store for application config
- Added proper error handling and validation

**Benefits:**
- ✅ No credentials in code or environment variables
- ✅ Centralized credential management
- ✅ Automatic credential rotation support
- ✅ Audit trail of credential access

**Usage:**
```python
from config.secure_config import get_config, get_s3_bucket, get_audit_table

# Get configuration
config = get_config()
s3_bucket = get_s3_bucket()
audit_table = get_audit_table()
confidence_threshold = get_confidence_threshold()
```

---

### 2. Backend Extractor - Secure Configuration

**File Modified:** `auditflow-pro/backend/functions/extractor/app.py`

**What Changed:**
```python
# BEFORE (Vulnerable)
BUCKET_NAME = os.environ.get('UPLOAD_BUCKET', 'auditflow-documents')
CONFIDENCE_THRESHOLD = float(os.environ.get('CONFIDENCE_THRESHOLD', '0.80'))

# AFTER (Secure)
from config.secure_config import get_config, get_confidence_threshold, get_processing_timeout

config = get_config()
aws_config = config.get_aws_config()
CONFIDENCE_THRESHOLD = get_confidence_threshold()
PROCESSING_TIMEOUT = get_processing_timeout()
```

**Benefits:**
- ✅ Eliminates hardcoded defaults
- ✅ Requires explicit configuration in Secrets Manager
- ✅ Fails fast if configuration missing
- ✅ Supports credential rotation

---

### 3. Backend API Handler - Secure Configuration & PII Detection

**File Modified:** `auditflow-pro/backend/functions/api_handler/app.py`

**What Changed:**

#### A. Secure Configuration
```python
# BEFORE (Vulnerable)
BUCKET_NAME = os.environ.get('UPLOAD_BUCKET', 'auditflow-documents')
AUDIT_TABLE = os.environ.get('AUDIT_TABLE', 'AuditFlow-AuditRecords')

# AFTER (Secure)
from config.secure_config import get_config, get_s3_bucket, get_audit_table

BUCKET_NAME = get_s3_bucket()
AUDIT_TABLE = get_audit_table()
```

#### B. Improved PII Detection
```python
# BEFORE (Vulnerable - Regex-based)
def clean_applicant_name(name):
    match = re.match(r'^([A-Za-z\s\.]+?)(?:\s+\d+\s+|$)', name)
    # Unreliable regex pattern

# AFTER (Secure - AWS Comprehend)
def detect_pii_comprehensive(text: str, document_id: str) -> Dict[str, Any]:
    """
    Uses AWS Comprehend ML-based PII detection instead of regex.
    - High confidence detection (>90%)
    - Identifies SSN, bank accounts, driver IDs, DOB
    - Proper error handling and logging
    """
    response = comprehend.detect_pii_entities(
        Text=text,
        LanguageCode='en'
    )
    # Returns high-confidence PII entities
```

**Benefits:**
- ✅ Reliable ML-based PII detection (not regex)
- ✅ High confidence threshold (>90%)
- ✅ Identifies sensitive PII types
- ✅ Proper logging without exposing PII values

---

### 4. Frontend Configuration Validation

**File Modified:** `auditflow-pro/frontend/src/main.tsx`

**What Changed:**
```typescript
// BEFORE (Vulnerable - No validation)
Amplify.configure({
  Auth: {
    Cognito: {
      userPoolId: import.meta.env.VITE_COGNITO_USER_POOL_ID,
      userPoolClientId: import.meta.env.VITE_COGNITO_CLIENT_ID,
    }
  }
});

// AFTER (Secure - Full validation)
function validateAmplifyConfig(): AmplifyConfig {
  // Validate required fields present
  if (!userPoolId || !clientId) {
    throw new Error('Missing required Cognito configuration');
  }
  
  // Validate User Pool ID format
  const userPoolIdPattern = /^[a-z0-9-]+_[a-zA-Z0-9]+$/;
  if (!userPoolIdPattern.test(userPoolId)) {
    throw new Error('Invalid User Pool ID format');
  }
  
  // Validate Client ID format
  const clientIdPattern = /^[a-zA-Z0-9]+$/;
  if (!clientIdPattern.test(clientId)) {
    throw new Error('Invalid Client ID format');
  }
  
  // Validate region format
  const regionPattern = /^[a-z]{2}-[a-z]+-\d{1}$/;
  if (!regionPattern.test(region)) {
    throw new Error('Invalid AWS region format');
  }
  
  return { userPoolId, clientId, region };
}
```

**Benefits:**
- ✅ Validates all required configuration present
- ✅ Validates format of credentials
- ✅ Prevents silent failures
- ✅ User-friendly error messages

---

## Remaining Actions Required

### Priority 1: AWS Secrets Manager Setup (24 Hours)

**Step 1: Create AWS Secrets Manager Secrets**

```bash
# 1. AWS Configuration Secret
aws secretsmanager create-secret \
  --name auditflow/aws-config \
  --secret-string '{
    "AWS_REGION": "ap-south-1",
    "S3_DOCUMENT_BUCKET": "auditflow-documents-prod"
  }'

# 2. DynamoDB Configuration Secret
aws secretsmanager create-secret \
  --name auditflow/dynamodb-config \
  --secret-string '{
    "DYNAMODB_DOCUMENTS_TABLE": "AuditFlow-Documents",
    "DYNAMODB_AUDIT_RECORDS_TABLE": "AuditFlow-AuditRecords"
  }'

# 3. Cognito Configuration Secret
aws secretsmanager create-secret \
  --name auditflow/cognito-config \
  --secret-string '{
    "COGNITO_USER_POOL_ID": "ap-south-1_YOUR_POOL_ID",
    "COGNITO_CLIENT_ID": "YOUR_CLIENT_ID",
    "COGNITO_IDENTITY_POOL_ID": "ap-south-1:YOUR_IDENTITY_POOL_ID"
  }'

# 4. SNS ARNs Secret
aws secretsmanager create-secret \
  --name auditflow/sns-arns \
  --secret-string '{
    "ALERTS_TOPIC_ARN": "arn:aws:sns:ap-south-1:ACCOUNT_ID:AuditFlow-RiskAlerts-prod",
    "CRITICAL_ALERTS_TOPIC_ARN": "arn:aws:sns:ap-south-1:ACCOUNT_ID:AuditFlow-CriticalAlerts-prod"
  }'
```

**Step 2: Create AWS Systems Manager Parameters**

```bash
# Application Configuration Parameters
aws ssm put-parameter \
  --name /auditflow/config/CONFIDENCE_THRESHOLD \
  --value "0.80" \
  --type String

aws ssm put-parameter \
  --name /auditflow/config/PROCESSING_TIMEOUT_SECONDS \
  --value "300" \
  --type String
```

**Step 3: Update Lambda IAM Roles**

Add these permissions to Lambda execution roles:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": [
        "arn:aws:secretsmanager:ap-south-1:ACCOUNT_ID:secret:auditflow/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "ssm:GetParameter",
        "ssm:GetParameters",
        "ssm:GetParametersByPath"
      ],
      "Resource": [
        "arn:aws:ssm:ap-south-1:ACCOUNT_ID:parameter/auditflow/*"
      ]
    }
  ]
}
```

### Priority 2: Credential Rotation (24 Hours)

**Step 1: Rotate Exposed Credentials**

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

**Step 2: Remove Exposed Files from Git History**

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

**Step 3: Update .gitignore**

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
```

### Priority 3: Deployment Updates (48 Hours)

**Step 1: Update Lambda Environment Variables**

Remove all hardcoded environment variables. Lambda will now retrieve configuration from Secrets Manager at runtime.

**Step 2: Update Frontend .env.example**

```env
# .env.example - DO NOT COMMIT ACTUAL VALUES
VITE_COGNITO_USER_POOL_ID=<your-user-pool-id>
VITE_COGNITO_CLIENT_ID=<your-client-id>
VITE_COGNITO_REGION=ap-south-1
```

**Step 3: Update Deployment Documentation**

Document the new secure configuration process:
1. Create Secrets Manager secrets
2. Create SSM parameters
3. Update IAM roles
4. Deploy Lambda functions
5. Deploy frontend with .env file

---

## Vulnerability Status Summary

| # | Vulnerability | Severity | Status | Code Changes |
|---|---|---|---|---|
| 1 | Exposed AWS Credentials | CRITICAL | ⚠️ Pending | N/A - Requires rotation |
| 2 | Exposed Cognito IDs | CRITICAL | ⚠️ Pending | N/A - Requires rotation |
| 3 | Exposed SNS ARNs | CRITICAL | ⚠️ Pending | N/A - Requires rotation |
| 4 | Hardcoded AWS Region | CRITICAL | ⚠️ Pending | N/A - Requires rotation |
| 5 | Default Credentials | CRITICAL | ⚠️ Pending | N/A - Requires rotation |
| 6 | Exposed Frontend Cognito IDs | CRITICAL | ⚠️ Pending | N/A - Requires rotation |
| 7 | Backup .env with Old Credentials | CRITICAL | ⚠️ Pending | N/A - Requires rotation |
| 8 | Exposed API Gateway URLs | HIGH | ⚠️ Pending | N/A - Requires rotation |
| 9 | Vulnerable Dependencies | HIGH | ✅ FIXED | Updated requirements.txt |
| 10 | Hardcoded Environment Variables | HIGH | ✅ FIXED | Secure config implementation |
| 11 | Insufficient PII Detection | MEDIUM | ✅ FIXED | AWS Comprehend integration |
| 12 | Insufficient Input Validation | MEDIUM | ✅ FIXED | Frontend validation added |

---

## Testing the Changes

### Test Secure Configuration

```python
# Test that configuration loads from Secrets Manager
from config.secure_config import get_config

config = get_config()
aws_config = config.get_aws_config()
print(f"S3 Bucket: {aws_config['S3_DOCUMENT_BUCKET']}")
print(f"Region: {aws_config['AWS_REGION']}")
```

### Test PII Detection

```python
from backend.functions.api_handler.app import detect_pii_comprehensive

text = "John Doe, SSN: 123-45-6789, Account: 9876543210"
result = detect_pii_comprehensive(text, "test-doc-1")
print(f"PII Types: {result['pii_types']}")
print(f"Has Sensitive PII: {result['has_sensitive_pii']}")
```

### Test Frontend Validation

```typescript
// Frontend will validate configuration on startup
// Check browser console for validation messages
// Should see: "✓ Amplify configuration validated successfully"
```

---

## Deployment Checklist

- [ ] Create Secrets Manager secrets
- [ ] Create SSM parameters
- [ ] Update Lambda IAM roles
- [ ] Deploy updated Lambda functions
- [ ] Test configuration loading
- [ ] Rotate exposed credentials
- [ ] Remove exposed files from git history
- [ ] Update .gitignore
- [ ] Deploy frontend with validation
- [ ] Test frontend configuration validation
- [ ] Update deployment documentation
- [ ] Team training on secure credential handling

---

## References

- [AWS Secrets Manager Best Practices](https://docs.aws.amazon.com/secretsmanager/latest/userguide/best-practices.html)
- [AWS Systems Manager Parameter Store](https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-parameter-store.html)
- [AWS Comprehend PII Detection](https://docs.aws.amazon.com/comprehend/latest/dg/how-pii.html)
- [OWASP: Secrets Management](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html)

