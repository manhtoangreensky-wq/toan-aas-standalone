# R218-06/07/08 — Các sản phẩm còn lại và Admin

Root inventory B21–B34 phải được ánh xạ, kể cả legacy/không hỗ trợ/technical deferred.
Không lược bỏ các sản phẩm này vì chưa là AI tạo media. Chỉ thay UI/copy/local UX.

| ID | Nhóm | Control và trình bày cụ thể | Gate / evidence |
|---|---|---|---|
| UT-01 | Dịch | Text/voice/file, source auto, target search, giữ nguồn/hai chiều, start/stop, copy/export/history | Không nhầm đổi locale UI với target language |
| UT-02 | Content | Brief goal/channel/audience/tone, idea/caption/hashtag/hook/script/CTA, variants/edit/copy/save/version | User data không dịch; draft khác posted |
| UT-03 | Free/Prompt library | Search/filter/category/detail/copy/save, Meta/image/video prompt, publish pack | Nêu giới hạn miễn phí/quota, empty/loading/error |
| UT-04 | QR/avatar/rate/weather/download | Input preview/source, refresh/stale/error, save/download | Không gọi external API trong QA khi chưa phép |
| UT-05 | Notes | List/search/create/detail/edit/version/delete confirmation, reminder/time/repeat | Chỉ dữ liệu người dùng hiện tại; confirmation xóa |
| UT-06 | Documents | File list/order/add/remove, page range/compress choices, preview/confirm/result | Khớp Web validator hiện hành; không chép range Bot vượt contract |
| UT-07 | Assets | Upload status/progress/retry, folders/filter/type/size, preview/tải/quota/expiry | Owner/download readiness, no public URL leak |
| UT-08 | Projects/Workboard | Project list/detail/draft/assets/task dependency/status/assignee/dates/reminder/report | Chỉ nối reference có thật, không fake job |
| AP-01 | AutoPost source | 7 nguồn: topic/URL/affiliate/media/TOAN AAS video/image/plan idea | Picker dùng asset ID, giữ source lineage |
| AP-02 | Content plan/brand | Calendar/agenda, idea→draft→edit/preview→review; brand view/edit/logo/tone | Save feedback + versions/revision |
| AP-03 | Channels | List platform/status/connected/expiry/action, audience/target selection | OAuth/key/publish không mở trong wave UI |
| AP-04 | Queue/history | Draft/approved/scheduled/publishing/published/failed, filters/detail/cancel/review/retry | Đăng thật cần receipt/post link; refresh không submit |
| AP-05 | Affiliate/ads/metrics | Import/list/filter/product selection, budget/status/metrics/guide | Không chi tiền; số thiếu là unknown |
| AC-01 | Profile/security/session | Locale/profile/password controls/session/logout/help | Không làm mất login, stale-account cleanup |
| AC-02 | Packages/price/topup/history | Amount/method→review→QR, pending/admin status/history/detail | Quote/canonical price; approve/ledger/wallet giữ T0 |
| SP-01 | Support/feedback | “Trung tâm hỗ trợ khách hàng”, intake/attachment/context, list/detail/reply/status | Không thêm chữ “web”; link đúng request/job |
| SP-02 | Guide/Chat/community | Search/help theo context, chat mode/usage/stop/history, feedback/handoff | Không fake AI output, provider metadata ẩn |
| AD-01 | Admin nav | Một rail dọc module nhóm rõ, search/filter, badge có ý nghĩa | Owner all; role khác theo manifest/capability |
| AD-02 | Tables/charts | Header/filter/columns/list/cards dọc mobile, detail drawer, legend/labels/empty | Không dùng màu làm nguồn trạng thái duy nhất |
| AD-03 | Customer→Admin | Customer/request/job/asset/report/audit references, status + action errors | Chỉ record thật; thiếu bridge ghi T0 |
| AD-04 | Approval/finance UI | Review/reason/confirm/success/failure, actor/time/reference | Không duyệt tiền thật/đổi luật ví trong wave UI |
| AD-05 | Internal app | Cùng module/quyền/record, bố cục ưu tiên công việc và mobile | Không coi app nội bộ là bản ít quyền thay Web |

Bot anchors: bot.py:42324..42558,71003,123957..123987,184154..184416,
186004..186090,60020..60528,230617; services/autopost_ui.py:48,87,132..321.

## R218 Utilities/Content/Projects control checkpoint — 18/10/2026

Đã khóa presentation-level cho các surface đã có contract Web-native: Content Studio/detail,
Content Prompt Pack, Free Prompt Gallery, Free Tools, Memory Center/Reminder, Project Center
và Workboard. Content Prompt Pack có form một cột, gợi ý theo loại bản nháp, empty/result/
receipt, ranh giới không chạy engine và catalogue fixed chrome cân bằng VI/EN/ZH; bản VI không
còn các chuỗi giao diện như `Draft composer`, `Execution boundary`, `Provider call` hoặc
`Local deterministic draft`. Dữ liệu chủ đề, nội dung, tag, title, receipt và checklist vẫn
được giữ nguyên như dữ liệu owner/server, không dịch trong trình duyệt.

Evidence local ngày 18/10/2026:

```text
UTILITY_TARGETED=25/25 (Content Prompt Pack/Content Studio/Free/Memory/Project/Workboard)
NODE_CHECK=PASS (static/portal/portal.js, static/portal/portal-i18n.js)
GIT_DIFF_CHECK=PASS
```

Đây chỉ là khóa UI/UX fixed chrome và locale. UT-01/04/06/07, AutoPost, Account, Support,
Admin, runtime dữ liệu thật, browser/AX, provider, publish, wallet và live vẫn mở theo bảng
control ở trên; không suy diễn từ route hoặc HTTP 200.

## Bố cục / action state

Không xây catalogue toàn card rời mà mất “việc đang làm”. Header sản phẩm + hành động
chính + nội dung hiện tại; form một cột, bảng đọc được với sticky heading nếu cần.
Mobile list dọc, chi tiết hiện theo yêu cầu; các filters bổ sung có disclosure.
Mỗi action có loading/retry/forbidden/empty/success và báo cáo tham chiếu nếu có record.

## Kiểm không sót

Từng ID chia nhiều control ledger theo R218-00. Menu Bot và Web không trùng một-một:
cần ghi explicit disposition cho duplicate/legacy/admin-only/technical gap.
Đếm classified source controls và unclassified; chỉ đóng completeness khi unclassified=0
trong inventory đã chốt, không dùng số route làm bằng chứng.

## Verify / scope

Focused renderer/action tests giữ route/action/revision/CSRF/ownership contract.
Browser fixture customer/admin/department denied; VI/EN/ZH, light/dark, 375/768/1440.
Không submit nạp/approval/publish/ads production. Các actions đó T0 sau UI/motion và lệnh riêng.
