# R218-05/09 — Image và toàn bộ Video

Video làm sau Voice/Music/SubDub/Image/các sản phẩm còn lại.
Allowed UI: static/portal/portal.js, portal-i18n.js, portal.css, product tests/docs.
Bot/backend/provider/wallet/auth contracts protected. Inventory B13–B20 là nguồn.

## Image: 4 chế độ trong workspace

| ID | Control/vị trí | Hành vi / state cần nghiệm thu |
|---|---|---|
| IM-01 | Tab Tạo ảnh / Câu lệnh từ ảnh / Chỉnh AI / Chỉnh thủ công | Một trang, nguồn/ảnh không mất khi đổi bước |
| IM-02 | Source picker/upload/reference + preview | Vai trò ảnh, MIME/size, remove/replace, ownership/failed upload |
| IM-03 | Goal/subject/style | Chọn từ gợi ý hoặc tự nhập; không trộn yêu cầu user với template |
| IM-04 | Prompt/negative prompt và biến thể | 3 biến thể prompt, chọn/sửa/copy/lưu/handoff; prompt không là ảnh đã tạo |
| IM-05 | Tạo nhanh | 5 gợi ý hoặc tự nhập; preview prompt; ratio/tier hiện hành |
| IM-06 | Ratio / tier / watermark | 9 ratio ở prompt builder theo source; 7 tier create; logo text/image/position |
| IM-07 | AI edit inspector | Thêm/xóa vật thể, background/color/product/advertising/ratio/custom, 3 phương án |
| IM-08 | Manual toolbar/inspector | Crop/pad/blur; pixel preset/custom 128–4096; text/logo/position; brightness 20–200/color/local upscale |
| IM-09 | Before/after + apply/reset | Giữ original, state selected/loading/failed, không gọi local upscale là AI upscale |
| IM-10 | Review/quote/confirm/result/history | Matching job, image thật/download_ready, tạo biến thể/tiếp tục sửa/đưa Video |

### R218 Image control checkpoint — 18/10/2026

`/image/create` hiện có một cụm điều hướng dọc gồm đúng bốn mode theo IM-01:

1. `create` → `/image/create`: mô tả ý tưởng, tỷ lệ và báo giá theo capability thật;
2. `prompt` → `/image-studio`: chọn ảnh tham chiếu trong Kho tài sản và soạn định hướng;
3. `aiEdit` → `/image/transform`: mô tả thay đổi trên ảnh nguồn, giữ trạng thái chờ quyền máy chủ;
4. `manual` → `/image/edit`: chỉnh màu/độ nét/thông số ảnh riêng tư, không gọi AI.

Đây là projection UI/UX, không phải bốn engine đã mở. Ba mode ngoài `create` dùng trạng thái
`guarded`, không tạo upload, preview, ảnh, quote, job, tệp, provider call hoặc thay đổi Xu.
Source/reference, AI edit runtime, before/after, giao tệp và browser/live evidence vẫn mở
theo IM-02 và IM-07..10.

Bot anchors: bot.py:123989,60783..61135,61246..61625,61777..62289,191497..191989.
Web phạm vi upload/reference/entitlement phải đọc hợp đồng thực tế, không tự mở backend.

## Video: lựa chọn sản phẩm đầu tiên, cấu hình giữ trong workspace

| ID | Lane / nguồn | Vùng chính và control cần có |
|---|---|---|
| VI-01 | AI chân thật, bot.py:93309 | Text/ảnh → chủ thể/bối cảnh/cảnh/prompts → brand/review/tier/quote |
| VI-02 | Trend, 107830..108909 | Catalog/search/tự nhập/video tham khảo; phân tích mẫu/source; scenes/ratio/profile/suggestions/preview |
| VI-03 | Kịch bản, 93330/87310..89300 | AI/tự nhập/upload; script scene editor, source per scene/profile/character/preservation/audio/transitions/text |
| VI-04 | Ghép ảnh, 177950..178037 | Thumbnail order/replace/remove/cover, duration chung/từng ảnh, ratio/fit, 5 transition/6 motion/4 fit/3 quality, text 3×3 |
| VI-05 | Tự quay, 110285..110945 | Đổi cảnh/biến đổi điện ảnh; timeline, giữ mặt/vóc dáng/chuyển động, reference, mong muốn thay đổi |
| VI-06 | Storyboard, 85741..86084 | AI/upload, số khung/ratio, grid/scenes/detail, prompts/source/addons/review/quality |
| VI-07 | Series/long, 93458 | Tập/bible/continuity/assets/scenes/review; planning riêng, không claim render nếu locked |
| VI-08 | Ý tưởng/reference/library/downloader, 93478..93565 | Search/category/detail/copy/save/import/link, handoff đúng lane và nguồn |
| VI-09 | Edit hub, 90523 | AI / Thủ công / Nâng chất lượng riêng; source info duration/res/fps/audio/format |
| VI-10 | Manual, 91819..92525 | Preview + segment/timeline + inspector; cut đầu/cuối/giữa, split, merge/order, ratio/crop/fit/720p/1080p |
| VI-11 | Manual transforms | Speed .5/.75/1/1.25/1.5/2, rotate 0/90/180/270, flip, brightness 20–200/color |
| VI-12 | Manual layers | Music/voice/SFX/volume/remove track/loudness, text/SRT/logo/watermark/position/effects theo capability |
| VI-13 | AI edit, catalog.py:49,84 | 5 nhóm, 39 options; multi-select/detail/reference/mask/old→new text, preservation/strength/ratio/duration/timing |
| VI-14 | Upscale/upgrade | Khả năng runtime thật; không hứa stabilization/denoise/restore nếu chưa chứng minh |
| VI-15 | Addons/review/result, bot.py:273272 | Voice/music/SRT/dub/logo có source tự có/tạo mới, selected vs applied, quote/report/download/history/reuse |

## Profile video: phải giữ đầy đủ catalog

`services/video_profile_catalog.py:73 PROFILE_SEEDS`: 32 loại, 3 nhóm 10/10/12.
Picker có search/filter, một profile chính và liên kết hỗ trợ theo giới hạn (MAX_LINKED_PROFILES=2).
Không dùng bộ legacy 12 làm danh mục đầy đủ.

sales_ads, product_review_demo, affiliate_ugc, testimonial_case_study, brand_corporate,
social_creator_trend, meme_parody_comedy, event_highlight, news_data_analysis,
podcast_interview_talking_head, storytelling_life, short_film_trailer, tutorial_howto,
knowledge_explainer, history_culture_mythology, philosophy_morality, motivation_self_help,
kids_education, documentary_series, asmr_relax_lofi_visualizer, architecture_interior_renovation,
real_estate_place_walkthrough, fashion_beauty_lookbook, food_cooking_asmr, travel_local_experience,
sports_esports, app_website_saas, game_trailer, engineering_industry_automation,
product_3d_showcase, character_animation_vfx, music_video_performance.

## AI edit catalog coverage

Scene: background/location/lighting/weather/day_time/season/overall_color/mood/luxury/modern/clean/custom.
Person: replace/outfit/outfit_color/accessory/appearance_reference/hair/custom.
Object: add/replace/remove/color/accessory/prop_replace/character_add/custom.
Style: cinematic/realistic/anime/3d/comic/art/advertising/custom.
Other: text_replace/detail_add/detail_remove/custom_request.
Stable IDs từ catalog là authority; mỗi lựa chọn cần detail field và capability state riêng.

## UI acceptance

Không nhồi toàn bộ options vào hàng ngang. Nhóm dọc và disclosure; inspector chỉ
hiện options của selected operation. Thumbnails có keyboard move-up/down thay drag-only.
Draft undo/reset giữ original; Preview là preview, Export chỉ khi readiness/quote hợp lệ.
Manual editor không được báo ngang CapCut chỉ vì toolbar tồn tại.
AI capability mặc định production-disabled; long/multiscene public locked phải hiển thị đúng.

Phiếu IM-A modes → B source/options → C editor → D quote/result → E browser.
Video-A catalog → B mỗi lane VI-01..08 → C manual → D AI → E addons/report → F browser.
Verify targeted tests cho hành vi và protected DTO, browser 375/390/768/1440 sáng/tối VI/EN/ZH.
