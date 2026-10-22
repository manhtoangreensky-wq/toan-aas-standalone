# R218 Voice audit — cổng đẩy tài liệu, 23/10/2026

Đang đọc và áp dụng skill owner-governed-codex cho task này.

TASK=R218-P1-Q0-VOICE-20261023
BASE_SHA=30903110482f0c15b20fc959b30796dc0c7a1490
APPLICATION_SOURCE_SHA=30903110482f0c15b20fc959b30796dc0c7a1490
SCOPE=docs/spec/checklist/evidence only; no application source changed
TESTS=Node927/927; Python source10/10; isolated Python runtime31/31; browser6configurations/24QAmetadatawrites
BASELINE_FAILURES=4observed EN/ZH filter-toast locale findings;3repeated technical boxes in Voice direction disclosure
BRANCH_FAILURES=same findings; no fix claimed
NEW_CODE_FAILURES=0; application source unchanged
PROTECTED_COMPARATORS=all Python/runtime/static/template/workflow application paths unchanged from BASE
PROVIDER_CALLS=0 product runtime; authorized Gemini Builder invocations returned no valid patch
WALLET_MUTATIONS=0
PRODUCTION_DATA_MUTATIONS=0
DEPLOY=NO
LIVE_PASS=NOT_TESTED

## Review và tài liệu vận hành

- Sửa ledger phân biệt hồ sơ hướng đọc Web và Voice Vault âm thanh canonical.
  `22` endpoint metadata không chứng minh đủ chức năng Bot.
- Source test31/31 không thay browser; browser6cấu hình không thay toàn ma trận.
- Đưa2 lỗi UI vào đúng hàng, ghi worker timeout không phải build thành công.
- `.agents/state/WEBAPP-BOT-PARITY-R218.yaml` cập nhật branch/PR/HEAD/checkpoint
  hiện hành, giữ lịch sử; không tiếp tục nhầm PR654/billing worker cũ.
- Tài liệu hiện trạng: `TAI-LIEU/01-NGHIEP-VU-VAN-HANH.md`; đối chiếu:
  `TAI-LIEU/02-CHUC-NANG-GOC-VA-HIEN-TAI.md`.

## Đối chiếu yêu cầu gốc

INITIAL_FEATURE_DOC=docs/superpowers/specs/2026-10-18-r218-02a-voice-vault-canonical-contract.md
INITIAL_FEATURE_COMPARISON=TAI-LIEU/02-CHUC-NANG-GOC-VA-HIEN-TAI.md, Voice23/10

Nguồn Bot/callback giữ ở spec gốc. Chưa có canonical management/preview/apply
thì tiếp tục OPEN; không thay yêu cầu bằng metadata Web hoặc tạo nút giả.

## Phiên Tester

TESTER_PROJECT_ID=R218-VOICE-20261023 (local repo session, not a new chat)
TESTER_PROJECT_STATUS=READY
TESTER_SCOPE=VO-META-01..04; VO-CLARITY-01; VO-BOUNDARY-01
TESTER_CASE_SOURCE=KIEM-THU/DANH-SACH-CASE.md
TESTER_EVIDENCE_DIR=C:/Users/toann/Documents/Codex/qa/r218-voice-direction-20261023/
QA_SUMMARY=reports/audit/R218-VOICE-METADATA-QA-20261023.json

Dữ liệu QA tạm; server đã dừng và DB/assets được dọn. Không tạo thẻ/project
GitHub hàng loạt, không đổi nhãn/quyền hoặc yêu cầu đăng nhập lại.

## Delivery chưa đóng

PR661 đọc bằng gh: OPEN, HEAD3090311, mergeStateDIRTY, checkRollup[].
Fetch main406127e và read-only merge-tree chỉ ra2conflict:
`reports/migration/preflight.json`, `reports/migration/web_inventory.json`.
Không thực hiện working-tree merge/rebase; không đẩy main, merge PR hoặc deploy.
Tệp evidence sẽ refresh sau commit docs sạch rồi verify đúng HEAD trước push.

PUSH_GATE=READY_DOCS_ONLY_AFTER_JSON_DIFF_AND_PROVENANCE_VERIFY
UI_ACCEPTANCE=OPEN
MERGE_GATE=NOT_READY
GOAL=ACTIVE
