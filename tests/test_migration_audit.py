"""Tests for the static-only bot-to-web migration auditor."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "migration" / "audit_bot_to_web.py"


def _load_audit_module():
    spec = importlib.util.spec_from_file_location("audit_bot_to_web", SCRIPT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_static_audit_never_imports_source_and_redacts_secret_literals(tmp_path: Path) -> None:
    audit = _load_audit_module()
    bot_root = tmp_path / "bot"
    web_root = tmp_path / "web"
    report_dir = tmp_path / "reports" / "migration"
    docs_dir = tmp_path / "docs" / "migration"
    bot_root.mkdir()
    web_root.mkdir()

    # A source import would raise immediately. The audit must only parse this text.
    (bot_root / "bot.py").write_text(
        """
raise RuntimeError('the static auditor must never execute bot source')
import os

def start_handler():
    return None

app.add_handler(CommandHandler('start', start_handler))
app.add_handler(CallbackQueryHandler(start_handler, pattern='^video:'))
button = InlineKeyboardButton('Video', callback_data='video:create')
token_name = os.getenv('BOT_TOKEN')
source_literal = 'sk-live-super-secret-value-123456789'

fastapi_app = FastAPI()
@fastapi_app.get('/health')
async def health():
    return {'ok': True}
""",
        encoding="utf-8",
    )
    (web_root / "app.py").write_text(
        """
app = FastAPI()
@app.get('/dashboard')
async def dashboard():
    return {'ok': True}
""",
        encoding="utf-8",
    )

    result = audit.run_audit(
        bot_root=bot_root,
        web_root=web_root,
        bot_baseline_sha="b29d0d474974075f4cba963d2c510f49d2d1b3e4",
        report_dir=report_dir,
        docs_dir=docs_dir,
    )

    assert result["bot_inventory"]["counts"]["commands"] == 1
    assert result["bot_inventory"]["commands"][0]["command"] == "start"
    assert result["bot_inventory"]["counts"]["callback_handlers"] == 1
    assert result["bot_inventory"]["counts"]["callback_data"] == 1
    assert result["bot_inventory"]["env_references"][0]["name"] == "BOT_TOKEN"
    assert result["web_inventory"]["routes"][0]["path"] == "/dashboard"
    assert result["parity_gap"]["command_mappings"][0]["status"] == "MAPPED_TO_EXISTING_ROUTE"
    assert result["preflight"]["bot"]["revision"] == {
        "checkout_sha": "",
        "baseline_relation": "not_a_git_worktree",
        "ahead_commits": None,
        "behind_commits": None,
    }
    assert result["preflight"]["bot"]["baseline_bridge_source"] == {
        "path": "webapp_core_bridge.py",
        "state": "baseline_unavailable",
        "present": None,
    }

    serialized = json.dumps(result, ensure_ascii=False)
    assert "sk-live-super-secret-value-123456789" not in serialized
    assert "***REDACTED***" in serialized or "source_literal" not in serialized
    for name in ("preflight.json", "bot_inventory.json", "web_inventory.json", "parity_gap.json"):
        assert (report_dir / name).is_file()
    for name in (
        "README.md",
        "inventory.md",
        "bot-inventory.md",
        "web-inventory.md",
        "parity-matrix.md",
        "route-map.md",
        "state-database-map.md",
        "payos-wallet-jobs.md",
        "admin-map.md",
        "env-provider-map.md",
        "key4u-map.md",
        "known-gaps.md",
    ):
        assert (docs_dir / name).is_file()
    assert "Manual top-up is a Telegram Bot-only handoff" in (docs_dir / "payos-wallet-jobs.md").read_text(encoding="utf-8")
    assert "Manual top-up stays a Bot handoff" in (docs_dir / "PAYOS_WALLET_JOB_MAP.md").read_text(encoding="utf-8")
    assert "BOT_COMPANION_HANDOFF.md" in (docs_dir / "README.md").read_text(encoding="utf-8")
    assert "Bot checkout audited: `unavailable` (`not_a_git_worktree`)" in (docs_dir / "README.md").read_text(encoding="utf-8")


def test_static_audit_records_api_routes_db_env_and_background_signals(tmp_path: Path) -> None:
    audit = _load_audit_module()
    bot_root = tmp_path / "bot"
    web_root = tmp_path / "web"
    bot_root.mkdir()
    web_root.mkdir()
    (bot_root / "bot.py").write_text(
        """
import os
API = os.environ['DEEPGRAM_API_KEY']
c.execute('CREATE TABLE IF NOT EXISTS jobs (id INTEGER)')
c.execute('INSERT INTO jobs VALUES (1)')
asyncio.create_task(run_worker())
fastapi_app = FastAPI()
@fastapi_app.post('/internal/worker/poll')
async def poll():
    return {}
""",
        encoding="utf-8",
    )
    (web_root / "app.py").write_text(
        """
app = FastAPI()
@app.get('/')
async def index():
    return {}
""",
        encoding="utf-8",
    )

    result = audit.run_audit(bot_root, web_root, "baseline", tmp_path / "reports", tmp_path / "docs")

    assert "DEEPGRAM_API_KEY" in {item["name"] for item in result["bot_inventory"]["env_references"]}
    assert "jobs" in result["bot_inventory"]["database_tables"]
    assert "/internal/worker/poll" in {item["path"] for item in result["bot_inventory"]["routes"]}
    assert any(item["kind"] == "create_task" for item in result["bot_inventory"]["background_jobs"])


def test_static_audit_recognizes_guarded_portal_surfaces_and_bot_bridge(tmp_path: Path) -> None:
    audit = _load_audit_module()
    bot_root = tmp_path / "bot"
    web_root = tmp_path / "web"
    bot_root.mkdir()
    web_root.mkdir()
    (bot_root / "bot.py").write_text(
        """
app.add_handler(CommandHandler('video_tier_status', handler))
router = APIRouter()
@router.get('/internal/v1/me')
async def me():
    return {}
""",
        encoding="utf-8",
    )
    (web_root / "app.py").write_text(
        """
app = FastAPI()
@app.get('/{page_path:path}')
async def page(page_path):
    return {}
""",
        encoding="utf-8",
    )

    result = audit.run_audit(bot_root, web_root, "baseline", tmp_path / "reports", tmp_path / "docs")

    assert result["parity_gap"]["command_mappings"][0]["status"] == "COPIED_GUARDED"
    assert result["parity_gap"]["gaps"][1]["area"] == "private_core_bridge"
    assert result["parity_gap"]["gaps"][1]["count"] == 0


def test_static_audit_compares_web_bridge_method_and_path_shapes(tmp_path: Path) -> None:
    """A source-only audit must expose Web calls absent from the Bot contract."""

    audit = _load_audit_module()
    bot_root = tmp_path / "bot"
    web_root = tmp_path / "web"
    bot_root.mkdir()
    web_root.mkdir()
    (bot_root / "bot.py").write_text(
        """
fastapi_app.include_router(build_core_bridge_router(globals()))
""",
        encoding="utf-8",
    )
    (bot_root / "webapp_core_bridge.py").write_text(
        """
router = APIRouter(prefix='/internal/v1')

@router.get('/me')
async def me():
    return {}

@router.post('/features/{feature}/draft')
async def draft():
    return {}
""",
        encoding="utf-8",
    )
    (web_root / "copyfast_api.py").write_text(
        """
async def call(feature, action):
    await _bridge('GET', '/internal/v1/me')
    await _bridge('POST', f'/internal/v1/features/{feature}/{action}')
    await bridge_request('GET', '/internal/v1/not-registered')
""",
        encoding="utf-8",
    )

    result = audit.run_audit(bot_root, web_root, "baseline", tmp_path / "reports", tmp_path / "docs")

    contract = result["parity_gap"]["bridge_contract"]
    assert contract["status"] == "CONTRACT_GAPS_FOUND"
    assert contract["bot_router_mount_observed"] is True
    assert contract["web_request_count"] == 3
    assert contract["matched_request_count"] == 2
    assert contract["unmatched_request_count"] == 1
    assert contract["unmatched_requests"][0]["path"] == "/internal/v1/not-registered"
    bridge_gap = next(item for item in result["parity_gap"]["gaps"] if item["area"] == "private_core_bridge")
    assert bridge_gap["count"] == 1
    assert (tmp_path / "docs" / "BRIDGE_CONTRACT_INVENTORY.md").is_file()


def test_static_audit_tracks_the_directional_telegram_link_callback_contract(tmp_path: Path) -> None:
    audit = _load_audit_module()
    bot_root = tmp_path / "bot"
    web_root = tmp_path / "web"
    bot_root.mkdir()
    web_root.mkdir()
    (bot_root / "bot.py").write_text(
        """
if context.args and str(context.args[0]).startswith("web_"):
    pass
app.add_handler(CommandHandler("linkweb", handler))
""",
        encoding="utf-8",
    )
    (bot_root / "webapp_core_bridge.py").write_text(
        """
def _web_link_callback_headers(callback_url, callback_token, callback_secret, body, request_id, timestamp):
    callback_path = "/api/v1/auth/internal/telegram-link/confirm"
    digest = hashlib.sha256(body).hexdigest()
    material = f"{timestamp}.{request_id}.POST.{callback_path}.{digest}".encode("utf-8")
    signature = hmac.new(callback_secret.encode("utf-8"), material, hashlib.sha256).hexdigest()
    return signature

async def confirm_web_link_from_telegram():
    callback_url = os.environ.get("WEBAPP_LINK_CALLBACK_URL")
    callback_token = os.environ.get("WEBAPP_LINK_CALLBACK_TOKEN")
    callback_secret = os.environ.get("WEBAPP_LINK_CALLBACK_HMAC_SECRET")
    return {
        "X-TOAN-AAS-BRIDGE-TOKEN": callback_token,
        "X-TOAN-AAS-Timestamp": "1",
        "X-TOAN-AAS-Request-ID": "request",
        "X-TOAN-AAS-Signature": "signature",
    }
""",
        encoding="utf-8",
    )
    (web_root / "copyfast_auth.py").write_text(
        """
def _bridge_callback_authorized(request):
    token = request.headers.get("X-TOAN-AAS-BRIDGE-TOKEN")
    timestamp = request.headers.get("X-TOAN-AAS-Timestamp")
    request_id = request.headers.get("X-TOAN-AAS-Request-ID")
    signature = request.headers.get("X-TOAN-AAS-Signature")
    body = request.body
    digest = hashlib.sha256(body).hexdigest()
    material = f"{timestamp}.{request_id}.{request.method.upper()}.{request.url.path}.{digest}".encode("utf-8")
    expected = hmac.new(secret.encode("utf-8"), material, hashlib.sha256).hexdigest()
    return token and timestamp and request_id and signature and expected

@router.post("/internal/telegram-link/confirm")
async def callback():
    return {"error_code": "TELEGRAM_BROWSER_INPUT_NOT_ACCEPTED"}
""",
        encoding="utf-8",
    )
    (web_root / "app.py").write_text('app.include_router(copyfast_auth.router, prefix="/api/v1/auth")', encoding="utf-8")

    contract = audit._telegram_link_callback_contract(bot_root, web_root)

    assert contract["status"] == "STATIC_CALLBACK_CONTRACT_PRESENT"
    assert contract["expected_web_callback_path"] == "/api/v1/auth/internal/telegram-link/confirm"
    assert contract["bot"]["fallback_link_command_observed"] is True
    assert contract["bot"]["callback_signature_shape_observed"] is True
    assert contract["web"]["callback_signature_shape_observed"] is True
    assert contract["web"]["raw_browser_id_rejection_observed"] is True


def test_static_audit_rejects_a_telegram_callback_contract_with_only_matching_headers(tmp_path: Path) -> None:
    """Header names alone must not be treated as a valid cross-service HMAC contract."""
    audit = _load_audit_module()
    bot_root = tmp_path / "bot"
    web_root = tmp_path / "web"
    bot_root.mkdir()
    web_root.mkdir()
    (bot_root / "bot.py").write_text(
        'if context.args and str(context.args[0]).startswith("web_"):\n    pass\napp.add_handler(CommandHandler("linkweb", handler))',
        encoding="utf-8",
    )
    (bot_root / "webapp_core_bridge.py").write_text(
        '''
async def confirm_web_link_from_telegram():
    callback_url = os.environ.get("WEBAPP_LINK_CALLBACK_URL")
    callback_token = os.environ.get("WEBAPP_LINK_CALLBACK_TOKEN")
    callback_secret = os.environ.get("WEBAPP_LINK_CALLBACK_HMAC_SECRET")
    return {"X-TOAN-AAS-BRIDGE-TOKEN": callback_token, "X-TOAN-AAS-Timestamp": "1", "X-TOAN-AAS-Request-ID": "request", "X-TOAN-AAS-Signature": "signature"}
''',
        encoding="utf-8",
    )
    (web_root / "copyfast_auth.py").write_text(
        '''
def _bridge_callback_authorized(request):
    return request.headers.get("X-TOAN-AAS-BRIDGE-TOKEN") and request.headers.get("X-TOAN-AAS-Timestamp") and request.headers.get("X-TOAN-AAS-Request-ID") and request.headers.get("X-TOAN-AAS-Signature")
@router.post("/internal/telegram-link/confirm")
async def callback():
    return {"error_code": "TELEGRAM_BROWSER_INPUT_NOT_ACCEPTED"}
''',
        encoding="utf-8",
    )
    (web_root / "app.py").write_text('app.include_router(copyfast_auth.router, prefix="/api/v1/auth")', encoding="utf-8")

    contract = audit._telegram_link_callback_contract(bot_root, web_root)

    assert contract["status"] == "CALLBACK_CONTRACT_GAPS_FOUND"
    assert contract["bot"]["callback_signature_shape_observed"] is False
    assert contract["web"]["callback_signature_shape_observed"] is False


def test_static_audit_does_not_treat_an_unmounted_legacy_web_route_as_deployed(tmp_path: Path) -> None:
    audit = _load_audit_module()
    bot_root = tmp_path / "bot"
    web_root = tmp_path / "web"
    bot_root.mkdir()
    web_root.mkdir()
    (bot_root / "bot.py").write_text("app.add_handler(CommandHandler('status', handler))", encoding="utf-8")
    (web_root / "app.py").write_text(
        """
app = FastAPI()
@app.get('/{page_path:path}')
async def page(page_path):
    return {}
""",
        encoding="utf-8",
    )
    (web_root / "legacy_control.py").write_text(
        """
router = APIRouter()
@router.get('/status')
async def status():
    return {}
""",
        encoding="utf-8",
    )

    result = audit.run_audit(bot_root, web_root, "baseline", tmp_path / "reports", tmp_path / "docs")

    mapped = result["parity_gap"]["command_mappings"][0]
    assert mapped["target"] == "/status"
    assert mapped["status"] == "COPIED_GUARDED"


def test_static_audit_classifies_neutrally_named_handlers_with_an_admin_guard_as_admin(tmp_path: Path) -> None:
    audit = _load_audit_module()
    bot_root = tmp_path / "bot"
    web_root = tmp_path / "web"
    bot_root.mkdir()
    web_root.mkdir()
    (bot_root / "bot.py").write_text(
        """
async def cmd_grant_combo(update, context):
    if not is_admin_user(update.effective_user.id):
        return None
    return None

app.add_handler(CommandHandler('grant_combo', cmd_grant_combo))
""",
        encoding="utf-8",
    )
    (web_root / "app.py").write_text(
        """
app = FastAPI()
@app.get('/{page_path:path}')
async def page(page_path):
    return {}
""",
        encoding="utf-8",
    )

    result = audit.run_audit(bot_root, web_root, "baseline", tmp_path / "reports", tmp_path / "docs")

    mapped = result["parity_gap"]["command_mappings"][0]
    assert mapped["classification"] == "admin"
    assert mapped["target"] == "/admin/grant_combo"
    assert mapped["status"] == "COPIED_GUARDED"


def test_static_admin_guard_analysis_follows_a_direct_guarded_command_alias() -> None:
    audit = _load_audit_module()
    handlers = audit._static_admin_guarded_handlers(
        """
async def cmd_admin_report(update, context):
    if not is_admin_user(update.effective_user.id):
        return None
    return None

async def cmd_billing_report(update, context):
    return await cmd_admin_report(update, context)

async def send_ai_admin_report(update, period):
    if not is_admin_user(update.effective_user.id):
        return None
    return None

async def cmd_report_ai_today(update, context):
    return await send_ai_admin_report(update, "today")

async def send_report_chart(update, period):
    if not is_admin_user(update.effective_user.id):
        return None
    return None

async def cmd_report_chart_today(update, context):
    return await send_report_chart(update, "today")

async def cmd_owner_only(update, context):
    if not is_admin_or_owner(update.effective_user.id):
        return None
    return None

async def cmd_fixed_admin(update, context):
    if str(update.effective_user.id) != ADMIN_ID:
        return None
    return None
"""
    )
    assert "cmd_admin_report" in handlers
    assert "cmd_billing_report" in handlers
    assert "cmd_report_ai_today" in handlers
    assert "cmd_report_chart_today" in handlers
    assert "cmd_owner_only" in handlers
    assert "cmd_fixed_admin" in handlers


def test_static_audit_excludes_clearly_named_bot_drafts_from_canonical_command_counts(tmp_path: Path) -> None:
    audit = _load_audit_module()
    bot_root = tmp_path / "bot"
    web_root = tmp_path / "web"
    bot_root.mkdir()
    web_root.mkdir()
    (bot_root / "bot.py").write_text("app.add_handler(CommandHandler('canonical', handler))", encoding="utf-8")
    (bot_root / "nháp 2.py").write_text("app.add_handler(CommandHandler('stale_draft', handler))", encoding="utf-8")
    (web_root / "app.py").write_text("app = FastAPI()", encoding="utf-8")

    result = audit.run_audit(bot_root, web_root, "baseline", tmp_path / "reports", tmp_path / "docs")

    assert [item["command"] for item in result["bot_inventory"]["commands"]] == ["canonical"]
    assert result["bot_inventory"]["excluded_noncanonical_source_files"] == ["nháp 2.py"]
    assert "Excluded clearly named Bot drafts" in (tmp_path / "docs" / "bot-inventory.md").read_text(encoding="utf-8")


def test_static_audit_routes_personal_bot_commands_to_distinct_companion_surfaces() -> None:
    audit = _load_audit_module()
    routes = {"/{page_path:path}"}
    expected = {
        "notes": "/notes",
        "reminders": "/reminders",
        "referral": "/referrals",
        "gift": "/rewards",
        "community": "/community",
        "guide": "/guides",
        "growth_ai": "/growth/ai",
        "campaign_report": "/campaign/report",
    }
    for command, target in expected.items():
        mapped = audit._map_command({"command": command, "handler": f"cmd_{command}", "file": "bot.py", "line": 1}, routes)
        assert mapped["target"] == target
        assert mapped["status"] == "COPIED_GUARDED"


def test_static_audit_routes_customer_hubs_to_specific_web_surfaces() -> None:
    audit = _load_audit_module()
    routes = {"/{page_path:path}"}
    expected = {
        "buy_plan": "/membership",
        "vip": "/membership",
        "trial_status": "/membership",
        "tools": "/tools",
        "ai_models": "/tools",
        "status": "/status",
        "telegram_status": "/status",
        "create_media": "/studio",
        "creative_flow": "/studio",
        "media_factory": "/studio",
        "growth_ai": "/growth/ai",
        "campaign_report": "/campaign/report",
    }
    for command, target in expected.items():
        mapped = audit._map_command({"command": command, "handler": f"cmd_{command}", "file": "bot.py", "line": 1}, routes)
        assert mapped["target"] == target
        assert mapped["status"] == "COPIED_GUARDED"


def test_static_audit_routes_customer_payment_support_policy_and_link_commands_to_safe_web_surfaces() -> None:
    audit = _load_audit_module()
    routes = {"/{page_path:path}"}
    expected = {
        "thucong": "/wallet/topup",
        "gopy": "/support",
        "source_help": "/guides",
        "linkweb": "/onboarding",
        "mode": "/account",
        "toanaas_hub": "/community",
        "uudai": "/rewards",
        "ads_policy": "/legal",
        "cancel": "/jobs",
    }
    for command, target in expected.items():
        mapped = audit._map_command({"command": command, "handler": f"cmd_{command}", "file": "bot.py", "line": 1}, routes)
        assert mapped["target"] == target
        assert mapped["status"] == "COPIED_GUARDED"
