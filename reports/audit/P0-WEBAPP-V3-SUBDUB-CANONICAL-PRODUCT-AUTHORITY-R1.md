# P0 WebApp SubDub Canonical Product Authority Reconciliation (R1)

- **Task**: `P0.WEBAPP.V3.SUBDUB.C1.INPUT.PRICING.EVIDENCE.AUTHORITY.TRUTH`
- **Parent Task**: `P0.WEBAPP.V3.SUBDUB.CANONICAL.PRODUCT.AUTHORITY.RECONCILIATION.R1`
- **Program**: `P0.WEBAPP.FULL.PRODUCT.TRUTH.REMEDIATION.V1`
- **Web Base Repository**: `manhtoangreensky-wq/toan-aas-standalone` (`WEB_BASE_SHA=db21c395eda8a2a23bbfac1ac9258f2c1840dce2`)
- **Bot Authority Repository**: `manhtoangreensky-wq/bot` (`BOT_AUTHORITY_SHA=661c0de773a68177f5c258843485a0177eb6b6e2`)
- **Mode**: `CORRECTION_ONLY`, `EVIDENCE_AND_TEST_ONLY`, `NO_UI_REDESIGN_YET`, `NO_RUNTIME_BRIDGE_YET`, `MINIMAL_CODE_FOOTPRINT`
- **Invariants**: `PROVIDER_CALLS=0`, `WALLET_MUTATIONS=0`, `MERGE=NO`, `DEPLOY=NO`, `RESTART=NO`

---

## 1. Preserved Verified R1 Invariants

| Invariant / Finding Flag | Value | Canonical Source & Empirical Verification |
|---|---|---|
| `FIRST_RED_SUBDUB_HUB_IS_UTILITY_FIRST` | **PROVEN** | `copyfast_pages.py:191`, `static/portal/portal.js:1935-1941, 24878-24921` |
| `SUBDUB_CANONICAL_LANES` | **4** | `bot.py:233106-233120`, `services/subdub_blackboxes/base.py` |
| `STATUS_ONLY_SUCCESS_AUTHORITY` | **NO** | `services/subtitle_dub_product_pipeline.py:546-557` (requires non-empty bytes) |
| `REAL_ARTIFACT_REQUIRED_FOR_COMPLETION` | **YES** | `services/subtitle_dub_product_pipeline.py:560-648` (verifies srt_bytes, audio_bytes, video_output) |
| `FICTIONAL_SUBTITLE_STUDIO_WORKBENCH_PRESENT` | **YES** | `static/portal/portal.js:20022-20120` (`portal-interactive-subdub-workbench`) |
| `UNSOURCED_99_5_ASR_BADGE_PRESENT` | **YES** | `static/portal/portal.js:24887-24888` (`qualityBadge: "99.5%"`) |
| `UNSOURCED_TIMELINE_MATCH_BADGE_PRESENT` | **YES** | `static/portal/portal.js:24889-24890` (`safetyBadge: "Timeline Match"`) |
| `SUBDUB_VI_LOCALE_PURITY` | **FAIL** | Mixed English labels in Vietnamese view (`portal-i18n.js`, `portal.js:20021`) |

---

## 2. Correct Pricing Authority

### A. Web Static Display Catalog (Not Canonical Bot Authority)
- **Source**: `static/portal/portal.js:22294-22296`
- **Authority**: `WEB_STATIC_ONLY` (`status: "read_only"`)
- **Entries**:
  - `subdub_subtitle`: `15 Xu / phút (~1.500 đ)`
  - `subdub_dub`: `25 Xu / phút (~2.500 đ)`
  - `subdub_combo`: `35 Xu / phút (~3.500 đ)`
- **Verdict**: `WEB_STATIC_SUBDUB_PRICE_IS_CANONICAL_AUTHORITY = NO`. These per-minute figures are presentation-only display estimates and MUST NOT be stated as Bot canonical pricing.

### B. Bot Canonical Price Keys, Units, and Derived Formulas
- **Source**: `bot.py:6766-6784, 6838-6855, 6878-6920`
- **Authority**: `BOT_CANONICAL`

| Canonical Price Key | Vietnamese Label | Unit | Default Value | Formula / Derivation |
|---|---|---|---|---|
| `subtitle_translate_video` | Dịch phụ đề video | **Xu/ký tự** | `0.1` | Base rate (`VIDEO_ONLY_SUBTITLE_TRANSLATE_RATE_XU`) |
| `auto_subtitle_video` | Tạo phụ đề tự động | **Xu** | `0` | Base rate (included / 0 Xu default) |
| `dub_video` | Lồng tiếng video | **Xu/ký tự** | `0.10` | Base rate (`VIDEO_ONLY_DUB_DEFAULT_RATE_XU`) |
| `subtitle_dub_video` | Phụ đề + lồng tiếng | **Xu/ký tự** | `0.20` | `subtitle_translate_video + dub_video` |
| `auto_subtitle_then_dub` | Tạo phụ đề rồi lồng tiếng | **Xu/ký tự** | `0.10` | `auto_subtitle_video + dub_video` |

### C. SubDub Auto Word Pricing Scope
- **Source**: `services/subdub_auto_word_pricing.py:1-58`
- **Rate**: `AUTO_XU_PER_WORD = Decimal("0.5")` (0.5 Xu/word)
- **Scope**: Dedicated strictly to Auto speaker diarization and casting (`subdub_auto_speaker`, `subdub_auto_settlement`). It is NOT generic dubbing pricing.
- **Verdict**: `SUBDUB_AUTO_WORD_PRICE_SCOPE_RESOLVED = YES`.

### D. Effective Runtime Pricing Status
- **Status**: `SUBDUB_EFFECTIVE_RUNTIME_PRICE_RESOLVED = NO`, `SUBDUB_PRICING_AUTHORITY_RESOLVED = PARTIAL`.
- **Reason**: Runtime pricing in Bot is dynamically overridden via SQLite `system_settings` (`canonical_price_xu:<key>`). The WebApp baseline does not possess an active, verified read-only pricing bridge for SubDub keys; effective runtime prices must not be fabricated.

---

## 3. Web Customer Form Authority vs. Bot Canonical Runtime Authority

### TABLE A: Current Web Customer Form Authority
- **Source**: `static/portal/portal.js:752-771` (`FIELD_SETS`)

| Form Name | Route(s) | Field Name | Control Type | Constraint / Options | Semantic Note |
|---|---|---|---|---|---|
| `subtitleCreate` | `/subtitle`, `/subtitle/create`, `/asr` | `source` | `file` | Audio/video MIME types | Required upload |
| | | `duration_seconds` | `number` | min: 1, max: 14400 | Required duration |
| | | `output_format` | `select` | `["srt"]` | Hardcoded SRT only |
| `subtitleTranslate` | `/translate` | `source` | `file` | `.srt,.vtt,.txt`, audio/video | Required upload |
| | | `target_language` | `select` | `LANGUAGE_OPTIONS` | Required language |
| | | `duration_seconds` | `number` | min: 1, max: 14400 | Required duration |
| | | `output_format` | `select` | `["srt"]` | Hardcoded SRT only |
| `dubbing` | `/dubbing` | `source` | `file` | Audio/video MIME types | Required upload |
| | | `mode` | `select` | `["dubbing", "subtitle_plus_dubbing"]` | Combo option present! |
| | | `target_language` | `select` | `LANGUAGE_OPTIONS` | Required language |
| | | `voice_profile_id` | `select` | `voiceProfiles` (Voice Vault) | Owner-scoped profile |
| | | `speed` | `select` | `1.0`, `0.9`, `1.5` | Fixed multipliers |
| | | `duration_seconds` | `number` | min: 1, max: 14400 | Required duration |
| | | `output_format` | `select` | `["srt"]` | **Semantic GAP: srt for dubbing** |

### TABLE B: Bot Canonical Runtime Input Authority
- **Source**: `bot.py`, `services/subtitle_dub_product_pipeline.py:170-224`

| Bot Runtime Field | Type | Domain / Values | Functional Purpose |
|---|---|---|---|
| `content_type` | `str` | `video/*`, `audio/*`, `text/plain` | Media discriminator |
| `source_bytes` | `bytes` | Raw binary media bytes | Pipeline payload |
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

## 4. Unproven Web Input Claims (Removed from Authority)

The following claims are **NOT** part of current Web customer authority:
1. `WEB_KEEP_ORIGINAL_AUDIO_AUTHORITY = NO`: `keep_original_audio` does not exist in any Web customer form.
2. `WEB_PROVIDER_VOICE_ID_AUTHORITY = NO`: Browser only selects `voice_profile_id` (owner-scoped Voice Vault profile), never a raw provider voice ID.
3. `WEB_REMOTE_MEDIA_URL_AUTHORITY = NO`: Real forms require `type: "file"`. Remote media URL inputs (YouTube/TikTok) exist only in the fictional workbench stub.
4. `FICTIONAL_UI_USED_AS_AUTHORITY = NO`: The mock `/subtitle-studio` workbench (`portal-interactive-subdub-workbench`) contains fake buttons and fake alerts; it confers zero authority.

---

## 5. Hub Authority & Combo Differentiation

1. `SUBDUB_HUB_BUSINESS_INPUT_SURFACE = NO`:
   - `/subdub` is registered as a customer navigation hub (`copyfast_registry.py:578`, `copyfast_pages.py:191`).
   - `renderSubDubHub` has `layout: "subdub-operations-hub"`, `fields: []`, `action: "none"`. It is NOT an input intake surface.
2. `HUB_COMBO_LAUNCHER_MISSING = YES`:
   - The `/subdub` Hub launcher grid links to `/subtitle/create`, `/dubbing`, `/translate`, `/asr`, but completely omits an explicit launcher for Lane 4 (`subtitle_plus_dub`).
3. `WEB_DUBBING_FORM_COMBO_MODE_PRESENT = YES`:
   - The Web `/dubbing` form (`portal.js:765`) explicitly includes `mode: ["dubbing", "subtitle_plus_dubbing"]`.
   - Statement *"Web has no combo capability anywhere"* is inaccurate and rejected; the capability is exposed inside the `/dubbing` form, but missing as a top-level launcher on the Hub.

---

## 6. Output Authority Separation

### A. Bot Canonical Output Capability (`BOT_OUTPUT_CAPABILITY_RESOLVED = YES`)
- `subtitle_create`: `.srt`, `.vtt`, `.txt`, `.mp4` (burn)
- `subtitle_translate`: `.srt` (translated), `.vtt` (translated), `.mp4` (translated burn)
- `dub`: `.mp4` (dubbed video), `.wav`/`.mp3` (dubbed audio)
- `subtitle_plus_dub`: `.mp4` (dual burned sub + dubbed audio), `.srt` (translated)

### B. Current Web Deliverable Truth (`WEB_CANONICAL_SUBDUB_RUNTIME_OUTPUT_PROVEN = NO`)
- `reports/audit/WEB_CUSTOMER_ADMIN_MASTER_INVENTORY_AND_GAP_MATRIX.json` line 241 specifies:
  `real_output: "SRT_VTT_LOCAL_ONLY"`
- Web currently delivers only client-side Format Lab conversions and signed Asset Vault container transformations. No canonical media artifact bridge exists.

---

## 7. Subtitle Output Format Discrepancies (Gaps)

- `subtitleCreate`: `output_format` offers only `["srt"]` (Bot supports `srt`, `vtt`, `txt`, `burn`).
- `subtitleTranslate`: `output_format` offers only `["srt"]` (Bot supports `srt`, `vtt`, `burn`).
- `dubbing`: `output_format` offers only `["srt"]` (Semantic GAP: dubbing output should be `video` or `audio`, not `srt`).
- `WEB_OUTPUT_FORM_VS_BOT_OUTPUT_GAPS_RESOLVED = YES`.

---

## 8. Voice Authority Separation

- `WEB_VOICE_PROFILE_AUTHORITY_RESOLVED = YES`: Web dubbing form accepts only `voice_profile_id` referencing a verified Voice Vault profile belonging to the signed account.
- `CLIENT_PROVIDER_VOICE_ID_AUTHORITY = NO`: Browser clients never specify provider voice IDs (e.g. MiniMax voice IDs).
- `BOT_VOICE_RESOLUTION_AUTHORITY_SEPARATE = YES`: The Bot Core resolves the provider voice ID server-side via `resolve_video_dub_tts_voice` or Auto speaker casting (`subdub_speaker_cast`).

---

## 9. Admin Traceability Findings

| Admin Surface | Code Reference | Columns / Surface | Current Gap / Forensic Evidence |
|---|---|---|---|
| `/admin/jobs` | `portal.js:30844-30847` | Job, Tính năng, Trạng thái, Chi phí canonical, Cập nhật, Output engine, Delivery, Thao tác | Does not differentiate the 4 SubDub canonical lanes; no multi-stage pipeline breakdown (`extracting_audio`, `transcribing`, `translating`, `synthesizing_speech`, `muxing`, `delivering`). |
| `/admin/jobs/failed` | `portal.js:30833-30843` | Job, Tính năng, Trạng thái, Nguyên nhân đã rút gọn, Chi phí / hoàn Xu, Output, Cập nhật | Lacks specific SubDub error codes (e.g., `TTS_SEGMENT_COVERAGE_FAILED`, `UNSUPPORTED_LANGUAGE_FOR_TTS`, `DIALOGUE_UNAVAILABLE`). |
| `/admin/providers` | `portal.js:30858-30890` | Mã Provider, Nhà cung cấp, Capabilities, Cấu hình, Khả dụng, Sức khỏe, Điều phối, Cập nhật | Generic status view; not linked to SubDub lane routing or per-stage provider fallback. |
| `/admin/runtime` | `portal.js:30844-30847` | Runtime status table | Generic runtime view. |
| `/admin/audit` | `portal.js:30815, 30897` | Sự kiện, Hành động, Kết quả, Thời điểm | Properly redacted; does not leak raw tokens or payload. |

---

## 10. Ordered Remediation Queue

- **R2**: `P0.WEBAPP.V3.SUBDUB.CANONICAL.DURABLE.JOB_BRIDGE.R1`
- **R3**: `P0.WEBAPP.V3.SUBDUB.CUSTOMER.HUB.FOUR_LANE.PRODUCT.R1`
- **R4**: `P0.WEBAPP.V3.SUBDUB.CUSTOMER.LOCALE.IA.CLEANUP.R1`
- **R5**: `P0.WEBAPP.V3.SUBDUB.ADMIN.RUNTIME.TRACE.R1`
- **R6**: `P0.WEBAPP.V3.SUBDUB.RUNTIME.ADAPTER.ACTIVATION.R1` (`OWNER_GATE_REQUIRED`)
- **R7**: `P0.WEBAPP.V3.SUBDUB.FOUR_LANE.E2E.PRODUCT.TRUTH.R1`

*(Production UI removal will be executed in R3 after authority reconciliation is locked).*
