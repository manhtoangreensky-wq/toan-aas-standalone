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
    "completed", "failed", "failed_no_charge", "cancelled", "refunded", "review", "approved", "scheduled", "archived", "guarded", "disabled", "read_only", "error", "empty"
  ]);

  const STATE_LABELS = Object.freeze({
    ready: "Sẵn sàng",
    draft: "Bản nháp",
    awaiting_confirm: "Chờ xác nhận",
    queued: "Đã xếp hàng",
    processing: "Đang xử lý",
    completed: "Hoàn tất",
    review: "Tự rà soát",
    approved: "Đã sẵn sàng",
    scheduled: "Đã xếp lịch",
    archived: "Đã lưu trữ",
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
    dashboard: "⌂", account: "◉", wallet: "◌", jobs: "⌛", assets: "▣",
    chat: "◒", prompt: "✦", image: "◩", video: "▶", voice: "◖", music: "♫",
    subtitle: "≡", document: "▤", support: "?", pricing: "◇", legal: "§",
    admin: "⌘", users: "◎", payments: "◈", providers: "◫", system: "⚙",
    reports: "◒", security: "◈", ticket: "✉", default: "·"
  });

  // These actions write only Web-owned planning metadata.  They never need a
  // provider/Core Bridge connection and must not inherit a false "Bot is
  // running" promise from the broader feature workflow UI.
  const WEB_LOCAL_ACTIONS = new Set(["campaign-create", "campaign-update", "campaign-update-status"]);

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
    documentPdf: [
      { name: "document", label: "Tài liệu nguồn", type: "file", accept: "application/pdf,image/jpeg,image/png,image/webp", requiredUpload: true, help: "Tệp chỉ vào bot-owned staging sau validation; Web không giữ raw path hoặc bytes lâu dài." },
      { name: "operation", label: "Công cụ PDF", control: "select", options: ["pdf_to_word", "pdf_to_images", "image_to_pdf"], help: "Chỉ nêu đúng tool local có trong bot; delivery vẫn cần canonical job/asset.", required: true },
      { name: "page_count", label: "Số trang để báo giá", type: "number", placeholder: "Ví dụ: 3", required: true, min: 1, max: 2_000, step: 1, inputMode: "numeric" }
    ],
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
    documentCompress: [
      { name: "document", label: "PDF nguồn", type: "file", accept: "application/pdf", requiredUpload: true },
      { name: "page_count", label: "Số trang để báo giá", type: "number", placeholder: "Ví dụ: 12", required: true, min: 1, max: 2_000, step: 1, inputMode: "numeric" },
      { name: "notes", label: "Ghi chú", control: "textarea", placeholder: "Yêu cầu đầu ra (không hứa mức nén chưa có trong helper bot)…" }
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
  // at their handlers.  Every one is zero-argument and opens a chooser,
  // guide, or draft-free overview; none serializes a Portal value into
  // Telegram.  Keep this deliberately small: a command that needs a prompt,
  // upload, ID, payment detail, or provider readiness belongs to the Bot menu
  // until a feature-specific bridge adapter exists.
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

  function customerPage(path, title, description, icon, extra) {
    return definePage({ path, title, description, icon, section: "Khách hàng", ...extra });
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
        "Core Bridge là nơi duy nhất ước tính Xu, tạo job và xác nhận output."
      ],
      ...settings,
      fields: copyFields(settings.fields || fields),
      notes: settings.notes ? [...settings.notes] : [
        "Không có provider nào được gọi từ giao diện này.",
        "Core Bridge là nơi duy nhất ước tính Xu, tạo job và xác nhận output."
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
  customerPage("/", "TOAN AAS", "Không gian AI có kiểm soát cho nội dung, hình ảnh, video và âm thanh.", ICONS.dashboard, {
    access: "public", layout: "landing", action: "none", status: "ready", section: "AI workspace",
    notes: ["Landing không gọi provider, ví Xu hoặc Bot từ browser.", "Mọi workflow riêng tư bắt đầu sau signed session và liên kết Telegram canonical."]
  });
  customerPage("/onboarding", "Thiết lập tài khoản", "Hoàn thiện hồ sơ và liên kết Telegram bằng mã dùng một lần do Web server tạo, bot xác nhận.", ICONS.account, {
    layout: "onboarding", fields: [], action: "start-telegram-link", actionLabel: "Tạo mã liên kết", status: "guarded",
    notes: ["Mã phải là one-time, hết hạn và được Core Bridge đánh dấu đã dùng.", "Không nhận Telegram ID thô từ URL hay localStorage."]
  });
  customerPage("/account", "Tài khoản & bảo mật", "Quản lý thông tin hồ sơ và trạng thái liên kết theo dữ liệu server-side.", ICONS.account, {
    layout: "account", fields: [], action: "none", status: "ready",
    notes: ["Tên hiển thị, ngôn ngữ và múi giờ là metadata Web có thể cập nhật bằng signed session, CSRF và audit event.", "Telegram identity, role, Xu, PayOS, job và provider vẫn là dữ liệu canonical chỉ đọc từ bot/Core Bridge.", "Đăng xuất thu hồi signed session ở server, không chỉ xóa state tại browser."]
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
  botCompanionPage("/notes", "Ghi chú & Memory", "Mở nhanh các ghi chú, memory và plan cá nhân trong Bot canonical; Web không tạo một kho dữ liệu thứ hai.", ICONS.prompt, [
    { command: "/notes", title: "Danh sách ghi chú", text: "Xem ghi chú do Bot quản lý trong đúng cuộc hội thoại Telegram của bạn." },
    { command: "/note", title: "Tạo ghi chú", text: "Bắt đầu luồng tạo hoặc cập nhật note trong Bot; không gửi nội dung note qua Web." },
    { command: "/memory", title: "Memory & plan", text: "Mở memory/plan cá nhân theo state canonical của Bot." }
  ]);
  botCompanionPage("/reminders", "Nhắc việc", "Nhắc việc, lặp lại, pause/resume và hoàn tất cần Bot giữ state thời gian canonical.", ICONS.jobs, [
    { command: "/reminders", title: "Danh sách nhắc việc", text: "Xem reminder thuộc đúng tài khoản Telegram đã xác minh." },
    { command: "/remind", title: "Tạo nhắc việc", text: "Tạo reminder trong Bot để lịch và callback không bị tách khỏi state canonical." }
  ]);
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
  }, ["/", "/app"]);
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
  customerPage("/support", "Hỗ trợ", "Tạo yêu cầu hỗ trợ không kèm secret; ticket hiện nhận nội dung văn bản cho đến khi adapter tệp ký tạm thời được xác minh.", ICONS.support, {
    fields: copyFields(FIELD_SETS.support), action: "create-ticket", actionLabel: "Tạo ticket", status: "guarded"
  });
  customerPage("/tickets", "Ticket của tôi", "Theo dõi ticket thuộc sở hữu của bạn; nội dung được nạp từ Core Bridge khi phiên hợp lệ.", ICONS.ticket, {
    layout: "tickets", action: "none", status: "empty"
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
  featurePage("/image/edit", "Chỉnh sửa ảnh", "Chuẩn bị thay đổi ảnh; upload và xử lý chỉ diễn ra qua đường dẫn được ký tạm thời.", ICONS.image, FIELD_SETS.imageSource, [], { action: "feature-estimate", actionLabel: "Ước tính Xu", estimateDirect: true });
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

  featurePage("/documents", "Document Studio", "Tập hợp workflow PDF, OCR, gộp/tách/nén và dịch tài liệu.", ICONS.document, FIELD_SETS.documentPdf);
  featurePage("/documents/pdf", "PDF tools", "Chuẩn bị thao tác PDF; Core Bridge kiểm tra file, path và ownership.", ICONS.document, FIELD_SETS.documentPdf, ["/pdf"]);
  featurePage("/documents/ocr", "OCR", "Chuẩn bị OCR, đợi engine trả về kết quả được kiểm tra thay vì text giả.", ICONS.document, FIELD_SETS.documentOcr);
  featurePage("/documents/merge", "Gộp tài liệu", "Gộp tài liệu qua job có kiểm tra file server-side.", ICONS.document, FIELD_SETS.documentMerge);
  featurePage("/documents/split", "Tách tài liệu", "Tách tài liệu theo phạm vi trang sau khi bridge xác thực input.", ICONS.document, FIELD_SETS.documentSplit);
  featurePage("/documents/compress", "Nén tài liệu", "Nén file theo job riêng; download chỉ xuất hiện khi output hợp lệ.", ICONS.document, FIELD_SETS.documentCompress);
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
  adminPage("/admin/support", "CSKH", "Không gian vận hành hỗ trợ, không hiển thị PII khi bridge chưa cấp quyền.", ICONS.support);
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
    return {
      path: normalizePath(source.path),
      title: typeof source.title === "string" ? source.title : "",
      isAdmin: source.isAdmin === true,
      // The registry is static, redacted route metadata. Do not truncate it:
      // `/features` must be able to disclose every mapped customer workflow.
      catalog: Array.isArray(source.catalog) ? source.catalog.slice() : [],
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
      tickets: Array.isArray(source.tickets) ? source.tickets : [],
      // Campaign Planner data is Web-owned and already account-scoped by the
      // API. Keep only a bounded presentation copy; the browser never keeps
      // a second campaign store in localStorage.
      campaignPlans: Array.isArray(source.campaignPlans) ? source.campaignPlans.slice(0, 100) : [],
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
      readiness: source.readiness && typeof source.readiness === "object" ? source.readiness : {},
      voiceProfiles: Array.isArray(source.voiceProfiles) ? source.voiceProfiles.slice(0, 20) : [],
      profile: source.profile && typeof source.profile === "object" ? source.profile : {},
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
    if (/^\/jobs\/[^/]+$/.test(normalized)) {
      const jobId = normalized.split("/").pop();
      return Object.freeze({
        path: "/jobs/:id", routePath: normalized, title: "Chi tiết job", icon: ICONS.jobs, section: "Job Center",
        description: "Trạng thái, output và download chỉ hiển thị nếu Core Bridge xác minh ownership và delivery hợp lệ.",
        status: "empty", access: "member", layout: "job-detail", action: "none", actionLabel: "", fields: [],
        recordId: jobId, notes: ["Không có preview hoặc download giả.", "Output riêng tư cần URL ký tạm thời từ Core Bridge."]
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
        description: `${featureFamily.description} Chọn một workflow đã đăng ký; trạng thái chạy vẫn chỉ đến từ Core Bridge.`,
        status: "read_only", access: "member", layout: "feature-family", action: "none", actionLabel: "", fields: [],
        notes: [
          "Đây là điều hướng cho các workflow đã đăng ký, không phải endpoint chạy provider.",
          "Card guarded giữ nguyên trạng thái cho đến khi Bot/Core Bridge công bố adapter canonical."
        ]
      });
    }
    if (normalized === "/features" || normalized.startsWith("/features/")) {
      const label = normalized.split("/").filter(Boolean).slice(1).join(" · ").replace(/[-_]/g, " ") || "Tính năng";
      return Object.freeze({
        path: "/features/:module", routePath: normalized, title: `Feature · ${label}`, icon: ICONS.prompt, section: "Feature parity",
        description: "Compatibility surface được tạo từ inventory bot. Chỉ core bridge có thể chuyển nó khỏi trạng thái guarded.",
        status: "guarded", access: "member", layout: "workspace", action: "none", actionLabel: "", fields: [],
        notes: ["Tính năng bot chưa có adapter Web không bị báo thành công giả.", "Kiểm tra parity matrix để biết trạng thái và blocker chính xác."]
      });
    }
    return Object.freeze({
      path: "/not-found", routePath: normalized, title: "Trang chưa được định tuyến", icon: ICONS.default, section: "TOAN AAS",
      description: "Route này chưa được Core Bridge công bố trong portal. Không có hành động hay dữ liệu nào được thực thi.",
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
      if (context.session.csrfReady !== true && context.bridge.csrfReady !== true) return "CSRF chưa sẵn sàng; thay đổi kế hoạch Web đang được khóa an toàn.";
      return "Khả năng lập kế hoạch Web chưa sẵn sàng cho phiên hiện tại.";
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
        label: "Tổng quan",
        links: [
          ["/dashboard", "Dashboard", ICONS.dashboard], ["/campaigns", "Campaign Planner", ICONS.prompt], ["/calendar", "Content Calendar", ICONS.system], ["/approvals", "Self-review Queue", ICONS.security], ["/jobs", "Job Center", ICONS.jobs], ["/assets", "Tài sản", ICONS.assets]
        ]
      },
      {
        label: "AI Studio",
        links: [
          ["/features", "Tất cả công cụ", ICONS.prompt], ["/tools", "Tools & models", ICONS.prompt], ["/studio", "Media Studio", ICONS.video], ["/chat", "AI Chat", ICONS.chat], ["/prompt-studio", "Prompt Studio", ICONS.prompt], ["/image/create", "Image", ICONS.image],
          ["/video/create", "Video", ICONS.video], ["/voice/tts", "Voice", ICONS.voice], ["/music", "Music", ICONS.music],
          ["/subtitle", "Ngôn ngữ", ICONS.subtitle], ["/documents", "Documents", ICONS.document]
        ]
      },
      {
        label: "Thanh toán & gói",
        links: [
          ["/wallet", "Ví Xu", ICONS.wallet], ["/wallet/topup", "Nạp Xu", ICONS.payments], ["/membership", "Gói thành viên", ICONS.pricing], ["/packages", "Gói dịch vụ", ICONS.pricing], ["/pricing", "Bảng giá", ICONS.pricing]
        ]
      },
      {
        label: "Tài khoản",
        links: [
          ["/tickets", "Ticket của tôi", ICONS.ticket], ["/support", "Hỗ trợ", ICONS.support], ["/notes", "Ghi chú", ICONS.prompt],
          ["/reminders", "Nhắc việc", ICONS.jobs], ["/rewards", "Ưu đãi", ICONS.pricing], ["/guides", "Bot & hướng dẫn", ICONS.legal], ["/status", "Trạng thái dịch vụ", ICONS.system], ["/account", "Tài khoản", ICONS.account]
        ]
      }
    ];
    if (context.isAdmin || currentPage.access === "admin" || currentPage.path.indexOf("/admin") === 0) {
      groups.push({
        label: "Admin ERP",
        links: [
          ["/admin", "Tất cả module", ICONS.admin], ["/admin/users", "Người dùng", ICONS.users], ["/admin/jobs", "Jobs", ICONS.jobs],
          ["/admin/payments", "Thanh toán", ICONS.payments], ["/admin/providers", "Providers", ICONS.providers], ["/admin/audit", "Audit", ICONS.security]
        ]
      });
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
    if (linkPath === "/image/create") return path === "/image" || matchesRouteFamily(path, "/image");
    if (linkPath === "/video/create") return path === "/video" || matchesRouteFamily(path, "/video");
    if (linkPath === "/voice/tts") return path === "/tts" || matchesRouteFamily(path, "/voice");
    if (linkPath === "/music") return matchesRouteFamily(path, "/music");
    if (linkPath === "/subtitle") return matchesRouteFamily(path, "/subtitle") || ["/translate", "/dubbing", "/asr"].includes(path);
    if (linkPath === "/documents") return matchesRouteFamily(path, "/documents");
    if (linkPath === "/wallet") return path === "/wallet";
    if (linkPath === "/wallet/topup") return matchesRouteFamily(path, "/wallet/topup");
    if (linkPath === "/membership") return path === "/membership";
    if (linkPath === "/account") return path === "/account" || path === "/onboarding";
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
      return ["/dashboard", "/campaigns", "/calendar", "/approvals"].includes(path);
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
      return isNavCurrent("/account", page) || ["/wallet", "/wallet/topup", "/membership", "/packages", "/pricing", "/tickets", "/support", "/notes", "/reminders", "/rewards", "/guides", "/status"].some((route) => matchesRouteFamily(path, route));
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
      if (candidate.access === "admin" && !(context && context.isAdmin === true)) return;
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
      <span class="portal-brand-copy"><span class="portal-brand-name">TOAN AAS</span><span class="portal-brand-caption">Control portal</span></span>
      <button class="portal-sidebar-close" type="button" aria-label="Đóng điều hướng" data-portal-close-menu>×</button>
    </div>
    <nav class="portal-nav">${groups}</nav>
    <div class="portal-sidebar-foot">
      <div class="portal-bridge-mini"><span class="portal-bridge-dot${bridgeReady ? " is-ready" : ""}" aria-hidden="true"></span>
        <span><strong>${bridgeReady ? "Core Bridge sẵn sàng" : "Chờ Core Bridge"}</strong><span>${bridgeReady ? "Khả năng được cấp theo phiên" : "Không gọi provider hoặc payment"}</span></span>
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
      const disabled = enabled ? "" : " disabled";
      const rawValue = Object.prototype.hasOwnProperty.call(values, field.name) ? values[field.name] : "";
      const value = rawValue === undefined || rawValue === null ? "" : String(rawValue);
      const stagedUploadCount = field.type === "file" && Array.isArray(values.upload_ids) ? values.upload_ids.filter((item) => typeof item === "string" && item).length : 0;
      const descriptionIds = [];
      const help = field.help ? (descriptionIds.push(`${id}-help`), `<span id="${id}-help" class="portal-field-help">${safeText(field.help)}</span>`) : "";
      const staged = stagedUploadCount ? (descriptionIds.push(`${id}-staged`), `<span id="${id}-staged" class="portal-field-staged">${safeText(String(stagedUploadCount))} tệp đã vào staging canonical; không cần chọn lại để estimate/confirm.</span>`) : "";
      const describedBy = descriptionIds.length ? ` aria-describedby="${descriptionIds.join(" ")}"` : "";
      const required = field.required === true && field.type !== "file" ? " required" : "";
      const ariaRequired = (field.required === true || field.requiredUpload === true) ? ' aria-required="true"' : "";
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
          const value = option && typeof option === "object" ? option.value : option;
          const label = option && typeof option === "object" ? option.label : option;
          const selected = String(value) === String(rawValue) ? " selected" : "";
          return `<option value="${safeText(value)}"${selected}>${safeText(label)}</option>`;
        }).join("");
        control = `<select class="portal-select" id="${id}" name="${safeText(field.name)}"${required}${ariaRequired}${describedBy}${disabled}>${empty}${optionMarkup}</select>`;
      } else if (field.type === "checkbox") {
        const checked = rawValue === true || rawValue === "true" || rawValue === 1 || rawValue === "1" ? " checked" : "";
        control = `<label class="portal-checkbox" for="${id}"><input id="${id}" name="${safeText(field.name)}" type="checkbox" value="true"${checked}${required}${ariaRequired}${describedBy}${disabled}><span>Tôi xác nhận</span></label>`;
      } else {
        const type = ["email", "password", "file", "number", "text"].includes(field.type) ? field.type : "text";
        const autocomplete = field.autocomplete ? ` autocomplete="${safeText(field.autocomplete)}"` : "";
        const multiple = type === "file" && field.multiple ? " multiple" : "";
        const accept = type === "file" && field.accept ? ` accept="${safeText(field.accept)}"` : "";
        const valueAttribute = type === "file" || type === "password" ? "" : ` value="${safeText(value)}"`;
        control = `<input class="portal-input" id="${id}" name="${safeText(field.name)}" type="${type}" placeholder="${safeText(field.placeholder)}"${valueAttribute}${autocomplete}${multiple}${accept}${required}${ariaRequired}${min}${max}${step}${minLength}${maxLength}${pattern}${inputMode}${describedBy}${disabled}>`;
      }
      const requiredMark = field.required === true || field.requiredUpload === true ? '<span class="portal-required-mark" aria-hidden="true">*</span><span class="portal-sr-only"> bắt buộc</span>' : "";
      return `<div class="portal-field${wide ? " portal-field--wide" : ""}"><label for="${id}">${safeText(field.label)}${requiredMark}</label>${control}${help}${staged}</div>`;
    }).join("")}</div>`;
  }

  function statusMessage(page, status, context) {
    if (status === "ready") return { icon: "✓", title: "Giao diện đã sẵn sàng", text: "Chỉ các khả năng đã được máy chủ ký và cấp cho phiên mới được bật." };
    if (status === "empty") return { icon: "○", title: "Chưa có dữ liệu để hiển thị", text: "Portal không tự tạo job, số dư, file hay output. Dữ liệu sẽ xuất hiện sau phản hồi Core Bridge hợp lệ." };
    if (status === "error" || status === "failed") return { icon: "!", title: "Chưa thể xác thực trạng thái", text: "Không có thao tác fallback hay giả lập. Hãy đợi Core Bridge trả trạng thái an toàn." };
    if (status === "queued" || status === "processing") return { icon: "◌", title: "Job đang do Core Bridge điều phối", text: "Chỉ trạng thái engine canonical mới có thể chuyển job sang completed." };
    if (status === "draft" || status === "awaiting_confirm") return { icon: "◇", title: "Bản nháp chờ luồng xác nhận", text: "Core Bridge phải estimate trước, sau đó người dùng xác nhận để tạo job." };
    if (status === "completed") return { icon: "✓", title: "Output đã hoàn tất", text: "Output cần được bridge xác thực file, ownership và URL ký tạm thời trước khi mở tải xuống." };
    if (status === "failed_no_charge") return { icon: "!", title: "Job thất bại · chưa trừ Xu", text: "Bot canonical xác nhận không có charge; Admin có thể retry sau khi Bot kiểm tra lại điều kiện." };
    if (status === "cancelled") return { icon: "—", title: "Yêu cầu đã hủy", text: "Browser chỉ hiển thị trạng thái canonical; không suy đoán charge, refund hoặc delivery." };
    if (status === "refunded") return { icon: "↺", title: "Hoàn Xu đã được ghi nhận", text: "Ledger canonical của bot quyết định số tiền hoàn và trạng thái cuối cùng." };
    if (status === "read_only") return { icon: "i", title: "Dữ liệu canonical chỉ đọc", text: "Portal đang hiển thị dữ liệu bot đã được role-check; mọi thay đổi vẫn cần adapter, confirmation, CSRF và audit riêng." };
    if (status === "disabled") return { icon: "—", title: "Tính năng đang tạm khóa", text: "Trạng thái maintenance/freeze phải được bridge quản lý; browser không thể tự bật lại." };
    const isAdmin = page.access === "admin" && !context.isAdmin;
    const planningAvailable = page.type === "feature" && page.action !== "none" && context.capabilities && context.capabilities["feature-draft"] === true;
    if (planningAvailable) return { icon: "◇", title: "Planning draft sẵn sàng; engine vẫn được bảo vệ", text: "Bạn có thể tạo draft/estimate canonical nếu bridge cấp helper tương ứng. Confirm, charge và output vẫn do bot quyết định." };
    return { icon: "⌁", title: isAdmin ? "Khu vực quản trị cần quyền máy chủ" : "Core Bridge chưa cấp khả năng thực thi", text: isAdmin ? "Server cần xác nhận signed admin session trước khi hiển thị dữ liệu hoặc thao tác ERP." : "Shell chỉ cho phép chuẩn bị giao diện. Provider, wallet, PayOS và job không được gọi trực tiếp tại đây." };
  }

  function renderStatusCard(page, context) {
    const status = stateFor(page, context);
    const message = statusMessage(page, status, context);
    const bridgeText = context.bridge.available === true ? "Bridge đã khai báo cho phiên" : "Bridge chưa bật cho phiên";
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
        <div class="portal-summary-item"><span class="portal-summary-key">Core Bridge</span><span class="portal-summary-value">${context.bridge.available === true ? "Đã khai báo" : "Chưa sẵn sàng"}</span></div>
        <div class="portal-summary-item"><span class="portal-summary-key">Signed session</span><span class="portal-summary-value">${context.session.authenticated === true ? "Được xác minh" : "Đang chờ"}</span></div>
        <div class="portal-summary-item"><span class="portal-summary-key">CSRF</span><span class="portal-summary-value">${context.session.csrfReady === true || context.bridge.csrfReady === true ? "Sẵn sàng" : "Chưa cấp"}</span></div>
        <div class="portal-summary-item"><span class="portal-summary-key">API base</span><span class="portal-summary-value">${safeText(api)}</span></div>
      </div></aside>`;
  }

  function renderNotes(page) {
    const notes = page.notes && page.notes.length ? page.notes : ["Core Bridge là authority cho mọi trạng thái có hiệu lực."];
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
    return `<section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">${page.layout === "auth" ? "Thông tin xác thực" : "Chuẩn bị yêu cầu"}</h2><p class="portal-card-subtitle">${enabled ? "Yêu cầu sẽ được chuyển tới lớp tích hợp thông qua custom event, không gọi trực tiếp từ UI." : safeText(reason)}</p></div>${badge(flowStatus || stateFor(page, context))}</div>
      <form class="portal-form" id="${safeText(formId)}" data-portal-form data-portal-action="${safeText(page.action)}" data-portal-route="${safeText(route)}" novalidate>${renderFields(page.fields, enabled, context, fieldValues)}
        <div class="portal-form-footer"><span class="portal-form-note">${enabled ? "Máy chủ vẫn phải xác minh phiên, CSRF, schema, ownership và idempotency." : "Các trường bị khóa cho tới khi máy chủ cấp khả năng cần thiết."}</span>
          <button class="portal-button portal-button--primary" type="submit"${enabled ? "" : ` disabled title="${safeText(reason)}"`}>${safeText(page.actionLabel || "Tiếp tục")}</button>
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
    if (path.startsWith("/voice")) return "voice";
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

  function renderDashboard(page, context) {
    const jobs = Array.isArray(context.jobs) ? context.jobs.slice(0, 5) : [];
    const assets = Array.isArray(context.assets) ? context.assets.slice(0, 5) : [];
    const wallet = context.wallet && typeof context.wallet === "object" ? context.wallet : null;
    const quickMetrics = wallet
      ? `<section class="portal-admin-grid"><div class="portal-metric"><span>Xu canonical</span><strong>${safeText(String(wallet.balance_xu || 0))}</strong><em>Không tính lại ở browser</em></div><div class="portal-metric"><span>Đã dùng</span><strong>${safeText(String(wallet.total_spent_xu || 0))}</strong><em>Đọc từ ledger canonical</em></div><div class="portal-metric"><span>Job gần đây</span><strong>${safeText(String(jobs.length))}</strong><em>Trong cửa sổ hiện tại</em></div><div class="portal-metric"><span>Asset metadata</span><strong>${safeText(String(assets.length))}</strong><em>Không đồng nghĩa delivery</em></div></section>`
      : "";
    const activity = `<div class="portal-work-grid"><section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Job gần đây</h2><p class="portal-card-subtitle">Core Bridge kiểm tra ownership trước khi trả dữ liệu.</p></div><a class="portal-button portal-button--quiet" href="/jobs">Mở Job Center →</a></div>${renderRowsTable(["Job", "Tính năng", "Trạng thái", "Output engine"], jobs, (item) => `<td><a href="/jobs/${encodeURIComponent(item.id || "")}">${safeText(item.id || "—")}</a></td><td>${safeText(item.feature || "—")}</td><td>${badge(jobStatus(item))}</td><td>${reportedOutput(item)}</td>`, "Chưa có hoạt động được xác minh", "Khi bạn có job hợp lệ, Core Bridge sẽ trả metadata canonical tại đây.")}</section>
      <section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Tài sản gần đây</h2><p class="portal-card-subtitle">Chỉ metadata riêng tư; output hợp lệ vẫn phải chờ delivery URL ký.</p></div><a class="portal-button portal-button--quiet" href="/assets">Mở tài sản →</a></div>${renderRowsTable(["Tài sản", "Tính năng", "Trạng thái", "Delivery"], assets, (item) => `<td>${assetJobLink(item)}</td><td>${safeText(item.feature || "—")}</td><td>${badge(jobStatus(item))}</td><td>${assetDeliveryState(item, "asset")}</td>`, "Chưa có asset metadata", "Không dùng placeholder để thay thế một output đã được xác minh.")}</section></div>`;
    return `<article class="portal-page">${renderHero(page, context)}<div class="portal-status-grid">${renderStatusCard(page, context)}${renderSummary(page, context)}</div>${quickMetrics}${renderWorkspaceActionCenter(context)}${renderStudioLaunchpad(context)}${renderModuleCards(context)}${activity}</article>`;
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
      { number: "04", icon: ICONS.voice, title: "Voice & music", text: "Chuẩn bị TTS, Voice Vault, nhạc hoặc SFX trong các workspace có consent và policy riêng.", href: "/voice/tts", action: "Chuẩn bị voice" },
      { number: "05", icon: ICONS.subtitle, title: "Subtitle & finalization", text: "Dùng subtitle/dubbing rồi mở finalization. Mux, watermark, export và delivery vẫn cần adapter Bot riêng.", href: "/video/add-ons", action: "Mở finalization" }
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
      <div class="portal-work-grid"><section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Hồ sơ & liên kết</h2><p class="portal-card-subtitle">Thông tin lấy từ signed session; browser không lưu Telegram ID, password hay token.</p></div>${badge("read_only")}</div>${accountRows}<div class="portal-form-footer"><span class="portal-form-note">${linked ? "Liên kết Telegram đã được xác minh qua bot." : "Hoàn tất liên kết Telegram để dùng dữ liệu wallet, jobs và assets canonical."}</span>${linked ? "" : `<a class="portal-button portal-button--primary" href="/onboarding">Liên kết Telegram</a>`}</div></section>
      <aside class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Bảo mật phiên</h2><p class="portal-card-subtitle">Logout luôn đi qua server để thu hồi session hiện tại.</p></div></div>${renderNotes(page)}<div class="portal-form-footer" style="margin-top:16px"><button class="portal-button portal-button--quiet" type="button" data-portal-action="auth-logout" data-portal-confirm="Bạn có chắc muốn đăng xuất khỏi phiên này?"${logoutEnabled ? "" : " disabled"}>Đăng xuất</button></div></aside></div>${botPreferenceHandoff}${oauthMethods}${telegramAccountUpgrade}${profileEditor}</article>`;
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
    return `<section class="portal-auth-provider"><div class="portal-card-header"><div><h3 class="portal-card-title">Cách đăng nhập khác</h3><p class="portal-card-subtitle">Email + mật khẩu (có thể dùng Gmail) dùng form ở trên. Telegram Login xác thực Web bằng OIDC; xác minh một lần qua Bot sẽ khóa đúng identity canonical cho Xu, jobs và assets.</p></div></div>${renderPublicOAuthCard("telegram", "Telegram Login", telegramOidcEnabled, "✈", "signin")}${connectionNotice}${pending}${renderPublicOAuthCard("google", "Google (OAuth)", googleEnabled, "G", "signin")}${renderPublicOAuthCard("github", "GitHub", githubEnabled, "◎", "signin")}${renderPublicOAuthCard("apple", "Sign in with Apple", appleEnabled, "", "signin")}</section>`;
  }

  function renderOAuthRegistrationMethods(context) {
    const providers = context.oauthProviders && typeof context.oauthProviders === "object" ? context.oauthProviders : {};
    const telegramOidcEnabled = providers.telegram && providers.telegram.enabled === true;
    const googleEnabled = providers.google && providers.google.enabled === true;
    const githubEnabled = providers.github && providers.github.enabled === true;
    const appleEnabled = providers.apple && providers.apple.enabled === true;
    return `<section class="portal-auth-provider"><div class="portal-card-header"><div><h3 class="portal-card-title">Tạo hoặc tiếp tục với OAuth</h3><p class="portal-card-subtitle">Telegram Login tạo signed Web session từ profile Telegram đã ký; onboarding sau đó yêu cầu Bot xác nhận cùng tài khoản trước khi dữ liệu canonical được mở. Các OAuth khác không tự ghép chỉ vì trùng email.</p></div></div>${renderPublicOAuthCard("telegram", "Telegram Login", telegramOidcEnabled, "✈", "register")}${renderPublicOAuthCard("google", "Google (OAuth)", googleEnabled, "G", "register")}${renderPublicOAuthCard("github", "GitHub", githubEnabled, "◎", "register")}${renderPublicOAuthCard("apple", "Sign in with Apple", appleEnabled, "", "register")}</section>`;
  }

  function renderAuth(page, context) {
    const alternative = page.path === "/login" ? ["/register", "Tạo tài khoản"] : ["/login", "Đăng nhập"];
    const enabled = canAct(page, context);
    const reason = actionBlockReason(page, context);
    const registrationHandoff = page.path === "/login" && new URLSearchParams(window.location.search).get("registered") === "1"
      ? `<div class="portal-notice portal-notice--info"><span class="portal-notice-icon" aria-hidden="true">i</span><div><strong>Tiếp tục bằng đăng nhập</strong><p>Nếu email vừa gửi chưa có tài khoản, hồ sơ đã được tạo. Đăng nhập để khởi tạo signed session và liên kết Telegram.</p></div></div>`
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
    return `<article class="portal-auth-page"><a class="portal-auth-brand" href="/" aria-label="Về trang chủ TOAN AAS"><span class="portal-brand-mark" aria-hidden="true">TA</span><span><strong>TOAN AAS</strong><small>AI workspace · secure access</small></span><em>← Trang chủ</em></a><section class="portal-auth-intro"><div class="portal-eyebrow">TOAN AAS · secure access</div><h1 class="portal-title">${safeText(displayPageTitle(page, context))}</h1><p class="portal-description">${safeText(page.description)}</p>
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
    // Planning may be available before an execution adapter is approved. Give
    // the customer a truthful exit to the Bot menu, but do not serialize the
    // current draft, upload, identity, quote, Xu, session or provider data
    // into Telegram. The user starts the actual Bot workflow independently.
    const executionReady = featureConfirmExecutionReady(page, context);
    const flowGuarded = Boolean(flow && ["guarded", "failed"].includes(String(flow.status || "").toLowerCase()));
    if (page.type !== "feature" || (executionReady && !flowGuarded)) return "";
    const connection = context.telegramConnection && typeof context.telegramConnection === "object" ? context.telegramConnection : {};
    const botUrl = safeTelegramLink(connection.bot_chat_url || "");
    const feature = featureKeyForPage(page, context) || "workflow";
    const handoff = FEATURE_BOT_HANDOFFS[feature] || null;
    const handoffCommand = handoff ? handoff.command : "/menu";
    const handoffLabel = handoff ? handoff.label : "Mở Bot menu";
    const explanation = flowGuarded
      ? "Lần yêu cầu này đang được bridge bảo vệ. Bạn có thể chủ động mở Bot menu để chọn workflow canonical phù hợp."
      : "Web App chưa có adapter tạo job canonical cho workflow này. Bạn vẫn có thể tiếp tục độc lập trong Bot menu.";
    const handoffNote = handoff
      ? `Web chỉ mở Bot / sao chép <code>${safeText(handoffCommand)}</code> để vào đúng nhóm công cụ; không truyền prompt, upload ID, Telegram ID, quote, Xu, session hoặc token.`
      : "Web chỉ mở Bot / sao chép <code>/menu</code>; workflow này chưa có command khởi động riêng an toàn (ví dụ Voice hiện còn guarded/admin-only). Không truyền prompt, upload ID, Telegram ID, quote, Xu, session hoặc token.";
    return `<section class="portal-card portal-card-pad" data-feature-bot-handoff><div class="portal-card-header"><div><h2 class="portal-card-title">Tiếp tục trong Telegram</h2><p class="portal-card-subtitle">${safeText(explanation)}</p></div>${badge(botUrl ? "read_only" : "guarded")}</div><div class="portal-summary-list"><div class="portal-summary-item"><span class="portal-summary-key">Workflow Web</span><span class="portal-summary-value">${safeText(feature)}</span></div><div class="portal-summary-item"><span class="portal-summary-key">Dữ liệu chuyển tiếp</span><span class="portal-summary-value">Không có</span></div></div>${botUrl ? `<div class="portal-form-footer"><span class="portal-form-note">${handoffNote}</span><a class="portal-button portal-button--quiet" href="${safeText(botUrl)}" target="_blank" rel="noopener noreferrer">Mở Bot</a><button class="portal-button portal-button--quiet" type="button" data-portal-action="copy-bot-companion-command" data-copy-text="${safeText(handoffCommand)}">${safeText(handoffLabel)}</button></div>` : `<div class="portal-notice"><span class="portal-notice-icon" aria-hidden="true">i</span><div><strong>Bot URL chưa sẵn sàng</strong><p>Web đang chờ <code>BOT_USERNAME</code> hợp lệ trước khi cung cấp handoff.</p></div></div>`}</section>`;
  }

  function renderWorkspace(page, context) {
    const route = page.routePath || page.path;
    const flow = context.featureFlows && context.featureFlows[route];
    const flowOutput = flow
      ? `<div class="portal-state" data-state="${safeText(flow.status || "guarded")}"><span class="portal-state-icon" aria-hidden="true">○</span><div><h3>${safeText(flow.message || "Core Bridge đã cập nhật trạng thái.")}</h3><p>Trạng thái canonical: ${safeText(STATE_LABELS[flow.status] || flow.status || "guarded")}. ${flow.status === "completed" ? "Output chỉ được cấp qua asset đã xác minh." : "Bản nháp planning có thể hiển thị; output engine vẫn phải qua job và asset hợp lệ."}</p></div></div>${renderCanonicalFlow(flow, route)}${renderFeatureTracking(flow)}`
      : renderEmpty("Chờ phản hồi Core Bridge", "Khi flow hoàn tất, bridge cung cấp trạng thái canonical và asset được xác minh.", "○");
    const voiceVault = page.path.startsWith("/voice") && page.path !== "/voice/outputs" ? renderVoiceVault(context) : "";
    return `<article class="portal-page">${renderHero(page, context)}<div class="portal-status-grid">${renderStatusCard(page, context)}${renderSummary(page, context)}</div>
      <div class="portal-work-grid"><div>${renderFormCard(page, context)}</div><aside class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Tích hợp an toàn</h2><p class="portal-card-subtitle">UI chỉ phát sự kiện có cấu trúc cho lớp FastAPI.</p></div></div>${renderNotes(page)}</aside></div>
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
    const scope = page.path === "/music/sfx-library" ? "sfx" : page.path.startsWith("/image") ? "image" : page.path.startsWith("/video") ? "video" : page.path.startsWith("/voice") ? "voice" : page.path.startsWith("/music") ? "music" : page.path.startsWith("/subtitle") ? "subtitle" : "";
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

  function campaignStatusControls(plan, enabled) {
    const id = String(plan.id);
    const current = campaignPlanStatus(plan);
    const transitions = CAMPAIGN_PLAN_TRANSITIONS[current] || [];
    const choices = [current, ...transitions];
    const options = choices.map((value) => `<option value="${safeText(value)}">${safeText(CAMPAIGN_PLAN_STATUS_LABELS[value] || value)}</option>`).join("");
    const disabled = enabled ? "" : " disabled";
    return `<form class="portal-campaign-review" data-portal-form data-portal-action="campaign-update-status" data-portal-route="/campaigns" data-portal-confirm="Cập nhật trạng thái kế hoạch cục bộ? Thao tác này không publish, không tạo job và không thay đổi Xu." novalidate>
      <input type="hidden" name="plan_id" value="${safeText(id)}">
      <label class="portal-field"><span class="portal-label">Trạng thái kế hoạch</span><select class="portal-select" name="approval_status"${disabled}>${options}</select></label>
      <label class="portal-field"><span class="portal-label">Ghi chú tự rà soát</span><textarea class="portal-textarea" name="review_note" maxlength="1000" placeholder="Điều cần hoàn thiện trước bước tiếp theo…"${disabled}>${safeText(String(plan.review_note || ""))}</textarea></label>
      <div class="portal-form-footer"><span class="portal-form-note">Chỉ thay đổi trạng thái quản lý cá nhân của bản kế hoạch này.</span><button class="portal-button portal-button--quiet" type="submit"${disabled}>Cập nhật</button></div>
    </form>`;
  }

  function campaignEditControls(plan, enabled) {
    const id = String(plan.id);
    const disabled = enabled ? "" : " disabled";
    const optionsFor = (source, selected) => Object.entries(source).map(([value, label]) => `<option value="${safeText(value)}"${value === selected ? " selected" : ""}>${safeText(label)}</option>`).join("");
    const platform = String(plan.platform || "").toLowerCase();
    const objective = String(plan.objective || "").toLowerCase();
    const scheduledFor = typeof plan.scheduled_for === "string" ? plan.scheduled_for.slice(0, 16) : "";
    return `<details class="portal-campaign-edit"><summary>Chỉnh sửa brief &amp; mốc lịch</summary><form class="portal-form" data-portal-form data-portal-action="campaign-update" data-portal-route="/campaigns" data-portal-confirm="Lưu thay đổi kế hoạch cục bộ? Thao tác này không publish, không tạo job và không thay đổi Xu." novalidate>
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
        return `<article class="portal-campaign-card" id="campaign-${safeText(plan.id)}" data-campaign-plan="${safeText(plan.id)}"><div class="portal-campaign-card-head"><div><div class="portal-eyebrow">${safeText(platform)} · ${safeText(objective)}</div><h3>${safeText(String(plan.title || "Kế hoạch chưa đặt tên"))}</h3></div>${badge(status)}</div><dl class="portal-campaign-facts"><div><dt>Liên kết đích</dt><dd>${campaignDestinationLink(plan.destination_url)}</dd></div><div><dt>Mốc lịch</dt><dd>${safeText(campaignScheduleLabel(plan.scheduled_for))}</dd></div><div><dt>Cập nhật</dt><dd>${safeText(campaignScheduleLabel(plan.updated_at))}</dd></div></dl>${campaignEditControls(plan, editEnabled)}${campaignStatusControls(plan, reviewEnabled)}</article>`;
      }).join("")
      : renderEmpty("Chưa có kế hoạch", "Tạo kế hoạch đầu tiên để có bảng lịch và luồng tự rà soát rõ ràng. Không có campaign hoặc nội dung nào được tự động xuất bản.", "✦");
    const scheduleStrip = scheduled.length
      ? `<div class="portal-campaign-timeline">${scheduled.map((plan) => `<a class="portal-campaign-timeline-item" href="#campaign-${safeText(plan.id)}"><span>${safeText(campaignScheduleLabel(plan.scheduled_for))}</span><strong>${safeText(String(plan.title || "Kế hoạch"))}</strong><em>${safeText(CAMPAIGN_PLATFORM_LABELS[String(plan.platform || "").toLowerCase()] || "Khác")}</em></a>`).join("")}</div>`
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
        return `<a class="portal-calendar-event" data-status="${safeText(status)}" href="/campaigns#campaign-${safeText(plan.id)}"><time>${safeText(time)}</time><strong>${safeText(String(plan.title || "Kế hoạch"))}</strong></a>`;
      }).join("");
      const overflow = entries.length > 3 ? `<span class="portal-calendar-overflow">+${entries.length - 3} kế hoạch</span>` : "";
      cells.push(`<div class="portal-calendar-cell${today ? " is-today" : ""}"><span class="portal-calendar-day">${safeText(String(day))}</span><div class="portal-calendar-events">${cards}${overflow}</div></div>`);
    }
    const scheduledCount = plans.filter((plan) => campaignScheduleParts(plan.scheduled_for)).length;
    return `<article class="portal-page portal-campaign-calendar">${renderHero(page, context)}
      <section class="portal-card portal-card-pad portal-campaign-boundary"><div class="portal-state" data-state="read_only"><span class="portal-state-icon" aria-hidden="true">⌁</span><div><h2>Calendar không tạo publish queue</h2><p>Lịch này chỉ đọc các mốc Web-owned của bạn. Mỗi card dẫn lại Campaign Planner; không gửi lịch sang Bot, kênh social hay provider.</p><div class="portal-state-meta"><span>${safeText(String(scheduledCount))} mốc đã lên lịch</span><span>Không reminder tự động</span><span>Không channel automation</span></div></div></div></section>
      <section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">${safeText(localeMonth)}</h2><p class="portal-card-subtitle">Các mốc trong tháng hiện tại theo giờ cục bộ bạn đã nhập. Có thể mở kế hoạch để tự rà soát hoặc đổi trạng thái.</p></div>${badge("read_only")}</div><div class="portal-calendar" role="grid" aria-label="Content Calendar ${safeText(localeMonth)}"><div class="portal-calendar-weekdays" role="row">${weekdayLabels.map((label) => `<span role="columnheader">${safeText(label)}</span>`).join("")}</div><div class="portal-calendar-grid">${cells.join("")}</div></div></section>
      <section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Kế hoạch chưa có mốc lịch</h2><p class="portal-card-subtitle">Đặt ngày giờ trong Campaign Planner khi bạn muốn theo dõi một mốc nội bộ. Không có tác vụ nào tự chạy khi thêm mốc.</p></div>${badge("read_only")}</div>${plans.filter((plan) => !campaignScheduleParts(plan.scheduled_for)).length ? `<div class="portal-feature-jumps">${plans.filter((plan) => !campaignScheduleParts(plan.scheduled_for)).slice(0, 12).map((plan) => `<a class="portal-feature-jump" href="/campaigns#campaign-${safeText(plan.id)}">${safeText(String(plan.title || "Kế hoạch"))}</a>`).join("")}</div>` : renderEmpty("Đã có mốc lịch", "Tất cả kế hoạch đang hiển thị đều có một mốc nội bộ hoặc danh sách hiện tại đang trống.", "✓")}</section>
    </article>`;
  }

  function renderCampaignApprovals(page, context) {
    const plans = campaignPlanItems(context);
    const reviewPlans = plans.filter((plan) => campaignPlanStatus(plan) === "review");
    const draftCount = plans.filter((plan) => campaignPlanStatus(plan) === "draft").length;
    const readyCount = plans.filter((plan) => ["approved", "scheduled"].includes(campaignPlanStatus(plan))).length;
    const reviewEnabled = Boolean(context.session.authenticated && context.session.csrfReady && context.capabilities && context.capabilities["campaign-update-status"] === true);
    const cards = reviewPlans.length
      ? reviewPlans.map((plan) => `<article class="portal-campaign-card" id="approval-${safeText(plan.id)}"><div class="portal-campaign-card-head"><div><div class="portal-eyebrow">${safeText(CAMPAIGN_PLATFORM_LABELS[String(plan.platform || "").toLowerCase()] || "Khác")} · ${safeText(CAMPAIGN_OBJECTIVE_LABELS[String(plan.objective || "").toLowerCase()] || "Mục tiêu")}</div><h3>${safeText(String(plan.title || "Kế hoạch"))}</h3></div>${badge("review")}</div><dl class="portal-campaign-facts"><div><dt>Mốc lịch</dt><dd>${safeText(campaignScheduleLabel(plan.scheduled_for))}</dd></div><div><dt>Liên kết đích</dt><dd>${campaignDestinationLink(plan.destination_url)}</dd></div></dl>${campaignStatusControls(plan, reviewEnabled)}</article>`).join("")
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
      { icon: ICONS.chat, tone: "cyan", title: "Content & Chat", text: "Chat, prompt, caption, hook, kịch bản và storyboard theo cùng một brief.", href: "/login?next=/chat", tag: "Draft trước" },
      { icon: ICONS.image, tone: "blue", title: "Image Studio", text: "Tạo, chỉnh sửa, upscale, image-to-image và xóa nền với input có kiểm tra.", href: "/login?next=/image/create", tag: "Ảnh" },
      { icon: ICONS.video, tone: "violet", title: "Video Studio", text: "Text-to-video, product, trend, multiscene và theo dõi job trong một workspace.", href: "/login?next=/video/create", tag: "Video" },
      { icon: ICONS.voice, tone: "amber", title: "Voice & Audio", text: "TTS, Voice Vault, clone có consent, nhạc AI và SFX theo policy canonical.", href: "/login?next=/voice/tts", tag: "Âm thanh" },
      { icon: ICONS.subtitle, tone: "rose", title: "Subtitle & Dubbing", text: "ASR, SRT, dịch và lồng tiếng luôn hiển thị đúng readiness của pipeline.", href: "/login?next=/subtitle", tag: "Ngôn ngữ" },
      { icon: ICONS.document, tone: "mint", title: "Document Studio", text: "PDF, OCR, gộp/tách/nén và dịch qua job có kiểm tra file và delivery riêng tư.", href: "/login?next=/documents", tag: "Tài liệu" }
    ];
    const studioCards = studios.map((studio) => `<a class="portal-landing-studio portal-landing-studio--${safeText(studio.tone)}" href="${safeText(studio.href)}"><span class="portal-landing-studio-icon" aria-hidden="true">${safeText(studio.icon)}</span><span class="portal-landing-studio-tag">${safeText(studio.tag)}</span><strong>${safeText(studio.title)}</strong><span>${safeText(studio.text)}</span><em>Mở workflow <span aria-hidden="true">→</span></em></a>`).join("");
    return `<article class="portal-landing" aria-label="Giới thiệu TOAN AAS">
      <nav class="portal-landing-nav" aria-label="Điều hướng giới thiệu"><a class="portal-landing-brand" href="/"><span class="portal-brand-mark" aria-hidden="true">TA</span><span><strong>TOAN AAS</strong><small>AI workspace</small></span></a><div class="portal-landing-nav-links"><a href="#studios">Tính năng</a><a href="#workflow">Quy trình</a><a href="#trust">Bảo mật</a></div><div class="portal-landing-nav-actions"><a class="portal-button portal-button--quiet" href="${secondaryHref}">${secondaryLabel}</a><a class="portal-button portal-button--primary" href="${primaryHref}">${primaryLabel}</a></div></nav>
      <section class="portal-landing-hero"><div class="portal-landing-hero-copy"><span class="portal-landing-kicker"><span aria-hidden="true">✦</span> Một workspace AI, có kiểm soát</span><h1>Biến brief thành nội dung, hình ảnh, video và âm thanh — theo đúng luồng làm việc.</h1><p>TOAN AAS gom các công cụ AI vào một portal rõ ràng. Bạn tạo bản nháp, xem ước tính canonical, xác nhận, rồi theo dõi job và tài sản thuộc quyền sở hữu của mình.</p><div class="portal-landing-hero-actions"><a class="portal-button portal-button--primary" href="${primaryHref}">${primaryLabel} <span aria-hidden="true">→</span></a><a class="portal-button" href="/login?next=/features">Khám phá công cụ</a></div><ul class="portal-landing-proof" aria-label="Cam kết sản phẩm"><li><span aria-hidden="true">✓</span> Không tạo output giả</li><li><span aria-hidden="true">✓</span> Xu và PayOS do Bot canonical</li><li><span aria-hidden="true">✓</span> Telegram xác minh một lần</li></ul></div><aside class="portal-landing-preview" aria-label="Minh họa quy trình"><div class="portal-landing-preview-bar"><span></span><span></span><span></span><strong>TOAN AAS / Workspace</strong></div><div class="portal-landing-preview-body"><div class="portal-landing-preview-heading"><span>Video sản phẩm</span><b>Draft</b></div><div class="portal-landing-preview-lines"><i></i><i></i><i></i></div><div class="portal-landing-preview-steps"><span class="is-active">1<br><small>Brief</small></span><span>2<br><small>Estimate</small></span><span>3<br><small>Confirm</small></span><span>4<br><small>Job</small></span></div><div class="portal-landing-preview-callout"><span aria-hidden="true">⌁</span><p><strong>Core Bridge</strong><br>Chỉ Bot quyết định Xu, payment, job và delivery.</p></div></div></aside></section>
      <section class="portal-landing-section" id="studios"><div class="portal-landing-section-heading"><span>AI Studios</span><h2>Một nơi cho toàn bộ workflow sáng tạo.</h2><p>Mỗi studio có route riêng, form phù hợp với bot và trạng thái sẵn sàng trung thực.</p></div><div class="portal-landing-studios">${studioCards}</div></section>
      <section class="portal-landing-workflow" id="workflow"><div><span class="portal-landing-kicker"><span aria-hidden="true">↗</span> Luồng rõ ràng</span><h2>Không có “đã xong” cho đến khi output thật sự được xác minh.</h2><p>Thiết kế Web giữ đúng authority của Bot: browser không gọi provider, không giữ ledger Xu và không tự xác nhận thanh toán.</p></div><ol><li><span>01</span><div><strong>Draft</strong><p>Chuẩn hóa brief và kiểm tra input.</p></div></li><li><span>02</span><div><strong>Estimate</strong><p>Nhận quote từ pricing canonical.</p></div></li><li><span>03</span><div><strong>Confirm</strong><p>Chỉ chuyển tiếp khi job adapter sẵn sàng.</p></div></li><li><span>04</span><div><strong>Delivery</strong><p>Job và file private phải qua ownership check.</p></div></li></ol></section>
      <section class="portal-landing-trust" id="trust"><div class="portal-landing-trust-copy"><span>Trust by design</span><h2>Đủ mạnh cho vận hành, đủ rõ ràng cho khách hàng.</h2><p>Đăng nhập dùng signed session; Telegram xác minh qua deep-link/mã một lần; tài sản chỉ tải qua delivery URL tạm thời đã được kiểm tra.</p></div><div class="portal-landing-trust-grid"><article><span aria-hidden="true">⌁</span><strong>Telegram verified</strong><p>Không nhận Telegram ID thô từ browser.</p></article><article><span aria-hidden="true">◌</span><strong>Canonical wallet</strong><p>Không có ledger Xu hoặc webhook PayOS thứ hai.</p></article><article><span aria-hidden="true">▣</span><strong>Private delivery</strong><p>Output phải đúng owner và được cấp URL ký.</p></article></div></section>
      <footer class="portal-landing-footer"><a class="portal-landing-brand" href="/"><span class="portal-brand-mark" aria-hidden="true">TA</span><span><strong>TOAN AAS</strong><small>AI workspace</small></span></a><span>Draft · Estimate · Confirm · Delivery</span><div><a href="/legal">Điều khoản</a><a href="/privacy">Quyền riêng tư</a></div></footer>
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
      case "campaign-calendar": return renderCampaignCalendar(page, context);
      case "campaign-approvals": return renderCampaignApprovals(page, context);
      case "feature-catalog": return renderFeatureCatalog(page, context);
      case "feature-family": return renderFeatureFamily(page, context);
      case "wallet": return renderWallet(page, context);
      case "catalog": return renderCatalog(page, context);
      case "jobs": return renderJobs(page, context);
      case "job-detail": return renderJobDetail(page, context);
      case "assets": return renderAssets(page, context);
      case "tickets": return renderTickets(page, context);
      case "account": return renderAccount(page, context);
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
    if (form && !form.reportValidity()) {
      const invalid = form.querySelector(":invalid");
      if (invalid && typeof invalid.focus === "function") invalid.focus();
      showToast("Hãy hoàn tất các trường bắt buộc trước khi tiếp tục.", "warning");
      return;
    }
    // Validate before asking for a destructive/financial confirmation so the
    // modal always describes the values that will actually be submitted.
    if (confirmation && !window.confirm(confirmation)) return;
    if (form) rememberTransientFormDraft(form);
    const fields = collectFormFields(form);
    const event = new CustomEvent(ACTION_EVENT, {
      detail: Object.freeze({ action, route, fields, jobFilter: source.getAttribute("data-job-filter") || "", assetFilter: source.getAttribute("data-asset-filter") || "", ticketFilter: source.getAttribute("data-ticket-filter") || "", paymentId: source.getAttribute("data-payment-id") || "", adminJobId: source.getAttribute("data-admin-job-id") || "", adminFeature: source.getAttribute("data-admin-feature") || "", adminFrozen: source.getAttribute("data-admin-frozen") || "", copyText: source.getAttribute("data-copy-text") || "", apiBase: context.apiBase || null }),
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
      if (form) rememberTransientFormDraft(form);
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
    states: Object.freeze({ ...STATE_LABELS })
  });

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", () => mountPortal(), { once: true });
  else mountPortal();
}());
