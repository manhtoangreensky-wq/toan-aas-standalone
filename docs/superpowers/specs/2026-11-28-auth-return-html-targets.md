# AUTH-RETURN-01 — quay về màn hình Web, không điều hướng sang API

Đang đọc và áp dụng skill owner-governed-codex cho task này.

BASE/runtime `fc9aef439d8fe7ecb00a2c68a167dad501f54eb9`;
branch `codex/auth-lifecycle-20261128`;standalone;Issue689.
AGC prerequisite đã giao PR820,CI46039186914haiSUCCESS/456QA,
Webdeploy46043920049SUCCESS,tree/source/assets/cache exact,
receipt689/7224786017 vàPR820/7224787056readback.

## READ và quyết định

Mounted auth baseline trênactualapp/DBtạm đã cóVI/ENluồngPASS trong
auth-mounted-SZtwAU;ZHrecoveryPASS auth-mounted-a5a6ON. Luồng dùng
formlogin thật,sai mật khẩu/cleanup,loginA→UIlogout/authme401→loginB
cùngcontext,Adisplayabsent. Không coi đây làfull draft/race lifecycle.
Signed profilefixtureVI;publicloginVI/EN/ZH,signedEN/ZH chưa covered.
Mixedrun thứchínloginthấtbại phùhợp8attempt/60sgiới hạnởapp.py;
khônglưuHTTPcodechínhxácnênkhôngcoiphânloại429làđãđođộc lập.
Khôngdisableprotection/xóathrottleDB;chỉrecoveryZHQAtemp/processmới.

Read-only16input helper probe xác nhậnpubliclogin safeReturnPath chấp
nhậnAPI/internal/encodedpaths;serverOAuthhelper cóAPI/internal/percent
fence riêng. integration.js cóhelper trùng tên với cùnggap.
Đây làfrontend return-target UX contract,khôngđổi session/login API,
authauthority/OAuth/backend hoặc coi làsecurityexploit đã xácminh.

Chốt return-path an toàn choWeb:

- Giữ UIpath/langvi/en/zh hợp lệ vàviệcchuẩn hóa trailing slash.
- Từchối exact `/api`, `/internal` vàmọi descendant của hairoot.
- Từchối percentencoding trong pathname,bấtkỳ segment `.`/`..`,
  controlU+0000..001F/007F sau trim;không “sửa” đường nguyhiểm thànhUIkhác.
- Giữ logic chốngexternal/protocolrelative/backslash/authloop/fragment/
  extraquery/duplicatelang vàunsupportedlang cósẵn.
- Prefix gần giống `/api-tools`, `/apiary`, `/internal-tools` vẫn hợp lệ.
- Khôngđổiquerylang hoặc field/nội dungkhách/credential/session.

## Allowlist

Ứngdụngchỉ `static/portal/portal-auth.js` và
`static/portal/integration.js`,mỗitệp đúnghelper safeReturnPath.
Khôngđổi signature/calls,khôngthêmsharedhelper/state/parserdependency.
QA CREATE `tests/auth-return-html-targets.test.mjs`;history/CIchỉmở
amendmentsauthựcnghiệmfailure/cổngchưagọi. Docs/spec/plan/Tester/
metadata theo local evidence;sauđó mộtPR/CI/merge/Webdeploy/receipt.
Khôngđọc/chạm10statefiles,ENV/secret/Bot/engine/provider/wallet/PayOS/
authbackend/schema/productiondata/motion. Chưa có quyền chạy paidAPI.

## Impact trước code

`git grep -n -E 'safeReturnPath\(|nextRoute\(|requestedPortalRoute\('`
trên haiappfiles vàtests đo3file/16linehits:
integration.js1026,1042,1043,27622,27666,27709,38205,38243;
portal-auth.js182,198,518,529,570;
test_portal_safety_contracts.py754,1203,1204
(khôngdùngfilecountlàmrisksmall).
Thayđổitrảvềunsafeinputcóchủđích,validinputs/calls/backendgiữ.

## Checklist vàcổng

note rõ là chia plan chi tiết ra thành từng spec kèm theo kết quả cần đạt để
qua spec khác, với spec đơn giản thì chạy nhiều spec một lúc, nếu spec phức
tạp thì làm từng spec.

- [x] AGCdeliveryreceipt vàmountedauthbaselineđãcó.
- [x] READ/impact/HTML-onlyreturnbehavior chốttrướcapplicationedit.
- [x] RED actualhelpers88ca:36FAIL/52PASS,0collectionerrors;
  artifactauth-return-html-targets-red-nov28.xml.
- [x] HaiAntigravity4ExtraHigh phiếuđộc lập,proposal-only,mỗitệpmộthelper.
- [x] Rootreviewcơhọc,88NodeGREEN/protectedoutsideexact,syntax2JS.
- [x] Consumer/source/browsertargetedverification;253sourcePASS,
  Node3FAIL→8selectedPASS,Python2physicalPASS;4mountedflow/8ảnh đạt.
- [ ] Docs/Tester/provenance/exactCI→mộtPR→merge/Webdeploy/receipt.
- [ ] Fullauth/draft/race/AX/device/Safari/signedproduction vẫnriêng,
  motioncuối. Khôngđónggoal từhaihelperfix.

Rootkhôngtựsửaapplicationtrước2workerfailurecùngacceptance;specmissing
doRootphảisửaphiếu,khôngtínhlỗiworker. No worker Git/VPS/browser/login.

## Amendment QA/CI — 28/11/2026, sau kết quả thực nghiệm

Hai worker R1 trả đúng proposal ngay lượt đầu; 88/88 primary đạt.
Hai tệp ứng dụng chỉ đổi đúng helper, mọi byte khác giữ theo Git BASE.
Kiểm ba module Node lịch sử: 241 ca, 238 đạt, 3 lỗi do fingerprint toàn
integration.js vẫn khóa mốc cũ. Không sửa hash, fixture hoặc kỳ vọng cũ.
Cho phép thêm inverse QA hữu hạn đúng hai cặp helper vào chuỗi historical
input; raw primary tiếp tục đọc trực tiếp ứng dụng, không qua inverse.
Allowlist QA: tạo fixture hai record, helper JS/Python và pressure test
JS/Python; nối tại gallery-native-runtime-historical.mjs và
gallery_native_transport_historical.py; áp projection trước đúng ba phép
đọc physical-source ở Node runtime và hai module Python lịch sử đã chỉ ra.
Phải giữ delta không liên quan, từ chối sửa/duplicate/partial helper mới,
no-op trên BASE và file không thuộc phạm vi. Không mở thêm application file.

Audit CI xác nhận test primary chưa được gọi vì workflow liệt kê từng tệp.
Chỉ bổ sung lệnh primary, kiểm cú pháp portal-auth và pressure tests;
không đổi trigger, quyền, môi trường, deploy hoặc các lệnh cũ.
Raw portal safety module có 15 lỗi câu chữ ngoài phạm vi trong portal.js
không đổi; giữ nguyên, phân loại bằng BASE riêng, không sửa app để khôi
phục chữ kỹ thuật cũ.

## Kết quả local đóng gói

Finite inverse120Node/120PythonPASS,không đổi hash/fixture/assertion cũ.
253affectedsourcePASS;241Nodehistory ban đầu238PASS/3FAIL,giữ238ca
vàchạy8selectedrecoveryPASS;không cộng thành whole-appcount.
Raw portal safety15FAIL đã tái hiện cùngIDtrên immutableBASE,63PASS giữ;
selector auth1PASS. Pythonme-probe/locale3cađầuPASS trước khi batch
backendGallerykhôngđổiđứng;batchđóđãkếtthúc,khôngcoiphầncònlạilàPASS.
Mounted4flowVI/API,EN/internal,ZH/dot,ZH/validlang390×844:
wrongpassword→A→UIlogout/authme401→Bsamecontext;8ảnh,
0console/pageerror/unknownrequest,serverexit0. SignedprofileVI;
khôngsuyfullauth/draft/race/AX/device/Safari/motion/production.
