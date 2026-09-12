# BRANDING SPEC — Golden Sign

Date: 2026-09-09 (updated Phase 10 rename)
Spec refs: §44.5b (Golden Branding), ui-ux-pro-max design-system search

## Product vs brand

| Layer | Value |
|---|---|
| Product name | **Golden Sign** (legacy: Golden Signing) |
| Developer | HOC HK |
| Brand artwork | Golden Logistics (`golden.svg`) — **not** the product name |

UI chrome always shows **Golden Sign**. Full GOLDEN LOGISTICS logo only in About / first-run branding slot.

## Source asset

| File | Role |
|---|---|
| `assets/branding/golden.svg` | Source of truth (keep untouched, ~3.2MB VTracer) |
| `assets/branding/golden-mark.svg` | Mark-only / cropped icon for sidebar + window icon source |
| `assets/branding/golden-mark.png` | Raster fallback (256px) |
| `assets/branding/golden-app-icon.ico` | Windows multi-size ICO |

## Placement (desktop)

- **Sidebar expanded:** mark 36–40px + “Golden Sign” 17–19px semibold + optional “Ký số PDF”
- **Sidebar collapsed:** mark 28–32px + tooltip
- **Workspace:** no large logo over PDF area
- **Title bar:** `Golden Sign — Ký số PDF` (no second large logo)
- **About:** full logo medium size + developer block + disclaimer

## Color derivation (from logo + Pro Max)

Sampled dominant fills in `golden.svg`: `#FDBE00`, `#FBBD02` (gold/amber).

UI/UX Pro Max “Enterprise Gateway / Minimalism Swiss” recommends trust navy for professional tools.

| Token | Hex | Source |
|---|---|---|
| `brand.gold` | `#FDBE00` | logo primary gold |
| `brand.gold-deep` | `#D4A000` | darker gold for hover/contrast |
| `ui.primary` | `#1E3A5F` | Pro Max navy (trust) |
| `ui.accent` | `#FDBE00` | brand gold as accent (max 2 uses per screen) |

Status colors are **semantic**, never brand-only (icon + text + color).

## Rules

1. Do not crop/distort/recolor source logo without brand-owner approval.
2. Do not use gold as Success/Error/Warning alone.
3. Mark must remain recognizable at 16px taskbar size.
4. App icon = mark, not full wordmark with tiny text.
