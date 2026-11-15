import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {chatHistoryRenderer,chatHistorySources} from './helpers/chat-history-runtime.mjs';
import {historyHistoricalSnapshot,historyHistoricalPortalSource} from './helpers/chat-history-snapshot.mjs';
import {cardsTurnHistoricalPortalSource} from './helpers/chat-context-cards-turn-snapshot.mjs';
import {requestPanelHistoricalSnapshot,requestPanelHistoricalPortalSource} from './helpers/chat-request-panel-snapshot.mjs';
const live=chatHistorySources(),source={...live,portal:requestPanelHistoricalPortalSource(live.portal)},oldSource=chatHistorySources(true);
const actual=await chatHistoryRenderer(source),before=await chatHistoryRenderer(oldSource);
const current=(...args)=>{
  const result=actual(...args);
  return {...result,catalogFrozen:Object.fromEntries(['vi','en','zh'].map(locale=>[locale,Object.isFrozen(result.messages[locale])])),messages:Object.fromEntries(['vi','en','zh'].map(locale=>[
    locale,Object.fromEntries(requestPanelHistoricalSnapshot(Object.entries(result.messages[locale]),locale))
  ]))};
};
const copy=JSON.parse(fs.readFileSync(new URL('./fixtures/chat-history-reviewed.json',import.meta.url),'utf8'));
const id='11111111-1111-4111-8111-111111111111',route='/chat/'+id,literal='CUSTOMER media studio Facebook TikTok <script>alert("Bot")</script>&';
const actionKeys={thread_created:'ThreadCreated',thread_updated:'ThreadUpdated',thread_draft:'@Draft',thread_review:'@Review',thread_ready:'@Ready',thread_archived:'@Archived',thread_version_restored:'ThreadRestored',context_created:'ContextCreated',context_updated:'ContextUpdated',context_active:'ContextActive',context_archived:'ContextArchived',turn_created:'TurnCreated',turn_active:'TurnActive',turn_archived:'TurnArchived',chat_run_guarded:'RequestNotExecuted'};
const actions=[...Object.keys(actionKeys),'',null,'UNKNOWN','__proto__','constructor','toString'];
const versions=[7,'7',0,2,3,4,'INVALID'].map((revision,k)=>({revision,title:k===2?'':literal,mode:['focus','deep','pro','UNKNOWN'][k%4],state:['draft','review','ready','archived','UNKNOWN'][k%5],created_at:k?'2026-11-14T08:00:00+00:00':''}));
const events=actions.map((action,k)=>({action,revision:k%2?String(k):0,created_at:k?'2026-11-14T09:10:00+00:00':''}));
const thread={id,revision:7,state:'draft',mode:'focus',title:literal,objective:literal,tags:['media','studio','Facebook','TikTok']};
const raw={chatWorkspaceEnabled:true,capabilities:{'chat-workspace-view':true},chatThreadDetail:{thread,contexts:[],turns:[],versions,events}};
const sessions=Object.fromEntries(['vi','en','zh'].map(locale=>[locale,{now:current(locale,route,raw),old:before(locale,route,raw)}]));
const tags=html=>[...html.replace(/data-portal-confirm="[^"]*"/g,'data-portal-confirm="__COPY__"').matchAll(/<[^>]+>/g)].map(m=>m[0]);
const attr=(tag,name)=>new RegExp(name+'="([^"]*)"').exec(tag)?.[1];
function render(session,state,capability,revision,empty=false){
  const context={...session.context,capabilities:{...session.context.capabilities,'chat-thread-restore-version':capability},chatThreadDetail:{thread:{...thread,state,revision},contexts:[],turns:[],versions:empty?[]:versions,events:empty?[]:events}};
  const saved=JSON.stringify(context),html=session.qa.renderChatWorkspaceDetail(session.page,context);
  assert.equal(JSON.stringify(context),saved);return html;
}
function history(html){const a=html.indexOf('<div class="portal-chat-workspace-history">'),b=html.lastIndexOf('</article>');assert.ok(a>=0&&b>a);return html.slice(a,b);}
function versionRows(html){return [...history(html).matchAll(/<article>([\s\S]*?)<\/article>/g)].map(m=>m[1]);}
function activityRows(html){return [...history(html).matchAll(/<div><span aria-hidden="true">•<\/span><span><strong>([\s\S]*?)<\/strong><small>([\s\S]*?)<\/small><\/span><\/div>/g)];}
function checkVersions(session,locale,html,prior,state,cap,revision){
  const e=copy[locale],old=sessions[locale].old.messages[locale],a=versionRows(html),b=versionRows(prior),records=versions.filter(x=>Number.isInteger(Number(x.revision)));
  assert.deepEqual(tags(history(html)),tags(history(prior)));assert.equal(a.length,records.length);
  for(const key of ['Kicker','Title','Body'])assert.ok(history(html).includes(session.qa.safeText(e['chatHistoryVersionUi'+key])));
  for(let k=0;k<a.length;k++){
    const row=a[k],item=records[k],mode=item.mode==='deep'?'Deep':item.mode==='pro'?'Pro':'Focus',normalized=session.qa.chatWorkspaceState(item.state);
    const status=normalized[0].toUpperCase()+normalized.slice(1);
    assert.ok(row.includes('<strong>'+session.qa.safeText(old.chatCardsUiUpdate)+' '+session.qa.safeText(String(item.revision))+' · '+session.qa.safeText(item.title||old.chatCardsUiTitleFallback)+'</strong>'));
    assert.ok(row.includes('<p>'+session.qa.safeText(old['chatCardsUiMode'+mode])+' · '+session.qa.safeText(old['chatCardsUiState'+status])+'</p>'));
    assert.ok(row.includes('<small>'+session.qa.safeText(String(item.created_at||'—'))+'</small>'));
    const button=/<button\b[^>]*>/.exec(row)?.[0],same=Number(item.revision)===Number(revision);
    assert.equal(Boolean(button),!same);assert.deepEqual(tags(row),tags(b[k]));
    if(same)assert.ok(row.includes('<span class="portal-form-note">'+session.qa.safeText(e.chatHistoryVersionUiCurrent)+'</span>'));
    else{
      assert.equal(attr(button,'data-portal-action'),'chat-thread-restore-version');assert.equal(attr(button,'data-portal-route'),route);
      assert.equal(attr(button,'data-chat-thread-id'),id);assert.equal(attr(button,'data-chat-thread-revision'),session.qa.safeText(String(revision)));
      assert.equal(attr(button,'data-chat-thread-version'),session.qa.safeText(String(item.revision)));
      assert.equal(/\sdisabled(?:\s|>)/.test(button),!(state==='draft'&&cap===true));
      assert.equal(attr(button,'data-portal-confirm'),session.qa.safeText(e.chatHistoryVersionUiRestoreConfirm.replace('{revision}',String(item.revision))));
      assert.ok(row.includes('>'+session.qa.safeText(old.chatLifecycleUiRestoreButton)+' '+session.qa.safeText(String(item.revision))+'</button>'));
    }
    assert.equal(row.includes('<script>'),false);
  }
}
function checkActivity(session,locale,html){
  const e=copy[locale],old=sessions[locale].old.messages[locale],rows=activityRows(html);assert.equal(rows.length,events.length);
  for(const key of ['Kicker','Title','Body'])assert.ok(history(html).includes(session.qa.safeText(e['chatHistoryActivityUi'+key])));
  for(let k=0;k<rows.length;k++){
    const action=String(events[k].action||''),suffix=Object.hasOwn(actionKeys,action)?actionKeys[action]:'Unknown';
    const label=suffix.startsWith('@')?old['chatCardsUiState'+suffix.slice(1)]:e['chatHistoryActivityUi'+suffix];
    assert.equal(rows[k][1],session.qa.safeText(label));
    assert.equal(rows[k][2],session.qa.safeText(old.chatCardsUiUpdate)+' '+session.qa.safeText(String(events[k].revision||1))+' · '+session.qa.safeText(String(events[k].created_at||'—')));
  }
}
for(const locale of ['vi','en','zh']){
  const {now,old}=sessions[locale],e=copy[locale];
  test(`${locale}: versions preserve number equality, row order, title/date literals and strict restore rights`,()=>{
    for(const state of ['draft','review','ready','archived'])for(const cap of [true,false,'true',undefined])for(const revision of [7,'7',0]){
      const a=render(now,state,cap,revision),b=render(old,state,cap,revision);checkVersions(now,locale,a,b,state,cap,revision);
      assert.ok(a.includes(now.qa.safeText(literal)));assert.ok(a.includes('<span>media</span><span>studio</span><span>Facebook</span><span>TikTok</span>'));
    }
  });
  test(`${locale}: fifteen known activities plus empty/unknown/prototype actions retain every row and literal values`,()=>{
    const a=render(now,'draft',true,7),b=render(old,'draft',true,7);assert.deepEqual(tags(history(a)),tags(history(b)));checkActivity(now,locale,a);
    assert.equal(Object.keys(actionKeys).length,15);assert.equal(activityRows(a).length,21);
    for(const action of ['__proto__','constructor','toString'])assert.equal(activityRows(a)[actions.indexOf(action)][1],now.qa.safeText(e.chatHistoryActivityUiUnknown));
  });
  test(`${locale}: empty guidance, runtime locale, VI fallbacks, safe interpolation and frozen ordered catalog remain`,()=>{
    const a=Object.entries(now.messages[locale]),b=Object.entries(old.messages[locale]);assert.equal(now.catalogFrozen[locale],true);
    assert.deepEqual(JSON.parse(JSON.stringify(a.slice(0,b.length))),JSON.parse(JSON.stringify(b)));assert.deepEqual(JSON.parse(JSON.stringify(a.slice(b.length))),Object.entries(e));
    const empty=render(now,'draft',true,7,true);assert.ok(empty.includes(now.qa.safeText(e.chatHistoryVersionUiEmpty)));assert.ok(empty.includes(now.qa.safeText(e.chatHistoryActivityUiEmpty)));
    const next=locale==='vi'?'en':locale==='en'?'zh':'vi';
    try{now.setLocale(next);const html=render(now,'draft',true,7);checkVersions(now,next,html,render(sessions[next].old,'draft',true,7),'draft',true,7);checkActivity(now,next,html);}finally{now.setLocale(locale);}
    const fallback=now.qa.withUiText((key,value)=>value,()=>render(now,'draft',true,7));checkActivity(now,'vi',fallback);
    checkVersions(now,'vi',fallback,render(sessions.vi.old,'draft',true,7),'draft',true,7);
    const fallbackEmpty=now.qa.withUiText((key,value)=>value,()=>render(now,'draft',true,7,true));
    for(const key of ['chatHistoryVersionUiEmpty','chatHistoryActivityUiEmpty'])assert.ok(fallbackEmpty.includes(now.qa.safeText(copy.vi[key])));
    const hostile='<img src=x onerror="alert(1)"> \'&',html=now.qa.withUiText(()=>hostile,()=>render(now,'draft',true,7));
    assert.equal(history(html).includes('<img'),false);assert.equal(history(html).includes('&amp;lt;img'),false);
    assert.ok(history(html).includes('data-portal-confirm="'+now.qa.safeText(hostile)+'"'));
    const normalized=historyHistoricalSnapshot(a,locale);assert.equal(normalized.length,a.length-22);
    for(const key of Object.keys(e)){
      assert.throws(()=>historyHistoricalSnapshot(a.filter(([k])=>k!==key),locale),/Unreviewed Chat history copy/);
      assert.throws(()=>historyHistoricalSnapshot(a.map(([k,v])=>[k,k===key?'UNREVIEWED':v]),locale),/Unreviewed Chat history copy/);
    }
    assert.throws(()=>historyHistoricalSnapshot([...normalized,...Object.entries(e).toReversed()],locale),/Unreviewed Chat history copy/);
    assert.throws(()=>historyHistoricalSnapshot([...a,['chatHistoryActivityUiUnknownKey','UNKNOWN']],locale),/Unreviewed Chat history copy/);
    const customer=['unknown.customer.key',literal];assert.deepEqual(historyHistoricalSnapshot([...a,customer],locale).at(-1),customer);
  });
}
test('history source normalizes only the accepted full detail and rejects exact scoped mutations',()=>{
  assert.notEqual(source.portal,oldSource.portal);assert.equal(historyHistoricalPortalSource(source.portal),oldSource.portal);
  const start='  function renderChatWorkspaceDetail(page, context) {',a=source.portal.indexOf(start),b=source.portal.indexOf('\n  // Analytics Workspace',a),part=source.portal.slice(a,b);
  for(const[old,next]of [['const writable = state === "draft";','const writable = true;'],['Object.prototype.hasOwnProperty.call','Object.prototype.propertyIsEnumerable.call']]){
    assert.equal(part.split(old).length-1,1);assert.throws(()=>historyHistoricalPortalSource(source.portal.slice(0,a)+part.replace(old,next)+source.portal.slice(b)),/Unreviewed Chat history source/);
  }
  assert.ok(historyHistoricalPortalSource(source.portal+'\n// UNKNOWN_OUTSIDE').endsWith('// UNKNOWN_OUTSIDE'));
});
test('marker-free previous detail remains exact and its earlier cards/turn gate still rejects mutation',()=>{
  assert.equal(historyHistoricalPortalSource(oldSource.portal),oldSource.portal);
  const start='  function renderChatWorkspaceDetail(page, context) {',a=oldSource.portal.indexOf(start),b=oldSource.portal.indexOf('\n  // Analytics Workspace',a),part=oldSource.portal.slice(a,b);
  assert.equal(/chatHistory(?:Version|Activity)Ui/.test(part),false);const old='const writable = state === "draft";';assert.equal(part.split(old).length-1,1);
  const changed=oldSource.portal.slice(0,a)+part.replace(old,'const writable = true;')+oldSource.portal.slice(b);
  assert.equal(historyHistoricalPortalSource(changed),changed);assert.throws(()=>cardsTurnHistoricalPortalSource(changed),/Unreviewed Chat cards\/turn source/);
});
