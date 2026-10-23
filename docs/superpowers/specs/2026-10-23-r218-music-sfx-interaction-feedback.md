# MU-INTERACTION-FEEDBACK — Music/SFX locale và kết quả cũ

Ngày 23/10/2026. Product standalone WebApp; repo
`manhtoangreensky-wq/toan-aas-standalone`; worktree `_webapp-r218-voice`;
branch `webapp-r218-billing-ui-20261022`; PR661.
BASE_SHA=`2d6f61f3a700cea49a6c61ec1eb57a5740dae541`.
FSM=CONTRACT; risk COMPLEX/SINGLE vì hai renderer dùng chung bundle.
Tracker: https://github.com/manhtoangreensky-wq/toan-aas-standalone/issues/664.

### Checkpoint VERIFY

Hai vòngFlash trảtest/contextkhônghợplệ cùngAC01; khôngápworkerpatch, khôngR3.
Primarytakeover đúngallowlist. Harnesswindowexport đãsửa trướcREDsạch:
8pass/22assertionfail, sau sửaGREEN30/30; focused34/34, fullNode987/987,
Pythonnative/portal21/21 trước/sau. Ngoài4hàm/2row byte bằngBASE và9protected
files bằngBASE. Browser60/60actualsigned/noresponsefixtures đãkhép local:
300selections/180edits/120explicittextPOSTs,3items/compose, errors/external/
unapprovedwrites/HTTP/overflow0. RawfinalSHAf5e31eed7d462c838ef13652d06de965624c61acfad94703cb39052f0a026b14.
Delivery/CI/receipt cònchờ. FulltesterWindows32pass/1knownPOSIX0600fail,
script/testblobsequalBASE; portable32/32, LinuxCIchạylạinguyênytest.
Ngoàiscope: toastsuccessVI/technical trênEN/ZH đãghimP2
MU-NATIVE-SUBMIT-FEEDBACK-LOCALE; khôngclaimfullpagelocalepass.
Reviewđộclập chạy34/34, Critical0/Important0. Đơnvịeventlà1event/mỗilần
gọi markhelper, khôngphải1/cửchỉ: input+change cũcóthể cùngphát. Unitstub
receipt/SFXremember khôngthay runtimeDOM/tabmemory; giữbrowsergate riêng.
QA Python3.12bundled dùngreadonly dependency
`../_wa35-r74-qa-python-20261012/site-packages` qua processPYTHONPATH;
khôngcàigói,khôngsửavenv,cấu hình hayENVbềnvững.

## Dependency và phạm vi

Voice notice delivery đã khép: HEAD2d6f61f3, CI39921027250 hai job SUCCESS,
receipt Issue662#issuecomment-6361097358. Không sửa lại Voice đã khóa.
Spec này nằm trong P2 của master checklist R218, không thay master ledger.

Owner: “tiếp tục”; yêu cầu đứng: làm phần dở trước, theo checklist, giao Flash
3.8 chạy nền, không ô vô nghĩa/nội dung giả, motion làm cuối.

## READ evidence và nguyên nhân

Probe chạy 4 hàm production thật với catalogue thật VI/EN/ZH ngày23/10:
hai hàm synchronize ghi literal VI thay vì gọi helper/copy đã có; hai hàm
mark gọi synchronize trước rồi chỉ ghi stale ở lần đầu. Edit2 vì vậy hiện
thông báo selected dù receipt vẫn `data-stale=true`. Cả6 tổ hợp lane/locale
tái hiện; mỗi edit vẫn dispatch đúng một event.

Impact scan `git grep -n -E` cho4symbol: runtime chỉ trong portal.js,
định nghĩa38252/38274/38293/38315; nội bộ38276/38318;
event consumers41000/41003/41074/41077. Hai test Python đọc hàm:
test_music_directions_portal_contracts.py125/126,
test_sfx_cue_sheet_portal_contracts.py136/137/268.
Không đổi tên, chữ ký, kiểu trả về, event hay consumers.

## Allowlist và protected comparators

Production chỉ4hàm trên trong `static/portal/portal.js` và thêm đúng1row
`form.stale` ở mỗi MUSIC_DIRECTION_COPY_ROWS/SFX_CUE_SHEET_COPY_ROWS trong
`static/portal/portal-i18n.js`. Test mới
`tests/music-sfx-interaction-feedback.test.mjs` thực thi hàm thật/catalogue thật.
Tài liệu/spec/checklist/state/evidence do Codex giữ, worker không sửa.

Protected: toàn bộ code ngoài4hàm/2row phải bằng BASE sau normalize CRLF;
integration.js, CSS/palette, backend/API/auth/schema/ENV/provider/ví/PayOS,
Voice, Bot, route-engine và motion không thay đổi. Không thêm DOM, nút,
request, storage hoặc audio/output/giá/tải xuống giả.

## AC và task nhỏ có thể nghiệm thu

1. AC01 (2–5phút): dùng `form.selected`/`form.unselected` sẵn có và
   localized preset label cho cả5preset/lane ởVI/EN/ZH. Unknown/unselected
   vẫn disabled; strict enabled flag không đổi. Real-function Node test.
2. AC02 (2–5phút): có kết quả thì mọi lần edit1/2/3 đều giữ cảnh báo kết quả
   thuộc nội dung trước; chỉ `data-stale=true`, không sửa nội dung kết quả
   hoặc input. Không có kết quả thì chỉ selected/unselected. Mỗi edit phát
   đúng1event cũ; SFX vẫn giữ tab-memory draft; sai action/null không tác động.
3. AC03 (2–5phút): actual signed localhost app,2route × VI/EN/ZH × light/dark
   ×375/390/768/1440 và landscape844×390. Chọn bằng bàn phím/chuột, nhập brief,
   submit thật vào endpoint deterministic text-only, xác minh3hướng/3cue,
   edit1/2/3 giữ kết quả và cảnh báo; submit mới bỏ stale. Edit không gửi POST.
   Không framework overlay/page/console error/overflow/external/unapproved write.
4. AC04: focused+fullNode và Python native/portal contracts; clean protected
   comparator; docs hiện tại/comparison/Tester/prepush trước push.

Chuỗi mới `form.stale`:

| Lane | VI | EN | ZH |
|---|---|---|---|
| Music | Nội dung đã thay đổi. Các hướng bên dưới thuộc nội dung trước; lập lại hướng âm nhạc để cập nhật. | The brief has changed. The directions below use the previous brief; create music directions again to update them. | 摘要已更改。下方方向仍基于先前内容，请重新创建音乐方向以更新。 |
| SFX | Nội dung đã thay đổi. Bảng hiệu ứng bên dưới thuộc nội dung trước; lập lại bảng để cập nhật. | The brief has changed. The cue sheet below uses the previous brief; create the cue sheet again to update it. | 摘要已更改。下方音效提示表仍基于先前内容，请重新创建提示表以更新。 |

## RED → GREEN và delivery

`node --test tests/music-sfx-interaction-feedback.test.mjs` phải RED đúng
locale/stale rồi GREEN. Focused: cả hai locale-presentation test và interaction.
`node --test --test-concurrency=2 tests/*.test.mjs` phải0fail.
Python: test_copyfast_music_directions.py, test_copyfast_sfx_cue_sheet.py,
test_music_directions_portal_contracts.py, test_sfx_cue_sheet_portal_contracts.py.
Syntax2JS và git diff --check0. Browser bằng Playwright headless do Browser
plugin/skill không có; dữ liệu/DB/assets tạm, không production.

Một Flash3.8worker, R1/R2 tối đa; Codex áp test trước rồi chạy RED, sau mới
áp production. Lệch cùngAC sau2round mới takeover; không vòng3.
Evidence/spec cần đủ mới mở bước kế; không dùng worker self-report làmPASS.
Commit/push vào PR661 sau prepush gate, không receipt-only CI loop.
Không kết luận mọi Music/SFX generation/player/reuse hay canonical parity đã xong.
`PROVIDER_CALLS_APP=0; WALLET_MUTATIONS=0; PRODUCTION_DATA_MUTATIONS=0`.
`DEPLOY=NO; LIVE_PASS=NOT_TESTED; GOAL=ACTIVE; M0=LAST`.
