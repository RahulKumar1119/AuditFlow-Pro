// auditflow-pro/frontend/src/services/api.js

import { fetchAuthSession } from 'aws-amplify/auth';

// Update this line to use import.meta.env
const API_URL = import.meta.env.VITE_API_URL || ''; 

export const getAuthToken = async () => {
  try {
    const session = await fetchAuthSession();
    return session.tokens.idToken.toString();
  } catch (error) {
    console.error("No valid session found", error);
    throw new Error("Authentication required");
  }
};

export const fetchAudits = async (limit = 20, nextToken = null) => {
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

// Add this export to frontend/src/services/api.js

export const requestUploadUrl = async (fileName, contentType, loanApplicationId, checksum) => {
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
