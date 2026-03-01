// auditflow-pro/frontend/src/services/api.ts

import { fetchAuthSession } from 'aws-amplify/auth';

// Update this line to use import.meta.env
const API_URL = import.meta.env.VITE_API_URL || ''; 

export interface AuditRecord {
  audit_record_id: string;
  loan_application_id: string;
  applicant_name?: string;
  audit_timestamp?: string;
  status: string;
  risk_level: string;
  risk_score: number;
  golden_record?: {
    first_name?: { value: string };
    last_name?: { value: string };
    ssn?: { value: string };
    annual_income?: { value: number };
  };
  risk_factors?: Array<{ description: string }>;
  inconsistencies?: Array<{
    id: string;
    field_name: string;
    severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
    expected_value: string;
    actual_value: string;
    sources: Array<{
      documentId: string;
      type: string;
      page: number;
    }>;
  }>;
}

export interface DocumentViewResponse {
  view_url: string;
}

export interface UploadUrlResponse {
  upload_url_data: {
    url: string;
    fields: Record<string, string>;
    document_id: string;
  };
} 

export const getAuthToken = async (): Promise<string> => {
  try {
    const session = await fetchAuthSession();
    const token = session.tokens?.idToken;
    if (!token) {
      throw new Error("No ID token found in session");
    }
    return token.toString();
  } catch (error) {
    console.error("No valid session found", error);
    throw new Error("Authentication required");
  }
};

export const fetchAudits = async (limit = 20, nextToken: Record<string, unknown> | null = null): Promise<{ items: AuditRecord[] }> => {
  const token = await getAuthToken();
  let url = `${API_URL}/audits?limit=${limit}`;
  if (nextToken) {
    url += `&ExclusiveStartKey=${encodeURIComponent(JSON.stringify(nextToken))}`;
  }

  const response = await fetch(url, {
    method: 'GET',
    headers: {
      'Authorization': token,
      'Content-Type': 'application/json'
    }
  });

  if (!response.ok) throw new Error('Failed to fetch audit records');
  return response.json();
};

// Add this export to frontend/src/services/api.ts

// Fetch the full audit record for Task 20.1
export const fetchAuditById = async (id: string): Promise<AuditRecord> => {
  const token = await getAuthToken();
  const url = `${import.meta.env.VITE_API_URL || ''}/audits/${id}`;

  const response = await fetch(url, {
    method: 'GET',
    headers: {
      'Authorization': token,
      'Content-Type': 'application/json'
    }
  });

  if (!response.ok) throw new Error('Failed to fetch audit details');
  return response.json();
};

// Log PII access events for Task 20.3
export const logPiiAccess = async (auditId: string, fieldName: string): Promise<void> => {
  const token = await getAuthToken();
  const url = `${import.meta.env.VITE_API_URL || ''}/audits/${auditId}/log-access`;

  // Fire and forget logging endpoint
  await fetch(url, {
    method: 'POST',
    headers: {
      'Authorization': token,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ field: fieldName, timestamp: new Date().toISOString() })
  }).catch(console.error);
};

export const requestUploadUrl = async (
  fileName: string,
  contentType: string,
  loanApplicationId: string,
  checksum: string
): Promise<UploadUrlResponse> => {
  const token = await getAuthToken();
  const url = `${API_URL}/documents`;

  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Authorization': token,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      file_name: fileName,
      content_type: contentType,
      loan_application_id: loanApplicationId,
      checksum: checksum // Task 17.3: Send checksum to backend to enforce integrity
    })
  });

  if (!response.ok) {
    // Attempt to extract a descriptive error message from the backend
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.error || 'Failed to get upload URL from server');
  }

  return response.json();
};
// Add to frontend/src/services/api.ts

export const fetchDocumentViewUrl = async (documentId: string, loanApplicationId: string): Promise<DocumentViewResponse> => {
  const token = await getAuthToken();
  const url = `${import.meta.env.VITE_API_URL || ''}/documents/${documentId}/view?loan_application_id=${loanApplicationId}`;

  const response = await fetch(url, {
    method: 'GET',
    headers: {
      'Authorization': token,
      'Content-Type': 'application/json'
    }
  });

  if (!response.ok) throw new Error('Failed to get document view URL');
  return response.json();
};
