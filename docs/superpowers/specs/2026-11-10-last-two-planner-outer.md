# Hai biểu mẫu lập kế hoạch còn lại — đợt riêng sau PR711

BASE_SHA=7f8753d5c35c6827a76fe9579041b1fe3812ba39.
Branch codex/last-two-planner-ui-20261110; Issue #689.
Hai hàm renderImageMotionPlanner/renderReferenceFormatPlanner không đổi so
với nguồn công khai e63f073f dùng trong phiếu. PR711 đã phát hành riêng.

| Spec | Kết quả chính | Phạm vi |
|---|---|---|
|LAST-TWO-OUTER-IMAGE|Bỏ khối giới thiệu/số đếm/aside/header kỹ thuật; dịch form|1hàm+lastTwoPlannerUi.image,giữ5trường|
|LAST-TWO-OUTER-REFERENCE|Tương tự,không có cột rỗng|1hàm+lastTwoPlannerUi.reference,giữ9trường|
|LAST-TWO-READABILITY|Mobile16px,nhãn/help sáng>=4,5:1|3ruleCSS đúng2form|

Ba phiếu độc lập trả output-only, không ghi cùng tệp. Điều phối chỉ áp dụng
tuần tự sau kiểm tra. Không thay metadata/customer names,normalizer,guards,
canCompose/canSave,quyền,action/route/inputscalar/default/constraint/result/savecall.
Không backend/auth/engine/provider/ví/ENV/schema/data/motion/deployworkflow.

- [x] Baseline24renderer:24controlpass,24localeRED và24clutterRED.
- [x] Một lượt gộp hai R1:referenceEN/ZH8stateđạt;VI4statecòn1từ;
  imageOLD0anchor vàNEWthiếudấukếtchuỗi,khôngápdụngsai vàoapp.
- [x] R2imagechỉbùdấukếtchuỗiOLD/NEW;R2referencechỉsửa1VIvalue/bỏ36keythừa.
- [x] Rerun16stateảnhhưởng,giữ8stateđãđạt;ngoài2hàm giữbyte,10349mục cũ giữ.
- [x] Nativebaseline4view:14controlmobile15px,20mẫusángfail,min1,2653:1;
 20mẫutốipass,min5,5225:1;khôngtrànngang.
- [x] Đúng3rule:mobile16px<=620 cho2form;lightlabelspanink;small/note muted.
- [x] Nativefinal12view (2route×VI/EN/ZH×320tối/1440sáng),actualempty/guard,
 labels/focus/type/contrast/overflow/console. Không giả dữ liệu tham chiếu từAPI.
- [ ] Docs/tester/provenance/CI/exactHEADmerge/exactSHAdeploy/runtime/assets.

Kết quả/saving/output-templatecủa2trangchưatrongđợtouternày,vẫngiữmởđểlàm
tiếp;khôngtuyênbốtoàntranghayengineđãhoạtđộngchỉvìformđượcđọcsạch.
PROVIDER_CALLS=0;WALLET_MUTATIONS=0;PRODUCTION_DATA_MUTATIONS=0.
