import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const source = fs.readFileSync('static/portal/portal-theme.js', 'utf8');
const ADMIN_KEY = 'toan-aas-admin-theme-v2';
const CUSTOMER_KEY = 'toan-aas-portal-theme';
function load(pathname, {search = '', dark = true, storage = new Map(), blocked = false} = {}) {
  const attrs = new Map(), events = [], media = {matches: dark, listener: null, addEventListener(_name, callback) { this.listener = callback; }};
  const root = {style:{}, setAttribute:(key,value)=>attrs.set(key,String(value)), getAttribute:key=>attrs.get(key), removeAttribute:key=>attrs.delete(key)};
  const metas=[{value:'',setAttribute(_key,value){this.value=value;}},{value:'',setAttribute(_key,value){this.value=value;}}];
  const document = {readyState:'complete',documentElement:root,body:{setAttribute(){}},querySelector:()=>metas[0],querySelectorAll:selector=>selector==='meta[name="theme-color"]'?metas:[],addEventListener(){}};
  const window = {document,location:{pathname,search},localStorage:{
    getItem(key){if(blocked)throw new Error('Storage unavailable');return storage.get(key)??null;},
    setItem(key,value){if(blocked)throw new Error('Storage unavailable');storage.set(key,String(value));},
    removeItem(key){if(blocked)throw new Error('Storage unavailable');storage.delete(key);}
  },matchMedia:()=>media,addEventListener(){},dispatchEvent:event=>events.push(event),CustomEvent:class{constructor(type,{detail}){this.type=type;this.detail=detail;}}};
  vm.runInNewContext(source, {window, URLSearchParams});
  return {theme:window.TOANAASPortalTheme,attrs,events,storage,metas,system(next){media.matches=next;media.listener?.();}};
}

for(const route of ['/admin','/admin/login']) {
  test(`${route}: default light is preserved without deleting a saved customer preference`,()=>{
    const h=load(route,{storage:new Map([[CUSTOMER_KEY,'dark']])});
    assert.equal(h.theme.getPreference(),'light'); assert.equal(h.theme.getResolvedTheme(),'light');
    assert.equal(h.storage.get(CUSTOMER_KEY),'dark');
  });
  test(`${route}: explicit dark query is applied before first paint`,()=>{
    const h=load(route,{search:'?theme=dark',dark:false});
    assert.equal(h.attrs.get('data-portal-theme'),'dark');
    assert.equal(h.attrs.get('data-portal-theme-preference'),'dark');
  });
  test(`${route}: saved admin dark preference survives load without being deleted`,()=>{
    const h=load(route,{storage:new Map([[ADMIN_KEY,'dark'],[CUSTOMER_KEY,'light']]),dark:false});
    assert.equal(h.theme.getResolvedTheme(),'dark'); assert.equal(h.storage.get(ADMIN_KEY),'dark');
    assert.equal(h.storage.get(CUSTOMER_KEY),'light');
  });
  test(`${route}: theme cycle and persistence use only the Admin key`,()=>{
    const storage=new Map([[CUSTOMER_KEY,'dark']]); const h=load(route,{storage});
    h.theme.toggle(); assert.equal(h.theme.getPreference(),'dark'); assert.equal(storage.get(ADMIN_KEY),'dark');
    h.theme.toggle(); assert.equal(h.theme.getPreference(),'system'); assert.equal(storage.get(ADMIN_KEY),'system');
    assert.equal(load(route,{storage,dark:false}).theme.getResolvedTheme(),'light');
    h.theme.toggle(); assert.equal(h.theme.getPreference(),'light'); assert.equal(storage.get(ADMIN_KEY),'light');
    assert.equal(storage.get(CUSTOMER_KEY),'dark');
  });
  test(`${route}: system preference follows media changes, explicit choice does not`,()=>{
    const h=load(route,{search:'?theme=system'}); assert.equal(h.theme.getResolvedTheme(),'dark');
    h.system(false); assert.equal(h.theme.getResolvedTheme(),'light');
    h.theme.setPreference('dark'); h.system(false); assert.equal(h.theme.getResolvedTheme(),'dark');
  });
  test(`${route}: storage denied still permits a volatile dark choice`,()=>{
    const h=load(route,{blocked:true}); assert.equal(h.theme.setPreference('dark'),'dark');
    assert.equal(h.theme.getPreference(),'dark');
  });
}

test('Customer preference and theme cycle remain isolated from Admin',()=>{
  const storage=new Map([[ADMIN_KEY,'dark']]); const h=load('/dashboard',{storage});
  assert.equal(h.theme.getPreference(),'system'); assert.equal(h.theme.getResolvedTheme(),'dark');
  h.theme.toggle(); assert.equal(storage.get(CUSTOMER_KEY),'light');
  h.theme.toggle(); assert.equal(storage.get(CUSTOMER_KEY),'dark');
  h.theme.toggle(); assert.equal(storage.has(CUSTOMER_KEY),false);
  assert.equal(storage.get(ADMIN_KEY),'dark');
});
test('Welcome default and customer auth defaults are unchanged',()=>{
  assert.equal(load('/welcome').theme.getPreference(),'light');
  assert.equal(load('/login').theme.getPreference(),'system');
  assert.equal(load('/administrator').theme.isAdminRoute(),false);
});
test('Unknown query/storage values do not become a theme or modify storage',()=>{
  const storage=new Map([[ADMIN_KEY,'invalid']]); const h=load('/admin',{search:'?theme=../../dark',storage});
  assert.equal(h.theme.getPreference(),'light'); assert.equal(h.theme.setPreference('invalid'),'light');
  assert.equal(storage.get(ADMIN_KEY),'invalid');
});
test('All media-specific Admin theme-color tags follow the chosen navy theme',()=>{
  const h=load('/admin',{search:'?theme=dark'});
  assert.deepEqual(h.metas.map(meta=>meta.value),['#0b132b','#0b132b']);
  h.theme.setPreference('light');assert.deepEqual(h.metas.map(meta=>meta.value),['#0d9488','#0d9488']);
});
test('Customer theme-color stays teal and both OS media tags agree with explicit choice',()=>{
  const h=load('/dashboard',{search:'?theme=dark'});
  assert.deepEqual(h.metas.map(meta=>meta.value),['#062026','#062026']);
});
