/**
 * Quick test to verify URL filter functionality
 */
const { test, expect } = require('@playwright/test');

test.describe('URL Filters', () => {
  test('should update URL when clicking featured toggle', async ({ page }) => {
    await page.goto('https://adrian.hensler.photography/');

    // Wait for gallery to load
    await page.waitForSelector('#gallery-grid');

    // Initial URL should have no query params (featured is default)
    expect(page.url()).toBe('https://adrian.hensler.photography/');

    // Click "all" button
    const allButton = page.locator('button[data-featured="false"]');
    await allButton.click();

    // URL should update to include ?featured=false
    await page.waitForTimeout(500);
    expect(page.url()).toContain('featured=false');

    console.log('✅ Featured toggle updates URL correctly');
  });

  test('should update URL when filtering by category', async ({ page }) => {
    await page.goto('https://adrian.hensler.photography/');
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
    await page.goto('https://adrian.hensler.photography/');
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
    await page.goto('https://adrian.hensler.photography/?featured=false&category=wildlife');
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
