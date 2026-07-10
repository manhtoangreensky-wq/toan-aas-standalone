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
