# Locale release unit — 08/11/2026

## Phạm vi đã sửa

Theo dõi: [Issue #689](https://github.com/manhtoangreensky-wq/toan-aas-standalone/issues/689).

- Dịch fixed chrome VI/EN/ZH của bảng kế hoạch, account, thư viện và ba công cụ âm nhạc; sửa tiêu đề server lần tải đầu.
- Giữ nguyên nội dung khách/máy chủ, ID, route/action, scalar option, quyền, normalizer và giới hạn.
- Không animate ancestor main của dashboard; chỉ giữ reveal các lớp quyết định.
- Mobile composer: chữ ô nhập16px, cao tối thiểu44px; desktop vẫn15px.
- Không sửa Bot, route-engine, backend/API/schema, auth authority, provider, ví/PayOS, ENV hoặc dữ liệu production.

Đây là một đơn vị sửa đã có bằng chứng; không phải tuyên bố toàn bộ UI/UX của mọi route đã hoàn tất hoặc engine/provider đã chạy thật.

## Nguồn và bằng chứng hiện tại

BASE: `3ff8644fb3f43ec6813090b2a11a85a8b81e93e3`.
Nền công bố GitHub: `2038b595348f3d5609a56827e3c2141eb53a4a24`; đã đối chiếu
hai source tree bằng nhau trước khi đặt riêng đơn vị sửa mới lên nền này.
Manifest9file runtime/UI: `6304e085b8df780e130841c5d2ba28f3de47b4efc5bf2bfda12119be6de0ba03` — đây là fingerprint nội dung, không phải commit SHA.
Bản chứng cứ có thể trỏ đến commit nguồn cha khi CI tạo synthetic merge commit; Git provenance được kiểm riêng.
Hash trong manifest dùng văn bản UTF-8/LF đúng Git blob, không phụ thuộc CRLF ở máy Windows.

| Cổng | Kết quả | Lệnh/nguồn |
|---|---|---|
| Toàn bộ Node, với catalogue chuẩn |1.871 đạt /0lỗi /0bỏ qua| `node --test tests/*.test.mjs` |
| Locale |418/418| `node --test tests/*locale*.test.mjs` |
| Dedicated audio + hồi quy thư viện |36/36| dedicated-audio-fixed-chrome-locale + library-account-locale-render-regression |
| Chọn mẫu/giữ nháp/chốt nút |30/30| music-sfx-interaction-feedback |
| HTMLResponse lần tải đầu |39/39| `python -m pytest -q tests/test_library_shell_locale_runtime.py` |
| Python hợp đồng portal/music/i18n/navigation |44/44| music_directions_portal_contracts, sfx_cue_sheet_portal_contracts, portal_i18n_bundle_contracts, portal_navigation_ux_contracts |
| Chrome3tool×3locale×2theme×3viewport |54/54| Bản trích JSON đã rà thông tin công bố |
| Mobile input |font tối thiểu16px, chiều cao tối thiểu45px| Cùng54records; desktop composer15px |
| Dashboard normal/reduced motion |0main-enter call,0page error| Local real-Chrome QA; rawtrace không xuất bản |
| Syntax/compile/diff |đạt| node --check, py_compile copyfast_pages.py, git diff --check |

Catalogue đối chiếu khóa tại commit `83a994aea6fb253ee9e64fcfc845d4c31aa2934d`.
Checkout và BOT_ROOT/BOT_AUTHORITY_SHA theo bước hiện hữu trong
[`webapp-quality.yml`](../../.github/workflows/webapp-quality.yml); đây là nguồn
đọc cho contract tests, không chạy hoặc sửa Bot. Hai tệp catalogue được lấy từ
đúng commit, không tạo fixture giả hoặc bỏ bài kiểm.

Bằng chứng portable:

- [Source manifest](../../reports/ui-qa/locale-20261108/source-manifest.json)
- [Chrome54records](../../reports/ui-qa/locale-20261108/dedicated-audio-browser.json)
- [FullNode summary](../../reports/ui-qa/locale-20261108/node-full-summary.json)
- [Phiên Tester](../../KIEM-THU/PHIEN-LOCALE-20261108.md)
- [Nguồn ca kiểm thử](../../KIEM-THU/DANH-SACH-CASE.md)

Rawlog, mã phiên nội bộ, máy local, bootstrap/API/login responses và dữ liệu người
dùng không thuộc gói công bố. Các tên/nội dung fixture trong test là dữ liệu
tổng hợp, không phải dữ liệu khách.

## Review và sai lệch đã xử lý

Review locale C0/I0 sau khi sửa first-paint và tool boundaries. H1 có một thay
đổi sai ký tự Trung; đã bị từ chối, sửa đúng ở H2 và chỉ áp sau kiểm tra exact
anchors. Các field contracts/sourceMatchesComposer và EN/ZH hiện hữu giữ nguyên.

Một Python test từng đòi khóa mobile.home không còn được render. Test hiện kiểm
đúng5khóa studio/publishing/projects/wallet/account trong renderer thật, không
khôi phục hằng số chết để làm xanh. Các trạng thái/nút/giữ nháp vẫn có ca chạy.

Sáu static contract cũ ngoài nhóm CI mục tiêu đã tái hiện tương đương trên BASE;
không sửa source bằng comment hoặc literal giả để che chúng. Kết quả này không
được gọi là full pytest PASS.

## Checklist theo thứ tự

- [x] Scope/source review và bảo vệ các luồng không liên quan.
- [x] Locale, form/result, first-paint và mobile font có RED→GREEN.
- [x] FullNode với catalogue chuẩn, các Python target và browser có bằng chứng.
- [x] Tài liệu vận hành/đối chiếu chức năng gốc/phiên Tester đã cập nhật.
- [ ] Exact-commit CI/provenance qua toàn bộ cổng bắt buộc.
- [ ] Merge và deployment có record riêng sau CI.
- [ ] Runtime SHA/service health và signed production UI được đối chiếu sau phát hành.
- [ ] Rà phần còn lại của checklist mẹ trước khi tuyên bố goal toàn diện đã hoàn tất.

## Trạng thái production

`MERGED != DEPLOYED != LIVE`. Các kết quả ở đây là local/QA cô lập.
Ma trận authenticated456/456 và responsive30/30 của nguồn trước là lịch sử, không
gán lại cho nguồn này. Không có provider trả phí, giao dịch ví hoặc dữ liệu
production nào được dùng để làm kiểm thử thực tế.

VPS đã được đọc trạng thái ở đầu đợt: Web/Bot/nginx active, Web runtime ở
`2038b595348f3d5609a56827e3c2141eb53a4a24`. Đó không phải nguồn mới này;
CI/deploy/runtime/LIVE mới phải có bằng chứng riêng.
