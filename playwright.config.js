// Playwright configuration for visual testing
const { defineConfig } = require('@playwright/test');

module.exports = defineConfig({
  testDir: './tests',

  // Test timeout
  timeout: 30000,

  // Retry failed tests
  retries: 1,

  // Run tests in parallel
  workers: 3,

  // Reporter
  reporter: [['html', { open: 'never' }]],

  use: {
    // Base URL for local testing
    baseURL: 'http://localhost:8080',

    // Screenshot on failure
    screenshot: 'only-on-failure',

    // Video on failure
    video: 'retain-on-failure',

    // Viewport
    viewport: { width: 1280, height: 720 },
  },

  // Configure projects for different browsers
  projects: [
    {
      name: 'chromium',
      use: { browserName: 'chromium' },
    },
    {
      name: 'firefox',
      use: { browserName: 'firefox' },
    },
    {
      name: 'webkit',
      use: { browserName: 'webkit' },
    },
  ],
});
