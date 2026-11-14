import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {execFileSync} from 'node:child_process';
import {CHAT_CONTEXT_LABEL_CONTRAST_ADDITION as addition,chatContextLabelHistoricalCss} from './helpers/chat-context-label-contrast-snapshot.mjs';
const file='static/portal/portal-theme.css';
const base=execFileSync('git',['show','87afb6b62dbe14fdc6a4f818161afaa5a0c6399d:'+file],{encoding:'utf8',maxBuffer:3e6}).replace(/\r\n/g,'\n');
const source=fs.readFileSync(file,'utf8').replace(/\r\n/g,'\n');
test('only saved-note label color is appended in the light theme; every earlier CSS byte remains',()=>{
  assert.equal(source===base+addition,true,'Only the exact reviewed one-rule EOF append is accepted');
  assert.equal(source.split(addition).length-1,1);
  assert.doesNotMatch(addition,/!important|opacity|display|visibility|font|padding|margin|transition|animation|transform/);
  assert.equal(chatContextLabelHistoricalCss(source),base);
});
test('finite CSS projection rejects duplicated or misplaced rules and retains unrelated edits',()=>{
  assert.equal(chatContextLabelHistoricalCss(base+addition),base);
  assert.throws(()=>chatContextLabelHistoricalCss(base+addition+addition),/Unreviewed Chat context label CSS/);
  assert.throws(()=>chatContextLabelHistoricalCss(base+addition+'\n/* UNKNOWN */'),/Unreviewed Chat context label CSS/);
  assert.ok(chatContextLabelHistoricalCss(base+'\n/* UNKNOWN */').endsWith('/* UNKNOWN */'));
  const changed=addition.replace('var(--portal-ink)','red');
  assert.equal(chatContextLabelHistoricalCss(base+changed),base+changed,'An unknown rule cannot be silently projected away');
});
// Computed color/contrast and protected dark/sentinel evidence are separate
// finite native baseline/green observations, not inferred from source.
