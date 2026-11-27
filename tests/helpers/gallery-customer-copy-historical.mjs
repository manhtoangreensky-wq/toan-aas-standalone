// Exact finite Gallery input inverse for historical tests, never runtime code.
import assert from "node:assert/strict";
import fs from "node:fs";
import {createHash} from "node:crypto";
import {galleryReadabilityHistoricalSource} from "./gallery-readability-historical.mjs";
import {galleryNativeHistoricalSource,galleryNativeHistoricalSnapshot} from "./gallery-native-historical.mjs";
const raw=fs.readFileSync(new URL("../fixtures/gallery-customer-copy.json",import.meta.url),"utf8").replace(/\r\n/g,"\n");
const fail="Unreviewed Gallery customer copy";
assert.equal(createHash("sha256").update(raw).digest("hex"),"c376690961cee3c23c17d0c4479f311b93e16bfcc8fda9d6abf6d6f07264e1ef",fail);
const fixture=JSON.parse(raw),files=new Set(fixture.applicationSources.map(row=>row.file));
assert.equal(fixture.base_sha,"bf95e4017717622d694cbef02fde07799a823a8a",fail);
assert.equal(fixture.records.length,56,fail);assert.equal(fixture.copyRows.length,17,fail);
const count=(source,part)=>source.split(part).length-1;
const escape=value=>value.replace(/[.*+?^${}()|[\]\\]/g,"\\$&");
export function galleryCustomerCopyHistoricalSource(source,file){
  assert.equal(typeof source,"string",fail);
  source=galleryNativeHistoricalSource(source,file);
  source=galleryReadabilityHistoricalSource(source,file);
  if(!files.has(file))return source;
  const records=fixture.records.filter(row=>row.file===file);
  if(!records.some(row=>source.includes(row.new)))return source;
  let previous=-1;
  if(file.endsWith("portal-i18n.js")){
    const declarations=new RegExp('^[ \\t]*"('+fixture.copyRows.map(row=>escape(row.key)).join("|")+')":',"gm");
    const counts=new Map();for(const match of source.matchAll(declarations))counts.set(match[1],(counts.get(match[1])||0)+1);
    for(const copy of fixture.copyRows)assert.equal(counts.get(copy.key),3,fail+" key ownership");
    for(const row of records){
      const owner="  const "+row.owner+" = {\n",a=source.indexOf(owner),b=source.indexOf("\n  };",a);
      assert(a>=0&&b>a&&count(source,owner)===1,fail+" object owner");
      const section=source.slice(a,b+6),locale="    "+row.locale+": {\n",lo=section.indexOf(locale);
      const index=["vi","en","zh"].indexOf(row.locale);
      const end=index<2?'\n    },\n    '+["en","zh"][index]+': {':'\n    }\n  };';
      const hi=section.indexOf(end,lo);assert(lo>=0&&hi>lo&&count(section,locale)===1,fail+" locale owner");
      const at=source.indexOf(row.new);assert.equal(count(source,row.new),1,fail+" exact copy");
      assert(at>=a+lo+locale.length&&at+row.new.length<=a+hi&&at>previous,fail+" placement/order");previous=at;
    }
  }else{
    for(const row of records){
      const owner="  function "+row.owner+"(",a=source.indexOf(owner);assert(a>=0&&count(source,owner)===1,fail+" function owner");
      const at=source.indexOf(row.new);assert.equal(count(source,row.new),1,fail+" exact source");
      if(row.owner==="freePromptGalleryCatalogState"){
        const helper="  function freePromptGallerySourceText(",lower=source.indexOf(helper);
        assert(lower>=0&&count(source,helper)===1&&at===lower&&at+row.new.length===a+row.old.length,fail+" helper insertion");
      }else{
        const end=source.indexOf("\n  }\n",a)+5;assert(at>=a&&at+row.new.length<=end,fail+" source placement");
      }
      assert(at>previous,fail+" source order");previous=at;
    }
  }
  for(const row of records)source=source.replace(row.new,()=>row.old);
  return source;
}

// Full-dictionary comparisons need the same finite projection as source readers.
const snapshotRows=new Map(fixture.copyRows.map(row=>[row.key,row]));
const snapshotOrder=["shellNav.freePromptGallery",...fixture.copyRows.filter(row=>row.key!=="shellNav.freePromptGallery").map(row=>row.key)];
export function galleryCustomerCopyHistoricalSnapshot(entries,locale){
  const failure=fail+" snapshot";
  assert(Array.isArray(entries)&&["vi","en","zh"].includes(locale),failure+" input");
  entries=galleryNativeHistoricalSnapshot(entries,locale);
  const values=entries.filter(row=>Array.isArray(row)&&snapshotRows.has(row[0]));
  if(!values.length)return entries;
  assert(values.every(row=>row.length===2),failure+" pair shape");
  assert.equal(values.length,17,failure+" complete");
  assert.equal(new Set(values.map(row=>row[0])).size,17,failure+" unique");
  assert.deepEqual(values.map(row=>row[0]),snapshotOrder,failure+" order");
  if(values.every(([key,value])=>value===snapshotRows.get(key).before[locale]))return entries;
  for(const[key,value]of values)assert.equal(value,snapshotRows.get(key).after[locale],failure+" exact locale value");
  return entries.map(row=>Array.isArray(row)&&snapshotRows.has(row[0])?[row[0],snapshotRows.get(row[0]).before[locale]]:row);
}
