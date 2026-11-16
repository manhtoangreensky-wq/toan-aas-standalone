import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import {createHash} from "node:crypto";
import {pdfCustomerCleanupSources,pdfCustomerCleanupRenderer} from "./helpers/pdf-customer-cleanup-runtime.mjs";
import {pdfCustomerCleanupHistoricalPortalSource as portalBack,pdfCustomerCleanupHistoricalI18nSource as i18nBack,pdfCustomerCleanupHistoricalSnapshot as catalogBack,pdfCustomerCleanupHistoricalCss as cssBack,PDF_CUSTOMER_CLEANUP_READY_CSS_PREFIX as readyCss,PDF_CUSTOMER_CLEANUP_REFERENCE_CSS_PREFIX as referenceCss} from "./helpers/pdf-customer-cleanup-snapshot.mjs";
const fixture=JSON.parse(fs.readFileSync(new URL("./fixtures/pdf-customer-cleanup-reviewed.json",import.meta.url),"utf8"));
const source=pdfCustomerCleanupSources(),baseline=pdfCustomerCleanupSources(true),actual=await pdfCustomerCleanupRenderer(source),before=await pdfCustomerCleanupRenderer(baseline);
const locales=["vi","en","zh"],strict=[true,false,"true",undefined],keys=Object.keys(fixture.vi),refEdits=fixture.changes.slice(-11),amendments=fixture.changes.slice(8,-11);
const tools=[["renderPdfSplit","/documents/split","split","Split","pdfSplitFormFields",1],["renderPdfMerge","/documents/merge","merge","Merge","pdfMergeFormFields",2],["renderPdfOptimize","/documents/compress","optimize","Optimize","pdfOptimizeFormFields",1]];
const customer='CUSTOMER media Bot provider CSRF Facebook TikTok <img src=x onerror="alert(1)">&.pdf',note='CUSTOMER media Bot PayOS Asset Vault Facebook TikTok <script>"&\'</script>';
const ids=["11111111-1111-4111-8111-111111111111","22222222-2222-4222-8222-222222222222"];
const hash=value=>createHash("sha256").update(value).digest("hex"),plain=value=>JSON.parse(JSON.stringify(value)),count=(value,part)=>value.split(part).length-1;
const esc=value=>String(value).replace(/[&<>'"]/g,char=>({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"}[char]));
const freeze=value=>{if(value&&typeof value==="object"&&!Object.isFrozen(value)){Object.values(value).forEach(freeze);Object.freeze(value);}return value;};
const format=(value,params={})=>String(value).replace(/\{([^}]+)\}/g,(token,key)=>Object.hasOwn(params,key)?String(params[key]):token);
const controls=html=>[...html.matchAll(/<(?:form|button|input|select|textarea|option|a)\b[^>]*>/g)].map(match=>match[0]);
function once(value,old,next){assert.equal(count(value,old),1,"Finite reviewed slot must occur exactly once");return value.replace(old,()=>next);}
function safe(html){assert.equal(html.includes("<img"),false);assert.equal(html.includes("<script>"),false);assert.equal(html.includes("&amp;lt;"),false);}
function readOnly(data,run){const saved=JSON.stringify(data),result=run();assert.equal(JSON.stringify(data),saved,"Raw input/context/page/records must remain immutable");return result;}
function asset(id,kind="pdf"){return {id,display_name:customer,original_filename:customer,state:"active",extension:kind==="pdf"?".pdf":".png",content_type:kind==="pdf"?"application/pdf":"image/png",byte_size:1024};}
function context(session,route,view,run,refresh,size=2){
  const raw=freeze({path:route,capabilities:{"document-operation-view":view,"document-operation-refresh":refresh,"document-operation-pdf-split":run,"document-operation-pdf-merge":run,"document-operation-pdf-optimize":run},
    documentAssetReferences:{pdf:ids.slice(0,size).map(id=>asset(id)),pdf_listing:{filters:{q:customer},pagination:{offset:50,returned:size,previous_offset:0,has_more:false}}},
    documentAssetReferenceReadState:"ready",documentOperations:[]});
  return freeze({raw,page:{...session.qa.resolvePage(route),notes:[note]},context:{...session.context,...raw}});
}
const render=(s,name,data)=>readOnly(data,()=>s.qa[name](data.page,data.context));
function navBack(a,b){
  if(!b){assert.equal(a,"");return a;}assert.deepEqual(controls(a),controls(b));
  const open=html=>html.match(/^<nav class="portal-vault-pagination portal-operation-reference-pagination" aria-label="[^"]*">/)?.[0];
  const x=open(a),y=open(b);assert.ok(x&&y);assert.equal(x.replace(/aria-label="[^"]*"/,'aria-label=""'),y.replace(/aria-label="[^"]*"/,'aria-label=""'));
  let value=once(a,x,y),caption=html=>html.match(/^<nav[^>]*>(<span>[\s\S]*?<\/span>)?<div>/)?.[1]||"";
  const current=caption(value),prior=caption(b);value=current?once(value,current,prior):once(value,y,y+prior);
  assert.equal(value,b,"Only the nav aria text/range caption may differ; offsets and buttons stay exact");return value;
}
function pickerBack(a,b){
  assert.deepEqual(controls(a),controls(b));
  const copy=html=>html.match(/<div class="portal-operation-reference-copy"><strong>([\s\S]*?)<\/strong><span>([\s\S]*?)<\/span><\/div>/);
  const x=copy(a),y=copy(b);assert.ok(x&&y);let value=once(a,"<strong>"+x[1]+"</strong>","<strong>"+y[1]+"</strong>");
  value=once(value,"<span>"+x[2]+"</span>","<span>"+y[2]+"</span>");
  const nav=html=>html.match(/<nav class="portal-vault-pagination portal-operation-reference-pagination"[\s\S]*?<\/nav>/)?.[0]||"";
  const current=nav(value),prior=nav(b);if(current)value=once(value,current,navBack(current,prior));else assert.equal(prior,"");
  assert.equal(value,b,"Only known title/status/nav copy slots can differ, never the picker body");return value;
}
function fieldsBack(a,b){
  const blocks=html=>[...html.matchAll(/<section class="portal-operation-reference-picker"[\s\S]*?<\/section>/g)].map(match=>match[0]);
  const x=blocks(a),y=blocks(b);assert.equal(x.length,y.length);let value=a;
  for(let index=0;index<x.length;index++)value=once(value,x[index],pickerBack(x[index],y[index]));return value;
}
const refText={
  vi:{title:"Tìm {type} trong kho tệp",loading:"Đang tải tệp…",failed:"Chưa tải được tệp. Hãy bấm Tìm để tải lại.",aria:"Trang tệp",label:"Tệp",image:"ảnh JPEG, PNG hoặc WebP"},
  en:{title:"Find {type} in your files",loading:"Loading files…",failed:"Files could not be loaded. Select Find to reload.",aria:"File pages",label:"Files",image:"JPEG, PNG or WebP images"},
  zh:{title:"在文件库中查找{type}",loading:"正在加载文件…",failed:"无法加载文件，请点击“查找”重新加载。",aria:"文件分页",label:"文件",image:"JPEG、PNG 或 WebP 图像"}
};
const paginationCases=[
  [{offset:0,returned:0,previous_offset:null,has_more:false,next_offset:null},null,[]],
  [{offset:0,returned:2,previous_offset:null,has_more:true,next_offset:50},[1,2],["50"]],
  [{offset:50,returned:0,previous_offset:0,has_more:false,next_offset:null},null,["0"]],
  [{offset:50,returned:2,previous_offset:0,has_more:true,next_offset:100},[51,52],["0","100"]],
  [{offset:"50",returned:"2",previous_offset:"0",has_more:"true",next_offset:"100"},null,[]]
];
for(const locale of locales){
  const now=actual(locale,"/documents/split",{}),old=before(locale,"/documents/split",{}),copy=fixture[locale],text=refText[locale];
  test(`${locale}: actual three PDF pages retain strict independent rights, controls, source thresholds, customer names and notes`,()=>{
    for(const [name,route,kind,prefix,factory,minimum]of tools)for(const view of strict)for(const run of strict)for(const refresh of strict)for(const size of [0,1,2]){
      const data=context(now,route,view,run,refresh,size),a=render(now,name,data),b=render(old,name,data);safe(a);
      if(view!==true){assert.equal(a,b,"Guarded whole page remains BASE-exact");assert.equal(a.includes("<form"),false);continue;}
      assert.ok(a.includes('portal-document-operation-layout portal-document-operation-layout--single"'));
      assert.equal(a.includes('class="portal-document-operation-intro"'),false);assert.equal(a.includes("<aside"),false);
      for(const suffix of [prefix+"Title",prefix+"Description",prefix+"History","HistoryBody","OpenFiles","Refresh"])assert.ok(a.includes(esc(copy["docPdfReadyUi"+suffix])),suffix);
      assert.ok(a.includes('<h2 class="portal-card-title">'+esc(copy["docPdfReadyUi"+prefix+"Title"])+"</h2>"));assert.ok(a.includes('<p class="portal-card-subtitle">'+esc(copy["docPdfReadyUi"+prefix+"Description"])+"</p>"));
      const reason=run!==true?"NoPermission":size<minimum?(minimum===2?"ChooseTwo":"ChooseOne"):"OriginalKept";
      assert.ok(a.includes('<span class="portal-form-note">'+esc(copy["docPdfReadyUi"+reason])+"</span>"));
      const form=html=>html.match(/<form class="portal-form"[\s\S]*?<\/form>/)?.[0],x=form(a),y=form(b);assert.ok(x&&y);
      assert.ok(x.startsWith('<form class="portal-form" data-portal-form data-portal-action="document-operation-pdf-'+kind+'" data-portal-route="'+route+'" data-portal-confirm="'+esc(copy["docPdfReadyUi"+prefix+"Confirm"])+'" novalidate>'));
      const vault='<a class="portal-button portal-button--quiet" href="/asset-vault">'+esc(copy.docPdfReadyUiOpenFiles)+"</a>";
      assert.equal(count(a,'href="/asset-vault"'),1);assert.equal(count(x,vault),1);assert.ok(x.indexOf(vault)<x.indexOf('type="submit"'));
      let projected=once(x,vault,"");projected=fieldsBack(projected,y);
      projected=projected.replace(/data-portal-confirm="[^"]*"/,y.match(/data-portal-confirm="[^"]*"/)[0]);
      projected=once(projected,'<span class="portal-form-note">'+esc(copy["docPdfReadyUi"+reason])+"</span>",y.match(/<span class="portal-form-note">[\s\S]*?<\/span>/)[0]);
      projected=once(projected,">"+esc(copy["docPdfReadyUi"+prefix+"Title"])+"</button>",y.match(/<button[^>]*type="submit"[^>]*>([\s\S]*?)<\/button>/)[0].replace(/^<button[^>]*>/,">"));
      assert.equal(projected,y,"Entire retained form differs only in declared copy, moved vault anchor and finite picker copy");
      const controlAttrs=html=>controls(html).filter(tag=>!tag.includes('href="/asset-vault"')).map(tag=>tag.replace(/data-portal-confirm="[^"]*"/,'data-portal-confirm="__DECLARED_COPY__"'));
      assert.deepEqual(controlAttrs(a),controlAttrs(b),"All page controls/DOM attributes remain exact after only the declared navigation move and confirm translation");
      assert.equal(x.match(/<button[^>]*type="submit"[^>]*>/)[0].includes(" disabled"),run!==true||size<minimum);
      assert.equal(a.match(/<button[^>]*data-portal-action="document-operation-refresh"[^>]*>/)[0].includes(" disabled"),refresh!==true);
      const notes=now.qa.renderNotes(data.page);assert.equal(notes,old.qa.renderNotes(data.page));assert.ok(a.includes(notes));assert.ok(a.includes(esc(note)));if(size)assert.ok(x.includes(esc(customer)));
      assert.deepEqual(plain(now.qa[factory]()),plain(old.qa[factory]()));const empty=now.qa.renderDocumentOperationCards([],data.context);
      assert.ok(a.includes(empty));assert.ok(empty.includes(esc(now.messages[locale].docCardEmptyUiTitle)));assert.ok(empty.includes(esc(now.messages[locale].docCardEmptyUiBody)));
    }
  });
  test(`${locale}: actual selected fields and history records retain IDs, validation, real download/rights and card markup`,()=>{
    for(const [name,route,kind,,factory]of tools){
      const data=context(now,route,true,true,true),values=freeze({source_asset_id:ids[0],source_asset_id_1:ids[0],source_asset_id_2:ids[1],page_range:"2-5"});
      const a=readOnly(values,()=>now.qa.renderFields(now.qa[factory](),true,data.context,values)),b=old.qa.renderFields(old.qa[factory](),true,data.context,values);
      assert.equal(fieldsBack(a,b),b);assert.ok(a.includes('value="'+ids[0]+'" selected'));assert.ok(a.includes(esc(customer)));safe(a);
      for(const state of ["completed","processing","guarded","failed"])for(const downloadable of strict){
        const records=freeze([{id:ids[0],kind:"pdf_"+kind,state,download_ready:downloadable,original_filename:customer,source_page_count:2,output_page_count:2,source_count:2,byte_size:1024,completed_at:"2026-11-16T08:00:00Z"}]);
        const ctx=freeze({...data.context,capabilities:{...data.context.capabilities,"document-operation-export-to-asset-vault":downloadable,"content-handoff-create":downloadable},documentOperations:records}),recordsSaved=JSON.stringify(records),cards=now.qa.renderDocumentOperationCards(records,ctx);
        assert.equal(cards,old.qa.renderDocumentOperationCards(records,ctx));assert.equal(JSON.stringify(records),recordsSaved);
        assert.ok(render(now,name,{...data,context:ctx}).includes(cards));safe(cards);
        assert.equal(cards.includes("/api/v1/document-operations/"+ids[0]+"/download"),state==="completed"&&downloadable===true);
      }
    }
  });
  test(`${locale}: real reference pagination retains empty-later Previous, offsets, routes and next policy without a redundant caption`,()=>{
    for(const [pagination,range,offsets]of paginationCases){
      const listing=freeze({pagination}),args=[listing,"document-asset-reference-page","data-document-asset-reference-offset","/documents/split"];
      const a=readOnly(listing,()=>now.qa.renderOperationAssetReferencePagination(...args)),b=old.qa.renderOperationAssetReferencePagination(...args);
      assert.equal(navBack(a,b),b);if(!offsets.length){assert.equal(a,"");continue;}
      assert.ok(a.includes('aria-label="'+text.aria+'"'));assert.deepEqual([...a.matchAll(/data-document-asset-reference-offset="([^"]+)"/g)].map(match=>match[1]),offsets);
      assert.equal(a.includes("<span>"),Boolean(range));if(range)assert.ok(a.includes("<span>"+text.label+(locale==="zh"?"：":": ")+range[0]+"–"+range[1]+"</span>"));
      assert.ok(a.includes('data-portal-action="document-asset-reference-page"'));assert.ok(a.includes('data-portal-route="/documents/split"'));
    }
  });
  test(`${locale}: actual three picker kinds normalize listing/query, preserve controls and read-state behavior`,()=>{
    for(const picker of ["document-pdf","document-image","image-operation"])for(const readState of ["loading","failed","guarded","ready"])for(const size of [0,2])for(const offset of [0,50]){
      const isDocument=picker!=="image-operation",kind=picker==="document-pdf"?"pdf":"image",route=isDocument?"/documents/split":"/images/resize";
      const rows=ids.slice(0,size).map(id=>asset(id,kind)),listing={filters:{q:customer},pagination:{offset,returned:size,has_more:offset===0,next_offset:50,previous_offset:offset?0:undefined}};
      const raw=freeze({path:route,documentAssetReferences:{[kind]:rows,[kind+"_listing"]:listing},imageOperationAssetReferences:{items:rows,listing},documentAssetReferenceReadState:readState,imageOperationAssetReferenceReadState:readState});
      const a=readOnly(raw,()=>now.qa.renderOperationAssetReferencePicker(raw,picker)),b=old.qa.renderOperationAssetReferencePicker(raw,picker);
      assert.equal(pickerBack(a,b),b);safe(a);assert.ok(a.includes("<strong>"+esc(format(text.title,{type:kind==="pdf"?"PDF":text.image}))+"</strong>"));
      if(["loading","failed"].includes(readState))assert.ok(a.includes("<span>"+esc(text[readState])+"</span>"));
      const input=a.match(/<input\b[^>]*>/)[0];assert.ok(input.includes('value="'+esc(customer)+'" maxlength="100"'));assert.equal(input.includes(" disabled"),readState==="guarded");
      const prefix=isDocument?"document-asset-reference":"image-operation-asset-reference";
      for(const action of ["filter","filter-clear"])assert.ok(a.includes('data-portal-action="'+prefix+"-"+action+'" data-portal-route="'+route+'"'+(readState==="guarded"?" disabled":"")+">"));
      assert.deepEqual(plain(now.qa.normalizeDocumentAssetReferences(raw.documentAssetReferences)),plain(old.qa.normalizeDocumentAssetReferences(raw.documentAssetReferences)));
      assert.deepEqual(plain(now.qa.operationAssetReferenceListing(listing,kind)),plain(old.qa.operationAssetReferenceListing(listing,kind)));
    }
    const malformed=freeze({filters:{q:customer.repeat(3)},pagination:{offset:-50,returned:"BAD",has_more:"true",next_offset:"BAD",previous_offset:-1}});
    assert.deepEqual(plain(now.qa.operationAssetReferenceListing(malformed,"pdf")),plain(old.qa.operationAssetReferenceListing(malformed,"pdf")));assert.equal(now.qa.operationAssetReferenceListing(malformed,"pdf").filters.q.length,100);
  });
  test(`${locale}: translated ready/reference text escapes once, same-VM locale and literal fallback retain placeholders`,()=>{
    const hostile='<img src=x onerror="alert(1)"> \'&',encoded='&lt;img src=x onerror=&quot;alert(1)&quot;&gt; &#39;&amp;';
    const override=(key,fallback,params)=>key.startsWith("docPdfReadyUi")||key.startsWith("imageOperationUi.reference")?hostile:format(fallback,params);
    for(const [name,route,,prefix]of tools){
      const data=context(now,route,true,true,true),html=now.qa.withUiText(override,()=>render(now,name,data));safe(html);
      assert.ok(html.includes('data-portal-confirm="'+encoded+'"'));assert.ok(html.includes('<h2 class="portal-card-title">'+encoded+"</h2>"));assert.ok(html.includes('<span class="portal-form-note">'+encoded+"</span>"));
      const next=locales[(locales.indexOf(locale)+1)%3];try{now.setLocale(next);assert.ok(render(now,name,data).includes(esc(fixture[next]["docPdfReadyUi"+prefix+"Description"])));}finally{now.setLocale(locale);}
      const fallback=now.qa.withUiText((key,value,params)=>format(value,params),()=>render(now,name,data));assert.ok(fallback.includes(esc(fixture.vi["docPdfReadyUi"+prefix+"Description"])));
    }
    const raw=context(now,"/documents/split",true,true,true).context,hostilePicker=now.qa.withUiText(override,()=>now.qa.renderOperationAssetReferencePicker(raw,"document-pdf"));safe(hostilePicker);assert.ok(hostilePicker.includes("<strong>"+encoded+"</strong>"));
    const fallback=now.qa.withUiText((key,value,params)=>format(value,params),()=>now.qa.renderOperationAssetReferencePicker(raw,"document-pdf"));
    assert.ok(fallback.includes("<strong>Tìm PDF trong kho tệp</strong>"));assert.ok(fallback.includes("<span>Tệp: 51–52</span>"));assert.equal(/\{(?:type|label|start|end)\}/.test(fallback),false);
    const next=locales[(locales.indexOf(locale)+1)%3];try{now.setLocale(next);assert.ok(now.qa.renderOperationAssetReferencePicker(raw,"document-pdf").includes(esc(format(refText[next].title,{type:"PDF"}))));}finally{now.setLocale(locale);}
    assert.ok(copy.docPdfReadyUiOptimizeDescription.includes("20 MB"));assert.ok(copy.docPdfReadyUiOptimizeDescription.includes("30"),"Removed aside's size/page limit remains visible");
  });
  test(`${locale}: frozen catalogue keeps ordered prior entries, edits only six known values and appends nineteen reviewed keys`,()=>{
    assert.ok(Object.isFrozen(now.messages[locale]));const entries=plain(Object.entries(now.messages[locale])),prior=plain(Object.entries(old.messages[locale]));
    assert.deepEqual(entries.slice(-keys.length),Object.entries(copy));assert.deepEqual(catalogBack(entries,locale),prior);assert.deepEqual(catalogBack(prior,locale),prior);
    const edited=fixture.reference.catalogEntries[locale];assert.deepEqual(entries.slice(0,-keys.length).map(([key])=>key),prior.map(([key])=>key));
    for(const row of edited){assert.equal(entries.find(([key])=>key===row.key)[1],row.new);assert.equal(prior.find(([key])=>key===row.key)[1],row.old);}
    for(const key of keys){
      assert.throws(()=>catalogBack(entries.filter(([k])=>k!==key),locale),/Unreviewed PDF customer cleanup/);
      assert.throws(()=>catalogBack(entries.map(([k,v])=>[k,k===key?"UNKNOWN":v]),locale),/Unreviewed PDF customer cleanup/);
    }
    assert.throws(()=>catalogBack([...entries,["docPdfReadyUiUnknown","UNKNOWN"]],locale),/Unreviewed PDF customer cleanup/);
    assert.throws(()=>catalogBack([...entries,entries.at(-1)],locale),/Unreviewed PDF customer cleanup/);
    assert.throws(()=>catalogBack([...entries.slice(0,-keys.length),...entries.slice(-keys.length).reverse()],locale),/Unreviewed PDF customer cleanup/);
    for(const row of edited){
      assert.throws(()=>catalogBack(entries.map(([key,value])=>[key,key===row.key?"UNKNOWN":value]),locale),/Unreviewed PDF customer cleanup/);
      assert.throws(()=>catalogBack(entries.filter(([key])=>key!==row.key),locale),/Unreviewed PDF customer cleanup/);
      assert.throws(()=>catalogBack(entries.map(([key,value])=>[key,key===row.key?row.old:value]),locale),/Unreviewed PDF customer cleanup/);
    }
    const addedUnknown=[...entries.slice(0,-keys.length),["imageOperationUi.reference.customerExtra","CUSTOMER"],...entries.slice(-keys.length)];
    assert.deepEqual(catalogBack(addedUnknown,locale).at(-1),["imageOperationUi.reference.customerExtra","CUSTOMER"]);
  });
}
function replaceScoped(text,index,old,next){
  const name=tools[Math.floor(index/2)][0],anchor="  function "+name+"(",start=text.indexOf(anchor),end=text.indexOf("\n  function ",start+anchor.length);
  assert.ok(start>=0&&end>start);return text.slice(0,start)+once(text.slice(start,end),old,next)+text.slice(end);
}
test("full-source binding and serial forward/function-scoped reverse preserve every outside byte and both prior PDF CSS additions",()=>{
  assert.match(fixture.base,/^[a-f0-9]{40}$/);const rebuilt={...baseline},files={"static/portal/portal.js":"portal","static/portal/portal-i18n.js":"i18n","static/portal/portal-theme.css":"theme"};
  for(const [index,edit]of fixture.changes.entries()){assert.equal(edit.count,1);const key=files[edit.file];rebuilt[key]=index<6?replaceScoped(rebuilt[key],index,edit.old,edit.new):once(rebuilt[key],edit.old,edit.new);}
  assert.deepEqual(rebuilt,source);
  for(const [key,suffix,inverse]of [["portal","Portal",portalBack],["i18n","I18n",i18nBack],["theme","Theme",cssBack]]){
    assert.equal(hash(baseline[key]),fixture.binding["baseline"+suffix]);assert.equal(hash(source[key]),fixture.binding["candidate"+suffix]);
    assert.equal(inverse(source[key]),baseline[key]);assert.equal(inverse(baseline[key]),baseline[key]);
    const outside='\r\n/* CUSTOMER media Bot Facebook TikTok outside bytes */\r\n';assert.equal(inverse(source[key]+outside),baseline[key]+outside);
  }
  assert.equal(source.theme,once(baseline.theme,fixture.changes[7].old,readyCss+referenceCss+fixture.changes[7].old));
  assert.doesNotMatch(readyCss,/font|color|gap|opacity|display|animation|transform|!important/);
  assert.doesNotMatch(referenceCss,/color|opacity|animation|transform|!important/);assert.ok(referenceCss.includes("gap: 6px;"));assert.ok(referenceCss.includes("min-height: 44px;"));
});
test("finite inverses reject partial, changed, duplicate or misplaced groups and never mask unknown customer bytes",()=>{
  for(let index=0;index<6;index++){
    let current=fixture.changes[index].new;
    for(const edit of amendments.filter(edit=>edit.file==="static/portal/portal.js"))if(current.includes(edit.old))current=once(current,edit.old,edit.new);
    assert.throws(()=>portalBack(replaceScoped(source.portal,index,current,current.replace("docPdfReadyUi","docPdfReadyUiUnknown"))),/Unreviewed PDF customer cleanup/);
    assert.throws(()=>portalBack(source.portal+"\n"+current),/Unreviewed PDF customer cleanup/);
  }
  for(const edit of refEdits.slice(0,4)){
    assert.throws(()=>portalBack(once(source.portal,edit.new,edit.old)),/Unreviewed PDF customer cleanup/);
    assert.throws(()=>portalBack(source.portal+"\n"+edit.new),/Unreviewed PDF customer cleanup/);
  }
  for(const edit of refEdits.slice(4,10))assert.throws(()=>i18nBack(once(source.i18n,edit.new,edit.old)),/Unreviewed PDF customer cleanup/);
  assert.throws(()=>i18nBack(source.i18n+"\n"+fixture.changes[6].new),/Unreviewed PDF customer cleanup/);
  assert.throws(()=>cssBack(source.theme+readyCss),/Unreviewed PDF customer cleanup/);
  assert.throws(()=>cssBack(source.theme.replace(referenceCss,"")),/Unreviewed PDF customer cleanup/);
  assert.throws(()=>cssBack(once(source.theme,referenceCss,referenceCss.replace("gap: 6px;","gap: 7px;"))),/Unreviewed PDF customer cleanup/);
  const outside="/* CUSTOMER outside */";assert.equal(portalBack(outside),outside);assert.equal(i18nBack(outside),outside);assert.equal(cssBack(outside),outside);
});
// Actual contrast, 44px paint geometry, overflow, keyboard, touch and 1440/375 screenshots remain separate native gates.
