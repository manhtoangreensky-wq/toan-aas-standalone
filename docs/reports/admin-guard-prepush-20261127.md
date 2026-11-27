# AGC — bàn giao trước push

Đang đọc và áp dụng skill owner-governed-codex cho task này.

Product=standalone WebApp;repo=manhtoangreensky-wq/toan-aas-standalone;
BASE=5f316f29c9b8657c4018f5174c4c4ce4f16c1e5f;
branch=codex/admin-guard-copy-20261127;Issue689;chưa sourcecommit.
Một batch,một PR sau local gates;không mở Issue/PR rỗng.

## Ba phần bàn giao

1. Current operations đã cập nhật trong
   `TAI-LIEU/01-NGHIEP-VU-VAN-HANH.md`:GSC đã giao PR819,AGC là
   ứng viên local. Không lấy câu chữ làm chứng cứ quyền hoặc kết quả engine.
2. Initial/current comparison trong
   `TAI-LIEU/02-CHUC-NANG-GOC-VA-HIEN-TAI.md`:nguồn masterR217/R218,
   actualhelpers/renderers/copyarrays tại BASE;không bịa danh sách chức năng.
   Allowance cũ Content Studio đã sửa theo chỉ thị Owner mới.
3. Phiên Tester `ADMIN-GUARD-CUSTOMER-COPY-20261127` cómanifest,
   támcase nguồn vàreport;dùngIssue689/nhãn/mẫu có sẵn,không tạo Project
   giả hoặc gọi quyền đăng nhập mới.

## Code và nghiệm thu

Hai appfiles khớp22worker proposals:
portal LF SHA c59c7676dcb1e7f30d404f6d66ac19ab4c8c8ff6d4aa1ff7ea7c7cb428abb591;
i18n LF SHA e00ccdd40c454eaea71eb361720f915a50444a9eba841f30ae9dd8f5b10f1c79.
31row/93value,giữ canAct/conditions/actions/handlers/backend.
Root semantic/proposal review một lượt;QA-only enclosing-owner gap đã
đóng bằng5RED→21targetedGREEN;0worker-code-failure/0root app rewrite.

Local ledger:129native,222consumer và130GalleryconsumerPASS;
Node source179/snapshot34 vàPython198pressurePASS;Python recovery2PASS.
Không cộng overlappinggroups hoặc re-run nhóm đã đạt. Browser108unique/
36guard/6ảnh,input16,target44,0error/overflow/egress,sourcehash held.
Giới hạncomponent/no fullmount/no contrastmatrix/no device/Safari/
no signed-production được giữ trongmanifestvàreport.

Protected domains:auth,canAct,bridge/realtime,backend,Bot/engine/provider/
wallet/PayOS,ENV/schema/proddata/motion/deploy workflow phải giữ so vớiBASE.
CI wiring chỉ append suiteAGC vào đúng hai runlines hiện có.
10oldstatefiles không đọc/chạm/stage;explicit file staging.

## Cổng vận chuyển

- [x] Ops/comparison/master/Tester/spec-plan phản ánh bằng chứnglocal.
- [ ] Final metadata LF hashes vàprotected/secret/manifest checks.
- [ ] Sourcecommit→Web-onlyprovenance refresh/verify.
- [ ] ExactHEAD CI haiSUCCESS→mộtPR→merge treeexact.
- [ ] ExclusiveWebdeploy→runtime/source/assets/cache→receiptreadback.
- [ ] Signedproduction riêng;không suy từpublicasset hoặcHTTP200.

PUSH_GATE=LOCKED_UNTIL_FINAL_METADATA_PROVENANCE_AND_PROTECTED_CHECKS.
COMMIT=NO;PUSH=NO;MERGE=NO;DEPLOY=NO;LIVE_PASS=NOT_TESTED.
PROVIDER_CALLS=0;WALLET_MUTATIONS=0;PRODUCTION_DATA_WRITES=0.
