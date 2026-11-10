import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import test from 'node:test';
import vm from 'node:vm';
import {fileURLToPath} from 'node:url';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const portal=fs.readFileSync(path.join(root,'static/portal/portal.js'),'utf8');
const i18n=fs.readFileSync(path.join(root,'static/portal/portal-i18n.js'),'utf8');
const plain=s=>String(s).replace(/<svg\b[\s\S]*?<\/svg>/g,' ').replace(/<[^>]+>/g,' ').replace(/&(?:amp|quot|lt|gt|#39);/g,' ').replace(/\s+/g,' ').trim();
function render(locale){
  const noop=()=>{};
  const document={readyState:'loading',title:'',addEventListener:noop,querySelector:()=>null,querySelectorAll:()=>[],getElementById:()=>null,documentElement:{lang:locale,setAttribute:noop,getAttribute:()=>null,classList:{add:noop,remove:noop}},body:{classList:{add:noop,remove:noop,toggle:noop},setAttribute:noop}};
  const window={document,navigator:{language:locale,userAgent:'Publishing locale QA'},location:{pathname:'/publishing',search:'',href:'https://unit.invalid/publishing',origin:'https://unit.invalid'},addEventListener:noop,dispatchEvent:noop,CustomEvent:function(){},matchMedia:()=>({matches:false,addEventListener:noop}),localStorage:{getItem:()=>null,setItem:noop}};
  const sandbox=vm.createContext({window,document,navigator:window.navigator,URL,URLSearchParams,Intl,console,setTimeout:noop,clearTimeout:noop,fetch:()=>{throw Error('No network in renderer locale tests');}});
  vm.runInContext(i18n,sandbox);
  const marker='  window.TOANAASPortal = Object.freeze({';
  assert.ok(portal.includes(marker));
  vm.runInContext(portal.replace(marker,'  window.__APLocaleQA={renderAutoPostHub,normalizeBootstrap,documentTitle,renderHeader,renderSidebar,localizedNavigationLabel};\n'+marker),sandbox);
  window.TOANAASI18n.setLocale(locale,{emit:false});
  const context=window.__APLocaleQA.normalizeBootstrap({path:'/publishing',interfaceLocale:locale,profile:{locale,displayName:'QA'},session:{authenticated:true,csrfToken:'synthetic-publishing-qa'},capabilities:{}});
  const page=window.TOANAASPortal.resolvePage('/publishing');
  const html=window.__APLocaleQA.renderAutoPostHub(page,context);
  return {html,text:plain(html),title:window.__APLocaleQA.documentTitle(page,context),alias:window.__APLocaleQA.localizedNavigationLabel('AutoPost Hub'),header:plain(window.__APLocaleQA.renderHeader(page,context)),messages:window.TOANAASI18n.messages};
}

test('Vietnamese Publishing visible fixed copy is Vietnamese rather than product/developer English',()=>{
  const r=render('vi');
  assert.ok(r.text.includes('Đăng bài'),r.text);
  assert.doesNotMatch(r.text,/\b(?:AutoPost|Hub|Affiliate|Asset Vault|Campaign|Project|Web|hashtag|workspace|workflow|capability|provider|output|server|browser)\b/i);
  assert.ok(r.title.includes('Đăng bài'),r.title);
  assert.equal(r.alias,'Đăng bài');
  assert.doesNotMatch(r.header,/AutoPost|\bHub\b/i);
});
test('English Publishing keeps its English product title and source labels',()=>{
  const r=render('en');
  assert.ok(r.text.includes('Publishing'));
  assert.ok(r.title.includes('Publishing'));
  assert.equal(r.alias,'Publishing');
  assert.equal(r.messages.en['autopostHub.source.affiliate.title'],'Affiliate product');
});
test('Chinese Publishing title and fixed intro do not expose untranslated AutoPost Hub',()=>{
  const r=render('zh');
  assert.ok(r.text.includes('内容发布'),r.text);
  assert.ok(r.title.includes('内容发布'),r.title);
  assert.equal(r.alias,'内容发布');
  assert.doesNotMatch(r.text,/AutoPost|\bHub\b/);
});
test('Publishing locale presentation retains three real links without static permission/source or disabled external cards',()=>{
  for(const locale of ['vi','en','zh']){
    const {html}=render(locale);
    assert.equal(html.includes('data-autopost-source='),false);
    for(const link of ['/content/channel-strategy','/calendar','/content/publish-review'])assert.ok(html.includes('href="'+link+'"'));
    assert.equal((html.match(/type="button" disabled/g)||[]).length,0);
    assert.equal(html.includes('portal-autopost-steps'),false);
  }
});
