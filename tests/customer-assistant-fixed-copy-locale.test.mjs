import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const source=fs.readFileSync('static/portal/portal.js','utf8'),messages=fs.readFileSync('static/portal/portal-i18n.js','utf8'),noop=()=>{};
function runtime(locale){
 const document={readyState:'loading',title:'',addEventListener:noop,querySelector:()=>null,querySelectorAll:()=>[],getElementById:()=>null,
 documentElement:{lang:locale,setAttribute:noop,getAttribute:()=>null,classList:{add:noop,remove:noop}},body:{classList:{add:noop,remove:noop,toggle:noop},setAttribute:noop}};
 const window={document,navigator:{language:locale,userAgent:'QA'},location:{pathname:'/dashboard',search:'',href:'http://127.0.0.1:4178/dashboard'},addEventListener:noop,dispatchEvent:noop,CustomEvent:function(){},matchMedia:()=>({matches:false,addEventListener:noop}),localStorage:{getItem:()=>null}};
 const sandbox=vm.createContext({window,document,navigator:window.navigator,URL,URLSearchParams,Intl,console,setTimeout,clearTimeout});vm.runInContext(messages,sandbox);
 vm.runInContext(source.replace('  window.TOANAASPortal = Object.freeze({','  window.__AssistantTest={renderCopilotHtml, copilotState};\n  window.TOANAASPortal = Object.freeze({'),sandbox);
 window.TOANAASI18n.setLocale(locale,{emit:false});
 const container={innerHTML:'',querySelector:()=>null,querySelectorAll:()=>[],contains:()=>false};
 return {state:window.__AssistantTest.copilotState,locale:next=>window.TOANAASI18n.setLocale(next,{emit:false}),render(){window.__AssistantTest.renderCopilotHtml(container,{});return container.innerHTML}};
}
const visible=html=>html.replace(/<style>[\s\S]*?<\/style>/g,'').replace(/<[^>]*>/g,' ').replace(/\s+/g,' ').trim();
const expected={vi:{close:'Đóng trợ lý',send:'Gửi',input:'Câu hỏi cho trợ lý',title:'Xin chào! Tôi là Trợ lý AI AAS BOT.',labels:['Nạp Xu','Video AI','Ảnh AI','Giọng đọc','SubDub','Âm nhạc','Kịch bản','Gói thành viên','Bảng giá','Số dư Xu','Giao diện']},en:{close:'Close assistant',send:'Send',input:'Question for the assistant',title:'Hello! I am the AAS BOT AI Assistant.',labels:['Top up Xu','AI video','AI image','Voice','SubDub','Music','Scripts','Membership','Pricing','Xu balance','Theme']},zh:{close:'关闭助手',send:'发送',input:'向助手提问',title:'你好！我是 AAS BOT AI 助手。',labels:['充值 Xu','AI 视频','AI 图片','语音','SubDub','音乐','脚本','会员套餐','价格','Xu 余额','主题']}};
const queryValues=['Nạp tiền vào tài khoản','Tạo video quảng cáo','Tạo ảnh sản phẩm','Lồng tiếng đọc văn bản','Bóc tách phụ đề video','Tạo nhạc Suno AI','Viết kịch bản video','Xem gói và quyền lợi thành viên','Bảng giá các dịch vụ','Kiểm tra số dư Xu hiện tại','Đổi giao diện sáng tối'];
for(const locale of ['vi','en','zh']){
 test(`Assistant fixed chrome and all eleven chips render in ${locale}`,()=>{
  const html=runtime(locale).render(),want=expected[locale];assert.ok(html.includes('aria-label="'+want.close+'"'));
  assert.ok(html.includes('<label class="portal-sr-only" for="portal-copilot-text-input">'+want.input+'</label>'));
  assert.ok(html.includes('>'+want.send+'</button>'));
  const chips=Array.from(html.matchAll(/class="portal-copilot-chip"[^>]*>([^<]*)<\/button>/g),m=>m[1]);assert.deepEqual(chips,want.labels);
 });
 test(`Initial assistant greeting and navigation labels are clean ${locale} without unverified claims`,()=>{
  const html=runtime(locale).render(),text=visible(html);assert.ok(text.includes(expected[locale].title));
  assert.doesNotMatch(text,/4K|toàn bộ hệ sinh thái|điều khiển Web App|connected directly to all|control every|全部生态系统/i);
  if(locale==='vi')assert.doesNotMatch(text,/\b(?:Voiceover|Music|Asset Vault|Theme|prompt|workspace|studio|voice|pricing)\b/i);
  if(locale==='en')assert.doesNotMatch(text,/[\u00c0-\u024f\u4e00-\u9fff]/u);
  if(locale==='zh'){const allowed=new Set(['AI','AAS','BOT','TOAN','XU','SUBDUB']);assert.deepEqual((text.match(/[a-z][a-z0-9]*/gi)||[]).filter(w=>!allowed.has(w.toUpperCase())),[])}
 });
 test(`Assistant display translation keeps ${locale} legacy query values and all eight initial destinations`,()=>{
  const html=runtime(locale).render();assert.deepEqual(Array.from(html.matchAll(/data-copilot-query="([^"]+)"/g),m=>m[1]),queryValues);
  assert.deepEqual(Array.from(html.matchAll(/data-copilot-navigate="([^"]+)"/g),m=>m[1]),['/wallet/topup','/video/product','/image/create','/voice/tts','/subtitle','/music/direction','/pricing','/pricing']);
 });
}
test('Changing interface locale projects the greeting again, without changing user text or existing replies',()=>{
 const r=runtime('vi');r.state.messages.push({role:'user',text:'&lt;QA user English text&gt;'}, {role:'assistant',text:'Existing reply fixture',actions:[{label:'User-owned label',route:'/voice'}]});
 const before=JSON.stringify(r.state);r.locale('en');const html=r.render();assert.ok(visible(html).includes(expected.en.title));assert.ok(html.includes('&lt;QA user English text&gt;'));assert.ok(html.includes('Existing reply fixture'));assert.ok(html.includes('User-owned label'));assert.equal(JSON.stringify(r.state),before);
});
