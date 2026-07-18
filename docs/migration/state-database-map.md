# State and database authority map

The bot remains the canonical writer for identity, wallet, PayOS, jobs, and provider state. The Web App consumes typed bridge contracts and must not duplicate those writes.

| Table set | Count | Examples |
| --- | --- | --- |
| Bot discovered | 97 | affiliate_links, api_debug_events, audit_logs, birthday, birthday_gifts, birthday_review_requests, campaigns, channel_profiles, content_calendar, content_performance_events, creative_variants, credit_events, feature_flags, feedback, finance_compliance_notes, finance_expense_events, finance_revenue_events, finance_usage_events, gift_assignments, gift_beta_requests, gift_redemptions, growth_recommendations, internal_documents, launch_bonus_redemptions, leads, local_worker_jobs, long_video_projects, long_video_scenes, manual_performance_events, media_factory_jobs |
| Web discovered | 192 | a, above, affiliate_links, any, b2b_projects, campaigns, credit_events, erp_approvals, erp_assets, erp_attendance, erp_banners, erp_chat, erp_customers, erp_employees, erp_goals, erp_inventory, erp_okrs, erp_production, erp_projects, erp_purchases, erp_sales, erp_social, erp_transactions, erp_workloads, feedback, manual_orders, manual_performance_events, media_assets, one, only |
| Bot-only (bridge/read contract required) | 86 | api_debug_events, audit_logs, birthday, birthday_gifts, birthday_review_requests, channel_profiles, content_calendar, content_performance_events, creative_variants, feature_flags, finance_compliance_notes, finance_expense_events, finance_revenue_events, finance_usage_events, gift_assignments, gift_beta_requests, gift_redemptions, growth_recommendations, internal_documents, launch_bonus_redemptions, leads, local_worker_jobs, long_video_projects, long_video_scenes, media_factory_jobs, member_tier_overrides, member_tier_rewards, memory_events, memory_notes, memory_plans |

## Additive Web-native Video Poster state

| Table | Owner | Purpose | Explicitly not authoritative for |
| --- | --- | --- | --- |
| `web_video_operations` | Signed Web account | One bounded private poster request, sealed output metadata and exact lifecycle | Bot jobs, provider execution, wallet/Xu, PayOS, Telegram identity or Asset Vault source ownership |
| `web_video_operation_attempts` | Web operation | In-request execution attempt/fence audit; future worker seam only | Durable worker lease, automatic retry, provider job or billing attempt |
| `web_video_operation_events` | Web operation | Ordered lifecycle evidence | Bot audit log, payment ledger, webhook, notification or delivery receipt |

These are additive schema records. They do not migrate, synchronize, infer or
overwrite any Bot table. The Bot remains the canonical writer for its own
identity, wallet, PayOS, jobs and provider state.

No destructive migration or schema synchronization is authorized by this inventory.

## Additive Web-native Frame Video state

| Table | Owner | Purpose | Explicitly not authoritative for |
| --- | --- | --- | --- |
| `web_frame_video_operations` | Signed Web account | One immutable ordered image-sequence MP4 receipt and lifecycle | Bot jobs, provider execution, wallet/Xu, PayOS, Telegram identity or Asset Vault source ownership |
| `web_frame_video_operation_sources` | Frame Video operation | Ordered source snapshot (Asset Vault ID/digest/size/MIME only) | Source path/URL, generic Asset Vault metadata, Bot upload or provider input |
| `web_frame_video_operation_attempts` | Web operation | In-request fence evidence; future worker seam only | Durable worker lease, automatic retry, provider job or billing attempt |
| `web_frame_video_operation_events` | Web operation | Ordered lifecycle evidence | Bot audit log, payment ledger, webhook, notification or delivery receipt |

Frame Video remains additive and Web-local. It never synchronizes, mutates or
claims authority over any Bot identity/wallet/PayOS/provider/job table.

## Additive Web-native Video Finishing state

| Table | Owner | Purpose | Explicitly not authoritative for |
| --- | --- | --- | --- |
| `web_video_transform_operations` | Signed Web account | One immutable Asset Vault source snapshot, closed transform specification and sealed H.264/AAC-or-muted MP4 receipt | Bot jobs, provider execution, wallet/Xu, PayOS, Telegram identity or arbitrary FFmpeg arguments |
| `web_video_transform_operation_attempts` | Web operation | In-request execution/fence evidence; future worker seam only | Durable worker lease, automatic retry, provider job or billing attempt |
| `web_video_transform_operation_events` | Web operation | Ordered lifecycle evidence | Bot audit log, payment ledger, webhook, notification or delivery receipt |

Video Finishing is additive and Web-local. It stores no source/output path,
URL, raw filter graph, Bot/provider handle, wallet/Xu or PayOS state.
