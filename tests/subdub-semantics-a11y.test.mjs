import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

const source = readFileSync('static/portal/portal.js', 'utf8');
const start = source.indexOf('  const SUBDUB_PRODUCT_MODES');
const end = source.indexOf('\n  function renderDocumentHub', start);
const block = source.slice(start, end);
const companionStart = source.indexOf('  function subDubVoiceCompanionUrl(');
const companion = source.slice(companionStart, source.indexOf('\n  }', companionStart) + 4);
const escape = value => String(value ?? '').replaceAll('&', '&amp;').replaceAll('<', '&lt;')
  .replaceAll('>', '&gt;').replaceAll('"', '&quot;').replaceAll("'", '&#39;');

function render(mode, locale = 'vi') {
  const window = { location: { search: `?mode=${mode}&lang=${locale}` } };
  return new Function('window', 'interfaceLocaleFor', 'safeText', 'badge', 'renderHero', 'transientFormDrafts', 'locale',
    companion + '\n' + block + '\nreturn renderSubDubHub({}, { locale });')(
    window, context => context.locale, escape, () => '', () => '', new Map(), locale
  );
}

test('SubDub Stage 3 exposes a live semantic region with a labelled heading', () => {
  for (const locale of ['vi', 'en', 'zh']) {
    const html = render('subtitle_plus_dubbing', locale);
    assert.match(html, /<h3[^>]*id="subdub-settings-title-[^"]+"/);
    assert.match(html, /data-subdub-settings-rows[^>]*role="region"/);
    assert.match(html, /data-subdub-settings-rows[^>]*aria-live="polite"/);
    assert.match(html, /data-subdub-settings-rows[^>]*aria-atomic="true"/);
    const titleId = html.match(/<h3[^>]*id="(subdub-settings-title-[^"]+)"/)?.[1];
    assert.match(html, new RegExp(`data-subdub-settings-rows[^>]*aria-labelledby="${titleId}"`));
  }
});

test('SubDub volume output is announced and every number/range error reference exists', () => {
  const html = render('dubbing_only', 'vi');
  for (const kind of ['original', 'dubbing']) {
    const output = html.match(new RegExp(`<output[^>]*data-subdub-volume-output="${kind}"[^>]*>`))?.[0] || '';
    assert.match(output, /role="status"/);
    assert.match(output, /aria-live="polite"/);
    assert.match(output, /aria-atomic="true"/);
    for (const type of ['range', 'number']) {
      const input = html.match(new RegExp(`<input[^>]*type="${type}"[^>]*data-subdub-local-volume="${kind}"[^>]*>`))?.[0] || '';
      const describedBy = input.match(/aria-describedby="([^"]+)"/)?.[1] || '';
      assert.match(describedBy, new RegExp(`subdub-${kind}-volume-(?:dub|number-dub)-error`));
      assert.match(html, new RegExp(`id="subdub-${kind}-volume-(?:dub|number-dub)-error"`));
    }
  }
});

test('SubDub tab controls keep a valid labelled panel relationship in every mode', () => {
  const html = render('subtitle_only', 'en');
  for (const match of html.matchAll(/<button[^>]*role="tab"[^>]*aria-controls="([^"]+)"[^>]*>/g)) {
    assert.match(html, new RegExp(`id="${match[1]}"[^>]*role="tabpanel"`));
  }
  for (const match of html.matchAll(/<section[^>]*role="tabpanel"[^>]*aria-labelledby="([^"]+)"[^>]*>/g)) {
    assert.match(html, new RegExp(`id="${match[1]}"`));
  }
});
