# Đặc tả — Hoàn thiện giao diện khung dùng chung Web App

- **SPEC_ID:** `WEBAPP_SHARED_SHELL_UI_CLOSEOUT`
- **PLAN_ID:** `WEBAPP-BOT-FUNCTION-PARITY-REBASELINE-20261009`
- **CONTROL_SPEC:** `WEBAPP-PRODUCT-CONTROL-BY-CONTROL-UX-20261010`
- **STATUS:** `PLAN_READY_WA35_AND_CURRENT_SOURCE_REBASELINE_REQUIRED`
**Mốc nguồn đã đọc:** `origin/main=86d4ee6e11ddfbc0d4e1dbf63b41d9b3ed7d859b` ngày 2026-10-10; không dùng làm SHA nghiệm thu sau khi WA-35 đóng.

## 1. Mục tiêu

Khép một lần các điều khiển và quy tắc giao diện dùng chung cho Web App khách;
không để từng sản phẩm tự vá thanh điều hướng, bộ chọn ngôn ngữ, giao diện sáng/tối
hoặc nút nổi. Người mới phải nhận ra vị trí hiện tại, việc có thể làm tiếp và
cách quay lại mà không cần hiểu cấu trúc nội bộ của Bot.

Spec này là kế hoạch cho giao diện khung dùng chung, không chứng nhận bất kỳ
điều khiển nào đã chạy đúng. Hoàn tất spec chỉ sau khi dùng source/DOM của SHA
mới, tạo action ledger và có browser evidence cho các trạng thái được liệt kê.

## 2. Thứ tự và cổng bắt đầu

1. Giữ nguyên worktree đang có; khép RCA WA-35 đang dở theo
   `2026-10-10-motion-webapp-surfaces-final.md` trước, không mở sản phẩm mới.
2. Sau WA-35, đọc lại `origin/main` và ghi `CURRENT_MAIN_SHA`; nếu khác
   `86d4ee6e11ddfbc0d4e1dbf63b41d9b3ed7d859b`, cập nhật source-touch matrix.
3. Khóa nguồn Bot canonical và provenance của dirty overlay; lập Bot action
   ledger. Nếu không khóa được thì ghi blocker, không tuyên bố parity.
4. Dựng Web control ledger từ source + DOM đã render. Mỗi tổ hợp route, trạng
   thái đăng nhập, control và kết quả là một dòng riêng. Không dùng selector,
   nhãn, endpoint, quyền hoặc hành vi suy đoán.
5. Chỉ bắt đầu sửa shared shell khi mọi control trong phạm vi có disposition
   rõ (`SUPPORTED`, `GUARDED`, `NOT_IMPLEMENTED`, `BACKEND_GAP` hoặc lý do khác)
   và không còn `UNKNOWN` trong action được giao.

## 3. Phạm vi điều khiển

Đưa vào ledger các mục thực sự tồn tại trên SHA mới; không tạo control giả để
đủ danh sách.

| Nhóm | Điều khiển/hành vi cần kiểm kê riêng | Trạng thái cần xác minh |
|---|---|---|
| Điều hướng chính | Mỗi liên kết nhóm/chức năng, mục đang chọn, mở/đóng sidebar hoặc menu trên điện thoại | Anonymous/authenticated, route đích, quyền truy cập, Back/Forward, focus khi mở/đóng |
| Thanh đầu trang | Tiêu đề/ngữ cảnh trang, thao tác điều hướng phụ nếu có | Không trùng tiêu đề/toolbar từ sản phẩm; co giãn mà không làm nhảy bố cục |
| Ngôn ngữ | Mở lựa chọn và chọn VI/EN/ZH nếu các ngôn ngữ đó được source hỗ trợ | Nội dung, aria/help/toast cùng ngôn ngữ; giữ route/query và trạng thái biểu mẫu được hỗ trợ |
| Giao diện sáng/tối | Chuyển theme nếu source hiện có | Dùng token của source; nền tối là xanh đậm, chữ sáng; không đổi brand thành đen |
| Tài khoản/xác thực | Đăng nhập, đăng xuất, hồ sơ/tài khoản và chuyển shell sau đăng nhập | Không lộ nội dung cần quyền trước khi xác thực; đường quay lại rõ; trạng thái phiên đúng server |
| Nút nổi dùng chung | Trợ lý và cài ứng dụng/PWA nếu source hiện có | Mỗi loại tối đa một nút; không che CTA, bàn phím, modal hoặc nội dung; quyền/điều kiện hiển thị đúng |
| Bàn phím và lịch sử | Tab/Shift+Tab, Enter/Space, Escape, Back/Forward, khôi phục focus/scroll | Thứ tự đúng luồng, đóng menu trả focus về nút mở, không trap hoặc mất đích focus |
| Khung nhỏ/PWA | Sidebar/drawer, safe-area, màn hình đứng/ngang, bàn phím ảo, standalone nếu được hỗ trợ | Điều khiển chạm được, nội dung không bị che; offline/write feedback chỉ khi source hỗ trợ |

Admin ERP có quyền, điều hướng và shell riêng; không tự đổi chúng trong spec
khách hàng này. Admin ERP được kiểm kê và xử lý ở lane Admin riêng trong master
checklist. Landing/trang chào mừng cũng có tiêu chí riêng trong spec control,
không bị xem là hoàn tất chỉ vì shell đã đạt.

## 4. Quy cách trình bày

- Dùng đúng token màu, kiểu chữ, khoảng cách và điểm gãy có trong current main;
  chụp/đo giá trị trước khi sửa. Không tự thêm màu hex hoặc font mới.
- Giữ nhận diện xanh–teal/xanh dương. Chế độ tối dùng nền xanh đậm và chữ sáng,
  không dùng nền đen thuần làm màu chủ đạo; mọi trạng thái phải tương phản rõ.
- Điều hướng và danh sách công cụ xếp thành cột dễ quét; chỉ toolbar cần thiết
  mới nằm ngang. Sidebar trên máy tính và drawer trên điện thoại phải cùng thứ
  tự, cùng trạng thái chọn và cùng quyền.
- Không để một nhãn bị cắt, đè, trùng hoặc đổi nghĩa giữa VI/EN/ZH. Ngôn ngữ
  chuyển theo nguyên câu; không trộn bản dịch cố định giữa các locale.
- Nút nổi không được che nút chính, lỗi trường, vùng upload, modal, bàn phím ảo
  hoặc nội dung kết quả. Nếu không tìm được vị trí an toàn thì ẩn/đưa vào menu
  theo đúng hành vi hiện có; không tự xóa chức năng.
- Motion chỉ là phản hồi phụ: không làm trễ thao tác, không khóa focus và không
  giấu nội dung khi `prefers-reduced-motion: reduce`.

## 5. Ma trận nghiệm thu

Chạy trên các viewport `360×800`, `390×844`, `768×1024`, `1024×768` và
`1440×900`; anonymous và authenticated theo route; VI/EN/ZH và sáng/tối nếu
source hỗ trợ. Dùng fixture QA cô lập; không dùng tài khoản/dữ liệu production.

- [ ] Mọi route/link trong ledger đi tới đúng trang hoặc trạng thái bảo vệ đúng;
      không có liên kết chết, vòng lặp, nội dung protected flash hoặc route bị mất.
- [ ] Fixed copy xen ngôn ngữ sai = `0`; chuỗi hiển thị, aria, trợ giúp, validation
      và thông báo đều theo locale đang chọn; không coi tên riêng là lỗi dịch.
- [ ] Tràn ngang = `0`; logo, chữ, điều khiển và form không bị cắt/đè ở mọi
      viewport; không mất focus/input khi bàn phím mở.
- [ ] Nút nổi trùng = `0`; mỗi điều khiển có thể tới bằng bàn phím và touch; focus
      trap = `0`; Escape/đóng menu trả focus đúng chỗ.
- [ ] Chuyển locale/theme không làm mất route hoặc tác vụ đang nhập nếu source
      hỗ trợ giữ trạng thái; giá trị dự phòng không làm lộ nội dung sai ngôn ngữ.
- [ ] Không có nhảy khung bất ngờ sau hydration/auth/menu; ghi CLS và trace theo
      cùng môi trường, phân biệt layout shift có chủ đích với lỗi.
- [ ] Không có lỗi console/unhandled rejection; request lỗi được phân loại; không
      có request rời localhost/QA trong lượt kiểm thử cô lập.
- [ ] Dark mode giữ nền xanh đậm/chữ sáng; đo WCAG AA cho chữ thường (≥4.5:1),
      chữ lớn và ranh giới điều khiển (≥3:1); vùng chạm ≥44×44 px.
- [ ] Reduced motion không để nội dung ẩn/chờ animation; toàn bộ shell vẫn dùng
      được và không phát lại entrance khi hydration.
- [ ] Nếu PWA/install không được source hỗ trợ, ghi `NOT_APPLICABLE` cùng đường
      dẫn/điều kiện nguồn; không tạo nút cài giả.

Không đánh dấu spec `PASS` chỉ bằng unit/contract test. Cần ảnh/DOM, console và
network capture, thao tác keyboard/touch thực trên browser, SHA chính xác và
review độc lập.

## 6. Kiểm thử và đầu ra

Trên checkout đã rebaseline, chạy tối thiểu:

```powershell
pytest -q tests/test_portal_i18n_bundle_contracts.py tests/test_customer_pwa_navigation_motion_contracts.py tests/test_auth_entry_motion_contracts.py tests/test_product_harmony_ui_contracts.py
node --test tests/customer-shell-locale-controls.test.mjs
```

Kỳ vọng: exit code `0`, mọi test được báo `passed`; browser acceptance matrix ở
mục 5 cũng phải lưu bằng chứng riêng theo `CURRENT_MAIN_SHA`. Nếu tên/lệnh test
đã đổi trên SHA mới, ghi lệnh thật dùng được vào từng phiếu trước khi giao; không
bỏ cổng browser để giữ nguyên lệnh cũ.

Đầu ra:

- `reports/audit/WEBAPP-PRODUCT-UI-ACTION-LEDGER.md`
- `reports/audit/WEBAPP-PRODUCT-UI-ACTION-LEDGER.json`
- Ma trận riêng trong `evidence/` có SHA, locale, theme, viewport, auth-state,
  console/network và ảnh/DOM; không chứa cookie, secret, PII hoặc dữ liệu thật.
- Cập nhật checklist tổng và bảng source-touch; không đánh dấu sản phẩm khác đã
  đạt nhờ shared shell.

## 7. Phạm vi file và điều cấm

Allowlist file chỉ chốt sau inventory trên SHA mới. Các vùng có thể phát sinh
trong phiếu: `static/portal/portal.js`, `static/portal/portal-i18n.js`,
`static/portal/portal.css`, `static/portal/portal-theme.css`,
`templates/portal_shell.html` và test/evidence liên quan. Đây là vùng ứng viên,
không phải quyền sửa sẵn.

Cấm trong spec này: sửa API/route server, engine, provider, pricing/quote, ví,
RBAC server, vòng đời job, dữ liệu, Bot, nội dung sản phẩm/editor, Admin ERP,
secret/environment, cài package, commit/push/PR/merge/deploy hoặc live production.
Nếu contract server thiếu, ghi `BACKEND_GAP`, không lấp bằng UI.

## 8. Điểm dừng và đóng sổ

Một nhóm shell/control mỗi phiếu; chỉ một phiếu được `RUNNING`. Trước khi qua
phiếu kế tiếp, reviewer kiểm diff, test đúng scope, evidence browser và cập nhật
checklist. Nếu có lỗi, mở lại `SPEC_ID` gốc và chạy lại comparator bị ảnh hưởng.

```ini
SPEC_ID=WEBAPP_SHARED_SHELL_UI_CLOSEOUT
PLAN=READY_NOT_IMPLEMENTED
CURRENT_MAIN_SHA=REFRESH_AFTER_WA35
CONTROL_LEDGER=NOT_CREATED
UNKNOWN_IN_SCOPE=NOT_MEASURED
TESTER=INDEPENDENT_REVIEW_REQUIRED
PRODUCT_CODE_CHANGED=0
PROVIDER_CALLS=0
WALLET_MUTATIONS=0
PRODUCTION_DATA_MUTATIONS=0
DEPLOY=NO
LIVE_PASS=NO
```
