import fs from 'node:fs';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
// Exact CSS-only historical boundary. Never a current CSS/source acceptance mask.
const raw=fs.readFileSync(new URL('../fixtures/vault-hint-contrast-reviewed.json',import.meta.url));
const fail='Unreviewed Vault hint contrast',count=(source,part)=>source.split(part).length-1;
assert.equal(createHash('sha256').update(raw).digest('hex'),'c58f59c1da9f1fdeff9582d2d05917d87d92e67cdf91a685bb65037898d44f7b',fail+' authority');
const fixture=JSON.parse(raw),edits=fixture.canonicalChanges,file='static/portal/portal-theme.css';
assert.equal(fixture.task,'VAULT-HINT-CONTRAST-20261119');assert.equal(fixture.base,'5b11e63f178b4ff81c4546462a8cb3ddcdc99fb5');assert.equal(fixture.revision,'ROOT_REVIEWED_R1');assert.equal(edits.length,1);
const edit=edits[0];assert.equal(edit.file,file);assert.equal(edit.count,1);assert.ok(edit.new.startsWith(edit.old));
const addition=edit.new.slice(edit.old.length),marker='/* Keep the file hint readable against the dark dropzone in every interaction state. */';
const selector='html[data-portal-theme="dark"] .portal-page.portal-asset-vault .portal-vault-dropzone small';
assert.equal(addition,'\n'+marker+'\n'+selector+' {\n  color: var(--portal-ink);\n}\n');
export function vaultHintContrastHistoricalCss(source,targetFile){
 assert.equal(typeof source,'string',fail);if(targetFile!==file)return source;
 // Comment removal is observation only; the returned source uses solely the exact immutable OLD/NEW substitution.
 const selectors=[...source.replace(/\/\*[\s\S]*?\*\//g,'').matchAll(/([^{}]+)\{/g)].map(match=>match[1].trim());
 const owned=selectors.filter(value=>value.includes('data-portal-theme')&&value.includes('.portal-asset-vault')&&value.includes('.portal-vault-dropzone')&&/\bsmall\b/.test(value));
 const next=count(source,addition);if(!source.includes(marker)&&!owned.length){assert.equal(next,0,fail+' absent owner');return source;}
 assert.equal(next,1,fail+' partial/changed/duplicate addition');assert.equal(count(source,marker),1,fail+' owner count');assert.deepEqual(owned,[selector],fail+' unknown/reordered/duplicate owned rule');
 assert.equal(count(source,edit.old),1,fail+' prior anchor');assert.equal(count(source,edit.new),1,fail+' detached/reordered append');return source.replace(edit.new,()=>edit.old);
}
