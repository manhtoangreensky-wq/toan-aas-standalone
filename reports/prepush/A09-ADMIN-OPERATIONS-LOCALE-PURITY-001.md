# A09 Admin Operations — báo cáo trước push

```text
SPEC_ID=A09-ADMIN-OPERATIONS-LOCALE-PURITY-001
BASE_SHA=cc3b4689f85d7c18ebb31b500b1eda1aca20cb6f
BRANCH=fix/a09-admin-operations-locale-purity
STATUS=LOCAL_VERIFIED_AWAITING_COMMIT
PROVIDER_CALLS=0
WALLET_MUTATIONS=0
PAYMENT_MUTATIONS=0
PRODUCTION_DATA_MUTATIONS=0
DEPLOY=NO
LIVE_PASS=NOT_TESTED
```

## 1. Kết quả người dùng nhìn thấy

- `/admin/operations` dùng catalogue fixed-copy VI/EN/ZH thay cho câu Việt–Anh trộn trực tiếp trong renderer.
- Cấu trúc thông tin theo đúng thứ tự: hero → vai trò/trạng thái → bốn số liệu thật → hàng chờ quyết định và ranh giới quyền → lần quét và sự cố.
- Light/dark cùng dùng semantic teal/cyan. Desktop hai cột; `<=980px` hạ grid chính xuống một cột; `<=700px` metric, thẻ và hành động xếp dọc.
- Empty state đổi từ mảng xám nặng thành surface teal-soft có viền nét đứt; nút `Làm mới / Refresh` giữ một dòng.
- Mã động hợp lệ giữ nguyên chữ số; mã không hợp lệ rơi về `review` và luôn được escape.
- Nút đổi locale không bị một remount kéo về `profile.locale` cũ: helper chỉ đồng bộ thêm scalar locale trong profile hiện có, giữ nguyên display name, timezone, session, role, identity và workflow.

## 2. RED → GREEN

| Cổng | RED quan sát | GREEN hiện tại |
|---|---|---|
| Locale renderer | `6 failed`: 43 nhóm foreign fixed-copy trong VI; EN/ZH còn copy Việt; `adminOperations.*=0` | `7 passed`; guarded/loading/manager/operator/partial/populated + 5 heartbeat states + pagination/action/incident đều được render thật |
| UX contract | Marker route-scoped chưa tồn tại | Semantic CSS contract GREEN; raw color/gradient/`!important`/decorative transition/transform bằng `0` |
| Locale receipt | `2 failed`: `interfaceLocale=en` nhưng `profile.locale=vi` còn thắng khi remount | Executable helper contract GREEN; chỉ hai scalar locale đổi, mọi field khác byte-semantically giữ nguyên |
| Protected comparator | Candidate ban đầu `67P/3F`, gồm 1 failure mới do metric hover | Đã bỏ motion trang trí; exact BASE và candidate cùng `68P/2F`, cùng failure IDs, `NEW_FAILURES=0` |
| Tester metadata | Metadata byte/SHA cũ làm readiness fail | `32P/1D`; một case POSIX mode-only được deselect trên Windows, failure `0` |

Fresh combined focused gate cuối trước tài liệu: `151 passed`, `2` dependency warnings, `0` failed. Ba JavaScript file parse exit `0`; `git diff --check` exit `0`.

## 3. Browser QA và fidelity ledger

Nguồn máy đọc: `reports/prepush/A09-ADMIN-OPERATIONS-LOCALE-PURITY-001.json`. Ảnh và JSON thô local nằm ngoài repo tại `evidence/a09-admin-operations-locale-20260910/browser/`.

| Điểm so sánh | Kết quả đo |
|---|---|
| Locale/theme/viewport | `20` trạng thái = VI/EN × light/dark × `1440/1024/768/390/360` |
| Page identity + copy anchor | `20/20`; VI/EN không trộn fixed copy; ZH có renderer executable riêng |
| Hierarchy desktop/mobile | `4` metric desktop, `2` metric tablet, `1` metric mobile; main grid `2→1` cột đúng breakpoint |
| Contrast | `80` phép đo, nhỏ nhất `5.23:1`, lớn nhất `15.17:1` |
| Layout safety | page overflow `0px`; clipped element `0`; high-level horizontal scroller `0`; touch-target violation `0` |
| Runtime health sau readiness | relevant console/network event `0`; framework overlay `0` |
| Side effects | Operations POST/PUT/PATCH/DELETE `0`; approve/reject submit `0` |

Ảnh full-page đã được xem trực tiếp ở VI light desktop và VI dark mobile. Sau vòng visual correction, không còn mảng empty-state xám nặng hoặc CTA desktop xuống hai dòng. Không thêm metric, chart, task hay dữ liệu giả để làm giao diện trông đầy.

## 4. Ranh giới nghiệp vụ và bảo mật

- Hai action `operations-approval-approve/reject`, route, record ID, expected revision và decision code giữ nguyên.
- Browser capability chỉ quyết định có render form; server vẫn giữ CSRF, role, revision và idempotency.
- Dữ liệu động, ID, timestamp, action code và machine code không được dịch; mọi giá trị đi qua `safeText` hoặc validator hữu hạn trước HTML.
- Service worker private boundary, API, schema, database, payment, wallet, provider và ENV không đổi.
- Codex Security scan `8bc4f21a-ed08-46ed-a7ba-ec0a0ae6e8ed`: parent review đủ `7` changed-file surfaces và ghi partial draft `0 findings`. Workbench inventory lỗi `destination escaped its bound context`; không gọi đây là plugin PASS.

## 5. Đối chiếu tài liệu gốc và tester

- `INITIAL_FEATURE_DOC=NOT_FOUND` vẫn đúng; không bịa danh sách chức năng gốc.
- `TAI-LIEU/01-NGHIEP-VU-VAN-HANH.md` cập nhật main/runtime PR #424 và trạng thái local của route Operations.
- `TAI-LIEU/02-CHUC-NANG-GOC-VA-HIEN-TAI.md` loại mô tả stale về PR #424/`78P`; ghi đúng Support `84P` và Operations candidate.
- `KIEM-THU/DANH-SACH-CASE.md` vẫn có đúng `WA-01..WA-43`; WA-43 được mở rộng, không tạo case giả mới.
- `KIEM-THU/HUONG-DAN-TESTER.md` thêm bước `81..87` cho Operations, gồm cổng zero-submit production.
- GitHub readback: tracker #412 `OPEN`, labels `case-test` + `chờ-test`, Project `TOAN AAS Web App · Tester P0` đã gắn. Không có GitHub mutation trong bước readback.

## 6. Chưa được tuyên bố hoàn tất

- Candidate chưa commit/push/PR/merge/deploy; `LOCAL_VERIFIED != LIVE`.
- Signed production DOM của PR #424 Support còn thiếu.
- A09 vẫn còn `/admin/reliability`, `/admin/content-handoffs`, `/admin/work-queue`, `/admin/crm/leads` và exhaustive route audit.
- Ma trận Customer task → Admin report/receipt, phân quyền Web/Internal App và live manual-topup approval là các spec Admin tiếp theo. Luồng tiền production chỉ chạy sau Owner action-time confirmation.
- Goal tổng “Web App hoàn chỉnh từ bot.py” vẫn active và không được đóng bởi PR route này.
