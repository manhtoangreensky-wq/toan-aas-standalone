import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import {execFileSync} from "node:child_process";
import {fileURLToPath,pathToFileURL} from "node:url";
import {pdfInputFont16HistoricalCss} from "./pdf-input-font16-snapshot.mjs";
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),"../..");
const fixture=JSON.parse(fs.readFileSync(new URL("../fixtures/pdf-customer-cleanup-reviewed.json",import.meta.url),"utf8"));
const files={portal:"static/portal/portal.js",i18n:"static/portal/portal-i18n.js",theme:"static/portal/portal-theme.css"};
export function pdfCustomerCleanupSources(historical=false){
  assert.match(fixture.base,/^[a-f0-9]{40}$/,"Bind the verified full 40-hex customer-cleanup BASE before git");
  return Object.fromEntries(Object.entries(files).map(([key,file])=>{
    const value=(historical
    ?execFileSync("git",["show",fixture.base+":"+file],{cwd:root,encoding:"utf8",maxBuffer:30e6})
    :fs.readFileSync(path.join(root,file),"utf8")).replace(/\r\n/g,"\n");
    return [key,key==="theme"?pdfInputFont16HistoricalCss(value):value];
  }));
}
export async function pdfCustomerCleanupRenderer(sources){
  assert.equal(typeof sources?.portal,"string");assert.equal(typeof sources?.i18n,"string");
  const folder=path.join(root,"tests/helpers");
  let helper=fs.readFileSync(path.join(folder,"document-pdf-ui-runtime.mjs"),"utf8");
  const once=(old,next)=>{assert.equal(helper.split(old).length-1,1,"Exact existing complete renderer exposure");helper=helper.replace(old,()=>next);};
  once("\nconst root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');\nexport const DOCUMENT_PDF_BASE=",
    "\nconst root="+JSON.stringify(root)+";\nexport const DOCUMENT_PDF_BASE=");
  once("window.__childLocale={renderDocumentOperationHistoryPagination,",
    "window.__childLocale={renderOperationAssetReferencePagination,renderOperationAssetReferencePicker,imageOperationText,operationAssetReferenceListing,documentAssetReferenceListing,imageOperationAssetReferenceListing,normalizeDocumentAssetReferences,normalizeImageOperationAssetReferences,pdfMergeFormFields,renderDocumentOperationHistoryPagination,");
  helper=helper.replace(/from (['"])(\.\/[^'"]+)\1/g,(_,quote,file)=>"from "+JSON.stringify(pathToFileURL(path.join(folder,file)).href));
  const module=await import("data:text/javascript;base64,"+Buffer.from(helper).toString("base64"));
  // Explicit full sources only: never call historical projections for the actual behavior under test.
  return module.documentPdfRenderer({portal:sources.portal,i18n:sources.i18n});
}
