# WebApp Bot Parity UI/UX Replan R218

## Mục tiêu

Đưa WebApp standalone về đúng luồng sản phẩm của Bot, giữ trải nghiệm một màn hình,
gọn nhưng đủ chi tiết, sau đó mới mở các bridge xử lý thật. R218 bắt đầu bằng SubDub
vì đây là lane đang có khoảng cách lớn nhất giữa giao diện Web và khả năng Bot.

Phạm vi của R218 là WebApp standalone. Bot chỉ là nguồn tham chiếu đọc-only. Không
sửa Bot/Core, route-engine, provider, ví/Xu, PayOS, dữ liệu production hoặc secret.

## Nguồn tham chiếu Bot đã kiểm tra

- `D:\TOANAAS\bot telegram\docs\public\TOAN_AAS_HUONG_DAN_SU_DUNG_CHO_KHACH_V2.md`
  — luồng người dùng: chọn công cụ → gửi tệp/nội dung → chọn cấu hình → xem hóa đơn
  → xác nhận → xử lý → nhận kết quả.
- `D:\TOANAAS\bot telegram\docs\subdub\TOAN_AAS_SUBDUB_4LANE_OPTIMAL_PIPELINE_RESEARCH_2026-07-28.md`
  — bốn lane dùng chung source semantic master và translation master.
- `D:\TOANAAS\bot telegram\docs\superpowers\specs\2026-08-14-subdub-per-speaker-auto-gender-cast-design.md`
  — giọng mặc định/thủ công/đã lưu và Auto speaker theo từng người nói.
- `D:\TOANAAS\bot telegram\docs\superpowers\specs\2026-08-24-subdub-multi-speaker-blackbox-design.md`
  — lane nhiều người nói tách khỏi lane hai người nói, fail-closed khi thiếu bằng chứng.
- `D:\TOANAAS\bot telegram\docs\superpowers\specs\2026-09-01-subdub-auto-multi-local-speaker-embedding-design.md`
  — Auto Multi xác định số người nói trong khoảng 3–8, ánh xạ mỗi người nói tới một
  giọng khác nhau, không ép số lượng hoặc gán xen kẽ.
- `D:\TOANAAS\bot telegram\reports\subdub_smart_shadow_comparison.json`
  — bằng chứng fixture cho 1, 2, 3, 5 và 8 người nói, cùng trạng thái fail-closed.

## Khoảng cách đã xác nhận ở WebApp

1. SubDub đã có bốn tab và volume control nhưng vẫn là presentation guarded; upload,
   tạo job, xử lý và kết quả thật chưa nối.
2. Dubbing/Combo chỉ có lựa chọn `auto`, `one`, `two`, `many`; chưa có lane rõ ràng
   cho giọng mặc định nam, giọng mặc định nữ, Multi 2, Multi 3–8 và Auto nhiều giọng.
3. `voice_profile_id` và `voice_style` đang disabled; liên kết sang Voice Studio chưa
   tải được Voice Library hoặc voice đã lưu.
4. Smart Multi mới là select và copy; chưa hiển thị bản đồ người nói → giọng, số người
   nói đã nhận diện, trạng thái chưa đủ bằng chứng hoặc lý do phải chọn thủ công.
5. Stage 3/4 đang guarded; chưa có receipt thật, tiến trình từng bước, artifact SRT/VTT,
   audio dubbing, MP4 combo và báo cáo sau xử lý.
6. Locale VI còn dấu vết thuật ngữ tiếng Anh trong copy SubDub; cần rà toàn bộ catalogue.

## Thứ tự triển khai

### W0 — Rebaseline và ledger

- Ghi R218 vào state/checklist mới.
- Khóa các yêu cầu Bot parity ở trên thành acceptance criteria.
- Giữ các wave đã đóng của R217, không mở lại source đã đạt.

### W1 — Đóng phần đang dở của SubDub WebApp

- Hoàn thiện IA một màn hình: nguồn → lane → ngôn ngữ → giọng → cân chỉnh âm thanh
  → báo giá/xác nhận → tiến trình → báo cáo.
- Bổ sung lane UI rõ ràng: mặc định nữ, mặc định nam, Voice Library/giọng tự thêm,
  Multi 2, Multi 3–8, Auto nhận diện nhiều giọng.
- Hiển thị trạng thái guarded đúng sự thật; không bật nút tạo job khi bridge chưa sẵn.
- Đồng bộ copy VI/EN/ZH; không trộn ngôn ngữ trong từng locale.
- Giữ màu xanh/navy/teal, không dùng nền đen brand; chuẩn hóa card, spacing, heading,
  touch target 44px và thứ tự đọc dọc trên mobile.

### W2 — Đối chiếu Voice và các lane sản phẩm

- Voice: mặc định, giọng đã lưu, giọng tự thêm, preview, tốc độ, âm lượng, consent.
- Music: nhạc nền, bài hát có lời, giọng nam/nữ/song ca/tự động, gợi ý và hóa đơn.
- Image: tạo ảnh, chỉnh ảnh, reference, preview, lịch sử và output readiness.
- Video: các lane video, addon voice/music/subtitle/dubbing, AI/manual editing boundary.
- Mỗi lane có checklist UI riêng trước khi mở runtime bridge.

### W3 — Locale, responsive, accessibility

- Rà fixed chrome và product copy theo VI/EN/ZH.
- Kiểm viewport 320/375/390/414/768/1024/1440, không tràn ngang.
- Kiểm heading order, label thật, focus, keyboard tab, contrast AA, reduced motion.

### W4 — Runtime bridge và báo cáo thật (Owner gate riêng)

- Chỉ mở sau khi UI contract xanh.
- Mọi lane dùng request ID, job ID, provider task ID, idempotency và audit.
- Không provider call hoặc wallet mutation trong fixture/QA.
- Chỉ claim PASS khi có artifact thật và receipt thật.

### W5 — Motion cuối

- Chỉ sau khi W1–W4 ổn định.
- Giữ transform/opacity, không animate layout, có skeleton và reduced-motion.
- Đo trace desktop/mobile: CLS < 0.10, LCP ≤ 2.5s, INP ≤ 200ms hoặc ghi blocker.

## Cổng dừng

- Không tạo copy giả cho output hoặc báo cáo.
- Không dùng `HTTP 200`, job ID hoặc cờ `completed` để claim thành công.
- Không sửa Bot/Core hoặc các luồng đã khóa.
- Nếu thiếu entitlement/provider/runtime, giữ guarded và ghi rõ blocker trong checklist.

## Kết quả mong đợi

R218 chỉ được coi là hoàn tất khi mỗi lane có UI/UX acceptance riêng, có bằng chứng
source và browser phù hợp, locale không rò, mobile không vỡ, và các phần bridge chưa
được mở vẫn hiển thị đúng trạng thái an toàn.
