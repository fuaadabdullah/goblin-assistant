import fs from 'fs';
import path from 'path';

const DANGEROUS_PATTERNS = [
  /SECRET/i,
  /PRIVATE/i,
  /API_KEY(?!.*PUBLIC)/i, // Allow PUBLIC_API_KEY but not API_KEY
  /PASSWORD/i,
  /CREDENTIALS/i,
];

// Allow list for known safe VITE_ variables
const ALLOWED_VITE_VARS = [
  'VITE_TURNSTILE_SITE_KEY', // Public key for Turnstile bot protection
];

function validateEnvFile(filePath: string) {
  const content = fs.readFileSync(filePath, 'utf-8');
  const lines = content.split('\n');
  const errors: string[] = [];

  lines.forEach((line, index) => {
    if (line.trim().startsWith('#')) return; // Skip comments

    if (line.includes('VITE_')) {
      const varName = line.split('=')[0].trim();

      // Skip allowed variables
      if (ALLOWED_VITE_VARS.includes(varName)) {
        return; // Skip this line
      }

      // Check for dangerous patterns
      DANGEROUS_PATTERNS.forEach((pattern) => {
        if (pattern.test(varName)) {
          errors.push(
            `Line ${index + 1}: Suspicious env var "${varName}" ` +
              `contains sensitive keyword. Remove or prefix without VITE_`
          );
        }
      });
    }
  });

  return errors;
}

// Run validation
const envFiles = ['.env', '.env.example', '.env.development'];
let hasErrors = false;

envFiles.forEach((file) => {
  const filePath = path.join(process.cwd(), file);
  if (fs.existsSync(filePath)) {
    const errors = validateEnvFile(filePath);
    if (errors.length > 0) {
      console.error(`\n🚨 Security issues in ${file}:\n`);
      errors.forEach((err) => console.error(`  - ${err}`));
      hasErrors = true;
    }
  }
});

if (hasErrors) {
  console.error('\n❌ Env validation failed. Fix security issues before committing.\n');
  process.exit(1);
} else {
  console.log('✅ Env files validated successfully\n');
}
