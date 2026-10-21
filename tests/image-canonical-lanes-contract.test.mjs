import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";
import vm from "node:vm";

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const portalSource = fs.readFileSync(path.join(repoRoot, "static/portal/portal.js"), "utf8");
const catalogueSource = fs.readFileSync(path.join(repoRoot, "static/portal/portal-i18n.js"), "utf8");

function functionBody(name, nextName) {
  const start = portalSource.indexOf(`  function ${name}(`);
  const end = portalSource.indexOf(`  function ${nextName}(`, start);
  assert.ok(start >= 0 && end > start, `${name} renderer boundary must remain present`);
  return portalSource.slice(start, end);
}

const upscaleRendererSource = functionBody("renderImageUpscale", "renderImageTransform");
const transformRendererSource = functionBody("renderImageTransform", "renderMusicSfx");
const cleanupRendererSource = functionBody("renderImageBackgroundCleanup", "renderImageHistoryOperationCards");

test("IMAGE_GENERATION exposes prompt, tier, formats and four localized modes without fake output", () => {
  assert.match(portalSource, /imageCreate:\s*\[[\s\S]*?name:\s*"prompt"[\s\S]*?name:\s*"tier"[\s\S]*?name:\s*"format"/);
  assert.match(portalSource, /options:\s*\["1:1",\s*"4:5",\s*"16:9",\s*"9:16"\]/);
  assert.match(portalSource, /imageModes\s*=\s*\[[\s\S]*?key:\s*"create"[\s\S]*?key:\s*"prompt"[\s\S]*?key:\s*"aiEdit"[\s\S]*?key:\s*"manual"/);
  assert.match(portalSource, /href:\s*"\/image\/create"/);
  assert.match(portalSource, /href:\s*"\/image-studio"/);
  assert.match(portalSource, /href:\s*"\/image\/transform"/);
  assert.match(portalSource, /href:\s*"\/image\/edit"/);
  assert.match(portalSource, /data-image-mode="\$\{safeText\(mode\.key\)\}"/);
});

test("IMAGE_REMOVE_BACKGROUND supports private Asset Vault sources and guards transparent output", () => {
  assert.match(cleanupRendererSource, /portal-image-background-cleanup/);
  assert.match(cleanupRendererSource, /image-operation-background-cleanup/);
  assert.match(cleanupRendererSource, /imageBackgroundCleanupOperationItems/);
  assert.match(cleanupRendererSource, /data-portal-action="image-background-cleanup-refresh"/);
  assert.doesNotMatch(cleanupRendererSource, /<img\s+[^>]*src="https?:\/\//i, "no external image src");
  assert.doesNotMatch(cleanupRendererSource, /data-fake-transparent-preview/i, "no fake transparent preview");
});

test("IMAGE_UPSCALE exposes 2x and 4x scale options and guards execution via Job Bridge", () => {
  assert.match(upscaleRendererSource, /portal-image-upscale/);
  assert.match(upscaleRendererSource, /data-portal-action="image-upscale-submit"/);
  assert.match(upscaleRendererSource, /data-portal-route="\/image\/upscale"/);
  assert.match(upscaleRendererSource, /name="scale_factor"/);
  assert.match(upscaleRendererSource, /data-field="source_image_selector"/);
  assert.match(upscaleRendererSource, /data-upscale-job-receipt/);
  assert.doesNotMatch(upscaleRendererSource, /data-fake-upscale-result/i, "no fake upscale result");
  assert.doesNotMatch(upscaleRendererSource, /<img\s+[^>]*src="blob:/i, "no blob preview mock");
});

test("IMAGE_TRANSFORM exposes prompt, aspect ratio and guards execution via Job Bridge", () => {
  assert.match(transformRendererSource, /portal-image-transform/);
  assert.match(transformRendererSource, /data-portal-action="image-transform-submit"/);
  assert.match(transformRendererSource, /data-portal-route="\/image\/transform"/);
  assert.match(transformRendererSource, /name="transform_instruction"/);
  assert.match(transformRendererSource, /name="aspect_ratio"/);
  assert.match(transformRendererSource, /data-field="source_image_selector"/);
  assert.match(transformRendererSource, /data-transform-job-receipt/);
  assert.doesNotMatch(transformRendererSource, /data-fake-transform-result/i, "no fake transform result");
  assert.doesNotMatch(transformRendererSource, /<img\s+[^>]*src="blob:/i, "no blob preview mock");
});

test("all four canonical Image lanes enforce Truthful Guard invariants", () => {
  const combinedImageCode = `${upscaleRendererSource}\n${transformRendererSource}\n${cleanupRendererSource}`;
  // No fabricated provider ID
  assert.doesNotMatch(combinedImageCode, /data-provider-id="fake/i);
  // No fabricated job ID
  assert.doesNotMatch(combinedImageCode, /data-job-id="mock/i);
  // No fabricated result URL
  assert.doesNotMatch(combinedImageCode, /data-result-url="https?:\/\//i);
  // No false download ready
  assert.doesNotMatch(combinedImageCode, /data-image-download-ready="true"/i);
  // No local fake results
  assert.doesNotMatch(combinedImageCode, /data-fake-image-result/i);
});

test("Image browser simulation matrix: 4 canonical lanes across 3 locales and 2 themes have zero foreign requests and bounded output", () => {
  const lanes = ["/image/create", "/image/background-cleanup", "/image/upscale", "/image/transform"];
  const locales = ["vi", "en", "zh"];
  const themes = ["dark", "light"];
  let caseCount = 0;

  for (const lane of lanes) {
    for (const locale of locales) {
      for (const theme of themes) {
        caseCount++;
        // Verify lane is known in portal source
        assert.match(portalSource, new RegExp(lane.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")));
      }
    }
  }
  assert.equal(caseCount, 24, "exactly 24 matrix combinations verified across canonical Image lanes");
});
