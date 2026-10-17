import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const source = fs.readFileSync('static/portal/portal-features.js', 'utf8');
const copySource = fs.readFileSync('static/portal/portal-feature-catalog-copy.js', 'utf8');
const registry = fs.readFileSync('copyfast_registry.py', 'utf8');

// A minimal tree records the real renderer's labels and attributes.
class Element {
  constructor(tag) { this.tagName = tag.toUpperCase(); this.className = ''; this.textContent = ''; this.children = []; this.attributes = {}; }
  setAttribute(name, value) { this.attributes[name] = String(value); }
  appendChild(child) { this.children.push(child); return child; }
}
const document = { createElement: tag => new Element(tag) };
const window = {};
const sandbox = vm.createContext({ window, document, console, Set, Object, Array });
vm.runInContext(copySource, sandbox);
vm.runInContext(source.replace('window.__TOAN_AAS_FEATURES_READY__ = hydrateFeatures();',
  'window.__catalogTest = { featureCard, classifyCatalogBoundary, COPY };'), sandbox);
const { featureCard, classifyCatalogBoundary, COPY } = window.__catalogTest;
const entries = [
  ['interface_locale_navigator', '/account/interface-language'],
  ['account_security', '/account/security'],
  ['workspace_care', '/account/workspace-care']
];
const collect = node => [node, ...node.children.flatMap(collect)];
function feature(key, route, engine = 'guarded', readiness = 'guarded') {
  const row = registry.split('\n').find(line => line.includes(`WebFeature("${key}",`));
  assert.ok(row, `Current registry must contain ${key}`);
  const fields = row.match(/WebFeature\("[^"]+",\s*"([^"]+)",\s*"([^"]+)",\s*"([^"]+)"/);
  assert.equal(fields[3], route);
  return { key, route, title: fields[1], group: fields[2], description: '',
    engine: { mode: engine, execution_state: engine === 'guarded' ? 'guarded' : 'ready' },
    readiness: { status: readiness } };
}

for (const [locale, expected] of [['vi', 'Quản lý tài khoản'], ['en', 'Account settings'], ['zh', '账户设置']]) {
  test(`account cards describe settings rather than AI generation or planning in ${locale}`, () => {
    for (const [key, route] of entries) for (const [engine, readiness] of [['guarded', 'guarded'], ['web_native', 'available']]) {
      const input = feature(key, route, engine, readiness), before = JSON.stringify(input);
      const card = featureCard(input, COPY[locale], locale), nodes = collect(card);
      const label = nodes.find(n => n.className === 'portal-boundary-label');
      assert.equal(label.textContent, expected, `${key} / ${engine}`);
      assert.equal(label.attributes['data-boundary'], 'account_management');
      assert.equal(nodes.find(n => n.className === 'portal-engine-label').attributes['data-engine-mode'], engine);
      assert.equal(nodes.find(n => n.className === 'portal-readiness-label').attributes['data-readiness'], readiness);
      assert.equal(nodes.find(n => n.tagName === 'A').attributes.href, route);
      assert.equal(nodes.find(n => n.tagName === 'H3').textContent, window.TOANAASFeatureCatalogCopy[locale][key].title);
      assert.equal(JSON.stringify(input), before);
    }
  });
}

test('unrelated media and workspace cards keep their existing classification', () => {
  for (const [key, route, mode, readiness, want] of [
    ['video_single', '/video/create', 'guarded', 'guarded', 'canonical_bridge'],
    ['music_song', '/music/song', 'guarded', 'guarded', 'runtime_generator'],
    ['prompt_library', '/prompt-library', 'web_native', 'available', 'web_planning'],
    ['image_create', '/image/create', 'guarded', 'guarded', 'runtime_generator']
  ]) assert.equal(classifyCatalogBoundary(feature(key, route, mode, readiness)), want);
  assert.equal(classifyCatalogBoundary({ key: 'account_security', route: '/music/song', engine: { mode: 'guarded' } }), 'runtime_generator');
  assert.equal(classifyCatalogBoundary({ key: 'unregistered_account_tool', route: '/account/security', engine: { mode: 'guarded' } }), 'runtime_generator');
});
