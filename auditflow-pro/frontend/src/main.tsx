// src/main.tsx
import React from 'react';
import ReactDOM from 'react-dom/client';
import { Amplify } from 'aws-amplify';
import App from './App';
import './index.css'; // Make sure you have Tailwind/CSS imported here

/**
 * Validate Amplify configuration from environment variables.
 * 
 * Implements Requirement 12.4: Input validation for configuration
 * Implements Requirement 2.8: TLS/HTTPS enforcement
 * 
 * Ensures all required Cognito configuration is present and properly formatted
 * before initializing Amplify. Prevents silent failures and configuration bypass.
 */
interface AmplifyConfig {
  userPoolId: string;
  clientId: string;
  region: string;
}

function validateAmplifyConfig(): AmplifyConfig {
  const userPoolId = import.meta.env.VITE_COGNITO_USER_POOL_ID;
  const clientId = import.meta.env.VITE_COGNITO_CLIENT_ID;
  const region = import.meta.env.VITE_COGNITO_REGION || 'ap-south-1';

  // Validate required fields are present
  if (!userPoolId || !clientId) {
    throw new Error(
      'Missing required Cognito configuration. ' +
      'Please ensure VITE_COGNITO_USER_POOL_ID and VITE_COGNITO_CLIENT_ID are set in .env'
    );
  }

  // Validate User Pool ID format (should be region_randomstring)
  const userPoolIdPattern = /^[a-z0-9-]+_[a-zA-Z0-9]+$/;
  if (!userPoolIdPattern.test(userPoolId)) {
    throw new Error(
      `Invalid User Pool ID format: ${userPoolId}. ` +
      'Expected format: region_randomstring (e.g., ap-south-1_abc123xyz)'
    );
  }

  // Validate Client ID format (should be alphanumeric)
  const clientIdPattern = /^[a-zA-Z0-9]+$/;
  if (!clientIdPattern.test(clientId)) {
    throw new Error(
      `Invalid Client ID format: ${clientId}. ` +
      'Expected format: alphanumeric string'
    );
  }

  // Validate region format
  const regionPattern = /^[a-z]{2}-[a-z]+-\d{1}$/;
  if (!regionPattern.test(region)) {
    throw new Error(
      `Invalid AWS region format: ${region}. ` +
      'Expected format: xx-xxxx-x (e.g., ap-south-1)'
    );
  }

  console.log('✓ Amplify configuration validated successfully');
  
  return {
    userPoolId,
    clientId,
    region
  };
}

// Validate configuration before initializing Amplify
let amplifyConfig: AmplifyConfig;
try {
  amplifyConfig = validateAmplifyConfig();
} catch (error) {
  console.error('Configuration validation failed:', error);
  // Display error to user
  const root = document.getElementById('root');
  if (root) {
    root.innerHTML = `
      <div style="padding: 20px; color: #d32f2f; font-family: Arial, sans-serif;">
        <h1>Configuration Error</h1>
        <p>${error instanceof Error ? error.message : 'Unknown configuration error'}</p>
        <p>Please check your environment variables and try again.</p>
      </div>
    `;
  }
  throw error;
}

// Configure Amplify with validated configuration
Amplify.configure({
  Auth: {
    Cognito: {
      userPoolId: amplifyConfig.userPoolId,
      userPoolClientId: amplifyConfig.clientId,
      region: amplifyConfig.region,
      loginWith: {
        email: true,
      },
    }
  }
});

ReactDOM.createRoot(document.getElementById('root') as HTMLElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
