# MU-NATIVE-VALIDATION-ERROR-LOCALE-B — lỗi có hướng xử lý, không rò raw copy

Ngày23/10/2026. LOCAL_UI_ACCEPTED_WITH_D0,deliverypending. A+C HEADfc8deb6,CI39950590927bothSUCCESS,
receipt Issue6646364623486. READ hoàn tất trước BUILD.
Standalone WebApp, repo manhtoangreensky-wq/toan-aas-standalone, PR661/Issue664.
Root `C:/Users/toann/Documents/Codex/_webapp-r218-voice`; branch
`webapp-r218-billing-ui-20261022`; BASE `fc8deb6a96566021a58cdcdf8ab77ed6796539cd`.
Owner “tiếp tục”; làm WIP trước, Flash3.8 nền, không IDE/login/settings; motion cuối.

## READ và nguyên nhân đã đo

Real payload function nhận mô tả1ký tự trả cùng câuVI ở VI/EN/ZH (6probe).
Hai payload functions có5literal errors mỗi hàm;3safetyhelpers có3literal
mỗi hàm;2action có10failureliteral sites (8throw+2inline),28unique strings.
Catch chung đang ưu tiên payload.message/error.message raw; catalogue tốt ở
renderer không dịch được late-error. Inventory localsource/probe ở
`../qa/r218-music-sfx-errors-20261023/inventory.json`, không gửi runtimeQA cho worker.

Không sửa nguyên nhân bằng nới validator hoặc đổi shared helper. LátB chỉ đổi
presentation lỗi của đúng `music-direction-preset-compose` và
`sfx-cue-sheet-compose`. Payload, guard/success validators, safety helpers,
classifyError/api/auth/CSRF/capability/epoch/finally/body/merge giữ nguyên byte.

## Thiết kế cố định

Thêm `musicSfxEditorialErrorText(action,error)` cạnh helper feedback hiện có.
Action khác hai tên chính xác trên trả null, không đọc message/payload. Với
hai action: top-level numeric HTTPstatus401/403 → keyauth; error có payload khác → retrygeneric,
không hiển thị raw server. Với localError khôngpayload, đối chiếu **exact**
các câu lỗi source đã đọc vào nhóm bên dưới; không regex đoán lý do. Unknown/
null/primitive → retry. Dùng `musicSfxEditorialFeedbackText(tool,"error.KEY",
fallbackVI)` và không đổi chữ ký helper cũ. Không gọi request/merge/navigation.

Nhóm map chính xác: route→route; capability→unavailable; payloadshape/type→fields;
brief length→length; invalidlanguage/preset→selection; Botcommand/markup/URL/
systemhandle/controlcharacter→content; payment/secret→sensitive; unsafe boundary/
receipt→receipt. Hai câu inline failure→retry. Không dò input khách để phân loại.

Chỉ thay2inlinefailure setters bằng bản dịch retry. Tại catch cuối handleAction,
tính text của helper mới; nếu khácnull dùngtextđó, nếunull giữ nguyên biểu thức
raw/fallback hiện có. Không sửa bất cứ nhánh payment/feature nào quanh catch.
A pending/success/copyright và C strictguard giữ nguyên từng byte.

### Copy chốt —10keys mỗi namespace,20cataloguerows

| KEY | VI Music | EN Music | ZH Music |
|---|---|---|---|
| route | Mở lại trang Hướng âm nhạc trước khi gửi. | Reopen Music Directions before submitting. | 请重新打开音乐方向页面后再提交。 |
| unavailable | Chức năng lập hướng âm nhạc hiện chưa sẵn sàng. Vui lòng quay lại sau. | Music Directions is not available right now. Please come back later. | 音乐方向暂不可用，请稍后再来。 |
| fields | Kiểm tra mô tả và các lựa chọn trước khi gửi. | Check the description and your selections before submitting. | 提交前请检查描述和选项。 |
| length | Mô tả cần từ 2 đến 500 ký tự. | The description must contain 2 to 500 characters. | 描述须为2至500个字符。 |
| selection | Chọn một hướng và ngôn ngữ có sẵn trong biểu mẫu. | Select a direction and a language available in the form. | 请选择表单中的方向和语言。 |
| content | Viết mô tả bằng lời, không nhập liên kết, mã lệnh hoặc mã tệp. | Write a plain-language description without links, commands or file references. | 请用文字描述，不要输入链接、命令或文件引用。 |
| sensitive | Xóa mật khẩu, mã xác thực, khóa truy cập và thông tin thanh toán khỏi mô tả. | Remove passwords, verification codes, access keys and payment details from the description. | 请移除描述中的密码、验证码、访问密钥和付款信息。 |
| receipt | Chưa nhận được kết quả hợp lệ cho nội dung này. Hãy gửi lại. | No valid result was received for this brief. Please submit again. | 未收到此摘要的有效结果，请重新提交。 |
| auth | Phiên làm việc không hợp lệ hoặc chưa có quyền. Hãy đăng nhập lại. | Your session is invalid or lacks access. Please sign in again. | 会话无效或没有访问权限，请重新登录。 |
| retry | Chưa thể lập hướng âm nhạc. Kiểm tra nội dung và kết nối rồi gửi lại. | Music directions could not be created. Check the brief and connection, then submit again. | 无法创建音乐方向，请检查摘要和连接后重新提交。 |

SFX dùng6key fields/length/content/sensitive/receipt/auth giống Music; selection
là “Chọn một loại hiệu ứng và ngôn ngữ có sẵn trong biểu mẫu.” / “Select an
effect type and a language available in the form.” / “请选择表单中的音效类型和语言。”
Route: “Mở lại trang Bảng hiệu ứng
trước khi gửi.” / “Reopen the SFX Cue Sheet before submitting.” /
“请重新打开音效提示表页面后再提交。” Unavailable: “Chức năng lập bảng hiệu ứng
hiện chưa sẵn sàng. Vui lòng quay lại sau.” / “The SFX Cue Sheet is not available
right now. Please come back later.” / “音效提示表暂不可用，请稍后再来。”
Retry: “Chưa thể lập bảng hiệu ứng. Kiểm tra nội dung và kết nối rồi gửi lại.” /
“The SFX cue sheet could not be created. Check the brief and connection, then
submit again.” / “无法创建音效提示表，请检查摘要和连接后重新提交。”

## Allowlist và bước thực hiện

Builder chỉ3files: `static/portal/integration.js` (helper mới+2inline+outertoast),
`static/portal/portal-i18n.js` (20rows), `tests/music-sfx-error-feedback.test.mjs` mới.
Codex quản lý spec/master/state/evidence/Tester/docs. Không thay existingtests
để ép PASS, không portal.js/CSS/motion/backend/API/auth/ENV/data/provider/ví/Bot.

1. Test mới (2–5phút): catalogue thật VM riêng/plainbridge, không sửa frozen.t;
 realhelper/error-displayconsumer, literalexpected VI/EN/ZH. Baseline missing
 helper phải failassertion rõ, khôngReferenceError. Ít nhất consumer length
 thực bằng payloadfunction thật và outercatchtoast thật; không chỉsourcegrep.
2. Helper+20rows (2–5phút): scopeactionchínhxác, exactmessages→keys, no rawunknown.
3. Wire2inline/outertoast (2–5phút): nonMusic fallback byteequal; không đổi gate.
4. Codex chạy RED trước source rồi GREEN/focused/full/Python/protected/browser.

## Acceptance/checklist công khai

- [x] READ/source inventory và6realfunction probes; rootcause/literal sites đã đo.
- [x] B01 realerrorpresentation/catalogue/consumer RED→GREEN VI/EN/ZH;
 knownlength/shape/selection/safety/route/capability/receipt,401/403,unknownnull.
- [x] B02 không raw server/message/URL/secret lêntoast; unknownpayload→retry,
 nonMusic action→null/oldfallback, khôngprovider/wallet/request mới.
- [x] B03 payload/safety/validators/API/auth/A+Cbyteunchanged;onlyhelper/2inline/
 outertoast/20rows. No signature/refactor/sharedvalidationchange.
- [x] B04 signedQA2routes×VI/EN/ZH×light/dark×390/1440: invalidbrief0POST;
 transportabort có chủ đích→localizederror/retry, draft/focus/busyrecover;
 normalnative3results/A+Cregression. Faultinjection được ghi riêng, khôngmockresponse.
- [ ] B05 focused/fullNode/Python/protected/syntax/diff/review; docs/Tester/
 prepush/provenance/push/readback/CI/receipt664 trước khi chuyển spec.

Verify: `node --test tests/music-sfx-error-feedback.test.mjs` RED assertion rồi
GREEN; fullNode concurrency2; Python4native/portal hiện21/21; A+Cfocused47/47.
Flash3.8 mộtworker, tốiđaR1/R2sameB01, khôngR3; chỉsource/test/ticket/MAP
stdouteditJSON, khôngtool/filewrite/Git/ENV/runtimepayload. Codex áp apply_patch.

### R1 review, trước R2 cùng B01

OuterworkerERROR500.306589s, innerJSON controlchar28661; validTEST_FILEprefix
được áp nguyên văn để chẩn đoán, production chưa áp. Diagnostic0pass/10fail:
literalbackslashn extractor, firstpaymentaction nhầm outercatch, realpayload
không được trích. Không dùng lỗi harness làm productRED. R2 cùngB01/noR3:
NLchar10/fullcatchmarker/sameVM/compacttest; top-level numeric HTTPstatus,
không suy auth từpayload.status (envelope là string). ActualbrowserRED vẫn
giữ riêng: zh invalidURL hiệnVI,0POST. Worker chỉ source/test/spec/MAP.

## Sau B, không bỏ sót

### Checkpoint VERIFY — focus dependency D0, không bỏ tiêu chí

BcleanRED2pass/4fail→sourceR2+2one-linecorrectionsGREEN6/6;focused53/53,
fullNode1006/1006,Python21/21. R2sameB01harness vẫn sai route/capabilities/
epoch và1Englishliteral; primary sửa test sau2lượt, khôngR3. Sourcecorrections:
own-propertylookup (unknownconstructor từng rơiVI), exactactionguard trước
outerhelpercall (6libraryVMtests từng thiếu helper; nay18/18 xanh, existingtests
không đổi).15protectedfunctions/10files byteequalBASE.

Browser copy/validation/transport/retry đạt24/24, review53+18/Critical0/Important0.
Nhưng strictfocuscheck FAIL: disabledbuttonlàmfocusvềBODY. Đối chiếu actualQA
BASE vàcandidate bằng2JS-source-overlays cho cùng nativePOSTabort: cảhai
BUTTON→BODY(disabled)→BODY(reenabled), trước khi feedback hiển thị. Không API
responsefixture; baselinefocusbug, khôngregressionB. B04focus **chưa tick**.

Dependency riêng `MU-NATIVE-ERROR-FOCUS-D0` phải trả focus button trước khi B
ACCEPTED/delivery; không hạ acceptance hoặc coi24copyconfigs làfocusPASS.
D0 là lỗi baseline riêng, không reset hai handoff củaB. Giữ QA39795/51738
để verify; không pushB trước D0gate. Detailspec/checklistD0 trước BUILD.

### D0 resolved — final local gate

D0R1/R2productionidenticalverbatim10logicalfocuslines; testR2bổsung2cases
sauhaiF02coveragegaps, khôngR3. CleanRED8pass/2focusfail→GREEN10/10;
combinedfocused63/63, fullNode1016/1016, Python21/21. Independent81/81,
Critical0/Important0. Strictactualbrowser24/24 trên combinedintegrationSHA
5ac46bc3fccdc893f73fa07efa3e0d56677606f2bf6d2617f5a540c5f8339912:
focusrestored24,validation0POST,24intentionalaborts+24native retrysuccess3texts,
unexpectederror/external/unapprovedwrite/overflow0. Expectednetworkerrors24
ghi riêng. RawSHA2b2c75da4b950ce78421064e7d11e1a35dcdae2562c86d706d2aa2b1b7535946.
B04giờmớiđượctick; không hạ criterion. QA39795stoppedexit0,tempclean,
listener51738=0. Deliveryprepush/newCI/receiptchưaxong; audio/Botparity/LIVEmở.

MU-NATIVE-PRESENTATION-COPY-D sẽ xử lý fielddescription placeholder/helpVI và
boundary/emptytechnicalcards. Chưa sửa renderer hoặc ẩn card ởB; D phải có
READ/contract/browser riêng, giữ sự thật text-only và không làm audio giả.
Generation/player/download/save/reuse/canonical/Botparity/M0 còn mở.
PROVIDER_CALLS_APP=0; WALLET_MUTATIONS=0; PRODUCTION_DATA_MUTATIONS=0;
DEPLOY=NO; LIVE_PASS=NOT_TESTED; GOAL=ACTIVE; MOTION=LAST.
