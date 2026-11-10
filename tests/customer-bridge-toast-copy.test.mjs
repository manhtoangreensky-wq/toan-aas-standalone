import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import test from 'node:test';

const integration=fs.readFileSync(new URL('../static/portal/integration.js',import.meta.url),'utf8');
const i18n=fs.readFileSync(new URL('../static/portal/portal-i18n.js',import.meta.url),'utf8');
const a=integration.indexOf('  function toast(message, type) {'),b=integration.indexOf('\n  }',a)+4;
assert.ok(a>=0&&b>a);
const cases=[
 ['draft','Bản nháp canonical đã được cập nhật.','Đã cập nhật bản nháp.','Draft has been updated.','草稿已更新。'],
 ['awaiting_confirm','Dữ liệu canonical đang chờ bước xác nhận phù hợp.','Vui lòng kiểm tra thông tin và xác nhận.','Please check the information and confirm.','请核对信息并确认。'],
 ['queued','Yêu cầu đã được canonical queue ghi nhận.','Yêu cầu đã được tiếp nhận.','Request has been received.','请求已接收。'],
 ['processing','Core Bridge đang cập nhật trạng thái canonical.','Đang cập nhật trạng thái.','Updating status.','正在更新状态。'],
 ['completed','Dữ liệu canonical đã được cập nhật.','Dữ liệu đã được cập nhật.','Data has been updated.','数据已更新。'],
 ['failed','Core Bridge chưa thể cấp dữ liệu an toàn.','Không thể tải dữ liệu. Vui lòng thử lại.','Unable to load data. Please try again.','无法加载数据，请重试。'],
 ['failed_no_charge','Yêu cầu không tạo kết quả; ledger canonical không bị browser thay đổi.','Yêu cầu chưa tạo được kết quả.','Request did not produce results.','请求未生成结果。'],
 ['guarded','Khả năng này đang được Core Bridge bảo vệ.','Không thể thực hiện thao tác này lúc này.','Cannot perform this action right now.','当前无法执行此操作。'],
 ['cancelled','Yêu cầu đã được canonical hủy.','Yêu cầu đã được hủy.','Request has been cancelled.','请求已取消。'],
 ['refunded','Core Bridge đã ghi nhận trạng thái hoàn Xu canonical.','Đã ghi nhận trạng thái hoàn Xu.','Xu refund status recorded.','已记录 Xu 退款状态。'],
 ['read_only','Dữ liệu canonical chỉ được hiển thị ở chế độ đọc.','Dữ liệu đang ở chế độ chỉ xem.','Data is in read-only mode.','数据处于只读模式。'],
 ['unverified','Tài khoản Telegram chưa kích hoạt trong hệ thống Bot.','Hãy kích hoạt tài khoản Telegram để tiếp tục.','Please activate your Telegram account to continue.','请激活 Telegram 账号以继续。'],
 ['unlinked','Tài khoản chưa liên kết Telegram.','Hãy liên kết tài khoản Telegram để tiếp tục.','Please link your Telegram account to continue.','请关联 Telegram 账号以继续。']
];
function runtime(locale){
 const nodes=[],timers=[];const noop=()=>{};
 const region={querySelectorAll:()=>nodes,appendChild:n=>nodes.push(n)};
 const document={readyState:'loading',addEventListener:noop,documentElement:{lang:locale,setAttribute:noop,getAttribute:()=>null},body:{classList:{add:noop,remove:noop}},querySelector:()=>region,createElement:()=>({className:'',textContent:'',attributes:{},setAttribute(k,v){this.attributes[k]=v;},remove(){const i=nodes.indexOf(this);if(i>=0)nodes.splice(i,1);}})};
 const window={document,navigator:{language:locale},location:{pathname:'/publishing',search:''},localStorage:{getItem:()=>null,setItem:noop},addEventListener:noop,dispatchEvent:noop,setTimeout:(fn,ms)=>timers.push({fn,ms})};
 const sandbox=vm.createContext({window,document,navigator:window.navigator,URL,URLSearchParams,Intl,console});vm.runInContext(i18n,sandbox);window.TOANAASI18n.setLocale(locale,{emit:false});const toast=vm.runInContext('('+integration.slice(a,b)+')',sandbox);
 return{toast,nodes,timers};
}
for(const[locale,index]of[['vi',2],['en',3],['zh',4]]){
 for(const row of cases)test(locale+': exact '+row[0]+' feedback follows its customer presentation rule',()=>{const r=runtime(locale);r.toast(row[1],'error');if(row[0]==='guarded'){assert.equal(r.nodes.length,0);assert.equal(r.timers.length,0);return;}assert.equal(r.nodes.length,1);assert.equal(r.nodes[0].textContent,row[index]);assert.equal(r.nodes[0].attributes.role,'alert');assert.match(r.nodes[0].className,/warning/);assert.equal(r.timers[0].ms,6500);});
 for(const text of['CUSTOMER message <b>keep & text</b>','__proto__','constructor','toString'])test(locale+': unknown message remains exact: '+text,()=>{const r=runtime(locale);r.toast(text);assert.equal(r.nodes[0]?.textContent,text);assert.equal(r.nodes[0].attributes.role,'status');});
 test(locale+': duplicate feedback stays deduplicated and dismisses on same timer',()=>{const r=runtime(locale);r.toast(cases[5][1],'error');r.toast(cases[5][1],'error');assert.equal(r.nodes.length,1);assert.equal(r.timers.length,1);r.timers[0].fn();assert.equal(r.nodes.length,0);});
}
