# Parity Audit Provenance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make committed static parity evidence verifiable against the exact Web source snapshot and exclude audit tooling from Web runtime inventory.

**Architecture:** Keep `scripts/migration/audit_bot_to_web.py` static-only. Extend its existing local Git read helper with Web revision provenance, add a verifier that consumes only a Web checkout and generated JSON, and share the same eligible-file fingerprint path used by the normal audit. Generated reports remain outside that source set, so a follow-up evidence commit is valid only when the fingerprint is unchanged.

**Tech Stack:** Python 3.12+, pathlib, local Git subprocess reads, pytest, GitHub Actions YAML.

---

### Task 1: Define the audit provenance contract with failing tests

**Files:**
- Modify: `tests/test_migration_audit.py`
- Modify: `docs/superpowers/specs/2026-08-02-parity-audit-provenance-design.md`

- [ ] **Step 1: Add a failing Git-fixture test for revision provenance and tooling exclusion**

```python
def test_static_audit_records_web_revision_and_excludes_migration_tooling(tmp_path: Path) -> None:
    audit = _load_audit_module()
    bot_root = tmp_path / "bot"
    web_root = tmp_path / "web"
    bot_root.mkdir()
    web_root.mkdir()
    (bot_root / "bot.py").write_text("app = ApplicationBuilder().build()\n", encoding="utf-8")
    (web_root / "app.py").write_text("app = FastAPI()\n@app.get('/runtime')\ndef runtime(): return {}\n", encoding="utf-8")
    tooling = web_root / "scripts" / "migration" / "audit_helper.py"
    tooling.parent.mkdir(parents=True)
    tooling.write_text("os.getenv('SHOULD_NOT_BE_INVENTORIED')\n", encoding="utf-8")
    web_sha = _commit_web_fixture(web_root)

    result = audit.run_audit(bot_root, web_root, "baseline", tmp_path / "reports", tmp_path / "docs", web_revision_sha=web_sha)

    revision = result["preflight"]["webapp"]["revision"]
    assert revision["checkout_sha"] == web_sha
    assert revision["requested_sha"] == web_sha
    assert revision["requested_relation"] == "exact"
    assert revision["working_tree_state"] == "clean"
    assert revision["source_fingerprint_sha256"] == result["web_inventory"]["source_fingerprint_sha256"]
    assert result["web_inventory"]["source_files_scanned"] == 1
    assert "SHOULD_NOT_BE_INVENTORIED" not in json.dumps(result["web_inventory"])
```

- [ ] **Step 2: Run the new test and confirm it fails because the Web revision field and tooling exclusion do not yet exist**

Run: `python -m pytest -q tests/test_migration_audit.py::test_static_audit_records_web_revision_and_excludes_migration_tooling`

Expected: FAIL with a missing `web_revision_sha` parameter or missing `preflight.webapp.revision` field.

- [ ] **Step 3: Add a failing verifier test for matching evidence and dirty source**

```python
def test_verify_web_evidence_requires_clean_matching_source(tmp_path: Path) -> None:
    audit = _load_audit_module()
    bot_root, web_root, web_sha = _git_web_fixture(tmp_path)
    report_dir = web_root / "reports" / "migration"
    audit.run_audit(bot_root, web_root, "baseline", report_dir, web_root / "docs" / "migration", web_revision_sha=web_sha)

    verified = audit.verify_web_evidence(web_root, report_dir, web_sha)
    assert verified["expected_sha"] == web_sha
    assert verified["source_fingerprint_sha256"]

    (web_root / "app.py").write_text("app = FastAPI()\n# un-audited change\n", encoding="utf-8")
    with pytest.raises(ValueError, match="clean"):
        audit.verify_web_evidence(web_root, report_dir, web_sha)
```

- [ ] **Step 4: Run the verifier test and confirm it fails because `verify_web_evidence` does not exist**

Run: `python -m pytest -q tests/test_migration_audit.py::test_verify_web_evidence_requires_clean_matching_source`

Expected: FAIL with `AttributeError: module ... has no attribute 'verify_web_evidence'`.

- [ ] **Step 5: Cover a clean but un-audited Web revision**

After the dirty assertion, commit the changed `app.py` into the fixture so
the Git worktree is clean but its eligible source fingerprint differs from the
recorded evidence. Assert `verify_web_evidence(web_root, report_dir, new_sha)`
raises `ValueError` matching `fingerprint`. In the provenance test, make an
additional non-source Git commit and run the audit using the earlier SHA;
assert that the record exposes the actual current checkout SHA and
`requested_relation == "different"` rather than echoing the requested SHA.

### Task 2: Implement source provenance and static evidence verification

**Files:**
- Modify: `scripts/migration/audit_bot_to_web.py`
- Modify: `tests/test_migration_audit.py`

- [ ] **Step 1: Exclude migration tooling from eligible Web source files**

Add `Path("scripts") / "migration"` to `STANDARD_WEB_AUDIT_EXCLUDED_RELATIVE_DIRS` and revise the related guarantee/README text to say that migration tooling is excluded alongside generated evidence and planning documentation.

- [ ] **Step 2: Add Web revision provenance using only local Git reads**

Implement a helper that returns this sanitized shape:

```python
{
    "checkout_sha": "<40 lowercase hex or empty>",
    "requested_sha": "<caller SHA or empty>",
    "requested_relation": "exact|different|requested_sha_invalid|requested_revision_unavailable|not_requested|not_a_git_worktree",
    "working_tree_state": "clean|dirty|status_unavailable|not_a_git_worktree",
    "source_fingerprint_sha256": source_fingerprint_sha256,
}
```

Use `_git_read()` for `rev-parse`, `status --porcelain=v1 --untracked-files=normal` and revision resolution. Normalize each porcelain path and ignore it only when it lies under the same `STANDARD_WEB_AUDIT_EXCLUDED_RELATIVE_DIRS` boundary used for inventory; a changed `app.py` must remain dirty while fresh `reports/migration/` output is not. Pass `web_revision_sha` into `run_audit()`, compute the Web inventory before constructing its preflight section, and store the helper result at `preflight["webapp"]["revision"]`.

- [ ] **Step 3: Add an evidence-only verifier**

Implement:

```python
def verify_web_evidence(web_root: Path, report_dir: Path, expected_sha: str) -> dict[str, str]:
    """Verify committed Web evidence without inspecting or importing Bot code."""
```

It must reject an invalid/mismatched expected SHA, non-clean checkout, absent or malformed report fields, non-ancestor recorded audit SHA, and differing preflight/Web-inventory/current fingerprints. It returns only expected SHA, recorded audit SHA and the matching source fingerprint.

- [ ] **Step 4: Add command-line modes without weakening normal audit requirements**

Add `--web-revision` as an explicit required input for the normal CLI audit path. Add `--verify-web-evidence` that needs only `--web-root`, `--report-dir` and `--web-revision`; it calls `verify_web_evidence()` and prints a sanitized JSON success envelope. Normal mode still requires `--bot-root` and `--bot-baseline-sha` before it calls `run_audit()`.

- [ ] **Step 5: Run the two focused tests and confirm they pass**

Run: `python -m pytest -q tests/test_migration_audit.py::test_static_audit_records_web_revision_and_excludes_migration_tooling tests/test_migration_audit.py::test_verify_web_evidence_requires_clean_matching_source`

Expected: `2 passed`.

### Task 3: Regenerate evidence and make CI verify it

**Files:**
- Modify: `.github/workflows/webapp-quality.yml`
- Modify: `docs/migration/README.md`
- Modify: `reports/migration/preflight.json`
- Modify: `reports/migration/web_inventory.json`
- Modify: `reports/migration/bot_inventory.json`
- Modify: `reports/migration/parity_gap.json`
- Modify: generated `docs/migration/*.md` changed only by the auditor
- Test: `tests/test_migration_audit.py`

- [ ] **Step 1: Add the CI evidence verifier before bounded contracts**

```yaml
- name: Verify committed migration evidence
  env:
    WEB_AUDIT_EXPECTED_SHA: ${{ github.sha }}
  run: |
    python scripts/migration/audit_bot_to_web.py \
      --verify-web-evidence \
      --web-root . \
      --report-dir reports/migration \
      --web-revision "$WEB_AUDIT_EXPECTED_SHA"
```

- [ ] **Step 2: Commit implementation source first**

```bash
git add scripts/migration/audit_bot_to_web.py tests/test_migration_audit.py \
  .github/workflows/webapp-quality.yml docs/superpowers/specs/2026-08-02-parity-audit-provenance-design.md \
  docs/superpowers/plans/2026-08-02-parity-audit-provenance.md
git commit -m "Add Web parity audit provenance gate"
```

- [ ] **Step 3: Regenerate evidence from the clean implementation commit**

```powershell
& 'C:\Users\toann\AppData\Local\Python\pythoncore-3.14-64\python.exe' scripts/migration/audit_bot_to_web.py `
  --bot-root 'D:\TOANAAS\bot telegram' `
  --web-root . `
  --bot-baseline-sha b29d0d474974075f4cba963d2c510f49d2d1b3e4 `
  --web-revision (git rev-parse HEAD) `
  --report-dir reports/migration `
  --docs-dir docs/migration
```

- [ ] **Step 4: Commit generated evidence separately**

```bash
git add docs/migration reports/migration
git commit -m "Refresh Web parity audit evidence"
```

- [ ] **Step 5: Run risk-focused verification from the final evidence commit**

```bash
python -m py_compile scripts/migration/audit_bot_to_web.py
python -m pytest -q tests/test_migration_audit.py
python scripts/migration/audit_bot_to_web.py --verify-web-evidence --web-root . --report-dir reports/migration --web-revision "$(git rev-parse HEAD)"
git diff --check origin/main...HEAD
```

Expected: static audit tests pass, the final checkout validates its evidence fingerprint, and no whitespace errors are reported.
