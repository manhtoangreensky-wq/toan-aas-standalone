import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';

const source = fs.readFileSync('static/portal/portal-i18n.js', 'utf8');
const catalogStart = source.indexOf('const ADMIN_GENERIC_MESSAGES = {');
const viStart = source.indexOf('    vi: {', catalogStart);
const enStart = source.indexOf('    en:', viStart);
assert.ok(catalogStart >= 0 && viStart > catalogStart && enStart > viStart, 'Admin generic catalogue exists');
const vi = source.slice(viStart, enStart);
const stewardship = vi.split(/\r?\n/).filter((line) => line.includes('"adminGeneric.systemStewardship.')).join('\n');

test('Vietnamese system stewardship cards use Vietnamese fixed chrome', () => {
  const expected = [
    'Theo dõi tự động hóa',
    'Tình trạng bảo mật',
    'Tình trạng quyền truy cập',
    'Tài liệu quản trị',
    'Kho tài liệu nội bộ',
    'Hệ thống',
    'Môi trường chạy',
    'Bản sao lưu'
  ];
  for (const label of expected) assert.match(stewardship, new RegExp(`"${label}"`));
  assert.doesNotMatch(stewardship, /\b(?:Automation Monitor|Security Posture|Access Posture|Governance Documents|Internal Document Archive|Runtime|Backups)\b/);
});
