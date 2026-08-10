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
| POST | /internal/v1/admin/features/{*}/freeze | copyfast_api.py | 4546 |
| GET | /internal/v1/admin/jobs | copyfast_api.py | 4430 |
| POST | /internal/v1/admin/jobs/{*}/refund | copyfast_api.py | 4522 |
| POST | /internal/v1/admin/jobs/{*}/retry | copyfast_api.py | 4499 |
| GET | /internal/v1/admin/modules/{*} | copyfast_api.py | 4469 |
| GET | /internal/v1/admin/payments | copyfast_api.py | 4435 |
| GET | /internal/v1/admin/providers | copyfast_api.py | 4440 |
| GET | /internal/v1/admin/summary | copyfast_api.py | 4420 |
| GET | /internal/v1/admin/tickets | copyfast_api.py | 4445 |
| GET | /internal/v1/admin/users | copyfast_api.py | 4425 |
| GET | /internal/v1/assets | copyfast_api.py | 4221 |
| GET | /internal/v1/assets | copyfast_api.py | 4224 |
| GET | /internal/v1/assets/{*}/download | copyfast_api.py | 2957 |
| GET | /internal/v1/features/status | copyfast_api.py | 4320 |
| POST | /internal/v1/features/{*}/{*} | copyfast_api.py | 4362 |
| POST | /internal/v1/features/{*}/{*} | copyfast_api.py | 4383 |
| GET | /internal/v1/jobs | copyfast_api.py | 4162 |
| GET | /internal/v1/jobs | copyfast_api.py | 4165 |
| GET | /internal/v1/jobs/{*} | copyfast_api.py | 4205 |
| GET | /internal/v1/me | copyfast_auth.py | 1287 |
| GET | /internal/v1/packages | copyfast_api.py | 4058 |
| POST | /internal/v1/payments/create | copyfast_api.py | 4142 |
| GET | /internal/v1/payments/{*} | copyfast_api.py | 4152 |
| GET | /internal/v1/pricing | copyfast_api.py | 4053 |
| GET | /internal/v1/support/tickets | copyfast_api.py | 4297 |
| POST | /internal/v1/support/tickets | copyfast_api.py | 4308 |
| POST | /internal/v1/uploads | copyfast_api.py | 4279 |
| GET | /internal/v1/voice/profiles | copyfast_api.py | 4254 |
| GET | /internal/v1/wallet | copyfast_api.py | 4042 |
| GET | /internal/v1/wallet/history | copyfast_api.py | 4047 |

## Telegram one-time identity callback

Static status: **CALLBACK_CONTRACT_GAPS_FOUND**. Expected Web receiver: `/api/v1/auth/internal/telegram-link/confirm`. Because no verified private bridge source was observed, this static audit cannot claim the Bot-to-Web callback uses any credential or route.

| Check | Bot | Web |
| --- | --- | --- |
| Deep link / fallback | False | False |
| Callback sender / receiver | False | True |
| HMAC authorization | False | True |
| HMAC material shape | False | True |
| Raw browser ID rejected | n/a | True |

A matched path does not authorize a feature. Bearer/HMAC, session ownership, schema, idempotency, provider readiness, payment policy, job validation and delivery safety must pass independently.
