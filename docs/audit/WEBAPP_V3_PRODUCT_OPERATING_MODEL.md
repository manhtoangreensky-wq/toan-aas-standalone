# WEBAPP V3 PRODUCT OPERATING MODEL — CANONICAL ARCHITECTURE AUDIT

> **Mã nhiệm vụ**: `P0.WEBAPP.V3.FULL.PRODUCT.IA.UX.ADMIN.REBASE.AUDIT`
> **Chương trình**: `P0.WEBAPP.FULL.PRODUCT.TRUTH.REMEDIATION.V1`
> **Repository**: `manhtoangreensky-wq/toan-aas-standalone`
> **Trạng thái**: `CANONICAL AUDIT & REPLAN (AUDIT_AND_REPLAN_ONLY)`
> **Ngày lập**: 19/09/2026
> **Quy chuẩn**: `owner-governed-codex`, `toanaas-system-design-and-open-apis`

---

## 1. NGUYÊN TẮC VẬN HÀNH CỐT LÕI (OWNER OPERATING MODEL)

Hệ sinh thái TOAN AAS Web App chuyển dịch triệt để từ mô hình **phẳng hóa 135 tính năng kỹ thuật** sang mô hình **các dòng sản phẩm độc lập (Distinct Product Families)**.

### 1.1. Triệt Tiêu Khái Niệm Phân Tuyến Kỹ Thuật Ở Giao Diện Khách Hàng
Khách hàng không bao giờ cần biết hoặc quan tâm đến các khái niệm sở hữu kỹ thuật như:
- `Web-native` (Xử lý tại Web)
- `Bot companion` (Đồng hành Bot)
- `canonical reader` (Đọc canonical)
- `guarded adapter` (Đang bảo vệ / Tạm dừng)

Các khái niệm trên **chỉ được phép lưu hành dưới dạng chẩn đoán nội bộ (internal diagnostics)** dành riêng cho Admin hoặc System Health. Giao diện khách hàng chỉ tập trung vào **giá trị nghiệp vụ và kết quả đầu ra (Outputs)**.

---

## 2. 10 DÒNG SẢN PHẨM MỤC TIÊU (TOP-LEVEL PRODUCT BOUNDARIES)

Thay vì một danh mục dàn trải 135 thẻ không phân cấp, Web App quy hoạch thành 10 dòng sản phẩm chuẩn:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        TOAN AAS PRODUCT ECOSYSTEM                      │
├───────────────────┬───────────────────┬────────────────────────────────┤
│ 1. PRODUCT VIDEO  │ 2. VOICE STUDIO   │ 3. MUSIC & SFX                 │
├───────────────────┼───────────────────┼────────────────────────────────┤
│ 4. LOCALIZATION   │ 5. MANUAL TOOLS   │ 6. AUTOMATED PUBLISHING        │
│ (Sub/Dub/Trans)   │ (FFmpeg Local)    │ (Multi-platform Social)        │
├───────────────────┼───────────────────┼────────────────────────────────┤
│ 7. IMAGE TOOLS    │ 8. FREE TOOLS     │ 9. PROJECTS & OUTPUTS          │
├───────────────────┴───────────────────┴────────────────────────────────┤
│ 10. ACCOUNT, WALLET & COMMERCE (Ví Xu, Gói Dịch Vụ & Đối Soát)        │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 3. PRODUCT VIDEO: XÂY DỰNG SẢN PHẨM KHÉP KÍN (END-TO-END PRODUCT)

### 3.1. Sự Thật Nguồn Hiện Tại (Current Source Fact)
- `copyfast_video_studio.py` (10.215 dòng, 37 routes) **chỉ sở hữu metadata lập kế hoạch (PLANNING-ONLY)**.
- Dòng 1-8 ghi nhận rõ ràng:
  > *"This router owns planning metadata only: a video brief, ordered scene board, self-review lifecycle and immutable revision history... It deliberately does not accept media, source URLs, engine configuration, delivery records or any execution request. A saved plan is never evidence that a video exists."*
- Hệ quả: Khách hàng lên kịch bản trên Web nhưng **không thể tạo Job, không thể render video, không có tiến độ thực tế, không nhận được file MP4 và không thể tải về**.

### 3.2. Ma Trận Khoảng Trống 25 Điểm Vòng Đời (Lifecycle Gap Matrix)

| STT | Bước Vòng Đời | Hiện Trạng Web | Hiện Trạng Telegram Bot | Khoảng Trống Cần Khép Kín Trên Web | Đánh Giá Nguồn |
|:---:|:---|:---|:---|:---|:---:|
| 01 | **Brief / Input** | Form cơ bản trong Video Studio | Q&A hội thoại tuần tự | Web cần bộ gợi ý AI brief theo ngành hàng | `SOURCE_VERIFIED` |
| 02 | **Product Assets** | Text links tham chiếu | Upload media qua chat | Cần S3/Local Vault drag-drop nhiều ảnh/video | `SOURCE_VERIFIED` |
| 03 | **Reference Material** | Ghi chú văn bản | Tải & phân tích link TikTok/YouTube | Cần nhúng phân tích hook/cấu trúc video tham khảo | `SOURCE_VERIFIED` |
| 04 | **Scene Generation** | Mẫu cố định tĩnh | LLM phân rã cảnh động theo sản phẩm | Cần engine LLM sinh prompt từng scene trên Web | `SOURCE_VERIFIED` |
| 05 | **Scene Ordering** | Mảng số nguyên | Kịch bản tuyến tính | Cần visual drag-and-drop scene storyboard | `SOURCE_VERIFIED` |
| 06 | **Prompt Generation** | Template ghép chuỗi | Compiler Veo/Kling/Sora chuẩn hóa | Đồng bộ compiler prompt từ Bot sang Web | `SOURCE_VERIFIED` |
| 07 | **Duration** | Trường nhập text | Ràng buộc 5s, 10s/scene theo engine | Khóa chặt thời lượng theo năng lực provider | `SOURCE_VERIFIED` |
| 08 | **Aspect Ratio** | Dropdown (9:16, 16:9, 1:1, 4:5) | Enforce nghiêm ngặt theo model | Cần khung preview tỷ lệ khung hình trực quan | `SOURCE_VERIFIED` |
| 09 | **Voice** | ID chuỗi opaque | Menu chọn giọng, nghe thử MP3, TTS | Cần bộ chọn giọng có player nghe thử tích hợp | `SOURCE_VERIFIED` |
| 10 | **Music** | ID chuỗi opaque | Thư viện nhạc, auto-cue, ducking | Cần bộ chọn nhạc nền và thanh cân bằng âm lượng | `SOURCE_VERIFIED` |
| 11 | **Subtitle** | Checkbox boolean | Whisper ASR, sinh SRT, burn-in ASS | Cần editor chỉnh sửa text phụ đề và font chữ | `SOURCE_VERIFIED` |
| 12 | **Render Options** | Enum không thực thi | Chọn chất lượng (Standard, High, Master) | Kết nối tùy chọn render với bảng giá Xu | `SOURCE_VERIFIED` |
| 13 | **Quote** | Ước tính mô phỏng tĩnh | Tính giá canonical (cảnh × giây + addon) | Web phải phát hành `quote_receipt` có thời hạn | `SOURCE_VERIFIED` |
| 14 | **Confirmation** | Chưa có | Modal xác nhận 2 bước chống bấm nhầm | Cần modal kiểm tra số dư Xu + xác nhận trừ tiền | `SOURCE_VERIFIED` |
| 15 | **Job Creation** | Nghiêm cấm trong video_studio | Thêm bản ghi `video_jobs` có atomic lock | Web phải gọi Core Bridge tạo Job chuẩn xác | `SOURCE_VERIFIED` |
| 16 | **Provider Exec** | Chưa có | Điều phối Veo/Kling/ShopAIKey worker | Worker VPS xử lý task theo hàng đợi ưu tiên | `RUNTIME_VERIFIED` |
| 17 | **Scene Progress** | Log mô phỏng | Polling trạng thái realtime từng cảnh | Web visualizer hiển thị % tiến độ từng scene | `SOURCE_VERIFIED` |
| 18 | **Retry / Recovery** | Chưa có | Fallback chain khi provider lỗi | Nút 'Thử lại cảnh lỗi' mà không phải chạy lại cả video | `SOURCE_VERIFIED` |
| 19 | **Finalizer** | Chưa có | FFmpeg ghép cảnh + voice + music + sub | Tiến trình ghép file hoàn thiện trên worker | `RUNTIME_VERIFIED` |
| 20 | **Preview** | Chưa có | Gửi video preview nén qua Telegram | Trình phát video Web xem trước tức thì | `SOURCE_VERIFIED` |
| 21 | **Final MP4** | Chưa có | Lưu file MP4 gốc độ nét cao | Lưu trữ bền vững tại `/opt/toanaas/storage/outputs` | `RUNTIME_VERIFIED` |
| 22 | **Download** | Chưa có | Link tải document không nén | Nút tải trực tiếp MP4 trên trình duyệt Web | `SOURCE_VERIFIED` |
| 23 | **Delivery** | Chưa có | Ghi nhận biên lai giao hàng thành công | Đánh dấu trạng thái `delivered` minh bạch | `SOURCE_VERIFIED` |
| 24 | **Billing State** | Chưa có | Trừ Xu đúng 1 lần sau khi giao MP4 | Khóa trừ Xu khi thành công; 0 Xu khi lỗi | `SOURCE_VERIFIED` |
| 25 | **History / Clone** | Lịch sử nháp | Nhân bản dự án, chỉnh sửa kịch bản | 1-click 'Nhân bản & tạo biến thể mới' | `SOURCE_VERIFIED` |

### 3.3. Lợi Thế Cốt Lõi Của Web (The Web Advantage)
Web không được sao chép máy móc giao diện chat Telegram. Trải nghiệm Product Video trên Web phải khai thác triệt để không gian màn hình:
1. **Quan sát đồng thời nhiều phân cảnh (Multi-scene simultaneous visibility)**: Xem toàn bộ storyboard 5-10 scene trên 1 màn hình.
2. **Chỉnh sửa hàng loạt (Bulk scene edits)**: Thay đổi phong cách, ánh sáng, góc máy cho toàn bộ cảnh chỉ bằng 1 thao tác.
3. **Kéo thả sắp xếp (Drag & reorder)**: Thay đổi thứ tự cảnh trực quan.
4. **So sánh phương án (Side-by-side preview)**: Đặt 2 biến thể video cạnh nhau để đánh giá hiệu quả chuyển đổi.
5. **Theo dõi tác vụ song song (Concurrent job monitoring)**: Giám sát 5 video đang render đồng thời mà không bị ngập tin nhắn như trên bot chat.

---

## 4. CÁC PHÂN HỆ SẢN PHẨM ĐỘC LẬP KHÁC

### 4.1. Voice Studio (Giọng Nói AI)
- **Tách khỏi Video Studio**: Không giấu tính năng giọng nói vào bên trong kịch bản video.
- **Quy trình chuẩn**:
  `Chọn Giọng -> Nhập Script -> Tùy Chỉnh (Tốc độ/Cao độ/Cảm xúc) -> Nghe Thử -> Tạo File MP3 -> Lưu Vào Kho Audio`.
- **Hồ sơ giọng nói (Voice Profile)**: Quản lý các mẫu giọng đã lưu, quản lý quyền sử dụng giọng đọc.

### 4.2. Music & SFX Studio (Âm Nhạc & Hiệu Ứng Âm Thanh)
- Tách biệt hoàn toàn khỏi Voice và Video.
- **Thành phần**:
  - `Music Generation`: Tạo nhạc nền theo mood, thể loại, thời lượng.
  - `Music Library`: Thư viện nhạc bản quyền thương mại có sẵn theo chủ đề (Review, Vlog, Hào hùng, Thư giãn).
  - `SFX Cue Sheet`: Bảng hiệu ứng âm thanh (tiếng ting, whoosh, pop) đồng bộ theo mốc thời gian.

### 4.3. Localization Suite (Phụ Đề, Lồng Tiếng & Dịch Thuật Đa Ngôn Ngữ)
- Gom toàn bộ các công cụ phiên dịch, phiên âm, phụ đề thành 1 suite duy nhất:
  - `Subtitle Transcription (ASR)`: Chuyển đổi giọng nói video thành phụ đề tự động (Whisper).
  - `Subtitle Editor`: Giao diện dòng thời gian trực quan chỉnh sửa từ ngữ, canh mốc thời gian, sửa lỗi chính tả.
  - `Translation Engine`: Dịch kịch bản/phụ đề sang 10+ ngôn ngữ mục tiêu.
  - `AI Dubbing`: Lồng tiếng tự động bằng ngôn ngữ mới, đồng bộ khẩu hình/nhịp điệu.
  - `Export Options`: Xuất file rời (.SRT, .VTT) hoặc burn-in trực tiếp vào video MP4.

### 4.4. Manual Video Tools (Bộ Công Cụ Video Thủ Công Nhanh)
- **Nguyên tắc phân tầng xử lý**:
  - `LOCAL_SAFE_OPERATION`: Cắt (trim), ghép (concat), đổi tỷ lệ (crop/resize), nén (compress), tắt tiếng (mute), trích xuất audio/frame. Các tác vụ này **xử lý 100% bằng FFmpeg cục bộ trên server**, không gọi bất kỳ AI Provider bên ngoài nào -> Chi phí 0 Xu hoặc siêu rẻ.
  - `CANONICAL_JOB_REQUIRED`: Tăng độ nét (Upscaling AI), xóa vật thể (Inpainting), làm mượt chuyển động (Frame Interpolation) -> Bắt buộc tạo Job hàng đợi.

### 4.5. Automated Content Publishing (Lịch Đăng & Phân Phối Đa Nền Tảng)
- Quy trình xuất bản không được đánh đồng giữa "đã lên lịch nội bộ" và "đã đăng thực tế".
- Bắt buộc 6 trạng thái độc lập:
  ```
  [PLANNED] (Đã lên kế hoạch)
      │
      ▼
  [APPROVED] (Đã duyệt nội dung)
      │
      ▼
  [SCHEDULED] (Đã nạp lịch nhắc)
      │
      ▼
  [DISPATCHED] (Đã gửi sang nền tảng: TikTok / Facebook / YouTube)
      │
      ├──► [PUBLISHED] (Đã xuất bản thành công kèm link bài viết)
      │
      └──► [FAILED] (Thất bại kèm mã lỗi và nút thử lại)
  ```

---

## 5. KẾT LUẬN & ĐỊNH HƯỚNG V3
Mô hình sản phẩm V3 tái định nghĩa lại giá trị thực của Web App: Biến Web App thành một **Production Studio chuyên nghiệp**, nơi người sáng tạo nội dung và doanh nghiệp có thể sản xuất hàng loạt video, âm thanh, giọng nói chất lượng cao với tốc độ và khả năng quản lý vượt trội so với môi trường hội thoại trên Telegram.
