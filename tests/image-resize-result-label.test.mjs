import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import {createHash} from "node:crypto";
import {fileURLToPath} from "node:url";

const ROOT=fileURLToPath(new URL("../",import.meta.url)).replace(/[\\/]$/,"");
const AUTHORITY=new URL("./fixtures/image-resize-result-label-reviewed.json",import.meta.url);
const SHA="37bfdac3738688316fa7d5a403283f305897eb7019afd7351a0ac538be4d2eeb";
const {pageMetaRenderer,pageMetaSources}=await import("./helpers/chat-page-meta-runtime.mjs");
const {resizeReadyContext}=await import("./helpers/image-resize-guidance-runtime.mjs");
const authorityRaw=fs.readFileSync(AUTHORITY),authority=JSON.parse(authorityRaw),proposal=authority.proposal,edits=proposal.changes;
const count=(text,part)=>text.split(part).length-1,digest=value=>createHash("sha256").update(value).digest("hex");
const LOCALES=["vi","en","zh"],ROUTES=["/image/resize","/image/history"];
const COPY={
  vi:{label:"Đổi kích thước",old:"Đổi canvas",custom:"Tùy chỉnh",fit:{crop:"Cắt giữa khung · lấp đầy, có thể cắt rìa",pad:"Đệm nền trắng · giữ trọn ảnh, không cắt",blur:"Nền mờ · giữ trọn ảnh ở giữa, nền mờ"}},
  en:{label:"Image resize",old:"Canvas resize",custom:"Custom",fit:{crop:"Center crop · fill the frame, edges may be cropped",pad:"White padding · keep full image, no crop",blur:"Blurred background · keep image centered"}},
  zh:{label:"调整尺寸",old:"调整画布",custom:"自定义",fit:{crop:"居中裁剪 · 填满画面，可能裁掉边缘",pad:"白色填充 · 保留完整图像，不裁剪",blur:"模糊背景 · 图像居中保留"}}
};
function inverse(source){
  const phases=edits.map(edit=>[count(source,edit.old),count(source,edit.new)]);
  const old=phases.every(([before,after])=>before===1&&after===0),next=phases.every(([before,after])=>before===0&&after===1);
  assert.ok(old||next,"Only two exact all-OLD/all-NEW reviewed Resize result rows are accepted");
  let result=source;if(next)for(const edit of edits)result=result.replace(edit.new,()=>edit.old);return result;
}
const sources=pageMetaSources(),prior={...sources,i18n:inverse(sources.i18n)},isNew=edits.every(edit=>count(sources.i18n,edit.new)===1);
assert.equal(prior.portal,sources.portal);assert.equal(prior.pages,sources.pages);
const render=await pageMetaRenderer(sources),before=await pageMetaRenderer(prior);
const CUSTOMER='CUSTOMER media studio Facebook TikTok <img src=x onerror="literal">&',id=n=>"11111111-1111-4111-8111-"+String(n).padStart(12,"0");
const escape=value=>String(value).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;").replace(/'/g,"&#39;");
const decode=value=>value.replace(/&quot;/g,'"').replace(/&#39;/g,"'").replace(/&lt;/g,"<").replace(/&gt;/g,">").replace(/&amp;/g,"&");
function freeze(value){if(value&&typeof value==="object"&&!Object.isFrozen(value)){Object.freeze(value);for(const child of Object.values(value))freeze(child);}return value;}
function item(n,extra={}){
  return{id:id(n),kind:"image_resize",state:"completed",download_ready:true,original_filename:CUSTOMER+".png",
    source_width:640,source_height:480,target_width:1280,target_height:720,byte_size:2048,fit_mode:"crop",preset:"custom",
    created_at:"2026-11-18T01:02:03Z",updated_at:"2026-11-18T02:03:04Z",completed_at:"2026-11-18T03:04:05Z",...extra};
}
function context(items,state="ready"){
  const raw=resizeReadyContext();raw.profile={locale:"en",displayName:CUSTOMER};raw.imageOperations=items;raw.imageHistoryOperations=items;raw.imageHistoryReadState="ready";
  raw.imageOperationListing={filters:{},pagination:{offset:0,returned:items.length,has_more:false,next_offset:null,previous_offset:null}};
  raw.imageHistoryListing={filters:{kind:"all"},pagination:{offset:0,returned:items.length,has_more:false,next_offset:null,previous_offset:null}};
  if(state==="guarded")raw.capabilities["image-operation-view"]=false;
  if(["loading","failed"].includes(state)){raw.assetVaultReadState=state;raw.imageOperationsReadState=state;raw.imageOperationAssetReferenceReadState=state;raw.imageHistoryReadState=state;}
  if(state==="read-only")raw.capabilities["image-operation-resize"]=false;
  return raw;
}
function view(renderer,locale,route,items,state="ready"){
  const raw=freeze(context(items,state)),saved=JSON.stringify(raw),output=renderer(locale,route,raw);
  assert.equal(JSON.stringify(raw),saved,"Full raw context stays immutable");assert.equal(output.route,route);return output;
}
function cardMatch(html,operationId){
  const matches=[...html.matchAll(/<article\b[^>]*data-image-operation="([^"]+)"[\s\S]*?<\/article>/g)].filter(match=>match[1]===operationId);
  assert.equal(matches.length,1,"One actual operation card "+operationId);return matches[0];
}
const card=(html,operationId)=>cardMatch(html,operationId)[0];
const one=(text,pattern,label)=>{const matches=[...text.matchAll(pattern)];assert.equal(matches.length,1,label);return matches[0];};
const captionNode=html=>one(html,/(<p class="portal-card-subtitle">)([\s\S]*?)(<\/p>)/g,"One selected card subtitle");
const typeNode=html=>one(html,/(<dl class="portal-document-operation-meta"><div><dt>[^<]*<\/dt><dd>)([^<]*)(<\/dd>)/g,"One first History type cell");
const caption=(html,operationId)=>decode(captionNode(card(html,operationId))[2]);
const type=(html,operationId)=>decode(typeNode(card(html,operationId))[2]);
const token=(row,locale)=>String(row.preset||"custom")==="custom"?COPY[locale].custom:String(row.preset||"custom");
const expected=(row,locale)=>COPY[locale].label+" · "+COPY[locale].fit[row.fit_mode]+" · "+token(row,locale);
function assertActualLabels(output,locale,route,rows){
  for(const row of rows){
    assert.equal(caption(output.html,row.id),expected(row,locale));
    if(route==="/image/history")assert.equal(type(output.html,row.id),COPY[locale].label);
  }
}
function projectOwnedLabel(html,oldHtml,operationId,locale,route){
  const selected=cardMatch(html,operationId),old=card(oldHtml,operationId),now=selected[0],next=captionNode(now),previous=captionNode(old);
  const label=escape(isNew?COPY[locale].label:COPY[locale].old),oldLabel=escape(COPY[locale].old);
  assert.ok(next[2].startsWith(label+" · "));assert.ok(previous[2].startsWith(oldLabel+" · "));
  assert.equal(next[2].slice(label.length),previous[2].slice(oldLabel.length),"Every fit/preset byte after fixed prefix is protected");
  const edits=[{start:next.index+next[1].length,length:label.length,value:oldLabel}];
  if(route==="/image/history"){
    const nextType=typeNode(now),oldType=typeNode(old);assert.equal(nextType[2],label);assert.equal(oldType[2],oldLabel);
    edits.push({start:nextType.index+nextType[1].length,length:nextType[2].length,value:oldType[2]});
  }
  let projected=now;for(const edit of edits.sort((a,b)=>b.start-a.start))projected=projected.slice(0,edit.start)+edit.value+projected.slice(edit.start+edit.length);
  return html.slice(0,selected.index)+projected+html.slice(selected.index+now.length);
}
function vectorGroups(locale){
  const absent=item(3,{fit_mode:"blur"});delete absent.preset;
  return[
    [item(1),item(2,{preset:"",fit_mode:"pad"}),absent,item(4,{preset:undefined,fit_mode:"blur"})],
    ["1:1","4:5","9:16","16:9","3:4","4:3","3:2","2:3","21:9"].map((preset,index)=>item(10+index,{preset,fit_mode:["crop","pad","blur"][index%3]})),
    [item(30,{preset:CUSTOMER,fit_mode:"pad"}),item(31,{preset:"CUSTOM",fit_mode:"blur"}),
      item(32,{preset:COPY[locale].old,original_filename:COPY[locale].old}),item(33,{preset:COPY[locale].label,original_filename:COPY[locale].label})],
    [item(40),item(41,{download_ready:false}),item(42,{state:"failed",download_ready:true}),item(43,{state:"qa_unknown_state",download_ready:true})]
  ];
}
const nonResize=()=>[
  item(70,{kind:"image_brand_overlay",settings:{text_position:"bottom_center",logo_position:"bottom_right",logo_scale_percent:18,logo_opacity_percent:78}}),
  item(71,{kind:"image_background_cleanup",settings:{profile:"white_studio"}}),
  item(72,{kind:"image_enhance",preset:"product_clean",settings:{brightness:1.1,contrast:1.2,saturation:1.3,sharpness:1.4,tone:"warm",basic_upscale:true}})
];
for(const locale of LOCALES){
  test(`${locale}: actual Resize subtitle prefix and History type use the reviewed plain result label`,()=>{
    const rows=[item(90)];for(const route of ROUTES)assertActualLabels(view(render,locale,route,rows),locale,route,rows);
  });
  test(`${locale}: both physical consumers retain every RSC fallback/ratio/fit/customer/state vector under the new label`,()=>{
    for(const route of ROUTES)for(const rows of vectorGroups(locale)){
      const output=view(render,locale,route,rows);assertActualLabels(output,locale,route,rows);
      for(const row of rows){
        const html=card(output.html,row.id);assert.ok(html.includes('<h2 class="portal-card-title">'+escape(row.original_filename)+"</h2>"));
        assert.equal(html.includes("<img src=x"),false);
        const href='/api/v1/image-operations/'+row.id+'/download';assert.equal(html.includes(href),row.state==="completed"&&row.download_ready===true);
        for(const value of ["640 × 480","1280 × 720","2026-11-18T03:04:05Z"])assert.ok(html.includes(value),value);
      }
      const saved=JSON.stringify(output.context);freeze(output.context);assert.equal(output.qa.renderPage(output.page,output.context),output.html);assert.equal(JSON.stringify(output.context),saved);
    }
  });
  test(`${locale}: whole HTML differs only in one owned card's fixed prefix and exact History type cell`,()=>{
    const selected=item(80,{preset:COPY[locale].old+" / "+COPY[locale].label+" / "+CUSTOMER,original_filename:COPY[locale].label});
    for(const route of ROUTES){
      const rows=route==="/image/history"?[selected,...nonResize()]:[selected],now=view(render,locale,route,rows),old=view(before,locale,route,rows);
      assert.equal(projectOwnedLabel(now.html,old.html,selected.id,locale,route),old.html);
      assert.equal(JSON.stringify(now.context),JSON.stringify(old.context));assert.equal(now.attributes,old.attributes);assert.equal(now.title,old.title);
      assert.equal(now.qa.renderHeader(now.page,now.context),old.qa.renderHeader(old.page,old.context));
      const selectedHtml=card(now.html,selected.id);assert.ok(selectedHtml.includes('<h2 class="portal-card-title">'+escape(COPY[locale].label)+"</h2>"));
      assert.ok(selectedHtml.includes(escape(selected.preset)),"Customer preset equal OLD/NEW labels remains literal");
      if(route==="/image/history")for(const row of nonResize())assert.equal(card(now.html,row.id),card(old.html,row.id));
    }
  });
}
test("mixed History non-Resize complete cards remain identical with and without the Resize card",()=>{
  for(const locale of LOCALES){
    const other=nonResize(),mixed=view(render,locale,"/image/history",[item(79),...other]),separate=view(render,locale,"/image/history",other);
    for(const row of other)assert.equal(card(mixed.html,row.id),card(separate.html,row.id));
  }
});
test("guarded/loading/failed/empty/read-only page guards and controls stay byte-identical",()=>{
  for(const locale of LOCALES)for(const route of ROUTES)for(const state of ["guarded","loading","failed","empty","read-only"]){
    const now=view(render,locale,route,[],state),old=view(before,locale,route,[],state);
    assert.equal(now.html,old.html);assert.equal(JSON.stringify(now.context),JSON.stringify(old.context));assert.equal(now.attributes,old.attributes);assert.equal(now.title,old.title);
    assert.equal([...now.html.matchAll(/data-image-operation="/g)].length,0);
    if(["guarded","loading","failed"].includes(state))assert.doesNotMatch(now.html,/<form\b/);
  }
});
test("same VM switches fixed Resize result labels and custom/fit text VI -> EN -> ZH -> VI",()=>{
  for(const route of ROUTES){
    const rows=[item(95)],output=view(render,"vi",route,rows),saved=JSON.stringify(output.context);freeze(output.context);
    for(const locale of ["vi","en","zh","vi"]){output.setLocale(locale);assertActualLabels({...output,html:output.qa.renderPage(output.page,output.context)},locale,route,rows);assert.equal(JSON.stringify(output.context),saved);}
  }
});
test("canonical authority is exact two count-one rows, one file, R1 and reviewed VI/EN/ZH labels",()=>{
  assert.equal(digest(authorityRaw),SHA);
  assert.equal(authority.review.schemaValid,true);assert.equal(authority.review.proposalExact,true);assert.equal(authority.review.conversation,"fbea6cea-423c-4d42-8769-f1a05f865c24");
  assert.equal(authority.review.specId,"IMAGE-RESIZE-PLAIN-RESULT-COPY-20261118");assert.equal(proposal.specId,"IMAGE-RESIZE-PLAIN-RESULT-COPY-20261118");assert.equal(proposal.revision,"R1");assert.equal(edits.length,2);
  for(const[index,edit]of edits.entries()){
    assert.equal(edit.file,"static/portal/portal-i18n.js");assert.equal(edit.count,1);
    const key=index===0?"result.resize.subtitle":"result.history.operation.resize",tail=index===0?" · {preset}":"";
    assert.deepEqual(JSON.parse(edit.old.trim().replace(/,$/,"")),[key,...LOCALES.map(locale=>COPY[locale].old+tail)]);
    assert.deepEqual(JSON.parse(edit.new.trim().replace(/,$/,"")),[key,...LOCALES.map(locale=>COPY[locale].label+tail)]);
  }
});
test("finite two-row inverse rejects partial/unknown/duplicate phases without swallowing outside bytes",()=>{
  const old=edits.map(edit=>edit.old).join("\n"),next=edits.map(edit=>edit.new).join("\n");
  assert.equal(inverse(old),old);assert.equal(inverse(next),old);
  assert.equal(inverse("CUSTOMER Facebook TikTok\n"+sources.i18n+"\nOUTSIDE"),"CUSTOMER Facebook TikTok\n"+prior.i18n+"\nOUTSIDE");
  assert.throws(()=>inverse(old.replace(edits[0].old,edits[0].new)),/all-OLD\/all-NEW/);assert.throws(()=>inverse(next.replace(edits[0].new,"UNKNOWN")),/all-OLD\/all-NEW/);
  assert.throws(()=>inverse(old+"\n"+edits[0].old),/all-OLD\/all-NEW/);
});
