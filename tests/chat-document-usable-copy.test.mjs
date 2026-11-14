import assert from 'node:assert/strict';
import test from 'node:test';
import fs from 'node:fs';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {usableCopyHistoricalSnapshot,usableCopyHistoricalPortalSource} from './helpers/chat-document-usable-snapshot.mjs';

// Exercise actual renderers: wrong language, lost fields/data/rights, fabricated
// tool readiness/counts/download, or an empty replacement must fail.
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const BASE='2cae14ab1825746b7e8e1123f59a89cb7cd54396';
const helper=fs.readFileSync(path.join(root,'tests/helpers/publishing-child-render.mjs'),'utf8');
async function load(base=false){
  let source=helper.replace("const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');",'const root='+JSON.stringify(root)+';');
  if(base)for(const [name,file]of [['portal','static/portal/portal.js'],['i18n','static/portal/portal-i18n.js']]){
    const old=`const ${name}=fs.readFileSync(path.join(root,'${file}'),'utf8');`;assert.equal(source.split(old).length-1,1);
    source=source.replace(old,'const '+name+'='+JSON.stringify(execFileSync('git',['show',BASE+':'+file],{cwd:root,encoding:'utf8',maxBuffer:30e6}))+';');
  }
  const old='normalizePublishReviewPackResult,customerMobileNavGroupForPath};';assert.equal(source.split(old).length-1,1);
  source=source.replace(old,'normalizePublishReviewPackResult,customerMobileNavGroupForPath,chatThreadFields};');
  source=source.replace('return {html,text:plain(html),','return {editorFields:window.__childLocale.chatThreadFields(context),html,text:plain(html),');
  return(await import('data:text/javascript;base64,'+Buffer.from(source).toString('base64'))).renderChild;
}
const current=await load(),base=await load(true),locales=['vi','en','zh'];
const approved=JSON.parse(fs.readFileSync(new URL('./fixtures/chat-document-usable-copy-reviewed.json',import.meta.url),'utf8'));
const esc=x=>String(x).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;');
const controls=html=>[...html.matchAll(/<(?:a|button|form|input|option|select|textarea)\b[^>]*>/g)].map(m=>m[0].replace(/placeholder="[^"]*"/g,'placeholder="__TEXT__"'));
const contracts=fields=>JSON.stringify(fields.map(field=>{
  const copy={...field};for(const key of ['label','placeholder','help','emptyLabel'])delete copy[key];
  if(copy.name==='mode')copy.options=copy.options.map(([value])=>value);
  return copy;
}));
const id='11111111-1111-4111-8111-111111111111',customer='CUSTOMER studio metadata <script>';
const thread={id,title:customer,mode:'focus',state:'draft',revision:1,context_count:1,turn_count:1};
function chatRaw(items=[],counts={},allowed=true){
  return {chatWorkspaceEnabled:true,capabilities:{'chat-workspace-view':true,'chat-thread-create':allowed,'chat-thread-update':allowed},
    chatThreads:items,chatWorkspaceSummary:{threads:counts},
    chatWorkspaceReferences:{projects:[{id,title:customer}],prompt_templates:[{id,title:customer}]},
    chatThreadDetail:{thread,contexts:[],turns:[],versions:[],events:[]}};
}
for(const locale of locales)for(const route of ['/chat','/chat/'+id])for(const allowed of [false,true])test(`${locale}${route}/write${allowed}: actual eight-field create/detail consumer preserves names/constraints/customer options`,()=>{
  const raw=chatRaw([],{},allowed),saved=JSON.stringify(raw),a=current(locale,route,raw),b=base(locale,route,structuredClone(raw));
  assert.equal(JSON.stringify(raw),saved);assert.equal(JSON.stringify(a.context),JSON.stringify(b.context));
  assert.equal(a.editorFields.length,8);assert.equal(contracts(a.editorFields),contracts(b.editorFields));
  assert.deepEqual(controls(a.html),controls(b.html),'control IDs/values/routes/permissions preserved');
  for(const [key,value]of Object.entries(a.messages[locale]).filter(([key])=>key.startsWith('chatFieldUi'))){
    assert.ok(a.html.includes(esc(value)),key+' actual consumer');
    if(locale==='vi')assert.doesNotMatch(value,/\b(?:launch|brief|tags?|profile|authoring|model|quota|Bot|prompt|library|workspace|ID|metadata)\b/i);
  }
  assert.equal(Object.keys(a.messages[locale]).filter(key=>key.startsWith('chatFieldUi')).length,19);
  assert.ok(a.editorFields.some(f=>JSON.stringify(f.options||[]).includes(customer)));
});
for(const locale of locales)for(const [name,counts,items,visible]of [
  ['missing',undefined,[],false],['zero',{total:0,review:0,ready:0},[],false],
  ['negative',{total:-1,review:-1,ready:-1},[],false],['invalid',{total:'invalid'},[],false],
  ['total',{total:2},[],true],['review',{review:1},[],true],['ready',{ready:1},[],true],
  ['thread-fallback',{},[thread],true]
])test(`${locale}/intro-${name}: zero-only cards omitted, real positive values remain unchanged`,()=>{
  const raw=chatRaw(items,counts),a=current(locale,'/chat',raw),b=base(locale,'/chat',structuredClone(raw));
  const intro=html=>/<section class="portal-chat-workspace-intro">[\s\S]*?<\/section>/.exec(html)?.[0];
  const actual=intro(a.html),old=intro(b.html);assert.ok(actual&&old);
  const dl=/<dl>[\s\S]*?<\/dl>/;assert.equal(dl.test(actual),visible);
  assert.equal(actual,visible?old:old.replace(dl,''));
  assert.equal(JSON.stringify(a.context),JSON.stringify(b.context));
});
for(const locale of locales)for(const route of ['/documents','/documents/pdf'])for(const enabled of [false,true])for(const state of ['empty','processing','completed'])test(`${locale}${route}/${enabled}/${state}: nine actual tools keep readiness/links/history/counts; implementation footer removed`,()=>{
  const flags=Object.fromEntries(['pdfToImagesEnabled','imageToPdfEnabled','pdfToWordEnabled','imageOcrEnabled','pdfOcrEnabled','pdfOcrWordEnabled'].map(k=>[k,enabled]));
  const operation={id,kind:'pdf_split',state,download_ready:state==='completed',source_name:customer,output_name:customer};
  const raw={capabilities:{'document-operation-view':true,'document-operation-refresh':true},documentOperationsReadState:'ready',documentOperations:state==='empty'?[]:[operation],...flags};
  const saved=JSON.stringify(raw),a=current(locale,route,raw),b=base(locale,route,structuredClone(raw));
  assert.equal(JSON.stringify(raw),saved);assert.equal(JSON.stringify(a.context),JSON.stringify(b.context));
  assert.deepEqual(controls(a.html),controls(b.html));
  const dt=html=>[...html.matchAll(/<dt>([^<]*)<\/dt>/g)].map(m=>m[1]);
  assert.deepEqual(dt(a.html),dt(b.html));
  const cards=html=>[...html.matchAll(/<a class="portal-module-card" data-document-tool-state="([^"]+)" href="([^"]+)"/g)].map(m=>[m[1],m[2]]);
  assert.equal(cards(a.html).length,9);assert.deepEqual(cards(a.html),cards(b.html));
  assert.equal((a.html.match(/class="portal-document-board-workflow-group"/g)||[]).length,3);
  assert.equal(a.html.includes('Biên giới dữ liệu rõ ràng'),false);
  assert.equal(a.html.includes('class="portal-panel-list"'),false);
  assert.match(a.html,/class="[^"]*\bportal-document-board-history\b/);
  assert.equal(Object.keys(a.messages[locale]).filter(k=>/^(docToolUi|docBoardUi)/.test(k)).length,48);
});
for(const locale of locales)for(const readState of ['loading','failed','guarded'])test(`${locale}/document-${readState}: unrelated read/access branch is byte-exact`,()=>{
  const raw={capabilities:readState==='guarded'?{}:{'document-operation-view':true,'document-operation-refresh':true},documentOperationsReadState:readState};
  assert.equal(current(locale,'/documents',raw).html,base(locale,'/documents',structuredClone(raw)).html);
});
for(const locale of locales)test(`${locale}: exactly 67 approved entries; every old value/order and message meaning remains`,()=>{
  const a=current(locale,'/chat',{}),b=base(locale,'/chat',{}),entries=Object.entries(a.messages[locale]);
  const added=entries.filter(([key])=>!Object.hasOwn(b.messages[locale],key));
  assert.equal(added.length,67);assert.deepEqual(JSON.parse(JSON.stringify(added)),approved.added[locale].entries);
  assert.deepEqual(entries.filter(([key])=>Object.hasOwn(b.messages[locale],key)),Object.entries(b.messages[locale]));
  for(const [,value]of added){
    assert.doesNotMatch(value,/\b(?:workspace|metadata|CSRF|provider|signed|guarded|pipeline|runtime|workflow|contract|artifact)\b|thử nghiệm|\bdemo\b|\btrial\b/i);
    if(locale==='zh')assert.match(value,/\p{Script=Han}/u);
    if(locale==='en')assert.doesNotMatch(value,/[À-ỹĐđ]|\p{Script=Han}/u);
  }
});
for(const locale of locales)test(`${locale}: historical adapter rejects mutated/missing values and preserves unknown keys`,()=>{
  const a=current(locale,'/chat',{}),entries=Object.entries(a.messages[locale]),saved=JSON.stringify(entries);
  const normalized=usableCopyHistoricalSnapshot(entries,locale);
  assert.equal(normalized.length,entries.length-67);assert.equal(JSON.stringify(entries),saved);
  for(const [key]of approved.added[locale].entries){
    assert.throws(()=>usableCopyHistoricalSnapshot(entries.map(([k,v])=>[k,k===key?'UNREVIEWED_MUTATION':v]),locale),/Unreviewed usable copy/);
  }
  assert.deepEqual(usableCopyHistoricalSnapshot([...entries,['unknown.customer.key',customer]],locale).at(-1),['unknown.customer.key',customer]);
});
test('historical source adapter accepts exactly reviewed spans and retains unrelated code',()=>{
  const source=fs.readFileSync(path.join(root,'static/portal/portal.js'),'utf8').replace(/\r\n/g,'\n');
  const expected=execFileSync('git',['show',BASE+':static/portal/portal.js'],{cwd:root,encoding:'utf8',maxBuffer:30e6}).replace(/\r\n/g,'\n');
  assert.equal(usableCopyHistoricalPortalSource(source),expected);
  for(const edit of approved.portalEdits.filter(edit=>edit.after)){
    assert.throws(()=>usableCopyHistoricalPortalSource(source.replace(edit.after,edit.after+'__UNREVIEWED__').replace(edit.after,'__MUTATED__')),/Unreviewed source fragment/);
  }
  assert.ok(usableCopyHistoricalPortalSource(source+'\n// UNRELATED_SOURCE_SENTINEL').endsWith('// UNRELATED_SOURCE_SENTINEL'));
});
