(function exposeFeatureCatalogCopy(root) {
  "use strict";
  if (typeof document !== "undefined" && document.head && typeof document.createElement === "function") {
    const style = document.createElement("style");
    style.textContent = ".portal-module-card-signals, .portal-boundary-label { display: none !important; }";
    document.head.appendChild(style);
  }
  root.TOANAASFeatureCatalogCopy = Object.freeze({
  "vi": {
    "dashboard": {
      "title": "Tổng quan",
      "description": "Theo dõi công việc, dự án và các đầu việc ưu tiên ở một nơi rõ ràng."
    },
    "projects": {
      "title": "Dự án",
      "description": "Quản lý các dự án và tài liệu sáng tạo riêng tư trong tài khoản của bạn."
    },
    "project_packages": {
      "title": "Bản lưu dự án",
      "description": "Xem và tải các bản lưu dự án đã được kiểm tra; đây không phải gói dịch vụ."
    },
    "workspace_drafts": {
      "title": "Bản nháp của tôi",
      "description": "Lưu và viết tiếp các bản nháp yêu cầu riêng tư. Tệp, báo giá và tiến độ trên Telegram không được lưu tại đây."
    },
    "workspace_menu": {
      "title": "Không gian làm việc",
      "description": "Mở nhanh các không gian làm việc được sắp xếp theo mục tiêu công việc. Quyền truy cập áp dụng riêng cho từng trang."
    },
    "account": {
      "title": "Tài khoản",
      "description": "Quản lý thông tin hồ sơ, cài đặt bảo mật và các phương thức đăng nhập của bạn."
    },
    "interface_locale_navigator": {
      "title": "Ngôn ngữ giao diện",
      "description": "Chọn ngôn ngữ hiển thị cho giao diện ứng dụng. Thay đổi này không làm đổi ngôn ngữ nội dung của bạn."
    },
    "account_activity": {
      "title": "Hoạt động tài khoản",
      "description": "Xem lịch sử hoạt động được ghi nhận cho tài khoản hiện tại của bạn."
    },
    "account_security": {
      "title": "Bảo mật tài khoản",
      "description": "Quản lý các phiên đăng nhập, mật khẩu và phương thức đăng nhập của tài khoản."
    },
    "workspace_care": {
      "title": "Chăm sóc dữ liệu",
      "description": "Rà soát dữ liệu trong không gian làm việc và mở công cụ phù hợp."
    },
    "partner_readiness": {
      "title": "Hồ sơ hợp tác",
      "description": "Chuẩn bị hồ sơ hợp tác riêng tư để tự rà soát, lưu lịch sử phiên bản và ghi nhận quan tâm. Mục này không tạo mã giới thiệu, hoa hồng, kết nối đối tác hay danh sách công khai."
    },
    "notes": {
      "title": "Ghi chú & kế hoạch",
      "description": "Lưu ghi chú và kế hoạch riêng tư với nhãn, mức ưu tiên, tìm kiếm, lưu trữ và lịch sử phiên bản."
    },
    "reminders": {
      "title": "Nhắc việc",
      "description": "Tạo lời nhắc một lần hoặc lặp lại, đồng thời tạm dừng, tiếp tục, hoàn tất hoặc hủy khi cần."
    },
    "inbox": {
      "title": "Hộp thư công việc",
      "description": "Xem các thông báo công việc riêng tư được ghi nhận khi bạn vắng mặt. Hộp thư này không gửi thông báo ra bên ngoài."
    },
    "automation": {
      "title": "Trung tâm tự động hóa",
      "description": "Xem các quy tắc tự động hóa và thông tin xác nhận đã được ghi nhận."
    },
    "referrals": {
      "title": "Giới thiệu bạn bè",
      "description": "Xem liên kết giới thiệu và số liệu thống kê đã được xác nhận; quyền lợi chỉ áp dụng khi đủ điều kiện."
    },
    "rewards": {
      "title": "Ưu đãi & quà",
      "description": "Xem các ưu đãi, quà sinh nhật và điều kiện áp dụng hiện có. Trang này chỉ hiển thị thông tin, không tự động cấp quyền lợi."
    },
    "community": {
      "title": "Kênh chính thức",
      "description": "Xem và đối chiếu các kênh chính thức của TOAN AAS."
    },
    "guides": {
      "title": "Trung tâm hướng dẫn",
      "description": "Tìm các bước chuẩn bị và chọn không gian làm việc phù hợp trong danh mục hướng dẫn."
    },
    "wallet": {
      "title": "Ví Xu",
      "description": "Xem số dư Xu và lịch sử giao dịch Xu của tài khoản."
    },
    "wallet_topup": {
      "title": "Nạp Xu",
      "description": "Chọn phương thức nạp đang khả dụng; số dư Xu chỉ được cộng sau khi thanh toán được xác nhận."
    },
    "packages": {
      "title": "Gói dịch vụ",
      "description": "Xem thông tin các gói dịch vụ hiện có. Trang này chỉ để tham khảo, không thực hiện mua gói hay thay đổi số dư Xu."
    },
    "membership": {
      "title": "Gói thành viên",
      "description": "Xem quyền lợi và trạng thái gói thành viên hiện tại của bạn. Trang này không tự cấp hạng thành viên hay thay đổi số dư Xu."
    },
    "jobs": {
      "title": "Tác vụ của tôi",
      "description": "Theo dõi các tác vụ thuộc tài khoản của bạn; kết quả chỉ hiển thị sau khi việc bàn giao được xác nhận."
    },
    "assets": {
      "title": "Tệp đã bàn giao",
      "description": "Xem các tệp đã hoàn tất của bạn; tệp chỉ xuất hiện tại đây sau khi việc bàn giao được xác nhận."
    },
    "asset_vault": {
      "title": "Kho tệp cá nhân",
      "description": "Lưu trữ các tệp cá nhân của bạn trong không gian riêng; kho này tách biệt với các tác vụ và tệp kết quả đã bàn giao."
    },
    "chat": {
      "title": "Trò chuyện với AI",
      "description": "Sắp xếp hội thoại, ngữ cảnh và ghi chú riêng tư. Nội dung tại đây không được gửi tới AI."
    },
    "analytics_workspace": {
      "title": "Phân tích số liệu",
      "description": "Tự nhập và ghi lại số liệu, ngày quan sát cùng nhận định của bạn. Mục này không kết nối nền tảng bên ngoài hay lấy số liệu trực tiếp."
    },
    "workboard": {
      "title": "Bảng công việc",
      "description": "Sắp xếp dự án, kế hoạch và bản nháp theo từng nhóm công việc. Bảng này không tự động tạo tác vụ, thông báo hay bài đăng."
    },
    "campaign_planner": {
      "title": "Lập kế hoạch chiến dịch",
      "description": "Ghi lại yêu cầu, mục tiêu, nền tảng và các mốc nội bộ để tự rà soát. Mục này không đăng bài hay lấy số liệu trực tiếp."
    },
    "prompt_studio": {
      "title": "Soạn câu lệnh AI",
      "description": "Tạo bản nháp câu lệnh có cấu trúc từ yêu cầu của bạn để tự rà soát. Công cụ này không gửi tới AI, tạo tác vụ hay xuất tệp."
    },
    "prompt_library": {
      "title": "Thư viện câu lệnh",
      "description": "Lưu mẫu câu lệnh riêng tư kèm nhãn, mô tả và lịch sử chỉnh sửa. Bạn có thể xem trước ngay tại đây mà không gửi nội dung tới AI."
    },
    "free_prompt_gallery": {
      "title": "Thư viện câu lệnh miễn phí",
      "description": "Duyệt, lọc và sao chép các mẫu câu lệnh đã rà soát trong thư viện miễn phí; mẫu chỉ được lưu khi bạn chủ động chọn."
    },
    "content_studio": {
      "title": "Không gian soạn nội dung",
      "description": "Sắp xếp yêu cầu, chú thích, câu mở đầu, kịch bản, phân cảnh và gói nội dung thành các bản nháp riêng tư."
    },
    "channel_strategy": {
      "title": "Chiến lược kênh",
      "description": "Lưu hồ sơ kênh, đối tượng, giọng văn, chủ đề ưu tiên hoặc cần tránh và mục tiêu phát triển. Mục này không kết nối mạng xã hội hay lấy số liệu."
    },
    "content_prompt_pack": {
      "title": "Bộ hướng dẫn nội dung",
      "description": "Tạo bản nháp gồm hướng dẫn, chú thích, câu mở đầu, ý tưởng và định hướng hình ảnh để tự chỉnh sửa; công cụ này không xuất tệp."
    },
    "publish_review_pack": {
      "title": "Gói rà soát trước khi đăng",
      "description": "Chuẩn bị sẵn tiêu đề, chú thích, thẻ chủ đề và lời kêu gọi hành động để kiểm tra; không kết nối mạng xã hội, lên lịch hay đăng bài."
    },
    "contextual_ad_prompt": {
      "title": "Soạn nội dung quảng cáo theo ngữ cảnh",
      "description": "Soạn bản nháp quảng cáo từ chủ đề, mục tiêu, nền tảng, tỷ lệ và phong cách bạn chọn; không kết nối Meta hay dịch vụ ngoài."
    },
    "trend_research": {
      "title": "Lập kế hoạch nghiên cứu xu hướng",
      "description": "Tạo danh sách từ khóa và tiêu chí để bạn tự nghiên cứu xu hướng; không tìm kiếm trực tiếp hay tự thu thập dữ liệu."
    },
    "media_factory": {
      "title": "Lập kế hoạch nội dung đa phương tiện",
      "description": "Lập dàn ý nội dung và kế hoạch video để rà soát, điều phối; chỉ dùng để lập kế hoạch, không tìm kiếm trực tiếp hay tạo tệp."
    },
    "creative_flow": {
      "title": "Soạn quy trình sáng tạo",
      "description": "Soạn bản nháp gồm câu mở đầu, kịch bản, định hướng hình ảnh, nhạc, hiệu ứng, chú thích và lời kêu gọi hành động để rà soát; không tạo tệp phương tiện."
    },
    "source_rights_guide": {
      "title": "Nguồn tư liệu & quyền sử dụng",
      "description": "Xem hướng dẫn chọn nguồn tư liệu, kiểm tra giấy phép, biên tập và lồng tiếng có trách nhiệm; công cụ không xác minh quyền sử dụng."
    },
    "media_workspace": {
      "title": "Thư viện âm thanh & mô tả",
      "description": "Sắp xếp bộ sưu tập âm thanh riêng cùng mô tả nhạc và hiệu ứng; khu vực này chỉ để quản lý, không tạo tệp âm thanh."
    },
    "video_factory_workflow": {
      "title": "Quy trình sản xuất video 7 bước",
      "description": "Xem bản đồ quy trình 7 bước kết nối các khu vực lập kế hoạch video. Chỉ dùng để tham khảo và điều hướng, không tạo hay xuất bản video."
    },
    "story_video_plan": {
      "title": "Lập kế hoạch video kể chuyện",
      "description": "Sắp xếp quy trình kể chuyện và chỉ dẫn chuyển động cho video bằng văn bản gợi ý. Chỉ lập kế hoạch nội dung, không tạo hay xuất bản video."
    },
    "video_studio": {
      "title": "Không gian lập kế hoạch video",
      "description": "Sắp xếp kế hoạch, chia cảnh, chỉnh thứ tự cảnh, tự rà soát và lưu phiên bản; chỉ lập kế hoạch, không tạo video tại đây."
    },
    "video_prompt_planner": {
      "title": "Lập câu lệnh tạo video",
      "description": "Tạo chỉ dẫn video bằng văn bản từ tóm tắt yêu cầu, cảnh quay, tính liền mạch và danh sách kiểm tra. Chỉ lập văn bản, không nhận tệp gốc hay tạo, xem trước hoặc xuất bản video."
    },
    "video_idea_planner": {
      "title": "Lập kế hoạch ý tưởng video",
      "description": "Phát triển ý tưởng thành ba hướng tiếp cận, bảng phân cảnh sáu cảnh, gợi ý hình ảnh, video và bản nháp kế hoạch. Chỉ lập kế hoạch, không tạo, xem trước hay xuất bản video."
    },
    "creative_motion_guide": {
      "title": "Hướng dẫn chuyển động sáng tạo",
      "description": "Chọn nhóm chủ đề, nhận ba gợi ý có thể làm mới và tạo hướng dẫn phong cách, chuyển động bằng văn bản. Chỉ lập kế hoạch nội dung, không tạo ảnh, xem trước hay xuất video."
    },
    "long_form_roadmap": {
      "title": "Lộ trình video thời lượng dài",
      "description": "Chuẩn bị dàn ý, hồ sơ nhân vật, kế hoạch từng phần và gợi ý sáng tạo để rà soát rồi lưu; chỉ lập kế hoạch, không tạo hay đăng video."
    },
    "self_shot_scene_planner": {
      "title": "Lập kế hoạch cảnh tự quay",
      "description": "Soạn chỉ dẫn cảnh quay, gợi ý video, khung hình chính, chuyển động và ghi chú âm thanh, yêu cầu có quyền sử dụng nguồn. Chỉ lập và lưu kế hoạch chữ, không mở tệp phương tiện hay tạo video."
    },
    "script_to_screen_planner": {
      "title": "Lập kế hoạch từ kịch bản lên hình",
      "description": "Soạn kịch bản, bảng phân cảnh, gợi ý ảnh và video, chuyển động và bộ rà soát cho luồng từ kịch bản sang ảnh rồi video hoặc phim dài tập. Chỉ lưu kế hoạch, không nhận tệp, xem trước hay tạo video."
    },
    "audio_hub": {
      "title": "Trung tâm sản xuất âm thanh",
      "description": "Theo dõi và sắp xếp các yêu cầu âm thanh, tài liệu tham khảo từ thư viện và các bước rà soát tại một nơi."
    },
    "music_prompt_composer": {
      "title": "Soạn lời nhắc tạo nhạc",
      "description": "Soạn các hướng nhạc và lời nhắc có cấu trúc để xem lại trước khi dùng; công cụ này không tạo tệp âm thanh."
    },
    "music_direction_presets": {
      "title": "Mẫu định hướng nhạc",
      "description": "Chọn một mẫu có sẵn, nhập yêu cầu để so sánh các hướng nhạc dạng văn bản; không tạo tệp âm thanh."
    },
    "sfx_cue_sheet": {
      "title": "Soạn gợi ý hiệu ứng âm thanh",
      "description": "Chọn mẫu và nhập yêu cầu để soạn gợi ý vị trí hiệu ứng mở đầu, chuyển cảnh hoặc kết thúc; không tìm kiếm hay phát âm thanh."
    },
    "voice_studio": {
      "title": "Hồ sơ giọng và lời thoại",
      "description": "Soạn định hướng giọng đọc, lưu lời thoại và quản lý xác nhận quyền sử dụng; không tạo hay phát âm thanh."
    },
    "voice_direction_composer": {
      "title": "Soạn cách thể hiện",
      "description": "Nhập lời thoại và chọn nhịp đọc để so sánh các cách thể hiện bằng văn bản; không tạo âm thanh."
    },
    "subtitle_studio": {
      "title": "Soạn phụ đề",
      "description": "Soạn bản chép lời, sắp xếp mốc thời gian và bản nháp ngôn ngữ trong không gian riêng; không tạo âm thanh hay video."
    },
    "subtitle_asset_operations": {
      "title": "Tệp phụ đề",
      "description": "Kiểm tra hoặc chuyển đổi tệp phụ đề SRT/VTT trong thư viện riêng; chỉ tải tệp khi kết quả đạt kiểm tra."
    },
    "audio_asset_operations": {
      "title": "Xử lý tệp âm thanh",
      "description": "Kiểm tra tệp âm thanh trong thư viện riêng, chuyển đổi MP3/M4A hoặc chuẩn hóa M4A theo thiết lập sẵn."
    },
    "image_studio": {
      "title": "Không gian sáng tạo ảnh",
      "description": "Lưu ý tưởng, định hướng hình ảnh, các phương án và tư liệu tham khảo riêng; khu vực này dùng để lập kế hoạch, không tạo ảnh."
    },
    "image_hub": {
      "title": "Trung tâm điều phối ảnh",
      "description": "Xem lại ý tưởng hình ảnh, các bước tự kiểm tra và việc cần làm tiếp theo trong cùng một nơi."
    },
    "quick_image_planner": {
      "title": "Lập nhanh ý tưởng ảnh",
      "description": "Soạn nhanh mô tả ảnh từ gợi ý hoặc nội dung tự nhập, rồi rà soát tỷ lệ, biểu trưng và dấu bản quyền; không tạo ảnh."
    },
    "image_prompt_composer": {
      "title": "Soạn mô tả tạo ảnh",
      "description": "Soạn bản nháp mô tả ảnh theo mục tiêu, phong cách và tỷ lệ khung hình để xem lại; không tạo ảnh tại đây."
    },
    "caption": {
      "title": "Chú thích nội dung",
      "description": "Soạn bản nháp chú thích để bạn chỉnh sửa lại trước khi sử dụng."
    },
    "hashtag": {
      "title": "Thẻ chủ đề",
      "description": "Soạn bản nháp thẻ chủ đề theo nội dung để bạn kiểm tra trước khi dùng."
    },
    "hook": {
      "title": "Câu mở đầu",
      "description": "Phác thảo câu mở đầu và nhịp nội dung ngắn từ các mẫu có sẵn."
    },
    "script": {
      "title": "Kịch bản",
      "description": "Soạn bản nháp gồm câu mở đầu, kịch bản và lời kêu gọi hành động để bạn biên tập tiếp."
    },
    "storyboard": {
      "title": "Bảng phân cảnh",
      "description": "Lập kế hoạch phân cảnh và định hướng hình ảnh bằng văn bản; không tạo ảnh hay video."
    },
    "content_pack": {
      "title": "Gói nội dung",
      "description": "Phát triển một chủ đề thành nhiều góc nội dung và câu mở đầu để tiếp tục biên tập."
    },
    "growth_ai": {
      "title": "Rà soát tăng trưởng",
      "description": "Đánh giá theo quy tắc dựa trên các số liệu bạn tự nhập; không dùng AI, dữ liệu trực tiếp hay doanh thu chính thức."
    },
    "campaign_report": {
      "title": "Báo cáo chiến dịch",
      "description": "Báo cáo chiến dịch và bảng tính chính thức được gửi qua Telegram; ứng dụng này không tự tạo bản thay thế."
    },
    "image_create": {
      "title": "Tạo ảnh",
      "description": "Mô tả hình ảnh, chọn loại ảnh và tỷ lệ khung hình, sau đó xem báo giá trước khi xác nhận tạo ảnh."
    },
    "image_edit": {
      "title": "Chỉnh màu và độ nét",
      "description": "Điều chỉnh cơ bản màu sắc, độ tương phản và độ nét cho ảnh đã lưu; thao tác này không dùng AI."
    },
    "image_resize": {
      "title": "Đổi kích thước và tỷ lệ",
      "description": "Cắt, thêm viền hoặc làm mờ nền cho ảnh đã lưu để tạo bản PNG riêng; không phải nâng cấp ảnh bằng AI."
    },
    "image_brand_overlay": {
      "title": "Thêm nhận diện thương hiệu",
      "description": "Thêm chữ hoặc biểu trưng lên bản sao của ảnh đã lưu mà không ghi đè ảnh gốc."
    },
    "image_storyboard_grid": {
      "title": "Chia ảnh theo lưới",
      "description": "Tách ảnh đã lưu thành các khung theo bố cục lưới; chỉ tải tệp khi kết quả đạt kiểm tra."
    },
    "image_upscale": {
      "title": "Nâng độ phân giải ảnh",
      "description": "Tăng độ phân giải lên 2× hoặc 4× cho ảnh thuộc quyền sở hữu của bạn; kết quả chỉ hiển thị sau khi xử lý xong."
    },
    "image_transform": {
      "title": "Biến đổi ảnh",
      "description": "Chọn ảnh nguồn và mô tả thay đổi để tạo phiên bản mới. Ảnh gốc được giữ nguyên; kết quả chỉ hiển thị sau khi xử lý xong."
    },
    "image_remove_background": {
      "title": "Xóa nền ảnh",
      "description": "Chuẩn bị yêu cầu xóa nền ảnh; kết quả chỉ hiển thị sau khi quá trình xử lý hoàn tất."
    },
    "image_history": {
      "title": "Lịch sử xử lý ảnh",
      "description": "Chỉ xem ảnh PNG được tạo bằng công cụ đổi kích thước và chỉnh màu của ứng dụng."
    },
    "voice_tts": {
      "title": "Đọc văn bản thành giọng nói",
      "description": "Nhập lời thoại, chọn giọng đọc, tốc độ và âm lượng, rồi xem báo giá trước khi xác nhận."
    },
    "voice_clone": {
      "title": "Nhân bản giọng nói",
      "description": "Xác nhận quyền sử dụng mẫu, chọn tệp và đặt tên giọng; chỉ tiếp tục khi được phép."
    },
    "voice_saved_tts": {
      "title": "Dùng giọng đã lưu",
      "description": "Chuẩn bị lời thoại với giọng nói đã lưu mà tài khoản của bạn được phép sử dụng."
    },
    "voice_vault": {
      "title": "Giọng nói AI",
      "description": "Đọc văn bản thành giọng nói, dùng giọng đã lưu hoặc chuẩn bị cách thể hiện lời thoại."
    },
    "voice_preview": {
      "title": "Nghe thử giọng",
      "description": "Xem các giọng đã lưu và thông tin bản nghe thử đã được xác nhận."
    },
    "voice_outputs": {
      "title": "Kết quả giọng đọc",
      "description": "Theo dõi tiến trình yêu cầu giọng đọc và mở tệp âm thanh sau khi kết quả được xác nhận."
    },
    "music_library": {
      "title": "Thư viện nhạc",
      "description": "Xem thông tin các bản nhạc đã lưu trong bộ sưu tập âm thanh riêng của tài khoản."
    },
    "sfx_library": {
      "title": "Thư viện hiệu ứng âm thanh",
      "description": "Xem thông tin các hiệu ứng âm thanh đã lưu trong bộ sưu tập riêng của tài khoản."
    },
    "music_background": {
      "title": "Nhạc nền AI",
      "description": "Tạo bản nháp nhạc nền AI, rồi xem ước tính và trạng thái trước khi xác nhận."
    },
    "music_song": {
      "title": "Bài hát có lời",
      "description": "Chuẩn bị yêu cầu bài hát với cấu trúc và tâm trạng; quá trình xử lý chỉ bắt đầu sau khi bạn xác nhận."
    },
    "music_sfx": {
      "title": "Hiệu ứng âm thanh",
      "description": "Mô tả âm thanh bạn muốn tạo; yêu cầu chỉ hoàn tất khi có tệp âm thanh thực tế."
    },
    "music_upload": {
      "title": "Nhạc của tôi",
      "description": "Tải tệp nhạc riêng tư lên tài khoản; định dạng tệp được kiểm tra trước khi lưu."
    },
    "subtitle_asr": {
      "title": "Tạo phụ đề từ video",
      "description": "Chuẩn bị yêu cầu nhận dạng lời nói từ video hoặc âm thanh; phụ đề chỉ hiển thị sau khi kết quả được xác nhận."
    },
    "subtitle_create": {
      "title": "Tạo phụ đề",
      "description": "Thêm video hoặc âm thanh để chuẩn bị yêu cầu tạo phụ đề; bước này chưa tạo sẵn bản chép lời hay tệp SRT/VTT."
    },
    "subtitle_translate": {
      "title": "Dịch phụ đề",
      "description": "Chuẩn bị yêu cầu dịch từ SRT/VTT hoặc văn bản; kiểm tra kỹ ngôn ngữ đích trước khi gửi."
    },
    "cinematic_ad_concept": {
      "title": "Soạn ý tưởng quảng cáo điện ảnh",
      "description": "Soạn ý tưởng quảng cáo, ba hướng sáng tạo, bảng phân cảnh và mô tả dựng cảnh tạm thời từ tóm tắt yêu cầu; chỉ lưu thành bản nháp kế hoạch video khi bạn xác nhận lưu. Chỉ hỗ trợ lập kế hoạch, không tạo hay phát hành video."
    },
    "image_motion_planner": {
      "title": "Lập kế hoạch chuyển động ảnh",
      "description": "Chuyển định hướng tạo ảnh kèm ảnh tham chiếu trong kho tệp thành kế hoạch chuyển động 3 cảnh và bản nháp kế hoạch video riêng tư. Chỉ xác minh thông tin tệp, không mở ảnh; chỉ lập kế hoạch, không tạo hay phát hành video."
    },
    "reference_format_planner": {
      "title": "Lập kế hoạch định dạng tham chiếu",
      "description": "Chuyển cấu trúc tham chiếu thành kế hoạch 3 cảnh nguyên bản từ video riêng tư trong kho tệp. Chỉ kiểm tra thông tin tệp, không mở hay phân tích video, không tải liên kết; chỉ lập kế hoạch, không tạo hay phát hành video."
    },
    "storyboard_composer": {
      "title": "Soạn bộ mô tả bảng phân cảnh",
      "description": "Soạn ba hướng phân cảnh, định hướng hình ảnh nhất quán, danh sách cảnh quay và mô tả văn bản cho ảnh, video kèm yếu tố loại trừ. Chỉ lập kế hoạch dạng chữ, không nhận tệp tải lên, không tạo video hay phát hành."
    },
    "video_single": {
      "title": "Video nhanh",
      "description": "Mở công cụ tạo video nhanh để nhập mô tả hoặc tóm tắt yêu cầu và kiểm tra các bước được hỗ trợ trước khi thực hiện."
    },
    "video_image_to_video": {
      "title": "Ảnh thành video",
      "description": "Mở công cụ chuyển ảnh thành video để chọn ảnh nguồn, mô tả chuyển động mong muốn và kiểm tra các bước được hỗ trợ."
    },
    "video_product": {
      "title": "Video sản phẩm",
      "description": "Mở công cụ video sản phẩm để chuẩn bị thông tin, hình ảnh sản phẩm và kiểm tra các bước được hỗ trợ trước khi thực hiện."
    },
    "video_trend": {
      "title": "Video theo xu hướng",
      "description": "Mở công cụ video theo xu hướng để chọn chủ đề thịnh hành hoặc tham chiếu an toàn và kiểm tra các bước được hỗ trợ."
    },
    "video_text_to_video": {
      "title": "Văn bản thành video",
      "description": "Mở công cụ chuyển văn bản thành video để nhập mô tả và xem các lựa chọn, bước được hỗ trợ trước khi tiếp tục."
    },
    "video_dub": {
      "title": "Lồng tiếng video",
      "description": "Chọn nội dung nguồn, ngôn ngữ đích và giọng đọc; kết quả chỉ hiển thị sau khi được xác nhận."
    },
    "asr": {
      "title": "Nhận dạng lời nói",
      "description": "Chuẩn bị yêu cầu nhận dạng lời nói từ video hoặc âm thanh; bản chép lời chỉ hiển thị khi có kết quả."
    },
    "subtitle_formats": {
      "title": "Đổi định dạng phụ đề",
      "description": "Chuyển đổi qua lại giữa SRT và VTT hoặc tạo nội dung SRT từ văn bản để sao chép; không tạo tệp tải xuống."
    },
    "documents": {
      "title": "Tài liệu & PDF",
      "description": "Chọn công cụ phù hợp cho tài liệu của bạn; mỗi thao tác có giới hạn sử dụng và điều kiện nhận kết quả riêng."
    },
    "documents_pdf": {
      "title": "Công cụ PDF",
      "description": "Chọn thao tác PDF phù hợp; giới hạn xử lý, quyền dùng tệp và điều kiện tải kết quả được kiểm tra trước khi dùng."
    },
    "documents_ocr": {
      "title": "Trích chữ từ ảnh",
      "description": "Trích xuất văn bản từ ảnh riêng tư đã lưu; tệp văn bản chỉ tải được sau khi kết quả được xác minh."
    },
    "documents_pdf_ocr": {
      "title": "Trích chữ từ PDF bản quét",
      "description": "Nhận dạng chữ trong PDF bản quét theo giới hạn trang; chỉ tải tệp văn bản sau khi kết quả được xác minh."
    },
    "documents_pdf_ocr_word": {
      "title": "PDF đã quét thành Word",
      "description": "Trích chữ từ PDF bản quét để tạo tài liệu chỉnh sửa được; chỉ tải kết quả sau khi được xác minh."
    },
    "documents_merge": {
      "title": "Gộp PDF",
      "description": "Gộp các tệp PDF theo thứ tự đã chọn; chỉ tải kết quả sau khi tệp được xác minh."
    },
    "documents_split": {
      "title": "Tách PDF",
      "description": "Tách một trang hoặc một dải trang liên tiếp từ PDF đã lưu; chỉ tải tệp sau khi kết quả được kiểm tra."
    },
    "documents_compress": {
      "title": "Nén PDF không giảm chất lượng",
      "description": "Tối ưu cấu trúc để giảm dung lượng PDF mà không mất dữ liệu; chỉ cung cấp tệp khi bản cuối nhỏ hơn bản gốc."
    },
    "documents_image_to_pdf": {
      "title": "Ảnh sang PDF",
      "description": "Chuyển các ảnh đã lưu thành PDF theo thứ tự đã chọn; chỉ nhận tệp sau khi kết quả được kiểm tra."
    },
    "documents_pdf_to_images": {
      "title": "PDF sang ảnh",
      "description": "Chuyển các trang PDF thành ảnh hoặc gói tệp; chỉ nhận kết quả sau khi từng trang được kiểm tra."
    },
    "documents_pdf_to_word": {
      "title": "PDF có chữ sang Word",
      "description": "Trích văn bản chọn được từ PDF thành tài liệu chỉnh sửa được; không nhận dạng chữ trong ảnh và không cam kết giữ nguyên bố cục."
    },
    "documents_translate": {
      "title": "Dịch tài liệu",
      "description": "Chọn ngôn ngữ đích và gửi yêu cầu dịch; kết quả chỉ hiển thị sau khi được xác nhận hoàn tất."
    },
    "support": {
      "title": "Trung tâm hỗ trợ",
      "description": "Gửi và theo dõi các yêu cầu hỗ trợ cho tài khoản hiện tại của bạn."
    },
    "tickets": {
      "title": "Yêu cầu hỗ trợ của tôi",
      "description": "Theo dõi trao đổi và trạng thái xử lý cho các yêu cầu hỗ trợ của tài khoản hiện tại."
    },
    "operations": {
      "title": "Trung tâm vận hành",
      "description": "Theo dõi tình trạng dịch vụ, mức ưu tiên xử lý và các sự cố."
    },
    "pricing": {
      "title": "Bảng giá",
      "description": "Xem bảng giá bán chính thức được niêm yết; trang này chỉ cung cấp thông tin, không thực hiện giao dịch mua."
    },
    "video_quick": {
      "title": "Video nhanh",
      "description": "Chuẩn bị yêu cầu cho video ngắn. Mở công cụ để xem các bước được hỗ trợ."
    },
    "video_multiscene": {
      "title": "Video nhiều cảnh",
      "description": "Chuẩn bị nội dung, các cảnh và giọng đọc cho video nhiều cảnh; mở công cụ để xem các bước được hỗ trợ."
    },
    "video_long": {
      "title": "Video dài",
      "description": "Chuẩn bị yêu cầu cho dự án video dài và xem các bước được hỗ trợ trong công cụ."
    },
    "video_progress": {
      "title": "Tiến độ video",
      "description": "Mở trang tiến độ video để xem thông tin và các bước được hỗ trợ."
    },
    "video_preview": {
      "title": "Xem trước video",
      "description": "Xem lại tệp MP4/WebM riêng tư đã có sẵn trong kho tệp cá nhân; chỉ dùng để xem tệp hiện có, không phải kết quả AI mới tạo."
    },
    "video_export": {
      "title": "Xuất video",
      "description": "Mở công cụ xuất video để xem các bước và lựa chọn được hỗ trợ."
    },
    "video_addons": {
      "title": "Tiện ích bổ sung video",
      "description": "Mở tiện ích bổ sung video để xem các lựa chọn và các bước được hỗ trợ."
    },
    "video_mux": {
      "title": "Ghép âm thanh và video",
      "description": "Mở công cụ ghép âm thanh với video và xem các bước được hỗ trợ."
    },
    "media_studio": {
      "title": "Không gian đa phương tiện",
      "description": "Lập kế hoạch và mở công cụ phù hợp cho dự án đa phương tiện; không tạo tệp tại đây."
    },
    "tool_directory": {
      "title": "Danh mục công cụ",
      "description": "Xem danh sách công cụ và quy trình hiện có; trạng thái sẵn sàng chỉ hiển thị khi đã được xác nhận."
    }
  },
  "en": {
    "dashboard": {
      "title": "Overview",
      "description": "Track your work, projects, and priorities in one clear place."
    },
    "projects": {
      "title": "Projects",
      "description": "Manage private projects and creative documents in your account."
    },
    "project_packages": {
      "title": "Project archives",
      "description": "View and download checked project archives; these are not service packages."
    },
    "workspace_drafts": {
      "title": "My drafts",
      "description": "Save and continue your private request drafts. Files, quotes, and Telegram task progress are not stored here."
    },
    "workspace_menu": {
      "title": "Switch workspace",
      "description": "Open workspaces grouped around your work goals. Account access and permissions apply separately on each page."
    },
    "account": {
      "title": "Account",
      "description": "Manage your profile, security settings, and sign-in methods."
    },
    "interface_locale_navigator": {
      "title": "Interface language",
      "description": "Choose the display language for the app interface. This does not change the language of your content."
    },
    "account_activity": {
      "title": "Account activity",
      "description": "Review the activity history recorded for your current account."
    },
    "account_security": {
      "title": "Account security",
      "description": "Manage active sessions, your password, and sign-in methods."
    },
    "workspace_care": {
      "title": "Workspace data care",
      "description": "Review your workspace data and open the tool you need."
    },
    "partner_readiness": {
      "title": "Partnership readiness",
      "description": "Prepare a private partnership profile with version history for self-review and noting interest. It does not create referral links, commissions, partner matches, or public listings."
    },
    "notes": {
      "title": "Notes & plans",
      "description": "Keep private notes and plans with labels, priorities, search, archiving, and version history."
    },
    "reminders": {
      "title": "Reminders",
      "description": "Create one-time or recurring reminders, and pause, resume, complete, or cancel them as needed."
    },
    "inbox": {
      "title": "Work inbox",
      "description": "View private work notices recorded while you were away. This inbox does not send external notifications."
    },
    "automation": {
      "title": "Automation center",
      "description": "Review your automation rules and recorded confirmations."
    },
    "referrals": {
      "title": "Referrals",
      "description": "View your referral links and confirmed statistics; benefits apply only when eligibility is met."
    },
    "rewards": {
      "title": "Rewards & gifts",
      "description": "View current promotions, birthday gifts, and eligibility rules. This page is informational only and does not grant benefits directly."
    },
    "community": {
      "title": "Official channels",
      "description": "View and verify official TOAN AAS channels."
    },
    "guides": {
      "title": "Guide center",
      "description": "Find preparation steps and the right workspace in the guide directory."
    },
    "wallet": {
      "title": "Xu wallet",
      "description": "View your Xu balance and transaction history."
    },
    "wallet_topup": {
      "title": "Add Xu",
      "description": "Choose an available top-up method. Xu is credited only after payment is confirmed."
    },
    "packages": {
      "title": "Service packages",
      "description": "Browse available service packages for reference. This page does not place purchases or change your Xu balance."
    },
    "membership": {
      "title": "Membership",
      "description": "View your membership benefits and current plan status. This page does not grant membership tiers or change your Xu balance."
    },
    "jobs": {
      "title": "My tasks",
      "description": "Track tasks for your account; results appear only after delivery is confirmed."
    },
    "assets": {
      "title": "Delivered files",
      "description": "Access your completed files; files appear here only after delivery to your account is confirmed."
    },
    "asset_vault": {
      "title": "Private file library",
      "description": "Store your personal files privately; this library is separate from tasks and delivered files."
    },
    "chat": {
      "title": "AI chat",
      "description": "Organize private conversations, context, and notes. Content here is not sent to AI."
    },
    "analytics_workspace": {
      "title": "Analytics",
      "description": "Manually record metrics, observation dates, and notes. No external platform is connected to fetch live data."
    },
    "workboard": {
      "title": "Workboard",
      "description": "Organize projects, plans, and drafts by workstream. It does not automatically create tasks, notifications, or posts."
    },
    "campaign_planner": {
      "title": "Campaign planner",
      "description": "Record your campaign brief, goals, platforms, and internal dates for review. It does not publish posts or pull live metrics."
    },
    "prompt_studio": {
      "title": "AI prompt studio",
      "description": "Create a structured prompt draft from your brief for review. No content is sent to AI and no file is created."
    },
    "prompt_library": {
      "title": "Prompt library",
      "description": "Save private prompt templates with labels, descriptions, and revision history. Preview them here without sending content to AI."
    },
    "free_prompt_gallery": {
      "title": "Free prompt gallery",
      "description": "Browse, filter, and copy reviewed prompts from the free gallery. Nothing is saved unless you choose to save it."
    },
    "content_studio": {
      "title": "Content studio",
      "description": "Organize briefs, captions, hooks, scripts, storyboards, and content packs into private drafts."
    },
    "channel_strategy": {
      "title": "Channel strategy",
      "description": "Save your channel profile, audience, tone, topics to use or avoid, and goals. No social platforms or analytics are connected."
    },
    "content_prompt_pack": {
      "title": "Content guidance pack",
      "description": "Create an editable draft with guidance, captions, hooks, ideas, and visual direction. No output file is generated."
    },
    "publish_review_pack": {
      "title": "Pre-publish review pack",
      "description": "Prepare a title, caption, hashtags, and call to action for review; does not connect to social accounts, schedule, or publish."
    },
    "contextual_ad_prompt": {
      "title": "Contextual ad copy",
      "description": "Turn your chosen topic, goal, platform, aspect ratio, and style into an ad draft; does not connect to Meta or external services."
    },
    "trend_research": {
      "title": "Trend research plan",
      "description": "Create a keyword list and research criteria to explore trends on your own; does not run live searches or collect data."
    },
    "media_factory": {
      "title": "Multimedia content planner",
      "description": "Create a content and video outline for review and coordination; for planning only, with no live search or file creation."
    },
    "creative_flow": {
      "title": "Creative workflow",
      "description": "Build a written draft with a hook, script, image, music, and sound-effect direction, caption, and call to action for review; no media is created."
    },
    "source_rights_guide": {
      "title": "Sources and usage rights",
      "description": "Read guidance on choosing sources, checking licenses, editing, and responsible voice-over; usage rights are not verified here."
    },
    "media_workspace": {
      "title": "Audio library & briefs",
      "description": "Organize your private audio collections and music or sound-effect briefs; no audio files are generated here."
    },
    "video_factory_workflow": {
      "title": "Video production workflow",
      "description": "View the 7-step workflow map connecting video planning workspaces. Read-only guidance only; does not generate or publish video."
    },
    "story_video_plan": {
      "title": "Story video planner",
      "description": "Outline a story video workflow and text motion directions in one place. Prompt and planning only; does not generate or publish video."
    },
    "video_studio": {
      "title": "Video production studio",
      "description": "Organize video plans, scenes, self-checks and saved versions. This workspace is for planning, not creating video."
    },
    "video_prompt_planner": {
      "title": "Video prompt planner",
      "description": "Draft structured text video directions from your brief, shot details, continuity notes, and review checklist. Text planning only; does not accept media, generate, preview, or publish video."
    },
    "video_idea_planner": {
      "title": "Video idea planner",
      "description": "Turn a video idea into three concepts, a six-scene storyboard, image and video directions, and a draft video plan. Planning only; does not generate, preview, or publish media."
    },
    "creative_motion_guide": {
      "title": "Creative motion guide",
      "description": "Choose a topic group, explore three refreshable ideas, and build a structured text style and motion guide. Planning only; does not generate images, previews, or video."
    },
    "long_form_roadmap": {
      "title": "Long-form video roadmap",
      "description": "Build an outline, character profiles, chapter plan and creative prompts to review, then save your video plan. This tool is for planning, not creating or publishing video."
    },
    "self_shot_scene_planner": {
      "title": "Self-shot scene planner",
      "description": "Plan scene directions, keyframe and video prompts, motion, and audio notes with required permission to use your source, then save a plan. Text planning only; does not open media or generate video."
    },
    "script_to_screen_planner": {
      "title": "Script-to-screen planner",
      "description": "Plan script-to-image-to-video and episodic series into a script, storyboard, image and video prompts, motion notes, and review pack. Saves a plan only; does not accept media, preview, or generate video."
    },
    "audio_hub": {
      "title": "Audio production hub",
      "description": "Keep your audio requests, library references, and review steps organized in one place."
    },
    "music_prompt_composer": {
      "title": "Music prompt composer",
      "description": "Draft structured music directions and prompts to review before use; no audio is generated here."
    },
    "music_direction_presets": {
      "title": "Music direction presets",
      "description": "Choose an available preset and add your brief to compare text-based music directions; no audio is generated."
    },
    "sfx_cue_sheet": {
      "title": "Sound-effect cue sheet",
      "description": "Choose a preset and add a brief to draft opening, transition, and closing sound-effect cues; no audio is searched or played."
    },
    "voice_studio": {
      "title": "Voice profiles and scripts",
      "description": "Prepare voice directions, scripts, and usage-rights confirmations; this workspace does not generate or play audio."
    },
    "voice_direction_composer": {
      "title": "Plan vocal delivery",
      "description": "Enter your script and choose a pace to compare written vocal delivery options; no audio is generated."
    },
    "subtitle_studio": {
      "title": "Subtitle workspace",
      "description": "Organize transcripts, timeline cues, and language drafts in a private workspace; does not generate audio or video."
    },
    "subtitle_asset_operations": {
      "title": "Subtitle file tools",
      "description": "Check or convert SRT and VTT files in your private library; downloads are available once the result passes checks."
    },
    "audio_asset_operations": {
      "title": "Audio file tools",
      "description": "Inspect your saved audio files, convert between MP3 and M4A, or normalize M4A using a fixed preset."
    },
    "image_studio": {
      "title": "Image creative workspace",
      "description": "Keep your ideas, visual directions, variations, and references in one place; for planning only, not image generation."
    },
    "image_hub": {
      "title": "Image operations hub",
      "description": "Review your image ideas, self-check steps, and next actions together in one place."
    },
    "quick_image_planner": {
      "title": "Quick image planner",
      "description": "Draft an image description from a suggestion or your own text, and review aspect ratio, logo, and watermark notes; no image is created."
    },
    "image_prompt_composer": {
      "title": "Compose an image description",
      "description": "Draft an image description by goal, style, and aspect ratio for review; no image is created here."
    },
    "caption": {
      "title": "Caption",
      "description": "Prepare a caption draft for you to edit before using."
    },
    "hashtag": {
      "title": "Hashtags",
      "description": "Draft hashtags based on your content for review before use."
    },
    "hook": {
      "title": "Opening hook",
      "description": "Use available templates to draft an opening hook and plan the pacing of short-form content."
    },
    "script": {
      "title": "Script",
      "description": "Draft an opening line, script, and call to action for further editing."
    },
    "storyboard": {
      "title": "Storyboard",
      "description": "Plan scenes and visual direction in text; no images or videos are created."
    },
    "content_pack": {
      "title": "Content pack",
      "description": "Turn one topic into content angles and opening lines for further editing."
    },
    "growth_ai": {
      "title": "Growth review",
      "description": "Run a rule-based check on metrics you enter manually; does not use AI, live data, or official revenue figures."
    },
    "campaign_report": {
      "title": "Campaign report",
      "description": "Official campaign reports and spreadsheets are sent through Telegram; this app does not create a substitute."
    },
    "image_create": {
      "title": "Create an image",
      "description": "Describe your image, choose the image type and aspect ratio, and review the quote before confirming."
    },
    "image_edit": {
      "title": "Adjust color and sharpness",
      "description": "Make basic color, contrast, and sharpness adjustments to a saved image; this does not use AI."
    },
    "image_resize": {
      "title": "Resize and adjust aspect ratio",
      "description": "Crop, pad, or blur the background of a saved image to create a private PNG copy; this is not AI upscaling."
    },
    "image_brand_overlay": {
      "title": "Add brand identity",
      "description": "Add text or a logo onto a copy of a saved image without overwriting the original."
    },
    "image_storyboard_grid": {
      "title": "Split an image into a grid",
      "description": "Split a saved image into grid frames; downloads are available only after the output passes checks."
    },
    "image_upscale": {
      "title": "Upscale image",
      "description": "Increase resolution by 2× or 4× for an image you own; results appear only after eligibility checks and processing finish."
    },
    "image_transform": {
      "title": "Transform image",
      "description": "Choose a source image and describe the changes you want to create a new version. The original stays intact, and results appear after processing finishes."
    },
    "image_remove_background": {
      "title": "Remove an image background",
      "description": "Prepare a background-removal request; the result appears only after processing is confirmed complete."
    },
    "image_history": {
      "title": "Image processing history",
      "description": "View only PNG images created with the app's resize and color-adjustment tools."
    },
    "voice_tts": {
      "title": "Text to speech",
      "description": "Enter a script, choose a voice, speed, and volume, then review the quote before confirming."
    },
    "voice_clone": {
      "title": "Voice cloning",
      "description": "Confirm rights to the sample, choose a file, and name the voice; continue only when permitted."
    },
    "voice_saved_tts": {
      "title": "Use a saved voice",
      "description": "Prepare a script using a saved voice that your account is permitted to use."
    },
    "voice_vault": {
      "title": "AI voice",
      "description": "Turn text into speech, use saved voices, or plan how a script is delivered."
    },
    "voice_preview": {
      "title": "Voice preview",
      "description": "View saved voices and confirmed preview details."
    },
    "voice_outputs": {
      "title": "Speech results",
      "description": "Track speech requests and open audio files once the result is confirmed."
    },
    "music_library": {
      "title": "Music library",
      "description": "View details of music saved in your account's private audio collection."
    },
    "sfx_library": {
      "title": "Sound-effect library",
      "description": "View details of sound effects saved in your account's private audio collection."
    },
    "music_background": {
      "title": "AI background music",
      "description": "Create an AI background-music draft, then review its estimate and status before confirming."
    },
    "music_song": {
      "title": "Song with lyrics",
      "description": "Prepare a song request with structure and mood; processing starts only after you confirm."
    },
    "music_sfx": {
      "title": "Sound effects",
      "description": "Describe the sound you want to create; the request is complete only when an actual audio file is available."
    },
    "music_upload": {
      "title": "My music",
      "description": "Upload private music to your account; the file format is checked before saving."
    },
    "subtitle_asr": {
      "title": "Create subtitles from video",
      "description": "Prepare a speech-recognition request from video or audio; subtitles appear only after a result is confirmed."
    },
    "subtitle_create": {
      "title": "Create subtitles",
      "description": "Add video or audio to prepare a subtitle request; this step does not generate a transcript or SRT/VTT file yet."
    },
    "subtitle_translate": {
      "title": "Translate subtitles",
      "description": "Prepare a translation request from SRT/VTT or text; check the target language before submitting."
    },
    "cinematic_ad_concept": {
      "title": "Cinematic Ad Concept Composer",
      "description": "Drafts an ad concept, three creative directions, a storyboard, and scene prompts from your brief; saves a video plan draft only when you confirm. For planning only; this tool does not generate or publish video."
    },
    "image_motion_planner": {
      "title": "Image Motion Planner",
      "description": "Turns an image direction with a vault image reference into a 3-scene motion plan and private video plan draft. Verifies file ownership without opening the image; planning only, and does not generate or publish video."
    },
    "reference_format_planner": {
      "title": "Reference Format Planner",
      "description": "Converts a reference layout into an original 3-scene plan from a private vault video. Checks file details only without opening or analyzing the video or fetching links; planning only, and does not generate or publish video."
    },
    "storyboard_composer": {
      "title": "Storyboard Prompt Pack Composer",
      "description": "Creates three storyboard directions, a visual style guide, a shot list, and text prompts for images, video, and exclusions. Text-only planning tool; does not accept media uploads, generate video, save files, or publish."
    },
    "video_single": {
      "title": "Quick Video",
      "description": "Open the quick video tool to enter a video prompt or brief and review the supported steps before starting."
    },
    "video_image_to_video": {
      "title": "Image to Video",
      "description": "Open the image-to-video tool to provide a source image and desired motion, and review the supported steps before starting."
    },
    "video_product": {
      "title": "Product Video",
      "description": "Open the product video tool to prepare your product details and images, and review the supported steps before starting."
    },
    "video_trend": {
      "title": "Trend Video",
      "description": "Open the trend video tool to enter a trend or safe reference and review the supported steps before starting."
    },
    "video_text_to_video": {
      "title": "Text to Video",
      "description": "Open the text-to-video tool to enter a video description and review the supported options and steps before continuing."
    },
    "video_dub": {
      "title": "Dub a video",
      "description": "Choose source media, target language, and voice; results appear only after confirmation."
    },
    "asr": {
      "title": "Speech recognition",
      "description": "Prepare a speech-recognition request from video or audio; no transcript is created until a result is available."
    },
    "subtitle_formats": {
      "title": "Convert subtitle formats",
      "description": "Convert between SRT and VTT, or turn text into copyable SRT content; no downloadable file is created."
    },
    "documents": {
      "title": "Documents & PDF",
      "description": "Choose a document tool; each operation has its own limits, file-access rules, and output conditions."
    },
    "documents_pdf": {
      "title": "PDF tools",
      "description": "Choose a PDF operation; processing limits, file-access rules, and download eligibility are checked before use."
    },
    "documents_ocr": {
      "title": "Extract text from an image",
      "description": "Extract text from a saved private image; the text file is available only after the result is verified."
    },
    "documents_pdf_ocr": {
      "title": "Extract text from a scanned PDF",
      "description": "Recognize text in a scanned PDF within page limits; download the text file only after the result is verified."
    },
    "documents_pdf_ocr_word": {
      "title": "Scanned PDF to Word",
      "description": "Extract text from a scanned PDF into an editable Word document; download is available only after verification."
    },
    "documents_merge": {
      "title": "Merge PDFs",
      "description": "Merge selected PDF files in order; download is available only after the result is verified."
    },
    "documents_split": {
      "title": "Split a PDF",
      "description": "Extract a single page or one continuous page range from a saved PDF; download the file only after the result is checked."
    },
    "documents_compress": {
      "title": "Compress a PDF without data loss",
      "description": "Optimize PDF structure to reduce size without data loss; the file is provided only when the result is smaller."
    },
    "documents_image_to_pdf": {
      "title": "Convert images to PDF",
      "description": "Convert saved images to PDF in the selected order; the file is provided only after it is checked."
    },
    "documents_pdf_to_images": {
      "title": "Convert PDF pages to images",
      "description": "Convert PDF pages into images or a file package; results are provided only after each page is checked."
    },
    "documents_pdf_to_word": {
      "title": "Text PDF to Word",
      "description": "Extract selectable PDF text into an editable Word document; text in images is not recognized and page layout is not guaranteed."
    },
    "documents_translate": {
      "title": "Translate a document",
      "description": "Choose a target language and submit a translation request; view the result only after completion is confirmed."
    },
    "support": {
      "title": "Support center",
      "description": "Submit and track support requests for your current account."
    },
    "tickets": {
      "title": "My support requests",
      "description": "Track replies and status updates for your current account's support requests."
    },
    "operations": {
      "title": "Operations center",
      "description": "Review service health, response priorities and incidents."
    },
    "pricing": {
      "title": "Pricing",
      "description": "View the officially published sale prices. This page provides information only and does not make purchases."
    },
    "video_quick": {
      "title": "Quick video",
      "description": "Prepare a request for a short video. Open the tool to review the supported steps."
    },
    "video_multiscene": {
      "title": "Multi-scene video",
      "description": "Prepare the content, scenes and voiceover for a multi-scene video, then review the supported steps in the tool."
    },
    "video_long": {
      "title": "Long video",
      "description": "Prepare a long-form video project request and review the supported steps in the tool."
    },
    "video_progress": {
      "title": "Video progress",
      "description": "Open the video progress page to review the information and supported steps."
    },
    "video_preview": {
      "title": "Video preview",
      "description": "View an existing private MP4/WebM file already saved in your file library; this displays an existing file, not a newly generated AI result."
    },
    "video_export": {
      "title": "Export video",
      "description": "Open the video export tool to review the supported steps and options."
    },
    "video_addons": {
      "title": "Video add-ons",
      "description": "Explore the video add-ons and review the supported options and steps."
    },
    "video_mux": {
      "title": "Combine audio and video",
      "description": "Open the audio and video combining tool to review the supported steps."
    },
    "media_studio": {
      "title": "Media Studio",
      "description": "Plan a media project and open the tools you need; no media files are created here."
    },
    "tool_directory": {
      "title": "Tool directory",
      "description": "Browse the tools and workflows listed in the catalogue; readiness is shown only when confirmed."
    }
  },
  "zh": {
    "dashboard": {
      "title": "概览",
      "description": "在一个清晰的页面中查看工作、项目和重要事项。"
    },
    "projects": {
      "title": "项目",
      "description": "在您的账户中管理私人项目与创作文档。"
    },
    "project_packages": {
      "title": "项目存档",
      "description": "查看并下载已检查的项目存档；这些并非服务套餐。"
    },
    "workspace_drafts": {
      "title": "我的草稿",
      "description": "保存并继续编辑您的私人请求草稿。文件、报价和 Telegram 任务进度不会保存在此处。"
    },
    "workspace_menu": {
      "title": "工作空间",
      "description": "按工作目标快速进入不同的工作空间。各页面的访问权限按当前账户单独生效。"
    },
    "account": {
      "title": "账户",
      "description": "管理您的个人资料、安全设置和登录方式。"
    },
    "interface_locale_navigator": {
      "title": "界面语言",
      "description": "选择应用界面的显示语言。此设置不会更改您的内容语言。"
    },
    "account_activity": {
      "title": "账户活动",
      "description": "查看当前账户记录的活动历史。"
    },
    "account_security": {
      "title": "账户安全",
      "description": "管理当前登录会话、密码和登录方式。"
    },
    "workspace_care": {
      "title": "工作空间数据管理",
      "description": "检查工作空间数据，并打开合适的工具。"
    },
    "partner_readiness": {
      "title": "合作资料准备",
      "description": "创建仅自己可见的合作准备资料，支持版本记录、自查及记录合作意向。本页不会生成推荐链接、佣金、合作匹配或公开列表。"
    },
    "notes": {
      "title": "笔记与计划",
      "description": "记录私人笔记与计划，支持标签、优先级、搜索、归档和版本记录。"
    },
    "reminders": {
      "title": "提醒",
      "description": "创建单次或重复提醒，并可根据需要暂停、继续、完成或取消。"
    },
    "inbox": {
      "title": "工作收件箱",
      "description": "查看您离开期间记录的私人工作通知。此收件箱不会向外发送通知。"
    },
    "automation": {
      "title": "自动化中心",
      "description": "查看您的自动化规则和已记录的确认信息。"
    },
    "referrals": {
      "title": "推荐好友",
      "description": "查看您的推荐链接和已确认的统计数据；权益仅在符合条件时生效。"
    },
    "rewards": {
      "title": "优惠与礼品",
      "description": "查看当前优惠活动、生日礼品及适用条件。本页面仅作展示，不会直接发放权益。"
    },
    "community": {
      "title": "官方渠道",
      "description": "查看并核对 TOAN AAS 官方渠道。"
    },
    "guides": {
      "title": "指南中心",
      "description": "在指南目录中查找准备步骤和合适的工作空间。"
    },
    "wallet": {
      "title": "Xu 钱包",
      "description": "查看您账户的 Xu 余额和交易记录。"
    },
    "wallet_topup": {
      "title": "充值 Xu",
      "description": "选择当前可用的充值方式。Xu 仅在付款确认后才会到账。"
    },
    "packages": {
      "title": "服务套餐",
      "description": "浏览当前提供的服务套餐信息。本页面仅供参考，不会发起购买或更改 Xu 余额。"
    },
    "membership": {
      "title": "会员方案",
      "description": "查看您的会员权益与当前套餐状态。本页面不会自行授予会员等级或更改 Xu 余额。"
    },
    "jobs": {
      "title": "我的任务",
      "description": "查看您账户下的任务状态；结果仅在确认交付后显示。"
    },
    "assets": {
      "title": "已交付文件",
      "description": "查看已完成的文件；文件仅在确认交付给您的账户后才会显示。"
    },
    "asset_vault": {
      "title": "个人文件库",
      "description": "私密保存您的个人文件；此文件库与任务及已交付文件分开存放。"
    },
    "chat": {
      "title": "AI 对话",
      "description": "整理私人对话、背景信息和备注。此处内容不会发送给 AI。"
    },
    "analytics_workspace": {
      "title": "数据分析",
      "description": "手动记录数据指标、观察日期和备注。本工具不会连接外部平台或获取实时数据。"
    },
    "workboard": {
      "title": "工作看板",
      "description": "按工作条线整理项目、计划和草稿。此处不会自动创建任务、通知或帖子。"
    },
    "campaign_planner": {
      "title": "活动计划",
      "description": "记录活动需求、目标、平台和内部日期以供核对。本工具不会发布帖子或获取实时分析数据。"
    },
    "prompt_studio": {
      "title": "AI 指令编写",
      "description": "根据您的需求编写结构化指令草稿以供核对。本工具不会调用 AI、创建任务或生成文件。"
    },
    "prompt_library": {
      "title": "指令库",
      "description": "保存私人指令模板、标签、说明及修改记录，并可直接在此预览，不会将内容发送给 AI。"
    },
    "free_prompt_gallery": {
      "title": "免费指令库",
      "description": "浏览、筛选并复制免费指令库中经整理的示例；仅在您主动选择时才会保存。"
    },
    "content_studio": {
      "title": "内容创作空间",
      "description": "将需求、配文、开场句、脚本、分镜和内容包整理为私人草稿。"
    },
    "channel_strategy": {
      "title": "频道策略",
      "description": "保存频道资料、受众、语气、优先或需避开的主题及目标。本工具不会连接社交平台或获取分析数据。"
    },
    "content_prompt_pack": {
      "title": "内容创作指南",
      "description": "整理包含指南、配文、开场句、创意和视觉方向的草稿以供编辑；不会生成文件。"
    },
    "publish_review_pack": {
      "title": "发布前检查包",
      "description": "整理标题、配文、话题标签和行动号召供发布前检查；不会连接社交账号，也不会自动排期或发布。"
    },
    "contextual_ad_prompt": {
      "title": "情境广告文案",
      "description": "根据您设定的主题、目标、平台、画面比例和风格整理广告草稿；不会连接 Meta 或外部广告服务。"
    },
    "trend_research": {
      "title": "趋势研究计划",
      "description": "生成关键词清单和研究标准供您自行调研趋势；不会进行实时搜索或抓取数据。"
    },
    "media_factory": {
      "title": "多媒体内容计划",
      "description": "整理内容与视频大纲以供检查和协调；仅用于规划，不会实时搜索或生成文件。"
    },
    "creative_flow": {
      "title": "创意流程编排",
      "description": "整理包含开场句、脚本、画面、音乐和音效方向、配文及行动号召的草稿供检查；不会生成媒体文件。"
    },
    "source_rights_guide": {
      "title": "素材来源与使用权",
      "description": "查看关于挑选素材来源、核查许可、编辑及负责任配音的指引；此处不会核验使用权。"
    },
    "media_workspace": {
      "title": "音频库与需求说明",
      "description": "整理私人音频合集以及配乐和音效需求说明；此处仅用于管理，不会生成音频。"
    },
    "video_factory_workflow": {
      "title": "视频制作七步流程",
      "description": "查看连接各视频规划工作区的七步流程导览。仅供查看与规划导航，不生成或发布视频。"
    },
    "story_video_plan": {
      "title": "故事视频规划",
      "description": "以纯文本方式整理故事视频流程与画面动作指导。仅用于规划与提示词准备，不生成或发布视频。"
    },
    "video_studio": {
      "title": "视频制作规划工作台",
      "description": "整理视频方案、分镜、场景顺序、自查清单与版本记录；此工作区仅用于规划，不会生成视频。"
    },
    "video_prompt_planner": {
      "title": "视频提示词规划",
      "description": "根据创作简报、镜头安排、连贯性要求与检查清单生成结构化文本视频指导。仅支持文本规划，不接收素材文件，也不生成、预览或发布视频。"
    },
    "video_idea_planner": {
      "title": "视频创意规划",
      "description": "将视频创意整理为三个方案、六个场景的分镜表、画面与视频指导及视频方案草稿；仅用于前期规划，不会生成、预览或发布媒体内容。"
    },
    "creative_motion_guide": {
      "title": "创意动态指南",
      "description": "按分组与主题选择方向，获取三组可刷新的灵感建议，并生成结构化文字风格与动态指导。仅用于文字规划，不生成图片、预览或视频。"
    },
    "long_form_roadmap": {
      "title": "长视频规划路线图",
      "description": "整理内容大纲、角色设定、分章计划和创作提示词，检查后保存视频方案；仅用于规划，不会生成或发布视频。"
    },
    "self_shot_scene_planner": {
      "title": "自拍分镜规划",
      "description": "规划分镜指导、视频与关键帧提示词、动作及音频备注，并须具备合法素材使用授权。仅支持文本规划与方案保存，不读取或打开媒体文件，也不生成视频。"
    },
    "script_to_screen_planner": {
      "title": "从剧本到画面规划",
      "description": "围绕剧本转图片再转视频与长剧集两条路线，整理脚本、分镜表、图片与视频提示词、动态说明与审阅包。仅用于保存规划方案，不接收媒体，也不预览或生成视频。"
    },
    "audio_hub": {
      "title": "音频制作中心",
      "description": "在一个页面集中整理音频需求、资料库参考和检查步骤。"
    },
    "music_prompt_composer": {
      "title": "音乐提示词编写",
      "description": "整理结构化的音乐方向和提示词供使用前检查；此处不会生成音频。"
    },
    "music_direction_presets": {
      "title": "音乐方向预设",
      "description": "选择预设模板并填写需求，对比多组文字版音乐方向；不会生成音频。"
    },
    "sfx_cue_sheet": {
      "title": "音效位置提示单",
      "description": "选择预设并填写需求，生成开场、转场或结尾的音效位置提示；不会搜索或播放音频。"
    },
    "voice_studio": {
      "title": "声音档案与台词",
      "description": "编写配音方向、台词并管理使用权确认信息；此工作区不会生成或播放音频。"
    },
    "voice_direction_composer": {
      "title": "规划声音表现",
      "description": "输入台词并选择语速，对比多组文字版配音表现方案；不会生成音频。"
    },
    "subtitle_studio": {
      "title": "字幕工作区",
      "description": "在私人工作区整理文稿、时间轴字幕和语言草稿；不会生成音频或视频。"
    },
    "subtitle_asset_operations": {
      "title": "字幕文件工具",
      "description": "在私人资料库中检查或转换 SRT 与 VTT 字幕文件；结果通过检查后即可下载。"
    },
    "audio_asset_operations": {
      "title": "音频文件处理",
      "description": "检查个人音频文件，进行 MP3 与 M4A 格式转换，或按预设参数标准化 M4A。"
    },
    "image_studio": {
      "title": "图像创意工作区",
      "description": "集中保存您的图像创意、视觉方向、方案和参考资料；此处仅用于规划，不会生成图像。"
    },
    "image_hub": {
      "title": "图像管理中心",
      "description": "在一个页面查看图像创意、自查步骤以及后续待办事项。"
    },
    "quick_image_planner": {
      "title": "快速规划图像",
      "description": "根据建议或您输入的内容快速起草图像描述，并核对比例、标志与水印说明；不会生成图像。"
    },
    "image_prompt_composer": {
      "title": "编写图像描述",
      "description": "按目标、风格和画面比例编写图像描述草稿供检查；此处不会生成图像。"
    },
    "caption": {
      "title": "内容配文",
      "description": "起草配文草稿，供您在使用前自行修改。"
    },
    "hashtag": {
      "title": "话题标签",
      "description": "根据您的内容整理话题标签草稿，供使用前检查。"
    },
    "hook": {
      "title": "开场句",
      "description": "根据现有模板起草开场句和简短的内容节奏。"
    },
    "script": {
      "title": "脚本",
      "description": "整理包含开场句、脚本和行动号召的草稿，供您继续编辑。"
    },
    "storyboard": {
      "title": "分镜表",
      "description": "以文字规划分镜场景与画面方向；不会生成图片或视频。"
    },
    "content_pack": {
      "title": "内容包",
      "description": "将一个主题展开为多个内容角度和开场句，供后续编辑。"
    },
    "growth_ai": {
      "title": "增长检查",
      "description": "根据您手动输入的指标按规则评估；不使用 AI，也不读取实时数据或正式收入数据。"
    },
    "campaign_report": {
      "title": "活动报告",
      "description": "正式的活动报告与表格将通过 Telegram 发送；本应用不会另行生成替代版本。"
    },
    "image_create": {
      "title": "创建图像",
      "description": "描述想要的图像，选择图像类型和画面比例，并在确认创建前查看报价。"
    },
    "image_edit": {
      "title": "调整颜色与清晰度",
      "description": "对已保存图像进行基础色彩、对比度和清晰度调整；此操作不使用 AI。"
    },
    "image_resize": {
      "title": "调整图像尺寸与比例",
      "description": "对已保存图像进行裁剪、留边或背景模糊以生成私人 PNG 副本；并非 AI 放大功能。"
    },
    "image_brand_overlay": {
      "title": "添加品牌标识",
      "description": "在已保存图像的副本上添加文字或品牌标识，不会覆盖原图。"
    },
    "image_storyboard_grid": {
      "title": "按网格拆分图像",
      "description": "按网格布局将已保存图像拆分为多个画面；结果通过检查后方可下载。"
    },
    "image_upscale": {
      "title": "提升图像分辨率",
      "description": "将归您所有的图像分辨率提升 2× 或 4×；确认权属并处理完成后才会显示结果。"
    },
    "image_transform": {
      "title": "转换图像",
      "description": "选择源图像并描述所需修改以生成新版本。原图保持不变，处理完成后才会显示结果。"
    },
    "image_remove_background": {
      "title": "移除图像背景",
      "description": "准备移除图像背景的请求；确认处理完成后才会显示结果。"
    },
    "image_history": {
      "title": "图像处理记录",
      "description": "仅查看本应用的尺寸调整与调色工具生成的 PNG 图片。"
    },
    "voice_tts": {
      "title": "文本转语音",
      "description": "输入台词，选择声音、语速和音量，并在确认前查看报价。"
    },
    "voice_clone": {
      "title": "声音克隆",
      "description": "确认样本使用权，选择文件并为声音命名；仅在获准后才可继续。"
    },
    "voice_saved_tts": {
      "title": "使用已保存的声音",
      "description": "使用您账户获准使用的已保存声音来准备台词。"
    },
    "voice_vault": {
      "title": "AI 语音",
      "description": "将文字转为语音、使用已保存的声音，或规划台词的表现方式。"
    },
    "voice_preview": {
      "title": "声音试听",
      "description": "查看已保存的声音及已确认的试听信息。"
    },
    "voice_outputs": {
      "title": "语音结果",
      "description": "跟踪语音请求的进度，并在结果确认后打开音频文件。"
    },
    "music_library": {
      "title": "音乐库",
      "description": "查看您账户私人音频合集中已保存的音乐信息。"
    },
    "sfx_library": {
      "title": "音效库",
      "description": "查看您账户私人音频合集中已保存的音效信息。"
    },
    "music_background": {
      "title": "AI 背景音乐",
      "description": "创建 AI 背景音乐草稿，并在确认前查看估算与状态。"
    },
    "music_song": {
      "title": "带歌词歌曲",
      "description": "准备歌曲需求、结构与情绪；仅在您确认后才会开始处理。"
    },
    "music_sfx": {
      "title": "音效",
      "description": "描述您想生成的声音；只有获得真实的音频文件后，请求才算完成。"
    },
    "music_upload": {
      "title": "我的音乐",
      "description": "将私人音乐上传至您的账户；保存前会先检查文件格式。"
    },
    "subtitle_asr": {
      "title": "从视频生成字幕",
      "description": "准备从视频或音频识别语音的请求；仅在结果确认后才会显示字幕。"
    },
    "subtitle_create": {
      "title": "生成字幕",
      "description": "添加视频或音频以准备字幕请求；此步骤不会直接生成转录文本或 SRT/VTT 文件。"
    },
    "subtitle_translate": {
      "title": "翻译字幕",
      "description": "使用 SRT/VTT 或文本准备翻译请求；提交前请确认目标语言。"
    },
    "cinematic_ad_concept": {
      "title": "电影感广告创意策划",
      "description": "根据简述整理临时广告创意、三个创作方向、分镜脚本与画面提示词；仅在您确认保存后才保存为视频方案草稿。本工具仅用于策划，不会制作或发布视频。"
    },
    "image_motion_planner": {
      "title": "图像动态规划",
      "description": "将关联个人文件库参考图的画面方向整理为3个场景的动态规划与私密视频方案草稿。仅核验文件归属而不打开原图，仅作规划用途，不会生成或发布视频。"
    },
    "reference_format_planner": {
      "title": "参考格式规划",
      "description": "基于个人文件库中的私密视频将参考方案整理为3个场景的原创规划。仅核验文件信息，不打开或分析视频内容，也不读取外部链接；仅用于规划，不会生成或发布视频。"
    },
    "storyboard_composer": {
      "title": "分镜提示词包编排",
      "description": "拟定三个方向的分镜方案、统一视觉规范、镜头清单以及图片、视频与排除项的文本提示词。仅限文字策划，不接收媒体文件，也不会生成视频、保存文件或发布内容。"
    },
    "video_single": {
      "title": "快速视频",
      "description": "打开快速视频工具，输入视频提示词或简述，并查看当前支持的步骤后再继续操作。"
    },
    "video_image_to_video": {
      "title": "图生视频",
      "description": "打开图生视频工具，提供源图片与期望的动态效果，并查看当前支持的步骤后再继续。"
    },
    "video_product": {
      "title": "产品视频",
      "description": "打开产品视频工具，准备产品信息与图片，并查看当前支持的步骤后再继续。"
    },
    "video_trend": {
      "title": "热门趋势视频",
      "description": "打开热门趋势视频工具，输入趋势主题或安全参考内容，并查看当前支持的步骤后再继续。"
    },
    "video_text_to_video": {
      "title": "文生视频",
      "description": "打开文生视频工具，输入视频描述，并在继续操作前查看支持的选项和步骤。"
    },
    "video_dub": {
      "title": "视频配音",
      "description": "选择源内容、目标语言和声音；仅在结果确认后才会显示。"
    },
    "asr": {
      "title": "语音识别",
      "description": "准备视频或音频语音识别请求；在取得结果前不会生成转录文本。"
    },
    "subtitle_formats": {
      "title": "转换字幕格式",
      "description": "在 SRT 与 VTT 间互转，或将文本整理为可复制的 SRT 内容；不会生成可下载文件。"
    },
    "documents": {
      "title": "文档与 PDF",
      "description": "选择合适的文档工具；每项操作均设有各自的限制、文件权限要求和输出条件。"
    },
    "documents_pdf": {
      "title": "PDF 工具",
      "description": "选择合适的 PDF 操作；使用前会检查处理限制、文件权限及下载条件。"
    },
    "documents_ocr": {
      "title": "提取图片文字",
      "description": "从已保存的私人图片中提取文字；结果通过验证后才提供文本文件。"
    },
    "documents_pdf_ocr": {
      "title": "识别扫描版 PDF 文本",
      "description": "在页数限制内识别扫描版 PDF 中的文字；结果通过验证后才可下载文本文件。"
    },
    "documents_pdf_ocr_word": {
      "title": "扫描版 PDF 转可编辑文档",
      "description": "从扫描版 PDF 提取文字并生成可编辑文档；仅在验证通过后才可下载。"
    },
    "documents_merge": {
      "title": "合并 PDF",
      "description": "按所选顺序合并 PDF 文件；结果通过验证后才可下载。"
    },
    "documents_split": {
      "title": "拆分 PDF",
      "description": "从已保存的 PDF 中提取单页或一个连续页码范围；结果检查通过后才可下载。"
    },
    "documents_compress": {
      "title": "无损压缩 PDF",
      "description": "无损优化 PDF 结构以减小体积；仅当最终文件小于原文件时才会提供。"
    },
    "documents_image_to_pdf": {
      "title": "图片转 PDF",
      "description": "按所选顺序将已保存图片转换为 PDF；文件检查通过后才会提供。"
    },
    "documents_pdf_to_images": {
      "title": "PDF 转图片",
      "description": "将 PDF 页面转换为图片或文件包；逐页检查通过后才会提供结果。"
    },
    "documents_pdf_to_word": {
      "title": "PDF 文本转可编辑文档",
      "description": "提取 PDF 中可选择的文字并转为可编辑文档；不识别图片文字，也不保证保留页面布局。"
    },
    "documents_translate": {
      "title": "翻译文档",
      "description": "选择目标语言并提交翻译请求；仅在确认完成后才会显示结果。"
    },
    "support": {
      "title": "客户支持中心",
      "description": "为当前账户提交并跟踪支持请求。"
    },
    "tickets": {
      "title": "我的支持请求",
      "description": "跟踪当前账户下支持请求的沟通记录与处理状态。"
    },
    "operations": {
      "title": "运营中心",
      "description": "查看服务状态、处理优先级和相关事件。"
    },
    "pricing": {
      "title": "价格",
      "description": "查看官方公布的销售价格；本页仅提供信息，不会发起购买。"
    },
    "video_quick": {
      "title": "快速视频",
      "description": "准备短视频需求，并打开工具查看支持的步骤。"
    },
    "video_multiscene": {
      "title": "多场景视频",
      "description": "准备多场景视频的内容、场景和配音安排，并在工具中查看支持的步骤。"
    },
    "video_long": {
      "title": "长视频",
      "description": "准备长视频项目需求，并在工具中查看支持的步骤。"
    },
    "video_progress": {
      "title": "视频进度",
      "description": "打开视频进度页面，查看相关信息和支持的步骤。"
    },
    "video_preview": {
      "title": "视频预览",
      "description": "播放个人文件库中已有的私有 MP4/WebM 视频文件；此处仅用于查看现有文件，并非新生成的 AI 视频结果。"
    },
    "video_export": {
      "title": "导出视频",
      "description": "打开视频导出工具，查看支持的步骤和选项。"
    },
    "video_addons": {
      "title": "视频附加功能",
      "description": "打开视频附加功能，查看支持的选项和步骤。"
    },
    "video_mux": {
      "title": "音视频合成",
      "description": "打开音视频合成工具，查看支持的合并步骤。"
    },
    "media_studio": {
      "title": "媒体策划中心",
      "description": "规划媒体项目并打开所需工具；此处不会生成媒体文件。"
    },
    "tool_directory": {
      "title": "工具目录",
      "description": "浏览目录中列出的工具与工作流程；仅在确认后才显示就绪状态。"
    }
  }
});
})(window);
