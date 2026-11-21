# Kiểm tra đường dẫn và số lượng tham khảo âm thanh

BASE=ea4da7c446059f911f3b59d61f9f92f63ea95c94.
STATUS=LOCAL_TESTS_PASS_RELEASE_PENDING.
Spec: `docs/superpowers/specs/2026-11-21-audio-review-visual-locale.md`.

| Case | Phạm vi và kết quả cục bộ |
|---|---|
| ARV-BREADCRUMB | VI/EN/ZH trên renderer header thật; VI/ZH RED trước, GREEN sau |
| ARV-COUNT | VI/EN/ZH × 0/1/2 trên renderer chi tiết thật; EN 1 RED trước, GREEN sau |
| ARV-SOURCE | Hai nguồn đầy đủ bằng BASE cộng ba record, historical projection chỉ cho test cũ |
| ARV-REGRESSION | Node historical 70 PASS; Python historical 95 PASS và hai pressure mới PASS |
| ARV-DELIVERY | CI, merge, deploy, runtime và signed UI cần bằng chứng riêng |

Targeted RED 12 ca: 9 PASS/3 FAIL; bản bổ sung GREEN 17 PASS,
gồm ba kiểm tra catalogue mới. Lượt adjacent 96 ca có 24 lỗi do
giả định QA sai về thứ tự khóa; sau sửa QA, 26 ca liên quan đạt.
Không cộng trùng receipt, không nhận toàn bộ CI hoặc UI live đã đạt.

Lỗi nhãn và mô tả dính liền chưa sửa. Các lỗi còn lại theo checklist;
motion cuối. Không provider, ví, dữ liệu production hay Bot trong scope.
