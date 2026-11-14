import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {execFileSync} from 'node:child_process';
import {chatBoundaryGridHistoricalCss} from './helpers/chat-boundary-grid-snapshot.mjs';
const base='3477d0d83cb88d96941f5790f642cceb285463d9';
const file='static/portal/portal-theme.css';
const source=chatBoundaryGridHistoricalCss(fs.readFileSync(file,'utf8'));
const old=execFileSync('git',['show',base+':'+file],{encoding:'utf8',maxBuffer:30e6}).replace(/\r\n/g,'\n');
const addition='\n/* Improve light theme Chat workspace field label readability and contrast. */\nhtml:not([data-portal-theme="dark"]) .portal-page:is(.portal-chat-workspace, .portal-chat-workspace-detail) .portal-field > label {\n  color: var(--portal-ink);\n}\n';
test('light Chat labels use the existing semantic ink while every other CSS byte remains protected',()=>{
  assert.equal(source,old+addition);
  assert.equal(source.split(addition).length-1,1);
  assert.doesNotMatch(addition,/!important|opacity|font-size|transition|animation|display/);
});
// Actual computed-colour proof is recorded from signed owned native375/812/
// 1440light/dark runs. A CSS source guard alone is not a contrast PASS.
