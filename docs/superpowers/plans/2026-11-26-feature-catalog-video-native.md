# Feature catalogue video native copy — implementation plan

> **For agentic workers:** use the existing Antigravity output-only proposals; root integrates and verifies. No worker may write the shared source or mutate Git/VPS.

**Goal:** Dịch đúng27mụcVideo cònthiếu trênroot `/features`,giữ135thẻvàmọichứcnăng.

**Architecture:** Thêm đúng dữliệubảndịch vào bộchữ nhẹ hiệncó.
Không đổi renderer/fallback,registry,auth hoặcAPI. Ba workerđộc lập
đã trả9records và35corrections;dùngnguyênvănbảnđãreview.

**Tech Stack:** FastAPI,vanillaJS/CSS,Node test,Playwright/Chrome cósẵn.

**Spec:** `docs/superpowers/specs/2026-11-26-feature-catalog-video-native.md`.

## Constraints

BASEccf824a1482ef3ae7fd2d4187932902e36ddbc14;Issue689;
27newkeys×VI/EN/ZH,108oldentriesheld;title≤70/description≤240Unicode;
noBot/engine/provider/wallet/PayOS/ENV/schema/data/auth/motion.
Giữ10stateuntracked,khôngđọc/canthiệpstatecampaign.

## Task1 — integrate reviewed data,2–5minutes

- [x] Sourceaudit/R1/R2/groupedcopyreviewvàRED87caseđãcó.
- [x] Tíchhợp9records từfrozenworkerreceipt vào
  `static/portal/portal-feature-catalog-copy.js`;before/afterhash ởspec.
- [x] Tạofixture `tests/fixtures/feature-catalog-video-native.json`
  cùngtest `tests/feature-catalog-video-native.test.mjs`,giữkỳvọngđãđóng.
- [x] Chạy `node --test tests/feature-catalog-video-native.test.mjs`
  →87pass/0fail/0skip;không gọi API/Git hoặc sửa dữliệu.

## Task2 — preserve inventory,2–5minutes

- [x] Testcũcustomer-card dùngexact135keys thay vìexact108,
  vẫn giữ108nonVideo/27Video vàpurity;chỉ thêmMP4/WEBMformat.
- [x] Chạy cùngtestmớivàaccounttaxonomy→0fail/skip;syntax/diffexit0.
- [x] Đăngkýchínhnodegroupnày trongCI;khôngđổiquyền/workflowdeploy.

## Task3 — actual rendered evidence,2–5minutes per view group

- [x] DùngactualrenderCatalogue/projectCatalogue/customerShell/CSS
  quaHTTP,chặnrequestngoài;không dùngDOMthiếucontextđểsửaứngdụng.
- [x]12viewVI/EN/ZH×light/dark×375/1440;native/source search,clear,
  Tab,focustarget44,khôngtràn/lỗi;đo màu thật vàmởảnhsáng/tối.
- [x] NếuQAhelpercómeasurementgapthìsửaQA/đothêm,khôngnhậnPASS
  hoặc tựđổipalette. CSSngoàiscope,phải cóRED/amendment/workerriêng.

## Task4 — deliver one complete batch

- [ ] Reviewgộpmộtlượt;docsvậnhành/featurecomparison/Tester/readiness.
- [ ] Explicitmanifest/secret/protectedgate→sourcecommit→Web-only
  provenancerefresh/evidencecommit/verify→pushmộtbranch/mộtPR.
- [ ] Exact-headCI2jobsSUCCESS→pinnedmerge/treeexact→exclusiveWeb
  deploy→runtime+assetsnhẹ/cũ→Issue689+PRreceiptsreadback.
- [ ] CậpnhậtchecklistNLRđãgiao/CVNthậttế;toàngoal/motionvẫnmở.
