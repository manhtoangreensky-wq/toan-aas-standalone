import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const source=fs.readFileSync('static/portal/portal.js','utf8');
const i18n=fs.readFileSync('static/portal/portal-i18n.js','utf8');
function section(start,end){const a=source.indexOf(start),b=source.indexOf(end,a+start.length);assert.ok(a>=0&&b>a,start);return source.slice(a,b);}
const detail=section('  function renderVoiceCueSheet(', '  // Video Production Studio');
for(const locale of ['vi','en','zh']){
  test(`Voice detail renderer exposes localized fixed copy and no raw technical labels (${locale})`,()=>{
    const context={};vm.createContext(context);vm.runInContext(i18n,context);
    const catalogKeys=['script.kind.narration','script.kind.ad','script.kind.explainer','script.kind.podcast','script.kind.training','script.kind.custom','detail.title','detail.status.active','detail.status.archived','detail.actions.archive','detail.actions.restore','detail.actions.duplicate','detail.actions.save','detail.actions.open','detail.sections.scripts','detail.sections.history','detail.sections.activity','detail.sections.policy','script.action.cue','script.action.archive','script.action.restore','script.action.duplicate','script.action.save','cue.title','cue.description','cue.empty','cue.words','cue.sentences','cue.seconds','cue.pace'];
    for(const key of catalogKeys) assert.ok(context.TOANAASI18n.has(`customerVoiceStudio.${key}`),`missing ${key}`);
    assert.doesNotMatch(detail,/\b(?:Direction & consent metadata|Archive direction|Archive script|Manual authoring|Local deterministic writing aid|Version history|Provider \/ delivery boundary|Scripts & cue-sheet|Direction mặc định|Voice direction|Voice script|Use case|Delivery notes|TTS|Job Center)\b/);
    if(locale==='en') assert.ok(context.TOANAASI18n.has('customerVoiceStudio.detail.title'));
  });
}
