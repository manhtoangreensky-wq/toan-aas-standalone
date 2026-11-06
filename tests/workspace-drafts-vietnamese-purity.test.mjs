import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";
import vm from "node:vm";

const portalSource = fs.readFileSync("static/portal/portal.js", "utf8");
const i18nSource = fs.readFileSync("static/portal/portal-i18n.js", "utf8");
const shellSource = fs.readFileSync("copyfast_pages.py", "utf8");
const untranslatedFixedCopy = /\b(?:media|studio|workspace|web|brief|workflow|route|project|job|browser|snapshot|owner-scoped|signed account|scalar|quote receipt|provider|payment|canonical|output|validation|staging|estimate|confirmation|authority|server|document|resume|handoff|content|assets?|file|upload|profile|api)\b/i;
const expectedVietnamese = {
  "workspaceDrafts.page.title": "Bản nháp không gian làm việc",
  "workspaceDrafts.page.description": "Quản lý các bản nháp riêng tư trên ứng dụng trước khi tiếp tục đúng quy trình.",
  "workspaceDrafts.filter.searchPlaceholder": "Tên bản nháp hoặc quy trình",
  "workspaceDrafts.filter.workflowLabel": "Quy trình",
  "workspaceDrafts.filter.workflowAll": "Tất cả quy trình",
  "workspaceDrafts.pagination.label": "Phân trang bản nháp",
  "workspaceDrafts.card.archiveConfirm": "Lưu trữ bản nháp này? Thao tác này không gửi dữ liệu sang Bot, không thay đổi tác vụ, Xu hay tệp.",
  "workspaceDrafts.card.defaultFeature": "Quy trình trên ứng dụng",
  "workspaceDrafts.card.workflow": "Quy trình",
  "workspaceDrafts.card.savedDataValue": "Chỉ gồm các giá trị ngắn thuộc ứng dụng.",
  "workspaceDrafts.card.resume": "Tiếp tục bản nháp",
  "workspaceDrafts.card.attach": "Thêm vào dự án",
  "workspaceDrafts.card.attachLocked": "Thao tác bàn giao đang khóa",
  "workspaceDrafts.card.attachProjectLabel": "Thêm vào dự án",
  "workspaceDrafts.card.attachProjectFallback": "Dự án trên ứng dụng",
  "workspaceDrafts.card.attachNote": "Máy chủ tạo bản chụp tài liệu phiên bản 1, gắn với tài khoản hiện tại; không đưa nội dung bản nháp vào đường dẫn hoặc bộ nhớ trình duyệt.",
  "workspaceDrafts.card.attachAcknowledgement": "Tôi xác nhận chỉ tạo một bản chụp tài liệu phiên bản 1 thuộc tài khoản này; bản nháp gốc không bị sửa.",
  "workspaceDrafts.card.attachConfirm": "Tạo một tài liệu phiên bản 1 từ bản nháp này trong dự án đã chọn? Bản nháp gốc vẫn được giữ nguyên; không gọi Bot hay nhà cung cấp, không tạo tác vụ, không thay đổi Xu hoặc PayOS.",
  "workspaceDrafts.card.attachEmpty": "Tạo một dự án đang hoạt động trước khi đưa bản nháp vào tài liệu.",
  "workspaceDrafts.card.attachCreateProject": "Tạo dự án",
  "workspaceDrafts.empty.filteredBody": "Điều chỉnh tên, quy trình hoặc trạng thái để xem các bản nháp khác của tài khoản này.",
  "workspaceDrafts.empty.title": "Chưa có bản nháp",
  "workspaceDrafts.empty.body": "Mở một công cụ rồi chọn Lưu bản nháp. Bạn có thể lưu nội dung trước khi kết nối sẵn sàng; không gửi yêu cầu sang Bot.",
  "workspaceDrafts.filter.note": "Bộ lọc chỉ tải lại dữ liệu của tài khoản trong phiên trang hiện tại. Không lưu vào đường dẫn, Telegram hay bộ nhớ trình duyệt; nội dung bản định hướng không được liệt kê hoặc tìm kiếm.",
  "workspaceDrafts.boundary.title": "Bản nháp, không phải tác vụ",
  "workspaceDrafts.boundary.body": "Thư viện này chỉ lưu nội dung bản định hướng và các lựa chọn ngắn của tài khoản đã xác thực. Không lưu tệp, mã tải lên, hồ sơ giọng, biên nhận báo giá, nhà cung cấp, thanh toán, Xu, tác vụ hay kết quả.",
  "workspaceDrafts.library.body": "Tiếp tục sẽ đưa nội dung hợp lệ trở lại đúng biểu mẫu. Tệp và lựa chọn nhạy cảm do nguồn chuẩn cấp phải được chọn và kiểm tra lại trong quy trình.",
  "workspaceDrafts.library.openWorkflow": "Mở quy trình",
  "workspaceDrafts.safety.body": "Mỗi lần tiếp tục vẫn phải kiểm tra biểu mẫu, tệp tải lên tạm, ước tính, xác nhận và quyền do nguồn chuẩn cấp. Bản nháp không chứng minh quyền sở hữu tệp, không giữ giá hoặc Xu và không tạo kết quả."
};

function textOf(html) {
  return String(html)
    .replace(/<svg\b[\s\S]*?<\/svg>/g, " ")
    .replace(/<[^>]*>/g, " ")
    .replace(/&(?:amp|quot|lt|gt|#39);/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function render(locale, options = {}) {
  const noop = () => {};
  const document = {
    readyState: "loading",
    title: "",
    addEventListener: noop,
    querySelector: () => null,
    querySelectorAll: () => [],
    getElementById: () => null,
    documentElement: { lang: locale, setAttribute: noop, getAttribute: () => null, classList: { add: noop, remove: noop } },
    body: { classList: { add: noop, remove: noop, toggle: noop }, setAttribute: noop }
  };
  const window = {
    document,
    navigator: { language: locale, userAgent: "Workspace draft locale QA" },
    location: { pathname: "/workspace", search: "", href: "https://unit.invalid/workspace" },
    addEventListener: noop,
    dispatchEvent: noop,
    CustomEvent: function () {},
    matchMedia: () => ({ matches: false, addEventListener: noop }),
    localStorage: { getItem: () => null, setItem: noop }
  };
  const sandbox = vm.createContext({
    window, document, navigator: window.navigator, URL, URLSearchParams, Intl, console,
    setTimeout: noop, clearTimeout: noop,
    fetch: () => { throw Error("Network access is forbidden in locale tests"); }
  });
  vm.runInContext(i18nSource, sandbox);
  const marker = "  window.TOANAASPortal = Object.freeze({";
  assert.ok(portalSource.includes(marker), "Portal export anchor exists");
  const exposedSource = portalSource.replace(marker,
    "  window.__WorkspaceDraftLocaleTest = {renderWorkspaceDrafts};\n" + marker);
  vm.runInContext(exposedSource, sandbox);
  window.TOANAASI18n.setLocale(locale, { emit: false });

  const page = window.TOANAASPortal.resolvePage("/workspace");
  const hasProject = options.hasProject === true;
  const drafts = options.filteredEmpty || options.empty ? [] : [{
    id: "11111111-1111-4111-8111-111111111111",
    state: "draft",
    route: "/features",
    title: "Bản nháp do khách nhập",
    feature_key: options.featureKey || "ma_42",
    ...(options.featureTitle ? { feature_title: options.featureTitle } : {}),
    created_at: "2026-11-05T00:00:00Z"
  }];
  const context = {
    profile: { locale, displayName: "QA" },
    session: { authenticated: true, csrfToken: "synthetic-locale-test" },
    capabilities: {
      "workspace-drafts-refresh": true,
      "workspace-draft-archive": true,
      "workspace-draft-resume": true,
      "workspace-draft-attach": true
    },
    workspaceDraftReadState: options.readState || "ready",
    workspaceDraftListing: {
      filters: { q: options.filteredEmpty ? "không khớp" : "", state: "all", feature_key: "" },
      summary: { active: drafts.length, archived: 0 },
      pagination: { offset: 0, returned: drafts.length, has_more: true, next_offset: 20, previous_offset: null }
    },
    workspaceDrafts: drafts,
    projects: hasProject ? [{ id: "22222222-2222-4222-8222-222222222222", state: "active", title: "Dự án QA" }] : [],
    catalog: [],
    workspaceDraftFeatures: []
  };
  const html = window.__WorkspaceDraftLocaleTest.renderWorkspaceDrafts(page, context);
  return {
    html,
    text: textOf(html),
    messages: window.TOANAASI18n.messages,
    rawFeatureKey: context.workspaceDrafts[0]?.feature_key || ""
  };
}

test("Vietnamese Workspace Drafts fixed copy is fully translated in rendered states", () => {
  const sample = render("vi", { hasProject: true });
  const actualVietnamese = Object.fromEntries(Object.keys(expectedVietnamese).map((key) => [key, sample.messages.vi[key]]));
  assert.deepEqual(actualVietnamese, expectedVietnamese, "All fixed Workspace Drafts Vietnamese copy must use the reviewed wording");
  for (const options of [{ hasProject: true }, {}, { empty: true }, { filteredEmpty: true }]) {
    const { text } = render("vi", options);
    assert.doesNotMatch(text, untranslatedFixedCopy, text);
  }
});

test("English and Chinese Workspace Drafts copy remains in its own language", () => {
  const en = render("en", { hasProject: true });
  const zh = render("zh", { hasProject: true });
  assert.ok(en.text.includes("Workspace drafts"));
  assert.ok(en.text.includes("Continue brief"));
  assert.ok(zh.text.includes("工作台草稿"));
  assert.ok(zh.text.includes("继续简报"));
  assert.equal(en.messages.en["workspaceDrafts.card.attach"], "Add to Project");
  assert.equal(zh.messages.zh["workspaceDrafts.card.attach"], "加入项目");
});

test("server first-paint title follows VI, EN and ZH without changing other locales", () => {
  const title = shellSource.match(/^\s*"\/workspace": \{([^\n]+)\},?$/m);
  assert.ok(title, "the /workspace first-paint title exists");
  assert.match(title[1], /"vi": "Bản nháp không gian làm việc · TOAN AAS"/);
  assert.match(title[1], /"en": "Workspace drafts · TOAN AAS"/);
  assert.match(title[1], /"zh": "工作台草稿 · TOAN AAS"/);
});

for (const [locale, expected] of [["vi", "Bài hát có lời"], ["en", "Song with lyrics"], ["zh", "带歌词歌曲"]]) {
  test(`${locale}: draft feature label uses its reviewed localized catalogue title`, () => {
    const { text, messages } = render(locale, { hasProject: true, featureKey: "music_song", featureTitle: "Bài hát AI" });
    assert.equal(messages[locale]["featureCatalog.entry.music_song.title"], expected);
    assert.ok(text.includes(expected), text);
    assert.doesNotMatch(text, /\bmusic_song\b|Workflow Web|Bài hát AI/);
  });
}

test("Workspace Drafts catalogue keys are complete and balanced across VI, EN and ZH", () => {
  const { messages } = render("vi");
  const keys = Object.fromEntries(["vi", "en", "zh"].map((locale) => [
    locale,
    Object.keys(messages[locale]).filter((key) => key.startsWith("workspaceDrafts.")).sort()
  ]));
  assert.ok(keys.vi.length > 0);
  assert.deepEqual(keys.en, keys.vi);
  assert.deepEqual(keys.zh, keys.vi);
  for (const locale of ["vi", "en", "zh"]) {
    for (const key of keys.vi) assert.ok(messages[locale][key]?.trim(), `${locale}.${key} must not be empty`);
  }
});

test("unknown draft feature does not expose the API's English fallback", () => {
  const { text } = render("vi", { hasProject: true, featureKey: "unknown_feature", featureTitle: "Workflow Web" });
  assert.ok(text.includes(expectedVietnamese["workspaceDrafts.card.defaultFeature"]), text);
  assert.doesNotMatch(text, /unknown_feature|Workflow Web/);
});

test("Workspace Drafts locale rendering preserves routes and dynamic records", () => {
  const withProject = render("vi", { hasProject: true });
  const withoutProject = render("vi");
  assert.ok(withProject.text.includes("Bản nháp do khách nhập"));
  assert.ok(withProject.text.includes("Dự án QA"));
  assert.equal(withProject.rawFeatureKey, "ma_42", "the renderer must not mutate the saved feature key");
  assert.doesNotMatch(withProject.text, /\bma_42\b/, "the internal feature key must not be shown as customer copy");
  assert.match(withProject.html, /data-portal-action="workspace-draft-resume"/);
  assert.match(withProject.html, /data-portal-action="workspace-draft-archive"/);
  assert.match(withProject.html, /data-portal-action="workspace-draft-attach"/);
  assert.match(withProject.html, /data-portal-route="\/workspace"/);
  assert.match(withoutProject.html, /href="\/projects\/new"/);
});

test("Vietnamese Workspace Drafts loading, failed and guarded states remain localised", () => {
  for (const state of ["loading", "failed", "guarded"]) {
    const { html, text } = render("vi", { readState: state });
    assert.match(html, new RegExp(`data-workspace-draft-read-state="${state}"`));
    assert.doesNotMatch(text, untranslatedFixedCopy, `${state}: ${text}`);
  }
});
