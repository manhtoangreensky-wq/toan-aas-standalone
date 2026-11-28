# Rà soát trước khi cập nhật lời trong ứng dụng

BASE=469f70063217814522b674272185227d93c8a08c;
branch=codex/customer-natural-followup-20261128;Issue689;
product=standalone WebApp;repo=manhtoangreensky-wq/toan-aas-standalone.

## Mã và tài liệu hiện tại

Hai record ứng dụng:413khóa hiện có được ghi đè lời theoVI/EN/ZH và
một dòng nhãn xác thực hai bước. Không đổi keyset hoặc logic. Root chỉ
ghép đề xuất Antigravity4ExtraHigh đã kiểm,không tự viết logic ứng dụng.
Số đổi thật406VI/331EN/340ZH. Tài liệu nghiệp vụ và đối chiếu chức năng
đã cập nhật ởTAI-LIEU/01và02;masterplan giữ đúng các mục còn mở.

134primary theo ledger khác lượt,7pressure mới ở nguồn cuối;595ca
lịch sử đã đạt,không chạy lặp toàn nhóm. Python35/44ban đầu,9lỗi
readerđược khép bằng18ca liên quan,không nới assertion/pin cũ.
36lượt native đúngkhung đã đạt0lỗi/tràn/kết nối ngoài;haiảnhđầutrang
đã khép đúng vùngcuộn vàxemlại. Reviewerfailed-onlycuốiAPPROVE,
khôngfinding;không kiểm lại toàn361câu hoặclặptests. Cú phápvàmetadata
phải chốt đủ trước nguồn. Không dùngHTTP200hoặc đề xuất worker thay bằng chứng.

## Đối chiếu chức năng gốc

Nguồn đã đọc:docs/migration/WORKSPACE_SETUP_PROFILE_CONTRACT.md,
WORKSPACE_STARTER_KITS_CONTRACT.md,DATA_CONTROLS_CONTRACT.md,
docs/superpowers/specs/2026-08-03-account-center-locale-clarity-design.md,
sourcevàhợp đồng kiểm tra ởBASE.

Thiết lập vẫn chỉ lưu lựa chọn; bộ mẫu vẫn tạo dự án/tài liệu/việc chứ
không tạo đầu ra xử lý;dữ liệu vẫn tải phạm vi hẹp hoặc yêu cầu xem xét,
không xóa ngay;liên kết Telegram và bảo mật vẫn do điều kiện cũ quyết định.
Rút lời giải thích nội bộ không biến phần bị khóa thành dùng được hoặc
mở rộng xuất/xóa sangtệp,Telegram,tiền hoặc dịch vụ xử lý.

## Chỗ làm việc cho người kiểm tra

TESTER_PROJECT_ID=CUSTOMER-NATURAL-20261128;
TESTER_MANIFEST=KIEM-THU/PHIEN-CUSTOMER-NATURAL-20261128.md;
CASE_SOURCE=KIEM-THU/DANH-SACH-CASE.md;TRACKER=Issue689.
Ngày28/11đã kiểm kho công khaiđúngmain469f7006,Issue689OPEN,
23nhãn gồm đủ12nhãn kiểm tra;hai mẫu issue hiện có được giữ. Không tạo
tracker hoặc bảng mới,không đăng nhập/xin quyền tài khoản lại.

PUSH_GATE=READY;TESTER_PROJECT_STATUS=READY;
CI=NOT_RUN;MERGE=NO;DEPLOY=NO;SIGNED_PRODUCTION_UI=NOT_TESTED.
PROVIDER_CALLS=0;WALLET_MUTATIONS=0;PRODUCTION_DATA_WRITES=0.

## Chốt bằng chứng cục bộ

Lớp kiểm tra mới dùng134kết quả primaryduynhất theoledger,mỗi ca lấy lượt
cuối có hiệu lực;không phải một lần chạy fullsuite. Bốn readerPython
đã khép18ca liên quan;runtimebundlecũ được bóc đúngsourcequa stdin,
failed-only1/1đạt. Lượt ghép kèm backendtestngoài phần chữ đã dừng
đúng tiến trình riêng trênWindows,không tínhAPI/lifecyclePASS.

Node --checkcho2tệp ứng dụng,py_compileapp.py/helpervàgitdiff--check
đều mã0ởsourcecuối. Có cảnh báo chuyểnLF/CRLFdoGit,không đổi bytes
đối chiếuLF. Không thaycấu hình hoặc bỏ assertion đểlàm xanh.

TASK=CUSTOMER-NATURAL-20261128_LOCAL_TARGETED_PASS;
BASE_SHA=469f70063217814522b674272185227d93c8a08c;
HEAD_SHA=WORKTREE_SOURCE_FREEZE_PENDING;
FILES_CHANGED=2_APPLICATION_RECORDS_PLUS_DECLARED_TEST_DOC_INPUTS;
TESTS=PRIMARY_LEDGER134_CURRENT_HISTORY7_PYTHON18_PLUS1_NATIVE36_CAPTURE2;
BASELINE_FAILURES=OLDER_WORDING_AND_DOCUMENTED_HISTORY_EPOCHS;
BRANCH_FAILURES=0_IN_APPLICABLE_TARGETED_LEDGER;
NEW_FAILURES=0_IN_DECLARED_PROTECTED_COMPARATORS;
PROTECTED_COMPARATORS=RAW_CONTROLS_DATA_COMMANDS_KEYSETS_OUTSIDE_ONE_LABEL;
DEPLOY=NO;LIVE_PASS=NOT_TESTED;LESSON_CANDIDATE=NONE;
BLOCKERS=EXACT_HEAD_DELIVERY_GATES_PENDING_NOT_OWNER_PERMISSION.

Metadata:67tệpđãđóngdấu;32PASS/1WindowsPOSIXbaseline/0newfailure.
Source test/scriptđồngbộgiữnguyênBASE;LinuxCIphảiqua,khôngbỏassertion.

PR824lượtkho46134749159dừng49/50đạt vì olddocumentdictionary
comparatorgặp nhãn đã đổi đúng. Chỉneo snapshotđầuvào tại phépso đó;
failed-only1/1đạt,khôngđổisourceứngdụng hoặc rawrenderer. Bảnkiểm
mới phải đạt trướcmerge/deploy;không xóalịchsửlượtlỗi.

CI2run46135662732đạt141/141nhómmớivà50/50tàiliệu;72oldmembership
comparatorfailcùngnhãntổnghợpđãđổi,khônglỗitiền/giá/dữliệu.
InputI18Ngiữđúngepochcũ,72failed+12liênquanđạt84/84. Noappchange.
CI3đúngHEADmớivẫnbắtbuộc,khôngdùngkếtquảlocalđểbỏgate.

ĐoảnhhưởngAccountsnapshot45ca:39đạt/6failđầuvàolịchsử;đúng14ca
failed/pressureliênquanđạt,khôngsửanguồnứngdụng. Bảnchínhhiện
564f5ded/PR823,tươngthíchhaiappfileđợtlờikhôngđổitrênmain;chỉhai
JSONprovenancexungđột.CầnmergemainvàregeneratedúngnguồntrướcCI3.
