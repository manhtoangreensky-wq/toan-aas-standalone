# R217-13 — Deferred technical register

**Status:** `DEFERRED`
**Wave:** W9
**Mục tiêu:** không bỏ sót các gap parity kỹ thuật, nhưng không trộn chúng vào wave UI/UX.

## Danh sách mở sau khi Owner giao task riêng

1. Web-to-Bot adapter và real job polling/output download cho Product Video, Image,
   Voice, Music, SubDub; artifact phải non-empty và có request/job/provider task ID.
2. Smart Multi backend: auto-detect source language/speaker, mapping 1/2/n giọng,
   idempotency, retry, audit và output video/audio/subtitle.
3. Autopost channel token bridge, publish queue thật, campaign execution và support ticket
   bridge; permission/secret gate riêng.
4. Admin cross-bridge trace, customer task report, RBAC/ABAC server enforcement và audit.
5. Manual top-up approval → ledger/Xu mutation, PayOS/manual methods; wallet safety gate,
   duplicate/idempotency/owner confirmation bắt buộc.

## Điều kiện mở

- Owner task rõ, allowed repo/path, rollback và test fixture.
- `PROVIDER_CALLS=0`, `WALLET_MUTATIONS=0`, `PRODUCTION_DATA_MUTATIONS=0` trong QA; nếu
  cần khác phải xin gate mới.
- Contract request/job/provider IDs, idempotency, admission fail-closed và audit đã viết.

## Cấm kết luận

UI shell, draft, guarded toast hoặc HTTP 200 không được ghi là real output/bridge PASS.

## Verify tối thiểu khi mở

```powershell
python -m pytest tests/test_bridge_runtime_hardening.py tests/test_browser_runtime_gate.py -q
git diff --check
```

Tên test thực tế có thể khác theo task mở; phải ghi đúng lệnh và output terminal, không
đổi trạng thái deferred chỉ vì test source xanh.
