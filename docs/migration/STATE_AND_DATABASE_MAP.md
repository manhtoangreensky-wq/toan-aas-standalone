# State and database authority map

| State | Canonical authority | Web role |
| --- | --- | --- |
| Telegram identity / role | Bot | Guarded unavailable: no verified private bridge source was observed in this static audit. A separately verified bridge release is required before canonical Bot data may be read. |
| Xu ledger / refunds | Bot | Guarded unavailable: no verified private bridge source was observed in this static audit. A separately verified bridge release is required before canonical Bot data may be read. |
| PayOS order / webhook | Bot | Guarded unavailable: no verified private bridge source was observed in this static audit. A separately verified bridge release is required before canonical Bot data may be read. |
| Jobs / outputs | Bot + workers | Guarded unavailable: no verified private bridge source was observed in this static audit. A separately verified bridge release is required before canonical Bot data may be read. |
| Web session / CSRF | Web App | Local additive session database only |

| Table set | Count | Examples |
| --- | --- | --- |
| Bot | 554 | _update, _utils, _valid_url, a, above, acodec, active, affiliate_links, again, all, an, ang, ann, annot, any, api_debug_events, application, applies, are, arr, associated, attached, attributes, audit_logs, available, b2b_projects, belongs, birthday, birthday_gifts, birthday_review_requests |
| Web | 224 | a, above, affiliate_links, any, b2b_projects, campaigns, clears, credit_events, erp_approvals, erp_assets, erp_attendance, erp_banners, erp_chat, erp_customers, erp_employees, erp_goals, erp_inventory, erp_okrs, erp_production, erp_projects, erp_purchases, erp_sales, erp_social, erp_transactions, erp_workloads, family, feedback, manual_orders, manual_performance_events, media_assets |

Bot Workboard/Task callbacks are distinct from the Web Workboard: the Browser must never replay a Bot production job/task identifier, stage/status value, handoff prompt or Telegram-admin context. See `WORKBOARD_TASK_CALLBACK_CONTRACT.md`.

Bot Creative callbacks are distinct from the Web Creative Studio: the Browser must never replay a Bot creative-variant identifier, selected state, production-job update, handoff instruction or Telegram-admin context. See `CREATIVE_VARIANT_CALLBACK_CONTRACT.md`.

## Web-native Finance Planning state

`/admin/finance/planning` is a separately signed Web-local Finance Planning workspace, protected by `WEBAPP_ADMIN_ERP_ENABLED` and `WEBAPP_FINANCE_PLANNING_ENABLED`. Its additive Web-owned tables are `web_finance_planning_budgets`, `web_finance_planning_costs` and `web_finance_planning_events`; they provide budget/cost planning, revision and audit evidence only. It never reads, mirrors or mutates Bot finance events, Telegram identity/role, Xu/wallet, PayOS, provider, refund, revenue, tax, export or canonical Bot-admin state.
