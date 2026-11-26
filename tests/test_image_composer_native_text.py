"""Exercise actual Web text builders and models without ASGI or external calls."""
from __future__ import annotations

import ast
import importlib
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BASE = "6ec003dbf8f80739f5fb93ff7bd1d7cc703c6792"


def test_actual_composer_builders_keep_native_copy_english_and_customer_text(tmp_path, monkeypatch):
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "unused-composer-text.db"))
    monkeypatch.setenv("WEB_SESSION_SECRET", "public-unit-only-composer-text-secret")
    studio = importlib.import_module("copyfast_image_studio")

    def forbidden(*args, **kwargs):
        raise AssertionError("Text builder must not read/write a database or open a network connection")

    monkeypatch.setattr(studio, "transaction", forbidden)
    monkeypatch.setattr(studio, "read_transaction", forbidden)
    import socket
    monkeypatch.setattr(socket, "create_connection", forbidden)

    baseline = subprocess.check_output(
        ["git", "show", BASE + ":copyfast_image_studio.py"], cwd=ROOT, encoding="utf-8"
    )
    function_names = {
        "_prompt_composer_goal_label", "_prompt_composer_default_style",
        "_prompt_composer_style_preset", "_prompt_composer_resolved_style",
        "_prompt_composer_variants", "_compose_image_prompt",
    }
    constant_names = {
        "PROMPT_COMPOSER_STYLE_SUGGESTION_GOAL_CODES", "PROMPT_COMPOSER_STYLE_SUGGESTION_CATALOG",
    }
    nodes = [
        node for node in ast.parse(baseline).body
        if (isinstance(node, ast.FunctionDef) and node.name in function_names)
        or (isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id in constant_names for target in node.targets))
    ]
    assert len(nodes) == len(function_names) + len(constant_names)
    old = {
        "Any": Any,
        "ImagePromptComposerRequest": studio.ImagePromptComposerRequest,
        "ImagePromptComposerResult": studio.ImagePromptComposerResult,
    }
    exec(compile(ast.Module(body=nodes, type_ignores=[]), "<fixed-delivered-Web-recipes>", "exec"), old)
    subject = "Nội dung khách Facebook TikTok media studio & chi tiết riêng"
    custom_goal = "Mục tiêu khách Facebook TikTok media studio"
    custom_style = "Phong cách khách Facebook TikTok media studio"
    vi_goals = {"product": "Ảnh sản phẩm", "ad": "Ảnh quảng cáo", "cinematic": "Ảnh điện ảnh / hình ảnh chủ đạo"}
    forbidden_words = re.compile(
        r"\b(?:prompt|studio|media|cinematic|visual|premium|luxury|watermark|claim|reference|lifestyle|showroom|fantasy|cyberpunk|viral)\b",
        re.IGNORECASE,
    )
    rows = []
    for language in ("vi", "en"):
        cases = [
            (goal, preset) for goal in ("product", "ad", "cinematic")
            for preset in ("auto", "suggestion_1", "suggestion_2", "suggestion_3")
        ] + [("custom", "custom")]
        for goal, preset in cases:
            source = {
                "goal_code": goal, "custom_goal": custom_goal if goal == "custom" else "",
                "subject": subject, "style_preset": preset,
                "style": custom_style if preset == "custom" else "",
                "ratio": "9:16", "language": language,
            }
            request = studio.ImagePromptComposerRequest.model_validate(source)
            composer = studio._compose_image_prompt(request)
            assert composer["subject"] == subject
            assert composer["language"] == language
            assert composer["style_preset"] == preset
            assert composer["goal_code"] == goal
            assert len(composer["variants"]) == 3
            assert len(composer["review_before_use"]) == 4
            assert subject in composer["short_prompt"] and subject in composer["detailed_prompt"]
            assert all(subject in variant for variant in composer["variants"])
            if goal == "custom":
                assert composer["custom_goal"] == composer["goal_label"] == custom_goal
                assert composer["style"] == custom_style
            if language == "en":
                assert composer == old["_compose_image_prompt"](request), "Selected English output must remain exactly delivered"
            else:
                assert composer["title"] == "Mô tả ảnh: " + subject
                if goal != "custom":
                    assert composer["goal_label"] == vi_goals[goal]
                display = "\n".join(
                    [composer[key] for key in ("title", "goal_label", "style", "short_prompt", "detailed_prompt", "negative_prompt")]
                    + composer["variants"] + composer["review_before_use"]
                )
                for customer_value in (subject, custom_goal, custom_style):
                    display = display.replace(customer_value, "")
                assert not forbidden_words.search(display), display
            boundary = studio._prompt_composer_boundary()
            assert boundary["execution"] == "web_native_deterministic_prompt_only"
            assert all(value is False for key, value in boundary.items() if key != "execution")
            rows.append({"source": source, "result": {"composer": composer, **boundary}})
    assert len(rows) == 26
    fixture = ROOT / "tests/fixtures/image-composer-native-text-results.json"
    if fixture.exists():
        stored = json.loads(fixture.read_bytes())
        assert stored["base"] == BASE
        assert stored["rows"] == rows
        assert stored["source_lf_sha256"] == hashlib.sha256(
            (ROOT / "copyfast_image_studio.py").read_text(encoding="utf-8").replace("\r\n", "\n").encode("utf-8")
        ).hexdigest()
    output = os.environ.get("COMPOSER_TEXT_RESULTS_OUT")
    if output:
        Path(output).write_text(
            json.dumps({
                "schema": "composer-native-text-qa-v1", "base": BASE, "rows": rows,
                "source": "Actual Web builders and real Pydantic models; not HTTP/auth or persistence acceptance",
                "database_operations": 0, "external_network_calls": 0,
            }, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
