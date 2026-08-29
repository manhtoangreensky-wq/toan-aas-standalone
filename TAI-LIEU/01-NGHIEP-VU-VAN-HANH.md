# Nghiệp vụ vận hành hiện tại — TOAN AAS Web App

> Phạm vi đo: source Web/Bot đã nghiệm thu local ngày 29/08/2026.
> Tài liệu này mô tả hành vi có bằng chứng trong source; không thay thế hướng dẫn deploy hay quyền phê duyệt của Owner.

## 1. Trạng thái và định danh nguồn

- Web BASE/HEAD: `b9ebe053cb000095254909e4789c1f579cbd5dd2`.
- Bot comparator BASE/HEAD: `6476f20bdd9f8728a5db0b1d62a245b0d612aea8`.
- Inventory P0-05B: `reports/migration/p0-05-prepush-inventory.json`.
- Inventory SHA-256: `b2f6549380826d2688fc648b46237acfe56d20d6512578dead00e3cd131cd7e3`.
- Trạng thái batch manual top-up: `ACCEPTED_LOCAL`.
- Source P0-01 đến P0-05B chưa được hợp nhất vào nhánh Git cuối.
- Batch này chưa được deploy lên VPS.
- Batch này chưa được kiểm thử luồng tiền thật.
- `MERGED != DEPLOYED != LIVE`.
- `HTTP 200` chỉ chứng minh request HTTP được xử lý; nó không chứng minh quyết định tài chính cuối hợp lệ.

## 2. Kiến trúc quyền sở hữu

- Web App là sản phẩm độc lập có signed session, CSRF, tài khoản và nhiều module Web-native.
- Riêng lane manual top-up, Web không phải nguồn ghi số dư Xu hay sổ tài chính canonical.
- Browser gửi yêu cầu qua signed Web session và CSRF.
- Web API kiểm tra owner hoặc Admin bằng authority server-side.
- Web backend gọi private Bot bridge bằng credential chỉ có ở server.
- Bot bridge kiểm tra bearer riêng cho owner và Admin.
- Bot writer thực hiện thay đổi canonical khi Admin confirm hợp lệ.
- Browser không được tự gửi Telegram ID để nhận quyền sở hữu.
- Browser không được tự gửi `admin_id` để nhận quyền Admin.
- Web không cộng Xu trực tiếp.
- Web không tạo PayOS webhook thứ hai.
- Web không duy trì một ledger thanh toán thứ hai.
- Ranh giới tổng quát được mô tả tại `README.md:236-263`.
- Ranh giới Admin server-authoritative được mô tả tại `docs/migration/ADMIN_ERP_NAVIGATION_CONTRACT.md:3-30`.

## 3. Luồng dữ liệu manual top-up

1. Owner đăng nhập Web và có signed session.
2. Owner gửi form manual top-up kèm CSRF và idempotency key.
3. Web lấy canonical owner identity từ session; không lấy từ query/body/header của browser.
4. Web proxy gửi request qua owner bridge tới Bot.
5. Bot tạo một pending deposit và finance invoice ở trạng thái chờ duyệt.
6. Trước quyết định Admin, credit và các positive-credit/usage/revenue event vẫn không tăng.
7. Owner chỉ thấy projection đã loại trường Admin, token và raw bridge data.
8. Admin đăng nhập bằng signed session có role phù hợp.
9. Web kiểm tra canonical Admin identity trước khi gọi Admin bridge.
10. Admin xem list/detail đã được projection và redaction.
11. Admin tạo draft quyết định; bước draft không cộng Xu.
12. Web lưu confirmation receipt ngắn hạn, ràng buộc với đúng Admin session.
13. Admin confirm bằng CSRF, receipt và idempotency key.
14. Bot thực thi đúng một quyết định canonical: approve hoặc reject.
15. Owner đọc lại status/history từ canonical bridge.
16. Luồng thật đã được kiểm bằng temp-only Web↔Bot ASGI fixture tại `tests/test_p0_manual_topup_cross_repo_integration.py:380-505`.

## 4. Các route Web dành cho khách

- `POST /api/v1/payments/manual` — tạo yêu cầu manual top-up.
- `GET /api/v1/payments/manual` — lịch sử owner-scoped.
- `GET /api/v1/payments/manual/{request_id}` — chi tiết owner-scoped.
- `GET /api/v1/payments/manual/{request_id}/status` — trạng thái rút gọn.
- Decorator và handler nằm tại `copyfast_api.py:4689-4763`.
- Placeholder công khai của Web là `{request_id}`.
- Owner khác đọc request không thuộc mình nhận response đã che thông tin.
- Invalid request ID không được dùng để truy vấn tùy ý vào Bot.

## 5. Các route Web dành cho Admin

- `GET /api/v1/admin/payments/manual` — hàng đợi có filter và limit đã kiểm tra.
- `GET /api/v1/admin/payments/manual/{request_id}` — chi tiết an toàn.
- `POST /api/v1/admin/payments/manual/{request_id}/draft` — tạo quyết định nháp.
- `POST /api/v1/admin/payments/manual/{request_id}/confirm` — xác nhận quyết định.
- Decorator và handler nằm tại `copyfast_api.py:4550-4675`.
- Cả hai write route cần signed Admin, CSRF và canonical Admin authority.
- Browser-supplied Admin ID bị bỏ qua hoặc bị từ chối trước bridge.
- Receipt từ Admin session A không dùng được ở session B.

## 6. Các route Bot dành cho owner

- `POST /internal/v1/payments/manual` — canonical create.
- `GET /internal/v1/payments/manual` — canonical owner history.
- `GET /internal/v1/payments/manual/{deposit_id}` — canonical owner detail.
- `GET /internal/v1/payments/manual/{deposit_id}/status` — canonical owner status.
- Decorator nằm tại `bot.py:274555-274732`.
- Placeholder nội bộ của Bot là `{deposit_id}`.
- Không đổi `{deposit_id}` thành `{request_id}` trong tài liệu route map; tên placeholder là một phần source truth.

## 7. Các route Bot dành cho Admin

- `GET /internal/v1/admin/payments/manual` — canonical Admin list.
- `GET /internal/v1/admin/payments/manual/{deposit_id}` — canonical Admin detail.
- `POST /internal/v1/admin/payments/manual/{deposit_id}/draft` — tạo token xác nhận nội bộ.
- `POST /internal/v1/admin/payments/manual/{deposit_id}/confirm` — quyết định canonical.
- Decorator nằm tại `bot.py:274983-275109`.
- Owner bearer gọi Admin route bị từ chối.
- Admin bearer gọi owner route bị từ chối.
- Admin token thiếu hoặc trùng owner token phải fail closed.
- Các denial này được khóa tại `tests/test_p0_manual_topup_cross_repo_integration.py:597-637`.

## 8. State machine và ý nghĩa tiền

- `pending_admin_review`: Bot đã ghi request/invoice chờ Admin; chưa cộng Xu.
- `awaiting_confirm`: Admin đã draft; đây là trạng thái envelope xác nhận, chưa cộng Xu.
- `approved`: Bot đã hoàn tất quyết định approve canonical.
- `rejected`: Bot đã hoàn tất quyết định reject canonical.
- Approve expected dùng số Xu do canonical Bot decision trả về.
- Approve custom yêu cầu số Xu và reason hợp lệ.
- Reject không tạo positive-credit, usage-credit hoặc revenue event.
- Status public không được lộ token, Admin ID riêng hoặc raw bridge response.
- Canonical status được kiểm tại `tests/test_p0_manual_topup_cross_repo_integration.py:380-476`.

## 9. Idempotency và concurrency

- Create dùng idempotency key để tránh tạo lại request do click/retry.
- Confirm dùng idempotency key và confirmation receipt.
- Hai confirm đồng thời chỉ được tạo một mutation canonical.
- Replay cùng key trả terminal result mà không cộng thêm.
- Dùng key khác với receipt đã dùng bị từ chối.
- Reject replay không tăng audit decision lần hai.
- Bằng chứng concurrency/replay nằm tại `tests/test_p0_manual_topup_cross_repo_integration.py:481-505`.
- HTTP retry không được coi là lý do hợp lệ để bỏ qua idempotency.

## 10. Auth, CSRF và ownership

- Signed Web session là nguồn account identity.
- CSRF bắt buộc trên customer create và Admin write.
- Canonical Admin ID được kiểm server-side bằng Bot authority.
- Anonymous customer/Admin read bị từ chối.
- Customer role không được gọi Admin list/draft/confirm.
- Foreign owner không đọc được detail/status của người khác.
- Forged Admin query/body/header không thay đổi canonical Admin identity.
- Cross-session, tampered và expired receipt đều bị từ chối.
- Các denial không được tạo wallet, usage, revenue hoặc audit mutation.
- Bằng chứng đầy đủ nằm tại `tests/test_p0_manual_topup_cross_repo_integration.py:510-589`.
- Raw Telegram ID trong browser không phải authentication; xem `docs/migration/TELEGRAM_WEB_CONNECTION.md:3-18`.

## 11. Safe projection

- Safe projection là projection response theo owner/role, không phải màn hình xem trước giá.
- Owner projection không chứa Admin note riêng, decision token hoặc raw response.
- Admin projection chỉ chứa các trường đã allow-list cho nghiệp vụ duyệt.
- Not-found và foreign-owner response không được tiết lộ record tồn tại.
- Projection không trao quyền write; write vẫn cần role, CSRF và confirmation.
- Bằng chứng owner/Admin projection nằm tại `tests/test_p0_manual_topup_cross_repo_integration.py:380-420`.

## 12. Dữ liệu và artifact kiểm thử

- Integration test dùng Bot DB, Web session DB và legacy Web DB trong pytest temp root.
- Test không đọc database production.
- Test không gọi production endpoint.
- Test dùng actual Web app và actual Bot ASGI handlers; transport chỉ thay network.
- Test chặn PayOS, provider và Telegram delivery bằng sentinel.
- Test xác nhận external HTTP call count bằng `0`.
- Bằng chứng isolation nằm tại `tests/test_p0_manual_topup_cross_repo_integration.py:665-698`.
- `PRODUCTION_RECORD_COUNTS=NOT_MEASURED`.
- Không suy số bản ghi production từ fixture.

## 13. Các số đo source hiện hành

- `tracked_files=1033`: số path trả về bởi `git ls-files` trong Web worktree.
- `production_python_files=100`: tracked `*.py` sau khi loại test/docs/scripts/reports và cache/generated components.
- `fastapi_route_decorators=702`: AST count các decorator HTTP/WebSocket trong tập Python production trên.
- `test_files=352`: tracked `tests/**/test_*.py` theo basename.
- `migration_markdown_files=208`: tracked Markdown dưới `docs/migration/`.
- Định nghĩa và số đo được lưu trong inventory P0-05B; không dùng số cũ trong tài liệu Admin 27/08.

## 14. Configuration surface

- `CORE_BRIDGE_BASE_URL` — địa chỉ bridge server-side; không đưa vào browser.
- `INTERNAL_BILLING_TOKEN` — owner bridge bearer; giá trị không ghi trong Git/tài liệu.
- `INTERNAL_MANUAL_ADMIN_TOKEN` — Admin bridge bearer riêng; không được trùng owner bearer.
- `WEBAPP_COPYFAST_ENABLED` — feature gate chung.
- `WEBAPP_ADMIN_ERP_ENABLED` — Admin ERP gate.
- `WEBAPP_ADMIN_WRITES_ENABLED` — Admin write gate.
- Tài liệu chỉ nêu tên biến, không nêu giá trị, hash hoặc phương pháp suy ra secret.
- Thay đổi ENV/restart là một Owner gate riêng, không thuộc local acceptance.

## 15. Hướng dẫn vận hành an toàn

- Khi khách báo lỗi, ghi `request_id`, thời gian và trạng thái public; không yêu cầu gửi secret.
- Khi Admin xử lý, đọc detail rồi draft trước khi confirm.
- Kiểm tra action, số Xu dự kiến/custom và reason ngay trên confirmation UI.
- Không reuse receipt giữa hai browser session.
- Sau confirm, đọc lại owner status và canonical decision counts.
- Nếu response timeout, retry bằng cùng idempotency key; không tạo key mới tùy tiện.
- Nếu state guarded/unavailable, giữ trạng thái thật và mở incident; không dựng output giả.
- Không sửa SQLite trực tiếp.
- Điều chỉnh tài chính phải là audited compensating business action qua nghiệp vụ được Owner duyệt.
- Không xóa pending deposit hoặc finance invoice để “sửa nhanh”.
- Không chạy provider/PayOS/Telegram smoke chỉ để làm test xanh.

## 16. Cổng an toàn và rollback

- `PROVIDER_CALLS=0` trong toàn bộ local acceptance P0.
- `PAYOS_LIVE_CALLS=0` trong toàn bộ local acceptance P0.
- `TELEGRAM_LIVE_CALLS=0` trong toàn bộ local acceptance P0.
- `EXTERNAL_HTTP_CALLS=0` ngoài in-process ASGI transport.
- `PRODUCTION_WALLET_MUTATIONS=0`.
- `PRODUCTION_DATA_MUTATIONS=0`.
- `ENV_MUTATIONS=0`.
- `LIVE_MONEY_FLOW=NOT_TESTED`.
- Rollback source dùng Git revision/PR được kiểm soát; rollback dữ liệu tài chính không đồng nghĩa sửa DB tay.

## 17. PWA, private data và UI truth

- PWA chỉ cache shell/public allow-list.
- Wallet, payment, Admin, API, download và workspace record không được cache offline.
- PWA boundary được khóa tại `docs/migration/PWA_ROLLOUT_VERSIONING_CONTRACT.md:51-61`.
- UI phải hiển thị guarded/unavailable khi capability chưa sẵn sàng.
- UI direction cấm làm Bot-owned record hoặc provider unavailable trông như ready; xem `docs/UX_APP_FIRST_REDESIGN.md:5-12`.
- `availability` trong Admin navigation là metadata, không phải engine/payment live claim; xem `docs/migration/ADMIN_ERP_NAVIGATION_CONTRACT.md:43-55`.

## 18. Việc còn mở

- `P0-05A`: rotate/revoke và loại ba credential-like tracked paths khỏi Bot HEAD theo security spec riêng.
- `P0-05D`: hoàn thiện case list, hướng dẫn Tester, issue templates và trạng thái project/labels có bằng chứng.
- Hợp nhất accepted Bot/Web source vào nhánh Git thật vẫn chưa thực hiện.
- Pre-push review toàn batch vẫn chưa hoàn tất.
- ENV/secret rotation chưa được thực hiện.
- Commit, push, PR, merge và deploy đều chưa thực hiện.
- Signed production customer/Admin routes chưa được kiểm cho batch này.
- Live money flow không được chạy khi chưa có Owner money gate.

## 19. Bản đồ bằng chứng

- P0-01 request bridge: `evidence/p0-01-codex-sol-manager-accepted-20260828.md`.
- P0-02 Admin decision bridge: `evidence/p0-02-primary-manager-accepted-20260828.md`.
- P0-03 customer Web flow: `evidence/p0-03-primary-manager-accepted-20260829.md`.
- P0-04 Admin Web queue: `evidence/p0-04-primary-manager-accepted-20260829.md`.
- P0-05 local cross-repo integration: `evidence/p0-05-local-integration-accepted-20260829.md`.
- P0-05B static inventory: `evidence/p0-05b-static-inventory-accepted-20260829.md`.
- Các bằng chứng trên chứng minh local source/test; chúng không chứng minh production deployment hoặc live money result.
