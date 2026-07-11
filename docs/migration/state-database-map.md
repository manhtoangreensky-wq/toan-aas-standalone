# State and database authority map

The bot remains the canonical writer for identity, wallet, PayOS, jobs, and provider state. The Web App consumes typed bridge contracts and must not duplicate those writes.

| Table set | Count | Examples |
| --- | --- | --- |
| Bot discovered | 97 | affiliate_links, api_debug_events, audit_logs, birthday, birthday_gifts, birthday_review_requests, campaigns, channel_profiles, content_calendar, content_performance_events, creative_variants, credit_events, feature_flags, feedback, finance_compliance_notes, finance_expense_events, finance_revenue_events, finance_usage_events, gift_assignments, gift_beta_requests, gift_redemptions, growth_recommendations, internal_documents, launch_bonus_redemptions, leads, local_worker_jobs, long_video_projects, long_video_scenes, manual_performance_events, media_factory_jobs |
| Web discovered | 43 | affiliate_links, any, b2b_projects, campaigns, credit_events, erp_approvals, erp_assets, erp_attendance, erp_banners, erp_chat, erp_customers, erp_employees, erp_goals, erp_inventory, erp_okrs, erp_production, erp_projects, erp_purchases, erp_sales, erp_social, erp_transactions, erp_workloads, feedback, manual_orders, manual_performance_events, media_assets, only, payos_orders, payos_processed, storage_entitlements |
| Bot-only (bridge/read contract required) | 86 | api_debug_events, audit_logs, birthday, birthday_gifts, birthday_review_requests, channel_profiles, content_calendar, content_performance_events, creative_variants, feature_flags, finance_compliance_notes, finance_expense_events, finance_revenue_events, finance_usage_events, gift_assignments, gift_beta_requests, gift_redemptions, growth_recommendations, internal_documents, launch_bonus_redemptions, leads, local_worker_jobs, long_video_projects, long_video_scenes, media_factory_jobs, member_tier_overrides, member_tier_rewards, memory_events, memory_notes, memory_plans |

No destructive migration or schema synchronization is authorized by this inventory.
