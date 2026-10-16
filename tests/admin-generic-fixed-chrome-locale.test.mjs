import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';

const source = fs.readFileSync('static/portal/portal-i18n.js', 'utf8');
const start = source.indexOf('const ADMIN_GENERIC_MESSAGES = {');
const viStart = source.indexOf('    vi: {', start);
const enStart = source.indexOf('    en:', viStart);
assert.ok(start >= 0 && viStart > start && enStart > viStart, 'Admin generic catalogue must remain present');
const vi = source.slice(viStart, enStart);

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
    '"adminGeneric.systemStewardship.route.title": "Quản trị hệ thống và dữ liệu"',
    '"adminGeneric.postbackReadiness.route.title": "Mức sẵn sàng phản hồi"',
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
    'Access Posture',
    'System & Data Stewardship',
    'Postback Readiness',
    'Job-Lock'
  ]) assert.equal(vi.includes(phrase), false, `English fixed chrome leaked: ${phrase}`);
});
