import assert from 'node:assert/strict';
import fs from 'node:fs';
const data=JSON.parse(fs.readFileSync(new URL('../fixtures/dashboard-customer-snapshot.json',import.meta.url),'utf8'));
assert.equal(data.existing.length,13);assert.equal(data.added.length,3);
const old=new Map(data.existing.map(row=>[row.key,row])),fresh=new Map(data.added.map(row=>[row.key,row]));
assert.equal(old.size,13);assert.equal(fresh.size,3);
export function dashboardCustomerHistoricalSnapshot(entries,locale){
  assert.ok(['vi','en','zh'].includes(locale));
  return entries.flatMap(([key,value])=>{
    const added=fresh.get(key),row=old.get(key);
    if(added){assert.equal(value,added.approved[locale],'Unreviewed added account label: '+key);return[];}
    if(!row)return[[key,value]];
    assert.equal(value,row.approved[locale],'Unreviewed Dashboard copy: '+key);
    return[[key,row.before[locale]]];
  });
}
