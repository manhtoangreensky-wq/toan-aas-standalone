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
| POST | /internal/v1/admin/features/{*}/freeze | copyfast_api.py | 3091 |
| GET | /internal/v1/admin/jobs | copyfast_api.py | 2989 |
| POST | /internal/v1/admin/jobs/{*}/refund | copyfast_api.py | 3067 |
| POST | /internal/v1/admin/jobs/{*}/retry | copyfast_api.py | 3044 |
| GET | /internal/v1/admin/modules/{*} | copyfast_api.py | 3014 |
| GET | /internal/v1/admin/payments | copyfast_api.py | 2994 |
| GET | /internal/v1/admin/providers | copyfast_api.py | 2999 |
| GET | /internal/v1/admin/summary | copyfast_api.py | 2979 |
| GET | /internal/v1/admin/tickets | copyfast_api.py | 3004 |
| GET | /internal/v1/admin/users | copyfast_api.py | 2984 |
| GET | /internal/v1/assets | copyfast_api.py | 2799 |
| GET | /internal/v1/assets/{*}/download | copyfast_api.py | 2074 |
| GET | /internal/v1/features/status | copyfast_api.py | 2879 |
| POST | /internal/v1/features/{*}/{*} | copyfast_api.py | 2921 |
| POST | /internal/v1/features/{*}/{*} | copyfast_api.py | 2942 |
| GET | /internal/v1/jobs | copyfast_api.py | 2788 |
| GET | /internal/v1/jobs/{*} | copyfast_api.py | 2794 |
| GET | /internal/v1/me | copyfast_auth.py | 708 |
| GET | /internal/v1/packages | copyfast_api.py | 2689 |
| POST | /internal/v1/payments/create | copyfast_api.py | 2773 |
| GET | /internal/v1/payments/{*} | copyfast_api.py | 2783 |
| GET | /internal/v1/pricing | copyfast_api.py | 2684 |
| GET | /internal/v1/support/tickets | copyfast_api.py | 2856 |
| POST | /internal/v1/support/tickets | copyfast_api.py | 2867 |
| POST | /internal/v1/uploads | copyfast_api.py | 2838 |
| GET | /internal/v1/voice/profiles | copyfast_api.py | 2813 |
| GET | /internal/v1/wallet | copyfast_api.py | 2673 |
| GET | /internal/v1/wallet/history | copyfast_api.py | 2678 |

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
