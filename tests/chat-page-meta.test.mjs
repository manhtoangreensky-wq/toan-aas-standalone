import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {createHash} from 'node:crypto';
import {pageMetaRenderer,pageMetaSources} from './helpers/chat-page-meta-runtime.mjs';
import {pageMetaHistoricalSnapshot,pageMetaHistoricalPortalSource,pageMetaFragments} from './helpers/chat-page-meta-snapshot.mjs';
import {chatDateHistoricalPortalSource} from './helpers/chat-date-snapshot.mjs';
import {documentCardHistoricalSnapshot,documentCardHistoricalI18nSource} from './helpers/document-card-copy-snapshot.mjs';
import {pdfSplitMetaHistoricalPagesSource} from './helpers/pdf-split-meta-snapshot.mjs';
const live=pageMetaSources(),source={...live,portal:chatDateHistoricalPortalSource(live.portal),i18n:documentCardHistoricalI18nSource(live.i18n),pages:pdfSplitMetaHistoricalPagesSource(live.pages)},baseline=pageMetaSources(true);
const actual=await pageMetaRenderer(source),before=await pageMetaRenderer(baseline);
const current=(...args)=>{
  const result=actual(...args);
  return {...result,catalogFrozen:Object.fromEntries(['vi','en','zh'].map(locale=>[locale,Object.isFrozen(result.messages[locale])])),messages:Object.fromEntries(['vi','en','zh'].map(locale=>[
    locale,Object.fromEntries(documentCardHistoricalSnapshot(Object.entries(result.messages[locale]),locale))
  ]))};
};
const copy=JSON.parse(fs.readFileSync(new URL('./fixtures/chat-page-meta-reviewed.json',import.meta.url),'utf8'));
const id='11111111-1111-4111-8111-111111111111',detail='/chat/'+id;
const customerTitles=['AI Chat Workspace','Trò chuyện','Chat','对话','AI Chat Workspace · Trò chuyện · Chat · 对话 <script>alert("x")</script> Facebook TikTok'];
const thread=title=>({id,revision:7,state:'draft',mode:'focus',title,objective:'CUSTOMER Facebook TikTok <script>literal</script>',tags:['AI Chat Workspace','Trò chuyện','Chat','对话','Facebook','TikTok']});
const raw=title=>({chatWorkspaceEnabled:true,capabilities:{'chat-workspace-view':true,'chat-thread-update':true,'chat-context-create':true,'chat-turn-create':true},chatThreadDetail:{thread:thread(title),contexts:[],turns:[],versions:[],events:[]}});
const sessions=Object.fromEntries(['vi','en','zh'].map(locale=>[locale,Object.fromEntries(['/chat',detail].map(route=>[route,{now:current(locale,route,raw(customerTitles[4])),old:before(locale,route,raw(customerTitles[4]))}]))]));
const esc=(session,value)=>session.qa.safeText(String(value));
const hash=value=>createHash('sha256').update(value).digest('hex');
const controls=html=>[...html.matchAll(/<(?:form|button|input|textarea|select|option|a)\b[^>]*>/g)].map(match=>match[0]);
const extract=(html,expression)=>{const match=expression.exec(html);assert.ok(match,'Actual metadata consumer must remain');return match[1];};
function render(session,changes={}){
  const page=session.qa.resolvePage(session.route),context={...session.context,...changes},saved=JSON.stringify(context),registry=JSON.stringify(page);
  const result={html:session.qa.renderPage(page,context),header:session.qa.renderHeader(page,context),title:session.qa.documentTitle(page,context),pageTitle:session.qa.localizedPageTitle(page,context),description:session.qa.localizedPageDescription(page),section:session.qa.supportTicketHeroSection(page),page,context};
  assert.equal(JSON.stringify(context),saved);assert.equal(JSON.stringify(page),registry);return result;
}
function checkFixed(session,value,locale){
  const expected=copy[locale],title=expected.chatPageMetaUiTitle,description=expected.chatPageMetaUiDescription;
  assert.equal(value.pageTitle,title);assert.equal(value.description,description);assert.equal(value.title,title+' · TOAN AAS');
  assert.equal(extract(value.html,/<h1 class="portal-title">([\s\S]*?)<\/h1>/),esc(session,title));
  assert.equal(extract(value.html,/<p class="portal-description">([\s\S]*?)<\/p>/),esc(session,description));
  const crumb=extract(value.header,/<nav class="portal-crumbs"[^>]*>([\s\S]*?)<\/nav>/);
  assert.ok(crumb.includes('<span aria-current="page">'+esc(session,title)+'</span>'));
  if(value.page.layout==='chat-workspace-detail'){
    assert.equal(value.section,title);assert.equal(extract(value.html,/<div class="portal-eyebrow">([\s\S]*?)<\/div>/),esc(session,title));
    assert.equal((crumb.match(/<span/g)||[]).length,2,'Actual de-duplication must retain the brand and one localized detail label');
  }
}
for(const locale of ['vi','en','zh']){
  test(`${locale}: actual root/detail h1, description, tab, detail section and header ignore fixed server titles`,()=>{
    for(const route of ['/chat',detail]){
      const {now,old}=sessions[locale][route],registry=JSON.stringify(now.page);
      assert.equal(JSON.stringify(now.page),JSON.stringify(old.page),'Raw registry metadata is not rewritten');
      for(const title of [undefined,'','TOAN AAS Workspace','AI Chat Workspace','FIXED ENGLISH SERVER TITLE','Chat · TOAN AAS']){
        const a=render(now,{title}),b=render(old,{title});checkFixed(now,a,locale);assert.deepEqual(controls(a.html),controls(b.html));assert.deepEqual(controls(a.header),controls(b.header));assert.equal(JSON.stringify(a.context),JSON.stringify(b.context));
      }
      assert.equal(JSON.stringify(now.page),registry);
    }
  });
  test(`${locale}: customer names identical to all product labels, tags and actual form values stay literal`,()=>{
    for(const title of customerTitles){
      const now=current(locale,detail,raw(title)),old=before(locale,detail,raw(title)),a=render(now),b=render(old);checkFixed(now,a,locale);
      assert.ok(a.html.includes('<h2>'+esc(now,title)+'</h2>'));assert.ok(a.html.includes('value="'+esc(now,title)+'"'));
      for(const tag of thread(title).tags)assert.ok(a.html.includes('<span>'+esc(now,tag)+'</span>'));
      assert.deepEqual(controls(a.html),controls(b.html));assert.equal(JSON.stringify(a.context),JSON.stringify(b.context));assert.equal(a.html.includes('<script>'),false);
    }
  });
  test(`${locale}: SAME VM session re-renders locale, full VI fallback and each metadata insertion escapes once`,()=>{
    const {now}=sessions[locale][detail],next=locale==='vi'?'en':locale==='en'?'zh':'vi';
    try{now.setLocale(next);checkFixed(now,render(now),next);}finally{now.setLocale(locale);}
    for(const route of ['/chat',detail]){
      const session=sessions[locale][route].now,fallback=session.qa.withUiText((key,value)=>value,()=>render(session));checkFixed(session,fallback,'vi');
      const hostile='<img src=x onerror="alert(1)"> \'&',value=session.qa.withUiText((key,fallback)=>key.startsWith('chatPageMetaUi')?hostile:fallback,()=>render(session));
      assert.equal(extract(value.html,/<h1 class="portal-title">([\s\S]*?)<\/h1>/),esc(session,hostile));
      assert.equal(extract(value.html,/<p class="portal-description">([\s\S]*?)<\/p>/),esc(session,hostile));
      const crumb=extract(value.header,/<nav class="portal-crumbs"[^>]*>([\s\S]*?)<\/nav>/);assert.ok(crumb.includes('<span aria-current="page">'+esc(session,hostile)+'</span>'));assert.equal(crumb.includes('&amp;lt;img'),false);
      if(route===detail)assert.equal(extract(value.html,/<div class="portal-eyebrow">([\s\S]*?)<\/div>/),esc(session,hostile));
    }
  });
  test(`${locale}: exact new pair, prior catalog order/values/freeze, broader workspace labels and legacy routes remain`,()=>{
    const {now,old}=sessions[locale][detail],entries=Object.entries(now.messages[locale]),prior=Object.entries(old.messages[locale]);assert.equal(now.catalogFrozen[locale],true);
    assert.deepEqual(JSON.parse(JSON.stringify(entries.slice(0,prior.length))),JSON.parse(JSON.stringify(prior)));assert.deepEqual(JSON.parse(JSON.stringify(entries.slice(prior.length))),Object.entries(copy[locale]));
    for(const suffix of ['title','description'])assert.equal(now.messages[locale]['workspaceMenu.card.chat_workspace.'+suffix],old.messages[locale]['workspaceMenu.card.chat_workspace.'+suffix]);
    assert.deepEqual(JSON.parse(JSON.stringify(pageMetaHistoricalSnapshot(entries,locale))),JSON.parse(JSON.stringify(prior)));
    for(const key of Object.keys(copy[locale])){
      assert.throws(()=>pageMetaHistoricalSnapshot(entries.filter(([name])=>name!==key),locale),/Unreviewed Chat page metadata copy/);
      assert.throws(()=>pageMetaHistoricalSnapshot(entries.map(([name,value])=>[name,name===key?'UNREVIEWED':value]),locale),/Unreviewed Chat page metadata copy/);
    }
    assert.throws(()=>pageMetaHistoricalSnapshot([...prior,...Object.entries(copy[locale]).toReversed()],locale),/Unreviewed Chat page metadata copy/);
    assert.throws(()=>pageMetaHistoricalSnapshot([...entries,['chatPageMetaUiUnknown','UNKNOWN']],locale),/Unreviewed Chat page metadata copy/);
    const customer=['customer.literal',customerTitles[4]];assert.deepEqual(pageMetaHistoricalSnapshot([...entries,customer],locale).at(-1),customer);
    for(const route of ['/chat/new','/chat/not-a-uuid','/documents']){
      const a=render(current(locale,route,raw(customerTitles[4]))),b=render(before(locale,route,raw(customerTitles[4])));
      for(const key of ['html','header','title','pageTitle','description','section'])assert.equal(a[key],b[key],'Actual unchanged sentinel '+route+'/'+key);
      assert.equal(JSON.stringify(a.page),JSON.stringify(b.page));assert.equal(JSON.stringify(a.context),JSON.stringify(b.context));
    }
    // The existing system catalogue card consumes these same fixed metadata
    // helpers. Admit only its two reviewed text nodes, not a whole-page mask.
    const catalogNow=current(locale,'/features/content',raw(customerTitles[4])),catalogOld=before(locale,'/features/content',raw(customerTitles[4]));
    const a=render(catalogNow),b=render(catalogOld),marker='<a class="portal-module-card" href="/chat">';
    const card=html=>{assert.equal(html.split(marker).length-1,1);const start=html.indexOf(marker),end=html.indexOf('</a>',start);assert.ok(end>start);return html.slice(start,end+4);};
    const nextCard=card(a.html),priorCard=card(b.html);let projected=nextCard;
    for(const[tag,key,oldKey]of[['h3','chatPageMetaUiTitle','workspaceMenu.card.chat_workspace.title'],['p','chatPageMetaUiDescription','workspaceMenu.card.chat_workspace.description']]){
      const next='<'+tag+'>'+esc(catalogNow,copy[locale][key])+'</'+tag+'>',prior='<'+tag+'>'+esc(catalogOld,catalogOld.messages[locale][oldKey])+'</'+tag+'>';
      assert.equal(projected.split(next).length-1,1);assert.equal(priorCard.split(prior).length-1,1);projected=projected.replace(next,prior);
    }
    assert.equal(projected,priorCard);assert.equal(a.html.replace(nextCard,projected),b.html);
    for(const key of ['header','title','pageTitle','description','section'])assert.equal(a[key],b[key],'Containing catalogue metadata remains unchanged');
    assert.equal(JSON.stringify(a.page),JSON.stringify(b.page));assert.equal(JSON.stringify(a.context),JSON.stringify(b.context));
  });
}
test('only all four reviewed source fragments normalize; unknown/partial edits and outside changes remain detectable',()=>{
  assert.equal(pageMetaHistoricalPortalSource(source.portal),baseline.portal);assert.equal(pageMetaHistoricalPortalSource(baseline.portal),baseline.portal);
  for(const edit of pageMetaFragments){
    assert.equal(baseline.portal.split(edit.old).length-1,1);assert.equal(hash(edit.old),edit.oldHash);
    assert.equal(source.portal.split(edit.new).length-1,1);assert.equal(hash(edit.new),edit.newHash);
    assert.throws(()=>pageMetaHistoricalPortalSource(source.portal.replace(edit.new,edit.old)),/Unreviewed Chat page metadata source/);
    assert.throws(()=>pageMetaHistoricalPortalSource(source.portal.replace(edit.new,edit.new.replace('chatPageMetaUi','UNREVIEWED'))),/Unreviewed Chat page metadata source/);
    assert.throws(()=>pageMetaHistoricalPortalSource(source.portal+'\n'+edit.new),/Unreviewed Chat page metadata source/);
  }
  const outside=source.portal+'\n// CUSTOMER AI Chat Workspace Facebook TikTok';assert.notEqual(pageMetaHistoricalPortalSource(outside),baseline.portal);assert.ok(pageMetaHistoricalPortalSource(outside).endsWith('Facebook TikTok'));
});
test('all three complete app files match the fixed seven-change contract; no unrelated portal/catalog/shell edit is normalized',()=>{
  for(const [key,expected]of Object.entries({portal:'d0ef279f5e464291c82d0fd7e23cb199921f605396782750fd6b64e87b04eec9',i18n:'a0a13408366575416d3ab8912ef5ec1889fab2bae69f282b89d2367416b092ab',pages:'d1baa0dc1faf5d130ab3e28ef44bde469da3aa078fa5be45529e374c87c59deb'}))assert.equal(hash(source[key]),expected,'Reviewed complete '+key+' source');
  assert.equal(hash(baseline.portal),'cf58e785c5fd4aba5d99cabfacadaef531dd04496139a7f04fced3917a5c1d89');assert.equal(hash(baseline.i18n),'5cee49a7507584eb057970b2f19977bbb4cf88400089754d03320c6349f3e52d');assert.equal(hash(baseline.pages),'5a170e976c16ff718ed9cf0e6f89986726e8f27fa26e73094339387a1e6588da');
});
