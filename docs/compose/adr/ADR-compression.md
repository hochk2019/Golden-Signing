# ADR — PDF compression engine (v1.1.0)

**Status:** Accepted · 2026-09-11  
**Spike evidence:** `.spike/v11/` with pikepdf 10.13 + Pillow 12.3

## Decision

Engine = **pikepdf** (structure/stream) + **Pillow** (image resample/JPEG).

**No Ghostscript** (AGPL / commercial). Optional qpdf CLI later; not required for v1.1.

### Tiers (v1.1)

| Preset | Behavior |
|---|---|
| **Lossless** | `compress_streams=True`, `object_stream_mode=generate`; strip optional metadata/thumbnails if safe |
| **Balanced** | Lossless + downsample images >150 DPI → ~150 DPI, JPEG q≈80 |
| **PUS Safe 400KB** | Target unsigned ≈ 400KB − reserve (default 32KB); iterative: lossless → image downsample/JPEG until target or quality floor |
| **Custom** | User target + JPEG quality + max DPI |

### Rules

1. **Compress before sign** — never mutate signed PDF.
2. If file already has signatures → block/warn.
3. If size already ≤ target → skip compression.
4. Never rasterize whole pages by default.
5. Keep text/vector streams untouched (only replace image XObjects).
6. Atomic write via existing `atomic_write_bytes`.

## Spike results

| File | Before | After | Method |
|---|---|---|---|
| Word→PDF text | 44.7 KB | 40.9 KB | lossless |
| Excel→PDF | 48.1 KB | 38.7 KB | lossless |
| Synthetic photo PDF | 113 KB | 46 KB | ½ resample JPEG 70 |
| Large photo PDF lossless | 2.05 MB | 2.05 MB | no gain (expected) |

## Image replace API (pikepdf 10)

```python
pim = pikepdf.PdfImage(obj)  # not a context manager
pil = pim.as_pil_image()
# write JPEG Stream, assign xobject[key] = new
```

## Consequences

- Add `pikepdf` dependency.
- `CompressionProfile` persisted in JSON/QSettings (not full SQLite schema yet).
- Auto-learn signature overhead deferred to v1.2 (fixed reserve 32KB in v1.1).
