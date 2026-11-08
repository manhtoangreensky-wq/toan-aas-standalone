import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';

const portal = fs.readFileSync('static/portal/portal.js', 'utf8');
const i18n = fs.readFileSync('static/portal/portal-i18n.js', 'utf8');

test('account avatar and membership panels use locale catalogues', () => {
  const start = portal.indexOf('function renderAccount(');
  const end = portal.indexOf('function renderInterfaceLocaleNavigator', start);
  const source = portal.slice(start, end);
  assert.match(source, /accountCenterText/);
  assert.doesNotMatch(source, /Nhận diện cá nhân|Ảnh đại diện cá nhân|Quyền lợi tài khoản|Xem bảng giá & dịch vụ/);
});

test('tickets Bot handoff fixed chrome uses support locale catalogue', () => {
  const start = portal.indexOf('function renderTickets(');
  const end = portal.indexOf('function renderSupport', start);
  const source = portal.slice(start, end);
  assert.match(source, /supportTicketText/);
  assert.doesNotMatch(source, /Theo dõi sâu trong Bot|Mở Bot|Sao chép \/tickets|Bot URL chưa sẵn sàng/);
});

test('admin support activity has an explicit admin locale path', () => {
  const start = portal.indexOf('function supportEventLabel');
  const end = portal.indexOf('function renderSupportActivity', start);
  const source = portal.slice(start, end);
  assert.match(source, /adminSupportText|admin/);
  assert.match(i18n, /adminSupport\./);
});
