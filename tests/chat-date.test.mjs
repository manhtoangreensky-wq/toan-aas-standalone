import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {chatDateRenderer,chatDateSources} from './helpers/chat-date-runtime.mjs';
import {chatDateChanges,chatDateHistoricalPortalSource} from './helpers/chat-date-snapshot.mjs';
const source=chatDateSources(),baseline=chatDateSources(true),current=await chatDateRenderer(source),before=await chatDateRenderer(baseline);
const id='11111111-1111-4111-8111-111111111111',turnId='22222222-2222-4222-8222-222222222222',runId='33333333-3333-4333-8333-333333333333',route='/chat/'+id;
const literal='CUSTOMER 2026-11-15T08:09:10Z media Facebook TikTok <script>alert("x")</script>&';
const caps=Object.fromEntries(['chat-workspace-view','chat-thread-update','chat-context-create','chat-turn-create','chat-turn-state','chat-thread-restore-version','chat-run-submit','chat-run-refresh'].map(key=>[key,true]));
const execution={mode:'web_native_chat_run',run_submission_available:true,provider_execution_available:false,assistant_reply_available:false,cancel_available:false,provider_called:false,bot_called:false,wallet_mutated:false,payment_started:false,job_created:false,output_created:false,stream_available:false,output_delivery:'guarded'};
const baseRaw={chatWorkspaceEnabled:true,capabilities:caps,chatExecutionEnabled:false,chatExecutionReadState:'ready',chatExecution:execution,chatThreadDetail:{thread:{id,revision:7,state:'draft',mode:'focus',title:literal,objective:literal,tags:['media','Facebook','TikTok']},contexts:[],turns:[],versions:[],events:[]}};
const sessions=Object.fromEntries(['vi','en','zh'].map(locale=>[locale,{now:current(locale,route,baseRaw),old:before(locale,route,baseRaw)}]));
const zone=Intl.DateTimeFormat().resolvedOptions().timeZone,options={dateStyle:'medium',timeStyle:'short'},tags={vi:'vi-VN',en:'en-US',zh:'zh-CN'};
const expected=(locale,date)=>new Intl.DateTimeFormat(tags[locale],{...options,timeZone:zone}).format(new Date(date));
const freeze=value=>{if(value&&typeof value==='object'&&!Object.isFrozen(value)){Object.values(value).forEach(freeze);Object.freeze(value);}return value;};
const esc=(session,value)=>session.qa.safeText(String(value));
function context(session,value,state='draft',capability){
  const cap=arguments.length>=4?capability:true;
  return freeze({...session.context,capabilities:{...caps,'chat-turn-state':cap,'chat-thread-restore-version':cap,'chat-run-submit':cap,'chat-run-refresh':cap},chatRuns:[{id:runId,state:'guarded',assistant_message_id:'',updated_at:value,created_at:'2026-01-01T00:00:00Z'}],chatThreadDetail:{...baseRaw.chatThreadDetail,thread:{...baseRaw.chatThreadDetail.thread,state},turns:[{id:turnId,revision:2,ordinal:1,kind:'note',state:'active',body:literal,updated_at:value,created_at:'2026-01-01T00:00:00Z'}],versions:[{revision:6,title:literal,mode:'focus',state:'draft',created_at:value}],events:[{action:'thread_updated',revision:7,created_at:value}]}});
}
function render(session,value,state='draft',capability){
  const ctx=arguments.length>=4?context(session,value,state,capability):context(session,value,state),saved=JSON.stringify(ctx),page=session.qa.resolvePage(route),html=session.qa.renderChatWorkspaceDetail(page,ctx);
  assert.equal(JSON.stringify(ctx),saved);return {html,ctx};
}
const scopes=[
  /<li class="portal-chat-run-card">([\s\S]*?)<\/li>/,
  /<article class="portal-chat-turn(?: is-archived)?">([\s\S]*?)<\/article>/,
  /<div class="portal-chat-version-list"><article>([\s\S]*?)<\/article>/,
  /<div class="portal-chat-event-list"><div>([\s\S]*?)<\/div>/
];
function smalls(html){return scopes.map(pattern=>{const area=pattern.exec(html)?.[0];assert.ok(area,'All four actual date consumers remain');const match=/<small>([\s\S]*?)<\/small>/.exec(area);assert.ok(match);return {area,tag:match[0],text:match[1]};});}
const controlTags=html=>[...html.matchAll(/<(?:form|button|input|textarea|select|option|a)\b[^>]*>/g)].map(match=>match[0]);
function assertDateOnly(session,now,old,locale,value){
  const a=smalls(now.html),b=smalls(old.html),formatted=esc(session,expected(locale,value));let projected=now.html;
  for(let k=0;k<4;k++){
    assert.ok(a[k].text.includes(formatted),'Actual slot '+k+' uses independent Intl expectation in '+zone);
    assert.equal(a[k].area.split(a[k].tag).length-1,1);projected=projected.replace(a[k].area,a[k].area.replace(a[k].tag,b[k].tag));
  }
  assert.equal(projected,old.html,'Every non-date byte, label, order, attribute, state and customer literal stays exact');
  assert.deepEqual(controlTags(now.html),controlTags(old.html));assert.equal(JSON.stringify(now.ctx),JSON.stringify(old.ctx));
  assert.ok(now.html.includes('<p>'+esc(session,literal)+'</p>'));assert.equal(now.html.includes('<script>'),false);
}
for(const locale of ['vi','en','zh']){
  const {now,old}=sessions[locale];
  test(`${locale}: actual helper follows existing card parsing semantics and real per-render Intl/local timezone`,()=>{
    assert.equal(typeof now.qa.chatWorkspaceDateLabel,'function');
    const good=[['2026-11-15T08:09:10Z','2026-11-15T08:09:10Z'],['  2026-11-15T15:09:10+07:00  ','2026-11-15T15:09:10+07:00'],[new Date('2026-11-15T08:09:10Z'),'2026-11-15T08:09:10Z'],[1794729600000,1794729600000],[1,1],[-1,-1],['2026','2026']];
    for(const[value,date]of good){const time=value instanceof Date?value.getTime():null;if(value&&typeof value==='object')Object.freeze(value);assert.equal(now.qa.chatWorkspaceDateLabel(value),expected(locale,date));if(time!==null)assert.equal(value.getTime(),time);}
    const hostile=Object.freeze({[Symbol.toPrimitive](){throw Error('untrusted date');}}),bad=['','   ',null,undefined,false,true,0,'not-a-date','1700000000000','<img src=x onerror=alert(1)>',new Date(NaN),hostile];
    for(const value of bad)assert.equal(now.qa.chatWorkspaceDateLabel(value),'—');
    assert.equal(now.qa.withDateFormatter(()=>'',()=>now.qa.chatWorkspaceDateLabel(good[0][0])),'—');
    assert.equal(now.qa.withDateFormatter(()=>{throw Error('formatter unavailable');},()=>now.qa.chatWorkspaceDateLabel(good[0][0])),'—');
    const seen=[];now.qa.withDateFormatter((date,opts)=>{seen.push({valid:Number.isFinite(date.getTime()),opts});return 'FORMATTED';},()=>assert.equal(now.qa.chatWorkspaceDateLabel(good[0][0]),'FORMATTED'));
    assert.deepEqual(JSON.parse(JSON.stringify(seen)),[{valid:true,opts:options}]);
  });
  test(`${locale}: four actual full-detail date positions change only display with frozen stored data and protected controls`,()=>{
    for(const value of ['2026-11-15T08:09:10Z','2026-11-15T15:09:10+07:00'])for(const state of ['draft','review','ready','archived'])for(const cap of [true,false,'true',undefined])assertDateOnly(now,render(now,value,state,cap),render(old,value,state,cap),locale,value);
    const value='2026-11-15T08:09:10Z',hostile='<img src=x onerror="alert(1)"> \'&',html=now.qa.withDateFormatter(()=>hostile,()=>render(now,value).html);
    for(const slot of smalls(html)){assert.ok(slot.text.includes(esc(now,hostile)));assert.equal(slot.text.includes('<img'),false);assert.equal(slot.text.includes('&amp;lt;img'),false);}
    const dash=now.qa.withDateFormatter(()=>'',()=>render(now,value).html);for(const slot of smalls(dash))assert.ok(slot.text.includes('—'));
    const fallback=context(now,'', 'draft',true);assert.ok(JSON.stringify(fallback).includes('2026-01-01T00:00:00Z'));const rendered=now.qa.renderChatWorkspaceDetail(now.qa.resolvePage(route),fallback),cells=smalls(rendered);
    for(const slot of cells.slice(0,2))assert.ok(slot.text.includes(esc(now,expected(locale,'2026-01-01T00:00:00Z'))));for(const slot of cells.slice(2))assert.ok(slot.text.includes('—'));
  });
  test(`${locale}: SAME VM locale changes dates again, catalog remains byte-exact/frozen and root card behavior is unchanged`,()=>{
    const value='2026-11-15T08:09:10Z',next=locale==='vi'?'en':locale==='en'?'zh':'vi';
    try{now.setLocale(next);const a=smalls(render(now,value).html);for(const slot of a)assert.ok(slot.text.includes(esc(now,expected(next,value))));}finally{now.setLocale(locale);}
    assert.ok(Object.isFrozen(now.messages[locale]));assert.deepEqual(JSON.parse(JSON.stringify(Object.entries(now.messages[locale]))),JSON.parse(JSON.stringify(Object.entries(old.messages[locale]))));
    const raw={chatWorkspaceEnabled:true,capabilities:{'chat-workspace-view':true},chatThreads:[{...baseRaw.chatThreadDetail.thread,objective_excerpt:literal,updated_at:value,context_count:0,turn_count:0}]};
    const rootNow=current(locale,'/chat',raw),rootOld=before(locale,'/chat',raw);assert.equal(rootNow.html,rootOld.html);assert.equal(JSON.stringify(rootNow.context),JSON.stringify(rootOld.context));
  });
}
test('finite helper plus four call contexts normalize FIRST; partial/unknown/duplicate source and outside changes cannot hide',()=>{
  const hash=value=>createHash('sha256').update(value).digest('hex');
  assert.equal(hash(baseline.portal),'d0ef279f5e464291c82d0fd7e23cb199921f605396782750fd6b64e87b04eec9');assert.equal(hash(source.portal),'7cb8bfb238a3bc124887279e67045f11fce722b17771ac0c9be364a1a3a74b8f');
  assert.equal(source.i18n,baseline.i18n);assert.equal(chatDateHistoricalPortalSource(source.portal),baseline.portal);assert.equal(chatDateHistoricalPortalSource(baseline.portal),baseline.portal);
  for(const edit of chatDateChanges){
    assert.equal(source.portal.split(edit.new).length-1,1);assert.equal(baseline.portal.split(edit.old).length-1,1);
    assert.throws(()=>chatDateHistoricalPortalSource(source.portal.replace(edit.new,edit.old)),/Unreviewed Chat date source/);
    assert.throws(()=>chatDateHistoricalPortalSource(source.portal+'\n'+edit.new),/Unreviewed Chat date source/);
    assert.throws(()=>chatDateHistoricalPortalSource(source.portal.replace(edit.new,edit.new.replace('chatWorkspaceDateLabel','UNREVIEWED_DATE'))),/Unreviewed Chat date source/);
  }
  const outside=source.portal+'\n// CUSTOMER 2026-11-15T08:09:10Z media Facebook TikTok';assert.notEqual(chatDateHistoricalPortalSource(outside),baseline.portal);assert.ok(chatDateHistoricalPortalSource(outside).endsWith('Facebook TikTok'));
});
