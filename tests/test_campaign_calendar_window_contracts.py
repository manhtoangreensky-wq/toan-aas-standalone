from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]
API = (ROOT / "copyfast_api.py").read_text(encoding="utf-8")
DB = (ROOT / "copyfast_db.py").read_text(encoding="utf-8")
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
INTEGRATION = (ROOT / "static" / "portal" / "integration.js").read_text(encoding="utf-8")
CSS = (ROOT / "static" / "portal" / "portal.css").read_text(encoding="utf-8")
CONTRACT = (ROOT / "docs" / "migration" / "CAMPAIGN_CALENDAR_WINDOW_CONTRACT.md").read_text(encoding="utf-8")


def test_campaign_calendar_window_route_is_owner_scoped_bounded_and_ordered_before_detail_route() -> None:
    calendar_route = API.index('@router.get("/campaign-calendar/window")')
    detail_route = API.index('@router.get("/campaigns/{plan_id}")')
    assert calendar_route < detail_route
    section = API[calendar_route:detail_route]
    for required in (
        "month: str",
        "CAMPAIGN_CALENDAR_WINDOW_MAX_ITEMS",
        "account_id=?",
        "scheduled_for!=''",
        "scheduled_for>=?",
        "scheduled_for<?",
        "ORDER BY scheduled_for ASC, updated_at DESC, id ASC",
        "status_name=\"read_only\"",
    ):
        assert required in section
    projection_start = API.index("def _campaign_calendar_public")
    projection = API[projection_start:API.index("def _workspace_draft_id", projection_start)]
    assert "destination_url" not in projection
    assert "review_note" not in projection
    assert "account_id" not in projection
    assert "canonical_user_id" not in projection
    assert "web_campaign_plans" in section
    assert "idx_web_campaign_plans_account_schedule_window" in DB


def test_campaign_calendar_browser_uses_a_dedicated_window_with_stale_response_fences() -> None:
    assert "function campaignCalendarSelection(raw, fallback)" in INTEGRATION
    assert "function campaignCalendarRequestIsCurrent(requestEpoch, sessionEpoch, expectedSelectionKey)" in INTEGRATION
    assert "async function hydrateCampaignCalendar(selectionValue)" in INTEGRATION
    assert 'api(campaignCalendarWindowPath(selected))' in INTEGRATION
    assert 'currentPath === "/calendar") await hydrateCampaignCalendar()' in INTEGRATION
    assert 'else if (account && ["/campaigns", "/approvals"].includes(currentPath)) await hydrateCampaignPlans()' in INTEGRATION
    assert '"campaign-calendar-view": Boolean(account)' in INTEGRATION
    assert '"campaign-calendar-refresh": Boolean(account)' in INTEGRATION
    for action in ("campaign-calendar-filter", "campaign-calendar-month", "campaign-calendar-refresh"):
        assert f'"{action}"' in INTEGRATION
    assert "++campaignCalendarHydrationEpoch;" in INTEGRATION
    assert "currentPortalPath() === \"/calendar\"" in INTEGRATION
    assert "campaignCalendarSelectionKey(selected) === expectedSelectionKey" in INTEGRATION
    assert "agenda from an all-plan list" in INTEGRATION
    assert '(status !== "all" && itemStatus !== status)' in PORTAL
    assert '(platform !== "all" && itemPlatform !== platform)' in PORTAL


def test_campaign_calendar_renderer_is_ephemeral_no_network_and_has_month_and_agenda_ui() -> None:
    start = PORTAL.index("function renderCampaignCalendar(page, context)")
    end = PORTAL.index("function renderCampaignApprovals(page, context)")
    calendar = PORTAL[start:end]
    assert "campaignCalendarWindow(context)" in calendar
    assert "data-portal-no-transient" in calendar
    assert "campaign-calendar-filter" in calendar
    assert "campaign-calendar-month" in calendar
    assert "campaign-calendar-refresh" in calendar
    assert "Agenda" in calendar
    overflow = subprocess.run(
        ["node", "--input-type=module", "--eval", """
import assert from 'node:assert/strict';
import {renderChild,calendarContext} from './tests/helpers/publishing-child-render.mjs';
for (const [locale, expected] of [['vi','+1 mốc đã tải'],['en','+1 loaded dates'],['zh','+1 个已加载日期']]) {
  const view = renderChild(locale, '/calendar', calendarContext());
  assert.ok(view.text.includes(expected), locale + ': overflow must use the interface language');
  assert.equal((view.html.match(/class="portal-calendar-event"/g) || []).length, 3);
  assert.equal((view.html.match(/class="portal-calendar-agenda-item"/g) || []).length, 4);
}
"""],
        cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=30,
    )
    assert overflow.returncode == 0, overflow.stdout + overflow.stderr
    assert "fetch(" not in calendar
    assert "localStorage" not in calendar
    assert "/api/v1/" not in calendar
    assert "data-campaign-calendar-month" in PORTAL
    for selector in (
        ".portal-calendar-filter",
        ".portal-calendar-agenda",
        ".portal-calendar-agenda-item",
    ):
        assert selector in CSS


def test_campaign_calendar_contract_keeps_web_native_boundaries_explicit() -> None:
    for required in (
        "read-only",
        "account_id = current account",
        "200 items",
        "Admin Calendar",
        "PayOS",
        "local, inert planning timestamp",
        "no-network/no-browser-storage boundary",
    ):
        assert required in CONTRACT
