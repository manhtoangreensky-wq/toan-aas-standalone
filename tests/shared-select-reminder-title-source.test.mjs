import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import {fileURLToPath} from "node:url";
import {execFileSync} from "node:child_process";
import {createHash} from "node:crypto";
import {sharedSelectReminderTitleHistoricalSource as inverse} from "./helpers/shared-select-reminder-title-snapshot.mjs";
const ROOT=path.resolve(path.dirname(fileURLToPath(import.meta.url)),"..");
const raw=fs.readFileSync(new URL("./fixtures/shared-select-reminder-title-reviewed.json",import.meta.url)),fixture=JSON.parse(raw);
const parentRaw=fs.readFileSync(new URL("./fixtures/shared-select-labels-reviewed.json",import.meta.url)),parent=JSON.parse(parentRaw);
const hash=x=>createHash("sha256").update(x).digest("hex"),lf=s=>s.replace(/\r\n/g,"\n"),file="static/portal/portal.js",edit=fixture.canonicalChanges[0];
const physical=lf(fs.readFileSync(path.join(ROOT,file),"utf8"));
let parentSource=lf(execFileSync("git",["show",fixture.base+":"+file],{cwd:ROOT,encoding:"utf8",maxBuffer:12e6}));
for(const row of parent.canonicalChanges.filter(row=>row.file===file)){assert.equal(parentSource.split(row.old).length-1,1);parentSource=parentSource.replace(row.old,()=>row.new);}
const candidate=parentSource.replace(edit.old,()=>edit.new),fail=/Unreviewed Shared select reminder title/;
test("title authority and complete physical source bind the parent four edits plus one reviewed route branch",()=>{
 assert.equal(hash(raw),"66d8d0d6bdf45c9bb59c8c3e3095bb67f1de44933ef73c260a31094045840132");
 assert.equal(hash(parentRaw),fixture.parentFixtureRawSha256);
 assert.equal(fixture.task,"SHARED-SELECT-REMINDER-TITLE-20261120");
 assert.equal(fixture.canonicalChanges.length,1);assert.equal(edit.count,1);assert.equal(edit.file,file);
 assert.equal(fixture.sourceAuthority.resultRawSha256,"a841185c402cfb94e9809c008acfb4aa27eb0a3fd218c0328fa90bd22d75e5b1");
 assert.equal(fixture.sourceAuthority.proposalDecodedExact,false);assert.equal(fixture.sourceAuthority.applicationReplayExact,true);
 assert.equal(fixture.sourceAuthority.terminalNewlinePairOnly,true);assert.equal(fixture.sourceAuthority.workerCodeFailures,0);
 assert.equal(physical,candidate);assert.equal(inverse(physical,file),parentSource);
 assert.equal(parentSource.replace(edit.old+"\n",()=>edit.new+"\n"),candidate,"Decoded worker newline-pair replays exact bytes");
 for(const pin of fixture.applicationBaseline){
  const actual=lf(fs.readFileSync(path.join(ROOT,pin.file),"utf8"));
  assert.equal(hash(actual),pin.candidateLfSha256,pin.file);
  assert.equal(hash(inverse(actual,pin.file)),pin.parentCandidateLfSha256,pin.file);
 }
 assert.equal(fixture.applicationBaseline.length,151);assert.equal(fixture.applicationBaseline.filter(p=>p.titleChanged).length,1);
 assert.equal(fixture.applicationBaseline.filter(p=>p.changed).length,2);
});
test("title historical projection is finite idempotent and leaves all outside customer bytes untouched",()=>{
 assert.equal(inverse(parentSource,file),parentSource);assert.equal(inverse(inverse(physical,file),file),parentSource);
 const prefix="/* Facebook TikTok <img>& */\n",suffix='\nconst customer="literal";';
 assert.equal(inverse(prefix+physical+suffix,file),prefix+parentSource+suffix);
 assert.equal(inverse(physical,"customer/unrelated.txt"),physical);
 for(const malformed of [
  physical.replace(edit.new,edit.new.replace("shellNav.reminders","shellNav.UNKNOWN")),
  physical+"\n"+edit.new,
  physical.replace(edit.new,"")+"\n"+edit.new,
  physical.replace(edit.new,edit.new+'\n    if (path === "/reminders") return "DUPLICATE";'),
  physical.replace("  function documentTitle(","  function UNKNOWN_DOCUMENT_TITLE(")
 ])assert.throws(()=>inverse(malformed,file),fail);
 for(const value of [null,undefined,1,{},[]])assert.throws(()=>inverse(value,file),fail);
});
