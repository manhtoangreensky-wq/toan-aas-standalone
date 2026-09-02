"""Customer top-up and fixed-control locale-purity contracts.

The interface locale is presentation-only. These tests must never create a
payment, provider call, wallet mutation, Telegram action, or production data.
"""

from pathlib import Path
import json
import subprocess


ROOT = Path(__file__).resolve().parents[1]
I18N_PATH = ROOT / "static/portal/portal-i18n.js"
PORTAL_PATH = ROOT / "static/portal/portal.js"
INTEGRATION_PATH = ROOT / "static/portal/integration.js"
I18N = I18N_PATH.read_text(encoding="utf-8")
PORTAL = PORTAL_PATH.read_text(encoding="utf-8")
INTEGRATION = INTEGRATION_PATH.read_text(encoding="utf-8")

EXPECTED_TOPUP_MESSAGES = {
    "customerTopup.assistant.label": ("Trợ lý AI AAS BOT", "AAS BOT AI Assistant", "AAS BOT AI 助手"),
    "customerTopup.assistant.openAria": ("Mở Trợ lý AI AAS BOT", "Open AAS BOT AI Assistant", "打开 AAS BOT AI 助手"),
    "customerTopup.history.unavailable": ("Lịch sử biến động Xu chưa sẵn sàng", "Xu transaction history is not ready", "Xu 变动记录尚未就绪"),
    "customerTopup.installApp": ("Cài đặt ứng dụng", "Install app", "安装应用"),
    "customerTopup.installAppAria": ("Cài đặt ứng dụng TOAN AAS", "Install the TOAN AAS app", "安装 TOAN AAS 应用"),
    "customerTopup.journey.aria": ("Quy trình nạp Xu", "Xu top-up flow", "Xu 充值流程"),
    "customerTopup.journey.description": ("Hỗ trợ tất cả ứng dụng ngân hàng và ví điện tử Việt Nam.", "Supports Vietnamese banking apps and e-wallets.", "支持越南银行应用和电子钱包。"),
    "customerTopup.journey.kicker": ("Quy trình nạp tiền", "Top-up flow", "充值流程"),
    "customerTopup.journey.step1.text": ("Chọn mệnh giá hoặc gói Xu phù hợp nhu cầu.", "Select the Xu amount or package that fits your needs.", "选择符合需要的 Xu 金额或套餐。"),
    "customerTopup.journey.step1.title": ("Chọn gói nạp", "Choose a top-up", "选择充值"),
    "customerTopup.journey.step2.text": ("Quét mã VietQR hoặc cổng PayOS bảo mật.", "Scan VietQR or use the secure PayOS gateway.", "扫描 VietQR 或使用安全的 PayOS 网关。"),
    "customerTopup.journey.step2.title": ("Thanh toán QR 24/7", "Pay by QR 24/7", "全天候二维码支付"),
    "customerTopup.journey.step3.text": ("Số dư tự động cập nhật trong 5-30 giây.", "The balance updates automatically within 5–30 seconds.", "余额将在 5–30 秒内自动更新。"),
    "customerTopup.journey.step3.title": ("Nhận Xu tức thì", "Receive Xu instantly", "即时获得 Xu"),
    "customerTopup.journey.title": ("Quy trình nạp Xu tức thì", "Instant Xu top-up flow", "Xu 即时充值流程"),
    "customerTopup.lane.manual": ("Nạp Thủ Công (ACB / MoMo / ZaloPay)", "Manual top-up (ACB / MoMo / ZaloPay)", "人工充值（ACB / MoMo / ZaloPay）"),
    "customerTopup.lane.payos": ("Cổng Nạp Tự Động PayOS (5-30s)", "Automatic PayOS top-up (5–30s)", "PayOS 自动充值（5–30 秒）"),
    "customerTopup.lookup.body": ("Tra cứu trạng thái nạp tiền theo mã đơn hàng.", "Check top-up status using the order ID.", "使用订单号查询充值状态。"),
    "customerTopup.lookup.fieldHelp": ("Nhập mã đơn hàng PayOS để kiểm tra trạng thái thanh toán.", "Enter the PayOS order ID to check its payment status.", "输入 PayOS 订单号以查询付款状态。"),
    "customerTopup.lookup.fieldLabel": ("Mã đơn PayOS / order code", "PayOS order ID / order code", "PayOS 订单号 / order code"),
    "customerTopup.lookup.fieldPlaceholder": ("Ví dụ: 12345678", "Example: 12345678", "示例：12345678"),
    "customerTopup.lookup.submit": ("Kiểm tra đơn PayOS", "Check PayOS order", "查询 PayOS 订单"),
    "customerTopup.lookup.summary": ("Tra cứu trạng thái đơn hàng PayOS", "Check PayOS order status", "查询 PayOS 订单状态"),
    "customerTopup.lookup.title": ("Kiểm tra đơn PayOS", "Check a PayOS order", "查询 PayOS 订单"),
    "customerTopup.membership.nav": ("👑 Hạng hội viên & VIP", "👑 Membership & VIP", "👑 会员与 VIP"),
    "customerTopup.package.rate": ("Tỷ lệ canonical: {amount} = {xu}", "Canonical rate: {amount} = {xu}", "canonical 比率：{amount} = {xu}"),
    "customerTopup.page.description": ("Chọn cổng PayOS khi tài khoản đủ điều kiện, hoặc tạo yêu cầu đối soát thủ công trực tiếp trên Web. Xu chỉ được cộng sau khi xác nhận thanh toán.", "Choose PayOS when the account is eligible, or create a manual reconciliation request directly on the Web. Xu is credited only after payment is confirmed.", "账户符合条件时可选择 PayOS，或直接在 Web 上创建人工对账请求。只有确认付款后才会增加 Xu。"),
    "customerTopup.page.title": ("Nạp Xu", "Top up credits", "充值积分"),
    "customerTopup.paymentFlow.amountLabel": ("Số tiền", "Amount", "金额"),
    "customerTopup.paymentFlow.body": ("Quét mã VietQR hoặc mở trang thanh toán PayOS để hoàn tất.", "Scan VietQR or open the PayOS payment page to finish.", "扫描 VietQR 或打开 PayOS 支付页面以完成充值。"),
    "customerTopup.paymentFlow.kicker": ("Thanh toán PayOS", "PayOS payment", "PayOS 支付"),
    "customerTopup.paymentFlow.open": ("Mở lại trang thanh toán PayOS", "Reopen the PayOS payment page", "重新打开 PayOS 支付页面"),
    "customerTopup.paymentFlow.orderLabel": ("Mã đơn", "Order ID", "订单号"),
    "customerTopup.paymentFlow.paid": ("Đã thanh toán thành công", "Payment confirmed", "付款已确认"),
    "customerTopup.paymentFlow.pending": ("Đang chờ chuyển khoản", "Awaiting bank transfer", "等待银行转账"),
    "customerTopup.paymentFlow.refresh": ("Kiểm tra trạng thái", "Check status", "查询状态"),
    "customerTopup.paymentFlow.statusLabel": ("Trạng thái", "Status", "状态"),
    "customerTopup.paymentFlow.title": ("Trạng thái yêu cầu nạp Xu", "Xu top-up request status", "Xu 充值请求状态"),
    "customerTopup.paymentFlow.waiting": ("Đang chờ quét mã thanh toán...", "Waiting for the payment QR to be scanned...", "等待扫描付款二维码..."),
    "customerTopup.paymentFlow.xuReceivedLabel": ("Xu nhận được", "Xu received", "收到的 Xu"),
    "customerTopup.payos.kicker": ("Cổng nạp tự động VietQR 24/7", "Automatic VietQR gateway 24/7", "全天候 VietQR 自动充值网关"),
    "customerTopup.payos.limitNotice": ("Cổng tự động PayOS áp dụng mức nạp tối đa {limit} mỗi giao dịch. Nếu cần nạp nhiều hơn, hãy chuyển sang {manualLane} để được hỗ trợ đối soát.", "Automatic PayOS top-ups are limited to {limit} per transaction. For a larger top-up, use {manualLane} for assisted reconciliation.", "PayOS 自动充值每笔最高为 {limit}。如需充值更高金额，请使用{manualLane}进行人工对账。"),
    "customerTopup.payos.noteTitle": ("Lưu ý:", "Note:", "注意："),
    "customerTopup.payos.ratioInstruction": ("Chọn mệnh giá nạp và mở cổng thanh toán. VietQR sẽ tự động đối soát trong 5–30 giây.", "Choose a top-up amount and open the payment gateway. VietQR reconciles the payment automatically within 5–30 seconds.", "选择充值金额并打开支付网关。VietQR 会在 5–30 秒内自动对账。"),
    "customerTopup.payos.ratioPrefix": ("Tỷ lệ quy đổi", "Exchange rate", "兑换比例"),
    "customerTopup.payos.title": ("Nạp Xu tự động trực tuyến qua PayOS", "Automatic online Xu top-up with PayOS", "通过 PayOS 在线自动充值 Xu"),
    "customerTopup.payos.unavailable": ("Cổng PayOS hoặc danh mục mệnh giá hiện chưa sẵn sàng.", "PayOS or the top-up catalogue is not ready yet.", "PayOS 或充值目录尚未就绪。"),
    "customerTopup.section.customer": ("Khách hàng", "Customer", "客户"),
    "customerTopup.submit": ("Nạp ngay (Mở cổng PayOS)", "Top up now (Open PayOS)", "立即充值（打开 PayOS）"),
    "customerTopup.supportedBanks": ("Hỗ trợ tất cả ngân hàng Việt Nam, MoMo, ZaloPay và ViettelPay.", "Supports Vietnamese banks, MoMo, ZaloPay and ViettelPay.", "支持越南各银行、MoMo、ZaloPay 和 ViettelPay。"),
    "customerTopup.wallet.unavailableBody": ("Web không thay thế ledger bằng activity, payment receipt hay giá trị 0.", "The Web does not replace the ledger with activity, payment receipts or a zero value.", "Web 不会用活动记录、付款凭证或零值替代账本。"),
    "interfaceLocale.updated": ("Đã cập nhật ngôn ngữ giao diện.", "Interface language updated.", "界面语言已更新。"),
}


def section(source: str, start: str, end: str) -> str:
    start_at = source.index(start)
    end_at = source.index(end, start_at + len(start))
    return source[start_at:end_at]


def catalogue() -> dict[str, dict[str, str]]:
    keys = sorted(EXPECTED_TOPUP_MESSAGES)
    script = r"""
require(process.argv[1]);
const api = globalThis.TOANAASI18n;
const keys = JSON.parse(process.argv[2]);
const out = {};
for (const locale of ["vi", "en", "zh"]) {
  out[locale] = Object.fromEntries(keys.map((key) => [key, api.messages[locale][key]]));
}
process.stdout.write(JSON.stringify(out));
"""
    result = subprocess.run(
        ["node", "-e", script, str(I18N_PATH), json.dumps(keys)],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


def test_customer_topup_catalogue_has_exact_reviewed_vi_en_zh_values() -> None:
    messages = catalogue()
    assert len(EXPECTED_TOPUP_MESSAGES) == 52
    for index, locale in enumerate(("vi", "en", "zh")):
        assert messages[locale] == {
            key: translations[index] for key, translations in EXPECTED_TOPUP_MESSAGES.items()
        }


def test_topup_renderers_use_distinct_catalogue_keys_without_cross_surface_leakage() -> None:
    title = section(PORTAL, "function localizedPageTitle", "function documentTitle")
    description = section(PORTAL, "function localizedPageDescription", "function initials")
    nav_map = section(PORTAL, "const NAVIGATION_I18N_KEYS", "function localizedNavigationLabel")
    billing_nav = section(PORTAL, "function renderBillingWorkspaceNav", "function renderPaymentEntryPoints")
    entrypoints = section(PORTAL, "function renderPaymentEntryPoints", "function manualTopupStatusLabel")
    request_form = section(PORTAL, "function renderPaymentRequestForm", "function renderPaymentLookup")
    lookup = section(PORTAL, "function renderPaymentLookup", "function renderPaymentFlow")
    flow = section(PORTAL, "function renderPaymentFlow", "function renderBillingJourney")
    journey = section(PORTAL, "function renderBillingJourney", "function renderWallet")
    wallet = section(PORTAL, "function renderWallet", "const DEFAULT_CANONICAL_PACKAGES")
    pwa = section(PORTAL, "function syncSmartInstallBanner", "function dismissSmartInstallBanner")
    copilot = section(PORTAL, "function renderCopilotHtml", "function mountPortalAiCopilot")
    mount = section(PORTAL, "function mountPortal(override)", "function executeCopilotQuery")
    topup_lane_handler = section(
        PORTAL,
        'const topupLaneBtn = event.target.closest("[data-portal-topup-lane]")',
        'const manualTabBtn = event.target.closest("[data-portal-manual-tab]")',
    )

    assert '"Khách hàng": "customerTopup.section.customer"' in nav_map
    assert 'path === "/wallet/topup"' in title
    assert 'uiText("customerTopup.page.title"' in title
    assert 'path === "/wallet/topup"' in description
    assert 'uiText("customerTopup.page.description"' in description
    assert 'uiText("customerTopup.membership.nav"' in billing_nav
    assert 'uiText("customerTopup.lane.payos"' in entrypoints
    assert 'uiText("customerTopup.lane.manual"' in entrypoints
    for key in (
        "customerTopup.payos.kicker",
        "customerTopup.payos.title",
        "customerTopup.payos.ratioPrefix",
        "customerTopup.payos.ratioInstruction",
        "customerTopup.payos.limitNotice",
        "customerTopup.package.rate",
        "customerTopup.payos.unavailable",
        "customerTopup.supportedBanks",
        "customerTopup.submit",
        "customerTopup.lookup.summary",
    ):
        assert f'uiText("{key}"' in request_form
    for key in (
        "customerTopup.lookup.fieldLabel",
        "customerTopup.lookup.fieldPlaceholder",
        "customerTopup.lookup.fieldHelp",
        "customerTopup.lookup.title",
        "customerTopup.lookup.body",
        "customerTopup.lookup.submit",
    ):
        assert f'uiText("{key}"' in lookup
    for key in (
        "customerTopup.paymentFlow.kicker",
        "customerTopup.paymentFlow.title",
        "customerTopup.paymentFlow.body",
        "customerTopup.paymentFlow.statusLabel",
        "customerTopup.paymentFlow.orderLabel",
        "customerTopup.paymentFlow.amountLabel",
        "customerTopup.paymentFlow.xuReceivedLabel",
        "customerTopup.paymentFlow.paid",
        "customerTopup.paymentFlow.pending",
        "customerTopup.paymentFlow.waiting",
        "customerTopup.paymentFlow.open",
        "customerTopup.paymentFlow.refresh",
    ):
        assert f'uiText("{key}"' in flow
    assert 'status === "ready" || status === "completed"' in flow
    fact_bindings = (
        ('customerTopup.paymentFlow.statusLabel', 'Trạng thái', "status === 'ready'"),
        ('customerTopup.paymentFlow.orderLabel', 'Mã đơn', 'safeText(orderId || "PayOS Order")'),
        ('customerTopup.paymentFlow.amountLabel', 'Số tiền', 'adminNumber(data.amount_vnd, " đ")'),
        ('customerTopup.paymentFlow.xuReceivedLabel', 'Xu nhận được', 'adminNumber(data.xu, " Xu")'),
    )
    binding_offsets = []
    for key, fallback, value_owner in fact_bindings:
        label = f'<span class="portal-summary-key">${{safeText(uiText("{key}", "{fallback}"))}}</span>'
        assert label in flow
        binding_offsets.append(flow.index(label))
    assert binding_offsets == sorted(binding_offsets)
    binding_limits = binding_offsets[1:] + [flow.index('</div><div class="portal-form-footer"', binding_offsets[-1])]
    for (_, _, value_owner), start_at, end_at in zip(fact_bindings, binding_offsets, binding_limits):
        assert value_owner in flow[start_at:end_at]
    assert "customerTopup.paymentFlow.factLabels" not in PORTAL
    assert 'uiText("customerTopup.journey.title"' in journey
    assert 'uiText("customerTopup.wallet.unavailableBody"' in wallet
    assert 'uiText("customerTopup.installApp"' in pwa
    assert 'uiText("customerTopup.installAppAria"' in pwa
    assert (
        'document.body.appendChild(fab);\n      }\n'
        '      fab.setAttribute("title", uiText("customerTopup.installAppAria"'
    ) in pwa
    assert pwa.index('fab.setAttribute("title"') < pwa.index('fab.setAttribute("aria-label"') < pwa.index("fab.innerHTML")
    assert 'btn.setAttribute("aria-selected", String(active));' in topup_lane_handler
    assert 'sidebar.setAttribute("aria-label", uiText("chrome.main_navigation", "Điều hướng chính"));' in mount
    assert 'uiText("customerTopup.assistant.label"' in copilot
    assert 'uiText("customerTopup.assistant.openAria"' in copilot

    allowed_sections = "\n".join(
        (nav_map, title, description, billing_nav, entrypoints, request_form, lookup, flow, journey, wallet, pwa, copilot)
    )
    assert PORTAL.count("customerTopup.") == allowed_sections.count("customerTopup.")
    assert "customerTopup." not in section(PORTAL, "function assetVaultLifecyclePanel", "function assetVaultFormFields")
    assert "customerTopup." not in section(PORTAL, "function renderFeatureTracking", "function renderFeatureBotHandoff")


def test_locale_update_toast_uses_newly_confirmed_catalogue_after_hydration() -> None:
    update = section(
        INTEGRATION,
        'if (action === "update-interface-locale") {',
        'if (action === "upgrade-telegram-account") {',
    )
    assert "toast(result.message)" not in update
    assert 'i18n.t("interfaceLocale.updated")' in update
    assert update.index("applyConfirmedProfileInterfaceLocale") < update.index("await hydrate()")
    assert update.index("await hydrate()") < update.index('i18n.t("interfaceLocale.updated")')


def test_product_harmony_comparator_tracks_catalogue_owned_copilot_aria() -> None:
    harmony = (ROOT / "tests/test_product_harmony_ui_contracts.py").read_text(encoding="utf-8")
    assert 'uiText("customerTopup.assistant.openAria"' in harmony
    assert 'aria-label="Mở Trợ Lý AI AAS BOT"' not in harmony
