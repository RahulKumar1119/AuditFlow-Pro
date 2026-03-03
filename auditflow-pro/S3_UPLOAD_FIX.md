# S3 Upload Fix - Checksum Policy Mismatch

## Problem
File uploads to S3 were failing with a 403 Forbidden error:
```
AccessDenied: Invalid according to Policy: Extra input fields: x-amz-checksum-sha256
```

## Root Cause
The issue occurred in three stages:

1. **Initial Problem**: The frontend was sending `x-amz-checksum-sha256` in the S3 POST request for file integrity verification, but the backend's presigned POST policy didn't include this field in the allowed conditions. S3 strictly validates that all fields in the POST request match what's defined in the policy.

2. **Secondary Problem**: After fixing the backend to include the checksum in the policy, the frontend was appending `x-amz-checksum-sha256` twice:
   - Once from the backend's `upload_fields` (which now included it)
   - Once manually in the frontend code (line 73 of UploadZone.tsx)
   
   This caused S3 to reject the upload with a duplicate field error.

3. **IAM Permissions Problem**: After fixing the duplicate checksum issue, uploads failed with an IAM permissions error. The Lambda function's IAM role policy was referencing the wrong S3 bucket name (`auditflow-documents-ap-south-1-438097524343` instead of `auditflow-documents-prod-438097524343`), preventing the Lambda from generating valid presigned URLs.

## Solution

### Issue Analysis
The problem occurred in two stages:
1. **Initial Issue**: Backend's presigned POST policy didn't include `x-amz-checksum-sha256` field
2. **Secondary Issue**: After backend fix, frontend was appending the checksum field twice - once from backend's `upload_fields` and once manually

### Changes Made

#### Backend Fix
**File**: `auditflow-pro/backend/functions/api_handler/app.py`

Modified the `handle_post_documents` function to:
1. Extract the checksum from the request body
2. Conditionally add `x-amz-checksum-sha256` to both the `Fields` and `Conditions` of the presigned POST policy

```python
# Extract checksum from request body if provided (for integrity verification)
checksum = body.get('checksum')

# Build fields and conditions
fields = {
    "Content-Type": content_type,
    "x-amz-server-side-encryption": "AES256",
    "acl": "private"
}

conditions = [
    {"Content-Type": content_type},
    ["content-length-range", 1, MAX_FILE_SIZE],
    {"x-amz-server-side-encryption": "AES256"},
    {"acl": "private"}
]

# If checksum is provided, add it to the policy to allow frontend to send it
if checksum:
    fields["x-amz-checksum-sha256"] = checksum
    conditions.append({"x-amz-checksum-sha256": checksum})
```

#### Frontend Fix
**File**: `auditflow-pro/frontend/src/components/upload/UploadZone.tsx`

Removed the manual append of `x-amz-checksum-sha256` on line 73, since the backend now includes it in `upload_fields`:

```typescript
// Before (line 73):
formData.append('x-amz-checksum-sha256', checksum);
formData.append('file', uploadRecord.file);

// After:
// Note: checksum is already included in upload_fields from backend
// No need to append it again here
formData.append('file', uploadRecord.file);
```

#### IAM Policy Fix
**IAM Role**: `AuditFlowAPIHandlerRole`

Updated the inline policy `APIHandlerAccessPolicy` to reference the correct S3 bucket name:

```json
{
  "Effect": "Allow",
  "Action": [
    "s3:GetObject",
    "s3:PutObject",
    "s3:ListBucket"
  ],
  "Resource": [
    "arn:aws:s3:::auditflow-documents-prod-438097524343",
    "arn:aws:s3:::auditflow-documents-prod-438097524343/*"
  ]
}
```

Previously, the policy incorrectly referenced `auditflow-documents-ap-south-1-438097524343`.

## Deployment

### Backend (Lambda Function)
The Lambda function has been updated and deployed:
```bash
aws lambda update-function-code \
  --function-name AuditFlowAPIHandler \
  --zip-file fileb://auditflow-pro/backend/functions/api_handler/api_handler.zip \
  --region ap-south-1
```

Status: ✅ Successful

### IAM Policy Update
The Lambda function's IAM role policy has been updated to reference the correct S3 bucket:
```bash
aws iam put-role-policy \
  --role-name AuditFlowAPIHandlerRole \
  --policy-name APIHandlerAccessPolicy \
  --policy-document file://auditflow-pro/fix-iam-policy.json \
  --region ap-south-1
```

Status: ✅ Successful

### Frontend (React App)
The frontend changes have been committed and deployed via AWS Amplify:
- Commit: `1688011` - "Fix S3 upload checksum policy mismatch - remove duplicate checksum field"
- Amplify Job ID: #35
- Status: ✅ Successful
- Deployed to: https://www.auditflowpro.online

## Testing
You can now test the file upload by:
1. Navigate to https://www.auditflowpro.online/upload
2. Select a PDF file (e.g., "PERSONAL LOAN APPLICATION FORM.pdf")
3. The upload should now complete successfully without the 403 error

## Technical Details
- The frontend calculates SHA-256 checksums using the Web Crypto API
- The checksum is sent to the backend when requesting the presigned URL
- The backend includes the checksum in the S3 policy, allowing S3 to verify file integrity
- This ensures end-to-end data integrity from browser to S3
