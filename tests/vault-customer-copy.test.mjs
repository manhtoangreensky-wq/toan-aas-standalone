// Full physical-bundle UI acceptance only; no native, blob, mutation or LIVE proof.
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {vaultHintContrastHistoricalCss} from './helpers/vault-hint-contrast-snapshot.mjs';
Error.stackTraceLimit=0;
const R=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const BASE='5b11e63f178b4ff81c4546462a8cb3ddcdc99fb5',rawDesign=fs.readFileSync(new URL('./fixtures/vault-customer-copy-reviewed.json',import.meta.url));
const hash=x=>createHash('sha256').update(x).digest('hex'),lf=x=>x.replace(/\r\n/g,'\n'),count=(s,p)=>s.split(p).length-1;
assert.equal(hash(rawDesign),'2b895f84f77c8656811c4e732506926a677dda1eb6aa824f854670e127e8228b');
const reviewed=JSON.parse(rawDesign),design={...reviewed,allRows:reviewed.rows},words=(key,locale,params={})=>{const row=design.allRows.find(row=>row[0]===key);assert.ok(row,key);let value=row[['vi','en','zh'].indexOf(locale)+1];for(const[k,v]of Object.entries(params))value=value.replaceAll('{'+k+'}',String(v));return value;};
let loader=fs.readFileSync(path.join(R,'tests/helpers/chat-page-meta-runtime.mjs'),'utf8');
for(const[old,next]of [["\nconst root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');",'\nconst root='+JSON.stringify(R)+';'],
 ['supportTicketHeroSection,resolvePage,safeText,withUiText:','supportTicketHeroSection,resolvePage,safeText,assetVaultFilterFields,assetVaultFormFields,renderAssetVaultPagination,assetVaultLifecyclePanel,renderAssetVault,withUiText:']]){
 assert.equal(count(loader,old),1,'Exact test-local five-function exposure');loader=loader.replace(old,()=>next);
}
const{pageMetaSources,pageMetaRenderer}=await import('data:text/javascript;base64,'+Buffer.from(loader).toString('base64'));
const physical=pageMetaSources(),files={portal:'static/portal/portal.js',i18n:'static/portal/portal-i18n.js',pages:'copyfast_pages.py'};
const baseline=Object.fromEntries(Object.entries(files).map(([key,file])=>[key,lf(execFileSync('git',['show',BASE+':'+file],{cwd:R,encoding:'utf8',maxBuffer:30e6}))]));
// Actual renderer always receives complete current physical source, not the design candidate or an inverse.
const actual=await pageMetaRenderer(physical),before=await pageMetaRenderer(baseline);
const IDs=['11111111-1111-4111-8111-111111111111','22222222-2222-4222-8222-222222222222','33333333-3333-4333-8333-333333333333','44444444-4444-4444-8444-444444444444'];
const PROJECT='55555555-5555-4555-8555-555555555555',UNKNOWN_PROJECT='66666666-6666-4666-8666-666666666666';
const CUSTOMER='CUSTOMER media studio provider Facebook TikTok <img src=x onerror="literal">&',DATE='2026-11-18T03:04:05Z';
const ACCEPT='.jpg,.jpeg,.png,.webp,.mp4,.mov,.webm,.mp3,.wav,.m4a,.ogg,.pdf,.txt,.srt,.vtt,.docx';
const capabilityNames=['view','upload','archive','refresh','lifecycle-view','restore'];
const referenceNames=['support_evidence_retention','media_library_reference','image_direction_reference','document_plan_reference','document_operation_source','document_operation_input','image_operation_source'];
const referenceKeys=['Support','Audio','Image','Document','DocumentSource','DocumentInput','ImageSource'];
const esc=s=>String(s).replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
const plain=x=>JSON.parse(JSON.stringify(x)),freeze=x=>{if(x&&typeof x==='object'&&!Object.isFrozen(x)){Object.values(x).forEach(freeze);Object.freeze(x);}return x;};
function item(id=IDs[0],state='active',overrides={}){return{id,state,display_name:CUSTOMER,original_filename:CUSTOMER+'.pdf',extension:'.pdf',byte_size:1024,project_id:PROJECT,updated_at:DATE,...overrides};}
function lifecycle(state='archived',overrides={}){return{state,state_reason:state==='active'?'available':state==='archived'?'owner_archived':'integrity_unavailable',lifecycle_revision:2,restore_available:state==='archived',created_at:DATE,updated_at:DATE,archived_at:DATE,reference_summary:{total_count:7,hard_blocker_count:2,references:referenceNames.map((reason,i)=>({reason,count:1,hard_blocker:i<2}))},...overrides};}
function context(overrides={}){
 return freeze({assetVaultEnabled:true,assetVaultReadState:'ready',capabilities:Object.fromEntries(capabilityNames.map(name=>['asset-vault-'+name,true])),projects:[{id:PROJECT,title:CUSTOMER+' PROJECT',state:'active'}],
  vaultItems:[item(),item(IDs[1],'archived',{project_id:null})],assetVaultListing:{filters:{q:'',state:'active'},pagination:{limit:50,offset:0,returned:2,has_more:false,next_offset:null,previous_offset:null}},...overrides});
}
function render(renderer,locale,overrides={},route='/asset-vault'){
 const raw=context(overrides),saved=JSON.stringify(raw);let result;try{result=renderer(locale,route,raw);}catch(e){throw Error((e.name+': '+e.message).slice(0,400));}
 assert.equal(JSON.stringify(raw),saved,'Frozen customer/request context unchanged');return result;
}
const controls=html=>[...html.matchAll(/<(?:form|button|input|select|textarea|option|a)\b[^>]*>/g)].map(m=>m[0].replace(/\b(data-portal-confirm|title|placeholder|aria-label)="[^"]*"/g,(_,name)=>name+'="DECLARED_COPY"')).sort();
const button=(html,action)=>html.match(new RegExp('<button\\b[^>]*data-portal-action="'+action+'"[^>]*>','g'))||[];
const withoutAside=html=>html.replace(/<aside\b[\s\S]*?<\/aside>/g,'');
const has=(html,text,label=text)=>assert.ok(html.includes(esc(text)),label);
const noBrokenMarkup=html=>{assert.ok(!html.includes('uiText(')&&!html.includes('${safeText'),'No inert interpolation');assert.doesNotMatch(html,/<(?:section|aside)\b[^>]*>\s*<\/(?:section|aside)>/);};
function panel(renderer,locale,source,items=[item()],canRestore=true){const r=render(renderer,locale);const input=freeze({assetVaultLifecycle:source}),saved=JSON.stringify(input),html=r.qa.assetVaultLifecyclePanel(input,freeze(items),canRestore);assert.equal(JSON.stringify(input),saved);return html;}
for(const locale of ['vi','en','zh']){
 const w=(key,params)=>words(key,locale,params);
 test(locale+': fields keep names constraints options IDs filter namespace and upload defaults while all copy is localized',()=>{
  const now=render(actual,locale),old=render(before,locale),filters=plain(now.qa.assetVaultFilterFields()),forms=plain(now.qa.assetVaultFormFields()),priorFilters=plain(old.qa.assetVaultFilterFields()),priorForms=plain(old.qa.assetVaultFormFields());
  assert.equal(filters[0].label,w('vaultFieldsUiSearch'));assert.equal(filters[0].placeholder,w('vaultFieldsUiPlaceholder'));assert.equal(filters[1].label,w('vaultFieldsUiState'));
  assert.deepEqual(filters[1].options,[['active',w('vaultFieldsUiActive')],['archived',w('vaultFieldsUiArchived')],['all',w('vaultFieldsUiAll')]]);
  for(const[index,keys]of [[0,['DisplayName','NamePlaceholder','NameHelp']],[1,['Project','NoProject','ProjectHelp']]])for(const[key,suffix]of [['label',keys[0]],[index===0?'placeholder':'emptyLabel',keys[1]],['help',keys[2]]])assert.equal(forms[index][key],w('vaultFieldsUi'+suffix));
  for(const list of [filters,forms,priorFilters,priorForms])for(const field of list){for(const key of ['label','placeholder','emptyLabel','help'])delete field[key];if(field.options)field.options=field.options.map(([code])=>code);}
  assert.deepEqual(filters,priorFilters);assert.deepEqual(forms,priorForms);assert.deepEqual(filters.map(f=>f.name),['q','state']);assert.equal(filters[0].maxLength,100);assert.equal(forms[0].maxLength,120);assert.equal(forms[1].optionsFrom,'projects');
  for(const form of forms)assert.ok(!Object.hasOwn(form,'defaultValue'),'No added upload draft default');
  const file=now.html.match(/<input\b[^>]*name="file"[^>]*>/)?.[0];assert.ok(file?.includes('id="portal-vault-file"')&&file.includes('type="file"')&&file.includes('accept="'+ACCEPT+'"')&&file.includes(' required'));assert.ok(!file.includes('multiple'));
  for(const id of ['portal-field-display_name','portal-field-project_id','portal-field-asset-vault-filter-q','portal-field-asset-vault-filter-state'])assert.equal(count(now.html,'id="'+id+'"'),1);
  assert.ok(now.html.match(/<form\b[^>]*data-portal-no-transient[^>]*data-portal-action="asset-vault-filter"/));has(now.html,w('vaultPageUiFileHelp'));assert.ok(w('vaultPageUiFileHelp').includes('25 MB'));
 });
 test(locale+': main ready empty filtered and guard states retain useful forms/nav with localized metadata and no technical-only wrapper',()=>{
  const now=render(actual,locale),old=render(before,locale);for(const key of ['Title','Description','UploadTitle','UploadHelp','ChooseFile','FileHelp','UploadNote','Upload','LibraryTitle','LibraryHelp','Refresh','FilterHint','Clear','Find'])has(now.html,w('vaultPageUi'+key));
  assert.equal(now.title,w('vaultPageUiTitle')+' · TOAN AAS');assert.equal(now.qa.localizedPageDescription(now.page),w('vaultPageUiDescription'));has(now.qa.renderHeader(now.page,now.context),w('vaultPageUiTitle'));
  assert.doesNotMatch(now.html,/portal-vault-intro|portal-vault-layout|<aside\b|portal-state-meta/);assert.ok(now.html.includes('href="/assets"'));assert.equal(count(now.html,'href="/assets"'),count(old.html,'href="/assets"')-1,'Only duplicate aside link removed; delivery navigation kept');noBrokenMarkup(now.html);
  const empty=render(actual,locale,{vaultItems:[]});has(empty.html,w('vaultCardsUiEmptyTitle'));has(empty.html,w('vaultCardsUiEmptyBody'));assert.ok(empty.html.includes('asset-vault-upload'));
  const filtered=render(actual,locale,{vaultItems:[],assetVaultListing:{filters:{q:'CUSTOMER_FILTER',state:'all'},pagination:{}}});has(filtered.html,w('vaultCardsUiFilteredTitle'));has(filtered.html,w('vaultCardsUiFilteredBody'));
  for(const value of [false,'true',undefined]){const caps=Object.fromEntries(capabilityNames.map(n=>['asset-vault-'+n,true]));caps['asset-vault-view']=value;const guarded=render(actual,locale,{capabilities:caps});assert.ok(!guarded.html.includes('<form'));has(guarded.html,w('vaultPageUiGuardTitle'));has(guarded.html,w('vaultPageUiGuardBody'));assert.ok(guarded.html.includes('href="/assets"'));noBrokenMarkup(guarded.html);}
 });
 test(locale+': active/archive cards localize fixed status actions fallbacks and confirmations without changing download eligibility',()=>{
  const now=render(actual,locale),old=render(before,locale);assert.deepEqual(controls(now.html),controls(withoutAside(old.html)),'Retained controls apart from redundant aside link');
  for(const key of ['Inspect','Download','Archive','ArchivedNote','Size','Project','Updated'])has(now.html,w('vaultCardsUi'+key));
  assert.equal(count(now.html,'href="/api/v1/asset-vault/'+IDs[0]+'/download"'),1);assert.equal(count(now.html,'href="/api/v1/asset-vault/'+IDs[1]+'/download"'),0);assert.equal(button(now.html,'asset-vault-lifecycle-open').length,2);assert.equal(button(now.html,'asset-vault-archive').length,1);
  assert.ok(now.html.includes('data-portal-confirm="'+esc(w('vaultCardsUiArchiveConfirm'))+'"'));
  const fallback=render(actual,locale,{vaultItems:[item(IDs[2],'active',{display_name:'',original_filename:'',extension:'',project_id:UNKNOWN_PROJECT}),item(IDs[3],'active',{display_name:'Named',project_id:null})]});for(const key of ['FileType','FileName','OriginalName','LinkedProject','NoProject'])has(fallback.html,key==='FileType'?w('vaultCardsUi'+key).toUpperCase():w('vaultCardsUi'+key));
  const invalid=render(actual,locale,{vaultItems:[item('not-a-uuid'),item(IDs[2],'unavailable')]});has(invalid.html,w('vaultCardsUiEmptyTitle'));assert.equal(button(invalid.html,'asset-vault-lifecycle-open').length,0);assert.ok(!invalid.html.includes('/not-a-uuid/download'));
 });
 test(locale+': pager translates range aria and directions and keeps middle/first/last/no-more/invalid offset guards',()=>{
  const a=render(actual,locale),b=render(before,locale);const cases=[
   [{offset:50,returned:2,previous_offset:0,has_more:true,next_offset:100},[0,100],['51','52']],
   [{offset:0,returned:2,previous_offset:null,has_more:true,next_offset:50},[50],['1','2']],
   [{offset:100,returned:2,previous_offset:50,has_more:false,next_offset:150},[50],['101','102']],
   [{offset:100,returned:0,previous_offset:50,has_more:false,next_offset:null},[50],null],
   [{offset:0,returned:0,previous_offset:null,has_more:false,next_offset:null},[],null],
   [{offset:50,returned:2,previous_offset:-1,has_more:'true',next_offset:100},[],null],
   [{offset:'bad',returned:'bad',previous_offset:0,has_more:true,next_offset:1.5},[0],null],
   [{offset:50,returned:2,previous_offset:'0',has_more:true,next_offset:50},[],null]
  ];for(const[pagination,offsets,range]of cases){const input=freeze({pagination}),saved=JSON.stringify(input),html=a.qa.renderAssetVaultPagination(input),prior=b.qa.renderAssetVaultPagination(input);assert.equal(JSON.stringify(input),saved);assert.deepEqual(controls(html),controls(prior));assert.deepEqual([...html.matchAll(/data-asset-vault-offset="(\d+)"/g)].map(m=>Number(m[1])),offsets);if(!offsets.length){assert.equal(html,'');continue;}assert.ok(html.includes('aria-label="'+esc(w('vaultCardsUiAria'))+'"'));has(html,range?w('vaultCardsUiRange',{start:range[0],end:range[1]}):w('vaultCardsUiEmptyPage'));if(offsets.length===2||pagination.previous_offset===offsets[0])has(html,w('vaultCardsUiPrevious'));if(pagination.has_more===true&&Number.isInteger(pagination.next_offset)&&pagination.next_offset>(Number.isInteger(pagination.offset)?pagination.offset:0))has(html,w('vaultCardsUiNext'));}
 });
 test(locale+': lifecycle loading/guarded/failed stays useful and translated with close, no restore and no stale placeholder',()=>{
  for(const state of ['loading','guarded','failed']){const source={asset_id:IDs[0],readState:state,lifecycle:null},html=panel(actual,locale,source),prior=panel(before,locale,source);has(html,w('vaultLifecycleUiHeading',{name:CUSTOMER}));has(html,w(state==='loading'?'vaultLifecycleUiLoading':'vaultLifecycleUiFailed'));has(html,w(state==='loading'?'vaultLifecycleUiLoadingBody':'vaultLifecycleUiFailedBody'));has(html,w('vaultLifecycleUiClose'));assert.deepEqual(controls(html),controls(prior));assert.equal(button(html,'asset-vault-lifecycle-close').length,1);assert.equal(button(html,'asset-vault-lifecycle-restore').length,0);noBrokenMarkup(html);}
  for(const asset_id of ['',undefined,'bad-uuid'])assert.equal(panel(actual,locale,{asset_id,readState:'ready',lifecycle:lifecycle()}),'');
 });
 test(locale+': ready lifecycle preserves states reasons references counts blockers revision restore guards and raw dates',()=>{
  for(const state of ['active','archived','unavailable']){const source={asset_id:IDs[0],readState:'ready',lifecycle:lifecycle(state)},html=panel(actual,locale,source),prior=panel(before,locale,source);has(html,w('vaultLifecycleUi'+({active:'Active',archived:'Archived',unavailable:'Unavailable'}[state])));has(html,w('vaultLifecycleUi'+({active:'AvailableReason',archived:'ArchivedReason',unavailable:'IntegrityReason'}[state])));has(html,w('vaultLifecycleUiReferenceSummary',{count:'7',required:'2'}));for(const key of referenceKeys)has(html,w('vaultLifecycleUi'+key));has(html,w('vaultLifecycleUiReferenceCount',{count:'1'}));has(html,DATE);assert.deepEqual(controls(html),controls(prior));assert.equal(button(html,'asset-vault-lifecycle-restore').length,state==='archived'?1:0);if(state==='archived')assert.ok(html.includes('data-portal-confirm="'+esc(w('vaultLifecycleUiRestoreConfirm'))+'"'));else has(html,w(state==='active'?'vaultLifecycleUiNoRestoreNeeded':'vaultLifecycleUiRestoreUnavailable'));}
  for(const revision of [undefined,0,1.5]){const source={asset_id:IDs[0],readState:'ready',lifecycle:lifecycle('archived',{lifecycle_revision:revision})},html=panel(actual,locale,source);assert.equal(button(html,'asset-vault-lifecycle-restore').length,0);assert.deepEqual(controls(html),controls(panel(before,locale,source)));}
  for(const value of [false,'true']){const caps=Object.fromEntries(capabilityNames.map(n=>['asset-vault-'+n,true]));caps['asset-vault-restore']=value;const html=render(actual,locale,{capabilities:caps,assetVaultLifecycle:{asset_id:IDs[0],readState:'ready',lifecycle:lifecycle()}}).html,restore=button(html,'asset-vault-lifecycle-restore')[0];assert.ok(restore?.includes(' disabled'));assert.ok(restore.includes('title="'+esc(w('vaultLifecycleUiRestoreDisabled'))+'"'));}
  for(const extra of [{restore_available:false},{restore_available:'true'},{reference_summary:{total_count:0,hard_blocker_count:0,references:[]}}]){const source={asset_id:IDs[0],readState:'ready',lifecycle:lifecycle('archived',extra)},html=panel(actual,locale,source);assert.deepEqual(controls(html),controls(panel(before,locale,source)));if(Object.hasOwn(extra,'restore_available'))assert.equal(button(html,'asset-vault-lifecycle-restore').length,0);else has(html,w('vaultLifecycleUiNoReferences'));}
  for(const reference_summary of [{total_count:1,hard_blocker_count:2,references:[]},{total_count:1,hard_blocker_count:0,references:[{reason:'UNKNOWN_REFERENCE',count:1}]},{total_count:2,hard_blocker_count:0,references:[{reason:referenceNames[0],count:1},{reason:referenceNames[0],count:1}]}]){const source={asset_id:IDs[0],readState:'ready',lifecycle:lifecycle('archived',{reference_summary})},now=render(actual,locale,{assetVaultLifecycle:source}),old=render(before,locale,{assetVaultLifecycle:source});assert.equal(now.context.assetVaultLifecycle.readState,'guarded');assert.deepEqual(controls(now.html),controls(withoutAside(old.html)));assert.equal(button(now.html,'asset-vault-lifecycle-restore').length,0);}
 });
 test(locale+': all six capabilities remain strict booleans and retain precise control eligibility and disabled copy',()=>{
  for(const name of capabilityNames)for(const value of [false,'true',undefined]){const caps=Object.fromEntries(capabilityNames.map(n=>['asset-vault-'+n,true]));caps['asset-vault-'+name]=value;const extra={capabilities:caps,assetVaultLifecycle:{asset_id:IDs[0],readState:'ready',lifecycle:lifecycle()}},now=render(actual,locale,extra),old=render(before,locale,extra);
   // Compare all real controls except the single removed duplicate aside link.
   assert.deepEqual(controls(now.html),controls(withoutAside(old.html)));
   if(name==='view'){assert.ok(!now.html.includes('<form'));continue;}if(name==='upload'){assert.ok(now.html.match(/<input\b[^>]*name="file"[^>]*>/)[0].includes(' disabled'));}
   if(name==='archive')assert.ok(button(now.html,'asset-vault-archive').every(tag=>tag.includes(' disabled')));if(name==='refresh')assert.ok(button(now.html,'asset-vault-refresh')[0].includes(' disabled'));
   if(name==='lifecycle-view')for(const tag of button(now.html,'asset-vault-lifecycle-open')){assert.ok(tag.includes(' disabled'));assert.ok(tag.includes('title="'+esc(w('vaultCardsUiInspectDisabled'))+'"'));}
   if(name==='restore')assert.ok(button(now.html,'asset-vault-lifecycle-restore')[0].includes(' disabled'));
  }
 });
 test(locale+': customer filenames project labels raw dates and context stay escaped literal and immutable',()=>{
  const input=context({assetVaultLifecycle:{asset_id:IDs[0],readState:'ready',lifecycle:lifecycle()}}),snapshot=JSON.stringify(input),now=actual(locale,'/asset-vault',input);assert.equal(JSON.stringify(input),snapshot);has(now.html,CUSTOMER);has(now.html,CUSTOMER+'.pdf');has(now.html,CUSTOMER+' PROJECT');has(now.html,DATE);assert.ok(!now.html.includes('<img src=x'));
  const source=freeze({asset_id:IDs[0],readState:'ready',lifecycle:lifecycle('archived',{updated_at:'RAW media studio provider date'})}),html=panel(actual,locale,source);has(html,'RAW media studio provider date');assert.ok(html.includes(esc(CUSTOMER)));assert.ok(!html.includes('&amp;lt;img'));assert.equal(input.vaultItems[0].display_name,CUSTOMER);
 });
}
test('nine prior OCR/PDF/Image routes remain whole physical HTML/title/context identical to delivered BASE',()=>{
 for(const route of ['/documents/ocr','/documents/pdf-ocr','/documents/pdf-ocr-to-word','/documents/pdf-to-images','/documents/pdf-to-word','/documents/compress','/image/edit','/image/history','/image/resize'])for(const locale of ['vi','en','zh']){const now=render(actual,locale,{},route),old=render(before,locale,{},route);assert.equal(now.html,old.html,route+'/'+locale);assert.equal(now.title,old.title);assert.equal(JSON.stringify(now.context),JSON.stringify(old.context));}
});
test('render-only Vault flows complete behind the existing throwing network guard without any action submission',()=>{
 for(const locale of ['vi','en','zh'])for(const assetVaultReadState of ['loading','failed','ready'])assert.doesNotThrow(()=>render(actual,locale,{assetVaultReadState}));
});
test('immutable reviewed design identity binds90rows12edits151sources with3changed148protected and no app writes',()=>{
 assert.equal(design.task,'ASSET-VAULT-CUSTOMER-COPY-20261119');assert.equal(design.base,BASE);assert.equal(design.applicationWrites,0);assert.equal(design.allRows.length,90);assert.equal(new Set(design.allRows.map(row=>row[0])).size,90);assert.equal(design.canonicalChanges.length,12);assert.ok(design.canonicalChanges.every(change=>change.count===1));assert.equal(design.applicationBaseline.length,151);assert.equal(design.applicationBaseline.filter(pin=>pin.changed).length,3);
 for(const pin of design.applicationBaseline){const actualSource=lf(fs.readFileSync(path.join(R,pin.file),'utf8'));assert.ok([pin.baselineLfSha256,pin.candidateLfSha256].includes(hash(vaultHintContrastHistoricalCss(actualSource,pin.file))),pin.file);if(!pin.changed)assert.equal(pin.baselineLfSha256,pin.candidateLfSha256);}
});
