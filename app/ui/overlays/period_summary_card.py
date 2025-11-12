from __future__ import annotations
import sys
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QGraphicsDropShadowEffect,
    QMessageBox,
    QDialog,
    QTextEdit,
    QScrollArea,
    QApplication,
)
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QTimer, QPoint, QSettings
from PyQt6.QtGui import QCursor

# Import DataRepository pour PostgreSQL
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from app.services.data_repo import DataRepository


class PeriodSummaryCard(QWidget):
    def __init__(self, summary: dict, main_window, parent=None):
        super().__init__(parent if parent else main_window)
        self.summary = summary
        self.main_window = main_window
        self._drag_pos = None
        self._is_compact = False
        self._content_widget = None
        self._scroll = None

        self.settings = QSettings("SCP", "PayrollAnalyzer")

        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedWidth(450)
        self.setMaximumHeight(650)

        self.frame = QFrame(self)
        self.frame.setObjectName("SummaryCard")
        self.frame.setStyleSheet(
            """
            QFrame#SummaryCard {
                background-color: white;
                border: 2px solid #4c6ef5;
                border-radius: 12px;
            }
            QScrollArea {
                border: none;
                background: transparent;
            }
            QLabel#Title {
                font-size: 16px;
                font-weight: bold;
                color: #1e3a8a;
            }
            QLabel#Status {
                font-size: 12px;
                color: #059669;
                font-weight: bold;
            }
            QLabel#SectionTitle {
                font-size: 13px;
                font-weight: bold;
                color: #1f2937;
                margin-top: 8px;
            }
            QLabel#KPI {
                font-size: 11px;
                color: #4b5563;
            }
            QLabel#Anomaly {
                font-size: 11px;
                color: #dc2626;
                padding: 6px 8px;
                background-color: #fee2e2;
                border-radius: 4px;
            }
            QLabel#Variation {
                font-size: 11px;
                color: #059669;
                padding: 6px 8px;
                background-color: #d1fae5;
                border-radius: 4px;
            }
            QLabel#NoAnomaly {
                font-size: 12px;
                color: #059669;
                font-weight: bold;
            }
            QPushButton {
                background-color: #4c6ef5;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 10px;
                font-weight: bold;
                min-height: 32px;
            }
            QPushButton:hover {
                background-color: #3b5bdb;
            }
            QPushButton:disabled {
                background-color: #9ca3af;
                color: #d1d5db;
            }
            QPushButton#CompactBtn {
                background-color: #6b7280;
                max-width: 28px;
                max-height: 28px;
                min-width: 28px;
                min-height: 28px;
                padding: 0px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton#CompactBtn:hover {
                background-color: #4b5563;
            }
            QPushButton#CloseBtn {
                background-color: #dc2626;
                max-width: 28px;
                max-height: 28px;
                min-width: 28px;
                min-height: 28px;
                padding: 0px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton#CloseBtn:hover {
                background-color: #b91c1c;
            }
        """
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(self.frame)

        self._scroll = QScrollArea(self.frame)
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        self._content_widget = QWidget()
        frame_layout = QVBoxLayout(self._content_widget)
        frame_layout.setContentsMargins(16, 16, 16, 16)
        frame_layout.setSpacing(10)

        self._build_header(frame_layout)

        if not self._load_and_validate_summary():
            err_lbl = QLabel("⚠️ Résumé indisponible\n\n(Base de données vide)")
            err_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            err_lbl.setStyleSheet("color: #dc2626; padding: 30px; font-size: 12px;")
            err_lbl.setWordWrap(True)
            frame_layout.addWidget(err_lbl)
        else:
            self._build_kpis(frame_layout)
            self._build_anomalies(frame_layout)
            self._build_comparaison(frame_layout)

        self._build_actions(frame_layout)

        self._scroll.setWidget(self._content_widget)

        frame_main_layout = QVBoxLayout(self.frame)
        frame_main_layout.setContentsMargins(0, 0, 0, 0)
        frame_main_layout.addWidget(self._scroll)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setOffset(0, 6)
        shadow.setColor(Qt.black)
        self.frame.setGraphicsEffect(shadow)

        self.adjustSize()

        self._is_compact = self.settings.value("summary_card/compact", False, type=bool)
        if self._is_compact:
            self._apply_compact_state(animate=False)

        QTimer.singleShot(100, self._position_and_animate)

    def _load_and_validate_summary(self):
        if self.summary and self.summary.get("kpis"):
            kpis = self.summary["kpis"]
            nb_emp = self._parse_number_safe(kpis.get("nb_employes", 0))
            if nb_emp > 0:
                return True

        if hasattr(self.main_window, "get_current_period_summary"):
            try:
                self.summary = self.main_window.get_current_period_summary()
                if self.summary and self.summary.get("kpis"):
                    return True
            except Exception as _exc:
                pass

        try:
            period = self.summary.get("period") if self.summary else None
            if not period or period in ["(inconnu)", "(tout)", "(erreur)"]:
                # PostgreSQL: récupérer la dernière période
                from config.config_manager import get_dsn

                dsn = get_dsn()
                repo = DataRepository(dsn, min_size=1, max_size=2)
                try:
                    row = repo.run_query(
                        'SELECT MAX("date de paie ") FROM payroll.imported_payroll_master',
                        fetch_one=True,
                    )
                    if row and row[0]:
                        period = row[0][:7] if len(row[0]) >= 7 else None
                finally:
                    repo.close()

            if period:
                # PostgreSQL: charger les données de la période
                from config.config_manager import get_dsn

                dsn = get_dsn()
                repo = DataRepository(dsn, min_size=1, max_size=2)
                try:
                    rows = repo.run_query(
                        "SELECT * FROM payroll.imported_payroll_master WHERE \"date de paie \" LIKE %s || '%%'",
                        (period,),
                        fetch_all=True,
                    )
                    # Récupérer les noms de colonnes
                    with repo.get_connection() as conn:
                        with conn.cursor() as cur:
                            cur.execute(
                                "SELECT * FROM payroll.imported_payroll_master LIMIT 0"
                            )
                            columns = [desc[0] for desc in cur.description]
                    df = __import__("pandas").DataFrame(rows, columns=columns)
                finally:
                    repo.close()

                if not df.empty:
                    from logic.formatting import _parse_number_safe

                    montant_col = (
                        "Montant"
                        if "Montant" in df.columns
                        else next(
                            (c for c in df.columns if "montant" in c.lower()), None
                        )
                    )
                    emp_col = (
                        "Matricule"
                        if "Matricule" in df.columns
                        else next(
                            (
                                c
                                for c in df.columns
                                if "matricule" in c.lower() or "employe" in c.lower()
                            ),
                            None,
                        )
                    )

                    if montant_col:
                        amounts = df[montant_col].apply(_parse_number_safe)
                        net_total = float(amounts.sum())
                        deductions = float(amounts[amounts < 0].sum())
                        brut_total = net_total + abs(deductions)
                        nb_emp = int(df[emp_col].nunique()) if emp_col else len(df)
                        net_moyen = net_total / nb_emp if nb_emp > 0 else 0.0

                        self.summary = {
                            "period": period,
                            "kpis": {
                                "net_total": net_total,
                                "brut_total": brut_total,
                                "deductions_total": deductions,
                                "nb_employes": nb_emp,
                                "net_moyen": net_moyen,
                            },
                            "anomalies": {},
                            "comparaison": {"exists": False},
                        }
                        return True
        except Exception as _exc:
            pass

        return False

    def _parse_number_safe(self, value):
        try:
            if isinstance(value, (int, float)):
                return float(value)
            s = str(value).replace("\u202f", " ").replace("\xa0", " ").replace(" ", "")
            s = s.replace(",", ".")
            return float(s)
        except Exception as _exc:
            return 0.0

    def _build_header(self, layout: QVBoxLayout):
        header = QHBoxLayout()
        header.setSpacing(10)

        self.title_label = QLabel()
        self.title_label.setObjectName("Title")
        self.title_label.setCursor(QCursor(Qt.CursorShape.OpenHandCursor))
        header.addWidget(self.title_label, 1)

        self.btn_compact = QPushButton("−")
        self.btn_compact.setObjectName("CompactBtn")
        self.btn_compact.setToolTip("Réduire/Agrandir (Ctrl+M)")
        self.btn_compact.clicked.connect(self._toggle_compact)
        header.addWidget(self.btn_compact, 0, Qt.AlignmentFlag.AlignTop)

        btn_close = QPushButton("✕")
        btn_close.setObjectName("CloseBtn")
        btn_close.setToolTip("Fermer (Esc)")
        btn_close.clicked.connect(self.close)
        header.addWidget(btn_close, 0, Qt.AlignmentFlag.AlignTop)

        layout.addLayout(header)

        self.status_label = QLabel("✓ Importé avec succès")
        self.status_label.setObjectName("Status")
        layout.addWidget(self.status_label)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setStyleSheet("background-color: #e5e7eb; max-height: 1px;")
        layout.addWidget(line)

        period = (
            self.summary.get("period", "(inconnu)") if self.summary else "(inconnu)"
        )
        self.title_label.setText(f"🎯 Bilan IA – {self._fmt_period(period)}")

    def _build_kpis(self, layout: QVBoxLayout):
        kpis = self.summary.get("kpis", {})
        if not kpis:
            return

        section = QLabel("📊 Indicateurs")
        section.setObjectName("SectionTitle")
        layout.addWidget(section)

        grid = QVBoxLayout()
        grid.setSpacing(4)

        net_total = self._parse_number_safe(kpis.get("net_total", 0))
        brut_total = self._parse_number_safe(kpis.get("brut_total", 0))
        deductions = self._parse_number_safe(kpis.get("deductions_total", 0))
        nb_emp = int(self._parse_number_safe(kpis.get("nb_employes", 0)))
        net_moyen = self._parse_number_safe(kpis.get("net_moyen", 0))

        grid.addWidget(self._kpi_label(f"• Net total : {self._fmt_money(net_total)}"))
        grid.addWidget(self._kpi_label(f"• Brut total : {self._fmt_money(brut_total)}"))
        grid.addWidget(self._kpi_label(f"• Déductions : {self._fmt_money(deductions)}"))
        grid.addWidget(self._kpi_label(f"• Employés : {nb_emp}"))
        if net_moyen > 0:
            grid.addWidget(
                self._kpi_label(f"• Moyenne/employé : {self._fmt_money(net_moyen)}")
            )

        layout.addLayout(grid)

    def _build_anomalies(self, layout: QVBoxLayout):
        anomalies = self.summary.get("anomalies", {})
        if not anomalies:
            return

        total_anomalies = sum(
            [
                anomalies.get("nets_negatifs", {}).get("count", 0),
                anomalies.get("inactifs_avec_gains", {}).get("count", 0),
                anomalies.get("codes_sensibles", {}).get("count", 0),
                anomalies.get("nouveaux_codes", {}).get("count", 0),
                anomalies.get("changements_poste", {}).get("count", 0),
            ]
        )

        if total_anomalies == 0:
            layout.addSpacing(4)
            ok_lbl = QLabel("✅ Aucune anomalie détectée")
            ok_lbl.setObjectName("NoAnomaly")
            layout.addWidget(ok_lbl)
            return

        section = QLabel("⚠️ Anomalies")
        section.setObjectName("SectionTitle")
        layout.addWidget(section)

        grid = QVBoxLayout()
        grid.setSpacing(6)

        nets_neg = anomalies.get("nets_negatifs", {}).get("count", 0)
        if nets_neg > 0:
            grid.addWidget(
                self._anomaly_label(
                    f"⚠️ {nets_neg} net{'s' if nets_neg > 1 else ''} négatif{'s' if nets_neg > 1 else ''}"
                )
            )

        inactifs = anomalies.get("inactifs_avec_gains", {}).get("count", 0)
        if inactifs > 0:
            grid.addWidget(
                self._anomaly_label(
                    f"👤 {inactifs} inactif{'s' if inactifs > 1 else ''} avec gains"
                )
            )

        codes_sens = anomalies.get("codes_sensibles", {}).get("count", 0)
        if codes_sens > 0:
            grid.addWidget(
                self._anomaly_label(
                    f"🔍 {codes_sens} code{'s' if codes_sens > 1 else ''} sensible{'s' if codes_sens > 1 else ''}"
                )
            )

        nouveaux = anomalies.get("nouveaux_codes", {}).get("count", 0)
        if nouveaux > 0:
            grid.addWidget(
                self._anomaly_label(
                    f"🆕 {nouveaux} nouveau{'x' if nouveaux > 1 else ''} code{'s' if nouveaux > 1 else ''}"
                )
            )

        changements = anomalies.get("changements_poste", {}).get("count", 0)
        if changements > 0:
            grid.addWidget(
                self._anomaly_label(
                    f"🔄 {changements} changement{'s' if changements > 1 else ''} de poste"
                )
            )

        layout.addLayout(grid)

    def _build_comparaison(self, layout: QVBoxLayout):
        comp = self.summary.get("comparaison", {})
        if not comp or not comp.get("exists", False):
            return

        section = QLabel("📈 Comparaison")
        section.setObjectName("SectionTitle")
        layout.addWidget(section)

        delta_net = self._parse_number_safe(comp.get("delta_net", 0))
        pct_var = self._parse_number_safe(comp.get("pct_variation", 0))
        tendance = comp.get("tendance", "stable")
        period_prec = comp.get("period_precedente", "")

        emoji = "📈" if tendance == "hausse" else "📉" if tendance == "baisse" else "➡️"

        var_text = f"{emoji} {self._fmt_money(abs(delta_net))} ({pct_var:+.1f}%) vs {self._fmt_period(period_prec)}"

        var_lbl = QLabel(var_text)
        var_lbl.setObjectName("Variation")
        var_lbl.setWordWrap(True)
        layout.addWidget(var_lbl)

    def _build_actions(self, layout: QVBoxLayout):
        layout.addSpacing(8)

        row1 = QHBoxLayout()
        row1.setSpacing(8)

        self.btn_analyze = QPushButton("🔍 Analyser")
        self.btn_analyze.setToolTip("Lancer l'audit complet")
        self.btn_analyze.clicked.connect(self._on_analyze)
        try:
            pass
        except Exception as _exc:
            self.btn_analyze.setEnabled(False)
            self.btn_analyze.setToolTip("Indisponible (module logic.audit manquant)")
        row1.addWidget(self.btn_analyze)

        self.btn_open = QPushButton("📂 Ouvrir")
        self.btn_open.setToolTip("Ouvrir la période dans le dashboard")
        self.btn_open.clicked.connect(self._on_open_period)
        if not (
            hasattr(self.main_window, "dashboard")
            and hasattr(self.main_window.dashboard, "period_combo")
        ):
            self.btn_open.setEnabled(False)
            self.btn_open.setToolTip("Indisponible (dashboard non accessible)")
        row1.addWidget(self.btn_open)

        layout.addLayout(row1)

        row2 = QHBoxLayout()
        row2.setSpacing(8)

        self.btn_compare = QPushButton("📊 Comparer")
        self.btn_compare.setToolTip("Comparer avec période précédente")
        self.btn_compare.clicked.connect(self._on_compare)
        comp = self.summary.get("comparaison", {}) if self.summary else {}
        if not comp or not comp.get("exists", False):
            self.btn_compare.setEnabled(False)
            self.btn_compare.setToolTip("Indisponible (aucune période précédente)")
        row2.addWidget(self.btn_compare)

        self.btn_insights = QPushButton("💡 Insights")
        self.btn_insights.setToolTip("Afficher résumé IA détaillé")
        self.btn_insights.clicked.connect(self._on_detailed_insights)
        try:
            pass
        except Exception as _exc:
            self.btn_insights.setEnabled(False)
            self.btn_insights.setToolTip(
                "Indisponible (module logic.insights manquant)"
            )
        row2.addWidget(self.btn_insights)

        layout.addLayout(row2)

    def _on_analyze(self):
        try:
            from logic.audit import run_basic_audit

            period = self.summary.get("period") if self.summary else None
            findings = run_basic_audit(period)

            if hasattr(self.main_window, "right_panel") and hasattr(
                self.main_window.right_panel, "refresh_audit"
            ):
                self.main_window.right_panel.refresh_audit(findings)
                if hasattr(self.main_window.right_panel, "tabs"):
                    audit_idx = self.main_window.right_panel.tabs.indexOf(
                        self.main_window.right_panel.tab_a
                    )
                    if audit_idx >= 0:
                        self.main_window.right_panel.tabs.setCurrentIndex(audit_idx)

            QMessageBox.information(
                self,
                "Analyse",
                f"✓ Audit terminé\n\n{len(findings.get('findings', []))} règles vérifiées.",
            )
        except Exception as e:
            QMessageBox.warning(self, "Analyse", f"Erreur :\n{e}")

    def _on_open_period(self):
        try:
            period = self.summary.get("period") if self.summary else None
            if period and hasattr(self.main_window, "dashboard"):
                if hasattr(self.main_window.dashboard, "period_combo"):
                    combo = self.main_window.dashboard.period_combo
                    idx = combo.findText(period)
                    if idx >= 0:
                        combo.setCurrentIndex(idx)

                if hasattr(self.main_window, "refresh_all"):
                    self.main_window.refresh_all()

            self.close()
        except Exception as e:
            QMessageBox.warning(self, "Ouvrir période", f"Erreur :\n{e}")

    def _on_compare(self):
        comp = self.summary.get("comparaison", {}) if self.summary else {}
        if not comp or not comp.get("exists", False):
            QMessageBox.information(
                self, "Comparaison", "Aucune période précédente disponible."
            )
            return

        period_prec = comp.get("period_precedente", "")
        delta_net = self._parse_number_safe(comp.get("delta_net", 0))
        delta_ded = self._parse_number_safe(comp.get("delta_deductions", 0))
        delta_eff = int(self._parse_number_safe(comp.get("delta_effectif", 0)))
        pct_var = self._parse_number_safe(comp.get("pct_variation", 0))

        msg = (
            f"📊 Comparaison avec {self._fmt_period(period_prec)}\n\n"
            f"• Delta net : {self._fmt_money(delta_net)} ({pct_var:+.1f}%)\n"
            f"• Delta déductions : {self._fmt_money(delta_ded)}\n"
            f"• Delta effectif : {delta_eff:+d} employé{'s' if abs(delta_eff) > 1 else ''}\n"
        )

        QMessageBox.information(self, "Comparaison P vs P-1", msg)

    def _on_detailed_insights(self):
        try:
            from logic.insights import generate_insights

            insights = generate_insights(self.summary)

            dlg = QDialog(self)
            dlg.setWindowTitle("💡 Résumé IA détaillé")
            dlg.resize(550, 450)

            layout = QVBoxLayout(dlg)

            text_edit = QTextEdit(dlg)
            text_edit.setReadOnly(True)
            text_edit.setPlainText("\n\n".join(insights))
            text_edit.setStyleSheet("font-size: 12px; padding: 10px;")
            layout.addWidget(text_edit)

            btn_close = QPushButton("Fermer", dlg)
            btn_close.clicked.connect(dlg.accept)
            layout.addWidget(btn_close)

            dlg.exec()
        except Exception as e:
            QMessageBox.warning(self, "Résumé IA", f"Erreur :\n{e}")

    def _toggle_compact(self):
        self._is_compact = not self._is_compact
        self.settings.setValue("summary_card/compact", self._is_compact)
        self._apply_compact_state(animate=True)

    def _apply_compact_state(self, animate=True):
        if self._is_compact:
            target_height = 80
            self.btn_compact.setText("+")
            if self._scroll:
                self._scroll.setVisible(False)
            if self.status_label:
                self.status_label.setVisible(False)
        else:
            target_height = min(650, self._content_widget.sizeHint().height() + 50)
            self.btn_compact.setText("−")
            if self._scroll:
                self._scroll.setVisible(True)
            if self.status_label:
                self.status_label.setVisible(True)

        if animate:
            anim = QPropertyAnimation(self, b"maximumHeight")
            anim.setDuration(300)
            anim.setStartValue(self.maximumHeight())
            anim.setEndValue(target_height)
            anim.setEasingCurve(QEasingCurve.OutCubic)
            anim.start()
            self._anim_compact = anim
        else:
            self.setMaximumHeight(target_height)

        self.adjustSize()

    def _kpi_label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName("KPI")
        lbl.setWordWrap(True)
        return lbl

    def _anomaly_label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName("Anomaly")
        lbl.setWordWrap(True)
        return lbl

    def _fmt_money(self, value: float) -> str:
        try:
            formatted = f"{abs(value):,.2f}".replace(",", " ")
            sign = "" if value >= 0 else "-"
            return f"{sign}{formatted} $"
        except Exception as _exc:
            return f"{value:.2f} $"

    def _fmt_period(self, period: str) -> str:
        try:
            if not period or period in ["(tout)", "(inconnu)", "(erreur)"]:
                return period
            year, month = period.split("-")
            months_fr = [
                "",
                "janvier",
                "février",
                "mars",
                "avril",
                "mai",
                "juin",
                "juillet",
                "août",
                "septembre",
                "octobre",
                "novembre",
                "décembre",
            ]
            month_name = months_fr[int(month)]
            return f"{month_name} {year}"
        except Exception as _exc:
            return period

    def _position_and_animate(self):
        saved_pos = self.settings.value("summary_card/pos")

        if saved_pos and isinstance(saved_pos, QPoint):
            x, y = saved_pos.x(), saved_pos.y()
        else:
            if self.main_window:
                main_geo = self.main_window.geometry()
                x = main_geo.right() - self.width() - 30
                y = main_geo.top() + 100
            else:
                screen = QApplication.desktop().availableGeometry(self)
                x = screen.right() - self.width() - 30
                y = 100

        screen = QApplication.desktop().availableGeometry(self)
        x = max(screen.left(), min(x, screen.right() - self.width()))
        y = max(screen.top(), min(y, screen.bottom() - self.height()))

        start_y = y - 30

        self.move(x, start_y)
        self.setWindowOpacity(0.0)

        anim_opacity = QPropertyAnimation(self, b"windowOpacity")
        anim_opacity.setDuration(400)
        anim_opacity.setStartValue(0.0)
        anim_opacity.setEndValue(1.0)
        anim_opacity.setEasingCurve(QEasingCurve.OutCubic)

        anim_pos = QPropertyAnimation(self, b"pos")
        anim_pos.setDuration(400)
        anim_pos.setStartValue(QPoint(x, start_y))
        anim_pos.setEndValue(QPoint(x, y))
        anim_pos.setEasingCurve(QEasingCurve.OutCubic)

        anim_opacity.start()
        anim_pos.start()

        self._anims = [anim_opacity, anim_pos]

        self.raise_()
        self.activateWindow()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            title_geo = self.title_label.geometry()
            title_global = self.title_label.mapToGlobal(QPoint(0, 0))
            title_local = self.mapFromGlobal(title_global)
            title_rect = title_geo.translated(title_local)

            if title_rect.contains(event.pos()):
                self._drag_pos = (
                    event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                )
                self.title_label.setCursor(QCursor(Qt.CursorShape.ClosedHandCursor))
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self._drag_pos is not None:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._drag_pos is not None:
            self._drag_pos = None
            self.title_label.setCursor(QCursor(Qt.CursorShape.OpenHandCursor))
            self.settings.setValue("summary_card/pos", self.pos())
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()
        elif event.key() == Qt.Key_M and event.modifiers() == Qt.ControlModifier:
            self._toggle_compact()
        else:
            super().keyPressEvent(event)
