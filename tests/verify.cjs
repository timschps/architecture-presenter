const { chromium } = require('@playwright/test');
const assert = require('node:assert/strict');
const path = require('node:path');
const fs = require('node:fs');
const os = require('node:os');
const { spawnSync } = require('node:child_process');
const { pathToFileURL } = require('node:url');

(async () => {
  const root = path.resolve(__dirname, '..');
  const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'architecture-presenter-'));
  const project = path.join(temp, 'project');
  fs.mkdirSync(project);
  const run = args => {
    const result = spawnSync('python', args, { encoding: 'utf8' });
    assert.equal(result.status, 0, result.stderr);
  };
  let html = process.argv[2] && path.resolve(process.argv[2]);
  if (!html) {
    run([path.join(root, 'skills', 'architecture-presenter', 'scripts', 'init.py'),
      '--project-root', project, '--name', 'Fabrikam architecture']);
    const storyPath = path.join(project, 'architecture', 'story.json');
    const story = JSON.parse(fs.readFileSync(storyPath, 'utf8'));
    story.views = { system: story.views.architecture, principles: story.views.principles };
    story.views.system.phases[1].title = 'A deliberately longer title that wraps while the architecture remains in exactly the same position';
    fs.writeFileSync(storyPath, JSON.stringify(story));
    run([path.join(project, 'architecture', 'build.py'), '--input', storyPath,
      '--project-root', project, '--output', path.join(project, 'architecture')]);
    html = path.join(project, 'architecture', 'presenter.html');
  }
  const browser = await chromium.launch({ channel: process.platform === 'win32' ? 'msedge' : undefined });
  try {
    const context = await browser.newContext({ offline: true });
    const page = await context.newPage();
    const errors = [], requests = [];
    page.on('pageerror', e => errors.push(e.message));
    page.on('request', r => { if (/^https?:/.test(r.url())) requests.push(r.url()); });
    const base = pathToFileURL(html).href;
    const firstGeometry = () => page.locator('.node .node-box').first().evaluate(element => {
      const box = element.getBBox(), matrix = element.getScreenCTM();
      const origin = new DOMPoint(box.x, box.y).matrixTransform(matrix);
      return { x: origin.x, y: origin.y, width: box.width * matrix.a, height: box.height * matrix.d };
    });
    await page.goto(base);
    await page.waitForFunction(() => document.getElementById('phase-title').textContent);
    const views = await page.locator('[data-journey]').evaluateAll(nodes => nodes.map(n => n.dataset.journey));
    for (const [width, height] of [[1280, 720], [1920, 1080]]) {
      await page.setViewportSize({ width, height });
      for (const view of views) {
        await page.goto(`${base}?view=${view}&phase=1&details=0`);
        const count = Number(await page.locator('#slider').getAttribute('max'));
        const initial = await firstGeometry();
        for (let phase = 1; phase <= count; phase++) {
          assert.equal(await page.locator('#slider').inputValue(), String(phase));
          assert.equal(await page.locator('#canvas svg').getAttribute('viewBox'), '0 0 1490 700');
          assert.equal(await page.locator('.group.future').count(), 0);
          assert.deepEqual(await firstGeometry(), initial, `${view}/${phase}: stable screen coordinates at ${width}`);
          const issues = await page.evaluate(() => {
            const result = [];
            for (const node of document.querySelectorAll('.node:not(.future):not(.gone)')) {
              const box = node.querySelector('rect').getBBox();
              for (const label of node.querySelectorAll('text')) {
                if (getComputedStyle(label).display === 'none') continue;
                const text = label.getBBox();
                if (text.x < box.x || text.x + text.width > box.x + box.width || text.y + text.height > box.y + box.height)
                  result.push(`${node.id}: ${label.textContent}`);
              }
            }
            if ([...document.querySelectorAll('.future,.gone')].some(n => n.tabIndex >= 0)) result.push('Hidden focus target');
            return result;
          });
          assert.deepEqual(issues, []);
          if (phase < count) await page.keyboard.press('PageDown');
        }
        await page.keyboard.press('PageDown');
        assert.match(await page.locator('#notice').innerText(), /End of this journey/);
        await page.locator('.node:not(.future):not(.gone)').first().click();
        assert.equal(await page.locator('#canvas').getAttribute('data-zoomed'), 'true');
        await page.keyboard.press('Escape');
        assert.equal(await page.locator('#canvas').getAttribute('data-zoomed'), 'false');
        await page.locator('#context-close').click();
        await page.keyboard.press('KeyB');
        assert.equal(await page.locator('#blackout').isVisible(), true);
        await page.keyboard.press('Space');
        assert.equal(await page.locator('#blackout').isVisible(), false);
        await page.screenshot({ path: path.join(temp, `${view}-${width}.png`) });
      }
    }
    for (const theme of ['light', 'dark']) {
      await page.goto(`${base}?view=${views[0]}&phase=1&present=0&brand=fluent&scoutTheme=${theme}&details=0`);
      assert.equal(await page.locator('html').getAttribute('data-theme'), theme);
    }
    await page.goto(`${base}?view=${views[0]}&phase=1&details=0`);
    await page.keyboard.down('ArrowRight');
    await page.keyboard.down('ArrowRight');
    await page.keyboard.up('ArrowRight');
    assert.equal(await page.locator('#slider').inputValue(), '2', 'Held-key repeats do not skip reveals');
    await page.locator('#stage-settings').click();
    await page.locator('#learn-next').click();
    await page.keyboard.press('KeyN');
    assert.equal(await page.locator('#next-binding').innerText(), 'KeyN');
    await page.keyboard.press('KeyN');
    assert.match(await page.locator('#key-test').innerText(), /No reveal was advanced/);
    await page.locator('[data-close="settings"]').click();
    await page.keyboard.press('KeyN');
    assert.equal(await page.locator('#slider').inputValue(), '3');
    await page.locator('#principle-context').click();
    assert.match(await page.locator('#panel').innerText(), /Requirement:.*Trade-off:.*Evidence limit:/s);
    await page.locator('#context-close').click();
    await page.goto(`${base}?view=missing&phase=-99&brand=invalid&focus=missing`);
    assert.equal(await page.locator('#slider').inputValue(), '1');
    assert.match(await page.locator('#notice').innerText(), /not active/);
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto(`${base}?view=${views[0]}&present=1&details=0`);
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));
    assert.deepEqual(errors, []);
    assert.deepEqual(requests, []);
    console.log(`PASS: declarative generation, arbitrary journeys, fixed overview, stable coordinates, manual zoom, focus, blackout, deep links, themes, responsive and offline. Screenshots: ${temp}`);
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
