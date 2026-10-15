import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import vm from "node:vm";
import { fileURLToPath } from "node:url";

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const i18nSource = fs.readFileSync(path.join(repoRoot, "static/portal/portal-i18n.js"), "utf8");
const portalSource = fs.readFileSync(path.join(repoRoot, "static/portal/portal.js"), "utf8");
const runtime = {};
vm.createContext(runtime);
vm.runInContext(i18nSource, runtime);

const messages = runtime.TOANAASI18n.messages;
const promptKeys = Object.keys(messages.vi).filter((key) => /^(?:promptLibrary|promptStudio)\./.test(key));
const englishOptionKeys = [
  "promptStudio.option.platform.general", "promptStudio.option.platform.chat", "promptStudio.option.platform.social",
  "promptStudio.option.platform.website", "promptStudio.option.platform.email", "promptStudio.option.platform.image",
  "promptStudio.option.platform.video", "promptStudio.option.platform.voice", "promptStudio.option.platform.document",
  "promptStudio.option.tone.clear", "promptStudio.option.tone.friendly", "promptStudio.option.tone.professional",
  "promptStudio.option.tone.persuasive", "promptStudio.option.tone.educational", "promptStudio.option.tone.creative",
  "promptStudio.option.tone.neutral", "promptStudio.option.language.vi", "promptStudio.option.language.en",
  "promptStudio.option.output.general", "promptStudio.option.output.content", "promptStudio.option.output.caption",
  "promptStudio.option.output.script", "promptStudio.option.output.image_prompt", "promptStudio.option.output.video_prompt",
  "promptStudio.option.output.voice_script", "promptStudio.option.output.document_outline"
];

test("Prompt Library and Prompt Studio keep a complete, equal VI/EN/ZH catalogue", () => {
  const keysets = ["vi", "en", "zh"].map((locale) => Object.keys(messages[locale]).sort());
  assert.deepEqual(keysets[1], keysets[0], "VI and EN i18n keysets must remain equal");
  assert.deepEqual(keysets[2], keysets[0], "VI and ZH i18n keysets must remain equal");
  assert.ok(promptKeys.length >= 150, "Prompt Library and Prompt Studio catalogues must stay populated");
  for (const key of englishOptionKeys) {
    assert.ok(messages.en[key], `missing English option label: ${key}`);
    assert.ok(messages.zh[key], `missing Chinese option label: ${key}`);
  }
});

test("Prompt authoring fixed copy uses localized helpers without changing workflow contracts", () => {
  assert.match(portalSource, /function promptLibraryText\(/);
  assert.match(portalSource, /function promptStudioText\(/);
  assert.match(portalSource, /function promptStudioOptions\(/);
  assert.match(portalSource, /promptStudioOptions\(PROMPT_STUDIO_PLATFORM_OPTIONS, "platform"\)/);
  assert.match(portalSource, /promptStudioOptions\(PROMPT_STUDIO_TONE_OPTIONS, "tone"\)/);
  assert.match(portalSource, /promptStudioOptions\(PROMPT_STUDIO_OUTPUT_FORMAT_OPTIONS, "output"\)/);

  for (const staleFallback of [
    "Tên template", "Tìm template", "Lưu template", "Đã lưu template",
    "Không tìm thấy template", "Biên tập template", "JSON template"
  ]) {
    assert.ok(!portalSource.includes(staleFallback), `legacy mixed-language fallback remains: ${staleFallback}`);
  }

  for (const contract of [
    'data-portal-action="prompt-library-filter"',
    'data-portal-action="prompt-template-create"',
    'data-portal-action="prompt-template-update"',
    'data-portal-action="prompt-studio-compose"',
    'data-portal-action="prompt-studio-save-library"',
    'href="/prompt-library"',
    'href="/prompt-studio"'
  ]) {
    assert.ok(portalSource.includes(contract), `Prompt authoring workflow contract missing: ${contract}`);
  }
});
