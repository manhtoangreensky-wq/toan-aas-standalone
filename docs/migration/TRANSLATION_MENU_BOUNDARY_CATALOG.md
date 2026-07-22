# Translation menu boundary catalog

## Reviewed Web entrances

The following Telegram menu buttons may open a fresh Web workspace. They are
navigation only: the browser does not receive a Telegram message, pending
input, language pair, callback value, provider state, Xu state, or output.

| Bot callback | Web destination | Web-owned capability | Boundary |
| --- | --- | --- | --- |
| `menu|translate`, `menu|translation_language_hub` | `/subtitle-studio` | Subtitle & Transcript Workspace | Starts a signed manual transcript/cue workspace. |
| `menu|translation_text` | `/subtitle-studio` | Subtitle & Transcript Workspace | Lets the signed owner author source/translated draft text; no machine translation is claimed. |
| `menu|translation_document` | `/documents` | Document & PDF workspace | Opens a fresh document workspace; it does not import Telegram files or run document translation. |

`/subtitle-studio` can hold author-supplied source and translated cue text,
review state, revisions and SRT/VTT text export. A new project may refer to
safe metadata from the signed owner's own Asset Vault, but it never reads the
asset's bytes, opens a player/preview/download, imports a Telegram file ID or
runs ASR, translation, TTS, dubbing, media processing, a provider, Bot bridge,
job, payment or delivery.

## Finite translation-picker callbacks

The `tr_*` handler consumes Bot-local recent-file/recent-audio/pending-text
state. It is therefore **not** a dynamic Web namespace. Static review of the
frozen Bot baseline allows only these exact non-executing dispositions:

| Bot callback/template | Audit target | Status | Boundary |
| --- | --- | --- | --- |
| `tr_pick|file` | `/documents/translate` | `COPIED_GUARDED` | Fresh signed Document Translate navigation only. The browser receives no Telegram cache/file ID, bytes, pending request, target language or translation result. |
| `tr_pick|voice` | `/subtitle-studio` | `COPIED_GUARDED` | Fresh signed Language Source Intake only: manual text or metadata reference to the owner's Asset Vault. No audio bytes, ASR, translation, TTS, provider, job or output. |
| `tr_more|voice` | `/subtitle-studio` | `COPIED_GUARDED` | The Bot extended-language picker is not replayed. Web opens the same fresh guarded intake with no target selection carried over. |
| `tr_pick|{*}`, `tr_more|{*}` except the three literals above | `TRANSLATION_SOURCE_SELECTOR_REVIEW_REQUIRED` | `NEEDS_FEATURE_DISPOSITION` | Fail closed: a new source selector may depend on Telegram cache/pending state or a future execution path. |
| `tr_target|…` | `CORE_CANONICAL_TRANSLATION_GUARDED` | `NEEDS_FEATURE_DISPOSITION` | Target callbacks can enter Bot translation/provider paths; no browser provider, job, wallet, payment, output or delivery action is mapped. |
| `tr_transcribe` | `CORE_CANONICAL_ASR_GUARDED` | `NEEDS_FEATURE_DISPOSITION` | Bot requires recent Telegram audio/video and delegates transcription. A Web metadata reference is not ASR source bytes or an execution request. |

`COPIED_GUARDED` means a signed navigation compatibility surface, not a claim
that the Bot callback's media, target selection, provider action, charge or
delivery works in Web. The source selection is finite so a new `tr_pick|…` or
`tr_more|…` suffix cannot silently inherit either route.

## Known-broken Bot transcript menu

`menu|translation_transcript` is recorded as
`BOT_TRANSLATION_TRANSCRIPT_KNOWN_BROKEN`, not as an operational Web parity
mapping. The frozen Bot stores `transcript` pending state, but its later
`handle_translation_callback` branch accepts only `voice`, `file` and `text`,
then returns an unsupported-source alert. Manual transcript authoring remains
available independently through signed `/subtitle-studio`; that does not turn
the broken Bot branch into a working translation runtime.

## Telegram-only session state

The Bot's target-language selectors, auto-translate setting, two-way and live
conversation sessions, pair selection/swap/start templates, voice output,
voice input and stop/cancel controls remain `TELEGRAM_ONLY` in this phase.
They depend on a Telegram identity plus Bot-local pending/session state and,
for voice paths, a provider readiness decision. The Web must not recreate this
state from a callback or present a translated/voiced result it did not make.

A future standalone Translation runtime needs a separate owner-scoped source
model, language-pair model, provider policy, consent/retention rules, cost
estimate and confirmation, idempotency, job status, output validation and
private delivery contract. It must not reuse Bot session keys or a browser
supplied Telegram ID.

## Deliberately deferred video dubbing entry

`menu|translation_video_factory` is `VIDEO_TRANSLATION_MENU_DEFERRED`. The
Bot first records a pending video-dubbing state and later reaches voice,
provider and output actions. The project sequence reserves this entry for the
final finite Video menu catalog; it must not fall through to a generic
`/dubbing` page.

## Interface language is separate

Web interface locale is an account presentation preference (`vi`, `en`, `zh`)
and is intentionally separate from Bot translation target choices. Selecting a
translation target never changes the Web interface language, and changing Web
locale never changes Bot auto-translation mode.
