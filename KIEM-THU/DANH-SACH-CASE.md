# Danh sách case TOAN AAS Web App — nguồn Tester

Tester project: `manhtoangreensky-wq/toan-aas-standalone#412`. Sửa case ở file này trước khi đổi tracker.

| ID | Case | PASS bắt buộc |
|---|---|---|
| WA-01 | Dashboard desktop `1440×900` | CLS/overlap/overflow/clip/error/non-read request `0`; không replay hydrate |
| WA-02 | Dashboard tablet `768×900` | Nội dung đủ; PWA/Copilot `44×44`; không che nội dung |
| WA-03 | Dashboard mobile `390×667` | Dock normal-flow; không overflow/clip/overlap |
| WA-04 | Dashboard compact `360×640` | Dock normal-flow; chữ/nút không chồng |
| WA-05 | Reduced motion | Presentation animation/transition `0`; content/focus/navigation hoạt động |
| WA-06 | Login/register | Intro/form opacity `1`, transform `none`, vị trí giống nhau ở 50ms/750ms; không remount khi provider hydrate; mobile form-first; Google/Apple ẩn khi disabled |
| WA-07 | Catalog `/features` | `135/135` mục; long task >`200ms` bằng `0`; không full integration parse ban đầu |
| WA-08 | Admin shell | Route/role server-authoritative; modal focus/Escape/backdrop/return-focus đạt |
| WA-09 | PayOS local contracts | Same key một order; foreign owner fail; URL ngoài allowlist fail; provider call thật `0` |
| WA-10 | PayOS live gate | Sau deploy, signed user click `Nạp ngay` đúng một lần mở checkout/QR thật; không quét, không trả tiền, không cộng Xu |
| WA-11 | Google readiness | `enabled=false` không anchor; start fail-closed; E2E chỉ mở lại khi đủ `6/6` cấu hình |
| WA-12 | Apple readiness | `enabled=false` không anchor; start fail-closed; E2E chỉ mở lại khi đủ `8/8` cấu hình |
| WA-13 | Admin shell VI/EN | App switcher đủ app server cấp; sidebar chỉ app hiện hành; header/drawer đúng 1440/768/390/360; Admin motion core `none` |
| WA-14 | Admin dashboard thật | Workload bar khớp counts; donut khớp ready/total; empty không vẽ số giả; bảng giữ đủ readiness row |
| WA-15 | Admin data views | Users/jobs/payments/providers/tickets search không dấu, status filter, clear/no-results, chọn row/inspector và action isolation đạt |
| WA-16 | Admin whole-surface locale | 5 route × VI/EN: hero/guard/table/aside/notes/status/inspector thuần locale; server row data không bị tự dịch |

Evidence local: `D:/TOANAAS/TOAN_AAS_WEB_APP/evidence/`. PASS cuối phải ghi PR SHA, deploy run, runtime SHA và live output riêng.
