from __future__ import annotations

import importlib.util
import json
import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "tester_case_sync.py"
SOURCE = ROOT / "KIEM-THU" / "DANH-SACH-CASE.md"
GUIDE = ROOT / "KIEM-THU" / "HUONG-DAN-TESTER.md"
CASE_FORM = ROOT / ".github" / "ISSUE_TEMPLATE" / "01-case-test.yml"
BUG_FORM = ROOT / ".github" / "ISSUE_TEMPLATE" / "02-bao-loi.yml"
READINESS = ROOT / "reports" / "migration" / "p0-05d-tester-workspace.json"


def load_sync():
    spec = importlib.util.spec_from_file_location("p0_05d_tester_case_sync", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


sync = load_sync()


def portable_text_bytes(path: Path) -> bytes:
    return path.read_bytes().replace(b"\r\n", b"\n")


def small_table(rows: list[str]) -> str:
    return "\n".join(
        [
            "# Test",
            "| ID | SPEC_ID | Mức | Môi trường | Route / role / viewport | Case | PASS bắt buộc | Canh lỗi cũ | Evidence |",
            "|---|---|---|---|---|---|---|---|---|",
            *rows,
            "",
        ]
    )


def valid_row(case_id: str = "WA-01") -> str:
    return f"| {case_id} | SPEC-1 | 🟢 nhẹ | local-temp-only | /route · role · API | Case | PASS marker | Regression | evidence/path |"


def test_source_has_exact_sequential_39_cases():
    cases = sync.parse_cases(SOURCE)
    assert [row["ID"] for row in cases] == [f"WA-{number:02d}" for number in range(1, 40)]


def test_original_case_semantics_and_risk_are_preserved():
    cases = {row["ID"]: row for row in sync.parse_cases(SOURCE)}
    assert cases["WA-01"]["SPEC_ID"] == "MOTION-TOANAAS-BATCH-001"
    assert cases["WA-08"]["Mức"] == "🔴 chặn-bán-hàng"
    assert cases["WA-09"]["SPEC_ID"] == "PAYOS-CHECKOUT-RESTORE-001"
    assert cases["WA-13"]["Mức"] == "🟠 nặng"
    assert cases["WA-16"]["SPEC_ID"] == "ADMIN-ERP-PROFESSIONAL-VI-003"


def test_all_p0_cases_have_real_specs_environments_and_evidence():
    cases = {row["ID"]: row for row in sync.parse_cases(SOURCE)}
    expected_env = {
        **{f"WA-{number:02d}": "local-temp-only" for number in range(17, 27)},
        "WA-27": "local-render",
        "WA-28": "local-render",
        "WA-29": "security-gated",
        "WA-30": "ship-gated",
        "WA-31": "live-money-gated",
        "WA-32": "local-temp-only",
        "WA-33": "local-render",
        "WA-34": "local-temp-only",
    }
    for case_id, environment in expected_env.items():
        row = cases[case_id]
        assert row["SPEC_ID"].startswith("P0-05")
        assert row["Môi trường"] == environment
        assert row["PASS bắt buộc"]
        assert row["Evidence"]


def test_critical_p0_cases_have_red_severity_and_regression_warning():
    cases = {row["ID"]: row for row in sync.parse_cases(SOURCE)}
    critical = [f"WA-{number:02d}" for number in range(17, 27)] + ["WA-29", "WA-31", "WA-32", "WA-33", "WA-34"]
    for case_id in critical:
        assert cases[case_id]["Mức"] == "🔴 chặn-bán-hàng"
        assert cases[case_id]["Canh lỗi cũ"]


def test_customer_and_admin_p0_routes_are_not_conflated():
    cases = {row["ID"]: row for row in sync.parse_cases(SOURCE)}
    assert "/api/v1/payments/manual" in cases["WA-17"]["Route / role / viewport"]
    assert "signed owner" in cases["WA-17"]["Route / role / viewport"]
    assert "/api/v1/admin/payments/manual" in cases["WA-19"]["Route / role / viewport"]
    assert "canonical Admin" in cases["WA-19"]["Route / role / viewport"]


def test_p0_05e_corrective_cases_keep_metadata_render_and_privacy_separate():
    cases = {row["ID"]: row for row in sync.parse_cases(SOURCE)}
    assert "payment_code" in cases["WA-32"]["PASS bắt buộc"]
    assert "hydration/remount" in cases["WA-33"]["PASS bắt buộc"]
    assert "admin_note" in cases["WA-34"]["PASS bắt buộc"]
    assert {cases[case_id]["Môi trường"] for case_id in ("WA-32", "WA-34")} == {"local-temp-only"}
    assert cases["WA-33"]["Môi trường"] == "local-render"


def test_motion_live_reopen_cases_keep_normal_and_reduced_motion_separate():
    cases = {row["ID"]: row for row in sync.parse_cases(SOURCE)}
    assert {cases[case_id]["Môi trường"] for case_id in ("WA-35", "WA-36")} == {"local-render"}
    assert {cases[case_id]["SPEC_ID"] for case_id in ("WA-35", "WA-36")} == {"MOTION-WEBAPP-SURFACES-001"}
    assert "680ms" in cases["WA-35"]["PASS bắt buộc"]
    assert "Animation name `none`" in cases["WA-36"]["PASS bắt buộc"]


def test_manual_visible_qr_cases_keep_render_and_atomic_security_separate():
    cases = {row["ID"]: row for row in sync.parse_cases(SOURCE)}
    assert {cases[case_id]["SPEC_ID"] for case_id in ("WA-37", "WA-38")} == {
        "CUST-WEB-MANUAL-TOPUP-VISIBLE-QR-001"
    }
    assert cases["WA-37"]["Môi trường"] == "local-render"
    assert cases["WA-38"]["Môi trường"] == "local-temp-only"
    assert {cases[case_id]["Mức"] for case_id in ("WA-37", "WA-38")} == {"🔴 chặn-bán-hàng"}
    assert cases["WA-37"]["Case"] == "5 QR + form Web độc lập"
    assert "signed private endpoint" in cases["WA-37"]["PASS bắt buộc"]
    assert "Same-key concurrent create" in cases["WA-38"]["PASS bắt buộc"]
    assert "malformed/bomb QR 404" in cases["WA-38"]["PASS bắt buộc"]


def test_admin_login_responsive_case_preserves_route_and_live_boundaries():
    case = {row["ID"]: row for row in sync.parse_cases(SOURCE)}["WA-39"]
    assert case["SPEC_ID"] == "ADMIN-LOGIN-RESPONSIVE-001"
    assert case["Mức"] == "🟠 nặng"
    assert case["Môi trường"] == "local-render + live-after-deploy"
    assert "/admin/login" in case["Route / role / viewport"]
    assert "1920/1440/1024/841/840/821/805/804/769/768/390/360" in case["Route / role / viewport"]
    assert "overflow/outside/console `0`" in case["PASS bắt buộc"]
    assert "`/login` và `/register` không đổi" in case["PASS bắt buộc"]
    assert "R1 selector ancestor đảo" in case["Canh lỗi cũ"]
    assert "live-after-deploy" in case["Môi trường"]


def test_parser_supports_escaped_pipe(tmp_path: Path):
    path = tmp_path / "cases.md"
    path.write_text(small_table([valid_row().replace("PASS marker", "approved \\| rejected")]), encoding="utf-8")
    rows = sync.parse_cases(path)
    assert rows[0]["PASS bắt buộc"] == "approved | rejected"


@pytest.mark.parametrize("field_index", [1, 3, 4, 5, 6, 8])
def test_parser_rejects_each_empty_required_field(tmp_path: Path, field_index: int):
    cells = sync.split_markdown_row(valid_row())
    cells[field_index] = ""
    path = tmp_path / "cases.md"
    path.write_text(small_table(["| " + " | ".join(cells) + " |"]), encoding="utf-8")
    with pytest.raises(ValueError, match="thiếu trường bắt buộc"):
        sync.parse_cases(path)


def test_parser_rejects_duplicate_and_gap(tmp_path: Path):
    duplicate = tmp_path / "duplicate.md"
    duplicate.write_text(small_table([valid_row("WA-01"), valid_row("WA-01")]), encoding="utf-8")
    with pytest.raises(ValueError, match="trùng"):
        sync.parse_cases(duplicate)
    gap = tmp_path / "gap.md"
    gap.write_text(small_table([valid_row("WA-01"), valid_row("WA-03")]), encoding="utf-8")
    with pytest.raises(ValueError, match="tuần tự"):
        sync.parse_cases(gap)


def test_parser_rejects_invalid_severity(tmp_path: Path):
    path = tmp_path / "cases.md"
    path.write_text(small_table([valid_row().replace("🟢 nhẹ", "invalid")]), encoding="utf-8")
    with pytest.raises(ValueError, match="Mức không hợp lệ"):
        sync.parse_cases(path)


def test_dry_run_preview_is_three_items_and_never_calls_runner(capsys):
    calls: list[list[str]] = []

    def forbidden_runner(command, **kwargs):
        calls.append(command)
        raise AssertionError("dry-run must not invoke subprocess")

    assert sync.run(["--source", str(SOURCE), "--so=3", "--json"], runner=forbidden_runner) == 0
    preview = json.loads(capsys.readouterr().out)
    assert len(preview) == 3
    assert all(item["dry_run"] is True for item in preview)
    assert calls == []


def test_default_source_command_runs_from_repo_root(capsys, monkeypatch):
    monkeypatch.chdir(ROOT)
    assert sync.run(["--so=3", "--json"]) == 0
    assert len(json.loads(capsys.readouterr().out)) == 3


def test_preview_create_command_is_complete_and_labels_are_deterministic():
    case = sync.parse_cases(SOURCE)[16]
    command = sync.issue_command(case, sync.DEFAULT_REPO, None)
    assert command[:3] == ["gh", "issue", "create"]
    assert command[command.index("--body-file") + 1] == "<BODY_FILE>"
    assert sync.labels_for(case) == ["case-test", "chờ-test", "🔴 chặn-bán-hàng"]
    assert sync.labels_for(case) == sync.labels_for(case)


def test_edit_command_uses_real_numeric_issue_number():
    case = sync.parse_cases(SOURCE)[4]
    command = sync.issue_command(case, sync.DEFAULT_REPO, 412)
    assert command[:4] == ["gh", "issue", "edit", "412"]
    assert "WA-05" not in command[:4]
    assert "--add-label" in command


def test_issue_body_uses_canonical_source_and_regression_warning():
    case = sync.parse_cases(SOURCE)[16]
    body = sync.issue_body(case, sync.DEFAULT_REPO)
    assert "sửa case thì sửa ở file đó trước" in body
    assert "https://github.com/manhtoangreensky-wq/toan-aas-standalone/blob/main/KIEM-THU/DANH-SACH-CASE.md" in body
    assert "FAIL là regression" in body


def test_cli_rejects_invalid_ranges_and_edit_without_single_selection():
    with pytest.raises(SystemExit):
        sync.run(["--so=0"])
    with pytest.raises(SystemExit):
        sync.run(["--bo=-1"])
    with pytest.raises(SystemExit):
        sync.run(["--sua=412"])
    with pytest.raises(SystemExit):
        sync.run(["--sua=412", "--so=2"])


def test_owner_authorized_write_uses_private_temp_file_and_cleans_it():
    observed: dict[str, object] = {}

    def runner(command, check):
        body_path = Path(command[command.index("--body-file") + 1])
        observed["path"] = body_path
        observed["mode"] = stat.S_IMODE(body_path.stat().st_mode)
        observed["body"] = body_path.read_text(encoding="utf-8")
        observed["check"] = check
        return subprocess.CompletedProcess(command, 0)

    assert sync.run(["--source", str(SOURCE), "--so=1", "--that"], runner=runner) == 0
    assert observed["mode"] == 0o600
    assert observed["check"] is True
    assert "sửa case thì sửa ở file đó trước" in str(observed["body"])
    assert not Path(observed["path"]).exists()


def test_owner_authorized_write_failure_propagates_and_cleans_temp(capsys):
    observed: dict[str, Path] = {}

    def runner(command, check):
        observed["path"] = Path(command[command.index("--body-file") + 1])
        raise subprocess.CalledProcessError(7, command)

    assert sync.run(["--source", str(SOURCE), "--so=1", "--that", "--json"], runner=runner) == 7
    assert not observed["path"].exists()
    result = json.loads(capsys.readouterr().out)
    assert result[0]["status"] == "failed"


def test_edit_write_requires_one_selected_case_and_uses_issue_number():
    commands: list[list[str]] = []

    def runner(command, check):
        commands.append(command)
        return subprocess.CompletedProcess(command, 0)

    assert sync.run(["--source", str(SOURCE), "--bo=4", "--so=1", "--sua=412", "--that"], runner=runner) == 0
    assert len(commands) == 1
    assert commands[0][:4] == ["gh", "issue", "edit", "412"]
    assert "WA-05" in commands[0][commands[0].index("--title") + 1]


def test_issue_forms_use_exact_labels_fields_and_safe_redaction():
    case_form = CASE_FORM.read_text(encoding="utf-8")
    bug_form = BUG_FORM.read_text(encoding="utf-8")
    combined = case_form + bug_form
    assert "labels: [case-test, chờ-test]" in case_form
    assert "labels: [lỗi, có-lỗi, chờ-sửa]" in bug_form
    for severity in sync.SEVERITIES:
        assert severity in combined
    for marker in ["SPEC_ID", "BASE / HEAD / runtime SHA", "Môi trường", "Route", "Role", "Viewport", "Bằng chứng", "Redaction confirmation"]:
        assert marker in combined
    assert "Không dán token, mật khẩu, backup code, Admin ID, email đầy đủ, số điện thoại hoặc raw customer record" in combined
    for line in combined.splitlines():
        if "placeholder:" in line.casefold():
            assert all(term.casefold() not in line.casefold() for term in ["token", "password", "mật khẩu", "backup code", "Admin ID"])


def test_guide_is_substantive_safe_and_separates_dry_run_from_write():
    guide = GUIDE.read_text(encoding="utf-8")
    assert len(guide.splitlines()) >= 45
    for marker in ["WA-01..WA-39", "BASE", "HEAD", "runtime SHA", "local", "CI", "deployed", "live", "CSRF", "idempotency", "redaction", "PROVIDER_CALLS=0", "WALLET_MUTATIONS=0", "LIVE_MONEY_FLOW=NOT_TESTED", "#412", "--so=3", "--that", "TOAN AAS Web App · Tester P0"]:
        assert marker in guide
    assert "python scripts/tester_case_sync.py --so=3 --json" in guide
    assert "--so=3 --that" not in guide
    for marker in ["Cấm quét QR", "Không gửi token", "Không gửi mật khẩu", "Không dán backup code"]:
        assert marker.casefold() in guide.casefold()


def test_portable_text_bytes_normalizes_crlf_without_changing_content(tmp_path: Path):
    lf = tmp_path / "lf.txt"
    crlf = tmp_path / "crlf.txt"
    lf.write_bytes("dòng một\ndòng hai\n".encode("utf-8"))
    crlf.write_bytes("dòng một\r\ndòng hai\r\n".encode("utf-8"))
    assert portable_text_bytes(lf) == portable_text_bytes(crlf) == lf.read_bytes()


def test_readiness_json_has_explicit_truth_and_file_metadata():
    data = json.loads(READINESS.read_text(encoding="utf-8"))
    assert data["schema_version"] == "p0-05d.v2"
    assert data["metadata_encoding"] == "utf-8-lf-portable"
    assert data["repo"] == sync.DEFAULT_REPO
    assert data["tracker_issue"] == 412
    assert data["case_count"] == 39
    assert data["p0_case_count"] == 18
    assert data["github_project"] == "TOAN AAS Web App · Tester P0"
    assert data["push_gate"] == "ADMIN_LOGIN_RESPONSIVE_001_READY_TO_PUSH"
    assert data["labels_missing"] == []
    assert data["external_mutations"] == 0
    assert all(value == 0 for value in data["safety"].values())
    paths = [row["path"] for row in data["local_files"]]
    assert paths == sorted(paths)
    for row in data["local_files"]:
        raw = portable_text_bytes(ROOT / row["path"])
        assert row["lines"] == len(raw.splitlines())
        assert row["bytes"] == len(raw)
        assert row["sha256"] == __import__("hashlib").sha256(raw).hexdigest()
