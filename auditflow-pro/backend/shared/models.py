import json
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any, Type, TypeVar
from datetime import datetime

T = TypeVar('T')

@dataclass
class ExtractedField:
    """Represents a single extracted field with confidence tracking."""
    value: Any
    confidence: Optional[float] = None
    requires_manual_review: bool = False

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'value': self.value,
            'confidence': self.confidence,
            'requires_manual_review': self.requires_manual_review
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'ExtractedField':
        """Create ExtractedField from dictionary."""
        return cls(**data)

# --- Document Specific Schemas ---

@dataclass
class W2Data:
    """W2 Form extracted data schema."""
    document_type: str = "W2"
    tax_year: Optional[ExtractedField] = None
    employer_name: Optional[ExtractedField] = None
    employer_ein: Optional[ExtractedField] = None
    employee_name: Optional[ExtractedField] = None
    employee_ssn: Optional[ExtractedField] = None
    employee_address: Optional[ExtractedField] = None
    wages: Optional[ExtractedField] = None
    federal_tax_withheld: Optional[ExtractedField] = None
    social_security_wages: Optional[ExtractedField] = None
    medicare_wages: Optional[ExtractedField] = None
    state: Optional[ExtractedField] = None
    state_tax_withheld: Optional[ExtractedField] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        result = {'document_type': self.document_type}
        for key, value in asdict(self).items():
            if key != 'document_type' and value is not None:
                if isinstance(value, ExtractedField):
                    result[key] = value.to_dict()
                else:
                    result[key] = value
        return result

    @classmethod
    def from_dict(cls, data: dict) -> 'W2Data':
        """Create W2Data from dictionary."""
        obj = cls()
        for key, value in data.items():
            if key != 'document_type' and value is not None:
                if isinstance(value, dict) and 'value' in value:
                    setattr(obj, key, ExtractedField.from_dict(value))
                else:
                    setattr(obj, key, value)
        return obj

@dataclass
class BankStatementData:
    """Bank Statement extracted data schema."""
    document_type: str = "BANK_STATEMENT"
    bank_name: Optional[ExtractedField] = None
    account_holder_name: Optional[ExtractedField] = None
    account_number: Optional[ExtractedField] = None
    statement_period_start: Optional[ExtractedField] = None
    statement_period_end: Optional[ExtractedField] = None
    beginning_balance: Optional[ExtractedField] = None
    ending_balance: Optional[ExtractedField] = None
    total_deposits: Optional[ExtractedField] = None
    total_withdrawals: Optional[ExtractedField] = None
    account_holder_address: Optional[ExtractedField] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        result = {'document_type': self.document_type}
        for key, value in asdict(self).items():
            if key != 'document_type' and value is not None:
                if isinstance(value, ExtractedField):
                    result[key] = value.to_dict()
                else:
                    result[key] = value
        return result

    @classmethod
    def from_dict(cls, data: dict) -> 'BankStatementData':
        """Create BankStatementData from dictionary."""
        obj = cls()
        for key, value in data.items():
            if key != 'document_type' and value is not None:
                if isinstance(value, dict) and 'value' in value:
                    setattr(obj, key, ExtractedField.from_dict(value))
                else:
                    setattr(obj, key, value)
        return obj

@dataclass
class TaxFormData:
    """Tax Form (1040) extracted data schema."""
    document_type: str = "TAX_FORM"
    form_type: Optional[ExtractedField] = None
    tax_year: Optional[ExtractedField] = None
    taxpayer_name: Optional[ExtractedField] = None
    taxpayer_ssn: Optional[ExtractedField] = None
    spouse_name: Optional[ExtractedField] = None
    filing_status: Optional[ExtractedField] = None
    address: Optional[ExtractedField] = None
    wages_salaries: Optional[ExtractedField] = None
    adjusted_gross_income: Optional[ExtractedField] = None
    taxable_income: Optional[ExtractedField] = None
    total_tax: Optional[ExtractedField] = None
    federal_tax_withheld: Optional[ExtractedField] = None
    refund_amount: Optional[ExtractedField] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        result = {'document_type': self.document_type}
        for key, value in asdict(self).items():
            if key != 'document_type' and value is not None:
                if isinstance(value, ExtractedField):
                    result[key] = value.to_dict()
                else:
                    result[key] = value
        return result

    @classmethod
    def from_dict(cls, data: dict) -> 'TaxFormData':
        """Create TaxFormData from dictionary."""
        obj = cls()
        for key, value in data.items():
            if key != 'document_type' and value is not None:
                if isinstance(value, dict) and 'value' in value:
                    setattr(obj, key, ExtractedField.from_dict(value))
                else:
                    setattr(obj, key, value)
        return obj

@dataclass
class DriversLicenseData:
    """Driver's License extracted data schema."""
    document_type: str = "DRIVERS_LICENSE"
    state: Optional[ExtractedField] = None
    license_number: Optional[ExtractedField] = None
    full_name: Optional[ExtractedField] = None
    date_of_birth: Optional[ExtractedField] = None
    address: Optional[ExtractedField] = None
    issue_date: Optional[ExtractedField] = None
    expiration_date: Optional[ExtractedField] = None
    sex: Optional[ExtractedField] = None
    height: Optional[ExtractedField] = None
    eye_color: Optional[ExtractedField] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        result = {'document_type': self.document_type}
        for key, value in asdict(self).items():
            if key != 'document_type' and value is not None:
                if isinstance(value, ExtractedField):
                    result[key] = value.to_dict()
                else:
                    result[key] = value
        return result

    @classmethod
    def from_dict(cls, data: dict) -> 'DriversLicenseData':
        """Create DriversLicenseData from dictionary."""
        obj = cls()
        for key, value in data.items():
            if key != 'document_type' and value is not None:
                if isinstance(value, dict) and 'value' in value:
                    setattr(obj, key, ExtractedField.from_dict(value))
                else:
                    setattr(obj, key, value)
        return obj

@dataclass
class IDDocumentData:
    """ID Document extracted data schema."""
    document_type: str = "ID_DOCUMENT"
    id_type: Optional[ExtractedField] = None  # PASSPORT, STATE_ID, OTHER
    document_number: Optional[ExtractedField] = None
    full_name: Optional[ExtractedField] = None
    date_of_birth: Optional[ExtractedField] = None
    issuing_authority: Optional[ExtractedField] = None
    issue_date: Optional[ExtractedField] = None
    expiration_date: Optional[ExtractedField] = None
    nationality: Optional[ExtractedField] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        result = {'document_type': self.document_type}
        for key, value in asdict(self).items():
            if key != 'document_type' and value is not None:
                if isinstance(value, ExtractedField):
                    result[key] = value.to_dict()
                else:
                    result[key] = value
        return result

    @classmethod
    def from_dict(cls, data: dict) -> 'IDDocumentData':
        """Create IDDocumentData from dictionary."""
        obj = cls()
        for key, value in data.items():
            if key != 'document_type' and value is not None:
                if isinstance(value, dict) and 'value' in value:
                    setattr(obj, key, ExtractedField.from_dict(value))
                else:
                    setattr(obj, key, value)
        return obj


# --- Core Metadata and Audit Models ---

@dataclass
class DocumentMetadata:
    """Document metadata with extracted data and processing status."""
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
    processing_status: str = "PENDING"  # PENDING, PROCESSING, COMPLETED, FAILED
    extracted_data: Dict[str, Any] = field(default_factory=dict)
    extraction_timestamp: Optional[str] = None
    page_count: int = 1
    low_confidence_fields: List[str] = field(default_factory=list)
    requires_manual_review: bool = False
    pii_detected: List[str] = field(default_factory=list)
    encryption_key_id: Optional[str] = None
    ttl: Optional[int] = None

    def to_json(self) -> str:
        """Serialize to JSON string."""
        data = asdict(self)
        # Convert ExtractedField objects in extracted_data
        if 'extracted_data' in data and data['extracted_data']:
            for key, val in data['extracted_data'].items():
                if isinstance(val, ExtractedField):
                    data['extracted_data'][key] = val.to_dict()
        return json.dumps(data, default=str)

    @classmethod
    def from_json(cls, json_str: str) -> 'DocumentMetadata':
        """Deserialize from JSON string."""
        data = json.loads(json_str)
        # Reconstruct nested extracted_data if necessary
        if 'extracted_data' in data and data['extracted_data']:
            for key, val in data['extracted_data'].items():
                if isinstance(val, dict) and 'value' in val:
                    data['extracted_data'][key] = ExtractedField.from_dict(val)
        return cls(**data)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        data = asdict(self)
        # Convert ExtractedField objects in extracted_data
        if 'extracted_data' in data and data['extracted_data']:
            for key, val in data['extracted_data'].items():
                if isinstance(val, ExtractedField):
                    data['extracted_data'][key] = val.to_dict()
        return data

    @classmethod
    def from_dict(cls, data: dict) -> 'DocumentMetadata':
        """Create from dictionary."""
        # Reconstruct nested extracted_data if necessary
        if 'extracted_data' in data and data['extracted_data']:
            for key, val in data['extracted_data'].items():
                if isinstance(val, dict) and 'value' in val:
                    data['extracted_data'][key] = ExtractedField.from_dict(val)
        return cls(**data)

@dataclass
class GoldenRecordField:
    """A field in the Golden Record with source tracking."""
    value: Any
    source_document: str
    confidence: float
    alternative_values: List[Any] = field(default_factory=list)
    verified_by: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> 'GoldenRecordField':
        """Create from dictionary."""
        return cls(**data)

@dataclass
class GoldenRecord:
    """Consolidated authoritative view of applicant data."""
    loan_application_id: str
    created_timestamp: str
    name: Optional[GoldenRecordField] = None
    date_of_birth: Optional[GoldenRecordField] = None
    ssn: Optional[GoldenRecordField] = None
    address: Optional[GoldenRecordField] = None
    employer: Optional[GoldenRecordField] = None
    employer_ein: Optional[GoldenRecordField] = None
    annual_income: Optional[GoldenRecordField] = None
    bank_account: Optional[GoldenRecordField] = None
    ending_balance: Optional[GoldenRecordField] = None
    drivers_license_number: Optional[GoldenRecordField] = None
    drivers_license_state: Optional[GoldenRecordField] = None

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        result = {
            'loan_application_id': self.loan_application_id,
            'created_timestamp': self.created_timestamp
        }
        for key, value in asdict(self).items():
            if key not in ['loan_application_id', 'created_timestamp'] and value is not None:
                if isinstance(value, GoldenRecordField):
                    result[key] = value.to_dict()
                else:
                    result[key] = value
        return result

    @classmethod
    def from_dict(cls, data: dict) -> 'GoldenRecord':
        """Create from dictionary."""
        obj = cls(
            loan_application_id=data['loan_application_id'],
            created_timestamp=data['created_timestamp']
        )
        for key, value in data.items():
            if key not in ['loan_application_id', 'created_timestamp'] and value is not None:
                if isinstance(value, dict) and 'value' in value:
                    setattr(obj, key, GoldenRecordField.from_dict(value))
        return obj

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), default=str)

    @classmethod
    def from_json(cls, json_str: str) -> 'GoldenRecord':
        """Deserialize from JSON string."""
        return cls.from_dict(json.loads(json_str))

@dataclass
class Inconsistency:
    """Represents a data inconsistency detected across documents."""
    inconsistency_id: str
    field: str
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW
    expected_value: Any
    actual_value: Any
    source_documents: List[str]
    description: str
    detected_by: str
    document_pages: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> 'Inconsistency':
        """Create from dictionary."""
        return cls(**data)

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), default=str)

    @classmethod
    def from_json(cls, json_str: str) -> 'Inconsistency':
        """Deserialize from JSON string."""
        return cls.from_dict(json.loads(json_str))

@dataclass
class RiskFactor:
    """A contributing factor to the risk score."""
    factor: str
    points: int
    description: str

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> 'RiskFactor':
        """Create from dictionary."""
        return cls(**data)

@dataclass
class Alert:
    """An alert triggered during audit processing."""
    alert_type: str
    timestamp: str
    notification_sent: bool
    message: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> 'Alert':
        """Create from dictionary."""
        return cls(**data)

@dataclass
class AuditRecord:
    """Complete audit result for a loan application."""
    audit_record_id: str
    loan_application_id: str
    applicant_name: str
    audit_timestamp: str
    processing_duration_seconds: int
    status: str  # COMPLETED, IN_PROGRESS, FAILED
    documents: List[Dict[str, str]]
    golden_record: Dict[str, Any]
    inconsistencies: List[Inconsistency]
    risk_score: int
    risk_level: str  # LOW, MEDIUM, HIGH, CRITICAL
    risk_factors: List[RiskFactor]
    alerts_triggered: List[Alert] = field(default_factory=list)
    reviewed_by: Optional[str] = None
    review_timestamp: Optional[str] = None
    review_notes: Optional[str] = None
    archived: bool = False
    archive_timestamp: Optional[str] = None
    ttl: Optional[int] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        result = asdict(self)
        # Convert nested objects
        result['inconsistencies'] = [inc.to_dict() if isinstance(inc, Inconsistency) else inc 
                                     for inc in self.inconsistencies]
        result['risk_factors'] = [rf.to_dict() if isinstance(rf, RiskFactor) else rf 
                                 for rf in self.risk_factors]
        result['alerts_triggered'] = [alert.to_dict() if isinstance(alert, Alert) else alert 
                                      for alert in self.alerts_triggered]
        return result

    @classmethod
    def from_dict(cls, data: dict) -> 'AuditRecord':
        """Create from dictionary."""
        # Convert nested objects
        if 'inconsistencies' in data:
            data['inconsistencies'] = [
                Inconsistency.from_dict(inc) if isinstance(inc, dict) else inc
                for inc in data['inconsistencies']
            ]
        if 'risk_factors' in data:
            data['risk_factors'] = [
                RiskFactor.from_dict(rf) if isinstance(rf, dict) else rf
                for rf in data['risk_factors']
            ]
        if 'alerts_triggered' in data:
            data['alerts_triggered'] = [
                Alert.from_dict(alert) if isinstance(alert, dict) else alert
                for alert in data['alerts_triggered']
            ]
        return cls(**data)

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), default=str)

    @classmethod
    def from_json(cls, json_str: str) -> 'AuditRecord':
        """Deserialize from JSON string."""
        return cls.from_dict(json.loads(json_str))


# Helper function to get document data class by type
def get_document_data_class(document_type: str) -> Type:
    """Get the appropriate data class for a document type."""
    type_map = {
        'W2': W2Data,
        'BANK_STATEMENT': BankStatementData,
        'TAX_FORM': TaxFormData,
        'DRIVERS_LICENSE': DriversLicenseData,
        'ID_DOCUMENT': IDDocumentData
    }
    return type_map.get(document_type, dict)
