# Hai biểu mẫu chuyển động ảnh và định dạng tham chiếu

TASK=LAST-TWO-OUTER; local accepted,delivery pending.
BASE_SHA=7f8753d5c35c6827a76fe9579041b1fe3812ba39; Issue #689.
Branch codex/last-two-planner-ui-20261110. Ngày nghiệm thu11/11,phiếu bắt đầu10/11.

Hai renderer bỏ intro/số đếm/aside giới hạn thực thi/header kỹ thuật và badge
trang trí. Giữ5/9trường,reference metadata,giá trị gốc,canCompose/canSave,
default/constraint/NoTransient và lời gọi kết quả/lưu. Biểu mẫu còn hướng dẫn
nguồn tham chiếu thật;không biến trạng thái không có tham chiếu thành sẵn sàng.
75khóa dùng thực tế mỗi locale,10349giá trị đã phát hành giữ nguyên byte.

## Nghiệm thu một lượt nhóm hoàn tất, sửa đâu kiểm đó

- Baseline24state:24controlpass,24localeRED/24clutterRED.
- R1gộp:reference8EN/ZHstateđạt,4VIstatecòn1từ;imageOLD0anchor/NEthiếu
  dấu backtick. Không áp dụng code lỗi. R2haiworker chỉ sửa2dấu kết chuỗi,
  mộtVIvalue và bỏ36alias không dùng.16affectedđạt,giữ8passcũ.
- Repo test54case:baseline27pass/27fail;27affectedcopy/catalogGREEN,
  giữ27control/oldcatalogpasses. Không chạy lại toàn nhóm sau sửa chữ.
- Nativebaseline4view:14mobile15px và20lightcontrastfailmin1,2653:1.
  Worker trả đúng3ruleCSS,không hex/important/layout/dark/desktopfont/routekhác.
- Nativefinal12/12 (2route×VI/EN/ZH×320tối/1440sáng):5/9controlđúng,
  42mobilecontrol>=16px;120/120label/helpsamplesđạt (60sángmin5,7971:1,
  60tốimin5,5225:1),12ảnh,không tràn ngang/lỗi/egress/productwrite.
  Nguồn trước/sau không đổi;server/browser do runner mở đã đóng.
- Native dùng phản hồi thật và trạng thái trống/bị khóa do tài khoản chưa có
  tham chiếu;không stubAPI để giả hoạt động. Tất cả ô đang khóa giữ native
  keyboard semantics;không chứng minh focus tương tác của form đang bật.
- Source:ngoài2hàmPortalgiữbyte,i18nchỉthêm75key/locale,CSSđúng3rule;
  15tệp nhạy cảm (kể cảintegration/backend/auth/provider/tiền/motion/deploy)khôngđổi.

Artifact: last-two-outer-candidate-nov10/affected-review.json,
video-inner-native-nov10-last-two-final-a/summary.json và12ảnh,
last-two-source-final-nov10.json. Tester session và tài liệu nghiệp vụ/đối chiếu
chức năng đã cập nhật trước push. CI/provenance/exactHEADmerge/exactSHAdeploy/
runtime/services/HTTPS là các cổng riêng,không suy LIVE từsource hoặcHTTP200.

Phần kết quả/biên nhận/saving và thông báo của hai công cụ này là bước tiếp
theo;không báo toàn trang hay engine đã hoàn tất từ việc dọn biểu mẫu. Toàn
goal vẫn có server-output/detail locale,khối thừa khác,auth/AX/device và motion cuối.
PROVIDER_CALLS=0;WALLET_MUTATIONS=0;PRODUCTION_DATA_MUTATIONS=0.
DEPLOY=NOT_YET;LIVE_PASS=NOT_TESTED;LESSON_CANDIDATE=NONE.
