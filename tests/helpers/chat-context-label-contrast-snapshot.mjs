import assert from 'node:assert/strict';
import {pdfSplitReadabilityHistoricalCss} from './pdf-split-readability-snapshot.mjs';

export const CHAT_CONTEXT_LABEL_CONTRAST_ADDITION='\n/* Keep saved Chat note labels readable in the light theme. */\nhtml:not([data-portal-theme="dark"]) .portal-chat-workspace-detail .portal-chat-context-edit .portal-field > span {\n  color: var(--portal-ink);\n}\n';
export function chatContextLabelHistoricalCss(value){
  const source=pdfSplitReadabilityHistoricalCss(value);
  const count=source.split(CHAT_CONTEXT_LABEL_CONTRAST_ADDITION).length-1;
  if(!count)return source;
  assert.equal(count,1,'Unreviewed Chat context label CSS');
  assert.ok(source.endsWith(CHAT_CONTEXT_LABEL_CONTRAST_ADDITION),'Unreviewed Chat context label CSS location');
  return source.slice(0,-CHAT_CONTEXT_LABEL_CONTRAST_ADDITION.length);
}
