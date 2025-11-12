# ui/table_panel.py — Table complète (modèle Qt ou DataFrame) + persistance colonnes + menu contextuel (PyQt6)
from __future__ import annotations
import os
import io
import csv
from PyQt6.QtCore import Qt, QAbstractTableModel, QModelIndex, QVariant, QSettings
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QTableView,
    QSizePolicy,
    QMessageBox,
    QMenu,
    QApplication,
)

try:
    import pandas as pd
except Exception:
    pd = None  # tolérant si pandas absent


class _DataFrameModel(QAbstractTableModel):
    """Modèle léger pour afficher un DataFrame quand le provider ne fournit pas déjà un modèle Qt."""

    def __init__(self, df=None, parent=None):
        super().__init__(parent)
        if df is None:
            self._df = pd.DataFrame() if pd is not None else None
        else:
            # normaliser (list/dict -> DataFrame si possible)
            if pd is not None and not isinstance(df, pd.DataFrame):
                try:
                    df = pd.DataFrame(df)
                except Exception:
                    pass
            self._df = df

    def rowCount(self, parent=QModelIndex()):
        if parent.isValid():
            return 0
        return 0 if self._df is None else len(self._df)

    def columnCount(self, parent=QModelIndex()):
        if parent.isValid():
            return 0
        if self._df is None:
            return 0
        try:
            return len(self._df.columns)
        except Exception:
            return 0

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or self._df is None:
            return QVariant()
        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
            try:
                val = self._df.iat[index.row(), index.column()]
                # éviter "nan" visible si pandas
                if pd is not None:
                    try:
                        if val is None or (
                            isinstance(val, float) and (val != val)
                        ):  # NaN check
                            return ""
                    except Exception:
                        pass
                return "" if val is None else str(val)
            except Exception:
                return ""
        return QVariant()

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role != Qt.ItemDataRole.DisplayRole or self._df is None:
            return QVariant()
        if orientation == Qt.Orientation.Horizontal:
            try:
                return str(self._df.columns[section])
            except Exception:
                return f"C{section+1}"
        else:
            return str(section + 1)


class TablePanel(QWidget):
    """
    Panneau Table :
    - charge un modèle Qt du provider si disponible, sinon DataFrame
    - persiste les largeurs de colonnes (QSettings)
    - menu contextuel (copier, copier tout, exporter CSV)
    - API : setModel(model), set_dataframe(df), refresh(), save_columns()
    """

    SETTINGS_GEOM = "TablePanel/columns"

    def __init__(self, provider, parent=None):
        super().__init__(parent)
        self.provider = provider

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(6)

        self.view = QTableView(self)
        # --- Politiques de taille pour éviter l'écrasement ---
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.view.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.view.setMinimumHeight(240)  # évite la table invisible
        self.view.setAlternatingRowColors(True)
        self.view.setSortingEnabled(True)
        self.view.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.view.setSelectionMode(QTableView.SelectionMode.ExtendedSelection)
        self.view.setWordWrap(False)
        self.view.horizontalHeader().setStretchLastSection(
            False
        )  # on contrôle les largeurs
        self.view.horizontalHeader().setDefaultSectionSize(140)
        self.view.verticalHeader().setVisible(False)
        self.view.setCornerButtonEnabled(False)

        # menu contextuel
        self.view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.view.customContextMenuRequested.connect(self._open_context_menu)

        root.addWidget(self.view, 1)

        # Charge le modèle depuis le provider
        self._load_model()
        # Restaurer largeurs de colonnes si déjà mémorisées
        self._restore_columns()

    # ------ Public API ------
    def setModel(self, model):
        """
        Compat : si ton code appelle déjà setModel, on conserve ce comportement.
        """
        self.view.setModel(model)
        try:
            self.view.resizeColumnsToContents()
        except Exception:
            pass
        self._restore_columns()

    def set_dataframe(self, df):
        """
        Nouvelle API (utilisée par MainWindow.refresh_all) : alimente la table avec un DataFrame.
        """
        model = _DataFrameModel(df, self)
        self.view.setModel(model)
        try:
            self.view.resizeColumnsToContents()
        except Exception:
            pass
        self._restore_columns()

    def refresh(self):
        """À appeler quand les filtres changent ou après import."""
        self._load_model()
        self._restore_columns()

    # ------ Internes ------
    def _load_model(self):
        try:
            # 1) si le provider expose un modèle Qt existant, on le garde
            if hasattr(self.provider, "get_table_model"):
                model = self.provider.get_table_model()
                if model is not None:
                    self.view.setModel(model)
                    try:
                        self.view.resizeColumnsToContents()
                    except Exception:
                        pass
                    return
            # 2) sinon, essayer un DataFrame "table"
            df = None
            for meth in (
                "get_table_df",
                "get_dataframe",
                "current_period_dataframe",
                "load_all",
            ):
                if hasattr(self.provider, meth):
                    try:
                        df = getattr(self.provider, meth)()
                        if df is not None:
                            break
                    except Exception:
                        pass
            self.view.setModel(_DataFrameModel(df, self))
            try:
                self.view.resizeColumnsToContents()
            except Exception:
                pass
        except Exception as e:
            QMessageBox.critical(
                self, "Table", f"Erreur de chargement du modèle :\n{e}"
            )

    def _restore_columns(self):
        """Restaure/initialise des largeurs raisonnables."""
        try:
            settings = QSettings()
            widths = settings.value(self.SETTINGS_GEOM, None)
            model = self.view.model()
            cols = model.columnCount() if model else 0

            if widths:
                if isinstance(widths, str):
                    widths = [int(x) for x in widths.split(",") if x.strip().isdigit()]
                # applique si tailles compatibles
                for c in range(min(cols, len(widths))):
                    w = max(80, min(380, int(widths[c])))
                    self.view.setColumnWidth(c, w)
            else:
                # première fois : largeur raisonnable
                for c in range(cols):
                    self.view.setColumnWidth(c, 140 if c > 0 else 180)
        except Exception:
            pass

    def save_columns(self):
        """À appeler avant fermeture si tu veux mémoriser les largeurs."""
        try:
            settings = QSettings()
            model = self.view.model()
            cols = model.columnCount() if model else 0
            widths = [str(self.view.columnWidth(c)) for c in range(cols)]
            settings.setValue(self.SETTINGS_GEOM, ",".join(widths))
        except Exception:
            pass

    # ------ Menu contextuel ------
    def _open_context_menu(self, pos):
        menu = QMenu(self)
        a_copy = menu.addAction("Copier")
        a_copy_all = menu.addAction("Copier tout")
        a_export = menu.addAction("Exporter CSV…")
        act = menu.exec(self.view.viewport().mapToGlobal(pos))
        if not act:
            return
        if act == a_copy:
            self._copy_selection()
        elif act == a_copy_all:
            self._copy_all()
        elif act == a_export:
            self._export_csv()

    def _copy_selection(self):
        idxs = sorted({i.row() for i in self.view.selectedIndexes()})
        if not idxs:
            return
        output = io.StringIO()
        w = csv.writer(output, delimiter="\t")
        headers = [
            self.view.model().headerData(
                c, Qt.Orientation.Horizontal, Qt.ItemDataRole.DisplayRole
            )
            for c in range(self.view.model().columnCount())
        ]
        w.writerow(headers)
        for r in idxs:
            row = []
            for c in range(self.view.model().columnCount()):
                row.append(self._data_text(r, c))
            w.writerow(row)
        QApplication.clipboard().setText(output.getvalue())

    def _copy_all(self):
        model = self.view.model()
        if not model:
            return
        output = io.StringIO()
        w = csv.writer(output, delimiter="\t")
        headers = [
            model.headerData(c, Qt.Orientation.Horizontal, Qt.ItemDataRole.DisplayRole)
            for c in range(model.columnCount())
        ]
        w.writerow(headers)
        for r in range(model.rowCount()):
            row = [self._data_text(r, c) for c in range(model.columnCount())]
            w.writerow(row)
        QApplication.clipboard().setText(output.getvalue())

    def _export_csv(self):
        # pas d'appel à QFileDialog ici pour rester simple et éviter conflits ;
        # si tu préfères une boîte de dialogue, ajoute-la côté action menu.
        try:
            # dossier courant de l'appli
            base = os.path.abspath(os.getcwd())
            path = os.path.join(base, "table_export.csv")
            model = self.view.model()
            with open(path, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                headers = [
                    model.headerData(
                        c, Qt.Orientation.Horizontal, Qt.ItemDataRole.DisplayRole
                    )
                    for c in range(model.columnCount())
                ]
                w.writerow(headers)
                for r in range(model.rowCount()):
                    row = [self._data_text(r, c) for c in range(model.columnCount())]
                    w.writerow(row)
            QMessageBox.information(self, "Export CSV", f"Exporté :\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Export CSV", f"Erreur d'export :\n{e}")

    def _data_text(self, r: int, c: int) -> str:
        it = self.view.model().index(r, c)
        val = self.view.model().data(it, Qt.ItemDataRole.DisplayRole)
        return "" if val is None else str(val)

    # ------ Persistance ------
    def closeEvent(self, e):
        self.save_columns()
        return super().closeEvent(e)
