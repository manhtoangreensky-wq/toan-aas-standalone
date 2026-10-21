# R218 — Music review và sửa provenance trước push

Đang đọc và áp dụng skill owner-governed-codex cho task này.
BASE_SHA=4e7943e17fecf63638457f6aaf1ef3854a92043e; PR654;
branch webapp-r217-subdub-ui-r218; không merge/deploy.

## Review code / nghiệp vụ

Ba lỗi Important được tái hiện độc lập: giá Music bị ẩn, report-only confirm
bị early return và nút EN/ZH còn VI. Sửa bằng renderer Music riêng; giữ
actions/DTO/receipt/progress/engine và khôi phục nguyên generic renderer.
`TAI-LIEU/01-NGHIEP-VU-VAN-HANH.md` và `02-CHUC-NANG-GOC-VA-HIEN-TAI.md`
đã có đính chính ưu tiên về thực trạng, không tiếp tục tuyên bố đủ sản phẩm.

## Đối chiếu yêu cầu và evidence

13/13 test tích hợp thực; independent review18/18; full Node826/826.
Browser18 cấu hình xác minh locale hồ sơ thật, apply/toast/giá0/unknown/edit/
revert/report-only18; idle expiry3 giữ cùng form. Có AX/ảnh sau animation,
source hashes và errors/network tại `R218-MUSIC-RUNTIME-REVIEW-QA-20261021.json`.
Đây là presentation fixture trên app QA, không gọi engine hoặc phát nhạc thật.

9 báo cáo cũ được reclassify: broad smoke chưa chứng minh locale/interaction/
AX/motion. Không thay/xóa con số lịch sử để làm xanh; phần thiếu trở lại ledger.

## Tester workspace

Dùng PR654 hiện hữu, không tạo issue/project cạnh tranh. Case source có
MREV-01..04; hướng dẫn yêu cầu locale hồ sơ, real envelopes, không fake draft;
metadata dùng portable LF hash được đo lại sau chỉnh tài liệu. Template issue
giữ nguyên. Không suy ra remote Project đã ready từ file JSON lịch sử.

Kiểm chứng metadata + i18n bundle/locale + motion source contracts ngày21/10:
`python -m pytest -q tests/test_p0_05d_tester_workspace.py::test_readiness_json_has_explicit_truth_and_file_metadata tests/test_portal_i18n_bundle_contracts.py tests/test_portal_i18n_locale_contracts.py tests/test_motion_webapp_surfaces_live_reopen_contracts.py --tb=short`
→ exit0, 29 passed, 2 cảnh báo deprecated. Phiên sandbox70666 bị ngắt khi
không tiến triển; lần chạy lại ngoài sandbox mới là bằng chứng. Server QA
exec54976 đã dừng graceful exit0 và dọn DB tạm. Không còn server của checkpoint.

## Failure nền / kỹ thuật ngoài scope

`test_storyboard_shortcut_uses_the_native_text_composer_while_image_transform_keeps_its_contract`
fail cùng assertion literal featurePage('/image/transform') trên cleanBASE và
candidate. Không sửa route/engine/test cũ để che lỗi. POSIX0600 trên Windows
vẫn là comparator riêng, phải báo khác với CI Ubuntu.

## CI provenance

Run39473056685 fail fingerprint trước test; không phải bằng chứng UI fail/pass.
Refresh/verify ở clean4e7943e đã khớp cfc6d46e1900. Sau code correction phải
commit source, cập nhật clean checkout, refresh hai JSON provenance và verify
lần cuối trước push. Không bỏ gate/đổi CI/Bot evidence; chỉ push khi đủ output.

DEPLOY=NO; LIVE_PASS=NOT_TESTED; provider/feature submits=0;
wallet/production/ENV/schema/auth/Bot mutations=0.
