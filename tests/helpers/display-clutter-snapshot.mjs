import fs from "node:fs";
import assert from "node:assert/strict";
const fixture=JSON.parse(fs.readFileSync(new URL("../fixtures/display-clutter-reviewed.json",import.meta.url),"utf8"));
export function displayClutterHistoricalPortalSource(value){
  let source=value.replace(/\r\n/g,"\n");
  const counts=fixture.changes.map(edit=>({old:source.split(edit.old).length-1,next:source.split(edit.new).length-1}));
  // Older release inputs may predate these localized Document paragraphs.
  // With no new chunk, keep every byte for their original comparators.
  if(!counts.some(({old,next})=>old===0&&next>0))return source;
  const states=counts.map(({old,next})=>{
    // The retained paragraph is a substring of OLD. Distinguish the removal
    // by its full old fragment first, never by a broad text/prefix filter.
    if(old===1)return "old";
    assert.equal(old,0,"Unreviewed display-clutter old fragment");
    assert.equal(next,1,"Unreviewed display-clutter new fragment");
    return "new";
  });
  assert.ok(states.every(state=>state===states[0]),"Unreviewed partial display-clutter change");
  if(states[0]==="old")return source;
  for(const edit of [...fixture.changes].reverse()){
    assert.equal(source.split(edit.new).length-1,1,"Unreviewed display-clutter boundary");
    source=source.replace(edit.new,()=>edit.old);
  }
  return source;
}
