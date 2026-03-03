#!/usr/bin/env python3
"""
Generate simple test PDF documents for AuditFlow testing
Uses PyPDF2 to create basic text PDFs - no external dependencies needed
"""

import os
from datetime import datetime

def create_text_pdf_content(title, content_lines):
    """Create a simple PDF with text content using PDF syntax"""
    # Basic PDF structure with text
    pdf_content = f"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj

2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj

3 0 obj
<<
/Type /Page
/Parent 2 0 R
/Resources <<
/Font <<
/F1 <<
/Type /Font
/Subtype /Type1
/BaseFont /Helvetica
>>
/F2 <<
/Type /Font
/Subtype /Type1
/BaseFont /Helvetica-Bold
>>
>>
>>
/MediaBox [0 0 612 792]
/Contents 4 0 R
>>
endobj

4 0 obj
<<
/Length {len(generate_content_stream(title, content_lines))}
>>
stream
{generate_content_stream(title, content_lines)}
endstream
endobj

xref
0 5
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000317 00000 n 
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
{400 + len(generate_content_stream(title, content_lines))}
%%EOF"""
    return pdf_content

def generate_content_stream(title, content_lines):
    """Generate PDF content stream with text"""
    stream = "BT\n"
    stream += "/F2 16 Tf\n"  # Bold font, size 16
    stream += "50 750 Td\n"  # Position
    stream += f"({title}) Tj\n"
    stream += "0 -30 Td\n"
    stream += "/F1 10 Tf\n"  # Regular font, size 10
    
    for line in content_lines:
        stream += f"({line}) Tj\n"
        stream += "0 -15 Td\n"
    
    stream += "ET"
    return stream

def create_w2_pdf(filename, employee_name, ssn, employer_name, ein, wages, address):
    """Generate W2 form PDF"""
    content = [
        "Form W-2 Wage and Tax Statement - 2023",
        "",
        "EMPLOYER INFORMATION:",
        f"Employer Name: {employer_name}",
        f"Employer EIN: {ein}",
        "",
        "EMPLOYEE INFORMATION:",
        f"Employee Name: {employee_name}",
        f"Employee SSN: {ssn}",
        f"Address: {address}",
        "",
        "WAGE INFORMATION:",
        f"Box 1 - Wages, tips, compensation: ${wages:,.2f}",
        f"Box 2 - Federal tax withheld: ${wages * 0.22:,.2f}",
        f"Box 3 - Social security wages: ${wages:,.2f}",
        f"Box 5 - Medicare wages: ${wages:,.2f}",
        "",
        "This is a test document for AuditFlow testing only."
    ]
    
    pdf_content = create_text_pdf_content("W-2 Form", content)
    with open(filename, 'wb') as f:
        f.write(pdf_content.encode('latin-1'))
    print(f"✓ Generated: {filename}")

def create_bank_statement_pdf(filename, account_holder, account_number, beginning_balance, ending_balance, address):
    """Generate bank statement PDF"""
    content = [
        "FIRST NATIONAL BANK",
        "Monthly Statement - December 2023",
        "",
        "ACCOUNT HOLDER:",
        account_holder,
        address,
        "",
        "ACCOUNT INFORMATION:",
        f"Account Number: {account_number}",
        "Account Type: Checking",
        "",
        "BALANCE SUMMARY:",
        f"Beginning Balance: ${beginning_balance:,.2f}",
        f"Total Deposits: ${(ending_balance - beginning_balance + 500):,.2f}",
        f"Total Withdrawals: $500.00",
        f"Ending Balance: ${ending_balance:,.2f}",
        "",
        "This is a test document for AuditFlow testing only."
    ]
    
    pdf_content = create_text_pdf_content("Bank Statement", content)
    with open(filename, 'wb') as f:
        f.write(pdf_content.encode('latin-1'))
    print(f"✓ Generated: {filename}")

def create_tax_form_pdf(filename, taxpayer_name, ssn, filing_status, agi, address):
    """Generate 1040 tax form PDF"""
    standard_deduction = 13850 if filing_status == "Single" else 27700
    taxable_income = max(0, agi - standard_deduction)
    tax = taxable_income * 0.22
    
    content = [
        "Form 1040 U.S. Individual Income Tax Return - 2023",
        "",
        "TAXPAYER INFORMATION:",
        f"Name: {taxpayer_name}",
        f"Social Security Number: {ssn}",
        f"Address: {address}",
        f"Filing Status: {filing_status}",
        "",
        "INCOME:",
        f"Line 1 - Wages, salaries, tips: ${agi:,.2f}",
        f"Line 11 - Adjusted Gross Income: ${agi:,.2f}",
        "",
        "DEDUCTIONS:",
        f"Line 12 - Standard Deduction: ${standard_deduction:,.2f}",
        "",
        "TAX CALCULATION:",
        f"Line 15 - Taxable Income: ${taxable_income:,.2f}",
        f"Line 24 - Total Tax: ${tax:,.2f}",
        "",
        "This is a test document for AuditFlow testing only."
    ]
    
    pdf_content = create_text_pdf_content("Form 1040", content)
    with open(filename, 'wb') as f:
        f.write(pdf_content.encode('latin-1'))
    print(f"✓ Generated: {filename}")

def create_drivers_license_pdf(filename, full_name, dob, address, license_number, state):
    """Generate driver's license PDF"""
    content = [
        f"{state} DRIVER'S LICENSE",
        "",
        "LICENSE INFORMATION:",
        f"License Number: {license_number}",
        f"Full Name: {full_name}",
        f"Date of Birth: {dob}",
        f"Address: {address}",
        f"State: {state}",
        "Issue Date: 01/15/2020",
        "Expiration Date: 01/15/2028",
        "Class: D",
        "",
        "This is a test document for AuditFlow testing only."
    ]
    
    pdf_content = create_text_pdf_content("Driver License", content)
    with open(filename, 'wb') as f:
        f.write(pdf_content.encode('latin-1'))
    print(f"✓ Generated: {filename}")

def main():
    """Generate test documents"""
    output_dir = "test_documents"
    os.makedirs(output_dir, exist_ok=True)
    
    print("\n" + "="*60)
    print("Generating Test PDF Documents for AuditFlow")
    print("="*60 + "\n")
    
    # Applicant 1 - John Smith
    print("Applicant 1: John Smith (Consistent Data)")
    create_w2_pdf(
        f"{output_dir}/john_smith_w2.pdf",
        "John Smith", "123-45-6789", "Tech Corp Inc",
        "12-3456789", 85000.00, "123 Main Street, New York, NY 10001"
    )
    create_bank_statement_pdf(
        f"{output_dir}/john_smith_bank_statement.pdf",
        "John Smith", "****1234", 5000.00, 12500.00,
        "123 Main Street, New York, NY 10001"
    )
    create_tax_form_pdf(
        f"{output_dir}/john_smith_1040.pdf",
        "John Smith", "123-45-6789", "Single", 85000.00,
        "123 Main Street, New York, NY 10001"
    )
    create_drivers_license_pdf(
        f"{output_dir}/john_smith_drivers_license.pdf",
        "John Smith", "05/15/1985",
        "123 Main Street, New York, NY 10001",
        "S123456789", "New York"
    )
    print()
    
    # Applicant 2 - Jane Doe (with inconsistencies)
    print("Applicant 2: Jane Doe (With Inconsistencies)")
    create_w2_pdf(
        f"{output_dir}/jane_doe_w2.pdf",
        "Jane M. Doe", "987-65-4321", "Global Services LLC",
        "98-7654321", 95000.00, "456 Oak Avenue, Los Angeles, CA 90001"
    )
    create_bank_statement_pdf(
        f"{output_dir}/jane_doe_bank_statement.pdf",
        "Jane Doe", "****5678", 8000.00, 15000.00,
        "456 Oak Ave, Los Angeles, CA 90001"
    )
    create_tax_form_pdf(
        f"{output_dir}/jane_doe_1040.pdf",
        "Jane Marie Doe", "987-65-4321", "Single", 92000.00,
        "456 Oak Avenue, Los Angeles, CA 90001"
    )
    create_drivers_license_pdf(
        f"{output_dir}/jane_doe_drivers_license.pdf",
        "Jane Marie Doe", "08/22/1990",
        "456 Oak Avenue, Los Angeles, CA 90001",
        "D987654321", "California"
    )
    print()
    
    # Applicant 3 - Robert Johnson
    print("Applicant 3: Robert Johnson (High Income)")
    create_w2_pdf(
        f"{output_dir}/robert_johnson_w2.pdf",
        "Robert Johnson", "555-12-3456", "Finance Partners Inc",
        "55-5123456", 150000.00, "789 Park Place, Chicago, IL 60601"
    )
    create_bank_statement_pdf(
        f"{output_dir}/robert_johnson_bank_statement.pdf",
        "Robert Johnson", "****9012", 25000.00, 35000.00,
        "789 Park Place, Chicago, IL 60601"
    )
    create_tax_form_pdf(
        f"{output_dir}/robert_johnson_1040.pdf",
        "Robert Johnson", "555-12-3456", "Married Filing Jointly", 150000.00,
        "789 Park Place, Chicago, IL 60601"
    )
    create_drivers_license_pdf(
        f"{output_dir}/robert_johnson_drivers_license.pdf",
        "Robert Johnson", "03/10/1978",
        "789 Park Place, Chicago, IL 60601",
        "J555123456", "Illinois"
    )
    print()
    
    print("="*60)
    print(f"✓ All test documents generated in '{output_dir}/' directory")
    print("="*60)
    print("\nTest Scenarios:")
    print("1. John Smith - Consistent data (LOW RISK)")
    print("2. Jane Doe - Name and income inconsistencies (MEDIUM/HIGH RISK)")
    print("3. Robert Johnson - High income, consistent (LOW RISK)")
    print("\nYou can now upload these PDFs to test AuditFlow!")
    print()

if __name__ == "__main__":
    main()
