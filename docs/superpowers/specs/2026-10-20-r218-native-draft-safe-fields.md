# NATIVE-DRAFT-SAFE-FIELDS-001 — lưu đủ lựa chọn Music và Voice

## CONTRACT và quyền

Owner đã duyệt ngày 20/10/2026: thêm đúng năm trường văn bản `lyrics`,
`vocal_mode`, `default_voice_gender`, `volume_percent`, `source_language` vào
hợp đồng lưu nháp; không bỏ nội dung dài và thông báo đúng ngôn ngữ.
BASE_SHA=2c216825b2b1fdfcdc4f97853961117299e39547; PR #654.
Đây là amendment hẹp của MUSIC-INTAKE-READABILITY-001, làm trước Music quote.

Root: C:/Users/toann/Documents/Codex/_webapp-r218-voice.
Allowed: `copyfast_api.py` chỉ WORKSPACE_DRAFT_ALLOWED_FIELDS;
`static/portal/integration.js` chỉ native save/input và helper copy riêng;
`static/portal/portal-i18n.js` chỉ catalogue native save mới; hai test mới,
spec/checklist/state/evidence tương ứng. Mọi dirty change trước amendment
thuộc các lát Voice/Music đang có và phải giữ nguyên.
Protected: schema, auth/CSRF/idempotency, feature allowlist, authority/file/
profile/quote/consent filters, giới hạn 4000 ký tự/trường và 16000 byte,
engine/provider/wallet/PayOS, Voice quote/timer, workflows/deploy.

## READ — nguyên nhân và ảnh hưởng

App QA Music song POST `/api/v1/workspace/drafts` trả 422 vì allowlist thiếu
lyrics/vocal_mode; Voice thiếu ba lựa chọn còn lại. Frontend chỉ copy chuỗi
`text.length <= 4000` nên chuỗi dài bị bỏ im lặng. Success/busy/title còn VI
cứng và lấy message VI từ API vào giao diện EN/ZH.

`git grep -n -E 'workspaceDraftInput\(|_workspace_draft_input\(' -- '*.js' '*.mjs' '*.py'`:

- copyfast_api.py:3050 định nghĩa, :4703 create, :4778 update.
- static/portal/integration.js:12541 định nghĩa, :36761 save/update caller.
- tests/test_portal_safety_contracts.py:543 chỉ kiểm presence của helper.

Hai file runtime; không đổi tên/chữ ký helper hay consumers khác. Quyền sửa
hợp đồng được Owner cấp rõ ràng; không suy ra quyền mở capability mới.

## Các bước 2–5 phút, gate chung

1. RED API: create/read/update/replay giữ đúng năm trường, 0 volume và Unicode;
   file/profile/authority/nested/non-string/oversize vẫn bị từ chối.
2. RED frontend: dài hơn 4000 Unicode code points phải báo lỗi trước POST và
   không sửa object nguồn; đủ 4000 vẫn giữ nguyên, không truncate.
3. Thêm đúng năm tên vào backend allowlist. Không sửa validator/giới hạn.
4. Native save dùng copy VI/EN/ZH cho lỗi/busy/success; tên nháp dùng tiêu đề
   đang hiển thị đã bản địa hóa. Không dịch lời bài hát/nội dung người dùng.
   Giữ CSRF/acquire/release/finally và API payload/idempotency.
5. Restart đúng server QA của task; save/readback thật trên localhost ba locale;
   test lỗi dài: 0 POST, giá trị còn nguyên. Không provider/production writes.

## Checklist nghiệm thu

- [ ] AC01 API roundtrip + replay + update đủ năm trường, Unicode/0.
- [ ] AC02 chốt authority/file/profile/consent, owner scope, CSRF và limits giữ.
- [ ] AC03 frontend từ chối quá dài, không làm mất hay cắt nội dung.
- [ ] AC04 title/busy/success/failure VI/EN/ZH, bỏ raw API prose khỏi toast.
- [ ] AC05 app QA actual save/readback ba ngôn ngữ; lỗi/overflow/external0.
- [ ] AC06 compile/Node/pytest/diff review và protected comparators đạt.

Verify: `node --test tests/workspace-draft-save-contract.test.mjs` và
`python -m pytest tests/test_workspace_draft_product_fields.py -q` → fail0.
Chỉ tick khi có output thực nghiệm. DEPLOY=NO, LIVE_PASS=NOT_TESTED;
PROVIDER_CALLS=0, WALLET_MUTATIONS=0. Engine/giao nhạc không thuộc gate này.
