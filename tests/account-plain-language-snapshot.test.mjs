import assert from 'node:assert/strict';
import test from 'node:test';
import fs from 'node:fs';
import {accountPlainLanguageHistoricalSnapshot} from './helpers/account-plain-language-snapshot.mjs';
import {renderPlainLanguage} from './helpers/account-plain-language-render.mjs';
const rows=JSON.parse(fs.readFileSync(new URL('./fixtures/account-plain-language-snapshot.json',import.meta.url),'utf8'));
for(const locale of ['vi','en','zh']){
 test(locale+': historical adapter accepts exactly reviewed current copy and retains original literal values',()=>{
  const actual=renderPlainLanguage(locale,'/account').messages;
  const entries=rows.map(row=>[row.key,actual[row.key]]),snapshot=JSON.stringify(entries);
  assert.deepEqual(accountPlainLanguageHistoricalSnapshot(entries,locale),rows.map(row=>[row.key,row.before[locale]]));
  assert.equal(JSON.stringify(entries),snapshot);
 });
 test(locale+': historical adapter does not hide a regression in any reviewed key',()=>{
  for(const row of rows)assert.throws(()=>accountPlainLanguageHistoricalSnapshot([[row.key,'UNREVIEWED_MUTATION']],locale),/Unreviewed Account\/Dashboard copy/);
 });
 test(locale+': unlisted catalogue changes are preserved for the original golden hash to reject',()=>{
  assert.deepEqual(accountPlainLanguageHistoricalSnapshot([['unknown.customer.key','UNREVIEWED_MUTATION']],locale),[['unknown.customer.key','UNREVIEWED_MUTATION']]);
 });
}
