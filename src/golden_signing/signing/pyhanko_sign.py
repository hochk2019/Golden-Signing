"""Shared pyHanko sign_pdf invocation (visible/invisible)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from golden_signing.signing.appearance import signing_extras
from golden_signing.signing.contracts import SigningProfile


def build_sign_call_kwargs(
    profile: SigningProfile | None,
    *,
    signer_display: str | None = None,
) -> dict[str, Any]:
    """Return field_name + extra kwargs for pyhanko sign_pdf."""
    visible = profile is not None and profile.mode.value == "visible"
    extras = signing_extras(profile, visible=visible, signer_display=signer_display)
    field_name = "GoldenSigning"
    if extras.get("field_name"):
        field_name = str(extras["field_name"])
    reason = profile.reason if profile else None
    location = profile.location if profile else None
    from pyhanko.sign.signers import PdfSignatureMetadata

    meta = PdfSignatureMetadata(
        field_name=field_name,
        reason=reason,
        location=location,
        md_algorithm="sha256",
    )
    out: dict[str, Any] = {"signature_meta": meta}
    if "new_field_spec" in extras:
        out["new_field_spec"] = extras["new_field_spec"]
    if "stamp_style" in extras:
        out["stamp_style"] = extras["stamp_style"]
    return out


def pyhanko_sign_file(
    *,
    input_path: Path,
    output_path: Path,
    pyhanko_signer: Any,
    profile: SigningProfile | None,
    signer_display: str | None = None,
) -> None:
    """Sign input → temp → os.replace(output). Raises on failure."""
    import os

    from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
    from pyhanko.sign.signers import PdfSigner

    kwargs = build_sign_call_kwargs(profile, signer_display=signer_display)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = output_path.with_name(f".{output_path.name}.tmp-sign")
    try:
        with open(input_path, "rb") as inf:
            writer = IncrementalPdfFileWriter(inf, strict=False)
            with open(tmp_path, "wb") as outf:
                pdf_signer = PdfSigner(
                    signature_meta=kwargs["signature_meta"],
                    signer=pyhanko_signer,
                    stamp_style=kwargs.get("stamp_style"),
                    new_field_spec=kwargs.get("new_field_spec"),
                )
                pdf_signer.sign_pdf(writer, output=outf, in_place=False)
        os.replace(tmp_path, output_path)
    finally:
        tmp_path.unlink(missing_ok=True)
