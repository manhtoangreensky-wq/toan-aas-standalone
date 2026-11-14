import assert from 'node:assert/strict';
import test from 'node:test';
import fs from 'node:fs';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {withoutLegacyDecorativeWorkbench} from './helpers/legacy-decorative-workbench.mjs';

// Catch the fixed AI Studio label leaking into VI/ZH, or a broad replacement
// that translates customer/unknown labels instead of adding one finite alias.
const ROOT=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const BASE='c4da5f4a90a4ca37c46b66220c81928b806a4f2a';
async function actualHelper(revision){
  let source=fs.readFileSync(path.join(ROOT,'tests/helpers/publishing-child-render.mjs'),'utf8');
  const edits=[
    ["const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');",'const root='+JSON.stringify(ROOT)+';'],
    ['window.__childLocale={renderPage,normalizeBootstrap,','window.__childLocale={renderPage,localizedNavigationLabel,normalizeBootstrap,'],
    ['return {html,text:plain(html),','return {localizeNavigationLabel:window.__childLocale.localizedNavigationLabel,html,text:plain(html),']
  ];
  if(revision)for(const [name,file]of [['portal','static/portal/portal.js'],['i18n','static/portal/portal-i18n.js']]){
    const text=execFileSync('git',['show',revision+':'+file],{cwd:ROOT,encoding:'utf8',maxBuffer:30e6});
    edits.push([`const ${name}=fs.readFileSync(path.join(root,'${file}'),'utf8');`,'const '+name+'='+JSON.stringify(text)+';']);
  }
  for(const [old,next]of edits){assert.equal(source.split(old).length-1,1);source=source.replace(old,next);}
  return (await import('data:text/javascript;base64,'+Buffer.from(source).toString('base64'))).renderChild;
}
const renderCurrent=await actualHelper(),renderBase=await actualHelper(BASE);
const controls=html=>[...html.matchAll(/<(?:a|button|input|form|select|textarea|option)\b[^>]*>/g)].map(m=>m[0]);
const labels={vi:'Xưởng sáng tạo AI',en:'AI Studios',zh:'AI 创作工坊'};
const routes=['/features',...['content','image','video','voice','music','subtitle','documents'].map(key=>'/features/'+key)];
for(const locale of ['vi','en','zh'])for(const route of routes)test(`${locale}${route}: fixed AI Studio hero alias follows locale without translating data or changing controls`,()=>{
  const raw={profile:{locale,displayName:'CUSTOMER AI Studio'},capabilities:{}},saved=structuredClone(raw);
  const current=renderCurrent(locale,route,raw),old=renderBase(locale,route,structuredClone(raw));
  const oldHtml=withoutLegacyDecorativeWorkbench(old.html).html;
  const eyebrow=/<div class="portal-eyebrow">([^<]*)<\/div>/,previous=eyebrow.exec(old.html),actual=eyebrow.exec(current.html);
  assert.ok(previous&&actual);assert.equal(previous[1],'AI Studio','BASE really reproduces the fixed-label leak');
  assert.deepEqual(raw,saved);assert.equal(JSON.stringify(current.context),JSON.stringify(old.context));
  assert.deepEqual(controls(current.html),controls(oldHtml));
  assert.equal(current.messages[locale]['shellNav.aiStudios'],labels[locale],'reuse the reviewed existing translation');
  assert.equal(actual[1],labels[locale]);
  assert.equal(current.html,oldHtml.replace(previous[0],'<div class="portal-eyebrow">'+labels[locale]+'</div>'),'only accepted alias and independently verified legacy decoration removal');
});
for(const locale of ['vi','en','zh'])test(`${locale}: finite alias addition never rewrites unknown or customer labels`,()=>{
  const result=renderCurrent(locale,'/features',{});
  for(const label of ['CUSTOMER Studio','Customer AI Studio','TIKTOK_CUSTOM_NAME','<script>alert(1)</script>']){
    assert.equal(result.localizeNavigationLabel(label),label);
  }
});
