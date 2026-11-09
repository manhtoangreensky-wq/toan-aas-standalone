# Biểu mẫu kế hoạch video — Việt hóa và opt-in chuyển trang — 09/11/2026

BASE_SHA=2c18607169dc0ed9d55d934741a6e26f730c9b88
STATUS=LOCAL_VERIFIED_PENDING_CI_DEPLOY
LOCALE_SCOPE=static/portal/portal-i18n.js, static/portal/portal.js
OPTIN_SCOPE=templates/portal_shell.html, copyfast_pages.py:_fallback_template
PROVENANCE=reports/migration/preflight.json

## Kết quả

- RED ban đầu: 23 ca renderer thật, 12 comparator bảo toàn đạt, 11 literal VI còn lẫn media/Workspace/Web/URL/CSRF/metadata.
- Renderer candidate: 23/23 đạt, gồm 11 literal VI và 12 comparator; 4 trạng thái (`ready-empty`, `ready-populated`, `read-only`, `guarded`) × VI/EN/ZH. Đây không phải whole-app locale PASS.
- Raw bootstrap không đổi; dữ liệu khách/máy chủ, UUID, project reference, format, language, aspect ratio, duration, revision, route, action, capability và disabled state giữ nguyên.
- EN/ZH không đổi; không dịch thương hiệu, tên người dùng hoặc dữ liệu trả về máy chủ.
- `node --check` hai file đạt; `git diff --check` đạt.

## Native/layout limitation

QA native R4 đạt 18/18 cấu hình 320/414/1024 × VI/EN/ZH × sáng/tối. Mỗi ca giữ route/locale/theme, 10 ô chỉnh sửa, không page/console/overflow/external/write lỗi; mobile editable fields đạt16px, desktop giữ15px, target không vi phạm. Runner cũ thiếu bước đăng ký fixture và không đóng browser trong nhánh lỗi; hai timeout được phân loại là harness failure, không phải app PASS/FAIL.

## Motion opt-in cùng đợt

Markup thêm đúng một style không thực thi ngay trước script parser-blocking `portal-theme.js` ở template chuẩn và fallback literal. Diagnostic lặp trước triển khai: 3/3 normal baseline còn `InvalidStateError`, 3/3 proposed không còn; reduced baseline/proposed 0 lỗi. 8 ca đều tới Studio mới/nonblank/không tràn/scroll0; screencast ACK muộn ở 2 ca được giữ là giới hạn transport, không che lỗi. Diagnostic này chưa phải native gate trên bốn tệp đã commit.

Permanent gate `tests/test_navigation_optin_markup_regression.py`: candidate 8/8 đạt; source BASE đọc vào RAM có 3 đạt/5 lỗi do thiếu early opt-in. AST/literal_eval và HTMLParser kiểm HTML thường/fallback, vị trí trước theme script, chỉ hai descriptor CSS, JSON bootstrap inert và CSP không bị nới. Không import app/config/ENV cho gate này. Fallback native đầy đủ chưa được claim.

Source review: tái dựng hai tệp JS từ BASE + đúng 11 giá trị VI/12 fallback của worker cho kết quả byte-identical với candidate. Mọi EN/ZH, guard, route, dữ liệu, focus counter/helper ngoài các literal đều giữ nguyên. Actual-source navigation R3 đạt8/8 (6 normal có transition,2 reduced không transition), no page/unhandled/overflow, scroll0. Permanent markup/font gates và full Node/Python regression đã chạy; release còn chờ CI/PR/deploy/runtime.

PROVIDER_CALLS=0
WALLET_MUTATIONS=0
ENV_MUTATIONS=0
PRODUCTION_DATA_MUTATIONS=0
LIVE_PASS=NOT_TESTED
