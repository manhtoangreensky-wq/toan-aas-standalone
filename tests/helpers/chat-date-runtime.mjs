import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
export const CHAT_DATE_BASE='c048dd7e70656d58f097c67bf7166b3486007bd6';
export function chatDateSources(historical=false){
  if(historical&&!/^[a-f0-9]{40}$/.test(CHAT_DATE_BASE))throw Error('Bind __META_RELEASE_SHA__ only after verified metadata delivery');
  return Object.fromEntries(Object.entries({portal:'static/portal/portal.js',i18n:'static/portal/portal-i18n.js'}).map(([key,file])=>[key,(historical?execFileSync('git',['show',CHAT_DATE_BASE+':'+file],{cwd:root,encoding:'utf8',maxBuffer:30e6}):fs.readFileSync(path.join(root,file),'utf8')).replace(/\r\n/g,'\n')]));
}
export async function chatDateRenderer(sources=chatDateSources()){
  let helper=fs.readFileSync(path.join(root,'tests/helpers/chat-page-meta-runtime.mjs'),'utf8');
  const once=(old,next)=>{assert.equal(helper.split(old).length-1,1,'Exact metadata renderer reuse');helper=helper.replace(old,next);};
  once("\nconst root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');\nexport const PAGE_META_BASE=",'\nconst root='+JSON.stringify(root)+';\nexport const PAGE_META_BASE=');
  once('window.__childLocale={renderHeader,','window.__childLocale={chatWorkspaceDateLabel:typeof chatWorkspaceDateLabel==="function"?chatWorkspaceDateLabel:null,renderChatWorkspaceDetail,localizedDateTime,withDateFormatter:(fn,run)=>{const old=localizedDateTime;try{localizedDateTime=fn;return run();}finally{localizedDateTime=old;}},renderHeader,');
  return(await import('data:text/javascript;base64,'+Buffer.from(helper).toString('base64'))).pageMetaRenderer(sources);
}
