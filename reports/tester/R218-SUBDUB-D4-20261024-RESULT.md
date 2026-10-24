# Tester độc lập — SD-D4 original-audio toggle — 24/10/2026

Đang đọc và áp dụng skill owner-governed-codex cho task này.

VERDICT=READY_FOR_SCOPED_LOCAL_ACCEPTANCE_ONLY
FINDINGS=C0/I0/M0 trong phạm vi SD-D4 đã kiểm.
Không phải READY_TO_MERGE, CI PASS, deployed, LIVE, toàn bộ SD01..21 hay goal COMPLETE.

## 1. Hợp đồng và nguồn kiểm chứng

- Task: SD-D4-ORIGINAL-AUDIO-TOGGLE; sản phẩm standalone WebApp, không phải Bot.
- ROOT: `C:/Users/toann/Documents/Codex/_webapp-r218-voice`.
- Branch: `webapp-r218-billing-ui-20261022`; PR661/Issue664 chỉ là context, không sửa remote.
- BASE_SHA=HEAD_SHA=`ba4b2dfa1be096e35198e8bf60f3fa5596ed5af8`.
- Candidate là worktree chưa commit, không gán hash HEAD thành hash candidate.
- Spec đã đọc đầy đủ: `docs/superpowers/specs/2026-10-24-r218-subdub-original-audio-toggle.md`.
- Session: `reports/tester/R218-SUBDUB-D4-20261024.md`; nguồn case `KIEM-THU/DANH-SACH-CASE.md`, đúng SDD4-01..08.
- Các skill đã áp dụng: owner-governed-codex, locked-focus-engineering, single-agent-anti-overengineering, toanaas-system-design-and-open-apis, verification-before-completion và frontend-testing-debugging. Đã đọc `C:/Users/toann/Documents/Codex/AGENTS.md`; không có AGENTS.md sâu hơn trong ROOT.
- FSM: READ → CONTRACT → BUILD (không sửa implementation) → REVIEW → VERIFY → REPORT → LEARN (không tạo lesson).
- Tester không spawn agent, không mở browser/server/process, không đổi source/test/Git/index/HEAD/settings/auth/ENV/provider/wallet/DB production. Chỉ tạo báo cáo này bằng apply_patch. Root đang cập nhật docs đồng thời; không coi các thay đổi docs đó là của Tester.

Flow kiểm: signed `/subdub` → original volume 37 → off0/on37 hoặc manual0/positive/invalid → mode/Voice return → đúng draft/review; account replacement/logout/re-login không mang nhớ37/53 sang phiên khác. Thiếu mức nhớ hợp lệ dùng default Web100 đã được Owner duyệt.

## 2. Kiểm thử Tester tự chạy, có terminal output

Tất cả command dưới chạy tại ROOT, không cài dependency và không gọi mạng/provider.

| Command | Exit | Kết quả thực tế |
|---|---:|---|
| `node --test (Get-ChildItem -LiteralPath tests -Filter 'subdub-*.test.mjs' -File \| ForEach-Object FullName)` | 0 | tests80/pass80/fail0/cancelled0/skipped0/todo0; duration_ms1025.2863 |
| `C:/Users/toann/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe -m pytest -q -p no:cacheprovider tests/test_p0_05d_tester_workspace.py -k 'not test_owner_authorized_write_uses_private_temp_file_and_cleans_it'` | 0 | 32passed/1deselected/1warning;0.64s |
| `node C:/Users/toann/Documents/Codex/qa/r218-music-review-FH-20261024/gate-SDD4-TOGGLE.cjs --r2 --sol --applied` | 0 | 215lines/6tests/9records/parse/reverseLF/17protectedWholeHelpers/actualSourceDeclaredState; BASE0pass6assert0harness, CANDIDATE6pass0assert0harness |
| `git diff --check` | 0 | Không whitespace error; chỉ advisory LF→CRLF cho các docs đang sửa |
| `node -` — verifier read-only parse/hash/Cartesian/geometry/401/assets trên hai raw cuối, nhập qua PowerShell here-string | 0 | PASS;48main +24nonvoice+12pending+6accounts;360asset comparisons;source end-disk binding khớp |
| `node -` — verifier read-only Git blobs/metadata/WA48/SD21/mainSFX/currentdocs | 0 | PASS;676oldtestsLF-exact/5mainSFX/6metadata/48WA/8SDD4/21originalSD/42historicalcrosswalkrows |

Python chỉ dùng process-local `PYTHONDONTWRITEBYTECODE=1` và `PYTHONPATH=C:/Users/toann/Documents/Codex/_wa35-r74-qa-python-20261012/site-packages`; không thay ENV cấu hình app. Một warning là Pydantic class-based config deprecation tại `config.py:27`. Một ca bị loại đúng POSIX permission semantics trên Windows, không che lỗi SD-D4.

Full Node1307 và isolated Python85/1deselected/2warnings là bằng chứng root đã chạy, KHÔNG phải Tester tự chạy lại. Không chạy full repository pytest, compile tất cả module, CI, browser mới hoặc engine output.

## 3. Raw browser cuối: parse toàn file, không lấy summary làm bằng chứng duy nhất

QA=`C:/Users/toann/Documents/Codex/qa/r218-music-review-FH-20261024`.

| Artifact | SHA256 actual kiểm lại | Terminal / coverage |
|---|---|---|
| `SDD4-green-1792851641552/result.json` | `d48beec7b6eb94fed80ff0b2c0017cdc2dd9aaa36a88f343adfad48797275780` | PASS;48unique=2Dub modes×3locale×2theme×4viewports |
| `SDD4-supplement-1792852608922/result.json` | `5167f89c40152fc668649d8a0e63b3e00eddc1ca5790d5241612601038e72844` | PASS;42unique=24nonvoice+12pending+6accountfences |

Đã JSON.parse toàn bộ hai raw, kiểm expected Cartesian set chứ không chỉ đếm48/42; đối chiếu từng row asset hash với cả raw sourceLFHashes và file hiện trên đĩa. Cả hai raw có sourceHead đúng BASE và sourceState WORKTREE_CANDIDATE. Script ghi raw được đọc đầy đủ, SHA actual khớp scriptSHA:

- `browser-SDD4-TOGGLE.cjs`: `b3a869b8b1f1542b22f938d6d1a7ed96fd6c6164703322f3ea6b152e0678781c`.
- `supplement-SDD4-TOGGLE.cjs`: `310d393c9c7a5bf974e7bef001b25b77315033352e462e9d97fa2f822763c3bc`.

Đây là audit độc lập root browser artifacts, KHÔNG phải một lượt browser do Tester chạy mới. Runner dùng headless Edge/Playwright; Browser plugin không có trong phiên root. Hai localhost origins trong raw lần lượt `http://127.0.0.1:48150` và `http://127.0.0.1:58023`; không thử kết nối lại.

### Main48

- Viewports đúng `390×900`, `768×1024`, `1440×900`, `844×390`; VI/EN/ZH; light/dark; DUBBING_ONLY và SUBTITLE_PLUS_DUBBING.
- Mỗi active panel có đúng1switch, role=switch/type=checkbox, associated native label; locale text literal đúng. Script kiểm off0/on37, Space, manual1/100/37, invalid empty/-1/101/1.5, rangeHome0, edit focus và number/range/output/review đồng bộ.
- 48mode roundtrips,96Voice returns (saved+custom),48text2x geometry cases và48focus positive/inViewport/uncovered. Final mỗi row giữ original37%,dubbing200%,targetja/customISOpt-BR,mode/locale/theme; Combo controls được snapshot so sánh trong runner.
- Voice return URL dùng finite existing contract `?mode=<mode>&lang=<locale>`, không đòi query theme còn nguyên; actual theme/locale/control snapshot vẫn được so sánh đầy đủ. Mode roundtrip giữ fullURL exact. Đây là sửa QA expectation theo locked contract, không sửa app để vừa test.
- Min label target270×44px; min text contrast12.351554732138213:1, min focus contrast5.860080947953878:1;unknown background0. Verifier tự kiểm lại geometry2x: không clip, không overlap sibling, không vượt outer/clip bounds; raw overflow0 cả48.
- 192four-asset LF checks; errors/external/UIwrites đều0. Script block non-GET UI requests và foreign origin; QA register/login/profile setup là context.request riêng trên DB tạm, không được gọi là zero auth setup writes.

### Supplement42 và 401 classification

- Nonvoice24:2modes(subtitle_only/translated_subtitle)×3locale×2theme×390/1440,0visible switches trong khi2hidden Dub controls vẫn tồn tại. Script assert horizontal overflow0 từng case.
- Pending12:3locale×2theme×390/1440; giữ actual200 GETauth/me response lấy bằng `route.fetch()`, chỉ release/fulfill chính response đó. Không fakebootstrap/session/forceclick. Root ready=false,2switch tồn tại/0enabled; normal uncheck timeout và Tab không focus switch; sau ready off0/on100 hoạt động.
- Account6:3locale×2theme,390px; register/loginA thật, A37→off; loginB thật email khác và projection email khớp mỗi login; B100, không nhớ37; B53→off; logout thật; retained root1/switch2/0enabled và visible original100; realreloginB/newCSRF, on/off/on100, không restore53.
- `PageTransitionEvent('pageshow',{persisted:true})` chỉ kiểm handler diagnostic trên trang retained. KHÔNG phải native BFCache restoration.
- Đã xác nhận đúng6expected401Responses và6expected401Console, mỗi locale×theme đúng1/case, chỉ account-fence390. Response bắt buộc `GET /api/v1/auth/me`,status401; console bắt buộc exact URL `http://127.0.0.1:58023/api/v1/auth/me` và exact message `Failed to load resource: the server responded with a status of 401 (Unauthorized)`.
- Đọc code xác nhận boolean classification chỉ bật sau actuallogout200, trước persisted-handler GET, giữ qua realrelogin rồi kiểm delta exactly1response+1console mỗi case và tắt. Mọi401 khác đi vào errors; console khác exact URL/message đi vào errors. Không có broad ignore401.
- 168four-asset LF checks;unexpectederrors/external/UIwrites0. Account pacing31s tôn trọng register4/login8 per60s; không bypass auth/rate-limit.

## 4. Visual QA từ ảnh thật

Tester đã mở bằng view_image:

1. `QA/SDD4-green-1792851641552/light-DUBBING_ONLY-volume.png`.
2. `QA/SDD4-green-1792851641552/dark-SUBTITLE_PLUS_DUBBING-volume.png`.
3. `QA/SDD4-green-1792851641552/light-DUBBING_ONLY-viewport.png` (390px mobile context).

Quan sát: một checkbox native rõ nhãn “Giữ âm thanh gốc” nằm ngay trên original slider/number; cùng fieldset “Cân chỉnh âm thanh”, không thêm card/pill/placeholder rỗng. Original37 và dubbing200 hiển thị tách bạch, không tràn ngang; dark/light giữ navy/blue/teal. Ghi chú nói rõ mức chọn trên màn hình chưa áp dụng video khi xử lý chưa mở, không hứa provider/audio/file đã hoạt động. Focus ring rõ ở number. Target/contrast/keyboard dựa trên geometry/AX và runner assertions nêu trên, không suy đo chỉ từ PNG.

## 5. So sánh bảo vệ và source binding

| Asset trên đĩa cuối lượt kiểm | SHA256 UTF-8/LF |
|---|---|
| `static/portal/portal.js` | `bb0b90fb9d45eb310127e3177c06da7ba73034bf04801fa1b9ad440d4d3c9879` |
| `static/portal/portal.css` | `514dd76e2c6714fa49a6b19f9dfd672a5a7121fbbd8469b2a354893fd521e3b3` |
| `static/portal/portal-theme.css` | `59cfaa8dc6486c869377a431241dffdbbc2a0a52d16ded7448f7b61d4a9ee711` |
| `static/portal/integration.js` | `5ac46bc3fccdc893f73fa07efa3e0d56677606f2bf6d2617f5a540c5f8339912` |
| `tests/subdub-original-audio-toggle.test.mjs` | `aea083834c223436f0aa8f114b856c529d25e8222bf260264ad9643efd018a6d` |

- Packet gate tái dựng exact9records trên actualBASE, reverse LF vềBASE, parse candidate và so actualportal.js với candidate;17/19pre-render helpers whole-function exact,2exceptions đúng normalizer/volumeupdater. Không ghi source khi kiểm.
- `git diff --name-only BASE` phân loại source production chỉ `static/portal/portal.js`; mọi tracked production khác không có diff, gồm integration/auth/API/backend/CSS/i18n/motion. Không đổi Bot/provider/engine/wallet.
-676oldtests: computed Git blob IDs từng file sau CRLF→LF đều khớpBASE. Cần gọi chính xác Git/LF-exact:73working files raw-byte-equal GitLF blob,603khác chỉ do CRLF checkout. Không tuyên bố676raw-byte-exact. Không sửa oldtests để đạt candidate.
-5mainSFXfiles LF-exact so cảBASE vàmain`0e1b49b58f180f4ae9df6425df533419f66e55c4`: `copyfast_api.py`, `copyfast_db.py`, `copyfast_music_sfx_library_bridge.py`, `tests/test_webapp_r36_sfx_library_bot_parity.py`, `docs/migration/TEST_EVIDENCE.md`.
-6portable metadata entries trong `reports/migration/p0-05d-tester-workspace.json` đều được đo lại UTF-8/LF lines/bytes/SHA:2issue templates,case source,tester guide,sync script,portable test. Không chỉ tin metadata tự khai.
-48oldWArows exact soBASE;8SDD4 IDs đúng thứ tự01..08. Original spec18/10 unchanged,21SD IDs còn đủ. Historical42crosswalk rows (2tables×21) nguyên văn; có caption lịch sử để không ghi ngược kết quả E3.
-OriginalSD15 rõ “Bật/tắt, slider+number0–100%;preserve0”; currentdocs phân biệt native switch mới/restore-lastWeb100 Owner duyệt với Bot behavior, không gán fallback30 thành productiontruth. T0 upload/ASR/translation/profile/speaker/quote/job/mixing/output/delivery/reuse giữ mở; motionLAST,goalACTIVE.

## 6. Đối chiếu từng case và giới hạn

| Case | Tester verdict / bằng chứng |
|---|---|
| SDD4-01 | LOCAL PASS:48main/6newunit/focused80,local toggle0/37/bounds/invalid/dub0ack/200 |
| SDD4-02 | LOCAL PASS:48modeLoops/96saved-customVoiceReturns/snapshot/finiteURL contract |
| SDD4-03 | LOCAL PASS trong tested scope:48keyboard/focus/geometry2x,min44px/AA;3actualPNGs inspected |
| SDD4-04 | LOCAL PASS:24nonvoiceunique/0visible switches;không extra emptycard từ source/visual |
| SDD4-05 | LOCAL PASS:12held-actual-response pending,0enabled before ready,no fakeauth/forceclick |
| SDD4-06 | LOCAL PASS:6real-account fences,distinctemails/projectedidentity/retainedroot/disabledlogout/relogin100 not53 |
| SDD4-07 | LOCAL PASS:9records/reverseBASE/17helpers/676GitLFoldtests/RED6→GREEN6/fresh80/portable32 |
| SDD4-08 | Raw/source binding LOCAL PASS;final delivery/exactHEAD CI/receipt remains root gate,NOT_RUN by Tester |

NativeSafari/iOS,OStextscale,nativeBFCache,PWA/offline/SW,motion/performance/full-pageWCAG và realengine/filedelivery NOT_RUN. Text2x là label font-size geometry probe, không phải OS-wide text-scale proof. Không coi HTTP200/selectedlocalconfig là output success. Không claim wholeSD15audiooutput hoặc toàn21SD hoàn thành.

## 7. Canonical report

TASK=SD-D4;READY_FOR_SCOPED_LOCAL_ACCEPTANCE_ONLY;C0/I0/M0
BASE_SHA=ba4b2dfa1be096e35198e8bf60f3fa5596ed5af8
HEAD_SHA=ba4b2dfa1be096e35198e8bf60f3fa5596ed5af8;candidate=UNCOMMITTED_WORKTREE
FILES_CHANGED_BY_TESTER=_giao-viec/TESTER-46-SDD4-RESULT.md only
TESTS=FreshNode80pass0fail;portablePython32pass1deselected1warning;packet9records17helpersBASE6assert→candidate6pass;allcommandsExit0
BASELINE_FAILURES=ExpectedSDD4RED6assert0harness in same in-memory packet gate;fullbaseline80NOT_RUN
BRANCH_FAILURES=0 in fresh80/portable32/packet;browserrawunexpected0
NEW_FAILURES=0 for directly comparable packet6;freshfocused/portablefail0;nofull-baseline-comparisonclaim
PROTECTED_COMPARATORS=17helpers;676oldtestGitLFblobs;allothertrackedproduction;mainSFX5;48WA;6portablemetadata;21SD/T0/motionLAST PASS
PROVIDER_CALLS=0 byTester;browserartifactsforeignrequest0/local-onlyguard
WALLET_MUTATIONS=0
PRODUCTION_DATA_MUTATIONS=0
DEPLOY=NO
RUNTIME_SHA=NOT_TESTED
LIVE_PASS=NOT_TESTED
BLOCKERS=NONE for scopedlocalSDD4acceptance;delivery/exactHEADCI/receipt and broaderT0 requirements remain separate
LESSON_CANDIDATE=NONE;AUTO_PROMOTION=OFF

Root có thể chấp nhận localSD-D4 và tiếp tục gate docs/provenance/delivery được cho phép. Báo cáo này không tự cho phép merge/deploy, không đóng goal hoặc chuyển sang chứng minh engine.
