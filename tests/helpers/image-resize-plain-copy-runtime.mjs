import assert from "node:assert/strict";
import {resizeDecode,resizeReadyContext} from "./image-resize-guidance-runtime.mjs";
export const oneSlot=(html,pattern,label)=>{const m=html.match(pattern);assert.ok(m,"Actual Resize slot "+label);return resizeDecode(m[1]);};
export function resizeCopyContext(state="ready"){
  const context=resizeReadyContext();
  if(state==="guard")context.capabilities["image-operation-view"]=false;
  if(state==="loading"||state==="failed")context.assetVaultReadState=state;
  if(state==="noRun"||state==="disabled")context.capabilities["image-operation-resize"]=false;
  if(state==="disabled")context.imageResizeEnabled=false;
  if(state==="empty"){context.vaultItems=[];context.imageOperationAssetReferences.items=[];}
  if(state==="card")context.imageOperations=[{id:"22222222-2222-4222-8222-222222222222",kind:"image_resize",state:"processing",
    original_filename:"",target_width:undefined,target_height:undefined,source_width:640,source_height:480,
    fit_mode:"crop",preset:"custom",byte_size:0,download_ready:false,created_at:"2026-11-17T00:00:00Z",updated_at:"2026-11-17T00:00:00Z"}];
  return context;
}
export function resizeCopySlot(html,key){
  const one=(pattern,label)=>oneSlot(html,pattern,label);
  if(key.startsWith("resize.guard."))return key.endsWith(".title")?one(/<div class="portal-state"[\s\S]*?<h2>([^<]*)<\/h2>/,"guard title"):one(/<div class="portal-state"[\s\S]*?<h2>[^<]*<\/h2><p>([^<]*)<\/p>/,"guard body");
  if(key==="resize.loading.body"||key==="resize.failed.body")return one(/<div class="portal-state"[\s\S]*?<h2>[^<]*<\/h2><p>([^<]*)<\/p>/,"read body");
  if(key.startsWith("resize.intro.")){
    const part=one(/<section class="portal-document-operation-intro">([\s\S]*?)<\/section>/,"intro");
    return key.endsWith(".kicker")?oneSlot(part,/<span class="portal-section-kicker">([^<]*)<\/span>/,"kicker"):key.endsWith(".title")?oneSlot(part,/<h2>([^<]*)<\/h2>/,"intro title"):oneSlot(part,/<p>([^<]*)<\/p>/,"intro body");
  }
  if(key.startsWith("resize.form.")){
    const part=one(/<section class="portal-card portal-card-pad portal-document-operation-form">([\s\S]*?<\/form>)<\/section>/,"form");
    return key.endsWith(".title")?oneSlot(part,/<h2 class="portal-card-title">([^<]*)<\/h2>/,"formtitle"):key.endsWith(".confirm")?oneSlot(part,/<form[^>]*data-portal-confirm="([^"]*)"/,"confirm"):oneSlot(part,/<button[^>]*type="submit"[^>]*>([^<]*)<\/button>/,"submit");
  }
  if(key.startsWith("field.resize.")){
    const name=key.includes(".preset.")?"preset":key.includes(".width.")?"target_width":key.includes(".height.")?"target_height":"fit_mode";
    const field=[...html.matchAll(/<div class="portal-field[^"]*"[^>]*>([\s\S]*?)(?=<div class="portal-field|<\/div><div class="portal-form-footer")/g)].map(m=>m[1]).find(part=>part.includes('name="'+name+'"'));
    assert.ok(field,"Existing field "+name);
    if(key.endsWith(".label"))return oneSlot(field,/<label[^>]*>([\s\S]*?)<\/label>/,"field label").replace(/<span[\s\S]*?<\/span>/g,"").trim();
    if(key.endsWith(".help"))return oneSlot(field,/<(?:div|p|span)[^>]* class="portal-field-help"[^>]*>([\s\S]*?)<\/(?:div|p|span)>/,"field help");
    const value=key.endsWith(".custom")?"custom":key.endsWith(".story")?"9:16":"crop";
    return oneSlot(field,new RegExp('<option value="'+value+'"[^>]*>([^<]*)</option>'),"option");
  }
  if(key.startsWith("resize.runReason."))return one(/<span class="portal-form-note">([^<]*)<\/span>/,"run reason");
  if(key==="resize.sourceCount")return one(/<section class="portal-document-operation-intro">[\s\S]*?<dt>([^<]*)<\/dt>/,"source count");
  if(key==="resize.metric.sources")return one(/<section class="portal-document-operation-intro">[\s\S]*?<dd>([^<]*)<\/dd>/,"source metric");
  if(key==="resize.results.description")return one(/<section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">[^<]*<\/h2><p class="portal-card-subtitle">([^<]*)<\/p>/,"result description");
  if(key==="resize.empty.title")return one(/<div class="portal-empty[^"]*">[\s\S]*?<h[23][^>]*>([^<]*)<\/h[23]>/,"empty title");
  if(key==="resize.empty.body")return one(/<div class="portal-empty[^"]*">[\s\S]*?<p[^>]*>([^<]*)<\/p>/,"empty body");
  if(key==="resize.fallbackName")return one(/data-image-operation="[^"]+"[\s\S]*?<h2 class="portal-card-title">([^<]*)<\/h2>/,"card fallback title");
  if(key==="resize.targetFallback")return one(/data-image-operation="[^"]+"[\s\S]*?<dt>[^<]*<\/dt><dd>[^<]*<\/dd><\/div><div><dt>[^<]*<\/dt><dd>([^<]*)<\/dd>/,"target fallback");
  const part=one(/<aside class="portal-card portal-card-pad portal-document-operation-boundary">([\s\S]*?)<\/aside>/,"placement");
  if(key==="resize.boundary.title")return oneSlot(part,/<h2 class="portal-card-title">([^<]*)<\/h2>/,"placement title");
  const steps=[...part.matchAll(/<li><strong>[\s\S]*?<\/strong><span>([^<]*)<\/span><\/li>/g)];assert.equal(steps.length,3);
  return resizeDecode(steps[key.includes(".crop.")?0:key.includes(".pad.")?1:2][1]);
}
export function resizeCopyStateForKey(key){
  if(key.startsWith("resize.guard."))return"guard";
  if(key==="resize.loading.body")return"loading";if(key==="resize.failed.body")return"failed";
  if(key==="resize.runReason.capability")return"noRun";if(key==="resize.runReason.disabled")return"disabled";if(key==="resize.runReason.empty")return"empty";
  if(["resize.targetFallback","resize.fallbackName"].includes(key))return"card";return"ready";
}
