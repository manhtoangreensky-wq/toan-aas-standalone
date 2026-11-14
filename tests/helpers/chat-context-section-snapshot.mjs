import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {cardsTurnHistoricalSnapshot,cardsTurnHistoricalPortalSource} from './chat-context-cards-turn-snapshot.mjs';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
const reviewed=JSON.parse(fs.readFileSync(new URL('../fixtures/chat-context-section-reviewed.json',import.meta.url),'utf8'));
const keys=new Set(Object.keys(reviewed.vi));
const hash=value=>createHash('sha256').update(value).digest('hex');
const hashes={vi:'84ed8ebd7a04b1e4d2afd4291a1755fe8ec1fa8ea3937b657a1366a23067c9ca',en:'50f71dc0f6a82bfb9e97585cd4e0b17b3a3ad11655529cf71b86674b613d8889',zh:'20320be8ccf8472b41e96f2241825b646dd4248fbe127ebcf6fefd3606b9288e'};
assert.equal(keys.size,17);
export function contextSectionHistoricalSnapshot(entries,locale){
  entries=cardsTurnHistoricalSnapshot(entries,locale);
  assert.ok(hashes[locale]);
  const scoped=entries.filter(([key])=>/^chatDetail(?:Context|Section)Ui/.test(key));
  if(!scoped.length)return entries;
  const added=entries.filter(([key])=>keys.has(key));
  assert.equal(scoped.length,added.length,'Unreviewed Chat context/section copy: unknown key');
  assert.equal(added.length,17,'Unreviewed Chat context/section copy: missing keys');
  assert.equal(hash(JSON.stringify(added)),hashes[locale],'Unreviewed Chat context/section copy');
  return entries.filter(([key])=>!keys.has(key));
}
const original=execFileSync('git',['show','d124b867c81ca0882a74721661fd8880e0451b8d:static/portal/portal.js'],{cwd:root,encoding:'utf8',maxBuffer:30e6}).replace(/\r\n/g,'\n');
const start='  function renderChatWorkspaceDetail(page, context) {',end='\n  // Analytics Workspace';
const oa=original.indexOf(start),ob=original.indexOf(end,oa);
assert.ok(oa>=0&&ob>oa);
const pinnedPrefix='      { name: "pinned", label: uiText("chatFieldUiPinnedLabel"';
const oldPinned=original.split('\n').find(line=>line.startsWith(pinnedPrefix));assert.ok(oldPinned);
export function contextSectionHistoricalPortalSource(value){
  let source=cardsTurnHistoricalPortalSource(value).replace(/\r\n/g,'\n');
  assert.equal(source.split(start).length-1,1,'Unreviewed Chat context/section source boundary');
  const a=source.indexOf(start),b=source.indexOf(end,a);assert.ok(a>=0&&b>a,'Unreviewed Chat context/section source boundary');
  const part=source.slice(a,b),old=original.slice(oa,ob);
  // Earlier finite snapshots still pass through the older strict hash gates.
  // Only this unit's newly introduced source is normalized here.
  if(part!==old && /chatDetail(?:Context|Section)Ui/.test(part)){
    assert.equal(hash(part),'52617a25f70badc73814d3de6b3968dd9fd20a142a8904782336e15e016567d5','Unreviewed Chat context/section source');
    source=source.slice(0,a)+old+source.slice(b);
  }
  const pins=source.split('\n').filter(line=>line.startsWith(pinnedPrefix));
  assert.equal(pins.length,1,'Unreviewed Chat context/section pinned source');
  if(pins[0]!==oldPinned){
    assert.equal(hash(pins[0]),'ffb8d6f25e95d3efed10481c813b7ed8d0f8ed1fa99254f55ef73cd5a10d6799','Unreviewed Chat context/section pinned source');
    source=source.replace(pins[0],oldPinned);
  }
  return source;
}
