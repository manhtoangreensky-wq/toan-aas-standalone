import test from "node:test";
import assert from "node:assert/strict";
import {pageMetaRenderer, pageMetaSources} from "./helpers/chat-page-meta-runtime.mjs";

const render = await pageMetaRenderer(pageMetaSources());
const native = {
  vi: {volume: "Âm lượng (%)", account: "Tài khoản", greeting: "Chào bạn"},
  en: {volume: "Volume (%)", account: "Account", greeting: "Hello there"},
  zh: {volume: "音量（%）", account: "账户", greeting: "你好，您"}
};
const escape = text => text.replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#39;");
for (const locale of ["vi", "en", "zh"]) {
  for (const route of ["/voice/tts", "/voice/saved"]) {
    test(`${locale}/${route}: volume slider uses the native accessible field name and retains numeric semantics`, () => {
      const view = render(locale, route, {});
      const range = view.html.match(/<input\b[^>]*data-portal-range-sync="volume_percent"[^>]*>/)?.[0];
      assert(range, "Actual Voice form range is present");
      assert(range.includes(`aria-label="${native[locale].volume}"`));
      for (const attribute of ['type="range"', 'min="0"', 'max="200"', 'step="10"', 'value="100"']) assert(range.includes(attribute), attribute);
      assert.equal((view.html.match(/name="volume_percent"/g) || []).length, 1, "Only one submitted volume field");
    });
  }
  test(`${locale}: missing name renders an account label and a natural greeting, not technical session text`, () => {
    const view = render(locale, "/dashboard", {
      profile: {locale},
      session: {authenticated: true, csrfToken: "synthetic-unit-only"}
    });
    const header = view.qa.renderHeader(view.page, view.context);
    assert(!header.includes("Phiên bảo mật đang chờ"));
    assert(header.includes(native[locale].account));
    assert(view.text.includes(native[locale].greeting));
    assert(!view.text.includes("Phiên bảo mật đang chờ"));
  });
  test(`${locale}: a real customer name stays opaque and escaped in header and greeting`, () => {
    const name = "Facebook TikTok media studio <b>Khách</b>";
    const raw = {profile: {locale, displayName: name}, session: {authenticated: true, csrfToken: "synthetic-unit-only"}};
    const view = render(locale, "/dashboard", raw);
    const header = view.qa.renderHeader(view.page, view.context);
    assert(header.includes(escape(name)));
    assert(view.html.includes(escape(name)));
    assert(!header.includes("<b>Khách</b>"));
    assert.equal(raw.profile.displayName, name);
  });
}
