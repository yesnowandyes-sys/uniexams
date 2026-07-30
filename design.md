# ESAT Gymnasium — Design Reference

*Condensed technical spec for implementation. For full rationale, see `DESIGN_PHILOSOPHY.md`.*

---

## Fonts

| Font | Weights | Usage |
|---|---|---|
| **Inter** | 400, 500, 600, 700 | All UI text, body copy, labels, buttons, navigation |
| **Instrument Serif** | italic only | Wordmark "Gymnasium" — nowhere else |
| **JetBrains Mono** | 500, 600, 700 | ALL numerical data (timers, scores, stats, percentages, question numbers) |

**Never add a fourth font.**

Google Fonts import:
```
@import url('https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@1&family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@500;600;700&display=swap');
```

---

## Type Scale

| rem | px | Usage |
|---|---|---|
| 0.625 | 10 | KBD badge labels only |
| 0.6875 | 11 | Label component (all-caps eyebrow), countdown sub-label — **minimum size** |
| 0.75 | 12 | Tertiary metadata, delta badges, bar labels |
| 0.8125 | 13 | Nav items, button text, topic names, sidebar labels |
| 0.875 | 14 | Body copy, answer options, hint/solution text |
| 0.9375 | 15 | Question text, card headings (h3) |
| 1.1 | ~18 | CTA heading |
| 1.125 | 18 | Countdown date, avg-score badge |
| 1.625 | 26 | Page heading |
| 1.875 | 30 | Stat card primary value |
| 3.75 | 60 | Countdown days remaining |

**Line heights:** Labels/data: 1. Buttons/nav: 1–1.3. Body/answers: 1.6. Question text: 1.85.

**Letter spacing:** Page heading `-0.025em`. "ESAT" acronym `0.07em`. Label component `0.08em`.

---

## Colour Palette

### Base
```
bg:   #F6F5F1  Background (barely warm white)
surf: #FFFFFF  Cards/surfaces
alt:  #EFECEA  Subtle fills, hover states, alternate surfaces
bdr:  #E3E0DA  Standard border
bdr2: #C9C6C0  Stronger border (KBD keys, focused inputs)
text: #18181A  Primary text (near-black, warm undertone)
sec:  #504F4C  Secondary text
ter:  #9E9C98  Tertiary text, placeholders
```

### Brand Blue
```
blue:  #1A47B8  Structural authority (logo, countdown, Gymnasium Lane)
mid:   #2563EB  Interactive elements (CTAs, hover, active states)
lite:  #EEF4FF  Blue tint fill (hover backgrounds, info panels)
liteb: #DBEAFE  Blue tint border
```

### Semantic (never used decoratively)
```
Green:  #15803D / #F0FDF4 / #86EFAC  — correct, strong (>75%), positive delta
Red:    #DC2626 / #FEF2F2 / #FECACA  — incorrect, weak (<55%), errors
Amber:  #B45309 / #FFFBEB / #FDE68A  — hint, medium (55-75%), Medium difficulty
Purple: #7C3AED / #F5F3FF / #DDD6FE  — Very Hard difficulty only
```

### Difficulty mapping
```
Easy:      Green
Medium:    Amber
Hard:      Red
Very Hard: Purple
```

---

## Shadows

```
card:   0 1px 2px rgba(0,0,0,0.05), 0 1px 4px rgba(0,0,0,0.03)
lifted: 0 3px 10px rgba(0,0,0,0.07), 0 1px 3px rgba(0,0,0,0.04)
blue:   0 4px 14px rgba(37,99,235,0.22), 0 1px 3px rgba(37,99,235,0.12)
```

Shadows create depth (layering) rather than borders (containment).

---

## Spacing

**4px base grid.** All margins, padding, gaps must be multiples of 4.

```
4  · 8  · 12  · 16  · 20  · 24  · 28  · 32
```

---

## Content Width

- **Dashboard:** max-width 1120px, padding 2rem 2rem 3rem
- **Practice Hub:** max-width 1200px, padding 1.5rem 1.75rem

---

## Buttons

**Primary** (`.btn-primary`): bg `#2563EB`, white text, no border, radius 10px, padding 0.75rem 1.25rem, font 0.9rem/600. Hover: brightness(1.07), blue shadow, translateY(-1px). Only one per view.

**Ghost** (`.btn-ghost`): bg white, 1px border `#E3E0DA`, text `#504F4C`. Hover: bg `#EFECEA`, border `#C9C6C0`.

No third button type. No red button variant.

---

## Icons

- **Source:** Heroicons outline, 24×24 viewBox
- **Default stroke-width:** 1.6px
- **Linecap/linejoin:** round
- **fill:** none (except play button: solid white)
- Stroke weights by context: nav 1.6, buttons 1.8, card headers 1.8, pills 2.0, navigator tick/cross 2.5
- **No emoji. Ever.**

---

## Key Components

### Gymnasium Lane
`borderLeft: 5px solid #2563EB` + `borderRadius: 0 12px 12px 0` — question cards ONLY.

### Answer Options
Three zones: letter badge (28×28px) → text → indicator circle (22×22px, post-answer only). After selection: disabled, cursor default. No re-clicking.

### KBD Component
JetBrains Mono 0.625rem, 1px border with 2px bottom border (key cap effect).

### Pill Badge
Height 22px, radius 5px, 0.6875rem font, weight 600.

### Arc Timer
SVG circle, rotates -90°, depletes from 12 o'clock. Colour: green >55s → amber 22-55s → red <22s. Pulse animation under 20s.

### Bar Component
Height 3px default. Fill transition: `0.55s cubic-bezier(0.16,1,0.3,1)`.

---

## Layout

### Dashboard
- Row 0: Countdown banner (full width)
- Row 1: `1fr 256px` — Knowledge Map + Stat Cards
- Row 2: `300px 1fr` — Needs Attention + CTA

### Practice Hub
- `flex: 1 1 0` (question pane, minWidth 0) + `width: 268px, flexShrink: 0` (sidebar)
- Sticky header with keyboard legend + progress dots + 2px progress stripe

---

## Animations

| Animation | Duration | Easing | Usage |
|---|---|---|---|
| Progress fill | 0.45–0.55s | `cubic-bezier(0.16,1,0.3,1)` | Bars, progress stripe, arc timer |
| Colour/hover | 0.1–0.12s | ease | Hover states |
| Timer colour | 0.3–0.5s | ease | Timer colour transitions |
| Pulse | 2s | ease-in-out, infinite | Streak dot, "now practising" dot |
| Spinner | 0.7s | linear, infinite | Loading state |
| Urgent timer | 0.9s | ease-in-out, infinite | Timer text <20s (opacity 1→0.55) |

**No animation on:** question card appear, answer option selection, page transitions.

---

## Hard Rules

1. Never add a fourth font
2. All numerical data uses JetBrains Mono — no exceptions
3. Semantic colours are never decorative
4. Gymnasium Lane is question cards only
5. No emoji
6. All interactive elements need hover states
7. Minimum text size: 11px (0.6875rem)
8. Icons from Heroicons outline only (24×24 viewBox)
9. All spacing multiples of 4px
10. The question is always the most visually prominent element on the Practice Hub
