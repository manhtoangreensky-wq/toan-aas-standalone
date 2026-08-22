# Route and action map

This maps Telegram entry points to the intended Web route family. Existing-route status uses the signed `app.py` entrypoint plus its directly included routers; unmounted legacy decorators are not treated as production routes. A dashboard navigation fallback is never counted as feature parity and remains `NEEDS_FEATURE_DISPOSITION`.

## Additive Web-native route (not a Telegram command mapping)

| Web route/action | Authority | Status |
| --- | --- | --- |
| `/api/v1/video-operations/*` (not yet a public catalogue route) | Signed Web account + private Asset Vault source | `WEB_NATIVE_DISABLED_BY_DEFAULT` — bounded JPEG poster utility; no Bot/provider/PayOS/wallet delegation and no claim that existing `/video/*` Bot companion routes render media. It stays outside the public registry until the dedicated signed workbench is implemented in the broader video navigation/UI phase. |

| Telegram command | Web route/action | Status |
| --- | --- | --- |
| /add | /admin/add | COPIED_GUARDED |
| /add | /admin/add | COPIED_GUARDED |
| /add | /admin/add | COPIED_GUARDED |
| /add | /admin/add | COPIED_GUARDED |
| /add | /admin/add | COPIED_GUARDED |
| /add | /admin/add | COPIED_GUARDED |
| /add_music | /admin/add_music | COPIED_GUARDED |
| /add_music | /admin/add_music | COPIED_GUARDED |
| /add_music | /admin/add_music | COPIED_GUARDED |
| /add_music | /admin/add_music | COPIED_GUARDED |
| /add_music | /admin/add_music | COPIED_GUARDED |
| /add_music_status | /admin/add_music_status | COPIED_GUARDED |
| /add_music_status | /admin/add_music_status | COPIED_GUARDED |
| /add_music_status | /admin/add_music_status | COPIED_GUARDED |
| /add_music_status | /admin/add_music_status | COPIED_GUARDED |
| /add_music_status | /admin/add_music_status | COPIED_GUARDED |
| /add_voice_to_video | /admin/add_voice_to_video | COPIED_GUARDED |
| /add_voice_to_video | /admin/add_voice_to_video | COPIED_GUARDED |
| /add_voice_to_video | /admin/add_voice_to_video | COPIED_GUARDED |
| /add_voice_to_video | /admin/add_voice_to_video | COPIED_GUARDED |
| /add_voice_to_video | /admin/add_voice_to_video | COPIED_GUARDED |
| /addcal | /admin/addcal | COPIED_GUARDED |
| /addcal | /admin/addcal | COPIED_GUARDED |
| /addcal | /admin/addcal | COPIED_GUARDED |
| /addcal | /admin/addcal | COPIED_GUARDED |
| /addcal | /admin/addcal | COPIED_GUARDED |
| /addlink | /admin/addlink | COPIED_GUARDED |
| /addlink | /admin/addlink | COPIED_GUARDED |
| /addlink | /admin/addlink | COPIED_GUARDED |
| /addlink | /admin/addlink | COPIED_GUARDED |
| /addlink | /admin/addlink | COPIED_GUARDED |
| /addon_pricing_status | /admin/addon_pricing_status | COPIED_GUARDED |
| /addon_pricing_status | /admin/addon_pricing_status | COPIED_GUARDED |
| /addon_pricing_status | /admin/addon_pricing_status | COPIED_GUARDED |
| /addon_pricing_status | /admin/addon_pricing_status | COPIED_GUARDED |
| /addon_pricing_status | /admin/addon_pricing_status | COPIED_GUARDED |
| /adjust_package | /admin/adjust_package | COPIED_GUARDED |
| /adjust_package | /admin/adjust_package | COPIED_GUARDED |
| /adjust_package | /admin/adjust_package | COPIED_GUARDED |
| /adjust_package | /admin/adjust_package | COPIED_GUARDED |
| /adjust_package | /admin/adjust_package | COPIED_GUARDED |
| /admin | /admin/admin | COPIED_GUARDED |
| /admin | /admin/admin | COPIED_GUARDED |
| /admin | /admin/admin | COPIED_GUARDED |
| /admin | /admin/admin | COPIED_GUARDED |
| /admin | /admin/admin | COPIED_GUARDED |
| /admin_api_roadmap | /admin/admin_api_roadmap | COPIED_GUARDED |
| /admin_api_roadmap | /admin/admin_api_roadmap | COPIED_GUARDED |
| /admin_api_roadmap | /admin/admin_api_roadmap | COPIED_GUARDED |
| /admin_api_roadmap | /admin/admin_api_roadmap | COPIED_GUARDED |
| /admin_api_roadmap | /admin/admin_api_roadmap | COPIED_GUARDED |
| /admin_dashboard | /admin/admin_dashboard | COPIED_GUARDED |
| /admin_dashboard | /admin/admin_dashboard | COPIED_GUARDED |
| /admin_dashboard | /admin/admin_dashboard | COPIED_GUARDED |
| /admin_dashboard | /admin/admin_dashboard | COPIED_GUARDED |
| /admin_dashboard | /admin/admin_dashboard | COPIED_GUARDED |
| /admin_doc_b2b | /admin/admin_doc_b2b | COPIED_GUARDED |
| /admin_doc_b2b | /admin/admin_doc_b2b | COPIED_GUARDED |
| /admin_doc_b2b | /admin/admin_doc_b2b | COPIED_GUARDED |
| /admin_doc_b2b | /admin/admin_doc_b2b | COPIED_GUARDED |
| /admin_doc_b2b | /admin/admin_doc_b2b | COPIED_GUARDED |
| /admin_doc_b2c | /admin/admin_doc_b2c | COPIED_GUARDED |
| /admin_doc_b2c | /admin/admin_doc_b2c | COPIED_GUARDED |
| /admin_doc_b2c | /admin/admin_doc_b2c | COPIED_GUARDED |
| /admin_doc_b2c | /admin/admin_doc_b2c | COPIED_GUARDED |
| /admin_doc_b2c | /admin/admin_doc_b2c | COPIED_GUARDED |
| /admin_doc_checklist | /admin/admin_doc_checklist | COPIED_GUARDED |
| /admin_doc_checklist | /admin/admin_doc_checklist | COPIED_GUARDED |
| /admin_doc_checklist | /admin/admin_doc_checklist | COPIED_GUARDED |
| /admin_doc_checklist | /admin/admin_doc_checklist | COPIED_GUARDED |
| /admin_doc_checklist | /admin/admin_doc_checklist | COPIED_GUARDED |
| /admin_doc_converter | /admin/admin_doc_converter | COPIED_GUARDED |
| /admin_doc_converter | /admin/admin_doc_converter | COPIED_GUARDED |
| /admin_doc_converter | /admin/admin_doc_converter | COPIED_GUARDED |
| /admin_doc_converter | /admin/admin_doc_converter | COPIED_GUARDED |
| /admin_doc_converter | /admin/admin_doc_converter | COPIED_GUARDED |
| /admin_doc_ip | /admin/admin_doc_ip | COPIED_GUARDED |
| /admin_doc_ip | /admin/admin_doc_ip | COPIED_GUARDED |
| /admin_doc_ip | /admin/admin_doc_ip | COPIED_GUARDED |
| /admin_doc_ip | /admin/admin_doc_ip | COPIED_GUARDED |
| /admin_doc_ip | /admin/admin_doc_ip | COPIED_GUARDED |
| /admin_doc_nda | /admin/admin_doc_nda | COPIED_GUARDED |
| /admin_doc_nda | /admin/admin_doc_nda | COPIED_GUARDED |
| /admin_doc_nda | /admin/admin_doc_nda | COPIED_GUARDED |
| /admin_doc_nda | /admin/admin_doc_nda | COPIED_GUARDED |
| /admin_doc_nda | /admin/admin_doc_nda | COPIED_GUARDED |
| /admin_doc_risk | /admin/admin_doc_risk | COPIED_GUARDED |
| /admin_doc_risk | /admin/admin_doc_risk | COPIED_GUARDED |
| /admin_doc_risk | /admin/admin_doc_risk | COPIED_GUARDED |
| /admin_doc_risk | /admin/admin_doc_risk | COPIED_GUARDED |
| /admin_doc_risk | /admin/admin_doc_risk | COPIED_GUARDED |
| /admin_doc_sources | /admin/admin_doc_sources | COPIED_GUARDED |
| /admin_doc_sources | /admin/admin_doc_sources | COPIED_GUARDED |
| /admin_doc_sources | /admin/admin_doc_sources | COPIED_GUARDED |
| /admin_doc_sources | /admin/admin_doc_sources | COPIED_GUARDED |
| /admin_doc_sources | /admin/admin_doc_sources | COPIED_GUARDED |
| /admin_doc_tax | /admin/admin_doc_tax | COPIED_GUARDED |
| /admin_doc_tax | /admin/admin_doc_tax | COPIED_GUARDED |
| /admin_doc_tax | /admin/admin_doc_tax | COPIED_GUARDED |
| /admin_doc_tax | /admin/admin_doc_tax | COPIED_GUARDED |
| /admin_doc_tax | /admin/admin_doc_tax | COPIED_GUARDED |
| /admin_docs | /admin/admin_docs | COPIED_GUARDED |
| /admin_docs | /admin/admin_docs | COPIED_GUARDED |
| /admin_docs | /admin/admin_docs | COPIED_GUARDED |
| /admin_docs | /admin/admin_docs | COPIED_GUARDED |
| /admin_docs | /admin/admin_docs | COPIED_GUARDED |
| /admin_gopy | /admin/admin_gopy | COPIED_GUARDED |
| /admin_gopy | /admin/admin_gopy | COPIED_GUARDED |
| /admin_gopy | /admin/admin_gopy | COPIED_GUARDED |
| /admin_gopy | /admin/admin_gopy | COPIED_GUARDED |
| /admin_gopy | /admin/admin_gopy | COPIED_GUARDED |
| /admin_gopy | /admin/admin_gopy | COPIED_GUARDED |
| /admin_grant_plan | /admin/admin_grant_plan | COPIED_GUARDED |
| /admin_grant_plan | /admin/admin_grant_plan | COPIED_GUARDED |
| /admin_grant_plan | /admin/admin_grant_plan | COPIED_GUARDED |
| /admin_grant_plan | /admin/admin_grant_plan | COPIED_GUARDED |
| /admin_grant_plan | /admin/admin_grant_plan | COPIED_GUARDED |
| /admin_help | /admin/admin_help | COPIED_GUARDED |
| /admin_help | /admin/admin_help | COPIED_GUARDED |
| /admin_help | /admin/admin_help | COPIED_GUARDED |
| /admin_help | /admin/admin_help | COPIED_GUARDED |
| /admin_help | /admin/admin_help | COPIED_GUARDED |
| /admin_import_affiliate_inventory | /admin/admin_import_affiliate_inventory | COPIED_GUARDED |
| /admin_import_affiliate_inventory | /admin/admin_import_affiliate_inventory | COPIED_GUARDED |
| /admin_import_affiliate_inventory | /admin/admin_import_affiliate_inventory | COPIED_GUARDED |
| /admin_import_affiliate_inventory | /admin/admin_import_affiliate_inventory | COPIED_GUARDED |
| /admin_import_affiliate_inventory | /admin/admin_import_affiliate_inventory | COPIED_GUARDED |
| /admin_import_reference_video | /admin/admin_import_reference_video | COPIED_GUARDED |
| /admin_import_reference_video | /admin/admin_import_reference_video | COPIED_GUARDED |
| /admin_import_reference_video | /admin/admin_import_reference_video | COPIED_GUARDED |
| /admin_import_reference_video | /admin/admin_import_reference_video | COPIED_GUARDED |
| /admin_import_reference_video | /admin/admin_import_reference_video | COPIED_GUARDED |
| /admin_member_help | /admin/admin_member_help | COPIED_GUARDED |
| /admin_member_help | /admin/admin_member_help | COPIED_GUARDED |
| /admin_member_help | /admin/admin_member_help | COPIED_GUARDED |
| /admin_member_help | /admin/admin_member_help | COPIED_GUARDED |
| /admin_member_help | /admin/admin_member_help | COPIED_GUARDED |
| /admin_payment_help | /admin/admin_payment_help | COPIED_GUARDED |
| /admin_payment_help | /admin/admin_payment_help | COPIED_GUARDED |
| /admin_payment_help | /admin/admin_payment_help | COPIED_GUARDED |
| /admin_payment_help | /admin/admin_payment_help | COPIED_GUARDED |
| /admin_payment_help | /admin/admin_payment_help | COPIED_GUARDED |
| /admin_plan_status | /admin/admin_plan_status | COPIED_GUARDED |
| /admin_plan_status | /admin/admin_plan_status | COPIED_GUARDED |
| /admin_plan_status | /admin/admin_plan_status | COPIED_GUARDED |
| /admin_plan_status | /admin/admin_plan_status | COPIED_GUARDED |
| /admin_plan_status | /admin/admin_plan_status | COPIED_GUARDED |
| /admin_report_month | /admin/admin_report_month | COPIED_GUARDED |
| /admin_report_month | /admin/admin_report_month | COPIED_GUARDED |
| /admin_report_month | /admin/admin_report_month | COPIED_GUARDED |
| /admin_report_month | /admin/admin_report_month | COPIED_GUARDED |
| /admin_report_month | /admin/admin_report_month | COPIED_GUARDED |
| /admin_report_year | /admin/admin_report_year | COPIED_GUARDED |
| /admin_report_year | /admin/admin_report_year | COPIED_GUARDED |
| /admin_report_year | /admin/admin_report_year | COPIED_GUARDED |
| /admin_report_year | /admin/admin_report_year | COPIED_GUARDED |
| /admin_report_year | /admin/admin_report_year | COPIED_GUARDED |
| /admin_revoke_plan | /admin/admin_revoke_plan | COPIED_GUARDED |
| /admin_revoke_plan | /admin/admin_revoke_plan | COPIED_GUARDED |
| /admin_revoke_plan | /admin/admin_revoke_plan | COPIED_GUARDED |
| /admin_revoke_plan | /admin/admin_revoke_plan | COPIED_GUARDED |
| /admin_revoke_plan | /admin/admin_revoke_plan | COPIED_GUARDED |
| /admin_tools_help | /admin/admin_tools_help | COPIED_GUARDED |
| /admin_tools_help | /admin/admin_tools_help | COPIED_GUARDED |
| /admin_tools_help | /admin/admin_tools_help | COPIED_GUARDED |
| /admin_tools_help | /admin/admin_tools_help | COPIED_GUARDED |
| /admin_tools_help | /admin/admin_tools_help | COPIED_GUARDED |
| /admin_trend_video | /admin/admin_trend_video | COPIED_GUARDED |
| /admin_trend_video | /admin/admin_trend_video | COPIED_GUARDED |
| /admin_trend_video | /admin/admin_trend_video | COPIED_GUARDED |
| /admin_trend_video | /admin/admin_trend_video | COPIED_GUARDED |
| /admin_trend_video | /admin/admin_trend_video | COPIED_GUARDED |
| /admin_whoami | /admin/admin_whoami | COPIED_GUARDED |
| /admin_whoami | /admin/admin_whoami | COPIED_GUARDED |
| /admin_whoami | /admin/admin_whoami | COPIED_GUARDED |
| /admin_whoami | /admin/admin_whoami | COPIED_GUARDED |
| /admin_whoami | /admin/admin_whoami | COPIED_GUARDED |
| /ads_policy | /legal | COPIED_GUARDED |
| /ads_policy | /legal | COPIED_GUARDED |
| /ads_policy | /legal | COPIED_GUARDED |
| /ads_policy | /legal | COPIED_GUARDED |
| /ads_policy | /legal | COPIED_GUARDED |
| /affiliate_add | /admin/affiliate_add | COPIED_GUARDED |
| /affiliate_add | /admin/affiliate_add | COPIED_GUARDED |
| /affiliate_add | /admin/affiliate_add | COPIED_GUARDED |
| /affiliate_add | /admin/affiliate_add | COPIED_GUARDED |
| /affiliate_add | /admin/affiliate_add | COPIED_GUARDED |
| /affiliate_bundle | /admin/affiliate_bundle | COPIED_GUARDED |
| /affiliate_bundle | /admin/affiliate_bundle | COPIED_GUARDED |
| /affiliate_bundle | /admin/affiliate_bundle | COPIED_GUARDED |
| /affiliate_bundle | /admin/affiliate_bundle | COPIED_GUARDED |
| /affiliate_bundle | /admin/affiliate_bundle | COPIED_GUARDED |
| /affiliate_cockpit | /admin/affiliate_cockpit | COPIED_GUARDED |
| /affiliate_cockpit | /admin/affiliate_cockpit | COPIED_GUARDED |
| /affiliate_cockpit | /admin/affiliate_cockpit | COPIED_GUARDED |
| /affiliate_cockpit | /admin/affiliate_cockpit | COPIED_GUARDED |
| /affiliate_cockpit | /admin/affiliate_cockpit | COPIED_GUARDED |
| /affiliate_decisions | /admin/affiliate_decisions | COPIED_GUARDED |
| /affiliate_decisions | /admin/affiliate_decisions | COPIED_GUARDED |
| /affiliate_decisions | /admin/affiliate_decisions | COPIED_GUARDED |

## Community Trust Center command boundary

Only the five exact public Bot commands below may open a fresh signed Web-native, read-only snapshot. No Bot identity, command/callback, pending/menu state, Bot-issued channel URL/configuration, or browser URL/query/action is transferred or replayed. The boundary creates no Bot mutation, bridge/provider/payment/job/asset/notification action or runtime claim.

| Bot command | Web target | Status | Boundary |
| --- | --- | --- | --- |
| /community | /community | WEB_NATIVE_READ_ONLY | Fresh signed server-validated snapshot; no Bot state, identity, URL/configuration or browser action is transferred. |
| /hub | /community | WEB_NATIVE_READ_ONLY | Fresh signed server-validated snapshot; no Bot state, identity, URL/configuration or browser action is transferred. |
| /kenh_chinh_thuc | /community | WEB_NATIVE_READ_ONLY | Fresh signed server-validated snapshot; no Bot state, identity, URL/configuration or browser action is transferred. |
| /official_channels | /community | WEB_NATIVE_READ_ONLY | Fresh signed server-validated snapshot; no Bot state, identity, URL/configuration or browser action is transferred. |
| /toanaas_hub | /community | WEB_NATIVE_READ_ONLY | Fresh signed server-validated snapshot; no Bot state, identity, URL/configuration or browser action is transferred. |
