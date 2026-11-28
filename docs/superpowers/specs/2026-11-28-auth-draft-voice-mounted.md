# AUTH-DRAFT-VOICE-01 — bản nháp trong phiên, kiểm trên ứng dụng thật

Đang đọc và áp dụng skill owner-governed-codex cho task này.

BASE_SHA=`cf94b23e6a26010e88ebcd33b36623204c784c9a`.
Nhánh `codex/auth-draft-isolation-20261128`; sản phẩm WebApp standalone;
tracker duy nhất Issue #689. Đây là kiểm thử trên môi trường tạm, không production.

## Điều kiện mở

AUTH-RETURN-01 đã giao PR #821: CI `46056807355` hai job SUCCESS,
456/456 bản ghi; Web-only deploy `46059896569` SUCCESS. Local/VPS cùng
BASE và cây `2894f7eda21cb379041e3f34219c5ea08d0e9e7f`.
Receipt Issue #689/comment7226125049 và PR #821/comment7227030166
đã đọc lại đúng nội dung. Không chạy lại các nhóm đã đạt của đợt đó.

## Mục tiêu và phạm vi khóa

Chứng minh bản nháp chưa lưu của Voice TTS/Saved trên DOM thật:
giữ riêng khi đổi chế độ, mất sau reload và không lọt từ tài khoản A sang B.
Không suy từ các bài kiểm trích hàm thành luồng trình duyệt hoàn chỉnh.

Ứng dụng, auth backend/session/CSRF, schema, provider, ví, PayOS, engine,
Bot, ENV thật và motion đều được bảo vệ. Không có application edit trong
phiếu kiểm thử này. Chỉ được tạo tài liệu/QA ngoài runtime và dữ liệu giả
trong SQLite/asset tạm của tiến trình QA. Không đọc `.env`.

## Checklist và tiêu chí nghiệm thu

- [x] AUTH-RETURN-01 đã giao; READ hiện trạng và điểm kiểm Voice đã có.
- [x] AC1: A nhập hai bộ scalar khác nhau tại TTS và Saved; bấm tab,
  Back/Forward; mỗi form phục hồi đúng dữ liệu riêng, gồm volume=0.
  URL, form route và đúng một tab `aria-current=page` đồng bộ; đổi tab
  không tải document mới. Giữ `lang=vi`.
- [x] AC2: reload thật, không xóa cookie/storage/context. A vẫn đăng nhập;
  hai script chưa lưu đều rỗng, scalar về mặc định renderer thực.
- [x] AC3: nhập lại draft A, đăng xuất bằng UI/confirm/POST thật;
  `/auth/me` trả 401; đăng nhập B cùng context. B không thấy identity/
  draft A; draft mới của B phục hồi riêng khi đổi tab.
- [x] Mỗi AC: sentinel không xuất hiện trong localStorage/sessionStorage;
  không POST ngoài register/login/logout, không upload/quote/provider/job/
  payment; không sửa disabled/capability bằng JavaScript để giúp test đạt.
- [x] Có ảnh, giá trị DOM/identity, network ledger, source hashes và chứng
  cứ dừng sạch browser/server. Chỉ tick khi có bằng chứng tương ứng.

Các giá trị được nhập phải hợp lệ theo type/options/min/max/step thật.
Không bơm profile giọng giả vào Saved. Không bấm Save/Continue/Estimate/Confirm.
Giới hạn phạm vi ban đầu: VI, 390×844, một context A→B và tối đa ba lần
đăng nhập trong một tiến trình/DB tạm; không nới throttle.

## Cổng mạng và dữ liệu

Kế thừa host auth QA cô lập đã kiểm. Chỉ thêm hai GET HTML
`/voice/tts`, `/voice/saved` vào cả allowlist server và browser.
Giữ các bootstrap/static GET và ba POST auth hiện có; không mở wildcard.
Không mở `/voice/profiles` hoặc `/features/status` chỉ để giả capability.
Bridge giữ trạng thái được bảo vệ; không gọi nguồn chuẩn/provider.

Nếu máy chủ không cấp khả năng soạn bản nháp, phải ghi DOM/bootstrap
thiếu điều kiện và kết quả chưa kiểm; không đổi ứng dụng, ENV, quyền hoặc
giả phản hồi để vượt cổng.

## Bằng chứng và bước tiếp

Root dùng harness localhost đã đọc, lưu JSON/ảnh ngoài repository.
Comparator nguồn: Git BASE, hash các tệp runtime và tracked diff trống.
Các unit test Voice/Music/SubDub đã có chỉ là nguồn tham chiếu, không
được gọi là bằng chứng mounted mới hoặc chạy lại khi input không đổi.

Nếu lộ lỗi ứng dụng thật: giữ bằng chứng RED, lập amendment đúng hàm và
giao Antigravity 4.0 Extra High; tối đa hai lượt cùng acceptance trước
khi root được sửa trực tiếp. Lỗi harness/spec do root sửa ở QA, không
tính lỗi worker và không sửa app để chiều fixture.

Canonical response race/error, các sản phẩm khác, signed production,
AX/responsive còn thiếu, thiết bị/Safari và cache offline vẫn mở.
Đường guarded không phát request không chứng minh được stale-response fence.
Motion M-FINAL làm cuối. WHOLE_GOAL_COMPLETE=NO.
PROVIDER_CALLS=0;WALLET_MUTATIONS=0;PRODUCTION_DATA_WRITES=0.

## Kết quả thực nghiệm 28/11/2026

Harness actual app trên BASE đã chạy: ba AC PASS, một luồng VI390×844,
bốn PNG; không lỗi trang/console/yêu cầu ngoài phạm vi, server exit0.
Actual DOM xác nhận các scalar hợp lệ; defaults script rỗng, speed1.0,
volume100. A dùng TTS0.85/0 và Saved1.2/130; tab/history phục hồi riêng,
reload về mặc định và B chỉ giữ draft B. Saved không dùng profile giả.
Không lưu sentinel trong browser storage; POST chỉ register2/login3/logout1.
Các hash runtime giữ nguyên trong toàn lượt kiểm; không có app edit.

Lượt đầu `auth-mounted-2K3k89` FAIL trước AC1 do harness chờ
workspaceDraftReadState hết loading. Nguồn xác nhận list này chỉ hydrate
ở workspace/dashboard; không phải readiness của Voice. Root sửa đúng
predicate QA sang signed identity rồi kiểm capability/control thật.
Lượt cuối `auth-mounted-0iJBAl/summary.json` PASS; giữ nguyên lượt FAIL,
không tính là lỗi ứng dụng hoặc worker. Preflight cuối vẫn thấy list-state
loading, nhưng capability authoring và input thật đều được cấp.

Ảnh chỉ hỗ trợ nhận diện trang tại thời điểm chuyển khung; không dùng để
kết luận giá trị input nhìn thấy, độ tương phản, trạng thái motion ổn định
hay accessibility. Ba AC chức năng được chứng minh bởi assertion DOM/
history/identity/storage thật và network ledger, không phải ảnh đơn lẻ.
Signed EN/ZH, các sản phẩm khác và canonical race/error vẫn chưa kiểm.
