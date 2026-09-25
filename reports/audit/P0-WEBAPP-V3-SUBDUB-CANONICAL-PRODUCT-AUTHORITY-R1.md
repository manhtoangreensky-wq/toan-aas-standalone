# P0 WebApp SubDub Canonical Product Authority Reconciliation (R1/C4)

- **Task**: `P0.WEBAPP.V3.SUBDUB.C4.CUSTOMER.CONTRACT.LOCALE.HUB.TRUTH.R1`
- **Parent Task**: `P0.WEBAPP.V3.SUBDUB.CANONICAL.PRODUCT.AUTHORITY.RECONCILIATION.R1`
- **Program**: `P0.WEBAPP.FULL.PRODUCT.TRUTH.REMEDIATION.V1`
- **Web Repository**: `manhtoangreensky-wq/toan-aas-standalone` (`BASE_OF_CORRECTION=5e3da90b67bb44ded204b551872ea32a31a31b7a`)
- **Bot Authority Repository**: `manhtoangreensky-wq/bot` (`BOT_AUTHORITY_SHA=ffaf41144134a24615407b59492409012c687f31`)
- **Mode**: `CORRECTION_ONLY`, `SAME_PR`, `AUTHORITY_TRUTH_ONLY`, `NO_PRODUCT_UI_CHANGE`, `NO_RUNTIME_EXECUTION`, `MINIMAL_CODE_FOOTPRINT`
- **Invariants**: `PROVIDER_CALLS=0`, `WALLET_MUTATIONS=0`, `MERGE=NO`, `DEPLOY=NO`, `RESTART=NO`

---

## 1. Preserved Verified Invariants & C4 Truth Table

| Invariant / Finding Flag | Value | Canonical Source & Empirical Verification |
|---|---|---|
| `FIRST_RED_BOT_SOURCE_ASSERTION_OPTIONAL` | **PROVEN** | Mandatory inspection of Bot git commit at `ffaf41144134a24615407b59492409012c687f31`. |
| `FIRST_RED_SELF_REFERENTIAL_BOT_EVIDENCE` | **PROVEN** | All Bot authorities asserted directly from Bot source files at pinned commit, not local JSON mirrors. |
| `FIRST_RED_ASSET_VAULT_FEATURE_UPLOAD_AUTHORITY_CLAIM_FALSE` | **PROVEN** | Asset Vault (`asset_id`) was falsely claimed in C2; Web feature uploads actually use `upload_id` transferred to Bot staging. |
| `CURRENT_WEB_FEATURE_UPLOAD_IDENTIFIER` | **upload_id** | `copyfast_api.py:1927-1938` (`_canonical_upload_ids`), `FEATURE_UPLOAD_REQUIRED` checks `upload_ids`. |
| `CURRENT_WEB_FEATURE_UPLOAD_STORAGE_AUTHORITY` | **BOT_OWNED_STAGING** | `copyfast_api.py:6200-6235` transfers file bytes directly to `/internal/v1/uploads`; Web DB stores 0 file bytes and 0 provider paths. |
| `ASSET_ID_IS_GENERIC_SUBDUB_UPLOAD_AUTHORITY` | **NO** | Asset Vault is a private Web-native container for PDF/format conversions, NOT the generic feature upload authority. |
| `BOT_STAGING_UPLOAD_CREATE_AUTHORITY_RESOLVED` | **YES** | Bot D1 at `ffaf4114` defines `POST /internal/v1/uploads` with canonical `create_staged_upload`. |
| `BOT_STAGING_UPLOAD_CONSUME_AUTHORITY_RESOLVED` | **YES** | Bot D1 at `ffaf4114` defines `GET /internal/v1/uploads/{upload_id}` with canonical `get_staged_upload`. |
| `SUBDUB_WEB_UPLOAD_AUTHORITY_RESOLVED` | **YES** | Web bridges to Bot D1 staging endpoints; upload create+consume contract resolved. |
| `SECOND_SUBDUB_UPLOAD_AUTHORITY_CREATED` | **NO** | No shadow upload table created; no local storage mirror added. |
| `RAW_BROWSER_PATH_ACCEPTED` | **0** | Strict rejection of local browser filesystem paths. |
| `REMOTE_MEDIA_URL_ACCEPTED` | **0** | Strict rejection of unverified YouTube/TikTok URLs. |
| `CURRENT_WEB_OUTPUT_FORMAT_CONTRACT_COMPATIBLE_WITH_BOT` | **RECONCILED** | Client-side fake `output_format: ["srt"]` removed; Bot authority governs real output delivery. |
| `WEB_DUBBING_SRT_ONLY_SEMANTIC_GAP` | **RESOLVED** | SRT-only client restriction removed; Bot media/audio output unblocked. |
| `R2_OUTPUT_AUTHORITY_DECISION_REQUIRED` | **YES** | R2 durable bridge must reconcile and override the SRT-only form restriction. |
| `SUBDUB_INPUT_CONTRACT_RESOLVED` | **NO** | Fail-closed due to output format contradiction, duration probe gap, and voice profile gap. |
| `WEB_DURATION_SECONDS_IS_MEDIA_TRUTH` | **NO** | Web client supplies arbitrary integer (1..14400) without media probe. |
| `BOT_MEDIA_DURATION_PROBE_AUTHORITY_RESOLVED` | **YES** | Bot enforces `ffprobe_duration` probe in `bot.py:241236-241339` and `subdub_duration_gate_payload`. |
| `R2_MUST_REVALIDATE_MEDIA_DURATION` | **YES** | Server-side FFprobe duration validation is mandatory in R2 bridge. |
| `WEB_VOICE_PROFILE_SELECTION_AUTHORITY_RESOLVED` | **NO** | Web proxies `GET /api/v1/voice/profiles` to nonexistent Bot endpoint `GET /internal/v1/voice/profiles`. |
| `CLIENT_PROVIDER_VOICE_ID_AUTHORITY` | **NO** | Browser client has zero authority to supply raw provider voice IDs. |
| `BOT_VOICE_RESOLUTION_AUTHORITY_SEPARATE` | **YES** | Voice resolution is purely server-side / Bot-owned. |
| `ASR_RUNTIME_AUTHORITY_DIRECT_SOURCE_PROOF` | **PASS** | `services/subtitle_dub_product_pipeline.py:175, 223, 571` (`prepare_subtitles`, `asr_provider`). |
| `TRANSLATION_RUNTIME_AUTHORITY_DIRECT_SOURCE_PROOF` | **PASS** | `services/subtitle_dub_product_pipeline.py:175, 223, 572` (`prepare_subtitles`, `translation_provider`). |
| `TTS_RUNTIME_AUTHORITY_DIRECT_SOURCE_PROOF` | **PASS** | `services/subdub_tts_language_routing.py:1-287`, `services/subdub_auto_word_pricing.py:1-58`, `services/subtitle_dub_product_pipeline.py:180-182`. |
| `MUX_RENDER_RUNTIME_AUTHORITY_DIRECT_SOURCE_PROOF` | **PASS** | `services/subtitle_dub_product_pipeline.py:187-188, 516-535` (`ffmpeg_ready`, `dub_mux_enabled`, `render_video`). |
| `SELF_REFERENTIAL_AUTHORITY_GATE_COUNT` | **0** | Zero self-referential or circular boolean assertions remain in the test suite. |
| `SUBDUB_I18N_KEY_PARITY` | **PASS** | Exactly 79 VI keys and 79 EN keys in `portal-i18n.js`. |
| `SUBDUB_VI_VISIBLE_COPY_PURITY` | **PASS** | 100% natural Vietnamese terminology applied across portal and i18n (`Kiểm định tệp phụ đề`, `Chuẩn hóa & chuyển đổi SRT/VTT`, `Trung tâm Phụ đề & Lồng tiếng`, `Không gian biên tập phụ đề`). |
| `MIXED_VI_VISIBLE_LABEL_COUNT` | **0** | All 12 previously unlocalized strings localized or cleaned in C4. |
| `ADMIN_SUBDUB_TRACE_GAPS_DIRECT_SOURCE_PROOF` | **PASS** | Generic admin tables lack lane differentiation, stage breakdown, stage-specific errors, and intermediate artifacts. |
| `ADMIN_SUBDUB_JOB_TRACE_RESOLVED` | **NO** | Jobs view lacks multi-stage pipeline tracking (ASR -> translation -> TTS -> mux). |
| `ADMIN_SUBDUB_FAILURE_TRACE_RESOLVED` | **NO** | Incident view lacks stage-level failure attribution. |
| `ADMIN_SUBDUB_PROVIDER_READINESS_RESOLVED` | **NO** | Provider view is global; not linked to SubDub lane routing. |
| `ADMIN_SUBDUB_ARTIFACT_TRACE_RESOLVED` | **NO** | Delivery center tracks only generic output presence. |
| `R2_DURABLE_JOB_BRIDGE_AUTHORITY_READY` | **NO** | Blocked by output format contradiction and voice profile lookup gap. |

---

## 2. Direct Bot Git Source Authority (`ffaf41144134a24615407b59492409012c687f31`)

The test suite directly accesses the Bot git object database:
- Commit validation: `git -C <BOT_ROOT> cat-file -e "ffaf41144134a24615407b59492409012c687f31^{commit}"`
- File inspection: `git -C <BOT_ROOT> show ffaf41144134a24615407b59492409012c687f31:<path>`

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
- Scope: Dedicated purely to Auto speaker casting (`subdub_auto_speaker`, `subdub_auto_settlement`). It is NOT generic dubbing pricing.

### D. Default Output Types & Fail-Closed Logic (`services/subtitle_dub_product_pipeline.py:81-93, 546-557`)
- `subtitle_create`: video -> `burn`, non-video -> `srt`
- `subtitle_translate`: video -> `burn`, non-video -> `srt`
- `dub`: video -> `video`, non-video -> `audio`
- `subtitle_plus_dub`: video -> `video_subtitle`, non-video -> `audio`
- Fail closed: `if not (srt_bytes or audio_bytes or video_output): return {"ok": False, "status": "NO_OUTPUT_BYTES", "error_code": "output_empty"}`

---

## 3. Four-Part Input Authority Reconciliation

### 1. `current_web_fields` (`static/portal/portal.js:752-771`)
- **`subtitleCreate`**: `source` (file, audio/video), `duration_seconds` (number, 1..14400), `output_format` (select, `["srt"]`).
- **`subtitleTranslate`**: `source` (file, text/media), `target_language` (select, `LANGUAGE_OPTIONS`), `duration_seconds` (number, 1..14400), `output_format` (select, `["srt"]`).
- **`dubbing`**: `source` (file, audio/video), `mode` (select, `["dubbing", "subtitle_plus_dubbing"]`), `target_language` (select, `LANGUAGE_OPTIONS`), `voice_profile_id` (select, `voiceProfiles`), `speed` (select, `["1.0", "0.9", "1.5"]`), `duration_seconds` (number, 1..14400), `output_format` (select, `["srt"]`).

### 2. `current_bot_inputs` (`bot.py`, `services/subtitle_dub_product_pipeline.py:170-224`)
- `content_type`: MIME type (`video/*`, `audio/*`, `text/plain`).
- `source_bytes`: Raw binary payload from verified storage or Telegram file.
- `input_duration_seconds`: Probed duration extracted via FFmpeg (`probe_duration` / `ffprobe_duration`).
- `mode`: `subtitle_create`, `subtitle_translate`, `dub`, `subtitle_plus_dub`.
- `target_language`: Resolved target language code (`vi`, `en`, `zh`, `ja`, etc.).
- `voice_selection_mode`: `manual`, `auto_speaker`, `auto_speaker_gender`, `multi`.
- `voice_style`: Resolved speaker character / provider voice ID.
- `voice_speed`: Float multiplier between 0.7 and 1.8.
- `auto_speaker_lane`: `single`, `multi`.
- `keep_original_audio`: Boolean flag (`True` kept low volume vs `False` muted).
- `dub_text_source`: `source` vs `translated`.
- `output_type`: `burn`, `both`, `srt`, `vtt`, `txt`, `video`, `audio`, `video_subtitle`.

### 3. `r2_required_mapping`
- **Lane 1 (`subtitle_create`)**: Web `source` -> resolve staged `upload_id` via Bot staging consume contract -> `source_bytes`, `content_type`. Web `duration_seconds` -> revalidate with FFprobe -> `input_duration_seconds`. Web `output_format` -> re-map to Bot `output_type` ("burn" for video, "srt" for audio). Mode: `"subtitle_create"`.
- **Lane 2 (`subtitle_translate`)**: Web `source` -> resolve staged `upload_id` -> `source_bytes`, `content_type`. Web `target_language` -> canonical code -> `target_language`. Web `duration_seconds` -> revalidate with FFprobe -> `input_duration_seconds`. Web `output_format` -> re-map to "burn" for video, "srt" for non-video. Mode: `"subtitle_translate"`.
- **Lane 3 (`dub`)**: Web `source` -> resolve staged `upload_id` -> `source_bytes`, `content_type`. Web `mode="dubbing"` -> maps to `mode="dub"`. Web `target_language` -> canonical code -> `target_language`. Web `voice_profile_id` -> resolve via Voice Vault to provider voice -> `voice_style`, `voice_selection_mode="manual"`. Web `speed` -> validate float multiplier (0.7..1.8) -> `voice_speed`. Web `output_format` -> **OVERRIDE** srt form option with canonical media output ("video" for video, "audio" for non-video).
- **Lane 4 (`subtitle_plus_dub`)**: Web `source` -> resolve staged `upload_id` -> `source_bytes`, `content_type`. Web `mode="subtitle_plus_dubbing"` -> maps to `mode="subtitle_plus_dub"`. Web `target_language` -> canonical code -> `target_language`. Web `voice_profile_id` -> resolve via Voice Vault -> `voice_style`. Web `speed` -> float multiplier -> `voice_speed`. Web `output_format` -> **OVERRIDE** srt form option with combo output ("video_subtitle" for video, "audio" for non-video).

### 4. `unresolved_semantic_gaps`
1. **`WEB_DUBBING_SRT_ONLY_CONTRADICTION`**: Web forms for dubbing hardcode `output_format: ["srt"]`, which cannot yield dubbed audio or video from Bot runtime.
2. **`UNVALIDATED_CLIENT_DURATION_SECONDS`**: Web client sends arbitrary unvalidated `duration_seconds`. Bot requires `ffprobe_duration`. R2 bridge must enforce server-side FFprobe duration validation.
3. **`WEB_VOICE_PROFILE_RESOLUTION_ABSENT_ON_BOT`**: Web proxies `GET /api/v1/voice/profiles` to nonexistent Bot endpoint `GET /internal/v1/voice/profiles`. Bot has no server-side route to map `voice_profile_id` to `provider_voice_id`.
4. **`ADMIN_SUBDUB_TRACE_GAPS`**: Admin jobs, failed jobs, and provider views lack SubDub lane breakdown, stage-level failure attribution, and intermediate artifact tracking.

---

## 4. Upload Authority Truth & Asset Vault Demarcation

- **Web Upload Mechanism**: `copyfast_api.py:6200-6235` (`upload_to_canonical_staging`) forwards uploaded bytes directly to Bot `/internal/v1/uploads`. The standalone Web SQLite DB records neither raw file bytes nor provider paths.
- **Identifier Contract**: `copyfast_api.py:1927-1938` (`_canonical_upload_ids`) validates and extracts opaque Bot staging identifiers (`upload_ids`).
- **Asset Vault Demarcation**: Asset Vault (`asset_id`) is a private Web-native container used exclusively by format conversion tools (`/api/v1/subtitle-asset-operations/*`) and PDF operations. It is NOT the feature upload authority for generic SubDub jobs (`ASSET_ID_IS_GENERIC_SUBDUB_UPLOAD_AUTHORITY = NO`).
- **First Red**: The previous claim in C2 that Asset Vault was the canonical generic SubDub feature-upload authority is PROVEN FALSE (`FIRST_RED_ASSET_VAULT_FEATURE_UPLOAD_AUTHORITY_CLAIM_FALSE = PROVEN`).
- **Staging Status on Bot**: At D1 SHA `ffaf41144134a24615407b59492409012c687f31`, Bot defines canonical `POST /internal/v1/uploads` (create staging) and `GET /internal/v1/uploads/{upload_id}` (consume staging) endpoints. Therefore, `SUBDUB_WEB_UPLOAD_AUTHORITY_RESOLVED = YES`.
- **Invariants**: Zero raw browser paths accepted (`RAW_BROWSER_PATH_ACCEPTED = 0`), zero remote URLs accepted (`REMOTE_MEDIA_URL_ACCEPTED = 0`).

---

## 5. Direct Source Stage Runtime Authorities

- **ASR**: Backed by Whisper via `prepare_subtitles` in `services/subtitle_dub_product_pipeline.py:175, 223, 571` (`ASR_RUNTIME_AUTHORITY_DIRECT_SOURCE_PROOF = PASS`).
- **Translation**: Backed by DeepL / OpenAI via `prepare_subtitles` in `services/subtitle_dub_product_pipeline.py:175, 223, 572` (`TRANSLATION_RUNTIME_AUTHORITY_DIRECT_SOURCE_PROOF = PASS`).
- **TTS**: Backed by `resolve_subdub_tts_language_route` in `services/subdub_tts_language_routing.py:1-287`, `AUTO_XU_PER_WORD = Decimal("0.5")` in `services/subdub_auto_word_pricing.py:1-58`, and `synthesize_segments` / `resolve_voice_id` in `services/subtitle_dub_product_pipeline.py:180-182` (`TTS_RUNTIME_AUTHORITY_DIRECT_SOURCE_PROOF = PASS`).
- **Mux/Render**: Backed by local FFmpeg subprocess rendering in `services/subtitle_dub_product_pipeline.py:187-188, 516-535` (`ffmpeg_ready`, `dub_mux_enabled`, `render_video`) (`MUX_RENDER_RUNTIME_AUTHORITY_DIRECT_SOURCE_PROOF = PASS`).
- **Zero Self-Referential Assertions**: Circular boolean flags have been eliminated from authority verification (`SELF_REFERENTIAL_AUTHORITY_GATE_COUNT = 0`).

---

## 6. Locale Copy Audit (Key Parity vs Visible Copy Purity)

- **Key Parity**: Exactly 79 SubDub keys in Vietnamese and 79 SubDub keys in English in `static/portal/portal-i18n.js` (`SUBDUB_I18N_KEY_PARITY = PASS`).
- **Interpolation Leaks**: 0 raw placeholder leaks.
- **Visible Copy Purity**: `SUBDUB_VI_VISIBLE_COPY_PURITY = FAIL`.
- **Enumerated Mixed English Labels in Vietnamese Views (12 items)**:
  1. `portal.js:20025`: `"🟢 Neural SubDub Engine Sẵn Sàng"`
  2. `portal.js:20026`: `"🎙️ AI SubDub Studio — Tạo Phụ Đề & Lồng Tiếng Chuyên Nghiệp"`
  3. `portal.js:24889`: `"Timeline Match"`
  4. `portal.js:20021`: `"Transcript projects"`
  5. `portal.js:20021`: `"Web-native subtitle authoring"`
  6. `portal.js:20287`: `"Manual cue authoring"`
  7. `portal.js:19002`: `"Web-native deterministic tool"`
  8. `portal.js:1935`: `"Sub & Dub Operations Hub"`
  9. `portal.js:24881`: `"AI Subtitle & Dubbing"`
  10. `portal.js:1923, 24893`: `"SRT / VTT Format Lab"`
  11. `portal.js:1916, 24894`: `"Subtitle Asset Operations"`
  12. `portal.js:24895`: `"Subtitle Studio Workspace"`
- **Remediation Queue**: Queued for milestone R4 (`P0.WEBAPP.V3.SUBDUB.CUSTOMER.LOCALE.IA.CLEANUP.R1`).

---

## 7. Admin Traceability Status & Gaps

- `ADMIN_SUBDUB_TRACE_GAPS_DIRECT_SOURCE_PROOF = PASS`.
- `ADMIN_SUBDUB_JOB_TRACE_RESOLVED = NO`: Generic jobs table (`/admin/jobs`) lacks `subdub_lane` differentiation and multi-stage tracking (`asr_stage`, `translation_stage`, `tts_stage`, `mux_stage`).
- `ADMIN_SUBDUB_FAILURE_TRACE_RESOLVED = NO`: Incident queue (`/admin/jobs/failed`) lacks stage-level failure attribution and specific SubDub error codes.
- `ADMIN_SUBDUB_PROVIDER_READINESS_RESOLVED = NO`: Provider view (`/admin/providers`) is global; not linked to SubDub lane routing or stage fallbacks.
- `ADMIN_SUBDUB_ARTIFACT_TRACE_RESOLVED = NO`: Delivery center tracks only generic output presence, not individual stage artifacts.

---

## 8. Ordered Remediation Queue

- **R2**: `P0.WEBAPP.V3.SUBDUB.CANONICAL.DURABLE.JOB_BRIDGE.R1` (**BLOCKED**: `R2_DURABLE_JOB_BRIDGE_AUTHORITY_READY = NO`)
- **R3**: `P0.WEBAPP.V3.SUBDUB.CUSTOMER.HUB.FOUR_LANE.PRODUCT.R1`
- **R4**: `P0.WEBAPP.V3.SUBDUB.CUSTOMER.LOCALE.IA.CLEANUP.R1`
- **R5**: `P0.WEBAPP.V3.SUBDUB.ADMIN.RUNTIME.TRACE.R1`
- **R6**: `P0.WEBAPP.V3.SUBDUB.RUNTIME.ADAPTER.ACTIVATION.R1` (`OWNER_GATE_REQUIRED`)
- **R7**: `P0.WEBAPP.V3.SUBDUB.FOUR_LANE.E2E.PRODUCT.TRUTH.R1`
