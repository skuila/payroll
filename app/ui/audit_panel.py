# ui/audit_panel.py — Panneau Audit complet (Anomalies + Questions) avec tri, filtre, export, signaux
# Version PyQt6
from __future__ import annotations
from typing import Optional, List, Dict
import csv
import io
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QListWidget,
    QLineEdit,
    QLabel,
    QPushButton,
    QFileDialog,
    QMenu,
    QApplication,
    QSizePolicy,
)
from PyQt6.QtCore import Qt, pyqtSignal, QSettings

APP_ORG = "SCP"
APP_NAME = "Payroll Analyzer"


class AuditPanel(QWidget):
    """
    Onglet 'Anomalies':
      - QTableWidget triable
      - Recherche (filtrage instantané)
      - Couleur facultative par sévérité (low/med/high) si fournie
      - Export CSV, copier
      - Persistance des largeurs de colonnes
      - signaux: anomalyActivated(rule, detail)

    Onglet 'Questions':
      - Suggestions dynamiques + depuis audit_result.get("questions", [])
      - signal: questionActivated(text)

    API acceptée (compat):
      - refresh(audit_result: dict)
      - set_audit_result(findings: dict)
      - refresh_audit(findings: dict)
      - suggest_questions(provider)
    """

    anomalyActivated = pyqtSignal(str, str)
    questionActivated = pyqtSignal(str)

    COL_RULE = 0
    COL_COUNT = 1
    COL_DETAIL = 2

    def __init__(self, provider: Optional[object] = None, parent=None):
        super().__init__(parent)
        self.provider = provider
        self._rows_cache: List[Dict] = []
        self._filter_text = ""

        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)

        self.tabs = QTabWidget(self)
        self.tabs.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.tabs, 1)

        # ---------- TAB ANOMALIES ----------
        tabA = QWidget(self)
        vA = QVBoxLayout(tabA)
        vA.setContentsMargins(0, 0, 0, 0)

        # Barre outils: recherche + actions
        tools = QHBoxLayout()
        tools.setSpacing(6)
        self.search = QLineEdit(tabA)
        self.search.setPlaceholderText("Rechercher (règle / détail)…")
        self.search.textChanged.connect(self._on_search_changed)
        self.btnCopy = QPushButton("Copier", tabA)
        self.btnCopy.clicked.connect(self._copy_selection)
        self.btnExport = QPushButton("Exporter CSV", tabA)
        self.btnExport.clicked.connect(self._export_csv)
        self.lblStatus = QLabel("", tabA)
        self.lblStatus.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        tools.addWidget(self.search, 1)
        tools.addWidget(self.btnCopy, 0)
        tools.addWidget(self.btnExport, 0)
        tools.addWidget(self.lblStatus, 0)
        vA.addLayout(tools)

        # Tableau
        self.tbl = QTableWidget(0, 3, tabA)
        self.tbl.setHorizontalHeaderLabels(["Règle", "Nb cas", "Détail"])
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setAlternatingRowColors(True)
        self.tbl.setSortingEnabled(True)  # tri natif
        self.tbl.setSelectionBehavior(QTableWidget.SelectRows)
        self.tbl.setSelectionMode(QTableWidget.ExtendedSelection)
        self.tbl.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tbl.customContextMenuRequested.connect(self._open_context_menu)
        self.tbl.itemDoubleClicked.connect(self._on_item_double_clicked)
        vA.addWidget(self.tbl, 1)

        # ---------- TAB QUESTIONS ----------
        tabQ = QWidget(self)
        vQ = QVBoxLayout(tabQ)
        vQ.setContentsMargins(0, 0, 0, 0)
        self.lst = QListWidget(tabQ)
        self.lst.itemDoubleClicked.connect(self._on_question_double_clicked)
        vQ.addWidget(self.lst, 1)

        # Ajout onglets
        self.tabs.addTab(tabA, "Anomalies")
        self.tabs.addTab(tabQ, "Questions")

        # Raccourcis “simples”
        self.search.installEventFilter(self)

        # Restaurer largeur colonnes si dispo
        self._restore_column_widths()

    # =========================================================
    # Compat: différentes entrées pour pousser l’audit
    # =========================================================
    def refresh(self, audit_result: dict):
        self._fill_table(audit_result or {})

    def set_audit_result(self, findings: dict):
        self._fill_table(findings or {})

    def refresh_audit(self, findings: dict):
        self._fill_table(findings or {})

    # =========================================================
    # Suggestions dynamiques (onglet Questions)
    # =========================================================
    def suggest_questions(self, provider=None):
        prov = provider or self.provider
        self.lst.clear()
        # 1) depuis l’audit si fourni directement
        #    (appelé avant/ailleurs)
        # ici on ne fait rien, c’est rempli par _fill_table si 'questions' présent

        # 2) dynamiques à partir du provider
        df = None
        if prov and hasattr(prov, "current_period_dataframe"):
            try:
                df = prov.current_period_dataframe()
            except Exception:
                df = None
        if (df is None or df.empty) and prov and hasattr(prov, "load_all"):
            try:
                df = prov.load_all()
            except Exception:
                df = None

        if df is not None and not df.empty:
            try:
                import pandas as pd

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
                for k in ("TypePaie", "Categorie", "CodePaie", "PosteBudgetaire"):
                    if k in df.columns:
                        self.lst.addItem(
                            f"Voir la répartition des montants par {k} sur les dernières périodes ?"
                        )
                        break
            except Exception:
                pass

        if self.lst.count() == 0:
            self.lst.addItem(
                "Charger des données puis relancer l’audit pour générer des suggestions."
            )

    # =========================================================
    # Remplissage du tableau & outils
    # =========================================================
    def _fill_table(self, audit_dict: dict):
        findings = (
            audit_dict.get("findings", []) if isinstance(audit_dict, dict) else []
        )
        questions = (
            audit_dict.get("questions", []) if isinstance(audit_dict, dict) else []
        )

        # Cache brut pour filtrage
        self._rows_cache = []
        for row in findings:
            self._rows_cache.append(
                {
                    "rule": str(row.get("rule", "")),
                    "count": str(row.get("count", "")),
                    "detail": str(row.get("detail", "")),
                    "severity": (
                        str(row.get("severity", ""))
                        if row.get("severity") is not None
                        else ""
                    ),
                }
            )

        # Appliquer filtre actuel
        self._apply_filter()

        # Questions provenant directement de l’audit
        if questions:
            self.lst.clear()
            for q in questions:
                self.lst.addItem(str(q))

    def _apply_filter(self):
        ft = (self._filter_text or "").lower()
        rows = [
            r
            for r in self._rows_cache
            if (ft in r["rule"].lower()) or (ft in r["detail"].lower()) or ft == ""
        ]
        self.tbl.setSortingEnabled(False)
        self.tbl.setRowCount(len(rows))
        for r, row in enumerate(rows):
            it_rule = QTableWidgetItem(row["rule"])
            it_cnt = QTableWidgetItem(row["count"])
            it_det = QTableWidgetItem(row["detail"])
            # Alignement numérique pour "Nb cas"
            it_cnt.setTextAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )

            self.tbl.setItem(r, self.COL_RULE, it_rule)
            self.tbl.setItem(r, self.COL_COUNT, it_cnt)
            self.tbl.setItem(r, self.COL_DETAIL, it_det)

            # Couleur de fond par sévérité si présente (tons doux compatibles)
            sev = (row.get("severity", "") or "").lower()
            if sev in ("high", "élevé", "eleve"):
                it_rule.setBackground(Qt.red)
                it_rule.setForeground(Qt.white)
                it_cnt.setBackground(Qt.red)
                it_cnt.setForeground(Qt.white)
                it_det.setBackground(Qt.red)
                it_det.setForeground(Qt.white)
            elif sev in ("med", "moyen", "medium"):
                it_rule.setBackground(Qt.yellow)
                it_cnt.setBackground(Qt.yellow)
                it_det.setBackground(Qt.yellow)
            elif sev in ("low", "faible"):
                # un gris très léger
                it_rule.setBackground(Qt.lightGray)
                it_cnt.setBackground(Qt.lightGray)
                it_det.setBackground(Qt.lightGray)

        self.tbl.setSortingEnabled(True)
        self.tbl.resizeColumnsToContents()
        self._update_status(len(rows), len(self._rows_cache))
        self._save_column_widths()

    # =========================================================
    # UI helpers
    # =========================================================
    def _on_search_changed(self, text: str):
        self._filter_text = text or ""
        self._apply_filter()

    def _update_status(self, shown: int, total: int):
        self.lblStatus.setText(f"{shown} / {total}")

    def _open_context_menu(self, pos):
        menu = QMenu(self)
        a_copy = menu.addAction("Copier")
        a_copy_all = menu.addAction("Copier tout")
        a_export = menu.addAction("Exporter CSV…")
        act = menu.exec(self.tbl.viewport().mapToGlobal(pos))
        if act == a_copy:
            self._copy_selection()
        elif act == a_copy_all:
            self._copy_all()
        elif act == a_export:
            self._export_csv()

    def _copy_selection(self):
        rows = sorted({i.row() for i in self.tbl.selectedIndexes()})
        if not rows:
            return
        output = io.StringIO()
        w = csv.writer(output, delimiter="\t")
        # entêtes
        headers = [
            self.tbl.horizontalHeaderItem(c).text()
            for c in range(self.tbl.columnCount())
        ]
        w.writerow(headers)
        # lignes
        for r in rows:
            w.writerow([self._item_text(r, c) for c in range(self.tbl.columnCount())])
        QApplication.clipboard().setText(output.getvalue())

    def _copy_all(self):
        output = io.StringIO()
        w = csv.writer(output, delimiter="\t")
        headers = [
            self.tbl.horizontalHeaderItem(c).text()
            for c in range(self.tbl.columnCount())
        ]
        w.writerow(headers)
        for r in range(self.tbl.rowCount()):
            w.writerow([self._item_text(r, c) for c in range(self.tbl.columnCount())])
        QApplication.clipboard().setText(output.getvalue())

    def _export_csv(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Exporter CSV", "audit.csv", "CSV (*.csv)"
        )
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            headers = [
                self.tbl.horizontalHeaderItem(c).text()
                for c in range(self.tbl.columnCount())
            ]
            w.writerow(headers)
            for r in range(self.tbl.rowCount()):
                w.writerow(
                    [self._item_text(r, c) for c in range(self.tbl.columnCount())]
                )

    def _item_text(self, row: int, col: int) -> str:
        it = self.tbl.item(row, col)
        return "" if it is None else it.text()

    def _on_item_double_clicked(self, it):
        if not it:
            return
        r = it.row()
        rule = self._item_text(r, self.COL_RULE)
        detail = self._item_text(r, self.COL_DETAIL)
        self.anomalyActivated.emit(rule, detail)

    def _on_question_double_clicked(self, it):
        if it:
            self.questionActivated.emit(it.text())

    # =========================================================
    # Persistance tailles de colonnes
    # =========================================================
    def _save_column_widths(self):
        try:
            s = QSettings(APP_ORG, APP_NAME)
            s.setValue("audit/col_w_0", self.tbl.columnWidth(0))
            s.setValue("audit/col_w_1", self.tbl.columnWidth(1))
            s.setValue("audit/col_w_2", self.tbl.columnWidth(2))
        except Exception:
            pass

    def _restore_column_widths(self):
        try:
            s = QSettings(APP_ORG, APP_NAME)
            for i in (0, 1, 2):
                w = s.value(f"audit/col_w_{i}", None)
                if w is not None:
                    self.tbl.setColumnWidth(i, int(w))
        except Exception:
            pass

    # =========================================================
    # Raccourcis “simples” (Ctrl+F/C/S)
    # =========================================================
    def eventFilter(self, obj, ev):
        # Ici on pourrait ajouter des raccourcis globaux si besoin
        return super().eventFilter(obj, ev)
