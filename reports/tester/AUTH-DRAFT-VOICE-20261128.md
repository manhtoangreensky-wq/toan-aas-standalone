# AUTH-DRAFT-VOICE-01 — kết quả kiểm bản nháp trong phiên

Đang đọc và áp dụng skill owner-governed-codex cho task này.

BASE/HEAD=`cf94b23e6a26010e88ebcd33b36623204c784c9a`;
tree=`2894f7eda21cb379041e3f34219c5ea08d0e9e7f`.
Nhánh `codex/auth-draft-isolation-20261128`; Issue #689;
contract comment7227137073. Ứng dụng đang ở đúng bản đã giao PR821.

| AC | Thao tác thực | Kết quả |
|---|---|---|
| AC1 | TTS/Saved nhập riêng; đổi tab, Back/Forward | PASS; dữ liệu riêng và volume0 giữ; tab/URL/form đúng; không document reload khi đổi tab |
| AC2 | Reload thật, cùng cookie/context | PASS; A vẫn đăng nhập; draft chưa lưu rỗng; speed1.0/volume100 |
| AC3 | Nhập lại A; logout/confirm/POST→401→B, cùng context | PASS; A draft/identity không còn; B draft phục hồi riêng |

Môi trường: actual FastAPI/shell/integration/renderer; SQLite và asset tạm;
secret giả chỉ trong child process; Chrome/Playwright sẵn có, VI390×844.
Browser plugin không có. Không mock bootstrap/capability, không force enabled,
không profile giọng giả hoặc Submit/Save/Estimate/Confirm.

Network ledger: register2/login3/logout1; chỉ GET allowlist, thêm đúng hai
HTML route Voice. Không canonicalVoice/features-status request hoặc provider/
engine/upload/job/payment call. Không sentinel trong browser storage.
0console/pageerror/unknownrequest; server exit0 và runtime hashes giữ.

Lượt cuối: `auth-mounted-0iJBAl/summary.json`; bốn PNG.
Lượt đầu: `auth-mounted-2K3k89/summary.json`, FAIL trước thao tác draft vì
harness chờ dashboard-list-state tại Voice. Root truy đúng nguồn
integration14983/16388 và sửa predicate QA; không sửa app hoặc nới capability.
Không đổi nhãn lượt đầu thành PASS, không tính lỗi worker.

Ảnh chỉ nhận diện trang, có khung đang chuyển; không chứng minh giá trị form,
contrast, layout/motion đã ổn định hoặc full AX. Chức năng dựa trên DOM/
history/storage/identity assertions thật. Root đã xem hai ảnh, không chạy lại
luồng đã đạt chỉ để làm ảnh đẹp hơn.

TASK=AUTH-DRAFT-VOICE-01_LOCAL_TARGETED_PASS
BASE_SHA=cf94b23e6a26010e88ebcd33b36623204c784c9a
HEAD_SHA=cf94b23e6a26010e88ebcd33b36623204c784c9a
FILES_CHANGED=Documentation_and_QA_only;APPLICATION=0
TESTS=3AC_PASS;1VI390flow;0console/pageerror/unknown;serverexit0
BASELINE_FAILURES=QA_predicate1_not_application
BRANCH_FAILURES=0_in_final_run;first_run_FAIL_retained
NEW_FAILURES=0_application_observed;not_whole_repo_claim
PROTECTED_COMPARATORS=Runtime_hashes_and_tracked_source_unchanged
PROVIDER_CALLS=0
WALLET_MUTATIONS=0
DEPLOY=NO_NEW_DEPLOY;existing_PR821_runtime_unchanged
LIVE_PASS=NOT_PRODUCTION;3local_acceptances_only
BLOCKERS=NONE_for_three_cases;broader_goal_open
LESSON_CANDIDATE=NONE
