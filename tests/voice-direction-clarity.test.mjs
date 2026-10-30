import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const portalJsPath = path.resolve(__dirname, "../static/portal/portal.js");
const portalSource = fs.readFileSync(portalJsPath, "utf8");

// Extract renderVoiceDirectionComposer function definition from portal.js
const fnMatch = portalSource.match(/function renderVoiceDirectionComposer\([\s\S]*?\n  \}/);
if (!fnMatch) {
  throw new Error("Unable to locate renderVoiceDirectionComposer in static/portal/portal.js");
}

const LOCALES = {
  vi: {
    "composer.direction.scope.title": "Phạm vi & giới hạn thực thi",
    "composer.direction.scope.description": "Trang này chỉ tạo bản nháp hướng thể hiện bằng văn bản; không tạo âm thanh, không gọi nhà cung cấp và không tính phí.",
    "composer.direction.form.title": "Soạn hướng thể hiện",
    "composer.direction.form.note": "Nhập văn bản và chọn phong cách",
    "composer.direction.form.description": "Lập kế hoạch hướng đọc cho nội dung",
    "composer.direction.form.submit": "Tạo hướng thể hiện",
    "composer.direction.guard.audio": "Audio / Generation",
    "composer.direction.guard.provider": "Provider / API",
    "composer.direction.guard.job": "Job / Wallet",
    "composer.off": "Tắt"
  },
  en: {
    "composer.direction.scope.title": "Scope & Execution Boundaries",
    "composer.direction.scope.description": "This tool produces editorial voice directions in text only. It does not synthesize speech, contact providers, or initiate jobs.",
    "composer.direction.form.title": "Compose voice direction",
    "composer.direction.form.note": "Provide text and select styling options",
    "composer.direction.form.description": "Plan voice characteristics for your script",
    "composer.direction.form.submit": "Generate direction",
    "composer.direction.guard.audio": "Audio / Generation",
    "composer.direction.guard.provider": "Provider / API",
    "composer.direction.guard.job": "Job / Wallet",
    "composer.off": "Off"
  },
  zh: {
    "composer.direction.scope.title": "范围与执行边界",
    "composer.direction.scope.description": "此工具仅生成文本形式的声音指导说明；不生成音频，不调用外部服务，亦不创建后台任务。",
    "composer.direction.form.title": "编写声音指导",
    "composer.direction.form.note": "输入脚本并选择风格",
    "composer.direction.form.description": "规划文本的声音方向",
    "composer.direction.form.submit": "生成声音指导",
    "composer.direction.guard.audio": "音频生成",
    "composer.direction.guard.provider": "供应商接口",
    "composer.direction.guard.job": "任务钱包",
    "composer.off": "已关闭"
  }
};

function createRendererInstance(localeKey) {
  const catalog = LOCALES[localeKey] || LOCALES.vi;
  let capturedFieldDeclarations = null;
  let capturedFieldValues = null;
  let capturedCanCompose = null;

  const sandbox = {
    safeText: (str) => String(str ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;"),
    voiceStudioText: (key, fallback) => catalog[key] || fallback || key,
    renderHero: () => `<header class="test-hero-sentinel"></header>`,
    badge: (state) => `<span class="portal-badge" data-badge="${state}">${state}</span>`,
    renderFields: (fields, canCompose, context, values, name) => {
      capturedFieldDeclarations = fields;
      capturedFieldValues = values;
      capturedCanCompose = canCompose;
      return `<div class="test-rendered-fields" data-form="${name}"></div>`;
    },
    voiceDirectionComposerFields: () => [
      { name: "text" }, { name: "language" }, { name: "suggestion_set" },
      { name: "selected_suggestion" }, { name: "reading_speed" }
    ],
    renderVoiceDirectionComposerResult: () => `<section class="test-voice-result-sentinel"></section>`
  };

  const script = new vm.Script(`${fnMatch[0]}; globalThis.__targetRenderer = renderVoiceDirectionComposer;`);
  const context = vm.createContext(sandbox);
  script.runInContext(context);

  return {
    render: sandbox.__targetRenderer,
    getCapturedFields: () => ({
      declarations: capturedFieldDeclarations,
      values: capturedFieldValues,
      canCompose: capturedCanCompose
    })
  };
}

for (const locale of ["vi", "en", "zh"]) {
  for (const capabilityEnabled of [true, false]) {
    test(`renderVoiceDirectionComposer - locale:${locale} capability:${capabilityEnabled}`, () => {
      const { render, getCapturedFields } = createRendererInstance(locale);
      const page = { title: "Voice Direction Composer" };
      const context = {
        capabilities: { "voice-direction-compose": capabilityEnabled },
        voiceDirectionComposerResult: null
      };

      const html = render(page, context);

      // 1. Scope details: bounded extraction of exactly the boundary details element
      const detailsMatch = html.match(/<details class="portal-card portal-card-pad portal-voice-direction-composer-boundary">([\s\S]*?)<\/details>/);
      assert.ok(detailsMatch, "Boundary details disclosure must exist in rendered HTML");
      const detailsInner = detailsMatch[1];

      const summaryMatches = detailsInner.match(/<summary>([\s\S]*?)<\/summary>/g) || [];
      assert.equal(summaryMatches.length, 1, "Scope details must have exactly one summary");
      const summaryContent = detailsInner.match(/<summary>([\s\S]*?)<\/summary>/)[1].trim();
      assert.ok(summaryContent.length > 0, "Summary content must be non-empty");

      const pMatches = detailsInner.match(/<p>([\s\S]*?)<\/p>/g) || [];
      assert.equal(pMatches.length, 1, "Scope details must have exactly one paragraph");
      const pContent = detailsInner.match(/<p>([\s\S]*?)<\/p>/)[1].trim();
      assert.ok(pContent.length > 0, "Paragraph content must be non-empty");

      assert.doesNotMatch(detailsInner, /<span\b/i, "No span technical status boxes allowed inside boundary details");
      assert.doesNotMatch(detailsInner, /<em\b/i, "No em technical status indicators allowed inside boundary details");
      assert.doesNotMatch(detailsInner, /portal-voice-direction-composer-guard-list/, "No guard-list inside boundary details");
      assert.doesNotMatch(detailsInner, /composer\.direction\.guard\./, "No guard keys inside boundary details");

      // 2. Sentinels and structure preserved
      assert.match(html, /class="test-hero-sentinel"/);
      assert.match(html, /class="test-voice-result-sentinel"/);
      assert.match(html, /data-portal-action="voice-direction-compose"/);
      assert.match(html, /data-portal-route="\/voice-studio\/direction-composer"/);

      // 3. Button disabled state conforms to capability
      if (capabilityEnabled) {
        assert.match(html, /<button class="portal-button portal-button--primary" type="submit">/);
      } else {
        assert.match(html, /<button class="portal-button portal-button--primary" type="submit" disabled>/);
      }

      // 4. Form fields, declarations, and capability passed unchanged
      const { declarations, values, canCompose } = getCapturedFields();
      assert.equal(canCompose, capabilityEnabled, "canCompose passed to renderFields must match capability");
      const declaredNames = (declarations || []).map((field) => field.name);
      assert.deepEqual(declaredNames, ["text", "language", "suggestion_set", "selected_suggestion", "reading_speed"]);
      const normalizedValues = JSON.parse(JSON.stringify(values));
      assert.deepEqual(normalizedValues, {
        text: "", language: "vi", suggestion_set: "core",
        selected_suggestion: "1", reading_speed: "normal"
      });
    });
  }
}
