# MU-NATIVE-SUBMIT-FEEDBACK-LOCALE-A — thông báo Music/SFX

Ngày 23/10/2026. LOCAL_UI_ACCEPTED_WITH_C; branch delivery pending.

- Sản phẩm: standalone WebApp, `manhtoangreensky-wq/toan-aas-standalone`.
- Worktree: `C:/Users/toann/Documents/Codex/_webapp-r218-voice`.
- Branch: `webapp-r218-billing-ui-20261022`; PR661; tracker Issue664.
- BASE_SHA: `80f12d220c83ae4febebb99ca9742560f3c2ac85`.
- Dependency đã đạt: MU-INTERACTION-FEEDBACK, CI39934950954 hai job SUCCESS,
  receipt Issue664#issuecomment-6362432472. Không sửa lại 4 helper đã khóa.
- Owner: “tiếp tục”; Flash3.8 chạy nền, Codex giao việc/review/verify;
  không chữ thử nghiệm, ô thừa, đầu ra giả; motion cuối.

## 1. Finding và kết quả cần thấy

Ảnh QA thật `sfx-zh-dark-390x900.png` cho thấy toast xác nhận còn tiếng Việt
và liệt kê thuật ngữ kỹ thuật. Hai nhánh action tại integration.js có 19 nơi
hiển thị thông báo, trong đó 6 nơi ưu tiên `result.message/guarded.message`
từ server. Màn hình/cảnh báo sửa nội dung đã dịch không thay thế được việc
kiểm tra phản hồi sau submit.

Spec A chỉ khép ba trạng thái: đang lập, thành công sau receipt hợp lệ,
và guarded sau boundary hợp lệ. Khách thấy thông báo ngắn, đúng VI/EN/ZH,
không nhầm văn bản hướng dẫn với âm thanh đã tạo. Không đổi server message,
payload, cờ an toàn, quyền, route, request epoch hoặc quy tắc xử lý.

## 2. Phạm vi và điều không làm

Cho phép:

1. `static/portal/integration.js`: thêm một helper locale nhỏ, giới hạn hai
   namespace Music/SFX; thay đúng 9 callsite phản hồi trong hai action:
   `music-direction-preset-compose` và `sfx-cue-sheet-compose`.
2. `static/portal/portal-i18n.js`: thêm 4 key `feedback.pending/success/guarded/
   copyright` vào mỗi catalogue Music Direction và SFX, tổng 8 row.
3. Một test mới `tests/music-sfx-submit-feedback.test.mjs` chạy helper và
   hai nhánh action thật qua VM với transport được kiểm soát.
4. Spec/checklist/state/evidence/Tester/operation docs do Codex quản lý.

Amendment trước production BUILD: thêm đúng test nguồn
`tests/test_sfx_cue_sheet_portal_contracts.py`, trong hàm
`test_sfx_cue_sheet_keeps_unsent_edits_stale_across_remount_without_storage_or_auto_navigation`.
Assertion đang buộc inline success phải dùng nguyên câu VI kỹ thuật; đổi sang
kiểm lời gọi status nằm sau accepted-receipt merge và trước catch. Node action
test mới kiểm copy/inline thật ở VI/EN/ZH. Không đổi test data/security/backend
hay bỏ assertion success wiring. Worker được thêm file thứ4 này trong R2.

### R1 review

Test R1 áp nguyên văn để chẩn đoán, 0pass/13fail: `Object.assign(Object.create(
realI18n),{t:...})` đụng inherited read-only property. Đây là lỗi harness, không
phải product RED. Production R1 chưa áp. R2 phải dùng plain-object locale bridge,
đúng3field payload (không brief/style/mood/v), guard đủ3locale và không silent
return ở test fallback. Production không suy copyright từ data.error_code ngoài
schema; chỉ exact top-level structured code. CùngAC01 fail1, không reset SPEC.

Không đổi `portal.js`, CSS/palette, shared `toast`, API helper, hai validator
payload, shared safety validator, backend/auth/ENV/schema/provider/ví/PayOS,
Bot/route-engine, mutation hoặc motion. Không thêm DOM/nút/giá/audio/output.

**Không bỏ sót phần chưa làm:** mọi thông báo validation, wrong-route,
not-ready, invalid receipt/boundary, retry/connection và outer catch còn lại
được ghi riêng thành `MU-NATIVE-VALIDATION-ERROR-LOCALE-B`. Không dùng spec A
để tuyên bố toàn bộ lỗi/locale của hai công cụ đã xong. B phải có READ/contract
riêng trước khi chạm shared safety hoặc luồng lỗi.

## 3. Copy chốt cho khách

| Tool/key | VI | EN | ZH |
|---|---|---|---|
| music/pending | Đang lập ba hướng âm nhạc… | Creating three music directions… | 正在创建三个音乐方向… |
| music/success | Đã lập ba hướng âm nhạc. | Three music directions created. | 已创建三个音乐方向。 |
| music/guarded | Điều chỉnh nội dung trước khi lập hướng âm nhạc. | Adjust the brief before creating music directions. | 请调整摘要后再创建音乐方向。 |
| music/copyright | Hãy mô tả phong cách riêng, không yêu cầu mô phỏng nghệ sĩ hoặc tác phẩm có bản quyền. | Describe an original style instead of asking to imitate an artist or copyrighted work. | 请描述原创风格，不要要求模仿艺术家或受版权保护的作品。 |
| sfx/pending | Đang lập ba vị trí hiệu ứng… | Creating three SFX cues… | 正在创建三个音效提示… |
| sfx/success | Đã lập ba vị trí hiệu ứng. | Three SFX cues created. | 已创建三个音效提示。 |
| sfx/guarded | Điều chỉnh nội dung trước khi lập bảng hiệu ứng. | Adjust the brief before creating the SFX cue sheet. | 请调整摘要后再创建音效提示表。 |
| sfx/copyright | Hãy mô tả hiệu ứng riêng, không yêu cầu mô phỏng nghệ sĩ hoặc tác phẩm có bản quyền. | Describe original effects instead of asking to imitate an artist or copyrighted work. | 请描述原创音效，不要要求模仿艺术家或受版权保护的作品。 |

Chỉ chọn copy copyright khi đúng mã lỗi hiện có
`WEB_MUSIC_DIRECTION_COPYRIGHT_GUARD` / `WEB_SFX_CUE_COPYRIGHT_GUARD`.
Guarded không rõ mã dùng copy guarded, không tự suy ra lý do. Không hiện raw
server message trong các trạng thái này; dữ liệu/code/boundary vẫn giữ nguyên.
SFX status inline và toast success dùng cùng copy success; không thêm ô.

## 4. Acceptance và bước 2–5 phút

- AC01/test-first: test helper/catalogue thật và hai action block thật; các
  state pending/success/known copyright/unknown guarded ở VI/EN/ZH. Expected
  là literal độc lập, không tự dùng helper đang test để tính expected.
- AC02/minimal change: chỉ 9 phản hồi đã chỉ định + helper + 8 row; không
  đổi fields/POST/receipt/source, strict capability, epoch/finally/merge.
  Raw server message cố tình là VI phải không thắng bản dịch UI.
- AC03/negative: không success toast khi envelope không hợp lệ hoặc trả muộn;
  route/capability không hợp lệ không gọi API; không tự gửi khi input thay đổi.
  Các thông báo lỗi còn tiếng Việt của B không được gắn nhãn locale PASS.
- AC04/runtime: app signed localhost/DB tạm; hai route × VI/EN/ZH × light/dark
  ×390/1440, thêm375/landscape ở boundary cần thiết. Giữ request đang chờ để
  quan sát pending, sau đó cho POST deterministic thật tiếp tục; kiểm result3,
  toast/status đúng locale và không giả audio. Guard known bằng input thực nếu
  client/backend cho phép; trường không thể tái hiện phải ghi rõ thay vì giả PASS.
- AC05/regression: full Node, Python native/portal và 4 helper cũ; comparator
  ngoài helper/9 callsite/8 row bằng BASE; không thay shared/API/safety/auth/
  palette/provider/wallet. Syntax/diff, docs/Tester/prepush/provenance/delivery.

Verify dự kiến: `node --test tests/music-sfx-submit-feedback.test.mjs` phải
RED trước patch, GREEN sau patch; current interaction/locale focused giữ34/34.
Full Node `node --test --test-concurrency=2 tests/*.test.mjs`. Python4native/
portal files đã dùng ở spec trước. Browser không có plugin/skill Browser,
dùng Playwright/Edge headless hiện có; không mở IDE hoặc xác thực lại.

Một worker Flash3.8, tối đa R1/R2 cùng SPEC_ID/AC, không vòng3. Worker chỉ trả
test/code qua stdout, Codex dùng apply_patch sau review; không worker tools/
Git/browser/network/file-write. Output edit-record JSON được dùng để tránh
hunk giả; old/new phải khớp duy nhất source thật, không tự áp không kiểm tra.

## 5. Cổng chuyển tiếp

Checklist `_giao-viec/CHECKLIST-23-MUSIC-SFX-SUBMISSION.md` phải tồn tại trước
BUILD; tracker664 phải có dependency và các AC. Chỉ mở B sau khi A có evidence
và delivery; không tạo checklist mẹ cạnh tranh hoặc receipt-only CI loop.
`PROVIDER_CALLS_APP=0; WALLET_MUTATIONS=0; PRODUCTION_DATA_MUTATIONS=0`.
`DEPLOY=NO; LIVE_PASS=NOT_TESTED; GOAL=ACTIVE; MOTION=LAST`.

## 6. Kết quả đo 23/10/2026 — không thay contract gốc

R2 tiếp tục lỗi harness read-only export/TDZ, cùng AC01 lần2. Codex sửa đúng
test sau hai lượt fail: real catalogue VM riêng, plain locale bridge, pending
deferred, cross-realm spread/API spy/unsafe boundary. Không vòng3. Production
R2 áp nguyên văn; comparator GitBASE→A→C khớp tuyệt đối sau chuẩn hóa CRLF.
Clean RED3pass/7assertionfail → GREEN10/10; C strict guard bổ sung3/3;
focused47/47, full Node1000/1000, Python4native/portal21/21.

Actual signed localhost/DB tạm đạt36 cấu hình/72POST/72pendingchecks; mỗi
success nhận3textitems và mỗi cấu hình đi qua copyrightguard thật. SFX18
chạy trước C trên integrationSHA c19fbc; Music18 chạy sau C trên SHA6f67e5.
SFX action block byte-equal qua C; không gộp giả thành36 lượt cùngrevision.
VI/EN/ZH × light390/light1440/dark390/dark1440/dark375×812/dark844×390.
Errors/external/unapprovedwrites/HTTP/overflow0; không responsefixture.

Independentreview47/47,Critical0/Important0. Test A dùng transport/receipt/
validator doubles nên chỉ chứng minh locale/controlflow/payloadforwarding;
test C dùng parser thật, fixture16flags tự khai từ backend source. Browser
mới chứng minh POST native và DOM thực, không audio/provider hoặc LIVE.
Evidence `reports/audit/R218-MUSIC-SFX-SUBMIT-GUARD-QA-20261023.json`.
B vẫn mở; screenshot còn field hint VI/technicalcopy ngoài phạm vi9site.

### Checklist công khai — đối chiếu master P2

- [x] AC01 helper/catalogue/action thật, RED→GREEN10/10, không tautology.
- [x] AC02 đúng9feedback/8rows; comparator source/9protectedfiles đạt.
- [x] AC03 unsafe/stale/wrongroute/capability/API spy đạt, không success giả.
- [x] AC04 signednativeQA36uniqueconfigs/72POST/72pending đạt, có phase disclosure.
- [x] AC05 focused47/fullNode1000/Python21/syntax/compile/diff đạt.
- [x] Delivery: HEADfc8deb6/CI39950590927bothSUCCESS/receipt Issue6646364623486.
