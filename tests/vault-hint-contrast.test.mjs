import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {vaultHintContrastHistoricalCss as inverse} from './helpers/vault-hint-contrast-snapshot.mjs';
import {vaultCustomerHistoricalSource as vaultInverse,vaultCustomerHistoricalSnapshot as vaultSnapshot} from './helpers/vault-customer-copy-snapshot.mjs';
Error.stackTraceLimit=0;
const ROOT=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..'),BASE='5b11e63f178b4ff81c4546462a8cb3ddcdc99fb5',CSS='static/portal/portal-theme.css';
const hash=x=>createHash('sha256').update(x).digest('hex'),lf=x=>x.replace(/\r\n/g,'\n'),count=(s,p)=>s.split(p).length-1;
const raw=fs.readFileSync(new URL('./fixtures/vault-hint-contrast-reviewed.json',import.meta.url)),fixture=JSON.parse(raw),edit=fixture.canonicalChanges[0];
const originalRaw=fs.readFileSync(new URL('./fixtures/vault-customer-copy-reviewed.json',import.meta.url)),original=JSON.parse(originalRaw);
const baseCss=lf(execFileSync('git',['show',BASE+':'+CSS],{cwd:ROOT,encoding:'utf8',maxBuffer:8e6})),actualCss=lf(fs.readFileSync(path.join(ROOT,CSS),'utf8'));
assert.equal(count(baseCss,edit.old),1);const candidate=baseCss.replace(edit.old,()=>edit.new),addition=edit.new.slice(edit.old.length);
const selector='html[data-portal-theme="dark"] .portal-page.portal-asset-vault .portal-vault-dropzone small';
const importLine="import {vaultHintContrastHistoricalCss} from './helpers/vault-hint-contrast-snapshot.mjs';\n";
const physicalPath='tests/vault-customer-copy.test.mjs',sourcePath='tests/vault-customer-copy-source.test.mjs';
const read=file=>lf(fs.readFileSync(path.join(ROOT,file),'utf8'));
test('authority binds one exact first-round worker CSS rule and preserves the prior immutable copy authority',()=>{
 assert.equal(hash(raw),'c58f59c1da9f1fdeff9582d2d05917d87d92e67cdf91a685bb65037898d44f7b');assert.equal(fixture.task,'VAULT-HINT-CONTRAST-20261119');assert.equal(fixture.base,BASE);assert.equal(fixture.revision,'ROOT_REVIEWED_R1');assert.equal(fixture.canonicalChanges.length,1);assert.equal(edit.file,CSS);assert.equal(edit.count,1);
 assert.deepEqual(fixture.sourceAuthority,{conversation:'f7770b7d-9716-4cf3-8ac4-3765d01014e6',packetSha256:'8b3bd708ab23a16c7bccd87a7bb9fddd8bccb1ac5b37a3d01059b3ec6207b96b',resultRawSha256:'9b5d244c599bc9208c9255bdbc522c785059b9a2e169f1bcf45df3d353804965',schemaValid:true,proposalExact:true,verify:'NOT_RUN',applicationWrites:0});
 assert.equal(fixture.applicationWrites,0);assert.equal(fixture.applicationFailureCount,0);assert.equal(fixture.rootApplicationTakeover,false);assert.equal(hash(originalRaw),'2b895f84f77c8656811c4e732506926a677dda1eb6aa824f854670e127e8228b');assert.equal(fixture.priorVaultCopyAuthorityRawSha256,hash(originalRaw));
});
test('actual current CSS independently equals BASE plus exactly one append with every outside byte unchanged',()=>{
 assert.equal(hash(baseCss),'9706f04bc230531f2e4bb77a6bb0c715061711cd33ca8510104859e25285639f');assert.equal(fixture.baselineLfSha256,hash(baseCss));assert.equal(actualCss,candidate,'Actual candidate acceptance must not consume inverse output');assert.equal(hash(actualCss),'353ce66afb195a866156ba6a1c523486dd3c8d620a082bcaf086ae7ea13825d2');assert.equal(fixture.candidateLfSha256,hash(actualCss));assert.ok(actualCss.endsWith(addition));
});
test('independent151-file overlay requires4actual changed files and147protected without masking the CSS addition',()=>{
 assert.equal(original.applicationBaseline.length,151);const changed=original.applicationBaseline.filter(pin=>pin.changed).map(pin=>pin.file);assert.equal(changed.length,3);assert.ok(!changed.includes(CSS));changed.push(CSS);assert.equal(new Set(changed).size,4);
 for(const pin of original.applicationBaseline){const actual=hash(read(pin.file)),wanted=pin.file===CSS?fixture.candidateLfSha256:pin.candidateLfSha256;assert.equal(actual,wanted,pin.file);if(!changed.includes(pin.file))assert.equal(pin.baselineLfSha256,pin.candidateLfSha256);if(pin.file===CSS){assert.equal(pin.baselineLfSha256,fixture.baselineLfSha256);assert.equal(pin.candidateLfSha256,fixture.baselineLfSha256);}}
 assert.equal(original.applicationBaseline.filter(pin=>!changed.includes(pin.file)).length,147);
});
test('finite CSS inverse accepts OLD/NEW idempotently and preserves unrelated files and all prefix/suffix bytes',()=>{
 const first='\r\n/* CUSTOMER media studio provider Facebook TikTok */\r\n',last='\r\n/* unrelated literal .portal-vault-dropzone small */\r\n';
 assert.equal(inverse(baseCss,CSS),baseCss);assert.equal(inverse(candidate,CSS),baseCss);assert.equal(inverse(inverse(candidate,CSS),CSS),baseCss);
 for(const source of [baseCss,candidate])assert.equal(inverse(first+source+last,CSS),first+baseCss+last);assert.equal(inverse(first+last,CSS),first+last);assert.equal(inverse(candidate,'customer/unrelated.css'),candidate);assert.ok(inverse(candidate+last,CSS).endsWith(last));assert.notEqual(inverse(candidate+last,CSS),baseCss);
});
test('finite CSS inverse rejects changed partial mixed duplicate detached reordered or unknown owned rules',()=>{
 const changes=[addition.replace('--portal-ink','--portal-muted'),addition.replace('"dark"','"light"'),addition.replace('color:','background:'),addition.replace('small {','strong {'),addition.replace('.portal-asset-vault','.portal-image-resize'),addition.replace('/* Keep the file hint readable against the dark dropzone in every interaction state. */\n',''),addition.slice(0,-2)];
 for(const change of changes)assert.throws(()=>inverse(candidate.replace(addition,change),CSS),/Unreviewed Vault hint contrast/);
 for(const malformed of [candidate+addition,baseCss+'\n/* detached */'+addition,addition+baseCss,candidate+'\n'+selector+' { opacity: .5; }\n',candidate+'\n'+selector.replace('"dark"','"light"')+' { color: red; }\n',candidate.replace(edit.new,edit.new.replace('text-overflow: clip;','text-overflow: ellipsis;'))])assert.throws(()=>inverse(malformed,CSS),/Unreviewed Vault hint contrast/);
});
test('one dark route/dropzone color property wins normal hover focus specificity without light layout font motion or important changes',()=>{
 const withoutComments=addition.replace(/\/\*[\s\S]*?\*\//g,'').trim(),rule=withoutComments.match(/^([^{}]+)\{([^{}]+)\}$/);assert.ok(rule);assert.equal(rule[1].trim(),selector);assert.equal(rule[2].trim(),'color: var(--portal-ink);');assert.equal(count(withoutComments,'{'),1);
 assert.doesNotMatch(addition,/!important|font-|padding|margin|width|height|transform|transition|animation|light|:hover|:focus/);
 const specificity=value=>{const attributes=(value.match(/\[[^\]]+\]/g)||[]).length,classes=(value.replace(/\[[^\]]+\]/g,'').match(/\.[A-Za-z][\w-]*/g)||[]).length,elements=value.replace(/\[[^\]]+\]/g,'').replace(/\.[A-Za-z][\w-]*/g,'').trim().split(/\s+/).filter(Boolean).length;return[0,attributes+classes,elements];};
 const newSpecificity=specificity(selector),oldSpecificity=specificity('.portal-page.portal-asset-vault .portal-vault-dropzone small');assert.deepEqual(newSpecificity,[0,4,2]);assert.deepEqual(oldSpecificity,[0,3,1]);assert.ok(newSpecificity[1]>oldSpecificity[1]);assert.ok(selector.startsWith('html[data-portal-theme="dark"] '));
 assert.match(baseCss,/\.portal-page\.portal-asset-vault \.portal-vault-dropzone small\s*\{\s*color: var\(--portal-muted\);\s*font-size: 13px;/);
 assert.match(baseCss,/\.portal-page\.portal-asset-vault :is\(\.portal-vault-dropzone:hover, \.portal-vault-dropzone:focus-within\)\s*\{[^}]*background:[^}]*transform: none;/);
 assert.ok(candidate.indexOf(addition)>candidate.indexOf('.portal-page.portal-asset-vault .portal-vault-dropzone small'),'Later and more-specific exact rule applies to the same descendant in normal/hover/focus; dark-only selector excludes light and other routes');
});
test('contrast luminance math exceeds4.5 for reviewed ink on measured background; this is math not new native evidence',()=>{
 const luminance=hex=>{const values=hex.match(/[0-9a-f]{2}/gi).map(v=>parseInt(v,16)/255).map(v=>v<=.04045?v/12.92:((v+.055)/1.055)**2.4);return .2126*values[0]+.7152*values[1]+.0722*values[2];};
 const ratio=(a,b)=>{const values=[luminance(a),luminance(b)].sort((x,y)=>y-x);return(values[0]+.05)/(values[1]+.05);};
 const old=ratio('83a5ad','134e5a'),next=ratio('f3fbfc','134e5a');assert.ok(Math.abs(old-3.5100441173202004)<1e-12);assert.ok(old<4.5);assert.ok(next>=4.5);assert.ok(next>old);assert.match(baseCss,/--portal-teal-dark-ink:\s*#f3fbfc;/);
});
test('all three previously accepted copy-source hashes remain exact and unchanged by this CSS overlay',()=>{
 const changed=original.applicationBaseline.filter(pin=>pin.changed);assert.equal(changed.length,3);assert.deepEqual(changed.map(pin=>pin.file).sort(),['copyfast_pages.py','static/portal/portal-i18n.js','static/portal/portal.js']);for(const pin of changed)assert.equal(hash(read(pin.file)),pin.candidateLfSha256,pin.file);
});
test('CSS type guard and historical151-pin boundary remain explicit with full physical renderer inputs',()=>{
 assert.throws(()=>inverse(null,CSS),/Unreviewed Vault hint contrast/);assert.throws(()=>inverse(null,'other.css'),/Unreviewed Vault hint contrast/);assert.equal(inverse('/* old unrelated CSS */',CSS),'/* old unrelated CSS */');
 assert.throws(()=>vaultInverse(null,'static/portal/portal.js'),/Unreviewed Vault customer copy/);assert.throws(()=>vaultSnapshot(null,'vi'),/Unreviewed Vault customer copy/);assert.throws(()=>vaultSnapshot([],'fr'),/Unreviewed Vault customer copy/);
 const physical=read(physicalPath),source=read(sourcePath);assert.equal(count(physical,'vaultHintContrastHistoricalCss(actualSource,pin.file)'),1);assert.equal(count(source,"vaultHintContrastHistoricalCss(lf(fs.readFileSync(path.join(ROOT,pin.file),'utf8')),pin.file)"),1);assert.ok(physical.includes('const actual=await pageMetaRenderer(physical),before=await pageMetaRenderer(baseline);'));assert.equal(count(physical,importLine),1);assert.equal(count(source,importLine),1);
});
test('original27physical and18source test logic remains LF-exact after removing only the CSS pin-boundary import/call',()=>{
 const physical=read(physicalPath).replace(importLine,'').replace('hash(vaultHintContrastHistoricalCss(actualSource,pin.file))','hash(actualSource)');
 const source=read(sourcePath).replace(importLine,'').replace("hash(vaultHintContrastHistoricalCss(lf(fs.readFileSync(path.join(ROOT,pin.file),'utf8')),pin.file))","hash(lf(fs.readFileSync(path.join(ROOT,pin.file),'utf8')))");
 assert.equal(hash(physical),'1eec8eed66c31e781dae1dc9f906d4af5a6c55415e090d368966c8afad5bae62');assert.equal(hash(source),'e5e64467687258409b815dcfafad58ccd26e457c587cc2b799cabee1b489d518');
});
