# AUTH-DRAFT-MUSIC-01 — kiểm bản nháp Âm nhạc trên ứng dụng thật

Đang đọc và áp dụng skill owner-governed-codex cho task này.

BASE/HEAD=`cf94b23e6a26010e88ebcd33b36623204c784c9a`;
tree=`2894f7eda21cb379041e3f34219c5ea08d0e9e7f`.
Branch auth-draft-isolation-20261128; Issue689/contract7227423788.

| AC | Thao tác và quan sát | Kết quả |
|---|---|---|
| AC1 | Nhạc nền và bài hát có bộ scalar/lyrics riêng; đổi tab/Back/Forward | PASS, không document reload khi đổi tab; newline/Unicode và querylang/theme giữ |
| AC2 | Reload thật, không xóa cookie/storage/context | PASS, A vẫn đăng nhập; draft rỗng và defaults thực phục hồi |
| AC3 | Nhập lại A→UIlogout/confirm/POST→401→B cùngcontext | PASS, A không còn; B draft phục hồi riêng |

Fixture chỉ dùng options thật: background premium/background/30; song
standard/lyrics/duet/seconds/45, lời gốc có xuống dòng. Không Submit/Save/
Estimate/Confirm, không fake capability. Actual server cấp authoring,
bridge guarded. POST register2/login3/logout1; GET finite allowlist.

Lượt duy nhất `auth-mounted-tIzOyd/summary.json` PASS; 3AC/VI390×844;
4PNG/0console/pageerror/unknownrequest/serverexit0; runtime hashes giữ.
Root xem ảnh A/B ở form mô tả thật. Ảnh không thay contrast/AX/motion proof.
Không gọi provider/engine/quote/job/upload/payment; dữ liệu chỉ tạm.

Các helper và scope Voice đã đạt không thay đổi/chạy lại. Đây chỉ là
RAM draft guarded-authoring; không server-saved draft, signed EN/ZH,
canonical race/error, production, thiết bị/Safari/offline hoặc whole goal.

TASK=AUTH-DRAFT-MUSIC-01_LOCAL_TARGETED_PASS
BASE_SHA=cf94b23e6a26010e88ebcd33b36623204c784c9a
HEAD_SHA=cf94b23e6a26010e88ebcd33b36623204c784c9a
FILES_CHANGED=Documentation_and_external_QA_only;APPLICATION=0
TESTS=3AC_PASS;1VI390flow;0console/pageerror/unknown;serverexit0
BASELINE_FAILURES=NONE_OBSERVED_IN_THIS_FLOW
BRANCH_FAILURES=0
NEW_FAILURES=0_in_this_scope;not_whole_repo_claim
PROTECTED_COMPARATORS=Runtime_hashes_and_tracked_source_unchanged
PROVIDER_CALLS=0
WALLET_MUTATIONS=0
DEPLOY=NO_NEW_DEPLOY;CODE_BASELINE_PR821
LIVE_PASS=NOT_PRODUCTION;3local_acceptances_only
BLOCKERS=NONE_for_three_cases;broader_goal_open
LESSON_CANDIDATE=NONE
