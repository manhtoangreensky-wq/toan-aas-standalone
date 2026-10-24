import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

const portalJs = fs.readFileSync('static/portal/portal.js', 'utf8').replace(/\r\n/g, '\n');
const i18nJs = fs.readFileSync('static/portal/portal-i18n.js', 'utf8');
const css = fs.readFileSync('static/portal/portal-theme.css', 'utf8');
const locales = ['vi', 'en', 'zh'];
const expectedRows = [
  ['musicDirectionUi.page.workspaceTitle', 'Hướng âm nhạc', 'Music directions', '音乐方向'],
  ['musicDirectionUi.form.body', 'Chọn phong cách và mô tả cảnh, người nghe, cảm xúc bạn muốn truyền tải.', 'Choose a style and describe the scene, audience and mood.', '选择风格，并描述场景、受众和情绪。'],
  ['musicDirectionUi.form.note', 'Nhận ba hướng âm nhạc bằng văn bản để biên tập; không tạo tệp nhạc.', 'Get three music directions as text for editing; no audio file is created.', '获取三个供编辑的文字音乐方向；不会生成音频文件。'],
  ['sfxCueSheetUi.page.workspaceTitle', 'Gợi ý hiệu ứng âm thanh', 'Sound effect planning', '音效规划'],
  ['sfxCueSheetUi.form.title', 'Bảng gợi ý hiệu ứng', 'SFX cue sheet', '音效提示表'],
  ['sfxCueSheetUi.form.body', 'Chọn loại hiệu ứng và mô tả những điểm cần nhấn trong video.', 'Choose an effect type and describe the video moments to emphasize.', '选择音效类型，并描述视频中需要突出的时刻。'],
  ['sfxCueSheetUi.form.note', 'Nhận một bảng gồm ba gợi ý hiệu ứng bằng văn bản; không tạo tệp âm thanh.', 'Get one cue sheet with three text-based effect suggestions; no audio file is created.', '获取一张包含三个文字音效建议的提示表；不会生成音频文件。'],
  ['sfxCueSheetUi.form.submit', 'Lập bảng gợi ý hiệu ứng', 'Create SFX cue sheet', '创建音效提示表']
];
const staleCopy = {
  music: ['Nội dung đã thay đổi. Các hướng bên dưới thuộc nội dung trước; lập lại hướng âm nhạc để cập nhật.', 'The brief has changed. The directions below use the previous brief; create music directions again to update them.', '摘要已更改。下方方向仍基于先前内容，请重新创建音乐方向以更新。'],
  sfx: ['Nội dung đã thay đổi. Bảng hiệu ứng bên dưới thuộc nội dung trước; lập lại bảng để cập nhật.', 'The brief has changed. The cue sheet below uses the previous brief; create the cue sheet again to update it.', '摘要已更改。下方音效提示表仍基于先前内容，请重新创建提示表以更新。']
};

function extract(name) {
  const start = portalJs.indexOf(`  function ${name}(`);
  assert.notEqual(start, -1, `real function ${name} exists`);
  const end = portalJs.indexOf('\n  }', start);
  assert.notEqual(end, -1, `real function ${name} has a top-level close`);
  return portalJs.slice(start, end + 4);
}

function extractPresets(name) {
  const start = portalJs.indexOf(`  const ${name} = Object.freeze([`);
  assert.notEqual(start, -1, `real presets ${name} exist`);
  const end = portalJs.indexOf(']);', start);
  assert.notEqual(end, -1);
  return portalJs.slice(start, end + 3);
}

function harness(locale) {
  const catalogue = vm.createContext({});
  vm.runInContext(i18nJs, catalogue);
  const i18n = catalogue.TOANAASI18n;
  const sandbox = {
    uiText: (key, fallback, params) => i18n.t(key, params, locale) || fallback,
    // Presentation-only doubles: no normalizer, input, provider or native-engine claims.
    normalizeMusicDirectionPresetState: value => value || {},
    normalizeSfxCueSheetState: value => value || {},
    musicDirectionPresetFormValues: () => ({ description: 'Brief', language: 'vi', web_preset_id: 'commercial_bright' }),
    sfxCueSheetFormValues: () => ({ description: 'Brief', language: 'vi', web_sfx_preset_id: 'motion_transition' }),
    renderFields: () => '', renderHero: () => '', renderNotes: () => '', badge: () => '',
    transientFormDrafts: new Map(), SFX_CUE_SHEET_ROUTE: '/media-workspace/sfx-cue-sheet',
    transientFormValues: () => sandbox.transientFormDrafts.get(sandbox.SFX_CUE_SHEET_ROUTE),
    sfxCueSheetTransientFormValues: value => value
  };
  vm.createContext(sandbox);
  const functions = ['safeText', 'musicDirectionUiText', 'sfxCueSheetUiText',
    'musicDirectionPresetText', 'sfxCueSheetPresetText', 'sfxCueSheetPlacementLabel',
    'musicDirectionPresetFields', 'sfxCueSheetFields', 'renderMusicDirectionPresets',
    'renderSfxCueSheet', 'renderMusicDirectionPresetResult', 'renderSfxCueSheetResult'];
  vm.runInContext([
    extractPresets('MUSIC_DIRECTION_PRESETS'), extractPresets('SFX_CUE_SHEET_PRESETS'),
    'const MUSIC_DIRECTION_PRESET_IDS = new Set(MUSIC_DIRECTION_PRESETS.map(p => p.id));',
    'const SFX_CUE_SHEET_PRESET_IDS = new Set(SFX_CUE_SHEET_PRESETS.map(p => p.id));',
    ...functions.map(extract)
  ].join('\n'), sandbox);
  return { sandbox, i18n };
}

const unsafe = ' <script>&</script>';
const escaped = ' &lt;script&gt;&amp;&lt;/script&gt;';
function fixtures() {
  return {
    music: {
      source: { description: 'Brief', language: 'vi', web_preset_id: 'commercial_bright' },
      receipt: { composer: {
        title: `Music title${unsafe}`, description: `Music description${unsafe}`, language: 'vi',
        selected_suggestion: 2, selected_direction: { choice: 2 },
        suggestions: [1, 2, 3].map(choice => ({ choice, name: `M${choice} name${unsafe}`,
          mood: `M${choice} mood${unsafe}`, tempo: `M${choice} tempo${unsafe}`,
          duration: `M${choice} duration${unsafe}`, use_case: `M${choice} use_case${unsafe}`,
          prompt: `M${choice} prompt${unsafe}` })),
        review_before_use: [`Music review${unsafe}`]
      } }
    },
    sfx: {
      source: { description: 'Brief', language: 'vi', web_sfx_preset_id: 'motion_transition' },
      receipt: { cue_sheet: {
        title: `SFX title${unsafe}`, description: `SFX description${unsafe}`, language: 'vi',
        web_sfx_preset_id: 'motion_transition', cue_family: 'motion',
        cues: ['opening', 'transition', 'closing'].map((placement_id, index) => ({
          ordinal: index + 1, placement_id, placement: placement_id,
          cue_role: `S${index + 1} cue_role${unsafe}`, editorial_note: `S${index + 1} editorial_note${unsafe}`,
          direction: `S${index + 1} direction${unsafe}`, mix_note: `S${index + 1} mix_note${unsafe}`,
          avoid_note: `S${index + 1} avoid_note${unsafe}` })),
        placement_notice: `SFX notice${unsafe}`, cautions: [`SFX caution${unsafe}`],
        review_before_use: [`SFX review${unsafe}`]
      } }
    }
  };
}

for (const [column, locale] of locales.entries()) {
  const { sandbox: s, i18n } = harness(locale);
  for (const [key, ...values] of expectedRows) {
    test(`D2 ${locale}: exact catalogue copy ${key}`, () => {
      assert.equal(i18n.t(key, {}, locale), values[column]);
    });
  }
  const context = { capabilities: { 'music-direction-preset-compose': true, 'sfx-cue-sheet-compose': true } };
  const cases = [
    { kind: 'music', namespace: 'musicDirectionUi', slug: 'music-directions', renderPage: 'renderMusicDirectionPresets', renderResult: 'renderMusicDirectionPresetResult', rows: [0, 1, 2] },
    { kind: 'sfx', namespace: 'sfxCueSheetUi', slug: 'sfx-cue-sheet', renderPage: 'renderSfxCueSheet', renderResult: 'renderSfxCueSheetResult', rows: [3, 4, 5, 6, 7] }
  ];
  for (const item of cases) {
    test(`D2 ${locale} ${item.kind}: local H1, scope and concise form copy`, () => {
      const html = s[item.renderPage]({ id: item.slug, action: 'none' }, context);
      assert.equal((html.match(/<h1\b/g) || []).length, 1, 'one local H1');
      assert.ok(html.includes(`<h1 class="portal-title">${expectedRows[item.rows[0]][column + 1]}</h1>`));
      assert.ok(html.includes(`portal-${item.slug}-scope`), 'scoped section retained');
      for (const row of item.rows) assert.ok(html.includes(expectedRows[row][column + 1]), expectedRows[row][0]);
      assert.equal((html.match(/type="radio"/g) || []).length, 5, 'all five real presets retained');
    });
    test(`D2 ${locale} ${item.kind}: all three server items and escaped content remain`, () => {
      const html = s[item.renderResult](fixtures()[item.kind]);
      const list = html.match(new RegExp(`<ol class="portal-${item.slug}-list">([\\s\\S]*?)</ol>`));
      assert.ok(list, 'real item list');
      assert.equal((list[1].match(/<li(?:\s|>)/g) || []).length, 3);
      const prefix = item.kind === 'music' ? 'Music' : 'SFX';
      for (const field of ['title', 'description', 'review']) assert.ok(html.includes(`${prefix} ${field}${escaped}`), field);
      const fields = item.kind === 'music' ? ['name', 'mood', 'tempo', 'duration', 'use_case', 'prompt'] : ['cue_role', 'editorial_note', 'direction', 'mix_note', 'avoid_note'];
      for (const number of [1, 2, 3]) for (const field of fields) {
        assert.ok(html.includes(`${item.kind === 'music' ? 'M' : 'S'}${number} ${field}${escaped}`), `${number} ${field}`);
      }
      if (item.kind === 'sfx') for (const field of ['notice', 'caution']) assert.ok(html.includes(`SFX ${field}${escaped}`));
      assert.ok(!html.includes('<script>'), 'server strings are not executable markup');
      assert.ok(html.includes('<p class="portal-form-note">'), 'existing result note remains in DOM');
    });
    test(`D2 ${locale} ${item.kind}: suffix and localized stale paragraph are real result DOM`, () => {
      const html = s[item.renderResult](fixtures()[item.kind]);
      const suffix = i18n.t(`${item.namespace}.result.bodySuffix`, {}, locale);
      assert.ok(html.includes(`<span class="portal-native-output-detail">${suffix}</span>`), 'suffix wrapper');
      assert.ok(html.includes(`<p class="portal-native-stale-note">${staleCopy[item.kind][column]}</p>`), 'localized stale paragraph');
      if (item.kind === 'sfx') assert.ok(html.includes('<span data-sfx-cue-sheet-family>MOTION</span>'));
    });
    test(`D2 ${locale} ${item.kind}: empty result does not acquire valid receipt hooks`, () => {
      const html = s[item.renderResult]({});
      assert.ok(html.includes(`portal-${item.slug}-result`));
      assert.ok(!html.includes('aria-live="polite"') && !html.includes('data-sfx-cue-sheet-receipt'));
      assert.ok(!html.includes('portal-native-stale-note') && !html.includes('portal-native-output-detail'));
    });
  }
  test(`D2 ${locale} SFX: existing draft comparison survives repeated result render`, () => {
    const state = fixtures().sfx;
    assert.ok(s.renderSfxCueSheetResult(state).includes('data-stale="false"'));
    s.transientFormDrafts.set(s.SFX_CUE_SHEET_ROUTE, { ...state.source, description: 'Edited brief' });
    try {
      for (const render of [1, 2]) {
        const html = s.renderSfxCueSheetResult(state);
        assert.ok(html.includes('data-stale="true"'), `render ${render}`);
        assert.ok(html.includes(`SFX description${escaped}`), 'last server content retained');
      }
    } finally { s.transientFormDrafts.clear(); }
  });
}

// Source placement only; actual visibility, computed layout and native POSTs require browser QA.
test('D2 scoped CSS declarations occur before Final Chat marker', () => {
  const marker = '/* Final light AI Chat Workspace surface */';
  assert.ok(css.includes(marker));
  const before = css.slice(0, css.indexOf(marker));
  for (const selector of ['article.portal-page:is(.portal-music-directions, .portal-sfx-cue-sheet)',
    'article.portal-page.portal-sfx-cue-sheet [data-sfx-cue-sheet-family]', '.portal-native-stale-note']) {
    assert.ok(before.includes(selector), selector);
  }
});
