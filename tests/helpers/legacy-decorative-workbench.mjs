import assert from 'node:assert/strict';

// Historical comparison only: remove the exact old alert-only decoration,
// never a real form/action or arbitrary text/card/customer content.
export function withoutLegacyDecorativeWorkbench(html){
  const opening='<div class="portal-interactive-feature-workbench"';
  const start=html.indexOf(opening);
  if(start<0)return{html,count:0};
  assert.equal(html.indexOf(opening,start+opening.length),-1,'at most one historical panel per page');
  const tags=/<\/?div\b[^>]*>/g;tags.lastIndex=start;let depth=0,end=-1;
  for(let match;(match=tags.exec(html));){
    depth+=match[0].startsWith('</')?-1:1;
    if(depth===0){end=tags.lastIndex;break;}
  }
  assert.ok(end>start,'historical workbench must have a balanced closing div');
  const fragment=html.slice(start,end);
  assert.equal((fragment.match(/onclick="alert\(/g)||[]).length,2,'only the two known alert-only controls');
  assert.doesNotMatch(fragment,/<form\b|\bname=|data-portal-action|data-portal-form|\bfetch\s*\(/i,'never remove a real form/API action');
  assert.deepEqual([...fragment.matchAll(/href="([^"]*)"/g)].map(match=>match[1]),['/studio'],'only the explicit duplicate studio link may disappear');
  return{html:html.slice(0,start)+html.slice(end),count:1};
}
