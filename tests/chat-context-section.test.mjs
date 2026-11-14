import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {cardsTurnHistoricalSnapshot,cardsTurnHistoricalPortalSource} from './helpers/chat-context-cards-turn-snapshot.mjs';
import {contextSectionRenderer,contextSectionSources} from './helpers/chat-context-section-runtime.mjs';
import {contextSectionHistoricalSnapshot,contextSectionHistoricalPortalSource} from './helpers/chat-context-section-snapshot.mjs';
import {summaryHistoricalPortalSource} from './helpers/chat-detail-summary-editor-snapshot.mjs';

const live=contextSectionSources(),source={...live,portal:cardsTurnHistoricalPortalSource(live.portal)},oldSource=contextSectionSources(true);
const actual=await contextSectionRenderer(source),before=await contextSectionRenderer(oldSource);
const current=(...args)=>{
  const result=actual(...args);
  return {...result,catalogFrozen:Object.fromEntries(['vi','en','zh'].map(locale=>[locale,Object.isFrozen(result.messages[locale])])),messages:Object.fromEntries(['vi','en','zh'].map(locale=>[
    locale,Object.fromEntries(cardsTurnHistoricalSnapshot(Object.entries(result.messages[locale]),locale))
  ]))};
};
const copy=JSON.parse(fs.readFileSync(new URL('./fixtures/chat-context-section-reviewed.json',import.meta.url),'utf8'));
const id='11111111-1111-4111-8111-111111111111',route='/chat/'+id;
const literal='CUSTOMER media studio OpenAI TOAN AAS <script>alert("Bot")</script>&';
const thread={id,revision:7,state:'draft',mode:'focus',pinned:true,title:literal,objective:literal,tags:['media','studio','OpenAI','Bot']};
const raw={chatWorkspaceEnabled:true,capabilities:{'chat-workspace-view':true,'chat-thread-create':true,'chat-thread-update':true,'chat-context-create':true,'chat-turn-create':true},chatThreadDetail:{thread,contexts:[],turns:[],versions:[],events:[]}};
const sessions=Object.fromEntries(['vi','en','zh'].map(locale=>[locale,{now:current(locale,route,raw),old:before(locale,route,raw)}]));
const tags=html=>[...html.matchAll(/<[^>]+>/g)].map(match=>match[0]);
function detail(session,state,capability){
  // No default capability: an explicitly passed undefined MUST remain denied.
  const context={...session.context,capabilities:{...session.context.capabilities,'chat-context-create':capability,'chat-turn-create':capability},chatThreadDetail:{...session.context.chatThreadDetail,thread:{...thread,state}}};
  const saved=JSON.stringify(context),html=session.qa.renderChatWorkspaceDetail(session.page,context);
  assert.equal(JSON.stringify(context),saved);return html;
}
function panel(html,action){
  const at=html.indexOf('data-portal-action="'+action+'"'),a=html.lastIndexOf('<section class="portal-card portal-card-pad">',at),b=html.indexOf('</form></section>',at);
  assert.ok(at>=0&&a>=0&&b>a);return html.slice(a,b+'</form></section>'.length);
}
function pinned(html){
  const match=/<label class="portal-checkbox"[^>]*>(<input\b[^>]*name="pinned"[^>]*>)<span>([\s\S]*?)<\/span><\/label>/.exec(html);
  assert.ok(match,'real pinned checkbox must remain');return match;
}
for(const locale of ['vi','en','zh']){
  const {now,old}=sessions[locale],e=copy[locale];
  test(`${locale}: creation/section copy preserves exact structures, customer content and strict write gates`,()=>{
    for(const state of ['draft','review','ready','archived'])for(const cap of [true,false,'true',undefined]){
      const html=detail(now,state,cap),prior=detail(old,state,cap);assert.deepEqual(tags(html),tags(prior));
      assert.ok(html.includes(now.qa.safeText(literal)));assert.ok(html.includes('<span>media</span><span>studio</span><span>OpenAI</span><span>Bot</span>'));
      for(const [kind,action]of [['Context','chat-context-create'],['Turn','chat-turn-create']]){
        const actual=panel(html,action),previous=panel(prior,action);assert.deepEqual(tags(actual),tags(previous));
        for(const suffix of ['Kicker','Title','Subtitle','Note','Submit'])assert.ok(actual.includes(now.qa.safeText(e['chatDetailContextUi'+kind+suffix])));
        const submit=/<button class="portal-button portal-button--primary" type="submit"([^>]*)>/.exec(actual);assert.ok(submit);
        assert.equal(submit[1].includes('disabled'),!(state==='draft'&&cap===true));
        assert.ok(actual.includes('data-chat-thread-id="'+id+'"'));assert.ok(actual.includes('data-chat-thread-revision="7"'));
        assert.ok(actual.includes('data-portal-route="'+route+'"'));assert.equal(actual.includes('class="portal-badge"'),false);
      }
      for(const key of Object.keys(e).filter(key=>key.startsWith('chatDetailSectionUi')&&!key.endsWith('PinnedCheck')))assert.ok(html.includes(now.qa.safeText(e[key])));
    }
  });
  test(`${locale}: root/create and detail/editor checkboxes keep values, IDs, checked and disabled state`,()=>{
    for(const cap of [true,false,'true',undefined]){
      const rootRaw={...raw,capabilities:{...raw.capabilities,'chat-thread-create':cap}};
      const a=current(locale,'/chat',rootRaw),b=before(locale,'/chat',rootRaw),x=pinned(a.html),y=pinned(b.html);
      assert.equal(x[1],y[1]);assert.equal(x[2],a.qa.safeText(e.chatDetailSectionUiPinnedCheck));
      assert.ok(x[1].includes('type="checkbox" value="true"'));assert.equal(x[1].includes(' disabled'),cap!==true);assert.equal(x[1].includes(' checked'),false);
      for(const checked of [false,true]){
        const detailRaw={...raw,capabilities:{...raw.capabilities,'chat-thread-update':cap},chatThreadDetail:{...raw.chatThreadDetail,thread:{...thread,pinned:checked}}};
        const c=current(locale,route,detailRaw),d=before(locale,route,detailRaw),m=pinned(c.html),n=pinned(d.html);
        assert.equal(m[1],n[1]);assert.equal(m[2],c.qa.safeText(e.chatDetailSectionUiPinnedCheck));
        assert.equal(m[1].includes(' checked'),checked);assert.equal(m[1].includes(' disabled'),cap!==true);
        assert.ok(m[1].includes('id="portal-field-chat-thread-editor-'+id+'-pinned"'));
      }
    }
  });
  test(`${locale}: runtime locale, escaping and exact frozen catalog/strict historical values remain`,()=>{
    const a=Object.entries(now.messages[locale]),b=Object.entries(old.messages[locale]);
    assert.equal(now.catalogFrozen[locale],true);assert.deepEqual(JSON.parse(JSON.stringify(a.slice(0,b.length))),JSON.parse(JSON.stringify(b)));
    assert.deepEqual(JSON.parse(JSON.stringify(a.slice(b.length))),Object.entries(e));
    const next=locale==='vi'?'en':locale==='en'?'zh':'vi';
    try{
      now.setLocale(next);const html=detail(now,'draft',true);
      assert.ok(html.includes(now.qa.safeText(copy[next].chatDetailContextUiContextTitle)));
      assert.ok(html.includes(now.qa.safeText(copy[next].chatDetailSectionUiTurnTitle)));
      assert.equal(pinned(html)[2],now.qa.safeText(copy[next].chatDetailSectionUiPinnedCheck));
    }finally{now.setLocale(locale);}
    const hostile='<img src=x onerror="alert(1)"> \'&';
    const html=now.qa.withUiText(()=>hostile,()=>detail(now,'draft',true));
    for(const action of ['chat-context-create','chat-turn-create']){
      const actual=panel(html,action);assert.equal(actual.includes('<img'),false);assert.ok(actual.includes(now.qa.safeText(hostile)));assert.equal(actual.includes('&amp;lt;img'),false);
    }
    assert.equal(pinned(html)[2],now.qa.safeText(hostile));
    const normalized=contextSectionHistoricalSnapshot(a,locale);assert.equal(normalized.length,a.length-17);
    for(const key of Object.keys(e)){
      assert.throws(()=>contextSectionHistoricalSnapshot(a.filter(([k])=>k!==key),locale),/Unreviewed Chat context\/section copy/);
      assert.throws(()=>contextSectionHistoricalSnapshot(a.map(([k,v])=>[k,k===key?'UNREVIEWED':v]),locale),/Unreviewed Chat context\/section copy/);
    }
    assert.throws(()=>contextSectionHistoricalSnapshot([...normalized,...Object.entries(e).toReversed()],locale),/Unreviewed Chat context\/section copy/);
    assert.throws(()=>contextSectionHistoricalSnapshot([...a,['chatDetailSectionUiUnknown','UNKNOWN']],locale),/Unreviewed Chat context\/section copy/);
    const customer=['unknown.customer.key',literal];assert.deepEqual(contextSectionHistoricalSnapshot([...a,customer],locale).at(-1),customer);
  });
}
test('future source normalization admits only the reviewed whole detail and separate pinned line',()=>{
  assert.notEqual(source.portal,oldSource.portal);assert.equal(contextSectionHistoricalPortalSource(source.portal),oldSource.portal);
  for(const [start,end,old,next]of [
    ['  function renderChatWorkspaceDetail(page, context) {','\n  // Analytics Workspace','const writable = state === "draft";','const writable = true;'],
    ['      { name: "pinned", label: uiText("chatFieldUiPinnedLabel"','\n','checkboxLabel: uiText("chatDetailSectionUiPinnedCheck", "Ghim hội thoại")','checkboxLabel: "UNREVIEWED"']
  ]){
    const a=source.portal.indexOf(start),b=source.portal.indexOf(end,a+start.length),part=source.portal.slice(a,b);
    assert.ok(a>=0&&b>a);assert.equal(part.split(old).length-1,1);
    assert.throws(()=>contextSectionHistoricalPortalSource(source.portal.slice(0,a)+part.replace(old,next)+source.portal.slice(b)),/Unreviewed Chat context\/section (?:source|pinned source)/);
  }
  assert.ok(contextSectionHistoricalPortalSource(source.portal+'\n// UNKNOWN_OUTSIDE').endsWith('// UNKNOWN_OUTSIDE'));
});
test('marker-free historical source remains exact and its previous strict gate still rejects mutations',()=>{
  assert.equal(contextSectionHistoricalPortalSource(oldSource.portal),oldSource.portal);
  const start='  function renderChatWorkspaceDetail(page, context) {',end='\n  // Analytics Workspace';
  const a=oldSource.portal.indexOf(start),b=oldSource.portal.indexOf(end,a),part=oldSource.portal.slice(a,b);
  assert.ok(a>=0&&b>a);assert.equal(/chatDetail(?:Context|Section)Ui/.test(part),false);
  const old='const writable = state === "draft";';assert.equal(part.split(old).length-1,1);
  const changed=oldSource.portal.slice(0,a)+part.replace(old,'const writable = true;')+oldSource.portal.slice(b);
  assert.equal(contextSectionHistoricalPortalSource(changed),changed);
  assert.throws(()=>summaryHistoricalPortalSource(changed),/Unreviewed Chat summary\/editor source/);
});
