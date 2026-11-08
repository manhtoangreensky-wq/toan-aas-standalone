import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';

const portal = fs.readFileSync('static/portal/portal.js', 'utf8');
const pages = fs.readFileSync('copyfast_pages.py', 'utf8');
const i18n = fs.readFileSync('static/portal/portal-i18n.js', 'utf8');

test('product library routes have locale-aware first-paint title and description resolvers', () => {
  const titleStart = portal.indexOf('function localizedPageTitle');
  const titleEnd = portal.indexOf('function documentTitle', titleStart);
  const descStart = portal.indexOf('function localizedPageDescription');
  const descEnd = portal.indexOf('function initials', descStart);
  assert.ok(titleStart >= 0 && titleEnd > titleStart);
  assert.ok(descStart >= 0 && descEnd > descStart);
  const title = portal.slice(titleStart, titleEnd);
  const description = portal.slice(descStart, descEnd);
  for (const route of ['/media-workspace', '/media-workspace/new', '/audio-hub', '/audio-hub/new', '/image-hub', '/image-hub/new']) {
    assert.match(title, new RegExp(route.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')), `title resolver missing ${route}`);
    assert.match(description, new RegExp(route.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')), `description resolver missing ${route}`);
  }
});

test('product library shell metadata has VI/EN/ZH entries', () => {
  for (const route of ['/media-workspace', '/media-workspace/new', '/audio-hub', '/audio-hub/new', '/image-hub', '/image-hub/new']) {
    const index = pages.indexOf(`"${route}"`);
    assert.ok(index >= 0, `missing shell route ${route}`);
    const slice = pages.slice(index, index + 500);
    assert.match(slice, /"vi"\s*:/);
    assert.match(slice, /"en"\s*:/);
    assert.match(slice, /"zh"\s*:/);
  }
});

test('product library detail fixed chrome is catalog-backed and action contracts remain', () => {
  const detail = portal.slice(portal.indexOf('function renderAudioHubCollectionBoard'), portal.indexOf('function renderMediaWorkspaceDetail') + 20000);
  assert.match(detail, /audioWorkspaceText|imageStudioDetailText|imageStudioLibraryText/);
  assert.match(detail, /media-item-|audio-change-request-|media-collection-/);
  assert.match(i18n, /AUDIO_WORKSPACE_COPY_ROWS|IMAGE_STUDIO_DETAIL_COPY_ROWS|IMAGE_STUDIO_LIBRARY_COPY_ROWS/);
});
