import assert from "node:assert/strict";
import fs from "node:fs";
import {imageStudioDetailLoadingHistoricalSource} from "./image-studio-detail-loading-historical.mjs";

const contract = JSON.parse(fs.readFileSync(new URL("../fixtures/image-studio-read-feedback-contract.json", import.meta.url)));
const fail = "Unreviewed Image Studio read feedback";
assert.equal(contract.base, "ef3643d84c269aa2a07e411debe400a44f72d8e6", fail);
assert.equal(contract.records.length, 6, fail);
const labels = {
  vi: ["Đã làm mới.", "Đã áp dụng bộ lọc.", "Đã tải danh sách.", "Đã tải trang.", "Không thể tải dữ liệu. Vui lòng thử lại."],
  en: ["Refreshed.", "Filter applied.", "List loaded.", "Page loaded.", "Could not load the data. Please try again."],
  zh: ["已刷新。", "已应用筛选。", "列表已加载。", "页面已加载。", "无法加载数据，请重试。"]
};
const keys = ["refreshed", "filtered", "listed", "paged", "failed"].map(key => "imageStudioReadFeedback." + key);

export function imageStudioReadFeedbackHistoricalSource(source, file) {
  source = imageStudioDetailLoadingHistoricalSource(source, file);
  const records = contract.records.filter(row => row.file === file);
  if (!records.length || !source.includes(records[0].new)) return source;
  for (const row of records) assert.equal(source.split(row.new).length - 1, 1, fail);
  for (const row of [...records].reverse()) source = source.replace(row.new, () => row.old);
  return source;
}

export function imageStudioReadFeedbackHistoricalSnapshot(entries, locale) {
  assert.ok(Array.isArray(entries) && Object.hasOwn(labels, locale), fail);
  const found = entries.filter(([key]) => keys.includes(key));
  if (!found.length) return entries;
  assert.equal(found.length, keys.length, fail);
  for (const [index, key] of keys.entries()) assert.equal(found.find(row => row[0] === key)?.[1], labels[locale][index], fail);
  return entries.filter(([key]) => !keys.includes(key));
}
