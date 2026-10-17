// Real DOM regression for the production mobile mutation block; no server/API.
const fs = require('node:fs'), path = require('node:path'), os = require('node:os');
const crypto = require('node:crypto'), assert = require('node:assert/strict');
const { chromium } = require(process.env.R193_PLAYWRIGHT_MODULE || 'playwright');
const repo = path.resolve(__dirname, '../..');
const out = process.env.R193_OUT || path.join(os.tmpdir(), 'toanaas-mobile-nav-' + crypto.randomBytes(5).toString('hex'));
fs.mkdirSync(out, { recursive: true });
const source = fs.readFileSync(path.join(repo, 'static/portal/portal.js'), 'utf8');
const start = source.indexOf('      mobileNav.hidden = !mobileNavMarkup;');
const end = source.indexOf('      if (mobileNavMarkup) mobileNav.dataset.portalMobileNavKind', start);
assert.ok(start >= 0 && end > start, 'Production mobile mutation block must exist');
const block = source.slice(start, end), phase = block.includes('createElement("template")') ? 'after' : 'before';
const result = { run: 'R193_REAL_DOM_RENDER_BLOCK', phase, portalHash: crypto.createHash('sha256').update(source).digest('hex'), cases: [] };
(async () => {
  const browser = await chromium.launch({ headless: true,
    ...(process.env.R193_CHROME_PATH ? { executablePath: process.env.R193_CHROME_PATH } : {}),
    args: ['--disable-background-networking', '--proxy-server=http://127.0.0.1:9', '--proxy-bypass-list=127.0.0.1;localhost'],
  });
  try {
    const context = await browser.newContext({ serviceWorkers: 'block' });
    await context.route('**/*', route => route.abort());
    const page = await context.newPage();
    await page.setContent('<main><nav id="qa-nav"></nav></main>');
    result.cases = await page.evaluate(code => {
      const render = new Function('mobileNav', 'mobileNavMarkup', 'appKind', code);
      const base = '<a href="/projects"><span>Dự án</span></a>';
      const svg = '<a href="/projects"><svg viewBox="0 0 20 20"><path d="M0 0L20 20" /></svg><span>Dự án</span></a>';
      const cases = [];
      for (const fixture of [
        { id: 'unchanged_customer_focus', kind: 'customer', initial: base, next: base, wantSame: true },
        { id: 'normalized_svg_unchanged', kind: 'customer', initial: svg, next: svg, wantSame: true },
        { id: 'changed_destination', kind: 'customer', initial: base, next: '<a href="/voice"><span>Giọng đọc</span></a>', wantSame: false },
        { id: 'changed_locale', kind: 'customer', initial: base, next: '<a href="/projects"><span>Projects</span></a>', wantSame: false },
        { id: 'changed_current_projection', kind: 'customer', initial: base, next: '<a href="/projects" aria-current="page"><span>Dự án</span></a>', wantSame: false },
        { id: 'clear_customer_hidden', kind: 'customer', initial: base, next: '', wantSame: false },
        { id: 'admin_same_retains_legacy_replace', kind: 'admin', initial: base, next: base, wantSame: false },
      ]) {
        const nav = document.querySelector('#qa-nav'); nav.hidden = false; nav.innerHTML = fixture.initial;
        const original = nav.firstElementChild; original.focus(); render(nav, fixture.next, fixture.kind);
        const same = nav.firstElementChild === original, focusSame = document.activeElement === original;
        const template = document.createElement('template'); template.innerHTML = fixture.next;
        cases.push({ id: fixture.id, kind: fixture.kind,
          pass: same === fixture.wantSame && (!fixture.wantSame || focusSame) && nav.innerHTML === template.innerHTML && nav.hidden === !fixture.next,
          same, focusSame, hidden: nav.hidden, actual: nav.innerHTML });
      }
      return cases;
    }, block);
    await context.close();
    result.failed = result.cases.filter(item => !item.pass).length;
    fs.writeFileSync(path.join(out, 'mobile-nav-dom-' + phase + '.json'), JSON.stringify(result, null, 2));
    for (const item of result.cases) console.log('R193_CASE ' + JSON.stringify(item));
    assert.equal(result.failed, 0, 'Render block must preserve only unchanged customer DOM');
    console.log('R193_REAL_DOM_BLOCK_PASS7');
  } finally { await browser.close(); }
})().catch(error => {
  result.fatal = error.stack;
  fs.writeFileSync(path.join(out, 'mobile-nav-dom-' + phase + '.json'), JSON.stringify(result, null, 2));
  console.error(error.stack); process.exitCode = 1;
});
