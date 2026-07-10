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
  try {
    const bootstrap = document.getElementById("portal-bootstrap");
    const parsed = bootstrap && JSON.parse(bootstrap.textContent || "{}");
    if (parsed && typeof parsed === "object") window.__TOAN_AAS_PORTAL__ = parsed;
  } catch (_) {
    window.__TOAN_AAS_PORTAL__ = window.__TOAN_AAS_PORTAL__ || {};
  }
  const ALLOWED_STATES = new Set([
    "ready", "draft", "awaiting_confirm", "queued", "processing",
    "completed", "failed", "guarded", "disabled", "error", "empty"
  ]);

  const STATE_LABELS = Object.freeze({
    ready: "Sẵn sàng",
    draft: "Bản nháp",
    awaiting_confirm: "Chờ xác nhận",
    queued: "Đã xếp hàng",
    processing: "Đang xử lý",
    completed: "Hoàn tất",
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
      { name: "format", label: "Tỷ lệ khung hình", control: "select", options: ["1:1", "4:5", "16:9", "9:16"] },
      { name: "reference", label: "Tệp tham chiếu", type: "file", help: "Chỉ hiển thị khi upload an toàn và kiểm tra MIME đã được Core Bridge bật." }
    ],
    video: [
      { name: "brief", label: "Brief video", control: "textarea", placeholder: "Mục tiêu, cảnh, chuyển động, giọng đọc…" },
      { name: "duration", label: "Thời lượng mục tiêu", control: "select", options: ["Theo gói hiện có", "Ngắn", "Tiêu chuẩn", "Nhiều cảnh"] },
      { name: "source", label: "Tệp / hình nguồn", type: "file", help: "Không tải lên hay gọi provider từ shell này." }
    ],
    voice: [
      { name: "script", label: "Nội dung lời thoại", control: "textarea", placeholder: "Nhập văn bản để chuẩn bị giọng nói…" },
      { name: "voice", label: "Giọng đã lưu", control: "select", options: ["Chờ Voice Vault", "Giọng mặc định theo server"] }
    ],
    music: [
      { name: "brief", label: "Mô tả âm thanh", control: "textarea", placeholder: "Thể loại, nhịp độ, cảm xúc, thời lượng…" },
      { name: "usage", label: "Mục đích sử dụng", control: "select", options: ["Nội dung ngắn", "Video sản phẩm", "SFX", "Nhạc nền"] }
    ],
    subtitle: [
      { name: "source", label: "Tệp media nguồn", type: "file", help: "Core Bridge phải kiểm tra ownership, định dạng và kích thước trước khi nhận tệp." },
      { name: "target_language", label: "Ngôn ngữ đích", control: "select", options: ["Giữ nguyên", "Tiếng Việt", "English", "Theo yêu cầu"] },
      { name: "instructions", label: "Hướng dẫn bổ sung", control: "textarea", placeholder: "Ví dụ: giữ tên thương hiệu, xuất SRT/VTT…" }
    ],
    document: [
      { name: "document", label: "Tài liệu nguồn", type: "file", help: "Tệp không được truyền từ browser cho tới khi có URL upload ký tạm thời." },
      { name: "operation", label: "Thao tác", control: "select", options: ["Theo tính năng hiện tại", "OCR", "Dịch", "Gộp", "Tách", "Nén"] },
      { name: "notes", label: "Ghi chú", control: "textarea", placeholder: "Phạm vi trang, ngôn ngữ, định dạng đầu ra…" }
    ],
    support: [
      { name: "subject", label: "Chủ đề", placeholder: "Tóm tắt vấn đề" },
      { name: "detail", label: "Nội dung", control: "textarea", placeholder: "Không nhập khoá API, token hoặc dữ liệu thanh toán nhạy cảm." },
      { name: "attachment", label: "Tệp đính kèm", type: "file", help: "Chỉ bật sau khi Core Bridge cấp upload ký tạm thời." }
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
      status: "guarded",
      action: "admin-review",
      actionLabel: "Gửi yêu cầu review",
      fields: copyFields(FIELD_SETS.adminFilter),
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
    fields: copyFields(FIELD_SETS.telegramLink), action: "complete-onboarding", actionLabel: "Xác minh liên kết", status: "guarded",
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
      { name: "package", label: "Gói nạp", control: "select", options: ["Chờ catalog từ server"] },
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
  customerPage("/support", "Hỗ trợ", "Tạo yêu cầu hỗ trợ không kèm secret; tệp chỉ được nhận qua upload ký tạm thời.", ICONS.support, {
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
  featurePage("/image/history", "Lịch sử ảnh", "Danh sách output ảnh thuộc phiên sẽ xuất hiện sau khi bridge xác thực.", ICONS.image, [], ["/image/assets"]);

  featurePage("/video/create", "Video nhanh", "Chuẩn bị brief video, sau đó ước tính và xác nhận với Core Bridge.", ICONS.video, FIELD_SETS.video, ["/video"]);
  featurePage("/video/long", "Video dài", "Chuẩn bị dự án video dài; tiến độ và output chỉ đến từ job canonical.", ICONS.video, FIELD_SETS.video);
  featurePage("/video/product", "Video sản phẩm", "Chuẩn bị brief video sản phẩm, cảnh và CTA theo flow draft → estimate → confirm.", ICONS.video, FIELD_SETS.video);
  featurePage("/video/text-to-video", "Text-to-Video", "Chuẩn bị yêu cầu text-to-video mà không gọi provider từ trình duyệt.", ICONS.video, FIELD_SETS.video);
  featurePage("/video/image-to-video", "Image-to-Video", "Chuẩn bị input hình nguồn; bridge kiểm tra quyền sở hữu và định dạng.", ICONS.video, FIELD_SETS.video);
  featurePage("/video/trend", "Video xu hướng", "Tạo brief video theo xu hướng và đợi engine có trạng thái sẵn sàng.", ICONS.video, FIELD_SETS.video);
  featurePage("/video/quick", "Quick Video", "Khởi tạo bản nháp video nhanh; không có kết quả giả lập trong UI.", ICONS.video, FIELD_SETS.video);
  featurePage("/video/multiscene", "Video nhiều cảnh", "Chuẩn bị nhiều cảnh và các thành phần media trước bước estimate.", ICONS.video, FIELD_SETS.video);
  featurePage("/video/progress", "Tiến độ video", "Theo dõi các job video được bridge trả về cho phiên sở hữu.", ICONS.video, []);
  featurePage("/video/preview", "Xem trước video", "Chỉ mở preview có URL ký tạm thời và output đã qua validation.", ICONS.video, []);
  featurePage("/video/export", "Xuất video", "Xuất file chỉ khi output hoàn tất, thuộc sở hữu người dùng và được ký tạm thời.", ICONS.video, []);
  featurePage("/video/add-ons", "Video add-ons", "Chuẩn bị voice, music, subtitle và các add-on trước khi bridge tạo job.", ICONS.video, FIELD_SETS.video);

  featurePage("/voice", "Voice Vault", "Danh mục giọng nói thuộc tài khoản, không hiển thị nếu bridge chưa xác minh phiên.", ICONS.voice, [], ["/voice-vault"]);
  featurePage("/voice/tts", "Text-to-Speech", "Chuẩn bị lời thoại và lựa chọn giọng trong flow có estimate rõ ràng.", ICONS.voice, FIELD_SETS.voice, ["/tts", "/voice/create"]);
  featurePage("/voice/saved", "Giọng đã lưu", "Chờ Voice Vault trả về danh sách giọng thuộc sở hữu bạn.", ICONS.voice, [], ["/voice/vault"]);
  featurePage("/voice/clone", "Voice Clone", "Tính năng clone chỉ khả dụng nếu engine và quyền sử dụng đã được bridge cho phép.", ICONS.voice, FIELD_SETS.voice);
  featurePage("/voice/preview", "Nghe thử giọng", "Preview là output riêng tư và phải dùng signed/temporary URL.", ICONS.voice, []);
  featurePage("/voice/outputs", "Voice outputs", "Tài sản audio đã tạo sẽ xuất hiện tại đây sau delivery hợp lệ.", ICONS.voice, []);

  featurePage("/music", "Music Studio", "Không gian chuẩn bị nhạc AI/SFX với trạng thái provider do bridge cung cấp.", ICONS.music, FIELD_SETS.music);
  featurePage("/music/library", "Thư viện nhạc", "Danh sách nhạc thuộc phiên chỉ được bridge cung cấp sau kiểm tra ownership.", ICONS.music, [], ["/music-library"]);
  featurePage("/music/sfx", "Hiệu ứng âm thanh", "Chuẩn bị brief SFX; không tạo âm thanh hay charge Xu ở browser.", ICONS.music, FIELD_SETS.music);
  featurePage("/music/create", "Tạo nhạc AI", "Tạo bản nháp nhạc AI và đợi engine/ước tính từ Core Bridge.", ICONS.music, FIELD_SETS.music, ["/music/ai"]);
  featurePage("/music/song", "AI Song", "Chuẩn bị yêu cầu bài hát, cấu trúc và mood; job chỉ được tạo sau confirm.", ICONS.music, FIELD_SETS.music);
  featurePage("/music/upload", "Nhạc của tôi", "Upload nhạc chỉ được bật qua URL ký tạm thời và kiểm tra MIME server-side.", ICONS.music, FIELD_SETS.music);

  featurePage("/subtitle", "Phụ đề", "Chuẩn bị phụ đề từ media nguồn với export SRT/VTT do job engine trả về.", ICONS.subtitle, FIELD_SETS.subtitle);
  featurePage("/subtitle/create", "Tạo phụ đề", "Tạo bản nháp phụ đề, không giả lập transcript hay file SRT/VTT.", ICONS.subtitle, FIELD_SETS.subtitle);
  featurePage("/translate", "Dịch nội dung", "Chuẩn bị yêu cầu dịch, giữ nguyên tên thương hiệu và ngôn ngữ mục tiêu.", ICONS.subtitle, FIELD_SETS.subtitle);
  featurePage("/dubbing", "Lồng tiếng", "Chuẩn bị dubbing với giọng/đích ngôn ngữ do Core Bridge xác minh.", ICONS.subtitle, FIELD_SETS.subtitle);
  featurePage("/asr", "Nhận dạng giọng nói", "Bản nháp ASR chờ output hợp lệ; không tự sinh transcript trong UI.", ICONS.subtitle, FIELD_SETS.subtitle);
  featurePage("/subtitle/formats", "SRT / VTT", "Quản lý định dạng phụ đề chỉ sau khi file output hợp lệ được bridge trả về.", ICONS.subtitle, []);
  featurePage("/video/mux", "Mux audio & video", "Chuẩn bị mux và fallback; Core Bridge chịu trách nhiệm FFmpeg/output validation.", ICONS.video, FIELD_SETS.video, ["/mux"]);

  featurePage("/documents", "Document Studio", "Tập hợp workflow PDF, OCR, gộp/tách/nén và dịch tài liệu.", ICONS.document, FIELD_SETS.document);
  featurePage("/documents/pdf", "PDF tools", "Chuẩn bị thao tác PDF; Core Bridge kiểm tra file, path và ownership.", ICONS.document, FIELD_SETS.document, ["/pdf"]);
  featurePage("/documents/ocr", "OCR", "Chuẩn bị OCR, đợi engine trả về kết quả được kiểm tra thay vì text giả.", ICONS.document, FIELD_SETS.document);
  featurePage("/documents/merge", "Gộp tài liệu", "Gộp tài liệu qua job có kiểm tra file server-side.", ICONS.document, FIELD_SETS.document);
  featurePage("/documents/split", "Tách tài liệu", "Tách tài liệu theo phạm vi trang sau khi bridge xác thực input.", ICONS.document, FIELD_SETS.document);
  featurePage("/documents/compress", "Nén tài liệu", "Nén file theo job riêng; download chỉ xuất hiện khi output hợp lệ.", ICONS.document, FIELD_SETS.document);
  featurePage("/documents/translate", "Dịch tài liệu", "Dịch tài liệu bằng workflow server-side và output riêng tư đã xác minh.", ICONS.document, FIELD_SETS.document);

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
      assets: Array.isArray(source.assets) ? source.assets : [],
      tickets: Array.isArray(source.tickets) ? source.tickets : [],
      adminData: source.adminData && typeof source.adminData === "object" ? source.adminData : {},
      readiness: source.readiness && typeof source.readiness === "object" ? source.readiness : {},
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
        status: "guarded", access: "admin", layout: "admin", type: "admin", action: "admin-review", actionLabel: "Gửi yêu cầu review",
        fields: copyFields(FIELD_SETS.adminFilter), recordId: userId,
        notes: ["Không sử dụng admin_id do browser gửi.", "Wallet adjustment/refund cần Core Bridge, CSRF, idempotency và audit."]
      });
    }
    if (normalized === "/admin" || normalized.startsWith("/admin/")) {
      const label = normalized.split("/").filter(Boolean).slice(1).join(" · ").replace(/[-_]/g, " ") || "Tổng quan";
      return Object.freeze({
        path: "/admin/:module", routePath: normalized, title: `Admin · ${label}`, icon: ICONS.admin, section: "Admin ERP",
        description: "Compatibility surface cho command quản trị của bot. Core Bridge phải xác minh quyền, confirmation, CSRF và audit trước mọi thay đổi.",
        status: "guarded", access: "admin", layout: "admin", type: "admin", action: "admin-review", actionLabel: "Yêu cầu kiểm tra", fields: copyFields(FIELD_SETS.adminFilter),
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
    if (page.action === "complete-onboarding") return context.session.authenticated === true && csrfReady && capability;
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

  function renderFields(fields, enabled) {
    if (!fields || !fields.length) return "";
    return `<div class="portal-fields">${fields.map((field) => {
      const wide = field.control === "textarea" || field.type === "file" || field.wide;
      const id = `portal-field-${safeText(field.name || "input").replace(/[^a-zA-Z0-9_-]/g, "-")}`;
      const disabled = enabled ? "" : " disabled";
      const help = field.help ? `<span class="portal-field-help">${safeText(field.help)}</span>` : "";
      let control;
      if (field.control === "textarea") {
        control = `<textarea class="portal-textarea" id="${id}" name="${safeText(field.name)}" placeholder="${safeText(field.placeholder)}"${disabled}></textarea>`;
      } else if (field.control === "select") {
        const options = (field.options || []).map((option) => `<option>${safeText(option)}</option>`).join("");
        control = `<select class="portal-select" id="${id}" name="${safeText(field.name)}"${disabled}>${options}</select>`;
      } else {
        const type = ["email", "password", "file", "text"].includes(field.type) ? field.type : "text";
        const autocomplete = field.autocomplete ? ` autocomplete="${safeText(field.autocomplete)}"` : "";
        control = `<input class="portal-input" id="${id}" name="${safeText(field.name)}" type="${type}" placeholder="${safeText(field.placeholder)}"${autocomplete}${disabled}>`;
      }
      return `<div class="portal-field${wide ? " portal-field--wide" : ""}"><label for="${id}">${safeText(field.label)}</label>${control}${help}</div>`;
    }).join("")}</div>`;
  }

  function statusMessage(page, status, context) {
    if (status === "ready") return { icon: "✓", title: "Giao diện đã sẵn sàng", text: "Chỉ các khả năng đã được máy chủ ký và cấp cho phiên mới được bật." };
    if (status === "empty") return { icon: "○", title: "Chưa có dữ liệu để hiển thị", text: "Portal không tự tạo job, số dư, file hay output. Dữ liệu sẽ xuất hiện sau phản hồi Core Bridge hợp lệ." };
    if (status === "error" || status === "failed") return { icon: "!", title: "Chưa thể xác thực trạng thái", text: "Không có thao tác fallback hay giả lập. Hãy đợi Core Bridge trả trạng thái an toàn." };
    if (status === "queued" || status === "processing") return { icon: "◌", title: "Job đang do Core Bridge điều phối", text: "Chỉ trạng thái engine canonical mới có thể chuyển job sang completed." };
    if (status === "draft" || status === "awaiting_confirm") return { icon: "◇", title: "Bản nháp chờ luồng xác nhận", text: "Core Bridge phải estimate trước, sau đó người dùng xác nhận để tạo job." };
    if (status === "completed") return { icon: "✓", title: "Output đã hoàn tất", text: "Output cần được bridge xác thực file, ownership và URL ký tạm thời trước khi mở tải xuống." };
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
    const flowControls = canAdvance
      ? `<div class="portal-flow-actions"><button class="portal-button portal-button--quiet" type="button" data-portal-action="feature-estimate" data-portal-route="${safeText(route)}">Ước tính Xu</button>${flowStatus === "awaiting_confirm" ? `<button class="portal-button portal-button--primary" type="button" data-portal-action="feature-confirm" data-portal-route="${safeText(route)}">Xác nhận chạy</button>` : ""}</div>`
      : "";
    return `<section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">${page.layout === "auth" ? "Thông tin xác thực" : "Chuẩn bị yêu cầu"}</h2><p class="portal-card-subtitle">${enabled ? "Yêu cầu sẽ được chuyển tới lớp tích hợp thông qua custom event, không gọi trực tiếp từ UI." : safeText(reason)}</p></div>${badge(flowStatus || stateFor(page, context))}</div>
      <form class="portal-form" data-portal-form novalidate>${renderFields(page.fields, enabled)}
        <div class="portal-form-footer"><span class="portal-form-note">${enabled ? "Máy chủ vẫn phải xác minh phiên, CSRF, schema, ownership và idempotency." : "Các trường bị khóa cho tới khi máy chủ cấp khả năng cần thiết."}</span>
          <button class="portal-button portal-button--primary" type="button" data-portal-action="${safeText(page.action)}" data-portal-route="${safeText(page.path)}"${enabled ? "" : ` disabled title="${safeText(reason)}"`}>${safeText(page.actionLabel || "Tiếp tục")}</button>
        </div>
      </form>${flowControls}</section>`;
  }

  function renderHero(page, context) {
    const state = stateFor(page, context);
    const route = page.routePath || page.path;
    const hasAction = page.action && page.action !== "none";
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
    return `<section><div class="portal-section-heading"><div><h2>Module theo feature parity</h2><p>Chỉ route và trạng thái được khai báo; không mô phỏng output.</p></div><a class="portal-button portal-button--quiet" href="/prompt-studio">Mở Studio →</a></div><div class="portal-module-grid">${cards}</div></section>`;
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
    return `<article class="portal-page">${renderHero(page, context)}<div class="portal-status-grid">${renderStatusCard(page, context)}${renderSummary(page, context)}</div>${renderModuleCards(context)}
      <section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Hoạt động gần đây</h2><p class="portal-card-subtitle">Job và asset thuộc phiên chỉ có mặt sau khi bridge kiểm tra ownership.</p></div><a class="portal-button portal-button--quiet" href="/jobs">Mở Job Center →</a></div>${renderEmpty("Chưa có hoạt động được xác minh", "Khi bạn có job hợp lệ, Core Bridge sẽ trả dữ liệu trạng thái tại đây.", "⌛")}</section></article>`;
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
    const catalog = context.catalog || [];
    const hasCatalog = catalog.length > 0;
    const cards = hasCatalog ? catalog.map((entry) => {
      const item = typeof entry === "string" ? { title: entry } : entry || {};
      return `<section class="portal-module-card"><div class="portal-module-card-top"><span class="portal-module-icon">◇</span>${badge(item.status && ALLOWED_STATES.has(item.status) ? item.status : "guarded")}</div><div><h3>${safeText(item.title || item.name || "Gói dịch vụ")}</h3><p>${safeText(item.description || "Thông tin quyền lợi do server phát hành.")}</p></div><span class="portal-module-card-footer"><span>${safeText(item.priceLabel || "Giá chờ Core Bridge")}</span><span class="portal-module-arrow">→</span></span></section>`;
    }).join("") : renderEmpty("Catalog chưa được cấp", "Giá, Xu và chính sách payment chỉ xuất hiện khi Core Bridge gửi catalog đã xác minh.", "◇");
    return `<article class="portal-page">${renderHero(page, context)}<div class="portal-status-grid">${renderStatusCard(page, context)}${renderSummary(page, context)}</div><section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">${page.path === "/pricing" ? "Giá theo catalog" : "Gói hiện có"}</h2><p class="portal-card-subtitle">Không tự suy đoán tỷ lệ Xu, giá hoặc khuyến mãi.</p></div>${badge(stateFor(page, context))}</div><div class="portal-module-grid">${cards}</div></section></article>`;
  }

  function renderJobs(page, context) {
    const jobs = Array.isArray(context.jobs) ? context.jobs : [];
    return `<article class="portal-page">${renderHero(page, context)}<div class="portal-status-grid">${renderStatusCard(page, context)}${renderSummary(page, context)}</div>
      <section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Danh sách job</h2><p class="portal-card-subtitle">Chỉ bao gồm job thuộc signed session hiện tại.</p></div><a class="portal-button portal-button--quiet" href="/assets">Mở tài sản →</a></div>${renderRowsTable(["Job", "Tính năng", "Trạng thái", "Cập nhật", "Output"], jobs, (item) => `<td><a href="/jobs/${encodeURIComponent(item.id || "")}">${safeText(item.id || "—")}</a></td><td>${safeText(item.feature || "—")}</td><td>${badge(item.status || "guarded")}</td><td>${safeText(item.updated_at || item.created_at || "—")}</td><td>${item.output_available ? "Có output" : "Chưa có"}</td>`, "Chưa có job được xác minh", "Core Bridge sẽ trả job sau khi tạo/confirm thành công.")}</section></article>`;
  }

  function renderJobDetail(page, context) {
    const record = safeText(page.recordId || "—");
    return `<article class="portal-page">${renderHero(page, context)}<div class="portal-status-grid">${renderStatusCard(page, context)}${renderSummary(page, context)}</div>
      <div class="portal-work-grid"><section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Job ${record}</h2><p class="portal-card-subtitle">ID hiển thị không xác thực dữ liệu hoặc quyền download.</p></div>${badge(stateFor(page, context))}</div>${renderEmpty("Chưa có job detail an toàn", "Bridge cần kiểm tra ownership trước khi trả request, timeline và output của job này.", "⌛")}</section>
      <aside class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Delivery protection</h2><p class="portal-card-subtitle">Không có download trực tiếp từ path đoán được.</p></div></div>${renderNotes(page)}</aside></div></article>`;
  }

  function renderAssets(page, context) {
    const assets = Array.isArray(context.assets) ? context.assets : [];
    const delivery = (item) => item.download_ready
      ? `<button class="portal-button portal-button--quiet" type="button" data-portal-action="asset-download" data-asset-id="${safeText(item.id || "")}">Yêu cầu URL ký</button>`
      : "Chưa sẵn sàng";
    return `<article class="portal-page">${renderHero(page, context)}<div class="portal-status-grid">${renderStatusCard(page, context)}${renderSummary(page, context)}</div>
      <section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Tài sản riêng tư</h2><p class="portal-card-subtitle">Preview và download cần output validation, ownership check và signed URL.</p></div></div>${renderRowsTable(["Tài sản", "Tính năng", "Trạng thái", "Tạo lúc", "Delivery"], assets, (item) => `<td>${safeText(item.id || "—")}</td><td>${safeText(item.feature || "—")}</td><td>${badge(item.status || "guarded")}</td><td>${safeText(item.created_at || "—")}</td><td>${delivery(item)}</td>`, "Chưa có tài sản có thể mở", "Shell không hiển thị placeholder là output thật. Tài sản hoàn tất sẽ đến từ Core Bridge.")}</section></article>`;
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

  function renderAuth(page, context) {
    const alternative = page.path === "/login" ? ["/register", "Tạo tài khoản"] : ["/login", "Đăng nhập"];
    const enabled = canAct(page, context);
    const reason = actionBlockReason(page, context);
    return `<article class="portal-auth-page"><section class="portal-auth-intro"><div class="portal-eyebrow">TOAN AAS · secure access</div><h1 class="portal-title">${safeText(context.title || page.title)}</h1><p class="portal-description">${safeText(page.description)}</p>
      <div class="portal-auth-facts"><div class="portal-auth-fact"><strong>Signed session</strong><span>Cookie/session do server quản lý, không dùng raw localStorage.</span></div><div class="portal-auth-fact"><strong>Telegram link</strong><span>Mã dùng một lần, hết hạn và chống replay.</span></div><div class="portal-auth-fact"><strong>CSRF</strong><span>Mọi thao tác ghi phải có CSRF hợp lệ.</span></div><div class="portal-auth-fact"><strong>Rate limit</strong><span>Giới hạn login/register do Core Bridge thực thi.</span></div></div>
    </section><section class="portal-card portal-card-pad portal-auth-card"><div class="portal-card-header"><div><h2 class="portal-card-title">${safeText(page.title)}</h2><p class="portal-card-subtitle">${enabled ? "Endpoint đã được server cấp khả năng." : safeText(reason)}</p></div>${badge(stateFor(page, context))}</div>
      <form class="portal-form" data-portal-form novalidate>${renderFields(page.fields, enabled)}<div class="portal-form-footer"><a class="portal-button portal-button--quiet" href="${alternative[0]}">${alternative[1]} →</a><button class="portal-button portal-button--primary" type="button" data-portal-action="${safeText(page.action)}" data-portal-route="${safeText(page.path)}"${enabled ? "" : ` disabled title="${safeText(reason)}"`}>${safeText(page.actionLabel)}</button></div></form>
      <div class="portal-notice" style="margin-top:16px"><span class="portal-notice-icon" aria-hidden="true">⌁</span><div><strong>Không có đăng nhập giả</strong><p>Giao diện không tạo session, không lưu mật khẩu và không tự đăng nhập người dùng.</p></div></div>
    </section></article>`;
  }

  function renderWorkspace(page, context) {
    const route = page.routePath || page.path;
    const flow = context.featureFlows && context.featureFlows[route];
    const flowOutput = flow
      ? `<div class="portal-state" data-state="${safeText(flow.status || "guarded")}"><span class="portal-state-icon" aria-hidden="true">○</span><div><h3>${safeText(flow.message || "Core Bridge đã cập nhật trạng thái.")}</h3><p>Trạng thái canonical: ${safeText(STATE_LABELS[flow.status] || flow.status || "guarded")}. ${flow.status === "completed" ? "Output chỉ được cấp qua asset đã xác minh." : "Không có output giả được hiển thị."}</p></div></div>`
      : renderEmpty("Chờ phản hồi Core Bridge", "Khi flow hoàn tất, bridge cung cấp trạng thái canonical và asset được xác minh.", "○");
    return `<article class="portal-page">${renderHero(page, context)}<div class="portal-status-grid">${renderStatusCard(page, context)}${renderSummary(page, context)}</div>
      <div class="portal-work-grid"><div>${renderFormCard(page, context)}</div><aside class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Tích hợp an toàn</h2><p class="portal-card-subtitle">UI chỉ phát sự kiện có cấu trúc cho lớp FastAPI.</p></div></div>${renderNotes(page)}</aside></div>
      <section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Output & trạng thái</h2><p class="portal-card-subtitle">Không tạo text, media, transcript hoặc file giả để thay thế engine thật.</p></div>${badge((flow && flow.status) || stateFor(page, context))}</div>${flowOutput}</section></article>`;
  }

  function renderAdminOverview(page, context) {
    const counts = context.adminData && context.adminData.counts ? context.adminData.counts : {};
    const metrics = [["Users", String(counts.users || "—"), "Dữ liệu cần role check"], ["Engine jobs", String(counts.engine_jobs || "—"), "Đọc từ queue canonical"], ["Payment", String(counts.payments || "—"), "Không có ledger client"], ["Worker jobs", String(counts.worker_jobs || "—"), "Trạng thái được redaction"]];
    return `<article class="portal-page">${renderHero(page, context)}<section class="portal-card portal-card-pad portal-admin-guard"><div class="portal-state" data-state="guarded"><span class="portal-state-icon" aria-hidden="true">⌘</span><div><h2>${context.isAdmin ? "Admin session đã được server xác nhận" : "Admin ERP đang chờ signed session"}</h2><p>${context.isAdmin ? "Tất cả read/write vẫn cần capability và Core Bridge; shell không tự thực hiện tác vụ quản trị." : "Client route không đủ để cấp quyền. FastAPI cần kiểm tra signed session trước khi render dữ liệu."}</p></div></div></section>
      <section class="portal-admin-grid">${metrics.map(([label, value, note]) => `<div class="portal-metric"><span>${label}</span><strong>${value}</strong><em>${note}</em></div>`).join("")}</section>
      <div class="portal-work-grid"><section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Công việc vận hành</h2><p class="portal-card-subtitle">Queue hành động cần confirmation, CSRF và audit event.</p></div></div>${renderEmpty("Chưa có sự kiện đã được cấp", "Không có admin data, retry, refund hay provider operation giả lập.", "⌘")}</section>${renderSummary(page, context)}</div></article>`;
  }

  function renderAdmin(page, context) {
    const enabled = canAct(page, context);
    const reason = actionBlockReason(page, context);
    const recordText = page.recordId ? `<div class="portal-notice portal-notice--info"><span class="portal-notice-icon">i</span><div><strong>Record được yêu cầu</strong><p>ID ${safeText(page.recordId)} không cấp quyền hay dữ liệu cho browser. Core Bridge phải kiểm tra permission trước khi trả chi tiết.</p></div></div>` : "";
    return `<article class="portal-page">${renderHero(page, context)}<section class="portal-card portal-card-pad portal-admin-guard"><div class="portal-state" data-state="guarded"><span class="portal-state-icon" aria-hidden="true">⌘</span><div><h2>${context.isAdmin ? "Lớp quản trị có kiểm soát" : "Cần quyền quản trị được server xác minh"}</h2><p>${context.isAdmin ? "Dữ liệu hiển thị, write permission, CSRF, confirmation và audit vẫn do Core Bridge quyết định." : "Không có dữ liệu PII, wallet hoặc payment được render cho client không có signed admin session."}</p></div></div></section>
      <div class="portal-work-grid"><section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Bộ lọc server-side</h2><p class="portal-card-subtitle">Các trường không thực hiện truy vấn trực tiếp từ shell.</p></div>${badge(stateFor(page, context))}</div><form class="portal-form" data-portal-form novalidate>${renderFields(page.fields, enabled)}<div class="portal-form-footer"><span class="portal-form-note">${enabled ? "Yêu cầu review sẽ được bridge xác nhận và ghi audit." : safeText(reason)}</span><button class="portal-button portal-button--primary" type="button" data-portal-action="${safeText(page.action)}" data-portal-route="${safeText(page.routePath || page.path)}"${enabled ? "" : ` disabled title="${safeText(reason)}"`}>${safeText(page.actionLabel)}</button></div></form></section>
        <aside class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Giao thức write</h2><p class="portal-card-subtitle">Không bypass canonical business rules.</p></div></div>${renderNotes(page)}</aside></div>${recordText}
      <section class="portal-card portal-card-pad"><div class="portal-card-header"><div><h2 class="portal-card-title">Dữ liệu vận hành</h2><p class="portal-card-subtitle">Hiển thị sau permission, redaction và ownership checks.</p></div></div>${renderRowsTable(["Đối tượng", "Trạng thái", "Cập nhật", "Hành động"], (context.adminData && context.adminData.items) || [], (item) => `<td>${safeText(item.user_id || item.id || item.order_code || "—")}</td><td>${safeText(item.status || item.feature || "—")}</td><td>${safeText(item.updated_at || item.created_at || item.paid_at || "—")}</td><td>Read-only</td>`, "Chưa có dữ liệu được ủy quyền", "Core Bridge chưa cung cấp bản ghi cho phiên này.")}</section></article>`;
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
    const route = button.getAttribute("data-portal-route") || context.path;
    const form = button.closest("form");
    const fields = {};
    if (form) {
      form.querySelectorAll("input, textarea, select").forEach((input) => {
        if (input.type === "file") return;
        fields[input.name] = input.value;
      });
    }
    const event = new CustomEvent(ACTION_EVENT, {
      detail: Object.freeze({ action, route, fields, assetId: button.getAttribute("data-asset-id") || "", apiBase: context.apiBase || null }),
      bubbles: false,
      cancelable: true
    });
    window.dispatchEvent(event);
    showToast("Giao diện đã phát yêu cầu cho lớp tích hợp an toàn. Không có provider, payment hay job nào được gọi trực tiếp.");
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

  function bindInteractions(context) {
    document.addEventListener("click", (event) => {
      const menu = event.target.closest("[data-portal-menu]");
      if (menu) { toggleSidebar(); return; }
      if (event.target.closest("[data-portal-backdrop]")) { closeSidebar(); return; }
      const action = event.target.closest("[data-portal-action]");
      if (action && !action.disabled) { dispatchAction(action, context); return; }
      const link = event.target.closest(".portal-nav-link");
      if (link) closeSidebar();
    }, { once: true });
    document.addEventListener("submit", (event) => {
      if (event.target.matches("[data-portal-form]")) {
        event.preventDefault();
        showToast("Form shell không tự gửi dữ liệu. Hãy chờ adapter FastAPI đã ký phiên.", "warning");
      }
    }, { once: true });
    window.addEventListener("keydown", (event) => { if (event.key === "Escape") closeSidebar(); }, { once: true });
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
    bindInteractions(context);
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
