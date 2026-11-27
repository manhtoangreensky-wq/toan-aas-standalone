import assert from "node:assert/strict";
import fs from "node:fs";
import {createHash} from "node:crypto";
import {featureFamilyNativeChromeHistoricalSource,featureFamilyNativeChromeHistoricalSnapshot} from "./feature-family-native-chrome-historical.mjs";
import {featureFamilyReadabilityHistoricalSource} from "./feature-family-readability-historical.mjs";

const raw=fs.readFileSync(new URL("../fixtures/feature-catalog-full-bundle135.json",import.meta.url),"utf8").replace(/\r\n/g,"\n");
assert.equal(createHash("sha256").update(raw).digest("hex"),"bcde5343c0494c81f7deefeb9fcae35293f2ecee4e35e4a35ff4d84ae0f08d28");
const fixture=JSON.parse(raw),file="static/portal/portal-i18n.js",rows=fixture.records;
assert.equal(fixture.base_sha,"fdfe2f753e641c5a5ecc7d6a19305fa3c42b7b30");
assert.equal(fixture.beforeLfSha256,"a342ad1156e277bb3a529b6cda7b396fde528d19bae098a8662c392fb197ae1c");
assert.equal(fixture.afterLfSha256,"6c6e866460c6e0473ecd7dbe6715673cf7ab6019b92f2dd44fa966f21c7105e2");
assert.equal(rows.length,289);assert.equal(fixture.changedExisting.length,286);assert.equal(fixture.missingKeys.length,39);
const canonicalRaw=fs.readFileSync(new URL("../fixtures/feature-catalog-descriptions108.json",import.meta.url),"utf8").replace(/\r\n/g,"\n");
assert.equal(createHash("sha256").update(canonicalRaw).digest("hex"),fixture.canonicalFixtureLfSha256);
const canonical=JSON.parse(canonicalRaw).copy,prefix="featureCatalog.entry.",locales=["vi","en","zh"];
const added=new Set(fixture.missingKeys.flatMap(key=>[prefix+key+".title",prefix+key+".description"]));
const expectedKeys=new Set(fixture.keys.flatMap(key=>[prefix+key+".title",prefix+key+".description"]));
assert.equal(added.size,78);assert.equal(expectedKeys.size,270);
const failure="Unreviewed full-bundle135 historical";

export function featureCatalogFullBundle135HistoricalSource(source,target){
  // Preserve the prior leaf's classification for its shared owner boundaries.
  if(target===file&&[...source.matchAll(/^[ \t]*"(featureCatalog\.entry\.[a-z0-9_]+\.(?:title|description))":/gm)].some(row=>added.has(row[1]))){
    assert.equal(source.split("  const FEATURE_CATALOG_MESSAGES = {").length-1,1,failure);
    assert.equal(source.split("\n  // Media Studio follows").length-1,1,failure);
  }
  source=featureFamilyNativeChromeHistoricalSource(source,target);
  source=featureFamilyReadabilityHistoricalSource(source,target);
  if(target!==file)return source;
  const declarations=[...source.matchAll(/^[ \t]*"(featureCatalog\.entry\.[a-z0-9_]+\.(?:title|description))":/gm)];
  // Without new owned keys, preserve OLD/unknown edits for the original pin.
  if(!declarations.some(row=>added.has(row[1])))return source;
  const counts=new Map();
  for(const row of declarations)counts.set(row[1],(counts.get(row[1])||0)+1);
  for(const key of expectedKeys)assert.equal(counts.get(key),3,failure);
  const start="  const FEATURE_CATALOG_MESSAGES = {",end="\n  // Media Studio follows";
  const lower=source.indexOf(start),upper=source.indexOf(end,lower);
  assert(lower>=0&&upper>lower&&lower===source.lastIndexOf(start)&&upper===source.lastIndexOf(end),failure);
  const section=source.slice(lower,upper),bounds=new Map();
  for(const[index,locale]of locales.entries()){
    const first="    "+locale+": {\n",last=index<2?"\n    },\n    "+locales[index+1]+": {":"\n    }\n  };";
    const a=section.indexOf(first),b=section.indexOf(last,a);
    assert(a>=0&&b>a&&a===section.lastIndexOf(first)&&b===section.lastIndexOf(last),failure);
    bounds.set(locale,{lower:lower+a+first.length,upper:lower+b});
  }
  let prior=-1;
  for(const row of rows){
    const at=source.indexOf(row.new),bound=bounds.get(row.locale);
    assert(at>=bound.lower&&at+row.new.length<=bound.upper&&at===source.lastIndexOf(row.new)&&at>prior,failure);
    prior=at;
  }
  for(const row of rows)source=source.replace(row.new,()=>row.old);
  return source;
}

export function featureCatalogFullBundle135HistoricalSnapshot(entries,locale){
  assert(locales.includes(locale)&&Array.isArray(entries),failure);
  entries=featureFamilyNativeChromeHistoricalSnapshot(entries,locale);
  if(!entries.some(row=>Array.isArray(row)&&added.has(row[0])))return entries;
  const owned=entries.filter(row=>Array.isArray(row)&&expectedKeys.has(row[0]));
  const expectedOrder=[...added,...Object.keys(fixture.beforeCatalog[locale])];
  assert.equal(owned.length,270,failure);assert.equal(new Set(owned.map(row=>row[0])).size,270,failure);
  assert.deepEqual(owned.map(row=>row[0]),expectedOrder,failure);
  for(const[key,value]of owned){
    const found=key.match(/^featureCatalog\.entry\.([a-z0-9_]+)\.(title|description)$/);
    assert.equal(value,canonical[locale][found[1]][found[2]],failure);
  }
  const changed=new Map(fixture.changedExisting.filter(row=>row.locale===locale).map(row=>[row.key,row.old]));
  return entries.filter(row=>!added.has(row[0])).map(row=>changed.has(row[0])?[row[0],changed.get(row[0])]:row);
}
