import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

const source=fs.readFileSync('static/portal/portal.js','utf8').replace(/\r\n/g,'\n');
const catalogue=fs.readFileSync('static/portal/portal-i18n.js','utf8');
const approved=JSON.parse(fs.readFileSync('tests/fixtures/admin-guard-customer-copy.json','utf8'));
function fn(name){
  const at=source.indexOf('  function '+name+'('),end=source.indexOf('\n  }\n',at);
  assert(at>=0&&end>at,'Real function boundary '+name);return source.slice(at,end+5);
}
function model(locale){
  const ctx={
    serverAuthorizesAdminRoute:context=>context.adminAllowed===true,
    telegramConnectionReady:context=>context.telegramConnection?.ready===true,
    telegramConnectionBlockReason:()=> 'TECHNICAL_CONFIGURATION_NAME',
    renderHero:()=>'',supportAdminCaseListing:()=>({filters:{state:'',category:'',team_queue:'',assignment:'',sla_class:'',care_sla_status:'',escalation_state:'',q:''}}),
    supportCaseItems:()=>[],renderSupportAdminSummary:()=>'',renderSupportResolutionFeedbackSummary:()=>'',renderSupportCaseCards:()=>'',renderSupportAdminCasePagination:()=>'',
    supportStateOptions:()=>'',supportCategoryOptions:()=>'',supportCareFilterOptions:()=>'',
    SUPPORT_CARE_QUEUES:[],SUPPORT_CARE_ASSIGNMENT_FILTER_LABELS:[],SUPPORT_CARE_SLA:[],SUPPORT_CARE_SLA_STATUS:[],SUPPORT_CARE_ESCALATION_LABELS:{},
    badge:()=>'',safeText:value=>String(value??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;')};
  vm.createContext(ctx);vm.runInContext(catalogue,ctx);
  ctx.uiText=(key,fallback,params)=>ctx.TOANAASI18n.has(key)?ctx.TOANAASI18n.t(key,params,locale):fallback;
  ctx.adminSupportText=(key,fallback,params)=>ctx.uiText('adminSupport.'+key,fallback,params);
  ctx.adminOperationsText=(key,fallback,params)=>ctx.uiText('adminOperations.'+key,fallback,params);
  const localActionsAt=source.indexOf('  const WEB_LOCAL_ACTIONS =');
  const localActionsEnd=source.indexOf(';\n',localActionsAt);
  assert(localActionsAt>=0&&localActionsEnd>localActionsAt,'Real local-action constant boundary');
  vm.runInContext(source.slice(localActionsAt,localActionsEnd+1)+[fn('canAct'),fn('telegramIdentityLinked'),fn('actionBlockReason'),fn('renderSupportAdminBase'),fn('renderOperationsAdmin')].join('\n'),ctx);
  return ctx;
}
const context=overrides=>({session:{authenticated:true,csrfReady:true},bridge:{available:true,csrfReady:true},
  capabilities:{},adminAllowed:true,telegramConnection:{ready:true},...overrides});
const cases=[
  ['telegramUnavailable',{action:'start-telegram-link',access:'member'},context({telegramConnection:{ready:false}}),false],
  ['adminRequired',{action:'admin-refresh',access:'admin',path:'/admin'},context({adminAllowed:false}),false],
  ['signInRequired',{action:'feature-draft',access:'member'},context({session:{authenticated:false}}),false],
  ['supportRetry',{action:'support-case-create',access:'member'},context({session:{authenticated:true},bridge:{available:true}}),false],
  ['planRetry',{action:'campaign-create',access:'member'},context({session:{authenticated:true},bridge:{available:true}}),false],
  ['supportUnavailable',{action:'support-case-create',access:'member'},context(),false],
  ['planUnavailable',{action:'campaign-create',access:'member'},context(),false],
  ['telegramLinkRequired',{action:'feature-draft',access:'member'},context({bridge:{available:false,csrfReady:true}}),false],
  ['temporarilyUnavailable',{action:'refresh-link-status',access:'member'},context({bridge:{available:false,csrfReady:true}}),false],
  ['retrySession',{action:'feature-draft',access:'member'},context({session:{authenticated:true},bridge:{available:true}}),false],
  ['payment-local-priority',{action:'payment-create',access:'member'},context({paymentOptions:{payos:{topup_catalog_available:false}}}),false,'planUnavailable'],
  ['unavailable',{action:'feature-draft',access:'member'},context(),false]
];
const signIn={vi:'Vui lòng đăng nhập để tiếp tục.',en:'Sign in to continue.',zh:'请登录后继续。'};
const noTechnical=/signed|CSRF|Core Bridge|canonical|payload|receipt|TECHNICAL_CONFIGURATION_NAME|idempotency|local storage|原始载荷|浏览器无法|Trình duyệt không thể/i;
for(const locale of ['vi','en','zh']){
  const m=model(locale);
  const index=['vi','en','zh'].indexOf(locale)+1;
  for(const [group,prefix]of [['support','adminSupport.'],['operations','adminOperations.']]){
    for(const row of approved[group])test(locale+' reviewed '+group+' message '+row[0]+' reaches the public dictionary',()=>{
      assert.equal(m.TOANAASI18n.t(prefix+row[0],{role:'QA_ROLE'},locale),row[index].replace('{role}','QA_ROLE'));
    });
  }
  for(const[key,page,state,enabled,wantedKey=key]of cases)test(locale+' action guard '+key+' stays closed and gives native guidance',()=>{
    const reason=m.actionBlockReason(page,state);
    assert.equal(m.canAct(page,state),enabled);
    assert.equal(reason,approved.action.find(row=>row[0]===wantedKey)[index]);
    assert.doesNotMatch(reason,noTechnical);
    if(locale==='en')assert.doesNotMatch(reason,/[À-ỹ]/);
    if(locale==='zh')assert.match(reason,/[\u3400-\u9fff]/);
  });
  test(locale+' sign-in guidance is literal and branch precedence is unchanged',()=>{
    assert.equal(m.actionBlockReason({action:'feature-draft',access:'member'},context({session:{authenticated:false}})),signIn[locale]);
    assert.equal(m.actionBlockReason({action:'admin-refresh',access:'admin'},context({adminAllowed:false,session:{authenticated:false}})),
      m.TOANAASI18n.t('actionBlockReason.adminRequired',undefined,locale));
    assert.equal(m.canAct({action:'campaign-create',access:'member'},context({capabilities:{'campaign-create':true}})),true);
  });
  for(const state of ['guarded','loading'])test(locale+' Support '+state+' renders only helpful native status',()=>{
    const html=m.renderSupportAdminBase({}, {supportAdminReadState:state});
    assert.match(html,/<h2>/);assert.doesNotMatch(html,noTechnical);
    assert.doesNotMatch(html,/data-portal-action=|portal-state-meta/);
  });
  test(locale+' Support ready keeps filters but removes the unused technical boundary card',()=>{
    const html=m.renderSupportAdminBase({}, {supportAdminReadState:'ready',supportAdminSummary:{operator_role:'operator'}});
    assert.match(html,/support-admin-cases-filter/);assert.match(html,/support-admin-cases-refresh/);
    assert.doesNotMatch(html,noTechnical);assert.doesNotMatch(html,/boundary\.|Ranh giới nghiệp vụ|Business boundary|业务边界/);
    assert.doesNotMatch(html,/<section[^>]*>\s*<\/section>/);
  });
  for(const state of ['disabled','loading','unavailable'])test(locale+' Operations '+state+' gives native non-technical recovery',()=>{
    const html=m.renderOperationsAdmin({}, {operationsAdminReadState:state==='loading'?'loading':'guarded',operationsConfigurationState:state});
    assert.match(html,/<h2>/);assert.doesNotMatch(html,noTechnical);
    assert.doesNotMatch(html,/data-portal-action=|approval_record_only/);
  });
  for(const[key]of [['guard.body'],['queue.guarded.body'],['partial.body'],['intro.body'],['approval.managerOnly.body']]){
    test(locale+' Operations '+key+' keeps meaning without implementation jargon',()=>{
      const text=m.TOANAASI18n.t('adminOperations.'+key,{role:'QA_ROLE'},locale);
      assert.doesNotMatch(text,noTechnical);if(key==='intro.body')assert.match(text,/QA_ROLE/);
    });
  }
}
