import fs from 'node:fs';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {summaryRenderer} from './chat-detail-summary-editor-runtime.mjs';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
export const CONTEXT_SECTION_BASE='d124b867c81ca0882a74721661fd8880e0451b8d';
const files={portal:'static/portal/portal.js',i18n:'static/portal/portal-i18n.js'};
export function contextSectionSources(historical=false){
  return Object.fromEntries(Object.entries(files).map(([key,file])=>[key,
    (historical?execFileSync('git',['show',CONTEXT_SECTION_BASE+':'+file],{cwd:root,encoding:'utf8',maxBuffer:30e6}):fs.readFileSync(path.join(root,file),'utf8')).replace(/\r\n/g,'\n')
  ]));
}
// Reuse the real full-bundle VM boundary, without copying application logic.
export async function contextSectionRenderer(sources=contextSectionSources()){
  return summaryRenderer(sources);
}
