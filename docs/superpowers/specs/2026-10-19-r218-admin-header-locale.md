# R218 — Q0-ZH-LOCALE-PICKER

## Kết quả cần đạt

Bộ chọn ngôn ngữ ở đầu Admin phải có đủ Việt/Anh/Trung và chọn đúng locale của hồ sơ.
Giữ nguyên form/action/route và cơ chế lưu ngôn ngữ hiện hành. Hoàn tất lát này rồi
tiếp tục AD-02-PRICING-LOCALE và ma trận role/module; motion cuối.

## Hiện trạng đã đo

- Worktree `C:/Users/toann/Documents/Codex/_webapp-r218-voice`.
- HEAD detached `1730ea41ffda53e6bcd068f45a49c8c9f6949929`.
- Shared state locale và mobile cards đã nghiệm thu local; phải bảo toàn mọi diff đó.
- `portal.js:11048` chỉ render option vi/en. `interfaceLocaleFor()` trả zh đúng; khi
  không có option zh, trình duyệt chọn vi đầu tiên. Đây là lỗi source đã tái hiện,
  không phải phỏng đoán từ ảnh fixture.
- Browser RED: rendererLocale zh nhưng select.value vi, exit 1 với `'vi' !== 'zh'`.
  Command do Codex chạy: `node ../qa/r218-voice-inventory/admin-data-reviewed-probe.cjs --locale --header-locale --baseline`.
  Evidence: `../qa/r218-voice-inventory/admin-header-locale-red.json` và ảnh failure.
- Hỗ trợ zh đã có ở integration.js INTERFACE_LOCALES:1409 và copyfast_auth.py:86;
  catalogue `locale.zh` đã có đủ VI/EN/ZH. Không cần sửa API/capability hoặc tạo chuỗi mới.

## Contract / phạm vi khóa

- COMPLEX vì cùng shared header; một worker, một spec.
- Allowed source duy nhất: `static/portal/portal.js`, đúng dòng template select
  `id="portal-admin-header-locale"` trong `renderHeader` khoảng11043–11051.
- Không sửa helper, chữ ký hàm, form/action/route, auth/session/CSRF/profile API,
  capability/RBAC, palette/CSS, i18n, state labels, tests hoặc mọi file khác.
- Portal.js trước lát này SHA256
  `c667988ae25dd790bcfe2786b8ebf57062c05e763c9d1c4fe97ce8f639312e0a`.
- Protected i18n SHA256 `83b93bc594cf55fbdde96d0cfe1f08abc46e84dd1fbb2dafcc387444c981c0f9`;
  shared-state test `efa2d2685e855a9d8b2d15ce5e6f02a5d24e55b327e1d3553e90a716f94a12cc`.
- Không shell/terminal/chạy lệnh qua UI; Codex chạy mọi verify. Không browser/network,
  Git/package/ENV/DB/provider/wallet/production/deploy hoặc Open IDE/trust prompt.

## Sửa chính xác một đoạn

Trước:

```js
          <select id="portal-admin-header-locale" name="locale" aria-label="${safeText(uiText("adminShell.language", "Ngôn ngữ"))}">${localeOption("vi", uiText("locale.vi", "Tiếng Việt"))}${localeOption("en", uiText("locale.en", "English"))}</select>
```

Sau:

```js
          <select id="portal-admin-header-locale" name="locale" aria-label="${safeText(uiText("adminShell.language", "Ngôn ngữ"))}">${localeOption("vi", uiText("locale.vi", "Tiếng Việt"))}${localeOption("en", uiText("locale.en", "English"))}${localeOption("zh", uiText("locale.zh", "Tiếng Trung"))}</select>
```

Không format hoặc rewrite toàn file. Không thêm renderer/catalogue thứ hai.

## Acceptance / evidence

1. Đúng ba giá trị option vi/en/zh, mỗi giá trị một lần; nhãn dùng catalogue theo locale.
2. Chọn đúng locale vi/en/zh đang hiển thị; không fallback select sang vi khi renderer zh.
3. Đổi lựa chọn cục bộ, phục hồi và focus hoạt động; không submit profile trong QA.
4. `data-portal-action=update-interface-locale` và `data-portal-route=/admin` không đổi.
5. Chỉ một dòng source thay đổi so với candidate local đã khóa; palette, state labels,
   Customer, Python/integration/workflow và các test đang có được giữ nguyên.
6. Browser12/12 VI/EN/ZH × light/dark ×390/1440; state/data-card regressions vẫn đạt,
   errors/write/external/unknown0. Full Node713/713, JS syntax/diff-check đạt.

Không thêm unit test chỉ lặp lại một dòng template; browser gate kiểm hành vi đã được
mở rộng trước BUILD và có RED thật. QA là fixture GET-only, không chứng minh backend/LIVE.

## Bàn giao

Worker ghi `_giao-viec/BAO-CAO-03-Q0-ZH-LOCALE-PICKER.md` gồm SPEC_ID, HANDOFF_ROUND,
file/dòng sửa, AC, verify NOT_RUN, điều không kiểm và COMMIT/PUSH/MERGE/DEPLOY=NO; rồi dừng.
Nếu source khác nội dung trước hoặc cần vượt allowlist thì báo BLOCKED. Không tự ACCEPTED.

## Nghiệm thu 19/10/2026

ACCEPTED_LOCAL_UI_CI_PENDING. Antigravity round1 sửa đúng một dòng; comparator đảo chuỗi
thêm khôi phục hash trước task. Codex full Node713/713, syntax/diff-check exit0;
browser12/12, đủ ba options/selected đúng/local change/focus/form, state/data-card
regression giữ nguyên, errors/write/external/unknown0. Artifact `admin-header-locale.json`
SHA256 `f099e8e7111316ab9f72e1277c8b24ef1be35d74f3bf1b3ead893d3831900fd1`.
CI/deploy/LIVE vẫn mở; không đóng các lỗi copy module ZH khác.
