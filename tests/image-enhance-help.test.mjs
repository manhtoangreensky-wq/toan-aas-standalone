import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {test} from 'node:test';
import {fileURLToPath} from 'node:url';
import {pageMetaRenderer} from './helpers/chat-page-meta-runtime.mjs';

// Preparation only: 12 declared tests. No application source is written here.
const R = fileURLToPath(new URL('../', import.meta.url));
const ROUTE = '/image/edit';
const LOCALES = ['vi', 'en', 'zh'];
const KEYS = ['enhance.intro.body', 'enhance.form.description', 'enhance.boundary.description',
  'enhance.step.order.body', 'enhance.step.upscale.body', 'enhance.step.delivery.body'];
const AUTHORITY_PATH = new URL('./fixtures/image-enhance-help-reviewed.json', import.meta.url);
const AUTHORITY_SHA = '8e6babf0753c2a4455b3264cedd3efddef99e11ca9e411621e835e8e9ec03c3a';
const TABLE_SHA = '87fa777c9dff0be8be5df87720b3c3c76c11e73b71eb0d4ba7be60cb87dd8a6f';
const digest = value => createHash('sha256').update(value).digest('hex');
const authorityBytes = fs.readFileSync(AUTHORITY_PATH);
const authority = JSON.parse(authorityBytes.toString('utf8'));
const rows = authority.proposal.changes.map(row => ({
  ...row, oldValues: JSON.parse(row.old.trim().slice(0, -1)),
  newValues: JSON.parse(row.new.trim().slice(0, -1))
}));
const sources = Object.fromEntries(Object.entries({
  portal: 'static/portal/portal.js', i18n: 'static/portal/portal-i18n.js', pages: 'copyfast_pages.py'
}).map(([key, file]) => [key, fs.readFileSync(path.join(R, file), 'utf8')]));
const slotMarker = key => `@@APPROVED_HELP_SLOT:${key}@@`;
const count = (text, needle) => text.split(needle).length - 1;

function tableRange(text) {
  const opening = '  const IMAGE_OPERATION_COPY_ROWS = [';
  const closing = '\n  ];\n';
  assert.equal(count(text, opening), 1, 'One attached image-operation catalogue');
  const start = text.indexOf(opening);
  const tail = text.indexOf(closing, start);
  assert.ok(tail > start, 'The catalogue has its physical closing delimiter');
  return {start, end: tail + closing.length};
}

function scanRows(text) {
  const normalized = text.replace(/\r\n/g, '\n');
  const table = tableRange(normalized);
  const slots = rows.map(row => {
    assert.equal(count(text, JSON.stringify(row.key)), 1, `One occurrence of ${row.key}`);
    const line = text.split(/\r?\n/).find(value => value.includes(JSON.stringify(row.key)));
    assert.ok(line === row.old || line === row.new, `Exact OLD or NEW row required: ${row.key}`);
    const start = text.indexOf(line);
    const normalizedStart = normalized.indexOf(line);
    assert.ok(normalizedStart > table.start && normalizedStart < table.end, `${row.key} stays attached`);
    return {start, end: start + line.length, row, state: line === row.old ? 'old' : 'new'};
  }).sort((left, right) => left.start - right.start);
  assert.deepEqual(slots.map(slot => slot.row.key), KEYS, 'Approved physical row order');
  assert.equal(new Set(slots.map(slot => slot.state)).size, 1, 'No partial OLD/NEW application');
  let cursor = 0;
  let outside = '';
  for (const slot of slots) {
    outside += text.slice(cursor, slot.start) + slotMarker(slot.row.key);
    cursor = slot.end;
  }
  outside += text.slice(cursor);
  return {slots, outside, state: slots[0].state};
}

const initial = scanRows(sources.i18n);
const outsideAnchor = initial.outside;
function exactInverse(text) {
  const scanned = scanRows(text);
  assert.equal(scanned.outside, outsideAnchor, 'Every byte outside the six rows stays unchanged');
  let cursor = 0;
  let oldSource = '';
  for (const slot of scanned.slots) {
    oldSource += text.slice(cursor, slot.start) + slot.row.old;
    cursor = slot.end;
  }
  oldSource += text.slice(cursor);
  assert.equal(scanRows(oldSource).outside, outsideAnchor, 'Inverse preserves outside bytes');
  return oldSource;
}

// Synthetic NEW is used only to test inverse rejection/acceptance, NEVER to render acceptance.
const oldSource = exactInverse(sources.i18n);
const newInverseFixture = rows.reduce((text, row) => text.replace(row.old, row.new), oldSource);
let candidatePromise;
let referencePromise;
const candidate = () => candidatePromise ??= pageMetaRenderer(sources);
const reference = () => referencePromise ??= pageMetaRenderer({...sources, i18n: oldSource});
const escaped = value => String(value).replace(/&/g, '&amp;').replace(/</g, '&lt;')
  .replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
const values = (locale, state) => rows.map(row => row[`${state}Values`][LOCALES.indexOf(locale) + 1]);

const HELP_PATTERNS = [
  /(<section class="portal-document-operation-intro"><div>[\s\S]*?<p>)([^<]*)(<\/p>)/g,
  /(<section class="portal-card portal-card-pad portal-document-operation-form"><div class="portal-card-header"><div><h2 class="portal-card-title">[^<]*<\/h2><p class="portal-card-subtitle">)([^<]*)(<\/p>)/g,
  /(<aside class="portal-card portal-card-pad portal-document-operation-boundary"><div class="portal-card-header"><div><h2 class="portal-card-title">[^<]*<\/h2><p class="portal-card-subtitle">)([^<]*)(<\/p>)/g
];
function helpSlots(html, hasHelp = true) {
  const found = HELP_PATTERNS.map(pattern => [...html.matchAll(pattern)]);
  const lists = [...html.matchAll(/(<ol class="portal-project-steps">)([\s\S]*?)(<\/ol>)/g)];
  if (!hasHelp) {
    assert.deepEqual(found.map(matches => matches.length), [0, 0, 0]);
    assert.equal(lists.length, 0);
    return [];
  }
  assert.deepEqual(found.map(matches => matches.length), [1, 1, 1], 'Exactly three fixed paragraphs');
  assert.equal(lists.length, 1, 'One three-step help list');
  const steps = [...lists[0][2].matchAll(/(<li><strong>[^<]*<\/strong><span>)([^<]*)(<\/span><\/li>)/g)];
  assert.equal(steps.length, 3, 'Exactly three fixed step bodies');
  return [...found.map(matches => matches[0][2]), ...steps.map(match => match[2])];
}

function maskSix(html, locale, state, hasHelp = true) {
  const bodies = helpSlots(html, hasHelp);
  if (!hasHelp) return html;
  assert.deepEqual(bodies, values(locale, state).map(escaped), 'Only exact approved bodies can be masked');
  let masked = html;
  HELP_PATTERNS.forEach((pattern, index) => {
    masked = masked.replace(pattern, (_all, prefix, _body, suffix) => prefix + slotMarker(KEYS[index]) + suffix);
  });
  masked = masked.replace(/(<ol class="portal-project-steps">)([\s\S]*?)(<\/ol>)/g,
    (_all, prefix, body, suffix) => {
      let index = 3;
      const result = body.replace(/(<li><strong>[^<]*<\/strong><span>)([^<]*)(<\/span><\/li>)/g,
        (_step, before, _copy, after) => before + slotMarker(KEYS[index++]) + after);
      assert.equal(index, 6);
      return prefix + result + suffix;
    });
  return masked;
}

const IDS = {
  image: '11111111-1111-4111-8111-111111111111', pinned: '22222222-2222-4222-8222-222222222222',
  invalid: '33333333-3333-4333-8333-333333333333', done: '44444444-4444-4444-8444-444444444444',
  failed: '55555555-5555-4555-8555-555555555555', unknown: '66666666-6666-4666-8666-666666666666',
  decoy: '77777777-7777-4777-8777-777777777777'
};
const CUSTOMER = 'CUSTOMER_IMAGE_<>&" Asset Vault 缓存 băm';
const UNKNOWN = 'qa_unknown_preset_<>&"';
const STATES = ['ready', 'empty', 'read-only', 'disabled', 'loading', 'failed', 'guarded', 'unknown-read'];
function fixture(state = 'ready') {
  const image = {id: IDS.image, display_name: CUSTOMER, original_filename: 'customer-original.png',
    extension: '.png', content_type: 'image/png', state: 'active', byte_size: 2048, updated_at: '2026-11-18T01:02:03Z'};
  const listing = {filters: {q: 'CUSTOMER_FILTER'}, pagination: {
    limit: 50, offset: 50, returned: 2, has_more: true, next_offset: 100, previous_offset: 0}};
  const raw = {
    capabilities: {'image-operation-view': true, 'image-operation-enhance': true, 'image-enhance-refresh': true,
      'image-operation-export-to-asset-vault': true, 'content-handoff-create': true},
    assetVaultReadState: 'ready', assetVaultEnabled: true, imageEnhanceEnabled: true,
    imageEnhanceOperationsReadState: 'ready', imageOperationAssetReferenceReadState: 'ready',
    imageOperationAssetReferences: {items: [image, {...image, id: IDS.invalid, extension: '.pdf', content_type: 'application/pdf'}],
      pinned: [{...image, id: IDS.pinned, display_name: 'CUSTOMER_PINNED', extension: '.webp', content_type: 'image/webp'}], listing},
    vaultItems: [{...image, id: IDS.decoy, display_name: 'DECOY_NOT_TYPED'}],
    imageEnhanceOperationListing: {filters: {kind: 'image_enhance'}, pagination: {
      offset: 50, returned: 3, has_more: true, next_offset: 100}},
    imageEnhanceOperations: [
      {id: IDS.done, kind: 'image_enhance', state: 'completed', download_ready: true,
        original_filename: CUSTOMER, preset: 'custom', source_width: 800, source_height: 600,
        target_width: 1600, target_height: 1200, completed_at: '2026-11-18T01:02:03Z',
        settings: {brightness: 1.11, contrast: 1.22, saturation: 1.33, sharpness: 1.44, tone: 'warm', basic_upscale: true}},
      {id: IDS.failed, kind: 'image_enhance', state: 'failed', download_ready: false,
        original_filename: 'CUSTOMER_FAILED.png', preset: UNKNOWN},
      {id: IDS.unknown, kind: 'image_enhance', state: 'qa_unknown_state', download_ready: true,
        original_filename: 'CUSTOMER_UNKNOWN.png', preset: UNKNOWN},
      {id: IDS.decoy, kind: 'image_resize', state: 'completed', download_ready: true,
        original_filename: 'DECOY_WRONG_KIND.png'}
    ]
  };
  if (state === 'empty') {
    raw.imageOperationAssetReferences = {items: [], pinned: [], listing: {}};
    raw.imageEnhanceOperations = [];
    raw.imageEnhanceOperationListing = {};
  }
  if (state === 'read-only' || state === 'disabled') {
    for (const key of Object.keys(raw.capabilities)) raw.capabilities[key] = key === 'image-operation-view';
  }
  if (state === 'disabled') raw.imageEnhanceEnabled = false;
  if (state === 'loading') raw.assetVaultReadState = 'loading';
  if (state === 'failed') raw.assetVaultReadState = 'failed';
  if (state === 'guarded') raw.capabilities['image-operation-view'] = false;
  if (state === 'unknown-read') raw.assetVaultReadState = 'qa_unknown_read';
  return raw;
}
const hasHelp = state => ['ready', 'empty', 'read-only', 'disabled'].includes(state);
const formHtml = html => {
  const matches = [...html.matchAll(/<form\b[^>]*data-portal-action="image-operation-enhance"[\s\S]*?<\/form>/g)];
  assert.equal(matches.length, 1);
  return matches[0][0];
};
const selectHtml = (html, name) => {
  const matches = [...html.matchAll(new RegExp(`<select\\b[^>]*name="${name}"[^>]*>[\\s\\S]*?<\\/select>`, 'g'))];
  assert.equal(matches.length, 1, `One ${name} selector`);
  return matches[0][0];
};
const options = html => [...html.matchAll(/<option value="([^"]*)"/g)].map(match => match[1]);

test('01 canonical six-row authority and protected Enhance consumers remain unchanged', () => {
  assert.equal(digest(authorityBytes), AUTHORITY_SHA);
  assert.equal(authority.review.specId, 'IMAGE-ENHANCE-STATIC-HELP-20261118-R1A');
  assert.equal(authority.review.conversation, 'cfda048e-035d-46cd-84ba-0639584c949c');
  assert.equal(authority.review.schemaValid, true);
  assert.equal(authority.review.proposalExact, true);
  assert.equal(authority.review.changes, 6);
  assert.deepEqual(rows.map(row => row.key), KEYS);
  for (const row of rows) {
    assert.equal(row.file, 'static/portal/portal-i18n.js');
    assert.equal(row.site, 'locale-row');
    assert.equal(row.count, 1);
    for (const cells of [row.oldValues, row.newValues]) {
      assert.equal(cells.length, 4);
      assert.equal(cells[0], row.key);
      assert.ok(cells.every(value => typeof value === 'string' && value.length > 0));
    }
  }
  const tableSource = initial.outside.replace(/\r\n/g, '\n');
  const range = tableRange(tableSource);
  assert.equal(digest(tableSource.slice(range.start, range.end)), TABLE_SHA, 'No extra catalogue keys or mutations');
  const portal = sources.portal.replace(/\r\n/g, '\n');
  for (const [opening, closing, expected] of [
    ['  function renderImageEnhance(page, context) {', '  function renderImageUpscale(page, context) {',
      '6fe425406eaa2b1af86b38f31ee6c25b6d860f9ba04a90615ceac5a3386a6de8'],
    ['  function imageEnhanceFormFields(values) {', '  function imageBackgroundCleanupFormFields() {',
      'b7b302d7f07fa9786c815ae92572d3cfbb5a3e19250e6155c05d9e66837340ec'],
    ['  function renderImageEnhanceOperationCards(items) {', '  function imageBrandOverlaySettings(item) {',
      '2dda3f2f81da8b48a66fab4fe461a23cbb60c118e24f34195c791fbc81551081']
  ]) {
    assert.equal(count(portal, opening), 1);
    const start = portal.indexOf(opening);
    const end = portal.indexOf(closing, start);
    assert.ok(end > start);
    assert.equal(digest(portal.slice(start, end)), expected, opening);
  }
});

async function assertActualNew(locale) {
  const output = (await candidate())(locale, ROUTE, fixture());
  assert.equal(output.route, ROUTE);
  assert.deepEqual(helpSlots(output.html), values(locale, 'new').map(escaped),
    `${locale}: actual physical /image/edit consumer must show all six approved NEW values`);
}
test('02 VI actual Enhance consumer shows six exact approved NEW values', () => assertActualNew('vi'));
test('03 EN actual Enhance consumer shows six exact approved NEW values', () => assertActualNew('en'));
test('04 ZH actual Enhance consumer shows six exact approved NEW values', () => assertActualNew('zh'));

test('05 fixed paragraphs retain honest controls, PNG, ordered processing and enlargement limits', async () => {
  const semantics = {
    vi: {four: /bốn thông số/u, order: ['tự cân bằng', 'độ sáng', 'độ tương phản', 'độ bão hòa', 'độ nét', 'sắc độ'],
      limits: [/tối đa 2 lần/u, /4096 điểm ảnh mỗi cạnh/u, /16 triệu điểm ảnh/u, /không tạo thêm chi tiết/u]},
    en: {four: /four controls/u, order: ['auto-balanced', 'brightness', 'contrast', 'saturation', 'sharpness', 'tone'],
      limits: [/up to 2 times/u, /4096 pixels per side/u, /16 million pixels in total/u, /does not add detail/u]},
    zh: {four: /四项参数/u, order: ['自动平衡', '亮度', '对比度', '饱和度', '锐度', '色调'],
      limits: [/最多可放大 2 倍/u, /每边不超过 4096 像素/u, /总计不超过 1600 万像素/u, /不会增加细节/u]}
  };
  const forbidden = /Asset Vault|LANCZOS|UnsharpMask|rehash|repars|authenticat|\bCSRF\b|\bPWA\b|\bcach(?:e|ing)\b|băm|xác thực|bộ nhớ đệm|哈希|验证会话|认证|缓存|内插|插值|算法|thuật toán|algorithm|local processing|cục bộ|本地|asset ID|mã tài sản|资产编号|\bserver\b|máy chủ|服务器/iu;
  for (const locale of LOCALES) {
    const body = helpSlots((await candidate())(locale, ROUTE, fixture()).html);
    for (const paragraph of body) assert.doesNotMatch(paragraph, forbidden, `${locale}: fixed help only`);
    assert.match(body[0], semantics[locale].four);
    assert.match(body[2], /PNG/u);
    assert.match(body[5], /PNG/u);
    const order = body[3].toLowerCase();
    let position = -1;
    for (const word of semantics[locale].order) {
      const next = order.indexOf(word, position + 1);
      assert.ok(next > position, `${locale}: processing order ${word}`);
      position = next;
    }
    for (const limit of semantics[locale].limits) assert.match(body[4], limit);
  }
});

test('06 actual versus exact inverse preserves whole HTML outside six bodies and entire context', async () => {
  const render = await candidate();
  const renderOld = await reference();
  for (const locale of LOCALES) for (const state of STATES) {
    const raw = fixture(state);
    const before = JSON.stringify(raw);
    const actual = render(locale, ROUTE, raw);
    const original = renderOld(locale, ROUTE, raw);
    assert.equal(maskSix(actual.html, locale, initial.state, hasHelp(state)),
      maskSix(original.html, locale, 'old', hasHelp(state)), `${locale}/${state}: full protected HTML`);
    assert.equal(JSON.stringify(actual.context), JSON.stringify(original.context), `${locale}/${state}: entire normalized context`);
    assert.equal(JSON.stringify(raw), before, `${locale}/${state}: raw customer data stays byte-identical`);
    assert.equal(actual.attributes, original.attributes, 'All confirmations and accessibility attributes');
    assert.equal(actual.title, original.title, 'Document title');
    assert.equal(JSON.stringify(actual.page), JSON.stringify(original.page), 'Entire resolved page metadata');
    for (const lang of LOCALES) {
      const actualMessages = {...actual.messages[lang]};
      const oldMessages = {...original.messages[lang]};
      for (const key of KEYS) {
        delete actualMessages[`imageOperationUi.${key}`];
        delete oldMessages[`imageOperationUi.${key}`];
      }
      assert.deepEqual(actualMessages, oldMessages, `${lang}: all unapproved catalogue messages`);
    }
  }
});

test('07 ready form retains typed sources, exact controls, actions and genuine download paths', async () => {
  for (const locale of LOCALES) {
    const output = (await candidate())(locale, ROUTE, fixture());
    const form = formHtml(output.html);
    assert.match(form, /data-portal-route="\/image\/edit"/);
    assert.match(form, /data-portal-confirm="[^"]+"/);
    assert.doesNotMatch(form.match(/<button\b[^>]*type="submit"[^>]*>/)[0], /\bdisabled\b/);
    assert.deepEqual(options(selectHtml(form, 'source_asset_id')), ['', IDS.pinned, IDS.image]);
    assert.match(form, new RegExp(escaped(CUSTOMER).replace(/[.*+?^${}()|[\]\\]/g, '\\$&')));
    assert.doesNotMatch(output.html, /DECOY_NOT_TYPED|DECOY_WRONG_KIND/);
    const numeric = [...form.matchAll(/<input\b[^>]*name="(brightness|contrast|saturation|sharpness)"[^>]*>/g)];
    assert.deepEqual(numeric.map(match => match[1]), ['brightness', 'contrast', 'saturation', 'sharpness']);
    for (const [tag] of numeric) {
      for (const property of ['type="number"', 'min="0.5"', 'max="2"', 'step="0.01"', ' disabled']) assert.ok(tag.includes(property));
    }
    assert.deepEqual(options(selectHtml(form, 'preset')), ['photo_clear_detail', 'product_clean', 'cinematic_warm', 'fresh_blue', 'food_vivid', 'custom']);
    assert.deepEqual(options(selectHtml(form, 'tone')), ['neutral', 'warm', 'cool', 'clean']);
    assert.deepEqual(options(selectHtml(form, 'basic_upscale')), ['false', 'true']);
    for (const action of ['image-enhance-refresh', 'image-operation-asset-reference-filter',
      'image-operation-export-to-asset-vault', 'image-operation-export-to-continue', 'image-operation-export-to-content-handoff']) {
      assert.ok(output.html.includes(`data-portal-action="${action}"`), action);
    }
    assert.ok(output.html.includes(`/api/v1/image-operations/${IDS.done}/download`));
    assert.ok(!output.html.includes(`/api/v1/image-operations/${IDS.failed}/download`));
    assert.ok(!output.html.includes(`/api/v1/image-operations/${IDS.unknown}/download`));
    assert.ok(output.html.includes(escaped(UNKNOWN)), 'Unknown customer preset remains literal');
  }
});

test('08 finite inverse accepts all-OLD and all-NEW only and preserves every outside byte', () => {
  assert.equal(scanRows(oldSource).state, 'old');
  assert.equal(scanRows(newInverseFixture).state, 'new');
  assert.equal(exactInverse(oldSource), oldSource, 'OLD is idempotent');
  assert.equal(exactInverse(newInverseFixture), oldSource, 'Exact NEW maps back to exact OLD');
  assert.deepEqual(Buffer.from(scanRows(newInverseFixture).outside), Buffer.from(scanRows(oldSource).outside));
  assert.equal(exactInverse(exactInverse(sources.i18n)), oldSource);
});

test('09 finite inverse rejects changed, missing and partially applied approved rows', () => {
  for (const row of rows) {
    assert.throws(() => exactInverse(oldSource.replace(row.old, row.new)), /partial OLD\/NEW/);
    assert.throws(() => exactInverse(newInverseFixture.replace(row.new, row.old)), /partial OLD\/NEW/);
    assert.throws(() => exactInverse(oldSource.replace(row.old, '')), /One occurrence/);
    assert.throws(() => exactInverse(newInverseFixture.replace(row.new, row.new.replace('],', ' ,"UNAPPROVED"],'))), /Exact OLD or NEW/);
  }
});

test('10 finite inverse rejects duplicate, detached, reordered and unknown outside mutations', () => {
  const [first, second] = rows;
  assert.throws(() => exactInverse(oldSource + '\n' + first.old + '\n'), /One occurrence/);
  assert.throws(() => exactInverse(oldSource.replace(first.old, '') + '\n' + first.old + '\n'), /stays attached/);
  const swapped = oldSource.replace(first.old, '@@TEMP@@').replace(second.old, first.old).replace('@@TEMP@@', second.old);
  assert.throws(() => exactInverse(swapped), /physical row order/);
  assert.throws(() => exactInverse(oldSource + '\n// UNKNOWN_OUTSIDE_MUTATION\n'), /outside the six rows/);
  assert.throws(() => exactInverse(oldSource.replace('TOAN AAS Portal i18n foundation', 'UNKNOWN_MUTATED_CATALOGUE')), /outside the six rows/);
});

test('11 six scoped masks never erase identical customer copy or unknown literal data elsewhere', async () => {
  for (const locale of LOCALES) {
    const raw = fixture();
    const customerCopy = values(locale, 'new')[0];
    raw.imageEnhanceOperations[0].original_filename = customerCopy;
    const output = (await candidate())(locale, ROUTE, raw);
    const masked = maskSix(output.html, locale, initial.state);
    assert.ok(masked.includes(`<h2 class="portal-card-title">${escaped(customerCopy)}</h2>`), 'Customer title is not a help paragraph');
    assert.ok(masked.includes(escaped(UNKNOWN)), 'Unknown preset is never projected or translated');
    assert.ok(masked.includes(escaped(CUSTOMER)), 'Typed source customer label remains untouched');
    for (const key of KEYS) assert.equal(count(masked, slotMarker(key)), 1, 'Exactly one scoped mask per approved body');
    assert.throws(() => maskSix(output.html.replace(helpSlots(output.html)[1], 'UNKNOWN_HELP_MUTATION'), locale, initial.state),
      /Only exact approved bodies/);
  }
});

test('12 guarded, loading, failed, unknown-read, empty and read-only consumers remain fail-closed', async () => {
  for (const locale of LOCALES) {
    for (const state of ['guarded', 'loading', 'failed', 'unknown-read']) {
      const output = (await candidate())(locale, ROUTE, fixture(state));
      helpSlots(output.html, false);
      assert.doesNotMatch(output.html, /<form\b|data-image-operation=|\/api\/v1\/image-operations\/[^"]+\/download/);
      assert.match(output.html, state === 'loading' ? /data-state="processing"/ : /data-state="guarded"/);
    }
    for (const state of ['empty', 'read-only', 'disabled']) {
      const output = (await candidate())(locale, ROUTE, fixture(state));
      assert.match(formHtml(output.html), /<button\b[^>]*type="submit"[^>]* disabled>/);
      assert.equal(output.context.capabilities['image-operation-enhance'], state === 'empty');
    }
  }
});
