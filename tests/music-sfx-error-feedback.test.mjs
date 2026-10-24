import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';

const NL = String.fromCharCode(10);
const integrationPath = path.resolve('static/portal/integration.js');
const i18nPath = path.resolve('static/portal/portal-i18n.js');
const source = fs.readFileSync(integrationPath, 'utf8').replaceAll(String.fromCharCode(13), '');

function extractFn(name) {
  const a = source.indexOf('  function ' + name + '(');
  if (a < 0) return '';
  const b = source.indexOf(NL + '  }', a);
  assert.ok(b > a);
  return source.slice(a, b + 4);
}

const marker = '    } catch (error) {' + NL + '      if ((action === "payment-create" || action === "payment-lookup")';
const a = source.lastIndexOf(marker);
assert.ok(a > 0);
const start = source.indexOf(NL, a) + 1;
const end = source.indexOf(NL + '    } finally {', start);
assert.ok(end > start);
const outerBody = source.slice(start, end);
const wrapper = 'function consume(action, error, toast) {' + NL + outerBody + NL + '}';

const i18nBox = { window: {} };
i18nBox.window.window = i18nBox.window;
i18nBox.globalThis = i18nBox.window;
vm.createContext(i18nBox);
vm.runInContext(fs.readFileSync(i18nPath, 'utf8'), i18nBox);
const realI18n = i18nBox.window.TOANAASI18n || i18nBox.TOANAASI18n;

function createContextForLocale(locale) {
  const ctx = {
    window: { TOANAASI18n: { t: (k, p) => realI18n.t(k, p, locale) } },
    console,
    merge: () => {},
    FEATURE_BY_PATH: {},
    priorFeatureFlow: () => ({}),
    base: () => ({ pageStates: {}, featureFlows: {} })
  };
  ctx.window.window = ctx.window;
  ctx.globalThis = ctx.window;
  vm.createContext(ctx);
  for (const name of ['musicSfxEditorialFeedbackText', 'musicDirectionPresetPayload', 'sfxCueSheetPayload', 'musicSfxEditorialErrorText']) {
    const code = extractFn(name);
    if (code) vm.runInContext(code, ctx);
  }
  vm.runInContext(wrapper, ctx);
  return ctx;
}

test('nonMusic consumer fallback preserves raw message on baseline and new', () => {
  const ctx = createContextForLocale('vi');
  let toasted;
  ctx.consume('other-action', new Error('fallback preserved'), (msg) => { toasted = msg; });
  assert.strictEqual(toasted, 'fallback preserved');
});

test('helper contract: existence and nonMusic null without reading error getters', () => {
  const ctx = createContextForLocale('vi');
  assert.strictEqual(typeof ctx.musicSfxEditorialErrorText, 'function');
  const throwingError = {
    get message() { throw new Error('getter leak message'); },
    get payload() { throw new Error('getter leak payload'); }
  };
  assert.strictEqual(ctx.musicSfxEditorialErrorText('other-action', throwingError), null);
});

const errorCases = [
  {
    action: 'music-direction-preset-compose',
    makeError: (ctx) => {
      try { ctx.musicDirectionPresetPayload({ description: 'x', language: 'vi', web_preset_id: 'p1' }); }
      catch (e) { assert.strictEqual(e.message, 'Brief âm nhạc cần từ 2 đến 500 ký tự hợp lệ.'); return e; }
    },
    exp: { vi: 'Mô tả cần từ 2 đến 500 ký tự.', en: 'The description must contain 2 to 500 characters.', zh: '描述须为2至500个字符。' }
  },
  {
    action: 'music-direction-preset-compose',
    makeError: (ctx) => {
      try { ctx.musicDirectionPresetPayload({ invalid: 1 }); }
      catch (e) { assert.strictEqual(e.message, 'Music Directions chỉ nhận brief, ngôn ngữ và một preset Web.'); return e; }
    },
    exp: { vi: 'Kiểm tra mô tả và các lựa chọn trước khi gửi.', en: 'Check the description and your selections before submitting.', zh: '提交前请检查描述和选项。' }
  },
  {
    action: 'sfx-cue-sheet-compose',
    makeError: (ctx) => {
      try { ctx.sfxCueSheetPayload({ description: 'x', language: 'vi', web_sfx_preset_id: 'p1' }); }
      catch (e) { assert.strictEqual(e.message, 'Brief SFX cần từ 2 đến 500 ký tự hợp lệ.'); return e; }
    },
    exp: { vi: 'Mô tả cần từ 2 đến 500 ký tự.', en: 'The description must contain 2 to 500 characters.', zh: '描述须为2至500个字符。' }
  },
  { action: 'music-direction-preset-compose', makeError: () => new Error('Ngôn ngữ hoặc preset Web không hợp lệ. Hãy chọn lại từ các lựa chọn trong trang.'), exp: { vi: 'Chọn một hướng và ngôn ngữ có sẵn trong biểu mẫu.', en: 'Select a direction and a language available in the form.', zh: '请选择表单中的方向和语言。' } },
  { action: 'sfx-cue-sheet-compose', makeError: () => new Error('Ngôn ngữ hoặc preset SFX Web không hợp lệ. Hãy chọn lại từ các lựa chọn trong trang.'), exp: { vi: 'Chọn một loại hiệu ứng và ngôn ngữ có sẵn trong biểu mẫu.', en: 'Select an effect type and a language available in the form.', zh: '请选择表单中的音效类型和语言。' } },
  { action: 'music-direction-preset-compose', makeError: () => new Error('Music Directions chỉ nhận thao tác từ màn hình Music Directions đang mở.'), exp: { vi: 'Mở lại trang Hướng âm nhạc trước khi gửi.', en: 'Reopen Music Directions before submitting.', zh: '请重新打开音乐方向页面后再提交。' } },
  { action: 'sfx-cue-sheet-compose', makeError: () => new Error('Cần signed Web session, CSRF và Music Workspace đang sẵn sàng để lập SFX Cue Sheet.'), exp: { vi: 'Chức năng lập bảng hiệu ứng hiện chưa sẵn sàng. Vui lòng quay lại sau.', en: 'The SFX Cue Sheet is not available right now. Please come back later.', zh: '音效提示表暂不可用，请稍后再来。' } },
  { action: 'music-direction-preset-compose', makeError: () => new Error('Music Prompt Composer không nhận URL hoặc scheme tệp trong mô tả direction.'), exp: { vi: 'Viết mô tả bằng lời, không nhập liên kết, mã lệnh hoặc mã tệp.', en: 'Write a plain-language description without links, commands or file references.', zh: '请用文字描述，不要输入链接、命令或文件引用。' } },
  { action: 'music-direction-preset-compose', makeError: () => new Error('Audio Library không nhận API key, khóa riêng, token, mật khẩu, OTP/CVV hoặc số thẻ.'), exp: { vi: 'Xóa mật khẩu, mã xác thực, khóa truy cập và thông tin thanh toán khỏi mô tả.', en: 'Remove passwords, verification codes, access keys and payment details from the description.', zh: '请移除描述中的密码、验证码、访问密钥和付款信息。' } },
  { action: 'sfx-cue-sheet-compose', makeError: () => new Error('Máy chủ chưa trả SFX Cue Sheet Web-native an toàn và khớp brief hiện tại.'), exp: { vi: 'Chưa nhận được kết quả hợp lệ cho nội dung này. Hãy gửi lại.', en: 'No valid result was received for this brief. Please submit again.', zh: '未收到此摘要的有效结果，请重新提交。' } },
  { action: 'music-direction-preset-compose', makeError: () => Object.assign(new Error('Auth'), { status: 401 }), exp: { vi: 'Phiên làm việc không hợp lệ hoặc chưa có quyền. Hãy đăng nhập lại.', en: 'Your session is invalid or lacks access. Please sign in again.', zh: '会话无效或没有访问权限，请重新登录。' } },
  { action: 'music-direction-preset-compose', makeError: () => ({ payload: { message: 'SQL injection at https://secret.internal' } }), exp: { vi: 'Chưa thể lập hướng âm nhạc. Kiểm tra nội dung và kết nối rồi gửi lại.', en: 'Music directions could not be created. Check the brief and connection, then submit again.', zh: '无法创建音乐方向，请检查摘要和连接后重新提交。' } },
  { action: 'music-direction-preset-compose', makeError: () => null, exp: { vi: 'Chưa thể lập hướng âm nhạc. Kiểm tra nội dung và kết nối rồi gửi lại.', en: 'Music directions could not be created. Check the brief and connection, then submit again.', zh: '无法创建音乐方向，请检查摘要和连接后重新提交。' } }
];

test('real error presentation and consumer across locales (VI/EN/ZH)', () => {
  for (const locale of ['vi', 'en', 'zh']) {
    const ctx = createContextForLocale(locale);
    for (const c of errorCases) {
      const err = c.makeError(ctx);
      let toasted;
      ctx.consume(c.action, err, (msg) => { toasted = msg; });
      assert.strictEqual(toasted, c.exp[locale]);
    }
  }
});

test('unknown errors and server payloads never leak raw copy or infer auth from envelope status', () => {
  const retry = {
    music: {vi:'Chưa thể lập hướng âm nhạc. Kiểm tra nội dung và kết nối rồi gửi lại.',en:'Music directions could not be created. Check the brief and connection, then submit again.',zh:'无法创建音乐方向，请检查摘要和连接后重新提交。'},
    sfx: {vi:'Chưa thể lập bảng hiệu ứng. Kiểm tra nội dung và kết nối rồi gửi lại.',en:'The SFX cue sheet could not be created. Check the brief and connection, then submit again.',zh:'无法创建音效提示表，请检查摘要和连接后重新提交。'}
  };
  const auth = {vi:'Phiên làm việc không hợp lệ hoặc chưa có quyền. Hãy đăng nhập lại.',en:'Your session is invalid or lacks access. Please sign in again.',zh:'会话无效或没有访问权限，请重新登录。'};
  const unknown = [null,undefined,'raw primitive',0,{},new Error('Failed to fetch'),new Error('constructor'),new Error('__proto__'),new Error('toString'),{status:'401'},
    {payload:{status:401,message:'RAW_SERVER_MARKER'}},
    {message:'Brief âm nhạc cần từ 2 đến 500 ký tự hợp lệ.',payload:{message:'RAW_SERVER_MARKER'}}];
  for(const locale of ['vi','en','zh'])for(const [tool,action] of [['music','music-direction-preset-compose'],['sfx','sfx-cue-sheet-compose']]){
    const ctx=createContextForLocale(locale);
    for(const error of unknown){let observed;ctx.consume(action,error,msg=>observed=msg);assert.strictEqual(observed,retry[tool][locale],`${tool}/${locale}/${String(error)}`);}
    for(const status of [401,403]){let observed;ctx.consume(action,{status,payload:{message:'RAW_SERVER_MARKER'}},msg=>observed=msg);assert.strictEqual(observed,auth[locale]);}
  }
});

test('nonMusic consumer preserves payload-first, local and generic fallback', () => {
  const ctx=createContextForLocale('zh');
  for(const [error,want] of [[{payload:{message:'original payload'},message:'local'},'original payload'],[new Error('original local'),'original local'],[{},'Yêu cầu chưa được xác nhận.']]){
    let observed;ctx.consume('unrelated-action',error,msg=>observed=msg);assert.strictEqual(observed,want);
  }
});

test('inline failure catches set localized retry status in 3 locales', async () => {
  const idxMusic = source.indexOf('      if (action === "music-direction-preset-compose") {');
  const idxSfx = source.indexOf('      if (action === "sfx-cue-sheet-compose") {');
  const idxPrompt = source.indexOf('      if (action === "music-prompt-compose") {');
  assert.ok(idxMusic > 0 && idxSfx > idxMusic && idxPrompt > idxSfx);
  const mBlock = source.slice(idxMusic, idxSfx);
  const sBlock = source.slice(idxSfx, idxPrompt);
  const runCode = 'async function runInline(action, route, fields) {' + NL + mBlock + NL + sBlock + NL + '}';

  const expRetry = {
    music: {
      vi: 'Chưa thể lập hướng âm nhạc. Kiểm tra nội dung và kết nối rồi gửi lại.',
      en: 'Music directions could not be created. Check the brief and connection, then submit again.',
      zh: '无法创建音乐方向，请检查摘要和连接后重新提交。'
    },
    sfx: {
      vi: 'Chưa thể lập bảng hiệu ứng. Kiểm tra nội dung và kết nối rồi gửi lại.',
      en: 'The SFX cue sheet could not be created. Check the brief and connection, then submit again.',
      zh: '无法创建音效提示表，请检查摘要和连接后重新提交。'
    }
  };

  const mRoute = '/media-workspace/music-directions';
  const sRoute = '/media-workspace/sfx-cue-sheet';

  for (const locale of ['vi', 'en', 'zh']) {
    const ctx = createContextForLocale(locale);
    let lastMusic = '', lastSfx = '', mergeCalled = false, toastCalled = false;
    ctx.musicDirectionPresetComposeRequestEpoch = 0;
    ctx.musicDirectionPresetComposePendingRequestEpoch = 0;
    ctx.sfxCueSheetComposeRequestEpoch = 0;
    ctx.sfxCueSheetComposePendingRequestEpoch = 0;
    ctx.currentPortalPath = () => ctx._activeRoute;
    ctx.base = () => ({ capabilities: { 'music-direction-preset-compose': true, 'sfx-cue-sheet-compose': true }, pageStates: {} });
    ctx.musicDirectionPresetPayload = (f) => f;
    ctx.sfxCueSheetPayload = (f) => f;
    ctx.musicDirectionPresetGuardBoundaryIsSafe = () => false;
    ctx.sfxCueSheetBoundaryIsSafe = () => false;
    const calls = [], busy = [];
    ctx.api = async (url, options) => { calls.push({ url, options }); throw new Error('transport throw'); };
    ctx.setActionBusy = (action, route, value) => busy.push(value);
    ctx.merge = () => { mergeCalled = true; };
    ctx.toast = () => { toastCalled = true; };
    ctx.setMusicDirectionPresetSubmissionStatus = (s) => { lastMusic = s; };
    ctx.setSfxCueSheetSubmissionStatus = (s) => { lastSfx = s; };

    vm.runInContext(runCode, ctx);

    ctx._activeRoute = mRoute;
    await assert.rejects(ctx.runInline('music-direction-preset-compose', mRoute, {}), /transport throw/);
    assert.strictEqual(calls.length, 1);
    assert.strictEqual(calls[0].url, '/media-workspace/tools/music-directions/compose');
    assert.deepEqual(busy, [true, false]);
    assert.strictEqual(lastMusic, expRetry.music[locale]);
    assert.strictEqual(mergeCalled, false);
    assert.strictEqual(toastCalled, false);

    ctx._activeRoute = sRoute;
    busy.length = 0;
    await assert.rejects(ctx.runInline('sfx-cue-sheet-compose', sRoute, {}), /transport throw/);
    assert.strictEqual(calls.length, 2);
    assert.strictEqual(calls[1].url, '/media-workspace/tools/sfx-cue-sheet/compose');
    assert.deepEqual(busy, [true, false]);
    assert.strictEqual(lastSfx, expRetry.sfx[locale]);
    assert.strictEqual(mergeCalled, false);
    assert.strictEqual(toastCalled, false);
  }
});
