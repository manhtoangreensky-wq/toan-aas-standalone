import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {execFileSync} from 'node:child_process';
import {CHAT_BOUNDARY_GRID_ADDITION,chatBoundaryGridHistoricalCss} from './helpers/chat-boundary-grid-snapshot.mjs';

const file='static/portal/portal-theme.css';
const base=execFileSync('git',['show','398cea1c4f6f6f256c646fa382a78563e66b8939:'+file],{encoding:'utf8',maxBuffer:30e6}).replace(/\r\n/g,'\n');
const source=fs.readFileSync(file,'utf8').replace(/\r\n/g,'\n');
test('only-child Chat create panel spans existing grid; all other theme bytes remain protected',()=>{
  assert.ok(source===base+CHAT_BOUNDARY_GRID_ADDITION,'Only the reviewed Chat only-child grid span may be appended');
  assert.doesNotMatch(CHAT_BOUNDARY_GRID_ADDITION,/!important|opacity|display|grid-template|transition|animation|width|padding/);
  assert.equal(chatBoundaryGridHistoricalCss(source),base);
});
test('historical CSS adapter rejects duplicate/misplaced addition and retains unknown mutations',()=>{
  assert.equal(chatBoundaryGridHistoricalCss(base+CHAT_BOUNDARY_GRID_ADDITION),base);
  assert.throws(()=>chatBoundaryGridHistoricalCss(base+CHAT_BOUNDARY_GRID_ADDITION+CHAT_BOUNDARY_GRID_ADDITION),/Unreviewed Chat grid CSS/);
  assert.throws(()=>chatBoundaryGridHistoricalCss(base+CHAT_BOUNDARY_GRID_ADDITION+'\n/* UNKNOWN */'),/Unreviewed Chat grid CSS/);
  assert.ok(chatBoundaryGridHistoricalCss(base+'\n/* UNKNOWN */').endsWith('/* UNKNOWN */'));
});
// The actual width effect and protected detail/mobile geometry are measured
// in the owned native geometry witness; CSS source presence alone is not PASS.
