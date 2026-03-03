// check-env.js - Debug script to verify environment variables
import { readFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

console.log('========================================');
console.log('Environment Variables Check');
console.log('========================================\n');

// Read .env file
const envPath = join(__dirname, '.env');
const envContent = readFileSync(envPath, 'utf-8');

console.log('.env file contents:');
console.log(envContent);
console.log('\n========================================\n');

// Parse .env
const envVars = {};
envContent.split('\n').forEach(line => {
  const match = line.match(/^([^#=]+)=(.*)$/);
  if (match) {
    envVars[match[1].trim()] = match[2].trim();
  }
});

console.log('Parsed environment variables:');
console.log(JSON.stringify(envVars, null, 2));
console.log('\n========================================\n');

console.log('Expected Cognito Configuration:');
console.log('User Pool ID:', envVars.VITE_COGNITO_USER_POOL_ID);
console.log('Client ID:', envVars.VITE_COGNITO_CLIENT_ID);
console.log('Region:', envVars.VITE_COGNITO_REGION);
