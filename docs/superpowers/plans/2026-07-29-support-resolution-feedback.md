# Support Resolution Feedback Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the signed owner of a resolved or closed Web Support Desk case one safe, revision-pinned satisfaction submission and give Customer Care managers a redacted aggregate quality view.

**Architecture:** `copyfast_support.py` remains the sole feature owner. A narrow additive SQLite table stores one feedback receipt for `(case_id, terminal_revision)`; its POST route validates signed ownership, CSRF, confirmation, terminal state, exact revision, strict input and idempotency in one transaction. Customer detail reads project only the current revision receipt; the manager-only aggregate read never returns a case, account, comment or raw audit entry. The Portal validates every field again, renders the existing compact teal–sky Support card/form family, and refreshes the source case after a successful receipt.

**Tech Stack:** FastAPI, Pydantic v2 strict models, SQLite, signed sessions/CSRF, existing support idempotency ledger/audit logger, vanilla Portal JavaScript/CSS tokens, pytest/TestClient, Node syntax checks.

---

### Task 1: Establish the failing security and lifecycle contract

**Files:**

- Create: `tests/test_support_resolution_feedback.py`
- Read: `tests/test_copyfast_support.py`
- Read: `tests/test_copyfast_support_care.py`
- Read: `copyfast_support.py:458-723, 727-970, 1369-2028, 2049-2180`
- Read: `copyfast_db.py:2170-2333`

- [ ] **Step 1: Create an isolated full-app fixture with two signed customers and Web-local support roles**

```python
MODULES = ["app", "copyfast_db", "copyfast_auth", "copyfast_auth_throttle", "copyfast_support"]

def make_client(tmp_path, monkeypatch, *, support_enabled=True):
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "support-resolution-feedback.db"))
    monkeypatch.setenv("WEB_SESSION_SECRET", "support-resolution-feedback-test-secret")
    monkeypatch.setenv("WEBAPP_SUPPORT_DESK_ENABLED", "true" if support_enabled else "false")
    for name in MODULES:
        sys.modules.pop(name, None)
    return TestClient(importlib.import_module("app").app)

def register_and_login(client, email):
    registered = client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "correct-horse-battery-staple",
        "display_name": "Support feedback owner",
    })
    assert registered.status_code == 200
    logged_in = client.post("/api/v1/auth/login", json={
        "email": email,
        "password": "correct-horse-battery-staple",
    })
    assert logged_in.status_code == 200
    return logged_in.json()["data"]["csrf_token"]
```

- [ ] **Step 2: Write the RED owner terminal-receipt test**

```python
def test_owner_can_submit_one_feedback_for_the_current_terminal_revision(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "owner-feedback@example.com")
        case = create_case_then_close(client, csrf)
        response = client.post(
            f"/api/v1/support/cases/{case['id']}/resolution-feedback",
            headers={"X-CSRF-Token": csrf},
            json={
                "rating": 5,
                "comment": "Hướng dẫn rõ ràng, dễ thực hiện.",
                "expected_revision": case["revision"],
                "confirm": True,
                "idempotency_key": "support-feedback-owner-0001",
            },
        )
        assert response.status_code == 200
        receipt = response.json()["data"]["resolution_feedback"]
        assert receipt["rating"] == 5
        assert receipt["terminal_revision"] == case["revision"]
        assert receipt["terminal_state"] == "closed"
        assert "comment" not in receipt
```

- [ ] **Step 3: Run the focused test and verify the route fails because it does not exist**

Run:

```powershell
& C:\Users\toann\Documents\Codex\2026-07-10\1-ngu-n-ch-nh-v\.venvs\toanaas-webapp-copyfast177\Scripts\python.exe -m pytest -q tests\test_support_resolution_feedback.py::test_owner_can_submit_one_feedback_for_the_current_terminal_revision
```

Expected: FAIL with a missing route/404 assertion. Do not add production code before observing this RED result.

- [ ] **Step 4: Add failing negative-path and receipt-redaction tests**

```python
@pytest.mark.parametrize("patch", [
    {"confirm": False},
    {"expected_revision": 999},
    {"rating": 0},
    {"rating": 6},
    {"rating": "5"},
    {"comment": "api_key=super-secret-token-value"},
    {"account_id": "browser-must-not-select-owner"},
])
def test_resolution_feedback_rejects_invalid_or_untrusted_input(tmp_path, monkeypatch, patch):
    response = submit_feedback(client, csrf, terminal_case, **patch)
    assert response.status_code in {200, 422}
    assert response.json()["ok"] is False or response.status_code == 422
    assert feedback_count(db_path) == 0
```

Also cover a foreign owner case id, unsigned session, invalid CSRF, `new`/`reviewing` case, disabled Support Desk, duplicate terminal revision using a distinct key, and same-key/different-body idempotency collision. Assert every guarded result leaves `web_support_case_resolution_feedback` unchanged.

- [ ] **Step 5: Add failing terminal-cycle and manager aggregate tests**

```python
def test_reopened_case_can_receive_feedback_only_after_a_new_terminal_revision(tmp_path, monkeypatch):
    first = submit_feedback(client, csrf, first_terminal_case)
    reopened = reopen_case(client, csrf, first_terminal_case)
    assert submit_feedback(client, csrf, reopened).json()["error_code"] == "WEB_SUPPORT_FEEDBACK_NOT_TERMINAL"
    second_terminal = close_case(client, csrf, reopened)
    second = submit_feedback(client, csrf, second_terminal, key="support-feedback-cycle-0002")
    assert second.json()["data"]["resolution_feedback"]["terminal_revision"] == second_terminal["revision"]

def test_manager_sees_only_redacted_aggregate_and_operator_is_forbidden(tmp_path, monkeypatch):
    manager = login_as_role(client, "manager-feedback@example.com", "support_manager")
    operator = login_as_role(client, "operator-feedback@example.com", "support_operator")
    summary = manager.get("/api/v1/support/admin/care/resolution-feedback-summary?days=30")
    assert summary.status_code == 200
    data = summary.json()["data"]
    assert set(data) >= {"window_days", "total_responses", "rating_counts", "average_rating", "comments_count", "delivery"}
    assert "case_id" not in json.dumps(data)
    assert operator.get("/api/v1/support/admin/care/resolution-feedback-summary").status_code == 403
```

- [ ] **Step 6: Run the complete new test file and record the expected RED failures**

Run:

```powershell
& C:\Users\toann\Documents\Codex\2026-07-10\1-ngu-n-ch-nh-v\.venvs\toanaas-webapp-copyfast177\Scripts\python.exe -m pytest -q tests\test_support_resolution_feedback.py
```

Expected: the new route, schema and projection assertions fail; existing Support tests are not changed.

### Task 2: Add an additive schema and strict Support-owned server contract

**Files:**

- Modify: `copyfast_db.py:2170-2333`
- Modify: `copyfast_support.py:20-35, 340-460, 727-970, 1050-1222, 1622-1685, 2021-2050`
- Test: `tests/test_support_resolution_feedback.py`

- [ ] **Step 1: Add the additive feedback table and non-destructive indexes inside `ensure_copyfast_schema()`**

```python
conn.execute("""
    CREATE TABLE IF NOT EXISTS web_support_case_resolution_feedback (
        id TEXT PRIMARY KEY,
        case_id TEXT NOT NULL,
        account_id TEXT NOT NULL,
        terminal_revision INTEGER NOT NULL,
        terminal_state TEXT NOT NULL,
        rating INTEGER NOT NULL,
        comment TEXT NOT NULL DEFAULT '',
        created_at TEXT NOT NULL,
        CHECK(terminal_revision >= 1),
        CHECK(terminal_state IN ('resolved', 'closed')),
        CHECK(rating BETWEEN 1 AND 5),
        CHECK(length(comment) <= 600),
        UNIQUE(case_id, terminal_revision),
        FOREIGN KEY(case_id) REFERENCES web_support_cases(id),
        FOREIGN KEY(account_id) REFERENCES web_accounts(id)
    )
""")
conn.execute("CREATE INDEX IF NOT EXISTS idx_web_support_feedback_owner_created ON web_support_case_resolution_feedback(account_id, created_at DESC, id DESC)")
conn.execute("CREATE INDEX IF NOT EXISTS idx_web_support_feedback_terminal_created ON web_support_case_resolution_feedback(terminal_state, created_at DESC, id DESC)")
```

Do not alter `web_support_cases`, Bot tables, payment tables, existing case revisions, or historical messages/events.

- [ ] **Step 2: Define strict request/read helpers in `copyfast_support.py`**

```python
TERMINAL_FEEDBACK_STATES = frozenset({"resolved", "closed"})
MAX_RESOLUTION_FEEDBACK_COMMENT = 600
MAX_RESOLUTION_FEEDBACK_WINDOW_DAYS = 365

class ResolutionFeedbackRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    rating: int = Field(ge=1, le=5)
    comment: str = Field(default="", max_length=MAX_RESOLUTION_FEEDBACK_COMMENT)
    expected_revision: int = Field(ge=1, le=1_000_000)
    confirm: bool = False
    idempotency_key: str = Field(min_length=12, max_length=160)

    @field_validator("comment")
    @classmethod
    def validate_comment(cls, value: str) -> str:
        return _safe_text(value, label="Nhận xét", minimum=0, maximum=MAX_RESOLUTION_FEEDBACK_COMMENT, allow_empty=True)

    @field_validator("idempotency_key")
    @classmethod
    def validate_idempotency_key(cls, value: str) -> str:
        return _idempotency_key(value)
```

Add `_resolution_feedback_receipt(row)` that returns only `rating`, `terminal_revision`, `terminal_state`, and `submitted_at`; add `_current_resolution_feedback(conn, case_id, account_id, revision, state)` that only queries a matching terminal feedback row; add `_bounded_feedback_days(days)` that accepts only 1–365. Do not include comment in a public projection.

- [ ] **Step 3: Extend the owner-only `_case_detail` response without broadening staff detail**

```python
result = {
    "case": _case_public(row, include_detail=True, admin=admin, include_assignee_id=...),
    "messages": ...,
    "events": ...,
    "attachments": ...,
    "delivery": "web_view_only",
}
if not admin:
    result["resolution_feedback"] = _current_resolution_feedback(
        conn,
        case_id=str(row[0]),
        account_id=str(row[1]),
        revision=int(row[7]),
        state=str(row[6]),
    )
```

`resolution_feedback` is `None` for non-terminal states or a receipt belonging to an older terminal revision. Admin detail never returns customer feedback/comment data.

- [ ] **Step 4: Implement the customer POST route atomically through the existing idempotency ledger**

```python
@router.post("/cases/{case_id}/resolution-feedback")
async def create_resolution_feedback(
    case_id: str,
    payload: ResolutionFeedbackRequest,
    request: Request,
    account: dict = Depends(require_csrf),
):
    _require_support_enabled()
    if not payload.confirm:
        raise HTTPException(status_code=422, detail="Cần xác nhận trước khi gửi đánh giá hỗ trợ")
    case_id = _uuid(case_id, label="Mã yêu cầu")
    account_id = str(account["id"])
    fingerprint = _fingerprint({
        "rating": payload.rating,
        "comment_sha256": _content_hash(payload.comment),
        "expected_revision": payload.expected_revision,
        "confirm": True,
    })

    def operation(conn):
        current = _case_row(conn, case_id=case_id, account_id=account_id)
        if not current:
            return _case_not_found()
        if int(current[7]) != payload.expected_revision:
            return envelope(False, "Yêu cầu đã có cập nhật mới. Hãy tải lại trước khi đánh giá.", data={"current_revision": int(current[7])}, status_name="guarded", error_code="WEB_SUPPORT_CASE_CONFLICT")
        if str(current[6]) not in TERMINAL_FEEDBACK_STATES:
            return envelope(False, "Chỉ yêu cầu đã được giải quyết hoặc đã đóng mới có thể đánh giá.", status_name="guarded", error_code="WEB_SUPPORT_FEEDBACK_NOT_TERMINAL")
        existing = _current_resolution_feedback(conn, case_id=case_id, account_id=account_id, revision=int(current[7]), state=str(current[6]))
        if existing:
            return envelope(False, "Revision yêu cầu này đã có đánh giá.", data={"resolution_feedback": existing}, status_name="guarded", error_code="WEB_SUPPORT_FEEDBACK_EXISTS")
        now = utc_now()
        feedback_id = str(uuid.uuid4())
        conn.execute("INSERT INTO web_support_case_resolution_feedback (id, case_id, account_id, terminal_revision, terminal_state, rating, comment, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (feedback_id, case_id, account_id, int(current[7]), str(current[6]), payload.rating, payload.comment, now))
        receipt = {"rating": payload.rating, "terminal_revision": int(current[7]), "terminal_state": str(current[6]), "submitted_at": now}
        _record_audit(conn, account_id=account_id, canonical_user_id=str(account.get("canonical_user_id") or "") or None, action="web.support.case.resolution_feedback", request_id=_request_id(request), target=case_id, detail=f"web support feedback recorded rating:{payload.rating} revision:{int(current[7])}; comment_not_in_audit")
        return envelope(True, "Đã ghi nhận đánh giá cho revision yêu cầu hiện tại.", data={"resolution_feedback": receipt, "delivery": "web_view_only"}, status_name="completed")

    return _idempotent(f"web-support:{account_id}:case:{case_id}:resolution-feedback", payload.idempotency_key, fingerprint, operation)
```

If a direct unique-key collision occurs, return `WEB_SUPPORT_FEEDBACK_EXISTS` without replacing or deleting a receipt. Do not increment a case revision, emit `_event`, change lifecycle, or send notifications.

- [ ] **Step 5: Implement the manager-only redacted aggregate route**

```python
@router.get("/admin/care/resolution-feedback-summary")
async def admin_resolution_feedback_summary(days: int = 30, account: dict = Depends(require_account)):
    _require_support_enabled()
    _require_support_manager(account)
    window_days = _bounded_feedback_days(days)
    cutoff = (datetime.now(timezone.utc) - timedelta(days=window_days)).isoformat(timespec="seconds")
    with transaction() as conn:
        rows = conn.execute("SELECT rating, COUNT(*) FROM web_support_case_resolution_feedback WHERE created_at>=? GROUP BY rating", (cutoff,)).fetchall()
        comments = conn.execute("SELECT COUNT(*) FROM web_support_case_resolution_feedback WHERE created_at>=? AND comment<>''", (cutoff,)).fetchone()
    rating_counts = {str(rating): 0 for rating in range(1, 6)}
    for rating, count in rows:
        rating_counts[str(int(rating))] = int(count)
    total = sum(rating_counts.values())
    average = round(sum(int(key) * value for key, value in rating_counts.items()) / total, 2) if total else None
    return envelope(True, "Tổng hợp chất lượng Customer Care đã được redaction.", data={"window_days": window_days, "total_responses": total, "rating_counts": rating_counts, "average_rating": average, "comments_count": int(comments[0] or 0), "delivery": "internal_metadata_only"}, status_name="read_only")
```

Do not return comment text, case/account identifiers, timestamps, customer name, email, audit values, Bot information, external delivery, payment, or provider state.

- [ ] **Step 6: Run the server suite and verify GREEN**

Run:

```powershell
& C:\Users\toann\Documents\Codex\2026-07-10\1-ngu-n-ch-nh-v\.venvs\toanaas-webapp-copyfast177\Scripts\python.exe -m pytest -q tests\test_support_resolution_feedback.py tests\test_copyfast_support.py tests\test_copyfast_support_care.py
```

Expected: all selected server tests pass; duplicate feedback does not create a second row and neither receipt nor audit carries raw comment content.

### Task 3: Add raw-body and fixed rate-family safety before router work

**Files:**

- Modify: `app.py:420-730, 1600-1935`
- Test: `tests/test_support_resolution_feedback.py`

- [ ] **Step 1: Declare and inject a compact feedback body limit into `PromptLibraryBodyLimitMiddleware`**

```python
SUPPORT_RESOLUTION_FEEDBACK_BODY_MAX_BYTES = 8 * 1024

@staticmethod
def _is_support_resolution_feedback_path(path: str) -> bool:
    return path.startswith("/api/v1/support/cases/") and path.rstrip("/").endswith("/resolution-feedback")
```

Add the path predicate to `_is_bounded_write`, add a `support_resolution_feedback_max_bytes` initializer argument/instance field, select it before the generic default in `_limit_for`, and produce the explicit guarded error code `WEB_SUPPORT_RESOLUTION_FEEDBACK_BODY_TOO_LARGE` with `Cache-Control: no-store` through the existing rejection envelope. The error contains no submitted text or case identifier.

- [ ] **Step 2: Give the endpoint a fixed pre-DB rate family**

```python
support_resolution_feedback_write = (
    request.method == "POST"
    and PromptLibraryBodyLimitMiddleware._is_support_resolution_feedback_path(request.url.path)
)

if support_resolution_feedback_write:
    rate_limit = 12

rate_scope = (
    "support-resolution-feedback-write" if support_resolution_feedback_write
    else "support-consultation-brief-compose" if support_consultation_compose
    else ...
)
```

Place this branch before the broader `support_write` scope. The fixed scope must apply to normal paths, trailing slashes, malformed UUID segments, and arbitrary route suffix attempts that end in `resolution-feedback`, so path churn cannot create unbounded limiter buckets.

- [ ] **Step 3: Add RED/then GREEN assertions for body and limiter behavior**

```python
def test_feedback_body_cap_and_fixed_rate_scope_happen_before_router_validation(tmp_path, monkeypatch):
    too_large = client.post(path, headers={"Content-Type": "application/json"}, content=b"{" + b'"x":"' + b"x" * 9000 + b'"}')
    assert too_large.status_code == 413
    assert too_large.json()["error_code"] == "WEB_SUPPORT_RESOLUTION_FEEDBACK_BODY_TOO_LARGE"
    assert "support-resolution-feedback-write" in app_module._auth_rate_windows
```

Submit 13 malformed feedback-route POSTs under the same client fixture and assert the final response is `429`; assert no feedback row exists.

- [ ] **Step 4: Run the focused safety tests**

Run:

```powershell
& C:\Users\toann\Documents\Codex\2026-07-10\1-ngu-n-ch-nh-v\.venvs\toanaas-webapp-copyfast177\Scripts\python.exe -m pytest -q tests\test_support_resolution_feedback.py -k "body or rate or feedback"
```

Expected: pass with no change to generic auth, Bot bridge, provider, payment, wallet, webhook, or PWA behavior.

### Task 4: Wire strict Portal projections, feedback form, and manager aggregate panel

**Files:**

- Modify: `static/portal/integration.js:1540-1730, 12270-12840, 13680-13715, 18111-18280, 31560-31700`
- Modify: `static/portal/portal.js:20270-21105, 21702-21945`
- Create: `tests/test_support_resolution_feedback_portal_contracts.py`
- Read: `static/portal/portal-theme.css`

- [ ] **Step 1: Add a closed browser projection for current feedback receipt**

```javascript
const SUPPORT_FEEDBACK_TERMINAL_STATES = new Set(["resolved", "closed"]);

function supportResolutionFeedbackProjection(value, caseItem) {
  const item = value && typeof value === "object" && !Array.isArray(value) ? value : null;
  if (!item) return null;
  const rating = supportReadPositiveInteger(item.rating);
  const revision = supportReadPositiveInteger(item.terminal_revision);
  const state = String(item.terminal_state || "").trim().toLowerCase();
  const submittedAt = supportReadTimestamp(item.submitted_at, false);
  if (!caseItem || !rating || rating > 5 || revision !== caseItem.revision
      || state !== caseItem.state || !SUPPORT_FEEDBACK_TERMINAL_STATES.has(state) || !submittedAt
      || Object.prototype.hasOwnProperty.call(item, "comment")) return null;
  return { rating, terminal_revision: revision, terminal_state: state, submitted_at: submittedAt };
}
```

Update `supportCustomerCaseDetailProjection` to accept only `null` or this projection and place it under `detail.resolution_feedback`. Clear it with the rest of support detail state on session/path/read failure.

- [ ] **Step 2: Add the new feedback capability, manager-summary hydration, and action**

```javascript
"support-resolution-feedback-submit": Boolean(account && me.csrf_token && supportDeskEnabled),
```

After `/support/admin/summary` has proved the server role is `manager`, request `/support/admin/care/resolution-feedback-summary?days=30` independently. Validate every aggregate field, keep it empty/guarded if the request fails, and never request it for an operator. Store it in `supportAdminResolutionFeedbackSummary` and clear it on every admin/session failure.

```javascript
if (action === "support-case-resolution-feedback") {
  const caseId = String(detail.supportCaseId || "").trim();
  const revision = validSupportRevision(detail.supportCaseRevision);
  const payload = supportResolutionFeedbackPayload(fields);
  if (!validSupportCaseId(caseId) || !revision) throw new Error("Mã hoặc revision yêu cầu Support Desk không hợp lệ.");
  const scope = `support:case:${caseId}:resolution-feedback:${revision}`;
  const submission = acquireSubmission(scope, JSON.stringify({ ...payload, revision }));
  if (!submission) return;
  setActionBusy(action, route, true);
  try {
    const result = await api(`/support/cases/${encodeURIComponent(caseId)}/resolution-feedback`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...payload, expected_revision: revision, confirm: true, idempotency_key: submission.key })
    });
    await hydrateSupportCase(caseId);
    toast(result.message || "Đã ghi nhận đánh giá cho yêu cầu Web.");
  } finally {
    releaseSubmission(submission);
    setActionBusy(action, route, false);
  }
  return;
}
```

`supportResolutionFeedbackPayload()` must require integer 1–5, optional `comment` at most 600 characters validated by `validateWebSupportText`, and an explicit `feedback_confirmed` checkbox. It must not accept `account_id`, role, case state, terminal state, raw receipt, or browser timestamp.

- [ ] **Step 3: Render compact customer and manager surfaces using existing tokens**

```javascript
function renderSupportResolutionFeedback(context, caseItem, revision) {
  const terminal = ["resolved", "closed"].includes(supportCaseState(caseItem.state));
  const receipt = context.supportCaseDetail && context.supportCaseDetail.resolution_feedback;
  if (!terminal) return "";
  if (receipt) return `<section class="portal-card portal-card-pad" data-support-resolution-feedback-receipt>...</section>`;
  return `<section class="portal-card portal-card-pad" data-support-resolution-feedback-form>...
    <fieldset><legend>Đánh giá trải nghiệm hỗ trợ</legend>
      <label><input type="radio" name="rating" value="1" required> 1</label> ... <label><input type="radio" name="rating" value="5"> 5</label>
    </fieldset>
    <label class="portal-field"><span>Nhận xét (không bắt buộc)</span><textarea class="portal-textarea" name="comment" maxlength="600"></textarea></label>
    <label class="portal-checkbox"><input type="checkbox" name="feedback_confirmed" value="true" required><span>Tôi xác nhận gửi đánh giá cho revision hiện tại.</span></label>
    <button class="portal-button portal-button--primary" type="submit">Gửi đánh giá</button>
  </section>`;
}
```

Insert the customer panel after the case summary and before the reply form. It uses existing semantic form/control classes, labels, `aria-live` status text, confirmation behavior, and token-driven colors; it adds no raw hex, image, hero, localStorage, sessionStorage, emoji icon, synthetic score, or motion-specific layout.

Render a manager-only `Customer Care Quality` panel inside `renderSupportAdminBase()` with `portal-operations-metrics`. It presents response count, average (or `Chưa có dữ liệu` when null), comments count, and 1–5 histogram labels. It contains no click-through, case link, customer content, identity, or operator fallback.

- [ ] **Step 4: Write static portal contract tests before implementation and then turn them GREEN**

```python
def test_portal_feedback_action_is_csrf_idempotent_revision_pinned_and_has_no_local_storage():
    action = slice_between(INTEGRATION, 'if (action === "support-case-resolution-feedback")', 'if (action === "support-case-attachment")')
    assert "/resolution-feedback" in action
    assert "expected_revision" in action
    assert "idempotency_key" in action
    assert "confirm: true" in action
    assert "localStorage" not in action and "sessionStorage" not in action
    assert "account_id" not in action and "terminal_state" not in action

def test_portal_manager_quality_summary_has_only_aggregate_fields():
    assert "resolution-feedback-summary" in INTEGRATION
    assert "Customer Care Quality" in PORTAL
    assert "comment" not in manager_summary_slice(PORTAL)
```

Also assert a current receipt is rendered read-only; non-terminal pages omit the form; Portal uses current server revision; PWA's service worker does not add `/api/v1/support/` to cache lists.

- [ ] **Step 5: Run browser syntax and static contracts**

Run:

```powershell
node --check static\portal\integration.js
node --check static\portal\portal.js
& C:\Users\toann\Documents\Codex\2026-07-10\1-ngu-n-ch-nh-v\.venvs\toanaas-webapp-copyfast177\Scripts\python.exe -m pytest -q tests\test_support_resolution_feedback_portal_contracts.py
```

Expected: both JavaScript files parse and every client boundary test passes.

### Task 5: Focused verification, independent review, and sequential merge

**Files:**

- Modify: `copyfast_db.py`, `copyfast_support.py`, `app.py`, `static/portal/integration.js`, `static/portal/portal.js`
- Create: `tests/test_support_resolution_feedback.py`, `tests/test_support_resolution_feedback_portal_contracts.py`
- Create: `docs/superpowers/specs/2026-07-29-support-resolution-feedback-design.md`, `docs/superpowers/plans/2026-07-29-support-resolution-feedback.md`

- [ ] **Step 1: Run the high-risk focused regression suite**

```powershell
& C:\Users\toann\Documents\Codex\2026-07-10\1-ngu-n-ch-nh-v\.venvs\toanaas-webapp-copyfast177\Scripts\python.exe -m pytest -q tests\test_support_resolution_feedback.py tests\test_support_resolution_feedback_portal_contracts.py tests\test_copyfast_support.py tests\test_copyfast_support_care.py
```

Expected: all selected tests pass; no Bot, provider, bridge, payment, PayOS, wallet, webhook, or live service is imported or called.

- [ ] **Step 2: Run compact syntax, scope, and cache-boundary checks**

```powershell
& C:\Users\toann\Documents\Codex\2026-07-10\1-ngu-n-ch-nh-v\.venvs\toanaas-webapp-copyfast177\Scripts\python.exe -m py_compile copyfast_support.py copyfast_db.py app.py
node --check static\portal\integration.js
node --check static\portal\portal.js
git diff --check
git diff --name-only origin/main...HEAD
```

Expected: clean whitespace/syntax and only the files named above differ from `origin/main`.

- [ ] **Step 3: Run local browser QA on the actual signed flow**

Use a local temporary test DB and signed test account. Confirm desktop and 375px widths: terminal case shows the form, confirm dialog submits once, the receipt replaces the form after server refresh, non-terminal/reopened cases hide it, the manager sees only aggregate quality metrics, and an operator is guarded. Inspect focus order, visible labels, 44px controls, teal–sky contrast, responsive wrapping, and no horizontal overflow. Remove temporary DB/log/screenshot artifacts afterward.

- [ ] **Step 4: Obtain two independent reviews**

First request a spec-compliance review for owner scope, exact terminal revision, no state mutation, strict payload, sensitivity validation, raw-body/rate boundaries, idempotency/unique collision, manager-only aggregate, and forbidden-system isolation. Only after that review passes, request a code-quality/security review for transaction behavior, timestamp/query correctness, no comment leakage, UI projection guards, accessibility, cache/storage boundaries, and test quality. Fix every finding and re-run the relevant review/test.

- [ ] **Step 5: Commit, push, create PR, wait for CI, and merge sequentially**

```powershell
git add copyfast_db.py copyfast_support.py app.py static\portal\integration.js static\portal\portal.js tests\test_support_resolution_feedback.py tests\test_support_resolution_feedback_portal_contracts.py docs\superpowers\specs\2026-07-29-support-resolution-feedback-design.md docs\superpowers\plans\2026-07-29-support-resolution-feedback.md
git commit -m "Add Support Resolution Feedback"
git push -u origin feature/p0-webapp-copyfast178-support-resolution-feedback
gh pr create --base main --head feature/p0-webapp-copyfast178-support-resolution-feedback --title "Add Support Resolution Feedback" --body "## Summary`n- Add revision-pinned Support Desk resolution feedback`n- Add redacted Customer Care manager aggregate`n- Keep Bot/payment/provider systems out of scope`n`n## Verification`n- Focused Support feedback, Support Desk, and Portal contracts"
```

After GitHub CI passes, merge the PR into `main`, verify the merge commit is visible on `origin/main`, and let Railway deploy from `main`. Do not perform a direct Railway deploy or enable production provider/payment calls.
