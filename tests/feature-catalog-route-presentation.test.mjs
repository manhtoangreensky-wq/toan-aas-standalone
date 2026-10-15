import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const featureSource = fs.readFileSync(path.join(root, "static", "portal", "portal-features.js"), "utf8");
const themeSource = fs.readFileSync(path.join(root, "static", "portal", "portal-theme.css"), "utf8");
const viCopy = featureSource.match(/vi:\s*\{([\s\S]*?)\n\s*en:\s*\{/u)?.[1] || "";
const routeStyles = themeSource.slice(themeSource.lastIndexOf("/* R142: standalone Features route presentation */"));
const motionStart = featureSource.indexOf("function mountFeatureMotion(main)");
const motionEnd = featureSource.indexOf("\n  function renderShell(", motionStart);
const motionBlock = featureSource.slice(motionStart, motionEnd);
const cleanupStart = motionBlock.lastIndexOf("featureMotionCleanup = () => {");
const cleanupEnd = motionBlock.indexOf("\n    };", cleanupStart);
const cleanup = cleanupStart >= 0 && cleanupEnd > cleanupStart ? motionBlock.slice(cleanupStart, cleanupEnd) : "";

test("standalone Features fixed Vietnamese chrome uses natural, translated wording", () => {
  assert.ok(viCopy, "Vietnamese copy block must exist");
  for (const phrase of ["Danh mục công cụ", "Mở quy trình", "Liên kết tác vụ chuẩn", "Lập kế hoạch trên Web", "Tạo nội dung bằng AI"]) {
    assert.ok(viCopy.includes(phrase), `Vietnamese Features copy must include ${phrase}`);
  }
  assert.doesNotMatch(viCopy, /\bworkflow\b|Web-native|Bot companion|canonical|Job Bridge/iu);
});

test("Features route card typography stays inside the product's approved type scale", () => {
  assert.match(routeStyles, /body\.portal-body--features[^{}]*\.portal-feature-group-head h2\s*\{[^}]*font-size:\s*clamp\(24px,/su);
  assert.match(routeStyles, /body\.portal-body--features[^{}]*\.portal-module-card h3\s*\{[^}]*font-size:\s*20px;[^}]*line-height:\s*1\.25/su);
  assert.match(routeStyles, /body\.portal-body--features[^{}]*\.portal-module-card p\s*\{[^}]*font-size:\s*16px;[^}]*line-height:\s*1\.625/su);
  assert.match(routeStyles, /body\.portal-body--features[^{}]*\.portal-module-card-footer\s*\{[^}]*font-size:\s*14px/su);
  assert.match(routeStyles, /body\.portal-body--features[^{}]*\.portal-catalog-search > label\s*\{[^}]*font-size:\s*14px/su);
  assert.match(routeStyles, /body\.portal-body--features[^{}]*\.portal-catalog-search-result\s*\{[^}]*font-size:\s*14px/su);
  assert.match(routeStyles, /body\.portal-body--features[^{}]*\.portal-catalog-clear\s*\{[^}]*min-width:\s*44px;[^}]*min-height:\s*44px/su);
});

test("Features route uses one entrance cue and remains static with reduced motion", () => {
  assert.match(routeStyles, /@media\s*\(prefers-reduced-motion:\s*no-preference\)[\s\S]*?body\.portal-body--features \.portal-page\s*\{\s*animation:\s*none;/u);
  assert.match(routeStyles, /@media\s*\(prefers-reduced-motion:\s*reduce\)[\s\S]*?body\.portal-body--features[\s\S]*?animation:\s*none\s*!important/u);
  assert.match(featureSource, /data-portal-features-motion/);
  const activate = motionBlock.match(/const activate = \(\) => \{([\s\S]*?)\n    \};/u)?.[1] || "";
  assert.match(activate, /featureMotionActive/);
  assert.ok(activate.indexOf('set(entrance, "data-portal-features-motion", "enter")') < activate.indexOf("clearTimer = window.setTimeout"));
  assert.match(cleanup, /featureMotionActive = false/);
});

test("Features motion ignores queued observer and animation-frame work after cleanup", () => {
  assert.match(motionBlock, /const reveal = \(target\) => \{[\s\S]*?featureMotionActive/);
  assert.match(motionBlock, /const scheduleReveal = \(target\) => \{[\s\S]*?if \(!featureMotionActive\)/);
  assert.match(motionBlock, /observer = new window\.IntersectionObserver\(\(entries\) => \{[\s\S]*?if \(!featureMotionActive\) return;/);
  assert.match(motionBlock, /const revealFrames = new Set\(\)/);
  assert.match(cleanup, /cancelAnimationFrame/);
  assert.match(cleanup, /revealFrames\.clear\(\)/);
});

test("Features motion removes focus listeners when the route unmounts", () => {
  assert.match(motionBlock, /const focusHandlers = \[\]/);
  assert.match(motionBlock, /focusHandlers\.push\(\{ target, onFocus \}\)/);
  assert.match(cleanup, /focusHandlers\.forEach/);
  assert.match(cleanup, /removeEventListener\("focusin", onFocus\)/);
});

test("Features hydration cannot render a stale response into a replaced route shell", () => {
  assert.match(featureSource, /function featuresHydrationIsCurrent\(main, expectedPath\)/);
  assert.match(featureSource, /document\.getElementById\("portal-main"\) !== main/);
  assert.match(featureSource, /location\.pathname === expectedPath/);
  assert.match(featureSource, /const initialMain = document\.getElementById\("portal-main"\) \|\| document\.getElementById\("portal-root"\)/);
  assert.ok(featureSource.includes('if (!featuresHydrationIsCurrent(initialMain, "/features")) return initial;'));
  assert.ok(featureSource.indexOf("featuresHydrationIsCurrent(initialMain, \"/features\")") < featureSource.indexOf("window.__TOAN_AAS_PORTAL__ = next;"));
});
