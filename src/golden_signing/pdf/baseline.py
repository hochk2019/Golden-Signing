"""Structural baseline compare — ECUS / golden fixtures (spec §11.3).

Not byte-for-byte identity. Records comparable structure so a Golden Signing
output can be checked against the ECUS-signed sample without claiming PUS
acceptance.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from golden_signing.pdf.inspection import preflight_pdf
from golden_signing.pdf.integrity import extract_byte_range, sha256_file, validate_byte_range

__all__ = ["StructuralBaseline", "build_baseline", "compare_baselines"]


@dataclass(slots=True)
class StructuralBaseline:
    path: str
    file_sha256: str
    file_size_bytes: int
    page_count: int
    pdf_version: str | None
    encrypted: bool
    has_acroform: bool
    incremental_revisions: int
    existing_signatures: list[str]
    byte_range: list[int] | None
    byte_range_valid: bool
    producer: str | None = None
    creator: str | None = None
    subfilter: str | None = None
    sig_filter: str | None = None
    cms_subject: str | None = None
    cms_issuer: str | None = None
    cms_serial: str | None = None
    cert_fingerprint_sha256: str | None = None
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _read_info_dict(path: Path) -> dict[str, str | None]:
    """Best-effort /Producer /Creator via pypdfium2 metadata."""
    producer: str | None = None
    creator: str | None = None
    try:
        import pypdfium2 as pdfium

        pdf = pdfium.PdfDocument(str(path))
        try:
            meta = pdf.get_metadata_dict()
            if meta:
                producer = meta.get("Producer") or None
                creator = meta.get("Creator") or None
        finally:
            pdf.close()
    except Exception:  # noqa: BLE001 — baseline should not crash on metadata
        pass
    return {"producer": producer, "creator": creator}


def _cms_summary(path: Path) -> dict[str, str | None]:
    """Parse first signature CMS via pyHanko validation helpers if possible."""
    out: dict[str, str | None] = {
        "subfilter": None,
        "sig_filter": None,
        "cms_subject": None,
        "cms_issuer": None,
        "cms_serial": None,
        "cert_fingerprint_sha256": None,
    }
    try:
        from pyhanko.pdf_utils.reader import PdfFileReader

        with open(path, "rb") as fh:
            reader = PdfFileReader(fh)
            # Walk AcroForm signature fields
            root = reader.root
            if "/AcroForm" not in root:
                return out
            acro = root["/AcroForm"]
            fields_ref = acro.get("/Fields")
            if fields_ref is None:
                return out
            from pyhanko.pdf_utils.generic import NameObject

            for field_ref in fields_ref:
                field_obj = (
                    field_ref.get_object() if hasattr(field_ref, "get_object") else field_ref
                )
                if field_obj.get("/FT") != NameObject("/Sig"):
                    continue
                # Widget /V is the signature dictionary
                v = field_obj.get("/V")
                if v is None and "/Kids" in field_obj:
                    kids = field_obj["/Kids"]
                    if kids:
                        kid = kids[0]
                        kid = kid.get_object() if hasattr(kid, "get_object") else kid
                        v = kid.get("/V")
                if v is None:
                    continue
                sig = v.get_object() if hasattr(v, "get_object") else v
                out["sig_filter"] = str(sig.get("/Filter", "")) or None
                out["subfilter"] = str(sig.get("/SubFilter", "")) or None
                contents = sig.get("/Contents")
                if contents is None:
                    break
                raw = contents
                if hasattr(raw, "original_bytes"):
                    der = raw.original_bytes
                else:
                    der = bytes(raw)
                    # pyHanko may expose hex string object
                    if isinstance(raw, str):
                        der = bytes.fromhex(raw.strip("<>"))
                # Strip PDF string padding zeros
                der = der.rstrip(b"\x00")
                try:
                    from asn1crypto import cms
                    from asn1crypto import x509 as asn1_x509

                    ci = cms.ContentInfo.load(der)
                    sd = ci["content"]
                    certs = sd["certificates"]
                    if certs:
                        chosen = None
                        for c in certs:
                            if c.name == "certificate":
                                chosen = c.chosen
                                break
                        if chosen is not None:
                            cert: asn1_x509.Certificate = chosen
                            out["cms_subject"] = cert.subject.human_friendly
                            out["cms_issuer"] = cert.issuer.human_friendly
                            out["cms_serial"] = format(cert.serial_number, "x")
                            import hashlib

                            out["cert_fingerprint_sha256"] = hashlib.sha256(
                                cert.dump()
                            ).hexdigest()
                except Exception:  # noqa: BLE001
                    pass
                break
    except Exception:  # noqa: BLE001
        pass
    return out


def build_baseline(path: Path) -> StructuralBaseline:
    data = path.read_bytes()
    pre = preflight_pdf(path, writable_check=False)
    br = extract_byte_range(data)
    br_valid = bool(br) and validate_byte_range(data, br) if br else False
    meta = _read_info_dict(path)
    cms = _cms_summary(path)
    notes: list[str] = []
    if pre.level.value == "block":
        notes.append("preflight BLOCK")
    return StructuralBaseline(
        path=str(path),
        file_sha256=sha256_file(path),
        file_size_bytes=pre.file_size_bytes,
        page_count=pre.page_count,
        pdf_version=pre.pdf_version,
        encrypted=pre.encrypted,
        has_acroform=pre.has_acroform,
        incremental_revisions=pre.incremental_revisions,
        existing_signatures=list(pre.existing_signatures),
        byte_range=br,
        byte_range_valid=br_valid,
        producer=meta["producer"],
        creator=meta["creator"],
        subfilter=cms["subfilter"],
        sig_filter=cms["sig_filter"],
        cms_subject=cms["cms_subject"],
        cms_issuer=cms["cms_issuer"],
        cms_serial=cms["cms_serial"],
        cert_fingerprint_sha256=cms["cert_fingerprint_sha256"],
        notes=notes,
    )


def compare_baselines(source: StructuralBaseline, signed: StructuralBaseline) -> dict[str, Any]:
    """Return a comparison dict: preserved structure vs signature-only deltas."""
    return {
        "page_count_equal": source.page_count == signed.page_count,
        "source_page_count": source.page_count,
        "signed_page_count": signed.page_count,
        "signed_has_acroform": signed.has_acroform,
        "signed_existing_signatures": list(signed.existing_signatures),
        "signed_byte_range_valid": signed.byte_range_valid,
        "signed_subfilter": signed.subfilter,
        "signed_cert_fingerprint_sha256": signed.cert_fingerprint_sha256,
        "source_unchanged_structure": (
            source.page_count == signed.page_count and not source.encrypted
        ),
    }
