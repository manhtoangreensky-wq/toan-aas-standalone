# Core mobile fields — Features + Account — 09/11/2026

SPEC_ID=CORE-MOBILE-FIELDS-16
BASE_SHA=6afca4a277c33283587e51e1b1986a09b1ce0283
Worker packet used public CSS/MAP only; one scoped mobile CSS block. No provider/wallet/ENV/production data.

Native QA after patch: Features/Account, VI/EN/ZH, light/dark, 320/414/1024 =36 records; transport/page/errors/overflow all0; mobile field font violations0; tracked field target observations all at/above44 except two Account buttons measured43.92px from subpixel geometry (CSS min-height44), no separate RED without device-level or screenshot confirmation. Desktop values unchanged by <=620 media.

This unit closes only the two proven mobile typography REDs. It does not close whole-app contrast/keyboard/locale state/auth first-paint/CLS-LCP-INP/signed production.
