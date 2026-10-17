import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const shell = fs.readFileSync(path.join(root, "templates", "portal_shell.html"), "utf8");
const portalSource = fs.readFileSync(path.join(root, "static", "portal", "portal.js"), "utf8");
const portalCss = fs.readFileSync(path.join(root, "static", "portal", "portal.css"), "utf8");
const themeCss = fs.readFileSync(path.join(root, "static", "portal", "portal-theme.css"), "utf8");

test("R215 shell keeps a working skip link and non-blocking skeleton", () => {
  assert.match(shell, /href="#portal-main"/);
  assert.match(shell, /<main[^>]*id="portal-main"[^>]*tabindex="-1"[^>]*data-portal-main/);
  for (const hook of ["portal-boot-skeleton", "portal-boot-skeleton-title", "portal-boot-skeleton-copy", "portal-boot-skeleton-grid"]) {
    assert.match(shell, new RegExp(`class="${hook}"`), hook);
  }
  assert.match(portalCss, /\.portal-boot-skeleton\s*\{/);
  assert.match(portalCss, /\.portal-boot-skeleton-grid\s*\{/);
});

test("R215 preserves the approved blue/teal palette in both themes", () => {
  assert.match(portalCss, /--portal-bg:\s*#0b1017\s*;/);
  assert.match(portalCss, /--portal-accent:\s*#51d5bc\s*;/);
  assert.match(themeCss, /--portal-dark-app-canvas:\s*#0b132b\s*;/);
  assert.match(themeCss, /--portal-teal-dark-canvas:\s*#062026\s*;/);
  assert.match(themeCss, /:root\[data-portal-theme="dark"\]/);
  assert.match(themeCss, /html\[data-portal-theme="dark"\][\s\S]*?\.portal-button--primary/);
});

test("R215 keeps vertical responsive surfaces and prevents page-wide overflow", () => {
  assert.match(portalCss, /html\s*\{[^}]*min-width:\s*320px/);
  assert.match(portalCss, /\.portal-shell\s*\{[^}]*grid-template-columns:\s*280px\s+minmax\(0,\s*1fr\)/);
  assert.match(portalCss, /\.portal-workspace\s*\{[^}]*min-width:\s*0/);
  assert.match(portalCss, /@media\s*\(max-width:\s*700px\)/);
  assert.match(themeCss, /@media\s*\(max-width:\s*700px\)/);
  assert.match(themeCss, /overflow-x:\s*hidden/);
  assert.match(themeCss, /@media\s*\(max-width:\s*700px\)[\s\S]*\.portal-module-grid/);
});

test("R217-01 keeps landing navigation controls touch-safe on mobile", () => {
  assert.match(
    portalCss,
    /@media\s*\(max-width:\s*700px\)[\s\S]*?\.portal-landing-nav-actions \.portal-button \{[^}]*min-height:\s*44px;/,
  );
});

test("R215 keeps visible keyboard focus and reduced-motion fallbacks", () => {
  assert.match(portalCss, /\.skip-link:focus\s*\{/);
  assert.match(themeCss, /:focus-visible\s*\{/);
  assert.match(themeCss, /\.portal-main\s*:focus-visible/);
  assert.match(portalCss, /@media\s*\(prefers-reduced-motion:\s*reduce\)/);
  assert.match(themeCss, /@media\s*\(prefers-reduced-motion:\s*reduce\)/);
  assert.doesNotMatch(`${portalCss}\n${themeCss}`, /transition\s*:\s*all\b/i);
});

test("R215 keeps customer and Admin shells on reviewed product surfaces", () => {
  for (const route of ["/tools/video", "/music", "/voice", "/subtitle", "/image", "/admin"]) {
    assert.match(portalSource, new RegExp(route.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")), route);
  }
  assert.match(portalSource, /data-portal-app-kind="admin"/);
  assert.match(portalSource, /data-portal-app-kind="customer"/);
  assert.match(portalSource, /class="portal-page portal-media-hub/);
});
