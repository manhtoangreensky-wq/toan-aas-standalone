# P0 WebApp SubDub Canonical Product Authority Reconciliation (R1/C2)

- **Task**: `P0.WEBAPP.V3.SUBDUB.C2.INDEPENDENT.AUTHORITY.EVIDENCE.COMPLETION`
- **Parent Task**: `P0.WEBAPP.V3.SUBDUB.CANONICAL.PRODUCT.AUTHORITY.RECONCILIATION.R1`
- **Program**: `P0.WEBAPP.FULL.PRODUCT.TRUTH.REMEDIATION.V1`
- **Web Repository**: `manhtoangreensky-wq/toan-aas-standalone` (`WEB_BASE_SHA=db21c395eda8a2a23bbfac1ac9258f2c1840dce2`)
- **Bot Authority Repository**: `manhtoangreensky-wq/bot` (`BOT_AUTHORITY_SHA=661c0de773a68177f5c258843485a0177eb6b6e2`)
- **Mode**: `CORRECTION_ONLY`, `SAME_PR`, `EVIDENCE_COMPLETION`, `NO_PRODUCT_UI_CHANGE`, `NO_RUNTIME_EXECUTION`, `MINIMAL_CODE_FOOTPRINT`
- **Invariants**: `PROVIDER_CALLS=0`, `WALLET_MUTATIONS=0`, `MERGE=NO`, `DEPLOY=NO`, `RESTART=NO`

---

## 1. Preserved Verified Invariants & C2 Resolutions

| Invariant / Finding Flag | Value | Canonical Source & Empirical Verification |
|---|---|---|
| `FIRST_RED_BOT_SOURCE_ASSERTION_OPTIONAL` | **PROVEN** | C1 `test_b` looped over candidates and passed silently if missing; now strictly required. |
| `FIRST_RED_SELF_REFERENTIAL_BOT_EVIDENCE` | **PROVEN** | C1 `test_m`, `test_n`, `test_p` asserted against the audit JSON; now asserted directly against Bot git commit. |
| `BOT_AUTHORITY_COMMIT_REQUIRED` | **YES** | Mandatory git object inspection at `661c0de773a68177f5c258843485a0177eb6b6e2^{commit}`. |
| `BOT_SOURCE_MISSING_FAILS_FOCUSED_SUITE` | **YES** | Test suite raises `pytest.fail` if Bot pinned commit is missing. |
| `FIRST_RED_SUBDUB_HUB_IS_UTILITY_FIRST` | **PROVEN** | `copyfast_pages.py:191`, `static/portal/portal.js:1935-1941, 24878-24921` (`layout: "subdub-operations-hub"`, `fields: []`, `action: "none"`). |
| `SUBDUB_CANONICAL_LANES` | **4** | `bot.py:233106-233120`, `services/subdub_blackboxes/base.py` (`subtitle_create`, `subtitle_translate`, `dub`, `subtitle_plus_dub`). |
| `STATUS_ONLY_SUCCESS_AUTHORITY` | **NO** | `services/subtitle_dub_product_pipeline.py:546-557` (fails closed if `not (srt_bytes or audio_bytes or video_output)`). |
| `REAL_ARTIFACT_REQUIRED_FOR_COMPLETION` | **YES** | `services/subtitle_dub_product_pipeline.py:560-648` (verifies physical bytes before completion). |
| `SUBDUB_INPUT_CONTRACT_RESOLVED` | **YES** | Exact Web fields mapped to Bot runtime parameters across all 4 lanes. |
| `SUBDUB_WEB_UPLOAD_AUTHORITY_RESOLVED` | **YES** | Web uploads go to owner-scoped Asset Vault (`asset_id`), NEVER raw client paths or untrusted URLs. |
| `ASR_RUNTIME_AUTHORITY_RESOLVED` | **YES** | Backed by Key4U/ShopAIKey Whisper in `services/subdub_blackboxes`. |
| `TRANSLATION_RUNTIME_AUTHORITY_RESOLVED` | **YES** | Backed by Key4U/DeepL/OpenAI in `services/subdub_blackboxes`. |
| `TTS_RUNTIME_AUTHORITY_RESOLVED` | **YES** | Backed by MiniMax / ShopAIKey in `services/subdub_blackboxes` & `subdub_tts_language_routing`. |
| `MUX_RENDER_RUNTIME_AUTHORITY_RESOLVED` | **YES** | Backed by local FFmpeg render & ducking in `services/subtitle_dub_product_pipeline.py`. |
| `ADMIN_SUBDUB_JOB_TRACE_RESOLVED` | **NO** | Generic jobs table lacks lane differentiation and multi-stage pipeline breakdown. |
| `ADMIN_SUBDUB_FAILURE_TRACE_RESOLVED` | **NO** | Incident view lacks stage-level failure attribution and specific subdub error codes. |
| `ADMIN_SUBDUB_PROVIDER_READINESS_RESOLVED` | **NO** | Provider view is global; not linked to subdub lane routing or stage-level fallback. |
| `ADMIN_SUBDUB_ARTIFACT_TRACE_RESOLVED` | **NO** | Delivery center only tracks generic output presence, not individual stage artifacts. |
| `FICTIONAL_SUBTITLE_STUDIO_WORKBENCH_PRESENT` | **YES** | `static/portal/portal.js:20022-20120` (`portal-interactive-subdub-workbench`). |
| `UNSOURCED_99_5_ASR_BADGE_PRESENT` | **YES** | `static/portal/portal.js:24887-24888` (`qualityBadge: "99.5%"`). |
| `UNSOURCED_TIMELINE_MATCH_BADGE_PRESENT` | **YES** | `static/portal/portal.js:24889-24890` (`safetyBadge: "Timeline Match"`). |
| `SUBDUB_VI_LOCALE_PURITY` | **FAIL** | Mixed English labels in Vietnamese view (`portal.js:20021` "Transcript projects"). |

---

## 2. Direct Bot Git Source Authority (`661c0de773a68177f5c258843485a0177eb6b6e2`)

The test suite now directly accesses the Bot git object database via:
- Commit validation: `git -C <BOT_ROOT> cat-file -e "661c0de773a68177f5c258843485a0177eb6b6e2^{commit}"`
- File inspection: `git -C <BOT_ROOT> show 661c0de773a68177f5c258843485a0177eb6b6e2:<path>`

### A. 4 Canonical Lanes (`bot.py:233105-233120`)
- `VIDEO_SUBTITLE_MODE_CREATE = "subtitle_create"`
- `VIDEO_SUBTITLE_MODE_TRANSLATE = "subtitle_translate"`
- `VIDEO_SUBTITLE_MODE_DUB = "dub"`
- `VIDEO_SUBTITLE_MODE_SUBTITLE_PLUS_DUB = "subtitle_plus_dub"`
- `_COMBO_MODE = "subtitle_plus_dub"` in `services/subdub_blackboxes/base.py`

### B. Canonical Pricing Keys, Units, and Derived Formulas (`bot.py:6766-6925`)
| Canonical Key | Label | Unit | Default Rate | Derivation Formula |
|---|---|---|---|---|
| `subtitle_translate_video` | Dịch phụ đề video | **Xu/ký tự** | `0.1` | Base rate (`VIDEO_ONLY_SUBTITLE_TRANSLATE_RATE_XU`) |
| `auto_subtitle_video` | Tạo phụ đề tự động | **Xu** | `0` | Base rate (included / 0 Xu default) |
| `dub_video` | Lồng tiếng video | **Xu/ký tự** | `0.10` | Base rate (`VIDEO_ONLY_DUB_DEFAULT_RATE_XU`) |
| `subtitle_dub_video` | Phụ đề + lồng tiếng | **Xu/ký tự** | `0.20` | `subtitle_translate_video + dub_video` |
| `auto_subtitle_then_dub` | Tạo phụ đề rồi lồng tiếng | **Xu/ký tự** | `0.10` | `auto_subtitle_video + dub_video` |

### C. SubDub Auto Word Pricing Scope (`services/subdub_auto_word_pricing.py:1-58`)
- `AUTO_XU_PER_WORD = Decimal("0.5")` (0.5 Xu/word).
- Scope: Dedicated purely to Auto speaker diarization and casting (`subdub_auto_speaker`, `subdub_auto_settlement`). It is NOT generic dubbing pricing.

### D. Default Output Types & Fail-Closed Logic (`services/subtitle_dub_product_pipeline.py:81-93, 546-557`)
- `subtitle_create`: video -> `burn`, non-video -> `srt`
- `subtitle_translate`: video -> `burn`, non-video -> `srt`
- `dub`: video -> `video`, non-video -> `audio`
- `subtitle_plus_dub`: video -> `video_subtitle`, non-video -> `audio`
- Fail closed: `if not (srt_bytes or audio_bytes or video_output): return {"ok": False, "status": "NO_OUTPUT_BYTES", "error_code": "output_empty"}`

---

## 3. Web Customer Form Authority vs. Bot Canonical Runtime Authority

### TABLE A: Current Web Customer Form Specifications
- **Source**: `static/portal/portal.js:752-771` (`FIELD_SETS`)

| Form Name | Route(s) | Field Name | Control Type | Complete Specification | Semantic Note |
|---|---|---|---|---|---|
| `subtitleCreate` | `/subtitle`, `/subtitle/create`, `/asr` | `source` | `file` | `accept`: audio/video MIME types, `requiredUpload: true` | Required media file |
| | | `duration_seconds` | `number` | `min: 1`, `max: 14400`, `step: 1`, `required: true`, `inputMode: "numeric"` | Probed duration |
| | | `output_format` | `select` | `options: ["srt"]`, `required: false` | Restricts to SRT |
| `subtitleTranslate` | `/translate` | `source` | `file` | `accept`: `.srt,.vtt,.txt`, audio/video MIME types, `requiredUpload: true` | Required text or media |
| | | `target_language` | `select` | `options: LANGUAGE_OPTIONS`, `required: true` | Canonical language |
| | | `duration_seconds` | `number` | `min: 1`, `max: 14400`, `step: 1`, `required: true`, `inputMode: "numeric"` | Probed duration |
| | | `output_format` | `select` | `options: ["srt"]`, `required: false` | Restricts to SRT |
| `dubbing` | `/dubbing` | `source` | `file` | `accept`: audio/video MIME types, `requiredUpload: true` | Required media file |
| | | `mode` | `select` | `options: ["dubbing", "subtitle_plus_dubbing"]`, `required: false` | Combo option present! |
| | | `target_language` | `select` | `options: LANGUAGE_OPTIONS`, `required: true` | Canonical language |
| | | `voice_profile_id` | `select` | `optionsFrom: "voiceProfiles"` (Voice Vault), `required: false` | Owner-scoped profile |
| | | `speed` | `select` | `options`: `1.0` (Bình thường), `0.9` (Chậm), `1.5` (Nhanh), `required: false` | Fixed speed presets |
| | | `duration_seconds` | `number` | `min: 1`, `max: 14400`, `step: 1`, `required: true`, `inputMode: "numeric"` | Probed duration |
| | | `output_format` | `select` | `options: ["srt"]`, `required: false` | **Semantic GAP: srt for dubbing** |

### TABLE B: Bot Canonical Runtime Input Authority
- **Source**: `bot.py`, `services/subtitle_dub_product_pipeline.py:170-224`

| Bot Runtime Parameter | Type | Valid Values | Functional Purpose |
|---|---|---|---|
| `content_type` | `str` | `video/*`, `audio/*`, `text/plain` | Media discriminator |
| `source_bytes` | `bytes` | Raw binary bytes from verified storage | Pipeline media payload |
| `input_duration_seconds` | `float` | Probe duration | Timeline boundary & padding |
| `mode` | `str` | `subtitle_create`, `subtitle_translate`, `dub`, `subtitle_plus_dub` | 4-lane router |
| `target_language` | `str` | Canonical code (`vi`, `en`, `zh`, etc.) | Translation & TTS routing |
| `voice_selection_mode` | `str` | `manual`, `auto_speaker`, `auto_speaker_gender`, `multi` | Speaker casting strategy |
| `voice_style` | `str` | Provider voice ID / voice label | Speech timbre selection |
| `voice_speed` | `float` | `0.7` to `1.8` | Time-stretching parameter |
| `keep_original_audio` | `bool` | `True` (low volume) / `False` (muted) | Audio ducking policy |
| `dub_text_source` | `str` | `source` vs `translated` | TTS segment source |
| `output_type` | `str` | `burn`, `both`, `srt`, `vtt`, `txt`, `video`, `audio`, `video_subtitle` | Output artifact selector |

---

## 4. Web-to-Bot Parameter Mapping & Upload Authority

### A. Web-to-Bot Lane Mapping (`SUBDUB_INPUT_CONTRACT_RESOLVED = YES`)
1. **Lane 1: `subtitle_create`**
   - Web `source` -> server resolves `asset_id` -> `source_bytes`, `content_type`.
   - Web `duration_seconds` -> verified by server probe -> `input_duration_seconds`.
   - Web `output_format` -> mapped to `output_type` ("burn" for video, "srt" for non-video).
   - Invariants: `mode="subtitle_create"`, `needs_subtitle=True`, `needs_dub=False`.

2. **Lane 2: `subtitle_translate`**
   - Web `source` -> server resolves `asset_id` (.srt/.vtt/.txt or media) -> `source_bytes`, `content_type`.
   - Web `target_language` -> canonical code -> `target_language`.
   - Web `duration_seconds` -> verified by server probe -> `input_duration_seconds`.
   - Web `output_format` -> mapped to `output_type` ("burn" for video, "srt" for non-video).
   - Invariants: `mode="subtitle_translate"`, `needs_subtitle=True`, `needs_dub=False`.

3. **Lane 3: `dub`**
   - Web `source` -> server resolves `asset_id` -> `source_bytes`, `content_type`.
   - Web `mode="dubbing"` -> maps to `mode="dub"`.
   - Web `target_language` -> canonical code -> `target_language`.
   - Web `voice_profile_id` -> server resolves provider voice from Voice Vault -> `voice_style`, `voice_selection_mode="manual"`.
   - Web `speed` -> float multiplier (1.0, 0.9, 1.5) -> `voice_speed`.
   - Web `output_format` -> overridden by canonical media output ("video" for video, "audio" for non-video).
   - Invariants: `mode="dub"`, `needs_subtitle=False`, `needs_dub=True`.

4. **Lane 4: `subtitle_plus_dub`**
   - Web `source` -> server resolves `asset_id` -> `source_bytes`, `content_type`.
   - Web `mode="subtitle_plus_dubbing"` -> maps to `mode="subtitle_plus_dub"`.
   - Web `target_language` -> canonical code -> `target_language`.
   - Web `voice_profile_id` -> server resolves provider voice -> `voice_style`.
   - Web `speed` -> float multiplier -> `voice_speed`.
   - Web `output_format` -> mapped to combo output ("video_subtitle" for video, "audio" for non-video).
   - Invariants: `mode="subtitle_plus_dub"`, `needs_subtitle=True`, `needs_dub=True`.

### B. Web Upload Authority (`SUBDUB_WEB_UPLOAD_AUTHORITY_RESOLVED = YES`)
- Uploads MUST go through owner-scoped Asset Vault (`asset_id`), NEVER raw client paths or untrusted URLs.
- Server validates signed session, account ownership, MIME whitelist, and file size before bridge ingestion.

---

## 5. Stage Runtime Authorities & Admin Gaps

### A. Stage Runtime Authorities
- **ASR**: Backed by Key4U / ShopAIKey Whisper (`ASR_RUNTIME_AUTHORITY_RESOLVED = YES`).
- **Translation**: Backed by Key4U / DeepL / OpenAI (`TRANSLATION_RUNTIME_AUTHORITY_RESOLVED = YES`).
- **TTS**: Backed by MiniMax / ShopAIKey in `subdub_blackboxes` & `subdub_tts_language_routing.py` (`TTS_RUNTIME_AUTHORITY_RESOLVED = YES`).
- **Mux/Render**: Backed by local FFmpeg subprocess rendering in `subtitle_dub_product_pipeline.py` (`MUX_RENDER_RUNTIME_AUTHORITY_RESOLVED = YES`).

### B. Admin Traceability Status (Fail-Closed NO)
- `ADMIN_SUBDUB_JOB_TRACE_RESOLVED = NO`: Generic jobs table lacks lane differentiation and multi-stage pipeline breakdown.
- `ADMIN_SUBDUB_FAILURE_TRACE_RESOLVED = NO`: Incident view lacks stage-level failure attribution and specific subdub error codes.
- `ADMIN_SUBDUB_PROVIDER_READINESS_RESOLVED = NO`: Provider view is global; not linked to subdub lane routing or stage-level fallback.
- `ADMIN_SUBDUB_ARTIFACT_TRACE_RESOLVED = NO`: Delivery center only tracks generic output presence, not individual stage artifacts.

---

## 6. Locale Purity & Key Counts

- **VI keys**: 79 SubDub keys in `static/portal/portal-i18n.js` (out of 345 total).
- **EN keys**: 79 SubDub keys in `static/portal/portal-i18n.js` (out of 333 total).
- **Key Parity**: 100% parity between VI and EN SubDub bundles.
- **Interpolation Leaks**: 0 raw placeholder leaks.
- **DOM Purity**: Mixed English text in Vietnamese DOM (e.g., `portal.js:20021` "Transcript projects" in Subtitle Studio metrics) is recorded and queued for remediation in milestone R4 (`P0.WEBAPP.V3.SUBDUB.CUSTOMER.LOCALE.IA.CLEANUP.R1`).

---

## 7. Ordered Remediation Queue

- **R2**: `P0.WEBAPP.V3.SUBDUB.CANONICAL.DURABLE.JOB_BRIDGE.R1`
- **R3**: `P0.WEBAPP.V3.SUBDUB.CUSTOMER.HUB.FOUR_LANE.PRODUCT.R1`
- **R4**: `P0.WEBAPP.V3.SUBDUB.CUSTOMER.LOCALE.IA.CLEANUP.R1`
- **R5**: `P0.WEBAPP.V3.SUBDUB.ADMIN.RUNTIME.TRACE.R1`
- **R6**: `P0.WEBAPP.V3.SUBDUB.RUNTIME.ADAPTER.ACTIVATION.R1` (`OWNER_GATE_REQUIRED`)
- **R7**: `P0.WEBAPP.V3.SUBDUB.FOUR_LANE.E2E.PRODUCT.TRUTH.R1`
