# IAM Permission Fix for Step Functions DynamoDB Access

## Problem

Step Function execution failed with:
```
User: arn:aws:sts::438097524343:assumed-role/AuditFlowStepFunctionsRole/...
is not authorized to perform: dynamodb:PutItem on resource: 
arn:aws:dynamodb:ap-south-1:438097524343:table/AuditFlow-Documents
```

The `AuditFlowStepFunctionsRole` was missing DynamoDB permissions.

## Root Cause

The Step Functions role only had permissions to:
- Invoke Lambda functions
- Write CloudWatch logs

But did NOT have permissions to:
- `dynamodb:PutItem` - Save documents
- `dynamodb:GetItem` - Load documents
- `dynamodb:UpdateItem` - Update documents
- `dynamodb:Query` - Query documents
- `dynamodb:Scan` - Scan documents

## Solution

Added DynamoDB permissions to the `AuditFlowStepFunctionsRole` IAM role.

## How to Fix

### Option 1: Run the Quick Fix Script (Recommended)

```bash
cd auditflow-pro
bash infrastructure/fix_stepfunctions_role.sh
```

This adds the DynamoDB policy immediately.

### Option 2: Manual AWS CLI

```bash
aws iam put-role-policy \
  --role-name AuditFlowStepFunctionsRole \
  --policy-name DynamoDBAccessPolicy \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": [
          "dynamodb:PutItem",
          "dynamodb:GetItem",
          "dynamodb:UpdateItem",
          "dynamodb:Query",
          "dynamodb:Scan"
        ],
        "Resource": [
          "arn:aws:dynamodb:ap-south-1:438097524343:table/AuditFlow-Documents",
          "arn:aws:dynamodb:ap-south-1:438097524343:table/AuditFlow-Documents/index/*",
          "arn:aws:dynamodb:ap-south-1:438097524343:table/AuditFlow-AuditRecords",
          "arn:aws:dynamodb:ap-south-1:438097524343:table/AuditFlow-AuditRecords/index/*"
        ]
      }
    ]
  }'
```

### Option 3: Update IAM Policy Script

The `infrastructure/iam_policies.sh` script has been updated to include DynamoDB permissions. Run it to apply all policies:

```bash
cd auditflow-pro
bash infrastructure/iam_policies.sh
```

## Permissions Added

The role now has:

```json
{
  "Effect": "Allow",
  "Action": [
    "dynamodb:PutItem",
    "dynamodb:GetItem",
    "dynamodb:UpdateItem",
    "dynamodb:Query",
    "dynamodb:Scan"
  ],
  "Resource": [
    "arn:aws:dynamodb:ap-south-1:ACCOUNT:table/AuditFlow-Documents",
    "arn:aws:dynamodb:ap-south-1:ACCOUNT:table/AuditFlow-Documents/index/*",
    "arn:aws:dynamodb:ap-south-1:ACCOUNT:table/AuditFlow-AuditRecords",
    "arn:aws:dynamodb:ap-south-1:ACCOUNT:table/AuditFlow-AuditRecords/index/*"
  ]
}
```

## What This Enables

With these permissions, the Step Function can now:

1. **Save extracted documents** - `SaveDocumentMetadata` state uses `dynamodb:PutItem`
2. **Load documents for validation** - Validator Lambda uses `dynamodb:GetItem`
3. **Update document status** - Update processing status after validation
4. **Query documents** - Find documents by loan application
5. **Scan documents** - List all documents in a table

## Security

These permissions are:
- **Scoped to specific tables** - Only `AuditFlow-Documents` and `AuditFlow-AuditRecords`
- **Scoped to specific actions** - Only read/write operations, no delete/admin
- **Scoped to specific resource** - Only Step Functions service can assume this role
- **Least privilege** - Only permissions needed for the workflow

## Next Steps

1. Apply the IAM policy fix using one of the methods above
2. Retry the Step Function execution
3. Monitor CloudWatch logs for successful completion

## Verification

To verify the permissions were applied:

```bash
aws iam get-role-policy \
  --role-name AuditFlowStepFunctionsRole \
  --policy-name DynamoDBAccessPolicy
```

Should return the policy document with DynamoDB permissions.

## Related Files

- `auditflow-pro/infrastructure/fix_stepfunctions_role.sh` - Quick fix script (new)
- `auditflow-pro/infrastructure/iam_policies.sh` - Updated with DynamoDB permissions
- `auditflow-pro/backend/DYNAMODB_SAVE_FIX.md` - DynamoDB save implementation
- `auditflow-pro/backend/step_functions/state_machine.asl.json` - Updated state machine

## Summary

The Step Functions role now has full DynamoDB access needed to save and load documents during the audit pipeline execution. The fix is minimal, scoped, and follows AWS security best practices.
