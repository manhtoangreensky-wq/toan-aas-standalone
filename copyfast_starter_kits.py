"""Signed Web-native Starter Kits for a deliberate Project launch.

Starter Kits turn a completed Workspace Setup profile into one transparent,
reviewable set of Web-owned records: a Project, initial Studio Documents and
one Workboard card.  They are intentionally local authoring/coordination
only.  This module never imports the Telegram Bot, a bridge, a provider or a
payment engine, and it never creates an execution job, media asset, delivery,
publication or notification.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, field_validator

import copyfast_workboard
import copyfast_workspace_setup
from copyfast_auth import _record_audit, _request_id, envelope, require_account, require_csrf
from copyfast_db import (
    ensure_copyfast_schema,
    read_transaction,
    starter_kits_enabled,
    transaction,
    utc_now,
    workboard_enabled,
)


router = APIRouter(prefix="/api/v1/workspace/starter-kits", tags=["Web Workspace Starter Kits"])

CATALOG_VERSION = "web_starter_kits_v1"
MAX_REVISION = 2_147_483_647
MAX_IDEMPOTENCY_RECORDS_PER_ACCOUNT = 1_024
IDEMPOTENCY_RETENTION = timedelta(hours=24)
IDEMPOTENCY_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{12,160}$")
KIT_KEY_PATTERN = re.compile(r"^[a-z][a-z0-9-]{2,47}$")
TEXT_CONTROL_PATTERN = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


# Every record specification is deliberately static and reviewed in source.
# The browser can choose only a closed key/version, so it cannot supply a
# title, document body, checklist, project reference or implicit action.
STARTER_KITS: tuple[dict[str, Any], ...] = (
    {
        "key": "project-foundation",
        "version": 1,
        "title": "Khung Project đầu tiên",
        "summary": "Bắt đầu bằng brief, tiêu chí review và một danh sách việc rõ ràng.",
        "outcome": "Một nền tảng Project để bạn tiếp tục bằng nội dung của chính mình.",
        "icon": "dashboard",
        "focus_areas": ("projects", "automation"),
        "goals": ("organize_work", "learn_workflows"),
        "project": {
            "title": "Khung Project Web",
            "summary": "Thiết lập mục tiêu, phạm vi và nhịp review trong Workspace.",
            "objective": "Xây một Project có brief và các bước tiếp theo rõ ràng.",
        },
        "documents": (
            {
                "kind": "brief",
                "title": "Brief khởi đầu",
                "content": "Mục tiêu\n- Viết mục tiêu cụ thể của Project.\n\nBối cảnh\n- Ghi người dùng, phạm vi và giới hạn cần tôn trọng.\n\nTiêu chí hoàn thành\n- Nêu những điều cần được tự review trước khi chuyển sang bước khác.",
            },
            {
                "kind": "note",
                "title": "Quy tắc làm việc",
                "content": "1. Chỉ thêm thông tin đã được kiểm tra.\n2. Giữ các quyết định trong Studio Documents.\n3. Đánh dấu điều chưa chắc chắn để review, không xem đó là kết quả đã hoàn tất.",
            },
        ),
        "workboard": {
            "title": "Khởi động Project",
            "description": "Rà soát brief, xác định bước đầu tiên và ghi lại điều cần review trước khi tiếp tục.",
            "priority": "normal",
            "checklist": ("Điền mục tiêu và phạm vi", "Xác định tiêu chí review", "Chọn bước tiếp theo"),
        },
    },
    {
        "key": "content-foundation",
        "version": 1,
        "title": "Nền tảng nội dung",
        "summary": "Sắp xếp góc nhìn, thông điệp và khung biên tập trước khi viết.",
        "outcome": "Một Project nội dung có brief, khung thông điệp và checklist review.",
        "icon": "prompt",
        "focus_areas": ("content", "projects"),
        "goals": ("create_content", "build_brand"),
        "project": {
            "title": "Kế hoạch nội dung Web",
            "summary": "Tổ chức bối cảnh, thông điệp và vòng review nội dung.",
            "objective": "Chuẩn bị một hướng nội dung có thể biên tập tiếp.",
        },
        "documents": (
            {
                "kind": "brief",
                "title": "Brief nội dung",
                "content": "Đối tượng\n- Ai sẽ đọc hoặc sử dụng nội dung này?\n\nThông điệp chính\n- Viết một câu ngắn, rõ và có thể kiểm tra.\n\nBằng chứng cần có\n- Liệt kê nguồn hoặc dữ kiện cần review trước khi xuất bản.",
            },
            {
                "kind": "caption",
                "title": "Khung thông điệp",
                "content": "Mở đầu\n- Gợi vấn đề hoặc lợi ích thật.\n\nGiá trị\n- Diễn giải bằng thông tin đã kiểm tra.\n\nLời mời tiếp theo\n- Chọn một hành động phù hợp, không hứa hẹn quá mức.",
            },
            {
                "kind": "script",
                "title": "Khung biên tập",
                "content": "1. Bối cảnh\n2. Vấn đề hoặc cơ hội\n3. Luận điểm chính\n4. Ví dụ hoặc bằng chứng\n5. Tự review về claim, giọng điệu và quyền sử dụng.",
            },
        ),
        "workboard": {
            "title": "Review nền tảng nội dung",
            "description": "Hoàn thiện brief và thông điệp trước khi mở một workflow biên tập chuyên sâu.",
            "priority": "normal",
            "checklist": ("Xác định đối tượng", "Rà soát claim và bằng chứng", "Chọn tài liệu cần biên tập tiếp"),
        },
    },
    {
        "key": "image-direction",
        "version": 1,
        "title": "Art direction hình ảnh",
        "summary": "Chuẩn bị ý đồ thị giác, hạn chế và tiêu chí chọn phương án.",
        "outcome": "Một Project direction để bạn review trước khi dùng bất kỳ công cụ nào.",
        "icon": "image",
        "focus_areas": ("image", "projects"),
        "goals": ("build_brand", "create_content"),
        "project": {
            "title": "Art direction hình ảnh",
            "summary": "Ghi lại ý đồ thị giác và tiêu chí tự review trên Web.",
            "objective": "Xây direction hình ảnh có thể trao đổi và chỉnh sửa rõ ràng.",
        },
        "documents": (
            {
                "kind": "brief",
                "title": "Brief art direction",
                "content": "Mục đích\n- Hình ảnh cần giải quyết điều gì?\n\nCảm nhận cần giữ\n- Nêu ba tính từ về không khí và thương hiệu.\n\nGiới hạn\n- Ghi rõ nội dung, biểu tượng hoặc claim không nên xuất hiện.",
            },
            {
                "kind": "prompt",
                "title": "Khung direction",
                "content": "Chủ thể\n- Mô tả chủ thể và bối cảnh.\n\nBố cục\n- Nêu trọng tâm, khoảng trống và tỉ lệ mong muốn.\n\nÁnh sáng và chất liệu\n- Ghi lựa chọn có thể review bằng mắt.\n\nLoại trừ\n- Liệt kê điều không phù hợp với brief.",
            },
            {
                "kind": "note",
                "title": "Tiêu chí chọn phương án",
                "content": "- Phù hợp với brief và đối tượng.\n- Không dùng claim hoặc nhận diện chưa được phép.\n- Có đủ khoảng trống cho thông tin cần đặt sau này.\n- Được người phụ trách tự review trước khi chuyển bước.",
            },
        ),
        "workboard": {
            "title": "Review art direction",
            "description": "Chốt direction và các giới hạn trước khi tiếp tục với phần hình ảnh.",
            "priority": "normal",
            "checklist": ("Điền mục đích và đối tượng", "Nêu giới hạn nhận diện", "Review tiêu chí chọn phương án"),
        },
    },
    {
        "key": "voice-script",
        "version": 1,
        "title": "Kịch bản và direction giọng nói",
        "summary": "Chuẩn bị script, nhịp thể hiện và điểm consent cần được xác nhận thủ công.",
        "outcome": "Một Project script có hướng dẫn review và không tạo audio.",
        "icon": "voice",
        "focus_areas": ("voice", "projects"),
        "goals": ("create_content", "build_brand"),
        "project": {
            "title": "Kịch bản giọng nói",
            "summary": "Tổ chức script và direction biểu đạt trong Workspace.",
            "objective": "Chuẩn bị bản script và review quyền sử dụng rõ ràng.",
        },
        "documents": (
            {
                "kind": "brief",
                "title": "Brief lời thoại",
                "content": "Mục tiêu nghe\n- Người nghe cần hiểu hoặc cảm nhận điều gì?\n\nNgữ cảnh\n- Ghi kênh, thời lượng dự kiến và đối tượng.\n\nĐiều cần tránh\n- Nêu các claim, giọng điệu hoặc tên riêng cần review.",
            },
            {
                "kind": "script",
                "title": "Kịch bản bản nháp",
                "content": "Mở đầu\n- Một câu rõ bối cảnh.\n\nNội dung chính\n- Chia câu ngắn theo nhịp dễ review.\n\nKết\n- Nêu hành động tiếp theo phù hợp.\n\nGhi chú nhịp\n- Đánh dấu nơi cần dừng hoặc nhấn ý.",
            },
            {
                "kind": "note",
                "title": "Consent và review",
                "content": "Người phụ trách tự xác nhận quyền sử dụng tên, nội dung và giọng nói trước khi dùng ở bất kỳ bước tiếp theo nào. Bản nháp này không phải consent hoặc xác nhận tự động.",
            },
        ),
        "workboard": {
            "title": "Review script giọng nói",
            "description": "Kiểm tra script, nhịp và quyền sử dụng trước khi tiếp tục.",
            "priority": "normal",
            "checklist": ("Rà soát wording và claim", "Xác nhận consent thủ công", "Chốt bản script cần biên tập tiếp"),
        },
    },
    {
        "key": "audio-brief",
        "version": 1,
        "title": "Brief âm thanh và quyền sử dụng",
        "summary": "Định hình mood, ngữ cảnh và tiêu chí quyền sử dụng cho audio/SFX.",
        "outcome": "Một Project brief âm thanh để review trước khi chọn tài sản hoặc công cụ.",
        "icon": "music",
        "focus_areas": ("music", "projects"),
        "goals": ("build_brand", "create_content"),
        "project": {
            "title": "Brief âm thanh Web",
            "summary": "Ghi mood, ngữ cảnh và tiêu chí quyền sử dụng âm thanh.",
            "objective": "Chuẩn bị brief âm thanh có checklist review rõ ràng.",
        },
        "documents": (
            {
                "kind": "brief",
                "title": "Brief âm thanh",
                "content": "Ngữ cảnh\n- Âm thanh sẽ hỗ trợ khoảnh khắc hoặc trải nghiệm nào?\n\nMood\n- Chọn ba từ mô tả cảm xúc và mức năng lượng.\n\nGiới hạn\n- Ghi các yếu tố cần tránh vì thương hiệu hoặc quyền sử dụng.",
            },
            {
                "kind": "prompt",
                "title": "Khung direction âm thanh",
                "content": "Nhịp và năng lượng\n- Nêu nhịp cảm nhận mong muốn.\n\nChất liệu\n- Liệt kê lớp âm thanh, nhạc cụ hoặc hiệu ứng theo cách mô tả.\n\nĐiểm chuyển\n- Ghi nơi cần lên hoặc hạ năng lượng.\n\nReview\n- Kiểm tra độ phù hợp và quyền sử dụng trước khi chọn tài sản.",
            },
            {
                "kind": "note",
                "title": "Checklist quyền sử dụng",
                "content": "- Ghi nguồn và điều kiện sử dụng khi đã có tài sản.\n- Không xem một brief là bằng chứng sở hữu hoặc cấp phép.\n- Rà soát claim, nhãn hiệu và phạm vi sử dụng trước khi phát hành.",
            },
        ),
        "workboard": {
            "title": "Review brief âm thanh",
            "description": "Hoàn thiện mood, giới hạn và tiêu chí quyền sử dụng của brief.",
            "priority": "normal",
            "checklist": ("Chốt mood và ngữ cảnh", "Liệt kê giới hạn thương hiệu", "Rà soát quyền sử dụng thủ công"),
        },
    },
    {
        "key": "subtitle-plan",
        "version": 1,
        "title": "Kế hoạch phụ đề và bản địa hóa",
        "summary": "Tổ chức mục tiêu ngôn ngữ, cue review và thuật ngữ cần kiểm tra.",
        "outcome": "Một Project planning text-only, không chạy nhận dạng, dịch hoặc lồng tiếng.",
        "icon": "subtitle",
        "focus_areas": ("subtitle", "projects"),
        "goals": ("create_content", "learn_workflows"),
        "project": {
            "title": "Kế hoạch phụ đề và ngôn ngữ",
            "summary": "Chuẩn bị cue review và quy ước ngôn ngữ trong Web Workspace.",
            "objective": "Xây một kế hoạch phụ đề có thể kiểm tra bằng người biên tập.",
        },
        "documents": (
            {
                "kind": "brief",
                "title": "Brief bản địa hóa",
                "content": "Ngôn ngữ nguồn và đích\n- Ghi rõ phạm vi người đọc.\n\nMục tiêu\n- Ưu tiên dễ đọc, đúng nghĩa hay nhất quán thương hiệu?\n\nThuật ngữ\n- Liệt kê từ cần được người biên tập kiểm tra kỹ.",
            },
            {
                "kind": "script",
                "title": "Khung cue review",
                "content": "Cue 01\n- Nội dung nguồn: …\n- Bản nháp: …\n- Ghi chú ngữ cảnh: …\n\nCue 02\n- Nội dung nguồn: …\n- Bản nháp: …\n- Ghi chú ngữ cảnh: …\n\nChỉ thêm cue sau khi nguồn đã được người dùng cung cấp và review.",
            },
            {
                "kind": "note",
                "title": "Nguyên tắc review ngôn ngữ",
                "content": "- Giữ nghĩa và ngữ cảnh trước khi rút gọn.\n- Kiểm tra tên riêng, số liệu và claim.\n- Đánh dấu đoạn chưa chắc chắn để người biên tập quyết định.\n- Bản kế hoạch không chứng minh thao tác ngôn ngữ nào đã chạy.",
            },
        ),
        "workboard": {
            "title": "Review kế hoạch phụ đề",
            "description": "Chuẩn bị ngôn ngữ, thuật ngữ và tiêu chí review trước khi tiếp tục.",
            "priority": "normal",
            "checklist": ("Chốt ngôn ngữ và mục tiêu", "Lập thuật ngữ cần kiểm tra", "Rà soát cue bằng người biên tập"),
        },
    },
    {
        "key": "document-qa",
        "version": 1,
        "title": "Intake tài liệu và review",
        "summary": "Chuẩn bị mục tiêu, danh sách nguồn và kiểm tra chất lượng trước thao tác tài liệu.",
        "outcome": "Một Project planning để tổ chức tài liệu mà không tự xử lý tệp.",
        "icon": "document",
        "focus_areas": ("documents", "projects"),
        "goals": ("organize_work", "learn_workflows"),
        "project": {
            "title": "Kế hoạch tài liệu Web",
            "summary": "Tổ chức intake và self-review cho một workflow tài liệu.",
            "objective": "Chuẩn bị phạm vi tài liệu, tiêu chí chất lượng và bước review.",
        },
        "documents": (
            {
                "kind": "brief",
                "title": "Brief tài liệu",
                "content": "Mục tiêu\n- Muốn tổ chức, đối chiếu hay chuẩn bị tài liệu cho việc gì?\n\nNguồn\n- Mô tả loại tài liệu và chủ sở hữu theo cách không chứa đường dẫn hoặc thông tin nhạy cảm.\n\nTiêu chí chất lượng\n- Nêu những trường, ngôn ngữ hoặc cấu trúc cần kiểm tra.",
            },
            {
                "kind": "content_pack",
                "title": "Checklist intake",
                "content": "1. Xác nhận quyền sử dụng và phạm vi.\n2. Ghi loại tài liệu và mục tiêu review.\n3. Nêu tiêu chí hoàn thành.\n4. Chọn thao tác phù hợp một cách riêng biệt khi đã sẵn sàng.\n5. Review kết quả ở bước có ownership rõ ràng.",
            },
            {
                "kind": "note",
                "title": "Rủi ro cần review",
                "content": "Không đưa mật khẩu, số thẻ, token, dữ liệu định danh nhạy cảm hoặc thông tin thanh toán vào Studio Documents. Ghi lại các điểm cần người phụ trách kiểm tra trước khi tiếp tục.",
            },
        ),
        "workboard": {
            "title": "Review intake tài liệu",
            "description": "Làm rõ phạm vi, quyền sử dụng và tiêu chí kiểm tra tài liệu.",
            "priority": "normal",
            "checklist": ("Xác định mục tiêu tài liệu", "Rà soát quyền và dữ liệu nhạy cảm", "Chọn bước review tiếp theo"),
        },
    },
    {
        "key": "operations-board",
        "version": 1,
        "title": "Bảng điều phối công việc",
        "summary": "Thiết lập mục tiêu vận hành, trách nhiệm review và một card công việc có checklist.",
        "outcome": "Một Project điều phối Web-native để theo dõi tiến độ có chủ đích.",
        "icon": "workboard",
        "focus_areas": ("automation", "projects"),
        "goals": ("run_operations", "organize_work"),
        "project": {
            "title": "Kế hoạch điều phối Web",
            "summary": "Thiết lập bối cảnh, trách nhiệm và nhịp review cho công việc.",
            "objective": "Điều phối một luồng công việc bằng record Web-owned rõ ràng.",
        },
        "documents": (
            {
                "kind": "brief",
                "title": "Brief vận hành",
                "content": "Mục tiêu vận hành\n- Nêu việc cần đạt và người chịu trách nhiệm review.\n\nPhạm vi\n- Ghi điều có thể xử lý trong Web Workspace.\n\nĐiểm kiểm tra\n- Xác định lúc nào cần dừng để tự review hoặc xin quyết định.",
            },
            {
                "kind": "note",
                "title": "Quy tắc điều phối",
                "content": "- Mỗi card cần một kết quả mong đợi có thể kiểm tra.\n- Không tự coi card hoàn thành khi checklist còn mở.\n- Ghi quyết định và rủi ro trong Project.\n- Không xem Workboard là hệ thống gửi thông báo bên ngoài.",
            },
        ),
        "workboard": {
            "title": "Thiết lập bảng điều phối",
            "description": "Biến brief thành card có checklist và xác định điểm review đầu tiên.",
            "priority": "high",
            "checklist": ("Xác định người review", "Ghi tiêu chí hoàn thành", "Chọn card tiếp theo theo ưu tiên"),
        },
    },
)

STARTER_KIT_BY_KEY = {str(kit["key"]): kit for kit in STARTER_KITS}


def _boundary(
    *,
    catalog_loaded: bool = False,
    installation_created: bool = False,
    project_created: bool = False,
    studio_documents_created: bool = False,
    workboard_items_created: bool = False,
) -> dict[str, bool | str]:
    """Make the local-only effect explicit in every response."""

    return {
        "execution": "web_native_starter_kit_install",
        "catalog_loaded": catalog_loaded,
        "installation_created": installation_created,
        "project_created": project_created,
        "studio_documents_created": studio_documents_created,
        "workboard_items_created": workboard_items_created,
        "bot_called": False,
        "bridge_called": False,
        "provider_called": False,
        "job_created": False,
        "wallet_mutated": False,
        "payment_started": False,
        "publish_action_created": False,
        "notification_sent": False,
        "asset_created": False,
        "delivery_created": False,
    }


def _require_enabled() -> None:
    if not starter_kits_enabled():
        raise HTTPException(
            status_code=503,
            detail="Starter Kits đang tạm dừng để bảo trì. WEBAPP_STARTER_KITS_ENABLED chưa được bật.",
        )


def _require_apply_enabled() -> None:
    _require_enabled()
    # A Starter Kit promises a complete, transparent set of Project + card
    # records. Do not create a partial Project if Workboard is in maintenance.
    if not workboard_enabled():
        raise HTTPException(
            status_code=503,
            detail="Starter Kits cần Workboard đang sẵn sàng để tạo bộ khởi đầu đầy đủ.",
        )


def _idempotency_key(value: str) -> str:
    normalized = str(value or "").strip()
    if not IDEMPOTENCY_PATTERN.fullmatch(normalized):
        raise ValueError("Idempotency key không hợp lệ")
    return normalized


def _idempotency_cutoff() -> str:
    return (datetime.now(timezone.utc) - IDEMPOTENCY_RETENTION).isoformat(timespec="seconds")


def _fingerprint(payload: dict[str, Any]) -> str:
    material = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(material).hexdigest()


def _kit_digest(kit: dict[str, Any]) -> str:
    material = {
        "key": kit["key"],
        "version": kit["version"],
        "project": kit["project"],
        "documents": kit["documents"],
        "workboard": kit["workboard"],
    }
    return _fingerprint(material)


def _guarded(message: str, error_code: str) -> dict[str, Any]:
    return envelope(
        False,
        message,
        data={"boundary": _boundary(catalog_loaded=True)},
        status_name="guarded",
        error_code=error_code,
    )


def _safe_profile(row: tuple[Any, ...] | None) -> dict[str, Any]:
    return copyfast_workspace_setup._safe_profile(row)


def _profile_row(conn: Any, account_id: str) -> tuple[Any, ...] | None:
    return conn.execute(
        """SELECT setup_state, role, goal, experience, focus_areas_json,
                  revision, completed_at, updated_at
           FROM web_workspace_setup_profiles WHERE account_id=?""",
        (account_id,),
    ).fetchone()


def _installation_public(row: tuple[Any, ...]) -> dict[str, Any]:
    return {
        "id": str(row[0]),
        "kit_key": str(row[1]),
        "kit_version": int(row[2]),
        "project_id": str(row[3]),
        "document_count": int(row[4]),
        "work_item_count": int(row[5]),
        "setup_profile_revision": int(row[6]),
        "created_at": str(row[7]),
    }


def _installations_for_account(conn: Any, account_id: str) -> dict[str, dict[str, Any]]:
    rows = conn.execute(
        """SELECT id, kit_key, kit_version, project_id, document_count,
                  work_item_count, setup_profile_revision, created_at
           FROM web_workspace_starter_kit_installs
           WHERE account_id=? ORDER BY created_at DESC, id DESC""",
        (account_id,),
    ).fetchall()
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        installation = _installation_public(tuple(row))
        key = installation["kit_key"]
        if key in STARTER_KIT_BY_KEY and key not in result:
            result[key] = installation
    return result


def _safe_text(value: Any, *, maximum: int) -> str:
    text = str(value or "")
    if not text or len(text) > maximum or TEXT_CONTROL_PATTERN.search(text):
        raise RuntimeError("Starter Kit catalog có text không hợp lệ")
    return text


def _validate_catalog() -> None:
    if len(STARTER_KITS) < 4:
        raise RuntimeError("Starter Kit catalog cần đủ lựa chọn Web-native")
    seen: set[str] = set()
    for kit in STARTER_KITS:
        key = str(kit.get("key") or "")
        if not KIT_KEY_PATTERN.fullmatch(key) or key in seen:
            raise RuntimeError("Starter Kit key không hợp lệ hoặc bị lặp")
        seen.add(key)
        version = kit.get("version")
        if not isinstance(version, int) or isinstance(version, bool) or version < 1:
            raise RuntimeError("Starter Kit version không hợp lệ")
        for field, maximum in (("title", 120), ("summary", 300), ("outcome", 300), ("icon", 32)):
            _safe_text(kit.get(field), maximum=maximum)
        focus = tuple(kit.get("focus_areas") or ())
        goals = tuple(kit.get("goals") or ())
        if not focus or not set(focus).issubset(copyfast_workspace_setup.FOCUS_AREAS):
            raise RuntimeError("Starter Kit focus area không hợp lệ")
        if not goals or not set(goals).issubset(copyfast_workspace_setup.GOALS):
            raise RuntimeError("Starter Kit goal không hợp lệ")
        project = kit.get("project") if isinstance(kit.get("project"), dict) else {}
        for field, maximum in (("title", 160), ("summary", 1_000), ("objective", 160)):
            _safe_text(project.get(field), maximum=maximum)
        documents = tuple(kit.get("documents") or ())
        if not 2 <= len(documents) <= 6:
            raise RuntimeError("Starter Kit cần từ hai đến sáu Studio Documents")
        for document in documents:
            if not isinstance(document, dict):
                raise RuntimeError("Studio Document Starter Kit không hợp lệ")
            if str(document.get("kind") or "") not in {"brief", "prompt", "caption", "script", "storyboard", "content_pack", "note"}:
                raise RuntimeError("Loại Studio Document Starter Kit không hợp lệ")
            _safe_text(document.get("title"), maximum=160)
            _safe_text(document.get("content"), maximum=12_000)
        workboard = kit.get("workboard") if isinstance(kit.get("workboard"), dict) else {}
        _safe_text(workboard.get("title"), maximum=180)
        _safe_text(workboard.get("description"), maximum=5_000)
        if str(workboard.get("priority") or "") not in copyfast_workboard.PRIORITIES:
            raise RuntimeError("Ưu tiên Workboard Starter Kit không hợp lệ")
        checklist = tuple(workboard.get("checklist") or ())
        if not 1 <= len(checklist) <= copyfast_workboard.MAX_CHECKLIST_PER_ITEM:
            raise RuntimeError("Checklist Starter Kit không hợp lệ")
        for item in checklist:
            _safe_text(item, maximum=360)


_validate_catalog()


def _rank_recommendations(profile: dict[str, Any], installations: dict[str, dict[str, Any]]) -> list[str]:
    focus = set(profile.get("focus_areas") or ())
    goal = str(profile.get("goal") or "")
    role = str(profile.get("role") or "")
    scored: list[tuple[int, int, str]] = []
    for index, kit in enumerate(STARTER_KITS):
        key = str(kit["key"])
        if key in installations:
            continue
        score = len(focus.intersection(set(kit["focus_areas"]))) * 10
        if goal in set(kit["goals"]):
            score += 5
        if role == "operator" and key == "operations-board":
            score += 3
        if role == "learner" and key == "project-foundation":
            score += 2
        scored.append((-score, index, key))
    scored.sort()
    return [key for _, _, key in scored[:3]]


def _catalog_item(
    kit: dict[str, Any],
    *,
    profile: dict[str, Any],
    installation: dict[str, Any] | None,
    workboard_ready: bool,
) -> dict[str, Any]:
    checklist = tuple(kit["workboard"]["checklist"])
    if installation:
        state = "installed"
    elif profile.get("setup_state") != "completed":
        state = "setup_required"
    elif not workboard_ready:
        state = "maintenance"
    else:
        state = "available"
    return {
        "key": str(kit["key"]),
        "version": int(kit["version"]),
        "title": str(kit["title"]),
        "summary": str(kit["summary"]),
        "outcome": str(kit["outcome"]),
        "icon": str(kit["icon"]),
        "focus_areas": list(kit["focus_areas"]),
        "record_counts": {
            "projects": 1,
            "documents": len(tuple(kit["documents"])),
            "work_items": 1,
            "checklist_items": len(checklist),
        },
        "state": state,
        "installation": installation or None,
    }


def _safe_receipt(response: dict[str, Any]) -> dict[str, Any]:
    """Persist only IDs/counts needed to replay a confirmed install safely."""

    if not isinstance(response, dict) or response.get("ok") is not True:
        return response
    source = response.get("data") if isinstance(response.get("data"), dict) else {}
    installation = source.get("installation") if isinstance(source.get("installation"), dict) else {}
    project_id = str(installation.get("project_id") or "")
    if not project_id:
        raise RuntimeError("Receipt Starter Kit thiếu Project ID")
    receipt = {
        "id": str(installation.get("id") or ""),
        "kit_key": str(installation.get("kit_key") or ""),
        "kit_version": int(installation.get("kit_version") or 0),
        "project_id": project_id,
        "document_count": int(installation.get("document_count") or 0),
        "work_item_count": int(installation.get("work_item_count") or 0),
        "setup_profile_revision": int(installation.get("setup_profile_revision") or 0),
        "created_at": str(installation.get("created_at") or ""),
    }
    return envelope(
        True,
        str(response.get("message") or "Đã tạo Starter Kit trong Web Workspace."),
        data={
            "installation": receipt,
            "boundary": _boundary(
                catalog_loaded=True,
                installation_created=True,
                project_created=True,
                studio_documents_created=True,
                workboard_items_created=True,
            ),
        },
        status_name="draft",
    )


def _idempotent(
    scope: str,
    account_id: str,
    key: str,
    request_fingerprint: str,
    operation: Callable[[Any], dict[str, Any]],
) -> dict[str, Any]:
    ensure_copyfast_schema()
    with transaction() as conn:
        conn.execute(
            "DELETE FROM web_idempotency WHERE scope LIKE ? AND created_at < ?",
            ("web-starter-kits:%", _idempotency_cutoff()),
        )
        existing = conn.execute(
            "SELECT response_json, request_fingerprint FROM web_idempotency WHERE scope=? AND key=?",
            (scope, key),
        ).fetchone()
        if existing:
            stored_fingerprint = str(existing[1] or "")
            if not stored_fingerprint or not hmac.compare_digest(stored_fingerprint, request_fingerprint):
                raise HTTPException(status_code=409, detail="Idempotency key đã được dùng cho yêu cầu khác")
            try:
                receipt = json.loads(str(existing[0]))
            except (TypeError, ValueError, json.JSONDecodeError) as exc:
                raise HTTPException(status_code=409, detail="Receipt Starter Kit không hợp lệ") from exc
            if not isinstance(receipt, dict):
                raise HTTPException(status_code=409, detail="Receipt Starter Kit không hợp lệ")
            return receipt
        count = conn.execute(
            "SELECT COUNT(*) FROM web_idempotency WHERE scope LIKE ?",
            (f"web-starter-kits:{account_id}:%",),
        ).fetchone()
        if int(count[0] or 0) >= MAX_IDEMPOTENCY_RECORDS_PER_ACCOUNT:
            return _guarded(
                "Kho receipt Starter Kits tạm thời đang đầy. Vui lòng thử lại sau.",
                "WEB_STARTER_KITS_IDEMPOTENCY_LIMIT",
            )
        response = operation(conn)
        if response.get("ok") is True:
            receipt = _safe_receipt(response)
            conn.execute(
                """INSERT INTO web_idempotency (scope, key, response_json, request_fingerprint, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (scope, key, json.dumps(receipt, ensure_ascii=False, separators=(",", ":")), request_fingerprint, utc_now()),
            )
            return receipt
        return response


def _insert_project_bundle(conn: Any, *, account_id: str, kit: dict[str, Any]) -> tuple[str, int]:
    project = kit["project"]
    project_id = str(uuid.uuid4())
    now = utc_now()
    conn.execute(
        """INSERT INTO web_projects (id, account_id, title, summary, objective, state, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, 'active', ?, ?)""",
        (project_id, account_id, project["title"], project["summary"], project["objective"], now, now),
    )
    documents = tuple(kit["documents"])
    for document in documents:
        document_id = str(uuid.uuid4())
        conn.execute(
            """INSERT INTO web_studio_documents
               (id, project_id, account_id, kind, title, content, revision, state, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, 1, 'active', ?, ?)""",
            (document_id, project_id, account_id, document["kind"], document["title"], document["content"], now, now),
        )
        conn.execute(
            """INSERT INTO web_studio_document_versions
               (id, document_id, account_id, revision, title, content, created_at)
               VALUES (?, ?, ?, 1, ?, ?, ?)""",
            (str(uuid.uuid4()), document_id, account_id, document["title"], document["content"], now),
        )
    return project_id, len(documents)


def _insert_workboard_seed(conn: Any, *, account_id: str, kit: dict[str, Any], project_id: str) -> tuple[str, int]:
    """Seed the same snapshot/event evidence as a normal Workboard card.

    This intentionally uses Workboard's narrow transaction helpers rather
    than its HTTP endpoint: the Project, documents, card and installation
    ledger must succeed or roll back together.
    """

    active_count = conn.execute(
        "SELECT COUNT(*) FROM web_workboard_items WHERE account_id=? AND state!='archived'",
        (account_id,),
    ).fetchone()
    if int(active_count[0] or 0) >= copyfast_workboard.MAX_ITEMS_PER_ACCOUNT:
        raise ValueError("WEB_STARTER_KITS_WORKBOARD_LIMIT")
    specification = kit["workboard"]
    payload = copyfast_workboard.ItemPayload.model_validate(
        {
            "title": specification["title"],
            "description": specification["description"],
            "priority": specification["priority"],
            "due_at": None,
            "references": [{"ref_type": "project", "ref_id": project_id}],
            "checklist": [{"body": item, "is_done": False} for item in specification["checklist"]],
        }
    )
    if not copyfast_workboard._references_are_owned(conn, account_id=account_id, references=payload.references):
        raise RuntimeError("Starter Kit Project reference không thuộc account hiện tại")
    item_id = str(uuid.uuid4())
    now = utc_now()
    conn.execute(
        """INSERT INTO web_workboard_items
           (id, account_id, title, description, priority, due_at, state, revision, created_at, updated_at, archived_at)
           VALUES (?, ?, ?, ?, ?, NULL, 'backlog', 1, ?, ?, NULL)""",
        (item_id, account_id, payload.title, payload.description, payload.priority, now, now),
    )
    copyfast_workboard._write_references(conn, item_id=item_id, account_id=account_id, references=payload.references)
    for ordinal, entry in enumerate(payload.checklist, start=1):
        conn.execute(
            """INSERT INTO web_workboard_checklist_items
               (id, item_id, account_id, ordinal, body, is_done, state, revision, completed_at, created_at, updated_at, archived_at)
               VALUES (?, ?, ?, ?, ?, 0, 'active', 1, NULL, ?, ?, NULL)""",
            (str(uuid.uuid4()), item_id, account_id, ordinal, entry.body, now, now),
        )
    item = copyfast_workboard._refresh_item(conn, item_id=item_id, account_id=account_id)
    rows = copyfast_workboard._checklist_rows(conn, item_id=item_id, account_id=account_id, include_archived=True)
    for row in rows:
        copyfast_workboard._insert_checklist_version(conn, row=row, account_id=account_id)
    copyfast_workboard._insert_item_version(conn, item=item, account_id=account_id, checklist=rows)
    copyfast_workboard._event(
        conn,
        account_id=account_id,
        item_id=item_id,
        entity_type="item",
        action="starter_kit_seeded",
        item_revision=1,
    )
    return item_id, len(rows)


class StarterKitApplyRequest(BaseModel):
    """A compact, strict confirmation receipt; kit content stays server-side."""

    model_config = ConfigDict(extra="forbid", strict=True)

    kit_version: StrictInt = Field(ge=1, le=1_000_000)
    expected_setup_revision: StrictInt = Field(ge=0, le=MAX_REVISION)
    confirmed: StrictBool
    idempotency_key: str = Field(min_length=12, max_length=160)

    @field_validator("confirmed")
    @classmethod
    def validate_confirmed(cls, value: bool) -> bool:
        if value is not True:
            raise ValueError("Cần xác nhận rõ ràng trước khi tạo Starter Kit")
        return value

    @field_validator("idempotency_key")
    @classmethod
    def validate_idempotency_key(cls, value: str) -> str:
        return _idempotency_key(value)


@router.get("")
async def list_starter_kits(account: dict = Depends(require_account)) -> dict[str, Any]:
    """Return a bounded catalog and signed-owner installation projection."""

    _require_enabled()
    account_id = str(account["id"])
    ensure_copyfast_schema()
    with read_transaction() as conn:
        profile = _safe_profile(_profile_row(conn, account_id))
        installations = _installations_for_account(conn, account_id)
    workboard_ready = workboard_enabled()
    return envelope(
        True,
        "Đã tải Starter Kits cho Web Workspace.",
        data={
            "catalog_version": CATALOG_VERSION,
            "profile": profile,
            "kits": [
                _catalog_item(kit, profile=profile, installation=installations.get(str(kit["key"])), workboard_ready=workboard_ready)
                for kit in STARTER_KITS
            ],
            "recommended_keys": _rank_recommendations(profile, installations),
            "workboard_ready": workboard_ready,
            "boundary": _boundary(catalog_loaded=True),
        },
        status_name="read_only",
    )


@router.post("/{kit_key}/apply")
async def apply_starter_kit(
    kit_key: str,
    payload: StarterKitApplyRequest,
    request: Request,
    account: dict = Depends(require_csrf),
) -> dict[str, Any]:
    """Atomically install one explicit, Web-only starter into owner records."""

    _require_apply_enabled()
    normalized_key = str(kit_key or "").strip().lower()
    kit = STARTER_KIT_BY_KEY.get(normalized_key)
    if not kit:
        raise HTTPException(status_code=404, detail="Starter Kit không tồn tại")
    if payload.kit_version != int(kit["version"]):
        raise HTTPException(status_code=409, detail="Starter Kit đã được cập nhật. Hãy tải lại trước khi tiếp tục.")
    account_id = str(account["id"])
    scope = f"web-starter-kits:{account_id}:apply"
    fingerprint = _fingerprint(
        {
            "kit_key": normalized_key,
            "kit_version": payload.kit_version,
            "expected_setup_revision": payload.expected_setup_revision,
            "confirmed": payload.confirmed,
        }
    )

    def operation(conn: Any) -> dict[str, Any]:
        profile = _safe_profile(_profile_row(conn, account_id))
        if profile["setup_state"] != "completed":
            return _guarded(
                "Hãy hoàn tất Workspace Setup trước khi tạo Starter Kit theo cách làm việc của bạn.",
                "WEB_STARTER_KITS_SETUP_REQUIRED",
            )
        if profile["revision"] != payload.expected_setup_revision:
            raise HTTPException(status_code=409, detail="Workspace Setup đã thay đổi ở nơi khác. Hãy tải lại Starter Kits trước khi tiếp tục.")
        existing = conn.execute(
            """SELECT id, kit_key, kit_version, project_id, document_count,
                      work_item_count, setup_profile_revision, created_at
               FROM web_workspace_starter_kit_installs WHERE account_id=? AND kit_key=?""",
            (account_id, normalized_key),
        ).fetchone()
        if existing:
            return _guarded(
                "Starter Kit này đã có trong Workspace của bạn. Hãy mở Project đã tạo để tiếp tục.",
                "WEB_STARTER_KITS_ALREADY_INSTALLED",
            )
        active_count = conn.execute(
            "SELECT COUNT(*) FROM web_workboard_items WHERE account_id=? AND state!='archived'",
            (account_id,),
        ).fetchone()
        if int(active_count[0] or 0) >= copyfast_workboard.MAX_ITEMS_PER_ACCOUNT:
            return _guarded(
                "Workboard của bạn đã đạt giới hạn card đang hoạt động. Không tạo bộ khởi đầu dở dang.",
                "WEB_STARTER_KITS_WORKBOARD_LIMIT",
            )
        project_id, document_count = _insert_project_bundle(conn, account_id=account_id, kit=kit)
        try:
            _work_item_id, _checklist_count = _insert_workboard_seed(conn, account_id=account_id, kit=kit, project_id=project_id)
        except ValueError as exc:
            if str(exc) == "WEB_STARTER_KITS_WORKBOARD_LIMIT":
                # Raising rolls back the whole transaction; the parent then
                # converts this explicit capacity condition below.
                raise HTTPException(status_code=409, detail="Workboard đã đạt giới hạn card đang hoạt động") from exc
            raise
        installation_id = str(uuid.uuid4())
        now = utc_now()
        digest = _kit_digest(kit)
        conn.execute(
            """INSERT INTO web_workspace_starter_kit_installs
               (id, account_id, kit_key, kit_version, kit_digest, setup_profile_revision,
                project_id, document_count, work_item_count, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?)""",
            (
                installation_id,
                account_id,
                normalized_key,
                int(kit["version"]),
                digest,
                int(profile["revision"]),
                project_id,
                document_count,
                now,
            ),
        )
        _record_audit(
            conn,
            account_id=account_id,
            canonical_user_id=str(account.get("canonical_user_id") or "") or None,
            action="web.starter_kit.apply",
            request_id=_request_id(request),
            target=installation_id,
            outcome="ok",
            detail="web-native starter kit installed",
        )
        installation = {
            "id": installation_id,
            "kit_key": normalized_key,
            "kit_version": int(kit["version"]),
            "project_id": project_id,
            "document_count": document_count,
            "work_item_count": 1,
            "setup_profile_revision": int(profile["revision"]),
            "created_at": now,
        }
        return envelope(
            True,
            "Đã tạo Project, Studio Documents và Workboard checklist từ Starter Kit. Đây là bản nháp Web để bạn tiếp tục review.",
            data={
                "installation": installation,
                "boundary": _boundary(
                    catalog_loaded=True,
                    installation_created=True,
                    project_created=True,
                    studio_documents_created=True,
                    workboard_items_created=True,
                ),
            },
            status_name="draft",
        )

    return _idempotent(scope, account_id, payload.idempotency_key, fingerprint, operation)
