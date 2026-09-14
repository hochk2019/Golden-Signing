# ADR-GSIGN-001 — Golden Sign application icon

**Status:** Accepted · 2026-09-14 (updated: user-supplied logo)  
**Final asset:** `assets/branding/gsign/golden-signing.ico` (+ PNG 16–512)  
**Source master:** `golden-signing-master.png` (1254×1254, user `G sign logo.png`)

## Why G-Sign

Product needs a **Windows app symbol** distinct from the Golden Logistics diamond used **inside** the UI sidebar. Spec: *“G đang ký”* (G is signing), not *“G + signature”*.

## Final artwork

User-supplied 3D gold one-stroke **G** on dark navy rounded plate.

Pipeline: master PNG → LANCZOS → sizes 16–512 (unsharp ≤64px) → ICO 10 entries (16–256) from 512px.

SVG exploration (`G_SIGN_CONCEPTS/`, `r1-one-stroke-master.svg`) kept as design reference only.

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
