# Core mobile fields — Features + Account — 09/11/2026

SPEC_ID=CORE-MOBILE-FIELDS-16
BASE_SHA=6afca4a277c33283587e51e1b1986a09b1ce0283
Worker packet used public CSS/MAP only; one scoped mobile CSS block. No provider/wallet/ENV/production data.

Native QA after patch: Features/Account, VI/EN/ZH, light/dark, 320/414/1024 =36 records; transport/page/errors/overflow all0; mobile field font violations0. Two Account buttons were observed at43.92px while CSS specifies min-height44px. The cause was not proven: do not label it subpixel rounding or dismiss it solely from source CSS. A fresh settled, transform-aware target measurement remains open. Desktop values were unchanged by the <=620 media rule.

This unit closes only the two proven mobile typography REDs. The Video Studio
native R4 matrix separately measured its ten editable fields at 16px on 320/414
and 15px on1024 across18 records; it does not close whole-app contrast/keyboard/
locale state/auth first-paint/CLS-LCP-INP/signed production.
