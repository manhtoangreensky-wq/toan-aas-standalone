# R217-11 — Authenticated QA matrix và bot-parity evidence

**Status:** `BLOCKED` (chưa có runtime QA cô lập trong lượt lập plan)
**Wave:** W7

## Điều kiện mở

- URL/lệnh runtime QA cô lập, DB fixture tách production.
- Tài khoản `customer_qa` và `canonical_admin_qa` không có ví/provider mutation.
- Browser session có thể ghi DOM/screenshot/console/network/trace.

## Contract kiểm thử

Ma trận bắt buộc: customer + Admin × VI/EN/ZH × light/dark × 375/390/768/1440.
Mỗi route ghi title/heading/CTA/field, AX name, focus order, screenshot, console, network,
persistence sau reload và state transitions input/preflight/confirm/progress/result/recovery.

Routes tối thiểu: `/welcome`, `/dashboard`, `/features`, `/image/create`, `/voice/create`,
`/music`, `/subdub`, `/tools/video`, `/video/create`, `/workboard`, `/campaigns`,
`/free-prompt-gallery`, `/wallet/topup`, `/admin`, `/admin/operations`, `/admin/billing`,
`/admin/customers`, `/admin/audit`, `/admin/support`.

## Cấm

Không đăng nhập production, không gửi form trả phí, không tạo job/provider call, không
approve top-up, không sửa DB production.

## Acceptance

- Có file result với URL/viewport/locale/theme/timestamp và pass/fail từng route.
- Các lane chưa có engine phải chứng minh guarded boundary, không ghi output PASS.
- Console không có error/warning mới; network không có provider/payment mutation.

## Verify

```powershell
python -m pytest tests/test_browser_runtime_gate.py -q
```

Nếu runtime không chạy, giữ `BLOCKED`, ghi lỗi khởi động cụ thể và không tạo fixture ở
production.
