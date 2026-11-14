import assert from 'node:assert/strict';
import test from 'node:test';
import fs from 'node:fs';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {withoutLegacyDecorativeWorkbench} from './helpers/legacy-decorative-workbench.mjs';
import {chatDocHistoricalMarkup} from './helpers/chat-doc-access-snapshot.mjs';

// Catch fabricated success/price/readiness/output panels returning before real
// forms, and catch accidentally deleting anything outside those exact panels.
const ROOT=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const BASE='c4da5f4a90a4ca37c46b66220c81928b806a4f2a';
const helper=path.join(ROOT,'tests/helpers/publishing-child-render.mjs');
const {renderChild:renderCurrent}=await import(pathToFileURL(helper).href);
let source=fs.readFileSync(helper,'utf8');
const edits=[["const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');",'const root='+JSON.stringify(ROOT)+';']];
for(const [name,file]of [['portal','static/portal/portal.js'],['i18n','static/portal/portal-i18n.js']]){
  const text=execFileSync('git',['show',BASE+':'+file],{cwd:ROOT,encoding:'utf8',maxBuffer:30e6});
  edits.push([`const ${name}=fs.readFileSync(path.join(root,'${file}'),'utf8');`,'const '+name+'='+JSON.stringify(text)+';']);
}
for(const [old,next]of edits){assert.equal(source.split(old).length-1,1);source=source.replace(old,next);}
const {renderChild:renderBase}=await import('data:text/javascript;base64,'+Buffer.from(source).toString('base64'));
const portal=fs.readFileSync(path.join(ROOT,'static/portal/portal.js'),'utf8');
const start=portal.indexOf('  function renderInteractiveFeatureWorkbench('),end=portal.indexOf('\n  function renderWorkspace(',start);
assert.ok(start>=0&&end>start);
const actualWorkbench=new Function(portal.slice(start,end)+'\nreturn renderInteractiveFeatureWorkbench;')();
const inputs=[{path:'/video/product'},{path:'/documents'},{path:'/pdf'},{path:'/chat'},{path:'/content/pack'},
  {featureFamily:'video'},{featureFamily:'documents'},{featureFamily:'content'},{featureFamily:'prompt'},
  {path:'/image/create'},{featureFamily:'image'},{path:'/music/create'},{featureFamily:'music'},{},null,undefined,
  {path:0},{routePath:'/VIDEO/product',path:'/image/create'}];
for(const [index,page]of inputs.entries())test(`helper/${index}: decorative helper emits no invented UI for any path/family`,()=>{
  const context={wallet:null,capabilities:{},bridge:{available:false}},before=structuredClone(context);
  assert.equal(actualWorkbench(page,context),'');assert.deepEqual(context,before);
});
const affected=['/features/video','/features/documents','/features/content','/video/long','/video/product',
  '/video/text-to-video','/video/image-to-video','/video/trend','/video/quick','/video/progress','/video/export'];
const protectedRoutes=['/features/image','/features/music','/video/create','/video/multiscene','/voice/tts',
  '/documents/pdf-to-word','/chat','/content/pack','/image/create'];
const labels={vi:'Xưởng sáng tạo AI',en:'AI Studios',zh:'AI 创作工坊'};
const controls=html=>[...html.matchAll(/<(?:a|button|input|form|select|textarea|option)\b[^>]*>/g)].map(match=>match[0]);
const withAcceptedAlias=(html,locale)=>html.replace('<div class="portal-eyebrow">AI Studio</div>','<div class="portal-eyebrow">'+labels[locale]+'</div>');
for(const locale of ['vi','en','zh'])for(const route of [...affected,...protectedRoutes])for(const knownWallet of [false,true]){
  test(`${locale}${route}/${knownWallet}: remove only legacy panel while preserving actual forms, states, raw data and controls`,()=>{
    const raw={wallet:knownWallet?{balance_xu:0,total_spent_xu:0,is_vip:false,plan:{plan_name:'CUSTOMER_PLAN',plan_status:'CUSTOMER_STATUS'}}:null,
      capabilities:{},assets:[],jobs:[],pageStates:{[route]:knownWallet?'failed':'guarded'}};
    const before=structuredClone(raw),old=renderBase(locale,route,structuredClone(raw)),current=renderCurrent(locale,route,raw);
    assert.deepEqual(raw,before);assert.equal(JSON.stringify(current.context),JSON.stringify(old.context));
    const expected=withoutLegacyDecorativeWorkbench(old.html);
    assert.equal(expected.count,affected.includes(route)?1:0,'BASE witness classification is explicit, not inferred from current output');
    assert.deepEqual(controls(current.html),controls(expected.html),'all real controls outside the known fake panel remain exact');
    assert.equal(chatDocHistoricalMarkup(current.html,locale),withAcceptedAlias(expected.html,locale),'every unrelated markup byte remains exact, aside from independently accepted alias and finite root-access copy');
    assert.doesNotMatch(current.html,/portal-interactive-feature-workbench|\bonclick\s*=/i);
  });
}
