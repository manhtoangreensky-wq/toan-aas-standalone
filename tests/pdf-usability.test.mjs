import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import {createHash} from "node:crypto";
import {pdfUsabilitySources,pdfUsabilityRenderer} from "./helpers/pdf-usability-runtime.mjs";
import {PDF_USABILITY_COMPRESS_ADDITION as addition,pdfUsabilityHistoricalPortalSource,pdfUsabilityHistoricalI18nSource,pdfUsabilityHistoricalSnapshot,pdfUsabilityHistoricalCss} from "./helpers/pdf-usability-snapshot.mjs";
// Prospective QA: install with the independently reviewed fixture only after its BASE is delivered.
const fixture=JSON.parse(fs.readFileSync(new URL("./fixtures/pdf-usability-reviewed.json",import.meta.url),"utf8"));
const source=pdfUsabilitySources(),baseline=pdfUsabilitySources(true);
const actual=await pdfUsabilityRenderer(source),before=await pdfUsabilityRenderer(baseline);
const locales=["vi","en","zh"],keys=["docPdfGuardUiTitle","docPdfGuardUiBody"];
const pages=[["renderPdfSplit","/documents/split","split"],["renderPdfMerge","/documents/merge","merge"],["renderPdfOptimize","/documents/compress","optimize"]];
const expected={
  vi:{docPdfGuardUiTitle:"Chưa mở được công cụ PDF",docPdfGuardUiBody:"Không thể tải công cụ lúc này. Vui lòng tải lại trang."},
  en:{docPdfGuardUiTitle:"PDF tool could not be opened",docPdfGuardUiBody:"The tool could not be loaded right now. Please reload the page."},
  zh:{docPdfGuardUiTitle:"无法打开 PDF 工具",docPdfGuardUiBody:"目前无法加载工具，请重新加载页面。"}
};
const customer='CUSTOMER Bot provider CSRF PayOS Facebook TikTok <img src=x onerror="alert(1)">&.pdf';
const note='CUSTOMER Document Operations Asset Vault Bot Facebook TikTok <script>"&\'</script>';
const metadata='<div class="portal-state-meta"><span>Signed session</span><span>Storage riêng</span><span>Không có output giả</span></div>';
const hash=value=>createHash("sha256").update(value).digest("hex"),plain=value=>JSON.parse(JSON.stringify(value));
const escape=value=>String(value).replace(/[&<>'"]/g,char=>({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"}[char]));
const count=(value,part)=>value.split(part).length-1;
const freeze=value=>{if(value&&typeof value==="object"&&!Object.isFrozen(value)){Object.values(value).forEach(freeze);Object.freeze(value);}return value;};
const controls=html=>[...html.matchAll(/<(?:form|button|input|select|textarea|option|a)\b[^>]*>/g)].map(match=>match[0]);
function once(value,old,next){assert.equal(count(value,old),1,"Only the exact reviewed text may be projected");return value.replace(old,()=>next);}
function input(session,route,cap,filled){
  const pdf=filled?["11111111-1111-4111-8111-111111111111","22222222-2222-4222-8222-222222222222"].map(id=>({
    id,display_name:customer,original_filename:customer,state:"active",extension:".pdf",content_type:"application/pdf",byte_size:1024
  })):[];
  const raw=freeze({path:route,capabilities:Object.fromEntries(["view","refresh","pdf-split","pdf-merge","pdf-optimize"].map(key=>["document-operation-"+key,cap])),
    documentAssetReferences:{pdf},documentAssetReferenceReadState:"ready",documentOperations:[]});
  return {raw,page:freeze({...session.qa.resolvePage(route),notes:[note]}),context:freeze({...session.context,...raw})};
}
function render(session,name,data){
  const saved=JSON.stringify(data),html=session.qa[name](data.page,data.context);
  assert.equal(JSON.stringify(data),saved,"Rendering cannot mutate page, context or raw customer records");return html;
}
function guardText(html){
  const marker='<div class="portal-state" data-state="guarded">';assert.equal(count(html,marker),1);
  const tail=html.slice(html.indexOf(marker)),h=tail.match(/<h2>([\s\S]*?)<\/h2>/),p=tail.match(/<p>([\s\S]*?)<\/p>/);
  assert.ok(h&&p);return {heading:h[0],paragraph:p[0]};
}
for(const locale of locales){
  const now=actual(locale,"/documents/split",{}),old=before(locale,"/documents/split",{});
  test(`${locale}: three actual PDF pages retain strict gates, full ready pages, customer text and every outside byte`,()=>{
    for(const [name,route,kind]of pages)for(const cap of [true,false,"true",undefined])for(const filled of [false,true]){
      const data=input(now,route,cap,filled),a=render(now,name,data),b=render(old,name,data);
      assert.ok(a.includes('class="portal-page portal-pdf-'+kind+'"'));assert.deepEqual(controls(a),controls(b));
      assert.equal(a.includes("<img"),false);assert.equal(a.includes("<script>"),false);assert.equal(a.includes("&amp;lt;"),false);
      if(cap===true){
        assert.equal(a,b,"Allowed pages, forms, refresh/run permissions and all controls are byte-identical to BASE");
        assert.ok(a.includes(escape(note)));if(filled)assert.ok(a.includes(escape(customer)));
        assert.ok(a.includes('data-portal-action="document-operation-pdf-'+kind+'"'));continue;
      }
      const shown=guardText(a),prior=guardText(b),copy=expected[locale];
      assert.equal(shown.heading,"<h2>"+escape(copy.docPdfGuardUiTitle)+"</h2>");
      assert.equal(shown.paragraph,"<p>"+escape(copy.docPdfGuardUiBody)+"</p>");
      assert.equal(count(a,shown.heading),1);assert.equal(count(a,shown.paragraph),1);
      assert.equal(a.includes("portal-state-meta"),false);assert.equal(count(b,metadata),1);
      assert.ok(b.includes(prior.paragraph+metadata),"Reinsert baseline metadata only immediately after the baseline paragraph");
      assert.equal(a.includes("<form"),false);assert.equal(a.includes('data-portal-action="document-operation-refresh"'),false);
      let projected=once(a,shown.heading,prior.heading);
      projected=once(projected,shown.paragraph,prior.paragraph+metadata);
      assert.equal(projected,b,"Only h2/p copy and the three reviewed metadata rows differ, never the guard region");
    }
  });
  test(`${locale}: view permission cannot grant run or refresh permissions implicitly`,()=>{
    for(const [name,route]of pages)for(const cap of [true,false,"true",undefined])for(const filled of [false,true]){
      const data=input(now,route,cap,filled),context=freeze({...data.context,capabilities:{...data.raw.capabilities,"document-operation-view":true}});
      const isolated={...data,context},a=render(now,name,isolated),b=render(old,name,isolated);
      assert.equal(a,b);assert.deepEqual(controls(a),controls(b));assert.ok(a.includes("<form"));assert.ok(a.includes(escape(note)));
      const refresh=a.match(/<button\b[^>]*data-portal-action="document-operation-refresh"[^>]*>/);
      const submit=a.match(/<button\b[^>]*type="submit"[^>]*>/);assert.ok(refresh&&submit);
      assert.equal(refresh[0].includes(" disabled"),cap!==true);assert.equal(submit[0].includes(" disabled"),cap!==true||!filled);
    }
  });
  test(`${locale}: hostile translated guards escape once; same VM switches locale and uses the literal VI fallback`,()=>{
    const hostile='<img src=x onerror="alert(1)"> \'&',escaped='&lt;img src=x onerror=&quot;alert(1)&quot;&gt; &#39;&amp;';
    for(const [name,route]of pages){
      const data=input(now,route,false,true);
      const html=now.qa.withUiText((key,fallback)=>keys.includes(key)?hostile:fallback,()=>render(now,name,data));
      assert.deepEqual(guardText(html),{heading:"<h2>"+escaped+"</h2>",paragraph:"<p>"+escaped+"</p>"});
      assert.equal(html.includes("<img"),false);assert.equal(html.includes("&amp;lt;"),false);
      const next=locales[(locales.indexOf(locale)+1)%locales.length];
      try{now.setLocale(next);const switched=guardText(render(now,name,data));
        assert.equal(switched.heading,"<h2>"+escape(expected[next].docPdfGuardUiTitle)+"</h2>");
        assert.equal(switched.paragraph,"<p>"+escape(expected[next].docPdfGuardUiBody)+"</p>");
      }finally{now.setLocale(locale);}
      const fallback=now.qa.withUiText((key,value)=>value,()=>guardText(render(now,name,data)));
      assert.equal(fallback.heading,"<h2>Chưa mở được công cụ PDF</h2>");
      assert.equal(fallback.paragraph,"<p>Không thể tải công cụ lúc này. Vui lòng tải lại trang.</p>");
    }
  });
  test(`${locale}: two ordered frozen catalogue keys append once; missing, unknown, duplicate and changed values fail closed`,()=>{
    const entries=plain(Object.entries(now.messages[locale])),prior=plain(Object.entries(old.messages[locale]));
    assert.ok(Object.isFrozen(now.messages[locale]));assert.deepEqual(fixture[locale],expected[locale]);
    assert.deepEqual(entries.slice(0,prior.length),prior);assert.deepEqual(entries.slice(prior.length),Object.entries(expected[locale]));
    assert.deepEqual(pdfUsabilityHistoricalSnapshot(entries,locale),prior);assert.deepEqual(pdfUsabilityHistoricalSnapshot(prior,locale),prior);
    for(const key of keys){
      assert.throws(()=>pdfUsabilityHistoricalSnapshot(entries.filter(([k])=>k!==key),locale),/Unreviewed PDF usability/);
      assert.throws(()=>pdfUsabilityHistoricalSnapshot(entries.map(([k,v])=>[k,k===key?"UNKNOWN":v]),locale),/Unreviewed PDF usability/);
      assert.throws(()=>pdfUsabilityHistoricalSnapshot([...entries,[key,expected[locale][key]]],locale),/Unreviewed PDF usability/);
    }
    assert.throws(()=>pdfUsabilityHistoricalSnapshot([...entries,["docPdfGuardUiUnknown","UNKNOWN"]],locale),/Unreviewed PDF usability/);
    assert.throws(()=>pdfUsabilityHistoricalSnapshot([...prior,...Object.entries(expected[locale]).reverse()],locale),/Unreviewed PDF usability/);
  });
}
test("full-source hashes bind the delivered BASE and all five exact reviewed forward/inverse edits",()=>{
  assert.match(fixture.base,/^[a-f0-9]{40}$/);assert.equal(fixture.changes.length,5);
  for(const [key,suffix]of [["portal","Portal"],["i18n","I18n"],["theme","Theme"]]){
    assert.equal(hash(baseline[key]),fixture.binding["baseline"+suffix]);assert.equal(hash(source[key]),fixture.binding["candidate"+suffix]);
  }
  const rebuilt={...baseline},files={"static/portal/portal.js":"portal","static/portal/portal-i18n.js":"i18n","static/portal/portal-theme.css":"theme"};
  for(const edit of fixture.changes){assert.equal(edit.count,1);rebuilt[files[edit.file]]=once(rebuilt[files[edit.file]],edit.old,edit.new);}
  assert.deepEqual(rebuilt,source);
  assert.equal(pdfUsabilityHistoricalPortalSource(source.portal),baseline.portal);assert.equal(pdfUsabilityHistoricalPortalSource(baseline.portal),baseline.portal);
  assert.equal(pdfUsabilityHistoricalI18nSource(source.i18n),baseline.i18n);assert.equal(pdfUsabilityHistoricalI18nSource(baseline.i18n),baseline.i18n);
  assert.equal(pdfUsabilityHistoricalCss(source.theme),baseline.theme);
});
test("finite guard inverses reject partial, changed and duplicate input without swallowing any outside bytes",()=>{
  const portalEdits=fixture.changes.filter(edit=>edit.file==="static/portal/portal.js"),catalogEdit=fixture.changes.at(-1);
  for(const edit of portalEdits){
    assert.throws(()=>pdfUsabilityHistoricalPortalSource(once(source.portal,edit.new,edit.old)),/Unreviewed PDF usability/);
    assert.throws(()=>pdfUsabilityHistoricalPortalSource(source.portal+edit.new),/Unreviewed PDF usability/);
    assert.throws(()=>pdfUsabilityHistoricalPortalSource(once(source.portal,edit.new,edit.new.replace("docPdfGuardUiTitle","UNKNOWN"))),/Unreviewed PDF usability/);
  }
  for(const key of keys){
    assert.throws(()=>pdfUsabilityHistoricalI18nSource(source.i18n.replace(key+":",key+"Unknown:")),/Unreviewed PDF usability/);
    const line='    '+key+': "'+expected.en[key]+'"'+(key===keys[0]?",":"")+"\n";
    assert.equal(count(source.i18n,line),1);assert.throws(()=>pdfUsabilityHistoricalI18nSource(source.i18n.replace(line,"")),/Unreviewed PDF usability/);
    assert.throws(()=>pdfUsabilityHistoricalI18nSource(source.i18n.replace(expected.en[key],"UNKNOWN")),/Unreviewed PDF usability/);
  }
  assert.throws(()=>pdfUsabilityHistoricalI18nSource(source.i18n+catalogEdit.new),/Unreviewed PDF usability/);
  const outside='\r\n/* CUSTOMER Bot Facebook TikTok unreviewed outside bytes */\r\n';
  assert.equal(pdfUsabilityHistoricalPortalSource(source.portal+outside),baseline.portal+outside);
  assert.equal(pdfUsabilityHistoricalI18nSource(source.i18n+outside),baseline.i18n+outside);
  assert.throws(()=>pdfUsabilityHistoricalPortalSource(source.portal+"\n// docPdfGuardUiUnknown"),/Unreviewed PDF usability/);
});
test("Compress CSS adds only the two reviewed light semantic colors, preserving Split and every baseline byte",()=>{
  assert.equal(source.theme,baseline.theme+addition);assert.equal(count(source.theme,addition),1);
  assert.equal(count(addition,'html:not([data-portal-theme="dark"]) .portal-page.portal-pdf-optimize'),2);
  assert.equal(count(addition,"color:"),2);assert.ok(addition.includes("color: var(--portal-text);"));assert.ok(addition.includes("color: var(--portal-muted);"));
  assert.doesNotMatch(addition,/!important|font|background|padding|margin|border|opacity|display|visibility|position|width|height|gap|transition|animation|transform/);
  assert.equal(pdfUsabilityHistoricalCss(baseline.theme),baseline.theme);
  assert.throws(()=>pdfUsabilityHistoricalCss(source.theme+addition),/Unreviewed PDF usability CSS/);
  assert.throws(()=>pdfUsabilityHistoricalCss(source.theme+"\n/* UNKNOWN */"),/Unreviewed PDF usability CSS/);
  const changed=addition.replace("var(--portal-muted)","red"),outside='\r\n/* CUSTOMER outside bytes */\r\n';
  assert.equal(pdfUsabilityHistoricalCss(baseline.theme+changed),baseline.theme+changed);
  assert.equal(pdfUsabilityHistoricalCss(outside+source.theme),outside+baseline.theme);
});
// Native paint/contrast, geometry, dark/sentinel equality and interactions are separate NOT_RUN gates.
