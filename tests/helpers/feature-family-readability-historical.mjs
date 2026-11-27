// Historical CSS input only. Current acceptance reads the physical stylesheet.
import assert from "node:assert/strict";
const file="static/portal/portal-theme.css",fail="Unreviewed feature-family readability";
const scope='[data-portal-main][data-portal-presentation-route="default"] > .portal-page:has(> .portal-feature-jumps)';
const marker="/* Keep family-directory text readable without changing surfaces or motion. */";
const selectors=[
  'html:not([data-portal-theme="dark"]) '+scope+' > .portal-feature-jumps a.portal-feature-jump:is(:hover, :focus-visible)',
  'html[data-portal-theme="dark"] '+scope+' > .portal-feature-jumps .portal-feature-jump--current',
  'html:not([data-portal-theme="dark"]) '+scope+' > .portal-feature-catalog > .portal-empty p',
  'html:not([data-portal-theme="dark"]) '+scope+' > .portal-hero .portal-eyebrow'
];
export const FAMILY_READABILITY_ADDITION="\n"+marker+"\n"+selectors.map(selector=>selector+" {\n  color: var(--portal-text);\n}").join("\n")+"\n";
const anchor="/* Clean end-user catalog cards: hide technical engine, boundary and readiness labels */\n.portal-module-card-signals,\n.portal-boundary-label,\n.portal-engine-label,\n.portal-readiness-label {\n  display: none !important;\n}\n\n";
const count=(source,part)=>source.split(part).length-1;
export function featureFamilyReadabilityHistoricalSource(source,target){
  assert.equal(typeof source,"string",fail);
  if(target!==file)return source;
  const owner=source.includes(marker)||source.includes(scope);
  if(!owner)return source;
  assert.equal(count(source,marker),1,fail+" marker");
  assert.equal(count(source,scope),4,fail+" four owners");
  for(const selector of selectors)assert.equal(count(source,selector),1,fail+" exact selectors");
  assert.equal(count(source,anchor),1,fail+" prior anchor");
  assert.equal(count(source,FAMILY_READABILITY_ADDITION),1,fail+" exact four rules");
  assert.equal(count(source,anchor+FAMILY_READABILITY_ADDITION),1,fail+" placement/order");
  return source.replace(anchor+FAMILY_READABILITY_ADDITION,()=>anchor);
}
