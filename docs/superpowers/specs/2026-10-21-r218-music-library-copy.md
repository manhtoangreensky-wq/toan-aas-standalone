# MU-E-02 — Hướng dẫn thư viện ngắn, tự nhiên và đúng khả năng

Dependency: MU-E-01 code/browser đã đạt; delivery source0469183 đang chờ CI.
Không sửa chức năng. Thực thi sau khi cổng Verify của source đó không có lỗi mới.

## CONTRACT

Allowed: `static/portal/portal-i18n.js` chỉ giá trị hiện hữu trong
`MUSIC_LIBRARY_COPY_ROWS`; `static/portal/portal.js` chỉ fallback tương ứng
của ba renderer Music Library. Tests/ledger/evidence cho đúng phạm vi này.
Protected: mọi key/placeholder/action/route/field/DTO/helper, integration.js,
CSS/palette/type scale/motion, dữ liệu người dùng, quyền/auth/backend/provider/ví.
Không thêm việc nghe/tải/tạo âm thanh. Không tạo design system mới cho sửa copy.

## Câu chữ và ưu tiên

Giữ H1 tên thư viện; H2 nội dung đã lưu; nhãn tìm kiếm rõ; phần hạn chế một
đoạn ngắn. Không nhồi các cụm kiểm toán “phiên ký”, “mã thô”, “tài sản chung”,
“trong phạm vi tài khoản” vào hướng dẫn khách. Không dịch tên/thẻ của khách.

| Key sau musicLibrary. | VI | EN | ZH |
|---|---|---|---|
| intro.title.music | Nhạc đã lưu | Saved music | 已保存的音乐 |
| intro.title.sfx | Hiệu ứng âm thanh đã lưu | Saved sound effects | 已保存的音效 |
| intro.description | Tìm nội dung đã lưu và mở bộ sưu tập để xem chi tiết. Thư viện chưa hỗ trợ nghe thử hoặc tải tệp. | Find saved items and open a collection for details. Playback and file downloads are not available here. | 查找已保存的内容，打开合集查看详情。此处暂不支持试听或下载文件。 |
| intro.readOnly | Chỉ xem thông tin | Details only | 仅查看信息 |
| filter.note | Tìm theo tên, bộ sưu tập hoặc thẻ. Từ khóa chỉ dùng trong phiên hiện tại. | Search names, collections or tags. Search terms are used only for this session. | 按名称、合集或标签搜索。关键词仅用于当前会话。 |
| guard.loading.copy | Đang tải danh sách. Vui lòng chờ trong giây lát. | Loading the list. Please wait a moment. | 正在加载列表，请稍候。 |
| guard.failed.copy | Chưa lấy được danh sách. Hãy thử tải lại; nội dung đã lưu không bị thay đổi. | The list could not be loaded. Try again; your saved items are unchanged. | 暂时无法加载列表。请重试，已保存的内容不会更改。 |
| guard.guarded.copy | Bạn cần đăng nhập và được cấp quyền truy cập thư viện âm thanh. | Sign in with an account that has access to the audio library. | 请使用有权访问音频资料库的账户登录。 |
| guard.failed.button | Thử tải lại | Retry loading | 重新加载 |
| result.query | Kết quả cho “{query}”. | Results for “{query}”. | “{query}”的搜索结果。 |
| metadataNotice | Thông tin đã lưu · chưa hỗ trợ nghe hoặc tải tại đây. | Saved details · playback and downloads are unavailable here. | 已保存的信息 · 此处暂不支持试听或下载。 |
| boundary.title | Khả năng hiện tại | Current availability | 当前可用功能 |

Các nhãn/phần còn lại được rút ngắn cùng nghĩa: role SFX thành “hiệu ứng âm
thanh”/“sound effects”/“音效”; guard title nói chưa thể mở, không “được bảo vệ”;
three status chips nói riêng tư/chưa nghe/chưa tải. Boundary vẫn nói rõ chỉ
thông tin, không phát/tạo/giao âm thanh, không tác vụ/tài sản/ví/thanh toán/
Bot/Telegram. Hai result-all vẫn chỉ nội dung đang hoạt động trong bộ sưu tập.
Không bỏ các ranh giới thực tế để giao diện có vẻ đầy đủ hơn.

## Checklist nghiệm thu

- [x] C1 Render ready/loading/failed/guarded/empty/search VI/EN/ZH không lộ
  ngôn ngữ kỹ thuật nội bộ; tên/query/thẻ user vẫn nguyên và được escape.
- [x] C2 Keys/placeholder/action/href/field/DTO/CSS giữ nguyên, không hứa
  nghe/tải/tạo nhạc. Thông tin đầy đủ nhưng câu hướng dẫn ngắn hơn baseline.
- [x] C3 Browser signed profile locale thật, hai theme, 390/768/1440,
  screenshot ready + state/AX/overflow; dùng lại runner tương tác MU-E-01.
- [~] C4 Targeted39/39, full Node856/856, syntax/diff-check đạt; cần commit,
  clean provenance và CI mới trên source copy trước delivery.

Verify: `node --test tests/music-library-locale-purity.test.mjs tests/music-library-runtime-state.test.mjs`
→0fail; browser `music-library-review-20261021.browser.cjs` trên QA DB cô lập.
Q0-TOAST-STACK giữ riêng, không được đánh dấu đã sửa từ screenshot đợi hết toast.
Evidence: `reports/audit/R218-MUSIC-LIBRARY-COPY-QA-20261021.json`.
