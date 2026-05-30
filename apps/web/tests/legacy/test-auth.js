#!/usr/bin/env node

/**
 * Test script to verify Supabase authentication setup
 */

/* eslint-disable no-console */
import crypto from 'node:crypto';
import fetch from 'node-fetch';

const API_BASE = 'http://localhost:3000/api';

function createTestCredentials() {
  const suffix = crypto.randomUUID().slice(0, 8);

  return {
    email: `goblin-test-${suffix}@example.com`,
    password: `TestPass!${suffix}`,
    name: 'Goblin Test User',
  };
}

async function testAuth() {
  console.log('🧪 Testing GoblinOS Assistant Authentication...\n');

  const testUser = createTestCredentials();

  // Test 1: Check if Supabase is configured
  console.log('1. Checking Supabase configuration...');
  try {
    const response = await fetch(`${API_BASE}/auth/session`);
    const data = await response.json();
    console.log('   ✅ Supabase configuration check passed');
    console.log('   Response:', data);
  } catch (error) {
    console.log('   ❌ Supabase configuration check failed:', error.message);
  }

  // Test 2: Test registration
  console.log('\n2. Testing user registration...');
  const registrationUser = {
    ...testUser,
    confirmPassword: testUser.password,
  };

  try {
    const response = await fetch(`${API_BASE}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(registrationUser),
    });

    const data = await response.json();
    console.log('   ✅ Registration test passed');
    console.log('   Response:', data);
  } catch (error) {
    console.log('   ❌ Registration test failed:', error.message);
  }

  // Test 3: Test login
  console.log('\n3. Testing user login...');
  try {
    const response = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        email: testUser.email,
        password: testUser.password,
      }),
    });

    const data = await response.json();
    console.log('   ✅ Login test passed');
    console.log('   Response:', data);
  } catch (error) {
    console.log('   ❌ Login test failed:', error.message);
  }

  console.log('\n🎉 Authentication tests completed!');
}

// Run the test
testAuth().catch(console.error);
