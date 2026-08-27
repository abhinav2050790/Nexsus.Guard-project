# 🍏 Apple Design System Specification (Human Interface Guidelines)
## Nexsus.Guard — AI Risk Manager UI/UX System

---

## 1. Design Principles & Aesthetics

Apple's design language prioritizes **clarity, deference, and depth**:
- **Clarity:** Text is legible at every size, icons are precise, adornments are subtle, and the focus remains on the content.
- **Deference:** The UI is fluid, minimalist, and unobtrusive. Subtle translucency and frosted glass (vibrancy/materials) provide context and depth.
- **Depth:** Visual layers, realistic physics-inspired blurs, smooth rounded corners (continuous curves / squircle `border-radius`), and elevated floating cards.

---

## 2. Color Palette (Apple Dark Mode System Colors)

### Base Materials & Surfaces
| Token | Hex / Value | Description |
|---|---|---|
| `apple-bg` | `#000000` or `#08080A` | Deep pure dark canvas |
| `apple-surface-1` | `rgba(28, 28, 30, 0.75)` | Secondary system background / card |
| `apple-surface-2` | `rgba(44, 44, 46, 0.85)` | Tertiary elevated card / input |
| `apple-surface-hover` | `rgba(58, 58, 60, 0.90)` | Hover state |
| `apple-border` | `rgba(255, 255, 255, 0.10)` | Hairline divider border |
| `apple-border-focus` | `rgba(0, 122, 255, 0.60)` | Apple System Blue focus ring |

### Semantic System Colors
| Color Name | Hex | Usage |
|---|---|---|
| **System Blue** | `#007AFF` / `#0A84FF` | Primary actions, links, active state |
| **System Green** | `#34C759` / `#30D158` | Positive win probability, safe status |
| **System Orange** | `#FF9500` / `#FF9F0A` | Review status, warning alerts |
| **System Red** | `#FF3B30` / `#FF453A` | Skip recommendation, critical risk |
| **System Purple** | `#AF52DE` / `#BF5AF2` | AI confidence, model metrics |
| **System Gray (Text)** | `#8E8E93` | Muted secondary labels |
| **System White (Text)**| `#F5F5F7` | Primary high-contrast typography |

---

## 3. Typography (SF Pro Display & SF Pro Text)

- **Primary Font Family:** `-apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Helvetica Neue", sans-serif`
- **Hero / Title 1:** `font-weight: 800; letter-spacing: -0.035em; font-size: 2.2rem;`
- **Headline / Title 2:** `font-weight: 700; letter-spacing: -0.02em; font-size: 1.25rem;`
- **Subheadline:** `font-weight: 500; font-size: 0.88rem; color: #8E8E93;`
- **Footnote / Caption:** `font-size: 0.75rem; letter-spacing: 0.02em; text-transform: uppercase; font-weight: 700;`

---

## 4. Components & Micro-Interactions

1. **Frosted Glass Cards (Material Vibrancy):**
   - `background: rgba(28, 28, 30, 0.70); backdrop-filter: blur(30px) saturate(190%);`
   - `border: 1px solid rgba(255, 255, 255, 0.12);`
   - `border-radius: 18px;`
   - `box-shadow: 0 8px 32px rgba(0, 0, 0, 0.45);`

2. **Apple Segmented Controls (Tabs):**
   - Seamless pill container with `background: rgba(118, 118, 128, 0.24); border-radius: 12px; padding: 4px;`
   - Selected tab: `background: rgba(255, 255, 255, 0.15); box-shadow: 0 3px 12px rgba(0,0,0,0.3); font-weight: 700;`

3. **SF Symbols Badges:**
   - Soft translucent background with high-contrast text and border pill.
   - Example: `background: rgba(52, 199, 89, 0.15); color: #30D158; border: 1px solid rgba(52, 199, 89, 0.3);`

4. **Action Buttons (Apple Style):**
   - Solid System Blue with subtle gradient: `background: linear-gradient(180deg, #0A84FF 0%, #0071E3 100%);`
   - `border-radius: 980px` (Apple Capsule pill shape) or `12px`.
   - Hover: `transform: scale(1.01); filter: brightness(1.08);`
   - Active: `transform: scale(0.98);`

5. **Data Visualization (Apple Health / Fitness Chart Style):**
   - Clean, rounded lines, smooth curves, and glow-filled gradients.
   - Dark background matching `#1C1C1E` with subtle grid lines.
