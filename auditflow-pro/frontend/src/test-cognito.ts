// test-cognito.ts - Quick test to verify Cognito configuration
import { Amplify } from 'aws-amplify';

console.log('========================================');
console.log('Cognito Configuration Test');
console.log('========================================\n');

console.log('Environment Variables:');
console.log('VITE_COGNITO_USER_POOL_ID:', import.meta.env.VITE_COGNITO_USER_POOL_ID);
console.log('VITE_COGNITO_CLIENT_ID:', import.meta.env.VITE_COGNITO_CLIENT_ID);
console.log('VITE_COGNITO_REGION:', import.meta.env.VITE_COGNITO_REGION);
console.log('\n');

// Configure Amplify
Amplify.configure({
  Auth: {
    Cognito: {
      userPoolId: import.meta.env.VITE_COGNITO_USER_POOL_ID,
      userPoolClientId: import.meta.env.VITE_COGNITO_CLIENT_ID,
      loginWith: {
        email: true,
      },
    }
  }
});

console.log('Amplify configured successfully!');
console.log('\nExpected values:');
console.log('User Pool ID: ap-south-1_lIhrnyezu');
console.log('Client ID: 7n2nt2p6l7dhifjihhk7eaqjjd');
console.log('\nIf values above are undefined or incorrect, check:');
console.log('1. .env file exists in frontend/ directory');
console.log('2. Dev server was restarted after .env changes');
console.log('3. Variable names start with VITE_');
