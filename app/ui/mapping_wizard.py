# ui/mapping_wizard.py
# ========================================
# ASSISTANT MAPPING COLONNES (UI PyQt6)
# ========================================
# Interface utilisateur pour confirmer/corriger le mapping auto-détecté

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QProgressBar,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QTextEdit,
    QSplitter,
    QWidget,
    QComboBox,
)
from PyQt6.QtCore import Qt, pyqtSignal
from typing import Dict, List


class MappingWizard(QDialog):
    """
    Assistant de mapping colonnes

    Fonctionnalités:
    - Affichage colonnes détectées avec barres de confiance
    - Drag & drop pour réassigner
    - Preview transformations sur échantillon
    - Sauvegarde profil
    """

    mapping_confirmed = pyqtSignal(dict)  # Émis quand utilisateur confirme

    def __init__(
        self,
        headers: List[str],
        detection_result: Dict,
        sample_rows: List[List],
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Assistant Mapping Colonnes")
        self.resize(1200, 800)

        self.headers = headers
        self.detection_result = detection_result
        self.sample_rows = sample_rows
        self.current_mapping = detection_result["global_suggestion"]["mapping"].copy()
        self.current_confidence = detection_result["global_suggestion"][
            "confidence"
        ].copy()

        self.setup_ui()
        self.populate_detected_mapping()

    def setup_ui(self):
        """Construit l'interface"""
        layout = QVBoxLayout(self)

        # Titre
        title = QLabel("<h2>🧭 Assistant Détection Colonnes</h2>")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # Splitter principal (gauche: mapping, droite: preview)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)

        # ===== PANNEAU GAUCHE: Mapping =====

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)

        info_label = QLabel(
            "✓ Vérifiez le mapping détecté ci-dessous\n"
            "⚠️ Corrigez si nécessaire avec les menus déroulants\n"
            "💡 Les barres de confiance indiquent la fiabilité"
        )
        info_label.setWordWrap(True)
        left_layout.addWidget(info_label)

        # Table mapping
        self.mapping_table = QTableWidget()
        self.mapping_table.setColumnCount(4)
        self.mapping_table.setHorizontalHeaderLabels(
            ["Type Cible", "Colonne Détectée", "Confiance", "Changer Vers"]
        )
        self.mapping_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        left_layout.addWidget(self.mapping_table)

        splitter.addWidget(left_panel)

        # ===== PANNEAU DROIT: Preview =====

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        preview_label = QLabel("<b>📋 Aperçu transformations (10 premières lignes)</b>")
        right_layout.addWidget(preview_label)

        self.preview_table = QTableWidget()
        right_layout.addWidget(self.preview_table)

        # Notes/warnings
        notes_label = QLabel("<b>📝 Notes de détection</b>")
        right_layout.addWidget(notes_label)

        self.notes_text = QTextEdit()
        self.notes_text.setReadOnly(True)
        self.notes_text.setMaximumHeight(150)
        right_layout.addWidget(self.notes_text)

        splitter.addWidget(right_panel)

        # Ratio splitter
        splitter.setSizes([500, 700])

        # ===== BOUTONS ACTIONS =====

        buttons_layout = QHBoxLayout()

        btn_test = QPushButton("🔄 Tester sur 50 lignes")
        btn_test.clicked.connect(self.preview_transformations)
        buttons_layout.addWidget(btn_test)

        btn_save_profile = QPushButton("💾 Sauvegarder comme profil")
        btn_save_profile.clicked.connect(self.save_as_profile)
        buttons_layout.addWidget(btn_save_profile)

        buttons_layout.addStretch()

        btn_cancel = QPushButton("❌ Annuler")
        btn_cancel.clicked.connect(self.reject)
        buttons_layout.addWidget(btn_cancel)

        btn_confirm = QPushButton("✅ Confirmer et Importer")
        btn_confirm.setStyleSheet(
            "QPushButton { background-color: #4CAF50; color: white; font-weight: bold; }"
        )
        btn_confirm.clicked.connect(self.confirm_mapping)
        buttons_layout.addWidget(btn_confirm)

        layout.addLayout(buttons_layout)

    def populate_detected_mapping(self):
        """
        Remplit la table de mapping avec les résultats de détection
        """
        mapping = self.current_mapping
        confidence = self.current_confidence

        self.mapping_table.setRowCount(len(mapping))

        row_idx = 0
        for type_name, col_idx in mapping.items():
            # Colonne 0: Type cible
            type_item = QTableWidgetItem(type_name)
            type_item.setFlags(Qt.ItemFlag.ItemIsEnabled)  # Read-only
            self.mapping_table.setItem(row_idx, 0, type_item)

            # Colonne 1: Colonne détectée
            if col_idx is not None:
                col_name = self.headers[col_idx]
                col_item = QTableWidgetItem(f"#{col_idx}: {col_name}")
            else:
                col_item = QTableWidgetItem("❌ NON DÉTECTÉ")
            col_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            self.mapping_table.setItem(row_idx, 1, col_item)

            # Colonne 2: Barre de confiance
            conf = confidence.get(type_name, 0.0)
            progress = QProgressBar()
            progress.setValue(int(conf * 100))
            progress.setFormat(f"{conf:.2f}")

            # Couleur selon confiance
            if conf >= 0.70:
                progress.setStyleSheet(
                    "QProgressBar::chunk { background-color: #4CAF50; }"
                )  # Vert
            elif conf >= 0.50:
                progress.setStyleSheet(
                    "QProgressBar::chunk { background-color: #FF9800; }"
                )  # Orange
            else:
                progress.setStyleSheet(
                    "QProgressBar::chunk { background-color: #F44336; }"
                )  # Rouge

            self.mapping_table.setCellWidget(row_idx, 2, progress)

            # Colonne 3: Menu déroulant pour changer
            combo = QComboBox()
            combo.addItem("(aucune)", None)
            for i, header in enumerate(self.headers):
                combo.addItem(f"#{i}: {header}", i)

            # Sélectionner col actuelle
            if col_idx is not None:
                combo.setCurrentIndex(col_idx + 1)  # +1 car "(aucune)" en premier

            combo.currentIndexChanged.connect(
                lambda idx, t=type_name, c=combo: self.on_mapping_changed(
                    t, c.currentData()
                )
            )
            self.mapping_table.setCellWidget(row_idx, 3, combo)

            row_idx += 1

        # Afficher notes
        notes = self.detection_result["global_suggestion"]["notes"]
        self.notes_text.setPlainText("\n".join(notes))

    def on_mapping_changed(self, type_name: str, new_col_idx: Optional[int]):
        """
        Callback quand utilisateur change un mapping

        Args:
            type_name: Type modifié
            new_col_idx: Nouvelle colonne (ou None)
        """
        self.current_mapping[type_name] = new_col_idx
        print(f"✏️ Mapping modifié: {type_name} → col {new_col_idx}")

    def preview_transformations(self):
        """
        Affiche preview des transformations sur 10 lignes
        """
        print("🔍 Preview transformations...")

        # TODO: Appeler staging_pipeline.prepare() et afficher résultats

        # Pour l'instant: affichage simple données brutes
        self.preview_table.clear()
        self.preview_table.setColumnCount(len(self.current_mapping))
        self.preview_table.setHorizontalHeaderLabels(list(self.current_mapping.keys()))

        preview_rows = self.sample_rows[:10]
        self.preview_table.setRowCount(len(preview_rows))

        for row_idx, row in enumerate(preview_rows):
            col_num = 0
            for type_name, col_idx in self.current_mapping.items():
                if col_idx is not None and col_idx < len(row):
                    value = str(row[col_idx])
                else:
                    value = ""

                item = QTableWidgetItem(value)
                self.preview_table.setItem(row_idx, col_num, item)
                col_num += 1

        print("✓ Preview mis à jour")

    def save_as_profile(self):
        """
        Sauvegarde le mapping actuel comme profil
        """
        from .profile_manager import ProfileManager

        manager = ProfileManager()

        # Demander nom profil (pour l'instant: auto)
        profile_name = f"Profil_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        manager.save_profile(
            name=profile_name,
            mapping=self.current_mapping,
            headers=self.headers,
            sample_rows=self.sample_rows,
            metadata={"source": "mapping_wizard"},
        )

        print(f"✓ Profil sauvegardé: {profile_name}")

    def confirm_mapping(self):
        """
        Utilisateur confirme le mapping → émet signal
        """
        print("✅ Mapping confirmé par utilisateur")

        result = {
            "mapping": self.current_mapping,
            "confidence": self.current_confidence,
            "headers": self.headers,
        }

        self.mapping_confirmed.emit(result)
        self.accept()


# ========== TEST STANDALONE ==========


def main():
    """Test standalone de l'assistant"""
    from PyQt6.QtWidgets import QApplication
    import sys

    app = QApplication(sys.argv)

    # Données test
    headers = ["Type", "Nom, Prénom", "Matricule", "Date", "Montant"]
    sample_rows = [
        ["Gains", "Dupont, Jean", "1001", "2023-01-15", "1234.56"],
        ["Gains", "Martin, Claire", "1002", "2023-01-15", "2500.00"],
    ]

    detection_result = {
        "global_suggestion": {
            "mapping": {
                "type_paie": 0,
                "fullname": 1,
                "matricule": 2,
                "date_paie": 3,
                "montant": 4,
            },
            "confidence": {
                "type_paie": 0.85,
                "fullname": 0.92,
                "matricule": 0.95,
                "date_paie": 0.91,
                "montant": 0.98,
            },
            "notes": [
                "✓ type_paie: col 0 'Type' (confiance: 0.85)",
                "✓ fullname: col 1 'Nom, Prénom' (confiance: 0.92)",
                "✓ matricule: col 2 'Matricule' (confiance: 0.95)",
            ],
        }
    }

    wizard = MappingWizard(headers, detection_result, sample_rows)

    def on_confirmed(result):
        print("\n✅ MAPPING CONFIRMÉ:")
        print(f"  {result}")

    wizard.mapping_confirmed.connect(on_confirmed)
    wizard.exec()

    sys.exit(0)


if __name__ == "__main__":
    main()
