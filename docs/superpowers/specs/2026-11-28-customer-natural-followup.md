# Lời dễ hiểu cho phần bắt đầu sử dụng, tài khoản và dự án

## Phạm vi và thứ tự

BASE `469f70063217814522b674272185227d93c8a08c`, nhánh
`codex/customer-natural-followup-20261128`, kho standalone; Issue689.
Đợt tài liệu PR822 đã gộp và cập nhật Web-only, máy chủ/cây/tệp giao diện
đã đối chiếu; không chạy lại các bước phát hành đó.

Chỉ đổi chữ cố định mà khách nhìn thấy. Không đổi xác thực, quyền, nút,
đường dẫn, tên/giá trị trường, trạng thái, thời hạn, yêu cầu xác nhận hoặc
dữ liệu khách. Không gửi thông tin đăng nhập, ENV, phản hồi thật, dữ liệu
khách hoặc mã Bot cho worker. Không mở dịch vụ có phí, ví/thanh toán,
đổi bộ tạo nội dung, dữ liệu production hay chuyển động.

| Thứ tự | Việc | Kết quả bắt buộc | Trạng thái |
|---|---|---|---|
| 1 | NATURAL-SETUP/ACCOUNT/PROJECT R1/R2 |150khóa có lời tự nhiên theo VI/EN/ZH | Đã có đề xuất;chưa ghép |
| 2 | Kiểm renderer thực các phần trên | Giữ dữ liệu/điều khiển;không sót chữ khó hiểu |33ca giữ điều khiển;vẫn có chỗ sót |
| 3 | NATURAL-STARTER-REST | Bảng mẫu/chi tiết/đang chờ/thiếu quyền đều dễ hiểu |29câu đã có đề xuất |
| 4 | NATURAL-ONBOARDING-REST | Hướng dẫn liên kết/tạm dừng/mã hết hạn và thiết lập không lộ thuật ngữ |18câu đã có đề xuất |
| 5 | NATURAL-SECURITY-REST | Bảo mật nói rõ khách cần làm gì;không lộ mô tả triển khai |74câu đã có đề xuất |
| 6 | NATURAL-DATA-REST | Phạm vi tải dữ liệu và yêu cầu xóa chính xác,dễ hiểu |35câu;hai nhãn Prompt chưa đạt,giao đúng hai nhãn lượt2 |
| 7 | NATURAL-PROJECT-REST | Dự án/tài liệu không còn giải thích triển khai thừa |23câu đã có đề xuất |
| 8 | Kiểm gộp chữ/renderer/input/lịch sử | Mỗi tiêu chí có bằng chứng,không chạy lặp nhóm đã đạt | Chưa chạy |
| 9 | Đưa lên kho,gộp,cập nhật web và đối chiếu | Một đợt liền mạch,không để nhiều bản treo | Chưa làm |

Các phiếu độc lập chỉ trả bảng chữ trong thư mục riêng, không ghi chung
ứng dụng. Dùng Antigravity4ExtraHigh hiện có, không kiểm tài khoản hoặc
đăng nhập lại. Ghép một lượt sau khi từng đề xuất được rà. Cùng lỗi còn
sai sau hai lượt mới tự sửa đúng câu đó; không tự nhận phần khác.

## Bằng chứng trước khi làm

33lượt renderer với bảng150khóa trong RAM giữ đúng dữ liệu và điều khiển.
Vẫn thấy chữ khó hiểu ở bộ mẫu và màn hình bắt đầu dùng. Từ “profile” ở
tài khoản là lệnh Telegram `/profile`, không phải nhãn tiếng Anh để dịch;
giữ nguyên lệnh và dữ liệu sao chép.

Đọc lại toàn câu cho thấy phần bảo mật/dự án còn những câu tiếng Việt
dịch nguyên mô tả hệ thống. Phải sửa ý diễn đạt, không chỉ xóa từ khóa.
Một fixture dự án dùng nhầm `projectsReadState`; phải dùng trường thật
`projectCenterReadState`, không sửa ứng dụng để hợp fixture.

## Tiêu chí

- [ ] AC1: Chữ cố định VI/EN/ZH trên các trạng thái trong bảng đều tự
  nhiên,không lẫn tên triển khai/viết tắt;ảnh và renderer là bằng chứng.
- [ ] AC2: Mọi trường/nút/quyền/đường dẫn/giá trị/hồ sơ khách giữ nguyên;
  không đổi thông báo lỗi thành thành công hoặc phần đang khóa thành mở.
- [ ] AC3: Giữ số giới hạn/thời gian và biến tên hiển thị cần thiết.
  Chỉ bỏ nhãn nội bộ `v1`, thuật toán `SHA-1` và tên cài đặt
  `{configuration}` vì khách không cần đọc, không đổi kiểm tra thực tế.
- [ ] AC4: Nội dung khách, tên riêng, lệnh có chức năng thật và mã liên
  kết tạm được giữ nguyên và hiển thị an toàn.
- [ ] AC5: Đối chiếu đúng phần dịch thay đổi;khóa/giá trị không giao giữ
  nguyên,không thêm chức năng,mạng,lưu trữ hay phụ thuộc.
- [ ] AC6: Kiểm tra liên quan,tài liệu bàn giao,bằng chứng đúng bản và
  cập nhật web;không suy toàn goal hoàn thành từ riêng đợt chữ.

Chi tiết cấu hình hoặc nhật ký không phải nội dung cho khách. Tuy nhiên
giới hạn sử dụng thật, mật khẩu, mã xác nhận, xác nhận xóa và quyền riêng
tư phải nói rõ bằng lời bình thường, không xóa để tạo cảm giác đã dùng được.

PROVIDER_CALLS=0; WALLET_MUTATIONS=0; PRODUCTION_DATA_WRITES=0.
Toàn lifecycle/thiết bị/Safari/offline/phiên production và chuyển động
bước cuối vẫn là các mục riêng, không được đánh dấu hoàn thành ở đây.

## Lượt giao và rà đầu

Năm worker hiện có terminal0;179câu bổ sung không trùng150câu trước,
tổng329khóa dự kiến. Chưa ghép mã ứng dụng. Hai nhãn dữ liệu giữ chữ
Prompt trái phiếu; giao lại đúng hai nhãn “Mẫu mô tả”,“Các mẫu mô tả bạn
đã lưu.” cùng EN/ZH. Không giao lại33câu khác, không tự sửa trước hai
lần sai cùng tiêu chí. Những đề xuất khác còn phải qua renderer/đọc nghĩa.

## Phụ lục đường hiển thị thật

Bản ghép riêng329khóa chạy91ca:45đạt/46chưa đạt. Không sửa mã ứng
dụng. Một số lỗi tiếng Anh do bộ dò của Root chặn cả “workspace” theo
nghĩa thông thường; đã phân biệt từ thông thường tiếng Anh với chữ
pha trong tiếng Việt. Không tính lỗi đó cho worker hoặc bỏ chốt dữ liệu.

Đọc các nhánh thật xác nhận thêm30khóa chưa giao và đúng một nhãn
viết tắt trong `renderAccountSecurity`. Bổ sung ba phiếu độc lập:

| Phiếu | Phạm vi chính xác | Kết quả |
|---|---|---|
| NATURAL-START-LABEL-GAPS |8khóa bộ mẫu/bắt đầu/liên kết | Không output/server/browser hoặc tên cài đặt trên màn hình |
| NATURAL-ACCOUNT-PROJECT-GAPS |22khóa tài khoản/dự án/mô tả dữ liệu | Câu tự nhiên cả VI/EN/ZH,giữ ý nghĩa giới hạn |
| NATURAL-SECURITY-METRIC-LABEL |Một dòng nhãn “MFA” | Dùng khóa mfaTitle đã có,không đổi mfaPosture hoặc bảo mật |

Đây là thiếu phạm vi ban đầu của Root, không reset số lỗi worker.
Không đổi chữ ký hàm hoặc cơ chế xác thực. Mọi byte ngoài dòng nhãn
được bảo vệ; hai bảng chữ chỉ đổi giá trị của khóa đã có.

Không coi những khóa trùng giá trị tìm được trong nhóm video/khác là
consumer thật; chúng không được sửa theo kết quả tìm chuỗi.

Đọc toàn bộ179câu VI phát hiện12câu trong ba phiếu cần rút/chỉnh ý:
sáu câu liên kết còn nhắc mã định danh không cần thiết;ba câu bảo mật
có lời bảo đảm lưu trữ rộng hoặc khiến khách hiểu lần đăng nhập hiện tại
bị kết thúc;ba câu dự án còn viết tắt hoặc gọi nhầm mục không có lịch sử
thành “chưa có hoạt động”. Giao lượt2 đúng12câu,không làm lại167câu.

Đối chiếu chỉ đọc phần tắt xác thực hai bước hiện có: các phiên cũ được
thay bằng phiên mới,mã khôi phục cũ hết hiệu lực. Chỉ sửa câu xác nhận để
phản ánh đúng điều đó, không sửa mã bảo mật hoặc thay đổi cài đặt.

## Phụ lục chốt câu hoàn chỉnh

Bản ghép riêng359khóa và một nhãn chạy86ca bị ảnh hưởng:
81đạt/5chưa đạt. Sáu ca thiết lập VI/ZH đã đạt ở lượt trước không
chạy lại. Năm lỗi còn lại cùng đi vào hai khóa chưa có trong phiếu:
`summary.companion` và `accountCenter.security.contactSectionBody`.
Đây là thiếu phạm vi của Root, không phải lỗi của worker.

Hai câu khác chỉ lộ vấn đề khi ghép thành đoạn hoàn chỉnh:
`accountCenter.profile.securityCheckDescription` có dấu chấm bị lặp
vì nơi hiển thị đã thêm dấu chấm; `accountCenter.profile.providerUnavailable`
lặp ý đăng nhập vì biến tên đã có “Sign-in”. Giao lại đúng hai câu
đó, giữ lịch sử lượt trước; không giao lại phần đã đạt.

| Phiếu | Phạm vi | Điều kiện nghiệm thu |
|---|---|---|
| NATURAL-RENDERED-SHARED-GAPS R1 |Hai khóa chưa giao nêu trên |Lời ngắn, dễ hiểu cả VI/EN/ZH;không đổi trạng thái |
| NATURAL-ACCOUNT-COMPOSITION R2 |Hai câu bị lặp khi ghép |Không dấu câu lặp hoặc “sign-in sign-in”;giữ biến tên |

Chỉ thêm hai khóa vào bảng359khóa, tổng361khóa dự kiến; vẫn đúng
một dòng nhãn trong mã hiển thị. Không xóa vùng tài khoản trong đợt
này. Kiểm lại năm ca chưa đạt, các phần dùng chung bị ảnh hưởng thật
và hai lỗi ghép câu; giữ bằng chứng nhóm đã đạt.

## Phụ lục rà nghĩa độc lập trước phát hành

Đọc độc lập toàn361bộ câu xác nhận12khóa cần chỉnh:10khóa còn danh từ
chung “Bot/bot” trong VI (không phải lệnh hoặc tên riêng);
`onboarding.challengeSubtitle` hứa mã không gửi tới mọi dịch vụ ngoài
trong khi phải gửi qua Telegram;`accountCenter.security.postureBody`
hứa toàn trang luôn ẩn mã đăng nhập trong khi trang có hiển thị mã
khôi phục dùng một lần. Giữ số lượt theo từng câu,không reset phiếu.

Giao đúng12câu còn lại trong ba thư mục đề xuất riêng. Không thêm khóa,
không đổi chức năng hoặc ẩn mã thật. Bổ sung trạng thái có mã liên kết
đang hoạt động,liên kết đang chờ,quay lại trang đã chọn,thiết lập xác
thực hai bước và tám mã khôi phục;kiểm toàn câu không chỉ dò từ khóa.
Tiếng Anh được dùng từ tiếng Anh thông thường,không đánh lỗi “bot”
trong EN chỉ vì đó là lỗi pha tiếng Anh trong VI.

Kiểm hiện tại sau ghép:104ca mới và2ca tài khoản đạt;đúng1tệp kiểm
lịch sử tài liệu dừng vì đầu vào chưa bóc lớp lời mới trước mốc cũ.
Thêm một inverse hữu hạn dành riêng đầu vào lịch sử theo đúng hai
record/361giá trị đã duyệt,không đổi fixture/pin/assertion cũ. Cho phép
hai helper JS/Python mới,một fixture mới,test mới và neo đầu vào ở
reader lịch sử thật sự bị ảnh hưởng. Raw primary luôn đọc ứng dụng
hiện tại,không dùng inverse. Đăng ký hai test mới trong workflow;
không thay các chốt hiện có hoặc quyền vận hành.

Trạng thái mã khôi phục/thiết lập vừa bổ sung xác nhận hai khóa ngoài
bảng361còn “Portal” ở EN/ZH:`accountCenter.security.mfaRecoveryBody`
và`accountCenter.security.manualSetupKeyBody`. Giao phiếu bổ sung R1
đúng hai khóa,không tính lỗi worker ngoài phạm vi;tổng363khóa.
Một fixture thiết lập thiếu thông tin bắt buộc đã sửa theo normalizer
thật,không sửa ứng dụng để hợp dữ liệu thử. Lượt27ca trước sửa có9đạt/
18chưa đạt,là bằng chứng cho Bot/cam kết sai và hai khóa vừa tìm.

## Phụ lục quét hết danh từ chung còn sót trong các nhóm đã khóa

Lượt gộp717ca sau sửa đạt705,còn12ca VI chưa đạt. Toàn bộ595ca lịch
sử đạt;110ca primary đạt. Mười hai lỗi đi vào các khóa chưa nằm trong
danh sách12câu rà nghĩa,không phải12câu đó sửa sai lần2.

Quét toàn giá trị cuối của các nhóm bắt đầu dùng,tài khoản,bảo mật,
dữ liệu,ngôn ngữ,bộ mẫu và dự án xác định đúng41khóa còn “Bot/bot”
hoặc “ID” trongVI. Giao ba phiếu rời theo khóa:21câu tài khoản,
13câu dữ liệu/ngôn ngữ/bộ mẫu/dự án,7câu liên kết/bảo mật. Khóa đã có
đề xuất được ghi lượt sửa đúng lỗi này;khóa chưa giao là thiếu phạm vi
Root,không reset lịch sử hoặc tính lỗi ngoài allowlist cho worker.

Bản báo cáo đọc361câu trước là rà đúng các câu đã giao,không chứng minh
những khóa chưa đổi đã sạch. Vì vậy chốt cả phép quét giá trị cuối của
các nhóm trên,không suy toàn ứng dụng đã sạch từ việc đọc bảng đề xuất.
Giữ nguyên lệnh thật/tên riêng,nhưng danh từ chung dùng “trợ lý Telegram”.

Nhóm44Python:35đạt/9lỗi trong4reader cũ chỉ do đếm declaration bằng3
ở epoch cũ. Chỉ đưa đầu vào I18N qua inverse hữu hạn mới tại bốn tệp:
test_account_security_locale_contracts.py,test_data_controls_locale_contracts.py,
test_interface_locale_navigator_portal_contracts.py,test_account_center_locale_contracts.py.
Không thay con số/assertion cũ. Những ca đã đạt không chạy lại vô ích.

Lượt41câu đã ghép đủ,quét các nhóm đã khóa không cònBot/ID. Bốn trạng
thái mở rộng giữ nguyên điều khiển,dữ liệu;nhưng sáu caaccount/data
vẫn đi vào sáu khóa chưa giao:avatar.presetAiBot,profile.upgradeAuditNote,
profile.linkedBody,profile.telegramConnected,dataControls.historyBody,
dataControls.requestSummary. Bộ dò substring còn trả các khóa trùng
giá trị ở video/support;không sửa chúng vì không phải consumer thật.

Bổ sung đúng10câu:5tên/nhãn ảnh đại diện,3câu tài khoản liên kết và
2câu lịch sử yêu cầu dữ liệu,bao gồm6câu còn lỗi nêu trên. Tên ảnh “Người
máy” thay Bot,nhãn tài khoản/thành viên bỏ chữWeb thừa;không đổi ID
hoặc ảnh. Đây là phạm vi thiếu củaRoot,không giao lại những câu đã đạt.
Preflight chặn đúng việc reset lịch sử:requestSummary đã có ở phiếu cũ
nhưng giữ nguyên ENRevision,cần lượt2 cùng tiêu chí;9khóa khác chưa
giao. Không gửi phiếu sai;không tính preflight củaRoot là lỗi worker.
Tổng413khóa dự kiến;vẫn chỉ2record mã ứng dụng. Màn hình chọn ngôn ngữ
riêng,ghi chú workspace mặc định và các yêu cầu lifecycle khác vẫn
ở checklist sau phát hành đợt này,không bị coi đã hoàn thành.

## Chốt tại máy trước phát hành

- [x] Đã ghép đúng413khóa;đổi thật406VI/331EN/340ZH;khóa dịch không thêm.
- [x] Ledger134primaryduynhất cókếtquảđạt ở lượt gộp/recovery phù hợp;
  không cộnglặp hoặc nhận là một lầnfullsuite mới.
- [x] 7pressurecuốigiữ2record/413giátrị;595lịchsửđãđạt;18Pythonliênquan
  ởnguồncuốikhép9lỗireadercũ,assertion/pin/fixturecũgiữ.
- [x] 36nativeđúngkhung đạt;2ảnhđầutrang đạt theo1+1recovery vàđãxem;
  không dùngảnhthiếukhung/cắtđầutrang làm bằngchứngmàu/bốcục.
- [x] Ràfailed-onlyđộclậpcuốicác12câusửa,51câubổsung,2câukhôiphục
  vàhelpers:APPROVE/khôngfinding;khônglặptests.
- [ ] Metadata/cúpháp/chốtnguồn/GitHub/triểnkhai/đốichiếucuốiphải có
  bằngchứngriêng. Toàn goalvàmọimụccònmởkhôngđượcđóngởđây.

Các mụcAC1..AC5chỉ nghiệmthuđúng413khóa/cáctìnhtrạngđãđo,không
phủnhậncácnhãncũcònWeb/giátrịmáyhoặctrangkhácchưagiao. Đợt tiếp
theosẽxửlýđúngnhữngđườnghiểnthịđãxácnhận,khôngthaychuỗichung.

Một kiểmtra runtime cũ của i18nbundle vẫn chốt nguyên văn starter.install.
Đã tái hiệnfailed-only1ca vì chữ mới,không phải mất khóa/ngôn ngữ.
Cho phép neo đầu vào của riêng _node_i18n_snapshot trong
test_portal_i18n_bundle_contracts.py qua cùnginversehữu hạn;giữ toàn
scriptassertioncũ và gửi sourceđãbóclớp qua stdin,không sửa ứng dụng.
Lượt gọi kèmba backendtestlocaleđãdừngđúnghaiPythonprocesscủaRoot
khi chờ trênWindows;không tínhAPI/lifecycleđạt hoặc thaycấu hình.

## Phụ lục lượt kho đầu — đúng một đối chiếu chữ cũ

PR824/HEAD8579271414e7395ed62c2ddd042834583ef78af3,
run46134749159:49/50đạt,1lỗi ở
`tests/document-workspace-natural-copy.test.mjs` — phép so giá trị
khóa cũ của đợt tài liệu gặpsummary.companionđã đổi hợp lệ. Các kiểm
renderer/transporttài liệu vẫn đạt;rawprimarymớichưatớibướcchạy.

Cho phép đưa riêng đầu vào phép so từ điển của test đó qua
customerNaturalHistoricalSnapshot,giữ nguyên mọi assertion/fixture/
kỳ vọng cũ. Không bóc sourcekhỏi runtimecác renderer/transporttài liệu;
rawprimarymới luôn đọcứngdụng hiện tại. Không sửa ứng dụng và không
chạy lại nhóm đã đạt ởlocal;kiểm failed-only1ca rồi cùngPR824chạy
đúngHEADmới. Giữlịch sửrunlỗi,khôngmerge/deploykhi chưa đạt.
