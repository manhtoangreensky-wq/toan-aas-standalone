import assert from "node:assert/strict";
import fs from "node:fs";
import {createHash} from "node:crypto";

const raw = fs.readFileSync(new URL("../fixtures/audio-review-pending-contract.json", import.meta.url));
const fail = "Unreviewed audio review pending feedback";
const hash = value => createHash("sha256").update(value).digest("hex");
const normalized = raw.toString("utf8").replace(/\r\n/g, "\n");
assert.equal(hash(normalized), "5f9c628132c86d4b7b5fa106cfa16b68a015b15a1bffa49dd303c4192db42aac", fail);
assert.ok([hash(normalized), hash(normalized.replace(/\n/g, "\r\n"))].includes(hash(raw)), fail + " uniform checkout newlines");
const contract = JSON.parse(normalized);
assert.equal(contract.base, "cd9c5c14263e1397531056e318a9f46394a8562d", fail);
assert.equal(contract.records.length, 3, fail);
const integration = "static/portal/integration.js", catalogue = "static/portal/portal-i18n.js";
assert.deepEqual(contract.records.map(row => row.file), [integration, integration, catalogue], fail);
const count = (source, part) => source.split(part).length - 1;
const markers = {
  [integration]: ['"review.notFound"', '"review.conflict"', '"review.maintenance"',
    "} catch (error) {\n          if (!audioHubReviewPackRequestIsCurrent(requestEpoch, sessionEpoch, route, collectionId, expectedRevision)) return;"],
  [catalogue]: ['"audioWorkspace.feedback.review.notFound"', '"audioWorkspace.feedback.review.conflict"',
    '"audioWorkspace.feedback.review.maintenance"']
};

// Historical input only; the physical candidate is independently compared with BASE plus forward records.
export function audioReviewPendingHistoricalSource(source, file) {
  assert.equal(typeof source, "string", fail);
  assert.equal(typeof file, "string", fail);
  if (!Object.hasOwn(markers, file) || !markers[file].some(marker => source.includes(marker))) return source;
  const records = contract.records.filter(row => row.file === file);
  for (const row of records) assert.equal(count(source, row.new), 1, fail + " exact current record");
  if (file === integration) {
    const action = source.indexOf('      if (action === "audio-hub-review-pack-compose") {');
    const next = source.indexOf('      if (action === "media-collection-compose") {', action);
    const catchAt = source.indexOf(records[0].new);
    const helper = source.indexOf("  function audioHubReviewFeedbackText(");
    const nextHelper = source.indexOf("  function audioHubReviewPackBoundaryIsSafe(", helper);
    const mappingAt = source.indexOf(records[1].new);
    assert.ok(action >= 0 && action < catchAt && catchAt < next && helper >= 0 && helper < mappingAt && mappingAt < nextHelper, fail + " ownership");
  } else {
    const verify = source.indexOf("  function verifyEqualKeysets() {"), at = source.indexOf(records[0].new);
    const call = source.indexOf("  verifyEqualKeysets();"), freeze = source.indexOf("  deepFreeze(MESSAGES);");
    assert.ok(verify >= 0 && verify < at && at < call && call < freeze, fail + " catalogue ownership");
  }
  for (const row of [...records].reverse()) source = source.replace(row.new, () => row.old);
  assert.ok(markers[file].every(marker => !source.includes(marker)), fail + " detached marker");
  return source;
}

const rows = [
  ["audioWorkspace.feedback.review.notFound", "Không tìm thấy bộ sưu tập trong tài khoản hiện tại.", "This collection was not found in your account.", "在当前账户中未找到该合集。"],
  ["audioWorkspace.feedback.review.conflict", "Bộ sưu tập đã thay đổi. Hãy tải lại trước khi tiếp tục.", "This collection has changed. Reload it before continuing.", "该合集已更改，请重新加载后继续。"],
  ["audioWorkspace.feedback.review.maintenance", "Trung tâm âm thanh đang bảo trì. Vui lòng thử lại sau.", "The audio workspace is under maintenance. Please try again later.", "音频工作区正在维护，请稍后重试。"]
];
export function audioReviewPendingHistoricalSnapshot(entries, locale) {
  assert.ok(["vi", "en", "zh"].includes(locale) && Array.isArray(entries), fail);
  const keys = rows.map(row => row[0]), found = entries.filter(([key]) => keys.includes(key));
  if (!found.length) return entries;
  assert.deepEqual(found.map(([key]) => key), keys, fail + " exact ordered keys");
  const index = ["vi", "en", "zh"].indexOf(locale) + 1;
  for (const row of rows) {
    const matches = entries.filter(([key]) => key === row[0]);
    assert.equal(matches.length, 1, fail + " unique key");
    assert.equal(matches[0][1], row[index], fail + " exact value");
  }
  return entries.filter(([key]) => !keys.includes(key));
}
