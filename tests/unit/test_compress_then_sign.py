"""Plan A: CHỈ NÉN → COMPRESSED; KÝ SỐ signs compressed artifact."""

from __future__ import annotations

from pathlib import Path

from golden_signing.batch.state import TERMINAL_STATES, JobState, SigningJob
from golden_signing.batch.worker import process_one_job
from golden_signing.signing.contracts import PusProfile, SignatureMode, SigningProfile


def _profile() -> SigningProfile:
    return SigningProfile(
        id="t",
        name="test",
        certificate_fingerprint_sha256="ab" * 32,
        mode=SignatureMode.INVISIBLE,
        pus_profile=PusProfile.PUS_SAFE,
    )


class _FakeEngine:
    certificate_fingerprint_sha256 = "ab" * 32

    def __init__(self) -> None:
        self.signed_inputs: list[Path] = []

    def sign(self, input_path, output_path, signer=None, profile=None):  # noqa: ANN001, ANN201
        from types import SimpleNamespace

        self.signed_inputs.append(Path(input_path))
        Path(output_path).write_bytes(b"%PDF-1.4 fake signed\n%%EOF")
        return SimpleNamespace(success=True, output_path=Path(output_path), message="")


def _make_pdf(path: Path) -> None:
    import pikepdf

    with pikepdf.Pdf.new() as pdf:
        pdf.add_blank_page(page_size=(595, 842))
        pdf.save(path)


def test_compress_only_then_sign_compressed(tmp_path: Path) -> None:
    src = tmp_path / "a.pdf"
    _make_pdf(src)
    out_dir = tmp_path / "out"
    engine = _FakeEngine()
    prof = _profile()

    job = SigningJob(input_path=src)
    process_one_job(
        job, engine, prof, output_dir=out_dir, compress_only=True  # type: ignore[arg-type]
    )
    assert job.state is JobState.COMPRESSED
    assert job.state not in TERMINAL_STATES
    assert job.output_path is not None
    assert job.output_path.name.endswith("_compressed.pdf")
    assert job.output_path.is_file()

    # KÝ SỐ picks up COMPRESSED job
    process_one_job(job, engine, prof, output_dir=out_dir)  # type: ignore[arg-type]
    assert job.state is JobState.SUCCESS
    assert engine.signed_inputs, "must sign the compressed file"
    assert engine.signed_inputs[0].name.endswith("_compressed.pdf")
    assert job.output_path is not None
    assert job.output_path.name.endswith("_signed.pdf")


def test_compressed_not_terminal() -> None:
    assert JobState.COMPRESSED not in TERMINAL_STATES
