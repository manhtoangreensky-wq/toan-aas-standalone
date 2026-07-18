# State and database authority map

| State | Canonical authority | Web role |
| --- | --- | --- |
| Telegram identity / role | Bot | Read via private bridge after account link |
| Xu ledger / refunds | Bot | Read-only; no direct credit/debit |
| PayOS order / webhook | Bot | Create/status only through canonical bridge when verified |
| Jobs / outputs | Bot + workers | Read/status via bridge, signed delivery only |
| Web session / CSRF | Web App | Local additive session database only |

| Table set | Count | Examples |
| --- | --- | --- |
| Bot | 97 | affiliate_links, api_debug_events, audit_logs, birthday, birthday_gifts, birthday_review_requests, campaigns, channel_profiles, content_calendar, content_performance_events, creative_variants, credit_events, feature_flags, feedback, finance_compliance_notes, finance_expense_events, finance_revenue_events, finance_usage_events, gift_assignments, gift_beta_requests, gift_redemptions, growth_recommendations, internal_documents, launch_bonus_redemptions, leads, local_worker_jobs, long_video_projects, long_video_scenes, manual_performance_events, media_factory_jobs |
| Web | 192 | a, above, affiliate_links, any, b2b_projects, campaigns, credit_events, erp_approvals, erp_assets, erp_attendance, erp_banners, erp_chat, erp_customers, erp_employees, erp_goals, erp_inventory, erp_okrs, erp_production, erp_projects, erp_purchases, erp_sales, erp_social, erp_transactions, erp_workloads, feedback, manual_orders, manual_performance_events, media_assets, one, only |
