"""Canonical public capability catalog for the standalone Web App.

This module deliberately contains no provider implementation. It is the one
place the Web shell, API and migration inventory use to describe routes owned
by the independent Web product and the small set of optional Bot companion
surfaces. A catalog entry is never evidence that an engine works: Web
authoring, Web-native execution and Bot integration each expose readiness
through their own capability checks.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable


@dataclass(frozen=True)
class WebFeature:
    key: str
    title: str
    group: str
    route: str
    kind: str = "customer"
    description: str = ""
    input_hint: str = ""


@dataclass(frozen=True)
class MenuCapability:
    """One reviewed Web navigation destination for the product capability menu.

    This is intentionally keyed by a Web product concept, never a raw
    Telegram callback.  The browser may use it to render a stable navigation
    choice, while the static migration audit retains the private evidence that
    a finite Bot menu action can lead to that choice.  A navigation destination
    does not grant an engine, provider, payment, job or Bot-state action.
    """

    key: str
    feature_key: str
    authority: str
    launch_mode: str
    availability: str
    description: str


CUSTOMER_FEATURES: tuple[WebFeature, ...] = (
    WebFeature("dashboard", "Tổng quan", "account", "/dashboard", description="Tài khoản, Xu, job và trạng thái gần đây."),
    WebFeature("feature_catalog", "Tất cả công cụ", "content", "/features", description="Khám phá workflow Web, phần authoring độc lập và trạng thái Engine/Bot companion tách biệt."),
    WebFeature("projects", "Project Center", "content", "/projects", description="Project và Studio Document có version do Web Workspace sở hữu, không phụ thuộc Telegram."),
    WebFeature("project_packages", "Project Packages", "content", "/project-packages", description="Snapshot ZIP bất biến của Project do Web App tạo và xác minh riêng tư; không phải Job Bot hay gói dịch vụ."),
    WebFeature("workspace_drafts", "Bản nháp của tôi", "content", "/workspace", description="Lưu và tiếp tục brief Web an toàn, không lưu file, quote hoặc trạng thái Bot."),
    WebFeature("account", "Tài khoản", "account", "/account", description="Hồ sơ, liên kết Telegram và bảo mật."),
    WebFeature("account_activity", "Hoạt động tài khoản", "account", "/account/activity", description="Nhật ký đã sanitize của các hoạt động Web thuộc signed account."),
    WebFeature("account_security", "Bảo mật tài khoản", "account", "/account/security", description="Quản lý signed session, mật khẩu Web và phương thức OAuth theo signed account; không lộ credential hoặc state Bot."),
    # Memory Center is deliberately Web-owned: it gives the full portal a
    # professional notes/task surface without copying Bot Telegram state,
    # wallet, payment, job or provider data.
    WebFeature("notes", "Ghi chú & Memory", "account", "/notes", description="Ghi chú, tag, ưu tiên, version history và reminder liên kết do Web account sở hữu riêng."),
    WebFeature("reminders", "Nhắc việc", "account", "/reminders", description="Nhắc việc một lần/lặp lại, pause/resume/complete do Web account quản lý; không giả Telegram notification."),
    WebFeature("inbox", "Inbox", "account", "/inbox", description="Bản ghi nhắc việc riêng tư do Web scheduler materialize; không gửi Telegram, email, SMS hay web-push."),
    WebFeature("automation", "Automation Center", "account", "/automation", description="Theo dõi chính sách và receipt của tự động hóa Web-native có kiểm soát; không gọi Bot, provider, ví hay PayOS."),
    WebFeature("referrals", "Giới thiệu", "account", "/referrals", description="Referral/link thống kê cần Bot canonical xác minh."),
    WebFeature("rewards", "Ưu đãi & quà", "account", "/rewards", description="Gift, birthday và promo chỉ được Bot canonical xử lý."),
    WebFeature("community", "Cộng đồng", "account", "/community", description="Kênh chính thức và community handoff qua Bot."),
    WebFeature("guides", "Hướng dẫn Bot", "account", "/guides", description="Trợ giúp và menu Bot cho các workflow chưa có adapter Web."),
    WebFeature("wallet", "Ví Xu", "wallet", "/wallet", description="Số dư và lịch sử canonical từ bot."),
    WebFeature("wallet_topup", "Nạp Xu", "wallet", "/wallet/topup", description="Tạo thanh toán qua core PayOS canonical."),
    WebFeature("packages", "Gói dịch vụ", "wallet", "/packages"),
    WebFeature("membership", "Gói thành viên", "wallet", "/membership", description="Tier, trial và quyền lợi chỉ đọc từ bot canonical."),
    WebFeature("jobs", "Công việc", "jobs", "/jobs", description="Theo dõi trạng thái và kết quả đã xác thực."),
    WebFeature("assets", "Tài sản Bot", "jobs", "/assets", description="Tệp đầu ra đã được Bot canonical xác thực ownership và delivery."),
    WebFeature("asset_vault", "Asset Vault", "jobs", "/asset-vault", description="Kho tệp riêng do Web Workspace sở hữu; không phải output, job hay storage của Bot."),
    WebFeature("chat", "AI Chat Workspace", "content", "/chat", description="Workspace hội thoại riêng tư: context, prompt/decision do bạn soạn và revision history. Chưa gọi model, Bot, provider, Xu hay job."),
    WebFeature("analytics_workspace", "Analytics Workspace", "content", "/analytics", description="Báo cáo, metric, snapshot và nhận định do chính tài khoản Web nhập; chỉ so sánh xác định từ dữ liệu đã lưu, không kết nối platform/Bot/provider, không tạo AI insight, Xu, PayOS, job hay publish."),
    WebFeature("workboard", "Workboard & Review Queue", "content", "/workboard", description="Kanban và checklist riêng tư để điều phối Project, Campaign, Studio, Analytics, Note hoặc Draft do Web account sở hữu; không tạo job, publish, thông báo, provider, Bot, Xu hay PayOS."),
    WebFeature("prompt_studio", "Prompt Studio", "content", "/prompt-studio", description="Blueprint prompt deterministic từ brief biên tập để tự review; không lưu template, gọi AI/Bot/provider, tạo job, Xu/PayOS, asset, publish hay delivery.", input_hint="Mô tả mục tiêu nội dung."),
    WebFeature("prompt_library", "Prompt Library", "content", "/prompt-library", description="Kho template prompt riêng tư có tag, metadata, version history và preview cục bộ; không gọi AI engine hoặc Bot."),
    WebFeature("free_prompt_gallery", "Free Prompt Gallery", "content", "/free-prompt-gallery", description="Snapshot 140 prompt seed đã rà soát từ Free Hub của Bot, có lọc/copy và lưu tường minh vào Prompt Library riêng; Gallery không gọi Bot/provider/job/ví Xu/PayOS hoặc publish."),
    WebFeature("content_studio", "Creative Content Studio", "content", "/content-studio", description="Workspace brief, caption, hook, script, storyboard và content pack có version/review riêng tư; chỉ tạo khung nháp cục bộ, không gọi Bot, provider, job, ví Xu, PayOS hoặc publish."),
    WebFeature("channel_strategy", "Channel Strategy", "content", "/content/channel-strategy", description="Hồ sơ kênh, đối tượng, giọng văn, chủ đề ưu tiên/cần tránh, affiliate, mục tiêu và version history Web-owned; direction chỉ deterministic để review, không kết nối nền tảng, lấy analytics, gọi Bot/provider, tạo job, Xu/PayOS hoặc publish."),
    WebFeature("content_prompt_pack", "Content Prompt Pack", "content", "/content/prompt-pack", description="Tạo bộ prompt, caption, hook, ý tưởng và hướng visual bằng template Web-native deterministic; không gọi AI/provider/Bot, tạo job, output, thanh toán hoặc publish."),
    WebFeature("publish_review_pack", "Gói review trước khi đăng", "content", "/content/publish-review", description="Chuyển Free Hub publish package của Bot thành gói title/caption/hashtag/CTA để người dùng tự review; không kết nối social, tạo lịch, job, output, thanh toán hoặc publish."),
    WebFeature("contextual_ad_prompt", "Contextual Ad Prompt Wizard", "content", "/content/contextual-prompt", description="Chuyển wizard Meta prompt nhiều lựa chọn của Bot thành plan prompt quảng cáo deterministic có goal, platform, ratio, style, caption, hashtag, shot list và guardrails; không gọi Meta/provider/Bot, tạo media/job, thanh toán hoặc publish."),
    WebFeature("trend_research", "Trend Research Plan", "content", "/trend-research", description="Checklist keyword và tiêu chí nghiên cứu trend thủ công chuyển từ Bot; không live search, scraping, social/provider/Bot call, job, Xu, PayOS, asset, media output hoặc publish."),
    WebFeature("media_factory", "Media Factory Blueprint", "content", "/media-factory", description="Bản đồ content/video pack deterministic chuyển từ Bot /media_factory để review và điều phối workspace; không live search, provider/Bot call, job, Xu/PayOS, media output, publish hoặc delivery."),
    WebFeature("creative_flow", "Creative Flow Composer", "content", "/creative-flow", description="Template creative flow deterministic chuyển từ Bot /creative_flow: hook, script, image/music/SFX direction, caption và CTA để review; không provider/Bot call, job, Xu/PayOS, output media hoặc publish."),
    WebFeature("video_factory_workflow", "Video Factory Workflow", "video", "/video-studio/workflow", description="Bản đồ quy trình 7 bước chuyển từ Bot /video_factory_flow giữa các Web workspace; read-only, không source fetch, provider/Bot call, job, Xu/PayOS, media output hoặc publish."),
    WebFeature("story_video_plan", "Story Video Planner", "video", "/video-studio/story-video-plan", description="Story workflow và motion direction prompt-only chuyển từ Bot /story_video_factory + /story_motion_prompt; không provider/Bot call, job, Xu/PayOS, video output hoặc publish."),
    WebFeature("source_rights_guide", "Nguồn tư liệu & Dubbing hợp lệ", "content", "/guides/source-rights", description="Guide read-only chuyển từ Bot /source_help + /dubbing_help về nguồn, license, biên tập và voice-over; không xác minh quyền, provider/Bot call, job, Xu/PayOS, output hoặc publish."),
    WebFeature("media_workspace", "Audio Library & Briefing", "music", "/media-workspace", description="Kho audio Asset Vault và music/SFX brief riêng tư có collection, revision, policy guard và hướng prompt cục bộ; không phải provider catalog, AI generator hay output Bot."),
    WebFeature("music_prompt_composer", "Music Prompt Composer", "music", "/media-workspace/music-prompt-composer", description="Tạo ba hướng prompt nhạc deterministic để review; không lưu input, gọi Suno/provider, tạo lyrics/audio/preview/job, thanh toán, asset, collection hoặc Telegram action."),
    WebFeature("voice_studio", "Voice Studio & Consent Vault", "voice", "/voice-studio", description="Workspace profile direction, consent self-attestation, script, cue-sheet và revision Web-native; không clone/TTS/preview/audio output, provider, Bot job, Xu hoặc PayOS."),
    WebFeature("voice_direction_composer", "Voice Direction Composer", "voice", "/voice-studio/direction-composer", description="Gợi ý ba hướng thể hiện giọng đọc từ text bằng template deterministic; không lưu input/consent/audio/voice ID, không TTS/clone/preview/provider/job, wallet, thanh toán, asset hoặc Telegram action."),
    WebFeature("video_studio", "Video Production Studio", "video", "/video-studio", description="Plan, scene planner, thứ tự cảnh, self-review và version Web-native; chỉ lập kế hoạch cục bộ, không render, media output, provider, Bot job, Xu hoặc PayOS."),
    WebFeature("video_prompt_planner", "Video Prompt Planner", "video", "/video-studio/prompt-planner", description="Tạo direction video dạng text deterministic theo brief, shot, continuity và review checklist; không nhận source media, gọi provider, tạo video/preview/output/job, thanh toán hoặc publish."),
    WebFeature("video_idea_planner", "Video Idea Planner", "video", "/video-studio/idea-planner", description="Chuyển conversation Bot `videoidea` thành ba concept, storyboard sáu cảnh, image/video direction và Video Plan Draft Web-native; không tạo Telegram state, gọi Bot/bridge/provider, media/preview/output/job, Xu/PayOS, asset, publish hoặc delivery."),
    WebFeature("long_form_roadmap", "Long-form Video Roadmap", "video", "/video-studio/long-form-planner", description="Chuyển conversation Bot `longvideo` thành outline, character bible, chapter roadmap và prompt areas có thể review; lưu chỉ tạo Video Plan Web-owned, không tạo Telegram/Bot state, provider/media/output/job, Xu/PayOS, asset, publish hoặc delivery."),
    WebFeature("self_shot_scene_planner", "Self-shot Scene Planner", "video", "/video-studio/self-shot-planner", description="Chuyển phần text-planning của Bot `selfscene` thành direction scene, prompt video/keyframe, motion và audio notes có consent/right-to-use bắt buộc; không nhận hoặc mở media, Telegram/Bot state, bridge/provider/output/job, Xu/PayOS, asset, publish hoặc delivery. Lưu rõ ràng chỉ tạo Video Plan Web-owned được server recompute."),
    WebFeature("script_to_screen_planner", "Script-to-Screen Planner", "video", "/video-studio/script-to-screen-planner", description="Chuyển hai flow Task3D `vproduct` Script→Ảnh→Video và Phim dài tập thành script, storyboard, prompt ảnh/video, motion và review pack deterministic; không nhận media, gọi Bot/bridge/provider, tạo preview/output/job, đổi Xu/PayOS, asset, publish hoặc delivery. Lưu rõ ràng chỉ tạo Video Plan Web-owned được server recompute."),
    WebFeature("cinematic_ad_concept", "Cinematic Ad Concept Composer", "video", "/video-studio/cinematic-concept", description="Tạo concept quảng cáo, ba hướng sáng tạo, storyboard và hướng prompt deterministic từ brief text; không gọi provider, tạo media/preview/output/job, thanh toán, lưu asset hoặc publish."),
    WebFeature("image_motion_planner", "Image Motion Planner", "video", "/video-studio/image-motion-planner", description="Chuyển Image Studio direction có Image Vault reference thành motion plan 3 cảnh và Video Plan Draft owner-only; chỉ kiểm tra metadata/ownership, không mở ảnh, gọi provider/Bot, render, tạo media/output/job, thanh toán, asset mới hoặc publish."),
    WebFeature("reference_format_planner", "Reference Format Planner", "video", "/video-studio/reference-format-planner", description="Chuyển flow plan `videoref` của Bot thành plan 3 cảnh nguyên bản từ video Asset Vault owner-only; chỉ kiểm tra metadata, không mở/phân tích video, fetch link, gọi provider/Bot, render, tạo media/output/job, thanh toán hoặc publish."),
    WebFeature("storyboard_composer", "Storyboard Prompt Pack Composer", "video", "/video-studio/storyboard-composer", description="Tạo ba hướng storyboard, visual canon, shot pack và prompt ảnh/video/negative dạng text deterministic; không nhận media, gọi provider, tạo output/job, thanh toán, lưu asset hoặc publish."),
    WebFeature("subtitle_studio", "Subtitle & Transcript Workspace", "subtitle", "/subtitle-studio", description="Transcript project, cue timeline, SRT/VTT text preview, bản nháp ngôn ngữ, self-review và version Web-native; không ASR/TTS/dubbing/translation provider, upload, output, Bot job, Xu hoặc PayOS."),
    WebFeature("image_studio", "Image Creative Studio", "image", "/image-studio", description="Art direction, Asset Vault reference, biến thể, self-review và version Web-native; không gọi provider, tạo image/preview/output, job, Xu hoặc PayOS."),
    WebFeature("image_prompt_composer", "Image Prompt Composer", "image", "/image/prompt-composer", description="Soạn bản nháp prompt ảnh deterministic theo mục tiêu, phong cách và tỷ lệ; không đọc ảnh, gọi AI/provider, tạo media/output, lưu asset, job, Xu, PayOS hoặc publish."),
    WebFeature("caption", "Caption", "content", "/content/caption"),
    WebFeature("hashtag", "Hashtag", "content", "/content/hashtag"),
    WebFeature("hook", "Hook", "content", "/content/hook"),
    WebFeature("script", "Kịch bản", "content", "/content/script"),
    WebFeature("storyboard", "Storyboard", "content", "/content/storyboard"),
    WebFeature("content_pack", "Content Pack", "content", "/content/pack"),
    WebFeature("growth_ai", "Growth Review", "content", "/growth/ai", description="Chấm điểm và gợi ý rule-based từ số liệu bạn tự nhập, chuyển đúng helper deterministic của Bot nhưng không gọi AI/Bot, không đọc analytics live hoặc doanh thu canonical."),
    WebFeature("campaign_report", "Báo cáo campaign", "content", "/campaign/report", description="Báo cáo campaign/text/CSV tiếp tục được Bot canonical tạo và gửi trong Telegram."),
    WebFeature("image_create", "Tạo ảnh", "image", "/image/create", input_hint="Prompt ảnh và tỉ lệ khung hình."),
    WebFeature("image_edit", "Image Enhance Studio", "image", "/image/edit", description="Chỉnh màu và làm nét cơ bản deterministic từ Asset Vault; không phải AI edit, Bot job hay provider call."),
    WebFeature("image_resize", "Resize & Aspect Studio", "image", "/image/resize", description="Tạo PNG private từ Asset Vault bằng crop, pad hoặc blur nền có kiểm tra; không phải AI upscale, Bot job hay provider call."),
    WebFeature("image_brand_overlay", "Brand Overlay Studio", "image", "/image/brand-overlay", description="Thêm chữ thương hiệu hoặc logo private vào bản sao PNG Web-native đã kiểm tra; không phải AI edit, Bot job hay provider call."),
    WebFeature("image_storyboard_grid", "Storyboard Grid Splitter", "image", "/image/storyboard-grid", description="Tách một ảnh Asset Vault private thành JPEG scene ZIP/manifest deterministic theo lưới storyboard; không phải AI, Bot job, provider call, Xu hoặc PayOS."),
    WebFeature("image_upscale", "Nâng cấp ảnh", "image", "/image/upscale", input_hint="Tải ảnh cần upscale."),
    WebFeature("image_transform", "Image-to-image", "image", "/image/transform", input_hint="Ảnh nguồn và mô tả biến thể."),
    WebFeature("image_remove_background", "Xóa nền", "image", "/image/remove-background", input_hint="Tải ảnh cần xử lý."),
    WebFeature("image_history", "Lịch sử ảnh", "image", "/image/history", input_hint="PNG Resize & Image Enhance riêng tư do Web Workspace đã xác minh; không bao gồm job/output Bot hoặc provider."),
    WebFeature("video_single", "Video nhanh", "video", "/video/create", input_hint="Prompt hoặc brief video."),
    WebFeature("video_image_to_video", "Ảnh thành video", "video", "/video/image-to-video", input_hint="Ảnh nguồn và chuyển động mong muốn."),
    WebFeature("video_product", "Video sản phẩm", "video", "/video/product", input_hint="Thông tin sản phẩm và hình ảnh."),
    WebFeature("video_trend", "Video theo trend", "video", "/video/trend", input_hint="Trend hoặc tham chiếu an toàn."),
    WebFeature("video_text_to_video", "Text-to-video", "video", "/video/text-to-video", input_hint="Prompt video và tham số đã xác minh."),
    WebFeature("video_quick", "Quick video", "video", "/video/quick", input_hint="Brief video ngắn."),
    WebFeature("video_multiscene", "Video nhiều cảnh", "video", "/video/multiscene", input_hint="Brief, cảnh và giọng đọc."),
    WebFeature("video_long", "Video dài", "video", "/video/long", input_hint="Dự án video dài."),
    WebFeature("video_progress", "Tiến độ video", "video", "/video/progress"),
    WebFeature("video_preview", "Xem trước video", "video", "/video/preview"),
    WebFeature("video_export", "Xuất video", "video", "/video/export"),
    WebFeature("video_addons", "Video add-ons", "video", "/video/add-ons"),
    WebFeature("video_mux", "Mux audio/video", "video", "/video/mux"),
    WebFeature("voice_tts", "Giọng đọc", "voice", "/voice/create", input_hint="Văn bản và giọng đọc."),
    WebFeature("voice_clone", "Clone giọng", "voice", "/voice/clone", input_hint="Mẫu âm thanh đã được phép sử dụng."),
    WebFeature("voice_saved_tts", "Giọng đã lưu", "voice", "/voice/saved", input_hint="Chọn voice vault."),
    WebFeature("voice_vault", "Voice vault", "voice", "/voice"),
    WebFeature("voice_preview", "Nghe thử giọng", "voice", "/voice/preview"),
    WebFeature("voice_outputs", "Voice outputs", "voice", "/voice/outputs"),
    WebFeature("music_library", "Thư viện nhạc", "music", "/music/library"),
    WebFeature("sfx_library", "Thư viện SFX", "music", "/music/sfx-library", description="Tài sản hiệu ứng âm thanh thuộc phiên đã được Core Bridge xác minh."),
    WebFeature("music_background", "Nhạc nền AI", "music", "/music/ai", input_hint="Phong cách, mood và thời lượng."),
    WebFeature("music_song", "Bài hát AI", "music", "/music/song", input_hint="Lời, phong cách và chế độ half/full."),
    WebFeature("music_sfx", "SFX", "music", "/music/sfx", input_hint="Brief hiệu ứng âm thanh."),
    WebFeature("music_upload", "Nhạc của tôi", "music", "/music/upload"),
    WebFeature("subtitle_asr", "Tạo phụ đề", "subtitle", "/subtitle", input_hint="Tải video hoặc audio."),
    WebFeature("subtitle_create", "Tạo phụ đề", "subtitle", "/subtitle/create", input_hint="Tải video hoặc audio."),
    WebFeature("subtitle_translate", "Dịch phụ đề", "subtitle", "/translate", input_hint="Tải SRT/VTT hoặc nhập văn bản."),
    WebFeature("video_dub", "Lồng tiếng", "subtitle", "/dubbing", input_hint="Media nguồn, ngôn ngữ và giọng đọc."),
    WebFeature("asr", "Nhận dạng giọng nói", "subtitle", "/asr", input_hint="Tải audio hoặc video."),
    WebFeature("subtitle_formats", "SRT/VTT", "subtitle", "/subtitle/formats", description="Chuyển đổi text SRT↔VTT hoặc tạo SRT từ text bằng Web-native Format Lab; không upload, ASR, dịch, TTS, dubbing, provider, job, payment hoặc file delivery."),
    WebFeature("documents", "Tài liệu & PDF", "documents", "/documents", input_hint="Tải tài liệu để chọn công cụ."),
    WebFeature("documents_pdf", "PDF tools", "documents", "/documents/pdf"),
    WebFeature("documents_ocr", "OCR ảnh private", "documents", "/documents/ocr", description="Trích xuất text từ một JPEG/PNG/WebP private trong Asset Vault bằng local Tesseract có cờ riêng; chỉ phát TXT sau khi kiểm tra output, không gọi Bot/provider/job/Xu/PayOS."),
    WebFeature("documents_pdf_ocr", "OCR PDF private", "documents", "/documents/pdf-ocr", description="Trích xuất text từ PDF private trong Asset Vault bằng local Tesseract có cờ riêng, giới hạn trang và delivery TXT được kiểm tra; không gọi Bot/provider/job/Xu/PayOS."),
    WebFeature("documents_pdf_ocr_word", "OCR PDF → Word private", "documents", "/documents/pdf-ocr-to-word", description="Đọc text từ PDF scan private bằng local OCR có cờ riêng rồi chỉ phát DOCX đã kiểm tra; không preview raw text, không gọi Bot/provider/job/Xu/PayOS."),
    WebFeature("documents_merge", "Gộp PDF", "documents", "/documents/merge", description="Gộp PDF private từ Asset Vault qua Web-native operation có thứ tự nguồn rõ ràng và output attachment được kiểm tra; không tạo Bot job hoặc charge."),
    WebFeature("documents_split", "Tách PDF", "documents", "/documents/split", description="Tách PDF private từ Asset Vault qua Web-native operation có output attachment được kiểm tra; không tạo Bot job hoặc charge."),
    WebFeature("documents_compress", "Tối ưu PDF", "documents", "/documents/compress", description="Tối ưu cấu trúc PDF private từ Asset Vault bằng Web-native lossless operation; chỉ phát output khi artifact cuối cùng nhỏ hơn thật, không tạo Bot job hoặc charge."),
    WebFeature("documents_image_to_pdf", "Ảnh sang PDF", "documents", "/documents/image-to-pdf", description="Chuyển ảnh private từ Asset Vault thành PDF Web-native theo thứ tự rõ ràng, với decoder và output attachment được kiểm tra; không tạo Bot job hoặc charge."),
    WebFeature("documents_pdf_to_images", "PDF sang ảnh", "documents", "/documents/pdf-to-images", description="Render PDF private trong Asset Vault thành PNG hoặc ZIP Web-native với kiểm tra pixel, output và private delivery; không tạo Bot job hoặc charge."),
    WebFeature("documents_pdf_to_word", "PDF có text → Word", "documents", "/documents/pdf-to-word", description="Trích xuất text có thể chọn thực sự từ PDF private trong Asset Vault thành DOCX Web-native; không OCR và không cam kết giữ bố cục trực quan."),
    WebFeature("documents_translate", "Dịch tài liệu", "documents", "/documents/translate"),
    WebFeature("support", "Hỗ trợ", "support", "/support"),
    WebFeature("tickets", "Phiếu hỗ trợ", "support", "/tickets"),
    WebFeature("operations", "Operations Autopilot", "support", "/operations", description="Tình trạng quan sát, phân loại SLA và incident Web-native có kiểm soát; không tự hoàn tiền, trả lời khách, gọi provider hoặc deploy."),
    WebFeature("pricing", "Bảng giá", "support", "/pricing"),
    WebFeature("service_status", "Trạng thái dịch vụ", "support", "/status", description="Trạng thái Web, Telegram và Core Bridge đã được server kiểm tra."),
    WebFeature("tool_directory", "Công cụ & models", "content", "/tools", description="Danh mục workflow và models đã được định tuyến, không suy đoán readiness."),
    WebFeature("media_studio", "Media Studio", "video", "/studio", description="Luồng lập kế hoạch media qua các workflow Web đã đăng ký."),
    WebFeature("legal", "Điều khoản", "support", "/legal"),
    WebFeature("privacy", "Quyền riêng tư", "support", "/privacy"),
)

ADMIN_FEATURES: tuple[WebFeature, ...] = (
    WebFeature("admin_overview", "Tổng quan vận hành", "admin", "/admin", "admin"),
    WebFeature("admin_users", "Người dùng", "admin", "/admin/users", "admin"),
    WebFeature("admin_wallet", "Ví & Xu", "admin", "/admin/wallet", "admin"),
    WebFeature("admin_payments", "Thanh toán", "admin", "/admin/payments", "admin"),
    WebFeature("admin_topups", "Nạp Xu", "admin", "/admin/topups", "admin"),
    WebFeature("admin_revenue", "Doanh thu", "admin", "/admin/revenue", "admin"),
    WebFeature("admin_jobs", "Jobs", "admin", "/admin/jobs", "admin"),
    WebFeature("admin_refunds", "Hoàn tiền", "admin", "/admin/refunds", "admin"),
    WebFeature("admin_providers", "Nhà cung cấp", "admin", "/admin/providers", "admin"),
    WebFeature("admin_provider_cost", "Chi phí provider", "admin", "/admin/provider-cost", "admin"),
    WebFeature("admin_workers", "Workers", "admin", "/admin/workers", "admin"),
    WebFeature("admin_features", "Readiness", "admin", "/admin/features", "admin"),
    WebFeature("admin_freezes", "Bảo trì & freeze", "admin", "/admin/freezes", "admin"),
    WebFeature("admin_pricing", "Giá & gói", "admin", "/admin/pricing", "admin"),
    WebFeature("admin_promos", "Khuyến mãi", "admin", "/admin/promos", "admin"),
    WebFeature("admin_leads", "Leads", "admin", "/admin/leads", "admin"),
    WebFeature("admin_tickets", "CSKH", "admin", "/admin/tickets", "admin"),
    WebFeature("admin_operations", "Operations Autopilot", "admin", "/admin/operations", "admin"),
    WebFeature("admin_reliability", "Reliability Follow-up", "admin", "/admin/reliability", "admin"),
    WebFeature("admin_campaigns", "Campaign Center", "admin", "/admin/campaigns", "admin"),
    WebFeature("admin_calendar", "Content Calendar", "admin", "/admin/calendar", "admin"),
    WebFeature("admin_approvals", "Approval Queue", "admin", "/admin/approvals", "admin"),
    WebFeature("admin_publishing", "Publishing & Channels", "admin", "/admin/publishing", "admin"),
    WebFeature("admin_analytics", "Analytics", "admin", "/admin/analytics", "admin"),
    WebFeature("admin_growth", "Growth & Affiliate", "admin", "/admin/growth", "admin"),
    WebFeature("admin_finance", "Finance & Revenue", "admin", "/admin/finance", "admin"),
    WebFeature("admin_trends", "Trends & Reference", "admin", "/admin/trends", "admin"),
    WebFeature("admin_audit", "Nhật ký audit", "admin", "/admin/audit", "admin"),
    WebFeature("admin_internal_documents", "Kho hồ sơ nội bộ", "admin", "/admin/internal-documents", "admin", description="Kho hồ sơ Web-native riêng cho local admin: blob private, phiên bản bất biến, metadata/audit và download kiểm tra integrity; tách khỏi Bot, Asset Vault khách hàng và Governance Documents."),
    WebFeature("admin_reports", "Báo cáo", "admin", "/admin/reports", "admin"),
    WebFeature("admin_system", "Hệ thống", "admin", "/admin/system", "admin"),
    WebFeature("admin_runtime", "Runtime", "admin", "/admin/runtime", "admin"),
    WebFeature("admin_backups", "Sao lưu", "admin", "/admin/backups", "admin"),
)

ALL_FEATURES: tuple[WebFeature, ...] = CUSTOMER_FEATURES + ADMIN_FEATURES
FEATURE_BY_KEY = {item.key: item for item in ALL_FEATURES}

# A small, reviewed subset of the Web catalog that can be used as a genuine
# application navigation menu.  It deliberately excludes raw Telegram button
# labels, pending-state transitions, provider controls, canonical wallet
# writes and administrative actions.  ``availability`` describes the Web
# navigation boundary only; it never indicates execution readiness.
MENU_CAPABILITIES: tuple[MenuCapability, ...] = (
    MenuCapability(
        "workspace_home",
        "dashboard",
        "SIGNED_CUSTOMER",
        "NAVIGATION_SHELL",
        "NAVIGATION_ONLY",
        "Mở workspace chính đã xác thực; không khôi phục menu hoặc state Telegram.",
    ),
    MenuCapability(
        "account",
        "account",
        "SIGNED_CUSTOMER",
        "WEB_NAVIGATION",
        "NAVIGATION_ONLY",
        "Hồ sơ và bảo mật Web theo signed session, tách khỏi callback Bot.",
    ),
    MenuCapability(
        "chat_workspace",
        "chat",
        "SIGNED_CUSTOMER_WEB_NATIVE",
        "WEB_NAVIGATION",
        "NAVIGATION_ONLY",
        "Mở AI Chat Workspace riêng của Web; không nhập hội thoại, context hoặc pending state Telegram.",
    ),
    MenuCapability(
        "prompt_studio",
        "prompt_studio",
        "SIGNED_CUSTOMER_WEB_NATIVE",
        "WEB_NAVIGATION",
        "NAVIGATION_ONLY",
        "Mở Prompt Studio Web-native để soạn brief mới; không gọi AI, Bot, provider, job, ví hoặc PayOS chỉ bằng điều hướng.",
    ),
    MenuCapability(
        "wallet",
        "wallet",
        "CORE_CANONICAL_READ",
        "READ_ONLY_CANONICAL",
        "GUARDED",
        "Mở số dư và lịch sử Xu canonical theo signed owner; không tạo checkout, cộng Xu, đổi giá hoặc xử lý webhook.",
    ),
    MenuCapability(
        "wallet_topup",
        "wallet_topup",
        "CORE_CANONICAL_PAYMENT",
        "BRIDGE_GUARDED_PROXY",
        "GUARDED",
        "Mở bề mặt nạp Xu canonical có guard; request đi qua core bridge, còn Web không tự định giá, cộng Xu hoặc xử lý webhook PayOS.",
    ),
    MenuCapability(
        "documents",
        "documents",
        "SIGNED_CUSTOMER",
        "WEB_NAVIGATION",
        "NAVIGATION_ONLY",
        "Mở Document & PDF Workspace; từng thao tác file vẫn tự kiểm tra quyền và capability riêng.",
    ),
    MenuCapability(
        "documents_pdf_to_word",
        "documents_pdf_to_word",
        "SIGNED_CUSTOMER_WEB_NATIVE",
        "WEB_NAVIGATION",
        "NAVIGATION_ONLY",
        "Mở PDF có text → Word từ Asset Vault Web-owned; không nhận file/pending state Telegram.",
    ),
    MenuCapability(
        "documents_image_to_pdf",
        "documents_image_to_pdf",
        "SIGNED_CUSTOMER_WEB_NATIVE",
        "WEB_NAVIGATION",
        "NAVIGATION_ONLY",
        "Mở Image → PDF từ Asset Vault Web-owned; nguồn, thứ tự và delivery được xác minh trong workflow riêng.",
    ),
    MenuCapability(
        "documents_compress",
        "documents_compress",
        "SIGNED_CUSTOMER_WEB_NATIVE",
        "WEB_NAVIGATION",
        "NAVIGATION_ONLY",
        "Mở PDF Optimize Web-native; không dùng lựa chọn nén hoặc file chờ của Telegram.",
    ),
    MenuCapability(
        "documents_split",
        "documents_split",
        "SIGNED_CUSTOMER_WEB_NATIVE",
        "WEB_NAVIGATION",
        "NAVIGATION_ONLY",
        "Mở PDF Split Web-native với source/ownership riêng; không nhập page range Telegram.",
    ),
    MenuCapability(
        "documents_merge",
        "documents_merge",
        "SIGNED_CUSTOMER_WEB_NATIVE",
        "WEB_NAVIGATION",
        "NAVIGATION_ONLY",
        "Mở PDF Merge Web-native với thứ tự source do signed owner xác nhận; không nhập file queue Telegram.",
    ),
    MenuCapability(
        "asset_vault",
        "asset_vault",
        "SIGNED_CUSTOMER_WEB_NATIVE",
        "WEB_NAVIGATION",
        "NAVIGATION_ONLY",
        "Mở Asset Vault riêng của Web; không đại diện cho quota, add-on hoặc storage settlement canonical của Bot.",
    ),
    MenuCapability(
        "image_studio",
        "image_studio",
        "SIGNED_CUSTOMER_WEB_NATIVE",
        "WEB_NAVIGATION",
        "NAVIGATION_ONLY",
        "Mở Image Creative Studio Web-native, không tạo ảnh hay gọi provider chỉ bằng điều hướng.",
    ),
    MenuCapability(
        "image_prompt_composer",
        "image_prompt_composer",
        "SIGNED_CUSTOMER_WEB_NATIVE",
        "WEB_NAVIGATION",
        "NAVIGATION_ONLY",
        "Mở Image Prompt Composer để soạn prompt mới; không nhận ảnh/pending state Telegram hoặc gọi provider.",
    ),
    MenuCapability(
        "image_edit",
        "image_edit",
        "SIGNED_CUSTOMER_WEB_NATIVE",
        "WEB_NAVIGATION",
        "NAVIGATION_ONLY",
        "Mở Image Enhance Studio riêng của Web; workflow tự chọn Asset Vault input và không dùng ảnh chờ Telegram.",
    ),
    MenuCapability(
        "image_upscale",
        "image_upscale",
        "SIGNED_CUSTOMER_WEB_NATIVE",
        "WEB_NAVIGATION",
        "NAVIGATION_ONLY",
        "Mở bề mặt Image Upscale có guard riêng; không gọi provider hoặc mang ảnh/pending state Telegram qua browser.",
    ),
    MenuCapability(
        "video_studio",
        "video_studio",
        "SIGNED_CUSTOMER_WEB_NATIVE",
        "WEB_NAVIGATION",
        "NAVIGATION_ONLY",
        "Mở Video Production Studio để lập kế hoạch; không nhập state Telegram hoặc khởi tạo render.",
    ),
    MenuCapability(
        "media_workspace",
        "media_workspace",
        "SIGNED_CUSTOMER_WEB_NATIVE",
        "WEB_NAVIGATION",
        "NAVIGATION_ONLY",
        "Mở Audio Library & Briefing Web-native; không dùng product context hoặc thư viện Bot.",
    ),
    MenuCapability(
        "guides",
        "guides",
        "SIGNED_CUSTOMER",
        "WEB_NAVIGATION",
        "NAVIGATION_ONLY",
        "Mở guide Web; nội dung không cấp quyền chạy workflow Bot.",
    ),
    MenuCapability(
        "pricing",
        "pricing",
        "SIGNED_CUSTOMER",
        "WEB_NAVIGATION",
        "NAVIGATION_ONLY",
        "Mở bảng giá Web để tham khảo; không tạo order, thay đổi giá, cộng Xu hoặc xử lý PayOS.",
    ),
    MenuCapability(
        "support",
        "support",
        "SIGNED_CUSTOMER",
        "WEB_NAVIGATION",
        "NAVIGATION_ONLY",
        "Mở Support Desk owner-scoped, không chuyển ticket hoặc callback Telegram.",
    ),
    MenuCapability(
        "media_factory",
        "media_factory",
        "SIGNED_CUSTOMER_WEB_NATIVE",
        "WEB_NAVIGATION",
        "NAVIGATION_ONLY",
        "Mở Media Factory Blueprint; không tạo media, job, provider call hoặc publish.",
    ),
    MenuCapability(
        "video_factory_workflow",
        "video_factory_workflow",
        "SIGNED_CUSTOMER_WEB_NATIVE",
        "WEB_NAVIGATION",
        "NAVIGATION_ONLY",
        "Mở bản đồ Video Factory Web-native; đây là điều hướng/read-only, không phải execution flow.",
    ),
)
MENU_CAPABILITY_BY_KEY = {item.key: item for item in MENU_CAPABILITIES}


def catalog() -> list[dict[str, str]]:
    return [asdict(item) for item in ALL_FEATURES]


def menu_capability_catalog() -> list[dict[str, str]]:
    """Return browser-safe menu destinations without Bot callback metadata.

    The registry itself is a closed local allow-list.  Constructing each item
    from ``FEATURE_BY_KEY`` prevents a stale menu entry from emitting a route
    that is not an actual Web feature.  The returned values are static product
    metadata; callers must still enforce their own signed-session, CSRF, role,
    ownership and runtime checks.
    """

    entries: list[dict[str, str]] = []
    for item in MENU_CAPABILITIES:
        feature = FEATURE_BY_KEY[item.feature_key]
        entries.append(
            {
                "key": item.key,
                "feature_key": feature.key,
                "title": feature.title,
                "group": feature.group,
                "route": feature.route,
                "authority": item.authority,
                "launch_mode": item.launch_mode,
                "availability": item.availability,
                "execution": "NO_EXECUTION_CLAIM",
                "description": item.description,
            }
        )
    return entries


def allowed_paths() -> set[str]:
    # These are Web-owned portal surfaces, not Bot feature adapters.  Keep
    # them explicit instead of smuggling them into the canonical Bot catalog.
    # `/welcome` is intentionally separate from the application root. The
    # root redirects into secure app access, while this explicit route keeps a
    # lightweight public product introduction available when needed.
    result = {"/", "/welcome", "/login", "/register", "/onboarding", "/campaigns", "/calendar", "/approvals"}
    for item in ALL_FEATURES:
        result.add(item.route.split("?", 1)[0])
    return result


def feature_keys() -> Iterable[str]:
    return FEATURE_BY_KEY.keys()
