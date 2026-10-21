const assert = require('node:assert/strict');
const fs = require('node:fs');
const http = require('node:http');
const path = require('node:path');
const { chromium } = require('playwright');

const root = path.resolve(__dirname, '../..');
const checks = [];
const server = http.createServer((req, res) => {
  const url = new URL(req.url, 'http://127.0.0.1');
  const file = { '/portal.css': 'static/portal/portal.css', '/theme.css': 'static/portal/portal-theme.css' }[url.pathname];
  if (file) { res.setHeader('Content-Type', 'text/css'); res.end(fs.readFileSync(path.join(root, file))); return; }
  res.setHeader('Content-Type', 'text/html; charset=utf-8');
  res.end(`<!doctype html><html data-portal-theme="${url.searchParams.get('theme')}"><head><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="stylesheet" href="/portal.css"><link rel="stylesheet" href="/theme.css"></head><body><div class="portal-shell" data-portal-app-kind="${url.searchParams.get('kind')}"><main class="portal-page" style="padding:16px;max-width:100%">
    <header class="portal-hero"><h1>Kiểm tra nhãn trạng thái</h1><span class="portal-badge" data-status="guarded" id="availability">Chưa thể tạo ảnh</span></header>
    <nav class="portal-image-create-workflow-nav"><a href="#form" aria-current="page">Tạo ảnh<span class="portal-badge" data-status="current" id="current">Đang ở trang này</span></a><span class="portal-module-link" id="nav-note">Đang chờ quyền xử lý</span></nav>
    ${['portal-status-badge', 'portal-nav-badge', 'portal-admin-pending-badge', 'portal-capability-hub-badge', 'portal-music-library-read-badge', 'portal-smart-install-badge'].map((name, index) => `<span class="${name}" id="extra-${index}">Nhãn thừa</span>`).join('')}
    <table class="portal-data-table"><thead><tr><th>Trạng thái tác vụ</th></tr></thead><tbody><tr><td><span class="portal-badge" data-status="processing" id="real-status">Đang xử lý</span></td></tr><tr><td><span class="portal-badge" data-status="guarded" id="unknown-status">Chưa xác minh</span></td></tr></tbody></table>
    <p role="alert" id="failure">Không thể tải dữ liệu. Vui lòng thử lại.</p><button type="button" id="retry">Thử lại</button><button id="guarded-action" disabled>Tạo ảnh</button><button class="portal-session-chip" id="account">Tài khoản</button><input aria-label="Mô tả" id="form">
  </main></div></body></html>`);
});

(async () => {
  let browser;
  try {
    await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
    const origin = `http://127.0.0.1:${server.address().port}`;
    browser = await chromium.launch({ channel: process.env.QA_BROWSER_CHANNEL || 'msedge', headless: true });
    for (const kind of ['customer', 'admin']) for (const theme of ['light', 'dark']) for (const width of [375, 1440]) {
      const page = await browser.newPage({ viewport: { width, height: 1000 }, reducedMotion: 'reduce', serviceWorkers: 'block' });
      const errors = []; page.on('pageerror', error => errors.push(String(error)));
      await page.goto(origin + `/?kind=${kind}&theme=${theme}`, { waitUntil: 'networkidle' });
      for (const id of ['availability', 'current', 'nav-note', ...Array.from({ length: 6 }, (_, index) => `extra-${index}`)]) assert.equal(await page.locator('#' + id).isVisible(), false, `${kind}/${theme}/${width}: ${id}`);
      for (const id of ['real-status', 'unknown-status']) {
        const status = page.locator('#' + id); assert.equal(await status.isVisible(), true);
        const style = await status.evaluate(element => { const s = getComputedStyle(element); return { border: s.borderTopWidth, background: s.backgroundColor, radius: s.borderRadius, padding: s.padding }; });
        assert.equal(style.border, '0px'); assert.equal(style.background, 'rgba(0, 0, 0, 0)'); assert.equal(style.radius, '0px'); assert.equal(style.padding, '0px');
      }
      assert.equal(await page.locator('#failure').isVisible(), true); assert.equal(await page.locator('#guarded-action').isDisabled(), true); assert.equal(await page.locator('#account').isVisible(), true);
      await page.locator('#retry').evaluate(element => { element.addEventListener('click', () => { element.dataset.clicked = 'yes'; }); });
      await page.locator('#retry').click(); assert.equal(await page.locator('#retry').getAttribute('data-clicked'), 'yes');
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth - innerWidth), 0); assert.deepEqual(errors, []);
      checks.push({ kind, theme, width, decorativeLabelsHidden: true, recordStatesPlain: true, actionAlertAccountPreserved: true });
      await page.close();
    }
    console.log(JSON.stringify({ result: 'PASS', cases: checks.length, checks, scope: 'Real shared stylesheets; customer/Admin CSS fixture, not RBAC or engine execution.' }));
  } finally { if (browser) await browser.close(); await new Promise(resolve => server.close(resolve)); }
})().catch(error => { console.error(error); process.exitCode = 1; });
