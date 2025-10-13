# Visual Testing with Playwright

This project includes Playwright tests for automated visual and functional testing of all three sites.

## Prerequisites

- Node.js (v18 or later)
- Docker (for running the local development server)

## Setup

1. **Install dependencies:**
```bash
npm install
npx playwright install --with-deps
```

2. **Start local development server:**
```bash
# In one terminal
docker compose -f docker-compose.local.yml up
```

## Running Tests

### Run all tests
```bash
npm test
```

### Run tests with UI mode (interactive)
```bash
npm run test:ui
```

### Run tests in headed mode (see browser)
```bash
npm run test:headed
```

### Take screenshots only
```bash
npm run screenshot
```

Screenshots will be saved to the `screenshots/` directory:
- `screenshots/main-site.png`
- `screenshots/liam-site.png`
- `screenshots/adrian-site.png`

## Test Coverage

The test suite verifies:

### Functional Tests
- ✅ All pages load successfully
- ✅ Correct page titles
- ✅ Headings display properly
- ✅ External links (Instagram, Flickr) have correct URLs
- ✅ Health check endpoints work
- ✅ Copyright year updates automatically

### Visual Tests
- ✅ Hero images display
- ✅ Layout is correct
- ✅ Responsive design on mobile, tablet, desktop
- ✅ Buttons and links are visible

### Browsers Tested
- Chromium (Chrome/Edge)
- Firefox
- WebKit (Safari)

## Test Results

After running tests:
- **HTML Report**: Opens automatically (or run `npx playwright show-report`)
- **Screenshots**: Saved to `screenshots/` directory
- **Videos**: Saved on test failures in `test-results/`

## CI/CD Integration

These tests can be integrated into CI/CD pipelines:

```yaml
# Example GitHub Actions
- name: Install dependencies
  run: npm ci
- name: Install Playwright
  run: npx playwright install --with-deps
- name: Start local server
  run: docker compose -f docker-compose.local.yml up -d
- name: Run tests
  run: npm test
```

## Debugging

### Debug a specific test
```bash
npx playwright test --debug tests/sites.spec.js
```

### Show test report
```bash
npx playwright show-report
```

## Tips

1. **Keep tests updated** when making design changes
2. **Review screenshots** after visual changes
3. **Check responsive tests** when modifying CSS
4. **Update test selectors** if HTML structure changes

## Troubleshooting

### Test fails with "Navigation timeout"
- Ensure local server is running: `docker compose -f docker-compose.local.yml up`
- Check server is accessible: `curl http://localhost:8080/healthz`

### Screenshots look wrong
- Check viewport size in `playwright.config.js`
- Verify CSS loads correctly in the browser
- Clear browser cache: `npx playwright cache clear`

### Tests pass locally but fail in CI
- Ensure CI has enough resources (memory, CPU)
- Check CI has proper browser dependencies installed
- Verify network access to localhost
