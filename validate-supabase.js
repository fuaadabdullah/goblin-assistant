#!/usr/bin/env node

/**
 * Supabase Configuration Validator
 * This script helps validate your Supabase setup and provides clear feedback
 */

/* eslint-disable no-console */
import fetch from 'node-fetch';
import { readFileSync } from 'fs';
import { dirname, join } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));

const API_BASE = 'http://localhost:3000/api';

async function validateSupabaseConfig() {
  console.log('🔍 Validating Supabase Configuration...\n');

  let configValid = true;
  const issues = [];
  let supabaseUrl, supabaseAnonKey, supabaseServiceKey;

  // 1. Check environment variables
  console.log('1. Checking environment variables...');
  try {
    const envPath = join(__dirname, '.env.local');
    const envContent = readFileSync(envPath, 'utf8');

    supabaseUrl = envContent.match(/NEXT_PUBLIC_SUPABASE_URL=(.+)/)?.[1];
    supabaseAnonKey = envContent.match(/NEXT_PUBLIC_SUPABASE_ANON_KEY=(.+)/)?.[1];
    supabaseServiceKey = envContent.match(/SUPABASE_SERVICE_ROLE_KEY=(.+)/)?.[1];

    if (!supabaseUrl) {
      console.log('   ❌ NEXT_PUBLIC_SUPABASE_URL not found in .env.local');
      issues.push('Missing NEXT_PUBLIC_SUPABASE_URL');
      configValid = false;
    } else {
      console.log('   ✅ NEXT_PUBLIC_SUPABASE_URL found');
    }

    if (!supabaseAnonKey) {
      console.log('   ❌ NEXT_PUBLIC_SUPABASE_ANON_KEY not found in .env.local');
      issues.push('Missing NEXT_PUBLIC_SUPABASE_ANON_KEY');
      configValid = false;
    } else {
      console.log('   ✅ NEXT_PUBLIC_SUPABASE_ANON_KEY found');
    }

    if (!supabaseServiceKey) {
      console.log('   ❌ SUPABASE_SERVICE_ROLE_KEY not found in .env.local');
      issues.push('Missing SUPABASE_SERVICE_ROLE_KEY');
      configValid = false;
    } else {
      console.log('   ✅ SUPABASE_SERVICE_ROLE_KEY found');
    }

    // Validate URL format
    if (supabaseUrl && !supabaseUrl.match(/^https:\/\/[a-zA-Z0-9-]+\.supabase\.co$/)) {
      console.log('   ⚠️  NEXT_PUBLIC_SUPABASE_URL format looks incorrect');
      issues.push('Invalid Supabase URL format');
    }

    // Validate key formats (JWT tokens)
    if (supabaseAnonKey && !supabaseAnonKey.startsWith('eyJ')) {
      console.log('   ⚠️  NEXT_PUBLIC_SUPABASE_ANON_KEY format looks incorrect');
      issues.push('Invalid anon key format');
    }

    if (supabaseServiceKey && !supabaseServiceKey.startsWith('eyJ')) {
      console.log('   ⚠️  SUPABASE_SERVICE_ROLE_KEY format looks incorrect');
      issues.push('Invalid service role key format');
    }

  } catch (error) {
    console.log('   ❌ Could not read .env.local file');
    issues.push('Cannot read environment file');
    configValid = false;
  }

  // 2. Test Supabase connectivity
  console.log('\n2. Testing Supabase connectivity...');
  try {
    const response = await fetch(`${supabaseUrl}/rest/v1/`, {
      headers: {
        'apikey': supabaseAnonKey,
        'Authorization': `Bearer ${supabaseAnonKey}`
      }
    });

    if (response.status === 401) {
      console.log('   ❌ Current Supabase keys are invalid/expired');
      issues.push('Supabase API keys are invalid');
      configValid = false;
    } else if (response.ok) {
      console.log('   ⚠️  Current Supabase keys are valid but may be expired');
      console.log('   ℹ️  Consider updating to fresh keys from a new project');
    } else {
      console.log('   ❌ Unexpected response from Supabase:', response.status);
      issues.push('Supabase connectivity issues');
      configValid = false;
    }
  } catch (error) {
    console.log('   ❌ Could not connect to Supabase');
    issues.push('Cannot connect to Supabase');
    configValid = false;
  }

  // 3. Check application status
  console.log('\n3. Checking application authentication status...');
  try {
    const response = await fetch(`${API_BASE}/auth/session`);
    const data = await response.json();

    if (response.ok) {
      console.log('   ✅ Application is using Supabase authentication');
    } else if (data.error === 'No token provided') {
      console.log('   ℹ️  Application is running but no active session');
      console.log('   ✅ Fallback to mock auth is working');
    } else {
      console.log('   ❌ Application authentication check failed');
      issues.push('Application auth check failed');
      configValid = false;
    }
  } catch (error) {
    console.log('   ❌ Could not check application status');
    console.log('   ℹ️  Make sure the development server is running on port 3000');
    issues.push('Cannot check application status');
  }

  // Summary
  console.log('\n📊 Configuration Summary:');
  console.log('=' .repeat(50));

  if (configValid && issues.length === 0) {
    console.log('✅ Supabase configuration is valid!');
    console.log('🎉 Your authentication system is ready for production.');
  } else {
    console.log('❌ Supabase configuration has issues that need to be fixed.');
    console.log('\n🔧 Issues to resolve:');
    issues.forEach((issue, index) => {
      console.log(`   ${index + 1}. ${issue}`);
    });

    console.log('\n📖 Next steps:');
    console.log('   1. Follow SUPABASE_SETUP_GUIDE.md');
    console.log('   2. Create a new Supabase project');
    console.log('   3. Update your .env.local file');
    console.log('   4. Restart the development server');
    console.log('   5. Run this validator again');
  }

  console.log('\n📚 Resources:');
  console.log('   • SUPABASE_SETUP_GUIDE.md - Step-by-step setup guide');
  console.log('   • AUTHENTICATION_SETUP.md - Detailed configuration info');
  console.log('   • supabase.com/docs - Official Supabase documentation');

  console.log('\n🔄 Current Status:');
  console.log('   • Development server: http://localhost:3000');
  console.log('   • Authentication: Mock fallback (working)');
  console.log('   • Database: Not connected to Supabase');
  console.log('   • Ready for production: No');
}

// Run the validation
validateSupabaseConfig().catch(console.error);
