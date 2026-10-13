const { test, expect } = require('@playwright/test');
const fs = require('fs');
const path = require('path');
const base = process.env.SHOP_PREVIEW_BASE_URL || 'https://adrian.hensler.photography:8080';
const fixture = (id, width, height) => ({ id, title: `Study ${id}`, alt_text: `Test photograph ${id}`, width, height, aspect_ratio: 1, medium_url: `/assets/gallery/study-${id}.png`, large_url: `/assets/gallery/study-${id}.png` });
const collections = {1: [fixture(52, 6146, 2633), fixture(45, 3323, 4985), fixture(47, 3579, 3579), fixture(54, 10000, 1000)], 2: [fixture(55, 5219, 3150), fixture(53, 3843, 5426), fixture(51, 5900, 3533)]};

test.beforeEach(async ({ page }) => {
  await page.route('**/api/gallery/published?*', route => {
    const seller = new URL(route.request().url()).searchParams.get('user_id');
    return route.fulfill({ json: { images: collections[seller] || [] } });
  });
  await page.route('**/assets/gallery/*', route => {
    const id = Number(route.request().url().match(/study-(\d+)/)?.[1]);
    const photo = Object.values(collections).flat().find(p => p.id === id);
    return route.fulfill({ contentType: 'image/svg+xml', body: `<svg xmlns="http://www.w3.org/2000/svg" width="${photo.width}" height="${photo.height}" viewBox="0 0 ${photo.width} ${photo.height}"><rect width="100%" height="100%" fill="#65736b"/></svg>` });
  });
});

test('geometry preserves exact pixel ratios for unusual sizes and all presentations', async () => {
  const source = fs.readFileSync(path.join(__dirname, '../sites/adrian/shop-preview/geometry.js'), 'utf8');
  const { printGeometry } = await import(`data:text/javascript;base64,${Buffer.from(source).toString('base64')}`);
  for (const [width, height] of [[6146,2633],[3323,4985],[3579,3579],[10000,1000],[1000,10000],[3666,4583]]) {
    for (const edge of [20,30,40]) for (const finish of ['paper','mat','frame']) {
      const g = printGeometry(width,height,edge,finish);
      expect(g.image.width/g.image.height).toBeCloseTo(width/height, 12);
      expect(Math.max(g.image.width,g.image.height)).toBeCloseTo(edge,12);
      expect(g.paper.width-g.image.width).toBeCloseTo(4,12);
      expect(g.mat.width-g.paper.width).toBeCloseTo(finish === 'paper' ? 0 : 10,12);
      expect(g.frame.width-g.mat.width).toBeCloseTo(finish === 'frame' ? 4 : 0,12);
    }
  }
  expect(() => printGeometry(0,100,30,'frame')).toThrow();
});

test('responsive display, selection, keyboard and ratios', async ({ page }) => {
  for (const width of [1440,768,390,320]) {
    await page.setViewportSize({ width, height: 900 });
    await page.goto(`${base}/shop-preview/`);
    await expect(page.locator('.photo-choice')).toHaveCount(4);
    for (const id of [52,45,47,54]) {
      const photo = collections[1].find(p => p.id === id);
      const sourceRatio = photo.width / photo.height;
      const choice = page.locator(`[data-photo-id="${id}"]`);
      await choice.focus();
      await page.keyboard.press('Enter');
      await expect(choice).toHaveAttribute('aria-pressed','true');
      await expect(page.locator('#photo-title')).toBeFocused();
      for (const finish of ['paper','mat','frame']) {
        await page.locator('#finish').selectOption(finish);
        await page.locator('#size').selectOption('40');
        await page.locator('#selected-photo').evaluate(img => img.decode());
        const ratio = await page.locator('#selected-photo').evaluate(img => {
          const r = img.getBoundingClientRect();
          return { rendered: r.width/r.height, intrinsic: img.naturalWidth/img.naturalHeight, loaded: img.complete };
        });
        expect(ratio.loaded).toBeTruthy();
        // WebKit reports integer raster-cache sizes for large SVGs through
        // naturalWidth/naturalHeight. Their declared viewport is the source
        // ratio; compare to it rather than that browser-specific bookkeeping.
        expect(Math.abs(ratio.rendered / sourceRatio - 1),JSON.stringify({width,id,finish,ratio,sourceRatio})).toBeLessThan(.001);
        const framed = await page.locator('#print-photo').evaluate(img => {
          const r = img.getBoundingClientRect();
          return { width:r.width, height:r.height, fit:getComputedStyle(img).objectFit };
        });
        // Browser boxes are quantized to subpixels; contain preserves the actual
        // pixels even when the source WebP rounds its resized dimensions.
        expect(Math.abs(framed.width - framed.height * sourceRatio)).toBeLessThan(.5);
        expect(framed.fit).toBe('contain');
      }
    }
    const overflow = await page.evaluate(() => ({ width:innerWidth, scroll:document.documentElement.scrollWidth, elements:Array.from(document.querySelectorAll('*')).filter(e=>e.getBoundingClientRect().right>innerWidth+1).map(e=>e.id||e.className||e.tagName) }));
    expect(overflow.scroll,JSON.stringify(overflow)).toBeLessThanOrEqual(width);
  }
});

test('seller isolation and mock actions accept no customer data or network writes', async ({ page }) => {
  const writes = [];
  page.on('request', request => { if (request.method() !== 'GET') writes.push(request.url()); });
  await page.goto(`${base}/shop-preview/`);
  await expect(page.locator('#study')).toBeVisible();
  await expect(page.locator('meta[name="robots"]')).toHaveAttribute('content','noindex, nofollow, noarchive');
  await page.locator('#seller').selectOption('liam');
  await expect(page.locator('.photo-choice')).toHaveCount(3);
  await expect(page.locator('#photo-seller')).toHaveText('Photograph by Liam Hensler');
  await expect(page.locator('#gallery-link')).toHaveAttribute('href','https://liam.hensler.photography/');
  await page.locator('#checkout-demo').click();
  await expect(page.locator('#order-status')).toContainText('no checkout');
  await page.locator('#onboarding-demo').click();
  await expect(page.locator('#payment-status')).toContainText('connects no account');
  await expect(page.locator('input, textarea, form, iframe')).toHaveCount(0);
  expect(writes).toEqual([]);
  expect(await page.evaluate(() => Object.keys(localStorage))).toEqual([]);
  await page.locator('#seller').selectOption('adrian');
  await expect(page.locator('.photo-choice')).toHaveCount(4);
  await expect(page.locator('#payment-status')).toBeEmpty();
  await expect(page.locator('#order-status')).toBeEmpty();
});

test('unavailable collection leaves no stale photograph or order controls', async ({ page }) => {
  await page.goto(`${base}/shop-preview/`);
  await expect(page.locator('#study')).toBeVisible();
  await page.route('**/api/gallery/published?user_id=2', route => route.fulfill({status:503,body:'Unavailable'}));
  await page.locator('#seller').selectOption('liam');
  await expect(page.locator('#load-status')).toContainText('could not be loaded');
  await expect(page.locator('#study')).toBeHidden();
  await expect(page.locator('.photo-choice')).toHaveCount(0);
});

test('metadata is treated as text; unsafe asset URLs never render', async ({ page }) => {
  const safe = {...fixture(52, 1000,1000), title:'<img src=x onerror=alert(1)>'};
  await page.route('**/api/gallery/published?user_id=1', route => route.fulfill({json:{images:[safe,{...fixture(45,1000,1000), large_url:'https://example.com/private.png'}]}}));
  await page.goto(`${base}/shop-preview/`);
  await expect(page.locator('.photo-choice')).toHaveCount(1);
  await expect(page.locator('#photo-title')).toHaveText(safe.title);
  await expect(page.locator('#photo-title img')).toHaveCount(0);
});
