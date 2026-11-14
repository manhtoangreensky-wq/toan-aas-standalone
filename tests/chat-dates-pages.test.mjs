import test from 'node:test';
import assert from 'node:assert/strict';
import {datePagesRenderer,datePagesSources} from './helpers/chat-dates-pages-runtime.mjs';
import {datePagesHistoricalSnapshot,datePagesHistoricalPortalSource} from './helpers/chat-dates-pages-snapshot.mjs';
const sources=datePagesSources(),priorSources=datePagesSources(true);
const render=await datePagesRenderer(sources),before=await datePagesRenderer(priorSources);
const id='11111111-1111-4111-8111-111111111111',tags={vi:'vi-VN',en:'en-US',zh:'zh-CN'};
const copy={
  vi:{chatPagesUiAria:'Chuyển trang hội thoại',chatPagesUiSummary:'Hiển thị {from}–{to} / {total} cuộc trò chuyện',chatPagesUiPrevious:'← Trước',chatPagesUiNext:'Sau →'},
  en:{chatPagesUiAria:'Conversation pages',chatPagesUiSummary:'Showing {from}–{to} / {total} conversations',chatPagesUiPrevious:'← Previous',chatPagesUiNext:'Next →'},
  zh:{chatPagesUiAria:'对话分页',chatPagesUiSummary:'显示第 {from}–{to} 条，共 {total} 条对话',chatPagesUiPrevious:'← 上一页',chatPagesUiNext:'下一页 →'}
};
const item=value=>({id,title:'CUSTOMER studio Bot <script>&',objective_excerpt:'CUSTOMER_GOAL',tags:['Bot','provider'],state:'draft',mode:'focus',context_count:7,turn_count:11,revision:9,updated_at:value});
const raw={capabilities:{'chat-workspace-view':true},chatWorkspaceEnabled:true};
const sessions=Object.fromEntries(['vi','en','zh'].map(locale=>[locale,{now:render(locale,'/chat',raw),old:before(locale,'/chat',raw)}]));
const card=(session,record)=>session.qa.renderChatWorkspaceCards([record],session.context);
const date=html=>{const m=/<div class="portal-chat-workspace-meta"><span>[\s\S]*?<\/span><span>[\s\S]*?<\/span><span>([\s\S]*?)<\/span><\/div>/.exec(html);assert.ok(m);return m[1];};
const expectedDate=(locale,value)=>new Intl.DateTimeFormat(tags[locale],{dateStyle:'medium',timeStyle:'short'}).format(new Date(value));
const attrs=html=>[...html.matchAll(/<[^>]+>/g)].map(m=>m[0].replace(/ aria-label="[^"]*"/,' aria-label="__LOCALIZED__"'));
const pages=(session,pagination,enabled=true)=>session.qa.renderChatWorkspacePagination({pagination},enabled);
function checkPage(session,old,locale,input,range,offsets,disabled,enabled=true){
  const saved=JSON.stringify(input),html=pages(session,input,enabled),prior=pages(old,input,enabled),c=copy[locale];
  assert.equal(JSON.stringify(input),saved);assert.deepEqual(attrs(html),attrs(prior));
  const summary=c.chatPagesUiSummary.replace('{from}',String(range[0])).replace('{to}',String(range[1])).replace('{total}',String(range[2]));
  assert.ok(html.includes('aria-label="'+c.chatPagesUiAria+'"'));assert.ok(html.includes('<span>'+summary+'</span>'));
  assert.ok(html.includes('>'+c.chatPagesUiPrevious+'</button>'));assert.ok(html.includes('>'+c.chatPagesUiNext+'</button>'));
  const buttons=[...html.matchAll(/<button\b([^>]*)>([\s\S]*?)<\/button>/g)];assert.equal(buttons.length,2);
  for(let i=0;i<2;i++){
    assert.ok(buttons[i][1].includes('data-portal-action="chat-workspace-page"'));
    assert.ok(buttons[i][1].includes('data-portal-route="/chat"'));
    assert.ok(buttons[i][1].includes('data-chat-workspace-offset="'+offsets[i]+'"'));
    assert.equal(/\sdisabled(?:\s|$)/.test(buttons[i][1]),disabled[i]);
  }
}
for(const locale of ['vi','en','zh']){
  const {now,old}=sessions[locale];
  test(`${locale}: valid UTC, offset and Date values use active locale without changing stored input`,()=>{
    for(const value of ['2026-11-14T08:00:00Z','2026-11-14T18:20:00+05:30',new Date('2026-04-03T21:15:00Z')]){
      const record=item(value),saved=JSON.stringify(record);
      assert.equal(date(card(now,record)),expectedDate(locale,value));assert.equal(JSON.stringify(record),saved);
    }
  });
  test(`${locale}: missing/null/empty/whitespace/invalid dates never expose raw values or exceptions`,()=>{
    for(const value of [undefined,null,'',' \t ','not-a-date','2026-13-99T80:00:00Z',new Date(NaN),false,true])assert.equal(date(card(now,item(value))),'—');
  });
  test(`${locale}: failed or empty formatter safely shows dash`,()=>{
    for(const format of [()=>{throw Error('PRIVATE_FORMAT_ERROR');},()=>''])assert.equal(date(now.qa.withDateFormatter(format,()=>card(now,item('2026-11-14T08:00:00Z')))),'—');
  });
  test(`${locale}: date locale changes after initialization and customer data/controls remain exact`,()=>{
    const value='2026-11-14T08:00:00Z',record=item(value),saved=JSON.stringify(record),html=card(now,record),prior=card(old,record);
    assert.ok(html.includes(now.qa.safeText(record.title)));assert.deepEqual(attrs(html),attrs(prior));
    assert.equal(html.replace(date(html),'__DATE__'),prior.replace(date(prior),'__DATE__'));
    const next=locale==='vi'?'en':locale==='en'?'zh':'vi';
    try{now.setLocale(next);assert.equal(date(card(now,record)),expectedDate(next,value));}finally{now.setLocale(locale);}
    assert.equal(JSON.stringify(record),saved);
  });
  test(`${locale}: pagination with no total creates no empty placeholder`,()=>{
    for(const listing of [null,undefined,{}, {pagination:{}},{pagination:{total:0}},{pagination:{total:'0'}}])assert.equal(now.qa.renderChatWorkspacePagination(listing,true),'');
  });
  test(`${locale}: first/middle/last retain range math, order, offsets and button gates`,()=>{
    for(const [input,range,offsets,disabled]of [
      [{total:75,offset:0,returned:20,previous_offset:null,next_offset:20},[1,20,75],[0,20],[true,false]],
      [{total:'75',offset:'20',returned:'20',previous_offset:'0',next_offset:'40'},[21,40,75],[0,40],[false,false]],
      [{total:75,offset:60,returned:15,previous_offset:40,next_offset:null},[61,75,75],[40,0],[false,true]]
    ])checkPage(now,old,locale,input,range,offsets,disabled);
  });
  test(`${locale}: disabled and invalid previous/next values never gain navigation`,()=>{
    checkPage(now,old,locale,{total:75,offset:20,returned:20,previous_offset:0,next_offset:40},[21,40,75],[0,40],[true,true],false);
    for(const offset of [null,undefined,-1,'2.5','INVALID'])checkPage(now,old,locale,{total:5,offset:20,returned:-3,previous_offset:offset,next_offset:offset},[5,5,5],[0,0],[true,true]);
  });
  test(`${locale}: pagination aria/summary/buttons follow locale changes per render`,()=>{
    const next=locale==='vi'?'en':locale==='en'?'zh':'vi';
    try{now.setLocale(next);checkPage(now,old,next,{total:75,offset:0,returned:20,previous_offset:null,next_offset:20},[1,20,75],[0,20],[true,false]);}finally{now.setLocale(locale);}
  });
  test(`${locale}: exactly four appended keys preserve every old value, order and frozen catalog`,()=>{
    const a=Object.entries(now.messages[locale]),b=Object.entries(old.messages[locale]);
    assert.deepEqual(JSON.parse(JSON.stringify(a.slice(0,b.length))),JSON.parse(JSON.stringify(b)));
    assert.deepEqual(JSON.parse(JSON.stringify(a.slice(b.length))),Object.entries(copy[locale]));
    assert.ok(Object.isFrozen(now.messages[locale]));
  });
  test(`${locale}: historical adapter rejects partial/mutated/reordered copy and retains unknown keys`,()=>{
    const entries=Object.entries(now.messages[locale]),normalized=datePagesHistoricalSnapshot(entries,locale);
    assert.equal(normalized.length,entries.length-4);
    for(const key of Object.keys(copy[locale])){
      assert.throws(()=>datePagesHistoricalSnapshot(entries.filter(([k])=>k!==key),locale),/Unreviewed Chat dates\/pages copy/);
      assert.throws(()=>datePagesHistoricalSnapshot(entries.map(([k,v])=>[k,k===key?'UNKNOWN':v]),locale),/Unreviewed Chat dates\/pages copy/);
    }
    assert.throws(()=>datePagesHistoricalSnapshot([...normalized,...Object.entries(copy[locale]).toReversed()],locale),/Unreviewed Chat dates\/pages copy/);
    const unknown=['chatPagesUiUnknown','CUSTOMER media studio'];
    assert.deepEqual(datePagesHistoricalSnapshot([...entries,unknown],locale).at(-1),unknown);
  });
}
test('reviewed full-span source normalization never hides unknown edits or the second date occurrence',()=>{
  assert.ok(sources.portal!==priorSources.portal);
  assert.equal(datePagesHistoricalPortalSource(sources.portal),priorSources.portal);
  for(const [start,end,before,after]of [
    ['  function renderChatWorkspacePagination(listing, enabled) {','  function renderChatWorkspaceTags(','    const total = Number(pagination.total || 0);','    const total = Number(pagination.total || 1);'],
    ['  function renderChatWorkspaceCards(items, context) {','  function renderChatWorkspace(page, context) {','    if (!Number.isFinite(date.getTime())) return "—";','    if (false) return "—";']
  ]){
    const a=sources.portal.indexOf(start),b=sources.portal.indexOf(end,a),span=sources.portal.slice(a,b);
    assert.ok(a>=0&&b>a);assert.equal(span.split(before).length-1,1);
    const mutated=sources.portal.slice(0,a)+span.replace(before,after)+sources.portal.slice(b);
    assert.throws(()=>datePagesHistoricalPortalSource(mutated),/Unreviewed Chat dates\/pages source/);
  }
  assert.ok(datePagesHistoricalPortalSource(sources.portal+'\n// UNKNOWN_SOURCE').endsWith('// UNKNOWN_SOURCE'));
  assert.equal(sources.portal.split('safeText(String(item.updated_at || "—"))').length-1,1);
});
