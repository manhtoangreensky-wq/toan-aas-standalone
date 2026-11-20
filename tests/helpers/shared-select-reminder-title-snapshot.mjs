import fs from "node:fs";
import assert from "node:assert/strict";
import {createHash} from "node:crypto";
import {vaultProjectOptionsHistoricalSource} from "./vault-project-options-snapshot.mjs";
const raw=fs.readFileSync(new URL("../fixtures/shared-select-reminder-title-reviewed.json",import.meta.url));
const fail="Unreviewed Shared select reminder title",hash=x=>createHash("sha256").update(x).digest("hex"),count=(s,p)=>s.split(p).length-1;
assert.equal(hash(raw),"66d8d0d6bdf45c9bb59c8c3e3095bb67f1de44933ef73c260a31094045840132",fail);
const fixture=JSON.parse(raw),edit=fixture.canonicalChanges[0];
assert.equal(fixture.base,"46423a6df9af67ac7ccabd88686d4cb42523a078");
assert.equal(fixture.parentFixtureRawSha256,"7cb67db3464cb45d3e0b243f388affb981fd4f5780e0ebb28105865885786817");
assert.equal(fixture.canonicalChanges.length,1);assert.equal(edit.file,"static/portal/portal.js");assert.equal(edit.count,1);
assert.equal(edit.new,edit.old+'\n    if (path === "/reminders") return uiText("shellNav.reminders", fallback);');
const owner="  function localizedPageTitle(page, context) {",next="  function documentTitle(page, context) {";
export function sharedSelectReminderTitleHistoricalSource(source,file){
 assert.equal(typeof source,"string",fail);
 source=vaultProjectOptionsHistoricalSource(source,file);
 if(file!==edit.file)return source;
 if(!source.includes(owner)&&!source.includes(edit.new)&&!source.includes('if (path === "/reminders") return uiText("shellNav.reminders"'))return source;
 assert.equal(count(source,owner),1,fail+" owner");assert.equal(count(source,next),1,fail+" next");
 const start=source.indexOf(owner),end=source.indexOf(next,start);
 assert.ok(end>start,fail+" order");
 const body=source.slice(start,end);
 if(!body.includes('"/reminders"')){
  assert.equal(count(source,edit.new),0,fail+" detached");return source;
 }
 assert.equal(count(source,edit.new),1,fail+" exact prefix");assert.equal(source.indexOf(edit.new),start,fail+" placement");
 assert.equal(count(body,'"/reminders"'),1,fail+" duplicate route");
 return source.replace(edit.new,()=>edit.old);
}
