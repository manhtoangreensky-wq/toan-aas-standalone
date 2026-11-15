import assert from 'node:assert/strict';
import fs from 'node:fs';
import {createHash} from 'node:crypto';
import {chatDateHistoricalPortalSource} from './chat-date-snapshot.mjs';
const reviewed=JSON.parse(fs.readFileSync(new URL('../fixtures/chat-page-meta-reviewed.json',import.meta.url),'utf8'));
const keys=new Set(Object.keys(reviewed.vi)),hash=text=>createHash('sha256').update(text).digest('hex');
const hashes={vi:'d4119da82b99375626286760c023e3596330746e253cb2df97c0b378ea331d95',en:'f2f07e43e87e942680adee4d7cf4e96f14330676a5c04d4c2d0627bb3c6d8ff0',zh:'69afb2ccba9f7d3c802ec061d372c26b75f1619ed6b0ab92e637ccccb33af659'};
assert.equal(keys.size,2);
export function pageMetaHistoricalSnapshot(entries,locale){
  assert.ok(hashes[locale]);
  const scoped=entries.filter(([key])=>/^chatPageMetaUi/.test(key));if(!scoped.length)return entries;
  const added=entries.filter(([key])=>keys.has(key));
  assert.equal(scoped.length,added.length,'Unreviewed Chat page metadata copy: unknown key');
  assert.equal(added.length,2,'Unreviewed Chat page metadata copy: missing keys');
  assert.equal(hash(JSON.stringify(added)),hashes[locale],'Unreviewed Chat page metadata copy: value/order');
  return entries.filter(([key])=>!keys.has(key));
}
export const pageMetaFragments=[
  {
    old:'    if (path === "/chat") {\n      return uiText("workspaceMenu.card.chat_workspace.title", fallback);\n    }',
    new:'    if (path === "/chat" || (page && page.layout === "chat-workspace-detail")) {\n      return uiText("chatPageMetaUiTitle", "Trò chuyện");\n    }',
    oldHash:'d5a320175858cea76402115ec5ddcdee46d979e57cf560f99c06781ad1e97872',
    newHash:'6c7075c1ffc3cca7b73be388fc099eb60ab964a8e9fda710e22f853d6a9486dc'
  },
  {
    old:'    if (path === "/chat") {\n      return uiText("workspaceMenu.card.chat_workspace.description", fallback);\n    }',
    new:'    if (path === "/chat" || (page && page.layout === "chat-workspace-detail")) {\n      return uiText("chatPageMetaUiDescription", "Viết và lưu mục tiêu, thông tin tham khảo và ghi chú để xem lại khi cần.");\n    }',
    oldHash:'d2b5de3e12274014b73fa23fd0e0b8e15b8ac430da6ccb9dfbe3830a6a5da7a2',
    newHash:'a2ae0dd8a37b5088d86283b20abb55ce7fa1dc8e3c43201fcdee0bc68164902f'
  },
  {
    old:'  function supportTicketHeroSection(page) {\n    const routeKey = supportTicketHeroRouteKey(page);\n    const route = normalizePath(page && (page.routePath || page.path) || "/");',
    new:'  function supportTicketHeroSection(page) {\n    const routeKey = supportTicketHeroRouteKey(page);\n    const route = normalizePath(page && (page.routePath || page.path) || "/");\n    if (page && page.layout === "chat-workspace-detail") return uiText("chatPageMetaUiTitle", "Trò chuyện");',
    oldHash:'bc27846cedf1828cbca4f37ab6fdd723c991b918fad6a6fadef9c88f88cd10ce',
    newHash:'86ada441f9d975319d8ec0a0debb8d7ac33757226e15af1eff59b48a3b578f92'
  },
  {
    old:'      : ["TOAN AAS", page.section, localizedPageTitle(page, context)])',
    new:'      : ["TOAN AAS", page && page.layout === "chat-workspace-detail" ? uiText("chatPageMetaUiTitle", "Trò chuyện") : page.section, localizedPageTitle(page, context)])',
    oldHash:'4aa7872f703443924cabb489f379d3f963fe553c4abff6a969af101b93b63ef3',
    newHash:'14502e0a88e84635f01c45680e36471dc8d4987804b6e04d424c94ff7646ebb0'
  }
];
for(const fragment of pageMetaFragments){assert.equal(hash(fragment.old),fragment.oldHash);assert.equal(hash(fragment.new),fragment.newHash);}
export function pageMetaHistoricalPortalSource(value){
  let source=chatDateHistoricalPortalSource(value).replace(/\r\n/g,'\n');
  const newCounts=pageMetaFragments.map(edit=>source.split(edit.new).length-1);
  // Earlier historical sources without this unit's markers remain untouched
  // for their original strict gates; no unknown source is silently normalized.
  if(newCounts.every(count=>count===0)&&!source.includes('chatPageMetaUi'))return source;
  assert.ok(newCounts.every(count=>count===1),'Unreviewed Chat page metadata source: partial/duplicate/unknown fragment set');
  for(const edit of [...pageMetaFragments].reverse())source=source.replace(edit.new,edit.old);
  for(const edit of pageMetaFragments)assert.equal(source.split(edit.old).length-1,1,'Unreviewed Chat page metadata source boundary');
  return source;
}
