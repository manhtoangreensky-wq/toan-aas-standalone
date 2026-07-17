"""Focused contract tests for the aggregate-only Bot-to-Web Capability Hub."""

from __future__ import annotations

import json

from copyfast_capability_hub import build_capability_hub


def test_capability_hub_keeps_only_customer_aggregate_metadata() -> None:
    hub = build_capability_hub(
        {
            "audit_mode": "static-only",
            "source_counts": {"commands": 6, "callback_handlers": 2, "callback_data": 4},
            "mapping_status_counts": {
                "MAPPED_TO_EXISTING_ROUTE": 1,
                "COPIED_GUARDED": 3,
                "TELEGRAM_ONLY": 2,
            },
            "command_mappings": [
                {
                    "source": "/video_product",
                    "target": "/features/video",
                    "classification": "customer",
                    "status": "COPIED_GUARDED",
                    "handler": "never_returned",
                    "evidence": {"file": "bot.py", "line": 99},
                },
                {
                    "source": "/pdf_split",
                    "target": "/documents/split",
                    "classification": "customer",
                    "status": "MAPPED_TO_EXISTING_ROUTE",
                },
                {
                    "source": "/bot_only_feature",
                    "target": "TELEGRAM_ONLY",
                    "classification": "customer",
                    "status": "TELEGRAM_ONLY",
                },
                {
                    "source": "/provider_secret_status",
                    "target": "/admin/provider_secret_status",
                    "classification": "admin",
                    "status": "COPIED_GUARDED",
                    "handler": "admin_secret_handler",
                    "evidence": {"file": "bot.py", "line": 100},
                },
                {
                    "source": "/unsafe",
                    "target": "https://outside.example/route",
                    "classification": "customer",
                    "status": "MAPPED_TO_EXISTING_ROUTE",
                },
            ],
        }
    )

    assert hub["available"] is True
    assert hub["audit"] == {
        "commands": 6,
        "callback_handlers": 2,
        "callback_data": 4,
        "mapped": 1,
        "guarded": 3,
        "telegram_only": 2,
    }
    by_key = {item["key"]: item for item in hub["families"]}
    assert by_key["video"]["customer_command_count"] == 1
    assert by_key["video"]["guarded_route_count"] == 1
    assert by_key["documents"]["mapped_route_count"] == 1
    assert by_key["workspace"]["telegram_only_count"] == 1
    # The raw sources, handlers, evidence and unsafe external target never
    # leave the aggregate contract.
    serialized = json.dumps(hub, ensure_ascii=False)
    assert "video_product" not in serialized
    assert "never_returned" not in serialized
    assert "provider_secret_status" not in serialized
    assert "outside.example" not in serialized


def test_capability_hub_fails_closed_for_incomplete_audit_data() -> None:
    hub = build_capability_hub({"audit_mode": "runtime", "source_counts": {}, "mapping_status_counts": {}})

    assert hub["available"] is False
    assert hub["audit"]["commands"] == 0
    assert len(hub["families"]) == 10
