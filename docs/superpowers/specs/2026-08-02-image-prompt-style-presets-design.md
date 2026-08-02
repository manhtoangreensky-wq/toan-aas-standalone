# Image Prompt Composer Style Presets — Design

## Purpose

Give the Web-native Image Prompt Composer a small, explicit style chooser so a
customer can start with a useful direction without copying Bot callback values
or relying on an unstructured free-text field.  This remains a deterministic,
request-only planning surface: it never creates an image, job, provider call,
wallet mutation, asset, or Telegram state.

## Approved scope

The composer accepts one new semantic field, `style_preset`, with exactly five
values:

| Value | Meaning |
| --- | --- |
| `auto` | Server selects the existing default direction for the selected goal and language. |
| `suggestion_1` | Server selects the first goal- and language-specific Web direction. |
| `suggestion_2` | Server selects the second goal- and language-specific Web direction. |
| `suggestion_3` | Server selects the third goal- and language-specific Web direction. |
| `custom` | Customer supplies the existing bounded `style` text field. |

The preset is an opaque Web contract, not a Bot callback alias.  The client
does not receive Bot tokens, provider/model identifiers, image/file IDs,
pending state, tier, quote, job, payment, or delivery information.

## Request and result rules

`style` is required only for `custom`, and must be empty for all four
server-resolved choices.  For backwards compatibility, an older request that
omits `style_preset` but includes a valid `style` is treated as `custom`; an
older request with neither retains the existing auto/default behaviour.  An
explicit invalid, Bot-shaped, or mismatched combination is rejected.

The server is the only resolver for presets.  It returns the chosen
`style_preset` alongside the resolved safe `style` in the existing strict
result schema.  The Memory Center save handoff carries only the same bounded
selection and the server recomputes the prompt transactionally.

## Interaction design

The form uses a labelled select with four clear starting directions and a
`Tự nhập` choice.  The custom textarea is hidden and disabled until `Tự nhập`
is selected, then becomes required and announces the change through a polite
status message.  Switching away hides and disables it, so stale text never
becomes part of a server-resolved request.

The control follows the existing portal form system: visible labels,
keyboard-operable select, 44px-compatible shared controls, an explicit
description, focused states from portal tokens, responsive one-column layout,
and no decorative motion.  It inherits the product's app shell rather than
introducing a separate visual language.

## Security and non-goals

- Direct API calls are schema-validated and cannot smuggle text into a preset.
- The originality guard still applies to custom text; fixed server catalog
  values are original generic directions.
- Signed session, CSRF, no-store headers, request-size limits, existing
  ownership checks, and Memory idempotency remain unchanged.
- This work does not add image generation, preview, upload, provider,
  Bot/core-bridge, payment, wallet, job, or persistent result behaviour.

## Verification

Tests prove every preset resolves deterministically per goal/language, custom
input is required and guarded, malformed/mismatched requests fail, legacy
input remains compatible, Memory recomputation retains the selection, and
portal code keeps the source/result boundary strict.  The focused API and
portal contract tests run before review and merge.
