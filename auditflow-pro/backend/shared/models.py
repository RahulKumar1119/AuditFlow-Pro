import json
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any, Type, TypeVar

T = TypeVar('T')

@dataclass
class ExtractedField:
    value: Any
    confidence: Optional[float] = None
    requires_manual_review: bool = False

    @classmethod
    def from_dict(cls, data: dict) -> 'ExtractedField':
        return cls(**data)

# --- Document Specific Schemas ---

@dataclass
class W2Data:
    document_type: str = "W2"
    tax_year: Optional[ExtractedField] = None
    employer_name: Optional[ExtractedField] = None
    employer_ein: Optional[ExtractedField] = None
    employee_name: Optional[ExtractedField] = None
    employee_ssn: Optional[ExtractedField] = None
    employee_address: Optional[ExtractedField] = None
    wages: Optional[ExtractedField] = None
    federal_tax_withheld: Optional[ExtractedField] = None
    state_tax_withheld: Optional[ExtractedField] = None

@dataclass
class BankStatementData:
    document_type: str = "BANK_STATEMENT"
    bank_name: Optional[ExtractedField] = None
    account_holder_name: Optional[ExtractedField] = None
    account_number: Optional[ExtractedField] = None
    statement_period_start: Optional[ExtractedField] = None
    statement_period_end: Optional[ExtractedField] = None
    beginning_balance: Optional[ExtractedField] = None
    ending_balance: Optional[ExtractedField] = None

# --- Core Metadata and Audit Models ---

@dataclass
class DocumentMetadata:
    document_id: str
    loan_application_id: str
    s3_bucket: str
    s3_key: str
    upload_timestamp: str
    file_name: str
    file_size_bytes: int
    file_format: str
    checksum: str
    uploaded_by: str = "system"
    document_type: Optional[str] = None
    classification_confidence: Optional[float] = None
    processing_status: str = "PENDING"
    extracted_data: Dict[str, Any] = field(default_factory=dict)
    extraction_timestamp: Optional[str] = None
    page_count: int = 1
    low_confidence_fields: List[str] = field(default_factory=list)
    requires_manual_review: bool = False
    pii_detected: List[str] = field(default_factory=list)
    encryption_key_id: Optional[str] = None
    ttl: Optional[int] = None

    def to_json(self) -> str:
        return json.dumps(asdict(self))

    @classmethod
    def from_json(cls, json_str: str) -> 'DocumentMetadata':
        data = json.loads(json_str)
        # Reconstruct nested extracted_data if necessary
        if 'extracted_data' in data and data['extracted_data']:
            for key, val in data['extracted_data'].items():
                if isinstance(val, dict) and 'value' in val:
                    data['extracted_data'][key] = ExtractedField(**val)
        return cls(**data)

@dataclass
class GoldenRecordField:
    value: Any
    source_document: str
    confidence: float
    alternative_values: List[Any] = field(default_factory=list)
    verified_by: List[str] = field(default_factory=list)

@dataclass
class Inconsistency:
    inconsistency_id: str
    field: str
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW
    expected_value: Any
    actual_value: Any
    source_documents: List[str]
    description: str
    detected_by: str
    document_pages: List[Dict[str, Any]] = field(default_factory=list)

@dataclass
class AuditRecord:
    audit_record_id: str
    loan_application_id: str
    applicant_name: str
    audit_timestamp: str
    processing_duration_seconds: int
    status: str
    documents: List[Dict[str, str]]
    golden_record: Dict[str, Any]
    inconsistencies: List[Inconsistency]
    risk_score: int
    risk_level: str
    risk_factors: List[Dict[str, Any]]
    alerts_triggered: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_json(self) -> str:
        return json.dumps(asdict(self))
