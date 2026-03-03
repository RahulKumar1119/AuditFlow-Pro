# Test Document Generator for AuditFlow

This script generates realistic PDF test documents for testing the AuditFlow document processing pipeline.

## Installation

```bash
pip install reportlab
```

## Usage

```bash
cd auditflow-pro
python3 generate_test_pdfs.py
```

## Generated Documents

The script creates a `test_documents/` directory with PDFs for three test applicants:

### 1. John Smith (Consistent Data - LOW RISK)
- `john_smith_w2.pdf` - W2 form with $85,000 wages
- `john_smith_bank_statement.pdf` - Bank statement
- `john_smith_1040.pdf` - Tax return with $85,000 AGI
- `john_smith_drivers_license.pdf` - Driver's license

All documents have consistent:
- Name: "John Smith"
- SSN: 123-45-6789
- Address: 123 Main Street, New York, NY 10001
- Income: $85,000

### 2. Jane Doe (Inconsistent Data - MEDIUM/HIGH RISK)
- `jane_doe_w2.pdf` - W2 with name "Jane M. Doe", $95,000 wages
- `jane_doe_bank_statement.pdf` - Bank statement with "Jane Doe", address variation
- `jane_doe_1040.pdf` - Tax return with "Jane Marie Doe", $92,000 AGI (income mismatch!)
- `jane_doe_drivers_license.pdf` - License with "Jane Marie Doe"

Inconsistencies:
- Name variations: "Jane M. Doe" vs "Jane Doe" vs "Jane Marie Doe"
- Address variations: "456 Oak Avenue" vs "456 Oak Ave"
- Income mismatch: W2 shows $95,000 but 1040 shows $92,000 AGI

### 3. Robert Johnson (High Income - LOW RISK)
- `robert_johnson_w2.pdf` - W2 with $150,000 wages
- `robert_johnson_bank_statement.pdf` - Bank statement with higher balances
- `robert_johnson_1040.pdf` - Tax return with $150,000 AGI
- `robert_johnson_drivers_license.pdf` - Driver's license

All documents have consistent data with high income.

## Testing the Pipeline

1. Generate the test documents:
   ```bash
   python3 generate_test_pdfs.py
   ```

2. Upload documents through the AuditFlow web interface:
   - Log in to your AuditFlow application
   - Navigate to "Upload Documents"
   - Upload all 4 documents for one applicant (same loan application ID)
   - Wait for processing to complete

3. Check the results:
   - View the Dashboard or Audit Records page
   - Click on the loan application to see the audit details
   - Review detected inconsistencies and risk scores

## Expected Results

- **John Smith**: Should show LOW risk with no inconsistencies
- **Jane Doe**: Should show MEDIUM/HIGH risk with name and income inconsistencies detected
- **Robert Johnson**: Should show LOW risk with no inconsistencies (high income is not a risk factor)

## Troubleshooting

If documents fail to process:
1. Check CloudWatch logs for the Lambda functions
2. Verify Step Functions execution in AWS Console
3. Check DynamoDB tables for document metadata
4. Review S3 bucket for uploaded files

## Notes

- All documents are clearly marked as "test documents for AuditFlow testing purposes only"
- SSNs and other identifiers are fake and for testing only
- The documents contain realistic formatting but simplified content
