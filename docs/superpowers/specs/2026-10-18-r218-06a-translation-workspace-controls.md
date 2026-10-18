# R218-06A — Bố cục workspace Dịch (UT-01)

Ngày 2026-10-18 · Trạng thái `CONTROL_LEVEL_PARTIAL`

## Mục tiêu

Đưa các lựa chọn Dịch về một workspace dọc, dễ hiểu và không trộn với luồng
SubDub legacy. Workspace phải thể hiện đúng thứ tự người dùng cần nhìn thấy:
nguồn → ngôn ngữ đích → tùy chọn → điều khiển → kết quả/lịch sử.

## Phạm vi đã lát

- Nguồn có lựa chọn `Tự nhận diện` và toàn bộ catalog ngôn ngữ đang được Web
  công bố (21 mục, dùng chung catalog trình bày của SubDub).
- Ngôn ngữ đích có ô tìm kiếm cục bộ, danh sách chọn và số lượng mục đang hiển
  thị. Tìm kiếm chỉ ẩn/hiện option trong DOM, không gọi mạng.
- Hai tuỳ chọn cục bộ: `Giữ lại bản gốc` và `Dịch hai chiều`.
- Khu vực `Bắt đầu dịch` / `Dừng xử lý`, trạng thái, Kết quả dịch và Lịch sử
  dịch nằm ngay trong workspace.
- VI/EN/ZH có bản dịch riêng; không dùng chuỗi giao diện tiếng Việt làm fallback
  cho EN/ZH.
- Giữ nguyên `/translate` → `/subtitle-studio/new?intent=translation`; không
  xóa `renderSubtitleStudioCompanionLink`, không thêm form/API action mới.

## Ranh giới an toàn

- Panel không phải `<form>` và không có `data-portal-action`, nên không làm thay
  đổi payload tạo transcript project hiện có.
- Nút bắt đầu/dừng chỉ mở khi capability server
  `translation-runtime-start === true`; hiện source không công bố capability
  này nên trạng thái mặc định là `guarded`.
- Chưa có dịch máy, nhận dạng giọng nói, TTS, quote, charge, job, provider,
  upload, output file, download hoặc delivery. Không đánh dấu runtime parity.

## File được phép sửa

```text
static/portal/portal.js
static/portal/portal.css
tests/translation-workspace-controls.test.mjs
docs/superpowers/specs/2026-10-18-r218-06a-translation-workspace-controls.md
reports/audit/WEBAPP-BOT-PARITY-UIUX-MASTER-CHECKLIST-R218.md
.agents/state/WEBAPP-BOT-PARITY-R218.yaml
TAI-LIEU/01-NGHIEP-VU-VAN-HANH.md
TAI-LIEU/02-CHUC-NANG-GOC-VA-HIEN-TAI.md
reports/prepush/WEBAPP-BOT-PARITY-R218-PR654-UPDATE.md
```

## Kiểm thử đóng lát

```text
node --test tests/translation-workspace-controls.test.mjs = 3/3
node --test tests/*.test.mjs = 547/547
node --check static/portal/portal.js = PASS
node --check static/portal/portal-i18n.js = PASS
git diff --check = PASS
pytest = BLOCKED (workspace không có python/py)
```

## Còn mở

UT-01 chỉ đạt `[~]` ở control-level. Cần backend capability/DTO, xử lý thật,
quote/confirm, tiến trình, kết quả, lịch sử, browser authenticated và live
evidence ở wave kỹ thuật sau; không tự mở trong wave UI này.
