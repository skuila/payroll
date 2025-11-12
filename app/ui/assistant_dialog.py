# ui/assistant_dialog.py — boîte de dialogue Assistant (Q&A)
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QTextEdit,
    QPushButton,
    QComboBox,
)
from PyQt6.QtCore import Qt
from agent.payroll_agent import answer

MODELS = ["gpt-5-mini", "gpt-5"]  # adapter selon ton contrat


class AssistantDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Assistant (ChatGPT Business)")
        self.resize(720, 520)

        root = QVBoxLayout(self)
        root.setSpacing(8)
        root.setContentsMargins(10, 10, 10, 10)

        # question
        box = QHBoxLayout()
        box.addWidget(QLabel("Modèle:"))
        self.model_combo = QComboBox()
        self.model_combo.addItems(MODELS)
        self.model_combo.setCurrentIndex(0)
        box.addWidget(self.model_combo)
        root.addLayout(box)

        self.input = QTextEdit(self)
        self.input.setPlaceholderText(
            "Pose ta question métier (ex: Montre-moi les 3 périodes avec le plus de nets négatifs)."
        )
        self.input.setAcceptRichText(False)
        root.addWidget(self.input, 1)

        # boutons
        btn_row = QHBoxLayout()
        self.btn_ask = QPushButton("Poser la question (Ctrl+Entrée)")
        self.btn_close = QPushButton("Fermer")
        btn_row.addWidget(self.btn_ask)
        btn_row.addStretch(1)
        btn_row.addWidget(self.btn_close)
        root.addLayout(btn_row)

        self.output = QTextEdit(self)
        self.output.setReadOnly(True)
        root.addWidget(self.output, 2)

        self.btn_ask.clicked.connect(self.on_ask)
        self.btn_close.clicked.connect(self.accept)
        self.input.keyPressEvent = self._wrap_keypress(self.input.keyPressEvent)

    def _wrap_keypress(self, orig):
        def handler(ev):
            if (ev.modifiers() & Qt.KeyboardModifier.ControlModifier) and ev.key() in (
                Qt.Key.Key_Return,
                Qt.Key.Key_Enter,
            ):
                self.on_ask()
                return
            return orig(ev)

        return handler

    def on_ask(self):
        q = (self.input.toPlainText() or "").strip()
        if not q:
            self.output.setPlainText("Entrez une question.")
            return
        self.btn_ask.setEnabled(False)
        self.output.setPlainText("…")
        try:
            model = self.model_combo.currentText()
            resp = answer(q, model=model)
            self.output.setPlainText(resp)
        except Exception as e:
            self.output.setPlainText(f"Erreur: {e}")
        finally:
            self.btn_ask.setEnabled(True)
