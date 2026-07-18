---
name: "algo-bounty-style"
description: "Living design system for AlgoBounty — design tokens, typography, color palette, component patterns, accessibility heuristics, and asset guidelines. Maintained by the UX researcher skill."
---

# AlgoBounty Design System & Style Guide

> **Living Document** — This file is the canonical source of truth for the AlgoBounty visual language. It is read by `proxy-user-experience` during test execution and **updated by `algo-bounty-user-experience`** when UX audits surface style inconsistencies, missing patterns, or accessibility regressions.

## 1. Design Tokens

All tokens are defined in `dashboard/src/app/globals.css` under both the `@theme` block (Tailwind) and `:root` (CSS custom properties). Always keep both in sync.

### 1.1 Colors

| Token | Value | Usage |
|---|---|---|
| `--color-bg` | `#070712` | Page background — near-black with a blue undertone |
| `--color-surface` | `rgba(12, 12, 28, 0.8)` | Card/panel backgrounds — translucent for glassmorphism |
| `--color-surface-2` | `rgba(255, 255, 255, 0.04)` | Subtle secondary surfaces (hover states, alternating rows) |
| `--color-border` | `rgba(255, 255, 255, 0.07)` | Default border — barely visible separation |
| `--color-border-2` | `rgba(255, 255, 255, 0.12)` | Emphasized border — interactive element boundaries |
| `--color-text-primary` | `#f1f5f9` | Primary text — slate-100 equivalent |
| `--color-text-secondary` | `#94a3b8` | Secondary text — labels, descriptions |
| `--color-text-muted` | `#475569` | Muted text — timestamps, metadata |
| `--color-text-subtle` | `#334155` | Near-invisible text — disabled states |
| `--color-accent` | `#6366f1` | Primary accent — indigo-500, buttons, links, focus rings |
| `--color-accent-2` | `#8b5cf6` | Secondary accent — violet-500, gradients, highlights |
| `--color-success` | `#10b981` | Success states — approved, completed, connected |
| `--color-warning` | `#f59e0b` | Warning states — sandbox/localnet badge, pending |
| `--color-error` / `--color-danger` | `#ef4444` | Error states — failed, rejected, disconnected |
| `--color-info` | `#22d3ee` | Informational — tips, help text, cyan highlights |

### 1.2 Typography

| Font | Stack | Weight Range | Usage |
|---|---|---|---|
| **Inter** | `'Inter', system-ui, -apple-system, sans-serif` | 300–900 | All UI text. Loaded via `next/font/google` with CSS variable `--font-inter` |
| **JetBrains Mono** | `'JetBrains Mono', 'Courier New', monospace` | 400–600 | Code blocks, wallet addresses, bounty IDs, transaction hashes |

**Type Scale** (observed from components):
- Hero headings: `2.25rem` / font-weight 800
- Section headings: `1.25rem` / font-weight 700
- Card titles: `1.0625rem` / font-weight 600
- Body text: `0.9375rem` / font-weight 400, line-height 1.6
- Labels/metadata: `0.8125rem` / font-weight 500
- Captions/badges: `0.75rem` / font-weight 600–700
- Micro text: `0.6875rem` / font-weight 700, letter-spacing `0.04em`

### 1.3 Spacing & Radii

| Token | Value | Usage |
|---|---|---|
| `--radius-sm` | `0.5rem` (8px) | Small interactive elements, tags |
| `--radius-md` | `0.75rem` (12px) | Buttons, inputs, small cards |
| `--radius-lg` | `1rem` (16px) | Cards, panels |
| `--radius-xl` | `1.25rem` (20px) | Modals, large containers |
| Pill radius | `9999px` | Badges, network indicator |

### 1.4 Shadows & Effects

| Token | Value | Usage |
|---|---|---|
| `--shadow-card` | `0 8px 32px rgba(0,0,0,0.35)` | Card elevation |
| `--shadow-glow` | `0 0 40px rgba(99,102,241,0.1)` | Accent glow on focus/hover |
| Hover card shadow | `0 12px 40px rgba(0,0,0,0.4), 0 0 0 1px rgba(99,102,241,0.1)` | Bounty card hover |
| Dropdown shadow | `0 20px 60px rgba(0,0,0,0.6)` | Wallet dropdown, popovers |
| `backdrop-filter` | `blur(24px)` | Glassmorphism on dropdowns/modals |

### 1.5 Background Texture

The page body uses a composite background:
1. Radial gradient: `ellipse 80% 50% at 50% -10%` with `rgba(99,102,241,0.12)` → creates a soft indigo glow at the top
2. Grid overlay: Two perpendicular `linear-gradient` lines at `rgba(255,255,255,0.015)`, `40px` spacing — creates a subtle engineering grid

## 2. Component Patterns

### 2.1 Component Inventory

| Component | File | Key IDs/Classes | Notes |
|---|---|---|---|
| `DashboardLayout` | `components/DashboardLayout.tsx` | `nav-marketplace`, `nav-create`, `nav-profile`, `nav-docs` | Full-width header with logo, nav, wallet connect |
| `WalletConnect` | `components/WalletConnect.tsx` | `wallet-connect-btn`, `connect-pera`, `connect-defly`, `connect-exodus` | Dropdown wallet selector with colored indicators |
| `BountyCard` | `components/BountyCard.tsx` | `.bounty-card` class | Animated card with hover lift, status badges |
| `NotificationsDrawer` | `components/NotificationsDrawer.tsx` | — | Slide-in drawer with unread count badge |
| `Modal` | `components/ui/Modal.tsx` | — | WCAG 2.1 AA modal: focus trap, Escape key, ARIA |
| `FeeBreakdownTable` | `components/ui/FeeBreakdownTable.tsx` | — | Responsive fee split visualization |
| `Button` | `components/ui/Button.tsx` | — | Variants: `primary`, `secondary`, `ghost`, `danger` |

### 2.2 Interaction Patterns

- **Card hover**: `translateY(-2px)` with border glow transition (`0.3s ease`)
- **Page entrance**: `fadeIn` animation (`0.35s ease`) — opacity 0→1, translateY 8→0
- **Slide-in elements**: `slideInRight` (20px) or `slideInUp` (16px)
- **Loading spinners**: `spin 0.7s linear infinite` on a 14px circle with accent color top-border
- **Shimmer loading**: `shimmer` animation, `-400%` to `400%` background-position

### 2.3 Surface Pattern (Glassmorphism)

Glassmorphism surfaces follow this recipe:
```css
background: rgba(10, 10, 20, 0.98);    /* near-opaque dark */
backdrop-filter: blur(24px);
border: 1px solid rgba(255, 255, 255, 0.1);
border-radius: var(--radius-xl);
```

For lighter surfaces (cards within panels):
```css
background: var(--color-surface);       /* rgba(12, 12, 28, 0.8) */
border: 1px solid var(--color-border);  /* rgba(255, 255, 255, 0.07) */
border-radius: var(--radius-lg);
```

## 3. Accessibility Heuristics (WCAG 2.1 AA)

### 3.1 Mandatory Requirements (per Constitution §12.1)

| Criterion | Standard | Current Status |
|---|---|---|
| Color contrast (text) | ≥ 4.5:1 normal, ≥ 3:1 large | `--color-text-primary` on `--color-bg`: ~15:1 ✓ |
| Color contrast (interactive) | ≥ 3:1 against adjacent colors | `--color-accent` on `--color-bg`: ~4.2:1 ✓ |
| Focus indicators | Visible 2px outline | `:focus-visible { outline: 2px solid rgba(99,102,241,0.6) }` ✓ |
| Keyboard navigation | All interactive elements reachable | Modal focus trap implemented ✓ |
| Touch targets | ≥ 44×44px on mobile | Verify on all buttons and links |
| Screen reader labels | ARIA labels on icon-only buttons | Verify on notification bell, mobile menu |
| Motion sensitivity | `prefers-reduced-motion` | **NOT YET IMPLEMENTED** — needs `@media` query |

### 3.2 Heuristic Evaluation Checklist

When auditing any page, check:
1. **Perceivable**: Can all information be perceived? (contrast, alt text, captions)
2. **Operable**: Can all functions be operated? (keyboard, timing, seizure-safe)
3. **Understandable**: Is the UI understandable? (readable, predictable, error-identified)
4. **Robust**: Is it robust enough for assistive tech? (valid HTML, ARIA roles)

## 4. Asset Sources & Usage

### 4.1 Fonts
- **Inter**: Google Fonts CDN, preconnected in `layout.tsx`. Loaded via `next/font/google` for optimal performance.
- **JetBrains Mono**: Google Fonts CDN via `@import` in `globals.css`.

### 4.2 Icons
- Currently: Inline SVG and Unicode characters (no icon library)
- Navigation icons: Emoji-style (🏪 marketplace, ✏️ create, etc.) — consider migrating to Lucide React
- Status indicators: Colored dots (8–10px circles with semantic colors)

### 4.3 Images
- **No images currently in the dashboard** — placeholder-free by design
- Logo: Text-only "AlgoBounty" with accent gradient
- Background: CSS-only (gradient + grid pattern)

### 4.4 Color Application Rules

| Context | Color | Opacity Pattern |
|---|---|---|
| Status: open | `--color-accent` | `background: {color}15`, `border: {color}30` |
| Status: claimed/submitted | `--color-warning` | Same opacity pattern |
| Status: approved/completed | `--color-success` | Same opacity pattern |
| Status: disputed/rejected | `--color-error` | Same opacity pattern |
| HITM badge | `--color-warning` | Full-strength text, muted background |
| Network badges | Context-dependent | Mainnet=green, Testnet=indigo, LocalNet=amber |

## 5. Responsive Breakpoints

| Breakpoint | Target | Key Changes |
|---|---|---|
| `< 640px` | Mobile | Single column, hamburger menu, stacked cards |
| `640–1024px` | Tablet | Two-column grid, compact nav |
| `> 1024px` | Desktop | Full layout, sidebar potential, max-width containers |

**Max content width**: `1200px` with `auto` side margins
**Content padding**: `1.5rem` (desktop), `1rem` (mobile)

## 6. Change Log

| Date | Author | Change |
|---|---|---|
| 2026-07-17 | System | Initial extraction from codebase |
| 2026-07-17 | UX Researcher | Performed styling audit; added token leakage warning (hardcoded hex vs CSS variables) |
| 2026-07-17 | UX Researcher | Resolved STYLE-001 by replacing hardcoded hexes with CSS variables across app components |
| 2026-07-17 | UX Researcher | Added navigation layout and wallet dropdown positioning rules to synchronize mock monologues with actual screenshots |

> **Note to `algo-bounty-user-experience`**: When you discover style inconsistencies, missing patterns, accessibility regressions, or new component patterns during UX audits, append findings to the relevant section above and update the Change Log. This keeps the design system in sync with reality.
