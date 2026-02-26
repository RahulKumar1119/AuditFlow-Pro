// src/main.tsx
import React from 'react';
import ReactDOM from 'react-dom/client';
import { Amplify } from 'aws-amplify';
import App from './App';
import './index.css'; // Make sure you have Tailwind/CSS imported here

// Configure Amplify (Replace with your actual Cognito details later)
Amplify.configure({
  Auth: {
    Cognito: {
      userPoolId: 'us-east-1_xxxxxxxxx',
      userPoolClientId: 'xxxxxxxxxxxxxxxxx',
    }
  }
});

ReactDOM.createRoot(document.getElementById('root') as HTMLElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
