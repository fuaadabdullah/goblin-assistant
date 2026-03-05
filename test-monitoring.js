// Test script to verify monitoring functionality
import https from 'https';

const baseUrl = process.env.BASE_URL || 'http://localhost:4173';

console.log('🧪 Testing Goblin Assistant Monitoring\n');

// Test 1: Basic site accessibility
console.log('1. Testing site accessibility...');
https
  .get(baseUrl, (res) => {
    console.log(`   ✅ Status: ${res.statusCode}`);
    console.log(`   ✅ Headers: ${Object.keys(res.headers).length} headers received`);

    // Test 2: Error testing page accessibility
    console.log('\n2. Testing error-testing page...');
    https
      .get(`${baseUrl}/error-testing`, (res) => {
        console.log(`   ✅ Status: ${res.statusCode}`);

        // Test 3: Check for Datadog RUM script
        console.log('\n3. Checking for monitoring scripts...');
        let data = '';
        res.on('data', (chunk) => (data += chunk));
        res.on('end', () => {
          const hasDatadog = data.includes('datadog') || data.includes('DD_');
          const hasSentry = data.includes('sentry') || data.includes('Sentry');

          console.log(`   ${hasDatadog ? '✅' : '❌'} Datadog RUM detected`);
          console.log(`   ${hasSentry ? '✅' : '❌'} Sentry monitoring detected`);

          // Test 4: Check API endpoint (if configured)
          console.log('\n4. Testing API configuration...');
          const apiUrl = 'https://api.goblin-assistant.com';
          https
            .get(apiUrl, { timeout: 5000 }, (res) => {
              console.log(`   ✅ API Status: ${res.statusCode}`);
              console.log('\n🎉 Monitoring test completed!');
              console.log('\n📋 Next steps:');
              console.log(`   - Visit ${baseUrl}/error-testing`);
              console.log('   - Click error testing buttons to generate test errors');
              console.log('   - Check Datadog dashboard for user sessions and errors');
              console.log('   - Look for "GoblinOS Assistant" service-tagged errors');
            })
            .on('error', () => {
              console.log('   ⚠️  API not accessible (expected in development)');
              console.log('\n🎉 Basic monitoring test completed!');
              console.log('\n�� Next steps:');
              console.log(`   - Visit ${baseUrl}/error-testing`);
              console.log('   - Click error testing buttons to generate test errors');
              console.log('   - Check Datadog dashboard for user sessions and errors');
              console.log('   - Look for "GoblinOS Assistant" service-tagged errors');
            });
        });
      })
      .on('error', (err) => {
        console.log(`   ❌ Error testing page failed: ${err.message}`);
      });
  })
  .on('error', (err) => {
    console.log(`   ❌ Site accessibility failed: ${err.message}`);
  });
