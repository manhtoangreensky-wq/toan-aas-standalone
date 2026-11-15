import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
export const DOCUMENT_CARD_BASE='5bc8f3cdf500e8035e55789cd8c30fb18e779eb6';
export function documentCardSources(historical=false){
  if(historical&&!/^[a-f0-9]{40}$/.test(DOCUMENT_CARD_BASE))throw Error('Bind __DATE_RELEASE_SHA__ only after verified PR742 delivery');
  return Object.fromEntries(Object.entries({portal:'static/portal/portal.js',i18n:'static/portal/portal-i18n.js'}).map(([key,file])=>[key,(historical?execFileSync('git',['show',DOCUMENT_CARD_BASE+':'+file],{cwd:root,encoding:'utf8',maxBuffer:30e6}):fs.readFileSync(path.join(root,file),'utf8')).replace(/\r\n/g,'\n')]));
}
export async function documentCardRenderer(sources=documentCardSources()){
  let helper=fs.readFileSync(path.join(root,'tests/helpers/chat-page-meta-runtime.mjs'),'utf8');
  const once=(old,next)=>{assert.equal(helper.split(old).length-1,1,'Exact complete renderer reuse');helper=helper.replace(old,next);};
  once("\nconst root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');\nexport const PAGE_META_BASE=",'\nconst root='+JSON.stringify(root)+';\nexport const PAGE_META_BASE=');
  once('window.__childLocale={renderHeader,','window.__childLocale={renderDocumentOperationCards,documentOperationState,documentOperationDownloadPath,renderHeader,');
  return(await import('data:text/javascript;base64,'+Buffer.from(helper).toString('base64'))).pageMetaRenderer(sources);
}
