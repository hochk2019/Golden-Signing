# DESIGN TOKENS — Golden Signing (desktop)

Stack: PySide6 / Qt. Tokens map to QSS / Qt palette. Source: ui-ux-pro-max + logo gold.

## Color

| Token | Light | Dark | Usage |
|---|---|---|---|
| `color.primary` | `#1E3A5F` | `#3D5A80` | Nav, primary buttons |
| `color.on-primary` | `#FFFFFF` | `#FFFFFF` | Text on primary |
| `color.brand-gold` | `#FDBE00` | `#FDBE00` | Logo, sparse accent |
| `color.on-gold` | `#1A1A1A` | `#1A1A1A` | Text on gold chips |
| `color.background` | `#F8FAFC` | `#0F172A` | Window bg |
| `color.surface` | `#FFFFFF` | `#1E293B` | Cards, lists |
| `color.foreground` | `#0F172A` | `#F8FAFC` | Body text |
| `color.muted-fg` | `#475569` | `#94A3B8` | Secondary text |
| `color.border` | `#CBD5E1` | `#334155` | Dividers |
| `color.success` | `#16A34A` | `#22C55E` | SUCCESS jobs (with icon) |
| `color.warning` | `#D97706` | `#F59E0B` | WARN preflight |
| `color.destructive` | `#DC2626` | `#EF4444` | Errors (with icon) |
| `color.focus` | `#1E3A5F` | `#93C5FD` | Focus ring |

Contrast: body ≥4.5:1 on surface; gold never as body text on light bg.

## Typography (Windows desktop)

| Role | Family | Size | Weight |
|---|---|---|---|
| UI body | Segoe UI | 12–13px | 400 |
| UI label | Segoe UI | 12px | 600 |
| Window title | Segoe UI Semibold | 14px | 600 |
| Product name (sidebar) | Segoe UI Semibold | 17–19px | 600 |
| Numeric/file list | Segoe UI | 12px | 400 |

Fallback stack: `"Segoe UI", "Open Sans", sans-serif`. Spec prefers system fonts for Windows.

## Spacing

4 / 8 / 12 / 16 / 24 / 32. Sidebar width expanded 220–240px; collapsed 56–64px.

## Radius / elevation

- Control radius 6px; card 8px.
- Shadows: none or 1-level subtle (desktop tool, Swiss/minimal).

## Motion

- Hover 150–200ms ease-out.
- Respect `prefers-reduced-motion` equivalent (Qt: disable nonessential animations if system asks).
- Batch progress updates without layout jump.

## Icons

SVG / Qt vector or monochrome PNG from one set. **No emoji as icons.**
