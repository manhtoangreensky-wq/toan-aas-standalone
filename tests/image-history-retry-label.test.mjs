import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import {createHash} from "node:crypto";
import {pathToFileURL,fileURLToPath} from "node:url";
const ROOT=fileURLToPath(new URL("..",import.meta.url)).replace(/[\\/]$/,"");
const AUTHORITY=new URL("./fixtures/image-history-retry-label-reviewed.json",import.meta.url);
const raw=fs.readFileSync(AUTHORITY),authority=JSON.parse(raw),edit=authority.proposal.changes[0],sha=value=>createHash("sha256").update(value).digest("hex"),count=(source,part)=>source.split(part).length-1;
const {pageMetaSources,pageMetaRenderer}=await import(pathToFileURL(ROOT+"/tests/helpers/chat-page-meta-runtime.mjs").href);
const {resizeReadyContext}=await import(pathToFileURL(ROOT+"/tests/helpers/image-resize-guidance-runtime.mjs").href);
function inverse(source){const old=count(source,edit.old),next=count(source,edit.new);assert.ok(old===1&&next===0||old===0&&next===1,"Exact one-row History retry phase");return next?source.replace(edit.new,()=>edit.old):source;}
const sources=pageMetaSources(),prior={...sources,i18n:inverse(sources.i18n)},render=await pageMetaRenderer(sources),before=await pageMetaRenderer(prior);
const LABEL={vi:"Thử lại",en:"Try again",zh:"重试"},ROUTE="/image/history",CUSTOMER='CUSTOMER Retry private data Thử lại 重试 Facebook TikTok <img src=x onerror="literal">&';
const frozen=value=>{if(value&&typeof value==="object"&&!Object.isFrozen(value)){Object.values(value).forEach(frozen);Object.freeze(value);}return value;};
function context(state="failed",refresh=true){
  const value=resizeReadyContext();value.profile={locale:"en",displayName:CUSTOMER};
  value.capabilities["image-operation-view"]=state!=="guarded";value.capabilities["image-operation-refresh"]=refresh;
  value.imageHistoryReadState=state==="guarded"?"ready":state;value.imageHistoryOperations=[];return value;
}
function result(renderer,locale,state="failed",refresh=true){
  const value=frozen(context(state,refresh)),saved=JSON.stringify(value),output=renderer(locale,ROUTE,value);assert.equal(JSON.stringify(value),saved);return output;
}
function button(html){const matches=[...html.matchAll(/(<button\b[^>]*data-portal-action="image-history-refresh"[^>]*>)([^<]*)(<\/button>)/g)];assert.equal(matches.length,1);return matches[0];}
function restoreLabel(html,oldHtml){const next=button(html),old=button(oldHtml),start=next.index+next[1].length;assert.equal(next[1],old[1]);return html.slice(0,start)+old[2]+html.slice(start+next[2].length);}
for(const locale of ["vi","en","zh"]){
  test(`${locale}: failed History has concise retry label with exact live action and permission`,()=>{
    const output=result(render,locale),node=button(output.html);assert.equal(node[2],LABEL[locale]);
    assert.ok(node[1].includes('type="button"'));assert.ok(node[1].includes('data-portal-route="/image/history"'));assert.equal(/\bdisabled\b/.test(node[1]),false);
  });
  test(`${locale}: only retry text changes; guarded/loading/ready/no-refresh and all outside HTML/context remain identical`,()=>{
    const now=result(render,locale),old=result(before,locale);assert.equal(restoreLabel(now.html,old.html),old.html);
    assert.equal(JSON.stringify(now.context),JSON.stringify(old.context));assert.equal(now.title,old.title);assert.equal(now.attributes,old.attributes);assert.equal(now.qa.renderHeader(now.page,now.context),old.qa.renderHeader(old.page,old.context));
    for(const[state,refresh]of [["guarded",true],["loading",true],["ready",true],["failed",false]]){
      const current=result(render,locale,state,refresh),previous=result(before,locale,state,refresh);assert.equal(current.html,previous.html);assert.equal(JSON.stringify(current.context),JSON.stringify(previous.context));
      if(state!=="ready")assert.equal([...current.html.matchAll(/data-portal-action="image-history-refresh"/g)].length,0);
    }
  });
}
test("same physical History VM changes retry text VI -> EN -> ZH -> VI without changing context",()=>{
  const output=result(render,"vi"),saved=JSON.stringify(output.context);frozen(output.context);
  for(const locale of ["vi","en","zh","vi"]){output.setLocale(locale);assert.equal(button(output.qa.renderPage(output.page,output.context))[2],LABEL[locale]);assert.equal(JSON.stringify(output.context),saved);}
});
test("authority pins exact single i18n row and three independent retry literals",()=>{
  assert.equal(sha(raw),"48164df192a9a685a32159fc1819da97598be44f73ca48a2eb61b6f8d4ebcb6a");assert.equal(authority.review.schemaValid,true);assert.equal(authority.review.proposalExact,true);
  assert.equal(authority.review.conversation,"d524969c-a91f-409f-bc14-730f13405a9b");assert.equal(authority.proposal.specId,"IMAGE-HISTORY-RETRY-LABEL-20261119");assert.equal(authority.proposal.revision,"R1");assert.equal(authority.proposal.changes.length,1);assert.equal(edit.file,"static/portal/portal-i18n.js");assert.equal(edit.count,1);
  assert.deepEqual(JSON.parse(edit.new.trim().replace(/,$/,"")),["history.retry","Thử lại","Try again","重试"]);
});
test("one-row inverse rejects missing/duplicate/unknown rows and preserves every outside byte",()=>{
  const outside="/* CUSTOMER Retry private data Facebook TikTok */\r\n";assert.equal(inverse(outside+edit.new+"\nTAIL"),outside+edit.old+"\nTAIL");
  assert.equal(inverse(edit.old),edit.old);assert.throws(()=>inverse("UNKNOWN"),/retry phase/);assert.throws(()=>inverse(edit.new+"\n"+edit.new),/retry phase/);
});
