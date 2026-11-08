# Phiên kiểm thử locale — 08/11/2026

SESSION_ID=LOCALE-CAMPAIGN-20261108
STATUS=READY_FOR_CI_HANDOFF
BASE_SHA=3ff8644fb3f43ec6813090b2a11a85a8b81e93e3
SOURCE_MANIFEST=6304e085b8df780e130841c5d2ba28f3de47b4efc5bf2bfda12119be6de0ba03
PRODUCTION_LIVE=NOT_TESTED

Theo dõi duy nhất của đợt: [Issue #689](https://github.com/manhtoangreensky-wq/toan-aas-standalone/issues/689).

## Phạm vi

Chỉ fixed chrome VI/EN/ZH, tiêu đề lần tải đầu và cỡ chữ mobile của công cụ âm
nhạc; giữ mọi customer/server text, field/control/option scalar, ID, route/action,
quyền, normalizer và giới hạn. Không sửa backend/auth/schema/provider/ví/Bot.

[Receipt phát hành](../docs/reports/locale-release-20261108.md) là bảng bằng chứng
hiện tại duy nhất. Các tài liệu lịch sử không dùng để gán PASS cho nguồn mới.

## Kết quả hiện tại

| Cổng | Kết quả |
|---|---|
| FullNode, catalogue chuẩn khóa SHA |1.871/1.871,0skip|
| Locale |418/418|
| Renderer dedicated-audio và hồi quy thư viện |36/36|
| Chọn mẫu/giữ nháp/trạng thái nút |30/30|
| HTMLResponse lần tải đầu |39/39|
| Python portal/music/i18n/navigation target |44/44|
| Chrome3tool×3locale×2theme×3viewport |54/54;0overflow;0page error|
| Input mobile |font tối thiểu16px,cao45px;desktop composer15px|
| Review locale |0Critical,0Important|

Xem [manifest](../reports/ui-qa/locale-20261108/source-manifest.json),
[bản trích Chrome](../reports/ui-qa/locale-20261108/dedicated-audio-browser.json)
và [Node summary](../reports/ui-qa/locale-20261108/node-full-summary.json).

## Chạy lại

Dùng các lệnh repository-owned trong [hướng dẫn Tester](HUONG-DAN-TESTER.md).
FullNode cần catalogue tại SHA83a994aea6fb253ee9e64fcfc845d4c31aa2934d, theo
checkout hiện hữu trong .github/workflows/webapp-quality.yml. Không dựng
catalogue giả hoặc bỏ test khi thiếu dependency.

Rawtraces, log, mã phiên agent, máy local và script điều phối không xuất bản.
Bản trích chỉ chứa route/locale/theme/viewport, nhãn hiển thị và số đo giao diện,
không có session/login/API response hay dữ liệu khách. Nó không thay thế chạy
lại browser/CI trên commit mới.

## Cổng còn mở

- Exact-commit CI và provenance theo workflow.
- Merge/deploy record, runtime SHA/service health và signed production UI riêng.
- Rà checklist còn lại trước khi tuyên bố toàn goal hoàn tất.

Ma trận456ca authenticated và30ca responsive của nguồn trước chỉ là lịch sử,
không dùng làm exact-source hoặc LIVE của phiên này.
