import assert from "node:assert/strict";
import fs from "node:fs";
import {createHash} from "node:crypto";

const raw=fs.readFileSync(new URL("../fixtures/feature-catalog-descriptions108.json",import.meta.url),"utf8").replace(/\r\n/g,"\n");
assert.equal(createHash("sha256").update(raw).digest("hex"),"0decec95d52d462c18482c823cb7032d8c4f5815cbc78516659f86036430f294");
const fixture=JSON.parse(raw),file="static/portal/portal-feature-catalog-copy.js",rows=fixture.records;
assert.equal(fixture.base_sha,"de870867a27edb02a0d944b3539c0623f1cde3eb");
assert.equal(fixture.beforeLfSha256,"8680e808c06e64358fe63ed08a7b06d21f9ccdc08e48f6e3cf4a19de35f4e329");
assert.equal(fixture.afterLfSha256,"6ca65ab581a72e731203c68ec1e38516305d4c70fd6803c7691234f61c74b1a6");
assert.equal(rows.length,322);assert.equal(fixture.entries.length,108);
assert.equal(new Set(rows.map(row=>row.key+"."+row.locale)).size,322);
assert.ok(rows.every(row=>row.file===file&&row.new!==row.old));
const failure="Unreviewed catalogue descriptions108 historical source";

// Only historical consumers use this leaf; newest CD108 acceptance reads raw bytes.
export function featureCatalogDescriptions108HistoricalSource(source,target){
  if(target!==file||!rows.some(row=>source.includes(row.new)))return source;
  const locales=["vi","en","zh"],bounds=new Map();
  for(const[index,locale]of locales.entries()){
    const start='  "'+locale+'": {\n';
    const end=index<2?'\n  },\n  "'+locales[index+1]+'": {':'\n  }\n});\n})(window);';
    const lower=source.indexOf(start),upper=source.indexOf(end);
    assert(lower>=0&&upper>lower&&lower===source.lastIndexOf(start)&&upper===source.lastIndexOf(end),failure);
    bounds.set(locale,{lower,upper});
  }
  let previous=-1;
  for(const row of rows){
    const at=source.indexOf(row.new),{lower,upper}=bounds.get(row.locale);
    assert(at>=0&&at===source.lastIndexOf(row.new)&&at>previous,failure);
    assert(at>lower&&at+row.new.length<=upper,failure);
    previous=at;
  }
  for(const row of rows)source=source.replace(row.new,()=>row.old);
  return source;
}
