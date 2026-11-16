import assert from 'node:assert/strict';
import fs from 'node:fs';
import {createHash} from 'node:crypto';
import {documentPdfSources} from './document-pdf-ui-runtime.mjs';
import {displayClutterHistoricalPortalSource} from './display-clutter-snapshot.mjs';
import {documentCardDisplayHistoricalSnapshot,documentCardDisplayHistoricalPortalSource,documentCardDisplayHistoricalI18nSource} from './document-card-display-snapshot.mjs';
const fixture=JSON.parse(fs.readFileSync(new URL('../fixtures/document-pdf-ui-reviewed.json',import.meta.url),'utf8')),keys=new Set(Object.keys(fixture.vi)),hash=value=>createHash('sha256').update(value).digest('hex');
assert.equal(keys.size,13);
export function documentPdfHistoricalSnapshot(entries,locale){
  entries=documentCardDisplayHistoricalSnapshot(entries,locale);
  const scoped=entries.filter(([key])=>/^(?:docHistoryUi|docPdf(?:Source|Page|Optimize)Ui)/.test(key));if(!scoped.length)return entries;
  const added=entries.filter(([key])=>keys.has(key));assert.equal(scoped.length,added.length,'Unreviewed PDF UI copy: unknown key');assert.equal(added.length,13,'Unreviewed PDF UI copy: missing key');
  assert.equal(hash(JSON.stringify(added)),fixture.binding.catalogHashes[locale],'Unreviewed PDF UI copy: value/order');return entries.filter(([key])=>!keys.has(key));
}
const marker='  verifyEqualKeysets();',blocks=fixture.binding.catalogGroups.map(group=>{
  const block=['vi','en','zh'].map(locale=>'  Object.assign(MESSAGES.'+locale+', {\n'+group.keys.map(key=>'    '+key+': '+JSON.stringify(fixture[locale][key])).join(',\n')+'\n  });').join('\n')+'\n\n'+marker;
  assert.equal(hash(block),group.hash,'Exact reviewed PDF UI addition');return block;
});
export function documentPdfHistoricalI18nSource(value){
  let source=documentCardDisplayHistoricalI18nSource(value);if(!/(?:docHistoryUi|docPdf(?:Source|Page|Optimize)Ui)/.test(source))return source;
  for(const block of [...blocks].reverse()){assert.equal(source.split(block).length-1,1,'Unreviewed PDF UI i18n addition');source=source.replace(block,marker);}return source;
}
function scope(source,name){
  const start='  function '+name+'(';assert.equal(source.split(start).length-1,1,'Unreviewed PDF UI source boundary');
  const a=source.indexOf(start),b=source.indexOf('\n  function ',a+start.length);assert.ok(a>=0&&b>a);return {a,b,text:source.slice(a,b)};
}
const original=documentPdfSources(true).portal,oldParts=fixture.binding.chunks.map((edit,index)=>{
  const part=scope(original,edit.name);const text=index<3?original.slice(part.a,part.a+edit.oldLength):part.text.split('\n').filter(line=>line.includes('Không thay thế workflow Bot'));
  const old=index<3?text:(assert.equal(text.length,1),text[0]);assert.equal(hash(old),edit.oldHash,'Reviewed document-card baseline chunk');return old;
});
export function documentPdfHistoricalPortalSource(value){
  let source=displayClutterHistoricalPortalSource(documentCardDisplayHistoricalPortalSource(value)),has=/docHistoryUi|docPdf(?:Source|Page|Optimize)Ui/.test(source);
  if(!has)has=fixture.binding.chunks.slice(3).some(edit=>source.includes('  function '+edit.name+'(')&&scope(source,edit.name).text.split('\n').includes('      ${renderNotes(page)}'));
  if(!has)return source;
  for(let k=fixture.binding.chunks.length-1;k>=0;k--){
    const edit=fixture.binding.chunks[k],part=scope(source,edit.name),text=k<3?source.slice(part.a,part.a+edit.newLength):'      ${renderNotes(page)}';
    assert.equal(hash(text),edit.newHash,'Unreviewed PDF UI source chunk '+edit.name);
    if(k<3)source=source.slice(0,part.a)+oldParts[k]+source.slice(part.a+edit.newLength);
    else{assert.equal(part.text.split(text).length-1,1,'Unreviewed PDF UI notice');source=source.slice(0,part.a)+part.text.replace(text,oldParts[k])+source.slice(part.b);}
  }return source;
}
