# TOAN AAS — Best-of-Open-Source Web App Blueprint

> **Mục tiêu:** chọn lọc những pattern tốt nhất và phù hợp nhất cho TOAN AAS Web App từ hệ thống hiện tại + các repository mã nguồn mở đã nghiên cứu, bao phủ UI, UX, motion, chức năng, architecture, jobs, assets, billing, Admin/Customer, PWA, accessibility và developer quality.
>
> **Nguyên tắc:** không rewrite lớn; không thay authority model đang đúng; không để UI tự tạo “truth”; ưu tiên thay đổi incremental, có contract/test/CI.
>
> **Snapshot nghiên cứu:** 2026-09-28, nhánh `main` của `manhtoangreensky-wq/toan-aas-standalone`.

---

## 1. Kết luận chọn lọc

TOAN AAS không nên “copy một repo” để trở thành Dify, Open WebUI, Twenty hay Plane. Hệ thống hiện tại đã có những đặc tính rất quan trọng mà nhiều app OSS không có cùng lúc:

- Web session + CSRF rõ ràng.
- Web/Bot authority được phân tách.
- Canonical identity, wallet/Xu và provider execution không bị browser tự quyết.
- Fail-closed khi capability/provider/output chưa được chứng minh.
- Owner-scoped private data và download.
- Customer/Admin hướng tới cùng canonical object thay vì shadow copy.
- PWA cache có allow-list và loại trừ dữ liệu account-private.
- UI đã có design tokens, responsive navigation, command trigger, light/dark theme, i18n VI/EN/ZH, skip-link, focus handling và reduced-motion.
- CI hiện đã chạy cả các contract PWA lifecycle/versioning quan trọng.

Điểm nên làm tiếp không phải thay framework. Điểm có ROI cao nhất là **chuẩn hóa các abstraction đang tồn tại rải rác** thành một hệ thống nhất quán:

1. Design System R1.
2. Capability Registry R1.
3. ExecutionRun + ExecutionEvent R1.
4. Asset + Artifact R1.
5. Provider Capability Registry R1.
6. Role → Permission → Capability R1.
7. Unified Product Workspace UX.
8. Unified Job/Result/History UX.
9. Unified Admin Object Detail + Timeline.
10. Contract → Test → CI Registry.

---

# 2. Những gì nên giữ nguyên từ TOAN AAS

## 2.1 Authority model

Giữ nguyên triết lý:

```text
Browser
  ↓
Web Session / CSRF
  ↓
Web API / Presentation / Web-owned state
  ↓
Canonical Bridge
  ↓
Bot / Ledger / Provider / Runtime authority
```

Browser không được gửi một identity rồi server “tin”. Server phải derive actor từ signed session và canonical mapping.

Web Admin permission cũng không được biến thành quyền ghi trực tiếp vào canonical wallet/runtime nếu authority thật nằm ở Bot.

## 2.2 Truth-first UI

Giữ các invariant:

- Unknown balance ≠ 0.
- Không có output thật ≠ có download.
- Provider chưa proven ≠ “Ready”.
- Planning-only ≠ execution.
- HTTP 200 ≠ media bytes hợp lệ.
- Job metadata completed ≠ artifact bytes tồn tại.
- External/provider URL ≠ public-safe download URL.
- Customer và Admin không được có hai bản ghi “sự thật” khác nhau.

Đây là lợi thế kiến trúc của TOAN AAS và phải được bảo vệ trong mọi cải tiến UI/UX.

## 2.3 PWA private-data boundary

Service worker hiện có explicit shell allow-list và danh sách private route families không được cache. Đây là hướng đúng.

Không biến PWA thành “cache everything”. TOAN AAS có wallet, admin, support, assets, private project metadata và signed-account projections; offline UX phải phân biệt rõ:

- public shell có thể cache;
- private data mặc định `no-store`;
- offline không được replay dữ liệu account trước sau logout/switch account;
- download/private media không được trở thành cache artifact ngoài authority.

## 2.4 Vanilla Web runtime hiện tại

Không đề xuất chuyển toàn Web App sang React chỉ để dùng shadcn/Radix/Motion.

Current Portal đã có:

- `portal.css`
- `portal-theme.css`
- `portal-motion.js`
- `portal-features.js`
- service worker
- browser verification
- nhiều contract test DOM/UX/security.

Rewrite framework lúc này sẽ phá quá nhiều contract và làm tăng regression surface.

**Chiến lược đúng:** lấy pattern từ các repo React/TypeScript, nhưng triển khai tương đương bằng HTML/CSS/JS hiện tại. Chỉ đánh giá framework migration nếu sau này có lý do product/runtime độc lập.

---

# 3. Nguồn OSS được chọn và cách dùng

## 3.1 Radix UI — accessibility behavior reference

Repository: https://github.com/radix-ui/primitives  
License: MIT.  
Code đã xem: `packages/react/focus-scope/src/focus-scope.tsx`, `packages/react/dialog/src/dialog.tsx`.

### Lấy gì

- Focus trapping đúng cho modal/drawer.
- Restore focus khi đóng.
- Escape-to-close.
- Dismissable layer.
- Roving focus cho menu/tabs.
- Dialog/AlertDialog semantics.
- Presence lifecycle mà không phá accessibility.
- Nested overlay behavior.

### Áp dụng vào TOAN AAS

Không import React Radix vào Portal hiện tại. Dùng nó làm **behavior specification** cho các primitive vanilla:

- Dialog
- Drawer
- Dropdown Menu
- Popover
- Tooltip
- Tabs
- Command Palette
- Alert Dialog

### Priority

**P0/P1**, vì accessibility behavior dùng lại trên toàn app.

---

## 3.2 shadcn/ui — component composition và visual discipline

Repository: https://github.com/shadcn-ui/ui  
License: MIT.

### Lấy gì

- Component nhỏ, composable.
- Visual hierarchy sạch.
- Form/control consistency.
- Dialog/sheet/table/card/badge/command patterns.
- Không khóa design system vào một “black-box UI framework”.
- Code ownership thuộc app.

### Áp dụng vào TOAN AAS

Dùng shadcn như **reference cho API/shape của component**, không copy nguyên React stack.

Ví dụ TOAN AAS nên có semantic primitives:

```text
Button
IconButton
Input
Textarea
Select
Checkbox
Radio
Switch
Tabs
SegmentedControl
Badge
StatusPill
Tooltip
Popover
DropdownMenu
Dialog
Drawer
AlertDialog
Toast
Banner
Skeleton
EmptyState
ErrorState
DataTable
Pagination
Timeline
Stepper
Progress
FileDropzone
AssetPicker
CommandPalette
```

Mỗi primitive cần một contract về:

- DOM semantics;
- keyboard;
- focus;
- disabled state;
- loading state;
- error state;
- reduced motion;
- mobile behavior;
- theme behavior.

### Priority

**P0** cho component contract; **P1** cho migration dần các màn hình.

---

## 3.3 Motion — motion language reference

Repository: https://github.com/motiondivision/motion  
License: MIT.  
Code đã xem: `packages/framer-motion/src/components/AnimatePresence/index.tsx`.

TOAN AAS hiện đã có `portal-motion.js`, `prefers-reduced-motion`, View Transition fallback và motion tokens. Vì vậy không cần cài Motion chỉ để có animation.

### Lấy gì

- Presence lifecycle.
- Enter/exit có ý nghĩa.
- Shared layout mental model.
- Stagger có giới hạn.
- Không animate khi content truth chưa có.
- Animation lifecycle tách khỏi domain state.

### Áp dụng

Chuẩn hóa motion thành 4 nhóm:

| Token | Mục đích | Gợi ý |
|---|---|---|
| fast | hover, press, focus, tooltip | 120–160ms |
| base | menu, popover, small state change | 180–240ms |
| slow | drawer, modal, workspace transition | 320–440ms |
| emphasis | success/result reveal quan trọng | 420–600ms |

Current tokens `140ms / 220ms / 420ms` đã rất hợp lý; nên giữ làm baseline.

### Motion rules

1. Motion không được trì hoãn truth.
2. Loading không được giả progress.
3. Job progress chỉ animate theo event/progress thật.
4. Error phải xuất hiện nhanh hơn decorative transition.
5. `prefers-reduced-motion: reduce` phải bỏ transform/stagger/parallax.
6. Hover motion không được là tín hiệu duy nhất.
7. Modal/drawer phải restore focus sau exit.
8. Không chạy infinite animation nếu không biểu diễn một trạng thái đang hoạt động thực.

### Priority

**P0:** contract.  
**P1:** thống nhất các surface.

---

## 3.4 Dify — ExecutionRun, workflow execution, provider abstraction

Repository: https://github.com/langgenius/dify  
License: modified Apache 2.0 với điều kiện bổ sung; **không copy frontend/code vào multi-tenant product nếu chưa review license**.

Code đã xem:

- `api/models/workflow.py` — `WorkflowRun`
- `api/services/workflow_run_service.py`
- `api/core/entities/provider_configuration.py`
- provider/repository/service patterns

### Lấy gì

- Run là durable first-class object.
- Execution không chỉ là một status string trong UI.
- Provider configuration/schema được resolve có cấu trúc.
- Service/repository boundary.
- Tenant/owner context phải đi xuyên qua các layer.

### Áp dụng

Tạo `ExecutionRun` canonical envelope cho TOAN AAS.

```text
run_id
owner_account_id
capability_id
capability_version
input_snapshot_hash
settings_snapshot
idempotency_key

runtime_authority
provider
model

execution_state
financial_state
artifact_state

quote_id
ledger_event_id
artifact_id

created_at
admitted_at
claimed_at
started_at
ended_at

error_code
error_class
terminal_reason
```

Không gộp execution và finance thành một state.

Ví dụ hợp lệ:

```text
execution_state = FAILED
financial_state = NO_CHARGE
artifact_state = NONE
```

hoặc:

```text
execution_state = COMPLETED
financial_state = CHARGED
artifact_state = SEALED
```

### Priority

**P0/P1** vì Product Video, SubDub và các provider job đều hưởng lợi.

---

## 3.5 LibreChat — rich run event taxonomy + secure file delivery

Repository: https://github.com/LibreChat-AI/LibreChat  
License: MIT.

Code đã xem:

- `packages/data-provider/src/types/assistants.ts` với các event như queued, in_progress, requires_action, completed, failed, cancelling, cancelled.
- storage/S3 signed URL patterns đã được nghiên cứu trước.

### Lấy gì

- Run lifecycle đủ giàu để UI không phải đoán.
- Cancel/cancelling là trạng thái thật.
- Requires-action/waiting state là first-class.
- File delivery nên tách storage identity khỏi public URL.

### Áp dụng

TOAN AAS nên có execution states:

```text
DRAFT
PREFLIGHT
ADMITTED
QUEUED
CLAIMED
RUNNING
WAITING_EXTERNAL
WAITING_HUMAN
SEALING_ARTIFACT
COMPLETED
FAILED
CANCELLING
CANCELLED
EXPIRED
```

Financial state riêng:

```text
NOT_APPLICABLE
NOT_QUOTED
QUOTED
NO_CHARGE
CHARGE_PENDING
CHARGED
REFUND_PENDING
REFUNDED
FAILED
```

Artifact state riêng:

```text
NONE
PENDING
RECEIVED
VERIFYING
SEALED
DELIVERY_READY
INVALID
MISSING
```

### Priority

**P1**.

---

## 3.6 Immich — Asset identity, media integrity, derivatives

Repository: https://github.com/immich-app/immich  
License: AGPLv3. **Học pattern; không copy server code trực tiếp vào proprietary TOAN AAS nếu chưa review license.**

Code đã xem:

- `server/src/services/integrity.service.ts`
- `server/src/services/asset-media.service.ts`
- `server/src/services/job.service.ts`
- `server/src/services/queue.service.ts`

### Lấy gì

- Asset là identity, không phải path.
- Integrity scan chủ động.
- Media derivative có lineage.
- Missing/untracked/checksum mismatch là trạng thái vận hành cần phát hiện.
- Media processing được đưa vào job lifecycle.

### Áp dụng

#### Asset

```text
asset_id
owner_account_id
media_type
content_type
byte_size
sha256
storage_backend
storage_key
sealed_at
status
created_at
```

#### Artifact

```text
artifact_id
asset_id
run_id
artifact_type
source_asset_id
operation
operation_version
created_at
delivery_state
```

Browser không cần biết storage path.

### Integrity sweep

```text
MISSING_FILE
UNTRACKED_FILE
BYTE_SIZE_MISMATCH
HASH_MISMATCH
INVALID_CONTENT_TYPE
UNSEALED_TERMINAL_ARTIFACT
ORPHAN_ARTIFACT
ORPHAN_ASSET
```

### Priority

**P0/P1** cho Asset Vault, Product Video, SubDub, PDF/Image outputs.

---

## 3.7 MoneyPrinterTurbo — Product Video UX/pipeline reference

Repository: https://github.com/harry0703/MoneyPrinterTurbo  
License: MIT.

Code đã xem:

- `app/services/task.py`
- `app/services/state.py`
- `app/models/schema.py`
- `app/services/ofox.py`

### Lấy gì

- Task có `task_id/state/progress/videos`.
- Video pipeline chia stage.
- Regenerate/reuse settings UX.
- Progress update theo pipeline.
- Provider normalization.

### Không lấy

Không hạ authority model của TOAN AAS xuống kiểu client-controlled task state.

Wallet, quote, charge, provider capability, owner và artifact truth của TOAN AAS phải mạnh hơn.

### Product Video target UX

```text
Brief
  ↓
Inputs verified
  ↓
Storyboard
  ↓
Provider selection / capability check
  ↓
Quote
  ↓
Admit run
  ↓
Queued
  ↓
Generating
  ↓
Provider output received
  ↓
Media verification
  ↓
Artifact sealed
  ↓
Delivery ready
```

Mỗi stage phải đến từ `ExecutionEvent`, không phải timer UI.

### Priority

**P0** cho Product Video.

---

## 3.8 Open WebUI — fine-grained permissions

Repository: https://github.com/open-webui/open-webui  
License: custom license có branding restrictions; **không copy UI/source trực tiếp nếu chưa review điều kiện**.

Code đã xem:

- `backend/open_webui/utils/access_control/__init__.py`
- `has_permission(user_id, permission_key, ...)`
- permission keys như `features.automations`

### Lấy gì

Role quá thô không đủ cho một app có nhiều capability.

### TOAN AAS target

```text
User
  → Roles
    → Permissions
      → Capabilities
```

Ví dụ:

```text
asset.read_own
asset.download_own
job.read_own
job.cancel_own
support.case.create
support.case.read_own
finance.wallet.read_own
finance.topup.create
admin.account.read
admin.support.assign
admin.finance.review
admin.capability.manage
```

Quan trọng: permission Web chỉ là admission layer. Canonical Bot action vẫn phải re-authorize theo authority của Bot.

### Priority

**P1**.

---

## 3.9 Twenty — metadata-driven Admin UI

Repository: https://github.com/twentyhq/twenty  
License: phần lớn AGPLv3; một số package như `twenty-ui` được nêu là MIT trong license root. **Chỉ reuse code từ package có license được xác minh cụ thể.**

Code/pattern đã xem:

- object metadata
- field metadata
- object permissions
- reusable record views

### Lấy gì

Admin không nên là hàng chục page CRUD viết riêng với layout khác nhau.

### TOAN AAS Admin Object System

```text
ObjectDefinition
FieldDefinition
ViewDefinition
PermissionDefinition
ActionDefinition
TimelineEventDefinition
```

Các object phù hợp:

- Account
- Run
- Job
- Asset
- Artifact
- Wallet/LedgerEvent
- TopUp
- Provider
- Capability
- SupportCase
- Project
- OperationReceipt
- AuditEvent

### Unified Admin Detail

```text
Header
├─ object identity
├─ canonical status
├─ safe actions
└─ context badges

Summary
├─ key fields
├─ owner/account
├─ finance
└─ runtime

Timeline
├─ events
├─ actions
├─ state changes
└─ receipts

Related
├─ runs
├─ assets
├─ artifacts
├─ support
└─ audit
```

### Priority

**P1/P2**.

---

## 3.10 Chatwoot — Support Desk workflow

Repository: https://github.com/chatwoot/chatwoot  
License: core ngoài enterprise directory là MIT Expat theo root license; enterprise code có license riêng.

Code đã xem:

- `app/models/conversation.rb`
- `app/finders/conversation_finder.rb`
- assignee/status filtering patterns

### Lấy gì

Support case cần durable workflow, không chỉ form + message list.

### TOAN AAS Support model

```text
SupportCase
  ├─ status
  ├─ priority
  ├─ category
  ├─ owner_account_id
  ├─ assignee
  ├─ tags
  ├─ related_run_id
  ├─ related_asset_id
  ├─ related_payment_id
  └─ timeline[]
```

Timeline event:

```text
CASE_CREATED
MESSAGE_ADDED
ASSIGNED
STATUS_CHANGED
PRIORITY_CHANGED
RUN_LINKED
ASSET_LINKED
PAYMENT_LINKED
INTERNAL_NOTE_ADDED
RESOLVED
REOPENED
```

### Priority

**P1**.

---

## 3.11 Plane — workspace/sidebar/command palette inspiration

Repository: https://github.com/makeplane/plane  
License: AGPLv3.

Code đã xem:

- `apps/web/core/components/workspace/sidebar/*`
- `apps/web/core/components/power-k/*`
- `apps/web/core/store/base-command-palette.store.ts`

### Lấy gì

- Workspace navigation hierarchy.
- Command palette as a fast navigation/action surface.
- Context-aware actions.
- Project/work-item mental model.

### Áp dụng

TOAN AAS đã có command trigger; nên nâng nó thành một command registry thay vì hard-code UI action.

```text
Command
-------
command_id
label
keywords
route
required_permission
required_capability
context
action_type
shortcut
```

Command palette không được hiển thị action mà user không có quyền/capability.

### Priority

**P1**.

---

## 3.12 Open SaaS — commodity SaaS reference

Repository: https://github.com/wasp-lang/open-saas  
License: MIT.

### Lấy gì

Chỉ dùng làm checklist cho commodity SaaS:

- auth UX;
- email flows;
- account settings;
- payment UX patterns;
- background jobs;
- file upload;
- admin basics;
- E2E testing.

### Không lấy

Không dùng làm core architecture replacement vì TOAN AAS có:

- Bot canonical authority;
- Xu wallet/ledger;
- provider jobs;
- asset truth;
- Admin/Customer parity;
- Product Video/SubDub;
- nhiều Web-native capability.

### Priority

**P2/reference only**.

---

# 4. Target UI/UX architecture

## 4.1 Customer information architecture

Giữ navigation đơn giản theo mục tiêu người dùng:

```text
Home
Create
Work
Library
Projects
Support
Billing
Account
```

### Desktop

Sidebar:

```text
TOAN AAS

+ Create

HOME
  Overview

CREATE
  AI Studio
  Video
  Image
  Voice
  Music
  Subtitle
  Documents
  Content

WORK
  Jobs
  Projects
  Workboard

LIBRARY
  Assets
  Artifacts
  History

SUPPORT
  Cases
  Guides

ACCOUNT
  Wallet & Billing
  Security
  Data Controls
  Settings
```

Không cần hiển thị tất cả feature như một menu phẳng. Feature Catalogue có thể giữ làm discovery surface.

### Mobile

Current 5-item bottom navigation là hợp lý:

```text
Home | Create | Work | Library | Account
```

Support/Billing/Projects đi qua các hub tương ứng hoặc More/Account tùy route.

---

# 5. Unified Product Workspace

Mọi product không nên tự phát minh layout riêng.

## 5.1 Workspace shell

```text
┌─────────────────────────────────────────────────────────┐
│ Product title      capability status       Help         │
│ Short explanation / current project                     │
├──────────────────────────────┬──────────────────────────┤
│ INPUT / EDITOR               │ CONTEXT                  │
│                              │                          │
│ form / upload / prompt       │ cost / capability       │
│ settings                     │ provider truth          │
│ asset picker                 │ run state               │
│ preview                      │ output summary          │
│                              │                          │
├──────────────────────────────┴──────────────────────────┤
│ Primary action / quote / run / cancel                   │
└─────────────────────────────────────────────────────────┘
```

Mobile: stack theo thứ tự Input → Context → Action → Progress → Result.

## 5.2 Capability banner

Mỗi product surface phải nhận một normalized capability projection:

```json
{
  "capability_id": "product_video.generate",
  "availability": "available",
  "execution_mode": "provider",
  "pricing_mode": "quote_required",
  "can_execute": true,
  "reason": null
}
```

UI render từ projection này.

Không để mỗi page tự suy luận:

```js
if (providerUrl && balance > 0 && ...)
```

## 5.3 State patterns dùng chung

### Loading

- skeleton cho layout đã biết;
- spinner chỉ cho action nhỏ;
- không fake percentage.

### Empty

Phải trả lời:

1. Chưa có gì?
2. Vì sao?
3. User làm gì tiếp?
4. CTA nào an toàn?

### Error

Phân loại:

- validation;
- auth/session;
- capability unavailable;
- provider failure;
- financial failure;
- asset verification failure;
- network/transient;
- permission.

Không dùng một toast “Something went wrong” cho tất cả.

### Disabled

Disabled control phải có reason gần control hoặc tooltip/inline note.

### Guarded

Nếu server không xác minh được capability:

```text
Tạm thời chưa thể xác minh khả năng chạy workflow này.
Không có khoản phí nào được thực hiện.
Thử lại
```

Không biến guarded thành disabled vô giải thích.

---

# 6. Job / Run / Result / History UX

Đây nên là một pattern toàn app.

## 6.1 Execution Event Ledger

```text
event_id
run_id
sequence
event_type
stage
status
timestamp
source
safe_metadata
```

Product Video example:

```text
ADMITTED
INPUT_VERIFIED
STORYBOARD_BUILT
QUOTE_ACCEPTED
PROVIDER_SUBMITTED
PROVIDER_PROCESSING
PROVIDER_OUTPUT_RECEIVED
MEDIA_VERIFIED
ARTIFACT_SEALED
DELIVERY_READY
COMPLETED
```

## 6.2 Customer run card

Hiển thị:

- product;
- created time;
- canonical run status;
- progress stage;
- cost state;
- output state;
- one primary next action.

Không hiển thị internal provider error/raw URL.

## 6.3 Run detail

```text
Summary
Progress timeline
Inputs snapshot
Settings snapshot
Cost / quote
Output / artifacts
Safe diagnostics
Retry / create new run
Support link
```

### Retry semantics

Phân biệt:

- **Retry same run**: chỉ cho transient execution khi backend hỗ trợ.
- **Create new run from settings**: new run_id, new idempotency key, new quote nếu giá thay đổi.

Không “retry” bằng cách sửa row cũ thành một execution mới.

---

# 7. Asset Vault / Artifact UX

## 7.1 Asset picker

Một picker dùng chung cho:

- Product Video;
- SubDub;
- Image;
- Documents;
- Voice;
- Content projects.

Filters:

- type;
- created date;
- source;
- project;
- status.

## 7.2 Asset card

Hiển thị safe metadata:

- preview;
- filename/display name;
- media type;
- size;
- created time;
- source product;
- integrity status nếu cần.

Không hiển thị storage path/provider URL.

## 7.3 Artifact lineage

Trong detail:

```text
Source asset
   ↓
Run
   ↓
Operation
   ↓
Artifact
   ↓
Sealed asset
```

Điều này đặc biệt hữu ích cho:

- dubbed video;
- extracted images;
- OCR output;
- ZIP export;
- generated video;
- subtitle file.

## 7.4 Delivery

Target:

```text
GET /api/v1/artifacts/{artifact_id}/download
  → derive signed account
  → owner/permission check
  → artifact lookup
  → asset integrity recheck
  → short-lived delivery
```

Provider URL không phải durable public object identity.

---

# 8. Wallet / Billing UX

## 8.1 Wallet card

Phải tách:

- verified balance;
- pending top-up;
- recent ledger;
- quote/cost estimate;
- billing status.

Nếu balance chưa xác minh:

```text
Số dư hiện chưa thể xác minh
```

không hiển thị `0 Xu`.

## 8.2 Quote UX

Trước provider execution có charge:

```text
Estimated cost
Pricing basis
Quote expiry
Current verified balance
Action: Confirm & run
```

Backend phải là authority của amount.

## 8.3 Run finance status

Trong run detail:

```text
Quoted
Charge pending
Charged
No charge
Refund pending
Refunded
```

Không suy ra charge từ execution state.

---

# 9. Admin UX blueprint

## 9.1 Admin navigation

```text
Overview

OPERATIONS
  Runs & Jobs
  Assets & Artifacts
  Providers
  Capabilities
  Reliability

CUSTOMERS
  Accounts
  Support
  Projects

FINANCE
  Wallet/Ledger
  Top-ups
  Pricing

GOVERNANCE
  Audit
  Operation Receipts
  Permissions
  System Settings
```

## 9.2 Shared canonical detail

Customer và Admin phải nhìn cùng:

- run_id;
- artifact_id;
- job state;
- amount;
- canonical timestamps.

Admin chỉ có thêm privileged metadata/action.

## 9.3 Admin action receipt

Mọi write quan trọng:

```text
operation_id
actor
permission
target_type
target_id
requested_action
before_state
after_state
authority
timestamp
result
reason
```

UI phải render receipt sau action thay vì chỉ toast “Success”.

---

# 10. Design System R1

TOAN AAS đã có token nền tảng khá tốt trong `portal-theme.css`. Không cần thay palette. Cần chuẩn hóa thành layer.

## 10.1 Token layers

### Primitive

```text
color.teal.50 ... 950
color.cyan...
color.slate...
space.1...12
radius.sm/md/lg/xl
font.size...
shadow...
duration...
easing...
```

### Semantic

```text
bg.canvas
bg.surface
bg.raised
text.primary
text.secondary
border.default
border.strong
action.primary
action.primary.hover
status.success
status.warning
status.danger
status.info
focus.ring
```

### Component

```text
button.primary.bg
button.primary.text
input.border
dialog.scrim
sidebar.width
card.radius
toast.shadow
```

Không để component mới thêm raw hex nếu semantic token đã có.

## 10.2 Typography

Đề xuất scale nhỏ, ổn định:

```text
12  caption/meta
13  compact control
14  body small
16  body
18  section title
24  page title
32  hero/dashboard emphasis
```

Tránh quá nhiều `font-weight: 760/850` khác nhau nếu font thực tế không có variable weight cần thiết. Chuẩn hóa semantic weight:

```text
regular 400
medium 500
semibold 600
bold 700
```

Nếu Inter variable được serve/verified thì có thể dùng intermediate weight, nhưng cần nhất quán.

## 10.3 Density

Tạo 2 density modes nội bộ:

- Comfortable: customer-facing.
- Compact: admin/data-heavy table.

Không dùng compact table density cho customer creation workspace.

---

# 11. Accessibility baseline

Mục tiêu: WCAG 2.2 AA cho core flows.

Checklist bắt buộc:

- keyboard complete;
- visible focus;
- skip link;
- focus trap + restore;
- labels cho input;
- error liên kết bằng `aria-describedby`;
- `aria-live` cho status thay đổi cần thông báo;
- table header semantics;
- button không dùng div click;
- icon-only action có accessible name;
- color contrast;
- status không chỉ dựa vào màu;
- touch target tối thiểu hợp lý;
- reduced motion;
- mobile drawer inert background;
- Escape close;
- no focus behind modal.

Current Portal đã có nhiều phần này; cần biến thành component contract để không regression.

---

# 12. Motion language cho TOAN AAS

## 12.1 Meaning-first motion

### Navigation

- route transition: subtle fade/translate;
- không slide quá xa;
- không animate toàn shell nếu chỉ đổi main content.

### Dialog/Drawer

- overlay fade;
- panel 8–16px transform;
- focus chỉ chuyển sau DOM ready;
- exit ngắn hơn enter.

### Job

- progress indicator chỉ dựa vào real event;
- stage change có highlight nhẹ;
- completed có one-shot emphasis;
- failed không bounce/shake quá mức.

### Upload

- real byte progress nếu có;
- nếu không có byte progress thì indeterminate;
- upload completed → verification state → ready.

### Result

- reveal artifact khi sealed/delivery-ready;
- không reveal fake download button trước verification.

## 12.2 Reduced motion

Khi reduce:

- duration gần 0 cho decorative transform;
- giữ instant state change;
- không stagger;
- không parallax;
- không autoplay demo motion dài.

Current `portal-motion.js` đã làm đúng hướng; giữ presentation-only boundary.

---

# 13. Capability Registry R1

```text
Capability
---------
capability_id
product_family
operation

execution_mode:
  LOCAL
  BOT
  PROVIDER
  PLANNING_ONLY
  READ_ONLY

runtime_authority
owner_authority
required_permission

availability
availability_reason

pricing_mode:
  FREE
  QUOTE_REQUIRED
  CANONICAL_REMOTE
  NOT_APPLICABLE

input_schema_version
output_schema_version

preflight_handler
execution_adapter
artifact_type
enabled
```

Examples:

```text
product_video.storyboard.generate
product_video.video.generate
subdub.dubbing.execute
image.resize.local
pdf.split.local
voice_studio.author
support.case.create
asset.download
```

## UI projection

Server trả một normalized projection để UI render badge/action.

Không duplicate capability logic ở:

- sidebar;
- catalogue;
- workspace;
- admin;
- command palette.

---

# 14. Provider Capability Registry R1

```text
provider
model
capability
configured
credential_available
health_status
proven_in_production
last_verified_at

supports_cancel
supports_async
supports_webhook
supports_poll

max_duration
input_types
output_types
```

Derived:

```text
advertised_available =
  product_enabled
  AND configured
  AND credential_available
  AND health_acceptable
  AND capability_supported
  AND proven_if_required
```

UI không được tự check provider name rồi quyết định “available”.

---

# 15. Storage Backend R1

Interface:

```text
put
open/read
stat
delete
exists
checksum
create_delivery
```

Backends có thể là:

- local private storage;
- S3-compatible object storage;
- future managed storage.

Business layer chỉ biết `asset_id`, không biết path.

Không cần migrate khỏi local storage ngay. Chỉ cần abstraction trước để tránh khóa architecture.

---

# 16. Contract → Test → CI Registry

Current CI đã có bounded critical suite và hiện đã bao gồm PWA lifecycle/versioning tests. Giữ hướng này và formalize.

```yaml
contracts:
  pwa_rollout:
    sources:
      - static/portal/service-worker.js
    docs:
      - docs/migration/PWA_ROLLOUT_VERSIONING_CONTRACT.md
    tests:
      - tests/test_portal_service_worker_lifecycle.py
      - tests/test_pwa_rollout_versioning.py
    required_ci_gate: true

  artifact_delivery:
    sources:
      - copyfast_api.py
      - copyfast_native_read_models.py
    tests:
      - tests/...
    required_ci_gate: true
```

CI validation:

1. contract có `required_ci_gate=true`;
2. test path tồn tại;
3. workflow thực sự invoke test;
4. source path tồn tại;
5. optional: owner/team.

Mục tiêu là tránh tình huống contract đúng, test có, nhưng CI quên chạy.

---

# 17. Những thứ không nên làm

## Không rewrite React/Next ngay

Lý do:

- Portal vanilla hiện có nhiều contract.
- Auth/PWA/private cache behavior đã được harden.
- UI đang có semantic tokens và motion lifecycle.
- Framework rewrite không trực tiếp giải quyết capability/run/asset truth.

## Không copy nguyên Dify/Open WebUI/Immich/Twenty/Plane

Ngoài mismatch architecture còn có license risk.

## Không dùng provider URL làm output identity

Luôn seal thành Asset/Artifact.

## Không đưa queue/distributed infra vào sớm

SQLite + one-replica có thể vẫn hợp lý. Chỉ cân nhắc Postgres/Redis/queue khi thực sự cần:

- nhiều Web replicas;
- distributed workers;
- concurrent job claims cao;
- shared queue;
- event volume lớn.

## Không biến motion thành product logic

`portal-motion.js` đang đúng khi presentation-only. Giữ boundary này.

## Không làm Admin thành một app dữ liệu riêng

Admin là privileged projection/action layer trên canonical objects.

---

# 18. Source → Pattern → TOAN AAS target

| Source | Pattern tốt nhất | TOAN AAS target | Cách dùng | Priority |
|---|---|---|---|---|
| Radix UI | focus/dialog/menu behavior | Accessible primitives | Adapt behavior, không cần React | P0 |
| shadcn/ui | composable component system | Design System R1 | Adapt visual/API patterns | P0 |
| Motion | presence/motion lifecycle | Motion Contract R1 | Adapt principles/tokens | P0 |
| Dify | WorkflowRun/provider registry | ExecutionRun + ProviderCapability | Adapt architecture; không copy license-sensitive frontend | P0 |
| Immich | asset identity/integrity | Asset + Artifact + Integrity Sweep | Adapt architecture | P0 |
| MoneyPrinterTurbo | video task stages/progress | Product Video workspace | Adapt UX/pipeline; giữ authority mạnh hơn | P0 |
| LibreChat | run event states/signed delivery | ExecutionEvent + secure delivery | Adapt architecture | P1 |
| Open WebUI | permission keys | Role→Permission→Capability | Adapt model; không copy branded UI | P1 |
| Twenty | metadata-driven objects/admin | Admin Object System | Adapt pattern; license-review code reuse | P1 |
| Chatwoot | support case workflow | Support Desk R1 | Adapt domain model | P1 |
| Plane | sidebar/command palette/work items | Command Registry + Workboard UX | Visual/behavior inspiration; AGPL caution | P1 |
| Open SaaS | commodity SaaS checklist | Account/email/E2E hygiene | Reference only | P2 |

---

# 19. Giữ nguyên / Cải tiến / Thay thế / Chưa nên làm

| Nhóm | Quyết định | Nội dung |
|---|---|---|
| Web/Bot authority | GIỮ | canonical identity/wallet/provider authority |
| CSRF/signed session | GIỮ | current security boundary |
| PWA private cache allow-list | GIỮ | chỉ public shell |
| Theme teal/cyan | GIỮ | đã có identity riêng |
| Motion presentation-only | GIỮ | không để animation sở hữu state |
| Feature catalogue | CẢI TIẾN | drive từ Capability Registry |
| Product pages | CẢI TIẾN | Unified Product Workspace |
| Jobs | CẢI TIẾN | ExecutionRun + Event timeline |
| Assets | CẢI TIẾN | Asset/Artifact split + integrity |
| Admin | CẢI TIẾN | metadata-driven detail/timeline |
| Support | CẢI TIẾN | durable case workflow |
| Permissions | CẢI TIẾN | permission keys + capability |
| Download | THAY DẦN | provider URL → artifact_id delivery |
| Scattered component CSS | THAY DẦN | Design System primitives |
| Scattered status mapping | THAY DẦN | normalized state projection |
| Full React rewrite | CHƯA NÊN | ROI thấp/risk cao hiện tại |
| Postgres/Redis migration | CHƯA NÊN | chỉ khi concurrency/replica yêu cầu |
| Microservices split | CHƯA NÊN | domain modularization trước |
| Heavy animation framework | CHƯA NÊN | current motion runtime đủ tốt |

---

# 20. Roadmap triển khai

## Phase 0 — Preserve current closure

Trước architecture expansion:

- giữ main green;
- không mở nhiều refactor song song;
- mọi thay đổi UI phải giữ auth/security/PWA/owner contracts;
- browser evidence gate tiếp tục bắt buộc.

---

## Phase 1 — UI Foundation R1

### 1. Design tokens cleanup

**Impact:** rất cao.  
**Risk:** thấp nếu visual regression test tốt.

Deliverables:

- semantic token inventory;
- raw-color lint/contract cho surface mới;
- spacing/radius/typography scale;
- state colors;
- motion tokens.

Acceptance:

- new primitives không dùng raw color ngoài token owner;
- light/dark render;
- customer/admin render;
- reduced motion pass.

### 2. Primitive component contracts

Bắt đầu:

- Button
- Input
- Select
- Badge/StatusPill
- Dialog
- Drawer
- Toast
- EmptyState
- ErrorState
- Skeleton
- Timeline
- Progress

Acceptance:

- keyboard;
- focus;
- mobile;
- theme;
- disabled/loading;
- accessibility tests.

---

## Phase 2 — Capability + Workspace

### 3. Capability Registry R1

**Impact:** cực cao.  
**Dependency:** existing catalogue/readiness logic.

Acceptance:

- catalogue;
- product page;
- command palette;
- admin;
- CTA

đều đọc cùng capability projection.

### 4. Unified Product Workspace R1

Migrate trước 2 product:

1. Product Video.
2. SubDub.

Sau đó Image/PDF.

Acceptance:

- cùng header/state/error/loading/result pattern;
- không duplicate capability logic;
- mobile flow hoàn chỉnh.

---

## Phase 3 — Execution Truth

### 5. ExecutionRun R1

Bọc existing job thay vì rewrite executor.

Acceptance:

- stable run_id;
- owner binding;
- idempotency;
- separate execution/finance/artifact state.

### 6. ExecutionEvent R1

Bắt đầu event cho Product Video/SubDub.

Acceptance:

- Customer timeline và Admin timeline dùng cùng event source;
- progress không dựa vào timer;
- terminal state deterministic.

---

## Phase 4 — Asset Truth

### 7. Asset + Artifact R1

Acceptance:

- output có asset_id/artifact_id;
- owner check;
- byte size/hash;
- lineage;
- browser không cần provider URL.

### 8. Signed Artifact Delivery

Acceptance:

- short-lived;
- owner-scoped;
- no storage path leak;
- no provider URL as durable identity.

### 9. Integrity Sweep

Acceptance:

- detect missing/orphan/hash mismatch;
- Admin reliability view;
- không auto-delete nguy hiểm trong R1.

---

## Phase 5 — Admin + Support

### 10. Admin Object Detail R1

Migrate:

- Run;
- Asset;
- Account;
- Support Case;
- Top-up.

### 11. Support Desk R1

Case timeline + assignment + related object links.

---

## Phase 6 — Permissions + Provider Registry

### 12. Permission Registry

Map role → permission → capability.

### 13. Provider Capability Registry

Admin view:

- configured;
- health;
- proven;
- supported operations;
- last verified.

---

## Phase 7 — Contract/CI Registry

Formalize critical contracts:

- auth/session;
- wallet;
- capability truth;
- artifact delivery;
- PWA;
- Admin/Customer parity;
- provider execution;
- billing;
- asset integrity.

---

# 21. Top 10 thay đổi ROI cao nhất

## 1. Capability Registry R1

Giảm duplicate logic và UI “đoán” availability.

## 2. Unified Product Workspace

Tăng consistency cho toàn bộ AI/media/document tools.

## 3. ExecutionRun R1

Một identity/lifecycle chung cho jobs.

## 4. ExecutionEvent Ledger

Progress thật, audit tốt, Customer/Admin parity tốt.

## 5. Asset/Artifact split

Giải quyết output identity, lineage, integrity và download.

## 6. Design System primitives

Giảm CSS/DOM drift, tăng accessibility và tốc độ phát triển.

## 7. Product Video migration đầu tiên

Flow phức tạp nhất sẽ ép các abstraction mới chứng minh giá trị.

## 8. Admin Object Detail + Timeline

Giảm page CRUD rời rạc và tăng operational clarity.

## 9. Permission Registry

Cho phép mở rộng Admin/Support an toàn mà không chỉ dựa vào role lớn.

## 10. Contract→Test→CI Registry

Giữ toàn bộ kiến trúc không trượt theo thời gian.

---

# 22. Execution sequence đề xuất

Không mở 10 epic cùng lúc. Chia thành PR nhỏ:

```text
PR-01  DESIGN_TOKEN_CONTRACT_R1
PR-02  UI_PRIMITIVES_BUTTON_INPUT_STATUS_R1
PR-03  UI_PRIMITIVES_DIALOG_DRAWER_TOAST_R1
PR-04  CAPABILITY_REGISTRY_SCHEMA_R1
PR-05  CAPABILITY_PROJECTION_API_R1
PR-06  CATALOGUE_READS_CAPABILITY_R1
PR-07  COMMAND_REGISTRY_READS_CAPABILITY_R1

PR-08  EXECUTION_RUN_ENVELOPE_R1
PR-09  EXECUTION_EVENT_SCHEMA_R1
PR-10  PRODUCT_VIDEO_RUN_ADAPTER_R1
PR-11  PRODUCT_VIDEO_EVENT_TIMELINE_R1
PR-12  PRODUCT_VIDEO_UNIFIED_WORKSPACE_R1

PR-13  ASSET_SCHEMA_R1
PR-14  ARTIFACT_SCHEMA_R1
PR-15  PRODUCT_VIDEO_ARTIFACT_SEAL_R1
PR-16  ARTIFACT_DOWNLOAD_R1
PR-17  ASSET_INTEGRITY_SWEEP_R1

PR-18  SUBDUB_RUN_ADAPTER_R1
PR-19  SUBDUB_UNIFIED_WORKSPACE_R1

PR-20  ADMIN_OBJECT_DETAIL_RUN_R1
PR-21  ADMIN_OBJECT_DETAIL_ASSET_R1
PR-22  SUPPORT_CASE_TIMELINE_R1

PR-23  PERMISSION_REGISTRY_R1
PR-24  PROVIDER_CAPABILITY_REGISTRY_R1
PR-25  CONTRACT_CI_REGISTRY_R1
```

Mỗi PR:

- một authority owner;
- một migration boundary;
- contract tests;
- browser evidence nếu UI;
- không rewrite unrelated code.

---

# 23. File/module impact dự kiến

## UI foundation

```text
static/portal/portal.css
static/portal/portal-theme.css
static/portal/portal-motion.js
static/portal/portal-features.js
static/portal/portal.js
tests/*portal*contracts.py
tests/*motion*.py
```

## Capability / API

```text
copyfast_api.py
copyfast_native_read_models.py
copyfast_bridge.py
new capability registry module(s)
tests/test_*capability*.py
```

## Execution

```text
copyfast_product_video_job_bridge.py
Bot bridge/runtime adapters
new execution_run / execution_event module(s)
tests/test_*product_video*.py
tests/test_*subdub*.py
```

## Asset

```text
copyfast_api.py
copyfast_db.py
copyfast_native_read_models.py
new asset/artifact service modules
tests/test_*asset*.py
tests/test_*artifact*.py
```

## Admin

```text
admin route/render modules
shared read models
operation receipt/audit modules
tests/test_*admin*.py
```

Không nên tách `copyfast_api.py` thành nhiều module trong cùng PR với thay đổi domain lớn. Trước hết đưa abstraction vào, sau đó move route/service từng nhóm với contract giữ nguyên.

---

# 24. Acceptance criteria cấp sản phẩm

Blueprint được xem là thành công khi:

1. User nhìn cùng một status vocabulary trên dashboard, product, jobs, assets và support.
2. Customer/Admin cùng run_id/artifact_id/amount/state.
3. UI không tự suy luận capability.
4. Job progress đến từ event thật.
5. Download chỉ xuất hiện khi artifact verified/delivery-ready.
6. Asset có owner + size + checksum + storage abstraction.
7. Product Video/SubDub dùng cùng workspace skeleton.
8. Modal/drawer/menu có keyboard/focus behavior nhất quán.
9. Reduced-motion không làm mất chức năng.
10. Mobile core flow không cần desktop fallback.
11. Permission/capability quyết định action visibility và admission.
12. Canonical Bot authority vẫn re-authorize action quan trọng.
13. Critical contract có test và test được CI chạy.
14. Không cần big-bang rewrite.

---

# 25. Source links

## TOAN AAS

- Main repo: https://github.com/manhtoangreensky-wq/toan-aas-standalone
- Master tracker: https://github.com/manhtoangreensky-wq/toan-aas-standalone/issues/561
- Portal CSS: https://github.com/manhtoangreensky-wq/toan-aas-standalone/blob/main/static/portal/portal.css
- Theme tokens: https://github.com/manhtoangreensky-wq/toan-aas-standalone/blob/main/static/portal/portal-theme.css
- Motion owner: https://github.com/manhtoangreensky-wq/toan-aas-standalone/blob/main/static/portal/portal-motion.js
- Feature catalogue: https://github.com/manhtoangreensky-wq/toan-aas-standalone/blob/main/static/portal/portal-features.js
- Service worker: https://github.com/manhtoangreensky-wq/toan-aas-standalone/blob/main/static/portal/service-worker.js
- Web quality CI: https://github.com/manhtoangreensky-wq/toan-aas-standalone/blob/main/.github/workflows/webapp-quality.yml

## External references

- Radix UI: https://github.com/radix-ui/primitives
- shadcn/ui: https://github.com/shadcn-ui/ui
- Motion: https://github.com/motiondivision/motion
- Dify: https://github.com/langgenius/dify
- LibreChat: https://github.com/LibreChat-AI/LibreChat
- Immich: https://github.com/immich-app/immich
- MoneyPrinterTurbo: https://github.com/harry0703/MoneyPrinterTurbo
- Open WebUI: https://github.com/open-webui/open-webui
- Twenty: https://github.com/twentyhq/twenty
- Chatwoot: https://github.com/chatwoot/chatwoot
- Plane: https://github.com/makeplane/plane
- Open SaaS: https://github.com/wasp-lang/open-saas

---

# 26. Final direction

**TOAN AAS nên trở thành một “truth-first multi-product workspace”, không phải một collection của nhiều tool page.**

Visual system nên sạch, nhẹ, teal/cyan có nhận diện nhưng không quá decorative. Motion phải giải thích lifecycle. Customer UX phải tập trung vào mục tiêu và kết quả. Admin UX phải tập trung vào canonical object, timeline, receipt và operational truth.

Kiến trúc đích không phải “giống Dify” hay “giống Twenty”. Kiến trúc đích là:

```text
TOAN AAS authority model
+ Dify-style durable runs
+ LibreChat-style run events
+ Immich-style asset integrity
+ Open WebUI-style permission granularity
+ Twenty-style admin object views
+ Chatwoot-style support timeline
+ Plane-style command/workspace navigation
+ Radix-style accessibility behavior
+ shadcn-style component discipline
+ Motion-style lifecycle animation principles
```

nhưng được triển khai **incrementally trên Web App hiện tại**, giữ toàn bộ security/truth contracts đang đúng.
