# ui/assistant_panel.py — Agent IA intégré (Chat, Questions, Audit) avec accès provider
# Version PyQt6
from __future__ import annotations
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTextEdit,
    QPushButton,
    QListWidget,
    QTabWidget,
    QMessageBox,
)
import pandas as pd


class AssistantPanel(QWidget):
    """
    Onglets:
      - Agent IA (chat simple)
      - Questions (suggestions proactives)
      - Audit (résultats)
    """

    def __init__(self, provider, parent=None):
        super().__init__(parent)
        self.provider = provider

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        self.tabs = QTabWidget(self)
        root.addWidget(self.tabs, 1)

        # --- Tab Chat ---
        self.tab_chat = QWidget(self)
        self.tabs.addTab(self.tab_chat, "Agent IA")
        v1 = QVBoxLayout(self.tab_chat)
        self.input = QTextEdit(self.tab_chat)
        self.input.setPlaceholderText("Pose ta question…")
        self.out = QTextEdit(self.tab_chat)
        self.out.setReadOnly(True)
        btns = QHBoxLayout()
        self.btn_send = QPushButton("Envoyer", self.tab_chat)
        btns.addStretch(1)
        btns.addWidget(self.btn_send)
        v1.addWidget(self.out, 1)
        v1.addWidget(self.input, 0)
        v1.addLayout(btns)

        # --- Tab Questions (suggestions) ---
        self.tab_q = QWidget(self)
        self.tabs.addTab(self.tab_q, "Questions")
        v2 = QVBoxLayout(self.tab_q)
        self.lst = QListWidget(self.tab_q)
        self.btn_runq = QPushButton("Lancer la question sélectionnée", self.tab_q)
        v2.addWidget(self.lst, 1)
        v2.addWidget(self.btn_runq, 0)

        # --- Tab Audit ---
        self.tab_a = QWidget(self)
        self.tabs.addTab(self.tab_a, "Audit")
        v3 = QVBoxLayout(self.tab_a)
        self.audit_view = QTextEdit(self.tab_a)
        self.audit_view.setReadOnly(True)
        v3.addWidget(self.audit_view, 1)

        # Signals
        self.btn_send.clicked.connect(self._on_send)
        self.btn_runq.clicked.connect(self._run_selected_question)
        self.lst.itemDoubleClicked.connect(lambda *_: self._run_selected_question())

    # ==== Chat ====
    def _on_send(self):
        q = (self.input.toPlainText() or "").strip()
        if not q:
            return
        try:
            # On fabrique un contexte métier via l’agent
            from agent.payroll_agent import answer

            ans = answer(q, model="gpt-4o-mini")  # modèle par défaut de ta base
            self.out.append(f">> {q}")
            self.out.append(ans)
            self.out.append("")
        except Exception as e:
            QMessageBox.warning(self, "Agent IA", f"Erreur: {e}")

    # ==== Audit ====
    def refresh_audit(self, findings: dict):
        try:
            if not findings:
                self.audit_view.setPlainText("(aucun résultat)")
                return
            lines = []
            for f in findings.get("findings", []):
                lines.append(f"• {f.get('rule','?')} — {f.get('count',0)}")
            for q in findings.get("questions", []):
                lines.append(f"? {q}")
            self.audit_view.setPlainText("\n".join(lines) or "(aucun résultat)")
        except Exception as e:
            self.audit_view.setPlainText(f"Erreur audit: {e}")

    # ==== Suggestions proactives ====
    def suggest_questions(self, provider):
        try:
            df = provider.current_period_dataframe()
            if df is None or df.empty:
                # On tente global si le provider expose un full dataset
                try:
                    df = provider.load_all()
                except Exception:
                    pass

            self.lst.clear()
            # Si colonnes dates disponibles, on propose une analyse d’évolution
            years = []
            for col in ["Date de paie", "date_paie", "DatePaie", "Date"]:
                if col in df.columns:
                    s = (
                        pd.to_datetime(df[col], errors="coerce")
                        .dt.year.dropna()
                        .astype(int)
                    )
                    if not s.empty:
                        years = sorted(s.unique().tolist())
                        break
            if years and (max(years) - min(years) >= 3):
                self.lst.addItem(
                    f"Voulez-vous l’évolution salariale par titre d’emploi entre {min(years)} et {max(years)} ?"
                )

            # Idées additionnelles (toujours sans casser le flux si colonnes manquantes)
            for k in ("TypePaie", "Categorie", "CodePaie", "PosteBudgetaire"):
                if k in df.columns:
                    self.lst.addItem(
                        f"Voir la répartition des montants par {k} sur les dernières périodes ?"
                    )
                    break

            if self.lst.count() == 0:
                self.lst.addItem("Comparer le net mensuel sur 6 dernières périodes ?")
        except Exception as e:
            self.lst.addItem(f"(Suggestion indisponible: {e})")

    def _run_selected_question(self):
        item = self.lst.currentItem()
        if not item:
            return
        self.input.setText(item.text())
        self.tabs.setCurrentWidget(self.tab_chat)
        self._on_send()
