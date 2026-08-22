# Package-purchase callback disposition contract

The frozen Bot has nine finite `pkgbuy` catalog-selector callbacks. Each validates a catalog package and redraws a Telegram detail/confirmation screen; it does not by itself create an order, call PayOS, grant entitlement, add Xu, or deliver an output. The Bot confirmation callback is a distinct stateful branch. It calls `start_package_purchase`, which may create a pending canonical order, create a PayOS checkout and later grant package entitlement only after canonical settlement.

| Bot callback source | Web target/boundary | Audit resolution | Status | Source dispositions |
| --- | --- | --- | --- | --- |
| nine exact package selectors | /packages | reviewed_package_catalog_selector_navigation | NAVIGATION_ONLY | FRESH_SIGNED_WEB_NAVIGATION, BOT_CATALOG_SELECTION_NOT_REPLAYED, NO_RUNTIME_CLAIM |
| pkgbuy\|confirm\|{*}\|{*} | TELEGRAM_ONLY | bot_canonical_package_checkout | TELEGRAM_ONLY | TELEGRAM_IDENTITY_CONTEXT, CANONICAL_BOT_ORDER_REQUIRED, CANONICAL_BOT_PAYOS_CHECKOUT, CANONICAL_PACKAGE_ENTITLEMENT_SETTLEMENT, NO_RUNTIME_CLAIM |
| other pkgbuy\|* | PACKAGE_PURCHASE_SOURCE_REVIEW_REQUIRED | package_purchase_callback_requires_source_review | NEEDS_FEATURE_DISPOSITION | CANONICAL_PACKAGE_PURCHASE_SOURCE_REVIEW, SOURCE_STATE_MACHINE_REQUIRED, NO_RUNTIME_CLAIM |

The exact catalog selectors are: `pkgbuy|combo|basic_199k`, `pkgbuy|combo|posting_499k`, `pkgbuy|combo|product_ads_699k`, `pkgbuy|combo|standard_299k`, `pkgbuy|combo|tiktok_99k`, `pkgbuy|monthly|creator_monthly`, `pkgbuy|monthly|pro_monthly`, `pkgbuy|monthly|shop_monthly`, `pkgbuy|monthly|starter_monthly`. They may open only a fresh signed `/packages` catalog. The Web receives no Bot package type/code, Telegram identity or pending state, price, entitlement, checkout URL, order ID, PayOS state, or confirmation action. `/packages` is not a browser checkout.

`pkgbuy|confirm|{*}|{*}` stays Telegram-only until a separately reviewed owner-scoped package-purchase bridge exists. The Web must not price a service package, create a canonical order, issue or finalize PayOS, credit Xu, grant package entitlement, create a second webhook/ledger, or infer success from a callback. Any unlisted `pkgbuy|*` value remains source-review-required.
