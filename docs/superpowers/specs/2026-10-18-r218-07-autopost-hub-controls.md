# R218-07 — AutoPost Hub control-level UI/UX

## Mục tiêu

Đưa toàn bộ phạm vi AutoPost vào một workspace Web dọc, dễ hiểu và trung thực:
nguồn → thương hiệu/kế hoạch → kênh → lịch/hàng đợi → rà soát/báo cáo. Lát này chỉ
khóa presentation/control-level; không mở kết nối mạng xã hội, OAuth, provider,
publish, quảng cáo, job, ví Xu, PayOS hay dữ liệu production.

## Phạm vi đã khóa

- Một route `/publishing` với layout `autopost-hub`, không tách thành các trang rời.
- Bảy nguồn được trình bày riêng, giữ source lineage và owner boundary:
  chủ đề/ý tưởng, URL tham khảo, sản phẩm Affiliate, tệp đa phương tiện,
  video TOAN AAS, ảnh TOAN AAS và ý tưởng từ kế hoạch.
- Trình tự năm bước cố định: chọn nguồn, lập kế hoạch/thương hiệu, chọn kênh,
  lịch/hàng đợi, báo cáo/lịch sử.
- Các lane liên kết đúng workspace Web-native đã có: Channel Strategy, Content
  Calendar và gói rà soát trước khi đăng.
- Các lane chưa có capability (kết nối kênh, hàng đợi xuất bản, Affiliate/số liệu)
  hiển thị `guarded`, không có dead click và không giả trạng thái thành công.
- Bố cục desktop chia nguồn và lane điều phối; tablet thu về một cột; mobile là
  một cột dọc với nhãn trạng thái nằm dưới nội dung, không tràn ngang.
- Fixed chrome có catalogue VI/EN/ZH cân bằng; tên riêng như AutoPost, Affiliate,
  OAuth, Asset Vault, Campaign, Project, TOAN AAS được giữ nguyên theo quy ước.

## Điều kiện không được suy diễn

- Bảy thẻ nguồn không chứng minh bytes upload, URL đọc được hay quyền publish.
- Nút mở Channel Strategy/Calendar/Review chỉ là handoff vào workspace tương ứng;
  không tự tạo lịch, kênh, draft, job hoặc bài đăng.
- `0` kết nối bên ngoài là trạng thái presentation hiện tại, không phải số liệu
  vận hành production.
- AP-01..05 chỉ có thể đóng hoàn toàn sau khi có capability server, browser/AX,
  queue/history receipt và delivery evidence riêng.

## Bằng chứng kiểm tra

```text
TEST=tests/autopost-hub-product-controls.test.mjs
SCOPE=route/layout, 7 sources, 5 steps, truthful guards, VI/EN/ZH, responsive CSS
PROVIDER_CALLS=0
WALLET_MUTATIONS=0
PUBLISH_MUTATIONS=0
```

## Trạng thái ledger

AP-01..AP-05: `[~]` control-level đã khóa; execution, channel connection, queue,
Affiliate metrics, browser/AX và live delivery vẫn mở theo R218-07.
