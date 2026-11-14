import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
export const CHAT_CARDS_BASE='398cea1c4f6f6f256c646fa382a78563e66b8939';
const files={portal:'static/portal/portal.js',i18n:'static/portal/portal-i18n.js'};
export function chatCardsSources(historical=false){
  return Object.fromEntries(Object.entries(files).map(([key,file])=>[
    key,(historical?execFileSync('git',['show',CHAT_CARDS_BASE+':'+file],{cwd:root,encoding:'utf8',maxBuffer:30e6}):fs.readFileSync(path.join(root,file),'utf8')).replace(/\r\n/g,'\n')
  ]));
}
export async function chatCardsRenderer(sources=chatCardsSources()){
  let helper=fs.readFileSync(path.join(root,'tests/helpers/publishing-child-render.mjs'),'utf8');
  const once=(before,after)=>{assert.equal(helper.split(before).length-1,1);helper=helper.replace(before,after);};
  once("const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');",'const root='+JSON.stringify(root)+';');
  for(const [key,file]of Object.entries(files))once("const "+key+"=fs.readFileSync(path.join(root,'"+file+"'),'utf8');",'const '+key+'='+JSON.stringify(sources[key])+';');
  once('window.__childLocale={renderPage,','window.__childLocale={renderChatWorkspaceBoundary,renderChatWorkspaceCards,renderChatExecutionPanel,chatWorkspaceModeLabel,renderChatWorkspaceTags,safeText,renderPage,');
  once('return {html,text:','return {qa:window.__childLocale,setLocale:locale=>window.TOANAASI18n.setLocale(locale,{emit:false}),html,text:');
  return(await import('data:text/javascript;base64,'+Buffer.from(helper).toString('base64'))).renderChild;
}
