# Private Core Bridge static contract

Status: **BOT_BRIDGE_SOURCE_MISSING**. Web outbound calls matched: `0/28`. The comparison parses source only; it does not contact the Bot, Railway, Telegram, PayOS, a provider, or read an environment value.

- Bot bridge source present: `False`
- Bot router mount observed in current checkout: `False`
- Requested baseline bridge source: `missing` (`present=False`)
- Unmatched Web calls: `28`
- Unresolved dynamic Web calls: `0`

## Matched method/path shapes

| Method | Web request | Bot route candidate | Web source |
| --- | --- | --- | --- |
| None |  |  |  |

## Gaps requiring a contract change

| Method | Web request | Web source | Line |
| --- | --- | --- | --- |
| POST | /internal/v1/admin/features/{*}/freeze | copyfast_api.py | 3109 |
| GET | /internal/v1/admin/jobs | copyfast_api.py | 3007 |
| POST | /internal/v1/admin/jobs/{*}/refund | copyfast_api.py | 3085 |
| POST | /internal/v1/admin/jobs/{*}/retry | copyfast_api.py | 3062 |
| GET | /internal/v1/admin/modules/{*} | copyfast_api.py | 3032 |
| GET | /internal/v1/admin/payments | copyfast_api.py | 3012 |
| GET | /internal/v1/admin/providers | copyfast_api.py | 3017 |
| GET | /internal/v1/admin/summary | copyfast_api.py | 2997 |
| GET | /internal/v1/admin/tickets | copyfast_api.py | 3022 |
| GET | /internal/v1/admin/users | copyfast_api.py | 3002 |
| GET | /internal/v1/assets | copyfast_api.py | 2817 |
| GET | /internal/v1/assets/{*}/download | copyfast_api.py | 2092 |
| GET | /internal/v1/features/status | copyfast_api.py | 2897 |
| POST | /internal/v1/features/{*}/{*} | copyfast_api.py | 2939 |
| POST | /internal/v1/features/{*}/{*} | copyfast_api.py | 2960 |
| GET | /internal/v1/jobs | copyfast_api.py | 2806 |
| GET | /internal/v1/jobs/{*} | copyfast_api.py | 2812 |
| GET | /internal/v1/me | copyfast_auth.py | 708 |
| GET | /internal/v1/packages | copyfast_api.py | 2707 |
| POST | /internal/v1/payments/create | copyfast_api.py | 2791 |
| GET | /internal/v1/payments/{*} | copyfast_api.py | 2801 |
| GET | /internal/v1/pricing | copyfast_api.py | 2702 |
| GET | /internal/v1/support/tickets | copyfast_api.py | 2874 |
| POST | /internal/v1/support/tickets | copyfast_api.py | 2885 |
| POST | /internal/v1/uploads | copyfast_api.py | 2856 |
| GET | /internal/v1/voice/profiles | copyfast_api.py | 2831 |
| GET | /internal/v1/wallet | copyfast_api.py | 2691 |
| GET | /internal/v1/wallet/history | copyfast_api.py | 2696 |

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
