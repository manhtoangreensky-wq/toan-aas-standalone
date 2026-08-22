# Admin ERP map

## Authority model

Admin navigation is an ERP information architecture, not a browser-issued permission. All server write actions require a signed session, CSRF, confirmation, permission check, idempotency where applicable, optimistic revision where applicable, and an audit event.

| Authority domain | Server authorizes | May do | Must not do |
| --- | --- | --- | --- |
| Canonical Bot admin | Guarded unavailable: no verified private bridge source was observed in this static audit. A separately verified bridge release is required before canonical Bot data may be read. | Guarded unavailable: no verified private bridge source was observed in this static audit. A separately verified bridge release is required before canonical Bot data may be read. | Accept a browser `admin_id`, duplicate wallet/PayOS state, call a provider from the browser, or create a second webhook/ledger. |
| Web Support Desk | Signed server-side staff role | Operate owner-scoped Web support cases, triage and review handoffs. | Become canonical Bot admin or perform wallet/payment/provider actions without a canonical bridge contract. |
| Web CRM manager | Signed server-side local admin role | Read redacted, Web-owned Partner & Lead CRM pipeline records. | Read another account's private content, impersonate a canonical admin, or mutate Bot canonical data. |

Bot Support/Ticket/Feedback callbacks are separate from the Web Support Desk: the eleven exact Support/Ticket entry literals plus nine Feedback literals are finite navigation-only exceptions that may only open new signed `/support` or `/tickets` navigation. There is no category preselection, Bot ticket fetch, or case creation from the Bot entry. The Browser must never replay a Bot ticket/lead/attachment identifier, feedback category, pending input, admin-preview or Telegram delivery state. The entry exceptions transfer no callback/category/state; see `SUPPORT_TICKET_CALLBACK_CONTRACT.md` and `FEEDBACK_MENU_CALLBACK_CONTRACT.md`.

Bot Workboard/Task callbacks are separate from the Web Workboard: the Browser must never replay a Bot production job/task identifier, stage/status value, handoff prompt or Telegram-admin context. See `WORKBOARD_TASK_CALLBACK_CONTRACT.md`.

Bot Creative callbacks are separate from the Web Creative Studio: the Browser must never replay a Bot creative-variant identifier, selected state, production-job update, handoff instruction or Telegram-admin context. See `CREATIVE_VARIANT_CALLBACK_CONTRACT.md`.

`WEBAPP_ADMIN_ERP_ENABLED` is the umbrella navigation gate. `WEBAPP_CONTENT_HANDOFF_ENABLED` and `WEBAPP_PARTNER_CRM_ENABLED` gate their Web-native modules. These flags do not create authority; the server still checks the signed role on every request.

The following is a Bot command compatibility map. A target is a signed guarded Web surface or a candidate canonical projection that remains guarded-unavailable until a separately verified bridge release; it is never proof that a browser may execute the Bot command directly.

| Bot command | Handler | Compatibility target |
| --- | --- | --- |
| /add | cmd_admin_add | /admin/add |
| /add | cmd_admin_add | /admin/add |
| /add | cmd_admin_add | /admin/add |
| /add | cmd_admin_add | /admin/add |
| /add | cmd_admin_add | /admin/add |
| /add | cmd_admin_add | /admin/add |
| /add_music | cmd_add_music | /admin/add_music |
| /add_music | cmd_add_music | /admin/add_music |
| /add_music | cmd_add_music | /admin/add_music |
| /add_music | cmd_add_music | /admin/add_music |
| /add_music | cmd_add_music | /admin/add_music |
| /add_music_status | cmd_add_music_status | /admin/add_music_status |
| /add_music_status | cmd_add_music_status | /admin/add_music_status |
| /add_music_status | cmd_add_music_status | /admin/add_music_status |
| /add_music_status | cmd_add_music_status | /admin/add_music_status |
| /add_music_status | cmd_add_music_status | /admin/add_music_status |
| /add_voice_to_video | cmd_add_voice_to_video | /admin/add_voice_to_video |
| /add_voice_to_video | cmd_add_voice_to_video | /admin/add_voice_to_video |
| /add_voice_to_video | cmd_add_voice_to_video | /admin/add_voice_to_video |
| /add_voice_to_video | cmd_add_voice_to_video | /admin/add_voice_to_video |
| /add_voice_to_video | cmd_add_voice_to_video | /admin/add_voice_to_video |
| /addcal | admin_internal_command | /admin/addcal |
| /addcal | admin_internal_command | /admin/addcal |
| /addcal | admin_internal_command | /admin/addcal |
| /addcal | admin_internal_command | /admin/addcal |
| /addcal | admin_internal_command | /admin/addcal |
| /addlink | admin_internal_command | /admin/addlink |
| /addlink | admin_internal_command | /admin/addlink |
| /addlink | admin_internal_command | /admin/addlink |
| /addlink | admin_internal_command | /admin/addlink |
| /addlink | admin_internal_command | /admin/addlink |
| /addon_pricing_status | cmd_addon_pricing_status | /admin/addon_pricing_status |
| /addon_pricing_status | cmd_addon_pricing_status | /admin/addon_pricing_status |
| /addon_pricing_status | cmd_addon_pricing_status | /admin/addon_pricing_status |
| /addon_pricing_status | cmd_addon_pricing_status | /admin/addon_pricing_status |
| /addon_pricing_status | cmd_addon_pricing_status | /admin/addon_pricing_status |
| /adjust_package | cmd_adjust_package | /admin/adjust_package |
| /adjust_package | cmd_adjust_package | /admin/adjust_package |
| /adjust_package | cmd_adjust_package | /admin/adjust_package |
| /adjust_package | cmd_adjust_package | /admin/adjust_package |
| /adjust_package | cmd_adjust_package | /admin/adjust_package |
| /admin | cmd_admin_center | /admin/admin |
| /admin | cmd_admin_center | /admin/admin |
| /admin | cmd_admin_center | /admin/admin |
| /admin | cmd_admin_center | /admin/admin |
| /admin | cmd_admin_center | /admin/admin |
| /admin_api_roadmap | cmd_admin_api_roadmap | /admin/admin_api_roadmap |
| /admin_api_roadmap | cmd_admin_api_roadmap | /admin/admin_api_roadmap |
| /admin_api_roadmap | cmd_admin_api_roadmap | /admin/admin_api_roadmap |
| /admin_api_roadmap | cmd_admin_api_roadmap | /admin/admin_api_roadmap |
| /admin_api_roadmap | cmd_admin_api_roadmap | /admin/admin_api_roadmap |
| /admin_dashboard | cmd_admin_dashboard | /admin/admin_dashboard |
| /admin_dashboard | cmd_admin_dashboard | /admin/admin_dashboard |
| /admin_dashboard | cmd_admin_dashboard | /admin/admin_dashboard |
| /admin_dashboard | cmd_admin_dashboard | /admin/admin_dashboard |
| /admin_dashboard | cmd_admin_dashboard | /admin/admin_dashboard |
| /admin_doc_b2b | cmd_admin_doc_b2b | /admin/admin_doc_b2b |
| /admin_doc_b2b | cmd_admin_doc_b2b | /admin/admin_doc_b2b |
| /admin_doc_b2b | cmd_admin_doc_b2b | /admin/admin_doc_b2b |
| /admin_doc_b2b | cmd_admin_doc_b2b | /admin/admin_doc_b2b |
| /admin_doc_b2b | cmd_admin_doc_b2b | /admin/admin_doc_b2b |
| /admin_doc_b2c | cmd_admin_doc_b2c | /admin/admin_doc_b2c |
| /admin_doc_b2c | cmd_admin_doc_b2c | /admin/admin_doc_b2c |
| /admin_doc_b2c | cmd_admin_doc_b2c | /admin/admin_doc_b2c |
| /admin_doc_b2c | cmd_admin_doc_b2c | /admin/admin_doc_b2c |
| /admin_doc_b2c | cmd_admin_doc_b2c | /admin/admin_doc_b2c |
| /admin_doc_checklist | cmd_admin_doc_checklist | /admin/admin_doc_checklist |
| /admin_doc_checklist | cmd_admin_doc_checklist | /admin/admin_doc_checklist |
| /admin_doc_checklist | cmd_admin_doc_checklist | /admin/admin_doc_checklist |
| /admin_doc_checklist | cmd_admin_doc_checklist | /admin/admin_doc_checklist |
| /admin_doc_checklist | cmd_admin_doc_checklist | /admin/admin_doc_checklist |
| /admin_doc_converter | cmd_admin_doc_converter | /admin/admin_doc_converter |
| /admin_doc_converter | cmd_admin_doc_converter | /admin/admin_doc_converter |
| /admin_doc_converter | cmd_admin_doc_converter | /admin/admin_doc_converter |
| /admin_doc_converter | cmd_admin_doc_converter | /admin/admin_doc_converter |
| /admin_doc_converter | cmd_admin_doc_converter | /admin/admin_doc_converter |
| /admin_doc_ip | cmd_admin_doc_ip | /admin/admin_doc_ip |
| /admin_doc_ip | cmd_admin_doc_ip | /admin/admin_doc_ip |
| /admin_doc_ip | cmd_admin_doc_ip | /admin/admin_doc_ip |
| /admin_doc_ip | cmd_admin_doc_ip | /admin/admin_doc_ip |
| /admin_doc_ip | cmd_admin_doc_ip | /admin/admin_doc_ip |
| /admin_doc_nda | cmd_admin_doc_nda | /admin/admin_doc_nda |
| /admin_doc_nda | cmd_admin_doc_nda | /admin/admin_doc_nda |
| /admin_doc_nda | cmd_admin_doc_nda | /admin/admin_doc_nda |
| /admin_doc_nda | cmd_admin_doc_nda | /admin/admin_doc_nda |
| /admin_doc_nda | cmd_admin_doc_nda | /admin/admin_doc_nda |
| /admin_doc_risk | cmd_admin_doc_risk | /admin/admin_doc_risk |
| /admin_doc_risk | cmd_admin_doc_risk | /admin/admin_doc_risk |
| /admin_doc_risk | cmd_admin_doc_risk | /admin/admin_doc_risk |
| /admin_doc_risk | cmd_admin_doc_risk | /admin/admin_doc_risk |
| /admin_doc_risk | cmd_admin_doc_risk | /admin/admin_doc_risk |
| /admin_doc_sources | cmd_admin_doc_sources | /admin/admin_doc_sources |
| /admin_doc_sources | cmd_admin_doc_sources | /admin/admin_doc_sources |
| /admin_doc_sources | cmd_admin_doc_sources | /admin/admin_doc_sources |
| /admin_doc_sources | cmd_admin_doc_sources | /admin/admin_doc_sources |
| /admin_doc_sources | cmd_admin_doc_sources | /admin/admin_doc_sources |
| /admin_doc_tax | cmd_admin_doc_tax | /admin/admin_doc_tax |
| /admin_doc_tax | cmd_admin_doc_tax | /admin/admin_doc_tax |
| /admin_doc_tax | cmd_admin_doc_tax | /admin/admin_doc_tax |
| /admin_doc_tax | cmd_admin_doc_tax | /admin/admin_doc_tax |
| /admin_doc_tax | cmd_admin_doc_tax | /admin/admin_doc_tax |
| /admin_docs | cmd_admin_docs | /admin/admin_docs |
| /admin_docs | cmd_admin_docs | /admin/admin_docs |
| /admin_docs | cmd_admin_docs | /admin/admin_docs |
| /admin_docs | cmd_admin_docs | /admin/admin_docs |
| /admin_docs | cmd_admin_docs | /admin/admin_docs |
| /admin_gopy | cmd_admin_gopy | /admin/admin_gopy |
| /admin_gopy | cmd_admin_gopy | /admin/admin_gopy |
| /admin_gopy | cmd_admin_gopy | /admin/admin_gopy |
| /admin_gopy | cmd_admin_gopy | /admin/admin_gopy |
| /admin_gopy | cmd_admin_gopy | /admin/admin_gopy |
| /admin_gopy | cmd_admin_gopy | /admin/admin_gopy |
| /admin_grant_plan | cmd_admin_grant_plan | /admin/admin_grant_plan |
| /admin_grant_plan | cmd_admin_grant_plan | /admin/admin_grant_plan |
| /admin_grant_plan | cmd_admin_grant_plan | /admin/admin_grant_plan |
| /admin_grant_plan | cmd_admin_grant_plan | /admin/admin_grant_plan |
| /admin_grant_plan | cmd_admin_grant_plan | /admin/admin_grant_plan |
| /admin_help | cmd_admin_help | /admin/admin_help |
| /admin_help | cmd_admin_help | /admin/admin_help |
| /admin_help | cmd_admin_help | /admin/admin_help |
| /admin_help | cmd_admin_help | /admin/admin_help |
| /admin_help | cmd_admin_help | /admin/admin_help |
| /admin_import_affiliate_inventory | admin_internal_command | /admin/admin_import_affiliate_inventory |
| /admin_import_affiliate_inventory | admin_internal_command | /admin/admin_import_affiliate_inventory |
| /admin_import_affiliate_inventory | admin_internal_command | /admin/admin_import_affiliate_inventory |
| /admin_import_affiliate_inventory | admin_internal_command | /admin/admin_import_affiliate_inventory |
| /admin_import_affiliate_inventory | admin_internal_command | /admin/admin_import_affiliate_inventory |
| /admin_import_reference_video | admin_internal_command | /admin/admin_import_reference_video |
| /admin_import_reference_video | admin_internal_command | /admin/admin_import_reference_video |
| /admin_import_reference_video | admin_internal_command | /admin/admin_import_reference_video |
| /admin_import_reference_video | admin_internal_command | /admin/admin_import_reference_video |
| /admin_import_reference_video | admin_internal_command | /admin/admin_import_reference_video |
| /admin_member_help | cmd_admin_member_help | /admin/admin_member_help |
| /admin_member_help | cmd_admin_member_help | /admin/admin_member_help |
| /admin_member_help | cmd_admin_member_help | /admin/admin_member_help |
| /admin_member_help | cmd_admin_member_help | /admin/admin_member_help |
| /admin_member_help | cmd_admin_member_help | /admin/admin_member_help |
| /admin_payment_help | cmd_admin_payment_help | /admin/admin_payment_help |
| /admin_payment_help | cmd_admin_payment_help | /admin/admin_payment_help |
| /admin_payment_help | cmd_admin_payment_help | /admin/admin_payment_help |
| /admin_payment_help | cmd_admin_payment_help | /admin/admin_payment_help |
| /admin_payment_help | cmd_admin_payment_help | /admin/admin_payment_help |
| /admin_plan_status | cmd_admin_plan_status | /admin/admin_plan_status |
| /admin_plan_status | cmd_admin_plan_status | /admin/admin_plan_status |
| /admin_plan_status | cmd_admin_plan_status | /admin/admin_plan_status |
| /admin_plan_status | cmd_admin_plan_status | /admin/admin_plan_status |
| /admin_plan_status | cmd_admin_plan_status | /admin/admin_plan_status |
| /admin_report_month | cmd_admin_report_month | /admin/admin_report_month |
| /admin_report_month | cmd_admin_report_month | /admin/admin_report_month |
| /admin_report_month | cmd_admin_report_month | /admin/admin_report_month |
| /admin_report_month | cmd_admin_report_month | /admin/admin_report_month |
| /admin_report_month | cmd_admin_report_month | /admin/admin_report_month |
| /admin_report_year | cmd_admin_report_year | /admin/admin_report_year |
| /admin_report_year | cmd_admin_report_year | /admin/admin_report_year |
| /admin_report_year | cmd_admin_report_year | /admin/admin_report_year |
| /admin_report_year | cmd_admin_report_year | /admin/admin_report_year |
| /admin_report_year | cmd_admin_report_year | /admin/admin_report_year |
| /admin_revoke_plan | cmd_admin_revoke_plan | /admin/admin_revoke_plan |
| /admin_revoke_plan | cmd_admin_revoke_plan | /admin/admin_revoke_plan |
| /admin_revoke_plan | cmd_admin_revoke_plan | /admin/admin_revoke_plan |
| /admin_revoke_plan | cmd_admin_revoke_plan | /admin/admin_revoke_plan |
| /admin_revoke_plan | cmd_admin_revoke_plan | /admin/admin_revoke_plan |
| /admin_tools_help | cmd_admin_tools_help | /admin/admin_tools_help |
| /admin_tools_help | cmd_admin_tools_help | /admin/admin_tools_help |
| /admin_tools_help | cmd_admin_tools_help | /admin/admin_tools_help |
| /admin_tools_help | cmd_admin_tools_help | /admin/admin_tools_help |
| /admin_tools_help | cmd_admin_tools_help | /admin/admin_tools_help |
| /admin_trend_video | admin_internal_command | /admin/admin_trend_video |
| /admin_trend_video | admin_internal_command | /admin/admin_trend_video |
| /admin_trend_video | admin_internal_command | /admin/admin_trend_video |
| /admin_trend_video | admin_internal_command | /admin/admin_trend_video |
| /admin_trend_video | admin_internal_command | /admin/admin_trend_video |
| /admin_whoami | cmd_admin_whoami | /admin/admin_whoami |
| /admin_whoami | cmd_admin_whoami | /admin/admin_whoami |
| /admin_whoami | cmd_admin_whoami | /admin/admin_whoami |
| /admin_whoami | cmd_admin_whoami | /admin/admin_whoami |
| /admin_whoami | cmd_admin_whoami | /admin/admin_whoami |
| /affiliate_add | admin_internal_command | /admin/affiliate_add |
| /affiliate_add | admin_internal_command | /admin/affiliate_add |
| /affiliate_add | admin_internal_command | /admin/affiliate_add |
| /affiliate_add | admin_internal_command | /admin/affiliate_add |
| /affiliate_add | admin_internal_command | /admin/affiliate_add |
| /affiliate_bundle | admin_internal_command | /admin/affiliate_bundle |
| /affiliate_bundle | admin_internal_command | /admin/affiliate_bundle |
| /affiliate_bundle | admin_internal_command | /admin/affiliate_bundle |
| /affiliate_bundle | admin_internal_command | /admin/affiliate_bundle |
| /affiliate_bundle | admin_internal_command | /admin/affiliate_bundle |
| /affiliate_cockpit | admin_internal_command | /admin/affiliate_cockpit |
| /affiliate_cockpit | admin_internal_command | /admin/affiliate_cockpit |
| /affiliate_cockpit | admin_internal_command | /admin/affiliate_cockpit |
| /affiliate_cockpit | admin_internal_command | /admin/affiliate_cockpit |
| /affiliate_cockpit | admin_internal_command | /admin/affiliate_cockpit |
| /affiliate_decisions | admin_internal_command | /admin/affiliate_decisions |
| /affiliate_decisions | admin_internal_command | /admin/affiliate_decisions |
| /affiliate_decisions | admin_internal_command | /admin/affiliate_decisions |
| /affiliate_decisions | admin_internal_command | /admin/affiliate_decisions |
| /affiliate_decisions | admin_internal_command | /admin/affiliate_decisions |
| /affiliate_ideas | admin_internal_command | /admin/affiliate_ideas |
| /affiliate_ideas | admin_internal_command | /admin/affiliate_ideas |
| /affiliate_ideas | admin_internal_command | /admin/affiliate_ideas |

## Web-local Finance Planning

`/admin/finance/planning` is a Web-local Finance Planning workspace, not a canonical Bot finance projection. The independently signed local-admin route requires `WEBAPP_ADMIN_ERP_ENABLED` and `WEBAPP_FINANCE_PLANNING_ENABLED`; every write is subject to the module's CSRF, confirmation, idempotency, revision and audit controls. It plans Web-owned budgets and operating costs only, and must not read or mutate Bot identity/roles, ledger/Xu, PayOS, provider, payment, refund, revenue, tax, export or canonical finance events.
