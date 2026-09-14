# ADR-GSIGN-001 — Golden Sign application icon

**Status:** Accepted · 2026-09-14  
**Concept:** R1 One-stroke G-Sign  
**Master:** `assets/branding/gsign/golden-signing.svg`

## Why G-Sign

Product needs a **Windows app symbol** distinct from the Golden Logistics diamond used **inside** the UI sidebar. Spec: *“G đang ký”* (G is signing), not *“G + signature”*.

## Why this geometry (R1)

- **One continuous gesture path:** G bowl → bar → exit flick = the act of signing in one breath.
- **Second stroke** (deep gold): verification terminal integrated into the same motion language — not a UI ✓.
- Asymmetric flick up-right gives **motion** and a unique silhouette vs PDF readers (Acrobat/Foxit) and generic check badges.

## Why color

- Primary `#D99A22` — same golden family as logistics brand.
- Deep `#A96F08` — verification terminal.
- Highlight `#F4C15D` reserved for future premium/256+ variants.
- No blue/red (avoids Acrobat/antivirus confusion).

## Rejected alternatives

| ID | Why not |
|---|---|
| A–E (first pass) | Looked like “letter G + attached stroke”; user rejected as generic |
| E07/R3 Diamond | Strong brand DNA but less “signing” gesture; keep as backup |
| E02/R2 Cut | Good story; silhouette weaker at 16px than R1 |
| E03 Cursive | Too soft / lifestyle |
| C Ribbon gradient | Gradient disappears at taskbar size |

## Small-size decisions

- Stroke ≥ ~10% canvas width so 16–24px still shows G + flick.
- No fine negative-space holes inside the bowl.
- ICO packs 16→256 from 512px master (not a single downsample of 256).

## Windows decisions

| Surface | Asset |
|---|---|
| EXE / taskbar / title bar / installer | `gsign/golden-signing.ico` via `app_icon_path()` |
| Sidebar / in-app brand | **unchanged** `golden-mark-ui.png` (logistics mark) |

## Brand relationship

Same golden family; **different artwork**. Logistics mark stays in-app; G-Sign is the OS application symbol.
