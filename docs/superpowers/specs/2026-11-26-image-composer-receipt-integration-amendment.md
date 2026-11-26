# COMP-RECEIPT — bổ sung điểm nhận dữ liệu trước bootstrap

BASE `6ec003dbf8f80739f5fb93ff7bd1d7cc703c6792`, nhánh
`codex/image-composer-locale-20261126`, Issue689/contract7170035286.
Phụ lục này không thay39record đã áp dụng hoặc nhận toàn Composer đạt.

## Nguyên nhân và chứng cứ

`static/portal/integration.js:imagePromptComposerMemorySaveReceipt` kiểm
đủ execution/true-facts/17false-flags, nhưng chỉ trả note/destination/index.
Khi merge vào state, `portal.js:normalizeBootstrap` gọi normalizer vốn
đòi toàn bộ các facts; biên nhận bị loại trước khi renderer nhận được.
Sửa return-shape ở portal đã qua150case nhưng không sửa được điểm rơi
trước đó. Đây là phần thiếu trong spec của điều phối, không lỗi worker.

Helper QA đầu thiếu `validProjectId`; đã sửa riêng, không tính worker fail.
RED đúng sau sửa QA:13case,12fail ở note mất qua acceptor→bootstrap→render,
1pass chứa85invalid-boundary observations. Bằng chứng
`image-composer-receipt-pipeline-red-r2-nov26.xml`; không gọi API/provider.

## Allowlist bổ sung và thay đổi duy nhất

Thêm `static/portal/integration.js` vào phạm vi ứng dụng, nhưng chỉ một
record return-object trong `imagePromptComposerMemorySaveReceipt`.
Giữ nguyên toàn bộ predicate, UUID/revision/index/note whitelist và23key
nhận. Return giữ lại chính các facts vừa được xác minh:

```javascript
return {
  note: { id: String(note.id), revision, state: "active", category: "Image Prompt Composer", priority: "normal" },
  destination: "memory_note",
  selected_variant_index: selectedVariantIndex,
  execution: "web_native_memory_note_server_recomputed",
  draft_recomputed_on_server: true,
  web_note_persisted: true,
  ...Object.fromEntries(IMAGE_PROMPT_COMPOSER_MEMORY_SAVE_FALSE_BOUNDARY_FIELDS.map((field) => [field, false]))
};
```

Không spread raw data hoặc thêm nội dung. Không đổi request/action/
endpoint/auth/ownership/persistence/idempotency/provider/wallet/PayOS/
ENV/data/motion.39record gốc bất biến; lưu record mới thành amendment
riêng trong fixture, thêm pin before/after cho integration.js và đảo
amendment trước39record khi so nguồn lịch sử.

## Trình tự

- [x] Source/luồng thật và RED12fail+1pass đúng nguyên nhân.
- [x] Antigravity4ExtraHigh R1 trả đúng một record, không ghi source.
- [x] Kiểm exact record/predicate; áp đúng record đã nhận.
- [x] Pipeline13case +raw-source8+inverse8 →29pass0fail0skip;
  `image-composer-receipt-amendment-green-nov26.xml`.
- [x] Bộ138receipt checks cũ, realmodel26cases và UIresult258cases giữ;
  không cộng lượt kiểm lại vào số ca duy nhất.
- [ ] Review/hồi quy/các cổng phát hành cùng batch Composer, không PR rời.

Lượt HTTP cục bộ đã chạm300giây ở testcase đầu,0case hoàn tất, SIGTERM
và không còn hai tiến trình QA do lượt đó tạo. Không nhận PASS hoặc baseline-equivalent.
Không chạy lại cùng lượt để làm xanh.20API/static cases phải đạt trên
Ubuntu CI trước merge; unit realbuilder26và receipt150 báo riêng,
không dùng thay bằng chứng HTTP.

Các câu phản hồi hành động và heading/thân ghi chú được mở và xử lý
bằng phụ lục `2026-11-26-image-composer-feedback-note-amendment.md`,
không thuộc quyền một-record của phụ lục receipt này.
