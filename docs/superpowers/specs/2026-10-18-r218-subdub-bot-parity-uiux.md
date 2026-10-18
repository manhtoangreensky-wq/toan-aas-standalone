# R218-SDUI — SubDub Bot Parity UI/UX

## Contract

- Repository: WebApp standalone.
- Allowed files: `static/portal/portal.js`, `static/portal/portal.css`,
  `static/portal/portal-i18n.js`, SubDub-specific tests, R218 docs.
- Protected: Bot repo, route-engine, provider adapters, wallet/PayOS, production data,
  existing auth and completed R217 contracts.
- Side effects: source/UI only; `PROVIDER_CALLS=0`, `WALLET_MUTATIONS=0`.

## Product model

The page has one workspace and four product modes:

| Mode | Input | Output contract |
|---|---|---|
| Phụ đề gốc | video/audio | SRT/VTT/TXT source subtitle |
| Phụ đề dịch | source subtitle/audio + target language | translated SRT/VTT, single or bilingual |
| Lồng tiếng | media + target language + voice lane | dubbed audio/video |
| Combo | media + target language + subtitle + voice lane | one subtitle artifact + one final dubbed MP4 |

The UI must expose the same source/target language, voice, quote and confirmation
concepts in all applicable modes. Combo must visually show that subtitle and dubbing
share one target language and one translation master.

## Voice lane contract

The dubbing and combo panels must show these mutually exclusive lanes as cards or a
segmented control, in this order:

1. `default_female` — Giọng nữ mặc định, no saved profile required.
2. `default_male` — Giọng nam mặc định, no saved profile required.
3. `saved_voice` — select a Voice Library profile owned by the signed account.
4. `custom_voice` — use a user-uploaded voice after consent and readiness checks.
5. `multi_two` — exactly two detected speakers, two distinct voice assignments.
6. `multi_three_eight` — automatic 3–8 speaker lane; the UI must show detected count
   and mapping summary when runtime data is available.
7. `auto_many` — automatic speaker discovery, bounded by server capability and fail-closed
   when evidence is insufficient.

Before bridge enablement, each lane may be disabled, but its label, reason, and link to
Voice Library must be truthful. A disabled lane must never look like a completed feature.

## State and report contract

The UI needs explicit states: `draft`, `checking`, `quote_ready`, `awaiting_confirm`,
`queued`, `processing`, `needs_review`, `completed`, `failed`, `guarded`.

The report panel must reserve rows for:

- request ID and job ID;
- selected mode and target language;
- voice lane and detected speaker count when available;
- subtitle artifact status (SRT/VTT);
- dubbed audio/video status;
- original/dubbing volume policy;
- failure reason and safe next action;
- download/export only when `completed` and `download_ready=true`.

## Layout and visual rules

- Use one vertical primary flow on mobile; desktop may use two columns only for independent
  subtitle and voice configuration cards.
- All interactive targets are at least 44×44px.
- Use the existing blue/navy/teal tokens; no black brand canvas and no raw inline gradients.
- Headings use the established portal type scale; body text stays at least 16px on mobile.
- Lane selection, disabled state, error state and current step must be distinguishable by
  text, border and icon, never color alone.
- Replace generic prose blocks with compact cards that answer: what it does, what is needed,
  what is ready, and what happens next.

## Acceptance tests

1. DOM contains one SubDub workspace with four modes and no duplicate form for the same mode.
2. Dubbing and combo DOM expose all seven voice lane keys in VI/EN/ZH.
3. `multi_two` and `multi_three_eight` are distinct controls; no `many` placeholder remains.
4. Voice Library and custom voice controls state their guarded reason when unavailable.
5. Combo has one shared target-language control and separate subtitle/dubbing config cards.
6. Report rows exist without inventing request/job/output data.
7. Mobile source gate proves no horizontal overflow and all controls meet 44px minimum.
8. `prefers-reduced-motion` leaves every state readable and interactive.
9. Existing SubDub tests and the full Node suite produce `NEW_FAILURES=0`.
10. No provider, wallet, PayOS or production-data action occurs in tests.

## Runtime gate

Source acceptance does not prove real dubbing. Runtime acceptance requires an isolated QA
fixture and real artifact evidence. Until then, the UI remains `guarded` and the checklist
must say `RUNTIME_OPEN`.
