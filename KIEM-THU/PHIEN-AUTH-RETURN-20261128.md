# Phiên Tester AUTH-RETURN-01

Đang đọc và áp dụng skill owner-governed-codex cho task này.

Product=standalone WebApp;repo=manhtoangreensky-wq/toan-aas-standalone;
Issue689;branch=codex/auth-lifecycle-20261128;
BASE=fc9aef439d8fe7ecb00a2c68a167dad501f54eb9.
Nguồn case duy nhất: KIEM-THU/DANH-SACH-CASE.md.

Ứng dụng chỉ hai helper safeReturnPath trong portal-auth.js/integration.js.
Hai worker gemini-4-hydrogen-xhigh trả đúng proposal lượt1,NOT_RUN đúng
quyền;root ghép cơ học rồi tự kiểm. 8 dòng thêm/2 dòng thay; không sửa
auth backend/session/CSRF/OAuth/provider/wallet/Bot/engine/motion.

| Cổng | Bằng chứng |
|---|---|
| RED/GREEN |88case:36FAIL/52PASS trước;88PASS sau,0error |
| Mã ngoài helper |BASE cộng đúng1pair/tệp,ngoài byte giữ;syntax2JS đạt |
| Historical Node |241case/238PASS/3FAIL rawpin;đúng3FAIL khép bằng8selectedPASS |
| QA finite inverse |120Node/120PythonPASS;fixturehash97a8aad3…;giữ oldpins |
| Python affected |Safetyselector1PASS;physicalreader2PASS |
| Raw safety ngoài phạm vi |15FAIL/63PASS;15FAIL tái hiện trên immutableBASE,không sửa |
| Mounted actual app |4flow/8ảnh,390×844,0pageerror/console/unknownrequest,serverexit0 |

Mounted:VI/API,EN/internal,ZH/dot,ZH/validlang;actual publicform sai
mật khẩu→A→actual UI logout/confirm/POST/authme401→B cùngcontext,
A absent,passwordclear/storageclean. Tài khoản/DB/asset/secret giả
chỉ trong process QA;không đọc .env hoặc sửa môi trường máy.
PublicloginVI/EN/ZH;signedprofileVI,không suy signedEN/ZH.
Root đã xem ảnh dashboardVI và publicloginZH.

Một batch Python có3ca auth đầu đạt rồi dừng tiến triển ở nhóm backend
Gallery không đổi;root kết thúc đúng ownedprocess,không coi phần chưa
chạy làPASS. Lượt startup sandbox thất bại giữ nguyên evidence;
accepted browser runs dùng quyền tạo process QA,không đổi ứng dụng.

Không signedproduction/draft/race/AX/device/Safari/motion/offline-cache
proof. Không cộng các suite chồng nhau thành một tổng whole-app.
PROVIDER_CALLS=0;WALLET_MUTATIONS=0;PRODUCTION_DATA_WRITES=0.
LOCAL=TARGETED_PASS;CI=NOT_RUN;DEPLOY=NO;LIVE_PASS=NOT_TESTED.
