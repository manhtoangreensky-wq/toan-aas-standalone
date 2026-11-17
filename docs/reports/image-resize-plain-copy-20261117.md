# Câu chữ đổi kích thước ảnh — nghiệm thu local

SPEC_ID=IMAGE-RESIZE-PLAIN-COPY-20261117;Issue689.
BASE_SHA=b6c717bc65c1abcb4f9ba0d65861225d09fb1691,PR758 đã giao.
Branchcodex/image-resize-plain-language-20261117.

Ba proposal AntigravityGemini3.8FlashHighR1 được ghép đúng33existingrows,
99giá trị VI/EN/ZH;không đổi khóa/thứ tự/option scalar/giới hạn. Chỉ một
tệp ứng dụng thay đổi:portal-i18n.js. Không điều phối tự viết apprepair.
Tên/nội dung tệp khách được giữ nguyên và escape;không dịch chữ của khách.

## Bằng chứng hành vi và lỗi bộ kiểm tra được phân loại rõ

- Prior12rowbaseline36cases1656.0354ms giữ,không chạy lại cả nhóm.
  Kiểm lại phạm vi phát hiện3submitcases thực ra bị bộ đọc cắt ở section
  tìm ảnh lồng bên trong;33case còn lại là contentRED. Chỉ3submit được đo
  lại trên đúng BASE bằng reader đúng:3contentRED1142.4129ms.
- New21rowsbaseline63cases:2PASS/49contentRED/12readererrors2496.7397ms.
  Chỉ12field-helpcases được sửa reader id-before-class và đo lại:
 12contentRED1713.0199ms. Không tính lỗi reader thành lỗi worker.
- GREEN một nhóm36tệp789cases:786PASS/3submitreadererrors231474.7303ms.
  Chỉ3submit bị ảnh hưởng chạy lại:3PASS2129.071ms.
- Ba Image history comparators mới,3PASS2450.3292ms:chỉ ba nhãn Resize
  dùng lại cùng khóa được thay;HTML ngoài nhãn,controls/title giữ.
  Không gọi đây là một lượt792ca xanh và không rerun786ca đã đạt.
- Rawbehavior chạy fullphysicalsource,99actualslots cho guard/loading/
  failed/ready/empty/permission/disabled/cards/fields. Các giá trị fit label
  EN/ZH đã đúng từBASE,không giả thành lỗi trước sửa.

## Giao diện thực

NativeR1 không có case hoàn tất vì typedGET timeout10s;nguồn/binding giữ,
owned0,không lỗi page/console/egress;nguyên nhân timeout đầu vẫn UNKNOWN.
NativeR2 GET đã về nhưng đo text coi nội dung ngoài scrollport là clipped.
Chỉnh riêng observer cuộn thật từng text node vào vùng xem rồi đo Range/
ancestorclipping,giữ ngưỡng và giới hạn. Không đổi app,không nới timeout.
R1/R2 đều0acceptedcases;không nhận đã đạt hoặc tính là worker-codefail.

NativeR3 đạt6uniqueVI/EN/ZH×375light/1440dark trong một freshownedrun:

-144READYconsumerassertions và120textvisibilitychecks sau real scroll;
  phần9keys không thuộcREADY được rawrenderer kiểm riêng,không fakeAPIstate.
- ActualHTML/bootstrap/header/hero metadata và footer đã giao giữ nguyên.
- Chọn ảnh thật do GET trả về,mỗi trang một typedimageGET/haiitems.
- Chuyển preset9:16:ô tùy chỉnh xóa/khóa/khôngrequired;trở vềcustom:
  enabled/required;nhập1080×1920 và Tab tớiheight;không submit.
-30lightlabel/helptargets5.797099–12.351555:1,no unsupportedpaint;
  không overflow/errors/dialog/egress;không tạo PNG.
- Fresh3register/3login/12typedmetadata/noblobs;registerrowhash/exact3login
  audit/otherproductrows/schema/source/binding giữ;22ownedprocesses dọn về0.
-6firstviewport+6field-region screenshots;VI375lightfields vàEN1440dark
  firstviewport đã xem. Không claim toàn trang được xem bằng mắt.

## Phạm vi và giao hàng

Đối chiếu toàn nguồn:143protectedapplicationfiles exact;allapplication
Python/portal.js/integration/styles/motion/templates/auth/engine/Bot/tiền
giữ nguyên. CI chỉ thêm một lệnh Node. FullapplicationdiffreviewC0/I0/M0.
Snapshot lịch sử chỉ đảo hữu hạn33rows ở ranh giới đọc test;oldassertions/
hashes/keys/order/outside/rawstaleintegrationguards không bị nới.

Currentoperations/originalcomparison/Tester chuẩn bị trướcpush.
ExactHEADCI/merge/deploy/runtime/assets và receipt là bước tiếp theo;
ở mốc local này chưa nhận đã triển khai hoặc signedLIVE.

Sharedfield.source/common/resultsubtitle và ba chip kỹ thuật của trạng thái
còn trong scope tiếp theo;không nhận cả trang/wholelocale/AX/auth/device/
Safari/finalPNG/motion/toàngoal đã sạch từ33rows. MetadataCompressproposal
vẫn xếp sau nhóm ảnh. Motionlast;không áp dụng enginecandidate.
PROVIDER_CALLS=0;WALLET_MUTATIONS=0;PRODUCTION_DATA_MUTATIONS=0;ENV=UNCHANGED.
