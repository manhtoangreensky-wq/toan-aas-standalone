"""RED contracts for Delivery & Runtime Admin ERP locale projection.

The canonical server remains the only authority for routes, availability and
state.  This contract permits a closed presentation translation only after
that server-issued projection has been admitted by the Portal.
"""

from __future__ import annotations

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]

ROUTES = {
    "/admin/jobs": "jobs",
    "/admin/jobs/failed": "failedJobs",
    "/admin/providers": "providers",
    "/admin/provider-cost": "providerCost",
    "/admin/workers": "workers",
    "/admin/features": "features",
    "/admin/freezes": "freezes",
    "/admin/runtime": "runtime",
}
JOB_RECOVERY_ROUTE = "/admin/job-recovery-guide"
NEW_KEYS = (
    "group.title",
    "group.description",
    *(f"{name}.{field}" for name in ROUTES.values() for field in ("title", "description")),
)
FIRST_PAINT_TITLES = {
    "/admin/jobs": {"vi": "Công việc · TOAN AAS", "en": "Jobs · TOAN AAS", "zh": "任务 · TOAN AAS"},
    "/admin/jobs/failed": {"vi": "Công việc thất bại · TOAN AAS", "en": "Failed jobs · TOAN AAS", "zh": "失败任务 · TOAN AAS"},
    "/admin/job-recovery-guide": {"vi": "Hướng dẫn xử lý Job-Lock · TOAN AAS", "en": "Job-Lock Recovery Guide · TOAN AAS", "zh": "任务锁恢复指南 · TOAN AAS"},
    "/admin/providers": {"vi": "Nhà cung cấp & chi phí · TOAN AAS", "en": "Providers & cost · TOAN AAS", "zh": "服务商与成本 · TOAN AAS"},
    "/admin/provider-cost": {"vi": "Chi phí nhà cung cấp · TOAN AAS", "en": "Provider cost · TOAN AAS", "zh": "服务商成本 · TOAN AAS"},
    "/admin/workers": {"vi": "Workers · TOAN AAS", "en": "Workers · TOAN AAS", "zh": "工作进程 · TOAN AAS"},
    "/admin/features": {"vi": "Sẵn sàng tính năng · TOAN AAS", "en": "Feature readiness · TOAN AAS", "zh": "功能就绪状态 · TOAN AAS"},
    "/admin/freezes": {"vi": "Bảo trì & đóng băng · TOAN AAS", "en": "Maintenance & freeze · TOAN AAS", "zh": "维护与冻结 · TOAN AAS"},
    "/admin/runtime": {"vi": "Runtime · TOAN AAS", "en": "Runtime · TOAN AAS", "zh": "运行时 · TOAN AAS"},
}


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _function_source(source: str, name: str) -> str:
    match = re.search(rf"(?:async )?function {re.escape(name)}\(", source)
    assert match, f"Missing function {name}"
    candidates = [
        source.find("\n  function ", match.end()),
        source.find("\n\n  const ", match.end()),
    ]
    end = min(candidate for candidate in candidates if candidate >= 0) if any(candidate >= 0 for candidate in candidates) else len(source)
    assert end > match.end(), f"Unable to bound function {name}"
    return source[match.start():end]


def _admin_generic_locale_block(source: str, locale: str) -> str:
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


def _first_paint_block(source: str, route: str) -> str:
    match = re.search(rf'"{re.escape(route)}": \{{(?P<titles>.*?)\}},', source, flags=re.DOTALL)
    assert match, f"Missing first-paint title mapping for {route}"
    return match.group("titles")


def test_delivery_runtime_navigation_catalogue_is_closed_equal_and_nonempty() -> None:
    i18n = _read("static/portal/portal-i18n.js")

    assert len(NEW_KEYS) == 18
    expected = {f"adminGeneric.deliveryRuntimeNavigation.{key}" for key in NEW_KEYS}
    for locale in ("vi", "en", "zh"):
        block = _admin_generic_locale_block(i18n, locale)
        actual = set(re.findall(r'"(adminGeneric\.deliveryRuntimeNavigation\.[^"]+)"\s*:', block))
        assert actual == expected
        for key in expected:
            value = re.search(rf'"{re.escape(key)}"\s*:\s*"(?P<value>(?:\\.|[^"\\])*)"', block)
            assert value and value.group("value").strip(), f"Missing reviewed {locale} copy for {key}"


def test_delivery_runtime_route_and_group_maps_are_exact_and_reuse_job_recovery_copy() -> None:
    portal = _read("static/portal/portal.js")
    route_helper = _function_source(portal, "adminDeliveryRuntimeNavigationText")
    group_helper = _function_source(portal, "adminDeliveryRuntimeGroupText")
    navigation = _function_source(portal, "adminErpNavigation")
    page_titles = _function_source(portal, "localizedPageTitle")
    page_descriptions = _function_source(portal, "localizedPageDescription")

    assert "const DELIVERY_RUNTIME_ROUTE_I18N = Object.freeze({" in portal
    assert "const DELIVERY_RUNTIME_GROUP_I18N = Object.freeze({" in portal
    for route, key in ROUTES.items():
        assert f'"{route}": {{ title: "adminGeneric.deliveryRuntimeNavigation.{key}.title", description: "adminGeneric.deliveryRuntimeNavigation.{key}.description" }}' in portal
        assert f'if (path === "{route}") return adminDeliveryRuntimeNavigationText(path, "title", fallback);' in page_titles
        assert f'if (path === "{route}") return adminDeliveryRuntimeNavigationText(path, "description", fallback);' in page_descriptions
    assert '"delivery_runtime": { title: "adminGeneric.deliveryRuntimeNavigation.group.title", description: "adminGeneric.deliveryRuntimeNavigation.group.description" }' in portal
    assert f'"{JOB_RECOVERY_ROUTE}": {{ title: "adminGeneric.jobRecoveryGuide.route.title", description: "adminGeneric.jobRecoveryGuide.route.description" }}' in portal
    assert f'if (path === "{JOB_RECOVERY_ROUTE}") return adminJobRecoveryGuideText("route.title", fallback);' in page_titles
    assert f'if (path === "{JOB_RECOVERY_ROUTE}") return adminJobRecoveryGuideText("route.description", fallback);' in page_descriptions

    for required in (
        "normalizePath(route)",
        "DELIVERY_RUNTIME_ROUTE_I18N",
        "uiText(entry[field], fallback)",
    ):
        assert required in route_helper
    for required in (
        "DELIVERY_RUNTIME_GROUP_I18N",
        'String(groupId || "")',
        "uiText(entry[field], fallback)",
    ):
        assert required in group_helper

    assert "const route = safeCatalogRoute" in navigation
    assert "routes.add(route)" in navigation
    assert "const localizedGroupTitle = adminDeliveryRuntimeGroupText(id, \"title\", title);" in navigation
    assert "const localizedGroupDescription = adminDeliveryRuntimeGroupText(id, \"description\", description);" in navigation
    assert "const localizedModuleTitle = adminDeliveryRuntimeNavigationText(route, \"title\", moduleTitle);" in navigation
    assert "const localizedModuleDescription = adminDeliveryRuntimeNavigationText(route, \"description\", moduleDescription);" in navigation
    assert "groups.push({ id, title: localizedGroupTitle, description: localizedGroupDescription, modules });" in navigation
    assert "title: localizedModuleTitle" in navigation
    assert "description: localizedModuleDescription" in navigation


def test_delivery_runtime_locale_projection_never_becomes_a_control_plane() -> None:
    portal = _read("static/portal/portal.js")
    route_helper = _function_source(portal, "adminDeliveryRuntimeNavigationText")
    group_helper = _function_source(portal, "adminDeliveryRuntimeGroupText")
    navigation = _function_source(portal, "adminErpNavigation")
    route_gate = _function_source(portal, "serverAuthorizesAdminRoute")

    for source in (route_helper, group_helper, navigation):
        for forbidden in (
            "fetch(", "api(", "data-portal-action", "<form", "<button", "localStorage", "sessionStorage",
            "setInterval", "adminData", "jobId", "/admin/modules/", "/clear_job_lock", "/retry", "/refund",
            "PayOS", "wallet", "provider call", "restart", "deploy",
        ):
            assert forbidden.lower() not in source.lower()
    for required in (
        "const routes = adminErpNavigation(context).routes;",
        "if (routes.has(normalized)) return true;",
        'normalized.startsWith("/admin/support/")',
        'normalized.startsWith("/admin/jobs/")',
    ):
        assert required in route_gate


def test_delivery_runtime_projection_keeps_admin_navigation_harness_self_contained() -> None:
    portal = _read("static/portal/portal.js")
    start = portal.index("const MAX_ADMIN_ERP_NAVIGATION_GROUPS = 16;")
    end = portal.index("function publicBuildId(value)", start)
    harness_prelude = portal[start:end]

    for declaration in (
        "const DELIVERY_RUNTIME_ROUTE_I18N = Object.freeze({",
        "const DELIVERY_RUNTIME_GROUP_I18N = Object.freeze({",
        "function adminDeliveryRuntimeNavigationText(route, field, fallback)",
        "function adminDeliveryRuntimeGroupText(groupId, field, fallback)",
        'typeof uiText === "function"',
    ):
        assert declaration in harness_prelude


def test_delivery_runtime_first_paint_titles_cover_only_the_reviewed_paths() -> None:
    pages = _read("copyfast_pages.py")

    for route, copies in FIRST_PAINT_TITLES.items():
        block = _first_paint_block(pages, route)
        for locale, title in copies.items():
            assert f'"{locale}": "{title}"' in block
