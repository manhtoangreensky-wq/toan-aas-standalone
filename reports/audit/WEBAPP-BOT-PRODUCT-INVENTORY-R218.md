# R218 — Inventory nghiệp vụ Bot và gap UI/UX WebApp

2026-10-18. Nguồn Bot: `D:/TOANAAS/bot telegram`, chỉ đọc source.
CODE = có menu/handler/catalog; DESIGN = đặc tả; LIVE = chưa kiểm trong audit này.
Không đọc DB, token/secret, không chạy Bot/import hoặc gọi provider.

## Root coverage

`bot.py:72195 localized_main_menu_keyboard`: miễn phí, Video, Image, dịch, âm thanh,
tài khoản/bảng giá, AutoPost, Chat Pro, ghi chú/tài liệu, support/guide/feedback,
cộng đồng/đổi ngôn ngữ; Admin thêm theo quyền. Mỗi nhóm phải có Web disposition.
Commit Bot UNKNOWN; hash bot.py
`7eae9610073d3000c2a949e78e2e48e0194eb402eedea7f9b9328fa09d7f0b0f`.

## Ma trận sản phẩm

| ID | Nguồn CODE trong Bot | Chi tiết không được bỏ khỏi Web plan |
|---|---|---|
| B01 Voice | bot.py:169455 voice_hub_keyboard | TTS/STT, nữ/nam mặc định hoặc một default khi ID trùng, kho giọng, tạo giọng |
| B02 TTS | bot.py:159975; 160106..160211 | Text/đếm từ, speed 0.1–2.0x default 1.0, volume 0–200 default 100, cảnh báo 0, quote/confirm |
| B03 Voice Vault | bot.py:169187; 169226; 171866..171981 | List/page/status/default, nghe/tạo/tải/dùng cho video, đổi tên/xóa có xác nhận, stale profile |
| B04 Clone | bot.py:167782..167798; 169264; 174810..174915 | Consent → upload → xác nhận mẫu bằng text → tên 2–80 → quote → preview → lưu/kho |
| B05 Music | bot.py:169508; 171046; 171061; 162316..162388 | Nền/bài hát/kho/chỉnh nhạc, 3 tier, nam/nữ/song ca/auto, idea/style/tự nhập lời |
| B06 Music result | bot.py:162697..162873; 172488..172632 | 3 gợi ý/chọn/đổi/sửa, invoice, progress, file/player/save/reuse, delivery lỗi |
| B07 Music/SFX library | bot.py:169536; 172093..172136 | Search/filter, nghe/tải/chọn dùng, input nhạc/SFX cá nhân, empty/error |
| B08 SubDub | bot.py:234163; 234206 | Phụ đề gốc/dịch/lồng tiếng/combo; có/chưa có phụ đề; nguồn theo mode |
| B09 SubDub language | bot.py:234604; 236039; 236083 | Giữ nguồn hoặc dịch, Việt → Anh/Trung → các tiếng khác, tự nhận diện nguồn |
| B10 SubDub voice | bot.py:234652..234709; 236113..236161 | Default nữ/nam, đã lưu/tạo, Auto 2, Auto Multi 3–8, Smart Multi riêng |
| B11 SubDub mix/subtitle | bot.py:236533; 236591; 235906; 236005 | Âm gốc bật/tắt 0–100%; dub 0–200%; 7 vị trí phụ đề khi hỗ trợ; original/translated source |
| B12 SubDub report | services/product_progress_status.py:187; bot.py:234811 | Nhận/tách/nhận diện/dịch/tạo giọng/ghép/kiểm/giao; report, tệp, recovery |
| B13 Image root | bot.py:123989 main_image_keyboard | Tạo nhanh, prompt từ ảnh, AI edit, manual edit |
| B14 Image prompt/create | bot.py:60783..61135; 191497..191989 | Reference/goal/subject/style, 9 ratio ở prompt, 3 biến thể, 5 gợi ý tạo nhanh, 7 tier, watermark/quote |
| B15 Image AI/local edit | bot.py:61246..61625; 61777..62289 | AI thêm/xóa/nền/màu/biến thể; local crop/pad/blur, kích thước 128–4096, chữ/logo, sáng 20–200 |
| B16 Video root | services/video_uifreeze1.py:15; bot.py:93286 | Trend/AI/script/frame/selfshot/storyboard/series/idea/edit/downloader + nested reference/profile |
| B17 Video profile | services/video_profile_catalog.py:73 | 32 profile, nhóm 10/10/12, primary + liên kết; planning metadata |
| B18 Video AI edit | services/video_ai_edit_catalog.py:49,84 | 5 nhóm, 39 stable capability; detail/reference/mask theo từng lựa chọn |
| B19 Video manual | bot.py:91819..92525 | Cắt/chia/ghép/order, ratio/crop/fit/resolution, speed/rotate/flip, audio/text/SRT/logo/color/effects/export |
| B20 Video report | bot.py:273272 product_video_delivery_report_text | Product/tier/scenes/duration/ratio, addons selected/applied, quote/charge/delivery |
| B21 Dịch chung | bot.py:42324..42558 | Text/voice, nguồn/đích, hai chiều, input/output mode, start/stop/result |
| B22 Free | bot.py:71003; free_tools_hub.py:11 | Chat, Meta prompt, caption/hashtag/ideas, prompt ảnh/video, library, publish pack, lưu media/script/dịch/download |
| B23 Utilities | free_tools_hub.py:11 FREE_TOOL_TYPES | QR/avatar/tỷ giá/thời tiết; nguồn dữ liệu, stale/loading/error, không tự gọi external API trong audit |
| B24 Content | free_tools_hub.py:340..389; services/autopost_ui.py:87 | Idea/caption/hook/script/CTA, mục tiêu/kênh, nhiều lựa chọn, sửa/copy/save/version/handoff |
| B25 Memory | bot.py:123957; 186004..186090 | Create/list/search/detail/delete confirm/reminder, storage/quota/cleanup/add storage |
| B26 Documents | bot.py:123976; 184154..184416 | PDF→Word/ảnh→PDF/nén/tách/gộp; multi-file/order/range/compress/confirm/error/result |
| B27 Assets/Projects | Memory + kết quả từng sản phẩm; Web project model | Upload/list/search/preview/download/quota, draft/project/version, source→result lineage/reuse |
| B28 AutoPost root | services/autopost_ui.py:48 | Content/plan/brand/affiliate/channels/calendar/queue/published/metrics/ads/guide |
| B29 AutoPost input | services/autopost_ui.py:87 | 7 nguồn: topic/URL/affiliate/media/video TOAN AAS/image TOAN AAS/plan idea |
| B30 AutoPost detail | services/autopost_ui.py:132..321 | Brand edit/preview, channels/connect status, queue/history/metrics/settings, draft approve/publish |
| B31 Support | bot.py:60020..60528 | Intake, attachment, list/detail/reply/status/escalation, linked request/report, Admin assignment |
| B32 Account/price/topup | Root main_profile/pricing + Web contracts | Locale/profile/session/roles, packages/quote/history, manual topup status/admin review |
| B33 Help/Chat Pro/feedback | Root + public_chat_runtime, support flows | Context help/search, chat mode/usage/stop, feedback gắn record, community |
| B34 Admin/internal app | bot.py:230617 admin_module_keyboard; Web Admin model | Role/module/action visibility, customer task/job/report/audit, Workboard/plan/internal docs |

## Phát hiện thay đổi plan

1. SubDub V2 shared source/translation master nằm trong DESIGN docs; không báo
   implementation/runtime đã sử dụng chỉ dựa trên tài liệu.
2. Ba Auto callback riêng: `auto_speaker_gender`, `auto_multi_speaker`,
   `auto_smart_multivoice`. Web control hiện map tường minh qua `auto_two`,
   `auto_multi_3_8`, `smart_multi`; không gửi lane presentation thẳng vào API
   và không nhập ba engine thành một select mơ hồ.
3. `/voice-studio` không mặc nhiên là canonical Voice Vault. Web đang có
   `/voice/saved` và `/voice/clone`; cần xác minh handoff trả về sản phẩm gốc.
4. Dub volume Bot 0–200; Web local control đã hiển thị max 200, còn number binding,
   server capability và artifact evidence vẫn mở.
5. Bot Music edit `bot.py:172099..172105` chỉ trả guard; ghi capability gap.
6. Music parser nhiều track `164605` chưa chứng minh giao 2 bản; `172553..172589`
   hiện đưa một audio_bytes vào delivery. Yêu cầu 2 bản giữ NEEDS_CONTRACT_CONFIRMATION.
7. Music duration menu cũ 18/30/60/half/full không chứng minh reachable qua entry
   3-tier hiện hành `171046/171061`; không áp các giới hạn cũ vào mọi mode.
8. Video AI Edit mặc định production-disabled; series/long public locked trong
   video_uifreeze1.py:42. Đừng dùng có nút làm bằng chứng engine chạy.
9. Các chuỗi Bot pha tiếng Anh không là chuẩn copy Web; VI/EN/ZH phải biên tập riêng.
10. PR #654 candidate chưa render QA; disabled cards/map rỗng không là UI hoàn thiện.

## Không bỏ sót / giới hạn

Mỗi root B01–B34 phải có control ledger và Web route/action/disposition.
Mục chưa hỗ trợ: ghi UI gap hoặc T0, lý do và acceptance; không xóa khỏi inventory.
Danh sách này chốt nhóm và control chính từ source; kiểm từng callback động, quyền
và runtime catalog vẫn OPEN. Không tuyên bố “mọi nút Bot đã hoạt động”.

PR #654 là source/docs candidate chưa merge/deploy. LIVE_PASS=NOT_TESTED.
