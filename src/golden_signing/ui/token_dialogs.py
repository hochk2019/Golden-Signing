"""Token cert picker + PIN dialogs (Phase 10 polish)."""

from __future__ import annotations

from typing import Any
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from golden_signing.ui.cert_label import common_name_from_subject, mst_from_subject
from golden_signing.ui.theme import apply_window_icon

__all__ = ["CertPickerDialog", "PinDialog"]


def _expiry_text(cert: Any) -> str:
    val = str(getattr(cert, "not_valid_after", "") or "")
    return val[:10] if val else "—"


class CertCard(QFrame):
    """Selectable certificate row with brand-aligned card chrome."""

    def __init__(
        self,
        cert: Any,
        *,
        selected: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._cert = cert
        self.setObjectName("certCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        row = QHBoxLayout(self)
        row.setContentsMargins(14, 12, 14, 12)
        row.setSpacing(12)

        self._radio = QRadioButton()
        self._radio.setChecked(selected)
        self._radio.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        row.addWidget(self._radio, alignment=Qt.AlignmentFlag.AlignTop)
        self.set_selected(selected)

        col = QVBoxLayout()
        col.setSpacing(4)
        cn = common_name_from_subject(getattr(cert, "subject", "") or "")
        self._title = QLabel(cn)
        self._title.setObjectName("certCardTitle")
        self._title.setWordWrap(True)
        col.addWidget(self._title)

        mst = mst_from_subject(getattr(cert, "subject", "") or "")
        token = getattr(cert, "token_label", None) or "USB token"
        lib = getattr(cert, "pkcs11_library", None)
        lib_name = Path(str(lib)).name if lib else ""
        meta_bits = [f"Token: {token}", f"Hết hạn: {_expiry_text(cert)}"]
        if lib_name:
            meta_bits.append(f"DLL: {lib_name}")
        if mst:
            meta_bits.insert(0, f"MST: {mst}")
        meta = QLabel("  ·  ".join(meta_bits))
        meta.setObjectName("certCardMeta")
        col.addWidget(meta)

        serial = str(getattr(cert, "serial", "") or "")
        if serial:
            sn = QLabel(f"Serial: {serial[:28]}")
            sn.setObjectName("certCardMeta")
            col.addWidget(sn)

        col.addStretch(1)
        row.addLayout(col, stretch=1)

    @property
    def cert(self) -> Any:
        return self._cert

    def set_selected(self, on: bool) -> None:
        self._radio.setChecked(on)
        self.setProperty("selected", "true" if on else "false")
        # Force QSS re-evaluation
        self.style().unpolish(self)
        self.style().polish(self)


class CertPickerDialog(QDialog):
    """Polished certificate chooser — card list, one primary action."""

    def __init__(self, certs: list, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        apply_window_icon(self)
        self.setWindowTitle("Chọn chứng thư số")
        self.setModal(True)
        self.setMinimumSize(480, 420)
        self.setMaximumWidth(560)
        self._certs = list(certs)
        self._cards: list[CertCard] = []
        self._selected_index = 0 if self._certs else -1

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        header = QFrame()
        header.setObjectName("dlgHeader")
        hlay = QVBoxLayout(header)
        hlay.setContentsMargins(20, 18, 20, 14)
        hlay.setSpacing(4)
        title = QLabel("Chọn chứng thư số")
        title.setObjectName("dlgTitle")
        hlay.addWidget(title)
        sub = QLabel("Chứng thư đang có trên USB token")
        sub.setObjectName("dlgSubtitle")
        hlay.addWidget(sub)
        root.addWidget(header)

        body = QWidget()
        body.setObjectName("dlgBody")
        blay = QVBoxLayout(body)
        blay.setContentsMargins(16, 12, 16, 8)
        blay.setSpacing(8)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setObjectName("certScroll")
        inner = QWidget()
        inner_lay = QVBoxLayout(inner)
        inner_lay.setContentsMargins(0, 0, 4, 0)
        inner_lay.setSpacing(8)

        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        for i, cert in enumerate(self._certs):
            card = CertCard(cert, selected=(i == 0))
            card._radio.clicked.connect(  # noqa: SLF001
                lambda _=False, idx=i: self.select_index(idx)
            )
            card.mousePressEvent = (  # type: ignore[method-assign]
                lambda ev, idx=i: self._on_card_click(idx, ev)
            )
            self._group.addButton(card._radio, i)  # noqa: SLF001
            self._cards.append(card)
            inner_lay.addWidget(card)
        inner_lay.addStretch(1)
        scroll.setWidget(inner)
        blay.addWidget(scroll, stretch=1)

        if not self._certs:
            empty = QLabel("Không tìm thấy chứng thư số trên token.")
            empty.setObjectName("dlgSubtitle")
            blay.addWidget(empty)
        root.addWidget(body, stretch=1)

        footer = QFrame()
        footer.setObjectName("dlgFooter")
        flay = QHBoxLayout(footer)
        flay.setContentsMargins(16, 12, 16, 14)
        flay.addStretch(1)
        cancel = QPushButton("Hủy")
        cancel.setObjectName("btnSecondary")
        cancel.clicked.connect(self.reject)
        flay.addWidget(cancel)
        self._ok = QPushButton("Chọn chứng thư")
        self._ok.setObjectName("primaryCta")
        self._ok.setEnabled(bool(self._certs))
        self._ok.clicked.connect(self.accept)
        flay.addWidget(self._ok)
        root.addWidget(footer)

    def _on_card_click(self, index: int, _ev: object) -> None:
        self.select_index(index)

    def select_index(self, index: int) -> None:
        if index < 0 or index >= len(self._cards):
            return
        self._selected_index = index
        for i, card in enumerate(self._cards):
            card.set_selected(i == index)

    def selected_cert(self) -> Any | None:
        if 0 <= self._selected_index < len(self._certs):
            return self._certs[self._selected_index]
        return None


class PinDialog(QDialog):
    """PIN entry — never stored; optional show/hide."""

    def __init__(
        self,
        *,
        company: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        apply_window_icon(self)
        self.setWindowTitle("PIN chữ ký số")
        self.setModal(True)
        self.setMinimumWidth(420)
        self.setMaximumWidth(480)
        self._pin = ""

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        header = QFrame()
        header.setObjectName("dlgHeader")
        hlay = QVBoxLayout(header)
        hlay.setContentsMargins(20, 18, 20, 14)
        hlay.setSpacing(4)
        title = QLabel("Nhập PIN chữ ký số")
        title.setObjectName("dlgTitle")
        hlay.addWidget(title)
        sub = QLabel(company or "USB token")
        sub.setObjectName("dlgSubtitle")
        sub.setWordWrap(True)
        hlay.addWidget(sub)
        root.addWidget(header)

        body = QWidget()
        body.setObjectName("dlgBody")
        blay = QVBoxLayout(body)
        blay.setContentsMargins(20, 16, 20, 8)
        blay.setSpacing(8)

        pin_label = QLabel("Mã PIN")
        pin_label.setObjectName("fieldLabel")
        blay.addWidget(pin_label)

        pin_row = QHBoxLayout()
        pin_row.setSpacing(6)
        self._edit = QLineEdit()
        self._edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._edit.setPlaceholderText("Nhập PIN token…")
        self._edit.setMinimumHeight(36)
        self._edit.setObjectName("pinInput")
        self._edit.returnPressed.connect(self._accept_if_valid)
        pin_row.addWidget(self._edit, stretch=1)
        self._toggle = QPushButton("Hiện")
        self._toggle.setObjectName("btnSecondary")
        self._toggle.setCheckable(True)
        self._toggle.setFixedHeight(36)
        self._toggle.clicked.connect(self._on_toggle)
        pin_row.addWidget(self._toggle)
        blay.addLayout(pin_row)

        hint = QLabel("PIN chỉ dùng để mở session token — không lưu trên máy tính.")
        hint.setObjectName("dlgSubtitle")
        hint.setWordWrap(True)
        blay.addWidget(hint)
        blay.addSpacing(8)
        root.addWidget(body)

        footer = QFrame()
        footer.setObjectName("dlgFooter")
        flay = QHBoxLayout(footer)
        flay.setContentsMargins(16, 12, 16, 14)
        flay.addStretch(1)
        cancel = QPushButton("Hủy")
        cancel.setObjectName("btnSecondary")
        cancel.clicked.connect(self.reject)
        flay.addWidget(cancel)
        self._ok = QPushButton("Xác nhận")
        self._ok.setObjectName("primaryCta")
        self._ok.clicked.connect(self._accept_if_valid)
        flay.addWidget(self._ok)
        root.addWidget(footer)

        self._edit.setFocus()

    def _on_toggle(self) -> None:
        show = self._toggle.isChecked()
        self._edit.setEchoMode(
            QLineEdit.EchoMode.Normal if show else QLineEdit.EchoMode.Password
        )
        self._toggle.setText("Ẩn" if show else "Hiện")

    def _accept_if_valid(self) -> None:
        text = self._edit.text().strip()
        if not text:
            self._edit.setFocus()
            return
        self._pin = text
        self._edit.clear()
        self.accept()

    def pin(self) -> str:
        return self._pin
