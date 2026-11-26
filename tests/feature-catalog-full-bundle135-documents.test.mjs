import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import {fileURLToPath} from "node:url";
import {createHash} from "node:crypto";
import {execFileSync} from "node:child_process";
import {fullBundleI18n,fullBundleConsumer} from "./helpers/feature-catalog-full-bundle135-render.mjs";

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),"..");
const read=file=>fs.readFileSync(path.join(root,file),"utf8").replace(/\r\n/g,"\n");
const fixture=JSON.parse(read("tests/fixtures/feature-catalog-full-bundle135.json"));
const canonicalRaw=read(fixture.canonicalFixture);
assert.equal(createHash("sha256").update(canonicalRaw).digest("hex"),fixture.canonicalFixtureLfSha256);
const canonical=JSON.parse(canonicalRaw).copy;
// The optional switch is set only in an isolated QA child to demonstrate RED
// against the frozen BASE. Normal CI always reads the physical current source.
const source=process.env.FBC135_DOCUMENTS_QA_BASE==="1"
  ?execFileSync("git",["show",fixture.base_sha+":"+fixture.applicationFile],{cwd:root,encoding:"utf8",maxBuffer:10e6})
  :read(fixture.applicationFile);
const api=fullBundleI18n(source);
const{pageDescription}=fullBundleConsumer(read("static/portal/portal.js"),api,fixture.entries);

for(const locale of["vi","en","zh"])test(`documents page consumes the reviewed shared description: ${locale}`,()=>{
  api.setLocale(locale,{emit:false});
  for(const page of[
    {routePath:"/documents",description:"Owner page description must not replace the localized UI"},
    {path:"/documents",description:"Owner page description must not replace the localized UI"}
  ]){
    const before=JSON.stringify(page);
    assert.equal(pageDescription(page),canonical[locale].documents.description);
    assert.equal(JSON.stringify(page),before);
  }
});
