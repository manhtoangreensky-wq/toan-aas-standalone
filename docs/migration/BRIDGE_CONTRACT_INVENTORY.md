# Private Core Bridge static contract

Status: **BOT_BRIDGE_SOURCE_MISSING**. Web outbound calls matched: `0/30`. The comparison parses source only; it does not contact the Bot, Railway, Telegram, PayOS, a provider, or read an environment value.

- Bot bridge source present: `False`
- Bot router mount observed in current checkout: `False`
- Requested baseline bridge source: `missing` (`present=False`)
- Unmatched Web calls: `30`
- Unresolved dynamic Web calls: `0`

## Matched method/path shapes

| Method | Web request | Bot route candidate | Web source |
| --- | --- | --- | --- |
| None |  |  |  |

## Gaps requiring a contract change

| Method | Web request | Web source | Line |
| --- | --- | --- | --- |
| POST | /internal/v1/admin/features/{*}/freeze | copyfast_api.py | 4447 |
| GET | /internal/v1/admin/jobs | copyfast_api.py | 4345 |
| POST | /internal/v1/admin/jobs/{*}/refund | copyfast_api.py | 4423 |
| POST | /internal/v1/admin/jobs/{*}/retry | copyfast_api.py | 4400 |
| GET | /internal/v1/admin/modules/{*} | copyfast_api.py | 4370 |
| GET | /internal/v1/admin/payments | copyfast_api.py | 4350 |
| GET | /internal/v1/admin/providers | copyfast_api.py | 4355 |
| GET | /internal/v1/admin/summary | copyfast_api.py | 4335 |
| GET | /internal/v1/admin/tickets | copyfast_api.py | 4360 |
| GET | /internal/v1/admin/users | copyfast_api.py | 4340 |
| GET | /internal/v1/assets | copyfast_api.py | 4136 |
| GET | /internal/v1/assets | copyfast_api.py | 4139 |
| GET | /internal/v1/assets/{*}/download | copyfast_api.py | 2886 |
| GET | /internal/v1/features/status | copyfast_api.py | 4235 |
| POST | /internal/v1/features/{*}/{*} | copyfast_api.py | 4277 |
| POST | /internal/v1/features/{*}/{*} | copyfast_api.py | 4298 |
| GET | /internal/v1/jobs | copyfast_api.py | 4077 |
| GET | /internal/v1/jobs | copyfast_api.py | 4080 |
| GET | /internal/v1/jobs/{*} | copyfast_api.py | 4120 |
| GET | /internal/v1/me | copyfast_auth.py | 1197 |
| GET | /internal/v1/packages | copyfast_api.py | 3973 |
| POST | /internal/v1/payments/create | copyfast_api.py | 4057 |
| GET | /internal/v1/payments/{*} | copyfast_api.py | 4067 |
| GET | /internal/v1/pricing | copyfast_api.py | 3968 |
| GET | /internal/v1/support/tickets | copyfast_api.py | 4212 |
| POST | /internal/v1/support/tickets | copyfast_api.py | 4223 |
| POST | /internal/v1/uploads | copyfast_api.py | 4194 |
| GET | /internal/v1/voice/profiles | copyfast_api.py | 4169 |
| GET | /internal/v1/wallet | copyfast_api.py | 3957 |
| GET | /internal/v1/wallet/history | copyfast_api.py | 3962 |

## Telegram one-time identity callback

Static status: **CALLBACK_CONTRACT_GAPS_FOUND**. Expected Web receiver: `/api/v1/auth/internal/telegram-link/confirm`. The Bot→Web callback uses separate bearer/HMAC credentials and is not part of the Web→Bot core bridge credential.

| Check | Bot | Web |
| --- | --- | --- |
| Deep link / fallback | False | False |
| Callback sender / receiver | False | True |
| HMAC authorization | False | True |
| HMAC material shape | False | True |
| Raw browser ID rejected | n/a | True |

A matched path does not authorize a feature. Bearer/HMAC, session ownership, schema, idempotency, provider readiness, payment policy, job validation and delivery safety must pass independently.
