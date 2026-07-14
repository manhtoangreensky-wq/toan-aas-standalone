/*
 * TOAN AAS portal shell
 *
 * This file is intentionally presentation-only. It performs no fetch, no
 * storage access, no provider call and no payment action. FastAPI injects a
 * server-derived signed-session bootstrap into window.__TOAN_AAS_PORTAL__.
 * A bridge integration can listen for the `toanaas:portal-action` event.
 */
(function portalShell() {
  "use strict";

  const ACTION_EVENT = "toanaas:portal-action";
  let interactionsBound = false;
  const transientFormDrafts = new Map();
  const transientWorkspaceDraftIds = new Map();
  let sidebarReturnFocus = null;
  let commandPaletteReturnFocus = null;
  try {
    const bootstrap = document.getElementById("portal-bootstrap");
    const parsed = bootstrap && JSON.parse(bootstrap.textContent || "{}");
    if (parsed && typeof parsed === "object") window.__TOAN_AAS_PORTAL__ = parsed;
  } catch (_) {
    window.__TOAN_AAS_PORTAL__ = window.__TOAN_AAS_PORTAL__ || {};
  }
  const ALLOWED_STATES = new Set([
    "ready", "draft", "awaiting_confirm", "queued", "processing",
    "completed", "failed", "failed_no_charge", "cancelled", "refunded", "review", "approved", "scheduled", "archived", "unavailable", "guarded", "disabled", "read_only", "error", "empty",
    // Web Support Desk owns its own case lifecycle.  These are not job,
    // provider, wallet or Telegram statuses.
    "new", "reviewing", "waiting_user", "waiting_provider", "refund_pending", "resolved", "closed"
  ]);

  const STATE_LABELS = Object.freeze({
    ready: "Sẵn sàng",
    draft: "Bản nháp",
    awaiting_confirm: "Chờ xác nhận",
    queued: "Đã xếp hàng",
    processing: "Đang xử lý",
    completed: "Hoàn tất",
    unavailable: "Không khả dụng",
    review: "Tự rà soát",
    approved: "Đã sẵn sàng",
    scheduled: "Đã xếp lịch",
    archived: "Đã lưu trữ",
    new: "Yêu cầu mới",
    reviewing: "Đang rà soát",
    waiting_user: "Chờ bạn phản hồi",
    waiting_provider: "Chờ đối tác xác minh",
    refund_pending: "Đang xem xét hoàn tiền",
    resolved: "Đã xử lý",
    closed: "Đã đóng",
    cancelled: "Đã hủy",
    refunded: "Đã hoàn Xu",
    read_only: "Chỉ đọc",
    failed: "Thất bại",
    failed_no_charge: "Thất bại · chưa trừ Xu",
    guarded: "Được bảo vệ",
    disabled: "Tạm khóa",
    error: "Lỗi kết nối",
    empty: "Chưa có dữ liệu"
  });

  const PAYMENT_STATUS_LABELS = Object.freeze({
    draft: "Khởi tạo",
    awaiting_confirm: "Chờ xác nhận",
    queued: "Chờ thanh toán",
    processing: "Đang đối soát",
    completed: "Đã thanh toán",
    failed: "Không thành công",
    cancelled: "Đã hủy",
    refunded: "Đã hoàn tiền",
    guarded: "Được bảo vệ",
    read_only: "Chỉ đọc"
  });

  const ICONS = Object.freeze({
    dashboard: "⌂", account: "◉", wallet: "◌", jobs: "⌛", assets: "▣", package: "▤",
    chat: "◒", prompt: "✦", image: "◩", video: "▶", voice: "◖", music: "♫",
    subtitle: "≡", document: "▤", support: "?", pricing: "◇", legal: "§",
    admin: "⌘", users: "◎", payments: "◈", providers: "◫", system: "⚙",
    reports: "◒", security: "◈", ticket: "✉", default: "·"
  });

  // These actions write only Web-owned data.  They never need a provider/Core
  // Bridge connection and must not inherit a false "Bot is running" promise
  // from the broader feature workflow UI.
  const WEB_LOCAL_ACTIONS = new Set([
    "campaign-create", "campaign-update", "campaign-update-status",
    "support-case-create", "support-case-reply", "support-case-close", "support-case-reopen",
    "support-admin-case-reply", "support-admin-case-update"
  ]);

  const LANGUAGE_OPTIONS = Object.freeze([
    { value: "vi", label: "Tiếng Việt" }, { value: "en", label: "English" },
    { value: "zh", label: "中文" }, { value: "zh_cn", label: "中文简体" }, { value: "zh_tw", label: "中文繁體" },
    { value: "ja", label: "日本語" }, { value: "ko", label: "한국어" }, { value: "th", label: "ไทย" },
    { value: "fr", label: "Français" }, { value: "de", label: "Deutsch" }, { value: "es", label: "Español" },
    { value: "id", label: "Indonesia" }, { value: "ms", label: "Malay" }, { value: "pt", label: "Português" },
    { value: "ru", label: "Русский" }, { value: "ar", label: "العربية" }, { value: "hi", label: "हिन्दी" },
    { value: "lo", label: "ລາວ" }, { value: "km", label: "ខ្មែរ" }, { value: "my", label: "Burmese" },
    { value: "fil", label: "Filipino" }, { value: "auto", label: "Tự nhận diện" }
  ]);

  const FIELD_SETS = Object.freeze({
    authLogin: [
      { name: "email", label: "Email (có thể dùng Gmail)", type: "email", placeholder: "you@example.com", autocomplete: "email", required: true, maxLength: 254, help: "Dùng Email + mật khẩu đã tạo tài khoản. Google (OAuth) là một phương thức riêng và chỉ được bật khi server có cấu hình OAuth." },
      { name: "password", label: "Mật khẩu", type: "password", placeholder: "Nhập mật khẩu", autocomplete: "current-password", required: true, maxLength: 256 }
    ],
    authRegister: [
      { name: "name", label: "Tên hiển thị", placeholder: "Tên bạn muốn dùng", autocomplete: "name", maxLength: 120, help: "Có thể để trống; khi liên kết Telegram, bot chỉ cập nhật tên hiển thị đã được xác minh." },
      { name: "email", label: "Email (có thể dùng Gmail)", type: "email", placeholder: "you@example.com", autocomplete: "email", required: true, maxLength: 254, help: "Đây là phương thức Email + mật khẩu; địa chỉ Gmail được hỗ trợ như một email bình thường. Google (OAuth) là một phương thức riêng." },
      { name: "password", label: "Mật khẩu", type: "password", placeholder: "Tối thiểu 12 ký tự", autocomplete: "new-password", required: true, minLength: 12, maxLength: 256 },
      { name: "confirm_password", label: "Xác nhận mật khẩu", type: "password", placeholder: "Nhập lại mật khẩu", autocomplete: "new-password", required: true, minLength: 12, maxLength: 256 }
    ],
    telegramAccountUpgrade: [
      { name: "email", label: "Email đăng nhập (có thể dùng Gmail)", type: "email", placeholder: "you@example.com", autocomplete: "email", required: true, maxLength: 254, help: "Thêm Email + mật khẩu vào đúng tài khoản Telegram đang đăng nhập; không ghép tự động với tài khoản Web khác." },
      { name: "password", label: "Mật khẩu mới", type: "password", placeholder: "Tối thiểu 12 ký tự", autocomplete: "new-password", required: true, minLength: 12, maxLength: 256 },
      { name: "confirm_password", label: "Xác nhận mật khẩu mới", type: "password", placeholder: "Nhập lại mật khẩu", autocomplete: "new-password", required: true, minLength: 12, maxLength: 256 }
    ],
    prompt: [
      { name: "request", label: "Yêu cầu", control: "textarea", placeholder: "Mô tả nội dung bạn muốn tạo…", help: "Bản nháp chỉ được chuyển khi phiên, CSRF và Core Bridge đã được máy chủ cấp. Các helper content/prompt P0 hiện trả bản nháp tiếng Việt; chọn ngôn ngữ chỉ xuất hiện khi bridge có contract riêng. Viết brief rõ hơn để có draft hữu ích hơn.", required: true, minLength: 1 }
    ],
    // These names intentionally mirror the pure storyboard helper exposed by
    // the frozen Bot P0 bridge.  Keep `duration` (rather than only a display
    // value) because the canonical helper reads this exact input when it
    // builds the planning pack.
    contentStoryboard: [
      { name: "request", label: "Chủ đề / brief", control: "textarea", placeholder: "Mục tiêu, câu chuyện, sản phẩm và thông điệp chính…", required: true, minLength: 1 },
      { name: "template", label: "Mẫu storyboard", control: "select", options: ["product_ad", "ugc", "story", "explainer"], help: "Tuỳ chọn planning; Bot dùng product_ad khi chưa có mẫu." },
      { name: "platform", label: "Kênh phát hành", control: "select", options: ["TikTok", "YouTube", "Facebook", "Instagram", "Khác"], help: "Tuỳ chọn planning để gợi ý ngữ cảnh phát hành." },
      { name: "format", label: "Tỷ lệ khung hình", control: "select", options: ["9:16", "16:9", "1:1", "4:5"], help: "Tuỳ chọn planning; chưa phải cam kết output." },
      { name: "duration", label: "Thời lượng mục tiêu (giây)", type: "number", placeholder: "Ví dụ: 30", min: 1, max: 600, step: 1, inputMode: "numeric", help: "Tuỳ chọn planning; Bot có thể lập draft trước khi biết thời lượng." },
      { name: "style", label: "Phong cách", placeholder: "Ví dụ: rõ nhịp, hiện đại, có phụ đề dễ đọc" },
      { name: "goal", label: "Mục tiêu / CTA", placeholder: "Ví dụ: giới thiệu sản phẩm và dẫn về trang mua" },
      { name: "notes", label: "Ghi chú", control: "textarea", placeholder: "Yêu cầu thương hiệu, điểm bắt buộc hoặc giới hạn an toàn…" }
    ],
    imageCreate: [
      { name: "prompt", label: "Mô tả hình ảnh", control: "textarea", placeholder: "Chủ thể, phong cách, bối cảnh, tỷ lệ…", required: true, minLength: 1 },
      { name: "tier", label: "Tier ảnh", control: "select", optionsFrom: "imageTiers", emptyLabel: "Để Bot trả lựa chọn tier canonical", help: "Có thể để trống khi tạo draft/khám phá quote. Trước confirm, Bot canonical phải xác nhận tier. Không nhập Xu hoặc giá thủ công." },
      { name: "format", label: "Ưu tiên tỷ lệ khi chạy", control: "select", options: ["1:1", "4:5", "16:9", "9:16"], help: "Bản nháp P0 hiện chỉ sinh gợi ý 1:1 và 9:16. Lựa chọn này là preference được lưu cho adapter image canonical tương lai, không phải xác nhận output." }
    ],
    imageSource: [
      { name: "instructions", label: "Yêu cầu xử lý", control: "textarea", placeholder: "Ví dụ: giữ chủ thể, nâng độ nét, xóa nền…", help: "Estimate dùng tier canonical; output vẫn chỉ xuất hiện sau delivery hợp lệ." },
      { name: "tier", label: "Tier ảnh", control: "select", optionsFrom: "imageTiers", emptyLabel: "Để Bot trả lựa chọn tier canonical", help: "Có thể để trống khi khám phá quote; confirm tương lai cần tier canonical." },
      { name: "source", label: "Ảnh nguồn", type: "file", accept: "image/jpeg,image/png,image/webp", requiredUpload: true, help: "Ảnh chỉ vào staging canonical sau kiểm tra MIME, chữ ký, kích thước và ownership." }
    ],
    imageTransform: [
      { name: "prompt", label: "Mô tả biến thể", control: "textarea", placeholder: "Giữ chủ thể, thay đổi phong cách, bối cảnh hoặc ánh sáng…", required: true, minLength: 1 },
      { name: "tier", label: "Tier ảnh", control: "select", optionsFrom: "imageTiers", emptyLabel: "Để Bot trả lựa chọn tier canonical", help: "Có thể để trống khi tạo draft/khám phá quote." },
      { name: "format", label: "Tỷ lệ khung hình", control: "select", options: ["1:1", "4:5", "16:9", "9:16"] },
      { name: "source", label: "Ảnh nguồn", type: "file", accept: "image/jpeg,image/png,image/webp", requiredUpload: true, help: "Image-to-Image chỉ tiếp tục khi ảnh thuộc tài khoản đã vào staging canonical; browser không gửi ảnh tới provider." }
    ],
    videoContextual: [
      { name: "brief", label: "Brief video", control: "textarea", placeholder: "Mục tiêu, cảnh, chuyển động, giọng đọc…", required: true, minLength: 1 },
      { name: "tier", label: "Tier video", control: "select", optionsFrom: "videoTiers", emptyLabel: "Để Bot trả lựa chọn tier canonical", help: "Có thể để trống khi tạo draft/khám phá quote. Confirm tương lai cần tier Bot xác nhận; không nhập giá hoặc Xu." },
      { name: "scene_count", label: "Số cảnh", type: "number", placeholder: "Ví dụ: 3", help: "Có thể để trống khi lập draft; Bot cần số cảnh hợp lệ trước khi tạo job để áp dụng giảm giá canonical.", min: 1, max: 20, step: 1, inputMode: "numeric" },
      { name: "duration_seconds", label: "Thời lượng mục tiêu (giây)", type: "number", placeholder: "Ví dụ: 15", min: 1, max: 600, step: 1, inputMode: "numeric", help: "Tuỳ chọn planning; không phải thời lượng output cam kết." },
      { name: "platform", label: "Kênh phát hành", control: "select", options: ["TikTok", "YouTube", "Facebook", "Instagram", "Khác"] },
      { name: "format", label: "Tỷ lệ khung hình", control: "select", options: ["9:16", "16:9", "1:1", "4:5"] },
      { name: "goal", label: "Mục tiêu / CTA", placeholder: "Ví dụ: giới thiệu sản phẩm và dẫn về trang mua" },
      { name: "source", label: "Tệp / hình nguồn (tuỳ chọn)", type: "file", accept: "image/jpeg,image/png,image/webp,video/mp4,video/quicktime,video/webm", help: "Tệp chỉ vào staging canonical sau kiểm tra MIME, chữ ký, kích thước và ownership; browser không gọi provider." }
    ],
    videoStoryboard: [
      { name: "brief", label: "Chủ đề / brief", control: "textarea", placeholder: "Mục tiêu, câu chuyện, sản phẩm và CTA…", required: true, minLength: 1 },
      { name: "tier", label: "Tier video", control: "select", optionsFrom: "videoTiers", emptyLabel: "Để Bot trả lựa chọn tier canonical", help: "Tuỳ chọn planning; confirm tương lai cần tier canonical." },
      { name: "scene_count", label: "Số cảnh", type: "number", placeholder: "Ví dụ: 3", min: 1, max: 20, step: 1, inputMode: "numeric", help: "Có thể để trống khi lập draft; cần trước khi xác nhận job." },
      { name: "duration", label: "Thời lượng mục tiêu (giây)", type: "number", placeholder: "Ví dụ: 30", min: 1, max: 600, step: 1, inputMode: "numeric", help: "Tuỳ chọn planning; storyboard canonical có thể lập draft trước khi biết thời lượng." },
      { name: "template", label: "Mẫu storyboard", control: "select", options: ["product_ad", "ugc", "story", "explainer"] },
      { name: "platform", label: "Kênh phát hành", control: "select", options: ["TikTok", "YouTube", "Facebook", "Instagram", "Khác"] },
      { name: "format", label: "Tỷ lệ khung hình", control: "select", options: ["9:16", "16:9", "1:1", "4:5"] },
      { name: "style", label: "Phong cách", placeholder: "Ví dụ: gọn, hiện đại, có phụ đề rõ" },
      { name: "goal", label: "Mục tiêu / CTA", placeholder: "Ví dụ: tăng nhận diện và dẫn về landing page" },
      { name: "notes", label: "Ghi chú cảnh", control: "textarea", placeholder: "Các điểm bắt buộc, giới hạn thương hiệu hoặc tham chiếu an toàn…" }
    ],
    videoImageToVideo: [
      { name: "brief", label: "Chuyển động mong muốn", control: "textarea", placeholder: "Mô tả camera, chủ thể và chuyển động…", required: true, minLength: 1 },
      { name: "tier", label: "Tier video", control: "select", optionsFrom: "videoTiers", emptyLabel: "Để Bot trả lựa chọn tier canonical", help: "Tuỳ chọn cho draft/quote discovery; confirm tương lai cần tier canonical." },
      { name: "scene_count", label: "Số cảnh", type: "number", placeholder: "Ví dụ: 1", min: 1, max: 20, step: 1, inputMode: "numeric", help: "Có thể để trống khi lập draft; cần trước khi tạo job." },
      { name: "duration_seconds", label: "Thời lượng mục tiêu (giây)", type: "number", placeholder: "Ví dụ: 8", min: 1, max: 600, step: 1, inputMode: "numeric", help: "Tuỳ chọn planning." },
      { name: "format", label: "Tỷ lệ khung hình", control: "select", options: ["9:16", "16:9", "1:1", "4:5"] },
      { name: "platform", label: "Kênh phát hành", control: "select", options: ["TikTok", "YouTube", "Facebook", "Instagram", "Khác"], help: "Helper canonical dùng kênh phát hành cùng tỷ lệ và thời lượng để lập prompt video có ngữ cảnh." },
      { name: "goal", label: "Mục tiêu / CTA", placeholder: "Ví dụ: tạo chuyển động sản phẩm để dùng cho quảng cáo dọc" },
      { name: "source", label: "Ảnh nguồn", type: "file", accept: "image/jpeg,image/png,image/webp", requiredUpload: true, help: "Ảnh phải vào staging canonical trước khi Core Bridge có thể kiểm tra ownership." }
    ],
    voice: [
      { name: "script", label: "Nội dung lời thoại", control: "textarea", placeholder: "Nhập văn bản để chuẩn bị giọng nói…", required: true, minLength: 1 },
      { name: "voice_profile_id", label: "Giọng đã lưu (tuỳ chọn)", control: "select", optionsFrom: "voiceProfiles", emptyLabel: "Dùng giọng mặc định do bot cấp", help: "Danh sách chỉ gồm metadata Voice Vault đã qua ownership check. Core Bridge luôn kiểm tra lại lựa chọn khi estimate/confirm." },
      { name: "speed", label: "Tốc độ đọc", control: "select", options: ["normal", "slow", "fast"], help: "Thời lượng hiển thị trong estimate được tính bởi helper canonical của bot." }
    ],
    voiceSaved: [
      { name: "script", label: "Nội dung lời thoại", control: "textarea", placeholder: "Nhập văn bản để chuẩn bị giọng nói…", required: true, minLength: 1 },
      { name: "voice_profile_id", label: "Giọng từ Voice Vault", control: "select", optionsFrom: "voiceProfiles", emptyLabel: "Chọn một giọng đã sẵn sàng", help: "Saved TTS chỉ estimate khi Voice Vault canonical xác nhận profile này thuộc tài khoản và sẵn sàng.", required: true },
      { name: "speed", label: "Tốc độ đọc", control: "select", options: ["normal", "slow", "fast"], help: "Thời lượng hiển thị trong estimate được tính bởi helper canonical của bot." }
    ],
    voiceClone: [
      { name: "display_name", label: "Tên giọng (tuỳ chọn)", placeholder: "Ví dụ: Giọng thương hiệu TOAN AAS", maxLength: 120, help: "Nếu để trống, Bot canonical đặt tên mặc định an toàn; tên này không phải provider voice ID." },
      { name: "sample", label: "Mẫu audio để clone", type: "file", accept: "audio/mpeg,audio/wav,audio/x-wav,audio/mp4,audio/ogg", requiredUpload: true, help: "Mẫu chỉ vào bot-owned staging sau kiểm tra MIME, chữ ký, kích thước và ownership; browser không gửi tới provider." },
      { name: "consent", label: "Quyền sử dụng mẫu giọng", type: "checkbox", required: true, help: "Tôi xác nhận mình có quyền sử dụng mẫu giọng này và không mạo danh người khác." }
    ],
    music: [
      { name: "brief", label: "Brief âm nhạc", control: "textarea", placeholder: "Bối cảnh, mood, nhịp độ, công cụ, đối tượng nghe…", help: "Bot sẽ chặn yêu cầu mô phỏng nghệ sĩ/bài hát hoặc giai điệu có bản quyền.", required: true, minLength: 1 },
      { name: "mode", label: "Loại định hướng", control: "select", options: ["background", "melody", "custom"], help: "Chỉ tạo gợi ý prompt canonical; chưa gọi provider tạo nhạc." },
      { name: "duration_seconds", label: "Thời lượng dự kiến (giây)", type: "number", placeholder: "Ví dụ: 30", help: "Tuỳ chọn planning; Bot dùng mặc định canonical khi để trống. Browser không tính Xu.", min: 1, max: 600, step: 1, inputMode: "numeric" }
    ],
    musicSong: [
      { name: "brief", label: "Brief bài hát", control: "textarea", placeholder: "Thông điệp, mood, cấu trúc, CTA và lời gốc mong muốn…", help: "Không yêu cầu cover, remix hoặc bắt chước nghệ sĩ/bài hát cụ thể.", required: true, minLength: 1 },
      { name: "mode", label: "Kiểu sáng tác", control: "select", options: [{ value: "lyrics", label: "Bài hát có lời gốc" }, { value: "melody", label: "Giai điệu / instrumental" }, { value: "custom", label: "Tuỳ biến theo brief" }], help: "Giá trị này được gửi trực tiếp tới helper prompt canonical của bot.", required: true },
      { name: "song_length_mode", label: "Dạng bài hát", control: "select", options: [{ value: "seconds", label: "Theo số giây" }, { value: "half", label: "Bản nửa" }, { value: "full", label: "Bản đầy đủ" }], emptyLabel: "Chọn dạng bài hát canonical", help: "Chế độ half/full được bot quy đổi theo product kind canonical.", required: true },
      { name: "duration_seconds", label: "Thời lượng khi chọn theo số giây", type: "number", placeholder: "Ví dụ: 30", min: 1, max: 600, step: 1, inputMode: "numeric", help: "Bắt buộc khi chọn Theo số giây; half/full dùng product kind canonical." }
    ],
    musicSfx: [
      { name: "brief", label: "Brief SFX", control: "textarea", placeholder: "Ví dụ: tiếng mở hộp gọn, hiện đại, không có nhạc nền…", help: "Bridge chỉ lưu query/policy và báo giá canonical; không tìm kho ngoài hay giả kết quả.", required: true, minLength: 1 },
      { name: "item_count", label: "Số hiệu ứng dự kiến", type: "number", placeholder: "Ví dụ: 2", help: "Tuỳ chọn planning; Bot dùng mặc định 1 khi để trống.", min: 1, max: 20, step: 1, inputMode: "numeric" },
      { name: "duration_seconds", label: "Thời lượng video tham chiếu (giây)", type: "number", placeholder: "Ví dụ: 30", help: "Tuỳ chọn planning; Bot dùng mặc định canonical khi để trống.", min: 1, max: 600, step: 1, inputMode: "numeric" }
    ],
    musicUpload: [
      { name: "audio", label: "Tệp âm thanh của bạn", type: "file", accept: "audio/mpeg,audio/wav,audio/x-wav,audio/mp4,audio/ogg", requiredUpload: true, help: "Tệp chỉ vào bot-owned staging sau kiểm tra MIME/chữ ký/kích thước; chưa ghép hoặc render video." },
      { name: "duration_seconds", label: "Thời lượng tham chiếu (giây)", type: "number", placeholder: "Ví dụ: 30", help: "Tuỳ chọn planning; Bot dùng mặc định canonical khi để trống.", min: 1, max: 600, step: 1, inputMode: "numeric" },
      { name: "notes", label: "Ghi chú dùng nhạc", control: "textarea", placeholder: "Ví dụ: chỉ dùng làm nhạc nền, cần loop…" }
    ],
    subtitleCreate: [
      { name: "source", label: "Tệp audio / video nguồn", type: "file", accept: "audio/mpeg,audio/wav,audio/x-wav,audio/mp4,audio/ogg,video/mp4,video/quicktime,video/webm", requiredUpload: true, help: "Core Bridge kiểm tra ownership, MIME và kích thước trước khi nhận tệp; không tự sinh transcript." },
      { name: "duration_seconds", label: "Thời lượng (giây)", type: "number", placeholder: "Ví dụ: 75", help: "Dùng cho estimate canonical; bot áp dụng mức tối thiểu theo phút.", required: true, min: 1, max: 14_400, step: 1, inputMode: "numeric" },
      { name: "output_format", label: "Định dạng phụ đề", control: "select", options: ["srt"], help: "SRT là định dạng output currently mapped. VTT vẫn được giữ guarded cho tới khi Bot adapter xác nhận delivery riêng." }
    ],
    subtitleTranslate: [
      { name: "source", label: "Nguồn SRT/VTT/TXT hoặc audio/video", type: "file", accept: ".srt,.vtt,.txt,text/plain,text/vtt,application/x-subrip,audio/mpeg,audio/wav,audio/x-wav,audio/mp4,audio/ogg,video/mp4,video/quicktime,video/webm", requiredUpload: true, help: "Bridge nhận tệp thuộc sở hữu bạn; không tạo bản dịch giả trong browser." },
      { name: "target_language", label: "Ngôn ngữ đích", control: "select", options: LANGUAGE_OPTIONS, emptyLabel: "Chọn ngôn ngữ canonical", required: true },
      { name: "duration_seconds", label: "Thời lượng (giây)", type: "number", placeholder: "Ví dụ: 75", required: true, min: 1, max: 14_400, step: 1, inputMode: "numeric" },
      { name: "output_format", label: "Định dạng xuất", control: "select", options: ["srt"], help: "VTT chưa có delivery adapter canonical được xác nhận; không hứa output VTT ở Web." }
    ],
    dubbing: [
      { name: "source", label: "Tệp audio / video nguồn", type: "file", accept: "audio/mpeg,audio/wav,audio/x-wav,audio/mp4,audio/ogg,video/mp4,video/quicktime,video/webm", requiredUpload: true, help: "Tệp cần qua staging canonical trước khi bot báo giá hoặc quyết định khả năng xử lý." },
      { name: "mode", label: "Workflow", control: "select", options: ["dubbing", "subtitle_plus_dubbing"], help: "Chọn rõ lồng tiếng hoặc phụ đề + lồng tiếng; bridge dùng mode canonical của bot." },
      { name: "target_language", label: "Ngôn ngữ đích", control: "select", options: LANGUAGE_OPTIONS, emptyLabel: "Chọn ngôn ngữ canonical", required: true },
      { name: "voice_profile_id", label: "Giọng từ Voice Vault (tuỳ chọn)", control: "select", optionsFrom: "voiceProfiles", emptyLabel: "Dùng giọng mặc định do bot chọn", help: "Chỉ profile thuộc tài khoản và sẵn sàng TTS mới xuất hiện. Browser gửi ID canonical, không gửi provider voice ID hoặc tên giọng tự do." },
      { name: "speed", label: "Tốc độ đọc", control: "select", options: [{ value: "1.0", label: "Bình thường (1.0×)" }, { value: "0.9", label: "Chậm (0.9×)" }, { value: "1.5", label: "Nhanh (1.5×)" }], help: "Bot canonical chỉ nhận tốc độ số từ 0.7× đến 1.8× cho dubbing." },
      { name: "duration_seconds", label: "Thời lượng (giây)", type: "number", placeholder: "Ví dụ: 75", required: true, min: 1, max: 14_400, step: 1, inputMode: "numeric" },
      { name: "output_format", label: "Định dạng phụ đề", control: "select", options: ["srt"], help: "VTT đang guarded cho tới khi canonical delivery adapter xác nhận." }
    ],
    // PDF utility routes now use owner-scoped Asset Vault sources and their
    // own server contracts. Keep this empty legacy field set so no generic
    // document form can accidentally revive a second bridge lifecycle.
    documentPdf: [],
    documentOcr: [
      { name: "document", label: "Ảnh hoặc PDF nguồn", type: "file", accept: "application/pdf,image/jpeg,image/png,image/webp", requiredUpload: true, help: "OCR không trả text cho đến khi pipeline canonical tạo output đã kiểm tra." },
      { name: "operation", label: "Loại OCR", control: "select", options: ["ocr_image", "ocr_pdf"], required: true },
      { name: "page_count", label: "Số trang khi OCR PDF", type: "number", placeholder: "Ví dụ: 2", required: true, min: 1, max: 2_000, step: 1, inputMode: "numeric" }
    ],
    documentMerge: [
      { name: "documents", label: "Các PDF cần gộp", type: "file", accept: "application/pdf", multiple: true, requiredUpload: true, help: "Chọn từ hai PDF trở lên; thứ tự staging là thứ tự gửi. Chưa chạy merge trực tiếp từ browser." },
      { name: "page_count", label: "Tổng trang để báo giá", type: "number", placeholder: "Ví dụ: 8", required: true, min: 1, max: 2_000, step: 1, inputMode: "numeric" }
    ],
    documentSplit: [
      { name: "document", label: "PDF nguồn", type: "file", accept: "application/pdf", requiredUpload: true },
      { name: "page_range", label: "Khoảng trang", placeholder: "Ví dụ: 1-3 hoặc 2", help: "Bot canonical chỉ nhận một trang hoặc một khoảng liên tiếp N-M; không dùng danh sách có dấu phẩy.", required: true, pattern: "\\d+(?:-\\d+)?" },
      { name: "page_count", label: "Số trang để báo giá", type: "number", placeholder: "Ví dụ: 12", required: true, min: 1, max: 2_000, step: 1, inputMode: "numeric" }
    ],
    documentTranslate: [
      { name: "document", label: "Tài liệu nguồn", type: "file", accept: ".txt,.srt,.vtt,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain,text/vtt,application/x-subrip", requiredUpload: true, help: "Nhận PDF, DOCX, TXT, SRT hoặc VTT vào staging canonical. Document translation chưa có quote/delivery adapter bền vững nên sẽ hiển thị guarded đúng trạng thái." },
      { name: "target_language", label: "Ngôn ngữ đích", control: "select", options: LANGUAGE_OPTIONS, emptyLabel: "Chọn ngôn ngữ canonical", required: true },
      { name: "notes", label: "Yêu cầu dịch", control: "textarea", placeholder: "Giữ thương hiệu, thuật ngữ, định dạng…" }
    ],
    support: [
      { name: "subject", label: "Chủ đề", placeholder: "Tóm tắt vấn đề", required: true, minLength: 3, maxLength: 180 },
      { name: "detail", label: "Nội dung", control: "textarea", placeholder: "Không nhập khoá API, token hoặc dữ liệu thanh toán nhạy cảm.", help: "Web server sẽ chặn secret, OTP/CVV và số thẻ trước khi ticket được gửi. Tệp đính kèm chỉ xuất hiện khi adapter canonical hỗ trợ reference upload; form hiện tại không nhận hoặc bỏ qua file.", required: true, minLength: 3, maxLength: 4000 }
    ],
    profile: [
      { name: "display_name", label: "Tên hiển thị", placeholder: "Tên bạn muốn hiển thị", maxLength: 120, help: "Đây là metadata Web; Telegram identity, role và Xu không thể sửa ở form này." },
      { name: "locale", label: "Ngôn ngữ hồ sơ", control: "select", options: [{ value: "vi", label: "Tiếng Việt" }, { value: "en", label: "English" }], help: "Lưu preference hồ sơ; nội dung workflow vẫn theo contract canonical." },
      { name: "timezone", label: "Múi giờ", control: "select", options: ["Asia/Ho_Chi_Minh", "UTC"], help: "Dùng cho preference hiển thị Web, không thay đổi timezone runtime Bot." }
    ],
    adminFilter: [
      { name: "query", label: "Tìm kiếm", placeholder: "ID, email hoặc mã job…" },
      { name: "period", label: "Khoảng thời gian", control: "select", options: ["Hôm nay", "7 ngày", "30 ngày", "Theo bộ lọc server"] }
    ]
  });

  const manifest = Object.create(null);
  // The catalog owns the canonical feature key. These aliases are only for
  // presentational routes whose friendly path differs from the one catalog
  // route; the server still enforces the exact per-feature adapter allowlist.
  const FEATURE_PAGE_KEY_ALIASES = Object.freeze({
    "/voice/tts": "voice_tts",
    "/music": "music_background",
    "/music/create": "music_background"
  });

  // These commands were read from the frozen Bot baseline and then reviewed
  // at their handlers. They are optional companion shortcuts only; none
  // serializes a Portal value into Telegram. Keep this deliberately small: a
  // command that needs a prompt, upload, ID, payment detail, or provider
  // readiness must stay in the Web Workspace until a dedicated integration is
  // tested.
  const FEATURE_BOT_HANDOFFS = Object.freeze({
    prompt_studio: Object.freeze({ command: "/film", label: "Mở Content Studio trong Bot" }),
    caption: Object.freeze({ command: "/film", label: "Mở Content Studio trong Bot" }),
    hashtag: Object.freeze({ command: "/film", label: "Mở Content Studio trong Bot" }),
    hook: Object.freeze({ command: "/film", label: "Mở Content Studio trong Bot" }),
    script: Object.freeze({ command: "/film", label: "Mở Content Studio trong Bot" }),
    storyboard: Object.freeze({ command: "/film", label: "Mở Content Studio trong Bot" }),
    content_pack: Object.freeze({ command: "/film", label: "Mở Content Studio trong Bot" }),
    image_create: Object.freeze({ command: "/image_tools", label: "Mở Image tools trong Bot" }),
    image_edit: Object.freeze({ command: "/image_tools", label: "Mở Image tools trong Bot" }),
    image_upscale: Object.freeze({ command: "/image_tools", label: "Mở Image tools trong Bot" }),
    image_transform: Object.freeze({ command: "/image_tools", label: "Mở Image tools trong Bot" }),
    image_remove_background: Object.freeze({ command: "/image_tools", label: "Mở Image tools trong Bot" }),
    video_single: Object.freeze({ command: "/create_media", label: "Mở Media Studio trong Bot" }),
    video_image_to_video: Object.freeze({ command: "/create_media", label: "Mở Media Studio trong Bot" }),
    video_product: Object.freeze({ command: "/create_media", label: "Mở Media Studio trong Bot" }),
    video_trend: Object.freeze({ command: "/create_media", label: "Mở Media Studio trong Bot" }),
    video_text_to_video: Object.freeze({ command: "/create_media", label: "Mở Media Studio trong Bot" }),
    video_quick: Object.freeze({ command: "/create_media", label: "Mở Media Studio trong Bot" }),
    video_multiscene: Object.freeze({ command: "/create_media", label: "Mở Media Studio trong Bot" }),
    video_long: Object.freeze({ command: "/create_media", label: "Mở Media Studio trong Bot" }),
    video_addons: Object.freeze({ command: "/create_media", label: "Mở Media Studio trong Bot" }),
    video_mux: Object.freeze({ command: "/create_media", label: "Mở Media Studio trong Bot" }),
    music_library: Object.freeze({ command: "/music", label: "Mở Music Studio trong Bot" }),
    sfx_library: Object.freeze({ command: "/music", label: "Mở Music Studio trong Bot" }),
    music_background: Object.freeze({ command: "/music", label: "Mở Music Studio trong Bot" }),
    music_song: Object.freeze({ command: "/music", label: "Mở Music Studio trong Bot" }),
    music_sfx: Object.freeze({ command: "/music", label: "Mở Music Studio trong Bot" }),
    music_upload: Object.freeze({ command: "/music", label: "Mở Music Studio trong Bot" }),
    subtitle_asr: Object.freeze({ command: "/translate", label: "Mở Translation tools trong Bot" }),
    subtitle_create: Object.freeze({ command: "/translate", label: "Mở Translation tools trong Bot" }),
    subtitle_translate: Object.freeze({ command: "/translate", label: "Mở Translation tools trong Bot" }),
    video_dub: Object.freeze({ command: "/translate", label: "Mở Translation tools trong Bot" }),
    asr: Object.freeze({ command: "/translate", label: "Mở Translation tools trong Bot" }),
    subtitle_formats: Object.freeze({ command: "/translate", label: "Mở Translation tools trong Bot" }),
    documents: Object.freeze({ command: "/doc_tools", label: "Mở Document tools trong Bot" }),
    documents_pdf: Object.freeze({ command: "/doc_tools", label: "Mở Document tools trong Bot" }),
    documents_ocr: Object.freeze({ command: "/doc_tools", label: "Mở Document tools trong Bot" }),
    documents_merge: Object.freeze({ command: "/doc_tools", label: "Mở Document tools trong Bot" }),
    documents_split: Object.freeze({ command: "/doc_tools", label: "Mở Document tools trong Bot" }),
    documents_compress: Object.freeze({ command: "/doc_tools", label: "Mở Document tools trong Bot" }),
    documents_translate: Object.freeze({ command: "/doc_tools", label: "Mở Document tools trong Bot" })
  });

  function copyFields(fields) {
    return (fields || []).map((field) => ({ ...field, options: field.options ? [...field.options] : undefined }));
  }

  function definePage(page, aliases) {
    const frozen = Object.freeze({
      status: "guarded",
      access: "member",
      layout: "workspace",
      action: "draft",
      actionLabel: "Tạo bản nháp",
      fields: [],
      notes: [],
      ...page,
      fields: copyFields(page.fields),
      notes: [...(page.notes || [])]
    });
    [frozen.path, ...(aliases || [])].forEach((path) => { manifest[path] = frozen; });
    return frozen;
  }

  function customerPage(path, title, description, icon, extra, aliases) {
    return definePage({ path, title, description, icon, section: "Khách hàng", ...extra }, aliases);
  }

  function botCompanionPage(path, title, description, icon, commands) {
    return customerPage(path, title, description, icon, {
      type: "bot-companion",
      layout: "bot-companion",
      action: "none",
      status: "read_only",
      botCommands: Array.isArray(commands) ? commands : [],
      notes: [
        "Dữ liệu, trạng thái và mọi thao tác vẫn do Telegram Bot canonical quản lý.",
        "Portal chỉ mở Bot hoặc sao chép một lệnh an toàn; không tạo bản sao state, job, wallet hay reward."
      ]
    });
  }

  function analyticsBotCompanionPage(path, title, description, icon, command, defaultDays) {
    return customerPage(path, title, description, icon, {
      type: "analytics-bot-companion",
      layout: "analytics-bot-companion",
      action: "none",
      status: "read_only",
      botCommand: command,
      botDefaultDays: defaultDays,
      notes: [
        "Web chỉ dựng lệnh đã được giới hạn tham số; Bot canonical vẫn kiểm tra dữ liệu, quota, Xu và quyền sở hữu.",
        "Không có doanh thu, performance, file report hoặc quyết định hoàn Xu nào được tính hay tạo trong browser."
      ]
    });
  }

  function featurePage(path, title, description, icon, fields, aliases, options) {
    const settings = options && typeof options === "object" ? options : {};
    const page = definePage({
      path,
      title,
      description,
      icon,
      section: "AI Studio",
      type: "feature",
      action: "feature-draft",
      actionLabel: "Tạo bản nháp",
      fields: copyFields(fields),
      notes: [
        "Không có provider nào được gọi từ giao diện này.",
        "Project và Studio Document là Web-owned. Khi bật tạo media, backend Web-native hoặc integration tùy chọn đã kiểm thử mới được tạo job và xác nhận output."
      ],
      ...settings,
      fields: copyFields(settings.fields || fields),
      notes: settings.notes ? [...settings.notes] : [
        "Không có provider nào được gọi từ giao diện này.",
        "Project và Studio Document là Web-owned. Khi bật tạo media, backend Web-native hoặc integration tùy chọn đã kiểm thử mới được tạo job và xác nhận output."
      ]
    }, aliases);
    return page;
  }

  function guardedFeaturePage(path, title, description, icon, aliases, notes) {
    const page = definePage({
      path,
      title,
      description,
      icon,
      section: "AI Studio",
      type: "feature",
      action: "none",
      layout: "workspace",
      status: "guarded",
      fields: [],
      notes: notes || [
        "Route này đã được map để giữ parity với bot, nhưng chưa có planning/job adapter canonical riêng.",
        "Portal không mở form hoặc tạo output thay thế khi contract chưa đủ."
      ]
    }, aliases);
    return page;
  }

  function guidedFeaturePage(path, title, description, icon, layout, aliases, notes) {
    return definePage({
      path,
      title,
      description,
      icon,
      section: "AI Studio",
      type: "feature",
      action: "none",
      layout,
      status: "guarded",
      fields: [],
      notes: notes || [
        "Các bước này được map từ video finalization của Bot nhưng chưa có adapter Web tạo job canonical riêng.",
        "Portal chỉ điều hướng tới workflow hiện có; không tự ghép file, gọi provider hoặc đánh dấu output hoàn tất."
      ]
    }, aliases);
  }

  function readOnlyPage(path, title, description, icon, view, aliases) {
    const page = definePage({
      path,
      title,
      description,
      icon,
      section: "AI Studio",
      type: "read-only",
      layout: "read-only",
      action: "none",
      status: "empty",
      view,
      fields: [],
      notes: [
        "Trang này chỉ hiển thị dữ liệu đã qua signed session, ownership và Core Bridge.",
        "Không tạo draft rỗng, không gọi provider và không tạo output thay thế dữ liệu canonical."
      ]
    }, aliases);
    return page;
  }

  function adminPage(path, title, description, icon, extra, aliases) {
    return definePage({
      path,
      title,
      description,
      icon,
      section: "Admin ERP",
      type: "admin",
      access: "admin",
      layout: "admin",
      ...extra,
      status: "read_only",
      action: "none",
      actionLabel: "",
      fields: [],
      notes: [
        "Quyền quản trị phải được máy chủ xác nhận từ signed session.",
        "Các thao tác ghi, retry, refund và freeze đều chờ Core Bridge, CSRF và audit event."
      ]
    }, aliases);
  }

  // Public account and portal routes.
  definePage({
    path: "/login", title: "Đăng nhập an toàn", icon: ICONS.account, section: "Tài khoản",
    description: "Đăng nhập bằng Email + mật khẩu (có thể dùng Gmail), Google/GitHub/Apple OAuth, hoặc xác minh Telegram một lần trong bot; signed session chỉ do máy chủ tạo sau xác thực.",
    access: "public", layout: "auth", status: "ready", action: "auth-login", actionLabel: "Đăng nhập", fields: copyFields(FIELD_SETS.authLogin),
    notes: ["Không nhập raw Telegram ID vào browser. Telegram Login dùng OIDC đã ký trên server; Bot deep-link một lần vẫn khóa identity canonical, hết hạn và chống replay.", "Email + mật khẩu (có thể dùng Gmail), Telegram Login, Google OAuth, GitHub OAuth và Sign in with Apple là các phương thức riêng. OAuth chỉ hiện khi server đã có client, secret và callback hợp lệ."]
  });
  definePage({
    path: "/register", title: "Tạo tài khoản", icon: ICONS.account, section: "Tài khoản",
    description: "Tạo hồ sơ bằng Email + mật khẩu (có thể dùng Gmail), hoặc bằng Google/GitHub/Apple OAuth khi server đã cấu hình thật. Mật khẩu chỉ được băm ở máy chủ.",
    access: "public", layout: "auth", status: "ready", action: "auth-register", actionLabel: "Tạo tài khoản", fields: copyFields(FIELD_SETS.authRegister),
    notes: ["Hồ sơ mới có sẵn locale vi, múi giờ Asia/Ho_Chi_Minh và avatar gradient. Browser không nhận hoặc lưu Telegram ID; server chỉ giữ identity canonical sau khi Bot xác minh.", "Email + mật khẩu là phương thức đang bật; địa chỉ Gmail hoạt động như email bình thường. Telegram Login, Google OAuth, GitHub OAuth và Sign in with Apple chỉ mở khi server có cấu hình OAuth thật.", "Web server kiểm tra định dạng email, băm mật khẩu và giới hạn tốc độ đăng ký; response đăng ký không tiết lộ email đã có tài khoản hay chưa.", "Chỉ đăng nhập Email + mật khẩu hoặc OAuth đã xác thực mới cấp signed session và CSRF; shell không giả lập token hoặc session."]
  });
  // Marketing remains available only as an explicit secondary route. The app
  // origin itself is a product surface: the server sends unsigned visitors to
  // secure access and signed visitors to their Workspace.
  customerPage("/welcome", "TOAN AAS", "Không gian AI có kiểm soát cho nội dung, hình ảnh, video và âm thanh.", ICONS.dashboard, {
    access: "public", layout: "landing", action: "none", status: "ready", section: "AI workspace",
    notes: ["Landing không gọi provider, ví Xu hoặc Bot từ browser.", "Mọi workflow riêng tư bắt đầu sau signed session và liên kết Telegram canonical."]
  });
  customerPage("/onboarding", "Kết nối Telegram", "Liên kết Telegram tùy chọn bằng mã dùng một lần do Web server tạo, bot xác nhận.", ICONS.account, {
    layout: "onboarding", fields: [], action: "start-telegram-link", actionLabel: "Tạo mã liên kết", status: "guarded",
    notes: ["Mã phải là one-time, hết hạn và được Core Bridge đánh dấu đã dùng.", "Không nhận Telegram ID thô từ URL hay localStorage."]
  });
  customerPage("/account", "Tài khoản & bảo mật", "Quản lý thông tin hồ sơ và trạng thái liên kết theo dữ liệu server-side.", ICONS.account, {
    layout: "account", fields: [], action: "none", status: "ready",
    notes: ["Tên hiển thị, ngôn ngữ và múi giờ là metadata Web có thể cập nhật bằng signed session, CSRF và audit event.", "Telegram identity, role, Xu, PayOS, job và provider vẫn là dữ liệu canonical chỉ đọc từ bot/Core Bridge.", "Đăng xuất thu hồi signed session ở server, không chỉ xóa state tại browser."]
  });
  customerPage("/account/activity", "Hoạt động tài khoản", "Xem nhật ký đã sanitize của hoạt động Web thuộc signed account hiện tại.", ICONS.account, {
    layout: "account-activity", fields: [], action: "none", status: "read_only",
    notes: ["Chỉ hiển thị hoạt động Web của signed account; không phải Bot audit, wallet ledger, lịch sử PayOS hay provider.", "Response không chứa Telegram ID, request ID, target, detail audit, password, token hoặc dữ liệu của tài khoản khác."]
  });
  customerPage("/membership", "Gói thành viên", "Xem tier, trial, quyền lợi và catalog gói từ Bot canonical; Web không tự cấp VIP hoặc thay đổi Xu.", ICONS.pricing, {
    layout: "membership", type: "membership", fields: [], action: "none", status: "read_only",
    notes: ["Tier, trial, grant, rank và package entitlement vẫn do Bot canonical quyết định.", "Trang này chỉ hiển thị metadata bridge đã redaction; không tự áp ưu đãi, grant quyền lợi hoặc sửa ledger Xu."]
  });
  customerPage("/status", "Trạng thái dịch vụ", "Kiểm tra sẵn sàng của signed session, Telegram link và Core Bridge mà không lộ danh tính, secret hoặc provider payload.", ICONS.system, {
    layout: "service-status", type: "service-status", fields: [], action: "none", status: "read_only",
    notes: ["Trạng thái này không phải dashboard provider và không bật/tắt runtime từ browser.", "Nếu Telegram chưa sẵn sàng, dùng liên kết một lần trong Tài khoản thay vì nhập Telegram ID."]
  });
  customerPage("/tools", "Công cụ & models", "Danh mục các workflow Web đã định tuyến từ Bot inventory. Card guarded vẫn giữ nguyên trạng thái cho đến khi Core Bridge công bố adapter.", ICONS.prompt, {
    layout: "feature-catalog", type: "feature-catalog", fields: [], action: "none", status: "read_only",
    notes: ["Danh mục không phải danh sách provider đang chạy và không hứa một engine/output chưa có contract canonical.", "Mỗi workflow vẫn dùng signed session, CSRF, ownership và flow draft → estimate → confirm riêng."]
  });
  customerPage("/studio", "Media Studio", "Lập luồng content, visual, video, voice, music và finalization bằng các workspace Web đã đăng ký.", ICONS.video, {
    layout: "media-studio", type: "media-studio", fields: [], action: "none", status: "read_only",
    notes: ["Media Studio chỉ điều hướng giữa các workflow canonical; không tự tạo project, job, output hay delivery giả.", "Mỗi bước vẫn cần estimate, confirm và adapter Bot riêng trước khi engine được phép chạy."]
  });
  customerPage("/workspace", "Bản nháp của tôi", "Lưu và tiếp tục brief Web an toàn giữa các workflow mà không gửi Bot, tạo quote, job hoặc Xu.", ICONS.prompt, {
    layout: "workspace-drafts", type: "workspace-drafts", fields: [], action: "none", status: "read_only",
    notes: ["Chỉ lưu brief và lựa chọn scalar do bạn nhập. Tệp, upload ID, voice profile, quote receipt, job, Xu, PayOS và provider không được lưu hoặc khôi phục.", "Bản nháp thuộc signed Web account hiện tại; tiếp tục một bản nháp vẫn cần đi qua toàn bộ kiểm tra form, upload, estimate và Bot canonical riêng."]
  });
  customerPage("/projects", "Project Center", "Tổ chức brief, prompt, caption, script và storyboard trong các Project có version history do Web Workspace sở hữu.", ICONS.dashboard, {
    layout: "project-center", type: "project-center", fields: [], action: "none", status: "ready",
    notes: ["Project và Studio Document thuộc Web account hiện tại, hoạt động ngay cả khi không liên kết Telegram.", "Đây là dữ liệu authoring do bạn tạo; không gọi Bot, provider, PayOS, ví Xu hoặc tự gắn nhãn output media."]
  });
  customerPage("/prompt-library", "Prompt Library", "Lưu template prompt riêng tư có metadata, biến, tag, version history và preview cục bộ — không tạo AI job hoặc gọi provider.", ICONS.prompt, {
    layout: "prompt-library", type: "prompt-library", fields: [], action: "none", status: "ready",
    notes: ["Mỗi template thuộc signed Web account hiện tại; kho JSON seed global của Bot không được copy hoặc hiển thị tại đây.", "Preview chỉ thay thế variable đã khai báo trong trình duyệt/server Web; không gọi engine, Bot, provider, Xu hoặc PayOS."]
  });
  customerPage("/prompt-library/new", "Template Prompt mới", "Tạo một recipe prompt có thể tái sử dụng trong Prompt Library riêng tư của Web account.", ICONS.prompt, {
    layout: "prompt-library", type: "prompt-library", fields: [], action: "none", status: "ready",
    notes: ["Điền nguồn và quyền sử dụng rõ ràng trước khi lưu. Không gửi secret, token, OTP/CVV, số thẻ hay dữ liệu thanh toán.", "Bạn có thể sao chép template sang Prompt Studio sau khi lưu; đó không phải yêu cầu chạy AI."]
  });
  customerPage("/media-workspace", "Audio Library & Briefing", "Tổ chức Audio Asset Vault và music/SFX brief riêng tư với version history, không chạy provider hoặc tạo audio giả.", ICONS.music, {
    layout: "media-workspace", type: "media-workspace", fields: [], action: "none", status: "guarded",
    notes: ["Workspace này chỉ quản lý metadata, creative brief và tham chiếu Asset Vault thuộc signed Web account. Nó không gọi Bot, provider, Xu, PayOS, job hay delivery.", "Music library bên ngoài, AI generation, enhance, translate, mux/render và preview provider vẫn được giữ guarded cho tới khi có adapter riêng đã được kiểm chứng."]
  });
  customerPage("/media-workspace/new", "Audio Collection mới", "Tạo collection riêng tư cho brief âm thanh, quyền sử dụng và tham chiếu Asset Vault đã được owner-check.", ICONS.music, {
    layout: "media-workspace", type: "media-workspace", fields: [], action: "none", status: "guarded",
    notes: ["Không nhập URL audio, Telegram file ID, provider preview hoặc thông tin thanh toán. Chỉ Asset Vault audio active thuộc account hiện tại có thể được gắn sau khi tạo collection.", "Duration là thông tin do bạn khai báo, không phải số liệu được parse, waveform hoặc promise render."]
  });
  customerPage("/content-studio", "Creative Content Studio", "Workspace chuyên nghiệp để tổ chức brief, caption, hook, script, storyboard và content pack với version history riêng tư.", ICONS.prompt, {
    layout: "content-studio", type: "content-studio", fields: [], action: "none", status: "ready",
    notes: ["Content Studio là authoring workspace Web-native. Nó không gọi Bot, provider, ví Xu, PayOS, job, publish hoặc delivery.", "Composer chỉ tạo ba khung nháp cục bộ có nhãn rõ ràng để biên tập; không tự nhận là AI output hoặc nội dung đã được duyệt."]
  });
  customerPage("/content-studio/new", "Content Brief mới", "Tạo brief có cấu trúc và liên kết Project, Campaign, Prompt Library hoặc Audio Library riêng tư.", ICONS.prompt, {
    layout: "content-studio", type: "content-studio", fields: [], action: "none", status: "ready",
    notes: ["Không truyền brief, ID hoặc text riêng tư qua query string. Chỉ loại nội dung allowlist mới được dùng từ liên kết nội bộ.", "Mọi write cần signed session, CSRF, optimistic revision, idempotency và owner check trên server."]
  });
  // Voice Studio intentionally has its own route family.  `/voice` remains
  // the Bot/Core-Bridge-facing Voice Vault and TTS surface, while this
  // workspace stores only Web-owned direction, consent metadata and scripts.
  customerPage("/voice-studio", "Voice Studio & Consent Vault", "Tổ chức voice direction, self-attested consent, lời thoại, cue-sheet và version history riêng tư — không tạo audio.", ICONS.voice, {
    layout: "voice-studio", type: "voice-studio", fields: [], action: "none", status: "ready",
    notes: ["Voice Studio không phải Voice Vault canonical của Bot và không lưu audio, provider voice ID, Telegram file ID, preview URL, job, Xu hay PayOS.", "TTS, voice clone, preview và delivery vẫn ở trạng thái guarded cho đến khi có adapter riêng được kiểm tra; cue-sheet chỉ là ước lượng theo text."]
  });
  customerPage("/voice-studio/new", "Voice direction mới", "Tạo profile hướng dẫn thể hiện và consent metadata Web-native có owner check, revision và audit.", ICONS.voice, {
    layout: "voice-studio", type: "voice-studio", fields: [], action: "none", status: "ready",
    notes: ["Không nhập hay upload audio, URL, provider profile, Telegram ID/file ID, secret hoặc thông tin thanh toán.", "Consent là self-attestation của người dùng, không phải quyết định quyền sử dụng, clone giọng hoặc phê duyệt provider."]
  });
  // Video Production Studio is deliberately separate from the historical
  // `/video/*` feature family.  This is a signed Web-native authoring space
  // for plans, scenes and self-review; it does not create, render or deliver
  // video/media merely because a plan is saved.
  customerPage("/video-studio", "Video Production Studio", "Lập brief, scene plan, runtime estimate và self-review trong workspace riêng tư có version history.", ICONS.video, {
    layout: "video-studio", type: "video-studio", fields: [], action: "none", status: "ready",
    notes: ["Video Production Studio chỉ lưu plan và scene metadata thuộc signed Web account. Không upload media, không tạo render, tệp hay delivery.", "Approve là self-review nội bộ, không phải xác nhận sản xuất hoặc kết quả media."]
  });
  customerPage("/video-studio/new", "Video plan mới", "Tạo kế hoạch sản xuất có cấu trúc, mục tiêu, thời lượng và tỷ lệ khung hình để review nội bộ.", ICONS.video, {
    layout: "video-studio", type: "video-studio", fields: [], action: "none", status: "ready",
    notes: ["Không đưa secret, OTP/CVV, chứng từ thanh toán, URL hoặc thông tin nhận dạng riêng tư vào brief.", "Server kiểm tra signed session, CSRF, owner check, idempotency và optimistic revision cho mỗi thay đổi."]
  });
  // Subtitle Studio is intentionally independent from the historical
  // `/subtitle`, `/translate`, `/dubbing` and `/asr` Bot-facing routes.  It
  // stores editor-authored transcript metadata/cues only; no media is
  // uploaded, transcribed, translated, spoken, rendered or delivered here.
  customerPage("/subtitle-studio", "Subtitle & Transcript Workspace", "Tổ chức transcript project, cue timeline, bản nháp ngôn ngữ và self-review trong một workspace riêng tư.", ICONS.subtitle, {
    layout: "subtitle-studio", type: "subtitle-studio", fields: [], action: "none", status: "ready",
    notes: ["Không có ASR, dịch máy, TTS, dubbing, upload, player, output hay file URL trong workspace này.", "Preview SRT/VTT là văn bản định dạng từ cue do bạn biên tập; nó không phải tệp xuất hoặc kết quả provider."]
  });
  customerPage("/subtitle-studio/new", "Transcript project mới", "Tạo transcript project có ngôn ngữ, chuẩn caption, review context và cue timeline có version riêng.", ICONS.subtitle, {
    layout: "subtitle-studio", type: "subtitle-studio", fields: [], action: "none", status: "ready",
    notes: ["Không nhập secret, OTP/CVV, chứng từ thanh toán, provider/job/file handle hoặc URL trong metadata dự án.", "Mỗi lần ghi cần signed session, CSRF, ownership, idempotency và optimistic revision do server xác minh."]
  });
  // Image Creative Studio intentionally has a route family of its own.  The
  // legacy `/image/*` pages retain their existing deterministic operations;
  // this workspace holds signed-account creative directions only and never
  // pretends to call an image provider, render an image, or deliver a file.
  customerPage("/image-studio", "Image Creative Studio", "Tổ chức art direction, Asset Vault reference, biến thể và self-review trong workspace riêng tư.", ICONS.image, {
    layout: "image-studio", type: "image-studio", fields: [], action: "none", status: "ready",
    notes: ["Image Creative Studio chỉ lưu creative brief, direction và metadata Asset Vault đã qua owner check. Không có URL media, upload, provider, render, preview hoặc delivery tại đây.", "Approve là self-review của brief, không phải xác nhận ảnh đã tạo hoặc kết quả xử lý AI."]
  });
  customerPage("/image-studio/new", "Artboard mới", "Tạo art direction có cấu trúc, tham chiếu Asset Vault an toàn và version history riêng.", ICONS.image, {
    layout: "image-studio", type: "image-studio", fields: [], action: "none", status: "ready",
    notes: ["Chỉ chọn reference thuộc Asset Vault của signed account; không nhập URL, provider/job/file handle, secret, OTP/CVV hoặc chứng từ thanh toán.", "Mỗi lần ghi cần signed session, CSRF, owner check, idempotency và optimistic revision do server xác minh."]
  });
  // Document & PDF Workspace intentionally has a separate native route family.
  // Historical `/documents/*` pages continue to own narrowly scoped,
  // deterministic file operations.  This workspace stores a signed user's
  // document brief and processing plans only; it never uploads, parses, OCRs,
  // translates, converts, creates, previews or delivers a file.
  customerPage("/document-workspace", "Document & PDF Workspace", "Tổ chức brief tài liệu, processing plan, Asset Vault metadata và self-review trong workspace riêng tư.", ICONS.document, {
    layout: "document-workspace", type: "document-workspace", fields: [], action: "none", status: "ready",
    notes: ["Document & PDF Workspace chỉ lưu authoring metadata thuộc signed Web account. OCR, dịch, converter, provider, Bot job, Xu, PayOS, upload, file preview và delivery đều không chạy tại đây.", "Kế hoạch có thể liên kết metadata Asset Vault đã owner-check; đó không phải source blob, path, URL, file output hoặc yêu cầu thực thi."]
  });
  customerPage("/document-workspace/new", "Document brief mới", "Tạo brief tài liệu có scope, target format, checklist và processing plan để self-review nội bộ.", ICONS.document, {
    layout: "document-workspace", type: "document-workspace", fields: [], action: "none", status: "ready",
    notes: ["Không nhập URL, provider/job/file handle, secret, OTP/CVV, chứng từ thanh toán hoặc dữ liệu nhạy cảm vào metadata.", "Mỗi lần ghi cần signed session, CSRF, owner check, idempotency và optimistic revision do server xác minh."]
  });
  customerPage("/project-packages", "Project Packages", "Xuất snapshot ZIP bất biến từ Project và Studio Document do Web App tự xác minh riêng tư.", ICONS.package, {
    layout: "project-packages", type: "project-packages", fields: [], action: "none", status: "ready",
    notes: ["Project Package là output Web-native riêng tư; không phải Gói dịch vụ, Job Bot hay Tài sản Bot.", "ZIP chỉ chứa snapshot Project và metadata tham chiếu; không chứa source blob, storage path, URL ký, identity, Xu, PayOS hay provider data."]
  });
  customerPage("/asset-vault", "Asset Vault", "Lưu tệp riêng trong Web Workspace, tùy chọn gắn với Project và luôn tải qua signed session.", ICONS.assets, {
    layout: "asset-vault", type: "asset-vault", fields: [], action: "none", status: "ready",
    notes: ["Asset Vault là storage Web-owned, tách biệt hoàn toàn với Tài sản Bot và output job canonical.", "Tệp không có URL công khai, không nằm trong static/PWA cache và chỉ tải dạng attachment sau owner check."]
  });
  customerPage("/notes", "Memory Center", "Ghi chú riêng, tag, ưu tiên, tìm kiếm, archive và lịch sử phiên bản thuộc signed Web account.", ICONS.prompt, {
    type: "memory-center", layout: "memory-notes", fields: [], action: "none", status: "ready",
    notes: ["Memory Center là dữ liệu Web-owned, không đọc/ghi bảng memory của Bot.", "Ghi chú có optimistic versioning, CSRF, owner check và audit; không lưu secret, token, mật khẩu hoặc số thẻ."]
  });
  customerPage("/reminders", "Nhắc việc", "Quản lý reminder một lần hoặc lặp lại, pause/resume/complete/cancel theo signed Web account.", ICONS.jobs, {
    type: "memory-center", layout: "memory-reminders", fields: [], action: "none", status: "ready",
    notes: ["Reminder chỉ hiển thị trong Web Workspace; chưa gửi Telegram, email hoặc push notification.", "Mỗi thay đổi dùng CSRF, optimistic revision, idempotency và audit; Bot state không bị sửa."]
  });
  botCompanionPage("/referrals", "Giới thiệu", "Referral, link mời và thống kê chỉ được Bot canonical xác minh để tránh gán nhầm quyền lợi.", ICONS.users, [
    { command: "/referral", title: "Referral của tôi", text: "Mở hub referral và trạng thái canonical trong Bot." },
    { command: "/ref", title: "Link mời", text: "Lấy hoặc quản lý link giới thiệu trong Bot thay vì tự tạo link ở browser." }
  ]);
  botCompanionPage("/rewards", "Ưu đãi & quà", "Gift, birthday và promo có điều kiện/ledger canonical; Web không tự grant hoặc đánh dấu đã nhận.", ICONS.pricing, [
    { command: "/gift", title: "Quà & quyền lợi", text: "Xem luồng quà canonical; Bot kiểm tra điều kiện và lịch sử nhận." },
    { command: "/promos", title: "Khuyến mãi", text: "Mở hướng dẫn promo/coupon trong Bot; Web không áp mã hoặc thay đổi Xu." },
    { command: "/birthday", title: "Quà sinh nhật", text: "Tiếp tục yêu cầu/quy trình birthday trong Bot canonical." }
  ]);
  botCompanionPage("/community", "Cộng đồng", "Các kênh chính thức và community links do Bot phát hành; Portal chỉ tạo handoff an toàn.", ICONS.support, [
    { command: "/community", title: "Community hub", text: "Mở community hub do Bot phát hành." },
    { command: "/official_channels", title: "Kênh chính thức", text: "Xem danh sách kênh chính thức từ Bot thay vì một danh sách URL tĩnh trong Web." }
  ]);
  botCompanionPage("/guides", "Hướng dẫn Bot", "Dùng menu/hướng dẫn Bot cho các thao tác Telegram-first chưa có adapter Web riêng.", ICONS.legal, [
    { command: "/menu", title: "Menu chính", text: "Mở menu nhanh theo capability của tài khoản Bot hiện tại." },
    { command: "/guide", title: "Hướng dẫn", text: "Mở hướng dẫn sử dụng được Bot phát hành." },
    { command: "/help", title: "Trợ giúp lệnh", text: "Tra cứu lệnh Bot hiện hành trong cuộc hội thoại canonical." }
  ]);
  analyticsBotCompanionPage("/growth/ai", "Growth AI", "Phân tích hiệu suất và khuyến nghị cần Bot đọc dữ liệu campaign canonical, kiểm tra quota/Xu và gửi kết quả vào đúng cuộc hội thoại Telegram.", ICONS.reports, "/growth_ai", 14);
  analyticsBotCompanionPage("/campaign/report", "Báo cáo campaign", "Báo cáo campaign và file CSV được Bot tạo từ dữ liệu canonical; Web không tự tính doanh thu, performance hay tạo file xuất giả.", ICONS.reports, "/campaign_report", 30);
  customerPage("/dashboard", "Không gian làm việc", "Điểm xuất phát cho các bản nháp, job và tài sản do Core Bridge sở hữu.", ICONS.dashboard, {
    layout: "dashboard", action: "none", status: "guarded"
  }, ["/app"]);
  customerPage("/campaigns", "Campaign Planner", "Lập lịch và tự rà soát kế hoạch nội dung trên Web với bảng thời gian rõ ràng. Đây không phải campaign canonical, không tự publish hoặc tạo analytics/doanh thu.", ICONS.prompt, {
    layout: "campaign-planner", action: "campaign-create", actionLabel: "Lưu kế hoạch", status: "ready",
    fields: [
      { name: "title", label: "Tên kế hoạch", placeholder: "Ví dụ: Video giới thiệu sản phẩm tháng 7", required: true, minLength: 3, maxLength: 180, help: "Tên hiển thị trong bảng kế hoạch cá nhân trên Web." },
      { name: "destination_url", label: "Liên kết đích HTTPS", type: "url", placeholder: "https://example.com/san-pham", required: true, maxLength: 1024, help: "Chỉ lưu để bạn theo dõi CTA. Web không truy cập, publish hoặc gửi liên kết này sang provider/Bot." },
      { name: "platform", label: "Nền tảng dự kiến", control: "select", required: true, options: [{ value: "tiktok", label: "TikTok" }, { value: "instagram", label: "Instagram" }, { value: "facebook", label: "Facebook" }, { value: "youtube", label: "YouTube" }, { value: "website", label: "Website" }, { value: "other", label: "Khác" }] },
      { name: "objective", label: "Mục tiêu", control: "select", required: true, options: [{ value: "affiliate", label: "Affiliate" }, { value: "traffic", label: "Tăng traffic" }, { value: "conversion", label: "Tăng chuyển đổi" }, { value: "revenue", label: "Tăng doanh thu" }, { value: "community", label: "Cộng đồng" }] },
      { name: "scheduled_for", label: "Mốc lịch dự kiến", type: "datetime-local", help: "Chỉ là mốc lịch nội bộ theo giờ bạn nhập. Không tạo tác vụ publish, reminder hay chạy provider." }
    ],
    notes: ["Campaign Planner chỉ lưu metadata thuộc tài khoản Web hiện tại, có CSRF, ownership, idempotency và audit.", "Duyệt ở đây là tự rà soát kế hoạch; queue publish, campaign canonical, analytics và báo cáo vẫn nằm trong Bot/adapter riêng.", "Không tạo output, job, payment, Xu, webhook hoặc link provider từ trang này."]
  });
  customerPage("/calendar", "Content Calendar", "Xem lịch nội dung Web-owned theo các mốc bạn đã lập. Đây là lịch quản lý cá nhân, không phải lịch xuất bản canonical hoặc automation của Bot.", ICONS.system, {
    layout: "campaign-calendar", action: "none", status: "read_only",
    notes: ["Chỉ hiển thị kế hoạch thuộc signed Web account; ngày giờ là mốc nội bộ bạn đã nhập.", "Không tạo reminder, queue publish, channel schedule, analytics hoặc doanh thu từ browser.", "Dùng Campaign Planner để thay đổi mốc/lifecycle; Bot canonical vẫn sở hữu publishing và report."]
  });
  customerPage("/approvals", "Self-review Queue", "Rà soát các kế hoạch Web của bạn trước khi đánh dấu sẵn sàng hoặc xếp lịch nội bộ. Đây không phải Admin Approval Queue của Bot.", ICONS.security, {
    layout: "campaign-approvals", action: "none", status: "read_only",
    notes: ["Mỗi chuyển trạng thái vẫn kiểm tra signed session, CSRF, ownership, idempotency và audit ở server.", "“Đã sẵn sàng” chỉ là quyết định trong kế hoạch cá nhân; không cấp quyền publish và không thay đổi state canonical.", "Hàng duyệt job/publish thực tế chỉ xuất hiện khi adapter admin/Bot được phê duyệt riêng."]
  });
  customerPage("/features", "Tất cả công cụ", "Khám phá các workflow Web đã được định tuyến. Mỗi trạng thái vẫn do Core Bridge canonical cấp, không phải do browser suy đoán.", ICONS.prompt, {
    section: "AI Studio", type: "feature-catalog", layout: "feature-catalog", action: "none", status: "read_only",
    notes: ["Danh mục là bản đồ route Web App, không phải tuyên bố provider/engine đang chạy.", "Workflow guarded hoặc admin-only vẫn hiển thị đúng trạng thái, không tạo output thay thế."]
  });
  customerPage("/wallet", "Ví Xu", "Số dư, lịch sử và quyền sử dụng Xu chỉ hiển thị từ ledger canonical của bot.", ICONS.wallet, {
    layout: "wallet", action: "none", status: "guarded",
    notes: ["Web App không giữ ledger Xu và không tự cộng/trừ số dư.", "Dữ liệu wallet cần Core Bridge kiểm tra signed session và ownership."]
  });
  customerPage("/wallet/topup", "Nạp Xu", "Chọn entrypoint canonical: bot tạo PayOS QR động hoặc xử lý đối soát thủ công; Web không tạo link hay webhook.", ICONS.wallet, {
    layout: "wallet", action: "payment-create", actionLabel: "Tạo yêu cầu thanh toán", status: "guarded",
    fields: [
      { name: "package", label: "Mệnh giá nạp", control: "select", optionsFrom: "topupPackages", emptyLabel: "Chọn mệnh giá từ catalog nạp canonical", help: "Danh mục nạp phải được bot cấp riêng. Web không dùng combo/gói tháng để tạo PayOS webhook.", required: true }
    ],
    notes: ["Payment, amount, signature và webhook chỉ do bot/Core Bridge xử lý.", "Shell chỉ mở bot theo thao tác của bạn hoặc hiển thị checkout bridge đã ký; không finalize và không ghi Xu."]
  });
  customerPage("/packages", "Gói dịch vụ", "Catalog, giá và quyền lợi chỉ được render từ gói đã được server phê duyệt.", ICONS.pricing, {
    layout: "catalog", action: "none", status: "guarded"
  });
  customerPage("/pricing", "Bảng giá", "Tham khảo mức giá hiện hành do Core Bridge phát hành; không suy đoán Xu hoặc chính sách refund.", ICONS.pricing, {
    layout: "catalog", action: "none", status: "guarded"
  });
  customerPage("/jobs", "Job Center", "Theo dõi job thuộc sở hữu của phiên hiện tại; không hiện output giả khi chưa có delivery hợp lệ.", ICONS.jobs, {
    layout: "jobs", action: "none", status: "empty"
  });
  customerPage("/assets", "Thư viện tài sản", "Tệp hoàn tất chỉ xuất hiện sau khi Core Bridge xác minh ownership và cung cấp URL ký tạm thời.", ICONS.assets, {
    layout: "assets", action: "none", status: "empty"
  });
  customerPage("/support", "Web Support Desk", "Tạo và theo dõi yêu cầu trực tiếp trong Web App, với signed session, CSRF, ownership và audit riêng.", ICONS.support, {
    layout: "support-desk", action: "support-case-create", actionLabel: "Tạo yêu cầu", status: "processing",
    notes: [
      "Web Support Desk là không gian độc lập: không copy lịch sử ticket Bot và không gửi Telegram, email hay thông báo ngoài Web.",
      "Không gửi secret, token, OTP/CVV, số thẻ, bill, TXID, số tài khoản hoặc QR thanh toán vào biểu mẫu hỗ trợ."
    ]
  });
  customerPage("/tickets", "Yêu cầu của tôi", "Danh sách yêu cầu Web-native thuộc signed account hiện tại; không phải lịch sử ticket Telegram Bot.", ICONS.ticket, {
    layout: "support-cases", action: "none", status: "processing",
    notes: [
      "Mỗi case và phản hồi chỉ hiện cho account Web sở hữu nó.",
      "Trạng thái chờ đối tác hoặc hoàn tiền là trạng thái vận hành do nhân sự xác nhận, không phải xác nhận provider hay ledger tự động."
    ]
  });
  customerPage("/legal", "Điều khoản sử dụng", "Khung hiển thị điều khoản. Nội dung pháp lý chính thức sẽ được máy chủ phát hành theo phiên bản.", ICONS.legal, {
    layout: "legal", access: "public", action: "none", status: "ready"
  });
  customerPage("/privacy", "Chính sách riêng tư", "Khung hiển thị nguyên tắc dữ liệu. Bản chính thức cần được quản trị nội dung phát hành.", ICONS.legal, {
    layout: "legal", access: "public", action: "none", status: "ready"
  });

  // Content, image, video, voice, music, language and document feature routes.
  featurePage("/chat", "AI Chat", "Chuẩn bị hội thoại có ngữ cảnh; Core Bridge quyết định provider, quota và lưu lịch sử.", ICONS.chat, FIELD_SETS.prompt, ["/tools/chat"], { action: "feature-estimate", actionLabel: "Ước tính Xu", estimateDirect: true });
  featurePage("/prompt-studio", "Prompt Studio", "Soạn và tinh chỉnh prompt thành bản nháp an toàn trước khi xác nhận.", ICONS.prompt, FIELD_SETS.prompt, ["/prompts"]);
  featurePage("/content/caption", "Caption", "Chuẩn bị caption theo brief, giọng điệu và kênh phát hành.", ICONS.prompt, FIELD_SETS.prompt, ["/caption"]);
  featurePage("/content/hashtag", "Hashtag", "Tạo bản nháp hashtag theo nội dung và nền tảng.", ICONS.prompt, FIELD_SETS.prompt, ["/hashtag"]);
  featurePage("/content/hook", "Hook", "Phác thảo hook ngắn để kiểm tra trước khi gọi engine.", ICONS.prompt, FIELD_SETS.prompt, ["/hook"]);
  featurePage("/content/script", "Kịch bản", "Chuẩn bị kịch bản với mục tiêu, giọng điệu và call-to-action.", ICONS.prompt, FIELD_SETS.prompt, ["/script"]);
  featurePage("/content/storyboard", "Storyboard", "Lập storyboard bằng đúng brief, template, kênh và thời lượng mà helper canonical của bot dùng; chưa tạo media hay trừ Xu.", ICONS.prompt, FIELD_SETS.contentStoryboard, ["/storyboard"]);
  featurePage("/content/pack", "Content Pack", "Gom brief nội dung thành một bản nháp có thể ước tính qua bridge.", ICONS.prompt, FIELD_SETS.prompt, ["/content-pack"]);

  featurePage("/image/create", "Tạo ảnh", "Chuẩn bị yêu cầu tạo ảnh và đợi Core Bridge ước tính trước khi xác nhận.", ICONS.image, FIELD_SETS.imageCreate, ["/image"]);
  customerPage("/image/edit", "Image Enhance Studio", "Chỉnh màu và làm nét cơ bản deterministic từ Asset Vault; không phải AI edit, Bot job hay provider call.", ICONS.image, {
    // Native private data must hydrate before the page may advertise readiness.
    layout: "image-enhance", type: "image-operation", action: "none", status: "guarded", fields: [],
    notes: [
      "Chỉ JPEG, PNG hoặc WebP active thuộc signed Web account hiện tại được chọn. Browser gửi Asset Vault ID và thông số đã giới hạn; không gửi path, URL hoặc bytes ảnh.",
      "Công cụ áp preset màu/làm nét cục bộ deterministic. Nó không tạo chi tiết AI, không xóa vật thể/nền, không gọi provider và không thay đổi file gốc."
    ]
  });
  customerPage("/image/resize", "Resize & Aspect Studio", "Tạo PNG private từ Asset Vault bằng crop, pad hoặc blur nền đã được kiểm tra; không phải AI upscale, Bot job hay provider call.", ICONS.image, {
    // This page has two owner-scoped reads before it can become usable. Start
    // fail-closed so the first paint never advertises readiness before the
    // signed integration has returned the native gates and private data.
    layout: "image-resize", type: "image-operation", action: "none", status: "guarded", fields: [],
    notes: [
      "Chỉ JPEG, PNG hoặc WebP active thuộc signed Web account hiện tại được chọn. Browser chỉ gửi Asset Vault ID và lựa chọn khung; không gửi path, URL hoặc bytes ảnh vào thao tác.",
      "Resize là nội suy LANCZOS deterministic. Nó không tạo chi tiết AI, không retouch, không subject-aware crop và không thay đổi file gốc trong Asset Vault."
    ]
  });
  featurePage("/image/upscale", "Nâng cấp ảnh", "Gửi yêu cầu upscale từ ảnh nguồn và nhận quote canonical trước khi xác nhận.", ICONS.image, FIELD_SETS.imageSource, [], { action: "feature-estimate", actionLabel: "Ước tính Xu", estimateDirect: true });
  featurePage("/image/transform", "Image-to-Image", "Chuẩn bị biến thể từ ảnh nguồn với toàn bộ quyền kiểm tra ở Core Bridge.", ICONS.image, FIELD_SETS.imageTransform, ["/image/image-to-image"]);
  featurePage("/image/remove-background", "Xóa nền", "Tạo quote xóa nền từ ảnh nguồn; job chỉ xuất hiện sau adapter canonical.", ICONS.image, FIELD_SETS.imageSource, [], { action: "feature-estimate", actionLabel: "Ước tính Xu", estimateDirect: true });
  readOnlyPage("/image/history", "Lịch sử ảnh", "Danh sách output ảnh thuộc phiên sẽ xuất hiện sau khi bridge xác thực.", ICONS.image, "assets", ["/image/assets"]);

  featurePage("/video/create", "Video nhanh", "Chuẩn bị brief video, sau đó ước tính và xác nhận với Core Bridge.", ICONS.video, FIELD_SETS.videoContextual, ["/video"]);
  featurePage("/video/long", "Video dài", "Chuẩn bị dự án video dài; tiến độ và output chỉ đến từ job canonical.", ICONS.video, FIELD_SETS.videoStoryboard);
  featurePage("/video/product", "Video sản phẩm", "Chuẩn bị brief video sản phẩm, cảnh và CTA theo flow draft → estimate → confirm.", ICONS.video, FIELD_SETS.videoContextual);
  featurePage("/video/text-to-video", "Text-to-Video", "Chuẩn bị yêu cầu text-to-video mà không gọi provider từ trình duyệt.", ICONS.video, FIELD_SETS.videoContextual);
  featurePage("/video/image-to-video", "Image-to-Video", "Chuẩn bị input hình nguồn; bridge kiểm tra quyền sở hữu và định dạng.", ICONS.video, FIELD_SETS.videoImageToVideo);
  featurePage("/video/trend", "Video xu hướng", "Tạo brief video theo xu hướng và đợi engine có trạng thái sẵn sàng.", ICONS.video, FIELD_SETS.videoContextual);
  featurePage("/video/quick", "Quick Video", "Khởi tạo bản nháp video nhanh; không có kết quả giả lập trong UI.", ICONS.video, FIELD_SETS.videoContextual);
  featurePage("/video/multiscene", "Video nhiều cảnh", "Chuẩn bị nhiều cảnh và các thành phần media trước bước estimate.", ICONS.video, FIELD_SETS.videoStoryboard);
  readOnlyPage("/video/progress", "Tiến độ video", "Theo dõi các job video được bridge trả về cho phiên sở hữu.", ICONS.video, "jobs");
  readOnlyPage("/video/preview", "Xem trước video", "Chỉ mở preview có URL ký tạm thời và output đã qua validation.", ICONS.video, "assets");
  readOnlyPage("/video/export", "Xuất video", "Xuất file chỉ khi output hoàn tất, thuộc sở hữu người dùng và được ký tạm thời.", ICONS.video, "assets");
  guidedFeaturePage("/video/add-ons", "Video finalization", "Chọn các thành phần hoàn thiện video theo cùng cấu trúc voice, music, subtitle và logo của Bot.", ICONS.video, "video-finalization", [], [
    "Video finalization chỉ điều hướng tới workflow đã đăng ký. Mux/attachment vẫn cần job adapter canonical của Bot.",
    "Không có file nào được ghép, charge Xu hoặc báo hoàn tất chỉ từ browser."
  ]);

  readOnlyPage("/voice", "Voice Vault", "Danh mục giọng nói thuộc tài khoản, không hiển thị nếu bridge chưa xác minh phiên.", ICONS.voice, "voices", ["/voice-vault"]);
  featurePage("/voice/tts", "Text-to-Speech", "Chuẩn bị lời thoại và lựa chọn giọng trong flow có estimate rõ ràng.", ICONS.voice, FIELD_SETS.voice, ["/tts", "/voice/create"], { action: "feature-estimate", actionLabel: "Ước tính Xu", estimateDirect: true });
  featurePage("/voice/saved", "Giọng đã lưu", "Chọn một giọng từ Voice Vault thuộc sở hữu bạn; Core Bridge kiểm tra lại trạng thái trước khi estimate/confirm.", ICONS.voice, FIELD_SETS.voiceSaved, ["/voice/vault"], { action: "feature-estimate", actionLabel: "Ước tính Xu", estimateDirect: true });
  featurePage("/voice/clone", "Voice Clone", "Tính năng clone chỉ khả dụng nếu engine, mẫu audio và quyền sử dụng đã được bridge cho phép.", ICONS.voice, FIELD_SETS.voiceClone);
  readOnlyPage("/voice/preview", "Nghe thử giọng", "Preview là output riêng tư và phải dùng signed/temporary URL.", ICONS.voice, "voices");
  guardedFeaturePage("/voice/outputs", "Voice outputs", "Bot P0 chưa có adapter delivery Voice-output riêng cho Web; portal giữ trạng thái guarded thay vì trộn tài sản audio chung thành output voice.", ICONS.voice, [], [
    "Route được map để giữ parity, nhưng adapter Voice-output canonical hiện chưa được bot công bố.",
    "Không có preview, URL hay output thay thế nào được hiển thị trước một delivery contract đã ký."
  ]);

  featurePage("/music", "Music Studio", "Không gian chuẩn bị nhạc AI/SFX với prompt, policy và báo giá do bot canonical kiểm soát.", ICONS.music, FIELD_SETS.music);
  readOnlyPage("/music/library", "Thư viện nhạc", "Danh sách nhạc thuộc phiên chỉ được bridge cung cấp sau kiểm tra ownership.", ICONS.music, "assets", ["/music-library"]);
  readOnlyPage("/music/sfx-library", "Thư viện SFX", "Danh sách hiệu ứng âm thanh thuộc phiên chỉ được bridge cung cấp sau kiểm tra ownership.", ICONS.music, "assets");
  featurePage("/music/sfx", "Hiệu ứng âm thanh", "Chuẩn bị brief SFX; không tìm kho ngoài, tạo âm thanh hay charge Xu ở browser.", ICONS.music, FIELD_SETS.musicSfx);
  featurePage("/music/create", "Tạo nhạc AI", "Tạo bản nháp nhạc AI và đợi engine/ước tính từ Core Bridge.", ICONS.music, FIELD_SETS.music, ["/music/ai"]);
  featurePage("/music/song", "AI Song", "Chuẩn bị yêu cầu bài hát, cấu trúc và mood; job chỉ được tạo sau confirm.", ICONS.music, FIELD_SETS.musicSong);
  featurePage("/music/upload", "Nhạc của tôi", "Upload nhạc chỉ được bật qua URL ký tạm thời và kiểm tra MIME server-side.", ICONS.music, FIELD_SETS.musicUpload);

  featurePage("/subtitle", "Phụ đề", "Chuẩn bị phụ đề từ media nguồn với export SRT/VTT do job engine trả về.", ICONS.subtitle, FIELD_SETS.subtitleCreate);
  featurePage("/subtitle/create", "Tạo phụ đề", "Tạo bản nháp phụ đề, không giả lập transcript hay file SRT/VTT.", ICONS.subtitle, FIELD_SETS.subtitleCreate);
  featurePage("/translate", "Dịch nội dung", "Chuẩn bị yêu cầu dịch, giữ nguyên tên thương hiệu và ngôn ngữ mục tiêu.", ICONS.subtitle, FIELD_SETS.subtitleTranslate);
  featurePage("/dubbing", "Lồng tiếng", "Chuẩn bị dubbing với giọng/đích ngôn ngữ do Core Bridge xác minh.", ICONS.subtitle, FIELD_SETS.dubbing);
  featurePage("/asr", "Nhận dạng giọng nói", "Bản nháp ASR chờ output hợp lệ; không tự sinh transcript trong UI.", ICONS.subtitle, FIELD_SETS.subtitleCreate);
  readOnlyPage("/subtitle/formats", "SRT / VTT", "Quản lý định dạng phụ đề chỉ sau khi file output hợp lệ được bridge trả về.", ICONS.subtitle, "assets");
  guidedFeaturePage("/video/mux", "Mux audio & video", "Mux/fallback chỉ khả dụng sau canonical job, output validation và private delivery.", ICONS.video, "video-finalization", ["/mux"], [
    "Web không ghép audio/video cục bộ và không nhận URL hoặc path do browser đưa vào.",
    "Khi Bot công bố adapter mux canonical, route này sẽ dùng chính job và asset ownership hiện có."
  ]);

  customerPage("/documents", "Document Studio", "Không gian xử lý PDF riêng tư: chọn workflow có contract rõ ràng thay vì một form generic hoặc output mô phỏng.", ICONS.document, {
    layout: "document-hub", type: "document-hub", action: "none", status: "ready", fields: [],
    notes: [
      "Mỗi tiện ích PDF Web-native chỉ đọc source thuộc Asset Vault của signed account và tạo artifact trong storage cô lập.",
      "Không route PDF qua Bot bridge, provider, ví Xu, PayOS hay webhook thanh toán."
    ]
  });
  customerPage("/documents/pdf", "PDF tools", "Chọn công cụ PDF private có giới hạn xử lý, ownership và delivery đã xác minh.", ICONS.document, {
    layout: "document-hub", type: "document-hub", action: "none", status: "ready", fields: [],
    notes: [
      "Trang legacy này là hub điều hướng; upload/path browser không được dùng để chạy PDF generic.",
      "Mỗi output chỉ xuất hiện sau khi server kiểm tra input, renderer/parser và artifact cuối."
    ]
  }, ["/pdf"]);
  featurePage("/documents/ocr", "OCR", "Chuẩn bị OCR, đợi engine trả về kết quả được kiểm tra thay vì text giả.", ICONS.document, FIELD_SETS.documentOcr);
  customerPage("/documents/merge", "Gộp PDF riêng tư", "Gộp nhiều PDF theo thứ tự rõ ràng từ Asset Vault bằng Document Operations độc lập của Web.", ICONS.document, {
    layout: "pdf-merge", type: "document-operation", action: "none", status: "ready", fields: [],
    notes: [
      "Thứ tự PDF 1 → PDF 8 trên form là thứ tự trang trong artifact. Web chỉ nhận Asset Vault private thuộc signed account hiện tại.",
      "Mỗi nguồn được sao chép, kiểm tra và xử lý trong storage cô lập. Web không gọi Bot, provider, PayOS hoặc ví Xu cho workflow này."
    ]
  });
  customerPage("/documents/split", "Tách PDF riêng tư", "Tách một trang hoặc dải liên tiếp từ PDF trong Asset Vault bằng Document Operations độc lập của Web.", ICONS.document, {
    layout: "pdf-split", type: "document-operation", action: "none", status: "ready", fields: [],
    notes: [
      "PDF nguồn luôn được chọn từ Asset Vault của chính signed account; browser không gửi path hoặc byte PDF mới vào thao tác này.",
      "Web tạo attachment PDF riêng trong storage cô lập, kiểm tra lại output trước khi cho tải và không gọi Bot, provider, PayOS hoặc ví Xu."
    ]
  });
  customerPage("/documents/compress", "Tối ưu PDF riêng tư", "Tối ưu lossless cấu trúc PDF từ Asset Vault; chỉ phát artifact khi phiên bản cuối thật sự nhỏ hơn.", ICONS.document, {
    layout: "pdf-optimize", type: "document-operation", action: "none", status: "ready", fields: [],
    notes: [
      "Không có mức light/medium/strong giả lập. Web chỉ thực hiện một profile lossless có giới hạn và nói rõ khi PDF không thể giảm dung lượng đủ ý nghĩa.",
      "File gốc trong Asset Vault không bị thay thế. PDF đầu ra là attachment private mới, chỉ xuất hiện sau kiểm tra parser, hash và kích thước."
    ]
  });
  customerPage("/documents/image-to-pdf", "Ảnh sang PDF riêng tư", "Chuyển ảnh private trong Asset Vault thành PDF theo thứ tự rõ ràng bằng pipeline Web-native có kiểm tra decoder.", ICONS.document, {
    layout: "image-to-pdf", type: "document-operation", action: "none", status: "ready", fields: [],
    notes: [
      "Ảnh 1 → Ảnh 8 xác định thứ tự trang PDF. Web chỉ nhận JPEG, PNG hoặc WebP active thuộc signed account hiện tại; browser không gửi path, URL hoặc bytes vào thao tác.",
      "Mỗi ảnh được hash-copy vào vùng cô lập, decode/kiểm tra thật, chuẩn hóa orientation và alpha trước khi output PDF riêng được parse/hash lại. Không gọi Bot, provider, PayOS hoặc ví Xu."
    ]
  });
  customerPage("/documents/pdf-to-images", "PDF sang ảnh riêng tư", "Render PDF private trong Asset Vault thành PNG hoặc ZIP ở chất lượng 2×, với kiểm tra pixel và delivery private.", ICONS.document, {
    layout: "pdf-to-images", type: "document-operation", action: "none", status: "ready", fields: [],
    notes: [
      "Một PDF một trang trả PNG private; PDF nhiều trang trả ZIP chứa page_001.png… sau khi từng trang và archive được kiểm tra lại.",
      "Không nhận URL, path hoặc bytes từ browser; không gọi Bot, provider, PayOS, ví Xu hoặc webhook."
    ]
  });
  customerPage("/documents/pdf-to-word", "PDF có text → Word riêng tư", "Trích xuất text có thể chọn thực sự từ PDF private trong Asset Vault thành DOCX; không OCR và không cam kết giữ bố cục trực quan.", ICONS.document, {
    layout: "pdf-to-word", type: "document-operation", action: "none", status: "ready", fields: [],
    notes: [
      "Chỉ PDF active thuộc signed account hiện tại được chọn từ Asset Vault. Browser không gửi URL, path hoặc bytes PDF vào thao tác này.",
      "Nếu PDF là bản scan hoặc không có text mà parser trích xuất được, thao tác dừng ở guarded và không tạo DOCX giả. Bố cục, ảnh, font và OCR không nằm trong phạm vi này."
    ]
  });
  featurePage("/documents/translate", "Dịch tài liệu", "Dịch tài liệu bằng workflow server-side và output riêng tư đã xác minh.", ICONS.document, FIELD_SETS.documentTranslate);

  // ERP pages. Server routes remain the actual access-control boundary.
  adminPage("/admin", "Admin Overview", "Tổng quan ERP chỉ hiển thị dữ liệu được Core Bridge cấp cho signed admin session.", ICONS.admin, { layout: "admin-overview", action: "none" }, ["/admin/"]);
  adminPage("/admin/users", "Người dùng", "Tìm kiếm và xem người dùng qua quyền canonical của bot.", ICONS.users);
  adminPage("/admin/wallet", "Ví & điều chỉnh Xu", "Chỉ review dữ liệu wallet; điều chỉnh cần permission, CSRF, idempotency và audit event.", ICONS.wallet);
  adminPage("/admin/payments", "Thanh toán", "Theo dõi payment từ canonical PayOS/wallet workflow, không có webhook thứ hai.", ICONS.payments);
  adminPage("/admin/topups", "Nạp Xu", "Xem topup theo dữ liệu server; không cấp credit từ Web App.", ICONS.payments);
  adminPage("/admin/revenue", "Doanh thu", "Báo cáo doanh thu do nguồn canonical cung cấp.", ICONS.reports);
  adminPage("/admin/refunds", "Refund", "Review yêu cầu refund; thao tác cần confirmation, idempotency và audit.", ICONS.payments);
  adminPage("/admin/jobs", "Jobs", "Theo dõi toàn bộ job, trạng thái delivery và lỗi từ Core Bridge.", ICONS.jobs);
  adminPage("/admin/jobs/failed", "Jobs thất bại", "Xem job thất bại; retry chỉ được bridge quyết định để tránh double-charge.", ICONS.jobs);
  adminPage("/admin/providers", "Providers & chi phí", "Trạng thái provider/cost do runtime canonical phát hành, không lộ secret.", ICONS.providers);
  adminPage("/admin/provider-cost", "Chi phí provider", "Chi phí runtime chỉ đọc do Core Bridge redaction; không sửa rate hoặc gọi provider từ browser.", ICONS.providers);
  adminPage("/admin/workers", "Workers", "Sức khỏe worker và queue chỉ đọc qua bridge có kiểm soát.", ICONS.system);
  adminPage("/admin/features", "Feature readiness", "Kiểm tra trạng thái, guarded mode và maintenance của từng feature.", ICONS.system);
  adminPage("/admin/freezes", "Bảo trì & freeze", "Theo dõi maintenance/freeze canonical; thao tác thay đổi vẫn chờ adapter write có audit.", ICONS.system);
  adminPage("/admin/pricing", "Giá & Xu", "Review pricing catalog; không thay đổi rate hoặc chính sách trong UI tĩnh.", ICONS.pricing);
  adminPage("/admin/packages", "Packages", "Xem và review packages do backend canonical quản lý.", ICONS.pricing);
  adminPage("/admin/promos", "Khuyến mãi", "Quản lý promo phải có permission, confirmation và audit event.", ICONS.pricing);
  adminPage("/admin/leads", "Leads", "Theo dõi lead và CSKH theo quyền server-side.", ICONS.users);
  adminPage("/admin/tickets", "Tickets", "Phân luồng ticket với dữ liệu đã được kiểm soát quyền truy cập.", ICONS.ticket);
  adminPage("/admin/support", "Web Support Desk", "Không gian CSKH Web-native được máy chủ cấp quyền support riêng; không phụ thuộc Telegram admin bridge.", ICONS.support, {
    layout: "support-admin", action: "none", status: "processing",
    notes: [
      "Quyền admin, support_manager hoặc support_operator do máy chủ xác minh; browser không gửi admin ID hoặc role.",
      "Không có thao tác ví Xu, PayOS, provider, refund ledger, job hoặc external delivery trong Support Desk."
    ]
  });
  adminPage("/admin/campaigns", "Campaign Center", "Campaign, brief và kết quả chỉ đọc từ Bot canonical; chưa có adapter write nào được mở từ browser.", ICONS.prompt, {}, ["/admin/campaign", "/admin/campaign_new", "/admin/campaign_preset"]);
  adminPage("/admin/calendar", "Content Calendar", "Lịch nội dung chỉ hiển thị khi Bot cấp adapter read-only có redaction; không tạo hoặc publish lịch giả.", ICONS.system, {}, ["/admin/calendar_plan"]);
  adminPage("/admin/approvals", "Approval Queue", "Duyệt job/publish cần workflow canonical, confirmation và audit; Web giữ chế độ chỉ đọc cho đến khi adapter được phê duyệt.", ICONS.security, {}, ["/admin/approve_ready", "/admin/approve_job", "/admin/approve_publish"]);
  adminPage("/admin/publishing", "Publishing & Channels", "Publish queue, channel và automation chỉ được Bot canonical phát hành; browser không tự gửi bài hoặc tạo lịch chạy.", ICONS.assets, {}, ["/admin/publish_cockpit", "/admin/publish_queue", "/admin/publish_pack", "/admin/publish_done", "/admin/publisher_status", "/admin/publisher_run", "/admin/publisher_auto"]);
  adminPage("/admin/analytics", "Analytics", "Campaign/performance analytics là dữ liệu vận hành đã redaction; không có export hay tính doanh thu ở client.", ICONS.reports, {}, ["/admin/campaign_stats", "/admin/campaign_report", "/admin/creative_report"]);
  adminPage("/admin/audit", "Audit logs", "Dấu vết hành động write và quyết định automation phải đến từ audit canonical.", ICONS.security);
  adminPage("/admin/reports", "Báo cáo", "Tạo báo cáo trên server; không export dữ liệu từ shell khi chưa kiểm tra quyền.", ICONS.reports);
  adminPage("/admin/export", "Xuất dữ liệu", "Xuất file qua signed URL sau ownership/permission checks.", ICONS.reports);
  adminPage("/admin/runtime", "Runtime", "Tình trạng runtime và queue chỉ đọc, không thao tác hạ tầng từ browser.", ICONS.system);
  adminPage("/admin/system", "Hệ thống", "Xem thiết lập hệ thống được redaction; write actions không nằm ở shell.", ICONS.system);
  adminPage("/admin/backups", "Sao lưu", "Trạng thái backup/disaster recovery là dữ liệu server-side được phân quyền.", ICONS.system, {}, ["/admin/backup"]);
  adminPage("/admin/security", "Bảo mật", "Kiểm tra access control, session và secret hygiene với audit event.", ICONS.security);
  adminPage("/admin/access", "Quyền truy cập", "Review role/capability canonical; client không tự quyết định quyền.", ICONS.security);

  function safeText(value, fallback) {
    if (typeof value !== "string") return fallback || "";
    return value.replace(/[&<>'"]/g, (character) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;"
    }[character]));
  }

  function normalizePath(path) {
    const raw = typeof path === "string" && path ? path : window.location.pathname || "/dashboard";
    const withoutQuery = raw.split("?")[0].split("#")[0].replace(/\\/g, "/");
    if (withoutQuery === "/") return "/";
    return withoutQuery.replace(/\/+$/, "") || "/";
  }

  function normalizeBootstrap(raw) {
    const source = raw && typeof raw === "object" ? raw : {};
    const session = source.session && typeof source.session === "object" ? source.session : {};
    const bridge = source.bridge && typeof source.bridge === "object" ? source.bridge : {};
    const capabilities = source.capabilities && typeof source.capabilities === "object" ? source.capabilities : {};
    const pageStates = source.pageStates && typeof source.pageStates === "object" ? source.pageStates : {};
    const featureFlows = source.featureFlows && typeof source.featureFlows === "object" ? source.featureFlows : {};
    const workspaceDraftFeatures = Array.isArray(source.workspaceDraftFeatures)
      ? [...new Set(source.workspaceDraftFeatures.filter((item) => typeof item === "string" && /^[a-z][a-z0-9_]{1,120}$/.test(item)))].slice(0, 200)
      : [];
    return {
      path: normalizePath(source.path),
      title: typeof source.title === "string" ? source.title : "",
      isAdmin: source.isAdmin === true,
      // The registry is static, redacted route metadata. Do not truncate it:
      // `/features` must be able to disclose every mapped customer workflow.
      catalog: Array.isArray(source.catalog) ? source.catalog.slice() : [],
      workspaceDraftFeatures,
      apiBase: typeof source.apiBase === "string" ? source.apiBase : "",
      session,
      bridge: {
        ...bridge,
        featureExecutionFeatures: Array.isArray(bridge.featureExecutionFeatures)
          ? bridge.featureExecutionFeatures.filter((item) => typeof item === "string" && /^[a-z0-9_]{2,80}$/.test(item)).slice(0, 200)
          : []
      },
      capabilities,
      pageStates,
      featureFlows,
      wallet: source.wallet && typeof source.wallet === "object" ? source.wallet : null,
      walletHistory: Array.isArray(source.walletHistory) ? source.walletHistory : [],
      jobAssets: Array.isArray(source.jobAssets) ? source.jobAssets : [],
      jobs: Array.isArray(source.jobs) ? source.jobs : [],
      jobDetail: source.jobDetail && typeof source.jobDetail === "object" ? source.jobDetail : {},
      assets: Array.isArray(source.assets) ? source.assets : [],
      // Asset Vault has a distinct owner-scoped projection. Never mix it
      // with Bot delivery metadata in `assets`, whose download contract is
      // intentionally different.
      vaultItems: Array.isArray(source.vaultItems) ? source.vaultItems.slice(0, 100) : [],
      assetVaultReadState: ["loading", "ready", "failed", "guarded"].includes(String(source.assetVaultReadState || ""))
        ? String(source.assetVaultReadState)
        : "guarded",
      tickets: Array.isArray(source.tickets) ? source.tickets : [],
      // Workspace drafts are Web-owned, owner-scoped planning records. They
      // arrive after initial hydration and must survive the presentation
      // normalizer just like jobs/assets; otherwise a successful server read
      // is silently rendered as an empty library.
      workspaceDrafts: Array.isArray(source.workspaceDrafts) ? source.workspaceDrafts.slice(0, 100) : [],
      // Campaign Planner data is Web-owned and already account-scoped by the
      // API. Keep only a bounded presentation copy; the browser never keeps
      // a second campaign store in localStorage.
      campaignPlans: Array.isArray(source.campaignPlans) ? source.campaignPlans.slice(0, 100) : [],
      campaignPlanDetail: source.campaignPlanDetail && typeof source.campaignPlanDetail === "object" ? source.campaignPlanDetail : {},
      // Project Center data is a bounded, owner-scoped Web projection. Keep
      // it through presentation normalization so a successful API hydration
      // cannot render the independent Workspace as empty.
      projects: Array.isArray(source.projects) ? source.projects.slice(0, 100) : [],
      projectDetail: source.projectDetail && typeof source.projectDetail === "object" ? source.projectDetail : {},
      projectDocuments: Array.isArray(source.projectDocuments) ? source.projectDocuments.slice(0, 100) : [],
      studioDocumentDetail: source.studioDocumentDetail && typeof source.studioDocumentDetail === "object" ? source.studioDocumentDetail : {},
      // Project Packages are a separate Web-native private export surface.
      // Keep their owner-scoped metadata through every render without mixing
      // them into Bot jobs/assets or customer-uploaded Asset Vault files.
      projectPackages: Array.isArray(source.projectPackages) ? source.projectPackages.slice(0, 100) : [],
      projectPackageEvents: source.projectPackageEvents && typeof source.projectPackageEvents === "object" ? source.projectPackageEvents : {},
      projectPackageEnabled: source.projectPackageEnabled === true,
      // Memory Center has its own signed-account data model, version history
      // and reminder lifecycle. It never falls back to Bot note/reminder
      // state or browser persistence when an owner-scoped API read fails.
      memorySummary: source.memorySummary && typeof source.memorySummary === "object" ? source.memorySummary : {},
      memoryNotes: Array.isArray(source.memoryNotes) ? source.memoryNotes.slice(0, 100) : [],
      memoryReminders: Array.isArray(source.memoryReminders) ? source.memoryReminders.slice(0, 100) : [],
      memoryEvents: Array.isArray(source.memoryEvents) ? source.memoryEvents.slice(0, 50) : [],
      memoryNoteDetail: source.memoryNoteDetail && typeof source.memoryNoteDetail === "object" ? source.memoryNoteDetail : {},
      // Search/filter state stays only in the mounted page state. It is not
      // written to localStorage, the customer-visible page URL or a Bot hand-off.
      // The integration layer may send a transient owner-scoped API query.
      memoryNoteFilter: {
        q: source.memoryNoteFilter && typeof source.memoryNoteFilter.q === "string"
          ? source.memoryNoteFilter.q.replace(/\s+/g, " ").trim().slice(0, 80)
          : "",
        priority: source.memoryNoteFilter && ["", "low", "normal", "important", "urgent"].includes(String(source.memoryNoteFilter.priority || ""))
          ? String(source.memoryNoteFilter.priority || "")
          : "",
        state: source.memoryNoteFilter && ["all", "active", "archived"].includes(String(source.memoryNoteFilter.state || ""))
          ? String(source.memoryNoteFilter.state || "all")
          : "all"
      },
      memoryCenterEnabled: source.memoryCenterEnabled === true,
      memoryReadState: ["loading", "ready", "failed", "guarded"].includes(String(source.memoryReadState || ""))
        ? String(source.memoryReadState)
        : "guarded",
      // Prompt Library is a separate private template store. It remains
      // account-scoped and never falls back to Bot seed data, a bridge read or
      // browser persistence when its signed Web API hydration fails.
      promptLibraryEnabled: source.promptLibraryEnabled === true,
      promptLibrarySummary: source.promptLibrarySummary && typeof source.promptLibrarySummary === "object" ? source.promptLibrarySummary : {},
      promptTemplates: Array.isArray(source.promptTemplates) ? source.promptTemplates.slice(0, 100) : [],
      promptTemplateDetail: source.promptTemplateDetail && typeof source.promptTemplateDetail === "object" ? source.promptTemplateDetail : {},
      promptTemplatePreview: source.promptTemplatePreview && typeof source.promptTemplatePreview === "object" ? source.promptTemplatePreview : {},
      promptLibraryEvents: Array.isArray(source.promptLibraryEvents) ? source.promptLibraryEvents.slice(0, 50) : [],
      promptLibraryFilter: {
        q: source.promptLibraryFilter && typeof source.promptLibraryFilter.q === "string" ? source.promptLibraryFilter.q.replace(/\s+/g, " ").trim().slice(0, 100) : "",
        category: source.promptLibraryFilter && typeof source.promptLibraryFilter.category === "string" ? source.promptLibraryFilter.category.replace(/\s+/g, " ").trim().slice(0, 100) : "",
        platform: source.promptLibraryFilter && typeof source.promptLibraryFilter.platform === "string" ? source.promptLibraryFilter.platform.replace(/\s+/g, " ").trim().slice(0, 100) : "",
        product_context: source.promptLibraryFilter && typeof source.promptLibraryFilter.product_context === "string" ? source.promptLibraryFilter.product_context.replace(/\s+/g, " ").trim().slice(0, 100) : "",
        tag: source.promptLibraryFilter && typeof source.promptLibraryFilter.tag === "string" ? source.promptLibraryFilter.tag.replace(/\s+/g, " ").trim().slice(0, 48) : "",
        state: source.promptLibraryFilter && ["all", "active", "archived"].includes(String(source.promptLibraryFilter.state || "")) ? String(source.promptLibraryFilter.state) : "all"
      },
      promptLibraryReadState: ["loading", "ready", "failed", "guarded"].includes(String(source.promptLibraryReadState || "")) ? String(source.promptLibraryReadState) : "guarded",
      // Audio Library & Briefing is a separate owner-scoped Web workspace.
      // It retains only server-redacted metadata in presentation state and
      // never falls back to Bot music data, provider results, raw URLs or a
      // browser-side audio cache when signed hydration fails.
      mediaWorkspaceEnabled: source.mediaWorkspaceEnabled === true,
      mediaWorkspaceSummary: source.mediaWorkspaceSummary && typeof source.mediaWorkspaceSummary === "object" ? source.mediaWorkspaceSummary : {},
      mediaCollections: Array.isArray(source.mediaCollections) ? source.mediaCollections.slice(0, 100) : [],
      mediaCollectionDetail: source.mediaCollectionDetail && typeof source.mediaCollectionDetail === "object" ? source.mediaCollectionDetail : {},
      mediaComposer: source.mediaComposer && typeof source.mediaComposer === "object" ? source.mediaComposer : {},
      mediaAudioAssets: Array.isArray(source.mediaAudioAssets) ? source.mediaAudioAssets.slice(0, 100) : [],
      mediaWorkspaceEvents: Array.isArray(source.mediaWorkspaceEvents) ? source.mediaWorkspaceEvents.slice(0, 50) : [],
      mediaWorkspacePolicy: source.mediaWorkspacePolicy && typeof source.mediaWorkspacePolicy === "object" ? source.mediaWorkspacePolicy : {},
      mediaWorkspaceFilter: {
        q: source.mediaWorkspaceFilter && typeof source.mediaWorkspaceFilter.q === "string" ? source.mediaWorkspaceFilter.q.replace(/\s+/g, " ").trim().slice(0, 100) : "",
        tag: source.mediaWorkspaceFilter && typeof source.mediaWorkspaceFilter.tag === "string" ? source.mediaWorkspaceFilter.tag.replace(/\s+/g, " ").trim().slice(0, 48) : "",
        prompt_mode: source.mediaWorkspaceFilter && ["", "background", "lyrics", "script", "melody", "custom"].includes(String(source.mediaWorkspaceFilter.prompt_mode || "")) ? String(source.mediaWorkspaceFilter.prompt_mode || "") : "",
        state: source.mediaWorkspaceFilter && ["all", "active", "archived"].includes(String(source.mediaWorkspaceFilter.state || "")) ? String(source.mediaWorkspaceFilter.state || "all") : "all"
      },
      mediaWorkspaceReadState: ["loading", "ready", "failed", "guarded"].includes(String(source.mediaWorkspaceReadState || "")) ? String(source.mediaWorkspaceReadState) : "guarded",
      // Content Studio is a standalone signed-account authoring surface.
      // Keep only bounded owner-scoped projections; no generic Bot fallback or
      // browser persistence can refill this state after a failed hydration.
      contentStudioEnabled: source.contentStudioEnabled === true,
      contentStudioSummary: source.contentStudioSummary && typeof source.contentStudioSummary === "object" ? source.contentStudioSummary : {},
      contentBriefs: Array.isArray(source.contentBriefs) ? source.contentBriefs.slice(0, 100) : [],
      contentBriefDetail: source.contentBriefDetail && typeof source.contentBriefDetail === "object" ? source.contentBriefDetail : {},
      contentVariantHistory: source.contentVariantHistory && typeof source.contentVariantHistory === "object" ? source.contentVariantHistory : {},
      contentStudioComposer: source.contentStudioComposer && typeof source.contentStudioComposer === "object" ? source.contentStudioComposer : {},
      contentStudioReferences: source.contentStudioReferences && typeof source.contentStudioReferences === "object" ? source.contentStudioReferences : {},
      contentStudioEvents: Array.isArray(source.contentStudioEvents) ? source.contentStudioEvents.slice(0, 50) : [],
      contentStudioPolicy: source.contentStudioPolicy && typeof source.contentStudioPolicy === "object" ? source.contentStudioPolicy : {},
      contentStudioFilter: {
        q: source.contentStudioFilter && typeof source.contentStudioFilter.q === "string" ? source.contentStudioFilter.q.replace(/\s+/g, " ").trim().slice(0, 100) : "",
        tag: source.contentStudioFilter && typeof source.contentStudioFilter.tag === "string" ? source.contentStudioFilter.tag.replace(/\s+/g, " ").trim().slice(0, 48) : "",
        content_kind: source.contentStudioFilter && ["", "caption_hashtag", "content_ideas", "hook_script", "content_pack", "storyboard"].includes(String(source.contentStudioFilter.content_kind || "")) ? String(source.contentStudioFilter.content_kind || "") : "",
        state: source.contentStudioFilter && ["all", "active", "archived"].includes(String(source.contentStudioFilter.state || "")) ? String(source.contentStudioFilter.state || "all") : "all"
      },
      contentStudioReadState: ["loading", "ready", "failed", "guarded"].includes(String(source.contentStudioReadState || "")) ? String(source.contentStudioReadState) : "guarded",
      // Voice Studio is deliberately a separate Web-native authoring
      // projection. It must never be conflated with Bot Voice Vault profiles
      // or hydrated from generic `/voice` bridge data after a private read
      // fails. The browser retains only bounded, account-scoped metadata.
      voiceStudioEnabled: source.voiceStudioEnabled === true,
      voiceStudioSummary: source.voiceStudioSummary && typeof source.voiceStudioSummary === "object" ? source.voiceStudioSummary : {},
      voiceVaults: Array.isArray(source.voiceVaults) ? source.voiceVaults.slice(0, 100) : [],
      voiceVaultDetail: source.voiceVaultDetail && typeof source.voiceVaultDetail === "object" ? source.voiceVaultDetail : {},
      voiceStudioReferences: source.voiceStudioReferences && typeof source.voiceStudioReferences === "object" ? source.voiceStudioReferences : {},
      voiceStudioEvents: Array.isArray(source.voiceStudioEvents) ? source.voiceStudioEvents.slice(0, 50) : [],
      voiceStudioPolicy: source.voiceStudioPolicy && typeof source.voiceStudioPolicy === "object" ? source.voiceStudioPolicy : {},
      voiceCueSheet: source.voiceCueSheet && typeof source.voiceCueSheet === "object" ? source.voiceCueSheet : {},
      voiceStudioFilter: {
        q: source.voiceStudioFilter && typeof source.voiceStudioFilter.q === "string" ? source.voiceStudioFilter.q.replace(/\s+/g, " ").trim().slice(0, 100) : "",
        tag: source.voiceStudioFilter && typeof source.voiceStudioFilter.tag === "string" ? source.voiceStudioFilter.tag.replace(/\s+/g, " ").trim().slice(0, 48) : "",
        state: source.voiceStudioFilter && ["all", "active", "archived"].includes(String(source.voiceStudioFilter.state || "")) ? String(source.voiceStudioFilter.state || "all") : "all"
      },
      voiceStudioReadState: ["loading", "ready", "failed", "guarded"].includes(String(source.voiceStudioReadState || "")) ? String(source.voiceStudioReadState) : "guarded",
      // Image Creative Studio is a distinct owner-scoped planning surface.
      // Preserve only bounded safe metadata from its signed API; a failed
      // hydration must never fall back to legacy `/image`, a prior account,
      // browser cached artwork, provider data or a fabricated preview.
      imageStudioEnabled: source.imageStudioEnabled === true,
      imageStudioSummary: source.imageStudioSummary && typeof source.imageStudioSummary === "object" ? source.imageStudioSummary : {},
      imageArtboards: Array.isArray(source.imageArtboards) ? source.imageArtboards.slice(0, 100) : [],
      imageArtboardDetail: source.imageArtboardDetail && typeof source.imageArtboardDetail === "object" ? source.imageArtboardDetail : {},
      imageArtboardEstimate: source.imageArtboardEstimate && typeof source.imageArtboardEstimate === "object" ? source.imageArtboardEstimate : {},
      imageStudioReferences: source.imageStudioReferences && typeof source.imageStudioReferences === "object" ? source.imageStudioReferences : {},
      imageStudioEvents: Array.isArray(source.imageStudioEvents) ? source.imageStudioEvents.slice(0, 50) : [],
      imageStudioPolicy: source.imageStudioPolicy && typeof source.imageStudioPolicy === "object" ? source.imageStudioPolicy : {},
      imageStudioReadState: ["loading", "ready", "failed", "guarded"].includes(String(source.imageStudioReadState || "")) ? String(source.imageStudioReadState) : "guarded",
      // Support Desk is a separate Web-native case store.  It never falls
      // back to Bot support/ticket state, and redacted page data must survive
      // render normalization after a successful owner-scoped hydration.
      supportDeskEnabled: source.supportDeskEnabled === true,
      supportSummary: source.supportSummary && typeof source.supportSummary === "object" ? source.supportSummary : {},
      supportCases: Array.isArray(source.supportCases) ? source.supportCases.slice(0, 100) : [],
      supportEvents: Array.isArray(source.supportEvents) ? source.supportEvents.slice(0, 100) : [],
      supportCaseDetail: source.supportCaseDetail && typeof source.supportCaseDetail === "object" ? source.supportCaseDetail : {},
      supportCaseFilter: {
        q: source.supportCaseFilter && typeof source.supportCaseFilter.q === "string"
          ? source.supportCaseFilter.q.replace(/\s+/g, " ").trim().slice(0, 80)
          : "",
        state: source.supportCaseFilter && ["all", "new", "reviewing", "waiting_user", "waiting_provider", "refund_pending", "resolved", "closed"].includes(String(source.supportCaseFilter.state || ""))
          ? String(source.supportCaseFilter.state)
          : "all",
        category: source.supportCaseFilter && /^[a-z_]{0,48}$/.test(String(source.supportCaseFilter.category || ""))
          ? String(source.supportCaseFilter.category || "")
          : ""
      },
      supportReadState: ["loading", "ready", "failed", "guarded"].includes(String(source.supportReadState || ""))
        ? String(source.supportReadState)
        : "guarded",
      supportAdminSummary: source.supportAdminSummary && typeof source.supportAdminSummary === "object" ? source.supportAdminSummary : {},
      supportAdminCases: Array.isArray(source.supportAdminCases) ? source.supportAdminCases.slice(0, 100) : [],
      supportAdminCaseDetail: source.supportAdminCaseDetail && typeof source.supportAdminCaseDetail === "object" ? source.supportAdminCaseDetail : {},
      supportAdminCaseFilter: {
        q: source.supportAdminCaseFilter && typeof source.supportAdminCaseFilter.q === "string"
          ? source.supportAdminCaseFilter.q.replace(/\s+/g, " ").trim().slice(0, 80)
          : "",
        state: source.supportAdminCaseFilter && ["all", "new", "reviewing", "waiting_user", "waiting_provider", "refund_pending", "resolved", "closed"].includes(String(source.supportAdminCaseFilter.state || ""))
          ? String(source.supportAdminCaseFilter.state)
          : "all",
        category: source.supportAdminCaseFilter && /^[a-z_]{0,48}$/.test(String(source.supportAdminCaseFilter.category || ""))
          ? String(source.supportAdminCaseFilter.category || "")
          : ""
      },
      supportAdminReadState: ["loading", "ready", "failed", "guarded"].includes(String(source.supportAdminReadState || ""))
        ? String(source.supportAdminReadState)
        : "guarded",
      // Document Operations output is a third, independent private surface:
      // it is neither an Asset Vault source blob nor a Bot delivery/job.
      documentOperations: Array.isArray(source.documentOperations) ? source.documentOperations.slice(0, 100) : [],
      documentOperationsEnabled: source.documentOperationsEnabled === true,
      imageToPdfEnabled: source.imageToPdfEnabled === true,
      pdfToWordEnabled: source.pdfToWordEnabled === true,
      // Resize Studio has its own private output schema and read readiness.
      // Preserve both through normalisation so a successful signed hydration
      // cannot be mistaken for an empty/static browser projection.
      imageOperations: Array.isArray(source.imageOperations) ? source.imageOperations.slice(0, 100) : [],
      imageOperationsEnabled: source.imageOperationsEnabled === true,
      imageResizeEnabled: source.imageResizeEnabled === true,
      imageOperationsReadState: ["loading", "ready", "failed", "guarded"].includes(String(source.imageOperationsReadState || ""))
        ? String(source.imageOperationsReadState)
        : "guarded",
      // Enhance history is a separate owner-scoped projection. Keeping it
      // distinct prevents a previously viewed Resize row from momentarily
      // looking like an Image Enhance result during route hydration.
      imageEnhanceOperations: Array.isArray(source.imageEnhanceOperations) ? source.imageEnhanceOperations.slice(0, 100) : [],
      imageEnhanceEnabled: source.imageEnhanceEnabled === true,
      imageEnhanceOperationsReadState: ["loading", "ready", "failed", "guarded"].includes(String(source.imageEnhanceOperationsReadState || ""))
        ? String(source.imageEnhanceOperationsReadState)
        : "guarded",
      // Account activity is already a redacted, owner-scoped projection from
      // the Web API. Retain the bounded list during each presentation pass so
      // a successful signed read cannot be rendered as an empty history.
      accountActivity: Array.isArray(source.accountActivity) ? source.accountActivity.slice(0, 50) : [],
      adminData: source.adminData && typeof source.adminData === "object" ? source.adminData : {},
      pricingCatalog: source.pricingCatalog && typeof source.pricingCatalog === "object" ? source.pricingCatalog : {},
      packageCatalog: source.packageCatalog && typeof source.packageCatalog === "object" ? source.packageCatalog : {},
      // These are hydrated asynchronously by integration.js.  Preserve their
      // redacted, browser-safe values across render cycles so a real OAuth
      // configuration or a pending Telegram challenge is reflected in the UI
      // instead of falling back to a disabled/default card.
      oauthProviders: source.oauthProviders && typeof source.oauthProviders === "object" ? source.oauthProviders : {},
      telegramConnection: source.telegramConnection && typeof source.telegramConnection === "object" ? source.telegramConnection : {},
      telegramLoginFlow: source.telegramLoginFlow && typeof source.telegramLoginFlow === "object" ? source.telegramLoginFlow : {},
      paymentOptions: source.paymentOptions && typeof source.paymentOptions === "object" ? source.paymentOptions : {},
      paymentFlow: source.paymentFlow && typeof source.paymentFlow === "object" ? source.paymentFlow : {},
      linkFlow: source.linkFlow && typeof source.linkFlow === "object" ? source.linkFlow : {},
      linkStatus: source.linkStatus && typeof source.linkStatus === "object" ? source.linkStatus : {},
      jobFilter: typeof source.jobFilter === "string" ? source.jobFilter : "all",
      assetFilter: typeof source.assetFilter === "string" ? source.assetFilter : "all",
      ticketFilter: typeof source.ticketFilter === "string" ? source.ticketFilter : "all",
      readiness: source.readiness && typeof source.readiness === "object" ? source.readiness : {},
      voiceProfiles: Array.isArray(source.voiceProfiles) ? source.voiceProfiles.slice(0, 20) : [],
      profile: source.profile && typeof source.profile === "object" ? source.profile : {},
      pwaEnabled: source.pwaEnabled === true,
      notifications: Array.isArray(source.notifications) ? source.notifications.slice(0, 5) : []
    };
  }

  function getBootstrap() {
    return normalizeBootstrap(window.__TOAN_AAS_PORTAL__);
  }

  function stateFor(page, context) {
    const stateValue = context.pageStates[page.path] || context.pageStates[normalizePath(context.path)];
    const candidate = typeof stateValue === "string" ? stateValue : stateValue && stateValue.status;
    return ALLOWED_STATES.has(candidate) ? candidate : page.status;
  }

  function resolvePage(path) {
    const normalized = normalizePath(path);
    if (manifest[normalized]) return manifest[normalized];
    if (/^\/campaigns\/[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(normalized)) {
      const planId = normalized.split("/").pop();
      return Object.freeze({
        path: "/campaigns/:id", routePath: normalized, title: "Chi tiết kế hoạch", icon: ICONS.prompt, section: "Campaign Planner",
        description: "Xem, chỉnh brief và tự rà soát một kế hoạch Web-owned thuộc signed session hiện tại.",
        status: "read_only", access: "member", layout: "campaign-detail", action: "none", actionLabel: "", fields: [],
        recordId: planId,
        notes: ["Kế hoạch này chỉ là metadata Web-owned, không phải campaign canonical của Bot.", "Không publish, tạo analytics/revenue, job, Xu hoặc PayOS từ trang chi tiết."]
      });
    }
    if (/^\/prompt-library\/[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(normalized)) {
      const templateId = normalized.split("/").pop();
      return Object.freeze({
        path: "/prompt-library/:id", routePath: normalized, title: "Chi tiết template", icon: ICONS.prompt, section: "Prompt Library",
        description: "Chỉnh metadata, xem version history và preview cục bộ của một template thuộc Web account hiện tại.",
        status: "read_only", access: "member", layout: "prompt-library-detail", action: "none", actionLabel: "", fields: [],
        recordId: templateId,
        notes: ["Template chỉ được nạp sau owner check ở server. Không có JSON seed/global path từ Bot, provider, job, Xu hoặc PayOS trong trang này.", "Preview thay variable đã khai báo theo dữ liệu bạn nhập; đó không phải AI execution hoặc output."]
      });
    }
    if (/^\/media-workspace\/[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(normalized)) {
      const collectionId = normalized.split("/").pop();
      return Object.freeze({
        path: "/media-workspace/:id", routePath: normalized, title: "Audio Collection", icon: ICONS.music, section: "Audio Library & Briefing",
        description: "Chỉnh metadata, gắn audio Asset Vault và xem history của một collection riêng tư thuộc signed Web account hiện tại.",
        status: "processing", access: "member", layout: "media-workspace-detail", action: "none", actionLabel: "", fields: [],
        recordId: collectionId,
        notes: ["Asset chỉ là tham chiếu private đến Asset Vault và tải qua attachment route hiện có; trang này không phát audio, waveform, URL provider hoặc Telegram file ID.", "Composer chỉ tạo text direction cục bộ. Nó không chạy AI, tạo job, charge Xu, output hay delivery."]
      });
    }
    if (/^\/content-studio\/[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(normalized)) {
      const briefId = normalized.split("/").pop();
      return Object.freeze({
        path: "/content-studio/:id", routePath: normalized, title: "Creative Content Studio", icon: ICONS.prompt, section: "Content Studio",
        description: "Biên tập brief, content pieces, selection và version history thuộc signed Web account hiện tại.",
        status: "processing", access: "member", layout: "content-studio-detail", action: "none", actionLabel: "", fields: [],
        recordId: briefId,
        notes: ["Brief và content pieces chỉ được nạp qua owner check. Không có generic Bot bridge hoặc browser storage fallback.", "Composer chỉ tạo khung nháp cục bộ có nhãn rõ ràng; không chạy AI, tạo job, charge, output media hay publish."]
      });
    }
    if (/^\/voice-studio\/[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(normalized)) {
      const vaultId = normalized.split("/").pop();
      return Object.freeze({
        path: "/voice-studio/:id", routePath: normalized, title: "Voice Studio", icon: ICONS.voice, section: "Voice Studio & Consent Vault",
        description: "Biên tập voice direction, consent metadata, script và version history thuộc signed Web account hiện tại.",
        status: "processing", access: "member", layout: "voice-studio-detail", action: "none", actionLabel: "", fields: [],
        recordId: vaultId,
        notes: ["Voice direction là metadata Web-owned, không phải Bot Voice Vault profile hoặc provider voice. Owner check luôn xảy ra ở server.", "Cue-sheet chỉ ước lượng thời lượng theo text; không gọi TTS, clone, preview, upload audio, job, Xu, PayOS hoặc delivery."]
      });
    }
    if (/^\/video-studio\/[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(normalized)) {
      const planId = normalized.split("/").pop();
      return Object.freeze({
        path: "/video-studio/:id", routePath: normalized, title: "Video Production Studio", icon: ICONS.video, section: "Video Production Studio",
        description: "Biên tập plan, scene, self-review và version history thuộc signed Web account hiện tại.",
        status: "processing", access: "member", layout: "video-studio-detail", action: "none", actionLabel: "", fields: [],
        recordId: planId,
        notes: ["Plan chỉ là authoring metadata Web-owned. Không có render, media URL, kết quả hoặc delivery được tạo ở trang này.", "Approved chỉ đánh dấu self-review nội bộ; quyền sở hữu và mọi bước thực thi tương lai cần contract riêng."]
      });
    }
    if (/^\/image-studio\/[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(normalized)) {
      const artboardId = normalized.split("/").pop();
      return Object.freeze({
        path: "/image-studio/:id", routePath: normalized, title: "Image Creative Studio", icon: ICONS.image, section: "Image Creative Studio",
        description: "Biên tập art direction, reference Asset Vault, biến thể và version history thuộc signed Web account hiện tại.",
        status: "processing", access: "member", layout: "image-studio-detail", action: "none", actionLabel: "", fields: [],
        recordId: artboardId,
        notes: ["Artboard và direction chỉ là authoring metadata Web-owned. Không tạo ảnh, thumbnail, preview, URL media, job hay delivery.", "Reference chỉ là metadata Asset Vault đã qua owner check; Resize/Enhance Web-native là utility riêng, không phải provider image engine."]
      });
    }
    if (/^\/document-workspace\/[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(normalized)) {
      const workspaceId = normalized.split("/").pop();
      return Object.freeze({
        path: "/document-workspace/:id", routePath: normalized, title: "Document & PDF Workspace", icon: ICONS.document, section: "Document & PDF Workspace",
        description: "Biên tập document brief, processing plan, self-review và version history thuộc signed Web account hiện tại.",
        status: "processing", access: "member", layout: "document-workspace-detail", action: "none", actionLabel: "", fields: [],
        recordId: workspaceId,
        notes: ["Workspace và plan chỉ là authoring metadata Web-owned. Không upload/đọc source file, OCR, dịch, convert, preview, output, job hoặc delivery.", "Asset Vault reference chỉ là metadata đã qua owner check. Các PDF utility deterministic là route riêng, không nhận lifecycle hay output từ workspace này."]
      });
    }
    if (/^\/subtitle-studio\/[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(normalized)) {
      const transcriptProjectId = normalized.split("/").pop();
      return Object.freeze({
        path: "/subtitle-studio/:id", routePath: normalized, title: "Subtitle & Transcript Workspace", icon: ICONS.subtitle, section: "Subtitle & Transcript Workspace",
        description: "Biên tập transcript project, cue timeline, bản nháp ngôn ngữ và version history thuộc signed Web account hiện tại.",
        status: "processing", access: "member", layout: "subtitle-studio-detail", action: "none", actionLabel: "", fields: [],
        recordId: transcriptProjectId,
        notes: ["Cue chỉ là văn bản do người biên tập nhập và không chứng minh rằng ASR, translation, TTS hoặc dubbing đã chạy.", "SRT/VTT preview được hiển thị dạng text an toàn, không có tệp, URL media, player hay delivery."]
      });
    }
    if (/^\/projects\/[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(normalized)) {
      const projectId = normalized.split("/").pop();
      return Object.freeze({
        path: "/projects/:id", routePath: normalized, title: "Project Workspace", icon: ICONS.dashboard, section: "Project Center",
        description: "Quản lý Studio Document có version history trong Project thuộc Web account hiện tại.",
        status: "read_only", access: "member", layout: "project-detail", action: "none", actionLabel: "", fields: [],
        recordId: projectId,
        notes: ["Dữ liệu ở đây thuộc Web Workspace và không phụ thuộc Telegram hoặc Bot bridge.", "Version history lưu nội dung authoring của bạn; không tạo provider job, charge, PayOS hay asset media."]
      });
    }
    if (/^\/jobs\/[^/]+$/.test(normalized)) {
      const jobId = normalized.split("/").pop();
      return Object.freeze({
        path: "/jobs/:id", routePath: normalized, title: "Chi tiết job", icon: ICONS.jobs, section: "Job Center",
        description: "Trạng thái, output và download chỉ hiển thị nếu Core Bridge xác minh ownership và delivery hợp lệ.",
        status: "empty", access: "member", layout: "job-detail", action: "none", actionLabel: "", fields: [],
        recordId: jobId, notes: ["Không có preview hoặc download giả.", "Output riêng tư cần URL ký tạm thời từ Core Bridge."]
      });
    }
    if (/^\/tickets\/[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(normalized)) {
      const caseId = normalized.split("/").pop();
      return Object.freeze({
        path: "/tickets/:id", routePath: normalized, title: "Chi tiết yêu cầu", icon: ICONS.ticket, section: "Web Support Desk",
        description: "Xem timeline và phản hồi một yêu cầu Web-native thuộc signed account hiện tại.",
        status: "processing", access: "member", layout: "support-case-detail", action: "none", actionLabel: "", fields: [],
        recordId: caseId,
        notes: ["Chỉ account sở hữu case này có thể xem, phản hồi, đóng hoặc mở lại.", "Phản hồi chỉ hiển thị trong Web Support Desk; không tạo thông báo Telegram, email hay provider."]
      });
    }
    if (/^\/admin\/support\/[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(normalized)) {
      const caseId = normalized.split("/").pop();
      return Object.freeze({
        path: "/admin/support/:id", routePath: normalized, title: "Xử lý yêu cầu", icon: ICONS.support, section: "Web Support Desk",
        description: "Triage một yêu cầu Web-native theo quyền Support Desk do máy chủ xác minh.",
        status: "processing", access: "admin", layout: "support-admin-case-detail", type: "admin", action: "none", actionLabel: "", fields: [],
        recordId: caseId,
        notes: ["Vai trò support do máy chủ xác minh, không nhận role hoặc admin ID từ browser.", "Operator không gửi external delivery, thay đổi ví Xu/PayOS, refund ledger, provider hoặc trạng thái job từ trang này."]
      });
    }
    if (/^\/admin\/users\/[^/]+$/.test(normalized)) {
      const userId = normalized.split("/").pop();
      return Object.freeze({
        path: "/admin/users/:id", routePath: normalized, title: "Chi tiết người dùng", icon: ICONS.users, section: "Admin ERP",
        description: "Thông tin người dùng chỉ xuất hiện sau permission check server-side và được redaction theo role.",
        status: "read_only", access: "admin", layout: "admin", type: "admin", action: "none", actionLabel: "",
        fields: [], recordId: userId,
        notes: ["Không sử dụng admin_id do browser gửi.", "Wallet adjustment/refund cần Core Bridge, CSRF, idempotency và audit."]
      });
    }
    if (normalized === "/admin" || normalized.startsWith("/admin/")) {
      const label = normalized.split("/").filter(Boolean).slice(1).join(" · ").replace(/[-_]/g, " ") || "Tổng quan";
      return Object.freeze({
        path: "/admin/:module", routePath: normalized, title: `Admin · ${label}`, icon: ICONS.admin, section: "Admin ERP",
        description: "Compatibility surface cho command quản trị của bot. Core Bridge phải xác minh quyền, confirmation, CSRF và audit trước mọi thay đổi.",
        status: "read_only", access: "admin", layout: "admin", type: "admin", action: "none", actionLabel: "", fields: [],
        notes: ["Không dùng admin ID do browser gửi.", "Nếu bot chưa có adapter Web đã kiểm chứng, action được giữ guarded và có audit."]
      });
    }
    const featureFamily = featureFamilyForPath(normalized);
    if (featureFamily) {
      return Object.freeze({
        path: "/features/:family", routePath: normalized, featureFamily: featureFamily.key,
        title: featureFamily.title, icon: featureFamilyIcon(featureFamily.key), section: "AI Studio",
        description: `${featureFamily.description} Chọn một workflow đã đăng ký; phần authoring Web và trạng thái engine/integration được hiển thị tách biệt.`,
        status: "read_only", access: "member", layout: "feature-family", action: "none", actionLabel: "", fields: [],
        notes: [
          "Đây là điều hướng cho các workflow đã đăng ký, không phải endpoint chạy provider.",
          "Card guarded giữ nguyên trạng thái cho đến khi Web Engine hoặc integration tùy chọn công bố adapter đã kiểm thử."
        ]
      });
    }
    if (normalized === "/features" || normalized.startsWith("/features/")) {
      const label = normalized.split("/").filter(Boolean).slice(1).join(" · ").replace(/[-_]/g, " ") || "Tính năng";
      return Object.freeze({
        path: "/features/:module", routePath: normalized, title: `Feature · ${label}`, icon: ICONS.prompt, section: "Feature parity",
        description: "Compatibility surface được tạo từ inventory bot. Route giữ guarded cho đến khi có capability Web hoặc integration đã được kiểm thử.",
        status: "guarded", access: "member", layout: "workspace", action: "none", actionLabel: "", fields: [],
        notes: ["Tính năng bot chưa có adapter Web không bị báo thành công giả.", "Kiểm tra parity matrix để biết trạng thái và blocker chính xác."]
      });
    }
    return Object.freeze({
      path: "/not-found", routePath: normalized, title: "Trang chưa được định tuyến", icon: ICONS.default, section: "TOAN AAS",
      description: "Route này chưa được Web App công bố. Không có hành động hay dữ liệu nào được thực thi.",
      status: "guarded", access: "public", layout: "not-found", action: "none", actionLabel: "", fields: [], notes: []
    });
  }

  function canAct(page, context) {
    if (!page.action || page.action === "none") return false;
    const capability = context.capabilities[page.action] === true || context.capabilities[page.path] === true;
    const csrfReady = context.session.csrfReady === true || context.bridge.csrfReady === true;
    const bridgeReady = context.bridge.available === true;
    if (page.access === "public") return capability;
    if (WEB_LOCAL_ACTIONS.has(page.action)) return context.session.authenticated === true && csrfReady && capability;
    if (page.action === "start-telegram-link" || page.action === "refresh-link-status") return context.session.authenticated === true && csrfReady && capability;
    if (page.access === "admin" && !context.isAdmin) return false;
    if (page.action === "payment-create") {
      const payos = context.paymentOptions && context.paymentOptions.payos;
      return context.session.authenticated === true && csrfReady && bridgeReady && capability && Boolean(payos && payos.topup_catalog_available === true);
    }
    return context.session.authenticated === true && csrfReady && bridgeReady && capability;
  }

  function telegramIdentityLinked(context) {
    return Boolean(
      context && (
        (context.linkStatus && context.linkStatus.linked === true)
        || (context.bridge && context.bridge.available === true)
      )
    );
  }

  function actionBlockReason(page, context) {
    if (page.action === "start-telegram-link" && !telegramConnectionReady(context)) return telegramConnectionBlockReason(context);
    if (page.access === "admin" && !context.isAdmin) return "Cần signed admin session do máy chủ xác minh.";
    if (context.session.authenticated !== true && page.access !== "public") return "Cần signed session trước khi tạo yêu cầu.";
    if (WEB_LOCAL_ACTIONS.has(page.action)) {
      const supportAction = String(page.action || "").startsWith("support-");
      if (context.session.csrfReady !== true && context.bridge.csrfReady !== true) return supportAction
        ? "CSRF chưa sẵn sàng; thao tác Support Desk đang được khóa an toàn."
        : "CSRF chưa sẵn sàng; thay đổi kế hoạch Web đang được khóa an toàn.";
      return supportAction ? "Khả năng Support Desk chưa sẵn sàng cho phiên hiện tại." : "Khả năng lập kế hoạch Web chưa sẵn sàng cho phiên hiện tại.";
    }
    const linkAction = page.action === "start-telegram-link" || page.action === "refresh-link-status";
    if (page.access === "member" && !linkAction && !telegramIdentityLinked(context)) return "Cần liên kết Telegram trong Bot trước khi dùng workflow canonical.";
    if (context.bridge.available !== true && page.access !== "public") return "Core Bridge chưa được máy chủ bật cho phiên này.";
    if (context.session.csrfReady !== true && context.bridge.csrfReady !== true) return "CSRF chưa sẵn sàng; yêu cầu write bị khóa an toàn.";
    if (page.action === "payment-create" && context.paymentOptions && context.paymentOptions.payos && context.paymentOptions.payos.topup_catalog_available !== true) return "Danh mục mệnh giá nạp canonical chưa được bridge cấp cho Web. Dùng /naptien trong bot đã liên kết để tạo PayOS QR động.";
    return "Khả năng này chưa được Core Bridge cấp cho phiên hiện tại.";
  }

  function badge(status) {
    const normalized = ALLOWED_STATES.has(status) ? status : "guarded";
    return `<span class="portal-badge" data-status="${normalized}">${safeText(STATE_LABELS[normalized] || normalized)}</span>`;
  }

  function icon(name) { return safeText(ICONS[name] || name || ICONS.default); }

  function displayName(context) {
    const candidate = context.profile.displayName || context.profile.name || context.session.displayName || context.session.email;
    return typeof candidate === "string" && candidate.trim() ? candidate.trim().slice(0, 80) : "Phiên bảo mật đang chờ";
  }

  function displayPageTitle(page, context) {
    const serverTitle = typeof context.title === "string" ? context.title.trim() : "";
    // The server intentionally uses the generic product name for unknown and
    // compatibility paths. A resolved portal page has richer metadata, so do
    // not let that generic placeholder erase its title in the UI/tab.
    return serverTitle && serverTitle !== "TOAN AAS" ? serverTitle : (page.title || "TOAN AAS");
  }

  function initials(name) {
    return safeText((name || "T").trim().charAt(0).toUpperCase() || "T");
  }

  function navGroups(context, currentPage) {
    const groups = [
      {
        label: "Workspace",
        links: [
          ["/dashboard", "Tổng quan", ICONS.dashboard], ["/projects", "Project Center", ICONS.dashboard], ["/project-packages", "Project Packages", ICONS.package], ["/asset-vault", "Asset Vault", ICONS.assets], ["/workspace", "Bản nháp", ICONS.prompt], ["/prompt-library", "Prompt Library", ICONS.prompt], ["/content-studio", "Content Studio", ICONS.prompt], ["/image-studio", "Image Studio", ICONS.image], ["/document-workspace", "Document Workspace", ICONS.document], ["/video-studio", "Video Studio", ICONS.video], ["/subtitle-studio", "Subtitle Studio", ICONS.subtitle], ["/voice-studio", "Voice Studio", ICONS.voice], ["/media-workspace", "Audio Library", ICONS.music], ["/notes", "Memory Center", ICONS.prompt], ["/reminders", "Nhắc việc", ICONS.jobs], ["/campaigns", "Kế hoạch nội dung", ICONS.prompt], ["/calendar", "Lịch nội dung", ICONS.system], ["/approvals", "Tự rà soát", ICONS.security]
        ]
      },
      {
        label: "Tạo mới",
        links: [
          ["/features", "Tất cả studio", ICONS.prompt], ["/chat", "Content & Chat", ICONS.chat], ["/image/create", "Image", ICONS.image], ["/video/create", "Video", ICONS.video], ["/voice/tts", "Voice & Music", ICONS.voice], ["/subtitle", "Ngôn ngữ & Docs", ICONS.subtitle]
        ]
      },
      {
        label: "Công việc",
        links: [
          ["/jobs", "Job Center", ICONS.jobs], ["/assets", "Tài sản Bot", ICONS.assets]
        ]
      },
      {
        label: "Ví & gói",
        links: [
          ["/wallet", "Ví Xu", ICONS.wallet], ["/wallet/topup", "Nạp Xu", ICONS.payments], ["/membership", "Membership", ICONS.pricing], ["/packages", "Gói dịch vụ", ICONS.pricing], ["/pricing", "Bảng giá", ICONS.pricing]
        ]
      },
      {
        label: "Tài khoản & hỗ trợ",
        links: [
          ["/account", "Tài khoản", ICONS.account], ["/account/activity", "Hoạt động Web", ICONS.account], ["/tickets", "Ticket của tôi", ICONS.ticket], ["/support", "Hỗ trợ", ICONS.support], ["/status", "Trạng thái dịch vụ", ICONS.system]
        ]
      },
      {
        label: "Bot companion",
        links: [
          ["/referrals", "Giới thiệu", ICONS.support], ["/rewards", "Ưu đãi", ICONS.pricing], ["/community", "Cộng đồng", ICONS.support], ["/guides", "Hướng dẫn Bot", ICONS.legal]
        ]
      }
    ];
    const supportSummary = context.supportAdminSummary && typeof context.supportAdminSummary === "object" ? context.supportAdminSummary : {};
    const supportRole = String(supportSummary.operator_role || "").trim();
    const supportRouteActive = ["support-admin", "support-admin-case-detail"].includes(String(currentPage.layout || ""));
    // A Support Desk operator is not automatically a canonical ERP admin.
    // Give this narrowly scoped Web-native route a discoverable sidebar entry
    // without exposing the rest of the Bot-compatible admin navigation.
    if (context.isAdmin) {
      groups.push({
        label: "Admin ERP",
        links: [
          ["/admin", "Tất cả module", ICONS.admin], ["/admin/users", "Người dùng", ICONS.users], ["/admin/jobs", "Jobs", ICONS.jobs],
          ["/admin/payments", "Thanh toán", ICONS.payments], ["/admin/providers", "Providers", ICONS.providers], ["/admin/audit", "Audit", ICONS.security], ["/admin/support", "Web Support Desk", ICONS.support]
        ]
      });
    } else if (supportRouteActive || ["operator", "manager"].includes(supportRole)) {
      groups.push({ label: "Support Desk", links: [["/admin/support", "Web Support Desk", ICONS.support]] });
    }
    return groups;
  }

  function matchesRouteFamily(path, root) {
    return path === root || path.indexOf(`${root}/`) === 0;
  }

  function isNavCurrent(linkPath, page) {
    const path = normalizePath(page.routePath || page.path);
    if (linkPath === "/dashboard") return path === "/dashboard";
    if (linkPath === "/features") return matchesRouteFamily(path, "/features");
    if (linkPath === "/tools") return path === "/tools";
    if (linkPath === "/studio") return path === "/studio";
    if (linkPath === "/chat") return path === "/chat" || path === "/tools/chat";
    if (linkPath === "/prompt-studio") return path === "/prompt-studio" || path === "/prompts" || matchesRouteFamily(path, "/content");
    if (linkPath === "/prompt-library") return matchesRouteFamily(path, "/prompt-library");
    if (linkPath === "/media-workspace") return matchesRouteFamily(path, "/media-workspace");
    if (linkPath === "/content-studio") return matchesRouteFamily(path, "/content-studio");
    if (linkPath === "/image-studio") return matchesRouteFamily(path, "/image-studio");
    if (linkPath === "/document-workspace") return matchesRouteFamily(path, "/document-workspace");
    if (linkPath === "/video-studio") return matchesRouteFamily(path, "/video-studio");
    if (linkPath === "/subtitle-studio") return matchesRouteFamily(path, "/subtitle-studio");
    if (linkPath === "/voice-studio") return matchesRouteFamily(path, "/voice-studio");
    if (linkPath === "/image/create") return path === "/image" || matchesRouteFamily(path, "/image");
    // Keep the legacy video entry exact: `/video-studio` is a native Web
    // workspace and must never inherit this historical route's navigation.
    if (linkPath === "/video/create") return path === "/video" || path.startsWith("/video/");
    if (linkPath === "/voice/tts") return path === "/tts" || matchesRouteFamily(path, "/voice");
    if (linkPath === "/music") return matchesRouteFamily(path, "/music");
    if (linkPath === "/subtitle") return matchesRouteFamily(path, "/subtitle") || ["/translate", "/dubbing", "/asr"].includes(path);
    if (linkPath === "/documents") return matchesRouteFamily(path, "/documents");
    if (linkPath === "/wallet") return path === "/wallet";
    if (linkPath === "/wallet/topup") return matchesRouteFamily(path, "/wallet/topup");
    if (linkPath === "/membership") return path === "/membership";
    if (linkPath === "/account") return path === "/account" || path === "/account/activity" || path === "/onboarding";
    if (linkPath === "/admin/users") return matchesRouteFamily(path, "/admin/users");
    if (linkPath === "/admin/jobs") return matchesRouteFamily(path, "/admin/jobs");
    if (linkPath === "/admin/payments") return matchesRouteFamily(path, "/admin/payments");
    if (linkPath === "/admin/providers") return matchesRouteFamily(path, "/admin/providers") || path === "/admin/provider-cost";
    if (linkPath === "/admin/audit") return matchesRouteFamily(path, "/admin/audit") || ["/admin/security", "/admin/access"].includes(path);
    if (linkPath === "/admin") {
      const directAdminFamilies = ["/admin/users", "/admin/jobs", "/admin/payments", "/admin/providers", "/admin/provider-cost", "/admin/audit", "/admin/security", "/admin/access"];
      return path === "/admin" || (matchesRouteFamily(path, "/admin") && !directAdminFamilies.some((root) => matchesRouteFamily(path, root)));
    }
    return matchesRouteFamily(path, linkPath);
  }

  // The compact dock intentionally links only to stable, signed workspace
  // routes. It does not show balance, job counts, provider readiness or any
  // other private state, so it remains a navigation aid rather than a second
  // dashboard with stale or browser-owned data.
  function isMobileNavCurrent(key, page) {
    const path = normalizePath(page.routePath || page.path);
    if (key === "dashboard") {
      return ["/dashboard", "/projects", "/prompt-library", "/content-studio", "/document-workspace", "/video-studio", "/subtitle-studio", "/voice-studio", "/media-workspace", "/campaigns", "/calendar", "/approvals"].includes(path) || path.startsWith("/projects/") || path.startsWith("/prompt-library/") || path.startsWith("/content-studio/") || path.startsWith("/document-workspace/") || path.startsWith("/video-studio/") || path.startsWith("/subtitle-studio/") || path.startsWith("/voice-studio/") || path.startsWith("/media-workspace/");
    }
    if (key === "studio") {
      return isNavCurrent("/features", page) || isNavCurrent("/tools", page) || isNavCurrent("/studio", page)
        || isNavCurrent("/chat", page) || isNavCurrent("/prompt-studio", page) || isNavCurrent("/image/create", page)
        || isNavCurrent("/video/create", page) || isNavCurrent("/voice/tts", page) || isNavCurrent("/music", page)
        || isNavCurrent("/subtitle", page) || isNavCurrent("/documents", page);
    }
    if (key === "jobs") return matchesRouteFamily(path, "/jobs");
    if (key === "assets") return matchesRouteFamily(path, "/assets");
    if (key === "account") {
      return isNavCurrent("/account", page) || ["/account/activity", "/wallet", "/wallet/topup", "/membership", "/packages", "/pricing", "/tickets", "/support", "/notes", "/reminders", "/rewards", "/guides", "/status"].some((route) => matchesRouteFamily(path, route));
    }
    return false;
  }

  function renderMobileNav(page) {
    const items = [
      ["dashboard", "/dashboard", "Tổng quan", ICONS.dashboard],
      ["studio", "/features", "AI Studio", ICONS.prompt],
      ["jobs", "/jobs", "Jobs", ICONS.jobs],
      ["assets", "/assets", "Tài sản", ICONS.assets],
      ["account", "/account", "Tài khoản", ICONS.account]
    ];
    return items.map(([key, href, label, icon]) => {
      const current = isMobileNavCurrent(key, page);
      return `<a class="portal-mobile-nav-link" href="${href}"${current ? ' aria-current="page"' : ""}>
        <span class="portal-mobile-nav-icon" aria-hidden="true">${safeText(icon)}</span>
        <span class="portal-mobile-nav-label">${safeText(label)}</span>
      </a>`;
    }).join("");
  }

  function normalizeCommandSearch(value) {
    const raw = String(value === undefined || value === null ? "" : value).trim().toLowerCase();
    return typeof raw.normalize === "function"
      ? raw.normalize("NFD").replace(/[\u0300-\u036f]/g, "")
      : raw;
  }

  function commandPaletteItems(context, page) {
    const activePath = normalizePath(page && (page.routePath || page.path));
    const items = [];
    const seen = new Set();
    Object.values(manifest).forEach((candidate) => {
      const path = candidate && typeof candidate.path === "string" ? candidate.path : "";
      if (!path || seen.has(path) || candidate.access === "public") return;
      const supportSummary = context && context.supportAdminSummary && typeof context.supportAdminSummary === "object" ? context.supportAdminSummary : {};
      const supportRole = String(supportSummary.operator_role || "").trim();
      const supportRoute = path === "/admin/support";
      const supportActive = page && ["support-admin", "support-admin-case-detail"].includes(String(page.layout || ""));
      if (candidate.access === "admin" && !(context && context.isAdmin === true) && !(supportRoute && (supportActive || ["operator", "manager"].includes(supportRole)))) return;
      seen.add(path);
      items.push({
        path,
        title: String(candidate.title || "TOAN AAS"),
        section: String(candidate.section || "Workspace"),
        icon: candidate.icon || ICONS.default,
        current: normalizePath(path) === activePath
      });
    });
    return items.sort((left, right) => {
      if (left.current !== right.current) return left.current ? -1 : 1;
      return `${left.section} ${left.title}`.localeCompare(`${right.section} ${right.title}`, "vi");
    });
  }

  function renderCommandPalette(page, context) {
    const items = commandPaletteItems(context, page);
    const markup = items.map((item) => {
      const search = normalizeCommandSearch(`${item.title} ${item.section} ${item.path}`);
      return `<a class="portal-command-item" href="${safeText(item.path)}" data-portal-command-item data-command-search="${safeText(search)}"${item.current ? ' aria-current="page"' : ""}>
        <span class="portal-command-item-icon" aria-hidden="true">${safeText(item.icon)}</span>
        <span class="portal-command-item-copy"><strong>${safeText(item.title)}</strong><small>${safeText(item.section)} · ${safeText(item.path)}</small></span>
        <span class="portal-command-item-arrow" aria-hidden="true">→</span>
      </a>`;
    }).join("");
    return `<div class="portal-command-palette-backdrop" data-portal-command-close></div>
      <section class="portal-command-dialog" role="dialog" aria-modal="true" aria-labelledby="portal-command-title">
        <header class="portal-command-header"><div><span class="portal-command-kicker">TOAN AAS workspace</span><h2 id="portal-command-title">Chuyển nhanh</h2></div><button class="portal-command-close" type="button" aria-label="Đóng chuyển nhanh" data-portal-command-close>×</button></header>
        <label class="portal-command-search"><span class="portal-sr-only">Tìm workspace</span><span aria-hidden="true">⌕</span><input type="search" placeholder="Tìm công cụ, jobs, tài sản, tài khoản…" autocomplete="off" data-portal-command-search></label>
        <p class="portal-command-hint"><span><kbd>Ctrl</kbd> <kbd>K</kbd> để mở</span><span><kbd>Esc</kbd> để đóng</span></p>
        <div class="portal-command-results" aria-label="Kết quả chuyển nhanh" data-portal-command-results>${markup}</div>
        <p class="portal-command-empty" data-portal-command-empty hidden>Không tìm thấy workspace phù hợp. Hãy thử tên tính năng hoặc đường dẫn khác.</p>
        <p class="portal-command-count" aria-live="polite" data-portal-command-count>${safeText(String(items.length))} workspace có thể mở trong phiên này.</p>
      </section>`;
  }

  function renderSidebar(page, context) {
    const bridgeReady = context.bridge.available === true;
    const groups = navGroups(context, page).map((group) => {
      const links = group.links.map(([path, label, linkIcon]) => {
        const current = isNavCurrent(path, page);
        return `<a class="portal-nav-link" href="${path}"${current ? ' aria-current="page"' : ""}>
          <span class="portal-nav-icon" aria-hidden="true">${safeText(linkIcon)}</span>
          <span>${safeText(label)}</span>
        </a>`;
      }).join("");
      return `<section class="portal-nav-group"><span class="portal-nav-label">${safeText(group.label)}</span>${links}</section>`;
    }).join("");
    return `<div class="portal-brand">
      <span class="portal-brand-mark" aria-hidden="true">TA</span>
      <span class="portal-brand-copy"><span class="portal-brand-name">TOAN AAS</span><span class="portal-brand-caption">AI Workspace</span></span>
      <button class="portal-sidebar-close" type="button" aria-label="Đóng điều hướng" data-portal-close-menu>×</button>
    </div>
    <a class="portal-sidebar-create" href="/features"><span aria-hidden="true">+</span><span>Tạo workflow mới</span><b aria-hidden="true">→</b></a>
    <nav class="portal-nav">${groups}</nav>
    <div class="portal-sidebar-foot">
      <div class="portal-bridge-mini"><span class="portal-bridge-dot${bridgeReady ? " is-ready" : ""}" aria-hidden="true"></span>
        <span><strong>${bridgeReady ? "Kết nối workspace sẵn sàng" : "Workspace đang ở chế độ an toàn"}</strong><span>${bridgeReady ? "Tính năng được cấp theo phiên hiện tại" : "Không gọi provider, Xu hoặc payment từ browser"}</span></span>
      </div>
      <a class="portal-nav-link" href="/legal"><span class="portal-nav-icon" aria-hidden="true">${ICONS.legal}</span><span>Pháp lý & riêng tư</span></a>
    </div>`;
  }

  function renderHeader(page, context) {
    const name = displayName(context);
    const crumbs = ["TOAN AAS", page.section, page.title].filter(Boolean).map((piece) => `<span>${safeText(piece)}</span>`).join("");
    const accountHref = context.session.authenticated === true ? "/account" : "/login";
    return `<button class="portal-menu-button" type="button" aria-label="Mở điều hướng" aria-controls="portal-sidebar" aria-expanded="false" data-portal-menu>☰</button>
      <div class="portal-crumbs" aria-label="Vị trí hiện tại">${crumbs}</div>
      <div class="portal-header-actions">
        <button class="portal-command-trigger" type="button" aria-label="Mở chuyển nhanh" aria-haspopup="dialog" aria-controls="portal-command-palette" data-portal-open-command-palette><span aria-hidden="true">⌕</span><span class="portal-command-trigger-label">Chuyển nhanh</span><kbd>Ctrl K</kbd></button>
        ${badge(stateFor(page, context))}
        <a class="portal-session-chip" href="${accountHref}" aria-label="Mở tài khoản">
          <span class="portal-session-avatar" aria-hidden="true">${initials(name)}</span><span class="portal-session-copy">${safeText(name)}</span>
        </a>
      </div>`;
  }

  function renderFields(fields, enabled, context, fieldValues) {
    if (!fields || !fields.length) return "";
    const values = fieldValues && typeof fieldValues === "object" ? fieldValues : {};
    return `<div class="portal-fields">${fields.map((field) => {
      const wide = field.control === "textarea" || field.type === "file" || field.wide;
      const id = `portal-field-${safeText(field.name || "input").replace(/[^a-zA-Z0-9_-]/g, "-")}`;
      const disabled = enabled && field.disabled !== true ? "" : " disabled";
      const rawValue = Object.prototype.hasOwnProperty.call(values, field.name) ? values[field.name] : "";
      const value = rawValue === undefined || rawValue === null ? "" : String(rawValue);
      const stagedUploadCount = field.type === "file" && Array.isArray(values.upload_ids) ? values.upload_ids.filter((item) => typeof item === "string" && item).length : 0;
      const descriptionIds = [];
      const help = field.help ? (descriptionIds.push(`${id}-help`), `<span id="${id}-help" class="portal-field-help">${safeText(field.help)}</span>`) : "";
      const staged = stagedUploadCount ? (descriptionIds.push(`${id}-staged`), `<span id="${id}-staged" class="portal-field-staged">${safeText(String(stagedUploadCount))} tệp đã vào staging canonical; không cần chọn lại để estimate/confirm.</span>`) : "";
      const describedBy = descriptionIds.length ? ` aria-describedby="${descriptionIds.join(" ")}"` : "";
      const required = field.required === true && field.type !== "file" ? " required" : "";
      const hasRequiredIndicator = field.required === true || field.requiredUpload === true || field.dynamicRequired === true;
      const ariaRequired = hasRequiredIndicator ? ` aria-required="${field.required === true || field.requiredUpload === true ? "true" : "false"}"` : "";
      const min = field.min !== undefined ? ` min="${safeText(String(field.min))}"` : "";
      const max = field.max !== undefined ? ` max="${safeText(String(field.max))}"` : "";
      const step = field.step !== undefined ? ` step="${safeText(String(field.step))}"` : "";
      const minLength = field.minLength !== undefined ? ` minlength="${safeText(String(field.minLength))}"` : "";
      const maxLength = field.maxLength !== undefined ? ` maxlength="${safeText(String(field.maxLength))}"` : "";
      const pattern = field.pattern ? ` pattern="${safeText(field.pattern)}"` : "";
      const inputMode = field.inputMode ? ` inputmode="${safeText(field.inputMode)}"` : "";
      let control;
      if (field.control === "textarea") {
        control = `<textarea class="portal-textarea" id="${id}" name="${safeText(field.name)}" placeholder="${safeText(field.placeholder)}"${required}${ariaRequired}${minLength}${maxLength}${describedBy}${disabled}>${safeText(value)}</textarea>`;
      } else if (field.control === "select") {
        let options = Array.isArray(field.options) ? field.options : [];
        if (field.optionsFrom === "voiceProfiles") {
          const profiles = context && Array.isArray(context.voiceProfiles) ? context.voiceProfiles : [];
          options = profiles
            .filter((profile) => profile && profile.id && profile.tts_ready)
            .map((profile) => ({ value: String(profile.id), label: `${profile.display_name || "Giọng chưa đặt tên"}${profile.is_default ? " · Mặc định" : ""}` }));
        }
        if (field.optionsFrom === "imageTiers" || field.optionsFrom === "videoTiers") {
          const key = field.optionsFrom === "imageTiers" ? "image_tiers" : "video_tiers";
          const tiers = context && context.pricingCatalog && Array.isArray(context.pricingCatalog[key]) ? context.pricingCatalog[key] : [];
          options = tiers
            .filter((tier) => tier && tier.code)
            .map((tier) => ({
              value: String(tier.code),
              label: `${tier.label || tier.code}${Number.isFinite(Number(tier.cost_xu)) ? ` · ${tier.cost_xu} Xu` : ""}`
            }));
        }
        if (field.optionsFrom === "packages") {
          const catalog = context && context.packageCatalog && typeof context.packageCatalog === "object" ? context.packageCatalog : {};
          options = [...(Array.isArray(catalog.monthly) ? catalog.monthly : []), ...(Array.isArray(catalog.combos) ? catalog.combos : [])]
            .filter((item) => item && item.code && item.manual !== true)
            .map((item) => {
              const price = Number(item.price_vnd);
              const priceLabel = Number.isFinite(price) && price > 0 ? ` · ${price.toLocaleString("vi-VN")}đ` : " · Chờ giá canonical";
              return { value: String(item.code), label: `${item.label || item.code}${priceLabel}` };
            });
        }
        if (field.optionsFrom === "projects") {
          const projects = context && Array.isArray(context.projects) ? context.projects : [];
          options = projects
            .filter((project) => project && validProjectId(project.id) && String(project.state || "active") === "active")
            .map((project) => ({ value: String(project.id), label: String(project.title || "Project Web") }));
        }
        if (field.optionsFrom === "memoryNotes") {
          const notes = context && Array.isArray(context.memoryNotes) ? context.memoryNotes : [];
          options = notes
            .filter((note) => note && validMemoryId(note.id) && String(note.state || "active") === "active")
            .map((note) => ({ value: String(note.id), label: String(note.title || "Ghi chú Web") }));
        }
        if (field.optionsFrom === "pdfVaultAssets") {
          const assets = context && Array.isArray(context.vaultItems) ? context.vaultItems : [];
          options = assets
            .filter((asset) => asset && validProjectId(asset.id) && String(asset.state || "") === "active"
              && String(asset.extension || "").toLowerCase() === ".pdf" && String(asset.content_type || "") === "application/pdf")
            .map((asset) => ({
              value: String(asset.id),
              label: `${asset.display_name || asset.original_filename || "PDF riêng tư"} · ${vaultBytes(asset.byte_size)}`
            }));
        }
        if (field.optionsFrom === "imageVaultAssets") {
          options = imageVaultItems(context).map((asset) => ({
            value: String(asset.id),
            label: `${asset.display_name || asset.original_filename || "Ảnh riêng tư"} · ${String(asset.extension || "").replace(".", "").toUpperCase()} · ${vaultBytes(asset.byte_size)}`
          }));
        }
        if (field.optionsFrom === "topupPackages") {
          const payos = context && context.paymentOptions && context.paymentOptions.payos && typeof context.paymentOptions.payos === "object" ? context.paymentOptions.payos : {};
          options = Array.isArray(payos.topup_packages) ? payos.topup_packages
            .filter((item) => item && item.code && item.available !== false)
            .map((item) => {
              const price = Number(item.amount_vnd);
              const priceLabel = Number.isFinite(price) && price > 0 ? ` · ${price.toLocaleString("vi-VN")}đ` : "";
              const xu = Number(item.xu);
              const xuLabel = Number.isFinite(xu) && xu >= 0 ? ` · ${xu.toLocaleString("vi-VN")} Xu` : "";
              return { value: String(item.code), label: `${item.label || item.code}${priceLabel}${xuLabel}` };
            }) : [];
        }
        const empty = field.emptyLabel ? `<option value=""${value === "" ? " selected" : ""}>${safeText(field.emptyLabel)}</option>` : "";
        const optionMarkup = options.map((option) => {
          // Most catalog options are objects, while compact fixed options
          // deliberately use [value, label] tuples. Support both shapes so a
          // select never renders an accidental `undefined` option.
          const value = Array.isArray(option) ? option[0] : (option && typeof option === "object" ? option.value : option);
          const label = Array.isArray(option) ? option[1] : (option && typeof option === "object" ? option.label : option);
          const selected = String(value) === String(rawValue) ? " selected" : "";
          return `<option value="${safeText(value)}"${selected}>${safeText(label)}</option>`;
        }).join("");
        control = `<select class="portal-select" id="${id}" name="${safeText(field.name)}"${required}${ariaRequired}${describedBy}${disabled}>${empty}${optionMarkup}</select>`;
      } else if (field.type === "checkbox") {
        const checked = rawValue === true || rawValue === "true" || rawValue === 1 || rawValue === "1" ? " checked" : "";
        control = `<label class="portal-checkbox" for="${id}"><input id="${id}" name="${safeText(field.name)}" type="checkbox" value="true"${checked}${required}${ariaRequired}${describedBy}${disabled}><span>Tôi xác nhận</span></label>`;
      } else {
        const type = ["email", "password", "file", "number", "text", "datetime-local"].includes(field.type) ? field.type : "text";
        const autocomplete = field.autocomplete ? ` autocomplete="${safeText(field.autocomplete)}"` : "";
        const multiple = type === "file" && field.multiple ? " multiple" : "";
        const accept = type === "file" && field.accept ? ` accept="${safeText(field.accept)}"` : "";
        const valueAttribute = type === "file" || type === "password" ? "" : ` value="${safeText(value)}"`;
        control = `<input class="portal-input" id="${id}" name="${safeText(field.name)}" type="${type}" placeholder="${safeText(field.placeholder)}"${valueAttribute}${autocomplete}${multiple}${accept}${required}${ariaRequired}${min}${max}${step}${minLength}${maxLength}${pattern}${inputMode}${describedBy}${disabled}>`;
      }
      const requiredMark = hasRequiredIndicator
        ? `<span class="portal-required-mark" data-portal-required-mark aria-hidden="true"${field.required === true || field.requiredUpload === true ? "" : " hidden"}>*</span><span class="portal-sr-only" data-portal-required-message${field.required === true || field.requiredUpload === true ? "" : " hidden"}> bắt buộc</span>`
        : "";
      return `<div class="portal-field${wide ? " portal-field--wide" : ""}"><label for="${id}">${safeText(field.label)}${requiredMark}</label>${control}${help}${staged}</div>`;
    }).join("")}</div>`;
  }

  function statusMessage(page, status, context) {
    const webSupportDesk = ["support-desk", "support-cases", "support-case-detail", "support-admin", "support-admin-case-detail"].includes(page.layout);
    if (webSupportDesk && status !== "guarded" && status !== "error" && status !== "failed") {
      return { icon: "✓", title: "Web Support Desk độc lập", text: "Case, timeline và quyền truy cập do Web App kiểm tra; không tạo ticket Bot, delivery Telegram/email, payment hoặc provider call." };
    }
    if (status === "ready") return { icon: "✓", title: "Giao diện đã sẵn sàng", text: "Chỉ các khả năng đã được máy chủ ký và cấp cho phiên mới được bật." };
    if (status === "empty") return { icon: "○", title: "Chưa có dữ liệu để hiển thị", text: "Portal không tự tạo job, số dư, file hay output. Dữ liệu chỉ xuất hiện sau phản hồi từ Engine Web hoặc integration đã được cấp quyền." };
    if (status === "error" || status === "failed") return { icon: "!", title: "Chưa thể xác thực trạng thái", text: "Không có thao tác fallback hay giả lập. Hãy đợi Engine Web hoặc integration trả trạng thái an toàn." };
    if (status === "queued" || status === "processing") return { icon: "◌", title: "Job đang được điều phối", text: "Chỉ engine đã được xác minh mới có thể chuyển job sang completed." };
    if (status === "draft" || status === "awaiting_confirm") return { icon: "◇", title: "Bản nháp chờ luồng xác nhận", text: "Authoring Web đã lưu brief; engine phải estimate trước khi người dùng xác nhận tạo job." };
    if (status === "completed") return { icon: "✓", title: "Output đã hoàn tất", text: "Output cần được backend xác thực file, ownership và URL ký tạm thời trước khi mở tải xuống." };
    if (status === "failed_no_charge") return { icon: "!", title: "Job thất bại · chưa trừ Xu", text: "Bot canonical xác nhận không có charge; Admin có thể retry sau khi Bot kiểm tra lại điều kiện." };
    if (status === "cancelled") return { icon: "—", title: "Yêu cầu đã hủy", text: "Browser chỉ hiển thị trạng thái canonical; không suy đoán charge, refund hoặc delivery." };
    if (status === "refunded") return { icon: "↺", title: "Hoàn Xu đã được ghi nhận", text: "Ledger canonical của bot quyết định số tiền hoàn và trạng thái cuối cùng." };
    if (status === "read_only") return { icon: "i", title: "Dữ liệu canonical chỉ đọc", text: "Portal đang hiển thị dữ liệu bot đã được role-check; mọi thay đổi vẫn cần adapter, confirmation, CSRF và audit riêng." };
    if (status === "disabled") return { icon: "—", title: "Tính năng đang tạm khóa", text: "Trạng thái maintenance/freeze phải được bridge quản lý; browser không thể tự bật lại." };
    const isAdmin = page.access === "admin" && !context.isAdmin;
    const webWorkspaceReady = ["dashboard", "project-center", "project-detail", "project-packages", "campaign-planner", "campaign-detail", "workspace-drafts", "asset-vault", "memory-notes", "memory-reminders", "prompt-library", "prompt-library-detail", "content-studio", "content-studio-detail", "voice-studio", "voice-studio-detail", "media-workspace", "media-workspace-detail", "pdf-split", "pdf-merge", "pdf-optimize", "image-to-pdf", "pdf-to-word", "image-resize", "image-enhance"].includes(page.layout)
      && context.session && context.session.authenticated === true;
    if (webWorkspaceReady) return { icon: "✓", title: "Web Workspace độc lập đã sẵn sàng", text: "Project, Studio Document, bản nháp và planning Web-owned không cần Telegram hoặc Bot bridge. Các integration bên ngoài vẫn được cấp riêng theo capability." };
    const feature = page.type === "feature" ? featureKeyForPage(page, context) : "";
    const planningAvailable = Boolean(
      feature && page.action !== "none" && context.session && context.session.authenticated === true
      && context.session.csrfReady === true && context.capabilities
      && context.capabilities["workspace-draft-save"] === true
      && Array.isArray(context.workspaceDraftFeatures) && context.workspaceDraftFeatures.includes(feature)
    );
    if (planningAvailable) return { icon: "◇", title: "Web Studio đã sẵn sàng; engine vẫn được bảo vệ", text: "Bạn có thể soạn và lưu brief Web ngay. Estimate, charge, job và output chỉ bật sau khi Engine Web hoặc integration đã được cấp capability riêng." };
    return { icon: "⌁", title: isAdmin ? "Khu vực quản trị cần quyền máy chủ" : "Engine Web chưa được bật", text: isAdmin ? "Server cần xác nhận signed admin session trước khi hiển thị dữ liệu hoặc thao tác ERP." : "Shell chỉ cho phép authoring đã được cấp quyền. Provider, wallet, PayOS và job không được gọi trực tiếp tại đây." };
  }

  function renderStatusCard(page, context) {
    const status = stateFor(page, context);
    const message = statusMessage(page, status, context);
    const bridgeText = context.bridge.available === true ? "Bot integration đã khai báo" : "Bot integration là tùy chọn";
    const sessionText = context.session.authenticated === true ? "Signed session hiện diện" : "Chưa có signed session";
    return `<section class="portal-card portal-card-pad"><div class="portal-state" data-state="${safeText(status)}">
      <span class="portal-state-icon" aria-hidden="true">${message.icon}</span><div><h2>${safeText(message.title)}</h2><p>${safeText(message.text)}</p>
      <div class="portal-state-meta"><span>${safeText(bridgeText)}</span><span>${safeText(sessionText)}</span><span>Không có provider/payment call</span></div></div>
    </div></section>`;
  }

  function renderSummary(page, context) {
    const status = stateFor(page, context);
    const api = context.apiBase ? "Đã cấu hình phía server" : "Chưa công bố";
    return `<aside class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Bảo đảm luồng</h2><p class="portal-card-subtitle">Trạng thái không được suy đoán ở client.</p></div>${badge(status)}</div>
      <div class="portal-summary-list">
        <div class="portal-summary-item"><span class="portal-summary-key">Web Workspace</span><span class="portal-summary-value">${context.session.authenticated === true ? "Độc lập" : "Cần đăng nhập"}</span></div>
        <div class="portal-summary-item"><span class="portal-summary-key">Bot companion</span><span class="portal-summary-value">${context.bridge.available === true ? "Đã kết nối" : "Tùy chọn"}</span></div>
        <div class="portal-summary-item"><span class="portal-summary-key">Signed session</span><span class="portal-summary-value">${context.session.authenticated === true ? "Được xác minh" : "Đang chờ"}</span></div>
        <div class="portal-summary-item"><span class="portal-summary-key">CSRF</span><span class="portal-summary-value">${context.session.csrfReady === true || context.bridge.csrfReady === true ? "Sẵn sàng" : "Chưa cấp"}</span></div>
        <div class="portal-summary-item"><span class="portal-summary-key">API base</span><span class="portal-summary-value">${safeText(api)}</span></div>
      </div></aside>`;
  }

  function renderNotes(page) {
    const notes = page.notes && page.notes.length ? page.notes : ["Trạng thái bên ngoài chỉ được dùng sau khi backend kiểm tra quyền sở hữu và capability."];
    return `<div class="portal-panel-list">${notes.map((note, index) => `<div class="portal-panel-row"><span class="portal-panel-row-icon" aria-hidden="true">${index ? "✓" : "i"}</span><div><strong>${index ? "Nguyên tắc an toàn" : "Trạng thái tích hợp"}</strong><span>${safeText(note)}</span></div></div>`).join("")}</div>`;
  }

  function flowHasFreshEstimate(flow) {
    const estimate = flow && flow.data && typeof flow.data === "object" ? flow.data.estimate : null;
    return Boolean(
      flow && flow.phase === "estimate" && flow.status === "awaiting_confirm" &&
      estimate && estimate.available === true && estimate.tier_required !== true && estimate.scene_count_required !== true && typeof flow.estimateFingerprint === "string" && flow.estimateFingerprint &&
      typeof flow.webQuoteReceipt === "string" && /^[A-Za-z0-9_-]{32,160}$/.test(flow.webQuoteReceipt)
    );
  }

  function transientFormValues(route) {
    const values = transientFormDrafts.get(route);
    return values && typeof values === "object" ? values : {};
  }

  function featureKeyForPage(page, context) {
    const routes = [page && page.path, page && page.routePath]
      .filter((value) => typeof value === "string" && value)
      .map((value) => normalizePath(value));
    const catalog = Array.isArray(context.catalog) ? context.catalog : [];
    for (const route of routes) {
      const item = catalog.find((candidate) => candidate && typeof candidate.key === "string" && normalizePath(candidate.route || "") === route);
      if (item) return item.key;
    }
    for (const route of routes) {
      if (FEATURE_PAGE_KEY_ALIASES[route]) return FEATURE_PAGE_KEY_ALIASES[route];
    }
    return "";
  }

  function featureConfirmExecutionReady(page, context) {
    const feature = featureKeyForPage(page, context);
    const allowed = context.bridge && Array.isArray(context.bridge.featureExecutionFeatures)
      ? context.bridge.featureExecutionFeatures : [];
    return Boolean(
      feature
      && allowed.includes(feature)
      && context.capabilities
      && context.capabilities["feature-confirm"] === true
      && context.bridge
      && context.bridge.featureExecutionAvailable === true
    );
  }

  function renderFormCard(page, context) {
    const enabled = canAct(page, context);
    const reason = actionBlockReason(page, context);
    const hasFields = page.fields && page.fields.length;
    if (!hasFields) {
      return `<section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Chờ dữ liệu Core Bridge</h2><p class="portal-card-subtitle">Không có form hay action có thể làm thay đổi trạng thái tại trang này.</p></div>${badge(stateFor(page, context))}</div>${renderNotes(page)}</section>`;
    }
    const route = page.routePath || page.path;
    const flow = context.featureFlows && context.featureFlows[route];
    const flowStatus = flow && ALLOWED_STATES.has(flow.status) ? flow.status : "";
    const hasFreshEstimate = flowHasFreshEstimate(flow);
    const quoteNeedsSelection = Boolean(flow && flow.phase === "estimate" && flow.status === "awaiting_confirm" && !hasFreshEstimate);
    const canEstimate = enabled && page.type === "feature" && !hasFreshEstimate && (
      page.action === "feature-estimate" || page.estimateDirect === true || flowStatus === "draft" || quoteNeedsSelection
    );
    const formId = `portal-form-${safeText(route).replace(/[^a-zA-Z0-9_-]/g, "-")}`;
    const feature = featureKeyForPage(page, context);
    const workspaceDraftSupported = Array.isArray(context.workspaceDraftFeatures) && context.workspaceDraftFeatures.includes(feature);
    const workspaceDraftId = workspaceDraftIdForRoute(route);
    // A signed Web account may compose and save a local brief before the
    // Telegram/Core Bridge execution gates are available. This does not
    // unlock feature submit, upload, estimate, quote, job or payment.
    const workspaceDraftEnabled = Boolean(
      page.type === "feature" && feature && workspaceDraftSupported && context.session && context.session.authenticated === true &&
      context.session.csrfReady === true && context.capabilities && context.capabilities["workspace-draft-save"] === true
    );
    const formFieldsEnabled = enabled || workspaceDraftEnabled;
    // When an external engine is not enabled, the primary form action is a
    // real, owner-scoped Web draft—not a disabled Bot action. This also makes
    // Enter submit the same safe action as the visible primary button.
    const localAuthoringOnly = !enabled && workspaceDraftEnabled;
    const localDraftAction = workspaceDraftId ? "workspace-draft-update" : "workspace-draft-save";
    const localDraftLabel = workspaceDraftId ? "Cập nhật bản nháp Web" : "Lưu bản nháp Web";
    const formAction = localAuthoringOnly ? localDraftAction : page.action;
    const workspaceDraftControl = workspaceDraftEnabled && !localAuthoringOnly
      ? (workspaceDraftId
        ? `<button class="portal-button portal-button--quiet" type="button" data-portal-action="workspace-draft-update" data-portal-route="${safeText(route)}" data-portal-form-id="${safeText(formId)}" data-workspace-draft-id="${safeText(workspaceDraftId)}">Cập nhật bản nháp Web</button><button class="portal-button portal-button--quiet" type="button" data-portal-action="workspace-draft-save" data-portal-route="${safeText(route)}" data-portal-form-id="${safeText(formId)}">Lưu thành bản mới</button>`
        : `<button class="portal-button portal-button--quiet" type="button" data-portal-action="workspace-draft-save" data-portal-route="${safeText(route)}" data-portal-form-id="${safeText(formId)}">Lưu bản nháp Web</button>`)
      : "";
    const estimateControl = canEstimate && page.action !== "feature-estimate"
      ? `<button class="portal-button portal-button--quiet" type="button" data-portal-action="feature-estimate" data-portal-route="${safeText(route)}" data-portal-form-id="${safeText(formId)}">Ước tính Xu</button>`
      : "";
    const executionReady = featureConfirmExecutionReady(page, context);
    const confirmControl = hasFreshEstimate
      ? (executionReady
        ? `<button class="portal-button portal-button--primary" type="button" data-portal-action="feature-confirm" data-portal-route="${safeText(route)}" data-portal-form-id="${safeText(formId)}" data-portal-confirm="Xác nhận gửi yêu cầu cho Core Bridge? Xu, job và trạng thái chỉ do bot canonical quyết định.">Xác nhận chạy</button>`
        : `<span class="portal-flow-note" role="status">Đã có estimate canonical. Web App đang chờ adapter tạo job canonical; chưa thể xác nhận chạy hoặc trừ Xu.</span>`)
      : "";
    const flowControls = estimateControl || confirmControl ? `<div class="portal-flow-actions">${estimateControl}${confirmControl}</div>` : "";
    const fieldValues = { ...(flow && flow.input && typeof flow.input === "object" ? flow.input : {}), ...transientFormValues(route) };
    const primaryActionLabel = localAuthoringOnly ? localDraftLabel : (page.actionLabel || "Tiếp tục");
    const primaryDisabled = localAuthoringOnly || enabled ? "" : ` disabled title="${safeText(reason)}"`;
    return `<section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">${page.layout === "auth" ? "Thông tin xác thực" : "Chuẩn bị yêu cầu"}</h2><p class="portal-card-subtitle">${enabled ? "Yêu cầu sẽ được chuyển tới lớp tích hợp thông qua custom event, không gọi trực tiếp từ UI." : (workspaceDraftEnabled ? "Bạn có thể soạn và lưu brief Web; estimate, job và integration ngoài chỉ bật theo capability riêng." : safeText(reason))}</p></div>${badge(flowStatus || stateFor(page, context))}</div>
      <form class="portal-form" id="${safeText(formId)}" data-portal-form data-portal-action="${safeText(formAction)}" data-portal-route="${safeText(route)}"${workspaceDraftId ? ` data-workspace-draft-id="${safeText(workspaceDraftId)}"` : ""} novalidate>${renderFields(page.fields, formFieldsEnabled, context, fieldValues)}
        <div class="portal-form-footer"><span class="portal-form-note">${enabled ? "Máy chủ vẫn phải xác minh phiên, CSRF, schema, ownership và idempotency." : (workspaceDraftEnabled ? "Bản nháp chỉ giữ brief scalar trên Web; không lưu file, upload ID, quote, job, Xu hoặc provider." : "Các trường bị khóa cho tới khi máy chủ cấp khả năng cần thiết.")}</span>
          ${workspaceDraftControl}<button class="portal-button portal-button--primary" type="submit"${primaryDisabled}>${safeText(primaryActionLabel)}</button>
        </div>
      </form>${flowControls}</section>`;
  }

  function renderHero(page, context) {
    const state = stateFor(page, context);
    const route = page.routePath || page.path;
    const linkPending = page.action === "start-telegram-link" && context.linkFlow && context.linkFlow.data && context.linkFlow.data.code && !(context.linkStatus && context.linkStatus.linked === true);
    const hasAction = page.action && page.action !== "none" && !linkPending;
    // A feature/customer form must submit through its own validated form so
    // that field values, staged upload IDs and the current quote fingerprint
    // are collected. A duplicate hero button used to emit an empty action.
    const hasFields = Array.isArray(page.fields) && page.fields.length > 0;
    const showHeroAction = hasAction && !hasFields;
    const enabled = hasAction && canAct(page, context);
    const reason = actionBlockReason(page, context);
    return `<section class="portal-hero"><div class="portal-hero-copy"><div class="portal-eyebrow">${safeText(page.section || "TOAN AAS")}</div>
      <h1 class="portal-title">${safeText(displayPageTitle(page, context))}</h1><p class="portal-description">${safeText(page.description)}</p></div>
      <div class="portal-hero-actions">${badge(state)}${showHeroAction ? `<button class="portal-button portal-button--primary" type="button" data-portal-action="${safeText(page.action)}" data-portal-route="${safeText(route)}"${enabled ? "" : ` disabled title="${safeText(reason)}"`}>${safeText(page.actionLabel)}</button>` : ""}</div>
    </section>`;
  }

  const FEATURE_CATALOG_GROUPS = Object.freeze([
    { key: "account", title: "Bắt đầu & tài khoản", description: "Onboarding, session và hồ sơ đã được server kiểm soát." },
    { key: "wallet", title: "Ví, nạp & gói", description: "Xu, pricing và thanh toán chỉ đọc qua authority canonical." },
    { key: "jobs", title: "Job & tài sản", description: "Theo dõi work, delivery và metadata thuộc phiên sở hữu." },
    { key: "content", title: "Content & Chat", description: "Prompt, caption, script và planning nội dung." },
    { key: "image", title: "Image Studio", description: "Tạo, chỉnh sửa và xử lý ảnh theo workflow canonical." },
    { key: "video", title: "Video Studio", description: "Brief, cảnh, tiến độ, preview và export có kiểm soát." },
    { key: "voice", title: "Voice Studio", description: "TTS, Voice Vault, clone và preview riêng tư." },
    { key: "music", title: "Music & SFX", description: "Nhạc AI, bài hát, SFX và thư viện tài sản âm thanh." },
    { key: "subtitle", title: "Phụ đề & ngôn ngữ", description: "ASR, SRT/VTT, dịch và lồng tiếng." },
    { key: "documents", title: "Documents & PDF", description: "PDF, OCR, gộp, tách, nén và dịch tài liệu." },
    { key: "support", title: "Hỗ trợ & thông tin", description: "Ticket, bảng giá và thông tin pháp lý." }
  ]);

  // These are navigation-only family shells.  They deliberately do not turn a
  // bot command into a new execution endpoint: cards are sourced from the
  // existing registry/manifest and retain their canonical readiness state.
  const FEATURE_FAMILY_KEYS = Object.freeze(["content", "image", "video", "voice", "music", "subtitle", "documents"]);

  function featureCatalogGroup(key) {
    return FEATURE_CATALOG_GROUPS.find((group) => group.key === key) || null;
  }

  function featureFamilyForPath(path) {
    const match = /^\/features\/([^/]+)$/.exec(path);
    if (!match || !FEATURE_FAMILY_KEYS.includes(match[1])) return null;
    return featureCatalogGroup(match[1]);
  }

  function featureFamilyIcon(key) {
    const icons = {
      content: ICONS.prompt,
      image: ICONS.image,
      video: ICONS.video,
      voice: ICONS.voice,
      music: ICONS.music,
      subtitle: ICONS.subtitle,
      documents: ICONS.document
    };
    return icons[key] || ICONS.prompt;
  }

  function safeCatalogRoute(value) {
    if (typeof value !== "string") return "";
    const route = value.trim();
    if (!route.startsWith("/") || route.startsWith("//") || route.includes("\\") || route.includes("\u0000")) return "";
    return route;
  }

  function catalogEntryRoute(entry) {
    if (typeof entry === "string") return safeCatalogRoute(entry);
    if (!entry || typeof entry !== "object") return "";
    return safeCatalogRoute(entry.route || entry.path || "");
  }

  function catalogEntryState(module, page, context) {
    const key = module && typeof module === "object" && typeof module.key === "string" ? module.key : "";
    const readiness = context.readiness && context.readiness.features && key ? context.readiness.features[key] : null;
    if (readiness && typeof readiness === "object") return readiness.public_ready && context.bridge && context.bridge.featureExecutionAvailable === true ? "ready" : "guarded";
    return stateFor(page, context);
  }

  function moduleCard(module, context, label) {
    const route = safeCatalogRoute(module.route || module.path || "");
    if (!route) return "";
    const path = normalizePath(route);
    const page = manifest[path] || { path, status: "guarded", access: "member" };
    const title = typeof module.title === "string" && module.title ? module.title : page.title || "Workflow";
    const description = typeof module.description === "string" && module.description
      ? module.description
      : (typeof module.input_hint === "string" && module.input_hint ? module.input_hint : "Route được Core Bridge quản lý trạng thái theo phiên.");
    return `<a class="portal-module-card" href="${safeText(route)}"><div class="portal-module-card-top"><span class="portal-module-icon" aria-hidden="true">${safeText(module.icon || page.icon || ICONS.default)}</span>${badge(catalogEntryState(module, page, context))}</div>
      <div><h3>${safeText(title)}</h3><p>${safeText(description)}</p></div><span class="portal-module-card-footer"><span>${safeText(label || "Mở workspace")}</span><span class="portal-module-arrow" aria-hidden="true">→</span></span></a>`;
  }

  function fallbackCatalogGroup(path) {
    if (["/dashboard", "/account"].includes(path)) return "account";
    if (path.startsWith("/wallet") || ["/packages"].includes(path)) return "wallet";
    if (["/jobs", "/assets"].includes(path)) return "jobs";
    if (path === "/chat" || path === "/prompt-studio" || path.startsWith("/content")) return "content";
    if (path.startsWith("/image")) return "image";
    if (path.startsWith("/video")) return "video";
    if (path === "/voice" || path.startsWith("/voice/") || path.startsWith("/voice-studio")) return "voice";
    if (path.startsWith("/music")) return "music";
    if (["/subtitle", "/translate", "/dubbing", "/asr"].includes(path) || path.startsWith("/subtitle/")) return "subtitle";
    if (path.startsWith("/documents")) return "documents";
    return "support";
  }

  function fallbackFeatureCatalog() {
    const seen = new Set();
    return Object.values(manifest).filter((page) => {
      if (!page || page.access === "admin" || ["/features", "/login", "/register", "/onboarding", "/not-found"].includes(page.path) || seen.has(page.path)) return false;
      seen.add(page.path);
      return true;
    }).map((page) => ({
      route: page.path,
      title: page.title,
      description: page.description,
      group: fallbackCatalogGroup(page.path),
      icon: page.icon,
      kind: "customer"
    }));
  }

  function customerCatalog(context) {
    const entries = (context.catalog || []).filter((entry) => {
      const route = catalogEntryRoute(entry);
      return route && route !== "/features" && (!entry || typeof entry !== "object" || entry.kind !== "admin");
    });
    return entries.length ? entries : fallbackFeatureCatalog();
  }

  function registeredFeatureFamilyEntries(context, familyKey) {
    const seen = new Set();
    return customerCatalog(context).filter((entry) => {
      if (!entry || typeof entry !== "object" || entry.group !== familyKey || entry.kind === "admin") return false;
      const route = catalogEntryRoute(entry);
      const page = route ? manifest[normalizePath(route)] : null;
      // Never turn an inventory-only route into a clickable module card.  A
      // family navigator is a directory of registered Web workflows only.
      if (!page || page.access === "admin" || seen.has(route)) return false;
      seen.add(route);
      return true;
    });
  }

  function renderModuleCards(context) {
    const quickRoutes = ["/chat", "/content/pack", "/image/create", "/image/edit", "/video/product", "/video/multiscene", "/voice/tts", "/voice/clone", "/music/create", "/subtitle", "/dubbing", "/documents"];
    const cards = quickRoutes.map((path) => manifest[path]).filter(Boolean).map((module) => moduleCard(module, context, "Mở workspace")).join("");
    return `<section><div class="portal-section-heading"><div><span class="portal-section-kicker">Khám phá nhanh</span><h2>Bắt đầu từ workflow phù hợp</h2><p>Một số workspace tiêu biểu; toàn bộ route Web được xem trong danh mục riêng.</p></div><a class="portal-button portal-button--quiet" href="/features">Xem tất cả công cụ →</a></div><div class="portal-module-grid">${cards}</div></section>`;
  }

  function renderFeatureCatalog(page, context) {
    const entries = customerCatalog(context);
    const grouped = FEATURE_CATALOG_GROUPS.map((group) => ({ ...group, entries: entries.filter((entry) => entry && typeof entry === "object" && entry.group === group.key) })).filter((group) => group.entries.length);
    const knownGroups = new Set(FEATURE_CATALOG_GROUPS.map((group) => group.key));
    const otherEntries = entries.filter((entry) => !entry || typeof entry !== "object" || !knownGroups.has(entry.group));
    if (otherEntries.length) grouped.push({ key: "other", title: "Workflow khác", description: "Các route customer được registry công bố ngoài nhóm Studio chuẩn.", entries: otherEntries });
    const jumps = grouped.length
      ? `<nav class="portal-feature-jumps" aria-label="Đi tới nhóm công cụ">${grouped.map((group) => `<a class="portal-feature-jump" href="#feature-group-${safeText(group.key)}">${safeText(group.title)}</a>`).join("")}</nav>`
      : "";
    const groups = grouped.map((group) => `<section class="portal-feature-group" data-catalog-group aria-labelledby="feature-group-${safeText(group.key)}"><div class="portal-feature-group-head"><div><span class="portal-section-kicker">${safeText(group.title)}</span><h2 id="feature-group-${safeText(group.key)}">${safeText(group.title)}</h2><p>${safeText(group.description)}</p></div><span class="portal-feature-count">${safeText(String(group.entries.length))} workflow</span></div><div class="portal-module-grid">${group.entries.map((entry) => {
      const searchText = [group.title, entry.title, entry.description, entry.input_hint, entry.key, entry.route].filter((part) => typeof part === "string").join(" ");
      return `<div class="portal-catalog-item" data-catalog-item data-catalog-text="${safeText(searchText)}">${moduleCard(entry, context, "Mở workflow")}</div>`;
    }).join("")}</div></section>`).join("");
    const body = groups || renderEmpty("Danh mục đang chờ registry", "Core Bridge chưa cấp metadata route. Portal không tự tạo danh sách hay trạng thái giả.", "⌁");
    const search = entries.length ? `<div class="portal-catalog-search"><label for="portal-catalog-search">Tìm công cụ</label><div class="portal-catalog-search-control"><span aria-hidden="true">⌕</span><input id="portal-catalog-search" class="portal-input" type="search" data-portal-catalog-search placeholder="Ví dụ: OCR, TTS, video sản phẩm, dịch…" autocomplete="off"><button class="portal-catalog-clear" type="button" data-portal-catalog-clear hidden>Xóa</button></div><p class="portal-catalog-search-result" data-portal-catalog-result aria-live="polite">${safeText(String(entries.length))} workflow đang hiển thị.</p><div class="portal-empty" data-portal-catalog-empty hidden><span class="portal-empty-icon" aria-hidden="true">⌕</span><h3>Không tìm thấy workflow</h3><p>Thử từ khoá khác hoặc chọn một nhóm công cụ phía trên.</p></div></div>` : "";
    return `<article class="portal-page">${renderHero(page, context)}<div class="portal-status-grid">${renderStatusCard(page, context)}${renderSummary(page, context)}</div><section class="portal-feature-catalog"><div class="portal-section-heading"><div><span class="portal-section-kicker">Web App catalogue</span><h2>Tất cả workflow đã định tuyến</h2><p>${safeText(String(entries.length))} route customer từ registry hoặc manifest fallback. Trạng thái engine/output luôn do Core Bridge cấp sau signed session.</p></div><a class="portal-button portal-button--quiet" href="/dashboard">Về Dashboard →</a></div>${search}${jumps}${body}</section></article>`;
  }

  function validWorkspaceDraftId(value) {
    return /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(String(value || "").trim());
  }

  function workspaceDraftItems(context) {
    return (Array.isArray(context.workspaceDrafts) ? context.workspaceDrafts : [])
      .filter((item) => item && typeof item === "object" && validWorkspaceDraftId(item.id))
      .slice(0, 100);
  }

  function workspaceDraftStatus(item) {
    return String(item && item.state || "") === "archived" ? "archived" : "draft";
  }

  function renderWorkspaceDrafts(page, context) {
    const drafts = workspaceDraftItems(context);
    const activeCount = drafts.filter((item) => workspaceDraftStatus(item) === "draft").length;
    const archivedCount = drafts.length - activeCount;
    const canArchive = Boolean(context.capabilities && context.capabilities["workspace-draft-archive"] === true);
    const canResume = Boolean(context.capabilities && context.capabilities["workspace-draft-resume"] === true);
    const canRefresh = Boolean(context.capabilities && context.capabilities["workspace-drafts-refresh"] === true);
    const cards = drafts.length
      ? `<div class="portal-module-grid portal-workspace-draft-grid">${drafts.map((item) => {
          const id = String(item.id || "");
          const active = workspaceDraftStatus(item) === "draft";
          const route = String(item.route || "");
          const resumeDisabled = canResume && route.startsWith("/") ? "" : " disabled";
          const archiveControl = active
            ? `<button class="portal-button portal-button--quiet" type="button" data-portal-action="workspace-draft-archive" data-portal-route="/workspace" data-workspace-draft-id="${safeText(id)}" data-portal-confirm="Lưu trữ bản nháp Web này? Nó sẽ không gửi Bot, thay đổi job, Xu hay tệp."${canArchive ? "" : " disabled"}>${canArchive ? "Lưu trữ" : "Lưu trữ đang khóa"}</button>`
            : `<span class="portal-form-note">Đã lưu trữ; có thể tiếp tục thành bản mới.</span>`;
          return `<article class="portal-card portal-card-pad portal-workspace-draft" data-workspace-draft="${safeText(id)}"><div class="portal-card-header"><div><span class="portal-eyebrow">${safeText(String(item.feature_title || "Workflow Web"))}</span><h3 class="portal-card-title">${safeText(String(item.title || "Bản nháp"))}</h3><p class="portal-card-subtitle">Cập nhật ${safeText(String(item.updated_at || item.created_at || "—"))}</p></div>${badge(workspaceDraftStatus(item))}</div><div class="portal-summary-list"><div class="portal-summary-item"><span class="portal-summary-key">Workflow</span><span class="portal-summary-value">${safeText(String(item.feature_key || "—"))}</span></div><div class="portal-summary-item"><span class="portal-summary-key">Dữ liệu đã lưu</span><span class="portal-summary-value">Brief scalar Web-only</span></div></div><div class="portal-form-footer"><button class="portal-button portal-button--primary" type="button" data-portal-action="workspace-draft-resume" data-portal-route="/workspace" data-workspace-draft-id="${safeText(id)}"${resumeDisabled}>Tiếp tục brief</button>${archiveControl}</div></article>`;
        }).join("")}</div>`
      : renderEmpty("Chưa có bản nháp Web", "Mở một workflow rồi chọn “Lưu bản nháp Web”. Bạn có thể lưu brief trước khi Telegram/Core Bridge sẵn sàng; không có request nào được gửi sang Bot.", "✦");
    return `<article class="portal-page portal-workspace-drafts">${renderHero(page, context)}
      <section class="portal-card portal-card-pad portal-campaign-boundary"><div class="portal-state" data-state="read_only"><span class="portal-state-icon" aria-hidden="true">⌁</span><div><h2>Bản nháp Web, không phải job</h2><p>Thư viện này chỉ lưu brief và lựa chọn scalar thuộc signed account. Nó không lưu file, upload ID, Voice Vault profile, quote receipt, provider, payment, Xu, job hay output.</p><div class="portal-state-meta"><span>${safeText(String(activeCount))} đang hoạt động</span><span>${safeText(String(archivedCount))} đã lưu trữ</span><span>Tối đa 100 bản active</span></div></div></div></section>
      <section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Bản nháp gần đây</h2><p class="portal-card-subtitle">Resume chỉ đưa brief hợp lệ trở lại đúng form. Tệp và các lựa chọn canonical nhạy cảm luôn phải được chọn/kiểm tra lại trong workflow.</p></div><div class="portal-inline-actions"><button class="portal-button portal-button--quiet" type="button" data-portal-action="workspace-drafts-refresh" data-portal-route="/workspace"${canRefresh ? "" : " disabled"}>Làm mới</button><a class="portal-button portal-button--primary" href="/features">Mở workflow</a></div></div>${cards}</section>
      <section class="portal-card portal-card-pad"><div class="portal-notice portal-notice--info"><span class="portal-notice-icon" aria-hidden="true">i</span><div><strong>Ranh giới an toàn</strong><p>Mỗi lần tiếp tục vẫn phải qua validation form, staging upload, estimate, confirmation và Bot canonical. Bản nháp không chứng minh quyền sở hữu file, không giữ giá/Xu và không tạo kết quả.</p></div></div></section>
    </article>`;
  }

  const PROJECT_DOCUMENT_KINDS = Object.freeze([
    ["brief", "Creative brief"], ["prompt", "Prompt"], ["caption", "Caption"],
    ["script", "Kịch bản"], ["storyboard", "Storyboard"], ["content_pack", "Content pack"], ["note", "Ghi chú"]
  ]);

  function validProjectId(value) {
    return /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(String(value || "").trim());
  }

  function projectState(value) {
    return String(value || "") === "archived" ? "archived" : "ready";
  }

  function projectFormFields() {
    return [
      { name: "title", label: "Tên Project", placeholder: "Ví dụ: Ra mắt sản phẩm mùa hè", required: true, minLength: 3, maxLength: 160, help: "Không gian làm việc riêng cho brief và Studio Document của bạn." },
      { name: "summary", label: "Tóm tắt", control: "textarea", placeholder: "Bối cảnh, khách hàng hoặc định hướng sáng tạo…", maxLength: 1000, help: "Dữ liệu authoring Web-owned; không gửi Bot, provider hoặc payment." },
      { name: "objective", label: "Mục tiêu", placeholder: "Ví dụ: Tăng chuyển đổi landing page", maxLength: 160, help: "Mục tiêu nội bộ của Project, có thể chỉnh sửa về sau." }
    ];
  }

  function projectDocumentFormFields() {
    return [
      { name: "kind", label: "Loại Studio Document", control: "select", required: true, options: PROJECT_DOCUMENT_KINDS.map(([value, label]) => ({ value, label })) },
      { name: "title", label: "Tên tài liệu", placeholder: "Ví dụ: Storyboard video 30 giây", required: true, minLength: 3, maxLength: 160 },
      { name: "content", label: "Nội dung", control: "textarea", placeholder: "Viết brief, prompt, caption, kịch bản hoặc storyboard của bạn…", required: true, minLength: 1, maxLength: 12000, help: "Mỗi lần lưu sẽ tạo một phiên bản mới. Không lưu API key, token, mật khẩu hoặc số thẻ." }
    ];
  }

  function renderProjectCenter(page, context) {
    const projects = (Array.isArray(context.projects) ? context.projects : []).filter((item) => item && typeof item === "object" && validProjectId(item.id)).slice(0, 100);
    const active = projects.filter((item) => String(item.state || "active") === "active");
    const canCreate = Boolean(context.capabilities && context.capabilities["project-create"] === true);
    const formId = "portal-project-create";
    const cards = projects.length
      ? `<div class="portal-project-grid">${projects.map((project) => `<article class="portal-card portal-card-pad portal-project-card"><div class="portal-card-header"><div><span class="portal-eyebrow">Web-owned Project</span><h2 class="portal-card-title">${safeText(String(project.title || "Project"))}</h2><p class="portal-card-subtitle">${safeText(String(project.summary || project.objective || "Chưa có mô tả"))}</p></div>${badge(projectState(project.state))}</div><div class="portal-summary-list"><div class="portal-summary-item"><span class="portal-summary-key">Mục tiêu</span><span class="portal-summary-value">${safeText(String(project.objective || "Chưa đặt"))}</span></div><div class="portal-summary-item"><span class="portal-summary-key">Studio Documents</span><span class="portal-summary-value">${safeText(String(Number(project.document_count || 0)))}</span></div><div class="portal-summary-item"><span class="portal-summary-key">Cập nhật</span><span class="portal-summary-value">${safeText(String(project.updated_at || "—"))}</span></div></div><div class="portal-form-footer"><a class="portal-button portal-button--primary" href="/projects/${encodeURIComponent(String(project.id))}">Mở Project <span aria-hidden="true">→</span></a></div></article>`).join("")}</div>`
      : renderEmpty("Chưa có Project", "Tạo Project đầu tiên để gom brief, prompt, caption, kịch bản và storyboard vào một lịch sử version riêng của Web.", "✦");
    return `<article class="portal-page portal-project-center">${renderHero(page, context)}<section class="portal-project-intro"><div><span class="portal-section-kicker">Independent Web Workspace</span><h2>Biến ý tưởng thành hệ thống tài liệu có thể tiếp tục</h2><p>Project Center là không gian Web-owned: không cần Telegram, không gọi Bot, provider, PayOS hoặc Xu để tạo và version hóa tài liệu sáng tạo.</p></div><dl><div><dt>${safeText(String(active.length))}</dt><dd>Project đang hoạt động</dd></div><div><dt>${safeText(String(projects.reduce((total, item) => total + Number(item.document_count || 0), 0)))}</dt><dd>Studio Documents</dd></div></dl></section><div class="portal-work-grid"><section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Tạo Project mới</h2><p class="portal-card-subtitle">Bắt đầu bằng brief, sau đó thêm prompt, caption, script hoặc storyboard có history rõ ràng.</p></div>${badge(canCreate ? "ready" : "guarded")}</div><form id="${formId}" class="portal-form" data-portal-form data-portal-action="project-create" data-portal-route="/projects" novalidate>${renderFields(projectFormFields(), canCreate, context, transientFormValues("/projects"))}<div class="portal-form-footer"><span class="portal-form-note">Chỉ signed session + CSRF được tạo Project. Không có Bot/bridge/provider call trong thao tác này.</span><button class="portal-button portal-button--primary" type="submit"${canCreate ? "" : " disabled"}>Tạo Project</button></div></form></section><aside class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Cách hoạt động</h2><p class="portal-card-subtitle">Một lớp authoring riêng trước khi bạn chọn bất kỳ engine hay integration nào.</p></div></div><ol class="portal-project-steps"><li><strong>1. Đặt brief</strong><span>Tạo Project với mục tiêu và bối cảnh.</span></li><li><strong>2. Xây tài liệu</strong><span>Thêm prompt, caption, script hoặc storyboard.</span></li><li><strong>3. Version rõ ràng</strong><span>Mỗi lần lưu Studio Document tạo một revision bất biến.</span></li></ol></aside></div><section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Project gần đây</h2><p class="portal-card-subtitle">Chỉ Project thuộc signed account hiện tại được hiển thị.</p></div><button class="portal-button portal-button--quiet" type="button" data-portal-action="projects-refresh" data-portal-route="/projects">Làm mới</button></div>${cards}</section></article>`;
  }

  // Memory Center mirrors the useful organization flow from the Bot while
  // keeping a deliberately separate, signed Web-owned record set.  It is not
  // a UI proxy for Telegram messages: notes, versions and reminders remain
  // private to the current browser account and delivery is Web-view-only.
  const MEMORY_PRIORITIES = Object.freeze([
    ["low", "Thấp"], ["normal", "Bình thường"], ["important", "Quan trọng"], ["urgent", "Khẩn"]
  ]);
  const MEMORY_REPEAT_RULES = Object.freeze([
    ["none", "Một lần"], ["daily", "Mỗi ngày"], ["weekly", "Mỗi tuần"], ["monthly", "Mỗi tháng"], ["yearly", "Mỗi năm"]
  ]);

  function validMemoryId(value) {
    return validProjectId(value);
  }

  function memoryItems(context, key) {
    const rows = Array.isArray(context && context[key]) ? context[key] : [];
    return rows.filter((item) => item && typeof item === "object" && validMemoryId(item.id)).slice(0, 100);
  }

  function memoryPriorityLabel(value) {
    return ({ low: "Thấp", normal: "Bình thường", important: "Quan trọng", urgent: "Khẩn" })[String(value || "")] || "Bình thường";
  }

  function memoryRepeatLabel(value) {
    return ({ none: "Một lần", daily: "Mỗi ngày", weekly: "Mỗi tuần", monthly: "Mỗi tháng", yearly: "Mỗi năm" })[String(value || "")] || "Một lần";
  }

  function memoryEventLabel(value) {
    return ({
      note_created: "Đã tạo ghi chú", note_updated: "Đã lưu phiên bản ghi chú", note_archived: "Đã archive ghi chú",
      note_restored: "Đã khôi phục ghi chú", note_version_restored: "Đã khôi phục phiên bản ghi chú",
      reminder_created: "Đã tạo reminder", reminder_updated: "Đã cập nhật reminder", reminder_complete: "Đã hoàn tất reminder",
      reminder_pause: "Đã tạm dừng reminder", reminder_resume: "Đã tiếp tục reminder", reminder_cancel: "Đã hủy reminder"
    })[String(value || "")] || "Đã cập nhật Memory Center";
  }

  function memoryTags(tags) {
    return Array.isArray(tags) ? tags.filter((tag) => typeof tag === "string" && tag.trim()).slice(0, 12) : [];
  }

  function renderMemoryTagList(tags) {
    const values = memoryTags(tags);
    return values.length ? `<div class="portal-memory-tags">${values.map((tag) => `<span>${safeText(tag)}</span>`).join("")}</div>` : "";
  }

  function memoryNoteFormFields() {
    return [
      { name: "title", label: "Tiêu đề", placeholder: "Ví dụ: Ý tưởng video tháng 8", required: true, minLength: 3, maxLength: 160 },
      { name: "content", label: "Nội dung", control: "textarea", placeholder: "Viết nội dung cần nhớ, quyết định, bối cảnh hoặc checklist…", required: true, minLength: 1, maxLength: 12000, help: "Không lưu API key, token, mật khẩu hoặc số thẻ." },
      { name: "tags", label: "Tags", placeholder: "Ví dụ: launch, video, ưu tiên", maxLength: 520, help: "Phân tách bằng dấu phẩy; tối đa 12 tags." },
      { name: "category", label: "Danh mục", placeholder: "Ví dụ: Marketing", maxLength: 80 },
      { name: "priority", label: "Ưu tiên", control: "select", options: MEMORY_PRIORITIES }
    ];
  }

  function memoryNoteFilterState(context) {
    const source = context && context.memoryNoteFilter && typeof context.memoryNoteFilter === "object"
      ? context.memoryNoteFilter
      : {};
    const priority = String(source.priority || "");
    const state = String(source.state || "all");
    return {
      q: typeof source.q === "string" ? source.q.replace(/\s+/g, " ").trim().slice(0, 80) : "",
      priority: MEMORY_PRIORITIES.some(([value]) => value === priority) ? priority : "",
      state: ["all", "active", "archived"].includes(state) ? state : "all"
    };
  }

  function memoryNoteFilterFields() {
    return [
      { name: "q", label: "Tìm ghi chú", placeholder: "Tiêu đề, tag, danh mục hoặc nội dung…", maxLength: 80, wide: true },
      { name: "priority", label: "Ưu tiên", control: "select", options: MEMORY_PRIORITIES, emptyLabel: "Mọi mức ưu tiên" },
      { name: "state", label: "Trạng thái", control: "select", options: [["all", "Tất cả"], ["active", "Đang hoạt động"], ["archived", "Đã archive"]] }
    ];
  }

  function memoryReminderFormFields() {
    return [
      { name: "title", label: "Tiêu đề reminder", placeholder: "Ví dụ: Rà soát storyboard", required: true, minLength: 3, maxLength: 160 },
      { name: "body", label: "Ghi chú", control: "textarea", placeholder: "Bối cảnh hoặc checklist ngắn (tùy chọn)", maxLength: 2000 },
      { name: "due_at", label: "Thời điểm", type: "datetime-local", required: true, help: "Reminder chỉ hiện trong Web Workspace; chưa gửi Telegram, email hoặc push." },
      { name: "timezone", label: "Múi giờ", control: "select", options: [["Asia/Ho_Chi_Minh", "Asia/Ho_Chi_Minh (GMT+7)"], ["UTC", "UTC"]] },
      { name: "repeat_rule", label: "Lặp lại", control: "select", options: MEMORY_REPEAT_RULES },
      { name: "note_id", label: "Liên kết ghi chú", control: "select", optionsFrom: "memoryNotes", emptyLabel: "Không liên kết ghi chú" }
    ];
  }

  function memoryNoteEditor(page, context) {
    const detail = context.memoryNoteDetail && typeof context.memoryNoteDetail === "object" ? context.memoryNoteDetail : {};
    const note = detail.note && typeof detail.note === "object" && validMemoryId(detail.note.id) ? detail.note : null;
    if (!note) {
      return `<section class="portal-card portal-card-pad portal-memory-editor"><div class="portal-card-header"><div><span class="portal-section-kicker">Version history</span><h2 class="portal-card-title">Mở một ghi chú</h2><p class="portal-card-subtitle">Nội dung đầy đủ chỉ được nạp sau owner check ở server.</p></div>${badge("read_only")}</div>${renderEmpty("Chưa chọn ghi chú", "Chọn một ghi chú ở danh sách để xem, chỉnh sửa hoặc khôi phục phiên bản. Web không đọc Memory của Bot.", "◇")}</section>`;
    }
    const state = String(note.state || "active");
    const canWrite = Boolean(context.capabilities && context.capabilities["memory-note-update"] === true && state === "active");
    const canArchive = Boolean(context.capabilities && context.capabilities["memory-note-archive"] === true && state === "active");
    const canRestore = Boolean(context.capabilities && context.capabilities["memory-note-restore"] === true && state === "archived");
    const canRestoreVersion = Boolean(context.capabilities && context.capabilities["memory-note-restore-version"] === true && state === "active");
    const route = page.routePath || page.path;
    const values = { ...note, tags: memoryTags(note.tags).join(", ") };
    const versions = Array.isArray(detail.versions) ? detail.versions.filter((item) => item && Number.isInteger(Number(item.revision))).slice(0, 50) : [];
    const related = Array.isArray(detail.reminders) ? detail.reminders.filter((item) => item && validMemoryId(item.id)).slice(0, 20) : [];
    const stateAction = state === "active"
      ? `<button class="portal-button portal-button--quiet" type="button" data-portal-action="memory-note-archive" data-portal-route="${safeText(route)}" data-memory-note-id="${safeText(String(note.id))}" data-memory-note-revision="${safeText(String(note.revision))}" data-portal-confirm="Archive ghi chú này? Reminder liên kết sẽ không bị thay đổi tự động."${canArchive ? "" : " disabled"}>${canArchive ? "Archive" : "Archive đang khóa"}</button>`
      : `<button class="portal-button portal-button--primary" type="button" data-portal-action="memory-note-restore" data-portal-route="${safeText(route)}" data-memory-note-id="${safeText(String(note.id))}" data-memory-note-revision="${safeText(String(note.revision))}"${canRestore ? "" : " disabled"}>Khôi phục ghi chú</button>`;
    const versionList = versions.length
      ? `<div class="portal-version-list">${versions.map((version) => `<div class="portal-version-row"><span><strong>v${safeText(String(version.revision))}</strong><small>${safeText(String(version.title || "Ghi chú"))} · ${safeText(String(version.created_at || "—"))}</small></span>${Number(version.revision) === Number(note.revision) ? `<span class="portal-form-note">Đang mở</span>` : `<button class="portal-button portal-button--quiet" type="button" data-portal-action="memory-note-restore-version" data-portal-route="${safeText(route)}" data-memory-note-id="${safeText(String(note.id))}" data-memory-note-revision="${safeText(String(note.revision))}" data-memory-note-version="${safeText(String(version.revision))}" data-portal-confirm="Khôi phục v${safeText(String(version.revision))} thành một phiên bản mới? Phiên bản hiện tại vẫn còn trong history."${canRestoreVersion ? "" : " disabled"}>Khôi phục</button>`}</div>`).join("")}</div>`
      : renderEmpty("Chưa có version history", "Version đầu tiên được lưu cùng ghi chú và không bị xóa khi cập nhật.", "○");
    const linked = related.length ? `<div class="portal-memory-linked-list">${related.map((item) => `<a href="/reminders" class="portal-memory-linked"><span><strong>${safeText(String(item.title || "Reminder"))}</strong><small>${safeText(memoryRepeatLabel(item.repeat_rule))} · ${safeText(String(item.next_run_at || item.due_at || "—"))}</small></span>${badge(String(item.state || "read_only"))}</a>`).join("")}</div>` : renderEmpty("Chưa có reminder liên kết", "Bạn có thể tạo reminder từ tab Nhắc việc và liên kết lại với ghi chú này.", "○");
    return `<section class="portal-card portal-card-pad portal-memory-editor"><div class="portal-card-header"><div><span class="portal-section-kicker">${safeText(memoryPriorityLabel(note.priority))} · v${safeText(String(note.revision))}</span><h2 class="portal-card-title">${safeText(String(note.title || "Ghi chú"))}</h2><p class="portal-card-subtitle">${state === "archived" ? "Ghi chú đang archive và giữ nguyên history." : "Mỗi lần lưu tạo phiên bản bất biến; không có ghi đè âm thầm."}</p></div>${badge(state === "archived" ? "read_only" : "ready")}</div><form class="portal-form" data-portal-form data-portal-action="memory-note-update" data-portal-route="${safeText(route)}" data-memory-note-id="${safeText(String(note.id))}" data-memory-note-revision="${safeText(String(note.revision))}" novalidate>${renderFields(memoryNoteFormFields(), canWrite, context, values)}<div class="portal-form-footer"><span class="portal-form-note">Optimistic revision bảo vệ thay đổi đang mở. Server luôn kiểm tra ownership, CSRF và idempotency.</span><div class="portal-inline-actions">${stateAction}<button class="portal-button portal-button--primary" type="submit"${canWrite ? "" : " disabled"}>Lưu phiên bản mới</button></div></div></form><section class="portal-project-history"><div class="portal-section-heading"><div><span class="portal-section-kicker">Version history</span><h3>Lịch sử phiên bản</h3><p>Khôi phục luôn tạo một revision mới, không sửa version cũ.</p></div></div>${versionList}</section><section class="portal-project-history"><div class="portal-section-heading"><div><span class="portal-section-kicker">Linked reminders</span><h3>Nhắc việc liên kết</h3><p>Trạng thái reminder luôn explicit; archive ghi chú không tự tắt reminder.</p></div></div>${linked}</section></section>`;
  }

  function renderMemoryNotes(page, context) {
    const notes = memoryItems(context, "memoryNotes");
    const summary = context.memorySummary && typeof context.memorySummary === "object" ? context.memorySummary : {};
    const noteSummary = summary.notes && typeof summary.notes === "object" ? summary.notes : {};
    const canView = Boolean(context.capabilities && context.capabilities["memory-view"] === true);
    const canCreate = Boolean(context.capabilities && context.capabilities["memory-note-create"] === true);
    if (!canView) return `<article class="portal-page portal-memory-center">${renderHero(page, context)}<section class="portal-card portal-card-pad">${renderEmpty("Memory Center đang được bảo vệ", "Đăng nhập bằng signed session để nạp ghi chú riêng tư. Web không dùng Telegram ID thô hoặc fallback sang Bot state.", "⌁")}</section></article>`;
    const filter = memoryNoteFilterState(context);
    const cards = notes.length
      ? `<div class="portal-memory-note-list">${notes.map((note) => `<button type="button" class="portal-memory-note" data-portal-action="memory-note-open" data-portal-route="/notes" data-memory-note-id="${safeText(String(note.id))}"><span class="portal-memory-note-head"><span><strong>${safeText(String(note.title || "Ghi chú"))}</strong><small>${safeText(String(note.category || "Chưa phân loại"))} · cập nhật ${safeText(String(note.updated_at || note.created_at || "—"))}</small></span>${badge(String(note.state || "read_only"))}</span><span class="portal-memory-note-excerpt">${safeText(String(note.excerpt || ""))}</span><span class="portal-memory-note-footer"><span class="portal-memory-priority" data-priority="${safeText(String(note.priority || "normal"))}">${safeText(memoryPriorityLabel(note.priority))}</span>${renderMemoryTagList(note.tags)}<b aria-hidden="true">→</b></span></button>`).join("")}</div>`
      : renderEmpty(filter.q || filter.priority || filter.state !== "all" ? "Không có ghi chú phù hợp" : "Chưa có ghi chú", filter.q || filter.priority || filter.state !== "all" ? "Điều chỉnh từ khóa hoặc bộ lọc để xem các ghi chú Web-owned khác." : "Tạo ghi chú đầu tiên để lưu bối cảnh, checklist và quyết định trong một Web Workspace riêng tư.", "◇");
    const filterForm = `<form class="portal-memory-filter" data-portal-form data-portal-action="memory-note-filter" data-portal-route="/notes" novalidate>${renderFields(memoryNoteFilterFields(), true, context, filter)}<div class="portal-form-footer"><span class="portal-form-note">Tìm kiếm thực hiện trên API owner-scoped, không tạo Bot hand-off hoặc lưu query vào URL.</span><div class="portal-inline-actions"><button class="portal-button portal-button--quiet" type="button" data-portal-action="memory-note-filter-clear" data-portal-route="/notes">Xóa lọc</button><button class="portal-button portal-button--primary" type="submit">Tìm kiếm</button></div></div></form>`;
    return `<article class="portal-page portal-memory-center">${renderHero(page, context)}
      <section class="portal-memory-intro"><div><span class="portal-section-kicker">Private Web memory</span><h2>Giữ ý tưởng, quyết định và việc cần làm ở đúng ngữ cảnh</h2><p>Memory Center hoạt động độc lập trên Web với tag, ưu tiên, archive và revision history. Nó không gửi nội dung sang Bot hay provider.</p></div><dl><div><dt>${safeText(String(Number(noteSummary.active || 0)))}</dt><dd>Ghi chú đang hoạt động</dd></div><div><dt>${safeText(String(Number(noteSummary.archived || 0)))}</dt><dd>Đã archive</dd></div><div><dt>v∞</dt><dd>Lịch sử phiên bản bất biến</dd></div></dl></section>
      <div class="portal-memory-layout"><section class="portal-card portal-card-pad portal-memory-create"><div class="portal-card-header"><div><h2 class="portal-card-title">Tạo ghi chú</h2><p class="portal-card-subtitle">Dùng tag và ưu tiên để biến một ý tưởng rời rạc thành bối cảnh có thể tiếp tục.</p></div>${badge(canCreate ? "ready" : "guarded")}</div><form class="portal-form" data-portal-form data-portal-action="memory-note-create" data-portal-route="/notes" novalidate>${renderFields(memoryNoteFormFields(), canCreate, context, transientFormValues("/notes"))}<div class="portal-form-footer"><span class="portal-form-note">Không tạo job, charge, output hoặc notification. Dữ liệu chỉ thuộc signed Web account hiện tại.</span><button class="portal-button portal-button--primary" type="submit"${canCreate ? "" : " disabled"}>Lưu ghi chú</button></div></form></section><aside class="portal-card portal-card-pad portal-memory-boundary"><div class="portal-card-header"><div><span class="portal-section-kicker">Privacy boundary</span><h2 class="portal-card-title">Web-owned, không giả delivery</h2><p class="portal-card-subtitle">Reminder chỉ hiển thị trong app. Nếu cần Telegram/email/push, đó là adapter riêng và sẽ không được tự nhận là đã gửi.</p></div></div>${renderNotes(page)}</aside></div>
      <section class="portal-memory-content"><section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Ghi chú của tôi</h2><p class="portal-card-subtitle">Tìm theo nội dung, tag hoặc danh mục; chọn một ghi chú để mở nội dung đầy đủ cùng history.</p></div><button class="portal-button portal-button--quiet" type="button" data-portal-action="memory-refresh" data-portal-route="/notes">Làm mới</button></div>${filterForm}${cards}</section>${memoryNoteEditor(page, context)}</section>
    </article>`;
  }

  function memoryDateInputValue(value, timezoneName) {
    const source = String(value || "").trim();
    if (!source) return "";
    const date = new Date(source);
    if (Number.isNaN(date.getTime())) return "";
    try {
      const parts = new Intl.DateTimeFormat("en-CA", {
        timeZone: timezoneName === "UTC" ? "UTC" : "Asia/Ho_Chi_Minh",
        year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", hourCycle: "h23"
      }).formatToParts(date).reduce((result, item) => ({ ...result, [item.type]: item.value }), {});
      return `${parts.year || ""}-${parts.month || ""}-${parts.day || ""}T${parts.hour || ""}:${parts.minute || ""}`;
    } catch (_) {
      return "";
    }
  }

  function renderMemoryReminderEdit(item, context, route) {
    const id = String(item.id || "");
    const state = String(item.state || "active");
    const canEdit = Boolean(context.capabilities && context.capabilities["memory-reminder-update"] === true && ["active", "paused"].includes(state));
    const linkedNotes = memoryItems(context, "memoryNotes").filter((note) => String(note.state || "active") === "active");
    const noteOptions = `<option value=""${item.note_id ? "" : " selected"}>Không liên kết ghi chú</option>${linkedNotes.map((note) => `<option value="${safeText(String(note.id))}"${String(note.id) === String(item.note_id || "") ? " selected" : ""}>${safeText(String(note.title || "Ghi chú Web"))}</option>`).join("")}`;
    return `<details class="portal-memory-reminder-edit"><summary>Chỉnh sửa reminder</summary><form class="portal-form" data-portal-form data-portal-action="memory-reminder-update" data-portal-route="${safeText(route)}" data-memory-reminder-id="${safeText(id)}" data-memory-reminder-revision="${safeText(String(item.revision || 1))}" novalidate><div class="portal-fields"><div class="portal-field portal-field--wide"><label for="memory-reminder-title-${safeText(id)}">Tiêu đề<span class="portal-required-mark" aria-hidden="true">*</span></label><input class="portal-input" id="memory-reminder-title-${safeText(id)}" name="title" value="${safeText(String(item.title || ""))}" minlength="3" maxlength="160" required${canEdit ? "" : " disabled"}></div><div class="portal-field portal-field--wide"><label for="memory-reminder-body-${safeText(id)}">Ghi chú</label><textarea class="portal-textarea" id="memory-reminder-body-${safeText(id)}" name="body" maxlength="2000"${canEdit ? "" : " disabled"}>${safeText(String(item.body || ""))}</textarea></div><div class="portal-field"><label for="memory-reminder-due-${safeText(id)}">Thời điểm<span class="portal-required-mark" aria-hidden="true">*</span></label><input class="portal-input" id="memory-reminder-due-${safeText(id)}" name="due_at" type="datetime-local" value="${safeText(memoryDateInputValue(item.next_run_at || item.due_at, item.timezone))}" required${canEdit ? "" : " disabled"}></div><div class="portal-field"><label for="memory-reminder-timezone-${safeText(id)}">Múi giờ</label><select class="portal-select" id="memory-reminder-timezone-${safeText(id)}" name="timezone"${canEdit ? "" : " disabled"}><option value="Asia/Ho_Chi_Minh"${String(item.timezone || "") === "Asia/Ho_Chi_Minh" ? " selected" : ""}>Asia/Ho_Chi_Minh (GMT+7)</option><option value="UTC"${String(item.timezone || "") === "UTC" ? " selected" : ""}>UTC</option></select></div><div class="portal-field"><label for="memory-reminder-repeat-${safeText(id)}">Lặp lại</label><select class="portal-select" id="memory-reminder-repeat-${safeText(id)}" name="repeat_rule"${canEdit ? "" : " disabled"}>${MEMORY_REPEAT_RULES.map(([value, label]) => `<option value="${safeText(value)}"${String(item.repeat_rule || "none") === value ? " selected" : ""}>${safeText(label)}</option>`).join("")}</select></div><div class="portal-field"><label for="memory-reminder-note-${safeText(id)}">Ghi chú liên kết</label><select class="portal-select" id="memory-reminder-note-${safeText(id)}" name="note_id"${canEdit ? "" : " disabled"}>${noteOptions}</select></div></div><div class="portal-form-footer"><span class="portal-form-note">Lưu lại yêu cầu revision hiện tại để tránh ghi đè một thay đổi ở tab khác.</span><button class="portal-button portal-button--primary" type="submit"${canEdit ? "" : " disabled"}>Lưu thay đổi</button></div></form></details>`;
  }

  function renderMemoryReminderCard(item, context, route) {
    const id = String(item.id || "");
    const state = String(item.state || "read_only");
    const revision = String(item.revision || 1);
    const canComplete = Boolean(context.capabilities && context.capabilities["memory-reminder-complete"] === true && state === "active");
    const canPause = Boolean(context.capabilities && context.capabilities["memory-reminder-pause"] === true && state === "active");
    const canResume = Boolean(context.capabilities && context.capabilities["memory-reminder-resume"] === true && state === "paused");
    const canCancel = Boolean(context.capabilities && context.capabilities["memory-reminder-cancel"] === true && ["active", "paused"].includes(state));
    const stateActions = state === "active"
      ? `<button class="portal-button portal-button--quiet" type="button" data-portal-action="memory-reminder-complete" data-portal-route="${safeText(route)}" data-memory-reminder-id="${safeText(id)}" data-memory-reminder-revision="${safeText(revision)}"${canComplete ? "" : " disabled"}>Hoàn tất</button><button class="portal-button portal-button--quiet" type="button" data-portal-action="memory-reminder-pause" data-portal-route="${safeText(route)}" data-memory-reminder-id="${safeText(id)}" data-memory-reminder-revision="${safeText(revision)}"${canPause ? "" : " disabled"}>Tạm dừng</button><button class="portal-button portal-button--quiet" type="button" data-portal-action="memory-reminder-cancel" data-portal-route="${safeText(route)}" data-memory-reminder-id="${safeText(id)}" data-memory-reminder-revision="${safeText(revision)}" data-portal-confirm="Hủy reminder này? Hành động không gửi notification và không thể tự đảo ngược."${canCancel ? "" : " disabled"}>Hủy</button>`
      : state === "paused"
        ? `<button class="portal-button portal-button--primary" type="button" data-portal-action="memory-reminder-resume" data-portal-route="${safeText(route)}" data-memory-reminder-id="${safeText(id)}" data-memory-reminder-revision="${safeText(revision)}"${canResume ? "" : " disabled"}>Tiếp tục</button><button class="portal-button portal-button--quiet" type="button" data-portal-action="memory-reminder-cancel" data-portal-route="${safeText(route)}" data-memory-reminder-id="${safeText(id)}" data-memory-reminder-revision="${safeText(revision)}" data-portal-confirm="Hủy reminder này? Hành động không gửi notification và không thể tự đảo ngược."${canCancel ? "" : " disabled"}>Hủy</button>`
        : `<span class="portal-form-note">${state === "completed" ? "Reminder đã hoàn tất." : "Reminder đã hủy."}</span>`;
    const due = String(item.next_run_at || item.due_at || "—");
    return `<article class="portal-card portal-card-pad portal-memory-reminder-card"><div class="portal-card-header"><div><span class="portal-section-kicker">${safeText(memoryRepeatLabel(item.repeat_rule))}</span><h3 class="portal-card-title">${safeText(String(item.title || "Reminder"))}</h3><p class="portal-card-subtitle">${safeText(String(item.body || "Không có ghi chú bổ sung."))}</p></div>${badge(state)}</div><dl class="portal-memory-reminder-meta"><div><dt>Lần chạy</dt><dd>${safeText(due)}</dd></div><div><dt>Múi giờ</dt><dd>${safeText(String(item.timezone || "—"))}</dd></div><div><dt>Liên kết</dt><dd>${safeText(String(item.note_title || "Không có ghi chú"))}</dd></div></dl>${item.overdue === true && state === "active" ? `<p class="portal-memory-overdue" role="status">Đã quá thời điểm; Web chỉ đánh dấu để bạn chủ động xử lý, không tuyên bố đã gửi thông báo.</p>` : ""}<div class="portal-form-footer"><div class="portal-inline-actions">${stateActions}</div></div>${renderMemoryReminderEdit(item, context, route)}</article>`;
  }

  function renderMemoryReminders(page, context) {
    const reminders = memoryItems(context, "memoryReminders");
    const summary = context.memorySummary && typeof context.memorySummary === "object" ? context.memorySummary : {};
    const reminderSummary = summary.reminders && typeof summary.reminders === "object" ? summary.reminders : {};
    const canView = Boolean(context.capabilities && context.capabilities["memory-view"] === true);
    const canCreate = Boolean(context.capabilities && context.capabilities["memory-reminder-create"] === true);
    const route = page.routePath || page.path;
    if (!canView) return `<article class="portal-page portal-memory-reminders">${renderHero(page, context)}<section class="portal-card portal-card-pad">${renderEmpty("Reminder đang được bảo vệ", "Đăng nhập bằng signed session để xem hoặc quản lý reminder riêng tư. Bot reminder không được đưa sang Web bằng raw Telegram ID.", "⌁")}</section></article>`;
    const cards = reminders.length ? `<div class="portal-memory-reminder-grid">${reminders.map((item) => renderMemoryReminderCard(item, context, route)).join("")}</div>` : renderEmpty("Chưa có reminder", "Tạo mốc đầu tiên để theo dõi việc cần làm trong Web Workspace. Web sẽ không giả lập Telegram/email/push delivery.", "◷");
    const events = memoryItems(context, "memoryEvents");
    const eventList = events.length ? `<div class="portal-memory-event-list">${events.map((item) => `<div class="portal-memory-event"><span aria-hidden="true">•</span><span><strong>${safeText(memoryEventLabel(item.action))}</strong><small>${safeText(String(item.created_at || "—"))}</small></span></div>`).join("")}</div>` : renderEmpty("Chưa có hoạt động", "Các cập nhật note/reminder của Web account sẽ xuất hiện tại đây sau khi server ghi audit event.", "○");
    return `<article class="portal-page portal-memory-reminders">${renderHero(page, context)}<section class="portal-memory-intro"><div><span class="portal-section-kicker">Web view-only delivery</span><h2>Quản lý nhịp công việc mà không đánh đồng với thông báo đã gửi</h2><p>Reminder giữ lịch một lần hoặc lặp lại, pause/resume và complete. Web chỉ hiển thị trạng thái trong account của bạn; Telegram, email và push cần adapter riêng.</p></div><dl><div><dt>${safeText(String(Number(reminderSummary.active || 0)))}</dt><dd>Đang hoạt động</dd></div><div><dt>${safeText(String(Number(reminderSummary.due_soon || 0)))}</dt><dd>Đến hạn trong 24h</dd></div><div><dt>${safeText(String(Number(reminderSummary.overdue || 0)))}</dt><dd>Cần xem lại</dd></div></dl></section><div class="portal-memory-layout"><section class="portal-card portal-card-pad portal-memory-create"><div class="portal-card-header"><div><h2 class="portal-card-title">Tạo reminder</h2><p class="portal-card-subtitle">Chọn mốc, múi giờ, lịch lặp và tùy chọn liên kết một ghi chú đang active.</p></div>${badge(canCreate ? "ready" : "guarded")}</div><form class="portal-form" data-portal-form data-portal-action="memory-reminder-create" data-portal-route="${safeText(route)}" novalidate>${renderFields(memoryReminderFormFields(), canCreate, context, transientFormValues(route))}<div class="portal-form-footer"><span class="portal-form-note">Không tạo Bot job, Xu, PayOS, provider call hay notification delivery.</span><button class="portal-button portal-button--primary" type="submit"${canCreate ? "" : " disabled"}>Tạo reminder</button></div></form></section><aside class="portal-card portal-card-pad portal-memory-boundary"><div class="portal-card-header"><div><span class="portal-section-kicker">Explicit status</span><h2 class="portal-card-title">Không có thông báo giả</h2><p class="portal-card-subtitle">Quá hạn chỉ là state để bạn xem lại. Việc complete reminder lặp lại tính mốc tiếp theo ở server theo đúng múi giờ đã chọn.</p></div></div>${renderNotes(page)}</aside></div><section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Reminder của tôi</h2><p class="portal-card-subtitle">Mọi thay đổi phải có CSRF, revision và idempotency. Các trạng thái terminal không thể chỉnh sửa.</p></div><button class="portal-button portal-button--quiet" type="button" data-portal-action="memory-refresh" data-portal-route="${safeText(route)}">Làm mới</button></div>${cards}</section><section class="portal-card portal-card-pad"><div class="portal-card-header"><div><span class="portal-section-kicker">Audit-safe feed</span><h2 class="portal-card-title">Hoạt động gần đây</h2><p class="portal-card-subtitle">Chỉ hiển thị nhãn thao tác đã sanitize, không lộ nội dung ghi chú hoặc request detail.</p></div></div>${eventList}</section></article>`;
  }

  // Prompt Library is intentionally a reusable recipe inventory rather than
  // a Bot prompt seed, a temporary workspace draft or a Project-bound Studio
  // Document. Every card below is rendered from an owner-scoped Web API
  // projection, with text escaped before it reaches the DOM.
  const PROMPT_LIBRARY_STATES = Object.freeze(["active", "archived"]);

  function validPromptTemplateId(value) {
    return validProjectId(value);
  }

  function promptTemplateItems(context) {
    return (Array.isArray(context && context.promptTemplates) ? context.promptTemplates : [])
      .filter((item) => item && typeof item === "object" && validPromptTemplateId(item.id))
      .slice(0, 100);
  }

  function promptTemplateState(value) {
    const state = String(value || "").toLowerCase();
    return state === "active" ? "ready" : state === "archived" ? "read_only" : "guarded";
  }

  function promptTemplateStateLabel(value) {
    return String(value || "").toLowerCase() === "archived" ? "Đã archive" : "Đang hoạt động";
  }

  function promptTemplateTags(value) {
    return Array.isArray(value) ? value.filter((tag) => typeof tag === "string" && tag.trim()).slice(0, 16) : [];
  }

  function promptTemplateVariables(value) {
    return Array.isArray(value) ? value.filter((name) => typeof name === "string" && name.trim()).slice(0, 24) : [];
  }

  function renderPromptTemplateTags(value) {
    const tags = promptTemplateTags(value);
    return tags.length ? `<div class="portal-prompt-library-tags">${tags.map((tag) => `<span>${safeText(tag)}</span>`).join("")}</div>` : "";
  }

  function promptLibraryFilterState(context) {
    const source = context && context.promptLibraryFilter && typeof context.promptLibraryFilter === "object" ? context.promptLibraryFilter : {};
    const clean = (value, maximum) => typeof value === "string" ? value.replace(/\s+/g, " ").trim().slice(0, maximum) : "";
    const state = String(source.state || "all").toLowerCase();
    return {
      q: clean(source.q, 100), category: clean(source.category, 100), platform: clean(source.platform, 100),
      product_context: clean(source.product_context, 100), tag: clean(source.tag, 48),
      state: ["all", ...PROMPT_LIBRARY_STATES].includes(state) ? state : "all"
    };
  }

  function promptTemplateFormFields() {
    return [
      { name: "title", label: "Tên template", placeholder: "Ví dụ: Hook video sản phẩm 3 giây", required: true, minLength: 3, maxLength: 180 },
      { name: "prompt_text", label: "Prompt", control: "textarea", placeholder: "Dùng {{product}}, {{benefit}} cho biến có thể thay thế…", required: true, minLength: 1, maxLength: 16000, help: "Đây là recipe authoring. Lưu template không chạy AI, không tạo job hoặc charge." },
      { name: "negative_prompt", label: "Negative prompt", control: "textarea", placeholder: "Điều cần tránh (tùy chọn)", maxLength: 8000 },
      { name: "category", label: "Danh mục", placeholder: "Ví dụ: Video product", required: true, maxLength: 100 },
      { name: "product_context", label: "Ngữ cảnh", placeholder: "Ví dụ: video, image, content", required: true, maxLength: 100 },
      { name: "platform", label: "Nền tảng", placeholder: "Ví dụ: TikTok", required: true, maxLength: 100 },
      { name: "style", label: "Phong cách", placeholder: "Ví dụ: rõ ràng, giàu nhịp điệu", maxLength: 100 },
      { name: "language", label: "Ngôn ngữ", placeholder: "Ví dụ: vi", required: true, maxLength: 100 },
      { name: "variables", label: "Variables", placeholder: "product, benefit", maxLength: 1560, help: "Tên biến ngắn, phân tách bằng dấu phẩy. Chỉ variable khai báo mới được preview thay thế." },
      { name: "tags", label: "Tags", placeholder: "launch, tiktok, hook", maxLength: 800, help: "Tối đa 16 tags, phân tách bằng dấu phẩy." },
      { name: "source", label: "Nguồn", placeholder: "Ví dụ: Tự soạn trong TOAN AAS Web", required: true, minLength: 2, maxLength: 600 },
      { name: "license_note", label: "Quyền sử dụng", placeholder: "Ví dụ: Tôi có quyền sử dụng nội dung này.", required: true, minLength: 2, maxLength: 600 },
      { name: "quality_score", label: "Mức hoàn thiện tự đánh giá", type: "number", min: 0, max: 100, step: 1, required: true, help: "Điểm tự mô tả của bạn, không phải điểm đánh giá AI hoặc provider." }
    ];
  }

  function promptLibraryFilterFields() {
    return [
      { name: "q", label: "Tìm template", placeholder: "Tên, metadata, tag hoặc prompt…", maxLength: 100, wide: true },
      { name: "category", label: "Danh mục", placeholder: "Ví dụ: Video", maxLength: 100 },
      { name: "platform", label: "Nền tảng", placeholder: "Ví dụ: TikTok", maxLength: 100 },
      { name: "product_context", label: "Ngữ cảnh", placeholder: "Ví dụ: video", maxLength: 100 },
      { name: "tag", label: "Tag", placeholder: "Ví dụ: launch", maxLength: 48 },
      { name: "state", label: "Trạng thái", control: "select", options: [["all", "Tất cả"], ["active", "Đang hoạt động"], ["archived", "Đã archive"]] }
    ];
  }

  function promptTemplateValues(value) {
    const source = value && typeof value === "object" ? value : {};
    return {
      title: String(source.title || ""), category: String(source.category || "General"), product_context: String(source.product_context || "general"),
      platform: String(source.platform || "general"), style: String(source.style || ""), language: String(source.language || "vi"),
      prompt_text: String(source.prompt_text || ""), negative_prompt: String(source.negative_prompt || ""),
      variables: promptTemplateVariables(source.variables).join(", "), tags: promptTemplateTags(source.tags).join(", "),
      source: String(source.source || "Tự soạn"), license_note: String(source.license_note || "Tôi có quyền sử dụng nội dung này."),
      quality_score: Number.isFinite(Number(source.quality_score)) ? String(Math.max(0, Math.min(100, Math.round(Number(source.quality_score))))) : "50"
    };
  }

  function promptLibraryEventLabel(value) {
    return ({
      template_created: "Đã tạo template", template_updated: "Đã lưu phiên bản mới", template_archived: "Đã archive template",
      template_restored: "Đã khôi phục template", template_version_restored: "Đã khôi phục phiên bản", template_duplicated: "Đã nhân bản template",
      template_imported: "Đã import template"
    })[String(value || "")] || "Đã cập nhật Prompt Library";
  }

  function renderPromptLibraryCards(items) {
    if (!items.length) return renderEmpty("Chưa có template", "Lưu recipe đầu tiên để tái sử dụng prompt, metadata và variables trong Web Workspace riêng tư.", "◇");
    return `<div class="portal-prompt-library-grid">${items.map((item) => {
      const id = String(item.id || "");
      const quality = Math.max(0, Math.min(100, Number(item.quality_score || 0) || 0));
      return `<article class="portal-card portal-card-pad portal-prompt-library-card"><div class="portal-card-header"><div><span class="portal-section-kicker">${safeText(String(item.product_context || "general"))} · ${safeText(String(item.platform || "general"))}</span><h3 class="portal-card-title">${safeText(String(item.title || "Template"))}</h3><p class="portal-card-subtitle">${safeText(String(item.excerpt || "Chưa có prompt hiển thị."))}</p></div>${badge(promptTemplateState(item.state))}</div><div class="portal-prompt-library-meta"><span>${safeText(String(item.category || "Chưa phân loại"))}</span><span>${safeText(String(item.language || "vi"))}</span><span>v${safeText(String(item.revision || 1))}</span><span>${safeText(String(quality))}/100</span></div>${renderPromptTemplateTags(item.tags)}<div class="portal-form-footer"><span class="portal-form-note">${safeText(promptTemplateStateLabel(item.state))} · cập nhật ${safeText(String(item.updated_at || item.created_at || "—"))}</span><a class="portal-button portal-button--quiet" href="/prompt-library/${encodeURIComponent(id)}">Mở template <span aria-hidden="true">→</span></a></div></article>`;
    }).join("")}</div>`;
  }

  function renderPromptLibrary(page, context) {
    const canView = Boolean(context.capabilities && context.capabilities["prompt-library-view"] === true);
    const canCreate = Boolean(context.capabilities && context.capabilities["prompt-library-create"] === true);
    const canImport = Boolean(context.capabilities && context.capabilities["prompt-library-import"] === true);
    const canExport = Boolean(context.capabilities && context.capabilities["prompt-library-export"] === true);
    const templates = promptTemplateItems(context);
    const summary = context.promptLibrarySummary && typeof context.promptLibrarySummary === "object" ? context.promptLibrarySummary : {};
    const counts = summary.templates && typeof summary.templates === "object" ? summary.templates : {};
    const filter = promptLibraryFilterState(context);
    const route = page.routePath || page.path;
    const values = promptTemplateValues({ ...transientFormValues(route), quality_score: transientFormValues(route).quality_score || "50" });
    if (!canView) return `<article class="portal-page portal-prompt-library">${renderHero(page, context)}<section class="portal-card portal-card-pad">${renderEmpty("Prompt Library đang được bảo vệ", "Đăng nhập bằng signed session để xem template riêng tư. Web không nhận Telegram ID thô hoặc mở kho seed global của Bot.", "⌁")}</section></article>`;
    const filterForm = `<form class="portal-prompt-library-filter" data-portal-form data-portal-action="prompt-library-filter" data-portal-route="/prompt-library" novalidate>${renderFields(promptLibraryFilterFields(), true, context, filter)}<div class="portal-form-footer"><span class="portal-form-note">Bộ lọc chỉ tồn tại trong trang đang mở và đi qua API owner-scoped; không lưu vào URL, localStorage hoặc Telegram.</span><div class="portal-inline-actions"><button class="portal-button portal-button--quiet" type="button" data-portal-action="prompt-library-filter-clear" data-portal-route="/prompt-library">Xóa lọc</button><button class="portal-button portal-button--primary" type="submit">Tìm kiếm</button></div></div></form>`;
    const events = Array.isArray(context.promptLibraryEvents) ? context.promptLibraryEvents.slice(0, 8) : [];
    const eventList = events.length ? `<div class="portal-prompt-library-events">${events.map((item) => `<div><span aria-hidden="true">•</span><span><strong>${safeText(promptLibraryEventLabel(item.action))}</strong><small>v${safeText(String(item.revision || 1))} · ${safeText(String(item.created_at || "—"))}</small></span></div>`).join("")}</div>` : renderEmpty("Chưa có hoạt động", "Timeline chỉ chứa nhãn audit-safe; không hiển thị prompt, license note hoặc request detail.", "○");
    return `<article class="portal-page portal-prompt-library">${renderHero(page, context)}
      <section class="portal-prompt-library-intro"><div><span class="portal-section-kicker">Private Web template vault</span><h2>Prompt tốt là tài sản có thể tiếp tục, không phải đoạn text bị thất lạc</h2><p>Lưu recipe có bối cảnh, biến, quyền sử dụng và lịch sử phiên bản rõ ràng. Prompt Library độc lập với Bot, provider, job, Xu và PayOS.</p></div><dl><div><dt>${safeText(String(Number(counts.active || 0)))}</dt><dd>Đang hoạt động</dd></div><div><dt>${safeText(String(Number(counts.with_variables || 0)))}</dt><dd>Có variables</dd></div><div><dt>${safeText(String(Number(counts.archived || 0)))}</dt><dd>Đã archive</dd></div></dl></section>
      <div class="portal-prompt-library-layout"><section class="portal-card portal-card-pad portal-prompt-library-create"><div class="portal-card-header"><div><h2 class="portal-card-title">Tạo template mới</h2><p class="portal-card-subtitle">Một template là recipe reusable. Hãy mô tả nguồn và quyền sử dụng, không lưu credential hay chứng từ thanh toán.</p></div>${badge(canCreate ? "ready" : "guarded")}</div><form class="portal-form" data-portal-form data-portal-action="prompt-template-create" data-portal-route="${safeText(route)}" novalidate>${renderFields(promptTemplateFormFields(), canCreate, context, values)}<div class="portal-form-footer"><span class="portal-form-note">Lưu version 1 với CSRF, idempotency và owner check. Không tạo engine request hoặc output.</span><button class="portal-button portal-button--primary" type="submit"${canCreate ? "" : " disabled"}>Lưu template</button></div></form></section><aside class="portal-card portal-card-pad portal-prompt-library-boundary"><div class="portal-card-header"><div><span class="portal-section-kicker">Ranh giới rõ ràng</span><h2 class="portal-card-title">Sử dụng có kiểm soát</h2><p class="portal-card-subtitle">Kho này là không gian authoring riêng tư, không phải catalog seed chung hoặc provider console.</p></div></div><ol class="portal-project-steps"><li><strong>1. Recipe có ngữ cảnh</strong><span>Ghi danh mục, nền tảng, phong cách, ngôn ngữ và variable.</span></li><li><strong>2. Version không ghi đè</strong><span>Mỗi lần lưu hoặc khôi phục tạo revision mới để so sánh rõ ràng.</span></li><li><strong>3. Preview trung thực</strong><span>Chỉ thay {{variable}} tại chỗ; không chạy AI hay phát sinh charge.</span></li></ol><div class="portal-form-footer"><a class="portal-button portal-button--quiet" href="/prompt-studio">Mở Prompt Studio</a><button class="portal-button portal-button--quiet" type="button" data-portal-action="prompt-library-export" data-portal-route="${safeText(route)}"${canExport ? "" : " disabled"}>Xuất JSON riêng tư</button></div></aside></div>
      <section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Tìm và tiếp tục template</h2><p class="portal-card-subtitle">Danh sách chỉ chứa metadata/excerpt thuộc signed account hiện tại. Nội dung đầy đủ chỉ nạp khi mở template.</p></div><button class="portal-button portal-button--quiet" type="button" data-portal-action="prompt-library-refresh" data-portal-route="/prompt-library">Làm mới</button></div>${filterForm}${renderPromptLibraryCards(templates)}</section>
      <details class="portal-prompt-library-import"><summary>Import JSON an toàn</summary><p>Chỉ dán JSON object có trường <code>templates</code> hoặc một mảng template. Không nhận file path, URL, scrape hoặc seed global của Bot; import tối đa 50 template mỗi lần.</p><form class="portal-form" data-portal-form data-portal-action="prompt-library-import" data-portal-route="/prompt-library" data-portal-confirm="Import các template JSON vào Prompt Library riêng tư? Dữ liệu sẽ được kiểm tra schema, secret và quyền sử dụng trước khi lưu." novalidate><label class="portal-field"><span>JSON template</span><textarea class="portal-textarea" name="templates_json" required minlength="2" maxlength="1400000" placeholder='{"templates":[{"title":"…","prompt_text":"…"}]}'${canImport ? "" : " disabled"}></textarea><small>Tối đa 1.400.000 ký tự mỗi batch; không bao gồm account ID, đường dẫn file, token, API key, khóa riêng, OTP/CVV, số thẻ hoặc chứng từ thanh toán.</small></label><div class="portal-form-footer"><span class="portal-form-note">Import append-only, idempotent và không fetch URL ngoài.</span><button class="portal-button portal-button--primary" type="submit"${canImport ? "" : " disabled"}>Kiểm tra & import</button></div></form></details>
      <section class="portal-card portal-card-pad"><div class="portal-card-header"><div><span class="portal-section-kicker">Audit-safe feed</span><h2 class="portal-card-title">Hoạt động gần đây</h2><p class="portal-card-subtitle">Chỉ nhãn thao tác và revision; không lộ prompt, variable value, license note hoặc request detail.</p></div></div>${eventList}</section>
    </article>`;
  }

  function renderPromptLibraryDetail(page, context) {
    const detail = context.promptTemplateDetail && typeof context.promptTemplateDetail === "object" ? context.promptTemplateDetail : {};
    const template = detail.template && typeof detail.template === "object" && validPromptTemplateId(detail.template.id) && String(detail.template.id) === String(page.recordId || "") ? detail.template : null;
    const canView = Boolean(context.capabilities && context.capabilities["prompt-library-view"] === true);
    if (!canView || !template) return `<article class="portal-page portal-prompt-library-detail">${renderHero(page, context)}<section class="portal-card portal-card-pad">${renderEmpty("Không tìm thấy template", "Template có thể không thuộc Web account hiện tại, đã bị gỡ hoặc dữ liệu riêng tư chưa được server xác minh.", "◇")}<div class="portal-form-footer"><a class="portal-button portal-button--primary" href="/prompt-library">Về Prompt Library</a></div></section></article>`;
    const state = String(template.state || "active");
    const canUpdate = Boolean(context.capabilities && context.capabilities["prompt-library-update"] === true && state === "active");
    const canArchive = Boolean(context.capabilities && context.capabilities["prompt-library-archive"] === true && state === "active");
    const canRestore = Boolean(context.capabilities && context.capabilities["prompt-library-restore"] === true && state === "archived");
    const canPurge = Boolean(context.capabilities && context.capabilities["prompt-library-purge"] === true && state === "archived");
    const canDuplicate = Boolean(context.capabilities && context.capabilities["prompt-library-duplicate"] === true && state === "active");
    const canPreview = Boolean(context.capabilities && context.capabilities["prompt-library-preview"] === true && state === "active");
    const canCopy = state === "active";
    const route = page.routePath || page.path;
    const values = promptTemplateValues(template);
    const versions = Array.isArray(detail.versions) ? detail.versions.filter((item) => item && Number.isInteger(Number(item.revision))).slice(0, 100) : [];
    const variables = promptTemplateVariables(template.variables);
    const stateAction = state === "active"
      ? `<button class="portal-button portal-button--quiet" type="button" data-portal-action="prompt-template-archive" data-portal-route="${safeText(route)}" data-prompt-template-id="${safeText(String(template.id))}" data-prompt-template-revision="${safeText(String(template.revision))}" data-portal-confirm="Archive template này? Nội dung và version history vẫn được giữ riêng tư, nhưng template không thể chỉnh sửa cho đến khi được khôi phục."${canArchive ? "" : " disabled"}>Archive</button>`
      : `<button class="portal-button portal-button--primary" type="button" data-portal-action="prompt-template-restore" data-portal-route="${safeText(route)}" data-prompt-template-id="${safeText(String(template.id))}" data-prompt-template-revision="${safeText(String(template.revision))}"${canRestore ? "" : " disabled"}>Khôi phục template</button><button class="portal-button portal-button--quiet" type="button" data-portal-action="prompt-template-purge" data-portal-route="${safeText(route)}" data-prompt-template-id="${safeText(String(template.id))}" data-prompt-template-revision="${safeText(String(template.revision))}" data-portal-confirm="Xóa vĩnh viễn template đã archive cùng toàn bộ version history? Thao tác này không thể hoàn tác."${canPurge ? "" : " disabled"}>Xóa vĩnh viễn</button>`;
    const versionList = versions.length ? `<div class="portal-version-list">${versions.map((version) => `<div class="portal-version-row"><span><strong>v${safeText(String(version.revision))}</strong><small>${safeText(String(version.title || "Template"))} · ${safeText(String(version.created_at || "—"))} · ${safeText(promptTemplateStateLabel(version.state))}</small></span>${Number(version.revision) === Number(template.revision) ? `<span class="portal-form-note">Đang mở</span>` : `<button class="portal-button portal-button--quiet" type="button" data-portal-action="prompt-template-restore-version" data-portal-route="${safeText(route)}" data-prompt-template-id="${safeText(String(template.id))}" data-prompt-template-revision="${safeText(String(template.revision))}" data-prompt-template-version="${safeText(String(version.revision))}" data-portal-confirm="Khôi phục v${safeText(String(version.revision))} thành một revision mới? Phiên bản hiện tại vẫn được giữ trong history."${canUpdate ? "" : " disabled"}>Khôi phục</button>`}</div>`).join("")}</div>` : renderEmpty("Chưa có version history", "Version đầu tiên được lưu khi template được tạo và không bị ghi đè âm thầm.", "○");
    const preview = context.promptTemplatePreview && typeof context.promptTemplatePreview === "object" ? context.promptTemplatePreview : {};
    const previewForTemplate = String(preview.template_id || "") === String(template.id) ? preview : {};
    const variableFields = variables.length ? variables.map((name) => `<label class="portal-field"><span>${safeText(name)}</span><input class="portal-input" name="variable_${safeText(name)}" maxlength="600" placeholder="Giá trị preview cho ${safeText(name)}"${canPreview ? "" : " disabled"}></label>`).join("") : `<p class="portal-form-note">Template chưa khai báo variable. Preview sẽ giữ nguyên nội dung.</p>`;
    const previewResult = previewForTemplate && typeof previewForTemplate.prompt_text === "string" ? `<section class="portal-prompt-library-preview-result"><div><span class="portal-section-kicker">Preview only</span><h3>Prompt sau khi thay variable</h3><p>Đây là render cục bộ, không phải AI output hoặc request engine.</p></div><pre>${safeText(previewForTemplate.prompt_text)}</pre>${previewForTemplate.negative_prompt ? `<h4>Negative prompt</h4><pre>${safeText(previewForTemplate.negative_prompt)}</pre>` : ""}</section>` : "";
    return `<article class="portal-page portal-prompt-library-detail">${renderHero(page, context)}
      <section class="portal-prompt-library-detail-summary"><div><span class="portal-section-kicker">${safeText(String(template.product_context || "general"))} · ${safeText(String(template.platform || "general"))}</span><h2>${safeText(String(template.title || "Template"))}</h2><p>${safeText(String(template.category || "Chưa phân loại"))} · ${safeText(String(template.style || "Chưa đặt phong cách"))} · ${safeText(String(template.language || "vi"))}</p>${renderPromptTemplateTags(template.tags)}</div><dl><div><dt>Revision</dt><dd>v${safeText(String(template.revision || 1))}</dd></div><div><dt>Tự đánh giá</dt><dd>${safeText(String(template.quality_score || 0))}/100</dd></div><div><dt>Trạng thái</dt><dd>${badge(promptTemplateState(template.state))}</dd></div></dl></section>
      <div class="portal-prompt-library-detail-grid"><section class="portal-card portal-card-pad portal-prompt-library-editor"><div class="portal-card-header"><div><h2 class="portal-card-title">Template editor</h2><p class="portal-card-subtitle">Mỗi lần lưu tạo revision mới. Server kiểm tra owner, CSRF, idempotency và optimistic revision trước khi ghi.</p></div>${badge(promptTemplateState(template.state))}</div><form class="portal-form" data-portal-form data-portal-action="prompt-template-update" data-portal-route="${safeText(route)}" data-prompt-template-id="${safeText(String(template.id))}" data-prompt-template-revision="${safeText(String(template.revision))}" novalidate>${renderFields(promptTemplateFormFields(), canUpdate, context, values)}<div class="portal-form-footer"><span class="portal-form-note">Không có provider/engine call, job, Xu hoặc payment trong thao tác lưu template.</span><div class="portal-inline-actions">${stateAction}<button class="portal-button portal-button--quiet" type="button" data-portal-action="prompt-template-duplicate" data-portal-route="${safeText(route)}" data-prompt-template-id="${safeText(String(template.id))}" data-prompt-template-revision="${safeText(String(template.revision))}"${canDuplicate ? "" : " disabled"}>Nhân bản</button><button class="portal-button portal-button--primary" type="submit"${canUpdate ? "" : " disabled"}>Lưu revision mới</button></div></div></form><div class="portal-form-footer"><button class="portal-button portal-button--quiet" type="button" data-portal-action="prompt-template-copy" data-portal-route="${safeText(route)}" data-prompt-template-id="${safeText(String(template.id))}"${canCopy ? "" : " disabled"}>Sao chép prompt</button><a class="portal-button portal-button--quiet" href="/prompt-studio">Mở Prompt Studio</a></div></section>
        <aside class="portal-card portal-card-pad portal-prompt-library-preview"><div class="portal-card-header"><div><span class="portal-section-kicker">Local preview</span><h2 class="portal-card-title">Thử variable an toàn</h2><p class="portal-card-subtitle">Chỉ variable đã khai báo mới được thay. Nội dung preview không được lưu tự động hoặc gửi tới engine.</p></div>${badge(canPreview ? "read_only" : "guarded")}</div><form class="portal-form" data-portal-form data-portal-action="prompt-template-preview" data-portal-route="${safeText(route)}" data-prompt-template-id="${safeText(String(template.id))}" data-prompt-template-revision="${safeText(String(template.revision))}" novalidate><div class="portal-fields">${variableFields}</div><div class="portal-form-footer"><span class="portal-form-note">Preview local-only · không tạo AI output.</span><button class="portal-button portal-button--primary" type="submit"${canPreview ? "" : " disabled"}>Tạo preview</button></div></form>${previewResult}</aside></div>
      <section class="portal-card portal-card-pad"><div class="portal-card-header"><div><span class="portal-section-kicker">Version history</span><h2 class="portal-card-title">Lịch sử phiên bản</h2><p class="portal-card-subtitle">Khôi phục luôn tạo revision mới. Dữ liệu phiên bản chỉ nạp sau owner check và không được cache PWA.</p></div></div>${versionList}</section>
      <section class="portal-card portal-card-pad portal-prompt-library-provenance"><div class="portal-card-header"><div><span class="portal-section-kicker">Provenance</span><h2 class="portal-card-title">Nguồn & quyền sử dụng</h2><p class="portal-card-subtitle">Thông tin này do bạn khai báo để quản lý template của chính mình; Web không tự chứng nhận bản quyền hoặc provenance ngoài hệ thống.</p></div></div><dl><div><dt>Nguồn</dt><dd>${safeText(String(template.source || "—"))}</dd></div><div><dt>Quyền sử dụng</dt><dd>${safeText(String(template.license_note || "—"))}</dd></div></dl>${renderNotes(page)}</section>
    </article>`;
  }

  // Audio Library & Briefing is intentionally an authoring workspace, not a
  // music-generator skin.  It only renders redacted, owner-scoped Asset Vault
  // references and local creative text; there is no audio player, waveform,
  // provider preview, raw URL, Telegram file ID, job or delivery simulation.
  const MEDIA_PROMPT_MODES = Object.freeze([
    ["background", "Nhạc nền"], ["lyrics", "Bài hát có lời nguyên gốc"], ["script", "Hướng lời / kịch bản nhạc"],
    ["melody", "Hướng giai điệu nguyên gốc"], ["custom", "Brief tùy chỉnh"]
  ]);
  const MEDIA_ITEM_ROLES = Object.freeze([["music", "Music"], ["sfx", "SFX"], ["reference", "Reference"]]);

  function validMediaCollectionId(value) {
    return validProjectId(value);
  }

  function mediaCollectionState(value) {
    const state = String(value || "").toLowerCase();
    return state === "active" ? "ready" : state === "archived" ? "read_only" : "guarded";
  }

  function mediaCollectionStateLabel(value) {
    return String(value || "").toLowerCase() === "archived" ? "Đã archive" : "Đang hoạt động";
  }

  function mediaCollectionTags(value) {
    return Array.isArray(value) ? value.filter((item) => typeof item === "string" && item.trim()).slice(0, 16) : [];
  }

  function renderMediaTags(value) {
    const tags = mediaCollectionTags(value);
    return tags.length ? `<div class="portal-media-tags">${tags.map((tag) => `<span>${safeText(tag)}</span>`).join("")}</div>` : "";
  }

  function mediaModeLabel(value) {
    const match = MEDIA_PROMPT_MODES.find(([key]) => key === String(value || "").toLowerCase());
    return match ? match[1] : "Brief âm thanh";
  }

  function mediaRoleLabel(value) {
    const match = MEDIA_ITEM_ROLES.find(([key]) => key === String(value || "").toLowerCase());
    return match ? match[1] : "Reference";
  }

  function mediaWorkspaceFilterState(context) {
    const source = context && context.mediaWorkspaceFilter && typeof context.mediaWorkspaceFilter === "object" ? context.mediaWorkspaceFilter : {};
    const tidy = (value, maximum) => typeof value === "string" ? value.replace(/\s+/g, " ").trim().slice(0, maximum) : "";
    const mode = String(source.prompt_mode || "").trim().toLowerCase();
    const state = String(source.state || "all").trim().toLowerCase();
    return {
      q: tidy(source.q, 100), tag: tidy(source.tag, 48),
      prompt_mode: MEDIA_PROMPT_MODES.some(([key]) => key === mode) ? mode : "",
      state: ["all", "active", "archived"].includes(state) ? state : "all"
    };
  }

  function mediaCollectionFormFields() {
    return [
      { name: "title", label: "Tên collection", placeholder: "Ví dụ: Âm thanh launch mùa hè", required: true, minLength: 3, maxLength: 180 },
      { name: "creative_brief", label: "Music / SFX brief", control: "textarea", placeholder: "Mood, tempo, nhạc cụ, cảm xúc, thời lượng mục tiêu và ngữ cảnh cảnh quay…", maxLength: 6000, help: "Mô tả thuộc Web Workspace. Không nêu yêu cầu mô phỏng nghệ sĩ, bài hát, melody hoặc giọng cụ thể." },
      { name: "description", label: "Mô tả nội bộ", control: "textarea", placeholder: "Mục đích, bối cảnh hoặc ghi chú team…", maxLength: 6000, help: "Không lưu secret, token, OTP/CVV, số thẻ hoặc chứng từ thanh toán." },
      { name: "prompt_mode", label: "Loại brief", control: "select", required: true, options: MEDIA_PROMPT_MODES },
      { name: "use_context", label: "Ngữ cảnh sử dụng", placeholder: "Ví dụ: video giới thiệu sản phẩm 15 giây", required: true, maxLength: 160 },
      { name: "tags", label: "Tags", placeholder: "launch, upbeat, short-form", maxLength: 800, help: "Tối đa 16 tags, phân tách bằng dấu phẩy." },
      { name: "project_id", label: "Liên kết planning với Project", control: "select", optionsFrom: "projects", emptyLabel: "Không liên kết Project", help: "Chỉ là liên kết planning Web-owned, không tự đưa audio vào package, job hoặc delivery." },
      { name: "rights_note", label: "Quyền sử dụng", placeholder: "Ví dụ: Tôi có quyền sử dụng các tệp và brief này.", required: true, minLength: 2, maxLength: 800, help: "Web không tự chứng nhận bản quyền, license hoặc quyền thương mại của bạn." }
    ];
  }

  function mediaAttachFields(context) {
    const assets = (Array.isArray(context.mediaAudioAssets) ? context.mediaAudioAssets : [])
      .filter((asset) => asset && validVaultAssetId(asset.id) && asset.download_available === true)
      .slice(0, 100)
      .map((asset) => ({ value: String(asset.id), label: `${asset.display_name || asset.original_filename || "Audio Asset Vault"} · ${String(asset.extension || "").replace(".", "").toUpperCase()} · ${vaultBytes(asset.byte_size)}` }));
    return [
      { name: "asset_id", label: "Audio từ Asset Vault", control: "select", required: true, options: assets, emptyLabel: assets.length ? "Chọn audio private" : "Chưa có audio Asset Vault active", help: "Chỉ audio active thuộc account hiện tại. Không nhận URL, provider preview hoặc Telegram file ID." },
      { name: "role", label: "Vai trò", control: "select", required: true, options: MEDIA_ITEM_ROLES },
      { name: "title_override", label: "Tên hiển thị (tùy chọn)", placeholder: "Ví dụ: Bed nhịp nhẹ", maxLength: 180 },
      { name: "attribution", label: "Attribution (tùy chọn)", placeholder: "Ví dụ: Tên tác giả / nguồn đã kiểm tra", maxLength: 500 },
      { name: "license_note", label: "Ghi chú license", placeholder: "Tôi chịu trách nhiệm kiểm tra license trước khi đăng.", required: true, minLength: 2, maxLength: 800 },
      { name: "tags", label: "Tags audio", placeholder: "hook, ambient", maxLength: 800 },
      { name: "user_declared_duration_seconds", label: "Thời lượng tự khai báo (giây)", type: "number", min: 1, max: 7200, step: 1, inputMode: "numeric", help: "Không được parse từ file và không phải duration/preview do provider xác nhận." }
    ];
  }

  function mediaCollectionValues(value) {
    const source = value && typeof value === "object" ? value : {};
    return {
      title: String(source.title || ""), description: String(source.description || ""), creative_brief: String(source.creative_brief || ""),
      prompt_mode: MEDIA_PROMPT_MODES.some(([key]) => key === String(source.prompt_mode || "")) ? String(source.prompt_mode) : "background",
      use_context: String(source.use_context || "general"), tags: mediaCollectionTags(source.tags).join(", "),
      project_id: String(source.project_id || ""), rights_note: String(source.rights_note || "Tôi xác nhận có quyền sử dụng các tệp và brief trong collection này.")
    };
  }

  function mediaEventLabel(value) {
    return ({
      collection_created: "Đã tạo collection", collection_updated: "Đã lưu revision mới", collection_archived: "Đã archive collection",
      collection_archived_without_snapshot: "Đã archive khi history đạt giới hạn", collection_restored: "Đã khôi phục collection",
      collection_restored_without_snapshot: "Đã khôi phục khi history đạt giới hạn", collection_duplicated: "Đã nhân bản collection",
      collection_version_restored: "Đã khôi phục revision metadata", item_attached: "Đã gắn audio Asset Vault",
      item_updated: "Đã cập nhật metadata audio", item_detached: "Đã gỡ audio reference"
    })[String(value || "")] || "Đã cập nhật Audio Library";
  }

  function mediaCollectionItems(context) {
    return (Array.isArray(context.mediaCollections) ? context.mediaCollections : [])
      .filter((item) => item && typeof item === "object" && validMediaCollectionId(item.id)).slice(0, 100);
  }

  function renderMediaCollectionCards(items) {
    if (!items.length) return renderEmpty("Chưa có audio collection", "Tạo collection đầu tiên để tổ chức brief, quyền sử dụng và các audio private đã có trong Asset Vault.", ICONS.music);
    return `<div class="portal-media-collection-grid">${items.map((item) => {
      const id = String(item.id || "");
      const policy = item.policy && typeof item.policy === "object" ? item.policy : {};
      const policyBadge = policy.status === "guarded" ? `<span class="portal-media-policy-flag">Brief cần chỉnh policy</span>` : "";
      return `<article class="portal-card portal-card-pad portal-media-collection-card"><div class="portal-card-header"><div><span class="portal-section-kicker">${safeText(mediaModeLabel(item.prompt_mode))} · ${safeText(String(item.use_context || "general"))}</span><h3 class="portal-card-title">${safeText(String(item.title || "Audio Collection"))}</h3><p class="portal-card-subtitle">${safeText(String(item.brief_excerpt || item.description_excerpt || "Chưa có brief hiển thị."))}</p></div>${badge(mediaCollectionState(item.state))}</div><div class="portal-media-card-meta"><span>v${safeText(String(item.revision || 1))}</span><span>${safeText(mediaCollectionStateLabel(item.state))}</span><span>${safeText(String(item.updated_at || item.created_at || "—"))}</span></div>${policyBadge}${renderMediaTags(item.tags)}<div class="portal-form-footer"><span class="portal-form-note">Authoring-only · không có job, charge hoặc output.</span><a class="portal-button portal-button--quiet" href="/media-workspace/${encodeURIComponent(id)}">Mở collection <span aria-hidden="true">→</span></a></div></article>`;
    }).join("")}</div>`;
  }

  function renderMediaPolicy(context) {
    const policy = context.mediaWorkspacePolicy && typeof context.mediaWorkspacePolicy === "object" ? context.mediaWorkspacePolicy : {};
    const statements = Array.isArray(policy.policy) ? policy.policy.filter((item) => typeof item === "string" && item.trim()).slice(0, 6) : [];
    const guarded = Array.isArray(policy.guarded_capabilities) ? policy.guarded_capabilities.filter((item) => typeof item === "string" && item.trim()).slice(0, 8) : [];
    return `<aside class="portal-card portal-card-pad portal-media-policy"><div class="portal-card-header"><div><span class="portal-section-kicker">Ranh giới an toàn</span><h2 class="portal-card-title">Authoring sẵn sàng, engine vẫn được bảo vệ</h2><p class="portal-card-subtitle">Không có music generation, provider library, enhance, translate, mux/render, job, Xu hay payment trong workspace này.</p></div>${badge("guarded")}</div><ol class="portal-project-steps">${statements.length ? statements.map((item, index) => `<li><strong>${index + 1}.</strong><span>${safeText(item)}</span></li>`).join("") : "<li><strong>1.</strong><span>Chính sách đang được nạp an toàn từ server.</span></li>"}</ol>${guarded.length ? `<div class="portal-media-guarded-list"><span>Đang guarded</span>${guarded.map((item) => `<em>${safeText(String(item).replace(/_/g, " "))}</em>`).join("")}</div>` : ""}<div class="portal-form-footer"><a class="portal-button portal-button--quiet" href="/asset-vault">Mở Asset Vault</a><a class="portal-button portal-button--quiet" href="/projects">Mở Project Center</a></div></aside>`;
  }

  function renderMediaWorkspace(page, context) {
    const canView = Boolean(context.capabilities && context.capabilities["media-workspace-view"] === true);
    const canCreate = Boolean(context.capabilities && context.capabilities["media-workspace-create"] === true);
    if (!canView) return `<article class="portal-page portal-media-workspace">${renderHero(page, context)}<section class="portal-card portal-card-pad">${renderEmpty("Audio Library đang được bảo vệ", "Đăng nhập bằng signed session để mở workspace audio riêng tư. Web không nhận Telegram ID thô và không hiển thị data music của Bot.", ICONS.music)}</section></article>`;
    const summary = context.mediaWorkspaceSummary && typeof context.mediaWorkspaceSummary === "object" ? context.mediaWorkspaceSummary : {};
    const collections = summary.collections && typeof summary.collections === "object" ? summary.collections : {};
    const items = summary.items && typeof summary.items === "object" ? summary.items : {};
    const execution = summary.execution && typeof summary.execution === "object" ? summary.execution : {};
    const filter = mediaWorkspaceFilterState(context);
    const values = mediaCollectionValues({ ...transientFormValues(page.routePath || page.path), prompt_mode: transientFormValues(page.routePath || page.path).prompt_mode || "background" });
    const filterFields = [
      { name: "q", label: "Tìm collection", placeholder: "Tên, brief hoặc mô tả…", maxLength: 100, wide: true },
      { name: "tag", label: "Tag", placeholder: "Ví dụ: launch", maxLength: 48 },
      { name: "prompt_mode", label: "Loại brief", control: "select", options: MEDIA_PROMPT_MODES, emptyLabel: "Tất cả loại" },
      { name: "state", label: "Trạng thái", control: "select", options: [["all", "Tất cả"], ["active", "Đang hoạt động"], ["archived", "Đã archive"]] }
    ];
    const events = Array.isArray(context.mediaWorkspaceEvents) ? context.mediaWorkspaceEvents.slice(0, 8) : [];
    const eventList = events.length ? `<div class="portal-media-events">${events.map((item) => `<div><span aria-hidden="true">•</span><span><strong>${safeText(mediaEventLabel(item.action))}</strong><small>v${safeText(String(item.revision || 1))} · ${safeText(String(item.created_at || "—"))}</small></span></div>`).join("")}</div>` : renderEmpty("Chưa có hoạt động", "Timeline chỉ lưu nhãn thao tác và revision; không hiển thị brief, attribution hoặc license note.", "○");
    return `<article class="portal-page portal-media-workspace">${renderHero(page, context)}
      <section class="portal-media-workspace-intro"><div><span class="portal-section-kicker">Private Audio Library & Briefing</span><h2>Âm thanh được tổ chức theo ngữ cảnh, quyền sử dụng và ý định sáng tạo</h2><p>Tạo collection cho music/SFX brief, liên kết planning với Project và gắn audio đã nằm trong Asset Vault. Đây là workspace authoring; không phải generator, catalog provider hay trình phát audio.</p></div><dl><div><dt>${safeText(String(Number(collections.active || 0)))}</dt><dd>Đang hoạt động</dd></div><div><dt>${safeText(String(Number(items.total || 0)))}</dt><dd>Audio references</dd></div><div><dt>${safeText(String(Number(items.favorites || 0)))}</dt><dd>Đã đánh dấu</dd></div></dl></section>
      <div class="portal-media-workspace-layout"><section class="portal-card portal-card-pad portal-media-create"><div class="portal-card-header"><div><h2 class="portal-card-title">Tạo audio collection</h2><p class="portal-card-subtitle">Lưu creative brief riêng tư với owner check, CSRF, idempotency và version history. Chưa có AI request hoặc media output.</p></div>${badge(canCreate ? "ready" : "guarded")}</div><form class="portal-form" data-portal-form data-portal-action="media-collection-create" data-portal-route="${safeText(page.routePath || page.path)}" novalidate>${renderFields(mediaCollectionFormFields(), canCreate, context, values)}<div class="portal-form-footer"><span class="portal-form-note">Collection chỉ lưu authoring metadata. Audio được gắn riêng từ Asset Vault sau khi server owner-check.</span><button class="portal-button portal-button--primary" type="submit"${canCreate ? "" : " disabled"}>Tạo collection</button></div></form></section>${renderMediaPolicy(context)}</div>
      <section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Tìm và tiếp tục collection</h2><p class="portal-card-subtitle">Danh sách chỉ chứa metadata/excerpt thuộc signed account hiện tại; nội dung đầy đủ chỉ nạp sau owner check khi mở collection.</p></div><button class="portal-button portal-button--quiet" type="button" data-portal-action="media-workspace-refresh" data-portal-route="/media-workspace">Làm mới</button></div><form class="portal-media-filter" data-portal-form data-portal-action="media-workspace-filter" data-portal-route="/media-workspace" novalidate>${renderFields(filterFields, true, context, filter)}<div class="portal-form-footer"><span class="portal-form-note">Bộ lọc chỉ tồn tại trong phiên trang hiện tại, không lưu localStorage hoặc Telegram.</span><div class="portal-inline-actions"><button class="portal-button portal-button--quiet" type="button" data-portal-action="media-workspace-filter-clear" data-portal-route="/media-workspace">Xóa lọc</button><button class="portal-button portal-button--primary" type="submit">Tìm collection</button></div></div></form>${renderMediaCollectionCards(mediaCollectionItems(context))}</section>
      <section class="portal-card portal-card-pad"><div class="portal-card-header"><div><span class="portal-section-kicker">Audit-safe feed</span><h2 class="portal-card-title">Hoạt động gần đây</h2><p class="portal-card-subtitle">Chỉ có nhãn thao tác, revision và thời điểm; không có raw brief, file path, URL hoặc data provider.</p></div><span class="portal-form-note">${safeText(String(execution.authoring || "ready"))} authoring · ${safeText(String(execution.generation || "guarded"))} generation</span></div>${eventList}</section>
    </article>`;
  }

  function mediaItemEditor(item, collection, enabled, route) {
    const itemId = String(item.id || "");
    const asset = item.asset && typeof item.asset === "object" ? item.asset : {};
    const assetId = validVaultAssetId(asset.id) ? String(asset.id) : "";
    const downloadPath = assetId && asset.download_available === true ? `/api/v1/asset-vault/${encodeURIComponent(assetId)}/download` : "";
    const uid = itemId.replace(/[^a-zA-Z0-9_-]/g, "");
    const editable = enabled && String(collection.state || "") === "active";
    const disabled = editable ? "" : " disabled";
    const selectedRole = String(item.role || "music");
    const tags = mediaCollectionTags(item.tags).join(", ");
    const duration = item.user_declared_duration_seconds === null || item.user_declared_duration_seconds === undefined ? "" : String(item.user_declared_duration_seconds);
    const favorite = item.favorite === true ? " checked" : "";
    return `<article class="portal-media-item-card"><div class="portal-media-item-head"><div><span class="portal-media-file-mark" aria-hidden="true">${safeText(String(asset.extension || "AUDIO").replace(".", "").slice(0, 5).toUpperCase())}</span><div><h3>${safeText(String(item.title_override || asset.display_name || asset.original_filename || "Audio reference"))}</h3><p>${safeText(mediaRoleLabel(item.role))} · ${safeText(vaultBytes(asset.byte_size))} · ${safeText(String(item.delivery || "guarded").replace(/_/g, " "))}</p></div></div>${item.favorite ? "<span class=\"portal-media-favorite\">★ Đã đánh dấu</span>" : ""}</div><form class="portal-form portal-media-item-form" data-portal-form data-portal-action="media-item-update" data-portal-route="${safeText(route)}" data-media-collection-id="${safeText(String(collection.id))}" data-media-collection-revision="${safeText(String(collection.revision))}" data-media-item-id="${safeText(itemId)}" novalidate><div class="portal-fields"><label class="portal-field"><span>Vai trò</span><select class="portal-select" id="media-role-${safeText(uid)}" name="role"${disabled}>${MEDIA_ITEM_ROLES.map(([key, label]) => `<option value="${safeText(key)}"${key === selectedRole ? " selected" : ""}>${safeText(label)}</option>`).join("")}</select></label><label class="portal-field"><span>Tên hiển thị</span><input class="portal-input" id="media-title-${safeText(uid)}" name="title_override" maxlength="180" value="${safeText(String(item.title_override || ""))}"${disabled}></label><label class="portal-field"><span>Attribution</span><input class="portal-input" id="media-attribution-${safeText(uid)}" name="attribution" maxlength="500" value="${safeText(String(item.attribution || ""))}"${disabled}></label><label class="portal-field"><span>Tags</span><input class="portal-input" id="media-tags-${safeText(uid)}" name="tags" maxlength="800" value="${safeText(tags)}"${disabled}></label><label class="portal-field"><span>Thời lượng tự khai báo (giây)</span><input class="portal-input" id="media-duration-${safeText(uid)}" name="user_declared_duration_seconds" type="number" min="1" max="7200" step="1" value="${safeText(duration)}"${disabled}></label><label class="portal-field portal-field--wide"><span>Ghi chú license <span class="portal-required-mark" aria-hidden="true">*</span></span><input class="portal-input" id="media-license-${safeText(uid)}" name="license_note" required minlength="2" maxlength="800" value="${safeText(String(item.license_note || ""))}"${disabled}><small>Thông tin do bạn khai báo; Web không chứng nhận license hoặc quyền thương mại.</small></label><label class="portal-media-checkbox"><input type="checkbox" name="favorite"${favorite}${disabled}><span>Đánh dấu reference này</span></label></div><div class="portal-form-footer"><span class="portal-form-note">Không parse, phát, render hoặc gửi audio đi nơi khác.</span><div class="portal-inline-actions">${downloadPath ? `<a class="portal-button portal-button--quiet" href="${safeText(downloadPath)}" rel="noreferrer">Tải qua Asset Vault</a>` : "<span class=\"portal-form-note\">Tệp không còn active để tải</span>"}<button class="portal-button portal-button--quiet" type="button" data-portal-action="media-item-detach" data-portal-route="${safeText(route)}" data-media-collection-id="${safeText(String(collection.id))}" data-media-collection-revision="${safeText(String(collection.revision))}" data-media-item-id="${safeText(itemId)}" data-portal-confirm="Gỡ audio reference này khỏi collection? Tệp gốc vẫn nằm trong Asset Vault riêng tư."${disabled}>Gỡ reference</button><button class="portal-button portal-button--primary" type="submit"${disabled}>Lưu metadata</button></div></div></form></article>`;
  }

  function renderMediaWorkspaceDetail(page, context) {
    const detail = context.mediaCollectionDetail && typeof context.mediaCollectionDetail === "object" ? context.mediaCollectionDetail : {};
    const collection = detail.collection && typeof detail.collection === "object" && validMediaCollectionId(detail.collection.id) && String(detail.collection.id) === String(page.recordId || "") ? detail.collection : null;
    const canView = Boolean(context.capabilities && context.capabilities["media-workspace-view"] === true);
    if (!canView || !collection) return `<article class="portal-page portal-media-workspace-detail">${renderHero(page, context)}<section class="portal-card portal-card-pad">${renderEmpty("Không tìm thấy audio collection", "Collection có thể không thuộc Web account hiện tại, đã bị gỡ hoặc dữ liệu riêng tư chưa được server xác minh.", ICONS.music)}<div class="portal-form-footer"><a class="portal-button portal-button--primary" href="/media-workspace">Về Audio Library</a></div></section></article>`;
    const state = String(collection.state || "active");
    const writable = state === "active";
    const canUpdate = Boolean(context.capabilities && context.capabilities["media-workspace-update"] === true && writable);
    const canArchive = Boolean(context.capabilities && context.capabilities["media-workspace-archive"] === true && writable);
    const canRestore = Boolean(context.capabilities && context.capabilities["media-workspace-restore"] === true && !writable);
    const canDuplicate = Boolean(context.capabilities && context.capabilities["media-workspace-duplicate"] === true);
    const canRestoreVersion = Boolean(context.capabilities && context.capabilities["media-workspace-restore-version"] === true && writable);
    const canCompose = Boolean(context.capabilities && context.capabilities["media-workspace-compose"] === true && writable);
    const canAttach = Boolean(context.capabilities && context.capabilities["media-workspace-item-attach"] === true && writable);
    const canItemUpdate = Boolean(context.capabilities && context.capabilities["media-workspace-item-update"] === true && writable);
    const route = page.routePath || page.path;
    const values = mediaCollectionValues(collection);
    const versions = Array.isArray(detail.versions) ? detail.versions.filter((item) => item && Number.isInteger(Number(item.revision))).slice(0, 100) : [];
    const items = Array.isArray(detail.items) ? detail.items.filter((item) => item && validMediaCollectionId(item.id)).slice(0, 250) : [];
    const composer = context.mediaComposer && typeof context.mediaComposer === "object" && String(context.mediaComposer.collection_id || "") === String(collection.id) ? context.mediaComposer : {};
    const directions = Array.isArray(composer.directions) ? composer.directions.filter((item) => item && typeof item.prompt === "string").slice(0, 3) : [];
    const policy = collection.policy && typeof collection.policy === "object" ? collection.policy : {};
    const stateAction = writable
      ? `<button class="portal-button portal-button--quiet" type="button" data-portal-action="media-collection-archive" data-portal-route="${safeText(route)}" data-media-collection-id="${safeText(String(collection.id))}" data-media-collection-revision="${safeText(String(collection.revision))}" data-portal-confirm="Archive collection này? Audio reference vẫn giữ trong Asset Vault, nhưng collection sẽ khóa chỉnh sửa cho đến khi khôi phục."${canArchive ? "" : " disabled"}>Archive collection</button>`
      : `<button class="portal-button portal-button--primary" type="button" data-portal-action="media-collection-restore" data-portal-route="${safeText(route)}" data-media-collection-id="${safeText(String(collection.id))}" data-media-collection-revision="${safeText(String(collection.revision))}"${canRestore ? "" : " disabled"}>Khôi phục collection</button>`;
    const versionList = versions.length ? `<div class="portal-version-list">${versions.map((version) => `<div class="portal-version-row"><span><strong>v${safeText(String(version.revision))}</strong><small>${safeText(String(version.title || "Collection"))} · ${safeText(mediaModeLabel(version.prompt_mode))} · ${safeText(String(version.created_at || "—"))}</small></span>${Number(version.revision) === Number(collection.revision) ? "<span class=\"portal-form-note\">Đang mở</span>" : `<button class="portal-button portal-button--quiet" type="button" data-portal-action="media-collection-restore-version" data-portal-route="${safeText(route)}" data-media-collection-id="${safeText(String(collection.id))}" data-media-collection-revision="${safeText(String(collection.revision))}" data-media-collection-version="${safeText(String(version.revision))}" data-portal-confirm="Khôi phục v${safeText(String(version.revision))} thành revision metadata mới? Audio references hiện tại không bị thay đổi."${canRestoreVersion ? "" : " disabled"}>Khôi phục</button>`}</div>`).join("")}</div>` : renderEmpty("Chưa có history", "Version đầu tiên được lưu khi collection được tạo và không bị ghi đè âm thầm.", "○");
    const composerResult = directions.length && composer.execution === "local_deterministic_draft_only" && composer.provider_called === false && composer.charge_started === false
      ? `<div class="portal-media-composer-result">${directions.map((direction) => `<article><span class="portal-section-kicker">${safeText(String(direction.title || "Hướng brief"))}</span><h3>${safeText(String(direction.intent || ""))}</h3><pre>${safeText(direction.prompt)}</pre></article>`).join("")}</div>`
      : "";
    const policyNotice = policy.status === "guarded" ? `<div class="portal-notice portal-notice--warning"><span class="portal-notice-icon" aria-hidden="true">!</span><div><strong>Brief đang bị policy guard</strong><p>Hãy bỏ yêu cầu mô phỏng nghệ sĩ, bài hát, giai điệu hoặc giọng cụ thể trước khi dùng composer. Web không đánh giá hoặc chứng nhận bản quyền.</p></div></div>` : "";
    return `<article class="portal-page portal-media-workspace-detail">${renderHero(page, context)}
      <section class="portal-media-detail-summary"><div><span class="portal-section-kicker">${safeText(mediaModeLabel(collection.prompt_mode))} · ${safeText(String(collection.use_context || "general"))}</span><h2>${safeText(String(collection.title || "Audio Collection"))}</h2><p>${safeText(String(collection.description_excerpt || "Collection authoring riêng tư của Web account hiện tại."))}</p>${renderMediaTags(collection.tags)}</div><dl><div><dt>Revision</dt><dd>v${safeText(String(collection.revision || 1))}</dd></div><div><dt>References</dt><dd>${safeText(String(Number(detail.item_count || items.length)))}/${safeText(String(Number(detail.item_limit || 250)))}</dd></div><div><dt>Trạng thái</dt><dd>${badge(mediaCollectionState(collection.state))}</dd></div></dl></section>
      ${policyNotice}<div class="portal-media-detail-grid"><section class="portal-card portal-card-pad portal-media-editor"><div class="portal-card-header"><div><h2 class="portal-card-title">Collection editor</h2><p class="portal-card-subtitle">Mỗi lần lưu metadata tạo revision mới. Server kiểm tra owner, CSRF, idempotency, policy và optimistic revision trước khi ghi.</p></div>${badge(mediaCollectionState(collection.state))}</div><form class="portal-form" data-portal-form data-portal-action="media-collection-update" data-portal-route="${safeText(route)}" data-media-collection-id="${safeText(String(collection.id))}" data-media-collection-revision="${safeText(String(collection.revision))}" novalidate>${renderFields(mediaCollectionFormFields(), canUpdate, context, values)}<div class="portal-form-footer"><span class="portal-form-note">Không có provider call, job, Xu, PayOS hoặc media output khi lưu collection.</span><div class="portal-inline-actions">${stateAction}<button class="portal-button portal-button--quiet" type="button" data-portal-action="media-collection-duplicate" data-portal-route="${safeText(route)}" data-media-collection-id="${safeText(String(collection.id))}" data-media-collection-revision="${safeText(String(collection.revision))}"${canDuplicate ? "" : " disabled"}>Nhân bản metadata</button><button class="portal-button portal-button--primary" type="submit"${canUpdate ? "" : " disabled"}>Lưu revision mới</button></div></div></form></section>
        <aside class="portal-card portal-card-pad portal-media-composer"><div class="portal-card-header"><div><span class="portal-section-kicker">Local deterministic draft</span><h2 class="portal-card-title">3 hướng brief cục bộ</h2><p class="portal-card-subtitle">Composer chỉ sắp xếp lại brief đã lưu thành text direction. Không chạy AI, tạo audio, job, charge hoặc gọi provider.</p></div>${badge(canCompose ? "read_only" : "guarded")}</div><form class="portal-form" data-portal-form data-portal-action="media-collection-compose" data-portal-route="${safeText(route)}" data-media-collection-id="${safeText(String(collection.id))}" data-media-collection-revision="${safeText(String(collection.revision))}" novalidate><div class="portal-form-footer"><span class="portal-form-note">Cần Music/SFX brief hợp lệ và không bị policy guard.</span><button class="portal-button portal-button--primary" type="submit"${canCompose ? "" : " disabled"}>Tạo hướng brief</button></div></form>${composerResult || "<p class=\"portal-form-note\">Kết quả chỉ tồn tại trong state phiên hiện tại, không tự lưu hoặc gửi tới engine.</p>"}</aside></div>
      <section class="portal-card portal-card-pad"><div class="portal-card-header"><div><span class="portal-section-kicker">Asset Vault references</span><h2 class="portal-card-title">Gắn audio private</h2><p class="portal-card-subtitle">Chỉ audio Asset Vault active thuộc account hiện tại. Không có URL, upload mới, player, waveform hay provider preview trong collection.</p></div>${badge(canAttach ? "ready" : "guarded")}</div><form class="portal-form portal-media-attach-form" data-portal-form data-portal-action="media-item-attach" data-portal-route="${safeText(route)}" data-media-collection-id="${safeText(String(collection.id))}" data-media-collection-revision="${safeText(String(collection.revision))}" novalidate>${renderFields(mediaAttachFields(context), canAttach, context, { role: "music", license_note: "Tôi chịu trách nhiệm kiểm tra license và quyền thương mại trước khi đăng." })}<div class="portal-form-footer"><span class="portal-form-note">Attachment chỉ tạo reference private; tệp gốc không bị copy, đổi state hoặc biến thành output.</span><button class="portal-button portal-button--primary" type="submit"${canAttach ? "" : " disabled"}>Gắn audio từ Asset Vault</button></div></form><div class="portal-media-item-grid">${items.length ? items.map((item) => mediaItemEditor(item, collection, canItemUpdate, route)).join("") : renderEmpty("Chưa có audio reference", "Chọn một tệp audio đã vào Asset Vault để gắn vào collection này. Tệp không được tạo hoặc upload lại ở đây.", ICONS.assets)}</div></section>
      <section class="portal-card portal-card-pad"><div class="portal-card-header"><div><span class="portal-section-kicker">Version history</span><h2 class="portal-card-title">Lịch sử metadata</h2><p class="portal-card-subtitle">Khôi phục luôn tạo revision mới; audio references không bị tự động đảo theo version metadata.</p></div></div>${versionList}</section>
      <section class="portal-card portal-card-pad portal-media-detail-boundary"><div class="portal-card-header"><div><span class="portal-section-kicker">Delivery boundary</span><h2 class="portal-card-title">Tệp vẫn đi qua Asset Vault</h2><p class="portal-card-subtitle">Nếu tệp còn active, nút tải dùng attachment route private đã có. Collection không tạo public URL, streaming, preview hay xác nhận output.</p></div></div>${renderNotes(page)}</section>
    </article>`;
  }

  // Creative Content Studio remains separate from generic /content/* bridge
  // forms. It owns private Web authoring records and local draft scaffolds.
  const CONTENT_STUDIO_KINDS = Object.freeze([
    ["caption_hashtag", "Caption & hashtag"], ["content_ideas", "Ý tưởng nội dung"],
    ["hook_script", "Hook & script"], ["content_pack", "Content pack"], ["storyboard", "Storyboard"]
  ]);

  function validContentBriefId(value) { return validProjectId(value); }
  function contentStudioKindLabel(value) {
    const found = CONTENT_STUDIO_KINDS.find(([key]) => key === String(value || ""));
    return found ? found[1] : "Content brief";
  }
  function contentStudioTags(value) {
    return Array.isArray(value) ? value.filter((item) => typeof item === "string" && item.trim()).slice(0, 20) : [];
  }
  function renderContentStudioTags(value) {
    const tags = contentStudioTags(value);
    return tags.length ? `<div class="portal-content-studio-tags">${tags.map((tag) => `<span>${safeText(tag)}</span>`).join("")}</div>` : "";
  }
  function contentStudioFilterState(context) {
    const source = context && context.contentStudioFilter && typeof context.contentStudioFilter === "object" ? context.contentStudioFilter : {};
    const tidy = (value, max) => typeof value === "string" ? value.replace(/\s+/g, " ").trim().slice(0, max) : "";
    const kind = String(source.content_kind || "").trim().toLowerCase();
    const state = String(source.state || "all").trim().toLowerCase();
    return { q: tidy(source.q, 100), tag: tidy(source.tag, 48), content_kind: CONTENT_STUDIO_KINDS.some(([key]) => key === kind) ? kind : "", state: ["all", "active", "archived"].includes(state) ? state : "all" };
  }
  function contentStudioKindFromQuery() {
    const raw = String(new URLSearchParams(window.location.search || "").get("kind") || "").trim().toLowerCase();
    return CONTENT_STUDIO_KINDS.some(([key]) => key === raw) ? raw : "caption_hashtag";
  }
  function contentStudioReferenceOptions(context, key) {
    const refs = context && context.contentStudioReferences && typeof context.contentStudioReferences === "object" ? context.contentStudioReferences : {};
    const names = { project_id: "projects", campaign_plan_id: "campaigns", prompt_template_id: "prompt_templates", media_collection_id: "media_collections" };
    return (Array.isArray(refs[names[key]]) ? refs[names[key]] : []).filter((item) => item && validContentBriefId(item.id)).slice(0, 100).map((item) => ({ value: String(item.id), label: String(item.title || "Reference riêng tư") }));
  }
  function contentStudioFields(context) {
    return [
      { name: "title", label: "Tên brief", placeholder: "Ví dụ: Launch mùa hè · Caption Instagram", required: true, minLength: 2, maxLength: 180 },
      { name: "content_kind", label: "Loại nội dung", control: "select", required: true, options: CONTENT_STUDIO_KINDS },
      { name: "subject", label: "Chủ đề", placeholder: "Sản phẩm, câu chuyện hoặc vấn đề cần truyền đạt", required: true, minLength: 2, maxLength: 700 },
      { name: "objective", label: "Mục tiêu", placeholder: "Lợi ích cần làm rõ", maxLength: 500 },
      { name: "audience", label: "Đối tượng", placeholder: "Người xem phù hợp", maxLength: 500 },
      { name: "platform", label: "Nền tảng", placeholder: "Instagram / TikTok / Website", maxLength: 100 },
      { name: "tone", label: "Giọng điệu", placeholder: "Rõ ràng, gần gũi", maxLength: 160 },
      { name: "language", label: "Ngôn ngữ", placeholder: "vi", required: true, minLength: 1, maxLength: 100 },
      { name: "call_to_action", label: "CTA", control: "textarea", placeholder: "Hành động mong muốn…", maxLength: 600 },
      { name: "brief_text", label: "Nội dung brief", control: "textarea", placeholder: "Bối cảnh, insight, điểm cần chứng minh và hướng triển khai…", required: true, minLength: 1, maxLength: 12000, wide: true },
      { name: "constraints", label: "Ràng buộc / review notes", control: "textarea", placeholder: "Claim cần kiểm tra, giới hạn thương hiệu, quyền dùng asset…", maxLength: 6000, wide: true },
      { name: "tags", label: "Tags", placeholder: "launch, summer, review", maxLength: 1000 },
      { name: "project_id", label: "Project (tùy chọn)", control: "select", options: contentStudioReferenceOptions(context, "project_id"), emptyLabel: "Không liên kết Project" },
      { name: "campaign_plan_id", label: "Campaign (tùy chọn)", control: "select", options: contentStudioReferenceOptions(context, "campaign_plan_id"), emptyLabel: "Không liên kết Campaign" },
      { name: "prompt_template_id", label: "Prompt template (tùy chọn)", control: "select", options: contentStudioReferenceOptions(context, "prompt_template_id"), emptyLabel: "Không liên kết Prompt template" },
      { name: "media_collection_id", label: "Audio collection (tùy chọn)", control: "select", options: contentStudioReferenceOptions(context, "media_collection_id"), emptyLabel: "Không liên kết Audio collection" },
      { name: "rights_note", label: "Ghi chú quyền sử dụng", control: "textarea", placeholder: "Kiểm tra quyền asset và claim trước khi publish.", maxLength: 1000, wide: true }
    ];
  }
  function contentStudioValues(value) {
    const source = value && typeof value === "object" ? value : {};
    return {
      title: String(source.title || ""), content_kind: CONTENT_STUDIO_KINDS.some(([key]) => key === String(source.content_kind || "")) ? String(source.content_kind) : contentStudioKindFromQuery(),
      subject: String(source.subject || ""), objective: String(source.objective || ""), audience: String(source.audience || ""),
      platform: String(source.platform || ""), tone: String(source.tone || ""), language: String(source.language || "vi"),
      call_to_action: String(source.call_to_action || ""), brief_text: String(source.brief_text || ""), constraints: String(source.constraints || ""),
      tags: contentStudioTags(source.tags).join(", "), project_id: String(source.project_id || ""), campaign_plan_id: String(source.campaign_plan_id || ""),
      prompt_template_id: String(source.prompt_template_id || ""), media_collection_id: String(source.media_collection_id || ""), rights_note: String(source.rights_note || "")
    };
  }
  function contentVariantFields() {
    return [
      { name: "kind", label: "Loại content piece", control: "select", required: true, options: [["caption", "Caption"], ["hashtag_set", "Hashtag set"], ["hook", "Hook"], ["script", "Script"], ["storyboard", "Storyboard"], ["content_pack", "Content pack"], ["content_ideas", "Content ideas"], ["custom", "Tùy chỉnh"]] },
      { name: "title", label: "Tiêu đề", placeholder: "Ví dụ: Hook mở đầu", required: true, minLength: 2, maxLength: 180 },
      { name: "content_text", label: "Nội dung", control: "textarea", placeholder: "Viết khung nội dung có thể review…", required: true, minLength: 1, maxLength: 20000, wide: true },
      { name: "note", label: "Ghi chú review", control: "textarea", placeholder: "Claim, quyền asset hoặc điểm cần xác minh…", maxLength: 2000, wide: true },
      { name: "tags", label: "Tags", placeholder: "launch, review", maxLength: 1000 }
    ];
  }
  function renderContentStudioPolicy(context) {
    const policy = context.contentStudioPolicy && typeof context.contentStudioPolicy === "object" ? context.contentStudioPolicy : {};
    const lines = Array.isArray(policy.guardrails) ? policy.guardrails.filter((item) => typeof item === "string").slice(0, 5) : [];
    return `<aside class="portal-card portal-card-pad portal-content-studio-policy"><div class="portal-card-header"><div><span class="portal-section-kicker">Review boundary</span><h2 class="portal-card-title">Authoring trước, execution sau</h2><p class="portal-card-subtitle">Không có Bot, provider, payment, job, publish hoặc delivery trong workspace này.</p></div>${badge("guarded")}</div><ol class="portal-project-steps">${lines.length ? lines.map((item, index) => `<li><strong>${index + 1}.</strong><span>${safeText(item)}</span></li>`).join("") : "<li><strong>1.</strong><span>Chính sách đang được nạp an toàn từ server.</span></li>"}</ol></aside>`;
  }
  function renderContentBriefCards(items) {
    if (!items.length) return renderEmpty("Chưa có content brief", "Tạo brief đầu tiên để tách tư duy, review và version history khỏi các form generic.", ICONS.prompt);
    return `<div class="portal-content-studio-grid">${items.map((item) => {
      const id = String(item.id || "");
      const archived = String(item.state || "") === "archived";
      return `<article class="portal-card portal-card-pad portal-content-studio-card"><div class="portal-card-header"><div><span class="portal-section-kicker">${safeText(contentStudioKindLabel(item.content_kind))}</span><h3 class="portal-card-title">${safeText(String(item.title || "Content brief"))}</h3><p class="portal-card-subtitle">${safeText(String(item.brief_excerpt || item.subject_excerpt || "Chưa có brief hiển thị."))}</p></div>${badge(archived ? "read_only" : "ready")}</div><div class="portal-content-studio-meta"><span>v${safeText(String(item.revision || 1))}</span><span>${safeText(archived ? "Đã archive" : "Đang hoạt động")}</span><span>${safeText(String(item.platform || "Chưa chọn kênh"))}</span></div>${renderContentStudioTags(item.tags)}<div class="portal-form-footer"><span class="portal-form-note">Private authoring · không có job, charge, output hay publish.</span><a class="portal-button portal-button--quiet" href="/content-studio/${encodeURIComponent(id)}">Mở brief <span aria-hidden="true">→</span></a></div></article>`;
    }).join("")}</div>`;
  }
  function renderContentStudio(page, context) {
    const canView = Boolean(context.capabilities && context.capabilities["content-studio-view"] === true);
    const canCreate = Boolean(context.capabilities && context.capabilities["content-studio-create"] === true);
    if (!canView) return `<article class="portal-page portal-content-studio">${renderHero(page, context)}<section class="portal-card portal-card-pad">${renderEmpty("Content Studio đang được bảo vệ", "Đăng nhập bằng signed session để mở workspace authoring riêng tư.", ICONS.prompt)}</section></article>`;
    const summary = context.contentStudioSummary && typeof context.contentStudioSummary === "object" ? context.contentStudioSummary : {};
    const briefs = summary.briefs && typeof summary.briefs === "object" ? summary.briefs : {};
    const variants = summary.variants && typeof summary.variants === "object" ? summary.variants : {};
    const draft = transientFormValues(page.routePath || page.path);
    const values = contentStudioValues({ ...draft, content_kind: draft.content_kind || contentStudioKindFromQuery() });
    const filter = contentStudioFilterState(context);
    const filterFields = [
      { name: "q", label: "Tìm brief", placeholder: "Tên, chủ đề hoặc brief…", maxLength: 100, wide: true },
      { name: "tag", label: "Tag", placeholder: "Ví dụ: launch", maxLength: 48 },
      { name: "content_kind", label: "Loại", control: "select", options: CONTENT_STUDIO_KINDS, emptyLabel: "Tất cả loại" },
      { name: "state", label: "Trạng thái", control: "select", options: [["all", "Tất cả"], ["active", "Đang hoạt động"], ["archived", "Đã archive"]] }
    ];
    return `<article class="portal-page portal-content-studio">${renderHero(page, context)}
      <section class="portal-content-studio-intro"><div><span class="portal-section-kicker">Creative Content Workspace</span><h2>Biến brief thành content có cấu trúc, dễ review và dễ tiếp tục</h2><p>Quản lý caption, hook, script, storyboard và content pack trong workspace riêng tư có version history. Mọi khung nháp cần được biên tập và xác minh trước khi dùng bên ngoài.</p></div><dl><div><dt>${safeText(String(Number(briefs.active || 0)))}</dt><dd>Brief đang hoạt động</dd></div><div><dt>${safeText(String(Number(variants.active || 0)))}</dt><dd>Content pieces</dd></div><div><dt>${safeText(String(Number(briefs.archived || 0)))}</dt><dd>Đã archive</dd></div></dl></section>
      <div class="portal-content-studio-layout"><section class="portal-card portal-card-pad portal-content-studio-create"><div class="portal-card-header"><div><h2 class="portal-card-title">Tạo content brief</h2><p class="portal-card-subtitle">Lưu ngữ cảnh, ràng buộc và reference theo signed account. Không có AI request, job hoặc publish.</p></div>${badge(canCreate ? "ready" : "guarded")}</div><form class="portal-form" data-portal-form data-portal-action="content-brief-create" data-portal-route="${safeText(page.routePath || page.path)}" novalidate>${renderFields(contentStudioFields(context), canCreate, context, values)}<div class="portal-form-footer"><span class="portal-form-note">Nhập nội dung nguyên bản; không nhập token, OTP, payment proof hoặc yêu cầu mô phỏng tác giả/phong cách.</span><button class="portal-button portal-button--primary" type="submit"${canCreate ? "" : " disabled"}>Tạo brief</button></div></form></section>${renderContentStudioPolicy(context)}</div>
      <section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Tìm và tiếp tục brief</h2><p class="portal-card-subtitle">List chỉ chứa metadata/excerpt riêng tư; nội dung đầy đủ chỉ nạp khi owner mở brief.</p></div><button class="portal-button portal-button--quiet" type="button" data-portal-action="content-studio-refresh" data-portal-route="/content-studio">Làm mới</button></div><form class="portal-content-studio-filter" data-portal-form data-portal-action="content-studio-filter" data-portal-route="/content-studio" novalidate>${renderFields(filterFields, true, context, filter)}<div class="portal-form-footer"><span class="portal-form-note">Bộ lọc chỉ tồn tại trong phiên trang hiện tại.</span><div class="portal-inline-actions"><button class="portal-button portal-button--quiet" type="button" data-portal-action="content-studio-filter-clear" data-portal-route="/content-studio">Xóa lọc</button><button class="portal-button portal-button--primary" type="submit">Tìm brief</button></div></div></form>${renderContentBriefCards(Array.isArray(context.contentBriefs) ? context.contentBriefs : [])}</section>
    </article>`;
  }
  function renderContentStudioDetail(page, context) {
    const detail = context.contentBriefDetail && typeof context.contentBriefDetail === "object" ? context.contentBriefDetail : {};
    const brief = detail.brief && typeof detail.brief === "object" && validContentBriefId(detail.brief.id) && String(detail.brief.id) === String(page.recordId || "") ? detail.brief : null;
    const canView = Boolean(context.capabilities && context.capabilities["content-studio-view"] === true);
    if (!canView || !brief) return `<article class="portal-page portal-content-studio-detail">${renderHero(page, context)}<section class="portal-card portal-card-pad">${renderEmpty("Không tìm thấy content brief", "Brief có thể không thuộc Web account hiện tại hoặc chưa được server xác minh.", ICONS.prompt)}<div class="portal-form-footer"><a class="portal-button portal-button--primary" href="/content-studio">Về Content Studio</a></div></section></article>`;
    const route = page.routePath || page.path;
    const writable = String(brief.state || "") === "active";
    const canUpdate = Boolean(context.capabilities && context.capabilities["content-studio-update"] === true && writable);
    const canCompose = Boolean(context.capabilities && context.capabilities["content-studio-compose"] === true && writable);
    const canArchive = Boolean(context.capabilities && context.capabilities["content-studio-archive"] === true && writable);
    const canRestore = Boolean(context.capabilities && context.capabilities["content-studio-restore"] === true && !writable);
    const canDuplicate = Boolean(context.capabilities && context.capabilities["content-studio-duplicate"] === true);
    const canRestoreVersion = Boolean(context.capabilities && context.capabilities["content-studio-restore-version"] === true && writable);
    const canVariantCreate = Boolean(context.capabilities && context.capabilities["content-studio-variant-create"] === true && writable);
    const canVariantArchive = Boolean(context.capabilities && context.capabilities["content-studio-variant-archive"] === true);
    const canVariantRestore = Boolean(context.capabilities && context.capabilities["content-studio-variant-restore"] === true);
    const canVariantDuplicate = Boolean(context.capabilities && context.capabilities["content-studio-variant-duplicate"] === true);
    const canVariantRestoreVersion = Boolean(context.capabilities && context.capabilities["content-studio-variant-restore-version"] === true && writable);
    const variants = Array.isArray(detail.variants) ? detail.variants.filter((item) => item && validContentBriefId(item.id)).slice(0, 250) : [];
    const versions = Array.isArray(detail.versions) ? detail.versions.filter((item) => Number.isInteger(Number(item.revision))).slice(0, 100) : [];
    const activeHistory = context.contentVariantHistory && typeof context.contentVariantHistory === "object" ? context.contentVariantHistory : {};
    const variantHistoryId = validContentBriefId(activeHistory.variant_id) ? String(activeHistory.variant_id) : "";
    const variantHistoryVersions = Array.isArray(activeHistory.versions) ? activeHistory.versions.filter((item) => item && Number.isInteger(Number(item.revision))).slice(0, 100) : [];
    const contentCards = variants.length ? variants.map((item) => {
      const itemId = String(item.id || "");
      const selected = String(brief.selected_variant_id || "") === itemId;
      const active = String(item.state || "") === "active";
      const selectable = Boolean(context.capabilities && context.capabilities["content-studio-variant-select"] === true && writable && active);
      const editable = Boolean(context.capabilities && context.capabilities["content-studio-variant-update"] === true && writable && active);
      const itemHistory = variantHistoryId === itemId ? variantHistoryVersions : [];
      const stateAction = active
        ? `<button class="portal-button portal-button--quiet" type="button" data-portal-action="content-variant-archive" data-portal-route="${safeText(route)}" data-content-brief-id="${safeText(String(brief.id))}" data-content-variant-id="${safeText(itemId)}" data-content-variant-revision="${safeText(String(item.revision))}" data-portal-confirm="Archive content piece này? Nội dung và history vẫn được giữ riêng tư cho đến khi khôi phục."${canVariantArchive && writable ? "" : " disabled"}>Archive</button>`
        : `<button class="portal-button portal-button--quiet" type="button" data-portal-action="content-variant-restore" data-portal-route="${safeText(route)}" data-content-brief-id="${safeText(String(brief.id))}" data-content-variant-id="${safeText(itemId)}" data-content-variant-revision="${safeText(String(item.revision))}"${canVariantRestore && writable ? "" : " disabled"}>Khôi phục</button>`;
      const historyPanel = itemHistory.length ? `<div class="portal-content-variant-history"><strong>Lịch sử content piece</strong>${itemHistory.map((version) => `<div><span>v${safeText(String(version.revision))} · ${safeText(String(version.created_at || "—"))}</span>${Number(version.revision) === Number(item.revision) ? "<em>Đang mở</em>" : `<button class="portal-button portal-button--quiet" type="button" data-portal-action="content-variant-restore-version" data-portal-route="${safeText(route)}" data-content-brief-id="${safeText(String(brief.id))}" data-content-variant-id="${safeText(itemId)}" data-content-variant-revision="${safeText(String(item.revision))}" data-content-variant-version="${safeText(String(version.revision))}" data-portal-confirm="Khôi phục v${safeText(String(version.revision))} thành một revision content piece mới?"${canVariantRestoreVersion && active ? "" : " disabled"}>Khôi phục v${safeText(String(version.revision))}</button>`}</div>`).join("")}</div>` : "";
      return `<article class="portal-content-variant-card${selected ? " is-selected" : ""}"><div class="portal-card-header"><div><span class="portal-section-kicker">${safeText(String(item.kind || "custom").replace(/_/g, " "))}</span><h3 class="portal-card-title">${safeText(String(item.title || "Content piece"))}</h3><p class="portal-card-subtitle">${safeText(String(item.content_excerpt || ""))}</p></div>${selected ? "<span class=\"portal-content-selected\">Đang chọn</span>" : badge(active ? "ready" : "read_only")}</div>${renderContentStudioTags(item.tags)}<div class="portal-inline-actions"><button class="portal-button portal-button--quiet" type="button" data-portal-action="content-variant-select" data-portal-route="${safeText(route)}" data-content-brief-id="${safeText(String(brief.id))}" data-content-brief-revision="${safeText(String(brief.revision))}" data-content-variant-id="${safeText(itemId)}"${selectable ? "" : " disabled"}>Chọn</button><button class="portal-button portal-button--quiet" type="button" data-portal-action="content-variant-history" data-portal-route="${safeText(route)}" data-content-brief-id="${safeText(String(brief.id))}" data-content-variant-id="${safeText(itemId)}">Lịch sử</button>${stateAction}<button class="portal-button portal-button--quiet" type="button" data-portal-action="content-variant-duplicate" data-portal-route="${safeText(route)}" data-content-brief-id="${safeText(String(brief.id))}" data-content-variant-id="${safeText(itemId)}" data-content-variant-revision="${safeText(String(item.revision))}"${canVariantDuplicate && active && writable ? "" : " disabled"}>Nhân bản</button></div><form id="piece-${safeText(itemId)}" class="portal-form portal-content-variant-form" data-portal-form data-portal-action="content-variant-update" data-portal-route="${safeText(route)}" data-content-brief-id="${safeText(String(brief.id))}" data-content-variant-id="${safeText(itemId)}" data-content-variant-revision="${safeText(String(item.revision))}" novalidate>${renderFields(contentVariantFields(), editable, context, { kind: String(item.kind || "custom"), title: String(item.title || ""), content_text: String(item.content_text || ""), note: String(item.note || ""), tags: contentStudioTags(item.tags).join(", ") })}<div class="portal-form-footer"><span class="portal-form-note">Content piece vẫn là bản biên tập riêng tư.</span><button class="portal-button portal-button--primary" type="submit"${editable ? "" : " disabled"}>Lưu piece</button></div></form>${historyPanel}</article>`;
    }).join("") : renderEmpty("Chưa có content piece", "Dùng composer hoặc thêm piece thủ công để bắt đầu review.", ICONS.prompt);
    const stateAction = writable
      ? `<button class="portal-button portal-button--quiet" type="button" data-portal-action="content-brief-archive" data-portal-route="${safeText(route)}" data-content-brief-id="${safeText(String(brief.id))}" data-content-brief-revision="${safeText(String(brief.revision))}" data-portal-confirm="Archive brief này? Nội dung, pieces và history vẫn giữ riêng tư cho đến khi khôi phục."${canArchive ? "" : " disabled"}>Archive brief</button>`
      : `<button class="portal-button portal-button--quiet" type="button" data-portal-action="content-brief-restore" data-portal-route="${safeText(route)}" data-content-brief-id="${safeText(String(brief.id))}" data-content-brief-revision="${safeText(String(brief.revision))}"${canRestore ? "" : " disabled"}>Khôi phục brief</button>`;
    const activity = Array.isArray(detail.events) ? detail.events.filter((item) => item && typeof item === "object").slice(0, 12) : [];
    return `<article class="portal-page portal-content-studio-detail">${renderHero(page, context)}
      <section class="portal-content-studio-detail-summary"><div><span class="portal-section-kicker">${safeText(contentStudioKindLabel(brief.content_kind))}</span><h2>${safeText(String(brief.title || "Content brief"))}</h2><p>${safeText(String(brief.brief_excerpt || brief.subject || ""))}</p></div><dl><div><dt>Trạng thái</dt><dd>${safeText(writable ? "Đang hoạt động" : "Đã archive")}</dd></div><div><dt>Revision</dt><dd>v${safeText(String(brief.revision || 1))}</dd></div><div><dt>Pieces</dt><dd>${safeText(String(variants.length))}</dd></div></dl></section>
      <div class="portal-content-studio-detail-grid"><section class="portal-card portal-card-pad portal-content-studio-editor"><div class="portal-card-header"><div><h2 class="portal-card-title">Brief & review context</h2><p class="portal-card-subtitle">Lưu bằng optimistic revision và owner check cho reference.</p></div>${badge(writable ? "ready" : "read_only")}</div><form class="portal-form" data-portal-form data-portal-action="content-brief-update" data-portal-route="${safeText(route)}" data-content-brief-id="${safeText(String(brief.id))}" data-content-brief-revision="${safeText(String(brief.revision))}" novalidate>${renderFields(contentStudioFields(context), canUpdate, context, contentStudioValues(brief))}<div class="portal-form-footer"><span class="portal-form-note">Mỗi lần lưu tạo revision mới; reference luôn được kiểm tra lại trên server.</span><div class="portal-inline-actions">${stateAction}<button class="portal-button portal-button--quiet" type="button" data-portal-action="content-brief-duplicate" data-portal-route="${safeText(route)}" data-content-brief-id="${safeText(String(brief.id))}" data-content-brief-revision="${safeText(String(brief.revision))}"${canDuplicate ? "" : " disabled"}>Nhân bản brief</button><button class="portal-button portal-button--primary" type="submit"${canUpdate ? "" : " disabled"}>Lưu brief</button></div></div></form></section>${renderContentStudioPolicy(context)}</div>
      <section class="portal-card portal-card-pad portal-content-studio-composer"><div class="portal-card-header"><div><span class="portal-section-kicker">Local deterministic drafts</span><h2 class="portal-card-title">Tạo 3 khung nháp để biên tập</h2><p class="portal-card-subtitle">Không phải AI output, job, asset, delivery hoặc nội dung đã publish.</p></div>${badge(canCompose ? "ready" : "guarded")}</div><div class="portal-form-footer"><span class="portal-form-note">Các khung nháp được lưu thành content pieces riêng tư và cần review thủ công.</span><button class="portal-button portal-button--primary" type="button" data-portal-action="content-brief-compose" data-portal-route="${safeText(route)}" data-content-brief-id="${safeText(String(brief.id))}" data-content-brief-revision="${safeText(String(brief.revision))}"${canCompose ? "" : " disabled"}>Tạo 3 khung nháp</button></div></section>
      <section class="portal-card portal-card-pad portal-content-variant-create"><div class="portal-card-header"><div><span class="portal-section-kicker">Manual authoring</span><h2 class="portal-card-title">Thêm content piece thủ công</h2><p class="portal-card-subtitle">Dành cho ý tưởng, caption, script hoặc checklist đã có sẵn để đưa vào cùng brief.</p></div>${badge(canVariantCreate ? "ready" : "guarded")}</div><form class="portal-form" data-portal-form data-portal-action="content-variant-create" data-portal-route="${safeText(route)}" data-content-brief-id="${safeText(String(brief.id))}" data-content-brief-revision="${safeText(String(brief.revision))}" novalidate>${renderFields(contentVariantFields(), canVariantCreate, context, { kind: "custom", title: "", content_text: "", note: "", tags: "" })}<div class="portal-form-footer"><span class="portal-form-note">Không nhập secret, OTP, payment proof hoặc yêu cầu mô phỏng tác giả/phong cách.</span><button class="portal-button portal-button--primary" type="submit"${canVariantCreate ? "" : " disabled"}>Thêm content piece</button></div></form></section>
      <section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Content pieces</h2><p class="portal-card-subtitle">Chọn, biên tập, archive hoặc xem history của từng piece trong brief.</p></div></div><div class="portal-content-variant-grid">${contentCards}</div></section>
      <div class="portal-content-studio-history-grid"><section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Lịch sử brief</h2><p class="portal-card-subtitle">Khôi phục version chỉ khi reference còn hợp lệ và thuộc signed account.</p></div></div><div class="portal-content-version-list">${versions.length ? versions.map((item) => `<article><div><strong>v${safeText(String(item.revision))} · ${safeText(String(item.title || "Content brief"))}</strong><p>${safeText(String(item.brief_excerpt || ""))}</p><small>${safeText(String(item.created_at || "—"))}</small></div>${Number(item.revision) === Number(brief.revision) ? "<span class=\"portal-form-note\">Đang mở</span>" : `<button class="portal-button portal-button--quiet" type="button" data-portal-action="content-brief-restore-version" data-portal-route="${safeText(route)}" data-content-brief-id="${safeText(String(brief.id))}" data-content-brief-revision="${safeText(String(brief.revision))}" data-content-brief-version="${safeText(String(item.revision))}" data-portal-confirm="Khôi phục v${safeText(String(item.revision))} thành một revision brief mới?"${canRestoreVersion ? "" : " disabled"}>Khôi phục v${safeText(String(item.revision))}</button>`}</article>`).join("") : renderEmpty("Chưa có history", "Version đầu tiên sẽ xuất hiện sau khi server lưu brief.", "↺")}</div></section><section class="portal-card portal-card-pad portal-content-studio-activity"><div class="portal-card-header"><div><h2 class="portal-card-title">Hoạt động gần đây</h2><p class="portal-card-subtitle">Chỉ ghi nhãn thao tác và revision, không đưa nội dung brief vào audit feed.</p></div></div><div class="portal-content-activity-list">${activity.length ? activity.map((item) => `<div><span></span><p><strong>${safeText(String(item.action || "content_updated").replace(/_/g, " "))}</strong><small>v${safeText(String(item.revision || 1))} · ${safeText(String(item.created_at || "—"))}</small></p></div>`).join("") : "<p class=\"portal-form-note\">Chưa có hoạt động được ghi nhận.</p>"}</div></section></div>
    </article>`;
  }

  // Voice Studio is intentionally distinct from the bridge-backed `/voice`
  // surface. These records are private Web authoring metadata only: a voice
  // direction, an optional self-attestation and scripts. They never become a
  // provider profile, a Bot Voice Vault profile, an audio preview or delivery.
  const VOICE_STUDIO_VAULT_KINDS = Object.freeze([
    ["delivery_style", "Hướng thể hiện"], ["brand_narration", "Narration thương hiệu"], ["consented_reference", "Reference có self-attestation"]
  ]);
  const VOICE_STUDIO_SCRIPT_KINDS = Object.freeze([
    ["narration", "Lời dẫn"], ["ad", "Quảng cáo / CTA"], ["explainer", "Giải thích"], ["podcast", "Podcast"], ["training", "Đào tạo"], ["custom", "Tùy chỉnh"]
  ]);
  const VOICE_STUDIO_CONSENT_STATUSES = Object.freeze([
    ["not_required", "Không cần consent"], ["self_attested", "Tự xác nhận quyền sử dụng"], ["revoked", "Đã thu hồi"]
  ]);

  function validVoiceVaultId(value) { return validProjectId(value); }
  function voiceStudioVaultKindLabel(value) {
    const found = VOICE_STUDIO_VAULT_KINDS.find(([key]) => key === String(value || ""));
    return found ? found[1] : "Voice direction";
  }
  function voiceStudioScriptKindLabel(value) {
    const found = VOICE_STUDIO_SCRIPT_KINDS.find(([key]) => key === String(value || ""));
    return found ? found[1] : "Script";
  }
  function voiceStudioConsentLabel(value) {
    const found = VOICE_STUDIO_CONSENT_STATUSES.find(([key]) => key === String(value || ""));
    return found ? found[1] : "Chưa khai báo";
  }
  function voiceStudioTags(value) {
    return Array.isArray(value) ? value.filter((item) => typeof item === "string" && item.trim()).slice(0, 20) : [];
  }
  function renderVoiceStudioTags(value) {
    const tags = voiceStudioTags(value);
    return tags.length ? `<div class="portal-voice-studio-tags">${tags.map((tag) => `<span>${safeText(tag)}</span>`).join("")}</div>` : "";
  }
  function voiceStudioFilterState(context) {
    const source = context && context.voiceStudioFilter && typeof context.voiceStudioFilter === "object" ? context.voiceStudioFilter : {};
    const tidy = (value, maximum) => typeof value === "string" ? value.replace(/\s+/g, " ").trim().slice(0, maximum) : "";
    const state = String(source.state || "all").trim().toLowerCase();
    return { q: tidy(source.q, 100), tag: tidy(source.tag, 48), state: ["all", "active", "archived"].includes(state) ? state : "all" };
  }
  function voiceStudioReferenceOptions(context, key) {
    const refs = context && context.voiceStudioReferences && typeof context.voiceStudioReferences === "object" ? context.voiceStudioReferences : {};
    const source = key === "content_brief_id" ? refs.content_briefs : refs.projects;
    return (Array.isArray(source) ? source : []).filter((item) => item && validVoiceVaultId(item.id)).slice(0, 100)
      .map((item) => ({ value: String(item.id), label: String(item.title || "Reference Web riêng tư") }));
  }
  function voiceStudioVaultFields(context) {
    return [
      { name: "title", label: "Tên voice direction", placeholder: "Ví dụ: Narration thương hiệu · ra mắt mùa hè", required: true, minLength: 2, maxLength: 180 },
      { name: "vault_kind", label: "Loại direction", control: "select", required: true, options: VOICE_STUDIO_VAULT_KINDS },
      { name: "language", label: "Ngôn ngữ", placeholder: "vi", required: true, minLength: 1, maxLength: 100 },
      { name: "style_notes", label: "Cách thể hiện", control: "textarea", placeholder: "Nhịp, mức độ rõ ràng, năng lượng, khoảng nghỉ và các nguyên tắc biên tập…", maxLength: 1600, wide: true, help: "Mô tả direction nguyên gốc, không yêu cầu mô phỏng hoặc nhái một người cụ thể." },
      { name: "use_context", label: "Ngữ cảnh sử dụng", control: "textarea", placeholder: "Ví dụ: lời dẫn video giới thiệu sản phẩm, bản nội bộ cần review…", maxLength: 1600, wide: true },
      { name: "consent_status", label: "Trạng thái consent", control: "select", required: true, options: VOICE_STUDIO_CONSENT_STATUSES, help: "Reference chỉ dùng self-attested hoặc Đã thu hồi. Đây là metadata do bạn khai báo, không phải phê duyệt quyền hay clone." },
      { name: "consent_note", label: "Ghi chú consent", control: "textarea", placeholder: "Nếu là reference: mô tả self-attestation hoặc việc thu hồi (ít nhất 12 ký tự).", maxLength: 1400, wide: true },
      { name: "is_default", label: "Direction mặc định trong Voice Studio", type: "checkbox", help: "Chỉ là ưu tiên local của workspace này; không đổi default TTS/Voice Vault của Bot hoặc provider." },
      { name: "tags", label: "Tags", placeholder: "brand, launch, review", maxLength: 1000 },
      { name: "project_id", label: "Project (tùy chọn)", control: "select", options: voiceStudioReferenceOptions(context, "project_id"), emptyLabel: "Không liên kết Project" },
      { name: "content_brief_id", label: "Content Brief (tùy chọn)", control: "select", options: voiceStudioReferenceOptions(context, "content_brief_id"), emptyLabel: "Không liên kết Content Brief" }
    ];
  }
  function voiceStudioVaultValues(value) {
    const source = value && typeof value === "object" ? value : {};
    const kind = String(source.vault_kind || "");
    const consent = String(source.consent_status || "");
    return {
      title: String(source.title || ""), vault_kind: VOICE_STUDIO_VAULT_KINDS.some(([key]) => key === kind) ? kind : "delivery_style",
      language: String(source.language || "vi"), style_notes: String(source.style_notes || ""), use_context: String(source.use_context || ""),
      consent_status: VOICE_STUDIO_CONSENT_STATUSES.some(([key]) => key === consent) ? consent : "not_required", consent_note: String(source.consent_note || ""),
      is_default: source.is_default === true, tags: voiceStudioTags(source.tags).join(", "), project_id: String(source.project_id || ""), content_brief_id: String(source.content_brief_id || "")
    };
  }
  function voiceStudioScriptFields() {
    return [
      { name: "title", label: "Tên script", placeholder: "Ví dụ: Mở đầu video launch", required: true, minLength: 2, maxLength: 180 },
      { name: "script_kind", label: "Loại script", control: "select", required: true, options: VOICE_STUDIO_SCRIPT_KINDS },
      { name: "language", label: "Ngôn ngữ", placeholder: "vi", required: true, minLength: 1, maxLength: 100 },
      { name: "audience", label: "Người nghe", placeholder: "Ví dụ: khách hàng mới", maxLength: 500 },
      { name: "pace_wpm", label: "Nhịp đọc ước lượng (WPM)", type: "number", required: true, min: 80, max: 240, step: 1, inputMode: "numeric", help: "Dùng riêng cho cue-sheet theo text; không phản ánh giọng, tốc độ provider hoặc audio thật." },
      { name: "script_text", label: "Lời thoại", control: "textarea", placeholder: "Viết bản lời thoại để review…", required: true, minLength: 1, maxLength: 24000, wide: true },
      { name: "delivery_notes", label: "Chỉ dẫn thể hiện", control: "textarea", placeholder: "Khoảng nghỉ, nhấn ý, cách nói rõ ràng…", maxLength: 5000, wide: true },
      { name: "pronunciation_notes", label: "Ghi chú phát âm", control: "textarea", placeholder: "Tên sản phẩm hoặc thuật ngữ cần kiểm tra…", maxLength: 3000, wide: true },
      { name: "tags", label: "Tags", placeholder: "launch, intro, review", maxLength: 1000 }
    ];
  }
  function voiceStudioScriptValues(value) {
    const source = value && typeof value === "object" ? value : {};
    const kind = String(source.script_kind || "");
    const pace = Number(source.pace_wpm);
    return {
      title: String(source.title || ""), script_kind: VOICE_STUDIO_SCRIPT_KINDS.some(([key]) => key === kind) ? kind : "narration",
      language: String(source.language || "vi"), audience: String(source.audience || ""), pace_wpm: Number.isFinite(pace) ? String(Math.min(240, Math.max(80, Math.round(pace)))) : "145",
      script_text: String(source.script_text || ""), delivery_notes: String(source.delivery_notes || ""), pronunciation_notes: String(source.pronunciation_notes || ""), tags: voiceStudioTags(source.tags).join(", ")
    };
  }
  function voiceStudioEventLabel(value) {
    const labels = {
      vault_created: "Đã tạo voice direction", vault_updated: "Đã lưu voice direction", vault_archived: "Đã archive voice direction", vault_restored: "Đã khôi phục voice direction", vault_duplicated: "Đã nhân bản voice direction", vault_version_restored: "Đã khôi phục version voice direction", default_cleared: "Đã cập nhật default local",
      script_created: "Đã tạo script", script_updated: "Đã lưu script", script_archived: "Đã archive script", script_restored: "Đã khôi phục script", script_duplicated: "Đã nhân bản script", script_version_restored: "Đã khôi phục version script", scripts_composed: "Đã tạo khung script cục bộ"
    };
    return labels[String(value || "")] || String(value || "voice_studio_updated").replace(/_/g, " ");
  }
  function renderVoiceStudioPolicy(context) {
    const policy = context.voiceStudioPolicy && typeof context.voiceStudioPolicy === "object" ? context.voiceStudioPolicy : {};
    const guardItems = [
      ["TTS", policy.tts || "guarded"], ["Voice clone", policy.voice_clone || "guarded"], ["Preview", policy.preview || "guarded"], ["Delivery", policy.output_delivery || "guarded"]
    ];
    return `<aside class="portal-card portal-card-pad portal-voice-studio-policy"><div class="portal-card-header"><div><span class="portal-section-kicker">Ranh giới thực thi</span><h2 class="portal-card-title">Soạn direction, không tạo giọng</h2><p class="portal-card-subtitle">Vault này chỉ lưu metadata riêng tư, self-attestation và script. Không có raw audio, provider profile, URL preview, Bot job, Xu hoặc PayOS.</p></div>${badge("guarded")}</div><div class="portal-voice-studio-guard-list">${guardItems.map(([label, state]) => `<span><strong>${safeText(label)}</strong><em>${safeText(String(state).replace(/_/g, " "))}</em></span>`).join("")}</div><div class="portal-notice portal-notice--info"><span class="portal-notice-icon" aria-hidden="true">i</span><div><strong>Consent là self-attestation</strong><p>Web lưu nội dung bạn tự xác nhận để review nội bộ; nó không xác minh danh tính, không cấp quyền sử dụng và không kích hoạt clone.</p></div></div></aside>`;
  }
  function renderVoiceVaultCards(items, context) {
    const canView = Boolean(context.capabilities && context.capabilities["voice-studio-view"] === true);
    if (!items.length) return renderEmpty("Chưa có voice direction", "Tạo direction đầu tiên để lưu guideline, consent metadata và các bản script riêng tư. Không có audio, preview hoặc output được tạo ở đây.", ICONS.voice);
    return `<div class="portal-voice-vault-grid">${items.map((item) => {
      const id = String(item.id || "");
      const active = String(item.state || "active") === "active";
      const isDefault = item.is_default === true;
      const policy = item.policy && typeof item.policy === "object" ? item.policy : {};
      const warning = policy.status === "guarded" ? `<span class="portal-voice-policy-flag">Cần review direction</span>` : "";
      return `<article class="portal-card portal-card-pad portal-voice-vault-card${isDefault ? " is-default" : ""}"><div class="portal-card-header"><div><span class="portal-section-kicker">${safeText(voiceStudioVaultKindLabel(item.vault_kind))}</span><h3 class="portal-card-title">${safeText(String(item.title || "Voice direction"))}</h3><p class="portal-card-subtitle">${safeText(String(item.style_excerpt || item.use_context_excerpt || "Chưa có mô tả hiển thị."))}</p></div>${isDefault ? "<span class=\"portal-voice-default\">Default local</span>" : badge(active ? "ready" : "read_only")}</div><div class="portal-voice-vault-meta"><span>${safeText(String(item.language || "vi"))}</span><span>${safeText(voiceStudioConsentLabel(item.consent_status))}</span><span>v${safeText(String(item.revision || 1))}</span></div>${warning}${renderVoiceStudioTags(item.tags)}<div class="portal-form-footer"><span class="portal-form-note">${active ? "Metadata-only · provider chưa kết nối" : "Đã archive · chỉ đọc"}</span>${canView && validVoiceVaultId(id) ? `<a class="portal-button portal-button--quiet" href="/voice-studio/${encodeURIComponent(id)}">Mở direction <span aria-hidden="true">→</span></a>` : ""}</div></article>`;
    }).join("")}</div>`;
  }
  function renderVoiceStudio(page, context) {
    const canView = Boolean(context.capabilities && context.capabilities["voice-studio-view"] === true);
    const canCreate = Boolean(context.capabilities && context.capabilities["voice-vault-create"] === true);
    if (!canView) return `<article class="portal-page portal-voice-studio">${renderHero(page, context)}<section class="portal-card portal-card-pad">${renderEmpty("Voice Studio đang được bảo vệ", "Đăng nhập bằng signed session để mở voice direction và script riêng tư. Route này không đọc Bot Voice Vault hoặc nhận Telegram ID thô.", ICONS.voice)}</section></article>`;
    const summary = context.voiceStudioSummary && typeof context.voiceStudioSummary === "object" ? context.voiceStudioSummary : {};
    const vaults = summary.vaults && typeof summary.vaults === "object" ? summary.vaults : {};
    const scripts = summary.scripts && typeof summary.scripts === "object" ? summary.scripts : {};
    const execution = summary.execution && typeof summary.execution === "object" ? summary.execution : {};
    const filter = voiceStudioFilterState(context);
    const formValues = voiceStudioVaultValues(transientFormValues(page.routePath || page.path));
    const filterFields = [
      { name: "q", label: "Tìm direction", placeholder: "Tên, style hoặc ngữ cảnh…", maxLength: 100, wide: true },
      { name: "tag", label: "Tag", placeholder: "Ví dụ: launch", maxLength: 48 },
      { name: "state", label: "Trạng thái", control: "select", options: [["all", "Tất cả"], ["active", "Đang hoạt động"], ["archived", "Đã archive"]] }
    ];
    const events = Array.isArray(context.voiceStudioEvents) ? context.voiceStudioEvents.filter((item) => item && typeof item === "object").slice(0, 8) : [];
    const eventMarkup = events.length ? `<div class="portal-voice-studio-events">${events.map((item) => `<div><span aria-hidden="true">•</span><span><strong>${safeText(voiceStudioEventLabel(item.action))}</strong><small>v${safeText(String(item.revision || 1))} · ${safeText(String(item.created_at || "—"))}</small></span></div>`).join("")}</div>` : renderEmpty("Chưa có hoạt động", "Audit feed chỉ giữ nhãn thao tác, revision và thời điểm; không lộ script, consent note, provider hoặc dữ liệu Bot.", "○");
    const readState = String(context.voiceStudioReadState || "guarded");
    const vaultListing = readState === "loading"
      ? renderEmpty("Đang nạp direction riêng tư", "Chờ server xác minh signed account; Web không hiển thị fallback từ Bot Voice Vault.", "…")
      : readState === "failed"
        ? renderEmpty("Chưa thể nạp Voice Studio", "Dữ liệu cũ không được giữ lại hoặc thay bằng dữ liệu Bot. Hãy làm mới sau khi signed API sẵn sàng.", "!")
        : readState === "guarded"
          ? renderEmpty("Voice Studio đang ở chế độ an toàn", "Owner-scoped hydration chưa sẵn sàng nên không hiển thị danh sách hoặc nội dung cũ.", "○")
          : renderVoiceVaultCards(Array.isArray(context.voiceVaults) ? context.voiceVaults : [], context);
    return `<article class="portal-page portal-voice-studio">${renderHero(page, context)}
      <section class="portal-voice-studio-intro"><div><span class="portal-section-kicker">Private Voice Direction & Script Workspace</span><h2>Giữ nhất quán cách kể, kiểm soát consent và review lời thoại trước khi đưa sang bất kỳ engine nào</h2><p>Voice Studio là workspace Web-native cho direction, consent metadata và script. Nó không phải TTS, voice clone, trình nghe thử hay khu vực delivery.</p></div><dl><div><dt>${safeText(String(Number(vaults.active || 0)))}</dt><dd>Direction hoạt động</dd></div><div><dt>${safeText(String(Number(scripts.active || 0)))}</dt><dd>Script hoạt động</dd></div><div><dt>${safeText(String(Number(vaults.archived || 0)))}</dt><dd>Đã archive</dd></div></dl></section>
      <div class="portal-voice-studio-layout"><section class="portal-card portal-card-pad portal-voice-studio-create"><div class="portal-card-header"><div><h2 class="portal-card-title">Tạo voice direction</h2><p class="portal-card-subtitle">Lưu metadata có owner check, CSRF, idempotency, audit và version history. Chưa có request TTS, clone, preview hay audio output.</p></div>${badge(canCreate ? "ready" : "guarded")}</div><form class="portal-form" data-portal-form data-portal-action="voice-vault-create" data-portal-route="${safeText(page.routePath || page.path)}" novalidate>${renderFields(voiceStudioVaultFields(context), canCreate, context, formValues)}<div class="portal-form-footer"><span class="portal-form-note">Reference có self-attestation cần ghi chú tối thiểu 12 ký tự. Không dùng trường này để yêu cầu nhái giọng.</span><button class="portal-button portal-button--primary" type="submit"${canCreate ? "" : " disabled"}>Tạo voice direction</button></div></form></section>${renderVoiceStudioPolicy(context)}</div>
      <section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Tìm và tiếp tục direction</h2><p class="portal-card-subtitle">Danh sách chỉ có metadata/excerpt thuộc signed account; consent note và script đầy đủ chỉ nạp sau owner check khi mở direction.</p></div><button class="portal-button portal-button--quiet" type="button" data-portal-action="voice-studio-refresh" data-portal-route="/voice-studio">Làm mới</button></div><form class="portal-voice-studio-filter" data-portal-form data-portal-action="voice-studio-filter" data-portal-route="/voice-studio" novalidate>${renderFields(filterFields, true, context, filter)}<div class="portal-form-footer"><span class="portal-form-note">Bộ lọc chỉ tồn tại ở state phiên trang, không vào URL, localStorage, Telegram hoặc provider.</span><div class="portal-inline-actions"><button class="portal-button portal-button--quiet" type="button" data-portal-action="voice-studio-filter-clear" data-portal-route="/voice-studio">Xóa lọc</button><button class="portal-button portal-button--primary" type="submit">Tìm direction</button></div></div></form>${vaultListing}</section>
      <section class="portal-card portal-card-pad portal-voice-studio-activity"><div class="portal-card-header"><div><span class="portal-section-kicker">Audit-safe feed</span><h2 class="portal-card-title">Hoạt động gần đây</h2><p class="portal-card-subtitle">Không có raw script, consent note, raw audio, provider ID, URL preview, job, Xu hoặc payment trong feed này.</p></div><span class="portal-form-note">${safeText(String(execution.authoring || "authoring_only"))}</span></div>${eventMarkup}</section>
    </article>`;
  }
  function renderVoiceCueSheet(cue, scriptId) {
    if (!cue || typeof cue !== "object" || String(cue.script_id || "") !== String(scriptId || "") || cue.execution !== "local_deterministic_writing_aid" || cue.provider_called !== false || cue.audio_created !== false) return "";
    const metrics = cue.metrics && typeof cue.metrics === "object" ? cue.metrics : {};
    const entries = Array.isArray(cue.items) ? cue.items.filter((item) => item && typeof item === "object").slice(0, 200) : [];
    const timing = (value) => Number.isFinite(Number(value)) ? `${Number(value).toFixed(2)}s` : "—";
    return `<section class="portal-voice-cue-sheet"><div class="portal-card-header"><div><span class="portal-section-kicker">Local deterministic writing aid</span><h4>Cue-sheet để review nhịp lời thoại</h4><p>Ước lượng theo text và WPM, không phải transcript, audio preview, SRT hoặc output TTS.</p></div>${badge("read_only")}</div><div class="portal-voice-cue-metrics"><span>${safeText(String(metrics.words || 0))} từ</span><span>${safeText(String(metrics.sentences || 0))} câu</span><span>~${safeText(String(metrics.estimated_seconds || 0))} giây</span><span>${safeText(String(metrics.pace_wpm || "—"))} WPM</span></div>${entries.length ? `<ol>${entries.map((item) => `<li><span>${safeText(String(item.index || "•"))}</span><time>${safeText(timing(item.start_seconds))}–${safeText(timing(item.end_seconds))}</time><p>${safeText(String(item.text || ""))}</p><small>${safeText(String(item.word_count || 0))} từ</small></li>`).join("")}</ol>` : `<p class="portal-form-note">Script chưa có câu nào để chia cue.</p>`}</section>`;
  }
  function renderVoiceScriptCard(script, vault, context, route) {
    const scriptId = String(script.id || "");
    const active = String(script.state || "active") === "active";
    const vaultActive = String(vault.state || "active") === "active";
    const consentRevoked = String(vault.vault_kind || "") === "consented_reference" && String(vault.consent_status || "") === "revoked";
    const canUpdate = Boolean(context.capabilities && context.capabilities["voice-script-update"] === true && active && vaultActive && !consentRevoked);
    const canArchive = Boolean(context.capabilities && context.capabilities["voice-script-archive"] === true && active && vaultActive);
    const canRestore = Boolean(context.capabilities && context.capabilities["voice-script-restore"] === true && !active && vaultActive && !consentRevoked);
    const canDuplicate = Boolean(context.capabilities && context.capabilities["voice-script-duplicate"] === true && active && vaultActive && !consentRevoked);
    const canRestoreVersion = Boolean(context.capabilities && context.capabilities["voice-script-restore-version"] === true && active && vaultActive && !consentRevoked);
    const canCueSheet = Boolean(context.capabilities && context.capabilities["voice-script-cue-sheet"] === true && active && vaultActive && !consentRevoked);
    const scriptVersions = Array.isArray(script.versions) ? script.versions.filter((item) => item && Number.isInteger(Number(item.revision))).slice(0, 50) : [];
    const policy = script.policy && typeof script.policy === "object" ? script.policy : {};
    const stateAction = active
      ? `<button class="portal-button portal-button--quiet" type="button" data-portal-action="voice-script-archive" data-portal-route="${safeText(route)}" data-voice-vault-id="${safeText(String(vault.id))}" data-voice-vault-revision="${safeText(String(vault.revision))}" data-voice-script-id="${safeText(scriptId)}" data-voice-script-revision="${safeText(String(script.revision))}" data-portal-confirm="Archive script này? Nội dung và lịch sử vẫn giữ riêng tư cho đến khi khôi phục."${canArchive ? "" : " disabled"}>Archive</button>`
      : `<button class="portal-button portal-button--quiet" type="button" data-portal-action="voice-script-restore" data-portal-route="${safeText(route)}" data-voice-vault-id="${safeText(String(vault.id))}" data-voice-vault-revision="${safeText(String(vault.revision))}" data-voice-script-id="${safeText(scriptId)}" data-voice-script-revision="${safeText(String(script.revision))}"${canRestore ? "" : " disabled"}>Khôi phục</button>`;
    const versionMarkup = scriptVersions.length ? `<div class="portal-voice-script-history"><strong>Lịch sử script</strong>${scriptVersions.map((version) => `<div><span>v${safeText(String(version.revision))} · ${safeText(String(version.created_at || "—"))}</span>${Number(version.revision) === Number(script.revision) ? "<em>Đang mở</em>" : `<button class="portal-button portal-button--quiet" type="button" data-portal-action="voice-script-restore-version" data-portal-route="${safeText(route)}" data-voice-vault-id="${safeText(String(vault.id))}" data-voice-vault-revision="${safeText(String(vault.revision))}" data-voice-script-id="${safeText(scriptId)}" data-voice-script-revision="${safeText(String(script.revision))}" data-voice-script-version="${safeText(String(version.revision))}" data-portal-confirm="Khôi phục v${safeText(String(version.revision))} thành một revision script mới?"${canRestoreVersion ? "" : " disabled"}>Khôi phục v${safeText(String(version.revision))}</button>`}</div>`).join("")}</div>` : "";
    const guard = policy.status === "guarded" ? `<div class="portal-notice portal-notice--warning"><span class="portal-notice-icon" aria-hidden="true">!</span><div><strong>Script cần review direction</strong><p>Loại bỏ yêu cầu mô phỏng hoặc nhái giọng trước khi lưu. Voice Studio không đánh giá hay tự xác nhận quyền.</p></div></div>` : "";
    return `<article class="portal-voice-script-card"><div class="portal-card-header"><div><span class="portal-section-kicker">${safeText(voiceStudioScriptKindLabel(script.script_kind))} · ${safeText(String(script.source_kind || "manual").replace(/_/g, " "))}</span><h3 class="portal-card-title">${safeText(String(script.title || "Voice script"))}</h3><p class="portal-card-subtitle">${safeText(String(script.script_excerpt || "Chưa có lời thoại hiển thị."))}</p></div>${badge(active ? "ready" : "read_only")}</div><div class="portal-voice-script-meta"><span>${safeText(String(script.language || "vi"))}</span><span>${safeText(String(script.metrics && script.metrics.words || 0))} từ</span><span>~${safeText(String(script.metrics && script.metrics.estimated_seconds || 0))} giây</span><span>v${safeText(String(script.revision || 1))}</span></div>${renderVoiceStudioTags(script.tags)}${guard}<div class="portal-inline-actions"><button class="portal-button portal-button--quiet" type="button" data-portal-action="voice-script-cue-sheet" data-portal-route="${safeText(route)}" data-voice-vault-id="${safeText(String(vault.id))}" data-voice-vault-revision="${safeText(String(vault.revision))}" data-voice-script-id="${safeText(scriptId)}" data-voice-script-revision="${safeText(String(script.revision))}"${canCueSheet ? "" : " disabled"}>Xem cue-sheet</button>${stateAction}<button class="portal-button portal-button--quiet" type="button" data-portal-action="voice-script-duplicate" data-portal-route="${safeText(route)}" data-voice-vault-id="${safeText(String(vault.id))}" data-voice-vault-revision="${safeText(String(vault.revision))}" data-voice-script-id="${safeText(scriptId)}" data-voice-script-revision="${safeText(String(script.revision))}"${canDuplicate ? "" : " disabled"}>Nhân bản script</button></div><form class="portal-form portal-voice-script-form" data-portal-form data-portal-action="voice-script-update" data-portal-route="${safeText(route)}" data-voice-vault-id="${safeText(String(vault.id))}" data-voice-vault-revision="${safeText(String(vault.revision))}" data-voice-script-id="${safeText(scriptId)}" data-voice-script-revision="${safeText(String(script.revision))}" novalidate>${renderFields(voiceStudioScriptFields(), canUpdate, context, voiceStudioScriptValues(script))}<div class="portal-form-footer"><span class="portal-form-note">Lưu script không gửi text tới TTS, clone, preview, provider hoặc Job Center.</span><button class="portal-button portal-button--primary" type="submit"${canUpdate ? "" : " disabled"}>Lưu revision script</button></div></form>${renderVoiceCueSheet(context.voiceCueSheet, scriptId)}${versionMarkup}</article>`;
  }
  function renderVoiceStudioDetail(page, context) {
    const detail = context.voiceVaultDetail && typeof context.voiceVaultDetail === "object" ? context.voiceVaultDetail : {};
    const vault = detail.vault && typeof detail.vault === "object" && validVoiceVaultId(detail.vault.id) && String(detail.vault.id) === String(page.recordId || "") ? detail.vault : null;
    const canView = Boolean(context.capabilities && context.capabilities["voice-studio-view"] === true);
    if (!canView || !vault) {
      const readState = String(context.voiceStudioReadState || "guarded");
      const title = !canView ? "Voice Studio đang được bảo vệ" : readState === "loading" ? "Đang nạp voice direction riêng tư" : readState === "failed" ? "Chưa thể nạp voice direction" : readState === "guarded" ? "Voice direction đang ở chế độ an toàn" : "Không tìm thấy voice direction";
      const text = !canView
        ? "Đăng nhập bằng signed session để mở metadata và script riêng tư. Web không fallback sang Bot Voice Vault."
        : readState === "loading"
          ? "Chờ server xác minh owner trước khi hiển thị consent metadata hoặc script."
          : readState === "failed" || readState === "guarded"
            ? "Dữ liệu cũ không được giữ lại hoặc thay bằng dữ liệu Bot khi signed API chưa sẵn sàng."
            : "Direction có thể không thuộc Web account hiện tại hoặc đã bị gỡ; Web sẽ không fallback sang Bot Voice Vault.";
      return `<article class="portal-page portal-voice-studio-detail">${renderHero(page, context)}<section class="portal-card portal-card-pad">${renderEmpty(title, text, ICONS.voice)}<div class="portal-form-footer"><a class="portal-button portal-button--primary" href="/voice-studio">Về Voice Studio</a></div></section></article>`;
    }
    const route = page.routePath || page.path;
    const writable = String(vault.state || "active") === "active";
    const consentRevoked = String(vault.vault_kind || "") === "consented_reference" && String(vault.consent_status || "") === "revoked";
    const canUpdate = Boolean(context.capabilities && context.capabilities["voice-vault-update"] === true && writable);
    const canArchive = Boolean(context.capabilities && context.capabilities["voice-vault-archive"] === true && writable);
    const canRestore = Boolean(context.capabilities && context.capabilities["voice-vault-restore"] === true && !writable);
    const canDuplicate = Boolean(context.capabilities && context.capabilities["voice-vault-duplicate"] === true && writable && !consentRevoked);
    const canRestoreVersion = Boolean(context.capabilities && context.capabilities["voice-vault-restore-version"] === true && writable);
    const canCompose = Boolean(context.capabilities && context.capabilities["voice-vault-compose"] === true && writable && !consentRevoked);
    const canScriptCreate = Boolean(context.capabilities && context.capabilities["voice-script-create"] === true && writable && !consentRevoked);
    const scripts = Array.isArray(detail.scripts) ? detail.scripts.filter((item) => item && validVoiceVaultId(item.id)).slice(0, 250) : [];
    const versions = Array.isArray(detail.versions) ? detail.versions.filter((item) => item && Number.isInteger(Number(item.revision))).slice(0, 100) : [];
    const references = detail.references && typeof detail.references === "object" ? detail.references : {};
    const stateAction = writable
      ? `<button class="portal-button portal-button--quiet" type="button" data-portal-action="voice-vault-archive" data-portal-route="${safeText(route)}" data-voice-vault-id="${safeText(String(vault.id))}" data-voice-vault-revision="${safeText(String(vault.revision))}" data-portal-confirm="Archive voice direction này? Direction, script và version history vẫn giữ riêng tư cho đến khi khôi phục."${canArchive ? "" : " disabled"}>Archive direction</button>`
      : `<button class="portal-button portal-button--quiet" type="button" data-portal-action="voice-vault-restore" data-portal-route="${safeText(route)}" data-voice-vault-id="${safeText(String(vault.id))}" data-voice-vault-revision="${safeText(String(vault.revision))}"${canRestore ? "" : " disabled"}>Khôi phục direction</button>`;
    const versionMarkup = versions.length ? `<div class="portal-voice-version-list">${versions.map((version) => `<article><div><strong>v${safeText(String(version.revision))} · ${safeText(String(version.title || "Voice direction"))}</strong><p>${safeText(String(version.style_excerpt || ""))}</p><small>${safeText(String(version.created_at || "—"))}</small></div>${Number(version.revision) === Number(vault.revision) ? "<span class=\"portal-form-note\">Đang mở</span>" : `<button class="portal-button portal-button--quiet" type="button" data-portal-action="voice-vault-restore-version" data-portal-route="${safeText(route)}" data-voice-vault-id="${safeText(String(vault.id))}" data-voice-vault-revision="${safeText(String(vault.revision))}" data-voice-vault-version="${safeText(String(version.revision))}" data-portal-confirm="Khôi phục v${safeText(String(version.revision))} thành một revision direction mới?"${canRestoreVersion ? "" : " disabled"}>Khôi phục v${safeText(String(version.revision))}</button>`}</article>`).join("")}</div>` : renderEmpty("Chưa có history", "Version đầu tiên được tạo khi direction được lưu và không bị ghi đè âm thầm.", "↺");
    const events = Array.isArray(detail.events) ? detail.events.filter((item) => item && typeof item === "object").slice(0, 18) : [];
    const referencesMarkup = [references.project, references.content_brief].filter((item) => item && typeof item === "object").map((item) => `<span>${safeText(String(item.title || "Reference Web"))}</span>`).join("") || "<span>Chưa liên kết reference</span>";
    const consentRevokedNotice = consentRevoked ? `<section class="portal-notice portal-notice--warning"><span class="portal-notice-icon" aria-hidden="true">!</span><div><strong>Consent đã được thu hồi</strong><p>Direction vẫn được giữ để audit. Bạn có thể archive hoặc cập nhật một self-attestation mới; mọi thao tác soạn, nhân bản, cue-sheet và khôi phục script đang bị khóa.</p></div></section>` : "";
    return `<article class="portal-page portal-voice-studio-detail">${renderHero(page, context)}
      <section class="portal-voice-studio-detail-summary"><div><span class="portal-section-kicker">${safeText(voiceStudioVaultKindLabel(vault.vault_kind))}${vault.is_default ? " · Default local" : ""}</span><h2>${safeText(String(vault.title || "Voice direction"))}</h2><p>${safeText(String(vault.style_notes || vault.style_excerpt || "Chưa có mô tả direction."))}</p><div class="portal-voice-reference-list">${referencesMarkup}</div></div><dl><div><dt>Trạng thái</dt><dd>${safeText(writable ? "Đang hoạt động" : "Đã archive")}</dd></div><div><dt>Revision</dt><dd>v${safeText(String(vault.revision || 1))}</dd></div><div><dt>Scripts</dt><dd>${safeText(String(Number(detail.script_count || scripts.length)))}/${safeText(String(Number(detail.script_limit || 250)))}</dd></div></dl></section>${consentRevokedNotice}
      <div class="portal-voice-studio-detail-grid"><section class="portal-card portal-card-pad portal-voice-studio-editor"><div class="portal-card-header"><div><h2 class="portal-card-title">Direction & consent metadata</h2><p class="portal-card-subtitle">Mỗi lần lưu tạo revision mới. Server xác minh owner, CSRF, idempotency, reference và optimistic revision trước khi ghi.</p></div>${badge(writable ? "ready" : "read_only")}</div><form class="portal-form" data-portal-form data-portal-action="voice-vault-update" data-portal-route="${safeText(route)}" data-voice-vault-id="${safeText(String(vault.id))}" data-voice-vault-revision="${safeText(String(vault.revision))}" novalidate>${renderFields(voiceStudioVaultFields(context), canUpdate, context, voiceStudioVaultValues(vault))}<div class="portal-form-footer"><span class="portal-form-note">Default ở đây chỉ là local preference; không chạm default của Bot, TTS hoặc provider.</span><div class="portal-inline-actions">${stateAction}<button class="portal-button portal-button--quiet" type="button" data-portal-action="voice-vault-duplicate" data-portal-route="${safeText(route)}" data-voice-vault-id="${safeText(String(vault.id))}" data-voice-vault-revision="${safeText(String(vault.revision))}"${canDuplicate ? "" : " disabled"}>Nhân bản direction</button><button class="portal-button portal-button--primary" type="submit"${canUpdate ? "" : " disabled"}>Lưu revision mới</button></div></div></form></section>${renderVoiceStudioPolicy(context)}</div>
      <section class="portal-card portal-card-pad portal-voice-studio-composer"><div class="portal-card-header"><div><span class="portal-section-kicker">Local deterministic drafts</span><h2 class="portal-card-title">Tạo 3 khung script để biên tập</h2><p class="portal-card-subtitle">Composer chỉ tạo scaffold text có nhãn rõ ràng. Không phải AI output, audio preview, TTS, clone, job, charge, asset hay delivery.</p></div>${badge(canCompose ? "read_only" : "guarded")}</div><div class="portal-form-footer"><span class="portal-form-note">Các khung được lưu thành script riêng tư để review thủ công; claim và quyền sử dụng vẫn cần được người biên tập xác minh.</span><button class="portal-button portal-button--primary" type="button" data-portal-action="voice-vault-compose" data-portal-route="${safeText(route)}" data-voice-vault-id="${safeText(String(vault.id))}" data-voice-vault-revision="${safeText(String(vault.revision))}"${canCompose ? "" : " disabled"}>Tạo 3 khung script</button></div></section>
      <section class="portal-card portal-card-pad portal-voice-script-create"><div class="portal-card-header"><div><span class="portal-section-kicker">Manual authoring</span><h2 class="portal-card-title">Thêm script thủ công</h2><p class="portal-card-subtitle">Lời thoại được giữ trong signed Web account, có version history và cue-sheet cục bộ. Nó không được gửi tới engine chỉ vì bạn lưu.</p></div>${badge(canScriptCreate ? "ready" : "guarded")}</div><form class="portal-form" data-portal-form data-portal-action="voice-script-create" data-portal-route="${safeText(route)}" data-voice-vault-id="${safeText(String(vault.id))}" data-voice-vault-revision="${safeText(String(vault.revision))}" novalidate>${renderFields(voiceStudioScriptFields(), canScriptCreate, context, { script_kind: "narration", language: String(vault.language || "vi"), pace_wpm: "145" })}<div class="portal-form-footer"><span class="portal-form-note">Không nhập secret, OTP, payment proof, URL provider hoặc chỉ dẫn mô phỏng người cụ thể.</span><button class="portal-button portal-button--primary" type="submit"${canScriptCreate ? "" : " disabled"}>Thêm script</button></div></form></section>
      <section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Scripts & cue-sheet</h2><p class="portal-card-subtitle">Mỗi script có revision riêng. Cue-sheet chỉ xuất hiện khi bạn yêu cầu và chỉ ước lượng thời lượng từ text/WPM.</p></div></div><div class="portal-voice-script-grid">${scripts.length ? scripts.map((script) => renderVoiceScriptCard(script, vault, context, route)).join("") : renderEmpty("Chưa có script", "Dùng composer hoặc thêm script thủ công để bắt đầu review. Không có audio được sinh thay thế.", ICONS.voice)}</div></section>
      <div class="portal-voice-studio-history-grid"><section class="portal-card portal-card-pad"><div class="portal-card-header"><div><span class="portal-section-kicker">Version history</span><h2 class="portal-card-title">Lịch sử direction</h2><p class="portal-card-subtitle">Khôi phục tạo revision mới và không xoá lịch sử cũ.</p></div></div>${versionMarkup}</section><section class="portal-card portal-card-pad portal-voice-studio-activity"><div class="portal-card-header"><div><span class="portal-section-kicker">Audit-safe feed</span><h2 class="portal-card-title">Hoạt động trong direction</h2><p class="portal-card-subtitle">Feed chỉ hiển thị nhãn thao tác, revision và thời điểm; không có raw script hoặc consent note.</p></div></div>${events.length ? `<div class="portal-voice-studio-events">${events.map((item) => `<div><span aria-hidden="true">•</span><span><strong>${safeText(voiceStudioEventLabel(item.action))}</strong><small>v${safeText(String(item.revision || 1))} · ${safeText(String(item.created_at || "—"))}</small></span></div>`).join("")}</div>` : "<p class=\"portal-form-note\">Chưa có hoạt động được ghi nhận.</p>"}</section></div>
      <section class="portal-card portal-card-pad portal-voice-studio-boundary"><div class="portal-card-header"><div><span class="portal-section-kicker">Provider / delivery boundary</span><h2 class="portal-card-title">Không có audio giả trong Voice Studio</h2><p class="portal-card-subtitle">TTS, voice clone, preview, saved voice, raw audio upload và delivery phải đi qua contract riêng. Workspace này sẽ hiển thị guarded thay vì tạo player, URL hoặc output giả.</p></div>${badge("guarded")}</div>${renderNotes(page)}</section>
    </article>`;
  }

  // Video Production Studio is a Web-native plan-and-review surface.  Its
  // data model deliberately stops at creative planning: no media source,
  // renderer configuration, output URL or delivery record belongs here.
  const VIDEO_STUDIO_FORMATS = Object.freeze([
    ["short_form", "Short-form"], ["product_demo", "Product demo"], ["explainer", "Explainer"],
    ["ugc", "UGC concept"], ["campaign", "Campaign"], ["custom", "Tùy chỉnh"]
  ]);
  const VIDEO_STUDIO_ASPECT_RATIOS = Object.freeze([
    ["9:16", "9:16 · Dọc"], ["16:9", "16:9 · Ngang"], ["1:1", "1:1 · Vuông"],
    ["4:5", "4:5 · Feed"], ["custom", "Tỷ lệ tùy chỉnh"]
  ]);
  const VIDEO_STUDIO_SCENE_TYPES = Object.freeze([
    ["hook", "Hook"], ["problem", "Vấn đề"], ["solution", "Giải pháp"], ["product", "Sản phẩm"],
    ["proof", "Bằng chứng"], ["cta", "CTA"], ["transition", "Chuyển cảnh"], ["custom", "Tùy chỉnh"]
  ]);
  const VIDEO_STUDIO_PLAN_STATE_LABELS = Object.freeze({
    draft: "Bản nháp", review: "Đang self-review", approved: "Self-review hoàn tất", archived: "Đã archive"
  });

  function validVideoStudioPlanId(value) { return validProjectId(value); }
  function validVideoStudioSceneId(value) { return validProjectId(value); }
  function videoStudioFormatLabel(value) {
    const found = VIDEO_STUDIO_FORMATS.find(([key]) => key === String(value || ""));
    return found ? found[1] : "Video plan";
  }
  function videoStudioSceneTypeLabel(value) {
    const found = VIDEO_STUDIO_SCENE_TYPES.find(([key]) => key === String(value || ""));
    return found ? found[1] : "Scene";
  }
  function videoStudioPlanStateLabel(value) {
    return VIDEO_STUDIO_PLAN_STATE_LABELS[String(value || "")] || "Được bảo vệ";
  }
  function videoStudioPlanStateBadge(value) {
    const state = ["draft", "review", "approved", "archived"].includes(String(value || "")) ? String(value) : "guarded";
    return `<span class="portal-badge" data-status="${safeText(state)}">${safeText(videoStudioPlanStateLabel(state))}</span>`;
  }
  function videoStudioTags(value) {
    return Array.isArray(value) ? value.filter((item) => typeof item === "string" && item.trim()).slice(0, 20) : [];
  }
  function renderVideoStudioTags(value) {
    const tags = videoStudioTags(value);
    return tags.length ? `<div class="portal-video-studio-tags">${tags.map((tag) => `<span>${safeText(tag)}</span>`).join("")}</div>` : "";
  }
  function videoStudioReferenceOptions(context) {
    const refs = context && context.videoStudioReferences && typeof context.videoStudioReferences === "object" ? context.videoStudioReferences : {};
    const projects = Array.isArray(refs.projects) ? refs.projects : [];
    return projects.filter((item) => item && validVideoStudioPlanId(item.id)).slice(0, 100)
      .map((item) => ({ value: String(item.id), label: String(item.title || "Project Web riêng tư") }));
  }
  function videoStudioPlanFields(context) {
    return [
      { name: "title", label: "Tên video plan", placeholder: "Ví dụ: Launch bộ sưu tập mùa hè", required: true, minLength: 2, maxLength: 180 },
      { name: "format", label: "Loại kế hoạch", control: "select", required: true, options: VIDEO_STUDIO_FORMATS },
      { name: "language", label: "Ngôn ngữ", placeholder: "vi", required: true, minLength: 1, maxLength: 100 },
      { name: "aspect_ratio", label: "Tỷ lệ khung hình", control: "select", required: true, options: VIDEO_STUDIO_ASPECT_RATIOS },
      { name: "target_duration_seconds", label: "Thời lượng mục tiêu (giây)", type: "number", required: true, min: 1, max: 7200, step: 1, inputMode: "numeric", help: "Đây là mục tiêu biên tập để kiểm tra nhịp scene, không phải thời lượng media đã được tạo." },
      { name: "objective", label: "Mục tiêu", placeholder: "Ví dụ: giúp khách mới hiểu lợi ích trong 30 giây", maxLength: 1200, wide: true },
      { name: "audience", label: "Đối tượng", placeholder: "Ví dụ: người mới tìm hiểu sản phẩm", maxLength: 1200, wide: true },
      { name: "brief", label: "Creative brief", control: "textarea", placeholder: "Thông điệp, bối cảnh, ràng buộc thương hiệu và điểm cần tự rà soát…", required: true, minLength: 3, maxLength: 12000, wide: true },
      { name: "tags", label: "Tags", placeholder: "launch, product, review", maxLength: 1000 },
      { name: "project_id", label: "Project (tùy chọn)", control: "select", options: videoStudioReferenceOptions(context), emptyLabel: "Không liên kết Project" }
    ];
  }
  function videoStudioPlanValues(value) {
    const source = value && typeof value === "object" ? value : {};
    const format = String(source.format || "");
    const ratio = String(source.aspect_ratio || "");
    const duration = Number(source.target_duration_seconds);
    return {
      title: String(source.title || ""), format: VIDEO_STUDIO_FORMATS.some(([key]) => key === format) ? format : "short_form",
      language: String(source.language || "vi"), aspect_ratio: VIDEO_STUDIO_ASPECT_RATIOS.some(([key]) => key === ratio) ? ratio : "9:16",
      target_duration_seconds: Number.isInteger(duration) && duration >= 1 && duration <= 7200 ? String(duration) : "30",
      objective: String(source.objective || ""), audience: String(source.audience || ""), brief: String(source.brief || source.brief_text || ""),
      tags: videoStudioTags(source.tags).join(", "), project_id: String(source.project_id || "")
    };
  }
  function videoStudioSceneFields() {
    return [
      { name: "title", label: "Tên scene", placeholder: "Ví dụ: Hook mở đầu", required: true, minLength: 2, maxLength: 180 },
      { name: "scene_type", label: "Vai trò scene", control: "select", required: true, options: VIDEO_STUDIO_SCENE_TYPES },
      { name: "duration_seconds", label: "Thời lượng ước lượng (giây)", type: "number", required: true, min: 1, max: 1800, step: 1, inputMode: "numeric" },
      { name: "visual_direction", label: "Visual direction", control: "textarea", placeholder: "Khung hình, bố cục, nhịp và thông tin phải có để biên tập…", maxLength: 5000, wide: true },
      { name: "narration", label: "Narration / thoại", control: "textarea", placeholder: "Nội dung dự kiến cần truyền đạt ở scene này…", maxLength: 5000, wide: true },
      { name: "on_screen_text", label: "Text trên màn hình", control: "textarea", placeholder: "Thông điệp ngắn cần hiển thị (nếu có)…", maxLength: 3000, wide: true },
      { name: "shot_notes", label: "Ghi chú quay dựng", control: "textarea", placeholder: "Góc máy, nhịp chuyển, điều cần tránh hoặc điểm review…", maxLength: 5000, wide: true },
      { name: "transition", label: "Chuyển cảnh", placeholder: "Ví dụ: cut theo beat, dissolve nhẹ", maxLength: 500 },
      { name: "tags", label: "Tags", placeholder: "hook, product, cta", maxLength: 1000 }
    ];
  }
  function videoStudioSceneValues(value) {
    const source = value && typeof value === "object" ? value : {};
    const type = String(source.scene_type || "");
    const duration = Number(source.duration_seconds);
    return {
      title: String(source.title || ""), scene_type: VIDEO_STUDIO_SCENE_TYPES.some(([key]) => key === type) ? type : "custom",
      duration_seconds: Number.isInteger(duration) && duration >= 1 && duration <= 1800 ? String(duration) : "5",
      visual_direction: String(source.visual_direction || ""), narration: String(source.narration || ""), on_screen_text: String(source.on_screen_text || ""),
      shot_notes: String(source.shot_notes || ""), transition: String(source.transition || ""), tags: videoStudioTags(source.tags).join(", ")
    };
  }
  function videoStudioEventLabel(value) {
    const labels = {
      plan_created: "Đã tạo video plan", plan_updated: "Đã lưu video plan", plan_state_changed: "Đã đổi trạng thái review", plan_version_restored: "Đã khôi phục version plan",
      scene_created: "Đã thêm scene", scene_updated: "Đã lưu scene", scene_archived: "Đã archive scene", scene_restored: "Đã khôi phục scene", scene_version_restored: "Đã khôi phục version scene", scenes_reordered: "Đã sắp xếp scene"
    };
    return labels[String(value || "")] || String(value || "video_studio_updated").replace(/_/g, " ");
  }
  function renderVideoStudioBoundary() {
    return `<aside class="portal-card portal-card-pad portal-video-studio-boundary"><div class="portal-card-header"><div><span class="portal-section-kicker">Authoring boundary</span><h2 class="portal-card-title">Plan & review, không tạo media</h2><p class="portal-card-subtitle">Workspace chỉ lưu brief, scene và self-review thuộc Web account. Không có upload, renderer, player, URL media, tệp hoặc delivery được tạo từ trang này.</p></div>${badge("guarded")}</div><div class="portal-video-studio-guard-list"><span><strong>Media generation</strong><em>guarded</em></span><span><strong>Media render</strong><em>guarded</em></span><span><strong>Media delivery</strong><em>guarded</em></span></div></aside>`;
  }
  function renderVideoPlanCards(items, context) {
    const canView = Boolean(context.capabilities && context.capabilities["video-studio-view"] === true);
    if (!items.length) return renderEmpty("Chưa có video plan", "Tạo plan đầu tiên để tổ chức brief, scene và self-review. Workspace không sinh media hay kết quả thay thế.", ICONS.video);
    return `<div class="portal-video-plan-grid">${items.map((item) => {
      const id = String(item.id || "");
      const state = ["draft", "review", "approved", "archived"].includes(String(item.state || "")) ? String(item.state) : "guarded";
      const duration = Number(item.target_duration_seconds || 0);
      return `<article class="portal-card portal-card-pad portal-video-plan-card"><div class="portal-card-header"><div><span class="portal-section-kicker">${safeText(videoStudioFormatLabel(item.format))}</span><h3 class="portal-card-title">${safeText(String(item.title || "Video plan"))}</h3><p class="portal-card-subtitle">${safeText(String(item.brief_excerpt || item.objective || "Chưa có brief hiển thị."))}</p></div>${videoStudioPlanStateBadge(state)}</div><div class="portal-video-plan-meta"><span>${safeText(String(item.aspect_ratio || "—"))}</span><span>${duration > 0 ? `~${safeText(String(duration))} giây` : "Chưa có thời lượng"}</span><span>${safeText(String(item.scene_count || 0))} scenes</span><span>v${safeText(String(item.revision || 1))}</span></div>${renderVideoStudioTags(item.tags)}<div class="portal-form-footer"><span class="portal-form-note">${state === "approved" ? "Self-review đã đánh dấu" : state === "archived" ? "Đã archive · chỉ đọc" : "Đang biên tập"}</span>${canView && validVideoStudioPlanId(id) ? `<a class="portal-button portal-button--quiet" href="/video-studio/${encodeURIComponent(id)}">Mở plan <span aria-hidden="true">→</span></a>` : ""}</div></article>`;
    }).join("")}</div>`;
  }
  function renderVideoStudio(page, context) {
    const canView = Boolean(context.capabilities && context.capabilities["video-studio-view"] === true);
    const canCreate = Boolean(context.capabilities && context.capabilities["video-plan-create"] === true);
    if (!canView) return `<article class="portal-page portal-video-studio">${renderHero(page, context)}<section class="portal-card portal-card-pad">${renderEmpty("Video Production Studio đang được bảo vệ", "Đăng nhập bằng signed session để mở các video plan riêng tư. Route này không dùng dữ liệu từ legacy video workflow.", ICONS.video)}</section></article>`;
    const summary = context.videoStudioSummary && typeof context.videoStudioSummary === "object" ? context.videoStudioSummary : {};
    const plansSummary = summary.plans && typeof summary.plans === "object" ? summary.plans : {};
    const plans = Array.isArray(context.videoPlans) ? context.videoPlans.filter((item) => item && validVideoStudioPlanId(item.id)).slice(0, 100) : [];
    const formValues = videoStudioPlanValues(transientFormValues(page.routePath || page.path));
    const total = Number(plansSummary.total || plans.length);
    const inReview = Number(plansSummary.review || 0);
    const approved = Number(plansSummary.approved || 0);
    return `<article class="portal-page portal-video-studio">${renderHero(page, context)}
      <section class="portal-video-studio-intro"><div><span class="portal-section-kicker">Web-native production planning</span><h2>Đi từ creative brief đến scene review, có kiểm soát.</h2><p>Tổ chức video plan, nhịp scene và self-review trong một không gian riêng tư. Các số liệu ở đây là metadata biên tập, không phải media đã được tạo hoặc xác minh.</p></div><dl><div><dt>${safeText(String(total))}</dt><dd>Video plans</dd></div><div><dt>${safeText(String(inReview))}</dt><dd>Đang review</dd></div><div><dt>${safeText(String(approved))}</dt><dd>Self-review xong</dd></div></dl></section>
      <div class="portal-video-studio-layout"><section class="portal-card portal-card-pad portal-video-studio-create"><div class="portal-card-header"><div><span class="portal-section-kicker">New production plan</span><h2 class="portal-card-title">Lập video plan</h2><p class="portal-card-subtitle">Bắt đầu bằng mục tiêu, audience, format, tỷ lệ và brief. Mỗi lần ghi được server kiểm tra phiên, CSRF, ownership, revision và idempotency.</p></div>${badge(canCreate ? "ready" : "guarded")}</div><form class="portal-form" data-portal-form data-portal-action="video-plan-create" data-portal-route="${safeText(page.routePath || page.path)}" novalidate>${renderFields(videoStudioPlanFields(context), canCreate, context, formValues)}<div class="portal-form-footer"><span class="portal-form-note">Không nhập secret, chứng từ thanh toán, URL media hoặc dữ liệu riêng tư không cần thiết.</span><button class="portal-button portal-button--primary" type="submit"${canCreate ? "" : " disabled"}>Tạo video plan</button></div></form></section>${renderVideoStudioBoundary()}</div>
      <section class="portal-card portal-card-pad"><div class="portal-card-header"><div><span class="portal-section-kicker">Plan library</span><h2 class="portal-card-title">Tiếp tục công việc</h2><p class="portal-card-subtitle">Danh sách chỉ hiển thị metadata/excerpt thuộc signed account. Mở plan để nạp scene, estimate và history sau owner check.</p></div><button class="portal-button portal-button--quiet" type="button" data-portal-action="video-studio-refresh" data-portal-route="/video-studio">Làm mới</button></div>${renderVideoPlanCards(plans, context)}</section>
    </article>`;
  }
  function videoRuntimeEstimateMarkup(estimate) {
    const source = estimate && typeof estimate === "object" ? estimate : {};
    const target = Number(source.target_duration_seconds || source.target_seconds || 0);
    const sceneTotal = Number(source.scene_duration_seconds || source.total_scene_duration_seconds || source.scene_seconds || 0);
    const delta = Number(source.delta_seconds || (target > 0 && sceneTotal >= 0 ? sceneTotal - target : NaN));
    const status = String(source.status || (target > 0 ? "ready" : "guarded"));
    const deltaText = Number.isFinite(delta) ? `${delta > 0 ? "+" : ""}${delta} giây` : "Chưa có so sánh";
    return `<section class="portal-card portal-card-pad portal-video-runtime-estimate"><div class="portal-card-header"><div><span class="portal-section-kicker">Runtime estimate</span><h2 class="portal-card-title">Kiểm tra nhịp scene</h2><p class="portal-card-subtitle">Estimate chỉ cộng metadata thời lượng của plan và scene để hỗ trợ review. Nó không suy diễn hay xác nhận media.</p></div>${badge(["ready", "guarded", "review"].includes(status) ? status : "guarded")}</div><div class="portal-video-runtime-grid"><div><small>Target</small><strong>${target > 0 ? `${safeText(String(target))} giây` : "Chưa khai báo"}</strong></div><div><small>Tổng scene</small><strong>${sceneTotal > 0 ? `${safeText(String(sceneTotal))} giây` : "Chưa có scene"}</strong></div><div><small>Chênh lệch</small><strong>${safeText(deltaText)}</strong></div></div></section>`;
  }
  function renderVideoSceneCard(scene, plan, context, route, order, total) {
    const sceneId = String(scene.id || "");
    const active = String(scene.state || "active") === "active";
    const displayOrder = active && Number.isInteger(order) && order >= 0 ? String(order + 1).padStart(2, "0") : "—";
    const planWritable = ["draft", "review"].includes(String(plan.state || ""));
    const canUpdate = Boolean(context.capabilities && context.capabilities["video-scene-update"] === true && active && planWritable);
    const canArchive = Boolean(context.capabilities && context.capabilities["video-scene-archive"] === true && active && planWritable);
    const canRestore = Boolean(context.capabilities && context.capabilities["video-scene-restore"] === true && !active && planWritable);
    const canRestoreVersion = Boolean(context.capabilities && context.capabilities["video-scene-restore-version"] === true && active && planWritable);
    const canReorder = Boolean(context.capabilities && context.capabilities["video-scene-reorder"] === true && active && planWritable);
    const versions = Array.isArray(scene.versions) ? scene.versions.filter((item) => item && Number.isInteger(Number(item.revision))).slice(0, 20) : [];
    const stateAction = active
      ? `<button class="portal-button portal-button--quiet" type="button" data-portal-action="video-scene-archive" data-portal-route="${safeText(route)}" data-video-plan-id="${safeText(String(plan.id))}" data-video-plan-revision="${safeText(String(plan.revision))}" data-video-scene-id="${safeText(sceneId)}" data-video-scene-revision="${safeText(String(scene.revision))}" data-portal-confirm="Archive scene này? History riêng tư vẫn được giữ để khôi phục."${canArchive ? "" : " disabled"}>Archive</button>`
      : `<button class="portal-button portal-button--quiet" type="button" data-portal-action="video-scene-restore" data-portal-route="${safeText(route)}" data-video-plan-id="${safeText(String(plan.id))}" data-video-plan-revision="${safeText(String(plan.revision))}" data-video-scene-id="${safeText(sceneId)}" data-video-scene-revision="${safeText(String(scene.revision))}"${canRestore ? "" : " disabled"}>Khôi phục</button>`;
    const versionsMarkup = versions.length ? `<div class="portal-video-scene-history"><strong>Lịch sử scene</strong>${versions.map((version) => `<div><span>v${safeText(String(version.revision))} · ${safeText(String(version.created_at || "—"))}</span>${Number(version.revision) === Number(scene.revision) ? "<em>Đang mở</em>" : `<button class="portal-button portal-button--quiet" type="button" data-portal-action="video-scene-restore-version" data-portal-route="${safeText(route)}" data-video-plan-id="${safeText(String(plan.id))}" data-video-plan-revision="${safeText(String(plan.revision))}" data-video-scene-id="${safeText(sceneId)}" data-video-scene-revision="${safeText(String(scene.revision))}" data-video-scene-version="${safeText(String(version.revision))}" data-portal-confirm="Khôi phục v${safeText(String(version.revision))} thành một revision scene mới?"${canRestoreVersion ? "" : " disabled"}>Khôi phục v${safeText(String(version.revision))}</button>`}</div>`).join("")}</div>` : "";
    return `<article class="portal-video-scene-card${active ? "" : " is-archived"}"><div class="portal-card-header"><div><span class="portal-section-kicker">${safeText(displayOrder)} · ${safeText(videoStudioSceneTypeLabel(scene.scene_type))}</span><h3 class="portal-card-title">${safeText(String(scene.title || "Scene"))}</h3><p class="portal-card-subtitle">${safeText(String(scene.visual_direction || scene.narration || "Chưa có direction hiển thị."))}</p></div>${badge(active ? "ready" : "archived")}</div><div class="portal-video-scene-meta"><span>~${safeText(String(scene.duration_seconds || 0))} giây</span><span>v${safeText(String(scene.revision || 1))}</span><span>${safeText(String(scene.transition || "Không transition"))}</span></div>${renderVideoStudioTags(scene.tags)}<div class="portal-inline-actions"><button class="portal-button portal-button--quiet" type="button" data-portal-action="video-scene-reorder" data-video-scene-direction="up" data-portal-route="${safeText(route)}" data-video-plan-id="${safeText(String(plan.id))}" data-video-plan-revision="${safeText(String(plan.revision))}" data-video-scene-id="${safeText(sceneId)}"${canReorder && order > 0 ? "" : " disabled"}>↑</button><button class="portal-button portal-button--quiet" type="button" data-portal-action="video-scene-reorder" data-video-scene-direction="down" data-portal-route="${safeText(route)}" data-video-plan-id="${safeText(String(plan.id))}" data-video-plan-revision="${safeText(String(plan.revision))}" data-video-scene-id="${safeText(sceneId)}"${canReorder && order >= 0 && order < total - 1 ? "" : " disabled"}>↓</button>${stateAction}</div><form class="portal-form portal-video-scene-form" data-portal-form data-portal-action="video-scene-update" data-portal-route="${safeText(route)}" data-video-plan-id="${safeText(String(plan.id))}" data-video-plan-revision="${safeText(String(plan.revision))}" data-video-scene-id="${safeText(sceneId)}" data-video-scene-revision="${safeText(String(scene.revision))}" novalidate>${renderFields(videoStudioSceneFields(), canUpdate, context, videoStudioSceneValues(scene))}<div class="portal-form-footer"><span class="portal-form-note">Mỗi lần lưu tạo revision; không biến direction thành media hay kết quả.</span><button class="portal-button portal-button--primary" type="submit"${canUpdate ? "" : " disabled"}>Lưu scene</button></div></form>${versionsMarkup}</article>`;
  }
  function renderVideoStudioDetail(page, context) {
    const detail = context.videoPlanDetail && typeof context.videoPlanDetail === "object" ? context.videoPlanDetail : {};
    const plan = detail.plan && typeof detail.plan === "object" && validVideoStudioPlanId(detail.plan.id) && String(detail.plan.id) === String(page.recordId || "") ? detail.plan : null;
    const canView = Boolean(context.capabilities && context.capabilities["video-studio-view"] === true);
    if (!canView || !plan) {
      const state = String(context.videoStudioReadState || "guarded");
      const title = !canView ? "Video Production Studio đang được bảo vệ" : state === "loading" ? "Đang nạp video plan riêng tư" : state === "failed" ? "Chưa thể nạp video plan" : "Không tìm thấy video plan";
      const text = !canView ? "Đăng nhập bằng signed session để mở plan thuộc account hiện tại." : "Server cần xác minh owner trước khi hiển thị brief, scene và history; dữ liệu cũ không được giữ trong browser.";
      return `<article class="portal-page portal-video-studio-detail">${renderHero(page, context)}<section class="portal-card portal-card-pad">${renderEmpty(title, text, ICONS.video)}<div class="portal-form-footer"><a class="portal-button portal-button--primary" href="/video-studio">Về Video Studio</a></div></section></article>`;
    }
    const route = page.routePath || page.path;
    const planState = ["draft", "review", "approved", "archived"].includes(String(plan.state || "")) ? String(plan.state) : "guarded";
    const writable = ["draft", "review"].includes(planState);
    const canUpdate = Boolean(context.capabilities && context.capabilities["video-plan-update"] === true && writable);
    const canState = Boolean(context.capabilities && context.capabilities["video-plan-lifecycle"] === true && planState !== "archived");
    const canRestoreVersion = Boolean(context.capabilities && context.capabilities["video-plan-restore-version"] === true && writable);
    const canSceneCreate = Boolean(context.capabilities && context.capabilities["video-scene-create"] === true && writable);
    const scenes = Array.isArray(detail.scenes) ? detail.scenes.filter((item) => item && validVideoStudioSceneId(item.id)).slice(0, 250) : [];
    const activeScenes = scenes.filter((item) => String(item.state || "active") === "active");
    const versions = Array.isArray(detail.versions) ? detail.versions.filter((item) => item && Number.isInteger(Number(item.revision))).slice(0, 100) : [];
    const events = Array.isArray(detail.events) ? detail.events.filter((item) => item && typeof item === "object").slice(0, 24) : [];
    const stateActions = planState === "archived"
      ? `<button class="portal-button portal-button--quiet" type="button" data-portal-action="video-plan-state" data-video-plan-state="draft" data-portal-route="${safeText(route)}" data-video-plan-id="${safeText(String(plan.id))}" data-video-plan-revision="${safeText(String(plan.revision))}" data-portal-confirm="Khôi phục plan này về Draft để tiếp tục biên tập?"${Boolean(context.capabilities && context.capabilities["video-plan-lifecycle"] === true) ? "" : " disabled"}>Khôi phục về Draft</button>`
      : `<button class="portal-button portal-button--quiet" type="button" data-portal-action="video-plan-state" data-video-plan-state="${planState === "draft" ? "review" : "draft"}" data-portal-route="${safeText(route)}" data-video-plan-id="${safeText(String(plan.id))}" data-video-plan-revision="${safeText(String(plan.revision))}" data-portal-confirm="${planState === "draft" ? "Chuyển plan sang Self-review?" : "Trả plan về Draft để tiếp tục biên tập?"}"${canState ? "" : " disabled"}>${planState === "draft" ? "Bắt đầu self-review" : "Trả về Draft"}</button><button class="portal-button portal-button--quiet" type="button" data-portal-action="video-plan-state" data-video-plan-state="approved" data-portal-route="${safeText(route)}" data-video-plan-id="${safeText(String(plan.id))}" data-video-plan-revision="${safeText(String(plan.revision))}" data-portal-confirm="Đánh dấu self-review hoàn tất? Điều này không tạo media hoặc delivery."${canState && planState === "review" ? "" : " disabled"}>Đánh dấu review xong</button><button class="portal-button portal-button--quiet" type="button" data-portal-action="video-plan-state" data-video-plan-state="archived" data-portal-route="${safeText(route)}" data-video-plan-id="${safeText(String(plan.id))}" data-video-plan-revision="${safeText(String(plan.revision))}" data-portal-confirm="Archive video plan này? Brief, scene và history vẫn được giữ riêng tư."${canState ? "" : " disabled"}>Archive plan</button>`;
    const versionMarkup = versions.length ? `<div class="portal-video-version-list">${versions.map((version) => `<article><div><strong>v${safeText(String(version.revision))} · ${safeText(String(version.title || "Video plan"))}</strong><p>${safeText(String(version.brief_excerpt || version.objective || ""))}</p><small>${safeText(String(version.created_at || "—"))}</small></div>${Number(version.revision) === Number(plan.revision) ? "<span class=\"portal-form-note\">Đang mở</span>" : `<button class="portal-button portal-button--quiet" type="button" data-portal-action="video-plan-restore-version" data-portal-route="${safeText(route)}" data-video-plan-id="${safeText(String(plan.id))}" data-video-plan-revision="${safeText(String(plan.revision))}" data-video-plan-version="${safeText(String(version.revision))}" data-portal-confirm="Khôi phục v${safeText(String(version.revision))} thành một revision plan mới?"${canRestoreVersion ? "" : " disabled"}>Khôi phục v${safeText(String(version.revision))}</button>`}</article>`).join("")}</div>` : renderEmpty("Chưa có history", "Version đầu tiên xuất hiện khi server lưu video plan.", "↺");
    let activeSceneOrder = 0;
    const sceneMarkup = scenes.length ? scenes.map((scene) => {
      const active = String(scene.state || "active") === "active";
      const order = active ? activeSceneOrder++ : -1;
      return renderVideoSceneCard(scene, plan, context, route, order, activeScenes.length);
    }).join("") : renderEmpty("Chưa có scene", "Thêm scene thủ công để bắt đầu sắp nhịp và self-review.", ICONS.video);
    const estimateMarkup = planState === "archived"
      ? `<section class="portal-card portal-card-pad portal-video-runtime-estimate"><div class="portal-card-header"><div><span class="portal-section-kicker">Runtime estimate</span><h2 class="portal-card-title">Estimate đã được khóa</h2><p class="portal-card-subtitle">Plan đang archive nên scene và estimate không được nạp hay tính lại. Khôi phục về Draft khi bạn muốn tiếp tục review.</p></div>${badge("archived")}</div></section>`
      : videoRuntimeEstimateMarkup(detail.estimate || context.videoPlanEstimate);
    return `<article class="portal-page portal-video-studio-detail">${renderHero(page, context)}
      <section class="portal-video-studio-detail-summary"><div><span class="portal-section-kicker">${safeText(videoStudioFormatLabel(plan.format))}</span><h2>${safeText(String(plan.title || "Video plan"))}</h2><p>${safeText(String(plan.objective || plan.brief_excerpt || "Chưa có mục tiêu hiển thị."))}</p>${renderVideoStudioTags(plan.tags)}</div><dl><div><dt>Trạng thái</dt><dd>${safeText(videoStudioPlanStateLabel(planState))}</dd></div><div><dt>Revision</dt><dd>v${safeText(String(plan.revision || 1))}</dd></div><div><dt>Scenes</dt><dd>${safeText(String(activeScenes.length))}</dd></div></dl></section>
      <div class="portal-video-studio-detail-grid"><section class="portal-card portal-card-pad portal-video-studio-editor"><div class="portal-card-header"><div><span class="portal-section-kicker">Plan editor</span><h2 class="portal-card-title">Brief & review context</h2><p class="portal-card-subtitle">Lưu bằng optimistic revision; self-review và archive là trạng thái server-side, không được browser tự suy diễn.</p></div>${videoStudioPlanStateBadge(planState)}</div><form class="portal-form" data-portal-form data-portal-action="video-plan-update" data-portal-route="${safeText(route)}" data-video-plan-id="${safeText(String(plan.id))}" data-video-plan-revision="${safeText(String(plan.revision))}" novalidate>${renderFields(videoStudioPlanFields(context), canUpdate, context, videoStudioPlanValues(plan))}<div class="portal-form-footer"><span class="portal-form-note">Plan đã approved hoặc archived sẽ khóa editor cho tới khi server xác nhận một trạng thái có thể biên tập.</span><div class="portal-inline-actions">${stateActions}<button class="portal-button portal-button--primary" type="submit"${canUpdate ? "" : " disabled"}>Lưu revision plan</button></div></div></form></section>${estimateMarkup}</div>
      <section class="portal-card portal-card-pad portal-video-scene-create"><div class="portal-card-header"><div><span class="portal-section-kicker">Scene board</span><h2 class="portal-card-title">Thêm scene thủ công</h2><p class="portal-card-subtitle">Mỗi scene có direction, thời lượng và history riêng; thứ tự scene được server kiểm tra lại trước khi lưu.</p></div>${badge(canSceneCreate ? "ready" : "guarded")}</div><form class="portal-form" data-portal-form data-portal-action="video-scene-create" data-portal-route="${safeText(route)}" data-video-plan-id="${safeText(String(plan.id))}" data-video-plan-revision="${safeText(String(plan.revision))}" novalidate>${renderFields(videoStudioSceneFields(), canSceneCreate, context, { scene_type: "hook", duration_seconds: "5" })}<div class="portal-form-footer"><span class="portal-form-note">Scene chỉ là metadata biên tập; không chứa source file, media URL hoặc output.</span><button class="portal-button portal-button--primary" type="submit"${canSceneCreate ? "" : " disabled"}>Thêm scene</button></div></form></section>
      <section class="portal-card portal-card-pad"><div class="portal-card-header"><div><span class="portal-section-kicker">Ordered scene board</span><h2 class="portal-card-title">Scenes & nhịp kể chuyện</h2><p class="portal-card-subtitle">Dùng mũi tên để thay thứ tự active scene. Thao tác gửi toàn bộ sequence cùng revision của plan để tránh ghi đè im lặng.</p></div></div><div class="portal-video-scene-grid">${sceneMarkup}</div></section>
      <div class="portal-video-studio-history-grid"><section class="portal-card portal-card-pad"><div class="portal-card-header"><div><span class="portal-section-kicker">Version history</span><h2 class="portal-card-title">Lịch sử video plan</h2><p class="portal-card-subtitle">Khôi phục version tạo revision mới, không xóa history cũ.</p></div></div>${versionMarkup}</section><section class="portal-card portal-card-pad portal-video-studio-activity"><div class="portal-card-header"><div><span class="portal-section-kicker">Audit-safe feed</span><h2 class="portal-card-title">Hoạt động gần đây</h2><p class="portal-card-subtitle">Feed chỉ hiển thị nhãn, revision và thời điểm; không đưa brief hay scene text vào audit view.</p></div></div>${events.length ? `<div class="portal-video-studio-events">${events.map((item) => `<div><span aria-hidden="true">•</span><span><strong>${safeText(videoStudioEventLabel(item.action))}</strong><small>v${safeText(String(item.revision || 1))} · ${safeText(String(item.created_at || "—"))}</small></span></div>`).join("")}</div>` : "<p class=\"portal-form-note\">Chưa có hoạt động được ghi nhận.</p>"}</section></div>
      ${renderVideoStudioBoundary()}
    </article>`;
  }

  // Image Creative Studio is a signed-account art-direction boundary.  It
  // keeps briefs, owned Asset Vault references, variants and self-review in
  // one place without becoming a proxy for any image provider or output.
  const IMAGE_STUDIO_INTENTS = Object.freeze([
    ["create", "Tạo concept (brief only)"], ["edit", "Chỉnh sửa direction"], ["upscale", "Nâng cấp direction"],
    ["image_to_image", "Image-to-image direction"], ["remove_background", "Tách nền direction"]
  ]);
  const IMAGE_STUDIO_ASPECT_RATIOS = Object.freeze([
    ["1:1", "1:1 · Vuông"], ["4:5", "4:5 · Portrait"], ["3:4", "3:4 · Dọc"], ["16:9", "16:9 · Ngang"],
    ["9:16", "9:16 · Story"], ["3:2", "3:2 · Landscape"], ["2:3", "2:3 · Portrait"], ["custom", "Tỷ lệ tùy chỉnh"]
  ]);
  const IMAGE_STUDIO_OUTPUT_FORMATS = Object.freeze([["png", "PNG · target metadata"], ["jpg", "JPG · target metadata"], ["webp", "WebP · target metadata"]]);
  const IMAGE_STUDIO_STATES = Object.freeze({
    draft: "Bản nháp", review: "Đang self-review", approved: "Self-review hoàn tất", archived: "Đã archive"
  });

  function validImageStudioArtboardId(value) { return validProjectId(value); }
  function validImageStudioDirectionId(value) { return validProjectId(value); }
  function imageStudioIntentLabel(value) {
    const found = IMAGE_STUDIO_INTENTS.find(([key]) => key === String(value || ""));
    return found ? found[1] : "Art direction";
  }
  function imageStudioFormatLabel(value) {
    const found = IMAGE_STUDIO_OUTPUT_FORMATS.find(([key]) => key === String(value || ""));
    return found ? found[1] : "Target metadata";
  }
  function imageStudioState(value) {
    const state = String(value || "").toLowerCase();
    return Object.prototype.hasOwnProperty.call(IMAGE_STUDIO_STATES, state) ? state : "guarded";
  }
  function imageStudioStateBadge(value) {
    const state = imageStudioState(value);
    return `<span class="portal-badge" data-status="${safeText(state)}">${safeText(IMAGE_STUDIO_STATES[state] || "Được bảo vệ")}</span>`;
  }
  function imageStudioTags(value) {
    return Array.isArray(value) ? value.filter((tag) => typeof tag === "string" && tag.trim()).slice(0, 20) : [];
  }
  function renderImageStudioTags(value) {
    const tags = imageStudioTags(value);
    return tags.length ? `<div class="portal-image-studio-tags">${tags.map((tag) => `<span>${safeText(tag)}</span>`).join("")}</div>` : "";
  }
  function imageStudioProjectOptions(context) {
    const refs = context && context.imageStudioReferences && typeof context.imageStudioReferences === "object" ? context.imageStudioReferences : {};
    return (Array.isArray(refs.projects) ? refs.projects : []).filter((item) => item && validImageStudioArtboardId(item.id)).slice(0, 100)
      .map((item) => ({ value: String(item.id), label: String(item.title || "Project Web riêng tư") }));
  }
  function imageStudioAssetOptions(context) {
    const refs = context && context.imageStudioReferences && typeof context.imageStudioReferences === "object" ? context.imageStudioReferences : {};
    return (Array.isArray(refs.image_assets) ? refs.image_assets : []).filter((item) => item && validImageStudioArtboardId(item.id)).slice(0, 100)
      .map((item) => {
        // The Image Studio API intentionally exposes a safe display label,
        // not a client filename/path. Do not revive a legacy filename field
        // if a future payload happens to contain one.
        const label = String(item.display_name || "Ảnh Asset Vault").replace(/\s+/g, " ").trim().slice(0, 160);
        const extension = String(item.extension || "").replace(/^\./, "").toUpperCase();
        return { value: String(item.id), label: extension ? `${label} · ${extension}` : label };
      });
  }
  function imageStudioAssetName(context, assetId) {
    const id = String(assetId || "");
    const refs = context && context.imageStudioReferences && typeof context.imageStudioReferences === "object" ? context.imageStudioReferences : {};
    const asset = (Array.isArray(refs.image_assets) ? refs.image_assets : []).find((item) => item && String(item.id || "") === id);
    if (!asset) return id ? "Asset Vault reference đã chọn" : "Không gắn asset";
    return String(asset.display_name || "Ảnh Asset Vault").replace(/\s+/g, " ").trim().slice(0, 160);
  }
  function imageStudioArtboardFields(context) {
    return [
      { name: "title", label: "Tên artboard", placeholder: "Ví dụ: Key visual bộ sưu tập mùa hè", required: true, minLength: 2, maxLength: 180 },
      { name: "image_intent", label: "Ý định direction", control: "select", required: true, options: IMAGE_STUDIO_INTENTS, help: "Nhãn để tổ chức brief; không gọi engine, provider hoặc tạo ảnh." },
      { name: "language", label: "Ngôn ngữ direction", placeholder: "vi", required: true, minLength: 1, maxLength: 100 },
      { name: "aspect_ratio", label: "Tỷ lệ khung hình", control: "select", required: true, options: IMAGE_STUDIO_ASPECT_RATIOS },
      { name: "output_format", label: "Định dạng đích", control: "select", required: true, options: IMAGE_STUDIO_OUTPUT_FORMATS, help: "Chỉ là metadata cho self-review, không có file đích được tạo." },
      { name: "creative_brief", label: "Creative brief", control: "textarea", placeholder: "Thông điệp, bối cảnh, giới hạn thương hiệu và điểm cần tự rà soát…", required: true, minLength: 3, maxLength: 12000, wide: true },
      { name: "style_direction", label: "Style direction", control: "textarea", placeholder: "Bố cục, ánh sáng, palette, chất liệu và cảm xúc mong muốn…", maxLength: 6000, wide: true },
      { name: "negative_direction", label: "Điều cần tránh", control: "textarea", placeholder: "Các yếu tố không phù hợp với thương hiệu hoặc mục tiêu brief…", maxLength: 4000, wide: true },
      { name: "tags", label: "Tags", placeholder: "launch, product, review", maxLength: 1000 },
      { name: "project_id", label: "Project (tùy chọn)", control: "select", options: imageStudioProjectOptions(context), emptyLabel: "Không liên kết Project" }
    ];
  }
  function imageStudioArtboardValues(value) {
    const source = value && typeof value === "object" ? value : {};
    const intent = String(source.image_intent || "");
    const aspectRatio = String(source.aspect_ratio || "");
    const outputFormat = String(source.output_format || "");
    return {
      title: String(source.title || ""), image_intent: IMAGE_STUDIO_INTENTS.some(([key]) => key === intent) ? intent : "create",
      language: String(source.language || "vi"), aspect_ratio: IMAGE_STUDIO_ASPECT_RATIOS.some(([key]) => key === aspectRatio) ? aspectRatio : "1:1",
      output_format: IMAGE_STUDIO_OUTPUT_FORMATS.some(([key]) => key === outputFormat) ? outputFormat : "png",
      creative_brief: String(source.creative_brief || source.creative_brief_excerpt || source.brief_excerpt || ""), style_direction: String(source.style_direction || ""),
      negative_direction: String(source.negative_direction || ""), tags: imageStudioTags(source.tags).join(", "), project_id: String(source.project_id || "")
    };
  }
  function imageStudioDirectionFields(context) {
    return [
      { name: "title", label: "Tên biến thể direction", placeholder: "Ví dụ: Bản tối giản cho feed", required: true, minLength: 2, maxLength: 180 },
      { name: "operation", label: "Loại biến thể", control: "select", required: true, options: IMAGE_STUDIO_INTENTS, help: "Không chạy thao tác ảnh. Với Edit/Upscale/Image-to-image/Tách nền, hãy chọn ảnh gốc trong Asset Vault." },
      { name: "asset_id", label: "Ảnh gốc từ Asset Vault", control: "select", options: imageStudioAssetOptions(context), emptyLabel: "Không dùng ảnh gốc (chỉ phù hợp Create)", help: "Chỉ có metadata của ảnh thuộc account hiện tại; không có thumbnail, blob hay URL công khai." },
      { name: "reference_asset_id", label: "Ảnh tham chiếu (tùy chọn)", control: "select", options: imageStudioAssetOptions(context), emptyLabel: "Không thêm ảnh tham chiếu" },
      { name: "prompt_text", label: "Prompt / concept text", control: "textarea", placeholder: "Mô tả concept, đối tượng và thông điệp cần được biên tập…", maxLength: 12000, wide: true },
      { name: "edit_instructions", label: "Chỉ dẫn chỉnh sửa", control: "textarea", placeholder: "Những thay đổi cần review nếu direction dựa trên ảnh Asset Vault…", maxLength: 6000, wide: true },
      { name: "composition_notes", label: "Bố cục & visual notes", control: "textarea", placeholder: "Vị trí chủ thể, crop, ánh sáng, khoảng trống, hệ chữ…", maxLength: 6000, wide: true },
      { name: "negative_direction", label: "Điều cần tránh", control: "textarea", placeholder: "Các yếu tố không nên xuất hiện trong direction này…", maxLength: 4000, wide: true },
      { name: "tags", label: "Tags", placeholder: "hero, minimal, feed", maxLength: 1000 }
    ];
  }
  function imageStudioDirectionValues(value) {
    const source = value && typeof value === "object" ? value : {};
    const operation = String(source.operation || "");
    return {
      title: String(source.title || ""), operation: IMAGE_STUDIO_INTENTS.some(([key]) => key === operation) ? operation : "create",
      prompt_text: String(source.prompt_text || source.prompt_excerpt || ""), edit_instructions: String(source.edit_instructions || ""),
      composition_notes: String(source.composition_notes || ""), negative_direction: String(source.negative_direction || ""),
      asset_id: String(source.asset_id || ""), reference_asset_id: String(source.reference_asset_id || ""), tags: imageStudioTags(source.tags).join(", ")
    };
  }
  function imageStudioEventLabel(value) {
    const labels = {
      artboard_created: "Đã tạo artboard", artboard_updated: "Đã lưu artboard", artboard_state_changed: "Đã đổi trạng thái self-review", artboard_version_restored: "Đã khôi phục version artboard",
      artboard_review: "Đã bắt đầu self-review", artboard_approved: "Đã hoàn tất self-review", artboard_archived: "Đã archive artboard", artboard_draft: "Đã trả artboard về Draft",
      direction_created: "Đã thêm biến thể direction", direction_updated: "Đã lưu biến thể direction", direction_archived: "Đã archive biến thể", direction_restored: "Đã khôi phục biến thể", direction_version_restored: "Đã khôi phục version biến thể"
    };
    return labels[String(value || "")] || String(value || "image_studio_updated").replace(/_/g, " ");
  }
  function renderImageStudioBoundary() {
    return `<aside class="portal-card portal-card-pad portal-image-studio-boundary"><div class="portal-card-header"><div><span class="portal-section-kicker">Authoring boundary</span><h2 class="portal-card-title">Direction & self-review, không tạo ảnh</h2><p class="portal-card-subtitle">Workspace chỉ lưu brief, Asset Vault reference đã được owner check và biến thể direction. Không gọi provider, không tạo ảnh/preview/job, không trừ Xu hay khởi tạo thanh toán.</p></div>${badge("guarded")}</div><div class="portal-image-studio-guard-list"><span><strong>Provider image call</strong><em>guarded</em></span><span><strong>Image / preview</strong><em>guarded</em></span><span><strong>Job / delivery</strong><em>guarded</em></span><span><strong>Wallet / payment</strong><em>guarded</em></span></div></aside>`;
  }
  function renderImageArtboardCards(items, context) {
    const canView = Boolean(context.capabilities && context.capabilities["image-studio-view"] === true);
    if (!items.length) return renderEmpty("Chưa có artboard", "Tạo artboard đầu tiên để tổ chức brief, Asset Vault reference và self-review. Workspace không sinh ảnh hoặc output thay thế.", ICONS.image);
    return `<div class="portal-image-artboard-grid">${items.map((item) => {
      const id = String(item.id || "");
      const state = imageStudioState(item.state);
      const directionCount = Number(item.direction_count || 0);
      return `<article class="portal-card portal-card-pad portal-image-artboard-card"><div class="portal-card-header"><div><span class="portal-section-kicker">${safeText(imageStudioIntentLabel(item.image_intent))}</span><h3 class="portal-card-title">${safeText(String(item.title || "Image artboard"))}</h3><p class="portal-card-subtitle">${safeText(String(item.creative_brief_excerpt || item.brief_excerpt || item.creative_brief || "Chưa có brief hiển thị."))}</p></div>${imageStudioStateBadge(state)}</div><div class="portal-image-artboard-meta"><span>${safeText(String(item.aspect_ratio || "—"))}</span><span>${safeText(String(item.output_format || "png").toUpperCase())} target</span><span>${safeText(String(directionCount))} directions</span><span>v${safeText(String(item.revision || 1))}</span></div>${renderImageStudioTags(item.tags)}<div class="portal-form-footer"><span class="portal-form-note">${state === "approved" ? "Self-review đã đánh dấu" : state === "archived" ? "Đã archive · chỉ đọc" : "Đang biên tập"}</span>${canView && validImageStudioArtboardId(id) ? `<a class="portal-button portal-button--quiet" href="/image-studio/${encodeURIComponent(id)}">Mở artboard <span aria-hidden="true">→</span></a>` : ""}</div></article>`;
    }).join("")}</div>`;
  }
  function renderImageStudio(page, context) {
    const canView = Boolean(context.capabilities && context.capabilities["image-studio-view"] === true);
    const enabled = context.imageStudioEnabled === true;
    if (!canView) {
      const copy = enabled
        ? "Đăng nhập bằng signed session để mở artboard thuộc account hiện tại. Route native này không sử dụng dữ liệu từ legacy /image."
        : "Image Creative Studio đang được server giữ ở chế độ guarded. Khi cờ feature chưa bật, Web không hiển thị fallback, provider flow, hình giả hoặc output giả.";
      return `<article class="portal-page portal-image-studio">${renderHero(page, context)}<section class="portal-card portal-card-pad">${renderEmpty("Image Creative Studio đang được bảo vệ", copy, ICONS.image)}</section></article>`;
    }
    const summary = context.imageStudioSummary && typeof context.imageStudioSummary === "object" ? context.imageStudioSummary : {};
    const artboardsSummary = summary.artboards && typeof summary.artboards === "object" ? summary.artboards : {};
    const artboards = Array.isArray(context.imageArtboards) ? context.imageArtboards.filter((item) => item && validImageStudioArtboardId(item.id)).slice(0, 100) : [];
    const values = imageStudioArtboardValues(transientFormValues(page.routePath || page.path));
    const total = Number(artboardsSummary.total || artboards.length);
    const review = Number(artboardsSummary.review || 0);
    const approved = Number(artboardsSummary.approved || 0);
    return `<article class="portal-page portal-image-studio">${renderHero(page, context)}
      <section class="portal-image-studio-intro"><div><span class="portal-section-kicker">Web-native visual direction</span><h2>Đi từ art direction đến review, với Asset Vault reference có kiểm soát.</h2><p>Giữ creative brief, negative direction và biến thể trong không gian riêng tư. Mọi số liệu là metadata authoring; không phải ảnh, thumbnail hay preview đã được tạo.</p></div><dl><div><dt>${safeText(String(total))}</dt><dd>Artboards</dd></div><div><dt>${safeText(String(review))}</dt><dd>Đang review</dd></div><div><dt>${safeText(String(approved))}</dt><dd>Self-review xong</dd></div></dl></section>
      <div class="portal-image-studio-layout"><section class="portal-card portal-card-pad portal-image-studio-create"><div class="portal-card-header"><div><span class="portal-section-kicker">New creative artboard</span><h2 class="portal-card-title">Lập art direction</h2><p class="portal-card-subtitle">Bắt đầu bằng intent, tỷ lệ, định dạng đích, creative brief và style direction. Server kiểm tra session, CSRF, ownership, revision và idempotency cho mỗi lần ghi.</p></div>${badge(canView && context.capabilities["image-artboard-create"] ? "ready" : "guarded")}</div><form class="portal-form" data-portal-form data-portal-action="image-artboard-create" data-portal-route="${safeText(page.routePath || page.path)}" novalidate>${renderFields(imageStudioArtboardFields(context), Boolean(context.capabilities && context.capabilities["image-artboard-create"]), context, values)}<div class="portal-form-footer"><span class="portal-form-note">Không nhập URL, asset path, provider/job ID, secret, OTP/CVV hoặc chứng từ thanh toán.</span><button class="portal-button portal-button--primary" type="submit"${context.capabilities && context.capabilities["image-artboard-create"] ? "" : " disabled"}>Tạo artboard</button></div></form></section>${renderImageStudioBoundary()}</div>
      <section class="portal-card portal-card-pad"><div class="portal-card-header"><div><span class="portal-section-kicker">Artboard library</span><h2 class="portal-card-title">Tiếp tục creative review</h2><p class="portal-card-subtitle">Danh sách chỉ hiển thị metadata/excerpt thuộc signed account. Mở artboard để server owner-check direction, history và Asset Vault reference an toàn.</p></div><button class="portal-button portal-button--quiet" type="button" data-portal-action="image-studio-refresh" data-portal-route="/image-studio">Làm mới</button></div>${renderImageArtboardCards(artboards, context)}</section>
    </article>`;
  }
  function imageStudioEstimateMarkup(estimate, directions) {
    const source = estimate && typeof estimate === "object" ? estimate : {};
    const active = Number(source.active_direction_count ?? source.direction_count ?? directions.length);
    const withAsset = Number(source.asset_reference_count ?? source.referenced_asset_count ?? directions.filter((item) => String(item.asset_id || "")).length);
    const variants = Number(source.variant_count ?? directions.length);
    return `<section class="portal-card portal-card-pad portal-image-studio-estimate"><div class="portal-card-header"><div><span class="portal-section-kicker">Review estimate</span><h2 class="portal-card-title">Tổng hợp metadata để rà soát</h2><p class="portal-card-subtitle">Estimate chỉ tổng hợp direction và Asset Vault reference đã chọn. Nó không đọc hình, render, tạo thumbnail, gọi provider hay xác nhận output.</p></div>${badge("read_only")}</div><div class="portal-image-studio-estimate-grid"><span><strong>${safeText(String(active))}</strong> directions active</span><span><strong>${safeText(String(withAsset))}</strong> Asset Vault refs</span><span><strong>${safeText(String(variants))}</strong> variant metadata</span></div></section>`;
  }
  function renderImageDirectionCard(direction, artboard, context, route) {
    const directionId = String(direction.id || "");
    const active = String(direction.state || "active") === "active";
    const artboardWritable = String(artboard.state || "") === "draft";
    const canUpdate = Boolean(context.capabilities && context.capabilities["image-direction-update"] === true && active && artboardWritable);
    const canArchive = Boolean(context.capabilities && context.capabilities["image-direction-archive"] === true && active && artboardWritable);
    const canRestore = Boolean(context.capabilities && context.capabilities["image-direction-restore"] === true && !active && artboardWritable);
    const canRestoreVersion = Boolean(context.capabilities && context.capabilities["image-direction-restore-version"] === true && active && artboardWritable);
    const versions = Array.isArray(direction.versions) ? direction.versions.filter((item) => item && Number.isInteger(Number(item.revision))).slice(0, 20) : [];
    const stateAction = active
      ? `<button class="portal-button portal-button--quiet" type="button" data-portal-action="image-direction-archive" data-portal-route="${safeText(route)}" data-image-artboard-id="${safeText(String(artboard.id))}" data-image-artboard-revision="${safeText(String(artboard.revision))}" data-image-direction-id="${safeText(directionId)}" data-image-direction-revision="${safeText(String(direction.revision))}" data-portal-confirm="Archive biến thể direction này? Metadata và history riêng tư vẫn được giữ để khôi phục."${canArchive ? "" : " disabled"}>Archive</button>`
      : `<button class="portal-button portal-button--quiet" type="button" data-portal-action="image-direction-restore" data-portal-route="${safeText(route)}" data-image-artboard-id="${safeText(String(artboard.id))}" data-image-artboard-revision="${safeText(String(artboard.revision))}" data-image-direction-id="${safeText(directionId)}" data-image-direction-revision="${safeText(String(direction.revision))}"${canRestore ? "" : " disabled"}>Khôi phục</button>`;
    const versionsMarkup = versions.length ? `<div class="portal-image-direction-history"><strong>Lịch sử biến thể</strong>${versions.map((version) => `<div><span>v${safeText(String(version.revision))} · ${safeText(String(version.created_at || "—"))}</span>${Number(version.revision) === Number(direction.revision) ? "<em>Đang mở</em>" : `<button class="portal-button portal-button--quiet" type="button" data-portal-action="image-direction-restore-version" data-portal-route="${safeText(route)}" data-image-artboard-id="${safeText(String(artboard.id))}" data-image-artboard-revision="${safeText(String(artboard.revision))}" data-image-direction-id="${safeText(directionId)}" data-image-direction-revision="${safeText(String(direction.revision))}" data-image-direction-version="${safeText(String(version.revision))}" data-portal-confirm="Khôi phục v${safeText(String(version.revision))} thành một revision biến thể mới?"${canRestoreVersion ? "" : " disabled"}>Khôi phục v${safeText(String(version.revision))}</button>`}</div>`).join("")}</div>` : "";
    const assetName = imageStudioAssetName(context, direction.asset_id);
    const referenceName = imageStudioAssetName(context, direction.reference_asset_id);
    return `<article class="portal-image-direction-card${active ? "" : " is-archived"}"><div class="portal-card-header"><div><span class="portal-section-kicker">${safeText(imageStudioIntentLabel(direction.operation))}</span><h3 class="portal-card-title">${safeText(String(direction.title || "Image direction"))}</h3><p class="portal-card-subtitle">${safeText(String(direction.prompt_excerpt || direction.prompt_text || direction.edit_instructions || "Chưa có direction hiển thị."))}</p></div>${badge(active ? "ready" : "archived")}</div><div class="portal-image-direction-meta"><span>Asset: ${safeText(assetName)}</span><span>Ref: ${safeText(referenceName)}</span><span>v${safeText(String(direction.revision || 1))}</span></div>${renderImageStudioTags(direction.tags)}<div class="portal-inline-actions">${stateAction}</div><form class="portal-form portal-image-direction-form" data-portal-form data-portal-action="image-direction-update" data-portal-route="${safeText(route)}" data-image-artboard-id="${safeText(String(artboard.id))}" data-image-artboard-revision="${safeText(String(artboard.revision))}" data-image-direction-id="${safeText(directionId)}" data-image-direction-revision="${safeText(String(direction.revision))}" novalidate>${renderFields(imageStudioDirectionFields(context), canUpdate, context, imageStudioDirectionValues(direction))}<div class="portal-form-footer"><span class="portal-form-note">Lưu direction không đọc Asset Vault blob, không tạo ảnh/preview và không gọi provider.</span><button class="portal-button portal-button--primary" type="submit"${canUpdate ? "" : " disabled"}>Lưu revision biến thể</button></div></form>${versionsMarkup}</article>`;
  }
  function renderImageStudioDetail(page, context) {
    const detail = context.imageArtboardDetail && typeof context.imageArtboardDetail === "object" ? context.imageArtboardDetail : {};
    const artboard = detail.artboard && typeof detail.artboard === "object" && validImageStudioArtboardId(detail.artboard.id) && String(detail.artboard.id) === String(page.recordId || "") ? detail.artboard : null;
    const canView = Boolean(context.capabilities && context.capabilities["image-studio-view"] === true);
    if (!canView || !artboard) {
      const title = !canView ? "Image Creative Studio đang được bảo vệ" : "Không tìm thấy artboard";
      const copy = !canView ? "Đăng nhập bằng signed session và chờ feature flag server-side để mở artboard của account hiện tại." : "Server cần xác minh owner trước khi hiển thị art direction, Asset Vault reference và history; dữ liệu cũ không được giữ trong browser.";
      return `<article class="portal-page portal-image-studio-detail">${renderHero(page, context)}<section class="portal-card portal-card-pad">${renderEmpty(title, copy, ICONS.image)}<div class="portal-form-footer"><a class="portal-button portal-button--primary" href="/image-studio">Về Image Studio</a></div></section></article>`;
    }
    const route = page.routePath || page.path;
    const state = imageStudioState(artboard.state);
    // The server permits authoring mutations only in Draft.  Review is an
    // explicit frozen self-review checkpoint, so keep the client affordance
    // conservative rather than letting a stale browser invite a rejected write.
    const writable = state === "draft";
    const canUpdate = Boolean(context.capabilities && context.capabilities["image-artboard-update"] === true && writable);
    const canLifecycle = Boolean(context.capabilities && context.capabilities["image-artboard-lifecycle"] === true);
    const canRestoreVersion = Boolean(context.capabilities && context.capabilities["image-artboard-restore-version"] === true && writable);
    const canDirectionCreate = Boolean(context.capabilities && context.capabilities["image-direction-create"] === true && writable);
    const directions = Array.isArray(detail.directions) ? detail.directions.filter((item) => item && validImageStudioDirectionId(item.id) && String(item.artboard_id || "") === String(artboard.id)).slice(0, 250) : [];
    const activeDirections = directions.filter((item) => String(item.state || "active") === "active");
    const versions = Array.isArray(detail.versions) ? detail.versions.filter((item) => item && Number.isInteger(Number(item.revision))).slice(0, 100) : [];
    const events = Array.isArray(detail.events) ? detail.events.filter((item) => item && typeof item === "object").slice(0, 24) : [];
    const stateActions = state === "archived"
      ? `<button class="portal-button portal-button--quiet" type="button" data-portal-action="image-artboard-state" data-image-artboard-state="draft" data-portal-route="${safeText(route)}" data-image-artboard-id="${safeText(String(artboard.id))}" data-image-artboard-revision="${safeText(String(artboard.revision))}" data-portal-confirm="Khôi phục artboard về Draft để tiếp tục biên tập?"${canLifecycle ? "" : " disabled"}>Khôi phục về Draft</button>`
      : `<button class="portal-button portal-button--quiet" type="button" data-portal-action="image-artboard-state" data-image-artboard-state="${state === "draft" ? "review" : "draft"}" data-portal-route="${safeText(route)}" data-image-artboard-id="${safeText(String(artboard.id))}" data-image-artboard-revision="${safeText(String(artboard.revision))}" data-portal-confirm="${state === "draft" ? "Chuyển artboard sang Self-review?" : "Trả artboard về Draft để tiếp tục biên tập?"}"${canLifecycle ? "" : " disabled"}>${state === "draft" ? "Bắt đầu self-review" : "Trả về Draft"}</button><button class="portal-button portal-button--quiet" type="button" data-portal-action="image-artboard-state" data-image-artboard-state="approved" data-portal-route="${safeText(route)}" data-image-artboard-id="${safeText(String(artboard.id))}" data-image-artboard-revision="${safeText(String(artboard.revision))}" data-portal-confirm="Đánh dấu self-review hoàn tất? Điều này không tạo ảnh, preview, job hoặc output."${canLifecycle && state === "review" ? "" : " disabled"}>Đánh dấu review xong</button><button class="portal-button portal-button--quiet" type="button" data-portal-action="image-artboard-state" data-image-artboard-state="archived" data-portal-route="${safeText(route)}" data-image-artboard-id="${safeText(String(artboard.id))}" data-image-artboard-revision="${safeText(String(artboard.revision))}" data-portal-confirm="Archive artboard? Direction và history riêng tư vẫn được giữ."${canLifecycle ? "" : " disabled"}>Archive artboard</button>`;
    const versionMarkup = versions.length ? `<div class="portal-image-version-list">${versions.map((version) => `<article><div><strong>v${safeText(String(version.revision))} · ${safeText(String(version.title || "Image artboard"))}</strong><p>${safeText(String(version.creative_brief_excerpt || version.brief_excerpt || version.creative_brief || ""))}</p><small>${safeText(String(version.created_at || "—"))}</small></div>${Number(version.revision) === Number(artboard.revision) ? "<span class=\"portal-form-note\">Đang mở</span>" : `<button class="portal-button portal-button--quiet" type="button" data-portal-action="image-artboard-restore-version" data-portal-route="${safeText(route)}" data-image-artboard-id="${safeText(String(artboard.id))}" data-image-artboard-revision="${safeText(String(artboard.revision))}" data-image-artboard-version="${safeText(String(version.revision))}" data-portal-confirm="Khôi phục v${safeText(String(version.revision))} thành một revision artboard mới?"${canRestoreVersion ? "" : " disabled"}>Khôi phục v${safeText(String(version.revision))}</button>`}</article>`).join("")}</div>` : renderEmpty("Chưa có history", "Version đầu tiên xuất hiện khi artboard được lưu.", "↺");
    const directionMarkup = directions.length ? directions.map((direction) => renderImageDirectionCard(direction, artboard, context, route)).join("") : renderEmpty("Chưa có biến thể direction", "Thêm direction thủ công để tách các phương án review. Workspace không tạo hình thay bạn.", ICONS.image);
    const estimate = detail.estimate && typeof detail.estimate === "object" ? detail.estimate : (context.imageArtboardEstimate && typeof context.imageArtboardEstimate === "object" ? context.imageArtboardEstimate : {});
    const estimateMarkup = state === "archived"
      ? `<section class="portal-card portal-card-pad portal-image-studio-estimate"><div class="portal-card-header"><div><span class="portal-section-kicker">Review estimate</span><h2 class="portal-card-title">Estimate đã được khóa</h2><p class="portal-card-subtitle">Artboard đang archive nên direction và estimate không được tính lại. Khôi phục về Draft khi bạn muốn tiếp tục review.</p></div>${badge("archived")}</div></section>`
      : imageStudioEstimateMarkup(estimate, activeDirections);
    return `<article class="portal-page portal-image-studio-detail">${renderHero(page, context)}
      <section class="portal-image-studio-detail-summary"><div><span class="portal-section-kicker">${safeText(imageStudioIntentLabel(artboard.image_intent))} · ${safeText(String(artboard.aspect_ratio || "—"))}</span><h2>${safeText(String(artboard.title || "Image artboard"))}</h2><p>${safeText(String(artboard.creative_brief || artboard.creative_brief_excerpt || artboard.brief_excerpt || "Chưa có brief hiển thị."))}</p>${renderImageStudioTags(artboard.tags)}</div><dl><div><dt>Trạng thái</dt><dd>${safeText(IMAGE_STUDIO_STATES[state] || "Được bảo vệ")}</dd></div><div><dt>Revision</dt><dd>v${safeText(String(artboard.revision || 1))}</dd></div><div><dt>Directions</dt><dd>${safeText(String(activeDirections.length))}</dd></div></dl></section>
      <div class="portal-image-studio-detail-grid"><section class="portal-card portal-card-pad portal-image-studio-editor"><div class="portal-card-header"><div><span class="portal-section-kicker">Artboard editor</span><h2 class="portal-card-title">Brief & visual direction</h2><p class="portal-card-subtitle">Lưu bằng optimistic revision; self-review và archive là trạng thái server-side, không do browser tự suy diễn.</p></div>${imageStudioStateBadge(state)}</div><form class="portal-form" data-portal-form data-portal-action="image-artboard-update" data-portal-route="${safeText(route)}" data-image-artboard-id="${safeText(String(artboard.id))}" data-image-artboard-revision="${safeText(String(artboard.revision))}" novalidate>${renderFields(imageStudioArtboardFields(context), canUpdate, context, imageStudioArtboardValues(artboard))}<div class="portal-form-footer"><span class="portal-form-note">Chỉ Draft có thể biên tập. Approved hoặc archived cần được server đưa về Draft trước khi sửa.</span><div class="portal-inline-actions">${stateActions}<button class="portal-button portal-button--primary" type="submit"${canUpdate ? "" : " disabled"}>Lưu revision artboard</button></div></div></form></section>${estimateMarkup}</div>
      <section class="portal-card portal-card-pad portal-image-direction-create"><div class="portal-card-header"><div><span class="portal-section-kicker">Variant direction board</span><h2 class="portal-card-title">Thêm biến thể direction</h2><p class="portal-card-subtitle">Mỗi biến thể có prompt, visual notes, Asset Vault reference và history riêng. Với non-create, server yêu cầu ảnh gốc thuộc account hiện tại.</p></div>${badge(canDirectionCreate ? "ready" : "guarded")}</div><form class="portal-form" data-portal-form data-portal-action="image-direction-create" data-portal-route="${safeText(route)}" data-image-artboard-id="${safeText(String(artboard.id))}" data-image-artboard-revision="${safeText(String(artboard.revision))}" novalidate>${renderFields(imageStudioDirectionFields(context), canDirectionCreate, context, { operation: artboard.image_intent || "create" })}<div class="portal-form-footer"><span class="portal-form-note">Chỉ reference Asset Vault UUID được gửi. Không có raw URL, blob, thumbnail, provider call, preview hoặc output.</span><button class="portal-button portal-button--primary" type="submit"${canDirectionCreate ? "" : " disabled"}>Thêm biến thể direction</button></div></form></section>
      <section class="portal-card portal-card-pad"><div class="portal-card-header"><div><span class="portal-section-kicker">Review-safe local utilities</span><h2 class="portal-card-title">Có ảnh private cần xử lý deterministic?</h2><p class="portal-card-subtitle">Resize & Enhance là utility Web-native riêng có output/private history riêng. Chúng không phải provider AI và không chuyển direction này thành ảnh đã tạo.</p></div>${badge("read_only")}</div><div class="portal-form-footer"><a class="portal-button portal-button--quiet" href="/image/resize">Mở Resize & Aspect Studio</a><a class="portal-button portal-button--quiet" href="/image/edit">Mở Image Enhance Studio</a><a class="portal-button portal-button--quiet" href="/asset-vault">Mở Asset Vault</a></div></section>
      <section class="portal-card portal-card-pad"><div class="portal-card-header"><div><span class="portal-section-kicker">Direction library</span><h2 class="portal-card-title">Biến thể & notes</h2><p class="portal-card-subtitle">Mọi card là metadata authoring. Asset name được hiển thị từ owner-scoped metadata, không phải thumbnail hoặc media URL.</p></div></div><div class="portal-image-direction-grid">${directionMarkup}</div></section>
      <div class="portal-image-studio-history-grid"><section class="portal-card portal-card-pad"><div class="portal-card-header"><div><span class="portal-section-kicker">Version history</span><h2 class="portal-card-title">Lịch sử artboard</h2><p class="portal-card-subtitle">Khôi phục version tạo revision mới, không xóa history cũ.</p></div></div>${versionMarkup}</section><section class="portal-card portal-card-pad portal-image-studio-activity"><div class="portal-card-header"><div><span class="portal-section-kicker">Audit-safe feed</span><h2 class="portal-card-title">Hoạt động gần đây</h2><p class="portal-card-subtitle">Feed chỉ hiển thị nhãn, revision và thời điểm; không chứa prompt, asset path, URL, provider hay payment data.</p></div></div>${events.length ? `<div class="portal-image-studio-events">${events.map((item) => `<div><span aria-hidden="true">•</span><span><strong>${safeText(imageStudioEventLabel(item.action))}</strong><small>v${safeText(String(item.revision || 1))} · ${safeText(String(item.created_at || "—"))}</small></span></div>`).join("")}</div>` : "<p class=\"portal-form-note\">Chưa có hoạt động được ghi nhận.</p>"}</section></div>
      ${renderImageStudioBoundary()}
    </article>`;
  }

  // This is a private authoring surface. It deliberately does not reuse the
  // historical document-operation history, which owns real deterministic
  // file work and delivery behind an independent contract.
  const DOCUMENT_WORKSPACE_TYPES = Object.freeze([
    ["pdf", "PDF"], ["office", "Office document"], ["text", "Text document"],
    ["image", "Ảnh / scan"], ["scan", "Tài liệu scan"], ["mixed", "Nhiều loại tài liệu"]
  ]);
  const DOCUMENT_WORKSPACE_OPERATIONS = Object.freeze([
    ["organize", "Tổ chức / QA"], ["split", "Tách PDF · planned"], ["merge", "Gộp PDF · planned"],
    ["optimize", "Tối ưu PDF · planned"], ["image_to_pdf", "Ảnh → PDF · planned"],
    ["pdf_to_images", "PDF → ảnh · planned"], ["pdf_to_word", "PDF text → Word · planned"],
    ["ocr", "OCR intent · guarded"], ["translate", "Dịch intent · guarded"],
    ["convert", "Convert intent · guarded"], ["other", "Khác"]
  ]);
  const DOCUMENT_WORKSPACE_STATES = Object.freeze({
    draft: "Bản nháp", review: "Đang self-review", approved: "Self-review hoàn tất", archived: "Đã archive"
  });

  function validDocumentWorkspaceId(value) { return validProjectId(value); }
  function validDocumentPlanId(value) { return validProjectId(value); }
  function documentWorkspaceState(value) {
    const state = String(value || "").toLowerCase();
    return Object.prototype.hasOwnProperty.call(DOCUMENT_WORKSPACE_STATES, state) ? state : "guarded";
  }
  function documentWorkspaceStateBadge(value) {
    const state = documentWorkspaceState(value);
    return '<span class="portal-badge" data-status="' + safeText(state) + '">' + safeText(DOCUMENT_WORKSPACE_STATES[state] || "Được bảo vệ") + "</span>";
  }
  function documentWorkspaceTags(value) {
    return Array.isArray(value) ? value.filter((tag) => typeof tag === "string" && tag.trim()).slice(0, 20) : [];
  }
  function renderDocumentWorkspaceTags(value) {
    const tags = documentWorkspaceTags(value);
    return tags.length ? '<div class="portal-document-workspace-tags">' + tags.map((tag) => "<span>" + safeText(tag) + "</span>").join("") + "</div>" : "";
  }
  function documentWorkspaceTypeLabel(value) {
    const item = DOCUMENT_WORKSPACE_TYPES.find((entry) => entry[0] === String(value || ""));
    return item ? item[1] : "Tài liệu";
  }
  function documentWorkspaceOperationLabel(value) {
    const item = DOCUMENT_WORKSPACE_OPERATIONS.find((entry) => entry[0] === String(value || ""));
    return item ? item[1] : "Processing plan";
  }
  function documentWorkspaceReferences(context) {
    return context && context.documentWorkspaceReferences && typeof context.documentWorkspaceReferences === "object" ? context.documentWorkspaceReferences : {};
  }
  function documentWorkspaceProjectOptions(context) {
    const refs = documentWorkspaceReferences(context);
    return (Array.isArray(refs.projects) ? refs.projects : []).filter((item) => item && validDocumentWorkspaceId(item.id)).slice(0, 100)
      .map((item) => ({ value: String(item.id), label: String(item.title || "Project Web riêng tư") }));
  }
  function documentWorkspaceAssetOptions(context) {
    const refs = documentWorkspaceReferences(context);
    const assets = Array.isArray(refs.document_assets) ? refs.document_assets : [];
    // The API intentionally returns owner-scoped display metadata only. No
    // filename/path/blob/url fallback is acceptable in this selector.
    return assets.filter((item) => item && validDocumentWorkspaceId(item.id)).slice(0, 100).map((item) => {
      const label = String(item.display_name || "Asset Vault document").replace(/\s+/g, " ").trim().slice(0, 160);
      const extension = String(item.extension || "").replace(/^\./, "").toUpperCase();
      return { value: String(item.id), label: extension ? label + " · " + extension : label };
    });
  }
  function documentWorkspaceAssetName(context, assetId) {
    const id = String(assetId || "");
    const assets = documentWorkspaceAssetOptions(context);
    const asset = assets.find((item) => item.value === id);
    return asset ? asset.label : (id ? "Asset Vault reference đã chọn" : "Không gắn asset");
  }
  function documentWorkspaceFields(context) {
    return [
      { name: "title", label: "Tên document brief", placeholder: "Ví dụ: Hồ sơ sản phẩm tháng 7", required: true, minLength: 2, maxLength: 180 },
      { name: "document_type", label: "Loại tài liệu", control: "select", required: true, options: DOCUMENT_WORKSPACE_TYPES },
      { name: "language", label: "Ngôn ngữ nguồn / review", placeholder: "vi", required: true, minLength: 1, maxLength: 100 },
      { name: "target_language", label: "Ngôn ngữ đích (tùy chọn)", placeholder: "en", maxLength: 100, help: "Chỉ là metadata review, không gọi dịch máy hoặc tạo bản dịch." },
      { name: "source_summary", label: "Scope, nguồn & trang dự kiến", control: "textarea", placeholder: "Mô tả phạm vi, loại trang, giới hạn đầu vào và những điều cần kiểm tra…", required: true, minLength: 3, maxLength: 6000, wide: true },
      { name: "objective", label: "Mục tiêu, target format & QA checklist", control: "textarea", placeholder: "Mục tiêu xử lý, định dạng dự kiến, tiêu chí QA và điều không được tự suy diễn…", required: true, minLength: 3, maxLength: 6000, wide: true },
      { name: "tags", label: "Tags", placeholder: "contract, pdf, qa", maxLength: 1000 },
      { name: "project_id", label: "Project (tùy chọn)", control: "select", options: documentWorkspaceProjectOptions(context), emptyLabel: "Không liên kết Project" }
    ];
  }
  function documentWorkspaceValues(value) {
    const source = value && typeof value === "object" ? value : {};
    const type = String(source.document_type || "");
    return {
      title: String(source.title || ""),
      document_type: DOCUMENT_WORKSPACE_TYPES.some((entry) => entry[0] === type) ? type : "mixed",
      language: String(source.language || "vi"),
      target_language: String(source.target_language || ""),
      source_summary: String(source.source_summary || source.source_excerpt || ""),
      objective: String(source.objective || source.objective_excerpt || ""),
      tags: documentWorkspaceTags(source.tags).join(", "),
      project_id: String(source.project_id || "")
    };
  }
  function documentPlanFields(context) {
    return [
      { name: "title", label: "Tên processing plan", placeholder: "Ví dụ: Rà soát trước khi tách trang", required: true, minLength: 2, maxLength: 180 },
      { name: "operation", label: "Intent / planned operation", control: "select", required: true, options: DOCUMENT_WORKSPACE_OPERATIONS, help: "Lưu intent để review; không gọi utility, OCR, converter, dịch, provider hoặc job." },
      { name: "source_asset_id", label: "Asset Vault source metadata", control: "select", options: documentWorkspaceAssetOptions(context), emptyLabel: "Không gắn source metadata", help: "Chỉ gửi UUID owner-scoped; workspace không đọc file, blob, path hoặc preview." },
      { name: "reference_asset_id", label: "Asset Vault reference metadata", control: "select", options: documentWorkspaceAssetOptions(context), emptyLabel: "Không gắn reference metadata" },
      { name: "instructions", label: "Scope, pages & kiểm tra dự kiến", control: "textarea", placeholder: "Phạm vi trang, thứ tự, tiêu chí QA và fallback cần tự review…", maxLength: 6000, wide: true },
      { name: "tags", label: "Tags", placeholder: "pages, legal, review", maxLength: 1000 }
    ];
  }
  function documentPlanValues(value) {
    const source = value && typeof value === "object" ? value : {};
    const operation = String(source.operation || "");
    return {
      title: String(source.title || ""),
      operation: DOCUMENT_WORKSPACE_OPERATIONS.some((entry) => entry[0] === operation) ? operation : "organize",
      source_asset_id: String(source.source_asset_id || ""),
      reference_asset_id: String(source.reference_asset_id || ""),
      instructions: String(source.instructions || source.instructions_excerpt || ""),
      tags: documentWorkspaceTags(source.tags).join(", ")
    };
  }
  function documentWorkspaceEventLabel(value) {
    const labels = {
      workspace_created: "Đã tạo document brief", workspace_updated: "Đã lưu document brief",
      workspace_state_changed: "Đã đổi trạng thái self-review", workspace_version_restored: "Đã khôi phục version brief",
      workspace_review: "Đã bắt đầu self-review", workspace_approved: "Đã hoàn tất self-review",
      workspace_archived: "Đã archive brief", workspace_draft: "Đã trả brief về Draft",
      plan_created: "Đã thêm processing plan", plan_updated: "Đã lưu processing plan",
      plan_archived: "Đã archive processing plan", plan_restored: "Đã khôi phục processing plan",
      plan_version_restored: "Đã khôi phục version processing plan", plans_reordered: "Đã đổi thứ tự processing plan"
    };
    return labels[String(value || "")] || String(value || "document_workspace_updated").replace(/_/g, " ");
  }
  function renderDocumentWorkspaceBoundary() {
    return '<aside class="portal-card portal-card-pad portal-document-workspace-boundary"><div class="portal-card-header"><div><span class="portal-section-kicker">Authoring boundary</span><h2 class="portal-card-title">Brief & processing plan, không xử lý file</h2><p class="portal-card-subtitle">Workspace chỉ lưu metadata review và opaque Asset Vault reference. Không upload/đọc file, tạo preview/output, gọi OCR/dịch/provider/Bot job hay trừ Xu/khởi tạo thanh toán.</p></div>' + badge("guarded") + '</div><div class="portal-document-workspace-guard-list"><span><strong>OCR / translation</strong><em>guarded</em></span><span><strong>Convert / output</strong><em>guarded</em></span><span><strong>Provider / Bot job</strong><em>guarded</em></span><span><strong>Wallet / payment</strong><em>guarded</em></span></div></aside>';
  }
  function renderDocumentWorkspaceCards(items, context) {
    const canView = Boolean(context.capabilities && context.capabilities["document-workspace-view"] === true);
    if (!items.length) return renderEmpty("Chưa có document brief", "Tạo brief đầu tiên để tổ chức scope, target format, QA checklist và processing plan. Workspace không tạo file hoặc output thay thế.", ICONS.document);
    return '<div class="portal-document-workspace-grid">' + items.map((item) => {
      const id = String(item.id || "");
      const state = documentWorkspaceState(item.lifecycle || item.state);
      const planCount = Number(item.plan_count || 0);
      const href = "/document-workspace/" + encodeURIComponent(id);
      const button = canView && validDocumentWorkspaceId(id)
        ? '<a class="portal-button portal-button--quiet" href="' + safeText(href) + '">Mở brief <span aria-hidden="true">→</span></a>' : "";
      return '<article class="portal-card portal-card-pad portal-document-workspace-card"><div class="portal-card-header"><div><span class="portal-section-kicker">' + safeText(documentWorkspaceTypeLabel(item.document_type)) + "</span><h3 class=\"portal-card-title\">" + safeText(String(item.title || "Document brief")) + "</h3><p class=\"portal-card-subtitle\">" + safeText(String(item.objective_excerpt || item.objective || item.source_excerpt || item.source_summary || "Chưa có scope hiển thị.")) + "</p></div>" + documentWorkspaceStateBadge(state) + '</div><div class="portal-document-workspace-meta"><span>' + safeText(String(planCount)) + " plans</span><span>" + safeText(String(item.language || "—")) + "</span><span>v" + safeText(String(item.revision || 1)) + "</span></div>" + renderDocumentWorkspaceTags(item.tags) + '<div class="portal-form-footer"><span class="portal-form-note">' + safeText(state === "approved" ? "Self-review đã đánh dấu" : state === "archived" ? "Đã archive · chỉ đọc" : "Đang biên tập") + "</span>" + button + "</div></article>";
    }).join("") + "</div>";
  }
  function renderDocumentWorkspace(page, context) {
    const canView = Boolean(context.capabilities && context.capabilities["document-workspace-view"] === true);
    const enabled = context.documentWorkspaceEnabled === true;
    if (!canView) {
      const copy = enabled
        ? "Đăng nhập bằng signed session để mở document brief thuộc account hiện tại. Route native này không đọc legacy document-operation history."
        : "Document & PDF Workspace đang được server giữ ở chế độ guarded. Khi feature flag chưa bật, Web không hiển thị converter, OCR, file preview hay output giả.";
      return '<article class="portal-page portal-document-workspace">' + renderHero(page, context) + '<section class="portal-card portal-card-pad">' + renderEmpty("Document & PDF Workspace đang được bảo vệ", copy, ICONS.document) + "</section></article>";
    }
    const summary = context.documentWorkspaceSummary && typeof context.documentWorkspaceSummary === "object" ? context.documentWorkspaceSummary : {};
    const workspaceSummary = summary.workspaces && typeof summary.workspaces === "object" ? summary.workspaces : {};
    const workspaces = Array.isArray(context.documentWorkspaces) ? context.documentWorkspaces.filter((item) => item && validDocumentWorkspaceId(item.id)).slice(0, 100) : [];
    const values = documentWorkspaceValues(transientFormValues(page.routePath || page.path));
    const canCreate = Boolean(context.capabilities && context.capabilities["document-workspace-create"] === true);
    const intro = '<section class="portal-document-workspace-intro"><div><span class="portal-section-kicker">Web-native document planning</span><h2>Rõ scope, target format và QA trước khi chọn công cụ phù hợp.</h2><p>Quản lý document brief, processing plan và Asset Vault metadata theo signed account. Các số liệu là metadata review; không phải file, trang, preview hay output đã được tạo.</p></div><dl><div><dt>' + safeText(String(Number(workspaceSummary.total || workspaces.length))) + '</dt><dd>Document briefs</dd></div><div><dt>' + safeText(String(Number(workspaceSummary.review || 0))) + '</dt><dd>Đang review</dd></div><div><dt>' + safeText(String(Number(workspaceSummary.approved || 0))) + "</dt><dd>Self-review xong</dd></div></dl></section>";
    const form = '<section class="portal-card portal-card-pad portal-document-workspace-create"><div class="portal-card-header"><div><span class="portal-section-kicker">New document brief</span><h2 class="portal-card-title">Lập scope & QA checklist</h2><p class="portal-card-subtitle">Bắt đầu bằng loại tài liệu, scope, target format, language và checklist review. Server kiểm tra session, CSRF, ownership, revision và idempotency cho mỗi lần ghi.</p></div>' + badge(canCreate ? "ready" : "guarded") + '</div><form class="portal-form" data-portal-form data-portal-action="document-workspace-create" data-portal-route="' + safeText(page.routePath || page.path) + '" novalidate>' + renderFields(documentWorkspaceFields(context), canCreate, context, values) + '<div class="portal-form-footer"><span class="portal-form-note">Không nhập URL, file/path/blob, provider/job ID, secret, OTP/CVV hoặc chứng từ thanh toán.</span><button class="portal-button portal-button--primary" type="submit"' + (canCreate ? "" : " disabled") + ">Tạo document brief</button></div></form></section>";
    const library = '<section class="portal-card portal-card-pad"><div class="portal-card-header"><div><span class="portal-section-kicker">Brief library</span><h2 class="portal-card-title">Tiếp tục self-review</h2><p class="portal-card-subtitle">Danh sách chỉ hiển thị metadata/excerpt thuộc signed account. Mở brief để server owner-check processing plan, history và Asset Vault reference an toàn.</p></div><button class="portal-button portal-button--quiet" type="button" data-portal-action="document-workspace-refresh" data-portal-route="/document-workspace">Làm mới</button></div>' + renderDocumentWorkspaceCards(workspaces, context) + "</section>";
    return '<article class="portal-page portal-document-workspace">' + renderHero(page, context) + intro + '<div class="portal-document-workspace-layout">' + form + renderDocumentWorkspaceBoundary() + "</div>" + library + "</article>";
  }
  function documentWorkspaceEstimateMarkup(estimate, plans) {
    const source = estimate && typeof estimate === "object" ? estimate : {};
    const active = Number(source.active_plan_count ?? source.plan_count ?? plans.length);
    const withAsset = Number(source.asset_reference_count ?? source.referenced_asset_count ?? plans.filter((item) => String(item.source_asset_id || item.reference_asset_id || "")).length);
    const guarded = Number(source.guarded_intent_count ?? plans.filter((item) => ["ocr", "translate", "convert"].includes(String(item.operation || ""))).length);
    return '<section class="portal-card portal-card-pad portal-document-workspace-estimate"><div class="portal-card-header"><div><span class="portal-section-kicker">Review estimate</span><h2 class="portal-card-title">Tổng hợp plan để rà soát</h2><p class="portal-card-subtitle">Estimate chỉ đếm metadata plan/reference. Nó không đọc file, đếm trang, chạy OCR/dịch, gọi provider, tạo output hoặc xác nhận delivery.</p></div>' + badge("read_only") + '</div><div class="portal-document-workspace-estimate-grid"><span><strong>' + safeText(String(active)) + "</strong> plans active</span><span><strong>" + safeText(String(withAsset)) + "</strong> Asset Vault refs</span><span><strong>" + safeText(String(guarded)) + "</strong> guarded intents</span></div></section>";
  }
  function documentWorkspaceDataAttrs(workspace, plan) {
    const baseAttrs = ' data-document-workspace-id="' + safeText(String(workspace.id)) + '" data-document-workspace-revision="' + safeText(String(workspace.revision)) + '"';
    if (!plan) return baseAttrs;
    return baseAttrs + ' data-document-plan-id="' + safeText(String(plan.id)) + '" data-document-plan-revision="' + safeText(String(plan.revision)) + '"';
  }
  function renderDocumentPlanCard(plan, workspace, context, route, position, total) {
    const active = String(plan.state || "active") === "active";
    const writable = documentWorkspaceState(workspace.lifecycle || workspace.state) === "draft";
    const canUpdate = Boolean(context.capabilities && context.capabilities["document-plan-update"] === true && active && writable);
    const canArchive = Boolean(context.capabilities && context.capabilities["document-plan-archive"] === true && active && writable);
    const canRestore = Boolean(context.capabilities && context.capabilities["document-plan-restore"] === true && !active && writable);
    const canReorder = Boolean(context.capabilities && context.capabilities["document-plan-reorder"] === true && active && writable);
    const attrs = documentWorkspaceDataAttrs(workspace, plan);
    const routeAttr = ' data-portal-route="' + safeText(route) + '"';
    const archiveButton = active
      ? '<button class="portal-button portal-button--quiet" type="button" data-portal-action="document-plan-archive"' + routeAttr + attrs + ' data-portal-confirm="Archive processing plan này? Metadata và history riêng tư vẫn được giữ."' + (canArchive ? "" : " disabled") + ">Archive</button>"
      : '<button class="portal-button portal-button--quiet" type="button" data-portal-action="document-plan-restore"' + routeAttr + attrs + (canRestore ? "" : " disabled") + ">Khôi phục</button>";
    const moves = active ? '<div class="portal-inline-actions"><button class="portal-button portal-button--quiet" type="button" data-portal-action="document-plan-reorder" data-document-plan-direction="up"' + routeAttr + attrs + (canReorder && position > 0 ? "" : " disabled") + '>Lên</button><button class="portal-button portal-button--quiet" type="button" data-portal-action="document-plan-reorder" data-document-plan-direction="down"' + routeAttr + attrs + (canReorder && position < total - 1 ? "" : " disabled") + ">Xuống</button></div>" : "";
    const sources = '<div class="portal-document-plan-meta"><span>Source: ' + safeText(documentWorkspaceAssetName(context, plan.source_asset_id)) + "</span><span>Ref: " + safeText(documentWorkspaceAssetName(context, plan.reference_asset_id)) + "</span><span>v" + safeText(String(plan.revision || 1)) + "</span></div>";
    const versions = Array.isArray(plan.versions) ? plan.versions.filter((item) => item && Number.isInteger(Number(item.revision))).slice(0, 20) : [];
    const canRestoreVersion = Boolean(context.capabilities && context.capabilities["document-plan-restore-version"] === true && active && writable);
    const history = versions.length ? '<div class="portal-document-plan-version-list">' + versions.map((version) => {
      const current = Number(version.revision) === Number(plan.revision);
      const restore = current ? '<span class="portal-form-note">Đang mở</span>' : '<button class="portal-button portal-button--quiet" type="button" data-portal-action="document-plan-restore-version" data-document-plan-version="' + safeText(String(version.revision)) + '"' + routeAttr + attrs + ' data-portal-confirm="Khôi phục v' + safeText(String(version.revision)) + ' thành revision plan mới?"' + (canRestoreVersion ? "" : " disabled") + '>Khôi phục v' + safeText(String(version.revision)) + '</button>';
      return '<article><span><strong>v' + safeText(String(version.revision)) + '</strong><small>' + safeText(String(version.instructions_excerpt || "")) + '</small></span>' + restore + '</article>';
    }).join("") + '</div>' : "";
    const form = '<form class="portal-form portal-document-plan-form" data-portal-form data-portal-action="document-plan-update"' + routeAttr + attrs + " novalidate>" + renderFields(documentPlanFields(context), canUpdate, context, documentPlanValues(plan)) + '<div class="portal-form-footer"><span class="portal-form-note">Lưu plan không đọc Asset Vault blob, không chạy utility/OCR/dịch và không tạo output.</span><button class="portal-button portal-button--primary" type="submit"' + (canUpdate ? "" : " disabled") + ">Lưu revision plan</button></div></form>";
    return '<article class="portal-document-plan-card' + (active ? "" : " is-archived") + '"><div class="portal-card-header"><div><span class="portal-section-kicker">' + safeText(documentWorkspaceOperationLabel(plan.operation)) + "</span><h3 class=\"portal-card-title\">" + safeText(String(plan.title || "Processing plan")) + "</h3><p class=\"portal-card-subtitle\">" + safeText(String(plan.instructions_excerpt || plan.instructions || "Chưa có scope plan hiển thị.")) + "</p></div>" + badge(active ? "ready" : "archived") + "</div>" + sources + renderDocumentWorkspaceTags(plan.tags) + '<div class="portal-inline-actions">' + archiveButton + moves + "</div>" + history + form + "</article>";
  }

  function documentWorkspaceStateActions(workspace, state, context, route) {
    const canLifecycle = Boolean(context.capabilities && context.capabilities["document-workspace-lifecycle"] === true);
    const attrs = documentWorkspaceDataAttrs(workspace, null);
    const routeAttr = ' data-portal-route="' + safeText(route) + '"';
    if (state === "archived") {
      return '<button class="portal-button portal-button--quiet" type="button" data-portal-action="document-workspace-state" data-document-workspace-state="draft"' + routeAttr + attrs + ' data-portal-confirm="Khôi phục document brief về Draft để tiếp tục biên tập?"' + (canLifecycle ? "" : " disabled") + ">Khôi phục về Draft</button>";
    }
    const reviewTarget = state === "draft" ? "review" : "draft";
    const reviewLabel = state === "draft" ? "Bắt đầu self-review" : "Trả về Draft";
    const reviewConfirm = state === "draft" ? "Chuyển document brief sang Self-review?" : "Trả document brief về Draft để tiếp tục biên tập?";
    return '<button class="portal-button portal-button--quiet" type="button" data-portal-action="document-workspace-state" data-document-workspace-state="' + reviewTarget + '"' + routeAttr + attrs + ' data-portal-confirm="' + reviewConfirm + '"' + (canLifecycle ? "" : " disabled") + ">" + reviewLabel + '</button><button class="portal-button portal-button--quiet" type="button" data-portal-action="document-workspace-state" data-document-workspace-state="approved"' + routeAttr + attrs + ' data-portal-confirm="Đánh dấu self-review hoàn tất? Điều này không đọc file, tạo output, job hoặc delivery."' + (canLifecycle && state === "review" ? "" : " disabled") + '>Đánh dấu review xong</button><button class="portal-button portal-button--quiet" type="button" data-portal-action="document-workspace-state" data-document-workspace-state="archived"' + routeAttr + attrs + ' data-portal-confirm="Archive document brief? Processing plan và history riêng tư vẫn được giữ."' + (canLifecycle ? "" : " disabled") + ">Archive brief</button>";
  }
  function renderDocumentWorkspaceVersions(workspace, versions, context, route) {
    if (!versions.length) return renderEmpty("Chưa có history", "Version đầu tiên xuất hiện khi document brief được lưu.", "↺");
    const canRestore = Boolean(context.capabilities && context.capabilities["document-workspace-restore-version"] === true && documentWorkspaceState(workspace.lifecycle || workspace.state) === "draft");
    const attrs = documentWorkspaceDataAttrs(workspace, null);
    return '<div class="portal-document-version-list">' + versions.map((version) => {
      const current = Number(version.revision) === Number(workspace.revision);
      const restore = current ? '<span class="portal-form-note">Đang mở</span>' : '<button class="portal-button portal-button--quiet" type="button" data-portal-action="document-workspace-restore-version" data-portal-route="' + safeText(route) + '"' + attrs + ' data-document-workspace-version="' + safeText(String(version.revision)) + '" data-portal-confirm="Khôi phục revision này thành một version mới?"' + (canRestore ? "" : " disabled") + ">Khôi phục v" + safeText(String(version.revision)) + "</button>";
      return "<article><div><strong>v" + safeText(String(version.revision)) + " · " + safeText(String(version.title || "Document brief")) + "</strong><p>" + safeText(String(version.objective_excerpt || version.objective || version.source_excerpt || version.source_summary || "")) + "</p><small>" + safeText(String(version.created_at || "—")) + "</small></div>" + restore + "</article>";
    }).join("") + "</div>";
  }
  function renderDocumentWorkspaceEvents(events) {
    if (!events.length) return '<p class="portal-form-note">Chưa có hoạt động được ghi nhận.</p>';
    return '<div class="portal-document-workspace-events">' + events.map((item) => '<div><span aria-hidden="true">•</span><span><strong>' + safeText(documentWorkspaceEventLabel(item.action)) + "</strong><small>v" + safeText(String(item.revision || 1)) + " · " + safeText(String(item.created_at || "—")) + "</small></span></div>").join("") + "</div>";
  }
  function renderDocumentWorkspaceDetail(page, context) {
    const detail = context.documentWorkspaceDetail && typeof context.documentWorkspaceDetail === "object" ? context.documentWorkspaceDetail : {};
    const workspace = detail.workspace && typeof detail.workspace === "object" && validDocumentWorkspaceId(detail.workspace.id) && String(detail.workspace.id) === String(page.recordId || "") ? detail.workspace : null;
    const canView = Boolean(context.capabilities && context.capabilities["document-workspace-view"] === true);
    if (!canView || !workspace) {
      const title = canView ? "Không tìm thấy document brief" : "Document & PDF Workspace đang được bảo vệ";
      const copy = canView ? "Server cần xác minh owner trước khi hiển thị brief, processing plan và history; dữ liệu cũ không được giữ trong browser." : "Đăng nhập bằng signed session và chờ feature flag server-side để mở brief của account hiện tại.";
      return '<article class="portal-page portal-document-workspace-detail">' + renderHero(page, context) + '<section class="portal-card portal-card-pad">' + renderEmpty(title, copy, ICONS.document) + '<div class="portal-form-footer"><a class="portal-button portal-button--primary" href="/document-workspace">Về Document Workspace</a></div></section></article>';
    }
    const route = page.routePath || page.path;
    const state = documentWorkspaceState(workspace.lifecycle || workspace.state);
    const writable = state === "draft";
    const canUpdate = Boolean(context.capabilities && context.capabilities["document-workspace-update"] === true && writable);
    const canPlanCreate = Boolean(context.capabilities && context.capabilities["document-plan-create"] === true && writable);
    const plans = Array.isArray(detail.plans) ? detail.plans.filter((item) => item && validDocumentPlanId(item.id) && String(item.workspace_id || "") === String(workspace.id)).slice(0, 250) : [];
    const activePlans = plans.filter((item) => String(item.state || "active") === "active");
    const versions = Array.isArray(detail.versions) ? detail.versions.filter((item) => item && Number.isInteger(Number(item.revision))).slice(0, 100) : [];
    const events = Array.isArray(detail.events) ? detail.events.filter((item) => item && typeof item === "object").slice(0, 24) : [];
    const estimate = detail.estimate && typeof detail.estimate === "object" ? detail.estimate : (context.documentWorkspaceEstimate && typeof context.documentWorkspaceEstimate === "object" ? context.documentWorkspaceEstimate : {});
    const attrs = documentWorkspaceDataAttrs(workspace, null);
    const summary = '<section class="portal-document-workspace-detail-summary"><div><span class="portal-section-kicker">' + safeText(documentWorkspaceTypeLabel(workspace.document_type)) + " · " + safeText(String(workspace.language || "—")) + "</span><h2>" + safeText(String(workspace.title || "Document brief")) + "</h2><p>" + safeText(String(workspace.objective || workspace.objective_excerpt || workspace.source_summary || workspace.source_excerpt || "Chưa có mục tiêu hiển thị.")) + "</p>" + renderDocumentWorkspaceTags(workspace.tags) + "</div><dl><div><dt>Trạng thái</dt><dd>" + safeText(DOCUMENT_WORKSPACE_STATES[state] || "Được bảo vệ") + "</dd></div><div><dt>Revision</dt><dd>v" + safeText(String(workspace.revision || 1)) + "</dd></div><div><dt>Plans</dt><dd>" + safeText(String(activePlans.length)) + "</dd></div></dl></section>";
    const editor = '<section class="portal-card portal-card-pad portal-document-workspace-editor"><div class="portal-card-header"><div><span class="portal-section-kicker">Document brief editor</span><h2 class="portal-card-title">Scope, target format & QA</h2><p class="portal-card-subtitle">Lưu bằng optimistic revision; self-review và archive là trạng thái server-side, không do browser tự suy diễn.</p></div>' + documentWorkspaceStateBadge(state) + '</div><form class="portal-form" data-portal-form data-portal-action="document-workspace-update" data-portal-route="' + safeText(route) + '"' + attrs + " novalidate>" + renderFields(documentWorkspaceFields(context), canUpdate, context, documentWorkspaceValues(workspace)) + '<div class="portal-form-footer"><span class="portal-form-note">Chỉ Draft có thể biên tập. Review, approved hoặc archived khóa plan và brief cho đến khi server trả về Draft.</span><div class="portal-inline-actions">' + documentWorkspaceStateActions(workspace, state, context, route) + '<button class="portal-button portal-button--primary" type="submit"' + (canUpdate ? "" : " disabled") + ">Lưu revision brief</button></div></div></form></section>";
    const estimateCard = state !== "draft"
      ? '<section class="portal-card portal-card-pad portal-document-workspace-estimate"><div class="portal-card-header"><div><span class="portal-section-kicker">Review estimate</span><h2 class="portal-card-title">Estimate đã được khóa</h2><p class="portal-card-subtitle">Document brief đang ở trạng thái self-review hoặc archive nên server không tính checklist lại. Trả về Draft khi bạn muốn tiếp tục chỉnh plan và review.</p></div>' + documentWorkspaceStateBadge(state) + "</div></section>"
      : documentWorkspaceEstimateMarkup(estimate, activePlans);
    const planCreate = '<section class="portal-card portal-card-pad portal-document-plan-create"><div class="portal-card-header"><div><span class="portal-section-kicker">Processing plan board</span><h2 class="portal-card-title">Thêm processing plan</h2><p class="portal-card-subtitle">Mỗi plan có intent, scope, Asset Vault metadata và history riêng. OCR, dịch và convert chỉ được ghi intent guarded, không chạy engine.</p></div>' + badge(canPlanCreate ? "ready" : "guarded") + '</div><form class="portal-form" data-portal-form data-portal-action="document-plan-create" data-portal-route="' + safeText(route) + '"' + attrs + " novalidate>" + renderFields(documentPlanFields(context), canPlanCreate, context, { operation: "organize" }) + '<div class="portal-form-footer"><span class="portal-form-note">Chỉ Asset Vault UUID metadata được gửi. Không có raw upload, file path, preview, provider/OCR/translation call hoặc output.</span><button class="portal-button portal-button--primary" type="submit"' + (canPlanCreate ? "" : " disabled") + ">Thêm processing plan</button></div></form></section>";
    const tools = '<section class="portal-card portal-card-pad"><div class="portal-card-header"><div><span class="portal-section-kicker">Separate deterministic utilities</span><h2 class="portal-card-title">Cần xử lý file đã được kiểm chứng?</h2><p class="portal-card-subtitle">Các utility PDF dưới đây là workflow Web-native riêng với input/output, history và policy riêng. Chúng không khởi chạy từ plan, không chia sẻ lifecycle và không biến brief thành output.</p></div>' + badge("read_only") + '</div><div class="portal-document-workspace-tool-links"><a class="portal-button portal-button--quiet" href="/documents/split">Tách PDF</a><a class="portal-button portal-button--quiet" href="/documents/merge">Gộp PDF</a><a class="portal-button portal-button--quiet" href="/documents/compress">Tối ưu PDF</a><a class="portal-button portal-button--quiet" href="/documents/image-to-pdf">Ảnh → PDF</a><a class="portal-button portal-button--quiet" href="/documents/pdf-to-images">PDF → ảnh</a><a class="portal-button portal-button--quiet" href="/documents/pdf-to-word">PDF text → Word</a></div></section>';
    const planCards = plans.length ? plans.map((plan, index) => renderDocumentPlanCard(plan, workspace, context, route, index, plans.length)).join("") : renderEmpty("Chưa có processing plan", "Thêm plan thủ công để tách scope và thứ tự review. Workspace không tự chạy tiện ích hoặc tạo file.", ICONS.document);
    const planLibrary = '<section class="portal-card portal-card-pad"><div class="portal-card-header"><div><span class="portal-section-kicker">Plan library</span><h2 class="portal-card-title">Thứ tự & review notes</h2><p class="portal-card-subtitle">Mọi card là metadata authoring. Asset name được hiển thị từ owner-scoped metadata, không phải file preview, path hay URL.</p></div></div><div class="portal-document-plan-grid">' + planCards + "</div></section>";
    const history = '<div class="portal-document-workspace-history-grid"><section class="portal-card portal-card-pad"><div class="portal-card-header"><div><span class="portal-section-kicker">Version history</span><h2 class="portal-card-title">Lịch sử document brief</h2><p class="portal-card-subtitle">Khôi phục version tạo revision mới, không xóa history cũ.</p></div></div>' + renderDocumentWorkspaceVersions(workspace, versions, context, route) + '</section><section class="portal-card portal-card-pad portal-document-workspace-activity"><div class="portal-card-header"><div><span class="portal-section-kicker">Audit-safe feed</span><h2 class="portal-card-title">Hoạt động gần đây</h2><p class="portal-card-subtitle">Feed chỉ hiển thị nhãn, revision và thời điểm; không chứa source text, asset path, URL, provider hay payment data.</p></div></div>' + renderDocumentWorkspaceEvents(events) + "</section></div>";
    return '<article class="portal-page portal-document-workspace-detail">' + renderHero(page, context) + summary + '<div class="portal-document-workspace-detail-grid">' + editor + estimateCard + "</div>" + planCreate + tools + planLibrary + history + renderDocumentWorkspaceBoundary() + "</article>";
  }

  // Subtitle & Transcript Workspace remains a text-only authoring boundary.

  // Subtitle & Transcript Workspace remains a text-only authoring boundary.
  // The preview below serializes user-authored cue metadata for review only;
  // it deliberately creates neither a subtitle file nor an ASR/translation/
  // TTS/dubbing job, and all text is escaped before it reaches the DOM.
  const SUBTITLE_STUDIO_FORMATS = Object.freeze([["srt", "SRT · text preview"], ["vtt", "WebVTT · text preview"]]);
  const SUBTITLE_STUDIO_INTENTS = Object.freeze([["subtitle", "Subtitle biên tập"], ["translation", "Bản nháp ngôn ngữ"], ["asr_review", "ASR review (không chạy ASR)"], ["dubbing_direction", "Dubbing direction (không tạo dubbing)"]]);
  const SUBTITLE_STUDIO_PROJECT_STATES = Object.freeze({
    draft: "Bản nháp", review: "Đang self-review", approved: "Self-review hoàn tất", archived: "Đã archive"
  });

  function validSubtitleStudioProjectId(value) { return validProjectId(value); }
  function validSubtitleStudioCueId(value) { return validProjectId(value); }
  function subtitleStudioState(value) {
    const state = String(value || "").toLowerCase();
    return Object.prototype.hasOwnProperty.call(SUBTITLE_STUDIO_PROJECT_STATES, state) ? state : "guarded";
  }
  function subtitleStudioStateLabel(value) { return SUBTITLE_STUDIO_PROJECT_STATES[subtitleStudioState(value)] || "Được bảo vệ"; }
  function subtitleStudioStateBadge(value) {
    const state = subtitleStudioState(value);
    return `<span class="portal-badge" data-status="${safeText(state)}">${safeText(subtitleStudioStateLabel(state))}</span>`;
  }
  function subtitleStudioTags(value) {
    return Array.isArray(value) ? value.filter((tag) => typeof tag === "string" && tag.trim()).slice(0, 20) : [];
  }
  function renderSubtitleStudioTags(value) {
    const tags = subtitleStudioTags(value);
    return tags.length ? `<div class="portal-subtitle-studio-tags">${tags.map((tag) => `<span>${safeText(tag)}</span>`).join("")}</div>` : "";
  }
  function subtitleStudioReferenceOptions(context) {
    const refs = context && context.subtitleStudioReferences && typeof context.subtitleStudioReferences === "object" ? context.subtitleStudioReferences : {};
    return (Array.isArray(refs.projects) ? refs.projects : []).filter((item) => item && validSubtitleStudioProjectId(item.id)).slice(0, 100)
      .map((item) => ({ value: String(item.id), label: String(item.title || "Project Web riêng tư") }));
  }
  function subtitleStudioProjectFields(context) {
    return [
      { name: "title", label: "Tên transcript project", placeholder: "Ví dụ: Launch summer — phụ đề Việt/Anh", required: true, minLength: 2, maxLength: 180 },
      { name: "source_language", label: "Ngôn ngữ nguồn", placeholder: "vi", required: true, minLength: 1, maxLength: 100 },
      { name: "target_language", label: "Ngôn ngữ bản nháp", placeholder: "en", required: true, minLength: 1, maxLength: 100, help: "Chỉ là nhãn bản nháp để bạn biên tập; không gọi dịch máy." },
      { name: "intent", label: "Mục đích workspace", control: "select", required: true, options: SUBTITLE_STUDIO_INTENTS, help: "Nhãn kiểm soát phạm vi; không kích hoạt ASR, dịch, TTS hoặc dubbing." },
      { name: "caption_format", label: "Chuẩn preview", control: "select", required: true, options: SUBTITLE_STUDIO_FORMATS },
      { name: "context", label: "Review context", control: "textarea", placeholder: "Mục đích hiển thị, thuật ngữ, quy tắc viết hoa và điểm cần tự rà soát…", maxLength: 5000, wide: true },
      { name: "tags", label: "Tags", placeholder: "launch, accessibility, review", maxLength: 1000 },
      { name: "project_id", label: "Project (tùy chọn)", control: "select", options: subtitleStudioReferenceOptions(context), emptyLabel: "Không liên kết Project" }
    ];
  }
  function subtitleStudioProjectValues(value) {
    const source = value && typeof value === "object" ? value : {};
    const format = String(source.caption_format || source.format || "").toLowerCase();
    return {
      title: String(source.title || ""), source_language: String(source.source_language || "vi"), target_language: String(source.target_language || "en"), intent: SUBTITLE_STUDIO_INTENTS.some(([key]) => key === String(source.intent || "")) ? String(source.intent) : "subtitle",
      caption_format: SUBTITLE_STUDIO_FORMATS.some(([key]) => key === format) ? format : "srt",
      context: String(source.context || source.review_context || ""), tags: subtitleStudioTags(source.tags).join(", "), project_id: String(source.project_id || "")
    };
  }
  function subtitleStudioCueFields() {
    return [
      { name: "start_ms", label: "Bắt đầu (ms)", type: "number", required: true, min: 0, max: 86399999, step: 1, inputMode: "numeric" },
      { name: "end_ms", label: "Kết thúc (ms)", type: "number", required: true, min: 1, max: 86400000, step: 1, inputMode: "numeric" },
      { name: "speaker", label: "Người nói (tùy chọn)", placeholder: "Ví dụ: MC", maxLength: 120 },
      { name: "source_text", label: "Caption nguồn", control: "textarea", placeholder: "Nhập nội dung caption do bạn đã có/quyền sử dụng…", required: true, minLength: 1, maxLength: 5000, wide: true, help: "URL xuất hiện trong lời nói hoặc text sẽ chỉ được hiển thị như văn bản, không thành liên kết." },
      { name: "translated_text", label: "Bản nháp ngôn ngữ", control: "textarea", placeholder: "Nhập/chỉnh bản nháp thủ công để review…", maxLength: 5000, wide: true, help: "Không gọi dịch máy; dòng trống chỉ có nghĩa là chưa có bản nháp." },
      { name: "notes", label: "Ghi chú biên tập", control: "textarea", placeholder: "Điểm xuống dòng, thuật ngữ, timing hoặc kiểm tra accessibility…", maxLength: 2000, wide: true }
    ];
  }
  function subtitleStudioImportFields() {
    return [
      { name: "format", label: "Chuẩn văn bản", control: "select", required: true, options: SUBTITLE_STUDIO_FORMATS },
      { name: "text", label: "Dán văn bản SRT/VTT", control: "textarea", placeholder: "Dán văn bản caption do bạn có quyền sử dụng. Không chọn file hoặc URL nguồn…", required: true, minLength: 1, maxLength: 60000, wide: true, help: "Server chỉ parse text và tạo cue authoring. URL xuất hiện trong caption sẽ là text, không được tải hoặc mở." }
    ];
  }
  function subtitleStudioCueValues(value) {
    const source = value && typeof value === "object" ? value : {};
    const start = Number(source.start_ms);
    const end = Number(source.end_ms);
    return {
      start_ms: Number.isInteger(start) && start >= 0 ? String(start) : "0", end_ms: Number.isInteger(end) && end > 0 ? String(end) : "1800",
      speaker: String(source.speaker || ""), source_text: String(source.source_text || ""), translated_text: String(source.translated_text || ""), notes: String(source.notes || "")
    };
  }
  function subtitleStudioTimecode(value, vtt) {
    const total = Math.max(0, Math.floor(Number(value) || 0));
    const hours = Math.floor(total / 3600000);
    const minutes = Math.floor((total % 3600000) / 60000);
    const seconds = Math.floor((total % 60000) / 1000);
    const millis = total % 1000;
    const pad = (number, width) => String(number).padStart(width, "0");
    return `${pad(hours, 2)}:${pad(minutes, 2)}:${pad(seconds, 2)}${vtt ? "." : ","}${pad(millis, 3)}`;
  }
  function subtitleStudioPreview(cues, format) {
    const vtt = String(format || "").toLowerCase() === "vtt";
    const lines = vtt ? ["WEBVTT", ""] : [];
    cues.filter((cue) => cue && String(cue.state || "active") === "active").forEach((cue, index) => {
      const source = String(cue.source_text || "").trim();
      const translation = String(cue.translated_text || "").trim();
      if (!source && !translation) return;
      if (!vtt) lines.push(String(index + 1));
      lines.push(`${subtitleStudioTimecode(cue.start_ms, vtt)} --> ${subtitleStudioTimecode(cue.end_ms, vtt)}`);
      if (cue.speaker) lines.push(`[${String(cue.speaker).trim()}]`);
      lines.push(source || "[Chưa có caption nguồn]");
      if (translation) lines.push(`→ ${translation}`);
      lines.push("");
    });
    return lines.join("\n") || (vtt ? "WEBVTT\n\n[Chưa có cue active]" : "[Chưa có cue active]");
  }
  function subtitleStudioEventLabel(value) {
    const labels = {
      project_created: "Đã tạo transcript project", project_updated: "Đã lưu transcript project", project_state_changed: "Đã đổi trạng thái review", project_version_restored: "Đã khôi phục version project",
      cue_created: "Đã thêm cue", cue_updated: "Đã lưu cue", cue_archived: "Đã archive cue", cue_restored: "Đã khôi phục cue", cue_version_restored: "Đã khôi phục version cue", cues_reordered: "Đã sắp xếp cue"
    };
    return labels[String(value || "")] || String(value || "subtitle_studio_updated").replace(/_/g, " ");
  }
  function renderSubtitleStudioBoundary() {
    return `<aside class="portal-card portal-card-pad portal-subtitle-studio-boundary"><div class="portal-card-header"><div><span class="portal-section-kicker">Text-only authoring boundary</span><h2 class="portal-card-title">Cue để review, không tạo media</h2><p class="portal-card-subtitle">Workspace lưu transcript và cue thuộc Web account. SRT/VTT chỉ có thể được parse hoặc sao chép dưới dạng văn bản tác giả; không upload, ASR, dịch máy, TTS, dubbing, player, tệp, URL media hay delivery được tạo ở đây.</p></div>${badge("guarded")}</div><div class="portal-subtitle-studio-guard-list"><span><strong>ASR / transcription</strong><em>guarded</em></span><span><strong>Translation provider</strong><em>guarded</em></span><span><strong>TTS / dubbing</strong><em>guarded</em></span><span><strong>Media/file delivery</strong><em>guarded</em></span></div></aside>`;
  }
  function renderSubtitleProjectCards(items, context) {
    const canView = Boolean(context.capabilities && context.capabilities["subtitle-studio-view"] === true);
    if (!items.length) return renderEmpty("Chưa có transcript project", "Tạo một project riêng tư để bắt đầu biên tập cue. Không có transcript hoặc file được tạo thay bạn.", ICONS.subtitle);
    return `<div class="portal-subtitle-project-grid">${items.map((item) => {
      const id = String(item.id || "");
      const state = subtitleStudioState(item.state);
      const language = `${String(item.source_language || "—")} → ${String(item.target_language || "—")}`;
      const intent = (SUBTITLE_STUDIO_INTENTS.find(([key]) => key === String(item.intent || "")) || ["", "Subtitle biên tập"])[1];
      return `<article class="portal-card portal-card-pad portal-subtitle-project-card"><div class="portal-card-header"><div><span class="portal-section-kicker">${safeText(String(item.caption_format || item.format || "SRT").toUpperCase())} · ${safeText(language)}</span><h3 class="portal-card-title">${safeText(String(item.title || "Transcript project"))}</h3><p class="portal-card-subtitle">${safeText(String(item.context_excerpt || item.context || "Chưa có review context hiển thị."))}</p></div>${subtitleStudioStateBadge(state)}</div><div class="portal-subtitle-project-meta"><span>${safeText(intent)}</span><span>${safeText(String(item.cue_count || 0))} cues</span><span>v${safeText(String(item.revision || 1))}</span></div>${renderSubtitleStudioTags(item.tags)}<div class="portal-form-footer"><span class="portal-form-note">${state === "approved" ? "Self-review đã đánh dấu" : state === "archived" ? "Đã archive · chỉ đọc" : "Đang biên tập"}</span>${canView && validSubtitleStudioProjectId(id) ? `<a class="portal-button portal-button--quiet" href="/subtitle-studio/${encodeURIComponent(id)}">Mở project <span aria-hidden="true">→</span></a>` : ""}</div></article>`;
    }).join("")}</div>`;
  }
  function renderSubtitleStudio(page, context) {
    const canView = Boolean(context.capabilities && context.capabilities["subtitle-studio-view"] === true);
    const canCreate = Boolean(context.capabilities && context.capabilities["subtitle-project-create"] === true);
    if (!canView) return `<article class="portal-page portal-subtitle-studio">${renderHero(page, context)}<section class="portal-card portal-card-pad">${renderEmpty("Subtitle Studio đang được bảo vệ", "Đăng nhập bằng signed session để mở transcript project riêng tư. Route này không dùng state của legacy subtitle, translate, dubbing hoặc ASR.", ICONS.subtitle)}</section></article>`;
    const summary = context.subtitleStudioSummary && typeof context.subtitleStudioSummary === "object" ? context.subtitleStudioSummary : {};
    const projects = Array.isArray(context.subtitleProjects) ? context.subtitleProjects.filter((item) => item && validSubtitleStudioProjectId(item.id)).slice(0, 100) : [];
    const stats = summary.projects && typeof summary.projects === "object" ? summary.projects : {};
    const total = Number(stats.total || projects.length);
    const review = Number(stats.review || 0);
    const approved = Number(stats.approved || 0);
    const values = { source_language: "vi", target_language: "en", intent: "subtitle", caption_format: "srt" };
    return `<article class="portal-page portal-subtitle-studio">${renderHero(page, context)}
      <section class="portal-subtitle-studio-intro"><div><span class="portal-section-kicker">Web-native subtitle authoring</span><h2>Biên tập transcript và caption có cấu trúc, dễ review.</h2><p>Tổ chức cue, timing, bản nháp ngôn ngữ và self-review trong không gian riêng tư. Đây là dữ liệu biên tập, không phải kết quả ASR, dịch, TTS, dubbing hay file xuất.</p></div><dl><div><dt>${safeText(String(total))}</dt><dd>Transcript projects</dd></div><div><dt>${safeText(String(review))}</dt><dd>Đang review</dd></div><div><dt>${safeText(String(approved))}</dt><dd>Self-review xong</dd></div></dl></section>
      <div class="portal-subtitle-studio-layout"><section class="portal-card portal-card-pad portal-subtitle-studio-create"><div class="portal-card-header"><div><span class="portal-section-kicker">New transcript project</span><h2 class="portal-card-title">Lập project subtitle</h2><p class="portal-card-subtitle">Đặt ngôn ngữ, chuẩn preview và review context trước khi thêm cue. Mỗi lần ghi được server kiểm tra session, CSRF, ownership, revision và idempotency.</p></div>${badge(canCreate ? "ready" : "guarded")}</div><form class="portal-form" data-portal-form data-portal-action="subtitle-project-create" data-portal-route="${safeText(page.routePath || page.path)}" novalidate>${renderFields(subtitleStudioProjectFields(context), canCreate, context, values)}<div class="portal-form-footer"><span class="portal-form-note">Không nhập secret, chứng từ thanh toán, provider/job/file handle hoặc URL vào metadata project.</span><button class="portal-button portal-button--primary" type="submit"${canCreate ? "" : " disabled"}>Tạo transcript project</button></div></form></section>${renderSubtitleStudioBoundary()}</div>
      <section class="portal-card portal-card-pad"><div class="portal-card-header"><div><span class="portal-section-kicker">Transcript library</span><h2 class="portal-card-title">Tiếp tục công việc</h2><p class="portal-card-subtitle">Danh sách chỉ hiển thị metadata/excerpt thuộc signed account. Mở project để nạp cue, preview text và version sau owner check.</p></div><button class="portal-button portal-button--quiet" type="button" data-portal-action="subtitle-studio-refresh" data-portal-route="/subtitle-studio">Làm mới</button></div>${renderSubtitleProjectCards(projects, context)}</section>
    </article>`;
  }

  function renderSubtitleCueCard(cue, project, context, route, order, total) {
    const cueId = String(cue.id || "");
    const active = String(cue.state || "active") === "active";
    const projectState = subtitleStudioState(project.state);
    const writable = projectState === "draft";
    const canUpdate = Boolean(active && writable && context.capabilities && context.capabilities["subtitle-cue-update"] === true);
    const canArchive = Boolean(active && writable && context.capabilities && context.capabilities["subtitle-cue-archive"] === true);
    const canRestore = Boolean(!active && writable && context.capabilities && context.capabilities["subtitle-cue-restore"] === true);
    const canRestoreVersion = Boolean(active && writable && context.capabilities && context.capabilities["subtitle-cue-restore-version"] === true);
    const canReorder = Boolean(active && writable && context.capabilities && context.capabilities["subtitle-cue-reorder"] === true);
    const versions = Array.isArray(cue.versions) ? cue.versions.filter((item) => item && Number.isInteger(Number(item.revision))).slice(0, 20) : [];
    const stateAction = active
      ? `<button class="portal-button portal-button--quiet" type="button" data-portal-action="subtitle-cue-archive" data-portal-route="${safeText(route)}" data-subtitle-project-id="${safeText(String(project.id))}" data-subtitle-project-revision="${safeText(String(project.revision))}" data-subtitle-cue-id="${safeText(cueId)}" data-subtitle-cue-revision="${safeText(String(cue.revision))}" data-portal-confirm="Archive cue này? History riêng tư vẫn được giữ để khôi phục."${canArchive ? "" : " disabled"}>Archive</button>`
      : `<button class="portal-button portal-button--quiet" type="button" data-portal-action="subtitle-cue-restore" data-portal-route="${safeText(route)}" data-subtitle-project-id="${safeText(String(project.id))}" data-subtitle-project-revision="${safeText(String(project.revision))}" data-subtitle-cue-id="${safeText(cueId)}" data-subtitle-cue-revision="${safeText(String(cue.revision))}"${canRestore ? "" : " disabled"}>Khôi phục</button>`;
    const history = versions.length ? `<div class="portal-subtitle-cue-history"><strong>Lịch sử cue</strong>${versions.map((version) => `<div><span>v${safeText(String(version.revision))} · ${safeText(String(version.created_at || "—"))}</span>${Number(version.revision) === Number(cue.revision) ? "<em>Đang mở</em>" : `<button class="portal-button portal-button--quiet" type="button" data-portal-action="subtitle-cue-restore-version" data-portal-route="${safeText(route)}" data-subtitle-project-id="${safeText(String(project.id))}" data-subtitle-project-revision="${safeText(String(project.revision))}" data-subtitle-cue-id="${safeText(cueId)}" data-subtitle-cue-revision="${safeText(String(cue.revision))}" data-subtitle-cue-version="${safeText(String(version.revision))}" data-portal-confirm="Khôi phục v${safeText(String(version.revision))} thành một revision cue mới?"${canRestoreVersion ? "" : " disabled"}>Khôi phục v${safeText(String(version.revision))}</button>`}</div>`).join("")}</div>` : "";
    const line = `${subtitleStudioTimecode(cue.start_ms, false)} → ${subtitleStudioTimecode(cue.end_ms, false)}`;
    return `<article class="portal-subtitle-cue-card${active ? "" : " is-archived"}"><div class="portal-card-header"><div><span class="portal-section-kicker">${safeText(active ? `Cue ${order + 1}` : "Archived cue")} · ${safeText(line)}</span><h3 class="portal-card-title">${safeText(String(cue.speaker || "Caption"))}</h3><p class="portal-card-subtitle">${safeText(String(cue.source_text || "Chưa có caption nguồn."))}</p>${String(cue.translated_text || "").trim() ? `<p class="portal-subtitle-cue-translation">${safeText(String(cue.translated_text))}</p>` : ""}</div>${badge(active ? "ready" : "archived")}</div><div class="portal-subtitle-cue-meta"><span>v${safeText(String(cue.revision || 1))}</span><span>${safeText(String(cue.notes || "Chưa có ghi chú"))}</span></div><div class="portal-inline-actions"><button class="portal-button portal-button--quiet" type="button" data-portal-action="subtitle-cue-reorder" data-subtitle-cue-direction="up" data-portal-route="${safeText(route)}" data-subtitle-project-id="${safeText(String(project.id))}" data-subtitle-project-revision="${safeText(String(project.revision))}" data-subtitle-cue-id="${safeText(cueId)}"${canReorder && order > 0 ? "" : " disabled"}>↑</button><button class="portal-button portal-button--quiet" type="button" data-portal-action="subtitle-cue-reorder" data-subtitle-cue-direction="down" data-portal-route="${safeText(route)}" data-subtitle-project-id="${safeText(String(project.id))}" data-subtitle-project-revision="${safeText(String(project.revision))}" data-subtitle-cue-id="${safeText(cueId)}"${canReorder && order >= 0 && order < total - 1 ? "" : " disabled"}>↓</button>${stateAction}</div><form class="portal-form portal-subtitle-cue-form" data-portal-form data-portal-action="subtitle-cue-update" data-portal-route="${safeText(route)}" data-subtitle-project-id="${safeText(String(project.id))}" data-subtitle-project-revision="${safeText(String(project.revision))}" data-subtitle-cue-id="${safeText(cueId)}" data-subtitle-cue-revision="${safeText(String(cue.revision))}" novalidate>${renderFields(subtitleStudioCueFields(), canUpdate, context, subtitleStudioCueValues(cue))}<div class="portal-form-footer"><span class="portal-form-note">URL trong caption chỉ là text; sửa cue không chạy ASR, dịch, TTS hoặc dubbing.</span><button class="portal-button portal-button--primary" type="submit"${canUpdate ? "" : " disabled"}>Lưu cue</button></div></form>${history}</article>`;
  }
  function renderSubtitleStudioDetail(page, context) {
    const detail = context.subtitleProjectDetail && typeof context.subtitleProjectDetail === "object" ? context.subtitleProjectDetail : {};
    const project = detail.project && typeof detail.project === "object" && validSubtitleStudioProjectId(detail.project.id) && String(detail.project.id) === String(page.recordId || "") ? detail.project : null;
    const canView = Boolean(context.capabilities && context.capabilities["subtitle-studio-view"] === true);
    if (!canView || !project) {
      const state = String(context.subtitleStudioReadState || "guarded");
      const title = !canView ? "Subtitle Studio đang được bảo vệ" : state === "loading" ? "Đang nạp transcript project riêng tư" : state === "failed" ? "Chưa thể nạp transcript project" : "Không tìm thấy transcript project";
      return `<article class="portal-page portal-subtitle-studio-detail">${renderHero(page, context)}<section class="portal-card portal-card-pad">${renderEmpty(title, "Server cần xác minh signed session và owner trước khi hiển thị cue, bản nháp ngôn ngữ và history; browser không giữ dữ liệu cũ.", ICONS.subtitle)}<div class="portal-form-footer"><a class="portal-button portal-button--primary" href="/subtitle-studio">Về Subtitle Studio</a></div></section></article>`;
    }
    const route = page.routePath || page.path;
    const state = subtitleStudioState(project.state);
    const writable = state === "draft";
    const canUpdate = Boolean(writable && context.capabilities && context.capabilities["subtitle-project-update"] === true);
    const canLifecycle = Boolean(context.capabilities && context.capabilities["subtitle-project-lifecycle"] === true);
    const canRestoreVersion = Boolean(writable && context.capabilities && context.capabilities["subtitle-project-restore-version"] === true);
    const canCueCreate = Boolean(writable && context.capabilities && context.capabilities["subtitle-cue-create"] === true);
    const canCueImport = Boolean(writable && context.capabilities && context.capabilities["subtitle-cue-import"] === true);
    const canTextExport = Boolean(context.capabilities && context.capabilities["subtitle-text-export"] === true && state !== "archived");
    const cues = Array.isArray(detail.cues) ? detail.cues.filter((item) => item && validSubtitleStudioCueId(item.id) && String(item.project_id || "") === String(project.id)).slice(0, 250) : [];
    const activeCues = cues.filter((item) => String(item.state || "active") === "active");
    const versions = Array.isArray(detail.versions) ? detail.versions.filter((item) => item && Number.isInteger(Number(item.revision))).slice(0, 100) : [];
    const events = Array.isArray(detail.events) ? detail.events.filter((item) => item && typeof item === "object").slice(0, 24) : [];
    const stateActions = state === "archived"
      ? `<button class="portal-button portal-button--quiet" type="button" data-portal-action="subtitle-project-state" data-subtitle-project-state="draft" data-portal-route="${safeText(route)}" data-subtitle-project-id="${safeText(String(project.id))}" data-subtitle-project-revision="${safeText(String(project.revision))}" data-portal-confirm="Khôi phục transcript project về Draft để tiếp tục biên tập?"${canLifecycle ? "" : " disabled"}>Khôi phục về Draft</button>`
      : `<button class="portal-button portal-button--quiet" type="button" data-portal-action="subtitle-project-state" data-subtitle-project-state="${state === "draft" ? "review" : "draft"}" data-portal-route="${safeText(route)}" data-subtitle-project-id="${safeText(String(project.id))}" data-subtitle-project-revision="${safeText(String(project.revision))}" data-portal-confirm="${state === "draft" ? "Chuyển project sang Self-review?" : "Trả project về Draft để tiếp tục biên tập?"}"${canLifecycle ? "" : " disabled"}>${state === "draft" ? "Bắt đầu self-review" : "Trả về Draft"}</button><button class="portal-button portal-button--quiet" type="button" data-portal-action="subtitle-project-state" data-subtitle-project-state="approved" data-portal-route="${safeText(route)}" data-subtitle-project-id="${safeText(String(project.id))}" data-subtitle-project-revision="${safeText(String(project.revision))}" data-portal-confirm="Đánh dấu self-review hoàn tất? Điều này không tạo ASR, dịch, TTS, dubbing hay file."${canLifecycle && state === "review" ? "" : " disabled"}>Đánh dấu review xong</button><button class="portal-button portal-button--quiet" type="button" data-portal-action="subtitle-project-state" data-subtitle-project-state="archived" data-portal-route="${safeText(route)}" data-subtitle-project-id="${safeText(String(project.id))}" data-subtitle-project-revision="${safeText(String(project.revision))}" data-portal-confirm="Archive transcript project? Cue và history vẫn được giữ riêng tư."${canLifecycle ? "" : " disabled"}>Archive project</button>`;
    const versionMarkup = versions.length ? `<div class="portal-subtitle-version-list">${versions.map((version) => `<article><div><strong>v${safeText(String(version.revision))} · ${safeText(String(version.title || "Transcript project"))}</strong><p>${safeText(String(version.context_excerpt || version.context || ""))}</p><small>${safeText(String(version.created_at || "—"))}</small></div>${Number(version.revision) === Number(project.revision) ? "<span class=\"portal-form-note\">Đang mở</span>" : `<button class="portal-button portal-button--quiet" type="button" data-portal-action="subtitle-project-restore-version" data-portal-route="${safeText(route)}" data-subtitle-project-id="${safeText(String(project.id))}" data-subtitle-project-revision="${safeText(String(project.revision))}" data-subtitle-project-version="${safeText(String(version.revision))}" data-portal-confirm="Khôi phục v${safeText(String(version.revision))} thành một revision project mới?"${canRestoreVersion ? "" : " disabled"}>Khôi phục v${safeText(String(version.revision))}</button>`}</article>`).join("")}</div>` : renderEmpty("Chưa có history", "Version đầu tiên xuất hiện khi transcript project được lưu.", "↺");
    let order = 0;
    const cueMarkup = cues.length ? cues.map((cue) => {
      const active = String(cue.state || "active") === "active";
      const index = active ? order++ : -1;
      return renderSubtitleCueCard(cue, project, context, route, index, activeCues.length);
    }).join("") : renderEmpty("Chưa có cue", "Thêm cue thủ công để bắt đầu biên tập timing và caption. Workspace không tạo transcript thay bạn.", ICONS.subtitle);
    const preview = subtitleStudioPreview(activeCues, project.caption_format || project.format);
    const estimate = detail.estimate && typeof detail.estimate === "object" ? detail.estimate : (context.subtitleProjectEstimate && typeof context.subtitleProjectEstimate === "object" ? context.subtitleProjectEstimate : {});
    const estimateMarkup = state === "archived" ? `<section class="portal-card portal-card-pad portal-subtitle-runtime-estimate"><div class="portal-card-header"><div><span class="portal-section-kicker">Timeline estimate</span><h2 class="portal-card-title">Estimate đã được khóa</h2><p class="portal-card-subtitle">Project đang archive nên cue và estimate không được tính lại. Khôi phục về Draft khi muốn tiếp tục review.</p></div>${badge("archived")}</div></section>` : `<section class="portal-card portal-card-pad portal-subtitle-runtime-estimate"><div class="portal-card-header"><div><span class="portal-section-kicker">Timeline estimate</span><h2 class="portal-card-title">Kiểm tra timing cục bộ</h2><p class="portal-card-subtitle">${safeText(String(estimate.message || "Tổng hợp timing từ cue hiện tại; không đọc media, không chạy ASR hoặc render."))}</p></div>${badge("read_only")}</div><div class="portal-subtitle-estimate-grid"><span><strong>${safeText(String(estimate.cue_count ?? activeCues.length))}</strong> cues active</span><span><strong>${safeText(String(estimate.duration_ms ?? "—"))}</strong> ms metadata</span><span><strong>${safeText(String(estimate.overlap_count ?? 0))}</strong> overlaps cần review</span></div></section>`;
    return `<article class="portal-page portal-subtitle-studio-detail">${renderHero(page, context)}
      <section class="portal-subtitle-studio-detail-summary"><div><span class="portal-section-kicker">${safeText(String(project.caption_format || project.format || "srt").toUpperCase())} · ${safeText(String(project.source_language || "—"))} → ${safeText(String(project.target_language || "—"))}</span><h2>${safeText(String(project.title || "Transcript project"))}</h2><p>${safeText(String(project.context || project.context_excerpt || "Chưa có review context hiển thị."))}</p>${renderSubtitleStudioTags(project.tags)}</div><dl><div><dt>Intent</dt><dd>${safeText((SUBTITLE_STUDIO_INTENTS.find(([key]) => key === String(project.intent || "")) || ["", "Subtitle biên tập"])[1])}</dd></div><div><dt>Revision</dt><dd>v${safeText(String(project.revision || 1))}</dd></div><div><dt>Cues</dt><dd>${safeText(String(activeCues.length))}</dd></div></dl></section>
      <div class="portal-subtitle-studio-detail-grid"><section class="portal-card portal-card-pad portal-subtitle-studio-editor"><div class="portal-card-header"><div><span class="portal-section-kicker">Project editor</span><h2 class="portal-card-title">Ngôn ngữ & review context</h2><p class="portal-card-subtitle">Lưu bằng optimistic revision; self-review và archive là trạng thái server-side, không do browser tự suy diễn.</p></div>${subtitleStudioStateBadge(state)}</div><form class="portal-form" data-portal-form data-portal-action="subtitle-project-update" data-portal-route="${safeText(route)}" data-subtitle-project-id="${safeText(String(project.id))}" data-subtitle-project-revision="${safeText(String(project.revision))}" novalidate>${renderFields(subtitleStudioProjectFields(context), canUpdate, context, subtitleStudioProjectValues(project))}<div class="portal-form-footer"><span class="portal-form-note">Chỉ Draft có thể biên tập. Khi đang self-review, approved hoặc archived, hãy dùng “Trả về Draft” sau khi server xác nhận.</span><div class="portal-inline-actions">${stateActions}<button class="portal-button portal-button--primary" type="submit"${canUpdate ? "" : " disabled"}>Lưu revision project</button></div></div></form></section>${estimateMarkup}</div>
      <section class="portal-card portal-card-pad portal-subtitle-cue-create"><div class="portal-card-header"><div><span class="portal-section-kicker">Manual cue authoring</span><h2 class="portal-card-title">Thêm cue thủ công</h2><p class="portal-card-subtitle">Cue có timing, caption nguồn, bản nháp ngôn ngữ và history riêng. Server kiểm tra thứ tự/revision trước khi lưu.</p></div>${badge(canCueCreate ? "ready" : "guarded")}</div><form class="portal-form" data-portal-form data-portal-action="subtitle-cue-create" data-portal-route="${safeText(route)}" data-subtitle-project-id="${safeText(String(project.id))}" data-subtitle-project-revision="${safeText(String(project.revision))}" novalidate>${renderFields(subtitleStudioCueFields(), canCueCreate, context, { start_ms: "0", end_ms: "1800" })}<div class="portal-form-footer"><span class="portal-form-note">Không upload hoặc tạo ASR/dịch/TTS/dubbing. URL trong caption hợp lệ sẽ chỉ là text để review.</span><button class="portal-button portal-button--primary" type="submit"${canCueCreate ? "" : " disabled"}>Thêm cue</button></div></form></section>
      <section class="portal-card portal-card-pad portal-subtitle-text-import"><div class="portal-card-header"><div><span class="portal-section-kicker">Text-only import</span><h2 class="portal-card-title">Dán & parse SRT/VTT</h2><p class="portal-card-subtitle">Chỉ dán văn bản tác giả để server parse thành cue có revision/owner check. Không chọn file, không upload, không gọi ASR hoặc dịch máy.</p></div>${badge(canCueImport ? "ready" : "guarded")}</div><form class="portal-form" data-portal-form data-portal-action="subtitle-cue-import" data-portal-route="${safeText(route)}" data-subtitle-project-id="${safeText(String(project.id))}" data-subtitle-project-revision="${safeText(String(project.revision))}" novalidate>${renderFields(subtitleStudioImportFields(), canCueImport, context, { format: String(project.caption_format || project.format || "srt") })}<div class="portal-form-footer"><span class="portal-form-note">Trong Draft, thao tác này sẽ archive toàn bộ cue active rồi thay bằng cue đã parse; history cũ vẫn được giữ. URL trong caption chỉ là text.</span><button class="portal-button portal-button--primary" type="submit" data-portal-confirm="Xác nhận: archive toàn bộ cue active và thay bằng cue parse từ văn bản tác giả này? History cũ vẫn được giữ; không đọc file hoặc tạo output media."${canCueImport ? "" : " disabled"}>Parse & thay cue active</button></div></form></section>
      <div class="portal-subtitle-preview-grid"><section class="portal-card portal-card-pad portal-subtitle-text-preview"><div class="portal-card-header"><div><span class="portal-section-kicker">${safeText(String(project.caption_format || project.format || "srt").toUpperCase())} text preview</span><h2 class="portal-card-title">Preview để rà soát định dạng</h2><p class="portal-card-subtitle">Đây là văn bản dựng từ cue active để review. Bạn có thể yêu cầu server trả văn bản tương đương rồi sao chép; không có file, output provider hoặc delivery.</p></div>${badge("read_only")}</div><pre class="portal-subtitle-preview-text">${safeText(preview)}</pre><div class="portal-form-footer"><span class="portal-form-note">Sao chép text không tạo download, tệp hoặc trạng thái completed.</span><div class="portal-inline-actions"><button class="portal-button portal-button--quiet" type="button" data-portal-action="subtitle-text-export" data-portal-route="${safeText(route)}" data-subtitle-project-id="${safeText(String(project.id))}" data-subtitle-export-format="srt"${canTextExport ? "" : " disabled"}>Sao chép SRT text</button><button class="portal-button portal-button--quiet" type="button" data-portal-action="subtitle-text-export" data-portal-route="${safeText(route)}" data-subtitle-project-id="${safeText(String(project.id))}" data-subtitle-export-format="vtt"${canTextExport ? "" : " disabled"}>Sao chép VTT text</button></div></div></section>${renderSubtitleStudioBoundary()}</div>
      <section class="portal-card portal-card-pad"><div class="portal-card-header"><div><span class="portal-section-kicker">Ordered cue timeline</span><h2 class="portal-card-title">Cue timeline & bản nháp ngôn ngữ</h2><p class="portal-card-subtitle">Dùng mũi tên để đổi thứ tự active cue. Browser gửi toàn bộ sequence cùng revision project để tránh ghi đè im lặng.</p></div></div><div class="portal-subtitle-cue-grid">${cueMarkup}</div></section>
      <div class="portal-subtitle-studio-history-grid"><section class="portal-card portal-card-pad"><div class="portal-card-header"><div><span class="portal-section-kicker">Version history</span><h2 class="portal-card-title">Lịch sử transcript project</h2><p class="portal-card-subtitle">Khôi phục version tạo revision mới, không xóa history cũ.</p></div></div>${versionMarkup}</section><section class="portal-card portal-card-pad portal-subtitle-studio-activity"><div class="portal-card-header"><div><span class="portal-section-kicker">Audit-safe feed</span><h2 class="portal-card-title">Hoạt động gần đây</h2><p class="portal-card-subtitle">Feed chỉ hiển thị nhãn, revision và thời điểm; không đưa raw cue text vào audit view.</p></div></div>${events.length ? `<div class="portal-subtitle-studio-events">${events.map((item) => `<div><span aria-hidden="true">•</span><span><strong>${safeText(subtitleStudioEventLabel(item.action))}</strong><small>v${safeText(String(item.revision || 1))} · ${safeText(String(item.created_at || "—"))}</small></span></div>`).join("")}</div>` : "<p class=\"portal-form-note\">Chưa có hoạt động được ghi nhận.</p>"}</section></div>
    </article>`;
  }

  function renderStudioDocumentEditor(page, context, project) {
    const detail = context.studioDocumentDetail && typeof context.studioDocumentDetail === "object" ? context.studioDocumentDetail : {};
    const document = detail.document && typeof detail.document === "object" && validProjectId(detail.document.id) ? detail.document : null;
    if (!document || String(document.project_id || "") !== String(project.id || "")) {
      return `<section class="portal-card portal-card-pad portal-project-editor"><div class="portal-card-header"><div><h2 class="portal-card-title">Studio Document editor</h2><p class="portal-card-subtitle">Chọn một tài liệu để chỉnh sửa và xem history phiên bản.</p></div>${badge("read_only")}</div>${renderEmpty("Chưa chọn tài liệu", "Mở một Studio Document từ danh sách bên trái. Nội dung chỉ được nạp sau owner check trên server.", "✦")}</section>`;
    }
    const canEdit = Boolean(context.capabilities && context.capabilities["studio-document-update"] === true && String(document.state || "active") === "active");
    const versions = Array.isArray(detail.versions) ? detail.versions.filter((item) => item && Number.isInteger(Number(item.revision))).slice(0, 50) : [];
    const formId = `portal-studio-document-${safeText(String(document.id))}`;
    const versionList = versions.length ? `<div class="portal-version-list">${versions.map((version) => `<div class="portal-version-row"><span><strong>v${safeText(String(version.revision))}</strong><small>${safeText(String(version.title || "Studio Document"))} · ${safeText(String(version.created_at || "—"))}</small></span>${Number(version.revision) === Number(document.revision) ? `<span class="portal-form-note">Đang mở</span>` : `<button class="portal-button portal-button--quiet" type="button" data-portal-action="studio-document-restore" data-portal-route="${safeText(page.routePath || page.path)}" data-studio-document-id="${safeText(String(document.id))}" data-studio-document-revision="${safeText(String(document.revision))}" data-studio-document-version="${safeText(String(version.revision))}" data-portal-confirm="Khôi phục v${safeText(String(version.revision))} thành một phiên bản mới? Nội dung hiện tại vẫn được giữ trong history."${canEdit ? "" : " disabled"}>Khôi phục</button>`}</div>`).join("")}</div>` : renderEmpty("Chưa có history", "Phiên bản đầu tiên sẽ xuất hiện sau khi Studio Document được tạo.", "○");
    return `<section class="portal-card portal-card-pad portal-project-editor"><div class="portal-card-header"><div><span class="portal-section-kicker">${safeText(String(document.kind || "document"))}</span><h2 class="portal-card-title">${safeText(String(document.title || "Studio Document"))}</h2><p class="portal-card-subtitle">Phiên bản v${safeText(String(document.revision))} · chỉ Web account hiện tại có quyền đọc/sửa.</p></div>${badge(projectState(document.state))}</div><form id="${formId}" class="portal-form" data-portal-form data-portal-action="studio-document-update" data-portal-route="${safeText(page.routePath || page.path)}" data-studio-document-id="${safeText(String(document.id))}" data-studio-document-revision="${safeText(String(document.revision))}" novalidate><label class="portal-field"><span>Tên tài liệu</span><input class="portal-input" name="title" value="${safeText(String(document.title || ""))}" minlength="3" maxlength="160" required${canEdit ? "" : " disabled"}></label><label class="portal-field"><span>Nội dung</span><textarea class="portal-input portal-textarea" name="content" minlength="1" maxlength="12000" required${canEdit ? "" : " disabled"}>${safeText(String(document.content || ""))}</textarea><small>Mỗi lần lưu sẽ tạo revision mới; không lưu secret, token, mật khẩu hoặc số thẻ.</small></label><div class="portal-form-footer"><span class="portal-form-note">Optimistic versioning bảo vệ thay đổi đang mở khỏi ghi đè im lặng.</span><button class="portal-button portal-button--primary" type="submit"${canEdit ? "" : " disabled"}>Lưu phiên bản mới</button></div></form><section class="portal-project-history"><div class="portal-section-heading"><div><span class="portal-section-kicker">Version history</span><h3>Lịch sử phiên bản</h3><p>Khôi phục luôn tạo revision mới; không xoá lịch sử cũ.</p></div></div>${versionList}</section></section>`;
  }

  function validProjectPackageId(value) {
    return validProjectId(value);
  }

  function projectPackageItems(context, projectId) {
    return (Array.isArray(context.projectPackages) ? context.projectPackages : [])
      .filter((item) => item && typeof item === "object" && validProjectPackageId(item.id)
        && (!projectId || String(item.project_id || "") === String(projectId)))
      .slice(0, 100);
  }

  function projectPackageDownloadPath(item) {
    const packageId = String(item && item.id || "").trim();
    return validProjectPackageId(packageId) && item && item.download_ready === true
      ? `/api/v1/project-packages/${encodeURIComponent(packageId)}/download`
      : "";
  }

  function renderProjectPackageCards(items, context) {
    if (!items.length) return renderEmpty("Chưa có Project Package", "Khi bạn xuất package, Web App sẽ tạo một snapshot ZIP bất biến sau khi kiểm tra file private. Không tạo Job Bot hoặc delivery giả.", "▤");
    return `<div class="portal-project-package-grid">${items.map((item) => {
      const state = String(item.state || "guarded");
      const downloadPath = projectPackageDownloadPath(item);
      const events = context.projectPackageEvents && context.projectPackageEvents[String(item.id)];
      const latestEvent = Array.isArray(events) && events.length ? events[events.length - 1] : null;
      const filename = String(item.original_filename || "Project Package riêng tư");
      return `<article class="portal-card portal-card-pad portal-project-package-card"><div class="portal-card-header"><div class="portal-project-package-title"><span class="portal-project-package-icon" aria-hidden="true">ZIP</span><div><h3 class="portal-card-title">${safeText(filename)}</h3><p class="portal-card-subtitle">${safeText(String(item.document_count || 0))} Studio Document · ${safeText(String(item.asset_reference_count || 0))} tham chiếu Asset Vault</p></div></div>${badge(state)}</div><dl class="portal-project-package-meta"><div><dt>Artifact</dt><dd>${safeText(item.byte_size ? vaultBytes(item.byte_size) : "Đang kiểm tra")}</dd></div><div><dt>Cập nhật</dt><dd>${safeText(String(item.completed_at || item.updated_at || item.created_at || "—"))}</dd></div><div><dt>Luồng</dt><dd>${safeText(latestEvent && latestEvent.state ? String(latestEvent.state) : state)}</dd></div></dl><div class="portal-form-footer">${downloadPath ? `<a class="portal-button portal-button--primary" href="${safeText(downloadPath)}" rel="noreferrer">Tải ZIP <span aria-hidden="true">↓</span></a>` : `<span class="portal-form-note">ZIP chỉ mở tải sau khi server xác minh byte size và integrity.</span>`}</div></article>`;
    }).join("")}</div>`;
  }

  function renderProjectPackagePanel(page, context, project) {
    const canView = Boolean(context.capabilities && context.capabilities["project-package-view"] === true);
    const canExport = Boolean(context.capabilities && context.capabilities["project-package-export"] === true && String(project.state || "active") === "active");
    const canRefresh = Boolean(context.capabilities && context.capabilities["project-package-refresh"] === true);
    if (!canView) {
      return `<section class="portal-card portal-card-pad portal-project-package-panel"><div class="portal-state" data-state="guarded"><span class="portal-state-icon" aria-hidden="true">${safeText(ICONS.package)}</span><div><h2>Project Package đang ở chế độ an toàn</h2><p>Xuất ZIP chỉ bật khi môi trường có persistent storage riêng. Không có fallback sang static, browser storage, Asset Vault hoặc Job Bot.</p><div class="portal-state-meta"><span>Snapshot Web-owned</span><span>Không có provider call</span><span>Không có output giả</span></div></div></div></section>`;
    }
    const route = page.routePath || page.path;
    const items = projectPackageItems(context, project.id);
    return `<section class="portal-card portal-card-pad portal-project-package-panel"><div class="portal-card-header"><div><span class="portal-section-kicker">Immutable export</span><h2 class="portal-card-title">Project Package</h2><p class="portal-card-subtitle">Đóng gói snapshot hiện tại của Project và Studio Document thành ZIP riêng tư. Asset Vault chỉ hiện metadata tham chiếu, không sao chép source blob.</p></div>${badge(canExport ? "ready" : "guarded")}</div><div class="portal-project-package-actions"><div><strong>Snapshot → verify → attachment</strong><span>Package/Web export không tạo Job Bot, charge Xu, PayOS hay provider request.</span></div><div class="portal-inline-actions"><button class="portal-button portal-button--quiet" type="button" data-portal-action="project-package-refresh" data-portal-route="${safeText(route)}" data-project-id="${safeText(String(project.id))}"${canRefresh ? "" : " disabled"}>Làm mới</button><button class="portal-button portal-button--primary" type="button" data-portal-action="project-package-export" data-portal-route="${safeText(route)}" data-project-id="${safeText(String(project.id))}" data-portal-confirm="Xuất Project Package sẽ tạo một snapshot ZIP bất biến của Studio Document hiện tại. Bạn có muốn tiếp tục?"${canExport ? "" : " disabled"}>Xuất Project Package</button></div></div><div class="portal-project-package-list">${renderProjectPackageCards(items, context)}</div><div class="portal-form-footer"><a class="portal-button portal-button--quiet" href="/project-packages">Xem tất cả Project Packages →</a></div></section>`;
  }

  function renderProjectPackages(page, context) {
    const canView = Boolean(context.capabilities && context.capabilities["project-package-view"] === true);
    const canRefresh = Boolean(context.capabilities && context.capabilities["project-package-refresh"] === true);
    if (!canView) return `<article class="portal-page portal-project-packages">${renderHero(page, context)}<section class="portal-card portal-card-pad"><div class="portal-state" data-state="guarded"><span class="portal-state-icon" aria-hidden="true">${safeText(ICONS.package)}</span><div><h2>Project Packages chưa được bật</h2><p>Capability này chỉ xuất hiện khi server có storage riêng, bền vững và không thuộc static/PWA cache.</p></div></div></section></article>`;
    const items = projectPackageItems(context);
    const projectNames = new Map((Array.isArray(context.projects) ? context.projects : [])
      .filter((project) => project && validProjectId(project.id))
      .map((project) => [String(project.id), String(project.title || "Project Web")]));
    const cards = items.length ? `<div class="portal-project-package-grid">${items.map((item) => {
      const downloadPath = projectPackageDownloadPath(item);
      const projectName = projectNames.get(String(item.project_id || "")) || "Project riêng tư";
      return `<article class="portal-card portal-card-pad portal-project-package-card"><div class="portal-card-header"><div class="portal-project-package-title"><span class="portal-project-package-icon" aria-hidden="true">ZIP</span><div><h2 class="portal-card-title">${safeText(projectName)}</h2><p class="portal-card-subtitle">${safeText(String(item.original_filename || "Project Package"))}</p></div></div>${badge(String(item.state || "guarded"))}</div><dl class="portal-project-package-meta"><div><dt>Documents</dt><dd>${safeText(String(item.document_count || 0))}</dd></div><div><dt>Artifact</dt><dd>${safeText(item.byte_size ? vaultBytes(item.byte_size) : "Đang kiểm tra")}</dd></div><div><dt>Cập nhật</dt><dd>${safeText(String(item.completed_at || item.updated_at || "—"))}</dd></div></dl><div class="portal-form-footer">${downloadPath ? `<a class="portal-button portal-button--primary" href="${safeText(downloadPath)}" rel="noreferrer">Tải ZIP <span aria-hidden="true">↓</span></a>` : `<a class="portal-button portal-button--quiet" href="/projects/${encodeURIComponent(String(item.project_id || ""))}">Mở Project</a>`}</div></article>`;
    }).join("")}</div>` : renderEmpty("Chưa có Project Package", "Mở một Project để xuất snapshot ZIP đầu tiên. Tính năng này độc lập với Bot và không tạo charge hay provider request.", "▤");
    return `<article class="portal-page portal-project-packages">${renderHero(page, context)}<section class="portal-project-package-intro"><div><span class="portal-section-kicker">Private Web exports</span><h2>Snapshot có thể giao, không trộn với Job Bot</h2><p>Mỗi Package là artifact ZIP bất biến tạo từ Project Web. File chỉ xuất hiện sau khi server kiểm tra storage riêng, byte size và integrity.</p></div><dl><div><dt>${safeText(String(items.length))}</dt><dd>Package thuộc account</dd></div><div><dt>ZIP</dt><dd>Attachment riêng tư</dd></div></dl></section><section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Lịch sử Project Packages</h2><p class="portal-card-subtitle">Không phải Gói dịch vụ, Tài sản Bot hay output provider. Chỉ snapshot Web-owned được kiểm tra.</p></div><button class="portal-button portal-button--quiet" type="button" data-portal-action="project-package-refresh" data-portal-route="/project-packages"${canRefresh ? "" : " disabled"}>Làm mới</button></div>${cards}</section></article>`;
  }

  function renderProjectDetail(page, context) {
    const detail = context.projectDetail && typeof context.projectDetail === "object" ? context.projectDetail : {};
    const project = detail && validProjectId(detail.id) ? detail : null;
    if (!project) return `<article class="portal-page">${renderHero(page, context)}<section class="portal-card portal-card-pad">${renderEmpty("Không tìm thấy Project", "Project có thể không thuộc account hiện tại hoặc đã không còn khả dụng. Portal không suy đoán hay hiển thị dữ liệu của account khác.", "⌁")}<div class="portal-form-footer"><a class="portal-button portal-button--primary" href="/projects">Về Project Center</a></div></section></article>`;
    const documents = (Array.isArray(context.projectDocuments) ? context.projectDocuments : []).filter((item) => item && typeof item === "object" && validProjectId(item.id)).slice(0, 100);
    const canCreate = Boolean(context.capabilities && context.capabilities["studio-document-create"] === true && String(project.state || "active") === "active");
    const route = page.routePath || page.path;
    const documentCards = documents.length ? `<div class="portal-project-document-list">${documents.map((document) => `<button type="button" class="portal-project-document" data-portal-action="studio-document-open" data-portal-route="${safeText(route)}" data-studio-document-id="${safeText(String(document.id))}"><span class="portal-project-document-icon" aria-hidden="true">${safeText(ICONS.prompt)}</span><span><strong>${safeText(String(document.title || "Studio Document"))}</strong><small>${safeText(String(document.kind || "document"))} · v${safeText(String(document.revision || 1))} · ${safeText(String(document.updated_at || "—"))}</small></span>${badge(projectState(document.state))}<b aria-hidden="true">→</b></button>`).join("")}</div>` : renderEmpty("Chưa có Studio Document", "Tạo brief, prompt, caption, kịch bản hoặc storyboard đầu tiên cho Project này.", "✦");
    return `<article class="portal-page portal-project-detail">${renderHero(page, context)}<section class="portal-project-summary"><div><span class="portal-section-kicker">Independent Web Project</span><h2>${safeText(String(project.title || "Project"))}</h2><p>${safeText(String(project.summary || "Chưa có tóm tắt"))}</p></div><dl><div><dt>Mục tiêu</dt><dd>${safeText(String(project.objective || "Chưa đặt"))}</dd></div><div><dt>Trạng thái</dt><dd>${badge(projectState(project.state))}</dd></div><div><dt>Documents</dt><dd>${safeText(String(documents.length))}</dd></div></dl></section><div class="portal-project-detail-grid"><section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Studio Documents</h2><p class="portal-card-subtitle">Tài liệu authoring được lưu/version trên Web, không cần Telegram hoặc Bot bridge.</p></div><a class="portal-button portal-button--quiet" href="/projects">Tất cả Project</a></div>${documentCards}<section class="portal-project-new-document"><div class="portal-section-heading"><div><span class="portal-section-kicker">Add document</span><h3>Thêm Studio Document</h3><p>Mỗi tài liệu mới bắt đầu ở v1 và có history riêng.</p></div></div><form class="portal-form" data-portal-form data-portal-action="studio-document-create" data-portal-route="${safeText(route)}" data-project-id="${safeText(String(project.id))}" novalidate>${renderFields(projectDocumentFormFields(), canCreate, context, transientFormValues(route))}<div class="portal-form-footer"><span class="portal-form-note">Không gọi provider hoặc tạo media output; đây là authoring workspace độc lập.</span><button class="portal-button portal-button--primary" type="submit"${canCreate ? "" : " disabled"}>Thêm Studio Document</button></div></form></section></section>${renderStudioDocumentEditor(page, context, project)}</div>${renderProjectPackagePanel(page, context, project)}</article>`;
  }

  function renderFeatureFamily(page, context) {
    const family = featureCatalogGroup(page.featureFamily);
    if (!family) return renderNotFound({ ...page, layout: "not-found", title: "Nhóm tính năng chưa được công bố" }, context);
    const entries = registeredFeatureFamilyEntries(context, family.key);
    const states = entries.reduce((counts, entry) => {
      const route = catalogEntryRoute(entry);
      const module = route ? manifest[normalizePath(route)] : null;
      const state = catalogEntryState(entry, module || { path: route || page.path, status: "guarded" }, context);
      counts[state] = (counts[state] || 0) + 1;
      return counts;
    }, Object.create(null));
    const otherFamilies = FEATURE_FAMILY_KEYS.map(featureCatalogGroup).filter((group) => group && group.key !== family.key);
    const familyNav = `<nav class="portal-feature-jumps" aria-label="Chuyển nhóm AI Studio"><a class="portal-feature-jump" href="/features">Tất cả công cụ</a>${otherFamilies.map((group) => `<a class="portal-feature-jump" href="/features/${safeText(group.key)}">${safeText(group.title)}</a>`).join("")}</nav>`;
    const summary = `<aside class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Trạng thái workflow</h2><p class="portal-card-subtitle">Số liệu chỉ mô tả route đã được registry công bố; không suy đoán engine, quota hoặc output.</p></div>${badge("read_only")}</div><div class="portal-summary-list"><div class="portal-summary-item"><span class="portal-summary-key">Đã định tuyến</span><span class="portal-summary-value">${safeText(String(entries.length))} workflow</span></div><div class="portal-summary-item"><span class="portal-summary-key">Sẵn sàng canonical</span><span class="portal-summary-value">${safeText(String(states.ready || 0))}</span></div><div class="portal-summary-item"><span class="portal-summary-key">Đang guarded</span><span class="portal-summary-value">${safeText(String(states.guarded || 0))}</span></div></div></aside>`;
    const cards = entries.length
      ? `<div class="portal-module-grid">${entries.map((entry) => moduleCard(entry, context, "Mở workflow")).join("")}</div>`
      : renderEmpty("Nhóm đang chờ registry", "Core Bridge chưa công bố workflow Web hợp lệ cho nhóm này. Portal không tự tạo form hay trạng thái thay thế.", "⌁");
    return `<article class="portal-page">${renderHero(page, context)}<div class="portal-status-grid">${renderStatusCard(page, context)}${summary}</div><section class="portal-feature-catalog"><div class="portal-section-heading"><div><span class="portal-section-kicker">${safeText(family.title)}</span><h2>Chọn workflow phù hợp</h2><p>${safeText(family.description)} Mỗi card giữ nguyên flow draft → estimate → confirm và trạng thái do Core Bridge cấp.</p></div><a class="portal-button portal-button--quiet" href="/features">Xem mọi công cụ →</a></div>${familyNav}${cards}</section></article>`;
  }

  function normalizeCatalogSearch(value) {
    const source = String(value || "").trim().toLocaleLowerCase("vi-VN");
    try {
      return source.normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/đ/g, "d");
    } catch (_) {
      return source;
    }
  }

  function filterFeatureCatalog(value) {
    const needle = normalizeCatalogSearch(value);
    const items = Array.from(document.querySelectorAll("[data-catalog-item]"));
    const groups = Array.from(document.querySelectorAll("[data-catalog-group]"));
    let matches = 0;
    items.forEach((item) => {
      const visible = !needle || normalizeCatalogSearch(item.getAttribute("data-catalog-text") || "").includes(needle);
      item.hidden = !visible;
      if (visible) matches += 1;
    });
    groups.forEach((group) => {
      group.hidden = !Array.from(group.querySelectorAll("[data-catalog-item]")).some((item) => !item.hidden);
    });
    const result = document.querySelector("[data-portal-catalog-result]");
    if (result) result.textContent = needle ? `${matches} workflow phù hợp.` : `${items.length} workflow đang hiển thị.`;
    const empty = document.querySelector("[data-portal-catalog-empty]");
    if (empty) empty.hidden = matches > 0;
    const clear = document.querySelector("[data-portal-catalog-clear]");
    if (clear) clear.hidden = !needle;
  }

  function renderEmpty(title, text, iconText) {
    return `<div class="portal-empty"><span class="portal-empty-icon" aria-hidden="true">${safeText(iconText || "○")}</span><h3>${safeText(title)}</h3><p>${safeText(text)}</p></div>`;
  }

  function renderTable(columns, emptyTitle, emptyText) {
    return `<div class="portal-data-table-wrap"><table class="portal-data-table"><thead><tr>${columns.map((column) => `<th scope="col">${safeText(column)}</th>`).join("")}</tr></thead>
      <tbody><tr><td class="portal-empty-cell" colspan="${columns.length}">${renderEmpty(emptyTitle, emptyText, "○")}</td></tr></tbody></table></div>`;
  }

  function renderRowsTable(columns, rows, renderRow, emptyTitle, emptyText) {
    const body = Array.isArray(rows) && rows.length
      ? rows.map((row) => `<tr>${renderRow(row)}</tr>`).join("")
      : `<tr><td class="portal-empty-cell" colspan="${columns.length}">${renderEmpty(emptyTitle, emptyText, "○")}</td></tr>`;
    return `<div class="portal-data-table-wrap"><table class="portal-data-table"><thead><tr>${columns.map((column) => `<th scope="col">${safeText(column)}</th>`).join("")}</tr></thead><tbody>${body}</tbody></table></div>`;
  }

  function dashboardActiveDrafts(context) {
    return (Array.isArray(context.workspaceDrafts) ? context.workspaceDrafts : [])
      .filter((item) => item && typeof item === "object" && String(item.state || "active") === "active")
      .slice(0, 100);
  }

  function renderDashboardWorkspaceSummary(context) {
    const name = displayName(context);
    const drafts = dashboardActiveDrafts(context);
    const projects = (Array.isArray(context.projects) ? context.projects : []).filter((item) => item && typeof item === "object" && validProjectId(item.id) && String(item.state || "active") === "active");
    const jobs = Array.isArray(context.jobs) ? context.jobs : [];
    const assets = Array.isArray(context.assets) ? context.assets : [];
    const processing = jobs.filter((item) => ["queued", "processing"].includes(jobStatus(item))).length;
    const deliveryReady = assets.filter((item) => item && item.delivery_ready === true && item.download_ready === true).length;
    return `<section class="portal-dashboard-overview" aria-labelledby="workspace-overview-title">
      <div class="portal-dashboard-overview-copy"><span class="portal-section-kicker">TOAN AAS / Workspace</span><h1 id="workspace-overview-title">Chào ${safeText(name)}</h1><p>Xây Project, tiếp tục brief và theo dõi công việc ở một nơi. Project và Studio Document hoạt động độc lập trên Web; Bot chỉ là integration tùy chọn cho các capability bạn chọn liên kết.</p><div class="portal-dashboard-overview-actions"><a class="portal-button portal-button--primary" href="/projects">Mở Project Center <span aria-hidden="true">→</span></a><a class="portal-button portal-button--quiet" href="/features">Tạo workflow</a></div></div>
      <dl class="portal-dashboard-overview-stats" aria-label="Tóm tắt workspace"><div><dt>Projects</dt><dd>${safeText(String(projects.length))}</dd><span>Web-owned</span></div><div><dt>Bản nháp</dt><dd>${safeText(String(drafts.length))}</dd><span>Web-owned</span></div><div><dt>Đang xử lý</dt><dd>${safeText(String(processing))}</dd><span>Integration</span></div><div><dt>Sẵn sàng tải</dt><dd>${safeText(String(deliveryReady))}</dd><span>Delivery đã kiểm tra</span></div></dl>
    </section>`;
  }

  function renderDashboardRecentDrafts(context) {
    const drafts = dashboardActiveDrafts(context).slice(0, 3);
    const body = drafts.length
      ? `<div class="portal-dashboard-draft-list">${drafts.map((item) => `<a class="portal-dashboard-draft" href="/workspace"><span class="portal-dashboard-draft-icon" aria-hidden="true">${safeText(ICONS.prompt)}</span><span><strong>${safeText(String(item.title || item.feature_title || "Bản nháp Web"))}</strong><small>${safeText(String(item.feature_title || "Workflow Web"))} · cập nhật ${safeText(String(item.updated_at || item.created_at || "—"))}</small></span><b aria-hidden="true">→</b></a>`).join("")}</div>`
      : renderEmpty("Chưa có brief đang làm", "Bắt đầu ở một studio; bản nháp Web chỉ lưu brief an toàn và không tạo job, charge hay output.", "✦");
    return `<section class="portal-card portal-card-pad portal-dashboard-drafts"><div class="portal-card-header"><div><span class="portal-section-kicker">Continue working</span><h2 class="portal-card-title">Bản nháp gần đây</h2><p class="portal-card-subtitle">Mở thư viện để tiếp tục đúng workflow; file, quote và trạng thái canonical luôn được kiểm tra lại.</p></div><a class="portal-button portal-button--quiet" href="/workspace">Xem tất cả →</a></div>${body}</section>`;
  }

  function renderDashboardRecentProjects(context) {
    const projects = (Array.isArray(context.projects) ? context.projects : []).filter((item) => item && typeof item === "object" && validProjectId(item.id)).slice(0, 3);
    const body = projects.length
      ? `<div class="portal-dashboard-draft-list">${projects.map((project) => `<a class="portal-dashboard-draft" href="/projects/${encodeURIComponent(String(project.id))}"><span class="portal-dashboard-draft-icon" aria-hidden="true">${safeText(ICONS.dashboard)}</span><span><strong>${safeText(String(project.title || "Project"))}</strong><small>${safeText(String(project.objective || "Web Workspace"))} · ${safeText(String(Number(project.document_count || 0)))} Studio Documents</small></span><b aria-hidden="true">→</b></a>`).join("")}</div>`
      : renderEmpty("Chưa có Project đang mở", "Tạo một Project để gom creative brief, prompt, script và storyboard có version history độc lập trên Web.", "✦");
    return `<section class="portal-card portal-card-pad portal-dashboard-drafts"><div class="portal-card-header"><div><span class="portal-section-kicker">Independent work</span><h2 class="portal-card-title">Project gần đây</h2><p class="portal-card-subtitle">Không cần liên kết Telegram để bắt đầu authoring và version hóa nội dung.</p></div><a class="portal-button portal-button--quiet" href="/projects">Mở Project Center →</a></div>${body}</section>`;
  }

  function renderDashboard(page, context) {
    const jobs = Array.isArray(context.jobs) ? context.jobs.slice(0, 5) : [];
    const assets = Array.isArray(context.assets) ? context.assets.slice(0, 5) : [];
    const wallet = context.wallet && typeof context.wallet === "object" ? context.wallet : null;
    const quickMetrics = wallet
      ? `<section class="portal-admin-grid"><div class="portal-metric"><span>Xu canonical</span><strong>${safeText(String(wallet.balance_xu || 0))}</strong><em>Không tính lại ở browser</em></div><div class="portal-metric"><span>Đã dùng</span><strong>${safeText(String(wallet.total_spent_xu || 0))}</strong><em>Đọc từ ledger canonical</em></div><div class="portal-metric"><span>Job gần đây</span><strong>${safeText(String(jobs.length))}</strong><em>Trong cửa sổ hiện tại</em></div><div class="portal-metric"><span>Asset metadata</span><strong>${safeText(String(assets.length))}</strong><em>Không đồng nghĩa delivery</em></div></section>`
      : "";
    const activity = `<div class="portal-work-grid"><section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Job gần đây</h2><p class="portal-card-subtitle">Core Bridge kiểm tra ownership trước khi trả dữ liệu.</p></div><a class="portal-button portal-button--quiet" href="/jobs">Mở Job Center →</a></div>${renderRowsTable(["Job", "Tính năng", "Trạng thái", "Output engine"], jobs, (item) => `<td><a href="/jobs/${encodeURIComponent(item.id || "")}">${safeText(item.id || "—")}</a></td><td>${safeText(item.feature || "—")}</td><td>${badge(jobStatus(item))}</td><td>${reportedOutput(item)}</td>`, "Chưa có hoạt động được xác minh", "Khi bạn có job hợp lệ, Core Bridge sẽ trả metadata canonical tại đây.")}</section>
      <section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Tài sản gần đây</h2><p class="portal-card-subtitle">Chỉ metadata riêng tư; output hợp lệ vẫn phải chờ delivery URL ký.</p></div><a class="portal-button portal-button--quiet" href="/assets">Mở tài sản →</a></div>${renderRowsTable(["Tài sản", "Tính năng", "Trạng thái", "Delivery"], assets, (item) => `<td>${assetJobLink(item)}</td><td>${safeText(item.feature || "—")}</td><td>${badge(jobStatus(item))}</td><td>${assetDeliveryState(item, "asset")}</td>`, "Chưa có asset metadata", "Không dùng placeholder để thay thế một output đã được xác minh.")}</section></div>`;
    return `<article class="portal-page portal-dashboard-app">${renderDashboardWorkspaceSummary(context)}<div class="portal-status-grid portal-dashboard-assurance">${renderStatusCard(page, context)}${renderSummary(page, context)}</div>${quickMetrics}${renderDashboardRecentProjects(context)}${renderWorkspaceActionCenter(context)}${renderDashboardRecentDrafts(context)}${renderStudioLaunchpad(context)}${activity}</article>`;
  }

  function renderWorkspaceActionCenter(context) {
    // This is a read-only projection of records already scoped to the signed
    // customer by the Core Bridge.  It deliberately creates no notification,
    // job, ticket, payment or provider state in the browser.
    const jobs = Array.isArray(context.jobs) ? context.jobs : [];
    const assets = Array.isArray(context.assets) ? context.assets : [];
    const tickets = Array.isArray(context.tickets) ? context.tickets : [];
    const processing = jobs.filter((item) => ["queued", "processing"].includes(jobStatus(item))).length;
    const deliveryReady = assets.filter((item) => item && item.download_ready === true && item.delivery_ready === true).length;
    const needsReview = jobs.filter((item) => ["failed", "failed_no_charge"].includes(jobStatus(item))).length;
    const waitingUser = tickets.filter((item) => canonicalTicketStatus(item) === "waiting_user").length;
    const cards = [
      {
        icon: ICONS.jobs,
        count: processing,
        label: "Đang xử lý",
        status: processing ? "processing" : "read_only",
        detail: processing ? "Job đang xếp hàng hoặc chạy theo trạng thái Bot canonical." : "Không có job queued hoặc processing trong dữ liệu hiện tại.",
        href: "/jobs",
        action: "Mở Job Center"
      },
      {
        icon: ICONS.assets,
        count: deliveryReady,
        label: "Tệp đã sẵn sàng",
        status: deliveryReady ? "ready" : "read_only",
        detail: deliveryReady ? "Asset đã có delivery contract owner-scoped từ Bot." : "Chưa có asset nào được Bot cấp delivery contract.",
        href: "/assets",
        action: "Mở thư viện"
      },
      {
        icon: ICONS.jobs,
        count: needsReview,
        label: "Cần xem job",
        status: needsReview ? "failed" : "read_only",
        detail: needsReview ? "Bot báo job failed; mở chi tiết trước khi tạo ticket hỗ trợ." : "Không có job failed trong cửa sổ metadata hiện tại.",
        href: "/jobs",
        action: "Xem job"
      },
      {
        icon: ICONS.ticket,
        count: waitingUser,
        label: "Ticket chờ bạn",
        status: waitingUser ? "awaiting_confirm" : "read_only",
        detail: waitingUser ? "Bot đang chờ phản hồi của bạn trong thread canonical." : "Không có ticket đang chờ phản hồi từ bạn.",
        href: "/tickets",
        action: "Mở ticket"
      }
    ];
    return `<section class="portal-action-center" data-workspace-action-center aria-labelledby="workspace-action-center-title"><div class="portal-section-heading"><div><span class="portal-section-kicker">Work Queue</span><h2 id="workspace-action-center-title">Công việc cần chú ý</h2><p>Chỉ tổng hợp metadata canonical thuộc signed session hiện tại; không suy đoán output, charge hay delivery.</p></div><a class="portal-button portal-button--quiet" href="/jobs">Xem tất cả công việc →</a></div><div class="portal-action-center-grid">${cards.map((card) => `<a class="portal-action-card" href="${safeText(card.href)}"><div class="portal-action-card-head"><span class="portal-module-icon" aria-hidden="true">${safeText(card.icon)}</span>${badge(card.status)}</div><strong>${safeText(String(card.count))}</strong><h3>${safeText(card.label)}</h3><p>${safeText(card.detail)}</p><span class="portal-action-card-link">${safeText(card.action)} <b aria-hidden="true">→</b></span></a>`).join("")}</div></section>`;
  }

  function renderStudioLaunchpad(context) {
    const studios = [
      { route: "/image/create", icon: ICONS.image, title: "Ảnh", description: "Prompt, tham chiếu và estimate canonical.", tags: ["Prompt", "Assets"] },
      { route: "/video/create", icon: ICONS.video, title: "Video", description: "Brief, cảnh và tiến độ từ Job Center.", tags: ["Draft", "Jobs"] },
      { route: "/voice/tts", icon: ICONS.voice, title: "Voice", description: "TTS, Voice Vault và consent rõ ràng.", tags: ["Vault", "Estimate"] },
      { route: "/music/create", icon: ICONS.music, title: "Music", description: "Prompt nhạc, chính sách và báo giá bot.", tags: ["Policy", "Quote"] },
      { route: "/content/pack", icon: ICONS.prompt, title: "Content", description: "Caption, hook, script và storyboard.", tags: ["Planning", "0 Xu draft"] },
      { route: "/documents", icon: ICONS.document, title: "Documents", description: "PDF/OCR theo contract và delivery riêng tư.", tags: ["Files", "Guarded"] }
    ];
    return `<section class="portal-studio-section"><div class="portal-section-heading"><div><span class="portal-section-kicker">TOAN AAS Studio</span><h2>Chọn một workflow rõ ràng</h2><p>Mỗi studio dùng cùng hợp đồng draft → estimate → confirm; browser không gọi provider, ví hay job trực tiếp.</p></div><a class="portal-button portal-button--quiet" href="/pricing">Xem pricing canonical →</a></div><div class="portal-studio-launchpad">${studios.map((studio) => {
      const studioPage = manifest[studio.route] || { path: studio.route, access: "member", action: "none" };
      const state = stateFor(studioPage, context);
      return `<a class="portal-studio-card" href="${studio.route}" data-studio="${safeText(studio.route.slice(1).split("/")[0])}"><div class="portal-studio-card-head"><span class="portal-studio-icon" aria-hidden="true">${safeText(studio.icon)}</span>${badge(state)}</div><div><h3>${safeText(studio.title)}</h3><p>${safeText(studio.description)}</p></div><div class="portal-studio-tags">${studio.tags.map((tag) => `<span>${safeText(tag)}</span>`).join("")}</div><span class="portal-studio-open">Mở studio <b aria-hidden="true">→</b></span></a>`;
    }).join("")}</div></section>`;
  }

  function membershipCatalogEntries(context) {
    const catalog = context.packageCatalog && typeof context.packageCatalog === "object" ? context.packageCatalog : {};
    const sources = [catalog.monthly, catalog.combos, catalog.items, catalog.packages];
    const seen = new Set();
    const entries = [];
    sources.forEach((source) => {
      if (!Array.isArray(source)) return;
      source.forEach((item) => {
        if (!item || typeof item !== "object") return;
        const code = typeof item.code === "string" && item.code ? item.code : (typeof item.id === "string" ? item.id : "");
        const label = typeof item.label === "string" && item.label ? item.label : (typeof item.title === "string" ? item.title : code);
        if (!label || seen.has(`${code}:${label}`)) return;
        seen.add(`${code}:${label}`);
        entries.push({ code, label, note: typeof item.note === "string" ? item.note : (typeof item.summary === "string" ? item.summary : "Quyền lợi do Bot canonical xác minh."), price: Number.isFinite(Number(item.price_vnd)) && Number(item.price_vnd) > 0 ? Number(item.price_vnd) : null, manual: item.manual === true });
      });
    });
    return entries.slice(0, 12);
  }

  function renderMembership(page, context) {
    const wallet = context.wallet && typeof context.wallet === "object" ? context.wallet : null;
    const plan = wallet && wallet.plan && typeof wallet.plan === "object" ? wallet.plan : {};
    const profile = context.profile && typeof context.profile === "object" ? context.profile : {};
    const catalog = context.packageCatalog && typeof context.packageCatalog === "object" ? context.packageCatalog : {};
    const planName = String(plan.plan_name || plan.current_plan || plan.name || "Chưa có gói canonical");
    const planStatus = String(plan.plan_status || plan.status || "Chờ Core Bridge");
    const entries = membershipCatalogEntries(context);
    const current = wallet
      ? `<section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Quyền lợi hiện tại</h2><p class="portal-card-subtitle">Metadata từ ví/gói do Bot canonical cấp; Web không tự cấp VIP, trial hoặc referral reward.</p></div>${badge("read_only")}</div><div class="portal-summary-list"><div class="portal-summary-item"><span class="portal-summary-key">Gói hiện tại</span><span class="portal-summary-value">${safeText(planName)}</span></div><div class="portal-summary-item"><span class="portal-summary-key">Trạng thái gói</span><span class="portal-summary-value">${safeText(planStatus)}</span></div><div class="portal-summary-item"><span class="portal-summary-key">Tài khoản Web</span><span class="portal-summary-value">${safeText(String(profile.accountType || "standard"))}</span></div><div class="portal-summary-item"><span class="portal-summary-key">Xu canonical</span><span class="portal-summary-value">${safeText(String(wallet.balance_xu || 0))} Xu</span></div></div></section>`
      : `<section class="portal-card portal-card-pad">${renderEmpty("Chờ quyền lợi canonical", "Bot/Core Bridge phải cấp metadata gói thuộc signed session trước khi Web có thể hiển thị tier hoặc trial.", "◇")}</section>`;
    const catalogCards = entries.length
      ? `<div class="portal-module-grid">${entries.map((item) => `<article class="portal-module-card"><div class="portal-module-card-top"><span class="portal-module-icon" aria-hidden="true">◇</span>${badge("read_only")}</div><div><h3>${safeText(item.label)}</h3><p>${safeText(item.note)}</p></div><span class="portal-module-card-footer"><span>${item.manual ? "Bot/Admin quản lý" : (item.price ? `${safeText(item.price.toLocaleString("vi-VN"))}đ` : "Giá canonical chờ bridge")}</span><span class="portal-module-arrow" aria-hidden="true">→</span></span></article>`).join("")}</div>`
      : renderEmpty("Chờ catalog gói canonical", "Không dùng danh mục feature để suy đoán gói, tier, giá hoặc khuyến mãi.", "◇");
    return `<article class="portal-page">${renderHero(page, context)}<div class="portal-status-grid">${renderStatusCard(page, context)}${renderSummary(page, context)}</div><div class="portal-work-grid"><div class="portal-stack">${current}</div><aside class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Nguyên tắc quyền lợi</h2><p class="portal-card-subtitle">Bot là authority cho tier và mọi tác động Xu.</p></div></div>${renderNotes(page)}</aside></div><section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Gói được Bot công bố</h2><p class="portal-card-subtitle">Thông tin chỉ đọc; mua/nâng cấp tiếp tục qua luồng canonical.</p></div>${badge(catalog.available === true ? "read_only" : "guarded")}</div>${catalogCards}<div class="portal-form-footer"><a class="portal-button portal-button--quiet" href="/packages">Xem catalog đầy đủ</a><a class="portal-button portal-button--quiet" href="/pricing">Xem bảng giá</a><a class="portal-button portal-button--primary" href="/wallet/topup">Nạp Xu canonical</a></div></section></article>`;
  }

  function renderServiceStatus(page, context) {
    const connection = context.telegramConnection && typeof context.telegramConnection === "object" ? context.telegramConnection : {};
    const readiness = context.readiness && context.readiness.features && typeof context.readiness.features === "object" ? context.readiness.features : {};
    const rows = [
      ["Signed session", context.session.authenticated === true, context.session.authenticated === true ? "Web đã xác thực phiên trên server." : "Cần đăng nhập để xem workspace riêng tư."],
      ["Telegram Login OIDC", connection.oidc_web_login_enabled === true, connection.oidc_web_login_enabled === true ? "Đã bật đăng nhập Web qua Telegram OIDC." : "Chờ BotFather Web Login Client ID/Secret và Railway flag."],
      ["Telegram deep link", connection.bot_deep_link_ready === true, connection.bot_deep_link_ready === true ? "Bot username công khai hợp lệ." : "Chờ BOT_USERNAME hợp lệ."],
      ["Telegram callback", connection.web_callback_ready === true, connection.web_callback_ready === true ? "Web receiver đã có credential callback riêng." : "Chờ cấu hình callback đã ký."],
      ["Bot link adapter", connection.bot_callback_adapter_enabled === true, connection.bot_callback_adapter_enabled === true ? "Operator đã bật cầu nối sau khi phát hành adapter Bot tương ứng." : "Chờ phát hành adapter Bot và xác nhận kích hoạt; Web sẽ không tạo mã chết."],
      ["Callback đã kiểm chứng", connection.bot_callback_observed === true, connection.bot_callback_observed === true ? "Web đã quan sát callback Bot hợp lệ." : (connection.bot_callback_adapter_enabled === true ? "Chưa quan sát callback hợp lệ; có thể tạo mã liên kết để kiểm tra luồng." : "Chờ adapter Bot được kích hoạt trước khi kiểm tra callback.")],
      ["Core Bridge", context.bridge.configured === true, context.bridge.configured === true ? (context.bridge.available === true ? "Sẵn sàng cho signed Telegram session hiện tại." : "Đã cấu hình, đang chờ session Telegram liên kết.") : "Chưa cấu hình bridge server-to-server."],
      ["Xác nhận engine", context.bridge.featureExecutionAvailable === true, context.bridge.featureExecutionAvailable === true ? "Có feature adapter đã được allowlist." : "Provider/job confirm vẫn được bảo vệ."]
    ];
    const featureRows = Object.entries(readiness).filter(([key, value]) => /^[a-z][a-z0-9_]{1,80}$/.test(key) && value && typeof value === "object").slice(0, 32);
    const readinessTable = featureRows.length
      ? renderRowsTable(["Workflow", "Public readiness", "Web execution"], featureRows, ([key, value]) => `<td>${safeText(key)}</td><td>${badge(value.public_ready === true ? "ready" : "guarded")}</td><td>${value.public_ready === true && context.bridge.featureExecutionAvailable === true ? "Theo allowlist canonical" : "Đang guarded"}</td>`, "", "")
      : renderEmpty("Chưa có readiness bridge", "Khi signed Telegram session và Core Bridge khả dụng, Bot mới cấp trạng thái feature đã redaction.", "⌁");
    return `<article class="portal-page">${renderHero(page, context)}<section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Kết nối được kiểm tra trên server</h2><p class="portal-card-subtitle">Không hiển thị Telegram ID, code, callback token, HMAC secret, provider key hoặc payload runtime.</p></div>${badge("read_only")}</div><div class="portal-panel-list">${rows.map(([label, ok, detail], index) => `<div class="portal-panel-row"><span class="portal-panel-row-icon" aria-hidden="true">${ok ? "✓" : (index < 4 ? "⌁" : "i")}</span><div><strong>${safeText(label)}</strong><span>${safeText(detail)}</span></div>${badge(ok ? "ready" : "guarded")}</div>`).join("")}</div></section><section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Readiness workflow</h2><p class="portal-card-subtitle">Chỉ trạng thái public do Bot/Core Bridge phát hành; không phải trạng thái provider trực tiếp.</p></div>${badge(featureRows.length ? "read_only" : "guarded")}</div>${readinessTable}</section><section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Cách khôi phục luồng</h2><p class="portal-card-subtitle">Nếu liên kết Telegram chưa hoàn tất, không thử nhập ID thủ công.</p></div></div>${renderNotes(page)}<div class="portal-form-footer"><a class="portal-button portal-button--primary" href="/account">Tài khoản & liên kết</a><a class="portal-button portal-button--quiet" href="/onboarding">Mở liên kết Telegram</a><a class="portal-button portal-button--quiet" href="/support">Liên hệ hỗ trợ</a></div></section></article>`;
  }

  function renderMediaStudio(page, context) {
    const steps = [
      { number: "01", icon: ICONS.prompt, title: "Brief & storyboard", text: "Bắt đầu bằng content pack hoặc storyboard để làm rõ câu chuyện, cảnh và CTA trước khi tạo media.", href: "/content/storyboard", action: "Lập storyboard" },
      { number: "02", icon: ICONS.image, title: "Visual & reference", text: "Tạo ảnh hoặc chuẩn bị image-to-image với asset được staging/ownership-check theo workflow riêng.", href: "/image/create", action: "Mở Image Studio" },
      { number: "03", icon: ICONS.video, title: "Video project", text: "Chọn video sản phẩm, quick video hoặc multiscene; estimate và số cảnh do Bot canonical xác nhận.", href: "/video/product", action: "Mở Video Studio" },
      { number: "04", icon: ICONS.voice, title: "Voice workspace", text: "Chuẩn bị TTS hoặc Voice Vault trong workflow có consent và policy riêng.", href: "/voice/tts", action: "Chuẩn bị voice" },
      { number: "05", icon: ICONS.music, title: "Audio Library & Briefing", text: "Tổ chức music/SFX brief và audio Asset Vault riêng tư. Đây là authoring-only, không phải music generator hoặc player.", href: "/media-workspace", action: "Mở Audio Library" },
      { number: "06", icon: ICONS.subtitle, title: "Subtitle & finalization", text: "Dùng subtitle/dubbing rồi mở finalization. Mux, watermark, export và delivery vẫn cần adapter Bot riêng.", href: "/video/add-ons", action: "Mở finalization" }
    ];
    const cards = steps.map((step) => `<article class="portal-finalization-card"><div class="portal-finalization-card-head"><span class="portal-finalization-number">${safeText(step.number)}</span><span class="portal-module-icon" aria-hidden="true">${safeText(step.icon)}</span></div><h3>${safeText(step.title)}</h3><p>${safeText(step.text)}</p><a class="portal-button portal-button--quiet" href="${safeText(step.href)}">${safeText(step.action)} <span aria-hidden="true">→</span></a></article>`).join("");
    return `<article class="portal-page">${renderHero(page, context)}<section class="portal-card portal-card-pad portal-media-studio-intro"><div class="portal-state" data-state="read_only"><span class="portal-state-icon" aria-hidden="true">${safeText(ICONS.video)}</span><div><h2>Điều phối workflow, không giả project</h2><p>Media Studio phản chiếu các bước media factory/creative flow của Bot bằng đường đi rõ ràng giữa các workspace Web đã đăng ký. Mỗi bước vẫn tự giữ input, quote, confirmation và quyền sở hữu riêng.</p><div class="portal-state-meta"><span>Không tạo job tại browser</span><span>Không suy đoán output</span><span>Không ghép file/URL tự do</span></div></div></div></section><section class="portal-finalization-grid" aria-label="Luồng Media Studio">${cards}</section><section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Sau khi xác nhận</h2><p class="portal-card-subtitle">Job Center và Assets là nơi duy nhất theo dõi status/delivery canonical sau khi một adapter Bot đã tạo job hợp lệ.</p></div>${badge("read_only")}</div>${renderNotes(page)}<div class="portal-form-footer"><a class="portal-button portal-button--quiet" href="/jobs">Mở Job Center</a><a class="portal-button portal-button--quiet" href="/assets">Mở tài sản</a><a class="portal-button portal-button--primary" href="/features">Khám phá workflow</a></div></section></article>`;
  }

  function safePayosCheckout(value) {
    if (typeof value !== "string" || !value) return "";
    try {
      const url = new URL(value);
      return url.protocol === "https:" && !url.username && !url.password && !url.port && !url.hash && (url.hostname === "pay.payos.vn" || url.hostname.endsWith(".payos.vn")) ? url.href : "";
    } catch (_) {
      return "";
    }
  }

  function paymentOrderId(flow) {
    const data = flow && flow.data && typeof flow.data === "object" ? flow.data : {};
    return String(data.payment_id || data.order_code || data.id || "").trim();
  }

  function paymentWebCatalogReady(context) {
    const payos = context && context.paymentOptions && context.paymentOptions.payos;
    return Boolean(payos && payos.request_enabled === true && payos.topup_catalog_available === true && context.capabilities && context.capabilities["payment-create"] === true);
  }

  function renderPaymentEntryPoints(context) {
    const options = context.paymentOptions && typeof context.paymentOptions === "object" ? context.paymentOptions : {};
    const payos = options.payos && typeof options.payos === "object" ? options.payos : {};
    const manual = options.manual && typeof options.manual === "object" ? options.manual : {};
    const payosWebReady = paymentWebCatalogReady(context);
    const payosUrl = safeTelegramLink(payos.telegram_url);
    const payosBotAvailable = Boolean(payosUrl);
    const manualUrl = safeTelegramLink(manual.telegram_url);
    const manualAvailable = manual.available === true && Boolean(manualUrl);
    const payosCommand = payos.command === "/naptien" ? payos.command : "/naptien";
    const manualCommand = manual.command === "/thucong" ? manual.command : "/thucong";
    const payosCopy = payosWebReady
      ? "Bridge đã công bố catalog nạp riêng cho Web. Bot vẫn là authority duy nhất cấp checkout URL đã ký."
      : "Mở Bot đã liên kết để kiểm tra và khởi tạo PayOS QR động canonical hiện tại. Bot có thể chuyển sang luồng thủ công theo trạng thái runtime; Web không suy đoán QR luôn sẵn sàng.";
    const manualCopy = manualAvailable
      ? "Mở bot đã liên kết, gửi /thucong và làm theo đúng luồng Telegram. VND cần ảnh bill; nạp quốc tế/USDT dùng TXID đầy đủ hoặc ảnh bill. Xu chỉ được ghi sau đối soát thật."
      : "Bot URL chưa sẵn sàng nên Web không hiển thị lệnh/copy action. Web không giữ số tài khoản, QR tĩnh, bill hoặc quyết định cộng Xu.";
    const payosActions = payosBotAvailable
      ? `<a class="portal-button portal-button--quiet" href="${safeText(payosUrl)}" target="_blank" rel="noopener noreferrer">Mở bot liên kết</a><button class="portal-button portal-button--quiet" type="button" data-portal-action="copy-payment-command" data-copy-text="${safeText(payosCommand)}">Sao chép lệnh</button><code class="portal-link-code">${safeText(payosCommand)}</code>`
      : `<span class="portal-payment-entry-note">Chưa có URL Bot hợp lệ để mở PayOS QR động.</span>`;
    const manualActions = manualAvailable
      ? `<a class="portal-button portal-button--quiet" href="${safeText(manualUrl)}" target="_blank" rel="noopener noreferrer">Mở bot liên kết</a><button class="portal-button portal-button--quiet" type="button" data-portal-action="copy-payment-command" data-copy-text="${safeText(manualCommand)}">Sao chép lệnh</button><code class="portal-link-code">${safeText(manualCommand)}</code>`
      : `<span class="portal-payment-entry-note">Chưa có URL Bot hợp lệ để bắt đầu nạp thủ công.</span>`;
    return `<section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Chọn kênh nạp an toàn</h2><p class="portal-card-subtitle">PayOS và nạp thủ công là hai luồng canonical riêng; không có webhook thứ hai trong Web App.</p></div>${badge(payosBotAvailable || manualAvailable ? "read_only" : "guarded")}</div><div class="portal-payment-entry-grid"><section class="portal-payment-entry"><div class="portal-payment-entry-head"><span class="portal-module-icon" aria-hidden="true">◈</span>${badge(payosWebReady ? "awaiting_confirm" : (payosBotAvailable ? "read_only" : "guarded"))}</div><h3>PayOS QR động</h3><p>${payosCopy}</p><div class="portal-payment-entry-actions">${payosActions}</div><span class="portal-payment-entry-note">Bot tạo QR động và xác nhận PayOS canonical.</span></section><section class="portal-payment-entry"><div class="portal-payment-entry-head"><span class="portal-module-icon" aria-hidden="true">⌁</span>${badge(manualAvailable ? "read_only" : "guarded")}</div><h3>Nạp thủ công có đối soát</h3><p>${manualCopy}</p><div class="portal-payment-entry-actions">${manualActions}</div><span class="portal-payment-entry-note">Gửi lệnh trong bot; không gửi bill vào Web App.</span></section></div></section>`;
  }

  function renderManualTopupGuide(context) {
    const options = context.paymentOptions && typeof context.paymentOptions === "object" ? context.paymentOptions : {};
    const manual = options.manual && typeof options.manual === "object" ? options.manual : {};
    const manualUrl = safeTelegramLink(manual.telegram_url);
    const available = manual.available === true && Boolean(manualUrl);
    const historySignal = manual.wallet_history_signal_available === true;
    const historyInBot = manual.history_in_web === false && manual.history_channel === "telegram_bot";
    const historyCommand = manual.history_command === "/thucong" ? manual.history_command : "/thucong";
    const historyMenu = typeof manual.history_menu_label === "string" && manual.history_menu_label ? manual.history_menu_label : "Lịch sử nạp thủ công";
    const refreshEnabled = context.capabilities && context.capabilities["refresh-wallet-after-bot"] === true;
    if (!available) {
      return `<section class="portal-card portal-card-pad" data-manual-topup-guide><div class="portal-card-header"><div><h2 class="portal-card-title">Nạp thủ công: chờ Bot canonical</h2><p class="portal-card-subtitle">Web không thể nhận chứng từ hoặc thay thế cuộc hội thoại Bot khi URL Bot chưa được cấu hình an toàn.</p></div>${badge("guarded")}</div>${renderEmpty("Kênh nạp thủ công chưa sẵn sàng", "Khi Bot đã có URL hợp lệ, Web chỉ mở handoff an toàn; bill, TXID, đối soát và ghi Xu vẫn ở Telegram.", "⌁")}</section>`;
    }
    const routeGuide = `<div class="portal-manual-topup-routes"><article class="portal-manual-topup-route"><span class="portal-module-icon" aria-hidden="true">₫</span><div><h3>Nạp VND</h3><p>Chọn phương thức trong Bot, rồi gửi ảnh bill ở chính cuộc hội thoại Telegram. Web không nhận hoặc lưu ảnh này.</p></div><span>Chứng từ chỉ ở Bot</span></article><article class="portal-manual-topup-route"><span class="portal-module-icon" aria-hidden="true">◌</span><div><h3>Quốc tế / USDT</h3><p>Chọn đúng luồng trong Bot, gửi TXID đầy đủ hoặc ảnh bill ở Bot để đội vận hành đối soát.</p></div><span>Không dán TXID vào Web</span></article><article class="portal-manual-topup-route is-guarded"><span class="portal-module-icon" aria-hidden="true">◈</span><div><h3>Không có QR tĩnh</h3><p>Không dùng số tài khoản, QR, ảnh bill, OTP hoặc thông tin thẻ từ trang Web này. Chỉ dùng thông tin Bot cấp cho đúng request.</p></div><span>Chống nhầm / giả mạo</span></article></div>`;
    const stateGuide = `<div class="portal-manual-topup-status"><span><code>pending</code><small>Đã gửi, đang chờ đối soát</small></span><span><code>pending_admin_review</code><small>Đội vận hành đang kiểm tra</small></span><span><code>approved</code><small>Chỉ lúc này wallet canonical mới là kết quả cuối</small></span><span><code>rejected</code><small>Xem lý do và xử lý lại trong Bot</small></span></div>`;
    return `<section class="portal-card portal-card-pad" data-manual-topup-guide><div class="portal-card-header"><div><h2 class="portal-card-title">Nạp thủ công: tiếp tục trong Telegram</h2><p class="portal-card-subtitle">Bot canonical giữ toàn bộ state, chứng từ, đối soát và quyết định ghi Xu. Web chỉ hướng dẫn và hiển thị dữ liệu ví đã được xác minh.</p></div>${badge("read_only")}</div>
      ${routeGuide}<div class="portal-panel-list"><div class="portal-panel-row"><span class="portal-panel-row-icon" aria-hidden="true">1</span><div><strong>Mở bot và gửi <code>/thucong</code></strong><span>Chọn tiền tệ, mệnh giá và phương thức trong cuộc hội thoại Telegram đang được Bot kiểm soát.</span></div></div><div class="portal-panel-row"><span class="portal-panel-row-icon" aria-hidden="true">2</span><div><strong>Gửi chứng từ đúng nơi</strong><span>Nạp VND: gửi ảnh bill trong Bot. Nạp quốc tế/USDT: gửi TXID đầy đủ hoặc ảnh bill trong Bot. Không gửi số tài khoản, QR, bill, OTP hay TXID vào Web App.</span></div></div><div class="portal-panel-row"><span class="portal-panel-row-icon" aria-hidden="true">3</span><div><strong>Chờ admin đối soát</strong><span><code>pending</code> hoặc <code>pending_admin_review</code> đều đang chờ đối soát; chưa phải Xu đã được cộng.</span></div></div><div class="portal-panel-row"><span class="portal-panel-row-icon" aria-hidden="true">4</span><div><strong>Đối chiếu kết quả canonical</strong><span><code>approved</code> mới là đã duyệt; <code>rejected</code> là bị từ chối. Xu hiển thị trước đối soát là ước tính; số Xu trong wallet/ledger canonical sau duyệt mới là cuối cùng.</span></div></div></div>${stateGuide}
      <div class="portal-form-footer"><span class="portal-form-note">${historyInBot ? `Xem yêu cầu trong Bot: <code>${safeText(historyCommand)}</code> → ${safeText(historyMenu)}. ` : ""}${historySignal ? "Bridge chưa có lịch sử manual-topup đã redaction, vì vậy Web không tra bill/TXID hoặc suy đoán trạng thái." : "Lịch sử Xu chỉ xuất hiện khi Core Bridge cấp dữ liệu canonical cho phiên."}</span>${historyInBot ? `<button class="portal-button portal-button--quiet" type="button" data-portal-action="copy-payment-command" data-copy-text="${safeText(historyCommand)}">Sao chép ${safeText(historyCommand)}</button>` : ""}<a class="portal-button portal-button--quiet" href="${safeText(manualUrl)}" target="_blank" rel="noopener noreferrer">Mở Bot</a><button class="portal-button portal-button--quiet" type="button" data-portal-action="refresh-wallet-after-bot"${refreshEnabled ? "" : " disabled title=\"Cần Core Bridge để làm mới ví canonical.\""}>Đã thao tác trong Bot — làm mới ví</button><a class="portal-button portal-button--quiet" href="/wallet">Xem lịch sử Xu canonical</a></div></section>`;
  }

  function renderPaymentRequestForm(page, context) {
    if (paymentWebCatalogReady(context)) return renderFormCard(page, context);
    return `<section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Checkout Web đang được bảo vệ</h2><p class="portal-card-subtitle">Không dùng catalog combo/gói tháng để giả làm mệnh giá nạp Xu.</p></div>${badge("guarded")}</div>${renderEmpty("Chờ catalog nạp canonical", "Khi bot công bố adapter danh mục nạp riêng cho bridge, form checkout Web mới được bật. Trong thời gian này dùng /naptien trong Bot để kiểm tra hoặc khởi tạo PayOS QR động canonical.", "◈")}</section>`;
  }

  function renderPaymentLookup(context) {
    const enabled = context.capabilities && context.capabilities["payment-lookup"] === true;
    const fields = [{
      name: "payment_id", label: "Mã đơn PayOS / order code", type: "text", placeholder: "Ví dụ: 12345678",
      autocomplete: "off", required: true, minLength: 1, maxLength: 120, pattern: "[A-Za-z0-9._:-]+",
      help: "Chỉ tra cứu đơn PayOS thuộc Telegram identity đã liên kết. Đây là GET read-only; Web không xác nhận, cộng Xu hoặc gửi webhook."
    }];
    const route = "/wallet/topup/payment-lookup";
    return `<section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Kiểm tra đơn PayOS</h2><p class="portal-card-subtitle">Chỉ tra cứu order PayOS canonical thuộc phiên của bạn. Nạp thủ công tiếp tục và được đối soát hoàn toàn trong Bot.</p></div>${badge(enabled ? "read_only" : "guarded")}</div><form class="portal-form" data-portal-form data-portal-action="payment-lookup" data-portal-route="${route}" novalidate>${renderFields(fields, enabled, context, transientFormValues(route))}<div class="portal-form-footer"><span class="portal-form-note">Không nhập ảnh bill, số tài khoản, OTP, TXID hay thông tin thẻ vào Web App.</span><button class="portal-button portal-button--quiet" type="submit"${enabled ? "" : " disabled"}>Kiểm tra đơn PayOS</button></div></form></section>`;
  }

  function renderPaymentFlow(context) {
    const flow = context.paymentFlow && typeof context.paymentFlow === "object" ? context.paymentFlow : {};
    const data = flow.data && typeof flow.data === "object" ? flow.data : {};
    if (!flow.status && !flow.message && !Object.keys(data).length) return "";
    const orderId = paymentOrderId(flow);
    const status = paymentStatus({ status: data.status || flow.status });
    const checkout = safePayosCheckout(data.checkout_url || data.payment_url || data.url || "");
    const refreshEnabled = Boolean(orderId && context.capabilities && context.capabilities["refresh-payment"] === true);
    const polling = ["queued", "awaiting_confirm", "processing"].includes(status);
    return `<section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Yêu cầu thanh toán canonical</h2><p class="portal-card-subtitle">Web chỉ hiển thị response đã được bridge ký; không tự tạo link, finalize webhook hoặc cộng Xu.</p></div>${badge(status)}</div><div class="portal-summary-list"><div class="portal-summary-item"><span class="portal-summary-key">Trạng thái</span><span class="portal-summary-value">${safeText(PAYMENT_STATUS_LABELS[status] || STATE_LABELS[status] || status)}</span></div><div class="portal-summary-item"><span class="portal-summary-key">Mã giao dịch</span><span class="portal-summary-value">${safeText(orderId || "Chưa được bridge cấp")}</span></div>${data.amount_vnd !== undefined ? `<div class="portal-summary-item"><span class="portal-summary-key">Giá trị</span><span class="portal-summary-value">${safeText(adminNumber(data.amount_vnd, " đ"))}</span></div>` : ""}${data.xu !== undefined ? `<div class="portal-summary-item"><span class="portal-summary-key">Xu canonical</span><span class="portal-summary-value">${safeText(adminNumber(data.xu, " Xu"))}</span></div>` : ""}${data.created_at ? `<div class="portal-summary-item"><span class="portal-summary-key">Khởi tạo</span><span class="portal-summary-value">${safeText(data.created_at)}</span></div>` : ""}${data.paid_at ? `<div class="portal-summary-item"><span class="portal-summary-key">Đã thanh toán</span><span class="portal-summary-value">${safeText(data.paid_at)}</span></div>` : ""}</div><div class="portal-form-footer"><span class="portal-form-note">${safeText(flow.message || "Đang chờ trạng thái canonical.")}${polling ? " Portal sẽ chỉ poll GET trạng thái canonical; không gọi PayOS trực tiếp." : ""}</span>${checkout ? `<a class="portal-button portal-button--primary" href="${safeText(checkout)}" target="_blank" rel="noopener noreferrer">Mở trang thanh toán</a>` : ""}${orderId ? `<button class="portal-button portal-button--quiet" type="button" data-portal-action="refresh-payment" data-payment-id="${safeText(orderId)}"${refreshEnabled ? "" : " disabled"}>Làm mới trạng thái</button>` : ""}</div></section>`;
  }

  function renderWallet(page, context) {
    const topup = page.path === "/wallet/topup";
    const wallet = context.wallet && typeof context.wallet === "object" ? context.wallet : null;
    const history = Array.isArray(context.walletHistory) ? context.walletHistory : [];
    const walletCard = wallet
      ? `<section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Số dư canonical</h2><p class="portal-card-subtitle">Dữ liệu được đọc từ bot qua private bridge, không tính lại trong browser.</p></div>${badge("completed")}</div><div class="portal-admin-grid"><div class="portal-metric"><span>Số dư</span><strong>${safeText(String(wallet.balance_xu || 0))} Xu</strong><em>Canonical wallet</em></div><div class="portal-metric"><span>Đã dùng</span><strong>${safeText(String(wallet.total_spent_xu || 0))} Xu</strong><em>Lịch sử canonical</em></div><div class="portal-metric"><span>Gói</span><strong>${safeText((wallet.plan && (wallet.plan.plan_name || wallet.plan.current_plan)) || "—")}</strong><em>${safeText((wallet.plan && wallet.plan.plan_status) || "Không có gói")}</em></div></div><div class="portal-form-footer"><span class="portal-form-note">Nạp Xu, gói và bảng giá chỉ mở dữ liệu/luồng đã được Core Bridge cấp.</span><a class="portal-button portal-button--primary" href="/wallet/topup">Nạp Xu</a><a class="portal-button portal-button--quiet" href="/packages">Xem gói</a><a class="portal-button portal-button--quiet" href="/pricing">Bảng giá</a></div></section>`
      : `<section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Số dư canonical</h2><p class="portal-card-subtitle">Số dư không được cache hoặc tính lại tại browser.</p></div>${badge("guarded")}</div>${renderEmpty("Chờ dữ liệu ví", "Core Bridge phải trả số dư và lịch sử đã xác minh cho signed session.", "◌")}</section>`;
    return `<article class="portal-page">${renderHero(page, context)}<div class="portal-status-grid">${renderStatusCard(page, context)}${renderSummary(page, context)}</div>
      <div class="portal-work-grid"><div class="portal-stack">${topup ? `${renderPaymentEntryPoints(context)}${renderManualTopupGuide(context)}${renderPaymentRequestForm(page, context)}${renderPaymentLookup(context)}${renderPaymentFlow(context)}` : walletCard}</div>
      <aside class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Quy tắc thanh toán</h2><p class="portal-card-subtitle">Bảo vệ khỏi double-credit và webhook trùng.</p></div></div>${renderNotes(page)}</aside></div>
      <section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Lịch sử Xu</h2><p class="portal-card-subtitle">Đọc từ ledger của bot.</p></div></div>${renderRowsTable(["Thời gian", "Loại", "Thay đổi", "Số dư"], history, (item) => `<td>${safeText(item.created_at || "—")}</td><td>${safeText(item.event_type || "—")}</td><td>${safeText(String(item.delta_xu || 0))} Xu</td><td>${safeText(String(item.balance_after_xu || 0))} Xu</td>`, "Chưa có lịch sử được cấp", "Browser không tự dựng lịch sử giao dịch.")}</section></article>`;
  }

  function renderCatalog(page, context) {
    const pricing = context.pricingCatalog && context.pricingCatalog.available ? context.pricingCatalog : null;
    const packages = context.packageCatalog && context.packageCatalog.available ? context.packageCatalog : null;
    // Pricing/packages must never fall back to the feature registry: a list
    // of tools presented as prices would be misleading when the canonical bot
    // bridge is unavailable.
    let catalog = (page.path === "/pricing" || page.path === "/packages") ? [] : (context.catalog || []);
    if (page.path === "/pricing" && pricing) {
      catalog = [
        ...(pricing.image_tiers || []).map((item) => ({ title: `Ảnh · ${item.label || item.code}`, description: item.note || "Tier ảnh canonical từ bot.", priceLabel: `${item.cost_xu || 0} Xu`, status: "completed" })),
        ...(pricing.video_tiers || []).map((item) => ({ title: `Video · ${item.label || item.code}`, description: item.note || "Tier video canonical từ bot.", priceLabel: `${item.cost_xu || 0} Xu`, status: "completed" })),
        ...(pricing.video_combos || []).map((item) => ({ title: item.label || item.code, description: item.summary || "Combo canonical từ bot.", priceLabel: item.display_price || (item.price_vnd ? `${item.price_vnd}đ` : "Liên hệ"), status: "completed" }))
      ];
    } else if (page.path === "/packages" && packages) {
      catalog = [
        ...(packages.monthly || []).map((item) => ({ title: item.label || item.code, description: item.note || "Gói tháng canonical từ bot.", priceLabel: item.manual ? "Admin quản lý" : (item.price_vnd ? `${item.price_vnd.toLocaleString("vi-VN")}đ` : "Chờ giá canonical"), status: "completed" })),
        ...(packages.combos || []).map((item) => ({ title: item.label || item.code, description: item.note || "Combo canonical từ bot.", priceLabel: item.manual ? "Admin quản lý" : (item.price_vnd ? `${item.price_vnd.toLocaleString("vi-VN")}đ` : "Chờ giá canonical"), status: "completed" }))
      ];
    }
    const hasCatalog = catalog.length > 0;
    const emptyTitle = page.path === "/pricing" ? "Chờ bảng giá canonical" : page.path === "/packages" ? "Chờ danh mục gói canonical" : "Catalog chưa được cấp";
    const emptyText = page.path === "/pricing" ? "Bảng giá sẽ chỉ xuất hiện sau khi bot canonical trả dữ liệu đã ký qua Core Bridge." : page.path === "/packages" ? "Gói dịch vụ sẽ chỉ xuất hiện sau khi bot canonical xác nhận danh mục hiện hành." : "Giá, Xu và chính sách payment chỉ xuất hiện khi Core Bridge gửi catalog đã xác minh.";
    const cards = hasCatalog ? catalog.map((entry) => {
      const item = typeof entry === "string" ? { title: entry } : entry || {};
      return `<section class="portal-module-card"><div class="portal-module-card-top"><span class="portal-module-icon">◇</span>${badge(item.status && ALLOWED_STATES.has(item.status) ? item.status : "guarded")}</div><div><h3>${safeText(item.title || item.name || "Gói dịch vụ")}</h3><p>${safeText(item.description || "Thông tin quyền lợi do server phát hành.")}</p></div><span class="portal-module-card-footer"><span>${safeText(item.priceLabel || "Giá chờ Core Bridge")}</span><span class="portal-module-arrow">→</span></span></section>`;
    }).join("") : renderEmpty(emptyTitle, emptyText, "◇");
    return `<article class="portal-page">${renderHero(page, context)}<div class="portal-status-grid">${renderStatusCard(page, context)}${renderSummary(page, context)}</div><section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">${page.path === "/pricing" ? "Giá theo catalog" : "Gói hiện có"}</h2><p class="portal-card-subtitle">Không tự suy đoán tỷ lệ Xu, giá hoặc khuyến mãi.</p></div>${badge(stateFor(page, context))}</div><div class="portal-module-grid">${cards}</div></section></article>`;
  }

  const JOB_FILTERS = Object.freeze([
    ["all", "Tất cả"], ["queued", "Đã xếp hàng"], ["processing", "Đang xử lý"], ["completed", "Hoàn tất"], ["failed", "Thất bại"], ["cancelled", "Đã hủy"], ["refunded", "Đã hoàn Xu"]
  ]);

  // These are browser-only views over redacted bridge metadata.  They never
  // decide that an asset is downloadable or that a ticket/job is owned.
  const ASSET_FILTERS = Object.freeze([
    ["all", "Tất cả"], ["validated", "Output đã xác minh"], ["waiting", "Chờ delivery"], ["completed", "Job hoàn tất"], ["failed", "Không có output"]
  ]);
  const TICKET_FILTERS = Object.freeze([
    ["all", "Tất cả"], ["new", "Mới"], ["reviewing", "Đang kiểm tra"], ["waiting_user", "Chờ bạn bổ sung"], ["waiting_provider", "Chờ provider"], ["refund_pending", "Chờ kiểm tra hoàn Xu"], ["resolved", "Đã xử lý"], ["closed", "Đã đóng"]
  ]);
  const TICKET_STATUS_LABELS = Object.freeze({
    new: "Mới", reviewing: "Đang kiểm tra", waiting_user: "Chờ khách bổ sung",
    waiting_provider: "Chờ provider", refund_pending: "Chờ kiểm tra hoàn Xu",
    resolved: "Đã xử lý", closed: "Đã đóng"
  });
  const TICKET_CATEGORY_LABELS = Object.freeze({
    web_ticket: "Hỗ trợ Web", payment_topup: "Nạp Xu/Thanh toán", image_error: "Lỗi ảnh",
    video_error: "Lỗi video", document_pdf: "Tài liệu/PDF", package_combo: "Gói/Combo",
    refund: "Hoàn Xu/Refund", feature_request: "Góp ý tính năng", lead_consulting: "Tư vấn dịch vụ",
    general_support: "Hỗ trợ chung", service_consulting: "Tư vấn gói dịch vụ",
    premium_lead: "Đăng ký Premium", custom_bot_lead: "Kết nối bot riêng", other: "Nội dung khác"
  });

  function jobStatus(item) {
    const value = String(item && item.status || "guarded").toLowerCase();
    if (ALLOWED_STATES.has(value)) return value;
    const aliases = { pending: "queued", new: "queued", running: "processing", success: "completed", succeeded: "completed", active: "ready", inactive: "disabled", canceled: "cancelled", refund: "refunded", error: "failed" };
    return aliases[value] || "guarded";
  }

  function canonicalTicketStatus(item) {
    const value = String(item && item.status || "guarded").trim().toLowerCase();
    const aliases = {
      open: "new", pending: "new", received: "new", queued: "new",
      reviewed: "reviewing", in_progress: "reviewing", assigned: "reviewing", processing: "reviewing",
      answered: "resolved", done: "resolved", completed: "resolved",
      rejected: "closed", cancelled: "closed", canceled: "closed", failed: "closed", error: "closed"
    };
    return TICKET_STATUS_LABELS[value] ? value : (aliases[value] || "unknown");
  }

  function ticketStatus(item) {
    const visualStates = {
      new: "queued", reviewing: "processing", waiting_user: "awaiting_confirm",
      waiting_provider: "processing", refund_pending: "awaiting_confirm",
      resolved: "completed", closed: "cancelled"
    };
    return visualStates[canonicalTicketStatus(item)] || "guarded";
  }

  function ticketStatusLabel(item) {
    const canonical = canonicalTicketStatus(item);
    return TICKET_STATUS_LABELS[canonical] || "Trạng thái chưa được bot công bố";
  }

  function ticketCategoryLabel(item) {
    const category = String(item && item.category || "").trim().toLowerCase();
    return TICKET_CATEGORY_LABELS[category] || "Hỗ trợ";
  }

  function ticketStatusCell(item) {
    return `<span class="portal-ticket-status">${badge(ticketStatus(item))}<small>${safeText(ticketStatusLabel(item))}</small></span>`;
  }

  function paymentStatus(item) {
    const value = String(item && item.status || "guarded").toLowerCase();
    if (ALLOWED_STATES.has(value)) return value;
    const aliases = { pending: "queued", waiting: "queued", unpaid: "queued", paid: "completed", success: "completed", succeeded: "completed", canceled: "cancelled", refund: "refunded", error: "failed" };
    return aliases[value] || "guarded";
  }

  function reportedOutput(item) {
    if (!(item && item.output_available)) return `<span class="portal-delivery-state" data-delivery="waiting">Chưa có metadata</span>`;
    const status = jobStatus(item);
    if (["failed", "cancelled", "refunded"].includes(status)) return `<span class="portal-delivery-state" data-delivery="unavailable">Metadata output đã bị giữ</span>`;
    if (status === "completed") return `<span class="portal-delivery-state" data-delivery="reported">Có metadata output · chờ validation</span>`;
    return `<span class="portal-delivery-state" data-delivery="reported">Có metadata output · chưa đủ delivery</span>`;
  }

  function deliveryPending() {
    return `<span class="portal-delivery-state" data-delivery="pending">Chờ delivery canonical</span>`;
  }

  function assetDownloadPath(item) {
    const assetId = String(item && item.id || "").trim();
    if (!/^[A-Za-z0-9._:-]{1,160}$/.test(assetId)) return "";
    return `/api/v1/assets/${encodeURIComponent(assetId)}/download`;
  }

  function assetJobLink(item) {
    // Bot P0 uses the same opaque canonical identifier for the asset/job
    // projection. Linking only this already-redacted ID gives the customer a
    // safe way to inspect ownership-checked job status; it never grants a
    // download, provider handle or filesystem path.
    const assetId = String(item && item.id || "").trim();
    if (!/^[A-Za-z0-9._:-]{1,160}$/.test(assetId)) return safeText(assetId || "—");
    return `<a href="/jobs/${encodeURIComponent(assetId)}">${safeText(assetId)}</a>`;
  }

  function assetDeliveryState(item, surface) {
    if (item && item.download_ready === true) {
      const deliveryPath = surface === "asset" && item.delivery_ready === true ? assetDownloadPath(item) : "";
      if (deliveryPath) {
        // This remains a same-origin signed-session request. The API checks
        // asset ownership and only then redirects once to a configured,
        // short-lived Bot-issued URL; no provider URL lives in portal state.
        return `<a class="portal-delivery-state portal-delivery-link" data-delivery="validated" href="${safeText(deliveryPath)}" rel="noreferrer">Tải tệp đã xác thực</a>`;
      }
      return `<span class="portal-delivery-state" data-delivery="validated">Output hợp lệ · chờ URL ký</span>`;
    }
    const status = jobStatus(item);
    if (["failed", "cancelled", "refunded"].includes(status)) return `<span class="portal-delivery-state" data-delivery="unavailable">Không có delivery</span>`;
    if (item && item.output_available) return `<span class="portal-delivery-state" data-delivery="reported">Có metadata output · chưa đủ delivery</span>`;
    if (status === "completed") return `<span class="portal-delivery-state" data-delivery="pending">Job hoàn tất · chưa có delivery Web</span>`;
    return deliveryPending();
  }

  function exactJobAssets(job, source) {
    const jobId = String(job && job.id || "").trim();
    if (!/^[A-Za-z0-9._:-]{1,160}$/.test(jobId) || !Array.isArray(source)) return [];
    return source
      .filter((item) => item && typeof item === "object" && String(item.id || "").trim() === jobId)
      .slice(0, 12);
  }

  function renderJobOutputAssets(job, source) {
    const assets = exactJobAssets(job, source);
    if (!assets.length) {
      return `<section class="portal-card portal-card-pad" data-job-output-assets><div class="portal-card-header"><div><h2 class="portal-card-title">Tài sản của job</h2><p class="portal-card-subtitle">Chỉ metadata asset owner-scoped mới có thể tạo delivery Web.</p></div>${badge("guarded")}</div>${renderEmpty("Chưa có tài sản được xác minh cho job này", "Job hoàn tất hoặc có metadata output chưa đồng nghĩa có asset delivery. Hãy làm mới hoặc mở Thư viện tài sản sau khi Bot cập nhật canonical.", "◌")}</section>`;
    }
    return `<section class="portal-card portal-card-pad" data-job-output-assets><div class="portal-card-header"><div><h2 class="portal-card-title">Tài sản của job</h2><p class="portal-card-subtitle">Danh sách chỉ lấy từ asset metadata thuộc signed session, đối chiếu đúng ID job.</p></div>${badge("read_only")}</div>${renderRowsTable(["Tài sản", "Tính năng", "Trạng thái", "Tạo lúc", "Delivery"], assets, (item) => `<td>${assetJobLink(item)}</td><td>${safeText(item.feature || job.feature || "—")}</td><td>${badge(jobStatus(item))}</td><td>${safeText(item.created_at || "—")}</td><td>${assetDeliveryState(item, "asset")}</td>`, "Chưa có tài sản được cấp", "Web không suy diễn asset từ runtime hoặc URL output.")}</section>`;
  }

  function canonicalXu(value) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? `${parsed.toLocaleString("vi-VN")} Xu` : "—";
  }

  function jobCost(item) {
    const refund = String(item && item.refund_status || "").trim();
    return `<span class="portal-job-cost"><strong>Dự kiến ${safeText(canonicalXu(item && item.estimated_xu))}</strong><small>Ledger ${safeText(canonicalXu(item && item.charged_xu))}${refund ? ` · ${safeText(refund)}` : ""}</small></span>`;
  }

  function shortText(value, limit) {
    const text = String(value === undefined || value === null ? "" : value).replace(/\s+/g, " ").trim();
    const max = Math.max(1, Number(limit || 140));
    return safeText(text.length > max ? `${text.slice(0, max - 1).trimEnd()}…` : (text || "—"));
  }

  function filterBar(filters, selected, action, attribute, label, counts) {
    return `<div class="portal-filter-bar" aria-label="${safeText(label)}">${filters.map(([value, title]) => `<button class="portal-filter-button${selected === value ? " is-active" : ""}" type="button" data-portal-action="${safeText(action)}" ${safeText(attribute)}="${safeText(value)}" aria-pressed="${selected === value}">${safeText(title)} <span>${safeText(String(counts[value] || 0))}</span></button>`).join("")}</div>`;
  }

  function jobStateExplanation(item) {
    const status = jobStatus(item);
    const copy = {
      draft: "Bot mới lưu planning; chưa có hàng đợi engine hoặc delivery Web.",
      awaiting_confirm: "Estimate đang chờ xác nhận canonical; browser không tự đưa job vào queue.",
      queued: "Bot đã ghi nhận hàng đợi. Không có polling provider trực tiếp trong browser.",
      processing: "Runtime canonical đang xử lý. Output chỉ hiện sau khi metadata được xác minh.",
      completed: "Engine đã báo hoàn tất. Delivery Web vẫn cần URL ký tạm thời và ownership check.",
      failed: "Job dừng ở runtime canonical. Không sinh output thay thế trong portal.",
      cancelled: "Job đã bị hủy theo trạng thái canonical; không có delivery Web.",
      refunded: "Bot đã báo trạng thái hoàn Xu. Số ledger hiển thị chỉ để tham khảo canonical.",
      guarded: "Adapter hoặc quyền hiện tại đang bảo vệ dữ liệu/job này."
    };
    return copy[status] || "Trạng thái được Core Bridge phát hành; browser không suy diễn lifecycle.";
  }

  function jobNeedsDeliverySupport(job, source) {
    if (jobStatus(job) !== "completed") return false;
    const assets = exactJobAssets(job, source);
    const outputReported = Boolean(job && job.output_available) || assets.some((item) => item && (item.output_available === true || item.download_ready === true));
    const deliveryReady = assets.some((item) => item && item.download_ready === true && item.delivery_ready === true);
    return outputReported && !deliveryReady;
  }

  function renderJobRecoverySupport(job, context, source) {
    const jobId = String(job && job.id || "").trim();
    const status = jobStatus(job);
    const recoveryStates = new Set(["failed", "failed_no_charge", "cancelled", "guarded"]);
    const deliveryPending = jobNeedsDeliverySupport(job, source);
    if (!/^[A-Za-z0-9._:-]{1,160}$/.test(jobId) || (!recoveryStates.has(status) && !deliveryPending)) return "";
    const enabled = context && context.capabilities && context.capabilities["create-ticket"] === true;
    const disabled = enabled ? "" : " disabled";
    const feature = String(job.feature || job.job_type || "—").trim().slice(0, 160) || "—";
    const subject = deliveryPending ? `Hỗ trợ delivery job ${jobId}` : `Hỗ trợ job ${jobId}`;
    const reason = enabled
      ? (deliveryPending
        ? "Ticket chỉ báo thiếu delivery sau output đã được Bot xác nhận; Web không tạo URL, retry, refund hay thay đổi Xu từ form này."
        : "Ticket chỉ gửi ngữ cảnh text an toàn sang Bot canonical; không retry, refund hay thay đổi Xu từ form này.")
      : "Cần signed session, CSRF và Core Bridge sẵn sàng trước khi gửi ticket hỗ trợ.";
    const title = deliveryPending ? "Output đã xong nhưng delivery đang chờ" : "Cần hỗ trợ cho job này?";
    const description = deliveryPending
      ? "Bot đã báo output hợp lệ, nhưng Web chưa nhận delivery URL ký. Đội hỗ trợ sẽ đối chiếu mã job trong Bot canonical."
      : "Dùng khi Bot đã trả trạng thái không thể tiếp tục trong Portal. Đội hỗ trợ sẽ đối chiếu mã job trong Bot canonical.";
    return `<section class="portal-card portal-card-pad" data-job-recovery-support data-delivery-pending="${deliveryPending ? "true" : "false"}"><div class="portal-card-header"><div><h2 class="portal-card-title">${safeText(title)}</h2><p class="portal-card-subtitle">${safeText(description)}</p></div>${badge(enabled ? "awaiting_confirm" : "guarded")}</div><div class="portal-summary-list"><div class="portal-summary-item"><span class="portal-summary-key">Job</span><span class="portal-summary-value">${safeText(jobId)}</span></div><div class="portal-summary-item"><span class="portal-summary-key">Workflow</span><span class="portal-summary-value">${safeText(feature)}</span></div><div class="portal-summary-item"><span class="portal-summary-key">Trạng thái</span><span class="portal-summary-value">${badge(status)}</span></div></div><form class="portal-form" data-portal-form data-portal-action="create-ticket" data-portal-route="/jobs/${safeText(jobId)}" novalidate><label class="portal-field"><span class="portal-label">Chủ đề ticket</span><input class="portal-input" name="subject" value="${safeText(subject)}" readonly aria-readonly="true"></label><label class="portal-field portal-field-wide"><span class="portal-label">Bạn cần hỗ trợ gì?</span><textarea class="portal-textarea" name="detail" placeholder="Mô tả điều bạn thấy và thời điểm xảy ra. Không gửi API key, mật khẩu, OTP/CVV, bill, TXID, số tài khoản hoặc QR thanh toán." minlength="3" maxlength="4000" required${disabled}></textarea><span class="portal-field-help">Mã job nằm trong chủ đề để đối chiếu thủ công. Web chưa ghi quan hệ job-ticket canonical, không đính kèm output hoặc dữ liệu thanh toán.</span></label><div class="portal-form-footer"><span class="portal-form-note">${safeText(reason)}</span><button class="portal-button portal-button--primary" type="submit"${disabled}>Tạo ticket hỗ trợ</button></div></form></section>`;
  }

  function renderJobs(page, context) {
    const allJobs = Array.isArray(context.jobs) ? context.jobs : [];
    const selected = JOB_FILTERS.some(([value]) => value === context.jobFilter) ? context.jobFilter : "all";
    const jobs = selected === "all" ? allJobs : allJobs.filter((item) => jobStatus(item) === selected);
    const refreshEnabled = context.capabilities && context.capabilities["refresh-jobs"] === true;
    const counts = Object.fromEntries(JOB_FILTERS.map(([status]) => [status, status === "all" ? allJobs.length : allJobs.filter((item) => jobStatus(item) === status).length]));
    const filters = filterBar(JOB_FILTERS, selected, "filter-jobs", "data-job-filter", "Lọc job", counts);
    return `<article class="portal-page">${renderHero(page, context)}<div class="portal-status-grid">${renderStatusCard(page, context)}${renderSummary(page, context)}</div>
      <section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Job gần đây (tối đa 100)</h2><p class="portal-card-subtitle">Bridge P0 hiện trả tối đa 100 job mới nhất thuộc signed session. Chi phí là metadata canonical; browser không tính Xu, gọi provider hoặc tạo delivery.</p></div><div class="portal-inline-actions"><button class="portal-button portal-button--quiet" type="button" data-portal-action="refresh-jobs" data-portal-route="/jobs"${refreshEnabled ? "" : " disabled"}>Làm mới</button><a class="portal-button portal-button--quiet" href="/assets">Mở tài sản →</a></div></div>${filters}${renderRowsTable(["Job", "Tính năng", "Trạng thái", "Chi phí canonical", "Cập nhật", "Output engine"], jobs, (item) => `<td><a href="/jobs/${encodeURIComponent(item.id || "")}">${safeText(item.id || "—")}</a></td><td>${safeText(item.feature || "—")}</td><td>${badge(jobStatus(item))}</td><td>${jobCost(item)}</td><td>${safeText(item.updated_at || item.created_at || "—")}</td><td>${reportedOutput(item)}</td>`, selected === "all" ? "Chưa có job được xác minh" : "Không có job ở trạng thái này", selected === "all" ? "Core Bridge sẽ trả job sau khi tạo/confirm thành công." : "Đổi bộ lọc hoặc làm mới để nhận trạng thái canonical mới nhất.")}</section>
      <section class="portal-card portal-card-pad"><div class="portal-notice portal-notice--info"><span class="portal-notice-icon" aria-hidden="true">i</span><div><strong>Delivery được tách riêng khỏi engine</strong><p>Job completed hoặc metadata output không tạo preview/download. Cần một signed delivery contract, ownership check và validation artifact trước khi Web mở file.</p></div></div></section></article>`;
  }

  function renderJobDetail(page, context) {
    const record = safeText(page.recordId || "—");
    const job = context.jobDetail && typeof context.jobDetail === "object" ? context.jobDetail : null;
    const jobAssets = exactJobAssets(job, context.jobAssets);
    const deliveryAsset = jobAssets[0] || null;
    const detail = job && Object.keys(job).length
      ? `<div class="portal-summary-list"><div class="portal-summary-item"><span class="portal-summary-key">Tính năng</span><span class="portal-summary-value">${safeText(job.feature || job.job_type || "—")}</span></div><div class="portal-summary-item"><span class="portal-summary-key">Trạng thái canonical</span><span class="portal-summary-value">${badge(jobStatus(job))}</span></div><div class="portal-summary-item"><span class="portal-summary-key">Tạo lúc</span><span class="portal-summary-value">${safeText(job.created_at || "—")}</span></div><div class="portal-summary-item"><span class="portal-summary-key">Cập nhật</span><span class="portal-summary-value">${safeText(job.updated_at || job.created_at || "—")}</span></div><div class="portal-summary-item"><span class="portal-summary-key">Xu dự kiến</span><span class="portal-summary-value">${safeText(canonicalXu(job.estimated_xu))}</span></div><div class="portal-summary-item"><span class="portal-summary-key">Xu đã ghi ledger</span><span class="portal-summary-value">${safeText(canonicalXu(job.charged_xu))}</span></div>${job.refund_status ? `<div class="portal-summary-item"><span class="portal-summary-key">Hoàn Xu</span><span class="portal-summary-value">${safeText(job.refund_status)}</span></div>` : ""}${job.error_category ? `<div class="portal-summary-item"><span class="portal-summary-key">Nhóm lỗi canonical</span><span class="portal-summary-value">${safeText(job.error_category)}</span></div>` : ""}<div class="portal-summary-item"><span class="portal-summary-key">Output engine</span><span class="portal-summary-value">${reportedOutput(job)}</span></div><div class="portal-summary-item"><span class="portal-summary-key">Delivery Web</span><span class="portal-summary-value">${assetDeliveryState(deliveryAsset || job, deliveryAsset ? "asset" : "")}</span></div></div>`
      : renderEmpty("Chưa có job detail an toàn", "Bridge cần kiểm tra ownership trước khi trả request, timeline và output của job này.", "⌛");
    return `<article class="portal-page">${renderHero(page, context)}<div class="portal-status-grid">${renderStatusCard(page, context)}${renderSummary(page, context)}</div>
      <div class="portal-work-grid"><section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Job ${record}</h2><p class="portal-card-subtitle">ID hiển thị không xác thực dữ liệu hoặc quyền download.</p></div>${badge(job ? jobStatus(job) : stateFor(page, context))}</div>${detail}</section>
      <aside class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Delivery protection</h2><p class="portal-card-subtitle">Không có download trực tiếp từ path đoán được.</p></div>${job ? assetDeliveryState(deliveryAsset || job, deliveryAsset ? "asset" : "") : deliveryPending()}<div class="portal-notice portal-notice--info" style="margin-top:14px"><span class="portal-notice-icon" aria-hidden="true">i</span><div><strong>Trạng thái hiện tại</strong><p>${safeText(job ? jobStateExplanation(job) : "Chờ Core Bridge kiểm tra ownership trước khi mô tả job.")}</p></div></div>${renderNotes(page)}</aside></div>${renderJobOutputAssets(job, context.jobAssets)}${renderJobRecoverySupport(job, context, context.jobAssets)}</article>`;
  }

  function renderAssets(page, context) {
    const allAssets = Array.isArray(context.assets) ? context.assets : [];
    const selected = ASSET_FILTERS.some(([value]) => value === context.assetFilter) ? context.assetFilter : "all";
    const isSelected = (item, value) => {
      if (value === "all") return true;
      if (value === "validated") return item && item.download_ready === true;
      if (value === "waiting") return !(item && item.download_ready === true);
      return jobStatus(item) === value;
    };
    const assets = allAssets.filter((item) => isSelected(item, selected));
    const counts = Object.fromEntries(ASSET_FILTERS.map(([value]) => [value, allAssets.filter((item) => isSelected(item, value)).length]));
    const filters = filterBar(ASSET_FILTERS, selected, "filter-assets", "data-asset-filter", "Lọc tài sản", counts);
    const refreshEnabled = context.capabilities && context.capabilities["refresh-assets"] === true;
    return `<article class="portal-page">${renderHero(page, context)}<div class="portal-status-grid">${renderStatusCard(page, context)}${renderSummary(page, context)}</div>
      <section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Tài sản gần đây (tối đa 100)</h2><p class="portal-card-subtitle">Bridge P0 hiện trả tối đa 100 metadata mới nhất. Output hợp lệ và URL tải là hai contract riêng: metadata không cấp quyền file.</p></div><button class="portal-button portal-button--quiet" type="button" data-portal-action="refresh-assets" data-portal-route="/assets"${refreshEnabled ? "" : " disabled"}>Làm mới</button></div>${filters}${renderRowsTable(["Tài sản", "Tính năng", "Trạng thái", "Tạo lúc", "Delivery"], assets, (item) => `<td>${assetJobLink(item)}</td><td>${safeText(item.feature || "—")}</td><td>${badge(jobStatus(item))}</td><td>${safeText(item.created_at || "—")}</td><td>${assetDeliveryState(item, "asset")}</td>`, selected === "all" ? "Chưa có tài sản có thể mở" : "Không có tài sản ở bộ lọc này", selected === "all" ? "Shell không hiển thị placeholder là output thật. Tài sản hoàn tất sẽ đến từ Core Bridge." : "Đổi bộ lọc hoặc làm mới metadata canonical để kiểm tra delivery.")}</section></article>`;
  }

  function validVaultAssetId(value) {
    return /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(String(value || "").trim());
  }

  function vaultItems(context) {
    return (Array.isArray(context.vaultItems) ? context.vaultItems : [])
      .filter((item) => item && typeof item === "object" && validVaultAssetId(item.id) && String(item.state || "") === "active")
      .slice(0, 100);
  }

  function vaultBytes(value) {
    const bytes = Number(value);
    if (!Number.isFinite(bytes) || bytes < 0) return "—";
    if (bytes < 1024) return `${Math.floor(bytes)} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }

  function vaultDownloadPath(item) {
    const assetId = String(item && item.id || "").trim();
    return validVaultAssetId(assetId) ? `/api/v1/asset-vault/${encodeURIComponent(assetId)}/download` : "";
  }

  function assetVaultFormFields() {
    return [
      { name: "display_name", label: "Tên hiển thị", placeholder: "Ví dụ: Brief ra mắt mùa hè", maxLength: 120, help: "Tùy chọn. Nếu để trống, Web dùng tên tệp an toàn làm nhãn." },
      { name: "project_id", label: "Gắn với Project", control: "select", optionsFrom: "projects", emptyLabel: "Không gắn Project", help: "Tùy chọn; chỉ Project đang hoạt động thuộc Web account hiện tại được hiển thị." }
    ];
  }

  function pdfVaultItems(context) {
    return vaultItems(context)
      .filter((item) => String(item.extension || "").toLowerCase() === ".pdf" && String(item.content_type || "") === "application/pdf")
      .slice(0, 100);
  }

  function imageVaultItems(context) {
    const allowed = {
      ".jpg": "image/jpeg",
      ".jpeg": "image/jpeg",
      ".png": "image/png",
      ".webp": "image/webp"
    };
    return vaultItems(context)
      .filter((item) => allowed[String(item.extension || "").toLowerCase()] === String(item.content_type || "").toLowerCase())
      .slice(0, 100);
  }

  function validDocumentOperationId(value) {
    return validVaultAssetId(value);
  }

  function documentOperationItems(context, requestedKind) {
    const kind = String(requestedKind || "").trim();
    return (Array.isArray(context.documentOperations) ? context.documentOperations : [])
      .filter((item) => {
        const itemKind = String(item && item.kind || "");
        return item && typeof item === "object" && validDocumentOperationId(item.id)
          && (kind ? itemKind === kind : ["pdf_split", "pdf_merge", "pdf_optimize", "image_to_pdf", "pdf_to_images", "pdf_to_word_text"].includes(itemKind));
      })
      .slice(0, 100);
  }

  function documentOperationState(item) {
    const state = String(item && item.state || "guarded").toLowerCase();
    return ALLOWED_STATES.has(state) ? state : "guarded";
  }

  function documentOperationDownloadPath(item) {
    const operationId = String(item && item.id || "").trim();
    return validDocumentOperationId(operationId) && documentOperationState(item) === "completed" && item && item.download_ready === true
      ? `/api/v1/document-operations/${encodeURIComponent(operationId)}/download`
      : "";
  }

  function pdfSplitFormFields() {
    return [
      {
        name: "source_asset_id", label: "PDF nguồn trong Asset Vault", control: "select", optionsFrom: "pdfVaultAssets",
        emptyLabel: "Chọn PDF riêng tư", required: true,
        help: "Chỉ PDF active thuộc signed Web account hiện tại xuất hiện. Không chọn URL, path hoặc tệp từ browser ở bước này."
      },
      {
        name: "page_range", label: "Trang cần tách", placeholder: "Ví dụ: 2 hoặc 2-5", required: true,
        pattern: "\\d+(?:-\\d+)?", maxLength: 32,
        help: "Chỉ một trang hoặc một dải liên tiếp. Dải đảo chiều như 5-2 được chuẩn hóa thành 2-5; giới hạn PDF nguồn là 20 MB và 30 trang."
      }
    ];
  }

  function pdfMergeFormFields() {
    return Array.from({ length: 8 }, (_, index) => {
      const position = index + 1;
      const required = position <= 2;
      return {
        name: `source_asset_id_${position}`,
        label: `PDF nguồn ${position}${required ? "" : " (tùy chọn)"}`,
        control: "select",
        optionsFrom: "pdfVaultAssets",
        emptyLabel: required ? `Chọn PDF thứ ${position}` : "Không thêm PDF",
        required,
        help: position === 1
          ? "Thứ tự slot quyết định thứ tự trang output. Chỉ PDF active thuộc signed Web account hiện tại được liệt kê."
          : position === 2
            ? "Cần tối thiểu hai nguồn khác nhau. Không dùng URL, path hoặc file browser trong bước này."
            : "Tùy chọn; để trống nếu không cần thêm nguồn. Một PDF chỉ có thể xuất hiện một lần."
      };
    });
  }

  function pdfOptimizeFormFields() {
    return [{
      name: "source_asset_id", label: "PDF nguồn trong Asset Vault", control: "select", optionsFrom: "pdfVaultAssets",
      emptyLabel: "Chọn PDF riêng tư", required: true,
      help: "Web tạo một bản tối ưu lossless độc lập và chỉ phát output nếu sau khi kiểm tra nó nhỏ hơn đủ ý nghĩa. File gốc không bị thay đổi."
    }];
  }

  function pdfToWordFormFields() {
    return [{
      name: "source_asset_id", label: "PDF nguồn trong Asset Vault", control: "select", optionsFrom: "pdfVaultAssets",
      emptyLabel: "Chọn PDF có text riêng tư", required: true,
      help: "Web chỉ trích xuất text mà parser PDF đọc được và tạo DOCX riêng tư mới. Không OCR, không đưa ảnh vào DOCX và không cam kết giữ nguyên bố cục, font hoặc định dạng thị giác."
    }];
  }

  function pdfToImagesFormFields() {
    return [{
      name: "source_asset_id", label: "PDF nguồn trong Asset Vault", control: "select", optionsFrom: "pdfVaultAssets",
      emptyLabel: "Chọn PDF riêng tư", required: true,
      help: "Server render toàn bộ trang ở 2× như Bot. Một trang tạo PNG private; nhiều trang tạo ZIP PNG private. Browser chỉ gửi ID asset, không gửi URL, path hoặc bytes PDF."
    }];
  }

  function imageToPdfFormFields() {
    return Array.from({ length: 8 }, (_, index) => {
      const position = index + 1;
      return {
        name: `source_asset_id_${position}`,
        label: `Ảnh nguồn ${position}${position === 1 ? "" : " (tùy chọn)"}`,
        control: "select",
        optionsFrom: "imageVaultAssets",
        emptyLabel: position === 1 ? "Chọn ảnh thứ 1" : "Không thêm ảnh",
        required: position === 1,
        help: position === 1
          ? "Ảnh 1 trở thành trang đầu. Chỉ JPEG, PNG hoặc WebP active của signed Web account hiện tại xuất hiện."
          : "Thứ tự slot là thứ tự trang PDF. Mỗi ảnh chỉ được chọn một lần; không dùng URL, path hoặc file browser ở bước này."
      };
    });
  }

  function validImageOperationId(value) {
    return validVaultAssetId(value);
  }

  function imageOperationItems(context) {
    return (Array.isArray(context.imageOperations) ? context.imageOperations : [])
      .filter((item) => item && typeof item === "object" && validImageOperationId(item.id)
        && String(item.kind || "") === "image_resize")
      .slice(0, 100);
  }

  function imageEnhanceOperationItems(context) {
    return (Array.isArray(context.imageEnhanceOperations) ? context.imageEnhanceOperations : [])
      .filter((item) => item && typeof item === "object" && validImageOperationId(item.id)
        && String(item.kind || "") === "image_enhance")
      .slice(0, 100);
  }

  function imageOperationState(item) {
    const state = String(item && item.state || "guarded").toLowerCase();
    return ALLOWED_STATES.has(state) ? state : "guarded";
  }

  function imageOperationDownloadPath(item) {
    const operationId = String(item && item.id || "").trim();
    return validImageOperationId(operationId) && imageOperationState(item) === "completed" && item && item.download_ready === true
      ? `/api/v1/image-operations/${encodeURIComponent(operationId)}/download`
      : "";
  }

  function imageResizeFormFields(values) {
    const selectedPreset = String(values && values.preset || transientFormValues("/image/resize").preset || "custom");
    const isCustom = selectedPreset === "custom";
    return [
      {
        name: "source_asset_id", label: "Ảnh nguồn trong Asset Vault", control: "select", optionsFrom: "imageVaultAssets",
        emptyLabel: "Chọn ảnh private", required: true,
        help: "Chỉ JPEG, PNG hoặc WebP active của signed Web account hiện tại xuất hiện. File gốc không bị ghi đè."
      },
      {
        name: "preset", label: "Canvas / tỷ lệ đích", control: "select", options: [
          { value: "custom", label: "Tùy chỉnh (nhập pixel)" },
          { value: "1:1", label: "Vuông 1:1 · 1024 × 1024" },
          { value: "4:5", label: "Chân dung 4:5 · 1080 × 1350" },
          { value: "9:16", label: "Story / Reel 9:16 · 1080 × 1920" },
          { value: "16:9", label: "Ngang 16:9 · 1920 × 1080" },
          { value: "3:4", label: "Chân dung 3:4 · 1080 × 1440" },
          { value: "4:3", label: "Cổ điển 4:3 · 1440 × 1080" },
          { value: "3:2", label: "Ảnh 3:2 · 1500 × 1000" },
          { value: "2:3", label: "Ảnh dọc 2:3 · 1000 × 1500" },
          { value: "21:9", label: "Wide 21:9 · 1920 × 823" }
        ],
        help: "Chọn preset để server dùng đúng pixel canonical của local image tool. Khi chọn Tùy chỉnh, nhập cả hai cạnh bên dưới."
      },
      {
        name: "target_width", label: "Chiều rộng tùy chỉnh (px)", type: "number", placeholder: "Ví dụ: 1080", min: 128, max: 4096, step: 1, inputMode: "numeric",
        required: isCustom, dynamicRequired: true, disabled: !isCustom,
        help: "Chỉ dùng khi Canvas là Tùy chỉnh. Nếu chọn preset, để trống để server áp pixel chuẩn; không nhập số khác preset."
      },
      {
        name: "target_height", label: "Chiều cao tùy chỉnh (px)", type: "number", placeholder: "Ví dụ: 1350", min: 128, max: 4096, step: 1, inputMode: "numeric",
        required: isCustom, dynamicRequired: true, disabled: !isCustom,
        help: "Canvas tối đa 16 MP, mỗi cạnh 128–4096 px, tỷ lệ tối đa 12:1. Không có upscale AI hoặc khôi phục chi tiết."
      },
      {
        name: "fit_mode", label: "Cách đặt ảnh vào canvas", control: "select", options: [
          { value: "pad", label: "Pad nền trắng · giữ trọn ảnh, không cắt" },
          { value: "crop", label: "Crop giữa khung · lấp đầy canvas, có thể cắt rìa" },
          { value: "blur", label: "Blur nền · giữ trọn ảnh ở giữa, nền mờ" }
        ],
        help: "Crop luôn cắt tâm, không có focal-point editor ở phiên bản này. Blur không nhận diện chủ thể; đây là xử lý ảnh cục bộ deterministic."
      }
    ];
  }

  const IMAGE_ENHANCE_PRESET_LABELS = {
    photo_clear_detail: "Rõ và chi tiết",
    product_clean: "Sản phẩm sạch sáng",
    cinematic_warm: "Cinematic ấm",
    fresh_blue: "Tươi xanh",
    food_vivid: "Ẩm thực nổi bật",
    custom: "Thông số tùy chỉnh"
  };

  function imageEnhanceFormFields(values) {
    const selectedPreset = String(values && values.preset || transientFormValues("/image/edit").preset || "photo_clear_detail");
    const isCustom = selectedPreset === "custom";
    return [
      {
        name: "source_asset_id", label: "Ảnh nguồn trong Asset Vault", control: "select", optionsFrom: "imageVaultAssets",
        emptyLabel: "Chọn ảnh private", required: true,
        help: "Chỉ JPEG, PNG hoặc WebP active của signed Web account hiện tại xuất hiện. File gốc không bị ghi đè."
      },
      {
        name: "preset", label: "Công thức màu cục bộ", control: "select", options: [
          { value: "photo_clear_detail", label: "Rõ và chi tiết · auto enhance" },
          { value: "product_clean", label: "Sản phẩm sạch sáng" },
          { value: "cinematic_warm", label: "Cinematic ấm" },
          { value: "fresh_blue", label: "Tươi xanh" },
          { value: "food_vivid", label: "Ẩm thực nổi bật" },
          { value: "custom", label: "Tùy chỉnh thông số" }
        ],
        help: "Preset dùng thông số deterministic canonical từ local editor của Bot. Chỉ chọn Tùy chỉnh khi cần nhập đủ bốn thông số bên dưới."
      },
      {
        name: "brightness", label: "Độ sáng", type: "number", placeholder: "0.50 – 2.00", min: 0.5, max: 2, step: 0.01, inputMode: "decimal",
        required: isCustom, dynamicRequired: true, disabled: !isCustom,
        help: "Chỉ dùng với Tùy chỉnh. 1.00 là giữ nguyên trước khi áp các bước tăng cường khác."
      },
      {
        name: "contrast", label: "Tương phản", type: "number", placeholder: "0.50 – 2.00", min: 0.5, max: 2, step: 0.01, inputMode: "decimal",
        required: isCustom, dynamicRequired: true, disabled: !isCustom,
        help: "Chỉ dùng với Tùy chỉnh. Không có HDR, khôi phục chi tiết hoặc AI retouch."
      },
      {
        name: "saturation", label: "Bão hòa màu", type: "number", placeholder: "0.50 – 2.00", min: 0.5, max: 2, step: 0.01, inputMode: "decimal",
        required: isCustom, dynamicRequired: true, disabled: !isCustom,
        help: "Chỉ dùng với Tùy chỉnh. Server chặn số ngoài 0.50–2.00."
      },
      {
        name: "sharpness", label: "Độ nét", type: "number", placeholder: "0.50 – 2.00", min: 0.5, max: 2, step: 0.01, inputMode: "decimal",
        required: isCustom, dynamicRequired: true, disabled: !isCustom,
        help: "Chỉ dùng với Tùy chỉnh. Đây là filter local, không tạo chi tiết AI mới."
      },
      {
        name: "tone", label: "Tone tùy chỉnh", control: "select", disabled: !isCustom, options: [
          { value: "neutral", label: "Neutral · không phủ tone" },
          { value: "warm", label: "Warm · ấm nhẹ" },
          { value: "cool", label: "Cool · xanh nhẹ" },
          { value: "clean", label: "Clean · sáng sạch" }
        ],
        help: "Chỉ dùng với Tùy chỉnh. Preset đã có tone canonical riêng."
      },
      {
        name: "basic_upscale", label: "Làm nét / nâng kích thước cơ bản", control: "select", options: [
          { value: "false", label: "Không · giữ kích thước an toàn" },
          { value: "true", label: "Có · tối đa 2×, luôn theo trần 4096 px / 16 MP" }
        ],
        help: "Dùng nội suy LANCZOS và UnsharpMask cục bộ. Không phải AI upscale; ảnh lớn có thể bị hạ về trần output để giữ an toàn."
      }
    ];
  }

  function imageEnhanceSettings(item) {
    const raw = item && item.settings && typeof item.settings === "object" ? item.settings : {};
    const values = ["brightness", "contrast", "saturation", "sharpness"].map((key) => {
      const value = Number(raw[key]);
      return Number.isFinite(value) ? `${key === "brightness" ? "Sáng" : key === "contrast" ? "Tương phản" : key === "saturation" ? "Bão hòa" : "Nét"} ${value.toFixed(2)}` : "";
    }).filter(Boolean);
    const tone = ["neutral", "warm", "cool", "clean"].includes(String(raw.tone || "")) ? `Tone ${String(raw.tone)}` : "";
    if (tone) values.push(tone);
    if (raw.basic_upscale === true) values.push("LANCZOS + sharpen cơ bản");
    return values.join(" · ") || "Preset canonical đã được server xác minh";
  }

  function renderImageEnhanceOperationCards(items) {
    if (!items.length) {
      return renderEmpty("Chưa có PNG đã chỉnh", "Bản sao chỉ xuất hiện sau khi server kiểm tra ảnh nguồn, áp preset/thông số cục bộ, mở lại PNG và xác minh integrity. Không có preview hoặc output mô phỏng.", "✦");
    }
    return `<div class="portal-document-operation-grid">${items.map((item) => {
      const status = imageOperationState(item);
      const downloadPath = imageOperationDownloadPath(item);
      const sourceWidth = Number(item.source_width);
      const sourceHeight = Number(item.source_height);
      const targetWidth = Number(item.target_width);
      const targetHeight = Number(item.target_height);
      const sourceGeometry = Number.isInteger(sourceWidth) && Number.isInteger(sourceHeight) ? `${sourceWidth} × ${sourceHeight}` : "Đang kiểm tra";
      const targetGeometry = Number.isInteger(targetWidth) && Number.isInteger(targetHeight) ? `${targetWidth} × ${targetHeight}` : "Canvas an toàn";
      const preset = String(item.preset || "custom");
      const pendingMessage = status === "failed" || status === "unavailable"
        ? "Không có PNG tải xuống; kiểm tra ảnh nguồn private và tạo bản sao mới."
        : status === "guarded"
          ? "Thao tác bị chặn an toàn; Web không phát output thay thế."
          : "Chỉ tải xuống sau khi server xác minh PNG và ownership.";
      return `<article class="portal-card portal-card-pad portal-document-operation-card" data-image-operation="${safeText(String(item.id))}"><div class="portal-card-header"><div class="portal-document-operation-title"><span class="portal-document-operation-icon" aria-hidden="true">✦</span><div><h2 class="portal-card-title">${safeText(String(item.original_filename || "PNG private đã chỉnh"))}</h2><p class="portal-card-subtitle">${safeText(IMAGE_ENHANCE_PRESET_LABELS[preset] || preset)}</p></div></div>${badge(status)}</div><dl class="portal-document-operation-meta"><div><dt>Nguồn</dt><dd>${safeText(sourceGeometry)}</dd></div><div><dt>PNG output</dt><dd>${safeText(targetGeometry)}</dd></div><div><dt>Thông số</dt><dd>${safeText(imageEnhanceSettings(item))}</dd></div><div><dt>Cập nhật</dt><dd>${safeText(String(item.completed_at || item.updated_at || item.created_at || "—"))}</dd></div></dl><div class="portal-form-footer">${downloadPath ? `<a class="portal-button portal-button--primary" href="${safeText(downloadPath)}" rel="noreferrer">Tải PNG riêng tư <span aria-hidden="true">↓</span></a>` : `<span class="portal-form-note">${pendingMessage}</span>`}</div></article>`;
    }).join("")}</div>`;
  }

  function renderImageOperationCards(items) {
    if (!items.length) {
      return renderEmpty("Chưa có PNG đã resize", "Bản sao chỉ xuất hiện sau khi server kiểm tra ảnh nguồn, render, mở lại PNG và xác minh integrity. Không có preview hay output mô phỏng.", "▧");
    }
    return `<div class="portal-document-operation-grid">${items.map((item) => {
      const status = imageOperationState(item);
      const downloadPath = imageOperationDownloadPath(item);
      const sourceWidth = Number(item.source_width);
      const sourceHeight = Number(item.source_height);
      const targetWidth = Number(item.target_width);
      const targetHeight = Number(item.target_height);
      const sourceGeometry = Number.isInteger(sourceWidth) && Number.isInteger(sourceHeight) ? `${sourceWidth} × ${sourceHeight}` : "Đang kiểm tra";
      const targetGeometry = Number.isInteger(targetWidth) && Number.isInteger(targetHeight) ? `${targetWidth} × ${targetHeight}` : "Canvas đã yêu cầu";
      const fitLabel = { crop: "Crop giữa khung", pad: "Pad nền trắng", blur: "Blur nền" }[String(item.fit_mode || "")] || "Đang kiểm tra";
      const pendingMessage = status === "failed" || status === "unavailable"
        ? "Không có PNG tải xuống; kiểm tra nguồn private và tạo bản sao mới."
        : status === "guarded"
          ? "Thao tác bị chặn an toàn; Web không phát output thay thế."
          : "Chỉ tải xuống sau khi server xác minh PNG và ownership.";
      return `<article class="portal-card portal-card-pad portal-document-operation-card" data-image-operation="${safeText(String(item.id))}"><div class="portal-card-header"><div class="portal-document-operation-title"><span class="portal-document-operation-icon" aria-hidden="true">PNG</span><div><h2 class="portal-card-title">${safeText(String(item.original_filename || "PNG private đã resize"))}</h2><p class="portal-card-subtitle">${safeText(fitLabel)} · ${safeText(String(item.preset || "custom"))}</p></div></div>${badge(status)}</div><dl class="portal-document-operation-meta"><div><dt>Nguồn</dt><dd>${safeText(sourceGeometry)}</dd></div><div><dt>Canvas</dt><dd>${safeText(targetGeometry)}</dd></div><div><dt>PNG output</dt><dd>${safeText(item.byte_size ? vaultBytes(item.byte_size) : "Chưa có")}</dd></div><div><dt>Cập nhật</dt><dd>${safeText(String(item.completed_at || item.updated_at || item.created_at || "—"))}</dd></div></dl><div class="portal-form-footer">${downloadPath ? `<a class="portal-button portal-button--primary" href="${safeText(downloadPath)}" rel="noreferrer">Tải PNG riêng tư <span aria-hidden="true">↓</span></a>` : `<span class="portal-form-note">${pendingMessage}</span>`}</div></article>`;
    }).join("")}</div>`;
  }

  function renderDocumentOperationCards(items, emptyTitle = "Chưa có artifact đã xử lý", emptyText = "Sau khi nguồn private vượt qua kiểm tra parser và output, attachment sẽ xuất hiện tại đây. Không có Job Bot hoặc output mô phỏng.") {
    if (!items.length) {
      return renderEmpty(emptyTitle, emptyText, "▤");
    }
    return `<div class="portal-document-operation-grid">${items.map((item) => {
      const status = documentOperationState(item);
      const downloadPath = documentOperationDownloadPath(item);
      const kind = String(item.kind || "");
      const isMerge = kind === "pdf_merge";
      const isOptimize = kind === "pdf_optimize";
      const isImageToPdf = kind === "image_to_pdf";
      const isPdfToImages = kind === "pdf_to_images";
      const isPdfToWord = kind === "pdf_to_word_text";
      const start = Number(item.selected_start_page);
      const end = Number(item.selected_end_page);
      const sourceCount = Math.max(1, Number(item.source_count) || 1);
      const selected = isOptimize
        ? "Tối ưu cấu trúc an toàn · file gốc được giữ nguyên"
        : isMerge
        ? `${sourceCount} PDF nguồn theo thứ tự đã chọn`
        : isImageToPdf
        ? `${sourceCount} ảnh nguồn theo thứ tự đã chọn`
        : isPdfToImages
        ? "Render toàn bộ trang PDF ở 2×"
        : isPdfToWord
        ? "Trích xuất text có thể chọn từ PDF"
        : (Number.isInteger(start) && Number.isInteger(end) ? (start === end ? `Trang ${start}` : `Trang ${start}–${end}`) : "Đang xác minh phạm vi");
      const sourcePages = Number(item.source_page_count);
      const outputPages = Number(item.output_page_count);
      const sourceMetric = isOptimize
        ? (Number.isFinite(Number(item.input_byte_size)) ? vaultBytes(item.input_byte_size) : (Number.isInteger(sourcePages) ? `${safeText(String(sourcePages))} trang` : "Đang kiểm tra"))
        : isMerge
        ? `${safeText(String(sourceCount))} PDF${Number.isInteger(sourcePages) ? ` · ${safeText(String(sourcePages))} trang` : ""}`
        : isImageToPdf
        ? `${safeText(String(sourceCount))} ảnh${Number.isInteger(sourcePages) ? ` · ${safeText(String(sourcePages))} trang` : ""}`
        : isPdfToImages
        ? (Number.isInteger(sourcePages) ? `${safeText(String(sourcePages))} trang PDF` : "Đang kiểm tra")
        : isPdfToWord
        ? (Number.isInteger(sourcePages) ? `${safeText(String(sourcePages))} trang PDF` : "Đang kiểm tra")
        : (Number.isInteger(sourcePages) ? `${safeText(String(sourcePages))} trang` : "Đang kiểm tra");
      const savedBytes = Number(item.saved_bytes);
      const savedPercent = Number(item.saved_percent);
      const thirdMetric = isOptimize
        ? (Number.isFinite(savedBytes) && savedBytes > 0 ? `${safeText(vaultBytes(savedBytes))}${Number.isFinite(savedPercent) ? ` · ${safeText(String(savedPercent))}%` : ""}` : "Chưa giảm đủ")
        : safeText(item.byte_size ? vaultBytes(item.byte_size) : "Đang kiểm tra");
      const pendingMessage = isOptimize && status === "guarded"
        ? "Không có bản nhỏ hơn đạt chuẩn an toàn; file gốc không thay đổi và không có artifact tải xuống."
        : isPdfToWord && status === "guarded"
        ? "PDF không có text có thể trích xuất; Web không OCR hoặc tạo DOCX giả."
        : isPdfToImages && (status === "failed" || status === "unavailable")
        ? "Không có PNG/ZIP tải xuống; hãy kiểm tra PDF nguồn và chạy thao tác mới."
        : (status === "failed" || status === "unavailable" ? "Không có output tải xuống; hãy kiểm tra nguồn và chạy thao tác mới." : "Chỉ tải xuống sau khi server xác minh output.");
      const outputMetric = isPdfToWord
        ? (status === "completed" && downloadPath ? "DOCX đã xác minh" : "Chưa có")
        : isPdfToImages
        ? (status === "completed" && downloadPath ? (Number.isInteger(outputPages) && outputPages === 1 ? "PNG đã xác minh" : `${safeText(String(outputPages || 0))} PNG trong ZIP`) : "Chưa có")
        : (isOptimize ? safeText(item.byte_size ? vaultBytes(item.byte_size) : "Chưa có") : (Number.isInteger(outputPages) ? `${safeText(String(outputPages))} trang` : "Chưa có"));
      const artifactLabel = isPdfToWord ? "DOCX" : (isPdfToImages ? (Number.isInteger(outputPages) && outputPages === 1 ? "PNG" : "ZIP") : (isOptimize ? "Đã giảm" : "Artifact"));
      const downloadLabel = isPdfToWord ? "Tải DOCX riêng tư" : (isPdfToImages ? (Number.isInteger(outputPages) && outputPages === 1 ? "Tải PNG riêng tư" : "Tải ZIP riêng tư") : "Tải PDF riêng tư");
      const fallbackFilename = isPdfToWord ? "DOCX riêng tư" : (isPdfToImages ? "PNG / ZIP riêng tư" : "PDF riêng tư");
      return `<article class="portal-card portal-card-pad portal-document-operation-card" data-document-operation="${safeText(String(item.id))}"><div class="portal-card-header"><div class="portal-document-operation-title"><span class="portal-document-operation-icon" aria-hidden="true">${isPdfToWord ? "DOCX" : (isPdfToImages ? "PNG" : (isImageToPdf ? "ẢNH" : "PDF"))}</span><div><h2 class="portal-card-title">${safeText(String(item.original_filename || fallbackFilename))}</h2><p class="portal-card-subtitle">${safeText(selected)}</p></div></div>${badge(status)}</div><dl class="portal-document-operation-meta"><div><dt>Nguồn</dt><dd>${sourceMetric}</dd></div><div><dt>Đầu ra</dt><dd>${outputMetric}</dd></div><div><dt>${artifactLabel}</dt><dd>${thirdMetric}</dd></div><div><dt>Cập nhật</dt><dd>${safeText(String(item.completed_at || item.updated_at || item.created_at || "—"))}</dd></div></dl><div class="portal-form-footer">${downloadPath ? `<a class="portal-button portal-button--primary" href="${safeText(downloadPath)}" rel="noreferrer">${downloadLabel} <span aria-hidden="true">↓</span></a>` : `<span class="portal-form-note">${pendingMessage}</span>`}</div></article>`;
    }).join("")}</div>`;
  }

  function renderDocumentHub(page, context) {
    const privateReady = Boolean(context.capabilities && context.capabilities["document-operation-view"] === true);
    const cards = [
      { href: "/documents/pdf-to-images", icon: "PNG", title: "PDF sang ảnh", text: "Render toàn bộ trang PDF ở 2×. Một trang trả PNG, nhiều trang trả ZIP private đã kiểm tra.", ready: Boolean(context.pdfToImagesEnabled) },
      { href: "/documents/split", icon: "PDF", title: "Tách PDF", text: "Tạo một PDF mới từ một trang hoặc dải liên tiếp trong Asset Vault.", ready: true },
      { href: "/documents/merge", icon: "PDF", title: "Gộp PDF", text: "Gộp tối đa 8 PDF private theo đúng thứ tự đã chọn.", ready: true },
      { href: "/documents/compress", icon: "PDF", title: "Tối ưu PDF", text: "Chỉ phát một bản lossless khi kết quả nhỏ hơn đủ ý nghĩa.", ready: true },
      { href: "/documents/image-to-pdf", icon: "ẢNH", title: "Ảnh sang PDF", text: "Tạo PDF từ JPEG/PNG/WebP private theo thứ tự trang có chủ đích.", ready: Boolean(context.imageToPdfEnabled) },
      { href: "/documents/pdf-to-word", icon: "DOCX", title: "PDF có text → Word", text: "Trích xuất text có thể chọn thành DOCX; không OCR hoặc sao chép layout giả.", ready: Boolean(context.pdfToWordEnabled) }
    ];
    return `<article class="portal-page portal-document-hub">${renderHero(page, context)}
      <section class="portal-document-operation-intro"><div><span class="portal-section-kicker">Private Document Studio</span><h2>Công cụ PDF có output thật, không form generic</h2><p>Chọn workflow phù hợp cho PDF của bạn. Mỗi công cụ chỉ đọc Asset Vault của signed account, xử lý trong storage cô lập và chỉ cho tải attachment sau khi server xác minh dữ liệu đầu ra.</p></div><dl><div><dt>${safeText(String(cards.filter((item) => item.ready && privateReady).length))}</dt><dd>Tiện ích private sẵn sàng</dd></div><div><dt>0</dt><dd>Bot job / provider call</dd></div></dl></section>
      <section class="portal-module-grid">${cards.map((item) => `<a class="portal-module-card" href="${safeText(item.href)}"><div class="portal-module-icon" aria-hidden="true">${safeText(item.icon)}</div><div class="portal-module-copy"><div class="portal-module-heading"><h2>${safeText(item.title)}</h2>${badge(privateReady && item.ready ? "ready" : "guarded")}</div><p>${safeText(item.text)}</p><span class="portal-module-link">Mở workflow <b aria-hidden="true">→</b></span></div></a>`).join("")}</section>
      <section class="portal-card portal-card-pad"><div class="portal-notice portal-notice--info"><span class="portal-notice-icon" aria-hidden="true">i</span><div><strong>Biên giới dữ liệu rõ ràng</strong><p>Không có URL công khai, PWA cache, raw path browser, provider payload, Bot job, ví Xu, PayOS order hay webhook mới trong các tiện ích này. Nếu một runtime chưa bật, card giữ guarded thay vì tạo kết quả giả.</p></div></div>${renderNotes(page)}</section>
    </article>`;
  }

  function renderPdfSplit(page, context) {
    const canView = Boolean(context.capabilities && context.capabilities["document-operation-view"] === true);
    const canRunCapability = Boolean(context.capabilities && context.capabilities["document-operation-pdf-split"] === true);
    const canRefresh = Boolean(context.capabilities && context.capabilities["document-operation-refresh"] === true);
    if (!canView) {
      return `<article class="portal-page portal-pdf-split">${renderHero(page, context)}<section class="portal-card portal-card-pad"><div class="portal-state" data-state="guarded"><span class="portal-state-icon" aria-hidden="true">${safeText(ICONS.document)}</span><div><h2>Document Operations đang ở chế độ an toàn</h2><p>PDF Split chỉ bật khi cả Asset Vault và thư mục output cô lập, persistent của Web được server xác nhận. Không fallback sang static, browser storage, Bot job hoặc provider.</p><div class="portal-state-meta"><span>Signed session</span><span>Storage riêng</span><span>Không có output giả</span></div></div></div></section></article>`;
    }
    const sources = pdfVaultItems(context);
    const operations = documentOperationItems(context, "pdf_split");
    const canRun = canRunCapability && sources.length > 0;
    const formValues = transientFormValues("/documents/split");
    const runReason = !canRunCapability
      ? "Cần signed session, CSRF và capability Document Operations từ server."
      : sources.length === 0
        ? "Hãy lưu một PDF private vào Asset Vault trước khi tách."
        : "Source → bản sao cô lập → xác minh parser/output → attachment riêng tư.";
    const sourceSummary = sources.length === 1 ? "1 PDF đang hoạt động" : `${sources.length} PDF đang hoạt động`;
    const completedCount = operations.filter((item) => documentOperationState(item) === "completed" && item.download_ready === true).length;
    return `<article class="portal-page portal-pdf-split">${renderHero(page, context)}
      <section class="portal-document-operation-intro"><div><span class="portal-section-kicker">Web-native Document Operations</span><h2>Tách PDF riêng tư, không qua Bot</h2><p>Chọn PDF đã có trong Asset Vault. Máy chủ sao chép input sang vùng xử lý cô lập, giới hạn parser theo 20 MB/30 trang, loại bỏ annotation/action tương tác và chỉ phát attachment khi output vượt qua kiểm tra.</p></div><dl><div><dt>${safeText(sourceSummary)}</dt><dd>Nguồn thuộc account hiện tại</dd></div><div><dt>${safeText(String(completedCount))}</dt><dd>PDF output sẵn sàng tải</dd></div></dl></section>
      <div class="portal-document-operation-layout"><section class="portal-card portal-card-pad portal-document-operation-form"><div class="portal-card-header"><div><h2 class="portal-card-title">Tạo PDF Split</h2><p class="portal-card-subtitle">Một trang hoặc một dải liên tiếp. Browser không upload bytes hoặc gửi raw file path cho thao tác này.</p></div>${badge(canRun ? "ready" : "guarded")}</div><form class="portal-form" data-portal-form data-portal-action="document-operation-pdf-split" data-portal-route="/documents/split" data-portal-confirm="Tách PDF từ Asset Vault? Web sẽ tạo một attachment riêng tư mới sau khi kiểm tra input và output." novalidate>${renderFields(pdfSplitFormFields(), canRun, context, formValues)}<div class="portal-form-footer"><span class="portal-form-note">${safeText(runReason)}</span><button class="portal-button portal-button--primary" type="submit"${canRun ? "" : " disabled"}>Tách PDF</button></div></form></section><aside class="portal-card portal-card-pad portal-document-operation-boundary"><div class="portal-card-header"><div><h2 class="portal-card-title">Ranh giới rõ ràng</h2><p class="portal-card-subtitle">Document Operations là pipeline Web độc lập.</p></div></div><ol class="portal-project-steps"><li><strong>1. Nguồn có ownership</strong><span>Chỉ asset PDF private đang active của signed account hiện tại được đọc.</span></li><li><strong>2. Xử lý có giới hạn</strong><span>Không PDF mã hóa, không quá 20 MB/30 trang, không page list tuỳ ý.</span></li><li><strong>3. Delivery riêng tư</strong><span>Output được hash/parse lại và tải qua signed session; không public URL hoặc PWA cache.</span></li></ol><div class="portal-form-footer"><a class="portal-button portal-button--quiet" href="/asset-vault">Mở Asset Vault</a></div></aside></div>
      <section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">PDF đã xử lý</h2><p class="portal-card-subtitle">Chỉ thao tác thuộc signed Web account hiện tại. Download không khả dụng nếu integrity hoặc ownership không còn hợp lệ.</p></div><button class="portal-button portal-button--quiet" type="button" data-portal-action="document-operation-refresh" data-portal-route="/documents/split"${canRefresh ? "" : " disabled"}>Làm mới</button></div>${renderDocumentOperationCards(operations)}</section>
      <section class="portal-card portal-card-pad"><div class="portal-notice portal-notice--info"><span class="portal-notice-icon" aria-hidden="true">i</span><div><strong>Không thay thế workflow Bot</strong><p>PDF Split này là artifact Web-native có lifecycle riêng. Nó không tạo Job Bot, gọi provider, trừ/cộng Xu, tạo PayOS order hoặc dùng webhook thanh toán.</p></div></div>${renderNotes(page)}</section>
    </article>`;
  }

  function renderPdfMerge(page, context) {
    const canView = Boolean(context.capabilities && context.capabilities["document-operation-view"] === true);
    const canRunCapability = Boolean(context.capabilities && context.capabilities["document-operation-pdf-merge"] === true);
    const canRefresh = Boolean(context.capabilities && context.capabilities["document-operation-refresh"] === true);
    if (!canView) {
      return `<article class="portal-page portal-pdf-merge">${renderHero(page, context)}<section class="portal-card portal-card-pad"><div class="portal-state" data-state="guarded"><span class="portal-state-icon" aria-hidden="true">${safeText(ICONS.document)}</span><div><h2>Document Operations đang ở chế độ an toàn</h2><p>PDF Merge chỉ bật khi cả Asset Vault và storage output cô lập, persistent của Web được server xác nhận. Không fallback sang static, browser storage, Bot job hoặc provider.</p><div class="portal-state-meta"><span>Signed session</span><span>Storage riêng</span><span>Không có output giả</span></div></div></div></section></article>`;
    }
    const sources = pdfVaultItems(context);
    const operations = documentOperationItems(context, "pdf_merge");
    const canRun = canRunCapability && sources.length >= 2;
    const formValues = transientFormValues("/documents/merge");
    const runReason = !canRunCapability
      ? "Cần signed session, CSRF và capability Document Operations từ server."
      : sources.length < 2
        ? "Hãy lưu ít nhất hai PDF private vào Asset Vault trước khi gộp."
        : "PDF 1 → PDF 8 xác định thứ tự trang; nguồn được sao chép cô lập trước khi parser xử lý.";
    const sourceSummary = sources.length === 1 ? "1 PDF đang hoạt động" : `${sources.length} PDF đang hoạt động`;
    const completedCount = operations.filter((item) => documentOperationState(item) === "completed" && item.download_ready === true).length;
    return `<article class="portal-page portal-pdf-merge">${renderHero(page, context)}
      <section class="portal-document-operation-intro"><div><span class="portal-section-kicker">Web-native Document Operations</span><h2>Gộp PDF riêng tư theo đúng thứ tự</h2><p>Chọn từ hai đến tám PDF đã có trong Asset Vault. Máy chủ kiểm tra ownership, sao chép từng nguồn vào vùng xử lý cô lập, giới hạn mỗi nguồn 20 MB, tổng 40 MB và 30 trang, sau đó loại bỏ annotation/action tương tác trước khi phát attachment riêng tư.</p></div><dl><div><dt>${safeText(sourceSummary)}</dt><dd>Nguồn thuộc account hiện tại</dd></div><div><dt>${safeText(String(completedCount))}</dt><dd>PDF Merge sẵn sàng tải</dd></div></dl></section>
      <div class="portal-document-operation-layout"><section class="portal-card portal-card-pad portal-document-operation-form"><div class="portal-card-header"><div><h2 class="portal-card-title">Chọn thứ tự PDF</h2><p class="portal-card-subtitle">PDF 1 xuất hiện trước, rồi tới PDF 2… Browser không upload bytes hoặc gửi raw file path cho thao tác này.</p></div>${badge(canRun ? "ready" : "guarded")}</div><form class="portal-form" data-portal-form data-portal-action="document-operation-pdf-merge" data-portal-route="/documents/merge" data-portal-confirm="Gộp PDF theo đúng thứ tự đã chọn? Web sẽ tạo một attachment riêng tư mới sau khi kiểm tra tất cả input và output." novalidate>${renderFields(pdfMergeFormFields(), canRun, context, formValues)}<div class="portal-form-footer"><span class="portal-form-note">${safeText(runReason)}</span><button class="portal-button portal-button--primary" type="submit"${canRun ? "" : " disabled"}>Gộp PDF riêng tư</button></div></form></section><aside class="portal-card portal-card-pad portal-document-operation-boundary"><div class="portal-card-header"><div><h2 class="portal-card-title">Ranh giới rõ ràng</h2><p class="portal-card-subtitle">Document Operations là pipeline Web độc lập.</p></div></div><ol class="portal-project-steps"><li><strong>1. Thứ tự có chủ đích</strong><span>Slot PDF 1 đến PDF 8 được giữ nguyên trong request fingerprint và output artifact.</span></li><li><strong>2. Xử lý có giới hạn</strong><span>Tối đa 8 nguồn, mỗi nguồn 20 MB, tổng 40 MB/30 trang; chặn PDF mã hóa và nguồn trùng.</span></li><li><strong>3. Delivery riêng tư</strong><span>Output được hash/parse lại và tải qua signed session; không public URL hoặc PWA cache.</span></li></ol><div class="portal-form-footer"><a class="portal-button portal-button--quiet" href="/asset-vault">Mở Asset Vault</a></div></aside></div>
      <section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">PDF đã gộp</h2><p class="portal-card-subtitle">Chỉ thao tác thuộc signed Web account hiện tại. Download không khả dụng nếu integrity hoặc ownership không còn hợp lệ.</p></div><button class="portal-button portal-button--quiet" type="button" data-portal-action="document-operation-refresh" data-portal-route="/documents/merge"${canRefresh ? "" : " disabled"}>Làm mới</button></div>${renderDocumentOperationCards(operations, "Chưa có PDF đã gộp", "PDF gộp chỉ xuất hiện sau khi mọi nguồn và output đều vượt qua kiểm tra server-side. Không có Job Bot hoặc output mô phỏng.")}</section>
      <section class="portal-card portal-card-pad"><div class="portal-notice portal-notice--info"><span class="portal-notice-icon" aria-hidden="true">i</span><div><strong>Không thay thế workflow Bot</strong><p>PDF Merge này là artifact Web-native có lifecycle riêng. Nó không tạo Job Bot, gọi provider, trừ/cộng Xu, tạo PayOS order hoặc dùng webhook thanh toán.</p></div></div>${renderNotes(page)}</section>
    </article>`;
  }

  function renderPdfOptimize(page, context) {
    const canView = Boolean(context.capabilities && context.capabilities["document-operation-view"] === true);
    const canRunCapability = Boolean(context.capabilities && context.capabilities["document-operation-pdf-optimize"] === true);
    const canRefresh = Boolean(context.capabilities && context.capabilities["document-operation-refresh"] === true);
    if (!canView) {
      return `<article class="portal-page portal-pdf-optimize">${renderHero(page, context)}<section class="portal-card portal-card-pad"><div class="portal-state" data-state="guarded"><span class="portal-state-icon" aria-hidden="true">${safeText(ICONS.document)}</span><div><h2>Document Operations đang ở chế độ an toàn</h2><p>PDF Optimize chỉ bật khi cả Asset Vault và storage output cô lập, persistent của Web được server xác nhận. Không fallback sang static, browser storage, Bot job hoặc provider.</p><div class="portal-state-meta"><span>Signed session</span><span>Storage riêng</span><span>Không có output giả</span></div></div></div></section></article>`;
    }
    const sources = pdfVaultItems(context);
    const operations = documentOperationItems(context, "pdf_optimize");
    const canRun = canRunCapability && sources.length > 0;
    const formValues = transientFormValues("/documents/compress");
    const runReason = !canRunCapability
      ? "Cần signed session, CSRF và capability Document Operations từ server."
      : sources.length === 0
        ? "Hãy lưu một PDF private vào Asset Vault trước khi tối ưu."
        : "Chỉ phát attachment khi bản đã kiểm tra thật sự giảm tối thiểu 1 KiB và 1%; nếu không file gốc vẫn nguyên vẹn.";
    const sourceSummary = sources.length === 1 ? "1 PDF đang hoạt động" : `${sources.length} PDF đang hoạt động`;
    const completedCount = operations.filter((item) => documentOperationState(item) === "completed" && item.download_ready === true).length;
    return `<article class="portal-page portal-pdf-optimize">${renderHero(page, context)}
      <section class="portal-document-operation-intro"><div><span class="portal-section-kicker">Web-native Document Operations</span><h2>Tối ưu PDF minh bạch, không hạ chất lượng hình ảnh</h2><p>Chọn PDF trong Asset Vault. Máy chủ sao chép input vào vùng xử lý cô lập, tối ưu content stream/cấu trúc, loại bỏ annotation/action tương tác, kiểm tra lại parser và hash. Nếu artifact cuối cùng không nhỏ hơn đủ ý nghĩa, Web không tạo download và không thay file gốc.</p></div><dl><div><dt>${safeText(sourceSummary)}</dt><dd>Nguồn thuộc account hiện tại</dd></div><div><dt>${safeText(String(completedCount))}</dt><dd>PDF tối ưu sẵn sàng tải</dd></div></dl></section>
      <div class="portal-document-operation-layout"><section class="portal-card portal-card-pad portal-document-operation-form"><div class="portal-card-header"><div><h2 class="portal-card-title">Tối ưu PDF không resample</h2><p class="portal-card-subtitle">Một profile duy nhất, có kiểm tra thật. Không có dropdown light/medium/strong không tác động engine.</p></div>${badge(canRun ? "ready" : "guarded")}</div><form class="portal-form" data-portal-form data-portal-action="document-operation-pdf-optimize" data-portal-route="/documents/compress" data-portal-confirm="Tối ưu PDF từ Asset Vault? File gốc không bị thay đổi; output chỉ được tạo nếu máy chủ xác minh bản mới nhỏ hơn đủ ý nghĩa." novalidate>${renderFields(pdfOptimizeFormFields(), canRun, context, formValues)}<div class="portal-form-footer"><span class="portal-form-note">${safeText(runReason)}</span><button class="portal-button portal-button--primary" type="submit"${canRun ? "" : " disabled"}>Tối ưu PDF</button></div></form></section><aside class="portal-card portal-card-pad portal-document-operation-boundary"><div class="portal-card-header"><div><h2 class="portal-card-title">Kết quả trung thực</h2><p class="portal-card-subtitle">Không resample ảnh hoặc tạo output giả; annotation/action tương tác được loại bỏ để delivery an toàn.</p></div></div><ol class="portal-project-steps"><li><strong>1. Nguồn có ownership</strong><span>Chỉ asset PDF private active của signed account hiện tại được sao chép/đọc.</span></li><li><strong>2. Tối ưu có giới hạn</strong><span>Tối đa 20 MB/30 trang; không PDF mã hóa, không chạy shell/command hoặc dịch vụ ngoài.</span></li><li><strong>3. Chỉ giao khi giảm thật</strong><span>Artifact phải strict-reparse, hash đúng và tiết kiệm tối thiểu 1 KiB cùng 1%; nếu không có output.</span></li></ol><div class="portal-form-footer"><a class="portal-button portal-button--quiet" href="/asset-vault">Mở Asset Vault</a></div></aside></div>
      <section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">PDF đã tối ưu</h2><p class="portal-card-subtitle">Dung lượng nguồn, output và mức giảm chỉ được server công bố sau completed. Trạng thái guarded nghĩa là không có bản nhỏ hơn đạt chuẩn — không phải một download bị ẩn.</p></div><button class="portal-button portal-button--quiet" type="button" data-portal-action="document-operation-refresh" data-portal-route="/documents/compress"${canRefresh ? "" : " disabled"}>Làm mới</button></div>${renderDocumentOperationCards(operations, "Chưa có PDF tối ưu", "Một output chỉ xuất hiện khi máy chủ xác minh bản lossless nhỏ hơn thật. File gốc trong Asset Vault luôn được giữ nguyên.")}</section>
      <section class="portal-card portal-card-pad"><div class="portal-notice portal-notice--info"><span class="portal-notice-icon" aria-hidden="true">i</span><div><strong>Không thay thế workflow Bot</strong><p>PDF Optimize này là artifact Web-native có lifecycle riêng. Nó không tạo Job Bot, gọi provider, trừ/cộng Xu, tạo PayOS order hoặc dùng webhook thanh toán.</p></div></div>${renderNotes(page)}</section>
    </article>`;
  }

  function renderPdfToImages(page, context) {
    const canView = Boolean(context.capabilities && context.capabilities["document-operation-view"] === true);
    const canRunCapability = Boolean(context.capabilities && context.capabilities["document-operation-pdf-to-images"] === true);
    const canRefresh = Boolean(context.capabilities && context.capabilities["document-operation-refresh"] === true);
    if (!canView) {
      return `<article class="portal-page portal-pdf-to-images">${renderHero(page, context)}<section class="portal-card portal-card-pad"><div class="portal-state" data-state="guarded"><span class="portal-state-icon" aria-hidden="true">${safeText(ICONS.document)}</span><div><h2>PDF → ảnh đang ở chế độ an toàn</h2><p>Tiện ích chỉ mở khi Asset Vault và storage output private persistent đã được server xác nhận. Web không fallback sang browser canvas, Bot job, provider hoặc output mô phỏng.</p><div class="portal-state-meta"><span>Signed session</span><span>Storage riêng</span><span>Không có output giả</span></div></div></div></section></article>`;
    }
    const sources = pdfVaultItems(context);
    const operations = documentOperationItems(context, "pdf_to_images");
    const canRun = canRunCapability && sources.length > 0;
    const formValues = transientFormValues("/documents/pdf-to-images");
    const runReason = !canRunCapability
      ? (context.pdfToImagesEnabled === true
        ? "Cần signed session, CSRF và capability PDF → ảnh từ server."
        : "PDF → ảnh đang tắt an toàn trên server; Web không fallback sang renderer browser, Bot hay provider.")
      : sources.length === 0
        ? "Hãy lưu một PDF private vào Asset Vault trước khi render."
        : "Server render 2×, kiểm tra lại từng PNG/ZIP và chỉ phát attachment private khi integrity hợp lệ.";
    const sourceSummary = sources.length === 1 ? "1 PDF đang hoạt động" : `${sources.length} PDF đang hoạt động`;
    const completedCount = operations.filter((item) => documentOperationState(item) === "completed" && item.download_ready === true).length;
    return `<article class="portal-page portal-pdf-to-images">${renderHero(page, context)}
      <section class="portal-document-operation-intro"><div><span class="portal-section-kicker">Web-native PDF renderer</span><h2>Render PDF thành ảnh riêng tư, không qua Telegram</h2><p>Chọn một PDF đã có trong Asset Vault. Máy chủ hash-copy source vào vùng cô lập, kiểm tra parser, render toàn bộ trang ở 2× như Bot rồi mở lại từng PNG. PDF một trang giao PNG; PDF nhiều trang giao ZIP với tên page_001.png, page_002.png… đã được xác minh lại.</p></div><dl><div><dt>${safeText(sourceSummary)}</dt><dd>Nguồn thuộc account hiện tại</dd></div><div><dt>${safeText(String(completedCount))}</dt><dd>PNG / ZIP sẵn sàng tải</dd></div></dl></section>
      <div class="portal-document-operation-layout"><section class="portal-card portal-card-pad portal-document-operation-form"><div class="portal-card-header"><div><h2 class="portal-card-title">Chọn PDF để render</h2><p class="portal-card-subtitle">Browser chỉ gửi Asset Vault ID private. Không upload bytes, URL hay raw file path vào renderer.</p></div>${badge(canRun ? "ready" : "guarded")}</div><form class="portal-form" data-portal-form data-portal-action="document-operation-pdf-to-images" data-portal-route="/documents/pdf-to-images" data-portal-confirm="Render toàn bộ PDF thành PNG riêng tư? Một trang trả PNG; nhiều trang trả ZIP sau khi server kiểm tra từng file." novalidate>${renderFields(pdfToImagesFormFields(), canRun, context, formValues)}<div class="portal-form-footer"><span class="portal-form-note">${safeText(runReason)}</span><button class="portal-button portal-button--primary" type="submit"${canRun ? "" : " disabled"}>Render PDF → ảnh</button></div></form></section><aside class="portal-card portal-card-pad portal-document-operation-boundary"><div class="portal-card-header"><div><h2 class="portal-card-title">Giới hạn có chủ đích</h2><p class="portal-card-subtitle">Kết quả bot-compatible, nhưng có hàng rào Web để tránh raster/ZIP amplification.</p></div></div><ol class="portal-project-steps"><li><strong>1. Nguồn có ownership</strong><span>Chỉ PDF active của signed account hiện tại được hash-copy và parse lại; PDF mã hóa hoặc không hợp lệ bị từ chối.</span></li><li><strong>2. Render 2× có giới hạn</strong><span>Tối đa 20 MB/30 trang, 8.192 px mỗi cạnh, 8 MP mỗi trang và 48 MP mỗi lần. Không có renderer browser hoặc provider fallback.</span></li><li><strong>3. Delivery riêng tư</strong><span>Mỗi PNG được decoder kiểm tra; ZIP nhiều trang có manifest tên/byte/hash chính xác. Attachment tải qua signed session, không public URL hoặc PWA cache.</span></li></ol><div class="portal-form-footer"><a class="portal-button portal-button--quiet" href="/asset-vault">Mở Asset Vault</a></div></aside></div>
      <section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Ảnh PDF đã render</h2><p class="portal-card-subtitle">Chỉ thao tác thuộc signed Web account hiện tại. Trạng thái failed/unavailable nghĩa là không có PNG hay ZIP bị ẩn hoặc thay thế bằng output giả.</p></div><button class="portal-button portal-button--quiet" type="button" data-portal-action="document-operation-refresh" data-portal-route="/documents/pdf-to-images"${canRefresh ? "" : " disabled"}>Làm mới</button></div>${renderDocumentOperationCards(operations, "Chưa có PDF đã render", "PNG hoặc ZIP chỉ xuất hiện sau khi PDF source, pixel budget và output private đều vượt qua kiểm tra server-side.")}</section>
      <section class="portal-card portal-card-pad"><div class="portal-notice portal-notice--info"><span class="portal-notice-icon" aria-hidden="true">i</span><div><strong>Tiện ích Web-native độc lập</strong><p>PDF → ảnh có lifecycle artifact riêng, không tạo Job Bot, gọi provider, trừ/cộng Xu, tạo PayOS order hoặc dùng webhook thanh toán.</p></div></div>${renderNotes(page)}</section>
    </article>`;
  }

  function renderPdfToWord(page, context) {
    const canView = Boolean(context.capabilities && context.capabilities["document-operation-view"] === true);
    const canRunCapability = Boolean(context.capabilities && context.capabilities["document-operation-pdf-to-word"] === true);
    const canRefresh = Boolean(context.capabilities && context.capabilities["document-operation-refresh"] === true);
    if (!canView) {
      return `<article class="portal-page portal-pdf-to-word">${renderHero(page, context)}<section class="portal-card portal-card-pad"><div class="portal-state" data-state="guarded"><span class="portal-state-icon" aria-hidden="true">${safeText(ICONS.document)}</span><div><h2>Document Operations đang ở chế độ an toàn</h2><p>PDF có text → Word chỉ bật khi cả Asset Vault và storage output cô lập, persistent của Web được server xác nhận. Không fallback sang static, browser storage, Bot job hoặc provider.</p><div class="portal-state-meta"><span>Signed session</span><span>Storage riêng</span><span>Không OCR giả</span></div></div></div></section></article>`;
    }
    const sources = pdfVaultItems(context);
    const operations = documentOperationItems(context, "pdf_to_word_text");
    const canRun = canRunCapability && sources.length > 0;
    const formValues = transientFormValues("/documents/pdf-to-word");
    const runReason = !canRunCapability
      ? (context.pdfToWordEnabled === true
        ? "Cần signed session, CSRF và capability PDF có text → Word từ server."
        : "PDF có text → Word đang tắt an toàn trên server; Web không fallback sang OCR hoặc DOCX mô phỏng.")
      : sources.length === 0
        ? "Hãy lưu một PDF private có text có thể chọn vào Asset Vault trước khi trích xuất."
        : "Server chỉ tạo DOCX sau khi parser đọc được text thực và xác minh output private.";
    const sourceSummary = sources.length === 1 ? "1 PDF đang hoạt động" : `${sources.length} PDF đang hoạt động`;
    const completedCount = operations.filter((item) => documentOperationState(item) === "completed" && item.download_ready === true).length;
    return `<article class="portal-page portal-pdf-to-word">${renderHero(page, context)}
      <section class="portal-document-operation-intro"><div><span class="portal-section-kicker">Web-native Document Operations</span><h2>Trích xuất text PDF thành DOCX riêng tư</h2><p>Chọn PDF đã có trong Asset Vault. Server chỉ lấy văn bản mà parser PDF thực sự đọc được, rồi tạo DOCX mới trong storage cô lập. Đây không phải OCR và không sao chép ảnh, font, bảng hay bố cục trực quan từ PDF sang Word.</p></div><dl><div><dt>${safeText(sourceSummary)}</dt><dd>Nguồn thuộc account hiện tại</dd></div><div><dt>${safeText(String(completedCount))}</dt><dd>DOCX sẵn sàng tải</dd></div></dl></section>
      <div class="portal-document-operation-layout"><section class="portal-card portal-card-pad portal-document-operation-form"><div class="portal-card-header"><div><h2 class="portal-card-title">Chọn PDF có text</h2><p class="portal-card-subtitle">Browser chỉ gửi ID asset private đã chọn; không upload bytes, URL hoặc raw file path cho thao tác này.</p></div>${badge(canRun ? "ready" : "guarded")}</div><form class="portal-form" data-portal-form data-portal-action="document-operation-pdf-to-word" data-portal-route="/documents/pdf-to-word" data-portal-confirm="Trích xuất text thực từ PDF sang DOCX riêng tư? PDF scan hoặc không có text sẽ không tạo output giả." novalidate>${renderFields(pdfToWordFormFields(), canRun, context, formValues)}<div class="portal-form-footer"><span class="portal-form-note">${safeText(runReason)}</span><button class="portal-button portal-button--primary" type="submit"${canRun ? "" : " disabled"}>Tạo DOCX riêng tư</button></div></form></section><aside class="portal-card portal-card-pad portal-document-operation-boundary"><div class="portal-card-header"><div><h2 class="portal-card-title">Giới hạn trung thực</h2><p class="portal-card-subtitle">Chỉ delivery khi có text có thể trích xuất và DOCX được server xác minh.</p></div></div><ol class="portal-project-steps"><li><strong>1. Nguồn có ownership</strong><span>Chỉ asset PDF private active của signed account hiện tại được sao chép/đọc trong vùng xử lý cô lập.</span></li><li><strong>2. Không OCR, không sao chép layout</strong><span>PDF scan hoặc rỗng text được ghi guarded, không có DOCX giả. Bố cục, ảnh, font, bảng và khả năng khớp thị giác không được cam kết.</span></li><li><strong>3. Delivery riêng tư</strong><span>DOCX mới được kiểm tra trước khi tải qua signed session; không public URL hoặc PWA cache.</span></li></ol><div class="portal-form-footer"><a class="portal-button portal-button--quiet" href="/asset-vault">Mở Asset Vault</a></div></aside></div>
      <section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">DOCX đã trích xuất</h2><p class="portal-card-subtitle">Chỉ thao tác thuộc signed Web account hiện tại. Trạng thái guarded nghĩa là PDF không có text parser đọc được — không có download bị ẩn hoặc output thay thế.</p></div><button class="portal-button portal-button--quiet" type="button" data-portal-action="document-operation-refresh" data-portal-route="/documents/pdf-to-word"${canRefresh ? "" : " disabled"}>Làm mới</button></div>${renderDocumentOperationCards(operations, "Chưa có DOCX đã trích xuất", "DOCX chỉ xuất hiện sau khi server đọc được text thực từ PDF và xác minh output private. PDF scan/rỗng text sẽ không sinh file giả.")}</section>
      <section class="portal-card portal-card-pad"><div class="portal-notice portal-notice--info"><span class="portal-notice-icon" aria-hidden="true">i</span><div><strong>Tiện ích Web-native độc lập</strong><p>Artifact DOCX có lifecycle private riêng; thao tác này không tạo Job Bot, gọi provider, trừ/cộng Xu, tạo PayOS order hoặc dùng webhook thanh toán.</p></div></div>${renderNotes(page)}</section>
    </article>`;
  }

  function renderImageToPdf(page, context) {
    const canView = Boolean(context.capabilities && context.capabilities["document-operation-view"] === true);
    const canRunCapability = Boolean(context.capabilities && context.capabilities["document-operation-image-to-pdf"] === true);
    const canRefresh = Boolean(context.capabilities && context.capabilities["document-operation-refresh"] === true);
    if (!canView) {
      return `<article class="portal-page portal-image-to-pdf">${renderHero(page, context)}<section class="portal-card portal-card-pad"><div class="portal-state" data-state="guarded"><span class="portal-state-icon" aria-hidden="true">${safeText(ICONS.document)}</span><div><h2>Document Operations đang ở chế độ an toàn</h2><p>Ảnh sang PDF chỉ bật khi Asset Vault và storage output cô lập, persistent của Web được server xác nhận. Không fallback sang static, browser storage, Bot job hoặc provider.</p><div class="portal-state-meta"><span>Signed session</span><span>Storage riêng</span><span>Không có output giả</span></div></div></div></section></article>`;
    }
    const sources = imageVaultItems(context);
    const operations = documentOperationItems(context, "image_to_pdf");
    const canRun = canRunCapability && sources.length > 0;
    const formValues = transientFormValues("/documents/image-to-pdf");
    const runReason = !canRunCapability
      ? (context.imageToPdfEnabled === true
        ? "Cần signed session, CSRF và capability Image → PDF từ server."
        : "Ảnh → PDF đang được server giữ guarded cho đến khi Pillow và private storage được bật có chủ đích.")
      : sources.length === 0
        ? "Hãy lưu ít nhất một JPEG, PNG hoặc WebP private vào Asset Vault trước khi tạo PDF."
        : "Ảnh 1 → Ảnh 8 là thứ tự trang; máy chủ decode thật, kiểm tra pixel và chỉ phát attachment sau strict re-parse/hash.";
    const sourceSummary = sources.length === 1 ? "1 ảnh đang hoạt động" : `${sources.length} ảnh đang hoạt động`;
    const completedCount = operations.filter((item) => documentOperationState(item) === "completed" && item.download_ready === true).length;
    return `<article class="portal-page portal-image-to-pdf">${renderHero(page, context)}
      <section class="portal-document-operation-intro"><div><span class="portal-section-kicker">Web-native Document Operations</span><h2>Biến ảnh riêng tư thành PDF có kiểm tra thật</h2><p>Chọn JPEG, PNG hoặc WebP đã có trong Asset Vault. Server kiểm tra ownership, hash-copy từng nguồn vào vùng cô lập, từ chối ảnh lỗi/ảnh động/decompression-bomb, chuẩn hóa orientation và nền trắng rồi tạo PDF một trang cho mỗi ảnh. Output chỉ được phát sau khi parser và hash xác minh lại.</p></div><dl><div><dt>${safeText(sourceSummary)}</dt><dd>Nguồn thuộc account hiện tại</dd></div><div><dt>${safeText(String(completedCount))}</dt><dd>PDF ảnh sẵn sàng tải</dd></div></dl></section>
      <div class="portal-document-operation-layout"><section class="portal-card portal-card-pad portal-document-operation-form"><div class="portal-card-header"><div><h2 class="portal-card-title">Chọn thứ tự ảnh</h2><p class="portal-card-subtitle">Ảnh 1 trở thành trang 1, rồi tới Ảnh 2… Browser không upload bytes hoặc gửi raw file path cho thao tác này.</p></div>${badge(canRun ? "ready" : "guarded")}</div><form class="portal-form" data-portal-form data-portal-action="document-operation-image-to-pdf" data-portal-route="/documents/image-to-pdf" data-portal-confirm="Tạo PDF từ ảnh theo đúng thứ tự đã chọn? Web sẽ tạo một attachment riêng tư mới sau khi kiểm tra mọi input và output." novalidate>${renderFields(imageToPdfFormFields(), canRun, context, formValues)}<div class="portal-form-footer"><span class="portal-form-note">${safeText(runReason)}</span><button class="portal-button portal-button--primary" type="submit"${canRun ? "" : " disabled"}>Tạo PDF riêng tư</button></div></form></section><aside class="portal-card portal-card-pad portal-document-operation-boundary"><div class="portal-card-header"><div><h2 class="portal-card-title">Web-native, có kiểm soát</h2><p class="portal-card-subtitle">Tiện ích tạo PDF riêng tư với output được xác minh trước khi phát hành.</p></div></div><ol class="portal-project-steps"><li><strong>1. Thứ tự có chủ đích</strong><span>Slot Ảnh 1 đến Ảnh 8 được giữ trong request fingerprint và trở thành thứ tự trang PDF.</span></li><li><strong>2. Decode có giới hạn</strong><span>JPEG/PNG/WebP tĩnh, tối đa 20 MB mỗi ảnh, 40 MB tổng, 7.680 px mỗi cạnh, tỷ lệ 12:1, 16 MP mỗi ảnh và 32 MP mỗi lần; chặn nguồn trùng hoặc ảnh động.</span></li><li><strong>3. Delivery riêng tư</strong><span>Output được strict-reparse, hash lại và tải qua signed session; không có public URL hoặc PWA cache.</span></li></ol><div class="portal-form-footer"><a class="portal-button portal-button--quiet" href="/asset-vault">Mở Asset Vault</a></div></aside></div>
      <section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">PDF đã tạo từ ảnh</h2><p class="portal-card-subtitle">Chỉ thao tác thuộc signed Web account hiện tại. Download không khả dụng nếu integrity hoặc ownership không còn hợp lệ.</p></div><button class="portal-button portal-button--quiet" type="button" data-portal-action="document-operation-refresh" data-portal-route="/documents/image-to-pdf"${canRefresh ? "" : " disabled"}>Làm mới</button></div>${renderDocumentOperationCards(operations, "Chưa có PDF từ ảnh", "PDF chỉ xuất hiện sau khi mọi ảnh nguồn và output đều vượt qua kiểm tra server-side. Không có output mô phỏng.")}</section>
      <section class="portal-card portal-card-pad"><div class="portal-notice portal-notice--info"><span class="portal-notice-icon" aria-hidden="true">i</span><div><strong>Tiện ích Web-native độc lập</strong><p>Artifact có lifecycle private riêng; thao tác này không thay đổi ví, thanh toán, provider hoặc webhook.</p></div></div>${renderNotes(page)}</section>
    </article>`;
  }

  function renderImageResize(page, context) {
    const canViewCapability = Boolean(context.capabilities && context.capabilities["image-operation-view"] === true);
    const canRunCapability = Boolean(context.capabilities && context.capabilities["image-operation-resize"] === true);
    const canRefresh = Boolean(context.capabilities && context.capabilities["image-operation-refresh"] === true);
    if (!canViewCapability) {
      return `<article class="portal-page portal-image-resize">${renderHero(page, context)}<section class="portal-card portal-card-pad"><div class="portal-state" data-state="guarded"><span class="portal-state-icon" aria-hidden="true">${safeText(ICONS.image)}</span><div><h2>Resize & Aspect Studio đang ở chế độ an toàn</h2><p>Tiện ích chỉ bật khi Asset Vault, private output storage và runtime Pillow được server xác nhận. Web không fallback sang browser canvas, Bot job, provider hoặc output giả.</p><div class="portal-state-meta"><span>Signed session</span><span>Storage riêng</span><span>Không AI giả</span></div></div></div></section></article>`;
    }
    const assetReadState = String(context.assetVaultReadState || "loading");
    const operationReadState = String(context.imageOperationsReadState || "loading");
    const privateReadsReady = assetReadState === "ready" && operationReadState === "ready";
    if (!privateReadsReady) {
      const loading = assetReadState === "loading" || operationReadState === "loading";
      const title = loading ? "Đang xác minh dữ liệu private" : "Chưa thể tải trạng thái private";
      const message = loading
        ? "Resize Studio đang tải Asset Vault và lịch sử thuộc signed Web account hiện tại. Form chỉ mở sau khi cả hai phản hồi server-side hoàn tất."
        : "Asset Vault hoặc lịch sử Resize Studio chưa trả dữ liệu an toàn. Web đã xóa projection cũ, không hiển thị form, output hay dữ liệu thay thế.";
      const retry = !loading && canRefresh
        ? `<div class="portal-form-footer"><button class="portal-button portal-button--primary" type="button" data-portal-action="image-operation-refresh" data-portal-route="/image/resize">Thử lại dữ liệu private</button></div>`
        : "";
      return `<article class="portal-page portal-image-resize">${renderHero(page, context)}<section class="portal-card portal-card-pad"><div class="portal-state" data-state="${loading ? "processing" : "guarded"}"><span class="portal-state-icon" aria-hidden="true">${loading ? "◌" : "!"}</span><div><h2>${safeText(title)}</h2><p>${safeText(message)}</p><div class="portal-state-meta"><span>Signed session</span><span>Không cache private</span><span>Không fallback browser</span></div>${retry}</div></div></section></article>`;
    }
    const sources = imageVaultItems(context);
    const operations = imageOperationItems(context);
    const canRun = canRunCapability && sources.length > 0;
    const formValues = transientFormValues("/image/resize");
    const runReason = !canRunCapability
      ? (context.imageResizeEnabled === true
        ? "Cần signed session, CSRF và capability Resize Studio từ server."
        : "Resize Studio đang được server giữ guarded cho đến khi private storage và WEBAPP_IMAGE_RESIZE_ENABLED được bật có chủ đích.")
      : sources.length === 0
        ? "Hãy lưu JPEG, PNG hoặc WebP private vào Asset Vault trước khi tạo bản sao."
        : "Nguồn → hash-copy cô lập → decode có giới hạn → PNG được mở lại và xác minh trước khi tải.";
    const sourceSummary = sources.length === 1 ? "1 ảnh đang hoạt động" : `${sources.length} ảnh đang hoạt động`;
    const completedCount = operations.filter((item) => imageOperationState(item) === "completed" && item.download_ready === true).length;
    return `<article class="portal-page portal-image-resize">${renderHero(page, context)}
      <section class="portal-document-operation-intro"><div><span class="portal-section-kicker">Web-native Image Operations</span><h2>Đổi canvas ảnh rõ ràng, không tạo ảnh AI</h2><p>Chọn ảnh private trong Asset Vault rồi tạo PNG mới theo crop giữa khung, pad nền trắng hoặc blur nền. Server giữ nguyên file gốc, sửa orientation, loại metadata nguồn, giới hạn decoder và chỉ phát bản sao sau khi tự mở lại, kiểm tra kích thước và hash integrity.</p></div><dl><div><dt>${safeText(sourceSummary)}</dt><dd>Nguồn thuộc account hiện tại</dd></div><div><dt>${safeText(String(completedCount))}</dt><dd>PNG sẵn sàng tải</dd></div></dl></section>
      <div class="portal-document-operation-layout"><section class="portal-card portal-card-pad portal-document-operation-form"><div class="portal-card-header"><div><h2 class="portal-card-title">Tạo canvas mới</h2><p class="portal-card-subtitle">Không upload bytes, URL hoặc raw file path ở bước này. Browser chỉ gửi Asset Vault ID và cấu hình canvas đã chọn.</p></div>${badge(canRun ? "ready" : "guarded")}</div><form class="portal-form" data-portal-form data-portal-action="image-operation-resize" data-portal-route="/image/resize" data-portal-confirm="Tạo một PNG private mới theo canvas và cách đặt ảnh đã chọn? File gốc trong Asset Vault sẽ không bị thay đổi." novalidate>${renderFields(imageResizeFormFields(), canRun, context, formValues)}<div class="portal-form-footer"><span class="portal-form-note">${safeText(runReason)}</span><button class="portal-button portal-button--primary" type="submit"${canRun ? "" : " disabled"}>Tạo PNG riêng tư</button></div></form></section><aside class="portal-card portal-card-pad portal-document-operation-boundary"><div class="portal-card-header"><div><h2 class="portal-card-title">Cách khung hoạt động</h2><p class="portal-card-subtitle">Canvas là thông số deterministic, không phải promise AI.</p></div></div><ol class="portal-project-steps"><li><strong>1. Crop giữa khung</strong><span>Lấp đầy canvas theo tỉ lệ và cắt phần rìa từ tâm. Không có focal-point hoặc nhận diện chủ thể.</span></li><li><strong>2. Pad nền trắng</strong><span>Giữ trọn ảnh, đặt giữa canvas trắng; alpha/metadata nguồn không đi sang PNG mới.</span></li><li><strong>3. Blur nền</strong><span>Giữ trọn ảnh ở giữa trên nền cover được làm mờ. Đây là hiệu ứng cục bộ, không retouch hay AI upscale.</span></li></ol><div class="portal-form-footer"><a class="portal-button portal-button--quiet" href="/asset-vault">Mở Asset Vault</a></div></aside></div>
      <section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">PNG đã tạo</h2><p class="portal-card-subtitle">Chỉ thao tác thuộc signed Web account hiện tại. Không có preview công khai; download bị khóa nếu ownership hoặc integrity không còn hợp lệ.</p></div><button class="portal-button portal-button--quiet" type="button" data-portal-action="image-operation-refresh" data-portal-route="/image/resize"${canRefresh ? "" : " disabled"}>Làm mới</button></div>${renderImageOperationCards(operations)}</section>
      <section class="portal-card portal-card-pad"><div class="portal-notice portal-notice--info"><span class="portal-notice-icon" aria-hidden="true">i</span><div><strong>Tiện ích Web-native độc lập</strong><p>Resize & Aspect Studio không tạo Bot job, không gọi provider, không trừ/cộng Xu, không tạo PayOS order và không dùng webhook thanh toán. AI Upscale vẫn là workflow riêng, chỉ hiển thị readiness canonical.</p></div></div>${renderNotes(page)}</section>
    </article>`;
  }

  function renderImageEnhance(page, context) {
    const canViewCapability = Boolean(context.capabilities && context.capabilities["image-operation-view"] === true);
    const canRunCapability = Boolean(context.capabilities && context.capabilities["image-operation-enhance"] === true);
    const canRefresh = Boolean(context.capabilities && context.capabilities["image-enhance-refresh"] === true);
    if (!canViewCapability) {
      return `<article class="portal-page portal-image-enhance">${renderHero(page, context)}<section class="portal-card portal-card-pad"><div class="portal-state" data-state="guarded"><span class="portal-state-icon" aria-hidden="true">${safeText(ICONS.image)}</span><div><h2>Image Enhance Studio đang ở chế độ an toàn</h2><p>Tiện ích chỉ mở khi Asset Vault và storage output private của Web được server xác nhận. Web không fallback sang canvas trình duyệt, Bot job, provider hay output giả.</p><div class="portal-state-meta"><span>Signed session</span><span>Storage riêng</span><span>Không AI giả</span></div></div></div></section></article>`;
    }
    const assetReadState = String(context.assetVaultReadState || "loading");
    const operationReadState = String(context.imageEnhanceOperationsReadState || "loading");
    const privateReadsReady = assetReadState === "ready" && operationReadState === "ready";
    if (!privateReadsReady) {
      const loading = assetReadState === "loading" || operationReadState === "loading";
      const title = loading ? "Đang xác minh dữ liệu private" : "Chưa thể tải trạng thái private";
      const message = loading
        ? "Image Enhance Studio đang tải Asset Vault và lịch sử thuộc signed Web account hiện tại. Form chỉ mở sau khi cả hai phản hồi server-side hoàn tất."
        : "Asset Vault hoặc lịch sử Image Enhance chưa trả dữ liệu an toàn. Web đã xóa projection cũ, không hiển thị form, output hay dữ liệu thay thế.";
      const retry = !loading && canRefresh
        ? `<div class="portal-form-footer"><button class="portal-button portal-button--primary" type="button" data-portal-action="image-enhance-refresh" data-portal-route="/image/edit">Thử lại dữ liệu private</button></div>`
        : "";
      return `<article class="portal-page portal-image-enhance">${renderHero(page, context)}<section class="portal-card portal-card-pad"><div class="portal-state" data-state="${loading ? "processing" : "guarded"}"><span class="portal-state-icon" aria-hidden="true">${loading ? "◌" : "!"}</span><div><h2>${safeText(title)}</h2><p>${safeText(message)}</p><div class="portal-state-meta"><span>Signed session</span><span>Không cache private</span><span>Không fallback browser</span></div>${retry}</div></div></section></article>`;
    }
    const sources = imageVaultItems(context);
    const operations = imageEnhanceOperationItems(context);
    const canRun = canRunCapability && sources.length > 0;
    const formValues = transientFormValues("/image/edit");
    const runReason = !canRunCapability
      ? (context.imageEnhanceEnabled === true
        ? "Cần signed session, CSRF và capability Image Enhance Studio từ server."
        : "Image Enhance Studio đang được server giữ guarded cho đến khi WEBAPP_IMAGE_ENHANCE_ENABLED được bật có chủ đích.")
      : sources.length === 0
        ? "Hãy lưu JPEG, PNG hoặc WebP private vào Asset Vault trước khi tạo bản sao."
        : "Nguồn → hash-copy cô lập → chỉnh màu/làm nét deterministic → PNG được mở lại và xác minh trước khi tải.";
    const sourceSummary = sources.length === 1 ? "1 ảnh đang hoạt động" : `${sources.length} ảnh đang hoạt động`;
    const completedCount = operations.filter((item) => imageOperationState(item) === "completed" && item.download_ready === true).length;
    return `<article class="portal-page portal-image-enhance">${renderHero(page, context)}
      <section class="portal-document-operation-intro"><div><span class="portal-section-kicker">Web-native Image Operations</span><h2>Làm ảnh sạch, rõ và nhất quán — không hứa hẹn AI</h2><p>Chọn ảnh private trong Asset Vault rồi áp một preset màu/làm nét cục bộ hoặc nhập đủ bốn thông số tùy chỉnh. Server giữ nguyên file gốc, chuẩn hóa orientation, làm phẳng alpha nền trắng, loại metadata nguồn và chỉ phát PNG mới sau khi tự mở lại, kiểm tra kích thước và hash integrity.</p></div><dl><div><dt>${safeText(sourceSummary)}</dt><dd>Nguồn thuộc account hiện tại</dd></div><div><dt>${safeText(String(completedCount))}</dt><dd>PNG sẵn sàng tải</dd></div></dl></section>
      <div class="portal-document-operation-layout"><section class="portal-card portal-card-pad portal-document-operation-form"><div class="portal-card-header"><div><h2 class="portal-card-title">Tạo bản sao đã chỉnh</h2><p class="portal-card-subtitle">Browser chỉ gửi Asset Vault ID và thông số đã giới hạn. Không upload bytes, URL hoặc raw file path cho thao tác này.</p></div>${badge(canRun ? "ready" : "guarded")}</div><form class="portal-form" data-portal-form data-portal-action="image-operation-enhance" data-portal-route="/image/edit" data-portal-confirm="Tạo một PNG private mới theo preset hoặc thông số cục bộ đã chọn? File gốc trong Asset Vault sẽ không bị thay đổi." novalidate>${renderFields(imageEnhanceFormFields(formValues), canRun, context, formValues)}<div class="portal-form-footer"><span class="portal-form-note">${safeText(runReason)}</span><button class="portal-button portal-button--primary" type="submit"${canRun ? "" : " disabled"}>Tạo PNG riêng tư</button></div></form></section><aside class="portal-card portal-card-pad portal-document-operation-boundary"><div class="portal-card-header"><div><h2 class="portal-card-title">Giới hạn trung thực</h2><p class="portal-card-subtitle">Preset là công thức local deterministic, không phải lời hứa retouch AI.</p></div></div><ol class="portal-project-steps"><li><strong>1. Thứ tự có thể kiểm tra</strong><span>Auto-contrast → sáng → tương phản → bão hòa → nét → tone, cùng thứ tự local editor của Bot tham chiếu.</span></li><li><strong>2. Upscale cơ bản có trần</strong><span>Nếu bật, server chỉ dùng LANCZOS + UnsharpMask tối đa 2× và luôn giữ trần 4096 px/16 MP. Không tạo chi tiết mới.</span></li><li><strong>3. Delivery riêng tư</strong><span>PNG mới được strict-reparse, hash lại và tải qua signed session; không có public URL, preview công khai hay PWA cache.</span></li></ol><div class="portal-form-footer"><a class="portal-button portal-button--quiet" href="/asset-vault">Mở Asset Vault</a></div></aside></div>
      <section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">PNG đã chỉnh</h2><p class="portal-card-subtitle">Chỉ thao tác thuộc signed Web account hiện tại. Download bị khóa nếu ownership hoặc integrity không còn hợp lệ.</p></div><button class="portal-button portal-button--quiet" type="button" data-portal-action="image-enhance-refresh" data-portal-route="/image/edit"${canRefresh ? "" : " disabled"}>Làm mới</button></div>${renderImageEnhanceOperationCards(operations)}</section>
      <section class="portal-card portal-card-pad"><div class="portal-notice portal-notice--info"><span class="portal-notice-icon" aria-hidden="true">i</span><div><strong>Tiện ích Web-native độc lập</strong><p>Image Enhance Studio không tạo Bot job, không gọi provider, không trừ/cộng Xu, không tạo PayOS order và không dùng webhook thanh toán. AI edit, remove background và AI upscale vẫn là workflow riêng, chỉ hiển thị readiness canonical.</p></div></div>${renderNotes(page)}</section>
    </article>`;
  }

  function renderAssetVault(page, context) {
    const canView = Boolean(context.capabilities && context.capabilities["asset-vault-view"] === true);
    const canUpload = Boolean(context.capabilities && context.capabilities["asset-vault-upload"] === true);
    const canArchive = Boolean(context.capabilities && context.capabilities["asset-vault-archive"] === true);
    const canRefresh = Boolean(context.capabilities && context.capabilities["asset-vault-refresh"] === true);
    if (!canView) {
      return `<article class="portal-page portal-asset-vault">${renderHero(page, context)}<section class="portal-card portal-card-pad"><div class="portal-state" data-state="guarded"><span class="portal-state-icon" aria-hidden="true">${safeText(ICONS.assets)}</span><div><h2>Asset Vault đang ở chế độ an toàn</h2><p>Kho tệp Web chỉ hoạt động khi môi trường có persistent volume riêng. Không có fallback sang static, browser storage hoặc Tài sản Bot.</p><div class="portal-state-meta"><span>Cần signed session</span><span>Không dùng storage công khai</span><span>Không có output giả</span></div></div></div></section></article>`;
    }
    const items = vaultItems(context);
    const projectNames = new Map((Array.isArray(context.projects) ? context.projects : [])
      .filter((project) => project && validProjectId(project.id))
      .map((project) => [String(project.id), String(project.title || "Project Web")]));
    const formValues = transientFormValues("/asset-vault");
    const cards = items.length
      ? `<div class="portal-vault-grid">${items.map((item) => {
          const id = String(item.id);
          const downloadPath = vaultDownloadPath(item);
          const projectName = item.project_id ? (projectNames.get(String(item.project_id)) || "Project đã liên kết") : "Không gắn Project";
          return `<article class="portal-card portal-card-pad portal-vault-card" data-vault-asset="${safeText(id)}"><div class="portal-card-header"><div class="portal-vault-card-title"><span class="portal-vault-file-icon" aria-hidden="true">${safeText(String(item.extension || "FILE").replace(".", "").slice(0, 5).toUpperCase())}</span><div><h2 class="portal-card-title">${safeText(String(item.display_name || "Tệp Web"))}</h2><p class="portal-card-subtitle">${safeText(String(item.original_filename || "Tệp riêng tư"))}</p></div></div>${badge("ready")}</div><dl class="portal-vault-meta"><div><dt>Dung lượng</dt><dd>${safeText(vaultBytes(item.byte_size))}</dd></div><div><dt>Project</dt><dd>${safeText(projectName)}</dd></div><div><dt>Cập nhật</dt><dd>${safeText(String(item.updated_at || item.created_at || "—"))}</dd></div></dl><div class="portal-form-footer"><a class="portal-button portal-button--primary" href="${safeText(downloadPath)}" rel="noreferrer">Tải tệp <span aria-hidden="true">↓</span></a><button class="portal-button portal-button--quiet" type="button" data-portal-action="asset-vault-archive" data-portal-route="/asset-vault" data-vault-asset-id="${safeText(id)}" data-portal-confirm="Lưu trữ tệp này khỏi Asset Vault đang hoạt động? Tệp vẫn được giữ riêng tư nhưng sẽ không thể tải từ danh sách active."${canArchive ? "" : " disabled"}>Lưu trữ</button></div></article>`;
        }).join("")}</div>`
      : renderEmpty("Asset Vault chưa có tệp", "Tải tệp đầu tiên để lưu cùng Project Web. Đây không phải asset delivery hay output của job Bot.", "▣");
    const fileDisabled = canUpload ? "" : " disabled";
    return `<article class="portal-page portal-asset-vault">${renderHero(page, context)}<section class="portal-vault-intro"><div><span class="portal-section-kicker">Private Web storage</span><h2>Kho tệp riêng cho Project và workflow Web</h2><p>Asset Vault dùng signed session, owner check, CSRF và private storage. Không tạo public link, preview giả, job, Xu hay PayOS.</p></div><dl><div><dt>${safeText(String(items.length))}</dt><dd>Tệp đang hoạt động</dd></div><div><dt>25 MB</dt><dd>Giới hạn mặc định mỗi tệp</dd></div></dl></section><div class="portal-vault-layout"><section class="portal-card portal-card-pad portal-vault-upload"><div class="portal-card-header"><div><h2 class="portal-card-title">Thêm tệp</h2><p class="portal-card-subtitle">Chỉ tải định dạng được kiểm tra ở máy chủ. Tệp luôn tải về dạng attachment riêng tư.</p></div>${badge(canUpload ? "ready" : "guarded")}</div><form class="portal-form" data-portal-form data-portal-action="asset-vault-upload" data-portal-route="/asset-vault" novalidate>${renderFields(assetVaultFormFields(), canUpload, context, formValues)}<label class="portal-vault-dropzone" for="portal-vault-file"><span class="portal-vault-dropzone-icon" aria-hidden="true">↑</span><span><strong>Chọn tệp riêng tư</strong><small>Ảnh, video, audio, PDF, TXT/SRT/VTT hoặc DOCX · tối đa 25 MB mặc định</small></span><input id="portal-vault-file" class="portal-vault-file-input" name="file" type="file" accept=".jpg,.jpeg,.png,.webp,.mp4,.mov,.webm,.mp3,.wav,.m4a,.ogg,.pdf,.txt,.srt,.vtt,.docx" required${fileDisabled}></label><div class="portal-form-footer"><span class="portal-form-note">Tệp không được gửi sang Bot, provider hoặc browser storage. Upload có idempotency và audit metadata đã sanitize.</span><button class="portal-button portal-button--primary" type="submit"${fileDisabled}>Lưu vào Asset Vault</button></div></form></section><aside class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Ranh giới rõ ràng</h2><p class="portal-card-subtitle">Hai thư viện phục vụ hai mục đích khác nhau.</p></div></div><ul class="portal-project-steps"><li><strong>Asset Vault Web</strong><span>Tệp bạn chủ động lưu cho Project/Web workflow, owner-scoped và private.</span></li><li><strong>Tài sản Bot</strong><span>Output delivery của job canonical, có metadata/URL ký riêng ở <a href="/assets">Tài sản Bot</a>.</span></li><li><strong>Không suy diễn output</strong><span>Một tệp Vault không tự trở thành input engine hoặc kết quả đã hoàn tất.</span></li></ul></aside></div><section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Tệp đang hoạt động</h2><p class="portal-card-subtitle">Chỉ tệp thuộc signed Web account hiện tại. Lưu trữ sẽ gỡ tệp khỏi danh sách và khóa download active.</p></div><button class="portal-button portal-button--quiet" type="button" data-portal-action="asset-vault-refresh" data-portal-route="/asset-vault"${canRefresh ? "" : " disabled"}>Làm mới</button></div>${cards}</section></article>`;
  }

  // Web Support Desk deliberately keeps its data model and language separate
  // from Bot ticket compatibility.  The browser only receives an owner- or
  // staff-scoped projection from `/api/v1/support/cases*`; it never reads the
  // Telegram ticket history or pretends to deliver a notification elsewhere.
  const SUPPORT_CASE_STATES = Object.freeze(["new", "reviewing", "waiting_user", "waiting_provider", "refund_pending", "resolved", "closed"]);
  const SUPPORT_CASE_CATEGORIES = Object.freeze([
    ["general_support", "Hỗ trợ chung"], ["image_error", "Ảnh / thiết kế"], ["video_error", "Video"],
    ["document_pdf", "Tài liệu / PDF"], ["payment_topup", "Thanh toán / nạp Xu"], ["package_combo", "Gói dịch vụ"],
    ["refund", "Yêu cầu hoàn tiền"], ["feature_request", "Đề xuất tính năng"], ["lead_consulting", "Tư vấn"],
    ["service_consulting", "Tư vấn dịch vụ"], ["premium_lead", "Gói cao cấp"], ["custom_bot_lead", "Bot tùy chỉnh"], ["other", "Khác"]
  ]);
  const SUPPORT_CASE_PRIORITIES = Object.freeze([["low", "Thấp"], ["normal", "Bình thường"], ["high", "Cao"], ["urgent", "Khẩn"]]);

  function supportCaseId(value) {
    const raw = String(value || "").trim();
    return /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(raw) ? raw : "";
  }

  function supportCaseState(value) {
    const state = String(value || "").trim().toLowerCase();
    return SUPPORT_CASE_STATES.includes(state) ? state : "guarded";
  }

  function supportCaseCategoryLabel(value) {
    const match = SUPPORT_CASE_CATEGORIES.find(([key]) => key === String(value || "").trim().toLowerCase());
    return match ? match[1] : "Yêu cầu Web";
  }

  function supportCasePriorityLabel(value) {
    const match = SUPPORT_CASE_PRIORITIES.find(([key]) => key === String(value || "").trim().toLowerCase());
    return match ? match[1] : "Bình thường";
  }

  function supportCaseTimestamp(value) {
    const raw = String(value || "").trim();
    if (!raw) return "—";
    const date = new Date(raw);
    if (Number.isNaN(date.getTime())) return raw.replace("T", " · ");
    try { return new Intl.DateTimeFormat("vi-VN", { dateStyle: "medium", timeStyle: "short" }).format(date); } catch (_) { return raw.replace("T", " · "); }
  }

  function supportCaseHref(item, admin) {
    const id = supportCaseId(item && item.id);
    if (!id) return admin ? "/admin/support" : "/tickets";
    return `${admin ? "/admin/support" : "/tickets"}/${encodeURIComponent(id)}`;
  }

  function supportCaseItems(context, admin) {
    const source = admin ? context.supportAdminCases : context.supportCases;
    return Array.isArray(source) ? source.filter((item) => item && supportCaseId(item.id)).slice(0, 100) : [];
  }

  function supportDetail(context, admin) {
    const source = admin ? context.supportAdminCaseDetail : context.supportCaseDetail;
    return source && typeof source === "object" && source.case && supportCaseId(source.case.id) ? source : {};
  }

  function supportEventLabel(value) {
    const labels = {
      case_created: "Đã tạo yêu cầu", customer_replied: "Khách hàng đã phản hồi", customer_close: "Khách hàng đã đóng yêu cầu",
      customer_reopen: "Khách hàng đã mở lại yêu cầu", operator_replied_public: "Nhân sự đã phản hồi", operator_noted_internal: "Đã thêm ghi chú nội bộ",
      operator_updated: "Nhân sự đã cập nhật triage"
    };
    return labels[String(value || "")] || "Đã cập nhật yêu cầu";
  }

  function supportStateOptions(selected, allowAll) {
    const first = allowAll ? `<option value="all"${String(selected || "all") === "all" ? " selected" : ""}>Tất cả trạng thái</option>` : "";
    return `${first}${SUPPORT_CASE_STATES.map((state) => `<option value="${state}"${state === supportCaseState(selected) ? " selected" : ""}>${safeText(STATE_LABELS[state])}</option>`).join("")}`;
  }

  function supportCategoryOptions(selected, allowAll) {
    const current = String(selected || "").trim().toLowerCase();
    const first = allowAll ? `<option value=""${!current ? " selected" : ""}>Tất cả nhóm</option>` : "";
    return `${first}${SUPPORT_CASE_CATEGORIES.map(([key, label]) => `<option value="${safeText(key)}"${key === current ? " selected" : ""}>${safeText(label)}</option>`).join("")}`;
  }

  function supportPriorityOptions(selected) {
    const current = String(selected || "normal").trim().toLowerCase();
    return SUPPORT_CASE_PRIORITIES.map(([key, label]) => `<option value="${safeText(key)}"${key === current ? " selected" : ""}>${safeText(label)}</option>`).join("");
  }

  function supportStateStats(summary) {
    const states = summary && summary.states && typeof summary.states === "object" ? summary.states : {};
    const count = (state) => Math.max(0, Number(states[state] || 0) || 0);
    const total = SUPPORT_CASE_STATES.reduce((sum, state) => sum + count(state), 0);
    return `<section class="portal-support-metrics" aria-label="Tóm tắt Web Support Desk"><div class="portal-metric"><span>Tổng yêu cầu</span><strong>${safeText(String(total))}</strong><em>Chỉ case Web của bạn</em></div><div class="portal-metric"><span>Đang xử lý</span><strong>${safeText(String(count("new") + count("reviewing") + count("waiting_provider") + count("refund_pending")))}</strong><em>Không phải trạng thái provider tự động</em></div><div class="portal-metric"><span>Chờ phản hồi</span><strong>${safeText(String(count("waiting_user")))}</strong><em>Chỉ hiển thị trong Web</em></div><div class="portal-metric"><span>Đã xử lý</span><strong>${safeText(String(count("resolved") + count("closed")))}</strong><em>Có thể mở lại khi cần</em></div></section>`;
  }

  function renderSupportCaseCards(items, admin) {
    if (!items.length) return renderEmpty("Chưa có yêu cầu Web", admin ? "Chưa có case nào cần xử lý theo bộ lọc hiện tại." : "Tạo yêu cầu đầu tiên để trao đổi ngay trong Web Support Desk.", ICONS.ticket);
    return `<div class="portal-support-case-grid">${items.map((item) => {
      const state = supportCaseState(item.state);
      const customer = admin && item.customer && typeof item.customer === "object" ? item.customer : {};
      return `<article class="portal-support-case-card"><div class="portal-support-case-head"><span class="portal-support-case-category">${safeText(supportCaseCategoryLabel(item.category))}</span>${badge(state)}</div><h3>${safeText(String(item.subject || "Yêu cầu Web"))}</h3><p>${safeText(String(item.excerpt || "Không có mô tả hiển thị."))}</p><dl class="portal-support-case-meta"><div><dt>Ưu tiên</dt><dd>${safeText(supportCasePriorityLabel(item.priority))}</dd></div><div><dt>Cập nhật</dt><dd>${safeText(supportCaseTimestamp(item.updated_at || item.created_at))}</dd></div>${admin ? `<div><dt>Khách hàng</dt><dd>${safeText(String(customer.display_name || "Khách Web"))}${customer.email_masked ? `<small>${safeText(String(customer.email_masked))}</small>` : ""}</dd></div>` : ""}</dl><div class="portal-form-footer"><a class="portal-button portal-button--quiet" href="${safeText(supportCaseHref(item, admin))}">Mở yêu cầu <span aria-hidden="true">→</span></a><span class="portal-form-note">${safeText(String(item.id).slice(0, 8))}</span></div></article>`;
    }).join("")}</div>`;
  }

  function renderSupportActivity(events) {
    const items = Array.isArray(events) ? events.slice(0, 8) : [];
    if (!items.length) return renderEmpty("Chưa có hoạt động", "Hoạt động sẽ xuất hiện sau khi bạn tạo hoặc cập nhật yêu cầu trong Web.", "·");
    return `<ol class="portal-support-activity">${items.map((event) => `<li><span class="portal-support-activity-dot" aria-hidden="true"></span><div><strong>${safeText(supportEventLabel(event && event.action))}</strong><small>${safeText(supportCaseTimestamp(event && event.created_at))} · ${safeText(STATE_LABELS[supportCaseState(event && event.state)] || "Đã cập nhật")}</small></div></li>`).join("")}</ol>`;
  }

  function renderSupportDesk(page, context) {
    const enabled = Boolean(context.capabilities && context.capabilities["support-case-create"] === true);
    const values = transientFormValues("/support");
    const cases = supportCaseItems(context, false).slice(0, 4);
    const state = context.supportReadState === "ready" ? "ready" : (context.supportReadState === "loading" ? "processing" : "guarded");
    const disabled = enabled ? "" : " disabled";
    const reason = context.session.authenticated !== true ? "Đăng nhập bằng signed Web session để tạo yêu cầu." : (context.supportDeskEnabled ? "CSRF hoặc quyền tạo yêu cầu chưa sẵn sàng cho phiên này." : "Web Support Desk đang tạm dừng theo cấu hình máy chủ.");
    return `<article class="portal-page portal-support-desk">${renderHero(page, context)}<section class="portal-support-intro"><div><span class="portal-section-kicker">Web-native Support Desk</span><h2>Trao đổi rõ ràng, riêng tư và có trạng thái</h2><p>Case, phản hồi và timeline được giữ trong Web App theo signed account. Đây không phải Telegram inbox và không tự gửi email, Telegram hay thông báo provider.</p></div><dl><div><dt>Web-only</dt><dd>Không sao chép lịch sử Bot</dd></div><div><dt>CSRF + audit</dt><dd>Mọi write đều được server kiểm tra</dd></div></dl></section>${supportStateStats(context.supportSummary)}<div class="portal-support-layout"><section class="portal-card portal-card-pad portal-support-intake"><div class="portal-card-header"><div><h2 class="portal-card-title">Tạo yêu cầu mới</h2><p class="portal-card-subtitle">Mô tả vấn đề, bối cảnh và kết quả bạn mong muốn. Không đính kèm dữ liệu thanh toán hoặc thông tin nhạy cảm.</p></div>${badge(enabled ? "ready" : state)}</div><form class="portal-form" data-portal-form data-portal-action="support-case-create" data-portal-route="/support" novalidate><div class="portal-fields"><div class="portal-field"><label for="support-category">Nhóm yêu cầu</label><select class="portal-select" id="support-category" name="category"${disabled}>${supportCategoryOptions(values.category || "general_support", false)}</select></div><div class="portal-field"><label for="support-priority">Mức ưu tiên</label><select class="portal-select" id="support-priority" name="priority"${disabled}>${supportPriorityOptions(values.priority || "normal")}</select></div><div class="portal-field portal-field--wide"><label for="support-subject">Chủ đề <span class="portal-required-mark" aria-hidden="true">*</span></label><input class="portal-input" id="support-subject" name="subject" type="text" minlength="3" maxlength="180" required value="${safeText(String(values.subject || ""))}" placeholder="Ví dụ: Không mở được file PDF riêng tư"${disabled}></div><div class="portal-field portal-field--wide"><label for="support-detail">Nội dung <span class="portal-required-mark" aria-hidden="true">*</span></label><textarea class="portal-textarea" id="support-detail" name="detail" minlength="3" maxlength="4000" required placeholder="Nêu bước bạn đã thử, thời điểm xảy ra và kết quả mong muốn…"${disabled}>${safeText(String(values.detail || ""))}</textarea><span class="portal-field-help">Không gửi password, API key, token, OTP/CVV, số thẻ, bill/TXID, số tài khoản hoặc QR thanh toán.</span></div></div><div class="portal-form-footer"><span class="portal-form-note">${safeText(enabled ? "Yêu cầu chỉ được ghi trong Web Support Desk; không tạo ticket Bot hoặc external delivery." : reason)}</span><button class="portal-button portal-button--primary" type="submit"${disabled}>Tạo yêu cầu</button></div></form></section><aside class="portal-card portal-card-pad portal-support-boundary"><div class="portal-card-header"><div><h2 class="portal-card-title">Phạm vi an toàn</h2><p class="portal-card-subtitle">Support Desk xử lý trao đổi trong Web, không xử lý bí mật hoặc đối soát thanh toán bằng nội dung tự do.</p></div>${badge("read_only")}</div><ul class="portal-project-steps"><li><strong>Không có thông báo giả</strong><span>Trạng thái và phản hồi chỉ hiển thị khi bạn mở Web App.</span></li><li><strong>Không có ledger write</strong><span>Không cộng/trừ Xu, tạo PayOS order hay hoàn tiền từ case.</span></li><li><strong>Không có upload ngầm</strong><span>Phiên bản đầu tiên nhận văn bản; không nhận tệp Telegram hoặc proof thanh toán.</span></li></ul><div class="portal-form-footer"><a class="portal-button portal-button--quiet" href="/tickets">Xem tất cả yêu cầu</a></div></aside></div><section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Yêu cầu gần đây</h2><p class="portal-card-subtitle">Chỉ case thuộc Web account hiện tại.</p></div><button class="portal-button portal-button--quiet" type="button" data-portal-action="support-cases-refresh" data-portal-route="/support"${context.capabilities && context.capabilities["support-case-refresh"] === true ? "" : " disabled"}>Làm mới</button></div>${renderSupportCaseCards(cases, false)}</section><section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Hoạt động Web gần đây</h2><p class="portal-card-subtitle">Audit/event hiển thị không bao gồm nội dung case.</p></div>${badge("read_only")}</div>${renderSupportActivity(context.supportEvents)}</section></article>`;
  }

  function renderSupportCases(page, context) {
    const filter = context.supportCaseFilter && typeof context.supportCaseFilter === "object" ? context.supportCaseFilter : { state: "all", category: "", q: "" };
    const items = supportCaseItems(context, false);
    const enabled = Boolean(context.capabilities && context.capabilities["support-case-view"] === true);
    const state = context.supportReadState === "ready" ? "read_only" : (context.supportReadState === "loading" ? "processing" : "guarded");
    const disabled = enabled ? "" : " disabled";
    return `<article class="portal-page portal-support-cases">${renderHero(page, context)}${supportStateStats(context.supportSummary)}<section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Lọc yêu cầu Web</h2><p class="portal-card-subtitle">Bộ lọc chỉ truy vấn case thuộc signed account hiện tại, không tìm trong Bot ticket hoặc nội dung của account khác.</p></div>${badge(state)}</div><form class="portal-support-filter" data-portal-form data-portal-action="support-cases-filter" data-portal-route="/tickets" novalidate><label class="portal-field"><span>Trạng thái</span><select class="portal-select" name="state"${disabled}>${supportStateOptions(filter.state, true)}</select></label><label class="portal-field"><span>Nhóm</span><select class="portal-select" name="category"${disabled}>${supportCategoryOptions(filter.category, true)}</select></label><label class="portal-field portal-support-filter-search"><span>Tìm trong yêu cầu của bạn</span><input class="portal-input" name="q" type="search" maxlength="80" value="${safeText(String(filter.q || ""))}" placeholder="Chủ đề hoặc nội dung…"${disabled}></label><div class="portal-form-footer"><span class="portal-form-note">${enabled ? "Tìm kiếm không được lưu vào URL, browser storage hay Bot." : "Cần signed Web session để xem yêu cầu riêng."}</span><button class="portal-button portal-button--quiet" type="submit"${disabled}>Áp dụng</button><button class="portal-button portal-button--quiet" type="button" data-portal-action="support-cases-refresh" data-portal-route="/tickets"${disabled}>Làm mới</button></div></form></section><section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Yêu cầu của tôi</h2><p class="portal-card-subtitle">Mở từng case để xem timeline, phản hồi hoặc đóng/mở lại theo revision server-side.</p></div><a class="portal-button portal-button--primary" href="/support">Tạo yêu cầu</a></div>${renderSupportCaseCards(items, false)}</section></article>`;
  }

  function renderSupportCaseDetail(page, context) {
    const detail = supportDetail(context, false);
    const caseItem = detail.case && typeof detail.case === "object" ? detail.case : null;
    const messages = Array.isArray(detail.messages) ? detail.messages : [];
    const events = Array.isArray(detail.events) ? detail.events : [];
    const canReply = Boolean(caseItem && context.capabilities && context.capabilities["support-case-reply"] === true && supportCaseState(caseItem.state) !== "closed");
    const canTransition = Boolean(caseItem && context.capabilities && context.capabilities["support-case-transition"] === true);
    const revision = caseItem ? Number(caseItem.revision || 0) : 0;
    if (!caseItem) {
      const loading = context.supportReadState === "loading";
      return `<article class="portal-page portal-support-case-detail">${renderHero(page, context)}<section class="portal-card portal-card-pad"><div class="portal-state" data-state="${loading ? "processing" : "guarded"}"><span class="portal-state-icon" aria-hidden="true">${loading ? "◌" : "!"}</span><div><h2>${loading ? "Đang nạp yêu cầu riêng" : "Yêu cầu không khả dụng"}</h2><p>${loading ? "Máy chủ đang kiểm tra ownership của Web case này." : "Case không tồn tại, không thuộc account hiện tại hoặc Support Desk đang bị bảo vệ."}</p></div></div><div class="portal-form-footer"><a class="portal-button portal-button--quiet" href="/tickets">Quay lại yêu cầu của tôi</a></div></section></article>`;
    }
    const state = supportCaseState(caseItem.state);
    const disabledReply = canReply ? "" : " disabled";
    const replyForm = state === "closed"
      ? `<section class="portal-card portal-card-pad"><div class="portal-notice"><span class="portal-notice-icon" aria-hidden="true">i</span><div><strong>Yêu cầu đã đóng</strong><p>Mở lại yêu cầu trước khi gửi phản hồi mới. Thao tác sẽ được máy chủ kiểm tra revision và ownership.</p></div></div></section>`
      : `<section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Thêm phản hồi</h2><p class="portal-card-subtitle">Phản hồi sẽ xuất hiện trong timeline Web của case này; không gửi Telegram, email hay thông báo bên ngoài.</p></div>${badge(canReply ? "ready" : "guarded")}</div><form class="portal-form" data-portal-form data-portal-action="support-case-reply" data-portal-route="${safeText(page.routePath || page.path)}" data-support-case-id="${safeText(caseItem.id)}" data-support-case-revision="${safeText(String(revision))}" novalidate><label class="portal-field"><span class="portal-label">Phản hồi <span class="portal-required-mark" aria-hidden="true">*</span></span><textarea class="portal-textarea" name="body" minlength="1" maxlength="4000" required placeholder="Viết thông tin bổ sung hoặc xác nhận của bạn…"${disabledReply}></textarea><span class="portal-field-help">Không gửi secret, OTP/CVV, số thẻ, bill, TXID, số tài khoản hoặc QR thanh toán.</span></label><div class="portal-form-footer"><span class="portal-form-note">${canReply ? "Server sẽ kiểm tra version trước khi lưu để không ghi đè cập nhật mới." : "CSRF hoặc quyền gửi phản hồi chưa sẵn sàng."}</span><button class="portal-button portal-button--primary" type="submit"${disabledReply}>Gửi phản hồi</button></div></form></section>`;
    const transition = state === "closed" || state === "resolved"
      ? `<button class="portal-button portal-button--quiet" type="button" data-portal-action="support-case-reopen" data-portal-route="${safeText(page.routePath || page.path)}" data-support-case-id="${safeText(caseItem.id)}" data-support-case-revision="${safeText(String(revision))}" data-portal-confirm="Mở lại yêu cầu này để Web Support Desk tiếp tục rà soát? Không có Telegram, email hay thay đổi payment nào được gửi."${canTransition ? "" : " disabled"}>Mở lại yêu cầu</button>`
      : `<button class="portal-button portal-button--quiet" type="button" data-portal-action="support-case-close" data-portal-route="${safeText(page.routePath || page.path)}" data-support-case-id="${safeText(caseItem.id)}" data-support-case-revision="${safeText(String(revision))}" data-portal-confirm="Đóng yêu cầu Web này? Bạn có thể mở lại sau; thao tác không gửi Telegram, email hay thay đổi payment."${canTransition ? "" : " disabled"}>Đóng yêu cầu</button>`;
    const messageTimeline = messages.length ? `<ol class="portal-support-thread">${messages.map((message) => `<li class="portal-support-message portal-support-message--${safeText(String(message.author_role || "customer"))}"><div class="portal-support-message-meta"><strong>${message.author_role === "operator" ? "Web Support Desk" : "Bạn"}</strong><span>${safeText(supportCaseTimestamp(message.created_at))}</span></div><p>${safeText(String(message.body || ""))}</p></li>`).join("")}</ol>` : renderEmpty("Chưa có nội dung hiển thị", "Case này chưa có phản hồi an toàn để hiển thị.", "·");
    return `<article class="portal-page portal-support-case-detail">${renderHero(page, context)}<section class="portal-support-case-hero"><div><div class="portal-support-case-head"><span class="portal-support-case-category">${safeText(supportCaseCategoryLabel(caseItem.category))}</span>${badge(state)}</div><h2>${safeText(String(caseItem.subject || "Yêu cầu Web"))}</h2><p>${safeText(String(caseItem.excerpt || ""))}</p></div><dl><div><dt>Ưu tiên</dt><dd>${safeText(supportCasePriorityLabel(caseItem.priority))}</dd></div><div><dt>Cập nhật</dt><dd>${safeText(supportCaseTimestamp(caseItem.updated_at || caseItem.created_at))}</dd></div><div><dt>Phiên bản</dt><dd>${safeText(String(revision))}</dd></div></dl></section><div class="portal-support-detail-layout"><section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Trao đổi</h2><p class="portal-card-subtitle">Chỉ hiển thị các phản hồi public của Web Support Desk.</p></div>${badge("read_only")}</div>${messageTimeline}</section><aside class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Thông tin case</h2><p class="portal-card-subtitle">Mọi trạng thái được server cập nhật theo revision.</p></div></div><dl class="portal-support-case-meta"><div><dt>Đã tạo</dt><dd>${safeText(supportCaseTimestamp(caseItem.created_at))}</dd></div><div><dt>Phản hồi public gần nhất</dt><dd>${safeText(supportCaseTimestamp(caseItem.last_public_message_at))}</dd></div><div><dt>Case ID</dt><dd><code>${safeText(String(caseItem.id).slice(0, 8))}</code></dd></div></dl><div class="portal-form-footer">${transition}<a class="portal-button portal-button--quiet" href="/tickets">Danh sách yêu cầu</a></div></aside></div>${replyForm}<section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Timeline trạng thái</h2><p class="portal-card-subtitle">Timeline không hiển thị nội dung audit riêng tư hoặc hoạt động ngoài Web.</p></div>${badge("read_only")}</div>${renderSupportActivity(events)}</section></article>`;
  }

  function renderTickets(page, context) {
    const allTickets = Array.isArray(context.tickets) ? context.tickets : [];
    const selected = TICKET_FILTERS.some(([value]) => value === context.ticketFilter) ? context.ticketFilter : "all";
    const tickets = selected === "all" ? allTickets : allTickets.filter((item) => canonicalTicketStatus(item) === selected);
    const counts = Object.fromEntries(TICKET_FILTERS.map(([value]) => [value, value === "all" ? allTickets.length : allTickets.filter((item) => canonicalTicketStatus(item) === value).length]));
    const filters = filterBar(TICKET_FILTERS, selected, "filter-tickets", "data-ticket-filter", "Lọc ticket", counts);
    const connection = context.telegramConnection && typeof context.telegramConnection === "object" ? context.telegramConnection : {};
    const botUrl = safeTelegramLink(connection.bot_chat_url || "");
    const ticketBotHandoff = `<section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Theo dõi sâu trong Bot</h2><p class="portal-card-subtitle">Thread/reply, attachment Telegram và trạng thái chi tiết tiếp tục do Bot canonical quản lý; Portal không gửi mã ticket, identity hoặc nội dung hiện có sang Bot.</p></div>${badge(botUrl ? "read_only" : "guarded")}</div>${botUrl ? `<div class="portal-form-footer"><a class="portal-button portal-button--quiet" href="${safeText(botUrl)}" target="_blank" rel="noopener noreferrer">Mở Bot</a><button class="portal-button portal-button--quiet" type="button" data-portal-action="copy-bot-companion-command" data-copy-text="/tickets">Sao chép /tickets</button><button class="portal-button portal-button--quiet" type="button" data-portal-action="copy-bot-companion-command" data-copy-text="/ticket_status">Sao chép /ticket_status</button></div>` : `<div class="portal-notice"><span class="portal-notice-icon" aria-hidden="true">i</span><div><strong>Bot URL chưa sẵn sàng</strong><p>Web đang chờ <code>BOT_USERNAME</code> hợp lệ trước khi mở handoff an toàn.</p></div></div>`}</section>`;
    return `<article class="portal-page">${renderHero(page, context)}<div class="portal-status-grid">${renderStatusCard(page, context)}${renderSummary(page, context)}</div>
      <section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Yêu cầu hỗ trợ</h2><p class="portal-card-subtitle">Nội dung chỉ được nạp cho signed session sở hữu ticket; không có inbox hay attachment provider trong browser.</p></div><a class="portal-button portal-button--quiet" href="/support">Tạo ticket →</a></div>${filters}${renderRowsTable(["Mã ticket", "Loại", "Chủ đề", "Trạng thái canonical", "Cập nhật", "Nội dung đã gửi"], tickets, (item) => `<td>${safeText(item.id || "—")}</td><td>${safeText(ticketCategoryLabel(item))}</td><td>${safeText(item.subject || "—")}</td><td>${ticketStatusCell(item)}</td><td>${safeText(item.updated_at || item.created_at || "—")}</td><td><span class="portal-ticket-preview">${shortText(item.content, 120)}</span></td>`, selected === "all" ? "Chưa có ticket được cấp" : "Không có ticket ở trạng thái này", selected === "all" ? "Core Bridge sẽ trả ticket theo signed session." : "Đổi bộ lọc hoặc quay lại sau khi Core Bridge cập nhật trạng thái.")}</section>${ticketBotHandoff}</article>`;
  }

  function renderSupportAdminSummary(summary) {
    const states = summary && summary.states && typeof summary.states === "object" ? summary.states : {};
    const count = (state) => Math.max(0, Number(states[state] || 0) || 0);
    const open = SUPPORT_CASE_STATES.filter((state) => !["resolved", "closed"].includes(state)).reduce((sum, state) => sum + count(state), 0);
    return `<section class="portal-support-metrics" aria-label="Tóm tắt vận hành Support Desk"><div class="portal-metric"><span>Đang mở</span><strong>${safeText(String(open))}</strong><em>Case Web chưa resolved/closed</em></div><div class="portal-metric"><span>Chờ khách</span><strong>${safeText(String(count("waiting_user")))}</strong><em>Chỉ public reply mới chuyển trạng thái</em></div><div class="portal-metric"><span>Chờ đối tác</span><strong>${safeText(String(count("waiting_provider")))}</strong><em>Chỉ chọn khi operator biết trạng thái</em></div><div class="portal-metric"><span>Quá SLA nội bộ</span><strong>${safeText(String(Math.max(0, Number(summary && summary.overdue || 0) || 0)))}</strong><em>24h/72h theo policy Web</em></div></section>`;
  }

  function renderSupportAdmin(page, context) {
    const summary = context.supportAdminSummary && typeof context.supportAdminSummary === "object" ? context.supportAdminSummary : {};
    const filter = context.supportAdminCaseFilter && typeof context.supportAdminCaseFilter === "object" ? context.supportAdminCaseFilter : { state: "all", category: "", q: "" };
    const items = supportCaseItems(context, true);
    const staffRole = String(summary.operator_role || "").trim();
    const allowed = context.supportAdminReadState === "ready" && (staffRole === "operator" || staffRole === "manager");
    const loading = context.supportAdminReadState === "loading";
    if (!allowed && !loading) {
      return `<article class="portal-page portal-support-admin">${renderHero(page, context)}<section class="portal-card portal-card-pad"><div class="portal-state" data-state="guarded"><span class="portal-state-icon" aria-hidden="true">⌘</span><div><h2>Quyền Support Desk chưa được cấp</h2><p>Máy chủ chỉ mở dữ liệu CSKH cho signed Web account có role server-side admin, support_manager hoặc support_operator. Browser không thể tự gán quyền bằng admin ID, Telegram ID hoặc localStorage.</p><div class="portal-state-meta"><span>Server-side role</span><span>Không gọi Bot bridge</span><span>Không có PII fallback</span></div></div></div></section></article>`;
    }
    if (loading) {
      return `<article class="portal-page portal-support-admin">${renderHero(page, context)}<section class="portal-card portal-card-pad"><div class="portal-state" data-state="processing"><span class="portal-state-icon" aria-hidden="true">◌</span><div><h2>Đang kiểm tra quyền Support Desk</h2><p>Máy chủ đang xác thực signed session và role Web trước khi nạp case vận hành.</p></div></div></section></article>`;
    }
    return `<article class="portal-page portal-support-admin">${renderHero(page, context)}<section class="portal-support-admin-intro"><div><span class="portal-section-kicker">Web-native operations</span><h2>Hỗ trợ có triage, không có đường tắt</h2><p>Operator xử lý đúng case, đúng revision và đúng phạm vi. Mọi thay đổi cần CSRF, confirmation, idempotency và audit do server thực hiện.</p></div><dl><div><dt>${safeText(staffRole === "manager" ? "Manager" : "Operator")}</dt><dd>Role do máy chủ xác minh</dd></div><div><dt>Web-only</dt><dd>Không gửi external delivery</dd></div></dl></section>${renderSupportAdminSummary(summary)}<section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Lọc hàng đợi</h2><p class="portal-card-subtitle">Chỉ hiển thị case Web Support Desk. Email được mask; không có Bot ticket history hoặc ledger/payment data.</p></div>${badge("read_only")}</div><form class="portal-support-filter" data-portal-form data-portal-action="support-admin-cases-filter" data-portal-route="/admin/support" novalidate><label class="portal-field"><span>Trạng thái</span><select class="portal-select" name="state">${supportStateOptions(filter.state, true)}</select></label><label class="portal-field"><span>Nhóm</span><select class="portal-select" name="category">${supportCategoryOptions(filter.category, true)}</select></label><label class="portal-field portal-support-filter-search"><span>Tìm case</span><input class="portal-input" name="q" type="search" maxlength="80" value="${safeText(String(filter.q || ""))}" placeholder="Tên, chủ đề hoặc nội dung…"></label><div class="portal-form-footer"><span class="portal-form-note">Tìm kiếm chỉ gửi query hẹp tới Web Support Desk theo quyền server-side.</span><button class="portal-button portal-button--quiet" type="submit">Áp dụng</button><button class="portal-button portal-button--quiet" type="button" data-portal-action="support-admin-cases-refresh" data-portal-route="/admin/support">Làm mới</button></div></form></section><section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Hàng đợi yêu cầu</h2><p class="portal-card-subtitle">Sắp theo ưu tiên và cập nhật gần nhất; mở case để phản hồi public, ghi chú nội bộ hoặc cập nhật triage.</p></div><span class="portal-form-note">${safeText(String(items.length))} case hiển thị</span></div>${renderSupportCaseCards(items, true)}</section><section class="portal-card portal-card-pad"><div class="portal-notice portal-notice--info"><span class="portal-notice-icon" aria-hidden="true">i</span><div><strong>Ranh giới nghiệp vụ</strong><p>Support Desk không thay đổi wallet/Xu, PayOS, refund ledger, job, provider hoặc file delivery. Nếu cần một workflow khác, case chỉ ghi nhận thông tin rõ ràng trong Web.</p></div></div></section></article>`;
  }

  function renderSupportAdminCaseDetail(page, context) {
    const detail = supportDetail(context, true);
    const caseItem = detail.case && typeof detail.case === "object" ? detail.case : null;
    const summary = context.supportAdminSummary && typeof context.supportAdminSummary === "object" ? context.supportAdminSummary : {};
    const staffRole = String(summary.operator_role || "").trim();
    const hasRole = staffRole === "operator" || staffRole === "manager";
    if (!caseItem || !hasRole) {
      const loading = context.supportAdminReadState === "loading";
      return `<article class="portal-page portal-support-admin-case-detail">${renderHero(page, context)}<section class="portal-card portal-card-pad"><div class="portal-state" data-state="${loading ? "processing" : "guarded"}"><span class="portal-state-icon" aria-hidden="true">${loading ? "◌" : "⌘"}</span><div><h2>${loading ? "Đang nạp case vận hành" : "Case không khả dụng"}</h2><p>${loading ? "Máy chủ đang kiểm tra quyền Support Desk và nạp dữ liệu đã được redaction." : "Case không tồn tại hoặc signed Web session không có quyền Support Desk."}</p></div></div><div class="portal-form-footer"><a class="portal-button portal-button--quiet" href="/admin/support">Quay lại Support Desk</a></div></section></article>`;
    }
    const state = supportCaseState(caseItem.state);
    const revision = Number(caseItem.revision || 0);
    const customer = caseItem.customer && typeof caseItem.customer === "object" ? caseItem.customer : {};
    const messages = Array.isArray(detail.messages) ? detail.messages : [];
    const events = Array.isArray(detail.events) ? detail.events : [];
    const writable = Boolean(context.capabilities && context.capabilities["support-admin-case-write"] === true);
    const writeDisabled = writable ? "" : " disabled";
    const publicReply = state === "closed" ? renderEmpty("Case đã đóng", "Mở lại case qua cập nhật trạng thái trước khi gửi phản hồi mới.", "·") : `<form class="portal-form" data-portal-form data-portal-action="support-admin-case-reply" data-portal-route="${safeText(page.routePath || page.path)}" data-support-case-id="${safeText(caseItem.id)}" data-support-case-revision="${safeText(String(revision))}" data-portal-confirm="Lưu phản hồi Support Desk? Nếu chọn public, khách hàng chỉ thấy phản hồi này khi mở Web App; không có Telegram, email hay external delivery." novalidate><div class="portal-fields"><div class="portal-field"><label for="support-reply-visibility">Phạm vi</label><select class="portal-select" id="support-reply-visibility" name="visibility"${writeDisabled}><option value="public">Public · khách hàng thấy trong Web</option><option value="internal">Internal · chỉ nhân sự Support Desk thấy</option></select></div><div class="portal-field"><label for="support-reply-state">Trạng thái sau phản hồi</label><select class="portal-select" id="support-reply-state" name="next_state"${writeDisabled}><option value="" selected>Tự chọn theo phạm vi phản hồi</option>${supportStateOptions("", false)}</select></div><div class="portal-field portal-field--wide"><label for="support-reply-body">Nội dung <span class="portal-required-mark" aria-hidden="true">*</span></label><textarea class="portal-textarea" id="support-reply-body" name="body" minlength="1" maxlength="4000" required placeholder="Viết hướng dẫn, câu hỏi làm rõ hoặc ghi chú nội bộ…"${writeDisabled}></textarea><span class="portal-field-help">Không ghi secret, OTP/CVV, số thẻ, bill/TXID, số tài khoản, QR thanh toán hoặc dữ liệu provider.</span></div></div><div class="portal-form-footer"><span class="portal-form-note">${writable ? "Máy chủ kiểm tra role, CSRF, confirmation, idempotency và revision trước khi lưu." : "Quyền write Support Desk chưa sẵn sàng cho phiên này."}</span><button class="portal-button portal-button--primary" type="submit"${writeDisabled}>Lưu phản hồi</button></div></form>`;
    const updateForm = `<form class="portal-form portal-support-admin-update" data-portal-form data-portal-action="support-admin-case-update" data-portal-route="${safeText(page.routePath || page.path)}" data-support-case-id="${safeText(caseItem.id)}" data-support-case-revision="${safeText(String(revision))}" data-portal-confirm="Cập nhật triage cho case Web này? Thao tác không gửi thông báo ngoài Web và không thay đổi Xu, PayOS, refund ledger, job hay provider." novalidate><div class="portal-fields"><div class="portal-field"><label for="support-update-state">Trạng thái</label><select class="portal-select" id="support-update-state" name="state"${writeDisabled}>${supportStateOptions(state, false)}</select></div><div class="portal-field"><label for="support-update-priority">Ưu tiên</label><select class="portal-select" id="support-update-priority" name="priority"${writeDisabled}>${supportPriorityOptions(caseItem.priority)}</select></div><div class="portal-field portal-field--wide"><label for="support-update-note">Ghi chú nội bộ <span class="portal-required-mark" aria-hidden="true">*</span></label><textarea class="portal-textarea" id="support-update-note" name="operation_note" minlength="3" maxlength="360" required placeholder="Tóm tắt lý do thay đổi trạng thái hoặc ưu tiên…"${writeDisabled}></textarea><span class="portal-field-help">Máy chủ lưu ghi chú này thành message nội bộ cho nhân sự Support Desk; nội dung không đi vào audit raw và không hiển thị cho khách hàng.</span></div></div><div class="portal-form-footer"><span class="portal-form-note">Cập nhật cần confirmation rõ ràng và revision hiện tại.</span><button class="portal-button portal-button--quiet" type="submit"${writeDisabled}>Cập nhật triage</button></div></form>`;
    const thread = messages.length ? `<ol class="portal-support-thread">${messages.map((message) => `<li class="portal-support-message portal-support-message--${safeText(String(message.author_role || "customer"))}${message.visibility === "internal" ? " is-internal" : ""}"><div class="portal-support-message-meta"><strong>${message.author_role === "operator" ? (message.visibility === "internal" ? "Ghi chú nội bộ" : "Web Support Desk") : "Khách hàng"}</strong><span>${safeText(supportCaseTimestamp(message.created_at))}</span></div>${message.author_display_name && message.author_role === "operator" ? `<small>${safeText(String(message.author_display_name))}</small>` : ""}<p>${safeText(String(message.body || ""))}</p></li>`).join("")}</ol>` : renderEmpty("Chưa có phản hồi", "Case này chưa có message để hiển thị.", "·");
    return `<article class="portal-page portal-support-admin-case-detail">${renderHero(page, context)}<section class="portal-support-case-hero"><div><div class="portal-support-case-head"><span class="portal-support-case-category">${safeText(supportCaseCategoryLabel(caseItem.category))}</span>${badge(state)}</div><h2>${safeText(String(caseItem.subject || "Yêu cầu Web"))}</h2><p>${safeText(String(caseItem.excerpt || ""))}</p></div><dl><div><dt>Khách hàng</dt><dd>${safeText(String(customer.display_name || "Khách Web"))}${customer.email_masked ? `<small>${safeText(String(customer.email_masked))}</small>` : ""}</dd></div><div><dt>Ưu tiên</dt><dd>${safeText(supportCasePriorityLabel(caseItem.priority))}</dd></div><div><dt>Revision</dt><dd>${safeText(String(revision))}</dd></div></dl></section><div class="portal-support-detail-layout"><section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Thread case</h2><p class="portal-card-subtitle">Operator thấy phản hồi public và ghi chú internal; khách hàng chỉ thấy public message.</p></div>${badge("read_only")}</div>${thread}</section><aside class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Triage</h2><p class="portal-card-subtitle">Role ${safeText(staffRole)} do máy chủ xác minh.</p></div>${badge(writable ? "ready" : "guarded")}</div><dl class="portal-support-case-meta"><div><dt>Đã tạo</dt><dd>${safeText(supportCaseTimestamp(caseItem.created_at))}</dd></div><div><dt>Public gần nhất</dt><dd>${safeText(supportCaseTimestamp(caseItem.last_public_message_at))}</dd></div><div><dt>Đã resolved</dt><dd>${safeText(supportCaseTimestamp(caseItem.resolved_at))}</dd></div></dl><a class="portal-button portal-button--quiet" href="/admin/support">Quay lại hàng đợi</a></aside></div><div class="portal-support-admin-forms"><section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Phản hồi hoặc ghi chú</h2><p class="portal-card-subtitle">Chọn public khi khách hàng cần thấy message trong Web; internal không hiển thị cho khách hàng.</p></div></div>${publicReply}</section><section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Cập nhật trạng thái</h2><p class="portal-card-subtitle">Không suy đoán provider/refund. Chỉ đặt trạng thái mà operator có căn cứ vận hành.</p></div></div>${updateForm}</section></div><section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Timeline hệ thống</h2><p class="portal-card-subtitle">Event không bao gồm operation note hoặc nội dung audit private.</p></div>${badge("read_only")}</div>${renderSupportActivity(events)}</section></article>`;
  }

  function renderAccount(page, context) {
    const profile = context.profile && typeof context.profile === "object" ? context.profile : {};
    const session = context.session && typeof context.session === "object" ? context.session : {};
    const linked = context.bridge.available === true || (context.linkStatus && context.linkStatus.linked === true);
    const logoutEnabled = context.capabilities && context.capabilities["auth-logout"] === true;
    const loginMethods = profile.loginMethods && typeof profile.loginMethods === "object" ? profile.loginMethods : {};
    const oauthProviders = context.oauthProviders && typeof context.oauthProviders === "object" ? context.oauthProviders : {};
    const methodSummary = [
      loginMethods.email !== false ? "Email + mật khẩu (có thể dùng Gmail)" : "",
      loginMethods.telegram_oidc === true ? "Telegram Login" : (oauthProviders.telegram && oauthProviders.telegram.enabled === true ? "Telegram Login sẵn sàng liên kết" : "Telegram Login chờ cấu hình server"),
      loginMethods.telegram === true ? "Telegram đã liên kết" : "",
      loginMethods.google === true ? "Google OAuth" : (oauthProviders.google && oauthProviders.google.enabled === true ? "Google OAuth sẵn sàng liên kết" : "Google OAuth chờ cấu hình server"),
      loginMethods.github === true ? "GitHub OAuth" : (oauthProviders.github && oauthProviders.github.enabled === true ? "GitHub OAuth sẵn sàng liên kết" : "GitHub OAuth chờ cấu hình server"),
      loginMethods.apple === true ? "Sign in with Apple" : (oauthProviders.apple && oauthProviders.apple.enabled === true ? "Apple OAuth sẵn sàng liên kết" : "Apple OAuth chờ cấu hình server")
    ].filter(Boolean).join(" · ");
    const accountRows = `<div class="portal-summary-list"><div class="portal-summary-item"><span class="portal-summary-key">Tên hiển thị</span><span class="portal-summary-value">${safeText(profile.displayName || profile.name || session.displayName || "—")}</span></div><div class="portal-summary-item"><span class="portal-summary-key">Email</span><span class="portal-summary-value">${safeText(profile.email || session.email || "—")}</span></div><div class="portal-summary-item"><span class="portal-summary-key">Mặc định hồ sơ</span><span class="portal-summary-value">${safeText(profile.locale || "vi")} · ${safeText(profile.timezone || "Asia/Ho_Chi_Minh")} · ${safeText(profile.avatarStyle || "gradient")}</span></div><div class="portal-summary-item"><span class="portal-summary-key">Đăng nhập</span><span class="portal-summary-value">${safeText(methodSummary || "Email + mật khẩu (có thể dùng Gmail)")}</span></div><div class="portal-summary-item"><span class="portal-summary-key">Telegram</span><span class="portal-summary-value">${linked ? "Đã liên kết canonical" : "Chưa liên kết"}</span></div><div class="portal-summary-item"><span class="portal-summary-key">Phiên</span><span class="portal-summary-value">${session.authenticated ? "Signed session hợp lệ" : "Đang chờ xác minh"}</span></div></div>`;
    const profileEnabled = context.capabilities && context.capabilities["update-profile"] === true;
    const profileValues = {
      display_name: profile.displayName || profile.name || session.displayName || "",
      locale: profile.locale || "vi",
      timezone: profile.timezone || "Asia/Ho_Chi_Minh",
      ...transientFormValues("/account")
    };
    const oauthMethodCard = (provider, label) => {
      const linkedProvider = loginMethods[provider] === true;
      const action = `link-oauth-${provider}`;
      const enabled = context.capabilities && context.capabilities[action] === true;
      const state = linkedProvider ? "Đã liên kết" : (enabled ? "Sẵn sàng liên kết" : "Chưa cấu hình");
      const button = linkedProvider
        ? `<span class="portal-form-note">Identity ${safeText(label)} đã được server xác minh; token không lưu trong browser.</span>`
        : `<button class="portal-button portal-button--quiet" type="button" data-portal-action="${safeText(action)}" data-portal-confirm="Bạn muốn liên kết ${safeText(label)} với signed session hiện tại?"${enabled ? "" : " disabled title=\"OAuth chưa được cấu hình trên server.\""}>Liên kết ${safeText(label)}</button>`;
      return `<div class="portal-oauth-method"><div><strong>${safeText(label)}</strong><span>${safeText(state)}</span></div>${button}</div>`;
    };
    const oauthResult = new URLSearchParams(window.location.search).get("oauth") || "";
    const oauthNotice = oauthResult === "linked" || oauthResult === "already-linked"
      ? `<div class="portal-notice portal-notice--info"><span class="portal-notice-icon" aria-hidden="true">✓</span><div><strong>OAuth</strong><p>${oauthResult === "linked" ? "Đã liên kết phương thức OAuth với signed session hiện tại." : "Phương thức OAuth này đã liên kết với tài khoản hiện tại."}</p></div></div>`
      : oauthResult
        ? `<div class="portal-notice"><span class="portal-notice-icon" aria-hidden="true">i</span><div><strong>OAuth chưa hoàn tất</strong><p>Không thể hoàn tất liên kết. Hãy bắt đầu lại từ nút liên kết bên dưới; không chia sẻ mã hoặc token OAuth với bất kỳ ai.</p></div></div>`
        : "";
    const oauthMethods = `${oauthNotice}<section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Phương thức đăng nhập</h2><p class="portal-card-subtitle">Liên kết OAuth luôn cần signed session, CSRF và xác minh trực tiếp tại provider. Telegram Login và Bot link phải khớp cùng Telegram identity; Web không tự ghép account chỉ vì trùng email.</p></div>${badge((oauthProviders.telegram && oauthProviders.telegram.enabled) || (oauthProviders.google && oauthProviders.google.enabled) || (oauthProviders.github && oauthProviders.github.enabled) || (oauthProviders.apple && oauthProviders.apple.enabled) ? "ready" : "guarded")}</div><div class="portal-summary-list">${oauthMethodCard("telegram", "Telegram Login")}${oauthMethodCard("google", "Google (OAuth)")}${oauthMethodCard("github", "GitHub")}${oauthMethodCard("apple", "Sign in with Apple")}</div></section>`;
    const profileEditor = `<section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Tuỳ chỉnh hồ sơ Web</h2><p class="portal-card-subtitle">Chỉ cập nhật metadata Web thuộc signed session này. Telegram identity, role, Xu, PayOS và provider luôn do canonical Bot kiểm soát.</p></div>${badge(profileEnabled ? "ready" : "guarded")}</div><form class="portal-form" data-portal-form data-portal-action="update-profile" data-portal-route="/account" novalidate>${renderFields(FIELD_SETS.profile, profileEnabled, context, profileValues)}<div class="portal-form-footer"><span class="portal-form-note">Các thay đổi được audit và yêu cầu CSRF hợp lệ.</span><button class="portal-button portal-button--primary" type="submit"${profileEnabled ? "" : " disabled title=\"Cần signed session và CSRF hợp lệ.\""}>Lưu hồ sơ</button></div></form></section>`;
    const connection = context.telegramConnection && typeof context.telegramConnection === "object" ? context.telegramConnection : {};
    const botUrl = safeTelegramLink(connection.bot_chat_url || "");
    const botPreferences = [
      { command: "/language", title: "Ngôn ngữ Bot", text: "Mở lựa chọn ngôn ngữ của Bot; locale Web chỉ ảnh hưởng Portal." },
      { command: "/mode", title: "Chế độ Bot", text: "Mở mode được Bot canonical kiểm tra theo tài khoản Telegram." },
      { command: "/profile", title: "Hồ sơ Bot", text: "Xem hồ sơ canonical trong cuộc hội thoại Bot, không render dữ liệu đó ở browser." },
      { command: "/mydata", title: "Dữ liệu của tôi", text: "Dùng luồng dữ liệu của Bot khi cần; Web không xuất hoặc xóa dữ liệu Bot." },
      { command: "/data_delete", title: "Yêu cầu kiểm tra/xóa dữ liệu", text: "Khởi động yêu cầu riêng trong Bot. Bot sẽ yêu cầu xác nhận và policy canonical; Web không tự xóa account hay dữ liệu Telegram." }
    ];
    const botPreferenceCards = botPreferences.map((entry) => `<article class="portal-bot-companion-card"><div class="portal-bot-companion-card-head"><code class="portal-link-code">${safeText(entry.command)}</code>${badge("read_only")}</div><h3>${safeText(entry.title)}</h3><p>${safeText(entry.text)}</p><div class="portal-form-footer"><button class="portal-button portal-button--quiet" type="button" data-portal-action="copy-bot-companion-command" data-copy-text="${safeText(entry.command)}"${botUrl ? "" : " disabled title=\"Cần BOT_USERNAME hợp lệ để mở đúng Bot.\""}>Sao chép lệnh</button></div></article>`).join("");
    const botPreferenceHandoff = `<section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Tuỳ chọn do Bot quản lý</h2><p class="portal-card-subtitle">Ngôn ngữ, mode và dữ liệu Telegram vẫn thuộc Bot canonical. Web không giả đồng bộ hoặc gửi Telegram ID sang Bot.</p></div>${badge(botUrl ? "read_only" : "guarded")}</div>${botUrl ? `<div class="portal-notice portal-notice--info"><span class="portal-notice-icon" aria-hidden="true">⌁</span><div><strong>Mở Bot để thay đổi</strong><p>Chọn một lệnh rồi chủ động gửi trong Bot. Các lệnh này không mang theo session, identity, token hoặc dữ liệu riêng tư từ Web.</p></div><a class="portal-button portal-button--quiet" href="${safeText(botUrl)}" target="_blank" rel="noopener noreferrer">Mở Bot</a></div>` : `<div class="portal-notice"><span class="portal-notice-icon" aria-hidden="true">i</span><div><strong>Bot URL chưa sẵn sàng</strong><p>Web đang chờ <code>BOT_USERNAME</code> hợp lệ trước khi cung cấp handoff.</p></div></div>`}<section class="portal-bot-companion-grid" aria-label="Tuỳ chọn Telegram Bot">${botPreferenceCards}</section><p class="portal-form-note" style="margin-top:14px">Xóa dữ liệu, đổi quyền hay thay Telegram identity chỉ có thể được Bot xác nhận theo policy riêng. Portal chỉ sao chép một lệnh allowlist, không tạo account deletion hoặc shortcut thay đổi canonical state.</p></section>`;
    const telegramFirstAccount = profile.accountType === "telegram" && loginMethods.email !== true;
    const upgradeEnabled = context.capabilities && context.capabilities["upgrade-telegram-account"] === true;
    const upgradeValues = { ...transientFormValues("/account") };
    const telegramAccountUpgrade = telegramFirstAccount
      ? `<section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Thêm Email + mật khẩu</h2><p class="portal-card-subtitle">Tài khoản này được tạo sau khi Telegram được xác minh trên server. Bạn có thể thêm một phương thức Email + mật khẩu vào chính tài khoản đó để đăng nhập linh hoạt hơn.</p></div>${badge(upgradeEnabled ? "ready" : "guarded")}</div><form class="portal-form" data-portal-form data-portal-action="upgrade-telegram-account" data-portal-route="/account" novalidate>${renderFields(FIELD_SETS.telegramAccountUpgrade, upgradeEnabled, context, upgradeValues)}<div class="portal-form-footer"><span class="portal-form-note">Không tự ghép với tài khoản email/OAuth đã tồn tại. Email phải chưa được dùng và thao tác được audit.</span><button class="portal-button portal-button--primary" type="submit"${upgradeEnabled ? "" : " disabled title=\"Cần signed session Telegram và CSRF hợp lệ.\""}>Thêm phương thức Email</button></div></form></section>`
      : "";
    return `<article class="portal-page">${renderHero(page, context)}<div class="portal-status-grid">${renderStatusCard(page, context)}${renderSummary(page, context)}</div>
      <div class="portal-work-grid"><section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Hồ sơ & liên kết</h2><p class="portal-card-subtitle">Thông tin lấy từ signed session; browser không lưu Telegram ID, password hay token.</p></div>${badge("read_only")}</div>${accountRows}<div class="portal-form-footer"><a class="portal-button portal-button--quiet" href="/account/activity">Nhật ký hoạt động →</a><span class="portal-form-note">${linked ? "Liên kết Telegram đã được xác minh qua bot." : "Workspace Web vẫn dùng được độc lập. Liên kết Telegram là tùy chọn để mở dữ liệu wallet, jobs và assets canonical của Bot."}</span>${linked ? "" : `<a class="portal-button portal-button--primary" href="/onboarding">Liên kết Telegram</a>`}</div></section>
      <aside class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Bảo mật phiên</h2><p class="portal-card-subtitle">Logout luôn đi qua server để thu hồi session hiện tại.</p></div></div>${renderNotes(page)}<div class="portal-form-footer" style="margin-top:16px"><button class="portal-button portal-button--quiet" type="button" data-portal-action="auth-logout" data-portal-confirm="Bạn có chắc muốn đăng xuất khỏi phiên này?"${logoutEnabled ? "" : " disabled"}>Đăng xuất</button></div></aside></div>${botPreferenceHandoff}${oauthMethods}${telegramAccountUpgrade}${profileEditor}</article>`;
  }

  function accountActivityStatus(item) {
    const status = String(item && item.status || "").trim();
    return ["completed", "guarded", "read_only"].includes(status) ? status : "read_only";
  }

  function renderAccountActivity(page, context) {
    const items = Array.isArray(context.accountActivity) ? context.accountActivity.slice(0, 50) : [];
    const refreshEnabled = Boolean(context.capabilities && context.capabilities["refresh-account-activity"] === true);
    const rows = renderRowsTable(
      ["Thời gian", "Nhóm hoạt động", "Hoạt động", "Trạng thái"],
      items,
      (item) => `<td>${safeText(String(item && item.created_at || "—"))}</td><td>${safeText(String(item && item.category || "Tài khoản"))}</td><td>${safeText(String(item && item.label || "Hoạt động Web"))}</td><td>${badge(accountActivityStatus(item))}</td>`,
      "Chưa có hoạt động Web để hiển thị",
      "Nhật ký sẽ ghi các hoạt động Portal đã được server xác nhận. Không có dữ liệu Bot, Xu, PayOS, provider, ticket hoặc output nào được suy diễn ở đây."
    );
    return `<article class="portal-page portal-account-activity">${renderHero(page, context)}
      <section class="portal-card portal-card-pad portal-campaign-boundary"><div class="portal-state" data-state="read_only"><span class="portal-state-icon" aria-hidden="true">⌁</span><div><h2>Nhật ký Web riêng tư</h2><p>Đây là lịch sử đã được server sanitize của signed account hiện tại. Nó không phải audit export, Bot history, wallet ledger, lịch sử PayOS hay provider log.</p><div class="portal-state-meta"><span>Owner-scoped read</span><span>Tối đa 50 hoạt động gần nhất</span><span>Không target/detail/request ID</span></div></div></div></section>
      <section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Hoạt động gần đây</h2><p class="portal-card-subtitle">Chỉ nhãn, nhóm, trạng thái đã chuẩn hóa và thời gian được hiển thị. Browser không nhận Telegram ID, credential hay nội dung audit gốc.</p></div><div class="portal-inline-actions"><a class="portal-button portal-button--quiet" href="/account">Tài khoản</a><button class="portal-button portal-button--quiet" type="button" data-portal-action="refresh-account-activity" data-portal-route="/account/activity"${refreshEnabled ? "" : " disabled"}>Làm mới</button></div></div>${rows}</section>
      <section class="portal-card portal-card-pad"><div class="portal-notice portal-notice--info"><span class="portal-notice-icon" aria-hidden="true">i</span><div><strong>Ranh giới dữ liệu</strong><p>Nếu bạn cần lịch sử giao dịch, job, delivery hoặc ticket canonical, mở đúng Ví Xu, Job Center, Tài sản hoặc Hỗ trợ khi Core Bridge công bố dữ liệu owner-scoped tương ứng. Trang này không sao chép hoặc hợp nhất các nguồn đó.</p></div></div></section>
    </article>`;
  }

  function renderLegal(page, context) {
    const privacy = page.path === "/privacy";
    return `<article class="portal-page">${renderHero(page, context)}<section class="portal-card portal-card-pad"><div class="portal-notice portal-notice--info"><span class="portal-notice-icon" aria-hidden="true">i</span><div><strong>Khung nội dung phiên bản hóa</strong><p>${privacy ? "Chính sách chính thức cần được máy chủ phát hành cùng phiên bản và ngày hiệu lực." : "Điều khoản chính thức cần được máy chủ phát hành cùng phiên bản và ngày hiệu lực."}</p></div></div>
      <div class="portal-panel-list" style="margin-top:16px"><div class="portal-panel-row"><span class="portal-panel-row-icon">1</span><div><strong>${privacy ? "Thu thập tối thiểu" : "Sử dụng có trách nhiệm"}</strong><span>${privacy ? "Browser không nhận hoặc lưu Telegram ID, OAuth token, password, wallet ledger hay file output. Server chỉ giữ Telegram identity canonical sau xác minh Bot và HMAC-hash identity OAuth để bảo vệ signed session/Core Bridge; OAuth token bị hủy sau xác minh." : "Provider, payment, job và Xu được điều phối bởi Core Bridge canonical."}</span></div></div>
        <div class="portal-panel-row"><span class="portal-panel-row-icon">2</span><div><strong>${privacy ? "Quyền truy cập" : "Xác nhận rõ ràng"}</strong><span>${privacy ? "Dữ liệu riêng tư cần ownership và role check server-side trước khi render hoặc tải xuống." : "Flow feature sử dụng draft → estimate → confirm → queued/processing → completed/failed/guarded."}</span></div></div>
        <div class="portal-panel-row"><span class="portal-panel-row-icon">3</span><div><strong>Thông báo cập nhật</strong><span>Văn bản pháp lý đầy đủ sẽ thay thế khung này khi module content được đưa vào production.</span></div></div></div>
    </section></article>`;
  }

  function safeTelegramLink(value) {
    if (typeof value !== "string" || !value) return "";
    try {
      const url = new URL(value);
      return url.protocol === "https:" && url.hostname === "t.me" && !url.port && !url.username && !url.password ? url.href : "";
    } catch (_) {
      return "";
    }
  }

  function telegramConnectionReady(context) {
    const connection = context.telegramConnection && typeof context.telegramConnection === "object" ? context.telegramConnection : {};
    return connection.ready === true;
  }

  function telegramConnectionBlockReason(context) {
    const connection = context.telegramConnection && typeof context.telegramConnection === "object" ? context.telegramConnection : {};
    if (connection.bot_callback_adapter_enabled !== true) {
      return "Bot TOAN AAS chưa deploy adapter liên kết đã ký hoặc release gate đang tắt; khách hàng không thể tự sửa và Web không tạo mã chết.";
    }
    const missing = Array.isArray(connection.missing_configuration)
      ? connection.missing_configuration.filter((item) => typeof item === "string" && /^[A-Z0-9_]{3,80}$/.test(item)).slice(0, 4)
      : [];
    if (missing.length) return "Web đang chờ cấu hình " + missing.join(", ") + " trước khi tạo mã liên kết Telegram.";
    return "Cầu nối Telegram chưa sẵn sàng trên máy chủ; Web không tạo mã để tránh một luồng không thể hoàn tất.";
  }

  function renderTelegramConnectionNotice(context) {
    const connection = context.telegramConnection && typeof context.telegramConnection === "object" ? context.telegramConnection : {};
    if (telegramConnectionReady(context)) {
      if (connection.bot_callback_observed === true) {
        const lastKind = connection.last_valid_callback_kind === "account_link" ? "liên kết tài khoản" : "đăng nhập";
        const lastAt = typeof connection.last_valid_callback_at === "string" && connection.last_valid_callback_at.trim()
          ? ` Lần callback hợp lệ gần nhất: ${connection.last_valid_callback_at.trim().slice(0, 80)}.`
          : "";
        return `<div class="portal-notice portal-notice--info"><span class="portal-notice-icon" aria-hidden="true">✓</span><div><strong>Cầu nối Telegram đã được xác minh</strong><p>Web đã nhận callback Bot đã ký cho luồng ${safeText(lastKind)}.${safeText(lastAt)} Telegram ID không đi qua browser.</p></div></div>`;
      }
      return `<div class="portal-notice portal-notice--info"><span class="portal-notice-icon" aria-hidden="true">⌁</span><div><strong>Sẵn sàng xác minh Telegram</strong><p>Web đã có deep link và receiver ký số. Hãy tạo mã rồi xác nhận trong Bot; sau callback hợp lệ đầu tiên, Portal sẽ đánh dấu cầu nối đã được kiểm chứng. Không nhập Telegram ID vào Web.</p></div></div>`;
    }
    const missing = Array.isArray(connection.missing_configuration) ? connection.missing_configuration.filter((item) => typeof item === "string" && /^[A-Z0-9_]{3,80}$/.test(item)).slice(0, 4) : [];
    const adapterPending = connection.bot_callback_adapter_enabled !== true;
    const text = adapterPending
      ? "Bot chưa được phát hành/kích hoạt adapter liên kết đã ký. Đăng nhập Telegram OIDC có thể dùng riêng cho Web khi đã cấu hình, nhưng Xu, jobs và assets canonical vẫn khóa. Không nhập Telegram ID; chờ Bot adapter được bật rồi tạo mã một lần."
      : (missing.length
        ? `Web đang chờ cấu hình ${missing.join(", ")}. Không nhập Telegram ID; sau khi cấu hình, dùng mã một lần trong Bot.`
        : "Web chưa xác nhận được cấu hình cầu nối Telegram. Không nhập Telegram ID; hãy thử lại sau khi Bot/Web được cấu hình.");
    return `<div class="portal-notice"><span class="portal-notice-icon" aria-hidden="true">i</span><div><strong>Kết nối Telegram chưa sẵn sàng</strong><p>${safeText(text)}</p></div></div>`;
  }

  function safeOnboardingContinuation(value) {
    if (typeof value !== "string") return "";
    const route = value.trim();
    if (!route || !route.startsWith("/") || route.startsWith("//") || route.includes("\\") || route.includes("\u0000") || route.includes("?") || route.includes("#")) return "";
    const normalized = normalizePath(route);
    return ["/login", "/register", "/onboarding"].includes(normalized) ? "" : normalized;
  }

  function onboardingContinuationRoute() {
    return safeOnboardingContinuation(new URLSearchParams(window.location.search).get("next") || "");
  }

  function renderRecoveredTelegramLinkChallenge({ enabled, reason, readyToComplete, expired, message }) {
    const disabled = enabled ? "" : " disabled title=\"" + safeText(reason) + "\"";
    const heading = readyToComplete
      ? "Bot đã xác minh Telegram"
      : (expired ? "Mã liên kết đã hết hạn" : "Phiên liên kết Telegram đang chờ");
    const body = readyToComplete
      ? "Portal đang hoàn tất liên kết bằng signed session và CSRF của đúng tab đã tạo mã. Không có Telegram ID nào được trả về browser."
      : (expired
        ? "Mã một lần không còn hợp lệ. Tạo mã mới để tiếp tục; mã cũ không thể dùng lại."
        : "Tab vừa được làm mới nên Portal không hiển thị lại mã hoặc deep link. Nếu bạn đã gửi mã vào Bot, hãy chờ hoặc kiểm tra lại; nếu chưa, hãy chủ động tạo mã mới để hủy mã đang chờ.");
    const safeMessage = typeof message === "string" && message.trim() ? "<p>" + safeText(message.trim()) + "</p>" : "";
    return '<section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">' + safeText(heading) + '</h2><p class="portal-card-subtitle">' + safeText(body) + '</p>' + safeMessage + '</div>' + badge(expired ? "failed" : "awaiting_confirm") + '</div><div class="portal-form-footer"><button class="portal-button portal-button--quiet" type="button" data-portal-action="refresh-link-status" data-portal-route="/onboarding">Kiểm tra ngay</button><button class="portal-button portal-button--primary" type="button" data-portal-action="start-telegram-link" data-portal-route="/onboarding" data-portal-confirm="Tạo mã mới sẽ hủy mã Telegram đang chờ. Bạn có chắc muốn tiếp tục?"' + disabled + '>' + (expired ? "Tạo mã mới" : "Tạo mã mới và hủy mã cũ") + '</button></div></section>';
  }

  function renderOnboarding(page, context) {
    const flow = context.linkFlow && typeof context.linkFlow === "object" ? context.linkFlow : {};
    const data = flow.data && typeof flow.data === "object" ? flow.data : {};
    const status = context.linkStatus && typeof context.linkStatus === "object" ? context.linkStatus : {};
    const linked = telegramIdentityLinked(context);
    const continuation = onboardingContinuationRoute();
    const enabled = canAct(page, context);
    const reason = actionBlockReason(page, context);
    const code = typeof data.code === "string" && data.code ? data.code : "";
    const recovered = data.recovered === true && !code;
    const readyToComplete = data.ready_to_complete === true;
    const expired = data.expired === true || flow.errorCode === "LINK_CODE_INVALID";
    const deepLink = safeTelegramLink(data.deep_link);
    const botCommand = code ? `/linkweb ${code}` : "";
    const pending = recovered
      ? renderRecoveredTelegramLinkChallenge({ enabled, reason, readyToComplete, expired, message: flow.message })
      : code
      ? `<section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Xác minh trong Telegram</h2><p class="portal-card-subtitle">Mã chỉ sống trong phiên này; không được lưu trong localStorage hoặc gửi sang provider.</p></div>${badge("awaiting_confirm")}</div>
        <div class="portal-summary-list"><div class="portal-summary-item"><span class="portal-summary-key">Mã một lần</span><code class="portal-link-code">${safeText(code)}</code></div><div class="portal-summary-item"><span class="portal-summary-key">Hiệu lực</span><span class="portal-summary-value">${safeText(String(data.expires_in_minutes || "—"))} phút</span></div></div>
        <div class="portal-form-footer"><span class="portal-form-note">Mở bot TOAN AAS bằng deep link. Nếu Telegram không mở được từ trình duyệt này, sao chép lệnh dự phòng rồi gửi vào Bot. Khi quay lại tab này, Portal tự kiểm tra callback đã ký; nút bên cạnh chỉ để kiểm tra ngay. Bot là authority duy nhất xác minh Telegram identity.</span>${deepLink ? `<a class="portal-button portal-button--primary" href="${safeText(deepLink)}" target="_blank" rel="noopener noreferrer">Mở Telegram</a>` : ""}<button class="portal-button portal-button--quiet" type="button" data-portal-action="copy-telegram-link-command" data-copy-text="${safeText(botCommand)}">Sao chép lệnh</button><button class="portal-button portal-button--quiet" type="button" data-portal-action="refresh-link-status" data-portal-route="/onboarding"${enabled ? "" : ` disabled title="${safeText(reason)}"`}>Kiểm tra ngay</button><button class="portal-button portal-button--quiet" type="button" data-portal-action="start-telegram-link" data-portal-route="/onboarding" data-portal-confirm="Tạo mã mới sẽ hủy mã đang hiển thị. Bạn có chắc muốn tiếp tục?"${enabled ? "" : ` disabled title="${safeText(reason)}"`}>Tạo mã mới</button></div>
      </section>`
      : `<section class="portal-card portal-card-pad">${renderEmpty("Chưa có mã liên kết", "Tạo mã một lần, sau đó xác minh trong bot TOAN AAS. Browser không nhận Telegram ID hoặc token thô.", "⌁")}<div class="portal-form-footer"><span class="portal-form-note">Mã sẽ được Web tạo cho signed session hiện tại, có hạn dùng ngắn và chỉ Bot đang mở của bạn mới có thể xác nhận.</span><button class="portal-button portal-button--primary" type="button" data-portal-action="start-telegram-link" data-portal-route="/onboarding"${enabled ? "" : ` disabled title="${safeText(reason)}"`}>Tạo mã liên kết Telegram</button></div></section>`;
    const continuationNotice = continuation
      ? `<div class="portal-notice portal-notice--info portal-onboarding-continuation"><span class="portal-notice-icon" aria-hidden="true">↗</span><div><strong>Workflow đang chờ</strong><p>Sau khi Bot xác minh Telegram, Portal sẽ mở lại workflow bạn đã chọn.</p></div></div>`
      : "";
    const completed = `<section class="portal-card portal-card-pad"><div class="portal-state" data-state="completed"><span class="portal-state-icon" aria-hidden="true">✓</span><div><h2>Telegram đã liên kết</h2><p>Phiên Web có thể đọc dữ liệu canonical qua Core Bridge. Xu, PayOS, job và provider vẫn do bot điều phối.</p><div class="portal-state-meta"><span>Identity canonical đã xác minh</span><span>Không lưu Telegram ID ở browser</span></div></div></div><div class="portal-form-footer"><a class="portal-button portal-button--primary" href="${safeText(continuation || "/dashboard")}">${continuation ? "Mở lại workflow" : "Vào Dashboard"}</a></div></section>`;
    return `<article class="portal-page">${renderHero(page, context)}<div class="portal-status-grid">${renderStatusCard(page, context)}${renderSummary(page, context)}</div>
      ${continuationNotice}${linked ? completed : `${renderTelegramConnectionNotice(context)}${pending}`}
      <section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Cách hoạt động</h2><p class="portal-card-subtitle">Luồng liên kết không lặp lại webhook hoặc PayOS.</p></div></div><div class="portal-panel-list"><div class="portal-panel-row"><span class="portal-panel-row-icon">1</span><div><strong>Tạo mã một lần</strong><span>Web server tạo, băm và đặt hạn dùng cho mã liên kết.</span></div></div><div class="portal-panel-row"><span class="portal-panel-row-icon">2</span><div><strong>Xác nhận trong bot</strong><span>Bot xác minh Telegram identity và gọi callback nội bộ đã ký.</span></div></div><div class="portal-panel-row"><span class="portal-panel-row-icon">3</span><div><strong>Quay lại portal</strong><span>Portal kiểm tra trạng thái signed session; không tự nhận quyền từ dữ liệu browser.</span></div></div></div></section></article>`;
  }

  function renderPublicOAuthCard(provider, label, enabled, icon, purpose) {
    const registration = purpose === "register";
    const isApple = provider === "apple";
    const isTelegram = provider === "telegram";
    if (isTelegram) label = label + " (chỉ truy cập Web)";
    const actionLabel = isApple
      ? "Sign in with Apple"
      : (isTelegram
        ? "Đăng nhập bằng Telegram"
        : `${registration ? "Tạo hoặc tiếp tục với" : "Tiếp tục với"} ${label}`);
    const description = enabled
      ? (registration
        ? (isTelegram
          ? "Telegram Login xác minh tại Telegram và tạo signed Web session. Sau đó bạn xác nhận cùng tài khoản trong Bot để mở Xu, jobs và assets canonical."
          : "Sau khi xác nhận tại provider, Web sẽ tạo tài khoản lần đầu hoặc mở đúng tài khoản OAuth hiện có. Token không được trả về browser.")
        : (isTelegram
          ? "Telegram Login được xác minh bằng OIDC trên server. Sau đó, Web vẫn yêu cầu Bot xác nhận cùng identity trước khi đọc dữ liệu canonical."
          : "OAuth server đã được cấu hình. Sau khi xác nhận tại provider, Web tạo signed session; token không được trả về browser."))
      : "OAuth chưa được cấu hình trên server nên nút được giữ khóa; không có đăng nhập giả.";
    const continuation = onboardingContinuationRoute();
    const startPath = `/api/v1/auth/oauth/${safeText(provider)}/start${continuation ? `?next=${encodeURIComponent(continuation)}` : ""}`;
    return `<div class="portal-notice${enabled ? " portal-notice--info" : ""}" style="margin-top:10px">${icon ? `<span class="portal-notice-icon" aria-hidden="true">${icon}</span>` : ""}<div><strong>${safeText(label)}</strong><p>${description}</p><div class="portal-form-footer" style="margin-top:10px">${enabled ? `<a class="portal-button portal-button--quiet" href="${startPath}">${safeText(actionLabel)}</a>` : `<button class="portal-button portal-button--quiet" type="button" disabled title="Cần OAuth client, secret và callback URL trên server">${safeText(actionLabel)}</button>`}</div></div></div>`;
  }

  function renderExpiredTelegramLoginChallenge(message, connectionDisabled) {
    const detail = typeof message === "string" && message.trim()
      ? message.trim()
      : "Mã một lần không còn hợp lệ và không được hiển thị lại. Hãy tạo mã mới trong chính tab này.";
    return '<div class="portal-notice"><span class="portal-notice-icon" aria-hidden="true">i</span><div><strong>Mã đăng nhập Telegram đã hết hạn</strong><p>' + safeText(detail) + '</p><div class="portal-form-footer" style="margin-top:10px"><button class="portal-button portal-button--quiet" type="button" data-portal-action="start-telegram-login" data-portal-route="/login"' + connectionDisabled + '>Tạo mã mới</button></div></div></div>';
  }

  function renderTelegramLoginMethod(context) {
    const flow = context.telegramLoginFlow && typeof context.telegramLoginFlow === "object" ? context.telegramLoginFlow : {};
    const data = flow.data && typeof flow.data === "object" ? flow.data : {};
    const code = typeof data.code === "string" ? data.code : "";
    const deepLink = safeTelegramLink(data.deep_link);
    const ready = data.ready === true;
    const recovered = data.recovered === true && !code;
    const expired = data.expired === true || flow.errorCode === "TELEGRAM_LOGIN_EXPIRED";
    const oauthProviders = context.oauthProviders && typeof context.oauthProviders === "object" ? context.oauthProviders : {};
    const telegramOidcEnabled = oauthProviders.telegram && oauthProviders.telegram.enabled === true;
    const googleEnabled = oauthProviders.google && oauthProviders.google.enabled === true;
    const githubEnabled = oauthProviders.github && oauthProviders.github.enabled === true;
    const appleEnabled = oauthProviders.apple && oauthProviders.apple.enabled === true;
    const connectionNotice = renderTelegramConnectionNotice(context);
    const connectionReady = telegramConnectionReady(context);
    const connectionDisabled = connectionReady ? "" : " disabled title=\"" + safeText(telegramConnectionBlockReason(context)) + "\"";
    const accountRequired = flow.errorCode === "TELEGRAM_LOGIN_ACCOUNT_REQUIRED" || data.restart_required === true;
    const botCommand = code ? `/linkweb ${code}` : "";
    const pending = accountRequired
      ? `<div class="portal-notice"><span class="portal-notice-icon" aria-hidden="true">i</span><div><strong>Telegram chưa liên kết với Web App</strong><p>${safeText(flow.message || "Hãy đăng ký/đăng nhập bằng email, liên kết Telegram trong Thiết lập tài khoản, rồi tạo mã đăng nhập mới.")}</p><div class="portal-form-footer" style="margin-top:10px"><a class="portal-button portal-button--quiet" href="/register">Tạo tài khoản</a><a class="portal-button portal-button--quiet" href="/login">Đăng nhập email</a></div></div></div>`
      : expired
      ? renderExpiredTelegramLoginChallenge(flow.message, connectionDisabled)
      : code
      ? `<div class="portal-notice portal-notice--info"><span class="portal-notice-icon" aria-hidden="true">⌁</span><div><strong>Xác minh Telegram</strong><p>Không nhập Telegram ID vào Web. Mở Bot bằng deep link; nếu trình duyệt không mở Telegram thì sao chép lệnh dự phòng. Khi quay lại tab này, Portal tự kiểm tra mã browser-bound đã ký.</p><div class="portal-form-footer" style="margin-top:10px"><code class="portal-link-code">${safeText(code)}</code>${deepLink ? `<a class="portal-button portal-button--quiet" href="${safeText(deepLink)}" target="_blank" rel="noopener noreferrer">Mở Telegram</a>` : ""}<button class="portal-button portal-button--quiet" type="button" data-portal-action="copy-telegram-link-command" data-copy-text="${safeText(botCommand)}">Sao chép lệnh</button><button class="portal-button portal-button--quiet" type="button" data-portal-action="refresh-telegram-login" data-portal-route="/login">${ready ? "Hoàn tất đăng nhập" : "Kiểm tra ngay"}</button></div></div></div>`
      : recovered
      ? `<div class="portal-notice portal-notice--info"><span class="portal-notice-icon" aria-hidden="true">⌁</span><div><strong>Phiên xác minh Telegram đang chờ</strong><p>Tab vừa được làm mới nên Portal không hiển thị lại mã một lần. Browser vẫn chỉ kiểm tra challenge HttpOnly của chính tab này; nếu bạn đã xác nhận trong Bot, Portal sẽ tự hoàn tất.</p><div class="portal-form-footer" style="margin-top:10px"><button class="portal-button portal-button--quiet" type="button" data-portal-action="refresh-telegram-login" data-portal-route="/login">${ready ? "Hoàn tất đăng nhập" : "Kiểm tra ngay"}</button><button class="portal-button portal-button--quiet" type="button" data-portal-action="start-telegram-login" data-portal-route="/login" data-portal-confirm="Tạo mã mới sẽ thay thế challenge đang chờ. Bạn có chắc muốn tiếp tục?"${connectionDisabled}>Tạo mã mới</button></div></div></div>`
      : `<div class="portal-notice"><span class="portal-notice-icon" aria-hidden="true">⌁</span><div><strong>Telegram</strong><p>Đăng nhập bằng chính tài khoản Telegram đang mở Bot. Bot chứng minh ownership; Web không nhận Telegram ID thô. Lần đầu có thể tự tạo hồ sơ Web mặc định sau xác minh.</p><div class="portal-form-footer" style="margin-top:10px"><button class="portal-button portal-button--quiet" type="button" data-portal-action="start-telegram-login" data-portal-route="/login"${connectionDisabled}>Đăng nhập với Telegram</button></div></div></div>`;
    return `<section class="portal-auth-provider"><div class="portal-card-header"><div><h3 class="portal-card-title">Cách đăng nhập khác</h3><p class="portal-card-subtitle">Email + mật khẩu (có thể dùng Gmail) dùng form ở trên. Telegram Login xác thực Web bằng OIDC; liên kết Bot là tùy chọn và chỉ cần khi bạn muốn đồng bộ Xu, jobs hoặc assets canonical.</p></div></div>${renderPublicOAuthCard("telegram", "Telegram Login", telegramOidcEnabled, "✈", "signin")}${connectionNotice}${pending}${renderPublicOAuthCard("google", "Google (OAuth)", googleEnabled, "G", "signin")}${renderPublicOAuthCard("github", "GitHub", githubEnabled, "◎", "signin")}${renderPublicOAuthCard("apple", "Sign in with Apple", appleEnabled, "", "signin")}</section>`;
  }

  function renderOAuthRegistrationMethods(context) {
    const providers = context.oauthProviders && typeof context.oauthProviders === "object" ? context.oauthProviders : {};
    const telegramOidcEnabled = providers.telegram && providers.telegram.enabled === true;
    const googleEnabled = providers.google && providers.google.enabled === true;
    const githubEnabled = providers.github && providers.github.enabled === true;
    const appleEnabled = providers.apple && providers.apple.enabled === true;
    return `<section class="portal-auth-provider"><div class="portal-card-header"><div><h3 class="portal-card-title">Tạo hoặc tiếp tục với OAuth</h3><p class="portal-card-subtitle">Telegram Login tạo signed Web session từ profile Telegram đã ký. Workspace Web hoạt động ngay với signed session; liên kết Bot chỉ là tùy chọn để mở dữ liệu canonical. Các OAuth khác không tự ghép chỉ vì trùng email.</p></div></div>${renderPublicOAuthCard("telegram", "Telegram Login", telegramOidcEnabled, "✈", "register")}${renderPublicOAuthCard("google", "Google (OAuth)", googleEnabled, "G", "register")}${renderPublicOAuthCard("github", "GitHub", githubEnabled, "◎", "register")}${renderPublicOAuthCard("apple", "Sign in with Apple", appleEnabled, "", "register")}</section>`;
  }

  function renderAuth(page, context) {
    const alternative = page.path === "/login" ? ["/register", "Tạo tài khoản"] : ["/login", "Đăng nhập"];
    const enabled = canAct(page, context);
    const reason = actionBlockReason(page, context);
    const registrationHandoff = page.path === "/login" && new URLSearchParams(window.location.search).get("registered") === "1"
      ? `<div class="portal-notice portal-notice--info"><span class="portal-notice-icon" aria-hidden="true">i</span><div><strong>Tiếp tục bằng đăng nhập</strong><p>Nếu email vừa gửi chưa có tài khoản, hồ sơ đã được tạo. Đăng nhập để khởi tạo signed session và dùng Workspace Web; Telegram có thể liên kết sau nếu cần đồng bộ Bot.</p></div></div>`
      : "";
    const oauthReason = page.path === "/login" || page.path === "/account" ? new URLSearchParams(window.location.search).get("oauth") || "" : "";
    const oauthMessages = {
      unavailable: "OAuth chưa được cấu hình trên server.",
      cancelled: "Bạn đã hủy xác minh tại nhà cung cấp.",
      failed: "Không thể xác minh OAuth. Hãy thử lại mà không chia sẻ mã hay token với bất kỳ ai.",
      state: "Phiên OAuth không hợp lệ hoặc đã hết hạn. Hãy bắt đầu lại từ Web App.",
      session: "Signed session đã thay đổi trong khi liên kết OAuth. Hãy đăng nhập lại rồi thử lại.",
      "link-required": "Email này đã có tài khoản Web. Hãy đăng nhập bằng phương thức hiện có, sau đó liên kết OAuth trong trang Tài khoản.",
      linked: "Đã liên kết OAuth với signed session hiện tại.",
      "already-linked": "OAuth này đã liên kết với tài khoản hiện tại."
    };
    const oauthHandoff = oauthMessages[oauthReason]
      ? `<div class="portal-notice${["linked", "already-linked"].includes(oauthReason) ? " portal-notice--info" : ""}"><span class="portal-notice-icon" aria-hidden="true">${["linked", "already-linked"].includes(oauthReason) ? "✓" : "i"}</span><div><strong>OAuth</strong><p>${safeText(oauthMessages[oauthReason])}</p></div></div>`
      : "";
    const registerSetup = page.path === "/register"
      ? `<div class="portal-notice portal-notice--info"><span class="portal-notice-icon" aria-hidden="true">i</span><div><strong>Hồ sơ mặc định sau khi tạo</strong><p>Locale Tiếng Việt · múi giờ Asia/Ho_Chi_Minh · avatar gradient. Email + mật khẩu (có thể dùng Gmail) đang hoạt động. Telegram Login dùng OIDC khi server đã cấu hình; Bot vẫn xác minh cùng identity trước khi mở dữ liệu canonical. Không nhập ID Telegram thô. Telegram Login, Google OAuth, GitHub OAuth và Sign in with Apple chỉ mở khi server có cấu hình thật.</p></div></div>`
      : "";
    return `<article class="portal-auth-page"><a class="portal-auth-brand" href="/welcome" aria-label="Xem giới thiệu TOAN AAS"><span class="portal-brand-mark" aria-hidden="true">TA</span><span><strong>TOAN AAS</strong><small>AI workspace · secure access</small></span><em>← Giới thiệu</em></a><section class="portal-auth-intro"><div class="portal-eyebrow">TOAN AAS · secure access</div><h1 class="portal-title">${safeText(displayPageTitle(page, context))}</h1><p class="portal-description">${safeText(page.description)}</p>
      <div class="portal-auth-facts"><div class="portal-auth-fact"><strong>Signed session</strong><span>Cookie/session do server quản lý, không dùng raw localStorage.</span></div><div class="portal-auth-fact"><strong>Telegram link</strong><span>Mã dùng một lần, hết hạn và chống replay.</span></div><div class="portal-auth-fact"><strong>CSRF</strong><span>Mọi thao tác ghi sau đăng nhập phải có CSRF hợp lệ.</span></div><div class="portal-auth-fact"><strong>Rate limit</strong><span>Login/register được giới hạn tại Web server; Core Bridge chỉ nhận yêu cầu đã xác thực.</span></div></div>
    </section><section class="portal-card portal-card-pad portal-auth-card"><div class="portal-card-header"><div><h2 class="portal-card-title">${safeText(page.title)}</h2><p class="portal-card-subtitle">${enabled ? "Endpoint đã được server cấp khả năng." : safeText(reason)}</p></div>${badge(stateFor(page, context))}</div>
      ${registerSetup}${registrationHandoff}${oauthHandoff}<div class="portal-auth-notes">${renderNotes(page)}</div><form class="portal-form" data-portal-form data-portal-action="${safeText(page.action)}" data-portal-route="${safeText(page.path)}" novalidate>${renderFields(page.fields, enabled, context, transientFormValues(page.path))}<div class="portal-form-footer"><a class="portal-button portal-button--quiet" href="${alternative[0]}">${alternative[1]} →</a><button class="portal-button portal-button--primary" type="submit"${enabled ? "" : ` disabled title="${safeText(reason)}"`}>${safeText(page.actionLabel)}</button></div></form>
      ${page.path === "/login" ? renderTelegramLoginMethod(context) : renderOAuthRegistrationMethods(context)}
      <div class="portal-notice" style="margin-top:16px"><span class="portal-notice-icon" aria-hidden="true">⌁</span><div><strong>Không có đăng nhập giả</strong><p>Giao diện không tạo session, không lưu mật khẩu và không tự đăng nhập người dùng.</p></div></div>
    </section></article>`;
  }

  const RESULT_LABELS = Object.freeze({
    title: "Tiêu đề", topic: "Chủ đề", prompt: "Prompt", meta_prompts: "Các prompt",
    captions: "Caption", hook: "Hook", hooks: "Hook", body: "Nội dung", cta: "CTA",
    hashtags: "Hashtag", video_ideas: "Ý tưởng video", post_ideas: "Ý tưởng bài đăng",
    recommended_first: "Hướng nên làm trước", image_video_prompts: "Prompt ảnh/video",
    variants: "Biến thể", script_15s: "Kịch bản 15 giây", script_30s: "Kịch bản 30 giây",
    shots: "Danh sách cảnh", shot: "Cảnh", shot_count: "Số cảnh", image_prompt: "Prompt ảnh",
    video_prompt: "Prompt video", scene_goal: "Mục tiêu cảnh", main_action: "Hành động chính",
    estimated_xu: "Ước tính", pricing_rule: "Quy tắc giá", choices: "Các gói canonical", tier_required: "Cần chọn tier", scene_count_required: "Cần số cảnh",
    label: "Tên gói", cost_xu: "Giá", note: "Ghi chú", source: "Nguồn canonical",
    display_name: "Tên hiển thị", sample_staged: "Mẫu âm thanh đã staging", consent_confirmed: "Đã xác nhận quyền sử dụng", next_step: "Bước tiếp theo",
    mode: "Chế độ", target_language: "Ngôn ngữ đích", output_format: "Định dạng đầu ra", voice_speed: "Tốc độ giọng",
    ready: "Sẵn sàng", missing: "Điều kiện còn thiếu", mux: "Mux", capability: "Khả năng canonical",
    operation: "Thao tác", page_count: "Số trang", local_tool_status: "Trạng thái công cụ", duration_seconds: "Thời lượng",
    product_kind: "Loại sản phẩm", billing: "Chi tiết tính phí", invoice: "Hoá đơn ước tính", processing_quote: "Ước tính xử lý", tts_quote: "Ước tính TTS",
    name: "Tên gợi ý", mood: "Cảm xúc", tempo: "Nhịp độ", instrument: "Nhạc cụ", duration: "Thời lượng", vocal: "Giọng hát", use_case: "Mục đích sử dụng",
    copyright_safe_request: "Yêu cầu an toàn bản quyền", search_ready: "Sẵn sàng tìm kiếm", provider_search_required: "Cần adapter thư viện"
  });

  // A feature workspace never guesses which row in Job Center belongs to a
  // request. The only valid deep link is an explicit, redacted bridge
  // tracking reference returned after a canonical confirm.
  const FEATURE_TRACKING_JOB_STATES = new Set([
    "queued", "processing", "completed", "failed", "failed_no_charge", "cancelled", "refunded"
  ]);
  const FEATURE_TRACKING_ID_PATTERN = /^[A-Za-z0-9._:-]{1,160}$/;
  const FEATURE_TRACKING_KEY_PATTERN = /^[a-z][a-z0-9_]{1,120}$/;

  function resultLabel(key) {
    return RESULT_LABELS[key] || String(key || "Dữ liệu").replace(/_/g, " ");
  }

  function renderCanonicalValue(value, depth) {
    const level = Number(depth || 0);
    if (value === null || value === undefined || value === "") return "<span class=\"portal-result-empty\">—</span>";
    if (typeof value === "boolean") return `<span>${value ? "Có" : "Không"}</span>`;
    if (typeof value === "number") return `<span>${safeText(String(value))}</span>`;
    if (typeof value === "string") {
      const text = safeText(value);
      return value.includes("\n") || value.length > 160
        ? `<div class="portal-result-text">${text}</div>`
        : `<span>${text}</span>`;
    }
    if (level >= 3) return `<span>${safeText(JSON.stringify(value).slice(0, 500))}</span>`;
    if (Array.isArray(value)) {
      if (!value.length) return "<span class=\"portal-result-empty\">Chưa có dữ liệu</span>";
      return `<ol class="portal-result-list">${value.slice(0, 8).map((item) => `<li>${renderCanonicalValue(item, level + 1)}</li>`).join("")}</ol>`;
    }
    if (typeof value === "object") {
      const entries = Object.entries(value).filter(([key]) => !["available", "provider_called", "charged_xu", "requires_confirm"].includes(key)).slice(0, 14);
      return `<div class="portal-result-grid">${entries.map(([key, item]) => `<section class="portal-result-item"><strong>${safeText(resultLabel(key))}</strong>${renderCanonicalValue(item, level + 1)}</section>`).join("")}</div>`;
    }
    return `<span>${safeText(String(value))}</span>`;
  }

  function canonicalDraftText(value) {
    if (typeof value !== "string") return "";
    const text = value.replace(/\u0000/g, "").trim();
    return text && text.length <= 2_000 ? text : "";
  }

  function featureDraftTarget(flow, route) {
    const feature = String(flow && flow.feature || "").trim();
    const page = manifest[normalizePath(route)] || {};
    const names = Array.isArray(page.fields) ? page.fields.map((field) => String(field && field.name || "")) : [];
    const preferred = feature.startsWith("image_") ? ["prompt", "instructions"]
      : feature.startsWith("video_") ? ["brief", "script", "prompt"]
      : feature.startsWith("music_") ? ["brief", "prompt"]
      : feature.startsWith("voice_") ? ["text", "script"]
      : feature.startsWith("subtitle_") || feature === "video_dub" ? ["script", "instructions"]
      : ["request", "prompt", "brief", "script"];
    const field = preferred.find((name) => names.includes(name)) || names.find((name) => /^(request|prompt|brief|script|text|instructions)$/.test(name)) || "";
    return /^[a-z][a-z0-9_]{0,80}$/.test(field) ? field : "";
  }

  function canonicalDraftActions(text, route, field, label) {
    const content = canonicalDraftText(text);
    const targetRoute = normalizePath(route || "");
    if (!content || !targetRoute.startsWith("/") || !field) return "";
    return `<div class="portal-canonical-actions"><button class="portal-button portal-button--quiet" type="button" data-portal-action="copy-canonical-draft" data-canonical-text="${safeText(content)}">Sao chép ${safeText(label || "nội dung")}</button><button class="portal-button portal-button--primary" type="button" data-portal-action="apply-canonical-draft" data-canonical-text="${safeText(content)}" data-canonical-route="${safeText(targetRoute)}" data-canonical-field="${safeText(field)}">Dùng trong form</button></div>`;
  }

  function canonicalPreferredText(content) {
    if (!content || typeof content !== "object" || Array.isArray(content)) return "";
    for (const key of ["prompt", "script", "video_prompt", "image_prompt", "script_30s", "script_15s", "recommended_first"]) {
      const candidate = canonicalDraftText(content[key]);
      if (candidate) return candidate;
    }
    const suggestions = Array.isArray(content.suggestions) ? content.suggestions : [];
    return canonicalDraftText(suggestions[0] && suggestions[0].prompt);
  }

  function renderCanonicalSuggestions(value, route, field) {
    if (!Array.isArray(value) || !value.length) return "";
    const cards = value.slice(0, 3).map((raw, index) => {
      const item = raw && typeof raw === "object" ? raw : {};
      const prompt = canonicalDraftText(item.prompt);
      const meta = [
        ["Mood", item.mood], ["Tempo", item.tempo], ["Nhạc cụ", item.instrument],
        ["Thời lượng", item.duration], ["Giọng", item.vocal], ["Dùng cho", item.use_case]
      ].filter(([, text]) => typeof text === "string" && text.trim());
      return `<article class="portal-suggestion-card"><div class="portal-suggestion-card-head"><strong>${safeText(String(item.name || `Gợi ý ${index + 1}`))}</strong><span>Canonical planning</span></div>${meta.length ? `<dl class="portal-suggestion-meta">${meta.map(([label, text]) => `<div><dt>${safeText(label)}</dt><dd>${safeText(String(text))}</dd></div>`).join("")}</dl>` : ""}${prompt ? `<div class="portal-result-text">${safeText(prompt)}</div>${canonicalDraftActions(prompt, route, field, "prompt")}` : ""}</article>`;
    }).join("");
    return `<section class="portal-canonical-suggestions"><div class="portal-section-heading"><div><span class="portal-section-kicker">Gợi ý canonical</span><h4>Chọn một hướng planning</h4><p>Các gợi ý do helper Bot phát hành, chưa gọi provider và chưa tạo asset/job.</p></div></div><div class="portal-suggestion-grid">${cards}</div></section>`;
  }

  function renderCanonicalFlow(flow, route) {
    const data = flow && flow.data && typeof flow.data === "object" ? flow.data : {};
    const payload = data.draft || data.estimate;
    if (!payload || typeof payload !== "object") return "";
    if (payload.available === false) {
      return `<div class="portal-notice"><span class="portal-notice-icon" aria-hidden="true">i</span><div><strong>Adapter chi tiết đang được bảo vệ</strong><p>${safeText(payload.reason || "Core Bridge đã nhận input nhưng chưa có helper canonical cho bước này.")}</p></div></div>`;
    }
    const content = payload.content || payload;
    const heading = data.draft ? "Bản nháp canonical" : "Ước tính canonical";
    const selectedFormat = payload.feature === "image_create" && flow && flow.input && typeof flow.input === "object" ? String(flow.input.format || "").trim() : "";
    const selectionRequired = data.estimate && (data.estimate.tier_required === true || data.estimate.scene_count_required === true);
    const selectionNotice = selectionRequired
      ? `<div class="portal-notice portal-notice--info"><span class="portal-notice-icon" aria-hidden="true">i</span><div><strong>Cần chọn cấu hình canonical trước khi xác nhận</strong><p>Bot đã trả lựa chọn quote nhưng chưa có tier hoặc số cảnh đủ để tạo receipt xác nhận. Chọn cấu hình trong form rồi ước tính lại; Portal không tự chọn giá trị thay bạn.</p></div></div>`
      : "";
    const preference = selectedFormat
      ? `<div class="portal-notice portal-notice--info"><span class="portal-notice-icon" aria-hidden="true">i</span><div><strong>Ưu tiên tỷ lệ bạn chọn: ${safeText(selectedFormat)}</strong><p>Đây là preference của request. Bản nháp P0 chưa chứng minh engine đã dùng tỷ lệ này; chỉ gợi ý canonical trong draft mới được hiển thị ở bên dưới.</p></div></div>`
      : "";
    const targetField = featureDraftTarget(flow, route);
    const preferred = canonicalPreferredText(content);
    const genericContent = content && typeof content === "object" && !Array.isArray(content)
      ? Object.entries(content).reduce((result, [key, value]) => {
        if (key !== "suggestions") result[key] = value;
        return result;
      }, Object.create(null))
      : content;
    const suggestions = content && typeof content === "object" && !Array.isArray(content) ? content.suggestions : [];
    const applyAction = canonicalDraftActions(preferred, route, targetField, "planning");
    return `<section class="portal-canonical-result"><div class="portal-card-header"><div><h3 class="portal-card-title">${heading}</h3><p class="portal-card-subtitle">Nguồn: ${safeText(payload.source || "canonical_bot")} · Chưa gọi provider · Chưa trừ Xu.</p></div>${badge(flow.status || "draft")}</div>${selectionNotice}${preference}${renderCanonicalValue(genericContent, 0)}${renderCanonicalSuggestions(suggestions, route, targetField)}${applyAction}</section>`;
  }

  function safeFeatureTracking(flow) {
    const data = flow && flow.data && typeof flow.data === "object" ? flow.data : {};
    const tracking = data.tracking && typeof data.tracking === "object" ? data.tracking : {};
    const id = String(tracking.id || "").trim();
    const status = String(tracking.status || "").trim().toLowerCase();
    const feature = String(tracking.feature || "").trim();
    const expectedFeature = String(flow && flow.feature || "").trim();
    const flowStatus = String(flow && flow.status || "").trim().toLowerCase();
    if (
      !FEATURE_TRACKING_ID_PATTERN.test(id)
      || !FEATURE_TRACKING_KEY_PATTERN.test(feature)
      || feature !== expectedFeature
      || !FEATURE_TRACKING_JOB_STATES.has(status)
      || flowStatus !== status
    ) return null;
    return { id, status, feature };
  }

  function renderFeatureTracking(flow) {
    if (!flow || flow.phase !== "confirm" || !FEATURE_TRACKING_JOB_STATES.has(String(flow.status || "").toLowerCase())) return "";
    const tracking = safeFeatureTracking(flow);
    if (!tracking) {
      return `<section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h3 class="portal-card-title">Theo dõi công việc</h3><p class="portal-card-subtitle">Bridge chưa cấp mã job xác thực cho request này.</p></div>${badge("guarded")}</div><div class="portal-notice"><span class="portal-notice-icon" aria-hidden="true">i</span><div><strong>Không ghép job theo thời gian hoặc tên feature</strong><p>Portal không suy đoán một job thuộc request hiện tại. Bạn vẫn có thể mở Job Center để xem các job canonical thuộc signed session.</p></div></div><div class="portal-form-footer"><a class="portal-button portal-button--quiet" href="/jobs">Mở Job Center</a></div></section>`;
    }
    const href = `/jobs/${encodeURIComponent(tracking.id)}`;
    return `<section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h3 class="portal-card-title">Theo dõi công việc</h3><p class="portal-card-subtitle">Mã job được Core Bridge cấp rõ ràng cho chính request đã xác nhận.</p></div>${badge(tracking.status)}</div><div class="portal-summary-list"><div class="portal-summary-item"><span class="portal-summary-key">Job canonical</span><code class="portal-link-code">${safeText(tracking.id)}</code></div><div class="portal-summary-item"><span class="portal-summary-key">Trạng thái</span><span class="portal-summary-value">${safeText(STATE_LABELS[tracking.status] || tracking.status)}</span></div></div><div class="portal-form-footer"><span class="portal-form-note">Job detail tiếp tục kiểm tra ownership qua signed session; Web không dùng ID này để cấp file, Xu hoặc quyền provider.</span><a class="portal-button portal-button--primary" href="${safeText(href)}">Theo dõi job</a></div></section>`;
  }

  function renderFeatureBotHandoff(page, context, flow) {
    // Planning may be available before an execution adapter is approved. The
    // default next step is Web authoring, not Telegram. A Bot companion stays
    // available as a clearly optional, no-data handoff for existing customers.
    const executionReady = featureConfirmExecutionReady(page, context);
    const flowGuarded = Boolean(flow && ["guarded", "failed"].includes(String(flow.status || "").toLowerCase()));
    if (page.type !== "feature" || (executionReady && !flowGuarded)) return "";
    const connection = context.telegramConnection && typeof context.telegramConnection === "object" ? context.telegramConnection : {};
    const botUrl = safeTelegramLink(connection.bot_chat_url || "");
    const feature = featureKeyForPage(page, context) || "workflow";
    const handoff = FEATURE_BOT_HANDOFFS[feature] || null;
    const handoffCommand = handoff ? handoff.command : "/menu";
    const handoffLabel = handoff ? handoff.label : "Mở Bot menu";
    const title = flowGuarded ? "Integration đang được bảo vệ" : "Engine Web chưa bật";
    const explanation = flowGuarded
      ? "Yêu cầu này không được chuyển sang engine. Bạn vẫn có thể tiếp tục soạn và lưu brief trong Web Workspace."
      : "Web App chưa có Engine Web được phê duyệt cho workflow này. Bạn vẫn có thể lưu brief, Project và Studio Document; không có job hay output nào được tạo.";
    const handoffNote = handoff
      ? `Nếu bạn đã dùng Bot, đây chỉ là companion tùy chọn mở <code>${safeText(handoffCommand)}</code>; không truyền prompt, upload ID, Telegram ID, quote, Xu, session hoặc token.`
      : "Bot companion không có command khởi động riêng cho workflow này. Không truyền prompt, upload ID, Telegram ID, quote, Xu, session hoặc token.";
    const companion = botUrl
      ? `<div class="portal-form-footer"><span class="portal-form-note"><strong>Bot companion (tùy chọn).</strong> ${handoffNote}</span><a class="portal-button portal-button--quiet" href="${safeText(botUrl)}" target="_blank" rel="noopener noreferrer">Mở Bot companion</a><button class="portal-button portal-button--quiet" type="button" data-portal-action="copy-bot-companion-command" data-copy-text="${safeText(handoffCommand)}">${safeText(handoffLabel)}</button></div>`
      : `<p class="portal-form-note">Bot companion chưa được cấu hình. Điều này không ảnh hưởng Project, Studio Document hoặc bản nháp Web.</p>`;
    return `<section class="portal-card portal-card-pad" data-feature-bot-handoff><div class="portal-card-header"><div><h2 class="portal-card-title">${safeText(title)}</h2><p class="portal-card-subtitle">${safeText(explanation)}</p></div>${badge("guarded")}</div><div class="portal-summary-list"><div class="portal-summary-item"><span class="portal-summary-key">Workflow Web</span><span class="portal-summary-value">${safeText(feature)}</span></div><div class="portal-summary-item"><span class="portal-summary-key">Dữ liệu gửi sang companion</span><span class="portal-summary-value">Không có</span></div></div><div class="portal-form-footer"><a class="portal-button portal-button--primary" href="/projects">Mở Project Center</a></div>${companion}</section>`;
  }

  function renderWorkspace(page, context) {
    const route = page.routePath || page.path;
    const contentStudioKindForFeaturePath = {
      "/content/caption": "caption_hashtag", "/content/hashtag": "caption_hashtag",
      "/content/hook": "hook_script", "/content/script": "hook_script",
      "/content/storyboard": "storyboard", "/content/pack": "content_pack"
    };
    const contentStudioKind = contentStudioKindForFeaturePath[page.path] || "";
    const contentStudioLink = contentStudioKind
      ? `<div class="portal-form-footer"><span class="portal-form-note">Cần tổ chức và review nội dung trong workspace riêng tư?</span><a class="portal-button portal-button--quiet" href="/content-studio?kind=${encodeURIComponent(contentStudioKind)}">Mở Content Studio</a></div>`
      : "";
    const flow = context.featureFlows && context.featureFlows[route];
    const flowOutput = flow
      ? `<div class="portal-state" data-state="${safeText(flow.status || "guarded")}"><span class="portal-state-icon" aria-hidden="true">○</span><div><h3>${safeText(flow.message || "Core Bridge đã cập nhật trạng thái.")}</h3><p>Trạng thái canonical: ${safeText(STATE_LABELS[flow.status] || flow.status || "guarded")}. ${flow.status === "completed" ? "Output chỉ được cấp qua asset đã xác minh." : "Bản nháp planning có thể hiển thị; output engine vẫn phải qua job và asset hợp lệ."}</p></div></div>${renderCanonicalFlow(flow, route)}${renderFeatureTracking(flow)}`
      : renderEmpty("Chờ Engine Web hoặc integration tùy chọn", "Khi một engine đã được cấp capability, backend mới cung cấp trạng thái và asset được xác minh.", "○");
    const isCanonicalVoiceRoute = page.path === "/voice" || page.path.startsWith("/voice/");
    const voiceVault = isCanonicalVoiceRoute && page.path !== "/voice/outputs" ? renderVoiceVault(context) : "";
    return `<article class="portal-page">${renderHero(page, context)}<div class="portal-status-grid">${renderStatusCard(page, context)}${renderSummary(page, context)}</div>
      <div class="portal-work-grid"><div>${renderFormCard(page, context)}${contentStudioLink}</div><aside class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Tích hợp an toàn</h2><p class="portal-card-subtitle">UI chỉ phát sự kiện có cấu trúc cho lớp FastAPI.</p></div></div>${renderNotes(page)}</aside></div>
      ${voiceVault}${renderFeatureBotHandoff(page, context, flow)}<section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Output & trạng thái</h2><p class="portal-card-subtitle">Không tạo text, media, transcript hoặc file giả để thay thế engine thật.</p></div>${badge((flow && flow.status) || stateFor(page, context))}</div>${flowOutput}</section></article>`;
  }

  function renderVoiceVault(context) {
    const profiles = Array.isArray(context.voiceProfiles) ? context.voiceProfiles : [];
    const consentLabel = (profile) => {
      const labels = { granted: "Đã đồng ý", confirmed: "Đã xác nhận", required: "Chờ xác nhận", pending: "Chờ xác nhận", revoked: "Đã thu hồi" };
      return labels[String(profile && profile.consent_status || "").toLowerCase()] || "Chưa được bot xác nhận";
    };
    const previewLabel = (profile) => profile && profile.preview_ready
      ? "Có preview canonical · chờ adapter URL ký"
      : "Chưa có preview canonical";
    return `<section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Voice Vault canonical</h2><p class="portal-card-subtitle">Tên, consent và trạng thái dùng giọng được bot kiểm tra; Web chưa có adapter URL ký để phát preview.</p></div></div>${renderRowsTable(["Giọng", "Trạng thái", "TTS", "Preview", "Consent", "Cập nhật"], profiles, (profile) => `<td>${safeText(profile.display_name || "Giọng chưa đặt tên")}${profile.is_default ? " · Mặc định" : ""}</td><td>${badge(profile.status || "guarded")}</td><td>${profile.tts_ready ? "Sẵn sàng" : "Chưa sẵn sàng"}</td><td>${safeText(previewLabel(profile))}</td><td>${safeText(consentLabel(profile))}</td><td>${safeText(profile.updated_at || profile.created_at || "—")}</td>`, "Chưa có giọng đã được bot cấp", "Voice Vault sẽ chỉ hiển thị metadata thuộc signed session hiện tại.")}</section>`;
  }

  const SUBTITLE_ASSET_FEATURES = new Set(["subtitle", "subtitle_asr", "subtitle_create", "subtitle_translate", "video_dub", "asr"]);

  function assetMatchesReadOnlyScope(item, scope) {
    const feature = String(item && (item.feature || item.job_type) || "").toLowerCase();
    if (!scope) return true;
    if (scope === "subtitle") return SUBTITLE_ASSET_FEATURES.has(feature);
    return feature.includes(scope);
  }

  function renderReadOnly(page, context) {
    const assets = Array.isArray(context.assets) ? context.assets : [];
    const jobs = Array.isArray(context.jobs) ? context.jobs : [];
    const scope = page.path === "/music/sfx-library" ? "sfx" : page.path.startsWith("/image") ? "image" : page.path.startsWith("/video") ? "video" : (page.path === "/voice" || page.path.startsWith("/voice/")) ? "voice" : page.path.startsWith("/music") ? "music" : page.path.startsWith("/subtitle") ? "subtitle" : "";
    const scopedAssets = assets.filter((item) => assetMatchesReadOnlyScope(item, scope));
    let content;
    if (page.view === "voices") {
      content = renderVoiceVault(context);
    } else if (page.view === "jobs") {
      content = `<section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Job gần đây (tối đa 100)</h2><p class="portal-card-subtitle">Không có polling provider trực tiếp từ browser.</p></div></div>${renderRowsTable(["Job", "Tính năng", "Trạng thái", "Chi phí canonical", "Cập nhật"], jobs, (item) => `<td><a href="/jobs/${encodeURIComponent(item.id || "")}">${safeText(item.id || "—")}</a></td><td>${safeText(item.feature || "—")}</td><td>${badge(jobStatus(item))}</td><td>${jobCost(item)}</td><td>${safeText(item.updated_at || item.created_at || "—")}</td>`, "Chưa có job được xác minh", "Core Bridge sẽ chỉ trả job thuộc signed session hiện tại.")}</section>`;
    } else {
      const isSfxLibrary = page.path === "/music/sfx-library";
      const isMusicLibrary = page.path === "/music/library";
      const assetTitle = isSfxLibrary ? "Hiệu ứng âm thanh gần đây (tối đa 100)" : "Tài sản gần đây (tối đa 100)";
      const emptyTitle = isSfxLibrary ? "Chưa có SFX được xác minh" : "Chưa có tài sản được xác minh";
      const emptyText = isSfxLibrary ? "Core Bridge chỉ trả metadata SFX thuộc signed session; không phát hoặc tải output chưa có delivery ký." : "Khi output hợp lệ, Core Bridge mới trả metadata và signed delivery theo ownership.";
      const siblingLibrary = isSfxLibrary ? { href: "/music/library", label: "Mở thư viện nhạc" } : isMusicLibrary ? { href: "/music/sfx-library", label: "Mở thư viện SFX" } : null;
      content = `<section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">${assetTitle}</h2><p class="portal-card-subtitle">Không hiển thị URL provider, file path hoặc preview không được ký.</p></div>${siblingLibrary ? `<a class="portal-button portal-button--quiet" href="${siblingLibrary.href}">${siblingLibrary.label} →</a>` : ""}</div>${renderRowsTable(["Tài sản", "Tính năng", "Trạng thái", "Delivery"], scopedAssets, (item) => `<td>${assetJobLink(item)}</td><td>${safeText(item.feature || "—")}</td><td>${badge(jobStatus(item))}</td><td>${assetDeliveryState(item, "asset")}</td>`, emptyTitle, emptyText)}</section>`;
    }
    return `<article class="portal-page">${renderHero(page, context)}<div class="portal-status-grid">${renderStatusCard(page, context)}${renderSummary(page, context)}</div>${content}<section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Quy tắc dữ liệu</h2><p class="portal-card-subtitle">Trang chỉ đọc không tạo request engine rỗng.</p></div></div>${renderNotes(page)}</section></article>`;
  }

  const ADMIN_DIRECTORY_GROUPS = Object.freeze([
    { key: "identity", title: "Tổng quan & quyền truy cập", description: "Người dùng, ví, lead, CSKH và access control." },
    { key: "billing", title: "Thanh toán & thương mại", description: "Payment, topup, revenue, refund, giá và khuyến mãi." },
    { key: "content-ops", title: "Content & Publishing", description: "Campaign, calendar, approval, channel và analytics chỉ đọc." },
    { key: "operations", title: "Jobs & vận hành", description: "Queue, provider, worker, readiness và maintenance." },
    { key: "governance", title: "Governance & hệ thống", description: "Audit, report, runtime, backup và hệ thống." }
  ]);

  function adminDirectoryGroup(path) {
    if (["/admin", "/admin/users", "/admin/wallet", "/admin/leads", "/admin/tickets", "/admin/support", "/admin/access", "/admin/security"].includes(path)) return "identity";
    if (["/admin/payments", "/admin/topups", "/admin/revenue", "/admin/refunds", "/admin/pricing", "/admin/packages", "/admin/promos"].includes(path)) return "billing";
    if (["/admin/campaigns", "/admin/calendar", "/admin/approvals", "/admin/publishing", "/admin/analytics"].includes(path)) return "content-ops";
    if (["/admin/jobs", "/admin/jobs/failed", "/admin/providers", "/admin/provider-cost", "/admin/workers", "/admin/features", "/admin/freezes", "/admin/runtime"].includes(path)) return "operations";
    return "governance";
  }

  function adminDirectoryEntries() {
    const seen = new Set();
    return Object.values(manifest).filter((candidate) => {
      if (!candidate || candidate.access !== "admin" || !candidate.path || !candidate.path.startsWith("/admin") || seen.has(candidate.path)) return false;
      seen.add(candidate.path);
      return true;
    }).map((candidate) => ({
      key: candidate.path,
      route: candidate.path,
      title: candidate.title,
      description: candidate.description,
      icon: candidate.icon,
      group: adminDirectoryGroup(candidate.path),
      kind: "admin"
    }));
  }

  function renderAdminDirectory(context) {
    // This is navigation metadata only. The FastAPI route and every bridge
    // read remain the security boundary; a browser flag never grants Admin.
    if (context.isAdmin !== true) return "";
    const entries = adminDirectoryEntries();
    const groups = ADMIN_DIRECTORY_GROUPS.map((group) => ({ ...group, entries: entries.filter((entry) => entry.group === group.key) })).filter((group) => group.entries.length);
    if (!groups.length) return "";
    return `<section class="portal-card portal-card-pad portal-admin-directory"><div class="portal-card-header"><div><h2 class="portal-card-title">Danh mục Admin ERP</h2><p class="portal-card-subtitle">Chỉ route điều hướng đã được server bảo vệ; mỗi module vẫn tự kiểm tra signed admin session, capability và redaction.</p></div>${badge("read_only")}</div><div class="portal-admin-directory-groups">${groups.map((group) => `<section class="portal-admin-directory-group" aria-labelledby="admin-directory-${safeText(group.key)}"><div class="portal-admin-directory-head"><div><h3 id="admin-directory-${safeText(group.key)}">${safeText(group.title)}</h3><p>${safeText(group.description)}</p></div><span class="portal-feature-count">${safeText(String(group.entries.length))} module</span></div><div class="portal-module-grid">${group.entries.map((entry) => moduleCard(entry, context, "Mở module")).join("")}</div></section>`).join("")}</div></section>`;
  }

  function renderAdminOverview(page, context) {
    const data = context.adminData && typeof context.adminData === "object" ? context.adminData : {};
    const counts = data.counts || {};
    const readiness = data.readiness && typeof data.readiness === "object" ? Object.entries(data.readiness) : [];
    const readyCount = readiness.filter(([, item]) => item && item.public_ready).length;
    const metrics = [["Users", String(counts.users || "—"), "Dữ liệu cần role check"], ["Engine jobs", String(counts.engine_jobs || "—"), "Đọc từ queue canonical"], ["Worker jobs", String(counts.worker_jobs || "—"), "Queue worker canonical"], ["Payment", String(counts.payments || "—"), "Không có ledger client"], ["Readiness", readiness.length ? `${readyCount}/${readiness.length}` : "—", "Feature public-ready"]];
    const refreshEnabled = context.capabilities && context.capabilities["refresh-admin"] === true;
    const readinessRows = readiness.slice(0, 8);
    return `<article class="portal-page">${renderHero(page, context)}<section class="portal-card portal-card-pad portal-admin-guard"><div class="portal-state" data-state="guarded"><span class="portal-state-icon" aria-hidden="true">⌘</span><div><h2>${context.isAdmin ? "Admin session đã được server xác nhận" : "Admin ERP đang chờ signed session"}</h2><p>${context.isAdmin ? "Tất cả read/write vẫn cần capability và Core Bridge; shell không tự thực hiện tác vụ quản trị." : "Client route không đủ để cấp quyền. FastAPI cần kiểm tra signed session trước khi render dữ liệu."}</p></div></div></section>
      <section class="portal-admin-grid">${metrics.map(([label, value, note]) => `<div class="portal-metric"><span>${label}</span><strong>${value}</strong><em>${note}</em></div>`).join("")}</section>
      <div class="portal-work-grid"><section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Readiness canonical</h2><p class="portal-card-subtitle">Chỉ xem trạng thái bot đã redaction; không bật/tắt provider từ trình duyệt.</p></div><button class="portal-button portal-button--quiet" type="button" data-portal-action="refresh-admin" data-portal-route="/admin"${refreshEnabled ? "" : " disabled"}>Làm mới</button></div>${renderRowsTable(["Tính năng", "Trạng thái", "Adapter"], readinessRows, ([key, item]) => `<td>${safeText(key)}</td><td>${badge(item && item.public_ready ? "ready" : "guarded")}</td><td>${safeText(item && item.adapter || "—")}</td>`, "Chưa có readiness được cấp", "Core Bridge sẽ chỉ trả trạng thái khi signed admin session còn hiệu lực.")}</section>${renderSummary(page, context)}</div>${renderAdminDirectory(context)}</article>`;
  }

  function adminModuleKey(page, context) {
    const data = context.adminData && typeof context.adminData === "object" ? context.adminData : {};
    return String(data.module || (page.routePath || page.path).split("/").filter(Boolean)[1] || "overview").toLowerCase().replace(/_/g, "-");
  }

  function adminNumber(value, suffix) {
    const parsed = Number(value);
    const display = Number.isFinite(parsed) ? parsed.toLocaleString("vi-VN") : "—";
    return `${display}${suffix || ""}`;
  }

  function adminJobActions(item, context, route) {
    const jobId = String(item && item.id || "").trim();
    if (!/^[A-Za-z0-9._:-]{1,160}$/.test(jobId)) return `<span class="portal-form-note">Chưa có job ID hợp lệ</span>`;
    const state = jobStatus(item);
    const canRetry = context.capabilities && context.capabilities["admin-retry"] === true;
    const canRefund = context.capabilities && context.capabilities["admin-refund"] === true;
    const retryEligible = ["failed", "failed_no_charge", "cancelled"].includes(state);
    const refundEligible = ["completed", "failed"].includes(state);
    if (!retryEligible && !refundEligible) return `<span class="portal-form-note">Không có action phù hợp</span>`;
    const disabledTitle = "Cần signed canonical admin session, CSRF, Core Bridge và WEBAPP_ADMIN_WRITES_ENABLED.";
    const retry = retryEligible
      ? `<button class="portal-button portal-button--quiet" type="button" data-portal-action="admin-retry" data-portal-route="${safeText(route)}" data-admin-job-id="${safeText(jobId)}" data-portal-confirm="Retry job ${safeText(jobId)}? Bot canonical sẽ kiểm tra lại quyền, trạng thái và charge trước khi quyết định."${canRetry ? "" : ` disabled title="${disabledTitle}"`}>Retry</button>`
      : "";
    const refund = refundEligible
      ? `<button class="portal-button portal-button--quiet" type="button" data-portal-action="admin-refund" data-portal-route="${safeText(route)}" data-admin-job-id="${safeText(jobId)}" data-portal-confirm="Yêu cầu hoàn Xu cho job ${safeText(jobId)}? Bot canonical sẽ kiểm tra charge, output và chính sách refund trước khi quyết định."${canRefund ? "" : ` disabled title="${disabledTitle}"`}>Yêu cầu hoàn Xu</button>`
      : "";
    return `<div class="portal-inline-actions portal-admin-write-actions">${retry}${refund}</div>`;
  }

  function renderAdminFreezeControls(page, context) {
    if (context.isAdmin !== true) return "";
    const module = adminModuleKey(page, context);
    if (!["features", "freezes"].includes(module)) return "";
    const features = (Array.isArray(context.catalog) ? context.catalog : [])
      .filter((item) => item && /^[a-z][a-z0-9_]{1,120}$/.test(String(item.key || "")))
      .map((item) => ({ key: String(item.key), label: String(item.title || item.key) }))
      .sort((left, right) => left.label.localeCompare(right.label, "vi"));
    const enabled = context.capabilities && context.capabilities["admin-freeze"] === true && features.length > 0;
    const disabled = enabled ? "" : " disabled";
    const reason = features.length
      ? "Chỉ bật sau signed canonical admin session, CSRF, Core Bridge và flag write riêng."
      : "Chờ catalog canonical để chọn feature cần điều khiển.";
    const options = features.map((item) => `<option value="${safeText(item.key)}">${safeText(item.label)} · ${safeText(item.key)}</option>`).join("");
    return `<section class="portal-card portal-card-pad portal-admin-write-panel"><div class="portal-card-header"><div><h2 class="portal-card-title">Maintenance feature canonical</h2><p class="portal-card-subtitle">Đóng băng/mở lại luôn đi qua confirmation, CSRF, idempotency và canonical admin check. Browser không thay provider, giá hoặc trạng thái job trực tiếp.</p></div>${badge(enabled ? "awaiting_confirm" : "guarded")}</div><form class="portal-form" data-portal-form data-portal-action="admin-freeze" data-portal-route="${safeText(page.routePath || page.path)}" data-portal-confirm="Xác nhận gửi thay đổi maintenance sang Bot canonical? Hãy kiểm tra feature, trạng thái và ghi chú trước khi tiếp tục." novalidate><label class="portal-field"><span class="portal-label">Feature</span><select class="portal-select" name="feature" required${disabled}><option value="" selected disabled>Chọn feature cần điều khiển</option>${options}</select></label><label class="portal-field"><span class="portal-label">Trạng thái</span><select class="portal-select" name="frozen" required${disabled}><option value="" selected disabled>Chọn thay đổi</option><option value="true">Đóng băng tạm thời</option><option value="false">Mở lại feature</option></select></label><label class="portal-field"><span class="portal-label">Ghi chú vận hành</span><textarea class="portal-textarea" name="note" placeholder="Lý do, phạm vi và điều kiện mở lại…" minlength="5" maxlength="300" required${disabled}></textarea></label><div class="portal-form-footer"><span class="portal-form-note">${safeText(reason)}</span><button class="portal-button portal-button--primary" type="submit"${disabled}>Áp dụng maintenance</button></div></form></section>`;
  }

  function renderAdminDataTable(page, context) {
    const data = context.adminData && typeof context.adminData === "object" ? context.adminData : {};
    const rows = Array.isArray(data.items) ? data.items : [];
    const module = adminModuleKey(page, context);
    if (["users", "user", "wallet"].includes(module)) {
      return renderRowsTable(["Người dùng", "Tên hiển thị", "Số dư", "Đã dùng", "Gói", "Tạo lúc"], rows, (item) => `<td>${safeText(item.user_id || "—")}</td><td>${safeText(item.username || "—")}</td><td>${safeText(adminNumber(item.balance_xu, " Xu"))}</td><td>${safeText(adminNumber(item.total_spent_xu, " Xu"))}</td><td>${item.is_vip ? "VIP" : "Chuẩn"}</td><td>${safeText(item.created_at || "—")}</td>`, "Chưa có người dùng được cấp", "Core Bridge chỉ trả các trường phù hợp với role quản trị hiện tại.");
    }
    if (["payments", "topups", "revenue", "refunds"].includes(module)) {
      const manualBoundary = module === "topups"
        ? `<div class="portal-notice portal-notice--info"><span class="portal-notice-icon" aria-hidden="true">i</span><div><strong>Chỉ đơn PayOS canonical</strong><p>Bảng này không phải hàng chờ nạp thủ công. Bill, TXID, đối soát và duyệt nạp thủ công tiếp tục trong Bot.</p></div></div>`
        : "";
      return `${manualBoundary}${renderRowsTable(["Mã đơn PayOS", "Người dùng", "Giá trị", "Xu", "Loại PayOS", "Trạng thái", "Cập nhật"], rows, (item) => `<td>${safeText(item.order_code || item.id || "—")}</td><td>${safeText(item.user_id || "—")}</td><td>${safeText(adminNumber(item.amount_vnd, " đ"))}</td><td>${safeText(adminNumber(item.xu, " Xu"))}</td><td>${safeText(item.type || "—")}</td><td>${badge(paymentStatus(item))}</td><td>${safeText(item.paid_at || item.created_at || "—")}</td>`, "Chưa có đơn PayOS được cấp", "Nạp thủ công không xuất hiện ở Web; Bot canonical giữ toàn bộ đối soát, approval và ledger.")}`;
    }
    if (module === "failed-jobs") {
      const incidentCount = rows.filter((item) => ["failed", "failed_no_charge", "cancelled"].includes(jobStatus(item))).length;
      const incidentNotice = `<div class="portal-notice portal-notice--info"><span class="portal-notice-icon" aria-hidden="true">i</span><div><strong>Incident queue chỉ đọc</strong><p>${safeText(String(incidentCount))} job lỗi/hủy được Core Bridge cấp trong lần đọc này. Chỉ category lỗi đã rút gọn được hiển thị; retry, refund, charge và provider operation tiếp tục do Bot canonical quyết định.</p></div></div>`;
      return `${incidentNotice}${renderRowsTable(["Job", "Tính năng", "Trạng thái", "Nguyên nhân đã rút gọn", "Chi phí / hoàn Xu", "Output", "Cập nhật"], rows, (item) => `<td>${safeText(item.id || "—")}</td><td>${safeText(item.feature || item.job_type || "—")}</td><td>${badge(jobStatus(item))}</td><td>${safeText(item.error_category || "Chưa có category canonical")}</td><td>${jobCost(item)}</td><td>${reportedOutput(item)}</td><td>${safeText(item.updated_at || item.created_at || "—")}</td>`, "Chưa có incident job được cấp", "Bot/Core Bridge chưa cấp job lỗi thuộc phạm vi quản trị hiện tại. Không tạo incident hoặc lỗi giả tại browser.")}`;
    }
    if (["jobs", "failed-jobs", "workers", "runtime"].includes(module)) {
      const route = page.routePath || page.path;
      return renderRowsTable(["Job", "Tính năng", "Trạng thái", "Chi phí canonical", "Cập nhật", "Output engine", "Delivery", "Thao tác canonical"], rows, (item) => `<td>${safeText(item.id || "—")}</td><td>${safeText(item.feature || item.job_type || "—")}</td><td>${badge(jobStatus(item))}</td><td>${jobCost(item)}</td><td>${safeText(item.updated_at || item.created_at || "—")}</td><td>${reportedOutput(item)}</td><td>${assetDeliveryState(item)}</td><td>${adminJobActions(item, context, route)}</td>`, "Chưa có job vận hành được cấp", "Admin view vẫn không hiển thị URL provider, local path hay download không ký.");
    }
    if (["providers", "provider-cost", "features", "freezes", "pricing", "promos"].includes(module)) {
      return renderRowsTable(["Tính năng", "Trạng thái", "Lý do đã rút gọn", "Cập nhật"], rows, (item) => `<td>${safeText(item.feature || item.id || "—")}</td><td>${badge(jobStatus(item))}</td><td>${safeText(item.reason || "—")}</td><td>${safeText(item.updated_at || "—")}</td>`, "Chờ trạng thái canonical", "Feature/provider readiness chỉ đọc. Freeze, giá và provider operation không được thực hiện từ UI.");
    }
    if (["tickets", "support"].includes(module)) {
      return renderRowsTable(["Ticket", "Loại", "Ưu tiên", "Trạng thái", "Đính kèm", "Cập nhật"], rows, (item) => `<td>${safeText(item.id || item.code || "—")}</td><td>${safeText(item.category || item.related_tool || "—")}</td><td>${safeText(item.priority || "—")}</td><td>${badge(ticketStatus(item))}</td><td>${item.has_attachment ? "Có" : "Không"}</td><td>${safeText(item.updated_at || item.created_at || "—")}</td>`, "Chưa có metadata ticket được cấp", "Nội dung, username, Telegram attachment ID và thread ticket không được render trong bảng ERP này.");
    }
    if (["audit", "security"].includes(module)) {
      return renderRowsTable(["Sự kiện", "Hành động", "Kết quả", "Thời điểm"], rows, (item) => `<td>${safeText(item.id || "—")}</td><td>${safeText(item.action || "—")}</td><td>${badge(jobStatus(item))}</td><td>${safeText(item.created_at || "—")}</td>`, "Chưa có audit event được cấp", "Không render raw audit payload, detail, token, file ID hoặc danh tính người dùng.");
    }
    return renderRowsTable(["Đối tượng", "Trạng thái", "Cập nhật"], rows, (item) => `<td>${safeText(item.id || item.feature || item.user_id || "—")}</td><td>${badge(jobStatus(item))}</td><td>${safeText(item.updated_at || item.created_at || "—")}</td>`, "Module đang chờ adapter canonical", "Không tạo record, số liệu hoặc action thay thế khi bot chưa có read-only adapter phù hợp.");
  }

  function renderAdmin(page, context) {
    const data = context.adminData && typeof context.adminData === "object" ? context.adminData : {};
    const compatibilityGuarded = data.compatibility_guarded === true;
    const refreshEnabled = !compatibilityGuarded && context.capabilities && context.capabilities["refresh-admin"] === true;
    const module = adminModuleKey(page, context);
    const incidentReadOnly = module === "failed-jobs";
    const writeEnabled = !compatibilityGuarded && !incidentReadOnly && Boolean(context.capabilities && (context.capabilities["admin-retry"] || context.capabilities["admin-refund"] || context.capabilities["admin-freeze"]));
    const recordText = page.recordId ? `<div class="portal-notice portal-notice--info"><span class="portal-notice-icon">i</span><div><strong>Record được yêu cầu</strong><p>ID ${safeText(page.recordId)} không cấp quyền hay dữ liệu cho browser. Core Bridge phải kiểm tra permission trước khi trả chi tiết.</p></div></div>` : "";
    const adapterMessage = data.message ? `<div class="portal-notice portal-notice--info"><span class="portal-notice-icon">i</span><div><strong>Trạng thái adapter</strong><p>${safeText(data.message)}</p></div></div>` : "";
    const compatibilityNotice = compatibilityGuarded
      ? `<div class="portal-notice"><span class="portal-notice-icon" aria-hidden="true">i</span><div><strong>Chờ adapter Web đã kiểm chứng</strong><p>Route này được giữ để không mất parity điều hướng với Bot, nhưng Web không gọi một module Bot chưa công bố. Không có số liệu, action, provider, Xu hoặc payment nào được tạo thay thế.</p></div></div>`
      : "";
    const refreshTitle = compatibilityGuarded ? "Module này chưa có adapter Bot canonical để làm mới từ Web." : "Làm mới dữ liệu quản trị đã được role-check.";
    return `<article class="portal-page">${renderHero(page, context)}<section class="portal-card portal-card-pad portal-admin-guard"><div class="portal-state" data-state="guarded"><span class="portal-state-icon" aria-hidden="true">⌘</span><div><h2>${context.isAdmin ? "Lớp quản trị có kiểm soát" : "Cần quyền quản trị được server xác minh"}</h2><p>${context.isAdmin ? "Dữ liệu hiển thị, write permission, CSRF, confirmation và audit vẫn do Core Bridge quyết định." : "Không có dữ liệu PII, wallet hoặc payment được render cho client không có signed admin session."}</p></div></div></section>
      <div class="portal-work-grid"><section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">${safeText(module)} · dữ liệu vận hành</h2><p class="portal-card-subtitle">Hiển thị sau permission, redaction và ownership checks. Bộ lọc/write sẽ chỉ xuất hiện khi có adapter canonical riêng.</p></div><button class="portal-button portal-button--quiet" type="button" data-portal-action="refresh-admin" data-portal-route="${safeText(page.routePath || page.path)}" title="${safeText(refreshTitle)}"${refreshEnabled ? "" : " disabled"}>Làm mới</button></div>${compatibilityNotice}${adapterMessage}${renderAdminDataTable(page, context)}</section>
        <aside class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">${writeEnabled ? "Write adapter có kiểm soát" : "Chế độ chỉ đọc"}</h2><p class="portal-card-subtitle">${compatibilityGuarded ? "Bot chưa công bố adapter; Web không dựng action thay thế." : (incidentReadOnly ? "Incident queue chỉ hỗ trợ triage bằng metadata canonical đã rút gọn; Bot giữ retry/refund/charge." : (writeEnabled ? "Mỗi write vẫn cần xác nhận Bot canonical và audit event." : "Không bypass canonical business rules."))}</p></div>${badge(writeEnabled ? "awaiting_confirm" : (compatibilityGuarded ? "guarded" : "read_only"))}</div>${renderNotes(page)}</aside></div>${renderAdminFreezeControls(page, context)}${recordText}</article>`;
  }

  const BOT_COMPANION_COMMAND_PATTERN = /^\/[a-z][a-z0-9_]{1,48}$/;

  function safeBotCompanionCommand(value) {
    const command = typeof value === "string" ? value.trim() : "";
    return BOT_COMPANION_COMMAND_PATTERN.test(command) ? command : "";
  }

  function renderBotCompanion(page, context) {
    const connection = context.telegramConnection && typeof context.telegramConnection === "object" ? context.telegramConnection : {};
    const botUrl = safeTelegramLink(connection.bot_chat_url || "");
    const botReady = Boolean(botUrl);
    const commands = Array.isArray(page.botCommands) ? page.botCommands.map((entry) => ({
      command: safeBotCompanionCommand(entry && entry.command),
      title: typeof (entry && entry.title) === "string" ? entry.title.slice(0, 100) : "Lệnh Bot",
      text: typeof (entry && entry.text) === "string" ? entry.text.slice(0, 300) : "Tiếp tục trong Bot canonical."
    })).filter((entry) => entry.command) : [];
    const connectionState = botReady
      ? `<div class="portal-notice portal-notice--info"><span class="portal-notice-icon" aria-hidden="true">⌁</span><div><strong>Handoff Bot canonical</strong><p>Mở đúng Bot đã cấu hình, sau đó gửi lệnh. Portal không truyền Telegram ID, nội dung ghi chú, trạng thái reward hay dữ liệu riêng tư sang Telegram.</p></div><a class="portal-button portal-button--quiet" href="${safeText(botUrl)}" target="_blank" rel="noopener noreferrer">Mở Bot</a></div>`
      : `<div class="portal-notice"><span class="portal-notice-icon" aria-hidden="true">i</span><div><strong>Bot chưa có URL công khai</strong><p>Web đang chờ <code>BOT_USERNAME</code> hợp lệ. Các lệnh bên dưới được giữ khóa để không tạo handoff mơ hồ.</p></div></div>`;
    const cards = commands.map((entry) => `<article class="portal-bot-companion-card"><div class="portal-bot-companion-card-head"><code class="portal-link-code">${safeText(entry.command)}</code>${badge("read_only")}</div><h3>${safeText(entry.title)}</h3><p>${safeText(entry.text)}</p><div class="portal-form-footer"><span class="portal-form-note">State, quyền lợi và lịch sử được Bot xác minh.</span><button class="portal-button portal-button--quiet" type="button" data-portal-action="copy-bot-companion-command" data-copy-text="${safeText(entry.command)}"${botReady ? "" : " disabled title=\"Cần BOT_USERNAME hợp lệ để mở đúng Bot.\""}>Sao chép lệnh</button></div></article>`).join("");
    return `<article class="portal-page">${renderHero(page, context)}<section class="portal-card portal-card-pad portal-bot-companion-intro"><div class="portal-state" data-state="read_only"><span class="portal-state-icon" aria-hidden="true">⌁</span><div><h2>Tiếp tục trong Bot, không nhân bản state</h2><p>${safeText(page.description)}</p><div class="portal-state-meta"><span>Bot là authority</span><span>Không có dữ liệu giả</span><span>Không gửi identity qua browser</span></div></div></div></section>${connectionState}<section class="portal-bot-companion-grid" aria-label="Lệnh Bot canonical">${cards || renderEmpty("Chưa có lệnh Bot được công bố", "Module này chưa có handoff an toàn.", "⌁")}</section><section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Ranh giới dữ liệu</h2><p class="portal-card-subtitle">Các module này giữ parity điều hướng với Bot nhưng không nhận dữ liệu/customer state từ browser.</p></div>${badge("read_only")}</div>${renderNotes(page)}<div class="portal-form-footer"><a class="portal-button portal-button--quiet" href="/account">Tài khoản & liên kết</a><a class="portal-button portal-button--quiet" href="/support">Cần hỗ trợ</a></div></section></article>`;
  }

  const ANALYTICS_BOT_COMMAND_PATTERN = /^\/(?:growth_ai|campaign_report)$/;

  function safeAnalyticsBotCommand(value) {
    const command = typeof value === "string" ? value.trim() : "";
    return ANALYTICS_BOT_COMMAND_PATTERN.test(command) ? command : "";
  }

  function renderAnalyticsBotCompanion(page, context) {
    const command = safeAnalyticsBotCommand(page.botCommand);
    const isGrowth = command === "/growth_ai";
    const defaultDays = Number.isInteger(Number(page.botDefaultDays)) && Number(page.botDefaultDays) >= 1 && Number(page.botDefaultDays) <= 90
      ? Number(page.botDefaultDays)
      : (isGrowth ? 14 : 30);
    const connection = context.telegramConnection && typeof context.telegramConnection === "object" ? context.telegramConnection : {};
    const botUrl = safeTelegramLink(connection.bot_chat_url || "");
    const botReady = Boolean(botUrl && command);
    const disabled = botReady ? "" : " disabled title=\"Cần BOT_USERNAME hợp lệ để mở đúng Bot.\"";
    const commandLabel = isGrowth ? "Growth AI" : "Báo cáo Campaign";
    const defaultDayOptions = [7, 14, 30, 60, 90].map((day) => `<option value="${day}"${day === defaultDays ? " selected" : ""}>${day} ngày</option>`).join("");
    const platformOptions = [
      ["", "Tất cả nền tảng"], ["facebook", "Facebook"], ["tiktok", "TikTok"], ["youtube", "YouTube"],
      ["instagram", "Instagram"], ["threads", "Threads"], ["website", "Website"]
    ].map(([value, label]) => `<option value="${safeText(value)}">${safeText(label)}</option>`).join("");
    const goalControl = isGrowth
      ? `<label class="portal-field"><span class="portal-label">Mục tiêu phân tích</span><select class="portal-select" name="goal"${disabled}><option value="kiếm tiền affiliate">Kiếm tiền affiliate</option><option value="tăng traffic">Tăng traffic</option><option value="tăng chuyển đổi">Tăng chuyển đổi</option><option value="tăng doanh thu">Tăng doanh thu</option><option value="tăng follow">Tăng follow</option></select><span class="portal-field-help">Chỉ các mục tiêu đã được Web allowlist mới được đặt vào lệnh Bot.</span></label>`
      : `<label class="portal-field"><span class="portal-label">Định dạng</span><select class="portal-select" name="format"${disabled}><option value="txt">TXT — bản đọc nhanh</option><option value="csv">CSV — file báo cáo</option></select><span class="portal-field-help">Bot tạo và gửi file; Web không tạo bản export thay thế.</span></label>`;
    const connectionState = botReady
      ? `<div class="portal-notice portal-notice--info"><span class="portal-notice-icon" aria-hidden="true">⌁</span><div><strong>Chuẩn bị lệnh Bot canonical</strong><p>Chọn bộ lọc an toàn, sau đó sao chép lệnh và chủ động gửi vào đúng Bot. Bot vẫn là nơi đọc dữ liệu, kiểm tra Xu, tạo output và hoàn phí khi cần.</p></div><a class="portal-button portal-button--quiet" href="${safeText(botUrl)}" target="_blank" rel="noopener noreferrer">Mở Bot</a></div>`
      : `<div class="portal-notice"><span class="portal-notice-icon" aria-hidden="true">i</span><div><strong>Bot chưa có URL công khai</strong><p>Web đang chờ <code>BOT_USERNAME</code> hợp lệ; form được khóa để không tạo handoff mơ hồ.</p></div></div>`;
    const form = command
      ? `<section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Bộ lọc ${safeText(commandLabel)}</h2><p class="portal-card-subtitle">Các giá trị này chỉ dùng để tạo một lệnh Telegram đã giới hạn. Không có request analytics, Xu hay file nào gửi từ browser.</p></div>${badge("read_only")}</div><form class="portal-form" data-portal-form data-portal-action="copy-analytics-bot-command" data-portal-route="${safeText(page.path)}" novalidate><input type="hidden" name="bot_command" value="${safeText(command)}"><label class="portal-field"><span class="portal-label">Khoảng thời gian</span><select class="portal-select" name="days"${disabled}>${defaultDayOptions}</select><span class="portal-field-help">Bot giới hạn tối đa 90 ngày và kiểm tra dữ liệu canonical trước khi tính phí.</span></label><label class="portal-field"><span class="portal-label">Nền tảng</span><select class="portal-select" name="platform"${disabled}>${platformOptions}</select><span class="portal-field-help">Để trống để Bot đọc tất cả nền tảng có dữ liệu của bạn.</span></label><label class="portal-field"><span class="portal-label">Campaign ID (tuỳ chọn)</span><input class="portal-input" name="campaign_id" type="number" min="1" max="2147483647" step="1" inputmode="numeric" autocomplete="off" placeholder="Ví dụ: 42"${disabled}><span class="portal-field-help">Chỉ nhận ID số của campaign; Web không tra cứu hoặc tiết lộ campaign khác.</span></label>${goalControl}<div class="portal-form-footer"><span class="portal-form-note">Lệnh chỉ chứa command và bộ lọc allowlist. Không kèm Telegram ID, session, Xu, token, doanh thu hoặc dữ liệu provider.</span><button class="portal-button portal-button--primary" type="submit"${disabled}>Sao chép lệnh ${safeText(command)}</button></div></form></section>`
      : renderEmpty("Chưa có lệnh Bot hợp lệ", "Module analytics này đang chờ command canonical được đăng ký.", "⌁");
    const resultNotice = isGrowth
      ? "Bot chỉ charge khi dữ liệu thật có mặt và workflow phân tích tiếp tục. Kết quả AI xuất hiện trong chính cuộc hội thoại Telegram."
      : "Bot chọn TXT/CSV, tạo file và xử lý lỗi/hoàn Xu nếu cần. Web không tự tổng hợp performance hay doanh thu.";
    return `<article class="portal-page">${renderHero(page, context)}<section class="portal-card portal-card-pad portal-bot-companion-intro"><div class="portal-state" data-state="read_only"><span class="portal-state-icon" aria-hidden="true">⌁</span><div><h2>Analytics nằm trong Bot canonical</h2><p>${safeText(page.description)}</p><div class="portal-state-meta"><span>Không có report giả</span><span>Không charge tại browser</span><span>Không lộ identity</span></div></div></div></section>${connectionState}${form}<section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Kết quả & chi phí</h2><p class="portal-card-subtitle">${safeText(resultNotice)}</p></div>${badge("read_only")}</div>${renderNotes(page)}<div class="portal-form-footer"><a class="portal-button portal-button--quiet" href="/jobs">Job Center</a><a class="portal-button portal-button--quiet" href="/wallet">Ví Xu canonical</a><a class="portal-button portal-button--quiet" href="/support">Cần hỗ trợ</a></div></section></article>`;
  }

  const CAMPAIGN_PLAN_STATUSES = Object.freeze(["draft", "review", "approved", "scheduled", "archived"]);
  const CAMPAIGN_PLAN_STATUS_LABELS = Object.freeze({
    draft: "Bản nháp", review: "Tự rà soát", approved: "Đã sẵn sàng", scheduled: "Đã xếp lịch", archived: "Đã lưu trữ"
  });
  const CAMPAIGN_PLAN_TRANSITIONS = Object.freeze({
    draft: ["review", "archived"], review: ["draft", "approved", "archived"], approved: ["draft", "scheduled", "archived"],
    scheduled: ["approved", "archived"], archived: ["draft"]
  });
  const CAMPAIGN_PLATFORM_LABELS = Object.freeze({
    facebook: "Facebook", instagram: "Instagram", tiktok: "TikTok", youtube: "YouTube", website: "Website", other: "Khác"
  });
  const CAMPAIGN_OBJECTIVE_LABELS = Object.freeze({
    affiliate: "Affiliate", traffic: "Tăng traffic", conversion: "Tăng chuyển đổi", revenue: "Tăng doanh thu", community: "Cộng đồng"
  });

  function campaignPlanStatus(plan) {
    const value = String(plan && plan.approval_status || "").trim().toLowerCase();
    return CAMPAIGN_PLAN_STATUSES.includes(value) ? value : "draft";
  }

  function campaignScheduleLabel(value) {
    const raw = typeof value === "string" ? value.trim() : "";
    if (!raw) return "Chưa xếp lịch";
    const parsed = new Date(raw);
    if (Number.isNaN(parsed.getTime())) return "Chưa xếp lịch";
    try {
      return new Intl.DateTimeFormat("vi-VN", { dateStyle: "medium", timeStyle: "short" }).format(parsed);
    } catch (_) {
      return raw.replace("T", " · ");
    }
  }

  function campaignDestinationLink(value) {
    try {
      const url = new URL(String(value || ""));
      if (url.protocol !== "https:" || !url.hostname || url.username || url.password || (url.port && url.port !== "443")) throw new Error("invalid campaign URL");
      return `<a class="portal-campaign-destination" href="${safeText(url.href)}" target="_blank" rel="noopener noreferrer">${safeText(url.hostname)}</a>`;
    } catch (_) {
      return `<span class="portal-form-note">Liên kết đích không còn hợp lệ</span>`;
    }
  }

  function campaignPlanItems(context) {
    if (!Array.isArray(context.campaignPlans)) return [];
    return context.campaignPlans.filter((plan) => plan && typeof plan === "object" && typeof plan.id === "string" && /^[0-9a-f-]{36}$/i.test(plan.id)).slice(0, 100);
  }

  function campaignPlanHref(plan) {
    const id = String(plan && plan.id || "").trim();
    return /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(id)
      ? `/campaigns/${encodeURIComponent(id)}`
      : "/campaigns";
  }

  function campaignStatusControls(plan, enabled, route) {
    const id = String(plan.id);
    const current = campaignPlanStatus(plan);
    const transitions = CAMPAIGN_PLAN_TRANSITIONS[current] || [];
    const choices = [current, ...transitions];
    const options = choices.map((value) => `<option value="${safeText(value)}">${safeText(CAMPAIGN_PLAN_STATUS_LABELS[value] || value)}</option>`).join("");
    const disabled = enabled ? "" : " disabled";
    const actionRoute = typeof route === "string" && route.startsWith("/campaigns/") ? route : "/campaigns";
    return `<form class="portal-campaign-review" data-portal-form data-portal-action="campaign-update-status" data-portal-route="${safeText(actionRoute)}" data-portal-confirm="Cập nhật trạng thái kế hoạch cục bộ? Thao tác này không publish, không tạo job và không thay đổi Xu." novalidate>
      <input type="hidden" name="plan_id" value="${safeText(id)}">
      <label class="portal-field"><span class="portal-label">Trạng thái kế hoạch</span><select class="portal-select" name="approval_status"${disabled}>${options}</select></label>
      <label class="portal-field"><span class="portal-label">Ghi chú tự rà soát</span><textarea class="portal-textarea" name="review_note" maxlength="1000" placeholder="Điều cần hoàn thiện trước bước tiếp theo…"${disabled}>${safeText(String(plan.review_note || ""))}</textarea></label>
      <div class="portal-form-footer"><span class="portal-form-note">Chỉ thay đổi trạng thái quản lý cá nhân của bản kế hoạch này.</span><button class="portal-button portal-button--quiet" type="submit"${disabled}>Cập nhật</button></div>
    </form>`;
  }

  function campaignEditControls(plan, enabled, route) {
    const id = String(plan.id);
    const disabled = enabled ? "" : " disabled";
    const optionsFor = (source, selected) => Object.entries(source).map(([value, label]) => `<option value="${safeText(value)}"${value === selected ? " selected" : ""}>${safeText(label)}</option>`).join("");
    const platform = String(plan.platform || "").toLowerCase();
    const objective = String(plan.objective || "").toLowerCase();
    const scheduledFor = typeof plan.scheduled_for === "string" ? plan.scheduled_for.slice(0, 16) : "";
    const actionRoute = typeof route === "string" && route.startsWith("/campaigns/") ? route : "/campaigns";
    return `<details class="portal-campaign-edit"><summary>Chỉnh sửa brief &amp; mốc lịch</summary><form class="portal-form" data-portal-form data-portal-action="campaign-update" data-portal-route="${safeText(actionRoute)}" data-portal-confirm="Lưu thay đổi kế hoạch cục bộ? Thao tác này không publish, không tạo job và không thay đổi Xu." novalidate>
      <input type="hidden" name="plan_id" value="${safeText(id)}">
      <div class="portal-fields"><label class="portal-field"><span class="portal-label">Tên kế hoạch</span><input class="portal-input" name="title" value="${safeText(String(plan.title || ""))}" minlength="3" maxlength="180" required${disabled}></label><label class="portal-field"><span class="portal-label">Liên kết đích HTTPS</span><input class="portal-input" name="destination_url" type="url" value="${safeText(String(plan.destination_url || ""))}" maxlength="1024" required${disabled}></label><label class="portal-field"><span class="portal-label">Nền tảng</span><select class="portal-select" name="platform" required${disabled}>${optionsFor(CAMPAIGN_PLATFORM_LABELS, platform)}</select></label><label class="portal-field"><span class="portal-label">Mục tiêu</span><select class="portal-select" name="objective" required${disabled}>${optionsFor(CAMPAIGN_OBJECTIVE_LABELS, objective)}</select></label><label class="portal-field"><span class="portal-label">Mốc lịch nội bộ</span><input class="portal-input" name="scheduled_for" type="datetime-local" value="${safeText(scheduledFor)}"${disabled}></label></div>
      <div class="portal-form-footer"><span class="portal-form-note">Chỉ cập nhật metadata Web-owned; Bot/provider/PayOS/Xu không nhận thay đổi này.</span><button class="portal-button portal-button--quiet" type="submit"${disabled}>Lưu thay đổi</button></div>
    </form></details>`;
  }

  function renderCampaignPlanner(page, context) {
    const plans = campaignPlanItems(context);
    const createEnabled = canAct(page, context);
    const createReason = actionBlockReason(page, context);
    const reviewEnabled = Boolean(context.session.authenticated && context.session.csrfReady && context.capabilities && context.capabilities["campaign-update-status"] === true);
    const editEnabled = Boolean(context.session.authenticated && context.session.csrfReady && context.capabilities && context.capabilities["campaign-update"] === true);
    const reviewCount = plans.filter((plan) => campaignPlanStatus(plan) === "review").length;
    const readyCount = plans.filter((plan) => ["approved", "scheduled"].includes(campaignPlanStatus(plan))).length;
    const scheduled = plans.filter((plan) => typeof plan.scheduled_for === "string" && plan.scheduled_for).slice(0, 12);
    const planCards = plans.length
      ? plans.map((plan) => {
        const status = campaignPlanStatus(plan);
        const platform = CAMPAIGN_PLATFORM_LABELS[String(plan.platform || "").toLowerCase()] || "Khác";
        const objective = CAMPAIGN_OBJECTIVE_LABELS[String(plan.objective || "").toLowerCase()] || "Mục tiêu chưa rõ";
        return `<article class="portal-campaign-card" id="campaign-${safeText(plan.id)}" data-campaign-plan="${safeText(plan.id)}"><div class="portal-campaign-card-head"><div><div class="portal-eyebrow">${safeText(platform)} · ${safeText(objective)}</div><h3><a href="${safeText(campaignPlanHref(plan))}">${safeText(String(plan.title || "Kế hoạch chưa đặt tên"))}</a></h3></div>${badge(status)}</div><dl class="portal-campaign-facts"><div><dt>Liên kết đích</dt><dd>${campaignDestinationLink(plan.destination_url)}</dd></div><div><dt>Mốc lịch</dt><dd>${safeText(campaignScheduleLabel(plan.scheduled_for))}</dd></div><div><dt>Cập nhật</dt><dd>${safeText(campaignScheduleLabel(plan.updated_at))}</dd></div></dl><div class="portal-form-footer"><a class="portal-button portal-button--quiet" href="${safeText(campaignPlanHref(plan))}">Mở chi tiết →</a></div>${campaignEditControls(plan, editEnabled)}${campaignStatusControls(plan, reviewEnabled)}</article>`;
      }).join("")
      : renderEmpty("Chưa có kế hoạch", "Tạo kế hoạch đầu tiên để có bảng lịch và luồng tự rà soát rõ ràng. Không có campaign hoặc nội dung nào được tự động xuất bản.", "✦");
    const scheduleStrip = scheduled.length
      ? `<div class="portal-campaign-timeline">${scheduled.map((plan) => `<a class="portal-campaign-timeline-item" href="${safeText(campaignPlanHref(plan))}"><span>${safeText(campaignScheduleLabel(plan.scheduled_for))}</span><strong>${safeText(String(plan.title || "Kế hoạch"))}</strong><em>${safeText(CAMPAIGN_PLATFORM_LABELS[String(plan.platform || "").toLowerCase()] || "Khác")}</em></a>`).join("")}</div>`
      : `<div class="portal-campaign-timeline-empty">Chưa có mốc lịch. Bạn vẫn có thể tạo bản nháp trước, rồi xếp lịch khi đã sẵn sàng.</div>`;
    const formValues = transientFormValues("/campaigns");
    return `<article class="portal-page portal-campaign-planner">${renderHero(page, context)}
      <section class="portal-card portal-card-pad portal-campaign-boundary"><div class="portal-state" data-state="read_only"><span class="portal-state-icon" aria-hidden="true">⌁</span><div><h2>Planning board thuộc Web App</h2><p>Module này giúp bạn tổ chức brief, CTA và lịch cá nhân. Nó không thay đổi campaign canonical của Bot, không tự publish, không chạy provider và không tạo analytics/revenue.</p><div class="portal-state-meta"><span>Signed session + CSRF</span><span>Ownership theo account</span><span>Audit không lưu URL/title</span></div></div></div></section>
      <section class="portal-campaign-metrics" aria-label="Tóm tắt kế hoạch"><div class="portal-metric"><span>Tổng kế hoạch</span><strong>${safeText(String(plans.length))}</strong><em>Chỉ dữ liệu thuộc Web account hiện tại</em></div><div class="portal-metric"><span>Cần tự rà soát</span><strong>${safeText(String(reviewCount))}</strong><em>Không phải hàng duyệt/publish canonical</em></div><div class="portal-metric"><span>Sẵn sàng / đã xếp lịch</span><strong>${safeText(String(readyCount))}</strong><em>Mốc nội bộ, không tạo automation</em></div></section>
      <section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Tạo kế hoạch mới</h2><p class="portal-card-subtitle">Lưu một bản nháp an toàn trước; mọi liên kết đích phải là HTTPS công khai và chỉ hiển thị lại cho chính tài khoản của bạn.</p></div>${badge(createEnabled ? "ready" : "guarded")}</div><form class="portal-form" data-portal-form data-portal-action="campaign-create" data-portal-route="/campaigns" novalidate>${renderFields(page.fields, createEnabled, context, formValues)}<div class="portal-form-footer"><span class="portal-form-note">${createEnabled ? "Lưu cục bộ kèm idempotency và audit. Không gọi Bot, PayOS, Xu hay provider." : safeText(createReason)}</span><button class="portal-button portal-button--primary" type="submit"${createEnabled ? "" : ` disabled title="${safeText(createReason)}"`}>Lưu kế hoạch</button></div></form></section>
      <section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Lịch dự kiến</h2><p class="portal-card-subtitle">Các mốc dưới đây chỉ là lịch quản lý cá nhân; không phát sinh queue xuất bản, reminder hay chạy tự động.</p></div>${badge("read_only")}</div>${scheduleStrip}</section>
      <section class="portal-campaign-board" aria-label="Danh sách kế hoạch">${planCards}</section>
      <section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Ranh giới với Bot canonical</h2><p class="portal-card-subtitle">Khi cần report, analytics, publish queue hoặc campaign automation, tiếp tục dùng adapter Bot đã được phê duyệt.</p></div>${badge("read_only")}</div>${renderNotes(page)}<div class="portal-form-footer"><a class="portal-button portal-button--quiet" href="/growth/ai">Growth AI trong Bot</a><a class="portal-button portal-button--quiet" href="/campaign/report">Báo cáo campaign trong Bot</a><a class="portal-button portal-button--quiet" href="/support">Cần hỗ trợ</a></div></section>
    </article>`;
  }

  function renderCampaignDetail(page, context) {
    const expectedId = String(page.recordId || "").trim();
    const source = context.campaignPlanDetail && typeof context.campaignPlanDetail === "object" ? context.campaignPlanDetail : null;
    const plan = source && String(source.id || "") === expectedId && /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(expectedId) ? source : null;
    const reviewEnabled = Boolean(context.session.authenticated && context.session.csrfReady && context.capabilities && context.capabilities["campaign-update-status"] === true);
    const editEnabled = Boolean(context.session.authenticated && context.session.csrfReady && context.capabilities && context.capabilities["campaign-update"] === true);
    if (!plan) {
      return `<article class="portal-page portal-campaign-detail">${renderHero(page, context)}<section class="portal-card portal-card-pad">${renderEmpty("Không tìm thấy kế hoạch Web", "Kế hoạch có thể không thuộc signed account hiện tại, đã bị xoá hoặc chưa tải xong. Web không thử tra cứu campaign Bot thay thế.", "⌁")}<div class="portal-form-footer"><a class="portal-button portal-button--primary" href="/campaigns">Về Campaign Planner</a></div></section></article>`;
    }
    const status = campaignPlanStatus(plan);
    const platform = CAMPAIGN_PLATFORM_LABELS[String(plan.platform || "").toLowerCase()] || "Khác";
    const objective = CAMPAIGN_OBJECTIVE_LABELS[String(plan.objective || "").toLowerCase()] || "Mục tiêu chưa rõ";
    const reviewNote = String(plan.review_note || "").trim();
    const actionRoute = String(page.routePath || campaignPlanHref(plan));
    const facts = `<dl class="portal-campaign-facts"><div><dt>Trạng thái kế hoạch</dt><dd>${badge(status)}</dd></div><div><dt>Nền tảng</dt><dd>${safeText(platform)}</dd></div><div><dt>Mục tiêu</dt><dd>${safeText(objective)}</dd></div><div><dt>Liên kết đích</dt><dd>${campaignDestinationLink(plan.destination_url)}</dd></div><div><dt>Mốc lịch nội bộ</dt><dd>${safeText(campaignScheduleLabel(plan.scheduled_for))}</dd></div><div><dt>Tạo lúc</dt><dd>${safeText(campaignScheduleLabel(plan.created_at))}</dd></div><div><dt>Cập nhật</dt><dd>${safeText(campaignScheduleLabel(plan.updated_at))}</dd></div></dl>`;
    const reviewCard = reviewNote
      ? `<section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Ghi chú tự rà soát</h2><p class="portal-card-subtitle">Ghi chú này chỉ thuộc kế hoạch cá nhân trên Web.</p></div>${badge("read_only")}</div><div class="portal-result-text">${safeText(reviewNote)}</div></section>`
      : `<section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Ghi chú tự rà soát</h2><p class="portal-card-subtitle">Chưa có ghi chú. Bạn có thể thêm nó khi chuyển trạng thái kế hoạch.</p></div>${badge("empty")}</div></section>`;
    return `<article class="portal-page portal-campaign-detail">${renderHero(page, context)}
      <section class="portal-card portal-card-pad portal-campaign-boundary"><div class="portal-state" data-state="read_only"><span class="portal-state-icon" aria-hidden="true">⌁</span><div><h2>Chi tiết planning Web-owned</h2><p>Trang này chỉ quản lý brief, CTA, lịch nội bộ và tự rà soát của một kế hoạch thuộc signed account hiện tại. Nó không tạo campaign canonical, publish queue, analytics/revenue, job, Xu hoặc PayOS.</p><div class="portal-state-meta"><span>Owner-scoped read</span><span>CSRF + idempotency cho write</span><span>Không gọi Bot/provider</span></div></div></div></section>
      <div class="portal-work-grid"><section class="portal-card portal-card-pad"><div class="portal-card-header"><div><span class="portal-eyebrow">${safeText(platform)} · ${safeText(objective)}</span><h2 class="portal-card-title">${safeText(String(plan.title || "Kế hoạch"))}</h2><p class="portal-card-subtitle">ID Web local: <code>${safeText(expectedId)}</code>. ID này không phải ID campaign Bot và không cho phép đọc chéo tài khoản.</p></div>${badge(status)}</div>${facts}<div class="portal-form-footer"><a class="portal-button portal-button--quiet" href="/campaigns">Tất cả kế hoạch</a><a class="portal-button portal-button--quiet" href="/calendar">Mở Calendar</a><a class="portal-button portal-button--quiet" href="/approvals">Self-review Queue</a></div></section><aside class="portal-stack">${reviewCard}<section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Ranh giới canonical</h2><p class="portal-card-subtitle">Nếu cần analytics, báo cáo hay publish thật, tiếp tục qua Bot đã được phê duyệt.</p></div>${badge("read_only")}</div><div class="portal-form-footer"><a class="portal-button portal-button--quiet" href="/growth/ai">Growth AI</a><a class="portal-button portal-button--quiet" href="/campaign/report">Báo cáo campaign</a></div></section></aside></div>
      <section class="portal-campaign-board" aria-label="Chỉnh sửa kế hoạch"><article class="portal-campaign-card"><div class="portal-campaign-card-head"><div><h2>Brief &amp; mốc lịch</h2><p>Chỉ cập nhật metadata Web-owned của kế hoạch này.</p></div>${badge(editEnabled ? "ready" : "guarded")}</div>${campaignEditControls(plan, editEnabled, actionRoute)}</article><article class="portal-campaign-card"><div class="portal-campaign-card-head"><div><h2>Tự rà soát</h2><p>Lifecycle tại đây không phải duyệt staff hoặc publish canonical.</p></div>${badge(reviewEnabled ? status : "guarded")}</div>${campaignStatusControls(plan, reviewEnabled, actionRoute)}</article></section>
    </article>`;
  }

  function campaignScheduleParts(value) {
    const match = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})/.exec(String(value || ""));
    if (!match) return null;
    const parts = { year: Number(match[1]), month: Number(match[2]) - 1, day: Number(match[3]), hour: Number(match[4]), minute: Number(match[5]) };
    if (parts.month < 0 || parts.month > 11 || parts.day < 1 || parts.day > 31 || parts.hour > 23 || parts.minute > 59) return null;
    return parts;
  }

  function campaignCalendarKey(parts) {
    return parts ? `${parts.year}-${String(parts.month + 1).padStart(2, "0")}-${String(parts.day).padStart(2, "0")}` : "";
  }

  function renderCampaignCalendar(page, context) {
    const plans = campaignPlanItems(context);
    const now = new Date();
    const year = now.getFullYear();
    const month = now.getMonth();
    const firstWeekday = (new Date(year, month, 1).getDay() + 6) % 7;
    const totalDays = new Date(year, month + 1, 0).getDate();
    const byDay = new Map();
    plans.forEach((plan) => {
      const parts = campaignScheduleParts(plan.scheduled_for);
      if (!parts || parts.year !== year || parts.month !== month) return;
      const key = campaignCalendarKey(parts);
      const entries = byDay.get(key) || [];
      entries.push({ plan, parts });
      byDay.set(key, entries);
    });
    const localeMonth = new Intl.DateTimeFormat("vi-VN", { month: "long", year: "numeric" }).format(new Date(year, month, 1));
    const weekdayLabels = ["Th 2", "Th 3", "Th 4", "Th 5", "Th 6", "Th 7", "CN"];
    const cells = [];
    for (let blank = 0; blank < firstWeekday; blank += 1) cells.push(`<div class="portal-calendar-cell is-empty" aria-hidden="true"></div>`);
    for (let day = 1; day <= totalDays; day += 1) {
      const key = `${year}-${String(month + 1).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
      const entries = byDay.get(key) || [];
      const today = now.getDate() === day;
      const cards = entries.slice(0, 3).map(({ plan, parts }) => {
        const status = campaignPlanStatus(plan);
        const time = `${String(parts.hour).padStart(2, "0")}:${String(parts.minute).padStart(2, "0")}`;
        return `<a class="portal-calendar-event" data-status="${safeText(status)}" href="${safeText(campaignPlanHref(plan))}"><time>${safeText(time)}</time><strong>${safeText(String(plan.title || "Kế hoạch"))}</strong></a>`;
      }).join("");
      const overflow = entries.length > 3 ? `<span class="portal-calendar-overflow">+${entries.length - 3} kế hoạch</span>` : "";
      cells.push(`<div class="portal-calendar-cell${today ? " is-today" : ""}"><span class="portal-calendar-day">${safeText(String(day))}</span><div class="portal-calendar-events">${cards}${overflow}</div></div>`);
    }
    const scheduledCount = plans.filter((plan) => campaignScheduleParts(plan.scheduled_for)).length;
    return `<article class="portal-page portal-campaign-calendar">${renderHero(page, context)}
      <section class="portal-card portal-card-pad portal-campaign-boundary"><div class="portal-state" data-state="read_only"><span class="portal-state-icon" aria-hidden="true">⌁</span><div><h2>Calendar không tạo publish queue</h2><p>Lịch này chỉ đọc các mốc Web-owned của bạn. Mỗi card dẫn lại Campaign Planner; không gửi lịch sang Bot, kênh social hay provider.</p><div class="portal-state-meta"><span>${safeText(String(scheduledCount))} mốc đã lên lịch</span><span>Không reminder tự động</span><span>Không channel automation</span></div></div></div></section>
      <section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">${safeText(localeMonth)}</h2><p class="portal-card-subtitle">Các mốc trong tháng hiện tại theo giờ cục bộ bạn đã nhập. Có thể mở kế hoạch để tự rà soát hoặc đổi trạng thái.</p></div>${badge("read_only")}</div><div class="portal-calendar" role="grid" aria-label="Content Calendar ${safeText(localeMonth)}"><div class="portal-calendar-weekdays" role="row">${weekdayLabels.map((label) => `<span role="columnheader">${safeText(label)}</span>`).join("")}</div><div class="portal-calendar-grid">${cells.join("")}</div></div></section>
      <section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Kế hoạch chưa có mốc lịch</h2><p class="portal-card-subtitle">Đặt ngày giờ trong Campaign Planner khi bạn muốn theo dõi một mốc nội bộ. Không có tác vụ nào tự chạy khi thêm mốc.</p></div>${badge("read_only")}</div>${plans.filter((plan) => !campaignScheduleParts(plan.scheduled_for)).length ? `<div class="portal-feature-jumps">${plans.filter((plan) => !campaignScheduleParts(plan.scheduled_for)).slice(0, 12).map((plan) => `<a class="portal-feature-jump" href="${safeText(campaignPlanHref(plan))}">${safeText(String(plan.title || "Kế hoạch"))}</a>`).join("")}</div>` : renderEmpty("Đã có mốc lịch", "Tất cả kế hoạch đang hiển thị đều có một mốc nội bộ hoặc danh sách hiện tại đang trống.", "✓")}</section>
    </article>`;
  }

  function renderCampaignApprovals(page, context) {
    const plans = campaignPlanItems(context);
    const reviewPlans = plans.filter((plan) => campaignPlanStatus(plan) === "review");
    const draftCount = plans.filter((plan) => campaignPlanStatus(plan) === "draft").length;
    const readyCount = plans.filter((plan) => ["approved", "scheduled"].includes(campaignPlanStatus(plan))).length;
    const reviewEnabled = Boolean(context.session.authenticated && context.session.csrfReady && context.capabilities && context.capabilities["campaign-update-status"] === true);
    const cards = reviewPlans.length
      ? reviewPlans.map((plan) => `<article class="portal-campaign-card" id="approval-${safeText(plan.id)}"><div class="portal-campaign-card-head"><div><div class="portal-eyebrow">${safeText(CAMPAIGN_PLATFORM_LABELS[String(plan.platform || "").toLowerCase()] || "Khác")} · ${safeText(CAMPAIGN_OBJECTIVE_LABELS[String(plan.objective || "").toLowerCase()] || "Mục tiêu")}</div><h3><a href="${safeText(campaignPlanHref(plan))}">${safeText(String(plan.title || "Kế hoạch"))}</a></h3></div>${badge("review")}</div><dl class="portal-campaign-facts"><div><dt>Mốc lịch</dt><dd>${safeText(campaignScheduleLabel(plan.scheduled_for))}</dd></div><div><dt>Liên kết đích</dt><dd>${campaignDestinationLink(plan.destination_url)}</dd></div></dl><div class="portal-form-footer"><a class="portal-button portal-button--quiet" href="${safeText(campaignPlanHref(plan))}">Mở chi tiết →</a></div>${campaignStatusControls(plan, reviewEnabled)}</article>`).join("")
      : renderEmpty("Không có kế hoạch cần tự rà soát", "Khi một bản nháp chuyển sang “Tự rà soát”, nó sẽ xuất hiện tại đây. Đây không phải hàng duyệt Admin/Bot.", "✓");
    return `<article class="portal-page portal-campaign-approvals">${renderHero(page, context)}
      <section class="portal-card portal-card-pad portal-campaign-boundary"><div class="portal-state" data-state="read_only"><span class="portal-state-icon" aria-hidden="true">⌁</span><div><h2>Self-review Queue của riêng bạn</h2><p>Chỉ bạn thay đổi lifecycle của kế hoạch Web-owned. “Approved” tại đây không cấp quyền cho channel, publish queue, job, Xu hoặc provider.</p><div class="portal-state-meta"><span>Không có admin approval giả</span><span>Không có publish giả</span><span>Server audit mọi write</span></div></div></div></section>
      <section class="portal-campaign-metrics" aria-label="Tóm tắt tự rà soát"><div class="portal-metric"><span>Bản nháp</span><strong>${safeText(String(draftCount))}</strong><em>Có thể chuyển sang tự rà soát</em></div><div class="portal-metric"><span>Đang tự rà soát</span><strong>${safeText(String(reviewPlans.length))}</strong><em>Cần quyết định trong kế hoạch Web</em></div><div class="portal-metric"><span>Sẵn sàng / đã xếp lịch</span><strong>${safeText(String(readyCount))}</strong><em>Không phải trạng thái canonical</em></div></section>
      <section class="portal-campaign-board" aria-label="Hàng tự rà soát">${cards}</section>
      <section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Cần duyệt thực tế?</h2><p class="portal-card-subtitle">Các job, output, channel và publishing cần queue canonical từ Bot/Admin ERP, không dùng trạng thái ở trang này.</p></div>${badge("read_only")}</div><div class="portal-form-footer"><a class="portal-button portal-button--quiet" href="/campaigns">Mở Campaign Planner</a><a class="portal-button portal-button--quiet" href="/admin/approvals">Admin Approval Queue</a><a class="portal-button portal-button--quiet" href="/support">Cần hỗ trợ</a></div></section>
    </article>`;
  }

  function renderLanding(page, context) {
    const signedIn = context.session && context.session.authenticated === true;
    const primaryHref = signedIn ? "/dashboard" : "/register";
    const primaryLabel = signedIn ? "Mở workspace" : "Bắt đầu miễn phí";
    const secondaryHref = signedIn ? "/account" : "/login";
    const secondaryLabel = signedIn ? "Tài khoản" : "Đăng nhập";
    const studios = [
      { icon: ICONS.chat, tone: "cyan", title: "Content & Chat", text: "Soạn prompt, caption, hook, kịch bản và storyboard từ cùng một brief Web.", href: "/login?next=/chat", tag: "Web authoring" },
      { icon: ICONS.image, tone: "blue", title: "Image Studio", text: "Chuẩn bị prompt ảnh, biến thể và input có kiểm tra trước khi chọn Engine Web.", href: "/login?next=/image/create", tag: "Ảnh" },
      { icon: ICONS.video, tone: "violet", title: "Video Studio", text: "Xây brief, scene và storyboard trong Workspace; engine hiển thị readiness riêng.", href: "/login?next=/video/create", tag: "Video" },
      { icon: ICONS.voice, tone: "amber", title: "Voice & Audio", text: "Soạn lời thoại, brief âm thanh, nhạc và SFX trong luồng có kiểm soát.", href: "/login?next=/voice/tts", tag: "Âm thanh" },
      { icon: ICONS.subtitle, tone: "rose", title: "Subtitle & Dubbing", text: "Lập kế hoạch ASR, SRT, dịch và lồng tiếng trước khi đưa vào engine đã phê duyệt.", href: "/login?next=/subtitle", tag: "Ngôn ngữ" },
      { icon: ICONS.document, tone: "mint", title: "Document Studio", text: "Chuẩn bị workflow PDF, OCR, gộp/tách/nén và dịch với trạng thái thực, không output giả.", href: "/login?next=/documents", tag: "Tài liệu" }
    ];
    const studioCards = studios.map((studio) => `<a class="portal-landing-studio portal-landing-studio--${safeText(studio.tone)}" href="${safeText(studio.href)}"><span class="portal-landing-studio-icon" aria-hidden="true">${safeText(studio.icon)}</span><span class="portal-landing-studio-tag">${safeText(studio.tag)}</span><strong>${safeText(studio.title)}</strong><span>${safeText(studio.text)}</span><em>Mở workflow <span aria-hidden="true">→</span></em></a>`).join("");
    return `<article class="portal-landing" aria-label="Giới thiệu TOAN AAS">
      <nav class="portal-landing-nav" aria-label="Điều hướng giới thiệu"><a class="portal-landing-brand" href="/welcome"><span class="portal-brand-mark" aria-hidden="true">TA</span><span><strong>TOAN AAS</strong><small>AI workspace</small></span></a><div class="portal-landing-nav-links"><a href="#studios">Tính năng</a><a href="#workflow">Quy trình</a><a href="#trust">Bảo mật</a></div><div class="portal-landing-nav-actions"><a class="portal-button portal-button--quiet" href="${secondaryHref}">${secondaryLabel}</a><a class="portal-button portal-button--primary" href="${primaryHref}">${primaryLabel}</a></div></nav>
      <section class="portal-landing-hero"><div class="portal-landing-hero-copy"><span class="portal-landing-kicker"><span aria-hidden="true">✦</span> Một workspace AI, có kiểm soát</span><h1>Biến brief thành một hệ thống nội dung, hình ảnh, video và âm thanh — theo cách của Web App.</h1><p>TOAN AAS là workspace độc lập: bạn quản lý Project, versioned Studio Document và brief ngay trên Web. Engine Web hoặc Bot companion chỉ được kết nối khi từng capability đã sẵn sàng.</p><div class="portal-landing-hero-actions"><a class="portal-button portal-button--primary" href="${primaryHref}">${primaryLabel} <span aria-hidden="true">→</span></a><a class="portal-button" href="/login?next=/features">Khám phá công cụ</a></div><ul class="portal-landing-proof" aria-label="Cam kết sản phẩm"><li><span aria-hidden="true">✓</span> Project &amp; Studio Document Web-owned</li><li><span aria-hidden="true">✓</span> Không tạo output giả</li><li><span aria-hidden="true">✓</span> Telegram companion là tùy chọn</li></ul></div><aside class="portal-landing-preview" aria-label="Minh họa quy trình"><div class="portal-landing-preview-bar"><span></span><span></span><span></span><strong>TOAN AAS / Workspace</strong></div><div class="portal-landing-preview-body"><div class="portal-landing-preview-heading"><span>Video sản phẩm</span><b>Draft</b></div><div class="portal-landing-preview-lines"><i></i><i></i><i></i></div><div class="portal-landing-preview-steps"><span class="is-active">1<br><small>Brief</small></span><span>2<br><small>Project</small></span><span>3<br><small>Engine</small></span><span>4<br><small>Delivery</small></span></div><div class="portal-landing-preview-callout"><span aria-hidden="true">⌁</span><p><strong>Web Engine</strong><br>Chưa bật cho đến khi capability, job và delivery được kiểm thử.</p></div></div></aside></section>
      <section class="portal-landing-section" id="studios"><div class="portal-landing-section-heading"><span>AI Studios</span><h2>Một nơi cho toàn bộ workflow sáng tạo.</h2><p>Mỗi studio có route và authoring Web riêng; trạng thái Engine Web và Bot companion luôn được hiển thị tách biệt.</p></div><div class="portal-landing-studios">${studioCards}</div></section>
      <section class="portal-landing-workflow" id="workflow"><div><span class="portal-landing-kicker"><span aria-hidden="true">↗</span> Luồng rõ ràng</span><h2>Không có “đã xong” cho đến khi output thật sự được xác minh.</h2><p>Web giữ authoring, session, ownership và audit của chính nó. Browser không gọi provider, không giữ ledger Xu và không tự xác nhận thanh toán.</p></div><ol><li><span>01</span><div><strong>Brief</strong><p>Chuẩn hóa ý tưởng trong Project và Studio Document.</p></div></li><li><span>02</span><div><strong>Engine</strong><p>Chọn Web Engine hoặc integration đã được cấp capability.</p></div></li><li><span>03</span><div><strong>Confirm</strong><p>Chỉ xác nhận khi quote, policy và job adapter sẵn sàng.</p></div></li><li><span>04</span><div><strong>Delivery</strong><p>Job và file private phải qua ownership check.</p></div></li></ol></section>
      <section class="portal-landing-trust" id="trust"><div class="portal-landing-trust-copy"><span>Trust by design</span><h2>Đủ mạnh cho vận hành, đủ rõ ràng cho khách hàng.</h2><p>Đăng nhập dùng signed session; Telegram chỉ liên kết qua deep-link/mã một lần khi bạn chọn dùng companion; tài sản riêng tư chỉ tải sau ownership check.</p></div><div class="portal-landing-trust-grid"><article><span aria-hidden="true">✦</span><strong>Web-owned workspace</strong><p>Project, Studio Document và audit Web không cần Telegram.</p></article><article><span aria-hidden="true">◌</span><strong>Guarded integrations</strong><p>Không có ledger Xu, webhook PayOS hoặc provider secret trong browser.</p></article><article><span aria-hidden="true">▣</span><strong>Private delivery</strong><p>Output phải đúng owner và được cấp URL ký.</p></article></div></section>
      <footer class="portal-landing-footer"><a class="portal-landing-brand" href="/welcome"><span class="portal-brand-mark" aria-hidden="true">TA</span><span><strong>TOAN AAS</strong><small>AI workspace</small></span></a><span>Draft · Estimate · Confirm · Delivery</span><div><a href="/legal">Điều khoản</a><a href="/privacy">Quyền riêng tư</a></div></footer>
    </article>`;
  }

  function renderVideoFinalization(page, context) {
    const muxOnly = page.path === "/video/mux";
    const cards = muxOnly
      ? [
        { number: "01", icon: ICONS.jobs, title: "Chọn job đã xác minh", text: "Bắt đầu từ Job Center để kiểm tra trạng thái, ownership và delivery thay vì dán URL hoặc path vào form.", href: "/jobs", action: "Mở Job Center" },
        { number: "02", icon: ICONS.assets, title: "Kiểm tra tài sản riêng tư", text: "Chỉ asset canonical có ownership và delivery hợp lệ mới có thể trở thành nguồn mux trong adapter tương lai.", href: "/assets", action: "Mở thư viện tài sản" },
        { number: "03", icon: ICONS.subtitle, title: "Chuẩn bị track phụ đề", text: "Tạo SRT/dubbing trong workflow riêng. Browser không burn subtitle hoặc giả video đã ghép.", href: "/subtitle", action: "Mở workflow phụ đề" }
      ]
      : [
        { number: "01", icon: ICONS.voice, title: "Giọng đọc", text: "Soạn lời thoại hoặc dùng Voice Vault. Mỗi voice/profile vẫn được Bot kiểm tra lại trước quote hoặc job.", href: "/voice/tts", action: "Chuẩn bị voice" },
        { number: "02", icon: ICONS.music, title: "Nhạc & SFX", text: "Tạo brief nhạc nền, AI song hoặc SFX theo policy bản quyền; chưa tìm/generate media ở browser.", href: "/music/create", action: "Chuẩn bị nhạc" },
        { number: "03", icon: ICONS.subtitle, title: "Phụ đề & lồng tiếng", text: "Chọn ASR, dịch hoặc dubbing; mode, quote và readiness được trả bởi canonical bridge.", href: "/dubbing", action: "Mở dubbing" },
        { number: "04", icon: ICONS.image, title: "Logo / watermark", text: "Bot có luồng lựa chọn vị trí watermark. Web giữ bước này guarded đến khi có adapter asset + mux riêng.", href: "", action: "Chờ adapter canonical", guarded: true },
        { number: "05", icon: ICONS.assets, title: "Preview & export", text: "Video chỉ preview/export khi job completed và delivery URL tạm thời đã được ownership-check.", href: "/video/preview", action: "Xem preview" }
      ];
    const cardsMarkup = cards.map((card) => `<article class="portal-finalization-card${card.guarded ? " is-guarded" : ""}"><div class="portal-finalization-card-head"><span class="portal-finalization-number">${safeText(card.number)}</span><span class="portal-module-icon" aria-hidden="true">${safeText(card.icon)}</span></div><h3>${safeText(card.title)}</h3><p>${safeText(card.text)}</p>${card.href ? `<a class="portal-button portal-button--quiet" href="${safeText(card.href)}">${safeText(card.action)} <span aria-hidden="true">→</span></a>` : `<span class="portal-finalization-guard">${safeText(card.action)}</span>`}</article>`).join("");
    const lead = muxOnly
      ? "Mux là bước delivery. Web không dùng file path, URL, ID provider hoặc upload browser làm bằng chứng rằng một video/audio thuộc tài khoản hiện tại."
      : "Bố cục này phản chiếu các nhánh vfinal của Bot: voice, music, subtitle/dubbing, logo và export. Mỗi workflow được chuẩn bị độc lập trước khi canonical adapter có thể ghép chúng vào video.";
    const stateLabel = muxOnly ? "Mux đang được bảo vệ" : "Finalization đang được bảo vệ";
    return `<article class="portal-page">${renderHero(page, context)}<section class="portal-card portal-card-pad portal-finalization-intro"><div class="portal-state" data-state="guarded"><span class="portal-state-icon" aria-hidden="true">${safeText(ICONS.video)}</span><div><h2>${safeText(stateLabel)}</h2><p>${safeText(lead)}</p><div class="portal-state-meta"><span>Không tự gọi FFmpeg/provider</span><span>Không trừ Xu ở browser</span><span>Không tạo delivery giả</span></div></div></div></section><section class="portal-finalization-grid" aria-label="Các bước video finalization">${cardsMarkup}</section><section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Điều kiện để hoàn tất</h2><p class="portal-card-subtitle">Khi Bot công bố adapter riêng, workflow sẽ dùng exact job reference, charge một lần, output validation và signed delivery URL. Route này không cố thay thế các điều kiện đó.</p></div>${badge("guarded")}</div>${renderNotes(page)}<div class="portal-form-footer"><a class="portal-button portal-button--quiet" href="/video/progress">Theo dõi job video</a><a class="portal-button portal-button--quiet" href="/assets">Tài sản đã xác minh</a><a class="portal-button portal-button--primary" href="/video/create">Tạo video mới</a></div></section></article>`;
  }

  function renderNotFound(page, context) {
    return `<article class="portal-page">${renderHero(page, context)}<section class="portal-card portal-card-pad">${renderEmpty("Route chưa có trong portal", "Không có action fallback. Quay lại Dashboard hoặc chọn module được khai báo.", "·")}<div class="portal-form-footer" style="justify-content:center;margin-top:14px"><a class="portal-button portal-button--primary" href="/dashboard">Về Dashboard</a></div></section></article>`;
  }

  function renderPage(page, context) {
    switch (page.layout) {
      case "landing": return renderLanding(page, context);
      case "bot-companion": return renderBotCompanion(page, context);
      case "analytics-bot-companion": return renderAnalyticsBotCompanion(page, context);
      case "auth": return renderAuth(page, context);
      case "dashboard": return renderDashboard(page, context);
      case "campaign-planner": return renderCampaignPlanner(page, context);
      case "campaign-detail": return renderCampaignDetail(page, context);
      case "campaign-calendar": return renderCampaignCalendar(page, context);
      case "campaign-approvals": return renderCampaignApprovals(page, context);
      case "feature-catalog": return renderFeatureCatalog(page, context);
      case "workspace-drafts": return renderWorkspaceDrafts(page, context);
      case "project-center": return renderProjectCenter(page, context);
      case "memory-notes": return renderMemoryNotes(page, context);
      case "memory-reminders": return renderMemoryReminders(page, context);
      case "prompt-library": return renderPromptLibrary(page, context);
      case "prompt-library-detail": return renderPromptLibraryDetail(page, context);
      case "media-workspace": return renderMediaWorkspace(page, context);
      case "media-workspace-detail": return renderMediaWorkspaceDetail(page, context);
      case "content-studio": return renderContentStudio(page, context);
      case "content-studio-detail": return renderContentStudioDetail(page, context);
      case "image-studio": return renderImageStudio(page, context);
      case "image-studio-detail": return renderImageStudioDetail(page, context);
      case "document-workspace": return renderDocumentWorkspace(page, context);
      case "document-workspace-detail": return renderDocumentWorkspaceDetail(page, context);
      case "video-studio": return renderVideoStudio(page, context);
      case "video-studio-detail": return renderVideoStudioDetail(page, context);
      case "subtitle-studio": return renderSubtitleStudio(page, context);
      case "subtitle-studio-detail": return renderSubtitleStudioDetail(page, context);
      case "voice-studio": return renderVoiceStudio(page, context);
      case "voice-studio-detail": return renderVoiceStudioDetail(page, context);
      case "project-detail": return renderProjectDetail(page, context);
      case "project-packages": return renderProjectPackages(page, context);
      case "feature-family": return renderFeatureFamily(page, context);
      case "wallet": return renderWallet(page, context);
      case "catalog": return renderCatalog(page, context);
      case "jobs": return renderJobs(page, context);
      case "job-detail": return renderJobDetail(page, context);
      case "assets": return renderAssets(page, context);
      case "asset-vault": return renderAssetVault(page, context);
      case "document-hub": return renderDocumentHub(page, context);
      case "pdf-split": return renderPdfSplit(page, context);
      case "pdf-merge": return renderPdfMerge(page, context);
      case "pdf-optimize": return renderPdfOptimize(page, context);
      case "pdf-to-images": return renderPdfToImages(page, context);
      case "pdf-to-word": return renderPdfToWord(page, context);
      case "image-to-pdf": return renderImageToPdf(page, context);
      case "image-resize": return renderImageResize(page, context);
      case "image-enhance": return renderImageEnhance(page, context);
      case "support-desk": return renderSupportDesk(page, context);
      case "support-cases": return renderSupportCases(page, context);
      case "support-case-detail": return renderSupportCaseDetail(page, context);
      case "support-admin": return renderSupportAdmin(page, context);
      case "support-admin-case-detail": return renderSupportAdminCaseDetail(page, context);
      case "tickets": return renderTickets(page, context);
      case "account": return renderAccount(page, context);
      case "account-activity": return renderAccountActivity(page, context);
      case "membership": return renderMembership(page, context);
      case "service-status": return renderServiceStatus(page, context);
      case "media-studio": return renderMediaStudio(page, context);
      case "read-only": return renderReadOnly(page, context);
      case "onboarding": return renderOnboarding(page, context);
      case "legal": return renderLegal(page, context);
      case "admin-overview": return renderAdminOverview(page, context);
      case "admin": return renderAdmin(page, context);
      case "video-finalization": return renderVideoFinalization(page, context);
      case "not-found": return renderNotFound(page, context);
      default: return renderWorkspace(page, context);
    }
  }

  function showToast(message, mode) {
    const region = document.querySelector("[data-portal-toast]");
    if (!region) return;
    const toast = document.createElement("div");
    toast.className = `portal-toast${mode === "warning" ? " portal-toast--warning" : ""}`;
    toast.textContent = message;
    region.appendChild(toast);
    window.setTimeout(() => { toast.remove(); }, 4800);
  }

  function rememberTransientFormDraft(form) {
    if (!form) return;
    const route = form.getAttribute("data-portal-route") || "";
    if (!route) return;
    const values = {};
    form.querySelectorAll("input, textarea, select").forEach((input) => {
      if (!input.name || input.type === "file" || input.type === "password") return;
      values[input.name] = input.type === "checkbox" ? input.checked : input.value;
    });
    transientFormDrafts.set(route, values);
  }

  function synchronizeImageResizePreset(form) {
    if (!form || form.getAttribute("data-portal-action") !== "image-operation-resize") return;
    const preset = form.querySelector('[name="preset"]');
    const isCustom = Boolean(preset && String(preset.value || "") === "custom");
    ["target_width", "target_height"].forEach((name) => {
      const input = form.querySelector(`[name="${name}"]`);
      if (!input) return;
      input.disabled = !isCustom;
      input.required = isCustom;
      input.setAttribute("aria-disabled", String(!isCustom));
      input.setAttribute("aria-required", String(isCustom));
      const field = input.closest(".portal-field");
      const requiredMark = field && field.querySelector("[data-portal-required-mark]");
      const requiredMessage = field && field.querySelector("[data-portal-required-message]");
      if (requiredMark) requiredMark.hidden = !isCustom;
      if (requiredMessage) requiredMessage.hidden = !isCustom;
      if (!isCustom) input.value = "";
    });
  }

  function synchronizeImageEnhancePreset(form) {
    if (!form || form.getAttribute("data-portal-action") !== "image-operation-enhance") return;
    const preset = form.querySelector('[name="preset"]');
    const isCustom = Boolean(preset && String(preset.value || "") === "custom");
    ["brightness", "contrast", "saturation", "sharpness", "tone"].forEach((name) => {
      const input = form.querySelector(`[name="${name}"]`);
      if (!input) return;
      input.disabled = !isCustom;
      input.required = isCustom && name !== "tone";
      input.setAttribute("aria-disabled", String(!isCustom));
      if (name !== "tone") input.setAttribute("aria-required", String(isCustom));
      const field = input.closest(".portal-field");
      const requiredMark = field && field.querySelector("[data-portal-required-mark]");
      const requiredMessage = field && field.querySelector("[data-portal-required-message]");
      if (requiredMark) requiredMark.hidden = !isCustom || name === "tone";
      if (requiredMessage) requiredMessage.hidden = !isCustom || name === "tone";
      if (!isCustom) input.value = name === "tone" ? "neutral" : "";
    });
  }

  function collectFormFields(form) {
    const fields = {};
    if (!form) return fields;
    form.querySelectorAll("input, textarea, select").forEach((input) => {
      if (!input.name) return;
      if (input.type === "file") {
        const selected = input.files ? Array.from(input.files) : [];
        if (selected.length) fields[input.name] = input.multiple ? selected : selected[0];
        return;
      }
      fields[input.name] = input.type === "checkbox" ? input.checked : input.value;
    });
    return fields;
  }

  async function copyCanonicalDraftText(value) {
    const text = canonicalDraftText(value);
    if (!text) throw new Error("Nội dung planning canonical không hợp lệ để sao chép.");
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(text);
      return;
    }
    const field = document.createElement("textarea");
    field.value = text;
    field.setAttribute("readonly", "");
    field.style.position = "fixed";
    field.style.opacity = "0";
    document.body.appendChild(field);
    field.select();
    const copied = document.execCommand("copy");
    field.remove();
    if (!copied) throw new Error("Trình duyệt chưa cho phép sao chép. Bạn có thể chọn nội dung planning và copy thủ công.");
  }

  function applyCanonicalDraftToForm(route, field, value) {
    const targetRoute = normalizePath(route || "");
    const name = String(field || "").trim();
    const text = canonicalDraftText(value);
    const page = manifest[targetRoute] || null;
    const definition = page && Array.isArray(page.fields) ? page.fields.find((item) => item && item.name === name) : null;
    if (!definition || !text || !/^[a-z][a-z0-9_]{0,80}$/.test(name) || ["file", "checkbox", "number"].includes(String(definition.type || "")) || definition.control === "select") {
      showToast("Nội dung canonical này không phù hợp với trường nhập của workflow hiện tại.", "warning");
      return;
    }
    transientFormDrafts.set(targetRoute, { ...transientFormValues(targetRoute), [name]: text });
    if (window.TOANAASPortal) window.TOANAASPortal.mount();
    window.setTimeout(() => {
      const form = Array.from(document.querySelectorAll("[data-portal-form]")).find((item) => item.getAttribute("data-portal-route") === targetRoute);
      const control = form && form.querySelector(`[name="${name}"]`);
      if (control && typeof control.focus === "function") control.focus();
    }, 0);
    showToast("Đã đưa nội dung planning canonical vào form. Bạn vẫn có thể chỉnh sửa trước khi tạo draft/estimate.");
  }

  function validWorkspaceDraftId(value) {
    return /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(String(value || "").trim());
  }

  function workspaceDraftIdForRoute(route) {
    const value = transientWorkspaceDraftIds.get(normalizePath(route || ""));
    return validWorkspaceDraftId(value) ? value : "";
  }

  function restoreWorkspaceDraft(route, input, draftId) {
    const targetRoute = normalizePath(route || "");
    const page = manifest[targetRoute] || null;
    if (!page || page.type !== "feature" || !input || typeof input !== "object" || Array.isArray(input)) return false;
    const forbidden = new Set(["upload_ids", "upload_id", "source", "sample", "audio", "document", "documents", "file", "files", "attachment", "voice_profile_id", "web_quote_receipt", "quote_receipt", "idempotency_key", "consent"]);
    const allowed = new Set((Array.isArray(page.fields) ? page.fields : [])
      .filter((field) => field && field.type !== "file" && field.name && !forbidden.has(field.name))
      .map((field) => field.name));
    const values = {};
    Object.entries(input).forEach(([name, value]) => {
      if (!allowed.has(name) || typeof value !== "string" || !value.trim() || value.length > 4000) return;
      values[name] = value;
    });
    if (!Object.keys(values).length) return false;
    transientFormDrafts.set(targetRoute, values);
    if (validWorkspaceDraftId(draftId)) transientWorkspaceDraftIds.set(targetRoute, String(draftId).trim());
    else transientWorkspaceDraftIds.delete(targetRoute);
    return true;
  }

  function dispatchAction(source, context) {
    const action = source.getAttribute("data-portal-action") || "";
    if (action === "copy-canonical-draft") {
      copyCanonicalDraftText(source.getAttribute("data-canonical-text") || "")
        .then(() => showToast("Đã sao chép nội dung planning canonical."))
        .catch((error) => showToast((error && error.message) || "Không thể sao chép nội dung planning.", "warning"));
      return;
    }
    if (action === "apply-canonical-draft") {
      applyCanonicalDraftToForm(
        source.getAttribute("data-canonical-route") || context.path,
        source.getAttribute("data-canonical-field") || "",
        source.getAttribute("data-canonical-text") || ""
      );
      return;
    }
    const confirmation = source.getAttribute("data-portal-confirm") || "";
    const route = source.getAttribute("data-portal-route") || context.path;
    const formId = source.getAttribute("data-portal-form-id") || "";
    const form = source.matches("form") ? source : (source.closest("form") || (formId ? document.getElementById(formId) : null));
    // A local Workspace draft may be intentionally incomplete. It is still
    // checked server-side for safe scalar fields, while later feature submit
    // re-runs the form's required/upload/canonical validation.
    if (form && !["workspace-draft-save", "workspace-draft-update", "memory-note-archive", "memory-note-restore", "memory-note-restore-version", "prompt-library-filter", "prompt-template-archive", "prompt-template-restore", "prompt-template-purge", "prompt-template-restore-version", "prompt-template-duplicate", "prompt-template-copy", "media-workspace-filter", "media-collection-archive", "media-collection-restore", "media-collection-duplicate", "media-collection-restore-version", "media-item-detach", "content-studio-filter", "content-brief-archive", "content-brief-restore", "content-brief-duplicate", "content-brief-restore-version", "content-brief-compose", "content-variant-select", "content-variant-archive", "content-variant-restore", "image-studio-refresh", "image-artboard-state", "image-artboard-restore-version", "image-direction-archive", "image-direction-restore", "image-direction-restore-version", "document-workspace-refresh", "document-workspace-state", "document-workspace-restore-version", "document-plan-archive", "document-plan-restore", "document-plan-restore-version", "document-plan-reorder", "video-studio-refresh", "video-plan-state", "video-plan-restore-version", "video-scene-archive", "video-scene-restore", "video-scene-restore-version", "video-scene-reorder", "subtitle-studio-refresh", "subtitle-project-state", "subtitle-project-restore-version", "subtitle-cue-archive", "subtitle-cue-restore", "subtitle-cue-restore-version", "subtitle-cue-reorder", "voice-studio-filter", "voice-studio-filter-clear", "voice-studio-refresh", "voice-vault-archive", "voice-vault-restore", "voice-vault-duplicate", "voice-vault-restore-version", "voice-vault-compose", "voice-script-archive", "voice-script-restore", "voice-script-duplicate", "voice-script-restore-version", "voice-script-cue-sheet"].includes(action) && !form.reportValidity()) {
      const invalid = form.querySelector(":invalid");
      if (invalid && typeof invalid.focus === "function") invalid.focus();
      showToast("Hãy hoàn tất các trường bắt buộc trước khi tiếp tục.", "warning");
      return;
    }
    // Validate before asking for a destructive/financial confirmation so the
    // modal always describes the values that will actually be submitted.
    if (confirmation && !window.confirm(confirmation)) return;
    // Search/filter text is intentionally ephemeral. Unlike an authoring
    // draft, it must not be copied into the generic transient form cache.
    if (form && action !== "memory-note-filter" && !["prompt-library-filter", "prompt-library-import", "media-workspace-filter", "media-collection-compose", "media-item-detach", "content-studio-filter", "content-brief-compose", "content-variant-select", "content-brief-archive", "content-brief-restore", "content-brief-duplicate", "content-brief-restore-version", "content-variant-archive", "content-variant-restore", "image-studio-refresh", "image-artboard-state", "image-artboard-restore-version", "image-direction-archive", "image-direction-restore", "image-direction-restore-version", "document-workspace-refresh", "document-workspace-state", "document-workspace-restore-version", "document-plan-archive", "document-plan-restore", "document-plan-restore-version", "document-plan-reorder", "video-studio-refresh", "video-plan-state", "video-plan-restore-version", "video-scene-archive", "video-scene-restore", "video-scene-restore-version", "video-scene-reorder", "subtitle-studio-refresh", "subtitle-project-state", "subtitle-project-restore-version", "subtitle-cue-archive", "subtitle-cue-restore", "subtitle-cue-restore-version", "subtitle-cue-reorder", "voice-studio-filter", "voice-studio-filter-clear", "voice-vault-archive", "voice-vault-restore", "voice-vault-duplicate", "voice-vault-restore-version", "voice-vault-compose", "voice-script-archive", "voice-script-restore", "voice-script-duplicate", "voice-script-restore-version", "voice-script-cue-sheet"].includes(action)) rememberTransientFormDraft(form);
    const fields = collectFormFields(form);
    // Document Workspace mutations deliberately use the same explicit
    // owner-scoped IDs/revisions rendered by the server. Keep them inside
    // the action field payload rather than teaching the generic event shape
    // about another private surface; the backend remains the authority.
    if (String(action || "").startsWith("document-")) {
      Object.assign(fields, {
        __documentWorkspaceId: source.getAttribute("data-document-workspace-id") || "",
        __documentWorkspaceRevision: source.getAttribute("data-document-workspace-revision") || "",
        __documentWorkspaceVersion: source.getAttribute("data-document-workspace-version") || "",
        __documentWorkspaceState: source.getAttribute("data-document-workspace-state") || "",
        __documentPlanId: source.getAttribute("data-document-plan-id") || "",
        __documentPlanRevision: source.getAttribute("data-document-plan-revision") || "",
        __documentPlanVersion: source.getAttribute("data-document-plan-version") || "",
        __documentPlanDirection: source.getAttribute("data-document-plan-direction") || ""
      });
    }
    const event = new CustomEvent(ACTION_EVENT, {
      detail: Object.freeze({ action, route, fields, jobFilter: source.getAttribute("data-job-filter") || "", assetFilter: source.getAttribute("data-asset-filter") || "", ticketFilter: source.getAttribute("data-ticket-filter") || "", paymentId: source.getAttribute("data-payment-id") || "", workspaceDraftId: source.getAttribute("data-workspace-draft-id") || "", projectId: source.getAttribute("data-project-id") || "", studioDocumentId: source.getAttribute("data-studio-document-id") || "", studioDocumentRevision: source.getAttribute("data-studio-document-revision") || "", studioDocumentVersion: source.getAttribute("data-studio-document-version") || "", vaultAssetId: source.getAttribute("data-vault-asset-id") || "", memoryNoteId: source.getAttribute("data-memory-note-id") || "", memoryNoteRevision: source.getAttribute("data-memory-note-revision") || "", memoryNoteVersion: source.getAttribute("data-memory-note-version") || "", memoryReminderId: source.getAttribute("data-memory-reminder-id") || "", memoryReminderRevision: source.getAttribute("data-memory-reminder-revision") || "", promptTemplateId: source.getAttribute("data-prompt-template-id") || "", promptTemplateRevision: source.getAttribute("data-prompt-template-revision") || "", promptTemplateVersion: source.getAttribute("data-prompt-template-version") || "", mediaCollectionId: source.getAttribute("data-media-collection-id") || "", mediaCollectionRevision: source.getAttribute("data-media-collection-revision") || "", mediaCollectionVersion: source.getAttribute("data-media-collection-version") || "", mediaItemId: source.getAttribute("data-media-item-id") || "", contentBriefId: source.getAttribute("data-content-brief-id") || "", contentBriefRevision: source.getAttribute("data-content-brief-revision") || "", contentBriefVersion: source.getAttribute("data-content-brief-version") || "", contentVariantId: source.getAttribute("data-content-variant-id") || "", contentVariantRevision: source.getAttribute("data-content-variant-revision") || "", imageArtboardId: source.getAttribute("data-image-artboard-id") || "", imageArtboardRevision: source.getAttribute("data-image-artboard-revision") || "", imageArtboardVersion: source.getAttribute("data-image-artboard-version") || "", imageArtboardState: source.getAttribute("data-image-artboard-state") || "", imageDirectionId: source.getAttribute("data-image-direction-id") || "", imageDirectionRevision: source.getAttribute("data-image-direction-revision") || "", imageDirectionVersion: source.getAttribute("data-image-direction-version") || "", videoPlanId: source.getAttribute("data-video-plan-id") || "", videoPlanRevision: source.getAttribute("data-video-plan-revision") || "", videoPlanVersion: source.getAttribute("data-video-plan-version") || "", videoPlanState: source.getAttribute("data-video-plan-state") || "", videoSceneId: source.getAttribute("data-video-scene-id") || "", videoSceneRevision: source.getAttribute("data-video-scene-revision") || "", videoSceneVersion: source.getAttribute("data-video-scene-version") || "", videoSceneDirection: source.getAttribute("data-video-scene-direction") || "", subtitleProjectId: source.getAttribute("data-subtitle-project-id") || "", subtitleProjectRevision: source.getAttribute("data-subtitle-project-revision") || "", subtitleProjectVersion: source.getAttribute("data-subtitle-project-version") || "", subtitleProjectState: source.getAttribute("data-subtitle-project-state") || "", subtitleCueId: source.getAttribute("data-subtitle-cue-id") || "", subtitleCueRevision: source.getAttribute("data-subtitle-cue-revision") || "", subtitleCueVersion: source.getAttribute("data-subtitle-cue-version") || "", subtitleCueDirection: source.getAttribute("data-subtitle-cue-direction") || "", subtitleExportFormat: source.getAttribute("data-subtitle-export-format") || "", voiceVaultId: source.getAttribute("data-voice-vault-id") || "", voiceVaultRevision: source.getAttribute("data-voice-vault-revision") || "", voiceVaultVersion: source.getAttribute("data-voice-vault-version") || "", voiceScriptId: source.getAttribute("data-voice-script-id") || "", voiceScriptRevision: source.getAttribute("data-voice-script-revision") || "", voiceScriptVersion: source.getAttribute("data-voice-script-version") || "", supportCaseId: source.getAttribute("data-support-case-id") || "", supportCaseRevision: source.getAttribute("data-support-case-revision") || "", adminJobId: source.getAttribute("data-admin-job-id") || "", adminFeature: source.getAttribute("data-admin-feature") || "", adminFrozen: source.getAttribute("data-admin-frozen") || "", copyText: source.getAttribute("data-copy-text") || "", apiBase: context.apiBase || null }),
      bubbles: false,
      cancelable: true
    });
    window.dispatchEvent(event);
  }

  function sidebarFocusables(sidebar) {
    if (!sidebar) return [];
    return Array.from(sidebar.querySelectorAll("a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled])"))
      .filter((element) => !element.hidden && element.getAttribute("aria-hidden") !== "true");
  }

  function setWorkspaceInert(opened) {
    const workspace = document.querySelector(".portal-workspace");
    if (!workspace) return;
    if ("inert" in workspace) workspace.inert = opened;
    if (opened) workspace.setAttribute("aria-hidden", "true");
    else workspace.removeAttribute("aria-hidden");
  }

  function setSidebarMenuState(button, opened) {
    if (!button) return;
    button.setAttribute("aria-expanded", String(opened));
    button.setAttribute("aria-label", opened ? "Đóng điều hướng" : "Mở điều hướng");
  }

  function closeSidebar(options) {
    const settings = options && typeof options === "object" ? options : {};
    const sidebar = document.querySelector("[data-portal-sidebar]");
    const backdrop = document.querySelector("[data-portal-backdrop]");
    const button = document.querySelector("[data-portal-menu]");
    const wasOpen = Boolean(sidebar && sidebar.classList.contains("is-open"));
    if (sidebar) sidebar.classList.remove("is-open");
    if (backdrop) backdrop.hidden = true;
    if (sidebar) {
      sidebar.removeAttribute("role");
      sidebar.removeAttribute("aria-modal");
    }
    setWorkspaceInert(false);
    setSidebarMenuState(button, false);
    if (wasOpen && settings.restoreFocus !== false && sidebarReturnFocus && typeof sidebarReturnFocus.focus === "function") {
      sidebarReturnFocus.focus({ preventScroll: true });
    }
    sidebarReturnFocus = null;
  }

  function toggleSidebar() {
    const sidebar = document.querySelector("[data-portal-sidebar]");
    const backdrop = document.querySelector("[data-portal-backdrop]");
    const button = document.querySelector("[data-portal-menu]");
    if (!sidebar || !backdrop || !button) return;
    const opened = sidebar.classList.toggle("is-open");
    backdrop.hidden = !opened;
    setSidebarMenuState(button, opened);
    if (!opened) {
      closeSidebar();
      return;
    }
    sidebarReturnFocus = button;
    sidebar.setAttribute("role", "dialog");
    sidebar.setAttribute("aria-modal", "true");
    setWorkspaceInert(true);
    window.requestAnimationFrame(() => {
      const first = sidebarFocusables(sidebar)[0];
      if (first && typeof first.focus === "function") first.focus({ preventScroll: true });
    });
  }

  function closeSidebarAboveMobileBreakpoint() {
    if (!window.matchMedia || !window.matchMedia("(min-width: 981px)").matches) return;
    const sidebar = document.querySelector("[data-portal-sidebar]");
    if (sidebar && sidebar.classList.contains("is-open")) closeSidebar({ restoreFocus: false });
  }

  function commandPaletteFocusables(palette) {
    if (!palette) return [];
    return Array.from(palette.querySelectorAll("a[href], button:not([disabled]), input:not([disabled])"))
      .filter((element) => !element.hidden && element.getAttribute("aria-hidden") !== "true");
  }

  function setCommandPaletteBackgroundInert(opened) {
    const targets = [
      document.querySelector("[data-portal-sidebar]"),
      document.querySelector(".portal-workspace"),
      document.querySelector("[data-portal-mobile-nav]")
    ].filter(Boolean);
    targets.forEach((target) => {
      if ("inert" in target) target.inert = opened;
      if (opened) target.setAttribute("aria-hidden", "true");
      else target.removeAttribute("aria-hidden");
    });
    document.body.classList.toggle("portal-body--command-palette", Boolean(opened));
  }

  function isCommandPaletteOpen() {
    const palette = document.querySelector("[data-portal-command-palette]");
    return Boolean(palette && !palette.hidden);
  }

  function filterCommandPalette(value) {
    const palette = document.querySelector("[data-portal-command-palette]");
    if (!palette || palette.hidden) return;
    const query = normalizeCommandSearch(value);
    const items = Array.from(palette.querySelectorAll("[data-portal-command-item]"));
    let visible = 0;
    items.forEach((item) => {
      const matches = !query || String(item.getAttribute("data-command-search") || "").includes(query);
      item.hidden = !matches;
      if (matches) visible += 1;
    });
    const empty = palette.querySelector("[data-portal-command-empty]");
    const count = palette.querySelector("[data-portal-command-count]");
    if (empty) empty.hidden = visible > 0;
    if (count) count.textContent = visible ? `${visible} workspace phù hợp.` : "Không có workspace phù hợp.";
  }

  function closeCommandPalette(options) {
    const settings = options && typeof options === "object" ? options : {};
    const palette = document.querySelector("[data-portal-command-palette]");
    const wasOpen = Boolean(palette && !palette.hidden);
    if (palette) {
      palette.hidden = true;
      palette.innerHTML = "";
    }
    setCommandPaletteBackgroundInert(false);
    if (wasOpen && settings.restoreFocus !== false && commandPaletteReturnFocus && typeof commandPaletteReturnFocus.focus === "function") {
      commandPaletteReturnFocus.focus({ preventScroll: true });
    }
    commandPaletteReturnFocus = null;
  }

  function openCommandPalette(trigger) {
    const context = getBootstrap();
    if (!(context.session && context.session.authenticated === true)) return;
    const palette = document.querySelector("[data-portal-command-palette]");
    if (!palette) return;
    closeSidebar({ restoreFocus: false });
    commandPaletteReturnFocus = trigger || document.activeElement;
    palette.innerHTML = renderCommandPalette(resolvePage(context.path), context);
    palette.hidden = false;
    setCommandPaletteBackgroundInert(true);
    window.requestAnimationFrame(() => {
      const input = palette.querySelector("[data-portal-command-search]");
      if (input && typeof input.focus === "function") input.focus({ preventScroll: true });
    });
  }

  function focusSnapshot() {
    const active = document.activeElement;
    if (!active || !active.matches || !active.matches("input, textarea, select")) return null;
    const snapshot = { id: active.id || "", name: active.name || "", selectionStart: null, selectionEnd: null };
    if (typeof active.selectionStart === "number") {
      snapshot.selectionStart = active.selectionStart;
      snapshot.selectionEnd = active.selectionEnd;
    }
    return snapshot;
  }

  function restoreFocus(snapshot) {
    if (!snapshot) return;
    const target = snapshot.id ? document.getElementById(snapshot.id) : document.querySelector(`[name="${snapshot.name.replace(/"/g, "\\\"")}"]`);
    if (!target || typeof target.focus !== "function") return;
    target.focus({ preventScroll: true });
    if (snapshot.selectionStart !== null && typeof target.setSelectionRange === "function") {
      try { target.setSelectionRange(snapshot.selectionStart, snapshot.selectionEnd); } catch (_) { /* non-text controls */ }
    }
  }

  function bindInteractions() {
    // The shell re-renders after every authenticated hydration. Delegated
    // listeners therefore belong to the document once, while each action
    // resolves the *current* signed-session bootstrap at click time. This
    // prevents duplicate register/payment/feature events after re-mounting.
    if (interactionsBound) return;
    interactionsBound = true;
    document.addEventListener("click", (event) => {
      const paletteTrigger = event.target.closest("[data-portal-open-command-palette]");
      if (paletteTrigger) { openCommandPalette(paletteTrigger); return; }
      if (event.target.closest("[data-portal-command-close]")) { closeCommandPalette(); return; }
      if (event.target.closest("[data-portal-command-item]")) { closeCommandPalette({ restoreFocus: false }); return; }
      const menu = event.target.closest("[data-portal-menu]");
      if (menu) { toggleSidebar(); return; }
      if (event.target.closest("[data-portal-close-menu]")) { closeSidebar(); return; }
      if (event.target.closest("[data-portal-backdrop]")) { closeSidebar(); return; }
      if (event.target.closest("[data-portal-catalog-clear]")) {
        const search = document.querySelector("[data-portal-catalog-search]");
        if (search) {
          search.value = "";
          filterFeatureCatalog("");
          search.focus({ preventScroll: true });
        }
        return;
      }
      const action = event.target.closest("[data-portal-action]");
      if (action && !action.disabled) {
        if (action.tagName === "BUTTON" && action.type === "submit") return;
        dispatchAction(action, getBootstrap());
        return;
      }
      const link = event.target.closest(".portal-nav-link");
      if (link) closeSidebar({ restoreFocus: false });
    });
    document.addEventListener("submit", (event) => {
      if (event.target.matches("[data-portal-form]")) {
        event.preventDefault();
        dispatchAction(event.target, getBootstrap());
      }
    });
    document.addEventListener("input", (event) => {
      const form = event.target.closest && event.target.closest("[data-portal-form]");
      if (form) rememberTransientFormDraft(form);
      if (event.target.matches && event.target.matches("[data-portal-catalog-search]")) filterFeatureCatalog(event.target.value);
      if (event.target.matches && event.target.matches("[data-portal-command-search]")) filterCommandPalette(event.target.value);
    });
    document.addEventListener("change", (event) => {
      const form = event.target.closest && event.target.closest("[data-portal-form]");
      if (form) {
        if (event.target && event.target.name === "preset") {
          synchronizeImageResizePreset(form);
          synchronizeImageEnhancePreset(form);
        }
        rememberTransientFormDraft(form);
      }
    });
    window.addEventListener("keydown", (event) => {
      const paletteOpen = isCommandPaletteOpen();
      if ((event.ctrlKey || event.metaKey) && String(event.key || "").toLowerCase() === "k") {
        event.preventDefault();
        if (paletteOpen) closeCommandPalette();
        else openCommandPalette(document.querySelector("[data-portal-open-command-palette]"));
        return;
      }
      if (event.key === "Escape" && paletteOpen) { event.preventDefault(); closeCommandPalette(); return; }
      if (event.key === "Tab" && paletteOpen) {
        const palette = document.querySelector("[data-portal-command-palette]");
        const focusables = commandPaletteFocusables(palette);
        if (!focusables.length) return;
        const first = focusables[0];
        const last = focusables[focusables.length - 1];
        if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
        else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
        return;
      }
      const sidebar = document.querySelector("[data-portal-sidebar]");
      const opened = Boolean(sidebar && sidebar.classList.contains("is-open"));
      if (event.key === "Escape" && opened) { event.preventDefault(); closeSidebar(); return; }
      if (event.key !== "Tab" || !opened) return;
      const focusables = sidebarFocusables(sidebar);
      if (!focusables.length) return;
      const first = focusables[0];
      const last = focusables[focusables.length - 1];
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    });
    window.addEventListener("resize", closeSidebarAboveMobileBreakpoint);
  }

  function mountPortal(override) {
    if (override && typeof override === "object") window.__TOAN_AAS_PORTAL__ = override;
    const focus = focusSnapshot();
    const context = getBootstrap();
    const page = resolvePage(context.path);
    const sidebar = document.querySelector("[data-portal-sidebar]");
    const header = document.querySelector("[data-portal-header]");
    const main = document.querySelector("[data-portal-main]");
    const shell = document.querySelector("[data-portal-shell]");
    const mobileNav = document.querySelector("[data-portal-mobile-nav]");
    const commandPalette = document.querySelector("[data-portal-command-palette]");
    if (!sidebar || !header || !main || !shell) return;
    // A hydration remount must not leave the responsive navigation in an
    // inert/modal state with a replaced header button behind it.
    if (sidebar.classList.contains("is-open")) closeSidebar({ restoreFocus: false });
    if (commandPalette && !commandPalette.hidden) closeCommandPalette({ restoreFocus: false });
    const isLanding = page.layout === "landing";
    const isAuth = page.layout === "auth";
    // The public landing and unauthenticated access screens intentionally
    // avoid showing an authenticated workspace sidebar. This keeps the first
    // visit focused, prevents a misleading "already inside" impression, and
    // leaves the regular navigation intact immediately after a signed login.
    const minimalShell = isLanding || isAuth;
    const showMobileNav = !minimalShell && context.session && context.session.authenticated === true;
    shell.classList.toggle("portal-shell--landing", isLanding);
    shell.classList.toggle("portal-shell--auth", isAuth);
    document.body.classList.toggle("portal-body--landing", isLanding);
    document.body.classList.toggle("portal-body--auth", isAuth);
    sidebar.hidden = minimalShell;
    header.hidden = minimalShell;
    if (mobileNav) {
      mobileNav.hidden = !showMobileNav;
      mobileNav.innerHTML = showMobileNav ? renderMobileNav(page) : "";
    }
    if (commandPalette && !showMobileNav) {
      commandPalette.hidden = true;
      commandPalette.innerHTML = "";
    }
    document.title = `${displayPageTitle(page, context)} · TOAN AAS`;
    sidebar.innerHTML = renderSidebar(page, context);
    header.innerHTML = renderHeader(page, context);
    main.innerHTML = renderPage(page, context);
    bindInteractions();
    restoreFocus(focus);
  }

  window.TOANAASPortal = Object.freeze({
    ACTION_EVENT,
    pageManifest: Object.freeze({ ...manifest }),
    resolvePage,
    mount: mountPortal,
    restoreWorkspaceDraft,
    states: Object.freeze({ ...STATE_LABELS })
  });

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", () => mountPortal(), { once: true });
  else mountPortal();
}());
