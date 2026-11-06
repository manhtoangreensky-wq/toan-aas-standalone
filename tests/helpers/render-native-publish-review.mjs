import {renderChild} from './publishing-child-render.mjs';

let input='';for await(const chunk of process.stdin)input+=chunk;
const receipt=JSON.parse(input),pack=receipt.package;
const results=[];
for(const locale of ['vi','en','zh']){
  const r=renderChild(locale,'/content/publish-review',{capabilities:{'publish-review-pack-compose':true},publishReviewPackEnabled:true,publishReviewPackResult:receipt});
  const errors=[];
  const customerText=[pack.title,pack.caption,pack.cta,pack.source_prompt,...pack.hashtags];
  for(const text of customerText)if(!r.text.includes(text))errors.push('customer copy missing');
  // Only these fields came from this test's explicit inputs; system-owned checklist
  // and copy instruction remain in fixedText and must follow the selected locale.
  let fixedText=r.text+' '+r.attributes;
  for(const text of customerText)fixedText=fixedText.replaceAll(text,'');
  if(locale==='vi'&&/\b(?:Web|Bot|Prompt|brief|hashtag|request|CSRF|URL|REF|CTA|caption|claim|asset|format|accessibility|disclosure|text|social|publish|Content Studio|Workboard|Project|Core Bridge)\b/i.test(fixedText))errors.push('foreign fixed system copy');
  if(locale!=='vi'&&/[À-ỹĐđ]/.test(fixedText))errors.push('Vietnamese fixed system copy');
  if(locale==='zh'&&/\b(?:Web|Bot|CSRF|URL|REF|brief|Content Studio|Workboard|Project|Core Bridge)\b/i.test(fixedText))errors.push('English fixed system copy');
  results.push({locale,errors:[...new Set(errors)]});
}
console.log(JSON.stringify({combinations:3,results}));
process.exitCode=results.some(r=>r.errors.length)?1:0;
