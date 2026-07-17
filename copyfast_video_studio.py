"""Private, Web-native Video Production Studio.

This router owns planning metadata only: a video brief, ordered scene board,
self-review lifecycle and immutable revision history for the signed Web
account.  It deliberately does not accept media, source URLs, engine
configuration, delivery records or any execution request.  A saved plan is
never evidence that a video exists.
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
from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, StrictStr, field_validator

from copyfast_auth import _record_audit, _request_id, envelope, require_account, require_csrf
from copyfast_db import ensure_copyfast_schema, read_transaction, transaction, utc_now, video_studio_enabled


router = APIRouter(prefix="/api/v1/video-studio", tags=["Web Video Production Studio"])

PLAN_STATES = frozenset({"draft", "review", "approved", "archived"})
WRITABLE_PLAN_STATES = frozenset({"draft", "review"})
PLAN_FORMATS = frozenset({"short_form", "product_demo", "explainer", "ugc", "campaign", "custom"})
ASPECT_RATIOS = frozenset({"9:16", "16:9", "1:1", "4:5", "custom"})
SCENE_TYPES = frozenset({"hook", "problem", "solution", "product", "proof", "cta", "transition", "custom"})
SCENE_STATES = frozenset({"active", "archived"})

# The prompt planner is deliberately narrower than the durable Video Studio.
# It adapts only the Bot's deterministic prompt-direction vocabulary for four
# text-only flows.  It must never become an accidental media/provider adapter.
VIDEO_PROMPT_PLANNER_MODES = frozenset({"prompt_to_video", "trend_video", "storyboard_video", "long_script"})
VIDEO_PROMPT_PLANNER_PLATFORMS = frozenset({"custom", "tiktok", "reels", "shorts", "youtube", "facebook"})
VIDEO_PROMPT_PLANNER_RATIOS = frozenset({"9:16", "16:9", "1:1", "4:5"})
VIDEO_PROMPT_PLANNER_DETAIL_LEVELS = frozenset({"quick", "director", "viral", "stability_first", "cinematic"})
VIDEO_PROMPT_PLANNER_LANGUAGES = frozenset({"vi", "en"})

# This compact catalog is intentionally shared with the portal contract.  Its
# directions are reimplemented from the Bot's static video_prompt_quality.py
# tables, rather than importing Bot code or any execution integration.
VIDEO_PROMPT_PLANNER_STYLE_PACKS: dict[str, dict[str, str]] = {
    "corporate_tech_commercial": {
        "label": "Corporate Tech Commercial",
        "mood": "clarity, trust and capability",
        "lighting": "clean neutral lighting with restrained brand accents",
        "camera": "smooth dolly, detail inserts and a clear team-wide composition",
        "audio": "modern corporate pulse with soft practical clicks",
        "negative": "avoid unreadable screen text and generic stock-video behavior",
    },
    "product_luxury_reveal": {
        "label": "Product Luxury Reveal",
        "mood": "premium desire and precise product detail",
        "lighting": "controlled studio key light with restrained rim highlights",
        "camera": "macro detail, slow orbit and a composed hero push-in",
        "audio": "luxury bass with tactile reveal details",
        "negative": "do not alter product shape, color, legitimate logo or packaging",
    },
    "tiktok_viral_product_demo": {
        "label": "TikTok Viral Product Demo",
        "mood": "fast, useful proof with a clear social hook",
        "lighting": "bright practical social lighting",
        "camera": "snap zoom, handheld detail and motivated quick cuts",
        "audio": "upbeat beat with restrained whoosh and click cues",
        "negative": "avoid exaggerated claims and unstable hands",
    },
    "ugc_review_style": {
        "label": "UGC Review Style",
        "mood": "honest first-person proof",
        "lighting": "natural window or phone-light direction",
        "camera": "stable handheld with close product inserts",
        "audio": "voice-first room ambience",
        "negative": "avoid false claims and over-polished stock appearance",
    },
    "documentary_premium": {
        "label": "Documentary Premium",
        "mood": "credible observation",
        "lighting": "natural available light",
        "camera": "stable handheld, wide context and detail inserts",
        "audio": "location ambience with a restrained score",
        "negative": "avoid staged reactions and artificial skin",
    },
    "emotional_storytelling": {
        "label": "Emotional Storytelling",
        "mood": "human memory and connection",
        "lighting": "soft natural golden light",
        "camera": "slow push-in, close detail and gentle handheld movement",
        "audio": "soft piano with intimate room tone",
        "negative": "avoid melodrama and artificial tears",
    },
    "app_saas_explainer": {
        "label": "App / SaaS Explainer",
        "mood": "simple understanding and utility",
        "lighting": "clean office light with screen-safe exposure",
        "camera": "over-shoulder framing, device macro and smooth push-in",
        "audio": "light electronic pulse and practical interface clicks",
        "negative": "avoid fabricated readable UI and impossible interactions",
    },
    "food_commercial": {
        "label": "Food Commercial",
        "mood": "freshness and appetite appeal",
        "lighting": "soft directional food lighting",
        "camera": "macro push-in, overhead detail and measured slow motion",
        "audio": "crisp kitchen ASMR with subtle music",
        "negative": "avoid synthetic texture and impossible liquid physics",
    },
}

VIDEO_PROMPT_PLANNER_ACTION_PACKS: dict[str, dict[str, str]] = {
    "product_spin_reveal": {
        "label": "Product Spin Reveal",
        "action": "the subject or product turns slowly into a stable hero angle",
        "camera": "macro orbit",
        "transition": "clean cut",
        "audio": "tactile click and restrained bass accent",
    },
    "logo_product_hero_shot": {
        "label": "Logo / Product Hero Shot",
        "action": "finish with a stable product or legitimate logo hero frame",
        "camera": "slow final push-in",
        "transition": "clean settle",
        "audio": "brand sting",
    },
    "slow_push_in": {
        "label": "Slow Push-in",
        "action": "hold natural action while the visual focus gradually increases",
        "camera": "slow push-in",
        "transition": "clean cut",
        "audio": "subtle room tone",
    },
    "before_after_wipe": {
        "label": "Before / After Wipe",
        "action": "show matched framing before and after one credible visible change",
        "camera": "locked camera",
        "transition": "split wipe",
        "audio": "snap and restrained result chime",
    },
    "phone_screen_transition": {
        "label": "Phone Screen Transition",
        "action": "move through a clean device-screen composition into the next scene",
        "camera": "push toward device",
        "transition": "screen portal cut",
        "audio": "tap and digital whoosh",
    },
    "walk_through_reveal": {
        "label": "Walk-through Reveal",
        "action": "move through foreground cover into a clear reveal",
        "camera": "gimbal tracking",
        "transition": "foreground wipe",
        "audio": "footsteps with a soft riser",
    },
    "ai_dashboard_reveal": {
        "label": "Workflow Reveal",
        "action": "reveal an original, non-readable workflow concept through clear visual milestones",
        "camera": "over-shoulder push-in",
        "transition": "screen-to-world cut",
        "audio": "interface clicks and a confirmation tone",
    },
    "customer_pain_to_solution": {
        "label": "Pain to Solution",
        "action": "show a credible pain point, practical solution and a restrained result",
        "camera": "problem close-up to a wider relief frame",
        "transition": "motivated match cut",
        "audio": "tension-to-relief sound arc",
    },
}

VIDEO_PROMPT_PLANNER_AUDIO_MODES: dict[str, dict[str, str]] = {
    "modern_electronic": {"label": "Modern Electronic", "direction": "modern electronic bed with a soft riser and clean transition cues"},
    "cinematic_light": {"label": "Light Cinematic", "direction": "light cinematic score with a restrained rise and clean final resolve"},
    "asmr_only": {"label": "ASMR Only", "direction": "no background music; use crisp practical ASMR and location cues"},
    "voiceover_first": {"label": "Voiceover First", "direction": "voiceover-first timing; keep any music low and make action support narration"},
    "voiceover_vi": {"label": "Vietnamese Voiceover", "direction": "Vietnamese voiceover-first timing with natural pacing and clear consonants"},
    "emotional_piano": {"label": "Emotional Piano", "direction": "soft emotional piano, intimate room tone and gentle final resolve"},
    "office_ambience": {"label": "Office Ambience", "direction": "clean office room tone with subtle keyboard/click cues and low music"},
    "silent": {"label": "Silent Planning", "direction": "no soundtrack; retain only visual timing notes for later editorial review"},
}

# Cinematic Ad Concept Composer is a second, deliberately request-only
# translation of the Bot's static ``adconcept`` menu.  These tables reproduce
# only its broad creative choices; they are not a provider/model catalog and
# do not describe an execution workflow.
CINEMATIC_AD_MESSAGE_THEMES: dict[str, dict[str, Any]] = {
    "memory": {"label": {"vi": "Ký ức & khoảnh khắc", "en": "Memory & meaningful moments"}, "angle": {"vi": "một khoảnh khắc đời thường đáng được trân trọng", "en": "an everyday moment worth noticing"}},
    "success": {"label": {"vi": "Bước tiến & cơ hội", "en": "Progress & opportunity"}, "angle": {"vi": "một bước tiến nhỏ nhưng có ý nghĩa", "en": "a small but meaningful next step"}},
    "confidence": {"label": {"vi": "Tự tin để bắt đầu", "en": "Confidence to begin"}, "angle": {"vi": "chuyển từ do dự sang tự tin", "en": "a shift from hesitation to confidence"}},
    "time_save": {"label": {"vi": "Nhẹ việc, tiết kiệm thời gian", "en": "Time-saving, lighter work"}, "angle": {"vi": "một cách làm gọn gàng và dễ theo dõi hơn", "en": "a clearer, lighter way to work"}},
    "luxury": {"label": {"vi": "Trải nghiệm cao cấp", "en": "Elevated experience"}, "angle": {"vi": "một trải nghiệm được chăm chút và có chủ đích", "en": "a considered, elevated experience"}},
    "future": {"label": {"vi": "Công nghệ & tương lai", "en": "Technology & future"}, "angle": {"vi": "một trải nghiệm hiện đại, dễ hiểu", "en": "a modern experience that remains human and clear"}},
    "family": {"label": {"vi": "Gia đình & sự quan tâm", "en": "Family & care"}, "angle": {"vi": "một hành động quan tâm trong nhịp sống hằng ngày", "en": "an act of care in everyday life"}},
    "before_after": {"label": {"vi": "Trước & sau có kiểm chứng", "en": "Reviewable before & after"}, "angle": {"vi": "một thay đổi thị giác cần được kiểm tra trước khi công bố", "en": "a visual change that needs review before publication"}},
    "custom": {"label": {"vi": "Thông điệp tùy chỉnh", "en": "Custom message"}, "angle": {"vi": "thông điệp do người dùng cung cấp", "en": "the message supplied by the author"}},
}

CINEMATIC_AD_STYLES: dict[str, dict[str, Any]] = {
    "cinematic": {"label": {"vi": "Điện ảnh cảm xúc", "en": "Emotional cinematic"}, "lighting": "soft directional light, restrained contrast", "camera": "slow push-in with stable close detail", "mood": "grounded, human and deliberate"},
    "bw_luxury": {"label": {"vi": "Đen trắng cao cấp", "en": "Black-and-white luxury"}, "lighting": "sculpted monochrome light with precise highlights", "camera": "measured detail orbit and clean hero framing", "mood": "quiet, premium and precise"},
    "viral": {"label": {"vi": "Nhịp social ngắn", "en": "Short-form social rhythm"}, "lighting": "bright practical light with clear focal separation", "camera": "controlled handheld detail and motivated quick cuts", "mood": "clear, energetic and reviewable"},
    "direct_sales": {"label": {"vi": "Lợi ích trực tiếp", "en": "Direct benefit-led"}, "lighting": "clean commercial light with visible product detail", "camera": "clear product inserts and a stable explanation frame", "mood": "plain-spoken, useful and restrained"},
    "ugc": {"label": {"vi": "UGC đời thường", "en": "Everyday UGC"}, "lighting": "natural window or practical phone light", "camera": "stable first-person framing with authentic detail", "mood": "observational and relatable"},
    "fpv": {"label": {"vi": "Quay lướt có kiểm soát", "en": "Controlled FPV movement"}, "lighting": "environment-led light with a legible route", "camera": "smooth foreground travel with safe visual anchors", "mood": "immersive without visual overload"},
    "product_reveal": {"label": {"vi": "Hé lộ sản phẩm", "en": "Product reveal"}, "lighting": "controlled studio key and restrained rim highlight", "camera": "macro detail into a stable hero reveal", "mood": "precise, tactile and product-led"},
}

CINEMATIC_AD_MOTION_PLANS: dict[int, dict[str, Any]] = {
    1: {"id": "1", "title": {"vi": "Push-in cảm xúc", "en": "Emotional push-in"}, "timeline": "open on a quiet detail, move closer only as the message becomes clear, then settle into a stable final frame", "camera": "slow push-in, close detail, final locked frame", "transitions": "clean cuts and one motivated match cut", "shot_direction": "one primary action per shot; preserve stable subject and empty CTA space"},
    2: {"id": "2", "title": {"vi": "Orbit hé lộ", "en": "Reveal orbit"}, "timeline": "move from context to product detail, reveal the central benefit through a measured orbit, then hold on the result", "camera": "macro insert, gentle orbit, composed hero push-in", "transitions": "detail match cut and controlled light transition", "shot_direction": "keep the product or subject consistent; do not invent readable text or marks"},
    3: {"id": "3", "title": {"vi": "Nhịp before/after", "en": "Before/after rhythm"}, "timeline": "show matched context, introduce one reviewable visible change, then conclude with a calm comparison frame", "camera": "locked comparison frame, short tracking transition, final wide hold", "transitions": "motivated wipe or match cut only", "shot_direction": "keep the comparison credible and leave CTA space empty for later editorial work"},
}

CINEMATIC_AD_MUSIC_CHOICES: dict[str, dict[str, Any]] = {
    "1": {"label": {"vi": "Piano điện ảnh nhẹ", "en": "Light cinematic piano"}, "direction": {"vi": "Nhịp piano nhẹ, khoảng nghỉ rõ và kết thúc êm để nâng nhịp kể chuyện.", "en": "Light piano pacing with clear rests and a soft narrative resolve."}, "ai_music_prompt": {"vi": "Hướng âm nhạc tham khảo: piano điện ảnh nhẹ, nhịp vừa, không lời, kết thúc êm; chỉ để biên tập, không tạo audio.", "en": "Reference music direction: light cinematic piano, moderate pace, instrumental, soft resolve; editorial text only, no audio creation."}},
    "2": {"label": {"vi": "Ambient cao cấp", "en": "Premium ambient"}, "direction": {"vi": "Ambient tinh tế, texture tối giản và chuyển cảnh nhẹ để giữ cảm giác cao cấp.", "en": "Refined ambient texture with minimal movement and soft transitions for a premium feel."}, "ai_music_prompt": {"vi": "Hướng âm nhạc tham khảo: ambient cao cấp, texture tối giản, không lời, không dùng sample nhận diện; chỉ để biên tập, không tạo audio.", "en": "Reference music direction: premium ambient, minimal texture, instrumental, no recognizable samples; editorial text only, no audio creation."}},
    "3": {"label": {"vi": "Electronic hiện đại", "en": "Modern electronic"}, "direction": {"vi": "Electronic hiện đại, pulse gọn và điểm nhấn chuyển cảnh tiết chế.", "en": "Modern electronic pulse with restrained transition accents."}, "ai_music_prompt": {"vi": "Hướng âm nhạc tham khảo: electronic hiện đại, pulse rõ, nhịp gọn, không lời; chỉ để biên tập, không tạo audio.", "en": "Reference music direction: modern electronic, clear pulse, tidy rhythm, instrumental; editorial text only, no audio creation."}},
    "none": {"label": {"vi": "Không dùng nhạc", "en": "No music"}, "direction": {"vi": "Không đưa hướng nhạc; chỉ giữ nhịp hình ảnh để biên tập sau.", "en": "No music direction; retain visual timing only for later editing."}, "ai_music_prompt": {"vi": "Không có prompt nhạc và không có yêu cầu tạo audio hoặc gọi provider.", "en": "No music prompt and no audio creation or provider call is requested."}},
}

# Image Motion Planner is the safe Web-native replacement for the Bot's
# ``imagevideo|save`` callback.  The Bot callback only retained a short-lived
# Telegram planning state after an uploaded image; it did not create a video.
# Here the source must instead be an owner-scoped Image Studio direction that
# already references an active Image Vault record.  These tables are editorial
# vocabulary only: they do not select a provider, model, renderer or job.
IMAGE_MOTION_PLANNER_STYLES: dict[str, dict[str, str]] = {
    "cinematic": {
        "label": "Cinematic có kiểm soát",
        "direction": "nhịp điện ảnh có tiết chế, ánh sáng ổn định và chủ thể nhất quán",
    },
    "product_reveal": {
        "label": "Hé lộ sản phẩm",
        "direction": "làm rõ hình dáng, màu sắc, logo hợp lệ và chi tiết sản phẩm mà không thay đổi chúng",
    },
    "social": {
        "label": "Social rõ nhịp",
        "direction": "nhịp social gọn, điểm nhìn rõ và chuyển động có động cơ thay vì rung lắc ngẫu nhiên",
    },
    "editorial": {
        "label": "Editorial sạch",
        "direction": "khung hình tối giản, khoảng thở rõ và ưu tiên tính dễ review khi dựng",
    },
}
IMAGE_MOTION_PLANNER_MOTIONS: dict[str, dict[str, str]] = {
    "slow_push_in": {
        "label": "Slow push-in",
        "action": "giữ chủ thể rồi tiến gần dần vào điểm nhấn chính",
        "camera": "slow push-in ổn định",
        "transition": "clean settle",
    },
    "orbit_reveal": {
        "label": "Orbit hé lộ",
        "action": "chuyển từ ngữ cảnh sang chi tiết bằng một vòng cung nhẹ có kiểm soát",
        "camera": "gentle orbit với hero framing",
        "transition": "detail match cut",
    },
    "handheld_detail": {
        "label": "Handheld detail ổn định",
        "action": "đi theo một chi tiết có ý nghĩa rồi dừng tại frame đọc được",
        "camera": "controlled handheld, no jitter",
        "transition": "motivated cut",
    },
    "hero_hold": {
        "label": "Hero hold",
        "action": "giữ khung hero rõ ràng để người biên tập kiểm tra chủ thể và khoảng CTA",
        "camera": "locked hero frame",
        "transition": "clean hold",
    },
}
IMAGE_MOTION_PLANNER_MUSIC: dict[str, dict[str, str]] = {
    "none": {"label": "Không hướng nhạc", "direction": "không đặt nhạc; chỉ giữ nhịp hình ảnh để editor quyết định sau"},
    "cinematic_light": {"label": "Cinematic nhẹ", "direction": "nhịp ambient/cinematic nhẹ, không lời, chỉ là note biên tập"},
    "modern_electronic": {"label": "Electronic hiện đại", "direction": "pulse electronic tiết chế, điểm chuyển cảnh gọn, chỉ là note biên tập"},
    "natural_ambience": {"label": "Âm thanh bối cảnh", "direction": "ưu tiên room tone hoặc ambience tự nhiên; không yêu cầu tạo audio"},
}
IMAGE_MOTION_PLANNER_DURATIONS = frozenset({5, 10, 15})
IMAGE_MOTION_IMAGE_EXTENSIONS = frozenset({"jpg", "jpeg", "png", "webp"})
IMAGE_MOTION_IMAGE_CONTENT_TYPES = frozenset({"image/jpeg", "image/png", "image/webp"})

# Reference Format Planner is the safe Web-native successor to the Bot's
# ``videoref`` planning menu.  In Telegram, that menu kept a temporary video
# file id and generated an editorial plan around a direction and a new topic.
# The Web version deliberately uses only an owner-scoped active Asset Vault
# *metadata* record.  It never opens a video, fetches a link, extracts frames,
# analyzes the source, or turns a reference into a render request.
REFERENCE_FORMAT_PLANNER_DIRECTIONS: dict[str, dict[str, str]] = {
    "product_ad": {
        "label": "Quảng cáo sản phẩm",
        "hook": "mở bằng một tình huống hoặc chi tiết sản phẩm có thể quan sát",
        "middle": "minh họa cách dùng hoặc bằng chứng cần được kiểm tra riêng",
        "finish": "kết ở khung hero sạch với một bước tiếp theo không phóng đại",
        "camera": "chi tiết sản phẩm rõ, chuyển động có động cơ và hero hold ổn định",
        "transition": "detail match cut có kiểm soát",
    },
    "viral": {
        "label": "TikTok / Reels",
        "hook": "đặt một quan sát hoặc vấn đề gần gũi trong vài giây đầu",
        "middle": "đưa một thao tác, demo hoặc minh họa gọn, ưu tiên dễ hiểu",
        "finish": "đóng bằng kết luận nhẹ và khoảng trống CTA để biên tập sau",
        "camera": "social handheld có kiểm soát, detail insert và khung hình ổn định",
        "transition": "clean cut theo hành động",
    },
    "cinematic": {
        "label": "Cinematic / kể chuyện",
        "hook": "mở bằng một chi tiết có cảm xúc nhưng không mô phỏng người hoặc tác phẩm cụ thể",
        "middle": "mở rộng ngữ cảnh bằng một chuyển biến có thể review",
        "finish": "hạ nhịp về hero frame rõ chủ thể và CTA mềm",
        "camera": "slow push-in, close detail và final composed hold",
        "transition": "motivated match cut tiết chế",
    },
    "education": {
        "label": "Hướng dẫn / giáo dục",
        "hook": "nêu một câu hỏi hoặc bước đầu tiên rõ ràng",
        "middle": "giải thích một quy trình bằng thao tác và bối cảnh dễ kiểm tra",
        "finish": "tóm tắt bước tiếp theo trong khung sạch, không bịa claim",
        "camera": "framing giải thích rõ, over-shoulder và detail insert ổn định",
        "transition": "clean instructional cut",
    },
}
REFERENCE_FORMAT_PLANNER_PLATFORMS: dict[str, dict[str, str]] = {
    "tiktok": {"label": "TikTok", "aspect_ratio": "9:16"},
    "reels": {"label": "Instagram / Facebook Reels", "aspect_ratio": "9:16"},
    "shorts": {"label": "YouTube Shorts", "aspect_ratio": "9:16"},
    "youtube": {"label": "YouTube", "aspect_ratio": "16:9"},
    "facebook": {"label": "Facebook", "aspect_ratio": "4:5"},
    "custom": {"label": "Kênh khác", "aspect_ratio": "custom"},
}
REFERENCE_FORMAT_PLANNER_GOALS: dict[str, dict[str, str]] = {
    "follow": {"label": "Tăng follow", "direction": "mời theo dõi vì giá trị nội dung rõ ràng, không hứa hẹn kết quả"},
    "sales": {"label": "Bán hàng", "direction": "làm rõ lợi ích có thể review và một CTA mua hàng có điều kiện"},
    "lead": {"label": "Lấy lead / inbox", "direction": "mời trao đổi hoặc để lại thông tin một cách minh bạch"},
    "website": {"label": "Kéo website", "direction": "dẫn về một trang thông tin phù hợp sau khi kiểm tra link và nội dung"},
    "educate": {"label": "Chia sẻ kiến thức", "direction": "ưu tiên bước làm có thể kiểm tra và mời người xem lưu lại"},
}
REFERENCE_FORMAT_PLANNER_TONES: dict[str, dict[str, str]] = {
    "clear": {"label": "Rõ ràng, tự nhiên", "direction": "ngắn gọn, trực tiếp và dễ hiểu"},
    "warm": {"label": "Ấm áp, gần gũi", "direction": "gần gũi nhưng không giả định trải nghiệm cá nhân"},
    "confident": {"label": "Tự tin có kiểm soát", "direction": "rõ giá trị nhưng tránh mọi cam kết tuyệt đối"},
    "premium": {"label": "Cao cấp, tiết chế", "direction": "tinh tế, ít lời và ưu tiên chi tiết có thật"},
    "educational": {"label": "Hướng dẫn dễ theo", "direction": "từng bước, dễ kiểm tra và không suy đoán"},
}
REFERENCE_FORMAT_PLANNER_DURATIONS = frozenset({15, 30, 45, 60})
REFERENCE_FORMAT_VIDEO_EXTENSIONS = frozenset({"mp4", "m4v", "mov", "webm"})
REFERENCE_FORMAT_VIDEO_CONTENT_TYPES = frozenset({"video/mp4", "video/quicktime", "video/webm", "video/x-m4v"})

# Storyboard Prompt Pack Composer adapts the Bot's ``storypack`` flow into a
# deliberately transient Web planning surface.  These are local editorial
# vocabularies only: no catalog entry selects a model, provider, media source or
# execution backend.
STORYBOARD_COMPOSER_TEMPLATES: dict[str, dict[str, Any]] = {
    "product_ad": {"label": {"vi": "Quảng cáo sản phẩm", "en": "Product ad"}},
    "cinematic_story": {"label": {"vi": "Điện ảnh / kể chuyện", "en": "Cinematic storytelling"}},
    "tiktok_reels": {"label": {"vi": "TikTok/Reels ngắn", "en": "Short TikTok/Reels"}},
    "tutorial": {"label": {"vi": "Hướng dẫn / tutorial", "en": "Tutorial"}},
    "shop_affiliate": {"label": {"vi": "Shop/Affiliate", "en": "Shop/Affiliate"}},
    "custom": {"label": {"vi": "Tùy chỉnh", "en": "Custom"}},
}
STORYBOARD_COMPOSER_PLATFORMS: dict[str, dict[str, Any]] = {
    "tiktok_reels": {"label": {"vi": "TikTok / Reels", "en": "TikTok / Reels"}},
    "facebook": {"label": {"vi": "Facebook", "en": "Facebook"}},
    "youtube_shorts": {"label": {"vi": "YouTube Shorts", "en": "YouTube Shorts"}},
    "youtube": {"label": {"vi": "YouTube", "en": "YouTube"}},
    "custom": {"label": {"vi": "Nền tảng tùy chỉnh", "en": "Custom platform"}},
}
STORYBOARD_COMPOSER_STYLES: dict[str, dict[str, Any]] = {
    "cinematic": {"label": {"vi": "Cinematic", "en": "Cinematic"}, "mood": {"vi": "cảm xúc có tiết chế", "en": "restrained emotional"}, "lighting": "soft directional light with reviewable contrast", "camera": "slow motivated push-in and stable detail framing"},
    "clean": {"label": {"vi": "Sạch hiện đại", "en": "Clean modern"}, "mood": {"vi": "rõ ràng, gọn gàng", "en": "clear and composed"}, "lighting": "clean neutral commercial light", "camera": "stable explanatory framing with simple moves"},
    "tech": {"label": {"vi": "Công nghệ", "en": "Technology"}, "mood": {"vi": "hiện đại, dễ hiểu", "en": "modern and legible"}, "lighting": "controlled practical light with restrained accent color", "camera": "precise detail inserts and smooth device-safe movement"},
    "luxury": {"label": {"vi": "Luxury", "en": "Luxury"}, "mood": {"vi": "cao cấp, tinh tế", "en": "premium and deliberate"}, "lighting": "sculpted key light with restrained rim highlights", "camera": "measured orbit and tactile hero detail"},
    "lifestyle": {"label": {"vi": "Lifestyle", "en": "Lifestyle"}, "mood": {"vi": "đời thường, gần gũi", "en": "relatable and lived-in"}, "lighting": "natural practical daylight", "camera": "observational handheld held stable"},
    "drama": {"label": {"vi": "Drama đời thường", "en": "Everyday drama"}, "mood": {"vi": "có chuyển biến nhưng không cường điệu", "en": "a grounded change arc"}, "lighting": "natural contrast with a clear emotional shift", "camera": "motivated close detail and calm reveal"},
    "product": {"label": {"vi": "Product commercial", "en": "Product commercial"}, "mood": {"vi": "rõ sản phẩm, dễ review", "en": "product-led and reviewable"}, "lighting": "controlled studio-commercial light", "camera": "macro product inserts into a stable hero frame"},
    "tiktok": {"label": {"vi": "TikTok ads", "en": "TikTok ads"}, "mood": {"vi": "nhịp social rõ, không quá tải", "en": "social-first without overload"}, "lighting": "bright practical social light", "camera": "controlled handheld detail with motivated quick cuts"},
    "custom": {"label": {"vi": "Phong cách tùy chỉnh", "en": "Custom style"}, "mood": {"vi": "theo brief cần review", "en": "brief-led and reviewable"}, "lighting": "balanced practical light", "camera": "stable editorial camera language"},
}
STORYBOARD_COMPOSER_GOALS: dict[str, dict[str, Any]] = {
    "sell": {"label": {"vi": "Bán hàng", "en": "Sell"}, "focus": {"vi": "làm rõ giá trị và bước tiếp theo mà không hứa hẹn tuyệt đối", "en": "make value and the next step clear without absolute claims"}},
    "engage": {"label": {"vi": "Tăng tương tác", "en": "Engage"}, "focus": {"vi": "mở bằng một quan sát dễ liên hệ và mời phản hồi tự nhiên", "en": "open with a relatable observation and invite a natural response"}},
    "introduce": {"label": {"vi": "Giới thiệu", "en": "Introduce"}, "focus": {"vi": "giới thiệu chủ thể và ngữ cảnh một cách dễ hiểu", "en": "introduce the subject and context clearly"}},
    "educate": {"label": {"vi": "Giáo dục", "en": "Educate"}, "focus": {"vi": "chia nội dung thành các bước có thể kiểm tra", "en": "split the content into reviewable steps"}},
    "custom": {"label": {"vi": "Mục tiêu tùy chỉnh", "en": "Custom goal"}, "focus": {"vi": "ưu tiên mục tiêu do người dùng mô tả và cần review", "en": "prioritize the supplied goal after review"}},
}
STORYBOARD_COMPOSER_SHOT_COUNTS = {15: 5, 30: 6, 60: 10}
STORYBOARD_COMPOSER_PHASES = (
    ("hook", {"vi": "Hook mở đầu", "en": "Opening hook"}, {"vi": "đặt một câu hỏi hoặc chi tiết để thu hút trong vài giây đầu", "en": "open on one question or detail that earns attention"}),
    ("context", {"vi": "Thiết lập bối cảnh", "en": "Context"}, {"vi": "đặt chủ thể vào tình huống dễ hiểu", "en": "place the subject in a legible situation"}),
    ("reveal", {"vi": "Hé lộ chủ thể", "en": "Subject reveal"}, {"vi": "đưa sản phẩm hoặc chủ đề vào khung hình rõ ràng", "en": "bring the product or topic into a clear frame"}),
    ("action", {"vi": "Hành động chính", "en": "Main action"}, {"vi": "minh họa một thao tác hoặc ý chính có thể review", "en": "show one reviewable action or key idea"}),
    ("proof", {"vi": "Chi tiết cần review", "en": "Reviewable detail"}, {"vi": "làm rõ một chi tiết quan sát được, không khẳng định vượt quá bằng chứng", "en": "clarify one observable detail without claiming more than evidence supports"}),
    ("cta", {"vi": "Khung CTA sạch", "en": "Clean CTA frame"}, {"vi": "kết bằng một bước tiếp theo nhẹ nhàng trong khung trống", "en": "end with a gentle next step in clear negative space"}),
)
STORYBOARD_COMPOSER_ORIGINALITY_MARKERS = (
    "in the style of", "style của", "phong cách của", "giống phong cách", "copy y hệt", "sao chép y hệt",
    "copy exact", "recreate exact", "remake exactly", "nhái phong cách", "bắt chước phong cách",
    "same as the ad of", "giống hệt quảng cáo của",
)
STORYBOARD_COMPOSER_LIKENESS_PATTERN = re.compile(
    r"\b(?:deepfake|face[ -]?swap|same[ -]?face|look\s+like|clone(?:\s+(?:face|voice|person|celebrity))?|"
    r"giống\s+hệt|mô\s*phỏng\s*(?:khuôn\s*mặt|người)|bắt\s*chước\s*(?:khuôn\s*mặt|người)|"
    r"thay\s*mặt|tái\s*tạo\s*khuôn\s*mặt)\b",
    re.IGNORECASE,
)
STORYBOARD_COMPOSER_NONCONSENSUAL_PATTERN = re.compile(
    r"(?:without\s+(?:their\s+)?consent|non[- ]?consensual|không\s+(?:có\s+)?(?:sự\s+)?đồng\s*ý|không\s+xin\s+phép)",
    re.IGNORECASE,
)
STORYBOARD_COMPOSER_CLAIM_PATTERN = re.compile(
    r"(?:\b100\s*%\b|\bguarantee(?:d)?\b|\bguaranteed\s+results?\b|\bclinically\s+proven\b|"
    r"\bproven\b|\bbest\b|\bnumber\s*(?:one|1)\b|\bno\.?\s*1\b|\bnever\s+fail\b|"
    r"\bperfect(?:ly)?\b|\bcure(?:s|d)?\b|\bheal(?:s|ed)?\b|cam\s*kết|chắc\s*chắn|"
    r"được\s*chứng\s*minh|bảo\s*đảm|hiệu\s*quả\s*tuyệt\s*đối|tốt\s*nhất|số\s*1|"
    r"không\s*bao\s*giờ\s*thất\s*bại|chữa\s*khỏi|điều\s*trị\s*dứt\s*điểm)",
    re.IGNORECASE,
)
STORYBOARD_COMPOSER_MARKUP_PATTERN = re.compile(
    r"(?:<\s*/?\s*[A-Za-z][^>\r\n]{0,240}>|\[[^\]\r\n]{1,160}\]\([^\)\r\n]{1,480}\)|```|\bon[a-z]+\s*=)",
    re.IGNORECASE,
)
STORYBOARD_COMPOSER_EXTERNAL_HANDLE_PATTERN = re.compile(
    r"\b(?:(?:provider|model|engine|bot|telegram|render|job|media|asset|file|output|preview)[ _-]*"
    r"(?:id|ref(?:erence)?|token|handle|url|path)|(?:upload|download)[ _-]*(?:id|url|path))\b|(?:^|\s)@[A-Za-z0-9_]{3,}",
    re.IGNORECASE,
)
STORYBOARD_COMPOSER_MAX_TOPIC = 500
STORYBOARD_COMPOSER_MAX_BRIEF = 500
STORYBOARD_COMPOSER_MAX_TEXT = 4_800

CINEMATIC_AD_ORIGINALITY_MARKERS = (
    "in the style of", "style của", "phong cách của", "giống phong cách", "copy y hệt", "sao chép y hệt",
    "copy exact", "recreate exact", "remake exactly", "nhái phong cách", "bắt chước phong cách",
    "same as the ad of", "giống hệt quảng cáo của",
)
CINEMATIC_AD_LIKENESS_PATTERN = re.compile(
    r"\b(?:deepfake|face[ -]?swap|same[ -]?face|look\s+like|clone(?:\s+(?:face|voice|person|celebrity))?|"
    r"giống\s+hệt|mô\s*phỏng\s*(?:khuôn\s*mặt|người)|bắt\s*chước\s*(?:khuôn\s*mặt|người)|"
    r"thay\s*mặt|tái\s*tạo\s*khuôn\s*mặt)\b",
    re.IGNORECASE,
)
CINEMATIC_AD_PERSON_PATTERN = re.compile(
    r"\b(?:celebrity|famous\s+person|public\s+figure|real\s+person|người\s+nổi\s+tiếng|"
    r"ca\s*sĩ|diễn\s*viên|nghệ\s*sĩ|idol|taylor\s+swift|cristiano\s+ronaldo|sơn\s+tùng|son\s+tung)\b",
    re.IGNORECASE,
)
CINEMATIC_AD_CLAIM_PATTERN = re.compile(
    r"(?:\b100\s*%\b|\bguarantee(?:d)?\b|\bguaranteed\s+results?\b|\bclinically\s+proven\b|"
    r"\bproven\b|\bbest\b|\bnumber\s*(?:one|1)\b|\bno\.?\s*1\b|\bnever\s+fail\b|"
    r"\bperfect(?:ly)?\b|cam\s*kết|chắc\s*chắn|được\s*chứng\s*minh|bảo\s*đảm|"
    r"hiệu\s*quả\s*tuyệt\s*đối|tốt\s*nhất|số\s*1|không\s*bao\s*giờ\s*thất\s*bại)",
    re.IGNORECASE,
)
CINEMATIC_AD_MARKUP_PATTERN = re.compile(
    r"(?:<\s*/?\s*[A-Za-z][^>\r\n]{0,240}>|\[[^\]\r\n]{1,160}\]\([^\)\r\n]{1,480}\)|```|\bon[a-z]+\s*=)",
    re.IGNORECASE,
)
CINEMATIC_AD_EXTERNAL_HANDLE_PATTERN = re.compile(
    r"\b(?:(?:provider|model|engine|bot|telegram|render|job|media|asset|file|output|preview)[ _-]*"
    r"(?:id|ref(?:erence)?|token|handle|url|path)|(?:upload|download)[ _-]*(?:id|url|path))\b",
    re.IGNORECASE,
)
CINEMATIC_AD_MAX_PRODUCT = 500
CINEMATIC_AD_MAX_MESSAGE = 500
CINEMATIC_AD_MAX_TEXT = 4_800

VIDEO_PROMPT_PLANNER_DEFAULT_NEGATIVE = (
    "distorted face, identity change, warped product, broken logo, misspelled text, random readable text, "
    "extra limbs, extra people, unstable geometry, flicker, morphing, watermark, unrelated objects"
)
VIDEO_PROMPT_PLANNER_ORIGINALITY_MARKERS = (
    "in the style of", "style của", "phong cách của", "giống phong cách", "copy y hệt", "sao chép y hệt",
    "copy exact", "recreate exact", "remake exactly", "nhái phong cách", "bắt chước phong cách",
)
VIDEO_PROMPT_PLANNER_CELEBRITY_PATTERN = re.compile(
    r"\b(?:celebrity|famous person|public figure|người nổi tiếng|ca sĩ|diễn viên|nghệ sĩ|idol|"
    r"taylor swift|cristiano ronaldo|son tung|sơn tùng)\b",
    re.IGNORECASE,
)
VIDEO_PROMPT_PLANNER_IMPERSONATION_PATTERN = re.compile(
    r"\b(?:look\s+like|same\s+face\s+as|giống|mô\s*phỏng|bắt\s*chước|clone|deepfake)\b",
    re.IGNORECASE,
)
VIDEO_PROMPT_PLANNER_MARKUP_PATTERN = re.compile(
    r"(?:<\s*/?\s*[A-Za-z][^>\r\n]{0,240}>|\[[^\]\r\n]{1,160}\]\([^\)\r\n]{1,480}\)|```)",
    re.IGNORECASE,
)
VIDEO_PROMPT_PLANNER_PROVIDER_HANDLE_PATTERN = re.compile(
    r"\b(?:(?:provider|model|engine|bot|telegram|render|job|media|asset)[ _-]*(?:id|ref(?:erence)?|token|handle))\b|(?:^|\s)@[A-Za-z0-9_]{3,}",
    re.IGNORECASE,
)
VIDEO_PROMPT_PLANNER_MAX_BRIEF = 900
VIDEO_PROMPT_PLANNER_MAX_OPTIONAL_LINE = 320
VIDEO_PROMPT_PLANNER_MAX_CONSTRAINTS = 6
VIDEO_PROMPT_PLANNER_MAX_TEXT = 12_000

IDEMPOTENCY_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{12,160}$")
UNSAFE_CONTROL_PATTERN = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
# Deliberately reject URL/scheme markers wherever they occur.  A boundary
# such as ``(^|\\s)`` is too weak here because a source URL is commonly
# enclosed in punctuation, e.g. ``(https://...)`` or ``<file:...>``.
URL_PATTERN = re.compile(r"(?:https?://|www\.|file:|data:|javascript:)", re.IGNORECASE)
SECRET_PATTERN = re.compile(
    r"\b(?:api[ _-]?(?:key|token)|access[ _-]?token|refresh[ _-]?token|"
    r"client[ _-]?secret|password|passphrase|authorization|otp|cvv|cvc|"
    r"private[ _-]?key)\b\s*(?:['\"]\s*)?(?:[:=]|\bis\b)\s*(?:['\"]\s*)?"
    r"[A-Za-z0-9_./+=:-]{6,}",
    re.IGNORECASE,
)
KNOWN_SECRET_PATTERN = re.compile(
    r"(?<![A-Za-z0-9_])(?:sk|pk|rk)_[A-Za-z0-9_-]{12,}|"
    r"github_pat_[A-Za-z0-9_]{12,}|gh[pousr]_[A-Za-z0-9]{12,}|"
    r"xox[bpars]-[A-Za-z0-9-]{12,}|AIza[0-9A-Za-z_-]{20,}|"
    r"(?:AKIA|ASIA)[0-9A-Z]{16}|eyJ[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]{8,}\.",
    re.IGNORECASE,
)
PAYMENT_PATTERN = re.compile(
    r"\b(?:txid|transaction\s+(?:hash|id|reference)|mã\s*(?:giao\s*)?(?:dịch|thanh\s*toán)|"
    r"bill|biên\s*lai|chứng\s*từ|số\s*tài\s*khoản|stk|qr\s*(?:code|thanh\s*toán))\b",
    re.IGNORECASE,
)
# Video Studio has no execution authority and deliberately stores no opaque
# provider/Bot/job/media handles.  Block identifier-shaped references in the
# authoring fields rather than allowing an accidental second integration
# contract to form inside free text.
EXTERNAL_REFERENCE_PATTERN = re.compile(
    r"\b(?:(?:provider|render|job|media)[ _-]*(?:id|ref(?:erence)?|token)|telegram[ _-]*file[ _-]*id|file[ _-]*id)\b\s*(?::|=|\bis\b)\s*\S+",
    re.IGNORECASE,
)

MAX_PLANS_PER_ACCOUNT = 300
MAX_SCENES_PER_PLAN = 250
MAX_VERSIONS_PER_ENTITY = 100
MAX_EVENT_LIMIT = 50
MAX_LIST_LIMIT = 100
IDEMPOTENCY_RETENTION = timedelta(hours=24)
MAX_IDEMPOTENCY_RECORDS_PER_ACCOUNT = 1024
# ``web_video_scenes`` intentionally keeps a single ``UNIQUE(plan_id,
# ordinal)`` constraint.  Archived scenes therefore live in a disjoint range
# so active scenes can always be reordered to 1..N without colliding with an
# archived middle scene.  The temporary reorder range remains separate from
# both ranges for the duration of an atomic SQLite transaction.
ARCHIVED_ORDINAL_BASE = 1_000_000
REORDER_TEMPORARY_ORDINAL_BASE = 2_000_000


def _require_enabled() -> None:
    if not video_studio_enabled():
        raise HTTPException(
            status_code=503,
            detail="Video Production Studio đang tạm dừng để bảo trì. WEBAPP_VIDEO_STUDIO_ENABLED chưa được bật.",
        )


def _uuid(value: Any, *, label: str) -> str:
    try:
        return str(uuid.UUID(str(value)))
    except (TypeError, ValueError, AttributeError) as exc:
        raise HTTPException(status_code=422, detail=f"{label} không hợp lệ") from exc


def _optional_uuid(value: Any, *, label: str) -> str | None:
    raw = str(value or "").strip()
    return _uuid(raw, label=label) if raw else None


def _idempotency_key(value: Any) -> str:
    key = str(value or "").strip()
    if not IDEMPOTENCY_PATTERN.fullmatch(key):
        raise ValueError("Idempotency key không hợp lệ")
    return key


def _sensitive_text(value: str) -> bool:
    return bool(
        URL_PATTERN.search(value)
        or SECRET_PATTERN.search(value)
        or KNOWN_SECRET_PATTERN.search(value)
        or PAYMENT_PATTERN.search(value)
        or EXTERNAL_REFERENCE_PATTERN.search(value)
        or "-----begin" in value.lower()
    )


def _line(value: Any, *, label: str, minimum: int, maximum: int, allow_empty: bool = False) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if UNSAFE_CONTROL_PATTERN.search(text) or len(text) > maximum or (not allow_empty and len(text) < minimum):
        raise ValueError(f"{label} cần từ {minimum} đến {maximum} ký tự hợp lệ")
    if text and _sensitive_text(text):
        raise ValueError(f"{label} không nhận URL, secret, mã xác thực, tham chiếu provider hoặc chứng từ thanh toán")
    return text


def _body(value: Any, *, label: str, maximum: int, allow_empty: bool = False) -> str:
    text = str(value or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    if UNSAFE_CONTROL_PATTERN.search(text) or len(text) > maximum or (not allow_empty and not text):
        raise ValueError(f"{label} cần từ 1 đến {maximum:,} ký tự hợp lệ".replace(",", "."))
    if text and _sensitive_text(text):
        raise ValueError(f"{label} không nhận URL, secret, mã xác thực, tham chiếu provider hoặc chứng từ thanh toán")
    return text


def _tags(value: Any) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError("Tags phải là danh sách")
    result: list[str] = []
    seen: set[str] = set()
    for raw in value:
        tag = _line(raw, label="Tag", minimum=1, maximum=48)
        marker = tag.casefold()
        if marker not in seen:
            seen.add(marker)
            result.append(tag)
    if len(result) > 20:
        raise ValueError("Tối đa 20 tags")
    return result


def _decode_tags(value: Any) -> list[str]:
    try:
        parsed = json.loads(str(value or "[]"))
    except (TypeError, ValueError, json.JSONDecodeError):
        return []
    return [str(item) for item in parsed if isinstance(item, str)][:20] if isinstance(parsed, list) else []


def _fingerprint(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _idempotency_cutoff() -> str:
    return (datetime.now(timezone.utc) - IDEMPOTENCY_RETENTION).isoformat(timespec="seconds")


def _excerpt(value: Any, limit: int = 280) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text if len(text) <= limit else f"{text[: max(1, limit - 1)].rstrip()}…"


def _planner_line(value: Any, *, label: str, minimum: int, maximum: int, allow_empty: bool = False) -> str:
    """Validate one stateless planner field without widening Studio inputs.

    The persistent Video Studio deliberately has its own authoring contract.
    This extra guard applies only to the new transient planner so raw markup,
    opaque handles and input that could form an integration contract are
    rejected before a prompt is constructed.
    """

    text = _line(value, label=label, minimum=minimum, maximum=maximum, allow_empty=allow_empty)
    if text and (VIDEO_PROMPT_PLANNER_MARKUP_PATTERN.search(text) or VIDEO_PROMPT_PLANNER_PROVIDER_HANDLE_PATTERN.search(text)):
        raise ValueError(f"{label} không nhận markup hoặc mã/tham chiếu hệ thống ngoài")
    return text


def _planner_constraints(value: Any, *, label: str) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(f"{label} phải là danh sách")
    if len(value) > VIDEO_PROMPT_PLANNER_MAX_CONSTRAINTS:
        raise ValueError(f"{label} tối đa {VIDEO_PROMPT_PLANNER_MAX_CONSTRAINTS} mục")
    result: list[str] = []
    seen: set[str] = set()
    for raw in value:
        item = _planner_line(raw, label=label, minimum=2, maximum=220)
        marker = item.casefold()
        if marker not in seen:
            seen.add(marker)
            result.append(item)
    return result


def _planner_guard_marker(*parts: Any) -> str:
    """Return only a narrow originality/likeness guard reason, if any."""

    text = re.sub(r"\s+", " ", " ".join(str(part or "") for part in parts)).strip().casefold()[:10_000]
    for marker in VIDEO_PROMPT_PLANNER_ORIGINALITY_MARKERS:
        if marker in text:
            return "originality"
    if VIDEO_PROMPT_PLANNER_CELEBRITY_PATTERN.search(text) and VIDEO_PROMPT_PLANNER_IMPERSONATION_PATTERN.search(text):
        return "likeness"
    return ""


def _cinematic_ad_line(
    value: Any,
    *,
    label: str,
    minimum: int,
    maximum: int,
    allow_empty: bool = False,
) -> str:
    """Validate one Cinematic Concept field before any template is built.

    The existing durable Video Studio accepts a broader authoring surface.  A
    stateless composer must instead reject markup, URLs, opaque execution
    handles, secret/payment material and file-like identifiers at the request
    boundary so it cannot grow into an accidental execution adapter.
    """

    text = _planner_line(value, label=label, minimum=minimum, maximum=maximum, allow_empty=allow_empty)
    if text and (CINEMATIC_AD_MARKUP_PATTERN.search(text) or CINEMATIC_AD_EXTERNAL_HANDLE_PATTERN.search(text)):
        raise ValueError(f"{label} không nhận markup hoặc mã/tham chiếu hệ thống ngoài")
    return text


def _cinematic_ad_code(value: Any, *, label: str, allowed: frozenset[str] | set[str]) -> str:
    normalized = _cinematic_ad_line(value, label=label, minimum=1, maximum=64).lower()
    if normalized not in allowed:
        raise ValueError(f"{label} không hợp lệ")
    return normalized


def _cinematic_ad_output_line(value: Any, *, label: str, minimum: int = 2, maximum: int = CINEMATIC_AD_MAX_TEXT) -> str:
    """Revalidate deterministic response text before it reaches the browser."""

    return _cinematic_ad_line(value, label=label, minimum=minimum, maximum=maximum)


def _cinematic_ad_marker(*parts: Any) -> str:
    """Classify only guarded claim/originality/likeness language.

    This is intentionally not a fact checker or a likeness clearance service.
    It only prevents the narrow requests that the deterministic composer cannot
    responsibly substantiate or transform into a generic plan.
    """

    text = re.sub(r"\s+", " ", " ".join(str(part or "") for part in parts)).strip().casefold()[:10_000]
    if CINEMATIC_AD_CLAIM_PATTERN.search(text):
        return "claim"
    for marker in CINEMATIC_AD_ORIGINALITY_MARKERS:
        if marker in text:
            return "originality"
    if CINEMATIC_AD_LIKENESS_PATTERN.search(text):
        return "likeness"
    # A named public/real person only becomes an impersonation guard when the
    # request also contains a likeness verb.  Merely discussing a public event
    # is not enough to make an advertising concept unsafe.
    if CINEMATIC_AD_PERSON_PATTERN.search(text) and VIDEO_PROMPT_PLANNER_IMPERSONATION_PATTERN.search(text):
        return "likeness"
    return ""


def _cinematic_ad_boundary() -> dict[str, Any]:
    """Exact no-execution boundary for the Cinematic Ad Concept Composer."""

    return {
        "execution": "web_native_deterministic_cinematic_concept_only",
        "input_persisted": False,
        "source_media_inspected": False,
        "provider_called": False,
        "image_created": False,
        "video_created": False,
        "audio_created": False,
        "preview_created": False,
        "output_created": False,
        "job_created": False,
        "payment_started": False,
        "wallet_mutated": False,
        "asset_saved": False,
        "publish_action_created": False,
        "fact_checked": False,
        "rights_verified": False,
    }


def _cinematic_ad_guard(marker: str) -> dict[str, Any] | None:
    if not marker:
        return None
    if marker == "claim":
        return envelope(
            False,
            "Thông điệp có tuyên bố cần nguồn hoặc kiểm chứng. Hãy viết lại theo hướng mô tả có thể review trước khi dùng.",
            data=_cinematic_ad_boundary(),
            status_name="guarded",
            error_code="WEB_CINEMATIC_CONCEPT_CLAIM_GUARD",
        )
    return envelope(
        False,
        "Mô tả cần được viết lại theo hướng nguyên bản và không mô phỏng người thật, người nổi tiếng hoặc phong cách cụ thể.",
        data=_cinematic_ad_boundary(),
        status_name="guarded",
        error_code="WEB_CINEMATIC_CONCEPT_ORIGINALITY_GUARD",
    )


def _cinematic_ad_plan_save_boundary(
    *,
    draft_recomputed_on_server: bool = True,
    web_video_plan_persisted: bool = True,
) -> dict[str, bool | str]:
    """State the exact effects of the explicit Concept-to-Plan handoff.

    The Bot's ``adconcept|save_*`` callbacks only adjust short-lived Telegram
    choices.  The Web equivalent creates a private, editable authoring plan
    from the original bounded inputs instead.  It never imports pending Bot
    state or implies approval, rendering, media generation, billing or
    delivery.
    """

    return {
        "execution": "web_native_video_plan_server_recomputed",
        "draft_recomputed_on_server": draft_recomputed_on_server,
        "web_video_plan_persisted": web_video_plan_persisted,
        "browser_result_persisted": False,
        "pending_bot_save_created": False,
        "telegram_state_changed": False,
        "bot_called": False,
        "bridge_called": False,
        "source_media_inspected": False,
        "media_uploads": False,
        "provider_called": False,
        "image_created": False,
        "video_created": False,
        "audio_created": False,
        "preview_created": False,
        "output_created": False,
        "job_created": False,
        "wallet_mutated": False,
        "payment_started": False,
        "asset_saved": False,
        "publish_action_created": False,
        "delivery_created": False,
        "approval_created": False,
        "plan_approved": False,
        "plan_locked": False,
        "generation_started": False,
        "fact_checked": False,
        "rights_verified": False,
    }


def _cinematic_ad_plan_save_guard(marker: str) -> dict[str, Any] | None:
    """Return a content-free, truthful guard receipt for a durable handoff."""

    if not marker:
        return None
    if marker == "claim":
        message = "Thông điệp có tuyên bố cần nguồn hoặc kiểm chứng. Hãy viết lại theo hướng mô tả có thể review trước khi lưu kế hoạch."
        error_code = "WEB_CINEMATIC_CONCEPT_CLAIM_GUARD"
    else:
        message = "Mô tả cần được viết lại theo hướng nguyên bản và không mô phỏng người thật, người nổi tiếng hoặc phong cách cụ thể."
        error_code = "WEB_CINEMATIC_CONCEPT_ORIGINALITY_GUARD"
    return envelope(
        False,
        message,
        data={
            "destination": "video_plan",
            **_cinematic_ad_plan_save_boundary(
                draft_recomputed_on_server=False,
                web_video_plan_persisted=False,
            ),
        },
        status_name="guarded",
        error_code=error_code,
    )


def _image_motion_code(value: Any, *, label: str, allowed: frozenset[str] | set[str]) -> str:
    """Validate a compact Image Motion Planner choice, never a media handle."""

    normalized = _planner_line(value, label=label, minimum=1, maximum=64).lower()
    if normalized not in allowed:
        raise ValueError(f"{label} không hợp lệ")
    return normalized


def _image_motion_boundary() -> dict[str, Any]:
    """Exact no-execution boundary for the temporary image-motion receipt."""

    return {
        "execution": "web_native_image_motion_planning_only",
        "input_persisted": False,
        "source_media_inspected": False,
        "source_metadata_owner_checked": True,
        "provider_called": False,
        "image_created": False,
        "video_created": False,
        "audio_created": False,
        "preview_created": False,
        "output_created": False,
        "job_created": False,
        "payment_started": False,
        "wallet_mutated": False,
        "asset_saved": False,
        "publish_action_created": False,
        "fact_checked": False,
        "rights_verified": False,
    }


def _image_motion_plan_save_boundary(
    *,
    draft_recomputed_on_server: bool = True,
    web_video_plan_persisted: bool = True,
) -> dict[str, bool | str]:
    """State the narrowly-scoped effect of an Image Motion Plan handoff."""

    return {
        "execution": "web_native_image_motion_video_plan_server_recomputed",
        "draft_recomputed_on_server": draft_recomputed_on_server,
        "web_video_plan_persisted": web_video_plan_persisted,
        "browser_result_persisted": False,
        "telegram_state_changed": False,
        "bot_called": False,
        "bridge_called": False,
        "source_media_inspected": False,
        "source_metadata_owner_checked": True,
        "media_uploads": False,
        "provider_called": False,
        "image_created": False,
        "video_created": False,
        "audio_created": False,
        "preview_created": False,
        "output_created": False,
        "job_created": False,
        "wallet_mutated": False,
        "payment_started": False,
        "asset_saved": False,
        "publish_action_created": False,
        "delivery_created": False,
        "approval_created": False,
        "plan_approved": False,
        "plan_locked": False,
        "generation_started": False,
        "fact_checked": False,
        "rights_verified": False,
    }


def _image_motion_guard(marker: str, *, saving: bool = False) -> dict[str, Any] | None:
    """Guard narrow imitation requests carried by an old Image Studio draft.

    A direction might predate newer policy controls.  The planner must not
    turn that stored text into a video instruction if it asks to imitate a
    particular artist/person.  This is not rights verification.
    """

    if not marker:
        return None
    boundary: dict[str, Any]
    if saving:
        boundary = {
            "destination": "video_plan",
            **_image_motion_plan_save_boundary(
                draft_recomputed_on_server=False,
                web_video_plan_persisted=False,
            ),
        }
    else:
        boundary = _image_motion_boundary()
    return envelope(
        False,
        "Image Motion Planner không chuyển hướng mô phỏng người thật, người nổi tiếng hoặc phong cách cụ thể thành video plan. Hãy chỉnh Image Studio direction theo hướng nguyên bản trước.",
        data=boundary,
        status_name="guarded",
        error_code="WEB_IMAGE_MOTION_ORIGINALITY_GUARD",
    )


def _image_motion_asset_is_active_image(conn: Any, *, asset_id: str | None, account_id: str) -> bool:
    """Check metadata only; no file, storage key or media bytes are read."""

    if not asset_id:
        return False
    row = conn.execute(
        """SELECT extension, content_type, state FROM web_asset_files
           WHERE id=? AND account_id=?""",
        (asset_id, account_id),
    ).fetchone()
    return bool(
        row
        and str(row[2]) == "active"
        and str(row[0]).lower() in IMAGE_MOTION_IMAGE_EXTENSIONS
        and str(row[1]).lower() in IMAGE_MOTION_IMAGE_CONTENT_TYPES
    )


def _image_motion_direction_reference(conn: Any, *, direction_id: str, account_id: str) -> dict[str, Any]:
    """Return only owner-scoped Image Studio metadata needed for a plan.

    This intentionally does not select storage paths, filenames, URLs, bytes
    or generated image output.  An attached active Image Vault record is only
    a permission/state prerequisite; the planner never sees the media.
    """

    row = conn.execute(
        """SELECT d.id, d.artboard_id, d.title, d.prompt_text, d.edit_instructions,
                  d.composition_notes, d.negative_direction, d.asset_id, d.reference_asset_id,
                  a.title, a.language, a.aspect_ratio
           FROM web_image_directions AS d
           JOIN web_image_artboards AS a ON a.id=d.artboard_id AND a.account_id=d.account_id
           WHERE d.id=? AND d.account_id=? AND d.state='active' AND a.lifecycle<>'archived'""",
        (direction_id, account_id),
    ).fetchone()
    if not row:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy Image Studio direction đang hoạt động thuộc Web account hiện tại.",
        )
    primary_asset_id = str(row[7]) if row[7] else None
    reference_asset_id = str(row[8]) if row[8] else None
    if not (
        _image_motion_asset_is_active_image(conn, asset_id=primary_asset_id, account_id=account_id)
        or _image_motion_asset_is_active_image(conn, asset_id=reference_asset_id, account_id=account_id)
    ):
        raise HTTPException(
            status_code=422,
            detail="Image Motion Planner cần một Image Vault JPEG, PNG hoặc WebP đang hoạt động gắn với Image Studio direction này.",
        )
    return {
        "direction_id": str(row[0]),
        "artboard_id": str(row[1]),
        "direction_title": _line(row[2], label="Tên Image Studio direction", minimum=2, maximum=180),
        # These owner-scoped texts are used only inside the server to screen
        # an old direction and to author a durable private plan.  They never
        # become request input, audit detail or a public source-media field.
        "prompt_text": _body(row[3], label="Prompt Image Studio", maximum=4_000, allow_empty=True),
        "edit_instructions": _body(row[4], label="Hướng dẫn Image Studio", maximum=4_000, allow_empty=True),
        "composition_notes": _body(row[5], label="Composition Image Studio", maximum=4_000, allow_empty=True),
        "negative_direction": _body(row[6], label="Negative Image Studio", maximum=4_000, allow_empty=True),
        "artboard_title": _line(row[9], label="Tên Image Studio artboard", minimum=2, maximum=180),
        "language": _line(row[10], label="Ngôn ngữ Image Studio", minimum=1, maximum=100),
        "aspect_ratio": _line(row[11], label="Tỷ lệ Image Studio", minimum=1, maximum=32),
        "source_image_attached": True,
    }


def _image_motion_reference_public(reference: dict[str, Any]) -> dict[str, Any]:
    """Keep a browser receipt free of asset ID, path, URL or prompt text."""

    return {
        "direction_id": str(reference["direction_id"]),
        "direction_title": str(reference["direction_title"]),
        "artboard_id": str(reference["artboard_id"]),
        "artboard_title": str(reference["artboard_title"]),
        "language": str(reference["language"]),
        "aspect_ratio": str(reference["aspect_ratio"]),
        "source_image_attached": True,
    }


def _image_motion_list_references(conn: Any, *, account_id: str) -> list[dict[str, Any]]:
    rows = conn.execute(
        """SELECT d.id FROM web_image_directions AS d
           JOIN web_image_artboards AS a ON a.id=d.artboard_id AND a.account_id=d.account_id
           WHERE d.account_id=? AND d.state='active' AND a.lifecycle<>'archived'
           ORDER BY d.updated_at DESC, d.id DESC LIMIT ?""",
        (account_id, MAX_LIST_LIMIT),
    ).fetchall()
    results: list[dict[str, Any]] = []
    for row in rows:
        try:
            reference = _image_motion_direction_reference(conn, direction_id=str(row[0]), account_id=account_id)
        except HTTPException as exc:
            if exc.status_code == 422:
                # Directions without an active image reference are useful in
                # Image Studio, but unavailable for this image-to-motion plan.
                continue
            raise
        results.append(_image_motion_reference_public(reference))
    return results


def _reference_format_code(value: Any, *, label: str, allowed: frozenset[str] | set[str]) -> str:
    """Validate one compact Reference Format Planner choice."""

    normalized = _planner_line(value, label=label, minimum=1, maximum=64).lower()
    if normalized not in allowed:
        raise ValueError(f"{label} không hợp lệ")
    return normalized


def _reference_format_boundary() -> dict[str, Any]:
    """State exactly what the transient reference-format plan does not do."""

    return {
        "execution": "web_native_reference_format_planning_only",
        "input_persisted": False,
        "source_video_opened": False,
        "source_metadata_owner_checked": True,
        "reference_analysis_performed": False,
        "source_link_fetched": False,
        "provider_called": False,
        "image_created": False,
        "video_created": False,
        "audio_created": False,
        "preview_created": False,
        "output_created": False,
        "job_created": False,
        "payment_started": False,
        "wallet_mutated": False,
        "asset_saved": False,
        "publish_action_created": False,
        "fact_checked": False,
        "rights_verified": False,
    }


def _reference_format_plan_save_boundary(
    *,
    draft_recomputed_on_server: bool = True,
    web_video_plan_persisted: bool = True,
) -> dict[str, bool | str]:
    """Describe the single durable effect of a planner-to-plan handoff."""

    return {
        "execution": "web_native_reference_format_video_plan_server_recomputed",
        "draft_recomputed_on_server": draft_recomputed_on_server,
        "web_video_plan_persisted": web_video_plan_persisted,
        "browser_result_persisted": False,
        "telegram_state_changed": False,
        "bot_called": False,
        "bridge_called": False,
        "source_video_opened": False,
        "source_metadata_owner_checked": True,
        "reference_analysis_performed": False,
        "source_link_fetched": False,
        "media_uploads": False,
        "provider_called": False,
        "image_created": False,
        "video_created": False,
        "audio_created": False,
        "preview_created": False,
        "output_created": False,
        "job_created": False,
        "wallet_mutated": False,
        "payment_started": False,
        "asset_saved": False,
        "publish_action_created": False,
        "delivery_created": False,
        "approval_created": False,
        "plan_approved": False,
        "plan_locked": False,
        "generation_started": False,
        "fact_checked": False,
        "rights_verified": False,
    }


def _reference_format_asset(conn: Any, *, asset_id: str, account_id: str) -> dict[str, Any]:
    """Resolve an active owner-scoped video Asset Vault record by metadata only.

    The planner intentionally never selects ``storage_key``, a URL, original
    filename, bytes, duration, preview or any provider metadata.  This makes
    the selector a permission prerequisite, rather than a video-analysis API.
    """

    row = conn.execute(
        """SELECT id, display_name, extension, content_type, byte_size, state
           FROM web_asset_files WHERE id=? AND account_id=?""",
        (asset_id, account_id),
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Không tìm thấy video Asset Vault thuộc Web account hiện tại.")
    extension = str(row[2] or "").lower()
    content_type = str(row[3] or "").lower()
    if str(row[5]) != "active" or extension not in REFERENCE_FORMAT_VIDEO_EXTENSIONS or content_type not in REFERENCE_FORMAT_VIDEO_CONTENT_TYPES:
        raise HTTPException(
            status_code=422,
            detail="Reference Format Planner chỉ nhận video MP4, M4V, MOV hoặc WebM đang hoạt động trong Asset Vault.",
        )
    return {
        "asset_id": _uuid(row[0], label="Reference video Asset Vault ID"),
        "display_name": _line(row[1], label="Tên video Asset Vault", minimum=2, maximum=180),
        "extension": extension,
        "content_type": content_type,
        # An integer size is used only as a malformed-row check and never
        # exposed: it must not become a claim that the source was examined.
        "byte_size": int(row[4]),
        "source_video_attached": True,
    }


def _reference_format_reference_public(reference: dict[str, Any]) -> dict[str, Any]:
    """Return a compact browser selector without private storage metadata."""

    return {
        "asset_id": str(reference["asset_id"]),
        "display_name": str(reference["display_name"]),
        "extension": str(reference["extension"]),
        "content_type": str(reference["content_type"]),
        "source_video_attached": True,
    }


def _reference_format_list_references(conn: Any, *, account_id: str) -> list[dict[str, Any]]:
    """List active, current-account video records usable as a plan reference."""

    rows = conn.execute(
        """SELECT id FROM web_asset_files
           WHERE account_id=? AND state='active'
           ORDER BY updated_at DESC, id DESC LIMIT ?""",
        (account_id, MAX_LIST_LIMIT),
    ).fetchall()
    results: list[dict[str, Any]] = []
    for row in rows:
        try:
            reference = _reference_format_asset(conn, asset_id=str(row[0]), account_id=account_id)
        except HTTPException as exc:
            if exc.status_code == 422:
                continue
            raise
        results.append(_reference_format_reference_public(reference))
    return results


def _reference_format_guard(
    *,
    reference: dict[str, Any],
    payload: "ReferenceFormatPlannerRequest",
    saving: bool = False,
) -> dict[str, Any] | None:
    """Refuse direct imitation requests before drafting a new plan."""

    marker = _planner_guard_marker(
        reference.get("display_name"),
        payload.topic,
        payload.audience,
    )
    if not marker:
        return None
    if marker == "likeness":
        message = "Reference Format Planner không chuyển yêu cầu mô phỏng người thật hoặc người nổi tiếng thành video plan. Hãy mô tả chủ thể nguyên bản trước."
        code = "WEB_REFERENCE_FORMAT_LIKENESS_GUARD"
    else:
        message = "Reference Format Planner không chuyển yêu cầu sao chép nguyên mẫu video/thương hiệu thành video plan. Hãy mô tả format và nội dung nguyên bản trước."
        code = "WEB_REFERENCE_FORMAT_ORIGINALITY_GUARD"
    boundary: dict[str, Any]
    if saving:
        boundary = {
            "destination": "video_plan",
            **_reference_format_plan_save_boundary(
                draft_recomputed_on_server=False,
                web_video_plan_persisted=False,
            ),
        }
    else:
        boundary = _reference_format_boundary()
    return envelope(False, message, data=boundary, status_name="guarded", error_code=code)


def _storyboard_composer_line(
    value: Any,
    *,
    label: str,
    minimum: int,
    maximum: int,
    allow_empty: bool = False,
) -> str:
    """Validate transient Storyboard Composer text before templating it.

    The persistent Video Studio deliberately permits a wider authoring surface.
    This stateless prompt pack does not: markup, URLs, file schemes, opaque
    handles, secret/payment material and external identifiers are rejected so a
    text planner cannot become an implicit integration surface.
    """

    text = _planner_line(value, label=label, minimum=minimum, maximum=maximum, allow_empty=allow_empty)
    if text and (
        STORYBOARD_COMPOSER_MARKUP_PATTERN.search(text)
        or STORYBOARD_COMPOSER_EXTERNAL_HANDLE_PATTERN.search(text)
    ):
        raise ValueError(f"{label} không nhận markup, handle hoặc mã/tham chiếu hệ thống ngoài")
    return text


def _storyboard_composer_code(value: Any, *, label: str, allowed: frozenset[str] | set[str]) -> str:
    normalized = _storyboard_composer_line(value, label=label, minimum=1, maximum=64).lower()
    if normalized not in allowed:
        raise ValueError(f"{label} không hợp lệ")
    return normalized


def _storyboard_composer_output_line(
    value: Any,
    *,
    label: str,
    minimum: int = 2,
    maximum: int = STORYBOARD_COMPOSER_MAX_TEXT,
    allow_empty: bool = False,
) -> str:
    """Revalidate generated deterministic text before it reaches the browser."""

    return _storyboard_composer_line(value, label=label, minimum=minimum, maximum=maximum, allow_empty=allow_empty)


def _storyboard_composer_marker(*parts: Any) -> str:
    """Classify guarded claims/originality/likeness requests without judging facts.

    This has no identity, rights or fact-verification authority.  It only keeps
    requests which require such review out of an otherwise generic text plan.
    """

    text = re.sub(r"\s+", " ", " ".join(str(part or "") for part in parts)).strip().casefold()[:10_000]
    if STORYBOARD_COMPOSER_CLAIM_PATTERN.search(text):
        return "claim"
    for marker in STORYBOARD_COMPOSER_ORIGINALITY_MARKERS:
        if marker in text:
            return "originality"
    if STORYBOARD_COMPOSER_LIKENESS_PATTERN.search(text):
        return "originality"
    if STORYBOARD_COMPOSER_NONCONSENSUAL_PATTERN.search(text) and CINEMATIC_AD_PERSON_PATTERN.search(text):
        return "originality"
    if CINEMATIC_AD_PERSON_PATTERN.search(text) and VIDEO_PROMPT_PLANNER_IMPERSONATION_PATTERN.search(text):
        return "originality"
    return ""


def _storyboard_composer_boundary() -> dict[str, Any]:
    """Exact no-execution boundary for Storyboard Prompt Pack Composer."""

    return {
        "execution": "web_native_deterministic_storyboard_composer_only",
        "input_persisted": False,
        "source_media_inspected": False,
        "provider_called": False,
        "image_created": False,
        "video_created": False,
        "audio_created": False,
        "preview_created": False,
        "output_created": False,
        "job_created": False,
        "payment_started": False,
        "wallet_mutated": False,
        "asset_saved": False,
        "publish_action_created": False,
        "fact_checked": False,
        "rights_verified": False,
    }


def _storyboard_composer_guard(marker: str) -> dict[str, Any] | None:
    if not marker:
        return None
    if marker == "claim":
        return envelope(
            False,
            "Chủ đề hoặc brief có tuyên bố cần nguồn hoặc kiểm chứng. Hãy viết lại theo hướng mô tả có thể review trước khi dùng.",
            data=_storyboard_composer_boundary(),
            status_name="guarded",
            error_code="WEB_STORYBOARD_COMPOSER_CLAIM_GUARD",
        )
    return envelope(
        False,
        "Mô tả cần được viết lại theo hướng nguyên bản và không mô phỏng người thật, người nổi tiếng hoặc phong cách cụ thể.",
        data=_storyboard_composer_boundary(),
        status_name="guarded",
        error_code="WEB_STORYBOARD_COMPOSER_ORIGINALITY_GUARD",
    )


def _storyboard_composer_plan_save_boundary(
    *,
    draft_recomputed_on_server: bool = True,
    web_video_plan_persisted: bool = True,
) -> dict[str, bool | str]:
    """State the exact effects of the explicit Composer-to-Plan handoff.

    The Web creates only its own private authoring records.  In particular,
    this does not reuse the Bot's short-lived pending state or imply that a
    media workflow has been approved, locked, queued or started.
    """

    return {
        "execution": "web_native_video_plan_server_recomputed",
        "draft_recomputed_on_server": draft_recomputed_on_server,
        "web_video_plan_persisted": web_video_plan_persisted,
        "browser_result_persisted": False,
        "pending_bot_save_created": False,
        "telegram_state_changed": False,
        "bot_called": False,
        "bridge_called": False,
        "source_media_inspected": False,
        "provider_called": False,
        "image_created": False,
        "video_created": False,
        "audio_created": False,
        "preview_created": False,
        "output_created": False,
        "job_created": False,
        "wallet_mutated": False,
        "payment_started": False,
        "asset_saved": False,
        "publish_action_created": False,
        "delivery_created": False,
        "plan_approved": False,
        "plan_locked": False,
        "generation_started": False,
        "fact_checked": False,
        "rights_verified": False,
    }


def _storyboard_composer_plan_save_guard(marker: str) -> dict[str, Any] | None:
    """Return a truthful guarded receipt for the persistent Web handoff."""

    if not marker:
        return None
    if marker == "claim":
        message = "Chủ đề hoặc brief có tuyên bố cần nguồn hoặc kiểm chứng. Hãy viết lại theo hướng mô tả có thể review trước khi lưu kế hoạch."
        error_code = "WEB_STORYBOARD_COMPOSER_CLAIM_GUARD"
    else:
        message = "Mô tả cần được viết lại theo hướng nguyên bản và không mô phỏng người thật, người nổi tiếng hoặc phong cách cụ thể."
        error_code = "WEB_STORYBOARD_COMPOSER_ORIGINALITY_GUARD"
    return envelope(
        False,
        message,
        data={
            "destination": "video_plan",
            **_storyboard_composer_plan_save_boundary(
                draft_recomputed_on_server=False,
                web_video_plan_persisted=False,
            ),
        },
        status_name="guarded",
        error_code=error_code,
    )


class VideoPromptPlannerRequest(BaseModel):
    """A strict, text-only request for an ephemeral video direction draft.

    No URL, source media, asset reference, project, engine/model selection,
    job, payment, wallet, idempotency or publish field is accepted.  This is
    deliberately separate from durable Video Studio plans and scenes.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    mode: str = "prompt_to_video"
    brief: str
    platform: str = "custom"
    ratio: str = "9:16"
    duration_seconds: int = Field(default=15, ge=3, le=180)
    scene_count: int = Field(default=0, ge=0, le=10)
    style_pack: str = "corporate_tech_commercial"
    action_pack: str = "logo_product_hero_shot"
    audio_mode: str = "modern_electronic"
    detail_level: str = "director"
    motion: str = ""
    background: str = ""
    must_keep: list[str] = Field(default_factory=list, max_length=VIDEO_PROMPT_PLANNER_MAX_CONSTRAINTS)
    must_avoid: list[str] = Field(default_factory=list, max_length=VIDEO_PROMPT_PLANNER_MAX_CONSTRAINTS)
    language: str = "vi"

    @field_validator("mode")
    @classmethod
    def validate_mode(cls, value: str) -> str:
        normalized = _planner_line(value, label="Mode video prompt", minimum=1, maximum=32).lower()
        if normalized not in VIDEO_PROMPT_PLANNER_MODES:
            raise ValueError("Mode video prompt không hợp lệ")
        return normalized

    @field_validator("brief")
    @classmethod
    def validate_brief(cls, value: str) -> str:
        return _planner_line(value, label="Video brief", minimum=2, maximum=VIDEO_PROMPT_PLANNER_MAX_BRIEF)

    @field_validator("platform")
    @classmethod
    def validate_platform(cls, value: str) -> str:
        normalized = _planner_line(value, label="Nền tảng", minimum=2, maximum=24).lower()
        if normalized not in VIDEO_PROMPT_PLANNER_PLATFORMS:
            raise ValueError("Nền tảng video không hợp lệ")
        return normalized

    @field_validator("ratio")
    @classmethod
    def validate_ratio(cls, value: str) -> str:
        normalized = _planner_line(value, label="Tỷ lệ khung hình", minimum=3, maximum=8)
        if normalized not in VIDEO_PROMPT_PLANNER_RATIOS:
            raise ValueError("Tỷ lệ video không hợp lệ")
        return normalized

    @field_validator("style_pack")
    @classmethod
    def validate_style_pack(cls, value: str) -> str:
        normalized = _planner_line(value, label="Style pack", minimum=2, maximum=64).lower()
        if normalized not in VIDEO_PROMPT_PLANNER_STYLE_PACKS:
            raise ValueError("Style pack không hợp lệ")
        return normalized

    @field_validator("action_pack")
    @classmethod
    def validate_action_pack(cls, value: str) -> str:
        normalized = _planner_line(value, label="Action pack", minimum=2, maximum=64).lower()
        if normalized not in VIDEO_PROMPT_PLANNER_ACTION_PACKS:
            raise ValueError("Action pack không hợp lệ")
        return normalized

    @field_validator("audio_mode")
    @classmethod
    def validate_audio_mode(cls, value: str) -> str:
        normalized = _planner_line(value, label="Audio mode", minimum=2, maximum=64).lower()
        if normalized not in VIDEO_PROMPT_PLANNER_AUDIO_MODES:
            raise ValueError("Audio mode không hợp lệ")
        return normalized

    @field_validator("detail_level")
    @classmethod
    def validate_detail_level(cls, value: str) -> str:
        normalized = _planner_line(value, label="Mức độ chi tiết", minimum=2, maximum=32).lower()
        if normalized not in VIDEO_PROMPT_PLANNER_DETAIL_LEVELS:
            raise ValueError("Mức độ chi tiết video không hợp lệ")
        return normalized

    @field_validator("motion", "background")
    @classmethod
    def validate_optional_direction(cls, value: str, info: Any) -> str:
        label = "Chuyển động" if info.field_name == "motion" else "Bối cảnh"
        return _planner_line(value, label=label, minimum=2, maximum=VIDEO_PROMPT_PLANNER_MAX_OPTIONAL_LINE, allow_empty=True)

    @field_validator("must_keep")
    @classmethod
    def validate_must_keep(cls, value: list[str]) -> list[str]:
        return _planner_constraints(value, label="Điều cần giữ")

    @field_validator("must_avoid")
    @classmethod
    def validate_must_avoid(cls, value: list[str]) -> list[str]:
        return _planner_constraints(value, label="Điều cần tránh")

    @field_validator("language")
    @classmethod
    def validate_language(cls, value: str) -> str:
        normalized = _planner_line(value, label="Ngôn ngữ", minimum=2, maximum=8).lower()
        if normalized not in VIDEO_PROMPT_PLANNER_LANGUAGES:
            raise ValueError("Ngôn ngữ chỉ hỗ trợ vi hoặc en")
        return normalized


class VideoPromptPlannerPlanSaveRequest(VideoPromptPlannerRequest):
    """Strict handoff of original text-only Planner inputs into a Web plan.

    The browser cannot submit the generated planner, a plan/scene object,
    media/file/URL/asset reference, execution handle or lifecycle override.
    The server recomputes the deterministic planner during its database write.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, strict=True)

    destination: StrictStr
    idempotency_key: StrictStr

    @field_validator("destination")
    @classmethod
    def validate_destination(cls, value: StrictStr) -> str:
        normalized = _planner_line(value, label="Nơi lưu video plan", minimum=1, maximum=32).lower()
        if normalized != "video_plan":
            raise ValueError("Nơi lưu video plan không hợp lệ")
        return normalized

    @field_validator("idempotency_key")
    @classmethod
    def validate_idempotency_key(cls, value: StrictStr) -> str:
        return _idempotency_key(value)


class VideoPromptPlannerChoice(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    label: str

    @field_validator("id")
    @classmethod
    def validate_choice_id(cls, value: str) -> str:
        return _planner_line(value, label="Mã lựa chọn", minimum=2, maximum=64).lower()

    @field_validator("label")
    @classmethod
    def validate_choice_label(cls, value: str) -> str:
        return _planner_line(value, label="Nhãn lựa chọn", minimum=2, maximum=180)


class VideoPromptPlannerShot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    index: int = Field(ge=1, le=10)
    start_seconds: float = Field(ge=0, le=180)
    end_seconds: float = Field(gt=0, le=180)
    beat: str
    visual: str
    action: str
    camera: str
    transition: str
    audio: str

    @field_validator("beat", "visual", "action", "camera", "transition", "audio")
    @classmethod
    def validate_shot_text(cls, value: str) -> str:
        return _planner_line(value, label="Nội dung shot", minimum=2, maximum=1_200)

    def model_post_init(self, __context: Any) -> None:
        if self.end_seconds <= self.start_seconds:
            raise ValueError("Mốc kết thúc shot phải lớn hơn mốc bắt đầu")


class VideoPromptPlannerCoverage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ok: bool
    missing: list[str] = Field(default_factory=list, max_length=6)

    @field_validator("missing")
    @classmethod
    def validate_missing(cls, value: list[str]) -> list[str]:
        return _planner_constraints(value, label="Thông tin còn thiếu")

    def model_post_init(self, __context: Any) -> None:
        if self.ok != (not self.missing):
            raise ValueError("Coverage không nhất quán")


class VideoPromptPlannerResult(BaseModel):
    """Exact, browser-safe display schema for the stateless video planner."""

    model_config = ConfigDict(extra="forbid")

    title: str
    mode: str
    brief: str
    platform: str
    ratio: str
    duration_seconds: int = Field(ge=3, le=180)
    scene_count: int = Field(ge=1, le=10)
    style_pack: VideoPromptPlannerChoice
    action_pack: VideoPromptPlannerChoice
    audio_mode: VideoPromptPlannerChoice
    detail_level: str
    needs_clarification: bool
    motion: str
    background: str
    must_keep: list[str] = Field(default_factory=list, max_length=VIDEO_PROMPT_PLANNER_MAX_CONSTRAINTS)
    must_avoid: list[str] = Field(default_factory=list, max_length=VIDEO_PROMPT_PLANNER_MAX_CONSTRAINTS)
    continuity_locks: list[str] = Field(min_length=1, max_length=12)
    coverage: VideoPromptPlannerCoverage
    cautions: list[str] = Field(default_factory=list, max_length=6)
    review_before_use: list[str] = Field(min_length=1, max_length=6)
    prompt: str
    negative_prompt: str
    shots: list[VideoPromptPlannerShot] = Field(min_length=1, max_length=10)

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        return _planner_line(value, label="Tiêu đề planner", minimum=2, maximum=180)

    @field_validator("mode")
    @classmethod
    def validate_result_mode(cls, value: str) -> str:
        if value not in VIDEO_PROMPT_PLANNER_MODES:
            raise ValueError("Mode kết quả không hợp lệ")
        return value

    @field_validator("brief")
    @classmethod
    def validate_result_brief(cls, value: str) -> str:
        return _planner_line(value, label="Video brief kết quả", minimum=2, maximum=VIDEO_PROMPT_PLANNER_MAX_BRIEF)

    @field_validator("platform")
    @classmethod
    def validate_result_platform(cls, value: str) -> str:
        if value not in VIDEO_PROMPT_PLANNER_PLATFORMS:
            raise ValueError("Nền tảng kết quả không hợp lệ")
        return value

    @field_validator("ratio")
    @classmethod
    def validate_result_ratio(cls, value: str) -> str:
        if value not in VIDEO_PROMPT_PLANNER_RATIOS:
            raise ValueError("Tỷ lệ kết quả không hợp lệ")
        return value

    @field_validator("style_pack")
    @classmethod
    def validate_result_style_pack(cls, value: VideoPromptPlannerChoice) -> VideoPromptPlannerChoice:
        expected = VIDEO_PROMPT_PLANNER_STYLE_PACKS.get(value.id)
        if not expected or value.label != expected["label"]:
            raise ValueError("Style pack kết quả không hợp lệ")
        return value

    @field_validator("action_pack")
    @classmethod
    def validate_result_action_pack(cls, value: VideoPromptPlannerChoice) -> VideoPromptPlannerChoice:
        expected = VIDEO_PROMPT_PLANNER_ACTION_PACKS.get(value.id)
        if not expected or value.label != expected["label"]:
            raise ValueError("Action pack kết quả không hợp lệ")
        return value

    @field_validator("audio_mode")
    @classmethod
    def validate_result_audio_mode(cls, value: VideoPromptPlannerChoice) -> VideoPromptPlannerChoice:
        expected = VIDEO_PROMPT_PLANNER_AUDIO_MODES.get(value.id)
        if not expected or value.label != expected["label"]:
            raise ValueError("Audio mode kết quả không hợp lệ")
        return value

    @field_validator("detail_level")
    @classmethod
    def validate_result_detail_level(cls, value: str) -> str:
        if value not in VIDEO_PROMPT_PLANNER_DETAIL_LEVELS:
            raise ValueError("Mức độ chi tiết kết quả không hợp lệ")
        return value

    @field_validator("motion", "background")
    @classmethod
    def validate_result_optional_direction(cls, value: str, info: Any) -> str:
        label = "Chuyển động kết quả" if info.field_name == "motion" else "Bối cảnh kết quả"
        return _planner_line(value, label=label, minimum=2, maximum=VIDEO_PROMPT_PLANNER_MAX_OPTIONAL_LINE, allow_empty=True)

    @field_validator("must_keep")
    @classmethod
    def validate_result_must_keep(cls, value: list[str]) -> list[str]:
        return _planner_constraints(value, label="Điều cần giữ kết quả")

    @field_validator("must_avoid")
    @classmethod
    def validate_result_must_avoid(cls, value: list[str]) -> list[str]:
        return _planner_constraints(value, label="Điều cần tránh kết quả")

    @field_validator("continuity_locks", "cautions", "review_before_use")
    @classmethod
    def validate_result_lines(cls, value: list[str], info: Any) -> list[str]:
        label = {
            "continuity_locks": "Khóa continuity",
            "cautions": "Lưu ý",
            "review_before_use": "Checklist review",
        }.get(info.field_name, "Nội dung planner")
        maximum = 12 if info.field_name == "continuity_locks" else 6
        if not isinstance(value, list) or len(value) > maximum:
            raise ValueError(f"{label} không hợp lệ")
        result = [_planner_line(item, label=label, minimum=2, maximum=360) for item in value]
        if info.field_name in {"continuity_locks", "review_before_use"} and not result:
            raise ValueError(f"{label} không được trống")
        return result

    @field_validator("prompt", "negative_prompt")
    @classmethod
    def validate_result_prompt(cls, value: str) -> str:
        text = str(value or "").replace("\r\n", "\n").replace("\r", "\n").strip()
        if not text or len(text) > VIDEO_PROMPT_PLANNER_MAX_TEXT or UNSAFE_CONTROL_PATTERN.search(text):
            raise ValueError("Prompt kết quả không hợp lệ")
        if _sensitive_text(text) or VIDEO_PROMPT_PLANNER_MARKUP_PATTERN.search(text) or VIDEO_PROMPT_PLANNER_PROVIDER_HANDLE_PATTERN.search(text):
            raise ValueError("Prompt kết quả vượt ranh giới an toàn")
        return text

    def model_post_init(self, __context: Any) -> None:
        if self.scene_count != len(self.shots):
            raise ValueError("Số cảnh phải khớp shot plan")
        if self.needs_clarification != (not self.coverage.ok):
            raise ValueError("Trạng thái clarification phải khớp coverage")


def _video_prompt_planner_boundary() -> dict[str, Any]:
    """Exact no-execution boundary returned by every planner response."""

    return {
        "execution": "web_native_deterministic_video_plan_only",
        "input_persisted": False,
        "source_media_inspected": False,
        "provider_called": False,
        "video_created": False,
        "preview_created": False,
        "output_created": False,
        "job_created": False,
        "payment_started": False,
        "wallet_mutated": False,
        "asset_saved": False,
        "publish_action_created": False,
        "fact_checked": False,
        "rights_verified": False,
    }


def _video_prompt_planner_guard(marker: str) -> dict[str, Any] | None:
    if not marker:
        return None
    message = (
        "Mô tả cần được viết lại theo hướng nguyên bản, không mô phỏng phong cách cụ thể."
        if marker == "originality"
        else "Mô tả cần tránh mô phỏng hoặc tái tạo chân dung người nổi tiếng/công chúng."
    )
    return envelope(
        False,
        message,
        data=_video_prompt_planner_boundary(),
        status_name="guarded",
        error_code="WEB_VIDEO_PROMPT_ORIGINALITY_GUARD",
    )


def _video_prompt_planner_plan_save_boundary(
    *,
    draft_recomputed_on_server: bool = True,
    web_video_plan_persisted: bool = True,
) -> dict[str, bool | str]:
    """State the exact effects of the explicit Planner-to-Plan handoff.

    The Web writes only its own private, editable authoring records.  It does
    not reuse the Bot's transient state or imply any approval, lock, media
    execution, provider work, payment, asset or delivery action.
    """

    return {
        "execution": "web_native_video_plan_server_recomputed",
        "draft_recomputed_on_server": draft_recomputed_on_server,
        "web_video_plan_persisted": web_video_plan_persisted,
        "browser_result_persisted": False,
        "pending_bot_save_created": False,
        "telegram_state_changed": False,
        "bot_called": False,
        "bridge_called": False,
        "source_media_inspected": False,
        "media_uploads": False,
        "provider_called": False,
        "image_created": False,
        "video_created": False,
        "audio_created": False,
        "preview_created": False,
        "output_created": False,
        "job_created": False,
        "wallet_mutated": False,
        "payment_started": False,
        "asset_saved": False,
        "publish_action_created": False,
        "delivery_created": False,
        "approval_created": False,
        "plan_approved": False,
        "plan_locked": False,
        "generation_started": False,
        "fact_checked": False,
        "rights_verified": False,
    }


def _video_prompt_planner_plan_save_guard(marker: str) -> dict[str, Any] | None:
    """Return a truthful guarded receipt for the persistent Web handoff."""

    if not marker:
        return None
    message = (
        "Mô tả cần được viết lại theo hướng nguyên bản, không mô phỏng phong cách cụ thể."
        if marker == "originality"
        else "Mô tả cần tránh mô phỏng hoặc tái tạo chân dung người nổi tiếng/công chúng."
    )
    return envelope(
        False,
        message,
        data={
            "destination": "video_plan",
            **_video_prompt_planner_plan_save_boundary(
                draft_recomputed_on_server=False,
                web_video_plan_persisted=False,
            ),
        },
        status_name="guarded",
        error_code="WEB_VIDEO_PROMPT_ORIGINALITY_GUARD",
    )


def _planner_choice(catalog: dict[str, dict[str, str]], key: str) -> dict[str, str]:
    entry = catalog[key]
    return {"id": key, "label": entry["label"]}


def _planner_mode_beats(mode: str) -> tuple[str, ...]:
    return {
        "prompt_to_video": ("hook", "context", "main action", "visual proof", "result", "final hold"),
        "trend_video": ("trend hook", "recognizable pattern", "adaptation", "surprise beat", "proof", "loop ending"),
        "storyboard_video": ("scene establish", "subject action", "visual proof", "transition bridge", "result", "next-scene handoff"),
        "long_script": ("chapter hook", "context", "development", "evidence", "resolution", "chapter handoff"),
    }[mode]


def _planner_scene_count(payload: VideoPromptPlannerRequest) -> int:
    if payload.scene_count:
        return payload.scene_count
    if payload.detail_level == "quick":
        return min(3, max(1, 3 if payload.duration_seconds <= 8 else 4))
    if payload.duration_seconds <= 6:
        return 3
    if payload.duration_seconds <= 8:
        return 4
    if payload.duration_seconds <= 10:
        return 5
    if payload.duration_seconds <= 15:
        return 7
    if payload.duration_seconds <= 30:
        return 6
    if payload.duration_seconds <= 60:
        return 8
    return max(6, min(10, round(payload.duration_seconds / 30)))


def _planner_title(payload: VideoPromptPlannerRequest) -> str:
    mode_labels = {
        "prompt_to_video": "Video Prompt Plan",
        "trend_video": "Trend Video Plan",
        "storyboard_video": "Storyboard Video Plan",
        "long_script": "Long-form Video Plan",
    }
    prefix = mode_labels[payload.mode]
    return f"{prefix}: {_excerpt(payload.brief, 118)}"


def _planner_coverage(payload: VideoPromptPlannerRequest) -> dict[str, Any]:
    words = [part for part in re.split(r"\W+", payload.brief, flags=re.UNICODE) if len(part) > 1]
    missing: list[str] = []
    if len(words) < 4:
        missing.append("Mục tiêu hoặc chủ thể cụ thể")
    if not payload.background:
        missing.append("Bối cảnh")
    if not payload.motion:
        missing.append("Chuyển động camera hoặc chủ thể")
    if payload.mode == "storyboard_video" and payload.scene_count == 0:
        missing.append("Số cảnh storyboard")
    if payload.mode == "long_script" and payload.duration_seconds < 60:
        missing.append("Thời lượng phù hợp cho long-form")
    return {"ok": not missing, "missing": missing[:6]}


def _planner_continuity_locks(payload: VideoPromptPlannerRequest) -> list[str]:
    locks = [
        "Giữ chủ thể, tỷ lệ khung hình và mạch cảnh nhất quán.",
        "Giữ chuyển động máy quay có chủ đích, mỗi shot chỉ có một hành động chính.",
        "Không dùng chữ sinh ngẫu nhiên, watermark hoặc chi tiết hình học thiếu ổn định.",
        *payload.must_keep,
    ]
    result: list[str] = []
    seen: set[str] = set()
    for item in locks:
        normalized = _planner_line(item, label="Khóa continuity", minimum=2, maximum=360)
        marker = normalized.casefold()
        if marker not in seen:
            seen.add(marker)
            result.append(normalized)
    return result[:12]


def _planner_shots(
    payload: VideoPromptPlannerRequest,
    *,
    scene_count: int,
    style: dict[str, str],
    action: dict[str, str],
    audio: dict[str, str],
) -> list[dict[str, Any]]:
    beats = _planner_mode_beats(payload.mode)
    shot_length = payload.duration_seconds / scene_count
    # The request permits a long brief/background, but a ten-shot plan repeats
    # that direction.  Keep each derived shot bounded so a valid request can
    # never turn into an invalid display receipt (and therefore a 500).
    brief_direction = _excerpt(payload.brief, 420)
    background = _excerpt(payload.background or "a relevant, clean and reviewable environment", 240)
    mood = _excerpt(style["mood"], 180)
    camera = payload.motion or action["camera"] or style["camera"]
    action_direction = action["action"]
    if payload.detail_level == "stability_first":
        camera = "one slow, stable camera move with restrained subject motion"
        action_direction = "one clear, physically plausible action with stable identity and geometry"
    elif payload.detail_level == "viral":
        action_direction = f"{action_direction}; introduce one clear pattern interrupt without visual overload"
    elif payload.detail_level == "cinematic":
        camera = f"{camera}; preserve motivated movement and smooth acceleration/deceleration"
    if payload.audio_mode == "silent":
        audio_direction = "no soundtrack; preserve only visual timing for editorial review"
    else:
        audio_direction = audio["direction"]
    shots: list[dict[str, Any]] = []
    for index in range(scene_count):
        start = round(index * shot_length, 1)
        end = round(payload.duration_seconds if index == scene_count - 1 else (index + 1) * shot_length, 1)
        beat = beats[min(len(beats) - 1, round(index * (len(beats) - 1) / max(1, scene_count - 1)))]
        shots.append(
            {
                "index": index + 1,
                "start_seconds": start,
                "end_seconds": end,
                "beat": beat,
                "visual": f"{brief_direction}; {mood}; setting: {background}",
                "action": action_direction,
                "camera": camera if index in {0, scene_count - 1} else style["camera"],
                "transition": "final hold" if index == scene_count - 1 else action["transition"],
                "audio": audio_direction,
            }
        )
    return shots


def _planner_prompt(
    payload: VideoPromptPlannerRequest,
    *,
    style: dict[str, str],
    action: dict[str, str],
    audio: dict[str, str],
    continuity_locks: list[str],
    shots: list[dict[str, Any]],
) -> str:
    task_notes = {
        "prompt_to_video": "Create an original video direction from this written brief only.",
        "trend_video": "Use a current-feeling structure without copying a specific creator, clip or protected identity.",
        "storyboard_video": "Keep each scene independently editable while preserving the shared continuity locks.",
        "long_script": "Split the plan into reviewable chapters; review each chapter separately before any future execution.",
    }
    detail_notes = {
        "quick": "Keep the direction concise and prioritize the essential visual constraints.",
        "director": "Use global vision, timed shots, camera, audio and continuity direction.",
        "viral": "Use one clear hook and pattern interrupt early, then keep proof and end-frame legible.",
        "stability_first": "Use restrained motion, stable geometry and simple transitions.",
        "cinematic": "Use controlled lensing, detailed movement and polished but physically plausible transitions.",
    }
    shot_lines = "\n".join(
        f"{shot['index']}. [{shot['start_seconds']:.1f}-{shot['end_seconds']:.1f}s] {shot['beat']}: "
        f"visual {shot['visual']}; action {shot['action']}; camera {shot['camera']}; "
        f"transition {shot['transition']}; audio {shot['audio']}"
        for shot in shots
    )
    # Prompt text is a single review field with a strict 12K result cap.  Do
    # not re-expand request-size strings in every section of a ten-shot plan.
    safe_brief = _excerpt(payload.brief, 520)
    safe_background = _excerpt(payload.background or "a relevant clean environment", 260)
    locks = _excerpt("; ".join(continuity_locks), 900)
    audio_direction = "No soundtrack; retain visual timing only." if payload.audio_mode == "silent" else audio["direction"]
    language_instruction = "Write production directions in Vietnamese." if payload.language == "vi" else "Write production directions in English."
    prompt = f"""
[Global Vision & Tone]
{task_notes[payload.mode]}
  Brief: {safe_brief}
Platform: {payload.platform}. Aspect ratio: {payload.ratio}. Duration: {payload.duration_seconds} seconds.
Style: {style['label']}. Mood: {style['mood']}. Lighting: {style['lighting']}.
{detail_notes[payload.detail_level]} {language_instruction}

[Subject / Environment Lock]
  Main subject or topic: {safe_brief}
  Background/context: {safe_background}.
Must keep: {locks}

[Shot Breakdown]
{shot_lines}

[Camera / Action]
Primary camera direction: {payload.motion or action['camera'] or style['camera']}.
Primary action: {action['action']}. Transition logic: {action['transition']}.

[Audio / Timing]
{audio_direction}

[Negative Constraints]
{'; '.join([*payload.must_avoid, style['negative'], VIDEO_PROMPT_PLANNER_DEFAULT_NEGATIVE])}

[Final Hold]
Hold the final composition for 0.5-1.0 seconds with stable geometry and clean negative space. Do not generate readable CTA text; add verified text separately after review.
"""
    normalized = "\n".join(line.rstrip() for line in prompt.strip().splitlines())
    if len(normalized) <= VIDEO_PROMPT_PLANNER_MAX_TEXT:
        return normalized
    return f"{normalized[: VIDEO_PROMPT_PLANNER_MAX_TEXT - 1].rstrip()}…"


def _compose_video_prompt_plan(payload: VideoPromptPlannerRequest) -> dict[str, Any]:
    style = VIDEO_PROMPT_PLANNER_STYLE_PACKS[payload.style_pack]
    action = VIDEO_PROMPT_PLANNER_ACTION_PACKS[payload.action_pack]
    audio = VIDEO_PROMPT_PLANNER_AUDIO_MODES[payload.audio_mode]
    scene_count = _planner_scene_count(payload)
    coverage = _planner_coverage(payload)
    continuity_locks = _planner_continuity_locks(payload)
    shots = _planner_shots(payload, scene_count=scene_count, style=style, action=action, audio=audio)
    cautions: list[str] = []
    if not coverage["ok"]:
        cautions.append("Bản kế hoạch vẫn dùng được để biên tập, nhưng các mục còn thiếu cần được làm rõ trước khi dùng cho một workflow thực tế.")
    if payload.must_keep or any(token in payload.brief.casefold() for token in ("logo", "brand", "thương hiệu", "mặt", "face", "sản phẩm", "product")):
        cautions.append("Chân dung, chữ, logo, bao bì và chi tiết sản phẩm có thể sai lệch; cần kiểm tra quyền sử dụng và độ chính xác trước khi dùng.")
    if payload.mode == "long_script":
        cautions.append("Long-form được chia thành các chapter để review; bản này không phải hướng dẫn tạo một video dài trong một lần.")
    prompt = _planner_prompt(
        payload,
        style=style,
        action=action,
        audio=audio,
        continuity_locks=continuity_locks,
        shots=shots,
    )
    negative_prompt = "; ".join([*payload.must_avoid, style["negative"], VIDEO_PROMPT_PLANNER_DEFAULT_NEGATIVE])
    result = {
        "title": _planner_title(payload),
        "mode": payload.mode,
        "brief": payload.brief,
        "platform": payload.platform,
        "ratio": payload.ratio,
        "duration_seconds": payload.duration_seconds,
        "scene_count": scene_count,
        "style_pack": _planner_choice(VIDEO_PROMPT_PLANNER_STYLE_PACKS, payload.style_pack),
        "action_pack": _planner_choice(VIDEO_PROMPT_PLANNER_ACTION_PACKS, payload.action_pack),
        "audio_mode": _planner_choice(VIDEO_PROMPT_PLANNER_AUDIO_MODES, payload.audio_mode),
        "detail_level": payload.detail_level,
        "needs_clarification": not coverage["ok"],
        "motion": payload.motion,
        "background": payload.background,
        "must_keep": payload.must_keep,
        "must_avoid": payload.must_avoid,
        "continuity_locks": continuity_locks,
        "coverage": coverage,
        "cautions": cautions,
        "review_before_use": [
            "Đây là bản kế hoạch văn bản; chưa tạo, render hoặc xem trước video.",
            "Kiểm tra sự thật, quyền sử dụng nội dung, thương hiệu, chân dung và mọi tuyên bố trước khi dùng.",
            "Rà soát khung hình, typography/CTA và tính khả thi trước khi đưa direction sang một workflow riêng.",
        ],
        "prompt": prompt,
        "negative_prompt": negative_prompt,
        "shots": shots,
    }
    return VideoPromptPlannerResult.model_validate(result).model_dump()


def _video_prompt_planner_plan_format(mode: str) -> str:
    """Map the compact Planner vocabulary onto existing Video Plan formats."""

    return {
        "prompt_to_video": "short_form",
        "trend_video": "short_form",
        "storyboard_video": "campaign",
        "long_script": "explainer",
    }[mode]


def _video_prompt_planner_scene_type(*, ordinal: int, total: int) -> str:
    """Give each generated scene an editable authoring role only."""

    if ordinal == 1:
        return "hook"
    if ordinal == total:
        return "cta"
    if ordinal == 2:
        return "problem"
    if ordinal == total - 1:
        return "proof"
    return "solution"


def _video_prompt_planner_scene_duration(*, start_seconds: float, end_seconds: float) -> int:
    """Keep durable authoring scenes valid even for an ultra-dense draft.

    The transient Planner supports fractional timing for editorial review,
    while the durable Studio scene schema intentionally uses whole positive
    seconds.  A draft scene therefore receives a minimum editable duration of
    one second; the original timing remains in its shot notes for review.
    """

    return max(1, min(1_800, int(round(end_seconds - start_seconds))))


def _video_prompt_planner_to_video_plan(
    payload: VideoPromptPlannerPlanSaveRequest,
    planner: dict[str, Any],
) -> tuple[PlanPayload, list[ScenePayload]]:
    """Derive a Web-owned plan from the server-recomputed Planner result.

    ``planner`` is never browser input.  Revalidating it here keeps durable
    plan and scene fields coupled to the deterministic generator, rather than
    allowing a client-rendered prompt, shot list or plan object into storage.
    """

    result = VideoPromptPlannerResult.model_validate(planner)
    total = len(result.shots)
    if not 1 <= total <= MAX_SCENES_PER_PLAN or total != result.scene_count:
        raise HTTPException(status_code=422, detail="Video prompt planner không đủ scene để lưu Video Plan")

    continuity = "\n".join(f"- {_excerpt(item, 360)}" for item in result.continuity_locks)
    plan_brief = "\n".join(
        (
            "Video Prompt Planner — Web-native plan rebuilt on the server.",
            f"Mode: {result.mode}",
            f"Platform: {result.platform}",
            f"Style: {result.style_pack.label}",
            f"Action direction: {result.action_pack.label}",
            f"Audio direction: {result.audio_mode.label}",
            "",
            "## Written brief",
            _excerpt(result.brief, 1_100),
            "",
            "## Continuity locks",
            continuity,
            "",
            "## Negative constraints",
            _excerpt(result.negative_prompt, 1_400),
            "",
            "This is a draft authoring plan. It does not approve, lock, render, generate, queue or deliver media.",
        )
    )
    plan = PlanPayload.model_validate(
        {
            "title": _line(result.title, label="Tên video plan prompt", minimum=2, maximum=180),
            "format": _video_prompt_planner_plan_format(result.mode),
            "language": payload.language,
            "aspect_ratio": result.ratio,
            "target_duration_seconds": result.duration_seconds,
            "objective": _excerpt(f"{result.style_pack.label} · {result.action_pack.label}", 1_000),
            "audience": _excerpt(result.platform, 1_000),
            "brief": _excerpt(plan_brief, 11_900),
            "tags": [
                "prompt-planner",
                f"mode-{payload.mode}",
                f"platform-{payload.platform}",
                f"style-{payload.style_pack}",
                f"detail-{payload.detail_level}",
            ],
            "project_id": None,
        }
    )

    scenes: list[ScenePayload] = []
    for shot in result.shots:
        ordinal = shot.index
        scene_title = _line(
            f"{'Cảnh' if payload.language == 'vi' else 'Scene'} {ordinal} — {_excerpt(shot.beat, 120)}",
            label="Tên scene video prompt",
            minimum=2,
            maximum=180,
        )
        shot_notes = "\n".join(
            (
                f"Planner timing: {shot.start_seconds:.1f}s–{shot.end_seconds:.1f}s.",
                f"Action: {_excerpt(shot.action, 1_000)}",
                f"Camera: {_excerpt(shot.camera, 800)}",
                f"Transition: {_excerpt(shot.transition, 600)}",
                f"Audio direction: {_excerpt(shot.audio, 1_000)}",
                "This is editable authoring metadata only; it does not start media generation.",
            )
        )
        scenes.append(
            ScenePayload.model_validate(
                {
                    "title": scene_title,
                    "scene_type": _video_prompt_planner_scene_type(ordinal=ordinal, total=total),
                    "duration_seconds": _video_prompt_planner_scene_duration(
                        start_seconds=shot.start_seconds,
                        end_seconds=shot.end_seconds,
                    ),
                    "visual_direction": _excerpt(shot.visual, 4_600),
                    # The Planner does not fabricate spoken or on-screen copy
                    # for this handoff; those remain explicit editor fields.
                    "narration": "",
                    "on_screen_text": "",
                    "shot_notes": _excerpt(shot_notes, 4_800),
                    "transition": _excerpt(shot.transition, 480),
                    "tags": ["prompt-planner", f"scene-{ordinal}", f"mode-{payload.mode}"],
                }
            )
        )
    return plan, scenes


class ImageMotionPlannerRequest(BaseModel):
    """Original bounded choices for a private Image Studio motion plan.

    The request deliberately omits asset IDs, URLs, files, prompt text,
    browser-rendered scenes, provider/job IDs and lifecycle fields.  The
    server resolves the selected direction under the current signed account.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, strict=True)

    direction_id: StrictStr
    style: StrictStr
    motion: StrictStr
    music: StrictStr
    duration_seconds: StrictInt

    @field_validator("direction_id")
    @classmethod
    def validate_direction_id(cls, value: StrictStr) -> str:
        return _uuid(value, label="Image Studio direction ID")

    @field_validator("style")
    @classmethod
    def validate_style(cls, value: StrictStr) -> str:
        return _image_motion_code(value, label="Phong cách Image Motion", allowed=set(IMAGE_MOTION_PLANNER_STYLES))

    @field_validator("motion")
    @classmethod
    def validate_motion(cls, value: StrictStr) -> str:
        return _image_motion_code(value, label="Chuyển động Image Motion", allowed=set(IMAGE_MOTION_PLANNER_MOTIONS))

    @field_validator("music")
    @classmethod
    def validate_music(cls, value: StrictStr) -> str:
        return _image_motion_code(value, label="Hướng nhạc Image Motion", allowed=set(IMAGE_MOTION_PLANNER_MUSIC))

    @field_validator("duration_seconds")
    @classmethod
    def validate_duration(cls, value: int) -> int:
        if value not in IMAGE_MOTION_PLANNER_DURATIONS:
            raise ValueError("Image Motion Planner chỉ hỗ trợ 5, 10 hoặc 15 giây")
        return value


class ImageMotionPlannerPlanSaveRequest(ImageMotionPlannerRequest):
    """Explicit Image Motion Planner-to-Video Plan handoff only."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, strict=True)

    destination: StrictStr
    idempotency_key: StrictStr

    @field_validator("destination")
    @classmethod
    def validate_destination(cls, value: StrictStr) -> str:
        return _image_motion_code(value, label="Nơi lưu Image Motion Planner", allowed={"video_plan"})

    @field_validator("idempotency_key")
    @classmethod
    def validate_idempotency_key(cls, value: StrictStr) -> str:
        return _idempotency_key(value)


class ImageMotionPlannerReference(BaseModel):
    model_config = ConfigDict(extra="forbid")

    direction_id: str
    direction_title: str
    artboard_id: str
    artboard_title: str
    language: str
    aspect_ratio: str
    source_image_attached: bool

    @field_validator("direction_id", "artboard_id")
    @classmethod
    def validate_identifier(cls, value: str) -> str:
        return _uuid(value, label="Image Motion reference ID")

    @field_validator("direction_title", "artboard_title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        return _line(value, label="Image Motion reference title", minimum=2, maximum=180)

    @field_validator("language")
    @classmethod
    def validate_language(cls, value: str) -> str:
        return _line(value, label="Image Motion reference language", minimum=1, maximum=100)

    @field_validator("aspect_ratio")
    @classmethod
    def validate_ratio(cls, value: str) -> str:
        return _line(value, label="Image Motion reference ratio", minimum=1, maximum=32)

    def model_post_init(self, __context: Any) -> None:
        if self.source_image_attached is not True:
            raise ValueError("Image Motion reference phải có ảnh Image Vault đang hoạt động")


class ImageMotionPlannerChoice(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    label: str

    @field_validator("id")
    @classmethod
    def validate_id(cls, value: str) -> str:
        return _line(value, label="Mã Image Motion choice", minimum=1, maximum=64)

    @field_validator("label")
    @classmethod
    def validate_label(cls, value: str) -> str:
        return _line(value, label="Nhãn Image Motion choice", minimum=2, maximum=180)


class ImageMotionPlannerScene(BaseModel):
    model_config = ConfigDict(extra="forbid")

    index: StrictInt = Field(ge=1, le=3)
    start_seconds: StrictInt = Field(ge=0, le=15)
    end_seconds: StrictInt = Field(ge=1, le=15)
    title: str
    visual_direction: str
    camera: str
    transition: str
    audio_direction: str
    editorial_note: str

    @field_validator("title", "visual_direction", "camera", "transition", "audio_direction", "editorial_note")
    @classmethod
    def validate_text(cls, value: str) -> str:
        return _line(value, label="Image Motion scene", minimum=2, maximum=2_400)

    def model_post_init(self, __context: Any) -> None:
        if self.end_seconds <= self.start_seconds:
            raise ValueError("Mốc kết thúc Image Motion scene phải lớn hơn mốc bắt đầu")


class ImageMotionPlannerResult(BaseModel):
    """Exact, browser-safe response for an owner-scoped motion planning receipt."""

    model_config = ConfigDict(extra="forbid")

    reference: ImageMotionPlannerReference
    title: str
    style: ImageMotionPlannerChoice
    motion: ImageMotionPlannerChoice
    music: ImageMotionPlannerChoice
    duration_seconds: StrictInt
    scenes: list[ImageMotionPlannerScene] = Field(min_length=3, max_length=3)
    review_before_use: list[str] = Field(min_length=1, max_length=6)

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        return _line(value, label="Tiêu đề Image Motion Planner", minimum=2, maximum=320)

    @field_validator("duration_seconds")
    @classmethod
    def validate_duration(cls, value: int) -> int:
        if value not in IMAGE_MOTION_PLANNER_DURATIONS:
            raise ValueError("Thời lượng Image Motion Planner không hợp lệ")
        return value

    @field_validator("review_before_use")
    @classmethod
    def validate_review(cls, value: list[str]) -> list[str]:
        if not isinstance(value, list):
            raise ValueError("Checklist Image Motion không hợp lệ")
        return [_line(item, label="Checklist Image Motion", minimum=2, maximum=900) for item in value]

    def model_post_init(self, __context: Any) -> None:
        if [scene.index for scene in self.scenes] != [1, 2, 3]:
            raise ValueError("Image Motion Planner cần đúng ba scene theo thứ tự")
        if self.scenes[-1].end_seconds != self.duration_seconds:
            raise ValueError("Timeline Image Motion Planner phải kết thúc đúng thời lượng đã chọn")


class ReferenceFormatPlannerRequest(BaseModel):
    """Strict original inputs for a reference-format planning receipt.

    An Asset Vault identifier is only a current-account permission selector.
    The client cannot provide video bytes, an external link, extracted frames,
    a source transcript, prebuilt analysis, provider/job data or lifecycle
    fields.  The server separately resolves the selected active asset.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, strict=True)

    asset_id: StrictStr
    direction: StrictStr
    platform: StrictStr
    goal: StrictStr
    tone: StrictStr
    topic: StrictStr
    audience: StrictStr
    language: StrictStr
    duration_seconds: StrictInt

    @field_validator("asset_id")
    @classmethod
    def validate_asset_id(cls, value: StrictStr) -> str:
        return _uuid(value, label="Reference video Asset Vault ID")

    @field_validator("direction")
    @classmethod
    def validate_direction(cls, value: StrictStr) -> str:
        return _reference_format_code(value, label="Hướng Reference Format", allowed=set(REFERENCE_FORMAT_PLANNER_DIRECTIONS))

    @field_validator("platform")
    @classmethod
    def validate_platform(cls, value: StrictStr) -> str:
        return _reference_format_code(value, label="Nền tảng Reference Format", allowed=set(REFERENCE_FORMAT_PLANNER_PLATFORMS))

    @field_validator("goal")
    @classmethod
    def validate_goal(cls, value: StrictStr) -> str:
        return _reference_format_code(value, label="Mục tiêu Reference Format", allowed=set(REFERENCE_FORMAT_PLANNER_GOALS))

    @field_validator("tone")
    @classmethod
    def validate_tone(cls, value: StrictStr) -> str:
        return _reference_format_code(value, label="Giọng Reference Format", allowed=set(REFERENCE_FORMAT_PLANNER_TONES))

    @field_validator("topic")
    @classmethod
    def validate_topic(cls, value: StrictStr) -> str:
        return _planner_line(value, label="Chủ đề mới", minimum=2, maximum=500)

    @field_validator("audience")
    @classmethod
    def validate_audience(cls, value: StrictStr) -> str:
        return _planner_line(value, label="Khán giả mục tiêu", minimum=2, maximum=500)

    @field_validator("language")
    @classmethod
    def validate_language(cls, value: StrictStr) -> str:
        normalized = _reference_format_code(value, label="Ngôn ngữ Reference Format", allowed={"vi", "en"})
        return normalized

    @field_validator("duration_seconds")
    @classmethod
    def validate_duration(cls, value: int) -> int:
        if value not in REFERENCE_FORMAT_PLANNER_DURATIONS:
            raise ValueError("Reference Format Planner chỉ hỗ trợ 15, 30, 45 hoặc 60 giây")
        return value


class ReferenceFormatPlannerPlanSaveRequest(ReferenceFormatPlannerRequest):
    """Explicit, idempotent planner-to-private-Video-Plan handoff only."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, strict=True)

    destination: StrictStr
    idempotency_key: StrictStr

    @field_validator("destination")
    @classmethod
    def validate_destination(cls, value: StrictStr) -> str:
        return _reference_format_code(value, label="Nơi lưu Reference Format Planner", allowed={"video_plan"})

    @field_validator("idempotency_key")
    @classmethod
    def validate_idempotency_key(cls, value: StrictStr) -> str:
        return _idempotency_key(value)


class ReferenceFormatPlannerReference(BaseModel):
    """Compact owner-scoped metadata returned to the browser."""

    model_config = ConfigDict(extra="forbid")

    asset_id: str
    display_name: str
    extension: str
    content_type: str
    source_video_attached: bool

    @field_validator("asset_id")
    @classmethod
    def validate_identifier(cls, value: str) -> str:
        return _uuid(value, label="Reference video ID")

    @field_validator("display_name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        return _line(value, label="Tên reference video", minimum=2, maximum=180)

    @field_validator("extension")
    @classmethod
    def validate_extension(cls, value: str) -> str:
        normalized = _line(value, label="Định dạng reference video", minimum=2, maximum=12).lower()
        if normalized not in REFERENCE_FORMAT_VIDEO_EXTENSIONS:
            raise ValueError("Định dạng reference video không hợp lệ")
        return normalized

    @field_validator("content_type")
    @classmethod
    def validate_content_type(cls, value: str) -> str:
        normalized = _line(value, label="Content type reference video", minimum=6, maximum=64).lower()
        if normalized not in REFERENCE_FORMAT_VIDEO_CONTENT_TYPES:
            raise ValueError("Content type reference video không hợp lệ")
        return normalized

    def model_post_init(self, __context: Any) -> None:
        if self.source_video_attached is not True:
            raise ValueError("Reference Format Planner cần video Asset Vault đang hoạt động")


class ReferenceFormatPlannerChoice(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    label: str

    @field_validator("id")
    @classmethod
    def validate_id(cls, value: str) -> str:
        return _line(value, label="Mã Reference Format choice", minimum=1, maximum=64)

    @field_validator("label")
    @classmethod
    def validate_label(cls, value: str) -> str:
        return _line(value, label="Nhãn Reference Format choice", minimum=2, maximum=180)


class ReferenceFormatPlannerScene(BaseModel):
    model_config = ConfigDict(extra="forbid")

    index: StrictInt = Field(ge=1, le=3)
    start_seconds: StrictInt = Field(ge=0, le=60)
    end_seconds: StrictInt = Field(ge=1, le=60)
    title: str
    visual_direction: str
    camera: str
    transition: str
    audio_direction: str
    editorial_note: str

    @field_validator("title", "visual_direction", "camera", "transition", "audio_direction", "editorial_note")
    @classmethod
    def validate_text(cls, value: str) -> str:
        return _line(value, label="Reference Format scene", minimum=2, maximum=2_400)

    def model_post_init(self, __context: Any) -> None:
        if self.end_seconds <= self.start_seconds:
            raise ValueError("Mốc kết thúc Reference Format scene phải lớn hơn mốc bắt đầu")


class ReferenceFormatPlannerResult(BaseModel):
    """Exact browser-safe result for deterministic reference-format planning."""

    model_config = ConfigDict(extra="forbid")

    reference: ReferenceFormatPlannerReference
    title: str
    direction: ReferenceFormatPlannerChoice
    platform: ReferenceFormatPlannerChoice
    goal: ReferenceFormatPlannerChoice
    tone: ReferenceFormatPlannerChoice
    topic: str
    audience: str
    language: str
    duration_seconds: StrictInt
    scenes: list[ReferenceFormatPlannerScene] = Field(min_length=3, max_length=3)
    review_before_use: list[str] = Field(min_length=1, max_length=6)

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        return _line(value, label="Tiêu đề Reference Format Planner", minimum=2, maximum=320)

    @field_validator("topic", "audience")
    @classmethod
    def validate_body(cls, value: str) -> str:
        return _planner_line(value, label="Nội dung Reference Format Planner", minimum=2, maximum=500)

    @field_validator("language")
    @classmethod
    def validate_language(cls, value: str) -> str:
        if value not in {"vi", "en"}:
            raise ValueError("Ngôn ngữ Reference Format Planner không hợp lệ")
        return value

    @field_validator("duration_seconds")
    @classmethod
    def validate_duration(cls, value: int) -> int:
        if value not in REFERENCE_FORMAT_PLANNER_DURATIONS:
            raise ValueError("Thời lượng Reference Format Planner không hợp lệ")
        return value

    @field_validator("review_before_use")
    @classmethod
    def validate_review(cls, value: list[str]) -> list[str]:
        if not isinstance(value, list):
            raise ValueError("Checklist Reference Format không hợp lệ")
        return [_line(item, label="Checklist Reference Format", minimum=2, maximum=900) for item in value]

    def model_post_init(self, __context: Any) -> None:
        if [scene.index for scene in self.scenes] != [1, 2, 3]:
            raise ValueError("Reference Format Planner cần đúng ba scene theo thứ tự")
        if self.scenes[-1].end_seconds != self.duration_seconds:
            raise ValueError("Timeline Reference Format Planner phải kết thúc đúng thời lượng đã chọn")


class CinematicAdConceptRequest(BaseModel):
    """Strict, stateless input for the Bot-derived concept composer.

    It accepts a written product/message brief and compact local choices only.
    It deliberately has no project, source media, file, URL, provider, Bot,
    job, payment, wallet, asset, publish or idempotency fields.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    product: str
    message: str
    message_theme: str = "custom"
    style: str
    language: str
    idea_choice: StrictInt = Field(ge=1, le=3)
    motion_choice: StrictInt = Field(ge=1, le=3)
    video_duration_variant: StrictInt
    music_choice: StrictStr

    @field_validator("product")
    @classmethod
    def validate_product(cls, value: str) -> str:
        return _cinematic_ad_line(value, label="Sản phẩm hoặc dịch vụ", minimum=2, maximum=CINEMATIC_AD_MAX_PRODUCT)

    @field_validator("message")
    @classmethod
    def validate_message(cls, value: str) -> str:
        return _cinematic_ad_line(value, label="Thông điệp", minimum=2, maximum=CINEMATIC_AD_MAX_MESSAGE)

    @field_validator("message_theme")
    @classmethod
    def validate_message_theme(cls, value: str) -> str:
        return _cinematic_ad_code(value, label="Chủ đề thông điệp", allowed=set(CINEMATIC_AD_MESSAGE_THEMES))

    @field_validator("style")
    @classmethod
    def validate_style(cls, value: str) -> str:
        return _cinematic_ad_code(value, label="Phong cách concept", allowed=set(CINEMATIC_AD_STYLES))

    @field_validator("language")
    @classmethod
    def validate_language(cls, value: str) -> str:
        return _cinematic_ad_code(value, label="Ngôn ngữ", allowed={"vi", "en"})

    @field_validator("video_duration_variant")
    @classmethod
    def validate_duration_variant(cls, value: int) -> int:
        if value not in {5, 10, 15}:
            raise ValueError("Thời lượng concept chỉ hỗ trợ 5, 10 hoặc 15 giây")
        return value

    @field_validator("music_choice")
    @classmethod
    def validate_music_choice(cls, value: StrictStr) -> str:
        normalized = _cinematic_ad_line(value, label="Lựa chọn nhạc", minimum=1, maximum=4).lower()
        if normalized not in CINEMATIC_AD_MUSIC_CHOICES:
            raise ValueError("Lựa chọn nhạc không hợp lệ")
        return normalized


class CinematicAdConceptPlanSaveRequest(CinematicAdConceptRequest):
    """Strict, explicit handoff of original Concept choices into a Web plan.

    Browser-rendered direction text, storyboard entries, prompts, files,
    assets, Bot state, provider handles and lifecycle overrides are not part
    of this contract.  The server recomputes the deterministic concept inside
    the write transaction before creating a private Video Plan.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, strict=True)

    destination: StrictStr
    idempotency_key: StrictStr

    @field_validator("destination")
    @classmethod
    def validate_destination(cls, value: StrictStr) -> str:
        return _cinematic_ad_code(value, label="Nơi lưu cinematic concept", allowed={"video_plan"})

    @field_validator("idempotency_key")
    @classmethod
    def validate_idempotency_key(cls, value: StrictStr) -> str:
        return _idempotency_key(value)


class CinematicAdChoice(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    label: str

    @field_validator("id")
    @classmethod
    def validate_id(cls, value: str) -> str:
        return _cinematic_ad_output_line(value, label="Mã lựa chọn", minimum=1, maximum=64)

    @field_validator("label")
    @classmethod
    def validate_label(cls, value: str) -> str:
        return _cinematic_ad_output_line(value, label="Nhãn lựa chọn", minimum=2, maximum=180)


class CinematicAdCreativeDirection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    index: StrictInt = Field(ge=1, le=3)
    title: str
    premise: str
    brand_story: str
    hook: str
    cta: str

    @field_validator("title", "premise", "brand_story", "hook", "cta")
    @classmethod
    def validate_text(cls, value: str) -> str:
        return _cinematic_ad_output_line(value, label="Nội dung creative direction", maximum=2_200)


class CinematicAdStoryboardScene(BaseModel):
    model_config = ConfigDict(extra="forbid")

    index: StrictInt = Field(ge=1, le=3)
    start_seconds: StrictInt = Field(ge=0, le=15)
    end_seconds: StrictInt = Field(ge=1, le=15)
    setting: str
    subject: str
    action: str
    emotion: str
    camera: str
    transition: str
    voiceover: str
    cta_space: str

    @field_validator("setting", "subject", "action", "emotion", "camera", "transition", "voiceover", "cta_space")
    @classmethod
    def validate_text(cls, value: str) -> str:
        return _cinematic_ad_output_line(value, label="Nội dung storyboard", maximum=2_400)

    def model_post_init(self, __context: Any) -> None:
        if self.end_seconds <= self.start_seconds:
            raise ValueError("Mốc kết thúc storyboard phải lớn hơn mốc bắt đầu")


class CinematicAdImagePrompt(BaseModel):
    model_config = ConfigDict(extra="forbid")

    index: StrictInt = Field(ge=1, le=3)
    label: str
    prompt: str
    negative_prompt: str

    @field_validator("label")
    @classmethod
    def validate_label(cls, value: str) -> str:
        return _cinematic_ad_output_line(value, label="Nhãn image direction", maximum=180)

    @field_validator("prompt", "negative_prompt")
    @classmethod
    def validate_prompt(cls, value: str) -> str:
        return _cinematic_ad_output_line(value, label="Image direction", maximum=CINEMATIC_AD_MAX_TEXT)


class CinematicAdVideoPrompt(BaseModel):
    model_config = ConfigDict(extra="forbid")

    duration_seconds: StrictInt
    prompt: str
    negative_prompt: str

    @field_validator("duration_seconds")
    @classmethod
    def validate_duration(cls, value: int) -> int:
        if value not in {5, 10, 15}:
            raise ValueError("Video direction chỉ có bản 5, 10 hoặc 15 giây")
        return value

    @field_validator("prompt", "negative_prompt")
    @classmethod
    def validate_prompt(cls, value: str) -> str:
        return _cinematic_ad_output_line(value, label="Video direction", maximum=CINEMATIC_AD_MAX_TEXT)


class CinematicAdMotionPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    timeline: str
    camera: str
    transitions: str
    shot_direction: str

    @field_validator("id", "title", "timeline", "camera", "transitions", "shot_direction")
    @classmethod
    def validate_text(cls, value: str) -> str:
        return _cinematic_ad_output_line(value, label="Motion plan", minimum=1, maximum=2_400)


class CinematicAdMusicDirection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    label: str
    direction: str
    ai_music_prompt: str

    @field_validator("id", "label", "direction", "ai_music_prompt")
    @classmethod
    def validate_text(cls, value: str) -> str:
        return _cinematic_ad_output_line(value, label="Music direction", minimum=1, maximum=2_400)


class CinematicAdConceptResult(BaseModel):
    """Exact browser schema for a deterministic, non-persistent concept."""

    model_config = ConfigDict(extra="forbid")

    title: str
    product: str
    message: str
    message_theme: CinematicAdChoice
    style: CinematicAdChoice
    language: str
    idea_choice: StrictInt = Field(ge=1, le=3)
    motion_choice: StrictInt = Field(ge=1, le=3)
    video_duration_variant: StrictInt
    music_choice: str
    topic: str
    creative_directions: list[CinematicAdCreativeDirection] = Field(min_length=3, max_length=3)
    selected_direction: CinematicAdCreativeDirection
    scripts: dict[str, str]
    storyboard: list[CinematicAdStoryboardScene] = Field(min_length=3, max_length=3)
    shot_list: list[str] = Field(min_length=1, max_length=10)
    image_prompts: list[CinematicAdImagePrompt] = Field(min_length=3, max_length=3)
    video_prompts: list[CinematicAdVideoPrompt] = Field(min_length=3, max_length=3)
    motion_plan: CinematicAdMotionPlan
    music_direction: CinematicAdMusicDirection
    cautions: list[str] = Field(default_factory=list, max_length=6)
    review_before_use: list[str] = Field(min_length=1, max_length=6)

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        return _cinematic_ad_output_line(value, label="Tiêu đề concept", maximum=320)

    @field_validator("product")
    @classmethod
    def validate_product(cls, value: str) -> str:
        return _cinematic_ad_output_line(value, label="Sản phẩm kết quả", maximum=CINEMATIC_AD_MAX_PRODUCT)

    @field_validator("message")
    @classmethod
    def validate_message(cls, value: str) -> str:
        return _cinematic_ad_output_line(value, label="Thông điệp kết quả", maximum=CINEMATIC_AD_MAX_MESSAGE)

    @field_validator("language")
    @classmethod
    def validate_language(cls, value: str) -> str:
        if value not in {"vi", "en"}:
            raise ValueError("Ngôn ngữ concept không hợp lệ")
        return value

    @field_validator("video_duration_variant")
    @classmethod
    def validate_duration_variant(cls, value: int) -> int:
        if value not in {5, 10, 15}:
            raise ValueError("Thời lượng concept kết quả không hợp lệ")
        return value

    @field_validator("music_choice")
    @classmethod
    def validate_music_choice(cls, value: str) -> str:
        if value not in CINEMATIC_AD_MUSIC_CHOICES:
            raise ValueError("Lựa chọn nhạc concept không hợp lệ")
        return value

    @field_validator("topic")
    @classmethod
    def validate_topic(cls, value: str) -> str:
        return _cinematic_ad_output_line(value, label="Chủ đề concept", maximum=1_800)

    @field_validator("scripts")
    @classmethod
    def validate_scripts(cls, value: dict[str, str]) -> dict[str, str]:
        if not isinstance(value, dict) or set(value) != {"15s", "30s", "60s"}:
            raise ValueError("Scripts phải có đúng các bản 15s, 30s và 60s")
        return {
            duration: _cinematic_ad_output_line(script, label=f"Script {duration}", maximum=CINEMATIC_AD_MAX_TEXT)
            for duration, script in value.items()
        }

    @field_validator("shot_list", "cautions", "review_before_use")
    @classmethod
    def validate_lines(cls, value: list[str], info: Any) -> list[str]:
        if not isinstance(value, list):
            raise ValueError("Danh sách concept không hợp lệ")
        label = {
            "shot_list": "Shot list",
            "cautions": "Lưu ý concept",
            "review_before_use": "Checklist review concept",
        }.get(info.field_name, "Nội dung concept")
        return [_cinematic_ad_output_line(item, label=label, maximum=1_200) for item in value]

    def model_post_init(self, __context: Any) -> None:
        expected_theme = _cinematic_ad_choice(CINEMATIC_AD_MESSAGE_THEMES, self.message_theme.id, self.language)
        expected_style = _cinematic_ad_choice(CINEMATIC_AD_STYLES, self.style.id, self.language)
        if self.message_theme.model_dump() != expected_theme:
            raise ValueError("Message theme kết quả không hợp lệ")
        if self.style.model_dump() != expected_style:
            raise ValueError("Style concept kết quả không hợp lệ")
        if [item.index for item in self.creative_directions] != [1, 2, 3]:
            raise ValueError("Creative directions phải có đúng ba lựa chọn theo thứ tự")
        if self.selected_direction.model_dump() != self.creative_directions[self.idea_choice - 1].model_dump():
            raise ValueError("Selected direction phải khớp idea choice")
        if [item.index for item in self.storyboard] != [1, 2, 3]:
            raise ValueError("Storyboard phải có đúng ba cảnh theo thứ tự")
        previous_end = 0
        for scene in self.storyboard:
            if scene.start_seconds != previous_end:
                raise ValueError("Storyboard phải phủ liên tục từ đầu đến cuối")
            previous_end = scene.end_seconds
        if previous_end != self.video_duration_variant:
            raise ValueError("Storyboard phải kết thúc đúng thời lượng đã chọn")
        if [item.index for item in self.image_prompts] != [1, 2, 3]:
            raise ValueError("Image prompts phải có đúng ba cảnh theo thứ tự")
        if [item.duration_seconds for item in self.video_prompts] != [5, 10, 15]:
            raise ValueError("Video prompts phải có đúng bản 5, 10 và 15 giây")
        expected_motion = CINEMATIC_AD_MOTION_PLANS.get(self.motion_choice)
        if not expected_motion or self.motion_plan.id != expected_motion["id"]:
            raise ValueError("Motion plan không khớp motion choice")
        expected_music_direction = CINEMATIC_AD_MUSIC_CHOICES.get(self.music_choice)
        if not expected_music_direction or self.music_direction.id != self.music_choice:
            raise ValueError("Music direction không khớp music choice")


def _cinematic_ad_label(entry: dict[str, Any], language: str) -> str:
    return str(entry["label"][language])


def _cinematic_ad_choice(catalog: dict[Any, dict[str, Any]], key: Any, language: str) -> dict[str, str]:
    entry = catalog[key]
    return {"id": str(key), "label": _cinematic_ad_label(entry, language)}


def _cinematic_ad_duration_cuts(duration: int) -> tuple[int, int]:
    """Return three contiguous, non-empty scene boundaries for 5/10/15s."""

    first = max(1, round(duration * 0.30))
    second = max(first + 1, round(duration * 0.67))
    return min(first, duration - 2), min(second, duration - 1)


def _cinematic_ad_directions(payload: CinematicAdConceptRequest) -> list[dict[str, Any]]:
    product = payload.product
    message = payload.message
    angle = str(CINEMATIC_AD_MESSAGE_THEMES[payload.message_theme]["angle"][payload.language])
    if payload.language == "vi":
        return [
            {"index": 1, "title": "Hướng cảm xúc", "premise": f"Đặt {product} trong {angle}, rồi dẫn người xem từ quan sát sang một lựa chọn rõ ràng.", "brand_story": f"Mở bằng một tình huống thật, để {product} xuất hiện như điểm chuyển có chủ đích; thông điệp trọng tâm là: {message}", "hook": "Bắt đầu bằng một chi tiết gần gũi trước khi mở rộng bối cảnh.", "cta": "Chừa một khung CTA trống để đội ngũ tự kiểm tra và thêm nội dung sau."},
            {"index": 2, "title": "Hướng lợi ích rõ ràng", "premise": f"Cho thấy bối cảnh, một thao tác hoặc chi tiết của {product}, rồi kết lại bằng lợi ích cần review.", "brand_story": f"Cấu trúc đi từ vấn đề dễ nhận biết tới cách {product} hỗ trợ quy trình; thông điệp cần được kiểm tra là: {message}", "hook": "Mở bằng một điểm ma sát đời thường, không dùng claim tuyệt đối.", "cta": "Giữ cuối khung hình sạch và trống để thêm CTA đã được duyệt riêng."},
            {"index": 3, "title": "Hướng nhịp social", "premise": f"Dùng hook nhanh, ba nhịp hình ảnh rõ và một kết thúc yên để giới thiệu {product}.", "brand_story": f"Đi từ pattern interrupt tới minh họa có thể review, rồi quay lại thông điệp: {message}", "hook": "Bắt đầu bằng tương phản thị giác hoặc chuyển động có động cơ, không sao chép clip cụ thể.", "cta": "Dành khoảng âm hình cuối cho CTA trống; không sinh chữ tự động."},
        ]
    return [
        {"index": 1, "title": "Emotional direction", "premise": f"Place {product} inside {angle}, then move the viewer from observation toward a clear, considered choice.", "brand_story": f"Open with a grounded situation and let {product} become the deliberate turning point; the message to review is: {message}", "hook": "Begin with a familiar detail before opening the wider context.", "cta": "Leave an empty CTA frame for the team to review and add later."},
        {"index": 2, "title": "Clear-benefit direction", "premise": f"Show context, one action or detail of {product}, then close on a benefit that needs review.", "brand_story": f"Move from a recognizable friction point to how {product} supports the workflow; the message to review is: {message}", "hook": "Open with an everyday friction point without absolute claims.", "cta": "Keep the final frame clean and empty for separately approved CTA text."},
        {"index": 3, "title": "Social-rhythm direction", "premise": f"Use a quick hook, three clear visual beats and a calm ending to introduce {product}.", "brand_story": f"Move from a pattern interrupt to reviewable visual illustration, then return to the message: {message}", "hook": "Start with a motivated visual contrast or movement, without copying a specific clip.", "cta": "Reserve final negative space for CTA; do not generate readable text."},
    ]


def _cinematic_ad_scripts(payload: CinematicAdConceptRequest) -> dict[str, str]:
    product = payload.product
    message = payload.message
    if payload.language == "vi":
        return {
            "15s": f"Hook ngắn → bối cảnh → {product} xuất hiện như một lựa chọn → chi tiết thị giác cần review → khung CTA trống. Thông điệp: {message}",
            "30s": f"Hook → tình huống đời thường → ba nhịp minh họa cho {product} → chuyển cảnh có động cơ → kết quả cần review → khung CTA trống. Thông điệp: {message}",
            "60s": f"Bối cảnh nhân vật/chủ thể → điểm ma sát → hành trình thay đổi có thể review → minh họa {product} → kết thúc có khoảng thở → khung CTA trống. Thông điệp: {message}",
        }
    return {
        "15s": f"Short hook → context → {product} appears as a considered choice → reviewable visual detail → empty CTA frame. Message: {message}",
        "30s": f"Hook → everyday situation → three visual beats for {product} → motivated transition → reviewable result → empty CTA frame. Message: {message}",
        "60s": f"Character or subject context → friction point → reviewable change journey → {product} illustration → breathing room at the end → empty CTA frame. Message: {message}",
    }


def _cinematic_ad_storyboard(payload: CinematicAdConceptRequest, motion: dict[str, Any]) -> list[dict[str, Any]]:
    first_end, second_end = _cinematic_ad_duration_cuts(payload.video_duration_variant)
    product = payload.product
    message = payload.message
    style = _cinematic_ad_label(CINEMATIC_AD_STYLES[payload.style], payload.language)
    if payload.language == "vi":
        values = [
            {"setting": f"Bối cảnh đời thường theo phong cách {style}", "subject": product, "action": "Mở bằng chi tiết gây tò mò, chưa vội đưa kết luận.", "emotion": "quan sát và gần gũi", "camera": motion["camera"], "transition": "clean cut có động cơ", "voiceover": f"Gợi ý lời dẫn: {message}", "cta_space": "Chừa vùng CTA trống, không sinh chữ đọc được hoặc watermark."},
            {"setting": "Bối cảnh sáng và rõ hơn để minh họa quy trình", "subject": product, "action": "Hé lộ một chi tiết hoặc thao tác có thể review.", "emotion": "rõ ràng và tự tin", "camera": motion["camera"], "transition": motion["transitions"], "voiceover": "Gợi ý lời dẫn: mô tả điều người xem có thể quan sát, tránh claim tuyệt đối.", "cta_space": "Giữ bố cục sạch, để khoảng trống CTA cho biên tập sau."},
            {"setting": "Khung kết thúc yên, đủ khoảng thở", "subject": product, "action": "Giữ kết quả thị giác ổn định thay vì tạo output hay lời hứa.", "emotion": "bình tĩnh và có chủ đích", "camera": "khóa khung hero ổn định", "transition": "final hold", "voiceover": "Gợi ý lời dẫn: mời người xem tự tìm hiểu thêm sau khi thông tin được duyệt.", "cta_space": "Khung CTA hoàn toàn trống; không có chữ, logo tự phát hoặc watermark."},
        ]
    else:
        values = [
            {"setting": f"Everyday context in a {style} treatment", "subject": product, "action": "Open on a curious detail without making a conclusion yet.", "emotion": "observant and relatable", "camera": motion["camera"], "transition": "motivated clean cut", "voiceover": f"Voiceover direction: {message}", "cta_space": "Leave empty CTA space; do not generate readable text or watermark."},
            {"setting": "A brighter, clearer context for a reviewable workflow illustration", "subject": product, "action": "Reveal one detail or action that can be reviewed.", "emotion": "clear and confident", "camera": motion["camera"], "transition": motion["transitions"], "voiceover": "Voiceover direction: describe what can be observed and avoid absolute claims.", "cta_space": "Keep the composition clean and reserve CTA space for later editorial work."},
            {"setting": "A calm final frame with adequate breathing room", "subject": product, "action": "Hold a stable visual result rather than asserting an output or promise.", "emotion": "calm and deliberate", "camera": "stable locked hero frame", "transition": "final hold", "voiceover": "Voiceover direction: invite further review after the information is approved.", "cta_space": "CTA frame remains completely empty; no invented text, logo or watermark."},
        ]
    boundaries = ((0, first_end), (first_end, second_end), (second_end, payload.video_duration_variant))
    return [
        {"index": index, "start_seconds": start, "end_seconds": end, **values[index - 1]}
        for index, (start, end) in enumerate(boundaries, start=1)
    ]


def _cinematic_ad_image_prompts(payload: CinematicAdConceptRequest) -> list[dict[str, Any]]:
    product = payload.product
    style = _cinematic_ad_label(CINEMATIC_AD_STYLES[payload.style], payload.language)
    labels = ("Cảnh mở", "Cảnh hé lộ", "Cảnh kết") if payload.language == "vi" else ("Opening scene", "Reveal scene", "Closing scene")
    bodies = (
        "bối cảnh đời thường, ánh sáng có chủ đích, chi tiết gần gũi",
        "chi tiết sản phẩm hoặc quy trình rõ ràng, bố cục sạch, chuyển động được gợi ý bằng hình ảnh",
        "khung hero ổn định, nền gọn và vùng CTA trống cho biên tập sau",
    ) if payload.language == "vi" else (
        "everyday context, deliberate light and a relatable close detail",
        "a clear product or workflow detail, clean composition and implied motivated movement",
        "a stable hero frame, tidy background and empty CTA space for later editorial work",
    )
    negative = (
        "watermark, chữ tự phát hoặc sai chính tả, logo không được cấp quyền, khuôn mặt/chủ thể biến dạng, hình học rung, claim chưa kiểm chứng"
        if payload.language == "vi"
        else "watermark, invented or misspelled readable text, unauthorized logo, distorted face or subject, unstable geometry, unverified claim"
    )
    return [
        {
            "index": index,
            "label": labels[index - 1],
            "prompt": f"Hướng visual để biên tập cho {product}: {bodies[index - 1]}, phong cách {style}, giữ chủ thể nhất quán, chừa vùng CTA trống, không sinh chữ đọc được hoặc watermark."
            if payload.language == "vi"
            else f"Editorial visual direction for {product}: {bodies[index - 1]}, {style} treatment, keep the subject consistent, reserve empty CTA space, no invented readable text or watermark.",
            "negative_prompt": negative,
        }
        for index in range(1, 4)
    ]


def _cinematic_ad_video_prompts(payload: CinematicAdConceptRequest, motion: dict[str, Any]) -> list[dict[str, Any]]:
    product = payload.product
    style = _cinematic_ad_label(CINEMATIC_AD_STYLES[payload.style], payload.language)
    negative = (
        "flicker, khuôn mặt/chủ thể biến dạng, chữ tự phát, watermark, hành động không khả thi, thay đổi logo/bao bì, claim chưa kiểm chứng"
        if payload.language == "vi"
        else "flicker, distorted face or subject, invented text, watermark, implausible action, altered logo or packaging, unverified claim"
    )
    return [
        {
            "duration_seconds": duration,
            "prompt": f"Hướng motion video {duration}s để biên tập cho {product}: phong cách {style}; {motion['timeline']}; camera {motion['camera']}; {motion['shot_direction']}; giữ chủ thể ổn định, chừa vùng CTA trống; planning text only, no generated output."
            if payload.language == "en"
            else f"Hướng motion video {duration}s để biên tập cho {product}: phong cách {style}; {motion['timeline']}; camera {motion['camera']}; {motion['shot_direction']}; giữ chủ thể ổn định, chừa vùng CTA trống; chỉ là kế hoạch văn bản, không tạo output.",
            "negative_prompt": negative,
        }
        for duration in (5, 10, 15)
    ]


def _compose_cinematic_ad_concept(payload: CinematicAdConceptRequest) -> dict[str, Any]:
    """Reimplement the Bot's fixed adconcept planning patterns without Bot state.

    The source Bot offered three creative directions, 15/30/60s script outlines,
    a three-scene storyboard, shot vocabulary, image/video direction text and
    music suggestions.  This Web adaptation deliberately omits Telegram state,
    all save/lock/finalize actions, media/provider calls, jobs, pricing and Xu.
    """

    theme = CINEMATIC_AD_MESSAGE_THEMES[payload.message_theme]
    style = CINEMATIC_AD_STYLES[payload.style]
    motion = CINEMATIC_AD_MOTION_PLANS[payload.motion_choice]
    music = CINEMATIC_AD_MUSIC_CHOICES[payload.music_choice]
    directions = _cinematic_ad_directions(payload)
    storyboard = _cinematic_ad_storyboard(payload, motion)
    style_label = _cinematic_ad_label(style, payload.language)
    theme_label = _cinematic_ad_label(theme, payload.language)
    if payload.language == "vi":
        title = f"Concept quảng cáo: {_excerpt(payload.product, 180)}"
        topic = f"Concept quảng cáo {style_label} cho {payload.product}; thông điệp cần review: {payload.message}. Chủ đề: {theme_label}."
        shot_list = [
            "Cận cảnh chi tiết chủ thể/sản phẩm có kiểm soát.",
            "Toàn cảnh bối cảnh để giữ mạch kể chuyện.",
            "Over-the-shoulder hoặc góc quan sát để minh họa thao tác.",
            "Slow push-in hoặc orbit tiết chế theo motion plan.",
            "Match cut hoặc chuyển cảnh có động cơ, không dùng hiệu ứng ngẫu nhiên.",
            "Khung cuối sạch với vùng CTA trống, không sinh chữ hoặc watermark.",
        ]
        cautions = [
            "Đây là concept và hướng prompt dạng văn bản; không tạo ảnh, video, audio, preview, output hoặc job.",
            "Mọi claim, số liệu, so sánh, giá, thương hiệu, logo, người và địa điểm cần được kiểm tra riêng trước khi dùng.",
        ]
        if payload.message_theme == "before_after":
            cautions.append("Before/after chỉ nên dùng khi bạn có bằng chứng và quyền công bố; concept này không xác minh điều đó.")
        review = [
            "Rà soát tính chính xác của thông điệp và mọi tuyên bố trước khi đưa vào kênh công khai.",
            "Xác nhận quyền sử dụng thương hiệu, logo, con người, địa điểm và mọi reference trước khi dùng.",
            "Giữ CTA ở bước biên tập riêng; không dựa vào text, logo hoặc kết quả được sinh tự động.",
        ]
    else:
        title = f"Advertising concept: {_excerpt(payload.product, 180)}"
        topic = f"{style_label} advertising concept for {payload.product}; message to review: {payload.message}. Theme: {theme_label}."
        shot_list = [
            "Controlled close detail of the product or subject.",
            "Wide context shot to preserve the story arc.",
            "Over-the-shoulder or observational framing for one clear action.",
            "Restrained slow push-in or orbit according to the motion plan.",
            "Motivated match cut or transition, never random effect stacking.",
            "Clean final frame with empty CTA space, no invented text or watermark.",
        ]
        cautions = [
            "This is text-only concept and prompt direction; it creates no image, video, audio, preview, output or job.",
            "Every claim, number, comparison, price, brand, logo, person and location needs separate review before use.",
        ]
        if payload.message_theme == "before_after":
            cautions.append("Use before/after only when evidence and publication rights are available; this concept does not verify either.")
        review = [
            "Review the accuracy of the message and every claim before publishing anywhere.",
            "Confirm rights for brands, logos, people, locations and every reference before use.",
            "Keep CTA as a separate editorial step; do not rely on generated text, logo or result.",
        ]
    result = {
        "title": title,
        "product": payload.product,
        "message": payload.message,
        "message_theme": _cinematic_ad_choice(CINEMATIC_AD_MESSAGE_THEMES, payload.message_theme, payload.language),
        "style": _cinematic_ad_choice(CINEMATIC_AD_STYLES, payload.style, payload.language),
        "language": payload.language,
        "idea_choice": payload.idea_choice,
        "motion_choice": payload.motion_choice,
        "video_duration_variant": payload.video_duration_variant,
        "music_choice": payload.music_choice,
        "topic": topic,
        "creative_directions": directions,
        "selected_direction": directions[payload.idea_choice - 1],
        "scripts": _cinematic_ad_scripts(payload),
        "storyboard": storyboard,
        "shot_list": shot_list,
        "image_prompts": _cinematic_ad_image_prompts(payload),
        "video_prompts": _cinematic_ad_video_prompts(payload, motion),
        "motion_plan": {
            "id": str(motion["id"]),
            "title": str(motion["title"][payload.language]),
            "timeline": str(motion["timeline"]),
            "camera": str(motion["camera"]),
            "transitions": str(motion["transitions"]),
            "shot_direction": str(motion["shot_direction"]),
        },
        "music_direction": {
            "id": payload.music_choice,
            "label": str(music["label"][payload.language]),
            "direction": str(music["direction"][payload.language]),
            "ai_music_prompt": str(music["ai_music_prompt"][payload.language]),
        },
        "cautions": cautions,
        "review_before_use": review,
    }
    return CinematicAdConceptResult.model_validate(result).model_dump()


def _cinematic_ad_scene_type(*, ordinal: int, total: int) -> str:
    """Give the fixed three-beat concept editable authoring roles only."""

    if ordinal == 1:
        return "hook"
    if ordinal == total:
        return "cta"
    return "product"


def _cinematic_ad_concept_to_video_plan(
    payload: CinematicAdConceptPlanSaveRequest,
    composer: dict[str, Any],
) -> tuple[PlanPayload, list[ScenePayload]]:
    """Rebuild one Web-owned draft plan from a server-computed ad concept.

    ``composer`` is deliberately never accepted from the browser.  The
    durable Video Plan remains an authoring record, not a media request: the
    chosen creative direction, storyboard and prompt direction are retained
    only for the signed owner's later editorial work.
    """

    result = CinematicAdConceptResult.model_validate(composer)
    total = len(result.storyboard)
    image_prompts = {item.index: item for item in result.image_prompts}
    video_prompts = {item.duration_seconds: item for item in result.video_prompts}
    if total != 3 or set(image_prompts) != {1, 2, 3}:
        raise HTTPException(status_code=422, detail="Cinematic concept không đủ scene để lưu Video Plan")
    selected_video_prompt = video_prompts.get(payload.video_duration_variant)
    if selected_video_prompt is None:
        raise HTTPException(status_code=422, detail="Cinematic concept thiếu video direction phù hợp để lưu Video Plan")

    selected = result.selected_direction
    language_prefix = "Kế hoạch cinematic ad" if payload.language == "vi" else "Cinematic ad plan"
    plan_title = _line(
        f"{language_prefix} · {_excerpt(result.product, 145)}",
        label="Tên video plan cinematic concept",
        minimum=2,
        maximum=180,
    )
    plan_brief = "\n".join(
        (
            "Cinematic Ad Concept — Web-native plan rebuilt on the server.",
            f"Message theme: {result.message_theme.label}",
            f"Style: {result.style.label}",
            f"Selected direction: {selected.title}",
            "",
            "## Message to review",
            _excerpt(result.message, 1_100),
            "",
            "## Selected creative direction",
            _excerpt(selected.premise, 1_700),
            _excerpt(selected.brand_story, 1_700),
            _excerpt(selected.hook, 1_200),
            _excerpt(selected.cta, 1_200),
            "",
            "## Motion and music direction",
            _excerpt(result.motion_plan.timeline, 1_500),
            _excerpt(result.music_direction.direction, 1_500),
            "",
            "This is a draft authoring plan. It does not approve, lock, render, generate, queue or deliver media.",
        )
    )
    plan = PlanPayload.model_validate(
        {
            "title": plan_title,
            "format": "ugc" if payload.style == "ugc" else "product_demo",
            "language": payload.language,
            # The Bot ad-concept interaction was a compact mobile-first flow;
            # Web starts with a conventional vertical draft that the owner may
            # edit later in Video Studio.
            "aspect_ratio": "9:16",
            "target_duration_seconds": payload.video_duration_variant,
            "objective": _excerpt(selected.hook, 1_000),
            "audience": _excerpt(result.message_theme.label, 1_000),
            "brief": _excerpt(plan_brief, 11_900),
            "tags": [
                "cinematic-ad-concept",
                f"theme-{payload.message_theme}",
                f"style-{payload.style}",
                f"motion-{payload.motion_choice}",
                f"duration-{payload.video_duration_variant}s",
            ],
            "project_id": None,
        }
    )

    scenes: list[ScenePayload] = []
    for shot in result.storyboard:
        image_prompt = image_prompts.get(shot.index)
        if image_prompt is None:
            raise HTTPException(status_code=422, detail="Cinematic concept thiếu image direction cho một scene")
        duration = max(1, min(1_800, shot.end_seconds - shot.start_seconds))
        scene_title = _line(
            f"{'Cảnh' if payload.language == 'vi' else 'Scene'} {shot.index} — {_excerpt(shot.action, 120)}",
            label="Tên scene cinematic concept",
            minimum=2,
            maximum=180,
        )
        visual_direction = "\n".join(
            (
                _excerpt(image_prompt.prompt, 3_000),
                f"Setting: {_excerpt(shot.setting, 700)}",
                f"Subject: {_excerpt(shot.subject, 700)}",
                f"Emotion: {_excerpt(shot.emotion, 700)}",
            )
        )
        notes = "\n".join(
            (
                f"Concept timing: {shot.start_seconds}s–{shot.end_seconds}s.",
                f"Action: {_excerpt(shot.action, 900)}",
                f"Camera: {_excerpt(shot.camera, 700)}",
                f"Motion direction: {_excerpt(result.motion_plan.shot_direction, 900)}",
                f"Video direction ({payload.video_duration_variant}s variant): {_excerpt(selected_video_prompt.prompt, 1_300)}",
                f"Negative constraints: {_excerpt(selected_video_prompt.negative_prompt, 900)}",
                f"CTA/editorial space: {_excerpt(shot.cta_space, 600)}",
                "This is editable authoring metadata only; it does not start media generation.",
            )
        )
        scenes.append(
            ScenePayload.model_validate(
                {
                    "title": scene_title,
                    "scene_type": _cinematic_ad_scene_type(ordinal=shot.index, total=total),
                    "duration_seconds": duration,
                    "visual_direction": _excerpt(visual_direction, 4_600),
                    "narration": _excerpt(shot.voiceover, 2_000),
                    # CTA/on-screen copy stays under explicit editor control;
                    # this handoff never fabricates a publishing-ready claim.
                    "on_screen_text": "",
                    "shot_notes": _excerpt(notes, 4_800),
                    "transition": _excerpt(shot.transition, 480),
                    "tags": ["cinematic-ad-concept", f"scene-{shot.index}", f"style-{payload.style}"],
                }
            )
        )
    return plan, scenes


class StoryboardComposerRequest(BaseModel):
    """Strict, transient input for the Bot-derived Storyboard Prompt Pack.

    It accepts only written topic/brief and compact editorial choices.  There is
    intentionally no source media, file, URL, project, engine, provider, Bot,
    job, payment, wallet, asset, publish or idempotency field.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    topic: StrictStr
    template: StrictStr
    platform: StrictStr
    aspect_ratio: StrictStr
    duration_seconds: StrictInt
    style: StrictStr
    goal: StrictStr
    language: StrictStr
    idea_choice: StrictInt = Field(ge=1, le=3)
    brief: StrictStr = ""

    @field_validator("topic")
    @classmethod
    def validate_topic(cls, value: StrictStr) -> str:
        return _storyboard_composer_line(value, label="Chủ đề storyboard", minimum=2, maximum=STORYBOARD_COMPOSER_MAX_TOPIC)

    @field_validator("brief")
    @classmethod
    def validate_brief(cls, value: StrictStr) -> str:
        return _storyboard_composer_line(
            value,
            label="Brief bổ sung",
            minimum=0,
            maximum=STORYBOARD_COMPOSER_MAX_BRIEF,
            allow_empty=True,
        )

    @field_validator("template")
    @classmethod
    def validate_template(cls, value: StrictStr) -> str:
        return _storyboard_composer_code(value, label="Mẫu storyboard", allowed=set(STORYBOARD_COMPOSER_TEMPLATES))

    @field_validator("platform")
    @classmethod
    def validate_platform(cls, value: StrictStr) -> str:
        return _storyboard_composer_code(value, label="Nền tảng", allowed=set(STORYBOARD_COMPOSER_PLATFORMS))

    @field_validator("aspect_ratio")
    @classmethod
    def validate_aspect_ratio(cls, value: StrictStr) -> str:
        return _storyboard_composer_code(value, label="Tỷ lệ khung hình", allowed={"9:16", "16:9", "1:1"})

    @field_validator("duration_seconds")
    @classmethod
    def validate_duration_seconds(cls, value: int) -> int:
        if value not in STORYBOARD_COMPOSER_SHOT_COUNTS:
            raise ValueError("Thời lượng storyboard chỉ hỗ trợ 15, 30 hoặc 60 giây")
        return value

    @field_validator("style")
    @classmethod
    def validate_style(cls, value: StrictStr) -> str:
        return _storyboard_composer_code(value, label="Phong cách storyboard", allowed=set(STORYBOARD_COMPOSER_STYLES))

    @field_validator("goal")
    @classmethod
    def validate_goal(cls, value: StrictStr) -> str:
        return _storyboard_composer_code(value, label="Mục tiêu storyboard", allowed=set(STORYBOARD_COMPOSER_GOALS))

    @field_validator("language")
    @classmethod
    def validate_language(cls, value: StrictStr) -> str:
        return _storyboard_composer_code(value, label="Ngôn ngữ", allowed={"vi", "en"})


class StoryboardComposerPlanSaveRequest(StoryboardComposerRequest):
    """Explicit, strict handoff of original composer inputs into a Web plan.

    The browser may not submit a generated pack, scene list, plan metadata,
    Bot record, asset, provider/job/payment handle or lifecycle override.  The
    server rebuilds the deterministic pack inside its write transaction.
    """

    destination: StrictStr
    idempotency_key: StrictStr

    @field_validator("destination")
    @classmethod
    def validate_destination(cls, value: StrictStr) -> str:
        return _storyboard_composer_code(value, label="Nơi lưu storyboard", allowed={"video_plan"})

    @field_validator("idempotency_key")
    @classmethod
    def validate_idempotency_key(cls, value: StrictStr) -> str:
        return _idempotency_key(value)


class StoryboardComposerChoice(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    label: str

    @field_validator("id")
    @classmethod
    def validate_id(cls, value: str) -> str:
        return _storyboard_composer_output_line(value, label="Mã lựa chọn storyboard", minimum=1, maximum=64)

    @field_validator("label")
    @classmethod
    def validate_label(cls, value: str) -> str:
        return _storyboard_composer_output_line(value, label="Nhãn lựa chọn storyboard", maximum=180)


class StoryboardComposerCreativeDirection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    index: StrictInt = Field(ge=1, le=3)
    title: str
    premise: str
    hook: str
    structure: str
    cta: str

    @field_validator("title", "premise", "hook", "structure", "cta")
    @classmethod
    def validate_text(cls, value: str) -> str:
        return _storyboard_composer_output_line(value, label="Nội dung creative direction", maximum=2_200)


class StoryboardComposerVisualCanon(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subject: str
    setting: str
    style: str
    aspect_ratio: str
    continuity_locks: list[str] = Field(min_length=4, max_length=4)
    negative_constraints: list[str] = Field(min_length=5, max_length=5)

    @field_validator("subject", "setting", "style")
    @classmethod
    def validate_text(cls, value: str) -> str:
        return _storyboard_composer_output_line(value, label="Visual canon storyboard", maximum=1_800)

    @field_validator("aspect_ratio")
    @classmethod
    def validate_aspect_ratio(cls, value: str) -> str:
        if value not in {"9:16", "16:9", "1:1"}:
            raise ValueError("Tỷ lệ visual canon không hợp lệ")
        return value

    @field_validator("continuity_locks", "negative_constraints")
    @classmethod
    def validate_lines(cls, value: list[str], info: Any) -> list[str]:
        if not isinstance(value, list):
            raise ValueError("Danh sách visual canon không hợp lệ")
        label = "Khóa continuity" if info.field_name == "continuity_locks" else "Ràng buộc negative"
        return [_storyboard_composer_output_line(item, label=label, maximum=600) for item in value]


class StoryboardComposerShot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    index: StrictInt = Field(ge=1, le=10)
    start_seconds: StrictInt = Field(ge=0, le=60)
    end_seconds: StrictInt = Field(ge=1, le=60)
    beat: str
    visual: str
    action: str
    camera: str
    transition: str
    voiceover: str
    cta_space: str

    @field_validator("beat", "visual", "action", "camera", "transition", "voiceover", "cta_space")
    @classmethod
    def validate_text(cls, value: str) -> str:
        return _storyboard_composer_output_line(value, label="Shot storyboard", maximum=2_400)

    def model_post_init(self, __context: Any) -> None:
        if self.end_seconds <= self.start_seconds:
            raise ValueError("Mốc kết thúc shot phải lớn hơn mốc bắt đầu")


class StoryboardComposerScenePrompt(BaseModel):
    model_config = ConfigDict(extra="forbid")

    index: StrictInt = Field(ge=1, le=10)
    image_prompt: str
    video_prompt: str
    negative_prompt: str

    @field_validator("image_prompt", "video_prompt", "negative_prompt")
    @classmethod
    def validate_text(cls, value: str) -> str:
        return _storyboard_composer_output_line(value, label="Prompt cảnh storyboard", maximum=STORYBOARD_COMPOSER_MAX_TEXT)


class StoryboardComposerMetaPrompt(BaseModel):
    model_config = ConfigDict(extra="forbid")

    index: StrictInt = Field(ge=1, le=3)
    label: str
    prompt: str

    @field_validator("label")
    @classmethod
    def validate_label(cls, value: str) -> str:
        return _storyboard_composer_output_line(value, label="Nhãn prompt tham khảo", maximum=180)

    @field_validator("prompt")
    @classmethod
    def validate_prompt(cls, value: str) -> str:
        return _storyboard_composer_output_line(value, label="Prompt tham khảo", maximum=STORYBOARD_COMPOSER_MAX_TEXT)


class StoryboardComposerResult(BaseModel):
    """Exact browser schema for a deterministic, non-persistent prompt pack."""

    model_config = ConfigDict(extra="forbid")

    title: str
    topic: str
    brief: str
    template: StoryboardComposerChoice
    platform: StoryboardComposerChoice
    aspect_ratio: str
    duration_seconds: StrictInt
    style: StoryboardComposerChoice
    goal: StoryboardComposerChoice
    language: str
    idea_choice: StrictInt = Field(ge=1, le=3)
    creative_directions: list[StoryboardComposerCreativeDirection] = Field(min_length=3, max_length=3)
    selected_direction: StoryboardComposerCreativeDirection
    visual_canon: StoryboardComposerVisualCanon
    shots: list[StoryboardComposerShot] = Field(min_length=5, max_length=10)
    scene_prompts: list[StoryboardComposerScenePrompt] = Field(min_length=5, max_length=10)
    meta_ai_prompts: list[StoryboardComposerMetaPrompt] = Field(min_length=3, max_length=3)
    caption: str
    hashtags: list[str] = Field(min_length=3, max_length=8)
    cta: str
    cautions: list[str] = Field(default_factory=list, max_length=6)
    review_before_use: list[str] = Field(min_length=1, max_length=6)

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        return _storyboard_composer_output_line(value, label="Tiêu đề storyboard", maximum=320)

    @field_validator("topic")
    @classmethod
    def validate_topic(cls, value: str) -> str:
        return _storyboard_composer_output_line(value, label="Chủ đề storyboard kết quả", maximum=STORYBOARD_COMPOSER_MAX_TOPIC)

    @field_validator("brief")
    @classmethod
    def validate_brief(cls, value: str) -> str:
        return _storyboard_composer_output_line(
            value,
            label="Brief storyboard kết quả",
            minimum=0,
            maximum=STORYBOARD_COMPOSER_MAX_BRIEF,
            allow_empty=True,
        )

    @field_validator("aspect_ratio")
    @classmethod
    def validate_aspect_ratio(cls, value: str) -> str:
        if value not in {"9:16", "16:9", "1:1"}:
            raise ValueError("Tỷ lệ storyboard kết quả không hợp lệ")
        return value

    @field_validator("duration_seconds")
    @classmethod
    def validate_duration_seconds(cls, value: int) -> int:
        if value not in STORYBOARD_COMPOSER_SHOT_COUNTS:
            raise ValueError("Thời lượng storyboard kết quả không hợp lệ")
        return value

    @field_validator("language")
    @classmethod
    def validate_language(cls, value: str) -> str:
        if value not in {"vi", "en"}:
            raise ValueError("Ngôn ngữ storyboard kết quả không hợp lệ")
        return value

    @field_validator("caption", "cta")
    @classmethod
    def validate_caption_or_cta(cls, value: str) -> str:
        return _storyboard_composer_output_line(value, label="Caption hoặc CTA storyboard", maximum=1_200)

    @field_validator("hashtags", "cautions", "review_before_use")
    @classmethod
    def validate_lines(cls, value: list[str], info: Any) -> list[str]:
        if not isinstance(value, list):
            raise ValueError("Danh sách storyboard không hợp lệ")
        label = {
            "hashtags": "Hashtag storyboard",
            "cautions": "Lưu ý storyboard",
            "review_before_use": "Checklist review storyboard",
        }.get(info.field_name, "Nội dung storyboard")
        maximum = 80 if info.field_name == "hashtags" else 1_200
        return [_storyboard_composer_output_line(item, label=label, maximum=maximum) for item in value]

    def model_post_init(self, __context: Any) -> None:
        expected_choices = (
            (self.template, STORYBOARD_COMPOSER_TEMPLATES),
            (self.platform, STORYBOARD_COMPOSER_PLATFORMS),
            (self.style, STORYBOARD_COMPOSER_STYLES),
            (self.goal, STORYBOARD_COMPOSER_GOALS),
        )
        for actual, catalog in expected_choices:
            if actual.id not in catalog:
                raise ValueError("Lựa chọn storyboard kết quả không hợp lệ")
            expected = _storyboard_composer_choice(catalog, actual.id, self.language)
            if actual.model_dump() != expected:
                raise ValueError("Lựa chọn storyboard kết quả không hợp lệ")
        if [item.index for item in self.creative_directions] != [1, 2, 3]:
            raise ValueError("Creative directions phải có đúng ba lựa chọn theo thứ tự")
        if self.selected_direction.model_dump() != self.creative_directions[self.idea_choice - 1].model_dump():
            raise ValueError("Selected direction phải khớp idea choice")
        expected_count = STORYBOARD_COMPOSER_SHOT_COUNTS[self.duration_seconds]
        if len(self.shots) != expected_count or [item.index for item in self.shots] != list(range(1, expected_count + 1)):
            raise ValueError("Số shot storyboard không khớp thời lượng đã chọn")
        previous_end = 0
        for shot in self.shots:
            if shot.start_seconds != previous_end:
                raise ValueError("Shot storyboard phải phủ liên tục từ đầu đến cuối")
            previous_end = shot.end_seconds
        if previous_end != self.duration_seconds:
            raise ValueError("Shot storyboard phải kết thúc đúng thời lượng đã chọn")
        if [item.index for item in self.scene_prompts] != list(range(1, expected_count + 1)):
            raise ValueError("Prompt từng cảnh phải khớp đầy đủ shot storyboard")
        if [item.index for item in self.meta_ai_prompts] != [1, 2, 3]:
            raise ValueError("Prompt tham khảo phải có đúng ba mục theo thứ tự")


def _storyboard_composer_label(entry: dict[str, Any], language: str) -> str:
    return str(entry["label"][language])


def _storyboard_composer_choice(catalog: dict[str, dict[str, Any]], key: str, language: str) -> dict[str, str]:
    return {"id": key, "label": _storyboard_composer_label(catalog[key], language)}


def _storyboard_composer_directions(payload: StoryboardComposerRequest) -> list[dict[str, Any]]:
    topic = _excerpt(payload.topic, 160)
    brief = _excerpt(payload.brief, 220)
    template = _storyboard_composer_label(STORYBOARD_COMPOSER_TEMPLATES[payload.template], payload.language)
    goal = STORYBOARD_COMPOSER_GOALS[payload.goal]["focus"][payload.language]
    note = f" Ghi chú cần giữ: {brief}." if brief and payload.language == "vi" else (f" Keep this note in review: {brief}." if brief else "")
    if payload.language == "vi":
        return [
            {
                "index": 1,
                "title": "Bản rõ ý & dễ review",
                "premise": f"Mở bằng tình huống quen thuộc, sau đó đưa {topic} vào trong một mạch kể ngắn và rõ.",
                "hook": f"Điều gì khiến {topic} đáng dừng lại xem trong vài giây đầu?",
                "structure": f"Hook → bối cảnh → chủ thể → một chi tiết quan sát được → khung CTA sạch. Mẫu {template}; ưu tiên {goal}.{note}",
                "cta": "Mời người xem tìm hiểu thêm sau khi thông tin và quyền sử dụng đã được duyệt.",
            },
            {
                "index": 2,
                "title": "Bản lợi ích & hành động",
                "premise": f"Đặt vấn đề thực tế trước, rồi cho thấy cách {topic} xuất hiện trong một thao tác có thể review.",
                "hook": f"Một cách làm gọn gàng hơn với {topic} có thể bắt đầu từ đâu?",
                "structure": f"Vấn đề → thao tác chính → chi tiết cần review → lợi ích mô tả có điều kiện → CTA nhẹ. Mẫu {template}; ưu tiên {goal}.{note}",
                "cta": "Lưu kế hoạch này để biên tập tiếp với thông tin đã được xác minh.",
            },
            {
                "index": 3,
                "title": "Bản cảm xúc & cinematic",
                "premise": f"Biến {topic} thành một khoảnh khắc có mở đầu, chuyển biến và kết thúc bình tĩnh.",
                "hook": f"Một chi tiết nhỏ của {topic} có thể gợi ra câu chuyện nào?",
                "structure": f"Chi tiết gợi tò mò → không gian → hé lộ → hành động chính → khung kết có khoảng thở. Mẫu {template}; ưu tiên {goal}.{note}",
                "cta": "Khám phá thêm sau bước kiểm tra nội dung, thương hiệu và quyền sử dụng.",
            },
        ]
    return [
        {
            "index": 1,
            "title": "Clear, reviewable direction",
            "premise": f"Open on a familiar situation, then introduce {topic} through a concise, clear story arc.",
            "hook": f"What makes {topic} worth pausing for in the opening seconds?",
            "structure": f"Hook → context → subject → one observable detail → clean CTA frame. Template: {template}; focus: {goal}.{note}",
            "cta": "Invite viewers to learn more after the information and usage rights are approved.",
        },
        {
            "index": 2,
            "title": "Benefit and action direction",
            "premise": f"Start with a practical problem, then show how {topic} appears in one reviewable action.",
            "hook": f"Where can a clearer approach with {topic} begin?",
            "structure": f"Problem → main action → reviewable detail → conditional value description → gentle CTA. Template: {template}; focus: {goal}.{note}",
            "cta": "Save this plan for a later editorial pass with verified information.",
        },
        {
            "index": 3,
            "title": "Emotional cinematic direction",
            "premise": f"Turn {topic} into a grounded moment with an opening, a shift and a calm ending.",
            "hook": f"What small detail of {topic} can suggest a larger story?",
            "structure": f"Curious detail → environment → reveal → main action → breathing-room final frame. Template: {template}; focus: {goal}.{note}",
            "cta": "Explore the next step after reviewing content, brand material and usage rights.",
        },
    ]


def _storyboard_composer_visual_canon(payload: StoryboardComposerRequest) -> dict[str, Any]:
    topic = _excerpt(payload.topic, 160)
    style = STORYBOARD_COMPOSER_STYLES[payload.style]
    platform = _storyboard_composer_label(STORYBOARD_COMPOSER_PLATFORMS[payload.platform], payload.language)
    template = _storyboard_composer_label(STORYBOARD_COMPOSER_TEMPLATES[payload.template], payload.language)
    if payload.language == "vi":
        return {
            "subject": topic,
            "setting": f"Bối cảnh {platform} phù hợp với mẫu {template}, nền gọn và có điểm nhìn chính.",
            "style": _storyboard_composer_label(style, "vi"),
            "aspect_ratio": payload.aspect_ratio,
            "continuity_locks": [
                f"Giữ chủ thể {topic}, tỷ lệ và chi tiết nhận diện nhất quán qua mọi cảnh.",
                f"Giữ khung {payload.aspect_ratio}, ngữ cảnh {platform} và bố cục có vùng trống cho CTA biên tập sau.",
                f"Giữ ánh sáng {style['lighting']} và camera {style['camera']} có chủ đích.",
                "Mỗi shot chỉ có một hành động chính; mọi chuyển cảnh phải có động cơ và dễ review.",
            ],
            "negative_constraints": [
                "Không có watermark, chữ tự phát hoặc lỗi chính tả trong khung hình.",
                "Không thay đổi gương mặt, chủ thể, hình dáng, màu hoặc chi tiết sản phẩm giữa các cảnh.",
                "Không dùng logo, thương hiệu, giao diện hoặc nội dung chưa được cấp quyền.",
                "Không tạo thao tác phi thực tế, hình học rung, tay thừa hoặc chủ thể biến dạng.",
                "Không đưa claim, so sánh hoặc kết quả chưa được kiểm chứng vào hình, lời dẫn hay CTA.",
            ],
        }
    return {
        "subject": topic,
        "setting": f"A {platform} context matched to the {template} template, with a tidy background and one clear focal point.",
        "style": _storyboard_composer_label(style, "en"),
        "aspect_ratio": payload.aspect_ratio,
        "continuity_locks": [
            f"Keep {topic}, its proportions and identifying details consistent across every scene.",
            f"Keep the {payload.aspect_ratio} frame, {platform} context and clear empty space for later editorial CTA work.",
            f"Keep {style['lighting']} and {style['camera']} intentional throughout the plan.",
            "Use one primary action per shot; every transition must be motivated and easy to review.",
        ],
        "negative_constraints": [
            "No watermark, invented readable text or misspelled text in frame.",
            "Do not change the face, subject, shape, color or product details between scenes.",
            "Do not introduce an unlicensed logo, brand, interface or protected material.",
            "No implausible action, unstable geometry, extra hands or distorted subject.",
            "Do not put unverified claims, comparisons or results into the image, narration or CTA.",
        ],
    }


def _storyboard_composer_shots(
    payload: StoryboardComposerRequest,
    *,
    visual_canon: dict[str, Any],
    selected_direction: dict[str, Any],
) -> list[dict[str, Any]]:
    shot_count = STORYBOARD_COMPOSER_SHOT_COUNTS[payload.duration_seconds]
    span = payload.duration_seconds // shot_count
    topic = _excerpt(payload.topic, 160)
    brief = _excerpt(payload.brief, 180)
    style = STORYBOARD_COMPOSER_STYLES[payload.style]
    goal = str(STORYBOARD_COMPOSER_GOALS[payload.goal]["focus"][payload.language])
    shots: list[dict[str, Any]] = []
    for offset in range(shot_count):
        phase_index = min(
            len(STORYBOARD_COMPOSER_PHASES) - 1,
            round(offset * (len(STORYBOARD_COMPOSER_PHASES) - 1) / max(1, shot_count - 1)),
        )
        beat_id, labels, actions = STORYBOARD_COMPOSER_PHASES[phase_index]
        start = offset * span
        end = (offset + 1) * span
        if payload.language == "vi":
            visual = f"{topic} ở nhịp {labels['vi'].lower()}, bố cục sạch theo visual canon và có điểm nhìn chính."
            if brief:
                visual = f"{visual} Gợi ý brief: {brief}."
            action = f"{actions['vi'].capitalize()}; {goal}."
            transition = "Giữ khung CTA cuối" if offset == shot_count - 1 else "Clean cut hoặc match cut có động cơ"
            voiceover = f"Gợi ý lời dẫn: {selected_direction['hook'] if offset == 0 else actions['vi'].capitalize() + '.'}"
            cta_space = "Chừa vùng CTA trống; không sinh chữ, logo hoặc watermark." if offset == shot_count - 1 else "Giữ khoảng trống an toàn cho text biên tập sau."
        else:
            visual = f"{topic} at the {labels['en'].lower()} beat, with clean composition from the visual canon and one clear focal point."
            if brief:
                visual = f"{visual} Brief direction: {brief}."
            action = f"{actions['en'].capitalize()}; {goal}."
            transition = "Hold the final CTA frame" if offset == shot_count - 1 else "Motivated clean cut or match cut"
            voiceover = f"Voiceover direction: {selected_direction['hook'] if offset == 0 else actions['en'].capitalize() + '.'}"
            cta_space = "Reserve empty CTA space; no invented text, logo or watermark." if offset == shot_count - 1 else "Keep clear negative space for later editorial text."
        shots.append(
            {
                "index": offset + 1,
                "start_seconds": start,
                "end_seconds": end,
                "beat": beat_id,
                "visual": visual,
                "action": action,
                "camera": style["camera"] if offset not in {0, shot_count - 1} else f"{style['camera']}; {visual_canon['continuity_locks'][2]}",
                "transition": transition,
                "voiceover": voiceover,
                "cta_space": cta_space,
            }
        )
    return shots


def _storyboard_composer_scene_prompts(
    payload: StoryboardComposerRequest,
    *,
    visual_canon: dict[str, Any],
    shots: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    topic = _excerpt(payload.topic, 160)
    style = _storyboard_composer_label(STORYBOARD_COMPOSER_STYLES[payload.style], payload.language)
    continuity = _excerpt("; ".join(visual_canon["continuity_locks"]), 760)
    negative = _excerpt("; ".join(visual_canon["negative_constraints"]), 900)
    prompts: list[dict[str, Any]] = []
    for shot in shots:
        if payload.language == "vi":
            image_prompt = (
                f"Hướng ảnh để biên tập, không tạo ảnh: {topic}; cảnh {shot['index']} {shot['beat']}; "
                f"{shot['visual']}; phong cách {style}; khung {payload.aspect_ratio}; {continuity}"
            )
            video_prompt = (
                f"Hướng video để biên tập, không tạo video: {topic}; cảnh {shot['index']} {shot['beat']}; "
                f"hành động {shot['action']}; camera {shot['camera']}; chuyển cảnh {shot['transition']}; "
                f"{shot['start_seconds']}-{shot['end_seconds']} giây; giữ {continuity}"
            )
        else:
            image_prompt = (
                f"Editorial image direction only, no image creation: {topic}; scene {shot['index']} {shot['beat']}; "
                f"{shot['visual']}; {style} treatment; {payload.aspect_ratio} frame; {continuity}"
            )
            video_prompt = (
                f"Editorial video direction only, no video creation: {topic}; scene {shot['index']} {shot['beat']}; "
                f"action {shot['action']}; camera {shot['camera']}; transition {shot['transition']}; "
                f"{shot['start_seconds']}-{shot['end_seconds']} seconds; preserve {continuity}"
            )
        prompts.append(
            {
                "index": shot["index"],
                "image_prompt": image_prompt,
                "video_prompt": video_prompt,
                "negative_prompt": negative,
            }
        )
    return prompts


def _storyboard_composer_meta_prompts(
    payload: StoryboardComposerRequest,
    *,
    selected_direction: dict[str, Any],
) -> list[dict[str, Any]]:
    topic = _excerpt(payload.topic, 160)
    style = _storyboard_composer_label(STORYBOARD_COMPOSER_STYLES[payload.style], payload.language)
    if payload.language == "vi":
        rows = [
            ("Ngắn gọn, dễ dùng", f"Soạn một storyboard {payload.duration_seconds}s cho {topic}, phong cách {style}, gồm hook, {STORYBOARD_COMPOSER_SHOT_COUNTS[payload.duration_seconds]} shot, prompt ảnh/video từng cảnh, negative prompt và CTA mềm. Chỉ lập kế hoạch văn bản để review."),
            ("Lợi ích có kiểm soát", f"Viết concept video ngắn cho {topic}: mở bằng vấn đề quan sát được, minh họa một hành động, mô tả điều cần review rồi kết bằng CTA không phóng đại. Giữ tỉ lệ {payload.aspect_ratio} và không bịa chữ hoặc claim."),
            ("Cinematic có continuity", f"Đóng vai đạo diễn lập shot pack cho {topic}: {selected_direction['structure']} Giữ chủ thể, ánh sáng, camera, continuity và negative prompt xuyên suốt. Đây là prompt tham khảo dạng văn bản, không gọi dịch vụ hay tạo media."),
        ]
    else:
        rows = [
            ("Concise and usable", f"Draft a {payload.duration_seconds}s storyboard for {topic} in a {style} treatment, with a hook, {STORYBOARD_COMPOSER_SHOT_COUNTS[payload.duration_seconds]} shots, per-scene image/video directions, negative constraints and a gentle CTA. Produce reviewable planning text only."),
            ("Controlled benefit direction", f"Write a short video concept for {topic}: begin with an observable problem, show one action, describe what needs review, then end with a non-exaggerated CTA. Keep {payload.aspect_ratio} framing and invent neither readable text nor claims."),
            ("Cinematic continuity", f"Act as an editorial director preparing a shot pack for {topic}: {selected_direction['structure']} Preserve subject, light, camera, continuity and negative constraints throughout. This is reference planning text only; do not call a service or create media."),
        ]
    return [{"index": index, "label": label, "prompt": prompt} for index, (label, prompt) in enumerate(rows, start=1)]


def _compose_storyboard_composer(payload: StoryboardComposerRequest) -> dict[str, Any]:
    """Reimplement only Bot ``storypack`` planning semantics for the Web.

    The Bot flow had template choices, three directions, a visual canon,
    5/6/10-scene packs, image/video/negative directions and three copy prompts.
    The Web version deliberately omits its Telegram state, save/lock actions,
    media generation, uploads, previews, jobs, wallet/Xu and payment flow.
    """

    directions = _storyboard_composer_directions(payload)
    selected_direction = directions[payload.idea_choice - 1]
    visual_canon = _storyboard_composer_visual_canon(payload)
    shots = _storyboard_composer_shots(payload, visual_canon=visual_canon, selected_direction=selected_direction)
    scene_prompts = _storyboard_composer_scene_prompts(payload, visual_canon=visual_canon, shots=shots)
    meta_ai_prompts = _storyboard_composer_meta_prompts(payload, selected_direction=selected_direction)
    topic = _excerpt(payload.topic, 160)
    if payload.language == "vi":
        caption = f"{topic} trong một storyboard {payload.duration_seconds}s rõ nhịp, có chủ thể nhất quán và CTA mềm để biên tập sau."
        hashtags = ["#TOANAAS", "#Storyboard", "#PromptVideo", "#AIVideo"]
        cautions = [
            "Đây là storyboard và prompt pack dạng văn bản; không tạo ảnh, video, audio, preview, output hoặc job.",
            "Mọi claim, số liệu, giá, thương hiệu, logo, người, địa điểm và reference cần được kiểm tra riêng trước khi dùng.",
            "Prompt tham khảo theo kiểu Meta AI chỉ để copy/biên tập; Web App không gọi Meta hoặc bất kỳ dịch vụ tạo media nào.",
        ]
        review = [
            "Rà soát tính chính xác của chủ đề, brief và mọi tuyên bố trước khi công khai.",
            "Xác nhận quyền sử dụng thương hiệu, logo, con người, địa điểm và mọi tài liệu tham chiếu.",
            "Kiểm tra continuity của chủ thể, text/CTA, khung hình và khả năng thực hiện trước khi chuyển sang một workflow riêng.",
        ]
    else:
        caption = f"{topic} in a {payload.duration_seconds}s storyboard with clear pacing, consistent subject direction and a gentle CTA for later editorial work."
        hashtags = ["#TOANAAS", "#Storyboard", "#PromptVideo", "#AIVideo"]
        cautions = [
            "This is a text-only storyboard and prompt pack; it creates no image, video, audio, preview, output or job.",
            "Every claim, number, price, brand, logo, person, location and reference needs separate review before use.",
            "The Meta-AI-style copy prompts are only for copying or editing; the Web App calls neither Meta nor any media-creation service.",
        ]
        review = [
            "Review the accuracy of the topic, brief and every claim before any public use.",
            "Confirm rights for brands, logos, people, locations and every reference.",
            "Review subject continuity, text/CTA, framing and feasibility before moving this direction into a separate workflow.",
        ]
    result = {
        "title": f"Storyboard Prompt Pack: {topic}" if payload.language == "en" else f"Gói storyboard + prompt: {topic}",
        "topic": payload.topic,
        "brief": payload.brief,
        "template": _storyboard_composer_choice(STORYBOARD_COMPOSER_TEMPLATES, payload.template, payload.language),
        "platform": _storyboard_composer_choice(STORYBOARD_COMPOSER_PLATFORMS, payload.platform, payload.language),
        "aspect_ratio": payload.aspect_ratio,
        "duration_seconds": payload.duration_seconds,
        "style": _storyboard_composer_choice(STORYBOARD_COMPOSER_STYLES, payload.style, payload.language),
        "goal": _storyboard_composer_choice(STORYBOARD_COMPOSER_GOALS, payload.goal, payload.language),
        "language": payload.language,
        "idea_choice": payload.idea_choice,
        "creative_directions": directions,
        "selected_direction": selected_direction,
        "visual_canon": visual_canon,
        "shots": shots,
        "scene_prompts": scene_prompts,
        "meta_ai_prompts": meta_ai_prompts,
        "caption": caption,
        "hashtags": hashtags,
        "cta": selected_direction["cta"],
        "cautions": cautions,
        "review_before_use": review,
    }
    return StoryboardComposerResult.model_validate(result).model_dump()


class PlanPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    format: str = "short_form"
    language: str = "vi"
    aspect_ratio: str = "9:16"
    target_duration_seconds: int = Field(ge=1, le=7200)
    objective: str = ""
    audience: str = ""
    brief: str
    tags: list[str] = Field(default_factory=list)
    project_id: str | None = None

    @field_validator("title")
    @classmethod
    def _title(cls, value: str) -> str:
        return _line(value, label="Tên video plan", minimum=2, maximum=180)

    @field_validator("format")
    @classmethod
    def _format(cls, value: str) -> str:
        normalized = _line(value, label="Loại video plan", minimum=1, maximum=32).lower()
        if normalized not in PLAN_FORMATS:
            raise ValueError("Loại video plan không hợp lệ")
        return normalized

    @field_validator("language")
    @classmethod
    def _language(cls, value: str) -> str:
        return _line(value, label="Ngôn ngữ", minimum=1, maximum=100)

    @field_validator("aspect_ratio")
    @classmethod
    def _ratio(cls, value: str) -> str:
        normalized = _line(value, label="Tỷ lệ khung hình", minimum=1, maximum=32)
        if normalized not in ASPECT_RATIOS:
            raise ValueError("Tỷ lệ khung hình không hợp lệ")
        return normalized

    @field_validator("objective")
    @classmethod
    def _objective(cls, value: str) -> str:
        return _body(value, label="Mục tiêu", maximum=1200, allow_empty=True)

    @field_validator("audience")
    @classmethod
    def _audience(cls, value: str) -> str:
        return _body(value, label="Đối tượng", maximum=1200, allow_empty=True)

    @field_validator("brief")
    @classmethod
    def _brief(cls, value: str) -> str:
        return _body(value, label="Creative brief", maximum=12000)

    @field_validator("tags")
    @classmethod
    def _tag_values(cls, value: list[str]) -> list[str]:
        return _tags(value)

    @field_validator("project_id")
    @classmethod
    def _project(cls, value: str | None) -> str | None:
        return _optional_uuid(value, label="Project ID")


class PlanCreateRequest(PlanPayload):
    idempotency_key: str

    @field_validator("idempotency_key")
    @classmethod
    def _key(cls, value: str) -> str:
        return _idempotency_key(value)


class PlanUpdateRequest(PlanPayload):
    expected_revision: int = Field(ge=1)
    idempotency_key: str

    @field_validator("idempotency_key")
    @classmethod
    def _key(cls, value: str) -> str:
        return _idempotency_key(value)


class RevisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_revision: int = Field(ge=1)
    idempotency_key: str

    @field_validator("idempotency_key")
    @classmethod
    def _key(cls, value: str) -> str:
        return _idempotency_key(value)


class RestoreVersionRequest(RevisionRequest):
    target_revision: int = Field(ge=1)


class LifecycleRequest(RevisionRequest):
    state: str

    @field_validator("state")
    @classmethod
    def _state(cls, value: str) -> str:
        normalized = _line(value, label="Trạng thái", minimum=1, maximum=20).lower()
        if normalized not in PLAN_STATES:
            raise ValueError("Trạng thái video plan không hợp lệ")
        return normalized


class ScenePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    scene_type: str = "custom"
    duration_seconds: int = Field(ge=1, le=1800)
    visual_direction: str = ""
    narration: str = ""
    on_screen_text: str = ""
    shot_notes: str = ""
    transition: str = ""
    tags: list[str] = Field(default_factory=list)

    @field_validator("title")
    @classmethod
    def _title(cls, value: str) -> str:
        return _line(value, label="Tên scene", minimum=2, maximum=180)

    @field_validator("scene_type")
    @classmethod
    def _kind(cls, value: str) -> str:
        normalized = _line(value, label="Vai trò scene", minimum=1, maximum=32).lower()
        if normalized not in SCENE_TYPES:
            raise ValueError("Vai trò scene không hợp lệ")
        return normalized

    @field_validator("visual_direction")
    @classmethod
    def _visual(cls, value: str) -> str:
        return _body(value, label="Visual direction", maximum=5000, allow_empty=True)

    @field_validator("narration")
    @classmethod
    def _narration(cls, value: str) -> str:
        return _body(value, label="Narration", maximum=5000, allow_empty=True)

    @field_validator("on_screen_text")
    @classmethod
    def _screen_text(cls, value: str) -> str:
        return _body(value, label="Text trên màn hình", maximum=3000, allow_empty=True)

    @field_validator("shot_notes")
    @classmethod
    def _shot_notes(cls, value: str) -> str:
        return _body(value, label="Ghi chú quay dựng", maximum=5000, allow_empty=True)

    @field_validator("transition")
    @classmethod
    def _transition(cls, value: str) -> str:
        return _line(value, label="Chuyển cảnh", minimum=0, maximum=500, allow_empty=True)

    @field_validator("tags")
    @classmethod
    def _tag_values(cls, value: list[str]) -> list[str]:
        return _tags(value)


class SceneCreateRequest(ScenePayload):
    expected_revision: int = Field(ge=1)
    idempotency_key: str

    @field_validator("idempotency_key")
    @classmethod
    def _key(cls, value: str) -> str:
        return _idempotency_key(value)


class SceneUpdateRequest(ScenePayload):
    expected_revision: int = Field(ge=1)
    idempotency_key: str

    @field_validator("idempotency_key")
    @classmethod
    def _key(cls, value: str) -> str:
        return _idempotency_key(value)


class ReorderRequest(RevisionRequest):
    scene_ids: list[str] = Field(min_length=1, max_length=MAX_SCENES_PER_PLAN)

    @field_validator("scene_ids")
    @classmethod
    def _ids(cls, value: list[str]) -> list[str]:
        values = [_uuid(item, label="Scene ID") for item in value]
        if len(values) != len(set(values)):
            raise ValueError("Scene ID không được trùng")
        return values


def _storyboard_composer_plan_format(template: str) -> str:
    """Map the small Composer template vocabulary onto existing plan formats."""

    return {
        "product_ad": "product_demo",
        "cinematic_story": "campaign",
        "tiktok_reels": "short_form",
        "tutorial": "explainer",
        "shop_affiliate": "product_demo",
        "custom": "custom",
    }[template]


def _storyboard_composer_scene_type(*, ordinal: int, total: int) -> str:
    """Give generated scenes a truthful editable role without execution semantics."""

    if ordinal == 1:
        return "hook"
    if ordinal == total:
        return "cta"
    if ordinal == 2:
        return "problem"
    if ordinal == total - 1:
        return "proof"
    return "solution"


def _storyboard_composer_to_video_plan(
    payload: StoryboardComposerRequest,
    composer: dict[str, Any],
) -> tuple[PlanPayload, list[ScenePayload]]:
    """Derive one durable Web plan and editable scenes from a server result.

    ``composer`` is never accepted from the browser.  Revalidating it here
    keeps the persistence mapping coupled to the deterministic generator and
    deliberately prevents a client-generated scene pack from becoming a write
    contract.
    """

    result = StoryboardComposerResult.model_validate(composer)
    scene_prompts = {item.index: item for item in result.scene_prompts}
    total = len(result.shots)
    if total < 1 or total != len(scene_prompts):
        raise HTTPException(status_code=422, detail="Storyboard đã dựng không đủ scene để lưu kế hoạch")

    language_prefix = "Kế hoạch storyboard" if payload.language == "vi" else "Storyboard plan"
    plan_title = _line(
        f"{language_prefix} · {_excerpt(payload.topic, 145)}",
        label="Tên video plan storyboard",
        minimum=2,
        maximum=180,
    )
    selected = result.selected_direction
    canon = result.visual_canon
    plan_brief = "\n".join(
        (
            "Storyboard Prompt Pack — Web-native plan rebuilt on the server.",
            f"Template: {result.template.label}",
            f"Platform: {result.platform.label}",
            f"Style: {result.style.label}",
            f"Goal: {result.goal.label}",
            "",
            "## Selected creative direction",
            selected.premise,
            selected.structure,
            "",
            "## Visual canon",
            canon.setting,
            *[f"- {item}" for item in canon.continuity_locks],
            "",
            "This is a draft authoring plan. It does not approve, lock, render, generate, queue or deliver media.",
        )
    )
    plan = PlanPayload.model_validate(
        {
            "title": plan_title,
            "format": _storyboard_composer_plan_format(payload.template),
            "language": payload.language,
            "aspect_ratio": payload.aspect_ratio,
            "target_duration_seconds": payload.duration_seconds,
            "objective": result.goal.label,
            "audience": result.platform.label,
            "brief": _excerpt(plan_brief, 11_900),
            "tags": [
                "storyboard-composer",
                f"template-{payload.template}",
                f"platform-{payload.platform}",
                f"style-{payload.style}",
                f"goal-{payload.goal}",
            ],
            "project_id": None,
        }
    )

    scenes: list[ScenePayload] = []
    for shot in result.shots:
        prompt = scene_prompts.get(shot.index)
        if prompt is None:
            raise HTTPException(status_code=422, detail="Storyboard thiếu prompt cho một scene")
        duration = shot.end_seconds - shot.start_seconds
        scene_title = _line(
            f"{'Cảnh' if payload.language == 'vi' else 'Scene'} {shot.index} — {_excerpt(shot.beat, 120)}",
            label="Tên scene storyboard",
            minimum=2,
            maximum=180,
        )
        notes = "\n\n".join(
            (
                f"Video direction:\n{_excerpt(prompt.video_prompt, 2_900)}",
                f"Negative constraints:\n{_excerpt(prompt.negative_prompt, 1_000)}",
                f"CTA / editorial space:\n{_excerpt(shot.cta_space, 500)}",
            )
        )
        scenes.append(
            ScenePayload.model_validate(
                {
                    "title": scene_title,
                    "scene_type": _storyboard_composer_scene_type(ordinal=shot.index, total=total),
                    "duration_seconds": duration,
                    "visual_direction": _excerpt(prompt.image_prompt, 4_600),
                    "narration": _excerpt(shot.voiceover, 2_000),
                    # The Composer reserves text/CTA for an editor; it does
                    # not fabricate on-screen copy during this handoff.
                    "on_screen_text": "",
                    "shot_notes": _excerpt(notes, 4_800),
                    "transition": _excerpt(shot.transition, 480),
                    "tags": ["storyboard-composer", f"scene-{shot.index}", f"beat-{shot.beat}"],
                }
            )
        )
    return plan, scenes


def _image_motion_scene_windows(duration_seconds: int) -> list[tuple[int, int]]:
    """Split a short planning duration into three non-zero editable beats."""

    base, remainder = divmod(duration_seconds, 3)
    durations = [base + (1 if index < remainder else 0) for index in range(3)]
    start = 0
    windows: list[tuple[int, int]] = []
    for duration in durations:
        end = start + duration
        windows.append((start, end))
        start = end
    return windows


def _image_motion_choice(catalog: dict[str, dict[str, str]], key: str) -> dict[str, str]:
    entry = catalog[key]
    return {"id": key, "label": _line(entry["label"], label="Nhãn Image Motion", minimum=2, maximum=180)}


def _image_motion_marker(reference: dict[str, Any]) -> str:
    """Screen stored direction text without exposing it to the browser."""

    return _planner_guard_marker(
        reference.get("direction_title"),
        reference.get("prompt_text"),
        reference.get("edit_instructions"),
        reference.get("composition_notes"),
        reference.get("negative_direction"),
    )


def _compose_image_motion_planner(
    payload: ImageMotionPlannerRequest,
    reference: dict[str, Any],
) -> dict[str, Any]:
    """Create a deterministic image-to-motion authoring receipt, not media.

    The selected image itself is intentionally never opened.  The result is a
    compact three-beat editorial plan around the *private direction title* and
    fixed local choices.  It is deliberately useful without asserting that a
    source image, video, preview, audio or engine output exists.
    """

    style = IMAGE_MOTION_PLANNER_STYLES[payload.style]
    motion = IMAGE_MOTION_PLANNER_MOTIONS[payload.motion]
    music = IMAGE_MOTION_PLANNER_MUSIC[payload.music]
    windows = _image_motion_scene_windows(payload.duration_seconds)
    source_title = reference["direction_title"]
    subject = f"the subject and composition described by the private Image Studio direction “{source_title}”"
    beats = (
        {
            "title": "Thiết lập continuity",
            "visual_direction": f"Establish {subject}; preserve recognizable subject geometry, legitimate marks and the existing composition direction. {style['direction']}.",
            "camera": "stable establishing frame with a controlled focal anchor",
            "transition": "clean opening hold",
            "editorial_note": "Kế hoạch không đọc hoặc phân tích ảnh; editor cần kiểm tra visual continuity trên nguồn hợp lệ trước khi thực thi.",
        },
        {
            "title": "Chuyển động chính",
            "visual_direction": f"Keep {subject} consistent while {motion['action']}. Maintain natural depth, lighting and object relationships.",
            "camera": motion["camera"],
            "transition": motion["transition"],
            "editorial_note": "Không tạo frame, footage, preview hoặc yêu cầu provider. Đây là direction để editor review.",
        },
        {
            "title": "Hero frame để review",
            "visual_direction": f"Resolve on a stable hero frame for {subject}; leave any copy/CTA as an empty editorial decision and do not invent readable text or logos.",
            "camera": "stable hero hold with clear subject separation",
            "transition": "clean settle",
            "editorial_note": "Xác nhận quyền sử dụng, thương hiệu, claim và consent trước khi đưa plan vào một execution workflow đã được cấp riêng.",
        },
    )
    scenes: list[dict[str, Any]] = []
    for index, (start, end) in enumerate(windows, start=1):
        beat = beats[index - 1]
        scenes.append(
            {
                "index": index,
                "start_seconds": start,
                "end_seconds": end,
                "title": beat["title"],
                "visual_direction": beat["visual_direction"],
                "camera": beat["camera"],
                "transition": beat["transition"],
                "audio_direction": music["direction"],
                "editorial_note": beat["editorial_note"],
            }
        )
    result = {
        "reference": _image_motion_reference_public(reference),
        "title": f"Image Motion Plan — {source_title}",
        "style": _image_motion_choice(IMAGE_MOTION_PLANNER_STYLES, payload.style),
        "motion": _image_motion_choice(IMAGE_MOTION_PLANNER_MOTIONS, payload.motion),
        "music": _image_motion_choice(IMAGE_MOTION_PLANNER_MUSIC, payload.music),
        "duration_seconds": payload.duration_seconds,
        "scenes": scenes,
        "review_before_use": [
            "Kiểm tra rằng Image Studio direction và ảnh Image Vault còn thuộc account hiện tại trước khi dùng ở workflow khác.",
            "Rà soát continuity của chủ thể, thương hiệu/logo hợp lệ, claim, consent và quyền sử dụng trước khi thực thi.",
            "Đây là Video Plan direction; xác nhận riêng một workflow có engine/provider đã được cấp nếu sau này cần tạo media.",
        ],
    }
    return ImageMotionPlannerResult.model_validate(result).model_dump()


def _image_motion_planner_to_video_plan(
    payload: ImageMotionPlannerPlanSaveRequest,
    planner: dict[str, Any],
) -> tuple[PlanPayload, list[ScenePayload]]:
    """Convert server-recomputed planning text into an editable private plan."""

    result = ImageMotionPlannerResult.model_validate(planner)
    ratio = result.reference.aspect_ratio if result.reference.aspect_ratio in ASPECT_RATIOS else "custom"
    plan = PlanPayload.model_validate(
        {
            "title": _line(result.title, label="Tên Image Motion Video Plan", minimum=2, maximum=180),
            "format": "short_form",
            "language": result.reference.language,
            "aspect_ratio": ratio,
            "target_duration_seconds": result.duration_seconds,
            "objective": "Private image-to-motion editorial plan derived from an owner-scoped Image Studio direction.",
            "audience": "Private Web editor",
            "brief": _body(
                "\n".join(
                    (
                        "This is a private, editable Image Motion authoring plan.",
                        f"Source direction: {result.reference.direction_title}.",
                        f"Style: {result.style.label}. Motion: {result.motion.label}. Music direction: {result.music.label}.",
                        "The source image was not opened or inspected. Saving this plan does not create, queue, render or deliver media.",
                    )
                ),
                label="Brief Image Motion Video Plan",
                maximum=11_900,
            ),
            "tags": [
                "image-motion-planner",
                f"style-{payload.style}",
                f"motion-{payload.motion}",
                f"music-{payload.music}",
            ],
            "project_id": None,
        }
    )
    scenes: list[ScenePayload] = []
    for scene in result.scenes:
        notes = "\n".join(
            (
                f"Planner timing: {scene.start_seconds}s–{scene.end_seconds}s.",
                f"Camera: {scene.camera}",
                f"Audio direction: {scene.audio_direction}",
                f"Editorial note: {scene.editorial_note}",
                "No source media was inspected and no media generation was started.",
            )
        )
        scenes.append(
            ScenePayload.model_validate(
                {
                    "title": _line(f"Scene {scene.index} — {scene.title}", label="Tên Image Motion scene", minimum=2, maximum=180),
                    "scene_type": _video_prompt_planner_scene_type(ordinal=scene.index, total=len(result.scenes)),
                    "duration_seconds": scene.end_seconds - scene.start_seconds,
                    "visual_direction": _body(scene.visual_direction, label="Image Motion visual direction", maximum=4_600),
                    "narration": "",
                    "on_screen_text": "",
                    "shot_notes": _body(notes, label="Image Motion scene notes", maximum=4_800),
                    "transition": _line(scene.transition, label="Image Motion transition", minimum=2, maximum=480),
                    "tags": ["image-motion-planner", f"scene-{scene.index}", f"motion-{payload.motion}"],
                }
            )
        )
    return plan, scenes


def _reference_format_choice(catalog: dict[str, dict[str, str]], key: str) -> dict[str, str]:
    entry = catalog[key]
    return {
        "id": key,
        "label": _line(entry["label"], label="Nhãn Reference Format", minimum=2, maximum=180),
    }


def _compose_reference_format_planner(
    payload: ReferenceFormatPlannerRequest,
    reference: dict[str, Any],
) -> dict[str, Any]:
    """Build a deterministic, original 3-beat plan from bounded Web inputs.

    The chosen Asset Vault video is a private metadata selector only.  This is
    deliberately not a video-analysis response: no source bytes, frames,
    transcript, duration, camera motion or content were opened or inferred.
    It uses the Bot's broad *planning* shape—direction, topic, hook/middle/end
    and channel goal—while requiring a newly supplied topic and audience.
    """

    direction = REFERENCE_FORMAT_PLANNER_DIRECTIONS[payload.direction]
    platform = REFERENCE_FORMAT_PLANNER_PLATFORMS[payload.platform]
    goal = REFERENCE_FORMAT_PLANNER_GOALS[payload.goal]
    tone = REFERENCE_FORMAT_PLANNER_TONES[payload.tone]
    windows = _image_motion_scene_windows(payload.duration_seconds)
    if payload.language == "en":
        beat_specs = (
            ("Original opening hook", "Open with one original, observable situation for the new topic; do not reproduce the source video's people, brand, wording, shots or timing."),
            ("Clear middle demonstration", "Show one new, reviewable action or explanation for the new topic. Keep all claims conditional until a human checks evidence."),
            ("Original resolution & CTA space", "Resolve into a stable original hero frame with room for a gentle editorial CTA; do not invent readable text, marks or performance claims."),
        )
        source_note = "The selected Asset Vault video was not opened, fetched, decoded, sampled or analyzed. It is only a current-account reference permission check."
        camera_prefix = "Editorial camera direction"
        audio_prefix = "Tone direction"
        review = [
            "Confirm you have the right to use the selected source as a private reference before any further workflow.",
            "Replace every identity, brand, logo, voice, wording, shot order and protected element with original work; this plan does not verify rights.",
            "Check factual claims, prices, disclosures, consent and platform policies before a separate approved execution or publishing workflow.",
        ]
        title = f"Reference Format Plan — {payload.topic}"
    else:
        beat_specs = (
            ("Hook nguyên bản", "Mở bằng một tình huống quan sát được cho chủ đề mới; không lặp lại người, thương hiệu, câu chữ, shot hay nhịp của video nguồn."),
            ("Demo / bằng chứng cần review", "Diễn giải một thao tác hoặc giải thích mới cho chủ đề; mọi claim vẫn cần người dùng kiểm tra bằng chứng trước khi dùng."),
            ("Kết nguyên bản & khoảng CTA", "Kết ở hero frame nguyên bản, chừa khoảng CTA mềm để biên tập; không bịa chữ, dấu hiệu nhận diện hoặc tuyên bố hiệu quả."),
        )
        source_note = "Video Asset Vault được chọn không bị mở, tải, giải mã, cắt frame hoặc phân tích. Nó chỉ là kiểm tra quyền tham chiếu thuộc Web account hiện tại."
        camera_prefix = "Hướng camera biên tập"
        audio_prefix = "Hướng giọng / âm thanh"
        review = [
            "Xác nhận bạn có quyền dùng video đã chọn làm tham chiếu riêng tư trước khi chuyển sang workflow khác.",
            "Thay toàn bộ nhận diện, thương hiệu, logo, giọng nói, câu chữ, shot order và phần tử có bảo hộ bằng sáng tạo nguyên bản; plan này không xác minh quyền.",
            "Rà soát claim, giá, disclosure, consent và chính sách nền tảng trước khi dùng một execution hoặc publishing workflow được cấp riêng.",
        ]
        title = f"Kế hoạch format tham chiếu — {payload.topic}"
    scenes: list[dict[str, Any]] = []
    for index, (start, end) in enumerate(windows, start=1):
        beat_title, original_direction = beat_specs[index - 1]
        if payload.language == "en":
            visual = (
                f"{original_direction} New topic: {payload.topic}. Audience: {payload.audience}. "
                f"Reference format direction: {direction['hook'] if index == 1 else direction['middle'] if index == 2 else direction['finish']}. "
                f"Platform: {platform['label']}; target objective: {goal['direction']}."
            )
            camera = f"{camera_prefix}: {direction['camera']}"
            audio = f"{audio_prefix}: {tone['direction']}; no audio is generated."
            editorial = f"{source_note} This is scene {index} of a text-only private plan; it creates no media, preview, job, payment or publish action."
        else:
            visual = (
                f"{original_direction} Chủ đề mới: {payload.topic}. Khán giả: {payload.audience}. "
                f"Hướng format: {direction['hook'] if index == 1 else direction['middle'] if index == 2 else direction['finish']}. "
                f"Nền tảng: {platform['label']}; mục tiêu: {goal['direction']}."
            )
            camera = f"{camera_prefix}: {direction['camera']}"
            audio = f"{audio_prefix}: {tone['direction']}; không có audio được tạo."
            editorial = f"{source_note} Đây là scene {index} của plan text riêng tư; không tạo media, preview, job, thanh toán hay publish action."
        scenes.append(
            {
                "index": index,
                "start_seconds": start,
                "end_seconds": end,
                "title": beat_title,
                "visual_direction": visual,
                "camera": camera,
                "transition": direction["transition"],
                "audio_direction": audio,
                "editorial_note": editorial,
            }
        )
    result = {
        "reference": _reference_format_reference_public(reference),
        "title": title,
        "direction": _reference_format_choice(REFERENCE_FORMAT_PLANNER_DIRECTIONS, payload.direction),
        "platform": _reference_format_choice(REFERENCE_FORMAT_PLANNER_PLATFORMS, payload.platform),
        "goal": _reference_format_choice(REFERENCE_FORMAT_PLANNER_GOALS, payload.goal),
        "tone": _reference_format_choice(REFERENCE_FORMAT_PLANNER_TONES, payload.tone),
        "topic": payload.topic,
        "audience": payload.audience,
        "language": payload.language,
        "duration_seconds": payload.duration_seconds,
        "scenes": scenes,
        "review_before_use": review,
    }
    return ReferenceFormatPlannerResult.model_validate(result).model_dump()


def _reference_format_planner_to_video_plan(
    payload: ReferenceFormatPlannerPlanSaveRequest,
    planner: dict[str, Any],
) -> tuple[PlanPayload, list[ScenePayload]]:
    """Persist only server-recomputed text as a private editable Video Plan."""

    result = ReferenceFormatPlannerResult.model_validate(planner)
    ratio = REFERENCE_FORMAT_PLANNER_PLATFORMS[payload.platform]["aspect_ratio"]
    plan = PlanPayload.model_validate(
        {
            "title": _line(result.title, label="Tên Reference Format Video Plan", minimum=2, maximum=180),
            "format": "short_form",
            "language": result.language,
            "aspect_ratio": ratio,
            "target_duration_seconds": result.duration_seconds,
            "objective": _body(
                f"{result.goal.label}: {REFERENCE_FORMAT_PLANNER_GOALS[payload.goal]['direction']}",
                label="Mục tiêu Reference Format Video Plan",
                maximum=1_200,
            ),
            "audience": result.audience,
            "brief": _body(
                "\n".join(
                    (
                        "This is a private, editable Reference Format authoring plan.",
                        f"Selected Asset Vault video: {result.reference.display_name}.",
                        f"Direction: {result.direction.label}. Platform: {result.platform.label}. Tone: {result.tone.label}.",
                        "The selected video was not opened or analyzed. Saving this plan does not create, queue, render or deliver media.",
                    )
                ),
                label="Brief Reference Format Video Plan",
                maximum=11_900,
            ),
            "tags": [
                "reference-format-planner",
                f"direction-{payload.direction}",
                f"platform-{payload.platform}",
                f"goal-{payload.goal}",
                f"tone-{payload.tone}",
            ],
            "project_id": None,
        }
    )
    scenes: list[ScenePayload] = []
    for scene in result.scenes:
        notes = "\n".join(
            (
                f"Planner timing: {scene.start_seconds}s–{scene.end_seconds}s.",
                f"Camera: {scene.camera}",
                f"Audio direction: {scene.audio_direction}",
                f"Editorial note: {scene.editorial_note}",
                "No source video was opened/analyzed and no media generation was started.",
            )
        )
        scenes.append(
            ScenePayload.model_validate(
                {
                    "title": _line(f"Scene {scene.index} — {scene.title}", label="Tên Reference Format scene", minimum=2, maximum=180),
                    "scene_type": _video_prompt_planner_scene_type(ordinal=scene.index, total=len(result.scenes)),
                    "duration_seconds": scene.end_seconds - scene.start_seconds,
                    "visual_direction": _body(scene.visual_direction, label="Reference Format visual direction", maximum=4_600),
                    "narration": "",
                    "on_screen_text": "",
                    "shot_notes": _body(notes, label="Reference Format scene notes", maximum=4_800),
                    "transition": _line(scene.transition, label="Reference Format transition", minimum=2, maximum=480),
                    "tags": ["reference-format-planner", f"scene-{scene.index}", f"direction-{payload.direction}"],
                }
            )
        )
    return plan, scenes


def _boundary(**extra: Any) -> dict[str, Any]:
    return {
        "execution": "authoring_only",
        "provider_called": False,
        "video_created": False,
        "media_uploads": False,
        "preview_available": False,
        "output_delivery": "guarded",
        **extra,
    }


def _safe_receipt(response: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(response, dict) or response.get("ok") is not True:
        return response
    source = response.get("data") if isinstance(response.get("data"), dict) else {}
    if source.get("_reference_format_planner_plan_save") is True:
        plan = source.get("plan") if isinstance(source.get("plan"), dict) else {}
        plan_id = str(plan.get("id") or "")
        if not plan_id:
            raise HTTPException(status_code=500, detail="Receipt lưu Reference Format plan không hợp lệ")
        try:
            normalized_plan_id = str(uuid.UUID(plan_id))
        except (ValueError, TypeError, AttributeError) as exc:
            raise HTTPException(status_code=500, detail="Receipt lưu Reference Format plan không hợp lệ") from exc
        scene_count = source.get("scene_count")
        if isinstance(scene_count, bool) or not isinstance(scene_count, int) or not 1 <= scene_count <= MAX_SCENES_PER_PLAN:
            raise HTTPException(status_code=500, detail="Receipt lưu Reference Format plan không hợp lệ")
        data = {
            "destination": "video_plan",
            "plan": {
                "id": normalized_plan_id,
                "revision": 1,
                "state": "draft",
            },
            "scene_count": scene_count,
            **_reference_format_plan_save_boundary(),
        }
        return envelope(
            True,
            str(response.get("message") or "Đã lưu Reference Format Plan thành Video Plan riêng tư."),
            data=data,
            status_name="draft",
        )
    if source.get("_image_motion_planner_plan_save") is True:
        plan = source.get("plan") if isinstance(source.get("plan"), dict) else {}
        plan_id = str(plan.get("id") or "")
        if not plan_id:
            raise HTTPException(status_code=500, detail="Receipt lưu Image Motion plan không hợp lệ")
        try:
            normalized_plan_id = str(uuid.UUID(plan_id))
        except (ValueError, TypeError, AttributeError) as exc:
            raise HTTPException(status_code=500, detail="Receipt lưu Image Motion plan không hợp lệ") from exc
        scene_count = source.get("scene_count")
        if isinstance(scene_count, bool) or not isinstance(scene_count, int) or not 1 <= scene_count <= MAX_SCENES_PER_PLAN:
            raise HTTPException(status_code=500, detail="Receipt lưu Image Motion plan không hợp lệ")
        data = {
            "destination": "video_plan",
            "plan": {
                "id": normalized_plan_id,
                "revision": 1,
                "state": "draft",
            },
            "scene_count": scene_count,
            **_image_motion_plan_save_boundary(),
        }
        return envelope(
            True,
            str(response.get("message") or "Đã lưu Image Motion Plan thành Video Plan riêng tư."),
            data=data,
            status_name="draft",
        )
    if source.get("_cinematic_ad_concept_plan_save") is True:
        plan = source.get("plan") if isinstance(source.get("plan"), dict) else {}
        plan_id = str(plan.get("id") or "")
        if not plan_id:
            raise HTTPException(status_code=500, detail="Receipt lưu cinematic concept plan không hợp lệ")
        try:
            normalized_plan_id = str(uuid.UUID(plan_id))
        except (ValueError, TypeError, AttributeError) as exc:
            raise HTTPException(status_code=500, detail="Receipt lưu cinematic concept plan không hợp lệ") from exc
        scene_count = source.get("scene_count")
        if isinstance(scene_count, bool) or not isinstance(scene_count, int) or not 1 <= scene_count <= MAX_SCENES_PER_PLAN:
            raise HTTPException(status_code=500, detail="Receipt lưu cinematic concept plan không hợp lệ")
        data = {
            "destination": "video_plan",
            "plan": {
                "id": normalized_plan_id,
                "revision": 1,
                "state": "draft",
            },
            "scene_count": scene_count,
            **_cinematic_ad_plan_save_boundary(),
        }
        return envelope(
            True,
            str(response.get("message") or "Đã lưu Cinematic Ad Concept thành Video Plan riêng tư."),
            data=data,
            status_name="draft",
        )
    if source.get("_video_prompt_planner_plan_save") is True:
        plan = source.get("plan") if isinstance(source.get("plan"), dict) else {}
        plan_id = str(plan.get("id") or "")
        if not plan_id:
            raise HTTPException(status_code=500, detail="Receipt lưu video prompt plan không hợp lệ")
        try:
            normalized_plan_id = str(uuid.UUID(plan_id))
        except (ValueError, TypeError, AttributeError) as exc:
            raise HTTPException(status_code=500, detail="Receipt lưu video prompt plan không hợp lệ") from exc
        scene_count = source.get("scene_count")
        if isinstance(scene_count, bool) or not isinstance(scene_count, int) or not 1 <= scene_count <= MAX_SCENES_PER_PLAN:
            raise HTTPException(status_code=500, detail="Receipt lưu video prompt plan không hợp lệ")
        data = {
            "destination": "video_plan",
            "plan": {
                "id": normalized_plan_id,
                "revision": 1,
                "state": "draft",
            },
            "scene_count": scene_count,
            **_video_prompt_planner_plan_save_boundary(),
        }
        return envelope(
            True,
            str(response.get("message") or "Đã lưu Video Prompt Plan riêng tư."),
            data=data,
            status_name="draft",
        )
    if source.get("_storyboard_composer_plan_save") is True:
        plan = source.get("plan") if isinstance(source.get("plan"), dict) else {}
        plan_id = str(plan.get("id") or "")
        if not plan_id:
            raise HTTPException(status_code=500, detail="Receipt lưu storyboard plan không hợp lệ")
        try:
            normalized_plan_id = str(uuid.UUID(plan_id))
        except (ValueError, TypeError, AttributeError) as exc:
            raise HTTPException(status_code=500, detail="Receipt lưu storyboard plan không hợp lệ") from exc
        scene_count = source.get("scene_count")
        if isinstance(scene_count, bool) or not isinstance(scene_count, int) or not 1 <= scene_count <= MAX_SCENES_PER_PLAN:
            raise HTTPException(status_code=500, detail="Receipt lưu storyboard plan không hợp lệ")
        data = {
            "destination": "video_plan",
            "plan": {
                "id": normalized_plan_id,
                "revision": 1,
                "state": "draft",
            },
            "scene_count": scene_count,
            **_storyboard_composer_plan_save_boundary(),
        }
        return envelope(
            True,
            str(response.get("message") or "Đã lưu storyboard thành Video Plan riêng tư."),
            data=data,
            status_name="draft",
        )
    if source.get("_video_idea_planner_plan_save") is True:
        plan = source.get("plan") if isinstance(source.get("plan"), dict) else {}
        plan_id = str(plan.get("id") or "")
        if not plan_id:
            raise HTTPException(status_code=500, detail="Receipt lưu Video Idea plan không hợp lệ")
        try:
            normalized_plan_id = str(uuid.UUID(plan_id))
        except (ValueError, TypeError, AttributeError) as exc:
            raise HTTPException(status_code=500, detail="Receipt lưu Video Idea plan không hợp lệ") from exc
        scene_count = source.get("scene_count")
        if isinstance(scene_count, bool) or not isinstance(scene_count, int) or scene_count != 6:
            raise HTTPException(status_code=500, detail="Receipt lưu Video Idea plan không hợp lệ")
        return envelope(
            True,
            str(response.get("message") or "Đã lưu Video Idea thành Video Plan riêng tư."),
            data={
                "destination": "video_plan",
                "plan": {"id": normalized_plan_id, "revision": 1, "state": "draft"},
                "scene_count": scene_count,
                **_video_idea_plan_save_boundary(),
            },
            status_name="draft",
        )
    if source.get("_long_form_roadmap_plan_save") is True:
        plan = source.get("plan") if isinstance(source.get("plan"), dict) else {}
        plan_id = str(plan.get("id") or "")
        if not plan_id:
            raise HTTPException(status_code=500, detail="Receipt lưu long-form roadmap không hợp lệ")
        try:
            normalized_plan_id = str(uuid.UUID(plan_id))
        except (ValueError, TypeError, AttributeError) as exc:
            raise HTTPException(status_code=500, detail="Receipt lưu long-form roadmap không hợp lệ") from exc
        scene_count = source.get("scene_count")
        if isinstance(scene_count, bool) or not isinstance(scene_count, int) or not 3 <= scene_count <= 30:
            raise HTTPException(status_code=500, detail="Receipt lưu long-form roadmap không hợp lệ")
        return envelope(
            True,
            str(response.get("message") or "Đã lưu Long-form Roadmap thành Video Plan riêng tư."),
            data={
                "destination": "video_plan",
                "plan": {"id": normalized_plan_id, "revision": 1, "state": "draft"},
                "scene_count": scene_count,
                **_long_form_roadmap_plan_save_boundary(),
            },
            status_name="draft",
        )
    if source.get("_self_shot_scene_planner_plan_save") is True:
        plan = source.get("plan") if isinstance(source.get("plan"), dict) else {}
        plan_id = str(plan.get("id") or "")
        if not plan_id:
            raise HTTPException(status_code=500, detail="Receipt lưu Self-shot Scene plan không hợp lệ")
        try:
            normalized_plan_id = str(uuid.UUID(plan_id))
        except (ValueError, TypeError, AttributeError) as exc:
            raise HTTPException(status_code=500, detail="Receipt lưu Self-shot Scene plan không hợp lệ") from exc
        scene_count = source.get("scene_count")
        if isinstance(scene_count, bool) or not isinstance(scene_count, int) or scene_count != 1:
            raise HTTPException(status_code=500, detail="Receipt lưu Self-shot Scene plan không hợp lệ")
        return envelope(
            True,
            str(response.get("message") or "Đã lưu Self-shot Scene Direction thành Video Plan riêng tư."),
            data={
                "destination": "video_plan",
                "plan": {"id": normalized_plan_id, "revision": 1, "state": "draft"},
                "scene_count": scene_count,
                **_self_shot_scene_plan_save_boundary(),
            },
            status_name="draft",
        )
    if source.get("_script_to_screen_planner_plan_save") is True:
        plan = source.get("plan") if isinstance(source.get("plan"), dict) else {}
        plan_id = str(plan.get("id") or "")
        if not plan_id:
            raise HTTPException(status_code=500, detail="Receipt lưu Script-to-Screen plan không hợp lệ")
        try:
            normalized_plan_id = str(uuid.UUID(plan_id))
        except (ValueError, TypeError, AttributeError) as exc:
            raise HTTPException(status_code=500, detail="Receipt lưu Script-to-Screen plan không hợp lệ") from exc
        scene_count = source.get("scene_count")
        if isinstance(scene_count, bool) or not isinstance(scene_count, int) or not 3 <= scene_count <= 12:
            raise HTTPException(status_code=500, detail="Receipt lưu Script-to-Screen plan không hợp lệ")
        return envelope(
            True,
            str(response.get("message") or "Đã lưu Script-to-Screen Prompt Pack thành Video Plan riêng tư."),
            data={
                "destination": "video_plan",
                "plan": {"id": normalized_plan_id, "revision": 1, "state": "draft"},
                "scene_count": scene_count,
                **_script_to_screen_plan_save_boundary(),
            },
            status_name="draft",
        )
    data = _boundary()
    plan = source.get("plan")
    if isinstance(plan, dict) and isinstance(plan.get("id"), str):
        data["plan"] = {
            "id": str(plan["id"]),
            "revision": int(plan.get("revision") or 0),
            "state": str(plan.get("state") or ""),
        }
    scene = source.get("scene")
    if isinstance(scene, dict) and isinstance(scene.get("id"), str):
        data["scene"] = {
            "id": str(scene["id"]),
            "plan_id": str(scene.get("plan_id") or ""),
            "revision": int(scene.get("revision") or 0),
            "state": str(scene.get("state") or ""),
        }
    for field in ("history_snapshot_recorded", "scene_count", "reordered"):
        if field in source:
            data[field] = source[field]
    return envelope(
        True,
        str(response.get("message") or "Đã lưu Video Production Studio."),
        data=data,
        status_name=str(response.get("status") or "draft"),
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
            ("web-video-studio:%", _idempotency_cutoff()),
        )
        existing = conn.execute(
            "SELECT response_json, request_fingerprint FROM web_idempotency WHERE scope=? AND key=?",
            (scope, key),
        ).fetchone()
        if existing:
            fingerprint = str(existing[1] or "")
            if not fingerprint or not hmac.compare_digest(fingerprint, request_fingerprint):
                raise HTTPException(status_code=409, detail="Idempotency key đã được dùng cho yêu cầu khác")
            try:
                replay = json.loads(str(existing[0]))
            except (TypeError, ValueError, json.JSONDecodeError) as exc:
                raise HTTPException(status_code=409, detail="Receipt Video Studio không hợp lệ") from exc
            if not isinstance(replay, dict):
                raise HTTPException(status_code=409, detail="Receipt Video Studio không hợp lệ")
            return replay
        count = conn.execute(
            "SELECT COUNT(*) FROM web_idempotency WHERE scope LIKE ?",
            (f"web-video-studio:{account_id}:%",),
        ).fetchone()
        if int(count[0] or 0) >= MAX_IDEMPOTENCY_RECORDS_PER_ACCOUNT:
            return envelope(
                False,
                "Kho receipt thao tác tạm thời đang đầy. Vui lòng thử lại sau.",
                status_name="guarded",
                error_code="WEB_VIDEO_IDEMPOTENCY_LIMIT",
            )
        response = operation(conn)
        if response.get("ok") is True:
            receipt = _safe_receipt(response)
            conn.execute(
                "INSERT INTO web_idempotency (scope, key, response_json, request_fingerprint, created_at) VALUES (?, ?, ?, ?, ?)",
                (scope, key, json.dumps(receipt, ensure_ascii=False, separators=(",", ":")), request_fingerprint, utc_now()),
            )
            return receipt
    return response


def _plan_row(conn: Any, *, plan_id: str, account_id: str) -> tuple[Any, ...] | None:
    return conn.execute(
        """SELECT id, project_id, title, video_format, language, aspect_ratio, target_duration_seconds,
                  objective, audience, brief, tags_json, lifecycle, revision, created_at, updated_at, archived_at
           FROM web_video_plans WHERE id=? AND account_id=?""",
        (plan_id, account_id),
    ).fetchone()


def _scene_row(conn: Any, *, plan_id: str, scene_id: str, account_id: str) -> tuple[Any, ...] | None:
    return conn.execute(
        """SELECT id, plan_id, ordinal, title, scene_type, duration_seconds, visual_direction, narration,
                  on_screen_text, shot_notes, transition, tags_json, state, revision, created_at, updated_at, archived_at
           FROM web_video_scenes WHERE id=? AND plan_id=? AND account_id=?""",
        (scene_id, plan_id, account_id),
    ).fetchone()


def _plan_not_found() -> dict[str, Any]:
    return envelope(False, "Không tìm thấy video plan thuộc Web account hiện tại.", status_name="guarded", error_code="WEB_VIDEO_PLAN_NOT_FOUND")


def _scene_not_found() -> dict[str, Any]:
    return envelope(False, "Không tìm thấy scene thuộc video plan hiện tại.", status_name="guarded", error_code="WEB_VIDEO_SCENE_NOT_FOUND")


def _revision_conflict() -> dict[str, Any]:
    return envelope(False, "Dữ liệu đã thay đổi ở nơi khác. Hãy tải lại trước khi lưu tiếp.", status_name="guarded", error_code="WEB_VIDEO_REVISION_CONFLICT")


def _plan_archived() -> dict[str, Any]:
    return envelope(False, "Video plan đã archive; hãy khôi phục về Draft trước khi tiếp tục.", status_name="guarded", error_code="WEB_VIDEO_PLAN_ARCHIVED")


def _plan_approved() -> dict[str, Any]:
    return envelope(False, "Video plan đã self-review. Hãy chuyển về Draft trước khi chỉnh sửa plan hoặc scene.", status_name="guarded", error_code="WEB_VIDEO_PLAN_APPROVED")


def _scene_archived() -> dict[str, Any]:
    return envelope(False, "Scene đã archive và không thể chỉnh sửa trước khi khôi phục.", status_name="guarded", error_code="WEB_VIDEO_SCENE_ARCHIVED")


def _plan_writable(plan: tuple[Any, ...]) -> dict[str, Any] | None:
    lifecycle = str(plan[11])
    if lifecycle == "archived":
        return _plan_archived()
    if lifecycle == "approved":
        return _plan_approved()
    if lifecycle not in WRITABLE_PLAN_STATES:
        return envelope(False, "Trạng thái video plan không cho phép authoring.", status_name="guarded", error_code="WEB_VIDEO_PLAN_GUARDED")
    return None


def _project_reference(conn: Any, *, account_id: str, project_id: str | None, active: bool = True) -> dict[str, Any]:
    if not project_id:
        return {}
    state_clause = "AND state='active'" if active else ""
    row = conn.execute(
        f"SELECT id, title, state FROM web_projects WHERE id=? AND account_id=? {state_clause}",
        (project_id, account_id),
    ).fetchone()
    if not row:
        raise HTTPException(status_code=422, detail="Project liên kết không hợp lệ hoặc không còn hoạt động")
    return {"project": {"id": str(row[0]), "title": str(row[1]), "state": str(row[2])}}


def _plan_snapshot(payload: PlanPayload, *, lifecycle: str = "draft") -> dict[str, Any]:
    return {
        "title": payload.title,
        "format": payload.format,
        "language": payload.language,
        "aspect_ratio": payload.aspect_ratio,
        "target_duration_seconds": int(payload.target_duration_seconds),
        "objective": payload.objective,
        "audience": payload.audience,
        "brief": payload.brief,
        "tags": list(payload.tags),
        "project_id": payload.project_id,
        "lifecycle": lifecycle,
    }


def _plan_snapshot_from_row(row: tuple[Any, ...], *, lifecycle: str | None = None) -> dict[str, Any]:
    return {
        "title": str(row[2]),
        "format": str(row[3]),
        "language": str(row[4]),
        "aspect_ratio": str(row[5]),
        "target_duration_seconds": int(row[6]),
        "objective": str(row[7]),
        "audience": str(row[8]),
        "brief": str(row[9]),
        "tags": _decode_tags(row[10]),
        "project_id": str(row[1]) if row[1] else None,
        "lifecycle": lifecycle or str(row[11]),
    }


def _plan_payload_from_snapshot(snapshot: dict[str, Any]) -> PlanPayload:
    return PlanPayload.model_validate(
        {
            "title": snapshot.get("title", ""),
            "format": snapshot.get("format", "short_form"),
            "language": snapshot.get("language", "vi"),
            "aspect_ratio": snapshot.get("aspect_ratio", "9:16"),
            "target_duration_seconds": snapshot.get("target_duration_seconds", 30),
            "objective": snapshot.get("objective", ""),
            "audience": snapshot.get("audience", ""),
            "brief": snapshot.get("brief", ""),
            "tags": snapshot.get("tags", []),
            "project_id": snapshot.get("project_id"),
        }
    )


def _scene_snapshot(payload: ScenePayload, *, state: str = "active") -> dict[str, Any]:
    return {
        "title": payload.title,
        "scene_type": payload.scene_type,
        "duration_seconds": int(payload.duration_seconds),
        "visual_direction": payload.visual_direction,
        "narration": payload.narration,
        "on_screen_text": payload.on_screen_text,
        "shot_notes": payload.shot_notes,
        "transition": payload.transition,
        "tags": list(payload.tags),
        "state": state,
    }


def _scene_snapshot_from_row(row: tuple[Any, ...], *, state: str | None = None) -> dict[str, Any]:
    return {
        "title": str(row[3]),
        "scene_type": str(row[4]),
        "duration_seconds": int(row[5]),
        "visual_direction": str(row[6]),
        "narration": str(row[7]),
        "on_screen_text": str(row[8]),
        "shot_notes": str(row[9]),
        "transition": str(row[10]),
        "tags": _decode_tags(row[11]),
        "state": state or str(row[12]),
    }


def _scene_payload_from_snapshot(snapshot: dict[str, Any]) -> ScenePayload:
    return ScenePayload.model_validate(
        {
            "title": snapshot.get("title", ""),
            "scene_type": snapshot.get("scene_type", "custom"),
            "duration_seconds": snapshot.get("duration_seconds", 5),
            "visual_direction": snapshot.get("visual_direction", ""),
            "narration": snapshot.get("narration", ""),
            "on_screen_text": snapshot.get("on_screen_text", ""),
            "shot_notes": snapshot.get("shot_notes", ""),
            "transition": snapshot.get("transition", ""),
            "tags": snapshot.get("tags", []),
        }
    )


def _plan_public(row: tuple[Any, ...], *, scene_count: int = 0, include_content: bool = False) -> dict[str, Any]:
    value = {
        "id": str(row[0]),
        "project_id": str(row[1]) if row[1] else None,
        "title": str(row[2]),
        "format": str(row[3]),
        "language": str(row[4]),
        "aspect_ratio": str(row[5]),
        "target_duration_seconds": int(row[6]),
        "objective": str(row[7]),
        "audience_excerpt": _excerpt(row[8], 180),
        "brief_excerpt": _excerpt(row[9], 360),
        "tags": _decode_tags(row[10]),
        "state": str(row[11]),
        "revision": int(row[12]),
        "created_at": str(row[13]),
        "updated_at": str(row[14]),
        "archived_at": str(row[15]) if row[15] else None,
        "scene_count": int(scene_count),
        **_boundary(),
    }
    if include_content:
        value.update({"audience": str(row[8]), "brief": str(row[9])})
    return value


def _scene_public(row: tuple[Any, ...], *, include_content: bool = False, versions: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    value = {
        "id": str(row[0]),
        "plan_id": str(row[1]),
        "ordinal": int(row[2]),
        "title": str(row[3]),
        "scene_type": str(row[4]),
        "duration_seconds": int(row[5]),
        "visual_excerpt": _excerpt(row[6], 260),
        "narration_excerpt": _excerpt(row[7], 260),
        "on_screen_text_excerpt": _excerpt(row[8], 200),
        "shot_notes_excerpt": _excerpt(row[9], 260),
        "transition": str(row[10]),
        "tags": _decode_tags(row[11]),
        "state": str(row[12]),
        "revision": int(row[13]),
        "created_at": str(row[14]),
        "updated_at": str(row[15]),
        "archived_at": str(row[16]) if row[16] else None,
        **_boundary(),
    }
    if include_content:
        value.update(
            {
                "visual_direction": str(row[6]),
                "narration": str(row[7]),
                "on_screen_text": str(row[8]),
                "shot_notes": str(row[9]),
            }
        )
    if versions is not None:
        value["versions"] = versions
    return value


def _plan_version_public(row: tuple[Any, ...]) -> dict[str, Any]:
    try:
        snapshot = json.loads(str(row[1] or "{}"))
    except (TypeError, ValueError, json.JSONDecodeError):
        snapshot = {}
    snapshot = snapshot if isinstance(snapshot, dict) else {}
    return {
        "revision": int(row[0]),
        "title": str(snapshot.get("title") or "Video plan"),
        "format": str(snapshot.get("format") or "short_form"),
        "state": str(snapshot.get("lifecycle") or "draft"),
        "brief_excerpt": _excerpt(snapshot.get("brief"), 280),
        "created_at": str(row[2]),
    }


def _scene_version_public(row: tuple[Any, ...]) -> dict[str, Any]:
    try:
        snapshot = json.loads(str(row[1] or "{}"))
    except (TypeError, ValueError, json.JSONDecodeError):
        snapshot = {}
    snapshot = snapshot if isinstance(snapshot, dict) else {}
    return {
        "revision": int(row[0]),
        "title": str(snapshot.get("title") or "Scene"),
        "scene_type": str(snapshot.get("scene_type") or "custom"),
        "state": str(snapshot.get("state") or "active"),
        "visual_excerpt": _excerpt(snapshot.get("visual_direction"), 220),
        "created_at": str(row[2]),
    }


def _insert_plan(conn: Any, *, plan_id: str, account_id: str, snapshot: dict[str, Any], revision: int, now: str) -> None:
    conn.execute(
        """INSERT INTO web_video_plans
           (id, account_id, project_id, title, video_format, language, aspect_ratio, target_duration_seconds,
            objective, audience, brief, tags_json, lifecycle, revision, created_at, updated_at, archived_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            plan_id, account_id, snapshot.get("project_id"), snapshot["title"], snapshot["format"], snapshot["language"],
            snapshot["aspect_ratio"], snapshot["target_duration_seconds"], snapshot["objective"], snapshot["audience"],
            snapshot["brief"], json.dumps(snapshot["tags"], ensure_ascii=False, separators=(",", ":")),
            snapshot["lifecycle"], revision, now, now, now if snapshot["lifecycle"] == "archived" else None,
        ),
    )


def _write_plan(conn: Any, *, plan_id: str, account_id: str, snapshot: dict[str, Any], revision: int, now: str, archived_at: str | None) -> None:
    conn.execute(
        """UPDATE web_video_plans
           SET project_id=?, title=?, video_format=?, language=?, aspect_ratio=?, target_duration_seconds=?,
               objective=?, audience=?, brief=?, tags_json=?, lifecycle=?, revision=?, updated_at=?, archived_at=?
           WHERE id=? AND account_id=?""",
        (
            snapshot.get("project_id"), snapshot["title"], snapshot["format"], snapshot["language"],
            snapshot["aspect_ratio"], snapshot["target_duration_seconds"], snapshot["objective"], snapshot["audience"],
            snapshot["brief"], json.dumps(snapshot["tags"], ensure_ascii=False, separators=(",", ":")),
            snapshot["lifecycle"], revision, now, archived_at, plan_id, account_id,
        ),
    )


def _insert_plan_version(conn: Any, *, plan_id: str, account_id: str, revision: int, snapshot: dict[str, Any], now: str) -> None:
    conn.execute(
        "INSERT INTO web_video_plan_versions (id, plan_id, account_id, revision, snapshot_json, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (str(uuid.uuid4()), plan_id, account_id, revision, json.dumps(snapshot, ensure_ascii=False, separators=(",", ":")), now),
    )


def _insert_scene(conn: Any, *, scene_id: str, plan_id: str, account_id: str, ordinal: int, snapshot: dict[str, Any], revision: int, now: str) -> None:
    conn.execute(
        """INSERT INTO web_video_scenes
           (id, plan_id, account_id, ordinal, title, scene_type, duration_seconds, visual_direction, narration,
            on_screen_text, shot_notes, transition, tags_json, state, revision, created_at, updated_at, archived_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            scene_id, plan_id, account_id, ordinal, snapshot["title"], snapshot["scene_type"],
            snapshot["duration_seconds"], snapshot["visual_direction"], snapshot["narration"],
            snapshot["on_screen_text"], snapshot["shot_notes"], snapshot["transition"],
            json.dumps(snapshot["tags"], ensure_ascii=False, separators=(",", ":")), snapshot["state"],
            revision, now, now, now if snapshot["state"] == "archived" else None,
        ),
    )


def _write_scene(conn: Any, *, scene_id: str, plan_id: str, account_id: str, snapshot: dict[str, Any], revision: int, now: str, archived_at: str | None) -> None:
    conn.execute(
        """UPDATE web_video_scenes
           SET title=?, scene_type=?, duration_seconds=?, visual_direction=?, narration=?, on_screen_text=?,
               shot_notes=?, transition=?, tags_json=?, state=?, revision=?, updated_at=?, archived_at=?
           WHERE id=? AND plan_id=? AND account_id=?""",
        (
            snapshot["title"], snapshot["scene_type"], snapshot["duration_seconds"], snapshot["visual_direction"],
            snapshot["narration"], snapshot["on_screen_text"], snapshot["shot_notes"], snapshot["transition"],
            json.dumps(snapshot["tags"], ensure_ascii=False, separators=(",", ":")), snapshot["state"],
            revision, now, archived_at, scene_id, plan_id, account_id,
        ),
    )


def _insert_scene_version(conn: Any, *, scene_id: str, account_id: str, revision: int, snapshot: dict[str, Any], now: str) -> None:
    conn.execute(
        "INSERT INTO web_video_scene_versions (id, scene_id, account_id, revision, snapshot_json, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (str(uuid.uuid4()), scene_id, account_id, revision, json.dumps(snapshot, ensure_ascii=False, separators=(",", ":")), now),
    )


def _can_add_version(conn: Any, *, table: str, entity_column: str, entity_id: str, account_id: str) -> bool:
    row = conn.execute(
        f"SELECT COUNT(*) FROM {table} WHERE {entity_column}=? AND account_id=?",
        (entity_id, account_id),
    ).fetchone()
    return int(row[0] or 0) < MAX_VERSIONS_PER_ENTITY


def _next_active_ordinal(conn: Any, *, plan_id: str, account_id: str) -> int:
    row = conn.execute(
        "SELECT COALESCE(MAX(ordinal), 0) FROM web_video_scenes WHERE plan_id=? AND account_id=? AND state='active'",
        (plan_id, account_id),
    ).fetchone()
    return int(row[0] or 0) + 1


def _next_archived_ordinal(conn: Any, *, plan_id: str, account_id: str) -> int:
    row = conn.execute(
        "SELECT COALESCE(MAX(ordinal), 0) FROM web_video_scenes WHERE plan_id=? AND account_id=? AND state='archived'",
        (plan_id, account_id),
    ).fetchone()
    return max(ARCHIVED_ORDINAL_BASE, int(row[0] or 0) + 1)


def _normalise_archived_ordinals(conn: Any, *, plan_id: str, account_id: str) -> None:
    """Put every archived scene into the non-active ordinal range.

    This also safely repairs any legacy archived row whose ordinal predates
    the range policy.  The negative temporary pass prevents a unique-index
    collision while two archived rows exchange their old positions.
    """

    rows = conn.execute(
        "SELECT id FROM web_video_scenes WHERE plan_id=? AND account_id=? AND state='archived' ORDER BY archived_at ASC, id ASC",
        (plan_id, account_id),
    ).fetchall()
    for index, row in enumerate(rows, start=1):
        conn.execute(
            "UPDATE web_video_scenes SET ordinal=? WHERE id=? AND plan_id=? AND account_id=?",
            (-index, str(row[0]), plan_id, account_id),
        )
    for index, row in enumerate(rows, start=1):
        conn.execute(
            "UPDATE web_video_scenes SET ordinal=? WHERE id=? AND plan_id=? AND account_id=?",
            (ARCHIVED_ORDINAL_BASE + index - 1, str(row[0]), plan_id, account_id),
        )


def _event(conn: Any, *, account_id: str, plan_id: str, action: str, revision: int, scene_id: str | None = None) -> None:
    conn.execute(
        """INSERT INTO web_video_studio_events
           (id, account_id, plan_id, scene_id, entity_type, action, revision, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (str(uuid.uuid4()), account_id, plan_id, scene_id, "scene" if scene_id else "plan", action, revision, utc_now()),
    )


def _audit(conn: Any, *, request: Request, account: dict, action: str, target: str, detail: str) -> None:
    _record_audit(
        conn,
        account_id=str(account["id"]),
        canonical_user_id=None,
        action=action,
        request_id=_request_id(request),
        target=target,
        detail=detail[:320],
    )


def _advance_plan_for_scene_change(conn: Any, *, plan: tuple[Any, ...], account_id: str, now: str, event: str, scene_id: str | None = None) -> tuple[Any, ...]:
    """Record a plan revision around a child change and reopen review if needed."""

    plan_id = str(plan[0])
    if not _can_add_version(conn, table="web_video_plan_versions", entity_column="plan_id", entity_id=plan_id, account_id=account_id):
        raise HTTPException(status_code=409, detail="Video plan đã đạt giới hạn lịch sử phiên bản")
    lifecycle = "draft" if str(plan[11]) == "review" else str(plan[11])
    snapshot = _plan_snapshot_from_row(plan, lifecycle=lifecycle)
    revision = int(plan[12]) + 1
    _write_plan(conn, plan_id=plan_id, account_id=account_id, snapshot=snapshot, revision=revision, now=now, archived_at=None)
    _insert_plan_version(conn, plan_id=plan_id, account_id=account_id, revision=revision, snapshot=snapshot, now=now)
    _event(conn, account_id=account_id, plan_id=plan_id, scene_id=scene_id, action=event, revision=revision)
    changed = _plan_row(conn, plan_id=plan_id, account_id=account_id)
    if not changed:
        raise HTTPException(status_code=500, detail="Không thể đọc lại video plan")
    return changed


def _summary_data(conn: Any, *, account_id: str) -> dict[str, Any]:
    counts = {
        str(row[0]): int(row[1])
        for row in conn.execute(
            "SELECT lifecycle, COUNT(*) FROM web_video_plans WHERE account_id=? GROUP BY lifecycle",
            (account_id,),
        ).fetchall()
    }
    scenes = conn.execute("SELECT COUNT(*) FROM web_video_scenes WHERE account_id=? AND state='active'", (account_id,)).fetchone()
    return {
        "plans": {
            "draft": counts.get("draft", 0),
            "review": counts.get("review", 0),
            "approved": counts.get("approved", 0),
            "archived": counts.get("archived", 0),
            "total": sum(counts.values()),
            "limit_per_account": MAX_PLANS_PER_ACCOUNT,
        },
        "scenes": {"active": int(scenes[0] or 0), "limit_per_plan": MAX_SCENES_PER_PLAN},
        **_boundary(),
    }


def _references_listing(conn: Any, *, account_id: str) -> dict[str, Any]:
    projects = conn.execute(
        "SELECT id, title, updated_at FROM web_projects WHERE account_id=? AND state='active' ORDER BY updated_at DESC, id DESC LIMIT 100",
        (account_id,),
    ).fetchall()
    return {
        "projects": [{"id": str(row[0]), "title": str(row[1]), "updated_at": str(row[2])} for row in projects],
        **_boundary(),
    }


def _scene_versions(conn: Any, *, scene_id: str, account_id: str) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT revision, snapshot_json, created_at FROM web_video_scene_versions WHERE scene_id=? AND account_id=? ORDER BY revision DESC LIMIT 20",
        (scene_id, account_id),
    ).fetchall()
    return [_scene_version_public(row) for row in rows]


def _plan_detail(conn: Any, *, plan_id: str, account_id: str) -> dict[str, Any] | None:
    plan = _plan_row(conn, plan_id=plan_id, account_id=account_id)
    if not plan:
        return None
    scene_count = conn.execute(
        "SELECT COUNT(*) FROM web_video_scenes WHERE plan_id=? AND account_id=? AND state='active'",
        (plan_id, account_id),
    ).fetchone()
    versions = conn.execute(
        "SELECT revision, snapshot_json, created_at FROM web_video_plan_versions WHERE plan_id=? AND account_id=? ORDER BY revision DESC LIMIT ?",
        (plan_id, account_id, MAX_VERSIONS_PER_ENTITY),
    ).fetchall()
    scenes = conn.execute(
        """SELECT id, plan_id, ordinal, title, scene_type, duration_seconds, visual_direction, narration,
                  on_screen_text, shot_notes, transition, tags_json, state, revision, created_at, updated_at, archived_at
           FROM web_video_scenes WHERE plan_id=? AND account_id=?
           ORDER BY CASE state WHEN 'active' THEN 0 ELSE 1 END, ordinal ASC, updated_at DESC, id DESC LIMIT ?""",
        (plan_id, account_id, MAX_SCENES_PER_PLAN),
    ).fetchall()
    events = conn.execute(
        "SELECT action, entity_type, scene_id, revision, created_at FROM web_video_studio_events WHERE plan_id=? AND account_id=? ORDER BY created_at DESC, id DESC LIMIT ?",
        (plan_id, account_id, MAX_EVENT_LIMIT),
    ).fetchall()
    references = _project_reference(conn, account_id=account_id, project_id=str(plan[1]) if plan[1] else None, active=False)
    return {
        "plan": _plan_public(plan, scene_count=int(scene_count[0] or 0), include_content=True),
        "versions": [_plan_version_public(row) for row in versions],
        "scenes": [
            _scene_public(row, include_content=True, versions=_scene_versions(conn, scene_id=str(row[0]), account_id=account_id))
            for row in scenes
        ],
        "events": [
            {
                "action": str(row[0]),
                "entity_type": str(row[1]),
                "scene_id": str(row[2]) if row[2] else None,
                "revision": int(row[3]),
                "created_at": str(row[4]),
            }
            for row in events
        ],
        "references": references,
        **_boundary(),
    }


def _estimate(conn: Any, *, plan: tuple[Any, ...], account_id: str) -> dict[str, Any]:
    if str(plan[11]) == "archived":
        return _plan_archived()
    scenes = conn.execute(
        "SELECT id, ordinal, title, scene_type, duration_seconds FROM web_video_scenes WHERE plan_id=? AND account_id=? AND state='active' ORDER BY ordinal ASC, id ASC",
        (str(plan[0]), account_id),
    ).fetchall()
    total = sum(max(0, int(row[4] or 0)) for row in scenes)
    target = int(plan[6])
    return envelope(
        True,
        "Đã tính runtime estimate cục bộ cho plan.",
        data={
            "plan_id": str(plan[0]),
            "target_duration_seconds": target,
            "scene_duration_seconds": total,
            "difference_seconds": total - target,
            "scene_count": len(scenes),
            "items": [
                {
                    "scene_id": str(row[0]),
                    "ordinal": int(row[1]),
                    "title": str(row[2]),
                    "scene_type": str(row[3]),
                    "duration_seconds": int(row[4]),
                }
                for row in scenes
            ],
            "notice": "Estimate chỉ dùng để review nhịp cảnh; không phải render, preview hoặc kết quả media.",
            **_boundary(),
        },
        status_name="completed",
    )


@router.post("/tools/prompt-planner")
async def create_video_prompt_plan(
    payload: VideoPromptPlannerRequest,
    account: dict = Depends(require_csrf),
):
    """Return a transient, deterministic video direction plan.

    ``require_csrf`` also verifies the signed Web session.  This endpoint must
    remain request/response-only: do not add an audit event, database write,
    idempotency receipt, source-media flow, asset save, engine/provider call,
    job, payment/wallet mutation, preview, output or publish action here.
    """

    _require_enabled()
    del account  # Auth/CSRF is the only account boundary for this stateless tool.
    marker = _planner_guard_marker(
        payload.brief,
        payload.motion,
        payload.background,
        *payload.must_keep,
        *payload.must_avoid,
    )
    guarded = _video_prompt_planner_guard(marker)
    if guarded:
        return guarded
    planner = _compose_video_prompt_plan(payload)
    return envelope(
        True,
        "Đã tạo video direction dạng văn bản để bạn biên tập. Không có video, preview, output, job, thanh toán hoặc publish nào được tạo.",
        data={"planner": planner, **_video_prompt_planner_boundary()},
        status_name="draft",
    )


@router.post("/tools/prompt-planner/save")
async def save_video_prompt_plan_to_video_plan(
    payload: VideoPromptPlannerPlanSaveRequest,
    request: Request,
    account: dict = Depends(require_csrf),
):
    """Create an editable Web-native draft from original Planner inputs.

    This is intentionally separate from ``/tools/prompt-planner``.  The
    browser sends only the bounded original text choices, a fixed destination
    and idempotency key.  The server rebuilds the full planner while its
    transaction is open, then creates private Web authoring metadata only.
    It does not reuse Bot state, call a bridge or external service, inspect
    media, create a job/asset/output, mutate wallet/payment, approve/lock a
    plan, start generation or deliver media.
    """

    _require_enabled()
    guarded = _video_prompt_planner_plan_save_guard(
        _planner_guard_marker(
            payload.brief,
            payload.motion,
            payload.background,
            *payload.must_keep,
            *payload.must_avoid,
        )
    )
    if guarded:
        return guarded

    account_id = str(account["id"])
    fingerprint = _fingerprint(
        {
            "operation": "video-prompt-planner-save-video-plan",
            **payload.model_dump(exclude={"idempotency_key"}),
        }
    )

    def operation(conn: Any) -> dict[str, Any]:
        # Do not accept a browser-generated result.  This recomputation keeps
        # the durable plan and scene mapping coupled to the safe local planner.
        planner = _compose_video_prompt_plan(payload)
        plan_payload, scene_payloads = _video_prompt_planner_to_video_plan(payload, planner)
        count = conn.execute(
            "SELECT COUNT(*) FROM web_video_plans WHERE account_id=? AND lifecycle<>'archived'",
            (account_id,),
        ).fetchone()
        if int(count[0] or 0) >= MAX_PLANS_PER_ACCOUNT:
            return envelope(
                False,
                "Video Production Studio đã đạt giới hạn plan đang hoạt động.",
                data={
                    "destination": "video_plan",
                    **_video_prompt_planner_plan_save_boundary(
                        draft_recomputed_on_server=True,
                        web_video_plan_persisted=False,
                    ),
                },
                status_name="guarded",
                error_code="WEB_VIDEO_PLAN_LIMIT",
            )
        if not 1 <= len(scene_payloads) <= MAX_SCENES_PER_PLAN:
            raise HTTPException(status_code=422, detail="Số scene video prompt không hợp lệ để lưu Video Plan")

        plan_id = str(uuid.uuid4())
        now = utc_now()
        plan_snapshot = _plan_snapshot(plan_payload, lifecycle="draft")
        _insert_plan(conn, plan_id=plan_id, account_id=account_id, snapshot=plan_snapshot, revision=1, now=now)
        _insert_plan_version(conn, plan_id=plan_id, account_id=account_id, revision=1, snapshot=plan_snapshot, now=now)
        _event(conn, account_id=account_id, plan_id=plan_id, action="plan_created", revision=1)

        for ordinal, scene_payload in enumerate(scene_payloads, start=1):
            scene_id = str(uuid.uuid4())
            scene_snapshot = _scene_snapshot(scene_payload, state="active")
            _insert_scene(
                conn,
                scene_id=scene_id,
                plan_id=plan_id,
                account_id=account_id,
                ordinal=ordinal,
                snapshot=scene_snapshot,
                revision=1,
                now=now,
            )
            _insert_scene_version(
                conn,
                scene_id=scene_id,
                account_id=account_id,
                revision=1,
                snapshot=scene_snapshot,
                now=now,
            )
            _event(conn, account_id=account_id, plan_id=plan_id, scene_id=scene_id, action="scene_created", revision=1)

        _audit(
            conn,
            request=request,
            account=account,
            action="web.video.prompt_planner.save_plan",
            target=plan_id,
            detail="server-recomputed video prompt planner saved as web-owned draft video plan",
        )
        return envelope(
            True,
            "Đã lưu Video Prompt Plan Draft riêng tư. Chưa có phê duyệt, lock, render, job, media, thanh toán hoặc giao hàng.",
            data={
                "_video_prompt_planner_plan_save": True,
                "plan": {"id": plan_id, "revision": 1, "state": "draft"},
                "scene_count": len(scene_payloads),
            },
            status_name="draft",
        )

    return _idempotent(
        f"web-video-studio:{account_id}:prompt-planner:save-plan",
        account_id,
        payload.idempotency_key,
        fingerprint,
        operation,
    )


@router.get("/tools/image-motion-planner/references")
async def image_motion_planner_references(account: dict = Depends(require_account)):
    """List only current-account Image Studio directions usable for planning.

    The response deliberately contains no asset ID, filename, storage key,
    URL, prompt text or media preview.  It is a signed metadata selector, not
    an upload/download or source-media endpoint.
    """

    _require_enabled()
    ensure_copyfast_schema()
    with read_transaction() as conn:
        references = _image_motion_list_references(conn, account_id=str(account["id"]))
    return envelope(
        True,
        "Đã nạp Image Studio directions có Image Vault reference đang hoạt động thuộc Web account hiện tại.",
        data={"references": references},
        status_name="completed",
    )


@router.post("/tools/image-motion-planner")
async def compose_image_motion_planner(
    payload: ImageMotionPlannerRequest,
    account: dict = Depends(require_csrf),
):
    """Build a transient motion plan from a private Image Studio reference.

    This endpoint checks account ownership and active image metadata but never
    opens the image or reads a storage key.  It creates no media, provider
    request, job, asset, payment or Bot state.
    """

    _require_enabled()
    ensure_copyfast_schema()
    account_id = str(account["id"])
    with read_transaction() as conn:
        reference = _image_motion_direction_reference(
            conn,
            direction_id=payload.direction_id,
            account_id=account_id,
        )
    guarded = _image_motion_guard(_image_motion_marker(reference))
    if guarded:
        return guarded
    planner = _compose_image_motion_planner(payload, reference)
    return envelope(
        True,
        "Đã tạo Image Motion Plan để review. Ảnh nguồn không được mở/đọc; không có video, preview, audio, provider, job, payment hoặc output nào được tạo.",
        data={"planner": planner, **_image_motion_boundary()},
        status_name="draft",
    )


@router.post("/tools/image-motion-planner/save")
async def save_image_motion_planner_to_video_plan(
    payload: ImageMotionPlannerPlanSaveRequest,
    request: Request,
    account: dict = Depends(require_csrf),
):
    """Persist a server-recomputed private Video Plan from original choices.

    The browser cannot submit source media, an asset URL, a rendered planner,
    scenes, lifecycle fields or any provider/Bot/payment data.  Ownership and
    active image metadata are checked again inside the write transaction.
    """

    _require_enabled()
    account_id = str(account["id"])
    fingerprint = _fingerprint(
        {
            "operation": "image-motion-planner-save-video-plan",
            **payload.model_dump(exclude={"idempotency_key"}),
        }
    )

    def operation(conn: Any) -> dict[str, Any]:
        reference = _image_motion_direction_reference(
            conn,
            direction_id=payload.direction_id,
            account_id=account_id,
        )
        guarded = _image_motion_guard(_image_motion_marker(reference), saving=True)
        if guarded:
            return guarded
        planner = _compose_image_motion_planner(payload, reference)
        plan_payload, scene_payloads = _image_motion_planner_to_video_plan(payload, planner)
        count = conn.execute(
            "SELECT COUNT(*) FROM web_video_plans WHERE account_id=? AND lifecycle<>'archived'",
            (account_id,),
        ).fetchone()
        if int(count[0] or 0) >= MAX_PLANS_PER_ACCOUNT:
            return envelope(
                False,
                "Video Production Studio đã đạt giới hạn plan đang hoạt động.",
                data={
                    "destination": "video_plan",
                    **_image_motion_plan_save_boundary(
                        draft_recomputed_on_server=True,
                        web_video_plan_persisted=False,
                    ),
                },
                status_name="guarded",
                error_code="WEB_VIDEO_PLAN_LIMIT",
            )
        if len(scene_payloads) != 3:
            raise HTTPException(status_code=422, detail="Image Motion Planner phải tạo đúng ba scene để lưu Video Plan")

        plan_id = str(uuid.uuid4())
        now = utc_now()
        plan_snapshot = _plan_snapshot(plan_payload, lifecycle="draft")
        _insert_plan(conn, plan_id=plan_id, account_id=account_id, snapshot=plan_snapshot, revision=1, now=now)
        _insert_plan_version(conn, plan_id=plan_id, account_id=account_id, revision=1, snapshot=plan_snapshot, now=now)
        _event(conn, account_id=account_id, plan_id=plan_id, action="plan_created", revision=1)

        for ordinal, scene_payload in enumerate(scene_payloads, start=1):
            scene_id = str(uuid.uuid4())
            scene_snapshot = _scene_snapshot(scene_payload, state="active")
            _insert_scene(
                conn,
                scene_id=scene_id,
                plan_id=plan_id,
                account_id=account_id,
                ordinal=ordinal,
                snapshot=scene_snapshot,
                revision=1,
                now=now,
            )
            _insert_scene_version(
                conn,
                scene_id=scene_id,
                account_id=account_id,
                revision=1,
                snapshot=scene_snapshot,
                now=now,
            )
            _event(conn, account_id=account_id, plan_id=plan_id, scene_id=scene_id, action="scene_created", revision=1)

        _audit(
            conn,
            request=request,
            account=account,
            action="web.video.image_motion_planner.save_plan",
            target=plan_id,
            detail="server-recomputed image motion planner saved as web-owned draft video plan",
        )
        return envelope(
            True,
            "Đã lưu Image Motion Plan thành Video Plan Draft riêng tư. Ảnh nguồn không được mở/đọc; chưa có render, job, media, thanh toán hoặc giao hàng.",
            data={
                "_image_motion_planner_plan_save": True,
                "plan": {"id": plan_id, "revision": 1, "state": "draft"},
                "scene_count": len(scene_payloads),
            },
            status_name="draft",
        )

    return _idempotent(
        f"web-video-studio:{account_id}:image-motion-planner:save-plan",
        account_id,
        payload.idempotency_key,
        fingerprint,
        operation,
    )


@router.get("/tools/reference-format-planner/references")
async def reference_format_planner_references(account: dict = Depends(require_account)):
    """List only active, owner-scoped Asset Vault video metadata.

    This is not an asset download, preview, upload, video decoder or external
    link fetch.  It intentionally excludes storage keys, original filenames,
    URLs, bytes, duration, frames and provider metadata.
    """

    _require_enabled()
    ensure_copyfast_schema()
    with read_transaction() as conn:
        references = _reference_format_list_references(conn, account_id=str(account["id"]))
    return envelope(
        True,
        "Đã nạp video Asset Vault đang hoạt động thuộc Web account hiện tại để chọn làm tham chiếu format riêng tư.",
        data={"references": references},
        status_name="completed",
    )


@router.post("/tools/reference-format-planner")
async def compose_reference_format_planner(
    payload: ReferenceFormatPlannerRequest,
    account: dict = Depends(require_csrf),
):
    """Make an original text plan without opening or analyzing a source video."""

    _require_enabled()
    ensure_copyfast_schema()
    account_id = str(account["id"])
    with read_transaction() as conn:
        reference = _reference_format_asset(conn, asset_id=payload.asset_id, account_id=account_id)
    guarded = _reference_format_guard(reference=reference, payload=payload)
    if guarded:
        return guarded
    planner = _compose_reference_format_planner(payload, reference)
    return envelope(
        True,
        "Đã tạo Reference Format Plan để review. Video nguồn không được mở hoặc phân tích; không có media, provider, Bot, job, Xu, thanh toán, publish hoặc output nào được tạo.",
        data={"planner": planner, **_reference_format_boundary()},
        status_name="draft",
    )


@router.post("/tools/reference-format-planner/save")
async def save_reference_format_planner_to_video_plan(
    payload: ReferenceFormatPlannerPlanSaveRequest,
    request: Request,
    account: dict = Depends(require_csrf),
):
    """Persist a server-recomputed private Video Plan, never browser scenes."""

    _require_enabled()
    account_id = str(account["id"])
    fingerprint = _fingerprint(
        {
            "operation": "reference-format-planner-save-video-plan",
            **payload.model_dump(exclude={"idempotency_key"}),
        }
    )

    def operation(conn: Any) -> dict[str, Any]:
        reference = _reference_format_asset(conn, asset_id=payload.asset_id, account_id=account_id)
        guarded = _reference_format_guard(reference=reference, payload=payload, saving=True)
        if guarded:
            return guarded
        planner = _compose_reference_format_planner(payload, reference)
        plan_payload, scene_payloads = _reference_format_planner_to_video_plan(payload, planner)
        count = conn.execute(
            "SELECT COUNT(*) FROM web_video_plans WHERE account_id=? AND lifecycle<>'archived'",
            (account_id,),
        ).fetchone()
        if int(count[0] or 0) >= MAX_PLANS_PER_ACCOUNT:
            return envelope(
                False,
                "Video Production Studio đã đạt giới hạn plan đang hoạt động.",
                data={
                    "destination": "video_plan",
                    **_reference_format_plan_save_boundary(
                        draft_recomputed_on_server=True,
                        web_video_plan_persisted=False,
                    ),
                },
                status_name="guarded",
                error_code="WEB_VIDEO_PLAN_LIMIT",
            )
        if len(scene_payloads) != 3:
            raise HTTPException(status_code=422, detail="Reference Format Planner phải tạo đúng ba scene để lưu Video Plan")

        plan_id = str(uuid.uuid4())
        now = utc_now()
        plan_snapshot = _plan_snapshot(plan_payload, lifecycle="draft")
        _insert_plan(conn, plan_id=plan_id, account_id=account_id, snapshot=plan_snapshot, revision=1, now=now)
        _insert_plan_version(conn, plan_id=plan_id, account_id=account_id, revision=1, snapshot=plan_snapshot, now=now)
        _event(conn, account_id=account_id, plan_id=plan_id, action="plan_created", revision=1)

        for ordinal, scene_payload in enumerate(scene_payloads, start=1):
            scene_id = str(uuid.uuid4())
            scene_snapshot = _scene_snapshot(scene_payload, state="active")
            _insert_scene(
                conn,
                scene_id=scene_id,
                plan_id=plan_id,
                account_id=account_id,
                ordinal=ordinal,
                snapshot=scene_snapshot,
                revision=1,
                now=now,
            )
            _insert_scene_version(
                conn,
                scene_id=scene_id,
                account_id=account_id,
                revision=1,
                snapshot=scene_snapshot,
                now=now,
            )
            _event(conn, account_id=account_id, plan_id=plan_id, scene_id=scene_id, action="scene_created", revision=1)

        _audit(
            conn,
            request=request,
            account=account,
            action="web.video.reference_format_planner.save_plan",
            target=plan_id,
            detail="server-recomputed reference format planner saved as web-owned draft video plan",
        )
        return envelope(
            True,
            "Đã lưu Reference Format Plan thành Video Plan Draft riêng tư. Video nguồn không được mở/phân tích; chưa có render, job, media, thanh toán hoặc giao hàng.",
            data={
                "_reference_format_planner_plan_save": True,
                "plan": {"id": plan_id, "revision": 1, "state": "draft"},
                "scene_count": len(scene_payloads),
            },
            status_name="draft",
        )

    return _idempotent(
        f"web-video-studio:{account_id}:reference-format-planner:save-plan",
        account_id,
        payload.idempotency_key,
        fingerprint,
        operation,
    )


@router.post("/tools/cinematic-concept")
async def compose_cinematic_ad_concept(
    payload: CinematicAdConceptRequest,
    account: dict = Depends(require_csrf),
):
    """Return a transient, deterministic advertising concept draft.

    ``require_csrf`` verifies the signed Web session.  This endpoint is
    intentionally request/response-only: it must not persist a concept, emit
    an audit event, touch an idempotency store, accept media/files, call a
    provider/bridge, create an image/video/audio/preview/output/job, mutate
    wallet/payment state, save an asset or create a publish action.
    """

    _require_enabled()
    del account  # Auth/CSRF is the only account boundary for this stateless tool.
    guarded = _cinematic_ad_guard(_cinematic_ad_marker(payload.product, payload.message))
    if guarded:
        return guarded
    composer = _compose_cinematic_ad_concept(payload)
    return envelope(
        True,
        "Đã tạo concept quảng cáo dạng văn bản để bạn biên tập. Không có ảnh, video, audio, preview, output, job, thanh toán hoặc publish nào được tạo.",
        data={"composer": composer, **_cinematic_ad_boundary()},
        status_name="draft",
    )


@router.post("/tools/cinematic-concept/save")
async def save_cinematic_ad_concept_to_video_plan(
    payload: CinematicAdConceptPlanSaveRequest,
    request: Request,
    account: dict = Depends(require_csrf),
):
    """Create an editable Web-native draft from original Concept choices.

    This is a second, explicit action after the transient composition.  The
    browser sends only bounded input choices, an explicit destination and an
    idempotency key.  No generated prompt/storyboard, Bot pending state,
    source media, provider handle or lifecycle override can enter this write.
    """

    _require_enabled()
    guarded = _cinematic_ad_plan_save_guard(
        _cinematic_ad_marker(payload.product, payload.message)
    )
    if guarded:
        return guarded

    account_id = str(account["id"])
    fingerprint = _fingerprint(
        {
            "operation": "cinematic-concept-save-video-plan",
            **payload.model_dump(exclude={"idempotency_key"}),
        }
    )

    def operation(conn: Any) -> dict[str, Any]:
        # Rebuild all durable content from server-side template logic.  The
        # rendered composition is never a persistence input.
        composer = _compose_cinematic_ad_concept(payload)
        plan_payload, scene_payloads = _cinematic_ad_concept_to_video_plan(payload, composer)
        count = conn.execute(
            "SELECT COUNT(*) FROM web_video_plans WHERE account_id=? AND lifecycle<>'archived'",
            (account_id,),
        ).fetchone()
        if int(count[0] or 0) >= MAX_PLANS_PER_ACCOUNT:
            return envelope(
                False,
                "Video Production Studio đã đạt giới hạn plan đang hoạt động.",
                data={
                    "destination": "video_plan",
                    **_cinematic_ad_plan_save_boundary(
                        draft_recomputed_on_server=True,
                        web_video_plan_persisted=False,
                    ),
                },
                status_name="guarded",
                error_code="WEB_VIDEO_PLAN_LIMIT",
            )
        if not 1 <= len(scene_payloads) <= MAX_SCENES_PER_PLAN:
            raise HTTPException(status_code=422, detail="Số scene cinematic concept không hợp lệ để lưu Video Plan")

        plan_id = str(uuid.uuid4())
        now = utc_now()
        plan_snapshot = _plan_snapshot(plan_payload, lifecycle="draft")
        _insert_plan(conn, plan_id=plan_id, account_id=account_id, snapshot=plan_snapshot, revision=1, now=now)
        _insert_plan_version(conn, plan_id=plan_id, account_id=account_id, revision=1, snapshot=plan_snapshot, now=now)
        _event(conn, account_id=account_id, plan_id=plan_id, action="plan_created", revision=1)

        for ordinal, scene_payload in enumerate(scene_payloads, start=1):
            scene_id = str(uuid.uuid4())
            scene_snapshot = _scene_snapshot(scene_payload, state="active")
            _insert_scene(
                conn,
                scene_id=scene_id,
                plan_id=plan_id,
                account_id=account_id,
                ordinal=ordinal,
                snapshot=scene_snapshot,
                revision=1,
                now=now,
            )
            _insert_scene_version(
                conn,
                scene_id=scene_id,
                account_id=account_id,
                revision=1,
                snapshot=scene_snapshot,
                now=now,
            )
            _event(conn, account_id=account_id, plan_id=plan_id, scene_id=scene_id, action="scene_created", revision=1)

        _audit(
            conn,
            request=request,
            account=account,
            action="web.video.cinematic_concept.save_plan",
            target=plan_id,
            detail="server-recomputed cinematic ad concept saved as web-owned draft video plan",
        )
        return envelope(
            True,
            "Đã lưu Cinematic Ad Concept thành Video Plan Draft riêng tư. Chưa có phê duyệt, lock, render, job, media, thanh toán hoặc giao hàng.",
            data={
                "_cinematic_ad_concept_plan_save": True,
                "plan": {"id": plan_id, "revision": 1, "state": "draft"},
                "scene_count": len(scene_payloads),
            },
            status_name="draft",
        )

    return _idempotent(
        f"web-video-studio:{account_id}:cinematic-concept:save-plan",
        account_id,
        payload.idempotency_key,
        fingerprint,
        operation,
    )


@router.post("/tools/storyboard-composer")
async def compose_storyboard_prompt_pack(
    payload: StoryboardComposerRequest,
    account: dict = Depends(require_csrf),
):
    """Return a transient, deterministic storyboard prompt pack.

    ``require_csrf`` verifies the signed Web session.  This endpoint is
    request/response-only: it must not persist a pack, emit an audit event,
    accept media/files, touch any external service, create image/video/audio,
    preview/output/job, mutate wallet/payment state, save an asset or create a
    publish action.
    """

    _require_enabled()
    del account  # Auth/CSRF is the only account boundary for this stateless tool.
    guarded = _storyboard_composer_guard(_storyboard_composer_marker(payload.topic, payload.brief))
    if guarded:
        return guarded
    composer = _compose_storyboard_composer(payload)
    return envelope(
        True,
        "Đã tạo storyboard và prompt pack dạng văn bản để bạn biên tập. Không có ảnh, video, audio, preview, output, job, thanh toán hoặc publish nào được tạo.",
        data={"composer": composer, **_storyboard_composer_boundary()},
        status_name="draft",
    )


@router.post("/tools/storyboard-composer/save")
async def save_storyboard_composer_to_video_plan(
    payload: StoryboardComposerPlanSaveRequest,
    request: Request,
    account: dict = Depends(require_csrf),
):
    """Create an editable Web-native draft plan from original Composer inputs.

    This is deliberately separate from ``/tools/storyboard-composer``.  The
    browser supplies only the original bounded choices, destination and an
    idempotency key; the full pack is recomputed within the write transaction.
    It neither reads or writes Bot state nor calls a bridge/provider, creates
    a job/media/asset, touches wallet/payment, approves/locks the plan or
    starts generation/delivery.
    """

    _require_enabled()
    guarded = _storyboard_composer_plan_save_guard(
        _storyboard_composer_marker(payload.topic, payload.brief)
    )
    if guarded:
        return guarded

    account_id = str(account["id"])
    fingerprint = _fingerprint(
        {
            "operation": "storyboard-composer-save-video-plan",
            **payload.model_dump(exclude={"idempotency_key"}),
        }
    )

    def operation(conn: Any) -> dict[str, Any]:
        # Rebuild all durable fields on the server.  No browser-rendered pack
        # or client-authored scene array is accepted as input to this write.
        composer = _compose_storyboard_composer(payload)
        plan_payload, scene_payloads = _storyboard_composer_to_video_plan(payload, composer)
        count = conn.execute(
            "SELECT COUNT(*) FROM web_video_plans WHERE account_id=? AND lifecycle<>'archived'",
            (account_id,),
        ).fetchone()
        if int(count[0] or 0) >= MAX_PLANS_PER_ACCOUNT:
            return envelope(
                False,
                "Video Production Studio đã đạt giới hạn plan đang hoạt động.",
                data={
                    "destination": "video_plan",
                    **_storyboard_composer_plan_save_boundary(
                        draft_recomputed_on_server=True,
                        web_video_plan_persisted=False,
                    ),
                },
                status_name="guarded",
                error_code="WEB_VIDEO_PLAN_LIMIT",
            )
        if not 1 <= len(scene_payloads) <= MAX_SCENES_PER_PLAN:
            raise HTTPException(status_code=422, detail="Số scene storyboard không hợp lệ để lưu Video Plan")

        plan_id = str(uuid.uuid4())
        now = utc_now()
        plan_snapshot = _plan_snapshot(plan_payload, lifecycle="draft")
        _insert_plan(conn, plan_id=plan_id, account_id=account_id, snapshot=plan_snapshot, revision=1, now=now)
        _insert_plan_version(conn, plan_id=plan_id, account_id=account_id, revision=1, snapshot=plan_snapshot, now=now)
        _event(conn, account_id=account_id, plan_id=plan_id, action="plan_created", revision=1)

        for ordinal, scene_payload in enumerate(scene_payloads, start=1):
            scene_id = str(uuid.uuid4())
            scene_snapshot = _scene_snapshot(scene_payload, state="active")
            _insert_scene(
                conn,
                scene_id=scene_id,
                plan_id=plan_id,
                account_id=account_id,
                ordinal=ordinal,
                snapshot=scene_snapshot,
                revision=1,
                now=now,
            )
            _insert_scene_version(
                conn,
                scene_id=scene_id,
                account_id=account_id,
                revision=1,
                snapshot=scene_snapshot,
                now=now,
            )
            _event(conn, account_id=account_id, plan_id=plan_id, scene_id=scene_id, action="scene_created", revision=1)

        _audit(
            conn,
            request=request,
            account=account,
            action="web.video.storyboard_composer.save_plan",
            target=plan_id,
            detail="server-recomputed storyboard composer saved as web-owned draft video plan",
        )
        return envelope(
            True,
            "Đã lưu storyboard thành Video Plan Draft riêng tư. Chưa có phê duyệt, lock, render, job, media, thanh toán hoặc giao hàng.",
            data={
                "_storyboard_composer_plan_save": True,
                "plan": {"id": plan_id, "revision": 1, "state": "draft"},
                "scene_count": len(scene_payloads),
            },
            status_name="draft",
        )

    return _idempotent(
        f"web-video-studio:{account_id}:storyboard-composer:save-plan",
        account_id,
        payload.idempotency_key,
        fingerprint,
        operation,
    )


@router.get("/summary")
async def video_studio_summary(account: dict = Depends(require_account)):
    _require_enabled()
    ensure_copyfast_schema()
    with read_transaction() as conn:
        data = _summary_data(conn, account_id=str(account["id"]))
    return envelope(True, "Video Production Studio đã sẵn sàng cho authoring Web-native.", data=data, status_name="completed")


@router.get("/policy")
async def video_studio_policy(account: dict = Depends(require_account)):
    _require_enabled()
    return envelope(
        True,
        "Boundary Video Production Studio đã được công bố.",
        data={
            **_boundary(),
            "render": "guarded",
            "media_generation": "guarded",
            "delivery": "guarded",
            "self_review": "metadata_only",
        },
        status_name="read_only",
    )


@router.get("/references")
async def video_studio_references(account: dict = Depends(require_account)):
    _require_enabled()
    ensure_copyfast_schema()
    with read_transaction() as conn:
        data = _references_listing(conn, account_id=str(account["id"]))
    return envelope(True, "Đã nạp Project reference thuộc Web account hiện tại.", data=data, status_name="completed")


@router.get("/plans")
async def list_plans(
    q: str = "",
    state: str = "all",
    limit: int = 100,
    account: dict = Depends(require_account),
):
    _require_enabled()
    ensure_copyfast_schema()
    query = _line(q, label="Từ khoá", minimum=0, maximum=100, allow_empty=True)
    state_value = str(state or "all").strip().lower()
    if state_value not in {"all", *PLAN_STATES}:
        raise HTTPException(status_code=422, detail="Bộ lọc trạng thái không hợp lệ")
    bounded = max(1, min(MAX_LIST_LIMIT, int(limit)))
    where = ["p.account_id=?"]
    params: list[Any] = [str(account["id"])]
    if state_value != "all":
        where.append("p.lifecycle=?")
        params.append(state_value)
    if query:
        escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        where.append("(p.title LIKE ? ESCAPE '\\' OR p.objective LIKE ? ESCAPE '\\' OR p.brief LIKE ? ESCAPE '\\')")
        params.extend([f"%{escaped}%", f"%{escaped}%", f"%{escaped}%"])
    with read_transaction() as conn:
        rows = conn.execute(
            f"""SELECT p.id, p.project_id, p.title, p.video_format, p.language, p.aspect_ratio, p.target_duration_seconds,
                       p.objective, p.audience, p.brief, p.tags_json, p.lifecycle, p.revision, p.created_at, p.updated_at, p.archived_at,
                       (SELECT COUNT(*) FROM web_video_scenes s WHERE s.plan_id=p.id AND s.account_id=p.account_id AND s.state='active')
                FROM web_video_plans p WHERE {' AND '.join(where)}
                ORDER BY CASE p.lifecycle WHEN 'draft' THEN 0 WHEN 'review' THEN 1 WHEN 'approved' THEN 2 ELSE 3 END,
                         p.updated_at DESC, p.id DESC LIMIT ?""",
            (*params, bounded),
        ).fetchall()
    items = [_plan_public(tuple(row[:16]), scene_count=int(row[16] or 0)) for row in rows]
    return envelope(True, "Đã nạp video plan riêng tư.", data={"items": items, "limit": bounded, **_boundary()}, status_name="completed")


@router.post("/plans")
async def create_plan(payload: PlanCreateRequest, request: Request, account: dict = Depends(require_csrf)):
    _require_enabled()
    account_id = str(account["id"])
    fingerprint = _fingerprint({"operation": "plan-create", **payload.model_dump(exclude={"idempotency_key"})})

    def operation(conn: Any) -> dict[str, Any]:
        count = conn.execute("SELECT COUNT(*) FROM web_video_plans WHERE account_id=? AND lifecycle<>'archived'", (account_id,)).fetchone()
        if int(count[0] or 0) >= MAX_PLANS_PER_ACCOUNT:
            return envelope(False, "Video Production Studio đã đạt giới hạn plan đang hoạt động.", status_name="guarded", error_code="WEB_VIDEO_PLAN_LIMIT")
        _project_reference(conn, account_id=account_id, project_id=payload.project_id, active=True)
        plan_id = str(uuid.uuid4())
        now = utc_now()
        snapshot = _plan_snapshot(payload, lifecycle="draft")
        _insert_plan(conn, plan_id=plan_id, account_id=account_id, snapshot=snapshot, revision=1, now=now)
        _insert_plan_version(conn, plan_id=plan_id, account_id=account_id, revision=1, snapshot=snapshot, now=now)
        _event(conn, account_id=account_id, plan_id=plan_id, action="plan_created", revision=1)
        _audit(conn, request=request, account=account, action="web.video.plan.create", target=plan_id, detail=f"format={payload.format};revision=1")
        row = _plan_row(conn, plan_id=plan_id, account_id=account_id)
        return envelope(True, "Đã tạo video plan Web-native.", data={"plan": _plan_public(row) if row else {}, **_boundary()}, status_name="draft")

    return _idempotent(f"web-video-studio:{account_id}:plan:create", account_id, payload.idempotency_key, fingerprint, operation)


@router.get("/plans/{plan_id}")
async def get_plan(plan_id: str, account: dict = Depends(require_account)):
    _require_enabled()
    resolved = _uuid(plan_id, label="Video plan ID")
    ensure_copyfast_schema()
    with read_transaction() as conn:
        detail = _plan_detail(conn, plan_id=resolved, account_id=str(account["id"]))
    return envelope(True, "Đã nạp video plan riêng tư.", data=detail, status_name="completed") if detail else _plan_not_found()


@router.patch("/plans/{plan_id}")
async def update_plan(plan_id: str, payload: PlanUpdateRequest, request: Request, account: dict = Depends(require_csrf)):
    _require_enabled()
    resolved = _uuid(plan_id, label="Video plan ID")
    account_id = str(account["id"])
    fingerprint = _fingerprint({"operation": "plan-update", "plan_id": resolved, **payload.model_dump(exclude={"idempotency_key"})})

    def operation(conn: Any) -> dict[str, Any]:
        existing = _plan_row(conn, plan_id=resolved, account_id=account_id)
        if not existing:
            return _plan_not_found()
        blocked = _plan_writable(existing)
        if blocked:
            return blocked
        if int(existing[12]) != payload.expected_revision:
            return _revision_conflict()
        if not _can_add_version(conn, table="web_video_plan_versions", entity_column="plan_id", entity_id=resolved, account_id=account_id):
            return envelope(False, "Video plan đã đạt giới hạn lịch sử phiên bản.", status_name="guarded", error_code="WEB_VIDEO_VERSION_LIMIT")
        _project_reference(conn, account_id=account_id, project_id=payload.project_id, active=True)
        now = utc_now()
        lifecycle = "draft" if str(existing[11]) == "review" else str(existing[11])
        snapshot = _plan_snapshot(payload, lifecycle=lifecycle)
        revision = int(existing[12]) + 1
        _write_plan(conn, plan_id=resolved, account_id=account_id, snapshot=snapshot, revision=revision, now=now, archived_at=None)
        _insert_plan_version(conn, plan_id=resolved, account_id=account_id, revision=revision, snapshot=snapshot, now=now)
        _event(conn, account_id=account_id, plan_id=resolved, action="plan_updated", revision=revision)
        _audit(conn, request=request, account=account, action="web.video.plan.update", target=resolved, detail=f"revision={revision};state={lifecycle}")
        row = _plan_row(conn, plan_id=resolved, account_id=account_id)
        return envelope(True, "Đã lưu revision video plan mới.", data={"plan": _plan_public(row) if row else {}, "history_snapshot_recorded": True, **_boundary()}, status_name="draft")

    return _idempotent(f"web-video-studio:{account_id}:plan:{resolved}:update", account_id, payload.idempotency_key, fingerprint, operation)


def _allowed_transition(current: str, target: str) -> bool:
    allowed = {
        "draft": {"review", "archived"},
        "review": {"draft", "approved", "archived"},
        "approved": {"draft", "archived"},
        "archived": {"draft"},
    }
    return target in allowed.get(current, set())


@router.post("/plans/{plan_id}/lifecycle")
async def set_plan_lifecycle(plan_id: str, payload: LifecycleRequest, request: Request, account: dict = Depends(require_csrf)):
    _require_enabled()
    resolved = _uuid(plan_id, label="Video plan ID")
    account_id = str(account["id"])
    fingerprint = _fingerprint({"operation": "plan-lifecycle", "plan_id": resolved, **payload.model_dump(exclude={"idempotency_key"})})

    def operation(conn: Any) -> dict[str, Any]:
        existing = _plan_row(conn, plan_id=resolved, account_id=account_id)
        if not existing:
            return _plan_not_found()
        if int(existing[12]) != payload.expected_revision:
            return _revision_conflict()
        current = str(existing[11])
        if not _allowed_transition(current, payload.state):
            return envelope(False, "Chuyển trạng thái self-review này không hợp lệ.", status_name="guarded", error_code="WEB_VIDEO_LIFECYCLE_GUARD")
        if not _can_add_version(conn, table="web_video_plan_versions", entity_column="plan_id", entity_id=resolved, account_id=account_id):
            return envelope(False, "Video plan đã đạt giới hạn lịch sử phiên bản.", status_name="guarded", error_code="WEB_VIDEO_VERSION_LIMIT")
        snapshot = _plan_snapshot_from_row(existing, lifecycle=payload.state)
        now = utc_now()
        revision = int(existing[12]) + 1
        _write_plan(conn, plan_id=resolved, account_id=account_id, snapshot=snapshot, revision=revision, now=now, archived_at=now if payload.state == "archived" else None)
        _insert_plan_version(conn, plan_id=resolved, account_id=account_id, revision=revision, snapshot=snapshot, now=now)
        _event(conn, account_id=account_id, plan_id=resolved, action="plan_state_changed", revision=revision)
        _audit(conn, request=request, account=account, action="web.video.plan.lifecycle", target=resolved, detail=f"{current}->{payload.state};revision={revision}")
        row = _plan_row(conn, plan_id=resolved, account_id=account_id)
        return envelope(True, "Đã cập nhật trạng thái self-review.", data={"plan": _plan_public(row) if row else {}, "history_snapshot_recorded": True, **_boundary()}, status_name=payload.state)

    return _idempotent(f"web-video-studio:{account_id}:plan:{resolved}:lifecycle:{payload.state}", account_id, payload.idempotency_key, fingerprint, operation)


@router.post("/plans/{plan_id}/restore-version")
async def restore_plan_version(plan_id: str, payload: RestoreVersionRequest, request: Request, account: dict = Depends(require_csrf)):
    _require_enabled()
    resolved = _uuid(plan_id, label="Video plan ID")
    account_id = str(account["id"])
    fingerprint = _fingerprint({"operation": "plan-restore-version", "plan_id": resolved, **payload.model_dump(exclude={"idempotency_key"})})

    def operation(conn: Any) -> dict[str, Any]:
        existing = _plan_row(conn, plan_id=resolved, account_id=account_id)
        if not existing:
            return _plan_not_found()
        blocked = _plan_writable(existing)
        if blocked:
            return blocked
        if int(existing[12]) != payload.expected_revision:
            return _revision_conflict()
        if not _can_add_version(conn, table="web_video_plan_versions", entity_column="plan_id", entity_id=resolved, account_id=account_id):
            return envelope(False, "Video plan đã đạt giới hạn lịch sử phiên bản.", status_name="guarded", error_code="WEB_VIDEO_VERSION_LIMIT")
        source = conn.execute(
            "SELECT snapshot_json FROM web_video_plan_versions WHERE plan_id=? AND account_id=? AND revision=?",
            (resolved, account_id, payload.target_revision),
        ).fetchone()
        if not source:
            return envelope(False, "Không tìm thấy version video plan cần khôi phục.", status_name="guarded", error_code="WEB_VIDEO_VERSION_NOT_FOUND")
        try:
            saved = json.loads(str(source[0]))
            restored = _plan_payload_from_snapshot(saved if isinstance(saved, dict) else {})
        except (TypeError, ValueError, json.JSONDecodeError):
            return envelope(False, "Version video plan không hợp lệ.", status_name="guarded", error_code="WEB_VIDEO_VERSION_INVALID")
        _project_reference(conn, account_id=account_id, project_id=restored.project_id, active=True)
        snapshot = _plan_snapshot(restored, lifecycle="draft")
        now = utc_now()
        revision = int(existing[12]) + 1
        _write_plan(conn, plan_id=resolved, account_id=account_id, snapshot=snapshot, revision=revision, now=now, archived_at=None)
        _insert_plan_version(conn, plan_id=resolved, account_id=account_id, revision=revision, snapshot=snapshot, now=now)
        _event(conn, account_id=account_id, plan_id=resolved, action="plan_version_restored", revision=revision)
        _audit(conn, request=request, account=account, action="web.video.plan.restore_version", target=resolved, detail=f"source={payload.target_revision};revision={revision}")
        row = _plan_row(conn, plan_id=resolved, account_id=account_id)
        return envelope(True, "Đã khôi phục version video plan thành revision mới.", data={"plan": _plan_public(row) if row else {}, "history_snapshot_recorded": True, **_boundary()}, status_name="draft")

    return _idempotent(f"web-video-studio:{account_id}:plan:{resolved}:restore-version:{payload.target_revision}", account_id, payload.idempotency_key, fingerprint, operation)


@router.post("/plans/{plan_id}/scenes")
async def create_scene(plan_id: str, payload: SceneCreateRequest, request: Request, account: dict = Depends(require_csrf)):
    _require_enabled()
    resolved = _uuid(plan_id, label="Video plan ID")
    account_id = str(account["id"])
    fingerprint = _fingerprint({"operation": "scene-create", "plan_id": resolved, **payload.model_dump(exclude={"idempotency_key"})})

    def operation(conn: Any) -> dict[str, Any]:
        plan = _plan_row(conn, plan_id=resolved, account_id=account_id)
        if not plan:
            return _plan_not_found()
        blocked = _plan_writable(plan)
        if blocked:
            return blocked
        if int(plan[12]) != payload.expected_revision:
            return _revision_conflict()
        count = conn.execute(
            "SELECT COUNT(*) FROM web_video_scenes WHERE plan_id=? AND account_id=? AND state='active'",
            (resolved, account_id),
        ).fetchone()
        if int(count[0] or 0) >= MAX_SCENES_PER_PLAN:
            return envelope(False, "Video plan đã đạt giới hạn scene đang hoạt động.", status_name="guarded", error_code="WEB_VIDEO_SCENE_LIMIT")
        scene_id = str(uuid.uuid4())
        now = utc_now()
        snapshot = _scene_snapshot(payload)
        _insert_scene(
            conn,
            scene_id=scene_id,
            plan_id=resolved,
            account_id=account_id,
            ordinal=_next_active_ordinal(conn, plan_id=resolved, account_id=account_id),
            snapshot=snapshot,
            revision=1,
            now=now,
        )
        _insert_scene_version(conn, scene_id=scene_id, account_id=account_id, revision=1, snapshot=snapshot, now=now)
        changed_plan = _advance_plan_for_scene_change(conn, plan=plan, account_id=account_id, now=now, event="scene_created", scene_id=scene_id)
        _audit(conn, request=request, account=account, action="web.video.scene.create", target=scene_id, detail=f"plan={resolved};plan_revision={changed_plan[12]}")
        row = _scene_row(conn, plan_id=resolved, scene_id=scene_id, account_id=account_id)
        return envelope(True, "Đã thêm scene riêng tư vào video plan.", data={"scene": _scene_public(row) if row else {}, "plan": _plan_public(changed_plan), **_boundary()}, status_name="draft")

    return _idempotent(f"web-video-studio:{account_id}:plan:{resolved}:scene:create", account_id, payload.idempotency_key, fingerprint, operation)


@router.patch("/plans/{plan_id}/scenes/{scene_id}")
async def update_scene(plan_id: str, scene_id: str, payload: SceneUpdateRequest, request: Request, account: dict = Depends(require_csrf)):
    _require_enabled()
    resolved_plan = _uuid(plan_id, label="Video plan ID")
    resolved_scene = _uuid(scene_id, label="Scene ID")
    account_id = str(account["id"])
    fingerprint = _fingerprint({"operation": "scene-update", "plan_id": resolved_plan, "scene_id": resolved_scene, **payload.model_dump(exclude={"idempotency_key"})})

    def operation(conn: Any) -> dict[str, Any]:
        plan = _plan_row(conn, plan_id=resolved_plan, account_id=account_id)
        if not plan:
            return _plan_not_found()
        blocked = _plan_writable(plan)
        if blocked:
            return blocked
        scene = _scene_row(conn, plan_id=resolved_plan, scene_id=resolved_scene, account_id=account_id)
        if not scene:
            return _scene_not_found()
        if str(scene[12]) != "active":
            return _scene_archived()
        if int(scene[13]) != payload.expected_revision:
            return _revision_conflict()
        if not _can_add_version(conn, table="web_video_scene_versions", entity_column="scene_id", entity_id=resolved_scene, account_id=account_id):
            return envelope(False, "Scene đã đạt giới hạn lịch sử phiên bản.", status_name="guarded", error_code="WEB_VIDEO_VERSION_LIMIT")
        now = utc_now()
        snapshot = _scene_snapshot(payload)
        revision = int(scene[13]) + 1
        _write_scene(conn, scene_id=resolved_scene, plan_id=resolved_plan, account_id=account_id, snapshot=snapshot, revision=revision, now=now, archived_at=None)
        _insert_scene_version(conn, scene_id=resolved_scene, account_id=account_id, revision=revision, snapshot=snapshot, now=now)
        changed_plan = _advance_plan_for_scene_change(conn, plan=plan, account_id=account_id, now=now, event="scene_updated", scene_id=resolved_scene)
        _audit(conn, request=request, account=account, action="web.video.scene.update", target=resolved_scene, detail=f"plan={resolved_plan};revision={revision}")
        row = _scene_row(conn, plan_id=resolved_plan, scene_id=resolved_scene, account_id=account_id)
        return envelope(True, "Đã lưu revision scene mới.", data={"scene": _scene_public(row) if row else {}, "plan": _plan_public(changed_plan), "history_snapshot_recorded": True, **_boundary()}, status_name="draft")

    return _idempotent(f"web-video-studio:{account_id}:plan:{resolved_plan}:scene:{resolved_scene}:update", account_id, payload.idempotency_key, fingerprint, operation)


def _scene_state_mutation(plan_id: str, scene_id: str, payload: RevisionRequest | RestoreVersionRequest, request: Request, account: dict, *, action: str) -> dict[str, Any]:
    account_id = str(account["id"])
    resolved_plan = _uuid(plan_id, label="Video plan ID")
    resolved_scene = _uuid(scene_id, label="Scene ID")
    source_revision = payload.target_revision if isinstance(payload, RestoreVersionRequest) else None
    fingerprint = _fingerprint(
        {
            "operation": f"scene-{action}",
            "plan_id": resolved_plan,
            "scene_id": resolved_scene,
            "expected_revision": payload.expected_revision,
            "target_revision": source_revision,
        }
    )

    def operation(conn: Any) -> dict[str, Any]:
        plan = _plan_row(conn, plan_id=resolved_plan, account_id=account_id)
        if not plan:
            return _plan_not_found()
        blocked = _plan_writable(plan)
        if blocked:
            return blocked
        scene = _scene_row(conn, plan_id=resolved_plan, scene_id=resolved_scene, account_id=account_id)
        if not scene:
            return _scene_not_found()
        if int(scene[13]) != payload.expected_revision:
            return _revision_conflict()
        if not _can_add_version(conn, table="web_video_scene_versions", entity_column="scene_id", entity_id=resolved_scene, account_id=account_id):
            return envelope(False, "Scene đã đạt giới hạn lịch sử phiên bản.", status_name="guarded", error_code="WEB_VIDEO_VERSION_LIMIT")
        current = str(scene[12])
        next_ordinal: int | None = None
        if action == "archive":
            if current != "active":
                return _scene_archived()
            snapshot = _scene_snapshot_from_row(scene, state="archived")
            next_ordinal = _next_archived_ordinal(conn, plan_id=resolved_plan, account_id=account_id)
            event = "scene_archived"
        elif action == "restore":
            if current != "archived":
                return envelope(False, "Scene đang hoạt động.", status_name="guarded", error_code="WEB_VIDEO_SCENE_ACTIVE")
            count = conn.execute(
                "SELECT COUNT(*) FROM web_video_scenes WHERE plan_id=? AND account_id=? AND state='active'",
                (resolved_plan, account_id),
            ).fetchone()
            if int(count[0] or 0) >= MAX_SCENES_PER_PLAN:
                return envelope(False, "Video plan đã đạt giới hạn scene đang hoạt động.", status_name="guarded", error_code="WEB_VIDEO_SCENE_LIMIT")
            snapshot = _scene_snapshot_from_row(scene, state="active")
            next_ordinal = _next_active_ordinal(conn, plan_id=resolved_plan, account_id=account_id)
            event = "scene_restored"
        elif action == "restore-version":
            if current != "active":
                return _scene_archived()
            saved = conn.execute(
                "SELECT snapshot_json FROM web_video_scene_versions WHERE scene_id=? AND account_id=? AND revision=?",
                (resolved_scene, account_id, source_revision),
            ).fetchone()
            if not saved:
                return envelope(False, "Không tìm thấy version scene cần khôi phục.", status_name="guarded", error_code="WEB_VIDEO_VERSION_NOT_FOUND")
            try:
                parsed = json.loads(str(saved[0]))
                restored = _scene_payload_from_snapshot(parsed if isinstance(parsed, dict) else {})
            except (TypeError, ValueError, json.JSONDecodeError):
                return envelope(False, "Version scene không hợp lệ.", status_name="guarded", error_code="WEB_VIDEO_VERSION_INVALID")
            snapshot = _scene_snapshot(restored, state="active")
            event = "scene_version_restored"
        else:
            raise HTTPException(status_code=500, detail="Thao tác scene không hỗ trợ")
        now = utc_now()
        revision = int(scene[13]) + 1
        _write_scene(
            conn,
            scene_id=resolved_scene,
            plan_id=resolved_plan,
            account_id=account_id,
            snapshot=snapshot,
            revision=revision,
            now=now,
            archived_at=now if snapshot["state"] == "archived" else None,
        )
        if next_ordinal is not None:
            conn.execute(
                "UPDATE web_video_scenes SET ordinal=? WHERE id=? AND plan_id=? AND account_id=?",
                (next_ordinal, resolved_scene, resolved_plan, account_id),
            )
        _insert_scene_version(conn, scene_id=resolved_scene, account_id=account_id, revision=revision, snapshot=snapshot, now=now)
        changed_plan = _advance_plan_for_scene_change(conn, plan=plan, account_id=account_id, now=now, event=event, scene_id=resolved_scene)
        _audit(conn, request=request, account=account, action=f"web.video.scene.{action}", target=resolved_scene, detail=f"plan={resolved_plan};revision={revision}")
        row = _scene_row(conn, plan_id=resolved_plan, scene_id=resolved_scene, account_id=account_id)
        return envelope(True, "Đã cập nhật trạng thái scene.", data={"scene": _scene_public(row) if row else {}, "plan": _plan_public(changed_plan), "history_snapshot_recorded": True, **_boundary()}, status_name="draft")

    suffix = f":{source_revision}" if source_revision else ""
    return _idempotent(f"web-video-studio:{account_id}:plan:{resolved_plan}:scene:{resolved_scene}:{action}{suffix}", account_id, payload.idempotency_key, fingerprint, operation)


@router.post("/plans/{plan_id}/scenes/{scene_id}/archive")
async def archive_scene(plan_id: str, scene_id: str, payload: RevisionRequest, request: Request, account: dict = Depends(require_csrf)):
    _require_enabled()
    return _scene_state_mutation(plan_id, scene_id, payload, request, account, action="archive")


@router.post("/plans/{plan_id}/scenes/{scene_id}/restore")
async def restore_scene(plan_id: str, scene_id: str, payload: RevisionRequest, request: Request, account: dict = Depends(require_csrf)):
    _require_enabled()
    return _scene_state_mutation(plan_id, scene_id, payload, request, account, action="restore")


@router.post("/plans/{plan_id}/scenes/{scene_id}/restore-version")
async def restore_scene_version(plan_id: str, scene_id: str, payload: RestoreVersionRequest, request: Request, account: dict = Depends(require_csrf)):
    _require_enabled()
    return _scene_state_mutation(plan_id, scene_id, payload, request, account, action="restore-version")


@router.post("/plans/{plan_id}/scenes/reorder")
async def reorder_scenes(plan_id: str, payload: ReorderRequest, request: Request, account: dict = Depends(require_csrf)):
    _require_enabled()
    resolved = _uuid(plan_id, label="Video plan ID")
    account_id = str(account["id"])
    fingerprint = _fingerprint({"operation": "scenes-reorder", "plan_id": resolved, **payload.model_dump(exclude={"idempotency_key"})})

    def operation(conn: Any) -> dict[str, Any]:
        plan = _plan_row(conn, plan_id=resolved, account_id=account_id)
        if not plan:
            return _plan_not_found()
        blocked = _plan_writable(plan)
        if blocked:
            return blocked
        if int(plan[12]) != payload.expected_revision:
            return _revision_conflict()
        rows = conn.execute(
            "SELECT id, ordinal FROM web_video_scenes WHERE plan_id=? AND account_id=? AND state='active' ORDER BY ordinal ASC, id ASC",
            (resolved, account_id),
        ).fetchall()
        current = [str(row[0]) for row in rows]
        proposed = list(payload.scene_ids)
        if len(current) != len(proposed) or set(current) != set(proposed):
            return envelope(False, "Thứ tự scene phải chứa đúng mỗi scene đang hoạt động của plan.", status_name="guarded", error_code="WEB_VIDEO_REORDER_INVALID")
        if not _can_add_version(conn, table="web_video_plan_versions", entity_column="plan_id", entity_id=resolved, account_id=account_id):
            return envelope(False, "Video plan đã đạt giới hạn lịch sử phiên bản.", status_name="guarded", error_code="WEB_VIDEO_VERSION_LIMIT")
        now = utc_now()
        # An archived scene is kept for history but must never reserve an
        # active ordinal.  Normalise first so both freshly archived and any
        # older low-ordinal rows cannot collide with the active 1..N order.
        _normalise_archived_ordinals(conn, plan_id=resolved, account_id=account_id)
        # The unique (plan_id, ordinal) constraint requires a temporary,
        # disjoint ordinal range before writing the final one-based sequence.
        for index, scene_id in enumerate(proposed, start=1):
            conn.execute(
                "UPDATE web_video_scenes SET ordinal=? WHERE id=? AND plan_id=? AND account_id=?",
                (REORDER_TEMPORARY_ORDINAL_BASE + index, scene_id, resolved, account_id),
            )
        for index, scene_id in enumerate(proposed, start=1):
            conn.execute(
                "UPDATE web_video_scenes SET ordinal=?, updated_at=? WHERE id=? AND plan_id=? AND account_id=?",
                (index, now, scene_id, resolved, account_id),
            )
        changed_plan = _advance_plan_for_scene_change(conn, plan=plan, account_id=account_id, now=now, event="scenes_reordered")
        _audit(conn, request=request, account=account, action="web.video.scene.reorder", target=resolved, detail=f"count={len(proposed)};revision={changed_plan[12]}")
        return envelope(True, "Đã cập nhật thứ tự scene.", data={"plan": _plan_public(changed_plan), "scene_count": len(proposed), "reordered": True, **_boundary()}, status_name="draft")

    return _idempotent(f"web-video-studio:{account_id}:plan:{resolved}:scenes:reorder", account_id, payload.idempotency_key, fingerprint, operation)


@router.get("/plans/{plan_id}/estimate")
async def plan_estimate(plan_id: str, account: dict = Depends(require_account)):
    _require_enabled()
    resolved = _uuid(plan_id, label="Video plan ID")
    ensure_copyfast_schema()
    with read_transaction() as conn:
        plan = _plan_row(conn, plan_id=resolved, account_id=str(account["id"]))
        if not plan:
            return _plan_not_found()
        return _estimate(conn, plan=plan, account_id=str(account["id"]))


@router.get("/events")
async def list_events(limit: int = 50, account: dict = Depends(require_account)):
    _require_enabled()
    ensure_copyfast_schema()
    bounded = max(1, min(MAX_EVENT_LIMIT, int(limit)))
    with read_transaction() as conn:
        rows = conn.execute(
            "SELECT plan_id, scene_id, entity_type, action, revision, created_at FROM web_video_studio_events WHERE account_id=? ORDER BY created_at DESC, id DESC LIMIT ?",
            (str(account["id"]), bounded),
        ).fetchall()
    return envelope(
        True,
        "Đã nạp hoạt động Video Production Studio.",
        data={
            "items": [
                {
                    "plan_id": str(row[0]),
                    "scene_id": str(row[1]) if row[1] else None,
                    "entity_type": str(row[2]),
                    "action": str(row[3]),
                    "revision": int(row[4]),
                    "created_at": str(row[5]),
                }
                for row in rows
            ],
            "limit": bounded,
            **_boundary(),
        },
        status_name="completed",
    )


# Video Idea Planner is the Web-native, deterministic translation of the
# Bot's ``videoidea`` conversation.  The Bot keeps a Telegram-only pending
# state and exposes a long callback tree (kind → product/topic → goal →
# context → three ideas → selected package).  The Web condenses those bounded
# choices into a single reviewable request.  It intentionally copies only the
# editorial grammar: it does not import Bot state, media, jobs, providers,
# billing or delivery behavior.
VIDEO_IDEA_PLANNER_KINDS = frozenset({"ad", "cinema", "custom"})
VIDEO_IDEA_PLANNER_PRODUCT_TYPES = frozenset({"physical", "service", "affiliate", "custom"})
VIDEO_IDEA_PLANNER_GOALS = frozenset({"sales", "brand", "viral", "story"})
VIDEO_IDEA_PLANNER_CONTEXTS = frozenset({"everyday", "studio", "cinematic", "technology", "lifestyle"})
VIDEO_IDEA_PLANNER_PLATFORMS = {
    "tiktok": {"label": "TikTok", "aspect_ratio": "9:16"},
    "reels": {"label": "Instagram Reels", "aspect_ratio": "9:16"},
    "shorts": {"label": "YouTube Shorts", "aspect_ratio": "9:16"},
    "youtube": {"label": "YouTube", "aspect_ratio": "16:9"},
    "facebook": {"label": "Facebook / Ads", "aspect_ratio": "4:5"},
    "custom": {"label": "Kênh riêng", "aspect_ratio": "custom"},
}
VIDEO_IDEA_PLANNER_DURATIONS = frozenset({15, 30, 45, 60})
VIDEO_IDEA_PLANNER_LANGUAGES = frozenset({"vi", "en"})


def _video_idea_code(value: Any, *, label: str, allowed: frozenset[str] | set[str]) -> str:
    normalized = _planner_line(value, label=label, minimum=1, maximum=64).lower()
    if normalized not in allowed:
        raise ValueError(f"{label} không hợp lệ")
    return normalized


def _video_idea_boundary() -> dict[str, Any]:
    """Exact no-execution boundary for one temporary idea-planner result."""

    return {
        "execution": "web_native_deterministic_video_idea_only",
        "input_persisted": False,
        "telegram_state_changed": False,
        "bot_called": False,
        "bridge_called": False,
        "source_media_inspected": False,
        "provider_called": False,
        "image_created": False,
        "video_created": False,
        "audio_created": False,
        "preview_created": False,
        "output_created": False,
        "job_created": False,
        "payment_started": False,
        "wallet_mutated": False,
        "asset_saved": False,
        "publish_action_created": False,
        "fact_checked": False,
        "rights_verified": False,
    }


def _video_idea_plan_save_boundary(
    *,
    draft_recomputed_on_server: bool = True,
    web_video_plan_persisted: bool = True,
) -> dict[str, bool | str]:
    """State the one permitted durable effect of an explicit Web save."""

    return {
        "execution": "web_native_video_plan_server_recomputed",
        "draft_recomputed_on_server": draft_recomputed_on_server,
        "web_video_plan_persisted": web_video_plan_persisted,
        "browser_result_persisted": False,
        "pending_bot_save_created": False,
        "telegram_state_changed": False,
        "bot_called": False,
        "bridge_called": False,
        "source_media_inspected": False,
        "media_uploads": False,
        "provider_called": False,
        "image_created": False,
        "video_created": False,
        "audio_created": False,
        "preview_created": False,
        "output_created": False,
        "job_created": False,
        "wallet_mutated": False,
        "payment_started": False,
        "asset_saved": False,
        "publish_action_created": False,
        "delivery_created": False,
        "approval_created": False,
        "plan_approved": False,
        "plan_locked": False,
        "generation_started": False,
        "fact_checked": False,
        "rights_verified": False,
    }


def _video_idea_guard(marker: str, *, saving: bool = False) -> dict[str, Any] | None:
    if not marker:
        return None
    if marker == "claim":
        message = "Mô tả có tuyên bố cần nguồn hoặc kiểm chứng. Hãy viết lại theo hướng có thể review trước khi lập kế hoạch."
        error_code = "WEB_VIDEO_IDEA_CLAIM_GUARD"
    else:
        message = "Mô tả cần được viết lại theo hướng nguyên bản và không mô phỏng người thật, người nổi tiếng hoặc phong cách cụ thể."
        error_code = "WEB_VIDEO_IDEA_ORIGINALITY_GUARD"
    data: dict[str, Any] = (
        {"destination": "video_plan", **_video_idea_plan_save_boundary(draft_recomputed_on_server=False, web_video_plan_persisted=False)}
        if saving
        else _video_idea_boundary()
    )
    return envelope(False, message, data=data, status_name="guarded", error_code=error_code)


class VideoIdeaPlannerRequest(BaseModel):
    """Bounded original choices for the Bot-derived idea conversation only."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, strict=True)

    idea_kind: StrictStr
    product_type: StrictStr
    topic: StrictStr
    audience: StrictStr
    goal: StrictStr
    context: StrictStr
    platform: StrictStr
    language: StrictStr
    duration_seconds: StrictInt
    idea_set: StrictInt = Field(ge=1, le=3)
    idea_choice: StrictInt = Field(ge=1, le=3)
    custom_brief: StrictStr = ""

    @field_validator("idea_kind")
    @classmethod
    def validate_idea_kind(cls, value: StrictStr) -> str:
        return _video_idea_code(value, label="Loại Video Idea", allowed=VIDEO_IDEA_PLANNER_KINDS)

    @field_validator("product_type")
    @classmethod
    def validate_product_type(cls, value: StrictStr) -> str:
        return _video_idea_code(value, label="Loại sản phẩm", allowed=VIDEO_IDEA_PLANNER_PRODUCT_TYPES)

    @field_validator("goal")
    @classmethod
    def validate_goal(cls, value: StrictStr) -> str:
        return _video_idea_code(value, label="Mục tiêu Video Idea", allowed=VIDEO_IDEA_PLANNER_GOALS)

    @field_validator("context")
    @classmethod
    def validate_context(cls, value: StrictStr) -> str:
        return _video_idea_code(value, label="Bối cảnh Video Idea", allowed=VIDEO_IDEA_PLANNER_CONTEXTS)

    @field_validator("platform")
    @classmethod
    def validate_platform(cls, value: StrictStr) -> str:
        return _video_idea_code(value, label="Nền tảng Video Idea", allowed=set(VIDEO_IDEA_PLANNER_PLATFORMS))

    @field_validator("language")
    @classmethod
    def validate_language(cls, value: StrictStr) -> str:
        return _video_idea_code(value, label="Ngôn ngữ Video Idea", allowed=VIDEO_IDEA_PLANNER_LANGUAGES)

    @field_validator("topic")
    @classmethod
    def validate_topic(cls, value: StrictStr) -> str:
        return _planner_line(value, label="Chủ đề Video Idea", minimum=2, maximum=500)

    @field_validator("audience")
    @classmethod
    def validate_audience(cls, value: StrictStr) -> str:
        return _planner_line(value, label="Khán giả Video Idea", minimum=2, maximum=500)

    @field_validator("custom_brief")
    @classmethod
    def validate_custom_brief(cls, value: StrictStr) -> str:
        return _planner_line(value, label="Brief tùy chỉnh", minimum=0, maximum=700, allow_empty=True)

    @field_validator("duration_seconds")
    @classmethod
    def validate_duration(cls, value: StrictInt) -> int:
        if value not in VIDEO_IDEA_PLANNER_DURATIONS:
            raise ValueError("Video Idea Planner chỉ hỗ trợ 15, 30, 45 hoặc 60 giây")
        return int(value)

    def model_post_init(self, __context: Any) -> None:
        if self.idea_kind == "custom" and not self.custom_brief:
            raise ValueError("Ý tưởng tùy chỉnh cần brief tùy chỉnh")


class VideoIdeaPlannerPlanSaveRequest(VideoIdeaPlannerRequest):
    """Browser sends choices only; the server rebuilds every plan field."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, strict=True)

    destination: StrictStr
    idempotency_key: StrictStr

    @field_validator("destination")
    @classmethod
    def validate_destination(cls, value: StrictStr) -> str:
        return _video_idea_code(value, label="Nơi lưu Video Idea", allowed={"video_plan"})

    @field_validator("idempotency_key")
    @classmethod
    def validate_idempotency_key(cls, value: StrictStr) -> str:
        return _idempotency_key(value)


class VideoIdeaPlannerConcept(BaseModel):
    model_config = ConfigDict(extra="forbid")

    index: StrictInt = Field(ge=1, le=3)
    title: str
    premise: str
    hook: str
    story_structure: str
    cta: str

    @field_validator("title", "premise", "hook", "story_structure", "cta")
    @classmethod
    def validate_text(cls, value: str) -> str:
        return _planner_line(value, label="Nội dung Video Idea", minimum=2, maximum=1_200)


class VideoIdeaPlannerScene(BaseModel):
    model_config = ConfigDict(extra="forbid")

    index: StrictInt = Field(ge=1, le=6)
    start_seconds: StrictInt = Field(ge=0, le=60)
    end_seconds: StrictInt = Field(ge=1, le=60)
    title: str
    visual_direction: str
    camera: str
    narration: str
    image_prompt: str
    video_prompt: str
    audio_direction: str
    transition: str

    @field_validator("title", "visual_direction", "camera", "narration", "image_prompt", "video_prompt", "audio_direction", "transition")
    @classmethod
    def validate_text(cls, value: str) -> str:
        return _planner_line(value, label="Scene Video Idea", minimum=2, maximum=2_400)

    def model_post_init(self, __context: Any) -> None:
        if self.end_seconds <= self.start_seconds:
            raise ValueError("Mốc kết thúc scene Video Idea phải lớn hơn mốc bắt đầu")


class VideoIdeaPlannerResult(BaseModel):
    """Exact browser-safe output: editorial text, never a media receipt."""

    model_config = ConfigDict(extra="forbid")

    title: str
    idea_kind: str
    product_type: str
    platform: str
    aspect_ratio: str
    goal: str
    context: str
    topic: str
    audience: str
    language: str
    duration_seconds: StrictInt
    idea_set: StrictInt
    selected_concept: VideoIdeaPlannerConcept
    concepts: list[VideoIdeaPlannerConcept] = Field(min_length=3, max_length=3)
    scenes: list[VideoIdeaPlannerScene] = Field(min_length=6, max_length=6)
    caption: str
    hashtags: list[str] = Field(min_length=3, max_length=8)
    review_before_use: list[str] = Field(min_length=2, max_length=7)

    @field_validator("title", "topic", "audience", "caption")
    @classmethod
    def validate_text(cls, value: str) -> str:
        return _planner_line(value, label="Kết quả Video Idea", minimum=2, maximum=2_400)

    @field_validator("idea_kind")
    @classmethod
    def validate_result_kind(cls, value: str) -> str:
        return _video_idea_code(value, label="Loại kết quả Video Idea", allowed=VIDEO_IDEA_PLANNER_KINDS)

    @field_validator("product_type")
    @classmethod
    def validate_result_product_type(cls, value: str) -> str:
        return _video_idea_code(value, label="Loại sản phẩm kết quả", allowed=VIDEO_IDEA_PLANNER_PRODUCT_TYPES)

    @field_validator("platform")
    @classmethod
    def validate_result_platform(cls, value: str) -> str:
        return _video_idea_code(value, label="Nền tảng kết quả", allowed=set(VIDEO_IDEA_PLANNER_PLATFORMS))

    @field_validator("goal")
    @classmethod
    def validate_result_goal(cls, value: str) -> str:
        return _video_idea_code(value, label="Mục tiêu kết quả", allowed=VIDEO_IDEA_PLANNER_GOALS)

    @field_validator("context")
    @classmethod
    def validate_result_context(cls, value: str) -> str:
        return _video_idea_code(value, label="Bối cảnh kết quả", allowed=VIDEO_IDEA_PLANNER_CONTEXTS)

    @field_validator("language")
    @classmethod
    def validate_result_language(cls, value: str) -> str:
        return _video_idea_code(value, label="Ngôn ngữ kết quả", allowed=VIDEO_IDEA_PLANNER_LANGUAGES)

    @field_validator("aspect_ratio")
    @classmethod
    def validate_ratio(cls, value: str) -> str:
        return _line(value, label="Tỷ lệ Video Idea", minimum=3, maximum=8)

    @field_validator("duration_seconds")
    @classmethod
    def validate_result_duration(cls, value: int) -> int:
        if value not in VIDEO_IDEA_PLANNER_DURATIONS:
            raise ValueError("Thời lượng Video Idea không hợp lệ")
        return value

    @field_validator("idea_set")
    @classmethod
    def validate_result_set(cls, value: int) -> int:
        if not 1 <= value <= 3:
            raise ValueError("Nhóm ý tưởng Video Idea không hợp lệ")
        return value

    @field_validator("hashtags", "review_before_use")
    @classmethod
    def validate_lists(cls, value: list[str]) -> list[str]:
        return [_planner_line(item, label="Danh sách Video Idea", minimum=2, maximum=500) for item in value]

    def model_post_init(self, __context: Any) -> None:
        if [concept.index for concept in self.concepts] != [1, 2, 3]:
            raise ValueError("Video Idea cần đúng ba concept theo thứ tự")
        if self.selected_concept.index not in {1, 2, 3}:
            raise ValueError("Concept Video Idea được chọn không hợp lệ")
        if [scene.index for scene in self.scenes] != [1, 2, 3, 4, 5, 6]:
            raise ValueError("Video Idea cần đúng sáu scene theo thứ tự")
        if self.scenes[-1].end_seconds != self.duration_seconds:
            raise ValueError("Timeline Video Idea phải kết thúc đúng thời lượng đã chọn")


def _video_idea_concept_templates(payload: VideoIdeaPlannerRequest) -> tuple[tuple[str, str, str, str, str], ...]:
    """Reimplement the Bot's three static choice sets without importing it."""

    is_cinema = payload.idea_kind == "cinema"
    if is_cinema:
        groups = (
            (
                ("Quyết định làm đổi hướng", "Một lựa chọn nhỏ đưa nhân vật từ do dự sang hành động có ý nghĩa.", "Một quyết định lặng lẽ có thể thay đổi cả hành trình.", "Quan sát → dấu hiệu → quyết định → dư âm.", "Mời người xem theo dõi phần tiếp theo của câu chuyện."),
                ("Ký ức nối hai thời điểm", "Một vật thể hoặc địa điểm nối quá khứ và hiện tại qua chi tiết thị giác.", "Một ký ức quay lại đúng lúc để mở ra cách nhìn mới.", "Kỷ niệm → phản chiếu → kết nối → khung kết.", "Gợi người xem chia sẻ ký ức của họ."),
                ("Khoảnh khắc người trong thế giới mới", "Không gian công nghệ rộng lớn đối lập với một khoảnh khắc con người gần gũi.", "Giữa nhịp sống nhanh, điều gì vẫn đáng được giữ lại?", "Thế giới → nhân vật → mâu thuẫn → điểm chạm.", "Mời người xem xem tiếp câu chuyện."),
            ),
            (
                ("Trước bình minh", "Nhân vật đi qua một đêm khó khăn rồi nhìn thấy hướng mới khi ánh sáng xuất hiện.", "Đôi khi bước tiếp theo bắt đầu trước khi ta sẵn sàng.", "Đêm → thử thách → ánh sáng → khởi đầu.", "Mời người xem lưu lại khoảnh khắc này."),
                ("Điều chưa từng nói", "Cảm xúc được kể bằng ánh mắt, bàn tay và khoảng lặng thay vì lời thoại dài.", "Có những điều không cần nói vẫn được hiểu.", "Quan sát → im lặng → dấu hiệu → thấu hiểu.", "Mời người xem suy ngẫm cùng câu chuyện."),
                ("Routine thay đổi", "Một ngày quen thuộc thay đổi sau một hành động nhỏ có chủ đích.", "Điều nhỏ nào có thể làm hôm nay khác đi?", "Lặp lại → gián đoạn → hành động → kết quả.", "Mời người xem thử một thay đổi nhỏ."),
            ),
            (
                ("Dấu hiệu của người lạ", "Một cuộc gặp ngắn để lại manh mối khiến nhân vật nhìn lại mục tiêu.", "Một dấu hiệu nhỏ có thể mở ra một hướng đi mới.", "Gặp gỡ → manh mối → lựa chọn → trở về.", "Mời người xem đón xem phần tiếp theo."),
                ("Hai thế giới trong một khung", "Phản chiếu, cửa kính và khung hình đồng điệu diễn tả một giằng co nội tâm.", "Nếu hai con đường cùng xuất hiện trước mắt, bạn chọn gì?", "Đối chiếu → căng thẳng → lựa chọn → bình yên.", "Mời người xem để lại góc nhìn của họ."),
                ("Hành trình trở về", "Nhân vật trở lại nơi cũ và nhận ra bản thân đã thay đổi.", "Nơi cũ vẫn vậy, nhưng người trở về đã khác.", "Quay lại → chi tiết cũ → nhận ra → khung biểu tượng.", "Mời người xem xem tiếp hành trình."),
            ),
        )
    else:
        groups = (
            (
                ("Vấn đề → giải pháp", "Hook thẳng một trở ngại quen thuộc rồi cho thấy chủ đề như bước chuyển rõ ràng.", "Nếu vấn đề này được giải quyết bằng một bước gọn hơn?", "Hook → vấn đề → demo → kết quả → CTA.", "Mời người xem tìm hiểu cách làm phù hợp."),
                ("POV đời thường", "Một tình huống gần gũi tạo mâu thuẫn ngắn, rồi chuyển thành khoảnh khắc dễ đồng cảm.", "Bạn có từng gặp tình huống này trong ngày bận rộn?", "Tình huống → căng thẳng → thay đổi → lợi ích.", "Mời người xem lưu video để xem lại."),
                ("Chuyển đổi có kiểm soát", "Một before/after có thể review, dùng match cut để làm rõ thay đổi thay vì phóng đại.", "Sự khác biệt nằm ở một thay đổi nhìn thấy được.", "Trước → thao tác → sau → khung hero.", "Mời người xem xem chi tiết phù hợp."),
            ),
            (
                ("Đừng mắc lỗi này", "Mở bằng một sai lầm phổ biến, mô tả ngắn hậu quả rồi đưa hướng xử lý vào.", "Một lỗi nhỏ có thể làm quy trình rối hơn bạn nghĩ.", "Cảnh báo → lỗi → cách làm → kết quả.", "Mời người xem lưu checklist này."),
                ("Ba mẹo nhanh", "Mỗi scene nêu một mẹo gọn để người xem có thể lưu và xem lại.", "Ba bước gọn để bắt đầu ngay hôm nay.", "Hook → mẹo 1 → mẹo 2 → mẹo 3 → CTA.", "Mời người xem lưu video để áp dụng."),
                ("Một ngày có và không có giải pháp", "So sánh nhịp ngày trước/sau bằng cùng một bối cảnh dễ nhận ra.", "Một ngày bận rộn có thể nhẹ hơn như thế nào?", "Trước → đối chiếu → thay đổi → kết quả.", "Mời người xem khám phá thêm."),
            ),
            (
                ("Bí mật phía sau kết quả", "Mở bằng kết quả cuối rồi tua lại các bước tạo ra nó.", "Kết quả gọn gàng này bắt đầu từ đâu?", "Kết quả → tua lại → thao tác → xác nhận.", "Mời người xem xem quy trình đầy đủ."),
                ("Mini story khách hàng", "Một nhân vật gặp vấn đề, thử hướng mới và nhận thay đổi nhỏ nhưng rõ.", "Một thay đổi nhỏ có thể tạo khác biệt trong ngày.", "Nhân vật → vấn đề → thử → kết quả.", "Mời người xem liên hệ khi cần tư vấn phù hợp."),
                ("Product reveal theo cảm xúc", "Ánh sáng, close-up và nhịp kể tiết chế làm chủ đề trở thành một câu chuyện có lý do.", "Không chỉ là một sản phẩm, mà là một khoảnh khắc dễ nhớ.", "Không gian → chi tiết → reveal → CTA mềm.", "Mời người xem tìm hiểu thêm."),
            ),
        )
    return groups[payload.idea_set - 1]


def _video_idea_scene_beats(kind: str) -> tuple[tuple[str, str, str, str], ...]:
    if kind == "cinema":
        return (
            ("Thế giới", "wide establishing", "Mở không gian và nhịp cảm xúc.", "slow dissolve"),
            ("Nhân vật", "close-up có khoảng thở", "Giới thiệu mong muốn hoặc điểm nhìn của nhân vật.", "motivated cut"),
            ("Dấu hiệu", "detail insert", "Đưa chi tiết làm thay đổi cách nhìn.", "match cut"),
            ("Bước ngoặt", "controlled push-in", "Ghi nhận hành động hoặc lựa chọn có ý nghĩa.", "clean cut"),
            ("Dư âm", "over-the-shoulder", "Cho thấy kết quả cảm xúc một cách tiết chế.", "gentle hold"),
            ("Khung kết", "symbolic hero frame", "Để lại một hình ảnh kết có thể review.", "fade to neutral"),
        )
    return (
        ("Hook", "close-up rõ điểm nhìn", "Mở bằng tình huống hoặc lợi ích dễ nhận ra.", "clean cut"),
        ("Bối cảnh", "wide context", "Cho thấy vấn đề hoặc nhịp sống liên quan.", "motivated cut"),
        ("Phát hiện", "over-the-shoulder", "Đưa chủ đề vào như một hướng xử lý có thể hiểu.", "match cut"),
        ("Demo", "stable detail / slow push-in", "Mô tả thao tác hoặc cơ chế ở mức biên tập.", "clean settle"),
        ("Kết quả", "before-after comparison", "Nêu kết quả cần được tự kiểm tra trước khi dùng ngoài.", "gentle hold"),
        ("CTA", "calm hero frame", "Đặt lời mời hành động không ép buộc.", "fade to neutral"),
    )


def _compose_video_idea_planner(payload: VideoIdeaPlannerRequest) -> dict[str, Any]:
    concepts = []
    for index, (title, premise, hook, story_structure, cta) in enumerate(_video_idea_concept_templates(payload), start=1):
        concepts.append({"index": index, "title": title, "premise": premise, "hook": hook, "story_structure": story_structure, "cta": cta})
    selected = concepts[payload.idea_choice - 1]
    platform = VIDEO_IDEA_PLANNER_PLATFORMS[payload.platform]
    beats = _video_idea_scene_beats(payload.idea_kind)
    scenes: list[dict[str, Any]] = []
    for index, (title, camera, narration, transition) in enumerate(beats, start=1):
        start = (index - 1) * payload.duration_seconds // len(beats)
        end = index * payload.duration_seconds // len(beats)
        visual = (
            f"{payload.topic}; bối cảnh {payload.context}; hướng '{selected['title']}'. "
            f"{selected['premise']} Scene {index} ưu tiên bố cục rõ, chủ thể nhất quán và khoảng trống an toàn cho biên tập."
        )
        image_prompt = (
            f"Original editorial image direction for {payload.topic}, {payload.context} context, {title.lower()}, "
            f"consistent subject, {camera}, reviewable composition, no watermark, no readable fabricated text."
        )
        video_prompt = (
            f"Original video direction for {payload.topic}: {title.lower()}, {camera}, controlled natural movement, "
            f"stable identity/product, motivated transition, no invented claims or readable fabricated text."
        )
        scenes.append(
            {
                "index": index,
                "start_seconds": start,
                "end_seconds": end,
                "title": title,
                "visual_direction": visual,
                "camera": camera,
                "narration": narration,
                "image_prompt": image_prompt,
                "video_prompt": video_prompt,
                "audio_direction": "Nhịp âm thanh chỉ là note biên tập: ambient hoặc pulse nhẹ, không tạo audio.",
                "transition": transition,
            }
        )
    title_prefix = "Cinematic Story Idea" if payload.idea_kind == "cinema" else "Video Idea"
    custom_context = f" Brief tùy chỉnh: {payload.custom_brief}" if payload.custom_brief else ""
    result = {
        "title": f"{title_prefix}: {payload.topic}",
        "idea_kind": payload.idea_kind,
        "product_type": payload.product_type,
        "platform": payload.platform,
        "aspect_ratio": platform["aspect_ratio"],
        "goal": payload.goal,
        "context": payload.context,
        "topic": payload.topic,
        "audience": payload.audience,
        "language": payload.language,
        "duration_seconds": payload.duration_seconds,
        "idea_set": payload.idea_set,
        "selected_concept": selected,
        "concepts": concepts,
        "scenes": scenes,
        "caption": f"{selected['hook']} {selected['cta']}{custom_context}",
        "hashtags": ["#TOANAAS", "#VideoIdea", "#ContentPlanning", f"#{payload.platform.title().replace('_', '')}"],
        "review_before_use": [
            "Tự kiểm tra claim, thông tin sản phẩm/dịch vụ và bằng chứng trước khi dùng ở kênh bên ngoài.",
            "Chỉ dùng chủ đề, thương hiệu, hình ảnh, giọng nói và nguồn tư liệu mà bạn có quyền sử dụng.",
            "Plan này là direction biên tập; rà soát consent, nhận diện và nội dung hiển thị trước bất kỳ runtime riêng nào.",
        ],
    }
    return VideoIdeaPlannerResult.model_validate(result).model_dump()


def _video_idea_plan_format(kind: str, product_type: str) -> str:
    if kind == "cinema":
        return "campaign"
    if product_type in {"physical", "affiliate"}:
        return "product_demo"
    if kind == "custom":
        return "custom"
    return "short_form"


def _video_idea_to_video_plan(
    payload: VideoIdeaPlannerPlanSaveRequest,
    planner: dict[str, Any],
) -> tuple[PlanPayload, list[ScenePayload]]:
    result = VideoIdeaPlannerResult.model_validate(planner)
    plan = PlanPayload.model_validate(
        {
            "title": result.title,
            "format": _video_idea_plan_format(result.idea_kind, result.product_type),
            "language": result.language,
            "aspect_ratio": result.aspect_ratio,
            "target_duration_seconds": result.duration_seconds,
            "objective": f"{result.goal}: {result.selected_concept.premise}",
            "audience": result.audience,
            "brief": "\n".join(
                (
                    "Private, editable Web-native Video Idea Plan rebuilt on the server.",
                    f"Idea kind: {result.idea_kind}; product type: {result.product_type}; platform: {result.platform}.",
                    f"Selected concept: {result.selected_concept.title}. {result.selected_concept.story_structure}",
                    "Saving this plan does not create a Telegram pending state, provider request, media, job, payment, asset, publish action or delivery.",
                )
            ),
            "tags": [
                "video-idea-planner",
                f"kind-{result.idea_kind}",
                f"platform-{result.platform}",
                f"goal-{result.goal}",
            ],
            "project_id": None,
        }
    )
    scenes: list[ScenePayload] = []
    for scene in result.scenes:
        scenes.append(
            ScenePayload.model_validate(
                {
                    "title": f"Scene {scene.index} — {scene.title}",
                    "scene_type": _storyboard_composer_scene_type(ordinal=scene.index, total=len(result.scenes)),
                    "duration_seconds": scene.end_seconds - scene.start_seconds,
                    "visual_direction": scene.visual_direction,
                    "narration": scene.narration,
                    "on_screen_text": "",
                    "shot_notes": "\n".join(
                        (
                            f"Planner timing: {scene.start_seconds}s–{scene.end_seconds}s.",
                            f"Camera: {scene.camera}",
                            f"Image direction: {scene.image_prompt}",
                            f"Video direction: {scene.video_prompt}",
                            f"Audio note: {scene.audio_direction}",
                            "No media, preview, provider, job, payment or delivery was created.",
                        )
                    ),
                    "transition": scene.transition,
                    "tags": ["video-idea-planner", f"scene-{scene.index}", f"kind-{result.idea_kind}"],
                }
            )
        )
    return plan, scenes


@router.post("/tools/video-idea-planner")
async def compose_video_idea_planner(
    payload: VideoIdeaPlannerRequest,
    account: dict = Depends(require_csrf),
):
    """Return Bot-derived editorial ideas without creating an execution flow."""

    _require_enabled()
    del account
    guarded = _video_idea_guard(_cinematic_ad_marker(payload.topic, payload.audience, payload.custom_brief))
    if guarded:
        return guarded
    planner = _compose_video_idea_planner(payload)
    return envelope(
        True,
        "Đã tạo ba hướng Video Idea và storyboard text để review. Không có Telegram state, Bot/bridge, provider, media, preview, output, job, thanh toán hoặc publish nào được tạo.",
        data={"planner": planner, **_video_idea_boundary()},
        status_name="draft",
    )


@router.post("/tools/video-idea-planner/save")
async def save_video_idea_planner_to_video_plan(
    payload: VideoIdeaPlannerPlanSaveRequest,
    request: Request,
    account: dict = Depends(require_csrf),
):
    """Save only a server-recomputed private Video Plan from original choices."""

    _require_enabled()
    guarded = _video_idea_guard(_cinematic_ad_marker(payload.topic, payload.audience, payload.custom_brief), saving=True)
    if guarded:
        return guarded
    account_id = str(account["id"])
    fingerprint = _fingerprint({"operation": "video-idea-planner-save-video-plan", **payload.model_dump(exclude={"idempotency_key"})})

    def operation(conn: Any) -> dict[str, Any]:
        planner = _compose_video_idea_planner(payload)
        plan_payload, scene_payloads = _video_idea_to_video_plan(payload, planner)
        count = conn.execute(
            "SELECT COUNT(*) FROM web_video_plans WHERE account_id=? AND lifecycle<>'archived'",
            (account_id,),
        ).fetchone()
        if int(count[0] or 0) >= MAX_PLANS_PER_ACCOUNT:
            return envelope(
                False,
                "Video Production Studio đã đạt giới hạn plan đang hoạt động.",
                data={"destination": "video_plan", **_video_idea_plan_save_boundary(draft_recomputed_on_server=True, web_video_plan_persisted=False)},
                status_name="guarded",
                error_code="WEB_VIDEO_PLAN_LIMIT",
            )
        if len(scene_payloads) != 6:
            raise HTTPException(status_code=422, detail="Video Idea Planner phải tạo đúng sáu scene để lưu Video Plan")
        plan_id = str(uuid.uuid4())
        now = utc_now()
        plan_snapshot = _plan_snapshot(plan_payload, lifecycle="draft")
        _insert_plan(conn, plan_id=plan_id, account_id=account_id, snapshot=plan_snapshot, revision=1, now=now)
        _insert_plan_version(conn, plan_id=plan_id, account_id=account_id, revision=1, snapshot=plan_snapshot, now=now)
        _event(conn, account_id=account_id, plan_id=plan_id, action="plan_created", revision=1)
        for ordinal, scene_payload in enumerate(scene_payloads, start=1):
            scene_id = str(uuid.uuid4())
            scene_snapshot = _scene_snapshot(scene_payload, state="active")
            _insert_scene(conn, scene_id=scene_id, plan_id=plan_id, account_id=account_id, ordinal=ordinal, snapshot=scene_snapshot, revision=1, now=now)
            _insert_scene_version(conn, scene_id=scene_id, account_id=account_id, revision=1, snapshot=scene_snapshot, now=now)
            _event(conn, account_id=account_id, plan_id=plan_id, scene_id=scene_id, action="scene_created", revision=1)
        _audit(
            conn,
            request=request,
            account=account,
            action="web.video.idea_planner.save_plan",
            target=plan_id,
            detail="server-recomputed Bot-derived video idea saved as web-owned draft video plan",
        )
        return envelope(
            True,
            "Đã lưu Video Idea thành Video Plan Draft riêng tư. Chưa có Telegram state, Bot/provider, media, job, thanh toán, approval, publish hoặc giao hàng.",
            data={"_video_idea_planner_plan_save": True, "plan": {"id": plan_id, "revision": 1, "state": "draft"}, "scene_count": len(scene_payloads)},
            status_name="draft",
        )

    return _idempotent(
        f"web-video-studio:{account_id}:video-idea-planner:save-plan",
        account_id,
        payload.idempotency_key,
        fingerprint,
        operation,
    )


# Bot `longvideo` is a planning conversation (topic → duration → style →
# structure → roadmap).  The Web version deliberately preserves only that
# editable editorial grammar.  It does not import the Bot's in-memory plan or
# long_video_projects tables, and it never calls a media/provider/billing path.
LONG_FORM_ROADMAP_TOPICS = frozenset({"sales", "education", "story", "custom"})
LONG_FORM_ROADMAP_STYLES = frozenset({"professional", "viral", "cinematic", "custom"})
LONG_FORM_ROADMAP_STRUCTURES = frozenset({"guided", "chapters", "segments", "scenes", "custom"})
LONG_FORM_ROADMAP_LANGUAGES = frozenset({"vi", "en"})
LONG_FORM_ROADMAP_PLATFORMS = {
    "youtube": {"label": "YouTube", "aspect_ratio": "16:9"},
    "facebook": {"label": "Facebook / Watch", "aspect_ratio": "16:9"},
    "course": {"label": "Khoá học / LMS", "aspect_ratio": "16:9"},
    "podcast": {"label": "Podcast có hình", "aspect_ratio": "16:9"},
    "vertical": {"label": "Bản dọc chia đoạn", "aspect_ratio": "9:16"},
    "custom": {"label": "Kênh riêng", "aspect_ratio": "custom"},
}


def _long_form_roadmap_code(value: Any, *, label: str, allowed: frozenset[str] | set[str]) -> str:
    normalized = _planner_line(value, label=label, minimum=1, maximum=64).lower()
    if normalized not in allowed:
        raise ValueError(f"{label} không hợp lệ")
    return normalized


def _long_form_roadmap_text(value: Any, *, label: str, minimum: int, maximum: int, allow_empty: bool = False) -> str:
    return _planner_line(value, label=label, minimum=minimum, maximum=maximum, allow_empty=allow_empty)


def _long_form_roadmap_boundary() -> dict[str, Any]:
    """Exact no-execution boundary for a temporary long-form roadmap."""

    return {
        "execution": "web_native_deterministic_long_form_roadmap_only",
        "input_persisted": False,
        "telegram_state_changed": False,
        "bot_called": False,
        "bridge_called": False,
        "source_media_inspected": False,
        "provider_called": False,
        "image_created": False,
        "video_created": False,
        "audio_created": False,
        "preview_created": False,
        "output_created": False,
        "job_created": False,
        "payment_started": False,
        "wallet_mutated": False,
        "asset_saved": False,
        "publish_action_created": False,
        "fact_checked": False,
        "rights_verified": False,
    }


def _long_form_roadmap_plan_save_boundary(
    *,
    draft_recomputed_on_server: bool = True,
    web_video_plan_persisted: bool = True,
) -> dict[str, Any]:
    """Content-free receipt boundary for the explicit Web Plan handoff."""

    return {
        "execution": "web_native_video_plan_server_recomputed",
        "draft_recomputed_on_server": bool(draft_recomputed_on_server),
        "web_video_plan_persisted": bool(web_video_plan_persisted),
        "browser_result_persisted": False,
        "pending_bot_save_created": False,
        "telegram_state_changed": False,
        "bot_called": False,
        "bridge_called": False,
        "source_media_inspected": False,
        "media_uploads": False,
        "provider_called": False,
        "image_created": False,
        "video_created": False,
        "audio_created": False,
        "preview_created": False,
        "output_created": False,
        "job_created": False,
        "wallet_mutated": False,
        "payment_started": False,
        "asset_saved": False,
        "publish_action_created": False,
        "delivery_created": False,
        "approval_created": False,
        "plan_approved": False,
        "plan_locked": False,
        "generation_started": False,
        "fact_checked": False,
        "rights_verified": False,
    }


def _long_form_roadmap_guard(marker: str, *, saving: bool = False) -> dict[str, Any] | None:
    if not marker:
        return None
    if marker == "claim":
        message = "Nội dung có tuyên bố cần nguồn hoặc kiểm chứng. Hãy viết lại theo hướng có thể review trước khi lập roadmap."
        code = "WEB_LONG_FORM_ROADMAP_CLAIM_GUARD"
    else:
        message = "Nội dung cần được viết lại theo hướng nguyên bản, không mô phỏng người thật, người nổi tiếng hoặc phong cách cụ thể."
        code = "WEB_LONG_FORM_ROADMAP_ORIGINALITY_GUARD"
    data: dict[str, Any] = (
        {"destination": "video_plan", **_long_form_roadmap_plan_save_boundary(draft_recomputed_on_server=False, web_video_plan_persisted=False)}
        if saving else _long_form_roadmap_boundary()
    )
    return envelope(False, message, data=data, status_name="guarded", error_code=code)


class LongFormRoadmapRequest(BaseModel):
    """Original bounded choices copied from Bot's long-video planning flow."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, strict=True)

    topic_category: StrictStr
    topic: StrictStr
    audience: StrictStr
    duration_minutes: StrictInt = Field(ge=3, le=120)
    style: StrictStr
    custom_style: StrictStr = ""
    structure_mode: StrictStr
    custom_structure: StrictStr = ""
    platform: StrictStr
    language: StrictStr

    @field_validator("topic_category")
    @classmethod
    def validate_topic_category(cls, value: StrictStr) -> str:
        return _long_form_roadmap_code(value, label="Nhóm chủ đề video dài", allowed=LONG_FORM_ROADMAP_TOPICS)

    @field_validator("style")
    @classmethod
    def validate_style(cls, value: StrictStr) -> str:
        return _long_form_roadmap_code(value, label="Phong cách video dài", allowed=LONG_FORM_ROADMAP_STYLES)

    @field_validator("structure_mode")
    @classmethod
    def validate_structure(cls, value: StrictStr) -> str:
        return _long_form_roadmap_code(value, label="Cấu trúc video dài", allowed=LONG_FORM_ROADMAP_STRUCTURES)

    @field_validator("platform")
    @classmethod
    def validate_platform(cls, value: StrictStr) -> str:
        return _long_form_roadmap_code(value, label="Nền tảng video dài", allowed=set(LONG_FORM_ROADMAP_PLATFORMS))

    @field_validator("language")
    @classmethod
    def validate_language(cls, value: StrictStr) -> str:
        return _long_form_roadmap_code(value, label="Ngôn ngữ video dài", allowed=LONG_FORM_ROADMAP_LANGUAGES)

    @field_validator("topic")
    @classmethod
    def validate_topic(cls, value: StrictStr) -> str:
        return _long_form_roadmap_text(value, label="Chủ đề video dài", minimum=2, maximum=500)

    @field_validator("audience")
    @classmethod
    def validate_audience(cls, value: StrictStr) -> str:
        return _long_form_roadmap_text(value, label="Khán giả video dài", minimum=2, maximum=500)

    @field_validator("custom_style")
    @classmethod
    def validate_custom_style(cls, value: StrictStr) -> str:
        return _long_form_roadmap_text(value, label="Phong cách tùy chỉnh", minimum=0, maximum=320, allow_empty=True)

    @field_validator("custom_structure")
    @classmethod
    def validate_custom_structure(cls, value: StrictStr) -> str:
        return _long_form_roadmap_text(value, label="Cấu trúc tùy chỉnh", minimum=0, maximum=180, allow_empty=True)

    def model_post_init(self, __context: Any) -> None:
        if self.style == "custom" and not self.custom_style:
            raise ValueError("Phong cách tùy chỉnh cần mô tả phong cách")
        if self.structure_mode == "custom" and not self.custom_structure:
            raise ValueError("Cấu trúc tùy chỉnh cần mô tả cấu trúc")


class LongFormRoadmapPlanSaveRequest(LongFormRoadmapRequest):
    """Only bounded original choices may cross the durable-plan boundary."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, strict=True)

    destination: StrictStr
    idempotency_key: StrictStr

    @field_validator("destination")
    @classmethod
    def validate_destination(cls, value: StrictStr) -> str:
        return _long_form_roadmap_code(value, label="Nơi lưu roadmap", allowed={"video_plan"})

    @field_validator("idempotency_key")
    @classmethod
    def validate_idempotency_key(cls, value: StrictStr) -> str:
        return _idempotency_key(value)


class LongFormRoadmapChapter(BaseModel):
    """One editable roadmap chapter, never an execution or delivery receipt."""

    model_config = ConfigDict(extra="forbid")

    index: StrictInt = Field(ge=1, le=30)
    start_seconds: StrictInt = Field(ge=0, le=7200)
    end_seconds: StrictInt = Field(ge=1, le=7200)
    title: str
    objective: str
    hook: str
    script_beat: str
    visual_direction: str
    image_prompt: str
    video_prompt: str
    voice_direction: str
    music_sfx_direction: str
    transition: str

    @field_validator(
        "title", "objective", "hook", "script_beat", "visual_direction", "image_prompt", "video_prompt",
        "voice_direction", "music_sfx_direction", "transition",
    )
    @classmethod
    def validate_text(cls, value: str) -> str:
        return _long_form_roadmap_text(value, label="Chương roadmap video dài", minimum=2, maximum=2_400)

    def model_post_init(self, __context: Any) -> None:
        if self.end_seconds <= self.start_seconds:
            raise ValueError("Mốc kết thúc chương roadmap phải lớn hơn mốc bắt đầu")


class LongFormRoadmapResult(BaseModel):
    """Exact browser-safe roadmap response with a strict planning-only shape."""

    model_config = ConfigDict(extra="forbid")

    title: str
    topic_category: str
    topic: str
    audience: str
    duration_minutes: StrictInt
    target_duration_seconds: StrictInt
    style: str
    style_label: str
    structure_mode: str
    structure: str
    platform: str
    aspect_ratio: str
    language: str
    chapter_count: StrictInt
    outline: list[str] = Field(min_length=4, max_length=7)
    character_bible: list[str] = Field(min_length=4, max_length=7)
    chapters: list[LongFormRoadmapChapter] = Field(min_length=3, max_length=30)
    audio_direction: str
    caption: str
    cta: str
    review_before_use: list[str] = Field(min_length=2, max_length=7)

    @field_validator("title", "topic", "audience", "style_label", "structure", "audio_direction", "caption", "cta")
    @classmethod
    def validate_text(cls, value: str) -> str:
        return _long_form_roadmap_text(value, label="Kết quả roadmap video dài", minimum=2, maximum=2_400)

    @field_validator("topic_category")
    @classmethod
    def validate_result_category(cls, value: str) -> str:
        return _long_form_roadmap_code(value, label="Nhóm roadmap", allowed=LONG_FORM_ROADMAP_TOPICS)

    @field_validator("style")
    @classmethod
    def validate_result_style(cls, value: str) -> str:
        return _long_form_roadmap_code(value, label="Phong cách roadmap", allowed=LONG_FORM_ROADMAP_STYLES)

    @field_validator("structure_mode")
    @classmethod
    def validate_result_structure(cls, value: str) -> str:
        return _long_form_roadmap_code(value, label="Cấu trúc roadmap", allowed=LONG_FORM_ROADMAP_STRUCTURES)

    @field_validator("platform")
    @classmethod
    def validate_result_platform(cls, value: str) -> str:
        return _long_form_roadmap_code(value, label="Nền tảng roadmap", allowed=set(LONG_FORM_ROADMAP_PLATFORMS))

    @field_validator("language")
    @classmethod
    def validate_result_language(cls, value: str) -> str:
        return _long_form_roadmap_code(value, label="Ngôn ngữ roadmap", allowed=LONG_FORM_ROADMAP_LANGUAGES)

    @field_validator("aspect_ratio")
    @classmethod
    def validate_ratio(cls, value: str) -> str:
        return _line(value, label="Tỷ lệ long-form roadmap", minimum=3, maximum=8)

    @field_validator("outline", "character_bible", "review_before_use")
    @classmethod
    def validate_lists(cls, value: list[str]) -> list[str]:
        return [_long_form_roadmap_text(item, label="Danh sách roadmap video dài", minimum=2, maximum=500) for item in value]

    def model_post_init(self, __context: Any) -> None:
        if not 3 <= self.duration_minutes <= 120 or self.target_duration_seconds != self.duration_minutes * 60:
            raise ValueError("Thời lượng roadmap video dài không hợp lệ")
        if self.aspect_ratio not in ASPECT_RATIOS:
            raise ValueError("Tỷ lệ roadmap video dài không hợp lệ")
        if self.chapter_count != len(self.chapters) or not 3 <= self.chapter_count <= 30:
            raise ValueError("Số chương roadmap video dài không hợp lệ")
        if [chapter.index for chapter in self.chapters] != list(range(1, self.chapter_count + 1)):
            raise ValueError("Chương roadmap cần liên tiếp từ 1")
        previous_end = 0
        for chapter in self.chapters:
            if chapter.start_seconds != previous_end:
                raise ValueError("Timeline chương roadmap phải liên tiếp")
            if chapter.end_seconds - chapter.start_seconds > 1800:
                raise ValueError("Một chương roadmap không thể dài hơn 30 phút")
            previous_end = chapter.end_seconds
        if previous_end != self.target_duration_seconds:
            raise ValueError("Timeline roadmap phải kết thúc đúng thời lượng đã chọn")


def _long_form_style_label(payload: LongFormRoadmapRequest) -> str:
    if payload.style == "custom":
        return payload.custom_style
    labels_vi = {
        "professional": "chuyên nghiệp, rõ ràng và có cấu trúc",
        "viral": "nhịp nhanh, hook rõ và dễ chia đoạn",
        "cinematic": "cinematic tiết chế, giàu nhịp cảm xúc",
    }
    labels_en = {
        "professional": "professional, clear and structured",
        "viral": "fast-paced, hook-led and easy to segment",
        "cinematic": "restrained cinematic storytelling with emotional pacing",
    }
    return (labels_vi if payload.language == "vi" else labels_en)[payload.style]


def _long_form_default_chapter_count(duration_minutes: int) -> int:
    if duration_minutes <= 3:
        return 3
    if duration_minutes <= 5:
        return 5
    if duration_minutes <= 10:
        return 5
    if duration_minutes <= 30:
        return 6
    if duration_minutes <= 60:
        return 12
    return min(24, max(12, duration_minutes // 5))


def _long_form_structure(payload: LongFormRoadmapRequest) -> tuple[str, int]:
    """Convert Bot's duration-dependent structure choices to bounded chapters."""

    duration = payload.duration_minutes
    guided = _long_form_default_chapter_count(duration)
    if payload.structure_mode == "guided":
        count = guided
        label = f"{count} chương theo nhịp {max(1, duration // count)} phút"
    elif payload.structure_mode == "chapters":
        count = guided
        label = f"{count} chương x khoảng {max(1, duration // count)} phút"
    elif payload.structure_mode == "segments":
        count = min(30, max(3, duration * 2))
        label = f"{count} đoạn biên tập dễ cắt"
    elif payload.structure_mode == "scenes":
        count = min(30, max(3, duration))
        label = f"{count} cảnh roadmap có thể review"
    else:
        label = payload.custom_structure
        match = re.search(r"\d+", label)
        count = int(match.group(0)) if match else guided
    # A private Web Video Plan uses one editable scene per chapter. Respect
    # its 30-minute per-scene limit, even when the Bot's custom duration text
    # asks for fewer chapters than can be represented safely.
    minimum_for_scene_limit = (duration * 60 + 1799) // 1800
    count = min(30, max(3, minimum_for_scene_limit, count))
    if payload.language == "en":
        if payload.structure_mode == "guided":
            label = f"{count} chapters paced at about {max(1, duration // count)} minutes"
        elif payload.structure_mode == "chapters":
            label = f"{count} chapters × about {max(1, duration // count)} minutes"
        elif payload.structure_mode == "segments":
            label = f"{count} editable production segments"
        elif payload.structure_mode == "scenes":
            label = f"{count} reviewable roadmap scenes"
    return _long_form_roadmap_text(label, label="Cấu trúc roadmap", minimum=2, maximum=180), count


def _long_form_phase(index: int, total: int, language: str) -> tuple[str, str, str, str]:
    if language == "en":
        if index == 1:
            return ("Hook and promise", "Open with a question, contrast or visible desired outcome.", "clean motivated cut", "Establish a reason to keep watching before explanation begins.")
        if index == total:
            return ("Recap and next step", "Summarize the usable point and invite one calm next action.", "soft resolve", "End with a reusable recap and non-coercive CTA.")
        return (f"Core chapter {index - 1}", "Advance one clear teaching, demo or story beat.", "chapter bridge", "Connect the previous insight to the next one without inventing proof.")
    if index == 1:
        return ("Hook và lời hứa", "Mở bằng câu hỏi, đối chiếu hoặc kết quả có thể quan sát.", "clean motivated cut", "Tạo lý do xem tiếp trước khi đi vào phần giải thích.")
    if index == total:
        return ("Recap và bước tiếp", "Tóm tắt điểm có thể áp dụng rồi mời một hành động nhẹ.", "soft resolve", "Kết bằng recap có thể dùng lại và CTA không ép buộc.")
    return (f"Chương nội dung {index - 1}", "Phát triển một ý chính, demo hoặc nhịp câu chuyện rõ ràng.", "chapter bridge", "Nối insight trước với phần sau mà không tự tạo bằng chứng.")


def _compose_long_form_roadmap(payload: LongFormRoadmapRequest) -> dict[str, Any]:
    structure, chapter_count = _long_form_structure(payload)
    target_seconds = payload.duration_minutes * 60
    style_label = _long_form_style_label(payload)
    platform = LONG_FORM_ROADMAP_PLATFORMS[payload.platform]
    if payload.language == "en":
        outline = [
            f"Hook and promise: state the viewer problem or desired outcome around {payload.topic}.",
            f"Context: connect the topic to {payload.audience} without making unverified claims.",
            f"Core chapters: follow {structure}; each chapter carries one editable teaching, demo or story beat.",
            "Proof and recap: mark examples as review items, not verified evidence or completed results.",
            "CTA: offer a clear, non-coercive next step that matches the topic.",
        ]
        character_bible = [
            f"Main subject/host: consistent editorial point of view for {payload.topic}.",
            "Continuity: keep wardrobe, palette, silhouette and terminology stable across chapters.",
            f"Performance: {style_label}; controlled gestures and a clear emotional through-line.",
            "Voice: consistent pace, pronunciation and pauses across every chapter.",
            "Guard: use only people, brands, voices and references you are authorized to use; do not imitate identifiable people.",
        ]
        title = f"Long-form Roadmap: {payload.topic}"
        audio_direction = "Voice is clear and paced for comprehension; music/SFX remain editorial notes only, never generated audio."
        caption = f"A long-form roadmap for {payload.topic}: one clear idea per chapter, then a reviewable next step."
        cta = "Invite the viewer to save the roadmap, review the relevant detail, or take one appropriate next step."
        review = [
            "Review every claim, comparison, example and supporting source before publishing outside this planning surface.",
            "Use only material, identity, voice, logo and brand references that you have rights and consent to use.",
            "This roadmap is editorial text only. A separate approved runtime is required for any media, provider, job, billing or delivery action.",
        ]
    else:
        outline = [
            f"Hook và lời hứa: nêu vấn đề hoặc kết quả mong muốn xoay quanh {payload.topic}.",
            f"Ngữ cảnh: nối chủ đề với {payload.audience} mà không đưa claim chưa kiểm chứng.",
            f"Các chương chính: đi theo {structure}; mỗi chương có một insight, demo hoặc nhịp kể chuyện có thể sửa.",
            "Ví dụ và recap: đánh dấu ví dụ là mục cần review, không coi là bằng chứng đã xác minh hoặc kết quả đã có.",
            "CTA: mời một bước tiếp theo rõ ràng, nhẹ nhàng và đúng chủ đề.",
        ]
        character_bible = [
            f"Chủ thể/host chính: điểm nhìn biên tập nhất quán cho {payload.topic}.",
            "Continuity: giữ trang phục, bảng màu, silhouette và thuật ngữ ổn định giữa các chương.",
            f"Diễn xuất: {style_label}; cử chỉ có kiểm soát và mạch cảm xúc rõ.",
            "Giọng đọc: tốc độ, cách phát âm và khoảng nghỉ nhất quán xuyên suốt roadmap.",
            "Guard: chỉ dùng người, thương hiệu, giọng nói và nguồn tham chiếu có quyền; không mô phỏng người được nhận diện.",
        ]
        title = f"Long-form Roadmap: {payload.topic}"
        audio_direction = "Giọng đọc rõ, nhịp vừa để dễ theo dõi; nhạc/SFX chỉ là note biên tập, không tạo audio."
        caption = f"Lộ trình video dài cho {payload.topic}: mỗi chương một ý rõ, sau đó là bước tiếp theo có thể review."
        cta = "Mời người xem lưu roadmap, xem lại chi tiết liên quan hoặc thực hiện một bước tiếp theo phù hợp."
        review = [
            "Tự kiểm tra mọi claim, so sánh, ví dụ và nguồn hỗ trợ trước khi dùng ở kênh bên ngoài.",
            "Chỉ dùng tư liệu, nhận diện, giọng nói, logo và tham chiếu thương hiệu mà bạn có quyền và consent sử dụng.",
            "Roadmap chỉ là text biên tập. Media, provider, job, thanh toán hoặc delivery phải đi qua runtime riêng đã được phê duyệt.",
        ]
    chapters: list[dict[str, Any]] = []
    for index in range(1, chapter_count + 1):
        start = (index - 1) * target_seconds // chapter_count
        end = index * target_seconds // chapter_count
        phase, objective, transition, narrative_goal = _long_form_phase(index, chapter_count, payload.language)
        if payload.language == "en":
            hook = f"Chapter {index}: what should a viewer understand or notice about {payload.topic} now?"
            script_beat = f"{objective} Explain one point for {payload.audience}, add a clearly labelled example if appropriate, then {narrative_goal.lower()}"
            visual = f"Original editorial direction for {payload.topic}; {phase.lower()}; {style_label}; consistent host/subject, clean framing and safe space for chapter title text."
            image_prompt = f"Original editorial image planning for {payload.topic}, {phase.lower()}, {style_label}, consistent subject, clean composition, no watermark, no fabricated readable text."
            video_prompt = f"Original long-form video planning for {payload.topic}: {phase.lower()}, controlled camera movement, natural cutaway or demo direction, stable subject, clear transition to the next chapter."
            voice = "Confident and clear, medium pace, short pause after the key idea; this is a voice direction only, not TTS or an audio preview."
            music = "Light editorial bed with subtle transition cue; this is direction text only, not generated music or SFX."
        else:
            hook = f"Chương {index}: người xem cần hiểu hoặc nhận ra điều gì về {payload.topic} ở thời điểm này?"
            script_beat = f"{objective} Giải thích một ý cho {payload.audience}, thêm ví dụ được gắn nhãn khi phù hợp, rồi {narrative_goal.lower()}"
            visual = f"Direction biên tập nguyên bản cho {payload.topic}; {phase.lower()}; phong cách {style_label}; chủ thể/host nhất quán, khung hình sạch và chừa khoảng trống cho nhãn chương."
            image_prompt = f"Original editorial image planning for {payload.topic}, {phase.lower()}, {style_label}, consistent subject, clean composition, no watermark, no fabricated readable text."
            video_prompt = f"Original long-form video planning for {payload.topic}: {phase.lower()}, controlled camera movement, natural cutaway or demo direction, stable subject, clear transition to the next chapter."
            voice = "Giọng tự tin, rõ, tốc độ vừa; nghỉ ngắn sau ý chính. Đây chỉ là direction voice, không phải TTS hoặc audio preview."
            music = "Nền âm thanh biên tập nhẹ với cue chuyển chương tinh tế; đây chỉ là direction text, không tạo nhạc hoặc SFX."
        chapters.append(
            {
                "index": index,
                "start_seconds": start,
                "end_seconds": end,
                "title": phase,
                "objective": objective,
                "hook": hook,
                "script_beat": script_beat,
                "visual_direction": visual,
                "image_prompt": image_prompt,
                "video_prompt": video_prompt,
                "voice_direction": voice,
                "music_sfx_direction": music,
                "transition": transition,
            }
        )
    result = {
        "title": title,
        "topic_category": payload.topic_category,
        "topic": payload.topic,
        "audience": payload.audience,
        "duration_minutes": payload.duration_minutes,
        "target_duration_seconds": target_seconds,
        "style": payload.style,
        "style_label": style_label,
        "structure_mode": payload.structure_mode,
        "structure": structure,
        "platform": payload.platform,
        "aspect_ratio": platform["aspect_ratio"],
        "language": payload.language,
        "chapter_count": chapter_count,
        "outline": outline,
        "character_bible": character_bible,
        "chapters": chapters,
        "audio_direction": audio_direction,
        "caption": caption,
        "cta": cta,
        "review_before_use": review,
    }
    return LongFormRoadmapResult.model_validate(result).model_dump()


def _long_form_roadmap_plan_format(category: str) -> str:
    if category == "story":
        return "campaign"
    if category in {"sales", "education"}:
        return "explainer"
    return "custom"


def _long_form_roadmap_to_video_plan(
    payload: LongFormRoadmapPlanSaveRequest,
    roadmap: dict[str, Any],
) -> tuple[PlanPayload, list[ScenePayload]]:
    """Persist only server-recomputed long-form planning text as Web data."""

    result = LongFormRoadmapResult.model_validate(roadmap)
    plan = PlanPayload.model_validate(
        {
            "title": result.title,
            "format": _long_form_roadmap_plan_format(result.topic_category),
            "language": result.language,
            "aspect_ratio": result.aspect_ratio,
            "target_duration_seconds": result.target_duration_seconds,
            "objective": f"Long-form {result.topic_category}: {result.structure}",
            "audience": result.audience,
            "brief": "\n".join(
                (
                    "Private editable Web-native Long-form Video Roadmap rebuilt on the server.",
                    f"Topic category: {result.topic_category}; platform: {result.platform}; style: {result.style}.",
                    f"Structure: {result.structure}; chapters: {result.chapter_count}.",
                    "Saving this plan does not create Telegram/Bot state, a provider request, media, job, payment, asset, publish action or delivery.",
                )
            ),
            "tags": [
                "long-form-roadmap",
                f"topic-{result.topic_category}",
                f"platform-{result.platform}",
                f"style-{result.style}",
            ],
            "project_id": None,
        }
    )
    scenes: list[ScenePayload] = []
    for chapter in result.chapters:
        scenes.append(
            ScenePayload.model_validate(
                {
                    "title": f"Chapter {chapter.index} — {chapter.title}",
                    "scene_type": _storyboard_composer_scene_type(ordinal=chapter.index, total=len(result.chapters)),
                    "duration_seconds": chapter.end_seconds - chapter.start_seconds,
                    "visual_direction": chapter.visual_direction,
                    "narration": chapter.script_beat,
                    "on_screen_text": chapter.title,
                    "shot_notes": "\n".join(
                        (
                            f"Roadmap timing: {chapter.start_seconds}s–{chapter.end_seconds}s.",
                            f"Hook: {chapter.hook}",
                            f"Image direction: {chapter.image_prompt}",
                            f"Video direction: {chapter.video_prompt}",
                            f"Voice direction: {chapter.voice_direction}",
                            f"Music/SFX direction: {chapter.music_sfx_direction}",
                            "No media, preview, provider, job, payment or delivery was created.",
                        )
                    ),
                    "transition": chapter.transition,
                    "tags": ["long-form-roadmap", f"chapter-{chapter.index}", f"topic-{result.topic_category}"],
                }
            )
        )
    return plan, scenes


@router.post("/tools/long-form-roadmap")
async def compose_long_form_roadmap(
    payload: LongFormRoadmapRequest,
    account: dict = Depends(require_csrf),
):
    """Return Bot-derived long-form planning text, never runtime execution."""

    _require_enabled()
    del account
    guarded = _long_form_roadmap_guard(
        _cinematic_ad_marker(payload.topic, payload.audience, payload.custom_style, payload.custom_structure)
    )
    if guarded:
        return guarded
    roadmap = _compose_long_form_roadmap(payload)
    return envelope(
        True,
        "Đã tạo Long-form Video Roadmap để review. Không có Telegram/Bot state, provider, media, preview, output, job, thanh toán, asset hoặc publish nào được tạo.",
        data={"roadmap": roadmap, **_long_form_roadmap_boundary()},
        status_name="draft",
    )


@router.post("/tools/long-form-roadmap/save")
async def save_long_form_roadmap_to_video_plan(
    payload: LongFormRoadmapPlanSaveRequest,
    request: Request,
    account: dict = Depends(require_csrf),
):
    """Save a separate server-recomputed Web Video Plan after confirmation."""

    _require_enabled()
    guarded = _long_form_roadmap_guard(
        _cinematic_ad_marker(payload.topic, payload.audience, payload.custom_style, payload.custom_structure), saving=True
    )
    if guarded:
        return guarded
    account_id = str(account["id"])
    fingerprint = _fingerprint({"operation": "long-form-roadmap-save-video-plan", **payload.model_dump(exclude={"idempotency_key"})})

    def operation(conn: Any) -> dict[str, Any]:
        roadmap = _compose_long_form_roadmap(payload)
        plan_payload, scene_payloads = _long_form_roadmap_to_video_plan(payload, roadmap)
        count = conn.execute(
            "SELECT COUNT(*) FROM web_video_plans WHERE account_id=? AND lifecycle<>'archived'",
            (account_id,),
        ).fetchone()
        if int(count[0] or 0) >= MAX_PLANS_PER_ACCOUNT:
            return envelope(
                False,
                "Video Production Studio đã đạt giới hạn plan đang hoạt động.",
                data={"destination": "video_plan", **_long_form_roadmap_plan_save_boundary(draft_recomputed_on_server=True, web_video_plan_persisted=False)},
                status_name="guarded",
                error_code="WEB_VIDEO_PLAN_LIMIT",
            )
        if not 3 <= len(scene_payloads) <= 30:
            raise HTTPException(status_code=422, detail="Long-form Roadmap cần từ 3 đến 30 chương để lưu Video Plan")
        plan_id = str(uuid.uuid4())
        now = utc_now()
        plan_snapshot = _plan_snapshot(plan_payload, lifecycle="draft")
        _insert_plan(conn, plan_id=plan_id, account_id=account_id, snapshot=plan_snapshot, revision=1, now=now)
        _insert_plan_version(conn, plan_id=plan_id, account_id=account_id, revision=1, snapshot=plan_snapshot, now=now)
        _event(conn, account_id=account_id, plan_id=plan_id, action="plan_created", revision=1)
        for ordinal, scene_payload in enumerate(scene_payloads, start=1):
            scene_id = str(uuid.uuid4())
            scene_snapshot = _scene_snapshot(scene_payload, state="active")
            _insert_scene(conn, scene_id=scene_id, plan_id=plan_id, account_id=account_id, ordinal=ordinal, snapshot=scene_snapshot, revision=1, now=now)
            _insert_scene_version(conn, scene_id=scene_id, account_id=account_id, revision=1, snapshot=scene_snapshot, now=now)
            _event(conn, account_id=account_id, plan_id=plan_id, scene_id=scene_id, action="scene_created", revision=1)
        _audit(
            conn,
            request=request,
            account=account,
            action="web.video.long_form_roadmap.save_plan",
            target=plan_id,
            detail="server-recomputed Bot-derived long-form roadmap saved as web-owned draft video plan",
        )
        return envelope(
            True,
            "Đã lưu Long-form Roadmap thành Video Plan Draft riêng tư. Chưa có Telegram/Bot state, provider, media, job, thanh toán, approval, publish hoặc giao hàng.",
            data={"_long_form_roadmap_plan_save": True, "plan": {"id": plan_id, "revision": 1, "state": "draft"}, "scene_count": len(scene_payloads)},
            status_name="draft",
        )

    return _idempotent(
        f"web-video-studio:{account_id}:long-form-roadmap:save-plan",
        account_id,
        payload.idempotency_key,
        fingerprint,
        operation,
    )


# Bot `selfscene` guides a user through subject → direction → scene → camera
# motion → optional audio guidance.  Its source-video/session and finalisation
# branches remain Telegram-only.  This Web surface carries only the useful
# editorial grammar, with affirmative consent and right-to-use assertions.
SELF_SHOT_SCENE_SUBJECT_KINDS = frozenset({"person", "product", "pet", "custom"})
SELF_SHOT_SCENE_DIRECTIONS = frozenset({"context", "cinematic", "ad", "custom"})
SELF_SHOT_SCENE_MOTIONS = frozenset({"pushin", "orbit", "fastcut", "macro", "handheld", "matchcut", "dolly", "parallax", "snapzoom", "custom"})
SELF_SHOT_SCENE_MUSIC = frozenset({"cinematic", "tech", "viral", "piano", "luxury", "ugc", "corporate", "suspense", "none", "custom"})
SELF_SHOT_SCENE_LANGUAGES = frozenset({"vi", "en"})
SELF_SHOT_SCENE_PLATFORMS = {
    "tiktok": {"label": "TikTok", "aspect_ratio": "9:16"},
    "reels": {"label": "Instagram Reels", "aspect_ratio": "9:16"},
    "shorts": {"label": "YouTube Shorts", "aspect_ratio": "9:16"},
    "marketplace": {"label": "Marketplace / social ad", "aspect_ratio": "1:1"},
    "youtube": {"label": "YouTube", "aspect_ratio": "16:9"},
    "custom": {"label": "Kênh riêng", "aspect_ratio": "custom"},
}


def _self_shot_scene_code(value: Any, *, label: str, allowed: frozenset[str] | set[str]) -> str:
    normalized = _planner_line(value, label=label, minimum=1, maximum=64).lower()
    if normalized not in allowed:
        raise ValueError(f"{label} không hợp lệ")
    return normalized


def _self_shot_scene_text(value: Any, *, label: str, minimum: int, maximum: int, allow_empty: bool = False) -> str:
    return _planner_line(value, label=label, minimum=minimum, maximum=maximum, allow_empty=allow_empty)


def _self_shot_scene_boundary() -> dict[str, Any]:
    """Exact no-execution boundary for a transient self-shot direction pack."""

    return {
        "execution": "web_native_deterministic_self_shot_scene_planner_only",
        "input_persisted": False,
        "telegram_state_changed": False,
        "bot_called": False,
        "bridge_called": False,
        "source_media_inspected": False,
        "provider_called": False,
        "image_created": False,
        "video_created": False,
        "audio_created": False,
        "preview_created": False,
        "output_created": False,
        "job_created": False,
        "payment_started": False,
        "wallet_mutated": False,
        "asset_saved": False,
        "publish_action_created": False,
        "fact_checked": False,
        "rights_verified": False,
    }


def _self_shot_scene_plan_save_boundary(
    *,
    draft_recomputed_on_server: bool = True,
    web_video_plan_persisted: bool = True,
) -> dict[str, Any]:
    """Content-free receipt for the deliberate, owner-scoped Web Plan handoff."""

    return {
        "execution": "web_native_self_shot_scene_video_plan_server_recomputed",
        "draft_recomputed_on_server": bool(draft_recomputed_on_server),
        "web_video_plan_persisted": bool(web_video_plan_persisted),
        "browser_result_persisted": False,
        "pending_bot_save_created": False,
        "telegram_state_changed": False,
        "bot_called": False,
        "bridge_called": False,
        "source_media_inspected": False,
        "media_uploads": False,
        "provider_called": False,
        "image_created": False,
        "video_created": False,
        "audio_created": False,
        "preview_created": False,
        "output_created": False,
        "job_created": False,
        "wallet_mutated": False,
        "payment_started": False,
        "asset_saved": False,
        "publish_action_created": False,
        "delivery_created": False,
        "approval_created": False,
        "plan_approved": False,
        "plan_locked": False,
        "generation_started": False,
        "fact_checked": False,
        "rights_verified": False,
    }


def _self_shot_scene_guard(marker: str, *, saving: bool = False) -> dict[str, Any] | None:
    """Narrow text guard; it never represents consent or rights verification."""

    if not marker:
        return None
    if marker == "claim":
        message = "Mô tả có tuyên bố cần nguồn hoặc kiểm chứng. Hãy viết lại theo hướng có thể review trước khi lập direction."
        code = "WEB_SELF_SHOT_SCENE_CLAIM_GUARD"
    else:
        message = "Yêu cầu cần được viết lại theo hướng nguyên bản, không mô phỏng người thật, người nổi tiếng, danh tính hoặc phong cách cụ thể."
        code = "WEB_SELF_SHOT_SCENE_LIKENESS_GUARD"
    data: dict[str, Any] = (
        {"destination": "video_plan", **_self_shot_scene_plan_save_boundary(draft_recomputed_on_server=False, web_video_plan_persisted=False)}
        if saving else _self_shot_scene_boundary()
    )
    return envelope(False, message, data=data, status_name="guarded", error_code=code)


class SelfShotScenePlannerRequest(BaseModel):
    """Bounded choice set derived from Bot selfscene's text-planning steps.

    The request intentionally contains no media ID, asset ID, URL, upload or
    Telegram reference.  The consent/right fields are customer assertions,
    not a verification result.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, strict=True)

    subject_kind: StrictStr
    subject_description: StrictStr
    preserve_details: StrictStr
    direction_mode: StrictStr
    custom_direction: StrictStr = ""
    target_context: StrictStr
    motion: StrictStr
    custom_motion: StrictStr = ""
    music: StrictStr
    custom_music: StrictStr = ""
    platform: StrictStr
    duration_seconds: StrictInt = Field(ge=5, le=60)
    language: StrictStr
    rights_to_source_confirmed: StrictBool
    person_likeness_consent_confirmed: StrictBool
    brand_or_logo_rights_confirmed: StrictBool
    no_impersonation_or_harm_confirmed: StrictBool

    @field_validator("subject_kind")
    @classmethod
    def validate_subject_kind(cls, value: StrictStr) -> str:
        return _self_shot_scene_code(value, label="Loại chủ thể", allowed=SELF_SHOT_SCENE_SUBJECT_KINDS)

    @field_validator("direction_mode")
    @classmethod
    def validate_direction(cls, value: StrictStr) -> str:
        return _self_shot_scene_code(value, label="Hướng chuyển cảnh", allowed=SELF_SHOT_SCENE_DIRECTIONS)

    @field_validator("motion")
    @classmethod
    def validate_motion(cls, value: StrictStr) -> str:
        return _self_shot_scene_code(value, label="Chuyển động camera", allowed=SELF_SHOT_SCENE_MOTIONS)

    @field_validator("music")
    @classmethod
    def validate_music(cls, value: StrictStr) -> str:
        return _self_shot_scene_code(value, label="Hướng nhạc/SFX", allowed=SELF_SHOT_SCENE_MUSIC)

    @field_validator("platform")
    @classmethod
    def validate_platform(cls, value: StrictStr) -> str:
        return _self_shot_scene_code(value, label="Nền tảng", allowed=set(SELF_SHOT_SCENE_PLATFORMS))

    @field_validator("language")
    @classmethod
    def validate_language(cls, value: StrictStr) -> str:
        return _self_shot_scene_code(value, label="Ngôn ngữ", allowed=SELF_SHOT_SCENE_LANGUAGES)

    @field_validator("subject_description")
    @classmethod
    def validate_subject_description(cls, value: StrictStr) -> str:
        return _self_shot_scene_text(value, label="Mô tả chủ thể", minimum=2, maximum=500)

    @field_validator("preserve_details")
    @classmethod
    def validate_preserve_details(cls, value: StrictStr) -> str:
        return _self_shot_scene_text(value, label="Chi tiết cần giữ", minimum=2, maximum=500)

    @field_validator("target_context")
    @classmethod
    def validate_target_context(cls, value: StrictStr) -> str:
        return _self_shot_scene_text(value, label="Bối cảnh mong muốn", minimum=2, maximum=500)

    @field_validator("custom_direction")
    @classmethod
    def validate_custom_direction(cls, value: StrictStr) -> str:
        return _self_shot_scene_text(value, label="Hướng tùy chỉnh", minimum=0, maximum=320, allow_empty=True)

    @field_validator("custom_motion")
    @classmethod
    def validate_custom_motion(cls, value: StrictStr) -> str:
        return _self_shot_scene_text(value, label="Chuyển động tùy chỉnh", minimum=0, maximum=320, allow_empty=True)

    @field_validator("custom_music")
    @classmethod
    def validate_custom_music(cls, value: StrictStr) -> str:
        return _self_shot_scene_text(value, label="Nhạc/SFX tùy chỉnh", minimum=0, maximum=320, allow_empty=True)

    def model_post_init(self, __context: Any) -> None:
        if not self.rights_to_source_confirmed:
            raise ValueError("Bạn cần xác nhận right-to-use nguồn và transformation được yêu cầu")
        if not self.person_likeness_consent_confirmed:
            raise ValueError("Bạn cần xác nhận consent của mọi người có thể nhận diện được")
        if not self.brand_or_logo_rights_confirmed:
            raise ValueError("Bạn cần xác nhận quyền với thương hiệu, logo và bao bì nếu có")
        if not self.no_impersonation_or_harm_confirmed:
            raise ValueError("Bạn cần xác nhận không mạo danh, lừa dối hoặc tạo nội dung gây hại")
        if self.direction_mode == "custom" and not self.custom_direction:
            raise ValueError("Hướng tùy chỉnh cần mô tả rõ")
        if self.motion == "custom" and not self.custom_motion:
            raise ValueError("Chuyển động tùy chỉnh cần mô tả rõ")
        if self.music == "custom" and not self.custom_music:
            raise ValueError("Nhạc/SFX tùy chỉnh cần mô tả rõ")


class SelfShotScenePlannerSaveRequest(SelfShotScenePlannerRequest):
    """Only original, server-recomputable choices cross the save boundary."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, strict=True)

    destination: StrictStr
    idempotency_key: StrictStr

    @field_validator("destination")
    @classmethod
    def validate_destination(cls, value: StrictStr) -> str:
        return _self_shot_scene_code(value, label="Nơi lưu kế hoạch", allowed={"video_plan"})

    @field_validator("idempotency_key")
    @classmethod
    def validate_idempotency_key(cls, value: StrictStr) -> str:
        return _idempotency_key(value)


class SelfShotScenePlannerResult(BaseModel):
    """Strict, browser-safe text direction pack—not an image/video receipt."""

    model_config = ConfigDict(extra="forbid")

    title: str
    subject_kind: str
    subject_description: str
    preserve_details: str
    direction_mode: str
    direction_label: str
    target_context: str
    motion: str
    motion_label: str
    music: str
    music_label: str
    platform: str
    aspect_ratio: str
    duration_seconds: StrictInt
    language: str
    transformation_brief: str
    video_prompt: str
    keyframe_image_prompt: str
    motion_suggestions: list[str] = Field(min_length=3, max_length=3)
    identity_safety: list[str] = Field(min_length=3, max_length=5)
    finishing_notes: list[str] = Field(min_length=2, max_length=4)
    review_before_use: list[str] = Field(min_length=3, max_length=5)

    @field_validator(
        "title", "subject_description", "preserve_details", "direction_label", "target_context", "motion_label",
        "music_label", "transformation_brief", "video_prompt", "keyframe_image_prompt",
    )
    @classmethod
    def validate_text(cls, value: str) -> str:
        return _self_shot_scene_text(value, label="Kết quả Self-shot Scene", minimum=2, maximum=2_400)

    @field_validator("subject_kind")
    @classmethod
    def validate_result_subject(cls, value: str) -> str:
        return _self_shot_scene_code(value, label="Loại chủ thể kết quả", allowed=SELF_SHOT_SCENE_SUBJECT_KINDS)

    @field_validator("direction_mode")
    @classmethod
    def validate_result_direction(cls, value: str) -> str:
        return _self_shot_scene_code(value, label="Hướng kết quả", allowed=SELF_SHOT_SCENE_DIRECTIONS)

    @field_validator("motion")
    @classmethod
    def validate_result_motion(cls, value: str) -> str:
        return _self_shot_scene_code(value, label="Motion kết quả", allowed=SELF_SHOT_SCENE_MOTIONS)

    @field_validator("music")
    @classmethod
    def validate_result_music(cls, value: str) -> str:
        return _self_shot_scene_code(value, label="Nhạc/SFX kết quả", allowed=SELF_SHOT_SCENE_MUSIC)

    @field_validator("platform")
    @classmethod
    def validate_result_platform(cls, value: str) -> str:
        return _self_shot_scene_code(value, label="Nền tảng kết quả", allowed=set(SELF_SHOT_SCENE_PLATFORMS))

    @field_validator("language")
    @classmethod
    def validate_result_language(cls, value: str) -> str:
        return _self_shot_scene_code(value, label="Ngôn ngữ kết quả", allowed=SELF_SHOT_SCENE_LANGUAGES)

    @field_validator("aspect_ratio")
    @classmethod
    def validate_aspect_ratio(cls, value: str) -> str:
        return _line(value, label="Tỷ lệ khung hình", minimum=3, maximum=8)

    @field_validator("motion_suggestions", "identity_safety", "finishing_notes", "review_before_use")
    @classmethod
    def validate_lists(cls, value: list[str]) -> list[str]:
        return [_self_shot_scene_text(item, label="Danh sách direction Self-shot Scene", minimum=2, maximum=900) for item in value]

    def model_post_init(self, __context: Any) -> None:
        if not 5 <= self.duration_seconds <= 60:
            raise ValueError("Thời lượng direction Self-shot Scene không hợp lệ")
        if self.aspect_ratio not in ASPECT_RATIOS:
            raise ValueError("Tỷ lệ direction Self-shot Scene không hợp lệ")


def _self_shot_scene_direction_label(payload: SelfShotScenePlannerRequest) -> str:
    if payload.direction_mode == "custom":
        return payload.custom_direction
    labels_vi = {
        "context": "đổi bối cảnh xung quanh nhưng giữ chủ thể nhất quán",
        "cinematic": "giữ chủ thể và chuyển thành nhịp cinematic tiết chế",
        "ad": "chuyển thành direction quảng cáo/social ngắn, rõ lợi ích",
    }
    labels_en = {
        "context": "change the surrounding context while keeping the subject consistent",
        "cinematic": "keep the subject and use a restrained cinematic treatment",
        "ad": "turn it into a short social-ad direction with a clear benefit",
    }
    return (labels_vi if payload.language == "vi" else labels_en)[payload.direction_mode]


def _self_shot_scene_motion_label(payload: SelfShotScenePlannerRequest) -> str:
    if payload.motion == "custom":
        return payload.custom_motion
    labels_vi = {
        "pushin": "slow push-in để reveal chủ thể",
        "orbit": "orbit nhẹ quanh chủ thể",
        "fastcut": "fast cuts có nhịp, không bẻ gãy continuity",
        "macro": "macro detail rồi reveal tổng thể",
        "handheld": "handheld tự nhiên, có chủ đích",
        "matchcut": "match cut rõ giữa cảnh gốc và bối cảnh mới",
        "dolly": "dolly-in mượt, ổn định",
        "parallax": "parallax nhẹ, ưu tiên chiều sâu tự nhiên",
        "snapzoom": "snap zoom tiết chế cho nhịp social",
    }
    labels_en = {
        "pushin": "slow push-in to reveal the subject",
        "orbit": "gentle orbit around the subject",
        "fastcut": "paced fast cuts without breaking continuity",
        "macro": "macro detail followed by a wider reveal",
        "handheld": "natural, intentional handheld movement",
        "matchcut": "a clear match cut from source context to new context",
        "dolly": "a stable, smooth dolly-in",
        "parallax": "gentle parallax that preserves natural depth",
        "snapzoom": "restrained snap zoom for social pacing",
    }
    return (labels_vi if payload.language == "vi" else labels_en)[payload.motion]


def _self_shot_scene_music_label(payload: SelfShotScenePlannerRequest) -> str:
    if payload.music == "custom":
        return payload.custom_music
    labels_vi = {
        "cinematic": "nền cinematic nhẹ, không lấn voice",
        "tech": "pulse công nghệ/tương lai tiết chế",
        "viral": "nhịp social nhanh nhưng có khoảng thở",
        "piano": "piano cảm xúc nhẹ",
        "luxury": "ambient luxury tối giản",
        "ugc": "nền UGC ưu tiên voice rõ",
        "corporate": "corporate nhẹ, sáng và rõ",
        "suspense": "build-up before/after tinh tế",
        "none": "không thêm direction nhạc/SFX",
    }
    labels_en = {
        "cinematic": "a light cinematic bed under the voice",
        "tech": "a restrained future/technology pulse",
        "viral": "fast social pacing with room to breathe",
        "piano": "a gentle emotional piano bed",
        "luxury": "minimal ambient luxury direction",
        "ugc": "a UGC direction that prioritizes clear voice",
        "corporate": "a light, bright corporate bed",
        "suspense": "a subtle before/after build-up",
        "none": "no music or SFX direction",
    }
    return (labels_vi if payload.language == "vi" else labels_en)[payload.music]


def _compose_self_shot_scene_planner(payload: SelfShotScenePlannerRequest) -> dict[str, Any]:
    """Rebuild Bot's plan text locally; never touch source media or Bot state."""

    direction = _self_shot_scene_direction_label(payload)
    motion = _self_shot_scene_motion_label(payload)
    music = _self_shot_scene_music_label(payload)
    platform = SELF_SHOT_SCENE_PLATFORMS[payload.platform]
    if payload.language == "en":
        title = f"Self-shot Scene Direction: {payload.subject_description}"
        brief = f"Keep {payload.preserve_details} stable for {payload.subject_description}; {direction}. Move the editorial setting toward {payload.target_context} in a {payload.duration_seconds}-second {platform['label']} direction."
        video_prompt = f"Original text direction only: {payload.subject_description} in {payload.target_context}; preserve {payload.preserve_details}; {direction}; {motion}; clean composition, plausible lighting, stable geometry and identity, no logo distortion, no fabricated events or proof. This is not a generation request."
        keyframe = f"Original keyframe direction only for {payload.subject_description} in {payload.target_context}; preserve {payload.preserve_details}; clean editorial framing, natural perspective, stable identity/product form, no watermark, no fabricated readable text."
        motions = [
            f"Open with a calm, readable view of {payload.subject_description} before changing context.",
            f"Use {motion}, then keep the transition motivated by a visible action or cut point.",
            "End on a stable, reviewable hero frame with room for an optional editorial label.",
        ]
        safety = [
            f"Preserve only the described details: {payload.preserve_details}.",
            "Do not impersonate, alter a recognizable person's identity, or imply consent, endorsement or an event that is not true.",
            "Treat the customer consent and right-to-use acknowledgement as an assertion; it is not verified by this planner.",
        ]
        finishing = [
            f"Audio direction: {music}. It is a note only, not generated music, SFX, voice or preview.",
            "Subtitle, translation, dubbing and final delivery require their own approved workflow.",
        ]
        review = [
            "Confirm that every recognizable person has consent and that you have the right to use the source and requested transformation.",
            "Review brand, music, location, talent, factual claims and disclosure needs before production or publication.",
            "This pack contains text directions only; it did not receive, inspect or transform media and did not create a provider request, job, payment or delivery.",
        ]
    else:
        title = f"Self-shot Scene Direction: {payload.subject_description}"
        brief = f"Giữ {payload.preserve_details} ổn định cho {payload.subject_description}; {direction}. Chuyển bối cảnh biên tập sang {payload.target_context} trong direction {payload.duration_seconds} giây cho {platform['label']}."
        video_prompt = f"Original text direction only: {payload.subject_description} trong {payload.target_context}; giữ {payload.preserve_details}; {direction}; {motion}; bố cục sạch, ánh sáng hợp lý, hình học và nhận diện ổn định, không méo logo, không dựng sự kiện hoặc bằng chứng. Đây không phải yêu cầu tạo video."
        keyframe = f"Original keyframe direction only cho {payload.subject_description} trong {payload.target_context}; giữ {payload.preserve_details}; khung biên tập sạch, phối cảnh tự nhiên, nhận diện/dáng sản phẩm ổn định, không watermark, không tạo chữ đọc được."
        motions = [
            f"Mở bằng khung dễ đọc của {payload.subject_description} trước khi đổi bối cảnh.",
            f"Dùng {motion}, rồi để transition có lý do từ hành động hoặc điểm cắt nhìn thấy được.",
            "Kết ở hero frame ổn định, có thể review, chừa khoảng cho nhãn biên tập nếu cần.",
        ]
        safety = [
            f"Chỉ giữ các chi tiết đã mô tả: {payload.preserve_details}.",
            "Không mạo danh, thay đổi nhận diện người có thể nhận ra, hoặc ngụ ý consent, endorsement hay sự kiện không đúng sự thật.",
            "Consent và right-to-use do khách hàng xác nhận là một assertion; planner này không xác minh các quyền đó.",
        ]
        finishing = [
            f"Direction âm thanh: {music}. Đây chỉ là note, không tạo nhạc, SFX, voice hoặc preview.",
            "Phụ đề, dịch, lồng tiếng và giao hàng cuối phải đi qua workflow riêng đã được phê duyệt.",
        ]
        review = [
            "Xác nhận mọi người có thể nhận diện được đều có consent, và bạn có right-to-use nguồn cùng transformation được yêu cầu.",
            "Review quyền thương hiệu, nhạc, địa điểm, talent, claim thực tế và yêu cầu disclosure trước khi sản xuất hoặc đăng.",
            "Pack này chỉ có text direction; nó không nhận, mở, kiểm tra hay biến đổi media và không tạo provider request, job, thanh toán hoặc delivery.",
        ]
    # A VideoPlan title is capped at 180 characters even though the editable
    # self-shot subject brief can be longer.
    title = _self_shot_scene_text(title, label="Tên Self-shot Scene Direction", minimum=2, maximum=180)
    result = {
        "title": title,
        "subject_kind": payload.subject_kind,
        "subject_description": payload.subject_description,
        "preserve_details": payload.preserve_details,
        "direction_mode": payload.direction_mode,
        "direction_label": direction,
        "target_context": payload.target_context,
        "motion": payload.motion,
        "motion_label": motion,
        "music": payload.music,
        "music_label": music,
        "platform": payload.platform,
        "aspect_ratio": platform["aspect_ratio"],
        "duration_seconds": payload.duration_seconds,
        "language": payload.language,
        "transformation_brief": brief,
        "video_prompt": video_prompt,
        "keyframe_image_prompt": keyframe,
        "motion_suggestions": motions,
        "identity_safety": safety,
        "finishing_notes": finishing,
        "review_before_use": review,
    }
    return SelfShotScenePlannerResult.model_validate(result).model_dump()


def _self_shot_scene_to_video_plan(
    payload: SelfShotScenePlannerSaveRequest,
    direction_pack: dict[str, Any],
) -> tuple[PlanPayload, list[ScenePayload]]:
    """Create one private editable Web plan, never a Bot or runtime record."""

    result = SelfShotScenePlannerResult.model_validate(direction_pack)
    plan = PlanPayload.model_validate(
        {
            "title": result.title,
            "format": "ugc" if result.direction_mode == "ad" else "custom",
            "language": result.language,
            "aspect_ratio": result.aspect_ratio,
            "target_duration_seconds": result.duration_seconds,
            "objective": result.transformation_brief,
            "audience": SELF_SHOT_SCENE_PLATFORMS[result.platform]["label"],
            "brief": "\n".join((
                "Private editable Web-native Self-shot Scene Direction rebuilt on the server.",
                "Customer asserted consent and right-to-use; this is not verified by the Web App.",
                "No source media, Telegram/Bot state, provider, output, job, payment, asset, publish action or delivery was created.",
            )),
            "tags": ["self-shot-scene", f"subject-{result.subject_kind}", f"direction-{result.direction_mode}", f"platform-{result.platform}"],
            "project_id": None,
        }
    )
    shot_notes = "\n".join((
        f"Video direction: {result.video_prompt}",
        f"Keyframe direction: {result.keyframe_image_prompt}",
        f"Identity and safety: {' '.join(result.identity_safety)}",
        f"Finishing: {' '.join(result.finishing_notes)}",
        "No media, preview, provider, job, payment or delivery was created.",
    ))
    if len(shot_notes) > 5_000:
        shot_notes = f"{shot_notes[:4_996].rstrip()}..."
    scene = ScenePayload.model_validate(
        {
            "title": "Self-shot scene direction",
            "scene_type": "product" if result.direction_mode == "ad" else "custom",
            "duration_seconds": result.duration_seconds,
            "visual_direction": result.transformation_brief,
            "narration": " ".join(result.review_before_use[:1]),
            "on_screen_text": "Review direction before production",
            "shot_notes": shot_notes,
            "transition": "review gate before any separate production workflow",
            "tags": ["self-shot-scene", "text-direction", "consent-asserted", "rights-asserted"],
        }
    )
    return plan, [scene]


@router.post("/tools/self-shot-scene-planner")
async def compose_self_shot_scene_planner(
    payload: SelfShotScenePlannerRequest,
    account: dict = Depends(require_csrf),
):
    """Build a consent-gated, Bot-derived text direction pack only."""

    _require_enabled()
    del account
    guarded = _self_shot_scene_guard(
        _cinematic_ad_marker(
            payload.subject_description,
            payload.preserve_details,
            payload.custom_direction,
            payload.target_context,
            payload.custom_motion,
            payload.custom_music,
        )
    )
    if guarded:
        return guarded
    direction_pack = _compose_self_shot_scene_planner(payload)
    return envelope(
        True,
        "Đã tạo Self-shot Scene Direction để review. Đây chỉ là text direction; không có runtime nào được khởi tạo.",
        data={"planner": direction_pack, **_self_shot_scene_boundary()},
        status_name="draft",
    )


@router.post("/tools/self-shot-scene-planner/save")
async def save_self_shot_scene_planner_to_video_plan(
    payload: SelfShotScenePlannerSaveRequest,
    request: Request,
    account: dict = Depends(require_csrf),
):
    """Persist an explicit, server-recomputed private Web Video Plan draft."""

    _require_enabled()
    guarded = _self_shot_scene_guard(
        _cinematic_ad_marker(
            payload.subject_description,
            payload.preserve_details,
            payload.custom_direction,
            payload.target_context,
            payload.custom_motion,
            payload.custom_music,
        ),
        saving=True,
    )
    if guarded:
        return guarded
    account_id = str(account["id"])
    fingerprint = _fingerprint({"operation": "self-shot-scene-planner-save-video-plan", **payload.model_dump(exclude={"idempotency_key"})})

    def operation(conn: Any) -> dict[str, Any]:
        direction_pack = _compose_self_shot_scene_planner(payload)
        plan_payload, scene_payloads = _self_shot_scene_to_video_plan(payload, direction_pack)
        count = conn.execute(
            "SELECT COUNT(*) FROM web_video_plans WHERE account_id=? AND lifecycle<>'archived'",
            (account_id,),
        ).fetchone()
        if int(count[0] or 0) >= MAX_PLANS_PER_ACCOUNT:
            return envelope(
                False,
                "Video Production Studio đã đạt giới hạn plan đang hoạt động.",
                data={"destination": "video_plan", **_self_shot_scene_plan_save_boundary(draft_recomputed_on_server=True, web_video_plan_persisted=False)},
                status_name="guarded",
                error_code="WEB_VIDEO_PLAN_LIMIT",
            )
        plan_id = str(uuid.uuid4())
        now = utc_now()
        plan_snapshot = _plan_snapshot(plan_payload, lifecycle="draft")
        _insert_plan(conn, plan_id=plan_id, account_id=account_id, snapshot=plan_snapshot, revision=1, now=now)
        _insert_plan_version(conn, plan_id=plan_id, account_id=account_id, revision=1, snapshot=plan_snapshot, now=now)
        _event(conn, account_id=account_id, plan_id=plan_id, action="plan_created", revision=1)
        scene_id = str(uuid.uuid4())
        scene_snapshot = _scene_snapshot(scene_payloads[0], state="active")
        _insert_scene(conn, scene_id=scene_id, plan_id=plan_id, account_id=account_id, ordinal=1, snapshot=scene_snapshot, revision=1, now=now)
        _insert_scene_version(conn, scene_id=scene_id, account_id=account_id, revision=1, snapshot=scene_snapshot, now=now)
        _event(conn, account_id=account_id, plan_id=plan_id, scene_id=scene_id, action="scene_created", revision=1)
        _audit(
            conn,
            request=request,
            account=account,
            action="web.video.self_shot_scene.save_plan",
            target=plan_id,
            detail="server-recomputed Bot-derived self-shot scene direction saved as web-owned draft video plan",
        )
        return envelope(
            True,
            "Đã lưu Self-shot Scene Direction thành Video Plan Draft riêng tư. Đây không xác minh consent/quyền sử dụng và không tạo Telegram/Bot state, media, provider, job, thanh toán, publish hoặc giao hàng.",
            data={"_self_shot_scene_planner_plan_save": True, "plan": {"id": plan_id, "revision": 1, "state": "draft"}, "scene_count": 1},
            status_name="draft",
        )

    return _idempotent(
        f"web-video-studio:{account_id}:self-shot-scene-planner:save-plan",
        account_id,
        payload.idempotency_key,
        fingerprint,
        operation,
    )


# Bot Task3D / ``vproduct`` contains a large product menu.  Most entries now
# have a dedicated Web planner, but its two useful text-first products are
# still a distinct workflow: ``script_image_video`` and the stable technical
# identifier ``multi_scene_film`` (presented to customers as an episodic series).
# This Web-native adaptation intentionally compiles only an original planning
# pack.  It does not reuse Bot sessions, prompt vaults, media references,
# package selection, renderer configuration or any paid execution path.
SCRIPT_TO_SCREEN_PROJECT_KINDS = frozenset({"script_image_video", "multi_scene_film"})
SCRIPT_TO_SCREEN_PLATFORMS: dict[str, dict[str, str]] = {
    "tiktok": {"vi": "TikTok", "en": "TikTok"},
    "reels": {"vi": "Instagram Reels", "en": "Instagram Reels"},
    "shorts": {"vi": "YouTube Shorts", "en": "YouTube Shorts"},
    "youtube": {"vi": "YouTube", "en": "YouTube"},
    "facebook": {"vi": "Facebook", "en": "Facebook"},
    "custom": {"vi": "Nền tảng riêng", "en": "Custom platform"},
}
SCRIPT_TO_SCREEN_STYLES: dict[str, dict[str, str]] = {
    "product_demo": {"vi": "Demo sản phẩm rõ ràng", "en": "Clear product demo"},
    "ugc": {"vi": "UGC tự nhiên", "en": "Natural UGC"},
    "cinematic": {"vi": "Điện ảnh có kiểm soát", "en": "Controlled cinematic"},
    "educational": {"vi": "Giải thích dễ hiểu", "en": "Clear educational"},
    "brand_story": {"vi": "Câu chuyện thương hiệu", "en": "Brand story"},
}
SCRIPT_TO_SCREEN_COLORS: dict[str, dict[str, str]] = {
    "warm": {"vi": "ấm áp", "en": "warm"},
    "bright": {"vi": "tươi sáng", "en": "bright"},
    "premium": {"vi": "cao cấp", "en": "premium"},
    "dark_cinematic": {"vi": "trầm điện ảnh", "en": "dark cinematic"},
    "cheerful": {"vi": "vui tươi", "en": "cheerful"},
}
SCRIPT_TO_SCREEN_PACES: dict[str, dict[str, str]] = {
    "slow_emotional": {"vi": "chậm, có cảm xúc", "en": "slow and emotional"},
    "balanced": {"vi": "vừa, dễ theo dõi", "en": "balanced and easy to follow"},
    "fast_dynamic": {"vi": "nhanh, năng động", "en": "fast and dynamic"},
    "ad_rhythm": {"vi": "nhịp quảng cáo", "en": "commercial rhythm"},
}
SCRIPT_TO_SCREEN_IMAGE_PLANS: dict[str, dict[str, str]] = {
    "per_scene": {"vi": "mỗi cảnh một keyframe", "en": "one keyframe per scene"},
    "hero_plus_details": {"vi": "hero frame và các cận cảnh", "en": "hero frame plus detail shots"},
    "single_continuity": {"vi": "một visual canon xuyên suốt", "en": "one continuous visual canon"},
}
SCRIPT_TO_SCREEN_OUTPUT_TARGETS: dict[str, dict[str, str]] = {
    "prompt_pack": {"vi": "Prompt pack để review", "en": "Reviewable prompt pack"},
    "storyboard": {"vi": "Storyboard để biên tập", "en": "Editable storyboard"},
    "video_plan": {"vi": "Video Plan Draft riêng tư", "en": "Private Video Plan Draft"},
}
SCRIPT_TO_SCREEN_LANGUAGES = frozenset({"vi", "en"})


def _script_to_screen_text(
    value: Any,
    *,
    label: str,
    minimum: int,
    maximum: int,
    allow_empty: bool = False,
) -> str:
    return _planner_line(value, label=label, minimum=minimum, maximum=maximum, allow_empty=allow_empty)


def _script_to_screen_code(value: Any, *, label: str, allowed: frozenset[str] | set[str]) -> str:
    normalized = _script_to_screen_text(value, label=label, minimum=1, maximum=64).lower()
    if normalized not in allowed:
        raise ValueError(f"{label} không hợp lệ")
    return normalized


def _script_to_screen_boundary() -> dict[str, Any]:
    """Exact no-execution boundary for a temporary vproduct planning pack."""

    return {
        "execution": "web_native_deterministic_script_to_screen_planner_only",
        "input_persisted": False,
        "telegram_state_changed": False,
        "bot_called": False,
        "bridge_called": False,
        "provider_called": False,
        "media_opened": False,
        "media_created": False,
        "preview_created": False,
        "output_created": False,
        "job_created": False,
        "wallet_changed": False,
        "payment_changed": False,
        "asset_created": False,
        "published": False,
        "delivered": False,
    }


def _script_to_screen_plan_save_boundary(
    *,
    draft_recomputed_on_server: bool = True,
    web_video_plan_persisted: bool = True,
) -> dict[str, Any]:
    return {
        "execution": "web_native_script_to_screen_video_plan_server_recomputed",
        "draft_recomputed_on_server": bool(draft_recomputed_on_server),
        "web_video_plan_persisted": bool(web_video_plan_persisted),
        "telegram_state_changed": False,
        "bot_called": False,
        "bridge_called": False,
        "provider_called": False,
        "media_opened": False,
        "media_created": False,
        "preview_created": False,
        "output_created": False,
        "job_created": False,
        "wallet_changed": False,
        "payment_changed": False,
        "asset_created": False,
        "published": False,
        "delivered": False,
    }


def _script_to_screen_guard(marker: str, *, saving: bool = False) -> dict[str, Any] | None:
    if not marker:
        return None
    if marker == "claim":
        message = "Brief có tuyên bố cần nguồn hoặc kiểm chứng. Hãy viết lại thành direction có thể review trước khi lập kịch bản."
        code = "WEB_SCRIPT_TO_SCREEN_CLAIM_GUARD"
    else:
        message = "Script-to-Screen Planner không hỗ trợ mô phỏng người thật, người nổi tiếng hoặc tác phẩm nhận diện. Hãy dùng direction nguyên bản."
        code = "WEB_SCRIPT_TO_SCREEN_ORIGINALITY_GUARD"
    data = (
        {
            "destination": "video_plan",
            **_script_to_screen_plan_save_boundary(
                draft_recomputed_on_server=False,
                web_video_plan_persisted=False,
            ),
        }
        if saving
        else _script_to_screen_boundary()
    )
    return envelope(False, message, data=data, status_name="guarded", error_code=code)


class ScriptToScreenPlannerRequest(BaseModel):
    """Bounded inputs distilled from Bot Task3D's text-first vproduct flows."""

    model_config = ConfigDict(extra="forbid", strict=True)

    project_kind: StrictStr
    brief: StrictStr
    audience: StrictStr = ""
    platform: StrictStr = "tiktok"
    aspect_ratio: StrictStr = "9:16"
    scene_count: StrictInt = Field(ge=3, le=12)
    # multi_scene_film is now presented as an episodic series. Keep the
    # technical identifier stable for Bot parity, but make the Web-owned
    # planning contract explicit about a bounded season and selected episode.
    # None is only a backwards-compatible input default; model_post_init
    # normalizes it to a concrete integer before composition or persistence.
    episode_count: StrictInt | None = None
    selected_episode: StrictInt | None = None
    style: StrictStr = "product_demo"
    color_mood: StrictStr = "bright"
    pace: StrictStr = "balanced"
    image_plan: StrictStr = "per_scene"
    extra_scene: StrictBool = False
    output_target: StrictStr = "prompt_pack"
    cta: StrictStr = ""
    language: StrictStr = "vi"

    @field_validator("project_kind")
    @classmethod
    def _project_kind(cls, value: str) -> str:
        return _script_to_screen_code(value, label="Loại project", allowed=SCRIPT_TO_SCREEN_PROJECT_KINDS)

    @field_validator("brief")
    @classmethod
    def _brief(cls, value: str) -> str:
        return _script_to_screen_text(value, label="Brief Script-to-Screen", minimum=2, maximum=1_000)

    @field_validator("audience")
    @classmethod
    def _audience(cls, value: str) -> str:
        return _script_to_screen_text(value, label="Khán giả", minimum=0, maximum=400, allow_empty=True)

    @field_validator("platform")
    @classmethod
    def _platform(cls, value: str) -> str:
        return _script_to_screen_code(value, label="Nền tảng", allowed=set(SCRIPT_TO_SCREEN_PLATFORMS))

    @field_validator("aspect_ratio")
    @classmethod
    def _aspect_ratio(cls, value: str) -> str:
        return _script_to_screen_code(value, label="Tỷ lệ khung hình", allowed={"9:16", "16:9", "1:1", "4:5"})

    @field_validator("episode_count", "selected_episode")
    @classmethod
    def _episode_number(cls, value: int | None) -> int | None:
        if value is None:
            return None
        if value < 1 or value > 8:
            raise ValueError("Số tập và tập được chọn chỉ có thể từ 1 đến 8")
        return value

    @field_validator("style")
    @classmethod
    def _style(cls, value: str) -> str:
        return _script_to_screen_code(value, label="Phong cách", allowed=set(SCRIPT_TO_SCREEN_STYLES))

    @field_validator("color_mood")
    @classmethod
    def _color_mood(cls, value: str) -> str:
        return _script_to_screen_code(value, label="Màu sắc", allowed=set(SCRIPT_TO_SCREEN_COLORS))

    @field_validator("pace")
    @classmethod
    def _pace(cls, value: str) -> str:
        return _script_to_screen_code(value, label="Nhịp dựng", allowed=set(SCRIPT_TO_SCREEN_PACES))

    @field_validator("image_plan")
    @classmethod
    def _image_plan(cls, value: str) -> str:
        return _script_to_screen_code(value, label="Kế hoạch hình ảnh", allowed=set(SCRIPT_TO_SCREEN_IMAGE_PLANS))

    @field_validator("output_target")
    @classmethod
    def _output_target(cls, value: str) -> str:
        return _script_to_screen_code(value, label="Đầu ra planner", allowed=set(SCRIPT_TO_SCREEN_OUTPUT_TARGETS))

    @field_validator("cta")
    @classmethod
    def _cta(cls, value: str) -> str:
        return _script_to_screen_text(value, label="CTA", minimum=0, maximum=280, allow_empty=True)

    @field_validator("language")
    @classmethod
    def _language(cls, value: str) -> str:
        return _script_to_screen_code(value, label="Ngôn ngữ", allowed=SCRIPT_TO_SCREEN_LANGUAGES)

    def model_post_init(self, __context: Any) -> None:
        episode_count = self.episode_count
        if episode_count is None:
            # Legacy Bot-shaped requests did not carry an episode count. A
            # normal Script → Image → Video remains one self-contained
            # episode; the renamed multi-scene product becomes a useful
            # three-episode roadmap rather than a misleading label.
            episode_count = 3 if self.project_kind == "multi_scene_film" else 1
            self.episode_count = episode_count
        selected_episode = self.selected_episode
        if selected_episode is None:
            selected_episode = 1
            self.selected_episode = selected_episode
        if self.project_kind == "script_image_video" and episode_count != 1:
            raise ValueError("Kịch bản → Ảnh → Video chỉ hỗ trợ một tập trong mỗi plan")
        if self.project_kind == "multi_scene_film" and not 2 <= episode_count <= 8:
            raise ValueError("Phim dài tập cần từ 2 đến 8 tập để lập roadmap")
        if selected_episode > episode_count:
            raise ValueError("Tập được chọn không thể lớn hơn tổng số tập")
        if self.extra_scene and self.scene_count >= 12:
            raise ValueError("Khi thêm cảnh kết, số cảnh cơ bản phải tối đa 11")


class ScriptToScreenPlannerSaveRequest(ScriptToScreenPlannerRequest):
    model_config = ConfigDict(extra="forbid", strict=True)

    destination: StrictStr = "video_plan"
    idempotency_key: StrictStr

    @field_validator("destination")
    @classmethod
    def _destination(cls, value: str) -> str:
        return _script_to_screen_code(value, label="Nơi lưu plan", allowed={"video_plan"})

    @field_validator("idempotency_key")
    @classmethod
    def _idempotency(cls, value: str) -> str:
        return _idempotency_key(value)


SCRIPT_TO_SCREEN_PHASES: tuple[tuple[str, str, str], ...] = (
    ("hook", "Hook", "Mở bằng vấn đề, kết quả hoặc chi tiết tạo tò mò"),
    ("context", "Bối cảnh", "Đặt người xem vào tình huống có thể nhận ra"),
    ("problem", "Điểm cần giải quyết", "Nêu trở ngại hoặc nhu cầu bằng ngôn ngữ cụ thể"),
    ("solution", "Giải pháp / diễn biến", "Cho thấy hành động, demo hoặc bước chuyển đổi có thể review"),
    ("proof", "Chi tiết thuyết phục", "Dùng cận cảnh, quy trình hoặc lý do thay vì khẳng định tuyệt đối"),
    ("cta", "Kết & CTA", "Chốt thông điệp, bước tiếp theo nhẹ và một khung hình ổn định"),
)


def _script_to_screen_label(catalog: dict[str, dict[str, str]], key: str, language: str) -> str:
    entry = catalog[key]
    return str(entry.get(language) or entry["vi"])


def _script_to_screen_kind_label(project_kind: str, language: str) -> str:
    labels = {
        "script_image_video": {"vi": "Kịch bản → Ảnh → Video", "en": "Script → Image → Video"},
        "multi_scene_film": {"vi": "Phim dài tập", "en": "Episodic series"},
    }
    return str(labels[project_kind].get(language) or labels[project_kind]["vi"])


def _script_to_screen_phase(index: int, total: int) -> tuple[str, str, str]:
    phase_index = min(
        len(SCRIPT_TO_SCREEN_PHASES) - 1,
        round((index - 1) * (len(SCRIPT_TO_SCREEN_PHASES) - 1) / max(1, total - 1)),
    )
    return SCRIPT_TO_SCREEN_PHASES[phase_index]


def _script_to_screen_motion(index: int, total: int, pace: str, language: str) -> str:
    motions_vi = ("cận cảnh tĩnh có chủ đích", "push-in chậm", "pan nhẹ theo hành động", "góc rộng có bối cảnh", "cận cảnh chi tiết", "hero frame ổn định")
    motions_en = ("purposeful static close-up", "slow push-in", "motivated pan", "contextual wide shot", "detail close-up", "stable hero frame")
    motions = motions_vi if language == "vi" else motions_en
    base = motions[min(len(motions) - 1, round((index - 1) * (len(motions) - 1) / max(1, total - 1)))]
    pace_label = _script_to_screen_label(SCRIPT_TO_SCREEN_PACES, pace, language)
    return f"{base}; {pace_label}"


def _script_to_screen_episode_descriptor(
    payload: ScriptToScreenPlannerRequest,
    *,
    index: int,
    scenes_per_episode: int,
) -> dict[str, Any]:
    """Return one reviewable episode card; never runtime or media state."""

    total = int(payload.episode_count or 1)
    topic = _excerpt(payload.brief, 110)
    if total == 1:
        if payload.language == "en":
            title = f"Episode 1: {topic}"
            arc = "A complete, reviewable narrative arc for this one planning pack."
            focus = "Set up one clear audience need, then show one truthful direction."
            cliffhanger = "Close on a stable review point, not a generated output."
        else:
            title = f"Tập 1: {topic}"
            arc = "Mạch nội dung hoàn chỉnh, có thể review cho một planning pack."
            focus = "Đặt một nhu cầu rõ ràng của khán giả rồi triển khai một direction trung thực."
            cliffhanger = "Khép lại ở điểm có thể review, không phải output đã tạo."
    else:
        stages_vi = (
            ("Khởi đầu", "Thiết lập vấn đề, nhân vật hoặc bối cảnh có thể nhận ra.", "Gợi một câu hỏi đủ rõ để người xem muốn theo dõi tập tiếp."),
            ("Mở rộng", "Đẩy tình huống đi sâu hơn bằng hành động hoặc chi tiết có thể kiểm tra.", "Để lại một lựa chọn hoặc trở ngại có lý do cho tập tiếp."),
            ("Chuyển biến", "Làm rõ cách tiếp cận, góc nhìn hoặc bước thay đổi trung tâm.", "Kết bằng một hệ quả cần được giải quyết tiếp, không hứa hẹn kết quả."),
            ("Giải quyết", "Gom các chi tiết quan trọng thành một bước tiến hợp lý và trung thực.", "Dành một nhịp mở nhẹ nếu series còn tiếp, hoặc kết thúc có thể review."),
        )
        stages_en = (
            ("Set-up", "Establish a recognizable problem, character or setting.", "Leave one concrete question that earns the next episode."),
            ("Escalation", "Move the situation forward with reviewable action or detail.", "Leave a justified choice or obstacle for the next episode."),
            ("Turn", "Clarify the central approach, perspective or change.", "End on a consequence to examine next, never a promised result."),
            ("Resolution", "Bring the important details into one honest next step.", "Leave a light continuation beat or a reviewable ending."),
        )
        stages = stages_en if payload.language == "en" else stages_vi
        stage_index = min(len(stages) - 1, round((index - 1) * (len(stages) - 1) / max(1, total - 1)))
        stage, focus, cliffhanger = stages[stage_index]
        if payload.language == "en":
            title = f"Episode {index}: {stage}"
            arc = f"{stage} for {topic}."
        else:
            title = f"Tập {index}: {stage}"
            arc = f"{stage} cho {topic}."
    return {
        "index": index,
        "title": _script_to_screen_text(_excerpt(title, 180), label="Tiêu đề tập", minimum=2, maximum=180),
        "arc": _script_to_screen_text(arc, label="Mạch tập", minimum=2, maximum=1_200),
        "focus": _script_to_screen_text(focus, label="Trọng tâm tập", minimum=2, maximum=1_200),
        "cliffhanger": _script_to_screen_text(cliffhanger, label="Nhịp nối tập", minimum=2, maximum=1_200),
        "scene_count": scenes_per_episode,
    }


def _script_to_screen_series_projection(
    payload: ScriptToScreenPlannerRequest,
    *,
    scenes_per_episode: int,
) -> dict[str, Any]:
    """Build a bounded season map without turning it into an execution plan."""

    total = int(payload.episode_count or 1)
    episodes = [
        _script_to_screen_episode_descriptor(payload, index=index, scenes_per_episode=scenes_per_episode)
        for index in range(1, total + 1)
    ]
    if payload.language == "en":
        continuity = [
            "Keep the subject, setting, approved brand details and visual treatment internally consistent between episodes.",
            "Each episode has its own reviewable narrative beat; it is not a queued render, job or delivery.",
            "Review claims, consent, rights and audience suitability before moving any episode into a separately approved workflow.",
        ]
        save_scope = "A save creates one private Video Plan draft for the selected episode only; it does not create a season, render, job or output."
    else:
        continuity = [
            "Giữ chủ thể, bối cảnh, chi tiết thương hiệu hợp lệ và treatment hình ảnh nhất quán giữa các tập.",
            "Mỗi tập có nhịp nội dung riêng để review; không phải render, job hoặc giao hàng đã được xếp hàng.",
            "Rà soát claim, consent, quyền sử dụng và phù hợp khán giả trước khi chuyển bất kỳ tập nào sang workflow được phê duyệt riêng.",
        ]
        save_scope = "Lưu chỉ tạo một Video Plan Draft riêng tư cho tập đang chọn; không tạo season, render, job hoặc output."
    return {
        "mode": "episodic_series" if total > 1 else "single_episode",
        "episode_count": total,
        "selected_episode": int(payload.selected_episode or 1),
        "episodes": episodes,
        "continuity_bible": continuity,
        "save_scope": save_scope,
    }


def _script_to_screen_prompt_language(payload: ScriptToScreenPlannerRequest) -> dict[str, str]:
    language = payload.language
    style = _script_to_screen_label(SCRIPT_TO_SCREEN_STYLES, payload.style, language)
    color = _script_to_screen_label(SCRIPT_TO_SCREEN_COLORS, payload.color_mood, language)
    image_plan = _script_to_screen_label(SCRIPT_TO_SCREEN_IMAGE_PLANS, payload.image_plan, language)
    platform = _script_to_screen_label(SCRIPT_TO_SCREEN_PLATFORMS, payload.platform, language)
    if language == "en":
        return {
            "style": style,
            "color": color,
            "image_plan": image_plan,
            "platform": platform,
            "audience": payload.audience or "the intended audience",
            "cta": payload.cta or "Invite the viewer to review, save, or take one appropriate next step.",
            "continuity": "Keep subject, proportions, legitimate brand details and color treatment internally consistent across scenes.",
            "negative": "No named living creator style, real-person imitation, unsupported claim, unreadable UI, fabricated proof or altered legitimate brand detail.",
        }
    return {
        "style": style,
        "color": color,
        "image_plan": image_plan,
        "platform": platform,
        "audience": payload.audience or "khán giả mục tiêu",
        "cta": payload.cta or "Mời người xem xem lại, lưu nội dung hoặc thực hiện một bước tiếp theo phù hợp.",
        "continuity": "Giữ nhất quán chủ thể, tỷ lệ, chi tiết thương hiệu hợp lệ và treatment màu giữa các cảnh.",
        "negative": "Không mô phỏng tác giả/người thật được nhận diện, không claim chưa kiểm chứng, UI không đọc được, bằng chứng bịa đặt hoặc thay đổi chi tiết thương hiệu hợp lệ.",
    }


def _compose_script_to_screen_planner(payload: ScriptToScreenPlannerRequest) -> dict[str, Any]:
    """Compile only reviewable text direction from fresh Web form values."""

    words = _script_to_screen_prompt_language(payload)
    total = payload.scene_count + (1 if payload.extra_scene else 0)
    project_label = _script_to_screen_kind_label(payload.project_kind, payload.language)
    series = _script_to_screen_series_projection(payload, scenes_per_episode=total)
    selected_episode = series["episodes"][int(payload.selected_episode or 1) - 1]
    episode_index = int(selected_episode["index"])
    episode_total = int(series["episode_count"])
    episode_context = str(selected_episode["title"])
    if payload.language == "en":
        title = f"{project_label}: {payload.brief}" if episode_total == 1 else f"{project_label} · Episode {episode_index}/{episode_total}: {payload.brief}"
        summary = (
            f"A {total}-scene {project_label.lower()} plan for {words['platform']}. "
            f"Treatment: {words['style']}, {words['color']}, {words['image_plan']}."
            if episode_total == 1
            else f"An {episode_total}-episode {project_label.lower()} roadmap for {words['platform']}; this pack expands Episode {episode_index} with {total} reviewable scenes. Treatment: {words['style']}, {words['color']}, {words['image_plan']}."
        )
        script = {
            "hook": f"Open {episode_context} with a specific, reviewable moment around {payload.brief}.",
            "arc": str(selected_episode["arc"]) if episode_total > 1 else "Move from context to a clear action or demonstration, then end with one truthful next step.",
            "voice_direction": f"Speak clearly for {words['audience']}; use natural pauses between scene changes.",
            "cta": words["cta"],
        }
    else:
        title = f"{project_label}: {payload.brief}" if episode_total == 1 else f"{project_label} · Tập {episode_index}/{episode_total}: {payload.brief}"
        summary = (
            f"Kế hoạch {total} cảnh cho {project_label.lower()} trên {words['platform']}. "
            f"Treatment: {words['style']}, {words['color']}, {words['image_plan']}."
            if episode_total == 1
            else f"Roadmap {episode_total} tập cho {project_label.lower()} trên {words['platform']}; pack này phát triển Tập {episode_index} với {total} cảnh có thể review. Treatment: {words['style']}, {words['color']}, {words['image_plan']}."
        )
        script = {
            "hook": f"Mở {episode_context} bằng một khoảnh khắc cụ thể, có thể review xoay quanh {payload.brief}.",
            "arc": str(selected_episode["arc"]) if episode_total > 1 else "Đi từ bối cảnh sang hành động hoặc demo rõ ràng, rồi kết bằng một bước tiếp theo trung thực.",
            "voice_direction": f"Nói rõ ràng cho {words['audience']}; ngắt nhịp tự nhiên khi chuyển cảnh.",
            "cta": words["cta"],
        }

    storyboard: list[dict[str, Any]] = []
    for index in range(1, total + 1):
        phase_id, phase_label_vi, phase_direction_vi = _script_to_screen_phase(index, total)
        if payload.language == "en":
            phase_labels = {
                "hook": ("Hook", "Create immediate, reviewable curiosity."),
                "context": ("Context", "Show the recognizable situation or setting."),
                "problem": ("Need", "Make the constraint or audience need concrete."),
                "solution": ("Action", "Show a clear, reviewable action or demonstration."),
                "proof": ("Detail", "Use tangible detail rather than an unsupported result claim."),
                "cta": ("Close", "Settle the message and invite one appropriate next step."),
            }
            phase_label, phase_direction = phase_labels[phase_id]
            narration = f"Episode {episode_index}/{episode_total}, scene {index}: {phase_direction} Relate it to {payload.brief}."
            screen_text = "One clear phrase, optional and reviewed before use."
            image_prompt = (
                f"Original {phase_label.lower()} keyframe for {payload.brief}; {words['style']}; {words['color']} palette; "
                f"{payload.aspect_ratio} composition; coherent subject and environment; no readable brand claim or copied visual identity."
            )
            video_prompt = (
                f"Original episode {episode_index}/{episode_total}, scene {index}/{total} for {payload.brief}: {phase_direction.lower()} "
                f"Camera: {_script_to_screen_motion(index, total, payload.pace, payload.language)}. "
                f"Maintain continuity and make a clean transition to the next scene."
            )
            transition = "Cut on a motivated action" if index < total else (
                "End on a reviewable beat that opens the next episode" if episode_index < episode_total else "Hold the final frame for review"
            )
        else:
            phase_label, phase_direction = phase_label_vi, phase_direction_vi
            narration = f"Tập {episode_index}/{episode_total}, cảnh {index}: {phase_direction}. Liên hệ trực tiếp với {payload.brief}."
            screen_text = "Một cụm ý rõ ràng, chỉ dùng sau khi người làm nội dung tự review."
            image_prompt = (
                f"Keyframe nguyên bản cho cảnh {phase_label.lower()} của {payload.brief}; phong cách {words['style']}; "
                f"màu {words['color']}; bố cục {payload.aspect_ratio}; chủ thể và bối cảnh nhất quán; "
                "không chèn claim thương hiệu chưa kiểm chứng hoặc nhận diện hình ảnh sao chép."
            )
            video_prompt = (
                f"Tập nguyên bản {episode_index}/{episode_total}, cảnh {index}/{total} cho {payload.brief}: {phase_direction.lower()}. "
                f"Camera: {_script_to_screen_motion(index, total, payload.pace, payload.language)}. "
                "Giữ continuity và chuyển sang cảnh kế tiếp có lý do."
            )
            transition = "Cắt theo hành động có chủ đích" if index < total else (
                "Kết bằng nhịp có thể review để mở sang tập tiếp" if episode_index < episode_total else "Giữ hero frame cuối để review"
            )
        storyboard.append(
            {
                "index": index,
                "phase": phase_id,
                "title": phase_label,
                "duration_seconds": 5 if payload.project_kind == "script_image_video" else 6,
                "purpose": phase_direction,
                "narration": narration,
                "on_screen_text": screen_text,
                "shot": _script_to_screen_motion(index, total, payload.pace, payload.language),
                "image_prompt": image_prompt,
                "video_prompt": video_prompt,
                "transition": transition,
            }
        )

    if payload.language == "en":
        caption = f"{payload.brief} — a reviewable {project_label.lower()} direction for {words['platform']}."
        review = [
            "Verify every product, price, performance and availability statement before publishing.",
            "Use only assets, logos, people and music you are authorized to use.",
            words["continuity"],
            "This pack is planning text only; use a separately approved workflow for any production or publication action.",
        ]
    else:
        caption = f"{payload.brief} — direction {project_label.lower()} có thể review trước khi sản xuất trên {words['platform']}."
        review = [
            "Kiểm tra mọi thông tin sản phẩm, giá, hiệu quả và khả dụng trước khi đăng.",
            "Chỉ dùng asset, logo, người xuất hiện và nhạc mà bạn có quyền sử dụng.",
            words["continuity"],
            "Pack này chỉ là text planning; production hoặc publish phải đi qua workflow riêng đã được phê duyệt.",
        ]
    if episode_total > 1:
        review.append(str(series["save_scope"]))
    return {
        "title": _script_to_screen_text(_excerpt(title, 180), label="Tiêu đề Script-to-Screen", minimum=2, maximum=180),
        "project_kind": {"id": payload.project_kind, "label": project_label},
        "platform": {"id": payload.platform, "label": words["platform"]},
        "aspect_ratio": payload.aspect_ratio,
        "style": {"id": payload.style, "label": words["style"]},
        "color_mood": {"id": payload.color_mood, "label": words["color"]},
        "pace": {"id": payload.pace, "label": _script_to_screen_label(SCRIPT_TO_SCREEN_PACES, payload.pace, payload.language)},
        "image_plan": {"id": payload.image_plan, "label": words["image_plan"]},
        "output_target": {"id": payload.output_target, "label": _script_to_screen_label(SCRIPT_TO_SCREEN_OUTPUT_TARGETS, payload.output_target, payload.language)},
        "brief": payload.brief,
        "audience": payload.audience,
        "scene_count": total,
        "series": series,
        "creative_summary": summary,
        "script": script,
        "storyboard": storyboard,
        "caption": caption,
        "hashtags": ["#contentplan", "#storyboard", "#reviewbeforepublish"] + (["#episodicseries", f"#episode{episode_index}"] if episode_total > 1 else []),
        "negative_constraints": [words["negative"], words["continuity"]],
        "review_before_use": review,
    }


def _script_to_screen_to_video_plan(
    payload: ScriptToScreenPlannerSaveRequest,
    planner: dict[str, Any],
) -> tuple[PlanPayload, list[ScenePayload]]:
    """Translate only the server-built pack into private Web plan records."""

    storyboard = planner.get("storyboard") if isinstance(planner.get("storyboard"), list) else []
    if not 3 <= len(storyboard) <= 12:
        raise HTTPException(status_code=422, detail="Số cảnh Script-to-Screen không hợp lệ để lưu Video Plan")
    project_label = _script_to_screen_kind_label(payload.project_kind, payload.language)
    series = planner.get("series") if isinstance(planner.get("series"), dict) else {}
    episode_count = int(series.get("episode_count") or 1)
    selected_episode = int(series.get("selected_episode") or 1)
    if not 1 <= selected_episode <= episode_count <= 8:
        raise HTTPException(status_code=422, detail="Roadmap tập Script-to-Screen không hợp lệ để lưu Video Plan")
    plan = PlanPayload.model_validate(
        {
            "title": str(planner["title"]),
            "format": "campaign" if payload.project_kind == "multi_scene_film" else "product_demo",
            "language": payload.language,
            "aspect_ratio": payload.aspect_ratio,
            "target_duration_seconds": sum(int(item.get("duration_seconds") or 0) for item in storyboard),
            "objective": _excerpt(str(planner.get("creative_summary") or project_label), 1_100),
            "audience": payload.audience,
            "brief": f"Web-native plan rebuilt on the server. Original brief: {payload.brief}. Episode {selected_episode}/{episode_count}.",
            "tags": [
                "script-to-screen", payload.project_kind, f"platform-{payload.platform}", f"style-{payload.style}",
                f"season-{episode_count}", f"episode-{selected_episode}",
            ],
        }
    )
    scenes: list[ScenePayload] = []
    for item in storyboard:
        if not isinstance(item, dict):
            raise HTTPException(status_code=422, detail="Storyboard Script-to-Screen không hợp lệ")
        index = int(item.get("index") or 0)
        if index < 1:
            raise HTTPException(status_code=422, detail="Storyboard Script-to-Screen không hợp lệ")
        phase = str(item.get("phase") or "custom")
        scene_type = phase if phase in SCENE_TYPES else "custom"
        shot_notes = "\n".join(
            [
                str(item.get("video_prompt") or ""),
                "Negative constraints:",
                *[str(value) for value in planner.get("negative_constraints", []) if isinstance(value, str)],
            ]
        )
        if len(shot_notes) > 5_000:
            shot_notes = f"{shot_notes[:4_996].rstrip()}..."
        scenes.append(
            ScenePayload.model_validate(
                {
                    "title": _excerpt(str(item.get("title") or f"Scene {index}"), 180),
                    "scene_type": scene_type,
                    "duration_seconds": int(item.get("duration_seconds") or 0),
                    "visual_direction": str(item.get("image_prompt") or ""),
                    "narration": str(item.get("narration") or ""),
                    "on_screen_text": str(item.get("on_screen_text") or ""),
                    "shot_notes": shot_notes,
                    "transition": str(item.get("transition") or ""),
                    "tags": ["script-to-screen", f"scene-{index}", f"phase-{phase}"],
                }
            )
        )
    return plan, scenes


@router.post("/tools/script-to-screen-planner")
async def compose_script_to_screen_planner(
    payload: ScriptToScreenPlannerRequest,
    account: dict = Depends(require_csrf),
):
    """Compile Bot-derived Script → Image → Video / episodic-series planning text only."""

    _require_enabled()
    del account
    guarded = _script_to_screen_guard(_cinematic_ad_marker(payload.brief, payload.audience, payload.cta))
    if guarded:
        return guarded
    planner = _compose_script_to_screen_planner(payload)
    return envelope(
        True,
        "Đã tạo Script-to-Screen Prompt Pack để review. Chưa tạo media, runtime, job, thanh toán hoặc output.",
        data={"planner": planner, **_script_to_screen_boundary()},
        status_name="draft",
    )


@router.post("/tools/script-to-screen-planner/save")
async def save_script_to_screen_planner_to_video_plan(
    payload: ScriptToScreenPlannerSaveRequest,
    request: Request,
    account: dict = Depends(require_csrf),
):
    """Persist a deliberate, server-recomputed Script-to-Screen Web draft."""

    _require_enabled()
    guarded = _script_to_screen_guard(_cinematic_ad_marker(payload.brief, payload.audience, payload.cta), saving=True)
    if guarded:
        return guarded
    account_id = str(account["id"])
    fingerprint = _fingerprint({"operation": "script-to-screen-planner-save-video-plan", **payload.model_dump(exclude={"idempotency_key"})})

    def operation(conn: Any) -> dict[str, Any]:
        planner = _compose_script_to_screen_planner(payload)
        plan_payload, scene_payloads = _script_to_screen_to_video_plan(payload, planner)
        count = conn.execute(
            "SELECT COUNT(*) FROM web_video_plans WHERE account_id=? AND lifecycle<>'archived'",
            (account_id,),
        ).fetchone()
        if int(count[0] or 0) >= MAX_PLANS_PER_ACCOUNT:
            return envelope(
                False,
                "Video Production Studio đã đạt giới hạn plan đang hoạt động.",
                data={"destination": "video_plan", **_script_to_screen_plan_save_boundary(draft_recomputed_on_server=True, web_video_plan_persisted=False)},
                status_name="guarded",
                error_code="WEB_VIDEO_PLAN_LIMIT",
            )
        if not 3 <= len(scene_payloads) <= 12:
            raise HTTPException(status_code=422, detail="Số scene Script-to-Screen không hợp lệ để lưu Video Plan")
        plan_id = str(uuid.uuid4())
        now = utc_now()
        plan_snapshot = _plan_snapshot(plan_payload, lifecycle="draft")
        _insert_plan(conn, plan_id=plan_id, account_id=account_id, snapshot=plan_snapshot, revision=1, now=now)
        _insert_plan_version(conn, plan_id=plan_id, account_id=account_id, revision=1, snapshot=plan_snapshot, now=now)
        _event(conn, account_id=account_id, plan_id=plan_id, action="plan_created", revision=1)
        for ordinal, scene_payload in enumerate(scene_payloads, start=1):
            scene_id = str(uuid.uuid4())
            scene_snapshot = _scene_snapshot(scene_payload, state="active")
            _insert_scene(conn, scene_id=scene_id, plan_id=plan_id, account_id=account_id, ordinal=ordinal, snapshot=scene_snapshot, revision=1, now=now)
            _insert_scene_version(conn, scene_id=scene_id, account_id=account_id, revision=1, snapshot=scene_snapshot, now=now)
            _event(conn, account_id=account_id, plan_id=plan_id, scene_id=scene_id, action="scene_created", revision=1)
        _audit(
            conn,
            request=request,
            account=account,
            action="web.video.script_to_screen.save_plan",
            target=plan_id,
            detail="server-recomputed Bot-derived script-to-screen planner saved as web-owned draft video plan",
        )
        return envelope(
            True,
            "Đã lưu Script-to-Screen Prompt Pack thành Video Plan Draft riêng tư. Không có Telegram/Bot state, provider, media, job, thanh toán, publish hoặc giao hàng.",
            data={"_script_to_screen_planner_plan_save": True, "plan": {"id": plan_id, "revision": 1, "state": "draft"}, "scene_count": len(scene_payloads)},
            status_name="draft",
        )

    return _idempotent(
        f"web-video-studio:{account_id}:script-to-screen-planner:save-plan",
        account_id,
        payload.idempotency_key,
        fingerprint,
        operation,
    )
