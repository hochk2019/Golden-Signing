# Branding assets — Golden Signing

| File | Role | Notes |
|---|---|---|
| `golden.svg` | Source artwork (Golden Logistics) | **Do not modify** — 3.2MB VTracer |
| `golden-mark.png` | App/sidebar mark 512px | Full diamond badge (recognizable); replace with icon-only cutout if brand owner provides |
| `golden-app-icon.ico` | Windows icon | 16–256px generated from mark |
| `golden-full-preview.png` | About / docs preview 512px | Same badge |

Product name in UI is **Golden Signing**, not Golden Logistics. See `docs/design/BRANDING_SPEC.md`.

## Pipeline (how assets were generated)

1. Headless Chrome screenshot of `golden.svg` at 1024×1024.
2. Pillow resize + ICO multi-size export.

Do not rasterize once and upscale for large surfaces — prefer `golden.svg` when the UI stack supports it.
