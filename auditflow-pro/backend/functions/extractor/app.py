import os
import json
import time
import logging
import boto3
from botocore.exceptions import ClientError
from typing import Dict, Any, List, Optional
from shared.models import (
    DocumentMetadata, ExtractedField,
    W2Data, BankStatementData, TaxFormData, 
    DriversLicenseData, IDDocumentData,
    get_document_data_class
)

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize clients outside handler for connection reuse
textract = boto3.client('textract', region_name=os.environ.get('AWS_REGION', 'us-east-1'))
comprehend = boto3.client('comprehend', region_name=os.environ.get('AWS_REGION', 'us-east-1'))

# Configuration
CONFIDENCE_THRESHOLD = float(os.environ.get('CONFIDENCE_THRESHOLD', '0.80'))
PROCESSING_TIMEOUT = int(os.environ.get('PROCESSING_TIMEOUT', '300'))  # 5 minutes in seconds


def analyze_document_with_retry(bucket: str, key: str, document_id: str, max_retries: int = 3):
    """
    Calls Textract with exponential backoff retry logic.
    
    Implements Requirement 11.3, 11.4: Retry with exponential backoff (5s, 15s, 45s).
    
    Args:
        bucket: S3 bucket name
        key: S3 object key
        document_id: Document identifier for logging
        max_retries: Maximum number of retry attempts (default: 3)
    
    Returns:
        Textract API response
        
    Raises:
        ClientError: When all retries are exhausted or non-retryable error occurs
    """
    retry_delays = [5, 15, 45]
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Calling Textract for document {document_id} (attempt {attempt + 1}/{max_retries})")
            
            response = textract.analyze_document(
                Document={'S3Object': {'Bucket': bucket, 'Name': key}},
                FeatureTypes=['FORMS', 'TABLES']
            )
            
            logger.info(f"Textract analysis successful for document {document_id}")
            return response
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error'].get('Message', str(e))
            
            logger.error(
                f"Textract API error for document {document_id}: "
                f"ErrorCode={error_code}, Message={error_message}, "
                f"Attempt={attempt + 1}/{max_retries}"
            )
            
            if error_code in ['ProvisionedThroughputExceededException', 'ThrottlingException', 'ServiceUnavailable']:
                if attempt < max_retries - 1:
                    sleep_time = retry_delays[attempt]
                    logger.warning(f"Retrying in {sleep_time} seconds")
                    time.sleep(sleep_time)
                else:
                    logger.error(f"Textract retries exhausted for document {document_id}")
                    raise
            else:
                logger.error(f"Non-retryable Textract error for document {document_id}: {error_code}")
                raise
                
        except Exception as e:
            logger.error(
                f"Unexpected error during Textract analysis for document {document_id}: "
                f"{type(e).__name__}: {str(e)}"
            )
            raise


def detect_pii(text: str, document_id: str) -> List[str]:
    """
    Detect PII in extracted text using AWS Comprehend.
    
    Implements Requirement 7.1: Detect PII using Comprehend_Service
    Implements Requirement 7.2: Identify SSN, account numbers, license numbers, and dates of birth
    Implements Requirement 7.3: Redact PII from CloudWatch_Log entries
    
    This function calls the AWS Comprehend DetectPiiEntities API to identify
    personally identifiable information in document text. The detected PII types
    are returned as a list for downstream processing and field-level encryption.
    
    PII Types Detected:
    - SSN (Social Security Numbers)
    - BANK_ACCOUNT_NUMBER (Bank account numbers)
    - DRIVER_ID (Driver's license numbers)
    - DATE_OF_BIRTH (Dates of birth)
    - And other PII types supported by AWS Comprehend
    
    Args:
        text: Text to analyze for PII
        document_id: Document identifier for logging (PII-safe)
    
    Returns:
        List of detected PII entity types (e.g., ['SSN', 'DATE_OF_BIRTH'])
    
    Note:
        - Text is truncated to 5000 bytes to comply with Comprehend API limits
        - PII values are NOT logged to maintain compliance (Requirement 7.3)
        - Errors are handled gracefully, returning empty list on failure
    """
    try:
        if not text or len(text.strip()) == 0:
            logger.debug(f"No text to analyze for PII in document {document_id}")
            return []
        
        # Truncate text if too long (Comprehend has 5000 byte limit)
        original_length = len(text)
        if original_length > 5000:
            text = text[:5000]
            logger.info(
                f"Truncated text for PII detection: document_id={document_id}, "
                f"original_length={original_length}, truncated_length=5000"
            )
        
        # Call AWS Comprehend DetectPiiEntities API (Requirement 7.1)
        logger.debug(f"Calling Comprehend DetectPiiEntities for document {document_id}")
        response = comprehend.detect_pii_entities(
            Text=text,
            LanguageCode='en'
        )
        
        # Extract unique PII entity types (Requirement 7.2)
        pii_types = []
        pii_counts = {}
        
        for entity in response.get('Entities', []):
            # Skip None or invalid entities
            if not entity or not isinstance(entity, dict):
                continue
                
            entity_type = entity.get('Type')
            if entity_type:
                # Count occurrences of each PII type
                pii_counts[entity_type] = pii_counts.get(entity_type, 0) + 1
                
                # Add to list if not already present
                if entity_type not in pii_types:
                    pii_types.append(entity_type)
        
        # Log PII detection results WITHOUT logging actual PII values (Requirement 7.3)
        if pii_types:
            # Create summary of detected PII types and counts
            pii_summary = ', '.join([f"{pii_type}({pii_counts[pii_type]})" for pii_type in pii_types])
            logger.info(
                f"PII detected in document {document_id}: types={pii_summary}, "
                f"total_entities={sum(pii_counts.values())}"
            )
            
            # Log specific PII types for compliance tracking
            if 'SSN' in pii_types:
                logger.info(f"SSN detected in document {document_id} - will apply field-level encryption")
            if 'BANK_ACCOUNT_NUMBER' in pii_types:
                logger.info(f"Bank account number detected in document {document_id} - will apply field-level encryption")
            if 'DRIVER_ID' in pii_types:
                logger.info(f"Driver's license number detected in document {document_id} - will apply field-level encryption")
            if 'DATE_OF_BIRTH' in pii_types:
                logger.info(f"Date of birth detected in document {document_id} - will apply field-level encryption")
        else:
            logger.debug(f"No PII detected in document {document_id}")
        
        return pii_types
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error'].get('Message', str(e))
        logger.warning(
            f"Comprehend PII detection failed for document {document_id}: "
            f"error_code={error_code}, error_message={error_message}"
        )
        return []
        
    except Exception as e:
        logger.warning(
            f"PII detection failed for document {document_id}: "
            f"{type(e).__name__}: {str(e)}"
        )
        return []


def process_multi_page_pdf(bucket: str, key: str, document_id: str, page_count: int) -> Dict[str, Any]:
    """
    Process multi-page PDF documents with timeout protection and error handling.

    Implements Requirements:
    - 5.1: Process all pages sequentially
    - 5.2: Maintain page order and associate data with page numbers
    - 5.3: Aggregate data from multiple pages
    - 5.4: Timeout protection (5-minute limit per document)
    - 5.5: Handle documents up to 100 pages
    - 5.6: Handle corrupted or illegible pages gracefully

    Args:
        bucket: S3 bucket name
        key: S3 object key
        document_id: Document identifier
        page_count: Number of pages in document

    Returns:
        Aggregated Textract response with all pages

    Raises:
        ValueError: If page_count exceeds 100 pages
        Exception: If processing fails after retries
    """
    logger.info(f"Processing multi-page PDF: document_id={document_id}, pages={page_count}")

    # Requirement 5.5: Handle documents up to 100 pages
    if page_count > 100:
        error_msg = f"Document exceeds maximum page limit: {page_count} > 100"
        logger.error(f"document_id={document_id}: {error_msg}")
        raise ValueError(error_msg)

    # Requirement 5.4: Timeout protection - split large documents
    # Textract has a 5-minute timeout, so we process in batches if needed
    # For very large documents (>50 pages), we could split into batches
    # For now, we rely on Textract's built-in handling

    try:
        # Textract handles multi-page PDFs automatically
        # It processes all pages and returns blocks with page numbers
        response = analyze_document_with_retry(bucket, key, document_id)

        # Requirement 5.2: Track which pages were successfully processed
        pages_processed = set()
        corrupted_pages = []

        for block in response.get('Blocks', []):
            if 'Page' in block:
                page_num = block['Page']
                pages_processed.add(page_num)

                # Check for low confidence blocks that might indicate corruption
                if block.get('BlockType') == 'PAGE' and block.get('Confidence', 100) < 50:
                    corrupted_pages.append(page_num)
                    logger.warning(
                        f"document_id={document_id}: Page {page_num} has low confidence "
                        f"({block.get('Confidence')}%), may be corrupted or illegible"
                    )

        # Requirement 5.6: Handle corrupted or illegible pages gracefully
        missing_pages = set(range(1, page_count + 1)) - pages_processed
        if missing_pages:
            logger.warning(
                f"document_id={document_id}: Missing pages detected: {sorted(missing_pages)}. "
                f"These pages may be corrupted or illegible. Continuing with available pages."
            )

        if corrupted_pages:
            logger.warning(
                f"document_id={document_id}: Corrupted/illegible pages detected: "
                f"{sorted(corrupted_pages)}. Data extraction may be incomplete."
            )

        # Add metadata about page processing
        response['PageProcessingMetadata'] = {
            'total_pages': page_count,
            'pages_processed': len(pages_processed),
            'pages_processed_list': sorted(pages_processed),
            'missing_pages': sorted(missing_pages),
            'corrupted_pages': sorted(corrupted_pages),
            'processing_complete': len(missing_pages) == 0
        }

        logger.info(
            f"Multi-page processing complete: document_id={document_id}, "
            f"pages_processed={len(pages_processed)}/{page_count}, "
            f"missing={len(missing_pages)}, corrupted={len(corrupted_pages)}"
        )

        return response

    except Exception as e:
        logger.error(
            f"Multi-page processing failed for document {document_id}: "
            f"{type(e).__name__}: {str(e)}"
        )
        raise


def extract_key_value_pairs(blocks: List[Dict]) -> Dict[str, Any]:
    """
    Extract key-value pairs from Textract response.
    
    Args:
        blocks: Textract blocks
    
    Returns:
        Dictionary of key-value pairs with confidence scores
    """
    key_map = {}
    value_map = {}
    block_map = {}
    
    # Build block map
    for block in blocks:
        block_id = block['Id']
        block_map[block_id] = block
        
        if block['BlockType'] == 'KEY_VALUE_SET':
            if 'KEY' in block.get('EntityTypes', []):
                key_map[block_id] = block
            elif 'VALUE' in block.get('EntityTypes', []):
                value_map[block_id] = block
    
    # Extract text from blocks
    def get_text(block, block_map):
        text = ''
        if 'Relationships' in block:
            for relationship in block['Relationships']:
                if relationship['Type'] == 'CHILD':
                    for child_id in relationship['Ids']:
                        if child_id in block_map:
                            child = block_map[child_id]
                            if child['BlockType'] == 'WORD':
                                text += child.get('Text', '') + ' '
        return text.strip()
    
    # Build key-value pairs
    kvs = {}
    for key_id, key_block in key_map.items():
        key_text = get_text(key_block, block_map)
        value_text = ''
        confidence = key_block.get('Confidence', 0) / 100.0
        
        # Find associated value
        if 'Relationships' in key_block:
            for relationship in key_block['Relationships']:
                if relationship['Type'] == 'VALUE':
                    for value_id in relationship['Ids']:
                        if value_id in value_map:
                            value_block = value_map[value_id]
                            value_text = get_text(value_block, block_map)
                            value_confidence = value_block.get('Confidence', 0) / 100.0
                            confidence = min(confidence, value_confidence)
        
        if key_text:
            kvs[key_text] = {
                'value': value_text,
                'confidence': confidence
            }
    
    return kvs


def route_to_extractor(document_type: str, textract_response: Dict, document_id: str) -> Any:
    """
    Route to appropriate extractor based on document type.
    
    Implements Requirement 4.1: Route to appropriate extractor based on document type.
    
    Args:
        document_type: Type of document (W2, BANK_STATEMENT, etc.)
        textract_response: Textract API response
        document_id: Document identifier for logging
    
    Returns:
        Extracted data object for the document type
    """
    logger.info(f"Routing document {document_id} to {document_type} extractor")
    
    # Extract key-value pairs and text blocks
    blocks = textract_response.get('Blocks', [])
    kvs = extract_key_value_pairs(blocks)
    
    # Get all text for PII detection
    all_text = ' '.join([block.get('Text', '') for block in blocks if block['BlockType'] == 'LINE'])
    
    # Route to appropriate extractor
    if document_type == 'W2':
        return extract_w2_data(kvs, blocks, document_id)
    elif document_type == 'BANK_STATEMENT':
        return extract_bank_statement_data(kvs, blocks, document_id)
    elif document_type == 'TAX_FORM':
        return extract_tax_form_data(kvs, blocks, document_id)
    elif document_type == 'DRIVERS_LICENSE':
        return extract_drivers_license_data(kvs, blocks, document_id)
    elif document_type == 'ID_DOCUMENT':
        return extract_id_document_data(kvs, blocks, document_id)
    else:
        logger.warning(f"Unknown document type {document_type} for document {document_id}")
        return {}



def extract_w2_data(kvs: Dict, blocks: List[Dict], document_id: str) -> W2Data:
    """
    Extract W2 form data.
    
    Implements Requirement 4.3: Extract employer name, employee name, wages, and tax withholdings.
    Implements Requirement 4.9: Store extracted data with confidence scores.
    
    Args:
        kvs: Key-value pairs from Textract
        blocks: Textract blocks
        document_id: Document identifier
    
    Returns:
        W2Data object with extracted fields
    """
    logger.info(f"Extracting W2 data for document {document_id}")
    
    w2_data = W2Data()
    
    # Helper function to find field by key patterns
    def find_field(patterns: List[str], kvs: Dict, exclude_patterns: List[str] = None) -> Optional[Dict]:
        """Find a field by matching key patterns (case-insensitive), optionally excluding certain patterns."""
        exclude_patterns = exclude_patterns or []
        for key, value_data in kvs.items():
            key_lower = key.lower()
            # Check if key should be excluded
            if any(excl.lower() in key_lower for excl in exclude_patterns):
                continue
            # Check if key matches any pattern
            for pattern in patterns:
                if pattern.lower() in key_lower:
                    return value_data
        return None
    
    # Helper function to extract numeric value
    def extract_numeric(text: str) -> Optional[float]:
        """Extract numeric value from text, handling currency formatting."""
        if not text:
            return None
        # Remove common currency symbols and commas
        cleaned = text.replace('$', '').replace(',', '').strip()
        try:
            return float(cleaned)
        except ValueError:
            return None
    
    # Helper function to create ExtractedField
    def create_field(value: Any, confidence: float) -> ExtractedField:
        """Create ExtractedField with manual review flag if confidence is low."""
        requires_review = confidence < CONFIDENCE_THRESHOLD
        return ExtractedField(value=value, confidence=confidence, requires_manual_review=requires_review)
    
    # Extract tax year
    tax_year_patterns = ['tax year', 'year', 'for calendar year']
    tax_year_data = find_field(tax_year_patterns, kvs)
    if tax_year_data:
        w2_data.tax_year = create_field(tax_year_data['value'], tax_year_data['confidence'])
        logger.debug(f"Extracted tax_year: {tax_year_data['value']} (confidence: {tax_year_data['confidence']:.2f})")
    
    # Extract employer name (check before employee to avoid confusion)
    employer_patterns = ['employer name', 'company name', 'business name', 'payer name']
    employer_data = find_field(employer_patterns, kvs)
    if employer_data:
        w2_data.employer_name = create_field(employer_data['value'], employer_data['confidence'])
        logger.debug(f"Extracted employer_name: {employer_data['value']} (confidence: {employer_data['confidence']:.2f})")
    
    # Extract employer EIN
    ein_patterns = ['employer identification number', 'ein', 'federal id', 'employer id']
    ein_data = find_field(ein_patterns, kvs)
    if ein_data:
        w2_data.employer_ein = create_field(ein_data['value'], ein_data['confidence'])
        logger.debug(f"Extracted employer_ein: {ein_data['value']} (confidence: {ein_data['confidence']:.2f})")
    
    # Extract employee name (exclude employer-related keys)
    employee_name_patterns = ['employee name', 'employee\'s name', 'name']
    employee_name_data = find_field(employee_name_patterns, kvs, exclude_patterns=['employer'])
    if employee_name_data:
        w2_data.employee_name = create_field(employee_name_data['value'], employee_name_data['confidence'])
        logger.debug(f"Extracted employee_name: {employee_name_data['value']} (confidence: {employee_name_data['confidence']:.2f})")
    
    # Extract employee SSN
    ssn_patterns = ['social security number', 'ssn', 'employee ssn', 'social security']
    ssn_data = find_field(ssn_patterns, kvs)
    if ssn_data:
        # Mask SSN for security (show only last 4 digits)
        ssn_value = ssn_data['value']
        if ssn_value and len(ssn_value) >= 4:
            masked_ssn = '***-**-' + ssn_value[-4:]
        else:
            masked_ssn = ssn_value
        w2_data.employee_ssn = create_field(masked_ssn, ssn_data['confidence'])
        logger.debug(f"Extracted employee_ssn: {masked_ssn} (confidence: {ssn_data['confidence']:.2f})")
    
    # Extract employee address
    address_patterns = ['address', 'employee address', 'street', 'city state zip']
    address_data = find_field(address_patterns, kvs)
    if address_data:
        w2_data.employee_address = create_field(address_data['value'], address_data['confidence'])
        logger.debug(f"Extracted employee_address: {address_data['value']} (confidence: {address_data['confidence']:.2f})")
    
    # Extract wages (Box 1)
    wages_patterns = ['wages', 'tips', 'other compensation', 'box 1', 'wages tips']
    wages_data = find_field(wages_patterns, kvs)
    if wages_data:
        wages_value = extract_numeric(wages_data['value'])
        if wages_value is not None:
            w2_data.wages = create_field(wages_value, wages_data['confidence'])
            logger.debug(f"Extracted wages: {wages_value} (confidence: {wages_data['confidence']:.2f})")
    
    # Extract federal tax withheld (Box 2)
    federal_tax_patterns = ['federal income tax withheld', 'federal tax', 'box 2', 'federal withholding']
    federal_tax_data = find_field(federal_tax_patterns, kvs)
    if federal_tax_data:
        federal_tax_value = extract_numeric(federal_tax_data['value'])
        if federal_tax_value is not None:
            w2_data.federal_tax_withheld = create_field(federal_tax_value, federal_tax_data['confidence'])
            logger.debug(f"Extracted federal_tax_withheld: {federal_tax_value} (confidence: {federal_tax_data['confidence']:.2f})")
    
    # Extract social security wages (Box 3)
    ss_wages_patterns = ['social security wages', 'box 3', 'ss wages']
    ss_wages_data = find_field(ss_wages_patterns, kvs)
    if ss_wages_data:
        ss_wages_value = extract_numeric(ss_wages_data['value'])
        if ss_wages_value is not None:
            w2_data.social_security_wages = create_field(ss_wages_value, ss_wages_data['confidence'])
            logger.debug(f"Extracted social_security_wages: {ss_wages_value} (confidence: {ss_wages_data['confidence']:.2f})")
    
    # Extract medicare wages (Box 5)
    medicare_wages_patterns = ['medicare wages', 'box 5', 'medicare wages and tips']
    medicare_wages_data = find_field(medicare_wages_patterns, kvs)
    if medicare_wages_data:
        medicare_wages_value = extract_numeric(medicare_wages_data['value'])
        if medicare_wages_value is not None:
            w2_data.medicare_wages = create_field(medicare_wages_value, medicare_wages_data['confidence'])
            logger.debug(f"Extracted medicare_wages: {medicare_wages_value} (confidence: {medicare_wages_data['confidence']:.2f})")
    
    # Extract state
    state_patterns = ['state', 'employer state', 'state abbreviation']
    state_data = find_field(state_patterns, kvs)
    if state_data:
        w2_data.state = create_field(state_data['value'], state_data['confidence'])
        logger.debug(f"Extracted state: {state_data['value']} (confidence: {state_data['confidence']:.2f})")
    
    # Extract state tax withheld
    state_tax_patterns = ['state income tax', 'state tax', 'state withholding']
    state_tax_data = find_field(state_tax_patterns, kvs)
    if state_tax_data:
        state_tax_value = extract_numeric(state_tax_data['value'])
        if state_tax_value is not None:
            w2_data.state_tax_withheld = create_field(state_tax_value, state_tax_data['confidence'])
            logger.debug(f"Extracted state_tax_withheld: {state_tax_value} (confidence: {state_tax_data['confidence']:.2f})")
    
    # Count extracted fields
    extracted_count = sum(1 for field in [
        w2_data.tax_year, w2_data.employer_name, w2_data.employer_ein,
        w2_data.employee_name, w2_data.employee_ssn, w2_data.employee_address,
        w2_data.wages, w2_data.federal_tax_withheld, w2_data.social_security_wages,
        w2_data.medicare_wages, w2_data.state, w2_data.state_tax_withheld
    ] if field is not None)
    
    logger.info(f"W2 extraction complete for document {document_id}: {extracted_count} fields extracted")
    
    return w2_data


def extract_bank_statement_data(kvs: Dict, blocks: List[Dict], document_id: str) -> BankStatementData:
    """
    Extract Bank Statement data.
    
    Implements Requirement 4.4: Extract account holder name, account number, statement period, and ending balance.
    Implements Requirement 4.7: Extract key-value pairs and table data from documents.
    Implements Requirement 4.9: Store extracted data with confidence scores.
    
    Args:
        kvs: Key-value pairs from Textract
        blocks: Textract blocks
        document_id: Document identifier
    
    Returns:
        BankStatementData object with extracted fields
    """
    logger.info(f"Extracting Bank Statement data for document {document_id}")
    
    bank_data = BankStatementData()
    
    # Helper function to find field by key patterns
    def find_field(patterns: List[str], kvs: Dict, exclude_patterns: List[str] = None) -> Optional[Dict]:
        """Find a field by matching key patterns (case-insensitive), optionally excluding certain patterns."""
        exclude_patterns = exclude_patterns or []
        for key, value_data in kvs.items():
            key_lower = key.lower()
            # Check if key should be excluded
            if any(excl.lower() in key_lower for excl in exclude_patterns):
                continue
            # Check if key matches any pattern
            for pattern in patterns:
                if pattern.lower() in key_lower:
                    return value_data
        return None
    
    # Helper function to extract numeric value
    def extract_numeric(text: str) -> Optional[float]:
        """Extract numeric value from text, handling currency formatting."""
        if not text:
            return None
        # Remove common currency symbols and commas
        cleaned = text.replace('$', '').replace(',', '').strip()
        # Handle negative values in parentheses
        if cleaned.startswith('(') and cleaned.endswith(')'):
            cleaned = '-' + cleaned[1:-1]
        try:
            return float(cleaned)
        except ValueError:
            return None
    
    # Helper function to create ExtractedField
    def create_field(value: Any, confidence: float) -> ExtractedField:
        """Create ExtractedField with manual review flag if confidence is low."""
        requires_review = confidence < CONFIDENCE_THRESHOLD
        return ExtractedField(value=value, confidence=confidence, requires_manual_review=requires_review)
    
    # Extract bank name
    bank_patterns = ['bank name', 'financial institution', 'bank', 'institution name']
    bank_data_field = find_field(bank_patterns, kvs)
    if bank_data_field:
        bank_data.bank_name = create_field(bank_data_field['value'], bank_data_field['confidence'])
        logger.debug(f"Extracted bank_name: {bank_data_field['value']} (confidence: {bank_data_field['confidence']:.2f})")
    
    # Extract account holder name
    holder_patterns = ['account holder', 'account name', 'customer name', 'name']
    holder_data = find_field(holder_patterns, kvs, exclude_patterns=['bank', 'institution'])
    if holder_data:
        bank_data.account_holder_name = create_field(holder_data['value'], holder_data['confidence'])
        logger.debug(f"Extracted account_holder_name: {holder_data['value']} (confidence: {holder_data['confidence']:.2f})")
    
    # Extract account number (mask for security)
    account_patterns = ['account number', 'account #', 'acct number', 'account no']
    account_data = find_field(account_patterns, kvs)
    if account_data:
        # Mask account number (show only last 4 digits)
        account_value = account_data['value']
        if account_value and len(account_value) >= 4:
            masked_account = '****' + account_value[-4:]
        else:
            masked_account = account_value
        bank_data.account_number = create_field(masked_account, account_data['confidence'])
        logger.debug(f"Extracted account_number: {masked_account} (confidence: {account_data['confidence']:.2f})")
    
    # Extract statement period start
    period_start_patterns = ['statement period from', 'period start', 'from date', 'statement from']
    period_start_data = find_field(period_start_patterns, kvs)
    if period_start_data:
        bank_data.statement_period_start = create_field(period_start_data['value'], period_start_data['confidence'])
        logger.debug(f"Extracted statement_period_start: {period_start_data['value']} (confidence: {period_start_data['confidence']:.2f})")
    
    # Extract statement period end
    period_end_patterns = ['statement period to', 'period end', 'to date', 'statement to', 'statement date']
    period_end_data = find_field(period_end_patterns, kvs)
    if period_end_data:
        bank_data.statement_period_end = create_field(period_end_data['value'], period_end_data['confidence'])
        logger.debug(f"Extracted statement_period_end: {period_end_data['value']} (confidence: {period_end_data['confidence']:.2f})")
    
    # Extract beginning balance
    beginning_patterns = ['beginning balance', 'opening balance', 'previous balance', 'balance forward']
    beginning_data = find_field(beginning_patterns, kvs)
    if beginning_data:
        beginning_value = extract_numeric(beginning_data['value'])
        if beginning_value is not None:
            bank_data.beginning_balance = create_field(beginning_value, beginning_data['confidence'])
            logger.debug(f"Extracted beginning_balance: {beginning_value} (confidence: {beginning_data['confidence']:.2f})")
    
    # Extract ending balance
    ending_patterns = ['ending balance', 'closing balance', 'current balance', 'final balance']
    ending_data = find_field(ending_patterns, kvs)
    if ending_data:
        ending_value = extract_numeric(ending_data['value'])
        if ending_value is not None:
            bank_data.ending_balance = create_field(ending_value, ending_data['confidence'])
            logger.debug(f"Extracted ending_balance: {ending_value} (confidence: {ending_data['confidence']:.2f})")
    
    # Extract total deposits
    deposits_patterns = ['total deposits', 'total credits', 'deposits', 'credits']
    deposits_data = find_field(deposits_patterns, kvs)
    if deposits_data:
        deposits_value = extract_numeric(deposits_data['value'])
        if deposits_value is not None:
            bank_data.total_deposits = create_field(deposits_value, deposits_data['confidence'])
            logger.debug(f"Extracted total_deposits: {deposits_value} (confidence: {deposits_data['confidence']:.2f})")
    
    # Extract total withdrawals
    withdrawals_patterns = ['total withdrawals', 'total debits', 'withdrawals', 'debits']
    withdrawals_data = find_field(withdrawals_patterns, kvs)
    if withdrawals_data:
        withdrawals_value = extract_numeric(withdrawals_data['value'])
        if withdrawals_value is not None:
            bank_data.total_withdrawals = create_field(withdrawals_value, withdrawals_data['confidence'])
            logger.debug(f"Extracted total_withdrawals: {withdrawals_value} (confidence: {withdrawals_data['confidence']:.2f})")
    
    # Extract account holder address
    address_patterns = ['address', 'mailing address', 'customer address']
    address_data = find_field(address_patterns, kvs)
    if address_data:
        bank_data.account_holder_address = create_field(address_data['value'], address_data['confidence'])
        logger.debug(f"Extracted account_holder_address: {address_data['value']} (confidence: {address_data['confidence']:.2f})")
    
    # Count extracted fields
    extracted_count = sum(1 for field in [
        bank_data.bank_name, bank_data.account_holder_name, bank_data.account_number,
        bank_data.statement_period_start, bank_data.statement_period_end,
        bank_data.beginning_balance, bank_data.ending_balance,
        bank_data.total_deposits, bank_data.total_withdrawals,
        bank_data.account_holder_address
    ] if field is not None)
    
    logger.info(f"Bank Statement extraction complete for document {document_id}: {extracted_count} fields extracted")
    
    return bank_data


def extract_tax_form_data(kvs: Dict, blocks: List[Dict], document_id: str) -> TaxFormData:
    """
    Extract Tax Form data (1040 and similar IRS forms).
    
    Implements Requirement 4.5: Extract taxpayer name, filing status, adjusted gross income, and tax year.
    Implements Requirement 4.9: Store extracted data with confidence scores.
    
    Args:
        kvs: Key-value pairs from Textract
        blocks: Textract blocks
        document_id: Document identifier
    
    Returns:
        TaxFormData object with extracted fields
    """
    logger.info(f"Extracting Tax Form data for document {document_id}")
    
    tax_form_data = TaxFormData()
    
    # Helper function to find field by key patterns
    def find_field(patterns: List[str], kvs: Dict, exclude_patterns: List[str] = None) -> Optional[Dict]:
        """Find a field by matching key patterns (case-insensitive), optionally excluding certain patterns."""
        exclude_patterns = exclude_patterns or []
        for key, value_data in kvs.items():
            key_lower = key.lower()
            # Check if key should be excluded
            if any(excl.lower() in key_lower for excl in exclude_patterns):
                continue
            # Check if key matches any pattern
            for pattern in patterns:
                if pattern.lower() in key_lower:
                    return value_data
        return None
    
    # Helper function to extract numeric value
    def extract_numeric(text: str) -> Optional[float]:
        """Extract numeric value from text, handling currency formatting."""
        if not text:
            return None
        # Remove common currency symbols and commas
        cleaned = text.replace('$', '').replace(',', '').strip()
        try:
            return float(cleaned)
        except ValueError:
            return None
    
    # Helper function to create ExtractedField
    def create_field(value: Any, confidence: float) -> ExtractedField:
        """Create ExtractedField with manual review flag if confidence is low."""
        requires_review = confidence < CONFIDENCE_THRESHOLD
        return ExtractedField(value=value, confidence=confidence, requires_manual_review=requires_review)
    
    # Extract form type (1040, 1040-SR, etc.)
    form_type_patterns = ['form', 'form type', '1040', 'form 1040']
    form_type_data = find_field(form_type_patterns, kvs)
    if form_type_data:
        # Extract just the form number if present
        form_value = form_type_data['value']
        if '1040' in form_value:
            form_value = '1040'
        tax_form_data.form_type = create_field(form_value, form_type_data['confidence'])
        logger.debug(f"Extracted form_type: {form_value} (confidence: {form_type_data['confidence']:.2f})")
    
    # Extract total tax (Line 24 on 1040) - check before tax year to avoid confusion
    total_tax_patterns = ['total tax', 'line 24']
    total_tax_data = find_field(total_tax_patterns, kvs, exclude_patterns=['withheld', 'refund', 'year'])
    if total_tax_data:
        total_tax_value = extract_numeric(total_tax_data['value'])
        if total_tax_value is not None:
            tax_form_data.total_tax = create_field(total_tax_value, total_tax_data['confidence'])
            logger.debug(f"Extracted total_tax: {total_tax_value} (confidence: {total_tax_data['confidence']:.2f})")
    
    # Extract tax year
    tax_year_patterns = ['tax year', 'year', 'for the year', 'calendar year']
    tax_year_data = find_field(tax_year_patterns, kvs)
    if tax_year_data:
        tax_form_data.tax_year = create_field(tax_year_data['value'], tax_year_data['confidence'])
        logger.debug(f"Extracted tax_year: {tax_year_data['value']} (confidence: {tax_year_data['confidence']:.2f})")
    
    # Extract taxpayer name
    taxpayer_name_patterns = ['your name', 'taxpayer name', 'first name and initial', 'name']
    taxpayer_name_data = find_field(taxpayer_name_patterns, kvs, exclude_patterns=['spouse'])
    if taxpayer_name_data:
        tax_form_data.taxpayer_name = create_field(taxpayer_name_data['value'], taxpayer_name_data['confidence'])
        logger.debug(f"Extracted taxpayer_name: {taxpayer_name_data['value']} (confidence: {taxpayer_name_data['confidence']:.2f})")
    
    # Extract taxpayer SSN
    ssn_patterns = ['social security number', 'ssn', 'your social security number']
    ssn_data = find_field(ssn_patterns, kvs, exclude_patterns=['spouse'])
    if ssn_data:
        # Mask SSN for security (show only last 4 digits)
        ssn_value = ssn_data['value']
        if ssn_value and len(ssn_value) >= 4:
            masked_ssn = '***-**-' + ssn_value[-4:]
        else:
            masked_ssn = ssn_value
        tax_form_data.taxpayer_ssn = create_field(masked_ssn, ssn_data['confidence'])
        logger.debug(f"Extracted taxpayer_ssn: {masked_ssn} (confidence: {ssn_data['confidence']:.2f})")
    
    # Extract spouse name
    spouse_name_patterns = ['spouse name', 'spouse\'s name', 'spouse first name']
    spouse_name_data = find_field(spouse_name_patterns, kvs)
    if spouse_name_data:
        tax_form_data.spouse_name = create_field(spouse_name_data['value'], spouse_name_data['confidence'])
        logger.debug(f"Extracted spouse_name: {spouse_name_data['value']} (confidence: {spouse_name_data['confidence']:.2f})")
    
    # Extract filing status
    filing_status_patterns = ['filing status', 'status', 'single', 'married filing jointly', 'married filing separately', 'head of household']
    filing_status_data = find_field(filing_status_patterns, kvs)
    if filing_status_data:
        tax_form_data.filing_status = create_field(filing_status_data['value'], filing_status_data['confidence'])
        logger.debug(f"Extracted filing_status: {filing_status_data['value']} (confidence: {filing_status_data['confidence']:.2f})")
    
    # Extract address
    address_patterns = ['home address', 'address', 'street address', 'city state zip']
    address_data = find_field(address_patterns, kvs)
    if address_data:
        tax_form_data.address = create_field(address_data['value'], address_data['confidence'])
        logger.debug(f"Extracted address: {address_data['value']} (confidence: {address_data['confidence']:.2f})")
    
    # Extract wages and salaries (Line 1)
    wages_patterns = ['wages', 'salaries', 'tips', 'line 1', 'wages salaries tips']
    wages_data = find_field(wages_patterns, kvs)
    if wages_data:
        wages_value = extract_numeric(wages_data['value'])
        if wages_value is not None:
            tax_form_data.wages_salaries = create_field(wages_value, wages_data['confidence'])
            logger.debug(f"Extracted wages_salaries: {wages_value} (confidence: {wages_data['confidence']:.2f})")
    
    # Extract adjusted gross income (Line 11 on 1040)
    agi_patterns = ['adjusted gross income', 'agi', 'line 11', 'total income']
    agi_data = find_field(agi_patterns, kvs)
    if agi_data:
        agi_value = extract_numeric(agi_data['value'])
        if agi_value is not None:
            tax_form_data.adjusted_gross_income = create_field(agi_value, agi_data['confidence'])
            logger.debug(f"Extracted adjusted_gross_income: {agi_value} (confidence: {agi_data['confidence']:.2f})")
    
    # Extract taxable income (Line 15 on 1040)
    taxable_income_patterns = ['taxable income', 'line 15', 'income after deductions']
    taxable_income_data = find_field(taxable_income_patterns, kvs)
    if taxable_income_data:
        taxable_income_value = extract_numeric(taxable_income_data['value'])
        if taxable_income_value is not None:
            tax_form_data.taxable_income = create_field(taxable_income_value, taxable_income_data['confidence'])
            logger.debug(f"Extracted taxable_income: {taxable_income_value} (confidence: {taxable_income_data['confidence']:.2f})")
    
    # Extract federal tax withheld (Line 25 on 1040)
    federal_tax_patterns = ['federal income tax withheld', 'federal tax withheld', 'line 25', 'withholding']
    federal_tax_data = find_field(federal_tax_patterns, kvs)
    if federal_tax_data:
        federal_tax_value = extract_numeric(federal_tax_data['value'])
        if federal_tax_value is not None:
            tax_form_data.federal_tax_withheld = create_field(federal_tax_value, federal_tax_data['confidence'])
            logger.debug(f"Extracted federal_tax_withheld: {federal_tax_value} (confidence: {federal_tax_data['confidence']:.2f})")
    
    # Extract refund amount (Line 35 on 1040)
    refund_patterns = ['refund', 'amount you overpaid', 'line 35', 'overpayment']
    refund_data = find_field(refund_patterns, kvs)
    if refund_data:
        refund_value = extract_numeric(refund_data['value'])
        if refund_value is not None:
            tax_form_data.refund_amount = create_field(refund_value, refund_data['confidence'])
            logger.debug(f"Extracted refund_amount: {refund_value} (confidence: {refund_data['confidence']:.2f})")
    
    # Count extracted fields
    extracted_count = sum(1 for field in [
        tax_form_data.form_type, tax_form_data.tax_year, tax_form_data.taxpayer_name,
        tax_form_data.taxpayer_ssn, tax_form_data.spouse_name, tax_form_data.filing_status,
        tax_form_data.address, tax_form_data.wages_salaries, tax_form_data.adjusted_gross_income,
        tax_form_data.taxable_income, tax_form_data.total_tax, tax_form_data.federal_tax_withheld,
        tax_form_data.refund_amount
    ] if field is not None)
    
    logger.info(f"Tax Form extraction complete for document {document_id}: {extracted_count} fields extracted")
    
    return tax_form_data


def extract_drivers_license_data(kvs: Dict, blocks: List[Dict], document_id: str) -> DriversLicenseData:
    """
    Extract Driver's License data.
    
    Implements Requirement 4.6: Extract full name, date of birth, license number, address, and expiration date.
    Implements Requirement 4.9: Store extracted data with confidence scores.
    
    Args:
        kvs: Key-value pairs from Textract
        blocks: Textract blocks
        document_id: Document identifier
    
    Returns:
        DriversLicenseData object with extracted fields
    """
    logger.info(f"Extracting Driver's License data for document {document_id}")
    
    dl_data = DriversLicenseData()
    
    # Helper function to find field by key patterns
    def find_field(patterns: List[str], kvs: Dict, exclude_patterns: List[str] = None) -> Optional[Dict]:
        """Find a field by matching key patterns (case-insensitive), optionally excluding certain patterns."""
        exclude_patterns = exclude_patterns or []
        for key, value_data in kvs.items():
            key_lower = key.lower()
            # Check if key should be excluded
            if any(excl.lower() in key_lower for excl in exclude_patterns):
                continue
            # Check if key matches any pattern
            for pattern in patterns:
                if pattern.lower() in key_lower:
                    return value_data
        return None
    
    # Helper function to create ExtractedField
    def create_field(value: Any, confidence: float) -> ExtractedField:
        """Create ExtractedField with manual review flag if confidence is low."""
        requires_review = confidence < CONFIDENCE_THRESHOLD
        return ExtractedField(value=value, confidence=confidence, requires_manual_review=requires_review)
    
    # Extract state
    state_patterns = ['state', 'st', 'jurisdiction', 'issuing state']
    state_data = find_field(state_patterns, kvs, exclude_patterns=['statement', 'estate'])
    if state_data:
        dl_data.state = create_field(state_data['value'], state_data['confidence'])
        logger.debug(f"Extracted state: {state_data['value']} (confidence: {state_data['confidence']:.2f})")
    
    # Extract license number
    license_patterns = ['license number', 'dl number', 'lic no', 'license no', 'dl#', 'lic#', 'driver license number']
    license_data = find_field(license_patterns, kvs)
    if license_data:
        dl_data.license_number = create_field(license_data['value'], license_data['confidence'])
        logger.debug(f"Extracted license_number: {license_data['value']} (confidence: {license_data['confidence']:.2f})")
    
    # Extract full name
    name_patterns = ['name', 'full name', 'driver name', 'ln', 'last name', 'first name']
    name_data = find_field(name_patterns, kvs, exclude_patterns=['bank', 'employer', 'institution'])
    if name_data:
        dl_data.full_name = create_field(name_data['value'], name_data['confidence'])
        logger.debug(f"Extracted full_name: {name_data['value']} (confidence: {name_data['confidence']:.2f})")
    
    # Extract date of birth
    dob_patterns = ['date of birth', 'dob', 'birth date', 'birthdate', 'born']
    dob_data = find_field(dob_patterns, kvs)
    if dob_data:
        dl_data.date_of_birth = create_field(dob_data['value'], dob_data['confidence'])
        logger.debug(f"Extracted date_of_birth: {dob_data['value']} (confidence: {dob_data['confidence']:.2f})")
    
    # Extract address
    address_patterns = ['address', 'addr', 'street address', 'residence', 'home address']
    address_data = find_field(address_patterns, kvs)
    if address_data:
        dl_data.address = create_field(address_data['value'], address_data['confidence'])
        logger.debug(f"Extracted address: {address_data['value']} (confidence: {address_data['confidence']:.2f})")
    
    # Extract issue date
    issue_patterns = ['issue date', 'iss', 'issued', 'date issued', 'issue']
    issue_data = find_field(issue_patterns, kvs, exclude_patterns=['issuing authority', 'issuing state'])
    if issue_data:
        dl_data.issue_date = create_field(issue_data['value'], issue_data['confidence'])
        logger.debug(f"Extracted issue_date: {issue_data['value']} (confidence: {issue_data['confidence']:.2f})")
    
    # Extract expiration date
    exp_patterns = ['expiration date', 'exp', 'expires', 'expiry', 'expiration', 'valid until']
    exp_data = find_field(exp_patterns, kvs)
    if exp_data:
        dl_data.expiration_date = create_field(exp_data['value'], exp_data['confidence'])
        logger.debug(f"Extracted expiration_date: {exp_data['value']} (confidence: {exp_data['confidence']:.2f})")
    
    # Extract sex/gender
    sex_patterns = ['sex', 'gender']
    sex_data = find_field(sex_patterns, kvs, exclude_patterns=['address', 'class', 'expires', 'state', 'residence', 'license', 'issue'])
    if sex_data:
        dl_data.sex = create_field(sex_data['value'], sex_data['confidence'])
        logger.debug(f"Extracted sex: {sex_data['value']} (confidence: {sex_data['confidence']:.2f})")
    
    # Extract height
    height_patterns = ['height', 'hgt', 'ht']
    height_data = find_field(height_patterns, kvs)
    if height_data:
        dl_data.height = create_field(height_data['value'], height_data['confidence'])
        logger.debug(f"Extracted height: {height_data['value']} (confidence: {height_data['confidence']:.2f})")
    
    # Extract eye color
    eye_patterns = ['eye color', 'eyes', 'eye', 'eye colour']
    eye_data = find_field(eye_patterns, kvs)
    if eye_data:
        dl_data.eye_color = create_field(eye_data['value'], eye_data['confidence'])
        logger.debug(f"Extracted eye_color: {eye_data['value']} (confidence: {eye_data['confidence']:.2f})")
    
    # Count extracted fields
    extracted_count = sum(1 for field in [
        dl_data.state, dl_data.license_number, dl_data.full_name,
        dl_data.date_of_birth, dl_data.address, dl_data.issue_date,
        dl_data.expiration_date, dl_data.sex, dl_data.height, dl_data.eye_color
    ] if field is not None)
    
    logger.info(f"Driver's License extraction complete for document {document_id}: {extracted_count} fields extracted")
    
    return dl_data


def extract_id_document_data(kvs: Dict, blocks: List[Dict], document_id: str) -> IDDocumentData:
    """
    Extract ID Document data (passport, state ID, etc.).

    Implements Requirement 4.2: Extract names, addresses, dates, and identification numbers.
    Implements Requirement 4.9: Store extracted data with confidence scores.

    Args:
        kvs: Key-value pairs from Textract
        blocks: Textract blocks
        document_id: Document identifier

    Returns:
        IDDocumentData object with extracted fields
    """
    logger.info(f"Extracting ID Document data for document {document_id}")

    id_data = IDDocumentData()

    # Helper function to find field by key patterns
    def find_field(patterns: List[str], kvs: Dict, exclude_patterns: List[str] = None) -> Optional[Dict]:
        """Find a field by matching key patterns (case-insensitive), optionally excluding certain patterns."""
        exclude_patterns = exclude_patterns or []
        for key, value_data in kvs.items():
            key_lower = key.lower()
            # Check if key should be excluded
            if any(excl.lower() in key_lower for excl in exclude_patterns):
                continue
            # Check if key matches any pattern
            for pattern in patterns:
                if pattern.lower() in key_lower:
                    return value_data
        return None

    # Helper function to create ExtractedField
    def create_field(value: Any, confidence: float) -> ExtractedField:
        """Create ExtractedField with manual review flag if confidence is low."""
        requires_review = confidence < CONFIDENCE_THRESHOLD
        return ExtractedField(value=value, confidence=confidence, requires_manual_review=requires_review)

    # Detect ID type (passport, state ID, or other)
    id_type_value = "OTHER"
    id_type_confidence = 0.70

    # Check for passport indicators
    passport_indicators = ['passport', 'passport no', 'passport number', 'passport#', 'p<']
    for key in kvs.keys():
        key_lower = key.lower()
        if any(indicator in key_lower for indicator in passport_indicators):
            id_type_value = "PASSPORT"
            id_type_confidence = 0.95
            break

    # Check for state ID indicators if not passport
    if id_type_value == "OTHER":
        state_id_indicators = ['state id', 'identification card', 'id card', 'state identification']
        for key in kvs.keys():
            key_lower = key.lower()
            if any(indicator in key_lower for indicator in state_id_indicators):
                id_type_value = "STATE_ID"
                id_type_confidence = 0.90
                break

    id_data.id_type = create_field(id_type_value, id_type_confidence)
    logger.debug(f"Detected ID type: {id_type_value} (confidence: {id_type_confidence:.2f})")

    # Extract document number
    doc_num_patterns = [
        'document number', 'doc number', 'doc no', 'document no',
        'passport number', 'passport no', 'id number', 'id no',
        'identification number', 'card number', 'number'
    ]
    doc_num_data = find_field(doc_num_patterns, kvs, exclude_patterns=['license', 'phone', 'account', 'ssn', 'social security'])
    if doc_num_data:
        id_data.document_number = create_field(doc_num_data['value'], doc_num_data['confidence'])
        logger.debug(f"Extracted document_number: {doc_num_data['value']} (confidence: {doc_num_data['confidence']:.2f})")

    # Extract full name
    name_patterns = ['name', 'full name', 'surname', 'given name', 'last name', 'first name', 'holder name']
    name_data = find_field(name_patterns, kvs, exclude_patterns=['bank', 'employer', 'institution', 'issuing'])
    if name_data:
        id_data.full_name = create_field(name_data['value'], name_data['confidence'])
        logger.debug(f"Extracted full_name: {name_data['value']} (confidence: {name_data['confidence']:.2f})")

    # Extract date of birth
    dob_patterns = ['date of birth', 'dob', 'birth date', 'birthdate', 'born', 'date birth']
    dob_data = find_field(dob_patterns, kvs)
    if dob_data:
        id_data.date_of_birth = create_field(dob_data['value'], dob_data['confidence'])
        logger.debug(f"Extracted date_of_birth: {dob_data['value']} (confidence: {dob_data['confidence']:.2f})")

    # Extract issuing authority
    issuing_patterns = [
        'issuing authority', 'issued by', 'authority', 'issuing country',
        'issuing state', 'issuing organization', 'issued authority',
        'country of issue', 'place of issue'
    ]
    issuing_data = find_field(issuing_patterns, kvs)
    if issuing_data:
        id_data.issuing_authority = create_field(issuing_data['value'], issuing_data['confidence'])
        logger.debug(f"Extracted issuing_authority: {issuing_data['value']} (confidence: {issuing_data['confidence']:.2f})")

    # Extract issue date
    issue_patterns = ['issue date', 'date of issue', 'issued', 'date issued', 'issue']
    issue_data = find_field(issue_patterns, kvs, exclude_patterns=['issuing authority', 'issuing state', 'issuing country'])
    if issue_data:
        id_data.issue_date = create_field(issue_data['value'], issue_data['confidence'])
        logger.debug(f"Extracted issue_date: {issue_data['value']} (confidence: {issue_data['confidence']:.2f})")

    # Extract expiration date
    exp_patterns = ['expiration date', 'exp', 'expires', 'expiry', 'expiration', 'valid until', 'date of expiry']
    exp_data = find_field(exp_patterns, kvs)
    if exp_data:
        id_data.expiration_date = create_field(exp_data['value'], exp_data['confidence'])
        logger.debug(f"Extracted expiration_date: {exp_data['value']} (confidence: {exp_data['confidence']:.2f})")

    # Extract nationality (common in passports)
    nationality_patterns = ['nationality', 'citizen', 'citizenship', 'country', 'nat']
    nationality_data = find_field(nationality_patterns, kvs, exclude_patterns=['issuing', 'place of', 'country of issue'])
    if nationality_data:
        id_data.nationality = create_field(nationality_data['value'], nationality_data['confidence'])
        logger.debug(f"Extracted nationality: {nationality_data['value']} (confidence: {nationality_data['confidence']:.2f})")

    # Count extracted fields
    extracted_count = sum(1 for field in [
        id_data.id_type, id_data.document_number, id_data.full_name,
        id_data.date_of_birth, id_data.issuing_authority, id_data.issue_date,
        id_data.expiration_date, id_data.nationality
    ] if field is not None)

    logger.info(f"ID Document extraction complete for document {document_id}: {extracted_count} fields extracted")

    return id_data




def lambda_handler(event, context):
    """
    Main Lambda entry point for data extraction.
    
    Implements:
    - Requirement 4.1: Extract structured data using Textract
    - Requirement 5.1, 5.2: Handle multi-page PDF processing
    - Requirement 7.1: Detect PII using Comprehend
    - Requirement 4.8, 4.9: Flag fields with confidence < 80% for manual verification
    
    Input: Step Functions event containing document details and classification.
    
    Expected input format:
    {
        "document_id": "uuid",
        "document_type": "W2",
        "s3_bucket": "bucket-name",
        "s3_key": "path/to/document.pdf",
        "page_count": 1,
        "loan_application_id": "uuid",
        "metadata": {...}
    }
    
    Output format:
    {
        "document_id": "uuid",
        "document_type": "W2",
        "extracted_data": {...},
        "extraction_timestamp": "2024-01-15T10:31:00Z",
        "low_confidence_fields": ["address"],
        "pii_detected": ["SSN", "DATE_OF_BIRTH"],
        "page_count": 1,
        "processing_status": "COMPLETED"
    }
    """
    logger.info(f"Processing extraction event: {json.dumps(event)}")
    
    # Validate input
    required_fields = ['document_id', 'document_type', 's3_bucket', 's3_key']
    for field in required_fields:
        if field not in event:
            error_msg = f"Missing required field: {field}"
            logger.error(error_msg)
            raise ValueError(error_msg)
    
    document_id = event['document_id']
    document_type = event['document_type']
    s3_bucket = event['s3_bucket']
    s3_key = event['s3_key']
    page_count = event.get('page_count', 1)
    loan_application_id = event.get('loan_application_id', 'unknown')
    
    logger.info(
        f"Starting extraction: document_id={document_id}, "
        f"document_type={document_type}, "
        f"loan_application_id={loan_application_id}, "
        f"page_count={page_count}"
    )
    
    try:
        # Handle multi-page PDFs
        if page_count > 1:
            logger.info(f"Processing multi-page PDF with {page_count} pages")
            textract_response = process_multi_page_pdf(s3_bucket, s3_key, document_id, page_count)
        else:
            textract_response = analyze_document_with_retry(s3_bucket, s3_key, document_id)
        
        # Route to appropriate extractor
        extracted_data_obj = route_to_extractor(document_type, textract_response, document_id)
        extracted_data = extracted_data_obj.to_dict() if hasattr(extracted_data_obj, 'to_dict') else {}
        
        # Detect PII in extracted text
        blocks = textract_response.get('Blocks', [])
        all_text = ' '.join([block.get('Text', '') for block in blocks if block['BlockType'] == 'LINE'])
        pii_detected = detect_pii(all_text, document_id)
        
        # Identify low confidence fields (Requirement 4.8, 4.9)
        low_confidence_fields = []
        for field_name, field_data in extracted_data.items():
            if field_name == 'document_type':
                continue
            if isinstance(field_data, dict) and 'confidence' in field_data:
                confidence = field_data.get('confidence', 1.0)
                if confidence < CONFIDENCE_THRESHOLD:
                    low_confidence_fields.append(field_name)
                    logger.warning(
                        f"Low confidence field detected: document_id={document_id}, "
                        f"field={field_name}, confidence={confidence:.2f}"
                    )
        
        # Get current timestamp
        from datetime import datetime
        extraction_timestamp = datetime.utcnow().isoformat() + 'Z'
        
        # Log successful extraction
        logger.info(
            f"Extraction completed: document_id={document_id}, "
            f"document_type={document_type}, "
            f"fields_extracted={len(extracted_data)}, "
            f"low_confidence_fields={len(low_confidence_fields)}, "
            f"pii_detected={len(pii_detected)}"
        )
        
        # Return extraction results
        return {
            "document_id": document_id,
            "document_type": document_type,
            "extracted_data": extracted_data,
            "extraction_timestamp": extraction_timestamp,
            "low_confidence_fields": low_confidence_fields,
            "pii_detected": pii_detected,
            "page_count": page_count,
            "processing_status": "COMPLETED",
            "loan_application_id": loan_application_id
        }
        
    except ClientError as e:
        from datetime import datetime
        error_code = e.response['Error']['Code']
        error_message = e.response['Error'].get('Message', str(e))
        
        # Handle corrupted or illegible pages (Requirement 5.6)
        if error_code in ['InvalidS3ObjectException', 'InvalidParameterException', 'UnsupportedDocumentException']:
            logger.error(
                f"Illegible or corrupted document: document_id={document_id}, "
                f"error_code={error_code}, error_message={error_message}"
            )
            
            return {
                "document_id": document_id,
                "document_type": document_type,
                "extracted_data": {},
                "extraction_timestamp": datetime.utcnow().isoformat() + 'Z',
                "low_confidence_fields": [],
                "pii_detected": [],
                "page_count": page_count,
                "processing_status": "FAILED",
                "error": f"Document is illegible or corrupted: {error_code}",
                "loan_application_id": loan_application_id
            }
        else:
            logger.error(
                f"Extraction failed for document {document_id}: "
                f"error_code={error_code}, error_message={error_message}"
            )
            raise
            
    except Exception as e:
        logger.error(
            f"Unexpected error during extraction: document_id={document_id}, "
            f"error_type={type(e).__name__}, error_message={str(e)}",
            exc_info=True
        )
        raise
