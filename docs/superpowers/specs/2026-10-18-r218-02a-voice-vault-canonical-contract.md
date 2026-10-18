# R218-02A — Voice Vault canonical contract gap

Ngày 2026-10-18. Phiếu này khóa phần còn thiếu của P1 Voice: nối Voice Vault
trên Web với cùng một read/write contract mà Bot đang dùng, nhưng không tự
đoán capability hoặc dựng dữ liệu mẫu.

## 1. Phạm vi và bảo vệ

- Chỉ áp dụng WebApp standalone và các projection an toàn cho browser.
- Bot tại `D:\TOANAAS\bot telegram` chỉ được đọc để đối soát; không sửa Bot,
  không gọi provider, không tạo audio/preview, không trừ Xu và không sửa dữ liệu
  production trong phiếu này.
- `provider_voice_id`, `source_file_id`, `source_file_ref`, đường dẫn file,
  token và URL preview riêng tư không được trả về browser.
- Owner-scoped: mọi record và mọi mutation phải được ràng buộc với signed
  account/canonical user hiện tại; không nhận `user_id` từ form.

## 2. Nguồn Bot đã đối soát (read-only)

Các hàm dưới đây là nguồn tham chiếu nghiệp vụ, không phải bằng chứng Web đã
hoàn thành:

| Nghiệp vụ | Nguồn Bot | Điều phải giữ trên Web |
|---|---|---|
| Danh sách + phân trang | `bot.py:169148-169203`, `user_voice_profile_rows` tại `167918` | `items`, `page`, `page_size`, `total`, `has_next`; sắp xếp mặc định trước rồi mới đến ID |
| Giọng mặc định nam/nữ hoặc trung tính | `bot.py:168632`, `voice_vault_keyboard` tại `169245-169264` | Chỉ hiện lựa chọn được DTO capability canonical xác nhận; không fallback im lặng |
| Điều kiện dùng TTS/nghe thử | `bot.py:169009`, `169019` | `tts_ready`, `preview_ready`, `status` phải do canonical trả về |
| Đặt mặc định | `bot.py:167898-167913`, `voice_profile_actions_keyboard` tại `169226` | Mutation riêng, idempotent, owner-scoped, có revision/state mới |
| Xóa mềm | `bot.py:167915-167916` | Không xóa vật lý; record chuyển trạng thái và biến mất khỏi danh sách active |
| Đổi tên | `bot.py:167850-167896` (`update_user_voice_profile`) | Chỉ `display_name`, giới hạn chiều dài, không cho sửa provider/source fields |
| Hành động nghe/tạo/dùng Video | `bot.py:169226-169270` | Handoff phải mang opaque profile ID và return path allowlist; không chỉ mở route trống |

## 3. Tình trạng Web hiện tại — không suy diễn

Đối soát bổ sung ngày 2026-10-19, nguồn Bot local ref `origin/main` tại
`4d086ccb4e1c7fec9c29ac949dbe4e28e2a0955e` (không phải LIVE):

- `bot.py:284199`, `api_internal_subdub_voice_profiles` gọi
  `get_owner_voice_profiles_safe(actor)` với limit mặc định 50. Handler bỏ qua
  `q/page/page_size/limit/offset`; `total=len(items)` là số mục trả về, không
  phải tổng COUNT của kho. Không được dựng pager hay tổng số kho từ giá trị này.
- `services/subdub_voice_resolution.py:73` kiểm owner, bỏ record đã xóa mềm và
  sắp xếp mặc định trước. HTTP API chưa có search hoặc management.
- `copyfast_api.py`: giữ GET proxy/projection đã có. Những proxy POST
  rename/default/delete và GET preview thêm ở `c6bc455` bị gỡ sau rà soát vì
  Core không có các endpoint đó; chúng không phải tính năng đã hoạt động.
- `copyfast_api.py:1891-1892`: projection chỉ cho phép
  `id`, `display_name`, `status`, `is_default`, `consent_status`, `tts_ready`,
  `preview_ready`, `created_at`, `updated_at`.
- `hydrateCanonicalVoiceData` chỉ GET danh sách và trạng thái dịch vụ; hai lần
  đọc độc lập. Xóa danh sách trước await, kiểm epoch/phiên/route sau await,
  phân biệt loading/ready/failed/guarded. Lỗi trạng thái dịch vụ không xóa một
  danh sách giọng đã đọc thành công. Bootstrap xóa dữ liệu trước await đầu tiên.
- `renderVoiceVault` chỉ hiển thị record khi read-state=ready, phân biệt lỗi
  với danh sách rỗng và có nút thử lại dùng GET. Giữ tối đa 50 mục trả về,
  cảnh báo danh sách có thể chưa đầy đủ khi chạm giới hạn; không tự bịa tổng.
- Search/management/preview/handoff vẫn được theo dõi tại T0; không thêm nút
  hoạt động giả hoặc thay Voice Studio metadata cho giọng canonical.

Vì vậy checklist phải giữ các mục quản lý Voice Vault ở trạng thái mở. Không
được thêm nút disabled để tạo cảm giác đã hoàn thành; cũng không được lấy
callback Telegram làm bằng chứng runtime Web.

## 4. DTO tối thiểu cần được canonical authority công bố

### 4.1 Read/list DTO

```json
{
  "items": [
    {
      "id": "opaque-canonical-id",
      "display_name": "Tên hiển thị",
      "status": "ready",
      "is_default": false,
      "consent_status": "confirmed",
      "tts_ready": true,
      "preview_ready": true,
      "created_at": "ISO-8601",
      "updated_at": "ISO-8601"
    }
  ],
  "page": 1,
  "page_size": 5,
  "total": 0,
  "has_next": false,
  "read_state": "ready"
}
```

`page`, `page_size`, `total`, `has_next` chỉ được coi là hợp lệ khi server
trả đủ và nhất quán; Web không tự tính tổng từ một trang bị cắt.

### 4.2 Default capability DTO

```json
{
  "default_voice_options": ["female", "male"],
  "default_voice_source": "canonical",
  "default_voice_read_state": "ready"
}
```

`default_voice_options` chỉ được chứa `female`, `male` hoặc `neutral`. Nếu
authority không trả DTO hoặc trả trạng thái khác `ready`, UI phải guarded và
không tự chọn giọng thay thế.

### 4.3 Mutation receipts

Mỗi mutation phải trả receipt tối thiểu gồm `request_id`, `profile_id`,
`profile_revision`, `status`, `read_state` và thông báo an toàn. Không trả
provider ID, file path hoặc URL nội bộ. Double click/retry cùng idempotency key
không được sinh hai mutation.

## 5. Tiêu chí đóng phiếu

- [ ] Canonical endpoint/DTO được công bố và allowlist ở Web server.
- [ ] List/search/pagination có test owner isolation và stale-account cleanup.
- [ ] Default male/female/neutral được chứng minh bằng capability DTO, không
  hardcode theo nguồn Bot.
- [ ] Rename, set-default, soft-delete có CSRF, idempotency, revision conflict
  và báo cáo trạng thái.
- [ ] Preview chỉ mở khi `preview_ready=true` và delivery adapter đã xác minh;
  thiếu cờ thì không render `<audio>` hoặc URL thay thế.
- [ ] Handoff SubDub/Video truyền profile ID opaque, return path allowlisted và
  giữ draft; browser test chứng minh quay về đúng sản phẩm.
- [ ] Browser VI/EN/ZH × sáng/tối × 390/768/1440 đạt, không overflow/console
  error/foreign request/mutation ngoài thao tác được phép.
- [ ] Chỉ sau các bằng chứng trên mới chuyển VO-09/VO-10/VO-13 sang `[x]`.
  UI được rà và khóa từng lát; phần kỹ thuật còn thiếu giữ ở T0 để tiếp tục
  wave UI kế tiếp theo thứ tự Owner đã chốt. Không chặn toàn bộ UI vì API thiếu.

## 6. Bằng chứng hiện có và blocker

- Voice source/control test: `75/75` pass trong lượt kiểm tra 18/10/2026.
- Full Node ledger trước đó: `601/601` pass; browser Voice synthetic renderer:
  `18/18` pass.
- Các số trên chỉ chứng minh renderer/control-level, không chứng minh DTO,
  backend, preview, runtime hay delivery.
- Lát ngày 2026-10-19 thay bộ regex kiểm tra tên route bằng kiểm thử hành vi
  read-state/hydration/stale response và trình duyệt localhost chạy renderer +
  integration.js thật trên API fixture chỉ-đọc. Kết quả cuối ghi tại ledger.
- Contract kỹ thuật còn thiếu: **Bot/Core management endpoint và preview/handoff
  delivery**. Giữ P1 runtime mở và xử lý các lát UI còn lại theo thứ tự.
