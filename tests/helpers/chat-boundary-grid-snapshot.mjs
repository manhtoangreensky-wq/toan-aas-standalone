import assert from 'node:assert/strict';

export const CHAT_BOUNDARY_GRID_ADDITION='\n/* Let the remaining Chat create panel fill its existing grid. */\n.portal-chat-workspace .portal-chat-workspace-layout > .portal-chat-workspace-create:only-child {\n  grid-column: 1 / -1;\n}\n';
// Historical CSS scopes may omit only this exact reviewed EOF addition.
export function chatBoundaryGridHistoricalCss(value){
  const source=value.replace(/\r\n/g,'\n');
  const count=source.split(CHAT_BOUNDARY_GRID_ADDITION).length-1;
  if(!count)return source;
  assert.equal(count,1,'Unreviewed Chat grid CSS');
  assert.ok(source.endsWith(CHAT_BOUNDARY_GRID_ADDITION),'Unreviewed Chat grid CSS location');
  return source.slice(0,-CHAT_BOUNDARY_GRID_ADDITION.length);
}
