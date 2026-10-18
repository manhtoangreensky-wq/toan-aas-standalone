# Pre-push report — WEBAPP-BOT-PARITY-R218 / PR #654

Đang đọc và áp dụng skill owner-governed-codex cho task này.

## Identity

```text
REPOSITORY=manhtoangreensky-wq/toan-aas-standalone
BRANCH=webapp-r217-subdub-ui-r218
SOURCE_HEAD_SHA=06380789abcc11d118286de3903c5bbab44e4176
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
LOCAL_REGRESSION=530 passed, 0 failed on candidate 814b70c
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
PUSH_GATE=READY_FOR_DOCUMENTATION_UPDATE
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
# Incremental Voice control evidence — candidate `814b70cee2b6f4d2d1d2db23c903bfc0ca3d50bd`

- Phạm vi: `static/portal/portal.js`, `static/portal/portal.css`, `tests/voice-controls-contract.test.mjs`.
- VO-04/VO-05: speed số `0,1–2,0` + mặc định `1,0` + 3 preset; volume slider `0–200` đồng bộ với một field số; label/help/preset đi qua catalogue locale.
- Verify: targeted `3/3`, Voice regression `97/97`, full Node `530/530`, `node --check static/portal/portal.js`, `git diff --check`.
- Không gọi provider, không sửa wallet/dữ liệu production, không merge/deploy/live. CI/browser cần chạy lại trên candidate này.
