import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';

const portalCss = fs.readFileSync('static/portal/portal.css', 'utf8');
const themeCss = fs.readFileSync('static/portal/portal-theme.css', 'utf8');
const portalJs = fs.readFileSync('static/portal/portal.js', 'utf8');
const legacyDashboardTemplate = fs.readFileSync('templates/dashboard.html', 'utf8');

function selectorBlocks(selector, source) {
  const escaped = selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const matches = [...source.matchAll(new RegExp(`${escaped}\\s*\\{([^}]*)\\}`, 'g'))];
  return matches.map(match => match[1]);
}

function mediaBlocks(source, expression) {
  const header = new RegExp(expression, 'g');
  const blocks = [];
  for (const match of source.matchAll(header)) {
    const open = source.indexOf('{', match.index + match[0].length);
    if (open < 0) continue;
    let depth = 0;
    for (let index = open; index < source.length; index += 1) {
      if (source[index] === '{') depth += 1;
      else if (source[index] === '}') {
        depth -= 1;
        if (depth === 0) {
          blocks.push(source.slice(open + 1, index));
          break;
        }
      }
    }
  }
  return blocks;
}

const reducedMotionBlocks = source => mediaBlocks(source, '@media\\s*\\(prefers-reduced-motion:\\s*reduce\\)');
const adminScope = '.portal-shell[data-portal-app-kind="admin"]';

test('Admin work-queue hover transitions only properties it changes', () => {
  const blocks = selectorBlocks(`${adminScope} .portal-admin-work-queue`, themeCss);
  assert.ok(blocks.length > 0);
  assert.equal(blocks.some(block => /transition\s*:\s*all\b/i.test(block)), false);
  assert.match(blocks.join('\n'), /transition\s*:[^;]*(?:transform|border-color|background-color|color|box-shadow)/i);
});

test('Admin tabs do not animate font-weight or layout with transition all', () => {
  const blocks = selectorBlocks(`${adminScope} .portal-admin-tab`, themeCss);
  assert.ok(blocks.length > 0);
  assert.equal(blocks.some(block => /transition\s*:\s*all\b/i.test(block)), false);
  assert.match(blocks.join('\n'), /transition\s*:[^;]*(?:color|background-color|border-color|box-shadow)/i);
});

test('Reduced-motion disables the Admin work-queue and tab transitions', () => {
  const blocks = reducedMotionBlocks(themeCss);
  assert.ok(blocks.some(block => /\.portal-admin-work-queue[\s\S]{0,220}transition\s*:\s*none\s*!important/i.test(block)
    && /\.portal-admin-work-queue[\s\S]{0,220}transform\s*:\s*none\s*!important/i.test(block)));
  assert.ok(blocks.some(block => /\.portal-admin-tab[\s\S]{0,220}transition\s*:\s*none\s*!important/i.test(block)));
});

test('Reduced-motion leaves the boot loader static and readable', () => {
  const blocks = reducedMotionBlocks(portalCss);
  assert.ok(blocks.some(block => /\.portal-loader[\s\S]{0,100}animation\s*:\s*none\s*!important/i.test(block)));
});

test('Reduced-motion leaves the Project-detail loading icon static', () => {
  const blocks = reducedMotionBlocks(themeCss);
  assert.ok(blocks.some(block => /portal-project-detail--loading[\s\S]{0,180}animation\s*:\s*none\s*!important/i.test(block)));
});

test('Reduced-motion leaves the Workboard loading surface static', () => {
  const blocks = reducedMotionBlocks(themeCss);
  assert.ok(blocks.some(block => /\.portal-workboard-recovery\[data-workboard-read-state="loading"\][\s\S]{0,180}animation\s*:\s*none\s*!important/i.test(block)));
});

test('Portal renderers do not add inline transition-all motion', () => {
  assert.doesNotMatch(portalJs, /transition\s*:\s*all\b/i);
});

test('Legacy dashboard template does not use shorthand all-property transitions', () => {
  assert.doesNotMatch(legacyDashboardTemplate, /transition\s*:\s*\.2s\b/i);
});

test('Landing mobile header wraps controls instead of clipping the brand row', () => {
  const blocks = mediaBlocks(portalCss, '@media\\s*\\(max-width:\\s*420px\\)');
  const mobile = blocks.join('\\n');
  assert.match(mobile, /\.portal-landing-nav\s*\{[^}]*flex-wrap\s*:\s*wrap/i);
  assert.match(mobile, /\.portal-landing-nav-actions\s*\{[^}]*flex:\s*1 1 100%/i);
  assert.match(mobile, /\.portal-landing-locale-link\s*\{[^}]*min-width:\s*38px/i);
});
