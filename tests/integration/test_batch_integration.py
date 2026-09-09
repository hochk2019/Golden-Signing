"""Batch integration: 10 PDFs, one corrupt (T5)."""

from __future__ import annotations

import shutil
from pathlib import Path

from golden_signing.batch.queue import BatchEngine
from golden_signing.batch.state import JobState
from golden_signing.pdf.integrity import sha256_file
from golden_signing.signing.pdf_signer import TestCertPdfSigner
from golden_signing.signing.profiles import pus_safe_profile

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "private"
SOURCE_PDF = FIXTURES / "ecus_source.pdf"
SOURCE_SHA256 = "76df3ed717a0077e4def2612005467ba8a21e095ffbe9dc076d14a150ec9b272"


def test_batch_ten_files_one_corrupt(tmp_path: Path) -> None:
    assert sha256_file(SOURCE_PDF) == SOURCE_SHA256
    engine = TestCertPdfSigner()
    profile = pus_safe_profile(certificate_fingerprint_sha256=engine.certificate_fingerprint_sha256)
    paths: list[Path] = []
    for i in range(9):
        p = tmp_path / f"doc_{i:02d}.pdf"
        shutil.copy(SOURCE_PDF, p)
        paths.append(p)
    corrupt = tmp_path / "doc_bad.pdf"
    corrupt.write_bytes(b"%%corrupt%%")
    paths.insert(4, corrupt)

    out = tmp_path / "signed"
    batch = BatchEngine(engine, profile, output_dir=out)
    batch.enqueue_paths(paths)
    result = batch.run()

    assert result.total == 10
    assert result.success == 9
    assert result.failed == 1
    assert result.all_terminal
    # original fixture untouched
    assert sha256_file(SOURCE_PDF) == SOURCE_SHA256
    # outputs exist for successes
    successes = [j for j in result.jobs if j.state is JobState.SUCCESS]
    assert len(successes) == 9
    for j in successes:
        assert j.output_path is not None
        assert j.output_path.exists()
        # sources not overwritten
        assert j.input_path.exists()
