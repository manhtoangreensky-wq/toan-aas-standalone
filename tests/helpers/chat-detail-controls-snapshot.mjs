import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import fs from 'node:fs';
import {execFileSync} from 'node:child_process';
import {summaryHistoricalSnapshot,summaryHistoricalPortalSource} from './chat-detail-summary-editor-snapshot.mjs';
const reviewed=JSON.parse(fs.readFileSync(new URL('../fixtures/chat-detail-controls-reviewed.json',import.meta.url),'utf8'));
const keys=new Set(Object.keys(reviewed.vi));
const hashes={vi:'4d831ce6031d06d5fc45df475c7755afdb1b0a6cfe801595ecd76c936024cb06',en:'582fda75ac8769ba5f073440684ae51ea2120363396289f3a091eb02e6f83316',zh:'2d58acc3c2ac1cf81f40e5360a7c610507c67129279dc90bec0d4b11133fba43'};
const hash=value=>createHash('sha256').update(value).digest('hex');
export function detailHistoricalSnapshot(entries,locale){
  entries=summaryHistoricalSnapshot(entries,locale);
  assert.ok(hashes[locale]);const added=entries.filter(([key])=>keys.has(key));if(!added.length)return entries;
  assert.equal(added.length,29,'Unreviewed Chat detail copy: missing keys');
  assert.equal(hash(JSON.stringify(added)),hashes[locale],'Unreviewed Chat detail copy');
  return entries.filter(([key])=>!keys.has(key));
}
const original=execFileSync('git',['show','d71c68c96439867a223d7ddc0757f8728adb9d96:static/portal/portal.js'],{encoding:'utf8',maxBuffer:30e6}).replace(/\r\n/g,'\n');
const spans=[
  ['  function chatContextFields() {','  function chatRunState(','582da9e07a857c1ae1988e3a2fa2d839bd0df82c0c786ebec2fd2116551e6f3b'],
  ['  function chatWorkspaceLifecycleActions(thread, state, context, route) {','  function renderChatWorkspaceDetail(','cecfc8e79ec871d79449c2aa15f222729fdcc5b2a9aff44a599395b4eca0aaee']
];
export function detailHistoricalPortalSource(value){
  let source=summaryHistoricalPortalSource(value).replace(/\r\n/g,'\n');
  for(const [start,end,expected]of spans){
    const a=source.indexOf(start),b=source.indexOf(end,a),oa=original.indexOf(start),ob=original.indexOf(end,oa);
    assert.ok(a>=0&&b>a&&oa>=0&&ob>oa,'Unreviewed Chat detail source boundary');
    const part=source.slice(a,b),old=original.slice(oa,ob);if(part===old)continue;
    assert.equal(hash(part),expected,'Unreviewed Chat detail source');
    source=source.slice(0,a)+old+source.slice(b);
  }
  return source;
}
