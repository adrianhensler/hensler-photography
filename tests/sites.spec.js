// Visual and functional tests for all Hensler Photography sites
const { test, expect } = require('@playwright/test');

test.describe('Main Site (hensler.photography)', () => {
  test('should load and display correctly @screenshot', async ({ page }) => {
    await page.goto('/');

    // Check title
    await expect(page).toHaveTitle(/Hensler Photography/);

    // Check heading
    const heading = page.locator('h1');
    await expect(heading).toContainText('Hensler Photography');

    // Check links to individual sites
    const liamLink = page.locator('a:has-text("Liam Hensler")');
    const adrianLink = page.locator('a:has-text("Adrian Hensler")');
    await expect(liamLink).toBeVisible();
    await expect(adrianLink).toBeVisible();

    // Take screenshot
    await page.screenshot({ path: 'screenshots/main-site.png', fullPage: true });
  });

  test('should have working health check', async ({ page }) => {
    const response = await page.goto('/healthz');
    expect(response.status()).toBe(200);
    const text = await page.textContent('body');
    expect(text).toBe('ok');
  });
});

test.describe("Liam's Site (liam.hensler.photography)", () => {
  test('should load and display correctly @screenshot', async ({ page }) => {
    await page.goto('/liam');

    // Check title
    await expect(page).toHaveTitle(/Liam Hensler Photography/);

    // Check heading
    const heading = page.locator('h1');
    await expect(heading).toContainText('Liam Hensler Photography');

    // Check Instagram link
    const instagramLink = page.locator('a:has-text("Follow on Instagram")');
    await expect(instagramLink).toBeVisible();
    await expect(instagramLink).toHaveAttribute('href', 'https://www.instagram.com/scotiancapture');

    // Check hero image exists
    const heroImage = page.locator('img[alt*="Liam"]');
    await expect(heroImage).toBeVisible();

    // Take screenshot
    await page.screenshot({ path: 'screenshots/liam-site.png', fullPage: true });
  });

  test('should have correct copyright year', async ({ page }) => {
    await page.goto('/liam');
    const footer = page.locator('footer');
    const currentYear = new Date().getFullYear().toString();
    await expect(footer).toContainText(currentYear);
    await expect(footer).toContainText('Liam Hensler');
  });
});

test.describe("Adrian's Site (adrian.hensler.photography)", () => {
  test('should load and display correctly @screenshot', async ({ page }) => {
    await page.goto('/adrian');

    // Check title
    await expect(page).toHaveTitle(/Adrian Hensler Photography/);

    // Check heading
    const heading = page.locator('h1');
    await expect(heading).toContainText('Adrian Hensler Photography');

    // Check Flickr link
    const flickrLink = page.locator('a:has-text("View on Flickr")');
    await expect(flickrLink).toBeVisible();
    await expect(flickrLink).toHaveAttribute('href', 'https://www.flickr.com/photos/adrianhensler/');

    // Check hero image exists
    const heroImage = page.locator('img[alt*="Adrian"]');
    await expect(heroImage).toBeVisible();

    // Take screenshot
    await page.screenshot({ path: 'screenshots/adrian-site.png', fullPage: true });
  });

  test('should have correct copyright year', async ({ page }) => {
    await page.goto('/adrian');
    const footer = page.locator('footer');
    const currentYear = new Date().getFullYear().toString();
    await expect(footer).toContainText(currentYear);
    await expect(footer).toContainText('Adrian Hensler');
  });
});

test.describe('Responsive Design', () => {
  const viewports = [
    { name: 'mobile', width: 375, height: 667 },
    { name: 'tablet', width: 768, height: 1024 },
    { name: 'desktop', width: 1920, height: 1080 },
  ];

  for (const viewport of viewports) {
    test(`should display correctly on ${viewport.name}`, async ({ page }) => {
      await page.setViewportSize({ width: viewport.width, height: viewport.height });

      // Test each site
      await page.goto('/');
      await expect(page.locator('h1')).toBeVisible();

      await page.goto('/liam');
      await expect(page.locator('h1')).toBeVisible();

      await page.goto('/adrian');
      await expect(page.locator('h1')).toBeVisible();
    });
  }
});
