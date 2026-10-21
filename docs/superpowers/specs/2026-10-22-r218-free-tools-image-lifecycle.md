# UT-CSP-EMPTY-THUMB — ảnh và phản hồi Free Tools

BASE d1d042e; PR654; ngày22/10/2026. Đang đọc và áp dụng skill
owner-governed-codex cho task này.

## Lỗi và phạm vi

Free Tools khởi tạo3img YouTube và1img QR với src rỗng; onerror inline của ảnh
max bị CSP chặn và định dùng placeholder ngoài. Đối chiếu browser baseline tái
hiện5CSP messages. Giữ CSP hiện tại, parser/ID/link/copy/QR và các tab.
Chỉ sửa helper ảnh, markup ảnh trong Free Tools,2row locale và test liên quan.

## Checklist và acceptance

- [x] AC1: không src rỗng, inline handler hoặc placeholder ngoài. Candidate
  browser initial errors0, CSP0; baseline5. Không đổi chính sách CSP.
- [x] AC2: lúc tải chỉ có một dòng trạng thái; ảnh chỉ hiện sau load có
  naturalWidth>0; lỗi là một câu ngắn, retry thay handler và phục hồi ảnh.
  Unit helper thật và browser12cấu hình đều đạt; bytes ảnh kiểm soát cục bộ.
- [x] AC3: tab/bàn phím/ID/parser/link giữ đúng; subtitle cleaner chạy thật,
  TXT tải về khớp văn bản đã làm sạch ở12cấu hình. UI writes/external0.
- [x] AC4:6/6focused, fullNode exit0, syntax2file/diff0. CSS/backend/integration
  không thay đổi trong wave này.
- [x] AC5:96trạng thái ở8route/3locale/2theme/2viewport được chạy trên app thật
  và DB QA cô lập; không có chữ thử nghiệm/demo/beta/sandbox trong màn được đo,
  ô lời thoại Voice trống, hero badge0 và overflow0.
- [ ] Delivery: push, đọc đúng HEAD và CI. Không tự chuyển thành LIVE/engine pass.

## Người làm và giới hạn

Antigravity Gemini3.8Flash round1 trả patch; Codex review/apply/verify.
Lần chạy toànrepo bị auto-review từ chối; đã thu hẹp thành packet3file chỉ có
phiếu/source excerpts/test. Không sửa quyền hoặc settings. Worker codefail0.
Source WIP đầu của Codex được worker hoàn thiện, không bỏ mất thay đổi.

Thumbnail browser dùng ảnh kiểm soát để đo load/error/retry, không xác nhận
YouTube luôn cung cấp mọi độ phân giải. Không gọi provider hoặc kiểm generation,
wallet, engine, production. Evidence R218-CUSTOMER-UI-REALITY-QA-20261022.json.
Motion cuối theo checklist mẹ.
