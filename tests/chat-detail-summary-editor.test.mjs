import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {summaryRenderer,summarySources} from './helpers/chat-detail-summary-editor-runtime.mjs';
import {summaryHistoricalSnapshot,summaryHistoricalPortalSource} from './helpers/chat-detail-summary-editor-snapshot.mjs';
const source=summarySources(),oldSource=summarySources(true),current=await summaryRenderer(source),before=await summaryRenderer(oldSource);
const approved=JSON.parse(fs.readFileSync(new URL('./fixtures/chat-detail-summary-editor-reviewed.json',import.meta.url),'utf8'));
const cards=JSON.parse(fs.readFileSync(new URL('./fixtures/chat-cards-customer-copy-reviewed.json',import.meta.url),'utf8'));
const id='11111111-1111-4111-8111-111111111111',route='/chat/'+id;
const literal='CUSTOMER Thread chưa khả dụng · Thread editor · Revision <script>alert("Bot")</script>&';
const thread={id,title:literal,objective:literal,objective_excerpt:'CUSTOMER_EXCERPT',tags:['Thread editor','Revision','Bot','provider'],revision:7,context_count:7,turn_count:11,state:'draft',mode:'focus',pinned:true};
const raw={chatWorkspaceEnabled:true,capabilities:{'chat-workspace-view':true,'chat-thread-update':true,'chat-thread-lifecycle':true},chatThreadDetail:{thread,contexts:[],turns:[],versions:[],events:[]}};
const sessions=Object.fromEntries(['vi','en','zh'].map(locale=>[locale,{now:current(locale,route,raw),old:before(locale,route,raw)}]));
const tags=html=>[...html.matchAll(/<[^>]+>/g)].map(m=>m[0]);
function detail(session,value,caps={}){
  const context={...session.context,capabilities:{...session.context.capabilities,...caps},chatThreadDetail:{...session.context.chatThreadDetail,thread:value}},saved=JSON.stringify(context);
  const html=session.qa.renderChatWorkspaceDetail(session.page,context);assert.equal(JSON.stringify(context),saved);return html;
}
const summary=html=>{const m=/<section class="portal-chat-thread-summary">[\s\S]*?<\/section>/.exec(html);assert.ok(m);return m[0];};
function editor(html){
  const at=html.indexOf('data-portal-action="chat-thread-update"'),a=html.lastIndexOf('<section class="portal-card portal-card-pad">',at),b=html.indexOf('</form></section>',at);
  assert.ok(at>=0&&a>=0&&b>a);return html.slice(a,b+17);
}
for(const locale of ['vi','en','zh']){
  const {now,old}=sessions[locale],copy=approved[locale],c=cards[locale];
  test(`${locale}: denied/missing/invalid details keep the original guard and useful localized backlink`,()=>{
    for(const [value,caps]of [[thread,{'chat-workspace-view':false}],[thread,{'chat-workspace-view':'true'}],[null,{}],[undefined,{}],[{...thread,id:'INVALID'},{}],[{...thread,id:'"><script>x</script>'},{}]]){
      const html=detail(now,value,caps),prior=detail(old,value,caps);
      assert.deepEqual(tags(html),tags(prior));
      for(const key of ['AccessTitle','AccessBody','Back'])assert.ok(html.includes(now.qa.safeText(copy['chatDetailSummaryUi'+key])));
      assert.ok(html.includes('href="/chat"'));assert.equal(html.includes('data-portal-action="chat-thread-update"'),false);
    }
  });
  test(`${locale}: summary states/modes/pinned and real metadata retain exact structure and numeric semantics`,()=>{
    for(const state of ['draft','review','ready','archived','UNKNOWN'])for(const mode of ['focus','deep','pro','DEEP'])for(const pinned of [false,true]){
      const value={...thread,state,mode,pinned},html=summary(detail(now,value)),prior=summary(detail(old,value));
      assert.deepEqual(tags(html),tags(prior));
      const normalized=now.qa.chatWorkspaceState(state),stateKey=normalized[0].toUpperCase()+normalized.slice(1),modeKey=mode==='deep'?'Deep':mode==='pro'?'Pro':'Focus';
      assert.ok(html.includes(now.qa.safeText(c['chatCardsUiMode'+modeKey])+(pinned?' · '+now.qa.safeText(c.chatCardsUiPinned):'')));
      const values=[...html.matchAll(/<dd>([\s\S]*?)<\/dd>/g)].map(m=>m[1]);
      assert.deepEqual(values,[now.qa.safeText(c['chatCardsUiState'+stateKey]),'7','7 / 11']);
      for(const key of ['State','Update','Counts'])assert.ok(html.includes('<dt>'+now.qa.safeText(copy['chatDetailSummaryUi'+key])+'</dt>'));
    }
  });
  test(`${locale}: summary fallback/coercion does not alter customer literals or hide technical words in data`,()=>{
    for(const extra of [{title:'',objective:'',objective_excerpt:'',revision:0,context_count:0,turn_count:0},{revision:'09',context_count:'7',turn_count:'11'},{revision:'<7>',context_count:'INVALID',turn_count:-2,mode:null}]){
      const value={...thread,...extra},html=summary(detail(now,value));
      assert.ok(html.includes('<dd>'+now.qa.safeText(String(value.revision||1))+'</dd>'));
      assert.ok(html.includes(now.qa.safeText(String(Number(value.context_count||0)))+' / '+now.qa.safeText(String(Number(value.turn_count||0)))));
      assert.ok(html.includes(now.qa.safeText(String(value.title||c.chatCardsUiTitleFallback))));
      assert.ok(html.includes(now.qa.safeText(String(value.objective||value.objective_excerpt||c.chatCardsUiObjectiveFallback))));
    }
    const html=summary(detail(now,thread));assert.ok(html.includes(now.qa.safeText(literal)));assert.equal(html.includes('<script>'),false);
    assert.ok(html.includes('Thread editor'));assert.ok(html.includes('Revision'));
  });
  test(`${locale}: editor copy and badge retain fields/lifecycle controls and strict write gates`,()=>{
    for(const state of ['draft','review','ready','archived','UNKNOWN'])for(const capability of [true,false,'true',undefined]){
      const value={...thread,state},caps={'chat-thread-update':capability,'chat-thread-lifecycle':capability},html=editor(detail(now,value,caps)),prior=editor(detail(old,value,caps));
      assert.deepEqual(tags(html),tags(prior));
      for(const [key,text]of Object.entries(copy).filter(([key])=>key.startsWith('chatDetailEditorUi')))assert.ok(html.includes(now.qa.safeText(text)),key);
      const normalized=now.qa.chatWorkspaceState(state),key=normalized[0].toUpperCase()+normalized.slice(1);
      assert.ok(html.includes('<span class="portal-badge" data-status="'+normalized+'">'+now.qa.safeText(c['chatCardsUiState'+key])+'</span>'));
      const submit=/<button class="portal-button portal-button--primary" type="submit"([^>]*)>/.exec(html);assert.ok(submit);
      assert.equal(submit[1].includes('disabled'),!(capability===true&&normalized==='draft'));
    }
  });
  test(`${locale}: active language changes per render and translated text is escaped exactly once`,()=>{
    const next=locale==='vi'?'en':locale==='en'?'zh':'vi';
    try{now.setLocale(next);assert.ok(summary(detail(now,thread)).includes(now.qa.safeText(approved[next].chatDetailSummaryUiCounts)));assert.ok(editor(detail(now,thread)).includes(now.qa.safeText(approved[next].chatDetailEditorUiTitle)));}finally{now.setLocale(locale);}
    const hostile='<img src=x onerror="alert(1)"> \'&';
    const html=now.qa.withUiText(()=>hostile,()=>detail(now,thread));
    assert.equal(html.includes('<img'),false);assert.ok(html.includes(now.qa.safeText(hostile)));assert.equal(html.includes('&amp;lt;img'),false);
  });
  test(`${locale}: exactly 11 new entries, every prior value/order and frozen dictionary remain`,()=>{
    const a=Object.entries(now.messages[locale]),b=Object.entries(old.messages[locale]);
    assert.deepEqual(JSON.parse(JSON.stringify(a.slice(0,b.length))),JSON.parse(JSON.stringify(b)));
    assert.deepEqual(JSON.parse(JSON.stringify(a.slice(b.length))),Object.entries(copy));assert.ok(Object.isFrozen(now.messages[locale]));
  });
  test(`${locale}: strict adapter rejects missing/mutated/reordered entries and preserves unknown customer keys`,()=>{
    const entries=Object.entries(now.messages[locale]),normalized=summaryHistoricalSnapshot(entries,locale);assert.equal(normalized.length,entries.length-11);
    for(const key of Object.keys(copy)){
      assert.throws(()=>summaryHistoricalSnapshot(entries.filter(([k])=>k!==key),locale),/Unreviewed Chat summary\/editor copy/);
      assert.throws(()=>summaryHistoricalSnapshot(entries.map(([k,v])=>[k,k===key?'UNKNOWN':v]),locale),/Unreviewed Chat summary\/editor copy/);
    }
    assert.throws(()=>summaryHistoricalSnapshot([...normalized,...Object.entries(copy).toReversed()],locale),/Unreviewed Chat summary\/editor copy/);
    const unknown=['chatDetailSummaryUiUnknown',literal];assert.deepEqual(summaryHistoricalSnapshot([...entries,unknown],locale).at(-1),unknown);
  });
}
test('whole reviewed detail scope normalizes only exact accepted source, retaining outside mutations',()=>{
  assert.ok(source.portal!==oldSource.portal);assert.equal(summaryHistoricalPortalSource(source.portal),oldSource.portal);
  const a=source.portal.indexOf('  function renderChatWorkspaceDetail(page, context) {'),b=source.portal.indexOf('\n  // Analytics Workspace',a),part=source.portal.slice(a,b);
  assert.ok(part.includes('const writable = state === "draft";'));
  assert.throws(()=>summaryHistoricalPortalSource(source.portal.slice(0,a)+part.replace('const writable = state === "draft";','const writable = true;')+source.portal.slice(b)),/Unreviewed Chat summary\/editor source/);
  assert.ok(summaryHistoricalPortalSource(source.portal+'\n// UNKNOWN_SOURCE').endsWith('// UNKNOWN_SOURCE'));
});
