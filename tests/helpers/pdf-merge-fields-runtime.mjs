import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import {execFileSync} from "node:child_process";
import {fileURLToPath} from "node:url";
import {pdfCustomerCleanupRenderer} from "./pdf-customer-cleanup-runtime.mjs";
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),"../..");
const fixture=JSON.parse(fs.readFileSync(new URL("../fixtures/pdf-merge-fields-reviewed.json",import.meta.url),"utf8"));
const files={portal:"static/portal/portal.js",i18n:"static/portal/portal-i18n.js",theme:"static/portal/portal-theme.css"};
export function pdfMergeFieldsSources(historical=false){
  assert.match(fixture.base,/^[a-f0-9]{40}$/,"Bind actual delivered full 40-hex PDF Merge fields BASE before git");
  return Object.fromEntries(Object.entries(files).map(([key,file])=>[key,(historical
    ?execFileSync("git",["show",fixture.base+":"+file],{cwd:root,encoding:"utf8",maxBuffer:30e6})
    :fs.readFileSync(path.join(root,file),"utf8")).replace(/\r\n/g,"\n")]));
}
export async function pdfMergeFieldsRenderer(sources){
  assert.equal(typeof sources?.portal,"string");assert.equal(typeof sources?.i18n,"string");
  return pdfCustomerCleanupRenderer({portal:sources.portal,i18n:sources.i18n});
}
