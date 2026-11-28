// Historical renderer input only; current primary tests never import this.
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import {fileURLToPath} from "node:url";
import {customerNaturalHistoricalSource} from "./customer-natural-followup-historical.mjs";
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),"../..");
const helper=fs.readFileSync(path.join(root,"tests/helpers/publishing-child-render.mjs"),"utf8");
const source=fs.readFileSync(path.join(root,"static/portal/portal-i18n.js"),"utf8");
const replacements=[
 ["const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');","const root="+JSON.stringify(root)+";"],
 ["const i18n=fs.readFileSync(path.join(root,'static/portal/portal-i18n.js'),'utf8');",
  "const i18n="+JSON.stringify(customerNaturalHistoricalSource(source,"static/portal/portal-i18n.js"))+";"]
];
let input=helper;
for(const[before,after]of replacements){
  assert.equal(input.split(before).length-1,1,"Exact historical rendering input anchor");
  input=input.replace(before,()=>after);
}
export const {renderChild}=await import("data:text/javascript;base64,"+Buffer.from(input).toString("base64"));
