/**
 * Share links: the photo open in the lightbox is mirrored to ?photo=<id>,
 * a shared link opens straight to that photo, and the lightbox's Share
 * button copies the link (desktop) or opens the share sheet (phones).
 *
 * Targets the dev stack on :8080 like url-filters.spec.js, and skips on
 * hosts without it or without published images.
 */
const { test, expect, request: apiRequest } = require('@playwright/test');

const BASE_URL = 'https://adrian.hensler.photography:8080';

let devStackReachable = true;
let images = [];

test.beforeAll(async () => {
  const ctx = await apiRequest.newContext({ ignoreHTTPSErrors: true });
  try {
    const res = await ctx.get(`${BASE_URL}/healthz`, { timeout: 5000 });
    devStackReachable = res.ok();
    if (devStackReachable) {
      const gallery = await ctx.get(`${BASE_URL}/api/gallery/published?user_id=1`, { timeout: 5000 });
      const published = await gallery.json();
      images = Array.isArray(published) ? published : (published.images || []);
    }
  } catch {
    devStackReachable = false;
  } finally {
    await ctx.dispose();
  }
});

test.beforeEach(() => {
  test.skip(!devStackReachable, `dev stack not reachable at ${BASE_URL}`);
  test.skip(images.length === 0, 'no published images in gallery');
});

test.describe('Share links', () => {
  test('opening a photo puts its link in the address bar; closing removes it', async ({ page }) => {
    await page.goto(`${BASE_URL}/`);
    await page.locator('.gallery-item').first().click();
    await page.waitForSelector('.glightbox-container .gshare');

    await expect(page).toHaveURL(new RegExp(`\\?photo=${images[0].id}$`));

    await page.keyboard.press('Escape');
    await expect(page).toHaveURL(`${BASE_URL}/`);
  });

  test('a shared link opens straight to its photo', async ({ page }) => {
    const target = images[images.length - 1];
    await page.goto(`${BASE_URL}/?photo=${target.id}`);
    await page.waitForSelector('.glightbox-container .gslide.current');

    const src = await page.locator('.gslide.current .gslide-image img').getAttribute('src');
    expect(new URL(src, BASE_URL).pathname).toBe(target.large_url);
    await expect(page).toHaveURL(`${BASE_URL}/?photo=${target.id}`);
  });

  test('Back and Forward reopen and close the photo', async ({ page }) => {
    const target = images[0];
    await page.goto(`${BASE_URL}/`);
    await page.waitForSelector('.gallery-item');
    await page.evaluate((id) => {
      history.pushState({}, '', `?photo=${id}`);
      history.pushState({}, '', '/');
    }, target.id);

    await page.goBack();
    await page.waitForSelector('.glightbox-container .gslide.current');
    await expect(page).toHaveURL(`${BASE_URL}/?photo=${target.id}`);

    await page.goForward();
    await expect(page.locator('.glightbox-container')).toHaveCount(0);
    await expect(page).toHaveURL(`${BASE_URL}/`);
  });

    test('an unknown photo id falls back to the gallery', async ({ page }) => {
    await page.goto(`${BASE_URL}/?photo=999999`);
    await page.waitForSelector('.gallery-item');

    await expect(page).toHaveURL(`${BASE_URL}/`);
    expect(await page.locator('.glightbox-container').count()).toBe(0);
  });

  test('Share copies the photo link on desktop', async ({ page, context, browserName }) => {
    // Only Chromium lets a test grant clipboard permissions
    test.skip(browserName !== 'chromium', 'clipboard permissions are Chromium-only in Playwright');
    await context.grantPermissions(['clipboard-read', 'clipboard-write']);
    await page.goto(`${BASE_URL}/?photo=${images[0].id}`);
    const share = page.locator('.glightbox-container .gshare');
    await share.click();

    await expect(share).toContainText('Link copied');
    const copied = await page.evaluate(() => navigator.clipboard.readText());
    expect(copied).toBe(`${BASE_URL}${images[0].page_path}`);
  });
});

test.describe('Share fallback', () => {
  test('shows the photo page link when copying is refused', async ({ page }) => {
    await page.addInitScript(() => {
      Object.defineProperty(navigator, 'clipboard', {
        value: { writeText: () => Promise.reject(new Error('denied')) },
      });
    });
    await page.goto(`${BASE_URL}/?photo=${images[0].id}`);
    await page.locator('.glightbox-container .gshare').click();

    const field = page.locator('.glightbox-container .gshare-link');
    await expect(field).toBeVisible();
    await expect(field).toHaveValue(`${BASE_URL}${images[0].page_path}`);
  });
});

test.describe('Photo pages', () => {
  test('serve the photo with link-preview tags', async ({ page }) => {
    const target = images[0];
    // An id link lands on the approved address when there is one
    const response = await page.goto(`${BASE_URL}/photo/${target.id}`);
    expect(response.status()).toBe(200);
    await expect(page).toHaveURL(`${BASE_URL}${target.page_path}`);

    await expect(page.locator('h1')).toHaveText(target.title);
    const ogImage = await page.locator('meta[property="og:image"]').getAttribute('content');
    expect(ogImage).toMatch(new RegExp(`^${BASE_URL}/assets/gallery/.+\\.webp$`));
    const canonical = await page.locator('link[rel="canonical"]').getAttribute('href');
    expect(canonical).toBe(`${BASE_URL}${target.page_path}`);
    await expect(page.locator('a.to-gallery')).toHaveAttribute('href', `/?photo=${target.id}`);
  });

  test('return 404 for unknown or non-numeric ids', async ({ page }) => {
    for (const key of ['999999', 'not-a-photo']) {
      const response = await page.goto(`${BASE_URL}/photo/${key}`);
      expect(response.status()).toBe(404);
      await expect(page.locator('.not-found')).toBeVisible();
    }
  });

  test('Share copies the page link', async ({ page, context, browserName }) => {
    test.skip(browserName !== 'chromium', 'clipboard permissions are Chromium-only in Playwright');
    await context.grantPermissions(['clipboard-read', 'clipboard-write']);
    await page.goto(`${BASE_URL}${images[0].page_path}`);
    await page.locator('#share').click();

    await expect(page.locator('#share')).toContainText('Link copied');
    const copied = await page.evaluate(() => navigator.clipboard.readText());
    expect(copied).toBe(`${BASE_URL}${images[0].page_path}`);
  });
});
