# Đọc chữ từ ảnh, PDF và PDF quét sang Word

## Chốt phát hành PR777 — thay các dòng chờ lịch sử phía dưới

PR777 đã gộp và triển khai. CI44531826202 đúng HEAD21176b3634bbf5abb541c108204f6961b5f84e51,
hai job thành công897s/318s. Artefact14533963958 đủ18trang/18hash;
artefact14534714930 đủ456bản ghi/456hash,0lỗi/provider/ví/dữ liệu production.
Merge/runtime5b11e63f178b4ff81c4546462a8cb3ddcdc99fb5, fulltree
45373d6382b3f4471753a10f88112056c707fb9a khớp bản đã kiểm.
Deploy44536393560 thành công72s; VPS trackedclean, Web/Bot/nginx active-running,
health và5public+5normallyversionedassets byteexact; buildlocal-392adcd5d51e1f37f743.
Receipt Issue689/comment7008143289 và PR/comment7010982669 đã đọc lại đúng.
Không còn PR mở của đơn vị này. SignedproductionUI/Tesseract/languagepacks/
TXT/DOCX cuối vẫn NOT_TESTED/NOT_PROVEN; toàn goal ACTIVE/incomplete, motion cuối.

TASK=DOCUMENT-OCR-CUSTOMER-COPY-20261119; FSM=REPORT_LOCAL_READY.
BASE_SHA=8ba0d0452f86dcc3d72e5087351134902eb4e659.
TRACKER=Issue689/comment7008143289.
PR=NOT_CREATED; DEPLOY=NOT_STARTED_FOR_OCR.

## Giao diện và giới hạn giữ nguyên

Ba trang dùng đúng VI/EN/ZH ở tên, mô tả, trường nguồn, ngôn ngữ,
xác nhận, hướng dẫn và lịch sử. Bỏ intro/aside/notice/notes/state-meta,
không khung trống; bỏ mô tả lặp đầu form. Giữ hai trường thật, liên kết
kho tệp trong chân form, quyền, mã lựa chọn, lịch sử/làm mới/phân trang
và tải kết quả. Tên khách không dịch và vẫn thoát ký tự an toàn.

`auto/vi/en` và mặc định `auto` không đổi. Đọc chữ không dịch nội dung.
PDF tối đa 20 MB/5 trang; Word chỉ tái tạo chữ, không giữ hình/bảng/
phông/bố cục. Không đổi API, auth, engine, schema, Bot, provider, ví,
PayOS, ENV, dữ liệu khách hay motion.

## Nguồn sửa

Bốn CLI worker `gemini-3.8-flash-high` dùng đăng nhập có sẵn, chỉ trả JSON,
không ghi shared application. Nguồn/MAP được đối chiếu GitHub công khai
HTTP200 trước gửi; không test/fixture/API/login response/secret/Bot source/
dữ liệu khách hoặc tài chính trong payload.

| R1 | Conversation đã kiểm |
|---|---|
| Trường chung/14 khóa |e848b31b-be36-4038-8801-e3bd569b6b29|
| Đọc chữ từ ảnh/7 khóa |3b569dc8-863e-47ca-a578-c0665a76b3c9|
| Đọc chữ từ PDF/7 khóa |569bac41-0255-4a3a-af0f-a46b54d013ae|
| PDF quét sang Word/8 khóa |c37404c0-ba40-47b9-8a8e-acede81796f5|

Đúng schema và từng giá trị ngay R1; 0 lỗi worker/0 Root application takeover.
Root áp dụng tuần tự đúng 19 phép thay/3 tệp ứng dụng, 36 khóa mới,
148/151 tệp nguồn bảo vệ. Fixture RAW SHA256:
`2784e5ec2bf31f4921f4d39fd495175dbb9871f860947d1c9b363218a453839f`.

## Bằng chứng đã có

Whole physical BASE: 10 đạt/18 RED trong 14202.5964 ms; candidate
28 đạt/0 lỗi trong 17278.0197 ms. HTMLResponse đầu BASE 1 đạt/9 RED
5.44s → 10 đạt/0 lỗi 2.76s. Hai bundle JS syntax/diff check đạt.
Chín trang trước giữ nguyên HTML/title/context ở ba locale.

Native BASE và GREEN: ba nhóm/phase, mỗi nhóm 24 cấu hình. Sáu nhóm
đều exit0/observationAccepted/owned-active0. Root xem VI320 tối Image
và EN768 ngang sáng Word trước/sau; không chạy OCR hoặc gửi form.
Tổng hợp PNG/hash/CRC đã xác nhận bằng chứng lưu như số đo phía dưới;
không suy từ quan sát form thành engine sẵn sàng.

Bộ portable/source đã đạt50/50 trong18023.7063ms;81tệp affected một lượt
1866/1866 đạt trong336348.5643ms,0fail/cancelled/skipped,không rerun.
Outputdiagnostic cóclippingđượcghirõ,khôngẩnexit/count. Pythonportable+
related71/71đạt22.39s;Tester2đạt31bỏchọn4.85s. SáuOCRcase/1781dòng/
184934byteLF/SHA5cb377539f2abddb0f23942386a2781bc38870d1dd986d9e6b4de3215f9a85ed.

StoredvalidatorRootđọcđủ/chạy1lần:6groups/144views/288PNGstructureCRC/
size/hashkhớp. Mỗinhóm42owned→0;BASEimage78.138s/pdf77.847s/word78.573s,
GREENimage78.095s/pdf77.458s/word78.375s. Source151/code/binding/core/
schema/authaudit/egressheld;nomedia/productwrite. GREEN0panelthừa,
1vaultfocusable,2field/source+languagecodesauto/vi/enđúng.
540BASE/540GREENpaintUNKNOWNgiữ,tấtcảwitnesskhôngbỏ;khôngWCAG/AA/
globalcontrast. Rootxemảnhtrước/saukhôngđồngnghĩaengine/output.
ValidatorSHA3052b498ba785cb126fcd358a43c444240b9d6c5e97a7a0ac204f118637e9ea7.
PublicauditSHAfa1bf830b2d4ee53bb31330b8b6d3890b284a16e629219802aa1ebd90bbddc18.

## Sửa đặc tả trước kiểm tra, không sửa quyền ứng dụng

Root ban đầu chỉ định một cờ QA cho PDF quét sang Word. Đọc
`copyfast_api.py:794–798` và handler gốc cho thấy cần đồng thời
OCR-to-Word, PDF-OCR và PDF-to-Word. Đã sửa matrix child trước chạy:
hai trang còn lại chỉ bật cờ riêng, Word bật đúng ba phụ thuộc; không
ghi ENV máy/VPS, không nới guard hoặc giả phản hồi.
Đây là thiếu đặc tả của Root, không tính lỗi Antigravity/ứng dụng.

Lazy `_image_ocr_runtime` chỉ kiểm Tesseract và gói ngôn ngữ khi đường xử
lý thật chạy. Cờ/form/startup không chứng minh engine hoặc kết quả.
ENGINE_RUNTIME_LANGUAGE_READINESS=NOT_PROVEN; FINAL_OCR_OUTPUT=NOT_TESTED.

## Review và cổng phát hành

Independent review C0/I0/M0; Root đã đọc đủ 317 dòng, SHA256
`ae157bbb086079095ce273abf9570f7cc90622f1117576bd999ef516f138d2e8`.
Tài liệu hiện tại/chức năng gốc/Tester và canonical checklist đã cập nhật.
Snapshot manifest 27 giữ nguyên; final manifest 28 thêm checklist tổng,
ghim từng tệp trước commit. Không đổi app/QA hoặc chạy lại nhóm đã đạt.

Một PR/exact HEAD CI/merge/deploy/
VPS/assets/receipt chốt theo thứ tự. Không tạo PR lưu việc chưa xong.
Signed production, thiết bị thật/Safari, toàn bộ contrast/recovery/auth
và kết quả TXT/DOCX cuối giữ mở nếu thiếu bằng chứng trực tiếp.
Goal ACTIVE/incomplete; motion M-FINAL-01..06 cuối.

Ba lỗi export/handoff Python ngoài phạm vi đã đo ởPR776không nằm trong
71cađợtnày,khôngnhậnđãsửa. Không nhận toàn repository xanh.
