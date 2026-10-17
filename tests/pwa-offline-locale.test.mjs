import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import vm from "node:vm";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const offlineHtml = fs.readFileSync(path.join(root, "static", "portal", "offline.html"), "utf8");
const offlineScript = fs.readFileSync(path.join(root, "static", "portal", "offline.js"), "utf8");
const workerSource = fs.readFileSync(path.join(root, "static", "portal", "service-worker.js"), "utf8");
const manifestPath = path.join(root, "static", "portal", "manifest.webmanifest");
const manifest = JSON.parse(fs.readFileSync(manifestPath, "utf8"));

function mountOffline(browserLanguage = "vi") {
  const attributes = new Map();
  const title = { textContent: "" };
  const message = { textContent: "" };
  const retry = { textContent: "" };
  const buttons = ["vi", "en", "zh"].map((locale) => {
    const listeners = new Map();
    const button = {
      dataset: { offlineLocale: locale },
      setAttribute: (name, value) => attributes.set(`${locale}:${name}`, value),
      addEventListener: (name, callback) => listeners.set(name, callback),
      listeners,
    };
    return button;
  });
  const languageSwitch = {
    querySelectorAll: () => buttons,
    setAttribute: (name, value) => attributes.set(`switch:${name}`, value),
  };
  const document = {
    title: "",
    documentElement: { lang: "vi" },
    querySelector: (selector) => ({
      "[data-offline-language-switcher]": languageSwitch,
      "[data-offline-title]": title,
      "[data-offline-message]": message,
      "[data-offline-retry]": retry,
    })[selector] || null,
  };
  const window = { navigator: { language: browserLanguage } };
  const context = vm.createContext({ window, document, String, Object, Array });
  vm.runInContext(offlineScript, context, { filename: "offline.js" });
  return { attributes, buttons, document, title, message, retry };
}

test("offline notice follows supported browser locale and defaults safely", () => {
  const vi = mountOffline("vi-VN");
  assert.equal(vi.document.documentElement.lang, "vi");
  assert.equal(vi.title.textContent, "Bạn đang ngoại tuyến");
  assert.equal(vi.attributes.get("switch:aria-label"), "Chọn ngôn ngữ");
  assert.equal(vi.attributes.get("vi:aria-pressed"), "true");

  const en = mountOffline("en-US");
  assert.equal(en.document.documentElement.lang, "en");
  assert.equal(en.title.textContent, "You’re offline");
  assert.equal(en.retry.textContent, "Try again");

  const zh = mountOffline("zh-CN");
  assert.equal(zh.document.documentElement.lang, "zh");
  assert.equal(zh.title.textContent, "当前处于离线状态");
  assert.equal(zh.retry.textContent, "重试");

  const unsupported = mountOffline("fr-FR");
  assert.equal(unsupported.document.documentElement.lang, "vi");
});

test("Vietnamese PWA manifest keeps user-facing copy in one language and all declared icons exist", () => {
  assert.equal(manifest.lang, "vi");
  assert.equal(manifest.name, "TOAN AAS");
  const visibleCopy = [manifest.name, manifest.short_name, manifest.description,
    ...manifest.shortcuts.flatMap((shortcut) => [shortcut.name, shortcut.short_name, shortcut.description])].join(" ");
  assert.doesNotMatch(visibleCopy, /\b(?:Autonomous Automation Suite|Dashboard|workspace|Project Center|Projects|project|workflow)\b/i);
  for (const icon of manifest.icons) {
    const iconPath = path.join(root, icon.src.replace(/^\//, "").replaceAll("/", path.sep));
    assert.ok(fs.existsSync(iconPath), `${icon.src} must exist`);
    const dimensions = /^(\d+)x(\d+)$/.exec(icon.sizes);
    if (icon.type === "image/png" && dimensions) {
      const png = fs.readFileSync(iconPath);
      assert.equal(png.toString("hex", 0, 8), "89504e470d0a1a0a", `${icon.src} must be a PNG`);
      assert.deepEqual([png.readUInt32BE(16), png.readUInt32BE(20)], [Number(dimensions[1]), Number(dimensions[2])],
        `${icon.src} dimensions must match the manifest`);
    }
  }
  assert.equal(manifest.start_url, "/dashboard");
  assert.equal(manifest.scope, "/");
  assert.equal(manifest.display, "standalone");
});

test("offline locale can be changed without persistence or network calls", () => {
  const offline = mountOffline("en-US");
  offline.buttons.find((button) => button.dataset.offlineLocale === "zh").listeners.get("click")();
  assert.equal(offline.document.documentElement.lang, "zh");
  assert.equal(offline.message.textContent, "此公共页面目前无法通过网络加载。请重新连接网络后重试。账户信息和私人工作区数据不会保存在离线缓存中。");
  assert.equal(offline.attributes.get("zh:aria-pressed"), "true");
  assert.equal(offline.attributes.get("en:aria-pressed"), "false");
  assert.doesNotMatch(offlineScript, /\b(?:fetch|XMLHttpRequest|localStorage|sessionStorage|indexedDB)\b/);
});

test("offline page loads its local language script from the public shell cache", () => {
  assert.match(offlineHtml, /<script src="\/static\/portal\/offline\.js" defer><\/script>/);
  assert.doesNotMatch(offlineHtml, /<script(?![^>]*\bsrc=)/i);
  assert.match(offlineHtml, /min-height:\s*100dvh/);
  assert.match(offlineHtml, /min-height:\s*44px/);
  assert.ok(workerSource.includes('"/static/portal/offline.js"'));
  assert.ok(workerSource.includes('"/static/portal/offline.html"'));
});
