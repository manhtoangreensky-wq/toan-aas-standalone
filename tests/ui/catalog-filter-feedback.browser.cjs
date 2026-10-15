// Exercise the real production local-filter callback in a real browser DOM.
const fs = require('node:fs'), path = require('node:path'), os = require('node:os');
const crypto = require('node:crypto'), assert = require('node:assert/strict');
const { chromium } = require(process.env.R194_PLAYWRIGHT_MODULE || 'playwright');
const repo = path.resolve(__dirname, '../..');
const source = fs.readFileSync(path.join(repo, 'static/portal/portal-features.js'), 'utf8');
const start = source.indexOf('    const filter = () => {', source.indexOf('function renderCatalogue('));
const end = source.indexOf('    input.addEventListener("input", filter);', start);
assert.ok(start >= 0 && end > start, 'Production catalogue filter must exist');
const block = source.slice(start, end), phase = block.includes('section.hidden') ? 'after' : 'before';
const out = process.env.R194_OUT || path.join(os.tmpdir(), 'toanaas-filter-' + crypto.randomBytes(5).toString('hex'));
fs.mkdirSync(out, { recursive: true });
const result = { run: 'R194_REAL_DOM_FILTER_CALLBACK', phase, featureHash: crypto.createHash('sha256').update(source).digest('hex'), cases: [] };
(async () => {
  const browser = await chromium.launch({ headless: true,
    ...(process.env.R194_CHROME_PATH ? { executablePath: process.env.R194_CHROME_PATH } : {}),
    args: ['--disable-background-networking', '--proxy-server=http://127.0.0.1:9', '--proxy-bypass-list=127.0.0.1;localhost'],
  });
  try {
    const context = await browser.newContext({ serviceWorkers: 'block' });
    await context.route('**/*', route => route.abort());
    const page = await context.newPage();
    await page.setContent('<input id="query"><button id="clear">Clear</button><p id="result"></p><section id="catalog"><section data-catalog-group="music"><b class="portal-feature-count">2</b><article data-catalog-item data-catalog-text="music_background"></article><article data-catalog-item data-catalog-text="music_song"></article></section><section data-catalog-group="voice"><b class="portal-feature-count">1</b><article data-catalog-item data-catalog-text="voice_tts"></article></section></section>');
    result.cases = await page.evaluate(code => {
      const input = document.querySelector('#query'), clear = document.querySelector('#clear');
      const result = document.querySelector('#result'), catalog = document.querySelector('#catalog');
      const cards = Array.from(catalog.querySelectorAll('[data-catalog-item]'));
      const filter = new Function('input', 'cards', 'clear', 'result', 'copy', 'catalog', code + '\nreturn filter;')(input, cards, clear, result, { result: 'matches' }, catalog);
      const rows = [];
      for (const fixture of [
        { id: 'default', query: '', visible: [true, true], counts: [2, 1], total: 3 },
        { id: 'one_music', query: 'music_background', visible: [true, false], counts: [1, 0], total: 1 },
        { id: 'music_group', query: 'music', visible: [true, false], counts: [2, 0], total: 2 },
        { id: 'voice_group', query: 'voice', visible: [false, true], counts: [0, 1], total: 1 },
        { id: 'no_match', query: 'not-a-feature', visible: [false, false], counts: [0, 0], total: 0 },
        { id: 'clear_restores', query: '', visible: [true, true], counts: [2, 1], total: 3 },
        { id: 'case_and_space', query: '  MUSIC_SONG  ', visible: [true, false], counts: [1, 0], total: 1 },
        { id: 'final_reset', query: '', visible: [true, true], counts: [2, 1], total: 3 },
      ]) {
        input.value = fixture.query; filter();
        const groups = Array.from(catalog.querySelectorAll('[data-catalog-group]'));
        const visible = groups.map(group => !group.hidden);
        const counts = groups.map(group => Number(group.querySelector('.portal-feature-count').textContent));
        const total = cards.filter(card => !card.hidden).length;
        rows.push({ id: fixture.id, query: fixture.query, visible, counts, total, feedback: result.textContent,
          pass: JSON.stringify(visible) === JSON.stringify(fixture.visible) && JSON.stringify(counts) === JSON.stringify(fixture.counts) && total === fixture.total && result.textContent === fixture.total + ' matches.' && clear.hidden === !fixture.query.trim() });
      }
      return rows;
    }, block);
    await context.close(); result.failed = result.cases.filter(row => !row.pass).length;
    fs.writeFileSync(path.join(out, 'filter-dom-' + phase + '.json'), JSON.stringify(result, null, 2));
    for (const row of result.cases) console.log('R194_CASE ' + JSON.stringify(row));
    assert.equal(result.failed, 0, 'Visible group counts must match filtered cards');
    console.log('R194_REAL_DOM_FILTER_PASS8');
  } finally { await browser.close(); }
})().catch(error => {
  result.fatal = error.stack;
  fs.writeFileSync(path.join(out, 'filter-dom-' + phase + '.json'), JSON.stringify(result, null, 2));
  console.error(error.stack); process.exitCode = 1;
});
