# WEB-BOT-TTS-OUTPUT-STATE-20261114

Owner requests UI work and Web–Bot connection in parallel. This extends the
previous UI-only boundary only for the bounded Web adapter work described here.
It does not permit paid calls, credentials/auth/ENV, financial rules, Bot code,
production jobs or customer-data changes.

Source audit `WEB-BOT-TTS-PATH-20261114` used four anonymous public blobs at
1370471, exact against Git, fullMAP; one Gemini3.8FlashHigh session. Its output
was reviewed once. Retain only the demonstrated source state gap here; Web ID
versus Bot runtime ID and artifact-request nonce remain contract risks, not
demonstrated bugs. Do not repair those from conjecture.

Real Web adapter + fresh SQLite + controlled transport reproduced four cases:
nonfinal confirm, completed/no-audio confirm, and old completed/no-audio GET
repair failed; valid completed/audio/no-extra-read passed. All charged values
were zero; network, real provider, wallet and production writes were zero.
The first local harness was restricted at the Windows event-loop self-pipe;
bounded diagnostic identified that boundary. Authorized isolated rerun gave
1PASS/3RED. This is not actual Bot output or a worker implementation failure.

Allowlist: only success-state handling in `confirm_voice_tts_job` and
`reconcile_voice_tts_job_status` in `copyfast_voice_tts_job_bridge.py`.
Protected: auth/ownership/prepare/payment/quote/charged calculations and values,
routes/IDs/nonce, schema, error gates and every other application file.
No source application edits in the UI branch; worker returns a separate proposal.

- [x] Source-only path audit and local reproduction have concrete evidence.
- [ ] Antigravity R1 output matches finite allowlist, no financial logic change.
- [ ] New and existing pending/valid-complete/concurrency/quote/ownership cases
  pass against the real Web adapter in fresh owned SQLite without real calls.
- [ ] True completion cannot downgrade or re-confirm; missing audio cannot
  become complete, and subsequent read can retrieve the canonical artifact.
- [ ] Separate source commit, provenance, exact-head CI and delivery evidence.
- [ ] Actual authorized Web–Bot request and decodable audio prove final output.
  This remains NOT_OBSERVED and cannot be ticked by synthetic responses.
