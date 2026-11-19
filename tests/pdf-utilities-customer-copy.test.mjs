// Physical-bundle unit QA only; never a native/provider/output proof.
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import {fileURLToPath} from "node:url";
import {execFileSync} from "node:child_process";
import {createHash} from "node:crypto";
import {imageEditCustomerHistoricalSource} from "./helpers/image-edit-customer-copy-snapshot.mjs";
const ROOT=path.resolve(path.dirname(fileURLToPath(import.meta.url)),"..");
const BASE="513557a9ece0f8fe049884868dc5fb3a1ac2339c",hash=x=>createHash("sha256").update(x).digest("hex"),count=(s,p)=>s.split(p).length-1;
const fixtureRaw=fs.readFileSync(path.join(ROOT,"tests/fixtures/pdf-utilities-customer-copy-reviewed.json"));
assert.equal(hash(fixtureRaw),"fb1ffa41f9d924a11caf78b840d5ebc2a8e6a270eb49e91838868def71973870","Pinned reviewed source authority");
const fixture=JSON.parse(fixtureRaw);
assert.equal(fixture.base,BASE);
assert.equal(fixture.task,"PDF-UTILITIES-CUSTOMER-COPY-20261119");
assert.equal(fixture.sourceAuthorities.length,3);
for(const authority of fixture.sourceAuthorities){
  assert.equal(authority.sourceProposalExact,true);
  assert.equal(authority.amendedSchemaValid,true);
}
let loader=fs.readFileSync(path.join(ROOT,"tests/helpers/chat-page-meta-runtime.mjs"),"utf8");
for(const[old,next]of [
  ["\nconst root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');","\nconst root="+JSON.stringify(ROOT)+";"],
  ["supportTicketHeroSection,resolvePage,safeText,withUiText:","supportTicketHeroSection,resolvePage,safeText,renderNotes,renderFields,imageToPdfFormFields,renderDocumentOperationCards,withUiText:"]
]){assert.equal(count(loader,old),1,"Exact test-local loader exposure");loader=loader.replace(old,()=>next);}
const{pageMetaSources,pageMetaRenderer}=await import("data:text/javascript;base64,"+Buffer.from(loader).toString("base64"));
const current=pageMetaSources(),files={portal:"static/portal/portal.js",i18n:"static/portal/portal-i18n.js",pages:"copyfast_pages.py"};
const baseline=Object.fromEntries(Object.entries(files).map(([key,file])=>[key,execFileSync("git",["show",BASE+":"+file],{cwd:ROOT,encoding:"utf8",maxBuffer:30e6}).replace(/\r\n/g,"\n")]));
assert.equal(fixture.canonicalChanges.length,4);
const phases=[],restored={...current};
for(const edit of fixture.canonicalChanges){
  const key=edit.file.endsWith("portal-i18n.js")?"i18n":"portal",source=restored[key];
  const next=count(source,edit.new),old=count(source,edit.old);
  assert.ok(next===1||(next===0&&old===1),"Exact old/new physical source slot");
  if(next){assert.equal(old,count(edit.new,edit.old));restored[key]=source.replace(edit.new,()=>edit.old);}
  phases.push(next);
}
assert.ok(phases.every(x=>x===0)||phases.every(x=>x===1),"No partial batch replay");
// Finite historical source comparator only; actual/before renderers below still receive full physical sources.
const sourceDigests=value=>Object.fromEntries(Object.entries(value).map(([key,source])=>[key,hash(imageEditCustomerHistoricalSource(source,files[key]))]));
assert.deepEqual(sourceDigests(restored),sourceDigests(baseline),"Complete physical source outside approved substitutions stays BASE-exact");
const actual=await pageMetaRenderer(current),before=await pageMetaRenderer(baseline);
const customer='CUSTOMER media provider CSRF Facebook TikTok <img src=x onerror="literal">&';
const ids=["11111111-1111-4111-8111-111111111111","22222222-2222-4222-8222-222222222222"];
const esc=s=>String(s).replace(/[&<>'"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"}[c]));
const plain=x=>JSON.parse(JSON.stringify(x));
function freeze(value){if(value&&typeof value==="object"&&!Object.isFrozen(value)){for(const x of Object.values(value))freeze(x);Object.freeze(value);}return value;}
function context(route,{view=true,run=true,refresh=true,size=2}={}){
  const asset=(id,kind)=>({id,display_name:customer,original_filename:customer+(kind==="pdf"?".pdf":".png"),state:"active",extension:kind==="pdf"?".pdf":".png",content_type:kind==="pdf"?"application/pdf":"image/png",byte_size:1024});
  return freeze({path:route,profile:{locale:"en"},capabilities:{"document-operation-view":view,"document-operation-refresh":refresh,"document-operation-pdf-optimize":run,"document-operation-image-to-pdf":run},
    imageToPdfEnabled:true,assetVaultReadState:"ready",documentOperationsReadState:"ready",documentAssetReferenceReadState:"ready",documentOperations:[],
    documentAssetReferences:{pdf:ids.slice(0,size).map(id=>asset(id,"pdf")),image:ids.slice(0,size).map(id=>asset(id,"image")),
      pdf_listing:{filters:{q:""},pagination:{offset:0,returned:size,has_more:false,previous_offset:null}},
      image_listing:{filters:{q:""},pagination:{offset:0,returned:size,has_more:false,previous_offset:null}}}});
}
function result(renderer,locale,route,settings){
  const raw=context(route,settings),saved=JSON.stringify(raw);let r;
  try{r=renderer(locale,route,raw);}catch(error){throw new Error((error.name+": "+error.message).slice(0,600));}
  assert.equal(JSON.stringify(raw),saved);return r;
}
const text=html=>html.replaceAll(esc(customer),"[CUSTOMER]").replace(/<[^>]*>/g," ");
const fieldsRows=fixture.fieldsRows,pageRows=fixture.pageRows;
const words=(rows,key,locale,position)=>rows.find(row=>row[0]===key)[["vi","en","zh"].indexOf(locale)+1].replaceAll("{position}",String(position));
const tags=html=>[...html.matchAll(/<(?:form|button|input|select|textarea|option|a)\b[^>]*>/g)].map(m=>m[0].replace(/data-portal-confirm="[^"]*"/,'data-portal-confirm="DECLARED_COPY"')).sort();
for(const locale of ["vi","en","zh"]){
  test(`${locale}: Nén PDF omits its real notes output without empty replacement`,()=>{
    const now=result(actual,locale,"/documents/compress"),old=result(before,locale,"/documents/compress"),notes=old.qa.renderNotes(old.page);
    assert.ok(notes.includes("portal-panel-list"));assert.ok(old.html.includes(notes));
    assert.equal(count(now.html,'class="portal-panel-list"'),0);assert.ok(!now.html.includes(notes));
    assert.equal(now.qa.renderNotes(now.page),notes,"Shared notes factory/config stays intact");
    assert.equal(now.html,old.html.replace("      "+notes+"\n",""),"Entire HTML except final real notes line held");
    assert.deepEqual(tags(now.html),tags(old.html));
  });
  test(`${locale}: eight image fields use actual locale labels/help and preserve fixed field contracts`,()=>{
    const now=result(actual,locale,"/documents/image-to-pdf"),old=result(before,locale,"/documents/image-to-pdf");
    const a=plain(now.qa.imageToPdfFormFields()),b=plain(old.qa.imageToPdfFormFields());assert.equal(a.length,8);
    for(let index=0;index<8;index++){
      const position=index+1,first=index===0,field=a[index],prior=b[index];
      assert.equal(field.label,words(fieldsRows,first?"docImageToPdfFieldLabel":"docImageToPdfFieldOptionalLabel",locale,position));
      assert.equal(field.emptyLabel,words(fieldsRows,first?"docImageToPdfFieldFirstEmpty":"docImageToPdfFieldOptionalEmpty",locale,position));
      assert.equal(field.help,words(fieldsRows,first?"docImageToPdfFieldFirstHelp":"docImageToPdfFieldOptionalHelp",locale,position));
      for(const key of ["label","emptyLabel","help"]){delete field[key];delete prior[key];}
      assert.deepEqual(field,prior);assert.equal(field.name,"source_asset_id_"+position);assert.equal(field.required,first);
    }
  });
  test(`${locale}: image-to-PDF presents only useful form/history with translated plain copy`,()=>{
    const r=result(actual,locale,"/documents/image-to-pdf"),visible=text(r.html);
    for(const row of pageRows.filter(row=>row[0]!=="docImageToPdfReadyUiChooseSource"))assert.ok(r.html.includes(esc(words(pageRows,row[0],locale))),row[0]);
    assert.ok(result(actual,locale,"/documents/image-to-pdf",{size:0}).html.includes(esc(words(pageRows,"docImageToPdfReadyUiChooseSource",locale))));
    assert.doesNotMatch(r.html,/<aside\b|class="portal-document-operation-intro"|class="portal-panel-list"|portal-notice/);
    assert.ok(r.html.includes("portal-document-operation-layout--single"));
    const form=r.html.match(/<form\b[\s\S]*?<\/form>/)?.[0];assert.ok(form);
    assert.equal(count(r.html,'href="/asset-vault"'),1);assert.ok(form.includes('href="/asset-vault"'));
    assert.equal(count(form,"<select "),8);
    assert.doesNotMatch(visible,/\b(?:signed|ownership|hash-copy|Web-native|Browser|Asset Vault|parser|provider|server-side|lossless|Slot)\b|Trạng thái tích hợp|Nguyên tắc an toàn/);
    assert.ok(r.html.includes(esc(customer)));assert.ok(!r.html.includes("<img src=x"));
  });
  test(`${locale}: strict rights/source thresholds and complete retained controls remain protected`,()=>{
    for(const route of ["/documents/compress","/documents/image-to-pdf"])for(const view of [true,false,"true"])for(const run of [true,false,"true"])for(const refresh of [true,false])for(const size of [0,2]){
      const settings={view,run,refresh,size},now=result(actual,locale,route,settings),old=result(before,locale,route,settings);
      assert.deepEqual(tags(now.html),tags(old.html),"Control attributes retained apart from declared confirmation copy");
      if(view!==true){assert.equal(now.html,old.html);assert.ok(!now.html.includes("<form"));continue;}
      const submit=now.html.match(/<button\b[^>]*type="submit"[^>]*>/)[0];
      assert.equal(submit.includes(" disabled"),run!==true||size===0);
      const update=now.html.match(/<button\b[^>]*data-portal-action="document-operation-refresh"[^>]*>/)[0];
      assert.equal(update.includes(" disabled"),!refresh);
      assert.equal(now.title,old.title);
      if(route==="/documents/image-to-pdf"){
        const a=now.html.match(/data-portal-confirm="([^"]*)"/)[1],b=old.html.match(/data-portal-confirm="([^"]*)"/)[1];
        assert.equal(count(now.attributes,a),1);assert.equal(count(old.attributes,b),1);
        assert.equal(now.attributes.replace(a,"DECLARED_CONFIRM"),old.attributes.replace(b,"DECLARED_CONFIRM"));
      }else assert.equal(now.attributes,old.attributes);
      assert.equal(JSON.stringify(now.context),JSON.stringify(old.context));
      const cards=now.qa.renderDocumentOperationCards([],now.context);
      assert.equal(cards,old.qa.renderDocumentOperationCards([],old.context),"Shared history-card renderer unchanged");
    }
  });
}
test("physical source scope is exact and no unrelated routes/catalog bytes change",()=>{
  assert.equal(phases.length,4);assert.deepEqual(sourceDigests(restored),sourceDigests(baseline));
  for(const route of ["/documents/split","/documents/merge","/image/resize","/image/history"])for(const locale of ["vi","en","zh"]){
    const now=result(actual,locale,route),old=result(before,locale,route);
    assert.equal(now.html,old.html);assert.equal(now.title,old.title);assert.equal(JSON.stringify(now.context),JSON.stringify(old.context));
  }
});
test("new messages initialize before catalog freeze with equal keysets and immutable dictionaries",()=>{
  const r=result(actual,"vi","/documents/image-to-pdf"),keys=[...fieldsRows,...pageRows].map(row=>row[0]);
  assert.equal(keys.length,15);
  for(const locale of ["vi","en","zh"]){
    assert.equal(Object.isFrozen(r.messages[locale]),true);
    for(const key of keys)assert.equal(typeof r.messages[locale][key],"string");
  }
  assert.deepEqual(Object.keys(r.messages.vi).sort(),Object.keys(r.messages.en).sort());
  assert.deepEqual(Object.keys(r.messages.vi).sort(),Object.keys(r.messages.zh).sort());
});
