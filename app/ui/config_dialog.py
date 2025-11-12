# ui/config_dialog.py — interface pour régler colonne Montant & stratégie du Net
# Version PyQt6 avec thème SaaS Finance moderne
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QTabWidget,
    QWidget,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
    QComboBox,
    QPushButton,
    QMessageBox,
    QGridLayout,
)
from PyQt6.QtCore import Qt
from config.config_manager import load_settings, save_settings

KEY_FIELDS = [
    ("Titre d'emploi", False),
    ("Matricule", True),
    ("Nom et prénom", True),
    ("Date de paie", True),
    ("Catégorie de paie", True),
    ("Code Paie", False),
    ("Description", False),
    ("Poste budgétaire", False),
    ("Description budgétaire", False),
    ("Montant Employé", False),
    ("Montant Employeur", False),
    ("Montant", False),
]

# Thème appliqué globalement via QApplication (ui/themes/style_saas_finance.qss)


class ConfigDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("⚙️ Configuration - Règles & Colonnes")
        self.resize(900, 680)
        self.settings = load_settings()
        self._net = self.settings.get("net", {})

        # Thème appliqué globalement

        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(24, 24, 24, 24)

        # En-tête
        header = QLabel("⚙️ Configuration du système")
        header.setProperty("heading", True)
        layout.addWidget(header)

        info = QLabel(
            "Configure le mapping des colonnes et les règles de calcul du salaire net."
        )
        info.setStyleSheet("color: #6B7280; font-size: 12px; padding-bottom: 12px;")
        layout.addWidget(info)

        # Onglets
        tabs = QTabWidget()
        layout.addWidget(tabs)

        self.tab_columns = QWidget()
        self.tab_net = QWidget()
        tabs.addTab(self.tab_columns, "📊 Colonnes & Locale")
        tabs.addTab(self.tab_net, "💰 Calcul du Net")

        self._init_columns_tab()
        self._init_net_tab()

        # Boutons d'action
        btns = QHBoxLayout()
        btns.setSpacing(12)
        btns.addStretch(1)

        self.btn_cancel = QPushButton("Annuler")
        btns.addWidget(self.btn_cancel)

        self.btn_save = QPushButton("Enregistrer")
        btns.addWidget(self.btn_save)

        layout.addLayout(btns)

        self.btn_save.clicked.connect(self.on_save)
        self.btn_cancel.clicked.connect(self.reject)

    def _init_columns_tab(self):
        s = self.settings
        fmt = s.get("input_format", "no_header")
        lay = QVBoxLayout(self.tab_columns)
        lay.setSpacing(16)
        lay.setContentsMargins(16, 16, 16, 16)

        # Section Locale
        locale_section = QLabel("🌍 Paramètres régionaux")
        locale_section.setProperty("section", True)
        lay.addWidget(locale_section)

        row_locale = QHBoxLayout()
        row_locale.setSpacing(12)
        locale_label = QLabel("Locale des fichiers (décimales/thousands) :")
        locale_label.setMinimumWidth(280)
        row_locale.addWidget(locale_label)

        self.combo_locale = QComboBox()
        self.combo_locale.addItems(
            ["🇫🇷 FR (France)", "🇨🇦 CA (Canada)", "🇺🇸 US (États-Unis)"]
        )
        cur = s.get("locale", "FR").upper()
        self.combo_locale.setCurrentIndex({"FR": 0, "CA": 1, "US": 2}.get(cur, 0))
        self.combo_locale.setMinimumWidth(200)
        row_locale.addWidget(self.combo_locale)
        row_locale.addStretch(1)
        lay.addLayout(row_locale)

        # Section Format
        format_section = QLabel("📄 Format des colonnes")
        format_section.setProperty("section", True)
        lay.addWidget(format_section)

        fmt_row = QHBoxLayout()
        fmt_row.setSpacing(12)
        format_label = QLabel("Format des fichiers d'entrée :")
        format_label.setMinimumWidth(280)
        fmt_row.addWidget(format_label)

        self.fmt_combo = QComboBox()
        self.fmt_combo.addItems(
            ["Sans en-tête (mapping par index)", "Avec en-tête (mapping par nom)"]
        )
        self.fmt_combo.setCurrentIndex(0 if fmt == "no_header" else 1)
        self.fmt_combo.setMinimumWidth(300)
        fmt_row.addWidget(self.fmt_combo, 1)
        lay.addLayout(fmt_row)

        # Forms for mapping
        self.no_header_widget = QWidget()
        self.has_header_widget = QWidget()
        lay.addWidget(self.no_header_widget)
        lay.addWidget(self.has_header_widget)

        # Mapping par index (sans en-tête)
        form_no = QFormLayout(self.no_header_widget)
        form_no.setSpacing(10)
        form_no.setContentsMargins(12, 12, 12, 12)
        form_no.setLabelAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )

        self.spin_by_index = {}
        map_idx = s.get("column_mapping_by_index", {})
        for name, required in KEY_FIELDS:
            sp = QSpinBox()
            sp.setMinimum(0)
            sp.setMaximum(999)
            default_idx = 0
            for k, v in map_idx.items():
                if v == name:
                    try:
                        default_idx = int(str(k).split(".")[0])
                    except Exception:
                        default_idx = 0
                    break
            sp.setValue(default_idx)

            label_text = f"{name}"
            if required:
                label_text = f'<span style="color: #DC2626;">*</span> {name}'

            label = QLabel(label_text)
            if required:
                label.setToolTip("Champ obligatoire")

            form_no.addRow(label, sp)
            self.spin_by_index[name] = sp

        # Mapping par nom (avec en-tête)
        form_hd = QFormLayout(self.has_header_widget)
        form_hd.setSpacing(10)
        form_hd.setContentsMargins(12, 12, 12, 12)
        form_hd.setLabelAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )

        self.edit_by_name = {}
        map_name = s.get("column_mapping_by_name", {})
        rev = {v: k for k, v in map_name.items()}
        for name, required in KEY_FIELDS:
            ed = QLineEdit()
            ed.setPlaceholderText(f"Nom de colonne dans le fichier (ex: '{name}')")
            ed.setText(rev.get(name, ""))

            label_text = f"{name}"
            if required:
                label_text = f'<span style="color: #DC2626;">*</span> {name}'

            label = QLabel(label_text)
            if required:
                label.setToolTip("Champ obligatoire")

            form_hd.addRow(label, ed)
            self.edit_by_name[name] = ed

        self._toggle_format_widgets()
        self.fmt_combo.currentIndexChanged.connect(self._toggle_format_widgets)

        lay.addStretch(1)

    def _toggle_format_widgets(self):
        if self.fmt_combo.currentIndex() == 0:
            self.no_header_widget.show()
            self.has_header_widget.hide()
        else:
            self.no_header_widget.hide()
            self.has_header_widget.show()

    def _init_net_tab(self):
        net = self._net
        lay = QVBoxLayout(self.tab_net)
        lay.setSpacing(16)
        lay.setContentsMargins(16, 16, 16, 16)

        # Section Stratégie
        strategy_section = QLabel("🎯 Stratégie de calcul")
        strategy_section.setProperty("section", True)
        lay.addWidget(strategy_section)

        row_s = QHBoxLayout()
        row_s.setSpacing(12)
        strategy_label = QLabel("Stratégie de calcul du Net :")
        strategy_label.setMinimumWidth(250)
        row_s.addWidget(strategy_label)

        self.combo_strategy = QComboBox()
        self.combo_strategy.addItems(
            [
                "Utiliser les montants tels quels (aucune transformation)",
                "Appliquer des règles par catégorie (gain / exclu / déduction)",
            ]
        )
        self.combo_strategy.setCurrentIndex(
            0 if (net.get("strategy", "as_is") == "as_is") else 1
        )
        row_s.addWidget(self.combo_strategy, 1)
        lay.addLayout(row_s)

        # Section Colonnes
        columns_section = QLabel("📋 Configuration des colonnes")
        columns_section.setProperty("section", True)
        lay.addWidget(columns_section)

        row_a = QHBoxLayout()
        row_a.setSpacing(12)
        amount_label = QLabel("Colonne Montant par défaut :")
        amount_label.setMinimumWidth(250)
        row_a.addWidget(amount_label)

        self.combo_amount_col = QComboBox()
        self.combo_amount_col.addItems(
            ["Montant", "Montant Employé", "Montant Employeur"]
        )
        try:
            idx = ["Montant", "Montant Employé", "Montant Employeur"].index(
                net.get("amount_column", "Montant")
            )
        except ValueError:
            idx = 0
        self.combo_amount_col.setCurrentIndex(idx)
        self.combo_amount_col.setMinimumWidth(250)
        row_a.addWidget(self.combo_amount_col)
        row_a.addStretch(1)
        lay.addLayout(row_a)

        # Section Effets par défaut
        default_section = QLabel("⚡ Effet par défaut")
        default_section.setProperty("section", True)
        lay.addWidget(default_section)

        row_d = QHBoxLayout()
        row_d.setSpacing(12)
        default_label = QLabel("Effet par défaut (catégorie inconnue) :")
        default_label.setMinimumWidth(250)
        row_d.addWidget(default_label)

        self.combo_default = QComboBox()
        self.combo_default.addItems(
            ["➖ -1 (déduction)", "⊘ 0 (exclu du calcul)", "➕ +1 (gain)"]
        )
        defmap = {"-1": 0, "0": 1, "+1": 2}
        cur = str(net.get("default_effect", -1))
        self.combo_default.setCurrentIndex(defmap.get(cur, 0))
        self.combo_default.setMinimumWidth(250)
        row_d.addWidget(self.combo_default)
        row_d.addStretch(1)
        lay.addLayout(row_d)

        # Section Effets par catégorie
        effects_section = QLabel("💡 Effets par catégorie")
        effects_section.setProperty("section", True)
        lay.addWidget(effects_section)

        effects_info = QLabel(
            "Définis comment chaque catégorie affecte le calcul du Net (gain, déduction ou exclu)"
        )
        effects_info.setStyleSheet(
            "color: #6B7280; font-size: 12px; padding: 4px 0 8px 0;"
        )
        lay.addWidget(effects_info)

        grid = QGridLayout()
        grid.setSpacing(8)
        grid.setColumnStretch(0, 1)
        grid.setColumnMinimumWidth(1, 180)

        # Headers
        header_name = QLabel("Catégorie canonique")
        header_name.setStyleSheet("font-weight: 600; color: #374151; padding: 4px;")
        header_effect = QLabel("Effet sur Net")
        header_effect.setStyleSheet("font-weight: 600; color: #374151; padding: 4px;")
        grid.addWidget(header_name, 0, 0)
        grid.addWidget(header_effect, 0, 1)

        self.effect_rows = []
        base_effects = net.get(
            "effects",
            {
                "gains": 1,
                "assurance": -1,
                "déductions légales": -1,
                "avantages imposables": 0,
            },
        )
        names = list(base_effects.keys())
        vals = list(base_effects.values())

        for i in range(6):
            ed_name = QLineEdit()
            ed_name.setPlaceholderText("Ex: gains, déductions, assurances...")

            cb_eff = QComboBox()
            cb_eff.addItems(["➖ -1 (déduction)", "⊘ 0 (exclu)", "➕ +1 (gain)"])

            if i < len(names):
                ed_name.setText(str(names[i]))
                cb_eff.setCurrentIndex(
                    {-1: 0, 0: 1, 1: 2}.get(
                        int(vals[i]) if str(vals[i]).lstrip("+-").isdigit() else -1, 0
                    )
                )
            else:
                cb_eff.setCurrentIndex(0)

            grid.addWidget(ed_name, i + 1, 0)
            grid.addWidget(cb_eff, i + 1, 1)
            self.effect_rows.append((ed_name, cb_eff))

        lay.addLayout(grid)

        # Section Alias de catégories
        alias_section = QLabel("🔗 Alias de catégories")
        alias_section.setProperty("section", True)
        lay.addWidget(alias_section)

        alias_info = QLabel(
            "Mappe les noms de catégories du fichier source vers les catégories canoniques ci-dessus"
        )
        alias_info.setStyleSheet(
            "color: #6B7280; font-size: 12px; padding: 4px 0 8px 0;"
        )
        lay.addWidget(alias_info)

        grid2 = QGridLayout()
        grid2.setSpacing(8)
        grid2.setColumnStretch(0, 1)
        grid2.setColumnStretch(1, 1)

        # Headers
        header_src = QLabel("Catégorie dans le fichier")
        header_src.setStyleSheet("font-weight: 600; color: #374151; padding: 4px;")
        header_dst = QLabel("→ Catégorie canonique")
        header_dst.setStyleSheet("font-weight: 600; color: #374151; padding: 4px;")
        grid2.addWidget(header_src, 0, 0)
        grid2.addWidget(header_dst, 0, 1)

        self.alias_rows = []
        base_alias = net.get(
            "aliases",
            {
                "syndicats": "déductions légales",
                "impôts": "déductions légales",
                "cotisations": "déductions légales",
                "assurance": "assurance",
            },
        )
        a_names = list(base_alias.keys())
        a_vals = list(base_alias.values())

        for i in range(6):
            ed_src = QLineEdit()
            ed_src.setPlaceholderText("Ex: syndicats, impôts...")
            ed_dst = QLineEdit()
            ed_dst.setPlaceholderText("Ex: déductions légales")

            if i < len(a_names):
                ed_src.setText(str(a_names[i]))
                ed_dst.setText(str(a_vals[i]))

            grid2.addWidget(ed_src, i + 1, 0)
            grid2.addWidget(ed_dst, i + 1, 1)
            self.alias_rows.append((ed_src, ed_dst))

        lay.addLayout(grid2)
        lay.addStretch(1)

    def on_save(self):
        s = load_settings()
        # columns / locale
        s["locale"] = ["FR", "CA", "US"][self.combo_locale.currentIndex()]
        s["input_format"] = (
            "no_header" if self.fmt_combo.currentIndex() == 0 else "has_header"
        )
        if s["input_format"] == "no_header":
            mapping = {}
            for name, sp in self.spin_by_index.items():
                idx = int(sp.value())
                if idx > 0:
                    key = str(idx)
                    while key in mapping and mapping[key] != name:
                        key = key + ".1"
                    mapping[key] = name
            s["column_mapping_by_index"] = mapping
        else:
            mapping = {}
            for name, ed in self.edit_by_name.items():
                key = ed.text().strip()
                if key:
                    mapping[key.lower()] = name
            s["column_mapping_by_name"] = mapping

        # net strategy
        s.setdefault("net", {})
        s["net"]["strategy"] = (
            "as_is" if self.combo_strategy.currentIndex() == 0 else "by_category"
        )
        s["net"]["amount_column"] = ["Montant", "Montant Employé", "Montant Employeur"][
            self.combo_amount_col.currentIndex()
        ]
        s["net"]["default_effect"] = [-1, 0, 1][self.combo_default.currentIndex()]

        effects = {}
        for ed, cb in self.effect_rows:
            name = ed.text().strip().lower()
            if not name:
                continue
            eff = [-1, 0, 1][cb.currentIndex()]
            effects[name] = eff
        s["net"]["effects"] = effects

        aliases = {}
        for ed_src, ed_dst in self.alias_rows:
            src = ed_src.text().strip().lower()
            dst = ed_dst.text().strip().lower()
            if src and dst:
                aliases[src] = dst
        s["net"]["aliases"] = aliases

        save_settings(s)
        QMessageBox.information(
            self,
            "Configuration",
            "Réglages sauvegardés. Réouvrez le dashboard pour appliquer.",
        )
        self.accept()
