# Mobile Responsive Fix — Dashboard & Practice Page

## Problem

Two pages in the dashboard are not usable on iPhone screens (375px–428px). Content overflows, sections stack incorrectly, and on the practice page, elements overlap and keyboard-shortcut UI is shown despite being irrelevant on mobile.

## Files to Fix

1. **`/home/ubuntu/dashboard/templates/dashboard.html`** — Main dashboard page
2. **`/home/ubuntu/dashboard/static/esat/index.html`** — ESAT practice page

## Page 1: Main Dashboard (`dashboard.html`)

### Current State
- Has a `viewport` meta tag ✅
- Has `@media (max-width: 768px)` (tablet) and `@media (max-width: 480px)` (iPhone) breakpoints
- BUT these breakpoints only adjust padding, font sizes, and basic layout — they do NOT handle the actual content sections properly

### Issues Reported
- **Stats section** (knowledge map, daily streak, average time, etc.) — stat cards are pushed off to the right, not visible
- **"Ready to Practice" card** — overflowed off the right edge, invisible on iPhone

### What to Fix
1. Identify the stats grid layout (likely `display: flex` or `display: grid` with fixed-width columns) and make it stack to single-column on mobile (≤480px)
2. Ensure the "Ready to Practice" CTA card fits within viewport — should be full-width, not offset
3. The `gridTemplateColumns: "300px 1fr"` layout (the two-column "Needs Attention" / "Knowledge Map" grid at ~line 1216) must collapse to single-column on mobile
4. The stats cards section needs to wrap or stack vertically — no horizontal overflow
5. The quota bar in the header area should remain functional (it already has 480px styles, verify it works)
6. Test: nothing should cause horizontal scrollbar on 375px viewport (iPhone SE)

### Approach
- Add a `@media (max-width: 480px)` block that handles the specific content sections the existing breakpoints miss
- Use `flex-wrap: wrap`, `grid-template-columns: 1fr`, and `width: 100%` / `max-width: 100%` as needed
- Any element with a fixed pixel width > 375px must get a responsive override

---

## Page 2: ESAT Practice Page (`static/esat/index.html`)

### Current State
- Has a `viewport` meta tag (need to verify — if missing, add it)
- Has **ZERO** `@media` queries — completely unresponsive
- This is a React app (minified/compiled JSX) with inline styles

### Issues Reported
- Elements overlap on iPhone
- Keyboard shortcut indicators are visible (irrelevant on mobile — touch-only interface)

### What to Fix
1. **Add responsive CSS** at the bottom of the `<style>` block:
   - Breakpoint at 768px (tablet) and 480px (iPhone)
   - The stats grid (`STATS.map` around line 1136) must stack vertically on mobile
   - The two-column layout (`gridTemplateColumns: "300px 1fr"` around line 1216) must collapse to single-column
   - The main content area (`maxWidth: 1120, padding: "2rem 2rem 3rem"`) needs smaller padding on mobile
   - The "Ready to practise?" card and CTA must fit within viewport

2. **Hide keyboard shortcut UI on mobile**:
   - The "Keyboard-first" tag in the pill badges (line ~1340) should be hidden on touch devices
   - The `keydown` event listener (line ~1549) is harmless but the UI labels referencing keyboard shortcuts should be hidden via `@media (max-width: 768px) { .keyboard-only { display: none } }` or similar
   - Add a CSS class (e.g., `keyboard-only`) to elements that show keyboard shortcut hints and hide them on narrow screens

3. **Fix overlapping elements**:
   - Likely caused by fixed/absolute positioning or elements with widths larger than the viewport
   - The header area (streak badge, user icon) needs to wrap properly
   - Ensure no `overflow: hidden` containers clip content unexpectedly

### Approach
Since this is compiled React with inline styles, the cleanest approach is:
- Add a `<style>` block at the end of `<head>` with responsive overrides using class names and element selectors
- Add appropriate CSS classes to elements where needed (or use element-type selectors if class names are unavailable in the compiled output)
- For the `STATS` cards and two-column grids, override the inline `display` and `grid-template-columns` via CSS selectors targeting the container divs
- Use `!important` where necessary to override inline React styles (this is acceptable for responsive overrides in a compiled build)

### Critical Constraint
- This is a **compiled/minified single-file React app**. Do NOT try to refactor it into separate components or add a build pipeline. Add responsive CSS only.
- The "Keyboard-first" pill badge and any keyboard shortcut indicators must be `display: none` on screens ≤ 768px

---

## Testing

After making changes, verify by viewing both pages at 375px width. The dashboard runs at `http://127.0.0.1:5000/` (or whatever port it's on). You can use the browser automation tool to take screenshots at mobile viewport width, or check manually.

Minimum verification:
- No horizontal scrollbar at 375px on either page
- All content visible without horizontal scrolling
- No overlapping elements on practice page
- No keyboard shortcut UI visible on mobile
- Stat cards, knowledge map, "Ready to Practice" all visible and readable
