#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script to fix existing audit records with correct applicant names from golden_record.
"""

import boto3
import re
import json
from decimal import Decimal

dynamodb = boto3.resource('dynamodb', region_name='ap-south-1')
table = dynamodb.Table('AuditFlow-AuditRecords')

def clean_applicant_name(name):
    """
    Clean applicant name by removing address data.
    Extracts just the name part (before street address).
    """
    if not name:
        return "Unknown Applicant"
    
    # Pattern: Name followed by numbers (street address)
    # Extract everything before the first digit that starts a street number
    match = re.match(r'^([A-Za-z\s\.]+?)(?:\s+\d+\s+|$)', name)
    if match:
        cleaned = match.group(1).strip()
        if cleaned:
            return cleaned
    
    # If no pattern match, return original
    return name.strip()

def extract_applicant_name(golden_record):
    """Extract applicant name from golden_record."""
    if not golden_record:
        return "Unknown Applicant"
    
    # Try to get name from 'name' field first (full name)
    if 'name' in golden_record and isinstance(golden_record['name'], dict):
        name_value = golden_record['name'].get('value', '').strip()
        if name_value:
            # Clean the name to remove address data
            return clean_applicant_name(name_value)
    
    # Fallback to first_name + last_name
    first_name = ''
    last_name = ''
    
    if 'first_name' in golden_record:
        if isinstance(golden_record['first_name'], dict):
            first_name = golden_record['first_name'].get('value', '').strip()
        else:
            first_name = str(golden_record['first_name']).strip()
    
    if 'last_name' in golden_record:
        if isinstance(golden_record['last_name'], dict):
            last_name = golden_record['last_name'].get('value', '').strip()
        else:
            last_name = str(golden_record['last_name']).strip()
    
    full_name = f"{first_name} {last_name}".strip()
    return full_name if full_name else "Unknown Applicant"

def update_records():
    """Scan all records and update applicant_name."""
    scan_kwargs = {}
    updated_count = 0
    
    while True:
        response = table.scan(**scan_kwargs)
        items = response.get('Items', [])
        
        for item in items:
            audit_id = item.get('audit_record_id')
            golden_record = item.get('golden_record', {})
            current_name = item.get('applicant_name', 'Unknown Applicant')
            
            # Extract correct name
            correct_name = extract_applicant_name(golden_record)
            
            # Only update if name is different
            if current_name != correct_name:
                try:
                    table.update_item(
                        Key={'audit_record_id': audit_id},
                        UpdateExpression='SET applicant_name = :name',
                        ExpressionAttributeValues={':name': correct_name}
                    )
                    print(f"✓ Updated {audit_id}: '{current_name}' → '{correct_name}'")
                    updated_count += 1
                except Exception as e:
                    print(f"✗ Failed to update {audit_id}: {str(e)}")
            else:
                print(f"- Skipped {audit_id}: already has correct name '{correct_name}'")
        
        # Check if there are more items
        if 'LastEvaluatedKey' not in response:
            break
        
        scan_kwargs['ExclusiveStartKey'] = response['LastEvaluatedKey']
    
    print(f"\n✓ Total records updated: {updated_count}")

if __name__ == '__main__':
    print("Starting batch update of applicant names...")
    print("=" * 60)
    update_records()
    print("=" * 60)
    print("Batch update complete!")
