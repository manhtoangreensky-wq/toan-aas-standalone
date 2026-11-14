import assert from 'node:assert/strict';
import test from 'node:test';
import fs from 'node:fs';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {chatDocAccessHistoricalSnapshot,chatDocHistoricalMarkup} from './helpers/chat-doc-access-snapshot.mjs';

// Catch fixed-language leaks without translating customer data or changing
// access decisions, real forms, controls, loading/error/ready output.
const ROOT=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const BASE='7ef5e3c6ade86acff9a9578f36f9c85287a37a73';
const helper=path.join(ROOT,'tests/helpers/publishing-child-render.mjs');
const {renderChild:renderCurrent}=await import(pathToFileURL(helper).href);
let source=fs.readFileSync(helper,'utf8');
const edits=[["const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');",'const root='+JSON.stringify(ROOT)+';']];
for(const [name,file]of [['portal','static/portal/portal.js'],['i18n','static/portal/portal-i18n.js']]){
  edits.push([`const ${name}=fs.readFileSync(path.join(root,'${file}'),'utf8');`,'const '+name+'='+JSON.stringify(execFileSync('git',['show',BASE+':'+file],{cwd:ROOT,encoding:'utf8',maxBuffer:30e6}))+';']);
}
for(const [old,next]of edits){assert.equal(source.split(old).length-1,1);source=source.replace(old,next);}
const {renderChild:renderBase}=await import('data:text/javascript;base64,'+Buffer.from(source).toString('base64'));
const escaped=x=>String(x).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;');
const controlTags=html=>[...html.matchAll(/<(?:a|button|input|form|select|textarea|option)\b[^>]*>/g)].map(m=>m[0]);
const language=(value,locale)=>locale==='vi'?/[À-ỹĐđ]/u.test(value)&&!/\p{Script=Han}/u.test(value):locale==='zh'?/\p{Script=Han}/u.test(value):/[a-z]/i.test(value)&&!/[À-ỹĐđ]|\p{Script=Han}/u.test(value);
const technical=/signed[ -]?session|owner[ -]?scoped|guarded|metadata|CSRF|Core Bridge|workspace|\bthread\b|\brevision\b|\bserver\b|\bworkflow\b|\bcontract\b|\bgeneric\b|\boutput\b|thử nghiệm|\bdemo\b|\bbeta\b|\btrial\b/i;
const headKeys={
  '/chat':['workspaceMenu.card.chat_workspace.title','workspaceMenu.card.chat_workspace.description'],
  '/documents':['workspaceMenu.card.documents.title','featureCatalog.entry.documents.description']
};
function finiteHeader(html){
  for(const [pattern,marker]of [[/(<h1 class="portal-title">)[\s\S]*?(<\/h1>)/,'__ROOT_TITLE__'],[/(<p class="portal-description">)[\s\S]*?(<\/p>)/,'__ROOT_DESCRIPTION__']]){
    assert.equal([...html.matchAll(new RegExp(pattern,'g'))].length,1);
    html=html.replace(pattern,'$1'+marker+'$2');
  }
  return html;
}
function guard(html){
  const index=html.indexOf('<section class="portal-card portal-card-pad">');assert.ok(index>=0);
  const prefix=html.slice(0,index),tail=html.slice(index),match=/<h([23])>([^<]+)<\/h\1><p>([^<]+)<\/p>/.exec(tail);
  assert.ok(match,'real root guard heading/body must remain');
  return{heading:match[2],body:match[3],tail,prefix,tag:match[1],
    comparable:prefix+tail.replace(match[0],'<h'+match[1]+'>__ACCESS_HEADING__</h'+match[1]+'><p>__ACCESS_BODY__</p>')};
}
const oldMeta='<div class="portal-state-meta"><span>Signed session</span><span>Owner-scoped</span><span>Không có output giả</span></div>';
const namedThread={id:'11111111-1111-4111-8111-111111111111',title:'CUSTOMER AI Chat Workspace <script>',objective_excerpt:'CUSTOMER metadata context',mode:'chat',state:'draft',revision:2,context_count:1,turn_count:2,tags:['CUSTOMER_WORD'],updated_at:'2026-11-14T01:00:00Z'};
const fixtures=[
  {name:'chat-disabled',route:'/chat',guard:true,raw:{chatWorkspaceEnabled:false,capabilities:{}}},
  {name:'chat-enabled-no-view',route:'/chat',guard:true,signIn:true,raw:{chatWorkspaceEnabled:true,capabilities:{}}},
  ...[false,true].map(create=>({name:'chat-authoring-'+create,route:'/chat',raw:{chatWorkspaceEnabled:true,capabilities:{'chat-workspace-view':true,'chat-thread-create':create},chatThreads:[namedThread]}})),
  ...['/documents','/documents/pdf'].flatMap(route=>[
    {name:route+'-no-view',route,guard:true,document:true,raw:{capabilities:{}}},
    ...['loading','failed','ready'].flatMap(state=>[false,true].map(refresh=>({name:route+'-'+state+'-'+refresh,route,raw:{capabilities:{'document-operation-view':true,'document-operation-refresh':refresh},documentOperationsReadState:state,documentOperations:[]}})))
  ])
];
for(const locale of ['vi','en','zh'])for(const fixture of fixtures)test(`${locale}/${fixture.name}: only approved root header/access text changes, data and all other markup remain exact`,()=>{
  const raw={...structuredClone(fixture.raw),profile:{locale,displayName:'CUSTOMER_TEXT'},wallet:{balance_xu:0},pageStates:{[fixture.route]:'guarded'}};
  const saved=structuredClone(raw),current=renderCurrent(locale,fixture.route,raw),old=renderBase(locale,fixture.route,structuredClone(raw));
  assert.deepEqual(raw,saved);assert.equal(JSON.stringify(current.context),JSON.stringify(old.context));
  assert.deepEqual(controlTags(current.html),controlTags(old.html),'permissions, disabled controls and form contracts stay exact');
  let actual=current.html,expected=old.html;
  if(headKeys[fixture.route]){
    const [titleKey,bodyKey]=headKeys[fixture.route],messages=current.messages[locale],title=messages[titleKey],body=messages[bodyKey];
    assert.ok(title&&body);assert.ok(actual.includes('<h1 class="portal-title">'+escaped(title)+'</h1>'));
    assert.ok(actual.includes('<p class="portal-description">'+escaped(body)+'</p>'));
    assert.equal(current.title,title+' · TOAN AAS');
    actual=finiteHeader(actual);expected=finiteHeader(expected);
  }else assert.equal(current.title,old.title,'non-root document aliases keep existing title');
  if(fixture.guard){
    const a=guard(actual),b=guard(expected);assert.equal(a.tag,b.tag);
    assert.ok(language(a.heading,locale)&&language(a.body,locale),'access text follows selected locale');
    assert.doesNotMatch(a.heading+' '+a.body,technical,'fixed access copy contains no implementation/demo jargon');
    const prefix=fixture.document?'documentAccessUi':'chatAccessUi';
    for(const text of [a.heading,a.body])assert.ok(Object.entries(current.messages[locale]).some(([key,value])=>key.startsWith(prefix)&&escaped(value)===text),'guard uses real new localized key');
    if(fixture.signIn)assert.match(a.body,locale==='vi'?/đăng nhập/i:locale==='en'?/(?:sign|log) in/i:/登录/);
    if(fixture.document){
      assert.equal(b.tail.split(oldMeta).length-1,1);assert.equal(a.tail.includes('portal-state-meta'),false,'no repetitive or empty implementation-tag row');
      expected=b.comparable.replace(oldMeta,'');
    }else expected=b.comparable;
    actual=a.comparable;
  }
  assert.equal(actual,expected,'entire non-finite output is byte-identical');
});
for(const locale of ['vi','en','zh'])test(`${locale}: exactly five new access keys, every previous catalogue value and customer title intact`,()=>{
  const current=renderCurrent(locale,'/chat',{}),old=renderBase(locale,'/chat',{});
  const entries=Object.entries(current.messages[locale]),newEntries=entries.filter(([key])=>!Object.hasOwn(old.messages[locale],key));
  assert.equal(newEntries.length,5);assert.equal(newEntries.filter(([key])=>key.startsWith('chatAccessUi')).length,3);
  assert.equal(newEntries.filter(([key])=>key.startsWith('documentAccessUi')).length,2);
  for(const [key,value]of newEntries){assert.ok(language(value,locale),key);assert.doesNotMatch(value,technical);}
  assert.deepEqual(entries.filter(([key])=>Object.hasOwn(old.messages[locale],key)),Object.entries(old.messages[locale]),'all old dictionary values/order preserved');
  const enabled=renderCurrent(locale,'/chat',{chatWorkspaceEnabled:true}),disabled=renderCurrent(locale,'/chat',{chatWorkspaceEnabled:false});
  assert.notEqual(guard(enabled.html).body,guard(disabled.html).body,'two real access situations remain distinct');
});
for(const locale of ['vi','en','zh'])test(`${locale}: historical snapshot rejects every unreviewed access value and never hides an unknown key`,()=>{
  const result=renderCurrent(locale,'/chat',{}),entries=Object.entries(result.messages[locale]),saved=JSON.stringify(entries);
  const normalized=chatDocAccessHistoricalSnapshot(entries,locale);
  assert.equal(normalized.length,entries.length-5);assert.equal(JSON.stringify(entries),saved);
  for(const [key]of entries.filter(([key])=>/^(chatAccessUi|documentAccessUi)/.test(key))){
    assert.throws(()=>chatDocAccessHistoricalSnapshot([[key,'UNREVIEWED_MUTATION']],locale),/Unreviewed access copy/);
  }
  assert.deepEqual(chatDocAccessHistoricalSnapshot([['unknown.customer.key','CUSTOMER_TEXT']],locale),[['unknown.customer.key','CUSTOMER_TEXT']]);
});
for(const locale of ['vi','en','zh'])for(const route of ['/features/content','/features/documents'])test(`${locale}${route}: actual module-card consumer changes only exact route-root title and description`,()=>{
  const current=renderCurrent(locale,route,{}),old=renderBase(locale,route,{});
  assert.deepEqual(controlTags(current.html),controlTags(old.html));
  assert.equal(JSON.stringify(current.context),JSON.stringify(old.context));
  const target=route.endsWith('content')?'/chat':'/documents',keys=headKeys[target],title=current.messages[locale][keys[0]],description=current.messages[locale][keys[1]];
  const pattern=new RegExp('<a class="portal-module-card" href="'+target+'">[\\s\\S]*?</a>');
  const card=pattern.exec(current.html)?.[0];assert.ok(card);
  assert.ok(card.includes('<h3>'+escaped(title)+'</h3><p>'+escaped(description)+'</p>'));
  assert.equal(chatDocHistoricalMarkup(current.html,locale),old.html);
  const mutated=current.html.replace('<h3>'+escaped(title)+'</h3>','<h3>UNREVIEWED_MUTATION</h3>');
  assert.notEqual(chatDocHistoricalMarkup(mutated,locale),old.html,'historical helper cannot hide a different card title');
});
for(const locale of ['vi','en','zh'])for(const title of ['AI Chat Workspace','Document Studio'])test(`${locale}/customer-title/${title}: detail records identical to product names are not translated`,()=>{
  const route='/chat/'+namedThread.id,raw={capabilities:{'chat-workspace-view':true},chatThreadDetail:{thread:{...namedThread,title},contexts:[],turns:[],versions:[],events:[]}};
  const saved=structuredClone(raw),current=renderCurrent(locale,route,raw),old=renderBase(locale,route,structuredClone(raw));
  assert.equal(current.html,old.html);assert.equal(current.title,old.title);
  assert.deepEqual(raw,saved);assert.equal(JSON.stringify(current.context),JSON.stringify(old.context));
  assert.ok(current.html.includes('<h2>'+escaped(title)+'</h2>'),'actual customer-authored title stays literal');
});
