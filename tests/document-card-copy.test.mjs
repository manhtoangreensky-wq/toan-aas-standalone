import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {createHash} from 'node:crypto';
import {documentCardRenderer,documentCardSources} from './helpers/document-card-copy-runtime.mjs';
import {documentCardHistoricalSnapshot,documentCardHistoricalPortalSource,documentCardHistoricalI18nSource} from './helpers/document-card-copy-snapshot.mjs';
import {documentPdfHistoricalSnapshot,documentPdfHistoricalPortalSource,documentPdfHistoricalI18nSource} from './helpers/document-pdf-ui-snapshot.mjs';
import {documentCardDisplayHistoricalPortalSource,documentCardDisplayHistoricalI18nSource} from './helpers/document-card-display-snapshot.mjs';
const reviewed=JSON.parse(fs.readFileSync(new URL('./fixtures/document-card-copy-reviewed.json',import.meta.url),'utf8'));
const rawSource=documentCardSources();
const source={portal:documentPdfHistoricalPortalSource(rawSource.portal),i18n:documentPdfHistoricalI18nSource(rawSource.i18n)};
const baseline=documentCardSources(true),rawCurrent=await documentCardRenderer({portal:documentCardDisplayHistoricalPortalSource(rawSource.portal),i18n:documentCardDisplayHistoricalI18nSource(rawSource.i18n)}),before=await documentCardRenderer(baseline);
const rawCatalogueFrozen=Symbol('rawCatalogueFrozen');
function current(...args){
  const session=rawCurrent(...args),frozen={},messages={};
  for(const locale of ['vi','en','zh']){
    frozen[locale]=Object.isFrozen(session.messages[locale]);
    messages[locale]=Object.fromEntries(documentPdfHistoricalSnapshot(Object.entries(session.messages[locale]),locale));
  }
  return {...session,messages,[rawCatalogueFrozen]:frozen};
}
const kinds=['pdf_split','pdf_merge','pdf_optimize','image_to_pdf','pdf_to_images','pdf_to_word_text','image_ocr','pdf_ocr','pdf_ocr_word'];
const id='11111111-1111-4111-8111-111111111111',literal='CUSTOMER Artifact provider Bot server media Facebook TikTok <script>alert("x")</script>.pdf';
const item=(kind='pdf_split',pages=1,extra={})=>({id,kind,state:'completed',download_ready:true,original_filename:literal,source_page_count:pages,output_page_count:pages,source_count:2,selected_start_page:2,selected_end_page:4,input_byte_size:4096,byte_size:3072,saved_bytes:1024,saved_percent:25,language:'vi',completed_at:'2026-11-15T08:09:10Z',updated_at:'RAW_UPDATED',created_at:'RAW_CREATED',...extra});
const sessions=Object.fromEntries(['vi','en','zh'].map(locale=>[locale,{now:current(locale,'/documents',{}),old:before(locale,'/documents',{})}]));
const esc=(session,value)=>session.qa.safeText(String(value)),hash=text=>createHash('sha256').update(text).digest('hex');
const freeze=value=>{if(value&&typeof value==='object'&&!Object.isFrozen(value)){Object.values(value).forEach(freeze);Object.freeze(value);}return value;};
function render(session,records,rights,empty){
  const cap=arguments.length>=3?rights:true,context=freeze({path:'/documents/pdf',capabilities:{'document-operation-export-to-asset-vault':cap,'content-handoff-create':cap}});freeze(records);
  const saved=JSON.stringify({records,context}),html=empty?session.qa.renderDocumentOperationCards(records,context,...empty):session.qa.renderDocumentOperationCards(records,context);
  assert.equal(JSON.stringify({records,context}),saved);return html;
}
const articles=html=>[...html.matchAll(/<article class="portal-card portal-card-pad portal-document-operation-card"[\s\S]*?<\/article>/g)].map(match=>match[0]);
const opening=html=>html.slice(0,html.indexOf('>')+1),attr=(tag,name)=>new RegExp(name+'="([^"]*)"').exec(tag)?.[1];
const oldDt=['Nguồn','Đầu ra',null,'Cập nhật'];
function labels(record,e){
  const kind=record.kind,pages=Number(record.output_page_count),ocr=['image_ocr','pdf_ocr'].includes(kind),word=['pdf_to_word_text','pdf_ocr_word'].includes(kind);
  return {artifact:ocr?'TXT':word?'DOCX':kind==='pdf_to_images'?(pages===1?'PNG':'ZIP'):e[kind==='pdf_optimize'?'docCardUiReduced':'docCardUiResultFile'],download:e[ocr?'docCardUiDownloadTxt':word?'docCardUiDownloadDocx':kind==='pdf_to_images'?(pages===1?'docCardUiDownloadPng':'docCardUiDownloadZip'):'docCardUiDownloadPdf']};
}
function project(session,next,prior,record,e,pendingKey){
  const selected=labels(record,e),a=[...next.matchAll(/<dt>([\s\S]*?)<\/dt>/g)],b=[...prior.matchAll(/<dt>([\s\S]*?)<\/dt>/g)];assert.equal(a.length,4);assert.equal(b.length,4);
  const texts=[e.docCardUiSource,e.docCardUiOutput,selected.artifact,e.docCardUiUpdated];let projected=next;
  for(let k=3;k>=0;k--){assert.equal(a[k][1],esc(session,texts[k]));if(oldDt[k])assert.equal(b[k][1],oldDt[k]);projected=projected.slice(0,a[k].index)+b[k][0]+projected.slice(a[k].index+a[k][0].length);}
  const pending=/<span class="portal-form-note">([\s\S]*?)<\/span>/,pn=pending.exec(projected),po=pending.exec(prior);assert.equal(Boolean(pn),Boolean(po));
  if(pn){assert.ok(pendingKey);assert.equal(pn[1],esc(session,e[pendingKey]));projected=projected.replace(pn[0],po[0]);}
  const link=/<a class="portal-button portal-button--primary"[^>]*>([\s\S]*?)<\/a>/,ln=link.exec(projected),lo=link.exec(prior);assert.equal(Boolean(ln),Boolean(lo));
  if(ln){assert.equal(opening(ln[0]),opening(lo[0]));assert.equal(ln[1],esc(session,selected.download)+' <span aria-hidden="true">↓</span>');projected=projected.replace(ln[0],ln[0].replace(ln[1],lo[1]));}
  const buttons=html=>[...html.matchAll(/<button\b[^>]*>([\s\S]*?)<\/button>/g)],bn=buttons(projected),bo=buttons(prior);assert.equal(bn.length,bo.length);
  for(let k=bn.length-1;k>=0;k--){
    const tag=opening(bn[k][0]),oldTag=opening(bo[k][0]),action=attr(tag,'data-portal-action'),save=action==='document-operation-export-to-asset-vault';assert.ok(save||action==='document-operation-export-to-content-handoff');
    assert.equal(attr(tag,'data-portal-confirm'),esc(session,e[save?'docCardUiSaveConfirm':'docCardUiHandoffConfirm']));assert.equal(bn[k][1],esc(session,e[save?'docCardUiSaveToVault':'docCardUiSaveAndHandoff']));
    assert.equal(tag.replace(/data-portal-confirm="[^"]*"/,'data-portal-confirm="__APPROVED__"'),oldTag.replace(/data-portal-confirm="[^"]*"/,'data-portal-confirm="__APPROVED__"'));
    projected=projected.slice(0,bn[k].index)+bo[k][0]+projected.slice(bn[k].index+bn[k][0].length);
  }
  assert.equal(projected,prior,'Only approved text nodes and the exact two confirmation attrs may differ; filename/metrics/rawdate/structure/controls stay exact');
  assert.ok(next.includes('<h2 class="portal-card-title">'+esc(session,record.original_filename)+'</h2>'));assert.equal(next.includes('<script>'),false);
}
const pendingCases=[
  ['pdf_optimize','guarded','docPendingUiOptimizeGuarded'],['pdf_to_word_text','guarded','docPendingUiWordGuarded'],['pdf_ocr_word','guarded','docPendingUiOcrWordGuarded'],
  ['pdf_to_images','failed','docPendingUiImagesFailed'],['pdf_to_images','unavailable','docPendingUiImagesFailed'],['image_ocr','guarded','docPendingUiOcrTextGuarded'],['pdf_ocr','guarded','docPendingUiOcrTextGuarded'],
  ['pdf_split','failed','docPendingUiFailed'],['pdf_split','unavailable','docPendingUiFailed'],['pdf_split','processing','docPendingUiWaiting'],['pdf_split','UNKNOWN','docPendingUiWaiting']
];
for(const locale of ['vi','en','zh']){
  const {now,old}=sessions[locale],e=reviewed[locale];
  test(`${locale}: every seven pending branches is localized once; states, filenames, metrics and absent downloads stay exact`,()=>{
    assert.equal(new Set(pendingCases.map(row=>row[2])).size,7);
    for(const[kind,state,key]of pendingCases){const record=item(kind,2,{state,download_ready:false}),a=articles(render(now,[record]))[0],b=articles(render(old,[record]))[0];project(now,a,b,record,e,key);assert.equal(now.qa.documentOperationDownloadPath(record),'');}
    const record=item('pdf_split',1,{state:'processing',download_ready:false}),hostile='<img src=x onerror="alert(1)"> \'&',html=now.qa.withUiText((key,fallback)=>key.startsWith('docPendingUi')?hostile:fallback,()=>render(now,[record])),note=/<span class="portal-form-note">([\s\S]*?)<\/span>/.exec(html)?.[1];
    assert.equal(note,esc(now,hostile));assert.equal(note.includes('&amp;lt;img'),false);
  });
  test(`${locale}: all nine kinds, page-count coercions, strict readiness/rights and canonical links preserve actual behavior`,()=>{
    for(const kind of kinds)for(const pages of [1,3])for(const rights of [true,false,'true',undefined]){
      const record=item(kind,pages),a=articles(render(now,[record],rights))[0],b=articles(render(old,[record],rights))[0];project(now,a,b,record,e);
      assert.ok(a.includes('href="/api/v1/document-operations/'+id+'/download"'));const allowed=rights===true&&(kind!=='pdf_to_images'||pages===1);
      assert.equal(a.includes('data-portal-action="document-operation-export-to-asset-vault"'),allowed);assert.equal(a.includes('data-portal-action="document-operation-export-to-content-handoff"'),allowed&&kind!=='pdf_to_images');
    }
    for(const extra of [{download_ready:false},{download_ready:'true'},{download_ready:null},{id:'INVALID'},{state:'processing'},{download_url:'https://foreign.invalid/file',download_path:'/api/v1/document-operations/FOREIGN/download'}]){
      const record=item('pdf_split',1,extra),a=articles(render(now,[record]))[0],b=articles(render(old,[record]))[0],path=now.qa.documentOperationDownloadPath(record);project(now,a,b,record,e,path?undefined:'docPendingUiWaiting');assert.equal(path,old.qa.documentOperationDownloadPath(record));assert.equal(a.includes('https://foreign.invalid'),false);assert.equal(a.includes('/FOREIGN/download'),false);
    }
    for(const extra of [{source_page_count:'1',output_page_count:'1'},{source_page_count:2,output_page_count:1}]){
      const record=item('pdf_to_images',1,extra);project(now,articles(render(now,[record]))[0],articles(render(old,[record]))[0],record,e);
    }
    const records=kinds.map((kind,k)=>item(kind,1,{id:`${String(k+1).padStart(8,'0')}-1111-4111-8111-111111111111`,original_filename:k%2?e.docCardUiResultFile:literal})),a=articles(render(now,records)),b=articles(render(old,records));assert.equal(a.length,9);
    for(let k=0;k<records.length;k++){assert.equal(attr(opening(a[k]),'data-document-operation'),records[k].id);project(now,a[k],b[k],records[k],e);}
  });
  test(`${locale}: defaults/custom empty text, SAME-VM locale, VI fallback and exact ordered frozen 23-key catalogue remain`,()=>{
    const empty=render(now,[]);assert.ok(empty.includes('<h3>'+esc(now,e.docCardEmptyUiTitle)+'</h3>'));assert.ok(empty.includes('<p>'+esc(now,e.docCardEmptyUiBody)+'</p>'));
    const custom=['CUSTOMER '+e.docCardEmptyUiTitle+' <script>',literal];assert.equal(render(now,[],true,custom),render(old,[],true,custom));
    const record=item('pdf_merge'),next=locale==='vi'?'en':locale==='en'?'zh':'vi';try{now.setLocale(next);assert.ok(render(now,[]).includes(esc(now,reviewed[next].docCardEmptyUiTitle)));assert.ok(render(now,[record]).includes(esc(now,reviewed[next].docCardUiDownloadPdf)));}finally{now.setLocale(locale);}
    const fallback=now.qa.withUiText((key,value)=>value,()=>render(now,[record])),priorFallback=old.qa.withUiText((key,value)=>value,()=>render(old,[record]));project(now,articles(fallback)[0],articles(priorFallback)[0],record,reviewed.vi);
    const fallbackEmpty=now.qa.withUiText((key,value)=>value,()=>render(now,[]));assert.ok(fallbackEmpty.includes(esc(now,reviewed.vi.docCardEmptyUiBody)));
    const hostile='<img src=x onerror="alert(1)"> \'&',html=now.qa.withUiText((key,fallback)=>key.startsWith('docCard')?hostile:fallback,()=>render(now,[record]));
    assert.ok(html.includes('data-portal-confirm="'+esc(now,hostile)+'"'));assert.equal(html.includes('<img'),false);assert.equal(html.includes('&amp;lt;img'),false);
    const entries=Object.entries(now.messages[locale]),prior=Object.entries(old.messages[locale]);assert.equal(now[rawCatalogueFrozen][locale],true);assert.deepEqual(JSON.parse(JSON.stringify(entries.slice(0,prior.length))),JSON.parse(JSON.stringify(prior)));assert.deepEqual(JSON.parse(JSON.stringify(entries.slice(prior.length))),Object.entries(e));
    assert.deepEqual(JSON.parse(JSON.stringify(documentCardHistoricalSnapshot(entries,locale))),JSON.parse(JSON.stringify(prior)));
    for(const key of Object.keys(e)){assert.throws(()=>documentCardHistoricalSnapshot(entries.filter(([name])=>name!==key),locale),/Unreviewed document card copy/);assert.throws(()=>documentCardHistoricalSnapshot(entries.map(([name,value])=>[name,name===key?'UNREVIEWED':value]),locale),/Unreviewed document card copy/);}
    assert.throws(()=>documentCardHistoricalSnapshot([...prior,...Object.entries(e).toReversed()],locale),/Unreviewed document card copy/);assert.throws(()=>documentCardHistoricalSnapshot([...entries,['docCardUiUnknown','UNKNOWN']],locale),/Unreviewed document card copy/);
    const customer=['customer.filename',literal];assert.deepEqual(documentCardHistoricalSnapshot([...entries,customer],locale).at(-1),customer);
  });
}
test('complete two-file binding and exact three source chunks reject partial/unknown mutation without masking older scopes',()=>{
  assert.equal(hash(source.portal),reviewed.binding.candidatePortal);assert.equal(hash(source.i18n),reviewed.binding.candidateI18n);assert.equal(hash(baseline.portal),reviewed.binding.baselinePortal);assert.equal(hash(baseline.i18n),reviewed.binding.baselineI18n);
  assert.equal(documentCardHistoricalPortalSource(source.portal),baseline.portal);assert.equal(documentCardHistoricalPortalSource(baseline.portal),baseline.portal);
  for(const anchor of ['emptyTitle = uiText("docCardEmptyUiTitle"','const pendingMessage = ','const artifactLabel = ']){
    const start=source.portal.indexOf('  function renderDocumentOperationCards('),end=source.portal.indexOf('\n  function renderMediaHubPage(',start),part=source.portal.slice(start,end);assert.equal(part.split(anchor).length-1,1);
    assert.throws(()=>documentCardHistoricalPortalSource(source.portal.slice(0,start)+part.replace(anchor,anchor+'/* UNKNOWN */')+source.portal.slice(end)),/Unreviewed document card/);
  }
  const a=source.portal.indexOf('  function renderDocumentOperationCards('),b=source.portal.indexOf('\n  function renderMediaHubPage(',a);assert.throws(()=>documentCardHistoricalPortalSource(source.portal+source.portal.slice(a,b)),/Unreviewed document card/);
  const outside=source.portal+'\n// CUSTOMER Artifact provider Facebook TikTok';assert.notEqual(documentCardHistoricalPortalSource(outside),baseline.portal);assert.ok(documentCardHistoricalPortalSource(outside).endsWith('Facebook TikTok'));
  assert.equal(documentCardHistoricalI18nSource(source.i18n),baseline.i18n);assert.equal(documentCardHistoricalI18nSource(baseline.i18n),baseline.i18n);
  assert.throws(()=>documentCardHistoricalI18nSource(source.i18n.replace('docPendingUiOptimizeGuarded:','UNREVIEWED:')),/Unreviewed document card i18n/);
  const addition=source.i18n.slice(baseline.i18n.indexOf('  verifyEqualKeysets();'),source.i18n.indexOf('  verifyEqualKeysets();'));
  assert.throws(()=>documentCardHistoricalI18nSource(source.i18n+addition),/Unreviewed document card i18n/);
  assert.ok(documentCardHistoricalI18nSource(source.i18n+'\n// CUSTOMER Artifact Facebook').endsWith('CUSTOMER Artifact Facebook'));
});
