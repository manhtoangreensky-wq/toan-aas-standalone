from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from db import now_text

router = APIRouter()


WORKFLOW_CONFIGS: dict[str, dict[str, str]] = {
    "video_trend": {"title": "Video theo trend", "category": "video", "guard": "render_video"},
    "video_ai": {"title": "Video AI chân thật", "category": "video", "guard": "render_video"},
    "storyboard_i2v": {"title": "Kịch bản -> Ảnh -> Video", "category": "storyboard", "guard": "render_video"},
    "frame_video": {"title": "Ghép ảnh thành video", "category": "frame_video", "guard": "local_worker"},
    "self_filming": {"title": "Tự quay & Đổi cảnh AI", "category": "video", "guard": "planning"},
    "long_story_video": {"title": "Phim AI nhiều cảnh", "category": "cinematic", "guard": "planning"},
    "storyboard_prompt": {"title": "Storyboard + Prompt", "category": "storyboard", "guard": "planning"},
    "reference_video": {"title": "Video / Kênh mẫu", "category": "reference", "guard": "planning"},
    "video_idea": {"title": "Ý tưởng video", "category": "video", "guard": "planning"},
    "motion_prompt": {"title": "Prompt / Chuyển động", "category": "motion", "guard": "planning"},
    "local_video_edit": {"title": "Chỉnh sửa video local", "category": "local_edit", "guard": "local_worker"},
    "tts": {"title": "Tạo giọng đọc (TTS)", "category": "voice", "guard": "provider"},
    "stt": {"title": "Bóc băng (STT)", "category": "transcript", "guard": "provider"},
    "voice_mix": {"title": "Ghép Voice", "category": "local_edit", "guard": "local_worker"},
    "music_prompt": {"title": "Tạo Prompt Nhạc", "category": "music", "guard": "planning"},
    "music_library": {"title": "Kho nhạc nền", "category": "music", "guard": "planning"},
    "sfx": {"title": "Hiệu ứng SFX", "category": "music", "guard": "planning"},
    "media_library": {"title": "Kho Media cá nhân", "category": "storage", "guard": "storage"},
    "music_to_video": {"title": "Ghép nhạc vào Video", "category": "local_edit", "guard": "local_worker"},
    "meta_prompt": {"title": "Prompt Meta AI", "category": "meta", "guard": "planning"},
    "caption_hashtag": {"title": "Caption / Hashtag", "category": "caption", "guard": "planning"},
    "content_idea": {"title": "Ý tưởng Content", "category": "content", "guard": "planning"},
    "image_video_prompt": {"title": "Prompt Ảnh/Video", "category": "image_video", "guard": "planning"},
    "post_pack": {"title": "Gói đăng bài", "category": "post_pack", "guard": "planning"},
    "prompt_library": {"title": "Kho Prompt mẫu", "category": "library", "guard": "planning"},
    "temporary_media": {"title": "Lưu Media tạm", "category": "storage", "guard": "storage"},
    "translation_hub": {"title": "Dịch Ngôn ngữ", "category": "translate", "guard": "provider"},
    "video_dub": {"title": "Dịch / Lồng tiếng Video", "category": "dub", "guard": "provider"},
    "quick_image": {"title": "Tạo ảnh nhanh", "category": "image", "guard": "render_image"},
    "image_prompt": {"title": "Tạo prompt ảnh", "category": "image", "guard": "planning"},
    "image_edit": {"title": "Chỉnh sửa ảnh", "category": "image_edit", "guard": "local_worker"},
    "ai_image_edit": {"title": "Chỉnh sửa AI", "category": "image_edit", "guard": "provider"},
    "support_ticket": {"title": "Tạo ticket hỗ trợ", "category": "support", "guard": "support"},
    "support_payment": {"title": "Hướng dẫn nạp Xu", "category": "support_payment", "guard": "support"},
    "support_video": {"title": "Hướng dẫn tạo video", "category": "support_video", "guard": "support"},
    "note_create": {"title": "Tạo ghi chú", "category": "storage", "guard": "storage"},
    "note_list": {"title": "Ghi chú đã lưu", "category": "storage", "guard": "storage"},
    "note_reminder": {"title": "Nhắc hẹn", "category": "storage", "guard": "storage"},
    "document_store": {"title": "Lưu tài liệu", "category": "storage", "guard": "storage"},
    "note_search": {"title": "Tìm ghi chú", "category": "storage", "guard": "storage"},
    "account_combo": {"title": "Combo của tôi", "category": "account", "guard": "account"},
    "account_gift": {"title": "Nhận thưởng", "category": "account", "guard": "account"},
    "account_referral": {"title": "Mời bạn bè", "category": "account", "guard": "account"},
}


SUGGESTION_BANKS: dict[str, list[str]] = {
    "video": [
        "Before/After giải quyết vấn đề",
        "POV tình huống đời thường",
        "3 mẹo nhanh có sản phẩm làm giải pháp",
        "Cinematic product reveal",
        "UGC review tự nhiên",
        "Ad hook bán hàng trực tiếp",
        "Mini tutorial 3 bước",
        "Founder story ngắn",
        "So sánh lỗi thường gặp",
    ],
    "storyboard": [
        "Quảng cáo sản phẩm 5 cảnh",
        "Tutorial 3 bước",
        "Câu chuyện cảm xúc 15 giây",
        "Affiliate demo có CTA",
        "Faceless narration",
        "Before/After transition",
        "Bóc tách pain point",
        "Hero product close-up",
    ],
    "cinematic": [
        "Hành trình thay đổi bản thân",
        "Cơ hội thành công",
        "Ký ức và thời gian",
        "Luxury black-and-white",
        "Tương lai công nghệ",
        "Gia đình và cảm xúc",
        "Cú twist ở cuối",
        "Nhân vật vượt qua áp lực",
    ],
    "motion": [
        "Slow push-in vào chủ thể",
        "Orbit quanh sản phẩm",
        "Handheld UGC nhẹ",
        "Match cut theo thời gian",
        "Pan ngang giới thiệu bối cảnh",
        "Macro close-up chi tiết",
        "Reveal từ bóng sáng",
        "Camera follow hành động",
    ],
    "image": [
        "Logo/branding tối giản",
        "Ảnh sản phẩm studio",
        "Banner social media",
        "Lifestyle quảng cáo",
        "Cinematic hero image",
        "Ảnh công nghệ/AI",
        "Poster ưu đãi sạch",
        "Ảnh nhân vật đại diện thương hiệu",
    ],
    "image_edit": [
        "Crop 9:16 và làm nét",
        "Thêm text/logo gọn",
        "Chỉnh màu sạch hơn",
        "Resize cho quảng cáo",
        "Nâng chi tiết sản phẩm",
        "Tách nền/chủ thể",
        "Làm sáng ảnh bán hàng",
        "Chuẩn hóa ảnh marketplace",
    ],
    "caption": [
        "Caption bán hàng mềm",
        "Caption kể chuyện",
        "Caption list 3 lợi ích",
        "Caption phản biện nỗi đau",
        "Caption UGC đời thường",
        "Caption ưu đãi ngắn",
        "Caption chuyên gia giải thích",
        "Caption gọi inbox nhẹ",
    ],
    "content": [
        "Hook gây tò mò",
        "Kịch bản 15 giây",
        "Ý tưởng series 5 bài",
        "Bài giải thích cho người mới",
        "Bài case study ngắn",
        "Bài so sánh trước/sau",
        "Bài checklist thực hành",
        "Bài xử lý phản đối",
    ],
    "meta": [
        "Prompt ảnh Meta AI",
        "Prompt video Meta AI",
        "Prompt quảng cáo sản phẩm",
        "Prompt UGC creator",
        "Prompt cinematic",
        "Prompt banner",
        "Prompt carousel",
        "Prompt avatar thương hiệu",
    ],
    "music": [
        "Piano cinematic",
        "Ambient luxury",
        "Electronic future",
        "Upbeat viral",
        "SFX chuyển cảnh nhẹ",
        "Lo-fi sạch cho voiceover",
        "Corporate tech beat",
        "Emotional strings",
    ],
    "translate": [
        "Dịch văn bản 2 chiều",
        "Dịch tài liệu ngắn",
        "Dịch transcript",
        "Dịch hội thoại",
        "Dịch voice/audio",
        "Dịch phụ đề",
        "Tóm tắt đa ngôn ngữ",
        "Chuẩn hóa tone bản dịch",
    ],
    "dub": [
        "Tạo phụ đề",
        "Dịch phụ đề",
        "Lồng tiếng",
        "Phụ đề + lồng tiếng",
        "Giữ giọng gốc tham khảo",
        "Voiceover mới",
        "Chia segment lời thoại",
        "Kiểm tra sync phụ đề",
    ],
    "support": [
        "Hướng dẫn nạp Xu",
        "Tư vấn gói video",
        "Kiểm tra lỗi thanh toán",
        "Hỏi cách tạo ảnh",
        "Hỏi cách tạo video",
        "Liên hệ admin",
        "Hỏi chính sách hoàn Xu",
        "Hỏi gói dung lượng",
    ],
    "support_payment": [
        "PayOS tự động",
        "Nạp thủ công qua QR",
        "USDT quốc tế",
        "ZaloPay/MoMo thủ công",
        "Lịch sử nạp",
        "Ưu đãi nội địa",
        "Sai nội dung chuyển khoản",
        "Chưa thấy cộng Xu",
    ],
    "support_video": [
        "Prompt -> Video AI",
        "Video theo trend",
        "Storyboard nhiều cảnh",
        "Phụ đề/lồng tiếng",
        "Gói 200/300/400",
        "Kiểm tra trạng thái job",
        "Chọn gói phù hợp",
        "Tạo video từ ảnh",
    ],
    "storage": [
        "Lưu ảnh tham chiếu",
        "Lưu video mẫu",
        "Tạo tags media",
        "Dọn file cũ",
        "Gói dung lượng",
        "Lưu kế hoạch sản xuất",
        "Lưu tài liệu nội bộ",
        "Tìm lại ghi chú",
    ],
    "local_edit": [
        "Cắt video ngắn",
        "Ghép nhạc",
        "Thêm phụ đề",
        "Resize dọc 9:16",
        "Ghép voice",
        "Nén xuất bản",
        "Cắt đoạn lỗi",
        "Chèn logo góc",
    ],
    "frame_video": [
        "Slideshow fade nhẹ",
        "Ken Burns zoom",
        "Pan ngang sản phẩm",
        "Random motion",
        "Ảnh + voice",
        "Ảnh + nhạc nền",
        "Ảnh sản phẩm carousel",
        "Reels giới thiệu nhanh",
    ],
    "reference": [
        "Học cấu trúc hook",
        "Học nhịp dựng",
        "Học caption/hashtag",
        "Học CTA kênh",
        "Học shot style",
        "Đóng gói bài đăng",
        "Tách format kênh mẫu",
        "Lập lịch nội dung",
    ],
    "post_pack": [
        "Post bán hàng",
        "Post giáo dục",
        "Post affiliate",
        "Post UGC",
        "Post ra mắt sản phẩm",
        "Post remarketing",
        "Post social proof",
        "Post checklist",
    ],
    "library": [
        "Prompt logo",
        "Prompt banner",
        "Prompt video quảng cáo",
        "Prompt phim AI",
        "Prompt voice",
        "Prompt caption",
        "Prompt edit ảnh",
        "Prompt phân tích kênh",
    ],
    "transcript": [
        "Bóc băng cuộc gọi",
        "Bóc băng video",
        "Tóm tắt audio",
        "Trích ý chính",
        "Tạo subtitle draft",
        "Dịch transcript",
        "Biên tập lời thoại",
        "Tạo minutes họp",
    ],
    "account": [
        "Xem combo/lượt còn lại",
        "Nhập gift code",
        "Lấy link giới thiệu",
        "Xem lịch sử quyền lợi",
        "Kiểm tra hạng thành viên",
        "Liên hệ admin",
        "Xem lịch sử Xu",
        "Kiểm tra gói tháng",
    ],
}


class WorkflowSuggestionReq(BaseModel):
    workflow_key: str
    topic: str = ""
    round: int = 0
    count: int = 3


def _bank(category: str) -> list[str]:
    return SUGGESTION_BANKS.get(category) or SUGGESTION_BANKS["content"]


def _guard_detail(guard: str) -> dict[str, Any]:
    details = {
        "planning": ("READY_PLANNING", "Miễn phí: tạo kế hoạch/prompt/caption, không gọi provider và không trừ Xu."),
        "render_video": ("GUARDED_RENDER_VIDEO", "Render video thật cần chọn gói, báo giá, xác nhận và job provider riêng."),
        "render_image": ("GUARDED_RENDER_IMAGE", "Tạo ảnh thật cần chọn tier, báo giá, xác nhận và job provider riêng."),
        "local_worker": ("WAITING_LOCAL_WORKER", "Tác vụ local/ffmpeg chỉ chạy khi worker an toàn sẵn sàng."),
        "provider": ("WAITING_PROVIDER_SMOKE", "Tác vụ provider chỉ mở sau khi smoke pass và có màn xác nhận giá."),
        "storage": ("READY_STORAGE_GUARD", "Lưu trữ dùng quota miễn phí 50MB và gói mua thêm nếu cần."),
        "support": ("READY_SUPPORT_DRAFT", "CSKH trả lời trước, ticket chỉ dùng để lưu và báo admin khi cần."),
        "account": ("READY_ACCOUNT_VIEW", "Tài khoản chỉ đọc/lập kế hoạch quyền lợi, không tự cộng/trừ Xu."),
    }
    status, message = details.get(guard, details["planning"])
    return {"status": status, "message": message}


def build_workflow_output(cfg: dict[str, str], topic: str, idea: str) -> str:
    topic = (topic or "sản phẩm/dịch vụ của bạn").strip()
    category = cfg["category"]
    title = f"{cfg['title']} - {idea}"

    if category in {"image", "image_edit", "image_video"}:
        return f"""{title}

Chủ đề: {topic}

Prompt chính:
{topic}, {idea}, bố cục rõ chủ thể, ánh sáng sạch, màu sắc chuyên nghiệp, chi tiết tự nhiên, không méo chữ/logo, không watermark.

Tỉ lệ đề xuất:
- 9:16 cho TikTok/Reels/Shorts
- 1:1 cho post vuông
- 16:9 cho banner/video ngang

Quality control:
- Giữ chủ thể rõ nét
- Không thêm chữ thừa
- Không biến dạng sản phẩm/người
- Nếu tạo ảnh thật: chọn tier giá và xác nhận trước khi trừ Xu"""

    if category in {"caption", "content", "post_pack", "meta"}:
        return f"""{title}

Chủ đề: {topic}

Hook:
Bạn đang bỏ lỡ điều này nếu chưa thử {topic}.

Nội dung chính:
- Nêu vấn đề người xem đang gặp
- Đưa {topic} như giải pháp rõ ràng
- Chứng minh bằng lợi ích cụ thể

Caption mẫu:
{topic} không cần phức tạp. Bắt đầu từ một bước nhỏ, đo kết quả, rồi tối ưu dần.

Hashtag:
#toanaas #aiworkflow #contentmarketing #automation

CTA:
Lưu lại để dùng khi cần và nhắn TOAN AAS nếu muốn biến ý tưởng này thành ảnh/video."""

    if category in {"music", "voice", "transcript"}:
        return f"""{title}

Nội dung: {topic}

Gợi ý xử lý:
- Mood: {idea}
- Nhịp: rõ lời, không lấn voice
- Voice: tự nhiên, tốc độ vừa
- Nếu là TTS/STT thật: cần upload/text đầu vào, báo Xu và xác nhận trước khi gọi provider

Prompt nhạc/voice:
{idea} cho nội dung {topic}, sạch, hiện đại, phù hợp video ngắn, không quá ồn, hỗ trợ voiceover rõ."""

    if category in {"translate", "dub"}:
        return f"""{title}

Nội dung: {topic}

Pipeline đề xuất:
1. Nhận text/audio/video/tài liệu
2. Chọn ngôn ngữ gốc và ngôn ngữ đích
3. Tạo bản dịch hoặc phụ đề nháp
4. Nếu lồng tiếng: chọn giọng, báo Xu, xác nhận
5. Xử lý và gửi kết quả

Guard:
Tác vụ dài hoặc cần STT/TTS/provider phải báo giá trước, chưa tự trừ Xu."""

    if category.startswith("support"):
        return f"""{title}

Câu hỏi: {topic}

Trả lời nhanh:
TOAN AAS sẽ hướng dẫn trực tiếp trước. Nếu cần admin kiểm tra, hệ thống mới lưu ticket để theo dõi.

Gợi ý xử lý:
- Nạp Xu: dùng PayOS tự động hoặc QR/thủ công theo hướng dẫn trong app
- Video: đi theo chuỗi prompt -> add-on -> giá -> xác nhận -> job -> kết quả
- Nếu gặp lỗi: gửi ảnh màn hình/tình huống, hệ thống lưu ticket cho admin

Trạng thái:
Web app đang chuẩn hóa ticket/CSKH tự động, chưa tự tạo ticket từ modal này."""

    if category == "account":
        return f"""{title}

Mục cần xử lý: {idea}

Trạng thái web app:
- Ví Xu đọc từ API tài khoản
- Lịch sử giao dịch đọc từ portal history
- Combo/gift/referral đang được chuẩn hóa thành API riêng

Nguyên tắc:
Không tự cộng/trừ Xu ở màn này. Mọi quyền lợi/gift/referral phải đi qua API kiểm tra và audit log."""

    if category in {"frame_video", "local_edit", "storage"}:
        return f"""{title}

Chủ đề/tài sản: {topic}

Kế hoạch:
- Kiểm tra file đầu vào
- Xác định tỉ lệ, thời lượng, hiệu ứng
- Kiểm tra local worker/storage quota
- Báo giá nếu xử lý thật
- Xác nhận trước khi chạy job

Guard:
Không render nặng trên Railway nếu worker/local tool chưa sẵn sàng. Web app chưa trừ Xu ở bước planning này."""

    return f"""{title}

Chủ đề: {topic}

Big idea:
Biến {topic} thành một câu chuyện rõ vấn đề, rõ giải pháp và có điểm nhớ.

Hook 3 giây:
Điều gì xảy ra nếu {topic} giúp bạn tiết kiệm một nửa thời gian?

Script 15s:
0-3s: Nêu vấn đề quen thuộc.
3-8s: Cho thấy {topic} xuất hiện như giải pháp.
8-12s: Hiển thị kết quả/bằng chứng.
12-15s: CTA nhẹ.

Storyboard:
1. Close-up vấn đề hoặc bối cảnh.
2. Sản phẩm/dịch vụ xuất hiện rõ chủ thể.
3. Chuyển động camera {idea.lower()}.
4. Before/after hoặc kết quả.
5. CTA sạch, không quá bán hàng.

Prompt video:
{topic}, {idea}, cinematic but realistic, clean lighting, stable subject identity, natural motion, no warped text, no watermark, 9:16 vertical short video.

Prompt ảnh khung chính:
{topic}, hero frame, clear subject, clean background, premium commercial lighting, realistic details.

Bước tiếp theo:
Copy kế hoạch này, hoặc lưu vào kho để dùng tiếp trong bước tạo ảnh/video/voice."""


@router.get("/catalog")
async def workflow_catalog() -> dict[str, Any]:
    return {
        "success": True,
        "workflows": WORKFLOW_CONFIGS,
        "generated_at": now_text(),
    }


@router.post("/suggestions")
async def workflow_suggestions(data: WorkflowSuggestionReq) -> dict[str, Any]:
    cfg = WORKFLOW_CONFIGS.get(data.workflow_key)
    if not cfg:
        return {"success": False, "message": "Workflow chưa được cấu hình."}

    count = max(1, min(int(data.count or 3), 3))
    bank = _bank(cfg["category"])
    offset = (max(int(data.round or 0), 0) * count) % len(bank)
    suggestions = []
    for idx in range(count):
        idea = bank[(offset + idx) % len(bank)]
        suggestions.append(
            {
                "index": idx + 1,
                "title": idea,
                "output": build_workflow_output(cfg, data.topic, idea),
            }
        )

    return {
        "success": True,
        "workflow_key": data.workflow_key,
        "title": cfg["title"],
        "category": cfg["category"],
        "guard": cfg["guard"],
        "guard_detail": _guard_detail(cfg["guard"]),
        "suggestions": suggestions,
        "generated_at": now_text(),
    }
