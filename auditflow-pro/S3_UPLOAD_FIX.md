# S3 Upload Fix - Checksum Policy Mismatch

## Problem
File uploads to S3 were failing with a 403 Forbidden error:
```
AccessDenied: Invalid according to Policy: Extra input fields: x-amz-checksum-sha256
```

## Root Cause
The frontend was sending `x-amz-checksum-sha256` in the S3 POST request for file integrity verification, but the backend's presigned POST policy didn't include this field in the allowed conditions. S3 strictly validates that all fields in the POST request match what's defined in the policy.

## Solution
Updated the backend Lambda function (`AuditFlowAPIHandler`) to include the checksum field in the presigned POST policy when provided by the frontend.

### Changes Made
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

## Deployment
The Lambda function has been updated and deployed:
```bash
aws lambda update-function-code \
  --function-name AuditFlowAPIHandler \
  --zip-file fileb://auditflow-pro/backend/functions/api_handler/api_handler.zip \
  --region ap-south-1
```

Status: ✅ Successful

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
