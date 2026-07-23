"""Tests for the static-only bot-to-web migration auditor."""

from __future__ import annotations

import importlib.util
import json
import subprocess
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
    assert result["parity_gap"]["command_mappings"][0]["status"] == "NAVIGATION_ENTRYPOINT"
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
        "FALLBACK_FEATURE_DISPOSITION.md",
        "CALLBACK_HANDLER_DISPATCH_MAP.md",
        "UNREFERENCED_STATIC_MODULES.md",
        "PAYOS_ALERT_CALLBACK_CONTRACT.md",
        "BILLING_MENU_CALLBACK_CONTRACT.md",
        "PACKAGE_PURCHASE_CALLBACK_CONTRACT.md",
        "MEDIA_CREATOR_CALLBACK_CONTRACT.md",
        "QUICK_IMAGE_PLANNER_CALLBACK_CONTRACT.md",
        "SHOPAI_CALLBACK_CONTRACT.md",
        "SHOPAI_VIDEO_JOB_CALLBACK_CONTRACT.md",
        "MANUAL_PAYMENT_CALLBACK_CONTRACT.md",
        "PROVIDER_CHOICE_CALLBACK_CONTRACT.md",
        "CREATIVE_MOTION_GUIDE_CALLBACK_CONTRACT.md",
        "VIDEO_JOB_CALLBACK_CONTRACT.md",
        "VIDEO_FINALIZATION_CALLBACK_CONTRACT.md",
        "STORAGE_ADDON_CALLBACK_CONTRACT.md",
    ):
        assert (docs_dir / name).is_file()
    assert "Manual top-up is a Telegram Bot-only handoff" in (docs_dir / "payos-wallet-jobs.md").read_text(encoding="utf-8")
    assert "Manual top-up stays a Bot handoff" in (docs_dir / "PAYOS_WALLET_JOB_MAP.md").read_text(encoding="utf-8")
    readme = (docs_dir / "README.md").read_text(encoding="utf-8")
    assert "BOT_COMPANION_HANDOFF.md" in readme
    assert "UNREFERENCED_STATIC_MODULES.md" in readme
    assert "BILLING_MENU_CALLBACK_CONTRACT.md" in readme
    assert "SHOPAI_CALLBACK_CONTRACT.md" in readme
    assert "SHOPAI_VIDEO_JOB_CALLBACK_CONTRACT.md" in readme
    assert "MANUAL_PAYMENT_CALLBACK_CONTRACT.md" in readme
    assert "PROVIDER_CHOICE_CALLBACK_CONTRACT.md" in readme
    assert "CREATIVE_MOTION_GUIDE_CALLBACK_CONTRACT.md" in readme
    # These are deliberate project-wide contracts, not a claim that the tiny
    # fixture executes any media feature.  The generated migration index must
    # keep their discoverability on every audit run instead of silently
    # dropping the guard docs after a source inventory refresh.
    for marker in (
        "SUBTITLE_ASSET_OPERATIONS_CONTRACT.md",
        "VIDEO_POSTER_OPERATION_CONTRACT.md",
        "ADMIN_INTERNAL_DOCUMENT_ARCHIVE_CONTRACT.md",
    ):
        assert marker in readme
    assert "Additive Web-native route (not a Telegram command mapping)" in (docs_dir / "route-map.md").read_text(encoding="utf-8")
    assert "Additive Web-native Video Poster state" in (docs_dir / "state-database-map.md").read_text(encoding="utf-8")
    assert "Web-native Video Poster environment names" in (docs_dir / "env-provider-map.md").read_text(encoding="utf-8")
    assert "Additive Web-native guard: Video Poster Lab" in (docs_dir / "known-gaps.md").read_text(encoding="utf-8")
    assert "Additive Web-native guard: Video Poster Lab" in (docs_dir / "KNOWN_GAPS_AND_GUARDS.md").read_text(encoding="utf-8")
    assert "Bot source audited: working-tree fallback `unavailable` (`not_a_git_worktree`)" in (docs_dir / "README.md").read_text(encoding="utf-8")
    # The generated compatibility map must preserve the three Web authority
    # domains.  A later static audit must not silently reduce it to a generic
    # "admin" list and thereby suggest that browser navigation grants Bot
    # canonical authority.
    erp_map = (docs_dir / "ADMIN_ERP_MAP.md").read_text(encoding="utf-8")
    for marker in (
        "## Authority model",
        "Canonical Bot admin",
        "Web Support Desk",
        "Web CRM manager",
        "WEBAPP_ADMIN_ERP_ENABLED",
        "Compatibility target",
    ):
        assert marker in erp_map


def test_static_audit_uses_requested_git_baseline_snapshot_not_dirty_worktree(tmp_path: Path) -> None:
    """A requested Git SHA must be the only Bot source evidence for the audit."""

    audit = _load_audit_module()
    bot_root = tmp_path / "bot"
    web_root = tmp_path / "web"
    bot_root.mkdir()
    web_root.mkdir()

    def git(*args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", "-C", str(bot_root), *args],
            check=True,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
        )

    (bot_root / "bot.py").write_text(
        """
def baseline_handler():
    return None

application.add_handler(CommandHandler('baseline_only', baseline_handler))
""",
        encoding="utf-8",
    )
    git("init")
    git("add", "bot.py")
    git("-c", "user.name=Static audit fixture", "-c", "user.email=audit@example.invalid", "commit", "-m", "baseline")
    baseline_sha = git("rev-parse", "HEAD").stdout.strip()

    # This source exists only in the dirty checkout.  If the audit ever walks
    # the supplied worktree instead of the committed snapshot, it will leak
    # into the command inventory below.
    (bot_root / "bot.py").write_text(
        """
def baseline_handler():
    return None

application.add_handler(CommandHandler('baseline_only', baseline_handler))
application.add_handler(CommandHandler('dirty_worktree_only', baseline_handler))
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
        bot_root,
        web_root,
        baseline_sha,
        tmp_path / "reports",
        tmp_path / "docs",
    )

    assert {item["command"] for item in result["bot_inventory"]["commands"]} == {"baseline_only"}
    assert "dirty_worktree_only" not in json.dumps(result["bot_inventory"], ensure_ascii=False)
    assert result["preflight"]["bot"]["audit_source"] == {
        "mode": "git_baseline_snapshot",
        "reason": "requested_baseline_materialized_static_only",
        "revision": baseline_sha,
        "files_materialized": 1,
    }
    assert result["preflight"]["bot"]["revision"] == {
        "checkout_sha": baseline_sha,
        "baseline_relation": "exact",
        "ahead_commits": 0,
        "behind_commits": 0,
    }
    readme = (tmp_path / "docs" / "README.md").read_text(encoding="utf-8")
    assert f"Bot source audited: static Git baseline snapshot `{baseline_sha}`" in readme
    assert "working tree not used as source evidence" in readme


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
    bridge_gap = next(item for item in result["parity_gap"]["gaps"] if item["area"] == "private_core_bridge")
    assert bridge_gap["count"] == 0


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


def test_static_audit_does_not_expose_a_raw_document_operation_api_as_a_command_route(tmp_path: Path) -> None:
    """A Bot command opens the safe Web page, never a write-capable raw API."""

    audit = _load_audit_module()
    bot_root = tmp_path / "bot"
    web_root = tmp_path / "web"
    bot_root.mkdir()
    web_root.mkdir()
    (bot_root / "bot.py").write_text("app.add_handler(CommandHandler('ocr_pdf', handler))", encoding="utf-8")
    (web_root / "app.py").write_text(
        """
app = FastAPI()
app.include_router(document_ops.router)
@app.get('/documents/pdf-ocr')
async def pdf_ocr_page():
    return {}
""",
        encoding="utf-8",
    )
    (web_root / "document_ops.py").write_text(
        """
router = APIRouter(prefix='/api/v1/document-operations')
@router.post('/ocr-pdf')
async def ocr_pdf():
    return {}
""",
        encoding="utf-8",
    )

    result = audit.run_audit(bot_root, web_root, "baseline", tmp_path / "reports", tmp_path / "docs")

    mapped = result["parity_gap"]["command_mappings"][0]
    assert mapped["target"] == "/documents/pdf-ocr"
    assert mapped["status"] == "NAVIGATION_ONLY"
    assert mapped["resolution"] == "reviewed_document_fresh_web_navigation"
    assert mapped["document_capability_key"] == "documents_pdf_ocr"
    assert "/api/v1/document-operations/ocr-pdf" not in mapped["target"]


def test_static_audit_maps_only_reviewed_document_commands_to_fresh_web_navigation() -> None:
    """Document entrypoints never carry Bot files, choices or execution state."""

    audit = _load_audit_module()
    routes = {"/{page_path:path}"}
    expected = {
        "doc_tools": ("/documents", "documents", "documents", "document_directory"),
        "pdf_to_word": ("/documents/pdf-to-word", "documents_pdf_to_word", "documents_pdf_to_word", "pdf_to_word"),
        "compress_pdf": ("/documents/compress", "documents_compress", "documents_compress", "pdf_optimize"),
        "split_pdf": ("/documents/split", "documents_split", "documents_split", "pdf_split"),
        "merge_pdf": ("/documents/merge", "documents_merge", "documents_merge", "pdf_merge"),
        "image_to_pdf": ("/documents/image-to-pdf", "documents_image_to_pdf", "documents_image_to_pdf", "image_to_pdf"),
        "ocr_pdf": ("/documents/pdf-ocr", "documents_pdf_ocr", "documents_pdf_ocr", "pdf_ocr"),
    }

    for command, (target, capability, feature, surface) in expected.items():
        mapped = audit._map_command(
            {"command": command, "handler": "customer_handler", "file": "bot.py", "line": 1},
            routes,
        )
        assert mapped["classification"] == "customer"
        assert mapped["target"] == target
        assert mapped["status"] == "NAVIGATION_ONLY"
        assert mapped["resolution"] == "reviewed_document_fresh_web_navigation"
        assert mapped["source_dispositions"] == audit.DOCUMENT_FRESH_WEB_NAVIGATION_DISPOSITIONS
        assert mapped["document_capability_key"] == capability
        assert mapped["document_feature_key"] == feature
        assert mapped["document_surface"] == surface
        assert mapped["document_authority"] == "SIGNED_CUSTOMER_WEB_NATIVE"
        assert mapped["document_launch_mode"] == "WEB_NAVIGATION"

    for command in ("translate_file", "pdf_to_images", "ocr_image"):
        mapped = audit._map_command(
            {"command": command, "handler": "customer_handler", "file": "bot.py", "line": 1},
            routes,
        )
        assert "document_capability_key" not in mapped


def test_static_audit_keeps_interface_locale_navigation_closed_to_reviewed_web_catalogs() -> None:
    """Bot language menus open a fresh signed navigator, never a locale write."""

    audit = _load_audit_module()
    routes = {"/{page_path:path}"}
    evidence = {"file": "bot.py", "line": 1}

    for command in sorted(audit.INTERFACE_LOCALE_FRESH_WEB_NAVIGATION_COMMANDS):
        mapped = audit._map_command(
            {"command": command, "handler": "customer_handler", "file": "bot.py", "line": 1},
            routes,
        )
        assert mapped["classification"] == "customer"
        assert mapped["target"] == audit.INTERFACE_LOCALE_NAVIGATOR_ROUTE
        assert mapped["status"] == "NAVIGATION_ONLY"
        assert mapped["resolution"] == "reviewed_interface_locale_fresh_web_navigation"
        assert mapped["source_dispositions"] == audit.INTERFACE_LOCALE_FRESH_WEB_NAVIGATION_DISPOSITIONS
        assert mapped["interface_locale_authority"] == "SIGNED_CUSTOMER_WEB_PROFILE"
        assert mapped["interface_locale_launch_mode"] == "WEB_NAVIGATION"
        assert mapped["interface_locale_route"] == audit.INTERFACE_LOCALE_NAVIGATOR_ROUTE
        assert mapped["interface_locale_feature_key"] == "interface_locale_navigator"
        assert mapped["interface_locale_supported_values"] == ("vi", "en", "zh")

    for token in sorted(audit.INTERFACE_LOCALE_WEB_SUPPORTED_ACTIONS):
        mapped = audit._map_callback(token, "callback_data", evidence, routes)
        assert mapped["classification"] == "customer"
        assert mapped["target"] == audit.INTERFACE_LOCALE_NAVIGATOR_ROUTE
        assert mapped["status"] == "NAVIGATION_ONLY"
        assert mapped["resolution"] == "reviewed_interface_locale_fresh_web_navigation"
        assert mapped["source_dispositions"] == audit.INTERFACE_LOCALE_FRESH_WEB_NAVIGATION_DISPOSITIONS
        assert mapped["interface_locale_authority"] == "SIGNED_CUSTOMER_WEB_PROFILE"
        assert mapped["interface_locale_launch_mode"] == "WEB_NAVIGATION"
        assert mapped["interface_locale_route"] == audit.INTERFACE_LOCALE_NAVIGATOR_ROUTE
        assert mapped["interface_locale_feature_key"] == "interface_locale_navigator"
        assert mapped["interface_locale_action_kind"] == "SUPPORTED_WEB_SELECTOR"
        assert mapped["interface_locale_selection_allowed"] is True
        assert mapped["interface_locale_supported_values"] == ("vi", "en", "zh")
        assert mapped["interface_locale_display_only_values"] == ("ja", "ko", "th", "ar")

    for token in sorted(audit.INTERFACE_LOCALE_WEB_DISPLAY_ONLY_ACTIONS):
        mapped = audit._map_callback(token, "callback_data", evidence, routes)
        assert mapped["target"] == audit.INTERFACE_LOCALE_NAVIGATOR_ROUTE
        assert mapped["status"] == "NAVIGATION_ONLY"
        assert mapped["interface_locale_action_kind"] == "UNSUPPORTED_WEB_DISPLAY_ONLY"
        assert mapped["interface_locale_selection_allowed"] is False
        assert "UNSUPPORTED_WEB_INTERFACE_LOCALE_DISPLAY_ONLY" in mapped["source_dispositions"]
        assert mapped["interface_locale_supported_values"] == ("vi", "en", "zh")

    for token in sorted(audit.INTERFACE_LOCALE_WEB_MENU_NAVIGATION_ACTIONS):
        mapped = audit._map_callback(token, "callback_data", evidence, routes)
        assert mapped["target"] == audit.INTERFACE_LOCALE_NAVIGATOR_ROUTE
        assert mapped["status"] == "NAVIGATION_ONLY"
        assert mapped["interface_locale_action_kind"] == "BOT_MENU_NAVIGATION_ONLY"
        assert mapped["interface_locale_selection_allowed"] is False
        assert mapped["source_dispositions"] == audit.INTERFACE_LOCALE_FRESH_WEB_NAVIGATION_DISPOSITIONS

    for template in ("lang|{*}", "lang|future_locale|{*}"):
        mapped = audit._map_callback_template(template, evidence, routes)
        assert mapped is not None
        assert mapped["source_kind"] == "callback_template"
        assert mapped["target"] == "INTERFACE_LOCALE_SOURCE_REVIEW_REQUIRED"
        assert mapped["status"] == "NEEDS_FEATURE_DISPOSITION"
        assert mapped["resolution"] == "interface_locale_callback_requires_source_review"

    # Translation-pair commands are workflow concerns. They may retain their
    # existing account route, but must not masquerade as an interface locale
    # catalog or inherit the new navigation-only metadata.
    for command in ("en_vi", "vi_en", "ja_vi", "ko_vi", "zh_vi"):
        mapped = audit._map_command(
            {"command": command, "handler": "customer_handler", "file": "bot.py", "line": 1},
            routes,
        )
        assert mapped["target"] == "/account"
        assert "interface_locale_authority" not in mapped
        assert "interface_locale_supported_values" not in mapped

    assert not any(
        prefix == "lang|"
        for prefix, _target, _classification in audit.DYNAMIC_CALLBACK_TEMPLATE_ROUTE_OVERRIDES
    )


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


def test_static_audit_prunes_ephemeral_pytest_project_copies(tmp_path: Path) -> None:
    audit = _load_audit_module()
    web_root = tmp_path / "web"
    web_root.mkdir()
    (web_root / "app.py").write_text("app = FastAPI()", encoding="utf-8")
    ephemeral_copy = web_root / "_pytest_route_copy" / "web"
    ephemeral_copy.mkdir(parents=True)
    (ephemeral_copy / "copyfast_api.py").write_text(
        "app = FastAPI()\n@app.get('/should-not-be-audited')\nasync def ignored(): return {}",
        encoding="utf-8",
    )

    discovered = audit._source_files(web_root)
    relative_paths = {path.relative_to(web_root).as_posix() for path in discovered}

    assert relative_paths == {"app.py"}


def test_static_audit_derives_only_reviewed_literal_guided_video_callbacks(tmp_path: Path) -> None:
    audit = _load_audit_module()
    bot_root = tmp_path / "bot"
    web_root = tmp_path / "web"
    bot_root.mkdir()
    web_root.mkdir()
    (bot_root / "bot.py").write_text(
        '''
def guided_video_result_keyboard(prefix):
    return [
        ("Save", f"{prefix}|save"),
        ("Strength", f"{prefix}|strength|quick"),
    ]

guided_video_result_keyboard("promptvideo")
guided_video_result_keyboard("imagevideo")
guided_video_result_keyboard("videoref")
guided_video_result_keyboard("videoidea")
guided_video_result_keyboard(flow)
''',
        encoding="utf-8",
    )
    (web_root / "app.py").write_text(
        '''
app = FastAPI()
@app.get('/{page_path:path}')
async def web_page(page_path: str):
    return {}
''',
        encoding="utf-8",
    )

    result = audit.run_audit(bot_root, web_root, "baseline", tmp_path / "reports", tmp_path / "docs")
    inventory = result["bot_inventory"]
    template_values = {item["template"] for item in inventory["callback_templates"]}
    concrete_tokens = {item["token"] for item in inventory["callback_data"]}
    gap = result["parity_gap"]

    assert "{*}|save" in template_values
    assert "{*}|strength|quick" in template_values
    assert {
        "promptvideo|save", "imagevideo|save",
        "promptvideo|strength|quick", "imagevideo|strength|quick",
    }.issubset(concrete_tokens)
    assert not {"flow|save", "videoref|save", "videoidea|save"}.intersection(concrete_tokens)
    assert inventory["counts"]["callback_templates"] == len(template_values)
    assert gap["source_counts"]["callback_templates"] == len(template_values)
    assert gap["source_counts"]["unresolved_callback_templates"] == 0
    assert gap["mapping_coverage_percent"] == 100.0
    template_records = {item["template"]: item for item in inventory["callback_templates"]}
    template_mappings = {item["source"]: item for item in gap["callback_template_mappings"]}
    for template in ("{*}|save", "{*}|strength|quick"):
        assert template_records[template]["resolution"] == "reviewed_literal_prefix_helper_calls"
        assert template_records[template]["helper"] == "guided_video_result_keyboard"
        assert set(template_records[template]["derived_callback_tokens"]) == {
            template.replace("{*}", "promptvideo", 1),
            template.replace("{*}", "imagevideo", 1),
        }
        assert template_mappings[template]["status"] == "COPIED_GUARDED"
        assert template_mappings[template]["target"] == "DERIVED_LITERAL_PREFIX_CALLBACKS"
        assert set(template_mappings[template]["target_routes"]) == {
            "/video-studio/prompt-planner",
            "/video-studio/image-motion-planner",
        }
    mappings = {item["source"]: item for item in gap["callback_mappings"]}
    assert mappings["promptvideo|save"]["target"] == "/video-studio/prompt-planner"
    assert mappings["imagevideo|save"]["target"] == "/video-studio/image-motion-planner"
    assert mappings["imagevideo|save"]["status"] == "COPIED_GUARDED"


def test_static_audit_derives_reviewed_motion_music_helpers_without_broad_generic_mapping(tmp_path: Path) -> None:
    audit = _load_audit_module()
    bot_root = tmp_path / "bot"
    web_root = tmp_path / "web"
    bot_root.mkdir()
    web_root.mkdir()
    (bot_root / "bot.py").write_text(
        '''
def guided_video_motion_keyboard(prefix):
    back_action = "back_choices" if prefix == "promptvideo" else "back_style"
    return [
        ("Motion", f"{prefix}|motion_choice|1"),
        ("Back", f"{prefix}|{back_action}"),
    ]

def guided_video_music_keyboard(prefix):
    return [
        ("Music", f"{prefix}|music_choice|1"),
        ("Back", f"{prefix}|back_motion"),
    ]

def unrelated_keyboard(prefix):
    return [("Unreviewed", f"{prefix}|save")]

guided_video_motion_keyboard("promptvideo")
guided_video_motion_keyboard("imagevideo")
guided_video_motion_keyboard("videoref")
guided_video_music_keyboard("promptvideo")
guided_video_music_keyboard("imagevideo")
guided_video_music_keyboard("videoidea")
unrelated_keyboard("promptvideo")
''',
        encoding="utf-8",
    )
    (web_root / "app.py").write_text(
        '''
app = FastAPI()
@app.get('/{page_path:path}')
async def web_page(page_path: str):
    return {}
''',
        encoding="utf-8",
    )

    result = audit.run_audit(bot_root, web_root, "baseline", tmp_path / "reports", tmp_path / "docs")
    inventory = result["bot_inventory"]
    concrete_tokens = {item["token"] for item in inventory["callback_data"]}
    mappings = {item["source"]: item for item in result["parity_gap"]["callback_template_mappings"]}

    assert {
        "promptvideo|motion_choice|1", "imagevideo|motion_choice|1",
        "promptvideo|back_choices", "imagevideo|back_style",
        "promptvideo|music_choice|1", "imagevideo|music_choice|1",
        "promptvideo|back_motion", "imagevideo|back_motion",
    }.issubset(concrete_tokens)
    assert not {
        "videoref|motion_choice|1", "videoidea|music_choice|1", "promptvideo|save",
    }.intersection(concrete_tokens)
    assert mappings["{*}|motion_choice|1"]["status"] == "COPIED_GUARDED"
    assert set(mappings["{*}|motion_choice|1"]["target_routes"]) == {
        "/video-studio/prompt-planner",
        "/video-studio/image-motion-planner",
    }
    assert set(mappings["{*}|{*}"]["target_routes"]) == {
        "/video-studio/prompt-planner",
        "/image-studio",
    }
    assert mappings["{*}|music_choice|1"]["status"] == "COPIED_GUARDED"
    assert mappings["{*}|back_motion"]["status"] == "COPIED_GUARDED"
    assert mappings["{*}|save"]["status"] == "NEEDS_WEB_IMPLEMENTATION"
    assert audit._map_callback_template("{*}|save", {"file": "bot.py", "line": 1}, {"/{page_path:path}"}) is None


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
        "creative_flow": "/creative-flow",
        "media_factory": "/media-factory",
        "trend_research": "/trend-research",
        "video_factory_flow": "/video-studio/workflow",
        "story_video_factory": "/video-studio/story-video-plan",
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
        "source_help": "/guides/source-rights",
        "dubbing_help": "/guides/source-rights",
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


def test_static_audit_keeps_explicit_public_overrides_out_of_admin_surface() -> None:
    audit = _load_audit_module()
    routes = {"/{page_path:path}"}

    mapped = audit._map_command(
        {"command": "media_factory", "handler": "cmd_media_factory", "file": "bot.py", "line": 1, "admin_guarded": True},
        routes,
    )

    assert mapped["classification"] == "customer"
    assert mapped["target"] == "/media-factory"
    assert mapped["status"] == "COPIED_GUARDED"


def test_static_audit_maps_bot_contextual_meta_callbacks_to_the_web_wizard() -> None:
    audit = _load_audit_module()
    routes = {"/{page_path:path}"}

    fast_meta = audit._map_callback("freehub|meta", "callback_data", {"file": "bot.py", "line": 1}, routes)
    assert fast_meta["classification"] == "customer"
    assert fast_meta["target"] == "/content/prompt-pack"
    assert fast_meta["status"] == "COPIED_GUARDED"

    for callback in ("freehub|meta_goal_sell", "freehub|meta_platform_tiktok", "freehub|meta_ratio_9x16", "freehub|meta_style_ugc"):
        mapped = audit._map_callback(callback, "callback_data", {"file": "bot.py", "line": 1}, routes)
        assert mapped["classification"] == "customer"
        assert mapped["target"] == "/content/contextual-prompt"
        assert mapped["status"] == "COPIED_GUARDED"


def test_static_audit_maps_bot_free_hub_text_recipes_to_content_prompt_pack() -> None:
    audit = _load_audit_module()
    routes = {"/{page_path:path}"}

    for callback in ("freehub|caption", "freehub|ideas", "freehub|prompts", "freehub|hook"):
        mapped = audit._map_callback(callback, "callback_data", {"file": "bot.py", "line": 1}, routes)
        assert mapped["classification"] == "customer"
        assert mapped["target"] == "/content/prompt-pack"
        assert mapped["status"] == "COPIED_GUARDED"


def test_static_audit_maps_bot_free_hub_publish_package_to_explicit_web_review() -> None:
    audit = _load_audit_module()
    routes = {"/{page_path:path}"}

    mapped = audit._map_callback("freehub|publish_package", "callback_data", {"file": "bot.py", "line": 1}, routes)

    assert mapped["classification"] == "customer"
    assert mapped["target"] == "/content/publish-review"
    assert mapped["status"] == "COPIED_GUARDED"


def test_static_audit_maps_bot_reference_format_planning_to_owner_scoped_web_workspace() -> None:
    audit = _load_audit_module()
    routes = {"/{page_path:path}"}

    for callback in (
        "videoref|hub", "videoref|start", "videoref|await_video", "videoref|direction|viral",
        "videoref|topic_choice", "videoref|profile_goal|sales", "videoref|plan", "videoref|save",
    ):
        mapped = audit._map_callback(callback, "callback_data", {"file": "bot.py", "line": 1}, routes)
        assert mapped["classification"] == "customer"
        assert mapped["target"] == "/video-studio/reference-format-planner"
        assert mapped["status"] == "COPIED_GUARDED"

    package = audit._map_callback("videoref|publish_package", "callback_data", {"file": "bot.py", "line": 1}, routes)
    assert package["target"] == "/content/publish-review"
    assert package["status"] == "COPIED_GUARDED"


def test_static_audit_maps_only_reviewed_video_idea_planning_callbacks_to_web_planner() -> None:
    audit = _load_audit_module()
    routes = {"/{page_path:path}"}

    for callback in (
        "videoidea|start",
        "videoidea|kind|ad",
        "videoidea|product_type|service",
        "videoidea|product_choice|2",
        "videoidea|goal|sales",
        "videoidea|context|3",
        "videoidea|cinema_choice|1",
        "videoidea|genre|drama",
        "videoidea|choose|2",
        "videoidea|storyboard",
        "videoidea|image_prompts",
        "videoidea|video_prompts",
        "videoidea|music",
        "videoidea|save",
    ):
        mapped = audit._map_callback(callback, "callback_data", {"file": "bot.py", "line": 1}, routes)
        assert mapped["classification"] == "customer"
        assert mapped["target"] == "/video-studio/idea-planner"
        assert mapped["status"] == "COPIED_GUARDED"

    for callback in (
        "videoidea|finalization",
        "videoidea|frame_video",
        "videoidea|render_ai",
        "videoidea|platform|tiktok",
        "videoidea|platform_custom",
        "videoidea|trend_type|problem_solution",
    ):
        mapped = audit._map_callback(callback, "callback_data", {"file": "bot.py", "line": 1}, routes)
        assert mapped["classification"] == "customer"
        assert mapped["target"] == "TELEGRAM_ONLY"
        assert mapped["status"] == "TELEGRAM_ONLY"

    # A future/unknown sub-action is intentionally not swallowed by a broad
    # ``videoidea|`` prefix. It must receive its own reviewed disposition.
    unknown = audit._map_callback("videoidea|future_action|1", "callback_data", {"file": "bot.py", "line": 1}, routes)
    assert unknown["target"] != "/video-studio/idea-planner"


def test_static_audit_maps_only_reviewed_self_scene_text_planning_to_web_planner() -> None:
    audit = _load_audit_module()
    routes = {"/{page_path:path}"}

    for callback in (
        "selfscene|start",
        "selfscene|plan_without_video",
        "selfscene|direction_choice|1",
        "selfscene|direction|cinematic",
        "selfscene|object|person",
        "selfscene|input|product",
        "selfscene|context|3",
        "selfscene|context_custom",
        "selfscene|style_choice|2",
        "selfscene|style_custom",
        "selfscene|music|none",
        "selfscene|image_guard",
        "selfscene|music_guard",
        "selfscene|plan",
        "selfscene|save",
    ):
        mapped = audit._map_callback(callback, "callback_data", {"file": "bot.py", "line": 1}, routes)
        assert mapped["classification"] == "customer"
        assert mapped["target"] == "/video-studio/self-shot-planner"
        assert mapped["status"] == "COPIED_GUARDED"

    for callback in (
        "selfscene|await_video",
        "selfscene|use_recent_video",
        "selfscene|input|video",
        "selfscene|back_upload",
        "selfscene|video_guard",
        "selfscene|frame_hint",
        "selfscene|finalization",
    ):
        mapped = audit._map_callback(callback, "callback_data", {"file": "bot.py", "line": 1}, routes)
        assert mapped["classification"] == "customer"
        assert mapped["target"] == "TELEGRAM_ONLY"
        assert mapped["status"] == "TELEGRAM_ONLY"

    # No broad ``selfscene|`` fallback: a future action cannot inherit the
    # proposed planner simply because it has the same Bot callback prefix.
    unknown = audit._map_callback("selfscene|future_action|1", "callback_data", {"file": "bot.py", "line": 1}, routes)
    assert unknown["target"] != "/video-studio/self-shot-planner"


def test_static_audit_maps_only_literal_long_video_planning_callbacks_to_web_roadmap() -> None:
    audit = _load_audit_module()
    routes = {"/{page_path:path}"}

    for callback in (
        "longvideo|start",
        "longvideo|topic|sales",
        "longvideo|topic_choice|2",
        "longvideo|topic_refresh",
        "longvideo|duration|10 phút",
        "longvideo|duration_custom",
        "longvideo|style|cinematic",
        "longvideo|style_custom",
        "longvideo|structure|3",
        "longvideo|structure_custom",
        "longvideo|storyboard",
        "longvideo|image_prompts",
        "longvideo|video_prompts",
        "longvideo|music",
        "longvideo|save",
    ):
        mapped = audit._map_callback(callback, "callback_data", {"file": "bot.py", "line": 1}, routes)
        assert mapped["classification"] == "customer"
        assert mapped["target"] == "/video-studio/long-form-planner"
        assert mapped["status"] == "COPIED_GUARDED"

    for callback in ("longvideo|finalization", "longvideo|frame_video", "longvideo|render_segments"):
        mapped = audit._map_callback(callback, "callback_data", {"file": "bot.py", "line": 1}, routes)
        assert mapped["classification"] == "customer"
        assert mapped["target"] == "TELEGRAM_ONLY"
        assert mapped["status"] == "TELEGRAM_ONLY"

    # Deliberately no ``longvideo|`` namespace fallback: an unreviewed action
    # cannot inherit a Web route merely because it resembles the planner.
    unknown = audit._map_callback("longvideo|future_action|1", "callback_data", {"file": "bot.py", "line": 1}, routes)
    assert unknown["target"] != "/video-studio/long-form-planner"
    structure = audit._map_callback_template("longvideo|structure|{*}", {"file": "bot.py", "line": 1}, routes)
    assert structure is not None
    assert structure["target"] == "/video-studio/long-form-planner"
    assert structure["status"] == "COPIED_GUARDED"
    assert structure["resolution"] == "reviewed_bounded_longvideo_structure_template"


def test_static_audit_maps_prompt_and_image_video_wizard_steps_to_web_planners() -> None:
    audit = _load_audit_module()
    routes = {"/{page_path:path}"}

    for callback in (
        "promptvideo|motion_choice|1", "promptvideo|music_custom", "promptvideo|strength|director",
        "promptvideo|finalization", "promptvideo|generate", "promptvideo|save", "promptvideo|edit_prompt",
    ):
        mapped = audit._map_callback(callback, "callback_data", {"file": "bot.py", "line": 1}, routes)
        assert mapped["target"] == "/video-studio/prompt-planner"
        assert mapped["status"] == "COPIED_GUARDED"

    for callback in ("imagevideo|motion_choice|1", "imagevideo|music_choice|2", "imagevideo|strength|premium", "imagevideo|edit_prompt"):
        mapped = audit._map_callback(callback, "callback_data", {"file": "bot.py", "line": 1}, routes)
        assert mapped["target"] == "/video-studio/image-motion-planner"
        assert mapped["status"] == "COPIED_GUARDED"

    # The upload-specific Bot screens are intentionally distinct: the Web
    # first sends the user to the validated Image Studio/Asset Vault boundary.
    source = audit._map_callback("imagevideo|await_image", "callback_data", {"file": "bot.py", "line": 1}, routes)
    assert source["target"] == "/image-studio"


def test_static_audit_maps_free_hub_gallery_upload_docs_and_server_recomputed_save() -> None:
    audit = _load_audit_module()
    routes = {"/{page_path:path}"}

    expected = {
        "freehub|library": "/free-prompt-gallery",
        "freehub|lib_pick1": "/free-prompt-gallery",
        "freehub|lib_more": "/free-prompt-gallery",
        "freehub|upload": "/asset-vault",
        "freehub|docs": "/notes",
        "freehub|docs_split_merge": "/documents",
        "freehub|suggest_pick1": "/content/prompt-pack",
        "freehub|to_cinematic": "/video-studio/cinematic-concept",
        "freehub|image_prompt": "/image/prompt-composer",
        "freehub|video_prompt": "/video-studio/prompt-planner",
    }
    for callback, target in expected.items():
        mapped = audit._map_callback(callback, "callback_data", {"file": "bot.py", "line": 1}, routes)
        assert mapped["classification"] == "customer"
        assert mapped["target"] == target
        if callback in audit.MEMORY_FRESH_WEB_NAVIGATION_ACTIONS:
            assert mapped["status"] == "NAVIGATION_ONLY"
            assert mapped["resolution"] == "reviewed_memory_fresh_web_navigation"
        else:
            assert mapped["status"] == "COPIED_GUARDED"

    save = audit._map_callback("freehub|save", "callback_data", {"file": "bot.py", "line": 1}, routes)
    assert save["target"] == "/content/prompt-pack"
    assert save["status"] == "COPIED_GUARDED"


def test_static_audit_maps_only_reviewed_free_hub_library_categories_to_fresh_gallery_navigation(tmp_path: Path) -> None:
    """The Bot library category state must not become a browser identifier."""

    audit = _load_audit_module()
    routes = {"/{page_path:path}"}
    evidence = {"file": "bot.py", "line": 1}

    mapped = audit._map_callback_template("freehub|lib_{*}", evidence, routes)
    assert mapped is not None
    assert mapped["classification"] == "customer"
    assert mapped["target"] == "/free-prompt-gallery"
    assert mapped["status"] == "NAVIGATION_ONLY"
    assert mapped["resolution"] == "reviewed_freehub_library_category_navigation"
    assert mapped["source_dispositions"] == [
        "FRESH_SIGNED_WEB_NAVIGATION",
        "BOT_PENDING_STATE_NOT_REPLAYED",
        "NO_RUNTIME_CLAIM",
    ]
    assert "never accepts that value" in mapped["source_evidence"]

    # This is intentionally an exact source-reviewed template, not a broad
    # freehub prefix that could turn a future Bot stateful callback green.
    assert audit._map_callback_template("freehub|lib_future_{*}", evidence, routes) is None

    bot_root = tmp_path / "bot"
    web_root = tmp_path / "web"
    bot_root.mkdir()
    web_root.mkdir()
    (bot_root / "bot.py").write_text(
        '''
category = "video"
InlineKeyboardButton("Prompt library", callback_data=f"freehub|lib_{category}")
''',
        encoding="utf-8",
    )
    (web_root / "app.py").write_text(
        '''
app = FastAPI()
@app.get("/{page_path:path}")
async def page(page_path):
    return {}
''',
        encoding="utf-8",
    )

    result = audit.run_audit(bot_root, web_root, "baseline", tmp_path / "reports", tmp_path / "docs")
    report_mapping = {
        item["source"]: item for item in result["parity_gap"]["callback_template_mappings"]
    }["freehub|lib_{*}"]
    assert report_mapping["status"] == "NAVIGATION_ONLY"
    assert report_mapping["target"] == "/free-prompt-gallery"
    assert report_mapping["resolution"] == "reviewed_freehub_library_category_navigation"
    assert result["parity_gap"]["source_counts"]["unresolved_callback_templates"] == 0
    assert result["parity_gap"]["static_web_surface_coverage_percent"] == 0.0
    assert result["parity_gap"]["mapping_coverage_percent"] == 100.0
    assert "FREE_PROMPT_GALLERY_CONTRACT.md" in (tmp_path / "docs" / "README.md").read_text(encoding="utf-8")


def test_static_audit_keeps_payos_alert_callbacks_in_their_admin_authority_boundary(tmp_path: Path) -> None:
    audit = _load_audit_module()
    routes = {"/{page_path:path}"}
    evidence = {"file": "bot.py", "line": 1}

    manual = audit._map_callback("payosalert|manual", "callback_data", evidence, routes)
    assert manual["classification"] == "admin"
    assert manual["target"] == "/admin/payments"
    assert manual["status"] == "NAVIGATION_ONLY"
    assert manual["resolution"] == "reviewed_payos_alert_admin_navigation"
    assert manual["source_dispositions"] == (
        "BOT_ADMIN_ONLY",
        "BOT_EPHEMERAL_BILL_STATE_NOT_REPLAYED",
        "FRESH_SIGNED_WEB_ADMIN_NAVIGATION",
        "NO_RUNTIME_CLAIM",
    )
    assert "no Bot state" in manual["source_evidence"]

    expected_dispositions = {
        "payosalert|test": "TELEGRAM_COMMAND_GUIDANCE",
        "payosalert|mute": "BOT_PROCESS_LOCAL_ALERT_STATE",
        "payosalert|renewed": "DEPLOYMENT_ENV_GUIDANCE",
        "payosalert|remind_later": "TELEGRAM_MESSAGE_DISMISSAL",
    }
    for callback, disposition in expected_dispositions.items():
        mapped = audit._map_callback(callback, "callback_data", evidence, routes)
        assert mapped["classification"] == "admin"
        assert mapped["target"] == "TELEGRAM_ONLY"
        assert mapped["status"] == "TELEGRAM_ONLY"
        assert mapped["resolution"] == "reviewed_payos_alert_telegram_admin_only"
        assert disposition in mapped["source_dispositions"]
        assert "NO_RUNTIME_CLAIM" in mapped["source_dispositions"]

    # The Bot dispatcher accepts a namespace pattern, but unreviewed future
    # values must never be silently classified as dashboard or payment UI.
    unknown = audit._map_callback("payosalert|future_action", "callback_data", evidence, routes)
    audit._annotate_feature_disposition(unknown)
    assert unknown["classification"] == "admin"
    assert unknown["target"] == "PAYOS_ALERT_SOURCE_REVIEW_REQUIRED"
    assert unknown["status"] == "NEEDS_FEATURE_DISPOSITION"
    assert unknown["fallback_family"] == "payosalert"
    assert "CANONICAL_BOT_PAYOS_ALERT_FLOW" in unknown["source_dispositions"]
    assert "NO_RUNTIME_CLAIM" in unknown["source_dispositions"]

    bot_root = tmp_path / "bot"
    web_root = tmp_path / "web"
    bot_root.mkdir()
    web_root.mkdir()
    (bot_root / "bot.py").write_text(
        '''
InlineKeyboardButton("Manual", callback_data="payosalert|manual")
InlineKeyboardButton("Test", callback_data="payosalert|test")
InlineKeyboardButton("Mute", callback_data="payosalert|mute")
InlineKeyboardButton("Renewed", callback_data="payosalert|renewed")
InlineKeyboardButton("Later", callback_data="payosalert|remind_later")
''',
        encoding="utf-8",
    )
    (web_root / "app.py").write_text(
        '''
app = FastAPI()
@app.get("/{page_path:path}")
async def page(page_path):
    return {}
''',
        encoding="utf-8",
    )

    result = audit.run_audit(bot_root, web_root, "baseline", tmp_path / "reports", tmp_path / "docs")
    report_mappings = {
        item["source"]: item
        for item in result["parity_gap"]["callback_mappings"]
    }
    assert report_mappings["payosalert|manual"]["status"] == "NAVIGATION_ONLY"
    assert report_mappings["payosalert|manual"]["target"] == "/admin/payments"
    assert all(
        report_mappings[callback]["status"] == "TELEGRAM_ONLY"
        for callback in expected_dispositions
    )
    assert "payosalert" not in {
        item["family"] for item in result["parity_gap"]["feature_disposition_backlog"]
    }
    contract = (tmp_path / "docs" / "PAYOS_ALERT_CALLBACK_CONTRACT.md").read_text(encoding="utf-8")
    assert "payosalert|manual" in contract
    assert "PAYOS_ALERT_SOURCE_REVIEW_REQUIRED" in contract
    assert "PAYOS_ALERT_CALLBACK_CONTRACT.md" in (tmp_path / "docs" / "README.md").read_text(encoding="utf-8")


def test_static_audit_keeps_billing_menu_private_canonical_admin_navigation_only() -> None:
    """Billing is an exact Bot-admin menu hint, never a customer payment action."""
    audit = _load_audit_module()
    routes = {"/{page_path:path}"}
    evidence = {"file": "bot.py", "line": 1}

    assert set(audit.BILLING_MENU_FRESH_WEB_ADMIN_NAVIGATION_ACTIONS) == {"menu|billing"}
    descriptor = audit.BILLING_MENU_FRESH_WEB_ADMIN_NAVIGATION_ACTIONS["menu|billing"]
    assert descriptor["target"] == "/admin/payments"
    assert descriptor["classification"] == "admin"
    assert descriptor["feature_key"] == "admin_payments"
    assert descriptor["authority"] == "SIGNED_CANONICAL_ADMIN_READ"
    assert descriptor["launch_mode"] == "WEB_NAVIGATION"
    assert descriptor["source_dispositions"] == (
        "BOT_ADMIN_ONLY",
        "BOT_BILLING_MENU_STATE_NOT_REPLAYED",
        "FRESH_SIGNED_WEB_CANONICAL_ADMIN_NAVIGATION",
        "NO_CUSTOMER_OR_MANUAL_TOPUP_ACTION",
        "NO_PAYOS_WALLET_OR_LEDGER_ACTION",
        "NO_RUNTIME_CLAIM",
    )

    mapped = audit._map_callback("menu|billing", "callback_data", evidence, routes)
    assert mapped["target"] == "/admin/payments"
    assert mapped["classification"] == "admin"
    assert mapped["status"] == "NAVIGATION_ONLY"
    assert mapped["resolution"] == "reviewed_billing_menu_admin_navigation"
    assert mapped["source_dispositions"] == descriptor["source_dispositions"]
    assert mapped["billing_menu_feature_key"] == "admin_payments"
    assert mapped["billing_menu_authority"] == "SIGNED_CANONICAL_ADMIN_READ"
    assert mapped["billing_menu_launch_mode"] == "WEB_NAVIGATION"

    # An adjacent or future Bot callback cannot inherit an administrator route
    # or any financial control through the menu namespace.
    unknown = audit._map_callback("menu|billing_future", "callback_data", evidence, routes)
    assert unknown["target"] != "/admin/payments"
    assert unknown["resolution"] != "reviewed_billing_menu_admin_navigation"
    wrong_case = audit._map_callback("MENU|BILLING", "callback_data", evidence, routes)
    assert wrong_case["target"] != "/admin/payments"
    assert wrong_case["resolution"] != "reviewed_billing_menu_admin_navigation"

    # The raw Bot identifier and the administrator-only target are both
    # absent from the browser-safe customer catalog.
    from copyfast_registry import menu_capability_catalog

    public_catalog = menu_capability_catalog()
    assert all("menu|billing" not in str(item) for item in public_catalog)
    assert all(item["route"] != "/admin/payments" for item in public_catalog)
    assert "menu|billing" not in audit.MENU_ACTION_REGISTRY


def test_static_audit_keeps_package_purchase_callbacks_in_catalog_or_bot_payment_boundary(tmp_path: Path) -> None:
    """A service package selection is not a Xu top-up or browser checkout."""

    audit = _load_audit_module()
    routes = {"/{page_path:path}"}
    evidence = {"file": "bot.py", "line": 1}
    expected_selectors = {
        "pkgbuy|combo|basic_199k",
        "pkgbuy|combo|posting_499k",
        "pkgbuy|combo|product_ads_699k",
        "pkgbuy|combo|standard_299k",
        "pkgbuy|combo|tiktok_99k",
        "pkgbuy|monthly|creator_monthly",
        "pkgbuy|monthly|pro_monthly",
        "pkgbuy|monthly|shop_monthly",
        "pkgbuy|monthly|starter_monthly",
    }
    assert set(audit.PACKAGE_PURCHASE_SELECTOR_CALLBACKS) == expected_selectors

    for callback in expected_selectors:
        mapped = audit._map_callback(callback, "callback_data", evidence, routes)
        assert mapped["classification"] == "customer"
        assert mapped["target"] == "/packages"
        assert mapped["status"] == "NAVIGATION_ONLY"
        assert mapped["resolution"] == "reviewed_package_catalog_selector_navigation"
        assert mapped["source_dispositions"] == (
            "FRESH_SIGNED_WEB_NAVIGATION",
            "BOT_CATALOG_SELECTION_NOT_REPLAYED",
            "NO_RUNTIME_CLAIM",
        )
        assert "never receives the Bot package type/code" in mapped["source_evidence"]

    confirm = audit._map_callback_template(
        "pkgbuy|confirm|{*}|{*}", evidence, routes
    )
    assert confirm is not None
    assert confirm["classification"] == "customer"
    assert confirm["target"] == "TELEGRAM_ONLY"
    assert confirm["status"] == "TELEGRAM_ONLY"
    assert confirm["resolution"] == "bot_canonical_package_checkout"
    assert confirm["source_dispositions"] == (
        "TELEGRAM_IDENTITY_CONTEXT",
        "CANONICAL_BOT_ORDER_REQUIRED",
        "CANONICAL_BOT_PAYOS_CHECKOUT",
        "CANONICAL_PACKAGE_ENTITLEMENT_SETTLEMENT",
        "NO_RUNTIME_CLAIM",
    )
    assert "start_package_purchase" in confirm["source_evidence"]

    unknown = audit._map_callback("pkgbuy|future|example", "callback_data", evidence, routes)
    audit._annotate_feature_disposition(unknown)
    assert unknown["target"] == "PACKAGE_PURCHASE_SOURCE_REVIEW_REQUIRED"
    assert unknown["status"] == "NEEDS_FEATURE_DISPOSITION"
    assert unknown["fallback_family"] == "pkgbuy"
    assert "CANONICAL_PACKAGE_PURCHASE_SOURCE_REVIEW" in unknown["source_dispositions"]

    unknown_template = audit._map_callback_template("pkgbuy|future|{*}", evidence, routes)
    assert unknown_template is not None
    assert unknown_template["target"] == "PACKAGE_PURCHASE_SOURCE_REVIEW_REQUIRED"
    assert unknown_template["status"] == "NEEDS_FEATURE_DISPOSITION"

    bot_root = tmp_path / "bot"
    web_root = tmp_path / "web"
    bot_root.mkdir()
    web_root.mkdir()
    selector_buttons = "\n".join(
        f'InlineKeyboardButton("Package", callback_data="{callback}")'
        for callback in sorted(expected_selectors)
    )
    (bot_root / "bot.py").write_text(
        selector_buttons
        + '''
package_type = "monthly"
package_code = "starter_monthly"
InlineKeyboardButton("Confirm", callback_data=f"pkgbuy|confirm|{package_type}|{package_code}")
''',
        encoding="utf-8",
    )
    (web_root / "app.py").write_text(
        '''
app = FastAPI()
@app.get("/{page_path:path}")
async def page(page_path):
    return {}
''',
        encoding="utf-8",
    )

    result = audit.run_audit(bot_root, web_root, "baseline", tmp_path / "reports", tmp_path / "docs")
    report_callbacks = {
        item["source"]: item for item in result["parity_gap"]["callback_mappings"]
    }
    assert all(
        report_callbacks[callback]["target"] == "/packages"
        and report_callbacks[callback]["status"] == "NAVIGATION_ONLY"
        for callback in expected_selectors
    )
    report_templates = {
        item["source"]: item
        for item in result["parity_gap"]["callback_template_mappings"]
    }
    assert report_templates["pkgbuy|confirm|{*}|{*}"]["target"] == "TELEGRAM_ONLY"
    assert "pkgbuy" not in {
        item["family"] for item in result["parity_gap"]["feature_disposition_backlog"]
    }
    contract = (tmp_path / "docs" / "PACKAGE_PURCHASE_CALLBACK_CONTRACT.md").read_text(encoding="utf-8")
    assert "pkgbuy|monthly|starter_monthly" in contract
    assert "pkgbuy|confirm|{*}|{*}" in contract
    assert "PACKAGE_PURCHASE_CALLBACK_CONTRACT.md" in (tmp_path / "docs" / "README.md").read_text(encoding="utf-8")
    assert "Service package/combo checkout is distinct from Xu top-up" in (
        tmp_path / "docs" / "PAYOS_WALLET_JOB_MAP.md"
    ).read_text(encoding="utf-8")


def test_static_audit_keeps_video_job_callbacks_in_admin_or_bot_mutation_boundary(tmp_path: Path) -> None:
    """Canonical Bot job IDs must never become customer or browser mutations."""

    audit = _load_audit_module()
    routes = {"/{page_path:path}"}
    evidence = {"file": "bot.py", "line": 1}

    stats = audit._map_callback("job|stats|0", "callback_data", evidence, routes)
    assert stats["classification"] == "admin"
    assert stats["target"] == "/admin/jobs"
    assert stats["status"] == "NAVIGATION_ONLY"
    assert stats["resolution"] == "reviewed_video_job_stats_admin_navigation"
    assert stats["source_dispositions"] == (
        "BOT_ADMIN_ONLY",
        "BOT_VIDEO_JOB_STATS_NOT_REPLAYED",
        "FRESH_SIGNED_WEB_ADMIN_NAVIGATION",
        "NO_RUNTIME_CLAIM",
    )
    assert "fresh role-checked admin view" in stats["source_evidence"]

    for template in ("job|approve|{*}", "job|cancel|{*}"):
        mapped = audit._map_callback_template(template, evidence, routes)
        assert mapped is not None
        assert mapped["classification"] == "admin"
        assert mapped["target"] == "TELEGRAM_ONLY"
        assert mapped["status"] == "TELEGRAM_ONLY"
        assert mapped["resolution"] == "bot_canonical_video_job_mutation"
        assert mapped["source_dispositions"] == (
            "BOT_ADMIN_ONLY",
            "CANONICAL_BOT_JOB_MUTATION",
            "OWNER_SCOPED_BOT_JOB_REQUIRED",
            "NO_RUNTIME_CLAIM",
        )
        assert "canonical ID and Telegram owner" in mapped["source_evidence"]

    unknown = audit._map_callback("job|future|example", "callback_data", evidence, routes)
    audit._annotate_feature_disposition(unknown)
    assert unknown["classification"] == "admin"
    assert unknown["target"] == "BOT_VIDEO_JOB_SOURCE_REVIEW_REQUIRED"
    assert unknown["status"] == "NEEDS_FEATURE_DISPOSITION"
    assert unknown["fallback_family"] == "job"
    assert "CANONICAL_BOT_VIDEO_JOB_STATE" in unknown["source_dispositions"]

    unknown_template = audit._map_callback_template("job|future|{*}", evidence, routes)
    assert unknown_template is not None
    assert unknown_template["classification"] == "admin"
    assert unknown_template["target"] == "BOT_VIDEO_JOB_SOURCE_REVIEW_REQUIRED"
    assert unknown_template["status"] == "NEEDS_FEATURE_DISPOSITION"

    bot_root = tmp_path / "bot"
    web_root = tmp_path / "web"
    bot_root.mkdir()
    web_root.mkdir()
    (bot_root / "bot.py").write_text(
        '''
job_id = 7
InlineKeyboardButton("Stats", callback_data="job|stats|0")
InlineKeyboardButton("Approve", callback_data=f"job|approve|{job_id}")
InlineKeyboardButton("Cancel", callback_data=f"job|cancel|{job_id}")
''',
        encoding="utf-8",
    )
    (web_root / "app.py").write_text(
        '''
app = FastAPI()
@app.get("/{page_path:path}")
async def page(page_path):
    return {}
''',
        encoding="utf-8",
    )

    result = audit.run_audit(bot_root, web_root, "baseline", tmp_path / "reports", tmp_path / "docs")
    report_callbacks = {
        item["source"]: item for item in result["parity_gap"]["callback_mappings"]
    }
    assert report_callbacks["job|stats|0"]["classification"] == "admin"
    assert report_callbacks["job|stats|0"]["target"] == "/admin/jobs"
    assert report_callbacks["job|stats|0"]["status"] == "NAVIGATION_ONLY"
    report_templates = {
        item["source"]: item
        for item in result["parity_gap"]["callback_template_mappings"]
    }
    assert all(
        report_templates[template]["target"] == "TELEGRAM_ONLY"
        and report_templates[template]["status"] == "TELEGRAM_ONLY"
        for template in ("job|approve|{*}", "job|cancel|{*}")
    )
    assert "job" not in {
        item["family"] for item in result["parity_gap"]["feature_disposition_backlog"]
    }
    contract = (tmp_path / "docs" / "VIDEO_JOB_CALLBACK_CONTRACT.md").read_text(encoding="utf-8")
    assert "job|stats|0" in contract
    assert "job|approve|{*}" in contract
    assert "BOT_VIDEO_JOB_SOURCE_REVIEW_REQUIRED" in contract
    assert "VIDEO_JOB_CALLBACK_CONTRACT.md" in (tmp_path / "docs" / "README.md").read_text(encoding="utf-8")
    assert "Bot video-job stats can only open" in (
        tmp_path / "docs" / "PAYOS_WALLET_JOB_MAP.md"
    ).read_text(encoding="utf-8")


def test_static_audit_keeps_storage_addon_callbacks_in_the_bot_payment_boundary(tmp_path: Path) -> None:
    """Storage quota purchase must never inherit the Xu top-up route."""

    audit = _load_audit_module()
    routes = {"/{page_path:path}"}
    evidence = {"file": "bot.py", "line": 1}

    expected_callbacks = {
        "storage|menu": (
            "CANONICAL_BOT_STORAGE_ADDON_CATALOG",
            "TELEGRAM_PAYMENT_CONTEXT",
            "NO_RUNTIME_CLAIM",
        ),
        "storage|custom": (
            "TELEGRAM_IDENTITY_CONTEXT",
            "BOT_PENDING_STORAGE_INPUT",
            "NO_RUNTIME_CLAIM",
        ),
    }
    for callback, dispositions in expected_callbacks.items():
        mapped = audit._map_callback(callback, "callback_data", evidence, routes)
        assert mapped["classification"] == "customer"
        assert mapped["target"] == "TELEGRAM_ONLY"
        assert mapped["status"] == "TELEGRAM_ONLY"
        assert mapped["resolution"] == "reviewed_storage_addon_telegram_only"
        assert mapped["source_dispositions"] == list(dispositions)
        assert "/wallet/topup" not in mapped["source_evidence"]

    confirm = audit._map_callback_template("storage|confirm|{*}", evidence, routes)
    assert confirm is not None
    assert confirm["classification"] == "customer"
    assert confirm["target"] == "TELEGRAM_ONLY"
    assert confirm["status"] == "TELEGRAM_ONLY"
    assert confirm["resolution"] == "bot_canonical_storage_addon_checkout"
    assert confirm["source_dispositions"] == (
        "TELEGRAM_IDENTITY_CONTEXT",
        "CANONICAL_BOT_STORAGE_ORDER_REQUIRED",
        "CANONICAL_BOT_PAYOS_CHECKOUT",
        "CANONICAL_STORAGE_ENTITLEMENT_SETTLEMENT",
        "NO_RUNTIME_CLAIM",
    )
    assert "canonical storage order and PayOS checkout" in confirm["source_evidence"]

    unknown = audit._map_callback("storage|future|example", "callback_data", evidence, routes)
    audit._annotate_feature_disposition(unknown)
    assert unknown["target"] == "STORAGE_ADDON_SOURCE_REVIEW_REQUIRED"
    assert unknown["status"] == "NEEDS_FEATURE_DISPOSITION"
    assert unknown["fallback_family"] == "storage"
    assert "CANONICAL_BOT_STORAGE_ADDON_SOURCE_REVIEW" in unknown["source_dispositions"]

    unknown_template = audit._map_callback_template("storage|select|{*}", evidence, routes)
    assert unknown_template is not None
    assert unknown_template["target"] == "STORAGE_ADDON_SOURCE_REVIEW_REQUIRED"
    assert unknown_template["status"] == "NEEDS_FEATURE_DISPOSITION"

    bot_root = tmp_path / "bot"
    web_root = tmp_path / "web"
    bot_root.mkdir()
    web_root.mkdir()
    (bot_root / "bot.py").write_text(
        '''
InlineKeyboardButton("Storage menu", callback_data="storage|menu")
InlineKeyboardButton("Custom", callback_data="storage|custom")
code = "100mb"
InlineKeyboardButton("Confirm", callback_data=f"storage|confirm|{code}")
''',
        encoding="utf-8",
    )
    (web_root / "app.py").write_text(
        '''
app = FastAPI()
@app.get("/{page_path:path}")
async def page(page_path):
    return {}
''',
        encoding="utf-8",
    )

    result = audit.run_audit(bot_root, web_root, "baseline", tmp_path / "reports", tmp_path / "docs")
    report_callbacks = {
        item["source"]: item for item in result["parity_gap"]["callback_mappings"]
    }
    assert all(
        report_callbacks[callback]["target"] == "TELEGRAM_ONLY"
        and report_callbacks[callback]["status"] == "TELEGRAM_ONLY"
        for callback in expected_callbacks
    )
    report_templates = {
        item["source"]: item
        for item in result["parity_gap"]["callback_template_mappings"]
    }
    assert report_templates["storage|confirm|{*}"]["target"] == "TELEGRAM_ONLY"
    assert "storage" not in {
        item["family"] for item in result["parity_gap"]["feature_disposition_backlog"]
    }
    contract = (tmp_path / "docs" / "STORAGE_ADDON_CALLBACK_CONTRACT.md").read_text(encoding="utf-8")
    assert "storage\\|custom" in contract
    assert "storage\\|confirm\\|{*}" in contract
    assert "STORAGE_ADDON_SOURCE_REVIEW_REQUIRED" in contract
    assert "STORAGE_ADDON_CALLBACK_CONTRACT.md" in (tmp_path / "docs" / "README.md").read_text(encoding="utf-8")
    assert "Storage quota add-on purchase is distinct from Xu top-up" in (
        tmp_path / "docs" / "PAYOS_WALLET_JOB_MAP.md"
    ).read_text(encoding="utf-8")


def test_static_audit_keeps_video_finalization_callbacks_out_of_browser_actions(tmp_path: Path) -> None:
    """Bot vfinal state must never inherit a Web export/voice/subtitle route."""

    audit = _load_audit_module()
    routes = {"/video/finishing", "/{page_path:path}"}
    evidence = {"file": "bot.py", "line": 1}
    reviewed = (
        "vfinal|review",
        "vfinal|export_ai",
        "vfinal|voice_lang|vi",
        "vfinal|tier|basic",
    )
    for callback in reviewed:
        mapped = audit._map_callback(callback, "callback_data", evidence, routes)
        assert mapped["classification"] == "customer"
        assert mapped["target"] == "TELEGRAM_ONLY"
        assert mapped["status"] == "TELEGRAM_ONLY"
        assert mapped["resolution"] == "reviewed_video_finalization_telegram_only"
        assert mapped["source_dispositions"] == (
            "TELEGRAM_IDENTITY_CONTEXT",
            "BOT_VIDEO_FINALIZATION_SESSION_STATE",
            "BOT_PENDING_MEDIA_OR_TEXT_STATE",
            "CANONICAL_VIDEO_EXPORT_AND_PAYMENT_GUARDS",
            "NO_RUNTIME_CLAIM",
        )
        assert "Web Video Finishing workflow" in mapped["source_evidence"]

    reviewed_template = audit._map_callback_template("vfinal|tier|{*}", evidence, routes)
    assert reviewed_template is not None
    assert reviewed_template["target"] == "TELEGRAM_ONLY"
    assert reviewed_template["status"] == "TELEGRAM_ONLY"
    assert reviewed_template["resolution"] == "reviewed_video_finalization_telegram_only"

    unknown = audit._map_callback("vfinal|future_export", "callback_data", evidence, routes)
    audit._annotate_feature_disposition(unknown)
    assert unknown["target"] == "VIDEO_FINALIZATION_SOURCE_REVIEW_REQUIRED"
    assert unknown["status"] == "NEEDS_FEATURE_DISPOSITION"
    assert unknown["fallback_family"] == "vfinal"

    unknown_template = audit._map_callback_template("vfinal|tier|future_{*}", evidence, routes)
    assert unknown_template is not None
    assert unknown_template["target"] == "VIDEO_FINALIZATION_SOURCE_REVIEW_REQUIRED"
    assert unknown_template["status"] == "NEEDS_FEATURE_DISPOSITION"

    bot_root = tmp_path / "bot"
    web_root = tmp_path / "web"
    bot_root.mkdir()
    web_root.mkdir()
    (bot_root / "bot.py").write_text(
        '''
InlineKeyboardButton("Review", callback_data="vfinal|review")
InlineKeyboardButton("Export", callback_data="vfinal|export_ai")
InlineKeyboardButton("Voice", callback_data="vfinal|voice_lang|vi")
tier = "basic"
InlineKeyboardButton("Tier", callback_data=f"vfinal|tier|{tier}")
''',
        encoding="utf-8",
    )
    (web_root / "app.py").write_text(
        '''
app = FastAPI()
@app.get("/video/finishing")
async def video_finishing():
    return {}
@app.get("/{page_path:path}")
async def page(page_path):
    return {}
''',
        encoding="utf-8",
    )

    result = audit.run_audit(bot_root, web_root, "baseline", tmp_path / "reports", tmp_path / "docs")
    callbacks = {item["source"]: item for item in result["parity_gap"]["callback_mappings"]}
    assert all(
        callbacks[source]["target"] == "TELEGRAM_ONLY"
        and callbacks[source]["status"] == "TELEGRAM_ONLY"
        for source in reviewed[:-1]
    )
    templates = {item["source"]: item for item in result["parity_gap"]["callback_template_mappings"]}
    assert templates["vfinal|tier|{*}"]["target"] == "TELEGRAM_ONLY"
    assert "vfinal" not in {
        item["family"] for item in result["parity_gap"]["feature_disposition_backlog"]
    }
    contract = (tmp_path / "docs" / "VIDEO_FINALIZATION_CALLBACK_CONTRACT.md").read_text(encoding="utf-8")
    assert "vfinal\\|export_ai" in contract
    assert "vfinal\\|tier\\|{*}" in contract
    assert "VIDEO_FINALIZATION_SOURCE_REVIEW_REQUIRED" in contract
    assert "VIDEO_FINALIZATION_CALLBACK_CONTRACT.md" in (tmp_path / "docs" / "README.md").read_text(encoding="utf-8")
    assert "Bot Video Finishing callbacks remain Telegram-only" in (
        tmp_path / "docs" / "PAYOS_WALLET_JOB_MAP.md"
    ).read_text(encoding="utf-8")


def test_static_audit_maps_reviewed_dynamic_callback_namespaces_without_resolving_ids() -> None:
    audit = _load_audit_module()
    routes = {"/{page_path:path}"}
    expected = {
        "ticket|reply|{*}": "/support",
        "pipe|stage|review|{*}": "/workboard",
        "storyboard|mode_ai|{*}": "/video-studio/storyboard-composer",
        "videodub|type|{*}": "/dubbing",
        "videoaddon|export|{*}": "/video/add-ons",
    }
    for template, target in expected.items():
        mapped = audit._map_callback_template(template, {"file": "bot.py", "line": 1}, routes)
        assert mapped is not None
        assert mapped["source_kind"] == "callback_template"
        assert mapped["source"] == template
        assert mapped["target"] == target
        assert mapped["status"] == "COPIED_GUARDED"
        assert mapped["resolution"] == "reviewed_namespace_compatibility_route"

    assert not any(prefix == "shopai|" for prefix, *_ in audit.DYNAMIC_CALLBACK_TEMPLATE_ROUTE_OVERRIDES)
    for template in sorted(audit.SHOPAI_CANONICAL_TELEGRAM_ONLY_CALLBACK_TEMPLATES):
        mapped = audit._map_callback_template(template, {"file": "bot.py", "line": 1}, routes)
        assert mapped is not None
        assert mapped["target"] == "TELEGRAM_ONLY"
        assert mapped["status"] == "TELEGRAM_ONLY"
        assert mapped["resolution"] == "bot_shopai_confirmation_requires_canonical_bot_state"
        assert "CANONICAL_SHOPAI_XU_PROVIDER_JOB_OR_PAYMENT_BOUNDARY" in mapped["source_dispositions"]

    for template in sorted(audit.MEMORY_RECORD_TELEGRAM_ONLY_CALLBACK_TEMPLATES):
        mapped = audit._map_callback_template(template, {"file": "bot.py", "line": 1}, routes)
        assert mapped is not None
        assert mapped["target"] == "TELEGRAM_ONLY"
        assert mapped["status"] == "TELEGRAM_ONLY"
        assert mapped["resolution"] == "bot_memory_record_identifier_requires_telegram_context"
        assert "BOT_MEMORY_NOTE_IDENTIFIER" in mapped["source_dispositions"]

    unreviewed_memory = audit._map_callback_template("memory|new_action|{*}", {"file": "bot.py", "line": 1}, routes)
    assert unreviewed_memory is not None
    assert unreviewed_memory["target"] == "BOT_MEMORY_SOURCE_REVIEW_REQUIRED"
    assert unreviewed_memory["status"] == "NEEDS_FEATURE_DISPOSITION"
    assert unreviewed_memory["resolution"] == "memory_callback_template_requires_source_review"

    admin = audit._map_callback_template("archive|dept|{*}", {"file": "bot.py", "line": 1}, routes)
    assert admin is not None
    assert admin["classification"] == "admin"
    assert admin["target"] == "ADMIN_INTERNAL_DOCUMENT_ARCHIVE_SOURCE_REVIEW_REQUIRED"
    assert admin["status"] == "NEEDS_FEATURE_DISPOSITION"
    assert admin["resolution"] == "archive_callback_requires_source_review"

    for template in ("trend|video|{*}", "manual|approve_expected|{*}", "adconcept|admin_video_smoke|{*}"):
        bot_only = audit._map_callback_template(template, {"file": "bot.py", "line": 1}, routes)
        assert bot_only is not None
        assert bot_only["classification"] == "admin"
        assert bot_only["target"] == "TELEGRAM_ONLY"
        assert bot_only["status"] == "TELEGRAM_ONLY"

    # A variable prefix has no fixed namespace. The audit must not guess that
    # it is a save/action from any one Bot workflow.
    assert audit._map_callback_template("{*}|save", {"file": "bot.py", "line": 1}, routes) is None


def test_static_audit_maps_frozen_quick_image_draft_but_keeps_tier_and_checkout_telegram_only(tmp_path: Path) -> None:
    """Quick Image draft grammar is Web-native; canonical execution never is."""

    audit = _load_audit_module()
    routes = {"/image/quick-planner", "/{page_path:path}"}
    evidence = {"file": "bot.py", "line": 1}

    for token in sorted(audit.QUICK_IMAGE_PLANNER_FRESH_WEB_CALLBACKS):
        mapped = audit._map_callback(token, "callback_data", evidence, routes)
        assert mapped["target"] == "/image/quick-planner"
        assert mapped["classification"] == "customer"
        assert mapped["status"] == "MAPPED_TO_EXISTING_ROUTE"
        assert mapped["resolution"] == "reviewed_quick_image_planner_fresh_web_draft"
        assert mapped["quick_image_planner_authority"] == "SIGNED_CUSTOMER_WEB_NATIVE_DRAFT_ONLY"
        assert "BOT_QUICK_IMAGE_CONVERSATION_STATE_NOT_REPLAYED" in mapped["source_dispositions"]

    for position in sorted(audit.QUICK_IMAGE_LOGO_POSITION_VALUES):
        mapped = audit._map_callback(f"create_media|qi_logo_pos|{position}", "callback_data", evidence, routes)
        assert mapped["target"] == "/image/quick-planner"
        assert mapped["status"] == "MAPPED_TO_EXISTING_ROUTE"

    for template in sorted(audit.QUICK_IMAGE_PLANNER_FRESH_WEB_CALLBACK_TEMPLATES):
        mapped = audit._map_callback_template(template, evidence, routes)
        assert mapped is not None
        assert mapped["target"] == "/image/quick-planner"
        assert mapped["status"] == "MAPPED_TO_EXISTING_ROUTE"

    for token in sorted(audit.QUICK_IMAGE_PLANNER_TELEGRAM_ONLY_CALLBACKS):
        mapped = audit._map_callback(token, "callback_data", evidence, routes)
        assert mapped["target"] == "TELEGRAM_ONLY"
        assert mapped["status"] == "TELEGRAM_ONLY"
        assert "CANONICAL_SHOPAI_XU_JOB_OR_PAYMENT_BOUNDARY" in mapped["source_dispositions"]
    for template in sorted(audit.QUICK_IMAGE_PLANNER_TELEGRAM_ONLY_CALLBACK_TEMPLATES):
        mapped = audit._map_callback_template(template, evidence, routes)
        assert mapped is not None
        assert mapped["target"] == "TELEGRAM_ONLY"
        assert mapped["status"] == "TELEGRAM_ONLY"

    for token in (
        "CREATE_MEDIA|QUICK_IMAGE",
        "create_media|quick_image|future",
        "CREATE_MEDIA|QUICK_IMAGE|future",
        "create_media|quick_image_extra",
        "create_media|QI_ENTRY",
        "create_media|qi_logo_pos|not_frozen",
        "create_media|qi_future",
    ):
        mapped = audit._map_callback(token, "callback_data", evidence, routes)
        assert mapped["target"] == "QUICK_IMAGE_PLANNER_SOURCE_REVIEW_REQUIRED"
        assert mapped["status"] == "NEEDS_FEATURE_DISPOSITION"
        assert mapped["resolution"] == "quick_image_planner_callback_requires_exact_source_review"
        assert "NO_TELEGRAM_STATE_OR_WEB_DRAFT_REPLAY" in mapped["source_dispositions"]

    for template in (
        "CREATE_MEDIA|QI_RATIO_{*}",
        "create_media|quick_image|future_{*}",
        "create_media|QI_TIER_{*}",
        "create_media|qi_unknown_{*}",
    ):
        mapped = audit._map_callback_template(template, evidence, routes)
        assert mapped is not None
        assert mapped["target"] == "QUICK_IMAGE_PLANNER_SOURCE_REVIEW_REQUIRED"
        assert mapped["status"] == "NEEDS_FEATURE_DISPOSITION"
        assert mapped["resolution"] == "quick_image_planner_callback_requires_exact_source_review"

    bot_root = tmp_path / "bot"
    bot_root.mkdir()
    bot_source = bot_root / "bot.py"
    bot_source.write_text(
        '''
def media_logo_watermark_position_keyboard(kind, lang, action_prefix, back_callback):
    InlineKeyboardButton("top left", callback_data=f"create_media|{action_prefix}|top_left")
    InlineKeyboardButton("center", callback_data=f"create_media|{action_prefix}|center")
    InlineKeyboardButton("bottom right", callback_data=f"create_media|{action_prefix}|bottom_right")

def quick_image_logo_position_keyboard(lang="vi"):
    return media_logo_watermark_position_keyboard("image", lang, "qi_logo_pos", "create_media|qi_logo_add")
''',
        encoding="utf-8",
    )
    inventory = audit._extract_python_inventory(bot_root, [bot_source])
    derived = {item["token"] for item in inventory["callback_data"]}
    assert {
        "create_media|qi_logo_pos|top_left",
        "create_media|qi_logo_pos|center",
        "create_media|qi_logo_pos|bottom_right",
    } <= derived
    raw_templates = {item["template"]: item for item in inventory["callback_templates"]}
    assert raw_templates["create_media|{*}|top_left"]["resolution"] == "reviewed_quick_image_logo_position_helper_calls"

    web_root = tmp_path / "web"
    web_root.mkdir()
    (web_root / "app.py").write_text(
        '''
app = FastAPI()
@app.get("/image/quick-planner")
async def quick_image_planner():
    return {}
''',
        encoding="utf-8",
    )
    result = audit.run_audit(bot_root, web_root, "baseline", tmp_path / "reports", tmp_path / "docs")
    template_mappings = {
        item["source"]: item for item in result["parity_gap"]["callback_template_mappings"]
    }
    assert template_mappings["create_media|{*}|top_left"]["target"] == "/image/quick-planner"
    contract = (tmp_path / "docs" / "QUICK_IMAGE_PLANNER_CALLBACK_CONTRACT.md").read_text(encoding="utf-8")
    assert "qi_logo_pos" in contract
    assert "TELEGRAM_ONLY" in contract
    assert "QUICK_IMAGE_PLANNER_SOURCE_REVIEW_REQUIRED" in contract
    assert "exact lowercase frozen literals" in contract
    assert "QUICK_IMAGE_PLANNER_CALLBACK_CONTRACT.md" in (tmp_path / "docs" / "README.md").read_text(encoding="utf-8")


def test_static_audit_keeps_shopai_confirmation_state_out_of_web_topup(tmp_path: Path) -> None:
    """ShopAI opaque tokens are Bot-only confirmation/billing state, never top-up routes."""

    audit = _load_audit_module()
    routes = {"/wallet/topup", "/{page_path:path}"}
    evidence = {"file": "bot.py", "line": 1}

    assert not any(prefix == "shopai|" for prefix, *_ in audit.DYNAMIC_CALLBACK_TEMPLATE_ROUTE_OVERRIDES)
    assert audit.SHOPAI_CANONICAL_TELEGRAM_ONLY_CALLBACK_TEMPLATES == {
        "shopai|confirm|{*}",
        "shopai|package|{*}",
        "shopai|cancel|{*}",
    }
    for template in sorted(audit.SHOPAI_CANONICAL_TELEGRAM_ONLY_CALLBACK_TEMPLATES):
        mapped = audit._map_callback_template(template, evidence, routes)
        assert mapped is not None
        assert mapped["target"] == "TELEGRAM_ONLY"
        assert mapped["status"] == "TELEGRAM_ONLY"
        assert mapped["resolution"] == "bot_shopai_confirmation_requires_canonical_bot_state"
        assert "BOT_SHOPAI_CONFIRMATION_TOKEN_STATE" in mapped["source_dispositions"]
        assert "NO_WEB_NAVIGATION_OR_BROWSER_ACTION" in mapped["source_dispositions"]

    for identifier in (
        "shopai|confirm",
        "shopai|cancel",
        "shopai|confirm|opaque",
        "shopai|package|opaque",
        "shopai|cancel|opaque",
        "SHOPAI|CONFIRM|opaque",
        "shopai|future|opaque",
    ):
        mapped = audit._map_callback(identifier, "callback_data", evidence, routes)
        assert mapped["target"] == "SHOPAI_SOURCE_REVIEW_REQUIRED"
        assert mapped["status"] == "NEEDS_FEATURE_DISPOSITION"
        assert mapped["resolution"] == "shopai_callback_requires_exact_source_review"
        assert "NO_PROVIDER_JOB_WALLET_PAYMENT_OR_DELIVERY_ACTION" in mapped["source_dispositions"]

    for template in (
        "SHOPAI|CONFIRM|{*}",
        "shopai|package|future_{*}",
        "shopai|cancel|future_{*}",
        "shopai|future|{*}",
    ):
        mapped = audit._map_callback_template(template, evidence, routes)
        assert mapped is not None
        assert mapped["target"] == "SHOPAI_SOURCE_REVIEW_REQUIRED"
        assert mapped["status"] == "NEEDS_FEATURE_DISPOSITION"
        assert mapped["resolution"] == "shopai_callback_requires_exact_source_review"

    bot_root = tmp_path / "bot"
    bot_root.mkdir()
    (bot_root / "bot.py").write_text(
        '''
def shopai_keyboard(token):
    InlineKeyboardButton("confirm", callback_data=f"shopai|confirm|{token}")
    InlineKeyboardButton("package", callback_data=f"shopai|package|{token}")
    InlineKeyboardButton("cancel", callback_data=f"shopai|cancel|{token}")
''',
        encoding="utf-8",
    )
    web_root = tmp_path / "web"
    web_root.mkdir()
    (web_root / "app.py").write_text("app = FastAPI()\n", encoding="utf-8")
    result = audit.run_audit(bot_root, web_root, "baseline", tmp_path / "reports", tmp_path / "docs")
    mappings = {item["source"]: item for item in result["parity_gap"]["callback_template_mappings"]}
    assert all(mappings[template]["target"] == "TELEGRAM_ONLY" for template in audit.SHOPAI_CANONICAL_TELEGRAM_ONLY_CALLBACK_TEMPLATES)
    contract = (tmp_path / "docs" / "SHOPAI_CALLBACK_CONTRACT.md").read_text(encoding="utf-8")
    assert "shopai\\|cancel\\|{*}" in contract
    assert "SHOPAI_SOURCE_REVIEW_REQUIRED" in contract
    assert "SHOPAI_CALLBACK_CONTRACT.md" in (tmp_path / "docs" / "README.md").read_text(encoding="utf-8")
    assert "ShopAI confirmation/package/cancel" in (tmp_path / "docs" / "PAYOS_WALLET_JOB_MAP.md").read_text(encoding="utf-8")


def test_static_audit_keeps_shopai_video_job_callbacks_out_of_web_routes(tmp_path: Path) -> None:
    """Canonical Bot video-job task IDs must never become browser workflow inputs."""

    audit = _load_audit_module()
    routes = {"/wallet/topup", "/jobs", "/features/video", "/{page_path:path}"}
    evidence = {"file": "bot.py", "line": 1}

    assert not any(prefix == "shopai_video_job|" for prefix, *_ in audit.DYNAMIC_CALLBACK_TEMPLATE_ROUTE_OVERRIDES)
    assert audit.SHOPAI_VIDEO_JOB_TELEGRAM_ONLY_CALLBACKS == {"shopai_video_job|main"}
    assert audit.SHOPAI_VIDEO_JOB_TELEGRAM_ONLY_CALLBACK_TEMPLATES == {
        "shopai_video_job|{*}",
        "shopai_video_job|status|{*}",
        "shopai_video_job|retry|{*}",
    }

    for identifier in sorted(audit.SHOPAI_VIDEO_JOB_TELEGRAM_ONLY_CALLBACKS):
        mapped = audit._map_callback(identifier, "callback_data", evidence, routes)
        assert mapped["target"] == "TELEGRAM_ONLY"
        assert mapped["status"] == "TELEGRAM_ONLY"
        assert mapped["resolution"] == "bot_shopai_video_job_requires_canonical_bot_state"
        assert "NO_WEB_NAVIGATION_OR_BROWSER_ACTION" in mapped["source_dispositions"]

    for template in sorted(audit.SHOPAI_VIDEO_JOB_TELEGRAM_ONLY_CALLBACK_TEMPLATES):
        mapped = audit._map_callback_template(template, evidence, routes)
        assert mapped is not None
        assert mapped["target"] == "TELEGRAM_ONLY"
        assert mapped["status"] == "TELEGRAM_ONLY"
        assert mapped["resolution"] == "bot_shopai_video_job_requires_canonical_bot_state"
        assert "CANONICAL_BOT_PROVIDER_POLL_DELIVERY_AND_BILLING_BOUNDARY" in mapped["source_dispositions"]

    for identifier in (
        "SHOPAI_VIDEO_JOB|MAIN",
        "shopai_video_job|",
        "shopai_video_job|opaque-task",
        "shopai_video_job|status",
        "shopai_video_job|status|opaque-task|future",
        "shopai_video_job|retry|opaque-job",
        "shopai_video_job|future|opaque",
    ):
        mapped = audit._map_callback(identifier, "callback_data", evidence, routes)
        assert mapped["target"] == "SHOPAI_VIDEO_JOB_SOURCE_REVIEW_REQUIRED"
        assert mapped["status"] == "NEEDS_FEATURE_DISPOSITION"
        assert mapped["resolution"] == "shopai_video_job_callback_requires_exact_source_review"
        assert "NO_PROVIDER_JOB_WALLET_PAYMENT_OR_DELIVERY_ACTION" in mapped["source_dispositions"]

    for template in (
        "SHOPAI_VIDEO_JOB|{*}",
        "shopai_video_job|status|future_{*}",
        "shopai_video_job|retry|{*}|future",
        "shopai_video_job|future|{*}",
    ):
        mapped = audit._map_callback_template(template, evidence, routes)
        assert mapped is not None
        assert mapped["target"] == "SHOPAI_VIDEO_JOB_SOURCE_REVIEW_REQUIRED"
        assert mapped["status"] == "NEEDS_FEATURE_DISPOSITION"
        assert mapped["resolution"] == "shopai_video_job_callback_requires_exact_source_review"

    bot_root = tmp_path / "bot"
    bot_root.mkdir()
    (bot_root / "bot.py").write_text(
        '''
def shopai_video_job_keyboard(task_id, job_id):
    InlineKeyboardButton("check", callback_data=f"shopai_video_job|{task_id}")
    InlineKeyboardButton("status", callback_data=f"shopai_video_job|status|{task_id}")
    InlineKeyboardButton("retry", callback_data=f"shopai_video_job|retry|{job_id}")
    InlineKeyboardButton("main", callback_data="shopai_video_job|main")
''',
        encoding="utf-8",
    )
    web_root = tmp_path / "web"
    web_root.mkdir()
    (web_root / "app.py").write_text("app = FastAPI()\n", encoding="utf-8")
    result = audit.run_audit(bot_root, web_root, "baseline", tmp_path / "reports", tmp_path / "docs")
    templates = {item["source"]: item for item in result["parity_gap"]["callback_template_mappings"]}
    assert all(templates[template]["target"] == "TELEGRAM_ONLY" for template in audit.SHOPAI_VIDEO_JOB_TELEGRAM_ONLY_CALLBACK_TEMPLATES)
    callbacks = {item["source"]: item for item in result["parity_gap"]["callback_mappings"]}
    assert callbacks["shopai_video_job|main"]["target"] == "TELEGRAM_ONLY"
    contract = (tmp_path / "docs" / "SHOPAI_VIDEO_JOB_CALLBACK_CONTRACT.md").read_text(encoding="utf-8")
    assert "shopai_video_job\\|retry\\|{*}" in contract
    assert "SHOPAI_VIDEO_JOB_SOURCE_REVIEW_REQUIRED" in contract
    assert "SHOPAI_VIDEO_JOB_CALLBACK_CONTRACT.md" in (tmp_path / "docs" / "README.md").read_text(encoding="utf-8")
    assert "ShopAI Video Job status/main/retry" in (tmp_path / "docs" / "PAYOS_WALLET_JOB_MAP.md").read_text(encoding="utf-8")


def test_static_audit_keeps_manual_payment_callbacks_out_of_web_routes(tmp_path: Path) -> None:
    """Telegram bill/deposit IDs must never become browser wallet inputs."""

    audit = _load_audit_module()
    routes = {"/wallet/topup", "/wallet/history", "/admin/payments", "/{page_path:path}"}
    evidence = {"file": "bot.py", "line": 1}

    assert not any(prefix == "manual|" for prefix, *_ in audit.DYNAMIC_CALLBACK_TEMPLATE_ROUTE_OVERRIDES)
    assert audit.MANUAL_PAYMENT_CUSTOMER_TELEGRAM_ONLY_CALLBACK_TEMPLATES == {
        "manual|start|{*}|{*}",
        "manual|currency|{*}|{*}",
        "manual|currency|VND|{*}",
        "manual|currency|USD|{*}",
        "manual|currency|CNY|{*}",
        "manual|history|{*}",
        "manual|vndamount|{*}|{*}",
        "manual|menu|{*}",
        "manual|method|{*}|{*}",
        "manual|fxamount|{*}|{*}|{*}",
        "manual|fxcustom|{*}|{*}",
        "manual|fxmethod|{*}|{*}|{*}|{*}",
        "manual|fxmethod|CNY|{*}|momo_tuithantai|{*}",
        "manual|fxmethod|CNY|{*}|usdt_trc20|{*}",
        "manual|fxmethod|CNY|{*}|zalopay_merchant|{*}",
        "manual|fxmethod|CNY|{*}|zalopay_personal|{*}",
        "manual|fxmethod|USD|{*}|usdt_trc20|{*}",
        "manual|await_bill|{*}",
    }
    assert audit.MANUAL_PAYMENT_ADMIN_TELEGRAM_ONLY_CALLBACK_TEMPLATES == {
        "manual|approve|{*}",
        "manual|approve_expected|{*}",
        "manual|approve_custom|{*}",
        "manual|reject|{*}",
        "manual|confirm|{*}|{*}",
    }

    for template in sorted(audit.MANUAL_PAYMENT_CUSTOMER_TELEGRAM_ONLY_CALLBACK_TEMPLATES):
        mapped = audit._map_callback_template(template, evidence, routes)
        assert mapped is not None
        assert mapped["target"] == "TELEGRAM_ONLY"
        assert mapped["classification"] == "customer"
        assert mapped["status"] == "TELEGRAM_ONLY"
        assert mapped["resolution"] == "bot_manual_payment_requires_canonical_bot_state"
        assert "TELEGRAM_IDENTITY_CONTEXT" in mapped["source_dispositions"]
        assert "NO_WEB_NAVIGATION_OR_BROWSER_ACTION" in mapped["source_dispositions"]

    for template in sorted(audit.MANUAL_PAYMENT_ADMIN_TELEGRAM_ONLY_CALLBACK_TEMPLATES):
        mapped = audit._map_callback_template(template, evidence, routes)
        assert mapped is not None
        assert mapped["target"] == "TELEGRAM_ONLY"
        assert mapped["classification"] == "admin"
        assert mapped["status"] == "TELEGRAM_ONLY"
        assert mapped["resolution"] == "bot_manual_payment_requires_canonical_bot_state"
        assert "CANONICAL_BOT_WALLET_LEDGER_OR_PAYMENT_APPROVAL" in mapped["source_dispositions"]

    for identifier in (
        "manual|",
        "manual|history|123456",
        "manual|await_bill|123456",
        "manual|confirm|17|100",
        "manual|future|opaque",
        "MANUAL|HISTORY|123456",
        "manual|reject|17|future",
    ):
        mapped = audit._map_callback(identifier, "callback_data", evidence, routes)
        assert mapped["target"] == "MANUAL_PAYMENT_SOURCE_REVIEW_REQUIRED"
        assert mapped["status"] == "NEEDS_FEATURE_DISPOSITION"
        assert mapped["resolution"] == "manual_payment_callback_requires_exact_source_review"
        assert "NO_PROVIDER_PAYMENT_OR_LEDGER_ACTION" in mapped["source_dispositions"]

    for template in (
        "MANUAL|HISTORY|{*}",
        "manual|history|{*}|future",
        "manual|confirm|{*}|{*}|future",
        "manual|future|{*}",
    ):
        mapped = audit._map_callback_template(template, evidence, routes)
        assert mapped is not None
        assert mapped["target"] == "MANUAL_PAYMENT_SOURCE_REVIEW_REQUIRED"
        assert mapped["status"] == "NEEDS_FEATURE_DISPOSITION"
        assert mapped["resolution"] == "manual_payment_callback_requires_exact_source_review"

    bot_root = tmp_path / "bot"
    bot_root.mkdir()
    (bot_root / "bot.py").write_text(
        '''
def manual_keyboard(pkg_key, uid, currency, amount, method, deposit_id, expected_xu):
    InlineKeyboardButton("start", callback_data=f"manual|start|{pkg_key}|{uid}")
    InlineKeyboardButton("history", callback_data=f"manual|history|{uid}")
    InlineKeyboardButton("method", callback_data=f"manual|method|{method}|{uid}")
    InlineKeyboardButton("await", callback_data=f"manual|await_bill|{uid}")
    InlineKeyboardButton("approve", callback_data=f"manual|approve_expected|{deposit_id}")
    InlineKeyboardButton("confirm", callback_data=f"manual|confirm|{deposit_id}|{expected_xu}")
''',
        encoding="utf-8",
    )
    web_root = tmp_path / "web"
    web_root.mkdir()
    (web_root / "app.py").write_text("app = FastAPI()\n", encoding="utf-8")
    result = audit.run_audit(bot_root, web_root, "baseline", tmp_path / "reports", tmp_path / "docs")
    templates = {item["source"]: item for item in result["parity_gap"]["callback_template_mappings"]}
    assert templates["manual|start|{*}|{*}"]["target"] == "TELEGRAM_ONLY"
    assert templates["manual|history|{*}"]["target"] == "TELEGRAM_ONLY"
    assert templates["manual|confirm|{*}|{*}"]["target"] == "TELEGRAM_ONLY"
    contract = (tmp_path / "docs" / "MANUAL_PAYMENT_CALLBACK_CONTRACT.md").read_text(encoding="utf-8")
    assert "manual\\|await_bill\\|{*}" in contract
    assert "MANUAL_PAYMENT_SOURCE_REVIEW_REQUIRED" in contract
    assert "MANUAL_PAYMENT_CALLBACK_CONTRACT.md" in (tmp_path / "docs" / "README.md").read_text(encoding="utf-8")
    assert "Manual payment callback" in (tmp_path / "docs" / "PAYOS_WALLET_JOB_MAP.md").read_text(encoding="utf-8")


def test_static_audit_keeps_provider_choice_callbacks_out_of_web_routes(tmp_path: Path) -> None:
    """Telegram pending/provider callbacks must never become browser actions."""

    audit = _load_audit_module()
    routes = {"/image", "/voice-vault", "/wallet/topup", "/{page_path:path}"}
    evidence = {"file": "bot.py", "line": 1}

    assert not any(prefix == "prov|" for prefix, *_ in audit.DYNAMIC_CALLBACK_TEMPLATE_ROUTE_OVERRIDES)
    assert audit.PROVIDER_CHOICE_TELEGRAM_ONLY_CALLBACK_TEMPLATES == {
        "prov|voice|paid|{*}",
        "prov|voice|free|{*}",
        "prov|image|paid|{*}",
        "prov|image|free|{*}",
        "prov|cancel|cancel|{*}",
    }

    for template in sorted(audit.PROVIDER_CHOICE_TELEGRAM_ONLY_CALLBACK_TEMPLATES):
        mapped = audit._map_callback_template(template, evidence, routes)
        assert mapped is not None
        assert mapped["target"] == "TELEGRAM_ONLY"
        assert mapped["classification"] == "customer"
        assert mapped["status"] == "TELEGRAM_ONLY"
        assert mapped["resolution"] == "bot_provider_choice_requires_canonical_pending_state"
        assert "TELEGRAM_IDENTITY_CONTEXT" in mapped["source_dispositions"]
        assert "CANONICAL_BOT_WALLET_CHARGE_REFUND_OR_PAYMENT_BOUNDARY" in mapped["source_dispositions"]
        assert "BOT_PROVIDER_EXECUTION_OUTPUT_AND_DELIVERY_BOUNDARY" in mapped["source_dispositions"]
        assert "NO_WEB_NAVIGATION_OR_BROWSER_ACTION" in mapped["source_dispositions"]

    for identifier in (
        "prov|",
        "prov|voice|paid|123456",
        "prov|voice|free|123456",
        "prov|image|paid|123456",
        "prov|cancel|cancel|123456",
        "prov|future|opaque|123456",
        "PROV|VOICE|PAID|123456",
        "prov|voice|paid|123456|future",
    ):
        mapped = audit._map_callback(identifier, "callback_data", evidence, routes)
        assert mapped["target"] == "PROVIDER_CHOICE_SOURCE_REVIEW_REQUIRED"
        assert mapped["status"] == "NEEDS_FEATURE_DISPOSITION"
        assert mapped["resolution"] == "provider_choice_callback_requires_exact_source_review"
        assert "NO_PROVIDER_JOB_WALLET_PAYMENT_OR_DELIVERY_ACTION" in mapped["source_dispositions"]

    for template in (
        "PROV|VOICE|PAID|{*}",
        "prov|voice|paid|{*}|future",
        "prov|cancel|cancel",
        "prov|future|{*}",
    ):
        mapped = audit._map_callback_template(template, evidence, routes)
        assert mapped is not None
        assert mapped["target"] == "PROVIDER_CHOICE_SOURCE_REVIEW_REQUIRED"
        assert mapped["status"] == "NEEDS_FEATURE_DISPOSITION"
        assert mapped["resolution"] == "provider_choice_callback_requires_exact_source_review"

    bot_root = tmp_path / "bot"
    bot_root.mkdir()
    (bot_root / "bot.py").write_text(
        '''
def provider_keyboard(uid):
    InlineKeyboardButton("voice paid", callback_data=f"prov|voice|paid|{uid}")
    InlineKeyboardButton("voice free", callback_data=f"prov|voice|free|{uid}")
    InlineKeyboardButton("image paid", callback_data=f"prov|image|paid|{uid}")
    InlineKeyboardButton("image free", callback_data=f"prov|image|free|{uid}")
    InlineKeyboardButton("cancel", callback_data=f"prov|cancel|cancel|{uid}")
''',
        encoding="utf-8",
    )
    web_root = tmp_path / "web"
    web_root.mkdir()
    (web_root / "app.py").write_text("app = FastAPI()\n", encoding="utf-8")
    result = audit.run_audit(bot_root, web_root, "baseline", tmp_path / "reports", tmp_path / "docs")
    templates = {item["source"]: item for item in result["parity_gap"]["callback_template_mappings"]}
    for template in audit.PROVIDER_CHOICE_TELEGRAM_ONLY_CALLBACK_TEMPLATES:
        assert templates[template]["target"] == "TELEGRAM_ONLY"
        assert templates[template]["status"] == "TELEGRAM_ONLY"
    contract = (tmp_path / "docs" / "PROVIDER_CHOICE_CALLBACK_CONTRACT.md").read_text(encoding="utf-8")
    assert "prov\\|cancel\\|cancel\\|{*}" in contract
    assert "PROVIDER_CHOICE_SOURCE_REVIEW_REQUIRED" in contract
    assert "PROVIDER_CHOICE_CALLBACK_CONTRACT.md" in (tmp_path / "docs" / "README.md").read_text(encoding="utf-8")
    assert "Provider choice stays a Bot handoff" in (tmp_path / "docs" / "PAYOS_WALLET_JOB_MAP.md").read_text(encoding="utf-8")


def test_media_creator_cancel_is_exactly_telegram_only_without_a_web_reset_or_navigation(tmp_path: Path) -> None:
    """The broad Bot pending-state clear must never become a browser cancel."""

    audit = _load_audit_module()
    routes = {"/media-factory", "/{page_path:path}"}
    evidence = {"file": "bot.py", "line": 1}
    expected = {"create_media|cancel"}
    assert set(audit.MEDIA_CREATOR_CANCEL_TELEGRAM_ONLY_CALLBACKS) == expected

    mapped = audit._map_callback("create_media|cancel", "callback_data", evidence, routes)
    assert mapped["target"] == "TELEGRAM_ONLY"
    assert mapped["classification"] == "customer"
    assert mapped["status"] == "TELEGRAM_ONLY"
    assert mapped["resolution"] == "reviewed_media_creator_cancel_requires_bot_local_pending_state"
    for disposition in (
        "TELEGRAM_CALLBACK_CONTEXT",
        "BOT_MEDIA_CREATOR_BROAD_PENDING_STATE_CLEARING",
        "BOT_SHOPAI_CONFIRMATION_TOKEN_STATE",
        "BOT_PENDING_CONTEXT_NOT_REPLAYED",
        "TELEGRAM_MESSAGE_REPLACEMENT",
        "NO_WEB_GLOBAL_DRAFT_SESSION_OR_HISTORY_RESET",
        "NO_WEB_NAVIGATION_OR_BROWSER_ACTION",
        "NO_BOT_OR_WEB_JOB_CANCELLATION_REPLAY",
        "NO_JOB_WALLET_PAYMENT_PROVIDER_OR_DELIVERY_ACTION",
        "NO_RUNTIME_CLAIM",
    ):
        assert disposition in mapped["source_dispositions"]

    # The Bot payload is exact and case-sensitive. Variants cannot inherit the
    # Bot-only cancel mapping or turn it into a browser reset/navigation action.
    for token in ("CREATE_MEDIA|CANCEL", "create_media|cancel_future"):
        unknown = audit._map_callback(token, "callback_data", evidence, routes)
        assert unknown["target"] == "MEDIA_CREATOR_CANCEL_SOURCE_REVIEW_REQUIRED"
        assert unknown["status"] == "NEEDS_FEATURE_DISPOSITION"
        assert unknown["resolution"] == "media_creator_cancel_callback_requires_source_review"
        assert "NO_WEB_NAVIGATION_OR_BROWSER_ACTION" in unknown["source_dispositions"]
    template_variant = audit._map_callback_template("CREATE_MEDIA|CANCEL", evidence, routes)
    assert template_variant is not None
    assert template_variant["target"] == "MEDIA_CREATOR_CANCEL_SOURCE_REVIEW_REQUIRED"
    assert template_variant["status"] == "NEEDS_FEATURE_DISPOSITION"
    assert template_variant["resolution"] == "media_creator_cancel_callback_requires_source_review"

    bot_root = tmp_path / "bot"
    bot_root.mkdir()
    (bot_root / "bot.py").write_text(
        'InlineKeyboardButton("Cancel", callback_data="create_media|cancel")\n',
        encoding="utf-8",
    )
    web_root = tmp_path / "web"
    web_root.mkdir()
    (web_root / "app.py").write_text('app = FastAPI()\n', encoding="utf-8")
    result = audit.run_audit(bot_root, web_root, "baseline", tmp_path / "reports", tmp_path / "docs")
    callbacks = {item["source"]: item for item in result["parity_gap"]["callback_mappings"]}
    assert callbacks["create_media|cancel"]["target"] == "TELEGRAM_ONLY"
    assert "create_media" not in {
        item["family"] for item in result["parity_gap"]["feature_disposition_backlog"]
    }
    contract = (tmp_path / "docs" / "MEDIA_CREATOR_CANCEL_CALLBACK_CONTRACT.md").read_text(encoding="utf-8")
    assert "create_media|cancel" in contract
    assert "not** a browser cancel, back or reset action" in contract
    assert "MEDIA_CREATOR_CANCEL_CALLBACK_CONTRACT.md" in (tmp_path / "docs" / "README.md").read_text(encoding="utf-8")


def test_static_audit_keeps_residual_media_creator_callbacks_out_of_generic_web_routes(tmp_path: Path) -> None:
    """Residual Media Creator state must never inherit keyword/namespace routes."""

    audit = _load_audit_module()
    routes = {"/media-factory", "/membership", "/features/video", "/{page_path:path}"}
    evidence = {"file": "bot.py", "line": 1}

    assert not any(prefix == "create_media|" for prefix, *_ in audit.DYNAMIC_CALLBACK_TEMPLATE_ROUTE_OVERRIDES)
    for token in (
        "create_media|main",
        "create_media|support",
        "create_media|pricing",
        "create_media|quick_video",
        "create_media|image_tier_low",
        "create_media|video_tier_basic",
        "CREATE_MEDIA|QUICK_VIDEO",
        "create_media|future_action",
    ):
        mapped = audit._map_callback(token, "callback_data", evidence, routes)
        assert mapped["target"] == "MEDIA_CREATOR_SOURCE_REVIEW_REQUIRED"
        assert mapped["status"] == "NEEDS_FEATURE_DISPOSITION"
        assert mapped["resolution"] == "media_creator_callback_requires_source_review"
        assert "NO_WEB_NAVIGATION_OR_BROWSER_ACTION" in mapped["source_dispositions"]
        assert "NO_PROVIDER_JOB_WALLET_PAYMENT_OR_DELIVERY_ACTION" in mapped["source_dispositions"]

    for template in (
        "create_media|image_tier_{*}",
        "create_media|video_tier_{*}",
        "create_media|{*}_add",
        "create_media|{*}_confirm",
        "create_media|{*}_aspect_{*}",
        "CREATE_MEDIA|VIDEO_TIER_{*}",
        "create_media|future_{*}",
    ):
        mapped = audit._map_callback_template(template, evidence, routes)
        assert mapped is not None
        assert mapped["target"] == "MEDIA_CREATOR_SOURCE_REVIEW_REQUIRED"
        assert mapped["status"] == "NEEDS_FEATURE_DISPOSITION"
        assert mapped["resolution"] == "media_creator_callback_requires_source_review"

    assert audit._map_callback("create_media|quick_image", "callback_data", evidence, routes)["target"] == "/image/quick-planner"
    assert audit._map_callback("create_media|cancel", "callback_data", evidence, routes)["target"] == "TELEGRAM_ONLY"
    assert audit._map_callback_template("create_media|qi_ratio_{*}", evidence, routes)["target"] == "/image/quick-planner"
    assert audit._map_callback_template("create_media|qi_tier_{*}", evidence, routes)["target"] == "TELEGRAM_ONLY"
    assert audit._map_callback_template("create_media|cancel_{*}", evidence, routes)["target"] == "MEDIA_CREATOR_CANCEL_SOURCE_REVIEW_REQUIRED"

    bot_root = tmp_path / "bot"
    bot_root.mkdir()
    (bot_root / "bot.py").write_text(
        '''
def media_creator_keyboard(tier):
    InlineKeyboardButton("Quick video", callback_data="create_media|quick_video")
    InlineKeyboardButton("Image tier", callback_data="create_media|image_tier_low")
    InlineKeyboardButton("Video tier", callback_data=f"create_media|video_tier_{tier}")
''',
        encoding="utf-8",
    )
    web_root = tmp_path / "web"
    web_root.mkdir()
    (web_root / "app.py").write_text("app = FastAPI()\n", encoding="utf-8")
    result = audit.run_audit(bot_root, web_root, "baseline", tmp_path / "reports", tmp_path / "docs")
    callbacks = {item["source"]: item for item in result["parity_gap"]["callback_mappings"]}
    templates = {item["source"]: item for item in result["parity_gap"]["callback_template_mappings"]}
    assert callbacks["create_media|quick_video"]["target"] == "MEDIA_CREATOR_SOURCE_REVIEW_REQUIRED"
    assert callbacks["create_media|image_tier_low"]["target"] == "MEDIA_CREATOR_SOURCE_REVIEW_REQUIRED"
    assert templates["create_media|video_tier_{*}"]["target"] == "MEDIA_CREATOR_SOURCE_REVIEW_REQUIRED"
    fallback = next(item for item in result["parity_gap"]["feature_disposition_backlog"] if item["family"] == "create_media")
    assert fallback["candidate_boundary"] == "MEDIA_CREATOR_SOURCE_REVIEW_REQUIRED"
    assert "NO_WEB_NAVIGATION_OR_BROWSER_ACTION" in fallback["source_dispositions"]
    contract = (tmp_path / "docs" / "MEDIA_CREATOR_CALLBACK_CONTRACT.md").read_text(encoding="utf-8")
    assert "MEDIA_CREATOR_SOURCE_REVIEW_REQUIRED" in contract
    assert "never becomes `/media-factory`" in contract
    assert "MEDIA_CREATOR_CALLBACK_CONTRACT.md" in (tmp_path / "docs" / "README.md").read_text(encoding="utf-8")


def test_static_audit_maps_only_reviewed_archive_literals_to_fresh_admin_navigation() -> None:
    """Archive callbacks never forward Bot state or fall through to keyword routes."""

    audit = _load_audit_module()
    routes = {"/{page_path:path}"}
    evidence = {"file": "bot.py", "line": 1}

    for token in sorted(audit.ARCHIVE_FRESH_WEB_ADMIN_NAVIGATION_ACTIONS):
        mapped = audit._map_callback(token, "callback_data", evidence, routes)
        assert mapped["classification"] == "admin"
        assert mapped["target"] == "/admin/internal-documents"
        assert mapped["status"] == "NAVIGATION_ONLY"
        assert mapped["resolution"] == "reviewed_archive_fresh_admin_navigation"
        assert mapped["archive_authority"] == "SIGNED_CANONICAL_ADMIN_WEB_NATIVE"
        assert mapped["archive_launch_mode"] == "WEB_NAVIGATION"
        assert "BOT_ARCHIVE_SELECTION_STATE_NOT_REPLAYED" in mapped["source_dispositions"]

    tax_invoice = audit._map_callback("archive|dept|tax_invoice", "callback_data", evidence, routes)
    assert tax_invoice["target"] == "/admin/internal-documents"
    assert "voice" not in tax_invoice["target"]

    for token in sorted(audit.ARCHIVE_SOURCE_REVIEW_ACTIONS):
        mapped = audit._map_callback(token, "callback_data", evidence, routes)
        assert mapped["classification"] == "admin"
        assert mapped["target"] == "ADMIN_INTERNAL_DOCUMENT_ARCHIVE_SOURCE_REVIEW_REQUIRED"
        assert mapped["status"] == "NEEDS_FEATURE_DISPOSITION"
        assert mapped["resolution"] == "reviewed_archive_callback_requires_source_review"

    for token in sorted(audit.ARCHIVE_TELEGRAM_ONLY_ACTIONS):
        mapped = audit._map_callback(token, "callback_data", evidence, routes)
        assert mapped["classification"] == "admin"
        assert mapped["target"] == "TELEGRAM_ONLY"
        assert mapped["status"] == "TELEGRAM_ONLY"
        assert mapped["resolution"] == "archive_preview_or_save_requires_telegram_state"

    unreviewed = audit._map_callback("archive|future_record", "callback_data", evidence, routes)
    assert unreviewed["target"] == "ADMIN_INTERNAL_DOCUMENT_ARCHIVE_SOURCE_REVIEW_REQUIRED"
    assert unreviewed["status"] == "NEEDS_FEATURE_DISPOSITION"
    assert unreviewed["resolution"] == "archive_callback_requires_source_review"
    assert not any(prefix == "archive|" for prefix, _target, _classification in audit.DYNAMIC_CALLBACK_TEMPLATE_ROUTE_OVERRIDES)


def test_static_audit_keeps_dashboard_fallbacks_actionable_instead_of_counting_feature_parity(tmp_path: Path) -> None:
    """A route catch-all must not turn unknown Bot flows into a green metric."""

    audit = _load_audit_module()
    bot_root = tmp_path / "bot"
    web_root = tmp_path / "web"
    bot_root.mkdir()
    web_root.mkdir()
    (bot_root / "bot.py").write_text(
        '''
app.add_handler(CommandHandler("start", start_handler))
app.add_handler(CommandHandler("opaque_flow", opaque_handler))
button = InlineKeyboardButton("Video", callback_data="menu|video")
''',
        encoding="utf-8",
    )
    (web_root / "app.py").write_text(
        '''
app = FastAPI()
@app.get('/dashboard')
async def dashboard():
    return {}
@app.get('/{page_path:path}')
async def page(page_path):
    return {}
''',
        encoding="utf-8",
    )

    result = audit.run_audit(bot_root, web_root, "baseline", tmp_path / "reports", tmp_path / "docs")
    gap = result["parity_gap"]
    command_mappings = {item["source"]: item for item in gap["command_mappings"]}
    callback_mappings = {item["source"]: item for item in gap["callback_mappings"]}

    assert command_mappings["/start"]["status"] == "NAVIGATION_ENTRYPOINT"
    assert command_mappings["/start"]["resolution"] == "reviewed_dashboard_navigation_entrypoint"
    assert command_mappings["/opaque_flow"]["status"] == "NEEDS_FEATURE_DISPOSITION"
    assert command_mappings["/opaque_flow"]["resolution"] == "unreviewed_dashboard_fallback_requires_feature_disposition"
    assert callback_mappings["menu|video"]["status"] == "NEEDS_FEATURE_DISPOSITION"
    assert callback_mappings["menu|video"]["resolution"] == "menu_callback_requires_explicit_feature_disposition"
    assert gap["static_web_surface_coverage_percent"] == 0.0
    assert gap["mapping_coverage_percent"] == 33.33
    assert gap["workflow_equivalence"] == {
        "status": "NOT_STATICALLY_VERIFIABLE",
        "verified_mapping_count": 0,
        "coverage_percent": 0.0,
        "note": "This source-only audit can verify route and disposition evidence, not signed runtime behavior, provider execution, billing, job delivery, or owner-scoped output access.",
    }
    fallback_gap = next(item for item in gap["gaps"] if item["area"] == "dashboard_navigation_fallbacks")
    assert fallback_gap["count"] == 2
    backlog = {item["family"]: item for item in gap["feature_disposition_backlog"]}
    assert backlog["menu"] == {
        "family": "menu",
        "priority": "P0",
        "candidate_boundary": "/features",
        "authority": "Web capability catalog",
        "next_contract": "Create an explicit menu-action catalog; never infer a destination from a button label or generic keyword.",
        "count": 1,
        "source_kinds": ["callback_data"],
        "sample_sources": ["menu|video"],
    }
    assert backlog["command:opaque_flow"]["candidate_boundary"] == "source_review_required"
    assert fallback_gap["families"] == [
        {"family": "menu", "priority": "P0", "count": 1},
        {"family": "command:opaque_flow", "priority": "P1", "count": 1},
    ]

    template = audit._map_callback_template("menu|video|{*}", {"file": "bot.py", "line": 1}, {"/{page_path:path}"})
    assert template is not None
    assert template["status"] == "NEEDS_FEATURE_DISPOSITION"
    assert template["target"] == "UNRESOLVED_DYNAMIC_MENU_ACTION"
    assert template["resolution"] == "dynamic_menu_action_requires_finite_catalog"


def test_static_audit_uses_only_the_finite_reviewed_menu_navigation_catalog() -> None:
    """Menu labels/state must never inherit a Web route through a wildcard."""
    audit = _load_audit_module()
    routes = {"/{page_path:path}"}
    expected = {
        "menu|main": ("/dashboard", "workspace_home", "dashboard", "SIGNED_CUSTOMER", "NAVIGATION_SHELL"),
        "menu|back": ("/dashboard", "workspace_home", "dashboard", "SIGNED_CUSTOMER", "NAVIGATION_SHELL"),
        "freehub|main": ("/dashboard", "workspace_home", "dashboard", "SIGNED_CUSTOMER", "NAVIGATION_SHELL"),
        "menu|main_ai": ("/chat", "chat_workspace", "chat", "SIGNED_CUSTOMER_WEB_NATIVE", "WEB_NAVIGATION"),
        "menu|hint_ai_prompt": ("/prompt-studio", "prompt_studio", "prompt_studio", "SIGNED_CUSTOMER_WEB_NATIVE", "WEB_NAVIGATION"),
        "menu|hint_campaign_preset": ("/campaigns", "campaign_planner", "campaign_planner", "SIGNED_CUSTOMER_WEB_NATIVE", "WEB_NAVIGATION"),
        "menu|main_profile": ("/account", "account", "account", "SIGNED_CUSTOMER", "WEB_NAVIGATION"),
        "menu|hint_profile": ("/account", "account", "account", "SIGNED_CUSTOMER", "WEB_NAVIGATION"),
        "menu|main_memory": ("/notes", "memory_center", "notes", "SIGNED_CUSTOMER_WEB_NATIVE", "WEB_NAVIGATION"),
        "menu|hint_note": ("/notes", "memory_center", "notes", "SIGNED_CUSTOMER_WEB_NATIVE", "WEB_NAVIGATION"),
        "menu|hint_search_note": ("/notes", "memory_center", "notes", "SIGNED_CUSTOMER_WEB_NATIVE", "WEB_NAVIGATION"),
        "menu|hint_remind": ("/reminders", "reminder_center", "reminders", "SIGNED_CUSTOMER_WEB_NATIVE", "WEB_NAVIGATION"),
        "freehub|docs": ("/notes", "memory_center", "notes", "SIGNED_CUSTOMER_WEB_NATIVE", "WEB_NAVIGATION"),
        "freehub|notes": ("/notes", "memory_center", "notes", "SIGNED_CUSTOMER_WEB_NATIVE", "WEB_NAVIGATION"),
        "menu|translate": ("/subtitle-studio", "subtitle_studio", "subtitle_studio", "SIGNED_CUSTOMER_WEB_NATIVE", "WEB_NAVIGATION"),
        "menu|translation_language_hub": ("/subtitle-studio", "subtitle_studio", "subtitle_studio", "SIGNED_CUSTOMER_WEB_NATIVE", "WEB_NAVIGATION"),
        "menu|translation_text": ("/subtitle-studio", "subtitle_studio", "subtitle_studio", "SIGNED_CUSTOMER_WEB_NATIVE", "WEB_NAVIGATION"),
        "menu|translation_document": ("/documents", "documents", "documents", "SIGNED_CUSTOMER", "WEB_NAVIGATION"),
        "menu|profile_packages": ("/membership", "membership", "membership", "CORE_CANONICAL_READ", "READ_ONLY_CANONICAL"),
        "menu|main_topup": ("/wallet/topup", "wallet_topup", "wallet_topup", "CORE_CANONICAL_PAYMENT", "BRIDGE_GUARDED_PROXY"),
        "menu|hint_naptien": ("/wallet/topup", "wallet_topup", "wallet_topup", "CORE_CANONICAL_PAYMENT", "BRIDGE_GUARDED_PROXY"),
        "menu|guide_credits": ("/wallet", "wallet", "wallet", "CORE_CANONICAL_READ", "READ_ONLY_CANONICAL"),
        "menu|hint_pricing": ("/pricing", "pricing", "pricing", "SIGNED_CUSTOMER", "WEB_NAVIGATION"),
        "menu|main_docs": ("/documents", "documents", "documents", "SIGNED_CUSTOMER", "WEB_NAVIGATION"),
        "menu|doc_tools": ("/documents", "documents", "documents", "SIGNED_CUSTOMER", "WEB_NAVIGATION"),
        "menu|hint_doc_pdf_to_word": ("/documents/pdf-to-word", "documents_pdf_to_word", "documents_pdf_to_word", "SIGNED_CUSTOMER_WEB_NATIVE", "WEB_NAVIGATION"),
        "menu|hint_doc_image_to_pdf": ("/documents/image-to-pdf", "documents_image_to_pdf", "documents_image_to_pdf", "SIGNED_CUSTOMER_WEB_NATIVE", "WEB_NAVIGATION"),
        "menu|hint_doc_compress_pdf": ("/documents/compress", "documents_compress", "documents_compress", "SIGNED_CUSTOMER_WEB_NATIVE", "WEB_NAVIGATION"),
        "menu|hint_doc_split_pdf": ("/documents/split", "documents_split", "documents_split", "SIGNED_CUSTOMER_WEB_NATIVE", "WEB_NAVIGATION"),
        "menu|hint_doc_merge_pdf": ("/documents/merge", "documents_merge", "documents_merge", "SIGNED_CUSTOMER_WEB_NATIVE", "WEB_NAVIGATION"),
        "menu|hint_doc_save_document": ("/asset-vault", "asset_vault", "asset_vault", "SIGNED_CUSTOMER_WEB_NATIVE", "WEB_NAVIGATION"),
        "menu|main_image": ("/image-studio", "image_studio", "image_studio", "SIGNED_CUSTOMER_WEB_NATIVE", "WEB_NAVIGATION"),
        "menu|hint_image_tools": ("/image-studio", "image_studio", "image_studio", "SIGNED_CUSTOMER_WEB_NATIVE", "WEB_NAVIGATION"),
        "menu|image_prompt_start": ("/image/prompt-composer", "image_prompt_composer", "image_prompt_composer", "SIGNED_CUSTOMER_WEB_NATIVE", "WEB_NAVIGATION"),
        "menu|image_edit_start": ("/image/edit", "image_edit", "image_edit", "SIGNED_CUSTOMER_WEB_NATIVE", "WEB_NAVIGATION"),
        "menu|image_upscale_start": ("/image/upscale", "image_upscale", "image_upscale", "SIGNED_CUSTOMER_WEB_NATIVE", "WEB_NAVIGATION"),
        "menu|main_video": ("/video-studio", "video_studio", "video_studio", "SIGNED_CUSTOMER_WEB_NATIVE", "WEB_NAVIGATION"),
        "menu|main_music": ("/media-workspace", "media_workspace", "media_workspace", "SIGNED_CUSTOMER_WEB_NATIVE", "WEB_NAVIGATION"),
        "menu|main_audio": ("/media-workspace", "media_workspace", "media_workspace", "SIGNED_CUSTOMER_WEB_NATIVE", "WEB_NAVIGATION"),
        "menu|main_guide": ("/guides", "guides", "guides", "SIGNED_CUSTOMER_WEB_NATIVE", "WEB_NAVIGATION"),
        "menu|guide": ("/guides", "guides", "guides", "SIGNED_CUSTOMER_WEB_NATIVE", "WEB_NAVIGATION"),
        "menu|guide_quick_start": ("/features", "guided_start", "feature_catalog", "SIGNED_CUSTOMER_WEB_NATIVE", "WEB_NAVIGATION"),
        "menu|guide_image_ai": ("/image-studio", "image_studio", "image_studio", "SIGNED_CUSTOMER_WEB_NATIVE", "WEB_NAVIGATION"),
        "menu|guide_music_add": ("/media-workspace", "media_workspace", "media_workspace", "SIGNED_CUSTOMER_WEB_NATIVE", "WEB_NAVIGATION"),
        "menu|guide_faq": ("/support", "support", "support", "SIGNED_CUSTOMER", "WEB_NAVIGATION"),
        "menu|support": ("/support", "support", "support", "SIGNED_CUSTOMER", "WEB_NAVIGATION"),
        "menu|create_media": ("/media-factory", "media_factory", "media_factory", "SIGNED_CUSTOMER_WEB_NATIVE", "WEB_NAVIGATION"),
        "menu|video_workflow": ("/video-studio/workflow", "video_factory_workflow", "video_factory_workflow", "SIGNED_CUSTOMER_WEB_NATIVE", "WEB_NAVIGATION"),
        "menu|video_factory_flow": ("/video-studio/workflow", "video_factory_workflow", "video_factory_workflow", "SIGNED_CUSTOMER_WEB_NATIVE", "WEB_NAVIGATION"),
    }
    assert set(audit.MENU_ACTION_REGISTRY) == set(expected)

    for callback, (target, capability, feature, authority, launch_mode) in expected.items():
        mapped = audit._map_callback(callback, "callback_data", {"file": "bot.py", "line": 1}, routes)
        assert mapped["classification"] == "customer"
        assert mapped["target"] == target
        assert mapped["status"] == "NAVIGATION_ONLY"
        expected_resolution = (
            "reviewed_memory_fresh_web_navigation"
            if callback in audit.MEMORY_FRESH_WEB_NAVIGATION_ACTIONS
            else "reviewed_guided_start_fresh_web_navigation"
            if callback in audit.GUIDED_START_FRESH_WEB_NAVIGATION_ACTIONS
            else "reviewed_exact_menu_navigation"
        )
        assert mapped["resolution"] == expected_resolution
        assert mapped["menu_capability_key"] == capability
        assert mapped["menu_feature_key"] == feature
        assert mapped["menu_authority"] == authority
        assert mapped["menu_launch_mode"] == launch_mode

    # The Guide Center is a fresh signed Web catalog, not a replay of the
    # Bot's guide menu, child callbacks or conversation state.
    expected_guide_dispositions = (
        "FRESH_SIGNED_WEB_GUIDE_NAVIGATION",
        "BOT_GUIDE_SECTION_CONTEXT_NOT_REPLAYED",
        "BOT_GUIDE_CHILD_CALLBACKS_NOT_REPLAYED",
        "NO_RUNTIME_CLAIM",
    )
    for callback in ("menu|main_guide", "menu|guide"):
        mapped = audit._map_callback(callback, "callback_data", {"file": "bot.py", "line": 1}, routes)
        assert mapped["source_dispositions"] == expected_guide_dispositions

    # The static audit's private Bot token registry and the browser-safe public
    # catalog must stay in lockstep.  This prevents an audit mapping from
    # claiming a different route, authority or launch semantics than the
    # Web product can actually render.
    from copyfast_registry import menu_capability_catalog

    public_catalog = {item["key"]: item for item in menu_capability_catalog()}
    for descriptor in audit.MENU_ACTION_REGISTRY.values():
        public_entry = public_catalog[descriptor["capability_key"]]
        assert public_entry["feature_key"] == descriptor["feature_key"]
        assert public_entry["route"] == descriptor["target"]
        assert public_entry["authority"] == descriptor["authority"]
        assert public_entry["launch_mode"] == descriptor["launch_mode"]

    # Parent/help actions can open a fresh Web Memory form/list only; no
    # Bot records, pending text/query, or Telegram state travels with them.
    for callback in sorted(audit.MEMORY_FRESH_WEB_NAVIGATION_ACTIONS):
        mapped = audit._map_callback(callback, "callback_data", {"file": "bot.py", "line": 1}, routes)
        descriptor = audit.MEMORY_FRESH_WEB_NAVIGATION_ACTIONS[callback]
        assert mapped["target"] == descriptor["target"]
        assert mapped["status"] == "NAVIGATION_ONLY"
        assert mapped["resolution"] == "reviewed_memory_fresh_web_navigation"
        assert mapped["source_dispositions"] == descriptor["source_dispositions"]
        assert mapped["memory_capability_key"] == descriptor["capability_key"]

    # The Main Guide may only start a fresh catalog or Support Desk. It never
    # transfers a Telegram guide section, FAQ/refund context, child callback,
    # raw Telegram identifier or Bot state into a Web route.
    for callback in sorted(audit.GUIDED_START_FRESH_WEB_NAVIGATION_ACTIONS):
        mapped = audit._map_callback(callback, "callback_data", {"file": "bot.py", "line": 1}, routes)
        descriptor = audit.GUIDED_START_FRESH_WEB_NAVIGATION_ACTIONS[callback]
        assert mapped["target"] == descriptor["target"]
        assert mapped["status"] == "NAVIGATION_ONLY"
        assert mapped["resolution"] == "reviewed_guided_start_fresh_web_navigation"
        assert mapped["source_dispositions"] == descriptor["source_dispositions"]
        assert mapped["guided_start_capability_key"] == descriptor["capability_key"]
        assert mapped["guided_start_feature_key"] == descriptor["feature_key"]
        assert mapped["guided_start_authority"] == descriptor["authority"]
        assert mapped["guided_start_launch_mode"] == descriptor["launch_mode"]

    # Marketing literals can only launch a fresh account-owned Campaign
    # Planner.  No suggestion index, custom brief, selection, campaign ID,
    # Bot save/schedule receipt or Telegram state becomes a browser value.
    for callback in sorted(audit.MARKETING_FRESH_WEB_NAVIGATION_ACTIONS):
        mapped = audit._map_callback(callback, "callback_data", {"file": "bot.py", "line": 1}, routes)
        descriptor = audit.MARKETING_FRESH_WEB_NAVIGATION_ACTIONS[callback]
        assert mapped["target"] == "/campaigns"
        assert mapped["status"] == "NAVIGATION_ONLY"
        assert mapped["resolution"] == "reviewed_marketing_fresh_web_navigation"
        assert mapped["source_dispositions"] == descriptor["source_dispositions"]
        assert mapped["marketing_capability_key"] == "campaign_planner"
        assert mapped["marketing_feature_key"] == "campaign_planner"
        assert mapped["marketing_authority"] == "SIGNED_CUSTOMER_WEB_NATIVE"
        assert mapped["marketing_launch_mode"] == "WEB_NAVIGATION"

    marketing_dynamic = audit._map_callback_template("marketing|future_{*}", {"file": "bot.py", "line": 1}, routes)
    assert marketing_dynamic is not None
    assert marketing_dynamic["target"] == "MARKETING_SOURCE_REVIEW_REQUIRED"
    assert marketing_dynamic["status"] == "NEEDS_FEATURE_DISPOSITION"
    assert marketing_dynamic["resolution"] == "marketing_callback_template_requires_source_review"

    for callback in sorted(audit.MEMORY_STORAGE_TELEGRAM_ONLY_ACTIONS):
        mapped = audit._map_callback(callback, "callback_data", {"file": "bot.py", "line": 1}, routes)
        assert mapped["target"] == "TELEGRAM_ONLY"
        assert mapped["status"] == "TELEGRAM_ONLY"
        assert mapped["resolution"] == "bot_canonical_memory_storage_requires_adapter"

    cleanup = audit._map_callback("menu|memory_storage_cleanup", "callback_data", {"file": "bot.py", "line": 1}, routes)
    assert cleanup["target"] == "/account/workspace-care"
    assert cleanup["status"] == "NAVIGATION_ONLY"
    assert cleanup["resolution"] == "reviewed_system_data_stewardship_fresh_web_navigation"
    assert cleanup["source_dispositions"] == (
        "BOT_STORAGE_CLEANUP_GUIDANCE_ONLY",
        "FRESH_SIGNED_WEB_WORKSPACE_CARE_NAVIGATION",
        "BOT_TEMP_FILE_TTL_NOT_REPLAYED",
        "NO_STORAGE_DELETE_OR_QUOTA_CLAIM",
        "NO_RUNTIME_CLAIM",
    )

    dynamic = audit._map_callback_template("menu|translation_pair_{*}", {"file": "bot.py", "line": 1}, routes)
    assert dynamic is not None
    assert dynamic["target"] == "UNRESOLVED_DYNAMIC_MENU_ACTION"
    assert dynamic["status"] == "NEEDS_FEATURE_DISPOSITION"
    assert dynamic["resolution"] == "dynamic_menu_action_requires_finite_catalog"

    # The two Bot Main Guide video/trend choices remain explicit backlog
    # records until the requested final Video-menu phase. They must never
    # inherit the generic menu Dashboard fallback or a Web Video route.
    for callback in sorted(audit.GUIDED_VIDEO_MENU_DEFERRED_ACTIONS):
        mapped = audit._map_callback(callback, "callback_data", {"file": "bot.py", "line": 1}, routes)
        assert mapped["target"] == "GUIDED_VIDEO_MENU_DEFERRED"
        assert mapped["status"] == "NEEDS_FEATURE_DISPOSITION"
        assert mapped["resolution"] == "guided_video_menu_deferred_until_video_menu_phase"
        assert mapped["source_dispositions"] == (
            "BOT_GUIDE_SECTION_CONTEXT_NOT_REPLAYED",
            "BOT_GUIDE_CHILD_CALLBACKS_NOT_REPLAYED",
            "VIDEO_MENU_LAST",
            "SOURCE_STATE_MACHINE_REQUIRED",
            "NO_RUNTIME_CLAIM",
        )


def test_profile_benefits_and_pricing_read_navigation_preserve_the_referral_boundary() -> None:
    """Only reviewed informational panels may open fresh canonical Web reads."""

    audit = _load_audit_module()
    routes = {"/{page_path:path}"}
    expected_pricing = {
        "pricing|main": ("/pricing", "pricing", "pricing", "SIGNED_CUSTOMER", "WEB_NAVIGATION"),
        "pricing|catalog": ("/pricing", "pricing", "pricing", "SIGNED_CUSTOMER", "WEB_NAVIGATION"),
        "pricing|xu": ("/wallet", "wallet", "wallet", "CORE_CANONICAL_READ", "READ_ONLY_CANONICAL"),
        "pricing|packages": ("/packages", "packages", "packages", "CORE_CANONICAL_READ", "READ_ONLY_CANONICAL"),
        "pricing|package_summary": ("/packages", "packages", "packages", "CORE_CANONICAL_READ", "READ_ONLY_CANONICAL"),
        "pricing|my_packages": ("/membership", "membership", "membership", "CORE_CANONICAL_READ", "READ_ONLY_CANONICAL"),
        "pricing|plans": ("/membership", "membership", "membership", "CORE_CANONICAL_READ", "READ_ONLY_CANONICAL"),
        "pricing|vip": ("/membership", "membership", "membership", "CORE_CANONICAL_READ", "READ_ONLY_CANONICAL"),
        "pricing|member": ("/membership", "membership", "membership", "CORE_CANONICAL_READ", "READ_ONLY_CANONICAL"),
    }
    assert set(audit.PRICING_READ_NAVIGATION_REGISTRY) == set(expected_pricing)

    for callback, (target, capability_key, feature_key, authority, launch_mode) in expected_pricing.items():
        mapped = audit._map_callback(callback, "callback_data", {"file": "bot.py", "line": 1}, routes)
        assert mapped["classification"] == "customer"
        assert mapped["target"] == target
        assert mapped["status"] == "NAVIGATION_ONLY"
        assert mapped["resolution"] == "reviewed_pricing_read_navigation"
        assert mapped["pricing_capability_key"] == capability_key
        assert mapped["pricing_feature_key"] == feature_key
        assert mapped["pricing_authority"] == authority
        assert mapped["pricing_launch_mode"] == launch_mode
        assert mapped["source_dispositions"] == (
            "BOT_INFORMATION_PANEL_NOT_REPLAYED",
            "FRESH_SIGNED_WEB_CANONICAL_READ"
            if authority == "CORE_CANONICAL_READ"
            else "FRESH_SIGNED_WEB_INFORMATION_NAVIGATION",
            "NO_PURCHASE_OR_ENTITLEMENT_ACTION",
            "NO_RUNTIME_CLAIM",
        )

    for callback in sorted(audit.PROFILE_REFERRAL_TELEGRAM_ONLY_ACTIONS):
        mapped = audit._map_callback(callback, "callback_data", {"file": "bot.py", "line": 1}, routes)
        assert mapped["classification"] == "customer"
        assert mapped["target"] == "TELEGRAM_ONLY"
        assert mapped["status"] == "TELEGRAM_ONLY"
        assert mapped["resolution"] == "profile_referral_requires_canonical_bot_adapter"
        assert mapped["source_dispositions"] == (
            "BOT_TELEGRAM_DEEP_LINK_IDENTITY",
            "BOT_CANONICAL_REFERRAL_REWARD_STATE",
            "NO_WEB_REFERRAL_READ_ADAPTER",
            "NO_RUNTIME_CLAIM",
        )

    # Exact audit descriptors remain constrained by the public browser-safe
    # catalog. Referral tokens are intentionally absent: no browser input can
    # grant referral reads, synthesize a Telegram link, or adjust rewards.
    from copyfast_registry import menu_capability_catalog

    public_catalog = {item["key"]: item for item in menu_capability_catalog()}
    for descriptor in audit.PRICING_READ_NAVIGATION_REGISTRY.values():
        public_entry = public_catalog[descriptor["capability_key"]]
        assert public_entry["feature_key"] == descriptor["feature_key"]
        assert public_entry["route"] == descriptor["target"]
        assert public_entry["authority"] == descriptor["authority"]
        assert public_entry["launch_mode"] == descriptor["launch_mode"]
    serialized_catalog = json.dumps(menu_capability_catalog(), ensure_ascii=False)
    assert "profile_ref_" not in serialized_catalog
    assert "pricing|" not in serialized_catalog


def test_translation_menu_opens_only_fresh_authoring_workspaces_and_defers_bot_sessions() -> None:
    """Translation Bot state must never leak into a Web navigation catalog."""

    audit = _load_audit_module()
    routes = {"/{page_path:path}"}
    navigation = {
        "menu|translate": ("/subtitle-studio", "subtitle_studio", "subtitle_studio", "SIGNED_CUSTOMER_WEB_NATIVE"),
        "menu|translation_language_hub": ("/subtitle-studio", "subtitle_studio", "subtitle_studio", "SIGNED_CUSTOMER_WEB_NATIVE"),
        "menu|translation_text": ("/subtitle-studio", "subtitle_studio", "subtitle_studio", "SIGNED_CUSTOMER_WEB_NATIVE"),
        "menu|translation_document": ("/documents", "documents", "documents", "SIGNED_CUSTOMER"),
    }
    for callback, (target, capability_key, feature_key, authority) in navigation.items():
        mapped = audit._map_callback(callback, "callback_data", {"file": "bot.py", "line": 1}, routes)
        assert mapped["classification"] == "customer"
        assert mapped["target"] == target
        assert mapped["status"] == "NAVIGATION_ONLY"
        assert mapped["resolution"] == "reviewed_exact_menu_navigation"
        assert mapped["menu_capability_key"] == capability_key
        assert mapped["menu_feature_key"] == feature_key
        assert mapped["menu_authority"] == authority
        assert mapped["menu_launch_mode"] == "WEB_NAVIGATION"

    # The frozen Bot stores a `transcript` pending source but the later
    # callback accepts only voice/file/text. Keep that known broken branch out
    # of the browser-safe menu catalog rather than making Subtitle Studio look
    # like an operational Bot translation adapter.
    assert audit.TRANSLATION_KNOWN_BROKEN_MENU_ACTIONS == {"menu|translation_transcript"}
    assert "menu|translation_transcript" not in audit.MENU_ACTION_REGISTRY
    transcript = audit._map_callback("menu|translation_transcript", "callback_data", {"file": "bot.py", "line": 1}, routes)
    assert transcript["target"] == "BOT_TRANSLATION_TRANSCRIPT_KNOWN_BROKEN"
    assert transcript["status"] == "NEEDS_FEATURE_DISPOSITION"
    assert transcript["resolution"] == "known_broken_bot_translation_transcript"
    assert transcript["source_dispositions"] == (
        "BOT_KNOWN_BROKEN_TRANSLATION_TRANSCRIPT",
        "BOT_PENDING_TEXT_OR_MEDIA_STATE",
        "NO_RUNTIME_CLAIM",
    )

    # The legacy `tr_*` handler consumes Telegram-local cached/pending source
    # state. Only three static picker literals may open a fresh guarded Web
    # surface; target/transcribe branches do not become browser execution.
    fresh_source_navigation = {
        "tr_pick|file": ("/documents/translate", "documents_translate"),
        "tr_pick|voice": ("/subtitle-studio", "subtitle_studio"),
        "tr_more|voice": ("/subtitle-studio", "subtitle_studio"),
    }
    for callback, (target, capability_key) in fresh_source_navigation.items():
        mapped = audit._map_callback(callback, "callback_data", {"file": "bot.py", "line": 1}, routes)
        assert mapped["target"] == target
        assert mapped["status"] == "COPIED_GUARDED"
        assert mapped["resolution"] == "reviewed_translation_source_navigation_guarded"
        assert mapped["translation_source_capability_key"] == capability_key
        assert "WEB_NAVIGATION_GUARDED" in mapped["source_dispositions"]
        assert "NO_RUNTIME_CLAIM" in mapped["source_dispositions"]

    for callback in ("tr_pick|future", "tr_more|file"):
        mapped = audit._map_callback(callback, "callback_data", {"file": "bot.py", "line": 1}, routes)
        assert mapped["target"] == "TRANSLATION_SOURCE_SELECTOR_REVIEW_REQUIRED"
        assert mapped["status"] == "NEEDS_FEATURE_DISPOSITION"
        assert mapped["resolution"] == "translation_source_selector_requires_finite_source_review"
        assert "SOURCE_VALUE_REQUIRES_FINITE_REVIEW" in mapped["source_dispositions"]
        assert "NO_RUNTIME_CLAIM" in mapped["source_dispositions"]

    for template in ("tr_pick|{*}", "tr_more|{*}"):
        mapped = audit._map_callback_template(template, {"file": "bot.py", "line": 1}, routes)
        assert mapped is not None
        assert mapped["target"] == "TRANSLATION_SOURCE_SELECTOR_REVIEW_REQUIRED"
        assert mapped["status"] == "NEEDS_FEATURE_DISPOSITION"
        assert mapped["resolution"] == "translation_source_selector_requires_finite_source_review"

    for callback in ("tr_target|voice|en", "tr_target|file|vi", "tr_target|text|zh"):
        mapped = audit._map_callback(callback, "callback_data", {"file": "bot.py", "line": 1}, routes)
        assert mapped["target"] == "CORE_CANONICAL_TRANSLATION_GUARDED"
        assert mapped["status"] == "NEEDS_FEATURE_DISPOSITION"
        assert mapped["resolution"] == "translation_target_requires_canonical_provider_or_core_contract"
        assert "CANONICAL_TRANSLATION_PROVIDER_OR_CORE_GUARD" in mapped["source_dispositions"]
        assert "NO_RUNTIME_CLAIM" in mapped["source_dispositions"]

    transcribe = audit._map_callback("tr_transcribe", "callback_data", {"file": "bot.py", "line": 1}, routes)
    assert transcribe["target"] == "CORE_CANONICAL_ASR_GUARDED"
    assert transcribe["status"] == "NEEDS_FEATURE_DISPOSITION"
    assert transcribe["resolution"] == "translation_transcribe_requires_canonical_asr_contract"
    assert "CANONICAL_ASR_PROVIDER_OR_CORE_GUARD" in transcribe["source_dispositions"]
    assert "NO_RUNTIME_CLAIM" in transcribe["source_dispositions"]

    telegram_only = {
        "menu|translate_more", "menu|translate_off", "menu|translate_set_ar", "menu|translate_set_en",
        "menu|translate_set_ja", "menu|translate_set_ko", "menu|translate_set_th", "menu|translate_set_vi",
        "menu|translate_set_zh", "menu|translation_auto_target", "menu|translation_language",
        "menu|translation_live_conversation", "menu|translation_output_voice", "menu|translation_stop_session",
        "menu|translation_swap_languages", "menu|translation_text_target_custom", "menu|translation_text_target_en",
        "menu|translation_text_target_ja", "menu|translation_text_target_ko", "menu|translation_text_target_th",
        "menu|translation_text_target_vi", "menu|translation_text_target_zh", "menu|translation_two_way",
        "menu|translation_voice",
    }
    assert audit.MENU_TRANSLATION_TELEGRAM_ONLY_ACTIONS == telegram_only
    for callback in sorted(telegram_only):
        mapped = audit._map_callback(callback, "callback_data", {"file": "bot.py", "line": 1}, routes)
        assert mapped["classification"] == "customer"
        assert mapped["target"] == "TELEGRAM_ONLY"
        assert mapped["status"] == "TELEGRAM_ONLY"
        assert mapped["resolution"] == "translation_session_requires_web_owned_contract"
        assert mapped["source_dispositions"] == (
            "TELEGRAM_IDENTITY_CONTEXT",
            "BOT_TRANSLATION_SESSION_OR_PREFERENCE_STATE",
            "BOT_PENDING_TEXT_OR_MEDIA_STATE",
            "PROVIDER_GUARD_OR_TTS_PATH",
            "NO_RUNTIME_CLAIM",
        )

    deferred = audit._map_callback("menu|translation_video_factory", "callback_data", {"file": "bot.py", "line": 1}, routes)
    assert deferred["target"] == "VIDEO_TRANSLATION_MENU_DEFERRED"
    assert deferred["status"] == "NEEDS_FEATURE_DISPOSITION"
    assert deferred["resolution"] == "translation_video_factory_deferred_until_video_menu_phase"
    assert deferred["source_dispositions"] == (
        "TELEGRAM_IDENTITY_CONTEXT",
        "BOT_VIDEO_DUBBING_PENDING_STATE",
        "VIDEO_MENU_LAST",
        "SOURCE_STATE_MACHINE_REQUIRED",
        "NO_RUNTIME_CLAIM",
    )

    templates = {
        "menu|translation_pair_back_{*}",
        "menu|translation_pair_start_{*}",
        "menu|translation_pair_swap_{*}",
    }
    assert audit.TRANSLATION_SESSION_TELEGRAM_ONLY_CALLBACK_TEMPLATES == templates
    for template in sorted(templates):
        mapped = audit._map_callback_template(template, {"file": "bot.py", "line": 1}, routes)
        assert mapped is not None
        assert mapped["target"] == "TELEGRAM_ONLY"
        assert mapped["status"] == "TELEGRAM_ONLY"
        assert mapped["resolution"] == "translation_session_template_requires_web_owned_contract"
        assert mapped["source_dispositions"] == (
            "TELEGRAM_IDENTITY_CONTEXT",
            "BOT_TRANSLATION_PAIR_DRAFT_STATE",
            "BOT_TRANSLATION_SESSION_STATE",
            "NO_RUNTIME_CLAIM",
        )

    unknown = audit._map_callback_template("menu|translation_pair_future_{*}", {"file": "bot.py", "line": 1}, routes)
    assert unknown is not None
    assert unknown["target"] == "UNRESOLVED_DYNAMIC_MENU_ACTION"
    assert unknown["status"] == "NEEDS_FEATURE_DISPOSITION"

    from copyfast_registry import menu_capability_catalog

    public_catalog = {item["key"]: item for item in menu_capability_catalog()}
    assert public_catalog["subtitle_studio"]["route"] == "/subtitle-studio"
    assert public_catalog["subtitle_studio"]["authority"] == "SIGNED_CUSTOMER_WEB_NATIVE"
    serialized_catalog = json.dumps(menu_capability_catalog(), ensure_ascii=False)
    assert "translation_pair" not in serialized_catalog
    assert "translation_video_factory" not in serialized_catalog


def test_operator_menu_category_navigation_is_admin_only_and_defers_video_production() -> None:
    """The Bot Operator menu may open a fresh ERP directory, never a command."""

    audit = _load_audit_module()
    routes = {"/{page_path:path}"}
    expected = {
        "opmenu|cat_control": ("/admin", "admin_overview", "Điều hành"),
        "opmenu|cat_trend": ("/admin/trends", "admin_trends", "Trend"),
        "opmenu|cat_affiliate": ("/admin/growth", "admin_growth", "Affiliate"),
        "opmenu|cat_schedule": ("/admin/calendar", "admin_calendar", "Kênh & lịch"),
        "opmenu|cat_publish": ("/admin/publishing", "admin_publishing", "Đăng bài"),
        "opmenu|cat_money": ("/admin/finance", "admin_finance", "Doanh thu"),
        "opmenu|cat_api": ("/admin/runtime", "admin_runtime", "API/Auto"),
        "opmenu|cat_internal": ("/admin/audit", "admin_audit", "Nội bộ"),
        "opmenu|dashboard": ("/admin", "admin_overview", "Dashboard"),
    }
    assert set(audit.OPERATOR_MENU_CATEGORY_REGISTRY) == set(expected)

    for callback, (target, feature_key, title) in expected.items():
        mapped = audit._map_callback(callback, "callback_data", {"file": "bot.py", "line": 1}, routes)
        assert mapped["classification"] == "admin"
        assert mapped["target"] == target
        assert mapped["status"] == "NAVIGATION_ONLY"
        assert mapped["resolution"] == "reviewed_operator_menu_category_navigation"
        assert mapped["operator_admin_feature_key"] == feature_key
        assert mapped["operator_category_title"] == title
        assert mapped["source_dispositions"] == (
            "BOT_ADMIN_ONLY",
            "BOT_COMMAND_SNIPPET_NOT_REPLAYED",
            "FRESH_SIGNED_WEB_ADMIN_NAVIGATION",
            "NO_RUNTIME_CLAIM",
        )

    deferred = audit._map_callback("opmenu|cat_production", "callback_data", {"file": "bot.py", "line": 1}, routes)
    assert deferred["classification"] == "admin"
    assert deferred["target"] == "VIDEO_ADMIN_MENU_DEFERRED"
    assert deferred["status"] == "NEEDS_FEATURE_DISPOSITION"
    assert deferred["resolution"] == "operator_production_category_deferred_until_video_menu_phase"
    assert "VIDEO_MENU_LAST" in deferred["source_dispositions"]

    # The audit knows private Bot tokens only to prove source coverage. The
    # browser-safe customer catalog cannot leak an operator token or turn it
    # into a client-side authority grant.
    from copyfast_registry import menu_capability_catalog

    assert "opmenu|" not in json.dumps(menu_capability_catalog(), ensure_ascii=False)


def test_operator_menu_root_is_an_exact_fresh_admin_entry_not_browser_back_navigation() -> None:
    """The only reviewed Operator root literal opens the guarded ERP overview."""

    audit = _load_audit_module()
    routes = {"/{page_path:path}"}
    assert audit.OPERATOR_MENU_ROOT_NAVIGATION == {
        "callback": "opmenu|root",
        "target": "/admin",
        "admin_feature_key": "admin_overview",
        "title": "AI Operator",
    }

    mapped = audit._map_callback("opmenu|root", "callback_data", {"file": "bot.py", "line": 1}, routes)
    assert mapped["classification"] == "admin"
    assert mapped["target"] == "/admin"
    assert mapped["status"] == "NAVIGATION_ONLY"
    assert mapped["resolution"] == "reviewed_operator_menu_root_navigation"
    assert mapped["operator_menu_entry"] == "root"
    assert mapped["operator_admin_feature_key"] == "admin_overview"
    assert mapped["operator_menu_title"] == "AI Operator"
    assert mapped["operator_navigation_mode"] == "FRESH_ADMIN_ERP_ROOT"
    assert mapped["source_dispositions"] == (
        "BOT_ADMIN_ONLY",
        "BOT_OPERATOR_MENU_RENDER_ONLY",
        "BOT_CALLBACK_CONTEXT_NOT_REPLAYED",
        "FRESH_SIGNED_WEB_ADMIN_NAVIGATION",
        "NO_RUNTIME_CLAIM",
    )

    # Bot callback data is case-sensitive. A spelling/case variant must stay
    # visible for review, never inherit this exact navigation allowance.
    unknown = audit._map_callback("OPMENU|ROOT", "callback_data", {"file": "bot.py", "line": 1}, routes)
    assert unknown["resolution"] != "reviewed_operator_menu_root_navigation"

    from copyfast_registry import menu_capability_catalog

    assert "opmenu|root" not in json.dumps(menu_capability_catalog(), ensure_ascii=False)


def test_operator_menu_unreviewed_actions_do_not_inherit_an_admin_route(tmp_path: Path) -> None:
    """Nested Operator snippets are not browser commands or admin navigation."""

    audit = _load_audit_module()
    routes = {"/admin", "/admin/jobs", "/admin/runtime", "/{page_path:path}"}
    evidence = {"file": "bot.py", "line": 1}

    assert not any(prefix == "opmenu|" for prefix, *_ in audit.DYNAMIC_CALLBACK_TEMPLATE_ROUTE_OVERRIDES)

    for callback in (
        "opmenu|missionrun",
        "opmenu|telegramtakeover",
        "opmenu|publisherrun",
        "opmenu|cat_future",
        "opmenu|unknown",
        "OPMENU|ROOT",
    ):
        mapped = audit._map_callback(callback, "callback_data", evidence, routes)
        assert mapped["target"] == "OPERATOR_MENU_SOURCE_REVIEW_REQUIRED"
        assert mapped["classification"] == "admin"
        assert mapped["status"] == "NEEDS_FEATURE_DISPOSITION"
        assert mapped["resolution"] == "operator_menu_callback_requires_exact_source_review"
        assert "BOT_ADMIN_ONLY" in mapped["source_dispositions"]
        assert "NO_WEB_NAVIGATION_OR_BROWSER_ACTION" in mapped["source_dispositions"]

    for template in (
        "opmenu|{*}",
        "opmenu|missionrun|future",
        "opmenu|cat_future_{*}",
        "OPMENU|{*}",
    ):
        mapped = audit._map_callback_template(template, evidence, routes)
        assert mapped is not None
        assert mapped["target"] == "OPERATOR_MENU_SOURCE_REVIEW_REQUIRED"
        assert mapped["classification"] == "admin"
        assert mapped["status"] == "NEEDS_FEATURE_DISPOSITION"
        assert mapped["resolution"] == "operator_menu_callback_requires_exact_source_review"

    bot_root = tmp_path / "bot"
    bot_root.mkdir()
    (bot_root / "bot.py").write_text(
        '''
def operator_category_keyboard(action):
    InlineKeyboardButton("Run", callback_data=f"opmenu|{action}")
    InlineKeyboardButton("Root", callback_data="opmenu|root")
''',
        encoding="utf-8",
    )
    web_root = tmp_path / "web"
    web_root.mkdir()
    (web_root / "app.py").write_text("app = FastAPI()\n", encoding="utf-8")
    result = audit.run_audit(bot_root, web_root, "baseline", tmp_path / "reports", tmp_path / "docs")
    templates = {item["source"]: item for item in result["parity_gap"]["callback_template_mappings"]}
    assert templates["opmenu|{*}"]["target"] == "OPERATOR_MENU_SOURCE_REVIEW_REQUIRED"
    callbacks = {item["source"]: item for item in result["parity_gap"]["callback_mappings"]}
    assert callbacks["opmenu|root"]["target"] == "/admin"


def test_system_data_stewardship_navigation_is_finite_and_never_leaks_bot_state() -> None:
    """System/data buttons can only open separately guarded Web read routes."""

    audit = _load_audit_module()
    routes = {"/{page_path:path}"}
    expected = {
        "menu|system": ("/admin/system", "admin", "admin_system", "SIGNED_CANONICAL_ADMIN_READ"),
        "menu|system_runtime_help": ("/admin/runtime", "admin", "admin_runtime", "SIGNED_CANONICAL_ADMIN_READ"),
        "menu|system_data_status_help": ("/admin/system", "admin", "admin_system", "SIGNED_CANONICAL_ADMIN_READ"),
        "menu|system_backup_help": ("/admin/backups", "admin", "admin_backups", "SIGNED_CANONICAL_ADMIN_READ"),
        "menu|system_health_help": ("/admin/runtime", "admin", "admin_runtime", "SIGNED_CANONICAL_ADMIN_READ"),
        "menu|internal_archive": ("/admin/internal-documents", "admin", "admin_internal_documents", "SIGNED_WEB_LOCAL_ADMIN"),
        "menu|memory_storage_cleanup": ("/account/workspace-care", "customer", "workspace_care", "SIGNED_CUSTOMER_WEB_NATIVE"),
    }
    assert set(audit.SYSTEM_DATA_STEWARDSHIP_FRESH_WEB_NAVIGATION_ACTIONS) == set(expected)

    for callback, (target, classification, feature_key, authority) in expected.items():
        descriptor = audit.SYSTEM_DATA_STEWARDSHIP_FRESH_WEB_NAVIGATION_ACTIONS[callback]
        mapped = audit._map_callback(callback, "callback_data", {"file": "bot.py", "line": 1}, routes)
        assert mapped["target"] == target
        assert mapped["classification"] == classification
        assert mapped["status"] == "NAVIGATION_ONLY"
        assert mapped["resolution"] == "reviewed_system_data_stewardship_fresh_web_navigation"
        assert mapped["source_dispositions"] == descriptor["source_dispositions"]
        assert mapped["system_data_stewardship_feature_key"] == feature_key
        assert mapped["system_data_stewardship_authority"] == authority
        assert mapped["system_data_stewardship_launch_mode"] == "WEB_NAVIGATION"
        assert "NO_RUNTIME_CLAIM" in mapped["source_dispositions"]

    # A finite source registry is not a prefix authorization. Billing, tax,
    # job cleanup and Video remain separate canonical/source-review work.
    for token in ("menu|billing", "menu|tax_daily", "menu|clear_stale_jobs_help", "menu|video_workflow"):
        assert token not in audit.SYSTEM_DATA_STEWARDSHIP_FRESH_WEB_NAVIGATION_ACTIONS
    unknown = audit._map_callback("menu|system_future", "callback_data", {"file": "bot.py", "line": 1}, routes)
    assert unknown["resolution"] != "reviewed_system_data_stewardship_fresh_web_navigation"

    from copyfast_registry import menu_capability_catalog

    serialized_catalog = json.dumps(menu_capability_catalog(), ensure_ascii=False)
    assert "menu|system" not in serialized_catalog
    assert "menu|memory_storage_cleanup" not in serialized_catalog


def test_postback_readiness_navigation_is_exact_and_never_becomes_a_configuration_or_event_action() -> None:
    """Only one raw Bot admin hint may open the static readiness guidance."""

    audit = _load_audit_module()
    routes = {"/{page_path:path}"}
    expected = {"menu|hint_postback_setup"}
    assert set(audit.POSTBACK_READINESS_FRESH_WEB_ADMIN_NAVIGATION_ACTIONS) == expected

    descriptor = audit.POSTBACK_READINESS_FRESH_WEB_ADMIN_NAVIGATION_ACTIONS["menu|hint_postback_setup"]
    mapped = audit._map_callback("menu|hint_postback_setup", "callback_data", {"file": "bot.py", "line": 1}, routes)
    assert mapped["target"] == "/admin/growth/postback-readiness"
    assert mapped["classification"] == "admin"
    assert mapped["status"] == "NAVIGATION_ONLY"
    assert mapped["resolution"] == "reviewed_postback_readiness_fresh_web_navigation"
    assert mapped["source_dispositions"] == descriptor["source_dispositions"]
    assert mapped["postback_readiness_feature_key"] == "admin_postback_readiness"
    assert mapped["postback_readiness_authority"] == "SIGNED_CANONICAL_ADMIN_GUIDANCE"
    assert mapped["postback_readiness_launch_mode"] == "WEB_NAVIGATION"
    for disposition in (
        "BOT_ADMIN_ONLY",
        "BOT_HINT_CONTEXT_NOT_REPLAYED",
        "BOT_POSTBACK_CONFIGURATION_NOT_REPLAYED",
        "NO_WEB_POSTBACK_CONFIGURATION_OR_EVENT_ACTION",
        "NO_AFFILIATE_JOB_OR_ATTRIBUTION_TRANSFER",
        "NO_REWARD_PAYOUT_OR_FINANCIAL_ACTION",
        "NO_PROVIDER_OR_RUNTIME_ACTION",
        "NO_RUNTIME_CLAIM",
    ):
        assert disposition in mapped["source_dispositions"]

    # Bot callbacks are case-sensitive and this allowance is intentionally
    # raw-identifier only. Variants never inherit the guidance route.
    for token in ("MENU|HINT_POSTBACK_SETUP", "menu|hint_postback_setup_future"):
        unknown = audit._map_callback(token, "callback_data", {"file": "bot.py", "line": 1}, routes)
        assert unknown["target"] != "/admin/growth/postback-readiness"
        assert unknown["resolution"] != "reviewed_postback_readiness_fresh_web_navigation"

    command = {
        "command": "postback_setup",
        "handler": "cmd_postback_setup",
        "file": "bot.py",
        "line": 1,
        "admin_guarded": True,
    }
    command_mapping = audit._map_command(command, routes)
    assert command_mapping["target"] == "CANONICAL_POSTBACK_CONFIGURATION_SOURCE_REVIEW_REQUIRED"
    assert command_mapping["status"] == "NEEDS_FEATURE_DISPOSITION"
    assert command_mapping["resolution"] == "reviewed_postback_configuration_command_requires_canonical_contract"
    assert "CANONICAL_BOT_POSTBACK_CONFIGURATION_AND_EVENT_INGRESS" in command_mapping["source_dispositions"]

    from copyfast_registry import menu_capability_catalog

    serialized_catalog = json.dumps(menu_capability_catalog(), ensure_ascii=False)
    assert "menu|hint_postback_setup" not in serialized_catalog


def test_tax_accounting_guidance_navigation_is_finite_and_never_becomes_a_finance_adapter() -> None:
    """Only reviewed tax-menu guidance can open the static canonical-admin page."""

    audit = _load_audit_module()
    routes = {"/{page_path:path}"}
    expected = {
        "menu|finance_tax",
        "menu|tax_checklist",
        "menu|tax_custom_help",
    }
    assert set(audit.TAX_ACCOUNTING_GUIDANCE_FRESH_WEB_ADMIN_NAVIGATION_ACTIONS) == expected

    for callback in expected:
        descriptor = audit.TAX_ACCOUNTING_GUIDANCE_FRESH_WEB_ADMIN_NAVIGATION_ACTIONS[callback]
        mapped = audit._map_callback(callback, "callback_data", {"file": "bot.py", "line": 1}, routes)
        assert mapped["target"] == "/admin/finance/tax-readiness"
        assert mapped["classification"] == "admin"
        assert mapped["status"] == "NAVIGATION_ONLY"
        assert mapped["resolution"] == "reviewed_tax_accounting_guidance_fresh_web_navigation"
        assert mapped["source_dispositions"] == descriptor["source_dispositions"]
        assert mapped["tax_accounting_guidance_feature_key"] == "admin_tax_readiness"
        assert mapped["tax_accounting_guidance_authority"] == "SIGNED_CANONICAL_ADMIN_READ"
        assert mapped["tax_accounting_guidance_launch_mode"] == "WEB_NAVIGATION"
        for disposition in (
            "BOT_ADMIN_ONLY",
            "NO_CANONICAL_FINANCE_DATA_TRANSFER",
            "NO_TAX_ESTIMATE_OR_FINANCIAL_CALCULATION",
            "NO_REPORT_EXPORT_OR_FILE_DELIVERY",
            "NO_TAX_PROFILE_OR_COMPLIANCE_MUTATION",
            "NO_PAYOS_WALLET_LEDGER_OR_PROVIDER_ACTION",
            "NO_RUNTIME_CLAIM",
        ):
            assert disposition in mapped["source_dispositions"]

    # The frozen Bot classifies its entire tax_ family as admin-only. The
    # finite guidance list cannot turn calculation, profile or CSV branches
    # into a Web adapter; exact sensitive actions remain canonical-finance
    # source-review records and even an unknown tax_ callback stays admin.
    canonical_finance_actions = {
        "menu|tax_estimate": "CANONICAL_BOT_TAX_ESTIMATE_CALCULATION",
        "menu|tax_estimate_month": "CANONICAL_BOT_TAX_ESTIMATE_CALCULATION",
        "menu|tax_estimate_previous": "CANONICAL_BOT_TAX_ESTIMATE_CALCULATION",
        "menu|tax_estimate_quarter": "CANONICAL_BOT_TAX_ESTIMATE_CALCULATION",
        "menu|tax_config": "CANONICAL_BOT_TAX_PROFILE_STATE",
        "menu|tax_export": "CANONICAL_BOT_CSV_EXPORT_MENU",
        "menu|tax_export_month": "CANONICAL_BOT_CSV_EXPORT_DELIVERY",
        "menu|tax_export_previous": "CANONICAL_BOT_CSV_EXPORT_DELIVERY",
        "menu|tax_export_quarter": "CANONICAL_BOT_CSV_EXPORT_DELIVERY",
        "menu|tax_export_custom_help": "CANONICAL_BOT_EXPORT_PERIOD_INPUT_GUIDANCE",
    }
    assert set(audit.TAX_ACCOUNTING_CANONICAL_FINANCE_SOURCE_REVIEW_ACTIONS) == set(canonical_finance_actions)
    for token, operation_disposition in canonical_finance_actions.items():
        descriptor = audit.TAX_ACCOUNTING_CANONICAL_FINANCE_SOURCE_REVIEW_ACTIONS[token]
        assert descriptor["operation_disposition"] == operation_disposition
        assert token not in audit.TAX_ACCOUNTING_GUIDANCE_FRESH_WEB_ADMIN_NAVIGATION_ACTIONS
        mapped = audit._map_callback(token, "callback_data", {"file": "bot.py", "line": 1}, routes)
        assert mapped["classification"] == "admin"
        assert mapped["target"] == "CANONICAL_TAX_ACCOUNTING_SOURCE_REVIEW_REQUIRED"
        assert mapped["status"] == "NEEDS_FEATURE_DISPOSITION"
        assert mapped["resolution"] == "reviewed_tax_accounting_callback_requires_canonical_finance_contract"
        for disposition in (
            "BOT_ADMIN_ONLY",
            "CANONICAL_BOT_FINANCE_TAX_STATE",
            "SOURCE_STATE_MACHINE_REQUIRED",
            "NO_CANONICAL_FINANCE_DATA_TRANSFER",
            "NO_REPORT_EXPORT_OR_FILE_DELIVERY",
            "NO_RUNTIME_CLAIM",
        ):
            assert disposition in mapped["source_dispositions"]
        assert operation_disposition in mapped["source_dispositions"]

    for token in (
        "menu|finance_compliance",
        "archive|dept|tax_invoice",
        "menu|tax_future",
    ):
        assert token not in audit.TAX_ACCOUNTING_GUIDANCE_FRESH_WEB_ADMIN_NAVIGATION_ACTIONS
        mapped = audit._map_callback(token, "callback_data", {"file": "bot.py", "line": 1}, routes)
        if token.startswith("menu|tax_"):
            assert mapped["classification"] == "admin"
        assert mapped["target"] != "/admin/finance/tax-readiness"
        assert mapped["resolution"] != "reviewed_tax_accounting_guidance_fresh_web_navigation"

    from copyfast_registry import menu_capability_catalog

    serialized_catalog = json.dumps(menu_capability_catalog(), ensure_ascii=False)
    for callback in expected:
        assert callback not in serialized_catalog


def test_job_lock_recovery_guidance_is_finite_and_never_becomes_a_job_or_refund_control() -> None:
    """Only Bot help becomes static canonical-admin guidance; mutations stay source-review-only."""

    audit = _load_audit_module()
    routes = {"/{page_path:path}"}
    expected = {"menu|clear_stale_jobs_help"}
    assert set(audit.JOB_LOCK_RECOVERY_FRESH_WEB_ADMIN_NAVIGATION_ACTIONS) == expected

    descriptor = audit.JOB_LOCK_RECOVERY_FRESH_WEB_ADMIN_NAVIGATION_ACTIONS["menu|clear_stale_jobs_help"]
    mapped = audit._map_callback("menu|clear_stale_jobs_help", "callback_data", {"file": "bot.py", "line": 1}, routes)
    assert mapped["target"] == "/admin/job-recovery-guide"
    assert mapped["classification"] == "admin"
    assert mapped["status"] == "NAVIGATION_ONLY"
    assert mapped["resolution"] == "reviewed_job_lock_recovery_fresh_web_navigation"
    assert mapped["source_dispositions"] == descriptor["source_dispositions"]
    assert mapped["job_lock_recovery_feature_key"] == "admin_job_recovery_guide"
    assert mapped["job_lock_recovery_authority"] == "SIGNED_CANONICAL_ADMIN_READ"
    assert mapped["job_lock_recovery_launch_mode"] == "WEB_NAVIGATION"
    for disposition in (
        "BOT_ADMIN_ONLY",
        "BOT_JOB_LOCK_HELP_NOT_REPLAYED",
        "BOT_JOB_LOCK_STATE_NOT_REPLAYED",
        "NO_BOT_JOB_OR_USER_IDENTIFIER_TRANSFER",
        "NO_JOB_CLEAR_RETRY_REFUND_OR_CHARGE_ACTION",
        "NO_PROVIDER_WORKER_RUNTIME_CONTROL",
        "NO_PAYOS_WALLET_LEDGER_ACTION",
        "NO_RUNTIME_CLAIM",
    ):
        assert disposition in mapped["source_dispositions"]

    canonical_callbacks = {
        "menu|admin_confirm_clear_stale_jobs": "CANONICAL_BOT_JOB_LOCK_CLEAR_CONFIRMATION",
        "menu|admin_confirm_ack_clear_stale_jobs": "CANONICAL_BOT_JOB_LOCK_CLEAR_ACKNOWLEDGEMENT",
        "menu|admin_confirm_refund_job": "CANONICAL_BOT_JOB_REFUND_CONFIRMATION",
        "menu|admin_confirm_ack_refund_job": "CANONICAL_BOT_JOB_REFUND_ACKNOWLEDGEMENT",
    }
    assert set(audit.JOB_LOCK_RECOVERY_CANONICAL_SOURCE_REVIEW_ACTIONS) == set(canonical_callbacks)
    for token, operation_disposition in canonical_callbacks.items():
        assert token not in audit.JOB_LOCK_RECOVERY_FRESH_WEB_ADMIN_NAVIGATION_ACTIONS
        mapped = audit._map_callback(token, "callback_data", {"file": "bot.py", "line": 1}, routes)
        assert mapped["target"] == "CANONICAL_JOB_LOCK_RECOVERY_SOURCE_REVIEW_REQUIRED"
        assert mapped["classification"] == "admin"
        assert mapped["status"] == "NEEDS_FEATURE_DISPOSITION"
        assert mapped["resolution"] == "reviewed_job_lock_recovery_callback_requires_canonical_mutation_contract"
        assert operation_disposition in mapped["source_dispositions"]
        assert "NO_JOB_CLEAR_RETRY_REFUND_OR_CHARGE_ACTION" in mapped["source_dispositions"]
        assert "NO_PAYOS_WALLET_LEDGER_ACTION" in mapped["source_dispositions"]

    canonical_commands = {
        "clear_job_lock": "CANONICAL_BOT_JOB_LOCK_CLEAR_MUTATION",
        "refund_job": "CANONICAL_BOT_JOB_REFUND_MUTATION",
    }
    assert set(audit.JOB_LOCK_RECOVERY_CANONICAL_SOURCE_REVIEW_COMMANDS) == set(canonical_commands)
    for command, operation_disposition in canonical_commands.items():
        mapped = audit._map_command(
            {"command": command, "handler": f"cmd_{command}", "file": "bot.py", "line": 1, "admin_guarded": True},
            routes,
        )
        assert mapped["target"] == "CANONICAL_JOB_LOCK_RECOVERY_SOURCE_REVIEW_REQUIRED"
        assert mapped["classification"] == "admin"
        assert mapped["status"] == "NEEDS_FEATURE_DISPOSITION"
        assert mapped["resolution"] == "reviewed_job_lock_recovery_command_requires_canonical_mutation_contract"
        assert operation_disposition in mapped["source_dispositions"]

    unknown = audit._map_callback("menu|clear_future", "callback_data", {"file": "bot.py", "line": 1}, routes)
    assert unknown["target"] != "/admin/job-recovery-guide"
    assert unknown["resolution"] != "reviewed_job_lock_recovery_fresh_web_navigation"

    from copyfast_registry import menu_capability_catalog

    serialized_catalog = json.dumps(menu_capability_catalog(), ensure_ascii=False)
    for callback in (*expected, *canonical_callbacks):
        assert callback not in serialized_catalog


def test_reviewed_menu_navigation_does_not_inflate_static_feature_parity(tmp_path: Path) -> None:
    """Opening a fresh Web workspace is not proof of Bot workflow parity."""
    audit = _load_audit_module()
    bot_root = tmp_path / "bot"
    web_root = tmp_path / "web"
    bot_root.mkdir()
    web_root.mkdir()
    (bot_root / "bot.py").write_text(
        'button = InlineKeyboardButton("Main", callback_data="menu|main")',
        encoding="utf-8",
    )
    (web_root / "app.py").write_text(
        """
app = FastAPI()
@app.get('/dashboard')
async def dashboard():
    return {}
@app.get('/{page_path:path}')
async def page(page_path):
    return {}
""",
        encoding="utf-8",
    )

    result = audit.run_audit(bot_root, web_root, "baseline", tmp_path / "reports", tmp_path / "docs")
    gap = result["parity_gap"]
    assert gap["callback_mappings"][0]["status"] == "NAVIGATION_ONLY"
    assert gap["static_web_surface_coverage_percent"] == 0.0
    assert gap["mapping_coverage_percent"] == 100.0


def test_static_audit_inventories_literal_tuple_keyboard_callbacks_in_small_and_monolithic_sources(tmp_path: Path) -> None:
    """Keyboard helper rows must not disappear when the Bot skips full AST parsing."""

    audit = _load_audit_module()
    bot_root = tmp_path / "bot"
    bot_root.mkdir()
    bot_source = bot_root / "bot.py"
    bot_source.write_text(
        '''
raise RuntimeError("The static auditor must not execute this source")

keyboard_rows = [
    ("Meta", "freehub|meta"),
    ("Caption" if language == "vi" else "Caption/hashtags", "freehub|caption"),
]
buttons.append(("Publish", "freehub|publish_package"))
not_a_keyboard_callback = ("Display only", "ordinary text")
''',
        encoding="utf-8",
    )

    expected = {"freehub|meta", "freehub|caption", "freehub|publish_package"}
    original_max_ast_parse_bytes = audit.MAX_AST_PARSE_BYTES
    try:
        for max_ast_parse_bytes in (original_max_ast_parse_bytes, 1):
            audit.MAX_AST_PARSE_BYTES = max_ast_parse_bytes
            inventory = audit._extract_python_inventory(bot_root, [bot_source])
            records = inventory["callback_data"]
            assert {record["token"] for record in records} == expected
            assert all(record["file"] == "bot.py" for record in records)
            assert all(record["line"] > 0 for record in records)
    finally:
        audit.MAX_AST_PARSE_BYTES = original_max_ast_parse_bytes


def test_static_audit_keeps_raw_patterned_handlers_as_transport_evidence(tmp_path: Path) -> None:
    """Raw-regex handler registrations must not collapse into fake catch-alls."""

    audit = _load_audit_module()
    bot_root = tmp_path / "bot"
    web_root = tmp_path / "web"
    bot_root.mkdir()
    web_root.mkdir()
    bot_source = bot_root / "bot.py"
    bot_source.write_text(
        r'''
app.add_handler(CallbackQueryHandler(safe_mode_callback_guard))
app.add_handler(CallbackQueryHandler(handle_trend_video_flow_callback, pattern=r"^tvflow\|"))
app.add_handler(CallbackQueryHandler(handle_affiliate_callback, pattern=r"^affiliate_"))
''',
        encoding="utf-8",
    )
    (web_root / "app.py").write_text("app = FastAPI()", encoding="utf-8")

    expected = {
        ("safe_mode_callback_guard", "<catch-all>"),
        ("handle_trend_video_flow_callback", r"^tvflow\|"),
        ("handle_affiliate_callback", r"^affiliate_"),
    }
    original_max_ast_parse_bytes = audit.MAX_AST_PARSE_BYTES
    try:
        for max_ast_parse_bytes in (original_max_ast_parse_bytes, 1):
            audit.MAX_AST_PARSE_BYTES = max_ast_parse_bytes
            inventory = audit._extract_python_inventory(bot_root, [bot_source])
            actual = {(item["handler"], item["pattern"]) for item in inventory["callback_handlers"]}
            assert actual == expected
        audit.MAX_AST_PARSE_BYTES = 1
        result = audit.run_audit(bot_root, web_root, "baseline", tmp_path / "reports", tmp_path / "docs")
    finally:
        audit.MAX_AST_PARSE_BYTES = original_max_ast_parse_bytes

    gap = result["parity_gap"]
    assert gap["callback_handler_summary"] == {
        "total": 3,
        "observed_runtime_registrations": 3,
        "unreferenced_static_module_registrations": 0,
        "catch_all": 1,
        "patterned": 2,
        "product_action_claims": 0,
        "note": "CallbackQueryHandler registrations are Telegram transport evidence only. They are excluded from product-action coverage and never prove a browser route or Web runtime parity.",
    }
    assert {item["status"] for item in gap["callback_handler_mappings"]} == {"TELEGRAM_TRANSPORT_HANDLER"}
    assert not gap["callback_mappings"]
    assert gap["mapping_status_counts"].get("TELEGRAM_TRANSPORT_HANDLER", 0) == 0
    assert gap["source_counts"]["telegram_transport_handler_records"] == 3
    assert gap["metric_scope"]["excluded_telegram_transport_handlers"] == 3
    assert gap["coverage_comparability"] == {
        "status": "NOT_COMPARABLE_TO_PREVIOUS_AUDIT_PERCENTAGES",
        "feature_progress_claim": False,
        "reason": "Schema 1.7 retains the 1.6 inventory corrections and records the finite Free Hub prompt-library category template as fresh signed Gallery navigation only; its Bot suggestion and pending state are not Web contracts.",
        "scope_changes": [
            "CallbackQueryHandler registrations are Telegram transport evidence, not product actions.",
            "Records from unreferenced handlers/ package files remain evidence-only instead of mapped/guarded runtime parity.",
            "Bare N:N tuple values are treated as aspect-ratio configuration, while numeric-leading structured callbacks remain supported.",
            "Embedded formatted callback values such as family_action_{*}_{*} are retained as opaque templates instead of being dropped from the static inventory.",
            "tvflow callbacks are finite Bot-state dispositions instead of generic image/video/content/package route matches.",
            "Dynamic media-preview callback templates are typed Bot-state dispositions instead of unresolved Web media actions.",
            "The finite Free Hub prompt-library category template opens a fresh signed Web Gallery as navigation-only; it does not carry a Bot category token, suggestion set, or pending state into the browser.",
        ],
        "note": "Any percentage delta caused by these inventory corrections is not feature progress. Compare absolute routes/contracts and separately verified runtime evidence instead.",
    }


def test_static_audit_large_parser_preserves_source_lines_without_rescanning(tmp_path: Path) -> None:
    """The optimized large-file location index keeps 1-based audit evidence."""

    audit = _load_audit_module()
    bot_root = tmp_path / "bot"
    bot_root.mkdir()
    bot_source = bot_root / "bot.py"
    bot_source.write_text(
        'header = True\n'
        'button = InlineKeyboardButton("Trend", callback_data="tvflow|confirm_content")\n'
        '\n'
        'app.add_handler(CallbackQueryHandler(handle_trend_video_flow_callback, pattern=r"^tvflow\\\\|"))\n',
        encoding="utf-8",
    )

    original_max_ast_parse_bytes = audit.MAX_AST_PARSE_BYTES
    try:
        audit.MAX_AST_PARSE_BYTES = 1
        inventory = audit._extract_python_inventory(bot_root, [bot_source])
    finally:
        audit.MAX_AST_PARSE_BYTES = original_max_ast_parse_bytes

    assert {record["token"]: record["line"] for record in inventory["callback_data"]} == {
        "tvflow|confirm_content": 2,
    }
    assert inventory["callback_handlers"] == [
        {
            "handler": "handle_trend_video_flow_callback",
            "pattern": r"^tvflow\\|",
            "file": "bot.py",
            "line": 4,
        }
    ]


def test_static_audit_keeps_tvflow_callbacks_at_bot_authority_boundaries(tmp_path: Path) -> None:
    """Trend-video names must not inherit convenient-looking Web route claims."""

    audit = _load_audit_module()
    # These are exactly the generic keyword targets that used to upgrade
    # tvflow records to COPIED_GUARDED.  A finite Bot-state disposition must
    # win even when each matching-looking Web surface exists.
    routes = {"/membership", "/features/content", "/features/image", "/features/video"}
    expected = {
        "tvflow|cancel_content": (
            "BOT_TREND_CONFIRMATION_AND_BILLING_REQUIRED",
            "tvflow_cancel_content_requires_bot_pending_state",
            "customer",
            "NEEDS_FEATURE_DISPOSITION",
        ),
        "tvflow|confirm_content": (
            "BOT_TREND_CONFIRMATION_AND_BILLING_REQUIRED",
            "tvflow_confirm_content_requires_bot_billing_execution",
            "customer",
            "NEEDS_FEATURE_DISPOSITION",
        ),
        "tvflow|confirm_content_package": (
            "BOT_TREND_CONFIRMATION_AND_BILLING_REQUIRED",
            "tvflow_confirm_content_requires_bot_billing_execution",
            "customer",
            "NEEDS_FEATURE_DISPOSITION",
        ),
        "tvflow|cancel": (
            "BOT_TREND_PENDING_STATE_REQUIRED",
            "tvflow_cancel_requires_bot_pending_state",
            "customer",
            "NEEDS_FEATURE_DISPOSITION",
        ),
        "tvflow|image_scene_1": (
            "BOT_TREND_OUTPUT_AND_IMAGE_CONFIRMATION_REQUIRED",
            "tvflow_image_scene_requires_bot_output_credit_confirmation",
            "customer",
            "NEEDS_FEATURE_DISPOSITION",
        ),
        "tvflow|image_scene_2": (
            "BOT_TREND_OUTPUT_AND_IMAGE_CONFIRMATION_REQUIRED",
            "tvflow_image_scene_requires_bot_output_credit_confirmation",
            "customer",
            "NEEDS_FEATURE_DISPOSITION",
        ),
        "tvflow|image_scene_3": (
            "BOT_TREND_OUTPUT_AND_IMAGE_CONFIRMATION_REQUIRED",
            "tvflow_image_scene_requires_bot_output_credit_confirmation",
            "customer",
            "NEEDS_FEATURE_DISPOSITION",
        ),
        "tvflow|save_image": (
            "TELEGRAM_GUIDANCE_OR_CHAT_STATE",
            "tvflow_save_image_is_not_a_web_asset",
            "customer",
            "NEEDS_FEATURE_DISPOSITION",
        ),
        "tvflow|edit_prompt": (
            "TELEGRAM_GUIDANCE_OR_CHAT_STATE",
            "tvflow_prompt_guidance_is_not_web_state_transfer",
            "customer",
            "NEEDS_FEATURE_DISPOSITION",
        ),
        "tvflow|rewrite": (
            "TELEGRAM_GUIDANCE_OR_CHAT_STATE",
            "tvflow_prompt_guidance_is_not_web_state_transfer",
            "customer",
            "NEEDS_FEATURE_DISPOSITION",
        ),
        "tvflow|video_prompt": (
            "TELEGRAM_GUIDANCE_OR_CHAT_STATE",
            "tvflow_prompt_guidance_is_not_web_state_transfer",
            "customer",
            "NEEDS_FEATURE_DISPOSITION",
        ),
        "tvflow|admin_video_image_7_1": (
            "BOT_ADMIN_SMOKE_REQUIRED",
            "tvflow_admin_smoke_requires_bot_authority",
            "admin",
            "TELEGRAM_ONLY",
        ),
        "tvflow|image_warranty_retry_7": (
            "BOT_IMAGE_JOB_WARRANTY_REQUIRED",
            "tvflow_warranty_retry_requires_bot_job_state",
            "customer",
            "NEEDS_FEATURE_DISPOSITION",
        ),
    }

    for callback, (target, resolution, classification, status) in expected.items():
        mapped = audit._map_callback(callback, "callback_data", {"file": "bot.py", "line": 1}, routes)
        audit._annotate_feature_disposition(mapped)
        assert mapped["target"] == target
        assert mapped["resolution"] == resolution
        assert mapped["classification"] == classification
        assert mapped["status"] == status
        assert mapped["status"] not in {"MAPPED_TO_EXISTING_ROUTE", "COPIED_GUARDED", "NAVIGATION_ONLY"}
        assert "NO_RUNTIME_CLAIM" in mapped["source_dispositions"]
        if status == "NEEDS_FEATURE_DISPOSITION":
            assert mapped["fallback_family"] == "tvflow"
        else:
            assert "fallback_family" not in mapped

    template_expectations = {
        "tvflow|regen_scene_{*}": "BOT_TREND_OUTPUT_AND_IMAGE_CONFIRMATION_REQUIRED",
        "tvflow|image_video_real_{*}_{*}": "BOT_IMAGE_TO_VIDEO_CONTEXT_REQUIRED",
        "tvflow|image_video_prompt_select_{*}_{*}": "BOT_IMAGE_TO_VIDEO_CONTEXT_REQUIRED",
        "tvflow|image_video_prompts_{*}": "BOT_IMAGE_TO_VIDEO_CONTEXT_REQUIRED",
        "tvflow|music_image_{*}": "BOT_IMAGE_TO_VIDEO_CONTEXT_REQUIRED",
        "tvflow|image_back_{*}": "BOT_IMAGE_TO_VIDEO_CONTEXT_REQUIRED",
    }
    for template, target in template_expectations.items():
        mapped = audit._map_callback_template(template, {"file": "bot.py", "line": 1}, routes)
        assert mapped is not None
        audit._annotate_feature_disposition(mapped)
        assert mapped["target"] == target
        assert mapped["status"] == "NEEDS_FEATURE_DISPOSITION"
        assert mapped["status"] not in {"MAPPED_TO_EXISTING_ROUTE", "COPIED_GUARDED"}
        assert "NO_RUNTIME_CLAIM" in mapped["source_dispositions"]

    admin_template = audit._map_callback_template(
        "tvflow|admin_video_image_{*}_{*}",
        {"file": "bot.py", "line": 1},
        routes,
    )
    assert admin_template is not None
    assert admin_template["target"] == "BOT_ADMIN_SMOKE_REQUIRED"
    assert admin_template["classification"] == "admin"
    assert admin_template["status"] == "TELEGRAM_ONLY"

    unknown = audit._map_callback("tvflow|future_action", "callback_data", {"file": "bot.py", "line": 1}, routes)
    assert unknown["target"] == "BOT_TRENDFLOW_SOURCE_REVIEW_REQUIRED"
    assert unknown["status"] == "NEEDS_FEATURE_DISPOSITION"
    assert "NO_RUNTIME_CLAIM" in unknown["source_dispositions"]

    # Exercise the real static inventory path, including f-string templates,
    # so an implementation cannot accidentally bypass the tvflow interceptor.
    bot_root = tmp_path / "bot"
    web_root = tmp_path / "web"
    bot_root.mkdir()
    web_root.mkdir()
    (bot_root / "bot.py").write_text(
        '''
InlineKeyboardButton("Confirm", callback_data="tvflow|confirm_content_package")
InlineKeyboardButton("Image", callback_data="tvflow|image_scene_1")
job_id = "ignored"
choice = "ignored"
InlineKeyboardButton("Video", callback_data=f"tvflow|image_video_real_{job_id}_{choice}")
InlineKeyboardButton("Admin", callback_data=f"tvflow|admin_video_image_{job_id}_{choice}")
''',
        encoding="utf-8",
    )
    (web_root / "app.py").write_text(
        '''
app = FastAPI()
@app.get("/membership")
async def membership():
    return {}
@app.get("/features/image")
async def image():
    return {}
@app.get("/features/video")
async def video():
    return {}
''',
        encoding="utf-8",
    )
    result = audit.run_audit(bot_root, web_root, "baseline", tmp_path / "reports", tmp_path / "docs")
    report_mappings = {
        item["source"]: item
        for item in result["parity_gap"]["callback_mappings"] + result["parity_gap"]["callback_template_mappings"]
        if str(item.get("source") or "").startswith("tvflow|")
    }
    assert set(report_mappings) == {
        "tvflow|confirm_content_package",
        "tvflow|image_scene_1",
        "tvflow|image_video_real_{*}_{*}",
        "tvflow|admin_video_image_{*}_{*}",
    }
    assert not {
        item["status"]
        for item in report_mappings.values()
    }.intersection({"MAPPED_TO_EXISTING_ROUTE", "COPIED_GUARDED", "NAVIGATION_ONLY"})
    assert report_mappings["tvflow|admin_video_image_{*}_{*}"]["status"] == "TELEGRAM_ONLY"
    assert (tmp_path / "docs" / "TVFLOW_CALLBACK_CONTRACT.md").is_file()


def test_static_audit_keeps_dynamic_media_preview_callbacks_telegram_only(tmp_path: Path) -> None:
    """Bot preview cache indexes cannot become browser media actions."""

    audit = _load_audit_module()
    routes = {"/media-workspace", "/{page_path:path}"}
    expectations = {
        "play_{*}|{*}": (
            "TELEGRAM_ONLY",
            "reviewed_bot_preview_play_telegram_only_web_owned_preview_separate",
            "TELEGRAM_CHAT_DELIVERY",
        ),
        "select_{*}|{*}": (
            "TELEGRAM_ONLY",
            "reviewed_bot_media_select_telegram_only_web_owned_reference_separate",
            "BOT_MEDIA_SELECTION_STATE",
        ),
        "license_{*}|1": (
            "TELEGRAM_ONLY",
            "reviewed_bot_media_license_telegram_only_web_rights_note_separate",
            "TELEGRAM_CHAT_GUIDANCE",
        ),
        "license_music|{*}": (
            "TELEGRAM_ONLY",
            "reviewed_bot_media_license_telegram_only_web_rights_note_separate",
            "TELEGRAM_CHAT_GUIDANCE",
        ),
        "play_media|{*}": (
            "TELEGRAM_ONLY",
            "reviewed_bot_preview_play_telegram_only_web_owned_preview_separate",
            "TELEGRAM_CHAT_DELIVERY",
        ),
        "select_media|{*}": (
            "TELEGRAM_ONLY",
            "reviewed_bot_media_select_telegram_only_web_owned_reference_separate",
            "BOT_MEDIA_SELECTION_STATE",
        ),
    }

    for template, (target, resolution, specific_disposition) in expectations.items():
        mapped = audit._map_callback_template(template, {"file": "bot.py", "line": 1}, routes)
        assert mapped is not None
        audit._annotate_feature_disposition(mapped)
        assert mapped["target"] == target
        assert mapped["resolution"] == resolution
        assert mapped["classification"] == "customer"
        assert mapped["status"] == "TELEGRAM_ONLY"
        assert "fallback_family" not in mapped
        assert specific_disposition in mapped["source_dispositions"]
        assert "NO_RUNTIME_CLAIM" in mapped["source_dispositions"]
        assert mapped["target"] == "TELEGRAM_ONLY"

    bot_root = tmp_path / "bot"
    web_root = tmp_path / "web"
    bot_root.mkdir()
    web_root.mkdir()
    (bot_root / "bot.py").write_text(
        '''
kind = "ignored"
index = "ignored"
InlineKeyboardButton("Play", callback_data=f"play_{kind}|{index}")
InlineKeyboardButton("Select", callback_data=f"select_{kind}|{index}")
InlineKeyboardButton("License", callback_data=f"license_{kind}|1")
InlineKeyboardButton("Music license", callback_data=f"license_music|{index}")
InlineKeyboardButton("Media play", callback_data=f"play_media|{index}")
InlineKeyboardButton("Media select", callback_data=f"select_media|{index}")
''',
        encoding="utf-8",
    )
    (web_root / "app.py").write_text(
        '''
app = FastAPI()
@app.get("/media-workspace")
async def media_workspace():
    return {}
@app.get("/{page_path:path}")
async def portal(page_path):
    return {}
''',
        encoding="utf-8",
    )

    result = audit.run_audit(bot_root, web_root, "baseline", tmp_path / "reports", tmp_path / "docs")
    mappings = {
        item["source"]: item
        for item in result["parity_gap"]["callback_template_mappings"]
    }
    assert set(mappings) == set(expectations)
    assert {item["status"] for item in mappings.values()} == {"TELEGRAM_ONLY"}
    assert all(str(item["target"]) == "TELEGRAM_ONLY" for item in mappings.values())
    backlog = {item["family"]: item for item in result["parity_gap"]["feature_disposition_backlog"]}
    assert "media_preview" not in backlog
    contract = tmp_path / "docs" / "MEDIA_PREVIEW_CALLBACK_CONTRACT.md"
    assert contract.is_file()
    assert "Bot cache index" in contract.read_text(encoding="utf-8")
    environment_contract = tmp_path / "docs" / "ENV_AND_PROVIDER_MAP.md"
    assert environment_contract.is_file()
    assert "WEBAPP_MEDIA_WORKSPACE_PREVIEW_ENABLED" in environment_contract.read_text(encoding="utf-8")


def test_static_audit_does_not_mistake_aspect_ratio_tuples_for_callbacks(tmp_path: Path) -> None:
    """A bare numeric ratio needs a parent workflow, not a callback record."""

    audit = _load_audit_module()
    bot_root = tmp_path / "bot"
    bot_root.mkdir()
    bot_source = bot_root / "bot.py"
    bot_source.write_text(
        '''
keyboard_rows = [
    ("Square", "1:1"),
    ("Wide", "21:9"),
    ("Portrait", "3:4"),
    ("Classic", "4:3"),
    ("Tall", "4:5"),
    ("Two-factor", "2fa|enable"),
    ("Valid callback", "freehub|meta"),
]
''',
        encoding="utf-8",
    )

    original_max_ast_parse_bytes = audit.MAX_AST_PARSE_BYTES
    try:
        for max_ast_parse_bytes in (original_max_ast_parse_bytes, 1):
            audit.MAX_AST_PARSE_BYTES = max_ast_parse_bytes
            inventory = audit._extract_python_inventory(bot_root, [bot_source])
            assert {record["token"] for record in inventory["callback_data"]} == {"2fa|enable", "freehub|meta"}
    finally:
        audit.MAX_AST_PARSE_BYTES = original_max_ast_parse_bytes


def test_static_audit_keeps_unreferenced_handler_modules_out_of_runtime_parity(tmp_path: Path) -> None:
    """Legacy handlers must remain evidence, not guarded/mapped Web parity."""

    audit = _load_audit_module()
    bot_root = tmp_path / "bot"
    web_root = tmp_path / "web"
    handlers_root = bot_root / "handlers"
    handlers_root.mkdir(parents=True)
    web_root.mkdir()
    (bot_root / "bot.py").write_text(
        '''
button_a = InlineKeyboardButton("Trend", callback_data="tvflow|confirm_content")
button_b = InlineKeyboardButton("Transcribe", callback_data="tr_transcribe")
''',
        encoding="utf-8",
    )
    (handlers_root / "affiliate_handler.py").write_text(
        'button = InlineKeyboardButton("Affiliate", callback_data="affiliate_join")',
        encoding="utf-8",
    )
    (handlers_root / "freelance_handler.py").write_text(
        'button = InlineKeyboardButton("Freelance", callback_data="freelance_post")',
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
    gap = result["parity_gap"]
    observation = gap["handler_module_observation"]
    active = {item["source"]: item for item in gap["callback_mappings"]}
    unreferenced = {item["source"]: item for item in gap["unreferenced_static_module_mappings"]}

    assert observation["status"] == "HANDLERS_UNREFERENCED_BY_OBSERVED_ENTRYPOINT"
    assert observation["unreferenced_module_files"] == [
        "handlers/affiliate_handler.py",
        "handlers/freelance_handler.py",
    ]
    assert set(active) == {"tvflow|confirm_content", "tr_transcribe"}
    assert set(unreferenced) == {"affiliate_join", "freelance_post"}
    assert {item["status"] for item in unreferenced.values()} == {"UNREFERENCED_BY_OBSERVED_ENTRYPOINT"}
    assert gap["source_counts"]["observed_runtime_product_action_mappings"] == 2
    assert gap["source_counts"]["unreferenced_static_module_records"] == 2
    assert gap["metric_scope"]["excluded_unreferenced_handler_package_records"] == 2
    assert "affiliate_join" not in active
    assert "freelance_post" not in active

    for callback in ("tvflow|confirm_content", "tr_transcribe", "affiliate_join", "freelance_post"):
        mapped = audit._map_callback(callback, "callback_data", {"file": "bot.py", "line": 1}, {"/{page_path:path}"})
        audit._annotate_feature_disposition(mapped)
        assert mapped["status"] == "NEEDS_FEATURE_DISPOSITION"
        assert mapped["status"] not in {"MAPPED_TO_EXISTING_ROUTE", "COPIED_GUARDED"}
        assert "NO_RUNTIME_CLAIM" in mapped["source_dispositions"]

    assert active["tvflow|confirm_content"]["fallback_family"] == "tvflow"
    assert active["tr_transcribe"]["fallback_family"] == "tr_transcribe"
    assert (tmp_path / "docs" / "UNREFERENCED_STATIC_MODULES.md").is_file()


def test_static_audit_keeps_handler_modules_in_scope_when_entrypoint_imports_them(tmp_path: Path) -> None:
    """The observed import closure must be conservative, never prune a live package."""

    audit = _load_audit_module()
    bot_root = tmp_path / "bot"
    handlers_root = bot_root / "handlers"
    handlers_root.mkdir(parents=True)
    (bot_root / "bot.py").write_text("import handlers\n", encoding="utf-8")
    (handlers_root / "__init__.py").write_text("", encoding="utf-8")
    (handlers_root / "affiliate_handler.py").write_text("pass\n", encoding="utf-8")

    observation = audit._unreferenced_handler_module_observation(bot_root)

    assert observation["status"] == "HANDLERS_REACHABLE_FROM_OBSERVED_ENTRYPOINT"
    assert observation["unreferenced_module_files"] == []


def test_static_audit_derives_all_creative_motion_guide_keyboard_literals_without_importing_bot(tmp_path: Path) -> None:
    """Nested localized tuple labels must not hide the 23 finite Motion actions."""

    audit = _load_audit_module()
    bot_root = tmp_path / "bot"
    bot_root.mkdir()
    bot_source = bot_root / "bot.py"
    bot_source.write_text(
        '''
raise RuntimeError("the static auditor must never execute this source")

def creative_motion_topic_keyboard(lang="vi"):
    return [
        (ui_text(lang, "motion.product"), "motion|topic|product"),
        (ui_text(lang, "motion.affiliate"), "motion|topic|affiliate"),
        (ui_text(lang, "motion.ai_tool"), "motion|topic|ai_tool"),
        (ui_text(lang, "motion.place"), "motion|topic|place"),
        (ui_text(lang, "motion.fashion"), "motion|topic|fashion"),
        (ui_text(lang, "motion.food"), "motion|topic|food"),
        (ui_text(lang, "motion.education"), "motion|topic|education"),
        (ui_text(lang, "motion.story"), "motion|topic|story"),
        (ui_text(lang, "motion.custom"), "motion|topic|custom"),
    ]

def creative_motion_suggestions_keyboard(lang="vi"):
    return [
        ("one" if lang == "vi" else "one", "motion|choice|1"),
        ("two" if lang == "vi" else "two", "motion|choice|2"),
        ("three" if lang == "vi" else "three", "motion|choice|3"),
        ("more" if lang == "vi" else "more", "motion|refresh"),
        ("back" if lang == "vi" else "back", "motion|start"),
    ]

def creative_motion_style_keyboard(lang="vi"):
    return [
        (ui_text(lang, "motion.style.cinematic"), "motion|style|cinematic"),
        (ui_text(lang, "motion.style.tiktok"), "motion|style|tiktok"),
        (ui_text(lang, "motion.style.tutorial"), "motion|style|tutorial"),
        (ui_text(lang, "motion.style.ads"), "motion|style|ads"),
        (ui_text(lang, "motion.style.fpv"), "motion|style|fpv"),
        (ui_text(lang, "motion.style.reveal"), "motion|style|reveal"),
        (ui_text(lang, "motion.style.ugc"), "motion|style|ugc"),
        ("back", "motion|back_suggestions"),
    ]

def creative_motion_result_keyboard(lang="vi"):
    return [("back", "motion|back_style")]
''',
        encoding="utf-8",
    )

    original_max_ast_parse_bytes = audit.MAX_AST_PARSE_BYTES
    try:
        # Force the bounded text scanner; no Bot import or AST evaluation is
        # necessary for the nested ``ui_text(...)`` keyboard rows.
        audit.MAX_AST_PARSE_BYTES = 1
        inventory = audit._extract_python_inventory(bot_root, [bot_source])
    finally:
        audit.MAX_AST_PARSE_BYTES = original_max_ast_parse_bytes

    records = {record["token"]: record for record in inventory["callback_data"]}
    assert set(records) == set(audit.CREATIVE_MOTION_GUIDE_CALLBACKS)
    assert len(records) == 23
    assert records["motion|topic|product"]["resolution"] == "reviewed_creative_motion_guide_keyboard_literal"
    assert records["motion|topic|product"]["helper"] == "creative_motion_topic_keyboard"
    assert records["motion|style|cinematic"]["helper"] == "creative_motion_style_keyboard"


def test_creative_motion_guide_audit_maps_exactly_23_text_only_intents_and_fails_closed() -> None:
    """The new guide is distinct from Image Motion and never replays Bot state."""

    audit = _load_audit_module()
    evidence = {"file": "bot.py", "line": 1}
    routes = {"/{page_path:path}"}

    assert len(audit.CREATIVE_MOTION_GUIDE_CALLBACKS) == 23
    assert all(prefix != "motion|" for prefix, _target, _classification in audit.DYNAMIC_CALLBACK_TEMPLATE_ROUTE_OVERRIDES)
    for token in sorted(audit.CREATIVE_MOTION_GUIDE_CALLBACKS):
        mapped = audit._map_callback(token, "callback_data", evidence, routes)
        assert mapped["target"] == "/video-studio/motion-guide"
        assert mapped["classification"] == "customer"
        assert mapped["status"] == "COPIED_GUARDED"
        assert mapped["resolution"] == "reviewed_creative_motion_guide_web_native_text_only"
        assert mapped["creative_motion_guide_authority"] == "SIGNED_CUSTOMER_WEB_NATIVE_TEXT_GUIDE"
        assert mapped["creative_motion_guide_execution_boundary"] == "DETERMINISTIC_TEXT_ONLY_NO_PERSISTENCE_OR_EXTERNAL_RUNTIME"
        assert "BOT_CREATIVE_MOTION_PENDING_STATE_NOT_REPLAYED" in mapped["source_dispositions"]
        assert "NO_TELEGRAM_STATE_MEDIA_PROVIDER_JOB_WALLET_PAYMENT_BRIDGE_ASSET_PUBLISH_OR_DELIVERY_ACTION" in mapped["source_dispositions"]
        assert "image-motion" not in mapped["target"]

    for token in ("motion|cancel", "motion|style|future", "MOTION|start"):
        mapped = audit._map_callback(token, "callback_data", evidence, routes)
        assert mapped["target"] == "CREATIVE_MOTION_GUIDE_SOURCE_REVIEW_REQUIRED"
        assert mapped["status"] == "NEEDS_FEATURE_DISPOSITION"
        assert "SOURCE_STATE_MACHINE_REQUIRED" in mapped["source_dispositions"]


def test_cinematic_ad_audit_maps_only_finite_planner_intents_to_fresh_web_navigation() -> None:
    """Cinematic Ad cannot inherit a generic `adconcept|` compatibility route."""

    audit = _load_audit_module()
    evidence = {"file": "bot.py", "line": 1}
    routes = {"/{page_path:path}"}

    assert all(prefix != "adconcept|" for prefix, _target, _classification in audit.DYNAMIC_CALLBACK_TEMPLATE_ROUTE_OVERRIDES)

    for token in sorted(audit.CINEMATIC_AD_CONCEPT_FRESH_WEB_PLANNER_CALLBACKS):
        mapped = audit._map_callback(token, "callback_data", evidence, routes)
        assert mapped["target"] == "/video-studio/cinematic-concept"
        assert mapped["classification"] == "customer"
        assert mapped["status"] == "NAVIGATION_ONLY"
        assert mapped["resolution"] == "reviewed_cinematic_ad_fresh_web_planner_navigation"
        assert mapped["cinematic_ad_concept_authority"] == "SIGNED_CUSTOMER_WEB_NATIVE_COMPOSER"
        assert mapped["cinematic_ad_concept_save_boundary"] == "EXPLICIT_SERVER_RECOMPUTED_OWNER_VIDEO_PLAN_ONLY"
        assert "BOT_CINEMATIC_AD_PENDING_STATE_NOT_REPLAYED" in mapped["source_dispositions"]
        assert "NO_RUNTIME_CLAIM" in mapped["source_dispositions"]

    for action in ("concept_choice", "motion_choice", "image_prompt_choice", "video_prompt_choice", "music_choice"):
        for ordinal in sorted(audit.CINEMATIC_AD_CONCEPT_PLANNER_ORDINALS):
            mapped = audit._map_callback(f"adconcept|{action}|{ordinal}", "callback_data", evidence, routes)
            assert mapped["target"] == "BOT_CINEMATIC_AD_TRANSIENT_STATE_NOT_REPLAYED"
            assert mapped["status"] == "NEEDS_FEATURE_DISPOSITION"
        unreviewed = audit._map_callback(f"adconcept|{action}|4", "callback_data", evidence, routes)
        assert unreviewed["target"] == "CINEMATIC_AD_SOURCE_REVIEW_REQUIRED"
        assert unreviewed["status"] == "NEEDS_FEATURE_DISPOSITION"


def test_cinematic_ad_audit_guards_bot_state_runtime_and_admin_callbacks() -> None:
    """The Bot conversation cannot turn lock/save/provider paths into Web actions."""

    audit = _load_audit_module()
    evidence = {"file": "bot.py", "line": 1}
    routes = {"/{page_path:path}"}

    for token in sorted(audit.CINEMATIC_AD_CONCEPT_BOT_STATE_CALLBACKS):
        mapped = audit._map_callback(token, "callback_data", evidence, routes)
        assert mapped["target"] == "BOT_CINEMATIC_AD_TRANSIENT_STATE_NOT_REPLAYED"
        assert mapped["status"] == "NEEDS_FEATURE_DISPOSITION"
        assert mapped["resolution"] == "bot_cinematic_ad_transient_state_requires_fresh_web_compose"
        assert "BOT_CINEMATIC_AD_SELECTION_LOCK_OR_PACKAGE_STATE_NOT_REPLAYED" in mapped["source_dispositions"]
        assert "NO_RUNTIME_CLAIM" in mapped["source_dispositions"]

    for template in sorted(audit.CINEMATIC_AD_CONCEPT_BOT_STATE_CALLBACK_TEMPLATES):
        mapped = audit._map_callback_template(template, evidence, routes)
        assert mapped is not None
        assert mapped["target"] == "BOT_CINEMATIC_AD_TRANSIENT_STATE_NOT_REPLAYED"
        assert mapped["status"] == "NEEDS_FEATURE_DISPOSITION"

    save = audit._map_callback("adconcept|save_video_package", "callback_data", evidence, routes)
    assert "WEB_EXPLICIT_SERVER_RECOMPUTED_OWNER_PLAN_SAVE_REQUIRED" in save["source_dispositions"]

    for token in sorted(audit.CINEMATIC_AD_CONCEPT_RUNTIME_GUARDED_CALLBACKS):
        mapped = audit._map_callback(token, "callback_data", evidence, routes)
        assert mapped["target"] == "CINEMATIC_AD_RUNTIME_CONTRACT_REQUIRED"
        assert mapped["status"] == "NEEDS_FEATURE_DISPOSITION"
        assert "CANONICAL_PROVIDER_JOB_WALLET_PAYMENT_OR_FINALIZATION_GUARD" in mapped["source_dispositions"]

    for template in sorted(audit.CINEMATIC_AD_CONCEPT_RUNTIME_GUARDED_CALLBACK_TEMPLATES):
        mapped = audit._map_callback_template(template, evidence, routes)
        assert mapped is not None
        assert mapped["target"] == "CINEMATIC_AD_RUNTIME_CONTRACT_REQUIRED"
        assert mapped["status"] == "NEEDS_FEATURE_DISPOSITION"

    for token in sorted(audit.CINEMATIC_AD_CONCEPT_TELEGRAM_ONLY_CALLBACKS):
        mapped = audit._map_callback(token, "callback_data", evidence, routes)
        assert mapped["target"] == "TELEGRAM_ONLY"
        assert mapped["classification"] == "admin"
        assert mapped["status"] == "TELEGRAM_ONLY"
        assert "BOT_PROVIDER_SMOKE_EXECUTION" in mapped["source_dispositions"]

    stale = audit._map_callback("adconcept|image_prompts", "callback_data", evidence, routes)
    assert stale["target"] == "CINEMATIC_AD_STALE_CALLBACK_REVIEW_REQUIRED"
    assert stale["status"] == "NEEDS_FEATURE_DISPOSITION"
    assert "NO_RUNTIME_CLAIM" in stale["source_dispositions"]

    unreviewed = audit._map_callback("adconcept|future_unreviewed_action", "callback_data", evidence, routes)
    assert unreviewed["target"] == "CINEMATIC_AD_SOURCE_REVIEW_REQUIRED"
    assert unreviewed["status"] == "NEEDS_FEATURE_DISPOSITION"


def test_vproduct_audit_maps_only_four_fresh_intents_to_the_web_planner() -> None:
    """Task3D callbacks must not inherit a broad Video Product Web route."""

    audit = _load_audit_module()
    evidence = {"file": "bot.py", "line": 1}
    routes = {"/{page_path:path}"}

    assert all(prefix != "vproduct|" for prefix, _target, _classification in audit.DYNAMIC_CALLBACK_TEMPLATE_ROUTE_OVERRIDES)
    assert audit.VPRODUCT_FRESH_WEB_PLANNER_CALLBACKS == {
        "vproduct|ideas|script_image_video",
        "vproduct|input_text|script_image_video",
        "vproduct|ideas|multi_scene_film",
        "vproduct|input_text|multi_scene_film",
    }
    for token in sorted(audit.VPRODUCT_FRESH_WEB_PLANNER_CALLBACKS):
        mapped = audit._map_callback(token, "callback_data", evidence, routes)
        assert mapped["target"] == "/video-studio/script-to-screen-planner"
        assert mapped["classification"] == "customer"
        assert mapped["status"] == "NAVIGATION_ONLY"
        assert mapped["resolution"] == "reviewed_vproduct_fresh_web_planner_navigation"
        assert mapped["vproduct_authority"] == "SIGNED_CUSTOMER_WEB_NATIVE_SCRIPT_TO_SCREEN_PLANNER"
        assert mapped["vproduct_save_boundary"] == "EXPLICIT_SERVER_RECOMPUTED_OWNER_VIDEO_PLAN_ONLY"
        assert "BOT_VPRODUCT_SESSION_NOT_REPLAYED" in mapped["source_dispositions"]
        assert "NO_RUNTIME_CLAIM" in mapped["source_dispositions"]

    # Callback payloads are source-sensitive: a case variant is not an
    # independently reviewed Web navigation intent.
    case_variant = audit._map_callback("VPRODUCT|ideas|script_image_video", "callback_data", evidence, routes)
    assert case_variant["target"] == "VPRODUCT_SOURCE_REVIEW_REQUIRED"
    assert case_variant["status"] == "NEEDS_FEATURE_DISPOSITION"


def test_vproduct_audit_keeps_guided_prompt_runtime_and_dynamic_state_fail_closed() -> None:
    """No Bot session, package, prompt or render transition becomes a browser action."""

    audit = _load_audit_module()
    evidence = {"file": "bot.py", "line": 1}
    routes = {"/{page_path:path}"}

    for token in (
        "vproduct|open|script_image_video",
        "vproduct|open|multi_scene_film",
        "vproduct|ideas|video_idea",
        "vproduct|input_text|video_reference",
        "vproduct|aspect|9:16",
        "vproduct|camera|skip",
        "vproduct|target|video",
        "vproduct|scene_count|2",
        "vproduct|scene_skip",
    ):
        mapped = audit._map_callback(token, "callback_data", evidence, routes)
        assert mapped["target"] == "BOT_VPRODUCT_GUIDED_STATE_NOT_REPLAYED"
        assert mapped["status"] == "NEEDS_FEATURE_DISPOSITION"
        assert "BOT_VPRODUCT_GUIDED_SESSION_STATE" in mapped["source_dispositions"]
        assert "NO_RUNTIME_CLAIM" in mapped["source_dispositions"]

    for token in ("vproduct|prompt_image_copy", "vproduct|prompt_video|2", "vproduct|export|json"):
        mapped = audit._map_callback(token, "callback_data", evidence, routes)
        assert mapped["target"] == "BOT_VPRODUCT_PROMPT_OR_DELIVERY_STATE_NOT_REPLAYED"
        assert mapped["status"] == "NEEDS_FEATURE_DISPOSITION"
        assert "NO_RUNTIME_CLAIM" in mapped["source_dispositions"]


def test_storypack_audit_maps_only_finite_entry_and_template_literals_to_fresh_web_navigation() -> None:
    """Storypack must not inherit a broad callback-family compatibility route."""

    audit = _load_audit_module()
    evidence = {"file": "bot.py", "line": 1}
    routes = {"/{page_path:path}"}

    assert all(prefix != "storypack|" for prefix, _target, _classification in audit.DYNAMIC_CALLBACK_TEMPLATE_ROUTE_OVERRIDES)
    assert audit.STORYPACK_FRESH_WEB_COMPOSER_CALLBACKS == {
        "storypack|start",
        "storypack|template|product_ad",
        "storypack|template|cinematic_story",
        "storypack|template|tiktok_reels",
        "storypack|template|tutorial",
        "storypack|template|shop_affiliate",
        "storypack|template|custom",
    }
    for token in sorted(audit.STORYPACK_FRESH_WEB_COMPOSER_CALLBACKS):
        mapped = audit._map_callback(token, "callback_data", evidence, routes)
        assert mapped["target"] == "/video-studio/storyboard-composer"
        assert mapped["classification"] == "customer"
        assert mapped["status"] == "NAVIGATION_ONLY"
        assert mapped["resolution"] == "reviewed_storypack_fresh_web_composer_navigation"
        assert mapped["storypack_authority"] == "SIGNED_CUSTOMER_WEB_NATIVE_STORYBOARD_COMPOSER"
        assert mapped["storypack_save_boundary"] == "EXPLICIT_SERVER_RECOMPUTED_OWNER_VIDEO_PLAN_ONLY"
        assert "BOT_STORYPACK_PENDING_AND_LATEST_STATE_NOT_REPLAYED" in mapped["source_dispositions"]
        assert "NO_RUNTIME_CLAIM" in mapped["source_dispositions"]

    case_variant = audit._map_callback("STORYPACK|start", "callback_data", evidence, routes)
    assert case_variant["target"] == "STORYPACK_SOURCE_REVIEW_REQUIRED"
    assert case_variant["status"] == "NEEDS_FEATURE_DISPOSITION"


def test_storypack_audit_keeps_bot_state_prompt_runtime_and_dynamic_values_fail_closed() -> None:
    """Storypack state/copy/media paths cannot reset, mutate or execute through Web."""

    audit = _load_audit_module()
    evidence = {"file": "bot.py", "line": 1}
    routes = {"/{page_path:path}"}

    for token in (
        "storypack|set_platform|facebook",
        # The frozen Bot keyboard uses this exact capitalized label. It is a
        # symbolic state disposition, never a fresh route/action.
        "storypack|set_platform|Facebook",
        "storypack|set_ratio|9:16",
        "storypack|set_duration|30",
        "storypack|set_style|cinematic",
        "storypack|set_goal|introduce",
        "storypack|concept|2",
        "storypack|brief_custom",
        "storypack|edit_requirement",
        "storypack|regenerate_concepts",
        "storypack|back_detail",
        "storypack|save",
        "storypack|lock",
    ):
        mapped = audit._map_callback(token, "callback_data", evidence, routes)
        assert mapped["target"] == "BOT_STORYPACK_STATE_NOT_REPLAYED"
        assert mapped["status"] == "NEEDS_FEATURE_DISPOSITION"
        assert "BOT_STORYPACK_PENDING_OR_LATEST_PLAN_STATE" in mapped["source_dispositions"]
        assert "NO_RUNTIME_CLAIM" in mapped["source_dispositions"]

    for token in (
        "storypack|image_prompts",
        "storypack|video_prompts",
        "storypack|meta_ai_prompt",
        "storypack|copy_plan",
        "storypack|copy_meta_ai_prompt",
        "storypack|regenerate_meta_ai_prompts",
    ):
        mapped = audit._map_callback(token, "callback_data", evidence, routes)
        assert mapped["target"] == "BOT_STORYPACK_PROMPT_OR_DELIVERY_STATE_NOT_REPLAYED"
        assert mapped["status"] == "NEEDS_FEATURE_DISPOSITION"
        assert "NO_RUNTIME_CLAIM" in mapped["source_dispositions"]

    for token in (
        "storypack|create_or_upload_images",
        "storypack|upload_images_guard",
        "storypack|image_keyframes",
        "storypack|preview",
        "storypack|create_video_ai",
        "storypack|ai_video",
    ):
        mapped = audit._map_callback(token, "callback_data", evidence, routes)
        assert mapped["target"] == "STORYPACK_RUNTIME_OR_MEDIA_CONTRACT_REQUIRED"
        assert mapped["status"] == "NEEDS_FEATURE_DISPOSITION"
        assert "CANONICAL_MEDIA_PROVIDER_JOB_WALLET_PAYMENT_OR_RENDER_GUARD" in mapped["source_dispositions"]
        assert "NO_RUNTIME_CLAIM" in mapped["source_dispositions"]

    for token in (
        "storypack|template|unknown",
        "storypack|future_unreviewed_action",
        "storypack|start|unexpected",
    ):
        mapped = audit._map_callback(token, "callback_data", evidence, routes)
        assert mapped["target"] == "STORYPACK_SOURCE_REVIEW_REQUIRED"
        assert mapped["status"] == "NEEDS_FEATURE_DISPOSITION"
        assert "NO_RUNTIME_CLAIM" in mapped["source_dispositions"]

    expected_templates = {
        "storypack|set_platform|{*}": "BOT_STORYPACK_STATE_NOT_REPLAYED",
        "storypack|concept|{*}": "BOT_STORYPACK_STATE_NOT_REPLAYED",
        "storypack|copy_meta_ai_prompt|{*}": "BOT_STORYPACK_PROMPT_OR_DELIVERY_STATE_NOT_REPLAYED",
        "storypack|create_video_ai|{*}": "STORYPACK_RUNTIME_OR_MEDIA_CONTRACT_REQUIRED",
        "storypack|template|{*}": "STORYPACK_SOURCE_REVIEW_REQUIRED",
        "storypack|{*}|{*}": "STORYPACK_SOURCE_REVIEW_REQUIRED",
    }
    for template, target in expected_templates.items():
        mapped = audit._map_callback_template(template, evidence, routes)
        assert mapped is not None
        assert mapped["target"] == target
        assert mapped["status"] == "NEEDS_FEATURE_DISPOSITION"
        assert "NO_RUNTIME_CLAIM" in mapped["source_dispositions"]

    for token in ("vproduct|prompt_image_package|50", "vproduct|prompt_image_execute", "vproduct|prompt_video_create", "vproduct|render"):
        mapped = audit._map_callback(token, "callback_data", evidence, routes)
        assert mapped["target"] == "VPRODUCT_RUNTIME_PACKAGE_PROVIDER_OR_PAYMENT_CONTRACT_REQUIRED"
        assert mapped["status"] == "NEEDS_FEATURE_DISPOSITION"
        assert "CANONICAL_PROVIDER_JOB_WALLET_PAYMENT_OR_RENDER_GUARD" in mapped["source_dispositions"]
        assert "NO_RUNTIME_CLAIM" in mapped["source_dispositions"]

    for token in ("vproduct|open|other", "vproduct|future_unreviewed_action"):
        mapped = audit._map_callback(token, "callback_data", evidence, routes)
        assert mapped["target"] == "VPRODUCT_SOURCE_REVIEW_REQUIRED"
        assert mapped["status"] == "NEEDS_FEATURE_DISPOSITION"
        assert "NO_RUNTIME_CLAIM" in mapped["source_dispositions"]

    expected_templates = {
        "vproduct|camera|{*}": "BOT_VPRODUCT_GUIDED_STATE_NOT_REPLAYED",
        "vproduct|input_text|{*}": "BOT_VPRODUCT_GUIDED_STATE_NOT_REPLAYED",
        "vproduct|prompt_video|{*}": "BOT_VPRODUCT_PROMPT_OR_DELIVERY_STATE_NOT_REPLAYED",
        "vproduct|prompt_image_package|{*}": "VPRODUCT_RUNTIME_PACKAGE_PROVIDER_OR_PAYMENT_CONTRACT_REQUIRED",
        "vproduct|open|{*}": "VPRODUCT_SOURCE_REVIEW_REQUIRED",
        "vproduct|{*}|{*}": "VPRODUCT_SOURCE_REVIEW_REQUIRED",
    }
    for template, target in expected_templates.items():
        mapped = audit._map_callback_template(template, evidence, routes)
        assert mapped is not None
        assert mapped["target"] == target
        assert mapped["status"] == "NEEDS_FEATURE_DISPOSITION"
        assert "NO_RUNTIME_CLAIM" in mapped["source_dispositions"]
