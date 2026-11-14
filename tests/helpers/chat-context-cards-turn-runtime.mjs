import fs from 'node:fs';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {contextSectionRenderer} from './chat-context-section-runtime.mjs';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
export const CARDS_TURN_BASE='6a51975654cfb30ae228bfef9064ac3141d53081';
const files={portal:'static/portal/portal.js',i18n:'static/portal/portal-i18n.js'};
export function cardsTurnSources(historical=false){
  return Object.fromEntries(Object.entries(files).map(([key,file])=>[key,
    (historical?execFileSync('git',['show',CARDS_TURN_BASE+':'+file],{cwd:root,encoding:'utf8',maxBuffer:30e6}):fs.readFileSync(path.join(root,file),'utf8')).replace(/\r\n/g,'\n')
  ]));
}
// Real full-bundle VM; option helper is exercised through actual card selects.
export async function cardsTurnRenderer(sources=cardsTurnSources()){
  return contextSectionRenderer(sources);
}
