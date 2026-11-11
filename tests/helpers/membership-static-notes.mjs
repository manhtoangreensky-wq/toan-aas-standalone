import assert from 'node:assert/strict';

// Match only the old, unconditional two-item implementation explanation. Never
// strip arbitrary customer notes, callouts, server errors or permission states.
export function withoutMembershipStaticNotes(html){
  const openings=[...html.matchAll(/<div class="portal-panel-list">/g)];
  assert.ok(openings.length<=1);
  if(!openings.length)return{html,count:0};
  const start=openings[0].index,tags=/<\/?div\b[^>]*>/g;tags.lastIndex=start;
  let depth=0,end=-1;
  for(let match;(match=tags.exec(html));){depth+=match[0].startsWith('</')?-1:1;if(depth===0){end=tags.lastIndex;break;}}
  assert.ok(end>start);
  const fragment=html.slice(start,end);
  assert.ok(fragment.includes('Tier, trial, grant, rank và package entitlement'));
  assert.ok(fragment.includes('metadata bridge đã redaction'));
  assert.doesNotMatch(fragment,/\b(?:href|data-portal-action)=/);
  return{html:html.slice(0,start)+html.slice(end),count:1};
}
