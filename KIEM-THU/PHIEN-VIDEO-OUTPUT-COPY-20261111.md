# Phiên kiểm thử — ngôn ngữ nội dung kế hoạch máy chủ

SESSION_ID=VIDEO-OUTPUT-COPY-20261111; Issue #689.
BASE_SHA=1b76f75d952fc5457458acc9030501139c6e0984.
HEAD_SHA=commit chứa phiên này; receipt CI ghi mốc cuối.

| Ca | Bằng chứng đạt |
|---|---|
| VOC-MAP | 134 phrase ID × VI/EN/ZH, placeholder định danh/số lượng không đổi |
| VOC-PURE | 1.392 tổ hợp, 36.000 kiểm chữ; ID/cấu trúc/timing/customer/determinism giữ |
| VOC-INPUT | Literal {p0}/{p1} của khách không bị xử lý lại; unknown Image language giữ raw, copy fallback VI |
| VOC-SCHEMA | Reference vẫn vi/en, không thêm zh; lựa chọn giả vẫn bị từ chối |
| VOC-API | 6 test ownership/CSRF/transient/recompute/idempotency hiện có đạt |
| VOC-NATIVE | 12 view, 6 actual UI flows, 6 plan/18 scene; phản hồi và đọc lại khớp nội dung ngôn ngữ đã chọn |
| VOC-SAFETY | 0 egress/provider/ví/production/.env/media read; source binding giữ, 46 Job process → 0 |
| VOC-SOURCE | Hai hàm/một import + dữ liệu thuần; 16 protected paths không đổi |
| VOC-DELIVERY | Chờ CI/merge/deploy/runtime/hashes/assets receipt |

TESTER_PROJECT_STATUS=READY; LOCAL_ACCEPTANCE=PASS; PUSH_GATE=READY sau provenance.
Không tạo tracker/bảng/thẻ trùng; sử dụng Issue #689 và mẫu/nhãn hiện có.
Không coi nội dung cũ, detail-page labels, thiết bị hay provider LIVE đã đạt.
