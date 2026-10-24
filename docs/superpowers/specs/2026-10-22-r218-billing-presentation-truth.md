# R218 — billing presentation truth and acceptance repair

Base `e5b1f5866867221f6ffd131a43f1644dc2c6249a`, branch
`webapp-r218-billing-ui-20261022`. One batch, one final PR. Motion remains last.

## Scope and measured baseline

Production metadata supplies four monthly plans and twenty combos. Package cards
eventually render after hydration; no published customer price can be inferred from
their names, quotas, notes or old static tables. Approved public sale SKUs/version
remain the only displayed sale-price source. No catalog publication is authorized.

The candidate had two invalid completion claims: history state was used for failed
options GET and its retry only read history; uniform QR scale/crop had not proved
quiet-zone preservation. Both are reopened before acceptance.

Wallet regression on the unchanged backend succeeds outside sandbox: 21 passed in
20.06s. The previous TestClient hang was sandbox loopback/self-pipe access, not proof
that Python or production failed. Do not change dependencies/tests/event-loop policy.

## Ordered acceptance

1. **AC-02-TOPUP-CATALOG-TRUTH**: remove client fallback top-up tiers; render only
   valid server rows. Retain request/catalog/capability guards and confirmation.
   Distinguish options GET loading/failure/ready/unavailable from history GET state.
   A dedicated retry reads options and cannot create a transaction. Stale/session/
   route fences must hold on every state merge.
2. **AC-02-PRICING-PACKAGES-CANONICAL**: verify the upstream sale projection, do not
   manufacture prices. Localize only the exact known internal legacy-note text;
   leave other customer/package content untouched. Do not infer visibility or
   purchase availability from a human note. Real price-publication gap remains open.
3. **AC-02-QR-ACB-PRESENTATION**: dedupe ACB choices using readiness; preserve an
   existing ready selected alias, otherwise prefer ready VietQR then ready bank.
   If neither is ready, do not enable either. Never rewrite confirmed IDs/history.
   Enlarge the full QR image responsively without scale/crop, losing modules or
   quiet zone. Maintain original bytes/endpoint and default visible instructions.
4. **UT-YT-RESULT-TRUTH**: do not promise 1080p/720p/360p for unmeasured thumbnails;
   names and success text must describe link preparation/actual preview, not fetched
   video/media. Preserve parser, URLs, controls and image lifecycle.

## Tests and gates

- Behavioral tests execute production renderers and hydration, not only regex.
- Failure/retry, invalid/empty/valid catalog, missing capability, ready/blocked ACB
  combinations, stale metadata, history-independent state and locale VI/EN/ZH.
- Signed local QA375/390/768/1440, light/dark; measure whole image bounds and
  document overflow, keyboard labels, loading/error/recovery and image dimensions.
- Wallet/backend tests on isolated DB/mocked bridge; no production transactions.
- Reproduce known CSS test failures against base before calling them baseline.
- Review/operations docs/tester packet/provenance before push, then exact HEAD CI.
- Do not change backend/schema/auth guards, financial rules, provider, original QR,
  ENV/secret, production data or deployment workflow.

## Status

Candidate incomplete. Narrow source tests are prior evidence only. No browser,
delivery or LIVE acceptance for this uncommitted batch yet. Runtime/financial
execution is not made complete by UI acceptance. Master ledger remains R218.
