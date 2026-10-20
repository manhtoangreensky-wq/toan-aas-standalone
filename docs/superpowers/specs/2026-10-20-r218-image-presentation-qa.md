# IM-R218 — Image presentation/runtime QA gate

## CONTRACT

Close only the Image UI/UX presentation gate for `/image/create`,
`/image/background-cleanup`, `/image/upscale`, and `/image/transform`.
Reference-image upload, AI/manual edit execution, quote/confirm, artifacts and
delivery remain server-gated and are not simulated.

Acceptance: create/prompt/AI-edit/manual navigation remains vertical and
localized VI/EN/ZH; form contracts for prompt/tier/ratio/source/scale stay
visible; guarded states are honest; no fake result, media, download, provider,
price or readiness claim; responsive 390/768/1440 and light/dark have no
overflow or console/external/mutation errors.

Verify: Image-focused Node suite and authenticated Edge QA matrix. Provider
calls and wallet mutations are zero; LIVE is not claimed.
