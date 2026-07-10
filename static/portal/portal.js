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
  try {
    const bootstrap = document.getElementById("portal-bootstrap");
    const parsed = bootstrap && JSON.parse(bootstrap.textContent || "{}");
    if (parsed && typeof parsed === "object") window.__TOAN_AAS_PORTAL__ = parsed;
  } catch (_) {
    window.__TOAN_AAS_PORTAL__ = window.__TOAN_AAS_PORTAL__ || {};
  }
  const ALLOWED_STATES = new Set([
    "ready", "draft", "awaiting_confirm", "queued", "processing",
    "completed", "failed", "guarded", "disabled", "read_only", "error", "empty"
  ]);

  const STATE_LABELS = Object.freeze({
    ready: "Sẵn sàng",
    draft: "Bản nháp",
    awaiting_confirm: "Chờ xác nhận",
    queued: "Đã xếp hàng",
    processing: "Đang xử lý",
    completed: "Hoàn tất",
    read_only: "Chỉ đọc",
    failed: "Thất bại",
    guarded: "Được bảo vệ",
    disabled: "Tạm khóa",
    error: "Lỗi kết nối",
    empty: "Chưa có dữ liệu"
  });

  const ICONS = Object.freeze({
    dashboard: "⌂", account: "◉", wallet: "◌", jobs: "⌛", assets: "▣",
    chat: "◒", prompt: "✦", image: "◩", video: "▶", voice: "◖", music: "♫",
    subtitle: "≡", document: "▤", support: "?", pricing: "◇", legal: "§",
    admin: "⌘", users: "◎", payments: "◈", providers: "◫", system: "⚙",
    reports: "◒", security: "◈", ticket: "✉", default: "·"
  });

  const FIELD_SETS = Object.freeze({
    authLogin: [
      { name: "email", label: "Email", type: "email", placeholder: "you@example.com", autocomplete: "email" },
      { name: "password", label: "Mật khẩu", type: "password", placeholder: "Nhập mật khẩu", autocomplete: "current-password" }
    ],
    authRegister: [
      { name: "name", label: "Tên hiển thị", placeholder: "Tên bạn muốn dùng", autocomplete: "name" },
      { name: "email", label: "Email", type: "email", placeholder: "you@example.com", autocomplete: "email" },
      { name: "password", label: "Mật khẩu", type: "password", placeholder: "Tối thiểu theo chính sách máy chủ", autocomplete: "new-password" },
      { name: "confirm_password", label: "Xác nhận mật khẩu", type: "password", placeholder: "Nhập lại mật khẩu", autocomplete: "new-password" }
    ],
    telegramLink: [
      { name: "telegram_code", label: "Mã liên kết Telegram", placeholder: "Nhập mã dùng một lần", help: "Mã được tạo và xác minh bởi Core Bridge; không lưu trên trình duyệt." }
    ],
    prompt: [
      { name: "request", label: "Yêu cầu", control: "textarea", placeholder: "Mô tả nội dung bạn muốn tạo…", help: "Bản nháp chỉ được chuyển khi phiên, CSRF và Core Bridge đã được máy chủ cấp." },
      { name: "language", label: "Ngôn ngữ đầu ra", control: "select", options: ["Tiếng Việt", "English", "Theo nội dung nguồn"] }
    ],
    image: [
      { name: "prompt", label: "Mô tả hình ảnh", control: "textarea", placeholder: "Chủ thể, phong cách, bối cảnh, tỷ lệ…" },
      { name: "tier", label: "Tier ảnh", control: "select", optionsFrom: "imageTiers", emptyLabel: "Chọn tier từ bảng giá canonical", help: "Giá và quota chỉ do Core Bridge phát hành. Không nhập Xu hoặc giá thủ công." },
      { name: "format", label: "Tỷ lệ khung hình", control: "select", options: ["1:1", "4:5", "16:9", "9:16"] },
      { name: "reference", label: "Tệp tham chiếu", type: "file", help: "Chỉ hiển thị khi upload an toàn và kiểm tra MIME đã được Core Bridge bật." }
    ],
    video: [
      { name: "brief", label: "Brief video", control: "textarea", placeholder: "Mục tiêu, cảnh, chuyển động, giọng đọc…" },
      { name: "tier", label: "Tier video", control: "select", optionsFrom: "videoTiers", emptyLabel: "Chọn tier từ bảng giá canonical", help: "Không nhập giá hoặc Xu; Core Bridge sẽ đối chiếu mã tier với catalog hiện hành." },
      { name: "scene_count", label: "Số cảnh", type: "number", placeholder: "Ví dụ: 3", help: "Dùng để Core Bridge áp dụng đúng giảm giá theo cảnh của bot." },
      { name: "duration", label: "Thời lượng mục tiêu", control: "select", options: ["Theo gói hiện có", "Ngắn", "Tiêu chuẩn", "Nhiều cảnh"] },
      { name: "source", label: "Tệp / hình nguồn", type: "file", help: "Tệp chỉ vào staging canonical sau kiểm tra MIME, chữ ký, kích thước và ownership; browser không gọi provider." }
    ],
    voice: [
      { name: "script", label: "Nội dung lời thoại", control: "textarea", placeholder: "Nhập văn bản để chuẩn bị giọng nói…" },
      { name: "voice_profile_id", label: "Giọng đã lưu (tuỳ chọn)", control: "select", optionsFrom: "voiceProfiles", emptyLabel: "Dùng giọng mặc định do bot cấp", help: "Danh sách chỉ gồm metadata Voice Vault đã qua ownership check. Core Bridge luôn kiểm tra lại lựa chọn khi estimate/confirm." },
      { name: "speed", label: "Tốc độ đọc", control: "select", options: ["normal", "slow", "fast"], help: "Thời lượng hiển thị trong estimate được tính bởi helper canonical của bot." }
    ],
    voiceClone: [
      { name: "display_name", label: "Tên giọng", placeholder: "Ví dụ: Giọng thương hiệu TOAN AAS" },
      { name: "sample", label: "Mẫu audio để clone", type: "file", help: "Mẫu chỉ vào bot-owned staging sau kiểm tra MIME, chữ ký, kích thước và ownership; browser không gửi tới provider." },
      { name: "consent", label: "Quyền sử dụng mẫu giọng", type: "checkbox", help: "Tôi xác nhận mình có quyền sử dụng mẫu giọng này và không mạo danh người khác." }
    ],
    music: [
      { name: "brief", label: "Brief âm nhạc", control: "textarea", placeholder: "Bối cảnh, mood, nhịp độ, công cụ, đối tượng nghe…", help: "Bot sẽ chặn yêu cầu mô phỏng nghệ sĩ/bài hát hoặc giai điệu có bản quyền." },
      { name: "mode", label: "Loại định hướng", control: "select", options: ["background", "melody", "custom"], help: "Chỉ tạo gợi ý prompt canonical; chưa gọi provider tạo nhạc." },
      { name: "duration_seconds", label: "Thời lượng dự kiến (giây)", type: "number", placeholder: "Ví dụ: 30", help: "Báo giá dùng helper duration/price của bot, không tính Xu tại browser." }
    ],
    musicSong: [
      { name: "brief", label: "Brief bài hát", control: "textarea", placeholder: "Thông điệp, mood, cấu trúc, CTA và lời gốc mong muốn…", help: "Không yêu cầu cover, remix hoặc bắt chước nghệ sĩ/bài hát cụ thể." },
      { name: "song_length_mode", label: "Dạng bài hát", control: "select", options: ["seconds", "half", "full"], help: "Chế độ half/full được bot quy đổi theo product kind canonical." },
      { name: "duration_seconds", label: "Thời lượng khi chọn seconds", type: "number", placeholder: "Ví dụ: 30" }
    ],
    musicSfx: [
      { name: "brief", label: "Brief SFX", control: "textarea", placeholder: "Ví dụ: tiếng mở hộp gọn, hiện đại, không có nhạc nền…", help: "Bridge chỉ lưu query/policy và báo giá canonical; không tìm kho ngoài hay giả kết quả." },
      { name: "item_count", label: "Số hiệu ứng dự kiến", type: "number", placeholder: "Ví dụ: 2", help: "SFX library dùng bảng giá standalone của bot, khác với add-on trong video order." },
      { name: "duration_seconds", label: "Thời lượng video tham chiếu (giây)", type: "number", placeholder: "Ví dụ: 30" }
    ],
    musicUpload: [
      { name: "audio", label: "Tệp âm thanh của bạn", type: "file", help: "Tệp chỉ vào bot-owned staging sau kiểm tra MIME/chữ ký/kích thước; chưa ghép hoặc render video." },
      { name: "duration_seconds", label: "Thời lượng tham chiếu (giây)", type: "number", placeholder: "Ví dụ: 30" },
      { name: "notes", label: "Ghi chú dùng nhạc", control: "textarea", placeholder: "Ví dụ: chỉ dùng làm nhạc nền, cần loop…" }
    ],
    subtitleCreate: [
      { name: "source", label: "Tệp audio / video nguồn", type: "file", help: "Core Bridge kiểm tra ownership, MIME và kích thước trước khi nhận tệp; không tự sinh transcript." },
      { name: "duration_seconds", label: "Thời lượng (giây)", type: "number", placeholder: "Ví dụ: 75", help: "Dùng cho estimate canonical; bot áp dụng mức tối thiểu theo phút." },
      { name: "output_format", label: "Định dạng phụ đề", control: "select", options: ["srt", "vtt"], help: "File chỉ xuất hiện sau canonical job, output validation và private asset delivery." }
    ],
    subtitleTranslate: [
      { name: "source", label: "Nguồn SRT/VTT hoặc audio/video", type: "file", help: "Bridge nhận tệp thuộc sở hữu bạn; không tạo bản dịch giả trong browser." },
      { name: "target_language", label: "Ngôn ngữ đích", control: "select", options: ["Tiếng Việt", "English", "Theo yêu cầu"] },
      { name: "duration_seconds", label: "Thời lượng (giây)", type: "number", placeholder: "Ví dụ: 75" },
      { name: "output_format", label: "Định dạng xuất", control: "select", options: ["srt", "vtt"] }
    ],
    dubbing: [
      { name: "source", label: "Tệp audio / video nguồn", type: "file", help: "Tệp cần qua staging canonical trước khi bot báo giá hoặc quyết định khả năng xử lý." },
      { name: "mode", label: "Workflow", control: "select", options: ["dubbing", "subtitle_plus_dubbing"], help: "Chọn rõ lồng tiếng hoặc phụ đề + lồng tiếng; bridge dùng mode canonical của bot." },
      { name: "target_language", label: "Ngôn ngữ đích", control: "select", options: ["Tiếng Việt", "English", "Theo yêu cầu"] },
      { name: "voice", label: "Định hướng giọng", placeholder: "Giọng mặc định hoặc Voice Vault đã kiểm tra" },
      { name: "speed", label: "Tốc độ đọc", control: "select", options: ["normal", "slow", "fast"] },
      { name: "duration_seconds", label: "Thời lượng (giây)", type: "number", placeholder: "Ví dụ: 75" },
      { name: "output_format", label: "Định dạng phụ đề", control: "select", options: ["srt", "vtt"] }
    ],
    documentPdf: [
      { name: "document", label: "Tài liệu nguồn", type: "file", help: "Tệp chỉ vào bot-owned staging sau validation; Web không giữ raw path hoặc bytes lâu dài." },
      { name: "operation", label: "Công cụ PDF", control: "select", options: ["pdf_to_word", "pdf_to_images"], help: "Chỉ nêu đúng tool local có trong bot; delivery vẫn cần canonical job/asset." },
      { name: "page_count", label: "Số trang để báo giá", type: "number", placeholder: "Ví dụ: 3" }
    ],
    documentOcr: [
      { name: "document", label: "Ảnh hoặc PDF nguồn", type: "file", help: "OCR không trả text cho đến khi pipeline canonical tạo output đã kiểm tra." },
      { name: "operation", label: "Loại OCR", control: "select", options: ["ocr_image", "ocr_pdf"] },
      { name: "page_count", label: "Số trang khi OCR PDF", type: "number", placeholder: "Ví dụ: 2" }
    ],
    documentMerge: [
      { name: "documents", label: "Các PDF cần gộp", type: "file", multiple: true, help: "Chọn từ hai PDF trở lên; thứ tự staging là thứ tự gửi. Chưa chạy merge trực tiếp từ browser." },
      { name: "page_count", label: "Tổng trang để báo giá", type: "number", placeholder: "Ví dụ: 8" }
    ],
    documentSplit: [
      { name: "document", label: "PDF nguồn", type: "file" },
      { name: "page_range", label: "Khoảng trang", placeholder: "Ví dụ: 1-3 hoặc 2", help: "Bot canonical chỉ nhận một trang hoặc một khoảng liên tiếp N-M; không dùng danh sách có dấu phẩy." },
      { name: "page_count", label: "Số trang để báo giá", type: "number", placeholder: "Ví dụ: 12" }
    ],
    documentCompress: [
      { name: "document", label: "PDF nguồn", type: "file" },
      { name: "page_count", label: "Số trang để báo giá", type: "number", placeholder: "Ví dụ: 12" },
      { name: "notes", label: "Ghi chú", control: "textarea", placeholder: "Yêu cầu đầu ra (không hứa mức nén chưa có trong helper bot)…" }
    ],
    documentTranslate: [
      { name: "document", label: "Tài liệu nguồn", type: "file", help: "Document translation chưa có quote/delivery adapter bền vững nên sẽ hiển thị guarded đúng trạng thái." },
      { name: "target_language", label: "Ngôn ngữ đích", control: "select", options: ["Tiếng Việt", "English", "Theo yêu cầu"] },
      { name: "notes", label: "Yêu cầu dịch", control: "textarea", placeholder: "Giữ thương hiệu, thuật ngữ, định dạng…" }
    ],
    support: [
      { name: "subject", label: "Chủ đề", placeholder: "Tóm tắt vấn đề" },
      { name: "detail", label: "Nội dung", control: "textarea", placeholder: "Không nhập khoá API, token hoặc dữ liệu thanh toán nhạy cảm.", help: "Tệp đính kèm sẽ chỉ xuất hiện khi ticket adapter canonical hỗ trợ reference upload; form hiện tại không nhận hoặc bỏ qua file." }
    ],
    profile: [
      { name: "display_name", label: "Tên hiển thị", placeholder: "Chờ dữ liệu phiên" },
      { name: "timezone", label: "Múi giờ", control: "select", options: ["Asia/Ho_Chi_Minh", "UTC", "Theo hồ sơ"] },
      { name: "telegram_link", label: "Liên kết Telegram", placeholder: "Mã dùng một lần do bot cấp", help: "Không dùng raw Telegram ID từ form hoặc localStorage." }
    ],
    adminFilter: [
      { name: "query", label: "Tìm kiếm", placeholder: "ID, email hoặc mã job…" },
      { name: "period", label: "Khoảng thời gian", control: "select", options: ["Hôm nay", "7 ngày", "30 ngày", "Theo bộ lọc server"] }
    ]
  });

  const manifest = Object.create(null);
  const featuredModules = [];

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

  function featurePage(path, title, description, icon, fields, aliases) {
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
      ]
    }, aliases);
    featuredModules.push(page);
    return page;
  }

  function readOnlyPage(path, title, description, icon, view, aliases) {
    return definePage({
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
      status: "read_only",
      action: "none",
      actionLabel: "",
      fields: [],
      notes: [
        "Quyền quản trị phải được máy chủ xác nhận từ signed session.",
        "Các thao tác ghi, retry, refund và freeze đều chờ Core Bridge, CSRF và audit event."
      ],
      ...extra
    }, aliases);
  }

  // Public account and portal routes.
  definePage({
    path: "/login", title: "Đăng nhập an toàn", icon: ICONS.account, section: "Tài khoản",
    description: "Đăng nhập email/mật khẩu chỉ được gửi sau khi endpoint signed-session và CSRF được máy chủ bật.",
    access: "public", layout: "auth", status: "ready", action: "auth-login", actionLabel: "Đăng nhập", fields: copyFields(FIELD_SETS.authLogin),
    notes: ["Không lưu raw Telegram ID, token hoặc mật khẩu trên browser.", "Liên kết Telegram sử dụng mã một lần, hết hạn và chống replay."]
  });
  definePage({
    path: "/register", title: "Tạo tài khoản", icon: ICONS.account, section: "Tài khoản",
    description: "Tạo hồ sơ mới với mật khẩu được băm phía máy chủ và giới hạn tốc độ đăng ký.",
    access: "public", layout: "auth", status: "ready", action: "auth-register", actionLabel: "Tạo tài khoản", fields: copyFields(FIELD_SETS.authRegister),
    notes: ["Chính sách mật khẩu và email verification được Core Bridge thực thi.", "Không có tài khoản, session hoặc token nào được giả lập trong shell."]
  });
  customerPage("/onboarding", "Thiết lập tài khoản", "Hoàn thiện hồ sơ và liên kết Telegram bằng mã dùng một lần do bot cấp.", ICONS.account, {
    layout: "onboarding", fields: [], action: "start-telegram-link", actionLabel: "Tạo mã liên kết", status: "guarded",
    notes: ["Mã phải là one-time, hết hạn và được Core Bridge đánh dấu đã dùng.", "Không nhận Telegram ID thô từ URL hay localStorage."]
  });
  customerPage("/account", "Tài khoản & bảo mật", "Quản lý thông tin hồ sơ và trạng thái liên kết theo dữ liệu server-side.", ICONS.account, {
    fields: copyFields(FIELD_SETS.profile), action: "save-profile", actionLabel: "Lưu thay đổi", status: "guarded"
  });
  customerPage("/dashboard", "Không gian làm việc", "Điểm xuất phát cho các bản nháp, job và tài sản do Core Bridge sở hữu.", ICONS.dashboard, {
    layout: "dashboard", action: "none", status: "guarded"
  }, ["/", "/app"]);
  customerPage("/wallet", "Ví Xu", "Số dư, lịch sử và quyền sử dụng Xu chỉ hiển thị từ ledger canonical của bot.", ICONS.wallet, {
    layout: "wallet", action: "none", status: "guarded",
    notes: ["Web App không giữ ledger Xu và không tự cộng/trừ số dư.", "Dữ liệu wallet cần Core Bridge kiểm tra signed session và ownership."]
  });
  customerPage("/wallet/topup", "Nạp Xu", "Khởi tạo thanh toán qua bridge canonical; giao diện này không tạo PayOS link hay webhook.", ICONS.wallet, {
    layout: "wallet", action: "payment-create", actionLabel: "Tạo yêu cầu thanh toán", status: "guarded",
    fields: [
      { name: "package", label: "Gói nạp", control: "select", optionsFrom: "packages", emptyLabel: "Chọn gói từ catalog canonical", help: "Catalog và giá được bot phát hành. Web không tự tính Xu hoặc tạo lại PayOS webhook." },
      { name: "note", label: "Ghi chú (tuỳ chọn)", placeholder: "Không nhập dữ liệu thẻ hoặc khoá bí mật" }
    ],
    notes: ["Payment, amount, signature và webhook chỉ do bot/Core Bridge xử lý.", "Shell không redirect, không finalize và không ghi Xu."]
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
  featurePage("/chat", "AI Chat", "Chuẩn bị hội thoại có ngữ cảnh; Core Bridge quyết định provider, quota và lưu lịch sử.", ICONS.chat, FIELD_SETS.prompt, ["/tools/chat"]);
  featurePage("/prompt-studio", "Prompt Studio", "Soạn và tinh chỉnh prompt thành bản nháp an toàn trước khi xác nhận.", ICONS.prompt, FIELD_SETS.prompt, ["/prompts"]);
  featurePage("/content/caption", "Caption", "Chuẩn bị caption theo brief, giọng điệu và kênh phát hành.", ICONS.prompt, FIELD_SETS.prompt, ["/caption"]);
  featurePage("/content/hashtag", "Hashtag", "Tạo bản nháp hashtag theo nội dung và nền tảng.", ICONS.prompt, FIELD_SETS.prompt, ["/hashtag"]);
  featurePage("/content/hook", "Hook", "Phác thảo hook ngắn để kiểm tra trước khi gọi engine.", ICONS.prompt, FIELD_SETS.prompt, ["/hook"]);
  featurePage("/content/script", "Kịch bản", "Chuẩn bị kịch bản với mục tiêu, giọng điệu và call-to-action.", ICONS.prompt, FIELD_SETS.prompt, ["/script"]);
  featurePage("/content/storyboard", "Storyboard", "Lập storyboard thành bản nháp; chưa tạo media hay trừ Xu.", ICONS.prompt, FIELD_SETS.prompt, ["/storyboard"]);
  featurePage("/content/pack", "Content Pack", "Gom brief nội dung thành một bản nháp có thể ước tính qua bridge.", ICONS.prompt, FIELD_SETS.prompt, ["/content-pack"]);

  featurePage("/image/create", "Tạo ảnh", "Chuẩn bị yêu cầu tạo ảnh và đợi Core Bridge ước tính trước khi xác nhận.", ICONS.image, FIELD_SETS.image, ["/image"]);
  featurePage("/image/edit", "Chỉnh sửa ảnh", "Chuẩn bị thay đổi ảnh; upload và xử lý chỉ diễn ra qua đường dẫn được ký tạm thời.", ICONS.image, FIELD_SETS.image);
  featurePage("/image/upscale", "Nâng cấp ảnh", "Gửi bản nháp upscale; không công bố output khi chưa kiểm tra file hợp lệ.", ICONS.image, FIELD_SETS.image);
  featurePage("/image/transform", "Image-to-Image", "Chuẩn bị biến thể từ ảnh nguồn với toàn bộ quyền kiểm tra ở Core Bridge.", ICONS.image, FIELD_SETS.image, ["/image/image-to-image"]);
  featurePage("/image/remove-background", "Xóa nền", "Tạo bản nháp xóa nền và đợi job hợp lệ trước khi mở tài sản.", ICONS.image, FIELD_SETS.image);
  readOnlyPage("/image/history", "Lịch sử ảnh", "Danh sách output ảnh thuộc phiên sẽ xuất hiện sau khi bridge xác thực.", ICONS.image, "assets", ["/image/assets"]);

  featurePage("/video/create", "Video nhanh", "Chuẩn bị brief video, sau đó ước tính và xác nhận với Core Bridge.", ICONS.video, FIELD_SETS.video, ["/video"]);
  featurePage("/video/long", "Video dài", "Chuẩn bị dự án video dài; tiến độ và output chỉ đến từ job canonical.", ICONS.video, FIELD_SETS.video);
  featurePage("/video/product", "Video sản phẩm", "Chuẩn bị brief video sản phẩm, cảnh và CTA theo flow draft → estimate → confirm.", ICONS.video, FIELD_SETS.video);
  featurePage("/video/text-to-video", "Text-to-Video", "Chuẩn bị yêu cầu text-to-video mà không gọi provider từ trình duyệt.", ICONS.video, FIELD_SETS.video);
  featurePage("/video/image-to-video", "Image-to-Video", "Chuẩn bị input hình nguồn; bridge kiểm tra quyền sở hữu và định dạng.", ICONS.video, FIELD_SETS.video);
  featurePage("/video/trend", "Video xu hướng", "Tạo brief video theo xu hướng và đợi engine có trạng thái sẵn sàng.", ICONS.video, FIELD_SETS.video);
  featurePage("/video/quick", "Quick Video", "Khởi tạo bản nháp video nhanh; không có kết quả giả lập trong UI.", ICONS.video, FIELD_SETS.video);
  featurePage("/video/multiscene", "Video nhiều cảnh", "Chuẩn bị nhiều cảnh và các thành phần media trước bước estimate.", ICONS.video, FIELD_SETS.video);
  readOnlyPage("/video/progress", "Tiến độ video", "Theo dõi các job video được bridge trả về cho phiên sở hữu.", ICONS.video, "jobs");
  readOnlyPage("/video/preview", "Xem trước video", "Chỉ mở preview có URL ký tạm thời và output đã qua validation.", ICONS.video, "assets");
  readOnlyPage("/video/export", "Xuất video", "Xuất file chỉ khi output hoàn tất, thuộc sở hữu người dùng và được ký tạm thời.", ICONS.video, "assets");
  featurePage("/video/add-ons", "Video add-ons", "Chuẩn bị voice, music, subtitle và các add-on trước khi bridge tạo job.", ICONS.video, FIELD_SETS.video);

  readOnlyPage("/voice", "Voice Vault", "Danh mục giọng nói thuộc tài khoản, không hiển thị nếu bridge chưa xác minh phiên.", ICONS.voice, "voices", ["/voice-vault"]);
  featurePage("/voice/tts", "Text-to-Speech", "Chuẩn bị lời thoại và lựa chọn giọng trong flow có estimate rõ ràng.", ICONS.voice, FIELD_SETS.voice, ["/tts", "/voice/create"]);
  featurePage("/voice/saved", "Giọng đã lưu", "Chọn một giọng từ Voice Vault thuộc sở hữu bạn; Core Bridge kiểm tra lại trạng thái trước khi estimate/confirm.", ICONS.voice, FIELD_SETS.voice, ["/voice/vault"]);
  featurePage("/voice/clone", "Voice Clone", "Tính năng clone chỉ khả dụng nếu engine, mẫu audio và quyền sử dụng đã được bridge cho phép.", ICONS.voice, FIELD_SETS.voiceClone);
  readOnlyPage("/voice/preview", "Nghe thử giọng", "Preview là output riêng tư và phải dùng signed/temporary URL.", ICONS.voice, "voices");
  readOnlyPage("/voice/outputs", "Voice outputs", "Tài sản audio đã tạo sẽ xuất hiện tại đây sau delivery hợp lệ.", ICONS.voice, "assets");

  featurePage("/music", "Music Studio", "Không gian chuẩn bị nhạc AI/SFX với prompt, policy và báo giá do bot canonical kiểm soát.", ICONS.music, FIELD_SETS.music);
  readOnlyPage("/music/library", "Thư viện nhạc", "Danh sách nhạc thuộc phiên chỉ được bridge cung cấp sau kiểm tra ownership.", ICONS.music, "assets", ["/music-library"]);
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
  featurePage("/video/mux", "Mux audio & video", "Chuẩn bị mux và fallback; Core Bridge chịu trách nhiệm FFmpeg/output validation.", ICONS.video, FIELD_SETS.video, ["/mux"]);

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
  adminPage("/admin/refunds", "Refund", "Review yêu cầu refund; thao tác cần confirmation, idempotency và audit.", ICONS.payments, { action: "admin-refund", actionLabel: "Gửi yêu cầu refund" });
  adminPage("/admin/jobs", "Jobs", "Theo dõi toàn bộ job, trạng thái delivery và lỗi từ Core Bridge.", ICONS.jobs);
  adminPage("/admin/jobs/failed", "Jobs thất bại", "Xem job thất bại; retry chỉ được bridge quyết định để tránh double-charge.", ICONS.jobs, { action: "admin-retry", actionLabel: "Gửi yêu cầu retry" });
  adminPage("/admin/providers", "Providers & chi phí", "Trạng thái provider/cost do runtime canonical phát hành, không lộ secret.", ICONS.providers);
  adminPage("/admin/workers", "Workers", "Sức khỏe worker và queue chỉ đọc qua bridge có kiểm soát.", ICONS.system);
  adminPage("/admin/features", "Feature readiness", "Kiểm tra trạng thái, guarded mode và maintenance của từng feature.", ICONS.system, { action: "admin-freeze", actionLabel: "Gửi yêu cầu freeze" });
  adminPage("/admin/pricing", "Giá & Xu", "Review pricing catalog; không thay đổi rate hoặc chính sách trong UI tĩnh.", ICONS.pricing);
  adminPage("/admin/packages", "Packages", "Xem và review packages do backend canonical quản lý.", ICONS.pricing);
  adminPage("/admin/promos", "Khuyến mãi", "Quản lý promo phải có permission, confirmation và audit event.", ICONS.pricing);
  adminPage("/admin/leads", "Leads", "Theo dõi lead và CSKH theo quyền server-side.", ICONS.users);
  adminPage("/admin/tickets", "Tickets", "Phân luồng ticket với dữ liệu đã được kiểm soát quyền truy cập.", ICONS.ticket);
  adminPage("/admin/support", "CSKH", "Không gian vận hành hỗ trợ, không hiển thị PII khi bridge chưa cấp quyền.", ICONS.support);
  adminPage("/admin/audit", "Audit logs", "Dấu vết hành động write và quyết định automation phải đến từ audit canonical.", ICONS.security);
  adminPage("/admin/reports", "Báo cáo", "Tạo báo cáo trên server; không export dữ liệu từ shell khi chưa kiểm tra quyền.", ICONS.reports);
  adminPage("/admin/export", "Xuất dữ liệu", "Xuất file qua signed URL sau ownership/permission checks.", ICONS.reports);
  adminPage("/admin/runtime", "Runtime", "Tình trạng runtime và queue chỉ đọc, không thao tác hạ tầng từ browser.", ICONS.system);
  adminPage("/admin/system", "Hệ thống", "Xem thiết lập hệ thống được redaction; write actions không nằm ở shell.", ICONS.system);
  adminPage("/admin/backup", "Sao lưu", "Trạng thái backup/disaster recovery là dữ liệu server-side được phân quyền.", ICONS.system);
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
      catalog: Array.isArray(source.catalog) ? source.catalog.slice(0, 24) : [],
      apiBase: typeof source.apiBase === "string" ? source.apiBase : "",
      session,
      bridge,
      capabilities,
      pageStates,
      featureFlows,
      wallet: source.wallet && typeof source.wallet === "object" ? source.wallet : null,
      walletHistory: Array.isArray(source.walletHistory) ? source.walletHistory : [],
      jobs: Array.isArray(source.jobs) ? source.jobs : [],
      jobDetail: source.jobDetail && typeof source.jobDetail === "object" ? source.jobDetail : {},
      assets: Array.isArray(source.assets) ? source.assets : [],
      tickets: Array.isArray(source.tickets) ? source.tickets : [],
      adminData: source.adminData && typeof source.adminData === "object" ? source.adminData : {},
      pricingCatalog: source.pricingCatalog && typeof source.pricingCatalog === "object" ? source.pricingCatalog : {},
      packageCatalog: source.packageCatalog && typeof source.packageCatalog === "object" ? source.packageCatalog : {},
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
    const stateValue = context.pageStates[page.path];
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
    if (page.action === "start-telegram-link" || page.action === "refresh-link-status") return context.session.authenticated === true && csrfReady && capability;
    if (page.access === "admin" && !context.isAdmin) return false;
    return context.session.authenticated === true && csrfReady && bridgeReady && capability;
  }

  function actionBlockReason(page, context) {
    if (page.access === "admin" && !context.isAdmin) return "Cần signed admin session do máy chủ xác minh.";
    if (context.bridge.available !== true && page.access !== "public") return "Core Bridge chưa được máy chủ bật cho phiên này.";
    if (context.session.csrfReady !== true && context.bridge.csrfReady !== true) return "CSRF chưa sẵn sàng; yêu cầu write bị khóa an toàn.";
    if (context.session.authenticated !== true && page.access !== "public") return "Cần signed session trước khi tạo yêu cầu.";
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

  function initials(name) {
    return safeText((name || "T").trim().charAt(0).toUpperCase() || "T");
  }

  function navGroups(context, currentPage) {
    const groups = [
      {
        label: "Tổng quan",
        links: [
          ["/dashboard", "Dashboard", ICONS.dashboard], ["/jobs", "Job Center", ICONS.jobs], ["/assets", "Tài sản", ICONS.assets]
        ]
      },
      {
        label: "AI Studio",
        links: [
          ["/chat", "AI Chat", ICONS.chat], ["/prompt-studio", "Prompt Studio", ICONS.prompt], ["/image/create", "Image", ICONS.image],
          ["/video/product", "Video", ICONS.video], ["/voice/tts", "Voice", ICONS.voice], ["/music", "Music", ICONS.music],
          ["/subtitle", "Ngôn ngữ", ICONS.subtitle], ["/documents", "Documents", ICONS.document]
        ]
      },
      {
        label: "Tài khoản",
        links: [
          ["/wallet", "Ví Xu", ICONS.wallet], ["/support", "Hỗ trợ", ICONS.support], ["/account", "Tài khoản", ICONS.account]
        ]
      }
    ];
    if (context.isAdmin || currentPage.access === "admin" || currentPage.path.indexOf("/admin") === 0) {
      groups.push({
        label: "Admin ERP",
        links: [
          ["/admin", "Overview", ICONS.admin], ["/admin/users", "Người dùng", ICONS.users], ["/admin/jobs", "Jobs", ICONS.jobs],
          ["/admin/payments", "Thanh toán", ICONS.payments], ["/admin/providers", "Providers", ICONS.providers], ["/admin/audit", "Audit", ICONS.security]
        ]
      });
    }
    return groups;
  }

  function isNavCurrent(linkPath, page) {
    if (linkPath === "/dashboard") return page.path === "/dashboard";
    if (linkPath === "/admin") return page.path === "/admin";
    return page.path === linkPath || page.path.indexOf(`${linkPath}/`) === 0;
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
      const help = field.help ? `<span class="portal-field-help">${safeText(field.help)}</span>` : "";
      const rawValue = Object.prototype.hasOwnProperty.call(values, field.name) ? values[field.name] : "";
      const value = rawValue === undefined || rawValue === null ? "" : String(rawValue);
      const stagedUploadCount = field.type === "file" && Array.isArray(values.upload_ids) ? values.upload_ids.filter((item) => typeof item === "string" && item).length : 0;
      const staged = stagedUploadCount ? `<span class="portal-field-staged">${safeText(String(stagedUploadCount))} tệp đã vào staging canonical; không cần chọn lại để estimate/confirm.</span>` : "";
      let control;
      if (field.control === "textarea") {
        control = `<textarea class="portal-textarea" id="${id}" name="${safeText(field.name)}" placeholder="${safeText(field.placeholder)}"${disabled}>${safeText(value)}</textarea>`;
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
        const empty = field.emptyLabel ? `<option value=""${value === "" ? " selected" : ""}>${safeText(field.emptyLabel)}</option>` : "";
        const optionMarkup = options.map((option) => {
          const value = option && typeof option === "object" ? option.value : option;
          const label = option && typeof option === "object" ? option.label : option;
          const selected = String(value) === String(rawValue) ? " selected" : "";
          return `<option value="${safeText(value)}"${selected}>${safeText(label)}</option>`;
        }).join("");
        control = `<select class="portal-select" id="${id}" name="${safeText(field.name)}"${disabled}>${empty}${optionMarkup}</select>`;
      } else if (field.type === "checkbox") {
        const checked = rawValue === true || rawValue === "true" || rawValue === 1 || rawValue === "1" ? " checked" : "";
        control = `<label class="portal-checkbox" for="${id}"><input id="${id}" name="${safeText(field.name)}" type="checkbox" value="true"${checked}${disabled}><span>Tôi xác nhận</span></label>`;
      } else {
        const type = ["email", "password", "file", "number", "text"].includes(field.type) ? field.type : "text";
        const autocomplete = field.autocomplete ? ` autocomplete="${safeText(field.autocomplete)}"` : "";
        const multiple = type === "file" && field.multiple ? " multiple" : "";
        const valueAttribute = type === "file" || type === "password" ? "" : ` value="${safeText(value)}"`;
        control = `<input class="portal-input" id="${id}" name="${safeText(field.name)}" type="${type}" placeholder="${safeText(field.placeholder)}"${valueAttribute}${autocomplete}${multiple}${disabled}>`;
      }
      return `<div class="portal-field${wide ? " portal-field--wide" : ""}"><label for="${id}">${safeText(field.label)}</label>${control}${help}${staged}</div>`;
    }).join("")}</div>`;
  }

  function statusMessage(page, status, context) {
    if (status === "ready") return { icon: "✓", title: "Giao diện đã sẵn sàng", text: "Chỉ các khả năng đã được máy chủ ký và cấp cho phiên mới được bật." };
    if (status === "empty") return { icon: "○", title: "Chưa có dữ liệu để hiển thị", text: "Portal không tự tạo job, số dư, file hay output. Dữ liệu sẽ xuất hiện sau phản hồi Core Bridge hợp lệ." };
    if (status === "error" || status === "failed") return { icon: "!", title: "Chưa thể xác thực trạng thái", text: "Không có thao tác fallback hay giả lập. Hãy đợi Core Bridge trả trạng thái an toàn." };
    if (status === "queued" || status === "processing") return { icon: "◌", title: "Job đang do Core Bridge điều phối", text: "Chỉ trạng thái engine canonical mới có thể chuyển job sang completed." };
    if (status === "draft" || status === "awaiting_confirm") return { icon: "◇", title: "Bản nháp chờ luồng xác nhận", text: "Core Bridge phải estimate trước, sau đó người dùng xác nhận để tạo job." };
    if (status === "completed") return { icon: "✓", title: "Output đã hoàn tất", text: "Output cần được bridge xác thực file, ownership và URL ký tạm thời trước khi mở tải xuống." };
    if (status === "read_only") return { icon: "i", title: "Dữ liệu canonical chỉ đọc", text: "Portal đang hiển thị dữ liệu bot đã được role-check; mọi thay đổi vẫn cần adapter, confirmation, CSRF và audit riêng." };
    if (status === "disabled") return { icon: "—", title: "Tính năng đang tạm khóa", text: "Trạng thái maintenance/freeze phải được bridge quản lý; browser không thể tự bật lại." };
    const isAdmin = page.access === "admin" && !context.isAdmin;
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
    const canAdvance = enabled && page.action === "feature-draft" && (flowStatus === "draft" || flowStatus === "awaiting_confirm");
    const formId = `portal-form-${safeText(route).replace(/[^a-zA-Z0-9_-]/g, "-")}`;
    const flowControls = canAdvance
      ? `<div class="portal-flow-actions"><button class="portal-button portal-button--quiet" type="button" data-portal-action="feature-estimate" data-portal-route="${safeText(route)}" data-portal-form-id="${safeText(formId)}">Ước tính Xu</button>${flowStatus === "awaiting_confirm" ? `<button class="portal-button portal-button--primary" type="button" data-portal-action="feature-confirm" data-portal-route="${safeText(route)}" data-portal-form-id="${safeText(formId)}">Xác nhận chạy</button>` : ""}</div>`
      : "";
    return `<section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">${page.layout === "auth" ? "Thông tin xác thực" : "Chuẩn bị yêu cầu"}</h2><p class="portal-card-subtitle">${enabled ? "Yêu cầu sẽ được chuyển tới lớp tích hợp thông qua custom event, không gọi trực tiếp từ UI." : safeText(reason)}</p></div>${badge(flowStatus || stateFor(page, context))}</div>
      <form class="portal-form" id="${safeText(formId)}" data-portal-form novalidate>${renderFields(page.fields, enabled, context, flow && flow.input)}
        <div class="portal-form-footer"><span class="portal-form-note">${enabled ? "Máy chủ vẫn phải xác minh phiên, CSRF, schema, ownership và idempotency." : "Các trường bị khóa cho tới khi máy chủ cấp khả năng cần thiết."}</span>
          <button class="portal-button portal-button--primary" type="button" data-portal-action="${safeText(page.action)}" data-portal-route="${safeText(page.path)}"${enabled ? "" : ` disabled title="${safeText(reason)}"`}>${safeText(page.actionLabel || "Tiếp tục")}</button>
        </div>
      </form>${flowControls}</section>`;
  }

  function renderHero(page, context) {
    const state = stateFor(page, context);
    const route = page.routePath || page.path;
    const linkPending = page.action === "start-telegram-link" && context.linkFlow && context.linkFlow.data && context.linkFlow.data.code && !(context.linkStatus && context.linkStatus.linked === true);
    const hasAction = page.action && page.action !== "none" && !linkPending;
    const enabled = hasAction && canAct(page, context);
    const reason = actionBlockReason(page, context);
    return `<section class="portal-hero"><div class="portal-hero-copy"><div class="portal-eyebrow">${safeText(page.section || "TOAN AAS")}</div>
      <h1 class="portal-title">${safeText(context.title || page.title)}</h1><p class="portal-description">${safeText(page.description)}</p></div>
      <div class="portal-hero-actions">${badge(state)}${hasAction ? `<button class="portal-button portal-button--primary" type="button" data-portal-action="${safeText(page.action)}" data-portal-route="${safeText(route)}"${enabled ? "" : ` disabled title="${safeText(reason)}"`}>${safeText(page.actionLabel)}</button>` : ""}</div>
    </section>`;
  }

  function renderModuleCards(context) {
    const catalogRoutes = new Set((context.catalog || []).map((entry) => typeof entry === "string" ? entry : entry && entry.path).filter(Boolean));
    const cards = featuredModules.slice(0, 18).map((module) => {
      const label = catalogRoutes.size && !catalogRoutes.has(module.path) ? "Chờ catalog" : "Mở workspace";
      return `<a class="portal-module-card" href="${module.path}"><div class="portal-module-card-top"><span class="portal-module-icon" aria-hidden="true">${safeText(module.icon)}</span>${badge(stateFor(module, context))}</div>
        <div><h3>${safeText(module.title)}</h3><p>${safeText(module.description)}</p></div><span class="portal-module-card-footer"><span>${label}</span><span class="portal-module-arrow" aria-hidden="true">→</span></span></a>`;
    }).join("");
    return `<section><div class="portal-section-heading"><div><span class="portal-section-kicker">Tất cả công cụ</span><h2>Workspace theo feature parity</h2><p>Chỉ route và trạng thái được khai báo; không mô phỏng output.</p></div><a class="portal-button portal-button--quiet" href="/prompt-studio">Mở Prompt Studio →</a></div><div class="portal-module-grid">${cards}</div></section>`;
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
      <section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Tài sản gần đây</h2><p class="portal-card-subtitle">Chỉ metadata riêng tư; file phải chờ delivery ký.</p></div><a class="portal-button portal-button--quiet" href="/assets">Mở tài sản →</a></div>${renderRowsTable(["Tài sản", "Tính năng", "Trạng thái", "Delivery"], assets, (item) => `<td>${safeText(item.id || "—")}</td><td>${safeText(item.feature || "—")}</td><td>${badge(jobStatus(item))}</td><td>${deliveryPending()}</td>`, "Chưa có asset metadata", "Không dùng placeholder để thay thế một output đã được xác minh.")}</section></div>`;
    return `<article class="portal-page">${renderHero(page, context)}<div class="portal-status-grid">${renderStatusCard(page, context)}${renderSummary(page, context)}</div>${quickMetrics}${renderStudioLaunchpad(context)}${renderModuleCards(context)}${activity}</article>`;
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

  function renderWallet(page, context) {
    const topup = page.path === "/wallet/topup";
    const wallet = context.wallet && typeof context.wallet === "object" ? context.wallet : null;
    const history = Array.isArray(context.walletHistory) ? context.walletHistory : [];
    const walletCard = wallet
      ? `<section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Số dư canonical</h2><p class="portal-card-subtitle">Dữ liệu được đọc từ bot qua private bridge, không tính lại trong browser.</p></div>${badge("completed")}</div><div class="portal-admin-grid"><div class="portal-metric"><span>Số dư</span><strong>${safeText(String(wallet.balance_xu || 0))} Xu</strong><em>Canonical wallet</em></div><div class="portal-metric"><span>Đã dùng</span><strong>${safeText(String(wallet.total_spent_xu || 0))} Xu</strong><em>Lịch sử canonical</em></div><div class="portal-metric"><span>Gói</span><strong>${safeText((wallet.plan && (wallet.plan.plan_name || wallet.plan.current_plan)) || "—")}</strong><em>${safeText((wallet.plan && wallet.plan.plan_status) || "Không có gói")}</em></div></div></section>`
      : `<section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Số dư canonical</h2><p class="portal-card-subtitle">Số dư không được cache hoặc tính lại tại browser.</p></div>${badge("guarded")}</div>${renderEmpty("Chờ dữ liệu ví", "Core Bridge phải trả số dư và lịch sử đã xác minh cho signed session.", "◌")}</section>`;
    return `<article class="portal-page">${renderHero(page, context)}<div class="portal-status-grid">${renderStatusCard(page, context)}${renderSummary(page, context)}</div>
      <div class="portal-work-grid"><div>${topup ? renderFormCard(page, context) : walletCard}</div>
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
    ["all", "Tất cả"], ["queued", "Đã xếp hàng"], ["processing", "Đang xử lý"], ["completed", "Hoàn tất"], ["failed", "Thất bại"]
  ]);

  function jobStatus(item) {
    const value = String(item && item.status || "guarded").toLowerCase();
    if (ALLOWED_STATES.has(value)) return value;
    const aliases = { pending: "queued", new: "queued", running: "processing", success: "completed", succeeded: "completed", paid: "completed", active: "ready", inactive: "disabled", cancelled: "failed", canceled: "failed", error: "failed" };
    return aliases[value] || "guarded";
  }

  function reportedOutput(item) {
    return item && item.output_available
      ? `<span class="portal-delivery-state" data-delivery="reported">Engine đã báo output</span>`
      : `<span class="portal-delivery-state" data-delivery="waiting">Chưa có metadata</span>`;
  }

  function deliveryPending() {
    return `<span class="portal-delivery-state" data-delivery="pending">Chờ delivery canonical</span>`;
  }

  function renderJobs(page, context) {
    const allJobs = Array.isArray(context.jobs) ? context.jobs : [];
    const selected = JOB_FILTERS.some(([value]) => value === context.jobFilter) ? context.jobFilter : "all";
    const jobs = selected === "all" ? allJobs : allJobs.filter((item) => jobStatus(item) === selected);
    const refreshEnabled = context.capabilities && context.capabilities["refresh-jobs"] === true;
    const counts = Object.fromEntries(JOB_FILTERS.map(([status]) => [status, status === "all" ? allJobs.length : allJobs.filter((item) => jobStatus(item) === status).length]));
    const filters = `<div class="portal-filter-bar" aria-label="Lọc job">${JOB_FILTERS.map(([status, label]) => `<button class="portal-filter-button${selected === status ? " is-active" : ""}" type="button" data-portal-action="filter-jobs" data-job-filter="${status}" aria-pressed="${selected === status}">${safeText(label)} <span>${safeText(String(counts[status] || 0))}</span></button>`).join("")}</div>`;
    return `<article class="portal-page">${renderHero(page, context)}<div class="portal-status-grid">${renderStatusCard(page, context)}${renderSummary(page, context)}</div>
      <section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Danh sách job</h2><p class="portal-card-subtitle">Chỉ bao gồm job thuộc signed session hiện tại. “Engine đã báo output” chưa đồng nghĩa có file Web để tải.</p></div><div class="portal-inline-actions"><button class="portal-button portal-button--quiet" type="button" data-portal-action="refresh-jobs" data-portal-route="/jobs"${refreshEnabled ? "" : " disabled"}>Làm mới</button><a class="portal-button portal-button--quiet" href="/assets">Mở tài sản →</a></div></div>${filters}${renderRowsTable(["Job", "Tính năng", "Trạng thái", "Cập nhật", "Output engine"], jobs, (item) => `<td><a href="/jobs/${encodeURIComponent(item.id || "")}">${safeText(item.id || "—")}</a></td><td>${safeText(item.feature || "—")}</td><td>${badge(jobStatus(item))}</td><td>${safeText(item.updated_at || item.created_at || "—")}</td><td>${reportedOutput(item)}</td>`, selected === "all" ? "Chưa có job được xác minh" : "Không có job ở trạng thái này", selected === "all" ? "Core Bridge sẽ trả job sau khi tạo/confirm thành công." : "Đổi bộ lọc hoặc làm mới để nhận trạng thái canonical mới nhất.")}</section>
      <section class="portal-card portal-card-pad"><div class="portal-notice portal-notice--info"><span class="portal-notice-icon" aria-hidden="true">i</span><div><strong>Delivery được tách riêng khỏi engine</strong><p>Job completed hoặc metadata output không tạo preview/download. Cần một signed delivery contract, ownership check và validation artifact trước khi Web mở file.</p></div></div></section></article>`;
  }

  function renderJobDetail(page, context) {
    const record = safeText(page.recordId || "—");
    const job = context.jobDetail && typeof context.jobDetail === "object" ? context.jobDetail : null;
    const detail = job && Object.keys(job).length
      ? `<div class="portal-summary-list"><div class="portal-summary-item"><span class="portal-summary-key">Tính năng</span><span class="portal-summary-value">${safeText(job.feature || job.job_type || "—")}</span></div><div class="portal-summary-item"><span class="portal-summary-key">Trạng thái</span><span class="portal-summary-value">${safeText(job.status || "—")}</span></div><div class="portal-summary-item"><span class="portal-summary-key">Cập nhật</span><span class="portal-summary-value">${safeText(job.updated_at || job.created_at || "—")}</span></div><div class="portal-summary-item"><span class="portal-summary-key">Output engine</span><span class="portal-summary-value">${job.output_available ? "Có metadata output" : "Chưa có metadata"}</span></div><div class="portal-summary-item"><span class="portal-summary-key">Delivery Web</span><span class="portal-summary-value">Chờ signed delivery canonical</span></div></div>`
      : renderEmpty("Chưa có job detail an toàn", "Bridge cần kiểm tra ownership trước khi trả request, timeline và output của job này.", "⌛");
    return `<article class="portal-page">${renderHero(page, context)}<div class="portal-status-grid">${renderStatusCard(page, context)}${renderSummary(page, context)}</div>
      <div class="portal-work-grid"><section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Job ${record}</h2><p class="portal-card-subtitle">ID hiển thị không xác thực dữ liệu hoặc quyền download.</p></div>${badge(job && job.status ? job.status : stateFor(page, context))}</div>${detail}</section>
      <aside class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Delivery protection</h2><p class="portal-card-subtitle">Không có download trực tiếp từ path đoán được.</p></div>${deliveryPending()}${renderNotes(page)}</aside></div></article>`;
  }

  function renderAssets(page, context) {
    const assets = Array.isArray(context.assets) ? context.assets : [];
    const refreshEnabled = context.capabilities && context.capabilities["refresh-assets"] === true;
    return `<article class="portal-page">${renderHero(page, context)}<div class="portal-status-grid">${renderStatusCard(page, context)}${renderSummary(page, context)}</div>
      <section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Tài sản riêng tư</h2><p class="portal-card-subtitle">Preview và download cần output validation, ownership check và signed URL. Metadata không phải file được cấp quyền.</p></div><button class="portal-button portal-button--quiet" type="button" data-portal-action="refresh-assets" data-portal-route="/assets"${refreshEnabled ? "" : " disabled"}>Làm mới</button></div>${renderRowsTable(["Tài sản", "Tính năng", "Trạng thái", "Tạo lúc", "Delivery"], assets, (item) => `<td>${safeText(item.id || "—")}</td><td>${safeText(item.feature || "—")}</td><td>${badge(item.status || "guarded")}</td><td>${safeText(item.created_at || "—")}</td><td>${deliveryPending()}</td>`, "Chưa có tài sản có thể mở", "Shell không hiển thị placeholder là output thật. Tài sản hoàn tất sẽ đến từ Core Bridge.")}</section></article>`;
  }

  function renderTickets(page, context) {
    const tickets = Array.isArray(context.tickets) ? context.tickets : [];
    return `<article class="portal-page">${renderHero(page, context)}<div class="portal-status-grid">${renderStatusCard(page, context)}${renderSummary(page, context)}</div>
      <section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Yêu cầu hỗ trợ</h2><p class="portal-card-subtitle">Nội dung ticket chỉ hiện cho người sở hữu hoặc nhân sự được cấp quyền.</p></div><a class="portal-button portal-button--quiet" href="/support">Tạo ticket →</a></div>${renderRowsTable(["Mã ticket", "Chủ đề", "Trạng thái", "Cập nhật"], tickets, (item) => `<td>${safeText(item.id || "—")}</td><td>${safeText(item.subject || "—")}</td><td>${badge(item.status || "guarded")}</td><td>${safeText(item.updated_at || item.created_at || "—")}</td>`, "Chưa có ticket được cấp", "Core Bridge sẽ trả ticket theo signed session.")}</section></article>`;
  }

  function renderLegal(page, context) {
    const privacy = page.path === "/privacy";
    return `<article class="portal-page">${renderHero(page, context)}<section class="portal-card portal-card-pad"><div class="portal-notice portal-notice--info"><span class="portal-notice-icon" aria-hidden="true">i</span><div><strong>Khung nội dung phiên bản hóa</strong><p>${privacy ? "Chính sách chính thức cần được máy chủ phát hành cùng phiên bản và ngày hiệu lực." : "Điều khoản chính thức cần được máy chủ phát hành cùng phiên bản và ngày hiệu lực."}</p></div></div>
      <div class="portal-panel-list" style="margin-top:16px"><div class="portal-panel-row"><span class="portal-panel-row-icon">1</span><div><strong>${privacy ? "Thu thập tối thiểu" : "Sử dụng có trách nhiệm"}</strong><span>${privacy ? "Portal không tự lưu raw Telegram ID, token, password, wallet ledger hoặc file output." : "Provider, payment, job và Xu được điều phối bởi Core Bridge canonical."}</span></div></div>
        <div class="portal-panel-row"><span class="portal-panel-row-icon">2</span><div><strong>${privacy ? "Quyền truy cập" : "Xác nhận rõ ràng"}</strong><span>${privacy ? "Dữ liệu riêng tư cần ownership và role check server-side trước khi render hoặc tải xuống." : "Flow feature sử dụng draft → estimate → confirm → queued/processing → completed/failed/guarded."}</span></div></div>
        <div class="portal-panel-row"><span class="portal-panel-row-icon">3</span><div><strong>Thông báo cập nhật</strong><span>Văn bản pháp lý đầy đủ sẽ thay thế khung này khi module content được đưa vào production.</span></div></div></div>
    </section></article>`;
  }

  function safeTelegramLink(value) {
    if (typeof value !== "string" || !value) return "";
    try {
      const url = new URL(value);
      return url.protocol === "https:" && (url.hostname === "t.me" || url.hostname.endsWith(".t.me")) ? url.href : "";
    } catch (_) {
      return "";
    }
  }

  function renderOnboarding(page, context) {
    const flow = context.linkFlow && typeof context.linkFlow === "object" ? context.linkFlow : {};
    const data = flow.data && typeof flow.data === "object" ? flow.data : {};
    const status = context.linkStatus && typeof context.linkStatus === "object" ? context.linkStatus : {};
    const linked = status.linked === true || context.bridge.available === true;
    const enabled = canAct(page, context);
    const reason = actionBlockReason(page, context);
    const code = typeof data.code === "string" && data.code ? data.code : "";
    const deepLink = safeTelegramLink(data.deep_link);
    const pending = code
      ? `<section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Xác minh trong Telegram</h2><p class="portal-card-subtitle">Mã chỉ sống trong phiên này; không được lưu trong localStorage hoặc gửi sang provider.</p></div>${badge("awaiting_confirm")}</div>
        <div class="portal-summary-list"><div class="portal-summary-item"><span class="portal-summary-key">Mã một lần</span><code class="portal-link-code">${safeText(code)}</code></div><div class="portal-summary-item"><span class="portal-summary-key">Hiệu lực</span><span class="portal-summary-value">${safeText(String(data.expires_in_minutes || "—"))} phút</span></div></div>
        <div class="portal-form-footer"><span class="portal-form-note">Mở bot TOAN AAS, dùng deep link hoặc gửi <code>/linkweb &lt;mã&gt;</code>. Bot là authority duy nhất xác minh Telegram identity.</span>${deepLink ? `<a class="portal-button portal-button--primary" href="${safeText(deepLink)}" target="_blank" rel="noopener noreferrer">Mở Telegram</a>` : ""}<button class="portal-button portal-button--quiet" type="button" data-portal-action="refresh-link-status" data-portal-route="/onboarding"${enabled ? "" : ` disabled title="${safeText(reason)}"`}>Kiểm tra liên kết</button><button class="portal-button portal-button--quiet" type="button" data-portal-action="start-telegram-link" data-portal-route="/onboarding" data-portal-confirm="Tạo mã mới sẽ hủy mã đang hiển thị. Bạn có chắc muốn tiếp tục?"${enabled ? "" : ` disabled title="${safeText(reason)}"`}>Tạo mã mới</button></div>
      </section>`
      : `<section class="portal-card portal-card-pad">${renderEmpty("Chưa có mã liên kết", "Tạo mã một lần, sau đó xác minh trong bot TOAN AAS. Browser không nhận Telegram ID hoặc token thô.", "⌁")}</section>`;
    const completed = `<section class="portal-card portal-card-pad"><div class="portal-state" data-state="completed"><span class="portal-state-icon" aria-hidden="true">✓</span><div><h2>Telegram đã liên kết</h2><p>Phiên Web có thể đọc dữ liệu canonical qua Core Bridge. Xu, PayOS, job và provider vẫn do bot điều phối.</p><div class="portal-state-meta"><span>Identity canonical đã xác minh</span><span>Không lưu Telegram ID ở browser</span></div></div></div><div class="portal-form-footer"><a class="portal-button portal-button--primary" href="/dashboard">Vào Dashboard</a></div></section>`;
    return `<article class="portal-page">${renderHero(page, context)}<div class="portal-status-grid">${renderStatusCard(page, context)}${renderSummary(page, context)}</div>
      ${linked ? completed : pending}
      <section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Cách hoạt động</h2><p class="portal-card-subtitle">Luồng liên kết không lặp lại webhook hoặc PayOS.</p></div></div><div class="portal-panel-list"><div class="portal-panel-row"><span class="portal-panel-row-icon">1</span><div><strong>Tạo mã một lần</strong><span>Web server tạo, băm và đặt hạn dùng cho mã liên kết.</span></div></div><div class="portal-panel-row"><span class="portal-panel-row-icon">2</span><div><strong>Xác nhận trong bot</strong><span>Bot xác minh Telegram identity và gọi callback nội bộ đã ký.</span></div></div><div class="portal-panel-row"><span class="portal-panel-row-icon">3</span><div><strong>Quay lại portal</strong><span>Portal kiểm tra trạng thái signed session; không tự nhận quyền từ dữ liệu browser.</span></div></div></div></section></article>`;
  }

  function renderAuth(page, context) {
    const alternative = page.path === "/login" ? ["/register", "Tạo tài khoản"] : ["/login", "Đăng nhập"];
    const enabled = canAct(page, context);
    const reason = actionBlockReason(page, context);
    return `<article class="portal-auth-page"><section class="portal-auth-intro"><div class="portal-eyebrow">TOAN AAS · secure access</div><h1 class="portal-title">${safeText(context.title || page.title)}</h1><p class="portal-description">${safeText(page.description)}</p>
      <div class="portal-auth-facts"><div class="portal-auth-fact"><strong>Signed session</strong><span>Cookie/session do server quản lý, không dùng raw localStorage.</span></div><div class="portal-auth-fact"><strong>Telegram link</strong><span>Mã dùng một lần, hết hạn và chống replay.</span></div><div class="portal-auth-fact"><strong>CSRF</strong><span>Mọi thao tác ghi phải có CSRF hợp lệ.</span></div><div class="portal-auth-fact"><strong>Rate limit</strong><span>Login/register được giới hạn tại Web server; Core Bridge chỉ nhận yêu cầu đã xác thực.</span></div></div>
    </section><section class="portal-card portal-card-pad portal-auth-card"><div class="portal-card-header"><div><h2 class="portal-card-title">${safeText(page.title)}</h2><p class="portal-card-subtitle">${enabled ? "Endpoint đã được server cấp khả năng." : safeText(reason)}</p></div>${badge(stateFor(page, context))}</div>
      <form class="portal-form" data-portal-form novalidate>${renderFields(page.fields, enabled, context)}<div class="portal-form-footer"><a class="portal-button portal-button--quiet" href="${alternative[0]}">${alternative[1]} →</a><button class="portal-button portal-button--primary" type="button" data-portal-action="${safeText(page.action)}" data-portal-route="${safeText(page.path)}"${enabled ? "" : ` disabled title="${safeText(reason)}"`}>${safeText(page.actionLabel)}</button></div></form>
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
    estimated_xu: "Ước tính", pricing_rule: "Quy tắc giá", choices: "Các gói canonical",
    label: "Tên gói", cost_xu: "Giá", note: "Ghi chú", source: "Nguồn canonical"
  });

  function resultLabel(key) {
    return RESULT_LABELS[key] || String(key || "Dữ liệu").replace(/_/g, " ");
  }

  function renderCanonicalValue(value, depth) {
    const level = Number(depth || 0);
    if (value === null || value === undefined || value === "") return "<span class=\"portal-result-empty\">—</span>";
    if (typeof value === "boolean") return `<span>${value ? "Có" : "Không"}</span>`;
    if (typeof value === "number") return `<span>${safeText(String(value))}</span>`;
    if (typeof value === "string") return `<span>${safeText(value)}</span>`;
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

  function renderCanonicalFlow(flow) {
    const data = flow && flow.data && typeof flow.data === "object" ? flow.data : {};
    const payload = data.draft || data.estimate;
    if (!payload || typeof payload !== "object") return "";
    if (payload.available === false) {
      return `<div class="portal-notice"><span class="portal-notice-icon" aria-hidden="true">i</span><div><strong>Adapter chi tiết đang được bảo vệ</strong><p>${safeText(payload.reason || "Core Bridge đã nhận input nhưng chưa có helper canonical cho bước này.")}</p></div></div>`;
    }
    const content = payload.content || payload;
    const heading = data.draft ? "Bản nháp canonical" : "Ước tính canonical";
    return `<section class="portal-canonical-result"><div class="portal-card-header"><div><h3 class="portal-card-title">${heading}</h3><p class="portal-card-subtitle">Nguồn: ${safeText(payload.source || "canonical_bot")} · Chưa gọi provider · Chưa trừ Xu.</p></div>${badge(flow.status || "draft")}</div>${renderCanonicalValue(content, 0)}</section>`;
  }

  function renderWorkspace(page, context) {
    const route = page.routePath || page.path;
    const flow = context.featureFlows && context.featureFlows[route];
    const flowOutput = flow
      ? `<div class="portal-state" data-state="${safeText(flow.status || "guarded")}"><span class="portal-state-icon" aria-hidden="true">○</span><div><h3>${safeText(flow.message || "Core Bridge đã cập nhật trạng thái.")}</h3><p>Trạng thái canonical: ${safeText(STATE_LABELS[flow.status] || flow.status || "guarded")}. ${flow.status === "completed" ? "Output chỉ được cấp qua asset đã xác minh." : "Bản nháp planning có thể hiển thị; output engine vẫn phải qua job và asset hợp lệ."}</p></div></div>${renderCanonicalFlow(flow)}`
      : renderEmpty("Chờ phản hồi Core Bridge", "Khi flow hoàn tất, bridge cung cấp trạng thái canonical và asset được xác minh.", "○");
    const voiceVault = page.path.startsWith("/voice") ? renderVoiceVault(context) : "";
    return `<article class="portal-page">${renderHero(page, context)}<div class="portal-status-grid">${renderStatusCard(page, context)}${renderSummary(page, context)}</div>
      <div class="portal-work-grid"><div>${renderFormCard(page, context)}</div><aside class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Tích hợp an toàn</h2><p class="portal-card-subtitle">UI chỉ phát sự kiện có cấu trúc cho lớp FastAPI.</p></div></div>${renderNotes(page)}</aside></div>
      ${voiceVault}<section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Output & trạng thái</h2><p class="portal-card-subtitle">Không tạo text, media, transcript hoặc file giả để thay thế engine thật.</p></div>${badge((flow && flow.status) || stateFor(page, context))}</div>${flowOutput}</section></article>`;
  }

  function renderVoiceVault(context) {
    const profiles = Array.isArray(context.voiceProfiles) ? context.voiceProfiles : [];
    return `<section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Voice Vault canonical</h2><p class="portal-card-subtitle">Tên, trạng thái và khả năng dùng giọng được bot kiểm tra; không hiển thị provider voice ID, file ID hay preview reference.</p></div></div>${renderRowsTable(["Giọng", "Trạng thái", "TTS", "Preview"], profiles, (profile) => `<td>${safeText(profile.display_name || "Giọng chưa đặt tên")}${profile.is_default ? " · Mặc định" : ""}</td><td>${badge(profile.status || "guarded")}</td><td>${profile.tts_ready ? "Sẵn sàng" : "Chưa sẵn sàng"}</td><td>${profile.preview_ready ? "Sẵn sàng" : "Chưa sẵn sàng"}</td>`, "Chưa có giọng đã được bot cấp", "Voice Vault sẽ chỉ hiển thị metadata thuộc signed session hiện tại.")}</section>`;
  }

  function renderReadOnly(page, context) {
    const assets = Array.isArray(context.assets) ? context.assets : [];
    const jobs = Array.isArray(context.jobs) ? context.jobs : [];
    const scope = page.path.startsWith("/image") ? "image" : page.path.startsWith("/video") ? "video" : page.path.startsWith("/voice") ? "voice" : page.path.startsWith("/music") ? "music" : page.path.startsWith("/subtitle") ? "subtitle" : "";
    const scopedAssets = scope ? assets.filter((item) => String(item.feature || item.job_type || "").toLowerCase().includes(scope)) : assets;
    let content;
    if (page.view === "voices") {
      content = renderVoiceVault(context);
    } else if (page.view === "jobs") {
      content = `<section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Job thuộc phiên</h2><p class="portal-card-subtitle">Không có polling provider trực tiếp từ browser.</p></div></div>${renderRowsTable(["Job", "Tính năng", "Trạng thái", "Cập nhật"], jobs, (item) => `<td><a href="/jobs/${encodeURIComponent(item.id || "")}">${safeText(item.id || "—")}</a></td><td>${safeText(item.feature || "—")}</td><td>${badge(item.status || "guarded")}</td><td>${safeText(item.updated_at || item.created_at || "—")}</td>`, "Chưa có job được xác minh", "Core Bridge sẽ chỉ trả job thuộc signed session hiện tại.")}</section>`;
    } else {
      content = `<section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Tài sản thuộc phiên</h2><p class="portal-card-subtitle">Không hiển thị URL provider, file path hoặc preview không được ký.</p></div></div>${renderRowsTable(["Tài sản", "Tính năng", "Trạng thái", "Delivery"], scopedAssets, (item) => `<td>${safeText(item.id || "—")}</td><td>${safeText(item.feature || "—")}</td><td>${badge(item.status || "guarded")}</td><td>${deliveryPending()}</td>`, "Chưa có tài sản được xác minh", "Khi output hợp lệ, Core Bridge mới trả metadata và signed delivery theo ownership.")}</section>`;
    }
    return `<article class="portal-page">${renderHero(page, context)}<div class="portal-status-grid">${renderStatusCard(page, context)}${renderSummary(page, context)}</div>${content}<section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Quy tắc dữ liệu</h2><p class="portal-card-subtitle">Trang chỉ đọc không tạo request engine rỗng.</p></div></div>${renderNotes(page)}</section></article>`;
  }

  function renderAdminOverview(page, context) {
    const data = context.adminData && typeof context.adminData === "object" ? context.adminData : {};
    const counts = data.counts || {};
    const readiness = data.readiness && typeof data.readiness === "object" ? Object.entries(data.readiness) : [];
    const readyCount = readiness.filter(([, item]) => item && item.public_ready).length;
    const metrics = [["Users", String(counts.users || "—"), "Dữ liệu cần role check"], ["Engine jobs", String(counts.engine_jobs || "—"), "Đọc từ queue canonical"], ["Payment", String(counts.payments || "—"), "Không có ledger client"], ["Readiness", readiness.length ? `${readyCount}/${readiness.length}` : "—", "Feature public-ready"]];
    const refreshEnabled = context.capabilities && context.capabilities["refresh-admin"] === true;
    const readinessRows = readiness.slice(0, 8);
    return `<article class="portal-page">${renderHero(page, context)}<section class="portal-card portal-card-pad portal-admin-guard"><div class="portal-state" data-state="guarded"><span class="portal-state-icon" aria-hidden="true">⌘</span><div><h2>${context.isAdmin ? "Admin session đã được server xác nhận" : "Admin ERP đang chờ signed session"}</h2><p>${context.isAdmin ? "Tất cả read/write vẫn cần capability và Core Bridge; shell không tự thực hiện tác vụ quản trị." : "Client route không đủ để cấp quyền. FastAPI cần kiểm tra signed session trước khi render dữ liệu."}</p></div></div></section>
      <section class="portal-admin-grid">${metrics.map(([label, value, note]) => `<div class="portal-metric"><span>${label}</span><strong>${value}</strong><em>${note}</em></div>`).join("")}</section>
      <div class="portal-work-grid"><section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Readiness canonical</h2><p class="portal-card-subtitle">Chỉ xem trạng thái bot đã redaction; không bật/tắt provider từ trình duyệt.</p></div><button class="portal-button portal-button--quiet" type="button" data-portal-action="refresh-admin" data-portal-route="/admin"${refreshEnabled ? "" : " disabled"}>Làm mới</button></div>${renderRowsTable(["Tính năng", "Trạng thái", "Adapter"], readinessRows, ([key, item]) => `<td>${safeText(key)}</td><td>${badge(item && item.public_ready ? "ready" : "guarded")}</td><td>${safeText(item && item.adapter || "—")}</td>`, "Chưa có readiness được cấp", "Core Bridge sẽ chỉ trả trạng thái khi signed admin session còn hiệu lực.")}</section>${renderSummary(page, context)}</div></article>`;
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

  function renderAdminDataTable(page, context) {
    const data = context.adminData && typeof context.adminData === "object" ? context.adminData : {};
    const rows = Array.isArray(data.items) ? data.items : [];
    const module = adminModuleKey(page, context);
    if (["users", "user", "wallet"].includes(module)) {
      return renderRowsTable(["Người dùng", "Tên hiển thị", "Số dư", "Đã dùng", "Gói", "Tạo lúc"], rows, (item) => `<td>${safeText(item.user_id || "—")}</td><td>${safeText(item.username || "—")}</td><td>${safeText(adminNumber(item.balance_xu, " Xu"))}</td><td>${safeText(adminNumber(item.total_spent_xu, " Xu"))}</td><td>${item.is_vip ? "VIP" : "Chuẩn"}</td><td>${safeText(item.created_at || "—")}</td>`, "Chưa có người dùng được cấp", "Core Bridge chỉ trả các trường phù hợp với role quản trị hiện tại.");
    }
    if (["payments", "topups", "revenue", "refunds"].includes(module)) {
      return renderRowsTable(["Mã giao dịch", "Người dùng", "Giá trị", "Xu", "Loại", "Trạng thái", "Cập nhật"], rows, (item) => `<td>${safeText(item.order_code || item.id || "—")}</td><td>${safeText(item.user_id || "—")}</td><td>${safeText(adminNumber(item.amount_vnd, " đ"))}</td><td>${safeText(adminNumber(item.xu, " Xu"))}</td><td>${safeText(item.type || "—")}</td><td>${badge(jobStatus(item))}</td><td>${safeText(item.paid_at || item.created_at || "—")}</td>`, "Chưa có giao dịch được cấp", "Web App không tính lại số tiền, Xu, refund hoặc trạng thái PayOS.");
    }
    if (["jobs", "failed-jobs", "workers", "runtime"].includes(module)) {
      return renderRowsTable(["Job", "Tính năng", "Trạng thái", "Cập nhật", "Output engine", "Delivery"], rows, (item) => `<td>${safeText(item.id || "—")}</td><td>${safeText(item.feature || item.job_type || "—")}</td><td>${badge(jobStatus(item))}</td><td>${safeText(item.updated_at || item.created_at || "—")}</td><td>${reportedOutput(item)}</td><td>${deliveryPending()}</td>`, "Chưa có job vận hành được cấp", "Admin view vẫn không hiển thị URL provider, local path hay download không ký.");
    }
    if (["providers", "provider-cost", "features", "freezes", "pricing", "promos"].includes(module)) {
      return renderRowsTable(["Tính năng", "Trạng thái", "Lý do đã rút gọn", "Cập nhật"], rows, (item) => `<td>${safeText(item.feature || item.id || "—")}</td><td>${badge(jobStatus(item))}</td><td>${safeText(item.reason || "—")}</td><td>${safeText(item.updated_at || "—")}</td>`, "Chờ trạng thái canonical", "Feature/provider readiness chỉ đọc. Freeze, giá và provider operation không được thực hiện từ UI.");
    }
    if (["tickets", "support"].includes(module)) {
      return renderRowsTable(["Ticket", "Loại", "Ưu tiên", "Trạng thái", "Đính kèm", "Cập nhật"], rows, (item) => `<td>${safeText(item.id || item.code || "—")}</td><td>${safeText(item.category || item.related_tool || "—")}</td><td>${safeText(item.priority || "—")}</td><td>${badge(jobStatus(item))}</td><td>${item.has_attachment ? "Có" : "Không"}</td><td>${safeText(item.updated_at || item.created_at || "—")}</td>`, "Chưa có metadata ticket được cấp", "Nội dung, username, Telegram attachment ID và thread ticket không được render trong bảng ERP này.");
    }
    if (["audit", "security"].includes(module)) {
      return renderRowsTable(["Sự kiện", "Hành động", "Kết quả", "Thời điểm"], rows, (item) => `<td>${safeText(item.id || "—")}</td><td>${safeText(item.action || "—")}</td><td>${badge(jobStatus(item))}</td><td>${safeText(item.created_at || "—")}</td>`, "Chưa có audit event được cấp", "Không render raw audit payload, detail, token, file ID hoặc danh tính người dùng.");
    }
    return renderRowsTable(["Đối tượng", "Trạng thái", "Cập nhật"], rows, (item) => `<td>${safeText(item.id || item.feature || item.user_id || "—")}</td><td>${badge(jobStatus(item))}</td><td>${safeText(item.updated_at || item.created_at || "—")}</td>`, "Module đang chờ adapter canonical", "Không tạo record, số liệu hoặc action thay thế khi bot chưa có read-only adapter phù hợp.");
  }

  function renderAdmin(page, context) {
    const data = context.adminData && typeof context.adminData === "object" ? context.adminData : {};
    const refreshEnabled = context.capabilities && context.capabilities["refresh-admin"] === true;
    const module = adminModuleKey(page, context);
    const recordText = page.recordId ? `<div class="portal-notice portal-notice--info"><span class="portal-notice-icon">i</span><div><strong>Record được yêu cầu</strong><p>ID ${safeText(page.recordId)} không cấp quyền hay dữ liệu cho browser. Core Bridge phải kiểm tra permission trước khi trả chi tiết.</p></div></div>` : "";
    const adapterMessage = data.message ? `<div class="portal-notice portal-notice--info"><span class="portal-notice-icon">i</span><div><strong>Trạng thái adapter</strong><p>${safeText(data.message)}</p></div></div>` : "";
    return `<article class="portal-page">${renderHero(page, context)}<section class="portal-card portal-card-pad portal-admin-guard"><div class="portal-state" data-state="guarded"><span class="portal-state-icon" aria-hidden="true">⌘</span><div><h2>${context.isAdmin ? "Lớp quản trị có kiểm soát" : "Cần quyền quản trị được server xác minh"}</h2><p>${context.isAdmin ? "Dữ liệu hiển thị, write permission, CSRF, confirmation và audit vẫn do Core Bridge quyết định." : "Không có dữ liệu PII, wallet hoặc payment được render cho client không có signed admin session."}</p></div></div></section>
      <div class="portal-work-grid"><section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">${safeText(module)} · dữ liệu vận hành</h2><p class="portal-card-subtitle">Hiển thị sau permission, redaction và ownership checks. Bộ lọc/write sẽ chỉ xuất hiện khi có adapter canonical riêng.</p></div><button class="portal-button portal-button--quiet" type="button" data-portal-action="refresh-admin" data-portal-route="${safeText(page.routePath || page.path)}"${refreshEnabled ? "" : " disabled"}>Làm mới</button></div>${adapterMessage}${renderAdminDataTable(page, context)}</section>
        <aside class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Chế độ chỉ đọc</h2><p class="portal-card-subtitle">Không bypass canonical business rules.</p></div>${badge("read_only")}</div>${renderNotes(page)}</aside></div>${recordText}</article>`;
  }

  function renderNotFound(page, context) {
    return `<article class="portal-page">${renderHero(page, context)}<section class="portal-card portal-card-pad">${renderEmpty("Route chưa có trong portal", "Không có action fallback. Quay lại Dashboard hoặc chọn module được khai báo.", "·")}<div class="portal-form-footer" style="justify-content:center;margin-top:14px"><a class="portal-button portal-button--primary" href="/dashboard">Về Dashboard</a></div></section></article>`;
  }

  function renderPage(page, context) {
    switch (page.layout) {
      case "auth": return renderAuth(page, context);
      case "dashboard": return renderDashboard(page, context);
      case "wallet": return renderWallet(page, context);
      case "catalog": return renderCatalog(page, context);
      case "jobs": return renderJobs(page, context);
      case "job-detail": return renderJobDetail(page, context);
      case "assets": return renderAssets(page, context);
      case "tickets": return renderTickets(page, context);
      case "read-only": return renderReadOnly(page, context);
      case "onboarding": return renderOnboarding(page, context);
      case "legal": return renderLegal(page, context);
      case "admin-overview": return renderAdminOverview(page, context);
      case "admin": return renderAdmin(page, context);
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

  function dispatchAction(button, context) {
    const action = button.getAttribute("data-portal-action") || "";
    const confirmation = button.getAttribute("data-portal-confirm") || "";
    if (confirmation && !window.confirm(confirmation)) return;
    const route = button.getAttribute("data-portal-route") || context.path;
    const formId = button.getAttribute("data-portal-form-id") || "";
    const form = button.closest("form") || (formId ? document.getElementById(formId) : null);
    const fields = {};
    if (form) {
      form.querySelectorAll("input, textarea, select").forEach((input) => {
        if (input.type === "file") {
          const selected = input.files ? Array.from(input.files) : [];
          if (selected.length) fields[input.name] = input.multiple ? selected : selected[0];
          return;
        }
        fields[input.name] = input.type === "checkbox" ? input.checked : input.value;
      });
    }
    const event = new CustomEvent(ACTION_EVENT, {
      detail: Object.freeze({ action, route, fields, jobFilter: button.getAttribute("data-job-filter") || "", apiBase: context.apiBase || null }),
      bubbles: false,
      cancelable: true
    });
    window.dispatchEvent(event);
  }

  function closeSidebar() {
    const sidebar = document.querySelector("[data-portal-sidebar]");
    const backdrop = document.querySelector("[data-portal-backdrop]");
    const button = document.querySelector("[data-portal-menu]");
    if (sidebar) sidebar.classList.remove("is-open");
    if (backdrop) backdrop.hidden = true;
    if (button) button.setAttribute("aria-expanded", "false");
  }

  function toggleSidebar() {
    const sidebar = document.querySelector("[data-portal-sidebar]");
    const backdrop = document.querySelector("[data-portal-backdrop]");
    const button = document.querySelector("[data-portal-menu]");
    if (!sidebar || !backdrop || !button) return;
    const opened = sidebar.classList.toggle("is-open");
    backdrop.hidden = !opened;
    button.setAttribute("aria-expanded", String(opened));
  }

  function bindInteractions() {
    // The shell re-renders after every authenticated hydration. Delegated
    // listeners therefore belong to the document once, while each action
    // resolves the *current* signed-session bootstrap at click time. This
    // prevents duplicate register/payment/feature events after re-mounting.
    if (interactionsBound) return;
    interactionsBound = true;
    document.addEventListener("click", (event) => {
      const menu = event.target.closest("[data-portal-menu]");
      if (menu) { toggleSidebar(); return; }
      if (event.target.closest("[data-portal-backdrop]")) { closeSidebar(); return; }
      const action = event.target.closest("[data-portal-action]");
      if (action && !action.disabled) { dispatchAction(action, getBootstrap()); return; }
      const link = event.target.closest(".portal-nav-link");
      if (link) closeSidebar();
    });
    document.addEventListener("submit", (event) => {
      if (event.target.matches("[data-portal-form]")) {
        event.preventDefault();
        showToast("Form shell không tự gửi dữ liệu. Hãy chờ adapter FastAPI đã ký phiên.", "warning");
      }
    });
    window.addEventListener("keydown", (event) => { if (event.key === "Escape") closeSidebar(); });
  }

  function mountPortal(override) {
    if (override && typeof override === "object") window.__TOAN_AAS_PORTAL__ = override;
    const context = getBootstrap();
    const page = resolvePage(context.path);
    const sidebar = document.querySelector("[data-portal-sidebar]");
    const header = document.querySelector("[data-portal-header]");
    const main = document.querySelector("[data-portal-main]");
    if (!sidebar || !header || !main) return;
    document.title = `${context.title || page.title} · TOAN AAS`;
    sidebar.innerHTML = renderSidebar(page, context);
    header.innerHTML = renderHeader(page, context);
    main.innerHTML = renderPage(page, context);
    bindInteractions();
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
