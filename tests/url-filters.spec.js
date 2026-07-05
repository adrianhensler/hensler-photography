/**
 * Quick test to verify URL filter functionality
 *
 * Uses the real adrian.hensler.photography hostname on the dev port
 * (:8080) rather than playwright.config.js's shared localhost baseURL:
 * the dev Caddy stack (Caddyfile.local) routes by domain name and
 * requires HTTPS, so localhost:8080 doesn't resolve to any site block
 * at all. This intentionally targets the dev/test stack, not
 * production (production has no :8080 listener).
 *
 * On hosts without the dev stack (e.g. CI runners, where the hostname
 * resolves to production and :8080 is closed) the suite skips instead
 * of failing.
 *
 * The scope/category/tag pills live inside the "Refine results"
 * disclosure, which is hidden in the default "browse" discovery mode —
 * tests must enter refine mode before interacting with them.
 */
const { test, expect, request: apiRequest } = require('@playwright/test');

const BASE_URL = 'https://adrian.hensler.photography:8080';

let devStackReachable = true;
let hasPublishedImages = true;

async function openRefinePanel(page) {
  await page.locator('button[data-mode="refine"]').click();
  const details = page.locator('#refine-results');
  if (!(await details.evaluate((el) => el.open))) {
    // "> summary" avoids matching the nested "Advanced filters" disclosure
    await details.locator('> summary').click();
  }
}

test.beforeAll(async () => {
  const ctx = await apiRequest.newContext();
  try {
    const res = await ctx.get(`${BASE_URL}/healthz`, { timeout: 5000 });
    devStackReachable = res.ok();

    // Filtering never initializes on a gallery with no published images
    // (e.g. a fresh CI database), so these tests need data to be meaningful
    if (devStackReachable) {
      const gallery = await ctx.get(`${BASE_URL}/api/gallery/published?user_id=1`, { timeout: 5000 });
      const published = await gallery.json();
      const images = Array.isArray(published) ? published : (published.images || []);
      hasPublishedImages = images.length > 0;
    }
  } catch {
    devStackReachable = false;
  } finally {
    await ctx.dispose();
  }
});

test.beforeEach(() => {
  test.skip(!devStackReachable, `dev stack not reachable at ${BASE_URL}`);
  test.skip(!hasPublishedImages, 'no published images in gallery — filter tests need data');
});

test.describe('URL Filters', () => {
  test('should update URL when clicking featured toggle', async ({ page, request }) => {
    // The default scope is data-driven: featured-only when featured images
    // exist, otherwise all images. Toggling away from the default must be
    // reflected in the URL; the default itself adds no query param.
    const response = await request.get(`${BASE_URL}/api/gallery/published?user_id=1`);
    const published = await response.json();
    const images = Array.isArray(published) ? published : (published.images || []);
    const hasFeatured = images.some((img) => img.featured);

    await page.goto(`${BASE_URL}/`);

    // Wait for gallery to load
    await page.waitForSelector('#gallery-grid');

    // Initial URL should have no query params (default scope is implicit)
    expect(page.url()).toBe(`${BASE_URL}/`);

    // Scope pills are inside the refine panel
    await openRefinePanel(page);

    // Click the pill for the non-default scope
    const nonDefault = hasFeatured ? 'false' : 'true';
    const toggleButton = page.locator(`button[data-featured="${nonDefault}"]`);
    await toggleButton.click();

    // URL should update to include the non-default scope
    await page.waitForTimeout(500);
    expect(page.url()).toContain(`featured=${nonDefault}`);

    console.log('✅ Featured toggle updates URL correctly');
  });

  test('should update URL when filtering by category', async ({ page }) => {
    await page.goto(`${BASE_URL}/`);
    await page.waitForSelector('#gallery-grid');

    await openRefinePanel(page);

    // Click first category pill
    const categoryPill = page.locator('#category-pills .pill').first();
    await categoryPill.click();

    // URL should include category parameter
    await page.waitForTimeout(500);
    expect(page.url()).toContain('category=');

    console.log('✅ Category filter updates URL correctly');
  });

  test('should show copy link button when filters are active', async ({ page }) => {
    await page.goto(`${BASE_URL}/`);
    await page.waitForSelector('#gallery-grid');

    await openRefinePanel(page);

    // Click a category
    await page.locator('#category-pills .pill').first().click();
    await page.waitForTimeout(500);

    // Copy link button should appear
    const copyButton = page.locator('.copy-filter-link');
    await expect(copyButton).toBeVisible();

    console.log('✅ Copy link button appears correctly');
  });

  test('should restore state from URL on direct visit', async ({ page }) => {
    // mode=refine so the scope pills and active-filter chips are visible
    await page.goto(`${BASE_URL}/?featured=false&category=wildlife&mode=refine`);
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
