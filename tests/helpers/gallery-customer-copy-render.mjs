// Real full portal/i18n renderer in an isolated VM; no presentation-function stubs.
import fs from "node:fs";
import path from "node:path";
import assert from "node:assert/strict";
import {fileURLToPath} from "node:url";
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),"../..");
const read=file=>fs.readFileSync(path.join(root,file),"utf8").replace(/\r\n/g,"\n");
export const galleryFiles=["static/portal/portal.js","static/portal/portal-i18n.js"];
export const physicalGallerySources=()=>Object.fromEntries(galleryFiles.map(file=>[file,read(file)]));
export async function galleryRendererFromSources(sources){
  let helper=read("tests/helpers/publishing-child-render.mjs");
  const replace=(old,next)=>{assert.equal(helper.split(old).length-1,1);helper=helper.replace(old,()=>next);};
  replace("const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');","const root="+JSON.stringify(root)+";");
  for(const[name,file]of[["portal",galleryFiles[0]],["i18n",galleryFiles[1]]]){
    replace(`const ${name}=fs.readFileSync(path.join(root,'${file}'),'utf8');`,`const ${name}=${JSON.stringify(sources[file])};`);
  }
  replace("normalizePublishReviewPackResult,customerMobileNavGroupForPath};",
    'normalizePublishReviewPackResult,customerMobileNavGroupForPath,gallerySourceText:value=>typeof freePromptGallerySourceText==="function"?freePromptGallerySourceText(value):String(value||""),localizedPageDescription,renderFreePromptGalleryDetail,renderFreePromptGallerySaveResult};');
  replace("return {html,text:plain(html),",
    'return {sourceText:window.__childLocale.gallerySourceText,pageDescription:window.__childLocale.localizedPageDescription(page),detailPreview:raw=>window.__childLocale.renderFreePromptGalleryDetail(raw,true,true),savedPreview:(raw,id)=>window.__childLocale.renderFreePromptGallerySaveResult(raw,id),html,text:plain(html),');
  return(await import("data:text/javascript;base64,"+Buffer.from(helper).toString("base64"))).renderChild;
}
export const galleryKnownDescription="Bộ seed prompt Free Hub đã rà soát, cố định cho Web App.";
export const galleryKnownInstruction="Dùng seed này làm brief hoặc prompt; tự rà soát sự chính xác, quyền sử dụng và claim trước khi xuất bản.";
export const galleryCustomer={
  title:"CUSTOMER_TITLE <script>not executable</script>",prompt:"CUSTOMER_PROMPT <safe> & Tiếng Việt",
  category:"CUSTOMER_CATEGORY",industry:"CUSTOMER_INDUSTRY",note:"CUSTOMER_NOTE"
};
export function galleryContext(state="list",{known=true,priority="normal"}={}){
  const boundaries={execution:"web_native_static_prompt_gallery",snapshot_read_only:true,
    ...Object.fromEntries(["gallery_request_persisted","provider_called","bot_called","bridge_called","job_created",
      "wallet_mutated","payment_started","asset_saved","publish_action_created","delivery_created"].map(key=>[key,false]))};
  const item={id:"sample_one",category_id:"category_one",category_title:galleryCustomer.category,industry_id:"industry_one",
    industry:galleryCustomer.industry,title:galleryCustomer.title,prompt:galleryCustomer.prompt,goals:["customer_goal"],platforms:["facebook"]};
  const hasItem=["list","detail","saved"].includes(state),hasDetail=["detail","saved"].includes(state);
  return{capabilities:{"free-prompt-gallery-view":state!=="guarded","free-prompt-gallery-save":state!=="guarded"},
    profile:{displayName:"CUSTOMER_PROFILE"},
    freePromptGalleryCatalog:{snapshot_version:state==="guarded"?"":"gallery-v1",description:known?galleryKnownDescription:"CUSTOMER_DESCRIPTION <safe>",
      total_items:1,categories:[{id:"category_one",title:galleryCustomer.category,goals:["customer_goal"],platforms:["facebook"],item_count:1}],
      industries:[{id:"industry_one",title:galleryCustomer.industry,item_count:1}],boundaries},
    freePromptGalleryListing:{snapshot_version:"gallery-v1",filters:{category_id:"",industry_id:"",goal:"",platform:"",q:"CUSTOMER_QUERY"},
      pagination:{page:1,page_size:20,total_items:hasItem?1:0,total_pages:1,has_next:false,has_previous:false},items:hasItem?[item]:[],boundaries},
    freePromptGalleryDetail:hasDetail?{snapshot_version:"gallery-v1",item,copy_instruction:known?galleryKnownInstruction:"CUSTOMER_COPY_INSTRUCTION <safe>",boundaries}:{},
    freePromptGallerySaveResult:state==="saved"?{note:{id:"11111111-1111-4111-8111-111111111111",category:galleryCustomer.note,priority,state:"active",revision:2},
      gallery:{prompt_id:"sample_one",snapshot_version:"gallery-v1"}}:{}};
}
export const galleryEscape=value=>String(value).replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;").replaceAll('"',"&quot;").replaceAll("'","&#39;");
export function galleryAssertNormalized(row,state){
  if(state!=="guarded"){
    assert.equal(row.context.freePromptGalleryCatalog.snapshot_version,"gallery-v1");
    assert.equal(row.context.freePromptGalleryListing.snapshot_version,"gallery-v1");
    assert.equal(row.context.freePromptGalleryListing.items.length,["list","detail","saved"].includes(state)?1:0);
  }
  if(["detail","saved"].includes(state))assert.equal(row.context.freePromptGalleryDetail.item.id,"sample_one");
  if(state==="saved")assert.equal(row.context.freePromptGallerySaveResult.note.revision,2);
}
