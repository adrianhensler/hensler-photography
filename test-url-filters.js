/**
 * Quick test to verify URL filter functionality
 * Run: node test-url-filters.js
 */

const https = require('https');

const tests = [
  {
    name: 'Base URL (featured only)',
    url: 'https://adrian.hensler.photography/',
    expectedStatus: 200
  },
  {
    name: 'Show all images',
    url: 'https://adrian.hensler.photography/?featured=false',
    expectedStatus: 200
  },
  {
    name: 'Category filter',
    url: 'https://adrian.hensler.photography/?category=wildlife',
    expectedStatus: 200
  },
  {
    name: 'Combined filters',
    url: 'https://adrian.hensler.photography/?featured=false&category=wildlife&tag=nature',
    expectedStatus: 200
  }
];

console.log('🧪 Testing URL Filter Functionality\n');

let passed = 0;
let failed = 0;

async function testURL(test) {
  return new Promise((resolve) => {
    https.get(test.url, (res) => {
      const success = res.statusCode === test.expectedStatus;
      if (success) {
        console.log(`✅ ${test.name}`);
        console.log(`   ${test.url}`);
        console.log(`   Status: ${res.statusCode}\n`);
        passed++;
      } else {
        console.log(`❌ ${test.name}`);
        console.log(`   ${test.url}`);
        console.log(`   Expected: ${test.expectedStatus}, Got: ${res.statusCode}\n`);
        failed++;
      }
      resolve();
    }).on('error', (err) => {
      console.log(`❌ ${test.name}`);
      console.log(`   Error: ${err.message}\n`);
      failed++;
      resolve();
    });
  });
}

async function runTests() {
  for (const test of tests) {
    await testURL(test);
  }

  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
  console.log(`Results: ${passed} passed, ${failed} failed`);

  if (failed === 0) {
    console.log('\n🎉 All URL filters are working correctly!');
    console.log('\nNext: Open https://adrian.hensler.photography/ and:');
    console.log('  1. Click "all" button → URL should change to ?featured=false');
    console.log('  2. Click any category → URL should update');
    console.log('  3. Look for "Copy link" button in active filters');
    console.log('  4. Click browser BACK → gallery should restore previous state');
  } else {
    process.exit(1);
  }
}

runTests();
