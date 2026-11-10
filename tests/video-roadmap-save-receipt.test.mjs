import assert from 'node:assert/strict';
import test from 'node:test';
import {renderChild} from './helpers/publishing-child-render.mjs';

const fixtures={
  "receipt": {
    "longFormRoadmapEnabled": true,
    "capabilities": {
      "long-form-roadmap-compose": true,
      "long-form-roadmap-save-plan": true,
      "video-plan-create": true
    },
    "longFormRoadmapSaveReceipt": {
      "destination": "video_plan",
      "plan": {
        "id": "11111111-1111-4111-8111-111111111111",
        "revision": 1,
        "state": "draft"
      },
      "scene_count": 3,
      "execution": "web_native_video_plan_server_recomputed",
      "draft_recomputed_on_server": true,
      "web_video_plan_persisted": true,
      "browser_result_persisted": false,
      "pending_bot_save_created": false,
      "telegram_state_changed": false,
      "bot_called": false,
      "bridge_called": false,
      "source_media_inspected": false,
      "media_uploads": false,
      "provider_called": false,
      "image_created": false,
      "video_created": false,
      "audio_created": false,
      "preview_created": false,
      "output_created": false,
      "job_created": false,
      "wallet_mutated": false,
      "payment_started": false,
      "asset_saved": false,
      "publish_action_created": false,
      "delivery_created": false,
      "approval_created": false,
      "plan_approved": false,
      "plan_locked": false,
      "generation_started": false,
      "fact_checked": false,
      "rights_verified": false
    }
  }
};
const copy=[
  [
    "kicker",
    "Video Production Studio riêng tư",
    "Không gian kế hoạch video riêng tư",
    "Private video planning workspace",
    "私有视频规划工作区"
  ],
  [
    "title",
    "Đã lưu Long-form Video Plan Draft",
    "Đã lưu bản nháp kế hoạch video dài",
    "Long-form video plan draft saved",
    "已保存长视频计划草稿"
  ],
  [
    "chapters",
    "chapters",
    "chương",
    "chapters",
    "章"
  ],
  [
    "revision",
    "revision",
    "phiên bản",
    "revision",
    "版本"
  ],
  [
    "body",
    "Receipt không giữ topic, outline, character bible, chapter hoặc prompt trong browser.",
    "Xác nhận lưu không giữ chủ đề, dàn ý, hồ sơ nhân vật, chương hoặc mô tả trong trình duyệt.",
    "The save receipt does not retain topics, outlines, character guides, chapters or prompts in the browser.",
    "保存确认不会在浏览器中保留主题、大纲、角色指南、章节或提示词。"
  ],
  [
    "note",
    "Plan là bản ghi owner-only có thể biên tập. Không có pending Telegram, Bot/provider call, media, preview, output, job, Xu, PayOS, asset, publish, delivery, approval, lock hoặc generation.",
    "Kế hoạch là bản ghi riêng tư của tài khoản và có thể biên tập. Không tạo trạng thái chờ trên Telegram, gọi trợ lý tự động hoặc nhà cung cấp, tạo tệp đa phương tiện, bản xem trước, tệp đầu ra, tác vụ, tài nguyên, xuất bản, bàn giao, phê duyệt, khóa hoặc tạo nội dung; không thay đổi Xu hay PayOS.",
    "The plan is a private, editable account-owned record. Saving does not create pending Telegram state, call a bot or provider, create media, previews, output, jobs or assets, publish, deliver, approve, lock or generate content, or change Xu or PayOS.",
    "该计划是账户私有且可编辑的记录。保存不会创建Telegram待处理状态、调用机器人或供应商、创建媒体、预览、输出、任务或资源、发布、交付、审批、锁定或生成内容，也不会更改Xu或PayOS。"
  ],
  [
    "open",
    "Mở Video Plan",
    "Mở kế hoạch video",
    "Open video plan",
    "打开视频计划"
  ]
];
const locales=['vi','en','zh'];
const route='/video-studio/long-form-planner';
const clone=value=>JSON.parse(JSON.stringify(value));
const decode=value=>String(value).replace(/&amp;/g,'&').replace(/&quot;/g,'"').replace(/&#39;/g,"'").replace(/&lt;/g,'<').replace(/&gt;/g,'>');
const outputText=html=>decode(html.replace(/<[^>]+>/g,' ')).replace(/\s+/g,' ').trim();
const id=fixtures.receipt.longFormRoadmapSaveReceipt.plan.id;
const planPath='/video-studio/'+id;
const validViews=new Map();
for(const locale of locales){
  const raw=clone(fixtures.receipt),before=JSON.stringify(raw);
  const result=renderChild(locale,route,raw);
  assert.equal(JSON.stringify(raw),before,'Rendering must not mutate raw save receipt');
  validViews.set(locale,result);
}
const invalid=[];
function reject(name,mutate){
  const raw=clone(fixtures.receipt);mutate(raw);invalid.push({name,raw});
}
reject('missing receipt',raw=>{delete raw.longFormRoadmapSaveReceipt;});
reject('null receipt',raw=>{raw.longFormRoadmapSaveReceipt=null;});
reject('empty receipt',raw=>{raw.longFormRoadmapSaveReceipt={};});
reject('compact projection supplied as raw transport',raw=>{const v=raw.longFormRoadmapSaveReceipt;raw.longFormRoadmapSaveReceipt={destination:v.destination,plan:v.plan,scene_count:v.scene_count};});
reject('missing execution boundary',raw=>{delete raw.longFormRoadmapSaveReceipt.provider_called;});
reject('extra transport field',raw=>{raw.longFormRoadmapSaveReceipt.extra='not-allowed';});
reject('provider side effect',raw=>{raw.longFormRoadmapSaveReceipt.provider_called=true;});
reject('wallet side effect',raw=>{raw.longFormRoadmapSaveReceipt.wallet_mutated=true;});
reject('unconfirmed persistence',raw=>{raw.longFormRoadmapSaveReceipt.web_video_plan_persisted=false;});
reject('not recomputed on server',raw=>{raw.longFormRoadmapSaveReceipt.draft_recomputed_on_server=false;});
reject('wrong destination',raw=>{raw.longFormRoadmapSaveReceipt.destination='asset';});
reject('wrong execution',raw=>{raw.longFormRoadmapSaveReceipt.execution='provider_output';});
reject('unsafe plan id',raw=>{raw.longFormRoadmapSaveReceipt.plan.id='../../other-account';});
reject('extra plan field',raw=>{raw.longFormRoadmapSaveReceipt.plan.owner_id='other-account';});
reject('unaccepted revision',raw=>{raw.longFormRoadmapSaveReceipt.plan.revision=2;});
reject('unaccepted state',raw=>{raw.longFormRoadmapSaveReceipt.plan.state='approved';});
reject('too few chapters',raw=>{raw.longFormRoadmapSaveReceipt.scene_count=2;});
for(const locale of locales){
  const result=validViews.get(locale);
  test(locale+':valid transport receipt survives real strict normalization unchanged',()=>{
    assert.equal(Object.keys(fixtures.receipt.longFormRoadmapSaveReceipt).length,31);
    assert.equal(JSON.stringify(result.context.longFormRoadmapSaveReceipt),JSON.stringify({destination:'video_plan',plan:{id,revision:1,state:'draft'},scene_count:3}));
  });
  test(locale+':valid normalized receipt displays a truthful saved section and safe plan link',()=>{
    const link=result.html.match(new RegExp('<a\\b[^>]*href="'+planPath+'"[^>]*>([\\s\\S]*?)<\\/a>'));
    assert.ok(link,'A validated saved plan must show its own plan link after normalization');
    const offset=result.html.lastIndexOf('<section',link.index);
    const end=result.html.indexOf('</section>',link.index)+'</section>'.length;
    const section=result.html.slice(offset,end),text=outputText(section);
    assert.ok(section.includes('aria-live="polite"'),'Save confirmation must remain a polite live region');
    assert.equal((section.match(new RegExp('href="'+planPath+'"','g'))||[]).length,1);
    assert.equal(/data-portal-action=/.test(section),false,'Receipt must not create new generation/payment actions');
    assert.ok(text.includes('3'));
    assert.ok(text.includes('1'));
  });
  test(locale+':saved receipt fixed copy follows the interface locale',()=>{
    const linkIndex=result.html.indexOf('href="'+planPath+'"');
    assert.ok(linkIndex>=0,'Locale checks require the actual saved receipt to render');
    const offset=result.html.lastIndexOf('<section',linkIndex),end=result.html.indexOf('</section>',linkIndex)+'</section>'.length;
    const text=outputText(result.html.slice(offset,end));
    const column=locales.indexOf(locale)+2;
    for(const row of copy)assert.ok(text.includes(row[column]),'Missing localized receipt label: '+row[0]);
  });
  for(const variant of invalid){
    test(locale+':'+variant.name+' rejects false confirmation before rendering',()=>{
      const raw=clone(variant.raw),before=JSON.stringify(raw),view=renderChild(locale,route,raw);
      assert.equal(JSON.stringify(raw),before);
      assert.equal(JSON.stringify(view.context.longFormRoadmapSaveReceipt),'{}','Invalid transport must be dropped by real normalization');
      assert.equal(view.html.includes(planPath),false);
      assert.equal(view.html.includes('aria-live="polite"'),false,'No unrelated valid result is provided, so no saved live region may appear');
      for(const row of copy.filter(row=>row[0]==='title'||row[0]==='open')){
        for(const column of [1,2,3,4])assert.equal(outputText(view.html).includes(row[column]),false,'Rejected transport may not show success copy in any locale');
      }
    });
  }
}
