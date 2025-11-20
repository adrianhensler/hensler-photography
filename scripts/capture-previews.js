/**
 * Capture preview screenshots for landing page cards
 *
 * Usage: node capture-previews.js
 */

const { chromium } = require('@playwright/test');
const path = require('path');

async function capturePreview(url, outputPath, width = 1200, height = 800) {
  console.log(`Capturing ${url}...`);

  const browser = await chromium.launch();
  const context = await browser.newContext({
    viewport: { width, height },
    deviceScaleFactor: 2 // Retina quality
  });

  const page = await context.newPage();

  try {
    // Navigate to the page
    await page.goto(url, { waitUntil: 'networkidle' });

    // Wait a bit for any animations or lazy-loaded images
    await page.waitForTimeout(2000);

    // Take screenshot
    await page.screenshot({
      path: outputPath,
      type: 'jpeg',
      quality: 85
    });

    console.log(`✓ Saved to ${outputPath}`);
  } catch (error) {
    console.error(`✗ Failed to capture ${url}:`, error.message);
  } finally {
    await browser.close();
  }
}

async function main() {
  const outputDir = path.join(__dirname, 'sites', 'main', 'assets');

  console.log('Capturing preview screenshots...\n');

  // Capture Liam's site
  await capturePreview(
    'https://liam.hensler.photography',
    path.join(outputDir, 'liam-preview.jpg')
  );

  // Capture Adrian's site
  await capturePreview(
    'https://adrian.hensler.photography',
    path.join(outputDir, 'adrian-preview.jpg')
  );

  console.log('\n✓ All screenshots captured!');
}

main().catch(console.error);
