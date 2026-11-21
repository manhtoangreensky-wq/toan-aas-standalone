# Trước phát hành — đường dẫn và số lượng âm thanh

BASE=ea4da7c446059f911f3b59d61f9f92f63ea95c94.
BRANCH=codex/audio-review-visual-20261121.
STATUS=LOCAL_TESTS_PASS_RELEASE_PENDING.

Hai lỗi chữ độc lập được xử lý trong hai tệp ứng dụng: breadcrumb
VI/ZH và số ít tiếng Anh. Contract giữ nguyên dữ liệu, route, quyền,
receipt và lần đọc số lượng. Antigravity cung cấp record breadcrumb;
sau hai đề xuất số ít không giữ đúng cách đánh giá dữ liệu, Root sửa
trực tiếp đúng biểu thức đó.

Renderer thật: 12 tình huống VI/EN/ZH, trong đó ba lỗi trước sửa;
17 case cuối đạt gồm source/compatibility. Node historical70 PASS,
Python historical95 PASS và hai case mới PASS. Lượt kiểm tra catalogue
cũ từng có 24 lỗi do giả định QA sai về vị trí khóa; 26 ca liên quan
đã đạt sau sửa QA. Các receipt là những lượt riêng, không cộng trùng.

Tài liệu vận hành, đối chiếu chức năng và checklist đã cập nhật. Trước
phát hành vẫn phải kiểm manifest/secret, provenance, CI, merge, deploy
và runtime. Signed production UI chưa được kiểm. Lỗi tách nhãn/mô tả
vẫn mở và không được tính là hoàn thành.
