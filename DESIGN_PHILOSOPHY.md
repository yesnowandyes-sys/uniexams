# ESAT Gymnasium — Design Philosophy

*A complete reference for anyone building on or modifying this codebase. Every decision documented here was deliberate. If you are tempted to change something, read its entry first — there is usually a reason that isn't immediately obvious.*

---

## 1. Who This Platform Is For

ESAT Gymnasium is a high-stakes exam preparation tool for 17–18 year olds applying to Cambridge, Imperial College, and UCL. These students are some of the highest-achieving in the country. They are not casual learners dabbling in a hobby — they are under genuine pressure, with university offers depending on their performance.

This context shapes every design decision. The interface must feel:

- **Serious, not playful.** Duolingo's owl and cartoon animations would feel condescending to a student who is genuinely anxious about an admissions test. We borrow Duolingo's structural ideas (streaks, progress, gamified feedback) but none of its visual register.
- **Reliable and unbreakable.** The platform must feel robust. Every button, every state, every edge case should look designed. Nothing should look like it was forgotten. When a student is stressed about a question, a janky UI adds cognitive load and erodes trust.
- **Focused.** The question is the product. Everything else — stats, sidebars, navigation — is support infrastructure. Visual hierarchy must always make the question the most prominent element on the practice page.
- **Fast to operate.** Students doing timed practice cannot afford to reach for the mouse. The entire Practice Hub is operable from the keyboard. This is not a nice-to-have; it is a core product requirement.

---

## 2. The Governing Philosophy: Precision Instrument

The ESAT Gymnasium should feel like a well-made instrument — like a good scientific calculator or a precision stopwatch. Not cold or clinical, but purposeful and exact. Every element should feel like it was put there deliberately, with no decoration added for its own sake.

The three platforms that most informed this direction were:

- **Linear** — for its discipline with information density, monospace data rendering, and the feeling that nothing is out of place
- **Khan Academy** — for its commitment to clarity in educational content and its restraint with visual noise during active learning
- **Quizlet** — for its clean card-based question presentation and the way it uses colour only semantically (green for correct, red for wrong, not decoratively)

We explicitly rejected the aesthetic of Duolingo (too playful), Notion (too grey and corporate), and most edtech platforms (too reliant on stock-photography splash screens and gradient everything).

---

## 3. Typography

Typography carries more of the design than any other single decision. Getting it wrong — using one font for everything, or using the wrong weight for a data value — undermines the entire platform's credibility.

### 3.1 The Three-Font System

**Inter** — all UI text, body copy, labels, buttons, navigation, form elements.

Inter was chosen over alternatives (Plus Jakarta Sans, DM Sans, Geist) for several reasons specific to a learning platform:
- Its letterforms at 13–15px are exceptionally clean, which matters when a student is reading long question text under time pressure.
- Its tabular numerals option means that changing numbers (timers, scores) do not cause layout shift.
- It is the de facto standard for serious software interfaces (Linear, Vercel, Notion all use it). This familiarity lowers cognitive overhead for the student — they are not spending processing power decoding an unusual typeface.
- Weights 400, 500, 600, and 700 all look meaningfully distinct, giving four usable levels of emphasis.

**Instrument Serif (italic only)** — the word "Gymnasium" in the wordmark, and nowhere else.

The contrast between the technical acronym "ESAT" in Inter Bold and the humanist italic "Gymnasium" in Instrument Serif communicates the platform's character in a single glance: rigorous and systematic (the exam), but also classical and aspiring (the place of learning). The italic specifically — not the roman — was chosen because italic serifs carry a historical association with handwritten scholarship and academic tradition that the roman does not. Using it *only* in the wordmark is intentional; it would look affected and inconsistent anywhere else.

**JetBrains Mono** — all numerical data throughout the interface.

Every percentage, score, timer, countdown, stat value, and question number uses JetBrains Mono. This decision serves three purposes:

1. **Legibility under time pressure.** When a student glances at the timer, they need to read it in under 100ms. The monospace construction of JetBrains Mono, with its tall x-height and wide apertures, makes individual digits easier to parse than proportional fonts.
2. **Tabular alignment.** Because all digits in a monospace font are the same width, numbers in a column (the topic strength percentages in the sidebar, for example) align perfectly without any additional CSS — each percentage occupies the same visual space.
3. **Semantic clarity.** When the brain sees JetBrains Mono, it reads data. When it sees Inter, it reads language. Separating these two reading modes — even subtly — reduces cognitive load by signalling what kind of information is being presented before the content is processed.

### 3.2 The Type Scale

All sizes are expressed in `rem` rather than `px` to respect user browser settings. The scale is:

| Token | Rem | Px equiv | Usage |
|---|---|---|---|
| `0.625rem` | — | 10px | KBD badge labels only |
| `0.6875rem` | — | 11px | `Label` component (all-caps eyebrow text), countdown sub-label |
| `0.75rem` | — | 12px | Tertiary metadata, delta badges, bar chart labels, progress counts |
| `0.8125rem` | — | 13px | Navigation items, button text, topic names, sidebar labels, secondary UI |
| `0.875rem` | — | 14px | Body copy, answer option text, hint/solution text, stat units |
| `0.9375rem` | — | 15px | Question text, card headings (`h3`) |
| `1.1rem` | — | ~18px | CTA heading |
| `1.125rem` | — | 18px | Countdown date, avg-score badge |
| `1.625rem` | — | 26px | Page heading ("Good morning, Alex.") |
| `1.875rem` | — | 30px | Stat card primary value |
| `3.75rem` | — | 60px | Countdown days remaining |

The minimum size in the UI is 11px (`0.6875rem`). Nothing goes below this. Anything rendered smaller than 11px requires the user to strain to read it, which is inappropriate in an educational context where information must be absorbed quickly and accurately.

**Line heights** follow the principle that longer text blocks need more breathing room:
- Single-line labels and data: `lineHeight: 1`
- Short UI labels (buttons, nav): `lineHeight: 1` to `1.3`
- Body text and answer options: `lineHeight: 1.6`
- Question text: `lineHeight: 1.85` — the highest on the page, because questions often contain mathematical notation and complex phrasing that requires careful reading

**Letter spacing** is applied where meaningful:
- Tight negative tracking (`-0.025em`) on the page heading — large type at 700 weight benefits from this to avoid the letters feeling overly spaced
- `0.07em` positive tracking on the "ESAT" acronym in the wordmark, because spaced capital letters read better at small sizes
- `0.08em` tracking on the `Label` component (all-caps eyebrow text) — all-caps text always needs positive tracking to remain legible

---

## 4. Colour System

### 4.1 The Base Palette

```
C.bg = #F6F5F1 Background — barely warm white
C.surf = #FFFFFF Card / surface — pure white
C.alt = #EFECEA Subtle fills (hover states, inactive areas, alternate surfaces)
C.bdr = #E3E0DA Standard border
C.bdr2 = #C9C6C0 Stronger border (KBD keys, focused inputs)
C.text = #18181A Primary text — near-black with the faintest warm undertone
C.sec = #504F4C Secondary text — warm mid-grey
C.ter = #9E9C98 Tertiary text — muted labels, placeholders
```

The background is not pure white (`#FFFFFF`) and not a heavy cream. `#F6F5F1` is a deliberate "barely warm white" — the difference from pure white is invisible on casual inspection but eliminates the harshness that pure white creates on modern high-brightness screens. Students spend extended sessions on this platform; a neutral slightly warm background reduces eye strain over time compared to clinical white. It also makes the pure-white cards pop with a very gentle depth relationship.

The text colours follow a three-tier warm-grey scale rather than black. `#18181A` (primary) has a faint warm undertone that harmonises with the background, avoiding the jarring contrast of pure black on off-white. The warm undertone matters because the entire palette has a warm bias — mixing cool greys into a warm palette creates visual inconsistency that registers subconsciously.

### 4.2 Brand Blue

```
C.blue = #1A47B8 Deep navy — brand authority, primary backgrounds
C.mid = #2563EB Interactive blue — hover targets, active states, CTA buttons
C.lite = #EEF4FF Blue tint fill — hover backgrounds, info panels
C.liteb = #DBEAFE Blue tint border — goes with C.lite
```

The two-tier blue system is a deliberate separation of roles. `C.blue` (`#1A47B8`) is used for structural elements that represent authority or permanence — the logo mark, the countdown banner, the question card's "Gymnasium Lane" left border. It is a deep academic navy, closer to Cambridge blue than corporate cobalt. `C.mid` (`#2563EB`) is the interactive blue — every element the user can click or interact with uses this brighter, more immediate tone. This distinction means users can glance at any element and know whether it is structural information or an invitation to act.

### 4.3 Semantic Colours

These four systems are used exclusively for their semantic meaning. They are never used decoratively.

**Green** (`#15803D` / `#F0FDF4` / `#86EFAC`) — Correct answers, strength above 75%, positive delta values, session complete.

**Red** (`#DC2626` / `#FEF2F2` / `#FECACA`) — Incorrect answers, strength below 55%, errors, failed generation.

**Amber** (`#B45309` / `#FFFBEB` / `#FDE68A`) — The hint system, strength between 55–75%, Medium difficulty. Amber was specifically darkened to `#B45309` rather than the more common `#D97706` to meet WCAG AA contrast ratio on its light background (`#FFFBEB`). Accessibility was the deciding factor.

**Purple** (`#7C3AED` / `#F5F3FF` / `#DDD6FE`) — Very Hard difficulty exclusively. Purple was chosen because it has no overlap with the three primary semantic meanings (correct, incorrect, warning), yet reads as "high intensity" or "elevated" — appropriate for the hardest question tier.

**Difficulty colour mapping:**
```
Easy: Green — achievable, not alarming
Medium: Amber — requires attention, not anxiety
Hard: Red — challenging, heightens focus
Very Hard: Purple — exceptional, outside the normal warning spectrum
```

This mapping was chosen carefully. Hard questions using red does not mean "wrong" — the user has not answered yet. The distinction is maintained because red on the difficulty pill is contained in a very small, clearly-labelled context, and users quickly learn its meaning. The alternative (using orange for Hard) would create confusion with Medium (amber). Four distinct colours for four distinct levels is the correct choice even if it temporarily overloads the semantic meaning of red.

### 4.4 Why No Gradients (Except the Countdown)

Gradients are used in exactly one place: the countdown banner. Everywhere else in the interface, surfaces are flat. This is intentional. Gradients date quickly, are harder to maintain consistently, and — critically — they compete with content for visual attention. In a learning environment, every decorative element that draws the eye away from the question content is a small but real distraction. The countdown banner earns its gradient because it is meant to be visually prominent: it is the emotional core of the dashboard, communicating urgency about time remaining.

---

## 5. Shadows and Depth

```
SH.card = "0 1px 2px rgba(0,0,0,0.05), 0 1px 4px rgba(0,0,0,0.03)"
SH.lifted = "0 3px 10px rgba(0,0,0,0.07), 0 1px 3px rgba(0,0,0,0.04)"
SH.blue = "0 4px 14px rgba(37,99,235,0.22), 0 1px 3px rgba(37,99,235,0.12)"
```

Shadows are used to create depth rather than borders. The `SH.card` shadow is extremely subtle — barely perceptible on its own, but it lifts the card surface slightly off the background. This is preferable to using only borders because borders imply containment (this thing is separated from that thing) while shadows imply layering (this thing is above the background). Cards with content are layers. They should feel like they have physical presence.

The `SH.blue` shadow on the CTA primary button matches the button's colour. Coloured drop shadows are a detail that distinguishes professionally-crafted interfaces from templated ones. A blue button with a neutral grey shadow looks generic. A blue button with a blue shadow looks intentional. At `rgba(37,99,235,0.22)`, the shadow is not garish — it reads only subconsciously, contributing to the sense that the button has weight and presence.

---

## 6. Icons

### 6.1 Why SVG, Never Emoji

Emoji are excluded from the entire interface. This is a hard rule. The reasons:

1. **Emoji render differently across operating systems.** The flame emoji on macOS looks nothing like the flame emoji on Windows or Android. An interface that uses emoji is an interface that looks different to every user — this is a loss of design control.
2. **Emoji communicate playfulness.** In a context where a student is anxious about an admissions exam, a 🔥 streak counter reads as casual and slightly childish. A stroke-based flame SVG in the brand's amber colour reads as designed and serious.
3. **Emoji cannot be styled.** They cannot receive `color`, `stroke`, `transform`, or any CSS property. This makes it impossible to integrate them into a coherent visual system. When a stat card uses an amber icon, that icon should be in exactly the same amber as the text and background. An emoji cannot be made to do that.

### 6.2 The Icon System

All icons are SVG path data derived from the **Heroicons** outline set (24×24 viewBox). The `Svg` component renders them with these invariable parameters:

- **Stroke width: 1.6px** — thinner than Heroicons' default 1.5px, slightly heavier for small sizes. At 14px rendered size, 1.6px stroke-width gives adequate visual weight without looking clunky.
- **Stroke linecap: round** — round caps make thin icons feel friendlier and more refined than square caps. Compare `square` vs `round` on any thin-line icon at 14px and the difference is immediately visible.
- **Stroke linejoin: round** — prevents the sharp angular spikes that appear at corners with `miter` join.
- **fill: none** (default) — all icons are outline-only, except the play button which uses `fill="#fff"` and `sw={0}` to become a solid white triangle.
- **aria-hidden: true** — all icons are decorative (they are always paired with text or semantic context). Hiding them from assistive technology is correct accessibility practice; the surrounding label provides the meaning.

### 6.3 Inline SVG for Navigator Buttons

The question navigator buttons render their tick/cross as literal inline SVG, not via the `Svg` component. This is because the buttons need to render a conditional path (`M4.5 12.75l6 6 9-13.5` for check vs the two-path X) inside a very small, fixed-size space (36×36px). The `Svg` component handles this, but inline SVG gives tighter control over the exact 11px size and 2.5px stroke weight needed at this scale. Icons that appear at very small sizes (under 14px) often need their own stroke-width adjustments — the general-purpose `Svg` component uses 1.6px which is too thin at 11px.

### 6.4 Icon Sizing Guide

When adding new icons:
- **Nav items:** 14px, sw=1.6 (default)
- **Inside buttons:** 14–15px, sw=1.8 (slightly heavier to match button font weight)
- **Card section headers (alongside h3 text):** 15–16px, sw=1.8
- **Inside stat card icon boxes:** 15px, sw=1.8
- **Inside small pills / badges:** 11px, sw=2.0 (heavier to compensate for small size)
- **The navigator tick/cross:** 11px, sw=2.5 (heaviest, because meaning must be instantly legible at this size)

Never render an icon without immediately adjacent text or a very clear semantic context. Icons alone are ambiguous. The only icon used without label text is in the streak pill in the nav, where the pulsing amber dot's context (placement, colour) makes its meaning clear.

---

## 7. Spacing

All spacing follows a **4px base grid**. This means every margin, padding, and gap value should be a multiple of 4:

```
4px — micro gaps (between icon and label within a component)
8px — small gaps (between chips in a row)
12px — medium inner padding
16px — standard inner padding, gap between elements
20px — comfortable inner padding for larger components
24px — standard outer padding, card padding
28px — padding at section level
32px — `2rem` large spacing
```

**Why a 4px grid?** Without a grid, developers make arbitrary choices (17px here, 11px there) that produce an interface where nothing quite lines up. The 4px grid makes it possible for two different areas of the interface, built independently, to feel spatially coherent when placed next to each other. It is also small enough to give fine-grained control — 4px vs 8px is a meaningful difference in tight UI — while still being coarser than pixel-perfect ad-hoc values.

### 7.1 The Content Width Constraint

Dashboard: `maxWidth: 1120px`, `padding: "2rem 2rem 3rem"`.
Practice Hub: `maxWidth: 1200px`, `padding: "1.5rem 1.75rem"`.

The different max-widths are intentional. The Dashboard is an information overview — it benefits from a slightly narrower container because the eye needs to traverse the full width and tighter content is easier to scan. The Practice Hub is a two-column layout with a question pane and sidebar — it needs slightly more horizontal room to avoid the two columns feeling cramped.

Bottom padding on the dashboard (`3rem`) is larger than the top/side (`2rem`) to prevent content from feeling like it cuts off at a hard edge.

---

## 8. Layout

### 8.1 Dashboard Grid

The dashboard uses a two-row grid system:

**Row 1:** `gridTemplateColumns: "1fr 256px"` — Knowledge Map (flexible width) + Stat Cards (fixed 256px).

The stat cards column is fixed at 256px because they contain specific data at a specific size. Letting them flex would make the numbers resize unexpectedly. The Knowledge Map fills the remaining space because the radar chart and bar chart can scale.

**Row 2:** `gridTemplateColumns: "300px 1fr"` — Needs Attention (fixed 300px) + CTA (flexible).

The "Needs Attention" list is fixed-width because topic names have predictable lengths and fixed width prevents awkward wrapping. The CTA card is flexible to use whatever space remains.

The full-width Countdown banner above both rows acts as a **visual anchor** — it gives the eye a starting point and communicates the platform's core purpose (exam countdown) before any other information is processed.

### 8.2 Practice Hub Split

`flex: "1 1 0"` (question pane) + `width: 268px, flexShrink: 0` (sidebar).

The sidebar is fixed-width rather than flex-based because it contains consistent content (topic list, subject selector) that does not need to grow. Fixing it ensures the question pane always gets maximum available width, which matters because question text — particularly in mathematics — often runs long and should not be forced into a narrow column.

`minWidth: 0` on the question pane prevents flex children from overflowing their container when content (long mathematical expressions) is wider than the flex item.

### 8.3 Sticky Navigation

Both pages use `position: "sticky", top: 0, zIndex: 100`. The navigation must remain visible during scrolling because:
- On the Dashboard, the streak/avatar and nav links are persistent context.
- On the Practice Hub, the keyboard shortcut legend and session progress counter must be visible at all times. A student mid-question should not have to scroll up to remember which key triggers a hint.

The Practice Hub header also bears a `2px` session progress bar pinned to its bottom edge. This thin line fills left-to-right as questions are answered, turning green when all 10 are complete. It is borrowed from video player progress bars (YouTube, Vimeo) because the pattern is universally understood: a filling bar means forward progress. Placing it on the header means it is always visible regardless of scroll position.

---

## 9. The Gymnasium Lane

The most distinctive visual element in the Practice Hub is the question card's left border:

```
borderLeft: `5px solid ${C.mid}` (#2563EB)
borderRadius: "0 12px 12px 0"
```

This is called the **Gymnasium Lane** — a reference to athletic track lanes that guide direction and separate distinct paths. The 5px left border is intentionally wider than the card's other three borders (1px). It serves several purposes:

1. **Visual anchor.** In a two-column layout, the eye needs an immediate starting point. The strong blue left edge draws the eye directly to the question content, even when the sidebar is full of information.
2. **Brand element.** It is the signature design decision of this platform — something no generic learning platform does. It is immediately recognisable as a "ESAT Gymnasium question card."
3. **Depth device.** Paired with the card's shadow, the thick left border implies a card that is sticking out of the surface slightly at a slight angle, like a physical index card in a stack.
4. **Subject encoding potential.** The current implementation uses a single brand blue for all subjects. If ESAT Gymnasium ever adds a coloured lane per subject (blue for Maths, purple for Physics, green for Biology, etc.), this border is where that information would live, without requiring any change to the overall card structure.

---

## 10. Buttons

There are two button types in the system. Do not add a third type without a strong reason.

### 10.1 Primary Button (`.btn-primary`)

```
background: C.mid (#2563EB)
color: #fff
border: none
borderRadius: 10px
padding: 0.75rem 1.25rem
fontSize: 0.9rem, fontWeight: 600
```

CSS hover state: `filter: brightness(1.07)`, `box-shadow: 0 4px 14px rgba(37,99,235,0.28)`, `transform: translateY(-1px)`.

The `translateY(-1px)` lift on hover communicates that the button is a physical object being pressed. The brightening (`brightness(1.07)`) is preferred over darkening on hover because it maintains the colour's character while clearly signalling hover. The coloured shadow (`rgba(37,99,235,0.28)`) communicates that this button has presence in three-dimensional space — the shadow matches the object, not a neutral dark.

Used for: Start Practising, Retry, session-complete Dashboard return. Only ever used for the single most important action available in any given context. If two primary buttons appear on screen simultaneously, one of them should be demoted to ghost.

### 10.2 Ghost Button (`.btn-ghost`)

```
background: C.surf (#FFFFFF)
border: 1px solid C.bdr
color: C.sec or C.text
```

CSS hover state: `background: #EFECEA`, `border-color: #C9C6C0`.

Used for: secondary actions (Mock Exam, Clear Focus, Back navigation). The ghost button does not compete with the primary for visual attention — it is visually quieter but still clearly interactive.

### 10.3 What Not to Do

- Do not add a "danger" red button variant. Error states use red backgrounds with white text already, and placing a red primary button on screen is visually alarming and confusing in an educational context. If a destructive action needs a button, use the ghost style.
- Do not change border-radius without updating both button types simultaneously. Inconsistent corner radii between interactive elements of similar type is one of the most common markers of an unfinished interface.
- Do not put icons inside ghost buttons without very strong justification. Primary buttons use icons (play icon, pencil icon) because they benefit from visual differentiation. Ghost buttons are already recessive — adding icons makes them visually noisy.

---

## 11. Answer Options

The answer option component is the most used interactive element in the entire platform. Its design must be irreproachable.

### 11.1 Three-Zone Structure

Each option button has three zones:

```
[ A ] [ option text ] [ ✓ or ✗ ]
 badge    flex, grows    indicator
```

**Left zone — letter badge (28×28px, 7px border radius):**
- Default (unanswered): grey background (`C.alt`), grey text — deliberately recessive, so it reads as a secondary label rather than a design element
- Hover (pre-answer): fills blue (`C.mid`), white text — the badge becomes the hover signal, drawing the eye to the "which letter am I about to select" information
- Correct (post-answer): fills green (`C.green`), white text
- Incorrect selected (post-answer): fills red (`C.red`), white text
- Other options (post-answer): stays grey with reduced opacity text

**Middle zone — option text:**
- 0.875rem, lineHeight 1.6 — readable even for multi-line options
- Font weight increases from 400 to 500 for the correct answer and the selected answer after submission, to help the eye find the resolution of the question quickly

**Right zone — indicator circle (22×22px, 50% border-radius):**
- Appears only after submission
- Green filled circle + white check SVG (11px, 2.5px stroke weight) for correct
- Red filled circle + white X SVG for incorrect
- Uses inline SVG, not the `Svg` component, for precise control at this small size
- Positioned on the *right* because the eye reads left to right — the student first sees the letter, then reads the text, then arrives at the result. The result is the last thing processed, which reinforces the learning cycle.

### 11.2 Hover State Management

Hover state is split between CSS (`.opt-btn:hover` for background and border) and React state (`hovOpt`) for the letter badge colour. This split is intentional: CSS transitions are hardware-accelerated and run even if JavaScript is momentarily busy; React state allows the badge to coordinate its colour change with the button's background change for a coherent visual effect.

The `answered` CSS class disables hover effects once the user has selected an answer. This prevents the disturbing visual of options appearing to highlight after the question is resolved.

### 11.3 The Finality Rule

Once an answer is selected, options become `cursor: "default"` and the button is `disabled`. This is non-negotiable. In a real exam, you cannot change your answer by clicking again — the practice platform must simulate this psychological commitment. If users could hover and re-click freely after selecting, it would undermine the exam-pressure training that is the platform's core purpose.

---

## 12. Difficulty System

```
Easy: { bg: "#F0FDF4", col: "#15803D", bdr: "#86EFAC" } — Green
Medium: { bg: "#FFFBEB", col: "#B45309", bdr: "#FDE68A" } — Amber
Hard: { bg: "#FEF2F2", col: "#DC2626", bdr: "#FECACA" } — Red
Very Hard: { bg: "#F5F3FF", col: "#7C3AED", bdr: "#DDD6FE" } — Purple
```

The difficulty pill appears in **two places** on the Practice Hub: once in the meta row at the top, and again inside the question card. This is deliberate repetition. In the meta row it provides context before reading; inside the card it serves as a reminder during reading without requiring the student to scroll up.

The difficulty sequence across a 10-question session (`DIFF_SEQ`) follows a pattern: Easy → Medium → Medium → Hard → Medium → Hard → Hard → Very Hard → Medium → Very Hard. This is not random. The session ramps up, has a mid-session recovery question (Medium after Hard), then escalates. This mirrors real exam conditions and the psychological research on "interleaved difficulty" producing better retention than monotonic difficulty increase.

---

## 13. Progress and Time Indicators

### 13.1 The Arc Timer

The timer is rendered as a circular SVG arc that depletes as time passes:

```jsx
strokeDasharray={circ} // Full circumference
strokeDashoffset={circ * (1-pct)} // Depleting arc
```

The arc rotates -90° so it starts depleting from the 12 o'clock position (the most natural "full" position for a circular indicator). The arc is paired with a JetBrains Mono countdown text — the arc provides instant visual context (how much time is left proportionally) while the number provides precision.

Colour transitions: green (>55s) → amber (22–55s) → red (<22s). Below 20 seconds, a CSS pulse animation (`timer-urgent`) makes the text throb. This is the only animation in the interface that is purely attention-grabbing rather than informational. It is justified because 20 seconds in an ESAT context is genuinely urgent — students need to be aware that time is running out even if they are focused on a calculation.

### 13.2 Session Progress Dot Row

The 10 dots in the practice hub header provide a glanceable session map. Each dot is 6px and changes colour as questions are answered (grey → green or red). The current question's dot has a blue ring halo (`boxShadow: 0 0 0 2px C.liteb`) to clearly identify position in the session without requiring the student to count.

This is not duplicated from the question navigator buttons — the dots and the buttons serve different purposes. The dots are for a global session overview (how far through am I? what's my score so far?). The numbered buttons are for navigation (let me go back to question 4).

### 13.3 The Header Progress Bar

The 2px stripe at the bottom of the sticky Practice Hub header fills from left to right as questions are answered. It turns green when all 10 are complete. The easing function `cubic-bezier(0.16, 1, 0.3, 1)` (a spring easing) gives the fill a satisfying snap quality — it overshoots very slightly then settles. This is not gratuitous animation; it provides tactile feedback that progress has been made.

---

## 14. The Stat Cards

Each dashboard stat card has this structure:

```
[ icon box ] [ delta badge ]
[ Label ]
[ large number ] [ unit ]
```

**Icon box (30×30px, 8px border-radius):** Uses the stat's accent colour at very low opacity as background, with the icon in the full accent colour. This creates a contained colour block that is recognisable and warm without overwhelming the card.

**Delta badge:** Shows week-on-week change (`+2`, `−0:04`, `+0.3`). This is the most important UX decision on the stat cards. A number alone (12 days) is a current state. A number with a delta (`+2 days`) is a narrative — it shows trajectory, which is what motivates continued practice. Duolingo, Strava, and Notion Analytics all use deltas for exactly this reason. The delta uses `JetBrains Mono` because it is data, and it is `0.6875rem` because it must not visually compete with the primary value.

**The number:** Large `JetBrains Mono 700` in the card's accent colour. The largest text on the card. Nothing else should be this size in the card.

**Unit text:** Small, `C.ter` (tertiary grey), normal weight. It qualifies the number without drawing attention away from it.

The CSS `.stat-card:hover` lifts the card 2px and increases its shadow. This is the only place in the dashboard where hover state produces a physical effect (translate). It is appropriate here because the stat cards are informational, not interactive — the hover just provides visual engagement for a student scanning the dashboard.

---

## 15. The Knowledge Map

The radar chart was chosen over a bar chart for the five ESAT modules because radar charts communicate *shape* as well as values. A student whose scores are 67/61/71/79/50 can glance at the radar and immediately see: "I am weak in one direction (Maths 2) and strongest in another (Biology)." A bar chart would convey the same data but would not convey the spatial relationship between subjects.

The radar chart is paired with a vertical bar chart for the same data to the right. This redundancy is intentional — the radar is good for shape, the bars are good for comparison. Together they cover different reading strategies and different cognitive strengths.

The average score badge above the bars (`Math.round(RADAR_DATA.reduce(...))%`) is computed live from the data array. It gives the student a single summary number to remember, which is the number they are most likely to want to communicate ("I'm averaging 70%"). It uses JetBrains Mono at `1.125rem` — large enough to be notable but not competing with the countdown banner's massive days counter.

---

## 16. Collapsible Panels (Hint & Solution)

Both the hint and solution panels use a collapsed-by-default pattern with a single button to reveal. The decision logic:

**Hint:** Available immediately, before or after answering. Collapsed by default because seeing a hint immediately removes the productive struggle that makes learning stick. The student must actively choose to get the hint.

**Solution:** Only available after answering. Collapsed by default because the student first needs to see the correct/incorrect status, process it emotionally, and then choose to read the explanation. If the solution were auto-expanded, many students would read it without having processed the outcome of their attempt.

The collapsed button when open shows a different background colour than default:
- Hint open: `C.aLite` (amber tint) — matches the hint panel's amber theme
- Solution open: `C.lite` (blue tint) — matches the solution panel's blue theme

This means the button acts as a visual anchor for the open panel below — the eye can trace the connection between "I clicked this" and "this content appeared."

The keyboard shortcuts `H` and `S` are documented on each button via a `KBD` component on the right edge of the button. This is the only place keyboard shortcuts are shown at point of use — the global legend in the header provides the full list, but inline `KBD` badges at the exact element reinforce the habit.

---

## 17. The KBD Component

```jsx
borderBottom: `2px solid ${C.bdr2}` // thicker bottom border
```

The `KBD` component simulates a physical key cap by using a thicker bottom border (2px vs 1px on the other three sides). This mimics the raised edge of a keyboard key. It is a widely recognised pattern — GitHub uses it, Stack Overflow uses it, Linear uses it — specifically because it triggers an immediate physical association with keyboard interaction.

Font: `JetBrains Mono` at `0.625rem`. Because key labels (`H`, `S`, `1–5`, `←`, `→`) are single characters or very short strings, the mono spacing and programming-console aesthetic of JetBrains Mono makes them read as "machine labels" rather than text. This creates the correct mental model: these are codes that the keyboard interprets, not words to be read.

---

## 18. The Wordmark

```jsx
// Logo mark: 34×34px navy square, 9px border-radius
// Italic G in Instrument Serif, 1.45rem, white
<span style={{ fontFamily:'"Instrument Serif", serif', fontStyle:"italic", fontSize:"1.45rem", marginTop:1 }}>G</span>

// Name: "ESAT" in Inter 700, 0.07em tracking | "Gymnasium" in Instrument Serif italic
```

The `G` in the logo mark has `marginTop: 1` applied. This is an **optical correction** for the descender of the capital G. Instrument Serif's G has a slight visual weight at its base (the horizontal spur). Without the 1px nudge, the G appears to sit too high within its container. This kind of pixel-level optical correction is invisible when applied and conspicuous when missing — it is the difference between a mark that looks "slightly off" and one that feels settled.

The "ESAT" portion uses `letterSpacing: "0.07em"` because spaced acronyms at small sizes (0.875rem) read more clearly when letters have breathing room. Without spacing, the four capital letters compress together and read as a single opaque block. With `0.07em`, each letter is distinct.

"Gymnasium" uses `fontSize: "1.1rem"` — slightly larger than "ESAT" at `0.875rem`. The size difference creates a deliberate hierarchy: the acronym is the identifier, the full word is the character. They are aligned at their baseline (using `alignItems: "baseline"` on the flex container) so that the different sizes feel harmonious rather than misaligned.

---

## 19. Animations and Transitions

The interface uses five animation mechanisms. Each has a specific purpose.

**1. Progress fills (`cubic-bezier(0.16, 1, 0.3, 1)` — spring)**
Used on: `Bar` component, session progress stripe, `strokeDashoffset` transition on arc timer base.
Duration: 0.45–0.55s.
This easing produces a satisfying snap quality — the fill accelerates quickly and decelerates with a slight spring. It signals that something definite has happened (an answer was submitted, a question was answered).

**2. Colour transitions (0.1–0.3s linear or ease)**
Used on: hover states (background, border-color), timer colour, stat card shadow.
Duration: very short (0.1–0.12s for hover, 0.3s for timer colour progression).
Hover transitions must be fast — 100ms or less. A hover that takes 300ms to transition feels sluggish and makes the interface feel unresponsive. The timer colour transition is longer (0.5s) because it is a gradual state change, not a user action.

**3. Pulse animations (2s ease-in-out infinite)**
Used on: the streak dot in the nav (`pdot`), the "now" practising dot in the sidebar.
These animations draw attention to persistent live information — the streak is active right now, the current topic is being practised right now. The 2-second period is slow enough to be calming rather than distracting. Using `opacity` and `scale` together for the pulse (rather than `background-color`) means the animation works regardless of the dot's colour.

**4. Spinner (0.7s linear infinite)**
Used on: the loading state.
Linear easing (not ease-in-out) is correct for a continuous rotation — any easing creates an unnatural stutter on a loop. 0.7s is slightly faster than the typical 1s spinner, which reads as responsive and fast rather than slow and uncertain.

**5. Urgent timer pulse (0.9s ease-in-out infinite, opacity only)**
Used on: the timer text when below 20 seconds.
This is the only animation in the interface that exists solely to alarm the user. It pulses the text opacity between 100% and 55%. This is enough to catch peripheral vision without making the number unreadable. Using opacity rather than colour-shift is important — the timer's colour (red) is already communicating urgency; adding a colour animation on top would be redundant and harder to parse.

**What does not animate:**
- The question card appearing (no fade-in or slide-in). Content that fades in requires the student to wait before they can begin reading. Instant appearance is correct.
- The answer options after selection (no scale or bounce). The options changing colour immediately on click is enough feedback. Adding motion to a completed answer selection would feel like the interface is celebrating or condemning the choice, which is distracting.
- Navigation between pages (no page transition). The two-page architecture uses a simple React state swap. Cross-page transitions add latency to every navigation and are generally not worth the overhead for a tool-like interface.

---

## 20. Loading and Error States

### 20.1 Loading State

The loading card shares the question card's `borderLeft: 5px solid C.mid` — the "Gymnasium Lane." This means the loading state occupies the same visual space and maintains the same brand identity as the content it will become. The student's eye goes to the correct location and waits. The spinner is inside the card, paired with a two-line description: "Generating question…" and a dynamic subtitle describing what is being generated. The subtitle reduces perceived wait time by telling the student something is happening.

### 20.2 Error State

The error card uses `C.rLite` background and `C.rBdr` border — the full red semantic system. The error message shows the specific failure reason, not a generic "something went wrong." The Retry button uses the primary button style but in red — this is the only departure from the "red means incorrect/semantic" rule, justified because the retry action is the only available response to the error, making it the primary action in context.

---

## 21. Topic Tracker Sidebar

The sidebar's primary function is **focus control** — letting the student redirect the AI question generation towards specific weak areas. The design reflects this:

- **Subject selector first:** The student can change the subject being displayed before looking at individual topics. This prevents the list from being confusing when the current question comes from a different subject.
- **"Practising now" indicator second:** Shows the current question's topic with a pulsing blue dot. Positioned above the list so the student can always see what they are currently working on, even before the list scrolls.
- **Topic list third:** Topics are not sorted alphabetically or by ID. They appear in the order defined in the `TOPICS` object — which is the natural pedagogical order within each subject. Sorting by strength would be useful but constantly reordering as strengths change would be disorienting.
- **Strength percentages in JetBrains Mono:** All percentages are right-aligned and monospaced, so they form a column of data rather than scattered numbers. The brain processes a column of numbers more quickly than scattered values.
- **Bar height: 3px:** Progress bars are intentionally thin (3px, not 5px or 8px). Thicker bars would imply the percentage is the main focus of the row. Thin bars subordinate the percentage to the topic name — students should be focused on *which topic* to practise, with the strength percentage as supporting information.

---

## 22. Session Complete State

When all 10 questions are answered, a completion card appears above the navigation buttons. Its structure:

1. **Trophy icon in a square tile** (green light background, green border, green icon) — not a circle. Circles for achievement icons are overdone. A subtle square tile with a trophy is more in keeping with the platform's angular, geometric aesthetic.
2. **Adaptive copy** — "excellent work" (≥8 correct), "solid session" (≥5), "keep practising" (<5). The copy is intentionally not overly congratulatory even at full marks. "Excellent work." is a measured academic acknowledgement, not a confetti explosion. This is appropriate for the platform's serious register.
3. **Per-question result grid** — 10 clickable tiles showing each question's outcome (green check / red X). Clicking any tile navigates back to that question. This is essential for review — the student needs to be able to revisit wrong answers and understand the solution.

---

## 23. Things That Were Deliberately Rejected

**Dark mode:** Not implemented. Dark mode is appropriate for sustained creative work (coding, writing) where eye strain over hours is the concern. Exam preparation sessions are typically 15–30 minutes and high cognitive demand — a light, clean surface keeps the brain alert. Dark mode for ESAT Gymnasium would be a future addition, not a current priority.

**Animations on question reveal:** The question card appears instantly when the question data arrives. No fade, no slide. Any delay between content availability and content visibility is wasted time in a timed practice context.

**Tooltips:** Nothing in the interface uses tooltips. Every element is labelled or self-explanatory. Tooltips require hover, which is unavailable on touch screens and slow. If an element requires a tooltip to explain it, it should be redesigned.

**Colour-coded subjects (beyond difficulty):** The Gymnasium Lane is always `C.mid` (cobalt blue), not colour-coded by subject. Subject colour-coding would require maintaining a 5-colour system for 5 subjects, and those colours would need to avoid conflict with the semantic colours (green, red, amber, purple). The complexity is not worth the gain at this stage.

**Gradient background fills:** Avoided throughout except the countdown banner. Gradients date quickly, cannot be perfectly reproduced across browsers, and add visual noise when content is nearby.

**Sans-serif numbers in stats:** JetBrains Mono is non-negotiable for all numerical data. Using Inter for stat values (as many platforms do) is a missed opportunity — the monospace font communicates that these are precise, machine-generated measurements, not approximations.

---

## 24. Rules for Future Changes

1. **Never introduce a fourth font.** The three-font system (Inter / Instrument Serif / JetBrains Mono) is complete and coherent. Adding a fourth typeface breaks the system.

2. **All numerical data uses JetBrains Mono.** No exceptions. If you are rendering a number and you are not using JetBrains Mono, the answer is to switch fonts, not to break the rule.

3. **Semantic colours are not decorative colours.** Do not use `C.green`, `C.red`, `C.amber`, or `C.purp` to colour a non-semantic element (a heading, a divider, a decorative border). These colours carry meaning (correct, incorrect, caution, very hard). Diluting that meaning costs the user cognitive load.

4. **The Gymnasium Lane (`borderLeft: 5px solid C.mid`) belongs exclusively to question cards.** Do not apply this treatment to other cards. Its power comes from its singularity — it signals "this is where the question lives" instantly because nothing else on the page looks like it.

5. **Do not add emoji.** Not in headings, not in button text, not as placeholder content. They render differently across platforms, cannot be styled, and communicate the wrong emotional register for this product.

6. **All interactive elements must have a hover state.** If you add a clickable element and it has no hover styling, it is incomplete. Use the established CSS class pattern (`.btn-ghost`, `.btn-primary`, `.nav-pill`, `.topic-row`) or add a new named class to `GCSS`.

7. **Minimum text size is 11px (0.6875rem).** If you need to make something smaller than this to fit, the solution is to redesign the layout, not to shrink the text.

8. **New icons must come from Heroicons outline (24×24 viewBox).** Do not mix icon libraries. Inconsistent icon styles — some filled, some outline, from different libraries with different grid systems — immediately reads as an unprofessional interface.

9. **All spacing values must be multiples of 4px.** If you find yourself writing `padding: "7px 11px"`, those values should be `8px 12px`. Use the grid.

10. **The question is always the most visually prominent element on the Practice Hub.** If any future feature addition makes the sidebar, the navigator, or any other element more visually dominant than the question card + answer options, it has gone wrong.

---

*This document should be updated whenever a significant design decision is made. The principle is that future developers — human or AI — should be able to read this document and understand not just what the interface looks like, but why every element is the way it is.*