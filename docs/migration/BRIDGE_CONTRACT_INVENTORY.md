# Private Core Bridge static contract

Status: **STATIC_CONTRACT_MATCHED**. Web outbound calls matched: `28/28`. The comparison parses source only; it does not contact the Bot, Railway, Telegram, PayOS, a provider, or read an environment value.

- Bot bridge source present: `True`
- Bot router mount observed in current checkout: `True`
- Requested baseline bridge source: `missing` (`present=False`)
- Unmatched Web calls: `0`
- Unresolved dynamic Web calls: `0`

## Matched method/path shapes

| Method | Web request | Bot route candidate | Web source |
| --- | --- | --- | --- |
| POST | /internal/v1/admin/features/{*}/freeze | /internal/v1/admin/features/{feature}/freeze | copyfast_api.py |
| GET | /internal/v1/admin/jobs | /internal/v1/admin/jobs | copyfast_api.py |
| POST | /internal/v1/admin/jobs/{*}/refund | /internal/v1/admin/jobs/{job_id}/refund | copyfast_api.py |
| POST | /internal/v1/admin/jobs/{*}/retry | /internal/v1/admin/jobs/{job_id}/retry | copyfast_api.py |
| GET | /internal/v1/admin/modules/{*} | /internal/v1/admin/modules/{module} | copyfast_api.py |
| GET | /internal/v1/admin/payments | /internal/v1/admin/payments | copyfast_api.py |
| GET | /internal/v1/admin/providers | /internal/v1/admin/providers | copyfast_api.py |
| GET | /internal/v1/admin/summary | /internal/v1/admin/summary | copyfast_api.py |
| GET | /internal/v1/admin/tickets | /internal/v1/admin/tickets | copyfast_api.py |
| GET | /internal/v1/admin/users | /internal/v1/admin/users | copyfast_api.py |
| GET | /internal/v1/assets | /internal/v1/assets | copyfast_api.py |
| GET | /internal/v1/assets/{*}/download | /internal/v1/assets/{asset_id}/download | copyfast_api.py |
| GET | /internal/v1/features/status | /internal/v1/features/status | copyfast_api.py |
| POST | /internal/v1/features/{*}/{*} | /internal/v1/features/{feature}/confirm, /internal/v1/features/{feature}/draft, /internal/v1/features/{feature}/estimate | copyfast_api.py |
| POST | /internal/v1/features/{*}/{*} | /internal/v1/features/{feature}/confirm, /internal/v1/features/{feature}/draft, /internal/v1/features/{feature}/estimate | copyfast_api.py |
| GET | /internal/v1/jobs | /internal/v1/jobs | copyfast_api.py |
| GET | /internal/v1/jobs/{*} | /internal/v1/jobs/{job_id} | copyfast_api.py |
| GET | /internal/v1/me | /internal/v1/me | copyfast_auth.py |
| GET | /internal/v1/packages | /internal/v1/packages | copyfast_api.py |
| POST | /internal/v1/payments/create | /internal/v1/payments/create | copyfast_api.py |
| GET | /internal/v1/payments/{*} | /internal/v1/payments/{payment_id} | copyfast_api.py |
| GET | /internal/v1/pricing | /internal/v1/pricing | copyfast_api.py |
| GET | /internal/v1/support/tickets | /internal/v1/support/tickets | copyfast_api.py |
| POST | /internal/v1/support/tickets | /internal/v1/support/tickets | copyfast_api.py |
| POST | /internal/v1/uploads | /internal/v1/uploads | copyfast_api.py |
| GET | /internal/v1/voice/profiles | /internal/v1/voice/profiles | copyfast_api.py |
| GET | /internal/v1/wallet | /internal/v1/wallet | copyfast_api.py |
| GET | /internal/v1/wallet/history | /internal/v1/wallet/history | copyfast_api.py |

## Gaps requiring a contract change

| Method | Web request | Web source | Line |
| --- | --- | --- | --- |
| None |  |  |  |

## Telegram one-time identity callback

Static status: **STATIC_CALLBACK_CONTRACT_PRESENT**. Expected Web receiver: `/api/v1/auth/internal/telegram-link/confirm`. The Bot→Web callback uses separate bearer/HMAC credentials and is not part of the Web→Bot core bridge credential.

| Check | Bot | Web |
| --- | --- | --- |
| Deep link / fallback | True | True |
| Callback sender / receiver | True | True |
| HMAC authorization | True | True |
| HMAC material shape | True | True |
| Raw browser ID rejected | n/a | True |

A matched path does not authorize a feature. Bearer/HMAC, session ownership, schema, idempotency, provider readiness, payment policy, job validation and delivery safety must pass independently.
