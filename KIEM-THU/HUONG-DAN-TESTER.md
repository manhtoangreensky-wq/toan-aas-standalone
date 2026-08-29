# Hướng dẫn Tester TOAN AAS Web App

## 1. Nguồn case

1. Nguồn duy nhất là `KIEM-THU/DANH-SACH-CASE.md`.
2. Chọn đúng một ID trong `WA-01..WA-31` cho mỗi lượt test.
3. Nếu cần đổi case, sửa case thì sửa ở file đó trước, rồi mới đồng bộ issue.
4. Tracker batch là GitHub issue `#412` của repo `manhtoangreensky-wq/toan-aas-standalone`.
5. Không dùng chat/Zalo làm nơi lưu kết quả duy nhất.

## 2. Ghi đúng phiên bản

6. Trước khi test, ghi `BASE` SHA và `HEAD` SHA của source.
7. Sau deploy, ghi `runtime SHA` đọc từ runtime/evidence; không chép theo trí nhớ.
8. Ghi rõ môi trường: `local-temp-only`, `local-render`, `CI`, `deployed`, `ship-gated` hoặc `live`.
9. Local PASS không thay CI PASS.
10. CI PASS không thay bằng chứng deployed.
11. Deployed không thay live output.
12. `HTTP 200` không chứng minh kết quả tiền, media hoặc provider hợp lệ.

## 3. Thứ tự manual top-up

13. Chạy customer create trước, kiểm một pending request/invoice và zero initial credit.
14. Kiểm owner history/detail/status và foreign-owner isolation.
15. Đăng nhập đúng Admin, kiểm list/detail đã redaction.
16. Chạy draft và xác nhận draft không mutate Xu/audit decision.
17. Kiểm receipt chỉ dùng trong đúng session, hết hạn/tamper bị từ chối.
18. Chạy approve expected hoặc custom theo case; không tự đổi reason/số Xu ngoài fixture.
19. Chạy reject trong một request riêng và kiểm zero credit/usage/revenue.
20. Chạy idempotency/replay/concurrent case bằng fixture; không lặp trên production.
21. Kiểm owner đọc terminal status sau quyết định.

## 4. Auth và dữ liệu nhạy cảm

22. Kiểm signed session, role, ownership và CSRF theo đúng case.
23. Browser query/body/header không được cấp canonical owner hoặc Admin authority.
24. Ghi safe `redaction` result: token, raw bridge field, private Admin data và customer record không được xuất hiện.
25. Ảnh/log phải che email, số điện thoại, ID riêng và dữ liệu khách.
26. Không gửi token.
27. Không gửi mật khẩu.
28. Không dán backup code.
29. Không gửi Admin ID hoặc raw customer record vào issue.

## 5. Chốt tiền và provider

30. Local/manual integration giữ `PROVIDER_CALLS=0`.
31. Local/manual integration giữ `WALLET_MUTATIONS=0` ngoài temp fixture đã kiểm soát.
32. Không tự bật ENV hoặc restart production để test.
33. Không gọi provider trả phí.
34. Cấm quét QR, thanh toán hoặc cộng Xu trong case PayOS chỉ kiểm checkout.
35. `LIVE_MONEY_FLOW=NOT_TESTED` cho tới khi Owner cấp quyền cụ thể.
36. Không có Owner gate thì WA-31 phải là BLOCKED, không phải FAIL hoặc PASS.

## 6. Evidence bắt buộc

37. Mỗi kết quả ghi route, role và viewport.
38. Ghi các bước đã thao tác theo thứ tự.
39. Ghi PASS criteria, expected và actual.
40. Đính kèm screenshot/JSON/terminal output phù hợp.
41. Với UI, ghi console/page/request error, overflow, clip và overlay count.
42. Với security/tiền, ghi provider/wallet/data/ENV/GitHub mutation counters.
43. Với ship, tách PR merge, CI run, deploy run, runtime SHA, service health và live output.
44. Builder self-report không thay independent Tester verdict.

## 7. Báo lỗi và retest

45. Chọn đúng severity: `🔴 chặn-bán-hàng`, `🟠 nặng`, `🟡 vừa` hoặc `🟢 nhẹ`.
46. FAIL phải mở lại cùng `SPEC_ID`; không tạo ID mới để né lịch sử.
47. Dùng nhãn dòng chảy: `chờ-test` → `đang-test` → `có-lỗi` → `chờ-test-lại` → `đạt`.
48. Báo lỗi dùng nhãn `lỗi`, `có-lỗi`, `chờ-sửa` và severity tương ứng.
49. Case có `Canh lỗi cũ` mà fail phải báo gấp vì đó là regression.
50. Retest phải ghi SHA mới và so lại protected comparator.

## 8. Dry-run đồng bộ issue

51. Xem trước ba thẻ, không ghi GitHub:

```text
python scripts/tester_case_sync.py --so=3 --json
```

52. Lệnh trên là dry-run mặc định và không gọi `gh`.
53. Dùng `--bo=N` để bỏ qua N case đầu, `--so=N` để giới hạn N case.
54. Dùng `--sua=<issue-number> --bo=N --so=1` để chuẩn bị preview sửa đúng một issue số thật.
55. Đọc kỹ title, body, labels và command preview trước khi xin quyền ghi.
56. Chỉ thêm `--that` sau khi đã xác minh repo, đăng nhập, Owner gate và một preview thật.
57. `--that` là external mutation; không dùng trong pytest/local dry-run.
58. Nếu `gh` trả lỗi, script phải trả nonzero; không báo thành công.

## 9. GitHub readiness

59. Repo/issue/labels đã được kiểm read-only; tracker #412 hiện chưa có P0-05B/C/D trong body.
60. GitHub Project hiện là `NOT_QUERIED_AUTH_REQUIRED`.
61. Khi Project chưa được đọc/tạo có bằng chứng, push gate vẫn BLOCKED.
62. Thao tác push sau này dùng signed Codex Web session theo chỉ thị Owner, không dùng VPS/Codex CLI.
63. Không tự tạo/sửa tracker, label hoặc Project nếu chưa qua local acceptance và external gate.
