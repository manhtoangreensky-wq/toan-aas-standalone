# Public Auth Locale Clarity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete immediate VI/EN/ZH presentation for public login, registration and password-recovery routes without changing their auth behavior.

**Architecture:** `portal-i18n.js` owns reviewed copy, while `portal.js` resolves that copy through existing `uiText`/`accessText` calls. `copyfast_pages.py` owns the no-JavaScript recovery document title. Static contracts prevent this presenter-only scope from expanding into browser-owned auth, payment, provider or Bot behavior.

**Tech Stack:** FastAPI/Python, static browser JavaScript, pytest.

---

## File structure

- `static/portal/portal-i18n.js`: reviewed `access.*` strings in each locale bundle.
- `static/portal/portal.js`: recovery field metadata and locale-key notice rendering.
- `copyfast_pages.py`: server-rendered recovery title tuple.
- `copyfast_registry.py`: explicit public recovery renderer admission.
- `tests/test_public_auth_locale_contracts.py`: static presentation and boundary contract.
- `docs/superpowers/specs/2026-08-03-public-auth-locale-clarity-design.md`: scope record.

### Task 1: Lock the public-auth presentation contract

**Files:**

- Create: `tests/test_public_auth_locale_contracts.py`

- [ ] **Step 1: Write the failing test**

```python
def test_public_auth_locale_copy_is_complete_without_new_browser_authority() -> None:
    auth = _between(PORTAL, "function renderAuth", "const RESULT_LABELS")
    fields = _between(PORTAL, "const FIELD_SETS = Object.freeze({", "// Public account and portal routes.")
    for key in (
        "access.heading.recovery", "access.intro.recovery", "access.primary.recovery",
        "access.primary.recoveryDescription", "access.action.recovery",
        "access.field.recoveryEmail", "access.help.recoveryEmail",
        "access.notice.registrationHandoffTitle", "access.notice.registrationHandoffBody",
        "access.oauth.title", "access.oauth.unavailable", "access.oauth.cancelled",
        "access.oauth.failed", "access.oauth.state", "access.oauth.session",
        "access.oauth.linkRequired", "access.oauth.linked", "access.oauth.alreadyLinked",
        "access.notice.defaultProfileTitle", "access.notice.defaultProfileBody",
    ):
        assert I18N.count(f'"{key}"') == 3
    assert 'labelKey: "access.field.recoveryEmail"' in fields
    assert 'placeholderKey: "access.placeholder.email"' in fields
    assert 'helpKey: "access.help.recoveryEmail"' in fields
    assert 'actionLabelKey: "access.action.recovery"' in PORTAL
    for required in ('accessText("heading.recovery", "Khôi phục mật khẩu")', 'accessText("intro.recovery", "Yêu cầu liên kết đặt lại mật khẩu một cách riêng tư.")', 'accessText("primary.recovery", "Khôi phục mật khẩu")', 'accessText("notice.registrationHandoffTitle", "Tiếp tục bằng đăng nhập")', 'accessText("oauth.title", "OAuth")', 'accessText("notice.defaultProfileTitle", "Hồ sơ mặc định sau khi tạo")'):
        assert required in auth
    for forbidden in ('fetch(', 'api(', 'localStorage', 'sessionStorage', 'telegram_id', 'wallet', 'payos'):
        assert forbidden not in auth.lower()


def test_recovery_route_and_server_title_stay_allowlisted() -> None:
    assert 'path: "/login"' in PORTAL and 'action: "auth-login"' in PORTAL
    assert 'path: "/register"' in PORTAL and 'action: "auth-register"' in PORTAL
    assert 'path: "/password-recovery"' in PORTAL
    assert 'action: "auth-password-recovery-start"' in PORTAL
    assert '"/password-recovery": {"vi": "Khôi phục mật khẩu · TOAN AAS", "en": "Password recovery · TOAN AAS", "zh": "找回密码 · TOAN AAS"}' in PAGES


def test_password_recovery_shell_is_publicly_renderable_in_english() -> None:
    response = render_portal("/password-recovery", interface_locale="en")
    assert response.status_code == 200
    assert b"<title>Password recovery \xc2\xb7 TOAN AAS</title>" in response.body
```

- [ ] **Step 2: Run the test to verify RED**

Run: `python -m pytest -q tests/test_public_auth_locale_contracts.py`

Expected: it fails because the recovery keys and server title tuple do not exist yet.

### Task 2: Project locale keys through the existing auth presenter

**Files:**

- Modify: `static/portal/portal-i18n.js`
- Modify: `static/portal/portal.js:438-440,862-865,23962-24052`

- [ ] **Step 1: Add exact recovery keys to every locale bundle**

| Key | Vietnamese | English | Simplified Chinese |
| --- | --- | --- | --- |
| `access.heading.recovery` | `Khôi phục mật khẩu` | `Recover your password` | `找回密码` |
| `access.intro.recovery` | `Yêu cầu liên kết đặt lại mật khẩu một cách riêng tư.` | `Request a password-reset link privately.` | `私密地请求密码重置链接。` |
| `access.primary.recovery` | `Khôi phục mật khẩu` | `Password recovery` | `密码找回` |
| `access.primary.recoveryDescription` | `Nhập email để nhận hướng dẫn an toàn.` | `Enter your email to receive safe instructions.` | `输入邮箱以接收安全说明。` |
| `access.action.recovery` | `Gửi liên kết đặt lại` | `Send reset link` | `发送重置链接` |
| `access.field.recoveryEmail` | `Email tài khoản` | `Account email` | `账户邮箱` |
| `access.help.recoveryEmail` | `Phản hồi luôn giống nhau để không tiết lộ tài khoản có tồn tại hay không.` | `The response is always the same and does not reveal whether an account exists.` | `响应始终相同，不会透露该账户是否存在。` |

Add the corresponding locale triplets for existing registration handoff title/body, OAuth title and eight OAuth outcomes, and default-profile title/body. Preserve the current Vietnamese fallback text exactly.

- [ ] **Step 2: Make recovery field and page metadata use the keys**

```javascript
passwordRecovery: [
  { name: "email", label: "Email tài khoản", labelKey: "access.field.recoveryEmail", type: "email", placeholder: "you@example.com", placeholderKey: "access.placeholder.email", autocomplete: "email", required: true, maxLength: 254, help: "Phản hồi luôn giống nhau để không tiết lộ tài khoản có tồn tại hay không.", helpKey: "access.help.recoveryEmail" }
],
```

```javascript
access: "public", layout: "auth", status: "ready", action: "auth-password-recovery-start", actionLabel: "Gửi liên kết đặt lại", actionLabelKey: "access.action.recovery", fields: copyFields(FIELD_SETS.passwordRecovery),
```

- [ ] **Step 3: Resolve the required presentational copy**

Set `isRecovery` once inside `renderAuth`. Resolve recovery heading, intro, primary title and description through the listed `access.*` keys. Replace only registration handoff, OAuth-result and default-profile notice strings with `accessText` keys; retain their query handling, visual status class and all existing `oauthReason` values.

Keep the already allowlisted interface locale through the existing public
continuations: the registration handoff must redirect to
`/login?registered=1&lang=<vi|en|zh>`, and public OAuth must retain only that
locale inside its already validated return path. Do not preserve arbitrary
query values, change provider configuration/state semantics, or add a cookie
or redirect target.

- [ ] **Step 4: Run the contract to verify GREEN**

Run: `python -m pytest -q tests/test_public_auth_locale_contracts.py`

Expected: `2 passed`.

### Task 3: Admit the existing public recovery route and add its no-JavaScript title

**Files:**

- Modify: `copyfast_pages.py:130-132`
- Modify: `copyfast_registry.py:541-547`

- [ ] **Step 1: Add the route tuple beside login and registration**

```python
"/password-recovery": {"vi": "Khôi phục mật khẩu · TOAN AAS", "en": "Password recovery · TOAN AAS", "zh": "找回密码 · TOAN AAS"},
```

Add the one exact existing public route to the closed registry set:

```python
"/login",
"/register",
"/password-recovery",
"/onboarding",
```

- [ ] **Step 2: Run the contract again**

Run: `python -m pytest -q tests/test_public_auth_locale_contracts.py`

Expected: `3 passed`, the exact server title tuple is present, and the public
renderer returns the English recovery shell instead of a 404.

### Task 4: Verify narrow scope and hand off safely

**Files:**

- Modify: `docs/superpowers/specs/2026-08-03-public-auth-locale-clarity-design.md`
- Modify: `docs/superpowers/plans/2026-08-03-public-auth-locale-clarity.md`

- [ ] **Step 1: Run focused regression tests and syntax validation**

```powershell
python -m pytest -q tests/test_public_auth_locale_contracts.py tests/test_login_app_ux_contracts.py tests/test_password_recovery_portal_contracts.py tests/test_portal_i18n_bundle_contracts.py tests/test_portal_i18n_locale_contracts.py tests/test_secure_access_first_run_contracts.py
node --check static/portal/portal.js
node --check static/portal/portal-i18n.js
git diff --check
```

Expected: selected tests pass, JavaScript parses, and diff check is empty.

- [ ] **Step 2: Run public route render smoke**

Start only a local app instance with an ephemeral `WEB_SESSION_SECRET` and no bridge/provider/payment variables. Check `/login?lang=en`, `/register?lang=zh` and `/password-recovery?lang=en` at desktop and 375px. Confirm translated recovery copy, translated notices when query states are present, no horizontal overflow, and no console error.

- [ ] **Step 3: Refresh the static migration evidence**

Run the audit against frozen Bot baseline `b29d0d474974075f4cba963d2c510f49d2d1b3e4` and retain only `docs/migration/README.md`, `reports/migration/preflight.json`, and `reports/migration/web_inventory.json` if they change. Do not import, run or modify Bot code.

- [ ] **Step 4: Commit and open one focused PR**

```powershell
git add static/portal/portal.js static/portal/portal-i18n.js copyfast_pages.py copyfast_registry.py tests/test_public_auth_locale_contracts.py tests/test_password_recovery_portal_contracts.py docs/superpowers/specs/2026-08-03-public-auth-locale-clarity-design.md docs/superpowers/plans/2026-08-03-public-auth-locale-clarity.md
git commit -m "Localize public auth continuation"
git push -u origin feature/p0-webapp-public-auth-locale-clarity
```

Open one PR against `main`, wait for `Verify Web App`, request independent spec and code-quality reviews, and merge only after all gates pass. Do not deploy Railway.
