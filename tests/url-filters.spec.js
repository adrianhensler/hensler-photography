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
 * The only public filter control is the #category-nav row of
 * .category-link buttons (one per category with >= 3 published images,
 * plus "all"). The nav is hidden when fewer than 2 categories qualify,
 * so category-specific tests skip themselves when the dev DB doesn't
 * have enough data to show it.
 */
const { test, expect, request: apiRequest } = require('@playwright/test');

const BASE_URL = 'https://adrian.hensler.photography:8080';

let devStackReachable = true;
let hasPublishedImages = true;

/**
 * Fetch published images and compute category -> count for categories
 * with >= 3 published images (the same threshold gallery.js uses to
 * decide whether a category qualifies for the nav).
 */
async function getQualifyingCategories(request) {
  const response = await request.get(`${BASE_URL}/api/gallery/published?user_id=1`);
  const published = await response.json();
  const images = Array.isArray(published) ? published : (published.images || []);

  const counts = {};
  for (const img of images) {
    if (!img.category) continue;
    counts[img.category] = (counts[img.category] || 0) + 1;
  }

  const qualifying = Object.entries(counts)
    .filter(([, count]) => count >= 3)
    .sort((a, b) => b[1] - a[1]);

  return { images, qualifying };
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
  test('should load gallery with no filter params by default', async ({ page }) => {
    await page.goto(`${BASE_URL}/`);
    await page.waitForSelector('#gallery-grid');
    await page.waitForSelector('.gallery-item');

    expect(page.url()).toBe(`${BASE_URL}/`);

    const itemCount = await page.locator('.gallery-item').count();
    expect(itemCount).toBeGreaterThan(0);

    console.log('✅ Gallery loads with no filter params by default');
  });

  test('should update URL when clicking a category', async ({ page, request }) => {
    const { qualifying } = await getQualifyingCategories(request);
    test.skip(qualifying.length < 2, 'fewer than 2 qualifying categories — category nav is hidden');

    await page.goto(`${BASE_URL}/`);
    await page.waitForSelector('#gallery-grid');

    // First .category-link is "all"; click the first real category button
    const categoryButton = page.locator('#category-nav .category-link').nth(1);
    await categoryButton.click();

    await page.waitForTimeout(500);
    expect(page.url()).toContain('category=');

    console.log('✅ Category filter updates URL correctly');
  });

  test('should restore category filter from URL on direct visit', async ({ page, request }) => {
    const { qualifying } = await getQualifyingCategories(request);
    test.skip(qualifying.length === 0, 'no qualifying categories to restore from URL');

    const [category, count] = qualifying[0];

    await page.goto(`${BASE_URL}/?category=${category}`);
    await page.waitForSelector('.gallery-item');

    const itemCount = await page.locator('.gallery-item').count();
    expect(itemCount).toBe(count);

    console.log('✅ URL category filter restores correctly on direct visit');
  });

  test('should ignore an invalid category from URL', async ({ page, request }) => {
    const response = await request.get(`${BASE_URL}/api/gallery/published?user_id=1`);
    const published = await response.json();
    const images = Array.isArray(published) ? published : (published.images || []);

    await page.goto(`${BASE_URL}/?category=not-a-real-category-xyz`);
    await page.waitForSelector('.gallery-item');

    const itemCount = await page.locator('.gallery-item').count();
    expect(itemCount).toBe(images.length);

    console.log('✅ Invalid category from URL is ignored');
  });
});
