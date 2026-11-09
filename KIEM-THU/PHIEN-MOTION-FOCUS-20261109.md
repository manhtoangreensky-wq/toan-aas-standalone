# Phiên Tester Focus — 09/11/2026

SESSION_ID=MOTION-NOV09-FOCUS-CONTINUATION
BASE_SHA=a3ebcadfed27d5038a78d5afc757b4bf339ba113
STATUS=LOCAL_VERIFIED_PENDING_CI_DEPLOY
TRACKING=https://github.com/manhtoangreensky-wq/toan-aas-standalone/issues/689

Receipt: [focus](../docs/reports/motion-focus-20261109.md).
Evidence: [native](../reports/ui-qa/motion-focus-20261109/native-focus.json).
Nguồn ca: [DANH-SACH-CASE.md](DANH-SACH-CASE.md).

- [x] RED 3 pass/5 fail → GREEN 8/8 từ state/prefix/tail/helpers thật.
- [x] Current/error/sync và stale pending/sync/null snapshot, preventScroll/selection.
- [x] Review 0C/0I; Node 24/24, full Node 1915, Python motion 18.
- [x] Native 20/20, 390/1440 thường/giảm; focus/draft/selection/scroll/Tab giữ.
- [x] Hai helper focus byte-identical; PR700 motion/CSS/backend/auth/provider/ví giữ.
- [x] Navigation control 4 ca: PR700 và candidate cùng lỗi thường, giảm 0;
  giữ lỗi và giới hạn, không nhận navigation PASS hoặc relocation tăng tốc.
- [ ] Exact-commit CI, merge/deploy/runtime/assets.
- [ ] Native navigation root cause/startup, signed production và toàn bộ R218.

Lệnh:
```powershell
node --test tests/motion-focus-continuation.test.mjs tests/customer-header-hydration.test.mjs tests/customer-entry-lifecycle.test.mjs
python -m pytest -q tests/test_portal_motion_foundation_contracts.py
```

Flow native: form /video-studio/new → title → delay completion cũ qua adapter →
brief → hydration thật → resolve/reject cũ; brief vẫn focus. Current/fallback
giữ title; Tab tới format, ShiftTab về title. Không submit, tạo job, upload,
payment/provider/OAuth hoặc dùng dữ liệu production.
