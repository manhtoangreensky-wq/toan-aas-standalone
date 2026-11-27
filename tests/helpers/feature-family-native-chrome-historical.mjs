// Historical QA only; application files never import this module.
import assert from "node:assert/strict";
import fs from "node:fs";
import {createHash} from "node:crypto";
const raw=fs.readFileSync(new URL("../fixtures/feature-family-native-chrome.json",import.meta.url),"utf8").replace(/\r\n/g,"\n");
const failure="Unreviewed feature-family native chrome";
assert.equal(createHash("sha256").update(raw).digest("hex"),"6da6b40e9a7a62b11363b3af067306e721fb51ddbdb6042b70ac5d601fc7cbff",failure);
const fixture=JSON.parse(raw),locales=["vi","en","zh"];
assert.equal(fixture.base_sha,"363d6ca55081eea4089ebf489cd183b09ba1aa96",failure);
assert.equal(fixture.records.length,21,failure);assert.equal(fixture.changedValues,20,failure);
const files=new Set(fixture.applicationSources.map(row=>row.file));
const owned=new Map(fixture.copyRows.map(row=>[row.key,row]));
assert.equal(owned.size,7,failure);
const escape=value=>value.replace(/[.*+?^${}()|[\]\\]/g,"\\$&");

export function featureFamilyNativeChromeHistoricalSource(source,file){
  if(!files.has(file))return source;
  const rows=fixture.records.filter(row=>row.file===file);
  if(file.endsWith("portal.js")){
    const owner="  function renderFeatureFamily(page, context) {\n",lower=source.indexOf(owner);
    const upper=source.indexOf("\n  function ",lower+owner.length);
    const body=lower>=0&&upper>lower?source.slice(lower,upper):"";
    const marker='<div class="portal-section-heading"><div><h2>';
    if(!source.includes(rows[0].new)&&!body.includes(marker))return source;
    assert(lower>=0&&upper>lower&&source.indexOf(owner)===source.lastIndexOf(owner),failure);
    assert.equal(source.split(rows[0].new).length-1,1,failure);
    assert.equal(source.split(rows[0].old).length-1,0,failure);
    const at=source.indexOf(rows[0].new);assert(at>=lower&&at+rows[0].new.length<=upper,failure);
  }else{
    if(!rows.some(row=>source.includes(row.new)))return source;
    const declaration=new RegExp('^[ \\t]*"('+[...owned.keys()].map(escape).join("|")+')":',"gm");
    const counts=new Map();
    for(const match of source.matchAll(declaration))counts.set(match[1],(counts.get(match[1])||0)+1);
    for(const key of owned.keys())assert.equal(counts.get(key),3,failure);
    const owner="  const FEATURE_CATALOG_MESSAGES = {\n",end="\n  // Media Studio follows";
    const lower=source.indexOf(owner),upper=source.indexOf(end,lower);
    assert(lower>=0&&upper>lower&&lower===source.lastIndexOf(owner)&&upper===source.lastIndexOf(end),failure);
    const section=source.slice(lower,upper),bounds=new Map();
    for(const[index,locale]of locales.entries()){
      const first="    "+locale+": {\n",last=index<2?"\n    },\n    "+locales[index+1]+": {":"\n    }\n  };";
      const a=section.indexOf(first),b=section.indexOf(last,a);
      assert(a>=0&&b>a&&a===section.lastIndexOf(first)&&b===section.lastIndexOf(last),failure);
      bounds.set(locale,{lower:lower+a+first.length,upper:lower+b});
    }
    let previous=-1;
    for(const row of rows){
      const at=source.indexOf(row.new),bound=bounds.get(row.locale);
      assert(at>=bound.lower&&at+row.new.length<=bound.upper&&at===source.lastIndexOf(row.new)&&at>previous,failure);
      assert.equal(source.split(row.old).length-1,0,failure);previous=at;
    }
  }
  for(const row of rows)source=source.replace(row.new,()=>row.old);
  return source;
}

export function featureFamilyNativeChromeHistoricalSnapshot(entries,locale){
  assert(Array.isArray(entries)&&locales.includes(locale),failure);
  const changed=fixture.copyRows.filter(row=>row.before[locale]!==row.after[locale]);
  if(!entries.some(row=>Array.isArray(row)&&changed.some(copy=>row[0]===copy.key&&row[1]===copy.after[locale])))return entries;
  const values=entries.filter(row=>Array.isArray(row)&&owned.has(row[0]));
  assert.equal(values.length,7,failure);assert.equal(new Set(values.map(row=>row[0])).size,7,failure);
  for(const[key,value]of values)assert.equal(value,owned.get(key).after[locale],failure);
  const replacements=new Map(changed.map(row=>[row.key,row.before[locale]]));
  return entries.map(row=>Array.isArray(row)&&replacements.has(row[0])?[row[0],replacements.get(row[0])]:row);
}
