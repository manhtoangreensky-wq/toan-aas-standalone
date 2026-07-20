# Translation menu boundary catalog

## Reviewed Web entrances

The following Telegram menu buttons may open a fresh Web workspace. They are
navigation only: the browser does not receive a Telegram message, pending
input, language pair, callback value, provider state, Xu state, or output.

| Bot callback | Web destination | Web-owned capability | Boundary |
| --- | --- | --- | --- |
| `menu|translate`, `menu|translation_language_hub` | `/subtitle-studio` | Subtitle & Transcript Workspace | Starts a signed manual transcript/cue workspace. |
| `menu|translation_text`, `menu|translation_transcript` | `/subtitle-studio` | Subtitle & Transcript Workspace | Lets the signed owner author source/translated draft text; no machine translation is claimed. |
| `menu|translation_document` | `/documents` | Document & PDF workspace | Opens a fresh document workspace; it does not import Telegram files or run document translation. |

`/subtitle-studio` can hold author-supplied source and translated cue text,
review state, revisions and SRT/VTT text export. It does not run ASR,
translation, TTS, dubbing, media processing, a provider, Bot bridge, job,
payment or delivery.

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
