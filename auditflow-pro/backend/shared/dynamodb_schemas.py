"""
DynamoDB table schema definitions for AuditFlow-Pro.

This module provides programmatic access to table schemas, indexes, and
configuration for use in repository classes, tests, and infrastructure code.
"""

from typing import Dict, List, Any
from dataclasses import dataclass, field


@dataclass
class AttributeDefinition:
    """DynamoDB attribute definition."""
    name: str
    type: str  # S (String), N (Number), B (Binary)
    description: str = ""


@dataclass
class KeySchema:
    """DynamoDB key schema (partition key and optional sort key)."""
    partition_key: str
    sort_key: str = None


@dataclass
class GlobalSecondaryIndex:
    """DynamoDB Global Secondary Index definition."""
    index_name: str
    partition_key: str
    sort_key: str = None
    projection_type: str = "ALL"
    description: str = ""


@dataclass
class TableSchema:
    """Complete DynamoDB table schema definition."""
    table_name: str
    partition_key: str
    sort_key: str = None
    attributes: List[AttributeDefinition] = field(default_factory=list)
    global_secondary_indexes: List[GlobalSecondaryIndex] = field(default_factory=list)
    billing_mode: str = "PAY_PER_REQUEST"
    encryption_enabled: bool = True
    ttl_enabled: bool = True
    ttl_attribute: str = "ttl"
    point_in_time_recovery: bool = True
    tags: Dict[str, str] = field(default_factory=dict)


# ==========================================
# AuditFlow-Documents Table Schema
# ==========================================

DOCUMENTS_TABLE_SCHEMA = TableSchema(
    table_name="AuditFlow-Documents",
    partition_key="document_id",
    attributes=[
        AttributeDefinition("document_id", "S", "Primary key - unique document identifier (UUID)"),
        AttributeDefinition("loan_application_id", "S", "Groups documents by loan application"),
        AttributeDefinition("upload_timestamp", "S", "ISO 8601 timestamp of document upload"),
        AttributeDefinition("processing_status", "S", "PENDING, PROCESSING, COMPLETED, FAILED"),
    ],
    global_secondary_indexes=[
        GlobalSecondaryIndex(
            index_name="loan_application_id-upload_timestamp-index",
            partition_key="loan_application_id",
            sort_key="upload_timestamp",
            description="Query all documents for a specific loan application, sorted by upload time"
        ),
        GlobalSecondaryIndex(
            index_name="processing_status-upload_timestamp-index",
            partition_key="processing_status",
            sort_key="upload_timestamp",
            description="Query documents by processing status (for audit queue display)"
        ),
    ],
    billing_mode="PAY_PER_REQUEST",
    encryption_enabled=True,
    ttl_enabled=True,
    ttl_attribute="ttl",
    point_in_time_recovery=True,
    tags={
        "Project": "AuditFlow-Pro",
        "Environment": "Production",
        "ManagedBy": "Infrastructure-Scripts"
    }
)


# ==========================================
# AuditFlow-AuditRecords Table Schema
# ==========================================

AUDIT_RECORDS_TABLE_SCHEMA = TableSchema(
    table_name="AuditFlow-AuditRecords",
    partition_key="audit_record_id",
    attributes=[
        AttributeDefinition("audit_record_id", "S", "Primary key - unique audit record identifier (UUID)"),
        AttributeDefinition("loan_application_id", "S", "Links audit to loan application"),
        AttributeDefinition("audit_timestamp", "S", "ISO 8601 timestamp when audit completed"),
        AttributeDefinition("risk_score", "N", "Calculated risk score (0-100)"),
        AttributeDefinition("status", "S", "COMPLETED, IN_PROGRESS, FAILED"),
    ],
    global_secondary_indexes=[
        GlobalSecondaryIndex(
            index_name="loan_application_id-audit_timestamp-index",
            partition_key="loan_application_id",
            sort_key="audit_timestamp",
            description="Query all audits for a specific loan application, sorted by time"
        ),
        GlobalSecondaryIndex(
            index_name="risk_score-audit_timestamp-index",
            partition_key="status",
            sort_key="risk_score",
            description="Query audits by status and filter/sort by risk score (for high-risk queue)"
        ),
        GlobalSecondaryIndex(
            index_name="status-audit_timestamp-index",
            partition_key="status",
            sort_key="audit_timestamp",
            description="Query audits by status, sorted by timestamp"
        ),
    ],
    billing_mode="PAY_PER_REQUEST",
    encryption_enabled=True,
    ttl_enabled=True,
    ttl_attribute="ttl",
    point_in_time_recovery=True,
    tags={
        "Project": "AuditFlow-Pro",
        "Environment": "Production",
        "ManagedBy": "Infrastructure-Scripts"
    }
)


# ==========================================
# Helper Functions
# ==========================================

def get_table_schema(table_name: str) -> TableSchema:
    """
    Get table schema by name.
    
    Args:
        table_name: Name of the table
        
    Returns:
        TableSchema object
        
    Raises:
        ValueError: If table name is not recognized
    """
    schemas = {
        "AuditFlow-Documents": DOCUMENTS_TABLE_SCHEMA,
        "AuditFlow-AuditRecords": AUDIT_RECORDS_TABLE_SCHEMA,
    }
    
    if table_name not in schemas:
        raise ValueError(f"Unknown table name: {table_name}")
    
    return schemas[table_name]


def get_gsi_names(table_name: str) -> List[str]:
    """
    Get list of GSI names for a table.
    
    Args:
        table_name: Name of the table
        
    Returns:
        List of GSI names
    """
    schema = get_table_schema(table_name)
    return [gsi.index_name for gsi in schema.global_secondary_indexes]


def get_gsi_by_name(table_name: str, index_name: str) -> GlobalSecondaryIndex:
    """
    Get GSI definition by name.
    
    Args:
        table_name: Name of the table
        index_name: Name of the GSI
        
    Returns:
        GlobalSecondaryIndex object
        
    Raises:
        ValueError: If GSI name is not found
    """
    schema = get_table_schema(table_name)
    
    for gsi in schema.global_secondary_indexes:
        if gsi.index_name == index_name:
            return gsi
    
    raise ValueError(f"GSI {index_name} not found in table {table_name}")


def to_boto3_attribute_definitions(schema: TableSchema) -> List[Dict[str, str]]:
    """
    Convert schema attributes to boto3 format.
    
    Args:
        schema: TableSchema object
        
    Returns:
        List of attribute definitions in boto3 format
    """
    return [
        {"AttributeName": attr.name, "AttributeType": attr.type}
        for attr in schema.attributes
    ]


def to_boto3_key_schema(schema: TableSchema) -> List[Dict[str, str]]:
    """
    Convert schema key to boto3 format.
    
    Args:
        schema: TableSchema object
        
    Returns:
        List of key schema elements in boto3 format
    """
    key_schema = [{"AttributeName": schema.partition_key, "KeyType": "HASH"}]
    
    if schema.sort_key:
        key_schema.append({"AttributeName": schema.sort_key, "KeyType": "RANGE"})
    
    return key_schema


def to_boto3_gsi_definitions(schema: TableSchema) -> List[Dict[str, Any]]:
    """
    Convert GSI definitions to boto3 format.
    
    Args:
        schema: TableSchema object
        
    Returns:
        List of GSI definitions in boto3 format
    """
    gsi_definitions = []
    
    for gsi in schema.global_secondary_indexes:
        key_schema = [{"AttributeName": gsi.partition_key, "KeyType": "HASH"}]
        
        if gsi.sort_key:
            key_schema.append({"AttributeName": gsi.sort_key, "KeyType": "RANGE"})
        
        gsi_def = {
            "IndexName": gsi.index_name,
            "KeySchema": key_schema,
            "Projection": {"ProjectionType": gsi.projection_type}
        }
        
        gsi_definitions.append(gsi_def)
    
    return gsi_definitions


def create_table_params(schema: TableSchema) -> Dict[str, Any]:
    """
    Generate complete boto3 create_table parameters.
    
    Args:
        schema: TableSchema object
        
    Returns:
        Dictionary of parameters for boto3 create_table call
    """
    params = {
        "TableName": schema.table_name,
        "AttributeDefinitions": to_boto3_attribute_definitions(schema),
        "KeySchema": to_boto3_key_schema(schema),
        "BillingMode": schema.billing_mode,
    }
    
    if schema.global_secondary_indexes:
        params["GlobalSecondaryIndexes"] = to_boto3_gsi_definitions(schema)
    
    if schema.tags:
        params["Tags"] = [{"Key": k, "Value": v} for k, v in schema.tags.items()]
    
    return params


# ==========================================
# Query Pattern Helpers
# ==========================================

class QueryPatterns:
    """Common query patterns for DynamoDB tables."""
    
    @staticmethod
    def documents_by_loan_application(loan_application_id: str) -> Dict[str, Any]:
        """
        Query pattern: Get all documents for a loan application.
        
        Args:
            loan_application_id: Loan application ID
            
        Returns:
            Query parameters for boto3
        """
        return {
            "TableName": "AuditFlow-Documents",
            "IndexName": "loan_application_id-upload_timestamp-index",
            "KeyConditionExpression": "loan_application_id = :loan_id",
            "ExpressionAttributeValues": {":loan_id": {"S": loan_application_id}}
        }
    
    @staticmethod
    def documents_by_status(status: str) -> Dict[str, Any]:
        """
        Query pattern: Get documents by processing status.
        
        Args:
            status: Processing status (PENDING, PROCESSING, COMPLETED, FAILED)
            
        Returns:
            Query parameters for boto3
        """
        return {
            "TableName": "AuditFlow-Documents",
            "IndexName": "processing_status-upload_timestamp-index",
            "KeyConditionExpression": "processing_status = :status",
            "ExpressionAttributeValues": {":status": {"S": status}}
        }
    
    @staticmethod
    def audits_by_loan_application(loan_application_id: str) -> Dict[str, Any]:
        """
        Query pattern: Get all audits for a loan application.
        
        Args:
            loan_application_id: Loan application ID
            
        Returns:
            Query parameters for boto3
        """
        return {
            "TableName": "AuditFlow-AuditRecords",
            "IndexName": "loan_application_id-audit_timestamp-index",
            "KeyConditionExpression": "loan_application_id = :loan_id",
            "ExpressionAttributeValues": {":loan_id": {"S": loan_application_id}},
            "ScanIndexForward": False  # Most recent first
        }
    
    @staticmethod
    def audits_by_risk_score(status: str, min_risk_score: int) -> Dict[str, Any]:
        """
        Query pattern: Get audits by status with minimum risk score.
        
        Args:
            status: Audit status (COMPLETED, IN_PROGRESS, FAILED)
            min_risk_score: Minimum risk score threshold
            
        Returns:
            Query parameters for boto3
        """
        return {
            "TableName": "AuditFlow-AuditRecords",
            "IndexName": "risk_score-audit_timestamp-index",
            "KeyConditionExpression": "#status = :status AND risk_score >= :threshold",
            "ExpressionAttributeNames": {"#status": "status"},
            "ExpressionAttributeValues": {
                ":status": {"S": status},
                ":threshold": {"N": str(min_risk_score)}
            }
        }
    
    @staticmethod
    def audits_by_status(status: str) -> Dict[str, Any]:
        """
        Query pattern: Get audits by status.
        
        Args:
            status: Audit status (COMPLETED, IN_PROGRESS, FAILED)
            
        Returns:
            Query parameters for boto3
        """
        return {
            "TableName": "AuditFlow-AuditRecords",
            "IndexName": "status-audit_timestamp-index",
            "KeyConditionExpression": "#status = :status",
            "ExpressionAttributeNames": {"#status": "status"},
            "ExpressionAttributeValues": {":status": {"S": status}}
        }


# ==========================================
# Constants
# ==========================================

# Table names
DOCUMENTS_TABLE = "AuditFlow-Documents"
AUDIT_RECORDS_TABLE = "AuditFlow-AuditRecords"

# Processing statuses
STATUS_PENDING = "PENDING"
STATUS_PROCESSING = "PROCESSING"
STATUS_COMPLETED = "COMPLETED"
STATUS_FAILED = "FAILED"

# Audit statuses
AUDIT_STATUS_IN_PROGRESS = "IN_PROGRESS"
AUDIT_STATUS_COMPLETED = "COMPLETED"
AUDIT_STATUS_FAILED = "FAILED"

# Risk levels
RISK_LEVEL_LOW = "LOW"
RISK_LEVEL_MEDIUM = "MEDIUM"
RISK_LEVEL_HIGH = "HIGH"
RISK_LEVEL_CRITICAL = "CRITICAL"

# Document types
DOC_TYPE_W2 = "W2"
DOC_TYPE_BANK_STATEMENT = "BANK_STATEMENT"
DOC_TYPE_TAX_FORM = "TAX_FORM"
DOC_TYPE_DRIVERS_LICENSE = "DRIVERS_LICENSE"
DOC_TYPE_ID_DOCUMENT = "ID_DOCUMENT"
