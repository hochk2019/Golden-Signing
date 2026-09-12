"""Application entrypoint (Phase 5)."""

from __future__ import annotations


def main() -> None:
    import os
    import sys

    # Allow headless smoke without display
    if os.environ.get("GOLDEN_SIGNING_OFFSCREEN") == "1":
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from golden_signing.security.redaction import setup_app_logging

    setup_app_logging()

    from golden_signing.ui.main_window import run_app

    sys.exit(run_app())


if __name__ == "__main__":
    main()
