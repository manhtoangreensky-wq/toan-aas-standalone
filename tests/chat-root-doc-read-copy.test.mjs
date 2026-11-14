import assert from 'node:assert/strict';
import test from 'node:test';
import fs from 'node:fs';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {chatRootDocReadHistoricalSnapshot,chatRootDocReadHistoricalMarkup} from './helpers/chat-root-doc-read-snapshot.mjs';

// Mutations caught: wrong-locale finite labels, changed controls/rights/data,
// lost safety categories, blank/error branches, and translated customer names.
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const BASE='d14c6f0e1e0ecbef2dbba53b60cec48db67b2763';
const helper=path.join(root,'tests/helpers/publishing-child-render.mjs');
const {renderChild:current}=await import(pathToFileURL(helper));
let source=fs.readFileSync(helper,'utf8');
source=source.replace("const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');",'const root='+JSON.stringify(root)+';');
for(const [name,file]of [['portal','static/portal/portal.js'],['i18n','static/portal/portal-i18n.js']]){
  const old=`const ${name}=fs.readFileSync(path.join(root,'${file}'),'utf8');`;
  assert.equal(source.split(old).length-1,1);
  source=source.replace(old,'const '+name+'='+JSON.stringify(execFileSync('git',['show',BASE+':'+file],{cwd:root,encoding:'utf8',maxBuffer:30e6}))+';');
}
const {renderChild:base}=await import('data:text/javascript;base64,'+Buffer.from(source).toString('base64'));
const locales=['vi','en','zh'];
const esc=x=>String(x).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;');
const decode=x=>String(x).replace(/&amp;/g,'&').replace(/&quot;/g,'"').replace(/&#39;/g,"'").replace(/&lt;/g,'<').replace(/&gt;/g,'>');
const text=html=>decode(html.replace(/<[^>]+>/g,' ')).replace(/\s+/g,' ').trim();
const technical=/\b(?:signed|workspace|threads?|metadata|CSRF|OTP|URL|server|fallback|projection|handoff|paginate|handles?|auth codes|provider|Bot)\b|thử nghiệm|\bdemo\b|\bbeta\b|\btrial\b/i;
const language=(s,l)=>l==='vi'?/[À-ỹĐđ]/u.test(s)&&!/\p{Script=Han}/u.test(s):l==='zh'?/\p{Script=Han}/u.test(s):/[a-z]/i.test(s)&&!/[À-ỹĐđ]|\p{Script=Han}/u.test(s);
const thread={id:'11111111-1111-4111-8111-111111111111',title:'CUSTOMER studio media metadata <script>',objective_excerpt:'CUSTOMER workspace objective',mode:'chat',state:'draft',revision:2,context_count:1,turn_count:2,tags:['CUSTOMER_TAG'],updated_at:'2026-11-14T01:00:00Z'};
function chatRaw(items=[],create=true){
  return{chatWorkspaceEnabled:true,capabilities:{'chat-workspace-view':true,'chat-thread-create':create},chatThreads:items,chatWorkspaceSummary:{threads:{total:7,review:2,ready:3}},chatWorkspaceListing:{state:'review',q:'CUSTOMER_QUERY',pagination:{total:60,limit:20,returned:items.length,offset:0,has_more:true,next_offset:20,previous_offset:null}}};
}
const controls=html=>[...html.matchAll(/<(?:a|button|input|form|select|textarea|option)\b[^>]*>/g)].map(m=>m[0].replace(/placeholder="[^"]*"/g,'placeholder="__TEXT__"'));
function segment(html,start,end){const a=html.indexOf(start),b=html.indexOf(end,a);assert.ok(a>=0&&b>a,start);return html.slice(a,b);}
function authored(html){
  const intro=segment(html,'<section class="portal-chat-workspace-intro">','<section class="portal-card portal-card-pad portal-chat-workspace-create">');
  const create=segment(html,'<section class="portal-card portal-card-pad portal-chat-workspace-create">','<section class="portal-card portal-card-pad"><div class="portal-card-header">');
  const library=html.slice(html.indexOf('<section class="portal-card portal-card-pad"><div class="portal-card-header">'));
  return{intro,create,library};
}
function finiteChat(html){
  // Only positions owned by these specs; no arbitrary/customer-node rewriting.
  const parts=authored(html);
  let intro=parts.intro.replace(/(<span class="portal-section-kicker">)[^<]+/,'$1__KICKER__').replace(/(<h2>)[^<]+/,'$1__TITLE__').replace(/(<p>)[^<]+/,'$1__BODY__').replace(/(<dd>)[^<]+/g,'$1__COUNT_LABEL__');
  let create=parts.create.replace(/(<span class="portal-section-kicker">)[^<]+/,'$1__KICKER__').replace(/(<h2 class="portal-card-title">)[^<]+/,'$1__TITLE__').replace(/(<p class="portal-card-subtitle">)[^<]+/,'$1__BODY__').replace(/(<span class="portal-form-note">)[^<]+/,'$1__HINT__').replace(/(<button class="portal-button portal-button--primary" type="submit"[^>]*>)[^<]+/,'$1__SUBMIT__');
  let library=parts.library.replace(/(<span class="portal-section-kicker">)[^<]+/,'$1__KICKER__').replace(/(<h2 class="portal-card-title">)[^<]+/,'$1__TITLE__').replace(/(<p class="portal-card-subtitle">)[^<]+/,'$1__BODY__').replace(/(<button[^>]+data-portal-action="chat-workspace-refresh"[^>]*>)[^<]+/,'$1__REFRESH__').replace(/(<span class="portal-form-note">)[^<]+/,'$1__HINT__').replace(/(<button class="portal-button portal-button--quiet" type="submit"[^>]*>)[^<]+/,'$1__APPLY__');
  const filter=segment(library,'<form class="portal-form portal-chat-workspace-filters"','</form>')+'</form>';
  let normalizedFilter=filter.replace(/(<label\b[^>]*>)[^<]+/g,'$1__FILTER_LABEL__').replace(/placeholder="[^"]*"/g,'placeholder="__PLACEHOLDER__"').replace(/(<option\b[^>]*>)[^<]+/g,'$1__OPTION_LABEL__');
  library=library.replace(filter,normalizedFilter);
  library=library.replace(/(<div class="portal-empty"[\s\S]*?<h3>)[^<]+(<\/h3><p>)[^<]+/,'$1__EMPTY_TITLE__$2__EMPTY_BODY__');
  return html.replace(parts.intro,intro).replace(parts.create,create).replace(parts.library,library);
}
for(const locale of locales)for(const items of [[],[thread]])for(const create of [false,true])test(`${locale}/chat/items${items.length}/create${create}: finite copy localized, controls/data and other output exact`,()=>{
  const raw=chatRaw(items,create),saved=JSON.stringify(raw),a=current(locale,'/chat',raw),b=base(locale,'/chat',structuredClone(raw));
  assert.equal(JSON.stringify(raw),saved);assert.equal(JSON.stringify(a.context),JSON.stringify(b.context));
  assert.deepEqual(controls(a.html),controls(b.html),'form contracts and real permissions unchanged');
  assert.equal(finiteChat(a.html),finiteChat(b.html),'all non-finite markup/data unchanged');
  const bits=authored(a.html),copy=[text(bits.intro)];
  const dict=a.messages[locale];
  for(const prefix of ['chatRootUi','chatFilterUi']){
    const rows=Object.entries(dict).filter(([key])=>key.startsWith(prefix));
    assert.equal(rows.length,prefix==='chatRootUi'?19:8);
    for(const [key,value]of rows){assert.ok(language(value,locale),key);assert.doesNotMatch(value,technical,key);}
  }
  for(const key of ['chatRootUiIntroTitle','chatRootUiCreateTitle','chatRootUiLibraryTitle','chatFilterUiSearchPlaceholder','chatFilterUiReview']){
    assert.ok(a.html.includes(esc(dict[key])),key+' used by actual root consumer');
  }
  assert.equal(bits.intro.match(/<dt>/g)?.length,3);
  assert.ok(copy[0].includes('7')&&copy[0].includes('2')&&copy[0].includes('3'),'counts retained');
  if(items.length)assert.ok(a.html.includes(esc(thread.title)),'customer jargon/content retained');
  else for(const key of ['chatRootUiEmptyTitle','chatRootUiEmptyBody'])assert.ok(a.html.includes(esc(dict[key])));
});
for(const locale of locales)for(const route of ['/documents','/documents/pdf'])for(const state of ['loading','failed','ready'])for(const refresh of [false,true])test(`${locale}${route}/${state}/refresh${refresh}: real loading/error/retry states remain, only five visible texts change`,()=>{
  const raw={capabilities:{'document-operation-view':true,'document-operation-refresh':refresh},documentOperationsReadState:state,documentOperations:[]},a=current(locale,route,raw),b=base(locale,route,structuredClone(raw));
  assert.deepEqual(controls(a.html),controls(b.html));assert.equal(JSON.stringify(a.context),JSON.stringify(b.context));
  if(state==='ready'){assert.equal(a.html,b.html);return;}
  const pattern=/(<h2>)([^<]+)(<\/h2><p>)([^<]+)(<\/p>)/;
  const m=pattern.exec(a.html),n=pattern.exec(b.html);assert.ok(m&&n);
  assert.ok(language(text(m[2]+' '+m[4]),locale));assert.doesNotMatch(text(m[2]+' '+m[4]),technical);
  let actual=a.html.replace(pattern,'$1__HEADING__$3__BODY__$5'),expected=b.html.replace(pattern,'$1__HEADING__$3__BODY__$5');
  if(state==='failed'&&refresh){
    const retry=/(data-portal-action="document-operation-refresh"[^>]*>)[^<]+/;
    actual=actual.replace(retry,'$1__RETRY__');expected=expected.replace(retry,'$1__RETRY__');
    assert.ok(a.html.includes(esc(a.messages[locale].docReadUiRetryButton)));
  }
  assert.equal(actual,expected,'hidden metadata, guards, retry and other output unchanged');
});
for(const locale of locales)test(`${locale}: exactly 32 finite additions, existing dictionary values/order and unrelated detail/customer data unchanged`,()=>{
  const a=current(locale,'/chat',{}),b=base(locale,'/chat',{});
  const entries=Object.entries(a.messages[locale]),oldEntries=Object.entries(b.messages[locale]);
  const added=entries.filter(([key])=>!Object.hasOwn(b.messages[locale],key));
  assert.equal(added.length,32);
  for(const [prefix,count]of [['chatRootUi',19],['chatFilterUi',8],['docReadUi',5]])assert.equal(added.filter(([key])=>key.startsWith(prefix)).length,count);
  assert.deepEqual(entries.filter(([key])=>Object.hasOwn(b.messages[locale],key)),oldEntries);
  const route='/chat/'+thread.id,raw={capabilities:{'chat-workspace-view':true},chatThreadDetail:{thread,contexts:[],turns:[],versions:[],events:[]}};
  const actual=current(locale,route,raw),expected=base(locale,route,structuredClone(raw));
  assert.equal(actual.html,expected.html);assert.equal(actual.title,expected.title);
});
test('Vietnamese safety copy retains all rejected-input categories in customer language',()=>{
  const x=current('vi','/chat',chatRaw()).messages.vi;
  assert.match(x.chatRootUiCreateSafetyHint,/liên kết/);
  for(const category of [/đường dẫn/,/nội dung tệp/,/mật khẩu/,/mã đăng nhập/,/mã bảo mật thẻ/,/mã giao dịch/,/mã yêu cầu/])assert.match(x.chatRootUiCreateSafetyHint,category);
  assert.match(x.chatRootUiIntroBody,/không trừ Xu/);assert.match(x.chatRootUiCreateSubtitle,/không trừ Xu/);
});
for(const locale of locales)test(`${locale}: historical adapter accepts only exact reviewed entries/positions and retains unknown/customer values`,()=>{
  const raw=chatRaw([thread]),a=current(locale,'/chat',raw),b=base(locale,'/chat',structuredClone(raw));
  const entries=Object.entries(a.messages[locale]),saved=JSON.stringify(entries),old=Object.entries(b.messages[locale]);
  assert.deepEqual(chatRootDocReadHistoricalSnapshot(entries,locale),old);assert.equal(JSON.stringify(entries),saved);
  for(const [key]of entries.filter(([key])=>/^(chatRootUi|chatFilterUi|docReadUi)/.test(key))){
    const changed=entries.map(([k,v])=>[k,k===key?'UNREVIEWED_MUTATION':v]);
    assert.throws(()=>chatRootDocReadHistoricalSnapshot(changed,locale),/Unreviewed root\/read copy/);
  }
  const unknown=[...entries,['unknown.customer.key','CUSTOMER_TEXT']];
  assert.deepEqual(chatRootDocReadHistoricalSnapshot(unknown,locale).at(-1),['unknown.customer.key','CUSTOMER_TEXT']);
  assert.equal(chatRootDocReadHistoricalMarkup(a.html,locale,a.messages[locale]),b.html);
  assert.ok(a.html.includes(esc(thread.title)));
});
