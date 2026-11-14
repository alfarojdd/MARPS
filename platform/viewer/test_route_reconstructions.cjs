// Requires the local viewer, Playwright, the reconstruction package and a generated real relief.
const assert = require('node:assert/strict');
const {chromium} = require(process.env.MARPS_PLAYWRIGHT || 'playwright');
const base = process.env.MARPS_VIEWER_URL || 'http://127.0.0.1:8765';

(async () => {
  const browser = await chromium.launch({headless: true, args: ['--no-sandbox', '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader']});
  const errors = [];
  try {
    const page = await browser.newPage({viewport: {width: 1100, height: 800}});
    page.on('pageerror', error => errors.push(error.message));
    // Exercise modal routing/state without allocating a second software WebGL context.
    // test_viewer.cjs separately loads and walks through the real local models.
    await page.route('**/surface.html?*', route => route.fulfill({contentType: 'text/html', body: '<!doctype html><title>Surface modal integration test</title><p>Surface viewer placeholder</p>'}));
    const catalogue = await (await page.request.get(`${base}/api/reconstructions`)).json();
    const inventory = await (await page.request.get(`${base}/api/terrain-sources`)).json();
    assert.ok(inventory.sources.length, 'Generate a real relief with build_terrain3d.py before running this test');

    for (const path of ['/', '/terrain3d/demo.html']) {
      await page.goto(base + path);
      await page.waitForFunction(() => document.querySelector('#sceneList')?.children.length > 0);
      await page.waitForFunction(() => document.querySelector('[data-route-ready=true]'));
      assert.equal(await page.locator('.leaflet-marker-icon.scene-pin').count(), catalogue.counts.placed);
      const routePaths = await page.locator('.leaflet-overlay-pane path').evaluateAll(paths => paths.map(path => path.getAttribute('d')));
      assert.ok(routePaths.length >= 3, 'The route, classic A* and stops must remain visible');
      if (process.env.MARPS_SCREENSHOTS && path !== '/') await page.screenshot({path: `${process.env.MARPS_SCREENSHOTS}/route-pois-2d-demo.jpg`, type: 'jpeg', quality: 82});
      if (path !== '/') await page.locator('.reconstruction-panel summary').click();
      await page.selectOption('#sceneFilter', 'local');
      await page.locator('[data-id=cheyava-falls] .scene-enter').click();
      const frameUrl = await page.locator('#surfaceViewport iframe').getAttribute('src');
      assert.equal(new URL(frameUrl, base).pathname, '/surface.html', 'Nested route page must open the same local scene URL');
      await page.click('#surfaceClose');
      await page.locator('#surfaceViewport iframe').waitFor({state: 'detached'});
      assert.deepEqual(await page.locator('.leaflet-overlay-pane path').evaluateAll(paths => paths.map(path => path.getAttribute('d'))), routePaths);
      if (path !== '/') await page.locator('.reconstruction-panel summary').click();

      await page.click('#btn3d');
      await page.waitForFunction(() => document.querySelector('#btn3d').textContent === '2D' && !document.querySelector('#btn3d').disabled, null, {timeout: 90000});
      assert.ok(await page.locator('.scene-terrain-pin:visible').count());
      const profile = await page.locator('#pinfo').textContent();
      assert.match(profile, /km.*m/);
      if (process.env.MARPS_SCREENSHOTS) await page.screenshot({path: `${process.env.MARPS_SCREENSHOTS}/route-pois-overview-${path === '/' ? 'main' : 'demo'}.jpg`, type: 'jpeg', quality: 82, timeout: 60000});
      // Locate from the catalogue in 3D, then click the actual projected marker.
      if (path !== '/') await page.locator('.reconstruction-panel summary').click();
      await page.fill('#sceneSearch', 'Cheyava');
      await page.locator('#sceneList [data-id=cheyava-falls]').getByRole('button', {name: 'Situar en mapa'}).click();
      if (path !== '/') await page.locator('.reconstruction-panel summary').click();
      const pin = page.locator('.scene-terrain-pin[data-id=cheyava-falls]');
      await pin.waitFor({state: 'visible'});
      await page.waitForFunction(() => {
        const pin = document.querySelector('.scene-terrain-pin[data-id="cheyava-falls"]').getBoundingClientRect();
        const layer = document.querySelector('.scene-terrain-layer').getBoundingClientRect();
        return Math.abs(pin.x + pin.width / 2 - layer.x - layer.width / 2) < layer.width / 5;
      });
      const originalAnchor = await pin.boundingBox();
      await pin.click();
      await page.waitForFunction(() => document.querySelector('#surfaceDialog').open);
      await page.click('#surfaceClose');
      await page.locator('#surfaceViewport iframe').waitFor({state: 'detached'});
      await page.waitForFunction(before => {
        const after = document.querySelector('.scene-terrain-pin[data-id="cheyava-falls"]').getBoundingClientRect();
        return Math.abs(before.x - after.x) < 1 && Math.abs(before.y - after.y) < 1;
      }, originalAnchor);
      assert.equal(await page.locator('#btn3d').textContent(), '2D', 'Closing a scene must preserve the tilted map');
      assert.equal(await page.locator('#pinfo').textContent(), profile);

      await page.click('#routeFit');
      const before = await page.locator('.scene-terrain-pin:visible').evaluateAll(pins => pins.map(pin => pin.style.transform));
      await page.locator('#ex').evaluate(input => { input.value = '6'; input.dispatchEvent(new Event('input', {bubbles: true})); });
      await page.waitForFunction(transforms => {
        const pins = [...document.querySelectorAll('.scene-terrain-pin:not([hidden])')];
        return pins.some((pin, index) => pin.style.transform !== transforms[index]);
      }, before);
      assert.equal(await page.locator('#pinfo').textContent(), profile, 'Vertical exaggeration must not change physical elevation values');
      if (inventory.sources.length > 1) {
        await page.selectOption('#src', inventory.sources[1].url);
        await page.waitForFunction(() => !document.querySelector('#src').disabled, null, {timeout: 60000});
        assert.match(await page.locator('#status').textContent(), /STL/);
        assert.ok(await page.locator('.scene-terrain-pin:visible').count());
      }
      if (process.env.MARPS_SCREENSHOTS) await page.screenshot({path: `${process.env.MARPS_SCREENSHOTS}/route-pois-${path === '/' ? 'main' : 'demo'}.png`, timeout: 60000});

      if (path !== '/') await page.locator('.reconstruction-panel summary').click();
      await page.locator('#sceneMarkers').uncheck();
      assert.equal(await page.locator('.scene-terrain-pin:visible').count(), 0);
      await page.locator('#sceneMarkers').check();
      if (path !== '/') await page.locator('.reconstruction-panel summary').click();
      await page.click('#btn3d');
      await page.waitForFunction(() => document.querySelector('#btn3d').textContent === '3D' && !document.querySelector('#btn3d').disabled, null, {timeout: 60000});
      assert.equal(await page.locator('.scene-terrain-pin:visible').count(), 0);
      assert.equal(await page.locator('.leaflet-marker-icon.scene-pin').count(), catalogue.counts.placed);
      console.log(`${path}: route + 2D/3D POIs, nested scene URL, camera preservation, exaggeration and return OK`);
    }

    // A checkout without generated terrain must still show the route and surface access points.
    await page.route('**/api/terrain-sources', route => route.fulfill({json: {sources: []}}));
    await page.goto(base);
    await page.waitForFunction(() => document.querySelector('#sceneList')?.children.length > 0);
    assert.equal(await page.locator('#btn3d').isDisabled(), true);
    assert.equal(await page.locator('.leaflet-marker-icon.scene-pin').count(), catalogue.counts.placed);
    assert.ok(await page.locator('.leaflet-overlay-pane path').count());
    await page.unroute('**/api/terrain-sources');

    // A WebGL failure must not remove the 2D route or reconstruction catalogue.
    const noGL = await browser.newPage();
    noGL.on('pageerror', error => errors.push(error.message));
    await noGL.addInitScript(() => {
      const original = HTMLCanvasElement.prototype.getContext;
      HTMLCanvasElement.prototype.getContext = function(type, ...args) {
        return type === 'webgl2' ? null : original.call(this, type, ...args);
      };
    });
    await noGL.goto(base);
    await noGL.waitForFunction(() => document.querySelector('#sceneList')?.children.length > 0);
    await noGL.click('#btn3d');
    await noGL.waitForFunction(() => document.querySelector('#status').textContent.includes('Relieve no disponible'), null, {timeout: 60000});
    assert.equal(await noGL.locator('.is3d').count(), 0);
    assert.equal(await noGL.locator('.leaflet-marker-icon.scene-pin').count(), catalogue.counts.placed);
    await noGL.close();

    await page.setViewportSize({width: 390, height: 844});
    for (const path of ['/', '/terrain3d/demo.html']) {
      await page.goto(base + path);
      await page.waitForFunction(() => document.querySelector('#sceneList')?.children.length > 0);
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
    }
    console.log('Missing terrain, unavailable WebGL and mobile layout: OK');
    assert.deepEqual(errors, []);
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
