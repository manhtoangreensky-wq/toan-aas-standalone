import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {documentRefreshHistoricalSnapshot} from './document-refresh-copy-snapshot.mjs';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
const reviewed=JSON.parse(fs.readFileSync(path.join(root,'tests/fixtures/chat-document-usable-copy-reviewed.json'),'utf8'));
const keys=new Set(reviewed.added.vi.entries.map(([key])=>key));
assert.equal(keys.size,67);

// No prefix filter: every approved value/order must match and unknown keys
// remain visible to older golden catalog checks.
export function usableCopyHistoricalSnapshot(entries,locale){
  entries=documentRefreshHistoricalSnapshot(entries,locale);
  assert.ok(reviewed.added[locale]);
  const added=entries.filter(([key])=>keys.has(key));if(!added.length)return entries;
  assert.equal(added.length,67,'Unreviewed usable copy: missing keys');
  assert.equal(createHash('sha256').update(JSON.stringify(added)).digest('hex'),reviewed.added[locale].sha256,'Unreviewed usable copy');
  return entries.filter(([key])=>!keys.has(key));
}

// Older scoped renderer tests retain their original scope only through exact
// approved source spans. Unexpected edits cannot be normalized as new copy.
export function usableCopyHistoricalPortalSource(value){
  let source=value.replace(/\r\n/g,'\n');
  for(const edit of [...reviewed.portalEdits].reverse()){
    const oldCount=source.split(edit.before).length-1;
    if(!edit.after){
      if(oldCount===1)continue;
      assert.equal(oldCount,0);
      const start=source.indexOf('  function renderDocumentHub('),end=source.indexOf('\n  function renderPdfSplit(',start);
      assert.ok(start>=0&&end>start);
      const part=source.slice(start,end),close=part.lastIndexOf('\n    </article>');
      assert.ok(close>0&&part.slice(0,close).endsWith('\n'),'Unreviewed document footer location');
      source=source.slice(0,start)+part.slice(0,close)+edit.before+part.slice(close)+source.slice(end);
    }else{
      const newCount=source.split(edit.after).length-1;
      if(newCount===1){assert.equal(oldCount,0);source=source.replace(edit.after,edit.before);}
      else assert.equal(oldCount,1,'Unreviewed source fragment: '+edit.specId);
    }
  }
  return source;
}

let helper=fs.readFileSync(path.join(root,'tests/helpers/publishing-child-render.mjs'),'utf8');
helper=helper.replace("const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');",'const root='+JSON.stringify(root)+';');
const anchor="const portal=fs.readFileSync(path.join(root,'static/portal/portal.js'),'utf8');";
assert.equal(helper.split(anchor).length-1,1);
helper=helper.replace(anchor,'const portal='+JSON.stringify(usableCopyHistoricalPortalSource(fs.readFileSync(path.join(root,'static/portal/portal.js'),'utf8')))+';');
const {renderChild}=await import('data:text/javascript;base64,'+Buffer.from(helper).toString('base64'));
export function renderUsableHistoricalChild(locale,route,raw={}){
  const result=renderChild(locale,route,raw);
  return {...result,messages:Object.fromEntries(['vi','en','zh'].map(l=>[l,Object.fromEntries(usableCopyHistoricalSnapshot(Object.entries(result.messages[l]),l))]))};
}
