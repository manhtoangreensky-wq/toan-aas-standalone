# VO-MANAGEMENT-FEEDBACK-LOCALE — thông báo quản lý hồ sơ hướng đọc

## Hiện trạng và thứ tự

Ngày23/10, source30903110482f0c15b20fc959b30796dc0c7a1490.
Đây là P1/Q0, sau Q0-VOICE-DIRECTION-CLARITY; chưa BUILD.
Không phải Voice Vault canonical hoặc task tạo âm thanh.
Tracker duy nhất của Voice UI: https://github.com/manhtoangreensky-wq/toan-aas-standalone/issues/662.
BASE thực thi: a0e19ec3792ff1dd3ed276760ef9e09b93017905, branch
webapp-r218-billing-ui-20261022; clarification local UI đã ACCEPTED.

Browser app thật với SQLite cô lập đã hoàn tất6 cấu hình:
VI/EN/ZH × (dark390, light1440). Tạo/đọc lại/ưu tiên/đổi tên/lưu trữ/khôi phục/
tìm kiếm/xóa bộ lọc đi qua API thật. Ở cả4 cấu hình EN/ZH, action
`voice-studio-filter` vẫn hiện `Đã áp dụng bộ lọc Voice Studio.`.
Source nằm trong4 nhánh read-only ở `static/portal/integration.js`:
`voice-studio-filter`, `voice-studio-filter-clear`, `voice-studio-page`,
`voice-studio-refresh` (khoảng33880–33900 tại source này).

## Contract hẹp

Allowlist tương lai: `static/portal/integration.js`, `static/portal/portal-i18n.js`,
`tests/voice-studio-feedback-locale.test.mjs`; tối đa3file, một worker.
Không đổi helper dùng chung/chữ ký hàm, payload, route, GET, offset, filter,
session/epoch, quyền, mutation hoặc backend. Không dịch tên/nội dung của khách.

Thông điệp đích được tra theo locale hiện tại, không còn thuật ngữ kỹ thuật:

| Key dưới customerVoiceStudio | VI | EN | ZH |
|---|---|---|---|
| feedback.filtered | Đã áp dụng bộ lọc. | Filters applied. | 已应用筛选条件。 |
| feedback.all | Đã hiển thị tất cả hồ sơ. | Showing all profiles. | 已显示全部档案。 |
| feedback.page | Đã tải trang hồ sơ. | Profile page loaded. | 档案页已加载。 |
| feedback.refreshed | Đã làm mới hồ sơ. | Profiles refreshed. | 档案已刷新。 |

Các validation/error và receipt của thao tác ghi phải được audit riêng; lát này
không được đổi thông báo lỗi hoặc che lỗi máy chủ để test xanh.

### Amendment trước BUILD — feedback phải đúng kết quả

Probe ngày23/10 chạy4nhánh production đã đo: filter/readState=failed vẫn báo
đã áp dụng, refresh/readState=failed vẫn báo đã làm mới; page trả `{stale:true}`
vẫn báo đã tải trang. Evidence local
`C:/Users/toann/Documents/Codex/qa/r218-voice-feedback-20261023/baseline-probe.json`.

Trong cùng4nhánh chỉ phát success toast khi hydrate trả object không stale,
`base().voiceStudioReadState === "ready"` và route vẫn đúng. Detail refresh
trảnull thì im lặng; UI failed state hiện có vẫn hiển thị lỗi theo locale.
Không thay hydrate return/schema, session/epoch fences, API hoặc error messages.
Test phải thêm ready/failed/stale/null/rejected và departed-route states;
success không được lọt sang trang khác. Không bỏ error UI để đạt locale test.

## Checklist và nghiệm thu

- [x] Tái hiện4 cấu hình EN/ZH bằng UI/app/API thật; ảnh và JSON đã lưu.
- [x] Phiếu Antigravity3.8Flash đã chạy hai lượt; lượt2 vẫn để worker patch, Codex tự kiểm.
- [x] RED5fail bắt đúng locale/false-success; test chạy handler/catalogue thật trong VM.
- [x] GREEN9/9; nguyên GET/payload/offset/session guard so với baseline.
- [x] Browser18configs, filter/clear/refresh/page,503 sau retry,recovery;51 QA profiles.
  có dữ liệu thật do QA dựng; không suy pagination từ một record.
- [x] FullNode942/942, syntax/diff/protected comparator; không provider/production.
- Acceptance evidence: `reports/audit/R218-VOICE-MANAGEMENT-FEEDBACK-QA-20261023.json`.

Verify dự kiến: `node --test tests/voice-studio-feedback-locale.test.mjs` và
`node --test tests/*.test.mjs` → fail0; browser phải không rò tiếng Việt ở EN/ZH
và còn nguyên Unicode trong tên hồ sơ.

Evidence gốc: `reports/audit/R218-VOICE-METADATA-QA-20261023.json`.
DEPLOY=NO; LIVE_PASS=NOT_TESTED; mọi capability/provider/audio giữ nguyên.
