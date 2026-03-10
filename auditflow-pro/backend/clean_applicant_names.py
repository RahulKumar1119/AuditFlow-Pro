#!/usr/bin/env python3
"""
Script to clean applicant names that contain address data.
Extracts just the name part (before street address).
"""

import boto3
import re

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

def clean_records():
    """Scan all records and clean applicant names with addresses."""
    scan_kwargs = {}
    updated_count = 0
    
    while True:
        response = table.scan(**scan_kwargs)
        items = response.get('Items', [])
        
        for item in items:
            audit_id = item.get('audit_record_id')
            current_name = item.get('applicant_name', 'Unknown Applicant')
            
            # Check if name contains address indicators
            if any(indicator in current_name for indicator in ['Street', 'Avenue', 'Road', 'Boulevard', 'Lane', 'Drive', 'Court', 'Circle']):
                cleaned_name = clean_applicant_name(current_name)
                
                if current_name != cleaned_name:
                    try:
                        table.update_item(
                            Key={'audit_record_id': audit_id},
                            UpdateExpression='SET applicant_name = :name',
                            ExpressionAttributeValues={':name': cleaned_name}
                        )
                        print(f"✓ Cleaned {audit_id}:")
                        print(f"  From: '{current_name}'")
                        print(f"  To:   '{cleaned_name}'")
                        updated_count += 1
                    except Exception as e:
                        print(f"✗ Failed to update {audit_id}: {str(e)}")
        
        # Check if there are more items
        if 'LastEvaluatedKey' not in response:
            break
        
        scan_kwargs['ExclusiveStartKey'] = response['LastEvaluatedKey']
    
    print(f"\n✓ Total records cleaned: {updated_count}")

if __name__ == '__main__':
    print("Starting cleanup of applicant names with address data...")
    print("=" * 70)
    clean_records()
    print("=" * 70)
    print("Cleanup complete!")
