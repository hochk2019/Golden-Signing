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
    cert_info: Any | None = None,
    text_color: tuple[float, float, float] | None = None,
    show_background: bool = True,
    show_logo: bool = False,
    logo_path: Any | None = None,
) -> dict[str, Any]:
    """Return field_name + extra kwargs for pyhanko sign_pdf."""
    visible = profile is not None and profile.mode.value == "visible"
    extras = signing_extras(
        profile,
        visible=visible,
        signer_display=signer_display,
        cert_info=cert_info,
        text_color=text_color,
        show_background=show_background,
        show_logo=show_logo,
        logo_path=logo_path,
    )
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
    cert_info: Any | None = None,
    text_color: tuple[float, float, float] | None = None,
    show_background: bool = True,
    show_logo: bool = False,
    logo_path: Any | None = None,
) -> None:
    """Sign input → temp → os.replace(output). Raises on failure."""
    import os

    from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
    from pyhanko.sign.signers import PdfSigner

    from golden_signing.pdf.crypto import open_pdf_reader

    kwargs = build_sign_call_kwargs(
        profile,
        signer_display=signer_display,
        cert_info=cert_info,
        text_color=text_color,
        show_background=show_background,
        show_logo=show_logo,
        logo_path=logo_path,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = output_path.with_name(f".{output_path.name}.tmp-sign")
    reader = None
    try:
        with open(input_path, "rb") as inf:
            reader = open_pdf_reader(input_path, strict=False)
            writer = IncrementalPdfFileWriter(inf, prev=reader, strict=False)
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
        fh = getattr(reader, "_gs_fh", None) if reader is not None else None
        if fh is not None and not fh.closed:
            fh.close()
