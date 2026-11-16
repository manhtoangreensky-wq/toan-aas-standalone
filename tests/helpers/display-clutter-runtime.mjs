import fs from "node:fs";
import path from "node:path";
import assert from "node:assert/strict";
import {execFileSync} from "node:child_process";
import {fileURLToPath} from "node:url";
import {documentCardDisplayHistoricalPortalSource,documentCardDisplayHistoricalI18nSource} from "./document-card-display-snapshot.mjs";
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),"../..");
export const DISPLAY_CLUTTER_BASE="206eccc2eabe546ac11be89c26423eb9bf58df81";
export function displayClutterSources(historical=false){
  return Object.fromEntries(Object.entries({portal:"static/portal/portal.js",i18n:"static/portal/portal-i18n.js"}).map(([key,file])=>{
    const source=(historical?execFileSync("git",["show",DISPLAY_CLUTTER_BASE+":"+file],{cwd:root,encoding:"utf8",maxBuffer:30e6}):
      fs.readFileSync(path.join(root,file),"utf8")).replace(/\r\n/g,"\n");
    return [key,key==="portal"?documentCardDisplayHistoricalPortalSource(source):documentCardDisplayHistoricalI18nSource(source)];
  }));
}
export async function displayClutterRenderer(sources=displayClutterSources()){
  let helper=fs.readFileSync(path.join(root,"tests/helpers/chat-page-meta-runtime.mjs"),"utf8");
  const once=(old,next)=>{assert.equal(helper.split(old).length-1,1);helper=helper.replace(old,next);};
  once("\nconst root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');\nexport const PAGE_META_BASE=",
    "\nconst root="+JSON.stringify(root)+";\nexport const PAGE_META_BASE=");
  once("window.__childLocale={renderHeader,",
    "window.__childLocale={renderDocumentHub,renderFeatureCatalog,renderFeatureFamily,renderRouteEngineBoundary,renderCapabilityHubFamilySummary,normalizeRouteEngineDescriptor,capabilityHubFamily,registeredFeatureFamilyEntries,customerCatalog,renderHeader,");
  return(await import("data:text/javascript;base64,"+Buffer.from(helper).toString("base64"))).pageMetaRenderer(sources);
}
