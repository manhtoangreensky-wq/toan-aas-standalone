import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import {execFileSync} from "node:child_process";
import {fileURLToPath} from "node:url";

// Catches technical customer wording across real stateful renderer branches.
// This suite reads the raw application; historical inverses are not used.
const ROOT=path.resolve(path.dirname(fileURLToPath(import.meta.url)),"..");
const BASE="469f70063217814522b674272185227d93c8a08c";
const actualI18n=fs.readFileSync(path.join(ROOT,"static/portal/portal-i18n.js"),"utf8");
const oldI18n=execFileSync("git",["show",BASE+":static/portal/portal-i18n.js"],{cwd:ROOT,encoding:"utf8",maxBuffer:30e6});
const actualPortal=fs.readFileSync(path.join(ROOT,"static/portal/portal.js"),"utf8");
const oldPortal=execFileSync("git",["show",BASE+":static/portal/portal.js"],{cwd:ROOT,encoding:"utf8",maxBuffer:30e6});
const helper=fs.readFileSync(path.join(ROOT,"tests/helpers/publishing-child-render.mjs"),"utf8");
const rootAnchor="const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');";
const i18nAnchor="const i18n=fs.readFileSync(path.join(root,'static/portal/portal-i18n.js'),'utf8');";
const portalAnchor="const portal=fs.readFileSync(path.join(root,'static/portal/portal.js'),'utf8');";
assert.equal(helper.split(rootAnchor).length-1,1);assert.equal(helper.split(i18nAnchor).length-1,1);
assert.equal(helper.split(portalAnchor).length-1,1);
async function load(i18n,portal){
  const source=helper.replace(rootAnchor,"const root="+JSON.stringify(ROOT)+";")
    .replace(i18nAnchor,"const i18n="+JSON.stringify(i18n)+";").replace(portalAnchor,"const portal="+JSON.stringify(portal)+";")
    .replace("displayName:'QA'","displayName:'Người dùng'")
    .replace('function renderChild(locale,route,raw={})','function renderChild(locale,route,raw={},search="")')
    .replace("search:'',href:","search,href:");
  return(await import("data:text/javascript;base64,"+Buffer.from(source).toString("base64"))).renderChild;
}
const now=await load(actualI18n,actualPortal),old=await load(oldI18n,oldPortal);
const ID="11111111-1111-4111-8111-111111111111";
const CUSTOMER="Khách giữ QA metadata Studio Facebook TikTok <img src=x onerror=1>";
const escaped=s=>s.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;").replace(/'/g,"&#39;");
const clone=value=>structuredClone(value);
const technical=/\b(?:QA|CSRF|UUID|API|metadata|provider|backend|frontend|runtime|canonical|guarded|signed session|signed account|owner.scoped|Web.native|workflow engine|revision|token|adapter|companion|MFA|TOTP|SMTP|OIDC|OAuth|PWA|webhook|SHA-1|Portal)\b/i;
const mixedVi=/\b(?:Bot|ID|workspace|workflow|engine|job|brief|Studio|media|profile|artboard|direction|authored|Prompt|Dashboard|Workboard|Starter Kits|review|checklist|Project|receiver|callback|deep link|authority|identity|server|browser|output|input)\b/i;
const internalVi=/siêu dữ liệu|bản dữ liệu đã làm sạch|suy đoán.*trình duyệt|ranh giới thực thi|biên nhận máy chủ|cờ tính năng|khóa mã hóa riêng|bộ đếm phía máy chủ/i;
function fixedText(html){
  const customer=escaped(CUSTOMER);
  let source=html.split(customer).join("CUSTOMER");
  // These exact customer-facing Telegram commands retain functional meaning.
  // Validate the command bytes separately; do not translate or mask other code.
  source=source.replace(/<code class="portal-link-code">([^<]*)<\/code>/g,(full,value)=>
    /^(?:\/(?:language|mode|profile|mydata|data_delete)|MÃ-LIÊN-KẾT-TẠM)$/.test(value)?"<code>COMMAND</code>":full);
  return source.replace(/<svg\b[\s\S]*?<\/svg>/g," ").replace(/<[^>]*>/g," ").replace(/\s+/g," ").trim();
}
const attrs=html=>[...html.matchAll(/\b(?:placeholder|aria-label|title|data-portal-confirm)="([^"]*)"/g)].map(m=>m[1]).join(" ");
const controls=html=>[...html.matchAll(/<(?:form|button|input|textarea|select|option|a)\b[^>]*>/g)]
  .map(m=>m[0].replace(/\b(?:placeholder|aria-label|title|data-portal-confirm)="[^"]*"/g,"copy=\"TEXT\""));
const capabilities=Object.fromEntries(["workspace-setup-save","projects-refresh","project-create","starter-kits-view","starter-kit-apply",
  "account-security-refresh","account-security-revoke-session","account-security-revoke-others","account-security-password-change",
  "account-security-oauth-unlink","account-security-mfa-start","account-security-mfa-confirm","account-security-mfa-disable"]
  .map(k=>[k,true]));
const kitKeys=["project-foundation","content-foundation","image-direction","voice-script","audio-brief","subtitle-plan","document-qa","operations-board"];
function catalog({state="available",setup=true,workboard=true}={}){
  return{readState:"read_only",profile:{setup_state:setup?"completed":"not_started",revision:2},
    recommendedKeys:["project-foundation"],workboardReady:workboard,kits:kitKeys.map((key,i)=>({
      key,version:1,title:CUSTOMER,summary:CUSTOMER,outcome:CUSTOMER,focus_areas:["projects"],
      state,record_counts:{projects:1,documents:2,work_items:1,checklist_items:3},
      ...(state==="installed"?{installation:{id:ID,project_id:ID,kit_key:key,kit_version:1,document_count:2,work_item_count:1,
        setup_profile_revision:2,created_at:"2026-11-28T00:00:00Z"}}:{})
    }))};
}
function security(state="read_only",password=true){
  return{readState:state,sessions:[{session_ref:"a".repeat(64),current:true,created_at:"2026-11-28T00:00:00Z"},
    {session_ref:"b".repeat(64),current:false,created_at:"2026-11-27T00:00:00Z"}],
    loginMethods:{password:{available:password},oauth:[{provider:"google",linked:true,enabled:true,can_unlink:false}],
      usable_factor_count:password?2:1,contact:{state:"verified_oauth",provider:"google",verified:true}},
    mfa:{enabled:false,available:false}};
}
const RECOVERY=["ABCD-EFGH","JKLM-NPQR","STUV-WXYZ","2345-6789","ABCD-2345","EFGH-6789","JKLM-2345","NPQR-6789"];
const cases=[
  ...["loading","guarded","read_only"].map(state=>({name:"setup-"+state,route:"/workspace/setup",
    raw:{capabilities,workspaceSetup:{readState:state,profile:{setup_state:"not_started",revision:0,focus_areas:[]}}}})),
  ...["loading","guarded"].map(state=>({name:"starter-"+state,route:"/starter-kits",raw:{capabilities,starterKits:{readState:state}}})),
  {name:"starter-no-access",route:"/starter-kits",raw:{}},
  {name:"starter-catalog",route:"/starter-kits",raw:{capabilities,starterKits:catalog()}},
  ...[
    ["available",catalog()],["setup-needed",catalog({setup:false})],
    ["maintenance",catalog({workboard:false})],["installed",catalog({state:"installed"})]
  ].map(([name,starterKits])=>({name:"starter-detail-"+name,route:"/starter-kits/project-foundation",raw:{capabilities,starterKits}})),
  {name:"account",route:"/account",raw:{}},
  {name:"account-linked",route:"/account",raw:{linkStatus:{linked:true},bridge:{available:true},
    profile:{locale:"vi",accountType:"telegram",loginMethods:{telegram:true}}}},
  ...["loading","guarded","read_only"].map(state=>({name:"security-"+state,route:"/account/security",raw:{capabilities,accountSecurity:security(state)}})),
  {name:"security-external-login",route:"/account/security",raw:{capabilities,accountSecurity:security("read_only",false)}},
  {name:"security-telegram",route:"/account/security",raw:{capabilities,bridge:{available:true},
    accountSecurity:{...security("read_only",false),loginMethods:{password:{available:false},
      oauth:[{provider:"telegram",linked:true,enabled:true,can_unlink:false}],usable_factor_count:1,
      contact:{state:"not_applicable",verified:false}}}}},
  {name:"security-recovery",route:"/account/security",raw:{capabilities,totpMfaEnabled:true,
    accountSecurity:{...security(),mfa:{enabled:true,runtime_available:true,password_factor_available:true,recovery_codes_remaining:8}},
    mfaRecoveryCodes:RECOVERY}},
  {name:"security-enrollment",route:"/account/security",raw:{capabilities,totpMfaEnabled:true,
    accountSecurity:{...security(),mfa:{enabled:false,runtime_available:true,password_factor_available:true,pending_enrollment:true}},
    mfaEnrollment:{factor_id:ID,enrollment_token:"synthetic_enrollment_".repeat(3),manual_key:"ABCDEFGHIJKLMNOP",
      issuer:"TOAN AAS",algorithm:"SHA1",digits:6,period_seconds:30,expires_in_minutes:5}}},
  ...["loading","guarded","ready","failed"].map(state=>({name:"projects-"+state,route:"/projects",raw:{
    capabilities,projectCenterReadState:state,projects:[{id:ID,title:CUSTOMER,objective:CUSTOMER,document_count:2,state:"active"}]}})),
  {name:"projects-new",route:"/projects/new",raw:{capabilities,projectCenterReadState:"ready"}},
  {name:"project-missing",route:"/projects/"+ID,raw:{capabilities}},
  {name:"data-disabled",route:"/account/data-controls",raw:{}},
  {name:"data-ready",route:"/account/data-controls",raw:{
    capabilities:{"data-controls-view":true,"data-controls-export":true,"data-controls-erasure-request":true,"data-controls-erasure-cancel":true},
    dataControlsEnabled:true,dataControlsReadState:"read_only",
    dataControlsSummary:{policyVersion:"web_data_controls_v1",scopeKey:"web_authoring_only",
      categories:["account_profile","memory_center","prompt_library","workboard"].map(key=>({key,recordCount:1,exportAvailable:true,erasureRequestAvailable:key!=="account_profile"})),
      authoringRecordCount:4,requestCounts:{awaiting_review:1,identity_verification_pending:0,cancelled:0,closed:0},
      automaticDeletion:false,humanReviewRequired:true},
    dataControlsRequests:[{id:ID,scopeKey:"web_authoring_only",state:"awaiting_review",revision:1,
      requestedAt:"2026-11-28T00:00:00Z",updatedAt:"2026-11-28T00:00:00Z",cancelledAt:null,
      automaticDeletion:false,humanReviewRequired:true}]}},
  {name:"onboarding-not-ready",route:"/onboarding",raw:{capabilities}},
  {name:"onboarding-config-pending",route:"/onboarding",raw:{capabilities,telegramConnection:{
    ready:false,bot_callback_adapter_enabled:true,missing_configuration:["INTERNAL_SETTING_NAME"]}}},
  {name:"onboarding-ready",route:"/onboarding",raw:{capabilities,telegramConnection:{
    ready:true,bot_callback_adapter_enabled:true,bot_callback_observed:false}}},
  {name:"onboarding-observed",route:"/onboarding",raw:{capabilities,telegramConnection:{
    ready:true,bot_callback_adapter_enabled:true,bot_callback_observed:true,last_valid_callback_kind:"account_link",last_valid_callback_at:"2026-11-28"}}},
  {name:"onboarding-linked",route:"/onboarding",raw:{capabilities,linkStatus:{linked:true},profile:{accountType:"telegram",loginMethods:{telegram:true}}}},
  {name:"onboarding-paused",route:"/onboarding",raw:{capabilities,linkFlow:{data:{code:"MÃ-LIÊN-KẾT-TẠM",expires_in_minutes:5}}}},
  {name:"onboarding-recovered",route:"/onboarding",raw:{capabilities,telegramConnection:{ready:true},
    linkFlow:{data:{recovered:true,expired:true}}}},
  {name:"onboarding-recovered-pending",route:"/onboarding",raw:{capabilities,telegramConnection:{ready:true},
    linkFlow:{data:{recovered:true,expired:false}}}},
  {name:"onboarding-recovered-ready",route:"/onboarding",raw:{capabilities,telegramConnection:{ready:true},
    linkFlow:{data:{recovered:true,ready_to_complete:true}}}},
  {name:"onboarding-active-code",route:"/onboarding",raw:{capabilities,telegramConnection:{ready:true},
    linkFlow:{data:{code:"MÃ-LIÊN-KẾT-TẠM",expires_in_minutes:5,deep_link:"https://t.me/toanaas_bot?start=synthetic-local"}}}},
  {name:"onboarding-continuation",route:"/onboarding",search:"?next=/voice/tts",raw:{capabilities,telegramConnection:{ready:true}}}
];
for(const locale of ["vi","en","zh"])for(const item of cases)test(`${locale}/${item.name}: natural fixed wording, same controls and customer content`,()=>{
  const before=old(locale,item.route,clone(item.raw),item.search),after=now(locale,item.route,clone(item.raw),item.search);
  assert.equal(JSON.stringify(after.context),JSON.stringify(before.context),"Text changes must not mutate normalized application data");
  assert.deepEqual(controls(after.html),controls(before.html),"Handlers,fields,values,permissions,links and confirmation presence stay exact");
  const commandValues=html=>[...html.matchAll(/<code class="portal-link-code">([^<]*)<\/code>/g)].map(m=>m[1]);
  assert.deepEqual(commandValues(after.html),commandValues(before.html),"Real commands and temporary codes unchanged");
  const copy=fixedText(after.html)+" "+attrs(after.html).split(escaped(CUSTOMER)).join("CUSTOMER");
  assert.equal(copy.match(technical)?.[0]??null,null,"No developer acronym or implementation label in customer text");
  assert(!copy.includes("INTERNAL_SETTING_NAME"),"Do not show environment setting names to customers");
  if(locale==="vi"){
    assert.equal(copy.match(mixedVi)?.[0]??null,null,"Fixed Vietnamese wording cannot contain English common terms");
    assert.equal(copy.match(internalVi)?.[0]??null,null,"Translated architecture explanations are still not customer wording");
  }
  if(locale==="zh")assert(!/\bBot\b/.test(copy),"Common assistant wording must be Chinese rather than a Latin internal label");
  assert(!after.html.includes("<img src=x"));
  if(before.html.includes(escaped(CUSTOMER)))assert(after.html.includes(escaped(CUSTOMER)),"Customer's words must be kept verbatim and escaped");
});
for(const locale of ["vi","en","zh"])test(`${locale}/truthful code guidance: active link and recovery codes remain visible without false privacy guarantees`,()=>{
  const challenge=cases.find(row=>row.name==="onboarding-active-code"),recovery=cases.find(row=>row.name==="security-recovery");
  const link=now(locale,challenge.route,clone(challenge.raw)).html;
  assert(link.includes("MÃ-LIÊN-KẾT-TẠM")&&link.includes("/linkweb MÃ-LIÊN-KẾT-TẠM"));
  assert(!/(?:not[^.!]*sent to any external service|không gửi ra dịch vụ bên ngoài|不会发送给外部服务)/i.test(fixedText(link)),
    "A code deliberately sent through Telegram cannot be promised never to leave the app");
  const account=now(locale,recovery.route,clone(recovery.raw)).html;
  for(const code of RECOVERY)assert(account.includes(`<code>${code}</code>`),"One-time recovery codes must not be hidden to make a copy claim true");
  assert(!/(?:sign-in codes[^.!]*never displayed|mã đăng nhập[^.!]*luôn được ẩn|登录密钥[^。]*均不会显示)/i.test(fixedText(account)),
    "The summary must not promise that codes shown on the same page are always hidden");
});
test("dictionary keysets and all unrelated text stay exact",()=>{
  const before=old("vi","/workspace/setup",{}).messages,after=now("vi","/workspace/setup",{}).messages;
  const allowed=/^(?:summary\.companion$|setup\.|onboarding\.|telegramConnection\.|account\.|accountCenter\.(?:avatar|profile|security|dataControls)\.|interfaceLocale\.|projectCenter\.|project\.|starter\.|workboard\.|nav\.workspace_setup$|page\.(?:workspaceSetup|starterKits|accountSecurity|accountDataControls|dataControls)\.description$)/;
  for(const locale of ["vi","en","zh"]){
    assert.deepEqual(Object.keys(after[locale]),Object.keys(before[locale]),"Do not add/remove/reorder dictionary keys");
    for(const[key,value]of Object.entries(before[locale]))if(!allowed.test(key))assert.equal(after[locale][key],value,key);
  }
});
for(const locale of ["vi","en","zh"])test(`${locale}/account sentence composition: no repeated punctuation or sign-in label`,()=>{
  const {html}=now(locale,"/account",{});
  const command=html.match(/<div class="portal-account-command-copy">([\s\S]*?)<\/div>/)?.[1];
  assert(command,"The real account next-step description must be rendered");
  assert(!/[.。]\s*[.。]/u.test(fixedText(command)),"The complete description must not repeat its sentence terminator");
  assert(!/sign-in\s+sign-in/i.test(fixedText(html)),"A sign-in method name must not acquire a duplicated sign-in suffix");
});
for(const locale of ["vi","en","zh"])for(const route of ["/membership","/wallet/topup","/documents/translate"])
test(`${locale}/shared summary ${route}: natural connected-service label without changing controls`,()=>{
  const before=old(locale,route,{}),after=now(locale,route,{});
  const label={vi:"Ứng dụng liên kết",en:"Connected services",zh:"关联应用"}[locale];
  assert(after.html.includes(`<span class="portal-summary-key">${label}</span>`),"Every real consumer must receive the ordinary service label");
  assert.deepEqual(controls(after.html),controls(before.html));
  assert.equal(JSON.stringify(after.context),JSON.stringify(before.context));
});
test("application logic outside the single customer label remains byte-identical",()=>{
  const before='      { label: "MFA", ...mfaPosture },';
  const after='      { label: copy("mfaTitle", "Xác thực hai bước"), ...mfaPosture },';
  assert.equal(oldPortal.split(before).length-1,1);
  assert.equal(actualPortal.replace(/\r\n/g,"\n"),oldPortal.replace(/\r\n/g,"\n").replace(before,after),
    "No auth,permissions,session,form,provider,wallet,data or motion logic change");
});
