#!/usr/bin/env python3
"""Preview or Owner-authorized synchronization of Tester cases to GitHub Issues."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Callable, Sequence


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "KIEM-THU" / "DANH-SACH-CASE.md"
DEFAULT_REPO = "manhtoangreensky-wq/toan-aas-standalone"
CANONICAL_SOURCE_URL = "https://github.com/{repo}/blob/main/KIEM-THU/DANH-SACH-CASE.md"
HEADERS = ["ID", "SPEC_ID", "Mức", "Môi trường", "Route / role / viewport", "Case", "PASS bắt buộc", "Canh lỗi cũ", "Evidence"]
SEVERITIES = ["🔴 chặn-bán-hàng", "🟠 nặng", "🟡 vừa", "🟢 nhẹ"]


def positive(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("phải là số nguyên dương")
    return parsed


def non_negative(value: str) -> int:
    parsed = int(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("không được âm")
    return parsed


def split_markdown_row(line: str) -> list[str]:
    stripped = line.strip()
    if not (stripped.startswith("|") and stripped.endswith("|")):
        raise ValueError("Dòng bảng phải bắt đầu và kết thúc bằng dấu |")
    cells: list[str] = []
    current: list[str] = []
    escaped = False
    for char in stripped[1:-1]:
        if escaped:
            current.append(char)
            escaped = False
        elif char == "\\":
            escaped = True
        elif char == "|":
            cells.append("".join(current).strip())
            current = []
        else:
            current.append(char)
    if escaped:
        current.append("\\")
    cells.append("".join(current).strip())
    return cells


def parse_cases(source: Path) -> list[dict[str, str]]:
    text = source.read_text(encoding="utf-8")
    lines = text.splitlines()
    header_index = next((index for index, line in enumerate(lines) if line.startswith("|") and split_markdown_row(line) == HEADERS), -1)
    if header_index < 0:
        raise ValueError("Không tìm thấy header bảng case chính xác")
    if header_index + 1 >= len(lines) or not re.fullmatch(r"\|(?:\s*:?-{3,}:?\s*\|){9}", lines[header_index + 1]):
        raise ValueError("Thiếu separator row hợp lệ")

    cases: list[dict[str, str]] = []
    for line in lines[header_index + 2 :]:
        if not line.startswith("|"):
            if cases:
                break
            continue
        cells = split_markdown_row(line)
        if len(cells) != len(HEADERS):
            raise ValueError(f"Case row phải có 9 cột: {line}")
        row = dict(zip(HEADERS, cells))
        if not re.fullmatch(r"WA-\d{2}", row["ID"]):
            raise ValueError(f"ID không hợp lệ: {row['ID']}")
        if row["Mức"] not in SEVERITIES:
            raise ValueError(f"Mức không hợp lệ: {row['Mức']}")
        for field in ["SPEC_ID", "Môi trường", "Route / role / viewport", "Case", "PASS bắt buộc", "Evidence"]:
            if not row[field]:
                raise ValueError(f"{row['ID']} thiếu trường bắt buộc: {field}")
        cases.append(row)

    if not cases:
        raise ValueError("Bảng case không có dữ liệu")
    numbers = [int(row["ID"].split("-")[1]) for row in cases]
    if len(numbers) != len(set(numbers)):
        raise ValueError("Case ID bị trùng")
    if numbers != list(range(1, len(numbers) + 1)):
        raise ValueError("Case ID phải tuần tự từ WA-01, không được thiếu hoặc đảo thứ tự")
    return cases


def canonical_source_url(repo: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
        raise ValueError("Repo phải có dạng owner/repository")
    return CANONICAL_SOURCE_URL.format(repo=repo)


def issue_body(case: dict[str, str], repo: str) -> str:
    parts = [
        "sửa case thì sửa ở file đó trước",
        "",
        f"Nguồn canonical: {canonical_source_url(repo)}",
        "",
        f"- **Case:** {case['ID']}",
        f"- **SPEC_ID:** {case['SPEC_ID']}",
        f"- **Mức:** {case['Mức']}",
        f"- **Môi trường:** {case['Môi trường']}",
        f"- **Route / role / viewport:** {case['Route / role / viewport']}",
        f"- **Case:** {case['Case']}",
        f"- **PASS bắt buộc:** {case['PASS bắt buộc']}",
        f"- **Evidence:** {case['Evidence']}",
    ]
    if case["Canh lỗi cũ"]:
        parts.extend(["", "🚨 **Canh lỗi cũ — FAIL là regression, báo gấp:**", case["Canh lỗi cũ"]])
    return "\n".join(parts) + "\n"


def labels_for(case: dict[str, str]) -> list[str]:
    return ["case-test", "chờ-test", case["Mức"]]


def issue_command(case: dict[str, str], repo: str, issue_number: int | None, body_file: str = "<BODY_FILE>") -> list[str]:
    title = f"[TEST] {case['ID']} — {case['Case']}"
    labels = ",".join(labels_for(case))
    if issue_number is None:
        return ["gh", "issue", "create", "--repo", repo, "--title", title, "--body-file", body_file, "--label", labels]
    return ["gh", "issue", "edit", str(issue_number), "--repo", repo, "--title", title, "--body-file", body_file, "--add-label", labels]


def select_cases(cases: list[dict[str, str]], skip: int, limit: int | None) -> list[dict[str, str]]:
    selected = cases[skip:]
    if limit is not None:
        selected = selected[:limit]
    return selected


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Dry-run mặc định; chỉ --that mới ghi GitHub.")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--repo", default=DEFAULT_REPO)
    parser.add_argument("--so", type=positive)
    parser.add_argument("--bo", type=non_negative, default=0)
    parser.add_argument("--sua", type=positive, help="Số issue GitHub thật; bắt buộc dùng cùng --so=1.")
    parser.add_argument("--that", action="store_true", help="Cho phép external GitHub write sau Owner gate.")
    parser.add_argument("--json", action="store_true")
    return parser


def run(argv: Sequence[str] | None = None, runner: Callable[..., subprocess.CompletedProcess] = subprocess.run) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.sua is not None and args.so != 1:
        parser.error("--sua yêu cầu --so=1 để chọn đúng một case")

    cases = parse_cases(args.source)
    selected = select_cases(cases, args.bo, args.so)
    if not selected:
        parser.error("Không có case nào trong phạm vi --bo/--so")
    if args.sua is not None and len(selected) != 1:
        parser.error("--sua chỉ được dùng với đúng một case")

    previews: list[dict[str, object]] = []
    for case in selected:
        body = issue_body(case, args.repo)
        preview_command = issue_command(case, args.repo, args.sua)
        preview: dict[str, object] = {
            "dry_run": not args.that,
            "id": case["ID"],
            "title": f"[TEST] {case['ID']} — {case['Case']}",
            "body": body,
            "labels": labels_for(case),
            "command": preview_command,
        }
        if args.that:
            fd, temp_name = tempfile.mkstemp(prefix="toanaas-case-", suffix=".md", text=True)
            try:
                os.chmod(temp_name, 0o600)
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    handle.write(body)
                actual_command = issue_command(case, args.repo, args.sua, temp_name)
                runner(actual_command, check=True)
                preview["status"] = "written"
            except subprocess.CalledProcessError as exc:
                preview["status"] = "failed"
                if args.json:
                    print(json.dumps([*previews, preview], ensure_ascii=False, indent=2))
                if not exc.returncode:
                    return 1
                return int(exc.returncode)
            finally:
                Path(temp_name).unlink(missing_ok=True)
        previews.append(preview)

    if args.json:
        print(json.dumps(previews, ensure_ascii=False, indent=2))
    else:
        for preview in previews:
            print(f"{preview['id']} | {'DRY-RUN' if preview['dry_run'] else preview.get('status', 'UNKNOWN')}")
            print(" ".join(str(part) for part in preview["command"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
