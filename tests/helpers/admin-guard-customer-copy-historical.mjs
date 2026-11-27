// Finite AGC inverse for historical QA only; never imported by the application.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {createHash} from 'node:crypto';

const failure='Unreviewed Admin guard customer copy history';
const hash=value=>createHash('sha256').update(value).digest('hex');
const raw=fs.readFileSync(new URL('../fixtures/admin-guard-customer-copy-history.json',import.meta.url),'utf8').replace(/\r\n/g,'\n');
assert.equal(hash(raw),'85dc5ee00b8cb42ec670ec782dbacca6e61d4f33b5436a1d9675b461770f8080',failure+' fixture');
const fixture=JSON.parse(raw);
const targets=new Set(['static/portal/portal.js','static/portal/portal-i18n.js']);
assert.equal(fixture.base_sha,'5f316f29c9b8657c4018f5174c4c4ce4f16c1e5f',failure+' BASE');
assert.equal(fixture.records.length,22,failure+' records');
assert.equal(fixture.owners.length,5,failure+' owners');
assert.deepEqual(fixture.provenance.map(row=>row.conversation_id),[
  '9dbcc5de-90b9-4a79-9a07-d1e98831c3f3',
  'dac917b7-aadc-4c2a-b14b-c6866ccbcf8d',
  'fab6a78b-c666-4cc9-ae63-a8e2c20576aa'
],failure+' provenance');
for(const row of [...fixture.records,...fixture.owners]){
  assert(targets.has(row.file)&&typeof row.before==='string'&&typeof row.after==='string',failure+' row');
  assert.equal(hash(row.before),row.before_lf_sha256,failure+' before hash');
  assert.equal(hash(row.after),row.after_lf_sha256,failure+' after hash');
}
const count=(source,part)=>source.split(part).length-1;
const once=(source,part,label)=>{
  assert(typeof part==='string'&&part.length>0,failure+' nonempty '+label);
  assert.equal(count(source,part),1,failure+' unique '+label);
  return source.indexOf(part);
};
const insertion=fixture.owners.find(row=>row.slot.kind==='insertion');
const actionKeys=[...new Set([...insertion.after.matchAll(/"(actionBlockReason\.[^"]+)"\s*:/g)].map(match=>match[1]))];
assert(actionKeys.length>0,failure+' action keys');
const escape=value=>value.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');
const actionDeclarations=new RegExp('"('+actionKeys.map(escape).join('|')+')"\\s*:','g');
const portalSignal=/uiText\("actionBlockReason\./;

function contextGap(gap){
  let code='',mode='',escaped=false;
  for(let i=0;i<gap.length;i++){
    const char=gap[i],next=gap[i+1];
    if(mode==='line'){
      code+=char==='\n'?'\n':' ';
      if(char==='\n')mode='';
    }else if(mode==='block'){
      if(char==='*'&&next==='/'){code+='  ';i++;mode='';}
      else code+=char==='\n'?'\n':' ';
    }else if(mode){
      code+=char==='\n'?'\n':' ';
      if(escaped)escaped=false;
      else if(char==='\\')escaped=true;
      else if(char===mode)mode='';
    }else if(char==='/'&&next==='/'){code+='  ';i++;mode='line';}
    else if(char==='/'&&next==='*'){code+='  ';i++;mode='block';}
    else if(char==='"'||char==="'"||char==='`'){code+=' ';mode=char;}
    else code+=char;
  }
  assert(!mode||mode==='line',failure+' closed slot comments/strings');
  assert(!/^  (?:async[ \t]+)?(?:function|const|let|class)\b/m.test(code),failure+' no intervening slot declaration');
  const stack=[],opening='([{',closing=')]}';
  for(const char of code){
    if(opening.includes(char))stack.push(char);
    else if(closing.includes(char)){
      assert(stack.pop()===opening[closing.indexOf(char)],failure+' balanced slot context');
    }
  }
  assert.equal(stack.length,0,failure+' no foreign enclosing block');
}

function slot(source,row){
  const start=once(source,row.after,row.name),stop=start+row.after.length;
  const previous=once(source,row.slot.previous,row.name+' previous owner');
  const following=once(source,row.slot.following,row.name+' following owner');
  once(source,row.slot.declaration,row.name+' declaration');
  let lower=previous+row.slot.previous.length;
  if(row.slot.kind==='function'){
    const previousEnd=source.indexOf('\n  }\n',previous);
    assert(previousEnd>previous,failure+' closed previous function');
    lower=previousEnd+5;
  }else{
    assert(['array','insertion'].includes(row.slot.kind),failure+' known slot');
  }
  assert(lower<=start&&start<stop&&stop<=following,failure+' owner slot/order');
  contextGap(source.slice(lower,start));
  if(row.slot.kind==='insertion'){
    const declarations=[...source.matchAll(actionDeclarations)].map(match=>match[1]);
    for(const key of actionKeys)assert.equal(declarations.filter(value=>value===key).length,3,failure+' action declaration ownership');
  }
  return {start,stop};
}

export function adminGuardCustomerCopyHistoricalSource(source,file){
  assert.equal(typeof source,'string',failure+' string source');
  if(!targets.has(file))return source;
  const owners=fixture.owners.filter(row=>row.file===file);
  const records=fixture.records.filter(row=>row.file===file);
  const hasSignal=(file==='static/portal/portal.js'&&portalSignal.test(source))
    || records.some(row=>row.after.length>0&&source.includes(row.after))
    || owners.some(row=>source.includes(row.after));
  if(!hasSignal)return source;
  let previousStop=-1;
  const ranges=[];
  for(const row of owners){
    const {start,stop}=slot(source,row);
    assert(start>=previousStop,failure+' file owner order');
    previousStop=stop;
    ranges.push({start,stop});
  }
  for(const row of records){
    if(!row.after.length)continue;
    const start=once(source,row.after,'approved proposal record');
    assert(ranges.some(range=>range.start<=start&&start+row.after.length<=range.stop),failure+' record ownership');
  }
  for(const row of [...owners].reverse()){
    // Full frozen owners make the empty boundary deletion reversible without
    // replacing an empty string or concealing an unreviewed condition/copy edit.
    once(source,row.after,'approved owner inverse');
    source=source.replace(row.after,()=>row.before);
  }
  return source;
}

const locales=['vi','en','zh'],changedRows=new Map(),oldOrder=[];
for(const owner of fixture.owners.filter(row=>row.slot.kind==='array')){
  const task=owner.name==='ADMIN_SUPPORT_COPY'?'AGC-SUPPORT':'AGC-OPERATIONS';
  const prefix=task==='AGC-SUPPORT'?'adminSupport.':'adminOperations.';
  const rows=fixture.records.filter(row=>row.file.endsWith('portal-i18n.js')&&row.task===task)
    .sort((a,b)=>owner.before.indexOf(a.before)-owner.before.indexOf(b.before));
  for(const row of rows){
    const parse=text=>JSON.parse(text.split('\n')[0].trim().replace(/,$/,''));
    const before=parse(row.before),after=parse(row.after);
    assert(before.length===4&&after.length===4&&before[0]===after[0],failure+' fixed row');
    const key=prefix+before[0];
    assert(!changedRows.has(key),failure+' unique changed row');
    changedRows.set(key,{before:before.slice(1),after:after.slice(1)});oldOrder.push(key);
  }
}
assert.equal(changedRows.size,19,failure+' nineteen changed rows');
const additions=new Map();
for(const match of insertion.after.matchAll(/^  Object\.assign\(MESSAGES\.(vi|en|zh), (\{[^\n]+\})\);$/gm)){
  assert(!additions.has(match[1]),failure+' unique action locale');
  additions.set(match[1],JSON.parse(match[2]));
}
assert.deepEqual([...additions.keys()],locales,failure+' three action locales');
assert.equal(actionKeys.length,12,failure+' twelve added action keys');
for(const locale of locales)assert.deepEqual(Object.keys(additions.get(locale)),actionKeys,failure+' action order');
const addedKeys=new Set(actionKeys),ownedKeys=new Set([...oldOrder,...actionKeys]);
const newOrder=[...oldOrder,...actionKeys];

export function adminGuardCustomerCopyHistoricalSnapshot(entries,locale){
  assert(Array.isArray(entries)&&locales.includes(locale),failure+' snapshot input/locale');
  const owned=entries.filter(row=>row!=null&&ownedKeys.has(row[0]));
  if(!owned.length)return entries;
  assert(entries.every(row=>Array.isArray(row)&&row.length===2),failure+' snapshot pair shape');
  const keys=owned.map(([key])=>key),index=locales.indexOf(locale);
  assert.equal(new Set(keys).size,keys.length,failure+' snapshot unique');
  const old=keys.length===oldOrder.length&&!keys.some(key=>addedKeys.has(key));
  assert.deepEqual(keys,old?oldOrder:newOrder,failure+' snapshot complete/order');
  for(const[key,value]of owned){
    const expected=addedKeys.has(key)?additions.get(locale)[key]:changedRows.get(key)[old?'before':'after'][index];
    assert.equal(value,expected,failure+' snapshot exact locale value');
  }
  if(old)return entries;
  return entries.filter(([key])=>!addedKeys.has(key)).map(row=>changedRows.has(row[0])
    ?[row[0],changedRows.get(row[0]).before[index]]:row);
}
