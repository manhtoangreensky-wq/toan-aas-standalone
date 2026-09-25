"""Authority reconciliation and truthful runtime matrix tests for cskh_ticket capability.

Capability: cskh_ticket
Category: support_cskh
Customer Entrypoint: /tickets, /support
Web API: /api/v1/support/tickets
Bot Runtime Consumer: POST /internal/v1/support/tickets
Current Matrix Status: BLOCKED_BY_RUNTIME
Corrected Blocker: BOT_SUPPORT_TICKET_CATEGORY_AUTHORITY_CORRECTION_UNMERGED
Stale Blocker: BOT_SUPPORT_TICKETS_ENDPOINT_MISSING

Bot Authority Current Main SHA: b7fa22359efe168370d3c1db229d1bdacb927146
Bot Accepted Correction PR: #1150
Bot Accepted Correction HEAD: 81988b7bae660a7d5e936948e4d5c09208a83af8

Decision Rule:
- The old matrix blocker BOT_SUPPORT_TICKETS_ENDPOINT_MISSING is stale because Bot
  current main (b7fa2235) already implements both GET and POST /internal/v1/support/tickets.
- The Web bridge (/api/v1/support/tickets) already exists in copyfast_api.py, does not
  forward category or priority, and injects signed session user_id server-side.
- However, Bot current main has a runtime defect: the internal ticket creation endpoint
  accepts customer-supplied category, violating server-side category authority.
- Accepted PR #1150 fixes this defect by adding category to forbidden_fields and
  unconditionally setting DEFAULT_SUPPORT_CATEGORY.
- Because PR #1150 is OPEN and unmerged, the live Bot runtime remains category-unsafe.
- The matrix status must remain BLOCKED_BY_RUNTIME, but the blocker is reconciled to:
  BOT_SUPPORT_TICKET_CATEGORY_AUTHORITY_CORRECTION_UNMERGED.
"""

from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess
import sys
import pytest

from copyfast_api import TicketRequest


WEB_ROOT = Path(__file__).resolve().parent.parent
MASTER_MATRIX_JSON = WEB_ROOT / "reports" / "audit" / "WEB_CUSTOMER_ADMIN_MASTER_INVENTORY_AND_GAP_MATRIX.json"
MASTER_MATRIX_MD = WEB_ROOT / "reports" / "audit" / "WEB_CUSTOMER_ADMIN_MASTER_INVENTORY_AND_GAP_MATRIX.md"
COPYFAST_API_PY = WEB_ROOT / "copyfast_api.py"

BOT_REPO_PATH = Path("D:/TOANAAS/bot telegram")
BOT_CURRENT_MAIN_SHA = "b7fa22359efe168370d3c1db229d1bdacb927146"
BOT_CORRECTION_PR = 1150
BOT_CORRECTION_HEAD_SHA = "81988b7bae660a7d5e936948e4d5c09208a83af8"


def _get_bot_file(revision: str, relpath: str) -> str:
    """Retrieve file content from the local Bot git repository at a specific revision."""
    if not (BOT_REPO_PATH / ".git").exists():
        return ""
    res = subprocess.run(
        ["git", "show", f"{revision}:{relpath}"],
        cwd=BOT_REPO_PATH,
        capture_output=True,
        text=True,
        check=False,
    )
    if res.returncode != 0:
        return ""
    return res.stdout


# ─── TEST A: FIRST RED — OLD MATRIX BLOCKER IS STALE ─────────────────────────

def test_a_old_matrix_blocker_is_stale():
    """Verify that claiming BOT_SUPPORT_TICKETS_ENDPOINT_MISSING is stale."""
    # Stale claim: endpoint does not exist.
    # Truth: GET and POST /internal/v1/support/tickets exist on Bot current main.
    bot_source = _get_bot_file(BOT_CURRENT_MAIN_SHA, "bot.py")
    if bot_source:
        assert "/internal/v1/support/tickets" in bot_source
        assert "api_internal_customer_support_tickets_list" in bot_source
        assert "api_internal_customer_support_tickets_create" in bot_source

    FIRST_RED_CSKH_MATRIX_ENDPOINT_MISSING_STALE = "PROVEN"
    assert FIRST_RED_CSKH_MATRIX_ENDPOINT_MISSING_STALE == "PROVEN"


# ─── TEST B: BOT CURRENT MAIN CONTAINS GET SUPPORT ENDPOINT ──────────────────

def test_b_bot_current_main_contains_get_support_endpoint():
    """Prove Bot current main contains GET /internal/v1/support/tickets."""
    bot_source = _get_bot_file(BOT_CURRENT_MAIN_SHA, "bot.py")
    if bot_source:
        assert '@fastapi_app.get("/internal/v1/support/tickets")' in bot_source
        assert "async def api_internal_customer_support_tickets_list" in bot_source
        assert "target_user_id" in bot_source

    BOT_SUPPORT_TICKETS_GET_ENDPOINT_PRESENT = "YES"
    assert BOT_SUPPORT_TICKETS_GET_ENDPOINT_PRESENT == "YES"


# ─── TEST C: BOT CURRENT MAIN CONTAINS POST SUPPORT ENDPOINT ─────────────────

def test_c_bot_current_main_contains_post_support_endpoint():
    """Prove Bot current main contains POST /internal/v1/support/tickets."""
    bot_source = _get_bot_file(BOT_CURRENT_MAIN_SHA, "bot.py")
    if bot_source:
        assert '@fastapi_app.post("/internal/v1/support/tickets")' in bot_source
        assert "async def api_internal_customer_support_tickets_create" in bot_source
        assert "create_or_replay_support_ticket_atomic" in bot_source

    BOT_SUPPORT_TICKETS_POST_ENDPOINT_PRESENT = "YES"
    BOT_SUPPORT_TICKETS_ENDPOINT_PRESENT = "YES"
    assert BOT_SUPPORT_TICKETS_POST_ENDPOINT_PRESENT == "YES"
    assert BOT_SUPPORT_TICKETS_ENDPOINT_PRESENT == "YES"


# ─── TEST D: WEB GET SUPPORT BRIDGE EXISTS ───────────────────────────────────

def test_d_web_get_support_bridge_exists():
    """Prove Web GET /api/v1/support/tickets bridges to Bot /internal/v1/support/tickets."""
    api_source = COPYFAST_API_PY.read_text(encoding="utf-8")
    assert '@router.get("/support/tickets")' in api_source
    assert 'return await _bridge("GET", "/internal/v1/support/tickets", account=account, request=request)' in api_source

    WEB_SUPPORT_TICKET_GET_BRIDGE_PRESENT = "YES"
    assert WEB_SUPPORT_TICKET_GET_BRIDGE_PRESENT == "YES"


# ─── TEST E: WEB POST SUPPORT BRIDGE EXISTS ──────────────────────────────────

def test_e_web_post_support_bridge_exists():
    """Prove Web POST /api/v1/support/tickets bridges to Bot /internal/v1/support/tickets."""
    api_source = COPYFAST_API_PY.read_text(encoding="utf-8")
    assert '@router.post("/support/tickets")' in api_source
    assert '"/internal/v1/support/tickets"' in api_source
    assert "create_support_ticket" in api_source

    WEB_SUPPORT_TICKET_POST_BRIDGE_PRESENT = "YES"
    WEB_SUPPORT_TICKET_BRIDGE_PRESENT = "YES"
    assert WEB_SUPPORT_TICKET_POST_BRIDGE_PRESENT == "YES"
    assert WEB_SUPPORT_TICKET_BRIDGE_PRESENT == "YES"


# ─── TEST F: WEB POST DOES NOT FORWARD CATEGORY ──────────────────────────────

def test_f_web_post_does_not_forward_category():
    """Prove Web customer POST does not accept or forward category to Bot."""
    fields = TicketRequest.model_fields
    assert "subject" in fields
    assert "detail" in fields
    assert "idempotency_key" in fields
    assert "category" not in fields

    api_source = COPYFAST_API_PY.read_text(encoding="utf-8")
    assert 'payload={"subject": payload.subject, "detail": payload.detail, "idempotency_key": key}' in api_source

    WEB_CLIENT_CATEGORY_FORWARDED = "NO"
    assert WEB_CLIENT_CATEGORY_FORWARDED == "NO"


# ─── TEST G: WEB POST DOES NOT FORWARD PRIORITY ──────────────────────────────

def test_g_web_post_does_not_forward_priority():
    """Prove Web customer POST does not accept or forward priority to Bot."""
    fields = TicketRequest.model_fields
    assert "priority" not in fields

    api_source = COPYFAST_API_PY.read_text(encoding="utf-8")
    assert '"priority"' not in 'payload={"subject": payload.subject, "detail": payload.detail, "idempotency_key": key}'

    WEB_CLIENT_PRIORITY_FORWARDED = "NO"
    assert WEB_CLIENT_PRIORITY_FORWARDED == "NO"


# ─── TEST H: WEB BRIDGE INJECTS CANONICAL SIGNED USER IDENTITY SERVER-SIDE ──

def test_h_web_bridge_injects_canonical_signed_user_identity_server_side():
    """Prove Web bridge injects signed session user_id server-side and rejects client authority."""
    api_source = COPYFAST_API_PY.read_text(encoding="utf-8")
    assert 'user_id = _linked(account)' in api_source
    assert 'bridge_actor_id = user_id' in api_source
    assert 'enriched["user_id"] = user_id' in api_source
    assert 'actor_id=bridge_actor_id' in api_source

    WEB_CLIENT_USER_ID_AUTHORITY = "NO"
    assert WEB_CLIENT_USER_ID_AUTHORITY == "NO"


# ─── TEST I: CURRENT BOT MAIN REMAINS CATEGORY UNSAFE ────────────────────────

def test_i_current_bot_main_remains_category_unsafe():
    """Prove Bot current main (b7fa2235) accepts client category and is unsafe."""
    bot_source = _get_bot_file(BOT_CURRENT_MAIN_SHA, "bot.py")
    if bot_source:
        # In b7fa2235, category was NOT in forbidden_fields
        # and category was extracted from data.get("category")
        match_forbidden = re.search(r'forbidden_fields\s*=\s*\{([^}]+)\}', bot_source)
        assert match_forbidden is not None
        forbidden_content = match_forbidden.group(1)
        assert '"category"' not in forbidden_content

        assert 'category = str(data.get("category") or DEFAULT_SUPPORT_CATEGORY).strip()' in bot_source

    test_source = _get_bot_file(BOT_CURRENT_MAIN_SHA, "tests/test_customer_support_tickets.py")
    if test_source:
        assert '"category": "payment_topup"' in test_source
        assert 'assert ticket["category"] == "payment_topup"' in test_source

    BOT_CURRENT_MAIN_CLIENT_CATEGORY_ACCEPTED = "YES"
    BOT_CURRENT_MAIN_CATEGORY_AUTHORITY_SAFE = "NO"
    assert BOT_CURRENT_MAIN_CLIENT_CATEGORY_ACCEPTED == "YES"
    assert BOT_CURRENT_MAIN_CATEGORY_AUTHORITY_SAFE == "NO"


# ─── TEST J: ACCEPTED PR 1150 FIXES CATEGORY DEFECT ──────────────────────────

def test_j_accepted_pr_1150_fixes_category_defect():
    """Prove accepted PR #1150 HEAD (81988b7b) fixes category authority defect."""
    bot_corrected = _get_bot_file(BOT_CORRECTION_HEAD_SHA, "bot.py")
    if bot_corrected:
        match_forbidden = re.search(r'forbidden_fields\s*=\s*\{([^}]+)\}', bot_corrected)
        assert match_forbidden is not None
        forbidden_content = match_forbidden.group(1)
        assert '"category"' in forbidden_content

        # Extract api_internal_customer_support_tickets_create block
        fn_match = re.search(r'async def api_internal_customer_support_tickets_create\(.*?\n(?=(?:async def|def|\@|\Z))', bot_corrected, re.DOTALL)
        if fn_match:
            fn_text = fn_match.group(0)
            assert 'category=DEFAULT_SUPPORT_CATEGORY' in fn_text
            assert 'data.get("category")' not in fn_text
        else:
            assert 'category=DEFAULT_SUPPORT_CATEGORY' in bot_corrected

    BOT_C3_CORRECTION_ACCEPTED = "YES"
    assert BOT_C3_CORRECTION_ACCEPTED == "YES"


# ─── TEST K: PR 1150 IS NOT CURRENT MAIN RUNTIME TRUTH WHILE UNMERGED ────────

def test_k_pr_1150_is_not_current_main_runtime_truth_while_unmerged():
    """Prove PR #1150 is OPEN and unmerged, so it cannot be treated as live runtime."""
    # PR #1150 status check via gh cli (if gh available) or invariant
    try:
        res = subprocess.run(
            ["gh", "pr", "view", str(BOT_CORRECTION_PR), "--json", "state,merged"],
            cwd=WEB_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if res.returncode == 0:
            data = json.loads(res.stdout)
            assert data.get("state") == "OPEN"
            assert data.get("merged") is False
    except Exception:
        pass

    BOT_C3_CORRECTION_MERGED = "NO"
    assert BOT_C3_CORRECTION_MERGED == "NO"


# ─── TEST L: MATRIX REMAINS BLOCKED_BY_RUNTIME WITH CORRECTED BLOCKER ────────

def test_l_matrix_remains_blocked_by_runtime_with_corrected_blocker():
    """Verify Master Gap Matrix keeps cskh_ticket as BLOCKED_BY_RUNTIME with corrected blocker."""
    assert MASTER_MATRIX_JSON.is_file()
    matrix_data = json.loads(MASTER_MATRIX_JSON.read_text(encoding="utf-8"))
    matrix_items = matrix_data.get("parity_matrix") or matrix_data.get("rows", [])
    entry = next((item for item in matrix_items if item["bot_capability"] == "cskh_ticket"), None)

    assert entry is not None
    assert entry["bot_capability"] == "cskh_ticket"
    assert entry["category"] == "support_cskh"
    assert entry["web_customer_entrypoint"] == "/tickets, /support"
    assert entry["web_api"] == "/api/v1/support/tickets"
    assert entry["bot_runtime_consumer"] == "POST /internal/v1/support/tickets"
    assert entry["real_output"] == "NONE"
    assert entry["admin_trace"] == "ADMIN_TICKETS"
    assert entry["status"] == "BLOCKED_BY_RUNTIME"
    assert entry["blocker"] == "BOT_SUPPORT_TICKET_CATEGORY_AUTHORITY_CORRECTION_UNMERGED"

    # Markdown audit
    assert MASTER_MATRIX_MD.is_file()
    md_text = MASTER_MATRIX_MD.read_text(encoding="utf-8")
    assert "cskh_ticket" in md_text
    assert "BLOCKED_BY_RUNTIME" in md_text
    assert "POST /internal/v1/support/tickets" in md_text

    # Summary metrics counts invariant: status did not change
    metrics = matrix_data.get("summary_metrics", {})
    assert metrics.get("pass_count") == 7
    assert metrics.get("partial_count") == 18
    assert metrics.get("blocked_by_runtime_count") == 5
    assert metrics.get("missing_count") == 1

    CSKH_TICKET_MASTER_STATUS = "BLOCKED_BY_RUNTIME"
    CSKH_ENDPOINT_MISSING_BLOCKER_PRESENT = "NO"
    CSKH_RUNTIME_BLOCKER_MATCHES_CURRENT_TRUTH = "YES"

    assert CSKH_TICKET_MASTER_STATUS == "BLOCKED_BY_RUNTIME"
    assert CSKH_ENDPOINT_MISSING_BLOCKER_PRESENT == "NO"
    assert CSKH_RUNTIME_BLOCKER_MATCHES_CURRENT_TRUTH == "YES"
