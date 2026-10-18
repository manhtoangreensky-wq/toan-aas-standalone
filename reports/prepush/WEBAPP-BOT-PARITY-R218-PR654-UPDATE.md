# Pre-push report — WEBAPP-BOT-PARITY-R218 / PR #654

Đang đọc và áp dụng skill owner-governed-codex cho task này.

## Identity

```text
REPOSITORY=manhtoangreensky-wq/toan-aas-standalone
BRANCH=webapp-r217-subdub-ui-r218
SOURCE_HEAD_SHA=db8faa41fd059467d8f084a7661a01e53f4a5e85
CURRENT_CANDIDATE_HEAD_SHA=3ecbdc8e6c7447570360aca6792d78f1d3cd995b
DOCS_ONLY_UPDATE=false
PR=https://github.com/manhtoangreensky-wq/toan-aas-standalone/pull/654
PROVIDER_CALLS=0
WALLET_MUTATIONS=0
PRODUCTION_DATA_MUTATIONS=0
DEPLOY=NO
LIVE_PASS=NOT_TESTED
```

## 1. Review code và tài liệu vận hành

- Runtime Voice control presentation đã cập nhật ở `static/portal/portal.js` và
  `static/portal/portal.css`; SubDub lane presentation vẫn là protected comparator.
- `TAI-LIEU/01-NGHIEP-VU-VAN-HANH.md` và `TAI-LIEU/02-CHUC-NANG-GOC-VA-HIEN-TAI.md`
  đã bổ sung disposition hiện tại: lane presentation đạt, capability/execution/delivery
  vẫn mở.
- Completion ledger duy nhất là
  `reports/audit/WEBAPP-BOT-PARITY-UIUX-MASTER-CHECKLIST-R218.md`; bảng B01–B34 trong
  `reports/audit/WEBAPP-BOT-PRODUCT-INVENTORY-R218.md` giữ toàn bộ phạm vi Voice, Music,
  SubDub, Image, Product Video/Video Editor, Utilities, AutoPost, Support, Account và Admin.

## 2. Evidence đã xác minh

```text
CI_RUN=39101124230 (prior SubDub comparator HEAD 148be4f)
VERIFY_WEB_APP=SUCCESS (prior comparator)
AUTHENTICATED_WEBAPP_QA=SUCCESS (prior comparator)
ROUTE_RENDER_MATRIX=456/456 (prior comparator)
LOCAL_TARGETED=3 voice control + 97 Voice regression passed; node --check static/portal/portal.js; git diff --check
LOCAL_REGRESSION=538 passed, 0 failed on source candidate db8faa4
JSON_EVIDENCE=preflight.json + web_inventory.json parse successfully
MIGRATION_SOURCE_FILES=recorded in reports/migration/web_inventory.json
MIGRATION_SOURCE_FINGERPRINT=recorded in reports/migration/preflight.json and web_inventory.json
GIT_DIFF_CHECK=PASS
```

Route/render matrix chỉ chứng minh shell, locale, theme, viewport và browser QA isolated;
không chứng minh provider call, server capability, upload, quote, job, artifact output,
delivery hoặc LIVE production.

## 3. Tester workspace

- Nguồn case: `KIEM-THU/DANH-SACH-CASE.md`.
- Hướng dẫn: `KIEM-THU/HUONG-DAN-TESTER.md`.
- Issue templates: `.github/ISSUE_TEMPLATE/01-case-test.yml` và `02-bao-loi.yml`.
- Tracker/Project đã nghiệm thu trước đó: issue `#412`, project `TOAN AAS Web App · Tester P0`;
  không tạo issue/project cạnh tranh trong incremental Voice update.
- Tester phải đối chiếu đúng `SOURCE_HEAD_SHA`; route matrix `456/456` và SubDub `13/13`
  là protected comparator từ HEAD trước, còn candidate mới cần chạy lại Voice control
  interaction/browser evidence. Giữ các comparator Auth/Admin/Landing, locale VI/EN/ZH,
  theme, phone/tablet/desktop.

```text
TESTER_WORKSPACE=REUSE_EXISTING_ACCEPTED_WORKSPACE
EXTERNAL_MUTATION_IN_THIS_UPDATE=0
PUSH_GATE=REMOTE_MATCHED; PR_OPEN_CONFLICTING; CI_UNKNOWN
```

## Current Image candidate identity — pushed head `3ecbdc8e6c7447570360aca6792d78f1d3cd995b`

Wave Image đã được commit/push sau khi kiểm tra đúng 8 tệp trong phạm vi. Local và GitHub
đang trùng SHA; PR #654 vẫn OPEN, `statusCheckRollup=[]` và `mergeable=CONFLICTING`. Bản ghi
này tách rõ candidate mới khỏi comparator cũ ở trên; CI, browser evidence và LIVE trên
candidate mới chưa được suy diễn từ run trước.

```text
IMAGE_TARGETED=48/48
LOCAL_FULL=541/541 tests/*.test.mjs
NODE_CHECK=PASS (static/portal/portal.js, static/portal/portal-i18n.js)
GIT_DIFF_CHECK=PASS
CI_ON_CURRENT_HEAD=UNKNOWN (PR statusCheckRollup rỗng)
PROVIDER_CALLS=0
WALLET_MUTATIONS=0
PRODUCTION_DATA_MUTATIONS=0
DEPLOY=NO
LIVE_PASS=NOT_TESTED
REMOTE_HEAD=3ecbdc8e6c7447570360aca6792d78f1d3cd995b (0/0 local-vs-GitHub)
PR_STATE=OPEN
PR_MERGEABLE=CONFLICTING
```

## 4. Disposition trước khi mở wave tiếp

- Đã khóa: SubDub lane selector, link Voice, ba callback riêng Auto 2/Multi 3–8/Smart Multi,
  dub volume static 0–200, locale copy và route/render CI evidence.
- Chưa khóa: Voice Vault mapping, Music editor/two-track delivery, SubDub server capability
  và execution, Image/Utilities/AutoPost/Admin control-level evidence, Product Video/Video
  Editor execution và toàn bộ motion cuối.
- Không merge, deploy, live hoặc gọi provider trong batch này.

## Incremental Music control evidence — candidate sau batch local 18/10/2026

- Phạm vi: `static/portal/portal.js`, `static/portal/portal-i18n.js`,
  `static/portal/portal-theme.css`, `tests/music-product-controls.test.mjs`.
- MU-01..MU-07 control-level: `/music/create` và `/music/song` có workspace dọc 4 bước,
  3 tier, 3 ô phương án guarded; bài hát giữ lyrics/vocal/song length/duration; nhạc nền không
  lộ field song-only; không còn badge provider, giá hard-code, player, MP3 hoặc download giả.
- Locale: catalogue `musicProduct.*` cân bằng `vi/en/zh`; placeholder phương án dùng đúng
  tham số locale; theme light/dark giữ token xanh/ngọc, card dọc và breakpoint 640/980px.
- Guard: thêm `data-music-product-enabled`; synchronizer không thể mở field khi thiếu
  capability hoặc bản nháp hợp lệ.

```text
MUSIC_TARGETED=7/7
MUSIC_VOICE_FOCUSED=19/19
MUSIC_EXISTING_FOCUSED=25/25
FULL_NODE=537/537
NODE_CHECK=PASS
GIT_DIFF_CHECK=PASS
PYTEST=BLOCKED (workspace không có lệnh python/py)
PROVIDER_CALLS=0
WALLET_MUTATIONS=0
PRODUCTION_DATA_MUTATIONS=0
DEPLOY=NO
LIVE_PASS=NOT_TESTED
```

Music generation, quote/confirm, editor, player/download/save/reuse, two-track delivery,
authenticated browser evidence và CI trên HEAD mới vẫn là `[~]/[ ]`; không được suy diễn
thành parity runtime hoặc LIVE.

## Incremental SubDub control evidence — source candidate 18/10/2026

- Phạm vi: `static/portal/portal.js`, `static/portal/portal.css`,
  `tests/subdub-hub-presentation.test.mjs` và các tài liệu R218 liên quan.
- SD-02/03/04/05/07/11/12/13/17 control-level: source nêu rõ đã có/chưa có
  phụ đề; source language mặc định tự nhận diện; target catalog đầy đủ, Việt đứng
  trước rồi Anh/Trung; 7 vị trí phụ đề; ba lane canonical `auto_two`,
  `auto_multi_3_8`, `smart_multi` map đúng ba callback Bot. Không tạo upload,
  speaker detection, quote, job, output hoặc delivery giả.
- Locale: nhãn catalog được chiếu riêng cho VI/EN/ZH; không dùng label English lẫn
  trong bản Việt hoặc fallback tiếng Việt ở bản EN/ZH.

```text
SUBDUB_TARGETED=14/14
FULL_NODE=538/538
NODE_CHECK=PASS
GIT_DIFF_CHECK=PASS
PYTEST=BLOCKED (workspace không có lệnh python/py)
PROVIDER_CALLS=0
WALLET_MUTATIONS=0
PRODUCTION_DATA_MUTATIONS=0
DEPLOY=NO
LIVE_PASS=NOT_TESTED
```

SubDub upload/preview/metadata, Voice Vault projection, speaker mapping thật,
quote/confirm/progress/report, artifact/delivery và browser/live evidence vẫn mở;
đợt này chỉ khóa presentation và local interaction.

## Incremental Image control evidence — local candidate 18/10/2026

- Phạm vi: `static/portal/portal.js`, `static/portal/portal-i18n.js`,
  `static/portal/portal.css` và `tests/image-create-locale-presentation.test.mjs`.
- IM-01 control-level: `/image/create` có đúng bốn mode dọc, không trùng lặp: tạo ảnh,
  ảnh tham chiếu/soạn câu lệnh (`/image-studio`), chỉnh sửa AI có bảo vệ
  (`/image/transform`) và chỉnh sửa thủ công (`/image/edit`). VI/EN/ZH có catalogue riêng;
  ba mode ngoài tạo ảnh gắn `guarded` và không tự mở runtime.
- Protected contracts giữ nguyên: form `prompt/tier/format`, action/estimate/confirm,
  report, quote redaction, tracking identity và fail-closed output. Không thêm upload,
  preview, ảnh giả, provider, job, wallet hoặc payment.

```text
IMAGE_TARGETED=48/48 (Image create/workbench/hub/operation/studio)
NODE_CHECK=PASS (portal.js, portal-i18n.js)
GIT_DIFF_CHECK=PASS
PYTEST=BLOCKED (workspace không có lệnh python/py)
PROVIDER_CALLS=0
WALLET_MUTATIONS=0
PRODUCTION_DATA_MUTATIONS=0
DEPLOY=NO
LIVE_PASS=NOT_TESTED
```

Image source/reference upload, AI edit runtime, before/after, quote/result/delivery,
authenticated browser evidence và CI trên HEAD mới vẫn mở; không gọi đây là Image parity
runtime hoặc LIVE.
# Incremental Voice control evidence — candidate `814b70cee2b6f4d2d1d2db23c903bfc0ca3d50bd`

- Phạm vi: `static/portal/portal.js`, `static/portal/portal.css`, `tests/voice-controls-contract.test.mjs`.
- VO-04/VO-05: speed số `0,1–2,0` + mặc định `1,0` + 3 preset; volume slider `0–200` đồng bộ với một field số; label/help/preset đi qua catalogue locale.
- Verify: targeted `3/3`, Voice regression `97/97`, full Node `530/530`, `node --check static/portal/portal.js`, `git diff --check`.
- Không gọi provider, không sửa wallet/dữ liệu production, không merge/deploy/live. CI/browser cần chạy lại trên candidate này.

## Incremental Utilities/Content/Projects locale evidence — committed candidate after pushed Image head

- Phạm vi code: `static/portal/portal.js`, `static/portal/portal-i18n.js` và test mới
  `tests/content-prompt-pack-locale-presentation.test.mjs`; tài liệu checklist/spec/vận hành
  được cập nhật cùng checkpoint này.
- Candidate commit `69ef97ffdf7f0c86aa950439dd8c83d64989f53e` khóa wave này trước push. UT-02/03/05/08 control-level: Content Studio/detail, Content Prompt Pack, Free Prompt Gallery,
  Free Tools, Memory Center/Reminder, Project Center và Workboard giữ route/action contracts;
  Content Prompt Pack dùng fixed chrome riêng cho VI/EN/ZH và bản VI không còn các chuỗi
  giao diện tiếng Anh generic.

```text
UTILITY_TARGETED=25/25
FULL_NODE=544/544
NODE_CHECK=PASS (portal.js, portal-i18n.js)
GIT_DIFF_CHECK=PASS
PYTEST=BLOCKED (workspace không có lệnh python/py)
PROVIDER_CALLS=0
WALLET_MUTATIONS=0
PRODUCTION_DATA_MUTATIONS=0
DEPLOY=NO
LIVE_PASS=NOT_TESTED
```

Working tree sạch sau commit; runtime dữ liệu thật, upload/download, provider, publish, wallet,
browser/AX và live vẫn mở; không suy diễn UI control-level thành parity runtime.
