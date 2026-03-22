# Step Functions Data Flow Diagram & Verification Points

---

## Complete Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         STEP FUNCTIONS WORKFLOW                             │
└─────────────────────────────────────────────────────────────────────────────┘

                                    START
                                      │
                                      ▼
                    ┌──────────────────────────────┐
                    │   S3 Upload Trigger          │
                    │  (Trigger Lambda)            │
                    └──────────────────────────────┘
                                      │
                    ┌─────────────────┴─────────────────┐
                    │ Payload:                          │
                    │ {                                 │
                    │   "loan_application_id": "...",   │
                    │   "documents": [{                 │
                    │     "document_id": "...",         │
                    │     "s3_bucket": "...",           │
                    │     "s3_key": "..."               │
                    │   }]                              │
                    │ }                                 │
                    └───────────────────────────────────┘
                                      │
                                      ▼
                    ┌──────────────────────────────┐
                    │   Classifier Lambda          │
                    │  (Classify Document Type)    │
                    └──────────────────────────────┘
                                      │
                    ┌─────────────────┴─────────────────┐
                    │ Output:                           │
                    │ {                                 │
                    │   "document_id": "...",           │
                    │   "document_type": "W2",          │
                    │   "s3_bucket": "...",             │
                    │   "s3_key": "..."                 │
                    │ }                                 │
                    └───────────────────────────────────┘
                                      │
                    ┌─────────────────┴─────────────────┐
                    │ ResultPath: "$.document"          │
                    │ (Merge with input)                │
                    └───────────────────────────────────┘
                                      │
                                      ▼
                    ┌──────────────────────────────┐
                    │   Extractor Lambda           │
                    │  (Extract Data from PDF)     │
                    └──────────────────────────────┘
                                      │
                    ┌─────────────────┴─────────────────┐
                    │ Output:                           │
                    │ {                                 │
                    │   "document_id": "...",           │
                    │   "document_type": "W2",          │
                    │   "extracted_data": {             │
                    │     "employee_name": {            │
                    │       "value": "John Doe",        │
                    │       "confidence": 0.95          │
                    │     },                            │
                    │     "employer_name": {...},       │
                    │     "wages": {...}                │
                    │   },                              │
                    │   "processing_status": "COMPLETED"│
                    │ }                                 │
                    └───────────────────────────────────┘
                                      │
                    ┌─────────────────┴─────────────────┐
                    │ ResultPath: "$.document"          │
                    │ (Merge with input)                │
                    │ ✓ CRITICAL: extracted_data        │
                    │   must be passed through!         │
                    └───────────────────────────────────┘
                                      │
                                      ▼
                    ┌──────────────────────────────┐
                    │   Validator Lambda           │
                    │  (Validate & Generate        │
                    │   Golden Record)             │
                    └──────────────────────────────┘
                                      │
                    ┌─────────────────┴─────────────────┐
                    │ Input:                            │
                    │ {                                 │
                    │   "loan_application_id": "...",   │
                    │   "documents": [{                 │
                    │     "document_id": "...",         │
                    │     "document_type": "W2",        │
                    │     "extracted_data": {           │
                    │       "employee_name": {...}      │
                    │     }                             │
                    │   }]                              │
                    │ }                                 │
                    │                                   │
                    │ ✓ MUST HAVE extracted_data!       │
                    └───────────────────────────────────┘
                                      │
                    ┌─────────────────┴─────────────────┐
                    │ Output:                           │
                    │ {                                 │
                    │   "golden_record": {              │
                    │     "name": {                     │
                    │       "value": "John Doe",        │
                    │       "confidence": 0.95          │
                    │     }                             │
                    │   },                              │
                    │   "inconsistencies": [...]        │
                    │ }                                 │
                    └───────────────────────────────────┘
                                      │
                                      ▼
                    ┌──────────────────────────────┐
                    │   Reporter Lambda            │
                    │  (Generate Audit Record)     │
                    └──────────────────────────────┘
                                      │
                    ┌─────────────────┴─────────────────┐
                    │ Input:                            │
                    │ {                                 │
                    │   "golden_record": {              │
                    │     "name": {                     │
                    │       "value": "John Doe"         │
                    │     }                             │
                    │   }                               │
                    │ }                                 │
                    │                                   │
                    │ Extracts: applicant_name =        │
                    │   "John Doe"                      │
                    └───────────────────────────────────┘
                                      │
                                      ▼
                    ┌──────────────────────────────┐
                    │   Save to DynamoDB           │
                    │  (AuditFlow-AuditRecords)    │
                    └──────────────────────────────┘
                                      │
                    ┌─────────────────┴─────────────────┐
                    │ Record:                           │
                    │ {                                 │
                    │   "audit_record_id": "...",       │
                    │   "applicant_name": "John Doe",   │
                    │   "golden_record": {...}          │
                    │ }                                 │
                    │                                   │
                    │ ✓ applicant_name populated!       │
                    └───────────────────────────────────┘
                                      │
                                      ▼
                                    END
```

---

## Verification Points

### ✓ Point 1: Extractor Output

**Location:** Step Functions Execution History → Extractor State → Output

**What to check:**
```json
{
  "document_id": "doc-123",
  "document_type": "W2",
  "extracted_data": {
    "employee_name": {
      "value": "John Doe",
      "confidence": 0.95
    }
  },
  "processing_status": "COMPLETED"
}
```

**Success Criteria:**
- ✓ `extracted_data` field exists
- ✓ `employee_name` is in `extracted_data`
- ✓ `value` and `confidence` are populated

**Failure Indicators:**
- ✗ `extracted_data` is null or missing
- ✗ `employee_name` is missing
- ✗ `value` is empty

---

### ✓ Point 2: Validator Input

**Location:** Step Functions Execution History → Validator State → Input

**What to check:**
```json
{
  "loan_application_id": "loan-123",
  "documents": [
    {
      "document_id": "doc-123",
      "document_type": "W2",
      "extracted_data": {
        "employee_name": {
          "value": "John Doe",
          "confidence": 0.95
        }
      }
    }
  ]
}
```

**Success Criteria:**
- ✓ `documents` array exists
- ✓ `documents[0]` has `extracted_data` field
- ✓ `extracted_data` matches Extractor output

**Failure Indicators:**
- ✗ `extracted_data` is missing from documents
- ✗ `extracted_data` is null or empty
- ✗ `employee_name` is missing

**⚠️ CRITICAL:** If Validator input is missing `extracted_data`, the Step Functions state machine is not properly configured!

---

### ✓ Point 3: Validator Output

**Location:** Step Functions Execution History → Validator State → Output

**What to check:**
```json
{
  "golden_record": {
    "name": {
      "value": "John Doe",
      "source_document": "doc-123",
      "confidence": 0.95
    }
  },
  "inconsistencies": []
}
```

**Success Criteria:**
- ✓ `golden_record` exists
- ✓ `golden_record.name` exists
- ✓ `name.value` is populated

**Failure Indicators:**
- ✗ `golden_record` is missing
- ✗ `name` field is missing
- ✗ `value` is empty

---

### ✓ Point 4: CloudWatch Logs - Extractor

**Location:** CloudWatch Logs → `/aws/lambda/AuditFlow-DataExtractor`

**What to search for:**
```
Extracted employee_name: John Doe (confidence: 0.95)
```

**Success Criteria:**
- ✓ Log message appears
- ✓ Employee name is shown
- ✓ Confidence score is shown

**Failure Indicators:**
- ✗ No extraction messages
- ✗ Error messages about Textract
- ✗ Low confidence scores

---

### ✓ Point 5: CloudWatch Logs - Validator

**Location:** CloudWatch Logs → `/aws/lambda/AuditFlow-DocumentValidator`

**What to search for:**
```
Extracted name 'John Doe' from document doc-123
Golden Record generated with X fields
```

**Success Criteria:**
- ✓ "Extracted name" message appears
- ✓ Name matches Extractor output
- ✓ "Golden Record generated" message appears

**Failure Indicators:**
- ✗ "No valid documents loaded" error
- ✗ "has no extracted data" warning
- ✗ No "Extracted name" messages

---

### ✓ Point 6: DynamoDB Audit Record

**Location:** DynamoDB → `AuditFlow-AuditRecords` table

**What to check:**
```json
{
  "audit_record_id": {"S": "audit-123"},
  "loan_application_id": {"S": "loan-123"},
  "applicant_name": {"S": "John Doe"},
  "golden_record": {
    "M": {
      "name": {
        "M": {
          "value": {"S": "John Doe"},
          "confidence": {"N": "0.95"}
        }
      }
    }
  }
}
```

**Success Criteria:**
- ✓ `applicant_name` field exists
- ✓ `applicant_name` is not "Unknown Applicant"
- ✓ `applicant_name` matches extracted name

**Failure Indicators:**
- ✗ `applicant_name` is "Unknown Applicant"
- ✗ `applicant_name` is empty
- ✗ `golden_record.name` is missing

---

## Verification Workflow

```
START
  │
  ├─→ Check Extractor Output
  │   ├─ Has extracted_data? ──NO──→ ERROR: Extractor not returning data
  │   └─ Has employee_name? ──NO──→ ERROR: Extractor not extracting names
  │
  ├─→ Check Validator Input
  │   ├─ Has extracted_data? ──NO──→ ERROR: Step Functions not passing data
  │   └─ Matches Extractor? ──NO──→ ERROR: Data corruption in workflow
  │
  ├─→ Check Validator Output
  │   ├─ Has golden_record? ──NO──→ ERROR: Validator not generating record
  │   └─ Has name field? ──NO──→ ERROR: Validator not extracting names
  │
  ├─→ Check CloudWatch Logs
  │   ├─ Extractor logs OK? ──NO──→ ERROR: Check Extractor Lambda
  │   └─ Validator logs OK? ──NO──→ ERROR: Check Validator Lambda
  │
  ├─→ Check DynamoDB
  │   ├─ Has applicant_name? ──NO──→ ERROR: Reporter not populating field
  │   └─ Is "Unknown Applicant"? ──YES──→ ERROR: Golden record not used
  │
  └─→ SUCCESS: All checks passed!
```

---

## Common Issues & Fixes

### Issue 1: Validator Input Missing `extracted_data`

**Symptom:**
```
Validator Input:
{
  "documents": [{
    "document_id": "doc-123",
    "document_type": "W2"
    // ✗ Missing extracted_data!
  }]
}
```

**Root Cause:** Step Functions state machine not merging Extractor output

**Fix:**
1. Check Step Functions state machine definition
2. Ensure Extractor state has `ResultPath: "$.document"`
3. Verify Validator state receives merged document

**Example Correct Configuration:**
```json
{
  "ExtractData": {
    "Type": "Task",
    "Resource": "arn:aws:lambda:...:function:AuditFlow-DataExtractor",
    "ResultPath": "$.document",  // ← CRITICAL
    "Next": "ValidateDocuments"
  }
}
```

---

### Issue 2: Validator Logs Show "No valid documents loaded"

**Symptom:**
```
[ERROR] No valid documents loaded for loan application loan-123
[WARNING] Document doc-123 has no extracted data
```

**Root Cause:** Validator receiving documents without `extracted_data`

**Fix:**
1. Verify Step Functions is passing `extracted_data`
2. Check Extractor is returning `extracted_data`
3. Verify `ResultPath` configuration

---

### Issue 3: DynamoDB Has "Unknown Applicant"

**Symptom:**
```json
{
  "applicant_name": {"S": "Unknown Applicant"}
}
```

**Root Cause:** Golden record not being used or name not extracted

**Fix:**
1. Check Validator output has `golden_record.name`
2. Check Reporter is receiving golden record
3. Verify Reporter Lambda is using golden record

---

## Quick Decision Tree

```
Is applicant_name showing correctly?
│
├─ YES → ✓ Everything is working!
│
└─ NO → Check:
    │
    ├─ Is it "Unknown Applicant"?
    │  └─ YES → Golden record not being used
    │          Check Reporter Lambda
    │
    ├─ Is it empty?
    │  └─ YES → Audit record not being saved
    │          Check Reporter Lambda logs
    │
    └─ Is it wrong name?
       └─ YES → Wrong name being extracted
               Check Validator output
               Check golden_record.name
```

---

## Summary

**To verify Step Functions data flow:**

1. **Check Extractor Output** - Has `extracted_data`?
2. **Check Validator Input** - Received `extracted_data`?
3. **Check Validator Output** - Generated `golden_record.name`?
4. **Check CloudWatch Logs** - Any errors?
5. **Check DynamoDB** - Has `applicant_name`?

**If all checks pass:** ✓ Data flow is correct

**If any check fails:** ✗ See troubleshooting section

