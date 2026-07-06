# HOW IT'S MADE — Skills Dashboard (`skills_reference.html`)

> **REV 4.1** · 72 Skills · Tactical Brutalist + Dawn Blue + Live 3D Effects

A single-file, zero-dependency HTML dashboard cataloging 72 Codebuff skills with install commands, prompts, and real-time visual effects. No frameworks, no build step — just vanilla HTML/CSS/JS.

---

## Table of Contents

1. [Design Philosophy](#design-philosophy)
2. [Design System Tokens](#design-system-tokens)
3. [Typography](#typography)
4. [CSS Architecture](#css-architecture)
5. [The Double-Bezel Card System](#the-double-bezel-card-system)
6. [The 4 Live Effects](#the-4-live-effects)
7. [Skill Data Structure](#skill-data-structure)
8. [JavaScript Architecture](#javascript-architecture)
9. [Skill Categories & Counts](#skill-categories--counts)
10. [How to Add New Skills](#how-to-add-new-skills)
11. [How the Effects Were Fixed (Debugging)](#how-the-effects-were-fixed-debugging)
12. [Performance Optimizations](#performance-optimizations)
13. [Browser Support](#browser-support)

---

## Design Philosophy

The dashboard fuses **4 design skill directives** into one cohesive visual language:

| Skill | Contribution |
|---|---|
| **industrial-brutalist-ui** | Tactical dark palette (#0A0A0A / #EAEAEA / #5B9BD5), visible 1px compartmentalization borders, zero border-radius on all content, monospace dominance, CRT scanlines, grid overlay |
| **high-end-visual-design** | Double-bezel nested cards (outer shell + inner core), Geist + JetBrains Mono fonts (no Inter/Roboto), custom `cubic-bezier(0.32, 0.72, 0, 1)` for all transitions, IntersectionObserver scroll reveals |
| **gpt-taste** | Ultra-wide hero (max 1800px), gapless 1px bento grid (`grid-auto-flow: dense`), massive section spacing, inline micro-block in heading |
| **minimalist-ui** | Pastel tag backgrounds, no gradients/shadows on primary surfaces, subtle hover states |

The **one exception** to "zero border-radius" is the floating glass pill filter bar — its `border-radius: 9999px` creates deliberate visual contrast.

---

## Design System Tokens

All visual properties are centralized in CSS custom properties on `:root`:

```css
:root {
  /* Palette */
  --bg-tactical:    #0A0A0A;   /* Main background */
  --bg-surface:     #0F0F0F;   /* Card hover surface */
  --text-phosphor:  #EAEAEA;   /* Primary text (like CRT phosphor) */
  --text-secondary: #999;       /* Description text */
  --text-muted:     #555;       /* Labels, timestamps */
  --accent-dawn:    #5B9BD5;   /* Dawn blue accent */
  --accent-glow:    rgba(91,155,213,0.15); /* Hover glow */
  --border-solid:   #EAEAEA;   /* 1px solid borders */
  --border-subtle:  rgba(234,234,234,0.10); /* Subtle dividers */
  --pastel-tag:     #1A1A1A;   /* Tag background */

  /* Motion */
  --cubic-editorial: cubic-bezier(0.32, 0.72, 0, 1);
  --glass-blur:      20px;
}
```

**Why dawn blue (#5B9BD5)?** Originally hazard red (#E61919), the user requested a warmer, calmer blue. A single CSS variable change propagates to all 20+ accent usages: hero tag, pre-loaded badges, copy feedback, GitHub link borders, particles, inline block glow.

---

## Typography

Two fonts, strict hierarchy:

| Font | Usage | Weight |
|---|---|---|
| **Geist** (sans-serif) | Hero heading, skill names, stat numbers | 400, 500, 700, 800 |
| **JetBrains Mono** (monospace) | Everything else — body, tags, commands, labels, categories | 400, 500, 700 |

Fonts are loaded via Google Fonts with `preconnect` for performance:

```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Geist:...&family=JetBrains+Mono:..." rel="stylesheet">
```

**No Inter. No Roboto.** This is a hard constraint from high-end-visual-design — those fonts are "AI slop" indicators.

---

## CSS Architecture

### Layering (z-index)

```
z-index 9998  →  #scanlines (CRT effect, pointer-events: none)
z-index 30    →  .controls-wrap (floating glass pill, sticky)
z-index 10    →  .hero (headline + parallax elements)
z-index 2     →  .container (skill grid)
z-index 1     →  #grid-overlay (dot grid, pointer-events: none)
z-index 0     →  canvas#particles (particle network background)
```

### Background Layers (bottom to top)

1. `#0A0A0A` solid background on `<body>`
2. `canvas#particles` — 50 dawn-blue dots with proximity lines
3. `#grid-overlay` — 80px dot grid at 3% opacity
4. Content (hero, controls, cards)
5. `#scanlines` — horizontal lines at 8% black, 60% opacity

### Responsive Breakpoints

```css
@media (max-width: 800px) {
  .hero { padding: 100px 20px 48px }
  .hero h1 { font-size: 2rem }
  .container { padding: 0 20px 80px }
  .grid { grid-template-columns: 1fr }  /* single column */
  .stats-bar { gap: 24px }
}
```

---

## The Double-Bezel Card System

Each skill card is a **nested two-layer structure**:

```
.card (outer shell)
├── padding: 6px           ← creates the "bezel gap"
├── perspective: 1200px    ← enables 3D tilt
├── opacity: 0             ← hidden until reveal
├── transform: translateY(48px)  ← slides up on reveal
└── filter: blur(4px)      ← sharpens on reveal

    .card-inner (inner core)
    ├── border: 1px solid #EAEAEA
    ├── border-radius: 0    ← STRICT: NO rounding
    ├── transform: rotateX(var(--tX)) rotateY(var(--tY))  ← 3D tilt vars
    ├── transform-style: preserve-3d
    └── hover:
        ├── background: #0F0F0F (lighter surface)
        └── box-shadow: dawn blue glow + deep shadow
```

**The 6px gap between outer and inner** creates the "bezel" effect — the background color (#0A0A0A) shows through, forming a visible border around the inner card's 1px solid border.

### Pre-loaded vs Community Cards

```css
.card.preloaded .card-inner { border-color: #5B9BD5 }  /* dawn blue border */
.card.preloaded .name       { color: #5B9BD5 }         /* dawn blue name */
```

Pre-loaded cards also get a `PRE-LOADED` badge positioned absolutely in the top-right corner.

---

## The 4 Live Effects

### 1. Canvas Particle Network (`drawParticles()`)

**Inspiration:** videodb skill (visual indexing / evidence links)

**How it works:**
- 50 nodes with random positions, velocities, radii, and alpha values
- Each frame: move nodes, wrap at edges, draw dots
- Proximity lines: connect nodes within 90px (fading with distance)
- Mouse proximity: nodes within 100px of cursor connect to cursor
- Pauses during scroll to save GPU
- Uses `requestAnimationFrame` loop

```javascript
const pCvs = document.getElementById('particles'), pCtx = pCvs.getContext('2d');
// ... 50 nodes, each with {x, y, vx, vy, r, a}
function drawParticles() {
  if (scrollPaused) { requestAnimationFrame(drawParticles); return }
  pCtx.clearRect(0, 0, pW, pH);
  // Draw nodes + proximity lines
  requestAnimationFrame(drawParticles);
}
```

**CSS requirement:** The canvas MUST have `position:fixed;inset:0;z-index:0;pointer-events:none` — this was a bug (canvas was invisible) until REV 4.1.

### 2. 3D Card Tilt (`tiltMove()`)

**Inspiration:** remotion-best-practices (interpolate-like easing)

**How it works:**
- Each `.card-inner` has mouseenter/mousemove/mouseleave listeners
- On mousemove: calculate mouse offset from card center (0..1 range)
- Map to CSS variables: `--tX` (rotateX, -12° to +12°) and `--tY` (rotateY, ±12°)
- CSS applies: `transform: rotateX(var(--tX)) rotateY(var(--tY))`
- Perspective is on the parent `.card` (1200px)
- On mouseleave: spring-back to 0° with `transition: transform 0.5s cubic-bezier(...)`
- Rect caching via WeakMap avoids layout thrashing

**Critical fix:** `bindTilt()` is called inside `render()` to re-attach listeners after filter rebuilds:

```javascript
function render() {
  // ... rebuild grid.innerHTML ...
  document.querySelectorAll('.card').forEach(c => { io.observe(c) });
  bindTilt();  // ← MUST be here, not just at page load
}
```

### 3. Character-by-Character Hero Reveal

**Inspiration:** remotion-best-practices (sequential staggering)

**How it works:**
- Each character in the hero h1 is wrapped in `<span class="char" style="--c:N">`
- CSS animation with per-character delay:

```css
.hero h1 .char {
  display: inline-block; opacity: 0;
  animation: charIn 0.5s var(--cubic-editorial) forwards;
  animation-delay: calc(var(--c) * 40ms + 400ms);
}
@keyframes charIn {
  0%   { opacity: 0; transform: translateY(30px); filter: blur(8px) }
  100% { opacity: 1; transform: translateY(0);    filter: blur(0) }
}
```

Characters marked with `.strike` class render in dawn blue.

### 4. Mouse Parallax on Hero

**Inspiration:** remotion-best-practices (individual transform properties)

**How it works:**
- Global mousemove listener tracks normalized cursor position (-1..+1)
- `requestAnimationFrame` loop lerps toward target position
- Hero h1, tag, and inline block each drift at different multipliers:
  - h1: ±12px X, ±8px Y
  - tag: ±4px X, ±3px Y
  - inline-block: ±18px X, ±10px Y

**Critical fix:** Removed CSS `transition: transform` on hero elements — it was fighting the JS animation loop, causing jerky motion.

---

## Skill Data Structure

Each skill is a JavaScript object in the `S` array:

```javascript
{
  n:   "skill-name",           // Display name
  g:   "https://github.com/owner/repo",  // GitHub URL (empty string for built-ins)
  c:   "d",                    // Category: d=design, s=system, u=utility, v=dev, c=comm
  p:   1,                      // Pre-loaded flag (1=yes, 0=community)
  d:   "Description text...",  // Full description
  cmd: "npx skills add ...",   // Install command (copyable)
  pr:  "Load skill. Do X...",  // Example prompt (copyable)
  t:   ["tag1", "tag2", ...]   // Tags displayed as pills
}
```

### GitHub URL Convention

```javascript
const G = "https://github.com/";
// Usage: g: G + "owner/repo"
```

Built-in skills (draft, find-session, pin) use `g: ""` and display "Built into Codebuff" instead of a link.

### Categories (single-letter codes)

| Code | Label | Color |
|---|---|---|
| `d` | DESIGN | Default phosphor |
| `s` | SYSTEM | Default phosphor |
| `u` | UTILITY | Default phosphor |
| `v` | DEV | Default phosphor |
| `c` | COMM | Default phosphor |
| `pre` | PRE-LOADED | Dawn blue (#5B9BD5) |

---

## JavaScript Architecture

### Core Functions

| Function | Purpose |
|---|---|
| `render()` | Rebuilds the entire grid based on filter + search. Calls `io.disconnect()`, rebuilds `grid.innerHTML`, re-observes cards, calls `bindTilt()`, updates stats |
| `debounceRender()` | 150ms debounce wrapper for search input |
| `setF(filter, el)` | Sets active filter chip and re-renders |
| `updStats(f)` | Updates the stats bar with category counts |
| `cpCmd(el, text)` / `cpPr(el, text)` | Copy-to-clipboard with "COPIED" feedback |
| `h(s)` | HTML-escapes a string using textContent/innerHTML sandwich |
| `bindTilt()` | Attaches 3D tilt listeners to all `.card-inner` elements |
| `tiltEnter/Move/Leave(e)` | 3D tilt event handlers |
| `drawParticles()` | Canvas animation loop |
| `parallaxLoop()` | Hero parallax animation loop |

### IntersectionObserver (Scroll Reveals)

```javascript
const io = new IntersectionObserver((entries) => {
  entries.forEach(e => {
    if (e.isIntersecting) {
      e.target.classList.add('revealed');
      io.unobserve(e.target);  // Only animate once
    }
  });
}, { threshold: 0.06 });
```

Cards enter with `opacity: 0; transform: translateY(48px); filter: blur(4px)` and reveal to `opacity: 1; transform: translateY(0); filter: blur(0)` with a 0.7s cubic-bezier transition. Each card gets a 35ms stagger via inline `transition-delay`.

### Filter System

- **Search:** Case-insensitive match against name, description, tags, and GitHub URL
- **Chip filters:** ALL / PRE-LOADED / DESIGN / SYSTEM / UTILITY / DEV / COMM
- Counter shows `matched / total SKILLS`

### Copy Functionality

Both the install command block and prompt block are clickable. Single-quote escaping uses `h(s).replace(/'/g, "\\'")` to safely embed strings in onclick handlers.

---

## Skill Categories & Counts (72 Total)

| Category | Count | Source |
|---|---|---|
| **Pre-Loaded** | 10 | Built into Codebuff + nextlevelbuilder |
| **Community Design** | 9 | Various GitHub repos |
| **Community System** | 1 | andrewvaughan/agent-council |
| **Community Dev** | 4 | Various GitHub repos |
| **Community Utility** | 5 | Various GitHub repos |
| **Taste-Skill** | 13 | Leonxlnx/taste-skill |
| **ComposioHQ** | 28 | ComposioHQ/awesome-claude-skills |
| **Remotion + VideoDB** | 2 | remotion-dev/skills + video-db/skills |
| **TOTAL** | **72** | |

---

## How to Add New Skills

1. Add a new entry to the `S` array in the appropriate section:
```javascript
{n:"new-skill",g:G+"owner/repo",c:"d",p:0,
 d:"Description of what the skill does.",
 cmd:"npx skills add owner/repo@new-skill --yes",
 pr:"Load new-skill. Do [action] for [purpose].",
 t:["tag1","tag2","tag3"]},
```

2. Update the REV tag in `.hero-tag` (e.g., `/// REV 4.2`)
3. Update the counter in `.cnt` element (e.g., `73 SKILLS`)
4. The `render()` function auto-handles the rest — categories, search, filtering, and display

---

## How the Effects Were Fixed (Debugging)

### Bug 1: Blank/Black Screen
**Cause:** `<h1id="hero-h1">` — missing space between tag name and attribute  
**Fix:** Changed to `<h1 id="hero-h1">`  
**Symptom:** Entire page rendered blank because the HTML parser couldn't parse the malformed tag

### Bug 2: No Particles Visible
**Cause:** `canvas#particles` had no CSS — it was an invisible inline element  
**Fix:** Added `position:fixed;inset:0;z-index:0;pointer-events:none;width:100%;height:100%`  
**Symptom:** Particle animation ran in JS but nothing appeared on screen

### Bug 3: 3D Tilt Stopped After Filtering
**Cause:** `render()` rebuilds `grid.innerHTML`, destroying old elements and their event listeners. `bindTilt()` was only called once at page init  
**Fix:** Added `bindTilt()` inside `render()` after grid rebuild  
**Symptom:** Tilt worked initially but broke after clicking any filter chip

### Bug 4: Parallax Was Jerky
**Cause:** CSS `transition: transform 0.1s ease-out` on `.hero h1` and `.hero-tag` fought against the JS `requestAnimationFrame` loop updating transforms every frame  
**Fix:** Removed the conflicting CSS transitions  
**Symptom:** Hero elements lagged behind mouse movement by 100ms

---

## Performance Optimizations

| Optimization | Detail |
|---|---|
| **`will-change` only on hover** | `.card-inner` gets `will-change: transform` — only applied on hover, not all 72 cards |
| **`io.unobserve()` after reveal** | Each card is only observed once, then removed from the observer |
| **`WeakMap` for tilt rects** | Cached bounding rects avoid layout thrashing on every mousemove |
| **Particles pause on scroll** | `scrollPaused` flag prevents canvas drawing during scroll events |
| **2 orbs, not 3** | Reduced from 3 to 2 ambient orbs; blur reduced from 120px to 80px |
| **`grid-auto-flow: dense`** | CSS grid packs cards tightly, no wasted space |
| **Inline `transition-delay`** | 35ms stagger per card computed inline, not via JS setTimeout |
| **Debounced search** | 150ms debounce on search input prevents excessive re-renders |

---

## Browser Support

- **Chrome/Edge:** Full support (all effects, backdrop-filter, IntersectionObserver)
- **Firefox:** Full support
- **Safari:** Full support (requires `-webkit-backdrop-filter`)
- **Mobile:** Responsive — single column below 800px, reduced hero padding

---

## File Stats

| Metric | Value |
|---|---|
| Total lines | ~590 |
| CSS rules | ~80 |
| JavaScript functions | ~20 |
| Skills cataloged | 72 |
| Dependencies | 0 (zero) |
| File size | ~38 KB |
| Load time | < 100ms (fonts cached) |

---

> **Built with:** industrial-brutalist-ui + high-end-visual-design + gpt-taste + minimalist-ui  
> **Fonts:** Geist + JetBrains Mono  
> **Palette:** Tactical dawn (#0A0A0A / #EAEAEA / #5B9BD5)  
> **License:** MIT — use, modify, distribute freely
