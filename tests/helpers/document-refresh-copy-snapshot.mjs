import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';

const keys=new Set(['RouteMismatch','Permission','ReadFailed','Success'].map(key=>'docRefreshUi'+key));
const hashes={
  vi:'4f5b3f610543425314f2f0b0fd9a085d7674e8b1504589ecebcba0aee620197e',
  en:'a53d500dc4496ea9be080a77a8315b530f647c526d2cbc7dbb67aa07c55a3ee2',
  zh:'b1f4898f1c7b23b7a3d3406ba996e06419331e0e69e914d46b8b98b5dce9645b'
};

// Older catalog contracts may omit only these four reviewed additions.
// Unknown keys, changed values/order and partial sets must remain failures.
export function documentRefreshHistoricalSnapshot(entries,locale){
  assert.ok(hashes[locale]);
  const added=entries.filter(([key])=>keys.has(key));
  if(!added.length)return entries;
  assert.equal(added.length,4,'Unreviewed document refresh copy: missing keys');
  assert.equal(createHash('sha256').update(JSON.stringify(added)).digest('hex'),hashes[locale],'Unreviewed document refresh copy');
  return entries.filter(([key])=>!keys.has(key));
}
