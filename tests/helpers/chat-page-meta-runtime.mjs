import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
export const PAGE_META_BASE='0e97fd8a39950b67e7a6b68a2bf17aa8d3cece01';
const files={portal:'static/portal/portal.js',i18n:'static/portal/portal-i18n.js',pages:'copyfast_pages.py'};
export function pageMetaSources(historical=false){
  return Object.fromEntries(Object.entries(files).map(([key,file])=>[key,(historical?execFileSync('git',['show',PAGE_META_BASE+':'+file],{cwd:root,encoding:'utf8',maxBuffer:30e6}):fs.readFileSync(path.join(root,file),'utf8')).replace(/\r\n/g,'\n')]));
}
export async function pageMetaRenderer(sources=pageMetaSources()){
  let helper=fs.readFileSync(path.join(root,'tests/helpers/publishing-child-render.mjs'),'utf8');
  const once=(old,next)=>{assert.equal(helper.split(old).length-1,1,'Exact existing renderer exposure');helper=helper.replace(old,next);};
  once("const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');",'const root='+JSON.stringify(root)+';');
  for(const key of ['portal','i18n'])once("const "+key+"=fs.readFileSync(path.join(root,'"+files[key]+"'),'utf8');",'const '+key+'='+JSON.stringify(sources[key])+';');
  once('window.__childLocale={renderPage,','window.__childLocale={renderHeader,localizedPageTitle,localizedPageDescription,supportTicketHeroSection,resolvePage,safeText,withUiText:(fn,run)=>{const old=uiText;try{uiText=fn;return run();}finally{uiText=old;}},renderPage,');
  once('return {html,text:','return {qa:window.__childLocale,page,route,setLocale:locale=>window.TOANAASI18n.setLocale(locale,{emit:false}),html,text:');
  return(await import('data:text/javascript;base64,'+Buffer.from(helper).toString('base64'))).renderChild;
}
