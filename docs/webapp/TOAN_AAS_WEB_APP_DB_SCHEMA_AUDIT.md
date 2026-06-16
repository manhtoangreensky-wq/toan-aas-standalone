# TOAN AAS Web App DB Schema Audit

Date: 2026-06-16

## Core Tables Seen In The Web App

User and wallet:

- `users`
- `credit_events`

Payment:

- `payos_orders`
- `payos_processed`
- `manual_orders`

Storage:

- `storage_entitlements`
- `storage_usage`
- `storage_events`

ERP/Admin:

- `erp_customers`
- `erp_projects`
- `erp_inventory`
- `erp_transactions`
- `erp_employees`
- `erp_attendance`
- `erp_sales`
- `erp_assets`
- `erp_social`
- `erp_okrs`
- `erp_purchases`
- `erp_approvals`
- `erp_production`
- `erp_workloads`
- `erp_goals`
- `erp_banners`
- `erp_chat`

Campaign/media:

- `campaigns`
- `media_assets`

## ERD Direction

Future production schema should keep the following separated:

- identity/account
- wallet balance
- billing order
- payment webhook idempotency
- storage entitlement
- usage event
- AI/render job
- provider attempt
- result asset
- admin audit event

This avoids mixing top-up, package purchase, manual review, provider job, and quota grants in one table.

## Storage Policy

Current web app policy:

- Free quota: 50MB.
- Add-on blocks:
  - 10k VND -> +50MB/month
  - 20k VND -> +100MB/month
  - 50k VND -> +250MB/month
  - 100k VND -> +500MB/month

Text notes and attached files count toward real storage usage. Temporary files do not count if they are automatically removed.

## Migration Safety

Rules:

- Do not drop production tables.
- Do not reset user, payment, wallet, entitlement, or job history.
- Add columns/tables idempotently.
- Keep payment idempotency by `payos_processed.order_code`.
