import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {historyHistoricalSnapshot,historyHistoricalPortalSource} from './helpers/chat-history-snapshot.mjs';
import {cardsTurnRenderer,cardsTurnSources} from './helpers/chat-context-cards-turn-runtime.mjs';
import {cardsTurnHistoricalSnapshot,cardsTurnHistoricalPortalSource} from './helpers/chat-context-cards-turn-snapshot.mjs';
import {contextSectionHistoricalPortalSource} from './helpers/chat-context-section-snapshot.mjs';
const live=cardsTurnSources(),source={...live,portal:historyHistoricalPortalSource(live.portal)},oldSource=cardsTurnSources(true);
const actual=await cardsTurnRenderer(source),before=await cardsTurnRenderer(oldSource);
const current=(...args)=>{
  const result=actual(...args);
  return {...result,catalogFrozen:Object.fromEntries(['vi','en','zh'].map(locale=>[locale,Object.isFrozen(result.messages[locale])])),messages:Object.fromEntries(['vi','en','zh'].map(locale=>[
    locale,Object.fromEntries(historyHistoricalSnapshot(Object.entries(result.messages[locale]),locale))
  ]))};
};
const approved=JSON.parse(fs.readFileSync(new URL('./fixtures/chat-context-cards-turn-reviewed.json',import.meta.url),'utf8'));
const uuid=k=>'22222222-2222-4222-8222-'+String(k).padStart(12,'0'),id=uuid(1),route='/chat/'+id;
const literal='CUSTOMER media studio Facebook TikTok <script>alert("Bot")</script>&';
const contextKinds=['brief','constraint','reference','instruction','UNKNOWN',null,''],turnKinds=['prompt','note','decision','UNKNOWN'];
const contexts=contextKinds.map((kind,k)=>({id:uuid(10+k),revision:k+1,state:'active',kind,title:k?literal:'',body:literal,tags:['media','studio','Facebook','TikTok']}));
const turns=turnKinds.map((kind,k)=>({id:uuid(30+k),revision:[0,'INVALID',3,null][k],ordinal:[0,'INVALID',3,null][k],state:'active',kind,body:literal,updated_at:k?'':'2026-11-14T08:00:00+00:00',created_at:'2026-11-13T08:00:00Z'}));
const thread={id,revision:7,state:'draft',mode:'focus',title:literal,objective:literal,tags:['media','studio','Facebook','TikTok']};
const raw={chatWorkspaceEnabled:true,capabilities:{'chat-workspace-view':true},chatThreadDetail:{thread,contexts,turns,versions:[],events:[]}};
const sessions=Object.fromEntries(['vi','en','zh'].map(locale=>[locale,{now:current(locale,route,raw),old:before(locale,route,raw)}]));
const tags=html=>[...html.replace(/data-portal-confirm="[^"]*"/g,'data-portal-confirm="__COPY__"').matchAll(/<[^>]+>/g)].map(match=>match[0]);
function render(session,state,capability,itemState,empty=false){
  // No default capability: undefined must remain denied.
  const ctx={...session.context,capabilities:{...session.context.capabilities,'chat-context-update':capability,'chat-context-state':capability,'chat-turn-state':capability},chatThreadDetail:{thread:{...thread,state},contexts:empty?[]:contexts.map(x=>({...x,state:itemState})),turns:empty?[]:turns.map(x=>({...x,state:itemState})),versions:[],events:[]}};
  const saved=JSON.stringify(ctx),html=session.qa.renderChatWorkspaceDetail(session.page,ctx);
  assert.equal(JSON.stringify(ctx),saved);return html;
}
const cards=html=>[...html.matchAll(/<article class="portal-chat-context-card[^"]*">[\s\S]*?<\/article>/g)].map(match=>match[0]);
const entries=html=>[...html.matchAll(/<article class="portal-chat-turn(?: is-archived)?">[\s\S]*?<\/article>/g)].map(match=>match[0]);
const attr=(tag,name)=>new RegExp(name+'="([^"]*)"').exec(tag)?.[1];
function checkCards(session,locale,html,old,state,cap,itemState){
  const copy=approved[locale],existing=sessions[locale].old.messages[locale],a=cards(html),b=cards(old),active=itemState==='active';
  assert.equal(a.length,contexts.length);assert.deepEqual(tags(html),tags(old));
  for(let k=0;k<a.length;k++){
    const text=a[k],record=contexts[k],canUpdate=state==='draft'&&cap===true&&active,canState=state==='draft'&&cap===true;
    const suffix={brief:'Brief',constraint:'Constraint',reference:'Reference',instruction:'Instruction'}[record.kind];
    assert.ok(text.includes(session.qa.safeText(suffix?existing['chatDetailFieldUiKind'+suffix]:copy.chatContextCardsUiTitleFallback)));
    assert.ok(text.includes('<h3 class="portal-card-title">'+session.qa.safeText(record.title||copy.chatContextCardsUiTitleFallback)+'</h3>'));
    assert.ok(text.includes('<p>'+session.qa.safeText(record.body)+'</p>'));assert.equal(text.includes('<script>'),false);
    assert.ok(text.includes('data-status="'+(active?'ready':'archived')+'">'+session.qa.safeText(active?copy.chatContextCardsUiStateActive:existing.chatCardsUiStateArchived)));
    const options=[...text.matchAll(/<option value="([^"]*)"([^>]*)>([\s\S]*?)<\/option>/g)];
    assert.deepEqual(options.map(m=>m[1]),contextKinds.slice(0,4));
    const selected=String(record.kind||'brief');assert.deepEqual(options.filter(m=>m[2].includes('selected')).map(m=>m[1]),contextKinds.slice(0,4).filter(x=>x===selected));
    for(let j=0;j<4;j++)assert.equal(options[j][3],session.qa.safeText(existing['chatDetailFieldUiKind'+['Brief','Constraint','Reference','Instruction'][j]]));
    const controls=[...text.matchAll(/<(?:select|input|textarea|button)\b[^>]*>/g)].map(m=>m[0]);
    assert.equal(controls.length,6);for(const control of controls.slice(0,5))assert.equal(/\sdisabled(?:\s|>)/.test(control),!canUpdate);
    const action=controls[5];assert.equal(/\sdisabled(?:\s|>)/.test(action),!canState);
    assert.equal(attr(action,'data-chat-context-state'),active?'archived':'active');
    assert.equal(attr(action,'data-portal-confirm'),session.qa.safeText(active?copy.chatContextCardsUiArchiveConfirm:copy.chatContextCardsUiRestoreConfirm));
    assert.ok(text.includes('>'+session.qa.safeText(copy.chatContextCardsUiSaveButton)+'</button>'));
    assert.ok(text.includes('>'+session.qa.safeText(active?existing.chatLifecycleUiArchiveButton:copy.chatContextCardsUiRestoreButton)+'</button>'));
    assert.ok(action.includes('data-chat-context-id="'+record.id+'"'));assert.ok(action.includes('data-chat-context-revision="'+record.revision+'"'));
    assert.deepEqual(tags(text),tags(b[k]));
  }
}
function checkTurns(session,locale,html,old,state,cap,itemState){
  const copy=approved[locale],existing=sessions[locale].old.messages[locale],a=entries(html),b=entries(old),active=itemState==='active';
  assert.equal(a.length,turns.length);
  for(let k=0;k<a.length;k++){
    const text=a[k],record=turns[k],kind=record.kind==='prompt'?'Prompt':record.kind==='decision'?'Decision':'Note';
    assert.ok(text.includes(session.qa.safeText(existing['chatDetailFieldUiTurn'+kind])+' · '+session.qa.safeText(copy.chatTurnListUiOrdinal)+' '+session.qa.safeText(String(record.ordinal||'—'))));
    assert.ok(text.includes('<small>'+session.qa.safeText(copy.chatTurnListUiUpdate)+' '+session.qa.safeText(String(record.revision||1))+' · '+session.qa.safeText(copy.chatTurnListUiUpdatedAt)+' '+session.qa.safeText(String(record.updated_at||record.created_at||'—'))+'</small>'));
    assert.ok(text.includes('<p>'+session.qa.safeText(record.body)+'</p>'));assert.deepEqual(tags(text),tags(b[k]));
    const button=/<button\b[^>]*>/.exec(text)?.[0];assert.ok(button);
    assert.equal(/\sdisabled(?:\s|>)/.test(button),!(state==='draft'&&cap===true));
    assert.equal(attr(button,'data-chat-turn-state'),active?'archived':'active');
    assert.equal(attr(button,'data-portal-confirm'),session.qa.safeText(active?copy.chatTurnListUiArchiveConfirm:copy.chatTurnListUiRestoreConfirm));
    assert.ok(text.includes('>'+session.qa.safeText(active?existing.chatLifecycleUiArchiveButton:copy.chatTurnListUiRestoreButton)+'</button>'));
  }
}
for(const locale of ['vi','en','zh']){
  const {now,old}=sessions[locale],copy=approved[locale];
  test(`${locale}: real cards/options/turns preserve values, order, states and strict capability gates`,()=>{
    for(const state of ['draft','review','ready','archived'])for(const cap of [true,false,'true',undefined])for(const active of ['active','archived','UNKNOWN']){
      const a=render(now,state,cap,active),b=render(old,state,cap,active);
      checkCards(now,locale,a,b,state,cap,active);checkTurns(now,locale,a,b,state,cap,active);
      assert.ok(a.includes(now.qa.safeText(literal)));assert.ok(a.includes('<span>media</span><span>studio</span><span>Facebook</span><span>TikTok</span>'));
    }
  });
  test(`${locale}: empty state, runtime locale and confirmation/button escaping remain meaningful`,()=>{
    const empty=render(now,'draft',true,'active',true);
    for(const key of ['chatContextCardsUiEmptyTitle','chatContextCardsUiEmptyBody','chatTurnListUiEmptyTitle','chatTurnListUiEmptyBody'])assert.ok(empty.includes(now.qa.safeText(copy[key])));
    const next=locale==='vi'?'en':locale==='en'?'zh':'vi';
    try{now.setLocale(next);const a=render(now,'draft',true,'active'),b=render(sessions[next].old,'draft',true,'active');checkCards(now,next,a,b,'draft',true,'active');checkTurns(now,next,a,b,'draft',true,'active');}finally{now.setLocale(locale);}
    const hostile='<img src=x onerror="alert(1)"> \'&',html=now.qa.withUiText(()=>hostile,()=>render(now,'draft',true,'active'));
    for(const text of [...cards(html),...entries(html)]){
      assert.equal(text.includes('<img'),false);assert.equal(text.includes('&amp;lt;img'),false);
      assert.ok(text.includes('data-portal-confirm="'+now.qa.safeText(hostile)+'"'));assert.ok(text.includes('>'+now.qa.safeText(hostile)+'</button>'));
    }
  });
  test(`${locale}: exactly sixteen approved ordered keys and real frozen old dictionary survive strict mutations`,()=>{
    const a=Object.entries(now.messages[locale]),b=Object.entries(old.messages[locale]);assert.equal(now.catalogFrozen[locale],true);
    assert.deepEqual(JSON.parse(JSON.stringify(a.slice(0,b.length))),JSON.parse(JSON.stringify(b)));assert.deepEqual(JSON.parse(JSON.stringify(a.slice(b.length))),Object.entries(copy));
    const normalized=cardsTurnHistoricalSnapshot(a,locale);assert.equal(normalized.length,a.length-16);
    for(const key of Object.keys(copy)){
      assert.throws(()=>cardsTurnHistoricalSnapshot(a.filter(([k])=>k!==key),locale),/Unreviewed Chat cards\/turn copy/);
      assert.throws(()=>cardsTurnHistoricalSnapshot(a.map(([k,v])=>[k,k===key?'UNREVIEWED':v]),locale),/Unreviewed Chat cards\/turn copy/);
    }
    assert.throws(()=>cardsTurnHistoricalSnapshot([...normalized,...Object.entries(copy).toReversed()],locale),/Unreviewed Chat cards\/turn copy/);
    assert.throws(()=>cardsTurnHistoricalSnapshot([...a,['chatTurnListUiUnknown','UNKNOWN']],locale),/Unreviewed Chat cards\/turn copy/);
    const customer=['unknown.customer.key',literal];assert.deepEqual(cardsTurnHistoricalSnapshot([...a,customer],locale).at(-1),customer);
  });
}
test('new full-detail and options source gates reject mutations while preserving unrelated source',()=>{
  assert.notEqual(source.portal,oldSource.portal);assert.equal(cardsTurnHistoricalPortalSource(source.portal),oldSource.portal);
  for(const[start,end,old,next]of [
    ['  function renderChatWorkspaceDetail(page, context) {','\n  // Analytics Workspace','const writable = state === "draft";','const writable = true;'],
    ['  function renderChatContextKindOptions(value) {','  function chatWorkspaceTurnLabel(','const selected = String(value || "brief");','const selected = "UNKNOWN";']
  ]){
    const a=source.portal.indexOf(start),b=source.portal.indexOf(end,a),part=source.portal.slice(a,b);assert.ok(a>=0&&b>a);assert.equal(part.split(old).length-1,1);
    assert.throws(()=>cardsTurnHistoricalPortalSource(source.portal.slice(0,a)+part.replace(old,next)+source.portal.slice(b)),/Unreviewed Chat cards\/turn source/);
  }
  assert.ok(cardsTurnHistoricalPortalSource(source.portal+'\n// UNKNOWN_OUTSIDE').endsWith('// UNKNOWN_OUTSIDE'));
});
test('marker-free earlier detail stays byte-exact and its existing CCS gate still rejects mutation',()=>{
  assert.equal(cardsTurnHistoricalPortalSource(oldSource.portal),oldSource.portal);
  const start='  function renderChatWorkspaceDetail(page, context) {',a=oldSource.portal.indexOf(start),b=oldSource.portal.indexOf('\n  // Analytics Workspace',a),part=oldSource.portal.slice(a,b);
  assert.equal(/chat(?:ContextCards|TurnList)Ui/.test(part),false);const old='const writable = state === "draft";';assert.equal(part.split(old).length-1,1);
  const changed=oldSource.portal.slice(0,a)+part.replace(old,'const writable = true;')+oldSource.portal.slice(b);
  assert.equal(cardsTurnHistoricalPortalSource(changed),changed);assert.throws(()=>contextSectionHistoricalPortalSource(changed),/Unreviewed Chat context\/section source/);
});
