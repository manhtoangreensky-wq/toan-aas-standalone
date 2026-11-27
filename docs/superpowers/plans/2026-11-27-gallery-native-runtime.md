# Gallery Native Runtime Implementation Plan

> For agentic workers: Antigravity4ExtraHigh chỉ trả đề xuất; root giữ
> lifecycle/QA/Git/ship. Không giao Builder nội bộ thay Antigravity trước
> hai lần sai cùng acceptance. Các phiên độc lập không ghi source chung.

**Goal:** Danh mục, tìm kiếm, chi tiết, sao chép và ghi chú mới dùng cùng
một ngôn ngữ; nội dung và yêu cầu lưu cũ không bị sửa hoặc mất khóa retry.

**Architecture:** Finite static native leaf +117row packaged JSON; optional
strict lang query riêng Gallery; cache ownership RAM ngoài DTO, fences
locale/session/route/generation. Giữ canonical helper và API body cũ.

**Tech Stack:** FastAPI/Python; vanilla JS/i18n; pytest DB tạm; Node VM.

**Spec:** `docs/superpowers/specs/2026-11-27-gallery-native-runtime.md`.

## Global Constraints

BASE29e0c154; branchcodex/gallery-static-catalogue-20261127; snapshot2026-07-15.1.
Không Bot/engine/provider/wallet/PayOS/ENV/authmodule/SQL/schema/customerdata/motion.
No-lang legacy canonical giữ; vi/en/zh native chỉ khi có query hợp lệ.
DTO/IDs/snapshot/requestbody giữ; không cắt chuỗi để qua giới hạn.
Một PR cuối sau nghiệm thu; không PR trống hoặc phát hành data-only.
Mười state cũ giữ nguyên; không đọc file campaign state bị cấm.

## Task1 — khóa nguồn và RED

- [x] GSC-DATA:117row/351value, semantic root một lượt, machine0lỗi.
- [x] Impact:7file/26hits; public canonical helpers giữ nguyên.
- [x] `tests/test_gallery_native_locale.py`:14ca,13RED/1legacyPASS.
 Fake DB/secret child-only; TestClient cần loopback, không provider.
- [x] `tests/gallery-native-taxonomy.test.mjs`:54RED; actual renderer+i18n.
- [x] `tests/gallery-native-currentness.test.mjs`:49ca,34RED/15PASS;
 actual complete integration VM, deferred boundary only, không DB/network.

## Task2 — ba phiếu độc lập

- [x] GSC-LEAF: `copyfast_gallery_locale.py` + root mechanical data
 `gallery_static_locales.json`; module exact worker proposal,117row exact
 approved candidate. Verify pure420samples,0mutation/unknown rewrite/
 invalidlocaleaccepted, exit0. Không claim API runtime từ cổng này.
- [x] GSC-TAXONOMY-UI: đúng3worker edits ở portal.js/i18n;16key48value.
 Node54GREEN sau RED; syntax2JS+diffcheck0; machine byte-exact to proposal.
- [x] GSC-ACTIONS-DATA:23row69value; root semantic một lượt, machine0lỗi.
 Đã tích hợp cùng client; loading thêm1key/3value, tổng24key/72value.

Ba worker hiện có đều terminal0/1turn, modelgemini-4-hydrogen-xhigh.
Transport sandbox0turn/0token không tính lỗi worker; retry được phép
dùng mạng hiện có, không đăng nhập/settings mới.

## Task3 — hai miền source độc lập, một gate tích hợp

- [x] GSC-SERVER, Antigravity R1A sau root missing-spec:
 `copyfast_free_prompt_gallery.py` + `copyfast_memory.py`.
 Exact input source/leaf signatures trong phiếu; ba GET localize trước
 search/paginate, native taxonomy search, note chrome mới; query strict,
 legacy VI fingerprint replay và SQL/auth/CSRF giữ.
- [x] GSC-CLIENT, Antigravity R1A→R2→cachedR1/R1A:
 integration.js, đúng Gallery results-call trong portal.js, thêm finite
 feedback keys i18n. RAM owner/cache/URL/currentness, stale-copy/save,
 locale-qualified submission scope; loading không hiện empty giả.
- [x] Root đọc từng proposal một lượt, kiểm allowlist và protected diff,
 ghép cơ học; sai acceptance nào giao đúng lỗi đó R2, không sửa ké.
- [x] Backend GREEN:
 `python -m pytest --noconftest -q tests/test_gallery_native_locale.py`
 →14PASS trong QAchild; đối chiếu no-lang/legacy notes/strictbody.
- [x] Client GREEN:
 `node --test tests/gallery-native-currentness.test.mjs`
 →55PASS cuối saureviewcached-reselection và hai hướng controlđối xứng,
 thêmdeniedsavecounterexample. Taxonomy54 đã khóa, chỉ chạy lại nếu renderer/i18n delta mới
 ảnh hưởng; không lặp semantic/suite không đổi.
- [x] Kiểm backend affected legacy Gallery/Memory/PromptLibrary:
 34ca32PASS/2thiếu tzdata; hai ca BASE cũng fail cùng stack,0newfail.
 Không cài package hoặc sửa logic nhắc lịch ngoài scope.
- [x] Kiểm client affected; pin/history cũ
 chỉ mở finite QA amendment khi có RED thực nghiệm, không nới assertion.
 131ca124PASS/7fail→finiteleaf70pressurePASS→135affectedPASS/0fail;
 Pythonhistory51PASS. Không sửa fixture/pin/kỳ vọng cũ; chỉ project input.
- [x] Python transport finiteleaf75pressurePASS,11record exact;
 static/mount/stale8ca→7PASS/1BASEFAIL,cùng assertion line115 từBASE
 tái hiện trong RAM. Không sửa câu chữapp để qua assertion lịch sử.
- [x] Runtime/backend historical input sau consumerclosure:
 3161ca3121PASS/40FAIL ở28file; bổ sung finite11integration/7backend
 inverse trước targetguard,169pressurePASS rồi chỉ chạy40testname từngFAIL
 trong28file:40PASS/0FAIL/0SKIP/0ERROR,exit0.
 Không sửa ứng dụng/pin/expected và không chạy lại3121ca đã đạt.

## Task4 — bàn giao và phát hành đúng một lô

- [x] Browser localhost54views:390/768/1440,VI/EN/ZH,light/dark,keyboard,
 firstpaint/loading,clipboard/save parity/escaping;0provider/wallet.
- [x] Independent review đúng delta:backendC0/I0/M0;clientC0/I1/M0,
 findingcachedreuse được tái hiện RED và khép bằngworker+55GREEN;
 không audit lạiPR818 hoặc giả có lượt reviewtoànbộ thứhai.
- [x] Actual mounted app3locale390px:filter→detail→clipboard→newMemorynote,
 profile-first signed shell; DB/secret giả child-only,externaldeny.
 Lượt đầu VI/EN fullflowPASS; ZH dừng ở runnerkhai báolangzh thayzh-CN,
 logo nội bộ thiếuallowlist. Chỉ sửa QAtools,không tính app/workerfailure;
 Sau toolfix terminal0,3flowPASS/0unexpected/0pageerror/0consoleerror;
 mỗi account0→1note,display/clipboard/note exact,serverexit0.
 Evidence `gallery-mounted-KIuDXw/summary.json`;không suy signedproduction.
- [x] CI wiring:chỉ thêm hai native test runlines;YAML/byteguardexit0,
 trigger/permissions/env/deploy giữ. Chưa có exact-headCI result.
- [x] Cập nhật current operations/initial comparison/master/Tester/
 readiness bằng evidence; thêm PR818DELIVERED recap trong cùng lô.
- [ ] Finalmanifest/sourcecommit vàWeb-onlyprovenance,không thaypublicationgate.
- [x] Owner duyệt riêng đúngfile;runtimecontract7219170926 đã công bố
 vàreadbackexact16416ký tự,không bypass rejection.
- [ ] Explicit stage đúng manifest, commit/push một nhánh/PR, exact-headCI.
- [ ] Merge→Web-onlydeploy→runtime SHA/services→assets/cache→receipt readback.
- [ ] Signed-production exact behavior có bằng chứng riêng hoặc để mở;
 public asset parity không được thay cho LIVE PASS.

Chưa tick Task3/4 thì không báo toàn Gallery locale hay toàn goal hoàn thành.
Admin/actionBlockReason/authdraft/device/Safari vẫn theo checklist mẹ;
motion chỉ xử lý ở cuối.
