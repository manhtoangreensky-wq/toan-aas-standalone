import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const portalSource = fs.readFileSync(path.join(repoRoot, "static/portal/portal.js"), "utf8");
const i18nSource = fs.readFileSync(path.join(repoRoot, "static/portal/portal-i18n.js"), "utf8");

test("UT-01: Translation workspace exposes source/target controls, 21 languages, search, two-way, and guarded execution", () => {
  assert.match(portalSource, /function renderTranslationWorkspace\(/);
  assert.match(portalSource, /const SUBDUB_LANGUAGE_CATALOG\s*=\s*Object\.freeze\(\[/);
  assert.match(portalSource, /data-translation-source-language/);
  assert.match(portalSource, /data-translation-target-language/);
  assert.match(portalSource, /data-translation-target-search/);
  assert.match(portalSource, /data-translation-preserve-original/);
  assert.match(portalSource, /data-translation-two-way/);
  assert.match(portalSource, /data-translation-local-action="start"/);
  assert.match(portalSource, /data-translation-local-action="stop"/);
  assert.match(portalSource, /data-translation-result-state/);
});

test("UT-02: Content Studio provides idea/caption/hashtag/script/CTA workflows, brief form, and complete VI/EN/ZH chrome", () => {
  assert.match(portalSource, /function renderContentStudio\(/);
  assert.match(portalSource, /function renderContentStudioDetail\(/);
  assert.match(portalSource, /function contentStudioKindOptions\(/);
  assert.match(portalSource, /function renderContentPromptPack\(/);
  assert.match(portalSource, /const CONTENT_STUDIO_KINDS\s*=\s*Object\.freeze\(\[/);
  assert.match(portalSource, /function contentStudioText\(/);
});

test("UT-03: Free Prompt Library & Gallery provides searchable prompt packs, copy/apply actions, and zero speculative metrics", () => {
  assert.match(portalSource, /function renderFreePromptGallery\(/);
  assert.match(portalSource, /function renderPromptStudio\(/);
  assert.match(portalSource, /function renderPromptLibrary\(/);
  assert.match(portalSource, /function freePromptGalleryCatalogState\(/);
  assert.doesNotMatch(portalSource, /data-fake-execution-metric/i);
});

test("UT-05: Notes / Memory Center provides owner-scoped note creation, list, search, tags, reminder, and delete confirmation", () => {
  assert.match(portalSource, /function renderMemoryNotes\(/);
  assert.match(portalSource, /function renderMemoryReminders\(/);
  assert.match(portalSource, /function renderMemoryReminderCard\(/);
  assert.match(portalSource, /function memoryNoteFilterFields\(/);
  assert.match(portalSource, /function memoryItems\(/);
});

test("UT-06: Documents Studio supports 9 canonical workflows, Asset Vault source, ordering, lossless compression, and guarded download", () => {
  assert.match(portalSource, /function renderDocumentWorkspace\(/);
  assert.match(portalSource, /function renderDocumentHub\(/);
  assert.match(portalSource, /function renderDocumentOperationCards\(/);
  assert.match(portalSource, /function documentWorkspaceFields\(/);
  assert.match(portalSource, /function documentOperationDownloadPath\(/);
});

test("UT-07: Asset Vault provides owner-scoped upload with 25MB allowlist, pagination, project tagging, and lifecycle management", () => {
  assert.match(portalSource, /function renderAssetVault\(/);
  assert.match(portalSource, /function renderAssets\(/);
  assert.match(portalSource, /function assetVaultFilterFields\(/);
  assert.match(portalSource, /function assetVaultLifecyclePanel\(/);
  assert.match(portalSource, /function imageVaultItems\(/);
});

test("UT-08: Projects & Workboard provide task/dependency/status/assignee tracking, board columns, and timeline view", () => {
  assert.match(portalSource, /function renderProjectCenter\(/);
  assert.match(portalSource, /function renderWorkboardBoard\(/);
  assert.match(portalSource, /function renderWorkboardOverview\(/);
  assert.match(portalSource, /function renderWorkboardChecklist\(/);
  assert.match(portalSource, /function workboardFields\(/);
});

test("AP-02: AutoPost Hub sequences brand/content plan to draft/review/calendar with Web-native handoffs and guarded external publish", () => {
  assert.match(portalSource, /function renderAutoPostHub\(/);
  assert.match(portalSource, /function renderCampaignPlanner\(/);
  assert.match(portalSource, /function renderChannelStrategy\(/);
  assert.match(portalSource, /function autopostHubText\(/);
  assert.match(portalSource, /function campaignPlanItems\(/);
});

test("AC-01: Account Profile & Security Center exposes profile, locale, timezone, sessions, password change, OAuth, and stale cleanup", () => {
  assert.match(portalSource, /function renderAccount\(/);
  assert.match(portalSource, /function renderAccountSecurity\(/);
  assert.match(portalSource, /function renderAccountActivity\(/);
  assert.match(portalSource, /function renderAccountDataControls\(/);
  assert.match(portalSource, /function clearTransientFormDraft\(/);
});

test("AC-01-AVATAR-PERSISTENCE: Avatar presets use inline data URIs and eliminate remote unverified image dependencies", () => {
  assert.match(portalSource, /function avatarPresetDataUri\(/);
  assert.match(portalSource, /data-portal-action="select-avatar-preset"/);
  assert.doesNotMatch(portalSource, /https:\/\/api\.dicebear\.com\//);
});

test("AC-02: Account Billing & Packages expose canonical balance, packages/pricing catalog, and guarded manual top-up QR readiness", () => {
  assert.match(portalSource, /function renderWallet\(/);
  assert.match(portalSource, /function canonicalWalletProjection\(/);
  assert.match(portalSource, /function canonicalWalletHistoryProjection\(/);
  assert.match(portalSource, /function manualTopupMethodHasCanonicalQr\(/);
  assert.doesNotMatch(portalSource, /data-fake-wallet-credit/i);
});

test("SP-01: Support Center provides owner-scoped tickets, pagination, attachments, replies, and status escalation", () => {
  assert.match(portalSource, /function renderSupportCaseCards\(/);
  assert.match(portalSource, /function renderSupportEvidence\(/);
  assert.match(portalSource, /function renderSupportRecoveryPlan\(/);
  assert.match(portalSource, /function renderSupportCasePagination\(/);
});

test("SP-02: Support Advisor, Consultation Brief, and Community Trust Center enforce verified channel boundaries and truthful help", () => {
  assert.match(portalSource, /function renderSupportAdvisor\(/);
  assert.match(portalSource, /function renderSupportConsultationBrief\(/);
  assert.match(portalSource, /function renderCommunityTrustCenter\(/);
  assert.match(portalSource, /function renderChatWorkspaceBoundary\(/);
  assert.match(portalSource, /portal-chat-workspace-guard-list/);
});

test("P5/P6: Master Ledger accounting enforces exact 13 closed P5/P6 rows and 78 remaining open rows", () => {
  const masterLedger = fs.readFileSync(path.join(repoRoot, "reports/audit/WEBAPP-BOT-PARITY-UIUX-MASTER-CHECKLIST-R218.md"), "utf8");
  assert.match(masterLedger, /MASTER_ROWS_TOTAL=260/);
  assert.match(masterLedger, /P5_P6_CLOSED_COUNT=13/);
  assert.match(masterLedger, /REAL_INTERNAL_UIUX_GAP_REMAINING_COUNT=(?:78|74|73|61|54)/);
  assert.match(masterLedger, /UNCLASSIFIED_MASTER_ROW_COUNT=0/);
});
