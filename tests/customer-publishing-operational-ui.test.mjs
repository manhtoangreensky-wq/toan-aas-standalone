import assert from 'node:assert/strict';
import test from 'node:test';
import {renderChild} from './helpers/publishing-child-render.mjs';

const destinations=['/content/channel-strategy','/calendar','/content/publish-review'];
const titles={vi:['Chiến lược kênh','Lịch nội dung','Rà soát bài đăng'],en:['Channel Strategy','Content Calendar','Publish Review'],zh:['渠道策略','内容日历','发布审核']};
const metadata={vi:['Đăng bài','Lập định hướng kênh, sắp xếp lịch nội dung và rà soát bài đăng.'],en:['Publishing','Plan channel direction, organize content dates and review posts.'],zh:['内容发布','规划渠道方向、安排内容日程并审核帖子。']};
for(const locale of['vi','en','zh']){
 const view=renderChild(locale,'/publishing',{});
 test(locale+': honest publishing metadata does not claim automated social posting',()=>{
  assert.equal(view.title,metadata[locale][0]+' · TOAN AAS');
  assert.ok(view.html.includes('<h1')&&view.text.includes(metadata[locale][0]));
  assert.ok(view.text.includes(metadata[locale][1]));
  assert.equal(view.messages[locale]['shellNav.autoPostHub'],metadata[locale][0]);
 });
 test(locale+': publishing shows exactly the three existing operational workflow links',()=>{
  const links=[...view.html.matchAll(/<a\b[^>]*href="([^"]*)"[^>]*>/g)].map(m=>m[1]);
  assert.deepEqual(links.sort(),[...destinations].sort());
  assert.equal((view.html.match(/<button\b/g)||[]).length,0,'no nonfunctional waiting button');
 });
 test(locale+': publishing does not show static permission or unimplemented source/queue cards',()=>{
  assert.doesNotMatch(view.html,/data-autopost-source|portal-autopost-status|portal-autopost-boundary|portal-autopost-steps/);
  assert.doesNotMatch(view.text,/Chờ cấp quyền|Core Bridge|canonical|adapter|capability|Awaiting permission|等待授权/i);
  const cards=view.html.match(/<div class="portal-stack">([\s\S]*?)<\/article>/)?.[1]||'';
  assert.ok(cards,'real tool launcher stack exists');
  assert.doesNotMatch(cards,/<section\b[^>]*>\s*<\/section>/,'no empty card replacing removed UI');
 });
 test(locale+': all three real tools have meaningful selected-language names and actions',()=>{
  assert.ok(view.html.includes('portal-page'));
  for(const title of titles[locale])assert.ok(view.text.includes(title),'localized real tool title: '+title);
  for(const route of destinations){const match=view.html.match(new RegExp('<a\\b[^>]*href="'+route+'"[^>]*>([\\s\\S]*?)<\\/a>'));assert.ok(match&&match[1].replace(/<[^>]*>/g,'').trim().length>2);}
  if(locale==='vi')assert.doesNotMatch(view.text,/\b(?:workspace|hub|source|review|publish|queue|affiliate|workflow)\b/i);
  if(locale==='en')assert.doesNotMatch(view.text,/[À-ỹ\u3400-\u9fff]/);
  if(locale==='zh')assert.doesNotMatch(view.text,/[À-ỹ]/);
 });
}
