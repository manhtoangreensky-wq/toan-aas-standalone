import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import {createHash} from "node:crypto";
import {documentCardDisplayRenderer,documentCardDisplaySources} from "./helpers/document-card-display-runtime.mjs";
import {documentCardDisplayHistoricalPortalSource,documentCardDisplayHistoricalI18nSource,documentCardDisplayHistoricalSnapshot} from "./helpers/document-card-display-snapshot.mjs";
const fixture=JSON.parse(fs.readFileSync(new URL("./fixtures/document-card-display-reviewed.json",import.meta.url),"utf8"));
const source=documentCardDisplaySources(),baseline=documentCardDisplaySources(true),actual=await documentCardDisplayRenderer(source),before=await documentCardDisplayRenderer(baseline);
const sessions=Object.fromEntries(["vi","en","zh"].map(locale=>[locale,{now:actual(locale,"/documents",{}),old:before(locale,"/documents",{})}]));
const kinds=["pdf_split","pdf_merge","pdf_optimize","image_to_pdf","pdf_to_images","pdf_to_word_text","image_ocr","pdf_ocr","pdf_ocr_word"];
const id="11111111-1111-4111-8111-111111111111",literal='CUSTOMER 2026-11-15T08:09:10Z media Facebook TikTok <img src=x onerror="alert(1)">&.pdf';
const esc=(s,v)=>s.qa.safeText(String(v)),hash=v=>createHash("sha256").update(v).digest("hex"),plain=v=>JSON.parse(JSON.stringify(v));
const date="2026-11-15T08:09:10Z",tags={vi:"vi-VN",en:"en-US",zh:"zh-CN"},zone=Intl.DateTimeFormat().resolvedOptions().timeZone;
const formatted=(locale,value)=>new Intl.DateTimeFormat(tags[locale],{dateStyle:"medium",timeStyle:"short",timeZone:zone}).format(new Date(value));
const item=(kind,extra={})=>({id,kind,state:"completed",download_ready:true,original_filename:"",source_page_count:2,output_page_count:2,
  source_count:3,selected_start_page:2,selected_end_page:4,byte_size:3072,input_byte_size:4096,saved_bytes:1024,saved_percent:25,
  language:"vi",completed_at:date,updated_at:"2026-01-01T00:00:00Z",created_at:"2025-01-01T00:00:00Z",...extra});
const freeze=v=>{if(v&&typeof v==="object"&&!Object.isFrozen(v)){Object.values(v).forEach(freeze);Object.freeze(v);}return v;};
function render(s,record,cap=true){
  const records=freeze([record]),context=freeze({path:"/documents/pdf",capabilities:{"document-operation-export-to-asset-vault":cap,"content-handoff-create":cap}});
  const saved=JSON.stringify({records,context}),html=s.qa.renderDocumentOperationCards(records,context);
  assert.equal(JSON.stringify({records,context}),saved);return html;
}
const slots=html=>{
  const title=/<h2 class="portal-card-title">[\s\S]*?<\/h2>/.exec(html)?.[0],icon=/<span class="portal-document-operation-icon"[^>]*>[\s\S]*?<\/span>/.exec(html)?.[0];
  const selected=/<p class="portal-card-subtitle">[\s\S]*?<\/p>/.exec(html)?.[0],dds=[...html.matchAll(/<dd>[\s\S]*?<\/dd>/g)];
  assert.ok(title&&icon&&selected);assert.equal(dds.length,4);return {title,icon,selected,date:dds[3][0]};
};
const nameKeys={pdf_split:"Pdf",pdf_merge:"Pdf",pdf_optimize:"Pdf",image_to_pdf:"Pdf",pdf_to_images:"Images",pdf_to_word_text:"Word",image_ocr:"ImageText",pdf_ocr:"PdfText",pdf_ocr_word:"OcrWord"};
const fixedSelected={pdf_optimize:"Optimize",pdf_to_images:"AllPages",pdf_to_word_text:"Word"};
function selected(s,record,e){
  const kind=record.kind,language=s.qa.imageOcrLanguageLabel(record.language||record.requested_language);
  let value;
  if(fixedSelected[kind])value=e["docSelectedUi"+fixedSelected[kind]];
  else if(kind==="pdf_merge"||kind==="image_to_pdf")value=e["docSelectedUi"+(kind==="pdf_merge"?"Merge":"Images")].replace("{count}",String(Math.max(1,Number(record.source_count)||1)));
  else if(["pdf_ocr_word","pdf_ocr","image_ocr"].includes(kind))value=e["docSelectedUi"+(kind==="pdf_ocr_word"?"ScanWord":kind==="pdf_ocr"?"PdfText":"ImageText")].replace("{language}",language);
  else{
    const start=Number(record.selected_start_page),end=Number(record.selected_end_page);
    value=Number.isInteger(start)&&Number.isInteger(end)?e["docSelectedUi"+(start===end?"Page":"Range")].replace("{start}",String(start)).replace("{end}",String(end)):e.docSelectedUiChecking;
  }
  return value;
}
function project(s,html,prior){
  const now=slots(html),old=slots(prior);let restored=html;
  for(const key of ["title","icon","selected","date"]){assert.equal(restored.split(now[key]).length-1,1);restored=restored.replace(now[key],()=>old[key]);}
  assert.equal(restored,prior,"All non-owned cells/attributes/order/state/actions/metrics remain exact");
}
for(const locale of ["vi","en","zh"]){
  const {now,old}=sessions[locale],e=fixture[locale];
  test(`${locale}: all nine actual card branches localize defaults/selection/date and retain all other markup/rights/state`,()=>{
    for(const kind of kinds)for(const cap of [true,false,"true",undefined])for(const state of ["completed","processing","failed","guarded"]){
      const record=item(kind,{state,download_ready:state==="completed"}),a=render(now,record,cap),b=render(old,record,cap),owned=slots(a);
      assert.equal(owned.title,'<h2 class="portal-card-title">'+esc(now,e["docCardNameUi"+nameKeys[kind]])+"</h2>");
      assert.equal(owned.selected,'<p class="portal-card-subtitle">'+esc(now,selected(now,record,e))+"</p>");
      const icon=["image_ocr","pdf_ocr"].includes(kind)?e.docCardNameUiTextIcon:["pdf_to_word_text","pdf_ocr_word"].includes(kind)?"DOCX":kind==="pdf_to_images"?"PNG":kind==="image_to_pdf"?e.docCardNameUiImageIcon:"PDF";
      assert.ok(owned.icon.includes(">"+esc(now,icon)+"</span>"));assert.equal(owned.date,"<dd>"+esc(now,formatted(locale,date))+"</dd>");
      project(now,a,b);
      assert.equal(now.qa.documentOperationState(record),old.qa.documentOperationState(record));assert.equal(now.qa.documentOperationDownloadPath(record),old.qa.documentOperationDownloadPath(record));
    }
  });
  test(`${locale}: customer filenames and hostile/default-identical strings are never translated or double-escaped`,()=>{
    for(const filename of [literal,e.docCardNameUiPdf,fixture.vi.docCardNameUiPdf,fixture.en.docCardNameUiImages,0,false]){
      const record=item("pdf_split",{original_filename:filename}),a=render(now,record),b=render(old,record);
      assert.equal(slots(a).title,'<h2 class="portal-card-title">'+esc(now,filename||e.docCardNameUiPdf)+"</h2>");assert.equal(a.includes("<img"),false);assert.equal(a.includes("&amp;lt;img"),false);project(now,a,b);
    }
    const hostile='<img src=x onerror="alert(1)"> \'&',record=item("image_to_pdf");
    const a=now.qa.withUiText((key,fallback)=>/^(docCardNameUi|docSelectedUi)/.test(key)?hostile:fallback,()=>render(now,record));
    for(const value of Object.values(slots(a)).slice(0,3))assert.ok(value.includes(esc(now,hostile)));
    assert.equal(a.includes("<img"),false);assert.equal(a.includes("&amp;lt;img"),false);
  });
  test(`${locale}: count/range/date coercions retain source precedence and invalid dates are not echoed`,()=>{
    for(const kind of kinds)for(const extra of [{source_count:0,selected_start_page:2,selected_end_page:2},{source_count:"4",selected_start_page:"3",selected_end_page:"7"},{source_count:"BAD",selected_start_page:"BAD",selected_end_page:3}]){
      const record=item(kind,extra),a=render(now,record),b=render(old,record);
      assert.equal(slots(a).selected,'<p class="portal-card-subtitle">'+esc(now,selected(now,record,e))+"</p>");project(now,a,b);
    }
    const cases=[
      [{completed_at:"",updated_at:date,created_at:"2020-01-01T00:00:00Z"},formatted(locale,date)],
      [{completed_at:null,updated_at:"",created_at:date},formatted(locale,date)],
      [{completed_at:"",updated_at:"",created_at:""},"—"],
      [{completed_at:"not-a-date",updated_at:date},"—"],
      [{completed_at:'<img src=x onerror="alert(1)">'}, "—"],
      [{completed_at:true,updated_at:date},"—"],
      [{completed_at:1794729600000},formatted(locale,1794729600000)]
    ];
    for(const [extra,want]of cases){const record=item("pdf_split",extra),a=render(now,record),b=render(old,record);assert.equal(slots(a).date,"<dd>"+esc(now,want)+"</dd>");project(now,a,b);}
    for(const formatter of [()=>"",()=>{throw Error("date formatter unavailable");}])assert.equal(slots(now.qa.withDateFormatter(formatter,()=>render(now,item("pdf_split")))).date,"<dd>—</dd>");
    const hostile='<img src=x onerror="alert(1)"> \'&';
    const escaped=slots(now.qa.withDateFormatter(()=>hostile,()=>render(now,item("pdf_split")))).date;
    assert.equal(escaped,"<dd>"+esc(now,hostile)+"</dd>");assert.equal(escaped.includes("&amp;lt;img"),false);
  });
  test(`${locale}: live locale/fallback and ordered frozen nineteen-key catalogue preserve earlier entries`,()=>{
    const next=locale==="vi"?"en":locale==="en"?"zh":"vi";
    try{now.setLocale(next);const html=render(now,item("pdf_optimize"));assert.ok(slots(html).title.includes(esc(now,fixture[next].docCardNameUiPdf)));assert.ok(slots(html).selected.includes(esc(now,fixture[next].docSelectedUiOptimize)));assert.equal(slots(html).date,"<dd>"+esc(now,formatted(next,date))+"</dd>");}finally{now.setLocale(locale);}
    const fallback=now.qa.withUiText((key,value)=>value,()=>render(now,item("pdf_optimize")));
    assert.ok(slots(fallback).title.includes(esc(now,fixture.vi.docCardNameUiPdf)));assert.ok(slots(fallback).selected.includes(esc(now,fixture.vi.docSelectedUiOptimize)));
    assert.equal(now.qa.renderDocumentOperationCards([]),old.qa.renderDocumentOperationCards([]));
    const entries=plain(Object.entries(now.messages[locale])),prior=plain(Object.entries(old.messages[locale]));
    assert.ok(Object.isFrozen(now.messages[locale]));assert.deepEqual(entries.slice(0,prior.length),prior);assert.deepEqual(entries.slice(prior.length),Object.entries(e));
    assert.deepEqual(documentCardDisplayHistoricalSnapshot(entries,locale),prior);
    for(const key of Object.keys(e)){
      assert.throws(()=>documentCardDisplayHistoricalSnapshot(entries.filter(([k])=>k!==key),locale),/Unreviewed document display/);
      assert.throws(()=>documentCardDisplayHistoricalSnapshot(entries.map(([k,v])=>[k,k===key?"UNKNOWN":v]),locale),/Unreviewed document display/);
    }
    assert.throws(()=>documentCardDisplayHistoricalSnapshot([...entries,["docSelectedUiUnknown","UNKNOWN"]],locale),/Unreviewed document display/);
  });
}
test("both full source bindings and finite inverse retain every outside mutation and reject partial card/key changes",()=>{
  assert.equal(hash(source.portal),fixture.binding.candidatePortal);assert.equal(hash(source.i18n),fixture.binding.candidateI18n);
  assert.equal(documentCardDisplayHistoricalPortalSource(source.portal),baseline.portal);assert.equal(documentCardDisplayHistoricalI18nSource(source.i18n),baseline.i18n);
  assert.equal(documentCardDisplayHistoricalPortalSource(baseline.portal),baseline.portal);assert.equal(documentCardDisplayHistoricalI18nSource(baseline.i18n),baseline.i18n);
  assert.throws(()=>documentCardDisplayHistoricalPortalSource(source.portal.replace("docSelectedUiOptimize","UNKNOWN")),/Unreviewed document display card/);
  assert.throws(()=>documentCardDisplayHistoricalI18nSource(source.i18n.replace("docSelectedUiOptimize:","UNKNOWN:")),/Unreviewed document display i18n/);
  const suffix="\n// CUSTOMER 2026-11-15T08:09:10Z Facebook TikTok";
  assert.ok(documentCardDisplayHistoricalPortalSource(source.portal+suffix).endsWith(suffix));
});
