import assert from 'node:assert/strict';
import test from 'node:test';
import fs from 'node:fs';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {fileURLToPath,pathToFileURL} from 'node:url';

// Missing-note provenance is independent of display text. Real customer notes
// identical to a historical fallback must remain intact and safely escaped.
const ROOT=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const BASE='051096fb1e48223034ee3cc81674e18e8e63c003';
const helper=path.join(ROOT,'tests/helpers/publishing-child-render.mjs');
const {renderChild}=await import(pathToFileURL(helper).href);
let source=fs.readFileSync(helper,'utf8');
const replacements=[["const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');",'const root='+JSON.stringify(ROOT)+';']];
for(const [variable,file]of [['portal','static/portal/portal.js'],['i18n','static/portal/portal-i18n.js']])replacements.push([`const ${variable}=fs.readFileSync(path.join(root,'${file}'),'utf8');`,'const '+variable+'='+JSON.stringify(execFileSync('git',['show',BASE+':'+file],{cwd:ROOT,encoding:'utf8',maxBuffer:25e6}))+';']);
for(const [old,next]of replacements){assert.equal(source.split(old).length-1,1);source=source.replace(old,next);}
const {renderChild:renderBase}=await import('data:text/javascript;base64,'+Buffer.from(source).toString('base64'));
const row=(extra={})=>({code:'synthetic_origin',label:'SYNTHETIC_LABEL',...extra});
const custom='CUSTOMER canonical metadata signed-session note';
const identical='Gói canonical do Core Bridge cấp.';
const cases=[
 {name:'missing',monthly:[row()],notes:[null]},
 {name:'empty',monthly:[row({note:''})],notes:[null]},
 {name:'whitespace',monthly:[row({note:' \n '})],notes:[null]},
 {name:'object-note',monthly:[row({note:{text:custom}})],notes:[null]},
 {name:'nul-note',monthly:[row({note:'a\0b'})],notes:[null]},
 {name:'too-long-note',monthly:[row({note:'x'.repeat(241)})],notes:[null]},
 {name:'custom-technical',monthly:[row({note:custom})],notes:[custom]},
 {name:'provided-default-literal',monthly:[row({note:identical})],notes:[identical]},
 {name:'escaping',monthly:[row({note:'<script>alert(1)</script> & customer'})],notes:['&lt;script&gt;alert(1)&lt;/script&gt; &amp; customer']},
 {name:'legacy',monthly:[row({note:'Legacy hidden package kept for existing wallets/tests.'})],notes:['LEGACY_BASE']},
 {name:'duplicate-missing-first',monthly:[row(),row({note:custom})],notes:[null]},
 {name:'duplicate-note-first',monthly:[row({note:custom}),row()],notes:[custom]},
 {name:'invalid-predecessor',monthly:[row({code:'invalid code',note:custom}),row()],notes:[null]},
 {name:'combo-duplicate',monthly:[row()],combos:[row({note:custom})],notes:[null]},
 {name:'valid-combo',monthly:[],combos:[row({note:custom})],notes:[custom]},
 {name:'label-falls-back-to-code',monthly:[row({label:'',note:identical})],notes:[identical]},
 {name:'source-limit',monthly:[...Array.from({length:100},()=>({code:'invalid code',note:custom})),row({note:custom})],notes:[]},
 {name:'same-code-distinct-labels',monthly:[row(),row({label:'OTHER_LABEL',note:custom})],notes:[null,custom]},
 {name:'trimmed-identity',monthly:[row({code:' synthetic_origin ',label:' SYNTHETIC_LABEL ',note:custom}),row()],notes:[custom]},
 {name:'maximum-valid-note',monthly:[row({note:'x'.repeat(240)})],notes:['x'.repeat(240)]}
];
const cards=html=>[...html.matchAll(/<article class="portal-module-card portal-billing-catalog-card">[\s\S]*?<\/article>/g)].map(match=>{
 const fragment=match[0],family=/<span class="portal-billing-catalog-family">([^<]*)<\/span>/.exec(fragment)?.[1];
 const note=/<h3>[^<]*<\/h3><p>([\s\S]*?)<\/p>/.exec(fragment);
 return{fragment,family,note:note?.[1]??null};
});
function finiteMarkup(html){
 return html.replace(/(<span class="portal-billing-catalog-family">)[^<]*(<\/span>)/g,'$1__LOCALIZED_FAMILY__$2')
  .replace(/(<h3>[^<]*<\/h3>)<p>[\s\S]*?<\/p>/g,'$1');
}
const controlTags=html=>[...html.matchAll(/<(?:a|button|input|form|select|textarea|option)\b[^>]*>/g)].map(match=>match[0]);
for(const locale of ['vi','en','zh'])for(const scenario of cases)test(locale+'/'+scenario.name+': origin-aware note/category changes preserve every unrelated value and control',()=>{
 const raw={wallet:{balance_xu:0,total_spent_xu:0,is_vip:false,plan:{plan_name:'CUSTOMER_PLAN',plan_status:'CUSTOMER_STATUS'}},packageCatalog:{available:true,monthly:structuredClone(scenario.monthly),combos:structuredClone(scenario.combos||[])},pricingCatalog:{available:true,image_tiers:[],video_tiers:[],video_combos:[],public_sale_catalog:{available:true,approval_status:'owner_approved',catalog_version:'synthetic_origin_v1',items:[{code:'synthetic_origin',family:'service',label:'SYNTHETIC_LABEL',sale_price_xu:425}]}}};
 const before=structuredClone(raw),current=renderChild(locale,'/membership',raw),baseline=renderBase(locale,'/membership',structuredClone(raw));
 assert.deepEqual(raw,before);assert.equal(JSON.stringify(current.context),JSON.stringify(baseline.context));
 assert.deepEqual(controlTags(current.html),controlTags(baseline.html));
 assert.equal(finiteMarkup(current.html),finiteMarkup(baseline.html),'every unrelated HTML byte stays unchanged');
 assert.ok(current.html.includes('CUSTOMER_PLAN')&&current.html.includes('CUSTOMER_STATUS')&&current.html.includes('0 Xu'));
 const actual=cards(current.html),old=cards(baseline.html);assert.equal(actual.length,scenario.notes.length);assert.equal(actual.length,old.length);
 for(const [index,card]of actual.entries()){
  const expected=scenario.notes[index]==='LEGACY_BASE'?old[index].note:scenario.notes[index];
  assert.equal(card.note,expected,'only the first accepted original valid note may have a paragraph');
  const pattern=locale==='vi'?/gói(?: dịch vụ)?/i:locale==='en'?/\b(?:service\s+)?packages?\b/i:/套餐|服务/;
  assert.match(card.family,pattern,'default category follows selected locale');
  if(locale!=='vi')assert.notEqual(card.family,'Gói dịch vụ');
  assert.ok(card.fragment.includes('425 Xu'),'approved real price stays visible');
 }
});
