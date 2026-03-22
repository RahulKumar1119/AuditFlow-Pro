# Fix: Applicant Name Not Displaying in Audit Queue

**Issue:** Applicant names showing as "Unknown Applicant" instead of actual names from PDF uploads

**Root Cause:** The extracted data from documents is not being properly passed through the Step Functions workflow, so the validator cannot find the name fields to populate the golden record

---

## Problem Analysis

### Current Flow:
1. PDF uploaded → Classifier extracts document type
2. Extractor extracts data (employee_name, first_name, last_name, etc.)
3. **ISSUE:** Extracted data not being passed to Validator
4. Validator creates golden record from extracted data (but data is missing)
5. Reporter uses golden record to populate applicant_name
6. Falls back to "Unknown Applicant" because golden_record['name'] is empty

### Why It Fails:
- The Step Functions workflow is not passing the extracted_data from the Extractor to the Validator
- Validator receives documents but without the extracted_data field
- name_candidates list remains empty
- Golden record has no 'name' field
- Reporter falls back to "Unknown Applicant"

---

## Solution

### The Real Issue:
The Step Functions workflow needs to pass the `extracted_data` from each document through to the Validator. Currently, the documents are being passed but without their extracted data.

### Step 1: Verify Step Functions Passes Extracted Data

**File:** `auditflow-pro/backend/functions/trigger/app.py` or Step Functions definition

The Step Functions workflow should pass documents with extracted_data:

```json
{
  "documents": [
    {
      "document_id": "doc-123",
      "document_type": "W2",
      "extracted_data": {
        "employee_name": {
          "value": "John Doe",
          "confidence": 0.95
        },
        "employer_name": {...},
        "wages": {...}
      }
    }
  ]
}
```

### Step 2: Verify Validator Receives Extracted Data

The validator is already set up to extract names from documents. Just ensure the extracted_data is being passed through.

In `validator/app.py`, the code already does this:

```python
for doc in documents:
    doc_type = doc.get('document_type')
    extracted_data = doc.get('extracted_data', {})  # ← This should have the data
    
    # Extract name field
    if doc_type == 'W2' and 'employee_name' in extracted_data:
        name_field = extracted_data['employee_name']
```

### Step 3: Verify Golden Record is Returned

The validator already returns the golden record with the name field:

```python
if name_candidates:
    golden_record['name'] = select_best_value(name_candidates)
```

### Step 4: Verify Reporter Uses Golden Record

The reporter already uses the golden record:

```python
if 'name' in golden_record and isinstance(golden_record['name'], dict):
    applicant_name = golden_record['name'].get('value', '').strip()
```

---

## Debugging Steps

### 1. Check CloudWatch Logs

Look for these log messages in CloudWatch:

**Extractor logs:**
```
Extracted employee_name: John Doe (confidence: 0.95)
```

**Validator logs:**
```
Extracted name 'John Doe' from document doc-123
Golden Record generated with X fields
```

**Reporter logs:**
```
Audit Complete. AuditRecordID: audit-xxx, RiskScore: 50
```

### 2. Check DynamoDB Audit Record

Query the AuditFlow-AuditRecords table and check:
- Is `applicant_name` field populated?
- Is `golden_record.name.value` populated?

### 3. Check Step Functions Execution

In AWS Step Functions console:
- View the execution history
- Check the input/output of each state
- Verify `extracted_data` is being passed from Extractor to Validator

---

## Quick Fix Checklist

- [ ] Verify Extractor is extracting employee_name correctly
- [ ] Verify Step Functions passes extracted_data to Validator
- [ ] Verify Validator receives extracted_data in documents
- [ ] Verify Validator generates golden_record with 'name' field
- [ ] Verify Reporter receives golden_record with 'name' field
- [ ] Check CloudWatch logs for any errors
- [ ] Test with a new PDF upload
- [ ] Verify applicant name appears in audit queue

---

## Implementation Steps

### 1. Update Validator Function

Add the `extract_applicant_name_from_documents()` function to `validator/app.py`

### 2. Update Lambda Handler

Modify the `lambda_handler` in `validator/app.py` to:
- Call `extract_applicant_name_from_documents()`
- Include golden record in response with applicant name

### 3. Test the Fix

```bash
# Upload a test PDF with applicant name
# Check that applicant name appears in audit queue

# Expected: "John Doe" instead of "Unknown Applicant"
```

---

## Expected Result

After implementing this fix:

| Before | After |
|--------|-------|
| Unknown Applicant | John Doe |
| Unknown Applicant | Jane Smith |
| Unknown Applicant | Robert Johnson |

---

## Files to Modify

1. `auditflow-pro/backend/functions/validator/app.py`
   - Add `extract_applicant_name_from_documents()` function
   - Update `lambda_handler()` to populate golden record with applicant name

---

## Testing

### Manual Test:
1. Upload a W2 PDF with employee name "John Doe"
2. Check audit queue
3. Verify applicant name shows as "John Doe" (not "Unknown Applicant")

### Automated Test:
```python
def test_applicant_name_extraction():
    documents = [
        {
            'document_id': 'doc-1',
            'document_type': 'W2',
            'extracted_data': {
                'employee_name': {
                    'value': 'John Doe',
                    'confidence': 0.95
                }
            }
        }
    ]
    
    result = extract_applicant_name_from_documents(documents)
    assert result['name']['value'] == 'John Doe'
    assert result['name']['confidence'] == 0.95
```

---

## Priority

**HIGH** - This is a critical user-facing issue affecting the audit queue display

