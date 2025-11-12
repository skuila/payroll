# ui/panel_frame.py — carte "Power BI" avec en-tête + boutons gris (réduire/agrandir) - PyQt6
from PyQt6.QtWidgets import (
    QFrame,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QToolButton,
    QWidget,
)
from PyQt6.QtCore import Qt, QSize


class PanelFrame(QFrame):
    def __init__(self, title: str, content: QWidget, on_maximize=None, parent=None):
        super().__init__(parent)
        self._content = content
        self._on_maximize = on_maximize
        self._collapsed = False

        self.setObjectName("Card")  # stylisé par ton thème Power BI
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(8)

        head = QHBoxLayout()
        head.setSpacing(8)
        title_lbl = QLabel(title)
        title_lbl.setObjectName("PanelTitle")  # Stylé par QSS
        head.addWidget(title_lbl, 1)

        self.btn_collapse = QToolButton(self)
        self.btn_collapse.setText("▼")
        self.btn_collapse.setToolTip("Réduire/Restaurer")
        self.btn_collapse.setFixedSize(QSize(24, 22))
        self.btn_collapse.clicked.connect(self._toggle_collapse)
        head.addWidget(self.btn_collapse, 0, Qt.AlignmentFlag.AlignRight)

        self.btn_max = QToolButton(self)
        self.btn_max.setText("⤢")
        self.btn_max.setToolTip("Agrandir ce panneau")
        self.btn_max.setFixedSize(QSize(24, 22))
        if callable(on_maximize):
            self.btn_max.clicked.connect(lambda: on_maximize(self))
        head.addWidget(self.btn_max, 0, Qt.AlignmentFlag.AlignRight)

        lay.addLayout(head)
        lay.addWidget(self._content, 1)

    def _toggle_collapse(self):
        self._collapsed = not self._collapsed
        self._content.setVisible(not self._collapsed)
        self.btn_collapse.setText("▲" if self._collapsed else "▼")
