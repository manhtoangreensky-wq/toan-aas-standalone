# MU-MUSIC-GUARD-BOUNDARY-C — nhận đúng cảnh báo không có composer

Ngày 23/10/2026. LOCAL_UI_ACCEPTED, delivery pending; dependency để hoàn tất AC04 của
MU-NATIVE-SUBMIT-FEEDBACK-LOCALE-A. Không reset spec A hoặc bộ đếm hai handoff.

Repo standalone; branch `webapp-r218-billing-ui-20261022`, PR661/Issue664.
Git BASE `80f12d220c83ae4febebb99ca9742560f3c2ac85` + overlay A đang kiểm thử.
Integration overlay SHA256:
`c19fbc13446f404526518578b8dbbc26ecb871c423d4453519f0950cd98b6b7a`.

## Bằng chứng và nguyên nhân

Actual signed localhost `/music-directions/compose` trả HTTP200, `ok=false`,
`status=guarded`, mã `WEB_MUSIC_DIRECTION_COPYRIGHT_GUARD`; data chỉ có
execution và16 cờ side-effect đều booleanfalse, không composer. Đây là cảnh
báo thật, không output giả. UI lại hiện lỗi kết nối và toast server VI.

Probe hàm production thật: accepted=false; missingKeys=[composer], extraKeys=[],
allSideEffectFlagsFalse=true. Hàm consumer này byte-equal với HEAD80f12d2,
vì vậy là lỗi baseline được browser phát hiện, không do thay9copy-site của A.
`MUSIC_PROMPT_COMPOSER_RESULT_KEYS` dành cho kết quả thành công có composer;
`MUSIC_PROMPT_COMPOSER_BOUNDARY_KEYS` hiện có mới là17key của cảnh báo.

## Thay đổi tối thiểu

Thêm `musicDirectionPresetGuardBoundaryIsSafe(value)` dùng đúng keyset
`MUSIC_PROMPT_COMPOSER_BOUNDARY_KEYS`, execution tag
`web_native_deterministic_music_direction_only`, và mọi key khác execution
phải **===false**. Không thêm composer giả, không bỏ/rút key, không nhận
truthy/falsy thay boolean. Không đổi success boundary/matcher hiện có.

Chỉ hai guard callsite của Music (direct guarded response và catch.payload
guarded) dùng helper mới. Thành công vẫn đi qua validator cũ có composer.
API, CSRF, quyền, route, epoch, finally, DTO server, wallet/provider và mọi
SFX consumer không đổi. Đây là nhận biết trạng thái UI bị từ chối, không mở
capability, job, output hoặc thực thi nào.

Allowlist C:

1. static/portal/integration.js: thêm helper và đổi2guard callsite của Music.
2. tests/music-direction-guard-boundary.test.mjs mới: helper/caller thật và
   fixture17keys/16flags tự khai độc lập từ backend source; không lấy response
   QA làm packet gửi worker, không mock guard validator để né lỗi.
3. tests/music-sfx-submit-feedback.test.mjs: thêm dependency double tên mới
   vào harness UI, không đổi literal mong đợi/giảm coverage. Test C và browser
   mới là bằng chứng parser DTO thật; test A vẫn được ghi rõ giới hạn transport.
4. tests/test_music_directions_portal_contracts.py: đổi một source assertion
   trong action sang guard-helper mới; giữ nguyên kiểm success validator cũ.

## Acceptance / RED→GREEN

- C01: action thật + `api()` double ném envelope theo source contract guarded, real exact-key
  helpers: trước sửa bị throw/lỗi kết nối; sau sửa merge guarded, giữ draft,
  không success/output, toast đúng thông báo A. Kiểm cả response/error paths.
- C02: guard17key thật được nhận; thiếu/extra key, composer giả, sai execution,
  null/array/string, từng cờ true/0/stringfalse/null/object/array/undefined đều bị
  từ chối. Success validator cũ vẫn cần composer và không bị sửa byte nào.
- C03: 2callsite/helper là toàn bộ production diff của C so với overlaySHA;
  không thay constant/shared exactkeys/API/auth/backend/SFX/portal.js/CSS.
- C04: Python21, Node A44 + C/full regression; actual signed browser Music/SFX
  pending→success3text→copyrightguard; metadata false và0provider/wallet/data thật.
  A chưa được tick runtime trước khi qua C. Không có response fixture hoặc giảm
  validator để tạo PASS. SFX helper giữ nguyên.

Một Flash3.8 worker, R1/R2 tối đa, Codex tự chạy gate; không vòng3. Mỗi task
2–5phút, source/test/MAP đủ trong packet. Không dùng model khác hoặc mở IDE.
Sổ C `_giao-viec/CHECKLIST-24-MUSIC-GUARD-BOUNDARY.md`; master/tracker vẫn P2/664.
PROVIDER_CALLS_APP=0; WALLET_MUTATIONS=0; PRODUCTION_DATA_MUTATIONS=0;
DEPLOY=NO; LIVE_PASS=NOT_TESTED; GOAL=ACTIVE; motion cuối.

## Kết quả và an toàn dữ liệu

Launch ban đầu chứa QA envelope bị auto-review từ chối trước CreateProcess;
không export. Đổi thật sang `--source-only`: chỉ source/test/ticket/MAP và3
pure backend function source, không runtime payload/log/DB/screenshot. R1
không đạt harness0/3ReferenceError và Pythonedit thiếucomma; không áp codeC.
R2 source-only SUCCESS205.684s/1turn; test áp nguyên văn trước, cleanRED0/3
assertionfail rồi productionR2 nguyên văn → GREEN3/3. Không có vòng3.

Focused47/47, fullNode1000/1000, Python21/21, syntax2JS/py_compile2/diff đạt.
Guard17keys/16strictfalse, từngflag invalid/missing bị từ chối; không cho
composer giả. Old success boundary/result/matcher/shared exactkeys byteequal
BASE; assertion composer:{} chỉ kiểm shell boundary, không successDTO đầy đủ.
Reverse C equals AoverlaySHAc19fbc; SFXblock/9protectedfiles unchanged.
Music signed browser18/18 sauC; SFX18/18 trướcC là regression evidence riêng,
không giả claim cùngrevision. Independentreview Critical0/Important0.
Helper21132 verifiedSPEC/round2/overlaySHA, dừng sauJSONSUCCESS; wrapper
4294967295 là cleanup, không product failure. QA server53124 dừngexit0.

### Checklist công khai — đối chiếu master P2

- [x] C01 realvalidator/caller cleanRED0/3→GREEN3/3.
- [x] C02 17keys/16strictfalse; negativeflags vàsuccessvalidator unchanged.
- [x] C03 helper/2calls only; Atestdependency/Pythonwire; comparator đạt.
- [x] C04 local47focused/1000Node/21Python/36two-phasebrowser; evidence/docs.
- [ ] Branchdelivery: prepush/provenance/push/readback/CI/receipt Issue664.
