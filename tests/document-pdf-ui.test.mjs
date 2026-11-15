import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {createHash} from 'node:crypto';
import {documentPdfRenderer,documentPdfSources} from './helpers/document-pdf-ui-runtime.mjs';
import {documentPdfHistoricalSnapshot,documentPdfHistoricalPortalSource,documentPdfHistoricalI18nSource} from './helpers/document-pdf-ui-snapshot.mjs';
const fixture=JSON.parse(fs.readFileSync(new URL('./fixtures/document-pdf-ui-reviewed.json',import.meta.url),'utf8')),source=documentPdfSources(),baseline=documentPdfSources(true),current=await documentPdfRenderer(source),before=await documentPdfRenderer(baseline);
const hash=value=>createHash('sha256').update(value).digest('hex'),id='11111111-1111-4111-8111-111111111111',literal='CUSTOMER PDF from file library Facebook TikTok <script>alert("x")</script>&';
const sessions=Object.fromEntries(['vi','en','zh'].map(locale=>[locale,{now:current(locale,'/documents/split',{}),old:before(locale,'/documents/split',{})}]));
const esc=(s,v)=>s.qa.safeText(String(v)),copyless=fields=>JSON.parse(JSON.stringify(fields.map(({label,help,emptyLabel,placeholder,...rest})=>rest)));
const tags=html=>[...html.replace(/aria-label="[^"]*"/g,'aria-label="__COPY__"').matchAll(/<[^>]+>/g)].map(m=>m[0]),controls=html=>[...html.matchAll(/<(?:form|button|input|select|textarea|option|a)\b[^>]*>/g)].map(m=>m[0]);
function pagination(s,data,enabled=true){const context={documentOperationListing:{filters:{kind:'pdf_split'},pagination:data}},saved=JSON.stringify(context),html=s.qa.renderDocumentOperationHistoryPagination(context,enabled,'/documents/split');assert.equal(JSON.stringify(context),saved);return html;}
function priorCopyFields(fields,oldFields){
  return fields.map((field,k)=>{const value={...field};for(const key of ['label','help','emptyLabel','placeholder']){if(oldFields[k][key]===undefined)delete value[key];else value[key]=oldFields[k][key];}return value;});
}
for(const locale of ['vi','en','zh']){
  const {now,old}=sessions[locale],e=fixture[locale];
  test(`${locale}: actual pagination retains offsets/actions/control states for empty, next, previous and malformed counts`,()=>{
    const cases=[{}, {offset:0,returned:2,has_more:true,next_offset:50},{offset:50,returned:0,has_more:false},{offset:50,returned:2,has_more:true,next_offset:100},{offset:-1,returned:'BAD',has_more:'true',next_offset:50},{offset:'50',returned:'2',has_more:true,next_offset:'100'}];
    for(const data of cases)for(const enabled of [true,false,'true']){
      const a=pagination(now,data,enabled),b=pagination(old,data,enabled);assert.deepEqual(tags(a),tags(b));assert.deepEqual(controls(a),controls(b));if(!b){assert.equal(a,'');continue;}
      assert.ok(a.includes('aria-label="'+esc(now,e.docHistoryUiAria)+'"'));for(const key of ['docHistoryUiPrevious','docHistoryUiNext'])if(b.includes(key.endsWith('Previous')?'←':'→'))assert.ok(a.includes(esc(now,e[key])));
      assert.ok(a.includes(esc(now,e.docHistoryUiLabel)));assert.ok(a.includes('data-portal-route="/documents/split"'));assert.ok(a.includes('data-document-operation-offset='));
    }
    const hostile='<img src=x onerror="alert(1)"> \'&',html=now.qa.withUiText((key,fallback)=>key.startsWith('docHistoryUi')?hostile:fallback,()=>pagination(now,cases[1]));assert.equal(html.includes('<img'),false);assert.equal(html.includes('&amp;lt;img'),false);
  });
  test(`${locale}: field copy and exact validation descriptors/rendered controls remain on split/optimize`,()=>{
    for(const name of ['pdfSplitFormFields','pdfOptimizeFormFields']){
      const a=now.qa[name](),b=old.qa[name]();assert.deepEqual(copyless(a),copyless(b));assert.equal(a[0].label,e.docPdfSourceUiLabel);assert.equal(a[0].emptyLabel,e.docPdfSourceUiEmpty);assert.equal(a[0].required,true);assert.equal(a[0].optionsFrom,'pdfVaultAssets');assert.equal(a[0].referencePicker,'document-pdf');
      if(name==='pdfSplitFormFields'){assert.equal(a[1].label,e.docPdfPageUiLabel);assert.equal(a[1].placeholder,e.docPdfPageUiPlaceholder);assert.equal(a[1].help,e.docPdfPageUiHelp);assert.equal(a[1].pattern,'\\d+(?:-\\d+)?');assert.equal(a[1].maxLength,32);assert.ok(a[1].help.includes('20 MB'));assert.ok(a[1].help.includes('30'));}
      else assert.equal(a[0].help,e.docPdfOptimizeUiHelp);
      for(const enabled of [true,false])for(const values of [{},{source_asset_id:id,page_range:'2-5'}]){
        const context={...now.context,pdfVaultAssets:[{value:id,label:literal}]},x=now.qa.renderFields(a,enabled,context,values),y=old.qa.renderFields(b,enabled,{...old.context,pdfVaultAssets:context.pdfVaultAssets},values);assert.equal(now.qa.renderFields(priorCopyFields(a,b),enabled,context,values),y);for(const field of a)for(const key of ['label','help','emptyLabel','placeholder'])if(field[key])assert.ok(x.includes(esc(now,field[key])));
      }
    }
  });
  test(`${locale}: three PDF pages remove only notice wrappers, retain real notes/aside/forms/rights and live locale/catalog`,()=>{
    for(const[name,route]of[['renderPdfSplit','/documents/split'],['renderPdfMerge','/documents/merge'],['renderPdfOptimize','/documents/compress']])for(const allowed of [true,false,'true'])for(const filled of [false,true]){
      const pdf=filled?[id,'22222222-2222-4222-8222-222222222222'].map(id=>({id,display_name:literal,original_filename:'source.pdf',state:'active',extension:'.pdf',content_type:'application/pdf',byte_size:1024})):[],notes=[literal,'CUSTOMER limits 20 MB / 30 pages'],page={...now.qa.resolvePage(route),notes},ctx={...now.context,path:route,capabilities:{'document-operation-view':allowed,'document-operation-refresh':allowed,'document-operation-pdf-split':allowed,'document-operation-pdf-merge':allowed,'document-operation-pdf-optimize':allowed},documentAssetReferences:{pdf},documentOperations:[]},saved=JSON.stringify({page,ctx});
      const a=now.qa[name](page,ctx),b=old.qa[name](page,ctx),note=now.qa.renderNotes(page);assert.equal(JSON.stringify({page,ctx}),saved);
      if(allowed!==true){assert.equal(a,b);continue;}assert.ok(a.includes(note));assert.equal(note,old.qa.renderNotes(page));assert.equal(a.includes('<strong>Không thay thế workflow Bot</strong>'),false);
      const pattern=/<section class="portal-card portal-card-pad"><div class="portal-notice portal-notice--info"><span class="portal-notice-icon" aria-hidden="true">i<\/span><div><strong>Không thay thế workflow Bot<\/strong><p>PDF (?:Split|Merge|Optimize)[\s\S]*?<\/p><\/div><\/div>([\s\S]*?)<\/section>/g,matches=[...b.matchAll(pattern)];assert.equal(matches.length,1);assert.equal(matches[0][1],note);
      let projected=a;if(name!=='renderPdfMerge'){const fieldName=name==='renderPdfSplit'?'pdfSplitFormFields':'pdfOptimizeFormFields',fields=now.qa[fieldName](),oldFields=old.qa[fieldName](),nextFields=now.qa.renderFields(fields,filled,ctx,{}),priorFields=now.qa.renderFields(priorCopyFields(fields,oldFields),filled,ctx,{});assert.equal(projected.split(nextFields).length-1,1);projected=projected.replace(nextFields,priorFields);}
      assert.equal(projected,b.replace(matches[0][0],note),'Whole page outside finite fields and the one notice wrapper stays exact');
    }
    const next=locale==='vi'?'en':locale==='en'?'zh':'vi';try{now.setLocale(next);assert.equal(now.qa.pdfSplitFormFields()[0].label,fixture[next].docPdfSourceUiLabel);}finally{now.setLocale(locale);}
    const fallback=now.qa.withUiText((key,value)=>value,()=>now.qa.pdfSplitFormFields());assert.equal(fallback[0].label,fixture.vi.docPdfSourceUiLabel);assert.equal(fallback[1].help,fixture.vi.docPdfPageUiHelp);
    const entries=Object.entries(now.messages[locale]),prior=Object.entries(old.messages[locale]);assert.ok(Object.isFrozen(now.messages[locale]));assert.deepEqual(JSON.parse(JSON.stringify(entries.slice(0,prior.length))),JSON.parse(JSON.stringify(prior)));assert.deepEqual(JSON.parse(JSON.stringify(entries.slice(prior.length))),Object.entries(e));assert.deepEqual(JSON.parse(JSON.stringify(documentPdfHistoricalSnapshot(entries,locale))),JSON.parse(JSON.stringify(prior)));
    for(const key of Object.keys(e)){assert.throws(()=>documentPdfHistoricalSnapshot(entries.filter(([k])=>k!==key),locale),/Unreviewed PDF UI copy/);assert.throws(()=>documentPdfHistoricalSnapshot(entries.map(([k,v])=>[k,k===key?'UNKNOWN':v]),locale),/Unreviewed PDF UI copy/);}assert.throws(()=>documentPdfHistoricalSnapshot([...entries,['docPdfSourceUiUnknown','X']],locale),/Unreviewed PDF UI copy/);
  });
}
test('six exact chunks and both literal i18n additions normalize first without hiding outside/unknown mutations',()=>{
  assert.equal(hash(source.portal),fixture.binding.candidatePortal);assert.equal(hash(source.i18n),fixture.binding.candidateI18n);assert.equal(documentPdfHistoricalPortalSource(source.portal),baseline.portal);assert.equal(documentPdfHistoricalI18nSource(source.i18n),baseline.i18n);
  for(const name of ['renderDocumentOperationHistoryPagination','pdfSplitFormFields','pdfOptimizeFormFields']){
    const anchor='  function '+name+'(';assert.equal(source.portal.split(anchor).length-1,1);assert.throws(()=>documentPdfHistoricalPortalSource(source.portal.replace(anchor,anchor+'/* UNKNOWN */')),/Unreviewed|Assertion/);
  }
  for(const name of ['renderPdfSplit','renderPdfMerge','renderPdfOptimize']){const a=source.portal.indexOf('  function '+name+'('),b=source.portal.indexOf('\n  function ',a+4),part=source.portal.slice(a,b);assert.equal(part.split('      ${renderNotes(page)}').length-1,1);assert.throws(()=>documentPdfHistoricalPortalSource(source.portal.slice(0,a)+part.replace('      ${renderNotes(page)}','      ${renderNotes(UNKNOWN)}')+source.portal.slice(b)),/Unreviewed PDF UI/);}
  const outside=source.portal+'\n// CUSTOMER PDF Facebook TikTok';assert.notEqual(documentPdfHistoricalPortalSource(outside),baseline.portal);assert.ok(documentPdfHistoricalPortalSource(outside).endsWith('Facebook TikTok'));
  assert.throws(()=>documentPdfHistoricalI18nSource(source.i18n.replace('docHistoryUiAria:','UNKNOWN:')),/Unreviewed PDF UI i18n/);
});
