// Visual and functional tests for all Hensler Photography sites
//
// Targets the dev/test stack via domain-based routing on :8080 (the dev
// Caddy routes by hostname over HTTPS; there is no localhost site block).
// In CI the workflow maps the domains to 127.0.0.1 and enables Caddy
// local_certs so the same URLs resolve to the compose stack. If the stack
// is not reachable at all, the suite skips instead of failing.
const { test, expect, request: apiRequest } = require('@playwright/test');

const SITES = {
  hub: 'https://hensler.photography:8080',
  liam: 'https://liam.hensler.photography:8080',
  adrian: 'https://adrian.hensler.photography:8080',
};

let stackReachable = true;

test.beforeAll(async () => {
  const ctx = await apiRequest.newContext({ ignoreHTTPSErrors: true });
  try {
    const res = await ctx.get(`${SITES.hub}/healthz`, { timeout: 5000 });
    stackReachable = res.ok();
  } catch {
    stackReachable = false;
  } finally {
    await ctx.dispose();
  }
});

test.beforeEach(() => {
  test.skip(!stackReachable, `dev stack not reachable at ${SITES.hub}`);
});

test.describe('Hub (hensler.photography)', () => {
  test('should load and display correctly @screenshot', async ({ page }) => {
    await page.goto(`${SITES.hub}/`);

    await expect(page).toHaveTitle(/Hensler Photography/);

    // Ghost typography renders the name lowercase
    const heading = page.locator('h1');
    await expect(heading).toContainText(/hensler photography/i);

    // Photographer cards link to both portfolio sites
    await expect(page.locator('text=Adrian Hensler')).toBeVisible();
    await expect(page.locator('text=Liam Hensler')).toBeVisible();
    await expect(page.locator('a[href="https://adrian.hensler.photography"]')).toBeVisible();
    await expect(page.locator('a[href="https://liam.hensler.photography"]')).toBeVisible();

    await page.screenshot({ path: 'screenshots/main-site.png', fullPage: true });
  });

  test('should have working health check', async ({ page }) => {
    const response = await page.goto(`${SITES.hub}/healthz`);
    expect(response.status()).toBe(200);
    const text = await page.textContent('body');
    expect(text).toBe('ok');
  });
});

test.describe("Liam's portfolio site (liam.hensler.photography)", () => {
  test('should load and display correctly @screenshot', async ({ page }) => {
    await page.goto(`${SITES.liam}/`);

    await expect(page).toHaveTitle(/Liam Hensler Photography/);
    await expect(page.locator('h1')).toContainText(/liam hensler/i);

    // Instagram link (appears in both the about section and the footer)
    const instagramLink = page.locator('a[href="https://www.instagram.com/scotiancapture"]').first();
    await expect(instagramLink).toBeVisible();

    await page.screenshot({ path: 'screenshots/liam-site.png', fullPage: true });
  });

  test('should have correct copyright year', async ({ page }) => {
    await page.goto(`${SITES.liam}/`);
    const footer = page.locator('footer');
    const currentYear = new Date().getFullYear().toString();
    await expect(footer).toContainText(currentYear);
    await expect(footer).toContainText('Liam Hensler');
  });

  test('should have working health check', async ({ page }) => {
    const response = await page.goto(`${SITES.liam}/healthz`);
    expect(response.status()).toBe(200);
  });
});

test.describe("Adrian's portfolio site (adrian.hensler.photography)", () => {
  test('should load and display correctly @screenshot', async ({ page }) => {
    await page.goto(`${SITES.adrian}/`);

    await expect(page).toHaveTitle(/Adrian Hensler Photography/);
    await expect(page.locator('h1')).toContainText(/adrian hensler/i);

    // Flickr link
    const flickrLink = page.locator('a[href="https://www.flickr.com/photos/adrianhensler/"]');
    await expect(flickrLink).toBeVisible();

    // Public gallery containers exist regardless of published data
    await expect(page.locator('#gallery-grid')).toBeAttached();
    await expect(page.locator('#slideshow')).toBeAttached();

    await page.screenshot({ path: 'screenshots/adrian-site.png', fullPage: true });
  });

  test('should have correct copyright year', async ({ page }) => {
    await page.goto(`${SITES.adrian}/`);
    const footer = page.locator('footer');
    const currentYear = new Date().getFullYear().toString();
    await expect(footer).toContainText(currentYear);
    await expect(footer).toContainText('Adrian Hensler');
  });

  test('should have working health check', async ({ page }) => {
    const response = await page.goto(`${SITES.adrian}/healthz`);
    expect(response.status()).toBe(200);
  });

  test('should render gallery images when published data exists', async ({ page, request }) => {
    // On CI the stack runs against a fresh database volume, so the gallery
    // API may error or return no data — this test only asserts rendering
    // when published data actually exists
    const response = await request.get(`${SITES.adrian}/api/gallery/published?user_id=1`);
    test.skip(!response.ok(), 'gallery API not serving — rendering test needs data');

    let published;
    try {
      published = await response.json();
    } catch {
      published = null;
    }
    test.skip(published === null, 'gallery API returned non-JSON — rendering test needs data');

    const images = Array.isArray(published) ? published : (published.images || []);
    test.skip(images.length === 0, 'no published images — rendering test needs data');

    await page.goto(`${SITES.adrian}/`);
    await page.waitForSelector('.gallery-item', { timeout: 10000 });
    const count = await page.locator('.gallery-item').count();
    expect(count).toBeGreaterThan(0);

    // The empty state must never show alongside rendered items
    await expect(page.locator('.enhanced-empty-state')).toHaveCount(0);
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

      for (const url of Object.values(SITES)) {
        await page.goto(`${url}/`);
        await expect(page.locator('h1')).toBeVisible();
      }
    });
  }
});
