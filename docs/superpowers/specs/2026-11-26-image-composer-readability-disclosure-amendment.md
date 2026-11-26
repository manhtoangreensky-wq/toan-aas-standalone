# COMP-COLOR / COMP-FONT / COMP-GOAL — ba lỗi hiển thị đo được

Nhánhcodex/image-composer-locale-20261126,BASE6ec003db,Issue689.
Giữ44record đã nhận; không đổi recipe/API/provider/luồng ghi/khách/motion.

Audit Chrome qua HTTP localhost, renderer/CSS/handler thật,48view
VI/EN/ZH×light/dark×360/375/768/1440×empty/result:
1536samples,1488enabled đo được,24enabledgradient chưa kết luận;
0pageerror/0externalrequests/0overflow.624findingobservations gồm
48ôcustomgoal dư,288inputfont15px và288cặp màu dưới4,5:1;
minimum1,0029432302. Đây là observations lặp theo view, không phải
624lỗi độc lập. Bản initial0view lỗi selectorQA đã giữ riêng, không
tính worker hoặc app. Ảnh375sáng đã mở xác nhận chữ gần trắng trên trắng.

## COMP-COLOR (một record CSS)

Chỉ `portal-theme.css`, một insertion trước comment customerComposer.
Trong `.portal-page.portal-image-composer-customer`, ghép surface/ink
theo token cho intro/form/result/prompt/variants/review/meta và các
textrole tương ứng; primarybutton pair tokens light/dark riêng, disabled
không đổi. Không đụng font/geometry/layout/copy/handlers/other route.
Kỳ vọng mọi enabled sample đo được≥4,5:1; gradient/opacity báo riêng,
không tự nhận pass. Không đổi source CSS chung QuickPlanner.

## COMP-FONT (một record CSS, anchor khác COLOR)

Chỉ scope customerComposer. Input/select/textarea16px; nội dung mô tả
pre14px, các nhãn mô tả/meta/review14px; kicker/eyebrow/ordinal12px.
Không đổi fontfamily, layout, min/max/required, palette hoặc motion.
Các nút đã44px giữ. Rà longtext/wrap/overflow sau font thay.

## COMP-GOAL (bốn record JS)

Chỉ custom_goal của form `image-prompt-compose`: thêm dynamicRequired
cho field metadata, helper riêng, changehookgoal_code và hook sau render.
Mục tiêu không phảicustom thì ẩn/disabled/notrequired, không vào FormData;
chuyểncustom thì hiện/required. Giữ giá trị trong phần tử khi tạm ẩn
để không mất nội dung khách khi đổi lựa chọn, không thêm storage/draft
map hay giữ qua session. Giữ capabilitydisabled của goal selector.
Không đổi stylehelper,validator/payloadschema, routes hoặc state.

## Gates

- [x] Source,48viewRED và ảnh thực tế đã rà; nguyên nhân scope màu cũ,
  font15px và thiếu goal-specific disclosure được xác minh.
- [x] Ba CODEworker4ExtraHigh độc lập, exact1/1/4records, không sourcewrite.
- [x] Apply đúng6amendment ban đầu; thêm labels/pseudo/focuspriority
  bằng các record riêng bên dưới, không sửa record gốc.
- [x] Browser48viewGREEN cuối physical-r8-final; realgoal change/
  FormData/value retention/required/focus/keyboard và không ô trống.
- [x] Otherroute18 giữ title/attributes/controls; source/history19 đạt.
- [ ] Draft/auth lifecycle/fullappBrowser riêng; CI/delivery cùng batch,
  không PR/issue rời. Không suy capability runtime từ component thường.

Không dùng số đo48view để kết luận signedproductionUI,device/Safari,
đầu ra thật/provider hoặc hoàn tất toàn goal. Motion vẫn cuối.

## Phụ lục nhãn field sau rà ảnh

Ba workerR1 đã trả đúng1/1/4record, root áp đúng6record;39gốc bất biến,
amendments từ5lên11, tổng50record. Browserphysical-r3 đạt48view trong
phạm vi selector:1896samples,1872enabledmeasured≥4,5,min5,47325,
0uncertainenabled/0error/0external/0overflow;24disabled báo riêng.
Không được gọi đây là toàn bộ text đã đạt: mở ảnh dark375 phát hiện
fieldlabel cũ chưa có trong selector QA. Phép đo bổ sung1view tái hiện
5label dưới chuẩn,min1,2621956. Đây là thiếu selector trong spec/QA,
không phải codefail workerR1 hoặc lỗi mới được che bằng sửa assertion.

Giao một record bổ sungCSS: chỉ
`:root .portal-page.portal-image-composer-customer .portal-field label`
`color: var(--portal-ink)`. Không đổi font/background/geometry/required
hoặc bản ghi màu trước. Worker chỉ trả record; rawfixture thêm amendment
riêng, tổng51record. Sau đó chạy48view với selector label bổ sung,
mở ảnh sáng/tối để rà thật. Không dùng số1872 cũ thay bằng chứng cuối.

Phép đo bổ sung placeholder/focus theo AC ở2view375: nền sáng có
placeholder3,2328:1 và focusring1,4793:1, nền tối tương ứng5,5225 và
9,8604. Hai loại này chưa được phép đo textnode trước bao phủ. Bổ sung
một recordCSS riêng (không sửa record trước): placeholder của input/
textarea đang bật dùng `--portal-muted`, opacity1; outline-color của
input/select/textarea `:focus-visible` dùng `--portal-focus`, không đổi
độ dày2px/geometry/handlers. Tổng dự kiến52record.
Sau đó48view đo đủ fieldlabels/placeholder/keyboardfocus; text≥4,5,
focus≥3. Không suy rộng48viewtext trước thành các trạng thái chưa đo.

## Phụ lục ưu tiên màu viền bàn phím — COMP-FOCUS-PRIORITY R1

Phép đo physical-r7-final đã hoàn tất 48 view: 2.112 mẫu chữ đang bật
đạt ít nhất 4,5:1; placeholder đạt, nhưng còn 12 quan sát focus ở giao
diện sáng chỉ đạt 1,4793:1. Review độc lập xác nhận rule
`portal.css:4215` đặt shorthand `outline: 2px solid #5eead4 !important`,
nên declaration màu thường trong scope Composer không thắng được.
Đây là thiếu ưu tiên CSS trong spec của người điều phối, không phải
worker trả sai record đã giao. Giữ nguyên bằng chứng RED và 52 record.

Giao đúng một record bổ sung trong `static/portal/portal-theme.css`:

```css
:root .portal-page.portal-image-composer-customer :is(.portal-input, .portal-select, .portal-textarea):focus-visible {
  outline-color: var(--portal-focus) !important;
}
```

Chỉ thêm ưu tiên cho màu của đúng rule hiện có. Không đổi rule chung,
độ dày 2px, khoảng cách viền, bóng, bố cục, xử lý form, locale, auth,
API hoặc motion. Worker Gemini 4.0 Extra High chỉ trả một OLD/NEW;
người điều phối đối chiếu rồi thêm amendment thứ 14, tổng 53 record.

- [x] Worker trả đúng một record, không ghi mã ứng dụng.
- [x] Phép đo vật lý cuối đủ 48 view, chữ/placeholder ≥4,5:1,
  focus ≥3:1 và dày ≥2px; không tràn ngang/lỗi/request ngoài.
- [x] Giữ nguyên năm source pin và inverse của 39 record gốc + các
  amendment; so sánh 18 route/locale ngoài Composer.
- [x] CI đăng ký thêm feedback-locale, 45 nhánh feedback-actions,
  note formatter và other-routes; gate HTTP Ubuntu vẫn bắt buộc.

Không dùng kết quả component localhost để kết luận đã đăng nhập thật,
đã ghi dữ liệu thật, đã lên production hoặc hoàn tất toàn goal.

Final physical48view:2112enabledtext samples đo được,min5,4732500812;
placeholdermin5,5224777212;24focusobservationsmin5,8600809480,vòng2px;
24disabledsamples báo riêng.0finding/error/externalrequest/overflow.
Nguồn/history19,otherroute18đạt; compile/syntax/diffcheckexit0.
Review correctionC0/I0/M0. Hai Important ban đầu đã khép; chờ CI.
