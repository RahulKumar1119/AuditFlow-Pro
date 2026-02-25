# backend/functions/extractor/parsers.py

import boto3
import logging
from typing import Dict, Any, List

logger = logging.getLogger()

# Initialize AWS Comprehend for PII detection
comprehend = boto3.client('comprehend')

def detect_and_mask_pii(text: str) -> tuple[str, List[str]]:
    """
    Uses AWS Comprehend to find PII (like SSNs, Account Numbers, etc.) and mask them.
    Returns the masked text and a list of detected PII types.
    """
    if not text or len(text) < 3:
        return text, []
        
    try:
        response = comprehend.detect_pii_entities(Text=text, LanguageCode='en')
        entities = response.get('Entities', [])
        
        detected_types = []
        masked_text = text
        
        # Sort entities in reverse order so string slicing doesn't break as we modify it
        for entity in sorted(entities, key=lambda x: x['BeginOffset'], reverse=True):
            pii_type = entity['Type']
            detected_types.append(pii_type)
            
            # Mask the entity, leaving only the last 4 characters if it's long enough
            begin = entity['BeginOffset']
            end = entity['EndOffset']
            original_val = text[begin:end]
            
            if len(original_val) > 5 and pii_type in ['SSN', 'BANK_ACCOUNT_NUMBER', 'DRIVER_ID']:
                masked_val = "*" * (len(original_val) - 4) + original_val[-4:]
            else:
                masked_val = "*" * len(original_val)
                
            masked_text = masked_text[:begin] + masked_val + masked_text[end:]
            
        return masked_text, list(set(detected_types))
    except Exception as e:
        logger.error(f"Comprehend PII detection failed: {str(e)}")
        return text, []

def parse_w2(textract_blocks: List[Dict]) -> Dict[str, Any]:
    """
    Task 6.2: Extracts W2 fields from Textract Key-Value pairs.
    """
    extracted_data = {}
    
    # Helper to find a value given a key in Textract's FORM output
    key_map = get_kv_relationship(textract_blocks)
    
    # Map expected W2 fields to extracted text
    wages = find_value_for_key(key_map, ["Wages, tips", "1 Wages"])
    ssn = find_value_for_key(key_map, ["Employee's social security number", "a Employee's social"])
    employer = find_value_for_key(key_map, ["Employer's name", "c Employer's name"])
    employer_ein = find_value_for_key(key_map, ["Employer identification number", "b Employer identification"])
    fed_tax = find_value_for_key(key_map, ["Federal income tax withheld", "2 Federal income"])
    
    if wages:
        extracted_data["wages"] = {"value": wages[0], "confidence": wages[1], "requires_manual_review": wages[1] < 80.0}
    if ssn:
        masked_ssn, pii_types = detect_and_mask_pii(ssn[0])
        extracted_data["employee_ssn"] = {"value": masked_ssn, "confidence": ssn[1], "requires_manual_review": ssn[1] < 80.0}
    if employer:
        extracted_data["employer_name"] = {"value": employer[0], "confidence": employer[1], "requires_manual_review": employer[1] < 80.0}
    if employer_ein:
        extracted_data["employer_ein"] = {"value": employer_ein[0], "confidence": employer_ein[1], "requires_manual_review": employer_ein[1] < 80.0}
    if fed_tax:
        extracted_data["federal_tax_withheld"] = {"value": fed_tax[0], "confidence": fed_tax[1], "requires_manual_review": fed_tax[1] < 80.0}
        
    return extracted_data

def parse_bank_statement(textract_blocks: List[Dict]) -> Dict[str, Any]:
    """
    Task 6.3: Extract Bank Statement fields and parse transaction tables.
    """
    extracted_data = {}
    key_map = get_kv_relationship(textract_blocks)
    
    # 1. Extract Key-Value Pairs
    account_num = find_value_for_key(key_map, ["Account Number", "Account #"])
    routing_num = find_value_for_key(key_map, ["Routing Number", "Routing #"])
    bank_name = find_value_for_key(key_map, ["Bank Name", "Institution"])
    beg_balance = find_value_for_key(key_map, ["Beginning Balance", "Previous Balance"])
    end_balance = find_value_for_key(key_map, ["Ending Balance", "New Balance"])
    
    if account_num:
        masked_acc, _ = detect_and_mask_pii(account_num[0])
        extracted_data["account_number"] = {"value": masked_acc, "confidence": account_num[1], "requires_manual_review": account_num[1] < 80.0}
    if routing_num:
        extracted_data["routing_number"] = {"value": routing_num[0], "confidence": routing_num[1], "requires_manual_review": routing_num[1] < 80.0}
    if bank_name:
        extracted_data["bank_name"] = {"value": bank_name[0], "confidence": bank_name[1], "requires_manual_review": bank_name[1] < 80.0}
    if beg_balance:
        extracted_data["beginning_balance"] = {"value": beg_balance[0], "confidence": beg_balance[1], "requires_manual_review": beg_balance[1] < 80.0}
    if end_balance:
        extracted_data["ending_balance"] = {"value": end_balance[0], "confidence": end_balance[1], "requires_manual_review": end_balance[1] < 80.0}

    # 2. Extract Transaction Tables
    transactions = []
    
    for block in textract_blocks:
        if block['BlockType'] == 'TABLE':
            table_confidence = block.get('Confidence', 0.0)
            if table_confidence > 50.0:
                transactions.append(f"Table Detected (Confidence {table_confidence:.2f}%)")
    
    extracted_data["transactions_detected"] = len(transactions) > 0
    return extracted_data

def parse_tax_form_1040(textract_blocks: List[Dict]) -> Dict[str, Any]:
    """
    Task 6.4: Extract Tax Form (1040) data.
    """
    extracted_data = {}
    key_map = get_kv_relationship(textract_blocks)
    
    # Map IRS 1040 specific fields
    ssn = find_value_for_key(key_map, ["Your social security number"])
    agi = find_value_for_key(key_map, ["11", "Adjusted gross income"])
    total_tax = find_value_for_key(key_map, ["24", "Total tax"])
    
    if ssn:
        masked_ssn, _ = detect_and_mask_pii(ssn[0])
        extracted_data["ssn"] = {"value": masked_ssn, "confidence": ssn[1], "requires_manual_review": ssn[1] < 80.0}
    if agi:
        extracted_data["adjusted_gross_income"] = {"value": agi[0], "confidence": agi[1], "requires_manual_review": agi[1] < 80.0}
    if total_tax:
        extracted_data["total_tax"] = {"value": total_tax[0], "confidence": total_tax[1], "requires_manual_review": total_tax[1] < 80.0}
        
    return extracted_data

def parse_id_document(analyze_id_response: Dict) -> Dict[str, Any]:
    """
    Task 6.5 & 6.6: Unified extraction for Driver's Licenses and ID Documents.
    Maps DMV-specific fields natively using Textract's AnalyzeID.
    """
    extracted_data = {}
    
    for doc in analyze_id_response.get('IdentityDocuments', []):
        for field in doc.get('IdentityDocumentFields', []):
            field_type = field.get('Type', {}).get('Text')
            value = field.get('ValueDetection', {}).get('Text')
            confidence = field.get('ValueDetection', {}).get('Confidence', 0.0)
            
            # Identify mapping targets
            if field_type in ['FIRST_NAME', 'LAST_NAME', 'MIDDLE_NAME', 'STATE_NAME', 'CITY_IN_ADDRESS', 'ZIP_CODE_IN_ADDRESS', 'ADDRESS']:
                extracted_data[field_type.lower()] = {"value": value, "confidence": confidence, "requires_manual_review": confidence < 80.0}
            elif field_type in ['DOCUMENT_NUMBER', 'DATE_OF_BIRTH', 'EXPIRATION_DATE', 'DATE_OF_ISSUE']:
                # Mask sensitive identity numbers/dates
                masked_val, _ = detect_and_mask_pii(value)
                extracted_data[field_type.lower()] = {"value": masked_val, "confidence": confidence, "requires_manual_review": confidence < 80.0}
                
    return extracted_data

# --- Helper functions for Textract Block parsing ---

def get_kv_relationship(blocks: List[Dict]) -> Dict[str, Any]:
    """Builds a map of KEY blocks to VALUE blocks from Textract."""
    key_map = {}
    value_map = {}
    block_map = {block['Id']: block for block in blocks}
    
    for block in blocks:
        if block['BlockType'] == 'KEY_VALUE_SET':
            if 'KEY' in block.get('EntityTypes', []):
                key_map[block['Id']] = block
            else:
                value_map[block['Id']] = block
                
    result_map = {}
    for block_id, key_block in key_map.items():
        value_block = find_value_block(key_block, value_map)
        key_text = get_text(key_block, block_map)
        val_text, val_confidence = get_text_and_confidence(value_block, block_map)
        if key_text and val_text:
            result_map[key_text.upper()] = (val_text, val_confidence)
            
    return result_map

def find_value_block(key_block, value_map):
    for relationship in key_block.get('Relationships', []):
        if relationship['Type'] == 'VALUE':
            for value_id in relationship['Ids']:
                return value_map.get(value_id)
    return None

def get_text_and_confidence(block, block_map):
    text = ""
    confidences = []
    if not block: return text, 0.0
    for relationship in block.get('Relationships', []):
        if relationship['Type'] == 'CHILD':
            for child_id in relationship['Ids']:
                word = block_map.get(child_id)
                if word and word['BlockType'] == 'WORD':
                    text += word['Text'] + " "
                    confidences.append(word['Confidence'])
    avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
    return text.strip(), avg_confidence

def get_text(block, block_map):
    text, _ = get_text_and_confidence(block, block_map)
    return text

def find_value_for_key(key_map: Dict, target_keys: List[str]) -> tuple:
    for target in target_keys:
        for key, value_tuple in key_map.items():
            if target.upper() in key:
                return value_tuple
    return None
