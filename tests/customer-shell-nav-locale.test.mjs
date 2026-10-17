import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const source = fs.readFileSync('static/portal/portal-i18n.js', 'utf8');
const document = { title: '', documentElement: { lang: '', setAttribute() {} } };
const window = { document, navigator: { language: 'vi' }, dispatchEvent() {}, CustomEvent() {} };
const context = vm.createContext({ window, document, Intl, Date, Number, String, Object, Array, Set, Map, Math, RegExp, JSON });
vm.runInContext(source, context);
const messages = window.TOANAASI18n.messages.vi;

test('Vietnamese customer shell navigation uses translated fixed chrome', () => {
  const expected = {
    'shellNav.analyticsWorkspace': 'Không gian phân tích',
    'shellNav.memoryCenter': 'Trung tâm ghi nhớ',
    'shellNav.imageOperationsHub': 'Trung tâm thao tác hình ảnh',
    'shellNav.documentWorkspace': 'Không gian tài liệu',
    'shellNav.audioWorkspace': 'Không gian âm thanh',
    'shellNav.automationCenter': 'Trung tâm tự động hóa',
    'shellNav.operationsCenter': 'Trung tâm điều hành',
    'shellNav.mediaFactory': 'Xưởng đa phương tiện',
    'shellNav.creativeFlow': 'Quy trình sáng tạo',
    'shellNav.storyboardComposer': 'Soạn bảng phân cảnh'
  };
  for (const [key, value] of Object.entries(expected)) assert.equal(messages[key], value, `${key} must use reviewed Vietnamese copy`);
  const changed = Object.keys(expected).map((key) => messages[key]).join(' | ');
  assert.doesNotMatch(changed, /(?:Analytics Workspace|Memory Center|Image Operations Hub|Document Workspace|Audio Workspace|Automation Center|Operations Center|Media Factory|Creative Flow|storyboard)/i);
});
