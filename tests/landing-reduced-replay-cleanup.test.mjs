import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const source = fs.readFileSync('static/portal/portal-motion.js', 'utf8');
const helperStart = source.indexOf('  function setReplayAvailability(');
const helperEnd = source.indexOf('  function clearMotion(', helperStart);
const cleanupStart = source.indexOf('    const clearLandingDecorations = () => {');
const cleanupEnd = source.indexOf('    // The aperture remains', cleanupStart);
assert.ok(helperStart > 0 && helperEnd > helperStart && cleanupStart > 0 && cleanupEnd > cleanupStart);

function cleanup(reduced) {
  const attributes = new Map();
  const replayControl = { hidden: false, disabled: false,
    setAttribute: (key, value) => attributes.set(key, value),
    removeAttribute: key => attributes.delete(key),
  };
  const runtime = vm.createContext({
    window: { matchMedia: () => ({ matches: reduced }) },
    REDUCED_MOTION_QUERY: '(prefers-reduced-motion: reduce)',
    root: { removeAttribute() {}, classList: { remove() {} } },
    documentElement: null, header: null, hero: null, preview: null,
    previewSteps: [], heroStages: [], revealDetails: [], scrollLayers: [],
    pointerHandlers: [], landingCtas: [], replayControl,
    removeStyleProperty() {},
  });
  vm.runInContext(source.slice(helperStart, helperEnd) + source.slice(cleanupStart, cleanupEnd) + '\nclearLandingDecorations();', runtime);
  return { replayControl, attributes };
}

test('Reduced-motion cleanup hides and disables replay after its listeners have been detached', () => {
  const result = cleanup(true);
  assert.equal(result.replayControl.hidden, true);
  assert.equal(result.replayControl.disabled, true);
  assert.equal(result.attributes.get('aria-hidden'), 'true');
  assert.equal(result.attributes.get('data-landing-motion-replay-disabled'), 'true');
});

test('Normal-motion cleanup preserves the existing replay availability contract', () => {
  const result = cleanup(false);
  assert.equal(result.replayControl.hidden, false);
  assert.equal(result.replayControl.disabled, false);
  assert.equal(result.attributes.has('aria-hidden'), false);
});
