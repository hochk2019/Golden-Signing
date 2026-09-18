from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, r"E:\GPT\Golden Signing\src")
out = Path(r"E:\GPT\Golden Signing\scripts\ui_live_out.txt")


def ps_count() -> int:
    try:
        o = subprocess.check_output(
            ["tasklist", "/FI", "IMAGENAME eq powershell.exe", "/FO", "CSV", "/NH"],
            text=True,
            errors="replace",
        )
        return sum(1 for line in o.splitlines() if "powershell" in line.lower())
    except Exception as e:  # noqa: BLE001
        return -1


def main() -> None:
    lines: list[str] = []

    def log(msg: str) -> None:
        lines.append(msg)
        out.write_text("\n".join(lines), encoding="utf-8")

    try:
        log(f"ps0={ps_count()}")
        from golden_signing.certificate.catalog import clear_certificate_cache
        from PySide6.QtWidgets import QApplication
        from golden_signing.ui.main_window import MainWindow

        clear_certificate_cache()
        app = QApplication([])
        w = MainWindow()
        w.show()
        for _ in range(200):
            app.processEvents()
            time.sleep(0.05)
            if "Đang quét" not in w._token_note.text():
                break
        log(f"note={w._token_note.text()!r}")
        log(f"ps1={ps_count()}")
        pdf = Path(r"E:\GPT\Golden Signing\tests\fixtures\private\ecus_source.pdf")
        w.add_paths([pdf])
        for _ in range(20):
            app.processEvents()
            time.sleep(0.02)
        jobs = w._model.jobs() if hasattr(w, "_model") else []
        log(f"jobs={len(jobs)}")
        log(f"note2={w._token_note.text()!r}")
        log(f"ps2={ps_count()}")
        w.close()
        app.quit()
        log("UI_OFFSCREEN_OK")
    except Exception as e:  # noqa: BLE001
        import traceback

        log("FAIL " + traceback.format_exc())
        raise SystemExit(1) from e


if __name__ == "__main__":
    main()
    print(out.read_text(encoding="utf-8"))
