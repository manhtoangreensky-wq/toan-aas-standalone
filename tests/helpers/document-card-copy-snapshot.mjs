import assert from 'node:assert/strict';
import fs from 'node:fs';
import {createHash} from 'node:crypto';
import {documentCardSources} from './document-card-copy-runtime.mjs';
import {documentPdfHistoricalSnapshot,documentPdfHistoricalPortalSource,documentPdfHistoricalI18nSource} from './document-pdf-ui-snapshot.mjs';
const reviewed=JSON.parse(fs.readFileSync(new URL('../fixtures/document-card-copy-reviewed.json',import.meta.url),'utf8'));
const keys=new Set(Object.keys(reviewed.vi)),hash=value=>createHash('sha256').update(value).digest('hex');
assert.equal(keys.size,23);
export function documentCardHistoricalSnapshot(entries,locale){
  entries=documentPdfHistoricalSnapshot(entries,locale);
  assert.ok(reviewed.binding.catalog[locale]);
  const reserved=entries.filter(([key])=>/^(?:docPendingUi|docCardUi|docCardEmptyUi)/.test(key));if(!reserved.length)return entries;
  const added=entries.filter(([key])=>keys.has(key));
  assert.equal(reserved.length,added.length,'Unreviewed document card copy: unknown key');
  assert.equal(added.length,23,'Unreviewed document card copy: missing keys');
  assert.equal(hash(JSON.stringify(added)),reviewed.binding.catalog[locale],'Unreviewed document card copy: value/order');
  return entries.filter(([key])=>!keys.has(key));
}
const catalogAddition=['docPendingUi','docCardUi','docCardEmptyUi'].map(prefix=>
  ['vi','en','zh'].map(locale=>'  Object.assign(MESSAGES.'+locale+', {\n'+
    Object.entries(reviewed[locale]).filter(([key])=>key.startsWith(prefix))
      .map(([key,value])=>'    '+key+': '+JSON.stringify(value)).join(',\n')+'\n  });').join('\n')
).join('\n\n')+'\n\n';
export function documentCardHistoricalI18nSource(value){
  const source=documentPdfHistoricalI18nSource(value);
  if(!/(?:docPendingUi|docCardUi|docCardEmptyUi)/.test(source))return source;
  assert.equal(source.split(catalogAddition).length-1,1,'Unreviewed document card i18n: partial/duplicate/changed addition');
  return source.replace(catalogAddition,'');
}
function span(source){
  const start='  function renderDocumentOperationCards(',end='\n  function renderMediaHubPage(';
  assert.equal(source.split(start).length-1,1,'Unreviewed document card source boundary');
  const a=source.indexOf(start),b=source.indexOf(end,a);assert.ok(a>=0&&b>a,'Unreviewed document card source boundary');return {a,b,text:source.slice(a,b)};
}
function chunks(part){
  const headerEnd=part.indexOf('\n'),pending='      const pendingMessage = ',actions='      const artifactLabel = ';
  assert.equal(part.split(pending).length-1,1);assert.equal(part.split(actions).length-1,1);
  const pa=part.indexOf(pending),pb=part.indexOf('\n      const outputMetric = ',pa),aa=part.indexOf(actions),ab=part.indexOf('\n    }).join("")}</div>`;',aa);
  assert.ok(headerEnd>0&&pa>headerEnd&&pb>pa&&aa>pb&&ab>aa,'Unreviewed document card chunk boundaries');
  return [{name:'header',a:0,b:headerEnd},{name:'pending',a:pa,b:pb},{name:'actions',a:aa,b:ab}].map(item=>({...item,text:part.slice(item.a,item.b)}));
}
// Builtin-only runtime module: no import of DATE/META/history and no cycle.
// Baseline access fails before Git while the release placeholder is unbound.
const original=documentCardSources(true).portal,old=chunks(span(original).text);
for(const item of old)assert.equal(hash(item.text),reviewed.binding.fragments[item.name].old,'Reviewed date-release document baseline differs');
export function documentCardHistoricalPortalSource(value){
  const source=documentPdfHistoricalPortalSource(value);
  if(!/(?:docPendingUi|docCardUi|docCardEmptyUi)/.test(source))return source;
  const scope=span(source),parts=chunks(scope.text);
  for(const item of parts)assert.equal(hash(item.text),reviewed.binding.fragments[item.name].new,'Unreviewed document card source: changed/partial chunk '+item.name);
  let restored=scope.text;
  for(let k=parts.length-1;k>=0;k--)restored=restored.slice(0,parts[k].a)+old[k].text+restored.slice(parts[k].b);
  return source.slice(0,scope.a)+restored+source.slice(scope.b);
}
