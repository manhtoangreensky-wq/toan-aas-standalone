# Reviewed App Shell locale coverage

The signed Web profile supports three reviewed interface catalogues: `vi`
(Vietnamese), `en` (English), and `zh` (Simplified Chinese).

This increment translates the persistent Web App shell: sidebar groups and
stable route entries, desktop breadcrumbs and generic route titles, the
existing mobile dock, and stable command-palette route metadata. The customer
asset center is named `Tài sản`/Assets/资源 in the standalone Web shell; legacy
`Tài sản Bot` manifest metadata resolves to that same reviewed label. The
`ERP` prefix is translated, but server-authorized ERP module names remain
server data and are never browser-translated.

The interface preference is presentation-only. It does not translate or
mutate customer briefs, prompts, files, generated text, Bot data, Telegram
identity, provider responses, job state, wallet/Xu, PayOS, or audit data.
Unknown route names safely fall back to their original server-provided text.
No persistence, network request, workflow action, provider call, or browser
storage is added by the i18n bundle.
