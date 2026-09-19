# Web App V3 Visual System, Motion & Locale Contract
> **Task**: `P0.WEBAPP.V3.AUDIT.FINAL.ROADMAP.EXECUTION.SAFETY.CLOSURE`
> **Program**: `P0.WEBAPP.FULL.PRODUCT.TRUTH.REMEDIATION.V1`
> **Repository**: `manhtoangreensky-wq/toan-aas-standalone`
> **Base Commit**: `8873e10f2279aec0fb312b70388b9073ba763f13`
> **Governance**: `OWNER-GOVERNED`, `AUDIT_DOCUMENTATION_ONLY`, `NO_FEATURE_IMPLEMENTATION`

---

## 1. Visual System Rebase to Light Teal / Mint

### 1.1 Root Cause of Current Navy/Blue Dominance
During migration cycles `WEB11` and `WEB12`, an explicit blue theme layer was injected into `static/portal/portal-theme.css`:
- Lines 73–98: Added `--portal-customer-blue-rail: #075985;`, `--portal-customer-blue-rail-surface: #0c4a6e;`, `--portal-blue-action: #0284c7;`, `--portal-blue-dark-canvas: #0b2545;`, etc.
- Lines 3967–3971: Forced customer sidebar into navy blue:
  ```css
  .portal-shell[data-portal-app-kind="customer"] .portal-sidebar {
    border-right-color: var(--portal-customer-blue-rail-border);
    background: var(--portal-customer-blue-rail) !important;
    color: var(--portal-customer-blue-rail-text) !important;
  }
  ```
- Lines 20030–20063: Dark theme was mapped directly to navy blue tokens (`var(--portal-blue-dark-canvas)` = `#0b2545`).

This produced a visual disconnect from the Owner's intended **Light Teal / Mint** brand identity and created severe contrast regressions in active states.

---

### 1.2 Canonical Token Replacements (Theme Contract)

The V3 visual system establishes **Light Teal / Mint** as the canonical aesthetic for both Customer and Admin surfaces, with clean semantic tokens and obsidian/pine dark mode.

| Token Identifier | Current Stale Value | Canonical V3 Value | Role & Usage |
| :--- | :--- | :--- | :--- |
| `--portal-app-canvas` | `#f3fbfc` (overridden in dark to `#0b2545`) | `#f3fbfc` (Light) / `#041f24` (Dark) | App base background canvas |
| `--portal-surface-light` | `#ffffff` | `#ffffff` (Light) / `#072b32` (Dark) | Surface card / workspace container |
| `--portal-surface-raised` | `#ffffff` | `#ffffff` (Light) / `#0a3740` (Dark) | Popovers, modals, dropdowns |
| `--portal-surface-soft` | `#e8f6f7` | `#e6f7f6` (Light) / `#0d434e` (Dark) | Secondary panels, grouped section backgrounds |
| `--portal-brand` | `#0d9488` | `#0d9488` (Light) / `#14b8a6` (Dark) | Primary brand teal identifier |
| `--portal-action` | `#0284c7` (forced blue) / `#0f766e` | `#0d9488` (Light) / `#14b8a6` (Dark) | Primary action buttons and indicators |
| `--portal-action-hover` | `#0369a1` (blue) | `#0f766e` (Light) / `#2dd4bf` (Dark) | Hover state on primary actions |
| `--portal-ink` | `#073a45` (overridden in dark to `#f0f9ff`) | `#073a45` (Light) / `#f0fdfa` (Dark) | High-contrast heading and primary text |
| `--portal-ink-secondary` | `#456b77` | `#0f3741` (Light) / `#ccfbf1` (Dark) | Body copy and secondary section headings |
| `--portal-muted` | `#456b77` | `#456b77` (Light) / `#99f6e4` (Dark) | Secondary captions, metadata, timestamps |
| `--portal-border` | `#d5e9ed` | `#d5e9ed` (Light) / `#134e5e` (Dark) | Card dividers, table borders, input borders |
| `--portal-border-strong` | `#8ccfcf` | `#99d5d8` (Light) / `#2dd4bf` (Dark) | Active focus rings, selected card outlines |
| `--portal-mint-soft` | *(none)* | `#e6f7f6` (Light) / `#064e58` (Dark) | Subtle mint fills, badge backgrounds |
| `--portal-mint-highlight`| *(none)* | `#ccf0ee` (Light) / `#0f766e` (Dark) | Active item highlight, subtle pill backgrounds |
| `--portal-customer-rail` | `#075985` (forced navy) | `#f0fdfa` (Light) / `#021a1f` (Dark) | Customer navigation rail / sidebar |
| `--portal-customer-rail-text` | `#f0f9ff` (on navy) | `#073a45` (Light) / `#effcfd` (Dark) | Navigation link text |
| `--portal-customer-rail-active`| `#0c4a6e` (dark blue) | `#ccf0ee` (Light) / `#0d5260` (Dark) | Active route indicator & surface |

---

### 1.3 Semantic Status Tokens (Preserved Purity)
Status colors must never be tinted teal; they remain strictly distinct and universally legible:
- **Success:** `#15803d` (Light text/border) / `#22c55e` (Dark), Surface: `#f0fdf4` / `#052e16`
- **Warning:** `#a16207` (Light text/border) / `#facc15` (Dark), Surface: `#fefce8` / `#422006`
- **Danger/Error:** `#b91c1c` (Light text/border) / `#f87171` (Dark), Surface: `#fef2f2` / `#450a0a`
- **Info/Telemetry:** `#0284c7` (Light text/border) / `#38bdf8` (Dark), Surface: `#f0f9ff` / `#082f49`

---

## 2. Interaction & Pressed State Contrast Audit (WCAG AA)

### 2.1 Contrast Failure Inventory in Current Source

| Component & State | Current CSS Selectors | Foreground Color | Background Color | Contrast Ratio | WCAG AA Status | Root Cause & Visual Defect |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Customer Rail Nav Link (Active)** | `.portal-sidebar .portal-nav-link[aria-current="page"]` | `#ffffff` | `#0c4a6e` (Navy) | 7.8:1 | PASS (Navy only) | In light rebase, text `#073a45` on `#0d9488` is **3.1:1** (FAIL). Text must be `#ffffff` on `#0d9488` (4.5:1) or `#073a45` on `#ccf0ee` (10.2:1). |
| **Customer Rail Nav Link (Pressed)** | `.portal-sidebar .portal-nav-link:active` | `#effcfd` | `#0e7490` | 4.8:1 | PASS | On click, box-shadow jumps and text shifts position, causing visual jitter. |
| **Primary Button (Pressed)** | `.portal-btn--primary:active` | `#ffffff` | `#0369a1` (Blue) / `#0f766e` | 6.3:1 | PASS | When theme fallback fails, text inherits `--portal-ink` (`#073a45`), dropping contrast to **1.8:1** (black-on-dark unreadable). |
| **Secondary Chip / Filter (Active)**| `.portal-filter-chip[aria-pressed="true"]` | `#0f766e` | `#e8f6f7` | 3.8:1 | **FAIL (< 4.5:1)** | Low-contrast teal text on soft background fails AA for normal body text. Must use `#073a45` (8.4:1) with solid border `#0d9488`. |
| **Form Input Placeholder (Dark)** | `html[data-portal-theme="dark"] input::placeholder` | `#7dd3fc` | `#102f4f` | 3.4:1 | **FAIL (< 4.5:1)** | Light blue placeholder on navy surface fails accessibility standards. |
| **Disabled Button State** | `.portal-btn:disabled` | `#78949b` | `#edf6f7` | 2.8:1 | **FAIL (< 3:1)** | Disabled text is nearly invisible on high-nit mobile screens under sunlight. |
| **Table Row Hover** | `.portal-table tr:hover td` | `#073a45` | `#f8fdfd` | 13.5:1 | PASS | Row hover is clear, but lacks left-rail marker indicating active row selection. |

---

### 2.2 Standardized WCAG AA State Rules

Every interactive element across Light and Dark themes must comply with the following contrast and visual hierarchy matrix:

```
[DEFAULT]       -> High contrast text (>= 4.5:1), subtle boundary (>= 3:1)
[HOVER]         -> Background shifts 4-8% tint, border deepens, cursor pointer
[ACTIVE/PRESS]  -> Scale down (0.98), background darkens 10%, text remains strictly legible (>= 4.5:1)
[FOCUS-VISIBLE] -> 2px solid --portal-brand ring with 2px offset; outline: none; box-shadow ring
[DISABLED]      -> Opacity 0.55, cursor not-allowed, pointer-events none, contrast >= 3.0:1
```

---

## 3. Motion & Performance Budget Contract

### 3.1 Interaction & Motion Timing Budgets

Animations must be purposeful, snappy, and strictly performance-capped:

| Motion Type | Duration Budget | Easing Curve | Allowed CSS Properties | Prohibited Behavior |
| :--- | :--- | :--- | :--- | :--- |
| **Micro-interactions** (button press, chip toggle, icon rotate) | **120ms – 180ms** | `cubic-bezier(0.16, 1, 0.3, 1)` | `transform`, `opacity` | NO animating `width`, `height`, `padding`, `margin` |
| **Sheet / Drawer Slide-in** (mobile detail drawer, filter panel) | **200ms – 240ms** | `cubic-bezier(0.2, 0, 0, 1)` | `transform: translateX/Y`, `opacity` | NO layout reflow; use fixed composite layer (`will-change: transform`) |
| **Modal / Dialog Fade** | **150ms – 200ms** | `ease-out` | `opacity`, `transform: scale(0.97 -> 1.0)` | NO backdrop blur animations |
| **Page / Tab View Switch** | **200ms – 250ms** | `ease-out` | `opacity`, `transform: translateY(4px -> 0)` | NO staggered children waterfalls exceeding 300ms total |

---

### 3.2 Performance Constraints (Anti-Overengineering & Rendering Efficiency)
1. **Zero Layout Thrashing:** All animated components must be isolated to GPU composite layers (`transform`, `opacity`). Never animate layout geometry (`height`, `top`, `left`, `margin`).
2. **Backdrop Filter Restrictions:** `backdrop-filter: blur(...)` is strictly prohibited on scrollable lists, large table containers, or frequently updating elements. Blur is restricted exclusively to static navigation headers (`header.portal-header` with max `blur(8px)`).
3. **Zero Floating Decorative Spam:** Particle canvases, floating background stars, falling confetti, or unconstrained looping CSS keyframe animations are strictly forbidden.
4. **Hardware Acceleration Contract:** Elements with sliding transitions must declare `transform: translateZ(0)` to prevent CPU rasterization stalls on budget Android/iOS mobile devices.

---

### 3.3 Accessible Motion (`prefers-reduced-motion`)

All CSS transitions and animations must strictly respect the user's OS accessibility settings:

```css
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}
```

---

## 4. Locale Purity Contract

### 4.1 Core Locales Supported
1. `vi` — **Tiếng Việt** (Default, 100% authoritative primary language).
2. `en` — **English** (International secondary language).
3. `zh` — **中文** (Auxiliary tertiary language).

---

### 4.2 Absolute Purity Rules
1. **Zero Raw English in Vietnamese Mode (`vi`):**
   - Every label, button, badge, header, tooltip, modal, error message, and placeholder must be 100% natural Vietnamese.
   - Forbidden terms in VI mode: `"Submit"`, `"Cancel"`, `"Save changes"`, `"Created at"`, `"Action"`, `"Status"`, `"Back"`, `"Search..."`.
   - Authorized translations: `"Xác nhận"`, `"Hủy bỏ"`, `"Lưu thay đổi"`, `"Thời gian tạo"`, `"Thao tác"`, `"Trạng thái"`, `"Quay lại"`, `"Tìm kiếm..."`.
2. **Zero Vietnamese in English Mode (`en`):**
   - In `en` mode, all Vietnamese terms must have full English parity.
   - Forbidden in EN mode: `"Xu"`, `"Tạo video"`, `"Đang xử lý"`, `"Lỗi kết nối"`.
   - Authorized: `"Coins / Credits"`, `"Create Video"`, `"Processing"`, `"Connection Error"`.
3. **Zero Raw Translation Keys:**
   - Raw dictionary identifiers like `PORTAL.NAV.DASHBOARD` or `ERR_GATEWAY_TIMEOUT` must **NEVER** be displayed to the user.
   - Every key must resolve to an exact localized string; if missing, a logged fallback string with clear meaning must be rendered, and a telemetry warning triggered.
4. **Number, Date & Currency Formatting:**
   - `vi`: Currency format `100.000 Xu` or `100.000 đ`; Date format `DD/MM/YYYY HH:mm`.
   - `en`: Currency format `100,000 Coins`; Date format `MM/DD/YYYY hh:mm A`.

---

### 4.3 Automated Verification Gate
In CI/CD quality pipelines, an automated audit script (`pytest tests/test_v3_locale_purity_contracts.py`) must parse all template files, JavaScript dictionaries, and rendered DOM elements to verify zero raw untranslated tokens. Any violation immediately breaks the build (`BUILD != PASS`).
