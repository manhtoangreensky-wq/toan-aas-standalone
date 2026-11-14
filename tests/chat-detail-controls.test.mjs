import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {detailRenderer,detailSources} from './helpers/chat-detail-controls-runtime.mjs';
import {detailHistoricalSnapshot,detailHistoricalPortalSource} from './helpers/chat-detail-controls-snapshot.mjs';
const source=detailSources(),oldSource=detailSources(true);
const current=await detailRenderer(source),before=await detailRenderer(oldSource);
const copy=JSON.parse(fs.readFileSync(new URL('./fixtures/chat-detail-controls-reviewed.json',import.meta.url),'utf8'));
const id='11111111-1111-4111-8111-111111111111',route='/chat/'+id;
const thread={id,revision:7,state:'draft',mode:'focus',title:'CUSTOMER Bot <script> "provider"&',objective:'CUSTOMER workflow metadata',tags:['Bot','provider','guarded']};
const raw={chatWorkspaceEnabled:true,capabilities:{'chat-workspace-view':true,'chat-thread-update':true,'chat-context-create':true,'chat-turn-create':true,'chat-thread-lifecycle':true,'chat-run-submit':false,'chat-run-refresh':true},chatThreadDetail:{thread,contexts:[],turns:[],versions:[],events:[]}};
const sessions=Object.fromEntries(['vi','en','zh'].map(locale=>[locale,{now:current(locale,route,raw),old:before(locale,route,raw)}]));
const json=value=>JSON.parse(JSON.stringify(value));
const contracts=fields=>json(fields.map(field=>{const x={...field};for(const key of ['label','placeholder','help','emptyLabel'])delete x[key];if(x.options)x.options=x.options.map(([value])=>value);return x;}));
const noncopy=html=>[...html.replace(/placeholder="[^"]*"/g,'placeholder="__COPY__"').replace(/data-portal-confirm="[^"]*"/g,'data-portal-confirm="__COPY__"').matchAll(/<[^>]+>/g)].map(m=>m[0]);
const branch={archived:[['draft','Restore']],draft:[['review','Review'],['archived','Archive']],review:[['draft','Draft'],['ready','Ready'],['archived','Archive']],ready:[['draft','Draft'],['archived','Archive']]};
function life(now,old,locale,state,cap){
  const context={capabilities:{'chat-thread-lifecycle':cap}},html=now.qa.chatWorkspaceLifecycleActions(thread,state,context,route),prior=old.qa.chatWorkspaceLifecycleActions(thread,state,context,route);
  assert.deepEqual(noncopy(html),noncopy(prior));
  const buttons=[...html.matchAll(/<button\b([^>]*)>([\s\S]*?)<\/button>/g)],expected=branch[state]||branch.ready;
  assert.equal(buttons.length,expected.length);
  for(let i=0;i<buttons.length;i++){
    const [attrs,label]=buttons[i].slice(1),[target,key]=expected[i];
    assert.ok(attrs.includes('data-portal-action="chat-thread-lifecycle"'));
    assert.ok(attrs.includes('data-chat-thread-state="'+target+'"'));
    assert.ok(attrs.includes('data-chat-thread-id="'+id+'"'));assert.ok(attrs.includes('data-chat-thread-revision="7"'));
    assert.ok(attrs.includes('data-portal-route="'+route+'"'));
    assert.equal(/\sdisabled(?:\s|$)/.test(attrs),cap!==true);
    assert.ok(attrs.includes('data-portal-confirm="'+now.qa.safeText(copy[locale]['chatLifecycleUi'+key+'Confirm'])+'"'));
    assert.equal(label,now.qa.safeText(copy[locale]['chatLifecycleUi'+key+'Button']));
  }
}
for(const locale of ['vi','en','zh']){
  const {now,old}=sessions[locale],e=copy[locale];
  test(`${locale}: four context fields/options use approved language without changing raw contracts`,()=>{
    const fields=now.qa.chatContextFields(),[kind,title,body,tags]=fields;
    assert.equal(fields.length,4);assert.deepEqual(contracts(fields),contracts(old.qa.chatContextFields()));
    assert.equal(kind.label,e.chatDetailFieldUiContextKindLabel);
    assert.deepEqual(json(kind.options),['brief','constraint','reference','instruction'].map((value,i)=>[value,e['chatDetailFieldUiKind'+['Brief','Constraint','Reference','Instruction'][i]]]));
    assert.equal(title.label,e.chatDetailFieldUiContextTitleLabel);assert.equal(title.placeholder,e.chatDetailFieldUiContextTitlePlaceholder);
    assert.equal(body.label,e.chatDetailFieldUiContextBodyLabel);assert.equal(body.placeholder,e.chatDetailFieldUiContextBodyPlaceholder);
    assert.equal(tags.label,e.chatDetailFieldUiContextTagsLabel);assert.equal(tags.placeholder,e.chatDetailFieldUiContextTagsPlaceholder);
  });
  test(`${locale}: turn/run fields keep codes, constraints and truthful request guidance`,()=>{
    const turns=now.qa.chatTurnFields(),runs=now.qa.chatRunFields();
    assert.deepEqual(contracts(turns),contracts(old.qa.chatTurnFields()));assert.deepEqual(contracts(runs),contracts(old.qa.chatRunFields()));
    assert.equal(turns[0].label,e.chatDetailFieldUiTurnKindLabel);
    assert.deepEqual(json(turns[0].options),['prompt','note','decision'].map((value,i)=>[value,e['chatDetailFieldUiTurn'+['Prompt','Note','Decision'][i]]]));
    assert.equal(turns[1].label,e.chatDetailFieldUiTurnBodyLabel);assert.equal(turns[1].placeholder,e.chatDetailFieldUiTurnBodyPlaceholder);
    assert.equal(runs[0].label,e.chatDetailFieldUiRunLabel);assert.equal(runs[0].placeholder,e.chatDetailFieldUiRunPlaceholder);
    assert.doesNotMatch(runs[0].placeholder,/generate|automatic|AI|tự động|生成|自动/i);
  });
  test(`${locale}: actual rendered fields preserve selection, disabled gates, IDs and customer escaping`,()=>{
    const literal='CUSTOMER Bot context provider <script>alert("x")</script>&';
    for(const [method,codes,namespace]of [['chatContextFields',['brief','constraint','reference','instruction'],'chat-context-create-'],['chatTurnFields',['prompt','note','decision'],'chat-turn-create-'],['chatRunFields',[''],'chat-run-compose-']]){
      for(const enabled of [false,true])for(const kind of codes){
        const values={kind,title:literal,body:literal,tags:literal,client_message:literal},saved=JSON.stringify(values);
        const html=now.qa.renderFields(now.qa[method](),enabled,now.context,values,namespace+id),prior=old.qa.renderFields(old.qa[method](),enabled,old.context,values,namespace+id);
        assert.deepEqual(noncopy(html),noncopy(prior));assert.ok(html.includes(now.qa.safeText(literal)));assert.equal(html.includes('<script>'),false);
        if(kind)assert.ok(html.includes('value="'+kind+'" selected'));
        assert.equal(JSON.stringify(values),saved);
      }
    }
    assert.equal(now.qa.chatContextFields()[0].label,e.chatDetailFieldUiContextKindLabel);
  });
  for(const state of ['draft','review','ready','archived'])test(`${locale}/${state}: lifecycle exact branch/actions/order and strict capability`,()=>{for(const cap of [true,false,'true',undefined])life(now,old,locale,state,cap);});
  test(`${locale}: unknown/direct lifecycle states retain the original final branch`,()=>{for(const state of ['UNKNOWN','DRAFT',undefined,null,''])for(const cap of [true,false,'true',undefined])life(now,old,locale,state,cap);});
  test(`${locale}: labels/options/confirmations change after locale selection and hostile translations stay escaped`,()=>{
    const next=locale==='vi'?'en':locale==='en'?'zh':'vi';
    try{
      now.setLocale(next);assert.equal(now.qa.chatContextFields()[0].label,copy[next].chatDetailFieldUiContextKindLabel);
      assert.equal(now.qa.chatTurnFields()[0].options[0][1],copy[next].chatDetailFieldUiTurnPrompt);life(now,old,next,'review',true);
    }finally{now.setLocale(locale);}
    const literal='<img src=x onerror="alert(1)"> \'& customer';
    const html=now.qa.withUiText(()=>literal,()=>now.qa.chatWorkspaceLifecycleActions(thread,'review',{capabilities:{'chat-thread-lifecycle':true}},route));
    assert.equal(html.includes('<img'),false);assert.equal((html.match(/<button\b/g)||[]).length,3);
    assert.ok(html.includes('data-portal-confirm="'+now.qa.safeText(literal)+'"'));
    assert.ok(html.includes('>'+now.qa.safeText(literal)+'</button>'));
  });
  test(`${locale}: real detail consumer keeps controls/data and only 29 reviewed catalog additions`,()=>{
    assert.deepEqual(noncopy(now.html),noncopy(old.html));assert.deepEqual(json(now.context),json(old.context));
    assert.ok(now.html.includes(now.qa.safeText(thread.title)));assert.ok(now.html.includes(thread.objective));
    for(const suffix of ['ContextKindLabel','ContextTitleLabel','ContextBodyLabel','ContextTagsLabel','TurnKindLabel','TurnBodyLabel','RunLabel'])assert.ok(now.html.includes(now.qa.safeText(e['chatDetailFieldUi'+suffix])));
    const a=Object.entries(now.messages[locale]),b=Object.entries(old.messages[locale]);
    assert.deepEqual(json(a.slice(0,b.length)),json(b));assert.deepEqual(json(a.slice(b.length)),Object.entries(e));assert.ok(Object.isFrozen(now.messages[locale]));
  });
  test(`${locale}: strict historical adapter rejects missing/mutated/reordered keys and preserves unknown text`,()=>{
    const entries=Object.entries(now.messages[locale]),normalized=detailHistoricalSnapshot(entries,locale);
    assert.equal(normalized.length,entries.length-29);
    for(const key of Object.keys(e)){
      assert.throws(()=>detailHistoricalSnapshot(entries.filter(([k])=>k!==key),locale),/Unreviewed Chat detail copy/);
      assert.throws(()=>detailHistoricalSnapshot(entries.map(([k,v])=>[k,k===key?'UNKNOWN':v]),locale),/Unreviewed Chat detail copy/);
    }
    assert.throws(()=>detailHistoricalSnapshot([...normalized,...Object.entries(e).toReversed()],locale),/Unreviewed Chat detail copy/);
    const unknown=['chatDetailFieldUiUnknown','CUSTOMER studio media'];assert.deepEqual(detailHistoricalSnapshot([...entries,unknown],locale).at(-1),unknown);
  });
}
test('historical detail source normalization accepts only the two full hash-reviewed spans',()=>{
  assert.ok(source.portal!==oldSource.portal);assert.equal(detailHistoricalPortalSource(source.portal),oldSource.portal);
  for(const [start,end,old,next]of [
    ['  function chatContextFields() {','  function chatRunState(','maxLength: 12000','maxLength: 1'],
    ['  function chatWorkspaceLifecycleActions(thread, state, context, route) {','  function renderChatWorkspaceDetail(','if (state === "draft")','if (state === "UNKNOWN")']
  ]){
    const a=source.portal.indexOf(start),b=source.portal.indexOf(end,a),span=source.portal.slice(a,b);
    assert.ok(a>=0&&b>a&&span.includes(old));
    assert.throws(()=>detailHistoricalPortalSource(source.portal.slice(0,a)+span.replace(old,next)+source.portal.slice(b)),/Unreviewed Chat detail source/);
  }
  assert.ok(detailHistoricalPortalSource(source.portal+'\n// UNKNOWN_SOURCE').endsWith('// UNKNOWN_SOURCE'));
});
