import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';

const source=fs.readFileSync('static/portal/portal.js','utf8');
const start=source.indexOf('  function renderVoiceDirectionComposerResult(');
const end=source.indexOf('  // Voice Studio is intentionally distinct',start);
assert.ok(start>=0&&end>start);
const section=source.slice(start,end);
const i18n=fs.readFileSync('static/portal/portal-i18n.js','utf8');
for(const locale of ['vi','en','zh']){
  test(`Voice Direction Composer fixed copy has a catalogue path (${locale})`,()=>{
    for(const key of ['composer.direction.title','composer.direction.empty','composer.direction.meta.set','composer.direction.meta.speed','composer.direction.compare.title','composer.direction.useCase','composer.direction.direction','composer.direction.stylePrompt','composer.direction.notes.title','composer.direction.review.title','composer.direction.scope.title','composer.direction.scope.description']){
      assert.match(i18n,new RegExp(`\\["${key.replace(/\./g,'\\.')}"`),`missing ${key}`);
    }
    assert.doesNotMatch(section,/Reviewable direction receipt|Web-native deterministic direction|Three delivery directions|Use case|Style prompt|Delivery notes|Execution boundary|Raw audio \/ voice ID|TTS \/ clone \/ preview|Job \/ wallet \/ payment|Asset \/ persistent record/);
  });
}
