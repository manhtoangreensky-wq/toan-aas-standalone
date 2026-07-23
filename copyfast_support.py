"""Professional, Web-owned Support Desk for signed TOAN AAS accounts.

This module deliberately improves the useful ticket/feedback workflows from
the frozen Telegram Bot without copying its database or conversation state.
It never reads or writes Bot ticket tables, sends Telegram/email, calls a
provider, changes a payment, wallet/Xu, refund, or job.  Every case, message
and event is private to a signed Web account and every operator write has a
server-side role, CSRF, confirmation, idempotency and audit trail.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json
import re
import uuid
from typing import Any, Callable

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator

from copyfast_auth import _record_audit, _request_id, envelope, require_account, require_csrf
from copyfast_assets import (
    open_verified_private_asset_stream,
    private_asset_attachment_response,
    read_verified_private_asset_bytes,
    seal_verified_private_file,
)
from copyfast_db import asset_vault_enabled, ensure_copyfast_schema, support_desk_enabled, transaction, utc_now


router = APIRouter(prefix="/api/v1/support", tags=["Web Support Desk"])

CASE_CATEGORIES = frozenset({
    "payment_topup", "image_error", "video_error", "document_pdf",
    "package_combo", "refund", "feature_request", "lead_consulting",
    "general_support", "service_consulting", "premium_lead",
    "custom_bot_lead", "other",
})
# The Advisor is intentionally a bounded, read-only preparation aid for the
# existing Web Support Desk.  It has no free-text classifier, AI/provider call
# or Bot compatibility layer.  Each guide returns one *existing* Web case
# category so the browser can offer a deliberate handoff to the normal,
# CSRF/idempotent case composer without creating or changing a case itself.
SUPPORT_ADVISOR_GUIDES: dict[str, dict[str, Any]] = {
    "image_error": {
        "topic": "technical",
        "title": "Kiểm tra thao tác ảnh trước khi gửi yêu cầu",
        "summary": "Ghi nhận bối cảnh hiển thị để đội ngũ Web có đủ thông tin xem lại, nhưng checklist này không tự xác nhận lỗi hay tạo lại ảnh.",
        "checklist": (
            "Xác nhận bạn đang ở đúng Web account và làm mới trang một lần.",
            "Ghi tên khu vực thao tác, thời điểm gần đúng và kết quả đang thấy.",
            "Mô tả điều bạn đã thử; không gửi token, mật khẩu hoặc thông tin thanh toán.",
        ),
        "handoff": "Nếu vẫn cần hỗ trợ, hãy tự mô tả lỗi trong yêu cầu Web. Không có kiểm tra provider hoặc output tự động từ checklist.",
    },
    "video_error": {
        "topic": "technical",
        "title": "Chuẩn bị thông tin về thao tác video",
        "summary": "Checklist chỉ giúp bạn mô tả hiện tượng rõ hơn; nó không kiểm tra tiến trình, trạng thái engine hoặc tạo video thay thế.",
        "checklist": (
            "Kiểm tra đúng workspace và làm mới trang trước khi báo lỗi.",
            "Ghi bước đang thực hiện, thời điểm gần đúng và kết quả hiển thị.",
            "Chỉ nêu ngữ cảnh cần thiết; không gửi secret, mã thanh toán hoặc dữ liệu của người khác.",
        ),
        "handoff": "Bạn tự quyết định gửi ticket Web sau khi xem checklist; hệ thống không tự mở case hoặc cam kết kết quả video.",
    },
    "document_pdf": {
        "topic": "technical",
        "title": "Chuẩn bị thông tin về tài liệu hoặc PDF",
        "summary": "Xác định thao tác và kết quả mong muốn trước khi gửi yêu cầu; checklist không đọc file, không tải file lên và không tạo output.",
        "checklist": (
            "Xác nhận bạn đang mở đúng khu vực tài liệu của signed Web account.",
            "Ghi thao tác, định dạng mong muốn và thời điểm gần đúng của hiện tượng.",
            "Không dán nội dung nhạy cảm, URL private, path máy tính hay thông tin thanh toán.",
        ),
        "handoff": "Nếu cần người hỗ trợ xem lại, hãy mô tả bối cảnh trong ticket Web; việc đọc file chỉ có thể diễn ra trong workflow riêng có quyền phù hợp.",
    },
    "payment_topup": {
        "topic": "billing_review",
        "title": "Chuẩn bị yêu cầu đối soát nạp tiền",
        "summary": "Support Advisor không xác nhận giao dịch, cộng Xu, tạo đơn hoặc đối soát thanh toán. Nó chỉ giúp bạn gửi yêu cầu Web an toàn nếu cần review.",
        "checklist": (
            "Kiểm tra lại trạng thái hiển thị trong account và thời điểm bạn quan sát.",
            "Nêu vấn đề cần được xem xét bằng mô tả ngắn, không đính kèm chứng từ nhạy cảm.",
            "Không gửi bill, TXID, QR, số tài khoản, số thẻ, OTP/CVV hoặc mật khẩu vào Web Support Desk.",
        ),
        "handoff": "Một ticket chỉ ghi nhận yêu cầu review trong Web; nó không chứng minh thanh toán, cộng Xu hay thay đổi ledger.",
    },
    "package_combo": {
        "topic": "billing_review",
        "title": "Chuẩn bị câu hỏi về gói dịch vụ",
        "summary": "Checklist giúp bạn làm rõ gói và nhu cầu cần giải đáp. Nó không tạo đơn, đổi gói, thay giá hay thay đổi quyền sử dụng.",
        "checklist": (
            "Ghi tên gói hoặc màn hình bạn đang xem cùng nhu cầu muốn làm rõ.",
            "Nêu thời điểm gần đúng và kết quả hiển thị trong account hiện tại.",
            "Không gửi mã giao dịch, QR, số tài khoản, số thẻ, OTP/CVV hay thông tin đăng nhập.",
        ),
        "handoff": "Bạn có thể tự gửi ticket Web để nhân sự xem lại; ticket không tự tạo hoặc điều chỉnh giao dịch.",
    },
    "refund": {
        "topic": "billing_review",
        "title": "Chuẩn bị yêu cầu xem xét hoàn tiền",
        "summary": "Checklist không phê duyệt, từ chối hoặc thực hiện hoàn tiền. Nó chỉ giúp bạn mô tả yêu cầu rõ ràng để được xem xét trong luồng Web.",
        "checklist": (
            "Nêu dịch vụ hoặc tình huống cần được xem xét và thời điểm gần đúng.",
            "Mô tả ngắn gọn lý do và kết quả bạn mong muốn được làm rõ.",
            "Không gửi bill, TXID, QR, số tài khoản, số thẻ, OTP/CVV hoặc bất kỳ secret nào.",
        ),
        "handoff": "Ticket Web chỉ là yêu cầu review; không có hoàn tiền, cập nhật wallet/Xu hoặc thông báo ngoài hệ thống tự động.",
    },
    "feature_request": {
        "topic": "product_consulting",
        "title": "Chuẩn bị đề xuất tính năng",
        "summary": "Biến ý tưởng thành yêu cầu có thể đánh giá, không hứa hẹn roadmap, thời điểm phát hành hoặc quyền truy cập mới.",
        "checklist": (
            "Mô tả vấn đề người dùng đang gặp thay vì chỉ nêu tên tính năng.",
            "Nêu kết quả mong muốn và ví dụ sử dụng ngắn gọn.",
            "Không gửi dữ liệu khách hàng, secret hoặc thông tin thanh toán vào mô tả.",
        ),
        "handoff": "Bạn có thể gửi ticket Web để lưu ý kiến; việc tiếp nhận không đồng nghĩa tính năng đã được duyệt hay triển khai.",
    },
    "lead_consulting": {
        "topic": "product_consulting",
        "title": "Chuẩn bị yêu cầu tư vấn",
        "summary": "Gom mục tiêu và bối cảnh để đội ngũ hiểu nhu cầu; checklist không đặt lịch, tạo hợp đồng hoặc cam kết dịch vụ.",
        "checklist": (
            "Nêu mục tiêu, loại nội dung hoặc quy trình bạn muốn tìm hiểu.",
            "Cho biết quy mô hoặc ràng buộc cần cân nhắc ở mức không nhạy cảm.",
            "Không gửi dữ liệu nhận diện, tài liệu mật, secret hoặc thông tin thanh toán.",
        ),
        "handoff": "Ticket Web chỉ ghi nhận nhu cầu tư vấn; không tự gửi email, Telegram hoặc tạo lead ở hệ thống ngoài.",
    },
    "service_consulting": {
        "topic": "product_consulting",
        "title": "Chuẩn bị câu hỏi về dịch vụ",
        "summary": "Làm rõ use case trước khi hỏi để trao đổi hiệu quả hơn; checklist không bật dịch vụ hay xác nhận phạm vi thực hiện.",
        "checklist": (
            "Nêu mục tiêu và loại kết quả bạn muốn tìm hiểu.",
            "Ghi công cụ hoặc khu vực Web liên quan nếu bạn đã xác định được.",
            "Không gửi thông tin đăng nhập, secret, dữ liệu thanh toán hoặc dữ liệu của người khác.",
        ),
        "handoff": "Bạn có thể tự tạo yêu cầu Web để trao đổi; hệ thống không tự kích hoạt dịch vụ hoặc gọi engine bên ngoài.",
    },
    "premium_lead": {
        "topic": "product_consulting",
        "title": "Chuẩn bị nhu cầu gói cao cấp",
        "summary": "Checklist giúp mô tả nhu cầu trước khi trao đổi. Nó không báo giá, tạo gói, thay quyền truy cập hoặc cam kết phạm vi.",
        "checklist": (
            "Nêu mục tiêu sử dụng và quy mô công việc muốn trao đổi.",
            "Ghi các yêu cầu vận hành hoặc hỗ trợ quan trọng ở mức không nhạy cảm.",
            "Không gửi thông tin thanh toán, dữ liệu hợp đồng, secret hoặc thông tin đăng nhập.",
        ),
        "handoff": "Một ticket Web mở đầu cuộc trao đổi; nó không phải báo giá hoặc xác nhận mua gói.",
    },
    "custom_bot_lead": {
        "topic": "product_consulting",
        "title": "Chuẩn bị nhu cầu giải pháp tùy chỉnh",
        "summary": "Ghi rõ bài toán và ràng buộc trước khi liên hệ. Checklist không tạo Bot, kết nối hệ thống hay thay đổi cấu hình hiện hữu.",
        "checklist": (
            "Mô tả quy trình cần hỗ trợ và người dùng dự kiến ở mức tổng quát.",
            "Nêu kết quả cần đạt, ràng buộc kỹ thuật hoặc vận hành không nhạy cảm.",
            "Không gửi API key, token, mật khẩu, dữ liệu khách hàng hoặc thông tin thanh toán.",
        ),
        "handoff": "Bạn có thể gửi yêu cầu Web để được xem xét; hệ thống không tự tạo Bot, kết nối Telegram hoặc triển khai tích hợp.",
    },
    "general_support": {
        "topic": "general",
        "title": "Chuẩn bị yêu cầu hỗ trợ chung",
        "summary": "Một mô tả ngắn, có bối cảnh giúp phân luồng rõ hơn. Checklist không tự phân loại bằng AI hay tạo phản hồi thay nhân sự.",
        "checklist": (
            "Nêu việc bạn đang cố thực hiện và kết quả đang thấy.",
            "Ghi thời điểm gần đúng và bước bạn đã thử nếu có.",
            "Không gửi password, token, OTP/CVV, số thẻ, mã thanh toán hoặc dữ liệu riêng tư của người khác.",
        ),
        "handoff": "Nếu vẫn cần hỗ trợ, bạn chủ động tạo ticket Web với mô tả của mình; hệ thống không tự gửi hoặc tự trả lời thay bạn.",
    },
    "other": {
        "topic": "general",
        "title": "Làm rõ yêu cầu trước khi gửi",
        "summary": "Khi chưa phù hợp nhóm nào, hãy mô tả bối cảnh và mục tiêu theo cách an toàn. Checklist không suy đoán hành động hay kết quả.",
        "checklist": (
            "Viết ngắn gọn điều bạn cần làm rõ và kết quả mong muốn.",
            "Nêu khu vực Web liên quan cùng thời điểm gần đúng nếu có.",
            "Loại bỏ secret, OTP/CVV, dữ liệu thanh toán và thông tin không thuộc quyền chia sẻ của bạn.",
        ),
        "handoff": "Bạn vẫn tự quyết định gửi ticket Web; không có phân loại Bot, tự tạo case hoặc thông báo ra bên ngoài.",
    },
}
SUPPORT_ADVISOR_EXTERNAL_BOUNDARIES = {
    "ticket_auto_create": False,
    "notification": False,
    "payment_or_refund": False,
    "provider_or_job_lookup": False,
    "bot_or_telegram": False,
}
# Consultation Brief is a deliberately closed Web-native catalog distilled
# from the useful *topics* of the frozen Bot support menu.  It is not a Bot
# callback compatibility layer: a selected item can only create an in-memory
# draft which the customer may explicitly copy into the normal Web case form.
# No item carries a price, quote, contract, contact channel or provider action.
CONSULTATION_BRIEF_CATALOG_VERSION = "2026-07-23"
CONSULTATION_BRIEF_BOUNDARIES = {
    "case_auto_create": False,
    "lead_or_crm_write": False,
    "external_notification": False,
    "contact_collection": False,
    "quote_or_contract": False,
    "payment_or_wallet": False,
    "bot_or_telegram": False,
    "provider_job_or_asset": False,
}
CONSULTATION_BRIEF_GROUPS: tuple[dict[str, Any], ...] = (
    {
        "id": "premium",
        "title": "Gói cao cấp",
        "summary": "Làm rõ phạm vi sử dụng và mức hỗ trợ cần trao đổi trước khi bạn tự gửi yêu cầu Web.",
        "services": (
            {
                "id": "web-premium-creator",
                "category": "premium_lead",
                "title": "Cá nhân / Creator",
                "summary": "Tư vấn cách tổ chức công việc sáng tạo cá nhân trong Web App.",
                "prompt": "Nêu loại nội dung và nhịp làm việc bạn muốn tối ưu.",
            },
            {
                "id": "web-premium-shop",
                "category": "premium_lead",
                "title": "Shop / Affiliate",
                "summary": "Làm rõ nhu cầu nội dung, vận hành hoặc báo cáo cho hoạt động bán hàng.",
                "prompt": "Nêu quy trình bán hàng hoặc kênh nội dung cần được trao đổi.",
            },
            {
                "id": "web-premium-business",
                "category": "premium_lead",
                "title": "Doanh nghiệp",
                "summary": "Chuẩn bị bối cảnh đội nhóm và yêu cầu vận hành ở mức không nhạy cảm.",
                "prompt": "Nêu quy mô công việc, vai trò sử dụng và ràng buộc cần cân nhắc.",
            },
            {
                "id": "web-premium-private",
                "category": "premium_lead",
                "title": "Trao đổi riêng về nhu cầu",
                "summary": "Đặt câu hỏi về phạm vi phù hợp mà không tạo báo giá hoặc cam kết dịch vụ.",
                "prompt": "Nêu vấn đề cần làm rõ và tiêu chí bạn muốn dùng để đánh giá.",
            },
        ),
    },
    {
        "id": "custom_bot",
        "title": "Giải pháp tùy chỉnh",
        "summary": "Mô tả bài toán Web ở mức tổng quát; bản nháp không tạo Bot, kết nối hay cấu hình mới.",
        "services": (
            {
                "id": "web-custom-shop",
                "category": "custom_bot_lead",
                "title": "Quy trình cho shop",
                "summary": "Trao đổi về luồng hỗ trợ hoạt động bán hàng hoặc vận hành shop.",
                "prompt": "Nêu các bước thủ công hiện tại và điểm cần được cải thiện.",
            },
            {
                "id": "web-custom-content",
                "category": "custom_bot_lead",
                "title": "Quy trình nội dung",
                "summary": "Làm rõ nhu cầu biên tập, phê duyệt hoặc tổ chức nội dung.",
                "prompt": "Nêu loại nội dung, các bước review và kết quả cần có.",
            },
            {
                "id": "web-custom-support",
                "category": "custom_bot_lead",
                "title": "Quy trình hỗ trợ khách hàng",
                "summary": "Xác định bối cảnh hỗ trợ và thông tin cần tổ chức trong Web.",
                "prompt": "Nêu các nhóm câu hỏi hoặc bước chăm sóc cần được làm rõ.",
            },
            {
                "id": "web-custom-internal",
                "category": "custom_bot_lead",
                "title": "Vận hành nội bộ",
                "summary": "Trao đổi nhu cầu phối hợp, theo dõi hoặc chuẩn hóa công việc nội bộ.",
                "prompt": "Nêu vai trò tham gia, quy trình hiện có và điểm đang bị gián đoạn.",
            },
            {
                "id": "web-custom-custom",
                "category": "custom_bot_lead",
                "title": "Bài toán khác",
                "summary": "Bắt đầu từ vấn đề cụ thể trước khi đánh giá phạm vi phù hợp.",
                "prompt": "Nêu vấn đề cốt lõi và kết quả tối thiểu bạn muốn đạt được.",
            },
        ),
    },
    {
        "id": "service",
        "title": "Tư vấn dịch vụ",
        "summary": "Chọn đúng loại công việc để chuẩn bị câu hỏi rõ ràng, không kích hoạt engine hay tạo output.",
        "services": (
            {
                "id": "web-service-image",
                "category": "service_consulting",
                "title": "Ảnh / thiết kế",
                "summary": "Tìm hiểu loại đầu ra hình ảnh hoặc quy trình thiết kế phù hợp.",
                "prompt": "Nêu loại ảnh, mục đích sử dụng và tiêu chí đầu ra cần làm rõ.",
            },
            {
                "id": "web-service-video",
                "category": "service_consulting",
                "title": "Video",
                "summary": "Làm rõ nhu cầu video, cấu trúc nội dung và cách review trong Web.",
                "prompt": "Nêu mục tiêu video, định dạng dự kiến và các bước bạn muốn trao đổi.",
            },
            {
                "id": "web-service-frame-video",
                "category": "service_consulting",
                "title": "Ảnh thành video",
                "summary": "Chuẩn bị câu hỏi về biến đổi hình ảnh thành chuyển động hoặc storyboard.",
                "prompt": "Nêu loại tư liệu đầu vào và phong cách chuyển động muốn tìm hiểu.",
            },
            {
                "id": "web-service-document",
                "category": "service_consulting",
                "title": "Tài liệu / PDF",
                "summary": "Trao đổi nhu cầu xử lý, tổ chức hoặc xuất tài liệu trong luồng phù hợp.",
                "prompt": "Nêu loại tài liệu và thao tác hoặc kết quả cần được tư vấn.",
            },
            {
                "id": "web-service-voice",
                "category": "service_consulting",
                "title": "Giọng nói / âm thanh",
                "summary": "Làm rõ use case audio, lời đọc hoặc nội dung cần chuẩn bị.",
                "prompt": "Nêu mục đích sử dụng âm thanh và yêu cầu nội dung ở mức tổng quát.",
            },
            {
                "id": "web-service-package",
                "category": "service_consulting",
                "title": "Gói và khả năng sử dụng",
                "summary": "Đặt câu hỏi về khả năng phù hợp, không tạo đơn hoặc thay đổi giá/quyền.",
                "prompt": "Nêu cách bạn dự định sử dụng và điều cần được làm rõ trước khi quyết định.",
            },
        ),
    },
)
CONSULTATION_BRIEF_SERVICES = {
    str(service["id"]): service
    for group in CONSULTATION_BRIEF_GROUPS
    for service in group["services"]
}
CASE_PRIORITIES = frozenset({"low", "normal", "high", "urgent"})
CASE_STATES = frozenset({
    "new", "reviewing", "waiting_user", "waiting_provider",
    "refund_pending", "resolved", "closed",
})
CARE_TEAM_QUEUES = frozenset({
    "general", "technical", "account", "creative", "document", "product",
})
CARE_ASSIGNMENT_FILTERS = frozenset({"all", "mine", "assigned", "unassigned"})
SLA_CLASSES = frozenset({"standard", "priority", "critical"})
SLA_TARGET_HOURS = {"standard": 24, "priority": 8, "critical": 2}
# This is deliberately distinct from the legacy customer-waiting report and
# Operations Autopilot's persisted triage health.  It is only the current,
# Web-native Customer Care first-touch target projected by ``_sla_public``.
CARE_SLA_STATUS_FILTERS = frozenset({
    "all", "unavailable", "pending", "within_target", "breached", "overdue_unacknowledged",
})
ESCALATION_STATES = frozenset({"none", "requested", "acknowledged", "resolved", "cancelled"})
ESCALATION_TRANSITIONS = {
    "none": frozenset({"requested"}),
    "requested": frozenset({"acknowledged", "cancelled"}),
    "acknowledged": frozenset({"resolved", "cancelled"}),
    "resolved": frozenset(),
    "cancelled": frozenset(),
}
VISIBLE_MESSAGE_ROLES = frozenset({"customer", "operator"})
MESSAGE_VISIBILITIES = frozenset({"public", "internal"})
# Customer timelines disclose only customer actions and a public operator
# reply.  Internal notes/triage events remain available to staff in the
# separate admin view, even though the customer can always see the current
# case state itself.
CUSTOMER_VISIBLE_EVENT_ACTIONS = frozenset({
    "case_created", "customer_replied", "customer_close", "customer_reopen",
    "operator_replied_public", "customer_attachment_added",
})
IDEMPOTENCY_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{12,160}$")
SECRET_ASSIGNMENT_PATTERN = re.compile(
    r"\b(?:api[ _-]?(?:key|token)|access[ _-]?token|refresh[ _-]?token|"
    r"token|client[ _-]?secret|secret(?:[ _-]?key)?|password|passphrase|authorization)"
    r"\b\s*(?:[:=]|\bis\b)\s*(?:bearer\s+)?[A-Za-z0-9_./+=:-]{8,}",
    re.IGNORECASE,
)
BEARER_PATTERN = re.compile(r"\bbearer\s+[A-Za-z0-9._~+/=-]{12,}\b", re.IGNORECASE)
KNOWN_SECRET_TOKEN_PATTERN = re.compile(
    r"(?<![A-Za-z0-9_])(?:"
    r"(?:sk|pk|rk)[_-][A-Za-z0-9_-]{12,}|"
    r"gh(?:p|o|u|s|r)_[A-Za-z0-9]{12,}|"
    r"github_pat_[A-Za-z0-9_]{12,}|"
    r"xox(?:b|p|a|r|s)-[A-Za-z0-9-]{12,}|"
    r"AIza[0-9A-Za-z_-]{20,}|"
    r"(?:AKIA|ASIA)[0-9A-Z]{16}|"
    r"eyJ[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}"
    r")(?![A-Za-z0-9_])",
    re.IGNORECASE,
)
VERIFICATION_PATTERN = re.compile(
    r"\b(?:otp|cvv|cvc|pin|mã\s*(?:xác\s*(?:minh|thực)|otp)|"
    r"ma\s*(?:xac\s*(?:minh|thuc)|otp)|verification\s+(?:code|token)|"
    r"one[ -]?time(?:\s+(?:pass(?:word|code)?|code))?)\b",
    re.IGNORECASE,
)
MANUAL_PAYMENT_PATTERN = re.compile(
    r"\b(?:tx(?:id|n)?|transaction\s+(?:hash|id|reference|no\.?|number)|"
    r"mã\s*(?:(?:giao\s*)?(?:dịch|gd)|tham\s*chiếu|thanh\s*toán)|"
    r"ma\s*(?:(?:giao\s*)?(?:dich|gd)|tham\s*chieu|thanh\s*toan)|"
    r"biên\s*lai|bien\s*lai|chứng\s*từ|chung\s*tu|bill|"
    r"số\s*tài\s*khoản|so\s*tai\s*khoan|stk|"
    r"tài\s*khoản\s*(?:ngân\s*hàng|bank)|tai\s*khoan\s*(?:ngan\s*hang|bank)|"
    r"bank\s+account|account\s+(?:number|no|id)|qr\s*(?:code|thanh\s*toán|thanh\s*toan)?)\b",
    re.IGNORECASE,
)
# Card-shaped numbers arrive with copy/paste separators as well as spaces and
# hyphens.  Permit only separators between digits so unrelated numbers from a
# prose sentence cannot be joined into a false candidate.
CARD_CANDIDATE_PATTERN = re.compile(r"(?<![0-9A-Za-z])[0-9](?:[\s./-]*[0-9]){12,18}(?![0-9A-Za-z])")
# A Consultation Brief is intentionally contact-free because the customer is
# already identified by the signed Web session.  Keep these detectors scoped
# to the new, non-persistent composer; existing Support cases retain their
# established content contract and may be reviewed independently.
EMAIL_ADDRESS_PATTERN = re.compile(
    r"(?<![A-Za-z0-9._%+-])[A-Za-z0-9][A-Za-z0-9._%+-]{0,63}@[A-Za-z0-9-]{1,63}(?:\.[A-Za-z0-9-]{1,63})+(?![A-Za-z0-9.-])",
    re.IGNORECASE,
)
PHONE_NUMBER_PATTERN = re.compile(r"(?<!\d)(?:\+?84|0)(?:[\s().-]*\d){8,10}(?!\d)")
CONTACT_LABEL_PATTERN = re.compile(
    r"\b(?:email|e-mail|zalo|telegram|phone|số\s*điện\s*thoại|so\s*dien\s*thoai|sđt|sdt)\s*(?:[:=]|là|la)\s*\S+",
    re.IGNORECASE,
)
TELEGRAM_HANDLE_PATTERN = re.compile(r"(?<![A-Za-z0-9._])@[A-Za-z][A-Za-z0-9_]{4,31}\b")
MAX_ACTIVE_CASES = 100
MAX_MESSAGES_PER_CASE = 500
MAX_SUBJECT = 180
MAX_DETAIL = 4_000
MAX_REPLY = 4_000
MAX_OPERATION_NOTE = 360
MAX_CARE_REASON = 360
STAFF_ACCOUNT_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,128}$")
MAX_SUPPORT_ATTACHMENTS_PER_CASE = 3
MAX_SUPPORT_ATTACHMENT_BYTES = 5 * 1024 * 1024
SUPPORT_ATTACHMENT_PAYMENT_CATEGORIES = frozenset({"payment_topup", "refund", "package_combo"})
SUPPORT_ATTACHMENT_CONTENT_TYPES = {
    (".png", "image/png"),
    (".jpg", "image/jpeg"),
    (".jpeg", "image/jpeg"),
    (".webp", "image/webp"),
    (".txt", "text/plain"),
}


def _require_support_enabled() -> None:
    if not support_desk_enabled():
        raise HTTPException(
            status_code=503,
            detail="Web Support Desk đang tạm dừng để bảo trì. WEBAPP_SUPPORT_DESK_ENABLED chưa được bật.",
        )


def _require_support_evidence_enabled() -> None:
    """Require the existing private Asset Vault boundary for evidence.

    Support Desk deliberately never owns a second upload directory. A case
    can only link a file after the same persistent, private Asset Vault gate
    used by the Web workspace is explicitly enabled.
    """
    if not asset_vault_enabled():
        raise HTTPException(
            status_code=503,
            detail="Đính kèm bằng chứng đang được bảo vệ vì Asset Vault chưa được bật.",
        )


def _uuid(value: str, *, label: str) -> str:
    try:
        return str(uuid.UUID(str(value)))
    except (TypeError, ValueError, AttributeError) as exc:
        raise HTTPException(status_code=422, detail=f"{label} không hợp lệ") from exc


def _idempotency_key(value: str) -> str:
    key = str(value or "").strip()
    if not IDEMPOTENCY_PATTERN.fullmatch(key):
        raise HTTPException(status_code=422, detail="Idempotency key không hợp lệ")
    return key


def _contains_sensitive(value: str) -> bool:
    text = str(value or "")
    if any(pattern.search(text) for pattern in (
        SECRET_ASSIGNMENT_PATTERN,
        BEARER_PATTERN,
        KNOWN_SECRET_TOKEN_PATTERN,
        VERIFICATION_PATTERN,
    )):
        return True
    # A support narrative never needs a card-shaped 13–19 digit sequence.
    # Reject it before deciding whether it happens to pass a Luhn check; that
    # avoids retaining a mistyped or partial card number in a private ticket.
    return bool(CARD_CANDIDATE_PATTERN.search(text))


def _safe_line(value: Any, *, label: str, minimum: int, maximum: int, allow_empty: bool = False) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if "\x00" in text or (not text and not allow_empty) or len(text) < minimum or len(text) > maximum:
        if allow_empty:
            raise ValueError(f"{label} tối đa {maximum} ký tự hợp lệ")
        raise ValueError(f"{label} cần từ {minimum} đến {maximum} ký tự hợp lệ")
    if text and _contains_sensitive(text):
        raise ValueError(f"{label} không nhận secret, token, OTP/CVV hoặc số thẻ")
    if text and MANUAL_PAYMENT_PATTERN.search(text):
        raise ValueError("Web Support Desk không nhận bill, TXID, số tài khoản hoặc QR thanh toán")
    return text


def _safe_text(value: Any, *, label: str, minimum: int, maximum: int, allow_empty: bool = False) -> str:
    text = str(value or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    if "\x00" in text or (not text and not allow_empty) or len(text) < minimum or len(text) > maximum:
        if allow_empty:
            raise ValueError(f"{label} tối đa {maximum} ký tự hợp lệ")
        raise ValueError(f"{label} cần từ {minimum} đến {maximum} ký tự hợp lệ")
    if text and _contains_sensitive(text):
        raise ValueError(f"{label} không nhận secret, token, OTP/CVV hoặc số thẻ")
    if text and MANUAL_PAYMENT_PATTERN.search(text):
        raise ValueError("Web Support Desk không nhận bill, TXID, số tài khoản hoặc QR thanh toán")
    return text


def _contains_consultation_contact(value: str) -> bool:
    text = str(value or "")
    return bool(
        EMAIL_ADDRESS_PATTERN.search(text)
        or PHONE_NUMBER_PATTERN.search(text)
        or CONTACT_LABEL_PATTERN.search(text)
        or TELEGRAM_HANDLE_PATTERN.search(text)
    )


def _consultation_line(value: Any, *, label: str, minimum: int, maximum: int) -> str:
    text = _safe_line(value, label=label, minimum=minimum, maximum=maximum)
    if _contains_consultation_contact(text):
        raise ValueError(
            "Consultation Brief dùng signed Web account; không nhập email, số điện thoại, Zalo hoặc Telegram vào nội dung"
        )
    return text


def _consultation_text(value: Any, *, label: str, minimum: int, maximum: int) -> str:
    text = _safe_text(value, label=label, minimum=minimum, maximum=maximum)
    if _contains_consultation_contact(text):
        raise ValueError(
            "Consultation Brief dùng signed Web account; không nhập email, số điện thoại, Zalo hoặc Telegram vào nội dung"
        )
    return text


def _validated_line(value: Any, *, label: str, minimum: int, maximum: int, allow_empty: bool = False) -> str:
    try:
        return _safe_line(value, label=label, minimum=minimum, maximum=maximum, allow_empty=allow_empty)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def _category(value: Any) -> str:
    normalized = str(value or "general_support").strip().lower()
    if normalized not in CASE_CATEGORIES:
        raise ValueError("Nhóm yêu cầu hỗ trợ không hợp lệ")
    return normalized


def _consultation_service_id(value: Any) -> str:
    normalized = str(value or "").strip()
    if normalized not in CONSULTATION_BRIEF_SERVICES:
        raise ValueError("Loại tư vấn Web không hợp lệ")
    return normalized


def _consultation_service_public(service: dict[str, Any]) -> dict[str, str]:
    """Project one server-owned catalog item without exposing mutable internals."""

    return {
        "id": str(service["id"]),
        "category": str(service["category"]),
        "title": str(service["title"]),
        "summary": str(service["summary"]),
        "prompt": str(service["prompt"]),
    }


def _consultation_catalog_public() -> list[dict[str, Any]]:
    return [
        {
            "id": str(group["id"]),
            "title": str(group["title"]),
            "summary": str(group["summary"]),
            "services": [_consultation_service_public(service) for service in group["services"]],
        }
        for group in CONSULTATION_BRIEF_GROUPS
    ]


def _priority(value: Any) -> str:
    normalized = str(value or "normal").strip().lower()
    if normalized not in CASE_PRIORITIES:
        raise ValueError("Mức ưu tiên không hợp lệ")
    return normalized


def _state(value: Any) -> str:
    normalized = str(value or "").strip().lower()
    if normalized not in CASE_STATES:
        raise ValueError("Trạng thái hỗ trợ không hợp lệ")
    return normalized


def _team_queue(value: Any) -> str:
    normalized = str(value or "general").strip().lower()
    if normalized not in CARE_TEAM_QUEUES:
        raise ValueError("Hàng đợi Customer Care không hợp lệ")
    return normalized


def _sla_class(value: Any) -> str:
    normalized = str(value or "standard").strip().lower()
    if normalized not in SLA_CLASSES:
        raise ValueError("Phân loại SLA nội bộ không hợp lệ")
    return normalized


def _escalation_state(value: Any) -> str:
    normalized = str(value or "").strip().lower()
    if normalized not in ESCALATION_STATES or normalized == "none":
        raise ValueError("Trạng thái escalation không hợp lệ")
    return normalized


def _staff_account_id(value: Any) -> str | None:
    normalized = str(value or "").strip()
    if not normalized:
        return None
    if not STAFF_ACCOUNT_ID_PATTERN.fullmatch(normalized):
        raise ValueError("Mã nhân sự Customer Care không hợp lệ")
    return normalized


def _visibility(value: Any) -> str:
    normalized = str(value or "public").strip().lower()
    if normalized not in MESSAGE_VISIBILITIES:
        raise ValueError("Phạm vi phản hồi không hợp lệ")
    return normalized


def _fingerprint(payload: dict[str, Any]) -> str:
    material = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(material).hexdigest()


def _content_hash(value: str) -> str:
    return hashlib.sha256(str(value).encode("utf-8")).hexdigest()


def _idempotent(scope: str, key: str, request_fingerprint: str, operation: Callable[[Any], dict[str, Any]]) -> dict[str, Any]:
    ensure_copyfast_schema()
    with transaction() as conn:
        existing = conn.execute(
            "SELECT response_json, request_fingerprint FROM web_idempotency WHERE scope=? AND key=?",
            (scope, key),
        ).fetchone()
        if existing:
            stored = str(existing[1] or "")
            if not stored or not hmac.compare_digest(stored, request_fingerprint):
                raise HTTPException(status_code=409, detail="Idempotency key đã được dùng cho yêu cầu khác")
            try:
                response = json.loads(str(existing[0]))
            except (TypeError, ValueError, json.JSONDecodeError) as exc:
                raise HTTPException(status_code=409, detail="Bản ghi idempotency Support Desk không hợp lệ") from exc
            if isinstance(response, dict):
                return response
            raise HTTPException(status_code=409, detail="Bản ghi idempotency Support Desk không hợp lệ")
        response = operation(conn)
        conn.execute(
            """INSERT INTO web_idempotency (scope, key, response_json, request_fingerprint, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (scope, key, json.dumps(response, ensure_ascii=False, separators=(",", ":")), request_fingerprint, utc_now()),
        )
    return response


def _event(conn: Any, *, case_id: str, account_id: str, actor_account_id: str | None, action: str, state: str) -> None:
    conn.execute(
        """INSERT INTO web_support_events (id, case_id, account_id, actor_account_id, action, state, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (str(uuid.uuid4()), case_id, account_id, actor_account_id or None, action, state, utc_now()),
    )


def _state_timestamps(current: tuple[Any, ...], next_state: str, now: str) -> tuple[str | None, str | None]:
    """Return truthful resolved/closed timestamps for a Support transition."""
    current_state = str(current[6])
    if next_state == "resolved":
        # A same-state internal note/priority change must not rewrite the
        # original resolution moment.  A real transition into `resolved`
        # receives the current timestamp instead.
        resolved_at = str(current[11]) if current_state == "resolved" and current[11] else now
        return resolved_at, None
    if next_state == "closed":
        # Closing a previously resolved case preserves the resolution moment;
        # closing an unresolved case never manufactures one. Repeating a
        # no-op close leaves the closed moment untouched.
        closed_at = str(current[12]) if current_state == "closed" and current[12] else now
        return (str(current[11]) if current[11] else None), closed_at
    # Any active/review/pending state is not resolved or closed.  This also
    # clears stale timestamps when staff/customer reopens a prior case.
    return None, None


def _case_not_found() -> dict[str, Any]:
    return envelope(False, "Không tìm thấy yêu cầu thuộc Web account hiện tại.", status_name="guarded", error_code="WEB_SUPPORT_CASE_NOT_FOUND")


def _case_row(conn: Any, *, case_id: str, account_id: str | None = None) -> tuple[Any, ...] | None:
    clauses = ["c.id=?"]
    params: list[Any] = [case_id]
    if account_id:
        clauses.append("c.account_id=?")
        params.append(account_id)
    row = conn.execute(
        f"""SELECT c.id, c.account_id, c.category, c.priority, c.subject, c.initial_detail, c.state, c.revision,
                   c.created_at, c.updated_at, c.last_public_message_at, c.resolved_at, c.closed_at,
                   a.display_name, a.email,
                   COALESCE(ctrl.team_queue, 'general'), ctrl.assigned_account_id,
                   assignee.display_name, COALESCE(ctrl.sla_class, 'standard'),
                   COALESCE(ctrl.escalation_state, 'none'), COALESCE(ctrl.escalation_reason, ''),
                   ctrl.escalation_requested_at, ctrl.escalation_acknowledged_at,
                   ctrl.escalation_resolved_at, ctrl.first_staff_touched_at
              FROM web_support_cases c
              JOIN web_accounts a ON a.id=c.account_id
              LEFT JOIN web_support_case_controls ctrl ON ctrl.case_id=c.id
              LEFT JOIN web_accounts assignee ON assignee.id=ctrl.assigned_account_id
              WHERE {' AND '.join(clauses)}""",
        tuple(params),
    ).fetchone()
    return tuple(row) if row else None


def _case_control(conn: Any, *, case_id: str) -> tuple[Any, ...] | None:
    row = conn.execute(
        """SELECT team_queue, assigned_account_id, sla_class, first_staff_touched_at,
                  escalation_state, escalation_reason, escalation_requested_at,
                  escalation_acknowledged_at, escalation_resolved_at, escalation_actor_account_id,
                  updated_at
             FROM web_support_case_controls WHERE case_id=?""",
        (case_id,),
    ).fetchone()
    return tuple(row) if row else None


def _ensure_case_control(conn: Any, *, case_id: str, now: str) -> None:
    """Create metadata lazily for legacy cases without changing case history."""
    conn.execute(
        """INSERT OR IGNORE INTO web_support_case_controls
           (case_id, team_queue, assigned_account_id, sla_class, first_staff_touched_at,
            escalation_state, escalation_reason, escalation_requested_at,
            escalation_acknowledged_at, escalation_resolved_at, escalation_actor_account_id, updated_at)
           VALUES (?, 'general', NULL, 'standard', NULL, 'none', '', NULL, NULL, NULL, NULL, ?)""",
        (case_id, now),
    )


def _care_event(
    conn: Any,
    *,
    case_id: str,
    account_id: str,
    actor_account_id: str,
    kind: str,
    action: str,
    previous_value: str = "",
    next_value: str = "",
    reason: str = "",
) -> None:
    """Persist staff-only metadata history, never a customer-visible event."""
    conn.execute(
        """INSERT INTO web_support_case_control_events
           (id, case_id, account_id, actor_account_id, kind, action, previous_value, next_value, reason, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            str(uuid.uuid4()), case_id, account_id, actor_account_id, kind, action,
            previous_value, next_value, reason, utc_now(),
        ),
    )


def _excerpt(value: str, length: int = 200) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text[:length] + ("…" if len(text) > length else "")


def _mask_email(value: str) -> str:
    email = str(value or "").strip()
    if "@" not in email:
        return ""
    local, domain = email.split("@", 1)
    if not local:
        return f"***@{domain}"
    return f"{local[:1]}***@{domain}"


def _as_utc(value: Any) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value or "").replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _sla_public(row: tuple[Any, ...]) -> dict[str, Any]:
    """Describe an internal triage target without promising customer delivery."""
    classification = str(row[18] or "standard")
    target_hours = SLA_TARGET_HOURS.get(classification, SLA_TARGET_HOURS["standard"])
    started_at = str(row[8] or "")
    first_touch_at = str(row[24]) if row[24] else None
    created = _as_utc(started_at)
    first_touch = _as_utc(first_touch_at)
    due_at = None
    status = "unavailable"
    if created:
        due = created + timedelta(hours=target_hours)
        due_at = due.isoformat(timespec="seconds")
        if first_touch:
            status = "within_target" if first_touch <= due else "breached"
        else:
            status = "overdue_unacknowledged" if datetime.now(timezone.utc) > due else "pending"
    return {
        "class": classification,
        "target_hours": target_hours,
        "starts_at": started_at,
        "due_at": due_at,
        "first_staff_touch_at": first_touch_at,
        "status": status,
        "scope": "internal_triage_only",
    }


def _care_sla_status_sql(*, now: str) -> tuple[str, tuple[str, ...]]:
    """Return the fixed SQL projection matching ``_sla_public`` statuses.

    Customer Care list filtering must happen before the bounded list query's
    ``LIMIT``/``OFFSET``.  Recomputing a page in the browser or post-filtering
    a page would silently hide matching cases.  SQLite ``julianday`` keeps the
    calculation server-side and treats malformed dates as NULL, which matches
    the fail-closed ``unavailable``/no-first-touch behavior of ``_as_utc``.

    The expression is intentionally local to this Web Support Desk table. It
    does not join the separate customer-waiting report, Operations Autopilot,
    Bot, provider, payment, wallet or job state.
    """
    target_hours = """
        CASE COALESCE(ctrl.sla_class, 'standard')
            WHEN 'critical' THEN 2.0
            WHEN 'priority' THEN 8.0
            ELSE 24.0
        END
    """
    return (
        f"""
        CASE
            WHEN julianday(c.created_at) IS NULL THEN 'unavailable'
            WHEN julianday(ctrl.first_staff_touched_at) IS NOT NULL THEN
                CASE
                    WHEN julianday(ctrl.first_staff_touched_at)
                         <= julianday(c.created_at) + (({target_hours}) / 24.0)
                    THEN 'within_target'
                    ELSE 'breached'
                END
            WHEN julianday(?) > julianday(c.created_at) + (({target_hours}) / 24.0)
            THEN 'overdue_unacknowledged'
            ELSE 'pending'
        END
        """,
        (now,),
    )


def _care_public(
    row: tuple[Any, ...], *, include_reason: bool, include_assignee_id: bool = False,
) -> dict[str, Any]:
    """Return the minimum Customer Care projection for the current surface.

    A staff-list item only needs to name the assignee.  The internal account
    identifier is needed exclusively by the manager's single-case triage
    form, so it must not be replicated across every operator list response.
    """
    assigned_account_id = str(row[16] or "")
    assignee = None
    if assigned_account_id:
        assignee = {"display_name": str(row[17] or "Customer Care")}
        if include_assignee_id:
            assignee["id"] = assigned_account_id
    escalation = {
        "state": str(row[19] or "none"),
        "requested_at": str(row[21]) if row[21] else None,
        "acknowledged_at": str(row[22]) if row[22] else None,
        "resolved_at": str(row[23]) if row[23] else None,
        "delivery": "internal_metadata_only",
    }
    if include_reason:
        escalation["reason"] = str(row[20] or "")
    return {
        "team_queue": str(row[15] or "general"),
        "assignee": assignee,
        "sla": _sla_public(row),
        "escalation": escalation,
    }


def _care_event_public(row: tuple[Any, ...]) -> dict[str, Any]:
    return {
        "id": str(row[0]),
        "kind": str(row[1]),
        "action": str(row[2]),
        "previous_value": str(row[3] or ""),
        "next_value": str(row[4] or ""),
        "reason": str(row[5] or ""),
        "created_at": str(row[6]),
        "actor_display_name": str(row[7] or "Customer Care"),
    }


def _case_public(
    row: tuple[Any, ...], *, include_detail: bool = False, admin: bool = False,
    include_assignee_id: bool = False,
) -> dict[str, Any]:
    result = {
        "id": str(row[0]),
        "category": str(row[2]),
        "priority": str(row[3]),
        "subject": str(row[4]),
        "state": str(row[6]),
        "revision": int(row[7]),
        "created_at": str(row[8]),
        "updated_at": str(row[9]),
        "last_public_message_at": str(row[10]),
        "resolved_at": str(row[11]) if row[11] else None,
        "closed_at": str(row[12]) if row[12] else None,
        "excerpt": _excerpt(str(row[5])),
    }
    if include_detail:
        result["detail"] = str(row[5])
    if admin:
        result["customer"] = {"display_name": str(row[13] or "Khách hàng"), "email_masked": _mask_email(str(row[14] or ""))}
        # Only the manager's case-specific triage form needs this ID to render
        # its selected roster value. Lists, mutation receipts and operator
        # detail views never need it.
        result["care"] = _care_public(
            row,
            include_reason=include_detail,
            include_assignee_id=include_assignee_id,
        )
    return result


def _event_public(row: tuple[Any, ...]) -> dict[str, Any]:
    return {"id": str(row[0]), "action": str(row[1]), "state": str(row[2]), "created_at": str(row[3])}


def _message_public(row: tuple[Any, ...], *, admin: bool) -> dict[str, Any]:
    result = {
        "id": str(row[0]),
        "author_role": str(row[1]),
        "visibility": str(row[2]),
        "body": str(row[3]),
        "created_at": str(row[4]),
    }
    if admin:
        result["author_display_name"] = str(row[5] or "")
    return result


def _staff_role(account: dict) -> str:
    role = str(account.get("role") or "").strip().lower()
    # `role` is read from the server-side signed-session account record. It
    # never accepts a browser-supplied admin ID, body field or an email/env
    # allowlist: password registration does not itself prove email ownership.
    # Support roles must be provisioned directly in the protected Web account
    # store by an approved administrator/deployment process.
    if role in {"admin", "support_manager"}:
        return "manager"
    if role == "support_operator":
        return "operator"
    return ""


def _require_staff(account: dict) -> str:
    role = _staff_role(account)
    if not role:
        raise HTTPException(status_code=403, detail="Quyền Support Desk chưa được cấp cho signed Web account này")
    return role


def _require_support_manager(account: dict) -> str:
    """Require the protected, server-side Customer Care manager role."""
    role = _require_staff(account)
    if role != "manager":
        raise HTTPException(status_code=403, detail="Chỉ Customer Care manager được thay đổi phân công hoặc SLA")
    return role


def require_support_staff(account: dict) -> str:
    """Public HTML/API guard for the Web-owned support operator surface.

    This intentionally does not ask the Bot core for a Telegram role.  Staff
    access is derived only from the signed Web account's server-side role or
    a protected, server-side role value, keeping the Support Desk independent
    while preserving the stricter canonical guard for all other Admin ERP
    routes. Email strings and browser inputs can never grant this role.
    """
    return _require_staff(account)


class SupportRequestModel(BaseModel):
    """Strict request envelope: ignored browser fields are never a feature."""
    model_config = ConfigDict(extra="forbid")


class CaseCreateRequest(SupportRequestModel):
    category: str = Field(default="general_support", max_length=48)
    priority: str = Field(default="normal", max_length=16)
    subject: str = Field(min_length=3, max_length=MAX_SUBJECT)
    detail: str = Field(min_length=3, max_length=MAX_DETAIL)
    idempotency_key: str = Field(min_length=12, max_length=160)

    @field_validator("category")
    @classmethod
    def validate_category(cls, value: str) -> str:
        return _category(value)

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, value: str) -> str:
        return _priority(value)

    @field_validator("subject")
    @classmethod
    def validate_subject(cls, value: str) -> str:
        return _safe_line(value, label="Chủ đề", minimum=3, maximum=MAX_SUBJECT)

    @field_validator("detail")
    @classmethod
    def validate_detail(cls, value: str) -> str:
        return _safe_text(value, label="Nội dung", minimum=3, maximum=MAX_DETAIL)


class ConsultationBriefComposeRequest(SupportRequestModel):
    """Validated input for a non-persistent customer-side consultation draft."""

    service_id: str = Field(min_length=3, max_length=64)
    goal: str = Field(min_length=3, max_length=600)
    current_context: str = Field(min_length=3, max_length=1_000)
    requested_outcome: str = Field(min_length=3, max_length=1_000)

    @field_validator("service_id")
    @classmethod
    def validate_service_id(cls, value: str) -> str:
        return _consultation_service_id(value)

    @field_validator("goal")
    @classmethod
    def validate_goal(cls, value: str) -> str:
        return _consultation_line(value, label="Mục tiêu", minimum=3, maximum=600)

    @field_validator("current_context")
    @classmethod
    def validate_current_context(cls, value: str) -> str:
        return _consultation_text(value, label="Bối cảnh hiện tại", minimum=3, maximum=1_000)

    @field_validator("requested_outcome")
    @classmethod
    def validate_requested_outcome(cls, value: str) -> str:
        return _consultation_text(value, label="Kết quả cần tư vấn", minimum=3, maximum=1_000)


class CaseReplyRequest(SupportRequestModel):
    body: str = Field(min_length=1, max_length=MAX_REPLY)
    expected_revision: int = Field(ge=1, le=1_000_000)
    idempotency_key: str = Field(min_length=12, max_length=160)

    @field_validator("body")
    @classmethod
    def validate_body(cls, value: str) -> str:
        return _safe_text(value, label="Phản hồi", minimum=1, maximum=MAX_REPLY)


class CaseAttachmentRequest(SupportRequestModel):
    """Link one existing Asset Vault item as private Support evidence.

    There is intentionally no ``UploadFile`` or arbitrary filename/path in
    this model.  The browser can only choose a server-listed private asset
    already owned by the signed account.
    """

    asset_id: str = Field(min_length=36, max_length=36)
    expected_revision: int = Field(ge=1, le=1_000_000)
    idempotency_key: str = Field(min_length=12, max_length=160)
    customer_redaction_confirmed: bool = False

    @field_validator("asset_id")
    @classmethod
    def validate_asset_id(cls, value: str) -> str:
        try:
            return str(uuid.UUID(str(value)))
        except (TypeError, ValueError, AttributeError) as exc:
            raise ValueError("Mã Asset Vault không hợp lệ") from exc


class CaseTransitionRequest(SupportRequestModel):
    expected_revision: int = Field(ge=1, le=1_000_000)
    idempotency_key: str = Field(min_length=12, max_length=160)
    confirm: bool = False


class AdminReplyRequest(CaseReplyRequest):
    visibility: str = Field(default="public", max_length=16)
    next_state: str = Field(default="", max_length=32)
    confirm: bool = False

    @field_validator("visibility")
    @classmethod
    def validate_visibility(cls, value: str) -> str:
        return _visibility(value)

    @field_validator("next_state")
    @classmethod
    def validate_next_state(cls, value: str) -> str:
        return _state(value) if str(value or "").strip() else ""


class AdminUpdateRequest(SupportRequestModel):
    expected_revision: int = Field(ge=1, le=1_000_000)
    state: str = Field(max_length=32)
    priority: str = Field(max_length=16)
    operation_note: str = Field(min_length=3, max_length=MAX_OPERATION_NOTE)
    idempotency_key: str = Field(min_length=12, max_length=160)
    confirm: bool = False

    @field_validator("state")
    @classmethod
    def validate_state(cls, value: str) -> str:
        return _state(value)

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, value: str) -> str:
        return _priority(value)

    @field_validator("operation_note")
    @classmethod
    def validate_note(cls, value: str) -> str:
        return _safe_text(value, label="Lý do thao tác", minimum=3, maximum=MAX_OPERATION_NOTE)


class AdminCareTriageRequest(SupportRequestModel):
    """Manager-only internal routing; it never sends a customer notification."""

    team_queue: str = Field(max_length=32)
    assigned_account_id: str | None = Field(default=None, max_length=128)
    sla_class: str = Field(max_length=16)
    operation_note: str = Field(min_length=3, max_length=MAX_CARE_REASON)
    expected_revision: int = Field(ge=1, le=1_000_000)
    idempotency_key: str = Field(min_length=12, max_length=160)
    confirm: bool = False

    @field_validator("team_queue")
    @classmethod
    def validate_team_queue(cls, value: str) -> str:
        return _team_queue(value)

    @field_validator("assigned_account_id")
    @classmethod
    def validate_assigned_account_id(cls, value: str | None) -> str | None:
        return _staff_account_id(value)

    @field_validator("sla_class")
    @classmethod
    def validate_sla_class(cls, value: str) -> str:
        return _sla_class(value)

    @field_validator("operation_note")
    @classmethod
    def validate_operation_note(cls, value: str) -> str:
        return _safe_text(value, label="Ghi chú phân công", minimum=3, maximum=MAX_CARE_REASON)


class AdminCareEscalationRequest(SupportRequestModel):
    """Controlled internal escalation lifecycle, not an external escalation."""

    escalation_state: str = Field(max_length=24)
    reason: str = Field(min_length=3, max_length=MAX_CARE_REASON)
    expected_revision: int = Field(ge=1, le=1_000_000)
    idempotency_key: str = Field(min_length=12, max_length=160)
    confirm: bool = False

    @field_validator("escalation_state")
    @classmethod
    def validate_escalation_state(cls, value: str) -> str:
        return _escalation_state(value)

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, value: str) -> str:
        return _safe_text(value, label="Lý do escalation", minimum=3, maximum=MAX_CARE_REASON)


@router.get("/summary")
async def support_summary(account: dict = Depends(require_account)):
    """Return only owner-scoped counters; never claim an external notification."""
    _require_support_enabled()
    ensure_copyfast_schema()
    account_id = str(account["id"])
    with transaction() as conn:
        rows = conn.execute(
            "SELECT state, COUNT(*) FROM web_support_cases WHERE account_id=? GROUP BY state",
            (account_id,),
        ).fetchall()
    states = {state: 0 for state in sorted(CASE_STATES)}
    for state, count in rows:
        if str(state) in states:
            states[str(state)] = int(count)
    active = sum(states[state] for state in ("new", "reviewing", "waiting_user", "waiting_provider", "refund_pending"))
    return envelope(
        True,
        "Tổng quan Web Support Desk của account hiện tại.",
        data={"states": states, "active": active, "delivery": "web_view_only"},
        status_name="read_only",
    )


@router.get("/advisor")
async def support_advisor(category: str = "general_support", account: dict = Depends(require_account)):
    """Return one bounded, Web-only support preparation checklist.

    The endpoint deliberately owns neither a support case nor a classifier.
    It does not query a Bot record, job, provider, payment, wallet/Xu or
    refund ledger.  A user must explicitly submit the existing case composer
    after reading the checklist.
    """
    _require_support_enabled()
    try:
        normalized_category = _category(category)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    guide = SUPPORT_ADVISOR_GUIDES.get(normalized_category)
    if not guide:
        # Keep the endpoint closed even if a future case category is added
        # without a deliberately reviewed self-service guide.
        raise HTTPException(status_code=503, detail="Checklist hỗ trợ Web chưa sẵn sàng cho nhóm này.")
    return envelope(
        True,
        "Checklist tự hỗ trợ chỉ để chuẩn bị yêu cầu Web; bạn vẫn tự quyết định có gửi ticket hay không.",
        data={
            "guide": {
                "category": normalized_category,
                "topic": str(guide["topic"]),
                "title": str(guide["title"]),
                "summary": str(guide["summary"]),
                "checklist": list(guide["checklist"]),
                "handoff": str(guide["handoff"]),
                "boundaries": dict(SUPPORT_ADVISOR_EXTERNAL_BOUNDARIES),
            },
            "delivery": "web_view_only",
            "automation": "none",
        },
        status_name="read_only",
    )


@router.get("/consultation-brief/catalog")
async def consultation_brief_catalog(_account: dict = Depends(require_account)):
    """Return the closed Web consultation catalog without creating a record.

    The catalog is intentionally account-gated, but it is not personalized,
    does not read a Bot conversation and does not start a CRM, quote, payment
    or provider flow.  The browser treats every field as untrusted again when
    it renders or selects an item.
    """

    _require_support_enabled()
    return envelope(
        True,
        "Chọn một nhu cầu để tạo bản nháp tư vấn trong Web; chưa có yêu cầu nào được tạo.",
        data={
            "catalog_version": CONSULTATION_BRIEF_CATALOG_VERSION,
            "groups": _consultation_catalog_public(),
            "boundaries": dict(CONSULTATION_BRIEF_BOUNDARIES),
            "delivery": "web_view_only",
            "persistence": "none",
            "automation": "none",
        },
        status_name="read_only",
    )


@router.post("/consultation-brief/compose")
async def compose_consultation_brief(
    payload: ConsultationBriefComposeRequest,
    _account: dict = Depends(require_csrf),
):
    """Produce one deterministic, non-persistent consultation draft.

    This endpoint does not call ``ensure_copyfast_schema`` or ``transaction``
    on purpose.  A customer must explicitly copy this returned draft into the
    existing, CSRF/idempotent case form and submit that form separately before
    any Support Desk record can exist.
    """

    _require_support_enabled()
    service = CONSULTATION_BRIEF_SERVICES[payload.service_id]
    selection = _consultation_service_public(service)
    subject = _safe_line(
        f"Tư vấn: {selection['title']}",
        label="Chủ đề bản nháp",
        minimum=3,
        maximum=MAX_SUBJECT,
    )
    detail = _safe_text(
        "\n".join((
            f"Nhu cầu đã chọn: {selection['title']}",
            f"Mục tiêu: {payload.goal}",
            f"Bối cảnh hiện tại: {payload.current_context}",
            f"Kết quả cần tư vấn: {payload.requested_outcome}",
            "",
            "Ghi chú: Đây là bản nháp do khách tự xác nhận trong Web; không phải báo giá, hợp đồng, lead, case hoặc cam kết xử lý.",
        )),
        label="Nội dung bản nháp",
        minimum=3,
        maximum=MAX_DETAIL,
    )
    return envelope(
        True,
        "Đã tạo bản nháp trong bộ nhớ Web. Bạn tự quyết định có đưa nó vào form yêu cầu hay không.",
        data={
            "catalog_version": CONSULTATION_BRIEF_CATALOG_VERSION,
            "selection": selection,
            "draft": {
                "category": selection["category"],
                "priority": "normal",
                "subject": subject,
                "detail": detail,
            },
            "boundaries": dict(CONSULTATION_BRIEF_BOUNDARIES),
            "case_created": False,
            "input_persisted": False,
            "delivery": "web_view_only",
            "persistence": "none",
            "automation": "none",
        },
        status_name="draft",
    )


@router.get("/cases")
async def list_cases(
    limit: int = 30,
    offset: int = 0,
    state: str = "all",
    category: str = "",
    q: str = "",
    account: dict = Depends(require_account),
):
    """List private Web cases without falling back to Bot ticket history."""
    _require_support_enabled()
    bounded_limit = max(1, min(int(limit), 100))
    if int(offset) < 0 or int(offset) > 10_000:
        raise HTTPException(status_code=422, detail="Offset danh sách không hợp lệ")
    bounded_offset = int(offset)
    state_filter = str(state or "all").strip().lower()
    if state_filter not in {*CASE_STATES, "all"}:
        raise HTTPException(status_code=422, detail="Bộ lọc trạng thái không hợp lệ")
    category_filter = str(category or "").strip().lower()
    if category_filter and category_filter not in CASE_CATEGORIES:
        raise HTTPException(status_code=422, detail="Bộ lọc nhóm yêu cầu không hợp lệ")
    query = _validated_line(q, label="Từ khóa tìm kiếm", minimum=0, maximum=80, allow_empty=True)
    account_id = str(account["id"])
    clauses = ["c.account_id=?"]
    params: list[Any] = [account_id]
    if state_filter != "all":
        clauses.append("c.state=?")
        params.append(state_filter)
    if category_filter:
        clauses.append("c.category=?")
        params.append(category_filter)
    if query:
        escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        clauses.append("(c.subject LIKE ? ESCAPE '\\' OR c.initial_detail LIKE ? ESCAPE '\\')")
        params.extend([f"%{escaped}%", f"%{escaped}%"])
    ensure_copyfast_schema()
    with transaction() as conn:
        rows = conn.execute(
            f"""SELECT c.id, c.account_id, c.category, c.priority, c.subject, c.initial_detail, c.state, c.revision,
                       c.created_at, c.updated_at, c.last_public_message_at, c.resolved_at, c.closed_at,
                       a.display_name, a.email
                  FROM web_support_cases c JOIN web_accounts a ON a.id=c.account_id
                  WHERE {' AND '.join(clauses)}
                  ORDER BY c.updated_at DESC, c.rowid DESC LIMIT ? OFFSET ?""",
            (*params, bounded_limit + 1, bounded_offset),
        ).fetchall()
    return envelope(
        True,
        "Danh sách yêu cầu riêng của Web Support Desk.",
        data={
            "items": [_case_public(tuple(row)) for row in rows[:bounded_limit]],
            "has_more": len(rows) > bounded_limit,
            "next_offset": bounded_offset + bounded_limit if len(rows) > bounded_limit else None,
            "delivery": "web_view_only",
        },
        status_name="read_only",
    )


@router.post("/cases")
async def create_case(payload: CaseCreateRequest, request: Request, account: dict = Depends(require_csrf)):
    """Create a case and initial public message in one Web-owned transaction."""
    _require_support_enabled()
    key = _idempotency_key(payload.idempotency_key)
    account_id = str(account["id"])
    fingerprint = _fingerprint({
        "category": payload.category, "priority": payload.priority, "subject": payload.subject,
        "detail_sha256": _content_hash(payload.detail),
    })

    def operation(conn: Any) -> dict[str, Any]:
        count = conn.execute(
            "SELECT COUNT(*) FROM web_support_cases WHERE account_id=? AND state NOT IN ('resolved', 'closed')",
            (account_id,),
        ).fetchone()
        if int(count[0] or 0) >= MAX_ACTIVE_CASES:
            return envelope(False, "Đã đạt giới hạn yêu cầu đang mở của Web Support Desk.", status_name="guarded", error_code="WEB_SUPPORT_CASE_LIMIT")
        case_id = str(uuid.uuid4())
        message_id = str(uuid.uuid4())
        now = utc_now()
        conn.execute(
            """INSERT INTO web_support_cases
               (id, account_id, category, priority, subject, initial_detail, state, revision, created_at, updated_at,
                last_public_message_at, resolved_at, closed_at, customer_waiting_since)
               VALUES (?, ?, ?, ?, ?, ?, 'new', 1, ?, ?, ?, NULL, NULL, ?)""",
            (case_id, account_id, payload.category, payload.priority, payload.subject, payload.detail, now, now, now, now),
        )
        conn.execute(
            """INSERT INTO web_support_messages
               (id, case_id, account_id, author_account_id, author_role, visibility, body, created_at)
               VALUES (?, ?, ?, ?, 'customer', 'public', ?, ?)""",
            (message_id, case_id, account_id, account_id, payload.detail, now),
        )
        _event(conn, case_id=case_id, account_id=account_id, actor_account_id=account_id, action="case_created", state="new")
        _record_audit(
            conn, account_id=account_id, canonical_user_id=str(account.get("canonical_user_id") or "") or None,
            action="web.support.case.create", request_id=_request_id(request), target=case_id,
            detail="web-owned support case created; no external delivery",
        )
        row = _case_row(conn, case_id=case_id, account_id=account_id)
        return envelope(True, "Đã ghi nhận yêu cầu trong Web Support Desk. Chưa gửi Telegram, email hoặc thông báo bên ngoài.", data={"case": _case_public(row or (), include_detail=False)}, status_name="completed")

    return _idempotent(f"web-support:{account_id}:case:create", key, fingerprint, operation)


def _support_attachment_not_found() -> dict[str, Any]:
    """Fail closed without disclosing another account's evidence metadata."""
    return envelope(
        False,
        "Không tìm thấy bằng chứng riêng tư thuộc yêu cầu Web hiện tại.",
        status_name="guarded",
        error_code="WEB_SUPPORT_ATTACHMENT_NOT_FOUND",
    )


def _support_attachment_unavailable() -> dict[str, Any]:
    return envelope(
        False,
        "Tệp bằng chứng riêng tư không còn sẵn sàng để dùng hoặc tải xuống.",
        status_name="guarded",
        error_code="WEB_SUPPORT_ATTACHMENT_UNAVAILABLE",
    )


def _attachment_public(row: tuple[Any, ...]) -> dict[str, Any]:
    """Return only snapshot fields safe for a case timeline/detail view."""
    return {
        "id": str(row[0]),
        "display_name": str(row[1]),
        "content_type": str(row[2]),
        "byte_size": int(row[3]),
        "created_at": str(row[4]),
    }


def _case_attachments(conn: Any, *, case_id: str) -> list[dict[str, Any]]:
    rows = conn.execute(
        """SELECT id, display_name_snapshot, content_type_snapshot, byte_size_snapshot, created_at
             FROM web_support_case_attachments
             WHERE case_id=?
             ORDER BY created_at ASC, id ASC
             LIMIT ?""",
        (case_id, MAX_SUPPORT_ATTACHMENTS_PER_CASE),
    ).fetchall()
    return [_attachment_public(tuple(row)) for row in rows]


def _support_attachment_asset_row(conn: Any, *, asset_id: str, account_id: str) -> tuple[Any, ...] | None:
    """Load only owner-scoped Asset Vault metadata needed for evidence checks."""
    row = conn.execute(
        """SELECT id, account_id, display_name, extension, content_type, byte_size, sha256, storage_key, state
             FROM web_asset_files
             WHERE id=? AND account_id=?""",
        (asset_id, account_id),
    ).fetchone()
    return tuple(row) if row else None


def _support_attachment_kind(asset: tuple[Any, ...]) -> str | None:
    pair = (str(asset[3] or "").lower(), str(asset[4] or "").lower())
    if pair not in SUPPORT_ATTACHMENT_CONTENT_TYPES:
        return None
    return "text" if pair[1] == "text/plain" else "image"


def _support_attachment_text_is_safe(content: bytes) -> bool:
    """Apply Support Desk's secret/payment rules to a bounded TXT asset.

    Images require an explicit customer redaction attestation but are never
    OCR-decoded or claimed to be inspected. Plain text is small enough to
    scan exactly before it enters the evidence relationship.
    """
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        return False
    return "\x00" not in text and not _contains_sensitive(text) and not MANUAL_PAYMENT_PATTERN.search(text)


def _mark_support_attachment_asset_unavailable(conn: Any, *, asset_id: str, account_id: str) -> None:
    """Fail closed on an integrity mismatch without deleting private evidence."""
    conn.execute(
        """UPDATE web_asset_files
           SET state='unavailable', updated_at=?, lifecycle_revision=lifecycle_revision + 1
           WHERE id=? AND account_id=? AND state IN ('active', 'archived')""",
        (utc_now(), asset_id, account_id),
    )


def _attachment_download_row(
    conn: Any,
    *,
    case_id: str,
    attachment_id: str,
    account_id: str | None,
) -> tuple[Any, ...] | None:
    clauses = ["e.id=?", "e.case_id=?", "e.account_id=c.account_id", "f.id=e.asset_id", "f.account_id=e.account_id"]
    params: list[Any] = [attachment_id, case_id]
    if account_id is not None:
        clauses.append("c.account_id=?")
        params.append(account_id)
    row = conn.execute(
        f"""SELECT e.id, e.case_id, e.account_id, e.display_name_snapshot, e.content_type_snapshot,
                   e.byte_size_snapshot, f.id, f.content_type, f.byte_size, f.sha256, f.storage_key, f.state
              FROM web_support_case_attachments e
              JOIN web_support_cases c ON c.id=e.case_id
              JOIN web_asset_files f ON f.id=e.asset_id
              WHERE {' AND '.join(clauses)}""",
        tuple(params),
    ).fetchone()
    return tuple(row) if row else None


def _attachment_download_response(conn: Any, *, row: tuple[Any, ...]) -> StreamingResponse | dict[str, Any]:
    """Build a verified, never-cached response for one private evidence item."""
    (
        _attachment_id, _case_id, account_id, display_name, snapshot_type, snapshot_size,
        asset_id, asset_type, asset_size, digest, storage_key, state,
    ) = row
    # Evidence can survive an Asset Vault archive, but an unavailable asset
    # is never downloadable. Snapshot fields must agree with the current
    # private asset row so stale metadata cannot be served as a file.
    if (
        str(state) not in {"active", "archived"}
        or str(snapshot_type) != str(asset_type)
        or int(snapshot_size) != int(asset_size)
        or str(snapshot_type) not in {"image/png", "image/jpeg", "image/webp", "text/plain"}
    ):
        return _support_attachment_unavailable()
    stream = open_verified_private_asset_stream(
        storage_key=str(storage_key),
        expected_bytes=int(asset_size),
        expected_digest=str(digest),
    )
    if stream is None:
        _mark_support_attachment_asset_unavailable(conn, asset_id=str(asset_id), account_id=str(account_id))
        return _support_attachment_unavailable()
    sealed_stream = seal_verified_private_file(
        stream,
        expected_bytes=int(asset_size),
        expected_digest=str(digest),
    )
    if sealed_stream is None:
        _mark_support_attachment_asset_unavailable(conn, asset_id=str(asset_id), account_id=str(account_id))
        return _support_attachment_unavailable()
    return private_asset_attachment_response(
        sealed_stream,
        byte_size=int(asset_size),
        media_type=str(snapshot_type),
        filename=str(display_name),
    )


def _case_detail(
    conn: Any, *, case_id: str, account_id: str | None, admin: bool,
    include_assignee_id: bool = False,
) -> dict[str, Any] | None:
    row = _case_row(conn, case_id=case_id, account_id=account_id)
    if not row:
        return None
    message_clauses = ["m.case_id=?"]
    message_params: list[Any] = [case_id]
    if not admin:
        message_clauses.append("m.visibility='public'")
    messages = conn.execute(
        f"""SELECT m.id, m.author_role, m.visibility, m.body, m.created_at, a.display_name
              FROM web_support_messages m JOIN web_accounts a ON a.id=m.author_account_id
              WHERE {' AND '.join(message_clauses)} ORDER BY m.created_at ASC, m.rowid ASC LIMIT 500""",
        tuple(message_params),
    ).fetchall()
    event_clauses = ["case_id=?"]
    event_params: list[Any] = [case_id]
    if not admin:
        event_clauses.append("action IN ({})".format(",".join("?" for _ in CUSTOMER_VISIBLE_EVENT_ACTIONS)))
        event_params.extend(sorted(CUSTOMER_VISIBLE_EVENT_ACTIONS))
    events = conn.execute(
        f"""SELECT id, action, state, created_at FROM web_support_events
            WHERE {' AND '.join(event_clauses)} ORDER BY created_at ASC, rowid ASC LIMIT 300""",
        tuple(event_params),
    ).fetchall()
    result = {
        "case": _case_public(
            row,
            include_detail=True,
            admin=admin,
            include_assignee_id=admin and include_assignee_id,
        ),
        "messages": [_message_public(tuple(item), admin=admin) for item in messages],
        "events": [_event_public(tuple(item)) for item in events],
        "attachments": _case_attachments(conn, case_id=case_id),
        "delivery": "web_view_only",
    }
    if admin:
        control_events = conn.execute(
            """SELECT e.id, e.kind, e.action, e.previous_value, e.next_value, e.reason, e.created_at,
                      a.display_name
                 FROM web_support_case_control_events e
                 LEFT JOIN web_accounts a ON a.id=e.actor_account_id
                 WHERE e.case_id=? ORDER BY e.created_at ASC, e.rowid ASC LIMIT 200""",
            (case_id,),
        ).fetchall()
        result["care_history"] = [_care_event_public(tuple(item)) for item in control_events]
    return result


@router.get("/cases/{case_id}")
async def get_case(case_id: str, account: dict = Depends(require_account)):
    _require_support_enabled()
    case_id = _uuid(case_id, label="Mã yêu cầu")
    ensure_copyfast_schema()
    with transaction() as conn:
        data = _case_detail(conn, case_id=case_id, account_id=str(account["id"]), admin=False)
    if not data:
        return _case_not_found()
    return envelope(True, "Đã nạp yêu cầu riêng từ Web Support Desk.", data=data, status_name="read_only")


@router.post("/cases/{case_id}/attachments")
async def attach_case_evidence(
    case_id: str,
    payload: CaseAttachmentRequest,
    request: Request,
    account: dict = Depends(require_csrf),
):
    """Link one existing, owner-scoped Asset Vault item as case evidence.

    This endpoint deliberately accepts metadata only. It never accepts file
    bytes, multipart form data, a source URL, an Asset Vault path, payment
    proof or an external-notification request.
    """
    _require_support_enabled()
    _require_support_evidence_enabled()
    if payload.customer_redaction_confirmed is not True:
        raise HTTPException(
            status_code=422,
            detail="Cần xác nhận đã che thông tin nhạy cảm trước khi đính kèm bằng chứng.",
        )
    case_id = _uuid(case_id, label="Mã yêu cầu")
    key = _idempotency_key(payload.idempotency_key)
    account_id = str(account["id"])
    fingerprint = _fingerprint({
        "action": "attach_private_asset",
        "asset_id": payload.asset_id,
        "expected_revision": payload.expected_revision,
        "customer_redaction_confirmed": True,
    })

    def operation(conn: Any) -> dict[str, Any]:
        current = _case_row(conn, case_id=case_id, account_id=account_id)
        if not current:
            return _case_not_found()
        if str(current[2]) in SUPPORT_ATTACHMENT_PAYMENT_CATEGORIES:
            return envelope(
                False,
                "Nhóm yêu cầu này không nhận bằng chứng tệp. Không gửi bill, TXID, QR hoặc dữ liệu thanh toán vào Web Support Desk.",
                status_name="guarded",
                error_code="WEB_SUPPORT_ATTACHMENT_PAYMENT_CATEGORY_BLOCKED",
            )
        if str(current[6]) == "closed":
            return envelope(
                False,
                "Yêu cầu đã đóng. Hãy mở lại trước khi liên kết bằng chứng mới.",
                status_name="guarded",
                error_code="WEB_SUPPORT_CASE_CLOSED",
            )
        if int(current[7]) != payload.expected_revision:
            return envelope(
                False,
                "Yêu cầu đã có cập nhật mới. Hãy tải lại trước khi đính kèm bằng chứng.",
                data={"current_revision": int(current[7])},
                status_name="guarded",
                error_code="WEB_SUPPORT_CASE_CONFLICT",
            )
        existing = conn.execute(
            "SELECT id FROM web_support_case_attachments WHERE case_id=? AND asset_id=?",
            (case_id, payload.asset_id),
        ).fetchone()
        if existing:
            return envelope(
                False,
                "Tệp này đã được liên kết với yêu cầu Web hiện tại.",
                status_name="guarded",
                error_code="WEB_SUPPORT_ATTACHMENT_ALREADY_LINKED",
            )
        count = conn.execute(
            "SELECT COUNT(*) FROM web_support_case_attachments WHERE case_id=?",
            (case_id,),
        ).fetchone()
        if int(count[0] or 0) >= MAX_SUPPORT_ATTACHMENTS_PER_CASE:
            return envelope(
                False,
                "Mỗi yêu cầu Web chỉ nhận tối đa 3 bằng chứng riêng tư.",
                status_name="guarded",
                error_code="WEB_SUPPORT_ATTACHMENT_LIMIT",
            )
        asset = _support_attachment_asset_row(conn, asset_id=payload.asset_id, account_id=account_id)
        if not asset or str(asset[8]) != "active":
            return envelope(
                False,
                "Tệp Asset Vault không còn sẵn sàng để liên kết với yêu cầu này.",
                status_name="guarded",
                error_code="WEB_SUPPORT_ATTACHMENT_ASSET_NOT_AVAILABLE",
            )
        kind = _support_attachment_kind(asset)
        if kind is None:
            return envelope(
                False,
                "Bằng chứng chỉ nhận PNG, JPEG, WebP hoặc TXT riêng tư từ Asset Vault.",
                status_name="guarded",
                error_code="WEB_SUPPORT_ATTACHMENT_TYPE_NOT_ALLOWED",
            )
        try:
            byte_size = int(asset[5])
        except (TypeError, ValueError):
            return _support_attachment_unavailable()
        if byte_size <= 0 or byte_size > MAX_SUPPORT_ATTACHMENT_BYTES:
            return envelope(
                False,
                "Tệp bằng chứng vượt giới hạn 5 MB của Web Support Desk.",
                status_name="guarded",
                error_code="WEB_SUPPORT_ATTACHMENT_SIZE_LIMIT",
            )
        if kind == "text":
            content = read_verified_private_asset_bytes(
                storage_key=str(asset[7]),
                expected_bytes=byte_size,
                expected_digest=str(asset[6]),
                maximum_bytes=MAX_SUPPORT_ATTACHMENT_BYTES,
            )
            if content is None:
                _mark_support_attachment_asset_unavailable(conn, asset_id=str(asset[0]), account_id=account_id)
                return _support_attachment_unavailable()
            if not _support_attachment_text_is_safe(content):
                return envelope(
                    False,
                    "Tệp TXT có dữ liệu nhạy cảm hoặc thông tin thanh toán nên không thể dùng làm bằng chứng.",
                    status_name="guarded",
                    error_code="WEB_SUPPORT_ATTACHMENT_CONTENT_RESTRICTED",
                )
        else:
            image_stream = open_verified_private_asset_stream(
                storage_key=str(asset[7]),
                expected_bytes=byte_size,
                expected_digest=str(asset[6]),
            )
            if image_stream is None:
                _mark_support_attachment_asset_unavailable(conn, asset_id=str(asset[0]), account_id=account_id)
                return _support_attachment_unavailable()
            image_stream.close()

        attachment_id = str(uuid.uuid4())
        now = utc_now()
        revision = int(current[7]) + 1
        changed = conn.execute(
            """UPDATE web_support_cases SET revision=?, updated_at=?
               WHERE id=? AND account_id=? AND revision=?""",
            (revision, now, case_id, account_id, int(current[7])),
        )
        if changed.rowcount != 1:
            return envelope(
                False,
                "Yêu cầu đã có cập nhật mới. Hãy tải lại trước khi đính kèm bằng chứng.",
                status_name="guarded",
                error_code="WEB_SUPPORT_CASE_CONFLICT",
            )
        conn.execute(
            """INSERT INTO web_support_case_attachments
               (id, case_id, account_id, asset_id, display_name_snapshot, content_type_snapshot,
                byte_size_snapshot, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                attachment_id, case_id, account_id, str(asset[0]), str(asset[2]), str(asset[4]), byte_size, now,
            ),
        )
        # This event carries only an action/state. It intentionally has no
        # Asset ID, name, storage path, checksum, text content or payment
        # metadata, while still invalidating stale triage/reliability reads
        # through the case revision update above.
        _event(
            conn,
            case_id=case_id,
            account_id=account_id,
            actor_account_id=account_id,
            action="customer_attachment_added",
            state=str(current[6]),
        )
        _record_audit(
            conn,
            account_id=account_id,
            canonical_user_id=str(account.get("canonical_user_id") or "") or None,
            action="web.support.case.attachment.link",
            request_id=_request_id(request),
            target=case_id,
            detail=f"private asset-vault evidence linked; kind={kind}; no upload/payment/OCR/external delivery",
        )
        row = _case_row(conn, case_id=case_id, account_id=account_id)
        attachment_row = conn.execute(
            """SELECT id, display_name_snapshot, content_type_snapshot, byte_size_snapshot, created_at
                 FROM web_support_case_attachments WHERE id=? AND case_id=? AND account_id=?""",
            (attachment_id, case_id, account_id),
        ).fetchone()
        return envelope(
            True,
            "Đã liên kết bằng chứng riêng tư từ Asset Vault. Không có upload mới, OCR, thông báo ngoài Web hoặc thao tác thanh toán.",
            data={
                "case": _case_public(row or ()),
                "attachment": _attachment_public(tuple(attachment_row)) if attachment_row else None,
                "delivery": "web_view_only",
            },
            status_name="completed",
        )

    return _idempotent(
        f"web-support:{account_id}:case:{case_id}:attachment:link",
        key,
        fingerprint,
        operation,
    )


@router.get("/cases/{case_id}/attachments/{attachment_id}/download")
async def download_case_evidence(
    case_id: str,
    attachment_id: str,
    account: dict = Depends(require_account),
):
    _require_support_enabled()
    _require_support_evidence_enabled()
    case_id = _uuid(case_id, label="Mã yêu cầu")
    attachment_id = _uuid(attachment_id, label="Mã bằng chứng")
    ensure_copyfast_schema()
    with transaction() as conn:
        row = _attachment_download_row(
            conn,
            case_id=case_id,
            attachment_id=attachment_id,
            account_id=str(account["id"]),
        )
        if not row:
            return _support_attachment_not_found()
        return _attachment_download_response(conn, row=row)


@router.get("/admin/cases/{case_id}/attachments/{attachment_id}/download")
async def admin_download_case_evidence(
    case_id: str,
    attachment_id: str,
    account: dict = Depends(require_account),
):
    _require_support_enabled()
    _require_support_evidence_enabled()
    require_support_staff(account)
    case_id = _uuid(case_id, label="Mã yêu cầu")
    attachment_id = _uuid(attachment_id, label="Mã bằng chứng")
    ensure_copyfast_schema()
    with transaction() as conn:
        row = _attachment_download_row(
            conn,
            case_id=case_id,
            attachment_id=attachment_id,
            account_id=None,
        )
        if not row:
            return _support_attachment_not_found()
        return _attachment_download_response(conn, row=row)


@router.post("/cases/{case_id}/reply")
async def reply_case(case_id: str, payload: CaseReplyRequest, request: Request, account: dict = Depends(require_csrf)):
    """Append an owner message; a closed case must be explicitly reopened."""
    _require_support_enabled()
    case_id = _uuid(case_id, label="Mã yêu cầu")
    key = _idempotency_key(payload.idempotency_key)
    account_id = str(account["id"])
    fingerprint = _fingerprint({"expected_revision": payload.expected_revision, "body_sha256": _content_hash(payload.body)})

    def operation(conn: Any) -> dict[str, Any]:
        current = _case_row(conn, case_id=case_id, account_id=account_id)
        if not current:
            return _case_not_found()
        if str(current[6]) == "closed":
            return envelope(False, "Yêu cầu đã đóng. Hãy mở lại trước khi gửi phản hồi.", status_name="guarded", error_code="WEB_SUPPORT_CASE_CLOSED")
        if int(current[7]) != payload.expected_revision:
            return envelope(False, "Yêu cầu đã có cập nhật mới. Hãy tải lại trước khi phản hồi.", data={"current_revision": int(current[7])}, status_name="guarded", error_code="WEB_SUPPORT_CASE_CONFLICT")
        message_count = conn.execute("SELECT COUNT(*) FROM web_support_messages WHERE case_id=?", (case_id,)).fetchone()
        if int(message_count[0] or 0) >= MAX_MESSAGES_PER_CASE:
            return envelope(False, "Yêu cầu đã đạt giới hạn phản hồi an toàn.", status_name="guarded", error_code="WEB_SUPPORT_MESSAGE_LIMIT")
        next_state = "reviewing" if str(current[6]) in {"waiting_user", "resolved"} else str(current[6])
        now = utc_now()
        revision = int(current[7]) + 1
        resolved_at, closed_at = _state_timestamps(current, next_state, now)
        conn.execute(
            """INSERT INTO web_support_messages
               (id, case_id, account_id, author_account_id, author_role, visibility, body, created_at)
               VALUES (?, ?, ?, ?, 'customer', 'public', ?, ?)""",
            (str(uuid.uuid4()), case_id, account_id, account_id, payload.body, now),
        )
        conn.execute(
            """UPDATE web_support_cases SET state=?, revision=?, updated_at=?, last_public_message_at=?, resolved_at=?, closed_at=?,
               customer_waiting_since=?
               WHERE id=? AND account_id=? AND revision=?""",
            (next_state, revision, now, now, resolved_at, closed_at, now, case_id, account_id, int(current[7])),
        )
        _event(conn, case_id=case_id, account_id=account_id, actor_account_id=account_id, action="customer_replied", state=next_state)
        _record_audit(conn, account_id=account_id, canonical_user_id=str(account.get("canonical_user_id") or "") or None, action="web.support.case.reply", request_id=_request_id(request), target=case_id, detail="web support customer reply appended")
        row = _case_row(conn, case_id=case_id, account_id=account_id)
        return envelope(True, "Đã thêm phản hồi trong Web Support Desk; không có thông báo ngoài Web.", data={"case": _case_public(row or ())}, status_name="completed")

    return _idempotent(f"web-support:{account_id}:case:{case_id}:reply", key, fingerprint, operation)


def _customer_transition(*, case_id: str, payload: CaseTransitionRequest, request: Request, account: dict, action: str) -> dict[str, Any]:
    if not payload.confirm:
        raise HTTPException(status_code=422, detail="Cần xác nhận thao tác Support Desk")
    key = _idempotency_key(payload.idempotency_key)
    account_id = str(account["id"])
    fingerprint = _fingerprint({"expected_revision": payload.expected_revision, "action": action})

    def operation(conn: Any) -> dict[str, Any]:
        current = _case_row(conn, case_id=case_id, account_id=account_id)
        if not current:
            return _case_not_found()
        state = str(current[6])
        if int(current[7]) != payload.expected_revision:
            return envelope(False, "Yêu cầu đã có cập nhật mới. Hãy tải lại trước khi tiếp tục.", data={"current_revision": int(current[7])}, status_name="guarded", error_code="WEB_SUPPORT_CASE_CONFLICT")
        if action == "close":
            if state == "closed":
                return envelope(False, "Yêu cầu đã đóng trước đó.", status_name="guarded", error_code="WEB_SUPPORT_CASE_CLOSED")
            next_state = "closed"
        elif action == "reopen":
            if state not in {"resolved", "closed"}:
                return envelope(False, "Chỉ yêu cầu đã giải quyết hoặc đã đóng mới có thể mở lại.", status_name="guarded", error_code="WEB_SUPPORT_CASE_STATE_INVALID")
            next_state = "reviewing"
        else:
            raise RuntimeError("Unknown Web Support customer transition")
        now = utc_now()
        revision = int(current[7]) + 1
        resolved_at, closed_at = _state_timestamps(current, next_state, now)
        conn.execute(
            """UPDATE web_support_cases SET state=?, revision=?, updated_at=?, closed_at=?, resolved_at=?, customer_waiting_since=?
               WHERE id=? AND account_id=? AND revision=?""",
            (next_state, revision, now, closed_at, resolved_at, None if action == "close" else now, case_id, account_id, int(current[7])),
        )
        _event(conn, case_id=case_id, account_id=account_id, actor_account_id=account_id, action=f"customer_{action}", state=next_state)
        _record_audit(conn, account_id=account_id, canonical_user_id=str(account.get("canonical_user_id") or "") or None, action=f"web.support.case.{action}", request_id=_request_id(request), target=case_id, detail="web support customer state changed")
        row = _case_row(conn, case_id=case_id, account_id=account_id)
        message = "Đã đóng yêu cầu trong Web Support Desk." if action == "close" else "Đã mở lại yêu cầu để Web Support Desk rà soát."
        return envelope(True, message, data={"case": _case_public(row or ())}, status_name="completed")

    return _idempotent(f"web-support:{account_id}:case:{case_id}:{action}", key, fingerprint, operation)


@router.post("/cases/{case_id}/close")
async def close_case(case_id: str, payload: CaseTransitionRequest, request: Request, account: dict = Depends(require_csrf)):
    _require_support_enabled()
    return _customer_transition(case_id=_uuid(case_id, label="Mã yêu cầu"), payload=payload, request=request, account=account, action="close")


@router.post("/cases/{case_id}/reopen")
async def reopen_case(case_id: str, payload: CaseTransitionRequest, request: Request, account: dict = Depends(require_csrf)):
    _require_support_enabled()
    return _customer_transition(case_id=_uuid(case_id, label="Mã yêu cầu"), payload=payload, request=request, account=account, action="reopen")


@router.get("/events")
async def support_events(limit: int = 40, account: dict = Depends(require_account)):
    _require_support_enabled()
    bounded_limit = max(1, min(int(limit), 100))
    ensure_copyfast_schema()
    with transaction() as conn:
        actions = sorted(CUSTOMER_VISIBLE_EVENT_ACTIONS)
        rows = conn.execute(
            f"""SELECT id, action, state, created_at FROM web_support_events
                WHERE account_id=? AND action IN ({','.join('?' for _ in actions)})
                ORDER BY created_at DESC, rowid DESC LIMIT ?""",
            (str(account["id"]), *actions, bounded_limit),
        ).fetchall()
    return envelope(True, "Hoạt động Web Support Desk của account hiện tại.", data={"items": [_event_public(tuple(row)) for row in rows]}, status_name="read_only")


@router.get("/admin/summary")
async def admin_summary(account: dict = Depends(require_account)):
    _require_support_enabled()
    role = require_support_staff(account)
    ensure_copyfast_schema()
    cutoff_one_day = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat(timespec="seconds")
    cutoff_three_days = (datetime.now(timezone.utc) - timedelta(hours=72)).isoformat(timespec="seconds")
    with transaction() as conn:
        rows = conn.execute("SELECT state, COUNT(*) FROM web_support_cases GROUP BY state").fetchall()
        overdue = conn.execute(
            """SELECT COUNT(*) FROM web_support_cases
               WHERE customer_waiting_since IS NOT NULL
                 AND ((state IN ('new','reviewing','refund_pending') AND customer_waiting_since<?)
                      OR (state='waiting_provider' AND customer_waiting_since<?))""",
            (cutoff_one_day, cutoff_three_days),
        ).fetchone()
    states = {state: 0 for state in sorted(CASE_STATES)}
    for state, count in rows:
        if str(state) in states:
            states[str(state)] = int(count)
    return envelope(True, "Tổng quan Web Support Desk cho operator.", data={"states": states, "overdue": int(overdue[0] or 0) if overdue else 0, "operator_role": role, "delivery": "web_view_only"}, status_name="read_only")


def _active_support_staff(conn: Any, *, account_id: str) -> dict[str, str] | None:
    """Resolve an assignee from protected account storage, never request data."""
    row = conn.execute(
        """SELECT id, display_name, role_cache
             FROM web_accounts WHERE id=? AND is_active=1""",
        (account_id,),
    ).fetchone()
    if not row:
        return None
    role = _staff_role({"role": str(row[2] or "")})
    if not role:
        return None
    return {
        "id": str(row[0]),
        "display_name": str(row[1] or "Customer Care"),
        "role": role,
    }


def _care_change_marker(*, team_queue: str, sla_class: str, assigned_account_id: str | None) -> str:
    # Preserve only bounded routing metadata in staff history. This avoids
    # copying customer content, email addresses or an internal support note
    # into a generic activity feed.
    assignment = "assigned" if assigned_account_id else "unassigned"
    return f"queue:{team_queue};sla:{sla_class};assignee:{assignment}"


@router.get("/admin/care/staff")
async def admin_care_staff(account: dict = Depends(require_account)):
    """Return a manager-only, server-derived assignee roster without email/PII."""
    _require_support_enabled()
    _require_support_manager(account)
    ensure_copyfast_schema()
    with transaction() as conn:
        rows = conn.execute(
            """SELECT id, display_name, role_cache
                 FROM web_accounts
                 WHERE is_active=1 AND role_cache IN ('admin', 'support_manager', 'support_operator')
                 ORDER BY CASE role_cache WHEN 'admin' THEN 0 WHEN 'support_manager' THEN 1 ELSE 2 END,
                          display_name COLLATE NOCASE ASC, id ASC
                 LIMIT 200"""
        ).fetchall()
    items = []
    for row in rows:
        role = _staff_role({"role": str(row[2] or "")})
        if role:
            items.append({"id": str(row[0]), "display_name": str(row[1] or "Customer Care"), "role": role})
    return envelope(
        True,
        "Danh sách nhân sự Customer Care được lấy từ Web account role phía máy chủ.",
        data={
            "items": items,
            "boundaries": [
                "Không trả email hoặc dữ liệu khách hàng.",
                "Roster chỉ phục vụ phân công nội bộ, không cấp quyền qua browser.",
            ],
        },
        status_name="read_only",
    )


@router.get("/admin/care/queues")
async def admin_care_queues(account: dict = Depends(require_account)):
    """Return staff-only queue/SLA counters; it never creates a timer or notice."""
    _require_support_enabled()
    role = require_support_staff(account)
    ensure_copyfast_schema()
    with transaction() as conn:
        rows = conn.execute(
            """SELECT COALESCE(ctrl.team_queue, 'general') AS team_queue,
                      COUNT(*) AS total,
                      SUM(CASE WHEN ctrl.assigned_account_id IS NULL THEN 1 ELSE 0 END) AS unassigned,
                      SUM(CASE WHEN COALESCE(ctrl.sla_class, 'standard')='critical' THEN 1 ELSE 0 END) AS critical,
                      SUM(CASE WHEN COALESCE(ctrl.escalation_state, 'none') IN ('requested', 'acknowledged') THEN 1 ELSE 0 END) AS escalated
                 FROM web_support_cases c
                 LEFT JOIN web_support_case_controls ctrl ON ctrl.case_id=c.id
                 WHERE c.state NOT IN ('resolved', 'closed')
                 GROUP BY COALESCE(ctrl.team_queue, 'general')
                 ORDER BY CASE COALESCE(ctrl.team_queue, 'general')
                     WHEN 'general' THEN 0 WHEN 'technical' THEN 1 WHEN 'account' THEN 2
                     WHEN 'creative' THEN 3 WHEN 'document' THEN 4 ELSE 5 END"""
        ).fetchall()
    items = [{
        "team_queue": str(row[0]),
        "total": int(row[1] or 0),
        "unassigned": int(row[2] or 0),
        "critical": int(row[3] or 0),
        "escalated": int(row[4] or 0),
    } for row in rows]
    return envelope(
        True,
        "Tổng hợp hàng đợi Customer Care nội bộ.",
        data={
            "items": items,
            "operator_role": role,
            "delivery": "internal_metadata_only",
            "boundaries": [
                "Không gửi thông báo khách hàng hoặc tạo SLA timer tự động.",
                "Không xử lý nạp thủ công, thanh toán, refund hoặc retry bên ngoài.",
            ],
        },
        status_name="read_only",
    )


@router.post("/admin/cases/{case_id}/care/triage")
async def admin_care_triage(
    case_id: str,
    payload: AdminCareTriageRequest,
    request: Request,
    account: dict = Depends(require_csrf),
):
    """Manager-only internal queue/assignee/SLA change with no external delivery."""
    _require_support_enabled()
    staff_role = _require_support_manager(account)
    if not payload.confirm:
        raise HTTPException(status_code=422, detail="Customer Care manager cần xác nhận trước khi phân công")
    case_id = _uuid(case_id, label="Mã yêu cầu")
    key = _idempotency_key(payload.idempotency_key)
    fingerprint = _fingerprint({
        "expected_revision": payload.expected_revision,
        "team_queue": payload.team_queue,
        "assigned_account_id": payload.assigned_account_id or "",
        "sla_class": payload.sla_class,
        "operation_note_sha256": _content_hash(payload.operation_note),
    })

    def operation(conn: Any) -> dict[str, Any]:
        current = _case_row(conn, case_id=case_id)
        if not current:
            return _case_not_found()
        if str(current[6]) == "closed":
            return envelope(False, "Yêu cầu đã đóng; hãy mở lại trước khi phân công Customer Care.", status_name="guarded", error_code="WEB_SUPPORT_CASE_CLOSED")
        if int(current[7]) != payload.expected_revision:
            return envelope(False, "Yêu cầu đã có cập nhật mới. Hãy tải lại trước khi phân công.", data={"current_revision": int(current[7])}, status_name="guarded", error_code="WEB_SUPPORT_CASE_CONFLICT")
        assignee = None
        if payload.assigned_account_id:
            assignee = _active_support_staff(conn, account_id=payload.assigned_account_id)
            if not assignee:
                return envelope(False, "Nhân sự được chọn không còn có quyền Customer Care hoạt động.", status_name="guarded", error_code="WEB_SUPPORT_ASSIGNEE_INVALID")
        control = _case_control(conn, case_id=case_id)
        previous_queue = str(control[0]) if control else "general"
        previous_assignee = str(control[1] or "") if control else ""
        previous_sla = str(control[2]) if control else "standard"
        now = utc_now()
        revision = int(current[7]) + 1
        changed = conn.execute(
            """UPDATE web_support_cases SET revision=?, updated_at=?
               WHERE id=? AND revision=?""",
            (revision, now, case_id, int(current[7])),
        )
        if changed.rowcount != 1:
            return envelope(False, "Yêu cầu đã có cập nhật mới. Hãy tải lại trước khi phân công.", status_name="guarded", error_code="WEB_SUPPORT_CASE_CONFLICT")
        _ensure_case_control(conn, case_id=case_id, now=now)
        conn.execute(
            """UPDATE web_support_case_controls
               SET team_queue=?, assigned_account_id=?, sla_class=?,
                   first_staff_touched_at=COALESCE(first_staff_touched_at, ?), updated_at=?
               WHERE case_id=?""",
            (payload.team_queue, assignee["id"] if assignee else None, payload.sla_class, now, now, case_id),
        )
        _care_event(
            conn,
            case_id=case_id,
            account_id=str(current[1]),
            actor_account_id=str(account["id"]),
            kind="triage",
            action="updated",
            previous_value=_care_change_marker(
                team_queue=previous_queue,
                sla_class=previous_sla,
                assigned_account_id=previous_assignee or None,
            ),
            next_value=_care_change_marker(
                team_queue=payload.team_queue,
                sla_class=payload.sla_class,
                assigned_account_id=assignee["id"] if assignee else None,
            ),
            reason=payload.operation_note,
        )
        _event(conn, case_id=case_id, account_id=str(current[1]), actor_account_id=str(account["id"]), action="operator_care_triaged", state=str(current[6]))
        _record_audit(
            conn,
            account_id=str(account["id"]),
            canonical_user_id=str(account.get("canonical_user_id") or "") or None,
            action="web.support.admin.care.triage",
            request_id=_request_id(request),
            target=case_id,
            detail=f"internal care triage queue:{payload.team_queue} sla:{payload.sla_class} assignee:{'assigned' if assignee else 'unassigned'} role:{staff_role}; no external delivery",
        )
        row = _case_row(conn, case_id=case_id)
        return envelope(
            True,
            "Đã cập nhật hàng đợi, phân công và SLA nội bộ. Chưa gửi thông báo khách hàng.",
            data={"case": _case_public(row or (), admin=True), "delivery": "internal_metadata_only"},
            status_name="completed",
        )

    return _idempotent(f"web-support:admin:{account['id']}:case:{case_id}:care:triage", key, fingerprint, operation)


@router.post("/admin/cases/{case_id}/care/escalation")
async def admin_care_escalation(
    case_id: str,
    payload: AdminCareEscalationRequest,
    request: Request,
    account: dict = Depends(require_csrf),
):
    """Record a controlled internal escalation lifecycle; no external action is implied."""
    _require_support_enabled()
    staff_role = require_support_staff(account)
    if payload.escalation_state != "requested" and staff_role != "manager":
        raise HTTPException(status_code=403, detail="Chỉ Customer Care manager được xác nhận, giải quyết hoặc hủy escalation")
    if not payload.confirm:
        raise HTTPException(status_code=422, detail="Cần xác nhận trước khi thay đổi escalation nội bộ")
    case_id = _uuid(case_id, label="Mã yêu cầu")
    key = _idempotency_key(payload.idempotency_key)
    fingerprint = _fingerprint({
        "expected_revision": payload.expected_revision,
        "escalation_state": payload.escalation_state,
        "reason_sha256": _content_hash(payload.reason),
    })

    def operation(conn: Any) -> dict[str, Any]:
        current = _case_row(conn, case_id=case_id)
        if not current:
            return _case_not_found()
        if str(current[6]) == "closed":
            return envelope(False, "Yêu cầu đã đóng; không thể tạo escalation mới.", status_name="guarded", error_code="WEB_SUPPORT_CASE_CLOSED")
        if int(current[7]) != payload.expected_revision:
            return envelope(False, "Yêu cầu đã có cập nhật mới. Hãy tải lại trước khi thay đổi escalation.", data={"current_revision": int(current[7])}, status_name="guarded", error_code="WEB_SUPPORT_CASE_CONFLICT")
        control = _case_control(conn, case_id=case_id)
        previous_state = str(control[4]) if control else "none"
        allowed = ESCALATION_TRANSITIONS.get(previous_state, frozenset())
        if payload.escalation_state not in allowed:
            return envelope(
                False,
                "Chuyển trạng thái escalation không hợp lệ. Hãy tải lại lịch sử Customer Care.",
                data={"current_escalation_state": previous_state},
                status_name="guarded",
                error_code="WEB_SUPPORT_ESCALATION_STATE_INVALID",
            )
        now = utc_now()
        revision = int(current[7]) + 1
        changed = conn.execute(
            """UPDATE web_support_cases SET revision=?, updated_at=?
               WHERE id=? AND revision=?""",
            (revision, now, case_id, int(current[7])),
        )
        if changed.rowcount != 1:
            return envelope(False, "Yêu cầu đã có cập nhật mới. Hãy tải lại trước khi thay đổi escalation.", status_name="guarded", error_code="WEB_SUPPORT_CASE_CONFLICT")
        _ensure_case_control(conn, case_id=case_id, now=now)
        requested_at = now if payload.escalation_state == "requested" else (str(control[6]) if control and control[6] else now)
        acknowledged_at = now if payload.escalation_state == "acknowledged" else (str(control[7]) if control and control[7] else None)
        resolved_at = now if payload.escalation_state in {"resolved", "cancelled"} else None
        conn.execute(
            """UPDATE web_support_case_controls
               SET escalation_state=?, escalation_reason=?, escalation_requested_at=?,
                   escalation_acknowledged_at=?, escalation_resolved_at=?, escalation_actor_account_id=?,
                   first_staff_touched_at=COALESCE(first_staff_touched_at, ?), updated_at=?
               WHERE case_id=?""",
            (
                payload.escalation_state, payload.reason, requested_at, acknowledged_at, resolved_at,
                str(account["id"]), now, now, case_id,
            ),
        )
        _care_event(
            conn,
            case_id=case_id,
            account_id=str(current[1]),
            actor_account_id=str(account["id"]),
            kind="escalation",
            action=payload.escalation_state,
            previous_value=previous_state,
            next_value=payload.escalation_state,
            reason=payload.reason,
        )
        _event(conn, case_id=case_id, account_id=str(current[1]), actor_account_id=str(account["id"]), action=f"operator_escalation_{payload.escalation_state}", state=str(current[6]))
        _record_audit(
            conn,
            account_id=str(account["id"]),
            canonical_user_id=str(account.get("canonical_user_id") or "") or None,
            action="web.support.admin.care.escalation",
            request_id=_request_id(request),
            target=case_id,
            detail=f"internal care escalation {previous_state}->{payload.escalation_state} role:{staff_role}; no external delivery",
        )
        row = _case_row(conn, case_id=case_id)
        return envelope(
            True,
            "Đã lưu trạng thái escalation nội bộ. Chưa kích hoạt thông báo hay thao tác bên ngoài.",
            data={"case": _case_public(row or (), admin=True), "delivery": "internal_metadata_only"},
            status_name="completed",
        )

    return _idempotent(f"web-support:admin:{account['id']}:case:{case_id}:care:escalation", key, fingerprint, operation)


@router.get("/admin/cases")
async def admin_list_cases(
    limit: int = 50,
    offset: int = 0,
    state: str = "all",
    category: str = "",
    q: str = "",
    team_queue: str = "all",
    assignment: str = "all",
    sla_class: str = "all",
    care_sla_status: str = "all",
    escalation_state: str = "all",
    account: dict = Depends(require_account),
):
    _require_support_enabled()
    require_support_staff(account)
    bounded_limit = max(1, min(int(limit), 100))
    if int(offset) < 0 or int(offset) > 10_000:
        raise HTTPException(status_code=422, detail="Offset danh sách không hợp lệ")
    bounded_offset = int(offset)
    state_filter = str(state or "all").strip().lower()
    if state_filter not in {*CASE_STATES, "all"}:
        raise HTTPException(status_code=422, detail="Bộ lọc trạng thái không hợp lệ")
    category_filter = str(category or "").strip().lower()
    if category_filter and category_filter not in CASE_CATEGORIES:
        raise HTTPException(status_code=422, detail="Bộ lọc nhóm yêu cầu không hợp lệ")
    team_queue_filter = str(team_queue or "all").strip().lower()
    if team_queue_filter not in {*CARE_TEAM_QUEUES, "all"}:
        raise HTTPException(status_code=422, detail="Bộ lọc hàng đợi Customer Care không hợp lệ")
    assignment_filter = str(assignment or "all").strip().lower()
    if assignment_filter not in CARE_ASSIGNMENT_FILTERS:
        raise HTTPException(status_code=422, detail="Bộ lọc phân công Customer Care không hợp lệ")
    sla_class_filter = str(sla_class or "all").strip().lower()
    if sla_class_filter not in {*SLA_CLASSES, "all"}:
        raise HTTPException(status_code=422, detail="Bộ lọc SLA Customer Care không hợp lệ")
    care_sla_status_filter = str(care_sla_status or "all").strip().lower()
    if care_sla_status_filter not in CARE_SLA_STATUS_FILTERS:
        raise HTTPException(status_code=422, detail="Bộ lọc trạng thái SLA Customer Care không hợp lệ")
    escalation_filter = str(escalation_state or "all").strip().lower()
    if escalation_filter not in {*ESCALATION_STATES, "all"}:
        raise HTTPException(status_code=422, detail="Bộ lọc escalation Customer Care không hợp lệ")
    query = _validated_line(q, label="Từ khóa tìm kiếm", minimum=0, maximum=80, allow_empty=True)
    clauses = ["1=1"]
    params: list[Any] = []
    if state_filter != "all":
        clauses.append("c.state=?")
        params.append(state_filter)
    if category_filter:
        clauses.append("c.category=?")
        params.append(category_filter)
    # Controls are left-joined so legacy/new cases without a triage row still
    # remain visible in their safe defaults (general, standard, none,
    # unassigned).  These are only staff-visible Web-native metadata filters;
    # no account ID, external queue, provider, payment or Bot state may enter
    # the query surface.
    if team_queue_filter != "all":
        clauses.append("COALESCE(ctrl.team_queue, 'general')=?")
        params.append(team_queue_filter)
    if assignment_filter == "mine":
        # The browser submits only the fixed enum. The signed staff account is
        # the sole assignee identity used here, so a user cannot enumerate or
        # query another operator's queue by supplying an account ID.
        clauses.append("ctrl.assigned_account_id=?")
        params.append(str(account["id"]))
    elif assignment_filter == "assigned":
        clauses.append("ctrl.assigned_account_id IS NOT NULL")
    elif assignment_filter == "unassigned":
        clauses.append("ctrl.assigned_account_id IS NULL")
    if sla_class_filter != "all":
        clauses.append("COALESCE(ctrl.sla_class, 'standard')=?")
        params.append(sla_class_filter)
    if care_sla_status_filter != "all":
        # The current time and every SLA target stay server-side.  This fixed
        # projection is intentionally evaluated before pagination so a
        # browser cannot suppress matching case IDs by filtering a partial
        # page, supply a clock/timestamp, or borrow another SLA policy.
        status_sql, status_params = _care_sla_status_sql(now=utc_now())
        clauses.append(f"({status_sql})=?")
        params.extend((*status_params, care_sla_status_filter))
    if escalation_filter != "all":
        clauses.append("COALESCE(ctrl.escalation_state, 'none')=?")
        params.append(escalation_filter)
    if query:
        escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        clauses.append("(c.subject LIKE ? ESCAPE '\\' OR c.initial_detail LIKE ? ESCAPE '\\' OR a.display_name LIKE ? ESCAPE '\\')")
        params.extend([f"%{escaped}%", f"%{escaped}%", f"%{escaped}%"])
    ensure_copyfast_schema()
    with transaction() as conn:
        rows = conn.execute(
            f"""SELECT c.id, c.account_id, c.category, c.priority, c.subject, c.initial_detail, c.state, c.revision,
                       c.created_at, c.updated_at, c.last_public_message_at, c.resolved_at, c.closed_at,
                       a.display_name, a.email,
                       COALESCE(ctrl.team_queue, 'general'), ctrl.assigned_account_id,
                       assignee.display_name, COALESCE(ctrl.sla_class, 'standard'),
                       COALESCE(ctrl.escalation_state, 'none'), COALESCE(ctrl.escalation_reason, ''),
                       ctrl.escalation_requested_at, ctrl.escalation_acknowledged_at,
                       ctrl.escalation_resolved_at, ctrl.first_staff_touched_at
                  FROM web_support_cases c
                  JOIN web_accounts a ON a.id=c.account_id
                  LEFT JOIN web_support_case_controls ctrl ON ctrl.case_id=c.id
                  LEFT JOIN web_accounts assignee ON assignee.id=ctrl.assigned_account_id
                  WHERE {' AND '.join(clauses)}
                  ORDER BY CASE c.priority WHEN 'urgent' THEN 0 WHEN 'high' THEN 1 WHEN 'normal' THEN 2 ELSE 3 END,
                           c.updated_at DESC, c.rowid DESC LIMIT ? OFFSET ?""",
            (*params, bounded_limit + 1, bounded_offset),
        ).fetchall()
    return envelope(
        True,
        "Danh sách yêu cầu Web Support Desk cho operator.",
        data={
            "items": [_case_public(tuple(row), admin=True) for row in rows[:bounded_limit]],
            "has_more": len(rows) > bounded_limit,
            "next_offset": bounded_offset + bounded_limit if len(rows) > bounded_limit else None,
            "filters": {
                "state": state_filter,
                "category": category_filter,
                "team_queue": team_queue_filter,
                "assignment": assignment_filter,
                "sla_class": sla_class_filter,
                "care_sla_status": care_sla_status_filter,
                "escalation_state": escalation_filter,
            },
        },
        status_name="read_only",
    )


@router.get("/admin/cases/{case_id}")
async def admin_get_case(case_id: str, account: dict = Depends(require_account)):
    _require_support_enabled()
    staff_role = require_support_staff(account)
    case_id = _uuid(case_id, label="Mã yêu cầu")
    ensure_copyfast_schema()
    with transaction() as conn:
        data = _case_detail(
            conn,
            case_id=case_id,
            account_id=None,
            admin=True,
            include_assignee_id=staff_role == "manager",
        )
    if not data:
        return _case_not_found()
    return envelope(True, "Đã nạp yêu cầu Web Support Desk cho operator.", data=data, status_name="read_only")


@router.post("/admin/cases/{case_id}/reply")
async def admin_reply_case(case_id: str, payload: AdminReplyRequest, request: Request, account: dict = Depends(require_csrf)):
    _require_support_enabled()
    staff_role = require_support_staff(account)
    if not payload.confirm:
        raise HTTPException(status_code=422, detail="Operator cần xác nhận trước khi gửi phản hồi")
    case_id = _uuid(case_id, label="Mã yêu cầu")
    key = _idempotency_key(payload.idempotency_key)
    fingerprint = _fingerprint({"expected_revision": payload.expected_revision, "body_sha256": _content_hash(payload.body), "visibility": payload.visibility, "next_state": payload.next_state})

    def operation(conn: Any) -> dict[str, Any]:
        current = _case_row(conn, case_id=case_id)
        if not current:
            return _case_not_found()
        if int(current[7]) != payload.expected_revision:
            return envelope(False, "Yêu cầu đã có cập nhật mới. Hãy tải lại trước khi phản hồi.", data={"current_revision": int(current[7])}, status_name="guarded", error_code="WEB_SUPPORT_CASE_CONFLICT")
        if str(current[6]) == "closed":
            return envelope(False, "Yêu cầu đã đóng; hãy dùng cập nhật trạng thái có xác nhận để mở lại trước.", status_name="guarded", error_code="WEB_SUPPORT_CASE_CLOSED")
        message_count = conn.execute("SELECT COUNT(*) FROM web_support_messages WHERE case_id=?", (case_id,)).fetchone()
        if int(message_count[0] or 0) >= MAX_MESSAGES_PER_CASE:
            return envelope(False, "Yêu cầu đã đạt giới hạn phản hồi an toàn.", status_name="guarded", error_code="WEB_SUPPORT_MESSAGE_LIMIT")
        next_state = payload.next_state or ("waiting_user" if payload.visibility == "public" else str(current[6]))
        now = utc_now()
        revision = int(current[7]) + 1
        resolved_at, closed_at = _state_timestamps(current, next_state, now)
        conn.execute(
            """INSERT INTO web_support_messages
               (id, case_id, account_id, author_account_id, author_role, visibility, body, created_at)
               VALUES (?, ?, ?, ?, 'operator', ?, ?, ?)""",
            (str(uuid.uuid4()), case_id, str(current[1]), str(account["id"]), payload.visibility, payload.body, now),
        )
        conn.execute(
            """UPDATE web_support_cases SET state=?, revision=?, updated_at=?, last_public_message_at=?, resolved_at=?, closed_at=?,
               customer_waiting_since=CASE WHEN ?='public' THEN NULL ELSE customer_waiting_since END
               WHERE id=? AND revision=?""",
            (next_state, revision, now, now if payload.visibility == "public" else current[10], resolved_at, closed_at,
             payload.visibility, case_id, int(current[7])),
        )
        _event(conn, case_id=case_id, account_id=str(current[1]), actor_account_id=str(account["id"]), action="operator_replied_public" if payload.visibility == "public" else "operator_noted_internal", state=next_state)
        _record_audit(conn, account_id=str(account["id"]), canonical_user_id=str(account.get("canonical_user_id") or "") or None, action="web.support.admin.reply", request_id=_request_id(request), target=case_id, detail=f"web support operator reply visibility:{payload.visibility} role:{staff_role}")
        row = _case_row(conn, case_id=case_id)
        return envelope(True, "Đã lưu phản hồi trong Web Support Desk. Chưa gửi Telegram, email hoặc thông báo bên ngoài.", data={"case": _case_public(row or (), admin=True)}, status_name="completed")

    return _idempotent(f"web-support:admin:{account['id']}:case:{case_id}:reply", key, fingerprint, operation)


@router.post("/admin/cases/{case_id}/update")
async def admin_update_case(case_id: str, payload: AdminUpdateRequest, request: Request, account: dict = Depends(require_csrf)):
    _require_support_enabled()
    staff_role = require_support_staff(account)
    if not payload.confirm:
        raise HTTPException(status_code=422, detail="Operator cần xác nhận trước khi cập nhật yêu cầu")
    case_id = _uuid(case_id, label="Mã yêu cầu")
    key = _idempotency_key(payload.idempotency_key)
    fingerprint = _fingerprint({"expected_revision": payload.expected_revision, "state": payload.state, "priority": payload.priority, "operation_note_sha256": _content_hash(payload.operation_note)})

    def operation(conn: Any) -> dict[str, Any]:
        current = _case_row(conn, case_id=case_id)
        if not current:
            return _case_not_found()
        if int(current[7]) != payload.expected_revision:
            return envelope(False, "Yêu cầu đã có cập nhật mới. Hãy tải lại trước khi thay đổi.", data={"current_revision": int(current[7])}, status_name="guarded", error_code="WEB_SUPPORT_CASE_CONFLICT")
        message_count = conn.execute("SELECT COUNT(*) FROM web_support_messages WHERE case_id=?", (case_id,)).fetchone()
        if int(message_count[0] or 0) >= MAX_MESSAGES_PER_CASE:
            return envelope(False, "Yêu cầu đã đạt giới hạn phản hồi an toàn.", status_name="guarded", error_code="WEB_SUPPORT_MESSAGE_LIMIT")
        now = utc_now()
        revision = int(current[7]) + 1
        resolved_at, closed_at = _state_timestamps(current, payload.state, now)
        conn.execute(
            """UPDATE web_support_cases SET state=?, priority=?, revision=?, updated_at=?, resolved_at=?, closed_at=?,
               customer_waiting_since=CASE WHEN ? IN ('resolved','closed') THEN NULL ELSE customer_waiting_since END
               WHERE id=? AND revision=?""",
            (payload.state, payload.priority, revision, now, resolved_at, closed_at, payload.state, case_id, int(current[7])),
        )
        conn.execute(
            """INSERT INTO web_support_messages
               (id, case_id, account_id, author_account_id, author_role, visibility, body, created_at)
               VALUES (?, ?, ?, ?, 'operator', 'internal', ?, ?)""",
            (str(uuid.uuid4()), case_id, str(current[1]), str(account["id"]), payload.operation_note, now),
        )
        _event(conn, case_id=case_id, account_id=str(current[1]), actor_account_id=str(account["id"]), action="operator_updated", state=payload.state)
        # Preserve the operator's safe narrative as a staff-only message so a
        # later shift can understand the decision, but never copy it into the
        # generally accessible audit trail.
        _record_audit(conn, account_id=str(account["id"]), canonical_user_id=str(account.get("canonical_user_id") or "") or None, action="web.support.admin.update", request_id=_request_id(request), target=case_id, detail=f"web support operator state:{payload.state} priority:{payload.priority} role:{staff_role}; internal_note_saved")
        row = _case_row(conn, case_id=case_id)
        return envelope(True, "Đã cập nhật trạng thái Web Support Desk; không có external delivery.", data={"case": _case_public(row or (), admin=True)}, status_name="completed")

    return _idempotent(f"web-support:admin:{account['id']}:case:{case_id}:update", key, fingerprint, operation)
