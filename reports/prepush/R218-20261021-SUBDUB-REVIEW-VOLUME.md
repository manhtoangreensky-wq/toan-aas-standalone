# Báo cáo trước push — SD-D2 SubDub review và cân âm lượng

Đang đọc và áp dụng skill owner-governed-codex cho task này.

## 1. Review mã và tài liệu vận hành hiện tại

- Repo: `manhtoangreensky-wq/toan-aas-standalone` · PR #654 · branch
  `webapp-r217-subdub-ui-r218` · BASE `9bc85a95389beb69c6d973f04b5f1eb14362c7e5`.
- Phạm vi code: `static/portal/portal.js` (SubDub summary, number/range,
  mute ack, capture/apply), `static/portal/portal.css` (bố cục volume con),
  test SubDub; không đổi API, engine, auth, schema, provider, ví, CTA guarded,
  theme token hoặc motion.
- Tài liệu nghiệp vụ đã cập nhật: `TAI-LIEU/01-NGHIEP-VU-VAN-HANH.md` ghi rõ
  Stage 3, unknown truth và volume/mute local; checklist mẹ và spec SD-D2 đã
  đánh dấu các cổng local đạt, runtime vẫn mở.
- Tester đã cập nhật: `KIEM-THU/DANH-SACH-CASE.md` thêm SDD2-01..04; metadata
  portable trong `reports/migration/p0-05d-tester-workspace.json` đo lại lines
  `404`, bytes `58962`, hash `4ea022eb...841f79`.

## 2. Đối chiếu tài liệu gốc

`TAI-LIEU/02-CHUC-NANG-GOC-VA-HIEN-TAI.md` vẫn là nguồn đối chiếu Bot/Web.
SD-D2 chỉ đóng presentation/control-level cho các mục SubDub có trong tài liệu;
không chuyển các mục upload, ASR, dịch, lồng tiếng, Smart Multi, quote, job,
output, delivery hoặc LIVE thành đã hoạt động. Không tìm thấy thay đổi nào cần
điều chỉnh tài liệu gốc ngoài việc bổ sung bằng chứng local và giới hạn.

## 3. Tester workspace

- Tracker hiện hữu: issue #412, nhãn Tester `12/12`, hai mẫu issue local và
  `KIEM-THU` là nguồn case duy nhất; không tạo issue/project trùng.
- Case mới SDD2-01..04 trỏ tới artifact browser ngoài repo và ghi rõ không có
  provider/ví/output. `reports/migration/p0-05d-tester-workspace.json` không
  suy diễn quyền Project mới.

## 4. Evidence

- Targeted Node: `44/44`; full Node: `880/880`; syntax portal.js và
  portal-i18n.js: exit0; `git diff --check`: exit0.
- Browser Edge headless trên DB QA tạm: `24/24` cấu hình VI/EN/ZH × sáng/tối ×
  375/390/768/1440; page/console/UIwrite/external/overflow `0`. Artifact:
  `reports/audit/R218-SUBDUB-REVIEW-VOLUME-QA-20261021.json` và kết quả ngoài
  repo `subdub-review-volume-green-20261021.json`.
- Python scoped: `49 passed`; các mismatch baseline ngoài phạm vi được giữ
  nguyên: Windows permission-mode, motion protected fingerprint và legacy
  `voice_style` assertion. Không có failure mới của SD-D2.
- Reviewer độc lập: Critical `0`, Important `0`; khoảng trống updater đã có
  test production helper.

## 5. Safety / delivery gate

`PROVIDER_CALLS=0` · `WALLET_MUTATIONS=0` · `PRODUCTION_DATA_MUTATIONS=0` ·
`DEPLOY=NO` · `LIVE_PASS=NOT_TESTED`.

`PUSH_GATE=READY_FOR_OWNER_APPROVED_PUSH`: code/docs/tester/evidence đã review;
PR #654 vẫn mở, chưa merge/deploy. Sau push phải đọc lại HEAD và theo dõi cả hai
job CI đến terminal; không dùng CI xanh để suy ra engine hoặc LIVE.
