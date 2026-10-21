import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const source = fs.readFileSync('static/portal/portal.js', 'utf8');
function production(name) {
  const a = source.indexOf(`  function ${name}(`), b = source.indexOf('\n  }', a) + 4;
  assert.ok(a >= 0 && b > a, `Missing production function ${name}`);
  return source.slice(a, b);
}
function harness() {
  const canonical = value => ({ '/tts': '/voice/tts', '/voice/create': '/voice/tts', '/voice/vault': '/voice/saved', '/voice/asr': '/voice/stt' })[value] || value;
  const moves = [], events = [], inputs = [{ name: 'script', type: 'textarea', value: 'Nội dung QA 😀' }, { name: 'volume_percent', type: 'number', value: '0' }, { name: 'sample', type: 'file', value: 'must not be retained' }];
  let state = { path: '/voice/tts', session: { authenticated: true, csrfToken: 'qa-session-a' } };
  const form = { hasAttribute: () => false, getAttribute: key => key === 'data-portal-route' ? canonical(state.path) : '', querySelectorAll: () => inputs };
  const context = vm.createContext({
    URL, normalizePath: value => String(value || '').split('?')[0].replace(/\/$/, ''),
    getBootstrap: () => state,
    resolvePage: value => ({ path: canonical(value) }),
    mountPortal: next => { state = next; },
    document: { querySelector: selector => selector.includes('[data-portal-form]') ? form : { focus() {} } },
    CustomEvent: class { constructor(type) { this.type = type; } },
    window: {
      __TOAN_AAS_PORTAL__: state,
      location: { origin: 'http://127.0.0.1', href: 'http://127.0.0.1/voice/tts?lang=vi', pathname: '/voice/tts', search: '?lang=vi' },
      history: { pushState: (_data, _title, url) => moves.push(url) },
      dispatchEvent: event => events.push(event.type)
    }
  });
  vm.runInContext('const transientFormDrafts=new Map(); const transientWorkspaceDraftIds=new Map(); let voiceWorkspaceDraftSession="qa-session-a";', context);
  vm.runInContext(['rememberTransientFormDraft', 'transientFormValues', 'clearTransientFormDraft', 'synchronizeVoiceWorkspaceDraftSession', 'navigateVoiceWorkspace'].map(production).join('\n'), context);
  const event = { button: 0, defaultPrevented: false, preventDefault() { this.defaultPrevented = true; } };
  const link = { getAttribute: key => key === 'href' ? '/voice/saved' : null, hasAttribute: () => false };
  return { context, moves, events, event, link, state: () => state };
}

test('Voice mode navigation retains scalar draft and does not copy file inputs', () => {
  const h = harness();
  assert.equal(h.context.navigateVoiceWorkspace(h.event, h.link), true);
  assert.equal(h.event.defaultPrevented, true);
  assert.equal(h.moves[0], '/voice/saved?lang=vi');
  assert.equal(h.state().path, '/voice/saved');
  assert.equal(h.context.transientFormValues('/voice/tts').script, 'Nội dung QA 😀');
  assert.equal(h.context.transientFormValues('/voice/tts').volume_percent, '0');
  assert.equal(h.context.transientFormValues('/voice/tts').sample, undefined);
  assert.deepEqual(h.events, ['toanaas:voice-workspace-navigation']);
});

test('Modified clicks retain normal browser link behavior', () => {
  for (const modifier of ['ctrlKey', 'metaKey', 'shiftKey', 'altKey']) {
    const h = harness(); h.event[modifier] = true;
    assert.equal(h.context.navigateVoiceWorkspace(h.event, h.link), false);
    assert.equal(h.event.defaultPrevented, false); assert.equal(h.moves.length, 0);
  }
});

test('Existing Voice aliases retain their canonical draft when switching modes', () => {
  for (const alias of ['/tts', '/voice/create', '/voice/vault', '/voice/asr']) {
    const h = harness(); h.state().path = alias;
    h.link.getAttribute = key => key === 'href' ? '/voice/clone' : null;
    assert.equal(h.context.navigateVoiceWorkspace(h.event, h.link), true, alias);
    assert.equal(h.moves[0], '/voice/clone?lang=vi');
    const canonical = h.context.resolvePage(alias).path;
    assert.equal(h.context.transientFormValues(canonical).script, 'Nội dung QA 😀');
  }
});

test('Activating the current Voice mode does not add duplicate history entries', () => {
  const h = harness();
  h.link.getAttribute = key => key === 'href' ? '/voice/tts' : null;
  assert.equal(h.context.navigateVoiceWorkspace(h.event, h.link), true);
  assert.equal(h.event.defaultPrevented, true);
  assert.equal(h.moves.length, 0);
});

test('Unknown, external or unsigned navigation cannot enter the Voice workspace handler', () => {
  for (const href of ['/admin', '/voice/outputs', 'https://example.com/voice/saved', '/voice/saved?profile_id=999']) {
    const h = harness(); h.link.getAttribute = key => key === 'href' ? href : null;
    assert.equal(h.context.navigateVoiceWorkspace(h.event, h.link), false);
    assert.equal(h.moves.length, 0);
  }
  const h = harness(); h.state().session.authenticated = false;
  assert.equal(h.context.navigateVoiceWorkspace(h.event, h.link), false);
  assert.equal(h.moves.length, 0);
});

test('Voice drafts survive same-session rendering and clear on session replacement', () => {
  const h = harness();
  h.context.navigateVoiceWorkspace(h.event, h.link);
  h.context.synchronizeVoiceWorkspaceDraftSession(h.state());
  assert.equal(h.context.transientFormValues('/voice/tts').script, 'Nội dung QA 😀');
  h.context.synchronizeVoiceWorkspaceDraftSession({ session: { authenticated: true, csrfToken: 'qa-session-b' } });
  assert.equal(Object.keys(h.context.transientFormValues('/voice/tts')).length, 0);
});

test('Signing out or losing a known session clears only Voice drafts', () => {
  for (const session of [{ authenticated: false }, { authenticated: true }]) {
    const h = harness(); h.context.navigateVoiceWorkspace(h.event, h.link);
    vm.runInContext('transientFormDrafts.set("/projects",{title:"Keep unrelated work"})', h.context);
    h.context.synchronizeVoiceWorkspaceDraftSession({ session });
    assert.equal(Object.keys(h.context.transientFormValues('/voice/tts')).length, 0);
    assert.equal(h.context.transientFormValues('/projects').title, 'Keep unrelated work');
  }
});
