import assert from 'node:assert/strict';
import fs from 'node:fs';

const {rows,introduced}=JSON.parse(fs.readFileSync(new URL('../fixtures/membership-plain-language-snapshot.json',import.meta.url),'utf8'));
assert.equal(rows.length,14);assert.equal(introduced.length,5);
const approved=new Map([...rows,...introduced].map(row=>[row.key,row]));
assert.equal(approved.size,19);

// Keep complete-catalog golden hashes. Reject every unreviewed value, even for
// these nineteen keys; unlisted keys are never removed or normalized away.
export function membershipPlainLanguageHistoricalSnapshot(entries,locale){
  assert.ok(['vi','en','zh'].includes(locale));
  return entries.flatMap(([key,value])=>{
    const row=approved.get(key);
    if(!row)return[[key,value]];
    assert.equal(value,row.approved[locale],'Unreviewed membership copy must fail: '+key);
    return row.before?[[key,row.before[locale]]]:[];
  });
}
