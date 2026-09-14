"""PDF compression tiers (v1.1) — compress BEFORE sign only."""

from __future__ import annotations

import io
import json
import shutil
from dataclasses import asdict, dataclass
from enum import StrEnum
from pathlib import Path

from golden_signing.security.integrity import atomic_write_bytes

__all__ = [
    "CompressionError",
    "CompressionProfile",
    "CompressionResult",
    "CompressionTier",
    "compress_pdf",
    "default_profile",
    "has_signature",
    "load_profiles_path",
]


class CompressionError(RuntimeError):
    def __init__(self, message: str, *, code: str = "COMPRESSION_FAILED") -> None:
        super().__init__(message)
        self.code = code


class CompressionTier(StrEnum):
    LOSSLESS = "lossless"
    BALANCED = "balanced"
    PUS_SAFE = "pus_safe"
    CUSTOM = "custom"


@dataclass
class CompressionProfile:
    name: str = "PUS Safe 400KB"
    tier: str = CompressionTier.PUS_SAFE
    target_bytes: int | None = 400 * 1024
    signature_reserve_bytes: int = 32 * 1024
    jpeg_quality: int = 70
    max_dpi: int = 150
    downsample: bool = True
    strip_metadata: bool = True

    def effective_target(self) -> int | None:
        if self.target_bytes is None:
            return None
        return max(1024, self.target_bytes - self.signature_reserve_bytes)


@dataclass(frozen=True, slots=True)
class CompressionResult:
    source: Path
    output: Path
    before_bytes: int
    after_bytes: int
    skipped: bool
    note: str = ""
    profile_name: str = ""

    @property
    def saved_bytes(self) -> int:
        return max(0, self.before_bytes - self.after_bytes)


def default_profile(tier: CompressionTier = CompressionTier.PUS_SAFE) -> CompressionProfile:
    """Distinct, realistic presets (v1.1.1). Names are user-facing Vietnamese."""
    if tier is CompressionTier.LOSSLESS:
        return CompressionProfile(
            name="Không nén ảnh (lossless)",
            tier=tier.value,
            target_bytes=None,
            jpeg_quality=95,
            max_dpi=300,
            downsample=False,
            strip_metadata=True,
        )
    if tier is CompressionTier.BALANCED:
        return CompressionProfile(
            name="Cân bằng (chất lượng tốt)",
            tier=tier.value,
            target_bytes=None,
            jpeg_quality=85,
            max_dpi=200,
            downsample=True,
            strip_metadata=True,
        )
    if tier is CompressionTier.CUSTOM:
        return CompressionProfile(
            name="Tùy chỉnh",
            tier=tier.value,
            target_bytes=500 * 1024,
            jpeg_quality=75,
            max_dpi=160,
            downsample=True,
        )
    # PUS Safe — aggressive enough for customs upload size
    return CompressionProfile(
        name="PUS Safe — mục tiêu ≤400 KB",
        tier=CompressionTier.PUS_SAFE.value,
        target_bytes=400 * 1024,
        signature_reserve_bytes=32 * 1024,
        jpeg_quality=60,
        max_dpi=120,
        downsample=True,
        strip_metadata=True,
    )


def load_profiles_path() -> Path:
    from golden_signing.storage.app_paths import data_dir

    return data_dir() / "compression_profiles.json"


def has_signature(path: Path) -> bool:
    try:
        import pikepdf

        with pikepdf.open(path) as pdf:
            root = pdf.Root
            acro = root.get("/AcroForm")
            if acro is None:
                return False
            fields = acro.get("/Fields")
            if fields is None:
                return False
            for f in fields:
                ft = f.get("/FT")
                if ft is not None and str(ft) == "/Sig":
                    return True
                # kids (signature fields often nested)
                kids = f.get("/Kids")
                if kids is not None:
                    for k in kids:
                        if str(k.get("/FT") or "") == "/Sig":
                            return True
    except Exception:  # noqa: BLE001
        return False
    return False


def _estimate_dpi(pil_w: int, pil_h: int, pdf_w_pt: float, pdf_h_pt: float) -> float:
    # Image placed roughly full-page: DPI ≈ pixels / inches; 72pt = 1 inch
    inches_w = max(pdf_w_pt, 1.0) / 72.0
    inches_h = max(pdf_h_pt, 1.0) / 72.0
    return max(pil_w / inches_w, pil_h / inches_h)


def _strip_metadata(pdf: object) -> None:
    import contextlib

    try:
        root = pdf.Root  # type: ignore[attr-defined]
        if "/Metadata" in root:
            del root["/Metadata"]
        with pdf.open_metadata() as meta:  # type: ignore[attr-defined]
            for key in list(meta.keys()):
                with contextlib.suppress(Exception):
                    del meta[key]
    except Exception:  # noqa: BLE001
        pass


def _lossless_save(pdf, dest: Path) -> None:  # noqa: ANN001
    import pikepdf

    buf = io.BytesIO()
    pdf.save(
        buf,
        compress_streams=True,
        object_stream_mode=pikepdf.ObjectStreamMode.generate,
    )
    # Direct write (new path) — avoid atomic replace while handles may exist
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(buf.getvalue())


def _run_downsample_pass(
    src: Path,
    dest: Path,
    *,
    quality: int,
    max_dpi: int,
    strip_meta: bool,
) -> bool:
    """Open src, downsample images, write dest. True if dest written."""
    import pikepdf

    if not src.is_file():
        return False
    with pikepdf.open(src) as pdf:
        changed = _downsample_images(pdf, quality, max_dpi)
        if not changed:
            return False
        if strip_meta:
            _strip_metadata(pdf)
        _lossless_save(pdf, dest)
    return dest.is_file()


def compress_pdf(
    source: Path,
    output: Path,
    profile: CompressionProfile | None = None,
    *,
    allow_signed: bool = False,
) -> CompressionResult:
    """Compress PDF to output. Never deletes a file that is still open."""
    import tempfile
    import uuid

    import pikepdf

    profile = profile or default_profile()
    source = Path(source)
    output = Path(output)
    if not source.is_file():
        raise CompressionError(f"Không tìm thấy file: {source}", code="IO_ERROR")
    if has_signature(source) and not allow_signed:
        raise CompressionError(
            "File đã có chữ ký số — không nén để tránh làm mất hiệu lực chữ ký.",
            code="SIGNED_PDF",
        )

    before = source.stat().st_size
    target = profile.effective_target()
    if target is not None and before <= target:
        atomic_write_bytes(output, source.read_bytes())
        return CompressionResult(
            source=source,
            output=output,
            before_bytes=before,
            after_bytes=before,
            skipped=True,
            note="File đã dưới mục tiêu — bỏ qua nén.",
            profile_name=profile.name,
        )

    work = Path(tempfile.mkdtemp(prefix="gs-cmp-"))
    token = uuid.uuid4().hex[:8]
    best = work / f"{token}_lossless.pdf"
    try:
        with pikepdf.open(source) as pdf:
            if profile.strip_metadata:
                _strip_metadata(pdf)
            _lossless_save(pdf, best)
        best_size = best.stat().st_size

        if (
            profile.downsample
            and profile.tier != CompressionTier.LOSSLESS
            and (target is None or best_size > target)
        ):
            cand = work / f"{token}_img.pdf"
            if _run_downsample_pass(
                best,
                cand,
                quality=profile.jpeg_quality,
                max_dpi=profile.max_dpi,
                strip_meta=profile.strip_metadata,
            ) and cand.stat().st_size < best_size:
                best, best_size = cand, cand.stat().st_size

        if target is not None and best_size > target and profile.downsample:
            cand = work / f"{token}_strong.pdf"
            if _run_downsample_pass(
                best,
                cand,
                quality=max(40, profile.jpeg_quality - 15),
                max_dpi=max(96, int(profile.max_dpi * 0.75)),
                strip_meta=profile.strip_metadata,
            ) and cand.stat().st_size < best_size:
                best, best_size = cand, cand.stat().st_size

        # Never ship a "compressed" file larger than the original
        if best_size >= before:
            atomic_write_bytes(output, source.read_bytes())
            after = before
            note_keep = True
        else:
            atomic_write_bytes(output, best.read_bytes())
            after = output.stat().st_size
            note_keep = False
    finally:
        shutil.rmtree(work, ignore_errors=True)

    note = ""
    if note_keep:
        note = "Nén không nhỏ hơn gốc — giữ nguyên file."
    elif target is not None and after > target:
        note = f"Đã tối ưu tới {after // 1024} KB (mục tiêu {target // 1024} KB)."
    return CompressionResult(
        source=source,
        output=output,
        before_bytes=before,
        after_bytes=after,
        skipped=note_keep,
        note=note,
        profile_name=profile.name,
    )


def _downsample_images(pdf, quality: int, max_dpi: int) -> bool:  # noqa: ANN001
    import pikepdf
    from PIL import Image as PILImage

    changed = False
    for page in pdf.pages:
        res = page.get("/Resources")
        if res is None:
            continue
        xobj = res.get("/XObject")
        if xobj is None:
            continue
        try:
            w_pt = float(page.MediaBox[2]) - float(page.MediaBox[0])
            h_pt = float(page.MediaBox[3]) - float(page.MediaBox[1])
        except Exception:  # noqa: BLE001
            w_pt, h_pt = 595.0, 842.0
        for key in list(xobj.keys()):
            obj = xobj[key]
            try:
                if str(obj.get("/Subtype") or "") != "/Image":
                    continue
                pim = pikepdf.PdfImage(obj)
                pil = pim.as_pil_image().convert("RGB")
            except Exception:  # noqa: BLE001
                continue
            dpi = _estimate_dpi(pil.width, pil.height, w_pt, h_pt)
            if (
                dpi <= max_dpi * 1.05
                and pim.bits_per_component == 8
                and str(obj.get("/Filter") or "") == "/DCTDecode"
            ):
                continue
            scale = min(1.0, max_dpi / max(dpi, 1.0))
            if scale < 1.0:
                nw = max(1, int(pil.width * scale))
                nh = max(1, int(pil.height * scale))
                pil = pil.resize((nw, nh), PILImage.Resampling.LANCZOS)
            buf = io.BytesIO()
            pil.save(buf, "JPEG", quality=quality, optimize=True)
            new = pikepdf.Stream(pdf, buf.getvalue())
            new.stream_dict = pikepdf.Dictionary(
                Type=pikepdf.Name.XObject,
                Subtype=pikepdf.Name.Image,
                Width=pil.width,
                Height=pil.height,
                ColorSpace=pikepdf.Name.DeviceRGB,
                BitsPerComponent=8,
                Filter=pikepdf.Name.DCTDecode,
            )
            xobj[key] = new
            changed = True
    return changed


def save_profile(profile: CompressionProfile, path: Path | None = None) -> Path:
    path = path or load_profiles_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    existing: list[dict] = []
    if path.is_file():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            existing = []
    existing = [p for p in existing if p.get("name") != profile.name]
    existing.append(asdict(profile))
    path.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
