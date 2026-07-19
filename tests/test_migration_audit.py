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
    ):
        assert (docs_dir / name).is_file()
    assert "Manual top-up is a Telegram Bot-only handoff" in (docs_dir / "payos-wallet-jobs.md").read_text(encoding="utf-8")
    assert "Manual top-up stays a Bot handoff" in (docs_dir / "PAYOS_WALLET_JOB_MAP.md").read_text(encoding="utf-8")
    readme = (docs_dir / "README.md").read_text(encoding="utf-8")
    assert "BOT_COMPANION_HANDOFF.md" in readme
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
    assert "Bot checkout audited: `unavailable` (`not_a_git_worktree`)" in (docs_dir / "README.md").read_text(encoding="utf-8")
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


def test_static_audit_resolves_mounted_router_prefixes_for_native_api_routes(tmp_path: Path) -> None:
    """A mounted APIRouter prefix is part of the deployed API path."""

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
    assert mapped["target"] == "/api/v1/document-operations/ocr-pdf"
    assert mapped["status"] == "MAPPED_TO_EXISTING_ROUTE"


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
        assert mapped["status"] == "COPIED_GUARDED"

    save = audit._map_callback("freehub|save", "callback_data", {"file": "bot.py", "line": 1}, routes)
    assert save["target"] == "/content/prompt-pack"
    assert save["status"] == "COPIED_GUARDED"


def test_static_audit_maps_reviewed_dynamic_callback_namespaces_without_resolving_ids() -> None:
    audit = _load_audit_module()
    routes = {"/{page_path:path}"}
    expected = {
        "memory|view|{*}": "/notes",
        "ticket|reply|{*}": "/support",
        "pipe|stage|review|{*}": "/workboard",
        "storyboard|mode_ai|{*}": "/video-studio/storyboard-composer",
        "videodub|type|{*}": "/dubbing",
        "vproduct|camera|{*}": "/video/product",
        "videoaddon|export|{*}": "/video/add-ons",
        "manual|history|{*}": "/wallet/topup",
        "shopai|confirm|{*}": "/wallet/topup",
        "license_music|{*}": "/media-workspace",
        "job|cancel|{*}": "/jobs",
        "archive|dept|{*}": "/admin",
    }
    for template, target in expected.items():
        mapped = audit._map_callback_template(template, {"file": "bot.py", "line": 1}, routes)
        assert mapped is not None
        assert mapped["source_kind"] == "callback_template"
        assert mapped["source"] == template
        assert mapped["target"] == target
        assert mapped["status"] == "COPIED_GUARDED"
        assert mapped["resolution"] == "reviewed_namespace_compatibility_route"

    admin = audit._map_callback_template("archive|dept|{*}", {"file": "bot.py", "line": 1}, routes)
    assert admin is not None
    assert admin["classification"] == "admin"

    for template in ("trend|video|{*}", "manual|approve_expected|{*}", "adconcept|admin_video_smoke|{*}"):
        bot_only = audit._map_callback_template(template, {"file": "bot.py", "line": 1}, routes)
        assert bot_only is not None
        assert bot_only["classification"] == "admin"
        assert bot_only["target"] == "TELEGRAM_ONLY"
        assert bot_only["status"] == "TELEGRAM_ONLY"

    # A variable prefix has no fixed namespace. The audit must not guess that
    # it is a save/action from any one Bot workflow.
    assert audit._map_callback_template("{*}|save", {"file": "bot.py", "line": 1}, routes) is None


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
    assert template["resolution"] == "menu_namespace_requires_explicit_feature_disposition"


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
