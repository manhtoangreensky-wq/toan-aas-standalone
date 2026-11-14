import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
export const CHAT_DATES_PAGES_BASE='7e30dd95d2d5652281f9462a73f7ba08b7801f59';
const files={portal:'static/portal/portal.js',i18n:'static/portal/portal-i18n.js'};
export function datePagesSources(historical=false){
  return Object.fromEntries(Object.entries(files).map(([key,file])=>[key,
    (historical?execFileSync('git',['show',CHAT_DATES_PAGES_BASE+':'+file],{cwd:root,encoding:'utf8',maxBuffer:30e6}):fs.readFileSync(path.join(root,file),'utf8')).replace(/\r\n/g,'\n')
  ]));
}
export async function datePagesRenderer(sources=datePagesSources()){
  let helper=fs.readFileSync(path.join(root,'tests/helpers/publishing-child-render.mjs'),'utf8');
  const once=(before,after)=>{assert.equal(helper.split(before).length-1,1);helper=helper.replace(before,after);};
  once("const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');",'const root='+JSON.stringify(root)+';');
  for(const [key,file]of Object.entries(files))once("const "+key+"=fs.readFileSync(path.join(root,'"+file+"'),'utf8');",'const '+key+'='+JSON.stringify(sources[key])+';');
  once('window.__childLocale={renderPage,','window.__childLocale={renderChatWorkspaceCards,renderChatWorkspacePagination,safeText,withDateFormatter:(fn,run)=>{const old=localizedDateTime;try{localizedDateTime=fn;return run();}finally{localizedDateTime=old;}},renderPage,');
  once('return {html,text:','return {qa:window.__childLocale,setLocale:locale=>window.TOANAASI18n.setLocale(locale,{emit:false}),html,text:');
  return(await import('data:text/javascript;base64,'+Buffer.from(helper).toString('base64'))).renderChild;
}
