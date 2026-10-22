// Uses the repository's existing @playwright/test development dependency.
const {chromium, expect} = require('@playwright/test');
const assert = require('node:assert/strict');
const {mkdtempSync, rmSync} = require('node:fs');
const {tmpdir} = require('node:os');
const path = require('node:path');
const {spawn, spawnSync} = require('node:child_process');
const cwd = path.resolve(__dirname, '..');
const temp = mkdtempSync(path.join(tmpdir(), 'local-browser-ui-'));
const python = process.env.PYTHON || 'python';
let server, browser;
(async () => {
  const demo = path.join(temp, 'demo');
  const fixture = spawnSync(python, ['-m', 'local_browser', 'demo', demo], {cwd, encoding:'utf8'});
  assert.equal(fixture.status, 0, fixture.stderr);
  server = spawn(python, ['-m', 'local_browser', 'serve', path.join(demo, 'photos'), '--metadata', path.join(demo, 'metadata.json'), '--data-dir', path.join(temp, 'catalog'), '--port', '8080'], {cwd});
  await new Promise((resolve, reject) => {
    let log = '';
    const timeout = setTimeout(() => reject(new Error('Server startup timed out: ' + log)), 30000);
    server.stdout.on('data', chunk => { log += chunk; if (log.includes('Open http://')) { clearTimeout(timeout); resolve(); } });
    server.on('exit', code => { clearTimeout(timeout); reject(new Error('Server exited: ' + code)); });
  });
  browser = await chromium.launch({headless:true});
  const page = await browser.newPage({viewport:{width:1440,height:1000}});
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto('http://127.0.0.1:8080');
  await page.waitForSelector('.tile');
  assert.equal(await page.locator('.tile').count(), 24);
  await page.locator('.tile').first().click();
  await page.getByRole('button', {name:'Open preview'}).click();
  await expect.poll(() => page.locator('#large').evaluate(image => image.naturalWidth)).toBeGreaterThan(0);
  const first = await page.locator('#viewername').textContent();
  await page.keyboard.press('ArrowRight');
  assert.notEqual(await page.locator('#viewername').textContent(), first);
  await page.keyboard.press('Escape');
  assert.equal(await page.locator('dialog').isVisible(), false);
  await page.selectOption('select[name=category]', 'nature');
  await expect(page.locator('#count')).toContainText('12 photos');
  assert.equal(await page.locator('.tile').count(), 12);
  await page.getByRole('button', {name:'Clear filters'}).click();
  await expect(page.locator('#count')).toContainText('24 photos');
  await page.fill('input[name=q]', '<script>bad</script>');
  await expect(page.locator('#count')).toContainText('0 photos');
  await page.getByRole('button', {name:'Clear filters'}).click();
  await page.waitForSelector('.tile');
  await page.locator('.tile').first().click();
  if (process.env.SCREENSHOT_DIR) await page.screenshot({path:path.join(process.env.SCREENSHOT_DIR, 'desktop.png'), fullPage:true});
  await page.setViewportSize({width:390,height:844});
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
  if (process.env.SCREENSHOT_DIR) await page.screenshot({path:path.join(process.env.SCREENSHOT_DIR, 'mobile.png'), fullPage:true});
  assert.deepEqual(errors, []);
  console.log('UI smoke passed: grid, preview, keyboard, filters, empty state, responsive layout');
})().catch(error => {console.error(error); process.exitCode = 1;}).finally(async () => {
  if (browser) await browser.close();
  if (server && server.exitCode === null) {
    await new Promise(resolve => {server.once('exit', resolve); server.kill();});
  }
  rmSync(temp, {recursive:true, force:true});
});
