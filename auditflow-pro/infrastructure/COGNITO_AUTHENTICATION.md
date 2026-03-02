# AWS Cognito Authentication Implementation

This document describes the AWS Cognito authentication implementation for AuditFlow-Pro.

## Overview

The authentication system uses AWS Cognito to provide secure user authentication and authorization with the following features:

- Email/password authentication
- Role-based access control (Loan Officers and Administrators)
- Session timeout (30 minutes)
- Account lockout after failed login attempts
- MFA support for Administrators
- Comprehensive authentication logging with PII redaction
- Temporary AWS credentials via Identity Pool

## Requirements Covered

- **2.1**: Authenticate users through Cognito
- **2.2**: Require valid credentials for Dashboard access
- **2.3**: Support Loan Officer and Administrator roles
- **2.4**: Grant Loan Officer access to upload documents and view audit results
- **2.5**: Grant Administrator full system access
- **2.6**: Enforce 30-minute session timeout
- **2.7**: Lock account after 3 failed login attempts for 15 minutes
- **2.8**: Use TLS for all authentication data
- **7.3**: Redact PII from logs
- **17.6**: Configure IAM roles for authenticated users
- **17.8**: Enforce MFA for Administrator role
- **18.3**: Log all authentication and authorization events
- **20.9**: Include security tests validating IAM policies and encryption

## Architecture

```
┌─────────────────┐
│  React Frontend │
│   (Amplify)     │
└────────┬────────┘
         │
         │ HTTPS/TLS
         │
┌────────▼────────┐
│  Cognito User   │
│      Pool       │
│                 │
│  - Users        │
│  - Groups       │
│  - MFA          │
│  - Policies     │
└────────┬────────┘
         │
         │ ID Token
         │
┌────────▼────────┐
│  Cognito        │
│  Identity Pool  │
│                 │
│  - Role Mapping │
│  - Temp Creds   │
└────────┬────────┘
         │
         │ AWS Credentials
         │
┌────────▼────────┐
│  AWS Resources  │
│  - S3           │
│  - DynamoDB     │
│  - Lambda       │
└─────────────────┘
```

## Components

### 1. Cognito User Pool

**Purpose**: Manages user identities and authentication

**Configuration**:
- Pool Name: `AuditFlowUserPool`
- Authentication: Email/password
- Password Policy:
  - Minimum length: 12 characters
  - Requires: uppercase, lowercase, numbers, symbols
- MFA: Optional (enforced for Administrators)
- Session timeout: 30 minutes (1800 seconds)
- Advanced Security Mode: ENFORCED
- Device tracking: Enabled

**User Groups**:
1. **LoanOfficers**
   - Read access to S3 documents
   - Read access to DynamoDB audit records
   - Can upload documents and view audit results

2. **Administrators**
   - Full system access
   - User management capabilities
   - CloudWatch logs access
   - MFA enforced

### 2. Cognito Identity Pool

**Purpose**: Provides temporary AWS credentials for authenticated users

**Configuration**:
- Pool Name: `AuditFlowIdentityPool`
- Unauthenticated access: Disabled
- Role mapping: Token-based with group mapping

**IAM Roles**:

**AuditFlowLoanOfficerRole**:
```json
{
  "S3": ["GetObject", "ListBucket"],
  "DynamoDB": ["GetItem", "Query", "Scan"]
}
```

**AuditFlowAdministratorRole**:
```json
{
  "S3": ["*"],
  "DynamoDB": ["*"],
  "Cognito": ["*"],
  "CloudWatch": ["*"]
}
```

### 3. Authentication Logger Lambda

**Purpose**: Logs all authentication and authorization events with PII redaction

**Function Name**: `AuditFlowAuthLogger`

**Triggers**:
- PreAuthentication
- PostAuthentication
- PreSignUp
- PostConfirmation
- PreTokenGeneration
- CustomMessage

**Features**:
- Automatic PII redaction (emails, SSN, phone numbers, IP addresses)
- Structured JSON logging
- Group membership tracking
- Authorization level determination

**Log Format**:
```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "event_type": "authentication",
  "trigger_source": "PostAuthentication_Authentication",
  "user_id": "user-123",
  "user_pool_id": "us-east-1_ABC123",
  "action": "post_authentication",
  "description": "User successfully signed in",
  "user_groups": ["LoanOfficers"],
  "authorization_level": "loan_officer",
  "request_id": "abc-123"
}
```

### 4. Security Policies

**Account Lockout**:
- Failed attempts threshold: 3
- Lockout duration: 15 minutes
- Implemented via Advanced Security Mode

**Risk-Based Authentication**:
- Low Risk: Notify user, no action
- Medium Risk: Notify user, MFA if configured
- High Risk: Notify user, MFA required
- Compromised Credentials: Block access

**Encryption**:
- All data in transit: TLS 1.2+
- All data at rest: AES-256 via KMS
- Field-level encryption for PII in DynamoDB

## Deployment

### Prerequisites

1. AWS CLI configured with appropriate credentials
2. AWS account with necessary permissions
3. Region configured (default: ap-south-1)

### Deployment Steps

1. **Create User Pool and Identity Pool**:
   ```bash
   ./infrastructure/cognito_setup.sh
   ```

2. **Configure Account Lockout**:
   ```bash
   ./infrastructure/cognito_account_lockout.sh
   ```

3. **Set Up Authentication Logging**:
   ```bash
   ./infrastructure/cognito_logging.sh
   ```

4. **Deploy Authentication Logger Lambda**:
   ```bash
   ./infrastructure/deploy_auth_logger.sh
   ```

5. **Update Frontend Configuration**:
   Add the following to `frontend/.env`:
   ```
   VITE_USER_POOL_ID=<user-pool-id>
   VITE_USER_POOL_CLIENT_ID=<client-id>
   VITE_IDENTITY_POOL_ID=<identity-pool-id>
   VITE_AWS_REGION=ap-south-1
   ```

### Creating Test Users

**Create Loan Officer**:
```bash
aws cognito-idp admin-create-user \
  --user-pool-id <user-pool-id> \
  --username officer@example.com \
  --user-attributes Name=email,Value=officer@example.com \
  --region ap-south-1

aws cognito-idp admin-set-user-password \
  --user-pool-id <user-pool-id> \
  --username officer@example.com \
  --password "SecurePass123!@#" \
  --permanent \
  --region ap-south-1

aws cognito-idp admin-add-user-to-group \
  --user-pool-id <user-pool-id> \
  --username officer@example.com \
  --group-name LoanOfficers \
  --region ap-south-1
```

**Create Administrator**:
```bash
aws cognito-idp admin-create-user \
  --user-pool-id <user-pool-id> \
  --username admin@example.com \
  --user-attributes Name=email,Value=admin@example.com \
  --region ap-south-1

aws cognito-idp admin-set-user-password \
  --user-pool-id <user-pool-id> \
  --username admin@example.com \
  --password "AdminPass123!@#" \
  --permanent \
  --region ap-south-1

aws cognito-idp admin-add-user-to-group \
  --user-pool-id <user-pool-id> \
  --username admin@example.com \
  --group-name Administrators \
  --region ap-south-1

# Enable MFA for administrator
aws cognito-idp admin-set-user-mfa-preference \
  --user-pool-id <user-pool-id> \
  --username admin@example.com \
  --software-token-mfa-settings Enabled=true,PreferredMfa=true \
  --region ap-south-1
```

## Testing

### Unit Tests

Run authentication logger unit tests:
```bash
cd backend
pytest tests/test_auth_logger.py -v
```

### Integration Tests

Run Cognito integration tests:
```bash
# Set environment variables
export AWS_REGION=ap-south-1
export TEST_USER_POOL_ID=<user-pool-id>
export TEST_CLIENT_ID=<client-id>
export TEST_IDENTITY_POOL_ID=<identity-pool-id>

# Run tests
cd backend
pytest tests/integration/test_cognito_authentication.py -v
```

### Manual Testing

1. **Test Login**:
   - Navigate to frontend
   - Enter valid credentials
   - Verify successful login
   - Check session expires after 30 minutes

2. **Test Account Lockout**:
   - Attempt login with wrong password 3 times
   - Verify account is locked
   - Wait 15 minutes and verify access is restored

3. **Test Role-Based Access**:
   - Login as Loan Officer
   - Verify can view documents but not manage users
   - Login as Administrator
   - Verify full system access

4. **Test MFA** (for Administrators):
   - Login as Administrator
   - Verify MFA challenge is presented
   - Complete MFA and verify access

## Monitoring

### CloudWatch Logs

**Authentication Logs**:
- Log Group: `/aws/cognito/auditflow-authentication`
- Retention: 365 days

**View Recent Logs**:
```bash
aws logs tail /aws/cognito/auditflow-authentication --follow --region ap-south-1
```

**Query Failed Logins**:
```bash
aws logs filter-log-events \
  --log-group-name /aws/cognito/auditflow-authentication \
  --filter-pattern "Failed" \
  --region ap-south-1
```

**Query Authorization Decisions**:
```bash
aws logs filter-log-events \
  --log-group-name /aws/cognito/auditflow-authentication \
  --filter-pattern "authorization" \
  --region ap-south-1
```

### Metrics

Monitor the following CloudWatch metrics:
- `SignInSuccesses`: Successful sign-ins
- `SignInThrottles`: Throttled sign-in attempts
- `UserAuthentication`: Authentication attempts
- `AccountTakeOverRisk`: Risk assessments

## Security Best Practices

1. **Password Management**:
   - Enforce strong password policy (12+ chars, complexity)
   - Rotate passwords regularly
   - Never log passwords

2. **MFA**:
   - Enforce MFA for all Administrators
   - Recommend MFA for Loan Officers
   - Support TOTP and SMS MFA

3. **Session Management**:
   - 30-minute session timeout
   - Secure token storage
   - Automatic token refresh

4. **Logging**:
   - Log all authentication events
   - Redact PII from logs
   - Retain logs for 1 year

5. **Access Control**:
   - Principle of least privilege
   - Role-based access control
   - Regular access reviews

## Troubleshooting

### Common Issues

**Issue**: User cannot login
- Check password meets complexity requirements
- Verify account is not locked
- Check user exists in correct group

**Issue**: Session expires too quickly
- Verify token validity is set to 30 minutes
- Check client-side token refresh logic

**Issue**: MFA not working
- Verify MFA is enabled for user
- Check MFA device is properly configured
- Verify time sync on MFA device

**Issue**: Authorization denied
- Check user group membership
- Verify IAM role policies
- Check Identity Pool role mapping

### Support

For issues or questions:
1. Check CloudWatch logs for error details
2. Review IAM policies and permissions
3. Verify Cognito configuration
4. Contact AWS support if needed

## References

- [AWS Cognito Documentation](https://docs.aws.amazon.com/cognito/)
- [Cognito User Pools](https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-user-identity-pools.html)
- [Cognito Identity Pools](https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-identity.html)
- [Advanced Security Features](https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-user-pool-settings-advanced-security.html)
