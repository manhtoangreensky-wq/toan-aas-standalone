# Phiên Tester — phản hồi đọc tệp âm thanh

ID=MEDIA-AUDIO-READ-FEEDBACK-20261121.
BASE=c8b14ade33ed62f2fefb34fe0d14aca198e03a8e.
BRANCH=codex/media-audio-read-feedback-20261121.
TRACKER=Issue689/comment7049170333.
STATUS=LOCAL_ACCEPTED_RELEASE_PENDING.

Nguồn case: bảy caseMARF ở DANH-SACH-CASE.md; sửa tại nguồn trước.
Spec:docs/superpowers/specs/2026-11-21-media-audio-read-feedback.md.
Fixture:tests/fixtures/media-audio-read-feedback-reviewed.json,
RAWsha8d54a2e60594277fd952e7323f5518bed6eb2dfc2e2e42faa81100fadb515cd8.

- [x] BASE147ca:7PASS140assertionRED, không setupfault.
- [x] Ba proposalCLI thật, bốn record/hai appfile, Rootserialreplay;
  R1A chỉ phục hồi finalLFBASE ở hai trường của readerrecord.
- [x] Physical147PASS0FAIL0skip; currentfailed cảnh báo, empty thành
  công, stale im lặng, giữ strictcapabilities và frozenDTO/query.
- [x] Forwardcurrent151LFpins/149protected, không inverse acceptance.
- [x] Historical106uniquePASS, chỉ bảy tên cũ từng lỗi được chạy lại;
  oldguards/fixture/golden/erroridentity giữ.
- [x] Python15PASS3exactBASEFAIL; review độc lập0blocker.
- [x] Hồi quy145CIlocaleNodefile được đối chiếu theo từng phần,
  giữ kết quả đã đạt, không chạy lại147/106.
  Nhóm136file4172PASS + ba remaining-slice34/15/62PASS =4283PASS0FAIL0skip.
- [x] NativeR2/lượt03:6view×2roots/48PNG mới,72feedback/48abort12heldGET,
  source/core/schema/auth/egress/owned0 vàfullPNGdecode.
- [ ] Tester metadata/prepush/audit/manifest/secret đạt.
- [ ] MộtPR/exactCI/artifacts/merge/deploy/VPS/assets/receipt.

Dùng form lọc tệp âm thanh trên chi tiết bộ sưu tập và AudioHub.
Tải lỗi không được báo thành công; validempty vẫn đúng. Kiểm xóa lọc,
trang50 và quay0 bằng control thật; tên/UUID của chủ tài khoản giữ.
VI/EN/ZH kiểm riêng, cảnh báo dùngalert và thành công dùngstatus.

QA dùng SQLite/metadata/tài khoản giả cô lập và secret giả child-only.
Không productPOST/download/preview/blob/player/provider/ví hoặc dữ
liệu thật. Native không chứng minh file tồn tại/phát âm thanh/output.
Full-documentstale không thay proofsame-document từ147physical.
GenericBODYfocus ghi nguyên trạng rồi dùngTab thật; không nhận đã
sửa focus hoặc toàn bộ accessibility/motion.

Native01 startupfalse/0case/0PNG do quyềnlocalhost; owned0 và binding
giữ. Native02 failngưỡngQA4500ms sau6feedback/4PNG/0acceptedview/owned0.
R2 chỉ đồng nhất với actionbound10000ms và ghi sốđo;native03 đã đạt
finalreceipt+48PNGgate;source/core/schema/auth/egress giữ,owned0.
Hồi quyR1 timeoutQA300s/khôngcompletereceipt được giữ, R2bound900s.
Không tính lỗi QA/quyền/transport là genuinecodefailure của worker.
WholegoalACTIVE, motioncuối; không suy signedproductionUI đã đạt.
