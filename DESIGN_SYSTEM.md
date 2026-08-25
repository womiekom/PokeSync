# PokeSync — Design System

> **Last Updated**: 2026-08-25
> **Source of Truth**: `client/style.css` (1709 lines), `client/index.html`, `client/assets/`
> **Status**: Documents the ACTUAL implemented visual language

---

## 1. Design Philosophy

### Intended Direction

PokeSync aims for a visual identity that is:

- **Retro / Pokémon-inspired** — evokes the Game Boy Advance (FireRed/LeafGreen) era through typography, color palette, and Poké Ball motifs
- **Approachable** — designed for non-expert users with beginner-friendly explanations and clear visual hierarchy
- **Game-like but functional** — strategic analysis presented through game-inspired UI elements (Poké Ball dials, type badges, element matrices) rather than generic dashboards
- **Not generic AI slop** — avoids corporate SaaS aesthetics, glassmorphism, excessive gradients, or dark-mode-heavy designs

### What Is Actually Implemented

The current UI **successfully delivers** on this philosophy:

- Custom Pokémon FRLG bitmap font used for all headings and labels
- Poké Ball SVGs used as animated background elements, loading animations, and score displays
- Type badge PNG icons for all 18 Pokémon types
- Custom SVG archetype icons for all 8 archetypes
- Warm light color palette (off-white background, red primary, blue accent)
- Rounded card-based layout with generous spacing
- No glassmorphism, no dark mode, no heavy gradients

---

## 2. Typography

### Font Families

| Variable | Value | Usage |
|----------|-------|-------|
| `--font-main` | `'Segoe UI', system-ui, -apple-system, sans-serif` | Body text, descriptions, paragraphs |
| `--font-custom` | `'Pokemon FRLG', sans-serif` | Headings, labels, buttons, counters, section titles |

### Font Loading

```css
@font-face {
    font-family: 'Pokemon FRLG';
    src: url('assets/font/Pokemon-FRLG.ttf') format('truetype');
    font-weight: normal;
    font-style: normal;
}
```

**File**: `client/assets/font/Pokemon-FRLG.ttf`

### Application Pattern

The custom font is applied via the `.custom-font` CSS class:

```css
.custom-font {
    font-family: var(--font-custom);
    letter-spacing: 1px;
}
```

### Where Custom Font Is Used

- `<h1>` title ("PokeSync")
- `<h2>` section headings ("Your Team Roster", "What Would You Like To Analyze?")
- `<h3>` card titles and sub-headings
- All button labels
- Slot counters ("0 / 6 Selected")
- Result labels ("PREDICTED ARCHETYPE", "SYNERGY SCORE")
- Tab buttons
- Score values
- Badge text

### Where System Font Is Used

- Card descriptions (`hub-card-desc`)
- Synergy summary descriptions
- Explanation list items
- Beginner guide text
- Tagline ("Competitive Pokémon Team Assistant & Strategy Analyst")
- General body copy

### Heading Sizes

| Element | Size | Weight | Notes |
|---------|------|--------|-------|
| `header h1` | `4rem` | Inherited from font | Red color, text-shadow |
| `.section-title-row h2` | `1.6rem` | Inherited | Dark grey (`--secondary`) |
| `.section-subheading` | `1.1rem` | 800 | Used inside card-inner sections |
| `.tagline` | `1.15rem` | 600 | Grey (#555) |
| Body | `1rem` (browser default) | Normal | Line-height 1.6 |

---

## 3. Color System

### Design Tokens (CSS Custom Properties)

All colors are defined in `:root` in `client/style.css` (lines 8-28):

#### Core Colors

| Token | Value | Swatch | Usage |
|-------|-------|--------|-------|
| `--primary` | `#ee1515` | 🔴 | Pokémon Red — title text, primary buttons, active states |
| `--primary-dark` | `#c00d0d` | 🔴 | Button hover state |
| `--secondary` | `#222224` | ⚫ | Dark grey — headings, active tabs, dark accents |
| `--bg` | `#f5f5f5` | ⬜ | Page background (off-white) |
| `--card-bg` | `#ffffff` | ⬜ | Card surfaces |
| `--text` | `#2c3e50` | 🔵 | Primary body text |
| `--accent` | `#3b4cca` | 🔵 | Pokémon Blue — links, input focus, highlights |
| `--accent-dark` | `#2a3898` | 🔵 | Accent hover states |

#### Semantic / Feedback Colors

| Token | Value | Swatch | Usage |
|-------|-------|--------|-------|
| `--success` | `#4caf50` | 🟢 | Strong rating, good synergy, strengths |
| `--success-dark` | `#2e7d32` | 🟢 | Success hover |
| `--warning` | `#ff9800` | 🟠 | Moderate rating, warnings |
| `--warning-dark` | `#e65100` | 🟠 | Warning hover |
| `--danger` | `#f44336` | 🔴 | Danger rating, critical gaps |
| `--danger-dark` | `#c62828` | 🔴 | Danger hover |

#### Non-Token Colors (Used Inline in CSS)

| Value | Usage |
|-------|-------|
| `#fafafa` | `.card-inner` background |
| `#e5e5e5` | `.card-inner` border |
| `#f0f0f0` | Slot counter background |
| `#555` | Tagline text, secondary labels |
| `#666` | Counter text, muted labels |
| `#999` | Disabled button text |
| `#eee` | Section dividers, borders |
| `#f9f9f9` | Coming-soon card background |
| `#f0f4ff` | Suggestion hover background |
| `rgba(0,0,0,0.06)` | Card border |
| `rgba(0,0,0,0.08)` | Standard shadow |
| `rgba(0,0,0,0.15)` | Heavy shadow |
| `rgba(59,76,202,0.12)` | Input focus glow (accent-derived) |

---

## 4. UI Components

### 4.1 Cards

**Primary Card** (`.card`):
- White background, 16px border-radius, soft shadow
- 2rem padding, 2.5rem bottom margin
- Subtle 1px border (`rgba(0,0,0,0.06)`)
- Used for: team input, analysis hub, result views

**Inner Card** (`.card-inner`):
- Off-white `#fafafa` background
- 2px solid `#e5e5e5` border, 12px border-radius
- 1.5rem padding
- Used for: explanations panel, strengths/gaps sections, type matrix

**Hub Card** (`.hub-card`):
- Within the analysis hub grid
- Contains: icon wrap, title (h3), description, action button
- Two variants:
  - `.active-option` — fully interactive
  - `.coming-soon-card` — 75% opacity, `#f9f9f9` background, disabled button

### 4.2 Buttons

**Hub Action Button** (`.hub-action-btn`):
- Background: `--primary` (red)
- Text: white, custom font, bold
- Rounded pill shape (30px radius)
- Contains retro SVG icon + text span
- Disabled state: grey `#eeeeee` background, `#999` text

**Synergy Button** (`.btn-synergy`):
- Background: `--accent` (blue) instead of red
- Otherwise same pattern as hub action button

**Tab Button** (`.tab-btn`):
- White background, 2px border, 30px border-radius
- Active state: dark `--secondary` background, white text, shadow

**Remove Button** (`.remove-btn`):
- Small circular button on filled team slots
- "×" character, positioned absolute

### 4.3 Input

**Search Input** (`input[type="text"]`):
- Full width (max 600px centered)
- 40px border-radius (pill shape)
- 3px border, transitions to `--accent` on focus
- Focus glow: `0 0 0 4px rgba(59,76,202,0.12)`

### 4.4 Suggestions Dropdown

- White background, 12px border-radius
- Max height 250px, scrollable
- Heavy shadow (`0 10px 30px rgba(0,0,0,0.15)`)
- Items: hover highlight with left blue accent border

### 4.5 Team Slots

- 6-column grid (3 cols on ≤900px, 2 cols on ≤600px)
- Empty: "+" placeholder, dashed-like appearance
- Filled: Pokémon image, name (custom font), type badges, remove button
- Type-colored border on fill (via `type-{name}` CSS class)

### 4.6 Score Displays

**Poké Ball Score Dial** (synergy):
- Custom CSS Poké Ball shape (top/bottom halves, center stripe, center button)
- Fill ring animates based on score percentage
- Score number displayed in center button
- Label underneath: "SYNERGY SCORE"

**Alignment Meter** (archetype):
- Horizontal progress bar with label and percentage value
- Fill animation on result display

**Sub-Score Bars** (synergy):
- Three cards: Defensive Coverage, Offensive Balance, Strategic Cohesion
- Each with retro SVG icon, title, percentage value, progress bar fill

### 4.7 Type Badges

- PNG images: `assets/symbols/type-{name}-badge.png`
- Used in team slots alongside Pokémon artwork
- All 18 Pokémon types represented

### 4.8 Archetype Icons

- SVG vector icons in `assets/archetypes/`
- One per archetype: `rain.svg`, `sun.svg`, `sand.svg`, `snow.svg`, `trick_room.svg`, `stall.svg`, `balance.svg`, `hyper_offense.svg`
- Used in hub cards and prediction results

### 4.9 Badges/Tags

- Rating badges: "STRONG" / "MODERATE" / "NEEDS ATTENTION"
- Colored by semantic status (success/warning/danger)
- Custom font, small pill shape

### 4.10 Elemental Defense Matrix

- 18-cell grid showing defensive matchup per attacking type
- Each cell shows weak/resist/immune counts
- Color-coded: strength (green), balanced (neutral), warning (orange), danger (red)
- Legend with colored dots

### 4.11 Offensive Profile Cards

- Three-card row: Damage Split, Speed Tiers, STAB Coverage
- Damage Split: Physical / Special / Mixed counts
- Speed Tiers: Fast (100+) / Mid (65-99) / Slow (≤60) with colored indicators
- STAB Coverage: X / 18 Types Hit display

### 4.12 Analysis Overlay

- Full-screen overlay with animated Poké Ball
- Step-by-step log display with "▶" retro bullets
- Three phases: "Scanning Team Composition...", "Analyzing Strategic Signatures...", "Generating Prediction..."

---

## 5. Layout Patterns

### Page Structure

| Property | Value |
|----------|-------|
| Max width | `1040px` |
| Horizontal padding | `1.5rem` |
| Top/bottom padding | `2.5rem` |
| Centered | `margin: 0 auto` |

### Card Spacing

| Property | Value |
|----------|-------|
| Card padding | `2rem` |
| Card margin-bottom | `2.5rem` |
| Card-inner padding | `1.5rem` |

### Grid Structures

| Grid | Columns | Gap |
|------|---------|-----|
| Team slots | 6 columns (3 at ≤900px, 2 at ≤600px) | 15px |
| Hub grid | 4 columns (implicit from flex/grid) | — |
| Sub-score grid | 3 columns | — |
| Strengths/gaps | 2 columns | — |
| Offensive profile | 3 columns | — |

### Responsive Breakpoints

| Breakpoint | Usage |
|------------|-------|
| `900px` | Team slots → 3 columns |
| `800px` | Offensive profile → stack |
| `768px` | Hub cards → 2 columns, sub-scores → stack, results adjustments |
| `600px` | Team slots → 2 columns |
| `500px` | Speed tiers → stack |

### Border Radius Convention

| Token | Value | Used For |
|-------|-------|----------|
| `--border-radius` | `16px` | Primary cards |
| — | `12px` | Inner cards, suggestions dropdown |
| — | `30px` | Tab buttons, action buttons (pill shape) |
| — | `40px` | Search input (pill shape) |
| — | `20px` | Slot counter (pill shape) |

---

## 6. Visual Language

### What Makes It Feel Retro/Pokémon

1. **FRLG Font**: The `Pokemon FRLG` bitmap-style font used for all headings and interactive elements evokes the Game Boy Advance era.
2. **Poké Ball Motifs**: Poké Ball SVGs appear in the background (animated drift), header logo (spinning), loading overlay (animated fill), and synergy score dial.
3. **Type Badge Icons**: Authentic Pokémon-style type badge PNGs displayed alongside Pokémon in team slots.
4. **Archetype Vector Icons**: Custom SVG icons representing each competitive archetype (weather, Trick Room, etc.).
5. **Red/Blue Color Scheme**: The `--primary` (Pokémon Red) and `--accent` (Pokémon Blue) colors reference the franchise's signature color pairing.
6. **Animated Background**: Multiple layers of Poké Ball SVGs (Poké, Great, Ultra, Master) drift diagonally with subtle opacity animation.
7. **Retro Button Icons**: Small SVG icons inside action buttons (predict-retro.svg, synergy-retro.svg, etc.).
8. **Retro Log Bullets**: The analysis overlay uses "▶" as step indicators, reminiscent of game text prompts.

### What Makes It Approachable

1. **Light Color Palette**: Off-white background with white cards — not dark/intimidating.
2. **Generous Spacing**: Large padding, margins, and gaps between elements.
3. **Beginner Guide**: Synergy results include a "beginner_guide" section explaining what synergy means.
4. **Plain Language**: Strategic rationale uses terms like "High defensive/stall presence detected" rather than technical jargon.
5. **Visual Scoring**: Percentage bars, Poké Ball dial, and color-coded ratings (green/yellow/red) provide instant understanding.
6. **Rounded Everything**: Heavy use of `border-radius` (12-40px) creates a friendly, non-corporate feel.

### What Makes It Non-AI-Slop

1. **No glassmorphism** — No frosted-glass backgrounds.
2. **No excessive gradients** — Solid colors throughout.
3. **No dark mode** — Light, warm palette only.
4. **No generic dashboard widgets** — Score displays use Poké Ball shapes, not generic radial charts.
5. **No stock icons** — Custom SVG assets themed to Pokémon.
6. **No loading spinners** — Custom animated Poké Ball overlay instead.
7. **No sidebar navigation** — Single-page vertical scroll.

---

## 7. Design Rules for Future Features (Phase 3)

### DO ✅

1. **Reuse existing components**: Cards (`.card`, `.card-inner`), buttons (`.hub-action-btn`), badges, progress bars, score displays.
2. **Use the same color tokens**: `--primary`, `--accent`, `--success`, `--warning`, `--danger`.
3. **Apply `.custom-font`** to all headings, labels, buttons, and interactive text.
4. **Follow the card-based layout** pattern — new features should be presented as cards within the existing flow.
5. **Add new hub cards** to the existing `hub-grid` for Moveset Recommender and Team Optimizer (replace the `coming-soon-card` class with `active-option`).
6. **Add new result tabs** alongside "Archetype Prediction" and "Team Synergy" in the `results-tab-bar`.
7. **Create new retro SVG icons** for Phase 3 features, matching the style of existing icons.
8. **Use the analysis overlay** for Phase 3 API calls — it already supports customizable phase text and log steps.
9. **Maintain the responsive breakpoints** — ensure new content works at 768px, 600px, and 500px.
10. **Keep the light color palette** — white cards on off-white background.

### DON'T ❌

1. **Don't introduce a different font** — stick with `Pokemon FRLG` + system font stack.
2. **Don't add npm/React/Vue** — the frontend is vanilla JS by design.
3. **Don't add glassmorphism, blur effects, or heavy gradients**.
4. **Don't create generic SaaS/AI dashboard layouts** with sidebars, breadcrumbs, or data tables.
5. **Don't use dark mode** or dark backgrounds.
6. **Don't replace the Poké Ball motifs** with generic icons.
7. **Don't break the single-page structure** — add sections within the existing `<main>` element.
8. **Don't introduce new color values** outside the existing token system unless necessary for Pokémon type colors.
9. **Don't use inline styles** — add CSS classes consistent with existing patterns.
10. **Don't remove the animated background** or analysis overlay — they are core to the identity.

### Recommended Pattern for Phase 3 Results

```
New Result Tab (e.g., "Moveset Recommendations")
  └── .result-view.card
       ├── Header section (icon + title + summary)
       ├── .card-inner sections for each recommendation
       │    ├── Move name (custom-font heading)
       │    ├── Type badge
       │    ├── Explanation text
       │    └── Relevance/confidence indicator
       └── .card-inner for team context
```
