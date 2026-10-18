# R218 — Checklist UI/UX toàn bộ sản phẩm WebApp

Ngày 2026-10-18. PLAN_IN_REVIEW. Source Bot được đọc-only; production chưa kiểm.
Không thay goal tổng; checklist này bổ sung và nối tiếp công việc R217 còn dở.
Từ ngày này, bảng dưới là completion ledger R218; lịch sử R217 giữ nguyên bằng chứng cũ.

## Quy ước

[x] Đủ evidence đúng phạm vi. [~] Một phần, chưa đóng. [ ] Chưa thực thi/chưa chứng minh.
[!] Có gap cụ thể. [→] Kỹ thuật giữ cuối, đợi lệnh sau UI/motion.
Bất kỳ mục không browser evidence không gọi là UX/LIVE hoàn thiện.

## C0 — Bảo toàn / chốt WIP

- [x] Root menu Bot và nhóm sản phẩm ghi tại WEBAPP-BOT-PRODUCT-INVENTORY-R218.md.
- [x] Đọc menu/handler/catalog chính cho Voice/Music/SubDub/Image/Video và tiện ích.
- [~] Các callback động và catalog runtime cần mapping control chi tiết, chưa đủ để
  tuyên bố audit mọi nút hoàn tất.
- [~] #653 auth responsive/contrast: CI source cũ xanh, delivery chưa đóng.
- [~] #654 candidate source đã push, CI đang sửa/check; UI lane chưa được review browser.
- [ ] Ghi current SHA/checks #653/#654 và disposition trước mở wave mới.
- [ ] Review #654 hidden field, default checked, duplicate selector, library link,
  guard blanket, locale, âm lượng dub max 100; chưa merge là hoàn tất.
- [ ] Toàn bộ plan/checklist/spec mới lên GitHub, provenance và CI candidate đạt.

## F0 — Shared contract R218-00/01

- [ ] Mỗi control có ID/source/label/position/input/default/guard/action/back/states/evidence.
- [ ] Typography/spacing/palette/contrast/touch/heading chuẩn, CTA chính rõ.
- [ ] Local config chỉnh được khi không sinh job; execution gate từ server.
- [ ] Back/mode change/hydration/reload giữ draft và focus đúng phiên.
- [ ] Upload/preview/result/history/recovery và cross-product picker thống nhất.
- [ ] Account change/logout xóa stale private data; UI quyền theo manifest thật.

## P1 — Voice R218-02 (VO-01..13)

- [ ] TTS/STT/default/saved/clone được bố trí trong workspace.
- [ ] Default nữ/nam distinct hoặc fallback một default theo capability.
- [ ] Nội dung/đếm từ/speed 0.1–2.0/volume 0–200 và cảnh báo volume 0.
- [ ] Quote/expiry/confirm/progress/player/download/report/retry đúng state.
- [ ] Kho giọng search/page/status/default/preview/rename/delete/reuse.
- [ ] Clone consent/upload/xác nhận text/name 2–80/quote/preview/save/back.
- [ ] Voice Vault dùng chung với SubDub/Video, owner scope/return draft.
- [ ] Renderer/interaction + browser/AX/screenshots đạt, không provider calls.

## P2 — Music R218-03 (MU-01..12)

- [ ] Nhạc nền/Bài hát/Kho nhạc-SFX/Chỉnh nhạc; capability thật.
- [ ] Brief/style/lyrics/vocal nam/nữ/song ca/auto/3 tier, không mất draft.
- [ ] Ba gợi ý chọn/đổi/sửa; quote/confirm/review rõ.
- [ ] Player/tải/save/reuse/history/progress và generation vs delivery failure.
- [!] Hai bản kết quả là yêu cầu cần contract confirmation; parser nhiều track
  không chứng minh Bot đã giao đủ hai bản.
- [!] Editor nhạc Bot hiện guard; UI không giả có editor thực thi.
- [ ] Duration/half/full chỉ options reachable, không chép menu legacy làm authority.
- [ ] Renderer/interaction + browser/AX/screenshots đạt.

## P3 — SubDub R218-04 (SD-01..21)

- [~] Shell một trang/bốn tab có source; chưa đủ bằng chứng UX toàn luồng.
- [ ] Source có/chưa có subtitle/upload/preview theo mode.
- [ ] Auto source, giữ gốc/dịch, target Việt/Anh/Trung + searchable catalog đầy đủ.
- [ ] Default Nữ/Nam; saved picker + custom Voice wizard, return đúng draft.
- [ ] Auto 2, Auto Multi 3–8 và Smart Multi riêng, mapping rõ callback/capability.
- [ ] Speaker map/preview/override chỉ khi có dữ liệu; ambiguous/review/fallback rõ.
- [ ] Original audio toggle 0–100, dub 0–200 và number+slider; preserve zero.
- [ ] Subtitle position/format/mono-bilingual/original-translated source/review.
- [ ] Quote/progress/result/report/download/recovery không giả.
- [ ] Review candidate #654 theo spec mới, không count thẻ disabled là hoàn tất.
- [ ] Renderer/interaction + browser/AX/screenshots đạt.

## P4 — Image R218-05 (IM-01..10)

- [ ] Tạo nhanh/prompt từ ảnh/AI edit/manual là 4 mode rõ.
- [ ] Reference goal/subject/style/ratio/negative prompt/3 biến thể.
- [ ] Tạo nhanh 5 gợi ý/tự nhập; 7 tier/watermark/quote/confirm.
- [ ] AI thêm/xóa/nền/màu/product/ratio/custom, phương án và readiness.
- [ ] Manual crop/pad/blur/pixel/text/logo/position/brightness/color/local upscale.
- [ ] Before-after/reset/history/save/reuse/Video, artifact readiness đúng.
- [ ] Renderer/interaction + browser/AX/screenshots đạt.

## P5/P6 — Các sản phẩm còn lại R218-06/07

- [ ] UT-01 Dịch text/voice/file/two-way/source-target/start-stop/result.
- [ ] UT-02 Content idea/caption/hashtag/hook/script/CTA/edit/save/version/handoff.
- [ ] UT-03 Free/prompt library/search/filter/copy/save/publish pack/quota.
- [ ] UT-04 QR/avatar/tỷ giá/thời tiết/downloader và stale/error states.
- [ ] UT-05 Notes create/list/search/detail/edit/reminder/delete confirmation.
- [ ] UT-06 Documents PDF→Word/ảnh→PDF/nén/tách/gộp, multi-file/order/range/result.
- [ ] UT-07 Assets upload/list/preview/download/quota/expiry/privacy.
- [ ] UT-08 Projects/Workboard task/dependency/status/assignee/dates/report.
- [ ] AP-01 Bảy nguồn nội dung AutoPost đúng source lineage.
- [ ] AP-02 Brand/content plan/draft/edit/preview/review/calendar/version.
- [ ] AP-03 Channels/platform/connection/expiry/target state.
- [ ] AP-04 Queue/published history/status/detail/cancel/review/recovery.
- [ ] AP-05 Affiliate/import/list/filter/ads/metrics, không fake số liệu.
- [ ] AC-01 Profile/locale/session/security và stale data cleanup.
- [ ] AC-02 Packages/pricing/topup/history/detail/pending, không wallet mutation.
- [ ] SP-01 Support/ticket/attachments/replies/status/escalation/task refs.
- [ ] SP-02 Guide/Chat Pro/feedback/community, context help đúng sản phẩm.
- [ ] Mỗi nhóm renderer/interaction + browser evidence, không chỉ navigation.

## A0 — Admin / nội bộ R218-08

- [ ] AD-01 Sidebar dọc/module/search theo quyền; Owner đủ, role khác theo policy.
- [ ] AD-02 Tables/list/mobile cards/detail/charts/legend/filter/empty-state.
- [ ] AD-03 Customer→Admin request/job/asset/report/audit reference đúng record.
- [ ] AD-04 Approval/finance UI có reason/review/error, money execution giữ T0.
- [ ] AD-05 Web và app cùng chức năng theo quyền, app ưu tiên công việc/mobile.
- [ ] Customer/admin/denied fixture browser matrix, không production mutation.

## V0 — Product Video và video tools R218-09 (làm cuối sản phẩm)

- [ ] VI-01 AI chân thật text/ảnh/scenes/brand/review.
- [ ] VI-02 Trend catalog/search/reference/source/suggestions.
- [ ] VI-03 Script AI/tự nhập/upload và scene editor.
- [ ] VI-04 Frame video source/order/cover/duration/fit/transitions/motion/audio/text.
- [ ] VI-05 Selfshot đổi cảnh/điện ảnh/timeline/preservation.
- [ ] VI-06 Storyboard grid/detail/source/prompts/addons/review.
- [ ] VI-07 Series/long bible/continuity/planning và khóa execution thật.
- [ ] VI-08 Idea/reference/library/profile/downloader/handoff.
- [ ] VI-09..12 Manual/AI/upgrade hub, timeline/segments/transforms/layers/exports.
- [ ] VI-13 39 AI edit options/5 nhóm, detail/reference/mask/preservation/readiness.
- [ ] VI-14 Upgrade chỉ hứa khả năng runtime đã chứng minh.
- [ ] VI-15 Addons selected/applied, quote/report/output/download/reuse.
- [ ] Đủ 32 profile/3 nhóm; catalog khác bộ legacy 12.
- [ ] Không claim CapCut parity từ toolbar; browser thao tác từng nhóm.

## Q0/M0/L0 — Nghiệm thu rồi motion, rồi báo cáo

- [ ] Inventory B01–B34 → control ledger; unclassified=0 hoặc ghi reason rõ từng mục.
- [ ] VI/EN/ZH sạch; dữ liệu user/tên riêng không bị dịch.
- [ ] Mobile 375/390/768/1440 × themes; shell/forms thêm 320/414/1024.
- [ ] Keyboard/focus/label/contrast/touch/overflow/empty/loading/error/recovery.
- [ ] Motion không bị hydration cắt/restart; route cleanup, reduced-motion.
- [ ] Trace/perceived loading: CLS/LCP/INP có số đo hoặc blocker cụ thể.
- [ ] CI đúng HEAD và authorized live SHA/DOM/screenshots/interaction đúng scope.
- [ ] Báo cáo UI/UX/motion, giữ goal chưa complete nếu requirements còn mở.
- [ ] Hết UI/UX/motion thì đợi lệnh cho T0.

## T0 — Kỹ thuật cuối, chưa triển khai

- [→] Canonical DTO/capability/catalog/Voice Library/speaker mapping.
- [→] Upload/quote/job/output bridge, paid providers và artifact delivery.
- [→] Backend RBAC/ABAC, cross-product references và mutation nghiệp vụ.
- [→] OAuth/publish/ads, wallet/PayOS/manual approval/ledger.
- [→] Mọi gap có trigger/input/authority/idempotency/audit/failure/evidence riêng.

PROVIDER_CALLS=0; WALLET_MUTATIONS=0; PRODUCTION_DATA_MUTATIONS=0.
MERGE/DEPLOY/LIVE không suy từ tests. Trạng thái delivery theo PR/checkpoint hiện tại.
