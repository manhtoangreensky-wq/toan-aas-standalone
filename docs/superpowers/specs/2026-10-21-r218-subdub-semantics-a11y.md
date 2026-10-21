# SD-E2 — SubDub ngữ nghĩa, trợ năng và thông báo trạng thái

## CONTRACT

Chỉ chạm renderer SubDub và test: `static/portal/portal.js`,
`tests/subdub-semantics-a11y.test.mjs`, hồi quy SubDub và evidence. Bảo vệ
engine/API/auth/schema/provider/ví/CTA/motion/theme/Voice-return.

## RED → GREEN

- RED: Stage 3 chưa có vùng semantic được gắn tiêu đề và `output` âm lượng chưa
  được thông báo; tab/panel relationship phải giữ nguyên.
- GREEN: vùng `Thiết lập của bạn`/`Your settings`/`你的设置` dùng `role=region`,
  `aria-live=polite`, `aria-atomic=true`, `aria-labelledby` tới heading theo
  mode; output âm lượng dùng `role=status`, `aria-live=polite`, `aria-atomic`;
  tab/panel vẫn liên kết bằng `aria-controls`/`aria-labelledby`.

## VERIFY

- Test `tests/subdub-semantics-a11y.test.mjs`: 3/3.
- Hồi quy SD-D2 + SD-C2: 47/47; Node syntax và diff-check exit0.
- Browser QA Edge headless, DB tạm: 24/24 cấu hình VI/EN/ZH × sáng/tối ×
  375/390/768/1440; AX/ảnh, live region, số↔thanh kéo, lỗi, mute, Voice-return,
  page/console/UIwrite/external/overflow đều đạt `0` lỗi.
- Không gọi upload, provider, quote, job, output, wallet hoặc production.

## OPEN

Ngữ nghĩa control-level đã khóa; runtime upload/ASR/dịch/lồng tiếng/Smart Multi,
quote/job/output/delivery và trace CLS/LCP/INP vẫn mở. Motion vẫn làm cuối.
