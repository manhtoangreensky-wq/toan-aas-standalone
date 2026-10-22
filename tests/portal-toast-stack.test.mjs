import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

const sources = [
  ['portal', 'static/portal/portal.js', 'showToast'],
  ['integration', 'static/portal/integration.js', 'toast'],
  ['auth', 'static/portal/portal-auth.js', 'toast'],
];

function extract(source, name) {
  const start = source.indexOf(`function ${name}(`);
  assert.ok(start >= 0, `${name} must exist`);
  const end = source.indexOf('\n  }\n', start);
  assert.ok(end > start, `${name} body must be bounded`);
  return source.slice(start, end + 5);
}

class FakeNode {
  constructor(region) {
    this.region = region;
    this.attributes = new Map();
    this.className = '';
    this.textContent = '';
  }

  setAttribute(name, value) { this.attributes.set(name, String(value)); }
  getAttribute(name) { return this.attributes.get(name) ?? null; }
  remove() {
    const index = this.region.nodes.indexOf(this);
    if (index >= 0) this.region.nodes.splice(index, 1);
  }
}

function runtime(file, name) {
  const source = fs.readFileSync(file, 'utf8').replace(/\r\n/g, '\n');
  const region = {
    nodes: [],
    appendChild(node) { this.nodes.push(node); },
    querySelectorAll(selector) { return selector === '.portal-toast' ? [...this.nodes] : []; },
  };
  const document = {
    querySelector(selector) { return selector === '[data-portal-toast]' ? region : null; },
    createElement() { return new FakeNode(region); },
  };
  const timers = [];
  const context = {
    document,
    window: { setTimeout(callback) { timers.push(callback); return timers.length; } },
  };
  vm.createContext(context);
  vm.runInContext(extract(source, name), context, { filename: file });
  return { fn: context[name], region };
}

for (const [label, file, name] of sources) {
  test(`${label} toast keeps at most two visible messages and collapses duplicates`, () => {
    const { fn, region } = runtime(file, name);
    fn('Lỗi kết nối', label === 'portal' ? 'warning' : 'error');
    fn('Lỗi kết nối', label === 'portal' ? 'warning' : 'error');
    fn('Đã lưu', 'info');
    fn('Đã thử lại', 'info');

    assert.equal(region.nodes.length, 2);
    assert.deepEqual(region.nodes.map(node => node.textContent), ['Đã lưu', 'Đã thử lại']);
    assert.equal(region.nodes[0].getAttribute('role'), 'status');
  });
}
