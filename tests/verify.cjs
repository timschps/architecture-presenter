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
  const env = { ...process.env, ARCHITECTURE_PRESENTER_CONFIG_ROOT: path.join(temp, 'libraries') };
  const run = args => {
    const result = spawnSync('python', args, { encoding: 'utf8', env });
    assert.equal(result.status, 0, result.stderr);
  };
  const mixedDecisionText = 'The source separates <request> input & runtime execution.';
  let bareHtml;
  let html = process.argv[2] && path.resolve(process.argv[2]);
  if (!html) {
    run([path.join(root, 'skills', 'architecture-presenter', 'scripts', 'init.py'),
      '--project-root', project, '--name', 'Fabrikam architecture']);
    const storyPath = path.join(project, 'architecture', 'story.json');
    const story = JSON.parse(fs.readFileSync(storyPath, 'utf8'));
    story.views = { system: story.views.architecture, principles: story.views.principles };
    story.views.system.phases[1].title = 'A deliberately longer title that wraps while the architecture remains in exactly the same position';
    const plain = JSON.parse(JSON.stringify(story.views.system));
    plain.label = 'Architecture only';
    for (const phase of plain.phases) {
      for (const key of ['principles', 'decisions', 'value', 'tradeoff', 'basis']) delete phase[key];
    }
    fs.writeFileSync(path.join(project, 'evidence.txt'),
      'Synthetic test decision: separate acceptance from execution to keep review independent.');
    plain.phases[0].evidence = ['evidence.txt'];
    plain.components[0].evidence = ['evidence.txt'];
    const mixed = JSON.parse(JSON.stringify(plain));
    mixed.label = 'Optional decision context';
    mixed.phases[1].principles = ['P2'];
    mixed.phases[1].basis = 'inferred';
    mixed.phases[2].decisions = [mixedDecisionText];
    mixed.phases[2].basis = 'observed';
    mixed.phases[4].value = 'Consider recording a reviewed architecture decision.';
    mixed.phases[4].tradeoff = 'Decision records require review and maintenance.';
    mixed.phases[4].basis = 'proposed';
    story.views.plain = plain;
    story.views.mixed = mixed;
    story.principles.P1.basis = 'documented';
    story.principles.P1.evidence = ['evidence.txt'];
    story.views.system.phases[0].basis = 'documented';
    story.views.system.phases[0].evidence = ['evidence.txt'];
    delete story.principles.P2.basis;
    delete story.views.system.phases[1].basis;
    fs.writeFileSync(storyPath, JSON.stringify(story));
    run([path.join(project, 'architecture', 'build.py'), '--input', storyPath,
      '--project-root', project, '--output', path.join(project, 'architecture')]);
    html = path.join(project, 'architecture', 'presenter.html');
    const clean = fs.readFileSync(html, 'utf8');
    assert.ok(!clean.includes('ignite') && !clean.includes('BRK285'), 'No owner theme in clean distribution');
    const localTheme = path.join(project, 'architecture', 'themes', 'midnight.json');
    fs.writeFileSync(localTheme, JSON.stringify({
      schemaVersion: 1, id: 'midnight', label: 'Midnight <local>', base: 'fluent',
      defaultAppearance: 'dark', appearances: { dark: { accent: '#aabbcc' } },
    }));
    const localLayout = path.join(project, 'architecture', 'layouts', 'workshop.json');
    fs.writeFileSync(localLayout, JSON.stringify({
      schemaVersion: 1, id: 'workshop', label: 'Workshop', preset: 'stage-ribbon',
      options: { captionHeight: 120, explanationHeight: 120, groupHeaders: true, trackGroupTitles: true },
    }));
    run([path.join(project, 'architecture', 'build.py'), '--input', storyPath,
      '--project-root', project, '--output', path.join(project, 'architecture'),
      '--stage-theme', 'project:midnight', '--stage-layout', 'project:workshop']);
    const bareStory = { ...story, views: { plain } };
    delete bareStory.principles;
    delete bareStory.insights;
    const bareStoryPath = path.join(project, 'architecture', 'bare-story.json');
    fs.writeFileSync(bareStoryPath, JSON.stringify(bareStory));
    run([path.join(project, 'architecture', 'build.py'), '--input', bareStoryPath,
      '--project-root', project, '--output', path.join(project, 'bare')]);
    bareHtml = path.join(project, 'bare', 'presenter.html');
  }
  const browser = await chromium.launch({ channel: process.platform === 'win32' ? 'msedge' : undefined });
  try {
    const context = await browser.newContext({ offline: true, reducedMotion: 'reduce' });
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
    const catalog = await page.evaluate(() => window.presenterDesign.design);
    const hasLocal = Object.hasOwn(catalog.themes, 'midnight');
    const combinations = Object.entries(catalog.layouts).flatMap(([layout, definition]) =>
      Object.entries(catalog.themes).flatMap(([theme, definitionTheme]) =>
        Object.keys(definitionTheme.appearances).map(appearance =>
          ({ layout, theme, appearance, presenting: definition.preset !== 'explore' }))));
    for (const { layout, theme, appearance, presenting } of combinations) {
    for (const [width, height] of [[1280, 720], [1920, 1080], [3840, 2160]]) {
      await page.setViewportSize({ width, height });
      for (const view of views) {
        await page.goto(`${base}?view=${view}&phase=1&details=0&present=${presenting ? 1 : 0}&layout=${layout}&theme=${theme}&appearance=${appearance}`);
        const count = Number(await page.locator('#slider').getAttribute('max'));
        const initial = await firstGeometry();
        for (let phase = 1; phase <= count; phase++) {
          assert.equal(await page.locator('#slider').inputValue(), String(phase));
          assert.equal(await page.locator('#canvas svg').getAttribute('viewBox'), '0 0 1490 700');
          assert.equal(await page.locator('.group.future').count(), 0);
          assert.deepEqual(await firstGeometry(), initial, `${view}/${phase}: stable screen coordinates at ${width}`);
          if (view === 'plain' && !process.argv[2]) {
            assert.equal(await page.locator('#principle-strip').isVisible(), false);
            assert.equal(await page.locator('html').getAttribute('data-commentary'), 'false');
            assert.equal(await page.locator('#status-key').isVisible(), true);
            assert.doesNotMatch(await page.locator('#panel').textContent(), /Decision context|Requirement:|undefined/i);
          }
          if (view === 'mixed' && !process.argv[2]) {
            const activeCommentary = [2, 3, 5].includes(phase);
            assert.equal(await page.locator('#principle-strip').isVisible(), activeCommentary);
            assert.equal(await page.locator('#principle-strip').getAttribute('aria-hidden'), String(!activeCommentary));
            assert.equal(await page.locator('#principle-context').count(), activeCommentary ? 1 : 0);
            assert.equal(await page.locator('#principle-strip').evaluate(strip => strip.inert), !activeCommentary);
            if (activeCommentary) {
              const label = { 2: /Inferred rationale/, 3: /Source observation/, 5: /Suggested lens/ }[phase];
              assert.match(await page.locator('#principle-strip .basis-label').innerText(), label);
            }
            if (phase === 3) {
              assert.equal(await page.locator('#principle-strip .decision').innerText(), mixedDecisionText);
              assert.equal(await page.locator('#principle-strip request').count(), 0);
              assert.match(await page.locator('#panel').textContent(), /Source observation, not recorded intent/);
            }
            if (phase === 5) {
              assert.match(await page.locator('#panel').textContent(), /Suggested lens, not an approved principle/);
              assert.match(await page.locator('#panel').textContent(), /Decision records require review and maintenance/);
            }
          }
          if (view === 'system' && !process.argv[2] && phase <= 2) {
            assert.equal(await page.locator('#principle-strip .basis-label').innerText(),
              phase === 1 ? 'Documented rationale' : 'Basis not recorded');
          }
          const issues = await page.evaluate(() => {
            const result = [];
            if (document.documentElement.dataset.present === 'true') {
              const caption = document.querySelector('.caption').getBoundingClientRect();
              const title = document.querySelector('#phase-title').getBoundingClientRect();
              const ribbon = document.querySelector('#principle-strip').getBoundingClientRect();
              if (title.bottom > caption.bottom + 1 || title.right > caption.right + 1)
                result.push('Reveal title overflows its reserved caption');
              for (const item of document.querySelectorAll('#principle-strip > *')) {
                const box = item.getBoundingClientRect();
                if (box.bottom > ribbon.bottom + 1 || box.right > ribbon.right + 1)
                  result.push('Ribbon content overflows its reserved area');
              }
            }
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
          if (presenting) {
          const sizes = await page.evaluate(() => {
            const size = selector => {
              const element = document.querySelector(selector);
              return element ? parseFloat(getComputedStyle(element).fontSize) : null;
            };
            return {
              title: size('#phase-title'), heading: size('#principle-strip strong'),
              content: size('#principle-strip .decision'),
              key: size('#principle-strip .implementation-key, #status-key:not([hidden])'),
            };
          });
          assert.ok(sizes.title >= height * 0.032, `${view}/${phase}: stage title size at ${width}`);
          if (sizes.heading !== null) assert.ok(sizes.heading >= height * 0.023, `${view}/${phase}: stage ribbon heading size at ${width}`);
          if (sizes.content !== null) assert.ok(sizes.content >= height * 0.019, `${view}/${phase}: stage ribbon text size at ${width}`);
          if (sizes.key !== null) assert.ok(sizes.key >= height * 0.015, `${view}/${phase}: stage status key size at ${width}`);
          }
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
        await page.waitForFunction(() => [...document.querySelectorAll('.node:not(.future):not(.gone)')]
          .every(node => getComputedStyle(node).opacity === '1'));
        await page.screenshot({ path: path.join(temp, `${layout}-${theme}-${appearance}-${view}-${width}.png`) });
      }
    }
    }
    if (bareHtml) {
      await page.goto(`${pathToFileURL(bareHtml).href}?view=plain&phase=1&details=0`);
      assert.equal(await page.locator('#principle-strip').isVisible(), false);
      assert.equal(await page.locator('#status-key').isVisible(), true);
      await page.keyboard.press('KeyC');
      assert.equal(await page.locator('#inspector').isVisible(), true);
      assert.match(await page.locator('#panel').innerText(), /Repository evidence/i);
      assert.doesNotMatch(await page.locator('#panel').innerText(), /Decision context|Requirement:|undefined/i);
      assert.ok(await page.locator('#panel a[href$="/blob/main/evidence.txt"]').count());
      await page.locator('.node:not(.future):not(.gone)').first().click();
      assert.match(await page.locator('#panel').innerText(), /Implementation state: TARGET/);
      assert.match(await page.locator('#panel').innerText(), /Component evidence/i);
      assert.ok(await page.locator('#panel a[href$="/blob/main/evidence.txt"]').count());
    }
    for (const theme of ['light', 'dark']) {
      await page.goto(`${base}?view=${views[0]}&phase=1&present=0&brand=fluent&scoutTheme=${theme}&details=0`);
      assert.equal(await page.locator('html').getAttribute('data-appearance'), theme);
      assert.equal(await page.locator('html').getAttribute('data-design-theme'), 'fluent');
    }
    await page.goto(`${base}?view=${views[0]}&phase=1&details=0&theme=fluent&layout=stage`);
    await page.locator('#stage-design').click();
    await page.locator('#design-layout').selectOption('stage-ribbon');
    assert.equal(await page.locator('html').getAttribute('data-design-theme'), 'fluent');
    await page.locator('#design-appearance').selectOption('light');
    if (hasLocal) {
      await page.locator('#design-theme').selectOption('midnight');
      assert.equal(await page.locator('html').getAttribute('data-layout'), 'stage-ribbon');
      assert.equal(await page.locator('html').getAttribute('data-appearance'), 'dark');
      assert.match(await page.locator('#design-effective').innerText(), /Supported: dark/);
      assert.equal(await page.locator('#design-appearance option[value="light"]').evaluate(option => option.disabled), true,
        JSON.stringify(errors));
    }
    await page.locator('[data-close="design-settings"]').click();
    const designUrl = page.url();
    await page.reload();
    assert.equal(page.url(), designUrl, 'Design choices round-trip in URL');
    await page.locator('#exit-present').click();
    assert.equal(await page.locator('html').getAttribute('data-layout'), 'explore');
    const chosenTheme = await page.locator('html').getAttribute('data-design-theme');
    await page.locator('#present').click();
    // Explicit stageTheme is allowed to switch branding, unlike an inferred theme ID.
    assert.equal(await page.locator('html').getAttribute('data-design-theme'), hasLocal ? 'midnight' : chosenTheme);
    await page.locator('[data-close="journey-menu"]').click();
    await page.evaluate(() => { window.presenterDesign.design.settings.stageTheme = null; });
    await page.locator('#exit-present').click();
    await page.locator('#theme').click();
    await page.locator('#design-theme').selectOption('fluent');
    await page.locator('[data-close="design-settings"]').click();
    await page.locator('#present').click();
    assert.equal(await page.locator('html').getAttribute('data-design-theme'), 'fluent',
      'Present never infers an event theme');
    await page.locator('[data-close="journey-menu"]').click();
    await page.goto(`${base}?phase=1&theme=missing&layout=missing&appearance=missing`);
    assert.match(await page.locator('#notice').innerText(), /Unavailable theme.*Unavailable appearance.*Unavailable layout/);
    await page.goto(`${base}?phase=1&brand=missing-personal-theme`);
    assert.match(await page.locator('#notice').innerText(), /Unavailable theme/);
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
    if (await page.locator('#principle-context').count()) {
      await page.locator('#principle-context').click();
      if (await page.locator('#panel .principle-chain').count())
        assert.match(await page.locator('#panel').innerText(), /Requirement:.*Trade-off:.*Evidence limit:/s);
      else assert.match(await page.locator('#panel').innerText(), /Decision context/i);
    } else {
      await page.keyboard.press('KeyC');
      assert.match(await page.locator('#panel').innerText(), /Repository evidence/i);
      assert.doesNotMatch(await page.locator('#panel').innerText(), /Decision context|Requirement:|undefined/i);
    }
    await page.locator('#context-close').click();
    await page.goto(`${base}?view=missing&phase=-99&brand=invalid&focus=missing`);
    assert.equal(await page.locator('#slider').inputValue(), '1');
    assert.match(await page.locator('#notice').innerText(), /not active/);
    await page.setViewportSize({ width: 390, height: 844 });
    for (const layout of ['explore', 'stage', 'stage-ribbon']) {
      for (const view of views) {
        await page.goto(`${base}?view=${view}&present=${layout === 'explore' ? 0 : 1}&details=0&layout=${layout}`);
        assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), layout);
      }
    }
    await page.goto(`${base}?view=${views[0]}&phase=1`);
    await page.evaluate(() => { document.documentElement.requestFullscreen = () => Promise.reject(new Error('Test denial')); });
    await page.locator('#fullscreen').click();
    await page.waitForFunction(() => document.getElementById('notice').textContent.includes('Test denial'));
    assert.match(await page.locator('#notice').innerText(), /Windowed stage mode still works/);
    assert.deepEqual(errors, []);
    assert.deepEqual(requests, []);
    console.log(`PASS: declarative generation, 720p/1080p/4K stage typography, fixed overview, stable coordinates, manual zoom, focus, blackout, deep links, themes, responsive and offline. Screenshots: ${temp}`);
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
