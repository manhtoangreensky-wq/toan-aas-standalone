import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
const reviewed=JSON.parse(fs.readFileSync(new URL('../fixtures/chat-history-reviewed.json',import.meta.url),'utf8'));
const keys=new Set(Object.keys(reviewed.vi)),hash=value=>createHash('sha256').update(value).digest('hex');
const hashes={vi:'c8e3a4bbb29f258ee4cd12c2cf80fca86c56d6fb028c59de0f0e1c26fe4f21d1',en:'918cf6e155874f3330abcd984fd3085476b960d0d846a6e7050870c26ae84295',zh:'84ed499da93d6ad0bcbb3bf5cfeca5903f99dab536e8a15214524fdda7e11b29'};
assert.equal(keys.size,22);
export function historyHistoricalSnapshot(entries,locale){
  assert.ok(hashes[locale]);
  const scoped=entries.filter(([key])=>/^chatHistory(?:Version|Activity)Ui/.test(key));
  if(!scoped.length)return entries;
  const added=entries.filter(([key])=>keys.has(key));
  assert.equal(scoped.length,added.length,'Unreviewed Chat history copy: unknown key');
  assert.equal(added.length,22,'Unreviewed Chat history copy: missing keys');
  assert.equal(hash(JSON.stringify(added)),hashes[locale],'Unreviewed Chat history copy');
  return entries.filter(([key])=>!keys.has(key));
}
const original=execFileSync('git',['show','d4ad39344f4b686dc7386257213ed9bc0b4fe809:static/portal/portal.js'],{cwd:root,encoding:'utf8',maxBuffer:30e6}).replace(/\r\n/g,'\n');
const start='  function renderChatWorkspaceDetail(page, context) {',end='\n  // Analytics Workspace';
const oa=original.indexOf(start),ob=original.indexOf(end,oa);assert.ok(oa>=0&&ob>oa);
export function historyHistoricalPortalSource(value){
  const source=value.replace(/\r\n/g,'\n');
  assert.equal(source.split(start).length-1,1,'Unreviewed Chat history source boundary');
  const a=source.indexOf(start),b=source.indexOf(end,a);assert.ok(a>=0&&b>a,'Unreviewed Chat history source boundary');
  const part=source.slice(a,b),old=original.slice(oa,ob);
  // Marker-free historical source is passed unchanged to the older strict gate.
  if(part===old||!/chatHistory(?:Version|Activity)Ui/.test(part))return source;
  assert.equal(hash(part),'517e5f452469eb96394f7a4b5d1a788b3a115848fe5c8833793d1a31be6f99b0','Unreviewed Chat history source');
  return source.slice(0,a)+old+source.slice(b);
}
