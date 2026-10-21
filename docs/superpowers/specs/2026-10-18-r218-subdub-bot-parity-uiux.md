# R218-04 — SubDub: một workspace, đủ luồng Bot

Trạng thái SPEC_CONTROL_PARTIAL_LOCKED. PR #654 vẫn là candidate; control-level UI/UX đã
được khóa cục bộ, còn capability/runtime/provider/upload/quote/job/output/delivery chưa mở.
Allowed UI: static/portal/portal.js, portal.css, portal-i18n.js và tests SubDub.
Không sửa Bot/API schema/provider/route-engine/wallet hoặc dữ liệu production.

## 1. Workspace theo thứ tự

Nguồn/preview → việc cần làm → ngôn ngữ/lời thoại → giọng → subtitle/mix → review
→ xử lý → kết quả/report. Mobile một cột; không tách thành 4 trang không liên thông.

Bốn mode: Phụ đề gốc, Phụ đề dịch, Lồng tiếng, Phụ đề và lồng tiếng.
Chuyển mode giữ nguồn và option phù hợp; field ẩn không tham gia request trái mode.

## 2. Bảng controls

| ID | Vị trí/nhãn | Hành vi và state |
|---|---|---|
| SD-01 | Đầu trang, lựa chọn mode | 4 mode in-place, keyboard, query/reload đúng |
| SD-02 | Nguồn/preview/upload | Audio/video/subtitle theo mode/contract, metadata/progress/cancel/replace/error |
| SD-03 | “Đã có phụ đề?” | Có: chọn tệp/cue; Chưa: tạo gốc hoặc đi thẳng lane hợp lệ |
| SD-04 | Ngôn ngữ nguồn | Tự nhận diện khi hỗ trợ; không mặc định Việt cho mọi file |
| SD-05 | Ngôn ngữ đầu ra | Giữ gốc hoặc dịch; Việt đầu tiên, Anh/Trung và catalog searchable đầy đủ |
| SD-06 | Phụ đề gốc/dịch | Xem/edit cue nếu Web đã có quyền, original/translated source, mono/bilingual, SRT/VTT/TXT theo contract |
| SD-07 | Kiểu giọng | Nhóm Mặc định / Đã lưu / Thêm giọng / Tự động thông minh; không trải hàng ngang quá dài |
| SD-08 | Default → Nữ/Nam | Chọn local config; readiness riêng, không cần kho giọng cá nhân |
| SD-09 | Đã lưu | Picker profile thật: tên/trạng thái/preview/default; owner/readiness; không gõ provider ID |
| SD-10 | Thêm giọng | Voice wizard consent/upload/name/quote/preview/save → quay về draft SubDub |
| SD-11 | Auto 2 người nói | Callback Bot auto_speaker_gender; không tự đổi sang Multi hoặc ép cặp nam/nữ |
| SD-12 | Auto Multi 3–8 | Callback auto_multi_speaker; count và mapping từ server, không nhập count để giả detection |
| SD-13 | Smart Multi | Callback auto_smart_multivoice; capability/quality/cost state riêng; không gộp auto_many |
| SD-14 | Người nói → giọng | Có evidence mới hiện từng speaker, preview/override nếu contract cho; thiếu/ambiguous → review/fallback rõ |
| SD-15 | Âm thanh gốc | Bật/tắt, slider+number 0–100%; preserve 0, không reset khi đổi mode |
| SD-16 | Giọng lồng tiếng | Slider+number 0–200%, giữ giá trị; xác nhận mute nếu 0 |
| SD-17 | Subtitles layout | Vị trí 7 slot khi capability hỗ trợ, style/line rule/mono-bilingual; chỉ mode có subtitle |
| SD-18 | Review | Nguồn/mode/language/voice/mix/subtitle/duration/count/cost/expiry; Sửa ngay nhóm liên quan |
| SD-19 | CTA xử lý | Quote/capability/inputs hợp lệ; double-submit guard, progress, lỗi giữ draft |
| SD-20 | Kết quả/report | Request/job refs, mỗi stage/status, source/target/voices/mix, file readiness/receipt/failure reason/recovery |
| SD-21 | Handoff | Dùng file/giọng/subtitle cho Voice/Video/Projects/Admin có context và return path |

## 3. Điều kiện quan trọng

- Tự động nhận diện nguồn khác đổi locale giao diện, khác nhận diện người nói.
- Original/translated speech source phải rõ khi giữ ngôn ngữ gốc.
- Combo dùng cấu hình target chung; không tính 2 lần cùng nguồn dịch nếu backend
  đang dùng master chung. Tài liệu V2 shared-master là DESIGN, không giả đã triển khai.
- Chỉ cấu hình local không cần khóa toàn trang. Khi server chưa mở xử lý, CTA nêu
  lý do thực tế; không dựng giá/ID/tác vụ giả.
- Target catalog runtime thiếu: ghi T0 + UI state, không dùng một ô ISO thay trải nghiệm tìm kiếm.
- Voice Vault canonical phải xác minh; /voice-studio không tự thay cho /voice/saved.
- Download chỉ khi completed + download_ready với file thực tế.
- Report queued không là “đã nhận kết quả”; failed_delivery có recovery đọc lại đúng job.

## 4. Nguồn bằng chứng

Bot: bot.py:234163/234206 (4 mode/source),234652..234709 và236113..236161
(3 Auto callback + default/saved/create),234604/236039/236083 (language),
236533/236591 (volume),235906/236005 (subtitle position),234811 (result).
Web: renderSubDubHub, updateSubDubModeSelection, updateSubDubLocalVolume;
copyfast_subdub_job_bridge.py là nguồn schema đọc-only cần đối chiếu DTO.

## 5. Phiếu có thứ tự

SD-A: audit SD-01..21, mapping code/capability/DTO và giá trị còn UNKNOWN.
SD-B: layout/config state và source/mode/language; test back/hydration/locale.
SD-C: grouped default/saved/custom/Auto controls, readiness riêng, tránh duplicate selector.
SD-D: subtitle/mix 0–100/0–200/review/result; không đổi submit contract chưa hỗ trợ.
SD-E: browser/AX/screenshots từng mode + keyboard/mobile/theme/locale.
SD-T: những DTO/upload/projection/job còn thiếu vào T0, chưa code backend.

## 6. Nghiệm thu

Focused tests kiểm hành vi từng mode và control, không chỉ value xuất hiện trong HTML.
VO/SD handoff giữ draft qua trở lại; không lộ stale profile/secret/provider ID.
Browser VI/EN/ZH × light/dark × 375/390/768/1440; form 320/414 thêm.
Thao tác local không mạng/charge; confirm chỉ khi authorized capability thật.

Candidate #654 phải review lại: upload/preview vẫn guarded; language catalog mới chỉ là
presentation; speaker map/quote/progress/result/delivery chưa có server evidence. Đợt
control hiện tại đã loại bỏ khóa `auto_many` mơ hồ bằng ba lane riêng `auto_two`,
`auto_multi_3_8`, `smart_multi`, thêm selector “đã có/chưa có phụ đề”, catalog ngôn ngữ
đầy đủ theo VI/EN/ZH và 7 vị trí phụ đề. Test mục tiêu hiện là 14/14; các test này chỉ
đóng renderer/interaction local, không đóng requirement runtime như Bot.
