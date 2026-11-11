import assert from 'node:assert/strict';import test from 'node:test';import fs from 'node:fs';
import {dashboardCustomerHistoricalSnapshot} from './helpers/dashboard-customer-snapshot.mjs';
import {renderPlainLanguage} from './helpers/account-plain-language-render.mjs';
const data=JSON.parse(fs.readFileSync(new URL('./fixtures/dashboard-customer-snapshot.json',import.meta.url),'utf8'));
for(const locale of ['vi','en','zh']){
 test(locale+': exact reviewed Dashboard copy and new account labels normalize for unchanged historical hashes',()=>{
  const actual=renderPlainLanguage(locale,'/dashboard').messages;
  const entries=[...data.existing,...data.added].map(row=>[row.key,actual[row.key]]),snapshot=JSON.stringify(entries);
  assert.deepEqual(dashboardCustomerHistoricalSnapshot(entries,locale),data.existing.map(row=>[row.key,row.before[locale]]));assert.equal(JSON.stringify(entries),snapshot);
 });
 test(locale+': every changed and added key still rejects unreviewed words',()=>{
  for(const row of [...data.existing,...data.added])assert.throws(()=>dashboardCustomerHistoricalSnapshot([[row.key,'UNREVIEWED_MUTATION']],locale),/Unreviewed/);
 });
 test(locale+': unknown catalogue changes remain visible to original gold guard',()=>assert.deepEqual(dashboardCustomerHistoricalSnapshot([['CUSTOMER_UNKNOWN','UNREVIEWED_MUTATION']],locale),[['CUSTOMER_UNKNOWN','UNREVIEWED_MUTATION']]));
}
