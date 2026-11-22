# Trước phát hành — làm gọn bảng thiết kế ảnh

BASE `07a89b79c442981ecb7433b607c981740c95c774`; 23record/3tệp ứng dụng:
19rowdịch,2callkhung dư bị bỏ,1ruleformmộtcột,1rulesốđếm sáng.
Không thay chức năng tạo ảnh, data, auth, backend, integration, provider, ví
hoặc motion. Đối chiếu nguồn vật lý giữ mọi byte ngoài đúng record.

Tài liệu vận hành hiện tại và đối chiếu chức năng gốc đã cập nhật; phiên
Tester có bảy case nguồn và ranh giới dùng dữ liệu giả.
23targeted/147Python/48rendermatrix/57dictionaryvalues đạt.
Hồi quy166tệp/5146ca có5145PASS/1FAIL lịch sử; đúng reader bị ảnh hưởng
được thêm inverse đầu vào hữu hạn, giữ assertions/golden; retest4/4PASS.
0lỗi chưa giải quyết; không gọi một lượt fullPASS mới. Metadata1PASS sau
sửa số đo về portableLF. Review một lượt không có finding chặn; root kiểm
delta reader2dòng và4retests. Gatepush sẵn sàng sau manifest/provenance;
không thêm source ứng dụng ngoài23record.

CI45001895285 dừng ở một parser lịch sử CSS với175PASS/1FAIL. Reproduce
tệp đó local1FAIL89PASS, thêm inverse hữu hạn tại đúng một reader, giữ mọi
assertions/golden và bài khác; retest90/90PASS. Source ứng dụng không đổi;
PR794 được cập nhật cùng nhánh, exactHEAD CI phải chạy lại trước phát hành.

Nguồn worker đã được đối chiếu23/23:

| Phiếu | SHA256 result |
|---|---|
| CREATECOPY R1 |20f765c0d1218c80a51cdae0610773fb9db0c0808726d87a7afa474608e87d76|
| DETAILCOPY R2 |2ccf0a8e8adc430c38705977948daa1d966437c0fde4f8b7fbefaa5378cb40b|
| CLEANUP R1 |7bee09d5845caacc0dde687a83b855f34e295134b95cad882b03eb5e981592c6|
| CONTRAST R1 |15a99bf8895db538374004cbd63c977c76ae451ee48a689abc800cab25d96502|

Issue689 là nơi chốt CI/merge/deploy/runtime/receipt. Signedproduction và
toàn goal chưa được nhận; không coi tệp công khai khớp là bằng chứng tương tác.
