# CloudWatch Debugging Guide - Applicant Name Issue

**Goal:** Find and analyze CloudWatch logs to verify if applicant names are being extracted

---

## Method 1: AWS Console (Easiest)

### Step 1: Open CloudWatch Console

1. Go to **AWS Console** → Search for **CloudWatch**
2. Click **CloudWatch** service
3. In left sidebar, click **Logs** → **Log Groups**

### Step 2: Find Validator Lambda Logs

1. Search for log group: `AuditFlow-DocumentValidator` or `/aws/lambda/AuditFlow-DocumentValidator`
2. Click on the log group
3. You'll see **Log Streams** (one per Lambda execution)

### Step 3: Search for "Extracted name" Messages

1. Click **Search log group** (magnifying glass icon)
2. Enter search query: `Extracted name`
3. Click **Search**

**Expected Output:**
```
[INFO] Extracted name 'John Doe' from document doc-123
[INFO] Extracted name 'Jane Smith' from document doc-456
```

### Step 4: Analyze Results

If you see these messages:
- ✅ **GOOD:** Validator is extracting names correctly
- ✅ **NEXT STEP:** Check if golden_record has 'name' field

If you DON'T see these messages:
- ❌ **PROBLEM:** Validator is not finding name fields in extracted_data
- ❌ **NEXT STEP:** Check Extractor logs to verify extraction

---

## Method 2: AWS CLI (For Automation)

### Step 1: List Log Groups

```bash
aws logs describe-log-groups --query 'logGroups[*].logGroupName' | grep -i validator
```

**Output:**
```
/aws/lambda/AuditFlow-DocumentValidator
```

### Step 2: Get Recent Log Streams

```bash
aws logs describe-log-streams \
  --log-group-name /aws/lambda/AuditFlow-DocumentValidator \
  --order-by LastEventTime \
  --descending \
  --max-items 5
```

### Step 3: Search for "Extracted name" in Logs

```bash
aws logs filter-log-events \
  --log-group-name /aws/lambda/AuditFlow-DocumentValidator \
  --filter-pattern "Extracted name" \
  --start-time $(date -d '1 hour ago' +%s)000
```

**Output:**
```json
{
  "events": [
    {
      "timestamp": 1711100000000,
      "message": "[INFO] Extracted name 'John Doe' from document doc-123"
    }
  ]
}
```

### Step 4: Get Full Log Stream

```bash
aws logs get-log-events \
  --log-group-name /aws/lambda/AuditFlow-DocumentValidator \
  --log-stream-name '2026/03/22/[$LATEST]abc123def456'
```

---

## Method 3: CloudWatch Insights (Advanced Queries)

### Step 1: Open CloudWatch Insights

1. Go to **CloudWatch** → **Logs** → **Insights**
2. Select log group: `/aws/lambda/AuditFlow-DocumentValidator`
3. Set time range: **Last 1 hour** (or adjust as needed)

### Step 2: Run Query to Find Name Extraction

```sql
fields @timestamp, @message
| filter @message like /Extracted name/
| stats count() as extraction_count by @message
```

**Output:**
```
extraction_count | @message
5                | Extracted name 'John Doe' from document doc-123
3                | Extracted name 'Jane Smith' from document doc-456
```

### Step 3: Find Missing Name Extractions

```sql
fields @timestamp, @message, @logStream
| filter @message like /No valid documents loaded/
| stats count() as failures
```

### Step 4: Check for Errors

```sql
fields @timestamp, @message, @logStream
| filter @message like /error|Error|ERROR/
| stats count() as error_count by @message
```

---

## Method 4: Check All Lambda Functions in Sequence

### Step 1: Classifier Logs

Search for: `Document classified as`

```bash
aws logs filter-log-events \
  --log-group-name /aws/lambda/AuditFlow-DocumentClassifier \
  --filter-pattern "Document classified as"
```

**Expected:** Should see document type classification

### Step 2: Extractor Logs

Search for: `Extracted employee_name`

```bash
aws logs filter-log-events \
  --log-group-name /aws/lambda/AuditFlow-DataExtractor \
  --filter-pattern "Extracted employee_name"
```

**Expected:** Should see extracted names

### Step 3: Validator Logs

Search for: `Extracted name`

```bash
aws logs filter-log-events \
  --log-group-name /aws/lambda/AuditFlow-DocumentValidator \
  --filter-pattern "Extracted name"
```

**Expected:** Should see names from validator

### Step 4: Reporter Logs

Search for: `applicant_name`

```bash
aws logs filter-log-events \
  --log-group-name /aws/lambda/AuditFlow-ReportGenerator \
  --filter-pattern "applicant_name"
```

**Expected:** Should see applicant name in audit record

---

## Complete Debugging Workflow

### Step 1: Upload a Test PDF

1. Upload a W2 PDF with clear applicant name
2. Note the **Loan ID** and **Document ID**
3. Wait 30 seconds for processing

### Step 2: Check Classifier Logs

```bash
aws logs filter-log-events \
  --log-group-name /aws/lambda/AuditFlow-DocumentClassifier \
  --filter-pattern "Document classified" \
  --start-time $(date -d '5 minutes ago' +%s)000
```

**Look for:**
```
Document classified as W2 with confidence 0.95
```

### Step 3: Check Extractor Logs

```bash
aws logs filter-log-events \
  --log-group-name /aws/lambda/AuditFlow-DataExtractor \
  --filter-pattern "Extracted employee_name" \
  --start-time $(date -d '5 minutes ago' +%s)000
```

**Look for:**
```
Extracted employee_name: John Doe (confidence: 0.95)
```

### Step 4: Check Validator Logs

```bash
aws logs filter-log-events \
  --log-group-name /aws/lambda/AuditFlow-DocumentValidator \
  --filter-pattern "Extracted name" \
  --start-time $(date -d '5 minutes ago' +%s)000
```

**Look for:**
```
Extracted name 'John Doe' from document doc-123
Golden Record generated with X fields
```

### Step 5: Check Reporter Logs

```bash
aws logs filter-log-events \
  --log-group-name /aws/lambda/AuditFlow-ReportGenerator \
  --filter-pattern "applicant_name" \
  --start-time $(date -d '5 minutes ago' +%s)000
```

**Look for:**
```
Audit Complete. AuditRecordID: audit-xxx, RiskScore: 50
```

### Step 6: Query DynamoDB

```bash
aws dynamodb get-item \
  --table-name AuditFlow-AuditRecords \
  --key '{"audit_record_id":{"S":"audit-xxx"}}'
```

**Check for:**
```json
{
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

---

## Troubleshooting Guide

### Issue: No "Extracted name" Messages Found

**Possible Causes:**
1. Validator Lambda not running
2. Extracted data not being passed to Validator
3. Name fields not in extracted_data

**Debug Steps:**
```bash
# Check if Validator is being invoked
aws logs filter-log-events \
  --log-group-name /aws/lambda/AuditFlow-DocumentValidator \
  --filter-pattern "Starting validation"

# Check for errors
aws logs filter-log-events \
  --log-group-name /aws/lambda/AuditFlow-DocumentValidator \
  --filter-pattern "error"

# Check if documents are being loaded
aws logs filter-log-events \
  --log-group-name /aws/lambda/AuditFlow-DocumentValidator \
  --filter-pattern "Loaded document"
```

### Issue: "No valid documents loaded" Error

**Possible Causes:**
1. Documents missing document_id
2. Documents not marked as COMPLETED
3. Documents have no extracted_data

**Debug Steps:**
```bash
# Check for this specific error
aws logs filter-log-events \
  --log-group-name /aws/lambda/AuditFlow-DocumentValidator \
  --filter-pattern "No valid documents loaded"

# Check document processing status
aws logs filter-log-events \
  --log-group-name /aws/lambda/AuditFlow-DocumentValidator \
  --filter-pattern "processing_status"
```

### Issue: Extractor Not Extracting Names

**Possible Causes:**
1. PDF quality too low
2. Name field not recognized by Textract
3. Confidence score too low

**Debug Steps:**
```bash
# Check Extractor logs
aws logs filter-log-events \
  --log-group-name /aws/lambda/AuditFlow-DataExtractor \
  --filter-pattern "employee_name"

# Check for low confidence
aws logs filter-log-events \
  --log-group-name /aws/lambda/AuditFlow-DataExtractor \
  --filter-pattern "confidence"
```

---

## Quick Reference: Key Log Messages

| Component | Log Message | Meaning |
|-----------|-------------|---------|
| Classifier | `Document classified as W2` | Document type identified |
| Extractor | `Extracted employee_name: John Doe` | Name extracted from W2 |
| Validator | `Extracted name 'John Doe' from document` | Name found in validator |
| Validator | `Golden Record generated with X fields` | Golden record created |
| Reporter | `Audit Complete. AuditRecordID: audit-xxx` | Audit record saved |

---

## Step-by-Step: Find Your Specific Audit

### 1. Get Loan ID from UI
From the audit queue, note the **Loan ID** (e.g., `loan-cd188bed`)

### 2. Search for This Loan in Logs

```bash
aws logs filter-log-events \
  --log-group-name /aws/lambda/AuditFlow-DocumentValidator \
  --filter-pattern "loan-cd188bed" \
  --start-time $(date -d '24 hours ago' +%s)000
```

### 3. Find the Audit Record ID

Look for output like:
```
[INFO] Starting validation for loan application loan-cd188bed with 2 documents
```

### 4. Search for Audit Record ID

```bash
aws logs filter-log-events \
  --log-group-name /aws/lambda/AuditFlow-ReportGenerator \
  --filter-pattern "audit-xxx" \
  --start-time $(date -d '24 hours ago' +%s)000
```

### 5. Check DynamoDB with Audit ID

```bash
aws dynamodb get-item \
  --table-name AuditFlow-AuditRecords \
  --key '{"audit_record_id":{"S":"audit-xxx"}}'
```

---

## Export Logs for Analysis

### Export to CSV

```bash
aws logs filter-log-events \
  --log-group-name /aws/lambda/AuditFlow-DocumentValidator \
  --filter-pattern "Extracted name" \
  --query 'events[*].[timestamp,message]' \
  --output text > validator_logs.txt
```

### Export to JSON

```bash
aws logs filter-log-events \
  --log-group-name /aws/lambda/AuditFlow-DocumentValidator \
  --filter-pattern "Extracted name" \
  --output json > validator_logs.json
```

---

## Summary

**To check if applicant names are being extracted:**

1. **Quick Check (Console):**
   - CloudWatch → Logs → Log Groups
   - Search `/aws/lambda/AuditFlow-DocumentValidator`
   - Search for "Extracted name"

2. **CLI Check:**
   ```bash
   aws logs filter-log-events \
     --log-group-name /aws/lambda/AuditFlow-DocumentValidator \
     --filter-pattern "Extracted name"
   ```

3. **If Found:** ✅ Names are being extracted → Check DynamoDB
4. **If Not Found:** ❌ Names not extracted → Check Extractor logs

