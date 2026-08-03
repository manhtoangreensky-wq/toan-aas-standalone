"""RED contracts for reviewed Job-Lock Recovery Safety Guide locale copy.

This route is a signed, read-only safety guide. Localizing its fixed Portal
copy must never introduce a job, finance, or runtime control plane.
"""

from __future__ import annotations

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]

LOCALE_KEYS = (
    "route.title", "route.description",
    "intro.kicker", "intro.title", "intro.body", "intro.statusTitle", "intro.statusBody",
    "checklist.kicker", "checklist.title", "checklist.body",
    "checkpoint.triage.title", "checkpoint.triage.body",
    "checkpoint.evidence.title", "checkpoint.evidence.body",
    "checkpoint.authority.title", "checkpoint.authority.body",
    "escalation.kicker", "escalation.title", "escalation.body",
    "escalation.itemScope.title", "escalation.itemScope.body",
    "escalation.itemCanonical.title", "escalation.itemCanonical.body",
    "escalation.itemEscalate.title", "escalation.itemEscalate.body",
    "limits.kicker", "limits.title", "limits.body",
    "boundary.noMutation.title", "boundary.noMutation.body",
    "boundary.noRuntime.title", "boundary.noRuntime.body",
    "boundary.noFinancial.title", "boundary.noFinancial.body",
    "link.jobs",
    "notes.integration.title", "notes.safety.title", "notes.scope.body", "notes.botBoundary.body",
)


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _function_source(source: str, name: str) -> str:
    match = re.search(rf"(?:async )?function {re.escape(name)}\(", source)
    assert match, f"Missing function {name}"
    following = re.search(r"\n  (?:async )?function [A-Za-z0-9_]+\(", source[match.end():])
    end = match.end() + following.start() if following else len(source)
    assert end > match.end(), f"Unable to bound function {name}"
    return source[match.start():end]


def _admin_generic_locale_block(source: str, locale: str) -> str:
    """Return one exact locale object from the static ADMIN_GENERIC catalogue."""

    start = source.index("  const ADMIN_GENERIC_MESSAGES = {")
    end = source.index("\n  };", start)
    catalog = source[start:end]
    match = re.search(
        rf"^    {re.escape(locale)}: \{{(?P<body>.*?)(?=^    (?:vi|en|zh): \{{|\Z)",
        catalog,
        flags=re.MULTILINE | re.DOTALL,
    )
    assert match, f"Missing {locale} ADMIN_GENERIC_MESSAGES catalogue"
    return match.group("body")


def _admin_generic_locale_keys(block: str) -> set[str]:
    return set(re.findall(r'"adminGeneric\.jobRecoveryGuide\.([^"]+)"\s*:', block))


def test_job_recovery_guide_fixed_copy_uses_reviewed_locale_catalogue_and_route_chrome() -> None:
    i18n = _read("static/portal/portal-i18n.js")
    portal = _read("static/portal/portal.js")
    pages = _read("copyfast_pages.py")
    renderer = _function_source(portal, "renderAdminJobRecoveryGuide")
    page_titles = _function_source(portal, "localizedPageTitle")
    page_descriptions = _function_source(portal, "localizedPageDescription")

    expected_keys = set(LOCALE_KEYS)
    assert len(expected_keys) == 39
    for locale in ("vi", "en", "zh"):
        locale_block = _admin_generic_locale_block(i18n, locale)
        assert _admin_generic_locale_keys(locale_block) == expected_keys
        for key in LOCALE_KEYS:
            value = re.search(
                rf'"adminGeneric\.jobRecoveryGuide\.{re.escape(key)}"\s*:\s*"(?P<value>(?:\\.|[^"\\])*)"',
                locale_block,
            )
            assert value and value.group("value").strip(), f"Missing reviewed {locale} copy for {key}"

    assert "function adminJobRecoveryGuideText(key, fallback, params)" in portal
    assert 'return adminGenericText("jobRecoveryGuide." + key, fallback, params);' in portal
    assert "const text = (key, fallback, params) => adminJobRecoveryGuideText(key, fallback, params);" in renderer
    assert '"Job-Lock Recovery Safety Guide": "adminGeneric.jobRecoveryGuide.route.title"' in portal
    assert 'if (path === "/admin/job-recovery-guide") return adminJobRecoveryGuideText("route.title", fallback);' in page_titles
    assert 'if (path === "/admin/job-recovery-guide") return adminJobRecoveryGuideText("route.description", fallback);' in page_descriptions
    first_paint = re.search(r'"/admin/job-recovery-guide": \{(?P<titles>.*?)\},', pages, flags=re.DOTALL)
    assert first_paint, "Missing Job Recovery first-paint title mapping"
    for locale, title in (
        ("vi", "Hướng dẫn xử lý Job-Lock · TOAN AAS"),
        ("en", "Job-Lock Recovery Guide · TOAN AAS"),
        ("zh", "任务锁恢复指南 · TOAN AAS"),
    ):
        assert f'"{locale}": "{title}"' in first_paint.group("titles")


def test_job_recovery_guide_locale_renderer_preserves_read_only_boundary_and_vietnamese_fallbacks() -> None:
    portal = _read("static/portal/portal.js")
    renderer = _function_source(portal, "renderAdminJobRecoveryGuide")

    for required in (
        'serverAuthorizesAdminRoute(context, "/admin/jobs")',
        "renderHero(page, context)",
        'badge("read_only")',
        "renderNotes({ ...page, notes: localizedNotes }, noteLabels)",
    ):
        assert required in renderer
    assert renderer.count('${badge("read_only")}') >= 3
    for key in set(LOCALE_KEYS) - {"route.title", "route.description"}:
        assert f'text("{key}",' in renderer

    for forbidden in (
        "fetch(",
        "api(",
        "readAdminPath(",
        "data-portal-action",
        "<form",
        "<button",
        "payloadFor(",
        "FormData",
        "Idempotency-Key",
        "/admin/modules/",
        "adminData",
        "localStorage",
        "sessionStorage",
        "setInterval",
        "data-admin-job-id",
        "jobId",
        "/clear_job_lock",
    ):
        assert forbidden.lower() not in renderer.lower()
    assert not re.search(r'''["']?method["']?\s*:\s*["']post["']''', renderer, flags=re.IGNORECASE)

    assert (
        'adminPage("/admin/job-recovery-guide", "Job-Lock Recovery Safety Guide", '
        '"Hướng dẫn triage job-lock dành cho canonical admin; không đọc queue/job, không clear/retry/refund và không điều khiển runtime từ browser."'
    ) in portal
    for fallback in (
        'text("intro.body", "Trang này giúp đội vận hành phân biệt bước triage, ghi nhận và escalation. Mọi kiểm tra trạng thái thực, quyết định can thiệp và financial side effect vẫn nằm trong canonical procedure đã được phê duyệt.")',
        'text("checklist.body", "Không cần nhập dữ liệu tại đây. Checklist không tạo ticket, không đọc job và không kích hoạt bất kỳ workflow nào.")',
        'text("escalation.body", "Tách triage khỏi quyền mutation để tránh thao tác nhầm trên queue, delivery hoặc billing.")',
        'text("limits.body", "Guidance không phải là queue console, job adapter, runbook executor hay một đường tắt tới financial mutation.")',
        'text("boundary.noMutation.title", "Không clear, retry hoặc refund")',
        'text("boundary.noMutation.body", "Không có chọn job, xác nhận, bulk operation hay đổi trạng thái; Web không hứa hẹn khôi phục hoặc delivery.")',
        'text("boundary.noRuntime.title", "Không điều khiển runtime")',
        'text("boundary.noRuntime.body", "Không đọc hoặc thao tác worker, provider, queue, lock, healthcheck, restart hay lịch chạy tự động.")',
        'text("boundary.noFinancial.title", "Không có financial side effect")',
        'text("boundary.noFinancial.body", "Không thay đổi Xu, charge, refund, payment, PayOS, ledger, entitlement hoặc billing event.")',
        'text("notes.scope.body", "Đây là hướng dẫn an toàn, không phải màn hình xử lý job. Mọi quyết định và thao tác canonical chỉ được thực hiện trong quy trình được phê duyệt.")',
        'text("notes.botBoundary.body", "Trang không nhận định danh người dùng hay job, không đọc queue/worker/provider và không nhận trạng thái, Xu, payment hay refund từ Bot/Core Bridge.")',
        'text("notes.integration.title", "Trạng thái tích hợp")',
        'text("notes.safety.title", "Nguyên tắc an toàn")',
    ):
        assert fallback in renderer

    assert 'const jobsLink = serverAuthorizesAdminRoute(context, "/admin/jobs")' in renderer
    assert 'href="/admin/jobs">${safeText(text("link.jobs", "Mở Jobs canonical"))}</a>' in renderer
    assert "const localizedNotes = [" in renderer
    assert "const noteLabels = {" in renderer
