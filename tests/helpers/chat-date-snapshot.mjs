import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {documentCardHistoricalPortalSource} from './document-card-copy-snapshot.mjs';
const hash=text=>createHash('sha256').update(text).digest('hex');
export const chatDateChanges=[
  {
    old:'  function chatRunBadge(value) {',
    new:`  function chatWorkspaceDateLabel(value) {
    try {
      const raw = typeof value === "string" ? value.trim() : value;
      if (!raw || typeof raw === "boolean") return "—";
      const date = raw instanceof Date ? raw : new Date(raw);
      if (!Number.isFinite(date.getTime())) return "—";
      return localizedDateTime(date, { dateStyle: "medium", timeStyle: "short" }) || "—";
    } catch (_) {
      return "—";
    }
  }

  function chatRunBadge(value) {`,
    oldHash:'561af851b5cddc9441161d3421e2e2e7ea29d6de6dc661ee818cccaf31690f75',
    newHash:'51362184535f046bd09ace2a630c9900310575f9d14f070c0164cd44cf930ba6'
  },
  {
    old:'      const timestamp = String(run.updated_at || run.created_at || "—");',
    new:'      const timestamp = chatWorkspaceDateLabel(run.updated_at || run.created_at);',
    oldHash:'f941e242cdab6e81dc9029f5d865f826b0656ce5a8f40fdbb3c7d1d30f7cb120',
    newHash:'cf9a4160c8caca2955959d3da822eaddaa7729fb23138c2563eebbbd3e979eb9'
  },
  {
    old:`safeText(uiText("chatTurnListUiUpdatedAt", "Cập nhật lúc")) + ' ' + safeText(String(item.updated_at || item.created_at || "—"))`,
    new:`safeText(uiText("chatTurnListUiUpdatedAt", "Cập nhật lúc")) + ' ' + safeText(chatWorkspaceDateLabel(item.updated_at || item.created_at))`,
    oldHash:'f8a1831e33cbb235090c809266db6e5b8085e2610e68183e0cc49d27320f5ff9',
    newHash:'49efb20c5bd1d7fcab615d96c1d2660e74da98f96ade5248dcc8d8fa446d1bd8'
  },
  {
    old:`safeText(String(item.created_at || "—")) + '</small></div>' + (Number(item.revision) === Number(thread.revision)`,
    new:`safeText(chatWorkspaceDateLabel(item.created_at)) + '</small></div>' + (Number(item.revision) === Number(thread.revision)`,
    oldHash:'9ade3bc90cb80b1b5385b32a54a2ce6167c3253de5af526b21e603aa7c450008',
    newHash:'7cef0b5be500493e8c4b780a236436b0fe36b98afb55274e153e9c6b3c20014b'
  },
  {
    old:`safeText(uiText("chatCardsUiUpdate", "Lần cập nhật")) + ' ' + safeText(String(item.revision || 1)) + ' · ' + safeText(String(item.created_at || "—")) + '</small></span></div>'`,
    new:`safeText(uiText("chatCardsUiUpdate", "Lần cập nhật")) + ' ' + safeText(String(item.revision || 1)) + ' · ' + safeText(chatWorkspaceDateLabel(item.created_at)) + '</small></span></div>'`,
    oldHash:'76ef13f9c8d8dbf8b0f03d91f47938f7091fdb99006feb41ef524907434b886b',
    newHash:'1651d24fb85aa34016117bbf9104b3a09721aa5cd78192e4867287d57d202ed6'
  }
];
for(const edit of chatDateChanges){assert.equal(hash(edit.old),edit.oldHash);assert.equal(hash(edit.new),edit.newHash);}
export function chatDateHistoricalPortalSource(value){
  let source=documentCardHistoricalPortalSource(value).replace(/\r\n/g,'\n');
  if(!source.includes('chatWorkspaceDateLabel'))return source;
  assert.ok(chatDateChanges.every(edit=>source.split(edit.new).length-1===1),'Unreviewed Chat date source: partial/duplicate/changed helper or call context');
  for(const edit of [...chatDateChanges].reverse())source=source.replace(edit.new,edit.old);
  assert.equal(source.includes('chatWorkspaceDateLabel'),false,'Unreviewed Chat date source: unreviewed extra call');
  for(const edit of chatDateChanges)assert.equal(source.split(edit.old).length-1,1,'Unreviewed Chat date source boundary');
  return source;
}
