# AuditFlow-Pro User Guide for Loan Officers

Complete guide for loan officers on how to use the AuditFlow-Pro system to upload documents and review audit results.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Logging In](#logging-in)
3. [Uploading Documents](#uploading-documents)
4. [Viewing Audit Queue](#viewing-audit-queue)
5. [Reviewing Audit Results](#reviewing-audit-results)
6. [Understanding Risk Scores](#understanding-risk-scores)
7. [Interpreting Inconsistencies](#interpreting-inconsistencies)
8. [Using Document Viewer](#using-document-viewer)
9. [FAQ](#faq)
10. [Support](#support)

---

## Getting Started

### System Requirements
- Modern web browser (Chrome, Firefox, Safari, Edge)
- Internet connection
- Adobe Reader (optional, for PDF viewing)

### Accessing AuditFlow-Pro
1. Open your web browser
2. Navigate to: https://auditflowpro.online
3. You will see the login page

### First Time Setup
- Contact your administrator for login credentials
- You will receive an email with temporary password
- Change your password on first login
- Set up multi-factor authentication (MFA) if required

---

## Logging In

### Standard Login
1. Enter your email address
2. Enter your password
3. Click "Sign In"
4. If MFA is enabled, enter the code from your authenticator app

### Forgot Password
1. Click "Forgot Password?" on login page
2. Enter your email address
3. Check your email for reset link
4. Click link and create new password
5. Return to login page and sign in

### Session Timeout
- Sessions expire after 30 minutes of inactivity
- You will be prompted to re-authenticate
- Your work is automatically saved

---

## Uploading Documents

### Supported Document Types
- **W2 Forms** - Wage and tax statements
- **Bank Statements** - Account statements with transactions
- **Tax Forms** - 1040, 1099, and other IRS forms
- **Driver's Licenses** - State-issued identification
- **ID Documents** - Passports, government IDs

### Supported File Formats
- PDF (.pdf)
- JPEG (.jpg, .jpeg)
- PNG (.png)
- TIFF (.tif, .tiff)

### File Size Limits
- Maximum file size: 50 MB
- Recommended: 5-20 MB for optimal processing

### Upload Process

#### Step 1: Navigate to Upload
1. Click "Upload Documents" in main menu
2. You will see the upload zone

#### Step 2: Select Files
**Option A - Drag and Drop**
1. Drag document files from your computer
2. Drop them into the upload zone
3. Files will be added to queue

**Option B - Click to Browse**
1. Click "Select Files" button
2. Browse to document location
3. Select one or more files
4. Click "Open"

#### Step 3: Review Files
- Check file names and sizes
- Verify all required documents are included
- Remove any incorrect files by clicking "X"

#### Step 4: Upload
1. Click "Upload All" button
2. Progress bars show upload status
3. Wait for all files to complete
4. You will see success confirmation

#### Step 5: Confirm Loan Application
1. Enter loan application ID
2. Enter applicant name
3. Click "Submit"
4. System will begin processing

### Upload Tips
- Upload all documents for one applicant together
- Ensure documents are clear and legible
- Include all required document types
- Check file format before uploading
- Verify file sizes are within limits

### Troubleshooting Uploads

**File Too Large**
- Compress PDF or image
- Reduce image resolution
- Split multi-page document

**Unsupported Format**
- Convert to PDF or JPEG
- Use online conversion tools
- Contact IT support

**Upload Failed**
- Check internet connection
- Try again in a few moments
- Use different browser
- Contact support if persists

---

## Viewing Audit Queue

### Audit Queue Overview
The audit queue shows all loan applications being processed or completed.

### Queue Columns
- **Application ID** - Unique identifier for loan application
- **Applicant Name** - Name of loan applicant
- **Upload Date** - When documents were uploaded
- **Status** - Current processing status
- **Risk Score** - Overall risk assessment (0-100)

### Status Indicators
- **Pending** - Waiting to be processed
- **Processing** - Currently being analyzed
- **Completed** - Analysis finished
- **Failed** - Error during processing

### Sorting and Filtering

#### Sort by Column
1. Click column header
2. Click again to reverse sort order
3. Arrow indicates sort direction

#### Filter by Date Range
1. Click "Date Range" filter
2. Select start date
3. Select end date
4. Click "Apply"

#### Filter by Risk Score
1. Click "Risk Score" filter
2. Select minimum score
3. Select maximum score
4. Click "Apply"

#### Filter by Status
1. Click "Status" filter
2. Check desired statuses
3. Click "Apply"

#### Search by ID or Name
1. Enter search term in search box
2. Results update automatically
3. Clear search to show all

### Viewing Details
1. Click on any row in queue
2. Detailed audit view opens
3. See full results and inconsistencies

---

## Reviewing Audit Results

### Audit Detail View

#### Golden Record Section
Shows consolidated applicant information from all documents:
- **Name** - Applicant's full name
- **Date of Birth** - Birth date
- **SSN** - Social Security Number (masked for security)
- **Address** - Current address
- **Contact** - Phone and email

#### Risk Score Section
- **Overall Score** - 0-100 scale
- **Risk Level** - LOW, MEDIUM, HIGH, or CRITICAL
- **Visual Indicator** - Color-coded gauge
- **Contributing Factors** - List of factors affecting score

#### Risk Score Breakdown
- **Name Inconsistencies** - 15 points each
- **Address Mismatches** - 20 points each
- **Income Discrepancies** - 15-25 points
- **ID Mismatches** - 30 points each
- **Low Confidence Fields** - 10 points each
- **Illegible Pages** - 5 points each

#### Inconsistencies Table
Shows all detected inconsistencies:
- **Field** - Which field has inconsistency
- **Severity** - Critical, High, Medium, or Low
- **Expected Value** - What should be there
- **Actual Value** - What was found
- **Source Documents** - Which documents differ

---

## Understanding Risk Scores

### Risk Score Scale

| Score | Level | Meaning | Action |
|-------|-------|---------|--------|
| 0-24 | LOW | Minimal risk | Approve |
| 25-49 | MEDIUM | Some concerns | Review carefully |
| 50-79 | HIGH | Significant issues | Investigate |
| 80-100 | CRITICAL | Major problems | Escalate |

### What Affects Risk Score

#### High Impact (25-30 points)
- SSN mismatch across documents
- Name completely different
- Address in different state
- Income discrepancy > 10%

#### Medium Impact (15-20 points)
- Minor name variations
- Address component mismatch
- Income discrepancy 5-10%
- Multiple low-confidence fields

#### Low Impact (5-10 points)
- Spelling variations
- Formatting differences
- Single low-confidence field
- Illegible page

### Interpreting Your Score

**LOW Risk (0-24)**
- Documents are consistent
- Applicant information matches
- Proceed with normal approval process
- No additional verification needed

**MEDIUM Risk (25-49)**
- Some minor inconsistencies found
- Review details carefully
- May need applicant clarification
- Consider requesting updated documents

**HIGH Risk (50-79)**
- Significant inconsistencies detected
- Investigate before approval
- Contact applicant for explanation
- May require additional documentation

**CRITICAL Risk (80-100)**
- Major discrepancies or red flags
- Do not approve without investigation
- Escalate to supervisor
- May indicate fraud or identity issues

---

## Interpreting Inconsistencies

### Inconsistency Severity Levels

#### Critical (Red)
- SSN mismatch
- Name completely different
- Address in different state
- Income variance > 20%

**Action**: Investigate immediately, contact applicant

#### High (Orange)
- Name spelling variation > 2 characters
- Address component mismatch
- Income variance 10-20%
- Multiple document mismatches

**Action**: Review carefully, may need clarification

#### Medium (Yellow)
- Minor name variation
- Partial address mismatch
- Income variance 5-10%
- Single field inconsistency

**Action**: Note for file, may not require action

#### Low (Gray)
- Formatting differences
- Abbreviation variations
- Single low-confidence field
- Illegible page

**Action**: Document for reference

### Common Inconsistencies

#### Name Variations
- **Example**: "John Smith" vs "Jon Smith"
- **Cause**: Nickname, typo, or abbreviation
- **Action**: Verify with applicant

#### Address Differences
- **Example**: "123 Main St" vs "123 Main Street"
- **Cause**: Abbreviation or formatting
- **Action**: Confirm current address

#### Income Discrepancies
- **Example**: W2 shows $50,000, tax form shows $48,000
- **Cause**: Different time periods or adjustments
- **Action**: Review both documents

#### Date Variations
- **Example**: DOB listed as 1/15/1985 and 1/15/1986
- **Cause**: Typo or data entry error
- **Action**: Request corrected document

---

## Using Document Viewer

### Opening Document Viewer
1. In audit detail view, find "Source Documents" section
2. Click on document name or page number
3. Document viewer opens in new panel

### Viewer Controls

#### Navigation
- **Previous Page** - Click left arrow
- **Next Page** - Click right arrow
- **Go to Page** - Enter page number and press Enter

#### Zoom
- **Zoom In** - Click + button or scroll up
- **Zoom Out** - Click - button or scroll down
- **Fit to Width** - Click fit width button
- **Fit to Page** - Click fit page button

#### Tools
- **Rotate** - Rotate document 90 degrees
- **Download** - Save document to computer
- **Print** - Print document

### Highlighting
- Extracted data fields are highlighted with boxes
- Hover over highlight to see extracted value
- Click highlight to see inconsistency details

### Side-by-Side Comparison
1. Click "Compare Documents" button
2. Select two documents to compare
3. Documents display side-by-side
4. Scroll synchronizes between documents
5. Corresponding fields are highlighted

### Tips for Document Review
- Zoom in to verify extracted data
- Check for document quality issues
- Verify all required fields are present
- Look for signs of tampering or forgery
- Compare signatures across documents

---

## FAQ

### Q: How long does document processing take?
**A**: Most documents process within 2-5 minutes. Complex multi-page documents may take up to 15 minutes.

### Q: Can I upload documents for multiple applicants at once?
**A**: No, upload documents for one applicant at a time. Each upload requires a separate loan application ID.

### Q: What if a document fails to upload?
**A**: Check file size and format. Try again or contact support. Failed uploads don't affect other documents.

### Q: Can I edit extracted data?
**A**: No, extracted data is read-only. Contact your administrator if corrections are needed.

### Q: How is my SSN protected?
**A**: SSNs are encrypted and masked in the interface. Only administrators can view full SSNs with explicit approval.

### Q: What does "low confidence" mean?
**A**: The system is uncertain about extracted data. Verify manually in the document viewer.

### Q: Can I download audit reports?
**A**: Yes, click "Download Report" button in audit detail view. Reports are PDF format.

### Q: How long are documents stored?
**A**: Documents are stored for 7 years per regulatory requirements. After 90 days, they move to archive storage.

### Q: What if I disagree with the risk score?
**A**: Review the inconsistencies section. Contact your supervisor if you believe the score is incorrect.

### Q: Can I reprocess documents?
**A**: No, reprocessing requires uploading new documents. Contact administrator if reprocessing is needed.

---

## Support

### Getting Help

#### In-App Help
- Click "?" icon in top right corner
- Search help topics
- View video tutorials

#### Contact Support
- **Email**: support@auditflowpro.online
- **Phone**: 1-800-AUDIT-PRO
- **Hours**: Monday-Friday, 8 AM - 6 PM EST

#### Report Issues
1. Click "Report Issue" in help menu
2. Describe problem
3. Attach screenshots if helpful
4. Submit
5. You will receive ticket number

### Common Support Topics
- Login issues
- Document upload problems
- Understanding risk scores
- Interpreting inconsistencies
- Accessing audit results
- Downloading reports

### Training Resources
- Video tutorials available in help menu
- Live training sessions (monthly)
- User documentation (this guide)
- Quick reference cards

---

## Best Practices

### Document Upload
✓ Upload all documents for one applicant together  
✓ Ensure documents are clear and legible  
✓ Use supported file formats  
✓ Check file sizes before uploading  
✓ Verify loan application ID is correct  

### Reviewing Results
✓ Review all inconsistencies carefully  
✓ Check risk score contributing factors  
✓ Use document viewer to verify extracted data  
✓ Compare documents side-by-side  
✓ Document any concerns in file notes  

### Risk Assessment
✓ Understand risk score scale  
✓ Investigate HIGH and CRITICAL scores  
✓ Contact applicant for clarification  
✓ Request updated documents if needed  
✓ Escalate concerns to supervisor  

---

**Document Version**: 1.0  
**Last Updated**: 2026-03-22  
**Status**: Production Ready
