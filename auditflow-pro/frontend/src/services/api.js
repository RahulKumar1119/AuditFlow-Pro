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
