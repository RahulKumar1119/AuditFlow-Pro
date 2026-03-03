#!/usr/bin/env python3
"""
Generate test PDF documents for AuditFlow testing
Requires: pip install reportlab
"""

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
import os
from datetime import datetime

def create_w2_form(filename, employee_name, ssn, employer_name, ein, wages, address):
    """Generate a sample W2 form PDF"""
    c = canvas.Canvas(filename, pagesize=letter)
    width, height = letter
    
    # Title
    c.setFont("Helvetica-Bold", 16)
    c.drawString(2*inch, height - 1*inch, "Form W-2 Wage and Tax Statement")
    c.setFont("Helvetica", 10)
    c.drawString(2*inch, height - 1.3*inch, "2023")
    
    # Employer Information
    c.setFont("Helvetica-Bold", 10)
    c.drawString(1*inch, height - 2*inch, "Employer Information:")
    c.setFont("Helvetica", 10)
    c.drawString(1*inch, height - 2.3*inch, f"Employer Name: {employer_name}")
    c.drawString(1*inch, height - 2.6*inch, f"Employer EIN: {ein}")
    
    # Employee Information
    c.setFont("Helvetica-Bold", 10)
    c.drawString(1*inch, height - 3.2*inch, "Employee Information:")
    c.setFont("Helvetica", 10)
    c.drawString(1*inch, height - 3.5*inch, f"Employee Name: {employee_name}")
    c.drawString(1*inch, height - 3.8*inch, f"Employee SSN: {ssn}")
    c.drawString(1*inch, height - 4.1*inch, f"Address: {address}")
    
    # Wage Information
    c.setFont("Helvetica-Bold", 10)
    c.drawString(1*inch, height - 4.7*inch, "Wage Information:")
    c.setFont("Helvetica", 10)
    c.drawString(1*inch, height - 5*inch, f"Box 1 - Wages, tips, other compensation: ${wages:,.2f}")
    c.drawString(1*inch, height - 5.3*inch, f"Box 2 - Federal income tax withheld: ${wages * 0.22:,.2f}")
    c.drawString(1*inch, height - 5.6*inch, f"Box 3 - Social security wages: ${wages:,.2f}")
    c.drawString(1*inch, height - 5.9*inch, f"Box 5 - Medicare wages and tips: ${wages:,.2f}")
    
    # Footer
    c.setFont("Helvetica-Italic", 8)
    c.drawString(1*inch, 1*inch, "This is a computer-generated test document for AuditFlow testing purposes only.")
    
    c.save()
    print(f"✓ Generated: {filename}")

def create_bank_statement(filename, account_holder, account_number, beginning_balance, ending_balance, address):
    """Generate a sample bank statement PDF"""
    c = canvas.Canvas(filename, pagesize=letter)
    width, height = letter
    
    # Bank Header
    c.setFont("Helvetica-Bold", 18)
    c.drawString(1*inch, height - 1*inch, "First National Bank")
    c.setFont("Helvetica", 10)
    c.drawString(1*inch, height - 1.3*inch, "123 Banking Street, New York, NY 10001")
    
    # Statement Period
    c.setFont("Helvetica-Bold", 12)
    c.drawString(1*inch, height - 1.8*inch, "Monthly Statement")
    c.setFont("Helvetica", 10)
    c.drawString(1*inch, height - 2.1*inch, "Statement Period: December 1, 2023 - December 31, 2023")
    
    # Account Holder Information
    c.setFont("Helvetica-Bold", 10)
    c.drawString(1*inch, height - 2.7*inch, "Account Holder:")
    c.setFont("Helvetica", 10)
    c.drawString(1*inch, height - 3*inch, account_holder)
    c.drawString(1*inch, height - 3.3*inch, address)
    
    # Account Information
    c.setFont("Helvetica-Bold", 10)
    c.drawString(1*inch, height - 3.9*inch, "Account Information:")
    c.setFont("Helvetica", 10)
    c.drawString(1*inch, height - 4.2*inch, f"Account Number: {account_number}")
    c.drawString(1*inch, height - 4.5*inch, "Account Type: Checking")
    
    # Balance Summary
    c.setFont("Helvetica-Bold", 10)
    c.drawString(1*inch, height - 5.1*inch, "Balance Summary:")
    c.setFont("Helvetica", 10)
    c.drawString(1*inch, height - 5.4*inch, f"Beginning Balance: ${beginning_balance:,.2f}")
    c.drawString(1*inch, height - 5.7*inch, f"Total Deposits: ${(ending_balance - beginning_balance + 500):,.2f}")
    c.drawString(1*inch, height - 6*inch, f"Total Withdrawals: ${500:,.2f}")
    c.drawString(1*inch, height - 6.3*inch, f"Ending Balance: ${ending_balance:,.2f}")
    
    # Footer
    c.setFont("Helvetica-Italic", 8)
    c.drawString(1*inch, 1*inch, "This is a computer-generated test document for AuditFlow testing purposes only.")
    
    c.save()
    print(f"✓ Generated: {filename}")

def create_tax_form(filename, taxpayer_name, ssn, filing_status, agi, address):
    """Generate a sample 1040 tax form PDF"""
    c = canvas.Canvas(filename, pagesize=letter)
    width, height = letter
    
    # Title
    c.setFont("Helvetica-Bold", 16)
    c.drawString(2*inch, height - 1*inch, "Form 1040 U.S. Individual Income Tax Return")
    c.setFont("Helvetica", 10)
    c.drawString(2*inch, height - 1.3*inch, "2023")
    
    # Taxpayer Information
    c.setFont("Helvetica-Bold", 10)
    c.drawString(1*inch, height - 2*inch, "Taxpayer Information:")
    c.setFont("Helvetica", 10)
    c.drawString(1*inch, height - 2.3*inch, f"Name: {taxpayer_name}")
    c.drawString(1*inch, height - 2.6*inch, f"Social Security Number: {ssn}")
    c.drawString(1*inch, height - 2.9*inch, f"Address: {address}")
    c.drawString(1*inch, height - 3.2*inch, f"Filing Status: {filing_status}")
    
    # Income Information
    c.setFont("Helvetica-Bold", 10)
    c.drawString(1*inch, height - 3.8*inch, "Income:")
    c.setFont("Helvetica", 10)
    c.drawString(1*inch, height - 4.1*inch, f"Line 1 - Wages, salaries, tips: ${agi:,.2f}")
    c.drawString(1*inch, height - 4.4*inch, f"Line 11 - Adjusted Gross Income (AGI): ${agi:,.2f}")
    
    # Deductions
    standard_deduction = 13850 if filing_status == "Single" else 27700
    c.setFont("Helvetica-Bold", 10)
    c.drawString(1*inch, height - 5*inch, "Deductions:")
    c.setFont("Helvetica", 10)
    c.drawString(1*inch, height - 5.3*inch, f"Line 12 - Standard Deduction: ${standard_deduction:,.2f}")
    
    # Tax Calculation
    taxable_income = max(0, agi - standard_deduction)
    tax = taxable_income * 0.22  # Simplified tax calculation
    c.setFont("Helvetica-Bold", 10)
    c.drawString(1*inch, height - 5.9*inch, "Tax Calculation:")
    c.setFont("Helvetica", 10)
    c.drawString(1*inch, height - 6.2*inch, f"Line 15 - Taxable Income: ${taxable_income:,.2f}")
    c.drawString(1*inch, height - 6.5*inch, f"Line 24 - Total Tax: ${tax:,.2f}")
    
    # Footer
    c.setFont("Helvetica-Italic", 8)
    c.drawString(1*inch, 1*inch, "This is a computer-generated test document for AuditFlow testing purposes only.")
    
    c.save()
    print(f"✓ Generated: {filename}")

def create_drivers_license(filename, full_name, dob, address, license_number, state):
    """Generate a sample driver's license PDF"""
    c = canvas.Canvas(filename, pagesize=letter)
    width, height = letter
    
    # Title
    c.setFont("Helvetica-Bold", 18)
    c.drawString(2*inch, height - 1*inch, f"{state} Driver's License")
    
    # License Information
    c.setFont("Helvetica-Bold", 12)
    c.drawString(1*inch, height - 2*inch, "License Information:")
    c.setFont("Helvetica", 11)
    c.drawString(1*inch, height - 2.4*inch, f"License Number: {license_number}")
    c.drawString(1*inch, height - 2.8*inch, f"Full Name: {full_name}")
    c.drawString(1*inch, height - 3.2*inch, f"Date of Birth: {dob}")
    c.drawString(1*inch, height - 3.6*inch, f"Address: {address}")
    c.drawString(1*inch, height - 4*inch, f"State: {state}")
    c.drawString(1*inch, height - 4.4*inch, "Issue Date: 01/15/2020")
    c.drawString(1*inch, height - 4.8*inch, "Expiration Date: 01/15/2028")
    c.drawString(1*inch, height - 5.2*inch, "Class: D")
    
    # Footer
    c.setFont("Helvetica-Italic", 8)
    c.drawString(1*inch, 1*inch, "This is a computer-generated test document for AuditFlow testing purposes only.")
    
    c.save()
    print(f"✓ Generated: {filename}")

def main():
    """Generate a complete set of test documents for a loan application"""
    
    # Create output directory
    output_dir = "test_documents"
    os.makedirs(output_dir, exist_ok=True)
    
    print("\n" + "="*60)
    print("Generating Test PDF Documents for AuditFlow")
    print("="*60 + "\n")
    
    # Applicant 1 - John Smith (consistent data)
    print("Applicant 1: John Smith (Consistent Data)")
    create_w2_form(
        f"{output_dir}/john_smith_w2.pdf",
        employee_name="John Smith",
        ssn="123-45-6789",
        employer_name="Tech Corp Inc",
        ein="12-3456789",
        wages=85000.00,
        address="123 Main Street, New York, NY 10001"
    )
    
    create_bank_statement(
        f"{output_dir}/john_smith_bank_statement.pdf",
        account_holder="John Smith",
        account_number="****1234",
        beginning_balance=5000.00,
        ending_balance=12500.00,
        address="123 Main Street, New York, NY 10001"
    )
    
    create_tax_form(
        f"{output_dir}/john_smith_1040.pdf",
        taxpayer_name="John Smith",
        ssn="123-45-6789",
        filing_status="Single",
        agi=85000.00,
        address="123 Main Street, New York, NY 10001"
    )
    
    create_drivers_license(
        f"{output_dir}/john_smith_drivers_license.pdf",
        full_name="John Smith",
        dob="05/15/1985",
        address="123 Main Street, New York, NY 10001",
        license_number="S123456789",
        state="New York"
    )
    
    print()
    
    # Applicant 2 - Jane Doe (with inconsistencies)
    print("Applicant 2: Jane Doe (With Inconsistencies)")
    create_w2_form(
        f"{output_dir}/jane_doe_w2.pdf",
        employee_name="Jane M. Doe",  # Name variation
        ssn="987-65-4321",
        employer_name="Global Services LLC",
        ein="98-7654321",
        wages=95000.00,
        address="456 Oak Avenue, Los Angeles, CA 90001"
    )
    
    create_bank_statement(
        f"{output_dir}/jane_doe_bank_statement.pdf",
        account_holder="Jane Doe",  # Different name format
        account_number="****5678",
        beginning_balance=8000.00,
        ending_balance=15000.00,
        address="456 Oak Ave, Los Angeles, CA 90001"  # Address variation
    )
    
    create_tax_form(
        f"{output_dir}/jane_doe_1040.pdf",
        taxpayer_name="Jane Marie Doe",  # Another name variation
        ssn="987-65-4321",
        filing_status="Single",
        agi=92000.00,  # Income inconsistency
        address="456 Oak Avenue, Los Angeles, CA 90001"
    )
    
    create_drivers_license(
        f"{output_dir}/jane_doe_drivers_license.pdf",
        full_name="Jane Marie Doe",
        dob="08/22/1990",
        address="456 Oak Avenue, Los Angeles, CA 90001",
        license_number="D987654321",
        state="California"
    )
    
    print()
    
    # Applicant 3 - Robert Johnson (high income)
    print("Applicant 3: Robert Johnson (High Income)")
    create_w2_form(
        f"{output_dir}/robert_johnson_w2.pdf",
        employee_name="Robert Johnson",
        ssn="555-12-3456",
        employer_name="Finance Partners Inc",
        ein="55-5123456",
        wages=150000.00,
        address="789 Park Place, Chicago, IL 60601"
    )
    
    create_bank_statement(
        f"{output_dir}/robert_johnson_bank_statement.pdf",
        account_holder="Robert Johnson",
        account_number="****9012",
        beginning_balance=25000.00,
        ending_balance=35000.00,
        address="789 Park Place, Chicago, IL 60601"
    )
    
    create_tax_form(
        f"{output_dir}/robert_johnson_1040.pdf",
        taxpayer_name="Robert Johnson",
        ssn="555-12-3456",
        filing_status="Married Filing Jointly",
        agi=150000.00,
        address="789 Park Place, Chicago, IL 60601"
    )
    
    create_drivers_license(
        f"{output_dir}/robert_johnson_drivers_license.pdf",
        full_name="Robert Johnson",
        dob="03/10/1978",
        address="789 Park Place, Chicago, IL 60601",
        license_number="J555123456",
        state="Illinois"
    )
    
    print()
    print("="*60)
    print(f"✓ All test documents generated in '{output_dir}/' directory")
    print("="*60)
    print("\nTest Scenarios:")
    print("1. John Smith - All data is consistent (LOW RISK)")
    print("2. Jane Doe - Has name and income inconsistencies (MEDIUM/HIGH RISK)")
    print("3. Robert Johnson - High income, consistent data (LOW RISK)")
    print("\nYou can now upload these PDFs to test the AuditFlow pipeline!")
    print()

if __name__ == "__main__":
    try:
        main()
    except ImportError:
        print("\n❌ Error: reportlab library not found")
        print("Please install it using: pip install reportlab")
        print()
