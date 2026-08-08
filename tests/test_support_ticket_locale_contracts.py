"""Locale and route-safety contracts for customer Support Desk and Tickets.

Only fixed interface copy belongs in this catalogue.  Case identifiers,
subjects, replies, timestamps, evidence, ownership and server state remain
canonical dynamic values at their existing escaping and authorization edges.
"""

from __future__ import annotations

from pathlib import Path
import re

from fastapi import HTTPException
import pytest

from copyfast_pages import render_portal


ROOT = Path(__file__).resolve().parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
I18N = (ROOT / "static" / "portal" / "portal-i18n.js").read_text(encoding="utf-8")
PAGES = (ROOT / "copyfast_pages.py").read_text(encoding="utf-8")


CUSTOMER_KEYS = frozenset(
    {
        "category.general_support", "category.image_error", "category.video_error",
        "category.document_pdf", "category.payment_topup", "category.package_combo",
        "category.refund", "category.feature_request", "category.lead_consulting",
        "category.service_consulting", "category.premium_lead", "category.custom_bot_lead",
        "category.other", "category.fallback",
        "priority.low", "priority.normal", "priority.high", "priority.urgent",
        "state.new", "state.reviewing", "state.waiting_user", "state.waiting_provider",
        "state.refund_pending", "state.resolved", "state.closed", "state.guarded",
        "hero.support.section", "hero.tickets.section", "hero.ticketDetail.section",
        "hero.support.actionLabel",
        "desk.intro.kicker", "desk.intro.title", "desk.intro.body",
        "desk.intake.title", "desk.intake.description", "desk.intake.create",
        "cases.filter.title", "cases.list.title", "cases.create",
        "detail.unavailable.title", "detail.reply.title", "detail.timeline.title",
        "tickets.title", "tickets.description", "tickets.create",
    }
)


RENDERER_FIXED_COPY_KEYS = {
    "advisor": frozenset(
        {
            "advisor.reason.enabled", "advisor.reason.disabled", "advisor.reason.signIn",
            "advisor.unavailable.loading", "advisor.unavailable.guardedAvailable",
            "advisor.unavailable.guardedDisabled", "advisor.unavailable.idle",
            "advisor.result.useCategory", "advisor.result.noneCreated", "advisor.kicker",
            "advisor.title", "advisor.description", "advisor.form.category",
            "advisor.form.submit",
        }
    ),
    "consultation": frozenset(
        {
            "consultation.reason.signIn", "consultation.reason.loading",
            "consultation.reason.guarded", "consultation.reason.ready",
            "consultation.retry.button", "consultation.retry.note",
            "consultation.result.kicker", "consultation.result.summary",
            "consultation.result.handoffConfirm", "consultation.result.handoff",
            "consultation.result.handoffNote",
            "consultation.result.loading", "consultation.result.idle",
            "consultation.kicker", "consultation.title", "consultation.description",
            "consultation.form.service", "consultation.form.servicePlaceholder",
            "consultation.form.goal", "consultation.form.goalPlaceholder",
            "consultation.form.context", "consultation.form.contextPlaceholder",
            "consultation.form.outcome", "consultation.form.outcomePlaceholder",
            "consultation.form.privacyHelp", "consultation.form.submit",
        }
    ),
    "triage": frozenset(
        {
            "triage.title", "triage.guarded.description", "triage.guarded.noticeTitle",
            "triage.guarded.noticeBody", "triage.description", "triage.sla.label",
            "triage.sla.withinTarget", "triage.sla.atRisk", "triage.sla.breached",
            "triage.sla.terminal", "triage.sla.unverified", "triage.sla.guarded",
            "triage.priority", "triage.role", "triage.role.operator", "triage.updated",
            "triage.note",
        }
    ),
}

REVIEWED_CUSTOMER_KEYS = CUSTOMER_KEYS | frozenset().union(*RENDERER_FIXED_COPY_KEYS.values())


CANONICAL_SUPPORT_STATES = (
    "new",
    "reviewing",
    "waiting_user",
    "waiting_provider",
    "refund_pending",
    "resolved",
    "closed",
)


SUPPORT_HERO_COPY = {
    "vi": {
        "hero.support.section": "Khách hàng",
        "hero.tickets.section": "Khách hàng",
        "hero.ticketDetail.section": "Web Support Desk",
        "hero.support.actionLabel": "Tạo yêu cầu",
    },
    "en": {
        "hero.support.section": "Customer",
        "hero.tickets.section": "Customer",
        "hero.ticketDetail.section": "Web Support Desk",
        "hero.support.actionLabel": "Create request",
    },
    "zh": {
        "hero.support.section": "客户",
        "hero.tickets.section": "客户",
        "hero.ticketDetail.section": "Web 支持服务台",
        "hero.support.actionLabel": "创建请求",
    },
}


def _catalogue_keys(locale: str) -> set[str]:
    match = re.search(
        rf"Object\.assign\(SUPPORT_TICKET_MESSAGES\.{re.escape(locale)}, \{{(?P<body>.*?)\n  \}}\);",
        I18N,
        flags=re.DOTALL,
    )
    assert match, f"Missing Support/Ticket catalogue for {locale}"
    return set(re.findall(r'^\s*"supportTicket\.([^"]+)"\s*:', match.group("body"), flags=re.MULTILINE))


def _catalogue_text(locale: str, key: str) -> str:
    match = re.search(
        rf"Object\.assign\(SUPPORT_TICKET_MESSAGES\.{re.escape(locale)}, \{{(?P<body>.*?)\n  \}}\);",
        I18N,
        flags=re.DOTALL,
    )
    assert match, f"Missing Support/Ticket catalogue for {locale}"
    value = re.search(
        rf'^\s*"supportTicket\.{re.escape(key)}":\s*"(?P<text>[^"]*)",?$',
        match.group("body"),
        flags=re.MULTILINE,
    )
    assert value, f"Missing Support/Ticket text for {locale}:{key}"
    return value.group("text")


# Keep the static scan narrow: customer Support Desk/Ticket entry points only,
# rather than every supportTicketText call in the portal bundle.
CUSTOMER_SUPPORT_RENDERER_BOUNDS = (
    ("function supportTicketHeroRouteKey", "const FEATURE_CATALOG_GROUPS"),
    ("function supportCaseCategoryLabel", "function operationsDisplayState"),
    (
        "function renderSupportCaseTriage",
        "// Inbox intentionally renders metadata only.",
    ),
    ("function renderTickets", "function renderSupportAdminSummary"),
)
DIRECT_SUPPORT_TICKET_LITERAL_RE = re.compile(r'\bsupportTicketText\(\s*"([^"]+)"')


def _section(start: str, end: str, source: str = PORTAL) -> str:
    offset = source.index(start)
    return source[offset:source.index(end, offset + len(start))]


def _customer_support_renderer_source() -> str:
    return "\n".join(_section(start, end) for start, end in CUSTOMER_SUPPORT_RENDERER_BOUNDS)


def _direct_support_ticket_literal_keys(source: str) -> set[str]:
    return set(DIRECT_SUPPORT_TICKET_LITERAL_RE.findall(source))


def _missing_support_ticket_literal_keys(source: str, catalogue: set[str]) -> set[str]:
    return _direct_support_ticket_literal_keys(source) - catalogue


def test_support_ticket_literal_detector_reports_missing_key_from_supplied_source() -> None:
    source = '''
      const title = supportTicketText("desk.intake.title", "Create request");
      const missing = supportTicketText("detector.missing", "Missing from catalogues");
    '''

    assert _missing_support_ticket_literal_keys(source, {"desk.intake.title"}) == {"detector.missing"}


def test_customer_support_renderer_literal_keys_exist_in_equal_vi_en_zh_catalogues() -> None:
    catalogues = {locale: _catalogue_keys(locale) for locale in ("vi", "en", "zh")}
    assert catalogues["vi"] == catalogues["en"] == catalogues["zh"]

    source = _customer_support_renderer_source()
    derived_keys = _direct_support_ticket_literal_keys(source)
    assert derived_keys, "Customer support renderer bounds must contain literal supportTicketText calls"

    missing_by_locale = {
        locale: _missing_support_ticket_literal_keys(source, catalogue)
        for locale, catalogue in catalogues.items()
    }
    assert not any(missing_by_locale.values()), missing_by_locale


def test_customer_support_ticket_catalogue_has_equal_reviewed_vi_en_zh_keys() -> None:
    catalogues = {locale: _catalogue_keys(locale) for locale in ("vi", "en", "zh")}

    assert catalogues["vi"] == catalogues["en"] == catalogues["zh"]
    assert REVIEWED_CUSTOMER_KEYS <= catalogues["vi"]
    for key in REVIEWED_CUSTOMER_KEYS:
        assert I18N.count(f'"supportTicket.{key}"') == 3


def test_customer_support_renderers_localize_only_fixed_copy() -> None:
    enum_labels = _section("function supportCaseCategoryLabel", "function supportAdvisorText")
    helpers = _section("function supportCaseTimestamp", "function renderSupportDesk")
    desk = _section("function renderSupportDesk", "function renderSupportCases")
    cases = _section("function renderSupportCases", "function renderSupportResolutionFeedback")
    detail = _section("function renderSupportCaseDetail", "function operationsDisplayState")
    tickets = _section("function renderTickets", "function renderSupportAdminSummary")

    # The canonical enum remains unchanged, while its presentation key is
    # derived from the closed local category/priority/state catalogues.
    for needle in (
        'supportTicketText(`category.${match[0]}`',
        'supportTicketText(`priority.${match[0]}`',
        'supportTicketText(`state.${state}`',
    ):
        assert needle in enum_labels

    for renderer, keys in {
        desk: {"desk.intro.kicker", "desk.intake.title", "desk.intake.create"},
        cases: {"cases.filter.title", "cases.list.title", "cases.create"},
        detail: {"detail.unavailable.title", "detail.reply.title", "detail.timeline.title"},
        tickets: {"tickets.title", "tickets.description", "tickets.create"},
    }.items():
        for key in keys:
            assert f'supportTicketText("{key}"' in renderer, key

    # Browser-side locale changes presentation only.  These renderers keep
    # owner-scoped ids and content escaped, and do not gain a data authority.
    assert "new Intl.DateTimeFormat(supportTicketLocale()" in helpers
    assert "safeText(String(caseItem.id).slice(0, 8))" in detail
    assert 'data-support-case-id="${safeText(caseItem.id)}"' in detail
    assert "fetch(" not in helpers + desk + cases + detail + tickets


def test_customer_support_badges_and_hero_chrome_are_route_scoped_and_localized() -> None:
    badge_helper = _section("function badge", "function subtitleAssetOperationsReadBadge")
    support_helpers = _section("function supportCaseState", "function supportAdvisorText")
    case_cards = _section("function renderSupportCaseCards", "function renderSupportCasePagination")
    detail = _section("function renderSupportCaseDetail", "function operationsDisplayState")
    triage = _section("function renderSupportCaseTriage", "// Inbox intentionally renders metadata only.")
    hero = _section("function renderHero", "const FEATURE_CATALOG_GROUPS")

    violations: list[str] = []

    for state in CANONICAL_SUPPORT_STATES:
        if f"state.{state}" not in REVIEWED_CUSTOMER_KEYS:
            violations.append(f"missing reviewed state key for {state}")
        if I18N.count(f'"supportTicket.state.{state}"') != 3:
            violations.append(f"missing vi/en/zh catalogue state label for {state}")

    for locale, copy in SUPPORT_HERO_COPY.items():
        for key, value in copy.items():
            if f'"supportTicket.{key}": "{value}"' not in I18N:
                violations.append(f"missing {locale} hero catalogue copy for {key}")

    required_badge_contracts = (
        ("badge supports a fixed presentation label", "function badge(status, label)" in badge_helper),
        ("badge falls back to the global state label", "label || stateLabel(normalized)" in badge_helper),
        ("support states have a support-only badge helper", "function supportCaseBadge" in support_helpers),
        ("support badge uses the local state catalogue", "return badge(state, supportCaseStateLabel(state));" in support_helpers),
        ("customer cards use the local status badge", "admin ? badge(state) : supportCaseBadge(state)" in case_cards),
        ("customer detail uses the local status badge", "${supportCaseBadge(state)}" in detail),
        ("terminal triage badge uses the local SLA label", '${badge(operationsDisplayState(sla, "sla"), slaText)}' in triage),
    )
    required_hero_contracts = (
        ("hero has a support route key helper", "function supportTicketHeroRouteKey" in hero),
        ("hero gates /support exactly", 'route === "/support"' in hero),
        ("hero gates /tickets exactly", 'route === "/tickets"' in hero),
        ("hero gates ticket detail with a strict UUID matcher", "SUPPORT_TICKET_HERO_DETAIL_PATH.test(route)" in hero),
        ("hero has a route-scoped section helper", "function supportTicketHeroSection" in hero),
        ("hero has a support-only action label helper", "function supportTicketHeroActionLabel" in hero),
        ("hero localizes its section through the helper", "supportTicketHeroSection(page)" in hero),
        ("hero localizes its action label through the helper", "supportTicketHeroActionLabel(page)" in hero),
        ("hero section derives its key from the strict route", "supportTicketText(`hero.${routeKey}.section`" in hero),
        ("hero action label is restricted to /support", 'routeKey === "support"' in hero),
        ("hero action label reads the support catalogue", 'supportTicketText("hero.support.actionLabel"' in hero),
    )
    violations.extend(label for label, satisfied in required_badge_contracts + required_hero_contracts if not satisfied)

    assert not violations, "\n".join(violations)


def test_support_terminal_sla_label_is_neutral_across_resolved_and_closed_cases() -> None:
    assert _catalogue_text("vi", "triage.sla.terminal") == "Đã kết thúc"
    assert _catalogue_text("en", "triage.sla.terminal") == "Terminal"
    assert _catalogue_text("zh", "triage.sla.terminal") == "已结束"


def test_support_hero_cta_links_to_validated_intake_without_dispatching_create() -> None:
    hero = _section("function renderHero", "const SUPPORT_TICKET_HERO_DETAIL_PATH")
    support_action = re.search(
        r'const supportHeroAction = route === "/support"\s*'
        r'\? `(?P<markup><a\b.*?</a>)`\s*'
        r': "";',
        hero,
        flags=re.DOTALL,
    )

    assert support_action, "the /support hero must use a route-scoped intake link"
    support_markup = support_action.group("markup")
    assert 'href="#support-subject"' in support_markup
    assert "data-portal-action" not in support_markup
    assert "support-case-create" not in support_markup

    # Non-support routes retain the generic enabled/disabled action button.
    assert 'route !== "/support" && showHeroAction' in hero
    assert 'data-portal-action="${safeText(page.action)}"' in hero
    assert "${supportHeroAction}${genericHeroAction}" in hero


def test_support_advisor_consultation_and_triage_localize_fixed_copy() -> None:
    regions = {
        "advisor": _section("function renderSupportAdvisor", "const SUPPORT_CONSULTATION_CATALOG_VERSION"),
        "consultation": _section("function renderSupportConsultationBrief", "function supportCaseTimestamp"),
        "triage": _section("function renderSupportCaseTriage", "// Inbox intentionally renders metadata only."),
    }

    for name, region in regions.items():
        used_keys = set(re.findall(r'supportTicketText\(\s*"([^"]+)"', region))
        assert RENDERER_FIXED_COPY_KEYS[name] <= used_keys


def test_customer_support_first_paint_is_localized_and_ticket_detail_is_strict() -> None:
    case_id = "1c4f86fe-12e5-4a67-9b92-c9d50309a2e1"
    expected = {
        "vi": {
            "/support": ("Hỗ trợ · TOAN AAS", "Tạo và theo dõi yêu cầu Support Desk theo signed Web account; Web không gửi nội dung sang Telegram hoặc provider."),
            "/tickets": ("Yêu cầu của tôi · TOAN AAS", "Theo dõi các yêu cầu Web thuộc signed account hiện tại; case, phản hồi và quyền sở hữu luôn do máy chủ xác minh."),
            f"/tickets/{case_id}": ("Chi tiết yêu cầu · TOAN AAS", "Xem case Support Desk owner-scoped; nội dung và trạng thái chỉ mở sau khi máy chủ xác minh phiên hiện tại."),
        },
        "en": {
            "/support": ("Support · TOAN AAS", "Create and track Support Desk requests for the signed Web account; the Web does not send content to Telegram or providers."),
            "/tickets": ("My requests · TOAN AAS", "Track Web requests owned by the current signed account; cases, replies and ownership are always verified by the server."),
            f"/tickets/{case_id}": ("Request details · TOAN AAS", "Review an owner-scoped Support Desk case; content and state open only after the server verifies the current session."),
        },
        "zh": {
            "/support": ("支持 · TOAN AAS", "为已签名 Web 账户创建和跟踪支持请求；Web 不会将内容发送到 Telegram 或服务商。"),
            "/tickets": ("我的请求 · TOAN AAS", "跟踪当前已签名账户拥有的 Web 请求；case、回复和所有权始终由服务器验证。"),
            f"/tickets/{case_id}": ("请求详情 · TOAN AAS", "查看仅限所有者的 Support Desk case；内容和状态仅在服务器验证当前会话后开放。"),
        },
    }

    assert "TICKET_DETAIL_PATH" in PAGES
    for locale, routes in expected.items():
        for path, (title, description) in routes.items():
            response = render_portal(path, interface_locale=locale)
            assert response.status_code == 200
            assert f"<title>{title}</title>".encode("utf-8") in response.body
            assert f'<meta name="description" content="{description}">'.encode("utf-8") in response.body

    for invalid in ("/tickets/not-a-uuid", f"/tickets/{case_id}/nested", "/tickets/%3Cscript%3E"):
        with pytest.raises(HTTPException):
            render_portal(invalid, interface_locale="en")
