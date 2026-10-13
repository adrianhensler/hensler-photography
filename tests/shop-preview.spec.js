const { test, expect } = require('@playwright/test');
const fs = require('fs');
const path = require('path');
const base = process.env.SHOP_PREVIEW_BASE_URL || 'https://adrian.hensler.photography:8080';
const fixture = (id,width,height) => ({id,title:`Study ${id}`,alt_text:`Test photograph ${id}`,width,height,aspect_ratio:1,medium_url:`/assets/gallery/study-${id}.png`,large_url:`/assets/gallery/study-${id}.png`});
const photos=[fixture(52,6146,2633),fixture(45,3323,4985),fixture(47,3579,3579),fixture(54,10000,1000)];
const options=(extra={})=>({sheet:'13x19',edge:'auto',pattern:'plain',package:'print',printer:'unsettled',...extra});
async function geometryModule(){const source=fs.readFileSync(path.join(__dirname,'../sites/adrian/shop-preview/geometry.js'),'utf8');return import(`data:text/javascript;base64,${Buffer.from(source).toString('base64')}`);}
test.beforeEach(async({page})=>{
 await page.route('**/api/gallery/published?*',route=>route.fulfill({json:{images:photos}}));
 await page.route('**/assets/gallery/*',route=>{const id=Number(route.request().url().match(/study-(\d+)/)?.[1]),photo=photos.find(p=>p.id===id);return route.fulfill({contentType:'image/svg+xml',body:`<svg xmlns="http://www.w3.org/2000/svg" width="${photo.width}" height="${photo.height}" viewBox="0 0 ${photo.width} ${photo.height}"><rect width="100%" height="100%" fill="#65736b"/></svg>`});});
});

test('stock fit geometry preserves source ratios and all four surrounds',async()=>{
 const {layoutVariant,sheets}=await geometryModule();
 for(const [width,height] of [[6146,2633],[3323,4985],[3579,3579],[10000,1000],[1000,10000],[3666,4583]]){
  for(const sheet of sheets)for(const pack of ['print','mat','frame']){
   const g=layoutVariant(width,height,options({sheet:sheet.id,package:pack}));
   expect(g.image.width/g.image.height).toBeCloseTo(width/height,12);
   expect(g.surround.left+g.image.width+g.surround.right).toBeCloseTo(g.paper.width,12);
   expect(g.surround.top+g.image.height+g.surround.bottom).toBeCloseTo(g.paper.height,12);
   expect(g.surround.left).toBeGreaterThanOrEqual(12.7-1e-8);
   expect(g.frameFit).toEqual(g.paper);expect(g.frameExternal).toBeNull();
   if(g.matWindow){expect(g.matWindow.width-g.image.width).toBeCloseTo(12.7,12);expect(g.matOuter).toEqual(g.paper);expect(g.matSurround.left).toBeGreaterThanOrEqual(25.4-1e-8);}
  }
 }
 const nominal=layoutVariant(2100,900,options()),a3=layoutVariant(2100,900,options({sheet:'a3plus'}));
 expect(nominal.paper).toEqual({width:482.6,height:330.2});expect(a3.paper).toEqual({width:483,height:329});
 expect(()=>layoutVariant(0,100,options())).toThrow();expect(()=>layoutVariant(100,100,options({sheet:'invented'}))).toThrow();
});

test('printer envelopes, fine-art exclusions and invalid sizes stay warnings, not recipes',async()=>{
 const {layoutVariant}=await geometryModule();
 const panoramic=layoutVariant(2100,900,options({edge:'457.2',printer:'fineart'}));
 expect(panoramic.image.width/25.4).toBeCloseTo(18,12);expect(panoramic.image.height/25.4).toBeCloseTo(7.714285714,8);
 expect(panoramic.endLimit/25.4).toBeCloseTo(17.031496,5);expect(panoramic.warnings.join(' ')).toContain('25 mm');
 const ink=layoutVariant(2100,900,options({edge:'304.8',printer:'fineart',pattern:'stone'}));expect(ink.warnings.join(' ')).toContain('Decorative ink');
 expect(layoutVariant(2100,900,options({sheet:'16x20'})).warnings.join(' ')).toContain('outsourced / other printer required');
 expect(layoutVariant(2100,900,options({printer:'top'})).warnings.join(' ')).toContain('top-feed');
 const custom=layoutVariant(2100,900,options({sheet:'30x13',edge:'711.2'}));expect(custom.image).toEqual({width:711.2,height:304.8});expect(custom.annotated).toContain('geometry only');
 expect(layoutVariant(1000,1000,options({sheet:'8x10',edge:'711.2'})).warnings.join(' ')).toContain('does not fit');
});

test('package wording separates printed artwork, physical mat and frame',async()=>{
 const {packageSummary}=await geometryModule();
 for(const pattern of ['feather','leather','stone']){
  const text=packageSummary(options({pattern}));expect(text.included.join(' ')).toContain('outside the photograph');
  expect(text.excluded.join(' ')).toContain('not real leather, stone');expect(text.excluded.join(' ')).toContain('No physical matboard');expect(text.excluded.join(' ')).toContain('No frame');
 }
 const framed=packageSummary(options({package:'frame',pattern:'leather'}));expect(framed.included.join(' ')).toContain('Separate physical window mat');expect(framed.included.join(' ')).toContain('Physical frame');expect(framed.excluded.join(' ')).not.toContain('No frame');
});

test('desktop/mobile keyboard choices preserve photographs and disclose invalid fit',async({page})=>{
 for(const width of [1440,768,390,320]){
  await page.setViewportSize({width,height:900});await page.goto(`${base}/shop-preview/`);await expect(page.locator('.photo-choice')).toHaveCount(4);
  for(const photo of photos){
   const choice=page.locator(`[data-photo-id="${photo.id}"]`);await choice.focus();await page.keyboard.press('Enter');await expect(page.locator('#photo-title')).toBeFocused();
   const original=await page.locator('#selected-photo').getAttribute('src');
   for(const pattern of ['plain','feather','leather','stone']){
    await page.locator('#pattern').selectOption(pattern);await page.locator('#selected-photo').evaluate(img=>img.decode());
    const ratio=await page.locator('#selected-photo').evaluate(img=>{const r=img.getBoundingClientRect();return r.width/r.height;});
    // Synthetic SVGs use their declared viewport, not WebKit's rounded cache.
    expect(Math.abs(ratio/(photo.width/photo.height)-1)).toBeLessThan(.001);
    await expect(page.locator('#selected-photo')).toHaveAttribute('src',original);
    expect(await page.locator('#print-photo').evaluate(img=>getComputedStyle(img).objectFit)).toBe('contain');
    await expect(page.locator('#surrounds')).not.toContainText('-0.000');
   }
  }
  await page.locator('#package').selectOption('frame');await expect(page.locator('#dimensions')).toContainText('Frame external size');await expect(page.locator('#dimensions')).toContainText('Unsettled');
  await page.locator('#sheet').selectOption('8x10');await page.locator('#edge').selectOption('711.2');await expect(page.locator('#comparison')).toBeHidden();await expect(page.locator('#fit-warnings')).toContainText('does not fit');
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy();
 }
});

test('review stays per variant, simulated and enquiry-only; no data or network writes',async({page})=>{
 const writes=[];page.on('request',request=>{if(request.method()!=='GET')writes.push(request.url());});
 await page.goto(`${base}/shop-preview/`);await expect(page.locator('#study')).toBeVisible();
 await expect(page.locator('meta[name="robots"]')).toHaveAttribute('content','noindex, nofollow, noarchive');
 await expect(page.locator('#pattern')).toHaveValue('plain');await expect(page.locator('#package')).toHaveValue('print');await expect(page.locator('#seller')).toBeDisabled();await expect(page.locator('#seller option')).toHaveCount(1);
 await page.locator('#pattern').selectOption('leather');await expect(page.locator('#excluded')).toContainText('not real leather, stone');
 await expect(page.locator('#contact-print')).toHaveAttribute('href',/^mailto:adrianhensler@gmail\.com\?subject=TEST/);
 await page.locator('#seller-tab').focus();await page.keyboard.press('Enter');await expect(page.locator('#seller-panel')).toBeVisible();await expect(page.locator('#buyer-panel')).toBeHidden();
 for(const box of await page.locator('#review-checklist input').all())await box.check();
 await expect(page.locator('#approval-status')).toContainText('11/11');await expect(page.locator('#approval-status')).toContainText('NOT seller-approved');await expect(page.locator('#approval-status')).toContainText('No physical proof');
 await page.locator('#sheet').selectOption('11x14');await expect(page.locator('#review-checklist input:checked')).toHaveCount(0);
 await page.locator('#signing').selectOption('signed');await page.locator('#fulfilment').selectOption('canada');await page.locator('#buyer-tab').click();await expect(page.locator('#buyer-unsettled')).toContainText('Possible hand-signing');await expect(page.locator('#buyer-unsettled')).toContainText('unapproved');
 await expect(page.locator('input:not([type="checkbox"]),textarea,form,iframe')).toHaveCount(0);expect(writes).toEqual([]);expect(await page.evaluate(()=>Object.keys(localStorage))).toEqual([]);
});

test('safe text/paths and unavailable galleries do not expose stale sale controls',async({page})=>{
 const safe={...photos[0],title:'<img src=x onerror=alert(1)>'};
 await page.route('**/api/gallery/published?*',route=>route.fulfill({json:{images:[safe,{...photos[1],large_url:'https://example.com/private.png'}]}}));
 await page.goto(`${base}/shop-preview/`);await expect(page.locator('.photo-choice')).toHaveCount(1);await expect(page.locator('#photo-title')).toHaveText(safe.title);await expect(page.locator('#photo-title img')).toHaveCount(0);
 await page.route('**/api/gallery/published?*',route=>route.fulfill({status:503,body:'Unavailable'}));await page.reload();await expect(page.locator('#study')).toBeHidden();await expect(page.locator('#load-status')).toContainText('could not be loaded');
});
