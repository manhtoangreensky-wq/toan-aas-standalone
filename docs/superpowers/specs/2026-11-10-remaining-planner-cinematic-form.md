# Cinematic native form freshness prerequisite

BASE_SHA=e63f073f460e551438fbb8e3627ec232353f3efe; Issue #689, current UI batch.
Native signed compose rendered its real result but kept save disabled. The
form-only matcher sends string select values into a strict numeric normalizer.
Allow one fragment in portal.js:cinematicConceptFormMatchesSavedSource to
convert canonical decimal strings for idea_choice,motion_choice and
video_duration_variant in its local fields only, before strict normalization.

- [x] Valid unchanged native form remains current and can save with capability.
- [x] Changed/invalid/wrong-action values remain stale; transport stays strict.
- [x] Actual signed compose-confirm-save-readback, no duplicate save.

Antigravity R1, output-only, full public MAP. No shared helper, auth, transport,
API, ownership fence, normalizer, backend, engine, provider or payment changes.
Focused30-case RED/GREEN then affected native flow; reuse other accepted gates.
