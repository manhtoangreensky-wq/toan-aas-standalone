# Customer Language Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tài khoản và chọn ngôn ngữ dùng lời tự nhiên,giữ đủ cách sử dụng.

**Architecture:** Chỉ sửa giá trị dịch và hai vùng renderer sẵn có. Antigravity
trả đề xuất cô lập;Root giữ trách nhiệm ghép,kiểm và bàn giao từng bước.

**Tech Stack:** FastAPI + vanilla JavaScript/CSS;Node renderer tests.

**Spec:** `docs/superpowers/specs/2026-11-28-customer-language-cleanup.md`

## Global Constraints

BASE2817dd9d221e04aa45945165ae60d5838cf9d920;nhánhcodex/customer-language-cleanup-20261128.
KhôngBot/route-engine/provider/ví/PayOS/ENV/dữliệuthật/motion.
Chỉthêm1khóangônngữ,mọitrường/quyền/action/route/dữliệugiữ.
Khôngcài phụ thuộc,khôngmởđăngnhập/kiểmtàikhoảnCLI,khôngtựrefactor.

### Task 1 — Chứng minh lỗi trước sửa

**Files:** Create `tests/customer-language-cleanup.test.mjs`.
**Interfaces:** Dùng renderer vật lý từpublishing-child-render.mjs;BASElấy
Gitimmutable,khônginverse.Rawprimarymớisẽđọctrựctiếpmãứngdụng.

- [x] Viết các caseaccountunlinked/linked,setup,languagevi/en/zhcóquyền/
  bịkhóa;so controls/context/commands vàtừngnhómlờitheospec.
- [x] Chạy `node --test tests/customer-language-cleanup.test.mjs`.
  Mongđợi failđúngWeb/Phiên/dònggradient/vùnggiảithích/titleCSRF,
  khônglỗithuhậphoặcfixturekhôngđúngnormalizer.

### Task 2 — Giao ba phần độc lập

**Files:** Modify `static/portal/portal-i18n.js`;
`static/portal/portal.js:renderAccount`;
`static/portal/portal.js:renderInterfaceLocaleNavigator`.
**Interfaces:** Giữnguyênchữkýhàm,uiText/accountCenterText,capabilities
và3giátrịradio.Tên/câucụthểđãđủtrongspec,kèmtoànMAPmỗi phiếu.

- [x] CL-ACCOUNT-LABELS:trả10before/afterVI/EN/ZH,tấtcảgiátrịkhácgiữ.
- [x] CL-ACCOUNT-DEFAULT-ROW:trảđúngmộteditxóadòngaccountRow
  cóprofileDefaultsLabel;khôngsửa profileValues/biểu mẫu.
- [x] CL-LANGUAGE-SELECTOR:trảmộteditđủhàmhiệncóvà5khóacũ/1mới,
  thực hiệnđúngcácvùnggiữ/bỏtrongspec;khôngđổihàmnào khác.
- [x] Kiểmmộtlượtsaukhiworkerxong;`node --test tests/customer-language-cleanup.test.mjs`
  phảiqua,cácspecsaichỉgiaođúngphầnsaitốiđa2lượtcùngtiêuchí.

### Task 3 — Ghép và kiểm giao diện

**Files:** Hai tệpứngdụngnêutrên;testmớivàinputreaderlịchsửchỉkhifailđãđo.
**Interfaces:** Giữrecordbefore/aftervàhashđúngnguồn;khôngnớifixture/
pin/assertioncũ.Rawprimarymớikhôngdùnginverse.

- [x] Rootghépcơhọcđềxuấtđãrà;kiểmsyntaxvàgitdiff--check.
- [x] BrowserHTTPcôlập390/1440sáng/tốiVI/EN/ZH:nút/nhãn/disabled,
  chọnradio/gõônhập,fieldsets/ARIA/footerđúng,khôngtràn/lỗi/egress.
- [x] Chỉthêmepochhữuhạnchoreadercũthựcsựbịảnhhưởng;testpressure
  thiếu/đổi/lặpvàgiữnộidunglạ.Khôngchạylạinhómđãđạt vôích.

### Task 4 — Bàn giao đợt gọn

**Files:** Spec/plan,masterR217,TAI-LIEU01/02,KIEM-THUcase/guide/
manifest,prepush,metadata đãđo;Webprovenancechỉsauchốtnguồn.

- [x] Ràđộclậpđúngđềxuấtđãxongmộtlượt,cậpnhậtbằngchứng/tài liệu.
- [ ] Nguồnđãkiểm→commit→refresh2Webprovenance→mộtPRcùngIssue689.
- [ ] ĐúngHEADCIđạt→mergeđúngcây→exclusiveWeb-onlydeploy→runtime/
  dịchvụ/tài nguyên→receiptđọc lại đúng.KhôngdừngởmergehoặcHTTP200.
- [ ] Giữmọimụccònmởcủagoal;khôngđóngtổngvìriêngđợtnàyđạt.
