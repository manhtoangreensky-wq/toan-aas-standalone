# IMAGE-STUDIO-VALIDATION-COPY-20261123

BASE/runtime: `5a95e48c9df922cc19a4bd83dfef46f2d85c04d2`, PR #799;
CI45129027195, deploy45132203233, receipt689/7094535782 đã đọc lại đúng.
Nhánh `codex/image-studio-validation-copy-20261123`. Motion vẫn cuối.

## Kết quả duy nhất

Thông báo từ chối đầu vào của thiết kế ảnh và công cụ soạn mô tả hiển
thị đúng ngôn ngữ Việt/Anh/Trung, dễ hiểu và chỉ hướng dẫn thao tác có
thật. Không thay đổi dữ liệu được chấp nhận hoặc kết quả xử lý hợp lệ.

Ứng dụng chỉ sửa `static/portal/integration.js` và `portal-i18n.js`:
29 record tích hợp và một record danh mục, tổng30; thêm51 key cân bằng.
Allowlist25 nhãn cố định chỉ được dịch trong nhánh báo lỗi; nhãn không
biết và nội dung khách giữ nguyên. Số hiển thị theo locale hiện tại.

Antigravity integration R1 và catalogue R1A đã trả đúng đề xuất.
Catalogue R1 phát hiện bộ tạo phiếu làm sai dấu nháy: SPEC_SAI, không
tính lỗi worker. Review phát hiện hướng dẫn chọn ảnh trong cảnh báo
dùng chung với Composer chỉ nhập chữ; phụ lục LINK R1 sửa fallback và
ba bản dịch của đúng một key. Hai sửa khớp đề xuất; workerCodeFailures=0.
Ứng viên cuối204 đối chiếu đạt; đây chưa là nghiệm thu nguồn vật lý.

## Phạm vi khóa

Giữ nguyên điều kiện/regex/sensitiveKind, normalization, enum, min/max,
UUID/reference, fingerprint/dedup, payload, acquire/release/busy, guard,
epoch, callback/catch, API, route và `result.message/error.message`.
Không gọi hàm dịch ở đường nhập liệu hợp lệ. Không đổi chữ ký hàm.

Không đổi CSS, markup, lựa chọn, biểu mẫu, bản nháp, auth/backend,
Bot/route-engine/provider/wallet/PayOS/ENV/secrets/production data/motion.
Không giao worker test, fixture hoặc phản hồi API/đăng nhập/dữ liệu thật.
Worker chỉ trả đề xuất; root áp dụng đúng record và tự nghiệm thu.

QA cho phép fixture/test/helper hữu hạn mới, hook đầu vào historical
hiện có, test Python đọc nguồn và đăng ký CI; không thay assertion cũ để
chấp nhận dữ liệu tùy ý. Hai biểu thức báo sai loại phương án giống
nhau phải đảo trong đúng hàm riêng, không thay chữ tổng quát.

## Checklist và gate theo thứ tự

- [x] PR799 merge/deploy/runtime/services/health/5+5assets/receipt đạt.
- [x] Hai phiếu đầu và phụ lục câu chữ có kết quả;204 kiểm ứng viên đạt.
- [x] Fixture nguồn đúng BASE+30 record; có RED trên nguồn chưa sửa.
- [x] Nhánh hợp lệ giữ normalized payload, không đổi input, không gọi dịch.
- [x] Nhánh từ chối giữ kết quả/loại lỗi, thông báo đúng ba locale;
 25 nhãn tĩnh, nhãn khách lạ, số lớn và thiếu I18n được kiểm.
- [x] Cảnh báo liên kết trong metadata và Composer chỉ nhập chữ không
 hướng dẫn chọn ảnh; mọi detector được giữ bởi comparator nguồn.
- [x]51 key thêm và khóa, mọi key/giá trị cũ giữ nguyên.
- [x] Historical inverse chỉ đảo record đã duyệt; giữ unknown changes,
 phát hiện thiếu/lặp/đổi câu, không che nội dung khách.
- [x] Hồi quy Node174 tệp chọn chạy,4.925ca duy nhất đạt; Python tĩnh42/42,
 metadata1/1. Python Image6/7 có đúng1lỗi câu cũ trên BASE, đã tái hiện
 bằng exactBASEtest/app. Không nhận toàn pytest xanh hoặc auth cục bộ đạt.
- [x] Giao diện thông báo đọc được trên375/1440, ba locale; phân biệt
 bằng chứng nguồn/VM/trình duyệt và production sau đăng nhập.
- [x] Review cuối một lượt gộp, không còn lỗi chặn; cập nhật vận hành,
 đối chiếu chức năng gốc, phiên Tester/case/provenance trước push.
- [ ] Một PR → exact-head CI → merge → exact-SHA deploy → runtime/
 services/health/5+5assets → receipt. Không đóng cả goal.

Lệnh chính: `node --test tests/image-studio-validation.test.mjs` phải
không lỗi sau sửa và có lỗi đúng câu chữ/nguồn trước sửa.
Python dùng interpreter hiện có, không cài gói hoặc thay môi trường.
Chỉ báo mức bằng chứng đã quan sát; signed production UI vẫn
`NOT_TESTED` nếu chưa quan sát được bằng công cụ trình duyệt hiện có.

## Phần kế tiếp chưa nằm trong đợt này

Thông báo hành động/lỗi động, bản nháp qua lỗi đọc/đổi revision/rời route,
locale toàn app, accessibility/responsive/auth/device/Safari và motion
cuối vẫn mở. Không mở rộng đợt thông báo nhập liệu sang các việc trên.

## Dependency cập nhật25/11

Main/VPSb24da8f1e41f51c1f51ae5b3abb7d99da10cebf1 đã có sửa catalogue
và QA riêng. PR800CIc732success nhưng chưamerge. Hòa nhập main cùng PR,
giữ nguyên mọi sửa main; xung đột chỉ hai tệp provenance, phải refresh
Web-only sau mergecommit. 30recordvalidation không đổi; cổngfreshHEAD
CI/AuthQA bắt buộc trước merge/deploy. Phụ lụcIssue689/7153324764.
