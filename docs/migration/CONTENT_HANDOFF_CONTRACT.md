# Content Handoff Web-native contract

## Mục đích

`copyfast_content_handoff.py` tạo một sổ bàn giao nội bộ, private theo signed
Web account. Đây là bề mặt điều phối có revision để một Project, Asset Vault
file hoặc Campaign Plan Web-owned được rà soát trước khi một nhân sự nội bộ tiếp
nhận. Nó không chuyển dữ liệu Bot sang Web, không phải một social-publishing
adapter và không thay thế Support Desk/ERP.

## Authority và dữ liệu

| Thành phần | Authority | Dữ liệu cho phép |
| --- | --- | --- |
| Customer record | Signed Web account | Tiêu đề, mục đích đã sanitize, opaque `project_id`, `asset_ids`, `campaign_id` |
| Reference validation | Server-side SQLite transaction | Project active, Asset active, Campaign có cùng `account_id` |
| Customer Care review | Signed Web role `admin`, `support_manager`, `support_operator` | Server-side role từ Support Desk, không nhận role/admin ID từ browser |
| Audit | `web_audit_events` | Action, request ID, opaque record ID và metadata ngắn đã sanitize |

Không lưu URL/handle/recipient external, OAuth token, password, API key,
payment proof, provider handle, blob path hoặc nội dung Asset. Reference JSON
chỉ giữ opaque IDs đã được ownership-check trong cùng transaction.

## State machine

`record_state` và `handoff_status` là hai trục độc lập:

```text
record_state: active <-> archived

handoff_status:
draft --customer confirm--> review
review --staff manager--> approved_for_handoff
review/approved_for_handoff --staff--> blocked
approved_for_handoff --staff manager + manual confirmation--> handed_off
blocked --customer edit--> draft
```

`handed_off` chỉ có nghĩa: Customer Care manager/admin đã **ghi nhận một bàn
giao nội bộ do con người thực hiện**. Nó không chứng minh external delivery,
notification, social post, provider result hoặc publish thành công. Envelopes
luôn trả `external_delivery_verified: false` để UI không được đổi nghĩa state
này thành kết quả bên ngoài.

`support_operator` có thể block record đang review/approved với ghi chú; chỉ
`support_manager` hoặc `admin` mới approve hay ghi nhận internal handoff. Quyền
được tính từ signed, server-side Web account qua `require_support_staff`; không
có role nào lấy từ body, localStorage hoặc email allowlist.

## API

Prefix: `/api/v1/content-handoffs`

| Method | Route | Quyền | Mô tả |
| --- | --- | --- | --- |
| GET | `/policy` | public metadata | Boundary và state model, không có data account |
| GET | `/summary` | signed account | Counts của account hiện tại |
| GET | `/records` | signed account | List owner-scoped, mặc định chỉ active |
| GET | `/records/{id}` | signed account | Detail, version metadata, event metadata owner-scoped |
| POST | `/records` | signed + CSRF | Create `draft` với reference IDs đã verify |
| PATCH | `/records/{id}` | signed + CSRF | Full update của `draft` hoặc `blocked`; blocked quay lại draft |
| POST | `/records/{id}/submit-review` | signed + CSRF + confirm | `draft → review` |
| POST | `/records/{id}/archive` | signed + CSRF + confirm | archive record, không thay handoff status |
| POST | `/records/{id}/restore` | signed + CSRF + confirm | restore record, không thay handoff status |
| GET | `/admin/records` | signed Support Desk authority | Queue nội bộ, không trả PII customer |
| POST | `/admin/records/{id}/review` | signed + CSRF + Support Desk authority | Staff decision bounded theo role/state |

Mọi mutation yêu cầu `idempotency_key` hợp lệ và `expected_revision` (ngoại trừ
create), dùng optimistic concurrency và ghi `web_content_handoff_versions`,
`web_content_handoff_events` cùng audit. Idempotency receipt chỉ chứa record
ID, revision và state; không giữ lại purpose, staff note hay references.

## Security / non-goals

- Không import/call Telegram Bot, core bridge, provider, wallet, PayOS, job,
  social API, HTTP client hay publish adapter.
- Không tạo notification, external request, upload, download, asset delivery
  hoặc fake success.
- Text fields chặn control characters, markup, URL/handle external, credential,
  payment evidence và card-like strings.
- Foreign/missing reference trả lỗi generic, không tiết lộ record của account
  khác.
- Module tạo ba bảng additive riêng sau `ensure_copyfast_schema()`:
  `web_content_handoff_records`, `_versions`, `_events`. Không thay đổi shared
  schema hoặc Bot state.

## Rollout

Feature switch: `WEBAPP_CONTENT_HANDOFF_ENABLED=true` (mặc định `true`, có thể
tắt để bảo trì). Module hiện là backend contract độc lập; router/navigation/UI
chỉ nên được đăng ký trong một thay đổi Web App riêng có smoke test, không được
tự suy diễn endpoint này là một publishing integration.

## Focused evidence

```powershell
C:\Users\toann\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m pytest -q tests\test_copyfast_content_handoff.py
```

Kết quả local: `4 passed` (một cảnh báo deprecation từ dependency
`fastapi.testclient`/Starlette, không phải failure của module).
