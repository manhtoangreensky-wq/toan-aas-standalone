import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {chatCardsSources,chatCardsRenderer} from './helpers/chat-cards-customer-runtime.mjs';
import {chatCardsHistoricalSnapshot,chatCardsHistoricalPortalSource} from './helpers/chat-cards-customer-snapshot.mjs';
import {datePagesHistoricalSnapshot,datePagesHistoricalPortalSource} from './helpers/chat-dates-pages-snapshot.mjs';

// Catches missing translation, lost customer data/controls, false execution
// promises, a retained technical aside, and silently normalized regressions.
const expected=JSON.parse(fs.readFileSync(new URL('./fixtures/chat-cards-customer-copy-reviewed.json',import.meta.url),'utf8'));
const live=chatCardsSources(),sources={...live,portal:datePagesHistoricalPortalSource(live.portal)},oldSources=chatCardsSources(true);
const currentRender=await chatCardsRenderer(sources),before=await chatCardsRenderer(oldSources);
const current=(...args)=>{
  const result=currentRender(...args);
  return {...result,catalogFrozen:Object.fromEntries(['vi','en','zh'].map(locale=>[locale,Object.isFrozen(result.messages[locale])])),messages:Object.fromEntries(['vi','en','zh'].map(locale=>[
    locale,Object.fromEntries(datePagesHistoricalSnapshot(Object.entries(result.messages[locale]),locale))
  ]))};
};
const id='11111111-1111-4111-8111-111111111111';
const item=(extra={})=>({id,state:'draft',mode:'focus',title:'CUSTOMER_TITLE',objective_excerpt:'CUSTOMER_GOAL',tags:['CUSTOMER_TAG'],context_count:7,turn_count:11,revision:9,updated_at:'2026-11-14T08:09:10Z',...extra});
const raw=(extra={})=>({capabilities:{'chat-workspace-view':true,'chat-thread-create':true,'chat-run-submit':false,'chat-run-refresh':true},chatWorkspaceEnabled:true,chatThreads:[item()],chatThreadDetail:{thread:item(),contexts:[],turns:[],versions:[],events:[]},...extra});
const attrs=html=>[...html.matchAll(/<[^>]+>/g)].map(m=>m[0]);
const sessions=Object.fromEntries(['vi','en','zh'].map(locale=>[locale,{now:current(locale,'/chat',raw()),old:before(locale,'/chat',raw())}]));
test('root/detail lose only the redundant aside; actual execution controls and other markup remain',()=>{
  for(const route of ['/chat','/chat/'+id]){
    const a=current('vi',route,raw()),b=before('vi',route,raw());
    assert.equal(a.html.includes('portal-chat-workspace-boundary'),false);
    const mask=html=>html.replace(/<aside class="portal-card portal-card-pad portal-chat-workspace-boundary">[\s\S]*?<\/aside>/g,'').replace(/<div class="portal-chat-workspace-grid">[\s\S]*?<\/article><\/div>/g,'__CARDS__');
    assert.equal(mask(a.html),mask(b.html));
    assert.equal(a.qa.renderChatExecutionPanel(item(),a.context,route),b.qa.renderChatExecutionPanel(item(),b.context,route));
  }
});
for(const locale of ['vi','en','zh']){
  const e=expected[locale],{now,old}=sessions[locale];
  const cards=(items,ctx=now.context)=>now.qa.renderChatWorkspaceCards(items,ctx);
  test(`${locale}: exactly 20 approved keys, old values/order and freeze remain`,()=>{
    const a=Object.entries(now.messages[locale]),b=Object.entries(old.messages[locale]);
    assert.deepEqual(JSON.parse(JSON.stringify(a.slice(0,b.length))),JSON.parse(JSON.stringify(b)));
    assert.deepEqual(JSON.parse(JSON.stringify(a.slice(b.length))),Object.entries(e));
    assert.equal(now.catalogFrozen[locale],true,'actual runtime catalog must remain frozen before historical projection');
  });
  test(`${locale}: real empty renderer gives useful localized guidance`,()=>{
    const html=cards([]);assert.ok(html.includes(e.chatCardsUiEmptyTitle));assert.ok(html.includes(e.chatCardsUiEmptyBody));
  });
  for(const state of ['draft','review','ready','archived','guarded'])test(`${locale}/${state}: modes, pinned, real numbers, badge and links retain contracts`,()=>{
    const records=['focus','deep','pro','UNKNOWN'].map((mode,k)=>item({state,mode,pinned:k%2===0,title:'TITLE_'+k}));
    const saved=JSON.stringify(records),html=cards(records),prior=old.qa.renderChatWorkspaceCards(records,old.context);
    assert.equal(JSON.stringify(records),saved);assert.deepEqual(attrs(html),attrs(prior));
    for(const key of ['ModeFocus','ModeDeep','ModePro'])assert.ok(html.includes(e['chatCardsUi'+key]));
    assert.ok(html.includes(' · '+e.chatCardsUiPinned));
    assert.ok(html.includes(e.chatCardsUiNotes+': 7 · '+e.chatCardsUiTurns+': 11'));
    assert.ok(html.includes(e.chatCardsUiUpdate+' 9'));assert.ok(html.includes('2026-11-14T08:09:10Z'));
    assert.ok(html.includes('data-status="'+state+'">'+e['chatCardsUiState'+state[0].toUpperCase()+state.slice(1)]));
    assert.ok(html.includes(e[state==='ready'?'chatCardsUiReadyNote':state==='archived'?'chatCardsUiArchivedNote':'chatCardsUiEditingNote']));
    assert.ok(html.includes(e.chatCardsUiOpen));assert.ok(html.indexOf('TITLE_0')<html.indexOf('TITLE_3'));
    assert.equal(now.qa.chatWorkspaceModeLabel('UNKNOWN'),old.qa.chatWorkspaceModeLabel('UNKNOWN'));
  });
  test(`${locale}: denied/invalid ID never gains a link and unknown state/mode keep original mapping`,()=>{
    for(const view of [true,false,'true',undefined])for(const value of [id,'invalid/"><script>','']){
      const record=item({id:value,state:'UNEXPECTED',mode:'DEEP'}),ctx={...now.context,capabilities:{'chat-workspace-view':view}};
      const html=cards([record],ctx),prior=old.qa.renderChatWorkspaceCards([record],ctx);
      assert.deepEqual(attrs(html),attrs(prior));assert.ok(html.includes('data-status="guarded">'+e.chatCardsUiStateGuarded));
      assert.ok(html.includes(e.chatCardsUiModeFocus));
    }
  });
  test(`${locale}: customer words and hostile literals remain literal and safely escaped`,()=>{
    const literal='<script>alert("studio media Bot provider guarded demo")</script>&\'';
    const record=item({title:literal,objective_excerpt:literal,tags:['Bot','provider','workflow','guarded']});
    const html=cards([record]),prior=old.qa.renderChatWorkspaceCards([record],old.context);
    assert.ok(html.includes(now.qa.safeText(literal)));assert.equal(html.includes('<script>'),false);
    assert.equal(now.qa.renderChatWorkspaceTags(record.tags),old.qa.renderChatWorkspaceTags(record.tags));
    assert.deepEqual(attrs(html),attrs(prior));
  });
  test(`${locale}: numeric coercions and absent customer fields retain values, localize only fixed fallbacks`,()=>{
    for(const values of [{title:'',objective_excerpt:'',revision:0,context_count:0,turn_count:0,updated_at:''},{title:null,objective_excerpt:null,revision:'<9>',context_count:'2',turn_count:'NaN',mode:null}]){
      const record=item(values),html=cards([record]);
      assert.ok(html.includes(e.chatCardsUiTitleFallback));assert.ok(html.includes(e.chatCardsUiObjectiveFallback));
      assert.ok(html.includes(e.chatCardsUiUpdate+' '+now.qa.safeText(String(record.revision||1))));
      assert.ok(html.includes(e.chatCardsUiNotes+': '+String(Number(record.context_count||0))));
      assert.ok(html.includes(e.chatCardsUiTurns+': '+String(Number(record.turn_count||0))));
    }
  });
  test(`${locale}: changing language after initialization updates the same renderer`,()=>{
    now.setLocale(locale);assert.ok(cards([item()]).includes(e.chatCardsUiOpen));
    const next=locale==='vi'?'en':locale==='en'?'zh':'vi';now.setLocale(next);
    assert.ok(cards([item()]).includes(expected[next].chatCardsUiOpen));now.setLocale(locale);
  });
  test(`${locale}: historical adapter rejects changed/missing/reordered keys, retains unknown customer copy`,()=>{
    const entries=Object.entries(now.messages[locale]),normalized=chatCardsHistoricalSnapshot(entries,locale);
    assert.equal(normalized.length,entries.length-20);
    for(const key of Object.keys(e)){
      assert.throws(()=>chatCardsHistoricalSnapshot(entries.filter(([k])=>k!==key),locale),/Unreviewed Chat cards copy/);
      assert.throws(()=>chatCardsHistoricalSnapshot(entries.map(([k,v])=>[k,k===key?'UNREVIEWED':v]),locale),/Unreviewed Chat cards copy/);
    }
    const added=entries.filter(([key])=>Object.hasOwn(e,key));
    assert.throws(()=>chatCardsHistoricalSnapshot([...normalized,...added.toReversed()],locale),/Unreviewed Chat cards copy/);
    const unknown=['chatCardsUiUnknown','CUSTOMER media studio'];
    assert.deepEqual(chatCardsHistoricalSnapshot([...entries,unknown],locale).at(-1),unknown);
  });
}
test('historical source adapter accepts only reviewed full spans, preserving unrelated source',()=>{
  assert.ok(sources.portal!==oldSources.portal,'Reviewed cards/boundary changes must be present');
  assert.equal(chatCardsHistoricalPortalSource(sources.portal),oldSources.portal);
  const mutate=(start,end,before,after)=>{
    const a=sources.portal.indexOf(start),b=sources.portal.indexOf(end,a);assert.ok(a>=0&&b>a);
    const span=sources.portal.slice(a,b);assert.equal(span.split(before).length-1,1);
    return sources.portal.slice(0,a)+span.replace(before,after)+sources.portal.slice(b);
  };
  assert.throws(()=>chatCardsHistoricalPortalSource(mutate('  function renderChatWorkspaceBoundary(context) {','  function renderChatWorkspaceCards(','    return "";\n','    return "UNREVIEWED";\n')),/Unreviewed Chat (?:cards|dates\/pages) source/);
  assert.throws(()=>chatCardsHistoricalPortalSource(mutate('  function renderChatWorkspaceCards(items, context) {','  function renderChatWorkspace(page, context) {','const statusLabel = state === "draft"','const statusLabel = state === "UNREVIEWED"')),/Unreviewed Chat (?:cards|dates\/pages) source/);
  assert.ok(chatCardsHistoricalPortalSource(sources.portal+'\n// UNRELATED_SENTINEL').endsWith('// UNRELATED_SENTINEL'));
});
