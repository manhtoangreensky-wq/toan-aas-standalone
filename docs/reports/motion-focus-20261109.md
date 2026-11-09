# Khôi phục focus đúng lượt dựng — 09/11/2026

BASE_SHA=a3ebcadfed27d5038a78d5afc757b4bf339ba113
STATUS=LOCAL_VERIFIED_PENDING_CI_DEPLOY
PROVENANCE=reports/migration/preflight.json
TRACKING=https://github.com/manhtoangreensky-wq/toan-aas-standalone/issues/689

## Hành vi

MOTION-NOV09-FOCUS-CONTINUATION: callback cũ không lấy lại focus trên DOM mới
có ID trường trùng nhau. Antigravity 3.8 Flash High R1 trả ba thay thế đúng;
portal.js chỉ thêm 6 dòng, bỏ 1 dòng: counter trong RAM, mountId mỗi lượt và
guard cả hai continuation. Fallback đồng bộ không đổi.

focusSnapshot/restoreFocus byte-identical với BASE, SHA256:
9a930f4a008b9fe32acaf6c80c68daed17e25e9626dc056a804e4cb820c39701.
Không đổi dữ liệu, route/session, header/sidebar, backend/auth authority,
Bot/engine/provider/ví/PayOS/ENV/schema. Bốn sửa motion PR700 được giữ nguyên.

## Bằng chứng

- RED thực thi source state/prefix/tail và helper: 3 pass/5 fail; GREEN 8/8.
- Focus/header/entry 24/24; full Node 1915/1915; Python motion 18/18.
- Detector Python nguyên chuỗi callback được thay bằng 8 test hành vi thực thi;
  không bỏ acceptance hoặc sửa ứng dụng để làm vừa bộ kiểm tra.
- Native form /video-studio/new: 20/20 ở 390/1440, thường/giảm, năm thứ tự.
  Old callbacks 8/8 giữ brief, selection và scroll; current/fallback 12/12 giữ
  title. Tab/ShiftTab, values và fresh document 20/20; page/console/overflow,
  request ngoài localhost và ghi sản phẩm đều 0.
- Review độc lập 0 Critical/0 Important; syntax, compile app và diff check đạt.

[Native tổng hợp](../../reports/ui-qa/motion-focus-20261109/native-focus.json)
không chứa bản gõ hoặc session/API. Nguồn đo khi chưa commit, ràng buộc bằng hash
portal.js f01508111706cc2d602286280348f295305667fe230ee169fede602586a192c6.
Form/DOM/public mount/motion là mã thật trong QA tạm; timing adapter là có
kiểm soát, không phải kiểm internals native ViewTransition: 8 ca thường dùng
adapter, 10 ca giảm tự bỏ qua, 4 ca fallback có giao với hai nhóm đó.

## Phần còn mở

Đối chiếu 4 click Dashboard→Studio: PR700 JS d41b0a9d… và candidate f0150811…
cùng 1 InvalidStateError ở chế độ thường, cả hai giảm chuyển động 0 lỗi.
Chín asset khác giống nhau; cả 4 ca mở tài liệu Studio mới, nonblank, không
tràn và scroll 0. Không khai navigation PASS vì lỗi vẫn còn; không quan sát
chữ ký lỗi mới trong bốn ca này, nguyên nhân chính xác còn mở.

Startup 103–108ms còn điều tra. A/B dời reset chưa có variant đạt comparator,
nên không áp relocation hoặc tuyên bố tăng tốc. Whole-app locale/responsive/
keyboard/auth/lab/device/signed production R218 vẫn mở. Form video còn chữ
cố định “media” trong VI; ghi backlog, không ghép vào sửa focus.

## Report

TASK=MOTION-NOV09-FOCUS-CONTINUATION
BASELINE_FAILURES=5/8 focus; PR700 normal navigation InvalidStateError1
BRANCH_FAILURES=0 focus; same normal navigation error1
NEW_FAILURES=0 observed bounded signatures; not whole-app claim
PROVIDER_CALLS=0
WALLET_MUTATIONS=0
ENV_MUTATIONS=0
PRODUCTION_DATA_MUTATIONS=0
DEPLOY=NO at receipt creation; delivery evidence is separate
LIVE_PASS=NOT_TESTED
LESSON_CANDIDATE=NONE
