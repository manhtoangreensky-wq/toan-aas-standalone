import fs from 'node:fs';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {chatHistoryRenderer} from './chat-history-runtime.mjs';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
export const REQUEST_PANEL_BASE='63ddccd5e34ee44590ff0493ba6a396d1e5cec2d';
const files={portal:'static/portal/portal.js',i18n:'static/portal/portal-i18n.js',css:'static/portal/portal.css'};
export function requestPanelSources(historical=false){
  if(historical&&!/^[a-f0-9]{40}$/.test(REQUEST_PANEL_BASE))throw Error('Fill __HISTORY_RELEASE_SHA__ with the verified history release before running this prepared gate');
  return Object.fromEntries(Object.entries(files).map(([key,file])=>[key,
    (historical?execFileSync('git',['show',REQUEST_PANEL_BASE+':'+file],{cwd:root,encoding:'utf8',maxBuffer:30e6}):fs.readFileSync(path.join(root,file),'utf8')).replace(/\r\n/g,'\n')
  ]));
}
// Reuse the actual full-bundle history VM and its existing full-detail QA exposure.
// Do not export/copy the panel, projection, guards, filters or timeline implementations.
export async function requestPanelRenderer(sources=requestPanelSources()){
  return chatHistoryRenderer(sources);
}
