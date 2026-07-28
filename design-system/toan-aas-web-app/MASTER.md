# Design System Master File

> **LOGIC:** When building a specific page, first check `design-system/pages/[page-name].md`.
> If that file exists, its rules **override** this Master file.
> If not, strictly follow the rules below.

---

**Project:** TOAN AAS Web App
**Generated:** 2026-07-18 14:18:24
**Category:** Productivity Tool
**Design Dials:** Variance 4/10 (Balanced / Modern) | Motion 3/10 (Subtle) | Density 8/10 (Dense / Dashboard)

---

## Project implementation override (authoritative)

The generated search result is useful for type scale, density, motion and
accessibility, but its landing-page pattern and purple/pink palette do not fit
the signed TOAN AAS application. The following decisions override it for the
portal implementation:

- **Product mode:** application-first AI productivity workspace and ERP, not a
  conversion landing. `/welcome` is the only public introduction; app root
  opens login/dashboard.
- **Style:** Swiss Modernism 2.0 + flat productivity UI: strict layout,
  semantic surfaces, one accent, limited decoration and high contrast.
- **Theme:** light cyan application canvas with white working surfaces. The
  deep teal rail is reserved for desktop navigation; primary actions are dark
  teal, mint is brand support, and sky blue communicates focus and context.
  No AI-purple/pink gradient treatment in workspace, account, billing or ERP
  screens.
- **Palette:** application canvas `#f4fbfc`; working surface `#ffffff`; deep
  teal rail and ink `#083344`; primary/action `#0f766e` with white action
  text; mint brand `#14b8a6`; sky context/focus `#0284c7`; muted text
  `#486b75`; border `#d7ecef`; danger `#b91c1c`.
- **Content density:** compact but readable: body 14–16px, 4/8px spacing
  rhythm, 40px desktop and 44px mobile controls; no operational copy below
  12px where it is needed to make a decision.
- **Motion:** 150–220ms opacity/transform only; no decorative infinite
  animation; respect `prefers-reduced-motion`.
- **Icons:** consistent accessible vector treatment for new structural UI;
  status also has textual labels.
- **Token ownership:** `static/portal/portal-theme.css :root` is the canonical
  owner of the shared teal--sky palette and all new/rebalanced theme rules use
  `--portal-*` semantic tokens. The historical catalogue still contains raw
  legacy colours; when a legacy route is placed on a light surface, add a
  specific final-theme override instead of inheriting pale-on-dark text or
  restoring new raw page colours.
- **Surface ownership:** signed Workspace, ERP, account operations and access
  screens use the light canvas and white surface family. The desktop sidebar
  alone uses the deep teal rail; `/welcome` follows the same calm public
  companion palette. All surfaces share the dark-teal action and sky context
  tokens.

The companion implementation guide is
[`docs/UX_APP_FIRST_REDESIGN.md`](../../docs/UX_APP_FIRST_REDESIGN.md).

---

## Global Rules

### Color Palette

| Role | Hex | CSS Variable |
|------|-----|--------------|
| Primary action | `#0F766E` | `--portal-action` |
| On action | `#FFFFFF` | `--portal-on-action` |
| Mint brand | `#14B8A6` | `--portal-brand` |
| Sky context / focus | `#0284C7` | `--portal-context` / `--portal-focus` |
| App canvas | `#F4FBFC` | `--portal-app-canvas` |
| Working surface | `#FFFFFF` | `--portal-surface-light` |
| Deep rail / ink | `#083344` | `--portal-rail` / `--portal-ink` |
| Border | `#D7ECEF` | `--portal-border` |
| Muted | `#486B75` | `--portal-muted` |
| Destructive | `#B91C1C` | `--portal-danger` |

**Color Notes:** dark teal actions and sky-blue context are shared across
public and signed surfaces. The signed workspace is light and operational;
only its navigation rail stays deep teal. Purple/pink generation gradients are
not part of the TOAN AAS system.

### Typography

- **Heading Font:** Inter
- **Body Font:** Inter
- **Mood:** calm, technical, precise, clean, high-trust, professional, dense operational utility
- **Google Fonts:** [Inter + Inter](https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap)
- **Scale:** 12 / 14 / 16 / 20 / 28 / 40px, with headings and controls kept on
  the shared scale instead of page-specific one-off values.

**CSS Import:**
```css
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
```

### Spacing Variables

*Density: 8/10 — Dense / Dashboard*

| Token | Value | Usage |
|-------|-------|-------|
| `--space-xs` | `2px` / `0.125rem` | Tight gaps |
| `--space-sm` | `4px` / `0.25rem` | Icon gaps, inline spacing |
| `--space-md` | `8px` / `0.5rem` | Standard padding |
| `--space-lg` | `12px` / `0.75rem` | Section padding |
| `--space-xl` | `16px` / `1rem` | Large gaps |
| `--space-2xl` | `24px` / `1.5rem` | Section margins |
| `--space-3xl` | `32px` / `2rem` | Hero padding |

### Shadow Depths

| Level | Value | Usage |
|-------|-------|-------|
| `--shadow-sm` | `0 1px 2px rgba(0,0,0,0.05)` | Subtle lift |
| `--shadow-md` | `0 4px 6px rgba(0,0,0,0.1)` | Cards, buttons |
| `--shadow-lg` | `0 10px 15px rgba(0,0,0,0.1)` | Modals, dropdowns |
| `--shadow-xl` | `0 20px 25px rgba(0,0,0,0.15)` | Hero images, featured cards |

---

## Component Specs

### Buttons

```css
/* Primary Button */
.btn-primary {
  background: var(--portal-accent);
  color: var(--portal-accent-ink);
  padding: 12px 24px;
  border-radius: 8px;
  font-weight: 600;
  transition: all 200ms ease;
  cursor: pointer;
}

.btn-primary:hover {
  opacity: 0.9;
  transform: translateY(-1px);
}

/* Secondary Button */
.btn-secondary {
  background: transparent;
  color: var(--portal-info);
  border: 2px solid var(--portal-info);
  padding: 12px 24px;
  border-radius: 8px;
  font-weight: 600;
  transition: all 200ms ease;
  cursor: pointer;
}
```

### Cards

```css
.card {
  background: var(--portal-surface);
  border-radius: 12px;
  padding: 24px;
  box-shadow: var(--shadow-md);
  transition: all 200ms ease;
  cursor: pointer;
}

.card:hover {
  box-shadow: var(--shadow-lg);
  transform: translateY(-2px);
}
```

### Inputs

```css
.input {
  padding: 12px 16px;
  border: 1px solid var(--portal-light-border);
  border-radius: 8px;
  font-size: 16px;
  transition: border-color 200ms ease;
}

.input:focus {
  border-color: var(--portal-focus);
  outline: none;
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--portal-focus) 20%, transparent);
}
```

### Modals

```css
.modal-overlay {
  background: rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(4px);
}

.modal {
  background: white;
  border-radius: 16px;
  padding: 32px;
  box-shadow: var(--shadow-xl);
  max-width: 500px;
  width: 90%;
}
```

---

## Style Guidelines

**Style:** Swiss Modernism 2.0 + flat productivity UI

**Keywords:** AI workspace, deep ink-blue, teal, sky cyan, clean, structured,
high-trust, compact, responsive, professional

**Best For:** Developer tools, pro productivity apps, fintech/trading dashboards, media/streaming platforms, AI tool interfaces, high-end gaming companion apps

**Key Effects:** 150–220ms opacity/transform transitions; restrained shadows;
flat operational surfaces; no decorative infinite animation or marketing-style
glassmorphism in the signed workspace.

### Page Pattern

**Pattern Name:** AI Personalization Landing

- **Conversion Strategy:** 20%+ conversion with personalization. Requires analytics integration. Fallback for new users.
- **CTA Placement:** Context-aware placement based on user segment
- **Section Order:** 1. Dynamic hero (personalized), 2. Relevant features, 3. Tailored testimonials, 4. Smart CTA

---

## Motion ownership

`static/portal/portal-theme.css` owns the shared teal–sky motion tokens,
keyframes and reduced-motion rules. `static/portal/portal-motion.js` is the
small browser-only lifecycle utility: it may enhance a completed shell render,
but never owns routing, authority, data, storage or requests.

Route, drawer, modal, toast and status feedback use the 140/220/420ms token
family with opacity and transform only. All non-essential motion respects
`prefers-reduced-motion`; no route content depends on animation to become
visible.

Customer Workspace and Internal ERP will use distinct visual shells while
server-issued access remains canonical. Browser presentation can style an
already granted route, but cannot discover, manufacture or authorize one.

---

## Anti-Patterns (Do NOT Use)

- ❌ Complex onboarding
- ❌ Slow performance

### Additional Forbidden Patterns

- ❌ **Emojis as icons** — Use SVG icons (Heroicons, Lucide, Simple Icons)
- ❌ **Missing cursor:pointer** — All clickable elements must have cursor:pointer
- ❌ **Layout-shifting hovers** — Avoid scale transforms that shift layout
- ❌ **Low contrast text** — Maintain 4.5:1 minimum contrast ratio
- ❌ **Instant state changes** — Always use transitions (150-300ms)
- ❌ **Invisible focus states** — Focus states must be visible for a11y

---

## Pre-Delivery Checklist

Before delivering any UI code, verify:

- [ ] No emojis used as icons (use SVG instead)
- [ ] All icons from consistent icon set (Heroicons/Lucide)
- [ ] `cursor-pointer` on all clickable elements
- [ ] Hover states with smooth transitions (150-300ms)
- [ ] Light mode: text contrast 4.5:1 minimum
- [ ] Focus states visible for keyboard navigation
- [ ] `prefers-reduced-motion` respected
- [ ] Responsive: 375px, 768px, 1024px, 1440px
- [ ] No content hidden behind fixed navbars
- [ ] No horizontal scroll on mobile
