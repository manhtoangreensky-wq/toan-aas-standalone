"""Web-native Media Factory blueprint derived from the frozen Telegram Bot.

The Bot's ``/media_factory <topic>`` command returns a deterministic content
and production *plan*.  It does not perform live trend search, generate a
video, publish a post, or call a provider for public customers.  This module
ports that useful planning grammar to a signed Web session without pretending
that any external media capability is available.

Every result is transient.  It deliberately does not write a Project, brief,
asset, audit event or browser draft; it never calls the Bot/Core Bridge,
providers, social platforms, wallet/Xu, PayOS, jobs, publishing or delivery.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, StrictStr, field_validator

from copyfast_auth import envelope, require_csrf
from copyfast_db import media_factory_enabled
from copyfast_trend_research import LANGUAGES, POLICY_GUARD_PATTERNS, _topic


router = APIRouter(prefix="/api/v1/media-factory", tags=["Web Media Factory"])


def _require_enabled() -> None:
    if not media_factory_enabled():
        raise HTTPException(
            status_code=503,
            detail="Media Factory Blueprint đang tạm dừng để bảo trì. WEBAPP_MEDIA_FACTORY_ENABLED chưa được bật.",
        )


class MediaFactoryRequest(BaseModel):
    """Exact transient contract for the Bot-derived Media Factory blueprint.

    The historical Bot accepted only a topic.  The optional language selector
    is presentation-only: it never changes into a source URL, model/provider,
    project, asset, job, price, payment, publish or delivery request.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    topic: StrictStr
    language: StrictStr = "vi"

    @field_validator("topic")
    @classmethod
    def validate_topic(cls, value: str) -> str:
        return _topic(value)

    @field_validator("language")
    @classmethod
    def validate_language(cls, value: str) -> str:
        language = str(value).strip().lower()
        if language not in LANGUAGES:
            raise ValueError("Ngôn ngữ Media Factory chỉ hỗ trợ vi hoặc en")
        return language


def _boundary() -> dict[str, Any]:
    """Return the explicit no-execution boundary required by the Portal."""

    return {
        "execution": "web_native_deterministic_media_factory_blueprint_only",
        "input_persisted": False,
        "live_search_called": False,
        "search_provider_called": False,
        "social_platform_called": False,
        "source_content_fetched": False,
        "source_content_stored": False,
        "provider_called": False,
        "bot_called": False,
        "job_created": False,
        "wallet_mutated": False,
        "payment_started": False,
        "asset_saved": False,
        "media_output_created": False,
        "publish_action_created": False,
        "fact_checked": False,
        "trend_claim_verified": False,
        "rights_verified": False,
    }


def _policy_guard(topic: str) -> dict[str, Any] | None:
    if not any(pattern.search(topic) for pattern in POLICY_GUARD_PATTERNS):
        return None
    return envelope(
        False,
        "Chủ đề cần được viết lại theo hướng sáng tạo nguyên bản, không reup/copy không có quyền, né watermark/DRM/Content ID, mạo danh, clone hoặc deepfake người thật.",
        data=_boundary(),
        status_name="guarded",
        error_code="WEB_MEDIA_FACTORY_POLICY_GUARD",
    )


def _angle(topic: str, title: str, reason: str, *, language: str) -> dict[str, str]:
    if language == "en":
        return {
            "title": title,
            "reason": reason,
            "hook": f"If this problem keeps happening with {topic}, watch this before you decide.",
            "format": "Everyday scene → problem → short checklist → balanced solution → self-directed CTA.",
            "visual_direction": "Use real-life situations, naturally placed product/solution context and before/after framing without exaggeration.",
            "caption_cta": "Save this to compare later; read the details only if it fits your actual need.",
            "policy_risk": "Do not promise outcomes, disparage competitors, reuse unlicensed footage or make unsupported claims.",
        }
    return {
        "title": title,
        "reason": reason,
        "hook": f"Nếu bạn đang gặp vấn đề này với {topic}, xem nhanh trước khi quyết định.",
        "format": "Cảnh đời thường → vấn đề → checklist ngắn → giải pháp cân bằng → CTA để người xem tự chọn.",
        "visual_direction": "Dùng tình huống thật, sản phẩm/giải pháp xuất hiện tự nhiên và before/after mềm, không phóng đại.",
        "caption_cta": "Lưu lại để so sánh sau; chỉ xem chi tiết nếu phù hợp nhu cầu thật của bạn.",
        "policy_risk": "Không hứa chắc kết quả, bôi xấu đối thủ, reup tư liệu không có quyền hoặc đưa claim chưa kiểm chứng.",
    }


def _compose_blueprint(payload: MediaFactoryRequest) -> dict[str, Any]:
    """Port the useful planning sequence in Bot ``fallback_media_factory_pack``.

    This is intentionally a structured version of the Bot's static text pack,
    rather than a synthetic live-trend result or a task sent to an execution
    engine.  The fields stay bounded so the browser can validate every value
    before it is rendered.
    """

    topic = payload.topic
    if payload.language == "en":
        angles = [
            _angle(topic, "A recurring 30-second pain point", "Turn a small repeated problem into a practical before/after hook.", language="en"),
            _angle(topic, "A comparison before buying", "Give viewers three criteria so they can choose for themselves.", language="en"),
            _angle(topic, "One common mistake", "Open with a frequent error, then offer a balanced, non-absolute correction.", language="en"),
            _angle(topic, "A time-saving habit", "Use an everyday quick-tip format with a save-for-later CTA.", language="en"),
            _angle(topic, "Who this is and is not for", "State clear fit and non-fit cases to build trust.", language="en"),
        ]
        source_rights = [
            "Use material you own, licensed stock, public-domain work or sources with documented permission.",
            "Do not reupload another creator's video or bypass watermark, DRM or Content ID controls.",
            "Verify rights, people, brands, facts and claims before using a reference outside this plan.",
            "Create a new script, image direction, voice direction and video plan from the insight instead of copying the source.",
        ]
        storyboard = [
            {"step": "01", "title": "Everyday situation", "detail": "Show the familiar decision or friction without overclaiming."},
            {"step": "02", "title": "Decision criteria", "detail": "Name the two or three checks that make the choice clearer."},
            {"step": "03", "title": "Balanced option", "detail": "Place the product or solution as one option with concrete context."},
            {"step": "04", "title": "Self-directed CTA", "detail": "Invite the viewer to save, compare or read details before deciding."},
        ]
        image_scenes = [
            {"name": "Opening hook", "purpose": "A person notices the problem in an everyday setting."},
            {"name": "Everyday context", "purpose": "A home, desk or small-business setting with natural details."},
            {"name": "Product in use", "purpose": "The product appears naturally rather than as a catalogue cutout."},
            {"name": "Balanced comparison", "purpose": "Show two states without exaggerated transformations."},
            {"name": "Thumbnail", "purpose": "A clear subject and authentic expression, with no unreliable text."},
            {"name": "Closing frame", "purpose": "A calm satisfied moment that does not feel like a hard sell."},
        ]
        review_checklist = [
            "Verify each factual, medical, financial, pricing or performance claim before use.",
            "Confirm usage rights for every reference, image, voice, person, brand and source.",
            "Check the script, caption, CTA and on-screen text for clarity and local relevance.",
            "Keep a human approval step before any real render, delivery or publication.",
        ]
        unavailable = [
            "Live trend data or social-platform search is not included.",
            "Real video/image/audio generation and provider previews are not included.",
            "Customer social-account connection and auto-publishing are not included.",
            "No Bot job, wallet/Xu charge, PayOS payment, asset delivery or webhook is created.",
        ]
        title = f"Media Factory Blueprint: {topic}"
        scope = "Content and production planning for you to review and self-publish; no media generation or publishing execution."
        video_direction = {
            "scene": f"A clean, rights-aware everyday commercial scene about {topic} with one clear subject.",
            "camera_movement": "A gentle 10% push-in with mild handheld texture; keep the subject readable.",
            "motion": "Natural, subtle movement with no dramatic or misleading transformation.",
            "lighting": "Soft, clean light with depth; avoid harsh artificial studio glare.",
            "style": "Realistic lifestyle, clean commercial look, natural colour, not over-polished.",
            "duration": "5–12 seconds for a short prompt; 12–20 seconds for a review-style edit plan.",
            "negative_prompt": "warped product, deformed hands, broken text, fake logo, watermark, flicker, unnatural motion, exaggerated claims",
        }
        source_keywords = [topic, f"{topic} review", f"{topic} common mistakes", f"{topic} before buying"]
    else:
        angles = [
            _angle(topic, "Nỗi đau lặp lại 30 giây mỗi ngày", "Biến vấn đề nhỏ lặp lại hằng ngày thành hook before/after thực tế.", language="vi"),
            _angle(topic, "So sánh trước khi mua", "Đưa ra ba tiêu chí để người xem tự chọn phương án phù hợp.", language="vi"),
            _angle(topic, "Một sai lầm thường gặp", "Mở bằng lỗi phổ biến, sau đó đưa giải pháp mềm và không claim quá đà.", language="vi"),
            _angle(topic, "Mẹo tiết kiệm thời gian", "Dùng format mẹo nhanh, cảnh đời thường và CTA lưu lại để xem sau.", language="vi"),
            _angle(topic, "Hợp với ai, không hợp với ai", "Nêu rõ trường hợp phù hợp và không phù hợp để tăng độ tin cậy.", language="vi"),
        ]
        source_rights = [
            "Chỉ dùng tư liệu tự có, public domain, licensed stock hoặc nội dung có quyền sử dụng được xác nhận.",
            "Không reup video người khác, không né watermark, DRM hoặc Content ID.",
            "Tự kiểm tra quyền cho mọi reference, người, thương hiệu, fact và claim trước khi dùng bên ngoài.",
            "Tạo script, image direction, voice direction và video plan mới từ insight thay vì sao chép tác phẩm nguồn.",
        ]
        storyboard = [
            {"step": "01", "title": "Tình huống đời thường", "detail": "Nêu bối cảnh và điểm vướng quen thuộc, không phóng đại vấn đề."},
            {"step": "02", "title": "Tiêu chí ra quyết định", "detail": "Chỉ ra hai hoặc ba điểm cần kiểm tra để người xem tự đánh giá."},
            {"step": "03", "title": "Giải pháp có ngữ cảnh", "detail": "Đặt sản phẩm hoặc giải pháp như một lựa chọn cân bằng, có lý do cụ thể."},
            {"step": "04", "title": "CTA để tự chọn", "detail": "Mời người xem lưu lại, so sánh hoặc đọc thêm trước khi quyết định."},
        ]
        image_scenes = [
            {"name": "Ảnh hook mở đầu", "purpose": "Nhân vật nhận ra vấn đề trong một tình huống đời thường."},
            {"name": "Ảnh bối cảnh", "purpose": "Không gian nhà, bàn làm việc hoặc cửa hàng nhỏ có chi tiết tự nhiên."},
            {"name": "Ảnh sản phẩm trong ngữ cảnh", "purpose": "Sản phẩm xuất hiện tự nhiên, không giống ảnh catalogue cắt nền."},
            {"name": "Ảnh so sánh mềm", "purpose": "Hai trạng thái khác nhau nhưng không biến đổi hay hứa hẹn quá đà."},
            {"name": "Ảnh thumbnail", "purpose": "Chủ thể rõ, cảm xúc thật và không dùng text dễ sai lệch."},
            {"name": "Ảnh kết thúc", "purpose": "Khoảnh khắc hài lòng nhẹ, không tạo cảm giác quảng cáo quá lố."},
        ]
        review_checklist = [
            "Kiểm tra lại mọi fact, claim y tế/tài chính/giá/hiệu năng trước khi dùng.",
            "Xác nhận quyền dùng của mọi reference, ảnh, voice, người, thương hiệu và nguồn.",
            "Đọc lại script, caption, CTA và text trên màn hình để tránh hiểu sai hoặc lỗi địa phương hóa.",
            "Giữ bước phê duyệt của con người trước khi render, giao hoặc đăng bất kỳ nội dung thật nào.",
        ]
        unavailable = [
            "Không có live trend data hoặc tìm kiếm trực tiếp trên nền tảng xã hội.",
            "Không có tạo ảnh/video/audio thật, provider preview hoặc render ngầm.",
            "Không có liên kết tài khoản mạng xã hội hoặc auto-publish cho khách.",
            "Không tạo Bot job, Xu/wallet charge, PayOS payment, asset delivery hoặc webhook.",
        ]
        title = f"Media Factory Blueprint: {topic}"
        scope = "Lập kế hoạch nội dung và sản xuất để bạn review/tự đăng; không tạo media hay thực thi publish."
        video_direction = {
            "scene": f"Một cảnh đời thường/quảng cáo nhẹ về {topic}, chủ thể rõ, bối cảnh sạch và có quyền sử dụng.",
            "camera_movement": "Slow push-in 10%, handheld nhẹ, giữ chủ thể rõ và hậu cảnh blur vừa phải.",
            "motion": "Chuyển động tự nhiên, nhẹ và không tạo biến đổi hoặc kết quả gây hiểu lầm.",
            "lighting": "Ánh sáng mềm, sạch, có chiều sâu; tránh ánh sáng studio giả quá gắt.",
            "style": "Realistic lifestyle, clean commercial look, màu tự nhiên, không over-polished.",
            "duration": "5–12 giây cho prompt ngắn hoặc 12–20 giây cho video review theo kế hoạch dựng.",
            "negative_prompt": "warped product, deformed hands, broken text, fake logo, watermark, flicker, unnatural motion, exaggerated claims",
        }
        source_keywords = [topic, f"{topic} review", f"{topic} lỗi thường gặp", f"{topic} trước khi mua"]

    return {
        "title": title,
        "topic": topic,
        "language": payload.language,
        "mode": "content_only_manual_review",
        "scope": scope,
        "trend_angles": angles,
        "source_keywords": source_keywords,
        "source_rights": source_rights,
        "storyboard": storyboard,
        "image_scenes": image_scenes,
        "video_direction": video_direction,
        "review_checklist": review_checklist,
        "unavailable_capabilities": unavailable,
        "next_workflows": [
            {"label": "Trend Research Plan", "route": "/trend-research", "purpose": "Tự kiểm tra nguồn, nhu cầu và originality trước khi mở rộng brief."},
            {"label": "Content Prompt Pack", "route": "/content/prompt-pack", "purpose": "Biên tập angle thành hook, caption, script hoặc content text."},
            {"label": "Image Prompt Composer", "route": "/image/prompt-composer", "purpose": "Soạn direction visual nguyên bản trước khi chọn engine riêng."},
            {"label": "Storyboard Composer", "route": "/video-studio/storyboard-composer", "purpose": "Chuyển câu chuyện thành nhịp cảnh có thể review."},
            {"label": "Video Prompt Planner", "route": "/video-studio/prompt-planner", "purpose": "Lập prompt/video plan text-only trước khi có runtime được cấp."},
            {"label": "Voice Direction Composer", "route": "/voice-studio/direction-composer", "purpose": "Chuẩn bị hướng đọc và kiểm tra consent mà không tạo audio."},
        ],
    }


@router.post("/blueprint")
async def create_media_factory_blueprint(
    payload: MediaFactoryRequest,
    account: dict = Depends(require_csrf),
):
    """Return the Bot-derived Media Factory plan without any execution side effect."""

    _require_enabled()
    del account
    guarded = _policy_guard(payload.topic)
    if guarded:
        return guarded
    return envelope(
        True,
        "Đã tạo Media Factory Blueprint để review và tiếp tục ở các workspace riêng. Không có live search, provider, Bot, job, thanh toán, media output hoặc publish nào được tạo.",
        data={"blueprint": _compose_blueprint(payload), **_boundary()},
        status_name="draft",
    )


class CreativeFlowRequest(BaseModel):
    """Exact, transient Web equivalent of Bot ``/creative_flow <idea>``."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    idea: StrictStr
    language: StrictStr = "vi"

    @field_validator("idea")
    @classmethod
    def validate_idea(cls, value: str) -> str:
        return _topic(value)

    @field_validator("language")
    @classmethod
    def validate_language(cls, value: str) -> str:
        language = str(value).strip().lower()
        if language not in LANGUAGES:
            raise ValueError("Ngôn ngữ Creative Flow chỉ hỗ trợ vi hoặc en")
        return language


def _creative_boundary() -> dict[str, Any]:
    boundary = _boundary()
    boundary["execution"] = "web_native_deterministic_creative_flow_only"
    return boundary


def _creative_policy_guard(idea: str) -> dict[str, Any] | None:
    if not any(pattern.search(idea) for pattern in POLICY_GUARD_PATTERNS):
        return None
    return envelope(
        False,
        "Ý tưởng cần được viết lại theo hướng sáng tạo nguyên bản, không reup/copy không có quyền, né watermark/DRM/Content ID, mạo danh, clone hoặc deepfake người thật.",
        data=_creative_boundary(),
        status_name="guarded",
        error_code="WEB_CREATIVE_FLOW_POLICY_GUARD",
    )


def _compose_creative_flow(payload: CreativeFlowRequest) -> dict[str, Any]:
    """Structure the eight deterministic sections of Bot ``creative_flow_text``."""

    idea = payload.idea
    if payload.language == "en":
        return {
            "title": f"Creative Flow: {idea}",
            "idea": idea,
            "language": "en",
            "mode": "template_only_manual_review",
            "script_framework": [
                "Open with a 2-second hook.",
                "Name the customer's real problem or decision point.",
                "Introduce the product or solution in context.",
                "State one concrete primary benefit without a guarantee.",
                "Close with a clear, self-directed call to action.",
            ],
            "image_prompt": f"Realistic product/lifestyle image for {idea}, clean commercial lighting, natural background, high detail, no watermark.",
            "image_story_direction": f"Use a rights-cleared reference image, then build a shot pack around: {idea}.",
            "music_search": "Search brief: upbeat product review — verify licensing before use.",
            "sfx_search": "Search brief: whoosh transition or click — verify licensing before use.",
            "caption_hashtags": "Write one short caption, one primary benefit and a clear CTA. Draft hashtag set: #toanaas #review #shortvideo #contentcreator",
            "cta": "Message for advice, see more product details, or save the video to use later.",
            "next_workflows": [
                {"label": "Image Prompt Composer", "route": "/image/prompt-composer", "purpose": "Refine an original visual direction without generating an image."},
                {"label": "Storyboard Composer", "route": "/video-studio/storyboard-composer", "purpose": "Turn the short script into reviewable scenes."},
                {"label": "Music Prompt Composer", "route": "/media-workspace/music-prompt-composer", "purpose": "Write a music direction without searching or previewing a catalog."},
                {"label": "Content Prompt Pack", "route": "/content/prompt-pack", "purpose": "Expand caption, hook and CTA text for review."},
            ],
            "review_checklist": [
                "Verify rights for every reference image, voice, sound effect, brand and source before use.",
                "Check all factual, medical, financial, performance and price claims before publishing.",
                "Keep a human review step before any real media generation, delivery or publication.",
            ],
        }
    return {
        "title": f"Creative Flow: {idea}",
        "idea": idea,
        "language": "vi",
        "mode": "template_only_manual_review",
        "script_framework": [
            "Mở bằng hook 2 giây đầu.",
            "Nêu vấn đề hoặc điểm ra quyết định thật của khách.",
            "Đưa sản phẩm/giải pháp vào đúng ngữ cảnh.",
            "Nêu một lợi ích chính cụ thể, không hứa chắc kết quả.",
            "Kết bằng CTA rõ ràng để người xem tự chọn.",
        ],
        "image_prompt": f"Realistic product/lifestyle image for {idea}, clean commercial lighting, natural background, high detail, no watermark.",
        "image_story_direction": f"Dùng ảnh tham chiếu có quyền sử dụng, sau đó lập shot pack theo ý tưởng: {idea}.",
        "music_search": "Brief tìm nhạc: upbeat product review — cần tự kiểm tra giấy phép trước khi dùng.",
        "sfx_search": "Brief tìm SFX: whoosh transition hoặc click — cần tự kiểm tra giấy phép trước khi dùng.",
        "caption_hashtags": "Viết caption ngắn, một lợi ích chính và CTA rõ. Bộ hashtag nháp: #toanaas #review #shortvideo #contentcreator",
        "cta": "Nhắn tin để nhận tư vấn, xem thêm chi tiết sản phẩm hoặc lưu video để dùng sau.",
        "next_workflows": [
            {"label": "Image Prompt Composer", "route": "/image/prompt-composer", "purpose": "Tinh chỉnh visual direction nguyên bản mà không tạo ảnh."},
            {"label": "Storyboard Composer", "route": "/video-studio/storyboard-composer", "purpose": "Chuyển kịch bản ngắn thành các cảnh có thể review."},
            {"label": "Music Prompt Composer", "route": "/media-workspace/music-prompt-composer", "purpose": "Viết music direction mà không tìm hoặc preview catalogue."},
            {"label": "Content Prompt Pack", "route": "/content/prompt-pack", "purpose": "Mở rộng caption, hook và CTA text để review."},
        ],
        "review_checklist": [
            "Xác nhận quyền dùng cho mọi ảnh tham chiếu, voice, SFX, thương hiệu và nguồn trước khi dùng.",
            "Kiểm tra mọi fact, claim y tế/tài chính/hiệu năng/giá trước khi publish.",
            "Giữ bước review của con người trước khi tạo media, giao hoặc đăng nội dung thật.",
        ],
    }


@router.post("/creative-flow")
async def create_creative_flow(
    payload: CreativeFlowRequest,
    account: dict = Depends(require_csrf),
):
    """Return the Bot-derived Creative Flow template without external work."""

    _require_enabled()
    del account
    guarded = _creative_policy_guard(payload.idea)
    if guarded:
        return guarded
    return envelope(
        True,
        "Đã tạo Creative Flow template để review và tiếp tục ở workspace riêng. Không có provider, Bot, job, thanh toán, media output hoặc publish nào được tạo.",
        data={"flow": _compose_creative_flow(payload), **_creative_boundary()},
        status_name="draft",
    )


class StoryVideoPlanRequest(BaseModel):
    """Exact request for the prompt-only Bot story-video/motion guidance."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    topic: StrictStr
    language: StrictStr = "vi"

    @field_validator("topic")
    @classmethod
    def validate_topic(cls, value: str) -> str:
        return _topic(value)

    @field_validator("language")
    @classmethod
    def validate_language(cls, value: str) -> str:
        language = str(value).strip().lower()
        if language not in LANGUAGES:
            raise ValueError("Ngôn ngữ Story Video Planner chỉ hỗ trợ vi hoặc en")
        return language


def _story_boundary() -> dict[str, Any]:
    boundary = _boundary()
    boundary["execution"] = "web_native_deterministic_story_video_plan_only"
    return boundary


def _story_policy_guard(topic: str) -> dict[str, Any] | None:
    if not any(pattern.search(topic) for pattern in POLICY_GUARD_PATTERNS):
        return None
    return envelope(
        False,
        "Chủ đề truyện/cảnh cần được viết lại theo hướng hợp lệ và nguyên bản, không reup/copy không có quyền, né watermark/DRM/Content ID, mạo danh, clone hoặc deepfake người thật.",
        data=_story_boundary(),
        status_name="guarded",
        error_code="WEB_STORY_VIDEO_POLICY_GUARD",
    )


def _compose_story_plan(payload: StoryVideoPlanRequest) -> dict[str, Any]:
    """Combine Bot story-video workflow and prompt-only motion direction.

    The Bot exposes the workflow and motion prompt as neighbouring public
    commands. The Web version makes their hand-off explicit in one transient,
    structured plan while retaining the same no-render/no-publish boundary.
    """

    topic = payload.topic
    if payload.language == "en":
        return {
            "title": f"Story Video Plan: {topic}",
            "topic": topic,
            "language": "en",
            "mode": "prompt_only_manual_review",
            "story_steps": [
                "Choose material you wrote, own, have licensed, are permitted to use, or that is genuinely public domain.",
                "Shape an episode arc: opening, escalation, resolution and an optional cliffhanger.",
                "Draft a natural narration script in your own words.",
                "Create one original image direction for each planned scene.",
                "Create a motion direction for each scene; it remains prompt-only.",
                "Prepare a lawful new voice-over direction with consent and source checks.",
                "Draft caption, hashtag and CTA for self-publishing after human review.",
            ],
            "motion_prompt": f"Animate a cinematic vertical story scene about {topic}, slow camera push-in, subtle character movement, natural atmosphere, soft lighting, emotional but not exaggerated, no watermark, no text artifacts, 12 seconds.",
            "camera_movement": "Slow push-in, slight parallax, gentle handheld feel; keep the main subject stable and readable.",
            "style": "Storytelling, realistic or semi-realistic only when appropriate to the lawful source, clean composition and safe content.",
            "output_status": "prompt_only_no_real_video",
            "next_workflows": [
                {"label": "Storyboard Composer", "route": "/video-studio/storyboard-composer", "purpose": "Build reviewable scene rhythm and visual beats."},
                {"label": "Video Prompt Planner", "route": "/video-studio/prompt-planner", "purpose": "Expand a text-only motion direction before a separately approved runtime."},
                {"label": "Voice Direction Composer", "route": "/voice-studio/direction-composer", "purpose": "Prepare lawful narration direction without creating audio."},
                {"label": "Content Prompt Pack", "route": "/content/prompt-pack", "purpose": "Draft caption, hooks and CTA in a separate text workflow."},
            ],
            "review_checklist": [
                "Verify the story/source rights, public-domain status or license before using it.",
                "Do not reupload/crawl protected stories or videos, bypass watermark/DRM/Content ID, or imitate real people without permission.",
                "Review fact, claim, consent, brand and audience suitability before any real render, delivery or self-publish step.",
            ],
        }
    return {
        "title": f"Story Video Plan: {topic}",
        "topic": topic,
        "language": "vi",
        "mode": "prompt_only_manual_review",
        "story_steps": [
            "Chọn truyện/nội dung tự viết, tự sở hữu, public domain, licensed hoặc được chủ sở hữu cho phép dùng.",
            "Chia tập theo mở đầu, cao trào, kết thúc và cliffhanger nếu thật sự cần.",
            "Viết script kể chuyện tự nhiên bằng lời của bạn.",
            "Soạn image direction nguyên bản cho từng cảnh dự kiến.",
            "Soạn motion direction cho từng cảnh; bước này vẫn chỉ là prompt.",
            "Chuẩn bị voice-over mới hợp lệ với consent và kiểm tra nguồn.",
            "Soạn caption, hashtag và CTA để tự đăng sau khi con người review.",
        ],
        "motion_prompt": f"Animate a cinematic vertical story scene about {topic}, slow camera push-in, subtle character movement, natural atmosphere, soft lighting, emotional but not exaggerated, no watermark, no text artifacts, 12 seconds.",
        "camera_movement": "Slow push-in, slight parallax, gentle handheld feel, giữ chủ thể chính ổn định và dễ đọc.",
        "style": "Storytelling, realistic hoặc semi-realistic phù hợp với nguồn hợp lệ, bố cục sạch và nội dung an toàn.",
        "output_status": "prompt_only_no_real_video",
        "next_workflows": [
            {"label": "Storyboard Composer", "route": "/video-studio/storyboard-composer", "purpose": "Xây nhịp cảnh và visual beat có thể review."},
            {"label": "Video Prompt Planner", "route": "/video-studio/prompt-planner", "purpose": "Mở rộng motion direction text-only trước khi có runtime được cấp riêng."},
            {"label": "Voice Direction Composer", "route": "/voice-studio/direction-composer", "purpose": "Chuẩn bị hướng narration hợp lệ mà không tạo audio."},
            {"label": "Content Prompt Pack", "route": "/content/prompt-pack", "purpose": "Soạn caption, hook và CTA trong workflow text riêng."},
        ],
        "review_checklist": [
            "Xác nhận quyền với truyện/nguồn, trạng thái public domain hoặc license trước khi dùng.",
            "Không reup/crawl truyện hay video vi phạm bản quyền, né watermark/DRM/Content ID hoặc mô phỏng người thật khi chưa có quyền.",
            "Rà soát fact, claim, consent, thương hiệu và mức phù hợp với người xem trước khi render, giao hoặc tự đăng thật.",
        ],
    }


@router.post("/story-video-plan")
async def create_story_video_plan(
    payload: StoryVideoPlanRequest,
    account: dict = Depends(require_csrf),
):
    """Return story workflow plus motion direction without media execution."""

    _require_enabled()
    del account
    guarded = _story_policy_guard(payload.topic)
    if guarded:
        return guarded
    return envelope(
        True,
        "Đã tạo Story Video Plan prompt-only để review. Không có provider, Bot, job, thanh toán, video output hoặc publish nào được tạo.",
        data={"plan": _compose_story_plan(payload), **_story_boundary()},
        status_name="draft",
    )
