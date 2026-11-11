import assert from 'node:assert/strict';
import test from 'node:test';
import fs from 'node:fs';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {renderChild} from './helpers/publishing-child-render.mjs';
import {landingWorkflowHistoricalSnapshot} from './helpers/landing-workflow-snapshot.mjs';

// Catch technical implementation prose returning to the customer workflow.
// Execute the real landing renderer and prove every other message/HTML unchanged.
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const base='8371c43d147b0074c71c00dc4d3f7f9927894d5c';
const oldI18n=execFileSync('git',['show',base+':static/portal/portal-i18n.js'],{cwd:root,encoding:'utf8',maxBuffer:12e6});
const helper=fs.readFileSync(path.join(root,'tests/helpers/publishing-child-render.mjs'),'utf8');
const rootLine="const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');";
const i18nLine="const i18n=fs.readFileSync(path.join(root,'static/portal/portal-i18n.js'),'utf8');";
assert.equal(helper.split(rootLine).length-1,1);assert.equal(helper.split(i18nLine).length-1,1);
const oracle=helper.replace(rootLine,'const root='+JSON.stringify(root)+';').replace(i18nLine,'const i18n='+JSON.stringify(oldI18n)+';');
const {renderChild:renderBase}=await import('data:text/javascript;base64,'+Buffer.from(oracle).toString('base64'));
const escape=text=>text.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;');
const concepts={vi:[/chọn.*công cụ/i,/chuẩn bị|soạn/i,/rà soát|kiểm tra|xem lại/i,/lưu/i],en:[/choose|select/i,/prepare|draft/i,/review|check/i,/save/i],zh:[/选择.*工具/,/准备|编写/,/检查|审阅|查看|核对/,/保存/]};
for(const locale of ['vi','en','zh'])test(locale+': customer workflow uses natural instructions and preserves the rest of landing',()=>{
  const before=renderBase(locale,'/welcome'),after=renderChild(locale,'/welcome');
  const key='landing.workflow.body',old=before.messages[locale][key],text=after.messages[locale][key];
  assert.equal(typeof text,'string');assert.ok(text.trim());
  assert.doesNotMatch(text,/signed|canonical|ledger|audit|provider|browser|ownership|nhà cung cấp|trình duyệt|sổ Xu|nhật ký|quyền sở hữu|已验证|所有权|操作记录|外部服务|浏览器|账本/i);
  for(const concept of concepts[locale])assert.match(text,concept);
  for(const language of ['vi','en','zh']){
    const a={...before.messages[language]},b={...after.messages[language]};delete a[key];delete b[key];
    assert.equal(JSON.stringify(b),JSON.stringify(a),'all other message values and keys are preserved for '+language);
  }
  const oldHtml=escape(old),newHtml=escape(text);
  assert.equal(before.html.split(oldHtml).length-1,1,'the real workflow intro is rendered exactly once');
  assert.equal(after.html.split(newHtml).length-1,1);
  assert.equal(after.html,before.html.replace(oldHtml,newHtml),'steps, controls and all other markup remain exact');
  const entries=[[key,text],['unknown.customer.key','UNCHANGED_CUSTOMER_VALUE']],snapshot=JSON.stringify(entries);
  assert.deepEqual(landingWorkflowHistoricalSnapshot(entries,locale),[[key,old],['unknown.customer.key','UNCHANGED_CUSTOMER_VALUE']]);
  assert.equal(JSON.stringify(entries),snapshot);
  assert.throws(()=>landingWorkflowHistoricalSnapshot([[key,'UNREVIEWED_MUTATION']],locale),/Unreviewed landing workflow copy/);
  assert.deepEqual(landingWorkflowHistoricalSnapshot([['unlisted.key','UNREVIEWED_MUTATION']],locale),[['unlisted.key','UNREVIEWED_MUTATION']]);
});
