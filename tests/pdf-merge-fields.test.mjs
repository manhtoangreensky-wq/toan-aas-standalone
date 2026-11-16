import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import {createHash} from "node:crypto";
import {pdfMergeFieldsSources,pdfMergeFieldsRenderer} from "./helpers/pdf-merge-fields-runtime.mjs";
import {pdfMergeFieldsHistoricalPortalSource as portalBack,pdfMergeFieldsHistoricalI18nSource as i18nBack,pdfMergeFieldsHistoricalSnapshot as catalogBack} from "./helpers/pdf-merge-fields-snapshot.mjs";
const fixture=JSON.parse(fs.readFileSync(new URL("./fixtures/pdf-merge-fields-reviewed.json",import.meta.url),"utf8"));
const source=pdfMergeFieldsSources(),baseline=pdfMergeFieldsSources(true),actual=await pdfMergeFieldsRenderer(source),before=await pdfMergeFieldsRenderer(baseline);
const locales=["vi","en","zh"],strict=[true,false,"true",undefined],route="/documents/merge";
const copy={
  vi:["PDF thứ {position}","PDF thứ {position} (tùy chọn)","Chọn PDF thứ {position}","Không thêm PDF","PDF được gộp theo thứ tự từ trên xuống dưới. Chọn các tệp trong kho tệp của bạn.","Chọn ít nhất hai PDF khác nhau.","Để trống nếu không cần thêm tệp. Mỗi PDF chỉ được chọn một lần."],
  en:["PDF {position}","PDF {position} (optional)","Choose PDF {position}","No additional PDF","PDFs are merged from top to bottom. Choose files from your file vault.","Choose at least two different PDFs.","Leave this empty if no more files are needed. Each PDF can be selected only once."],
  zh:["第 {position} 个 PDF","第 {position} 个 PDF（可选）","选择第 {position} 个 PDF","不添加 PDF","PDF 将按从上到下的顺序合并。请从文件库中选择文件。","请至少选择两个不同的 PDF。","无需添加更多文件时可留空。每个 PDF 只能选择一次。"]
};
const suffixes=["SourceLabel","SourceOptionalLabel","Select","NoExtra","OrderHelp","MinimumHelp","OptionalHelp"],keys=suffixes.map(suffix=>"docPdfMergeUi"+suffix);
const ids=["11111111-1111-4111-8111-111111111111","22222222-2222-4222-8222-222222222222"];
const customer='CUSTOMER Bot media CSRF Facebook TikTok <img src=x onerror="alert(1)">&.pdf',note='CUSTOMER provider Bot Asset Vault PayOS <script>"&\'</script>';
const hash=value=>createHash("sha256").update(value).digest("hex"),plain=value=>JSON.parse(JSON.stringify(value)),count=(value,part)=>value.split(part).length-1;
const esc=value=>String(value).replace(/[&<>'"]/g,char=>({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"}[char]));
const format=(text,params={})=>String(text).replace(/\{([^}]+)\}/g,(token,key)=>Object.hasOwn(params,key)?String(params[key]):token);
const freeze=value=>{if(value&&typeof value==="object"&&!Object.isFrozen(value)){Object.values(value).forEach(freeze);Object.freeze(value);}return value;};
const controls=html=>[...html.matchAll(/<(?:form|select|option|input|button|a|textarea)\b[^>]*>/g)].map(match=>match[0]);
const copyless=fields=>fields.map(({label,emptyLabel,help,...rest})=>rest);
function once(value,old,next){assert.equal(count(value,old),1,"Only one exact reviewed field-copy slot may change");return value.replace(old,()=>next);}
function readonly(data,run){const saved=JSON.stringify(data),result=run();assert.equal(JSON.stringify(data),saved);return result;}
function safe(html){assert.equal(html.includes("<img"),false);assert.equal(html.includes("<script>"),false);assert.equal(html.includes("&amp;lt;"),false);}
function expectedFields(locale){return Array.from({length:8},(_,index)=>{const position=index+1,c=copy[locale];return {label:format(c[index<2?0:1],{position}),emptyLabel:index<2?format(c[2],{position}):c[3],help:c[index===0?4:index===1?5:6]};});}
function projectCopy(html,fields,prior){
  let value=html;
  for(let index=0;index<8;index++){
    const id="portal-field-source_asset_id_"+(index+1),a=fields[index],b=prior[index];
    value=once(value,'<label for="'+id+'">'+esc(a.label),'<label for="'+id+'">'+esc(b.label));
    value=once(value,'<span id="'+id+'-help" class="portal-field-help">'+esc(a.help)+"</span>",'<span id="'+id+'-help" class="portal-field-help">'+esc(b.help)+"</span>");
    const start=value.indexOf('<select class="portal-select" id="'+id+'"'),end=value.indexOf("</select>",start)+9;assert.ok(start>=0&&end>start);
    const select=value.slice(start,end),empty=select.match(/(<option value=""(?: selected)?>)([\s\S]*?)(<\/option>)/);assert.ok(empty);assert.equal(empty[2],esc(a.emptyLabel));
    value=value.slice(0,start)+once(select,empty[0],empty[1]+esc(b.emptyLabel)+empty[3])+value.slice(end);
  }
  return value;
}
function input(session,view,run,refresh,size){
  const pdf=ids.slice(0,size).map(id=>({id,display_name:customer,original_filename:customer,extension:".pdf",content_type:"application/pdf",state:"active",byte_size:1024}));
  const raw=freeze({path:route,capabilities:{"document-operation-view":view,"document-operation-pdf-merge":run,"document-operation-refresh":refresh},
    documentAssetReferences:{pdf,pdf_listing:{filters:{q:customer},pagination:{offset:50,returned:size,has_more:false,previous_offset:0}}},
    documentAssetReferenceReadState:"ready",documentOperations:[{id:ids[0],kind:"pdf_merge",state:"completed",download_ready:true,original_filename:customer,source_count:2,source_page_count:2,output_page_count:2,byte_size:1024,completed_at:"2026-11-16T13:00:00Z"}]});
  return freeze({raw,page:{...session.qa.resolvePage(route),notes:[note]},context:{...session.context,...raw}});
}
for(const locale of locales){
  const now=actual(locale,route,{}),old=before(locale,route,{});
  test(`${locale}: eight actual field descriptors localize literal copy/position params, keeping names, first-two required, order and other properties`,()=>{
    const fields=freeze(now.qa.pdfMergeFormFields()),prior=freeze(old.qa.pdfMergeFormFields());assert.equal(fields.length,8);
    assert.deepEqual(plain(fields.map(({label,emptyLabel,help})=>({label,emptyLabel,help}))),expectedFields(locale));
    assert.deepEqual(plain(copyless(fields)),plain(copyless(prior)));
    for(let index=0;index<8;index++){assert.equal(fields[index].name,"source_asset_id_"+(index+1));assert.equal(fields[index].required,index<2);assert.equal(fields[index].control,"select");assert.equal(fields[index].optionsFrom,"pdfVaultAssets");assert.equal(fields[index].referencePicker,index===0?"document-pdf":"");}
    const calls=[];const observed=now.qa.withUiText((key,fallback,params)=>{if(key.startsWith("docPdfMergeUi"))calls.push([key,params?plain(params):null]);return format(now.messages[locale][key]??fallback,params);},()=>now.qa.pdfMergeFormFields());
    assert.deepEqual(plain(observed),plain(fields));assert.equal(calls.length,24);
    for(const [key,positions]of [["SourceLabel",[1,2]],["SourceOptionalLabel",[3,4,5,6,7,8]],["Select",[1,2]]])
      assert.deepEqual(calls.filter(([name])=>name==="docPdfMergeUi"+key).map(([,params])=>params),positions.map(position=>({position})));
    for(const [key,total]of [["NoExtra",6],["OrderHelp",1],["MinimumHelp",1],["OptionalHelp",6]]){
      const uses=calls.filter(([name])=>name==="docPdfMergeUi"+key);assert.equal(uses.length,total);assert.ok(uses.every(([,params])=>params===null));
    }
    const values=freeze({source_asset_id_1:ids[0],source_asset_id_2:ids[1]}),data=input(now,true,true,true,2);
    for(const enabled of [true,false]){
      const a=readonly({fields,values,data},()=>now.qa.renderFields(fields,enabled,data.context,values)),b=old.qa.renderFields(prior,enabled,data.context,values);
      assert.deepEqual(controls(a),controls(b));assert.equal(projectCopy(a,fields,prior),b);safe(a);assert.ok(a.includes(esc(customer)));assert.ok(a.includes('value="'+ids[0]+'" selected'));
    }
  });
  test(`${locale}: actual Merge whole pages preserve strict independent rights, 0/1/2 sources, forms, history, notes and every outside byte`,()=>{
    const fields=now.qa.pdfMergeFormFields(),prior=old.qa.pdfMergeFormFields();
    for(const view of strict)for(const run of strict)for(const refresh of strict)for(const size of [0,1,2]){
      const data=input(now,view,run,refresh,size),a=readonly(data,()=>now.qa.renderPdfMerge(data.page,data.context)),b=old.qa.renderPdfMerge(data.page,data.context);safe(a);
      assert.deepEqual(controls(a),controls(b));
      if(view!==true){assert.equal(a,b);assert.equal(a.includes("<form"),false);continue;}
      assert.equal(projectCopy(a,fields,prior),b,"Only 8 labels/empty captions/help slots may differ across the complete page");
      assert.equal(a.match(/<button[^>]*type="submit"[^>]*>/)[0].includes(" disabled"),run!==true||size<2);
      assert.equal(a.match(/<button[^>]*data-portal-action="document-operation-refresh"[^>]*>/)[0].includes(" disabled"),refresh!==true);
      const notes=now.qa.renderNotes(data.page),cards=now.qa.renderDocumentOperationCards(data.context.documentOperations,data.context);
      assert.equal(notes,old.qa.renderNotes(data.page));assert.equal(cards,old.qa.renderDocumentOperationCards(data.context.documentOperations,data.context));assert.ok(a.includes(notes));assert.ok(a.includes(cards));assert.ok(a.includes(esc(note)));assert.ok(a.includes(esc(customer)));
      assert.ok(a.includes('data-portal-action="document-operation-pdf-merge" data-portal-route="'+route+'"'));assert.ok(a.includes(" novalidate>"));assert.equal(count(a,'href="/asset-vault"'),1);
    }
  });
  test(`${locale}: live locale, dynamic VI fallback, hostile translations, frozen seven-key append and inverse catalogue guards remain exact`,()=>{
    const next=locales[(locales.indexOf(locale)+1)%3];
    try{now.setLocale(next);assert.deepEqual(plain(now.qa.pdfMergeFormFields().map(({label,emptyLabel,help})=>({label,emptyLabel,help}))),expectedFields(next));}finally{now.setLocale(locale);}
    const fallback=now.qa.withUiText((key,value,params)=>format(value,params),()=>now.qa.pdfMergeFormFields());
    assert.deepEqual(plain(fallback.map(({label,emptyLabel,help})=>({label,emptyLabel,help}))),expectedFields("vi"));
    const hostile='<img src=x onerror="alert(1)"> \'&',encoded='&lt;img src=x onerror=&quot;alert(1)&quot;&gt; &#39;&amp;';
    const fields=now.qa.withUiText((key,value,params)=>key.startsWith("docPdfMergeUi")?hostile:format(value,params),()=>now.qa.pdfMergeFormFields()),data=input(now,true,true,true,2);
    const html=readonly(data,()=>now.qa.renderFields(fields,true,data.context,{}));safe(html);
    for(let position=1;position<=8;position++){assert.ok(html.includes('<label for="portal-field-source_asset_id_'+position+'">'+encoded));assert.ok(html.includes('<span id="portal-field-source_asset_id_'+position+'-help" class="portal-field-help">'+encoded+"</span>"));}
    assert.ok(html.includes('<option value="" selected>'+encoded+"</option>"));assert.ok(html.includes(esc(customer)));
    assert.ok(Object.isFrozen(now.messages[locale]));const entries=plain(Object.entries(now.messages[locale])),prior=plain(Object.entries(old.messages[locale])),added=keys.map((key,index)=>[key,copy[locale][index]]);
    assert.deepEqual(entries.slice(0,-7),prior);assert.deepEqual(entries.slice(-7),added);assert.deepEqual(catalogBack(entries,locale),prior);assert.deepEqual(catalogBack(prior,locale),prior);
    for(const key of keys){assert.throws(()=>catalogBack(entries.filter(([k])=>k!==key),locale),/Unreviewed PDF Merge fields/);assert.throws(()=>catalogBack(entries.map(([k,v])=>[k,k===key?"UNKNOWN":v]),locale),/Unreviewed PDF Merge fields/);}
    assert.throws(()=>catalogBack([...entries,["docPdfMergeUiUnknown","UNKNOWN"]],locale),/Unreviewed PDF Merge fields/);
    assert.throws(()=>catalogBack([...entries,entries.at(-1)],locale),/Unreviewed PDF Merge fields/);assert.throws(()=>catalogBack([...prior,...added.reverse()],locale),/Unreviewed PDF Merge fields/);
    assert.deepEqual(catalogBack([...prior,["customerOutside","UNCHANGED"],...keys.map((key,index)=>[key,copy[locale][index]])],locale),[...prior,["customerOutside","UNCHANGED"]]);
  });
}
test("three exact forward edits and scoped inverse bind full raw portal/i18n; theme stays unchanged",()=>{
  assert.equal(fixture.changes.length,3);assert.match(fixture.base,/^[a-f0-9]{40}$/);
  const rebuilt={...baseline};
  for(const edit of fixture.changes){assert.equal(edit.count,1);const key=edit.file.endsWith("portal.js")?"portal":"i18n";rebuilt[key]=once(rebuilt[key],edit.old,edit.new);}
  assert.deepEqual(rebuilt,source);
  for(const [key,suffix,inverse]of [["portal","Portal",portalBack],["i18n","I18n",i18nBack]]){assert.equal(hash(baseline[key]),fixture.binding["baseline"+suffix]);assert.equal(hash(source[key]),fixture.binding["candidate"+suffix]);assert.equal(inverse(source[key]),baseline[key]);assert.equal(inverse(baseline[key]),baseline[key]);}
  assert.equal(source.theme,baseline.theme);assert.equal(hash(source.theme),fixture.binding.candidateTheme);
});
test("source inverses reject partial, mutated, duplicate or detached chunks instead of hiding unknown code",()=>{
  for(const edit of fixture.changes.slice(0,2)){
    assert.throws(()=>portalBack(once(source.portal,edit.new,edit.old)),/Unreviewed PDF Merge fields/);
    assert.throws(()=>portalBack(once(source.portal,edit.new,edit.new.replace("docPdfMergeUi","docPdfMergeUiUnknown"))),/Unreviewed PDF Merge fields/);
    assert.throws(()=>portalBack(source.portal+"\n"+edit.new),/Unreviewed PDF Merge fields/);
    assert.throws(()=>portalBack(once(source.portal,edit.new,edit.old)+"\n"+edit.new),/Unreviewed PDF Merge fields/);
  }
  const addition=fixture.changes[2].new;
  assert.throws(()=>i18nBack(source.i18n+"\n"+addition),/Unreviewed PDF Merge fields/);
  assert.throws(()=>i18nBack(once(source.i18n,addition,addition.replace("docPdfMergeUiSourceLabel","docPdfMergeUiUnknown"))),/Unreviewed PDF Merge fields/);
  assert.throws(()=>i18nBack(source.i18n+"\n// docPdfMergeUiUnknown"),/Unreviewed PDF Merge fields/);
});
test("old unrelated sources/catalogues and mixed-line-ending customer bytes survive inverses untouched",()=>{
  const prefix='\r\n/* CUSTOMER prefix */\r\n',suffix='\r\n/* CUSTOMER Bot Facebook TikTok suffix */\r\n';
  assert.equal(portalBack(prefix+source.portal+suffix),prefix+baseline.portal+suffix);
  assert.equal(i18nBack(prefix+source.i18n+suffix),prefix+baseline.i18n+suffix);
  assert.equal(portalBack(prefix),prefix);assert.equal(i18nBack(suffix),suffix);
  assert.deepEqual(catalogBack([["customerOnly","UNCHANGED"]],"vi"),[["customerOnly","UNCHANGED"]]);
});
// Source/renderer QA only. Native layout, iOS focus, provider output and deployment are not asserted here.
