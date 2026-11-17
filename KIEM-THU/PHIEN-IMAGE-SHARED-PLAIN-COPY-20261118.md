# Phiên kiểm tra — nhãn dùng chung công cụ ảnh

TESTER_PROJECT_ID=IMAGE-SHARED-PLAIN-COPY-20261118.
TESTER_PROJECT_STATUS=READY.
BASE_SHA=ce40bf4089701d0ba47f46845e7061cb92d5bba1.
HEAD_SHA=Chốt tại source commit và receipt CI trước phát hành.
TRACKER=Issue689.

Nguồn case duy nhất: DANH-SACH-CASE.md, tám hàng ISPC.
Ứng dụng: đúng 21 hàng i18n và hai div ba nhãn trong renderImageResize.
Không thay khóa, quyền, route, validation, controls, dữ liệu khách hoặc engine.
Không gọi provider/ví/production. Motion vẫn cuối.

Bằng chứng đã có:

- BASE thật: 85 ca,7 đạt/78 nội dung RED,7484.2387ms.
- Candidate một lượt85ca:76đạt/chín lỗi phép đo,11152.9626ms.
  Phép đo đã đếm hero-actions rỗng có sẵn; không phải lỗi worker.
- Chỉ chín ca sau sửa phép đo:9đạt/0lỗi,2838.9496ms.
- Hai comparator nguồn đầu lỗi sắp neo theo toàn tệp thay vì đúng mảng;
  chỉ hai ca sau sửa bộ đo đạt,3051.7252ms.
- 304ca liên quan trong14tệp:304đạt/0lỗi,25845.6079ms.
- Chữ/tên tệp khách được escape, key/order/freeze/outside giữ.
- 149tệp ứng dụng bảo vệ/allPython giữ, app chỉ hai tệp.

Không ghi thành một lượt391ca cùng xanh. Không chạy lại nhóm đã đạt.
Ba ca consumercompleted bổ sung đạt riêng2446.4402ms.
NativeR2sáu ca đạt24copy/18visibletext/30control/typedGET1items2/
select1080×1920Tab,nosubmit/errors/overflow/egress. Fresh3register/
3login/12metadata/noblobs/exactoldregister+3loginaudit/schema/otherdata/
source151/binding,22ownedstopped0active. R1zeroaccepted do readerlabel
đọcrequired/sr-only;chỉ sửaQA,13ownedstopped0active,khôngapp/timeoutchange.
Bốnrawscreensđãxem,croplimitsghi rõ;khôngnhậntoànpage/device.
Ô presetdesktop131.828125px làbacklogbố cụctiếp theo,mobile44px.
CI và phát hành còn phải có kết
quả độc lập trước khi khóa phần việc. READY là phiên kiểm tra sẵn sàng,
không phải toàn bộ goal hoặc sản phẩm LIVE đã đạt.
