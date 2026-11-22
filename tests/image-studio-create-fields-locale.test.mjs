import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
import {execFileSync} from "node:child_process";

const BASE = "05b7ba761bd35cf4da498443db9046ed59429d90";
const files = {portal: "static/portal/portal.js", i18n: "static/portal/portal-i18n.js"};
const current = Object.fromEntries(Object.entries(files).map(([k, f]) => [k, fs.readFileSync(f, "utf8")]));
const baseline = Object.fromEntries(Object.entries(files).map(([k, f]) => [k,
  execFileSync("git", ["show", BASE + ":" + f], {encoding: "utf8", maxBuffer: 20e6})]));
const expected = {
  vi: {
    labels: ["Tên bảng thiết kế", "Mục đích thiết kế", "Ngôn ngữ mô tả", "Tỷ lệ khung hình", "Định dạng mong muốn", "Mô tả ý tưởng", "Định hướng phong cách", "Điều cần tránh", "Thẻ", "Dự án (không bắt buộc)"],
    hints: ["Ví dụ: Hình ảnh bộ sưu tập mùa hè", "Thông điệp, bối cảnh, giới hạn thương hiệu và điểm cần rà soát…", "Bố cục, ánh sáng, màu sắc, chất liệu và cảm xúc mong muốn…", "Những yếu tố không phù hợp với thương hiệu hoặc mục tiêu…", "ra mắt, sản phẩm, đánh giá"],
    helps: ["Chỉ dùng để sắp xếp ý tưởng, không tự tạo ảnh.", "Chỉ ghi nhận lựa chọn; chưa tạo tệp."], noProject: "Không liên kết dự án"
  },
  en: {
    labels: ["Design board name", "Design intent", "Description language", "Aspect ratio", "Preferred format", "Creative brief", "Style direction", "What to avoid", "Tags", "Project (optional)"],
    hints: ["Example: Summer collection visuals", "Message, context, brand limits and points to review…", "Desired layout, lighting, colors, materials and mood…", "Elements that do not fit your brand or goal…", "launch, product, review"],
    helps: ["Organizes ideas only; it does not create an image.", "Records your choice only; no file is created."], noProject: "No project"
  },
  zh: {
    labels: ["画板名称", "设计意图", "描述语言", "画面比例", "期望格式", "创意说明", "风格方向", "需要避免的内容", "标签", "项目（可选）"],
    hints: ["例如：夏季系列视觉设计", "信息、背景、品牌限制和需要检查的要点……", "期望的构图、光线、颜色、材质与氛围……", "不符合品牌或目标的元素……", "上新，产品，评审"],
    helps: ["仅用于整理想法，不会自动生成图像。", "仅记录选择，尚未创建文件。"], noProject: "不关联项目"
  }
};
const names = ["title", "image_intent", "language", "aspect_ratio", "output_format", "creative_brief", "style_direction", "negative_direction", "tags", "project_id"];
const hintNames = ["title", "creative_brief", "style_direction", "negative_direction", "tags"];
const id = "11111111-1111-4111-8111-111111111111";

function fields(source, locale) {
  const noop = () => {};
  const document = {readyState: "loading", addEventListener: noop, querySelector: () => null, querySelectorAll: () => [],
    getElementById: () => null, documentElement: {lang: locale, setAttribute: noop, getAttribute: () => null,
      classList: {add: noop, remove: noop}}, body: {classList: {add: noop, remove: noop, toggle: noop}, setAttribute: noop}};
  const window = {document, navigator: {language: locale}, location: {pathname: "/image-studio", search: ""},
    addEventListener: noop, dispatchEvent: noop, matchMedia: () => ({matches: false, addEventListener: noop}),
    localStorage: {getItem: () => null, setItem: noop}, setTimeout: noop, clearTimeout: noop};
  const box = vm.createContext({window, document, navigator: window.navigator, location: window.location,
    URL, URLSearchParams, Intl, console, setTimeout: noop, clearTimeout: noop});
  vm.runInContext(source.i18n, box);
  const anchor = "  window.TOANAASPortal = Object.freeze({";
  assert.equal(source.portal.split(anchor).length - 1, 1);
  vm.runInContext(source.portal.replace(anchor, "  window.__fieldsQA = imageStudioArtboardFields;\n" + anchor), box);
  window.TOANAASI18n.setLocale(locale, {emit: false});
  const context = {imageStudioReferences: {projects: [{id, title: "Facebook & 客户 <Original>"}]}};
  const before = JSON.stringify(context);
  const result = JSON.parse(JSON.stringify(window.__fieldsQA(context)));
  assert.equal(JSON.stringify(context), before);
  return result;
}

for (const locale of ["vi", "en", "zh"]) {
  test(`${locale}: shared field definitions use labels and prompts in the selected language`, () => {
    const result = fields(current, locale), want = expected[locale];
    assert.deepEqual(result.map(row => row.name), names);
    assert.deepEqual(result.map(row => row.label), want.labels);
    assert.deepEqual(hintNames.map(name => result.find(row => row.name === name).placeholder), want.hints);
    assert.deepEqual([result[1].help, result[4].help], want.helps);
    assert.equal(result[9].emptyLabel, want.noProject);
  });
  test(`${locale}: option values, limits, required flags and customer project text remain unchanged`, () => {
    const now = fields(current, locale), old = fields(baseline, locale);
    // The later ratio/format copy unit intentionally changes only their option
    // text; its own physical-bundle tests validate that text independently.
    const stripCopy = rows => rows.map(({label, placeholder, help, emptyLabel, ...other}) => {
      if (["aspect_ratio", "output_format"].includes(other.name)) other.options = other.options.map(([value]) => [value]);
      return other;
    });
    assert.deepEqual(stripCopy(now), stripCopy(old));
    assert.deepEqual(now[9].options, [{value: id, label: "Facebook & 客户 <Original>"}]);
    assert.equal(now[2].placeholder, "vi");
  });
}
