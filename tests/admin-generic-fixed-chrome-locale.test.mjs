import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';

const source = fs.readFileSync('static/portal/portal-i18n.js', 'utf8');
const start = source.indexOf('const ADMIN_GENERIC_MESSAGES = {');
const viStart = source.indexOf('    vi: {', start);
const enStart = source.indexOf('    en:', viStart);
assert.ok(start >= 0 && viStart > start && enStart > viStart, 'Admin generic catalogue must remain present');
const vi = source.slice(viStart, enStart);
const securityStart = vi.indexOf('"adminGeneric.securityAccess.state.loadingTitle"');
const securityEnd = vi.indexOf('"adminGeneric.automationMonitor.route.title"', securityStart);
assert.ok(securityStart >= 0 && securityEnd > securityStart, 'Security/access catalogue must remain present');
const security = vi.slice(securityStart, securityEnd);
const automationStart = vi.indexOf('"adminGeneric.automationMonitor.route.title"');
const automationEnd = vi.indexOf('"adminGeneric.systemStewardship.route.title"', automationStart);
assert.ok(automationStart >= 0 && automationEnd > automationStart, 'Automation monitor catalogue must remain present');
const automation = vi.slice(automationStart, automationEnd);
const guidanceStart = vi.indexOf('"adminGeneric.postbackReadiness.route.title"');
const guidanceEnd = vi.indexOf('"adminGeneric.deliveryRuntimeNavigation.group.title"', guidanceStart);
assert.ok(guidanceStart >= 0 && guidanceEnd > guidanceStart, 'Admin guidance catalogue must remain present');
const guidance = vi.slice(guidanceStart, guidanceEnd);
const guidanceValues = guidance.replace(/^\s*"[^"]+":\s*/gm, '');
const deliveryStart = vi.indexOf('"adminGeneric.deliveryRuntimeNavigation.group.title"');
const deliveryEnd = vi.length;
assert.ok(deliveryStart >= 0, 'Delivery/runtime catalogue must remain present');
const delivery = vi.slice(deliveryStart, deliveryEnd);
const deliveryValues = delivery.replace(/^\s*"[^"]+":\s*/gm, '');

test('Vietnamese Admin fixed chrome removes the reported English leaks', () => {
  const expected = [
    '"adminGeneric.module.freezes": "Bảo trì"',
    '"adminGeneric.module.audit": "Kiểm soát"',
    '"adminGeneric.failedJobs.noticeTitle": "Hàng chờ sự cố chỉ đọc"',
    '"adminGeneric.failedJobs.column.job": "Tác vụ"',
    '"adminGeneric.failedJobs.column.output": "Kết quả"',
    '"adminGeneric.audit.filter.option.workspace": "Không gian làm việc"',
    '"adminGeneric.maintenance.title": "Bảo trì tính năng chuẩn"',
    '"adminGeneric.securityAccess.route.securityTitle": "Tình trạng bảo mật"',
    '"adminGeneric.securityAccess.metric.mfaRuntime.label": "MFA đang chạy"',
    '"adminGeneric.securityAccess.access.roleCounts.label": "Quản trị viên / Quản lý hỗ trợ / Nhân viên hỗ trợ"',
    '"adminGeneric.securityAccess.panel.rateLimit.title": "Tổng hợp giới hạn tốc độ"',
    '"adminGeneric.securityAccess.boundary.body": "Màn hình này là khả năng quan sát của ứng dụng Web, không phải mặt phẳng điều khiển hay mô-đun tương thích cầu nối."',
    '"adminGeneric.systemStewardship.route.title": "Quản trị hệ thống và dữ liệu"',
    '"adminGeneric.postbackReadiness.route.title": "Postback Readiness"',
    '"adminGeneric.jobRecoveryGuide.route.title": "Hướng dẫn xử lý tác vụ bị khóa"'
  ];
  for (const line of expected) assert.ok(vi.includes(line), `missing reviewed Vietnamese copy: ${line}`);
  for (const phrase of [
    'Incident queue',
    '"Job"',
    '"Output"',
    '"Workspace"',
    '"Maintenance"',
    '"Audit"',
    'Security Posture',
    'System & Data Stewardship',
    'Job-Lock'
  ]) assert.equal(vi.includes(phrase), false, `English fixed chrome leaked: ${phrase}`);
  for (const phrase of [
    'Security Posture',
    'Web-native',
    'aggregate',
    'session reference',
    'rate limit',
    'control plane'
  ]) assert.equal(security.includes(phrase), false, `English security/access chrome leaked: ${phrase}`);
  for (const phrase of [
    'receipt scheduler',
    'receipt private',
    'projection receipt',
    'Inbox Center',
    'Scheduler',
    'Web-native',
    'metadata',
    'Preflight',
    'control plane',
    'provider',
    'delivery',
    'payment',
    'job'
  ]) assert.equal(automation.includes(phrase), false, `English automation chrome leaked: ${phrase}`);
  for (const line of [
    '"adminGeneric.postbackReadiness.route.title": "Postback Readiness"',
    '"adminGeneric.postbackReadiness.checkpoint.handoff.title": "Bàn giao đúng thẩm quyền"',
    '"adminGeneric.jobRecoveryGuide.route.title": "Hướng dẫn xử lý tác vụ bị khóa"',
    '"adminGeneric.jobRecoveryGuide.escalation.kicker": "Chuyển cấp an toàn"',
    '"adminGeneric.jobRecoveryGuide.boundary.noMutation.title": "Không xóa, thử lại hoặc hoàn tiền"'
  ]) assert.ok(guidance.includes(line), `missing reviewed guidance copy: ${line}`);
  for (const phrase of [
    'canonical admin',
    'handoff',
    'guidance',
    'triage',
    'job-lock',
    'queue',
    'delivery',
    'billing',
    'browser',
    'credential',
    'escalate',
    'runbook',
    'financial',
    'mutation',
    'provider'
  ]) assert.equal(guidanceValues.includes(phrase), false, `English guidance chrome leaked: ${phrase}`);
  for (const line of [
    '"adminGeneric.deliveryRuntimeNavigation.group.title": "Giao nhận & Môi trường vận hành"',
    '"adminGeneric.deliveryRuntimeNavigation.workers.title": "Tiến trình xử lý"',
    '"adminGeneric.deliveryRuntimeNavigation.runtime.title": "Môi trường vận hành"'
  ]) assert.ok(delivery.includes(line), `missing reviewed delivery/runtime copy: ${line}`);
  for (const phrase of [
    'Runtime',
    'Jobs',
    'job',
    'delivery',
    'provider',
    'secret',
    'browser',
    'Workers',
    'queue',
    'guarded mode',
    'maintenance',
    'freeze',
    'adapter write',
    'audit'
  ]) assert.equal(deliveryValues.includes(phrase), false, `English delivery/runtime chrome leaked: ${phrase}`);
});
