"""Signed, read-only Community Trust Center for the standalone Web App.

The frozen Telegram Bot is reference material only.  This module exposes a
small Web-owned catalog of official destinations and anti-impersonation
guidance.  It never reads a Bot conversation, imports a bridge, or starts a
provider, wallet, payment, job, asset, webhook, notification, or delivery
operation.
"""

from __future__ import annotations

import os
from types import MappingProxyType
from typing import Any, Mapping
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, Response

from copyfast_auth import _telegram_bot_username, envelope, normalize_interface_locale, require_account


router = APIRouter(prefix="/api/v1/community", tags=["Community Trust Center"])

SNAPSHOT_VERSION = "2026-07-27.1"
LOCALES = frozenset({"vi", "en", "zh"})
CHANNEL_IDS = ("website", "workspace", "telegram_bot", "community", "support")
INTERNAL_ROUTES = MappingProxyType({"workspace": "/dashboard", "support": "/support"})


def _localized(**values: Mapping[str, Any]) -> Mapping[str, Mapping[str, Any]]:
    if set(values) != LOCALES:
        raise RuntimeError("Community Trust Center translations must define exactly vi/en/zh")
    return MappingProxyType({locale: MappingProxyType(dict(value)) for locale, value in values.items()})


CHANNEL_COPY = MappingProxyType(
    {
        "website": _localized(
            vi={"title": "Website TOAN AAS", "summary": "Thông tin sản phẩm, hướng dẫn và điểm vào Workspace chính thức.", "guarded": "Website chính thức chưa được cấu hình an toàn."},
            en={"title": "TOAN AAS website", "summary": "Official product information, guidance and Workspace entry point.", "guarded": "The official website is not safely configured yet."},
            zh={"title": "TOAN AAS 网站", "summary": "官方产品信息、指南和 Workspace 入口。", "guarded": "官方网站尚未完成安全配置。"},
        ),
        "workspace": _localized(
            vi={"title": "TOAN AAS Workspace", "summary": "Mở không gian làm việc đã xác thực của bạn.", "guarded": "Workspace hiện chưa sẵn sàng."},
            en={"title": "TOAN AAS Workspace", "summary": "Open your signed-in workspace.", "guarded": "The Workspace is not ready yet."},
            zh={"title": "TOAN AAS Workspace", "summary": "打开你的已登录工作区。", "guarded": "工作区暂不可用。"},
        ),
        "telegram_bot": _localized(
            vi={"title": "Telegram Bot chính thức", "summary": "Mở Bot đã được máy chủ xác nhận, không tìm qua link lạ.", "guarded": "Bot username công khai chưa hợp lệ."},
            en={"title": "Official Telegram Bot", "summary": "Open the server-verified Bot instead of following an unknown link.", "guarded": "The public Bot username is not valid yet."},
            zh={"title": "官方 Telegram Bot", "summary": "打开由服务器验证的 Bot，不要点击未知链接。", "guarded": "公开 Bot 用户名暂不可用。"},
        ),
        "community": _localized(
            vi={"title": "Cộng đồng chính thức", "summary": "Kênh cộng đồng được cấu hình riêng cho Web App.", "guarded": "Kênh cộng đồng chưa được cấu hình hoặc không hợp lệ."},
            en={"title": "Official community", "summary": "A community channel explicitly configured for the Web App.", "guarded": "The community channel is missing or invalid."},
            zh={"title": "官方社区", "summary": "为 Web App 明确配置的社区频道。", "guarded": "社区频道缺失或无效。"},
        ),
        "support": _localized(
            vi={"title": "Hỗ trợ trong Workspace", "summary": "Gửi yêu cầu có ngữ cảnh và không chứa thông tin nhạy cảm.", "guarded": "Kênh hỗ trợ hiện chưa sẵn sàng."},
            en={"title": "Workspace support", "summary": "Send a contextual request without sensitive information.", "guarded": "The support channel is not ready yet."},
            zh={"title": "Workspace 支持", "summary": "发送包含上下文且不含敏感信息的请求。", "guarded": "支持渠道暂不可用。"},
        ),
    }
)

UI_COPY = _localized(
    vi={
        "kicker": "Kênh chính thức · chỉ đọc",
        "heading": "Luôn bắt đầu từ đúng kênh của TOAN AAS.",
        "body": "Danh sách này chỉ hiển thị các điểm vào đã được Web App kiểm tra. Không dùng link được gửi từ tài khoản lạ để đăng nhập, nạp tiền hoặc chia sẻ thông tin cá nhân.",
        "ready": "Đã xác minh",
        "guarded": "Đang bảo vệ",
        "open": "Mở kênh",
        "open_workspace": "Mở Workspace",
        "safety_title": "Giữ tài khoản an toàn",
        "safety_body": "Nếu một tin nhắn hoặc link khiến bạn thấy bất thường, dừng lại và mở kênh từ danh sách này hoặc gửi ticket trong Workspace.",
        "boundary_title": "Danh mục tin cậy, không phải tác vụ",
        "boundary_body": "Trang này không gọi Bot, bridge, provider, ví Xu, PayOS, job, asset, webhook hoặc delivery. Nó không xác minh danh tính Telegram và không xử lý thanh toán.",
        "loading_title": "Đang kiểm tra kênh chính thức",
        "loading_body": "Portal đang tải danh sách từ phiên đã xác thực; không dùng link cũ trong trình duyệt để thay thế.",
        "failed_title": "Chưa thể xác minh danh sách kênh",
        "failed_body": "Hãy tải lại hoặc dùng Hỗ trợ trong Workspace. Portal không hiển thị link suy đoán.",
        "guarded_title": "Cần đăng nhập để xem kênh đã xác minh",
        "guarded_body": "Danh sách kênh chỉ được tải trong phiên Web đã ký; không có fallback sang lệnh Bot hoặc URL lưu trong trình duyệt.",
    },
    en={
        "kicker": "Official channels · read-only",
        "heading": "Always start from an official TOAN AAS channel.",
        "body": "This directory shows only entry points checked by the Web App. Do not use a link from an unknown account to sign in, top up, or share personal information.",
        "ready": "Verified",
        "guarded": "Protected",
        "open": "Open channel",
        "open_workspace": "Open Workspace",
        "safety_title": "Keep your account safe",
        "safety_body": "If a message or link feels unusual, stop and open a channel from this directory or send a ticket in the Workspace.",
        "boundary_title": "Trust directory, not an action",
        "boundary_body": "This page does not call a Bot, bridge, provider, Xu wallet, PayOS, job, asset, webhook or delivery flow. It does not verify a Telegram identity or process a payment.",
        "loading_title": "Checking official channels",
        "loading_body": "The Portal is loading this directory from the signed session and will not replace it with an old browser link.",
        "failed_title": "The official-channel directory could not be verified",
        "failed_body": "Reload the page or use Workspace Support. The Portal never shows a guessed link.",
        "guarded_title": "Sign in to view verified channels",
        "guarded_body": "The directory loads only in a signed Web session; there is no fallback to Bot commands or browser-stored URLs.",
    },
    zh={
        "kicker": "官方渠道 · 只读",
        "heading": "始终从 TOAN AAS 官方渠道开始。",
        "body": "此目录仅显示经 Web App 核查的入口。不要使用陌生账户发送的链接登录、充值或分享个人信息。",
        "ready": "已验证",
        "guarded": "受保护",
        "open": "打开渠道",
        "open_workspace": "打开 Workspace",
        "safety_title": "保护你的账户",
        "safety_body": "如果消息或链接看起来异常，请停止操作，并从此目录打开渠道或在 Workspace 中提交工单。",
        "boundary_title": "信任目录，不是执行操作",
        "boundary_body": "此页面不会调用 Bot、bridge、provider、Xu 钱包、PayOS、任务、资产、webhook 或交付流程。它不会验证 Telegram 身份或处理付款。",
        "loading_title": "正在核查官方渠道",
        "loading_body": "Portal 正在从已登录会话加载目录，不会用浏览器中的旧链接替代。",
        "failed_title": "无法验证官方渠道目录",
        "failed_body": "请重新加载页面或使用 Workspace 支持。Portal 不会显示猜测的链接。",
        "guarded_title": "登录后查看已验证渠道",
        "guarded_body": "目录仅在已签名的 Web 会话中加载；不会回退到 Bot 命令或浏览器保存的 URL。",
    },
)

SAFETY_CHECKS = _localized(
    vi={"checks": ("Không gửi mật khẩu, OTP, token phiên, API key hoặc mã khôi phục cho bất kỳ ai.", "Không nhập thông tin thẻ hoặc thanh toán qua link lạ, tin nhắn riêng hoặc cuộc gọi.", "Kiểm tra tên miền và kênh từ danh sách này trước khi đăng nhập hoặc nạp Xu.", "Khi nghi ngờ, dừng thao tác và gửi ticket trong Workspace.")},
    en={"checks": ("Never send a password, OTP, session token, API key or recovery code to anyone.", "Never enter card or payment information through an unknown link, direct message or call.", "Check the domain and channel in this directory before signing in or topping up Xu.", "When in doubt, stop and send a ticket in the Workspace.")},
    zh={"checks": ("不要向任何人发送密码、OTP、会话令牌、API 密钥或恢复码。", "不要通过未知链接、私信或电话输入银行卡或支付信息。", "登录或充值 Xu 前，请在此目录核查域名和渠道。", "如有疑问，请停止操作并在 Workspace 中提交工单。")},
)


def _safe_text(value: object, *, limit: int = 360) -> str:
    text = str(value or "").strip()
    if not text or len(text) > limit or any(ord(character) < 32 for character in text):
        raise RuntimeError("Community Trust Center snapshot contains unsafe text")
    return text


def _safe_url(value: object, *, hosts: frozenset[str], require_path: bool = False) -> str:
    raw = str(value or "").strip()
    if not raw or len(raw) > 400 or any(ord(character) < 32 for character in raw):
        return ""
    try:
        parsed = urlsplit(raw)
        port = parsed.port
    except ValueError:
        return ""
    if (
        parsed.scheme != "https"
        or parsed.hostname not in hosts
        or parsed.username is not None
        or parsed.password is not None
        or port is not None
        or parsed.query
        or parsed.fragment
        or (require_path and not parsed.path)
    ):
        return ""
    return raw


def _localized_copy(channel_id: str, locale: str) -> Mapping[str, str]:
    if channel_id not in CHANNEL_IDS:
        raise RuntimeError("Community Trust Center channel is unsupported")
    copy = CHANNEL_COPY[channel_id][locale]
    return {key: _safe_text(value, limit=240) for key, value in copy.items()}


def _ready_external(channel_id: str, locale: str, url: str) -> dict[str, str]:
    copy = _localized_copy(channel_id, locale)
    return {"id": channel_id, "kind": "external", "availability": "ready", "title": copy["title"], "summary": copy["summary"], "url": url}


def _ready_internal(channel_id: str, locale: str) -> dict[str, str]:
    copy = _localized_copy(channel_id, locale)
    route = INTERNAL_ROUTES[channel_id]
    return {"id": channel_id, "kind": "internal", "availability": "ready", "title": copy["title"], "summary": copy["summary"], "route": route}


def _guarded(channel_id: str, locale: str, setting: str) -> dict[str, Any]:
    copy = _localized_copy(channel_id, locale)
    return {"id": channel_id, "kind": "external" if channel_id in {"website", "telegram_bot", "community"} else "internal", "availability": "guarded", "title": copy["title"], "summary": copy["guarded"], "missing_config": [setting]}


def _private_no_store(response: Response) -> None:
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["Pragma"] = "no-cache"
    response.headers["Vary"] = "Cookie"


def trust_center_catalog(locale: object) -> dict[str, Any]:
    """Return a new JSON-safe snapshot using only server configuration."""

    selected_locale = normalize_interface_locale(locale)
    if selected_locale not in LOCALES:
        selected_locale = "vi"
    website_url = _safe_url(
        os.environ.get("WEBAPP_OFFICIAL_SITE_URL", "https://toanaas.vn"),
        hosts=frozenset({"toanaas.vn", "www.toanaas.vn"}),
    )
    community_url = _safe_url(
        os.environ.get("WEBAPP_COMMUNITY_URL", ""),
        hosts=frozenset({"t.me"}),
        require_path=True,
    )
    bot_username = _telegram_bot_username()
    channels = [
        _ready_external("website", selected_locale, website_url) if website_url else _guarded("website", selected_locale, "WEBAPP_OFFICIAL_SITE_URL"),
        _ready_internal("workspace", selected_locale),
        _ready_external("telegram_bot", selected_locale, f"https://t.me/{bot_username}") if bot_username else _guarded("telegram_bot", selected_locale, "BOT_USERNAME"),
        _ready_external("community", selected_locale, community_url) if community_url else _guarded("community", selected_locale, "WEBAPP_COMMUNITY_URL"),
        _ready_internal("support", selected_locale),
    ]
    ui = {key: _safe_text(value) for key, value in UI_COPY[selected_locale].items()}
    checks = [_safe_text(item, limit=260) for item in SAFETY_CHECKS[selected_locale]["checks"]]
    return {
        "snapshot_version": SNAPSHOT_VERSION,
        "locale": selected_locale,
        "ui": ui,
        "channels": channels,
        "safety": {"title": ui["safety_title"], "body": ui["safety_body"], "checks": checks},
        "boundaries": {
            "execution": "web_native_community_trust_center",
            "snapshot_read_only": True,
            "bot_called": False,
            "bridge_called": False,
            "provider_called": False,
            "wallet_mutated": False,
            "payment_started": False,
            "job_created": False,
            "asset_saved": False,
            "notification_sent": False,
        },
    }


@router.get("/trust-center")
def get_trust_center(response: Response, account: dict[str, Any] = Depends(require_account)) -> dict[str, Any]:
    """Serve the signed account's localized, non-executing trust directory."""

    _private_no_store(response)
    return envelope(
        True,
        "Đã tải danh sách kênh chính thức đã xác minh.",
        data=trust_center_catalog(account.get("locale")),
        status_name="completed",
    )
