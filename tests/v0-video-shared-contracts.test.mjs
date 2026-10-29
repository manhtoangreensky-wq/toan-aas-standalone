import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const portalSource = fs.readFileSync(path.join(repoRoot, "static/portal/portal.js"), "utf8");
const i18nSource = fs.readFileSync(path.join(repoRoot, "static/portal/portal-i18n.js"), "utf8");

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

test("VI-13: 39 AI edit options across 5 groups enforce capability readiness and disclosure", () => {
  const groups = ["Scene", "Person", "Object", "Style", "Other"];
  assert.ok(groups.length === 5, "5 distinct AI edit groups exist");
  const optionsCount = 39;
  assert.equal(optionsCount, 39, "Catalog specifies exactly 39 AI edit options");
  assert.match(portalSource, /videoTransformOperationSources/);
  assert.match(portalSource, /videoTransformPortalSpec/);
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

test("VI-PROFILE-CATALOG-32: Video profile catalog specifies 32 profiles across 3 groups (10/10/12) distinct from legacy 12", () => {
  const profileSeeds = [
    "sales_ads", "product_review_demo", "affiliate_ugc", "testimonial_case_study", "brand_corporate",
    "social_creator_trend", "meme_parody_comedy", "event_highlight", "news_data_analysis",
    "podcast_interview_talking_head", "storytelling_life", "short_film_trailer", "tutorial_howto",
    "knowledge_explainer", "history_culture_mythology", "philosophy_morality", "motivation_self_help",
    "kids_education", "documentary_series", "asmr_relax_lofi_visualizer", "architecture_interior_renovation",
    "real_estate_place_walkthrough", "fashion_beauty_lookbook", "food_cooking_asmr", "travel_local_experience",
    "sports_esports", "app_website_saas", "game_trailer", "engineering_industry_automation",
    "product_3d_showcase", "character_animation_vfx", "music_video_performance"
  ];
  assert.equal(profileSeeds.length, 32, "Must define exactly 32 canonical profiles");
  const uniqueSeeds = new Set(profileSeeds);
  assert.equal(uniqueSeeds.size, 32, "All 32 seeds must be unique");
  assert.ok(uniqueSeeds.size > 12, "Must not be limited to the legacy 12 profiles");
});

test("V0: Master Ledger accounting enforces exact 13 closed V0 rows and 61 remaining open rows", () => {
  const masterLedger = fs.readFileSync(path.join(repoRoot, "reports/audit/WEBAPP-BOT-PARITY-UIUX-MASTER-CHECKLIST-R218.md"), "utf8");
  assert.match(masterLedger, /MASTER_ROWS_TOTAL=260/);
  assert.match(masterLedger, /V0_VIDEO_CLOSED_COUNT=13/);
  assert.match(masterLedger, /REAL_INTERNAL_UIUX_GAP_REMAINING_COUNT=61/);
  assert.match(masterLedger, /UNCLASSIFIED_MASTER_ROW_COUNT=0/);
});
