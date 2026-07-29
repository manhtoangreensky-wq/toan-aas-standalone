# Content Handoff → Workboard Follow-up Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a signed owner turn one eligible Content Handoff revision into exactly one private, editable Workboard follow-up without copying sensitive Handoff data or invoking external systems.

**Architecture:** The Workboard module owns a small additive relation table and a dedicated POST endpoint. It validates the Handoff directly inside the same SQLite transaction, creates a normal owner-owned Workboard item through a shared internal helper, and returns only safe identifiers/revision/link state. Reads reconcile a stale source to `superseded` while never mutating the customer's card.

**Tech Stack:** FastAPI, Pydantic v2 strict models, SQLite transactions and existing `web_idempotency` ledger, signed session/CSRF middleware, existing portal JavaScript and PWA cache controls, pytest/TestClient.

---

### Task 1: Establish the follow-up boundary with failing end-to-end tests

**Files:**

- Create: `tests/test_content_handoff_workboard_followup.py`
- Read: `tests/test_copyfast_content_handoff.py`
- Read: `tests/test_copyfast_workboard.py`
- Read: `copyfast_content_handoff.py:199-270, 463-547, 1267-1344`
- Read: `copyfast_workboard.py:25-132, 697-839, 1124-1170`

- [ ] **Step 1: Write a shared full-app fixture that authenticates two owners and a Support Manager**

```python
def make_client(tmp_path, monkeypatch):
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "handoff-followup.db"))
    monkeypatch.setenv("WEB_SESSION_SECRET", "handoff-followup-test-secret")
    monkeypatch.setenv("WEBAPP_CONTENT_HANDOFF_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_WORKBOARD_ENABLED", "true")
    for module_name in MODULES:
        sys.modules.pop(module_name, None)
    return TestClient(importlib.import_module("app").app)

def login(client, email, *, role="customer"):
    registered = client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "correct-horse-battery-staple",
        "display_name": "Follow-up owner",
    })
    assert registered.status_code == 200
    # Test fixture may set the desired Web-local role directly only after
    # registration; the endpoint must never accept a browser role field.
    return client.post("/api/v1/auth/login", json={
        "email": email,
        "password": "correct-horse-battery-staple",
    }).json()["data"]["csrf_token"]
```

- [ ] **Step 2: Add the initial failing owner-path contract**

```python
def test_owner_creates_one_followup_from_an_approved_handoff(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = login(client, "owner-followup@example.com")
        handoff = create_and_approve_handoff(client, csrf)
        payload = {
            "handoff_id": handoff["id"],
            "expected_handoff_revision": handoff["revision"],
            "title": "Theo dõi bước bàn giao nội bộ",
            "checklist": [{"body": "Rà soát tiến độ follow-up", "is_done": False}],
            "priority": "high",
            "due_at": "2026-08-01T09:00",
            "confirm": True,
            "idempotency_key": "handoff-followup-owner-0001",
        }
        created = client.post("/api/v1/workboard/content-handoff-followups", headers={"X-CSRF-Token": csrf}, json=payload)
        assert created.status_code == 200
        assert created.json()["ok"] is True
        assert created.json()["data"]["content_handoff_followup"]["link_state"] == "active"
```

- [ ] **Step 3: Run the test to verify it fails for the absent route**

Run:

```powershell
C:\Users\toann\Documents\Codex\2026-07-10\1-ngu-n-ch-nh-v\.venvs\toanaas-webapp-copyfast177\Scripts\python.exe -m pytest -q tests\test_content_handoff_workboard_followup.py::test_owner_creates_one_followup_from_an_approved_handoff
```

Expected: FAIL because `POST /api/v1/workboard/content-handoff-followups` does not exist.

- [ ] **Step 4: Add failing authorization, lifecycle, and input-boundary tests**

```python
@pytest.mark.parametrize("patch", [
    {"confirm": False},
    {"expected_handoff_revision": 999},
    {"staff_note": "do not copy"},
    {"purpose": "do not copy"},
    {"references": [{"ref_type": "project", "ref_id": str(uuid.uuid4())}]},
])
def test_followup_rejects_unconfirmed_stale_or_sensitive_input(tmp_path, monkeypatch, patch):
    response = client.post("/api/v1/workboard/content-handoff-followups", headers={"X-CSRF-Token": csrf}, json={**payload, **patch})
    assert response.status_code in {200, 422}
    assert response.json()["ok"] is False or response.status_code == 422
```

Also cover foreign-owner ID, manager account attempting an owner's follow-up, `draft`, `review`, `blocked`, and archived source states. Assert no `web_workboard_items` row is created after every guarded outcome.

- [ ] **Step 5: Add failing retry, race, and supersession tests**

```python
first = client.post(PATH, headers={"X-CSRF-Token": csrf}, json=payload)
replay = client.post(PATH, headers={"X-CSRF-Token": csrf}, json=payload)
assert replay.json()["data"]["item"]["id"] == first.json()["data"]["item"]["id"]

with pytest.raises(sqlite3.IntegrityError):
    insert_duplicate_relation_for_same_handoff_revision(db_path, handoff, first_item_id)

supersede_handoff_revision(db_path, handoff["id"])
detail = client.get(f"/api/v1/workboard/items/{first_item_id}")
assert detail.json()["data"]["content_handoff_followup"]["link_state"] == "superseded"
assert detail.json()["data"]["item"]["state"] == "backlog"
```

- [ ] **Step 6: Run the complete new test file and record the expected RED failures**

Run:

```powershell
C:\Users\toann\Documents\Codex\2026-07-10\1-ngu-n-ch-nh-v\.venvs\toanaas-webapp-copyfast177\Scripts\python.exe -m pytest -q tests\test_content_handoff_workboard_followup.py
```

Expected: route/model/schema assertions fail before implementation; no unrelated test file is changed.

### Task 2: Add the additive relation schema and safe internal source/card helpers

**Files:**

- Modify: `copyfast_workboard.py:25-132, 640-839, 1124-1170`
- Test: `tests/test_content_handoff_workboard_followup.py`

- [ ] **Step 1: Extend `_ensure_schema()` with the relation table and indexes**

```python
conn.execute("""
    CREATE TABLE IF NOT EXISTS web_content_handoff_workboard_followups (
        id TEXT PRIMARY KEY,
        account_id TEXT NOT NULL,
        handoff_id TEXT NOT NULL,
        handoff_revision INTEGER NOT NULL,
        workboard_item_id TEXT NOT NULL,
        link_state TEXT NOT NULL DEFAULT 'active',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        superseded_at TEXT,
        CHECK(link_state IN ('active', 'superseded')),
        UNIQUE(handoff_id, handoff_revision),
        UNIQUE(workboard_item_id),
        FOREIGN KEY(account_id) REFERENCES web_accounts(id),
        FOREIGN KEY(workboard_item_id) REFERENCES web_workboard_items(id)
    )
""")
conn.execute("CREATE INDEX IF NOT EXISTS idx_handoff_workboard_followups_owner_item ON web_content_handoff_workboard_followups(account_id, workboard_item_id)")
```

- [ ] **Step 2: Add a strict request model and source selector**

```python
class ContentHandoffFollowupCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    handoff_id: str
    expected_handoff_revision: int = Field(ge=1)
    title: str
    checklist: list[ChecklistInput] = Field(default_factory=list)
    priority: str = "normal"
    due_at: str | None = None
    confirm: bool
    idempotency_key: str

def _eligible_handoff(conn, *, handoff_id: str, account_id: str, expected_revision: int):
    row = conn.execute(
        "SELECT id, account_id, handoff_status, record_state, revision FROM web_content_handoff_records WHERE id=? AND account_id=?",
        (handoff_id, account_id),
    ).fetchone()
    if not row:
        return _guarded("Không tìm thấy Content Handoff thuộc Web account hiện tại.", "WEB_WORKBOARD_HANDOFF_NOT_FOUND")
    if str(row[3]) != "active":
        return _guarded("Content Handoff đã archive nên không thể tạo follow-up.", "WEB_WORKBOARD_HANDOFF_ARCHIVED")
    if int(row[4]) != expected_revision:
        return _guarded("Content Handoff đã có revision mới. Hãy tải lại trước khi tạo follow-up.", "WEB_WORKBOARD_HANDOFF_REVISION_CONFLICT")
    if str(row[2]) not in {"approved_for_handoff", "handed_off"}:
        return _guarded("Content Handoff chưa sẵn sàng để tạo follow-up Workboard.", "WEB_WORKBOARD_HANDOFF_NOT_ELIGIBLE")
    return {"id": str(row[0]), "revision": int(row[4]), "status": str(row[2])}
```

The selector must not select `purpose`, `staff_note`, `references_json`, or reviewer values.

- [ ] **Step 3: Extract the existing normal card creation code into one transaction-only helper**

```python
def _create_item_in_transaction(conn, *, account, request, payload: ItemPayload, audit_action: str) -> dict[str, Any]:
    if not _references_are_owned(conn, account_id=str(account["id"]), references=payload.references):
        return _guarded("Reference Workboard không tồn tại hoặc không thuộc Web account hiện tại.", "WEB_WORKBOARD_REFERENCE_NOT_FOUND")
    # Preserve the existing insert, checklist version, item version, event,
    # audit, and receipt behavior from create_item without accepting a source
    # Handoff as a generic reference.
```

Refactor `create_item()` to call the helper unchanged in behavior; the helper receives the already validated owner payload and does not call any external service.

- [ ] **Step 4: Run the tests to verify schema and helper checks turn green**

Run:

```powershell
C:\Users\toann\Documents\Codex\2026-07-10\1-ngu-n-ch-nh-v\.venvs\toanaas-webapp-copyfast177\Scripts\python.exe -m pytest -q tests\test_content_handoff_workboard_followup.py -k "owner or stale or sensitive"
```

Expected: owner creation, source lifecycle, and strict-model tests PASS; retry/supersession tests remain RED until Task 3/4.

### Task 3: Implement the idempotent owner-confirmed endpoint

**Files:**

- Modify: `copyfast_workboard.py:839-895, after create_item()`
- Test: `tests/test_content_handoff_workboard_followup.py`

- [ ] **Step 1: Implement the endpoint with CSRF, confirmation, and an explicit idempotency scope**

```python
@router.post("/content-handoff-followups")
async def create_content_handoff_followup(
    payload: ContentHandoffFollowupCreateRequest,
    request: Request,
    account: dict = Depends(require_csrf),
):
    _require_enabled()
    if not payload.confirm:
        raise HTTPException(status_code=422, detail="Cần xác nhận rõ ràng trước khi tạo follow-up Workboard")
    account_id = str(account["id"])
    fingerprint = _fingerprint({
        "handoff_id": payload.handoff_id,
        "expected_handoff_revision": payload.expected_handoff_revision,
        "title": payload.title,
        "checklist": [{"body": entry.body, "is_done": entry.is_done} for entry in payload.checklist],
        "priority": payload.priority,
        "due_at": payload.due_at,
    })
    scope = f"web-workboard:{account_id}:content-handoff:{payload.handoff_id}:followup:create"
```

- [ ] **Step 2: Write the whole owner write atomically inside `_idempotent`**

```python
def operation(conn):
    source = _eligible_handoff(conn, handoff_id=payload.handoff_id, account_id=account_id, expected_revision=payload.expected_handoff_revision)
    if isinstance(source, dict) and source.get("ok") is False:
        return source
    relation = conn.execute(
        "SELECT workboard_item_id FROM web_content_handoff_workboard_followups WHERE handoff_id=? AND handoff_revision=?",
        (source["id"], source["revision"]),
    ).fetchone()
    if relation:
        return _guarded("Revision Content Handoff này đã có follow-up Workboard.", "WEB_WORKBOARD_HANDOFF_FOLLOWUP_EXISTS")
    item = _create_item_in_transaction(
        conn,
        account=account,
        request=request,
        payload=ItemPayload(
            title=payload.title,
            description="",
            priority=payload.priority,
            due_at=payload.due_at,
            references=[],
            checklist=payload.checklist,
        ),
        audit_action="web.workboard.content_handoff_followup.create",
    )
    if item.get("ok") is not True:
        return item
    item_id = str(item["data"]["item"]["id"])
    followup_id = str(uuid.uuid4())
    now = utc_now()
    conn.execute(
        """INSERT INTO web_content_handoff_workboard_followups
           (id, account_id, handoff_id, handoff_revision, workboard_item_id, link_state, created_at, updated_at, superseded_at)
           VALUES (?, ?, ?, ?, ?, 'active', ?, ?, NULL)""",
        (followup_id, account_id, source["id"], source["revision"], item_id, now, now),
    )
    _event(conn, account_id=account_id, item_id=item_id, entity_type="content_handoff_followup", entity_id=source["id"], action="content_handoff_followup_created", item_revision=1, entity_revision=source["revision"])
    return envelope(
        True,
        "Đã tạo follow-up Workboard riêng tư từ revision Content Handoff hiện tại.",
        data=_boundary(
            item=item["data"]["item"],
            content_handoff_followup={
                "id": followup_id,
                "handoff_id": source["id"],
                "handoff_revision": source["revision"],
                "link_state": "active",
            },
        ),
        status_name="completed",
    )
```

Catch only the relation unique-constraint collision and turn it into a guarded duplicate response; do not retry a non-idempotent write and do not double-create a card.

- [ ] **Step 3: Verify idempotent replay, collision, and receipt redaction**

Run:

```powershell
C:\Users\toann\Documents\Codex\2026-07-10\1-ngu-n-ch-nh-v\.venvs\toanaas-webapp-copyfast177\Scripts\python.exe -m pytest -q tests\test_content_handoff_workboard_followup.py -k "idempotent or duplicate or receipt"
```

Expected: PASS. Stored `web_idempotency.response_json` contains only the Workboard item ID/revision/state and safe follow-up ID/revision/link state, never title, checklist body, purpose, staff note, or source references.

### Task 4: Reconcile source supersession and expose the safe portal confirmation flow

**Files:**

- Modify: `copyfast_workboard.py:1037-1128, 1535-1563`
- Modify: `static/portal/portal.js` Content Handoff detail renderer
- Modify: `static/portal/integration.js` Content Handoff hydrator, capability flags, and action dispatcher
- Modify: `tests/test_workboard_portal_contracts.py`
- Test: `tests/test_content_handoff_workboard_followup.py`

- [ ] **Step 1: Add a private relation reconciler and minimal public projection**

```python
def _reconcile_handoff_followup(conn, *, account_id: str, item_id: str) -> dict[str, Any] | None:
    relation = conn.execute("SELECT id, handoff_id, handoff_revision, link_state FROM web_content_handoff_workboard_followups WHERE account_id=? AND workboard_item_id=?", (account_id, item_id)).fetchone()
    if not relation:
        return None
    source = conn.execute("SELECT handoff_status, record_state, revision FROM web_content_handoff_records WHERE id=? AND account_id=?", (relation[1], account_id)).fetchone()
    should_supersede = not source or str(source[1]) != "active" or str(source[0]) == "blocked" or int(source[2]) != int(relation[2])
    if should_supersede and str(relation[3]) != "superseded":
        conn.execute("UPDATE web_content_handoff_workboard_followups SET link_state='superseded', updated_at=?, superseded_at=? WHERE id=?", (utc_now(), utc_now(), relation[0]))
    return {"handoff_id": str(relation[1]), "handoff_revision": int(relation[2]), "link_state": "superseded" if should_supersede else str(relation[3])}
```

Call it from owner-only Workboard list/detail read paths. It may update only the relation; it must never alter `web_workboard_items`, checklist rows, schedule intents, version history, or Workboard card state.

- [ ] **Step 2: Add a compact eligible-state form to the existing Content Handoff detail page**

The renderer shows the form only when `record_state === "active"` and status is `approved_for_handoff` or `handed_off`. It uses fresh user-entered values; never prepopulates from Handoff purpose, staff note, recipient, or references.

```javascript
if (eligibleForWorkboardFollowup(record)) {
  const followupMarkup = [
    `<form data-action="content-handoff-workboard-followup" data-handoff-id="${escapeHtml(record.id)}">`,
    '<input name="title" maxlength="180" required />',
    '<textarea name="checklist" maxlength="360"></textarea>',
    '<select name="priority"><option value="normal">Bình thường</option><option value="high">Cao</option></select>',
    '<input type="datetime-local" name="due_at" />',
    '<label><input type="checkbox" name="confirm" required /> Tôi xác nhận tạo follow-up riêng tư</label>',
    '<button type="submit">Tạo follow-up Workboard</button>',
    '</form>',
  ].join("");
  html += followupMarkup;
}
```

The integration action sends only the closed endpoint fields, uses the current record revision, a generated idempotency key, CSRF, boundary verification, then refreshes both Handoff detail and Workboard state. It does not use localStorage/sessionStorage, external URLs, browser file upload, or provider/payment/bridge APIs.

- [ ] **Step 3: Add static PWA and portal contract assertions**

```python
assert 'api("/workboard/content-handoff-followups"' in INTEGRATION
assert 'content-handoff-workboard-followup' in INTEGRATION
assert 'purpose' not in followup_action_slice
assert 'staff_note' not in followup_action_slice
assert 'localStorage' not in followup_action_slice
assert '"/" + "api/v1/workboard"' in SERVICE_WORKER
```

- [ ] **Step 4: Run supersession, UI contract, and PWA boundary tests**

Run:

```powershell
C:\Users\toann\Documents\Codex\2026-07-10\1-ngu-n-ch-nh-v\.venvs\toanaas-webapp-copyfast177\Scripts\python.exe -m pytest -q tests\test_content_handoff_workboard_followup.py tests\test_workboard_portal_contracts.py
```

Expected: PASS. The PWA has no eligible cache path for the private API; owner sees a minimal source link only; source supersession leaves the card untouched.

### Task 5: Verify scope, review, and deliver the isolated PR

**Files:**

- Modify: `docs/superpowers/specs/2026-07-29-content-handoff-workboard-followup-design.md`
- Create: `docs/superpowers/plans/2026-07-29-content-handoff-workboard-followup.md`
- Modify: only files named in Tasks 1-4

- [ ] **Step 1: Run the high-risk focused suite in the isolated environment**

```powershell
C:\Users\toann\Documents\Codex\2026-07-10\1-ngu-n-ch-nh-v\.venvs\toanaas-webapp-copyfast177\Scripts\python.exe -m pytest -q tests\test_content_handoff_workboard_followup.py tests\test_copyfast_content_handoff.py tests\test_copyfast_workboard.py tests\test_workboard_portal_contracts.py
```

Expected: all selected tests pass; no Bot, provider, bridge, wallet, payment, PayOS, webhook, or live service is invoked.

- [ ] **Step 2: Run syntax and source-boundary checks**

```powershell
C:\Users\toann\Documents\Codex\2026-07-10\1-ngu-n-ch-nh-v\.venvs\toanaas-webapp-copyfast177\Scripts\python.exe -m py_compile copyfast_workboard.py
node --check static\portal\portal.js
node --check static\portal\integration.js
git diff --check
git diff --name-only $(git merge-base origin/main HEAD) HEAD
```

Expected: clean syntax/whitespace; diff contains only this feature's contract, server, portal, test, spec, and plan files.

- [ ] **Step 3: Request independent spec review, then code-quality/security-boundary review**

Reviewers must verify exact owner scope, CSRF, revision guard, status guard, idempotency, unique relation, no sensitive source-field transfer, supersession without card mutation, PWA private cache exclusion, and no forbidden subsystem import/call.

- [ ] **Step 4: Commit and open a PR only after reviews pass**

```powershell
git add copyfast_workboard.py static\portal\portal.js static\portal\integration.js tests\test_content_handoff_workboard_followup.py tests\test_workboard_portal_contracts.py docs\superpowers\specs\2026-07-29-content-handoff-workboard-followup-design.md docs\superpowers\plans\2026-07-29-content-handoff-workboard-followup.md
git commit -m "Add Content Handoff Workboard follow-up"
git push -u origin feature/p0-webapp-copyfast177-content-handoff-workboard-followup
gh pr create --base main --title "Add Content Handoff Workboard follow-up"
```

- [ ] **Step 5: Merge only after CI passes**

Use the repository quality gate. Verify the merge commit is on `origin/main`; let Railway deploy from `main` rather than sending a separate direct deploy command.
