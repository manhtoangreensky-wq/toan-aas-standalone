import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const source=fs.readFileSync(process.env.R173_SOURCE_FIXTURE||'static/portal/portal.js','utf8'),messages=fs.readFileSync('static/portal/portal-i18n.js','utf8'),noop=()=>{};
function runtime(locale,path='/dashboard',options={}){
 const document={readyState:'loading',title:'',addEventListener:noop,querySelector:()=>null,querySelectorAll:()=>[],getElementById:()=>null,documentElement:{lang:locale,setAttribute:noop,getAttribute:()=>null,classList:{add:noop,remove:noop}},body:{classList:{add:noop,remove:noop,toggle:noop},setAttribute:noop}};
 const window={document,navigator:{language:locale,userAgent:'QA'},location:{pathname:path,search:'',href:'http://127.0.0.1:4178'+path},addEventListener:noop,dispatchEvent:noop,CustomEvent:function(){},matchMedia:()=>({matches:false,addEventListener:noop}),localStorage:{getItem:()=>null}};
 const sandbox=vm.createContext({window,document,navigator:window.navigator,URL,URLSearchParams,Intl,console,setTimeout,clearTimeout});vm.runInContext(messages,sandbox);
 vm.runInContext(source.replace('  window.TOANAASPortal = Object.freeze({','  window.__SidebarTest={renderSidebar,pageStatusBadge,normalizeBootstrap};\n  window.TOANAASPortal = Object.freeze({'),sandbox);
 const registry=fs.readFileSync('copyfast_registry.py','utf8'),catalog=Array.from(registry.matchAll(/WebFeature\(\s*"([^"]+)"\s*,\s*"([^"]*)"\s*,\s*"([^"]+)"\s*,\s*"([^"]+)"/g)).map(([,key,title,group,route])=>({key,title,group,route}));
 window.TOANAASI18n.setLocale(locale,{emit:false});const ctx=window.__SidebarTest.normalizeBootstrap({path,profile:{locale},session:{authenticated:true,csrfToken:'qa'},catalog,...options}),page=window.TOANAASPortal.resolvePage(path);
 return {html:window.__SidebarTest.renderSidebar(page,ctx),badge:window.__SidebarTest.pageStatusBadge(page,ctx)};
}
const paths=['/dashboard','/studio','/tools/image','/voice','/music','/subdub','/content','/documents','/projects','/publishing','/jobs','/wallet','/packages','/history','/account','/features','/tools/free'];
const expected={vi:{groups:['Tổng quan','Sáng tạo','Công việc','Tài khoản','Tất cả công cụ'],labels:['Tổng quan','Video AI','Ảnh AI','Giọng đọc','Âm nhạc','SubDub','Nội dung','Tài liệu','Dự án','Đăng bài','Tác vụ','Ví Xu','Gói dịch vụ','Lịch sử','Tài khoản','Tất cả công cụ','Công cụ miễn phí'],badge:'Kế hoạch & bản nháp'},en:{groups:['Overview','Create','Work','Account','All tools'],labels:['Overview','AI video','AI images','Voice','Music','SubDub','Content','Documents','Projects','Publishing','Jobs','Xu wallet','Plans','History','Account','All tools','Free tools'],badge:'Plans & drafts'},zh:{groups:['概览','创作','工作','账户','全部工具'],labels:['概览','AI 视频','AI 图片','语音','音乐','SubDub','内容','文档','项目','发布','任务','Xu 钱包','套餐','记录','账户','全部工具','免费工具'],badge:'计划与草稿'}};
const text=html=>html.replace(/<[^>]+>/g,' ').replace(/&amp;/g,'&').replace(/\s+/g,' ').trim();
for(const locale of ['vi','en','zh']){
 test(`All seventeen primary customer sidebar labels and five groups use ${locale}`,()=>{
  const r=runtime(locale),links=Array.from(r.html.matchAll(/<a class="portal-nav-link" href="([^"]+)"[^>]*>([\s\S]*?)<\/a>/g)).filter(m=>paths.includes(m[1]));
  assert.deepEqual(links.map(m=>m[1]),paths);assert.deepEqual(links.map(m=>text(m[2])),expected[locale].labels);
  assert.deepEqual(Array.from(r.html.matchAll(/class="portal-nav-label">([^<]+)<\/span>/g),m=>m[1]),expected[locale].groups);
 });
 test(`Planning status copy follows ${locale} while its draft authority attributes stay unchanged`,()=>{
  const r=runtime(locale);assert.equal(text(r.badge),expected[locale].badge);assert.match(r.badge,/data-status="draft" data-boundary="web_planning"/);
 });
}
test('Primary sidebar retains the one active route and keeps customer role from exposing Admin',()=>{
 const r=runtime('en','/music',{session:{authenticated:true,role:'admin',csrfToken:'qa'}});
 assert.equal((r.html.match(/aria-current="page"/g)||[]).length,1);assert.match(r.html,/<a class="portal-nav-link" href="\/music" aria-current="page"/);assert.doesNotMatch(r.html,/href="\/admin/);
});
test('Customer planning and generator badges do not claim provider availability from a static label',()=>{
 assert.doesNotMatch(text(runtime('vi','/image/upscale').badge),/Sẵn sàng|Job Bridge|Adapter|Generator/);
 assert.doesNotMatch(text(runtime('en','/music/song').badge),/Adapter|Bộ tạo|Chờ/);
});
function renderAdminSidebar(portalSource){
 const start=portalSource.indexOf('  function renderSidebar(page, context) {'),end=portalSource.indexOf('  function renderThemeToggle()',start);
 const sandbox=vm.createContext({isAdminPortalSurface:()=>true,uiText:(_key,fallback)=>fallback,localizedNavigationLabel:v=>v,
  safeText:v=>String(v??''),portalIcon:v=>v,portalBrandMark:()=>'<svg></svg>',ICONS:{legal:'legal',close:'close'},
  isNavCurrent:path=>path==='/admin/topups',navGroups:()=>[{label:'Quản trị fixture',current:true,links:[['/admin','Tổng quan','home'],['/admin/topups','Duyệt nạp','payment']]}]});
 vm.runInContext(portalSource.slice(start,end)+'\nglobalThis.renderSidebar=renderSidebar;',sandbox);
 return sandbox.renderSidebar({path:'/admin/topups'},{bridge:{available:true},adminData:{counts:{pending_topups:2}}});
}
test('Customer locale projection leaves the issued Admin destinations and pending count intact',()=>{
 const html=renderAdminSidebar(source);
 assert.deepEqual(Array.from(html.matchAll(/class="portal-nav-link" href="([^"]+)"/g),m=>m[1]),['/admin','/admin/topups','/legal']);
 assert.ok(html.includes('Quản trị fixture'));assert.ok(html.includes('Duyệt nạp'));assert.match(html,/<span class="portal-nav-badge"[^>]*>2<\/span>/);
 assert.ok(!html.includes('customerChrome'));assert.ok(!html.includes('portal-nav-group--current" open'));
 if(process.env.R173_ADMIN_BASELINE)assert.equal(html,renderAdminSidebar(fs.readFileSync(process.env.R173_ADMIN_BASELINE,'utf8')));
});
