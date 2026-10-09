"""Tests for R5 Cross-Product Engine Wiring & False-Block Elimination runtime matrix contracts."""

from __future__ import annotations

import json
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
REPORT_DIR = REPO_ROOT / "reports" / "webapp_full_product_truth"
MATRIX_FILE = REPORT_DIR / "R5_FINAL_ROUTE_RUNTIME_MATRIX.json"
PROVENANCE_FILE = REPORT_DIR / "00_data_provenance.json"
DEFECTS_FILE = REPORT_DIR / "defects.json"


def test_r5_matrix_exists_and_reconciles_total_routes() -> None:
    assert MATRIX_FILE.exists(), "R5_FINAL_ROUTE_RUNTIME_MATRIX.json must exist"
    with open(MATRIX_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    summary = data["summary"]
    routes = data["routes"]

    assert summary["BATCH"] == "WEBAPP_R5_CROSS_PRODUCT_ENGINE_WIRING_AND_FALSE_BLOCK_ELIMINATION_MASTER_BATCH_R1"
    assert summary["TOTAL_SURFACES"] == 221
    assert len(routes) == 221
    assert summary["UNCLASSIFIED_ROUTE_COUNT"] == 0
    assert summary["UNKNOWN_RUNTIME_OWNER_COUNT"] == 0
    assert summary["UNKNOWN_DATA_OWNER_COUNT"] == 0
    assert summary["STALE_PROVENANCE_SHA_COUNT"] == 0


def test_r5_blocked_backend_missing_count_reduced() -> None:
    with open(MATRIX_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    summary = data["summary"]
    assert summary["R4_BLOCKED_CANONICAL_BACKEND_MISSING_COUNT"] == 18
    assert summary["R5_BLOCKED_CANONICAL_BACKEND_MISSING_COUNT"] == 13
    assert summary["R5_BLOCKED_CANONICAL_BACKEND_MISSING_COUNT"] < 18
    assert summary["R5_WEB_NATIVE_PROMOTED_COUNT"] == 4
    assert summary["R5_READ_ONLY_COMPANION_PROMOTED_COUNT"] == 1

    class_counts = summary["CLASSIFICATION_COUNTS"]
    assert class_counts["BLOCKED_CANONICAL_BACKEND_MISSING"] == 13
    assert class_counts["RELEASED_WEB_NATIVE_RUNTIME"] == 112
    assert class_counts["RELEASED_READ_ONLY_CANONICAL_COMPANION"] == 19
    assert class_counts["RELEASED_ACTIVE_CANONICAL_RUNTIME"] == 13
    assert class_counts["ADMIN_INTERNAL_ONLY"] == 48
    assert class_counts["NOT_A_PRODUCT_ACTION_INFORMATIONAL_ONLY"] == 15
    assert class_counts["BLOCKED_EXTERNAL_CAPABILITY_OR_GRANT_REQUIRED"] == 1


def test_r5_promoted_video_operational_and_companion_routes() -> None:
    with open(MATRIX_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    routes_by_path = {r["route"]: r for r in data["routes"]}

    # 4 promoted web-native operations
    poster = routes_by_path["/video/poster"]
    assert poster["final_classification"] == "RELEASED_WEB_NATIVE_RUNTIME"
    assert poster["actual_root_gap"] == "FALSE_BLOCK_WEB_NATIVE_RUNTIME_ALREADY_EXISTS"
    assert poster["local_web_native_engine_exists"] is True
    assert poster["web_api_implemented"] is True
    assert poster["runtime_execution_enabled"] is True

    frame_seq = routes_by_path["/video/frame-sequence"]
    assert frame_seq["final_classification"] == "RELEASED_WEB_NATIVE_RUNTIME"
    assert frame_seq["actual_root_gap"] == "FALSE_BLOCK_WEB_NATIVE_RUNTIME_ALREADY_EXISTS"
    assert frame_seq["local_web_native_engine_exists"] is True
    assert frame_seq["web_api_implemented"] is True
    assert frame_seq["runtime_execution_enabled"] is True

    finishing = routes_by_path["/video/finishing"]
    assert finishing["final_classification"] == "RELEASED_WEB_NATIVE_RUNTIME"
    assert finishing["actual_root_gap"] == "FALSE_BLOCK_WEB_NATIVE_RUNTIME_ALREADY_EXISTS"
    assert finishing["local_web_native_engine_exists"] is True
    assert finishing["web_api_implemented"] is True
    assert finishing["runtime_execution_enabled"] is True

    add_ons = routes_by_path["/video/add-ons"]
    assert add_ons["final_classification"] == "RELEASED_WEB_NATIVE_RUNTIME"
    assert add_ons["actual_root_gap"] == "FALSE_BLOCK_WEB_NATIVE_RUNTIME_ALREADY_EXISTS"
    assert add_ons["local_web_native_engine_exists"] is True
    assert add_ons["runtime_execution_enabled"] is True

    # 1 promoted companion export view
    export = routes_by_path["/video/export"]
    assert export["final_classification"] == "RELEASED_READ_ONLY_CANONICAL_COMPANION"
    assert export["actual_root_gap"] == "OUTPUT_DELIVERY_GAP"
    assert export["canonical_bot_engine_exists"] is True
    assert export["web_to_bot_bridge_mounted"] is True
    assert export["runtime_execution_enabled"] is True


def test_r5_exact_root_gaps_for_remaining_blocked_routes() -> None:
    with open(MATRIX_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    routes_by_path = {r["route"]: r for r in data["routes"]}

    # GENUINE_CANONICAL_ENGINE_MISSING
    for p in ("/music/sfx", "/image/upscale", "/image/transform", "/image/remove-background"):
        r = routes_by_path[p]
        assert r["final_classification"] == "BLOCKED_CANONICAL_BACKEND_MISSING"
        assert r["actual_root_gap"] == "GENUINE_CANONICAL_ENGINE_MISSING"

    # WORKER_CONSUMER_EXISTS_NOT_ACTIVATED
    for p in ("/video/trend", "/video/long", "/video/multiscene"):
        r = routes_by_path[p]
        assert r["final_classification"] == "BLOCKED_CANONICAL_BACKEND_MISSING"
        assert r["actual_root_gap"] == "WORKER_CONSUMER_EXISTS_NOT_ACTIVATED"

    # WEB_BRIDGE_NOT_MOUNTED
    for p in ("/video/quick", "/video/product", "/video/text-to-video", "/documents/translate"):
        r = routes_by_path[p]
        assert r["final_classification"] == "BLOCKED_CANONICAL_BACKEND_MISSING"
        assert r["actual_root_gap"] == "WEB_BRIDGE_NOT_MOUNTED"

    # BOT_ADAPTER_EXISTS_NOT_EXPOSED_TO_WEB
    for p in ("/video/image-to-video", "/video/mux"):
        r = routes_by_path[p]
        assert r["final_classification"] == "BLOCKED_CANONICAL_BACKEND_MISSING"
        assert r["actual_root_gap"] == "BOT_ADAPTER_EXISTS_NOT_EXPOSED_TO_WEB"


def test_r5_provenance_and_defects_zero_placeholder() -> None:
    with open(PROVENANCE_FILE, "r", encoding="utf-8") as f:
        prov = json.load(f)

    s = prov["summary"]
    assert s["SOURCE_RUNTIME_MATCH"] == "YES"
    assert s["PLACEHOLDER_SURFACES"] == 0
    assert s["BROKEN_SURFACES"] == 0
    assert s["UNKNOWN_DATA_SURFACES"] == 0
    assert s["DEMO_DATA_SURFACES"] == 0

    with open(DEFECTS_FILE, "r", encoding="utf-8") as f:
        defects = json.load(f)

    defect_ids = {d["DEFECT_ID"]: d for d in defects}
    assert "DEFECT-R5-001" in defect_ids
    assert defect_ids["DEFECT-R5-001"]["STATUS"] == "REPAIRED_IN_R5"
