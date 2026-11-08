import assert from 'node:assert/strict';
import test from 'node:test';
import { renderChild } from './helpers/publishing-child-render.mjs';

const routes = [
  ['/media-workspace/music-prompt-composer', 'music-prompt-compose', ['Soạn hướng dẫn âm nhạc', 'Music Prompt Composer', '音乐提示编写器']],
  ['/media-workspace/music-directions', 'music-direction-preset-compose', ['Hướng âm nhạc', 'Music Directions', '音乐方向']],
  ['/media-workspace/sfx-cue-sheet', 'sfx-cue-sheet-compose', ['Gợi ý hiệu ứng âm thanh', 'SFX Cue Sheet', '音效提示表']],
];
const genericEnglish = /\b(?:Music|Directions?|Composer|cue|SFX|preset|Cinematic|Short-form|Primary|Alternate|English|brief|metadata|workflow|reviewable|review|claim|server|provider|capability|request|state|input|Collection|Project|audit|browser|storage|audio|preview|output|job|asset|publish|delivery|Memory|callback|keyword|deterministic|lyrics|player|source|catalog|Module|token|form|reset)\b/iu;
const viCopy = /[À-ỹĐđ]/u;
function composerFixture() {
  const names = ['input_persisted','source_audio_inspected','provider_called','ai_music_called','lyrics_generated','audio_created','preview_created','output_created','job_created','wallet_mutated','payment_started','asset_saved','collection_saved','publish_action_created','telegram_called','rights_verified'];
  const fields = ['name','mood','tempo','instruments','duration','vocal','lyric_direction','use_case','prompt'];
  const suggestions = [1,2,3].map(choice => ({choice, ...Object.fromEntries(fields.map(key => [key, `CUSTOMER_${key}_${choice}`]))}));
  const composer = {title:'CUSTOMER_TITLE', description:'CUSTOMER_DESCRIPTION', mode:'melody', language:'en', suggestion_set:'alternate', selected_suggestion:2,
    suggestions, selected_direction:{...suggestions[1]}, usage_notes:{voice_mix_notes:'CUSTOMER_VOICE',edit_notes:'CUSTOMER_EDIT',rights_notes:'CUSTOMER_RIGHTS',delivery_notes:'CUSTOMER_DELIVERY'}, cautions:[],review_before_use:['CUSTOMER_REVIEW']};
  return {composer, execution:'web_native_deterministic_music_prompt_only', ...Object.fromEntries(names.map(key => [key,false]))};
}
for (const [index, locale] of ['vi','en','zh'].entries()) {
  for (const [route, action, titles] of routes) {
    test(`${locale} ${route} renders complete fixed chrome in the selected language`, () => {
      const result = renderChild(locale, route, {});
      assert.equal(result.title, `${titles[index]} · TOAN AAS`);
      const fixed = result.text + ' ' + result.attributes;
      if (locale === 'vi') assert.doesNotMatch(fixed, genericEnglish);
      else assert.doesNotMatch(fixed, viCopy);
      assert.match(result.html, new RegExp(`data-portal-action="${action}"`));
      assert.doesNotMatch(result.text, /References point only to the private Asset Vault|Tham chiếu chỉ trỏ tới Kho tài sản riêng|参考仅指向私有资产库/u);
    });
  }
}

for (const locale of ['vi','en','zh']) {
  test(`${locale} populated music guidance translates chrome but preserves every server text`, () => {
    const receipt = composerFixture();
    const c = receipt.composer;
    const source = {description:c.description, mode:c.mode, language:c.language, suggestion_set:c.suggestion_set, selected_suggestion:c.selected_suggestion};
    const result = renderChild(locale, '/media-workspace/music-prompt-composer', {
      capabilities:{'music-prompt-compose':true,'music-prompt-composer-save-memory':true},
      musicPromptComposerResult:receipt, musicPromptComposerSaveSource:source,
    });
    const values = [c.title,c.description,...c.suggestions.flatMap(x => Object.values(x).filter(v => typeof v === 'string')),...Object.values(c.usage_notes),...c.review_before_use];
    for (const value of values) assert.ok(result.text.includes(value), `server value lost: ${value}`);
    const fixed = (result.text + ' ' + result.attributes).replace(/CUSTOMER_[A-Za-z_0-9]+/g,'');
    if (locale === 'vi') assert.doesNotMatch(fixed, genericEnglish);
    else assert.doesNotMatch(fixed, viCopy);
    assert.match(result.html, /data-portal-action="music-prompt-composer-save-memory"/);
  });
}
