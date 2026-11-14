import assert from 'node:assert/strict';
import fs from 'node:fs';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {contextSectionHistoricalSnapshot,contextSectionHistoricalPortalSource} from './chat-context-section-snapshot.mjs';
const reviewed=JSON.parse(fs.readFileSync(new URL('../fixtures/chat-detail-summary-editor-reviewed.json',import.meta.url),'utf8'));
const keys=new Set(Object.keys(reviewed.vi)),hash=value=>createHash('sha256').update(value).digest('hex');
const hashes={vi:'39e705991fde89d27ce49d031dae491992519c3e05550c188a8cc3a4bd117931',en:'c6d19e50bcb416b57d5a20f3dda7dcf4b03b5258f12e183f027a0d791c3e3c6e',zh:'777e6f1951c2167cf31c79aa1e4f66231f0586fd4ef56b0ab86fbca70ed0705e'};
export function summaryHistoricalSnapshot(entries,locale){
  entries=contextSectionHistoricalSnapshot(entries,locale);
  assert.ok(hashes[locale]);const added=entries.filter(([key])=>keys.has(key));if(!added.length)return entries;
  assert.equal(added.length,11,'Unreviewed Chat summary/editor copy: missing keys');
  assert.equal(hash(JSON.stringify(added)),hashes[locale],'Unreviewed Chat summary/editor copy');
  return entries.filter(([key])=>!keys.has(key));
}
const original=execFileSync('git',['show','20c3e6fdf25f834fd6b62fbccbe6f8934e188119:static/portal/portal.js'],{encoding:'utf8',maxBuffer:30e6}).replace(/\r\n/g,'\n');
const start='  function renderChatWorkspaceDetail(page, context) {',end='\n  // Analytics Workspace';
const oa=original.indexOf(start),ob=original.indexOf(end,oa);assert.ok(oa>=0&&ob>oa);
export function summaryHistoricalPortalSource(value){
  const source=contextSectionHistoricalPortalSource(value).replace(/\r\n/g,'\n'),a=source.indexOf(start),b=source.indexOf(end,a);
  assert.ok(a>=0&&b>a,'Unreviewed Chat summary/editor source boundary');
  const part=source.slice(a,b),old=original.slice(oa,ob);if(part===old)return source;
  assert.equal(hash(part),'b59ff691d7f4afee224b001598b3df4dae351cd741587e6ff1ad29a122aa04c7','Unreviewed Chat summary/editor source');
  return source.slice(0,a)+old+source.slice(b);
}
