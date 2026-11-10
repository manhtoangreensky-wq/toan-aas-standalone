# Phiên kiểm thử — chữ hệ thống trong kế hoạch đã lưu

SESSION_ID=SAVED-PLAN-SYSTEM-COPY-20261111; Issue #689.
BASE_SHA=7ef871e396a3f3c9d006b24397044ed68870c8cf.
HEAD_SHA=commit chứa phiên này; receipt ghi exact tested HEAD sau CI.
TESTER_PROJECT_STATUS=READY; LOCAL_ACCEPTANCE=PASS; PUSH_GATE=AWAITING_PROVENANCE.

Nguồn case: [DANH-SACH-CASE.md](DANH-SACH-CASE.md), nhóm SPC dưới đây.
Không tạo tracker, dự án, nhãn hoặc thẻ trùng; dùng Issue689 và bộ hiện có.

| Ca | Acceptance / bằng chứng bắt buộc | Trạng thái |
|---|---|---|
| SPC-LANGUAGE |192 Image/1200 Reference choices, fixed saved prose theo content language | GREEN matrix sau R2 |
| SPC-CUSTOMER |Tên/chủ đề/audience và literal braces không mất; IDs/timing/tags/role/limits giữ |15retained+3affectedpass;222native reopenedfieldmatches |
| SPC-USEFUL |Image audience không bịa; brief3dòng; scene notes4dòng, còn giá trị thật | Pure và6actualreadbacks đạt |
| SPC-BOUNDARY |40 BASE/candidate samples,0newrejections, full customer text |0newrejections/2BASE-equivalentrejections |
| SPC-NATIVE |6actual compose-confirm-save-GET-reopen,6plan18scene, temporary DB |12views/36screens,quickcheckok,48Jobprocesses->0 |
| SPC-DARK |6read-only views của kế hoạch đã lưu, actualthemeflag và palette |6/6GET/reopened,282contrast min5.522477721172796:1,0compose/save,22Jobprocesses->0 |
| SPC-SOURCE |2function spans +17data leaves only,134existing leaves/16protected paths giữ | Final R2 comparator đạt |
| SPC-DELIVERY |ExactHEADCI/merge/exactSHAdeploy/runtime/hashes/assets riêng | NOT_RUN |

R1 independent18-testgroup:15passed/3failed. R2 chỉ sửa một nhãn EN do
coordinator đưa sai; không sửa guard hoặc dữ liệu khách và không tính lỗi thợ.
Sau R2 chỉ chạy3failedtests + affectedboundary/sourcegate;15passkhôngđổi giữ.
Native chỉ chạy sau patch readiness; không mở production browser hoặc gọi provider.
Local PASS không thay signed production/device proof. Phần detail labels/tags,
old-record presentation,11BASE-equivalent title cases, stale/retry/auth/AX/motion
vẫn ở checklist tổng, không đóng bằng phiên này.

Final local gate:3failedtests corrected+15unchangedpasses retained=18accepted.
Native12views/6realflows,222reopenedfieldvalues,6plan18scene/36screens,48Job->0.
Dark supplement6views/6screens on DBcopy: original artifacts and plan data hash
unchanged,quick_checkok. No source/appdata changes during either group. Delivery
status is final exactHEAD/merge/deploy/runtime/asset receipt on Issue689, not this
pre-push snapshot. Whole-detail labels/tags and device proofs remain separate.
