# TOAN AAS Web App PayOS Single Source

Date: 2026-06-16

## Single Source Routes

Payment link creation:

- `/api/v1/billing/create-payment-link`

Webhook:

- `/api/v1/billing/webhook/payos`

The customer compatibility route `/api/v1/customer/payos/create-link` remains only as a wrapper. It calls the billing route and should not contain independent PayOS signing logic.

## Supported Payment Types

- `topup_xu`
- `storage_addon`

## Top-up Behavior

For `topup_xu`:

- Expected Xu = `amount // 100`.
- Webhook adds Xu only after PayOS signature and amount checks pass.
- Idempotency is controlled through `payos_processed`.

## Storage Add-on Behavior

For `storage_addon`:

- Amount is taken from server-side `STORAGE_PACKAGES`.
- Client-provided amount is ignored for package pricing.
- Webhook creates an active storage entitlement after signature and amount checks pass.

Current storage packages:

- `storage_10k`: 10,000 VND -> +50MB/month
- `storage_20k`: 20,000 VND -> +100MB/month
- `storage_50k`: 50,000 VND -> +250MB/month
- `storage_100k`: 100,000 VND -> +500MB/month

## Required PayOS ENV

- `PAYOS_CLIENT_ID`
- `PAYOS_API_KEY`
- `PAYOS_CHECKSUM_KEY`
- `PUBLIC_BASE_URL=https://app.toanaas.vn`

## Do Not Duplicate

Do not add another PayOS webhook or another signing implementation in customer pages, wallet pages, admin pages, or future modules.
