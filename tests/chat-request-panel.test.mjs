import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {requestPanelRenderer,requestPanelSources} from './helpers/chat-request-panel-runtime.mjs';
import {requestPanelHistoricalSnapshot,requestPanelHistoricalPortalSource,requestPanelHistoricalCss,requestPanelCssOld,requestPanelCssNew,requestPanelSpans,requestStatusWrapRules} from './helpers/chat-request-panel-snapshot.mjs';
import {historyHistoricalPortalSource,historyHistoricalSnapshot} from './helpers/chat-history-snapshot.mjs';
import {pageMetaHistoricalSnapshot,pageMetaHistoricalPortalSource} from './helpers/chat-page-meta-snapshot.mjs';
import {imageEditCustomerHistoricalSource} from './helpers/image-edit-customer-copy-snapshot.mjs';
const live=requestPanelSources(),source={...live,portal:pageMetaHistoricalPortalSource(live.portal)},oldSource=requestPanelSources(true);
// Historical CSS comparator only; source.css and runtime renderer retain physical CSS.
const historicalCss=imageEditCustomerHistoricalSource(source.css,'static/portal/portal.css');
const actual=await requestPanelRenderer(source),before=await requestPanelRenderer(oldSource);
const current=(...args)=>{
  const result=actual(...args);
  return {...result,catalogFrozen:Object.fromEntries(['vi','en','zh'].map(locale=>[locale,Object.isFrozen(result.messages[locale])])),messages:Object.fromEntries(['vi','en','zh'].map(locale=>[
    locale,Object.fromEntries(pageMetaHistoricalSnapshot(Object.entries(result.messages[locale]),locale))
  ]))};
};
const copy=JSON.parse(fs.readFileSync(new URL('./fixtures/chat-request-panel-reviewed.json',import.meta.url),'utf8'));
const id='11111111-1111-4111-8111-111111111111',route='/chat/'+id,literal='CUSTOMER media studio Bot provider Facebook TikTok <script>alert("x")</script>&';
const thread={id,revision:7,state:'draft',mode:'focus',title:literal,objective:literal,tags:['media','studio','Bot','provider','Facebook','TikTok']};
const execution={mode:'web_native_chat_run',run_submission_available:true,provider_execution_available:false,assistant_reply_available:false,cancel_available:false,provider_called:false,bot_called:false,wallet_mutated:false,payment_started:false,job_created:false,output_created:false,stream_available:false,output_delivery:'guarded'};
const projectionFlags=Object.keys(execution).filter(key=>execution[key]===false);
const baseContext={chatWorkspaceEnabled:true,chatExecutionEnabled:false,chatExecutionReadState:'ready',chatExecution:execution,chatRuns:[],capabilities:{'chat-workspace-view':true,'chat-run-submit':true,'chat-run-refresh':true},chatThreadDetail:{thread,contexts:[],turns:[],versions:[],events:[]}};
const sessions=Object.fromEntries(['vi','en','zh'].map(locale=>[locale,{now:current(locale,route,baseContext),old:before(locale,route,baseContext)}]));
const freeze=value=>{if(value&&typeof value==='object'&&!Object.isFrozen(value)){Object.values(value).forEach(freeze);Object.freeze(value);}return value;};
const esc=(session,text)=>session.qa.safeText(String(text)),attr=(tag,name)=>new RegExp(name+'="([^"]*)"').exec(tag)?.[1];
function render(session,changes={}){
  const {threadState,submit,refresh,...rest}=changes,context=freeze({...session.context,...rest,capabilities:{...session.context.capabilities,'chat-run-submit':Object.hasOwn(changes,'submit')?submit:true,'chat-run-refresh':Object.hasOwn(changes,'refresh')?refresh:true},chatThreadDetail:{...session.context.chatThreadDetail,thread:{...thread,state:threadState||'draft'}}});
  const saved=JSON.stringify(context),html=session.qa.renderChatWorkspaceDetail(session.page,context);assert.equal(JSON.stringify(context),saved);return html;
}
function panel(html){
  const a=html.indexOf('<section class="portal-card portal-card-pad portal-chat-execution">');assert.ok(a>=0);let depth=0;
  for(const match of html.slice(a).matchAll(/<\/?section\b[^>]*>/g)){depth+=match[0].startsWith('</')?-1:1;if(depth===0)return html.slice(a,a+match.index+match[0].length);}assert.fail('Unclosed actual request panel');
}
const strip=html=>{const a=html.indexOf('<div class="portal-chat-execution-status">'),b=html.indexOf('<div class="portal-chat-execution-layout">',a);assert.ok(a>=0&&b>a);return html.slice(a,b);};
const timeline=html=>/<ol class="portal-chat-run-timeline"[\s\S]*?<\/ol>/.exec(html)?.[0]||'';
const rows=html=>[...timeline(html).matchAll(/<li class="portal-chat-run-card">([\s\S]*?)<\/li>/g)].map(match=>match[1]);
const tags=html=>[...html.replace(/aria-label="[^"]*"/g,'aria-label="__COPY__"').replace(/data-portal-confirm="[^"]*"/g,'data-portal-confirm="__COPY__"').matchAll(/<[^>]+>/g)].map(match=>match[0]);
const controls=html=>[...html.matchAll(/<(?:form|input|select|textarea|button)\b[^>]*>/g)].map(match=>match[0].replace(/data-portal-confirm="[^"]*"/g,'data-portal-confirm="__COPY__"'));
const uuid=n=>`${String(n).padStart(8,'0')}-1111-4111-8111-111111111111`;
const states=['draft','queued','processing','completed','failed','guarded','cancelled','UNKNOWN','COMPLETED','__proto__','constructor'];
const runs=states.map((state,k)=>({id:uuid(k+1),state,assistant_message_id:'',updated_at:k%3?'':literal,created_at:k%3===1?'2026-11-15T08:09:10+07:00':''}));
function checkRows(session,html,records,locale){
  const e=copy[locale],found=rows(html);assert.equal(found.length,records.length);assert.ok(timeline(html).includes('aria-label="'+esc(session,e.chatRunTimelineUiAria)+'"'));
  for(let k=0;k<records.length;k++){
    const item=records[k],row=found[k],state=String(item.state||'').toLowerCase(),known=['draft','queued','processing','completed','failed','guarded','cancelled'],normal=known.includes(state)?state:'guarded',suffix=normal[0].toUpperCase()+normal.slice(1),label=esc(session,e['chatRunTimelineUiState'+suffix]);
    assert.ok(row.includes('<h3>'+label+'</h3>'));assert.ok(row.includes('<span class="portal-badge" data-status="'+normal+'">'+label+'</span>'));
    assert.ok(row.includes('<span class="portal-section-kicker">'+esc(session,e.chatRunTimelineUiKicker)+'</span>'));assert.ok(row.includes('<p>'+esc(session,e.chatRunTimelineUiBody)+'</p>'));
    assert.ok(row.includes('<small>'+esc(session,String(item.updated_at||item.created_at||'—'))+'</small>'));assert.equal(row.includes('<script>'),false);
  }
}
function checkPanel(session,locale,html,prior,changes){
  const e=copy[locale],a=panel(html),b=panel(prior),status=strip(a),oldStatus=strip(b),rest=a.replace(status,''),oldRest=b.replace(oldStatus,'');
  assert.deepEqual(tags(rest),tags(oldRest));assert.deepEqual(controls(a),controls(b));assert.equal((status.match(/<em>/g)||[]).length,2);assert.equal((oldStatus.match(/<em>/g)||[]).length,4);
  const available=Object.hasOwn(changes,'chatExecution')?Boolean(changes.chatExecution&&changes.chatExecution.run_submission_available===true&&changes.valid!==false):true;
  assert.equal(status,'<div class="portal-chat-execution-status"><span><strong>'+esc(session,e.chatExecutionUiReceiveLabel)+'</strong><em>'+esc(session,e[available?'chatExecutionUiReceiveAvailable':'chatExecutionUiReceiveUnavailable'])+'</em></span><span><strong>'+esc(session,e.chatExecutionUiReplyLabel)+'</strong><em>'+esc(session,e.chatExecutionUiReplyUnavailable)+'</em></span></div>');
  const form=/<form\b[^>]*data-portal-action="chat-run-submit"[^>]*>/.exec(a)?.[0],button=/<button\b[^>]*type="submit"[^>]*>/.exec(a)?.[0],refresh=/<button\b[^>]*data-portal-action="chat-run-refresh"[^>]*>/.exec(a)?.[0];assert.ok(form&&button&&refresh);
  for(const tag of [form,refresh]){assert.equal(attr(tag,'data-portal-route'),route);assert.equal(attr(tag,'data-chat-thread-id'),id);assert.equal(attr(tag,'data-chat-thread-revision'),'7');assert.equal(attr(tag,'data-chat-thread-state'),changes.threadState||'draft');}
  assert.equal(/\sdisabled(?:\s|>)/.test(button),!(Object.hasOwn(changes,'submit')?changes.submit===true:true)||!available||(changes.threadState||'draft')!=='draft');
  assert.equal(/\sdisabled(?:\s|>)/.test(refresh),!(Object.hasOwn(changes,'refresh')?changes.refresh===true:true));assert.equal(attr(form,'data-portal-confirm'),esc(session,e.chatExecutionUiConfirm));
  const unconfirmed=changes.valid===false||(changes.chatExecutionReadState||'ready')!=='ready',readiness=unconfirmed?'Unconfirmed':changes.chatExecutionEnabled===true?'Confirmed':'Disabled';
  assert.ok(a.includes('<p class="portal-card-subtitle">'+esc(session,e['chatExecutionUiReadiness'+readiness])+'</p>'));
  for(const suffix of ['Kicker','Title','SafetyNote','Submit','Refresh','ComposerHeading','TimelineKicker','RecentTitle'])assert.ok(a.includes(esc(session,e['chatExecutionUi'+suffix])));
  assert.ok(html.includes(esc(session,literal)));assert.equal(html.includes('<script>'),false);
}
for(const locale of ['vi','en','zh']){
  const {now,old}=sessions[locale];
  test(`${locale}: full detail preserves controls/attributes/fields and existing strict gates in every projection/read/flag case`,()=>{
    const cases=[];for(const threadState of ['draft','review','ready','archived'])for(const capability of [true,false,'true',undefined])for(const chatExecutionEnabled of [true,false])cases.push({threadState,submit:capability,refresh:capability,chatExecutionEnabled});
    for(const chatExecutionReadState of ['ready','pending','failed','guarded'])for(const chatExecutionEnabled of [true,false])cases.push({chatExecutionReadState,chatExecutionEnabled});
    for(const flag of projectionFlags)cases.push({chatExecution:{...execution,[flag]:true},valid:false});
    for(const chatExecution of [null,undefined,{},{...execution,mode:'INVALID'},{...execution,run_submission_available:'true'},{...execution,output_delivery:'ready'},{...execution,run_submission_available:false}])cases.push({chatExecution,valid:chatExecution?.run_submission_available===false});
    for(const changes of cases){const input={...changes};delete input.valid;const a=render(now,input),b=render(old,input);checkPanel(now,locale,a,b,changes);}
  });
  test(`${locale}: actual timeline keeps seven states/unknown/case, filter, first50/order and literal times with frozen input`,()=>{
    const ignored=[{id:'INVALID',state:'completed',assistant_message_id:''},{id:uuid(90),state:'completed',assistant_message_id:'answer'}],input=[...ignored,...runs];
    const a=render(now,{chatRuns:input}),b=render(old,{chatRuns:input});checkRows(now,a,runs,locale);assert.deepEqual(tags(timeline(a)),tags(timeline(b)));
    const many=Array.from({length:55},(_,k)=>({id:uuid(k+101),state:states[k%states.length],assistant_message_id:'',updated_at:'LITERAL-'+k}));checkRows(now,render(now,{chatRuns:many}),many.slice(0,50),locale);
    for(const chatRuns of [[],ignored,undefined,null]){const empty=panel(render(now,{chatRuns}));assert.equal(timeline(empty),'');assert.ok(empty.includes('<h3>'+esc(now,copy[locale].chatRunTimelineUiEmptyTitle)+'</h3>'));assert.ok(empty.includes('<p>'+esc(now,copy[locale].chatRunTimelineUiEmptyBody)+'</p>'));}
  });
  test(`${locale}: per-render locale/VI fallback, fixed29 copy, catalog order/freeze and single escaping remain exact`,()=>{
    const entries=Object.entries(now.messages[locale]),previous=Object.entries(old.messages[locale]);assert.equal(now.catalogFrozen[locale],true);assert.deepEqual(JSON.parse(JSON.stringify(entries.slice(0,previous.length))),JSON.parse(JSON.stringify(previous)));assert.deepEqual(JSON.parse(JSON.stringify(entries.slice(previous.length))),Object.entries(copy[locale]));
    const next=locale==='vi'?'en':locale==='en'?'zh':'vi';try{now.setLocale(next);checkRows(now,render(now,{chatRuns:runs}),runs,next);checkPanel(now,next,render(now),render(sessions[next].old),{});}finally{now.setLocale(locale);}
    const fallback=now.qa.withUiText((key,value)=>value,()=>render(now,{chatRuns:runs}));checkRows(now,fallback,runs,'vi');checkPanel(now,'vi',fallback,render(sessions.vi.old,{chatRuns:runs}),{});
    const empty=now.qa.withUiText((key,value)=>value,()=>panel(render(now)));for(const key of ['chatRunTimelineUiEmptyTitle','chatRunTimelineUiEmptyBody'])assert.ok(empty.includes(esc(now,copy.vi[key])));
    const hostile='<img src=x onerror="alert(1)"> \'&',html=now.qa.withUiText(()=>hostile,()=>panel(render(now,{chatRuns:runs})));assert.equal(html.includes('<img'),false);assert.equal(html.includes('&amp;lt;img'),false);assert.ok(html.includes('data-portal-confirm="'+esc(now,hostile)+'"'));assert.ok(html.includes('aria-label="'+esc(now,hostile)+'"'));
    const normalized=requestPanelHistoricalSnapshot(entries,locale);assert.deepEqual(JSON.parse(JSON.stringify(normalized)),JSON.parse(JSON.stringify(previous)));
    for(const key of Object.keys(copy[locale])){assert.throws(()=>requestPanelHistoricalSnapshot(entries.filter(([name])=>name!==key),locale),/Unreviewed Chat request copy/);assert.throws(()=>requestPanelHistoricalSnapshot(entries.map(([name,value])=>[name,name===key?'UNREVIEWED':value]),locale),/Unreviewed Chat request copy/);}
    assert.throws(()=>requestPanelHistoricalSnapshot([...normalized,...Object.entries(copy[locale]).toReversed()],locale),/Unreviewed Chat request copy/);assert.throws(()=>requestPanelHistoricalSnapshot([...entries,['chatExecutionUiUnknownKey','UNKNOWN']],locale),/Unreviewed Chat request copy/);
    const customer=['customer.literal',literal];assert.deepEqual(requestPanelHistoricalSnapshot([...entries,customer],locale).at(-1),customer);assert.deepEqual(historyHistoricalSnapshot(normalized,locale),historyHistoricalSnapshot(previous,locale));
  });
}
test('strict three-function spans normalize before the prior whole-detail history gate, retaining all protected source',()=>{
  const normalized=requestPanelHistoricalPortalSource(source.portal);assert.equal(normalized,oldSource.portal);assert.equal(requestPanelHistoricalPortalSource(oldSource.portal),oldSource.portal);assert.equal(historyHistoricalPortalSource(normalized),historyHistoricalPortalSource(oldSource.portal));
  for(const [name,start,end]of requestPanelSpans){
    const a=source.portal.indexOf(start),b=source.portal.indexOf(end,a),part=source.portal.slice(a,b),anchor=name==='chatRunBadge'?'const state = chatRunState(value);':name==='renderChatRunTimeline'?'const runs = ':'const execution = ';assert.equal(part.split(anchor).length-1,1);
    assert.throws(()=>requestPanelHistoricalPortalSource(source.portal.slice(0,a)+part.replace(anchor,anchor.replace('const ','let '))+source.portal.slice(b)),/Unreviewed Chat request source/);
    const oa=oldSource.portal.indexOf(start),ob=oldSource.portal.indexOf(end,oa);assert.throws(()=>requestPanelHistoricalPortalSource(source.portal.slice(0,a)+oldSource.portal.slice(oa,ob)+source.portal.slice(b)),/Unreviewed Chat request source/);
  }
  assert.ok(requestPanelHistoricalPortalSource(source.portal+'\n// OUTSIDE_LITERAL').endsWith('// OUTSIDE_LITERAL'));
});
test('CSS accepts only the exact desktop property edit; all other CSS and mobile overrides remain visible to the old comparator',()=>{
  assert.equal(requestPanelHistoricalCss(historicalCss),oldSource.css);assert.equal(requestPanelHistoricalCss(oldSource.css),oldSource.css);assert.equal(historicalCss.split(requestPanelCssNew).length-1,1);assert.equal(oldSource.css.split(requestPanelCssOld).length-1,1);
  for(const altered of [historicalCss.replace(requestPanelCssNew,requestPanelCssNew.replace('repeat(2','repeat(3')),historicalCss+'\n'+requestPanelCssNew])assert.throws(()=>requestPanelHistoricalCss(altered),/Unreviewed Chat request CSS/);
  const outside=historicalCss+'\n/* CUSTOMER media studio Bot provider Facebook TikTok */';assert.notEqual(requestPanelHistoricalCss(outside),oldSource.css);assert.ok(requestPanelHistoricalCss(outside).endsWith('TikTok */'));
});
test('status labels and values wrap instead of clipping; only the two reviewed CSS rules can project to the old source',()=>{
  for(const[old,next]of requestStatusWrapRules){
    assert.equal(historicalCss.split(next).length-1,1,'Reviewed wrapping rule must be present');
    assert.equal(historicalCss.includes(old),false);
    assert.throws(()=>requestPanelHistoricalCss(historicalCss.replace(next,old)),/Unreviewed Chat request CSS: partial status wrap/);
    assert.throws(()=>requestPanelHistoricalCss(historicalCss+'\n'+next),/Unreviewed Chat request CSS: status wrap rule count/);
    assert.throws(()=>requestPanelHistoricalCss(historicalCss.replace(next,next.replace('overflow: visible','overflow: hidden'))),/Unreviewed Chat request CSS: status wrap rule count/);
  }
  assert.equal(requestPanelHistoricalCss(historicalCss),oldSource.css);
});
