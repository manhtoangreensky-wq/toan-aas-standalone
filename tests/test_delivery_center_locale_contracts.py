"""Locale contracts for the customer Job and Asset delivery lists.

The catalogue owns fixed Web chrome only. Job/asset identifiers, feature names,
timestamps, costs, lifecycle values and signed delivery data remain canonical
server projections and must stay escaped at their existing boundaries.
"""

from __future__ import annotations

from pathlib import Path
import re

from copyfast_pages import render_portal


ROOT = Path(__file__).resolve().parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
I18N = (ROOT / "static" / "portal" / "portal-i18n.js").read_text(encoding="utf-8")
PAGES = (ROOT / "copyfast_pages.py").read_text(encoding="utf-8")


FIXED_KEYS = frozenset(
    {
        "page.jobs.title", "page.jobs.description", "page.assets.title", "page.assets.description",
        "filter.jobs", "filter.assets", "filter.result",
        "filter.jobs.all", "filter.jobs.queued", "filter.jobs.processing", "filter.jobs.completed",
        "filter.jobs.failed", "filter.jobs.cancelled", "filter.jobs.refunded",
        "filter.assets.all", "filter.assets.validated", "filter.assets.waiting", "filter.assets.completed",
        "filter.assets.failed", "filter.assets.web_vault",
        "status.output.none", "status.output.held", "status.output.reportedWaiting", "status.output.reportedPending",
        "status.delivery.pending", "status.delivery.vault", "status.delivery.validated", "status.delivery.validatedWaiting",
        "status.delivery.unavailable", "status.delivery.reported", "status.delivery.completedWaiting",
        "identity.vault.label", "identity.vault.description", "identity.webNative.label", "identity.webNative.description",
        "identity.canonical.label", "identity.canonical.description", "cost.estimated", "cost.ledger",
        "summary.jobs.label", "summary.jobs.active", "summary.jobs.activeDetail", "summary.jobs.attention",
        "summary.jobs.attentionDetail", "summary.jobs.completed", "summary.jobs.completedDetail",
        "summary.assets.label", "summary.assets.ready", "summary.assets.readyDetail", "summary.assets.waiting",
        "summary.assets.waitingDetail", "summary.assets.vault", "summary.assets.vaultDetail",
        "jobs.mobile.kicker", "jobs.mobile.detail", "jobs.mobile.workflow", "jobs.mobile.updated", "jobs.mobile.outputEngine", "jobs.mobile.canonicalCost",
        "jobs.first.note", "jobs.first.workflow", "jobs.first.drafts", "jobs.section.title", "jobs.section.subtitle",
        "jobs.refresh", "jobs.openAssets", "jobs.readStatus", "jobs.notice.title", "jobs.notice.body",
        "jobs.empty.title", "jobs.empty.filteredTitle", "jobs.empty.body", "jobs.empty.filteredBody",
        "jobs.table.job", "jobs.table.feature", "jobs.table.status", "jobs.table.cost", "jobs.table.updated", "jobs.table.output",
        "assets.mobile.openVault", "assets.mobile.openJobCenter", "assets.mobile.feature", "assets.mobile.createdAt", "assets.mobile.delivery",
        "assets.first.note", "assets.first.vault", "assets.first.workflow", "assets.section.title", "assets.section.subtitle",
        "assets.refresh", "assets.readStatus", "assets.empty.allTitle", "assets.empty.vaultTitle", "assets.empty.filterTitle",
        "assets.empty.allBody", "assets.empty.vaultBody", "assets.empty.filterBody",
        "assets.table.asset", "assets.table.feature", "assets.table.status", "assets.table.created", "assets.table.delivery",
    }
)


def _section(source: str, start: str, end: str) -> str:
    begin = source.index(start)
    return source[begin : source.index(end, begin + len(start))]


def _catalogue_keys(locale: str) -> set[str]:
    match = re.search(
        rf"Object\.assign\(DELIVERY_CENTER_MESSAGES\.{re.escape(locale)}, \{{(?P<body>.*?)\n  \}}\);",
        I18N,
        flags=re.DOTALL,
    )
    assert match, f"Missing delivery catalogue for {locale}"
    return set(re.findall(r'^\s*"deliveryCenter\.([^"]+)"\s*:', match.group("body"), flags=re.MULTILINE))


def test_delivery_catalogue_has_equal_reviewed_vi_en_zh_keys() -> None:
    assert "const DELIVERY_CENTER_MESSAGES = { vi: {}, en: {}, zh: {} };" in I18N
    catalogues = {locale: _catalogue_keys(locale) for locale in ("vi", "en", "zh")}
    assert catalogues["vi"] == catalogues["en"] == catalogues["zh"]
    assert FIXED_KEYS <= catalogues["vi"]
    assert "DELIVERY_CENTER_MESSAGES[locale]" in I18N
    used_keys = set(re.findall(r'deliveryCenterText\("([^"]+)"', PORTAL))
    assert used_keys <= catalogues["vi"]
    for key in FIXED_KEYS | used_keys:
        assert I18N.count(f'"deliveryCenter.{key}"') == 3


def test_delivery_lists_localize_fixed_copy_and_keep_canonical_records_escaped() -> None:
    shared = _section(PORTAL, "function reportedOutput(item)", "function renderJobDetail(page, context)")
    assets = _section(PORTAL, "function renderAssets(page, context)", "function validVaultAssetId")
    rendered = shared + assets

    assert "function deliveryCenterText(" in PORTAL
    for key in FIXED_KEYS:
        if key.startswith("page."):
            continue
        assert f'deliveryCenterText("{key}"' in rendered, key

    assert 'localizedDeliveryFilters("jobs", JOB_FILTERS)' in rendered
    assert 'localizedDeliveryFilters("assets", ASSET_FILTERS)' in rendered
    assert 'function localizedDeliveryFilters(group, filters)' in PORTAL

    for token in (
        "safeText(item.feature", "safeText(item.created_at", "safeText(item.updated_at", "safeText(item.id",
        "safeText(jobId", "safeText(assetId", "safeText(localizedAssetIdentityLabel(identity))",
        "safeText(localizedAssetIdentityDescription(identity))", "canonicalXu(", "jobCost(item)", "assetDeliveryState(item",
    ):
        assert token in rendered

    # The list renderers only declare browser actions; data loading remains in
    # the signed integration layer and no new endpoint/provider call is added.
    for forbidden in ("fetch(", "api(", "window.open(", "payment-create"):
        assert forbidden not in rendered
    assert 'data-portal-action="refresh-jobs"' in rendered
    assert 'data-portal-action="refresh-assets"' in rendered

    canonical_xu = _section(PORTAL, "function canonicalXu(value)", "function jobCost(item)")
    assert "localizedNumber(parsed)" in canonical_xu
    assert 'toLocaleString("vi-VN")' not in canonical_xu


def test_delivery_first_paint_is_route_and_locale_specific() -> None:
    expected = {
        "vi": {
            "/jobs": ("Job Center · TOAN AAS", "Theo dõi job thuộc sở hữu của phiên hiện tại; không hiện output giả khi chưa có delivery hợp lệ."),
            "/assets": ("Thư viện tài sản · TOAN AAS", "Tệp hoàn tất chỉ xuất hiện sau khi Core Bridge xác minh ownership và cung cấp URL ký tạm thời."),
        },
        "en": {
            "/jobs": ("Job Center · TOAN AAS", "Track jobs owned by the current session; do not show a fake output before valid delivery is available."),
            "/assets": ("Asset library · TOAN AAS", "Completed files appear only after Core Bridge verifies ownership and supplies a temporary signed URL."),
        },
        "zh": {
            "/jobs": ("任务中心 · TOAN AAS", "跟踪当前会话拥有的任务；在有效交付可用前不会显示虚假的输出。"),
            "/assets": ("资源库 · TOAN AAS", "只有在 Core Bridge 验证所有权并提供临时签名 URL 后，完成的文件才会显示。"),
        },
    }

    assert '"/jobs": {' in PAGES
    assert '"/assets": {' in PAGES
    for locale, routes in expected.items():
        for route, (title, description) in routes.items():
            response = render_portal(route, interface_locale=locale)
            assert response.status_code == 200
            assert f"<title>{title}</title>".encode("utf-8") in response.body
            assert f'<meta name="description" content="{description}">'.encode("utf-8") in response.body
