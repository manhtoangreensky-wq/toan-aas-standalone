# R218 — Checklist UI/UX toàn bộ sản phẩm WebApp

Ngày 2026-10-18. WIP_UTILITIES_CONTENT_PROJECTS_LOCALE_GREEN. Source Bot được đọc-only; production chưa kiểm.
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
- [x] #654 candidate source đã push; SubDub lane patch đạt kiểm thử local và CI/browser trên HEAD `148be4f6ec18e3c7fe3abfee8ca8a34ee1a5d099`.
- [x] Ghi current SHA/checks #653/#654 và disposition trước mở wave mới: Verify Web App + Authenticated WebApp QA SUCCESS, run `39101124230`, route matrix `456/456`.
- [x] Review #654 hidden field, default checked, duplicate selector, library link,
  guard blanket, locale, âm lượng dub max 100: đã sửa và khóa bằng 13 kiểm thử mục tiêu;
  CI/browser trên commit mới đã đạt route/render matrix.
- [x] Toàn bộ plan/checklist/spec đã lên GitHub; provenance được refresh cho HEAD mới và
  candidate gate đã xanh ở run `39101124230`.
- [x] VO-04/VO-05 Voice controls đã có candidate local `814b70cee2b6f4d2d1d2db23c903bfc0ca3d50bd`:
  tốc độ số `0,1–2,0` với mặc định `1,0` và 3 preset; âm lượng slider `0–200` đồng bộ
  với đúng một field số. Targeted `3/3`, Voice regression `97/97`, full Node `530/530`,
  `node --check` và `git diff --check` đều đạt; chưa có CI/live/runtime execution evidence.
- [x] MU-00 Music control-level local đã khóa: `/music/create` và `/music/song` dùng một
  workspace dọc gồm 4 bước, 3 tier và 3 ô phương án guarded; không còn provider badge, giá,
  player, MP3 hoặc download giả. Form song giữ `brief/tier/mode/vocal_mode/lyrics/song_length_mode/
  duration_seconds`; route nền cô lập các field song-only; trạng thái thiếu capability không tự
  mở field. Catalogue `musicProduct.*` cân bằng VI/EN/ZH; test mới `7/7`, focused Music+Voice
  `19/19`, focused Music hub/prompt/library `25/25`, full Node `537/537`, syntax và diff-check đạt.
  Đây chỉ là UI/control-level local; quote, confirm, generation, player/download/save/reuse,
  editor, delivery và browser/CI/live vẫn mở.

- [~] UT-02/UT-03/UT-05/UT-08 control-level đã được rà soát bằng bộ test cố định; riêng
  Content Prompt Pack đã loại các chuỗi tiếng Anh giao diện khỏi bản VI và tách catalogue
  VI/EN/ZH. Runtime tạo nội dung, lưu, phiên bản, dữ liệu thật, browser và live vẫn mở.

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
- [~] Nội dung/đếm từ/speed 0.1–2.0/volume 0–200: control và giá trị mặc định đã khóa
  bằng test `tests/voice-controls-contract.test.mjs`; cảnh báo volume 0 và quote stale
  vẫn chờ contract/runtime evidence.
- [ ] Quote/expiry/confirm/progress/player/download/report/retry đúng state.
- [ ] Kho giọng search/page/status/default/preview/rename/delete/reuse.
- [ ] Clone consent/upload/xác nhận text/name 2–80/quote/preview/save/back.
- [ ] Voice Vault dùng chung với SubDub/Video, owner scope/return draft.
- [ ] Renderer/interaction + browser/AX/screenshots đạt, không provider calls.

## P2 — Music R218-03 (MU-01..12)

- [~] MU-00 control-level local đã khóa theo C0; các mục runtime và delivery dưới đây chưa đóng.
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

- [x] Shell một trang/bốn tab, mode/query/keyboard và panel tại chỗ đã khóa bằng test presentation.
- [~] Source đã có lựa chọn “đã có/chưa có phụ đề”, bộ chọn tệp và trạng thái source rõ ràng;
  upload/preview/metadata/progress/cancel/replace/error vẫn chờ capability máy chủ.
- [~] Auto source mặc định tự nhận diện; target hiển thị catalog đầy đủ, Việt đứng trước rồi Anh/Trung;
  tìm kiếm runtime và giữ gốc/dịch theo DTO thật vẫn chưa có bằng chứng.
- [ ] Default Nữ/Nam; saved picker + custom Voice wizard, return đúng draft.
- [~] Auto 2, Auto Multi 3–8 và Smart Multi đã tách thành ba lane canonical riêng,
  mapping callback rõ; server capability/execution vẫn mở.
- [ ] Speaker map/preview/override chỉ khi có dữ liệu; ambiguous/review/fallback rõ.
- [~] Original audio toggle 0–100, dub 0–200 và number+slider; static dub max 200 đã có,
  number control/backend/browser evidence vẫn mở.
- [~] Subtitle position đã có đủ 7 slot cho các mode có phụ đề; format/mono-bilingual/original-translated
  source/review runtime vẫn mở.
- [ ] Quote/progress/result/report/download/recovery không giả.
- [~] Review candidate #654 theo spec mới: không còn count thẻ disabled là hoàn tất;
  lane selector/link/callback đã được kiểm thử static và CI/browser route/render; chưa có
  bằng chứng backend capability, upload, quote, job, result hoặc delivery.
- [ ] Renderer/interaction + browser/AX/screenshots đạt.

## P4 — Image R218-05 (IM-01..10)

- [~] Tạo nhanh/prompt từ ảnh/AI edit/manual đã có 4 mode dọc rõ trên `/image/create`;
  `prompt` nối `/image-studio`, `aiEdit` nối `/image/transform`, `manual` nối `/image/edit`.
  Đây mới là control-level projection; source/reference, AI runtime, upload, preview,
  before/after, quote, result và delivery vẫn chưa có bằng chứng.
- [ ] Reference goal/subject/style/ratio/negative prompt/3 biến thể.
- [ ] Tạo nhanh 5 gợi ý/tự nhập; 7 tier/watermark/quote/confirm.
- [ ] AI thêm/xóa/nền/màu/product/ratio/custom, phương án và readiness.
- [ ] Manual crop/pad/blur/pixel/text/logo/position/brightness/color/local upscale.
- [ ] Before-after/reset/history/save/reuse/Video, artifact readiness đúng.
- [ ] Renderer/interaction + browser/AX/screenshots đạt.

## P5/P6 — Các sản phẩm còn lại R218-06/07

- [ ] UT-01 Dịch text/voice/file/two-way/source-target/start-stop/result.
- [~] UT-02 Content idea/caption/hashtag/hook/script/CTA đã có workspace/brief/detail và
  Prompt Pack với gợi ý, trạng thái rỗng, ranh giới xử lý, lưu vào Ghi chú và locale VI/EN/ZH;
  edit/save/version/handoff runtime chưa có bằng chứng.
- [~] UT-03 Free/prompt library/search/filter/copy/save/publish pack/quota đã có các projection
  giao diện và trạng thái guarded; `Content Prompt Pack` fixed chrome đã cân bằng VI/EN/ZH,
  không trộn tiếng Anh ở bản VI; quota/runtime/provider chưa chứng minh.
- [ ] UT-04 QR/avatar/tỷ giá/thời tiết/downloader và stale/error states.
- [~] UT-05 Notes create/list/search/detail/edit/reminder/delete confirmation đã có Memory
  Center/Reminder shell, locale và contract owner-scoped; dữ liệu thật, browser và live chưa
  chứng minh.
- [ ] UT-06 Documents PDF→Word/ảnh→PDF/nén/tách/gộp, multi-file/order/range/result.
- [ ] UT-07 Assets upload/list/preview/download/quota/expiry/privacy.
- [~] UT-08 Projects/Workboard task/dependency/status/assignee/dates/report đã có Project
  Center, Workboard dọc, checklist, lịch, lịch sử và trạng thái; browser fixture/runtime chưa
  chứng minh.
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
