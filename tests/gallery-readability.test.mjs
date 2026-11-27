import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import {createHash} from "node:crypto";
import {execFileSync} from "node:child_process";
import {physicalGallerySources,galleryRendererFromSources,galleryContext} from "./helpers/gallery-customer-copy-render.mjs";
const fixtureRaw=fs.readFileSync(new URL("./fixtures/gallery-readability.json",import.meta.url),"utf8").replace(/\r\n/g,"\n");
assert.equal(createHash("sha256").update(fixtureRaw).digest("hex"),"3cfbd7b2618e05a11d91179d0b12d6be37d911e2d85ad495738defb0e00ab68f");
const fix=JSON.parse(fixtureRaw);
const source=physicalGallerySources(),render=await galleryRendererFromSources(source);
const hash=value=>createHash("sha256").update(value).digest("hex");
const cssFile="static/portal/portal-theme.css",portalFile="static/portal/portal.js";
const css=fs.readFileSync(cssFile,"utf8").replace(/\r\n/g,"\n");
const baseCss=execFileSync("git",["show",fix.base_sha+":"+cssFile],{encoding:"utf8",maxBuffer:8e6}).replace(/\r\n/g,"\n");
const addition="\n"+fix.cssMarker+"\n"+fix.cssRules.join("\n")+"\n";
const prior=JSON.parse(fs.readFileSync(new URL("./fixtures/gallery-customer-copy.json",import.meta.url),"utf8"));
test("raw Gallery CSS changes no existing byte or other route rule",()=>{
  assert.equal(hash(baseCss),fix.cssBeforeLfSha256);
  assert.equal(css===baseCss+addition,true,"Only the reviewed Gallery-specific rules may be appended");
});
test("raw Gallery source changes only the approved counts condition after GPC",()=>{
  let expected=execFileSync("git",["show",fix.base_sha+":"+portalFile],{encoding:"utf8",maxBuffer:12e6}).replace(/\r\n/g,"\n");
  for(const row of prior.records.filter(row=>row.file===portalFile)){
    assert.equal(expected.split(row.old).length-1,1);expected=expected.replace(row.old,()=>row.new);
  }
  assert.equal(hash(expected),fix.portalBeforeLfSha256);
  assert.equal(expected.split(fix.portalRecord.old).length-1,1);
  expected=expected.replace(fix.portalRecord.old,()=>fix.portalRecord.new);
  assert.equal(source[portalFile]===expected,true,"Unknown application edits must not be hidden");
});
for(const locale of["vi","en","zh"]){
  for(const state of["guarded","unloaded","denied-valid","malformed"])test(`Gallery ${locale}/${state} never represents an unknown catalog with zero metric tiles`,()=>{
    const raw=galleryContext("list");
    if(state==="guarded")raw.capabilities["free-prompt-gallery-view"]=false;
    if(state==="unloaded")raw.freePromptGalleryCatalog={};
    if(state==="denied-valid")raw.capabilities["free-prompt-gallery-view"]=false;
    if(state==="malformed")raw.freePromptGalleryCatalog={snapshot_version:"",categories:[],industries:[]};
    const value=render(locale,"/free-prompt-gallery",raw);
    const intro=value.html.match(/<section class="portal-content-prompt-pack-intro">([\s\S]*?)<\/section>/);
    assert(intro,"Real intro must remain, not the entire page hidden");
    assert.doesNotMatch(intro[1],/<dl>|<dt>|<dd>/,"No counts before readable catalog");
    assert.match(value.html,/<h1\b/,"The useful page remains visible");
  });
  for(const state of["empty","list","detail","saved"])test(`Gallery ${locale}/${state} keeps real category and industry counts when browsing is allowed`,()=>{
    const raw=galleryContext(state),value=render(locale,"/free-prompt-gallery",raw);
    const intro=value.html.match(/<section class="portal-content-prompt-pack-intro">([\s\S]*?)<\/section>/);
    assert(intro);assert.equal((intro[1].match(/<dt>1<\/dt>/g)||[]).length,2);
    assert.equal((intro[1].match(/<dd>/g)||[]).length,2);
    if(state==="empty")assert.equal(value.context.freePromptGalleryListing.items.length,0);
  });
}
// Actual cascade, contrast, focus, targets, mobile sizing and layout are measured
// by the real-CSS HTTP browser gate, not inferred from these finite source guards.
