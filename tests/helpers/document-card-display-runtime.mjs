import fs from "node:fs";
import path from "node:path";
import assert from "node:assert/strict";
import {execFileSync} from "node:child_process";
import {fileURLToPath} from "node:url";
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),"../..");
export const DOCUMENT_CARD_DISPLAY_BASE="c40f94ce713576a65a8d30399bd3b8516346cba2";
export function documentCardDisplaySources(historical=false){
  return Object.fromEntries(Object.entries({portal:"static/portal/portal.js",i18n:"static/portal/portal-i18n.js"}).map(([key,file])=>[
    key,(historical?execFileSync("git",["show",DOCUMENT_CARD_DISPLAY_BASE+":"+file],{cwd:root,encoding:"utf8",maxBuffer:30e6}):
      fs.readFileSync(path.join(root,file),"utf8")).replace(/\r\n/g,"\n")]));
}
export async function documentCardDisplayRenderer(sources=documentCardDisplaySources()){
  let helper=fs.readFileSync(path.join(root,"tests/helpers/chat-page-meta-runtime.mjs"),"utf8");
  const once=(old,next)=>{assert.equal(helper.split(old).length-1,1);helper=helper.replace(old,next);};
  once("\nconst root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');\nexport const PAGE_META_BASE=",
    "\nconst root="+JSON.stringify(root)+";\nexport const PAGE_META_BASE=");
  once("window.__childLocale={renderHeader,",
    "window.__childLocale={renderDocumentOperationCards,documentOperationState,documentOperationDownloadPath,imageOcrLanguageLabel,chatWorkspaceDateLabel,withDateFormatter:(fn,run)=>{const old=localizedDateTime;try{localizedDateTime=fn;return run();}finally{localizedDateTime=old;}},renderHeader,");
  return(await import("data:text/javascript;base64,"+Buffer.from(helper).toString("base64"))).pageMetaRenderer(sources);
}
