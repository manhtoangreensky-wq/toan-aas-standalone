import fs from "node:fs";
import path from "node:path";
import assert from "node:assert/strict";
import {fileURLToPath} from "node:url";
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),"../..");
export const RESIZE_CUSTOMER='CUSTOMER media studio provider Facebook TikTok <img src=x onerror="literal">&';
export const RESIZE_ID="11111111-1111-4111-8111-111111111111";
export function resizeReadyContext(){
  const file={id:RESIZE_ID,display_name:RESIZE_CUSTOMER,original_filename:RESIZE_CUSTOMER+".png",extension:".png",
    content_type:"image/png",byte_size:1024,state:"active",updated_at:"2026-11-17T00:00:00Z"};
  return {capabilities:{"image-operation-view":true,"image-operation-resize":true,"image-operation-refresh":true},
    assetVaultEnabled:true,imageOperationsEnabled:true,imageResizeEnabled:true,assetVaultReadState:"ready",
    imageOperationsReadState:"ready",imageOperationAssetReferenceReadState:"ready",vaultItems:[file],imageOperations:[],
    imageOperationAssetReferences:{items:[file],pinned:[],listing:{kind:"image",filters:{q:""},
      pagination:{limit:50,offset:0,returned:1,has_more:false,next_offset:null,previous_offset:null}}}};
}
export function resizeGuidanceSources(){
  return Object.fromEntries([["portal","static/portal/portal.js"],["i18n","static/portal/portal-i18n.js"]]
    .map(([key,file])=>[key,fs.readFileSync(path.join(root,file),"utf8").replace(/\r\n/g,"\n")]));
}
export async function resizeGuidanceRenderer(sources=resizeGuidanceSources()){
  // Execute both full physical bundles through the established network-denying renderer.
  let helper=fs.readFileSync(path.join(root,"tests/helpers/publishing-child-render.mjs"),"utf8");
  const once=(old,next)=>{assert.equal(helper.split(old).length-1,1,"Exact renderer read boundary");helper=helper.replace(old,()=>next);};
  once("const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');","const root="+JSON.stringify(root)+";");
  for(const [key,file]of [["portal","static/portal/portal.js"],["i18n","static/portal/portal-i18n.js"]]){
    assert.equal(typeof sources[key],"string");
    once("const "+key+"=fs.readFileSync(path.join(root,'"+file+"'),'utf8');","const "+key+"="+JSON.stringify(sources[key])+";");
  }
  return (await import("data:text/javascript;base64,"+Buffer.from(helper).toString("base64"))).renderChild;
}
export const resizeDecode=value=>value.replace(/&quot;/g,'"').replace(/&#39;/g,"'").replace(/&lt;/g,"<").replace(/&gt;/g,">").replace(/&amp;/g,"&");
export function resizeVisibleGuidance(html){
  const form=html.match(/<section class="portal-card portal-card-pad portal-document-operation-form">([\s\S]*?)<\/section>/);
  const boundary=html.match(/<aside class="portal-card portal-card-pad portal-document-operation-boundary">([\s\S]*?)<\/aside>/);
  assert.ok(form,"Actual ready Resize form");assert.ok(boundary,"Actual Resize guidance section");
  const read=(part,pattern)=>{const match=part.match(pattern);assert.ok(match,"Existing text slot");return resizeDecode(match[1]);};
  return {form:read(form[1],/<p class="portal-card-subtitle">([^<]*)<\/p>/),
    ready:read(html,/<span class="portal-form-note">([^<]*)<\/span>/),
    boundary:read(boundary[1],/<p class="portal-card-subtitle">([^<]*)<\/p>/)};
}
