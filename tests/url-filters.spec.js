/**
 * Quick test to verify URL filter functionality
 *
 * Uses the real adrian.hensler.photography hostname on the dev port
 * (:8080) rather than playwright.config.js's shared localhost baseURL:
 * the dev Caddy stack (Caddyfile.local) routes by domain name and
 * requires HTTPS, so localhost:8080 doesn't resolve to any site block
 * at all. This intentionally targets the dev/test stack, not
 * production (production has no :8080 listener).
 */
const { test, expect } = require('@playwright/test');

const BASE_URL = 'https://adrian.hensler.photography:8080';

test.describe('URL Filters', () => {
  test('should update URL when clicking featured toggle', async ({ page }) => {
    await page.goto(`${BASE_URL}/`);

    // Wait for gallery to load
    await page.waitForSelector('#gallery-grid');

    // Initial URL should have no query params (featured is default)
    expect(page.url()).toBe(`${BASE_URL}/`);

    // Click "all" button
    const allButton = page.locator('button[data-featured="false"]');
    await allButton.click();

    // URL should update to include ?featured=false
    await page.waitForTimeout(500);
    expect(page.url()).toContain('featured=false');

    console.log('✅ Featured toggle updates URL correctly');
  });

  test('should update URL when filtering by category', async ({ page }) => {
    await page.goto(`${BASE_URL}/`);
    await page.waitForSelector('#gallery-grid');

    // Click first category pill
    const categoryPill = page.locator('#category-pills .pill').first();
    const categoryText = await categoryPill.textContent();
    await categoryPill.click();

    // URL should include category parameter
    await page.waitForTimeout(500);
    expect(page.url()).toContain('category=');

    console.log('✅ Category filter updates URL correctly');
  });

  test('should show copy link button when filters are active', async ({ page }) => {
    await page.goto(`${BASE_URL}/`);
    await page.waitForSelector('#gallery-grid');

    // Click a category
    await page.locator('#category-pills .pill').first().click();
    await page.waitForTimeout(500);

    // Copy link button should appear
    const copyButton = page.locator('.copy-filter-link');
    await expect(copyButton).toBeVisible();

    console.log('✅ Copy link button appears correctly');
  });

  test('should restore state from URL on direct visit', async ({ page }) => {
    await page.goto(`${BASE_URL}/?featured=false&category=wildlife`);
    await page.waitForSelector('#gallery-grid');

    // Check that "all" button is active
    const allButton = page.locator('button[data-featured="false"]');
    await expect(allButton).toHaveClass(/active/);

    // Check that active filter text is shown
    const activeFilters = page.locator('#active-filter-text');
    const filterText = await activeFilters.textContent();
    expect(filterText).toContain('wildlife');

    console.log('✅ URL state restores correctly on direct visit');
  });
});
