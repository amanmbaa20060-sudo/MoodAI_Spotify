---
name: MoodAI Digital Experience
colors:
  surface: '#0e150e'
  surface-dim: '#0e150e'
  surface-bright: '#333b33'
  surface-container-lowest: '#091009'
  surface-container-low: '#161d16'
  surface-container: '#1a221a'
  surface-container-high: '#242c24'
  surface-container-highest: '#2f372e'
  on-surface: '#dce5d9'
  on-surface-variant: '#bccbb9'
  inverse-surface: '#dce5d9'
  inverse-on-surface: '#2a322a'
  outline: '#869585'
  outline-variant: '#3d4a3d'
  surface-tint: '#4ae176'
  primary: '#4be277'
  on-primary: '#003915'
  primary-container: '#22c55e'
  on-primary-container: '#004b1e'
  inverse-primary: '#006e2f'
  secondary: '#7bd0ff'
  on-secondary: '#00354a'
  secondary-container: '#00a6e0'
  on-secondary-container: '#00374d'
  tertiary: '#ffb5ab'
  on-tertiary: '#60130d'
  tertiary-container: '#ff8b7c'
  on-tertiary-container: '#76231b'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#6bff8f'
  primary-fixed-dim: '#4ae176'
  on-primary-fixed: '#002109'
  on-primary-fixed-variant: '#005321'
  secondary-fixed: '#c4e7ff'
  secondary-fixed-dim: '#7bd0ff'
  on-secondary-fixed: '#001e2c'
  on-secondary-fixed-variant: '#004c69'
  tertiary-fixed: '#ffdad5'
  tertiary-fixed-dim: '#ffb4a9'
  on-tertiary-fixed: '#410001'
  on-tertiary-fixed-variant: '#7f2a21'
  background: '#0e150e'
  on-background: '#dce5d9'
  surface-variant: '#2f372e'
typography:
  display-lg:
    fontFamily: Inter
    fontSize: 48px
    fontWeight: '800'
    lineHeight: 56px
    letterSpacing: -0.02em
  display-lg-mobile:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '800'
    lineHeight: 40px
    letterSpacing: -0.01em
  headline-md:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '700'
    lineHeight: 32px
    letterSpacing: -0.01em
  body-lg:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '400'
    lineHeight: 28px
  body-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-sm:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '500'
    lineHeight: 20px
  label-caps:
    fontFamily: JetBrains Mono
    fontSize: 12px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.05em
  caption:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 16px
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  base: 8px
  container-padding-mobile: 1.25rem
  container-padding-desktop: 2.5rem
  gutter: 1.5rem
  stack-sm: 0.5rem
  stack-md: 1rem
  stack-lg: 2rem
---

## Brand & Style
The design system focuses on a **Premium Modernist** aesthetic, tailored for high-fidelity music discovery. The personality is calm and sophisticated, yet energized by vibrant accents. It employs a "Minimal Chrome" philosophy, where the interface recedes to let album art and data-driven visualizations take center stage.

The style leverages **Glassmorphism** and **Tonal Layering** to create a sense of deep, digital space. By using high-contrast typography against a dark, monochromatic foundation, the system evokes a sense of late-night focus and rhythmic energy. This is a "dark mode first" system designed to feel like a high-end physical audio component translated into a digital interface.

## Colors
This design system utilizes a specialized dark palette to maintain premium depth and readability. 
- **Primary Emerald:** Used exclusively for high-impact actions, active playback states, and progress indicators.
- **Deep Navy Base:** The background (#0F172A) provides a non-pure-black canvas that feels more expansive and atmospheric.
- **Elevated Surfaces:** Surfaces use #111827 to create subtle separation. 
- **Interaction States:** Hover states should shift background colors towards #1E293B. Secondary accents may use a muted blue-grey to maintain the "cool" temperature of the interface.

## Typography
The typographic system relies on **Inter** for its neutral, highly legible Swiss-style proportions, ensuring that metadata (track titles, artist names) remains clear at all sizes. 

For technical metadata and mood labeling, **JetBrains Mono** is introduced sparingly to provide a "calculated" or "AI-driven" feel. High contrast is achieved through weight rather than just size; use Bold (700) or ExtraBold (800) for primary headers, while secondary information stays in Medium (500) with a muted text color (#94A3B8).

## Layout & Spacing
This system utilizes a **12-column fluid grid** for desktop and a **4-column grid** for mobile. 
- **The Sidebar:** A fixed 280px navigation rail on desktop.
- **Main Viewport:** Uses a dynamic "Shelf" system for album carousels, with 24px (1.5rem) gutters between cards.
- **Rhythm:** All spacing must be a multiple of 8px. Use generous 32px or 48px vertical padding between sections to maintain the "minimal chrome" breathing room. 
- **Safe Zones:** Content should never touch the edges of the viewport; maintain a minimum 20px margin on mobile devices.

## Elevation & Depth
Hierarchy is established through **Tonal Layers** and **Luminous Shadows**.
- **Level 0 (Background):** #0F172A.
- **Level 1 (Cards/Sidebar):** #111827 with a 1px solid border of #1E293B.
- **Level 2 (Floating/Modals):** #1E293B with a "Luminous Shadow": `0 20px 40px -12px rgba(0, 0, 0, 0.5)`. 

Active elements, such as the currently playing track card, should feature a subtle Emerald (#22C55E) outer glow at 10% opacity to suggest "energy" without overwhelming the dark aesthetic.

## Shapes
The shape language balances strict geometry with organic softness. 
- **Album Art:** Fixed at 16px (rounded-lg) to soften the "grid" feel of the discovery engine.
- **Buttons:** Interactive elements use the "Rounded" (0.5rem) standard, except for Mood Chips and Play Buttons.
- **Pill Shapes:** Mood-based categories and primary Play/Pause buttons are fully rounded (pill-shaped) to distinguish them as high-intent interactive components.

## Components
- **Mood Chips:** Pill-shaped, semi-transparent backgrounds (`rgba(30, 41, 59, 0.5)`) with 1px borders. On hover, the border glows Emerald.
- **Play Buttons:** Circular, using the Primary Emerald (#22C55E) background with a dark icon for maximum visibility.
- **Track Rows:** Sleek, horizontal layouts with no background in their default state. On hover, apply a #111827 background with 8px rounded corners.
- **Input Fields:** Search bars should be dark-filled with subtle inset shadows and use the `label-caps` typography for placeholder text to emphasize the "discovery tool" nature of the app.
- **Progress Bars:** Ultra-thin (4px) with an Emerald fill and a semi-transparent slate track. The "thumb" should only appear on hover for a cleaner look during passive listening.
- **Glass Headers:** On scroll, the top navigation should apply a `backdrop-filter: blur(12px)` with 80% opacity of the background color.