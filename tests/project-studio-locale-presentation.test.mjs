import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import vm from "node:vm";
import { fileURLToPath } from "node:url";

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const i18nSource = fs.readFileSync(path.join(repoRoot, "static/portal/portal-i18n.js"), "utf8");
const portalSource = fs.readFileSync(path.join(repoRoot, "static/portal/portal.js"), "utf8");
const projectCenterStart = portalSource.indexOf("  function renderProjectCenter(page, context)");
const projectCenterEnd = portalSource.indexOf("  function renderMemory", projectCenterStart);
const projectPackageStart = portalSource.indexOf("  function renderProjectPackagePagination(context, enabled, route, projectId)");
const projectPackageEnd = portalSource.indexOf("  function renderFeatureFamily(page, context)", projectPackageStart);
const projectFallbackSource = [
  portalSource.slice(projectCenterStart, projectCenterEnd),
  portalSource.slice(projectPackageStart, projectPackageEnd),
  portalSource.slice(portalSource.indexOf('  customerPage("/projects"'), portalSource.indexOf('  customerPage("/prompt-library"')),
  portalSource.slice(portalSource.indexOf('  customerPage("/project-packages"'), portalSource.indexOf('  customerPage("/publishing"'))
].join("\n");

const context = {};
vm.createContext(context);
vm.runInContext(i18nSource, context);
const messages = context.TOANAASI18n.messages.vi;
const projectKeys = Object.keys(messages).filter((key) => /^(?:projectCenter|project\.|projectPackage\.)/.test(key));

assert.ok(projectKeys.length >= 100, "Project/Studio locale catalogue is present");

const leakedGenericEnglish = /\b(?:Project|Projects|Project\s+(?:Center|Workspace|Package|Packages)|Studio\s+Documents?|Documents?|signed\s+Web\s+account|owner-scoped|owner\s+check|browser\s+cache|browser\s+storage|fallback|private|provider|payment|brief|authoring|workspace|receipt|version\s+history|history|revision|workflow|execution|engine|job|charge|publish|delivery|review|timeline|detail|count|metadata|filter|pagination|refresh|activity|output|snapshot|artifact|package|Creative\s+brief|Content\s+pack|Prompt|Caption|Storyboard|Web-owned|server-side)\b/i;

test("Vietnamese Project, Studio Document and package copy is not mixed with generic English", () => {
  const leaks = projectKeys
    .map((key) => ({ key, value: String(messages[key] || "") }))
    .filter(({ value }) => leakedGenericEnglish.test(value));
  assert.deepEqual(leaks, [], `unexpected generic English in VI catalogue: ${JSON.stringify(leaks)}`);
});
test("Project route fallbacks keep the same Vietnamese vocabulary", () => {
  for (const legacy of [
    "Project Operations Board đang được bảo vệ",
    "Đang xác minh Project riêng tư",
    "Tìm và tiếp tục Project",
    "Studio Documents trên trang này",
    "Project Workspace riêng tư",
    "Project Package"
  ]) {
    assert.doesNotMatch(projectFallbackSource, new RegExp(legacy.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")), legacy);
  }
  assert.match(projectFallbackSource, /projectCenterText\("summary\.title", "Giữ định hướng, tài liệu và phiên bản đi đúng dự án\./);
  assert.match(projectFallbackSource, /projectText\("detail\.documentsTitle", "Tài liệu Studio"\)/);
});
