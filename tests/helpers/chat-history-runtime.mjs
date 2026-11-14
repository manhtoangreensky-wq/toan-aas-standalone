import fs from 'node:fs';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {cardsTurnRenderer} from './chat-context-cards-turn-runtime.mjs';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
export const CHAT_HISTORY_BASE='d4ad39344f4b686dc7386257213ed9bc0b4fe809';
const files={portal:'static/portal/portal.js',i18n:'static/portal/portal-i18n.js'};
export function chatHistorySources(historical=false){
  return Object.fromEntries(Object.entries(files).map(([key,file])=>[key,
    (historical?execFileSync('git',['show',CHAT_HISTORY_BASE+':'+file],{cwd:root,encoding:'utf8',maxBuffer:30e6}):fs.readFileSync(path.join(root,file),'utf8')).replace(/\r\n/g,'\n')
  ]));
}
// Reuse the existing real full-bundle VM, including per-render locale selection.
export async function chatHistoryRenderer(sources=chatHistorySources()){
  return cardsTurnRenderer(sources);
}
