# S3 Bucket Configuration for AuditFlow-Pro

## Overview

This document describes the S3 bucket configuration for the AuditFlow-Pro loan document auditor system. The S3 bucket stores uploaded loan documents with banking-grade security including encryption at rest, secure transport, and automated lifecycle management.

## Bucket Details

- **Bucket Name**: `auditflow-documents-prod-{ACCOUNT_ID}`
- **Region**: `ap-south-1` (Asia Pacific - Mumbai)
- **Purpose**: Store uploaded loan documents (W2s, bank statements, tax forms, driver's licenses, ID documents)

## Security Configuration

### 1. Encryption at Rest

**KMS Encryption**:
- All objects are encrypted using AWS KMS (Key Management Service)
- Encryption algorithm: AES-256
- KMS Key: `alias/auditflow-s3-encryption`
- Bucket key enabled for cost optimization
- Automatic key rotation: Enabled (annual)

**Requirements Satisfied**:
- Requirement 1.2: Store documents in encrypted S3 bucket
- Requirement 1.6: Apply encryption at rest using KMS
- Requirement 16.1: Encrypt all data at rest using KMS with AES-256
- Requirement 16.3: S3 bucket shall enforce server-side encryption

### 2. Encryption in Transit

**TLS/HTTPS Enforcement**:
- All S3 API calls must use HTTPS (TLS 1.2+)
- Bucket policy denies all requests over insecure transport
- Pre-signed URLs are generated with HTTPS only

**Requirements Satisfied**:
- Requirement 2.8: Transmit all authentication data using encryption in transit
- Requirement 16.2: Encrypt all data in transit using TLS 1.2 or higher

### 3. Bucket Policies

**Access Control**:
- Deny unencrypted object uploads (enforce KMS encryption)
- Deny insecure transport (HTTP requests blocked)
- Allow Lambda execution role to read/write objects
- Block all public access

**Policy Rules**:
1. **DenyUnencryptedObjectUploads**: Rejects PUT requests without KMS encryption
2. **DenyInsecureTransport**: Blocks all HTTP requests (requires HTTPS)
3. **AllowLambdaAccess**: Grants Lambda functions read/write permissions
4. **AllowLambdaListBucket**: Grants Lambda functions list bucket permissions

### 4. Public Access Block

All public access is blocked:
- BlockPublicAcls: true
- IgnorePublicAcls: true
- BlockPublicPolicy: true
- RestrictPublicBuckets: true

### 5. Versioning

**Configuration**:
- S3 versioning: Enabled
- Provides protection against accidental deletion
- Supports audit trail and compliance requirements

**Lifecycle Management**:
- Non-current versions are deleted after 30 days

## CORS Configuration

**Purpose**: Allow frontend dashboard to upload and view documents

**Allowed Methods**: GET, PUT, POST, HEAD
**Allowed Origins**: * (should be restricted to specific domain in production)
**Allowed Headers**: *
**Exposed Headers**: ETag, x-amz-server-side-encryption, x-amz-request-id
**Max Age**: 3000 seconds

**Requirements Satisfied**:
- Requirement 1.1: Provide drag-and-drop interface for uploading documents
- Requirement 14.1: Provide links to view original documents

## Lifecycle Policies

### Policy 1: Archive to Glacier

**Configuration**:
- **Transition**: Move objects to Glacier storage class after 90 days
- **Expiration**: Delete objects after 2555 days (7 years)
- **Status**: Enabled
- **Filter**: Applies to all objects (empty prefix)

**Requirements Satisfied**:
- Requirement 25.1: Move audit records older than 90 days to archival storage
- Requirement 25.2: Use S3 Glacier for archival storage
- Requirement 25.5: Delete archived records after 7 years

### Policy 2: Delete Old Versions

**Configuration**:
- **Non-current Version Expiration**: 30 days
- **Purpose**: Clean up old versions to reduce storage costs
- **Status**: Enabled

## Access Logging

**Configuration**:
- Server access logging: Enabled
- Log bucket: `auditflow-documents-prod-{ACCOUNT_ID}-logs`
- Log prefix: `s3-access-logs/`

**Purpose**:
- Audit trail for all S3 access
- Compliance and security monitoring
- Troubleshooting access issues

**Requirements Satisfied**:
- Requirement 18.1: Log all document uploads
- Requirement 18.4: Log all data access events

## File Format Support

**Supported Formats**:
- PDF (Portable Document Format)
- JPEG (Joint Photographic Experts Group)
- PNG (Portable Network Graphics)
- TIFF (Tagged Image File Format)

**File Size Limits**:
- Maximum file size: 50 MB per document
- Enforced at API Gateway level before S3 upload

**Requirements Satisfied**:
- Requirement 1.3: Support PDF, JPEG, PNG, and TIFF file formats
- Requirement 1.4: Display file size error when document exceeds 50MB

## Document Organization

**Folder Structure**:
```
auditflow-documents-prod-{ACCOUNT_ID}/
├── loans/
│   ├── {loan_application_id}/
│   │   ├── {document_id}_w2.pdf
│   │   ├── {document_id}_bank_statement.pdf
│   │   ├── {document_id}_tax_form.pdf
│   │   ├── {document_id}_drivers_license.jpg
│   │   └── {document_id}_id_document.jpg
│   └── ...
└── archived/
    └── {year}/
        └── {month}/
            └── ...
```

**Key Naming Convention**:
- Format: `loans/{loan_application_id}/{document_id}_{document_type}.{extension}`
- Document ID: UUID v4
- Document type: w2, bank_statement, tax_form, drivers_license, id_document

## Deployment Scripts

### 1. kms_setup.sh

**Purpose**: Create and configure KMS encryption keys

**Actions**:
- Creates KMS key for S3 encryption
- Creates KMS key for DynamoDB encryption
- Sets up key policies for service access
- Enables automatic key rotation
- Creates key aliases for easy reference

**Usage**:
```bash
bash infrastructure/kms_setup.sh
```

### 2. s3_bucket_policy.sh

**Purpose**: Configure S3 bucket security policies

**Actions**:
- Applies bucket policy to enforce encryption and secure transport
- Enables S3 versioning
- Blocks public access
- Configures access for Lambda execution role

**Usage**:
```bash
bash infrastructure/s3_bucket_policy.sh
```

### 3. s3_config.sh

**Purpose**: Configure S3 CORS and lifecycle policies

**Actions**:
- Configures CORS for frontend access
- Sets up lifecycle policy for Glacier archival
- Configures server access logging
- Creates logging bucket if needed

**Usage**:
```bash
bash infrastructure/s3_config.sh
```

### 4. deploy.sh

**Purpose**: Main deployment script that orchestrates all infrastructure setup

**Actions**:
- Calls kms_setup.sh to create encryption keys
- Creates S3 bucket with KMS encryption
- Calls s3_bucket_policy.sh to configure security
- Calls s3_config.sh to configure CORS and lifecycle
- Creates DynamoDB tables
- Creates IAM roles

**Usage**:
```bash
bash infrastructure/deploy.sh
```

## Monitoring and Alerts

**CloudWatch Metrics**:
- BucketSizeBytes: Monitor storage usage
- NumberOfObjects: Track document count
- AllRequests: Monitor API request volume
- 4xxErrors: Track client errors
- 5xxErrors: Track server errors

**CloudWatch Alarms** (to be configured):
- Alert when bucket size exceeds threshold
- Alert on high error rates
- Alert on unauthorized access attempts

**Requirements Satisfied**:
- Requirement 18.5: Log all API calls to AWS services
- Requirement 22.4: Send capacity alert when DynamoDB throttling occurs

## Compliance and Retention

**Data Retention**:
- Active storage: 90 days (S3 Standard)
- Archival storage: 7 years (S3 Glacier)
- Total retention: 7 years from upload date

**Compliance Features**:
- Encryption at rest and in transit
- Access logging and audit trails
- Versioning for data protection
- Automated lifecycle management
- Secure access controls

**Requirements Satisfied**:
- Requirement 12.5: Retain audit records for 7 years
- Requirement 25.6: Maintain encryption for archived data
- Requirement 25.7: Log all archival and deletion operations

## Cost Optimization

**Strategies**:
1. **Bucket Keys**: Reduce KMS API calls by 99%
2. **Lifecycle Policies**: Move to Glacier after 90 days (90% cost reduction)
3. **Version Cleanup**: Delete old versions after 30 days
4. **Intelligent Tiering**: Consider for variable access patterns

**Estimated Costs** (per 1000 documents):
- S3 Standard (0-90 days): ~$0.023/GB/month
- S3 Glacier (90 days - 7 years): ~$0.004/GB/month
- KMS: ~$1/month (with bucket keys)
- Data transfer: Varies by usage

## Troubleshooting

### Issue: Upload fails with "Access Denied"

**Possible Causes**:
- Lambda execution role lacks S3 permissions
- Bucket policy is too restrictive
- KMS key policy doesn't allow Lambda access

**Solution**:
- Verify IAM role has s3:PutObject permission
- Check bucket policy allows the role
- Verify KMS key policy includes Lambda role

### Issue: "Encryption header not provided"

**Cause**: Client not specifying server-side encryption

**Solution**:
- Ensure upload requests include `x-amz-server-side-encryption: aws:kms`
- Use AWS SDK with encryption configuration
- Bucket policy enforces KMS encryption

### Issue: CORS errors in browser

**Cause**: CORS configuration not applied or incorrect

**Solution**:
- Run `bash infrastructure/s3_config.sh` to apply CORS
- Verify CORS allows your frontend domain
- Check browser console for specific CORS error

## Security Best Practices

1. **Restrict CORS Origins**: Update CORS to allow only your frontend domain
2. **Enable MFA Delete**: Require MFA for object deletion
3. **Regular Key Rotation**: KMS keys rotate automatically annually
4. **Monitor Access Logs**: Review S3 access logs regularly
5. **Least Privilege**: Grant minimum required permissions to roles
6. **Encryption Verification**: Audit that all objects are encrypted

## References

- AWS S3 Documentation: https://docs.aws.amazon.com/s3/
- AWS KMS Documentation: https://docs.aws.amazon.com/kms/
- S3 Lifecycle Policies: https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lifecycle-mgmt.html
- S3 Encryption: https://docs.aws.amazon.com/AmazonS3/latest/userguide/UsingEncryption.html
