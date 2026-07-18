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
| POST | /internal/v1/admin/features/{*}/freeze | copyfast_api.py | 4411 |
| GET | /internal/v1/admin/jobs | copyfast_api.py | 4309 |
| POST | /internal/v1/admin/jobs/{*}/refund | copyfast_api.py | 4387 |
| POST | /internal/v1/admin/jobs/{*}/retry | copyfast_api.py | 4364 |
| GET | /internal/v1/admin/modules/{*} | copyfast_api.py | 4334 |
| GET | /internal/v1/admin/payments | copyfast_api.py | 4314 |
| GET | /internal/v1/admin/providers | copyfast_api.py | 4319 |
| GET | /internal/v1/admin/summary | copyfast_api.py | 4299 |
| GET | /internal/v1/admin/tickets | copyfast_api.py | 4324 |
| GET | /internal/v1/admin/users | copyfast_api.py | 4304 |
| GET | /internal/v1/assets | copyfast_api.py | 4100 |
| GET | /internal/v1/assets | copyfast_api.py | 4103 |
| GET | /internal/v1/assets/{*}/download | copyfast_api.py | 2850 |
| GET | /internal/v1/features/status | copyfast_api.py | 4199 |
| POST | /internal/v1/features/{*}/{*} | copyfast_api.py | 4241 |
| POST | /internal/v1/features/{*}/{*} | copyfast_api.py | 4262 |
| GET | /internal/v1/jobs | copyfast_api.py | 4041 |
| GET | /internal/v1/jobs | copyfast_api.py | 4044 |
| GET | /internal/v1/jobs/{*} | copyfast_api.py | 4084 |
| GET | /internal/v1/me | copyfast_auth.py | 1197 |
| GET | /internal/v1/packages | copyfast_api.py | 3937 |
| POST | /internal/v1/payments/create | copyfast_api.py | 4021 |
| GET | /internal/v1/payments/{*} | copyfast_api.py | 4031 |
| GET | /internal/v1/pricing | copyfast_api.py | 3932 |
| GET | /internal/v1/support/tickets | copyfast_api.py | 4176 |
| POST | /internal/v1/support/tickets | copyfast_api.py | 4187 |
| POST | /internal/v1/uploads | copyfast_api.py | 4158 |
| GET | /internal/v1/voice/profiles | copyfast_api.py | 4133 |
| GET | /internal/v1/wallet | copyfast_api.py | 3921 |
| GET | /internal/v1/wallet/history | copyfast_api.py | 3926 |

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
