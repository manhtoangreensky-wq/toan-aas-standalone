import fs from "node:fs";
import path from "node:path";
import {execFileSync} from "node:child_process";
import {fileURLToPath} from "node:url";
import {documentCardDisplayRenderer} from "./document-card-display-runtime.mjs";
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),"../..");
export const DOCUMENT_CARD_METRICS_BASE="b3c1749fdc0876164cf9b3bedd64290fdf4d9bf4";
export function documentCardMetricsSources(historical=false){
  return Object.fromEntries(Object.entries({portal:"static/portal/portal.js",i18n:"static/portal/portal-i18n.js"}).map(([key,file])=>[
    key,(historical?execFileSync("git",["show",DOCUMENT_CARD_METRICS_BASE+":"+file],{cwd:root,encoding:"utf8",maxBuffer:30e6}):
      fs.readFileSync(path.join(root,file),"utf8")).replace(/\r\n/g,"\n")]));
}
export const documentCardMetricsRenderer=documentCardDisplayRenderer;
