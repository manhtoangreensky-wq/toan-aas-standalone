import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import {execFileSync} from "node:child_process";
import {fileURLToPath} from "node:url";
import {documentPdfRenderer} from "./document-pdf-ui-runtime.mjs";
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),"../..");
const fixture=JSON.parse(fs.readFileSync(new URL("../fixtures/pdf-usability-reviewed.json",import.meta.url),"utf8"));
const files={portal:"static/portal/portal.js",i18n:"static/portal/portal-i18n.js",theme:"static/portal/portal-theme.css"};
export function pdfUsabilitySources(historical=false){
  // Validate before the first git invocation. Never accept a branch/ref or a guessed delivery revision.
  assert.match(fixture.base,/^[a-f0-9]{40}$/,"Bind the verified full 40-hex PDF usability delivery BASE");
  return Object.fromEntries(Object.entries(files).map(([key,file])=>[key,(historical
    ?execFileSync("git",["show",fixture.base+":"+file],{cwd:root,encoding:"utf8",maxBuffer:30e6})
    :fs.readFileSync(path.join(root,file),"utf8")).replace(/\r\n/g,"\n")]));
}
export async function pdfUsabilityRenderer(sources){
  assert.equal(typeof sources?.portal,"string","Supply the complete raw portal source explicitly");
  assert.equal(typeof sources?.i18n,"string","Supply the complete raw i18n source explicitly");
  // Do not invoke any historical projection here: this renderer must consume the full current bundle.
  return documentPdfRenderer({portal:sources.portal,i18n:sources.i18n});
}
