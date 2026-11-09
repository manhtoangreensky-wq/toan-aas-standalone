# Video Studio — hoàn tất chữ tiếng Việt cố định — 09/11/2026

BASE_SHA=2c18607169dc0ed9d55d934741a6e26f730c9b88
STATUS=LOCAL_VERIFIED_PENDING_CI_DEPLOY
SCOPE=static/portal/portal-i18n.js, static/portal/portal.js

## Kết quả

- RED ban đầu: 23 ca renderer thật, 12 comparator bảo toàn đạt, 11 literal VI còn lẫn media/Workspace/Web/URL/CSRF/metadata.
- Candidate: 23/23 đạt; 4 trạng thái (`ready-empty`, `ready-populated`, `read-only`, `guarded`) × VI/EN/ZH.
- Raw bootstrap không đổi; dữ liệu khách/máy chủ, UUID, project reference, format, language, aspect ratio, duration, revision, route, action, capability và disabled state giữ nguyên.
- EN/ZH không đổi; không dịch thương hiệu, tên người dùng hoặc dữ liệu trả về máy chủ.
- `node --check` hai file đạt; `git diff --check` đạt.

## Native/layout limitation

Đã chuẩn bị QA 18 cấu hình 320/414/1024 × VI/EN/ZH × sáng/tối. Harness native đầu tiên bị timeout vì fixture/login flow và không tạo được kết quả tin cậy; không dùng timeout làm PASS/FAIL UI. RenderChild/contract là bằng chứng hiện có, còn native layout phải chạy lại bằng runner đã sửa fixture trước khi đóng hẳn mục responsive này.

## Motion opt-in cùng đợt

Markup thêm đúng một style không thực thi ngay trước script parser-blocking `portal-theme.js` ở template chuẩn và fallback literal. Diagnostic lặp: 3/3 normal baseline còn `InvalidStateError`, 3/3 proposed không còn; reduced baseline/proposed 0 lỗi. 8 ca đều tới Studio mới/nonblank/không tràn/scroll0; screencast ACK muộn ở 2 ca được giữ là giới hạn transport, không che lỗi. Fallback native runtime chưa được claim.

PROVIDER_CALLS=0
WALLET_MUTATIONS=0
ENV_MUTATIONS=0
PRODUCTION_DATA_MUTATIONS=0
LIVE_PASS=NOT_TESTED

