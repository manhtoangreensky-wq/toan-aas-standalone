import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {displayClutterHistoricalPortalSource} from './display-clutter-snapshot.mjs';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
export const DOCUMENT_PDF_BASE='c2fc6c657e41972d806c9a3504ea2c0e0438d975';
export function documentPdfSources(historical=false){
  if(historical&&!/^[a-f0-9]{40}$/.test(DOCUMENT_PDF_BASE))throw Error('Bind verified PR743 delivery before permanent PDF tests');
  return Object.fromEntries(Object.entries({portal:'static/portal/portal.js',i18n:'static/portal/portal-i18n.js'}).map(([key,file])=>{
    const source=(historical?execFileSync('git',['show',DOCUMENT_PDF_BASE+':'+file],{cwd:root,encoding:'utf8',maxBuffer:30e6}):fs.readFileSync(path.join(root,file),'utf8')).replace(/\r\n/g,'\n');
    return [key,key==='portal'?displayClutterHistoricalPortalSource(source):source];
  }));
}
export async function documentPdfRenderer(sources=documentPdfSources()){
  let helper=fs.readFileSync(path.join(root,'tests/helpers/document-card-copy-runtime.mjs'),'utf8');
  const once=(old,next)=>{assert.equal(helper.split(old).length-1,1);helper=helper.replace(old,next);};
  once("\nconst root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');\nexport const DOCUMENT_CARD_BASE=",'\nconst root='+JSON.stringify(root)+';\nexport const DOCUMENT_CARD_BASE=');
  once('window.__childLocale={renderDocumentOperationCards,','window.__childLocale={renderDocumentOperationHistoryPagination,pdfSplitFormFields,pdfOptimizeFormFields,renderPdfSplit,renderPdfMerge,renderPdfOptimize,renderNotes,renderFields,renderDocumentOperationCards,');
  return(await import('data:text/javascript;base64,'+Buffer.from(helper).toString('base64'))).documentCardRenderer(sources);
}
