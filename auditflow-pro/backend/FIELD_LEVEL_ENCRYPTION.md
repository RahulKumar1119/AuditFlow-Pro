# Field-Level Encryption Requirements

## Overview

This document outlines the field-level encryption requirements for PII (Personally Identifiable Information) data in the AuditFlow-Pro system. Field-level encryption ensures that sensitive data is encrypted at the application layer before being stored in DynamoDB, providing an additional layer of security beyond encryption at rest.

## Requirements

**Implements:**
- Requirement 7.4: Encrypt all PII fields in DynamoDB_Table using field-level encryption
- Requirement 16.1: Encrypt all data at rest using KMS_Key with AES-256 encryption

## PII Fields Requiring Encryption

The following PII types detected by AWS Comprehend must be encrypted at the field level:

### Critical PII (Always Encrypted)
1. **SSN (Social Security Numbers)**
   - Format: XXX-XX-XXXX
   - Storage: Encrypted in DynamoDB
   - Display: Masked (***-**-XXXX) for Loan Officers
   - Full access: Administrators only with audit trail

2. **BANK_ACCOUNT_NUMBER (Bank Account Numbers)**
   - Format: Variable length numeric
   - Storage: Encrypted in DynamoDB
   - Display: Masked (****XXXX) for all users
   - Full access: Administrators only with audit trail

3. **DRIVER_ID (Driver's License Numbers)**
   - Format: State-specific format
   - Storage: Encrypted in DynamoDB
   - Display: Masked for Loan Officers
   - Full access: Administrators only with audit trail

4. **DATE_OF_BIRTH (Dates of Birth)**
   - Format: YYYY-MM-DD
   - Storage: Encrypted in DynamoDB
   - Display: Full date visible to Loan Officers
   - Full access: All authorized users

### Additional PII Types
The following additional PII types detected by Comprehend should also be encrypted:
- PASSPORT_NUMBER
- CREDIT_DEBIT_NUMBER
- PIN
- EMAIL
- PHONE
- ADDRESS
- NAME

## Encryption Implementation

### Encryption Method
- **Algorithm**: AES-256-GCM (Galois/Counter Mode)
- **Key Management**: AWS KMS Customer Master Key (CMK)
- **Key Rotation**: Annual automatic rotation
- **Envelope Encryption**: Data keys generated per field, encrypted with KMS CMK

### Encryption Workflow

```
1. Extract PII field from document
2. Generate data encryption key (DEK) using KMS
3. Encrypt field value with DEK using AES-256-GCM
4. Encrypt DEK with KMS CMK
5. Store encrypted value + encrypted DEK in DynamoDB
6. Log encryption event (without PII value)
```

### Decryption Workflow

```
1. Retrieve encrypted value + encrypted DEK from DynamoDB
2. Decrypt DEK using KMS CMK
3. Decrypt field value using DEK
4. Return plaintext value to authorized user
5. Log decryption event with user ID and timestamp
```

## Implementation Status

### Current Implementation (Task 6.7)
- ✅ PII detection using AWS Comprehend DetectPiiEntities API
- ✅ PII masking in logs (Requirement 7.3)
- ✅ PII masking in extraction functions (SSN, account numbers)
- ✅ PII type identification and tracking

### Future Implementation (Task 23.3)
- ⏳ Field-level encryption for DynamoDB storage
- ⏳ KMS key management and rotation
- ⏳ Encryption/decryption utilities
- ⏳ PII access audit trail
- ⏳ Role-based PII access control

## Data Model Changes

### DynamoDB Schema Enhancement

Current extracted data format:
```json
{
  "employee_ssn": {
    "value": "***-**-6789",
    "confidence": 0.99,
    "requires_manual_review": false
  }
}
```

Future encrypted format (Task 23.3):
```json
{
  "employee_ssn": {
    "encrypted_value": "AQICAHh...base64...",
    "encrypted_dek": "AQICAHh...base64...",
    "encryption_key_id": "arn:aws:kms:ap-south-1:123456789012:key/...",
    "encryption_algorithm": "AES-256-GCM",
    "confidence": 0.99,
    "requires_manual_review": false,
    "pii_type": "SSN"
  }
}
```

## Access Control

### Role-Based Access (Requirement 7.5, 7.6)

**Loan Officer Role:**
- View masked SSN (***-**-XXXX)
- View masked account numbers (****XXXX)
- View full dates of birth
- Cannot access full PII values

**Administrator Role:**
- View full PII values when explicitly requested
- All PII access is logged with audit trail
- Requires MFA for PII access

### Audit Trail (Requirement 7.7)

All PII access events must be logged:
```json
{
  "event_type": "PII_ACCESS",
  "timestamp": "2024-01-15T10:30:00Z",
  "user_id": "admin@example.com",
  "user_role": "Administrator",
  "document_id": "uuid",
  "field_name": "employee_ssn",
  "pii_type": "SSN",
  "action": "DECRYPT",
  "ip_address": "192.168.1.100",
  "user_agent": "Mozilla/5.0..."
}
```

## Security Best Practices

1. **Never Log PII Values**: All logging must mask or exclude PII values
2. **Encrypt in Transit**: Use TLS 1.2+ for all data transmission
3. **Minimize PII Exposure**: Only decrypt PII when absolutely necessary
4. **Audit All Access**: Log every PII access event with user context
5. **Key Rotation**: Rotate KMS keys annually
6. **Least Privilege**: Grant minimum required permissions for PII access
7. **Secure Key Storage**: Never store encryption keys in application code
8. **Data Retention**: Encrypt PII in archived data (S3 Glacier)

## Compliance Considerations

### Regulatory Requirements
- **GLBA (Gramm-Leach-Bliley Act)**: Financial institution data protection
- **FCRA (Fair Credit Reporting Act)**: Consumer credit information protection
- **State Privacy Laws**: California CCPA, Virginia CDPA, etc.

### Encryption Standards
- **NIST SP 800-57**: Key management recommendations
- **FIPS 140-2**: Cryptographic module standards
- **PCI DSS**: Payment card industry data security (if applicable)

## Testing Requirements

### Unit Tests
- Test PII detection for all supported types
- Test encryption/decryption round-trip
- Test key rotation handling
- Test error handling for encryption failures

### Integration Tests
- Test end-to-end PII workflow
- Test role-based access control
- Test audit trail logging
- Test KMS integration

### Security Tests
- Test unauthorized PII access attempts
- Test encryption key exposure prevention
- Test audit trail completeness
- Test data masking in logs

## Migration Plan (Task 23.3)

### Phase 1: Infrastructure Setup
1. Create KMS Customer Master Key (CMK)
2. Configure key policies and IAM roles
3. Enable automatic key rotation
4. Set up CloudWatch alarms for key usage

### Phase 2: Encryption Implementation
1. Implement encryption utility functions
2. Implement decryption utility functions
3. Add encryption to data extraction workflow
4. Update DynamoDB schema

### Phase 3: Access Control
1. Implement role-based PII access
2. Add PII masking to API responses
3. Implement audit trail logging
4. Add MFA requirement for admin PII access

### Phase 4: Testing and Validation
1. Run comprehensive test suite
2. Perform security audit
3. Validate compliance requirements
4. Load testing with encrypted data

### Phase 5: Deployment
1. Deploy to staging environment
2. Migrate existing data (if any)
3. Validate production readiness
4. Deploy to production
5. Monitor and validate

## References

- AWS Comprehend PII Detection: https://docs.aws.amazon.com/comprehend/latest/dg/how-pii.html
- AWS KMS Best Practices: https://docs.aws.amazon.com/kms/latest/developerguide/best-practices.html
- DynamoDB Encryption at Rest: https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/encryption.howitworks.html
- NIST Encryption Standards: https://csrc.nist.gov/publications/detail/sp/800-57-part-1/rev-5/final

## Contact

For questions about field-level encryption implementation, contact the security team or refer to Task 23.3 in the project specification.
