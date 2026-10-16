import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';

const i18nSource = fs.readFileSync('static/portal/portal-i18n.js', 'utf8');
const portalSource = fs.readFileSync('static/portal/portal.js', 'utf8');
const viStart = i18nSource.indexOf('Object.assign(SUPPORT_TICKET_MESSAGES.vi, {');
const enStart = i18nSource.indexOf('Object.assign(SUPPORT_TICKET_MESSAGES.en, {', viStart);
assert.ok(viStart >= 0 && enStart > viStart, 'Support Ticket Vietnamese catalogue must remain present');
const vi = i18nSource.slice(viStart, enStart);
const values = [...vi.matchAll(/^\s*"supportTicket\.[^"]+":\s*"([^"]*)"/gm)].map((match) => match[1]);

const renderStart = portalSource.indexOf('function renderSupportAdvisor(');
const renderEnd = portalSource.indexOf('function renderTickets(', renderStart);
assert.ok(renderStart >= 0 && renderEnd > renderStart, 'Support Ticket customer renderer must remain present');
const renderer = portalSource.slice(renderStart, renderEnd);
const fallbacks = [...renderer.matchAll(/supportTicketText\(\s*"[^"]+"\s*,\s*"([^"\\]*(?:\\.[^"\\]*)*)"/g)].map((match) => match[1]);

const genericEnglish = /\b(?:support desk|signed|web|timeline|case|role|owner|integrity|external|asset vault|secret|upload|private|payment proof|provider|activity|session|native|engine|inbox|audit|write|server|file|ticket|canonical|ledger|order|raw|browser|storage|receipt|revision|workflow|public|notification|password|token|account|version|operations|autopilot|metadata|refund|operator|triage|catalog|lead|filter|web-only|webapp|review|fallback|owner-scoped|server-side|attachment|checklist|form|redaction|proof|bill)\b/i;

test('Vietnamese Support Ticket fixed chrome stays free of generic English', () => {
  assert.equal(values.length, 295, 'Support Ticket must keep the complete fixed catalogue');
  const visibleCopy = values.join(' | ').replace(/\{[^}]+\}/g, '');
  assert.doesNotMatch(visibleCopy, genericEnglish, 'generic English leaked into the Vietnamese Support Ticket catalogue');
});

test('Support Ticket renderer fallbacks stay Vietnamese and preserve contracts', () => {
  assert.ok(fallbacks.length >= 210, 'Support Ticket renderer must keep explicit safe fallbacks');
  const visibleCopy = fallbacks.join(' | ').replace(/\{[^}]+\}/g, '');
  assert.doesNotMatch(visibleCopy, genericEnglish, 'generic English leaked into Support Ticket renderer fallbacks');
  assert.match(renderer, /data-portal-action="support-case-create"/);
  assert.match(renderer, /data-portal-action="support-case-reply"/);
  assert.match(renderer, /data-portal-action="support-case-attachment"/);
  assert.match(renderer, /data-support-case-id=/);
  assert.match(renderer, /data-support-case-revision=/);
  assert.match(renderer, /supportTicketText\("triage\.title"/);
  assert.match(renderer, /supportTicketText\("case\.subjectFallback"/);
  assert.doesNotMatch(renderer, /supportTicketText\("(?:phân loại|yêu cầu|trực tuyến)\./, 'locale text must not replace support message keys');
});
