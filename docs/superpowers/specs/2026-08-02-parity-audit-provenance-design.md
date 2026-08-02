# Parity audit provenance design

## Goal

Make the static Bot-to-Web parity evidence attributable to a concrete,
reproducible Web source snapshot, while preventing the audit implementation
itself from inflating Web runtime inventory.

## Scope

- The static auditor records a Web checkout SHA, requested revision relation,
  clean/dirty state and the fingerprint of the exact eligible Web source set.
- Command-line audits require an explicit `--web-revision` SHA. Direct
  `run_audit()` calls keep an optional argument so isolated parser fixtures do
  not need to manufacture a Git Web checkout unless they are testing revision
  semantics.
- `scripts/migration/` is audit tooling, not Web runtime source. It joins the
  existing exclusions for generated migration evidence and design/planning
  documents.
- A static-only verification mode confirms the committed evidence fingerprint
  still equals the checked-out source at the supplied GitHub SHA. It does not
  need a Bot checkout, import the app, or call a network, provider, payment or
  Telegram service.

## Truth model

Generated evidence may be committed after the source snapshot is audited.
Therefore its recorded checkout SHA may be an ancestor of the final evidence
commit. The verifier accepts that only when all of the following are true:

1. the checked-out Git HEAD equals the explicit expected SHA;
2. the checkout has no change in the eligible Web source set (generated
   migration evidence, planning documents and `scripts/migration/` tooling
   are intentionally outside that set);
3. the recorded SHA is an ancestor of the expected SHA; and
4. the recorded preflight and Web inventory fingerprints equal a fresh
   fingerprint of the eligible source files.

This makes an evidence-only follow-up commit valid but rejects an un-audited
runtime source change.

## Non-goals

- No Bot bridge, Telegram callback, wallet, PayOS, provider, job or output
  behavior changes.
- No new Web feature status or runtime-parity claim.
- No remote Git operation: all revision checks use local read-only Git.

## Acceptance criteria

- Audit tests prove tooling under `scripts/migration/` changes neither the
  runtime inventory nor its fingerprint.
- Audit tests prove a clean Git Web fixture records its requested SHA and
  source fingerprint.
- Verifier tests prove matching evidence passes, generated excluded evidence
  does not mark the source dirty, and both a dirty and a clean-but-un-audited
  source are rejected.
- GitHub Actions invoke the verifier with `${{ github.sha }}` before the
  bounded contract suite.
- Regenerated reports and generated migration README describe the Web snapshot
  and exclusion boundary without exposing secrets.
