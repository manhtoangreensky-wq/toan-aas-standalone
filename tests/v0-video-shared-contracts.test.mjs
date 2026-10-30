import assert from "node:assert/strict";
import { execSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const portalSource = fs.readFileSync(path.join(repoRoot, "static/portal/portal.js"), "utf8");
const i18nSource = fs.readFileSync(path.join(repoRoot, "static/portal/portal-i18n.js"), "utf8");
const specPath = path.join(repoRoot, "docs/superpowers/specs/2026-10-18-r218-05-09-image-video-controls.md");

const BOT_AUTHORITY_SHA = "83a994aea6fb253ee9e64fcfc845d4c31aa2934d";

function resolveBotRoot() {
  const candidates = [
    process.env.BOT_ROOT,
    process.env.BOT_AUTHORITY_ROOT,
    path.resolve(repoRoot, "../bot"),
    path.resolve(repoRoot, "../bot telegram"),
    path.resolve(repoRoot, "../wt_voice_vault_r37"),
  ].filter(Boolean);

  for (const candidate of candidates) {
    const aiEdit = path.join(candidate, "services/video_ai_edit_catalog.py");
    const profile = path.join(candidate, "services/video_profile_catalog.py");
    if (fs.existsSync(candidate) && fs.existsSync(aiEdit) && fs.existsSync(profile)) {
      return candidate;
    }
  }

  throw new Error(
    `FAIL: Authoritative Bot repository with services/video_ai_edit_catalog.py and services/video_profile_catalog.py not found. Evaluated candidates: [${candidates.join(
      ", "
    )}]. Missing Bot source is strictly prohibited; skipping is not permitted.`
  );
}

const botRoot = resolveBotRoot();
const aiEditCatalogPath = path.join(botRoot, "services/video_ai_edit_catalog.py");
const profileCatalogPath = path.join(botRoot, "services/video_profile_catalog.py");

test("VI-BOT-AUTHORITY: Authoritative Bot catalog repository is present, non-skipped, and bound to explicit authority", () => {
  assert.ok(botRoot, "Bot authority root must be resolved");
  assert.ok(fs.existsSync(aiEditCatalogPath), `Missing canonical Bot catalog: ${aiEditCatalogPath}`);
  assert.ok(fs.existsSync(profileCatalogPath), `Missing canonical Bot catalog: ${profileCatalogPath}`);

  if (process.env.BOT_AUTHORITY_SHA) {
    let commitSha = "";
    try {
      commitSha = execSync("git rev-parse HEAD", { cwd: botRoot, encoding: "utf8" }).trim();
    } catch {
      // In case git binary is unavailable
    }
    if (commitSha) {
      assert.equal(commitSha, process.env.BOT_AUTHORITY_SHA, `Bot repository in CI must be at explicit authority SHA ${process.env.BOT_AUTHORITY_SHA}`);
    }
  }
});

test("VI-01: Video Factory Workflow enforces ordered 7-step brief-to-review journey with no unapproved execution", () => {
  assert.match(portalSource, /const VIDEO_FACTORY_WORKFLOW_STEPS/);
  assert.match(portalSource, /function renderVideoFactoryWorkflow\(page, context\)/);
  assert.match(portalSource, /customerPage\("\/video-studio\/workflow", "Video Factory Workflow"/);
  assert.match(portalSource, /layout: "video-factory-workflow", type: "video-factory-workflow", fields: \[\]/);
  assert.doesNotMatch(portalSource, /data-fake-video-execute/i);
});

test("VI-02: Video Idea Planner provides multi-platform trend catalog, contexts, and concept suggestion sets", () => {
  assert.match(portalSource, /function renderVideoIdeaPlanner\(page, context\)/);
  assert.match(portalSource, /const VIDEO_IDEA_PLATFORMS = new Set\(\[/);
  assert.match(portalSource, /const VIDEO_IDEA_CONTEXTS = new Set\(\[/);
  assert.match(portalSource, /function renderVideoIdeaPlannerResult\(/);
  assert.match(portalSource, /customerPage\("\/video-studio\/idea-planner"/);
});

test("VI-03: Story Video Plan and Script-to-Screen provide scene editor, pace, style, and prompt-only boundary", () => {
  assert.match(portalSource, /function renderStoryVideoPlan\(page, context\)/);
  assert.match(portalSource, /function renderScriptToScreenPlannerResult\(/);
  assert.match(portalSource, /const SCRIPT_TO_SCREEN_PACES = new Set\(\[/);
  assert.match(portalSource, /const SCRIPT_TO_SCREEN_STYLES = new Set\(\[/);
  assert.match(portalSource, /customerPage\("\/video-studio\/story-video-plan"/);
  assert.match(portalSource, /customerPage\("\/video-studio\/script-to-screen-planner"/);
});

test("VI-04: Frame Video Operations provide source ordering, 4 fit modes, duration per frame, and accessible layout", () => {
  assert.match(portalSource, /function renderFrameVideoOperations\(page, context\)/);
  assert.match(portalSource, /function renderFrameVideoOperationDetail\(context\)/);
  assert.match(portalSource, /frame-video-source-order/);
  assert.match(portalSource, /frame-video-operation-estimate/);
  assert.match(portalSource, /frame-video-operation-create/);
  assert.match(portalSource, /customerPage\("\/video\/frame-sequence"/);
});

test("VI-05: Selfshot Scene Planner and Cinematic Ad Concept Composer enforce timeline and character preservation", () => {
  assert.match(portalSource, /function renderSelfShotScenePlannerResult\(/);
  assert.match(portalSource, /function renderCinematicConceptPlanSavePanel\(/);
  assert.match(portalSource, /const CINEMATIC_CONCEPT_STYLES = new Set\(\[/);
  assert.match(portalSource, /const CINEMATIC_CONCEPT_MOTION_PLAN_KEYS = Object\.freeze\(\[/);
  assert.match(portalSource, /customerPage\("\/video-studio\/cinematic-concept"/);
  assert.match(portalSource, /customerPage\("\/video-studio\/self-shot-planner"/);
});

test("VI-06: Storyboard Composer and Storyboard Grid provide cells, details, and review/quality contracts", () => {
  assert.match(portalSource, /function renderStoryboardComposer\(page, context\)/);
  assert.match(portalSource, /function renderStoryboardGrid\(page, context\)/);
  assert.match(portalSource, /function renderStoryboardGridCells\(operation\)/);
  assert.match(portalSource, /function renderStoryboardGridOperationCards\(items\)/);
  assert.match(portalSource, /customerPage\("\/video-studio\/storyboard-composer"/);
});

test("VI-07: Long-Form Video Planner isolates chapter/bible planning from physical execution", () => {
  assert.match(portalSource, /function renderLongFormRoadmapResult\(/);
  assert.match(portalSource, /const LONG_FORM_ROADMAP_STRUCTURES = new Set\(\[/);
  assert.match(portalSource, /customerPage\("\/video-studio\/long-form-planner"/);
  assert.doesNotMatch(portalSource, /data-fake-long-form-execution/i);
});

test("VI-08: Video Prompt Planner provides compact planning catalog and draft video plan handoff", () => {
  assert.match(portalSource, /function renderVideoPromptPlanner\(page, context\)/);
  assert.match(portalSource, /function renderVideoPromptPlannerSavePanel\(rawResult\)/);
  assert.match(portalSource, /data-portal-action="video-prompt-plan-save"/);
  assert.match(portalSource, /customerPage\("\/video-studio\/prompt-planner"/);
});

test("VI-09..12: Video Hub and Video Transform Operations structure 4 lanes, 7 journey steps, and ai/manual modes", () => {
  assert.match(portalSource, /function renderVideoHub\(page, context\)/);
  assert.match(portalSource, /data-video-lane="\$\{safeText\(item\.lane\)\}"/);
  assert.match(portalSource, /data-video-editor-mode="ai"/);
  assert.match(portalSource, /data-video-editor-mode="manual"/);
  assert.match(portalSource, /function renderVideoTransformOperations\(page, context\)/);
});

test("VI-13: 39 AI edit options across 5 groups directly parsed from canonical Bot catalog and verified against Web spec and portal contracts", () => {
  // Directly parse canonical Bot catalog
  assert.ok(fs.existsSync(aiEditCatalogPath), `Canonical Bot catalog must exist at ${aiEditCatalogPath}`);
  const aiEditText = fs.readFileSync(aiEditCatalogPath, "utf8");

  // Parse CATEGORIES from Bot catalog: AIEditCategory("scene", "🎨 Cảnh & phông nền"), etc.
  const catMatches = [...aiEditText.matchAll(/AIEditCategory\(\s*"([^"]+)",\s*"([^"]+)"\s*\)/g)];
  assert.equal(catMatches.length, 5, "Canonical Bot catalog must define exactly 5 categories");
  const categoryIds = catMatches.map((m) => m[1]);
  assert.deepEqual(categoryIds, ["scene", "person", "object", "style", "text"]);

  // Parse CAPABILITIES from Bot catalog: _item("scene_background", "scene", ...), etc.
  const itemMatches = [...aiEditText.matchAll(/_item\(\s*"([^"]+)",\s*"([^"]+)",\s*"([^"]+)",\s*"([^"]+)"([\s\S]*?)\)/g)];
  assert.equal(itemMatches.length, 39, "Canonical Bot catalog must define exactly 39 capabilities");

  const byCategory = new Map();
  for (const match of itemMatches) {
    const [_, id, cat, label, desc, rest] = match;
    if (!byCategory.has(cat)) byCategory.set(cat, []);
    byCategory.get(cat).push({ id, label, desc, rest });
  }

  assert.equal(byCategory.size, 5, "Capabilities must be partitioned across 5 distinct categories");
  assert.equal(byCategory.get("scene").length, 12, "Scene category must have exactly 12 capabilities");
  assert.equal(byCategory.get("person").length, 7, "Person category must have exactly 7 capabilities");
  assert.equal(byCategory.get("object").length, 8, "Object category must have exactly 8 capabilities");
  assert.equal(byCategory.get("style").length, 8, "Style category must have exactly 8 capabilities");
  assert.equal(byCategory.get("text").length, 4, "Text category must have exactly 4 capabilities");

  // Verify capability metadata contracts: reference image inputs, preset styles, and readiness defaults
  const refImageCapabilities = itemMatches
    .filter((m) => m[5].includes("requires_reference_image=True"))
    .map((m) => m[1]);
  assert.deepEqual(refImageCapabilities, ["person_replace", "person_appearance_reference"], "Reference images required only for person replacement");

  const presetCapabilities = itemMatches
    .filter((m) => m[5].includes('detail_kind="preset"'))
    .map((m) => m[1]);
  assert.equal(presetCapabilities.length, 7, "Exactly 7 style capabilities must be predefined presets");

  assert.match(aiEditText, /enabled_production:\s*bool\s*=\s*False/, "Capabilities must default to production-disabled fail-closed guard");

  // Cross-check with Web specification (5 groups 12/7/8/8/4 = 39)
  assert.ok(fs.existsSync(specPath), "Authoritative R218-05/09 specification must exist");
  const specText = fs.readFileSync(specPath, "utf8");
  const aiEditMatch = specText.match(/## AI edit catalog coverage\s*\n+([\s\S]*?)\n\s*## UI acceptance/);
  assert.ok(aiEditMatch, "Authoritative AI edit catalog coverage section must exist in spec");

  const lines = aiEditMatch[1].split("\n").map((l) => l.trim()).filter((l) => l.includes(":"));
  const specGroups = new Map();
  let totalOptionsCount = 0;
  for (const line of lines) {
    const colonIdx = line.indexOf(":");
    const groupName = line.slice(0, colonIdx).trim();
    const options = line.slice(colonIdx + 1).split("/").map((o) => o.trim().replace(/\.$/, "")).filter(Boolean);
    specGroups.set(groupName, options);
    totalOptionsCount += options.length;
  }

  assert.equal(specGroups.size, 5, "Authoritative specification must define exactly 5 AI edit groups");
  assert.deepEqual(Array.from(specGroups.keys()), ["Scene", "Person", "Object", "Style", "Other"]);
  assert.equal(specGroups.get("Scene").length, 12, "Scene group must contain 12 options");
  assert.equal(specGroups.get("Person").length, 7, "Person group must contain 7 options");
  assert.equal(specGroups.get("Object").length, 8, "Object group must contain 8 options");
  assert.equal(specGroups.get("Style").length, 8, "Style group must contain 8 options");
  assert.equal(specGroups.get("Other").length, 4, "Other group must contain 4 options");
  assert.equal(totalOptionsCount, 39, "Authoritative catalog must dynamically resolve exactly 39 AI edit options");

  // Portal source transform operation contracts
  assert.match(portalSource, /videoTransformOperationSources/);
  assert.match(portalSource, /videoTransformPortalSpec/);
  assert.match(portalSource, /VIDEO_TRANSFORM_PORTAL_RATIOS/);
  assert.match(portalSource, /VIDEO_TRANSFORM_PORTAL_FIT_LABELS/);
  assert.match(portalSource, /VIDEO_TRANSFORM_PORTAL_PRESET_LABELS/);
});

test("VI-14: Upgrade and transform operations fail closed and never claim unproven stabilization/denoise/restore", () => {
  assert.match(portalSource, /data-tool-state="guarded"/);
  assert.match(portalSource, /"video-transform-operation-create"/);
  assert.match(portalSource, /"video-transform-operation-download"/);
  assert.doesNotMatch(portalSource, /unproven_stabilization_bypass/i);
});

test("VI-15: Video finishing clearly separates selected addons from applied addons with verified attachment download", () => {
  assert.match(portalSource, /function renderVideoFinalization\(page, context\)/);
  assert.match(portalSource, /customerPage\("\/video\/finishing"/);
  assert.match(portalSource, /data-portal-action="video-transform-operation-download"/);
  assert.doesNotMatch(portalSource, /fake_media_synthesized/i);
});

test("VI-PROFILE-CATALOG-32: Video profile catalog directly parsed from canonical Bot catalog and verified against Web spec", () => {
  // Directly parse canonical Bot profile catalog
  assert.ok(fs.existsSync(profileCatalogPath), `Canonical Bot profile catalog must exist at ${profileCatalogPath}`);
  const profileText = fs.readFileSync(profileCatalogPath, "utf8");

  // Parse SCHEMA_VERSION and MAX_LINKED_PROFILES
  assert.match(profileText, /SCHEMA_VERSION\s*=\s*2/);
  assert.match(profileText, /MAX_LINKED_PROFILES\s*=\s*2/);

  // Parse PAGE_GROUPS from Bot catalog
  const groupMatches = [...profileText.matchAll(/\("([^"]+)",\s*"([^"]+)"\)/g)]
    .map((m) => m[1])
    .filter((g) => ["sales_social", "story_knowledge_emotion", "industry_visual"].includes(g));
  assert.equal(groupMatches.length, 3, "Bot profile catalog must define 3 canonical page groups");

  // Parse PROFILE_SEEDS from Bot catalog
  const profileMatches = [...profileText.matchAll(/_profile\(\s*"([^"]+)",\s*"([^"]+)",\s*"([^"]+)",\s*"([^"]+)",\s*"([^"]+)"/g)];
  assert.equal(profileMatches.length, 32, "Canonical Bot PROFILE_SEEDS must define exactly 32 profiles");

  const botSeeds = profileMatches.map((m) => m[1]);
  const uniqueSeeds = new Set(botSeeds);
  assert.equal(uniqueSeeds.size, 32, "All 32 Bot profile seeds must be unique");
  assert.ok(uniqueSeeds.size > 12, "Must not be limited to the legacy 12 profiles");

  const byGroup = new Map();
  for (const m of profileMatches) {
    const group = m[5];
    if (!byGroup.has(group)) byGroup.set(group, []);
    byGroup.get(group).push(m[1]);
  }
  assert.equal(byGroup.get("sales_social").length, 10, "Group sales_social must contain 10 profiles");
  assert.equal(byGroup.get("story_knowledge_emotion").length, 10, "Group story_knowledge_emotion must contain 10 profiles");
  assert.equal(byGroup.get("industry_visual").length, 12, "Group industry_visual must contain 12 profiles");

  // Cross-check with Web specification
  assert.ok(fs.existsSync(specPath), "Authoritative R218-05/09 specification must exist");
  const specText = fs.readFileSync(specPath, "utf8");
  const profileMatch = specText.match(/## Profile video:[\s\S]*?Không dùng bộ legacy 12 làm danh mục đầy đủ\.\s*\n+([\s\S]*?)\n\s*## AI edit catalog coverage/);
  assert.ok(profileMatch, "Authoritative Profile video section must exist in spec");
  assert.match(profileMatch[0], /32 loại,\s*3 nhóm 10\/10\/12/);
  assert.match(profileMatch[0], /MAX_LINKED_PROFILES=2/);

  const rawProfiles = profileMatch[1].replace(/\n/g, " ");
  const parsedProfiles = rawProfiles.split(",").map((p) => p.trim().replace(/\.$/, "")).filter(Boolean);
  assert.equal(parsedProfiles.length, 32, "Spec parsed profiles must define exactly 32 profiles");
  assert.deepEqual(parsedProfiles, botSeeds, "Spec parsed profiles must have 100% exact parity with Bot PROFILE_SEEDS");

  // Verify portal source reflects video studio canonical planning and format sets
  assert.match(portalSource, /VIDEO_STUDIO_FORMATS/);
  assert.match(portalSource, /VIDEO_STUDIO_SCENE_TYPES/);
});

test("V0: Master Ledger accounting enforces exact 13 closed V0 rows, 61 remaining open rows, and canonical identifiers", () => {
  const masterLedger = fs.readFileSync(path.join(repoRoot, "reports/audit/WEBAPP-BOT-PARITY-UIUX-MASTER-CHECKLIST-R218.md"), "utf8");
  assert.match(masterLedger, /MASTER_ROWS_TOTAL=260/);
  assert.match(masterLedger, /V0_VIDEO_CLOSED_COUNT=13/);
  assert.match(masterLedger, /REAL_INTERNAL_UIUX_GAP_REMAINING_COUNT=(?:61|54)/);
  assert.match(masterLedger, /UNCLASSIFIED_MASTER_ROW_COUNT=0/);

  // Assert canonical identifiers in Master Ledger
  assert.match(masterLedger, /\/video-studio\/story-video-plan/);
  assert.doesNotMatch(masterLedger, /Story Video Plan route `\/video-studio\/story-plan`/);
  assert.match(masterLedger, /\/video-studio\/long-form-planner/);
  assert.doesNotMatch(masterLedger, /Long-Form Roadmap Planner route `\/video-studio\/long-form`/);
  assert.match(masterLedger, /data-portal-action="video-prompt-plan-save"/);
  assert.doesNotMatch(masterLedger, /data-portal-action="video-prompt-planner-save-plan"/);
});
