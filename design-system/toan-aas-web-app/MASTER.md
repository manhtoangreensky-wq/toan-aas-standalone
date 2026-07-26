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
- **Theme:** dark slate surfaces with a teal brand/action accent. No
  AI-purple/pink gradient treatment in workspace, account, billing or ERP
  screens.
- **Palette:** workspace background `#07141d`; surface `#0d2330`; elevated
  surface `#112b39`; primary/action `#0e9f9a`; primary ink `#06212b`; text
  `#edf8fa`; muted text `#9bb9c3`; border `#234555`; cyan context `#0284c7`;
  light public canvas `#f6fcfc`; light ink `#06212b`; danger `#e66d70`.
- **Content density:** compact but readable: body 14–16px, 4/8px spacing
  rhythm, 40px desktop and 44px mobile controls; no operational copy below
  12px where it is needed to make a decision.
- **Motion:** 150–220ms opacity/transform only; no decorative infinite
  animation; respect `prefers-reduced-motion`.
- **Icons:** consistent accessible vector treatment for new structural UI;
  status also has textual labels.

The companion implementation guide is
[`docs/UX_APP_FIRST_REDESIGN.md`](../../docs/UX_APP_FIRST_REDESIGN.md).

---

## Global Rules

### Color Palette

| Role | Hex | CSS Variable |
|------|-----|--------------|
| Primary | `#0E9F9A` | `--portal-accent` |
| On Primary | `#06212B` | `--portal-accent-ink` |
| Secondary | `#0284C7` | `--portal-info` |
| Workspace background | `#07141D` | `--portal-bg` |
| Workspace surface | `#0D2330` | `--portal-surface` |
| Public canvas | `#F6FCFC` | `--portal-light-canvas` |
| Light foreground | `#06212B` | `--portal-ink` |
| Muted | `#9BB9C3` / `#52727C` | `--portal-muted` / `--portal-light-muted` |
| Border | `#234555` / `#C7E3E6` | `--portal-border` / `--portal-light-border` |
| Destructive | `#E66D70` | `--portal-danger` |
| Ring | `#0284C7` | `--portal-focus` |

**Color Notes:** teal actions and sky-cyan context; public routes use a cool
light canvas while signed workspaces remain deep ink-blue. Purple/pink
generation gradients are not part of the TOAN AAS system.

### Typography

- **Heading Font:** Inter
- **Body Font:** Inter
- **Mood:** dark, cinematic, technical, precision, clean, premium, developer, professional, high-end utility
- **Google Fonts:** [Inter + Inter](https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap)

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
  background: #0E9F9A;
  color: #06212B;
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
  color: #0284C7;
  border: 2px solid #0284C7;
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
  background: #0D2330;
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
  border: 1px solid #E2E8F0;
  border-radius: 8px;
  font-size: 16px;
  transition: border-color 200ms ease;
}

.input:focus {
  border-color: #0284C7;
  outline: none;
  box-shadow: 0 0 0 3px rgb(2 132 199 / 20%);
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

## Motion

**Scroll Reveal** (Subtle) — Trigger: scroll (viewport enter) | Duration: 300-400ms | Easing: `power1.out`

```js
gsap.from(el, { opacity: 0, y: 12, duration: 0.35, ease: 'power1.out', scrollTrigger: { trigger: el, start: 'top 90%', toggleActions: 'play none none reverse' } });
```

**Framework notes:** Requires the ScrollTrigger plugin registered once via gsap.registerPlugin(ScrollTrigger)

- ✅ Keep the y offset small (8-16px) so it reads as a fade, not a slide
- ❌ Don't reveal below-the-fold content needed for SEO/crawlers as invisible-by-default without a no-JS fallback
- ⚡ toggleActions 'play none none reverse' avoids re-triggering on every scroll direction change

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
