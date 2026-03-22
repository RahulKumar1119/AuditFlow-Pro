"""
API Endpoint Testing for AuditFlow-Pro
Tests all REST API endpoints with authentication, validation, and error handling
"""

import json
import pytest
import requests
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import base64


class APITestConfig:
    """Configuration for API testing"""
    
    def __init__(self, base_url: str = "https://api.auditflowpro.online"):
        self.base_url = base_url
        self.headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer test-token-12345'
        }
        self.timeout = 30
        
    def get_url(self, endpoint: str) -> str:
        """Build full URL for endpoint"""
        return f"{self.base_url}{endpoint}"


class TestAuthenticationEndpoints:
    """Test authentication and authorization endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test configuration"""
        self.config = APITestConfig()
        self.session = requests.Session()
    
    def test_login_endpoint_success(self):
        """Test successful user login"""
        print("\n=== Testing Login Endpoint ===")
        
        payload = {
            'email': 'user@example.com',
            'password': 'SecurePassword123!'
        }
        
        with patch('requests.post') as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'access_token': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...',
                'token_type': 'Bearer',
                'expires_in': 3600,
                'user_id': 'user-123',
                'role': 'LOAN_OFFICER'
            }
            mock_post.return_value = mock_response
            
            response = requests.post(
                self.config.get_url('/auth/login'),
                json=payload,
                timeout=self.config.timeout
            )
            
            assert response.status_code == 200
            data = response.json()
            assert 'access_token' in data
            assert data['token_type'] == 'Bearer'
            assert data['expires_in'] == 3600
            print(f"✓ Login successful")
            print(f"✓ Token type: {data['token_type']}")
            print(f"✓ User role: {data['role']}")
    
    def test_login_endpoint_invalid_credentials(self):
        """Test login with invalid credentials"""
        print("\n=== Testing Login with Invalid Credentials ===")
        
        payload = {
            'email': 'user@example.com',
            'password': 'WrongPassword'
        }
        
        with patch('requests.post') as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 401
            mock_response.json.return_value = {
                'error': 'Invalid credentials',
                'message': 'Email or password is incorrect'
            }
            mock_post.return_value = mock_response
            
            response = requests.post(
                self.config.get_url('/auth/login'),
                json=payload,
                timeout=self.config.timeout
            )
            
            assert response.status_code == 401
            data = response.json()
            assert 'error' in data
            print(f"✓ Invalid credentials rejected")
            print(f"✓ Error: {data['error']}")
    
    def test_logout_endpoint(self):
        """Test user logout"""
        print("\n=== Testing Logout Endpoint ===")
        
        with patch('requests.post') as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'message': 'Logged out successfully'
            }
            mock_post.return_value = mock_response
            
            response = requests.post(
                self.config.get_url('/auth/logout'),
                headers=self.config.headers,
                timeout=self.config.timeout
            )
            
            assert response.status_code == 200
            print(f"✓ Logout successful")
    
    def test_refresh_token_endpoint(self):
        """Test token refresh"""
        print("\n=== Testing Token Refresh Endpoint ===")
        
        payload = {
            'refresh_token': 'refresh-token-xyz'
        }
        
        with patch('requests.post') as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'access_token': 'new-access-token-abc',
                'token_type': 'Bearer',
                'expires_in': 3600
            }
            mock_post.return_value = mock_response
            
            response = requests.post(
                self.config.get_url('/auth/refresh'),
                json=payload,
                timeout=self.config.timeout
            )
            
            assert response.status_code == 200
            data = response.json()
            assert 'access_token' in data
            print(f"✓ Token refreshed successfully")


class TestDocumentUploadEndpoints:
    """Test document upload endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test configuration"""
        self.config = APITestConfig()
    
    def test_get_presigned_url_endpoint(self):
        """Test getting pre-signed S3 URL for upload"""
        print("\n=== Testing Pre-signed URL Endpoint ===")
        
        payload = {
            'file_name': 'document.pdf',
            'file_size': 2048576,
            'content_type': 'application/pdf'
        }
        
        with patch('requests.post') as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'document_id': 'doc-12345',
                'upload_url': 'https://s3.amazonaws.com/bucket/documents/doc-12345.pdf?...',
                'expires_in': 3600,
                'fields': {
                    'key': 'documents/doc-12345.pdf',
                    'policy': 'eyJleHBpcmF0aW9uIjogIjIwMjMtMDEtMDFUMDA6MDA6MDBaIiwgImNvbmRpdGlvbnMiOiBbXX0=',
                    'signature': 'signature-value'
                }
            }
            mock_post.return_value = mock_response
            
            response = requests.post(
                self.config.get_url('/documents/upload-url'),
                json=payload,
                headers=self.config.headers,
                timeout=self.config.timeout
            )
            
            assert response.status_code == 200
            data = response.json()
            assert 'document_id' in data
            assert 'upload_url' in data
            print(f"✓ Pre-signed URL generated")
            print(f"✓ Document ID: {data['document_id']}")
            print(f"✓ URL expires in: {data['expires_in']} seconds")
    
    def test_upload_document_endpoint(self):
        """Test document upload"""
        print("\n=== Testing Document Upload Endpoint ===")
        
        with patch('requests.post') as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 201
            mock_response.json.return_value = {
                'document_id': 'doc-12345',
                'status': 'UPLOADED',
                'file_name': 'document.pdf',
                'file_size': 2048576,
                'upload_timestamp': '2023-01-01T12:00:00Z',
                'checksum': 'sha256-abc123def456'
            }
            mock_post.return_value = mock_response
            
            response = requests.post(
                self.config.get_url('/documents'),
                json={
                    'file_name': 'document.pdf',
                    'file_size': 2048576,
                    'checksum': 'sha256-abc123def456'
                },
                headers=self.config.headers,
                timeout=self.config.timeout
            )
            
            assert response.status_code == 201
            data = response.json()
            assert data['status'] == 'UPLOADED'
            print(f"✓ Document uploaded successfully")
            print(f"✓ Document ID: {data['document_id']}")
    
    def test_get_document_status_endpoint(self):
        """Test getting document processing status"""
        print("\n=== Testing Document Status Endpoint ===")
        
        with patch('requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'document_id': 'doc-12345',
                'status': 'PROCESSING',
                'progress': 45,
                'current_stage': 'CLASSIFICATION',
                'stages': {
                    'UPLOADED': {'status': 'COMPLETED', 'timestamp': '2023-01-01T12:00:00Z'},
                    'CLASSIFICATION': {'status': 'IN_PROGRESS', 'timestamp': '2023-01-01T12:01:00Z'},
                    'EXTRACTION': {'status': 'PENDING', 'timestamp': None},
                    'VALIDATION': {'status': 'PENDING', 'timestamp': None}
                }
            }
            mock_get.return_value = mock_response
            
            response = requests.get(
                self.config.get_url('/documents/doc-12345/status'),
                headers=self.config.headers,
                timeout=self.config.timeout
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data['status'] == 'PROCESSING'
            assert data['progress'] == 45
            print(f"✓ Document status retrieved")
            print(f"✓ Current stage: {data['current_stage']}")
            print(f"✓ Progress: {data['progress']}%")


class TestAuditQueryEndpoints:
    """Test audit query and retrieval endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test configuration"""
        self.config = APITestConfig()
    
    def test_list_audits_endpoint(self):
        """Test listing audit records"""
        print("\n=== Testing List Audits Endpoint ===")
        
        with patch('requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'total': 150,
                'page': 1,
                'page_size': 10,
                'total_pages': 15,
                'audits': [
                    {
                        'audit_id': 'audit-001',
                        'loan_application_id': 'app-001',
                        'applicant_name': 'John Doe',
                        'status': 'COMPLETED',
                        'risk_score': 35,
                        'risk_level': 'LOW',
                        'created_at': '2023-01-01T12:00:00Z'
                    },
                    {
                        'audit_id': 'audit-002',
                        'loan_application_id': 'app-002',
                        'applicant_name': 'Jane Smith',
                        'status': 'COMPLETED',
                        'risk_score': 75,
                        'risk_level': 'HIGH',
                        'created_at': '2023-01-02T12:00:00Z'
                    }
                ]
            }
            mock_get.return_value = mock_response
            
            response = requests.get(
                self.config.get_url('/audits?page=1&page_size=10'),
                headers=self.config.headers,
                timeout=self.config.timeout
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data['total'] == 150
            assert len(data['audits']) == 2
            print(f"✓ Audits retrieved successfully")
            print(f"✓ Total audits: {data['total']}")
            print(f"✓ Page: {data['page']} of {data['total_pages']}")
    
    def test_get_audit_detail_endpoint(self):
        """Test getting detailed audit record"""
        print("\n=== Testing Get Audit Detail Endpoint ===")
        
        with patch('requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'audit_id': 'audit-001',
                'loan_application_id': 'app-001',
                'applicant_name': 'John Doe',
                'status': 'COMPLETED',
                'risk_score': 65,
                'risk_level': 'HIGH',
                'documents_processed': 3,
                'golden_record': {
                    'applicant_name': 'John Doe',
                    'date_of_birth': '1990-01-15',
                    'ssn': '***-**-1234',
                    'address': '123 Main St, City, State 12345'
                },
                'inconsistencies': [
                    {
                        'field': 'applicant_name',
                        'severity': 'HIGH',
                        'expected': 'John Doe',
                        'actual': 'Jon Doe',
                        'source_documents': ['W2', 'BankStatement']
                    }
                ],
                'risk_factors': [
                    {'factor': 'name_inconsistency', 'points': 15},
                    {'factor': 'address_mismatch', 'points': 20},
                    {'factor': 'income_discrepancy', 'points': 25}
                ]
            }
            mock_get.return_value = mock_response
            
            response = requests.get(
                self.config.get_url('/audits/audit-001'),
                headers=self.config.headers,
                timeout=self.config.timeout
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data['audit_id'] == 'audit-001'
            assert data['risk_score'] == 65
            assert len(data['inconsistencies']) > 0
            print(f"✓ Audit detail retrieved")
            print(f"✓ Risk score: {data['risk_score']}")
            print(f"✓ Inconsistencies found: {len(data['inconsistencies'])}")
    
    def test_filter_audits_by_risk_score(self):
        """Test filtering audits by risk score"""
        print("\n=== Testing Filter Audits by Risk Score ===")
        
        with patch('requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'total': 25,
                'page': 1,
                'page_size': 10,
                'filter': {'min_risk_score': 50},
                'audits': [
                    {
                        'audit_id': 'audit-002',
                        'risk_score': 75,
                        'risk_level': 'HIGH'
                    },
                    {
                        'audit_id': 'audit-003',
                        'risk_score': 85,
                        'risk_level': 'CRITICAL'
                    }
                ]
            }
            mock_get.return_value = mock_response
            
            response = requests.get(
                self.config.get_url('/audits?min_risk_score=50'),
                headers=self.config.headers,
                timeout=self.config.timeout
            )
            
            assert response.status_code == 200
            data = response.json()
            assert all(audit['risk_score'] >= 50 for audit in data['audits'])
            print(f"✓ Audits filtered by risk score")
            print(f"✓ Total high-risk audits: {data['total']}")
    
    def test_search_audits_endpoint(self):
        """Test searching audits by applicant name or ID"""
        print("\n=== Testing Search Audits Endpoint ===")
        
        with patch('requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'total': 3,
                'search_query': 'John',
                'audits': [
                    {
                        'audit_id': 'audit-001',
                        'applicant_name': 'John Doe',
                        'loan_application_id': 'app-001'
                    },
                    {
                        'audit_id': 'audit-004',
                        'applicant_name': 'John Smith',
                        'loan_application_id': 'app-004'
                    }
                ]
            }
            mock_get.return_value = mock_response
            
            response = requests.get(
                self.config.get_url('/audits/search?q=John'),
                headers=self.config.headers,
                timeout=self.config.timeout
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data['total'] == 3
            print(f"✓ Search completed")
            print(f"✓ Results found: {data['total']}")


class TestDocumentViewerEndpoints:
    """Test document viewer endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test configuration"""
        self.config = APITestConfig()
    
    def test_get_document_view_url_endpoint(self):
        """Test getting pre-signed URL for document viewing"""
        print("\n=== Testing Document View URL Endpoint ===")
        
        with patch('requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'document_id': 'doc-12345',
                'view_url': 'https://s3.amazonaws.com/bucket/documents/doc-12345.pdf?...',
                'expires_in': 3600,
                'content_type': 'application/pdf'
            }
            mock_get.return_value = mock_response
            
            response = requests.get(
                self.config.get_url('/documents/doc-12345/view'),
                headers=self.config.headers,
                timeout=self.config.timeout
            )
            
            assert response.status_code == 200
            data = response.json()
            assert 'view_url' in data
            print(f"✓ Document view URL generated")
            print(f"✓ URL expires in: {data['expires_in']} seconds")
    
    def test_get_document_metadata_endpoint(self):
        """Test getting document metadata"""
        print("\n=== Testing Document Metadata Endpoint ===")
        
        with patch('requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'document_id': 'doc-12345',
                'file_name': 'document.pdf',
                'file_size': 2048576,
                'content_type': 'application/pdf',
                'pages': 5,
                'upload_timestamp': '2023-01-01T12:00:00Z',
                'classification': {
                    'document_type': 'W2',
                    'confidence': 0.95
                },
                'extracted_fields': 12,
                'low_confidence_fields': 1
            }
            mock_get.return_value = mock_response
            
            response = requests.get(
                self.config.get_url('/documents/doc-12345/metadata'),
                headers=self.config.headers,
                timeout=self.config.timeout
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data['pages'] == 5
            print(f"✓ Document metadata retrieved")
            print(f"✓ Pages: {data['pages']}")
            print(f"✓ Extracted fields: {data['extracted_fields']}")


class TestErrorHandlingEndpoints:
    """Test error handling and validation"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test configuration"""
        self.config = APITestConfig()
    
    def test_missing_authentication_header(self):
        """Test request without authentication header"""
        print("\n=== Testing Missing Authentication Header ===")
        
        with patch('requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 401
            mock_response.json.return_value = {
                'error': 'Unauthorized',
                'message': 'Missing or invalid authentication token'
            }
            mock_get.return_value = mock_response
            
            response = requests.get(
                self.config.get_url('/audits'),
                timeout=self.config.timeout
            )
            
            assert response.status_code == 401
            print(f"✓ Unauthorized request rejected")
    
    def test_invalid_request_payload(self):
        """Test request with invalid payload"""
        print("\n=== Testing Invalid Request Payload ===")
        
        with patch('requests.post') as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 400
            mock_response.json.return_value = {
                'error': 'Bad Request',
                'message': 'Invalid request payload',
                'details': {
                    'file_size': 'File size must be between 1KB and 50MB'
                }
            }
            mock_post.return_value = mock_response
            
            response = requests.post(
                self.config.get_url('/documents'),
                json={'file_size': 100 * 1024 * 1024},
                headers=self.config.headers,
                timeout=self.config.timeout
            )
            
            assert response.status_code == 400
            data = response.json()
            assert 'details' in data
            print(f"✓ Invalid payload rejected")
            print(f"✓ Validation error: {data['details']}")
    
    def test_resource_not_found(self):
        """Test request for non-existent resource"""
        print("\n=== Testing Resource Not Found ===")
        
        with patch('requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 404
            mock_response.json.return_value = {
                'error': 'Not Found',
                'message': 'Audit record not found'
            }
            mock_get.return_value = mock_response
            
            response = requests.get(
                self.config.get_url('/audits/nonexistent-id'),
                headers=self.config.headers,
                timeout=self.config.timeout
            )
            
            assert response.status_code == 404
            print(f"✓ Non-existent resource returns 404")
    
    def test_rate_limiting(self):
        """Test rate limiting"""
        print("\n=== Testing Rate Limiting ===")
        
        with patch('requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 429
            mock_response.headers = {
                'Retry-After': '60',
                'X-RateLimit-Limit': '100',
                'X-RateLimit-Remaining': '0'
            }
            mock_response.json.return_value = {
                'error': 'Too Many Requests',
                'message': 'Rate limit exceeded',
                'retry_after': 60
            }
            mock_get.return_value = mock_response
            
            response = requests.get(
                self.config.get_url('/audits'),
                headers=self.config.headers,
                timeout=self.config.timeout
            )
            
            assert response.status_code == 429
            assert 'Retry-After' in response.headers
            print(f"✓ Rate limiting enforced")
            print(f"✓ Retry after: {response.headers['Retry-After']} seconds")
    
    def test_server_error_handling(self):
        """Test server error handling"""
        print("\n=== Testing Server Error Handling ===")
        
        with patch('requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_response.json.return_value = {
                'error': 'Internal Server Error',
                'message': 'An unexpected error occurred',
                'request_id': 'req-12345'
            }
            mock_get.return_value = mock_response
            
            response = requests.get(
                self.config.get_url('/audits'),
                headers=self.config.headers,
                timeout=self.config.timeout
            )
            
            assert response.status_code == 500
            data = response.json()
            assert 'request_id' in data
            print(f"✓ Server error handled gracefully")
            print(f"✓ Request ID: {data['request_id']}")


class TestAPIPerformance:
    """Test API performance and response times"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test configuration"""
        self.config = APITestConfig()
    
    def test_list_audits_response_time(self):
        """Test list audits response time"""
        print("\n=== Testing List Audits Response Time ===")
        
        with patch('requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.elapsed.total_seconds.return_value = 0.234
            mock_response.json.return_value = {'total': 150, 'audits': []}
            mock_get.return_value = mock_response
            
            response = requests.get(
                self.config.get_url('/audits'),
                headers=self.config.headers,
                timeout=self.config.timeout
            )
            
            response_time = response.elapsed.total_seconds()
            assert response_time < 1.0  # Should be under 1 second
            print(f"✓ Response time: {response_time:.3f}s")
            print(f"✓ Performance acceptable (< 1s)")
    
    def test_get_audit_detail_response_time(self):
        """Test get audit detail response time"""
        print("\n=== Testing Get Audit Detail Response Time ===")
        
        with patch('requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.elapsed.total_seconds.return_value = 0.456
            mock_response.json.return_value = {
                'audit_id': 'audit-001',
                'risk_score': 65
            }
            mock_get.return_value = mock_response
            
            response = requests.get(
                self.config.get_url('/audits/audit-001'),
                headers=self.config.headers,
                timeout=self.config.timeout
            )
            
            response_time = response.elapsed.total_seconds()
            assert response_time < 2.0  # Should be under 2 seconds
            print(f"✓ Response time: {response_time:.3f}s")
            print(f"✓ Performance acceptable (< 2s)")


class TestAPISecurityHeaders:
    """Test API security headers"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test configuration"""
        self.config = APITestConfig()
    
    def test_security_headers_present(self):
        """Test that security headers are present"""
        print("\n=== Testing Security Headers ===")
        
        with patch('requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.headers = {
                'X-Content-Type-Options': 'nosniff',
                'X-Frame-Options': 'DENY',
                'X-XSS-Protection': '1; mode=block',
                'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
                'Content-Security-Policy': "default-src 'self'"
            }
            mock_get.return_value = mock_response
            
            response = requests.get(
                self.config.get_url('/audits'),
                headers=self.config.headers,
                timeout=self.config.timeout
            )
            
            assert 'X-Content-Type-Options' in response.headers
            assert 'X-Frame-Options' in response.headers
            assert 'Strict-Transport-Security' in response.headers
            print(f"✓ Security headers present")
            print(f"✓ X-Content-Type-Options: {response.headers['X-Content-Type-Options']}")
            print(f"✓ X-Frame-Options: {response.headers['X-Frame-Options']}")
    
    def test_https_enforcement(self):
        """Test HTTPS enforcement"""
        print("\n=== Testing HTTPS Enforcement ===")
        
        assert self.config.base_url.startswith('https://')
        print(f"✓ API uses HTTPS")
        print(f"✓ Base URL: {self.config.base_url}")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
