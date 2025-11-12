# agent/standalone_app.py — Agent IA indépendant, avec provider
import sys
import os
from PyQt6.QtWidgets import QApplication, QMainWindow

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from ui.assistant_panel import AssistantPanel
from ui.data_provider import PayrollDataProvider
from logic.audit import run_basic_audit

THEME_QSS = """
* { font-family: "Segoe UI", "Inter", "Roboto", Arial, sans-serif; }
QMainWindow, QDialog { background-color: #f7f7fb; }
QMenuBar { background: #ffffff; border-bottom: 1px solid #e5e7eb; }
QStatusBar { background: #ffffff; border-top: 1px solid #e5e7eb; }
QFrame#KPI { background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #ffffff, stop:1 #f2f4f8); border: 1px solid #e5e7eb; border-radius: 10px; }
"""


def main():
    app = QApplication(sys.argv)
    qss_path = os.path.join(ROOT, "assets", "style.qss")
    if os.path.exists(qss_path):
        try:
            with open(qss_path, "r", encoding="utf-8") as f:
                app.setStyleSheet(f.read())
        except Exception:
            app.setStyleSheet(THEME_QSS)
    else:
        app.setStyleSheet(THEME_QSS)

    win = QMainWindow()
    win.setWindowTitle("Agent IA — indépendant")
    win.resize(900, 640)

    db_path = os.path.join(ROOT, "payroll.db")
    provider = PayrollDataProvider(db_path)
    panel = AssistantPanel(provider, win)
    try:
        panel.refresh_audit(run_basic_audit())
        panel.suggest_questions(provider)
    except Exception:
        pass

    win.setCentralWidget(panel)
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
