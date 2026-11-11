import assert from 'node:assert/strict';
import fs from 'node:fs';
import {dashboardCustomerHistoricalSnapshot} from './dashboard-customer-snapshot.mjs';

// Historical whole-catalog guards retain their original hashes. Only these
// reviewed copy edits may normalize to their literal pre-change values.
const rows=JSON.parse(fs.readFileSync(new URL('../fixtures/account-plain-language-snapshot.json',import.meta.url),'utf8'));
assert.equal(rows.length,33);
const approved=new Map(rows.map(row=>[row.key,row]));
assert.equal(approved.size,33);
export function accountPlainLanguageHistoricalSnapshot(entries,locale){
  assert.ok(['vi','en','zh'].includes(locale));
  return dashboardCustomerHistoricalSnapshot(entries,locale).map(([key,value])=>{
    const row=approved.get(key);
    if(!row)return[key,value];
    assert.equal(value,row.approved[locale],'Unreviewed Account/Dashboard copy must still fail: '+key);
    return[key,row.before[locale]];
  });
}
