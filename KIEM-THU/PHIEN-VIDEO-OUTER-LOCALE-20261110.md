# Phiên kiểm thử — chữ biểu mẫu video, 10/11/2026

SESSION_ID=VIDEO-OUTER-LOCALE-20261110.
BASE_SHA=3e6732446a89ce84ddc90711294b6e504bc593b8. Theo dõi Issue #689.

| Ca | Kết quả bắt buộc | Bằng chứng hiện tại |
|---|---|---|
| OUTER-COPY-01 |132chữ cố định của hai biểu mẫu/metadata đúngVI/EN/ZH |24/24renderer;9361bản dịch cũ giữ nguyên |
| OUTER-CONTROL-02 |10field long-form, mã9/3/7motion và4/4/5/6/2long-form, mặc định/quyền giữ |Fixture chuẩn hóa thật; scalar/action/disabled checks đạt |
| OUTER-CARD-03 |Ba gợi ý có chữ giao diện đúng, nội dung máy chủ giữ, count/topic đúng thứ tự |3locale renderer với3card hợp lệ; dữ liệu được thoát ký tự nguyên vẹn |
| OUTER-NATIVE-04 |320/1440 sáng/tối ba ngôn ngữ, form/Tab/draft/font/target/contrast/khung/AX đạt |24/24đạt từ18ca giữ lại+6ca sửa; cảnh báo8,4502:1, ghi chú5,7971:1 |
| OUTER-GUARD-05 |Mặc định/khóa quyền/nhập riêng/thông báo cũ không tạo trạng thái giả |Đang kiểm native; stale-guide dùng phép chiếu tổng hợp có ghi nhãn, không gọi tạo video |
| OUTER-REGRESSION-06 |Không đổi result/receipt/helper/CSS/integration/backend/quyền/tiền |Source exact/protected đạt;Node2280/2280;Python22+2đạt |
| OUTER-DELIVERY-07 |Tài liệu/provenance/CI/merge/deploy/runtime có bằng chứng riêng |Local đạt, chờ CI/phát hành |

Builder chỉ trả mã, tester không sửa ứng dụng. Nghiệm thu gộp theo quy tắc Owner;
không chạy lại bộ lớn trên mã không đổi. Bằng chứng PR705 của luồng lưu/mở đã khóa
được dùng lại, không tạo lại12kếhoạch chỉ để kiểm tra chữ biểu mẫu.

TESTER_PROJECT_STATUS=READY; PUSH_GATE=READY.
Private session-stamp prerequisite:9/9handler/hydrate với dữ liệu tài khoản
đúng cấu trúc không cóid; thiếu token/phiên/quyền/tuyến và phản hồi cũ vẫn bị
chặn. Không thêmidvàoAPI hoặc đổi auth/CSRF. Native tạo gợi ý thật đã chạy.
Không dữ liệu khách, không provider/ví/production; chưa chứng minh toàn goal.
