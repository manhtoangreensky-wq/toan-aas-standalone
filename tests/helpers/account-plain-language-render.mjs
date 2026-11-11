import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

// Real bundles in a network-free shell. Query states exercise the real notice branches.
export function renderPlainLanguage(locale, route, raw = {}, search = '', bundles = {}) {
  const noop = () => {};
  const document = {readyState:'loading', title:'', addEventListener:noop, querySelector:()=>null,
    querySelectorAll:()=>[], getElementById:()=>null,
    documentElement:{lang:locale,setAttribute:noop,getAttribute:()=>null,classList:{add:noop,remove:noop}},
    body:{classList:{add:noop,remove:noop,toggle:noop},setAttribute:noop}};
  const window = {document,navigator:{language:locale,userAgent:'Owned plain-language QA'},
    location:{pathname:route,search,href:'https://unit.invalid'+route+search,origin:'https://unit.invalid'},
    addEventListener:noop,dispatchEvent:noop,CustomEvent:function(){},
    matchMedia:()=>({matches:false,addEventListener:noop}),localStorage:{getItem:()=>null,setItem:noop}};
  const sandbox = vm.createContext({window,document,navigator:window.navigator,URL,URLSearchParams,Intl,console,
    setTimeout:noop,clearTimeout:noop,fetch:()=>{throw Error('No network in renderer tests');}});
  vm.runInContext(bundles.i18n ?? fs.readFileSync('static/portal/portal-i18n.js','utf8'),sandbox);
  const source=bundles.portal ?? fs.readFileSync('static/portal/portal.js','utf8');
  const anchor='  window.TOANAASPortal = Object.freeze({';
  assert.equal(source.split(anchor).length,2);
  vm.runInContext(source.replace(anchor,'  window.__plainLanguage={renderPage,normalizeBootstrap};\n'+anchor),sandbox);
  window.TOANAASI18n.setLocale(locale,{emit:false});
  const before=JSON.stringify(raw);
  const context=window.__plainLanguage.normalizeBootstrap({path:route,interfaceLocale:locale,
    profile:{locale,displayName:'OWNED_PROFILE'},session:{authenticated:true,csrfToken:'synthetic-local-only'},...raw});
  const html=window.__plainLanguage.renderPage(window.TOANAASPortal.resolvePage(route),context);
  assert.equal(JSON.stringify(raw),before,'Customer input is never translated or mutated');
  return {html,context,messages:window.TOANAASI18n.messages[locale]};
}

export function sectionWith(html, label) {
  const index=html.indexOf(label), start=html.lastIndexOf('<section',index);
  assert.ok(index>=0 && start>=0, 'Actual rendered section exists: '+label);
  let depth=0;
  for(const match of html.slice(start).matchAll(/<\/?section\b[^>]*>/g)){
    depth+=match[0].startsWith('</')?-1:1;
    if(depth===0)return html.slice(start,start+match.index+match[0].length);
  }
  throw Error('Rendered section has no matching closing tag: '+label);
}
