# VO-VAULT-NOTICE-CLARITY — một thông báo chung, không lặp từng giọng

BASE_SHA=efbe362da9158762136820aa63112fa6882bd870
Repo standalone; branch webapp-r218-billing-ui-20261022; PR661; trackerIssue662.
Dependency VO-CANONICAL-FLAG-TRUTH đã ACCEPTED: CI39908802221 hai jobsSUCCESS,
receipt Issue662#issuecomment-6358673449. Không mở lại hoặc sửa các predicate đó.
COMPLEX/SINGLE vì cùng bundle dùng chung; chỉ một worker Flash3.8, tối đa2vòng.

## READ và nguyên nhân

Renderer thật + catalogue EN đã đo:0giọng→0thông báo,1→1,10→10. Paragraph
`library.manageGuarded` nằm trong profiles.map của renderVoiceVault; vì vậy cùng
một giới hạn của toàn trang bị lặp lại ở mỗi thẻ giọng. Đây là thừa thông tin UI,
không phải backend incident. Dữ liệu status/consent/preview/update vẫn hữu ích.

Impact: một renderer private trong portal.js, các callsites hiện hữu vẫn giữ
nguyên; không đổi signature/export/route. Giữ scope Voice inventory và các nơi
đang nhúng inventory đó. Baseline focused48/48; previous fullNode951/951.

UI review: truy vấn database UX không tìm được mục sát việc lặp hướng dẫn;
không dùng kết quả animation không liên quan. Dùng quick-reference về hierarchy,
read-only distinction, contrast và giảm clutter; design system/màu/font hiện tại
được giữ, không sinh theme mới hoặc motion.

## CONTRACT / allowlist

- `static/portal/portal.js`: chỉ đoạn tạo list trong renderVoiceVault. Di chuyển
  paragraph hiện tại, giữ nguyên class, safeText, key và fallback text, ra trước
  div.portal-voice-inventory-list trong nhánh profiles.length>0. Bỏ paragraph
  tương ứng trong mỗi details. Không thêm wrapper/card/attribute/helper/action.
- `tests/voice-inventory-presentation.test.mjs`: thêm test hành vi vào harness
  renderer/catalogue thật, không sửa/xóa các assertion cũ hoặc dựng renderergiả.
- Protected: strictboolean flags, thẻ/profile metadata/default/status/consent,
  escaping, slicing50/snapshot notice, links/field selection, other renderer,
  integration/i18n/CSS/auth/API/backend/Bot/engine/provider/wallet/data/ENV/motion.
- Không xóa ý nghĩa giới hạn, không thêm nút management/preview giả, không đổi chữ.
- Empty/loading/failed/guarded không được thêm thông báo quản lý không liên quan.

## Task và tiêu chí mở gate

1. TEST2–5min: trong mỗi localeVI/EN/ZH, render ready với0/1/2/50/51profiles;
   notice count là0khiempty,1khinonempty; card count=min(n,50); notice nằm trước
   firstdetails và không nằm trong card. Với loading/failed/guarded + stale data,
   count0notice/0card. Giữ tất cả test flag-truth và metadata hiện có.
2. BUILD2–5min: một phép di chuyển HTML paragraph như trên. Không refactor,
   rename hoặc thay dữ liệu. Đọc actual diff và kiểm7strictbooleanpredicates giữ.
3. Codex RED→GREEN: test-only phải fail đúng counts/order/inside-card, không
   syntax/missing helper. FocusedVoice/fullNode/PythonSource/syntax/diff trước nhận.
4. Browser18configs VI/EN/ZH ×light/dark ×390/768/1440, thêm375smallphone và
   landscape khi kiểm mới. Fixture10profiles:1notice chung,0notice trongcards,
   metadata/keyboard/flags/select unchanged. Đo contrast notice>=4.5:1 vàoverflow0;
   không CSS/palette thay đổi trong spec. Check screenshot, AX, noerrors/write/
   external; giữ fixture READbootstrap/profile đã khai báo từ flagtruth.
5. Operationaldocs/featurecomparison/Tester cases, provenance, push/readback/CI
   đúngHEAD và receiptIssue662. Không nhận là canonicalbackend/audio/LIVE.

### Acceptance

AC-01 notice0hoặc1 đúng readstate/cardinality, trước list và ngoài mỗi card.
AC-02 đủ metadata/copy/escaping/limit/flag/route/guard, noinputmutation/noaudio.
AC-03 browser matrix>=18configs,375+landscape,keyboard/contrast/overflow/AX đạt;
      noerror/external/UIwrite. Không claimprovider/Core/auth-link từ fixtures.
AC-04 diff đúngallowlist, sourcecontract/regression/provenance/CI có output.

Verify: `node --test tests/voice-inventory-presentation.test.mjs`;
`node --test tests/*.test.mjs`; Voice sourcePython2files; node--check/diff-check.
Worker stdout-only:VERIFY=NOT_RUN; Codex thực thi, không lấy self-report làmPASS.
Stop nếu cần thay file khác, CSS/màu/quyền/data, unknownworker hoặc BASElệch.
PROVIDER_CALLS_APP=0; WALLET_MUTATIONS=0; PRODUCTION_DATA_MUTATIONS=0;
DEPLOY=NO; LIVE_PASS=NOT_TESTED; GOAL=ACTIVE.
