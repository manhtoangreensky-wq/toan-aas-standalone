# WEBAPP V3 CUSTOMER PRODUCT IA & WORKFLOW INVENTORY AUDIT

> **Mã nhiệm vụ**: `P0.WEBAPP.V3.FULL.PRODUCT.IA.UX.ADMIN.REBASE.AUDIT`  
> **Chương trình**: `P0.WEBAPP.FULL.PRODUCT.TRUTH.REMEDIATION.V1`  
> **Repository**: `manhtoangreensky-wq/toan-aas-standalone`  
> **Trạng thái**: `CANONICAL AUDIT & REPLAN`  
> **Ngày lập**: 19/09/2026

---

## 1. TÁI CẤU TRÚC KIẾN TRÚC THÔNG TIN KHÁCH HÀNG (CUSTOMER IA REBUILD)

### 1.1. Vấn Đề Gốc Của Kiến Trúc Cũ
- **Phẳng hóa 135 tính năng ngang cấp**: Hiện tại khách hàng khi vào `/features` phải đối diện với một lưới khổng lồ 135 thẻ phân mảnh.
- **Rác kỹ thuật trong định hướng người dùng**: Các nhãn "Web-native", "Bot companion", "Đang bảo vệ", "Lập kế hoạch" gây rối loạn nhận thức, khiến người dùng không biết tính năng nào thực sự tạo ra sản phẩm.
- **Phân tán công cụ cùng mục đích**: Ví dụ công cụ Video bị chẻ nhỏ thành 27 mục rời rạc (Ý tưởng video, Kịch bản dài, Prompt planner, Motion planner, Storyboard composer...).

### 1.2. Thanh Điều Hướng Mục Tiêu (Target Customer Sidebar)
Thanh bên (Sidebar) của khách hàng được tái thiết kế tinh gọn gồm **13 mục sản phẩm có thứ bậc rõ ràng**:

```
[ TOAN AAS CREATOR SUITE ]

  🏠 TRANG CHỦ (Home / Overview)
  📁 DỰ ÁN (Projects / Active Workspaces)

── DÒNG SẢN PHẨM AI CHÍNH ─────────────────
  🎬 VIDEO SẢN PHẨM (Product Video Studio)
  🎙️ GIỌNG NÓI AI (Voice Studio & TTS)
  🎵 ÂM NHẠC & HIỆU ỨNG (Music & SFX)
  🌐 PHỤ ĐỀ & LỒNG TIẾNG (Localization & Dubbing)
  🎨 HÌNH ẢNH AI (Image Studio)

── BỘ CÔNG CỤ TIỆN ÍCH ────────────────────
  ✂️ CÔNG CỤ VIDEO NHANH (Manual Video / FFmpeg)
  🎁 TIỆN ÍCH MIỄN PHÍ (Free Tools & Prompts)
  📅 LỊCH XUẤT BẢN (Social Publishing & Schedule)

── KHO THÀNH PHẨM & TÀI KHOẢN ──────────────
  📦 KHO TÀI SẢN & THÀNH PHẨM (Outputs & Downloads)
  💳 VÍ XU & BẢNG GIÁ (Wallet, Topup & Pricing)
  ⚙️ TÀI KHOẢN & HỖ TRỢ (Account Settings & Helpdesk)
```

---

## 2. PHÂN LOẠI CHI TIẾT DANH MỤC 135 WORKFLOWS (WORKFLOW DISPOSITION)

Theo kết quả quét độc lập từ [`copyfast_registry.py`](file:///D:/TOANAAS/TOAN_AAS_WEB_APP/GitHub/copyfast_registry.py):
- **Tổng số tính năng trong Registry**: 179 tính năng.
- **Phân hệ Admin**: 40 tính năng (chỉ hiển thị cho vai trò Admin).
- **Phân hệ Khách hàng (Customer Visible Workflows)**: 139 tính năng (trong đó 4 trang hệ thống: `/`, `/login`, `/register`, `/features`, còn lại 135 thẻ hiển thị).

### 2.1. Thống Kê Phân Loại Theo Hướng Xử Lý Mới

| Nhóm Phân Loại | Số Lượng | Hướng Xử Lý |
|:---|:---:|:---|
| `PRIMARY_PRODUCT_ENTRIES` (Cửa ngõ sản phẩm chính) | **10** | Đưa lên Sidebar cấp 1 làm điểm đến chính |
| `PRODUCT_SUBTOOL` (Công cụ con tích hợp trong sản phẩm) | **45** | Tích hợp thành các tab/bước bên trong từng Studio |
| `SECONDARY_DISCOVERY_ONLY` (Khám phá thứ cấp) | **64** | Đưa vào tìm kiếm nhanh (Ctrl+K) và bộ lọc chuyên sâu |
| `MERGE_OR_CONSOLIDATE` (Gom nhóm trùng lặp) | **20** | Gom các thẻ tương đồng tính năng thành 1 giao diện duy nhất |
| **TỔNG CỘNG** | **139** | **Triệt tiêu hoàn toàn danh mục phẳng gây quá tải nhận thức** |

### 2.2. Bảng Chuyển Dịch Các Nhóm Tính Năng Trọng Yếu

#### A. Nhóm Video (27 tính năng cũ -> 1 Studio duy nhất `/video`)
- `video_factory_workflow`, `story_video_plan`, `video_studio`, `video_prompt_planner`, `video_idea_planner`, `cinematic_concept`, `storyboard_composer`, `image_motion_planner`, `creative_motion_guide`, `reference_format_planner`, `self_shot_scene_planner`, `script_to_screen_planner`, `long_form_roadmap`:
  -> **Gom lại thành Product Video Workspace** với luồng: *Idea -> Script -> Storyboard Multi-Scene -> Render Config -> Preview & Export*.

#### B. Nhóm Voice & Audio (20 tính năng cũ -> 2 Studio riêng biệt)
- `voice_studio`, `voice_direction_composer`, `voice_tts`, `voice_clone`, `voice_saved_tts`:
  -> **Voice Studio (`/voice`)**.
- `media_workspace`, `audio_hub`, `music_prompt_composer`, `music_direction_presets`, `sfx_cue_sheet`:
  -> **Music & SFX Hub (`/audio`)**.

#### C. Nhóm Phụ Đề & Dịch Thuật (8 tính năng cũ -> 1 Localization Hub `/localization`)
- `subtitle_studio`, `subtitle_asset_operations`, `subtitle_asr`, `subtitle_create`, `subtitle_translate`:
  -> **Localization Suite**: Phụ đề tự động, chỉnh sửa timeline, dịch kịch bản, lồng tiếng đa ngôn ngữ.

#### D. Nhóm Đăng Bài & Lịch Trình (30 tính năng Content cũ -> 1 Publishing Hub `/publishing`)
- `campaigns`, `calendar`, `approvals`, `content_ideas`, `caption_hashtag`:
  -> **Publishing & Social Hub**: Lịch đăng nội dung, quản lý chiến dịch, phê duyệt và theo dõi trạng thái đăng bài thực tế.

---

## 3. THIẾT KẾ DỮ LIỆU SẢN PHẨM KHÁCH HÀNG (CUSTOMER PRODUCT DATA DESIGN)

Mỗi không gian làm việc sản phẩm (Workspace) phải cung cấp đầy đủ **10 trường thông tin tiêu chuẩn**:
1. **Mã dự án (Project ID & Friendly Name)**: Ví dụ `PRJ-2026-VID-0089: Review Son Dưỡng Hạt Lựu`.
2. **Đầu vào gốc (Inputs)**: Text kịch bản, hình ảnh sản phẩm đính kèm, video tham khảo.
3. **Giai đoạn hiện tại (Stage)**: `Kịch bản` -> `Phân cảnh` -> `Tạo prompt` -> `Đang render` -> `Hoàn thành`.
4. **Báo giá minh bạch (Quote / Cost)**: Số Xu ước tính và số Xu đã khóa theo bảng giá niêm yết.
5. **Tiến độ trực quan (Progress)**: Thanh phần trăm và trạng thái từng cảnh (Scene 1: Done, Scene 2: 60%...).
6. **Thành phẩm xem trước (Outputs / Player)**: Trình phát MP4/MP3 độ trễ thấp ngay trên trang.
7. **Thông báo lỗi & Hướng xử lý (Errors & Next Actions)**: Báo rõ lý do nếu 1 cảnh bị lỗi và nút bấm 'Thử lại cảnh này'.
8. **Hành động tiếp theo (Next Action)**: Gợi ý rõ ràng: "Xuất file", "Tạo phụ đề", "Lên lịch đăng".
9. **Lịch sử phiên bản (Version History)**: Các lần chỉnh sửa kịch bản để khôi phục khi cần.
10. **Tài sản liên quan (Linked Assets)**: File giọng đọc đã dùng, file nhạc nền đã lồng.

### 3.4. Hỗ Trợ Tác Vụ Hàng Loạt (Multi-Item Bulk Operations)
Đối với các sản phẩm sản xuất hàng loạt (video ngắn, ảnh quảng cáo, bài viết), giao diện Web phải hỗ trợ:
- **Chọn nhiều mục (Multi-select)**: Checkbox chọn 5-20 video cùng lúc.
- **Xem trạng thái tổng thể (Bulk status)**: Bao nhiêu video đã xong, bao nhiêu video đang render.
- **Tải về dạng nén (Download Bundle)**: Tải toàn bộ video đã chọn dưới dạng 1 file .ZIP an toàn.
- **Thử lại hàng loạt (Batch Retry)**: Bấm 1 nút để render lại toàn bộ các cảnh bị lỗi timeout.
