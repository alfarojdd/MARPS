// Optional browser test: requires the viewer server running and Playwright installed.
// MARPS_PLAYWRIGHT=/path/node_modules/playwright node platform/viewer/test_viewer.cjs
const assert = require('node:assert/strict');
const { chromium } = require(process.env.MARPS_PLAYWRIGHT || 'playwright');
const base = process.env.MARPS_VIEWER_URL || 'http://127.0.0.1:8765';

(async () => {
  const browser = await chromium.launch({headless: true, args: ['--no-sandbox', '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader']});
  const errors = [];
  try {
    const page = await browser.newPage({viewport: {width: 1100, height: 850}});
    page.on('pageerror', error => errors.push(error.message));
    await page.goto(base);
    await page.waitForFunction(() => document.querySelector('#sceneList').children.length > 0);
    const catalog = await page.evaluate(() => fetch('/api/reconstructions').then(r => r.json()));
    assert.equal(await page.locator('.leaflet-marker-icon.scene-pin').count(), catalog.counts.placed);
    const plannedPaths = await page.locator('.leaflet-overlay-pane path').count();
    await page.locator('#sceneRoute').check();
    await page.waitForFunction(count => document.querySelectorAll('.leaflet-overlay-pane path').length > count, plannedPaths);
    await page.locator('#sceneRoute').uncheck();
    assert.equal(await page.locator('.leaflet-overlay-pane path').count(), plannedPaths);
    await page.locator('#sceneMarkers').uncheck();
    assert.equal(await page.locator('.leaflet-marker-icon.scene-pin').count(), 0);
    await page.locator('#sceneMarkers').check();
    await page.selectOption('#sceneFilter', 'unplaced');
    assert.equal(await page.locator('#sceneList .scene-card').count(), catalog.counts.total - catalog.counts.placed);
    assert.equal(await page.getByRole('button', {name: 'Show on map', exact: true}).count(), 0);
    await page.selectOption('#sceneFilter', 'local');
    await page.fill('#sceneSearch', 'Cheyava');
    assert.equal(await page.locator('#sceneList .scene-card').count(), 1);
    await page.fill('#sceneSearch', 'no-scene-with-this-name');
    assert.match(await page.locator('#sceneList').textContent(), /No reconstructions match/);
    await page.fill('#sceneSearch', '');
    console.log('Map, catalogue, filters and visibility: OK');

    // Check the external integration without depending on Sketchfab availability.
    await page.route('https://sketchfab.com/models/**/embed*', route => route.fulfill({body: '<p>Test external viewer</p>', contentType: 'text/html'}));
    await page.selectOption('#sceneFilter', 'landscape');
    const external = page.locator('#sceneList .scene-card').filter({hasText: 'Sketchfab'}).first();
    await external.locator('.scene-enter').click();
    assert.match(await page.locator('#surfaceViewport iframe').getAttribute('src'), /navigation=fps/);
    await page.click('#surfaceClose');
    await page.locator('#surfaceViewport iframe').waitFor({state: 'detached'});
    assert.equal(await page.locator('#surfaceViewport iframe').count(), 0);
    console.log('External viewer open and close: OK');

    // Moderate resolution: the CI browser uses software rendering.
    await page.setViewportSize({width: 640, height: 480});
    for (const id of ['cheyava-falls', 'nasa-navcam-sol180']) {
      if (!catalog.scenes.some(s => s.id === id && s.available)) continue;
      await page.goto(`${base}/surface.html?id=${id}&quality=light`);
      await page.locator('#view[data-ready=true]').waitFor({timeout: 90000});
      await page.waitForFunction(() => document.querySelector('#view').dataset.position, null, {timeout: 90000});
      const position = await page.locator('#view').getAttribute('data-position');
      assert.equal(position.split(',').length, 3);
      await page.locator('#view').click({position: {x: 200, y: 200}});
      await page.keyboard.down('w');
      try {
        await page.waitForFunction(before => document.querySelector('#view').dataset.position !== before, position, {timeout: 30000});
      } finally { await page.keyboard.up('w'); }
      await page.locator('#orbit').click();
      assert.equal(await page.locator('#orbit').getAttribute('aria-pressed'), 'true');
      await page.locator('#walk').click();
      assert.equal(await page.locator('#walk').getAttribute('aria-pressed'), 'true');
      if (process.env.MARPS_SCREENSHOTS) {
        await page.waitForTimeout(1500);
        await page.screenshot({path: `${process.env.MARPS_SCREENSHOTS}/${id}.png`, timeout: 60000});
      }
      console.log(`${id}: loading, movement and camera modes OK`);
    }
    await page.setViewportSize({width: 390, height: 844});
    await page.goto(base);
    await page.waitForFunction(() => document.querySelector('#sceneList').children.length > 0);
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
    await page.click('#sceneFeatured');
    await page.click('#surfaceClose');
    await page.locator('#surfaceViewport iframe').waitFor({state: 'detached'});
    assert.equal(await page.locator('#surfaceViewport iframe').count(), 0);
    console.log('Mobile layout and return to map: OK');
    assert.deepEqual(errors, []);
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
