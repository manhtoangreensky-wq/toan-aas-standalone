import test from 'node:test';
import assert from 'node:assert/strict';
import {documentRefreshRuntime} from './helpers/document-refresh-action-runtime.mjs';
import {documentRefreshHistoricalSnapshot} from './helpers/document-refresh-copy-snapshot.mjs';

for(const locale of ['vi','en','zh'])test(`${locale}: historical refresh adapter never hides changed, missing, reordered or unknown copy`,()=>{
  const entries=Object.entries(documentRefreshRuntime(locale).messages[locale]);
  const approved=entries.filter(([key])=>key.startsWith('docRefreshUi'));
  assert.equal(approved.length,4);
  const saved=JSON.stringify(entries);
  const normalized=documentRefreshHistoricalSnapshot(entries,locale);
  assert.equal(normalized.length,entries.length-4);
  assert.equal(JSON.stringify(entries),saved);
  for(const [key]of approved){
    assert.throws(()=>documentRefreshHistoricalSnapshot(entries.filter(([name])=>name!==key),locale),/Unreviewed document refresh copy/);
    assert.throws(()=>documentRefreshHistoricalSnapshot(entries.map(([name,value])=>[name,name===key?'UNREVIEWED':value]),locale),/Unreviewed document refresh copy/);
  }
  assert.throws(()=>documentRefreshHistoricalSnapshot([...normalized,...approved.toReversed()],locale),/Unreviewed document refresh copy/);
  const unknown=['docRefreshUiUnknown','CUSTOMER studio metadata'];
  assert.deepEqual(documentRefreshHistoricalSnapshot([...entries,unknown],locale).at(-1),unknown);
  assert.deepEqual(documentRefreshHistoricalSnapshot(normalized,locale),normalized);
});
