# Unreferenced static Bot handler-package modules

Observation status: `HANDLERS_UNREFERENCED_BY_OBSERVED_ENTRYPOINT`. Observed entrypoint: `bot.py`. Records preserved outside the observed-runtime denominator: `57`. This scoped source-only observation evaluates the local `handlers/` package, not every Python module in the repository. It does not delete a file or prove that an arbitrary deployment can never load it. It only prevents a handler-package module with no static path from the observed entrypoint from becoming a false Web parity claim.

## Handler-package files outside the observed import closure

- `handlers/__init__.py`
- `handlers/admin_handler.py`
- `handlers/affiliate_handler.py`
- `handlers/freelance_handler.py`
- `handlers/mxh_handler.py`
- `handlers/tools_handler.py`
- `handlers/video_handler.py`

## Preserved source evidence

| Source type | Bot entry | Disposition | File | Line |
| --- | --- | --- | --- | --- |
| callback_data | affiliate_intl | UNREFERENCED_BY_OBSERVED_ENTRYPOINT | handlers/affiliate_handler.py | 15 |
| callback_data | affiliate_social | UNREFERENCED_BY_OBSERVED_ENTRYPOINT | handlers/affiliate_handler.py | 16 |
| callback_data | affiliate_tips | UNREFERENCED_BY_OBSERVED_ENTRYPOINT | handlers/affiliate_handler.py | 17 |
| callback_data | affiliate_vn | UNREFERENCED_BY_OBSERVED_ENTRYPOINT | handlers/affiliate_handler.py | 14 |
| callback_data | back_main | UNREFERENCED_BY_OBSERVED_ENTRYPOINT | handlers/affiliate_handler.py | 18 |
| callback_data | back_main | UNREFERENCED_BY_OBSERVED_ENTRYPOINT | handlers/freelance_handler.py | 20 |
| callback_data | back_main | UNREFERENCED_BY_OBSERVED_ENTRYPOINT | handlers/mxh_handler.py | 20 |
| callback_data | back_main | UNREFERENCED_BY_OBSERVED_ENTRYPOINT | handlers/tools_handler.py | 20 |
| callback_data | back_main | UNREFERENCED_BY_OBSERVED_ENTRYPOINT | handlers/video_handler.py | 18 |
| callback_data | freelance_design | UNREFERENCED_BY_OBSERVED_ENTRYPOINT | handlers/freelance_handler.py | 16 |
| callback_data | freelance_marketing | UNREFERENCED_BY_OBSERVED_ENTRYPOINT | handlers/freelance_handler.py | 18 |
| callback_data | freelance_platforms | UNREFERENCED_BY_OBSERVED_ENTRYPOINT | handlers/freelance_handler.py | 14 |
| callback_data | freelance_tech | UNREFERENCED_BY_OBSERVED_ENTRYPOINT | handlers/freelance_handler.py | 17 |
| callback_data | freelance_translate | UNREFERENCED_BY_OBSERVED_ENTRYPOINT | handlers/freelance_handler.py | 19 |
| callback_data | freelance_writing | UNREFERENCED_BY_OBSERVED_ENTRYPOINT | handlers/freelance_handler.py | 15 |
| callback_data | menu_affiliate | UNREFERENCED_BY_OBSERVED_ENTRYPOINT | handlers/affiliate_handler.py | 61 |
| callback_data | menu_affiliate | UNREFERENCED_BY_OBSERVED_ENTRYPOINT | handlers/affiliate_handler.py | 94 |
| callback_data | menu_affiliate | UNREFERENCED_BY_OBSERVED_ENTRYPOINT | handlers/affiliate_handler.py | 131 |
| callback_data | menu_affiliate | UNREFERENCED_BY_OBSERVED_ENTRYPOINT | handlers/affiliate_handler.py | 163 |
| callback_data | menu_freelance | UNREFERENCED_BY_OBSERVED_ENTRYPOINT | handlers/freelance_handler.py | 75 |
| callback_data | menu_freelance | UNREFERENCED_BY_OBSERVED_ENTRYPOINT | handlers/freelance_handler.py | 109 |
| callback_data | menu_freelance | UNREFERENCED_BY_OBSERVED_ENTRYPOINT | handlers/freelance_handler.py | 141 |
| callback_data | menu_freelance | UNREFERENCED_BY_OBSERVED_ENTRYPOINT | handlers/freelance_handler.py | 175 |
| callback_data | menu_freelance | UNREFERENCED_BY_OBSERVED_ENTRYPOINT | handlers/freelance_handler.py | 207 |
| callback_data | menu_freelance | UNREFERENCED_BY_OBSERVED_ENTRYPOINT | handlers/freelance_handler.py | 238 |
| callback_data | menu_mxh | UNREFERENCED_BY_OBSERVED_ENTRYPOINT | handlers/mxh_handler.py | 67 |
| callback_data | menu_mxh | UNREFERENCED_BY_OBSERVED_ENTRYPOINT | handlers/mxh_handler.py | 93 |
| callback_data | menu_mxh | UNREFERENCED_BY_OBSERVED_ENTRYPOINT | handlers/mxh_handler.py | 119 |
| callback_data | menu_mxh | UNREFERENCED_BY_OBSERVED_ENTRYPOINT | handlers/mxh_handler.py | 147 |
| callback_data | menu_mxh | UNREFERENCED_BY_OBSERVED_ENTRYPOINT | handlers/mxh_handler.py | 172 |
| callback_data | menu_mxh | UNREFERENCED_BY_OBSERVED_ENTRYPOINT | handlers/mxh_handler.py | 198 |
| callback_data | menu_tools | UNREFERENCED_BY_OBSERVED_ENTRYPOINT | handlers/tools_handler.py | 71 |
| callback_data | menu_tools | UNREFERENCED_BY_OBSERVED_ENTRYPOINT | handlers/tools_handler.py | 103 |
| callback_data | menu_tools | UNREFERENCED_BY_OBSERVED_ENTRYPOINT | handlers/tools_handler.py | 139 |
| callback_data | menu_tools | UNREFERENCED_BY_OBSERVED_ENTRYPOINT | handlers/tools_handler.py | 177 |
| callback_data | menu_tools | UNREFERENCED_BY_OBSERVED_ENTRYPOINT | handlers/tools_handler.py | 209 |
| callback_data | menu_tools | UNREFERENCED_BY_OBSERVED_ENTRYPOINT | handlers/tools_handler.py | 248 |
| callback_data | menu_video | UNREFERENCED_BY_OBSERVED_ENTRYPOINT | handlers/video_handler.py | 69 |
| callback_data | menu_video | UNREFERENCED_BY_OBSERVED_ENTRYPOINT | handlers/video_handler.py | 100 |
| callback_data | menu_video | UNREFERENCED_BY_OBSERVED_ENTRYPOINT | handlers/video_handler.py | 131 |
| callback_data | menu_video | UNREFERENCED_BY_OBSERVED_ENTRYPOINT | handlers/video_handler.py | 166 |
| callback_data | mxh_facebook | UNREFERENCED_BY_OBSERVED_ENTRYPOINT | handlers/mxh_handler.py | 15 |
| callback_data | mxh_instagram | UNREFERENCED_BY_OBSERVED_ENTRYPOINT | handlers/mxh_handler.py | 16 |
| callback_data | mxh_linkedin | UNREFERENCED_BY_OBSERVED_ENTRYPOINT | handlers/mxh_handler.py | 18 |
| callback_data | mxh_tiktok | UNREFERENCED_BY_OBSERVED_ENTRYPOINT | handlers/mxh_handler.py | 14 |
| callback_data | mxh_twitter | UNREFERENCED_BY_OBSERVED_ENTRYPOINT | handlers/mxh_handler.py | 19 |
| callback_data | mxh_youtube | UNREFERENCED_BY_OBSERVED_ENTRYPOINT | handlers/mxh_handler.py | 17 |
| callback_data | tools_ai | UNREFERENCED_BY_OBSERVED_ENTRYPOINT | handlers/tools_handler.py | 14 |
| callback_data | tools_automation | UNREFERENCED_BY_OBSERVED_ENTRYPOINT | handlers/tools_handler.py | 18 |
| callback_data | tools_design | UNREFERENCED_BY_OBSERVED_ENTRYPOINT | handlers/tools_handler.py | 15 |
| callback_data | tools_payment | UNREFERENCED_BY_OBSERVED_ENTRYPOINT | handlers/tools_handler.py | 17 |
| callback_data | tools_productivity | UNREFERENCED_BY_OBSERVED_ENTRYPOINT | handlers/tools_handler.py | 19 |
| callback_data | tools_seo | UNREFERENCED_BY_OBSERVED_ENTRYPOINT | handlers/tools_handler.py | 16 |
| callback_data | video_course | UNREFERENCED_BY_OBSERVED_ENTRYPOINT | handlers/video_handler.py | 17 |
| callback_data | video_editing | UNREFERENCED_BY_OBSERVED_ENTRYPOINT | handlers/video_handler.py | 15 |
| callback_data | video_faceless | UNREFERENCED_BY_OBSERVED_ENTRYPOINT | handlers/video_handler.py | 14 |
| callback_data | video_stock | UNREFERENCED_BY_OBSERVED_ENTRYPOINT | handlers/video_handler.py | 16 |

A module moves back into the runtime parity denominator only after a static import path from the observed entrypoint is present and its finite behavior is reviewed.
