# ui/simple_professional_chat.py - Chat IA Minimaliste et Professionnel (PyQt6)
"""
Chat IA simple, élégant et professionnel
- Design minimaliste et épuré
- Bien visible et lisible
- Fonctionnalités essentielles uniquement
"""
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTextEdit,
    QLineEdit,
    QPushButton,
    QFrame,
    QLabel,
    QComboBox,
)
from PyQt6.QtCore import pyqtSignal, QThread, pyqtSlot
import json
import os
from pathlib import Path

try:
    import openai

    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


class OpenAIThread(QThread):
    """Thread pour appels API OpenAI"""

    responseReady = pyqtSignal(str)
    errorOccurred = pyqtSignal(str)

    def __init__(self, api_key: str, messages: list, model: str):
        super().__init__()
        self.api_key = api_key
        self.messages = messages
        self.model = model

    def run(self):
        try:
            if not OPENAI_AVAILABLE:
                self.errorOccurred.emit("Module 'openai' non installé")
                return

            openai.api_key = self.api_key

            response = openai.ChatCompletion.create(
                model=self.model,
                messages=self.messages,
                temperature=0.7,
                max_tokens=1500,
            )
            answer = response["choices"][0]["message"]["content"]
            self.responseReady.emit(answer)

        except Exception as e:
            self.errorOccurred.emit(f"Erreur : {str(e)}")


class SimpleProfessionalChat(QWidget):
    """Chat IA Simple et Professionnel"""

    def __init__(self, provider=None, parent=None):
        super().__init__(parent)
        self.setObjectName("SimpleProfessionalChat")
        self.provider = provider
        self._conversation = []
        self._api_key = self._load_api_key()
        self._current_thread = None

        # Layout principal
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header minimaliste
        self.header = self._create_header()
        layout.addWidget(self.header)

        # Zone de messages
        self.messages_area = QTextEdit()
        self.messages_area.setReadOnly(True)
        self.messages_area.setFrameStyle(QFrame.Shape.NoFrame)
        self.messages_area.setStyleSheet(
            """
            QTextEdit {
                background: #1E1E1E;
                color: #E0E0E0;
                border: none;
                padding: 16px;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 13px;
                line-height: 1.6;
            }
            QScrollBar:vertical {
                width: 8px;
                background: #2A2A2A;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: #4A4A4A;
                border-radius: 4px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background: #5A5A5A;
            }
        """
        )
        layout.addWidget(self.messages_area, 1)

        # Zone de saisie
        self.input_area = self._create_input_area()
        layout.addWidget(self.input_area)

        # Message de bienvenue
        self._show_welcome()

    def _create_header(self) -> QFrame:
        """Crée le header minimaliste"""
        header = QFrame()
        header.setStyleSheet(
            """
            QFrame {
                background: #252525;
                border-bottom: 2px solid #1DD1A1;
                padding: 12px 16px;
            }
        """
        )

        layout = QHBoxLayout(header)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # Icône + Titre
        title = QLabel("💬 Assistant IA")
        title.setStyleSheet(
            """
            QLabel {
                color: #FFFFFF;
                font-size: 16px;
                font-weight: 600;
                background: transparent;
                border: none;
            }
        """
        )
        layout.addWidget(title)

        layout.addStretch()

        # Sélecteur de modèle (minimaliste)
        self.model_selector = QComboBox()
        self.model_selector.addItems(["GPT-4", "GPT-3.5"])
        self.model_selector.setCurrentText("GPT-4")
        self.model_selector.setStyleSheet(
            """
            QComboBox {
                background: #2A2A2A;
                color: #E0E0E0;
                border: 1px solid #3A3A3A;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 12px;
                min-width: 100px;
            }
            QComboBox:hover {
                border: 1px solid #1DD1A1;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox QAbstractItemView {
                background: #2A2A2A;
                color: #E0E0E0;
                selection-background-color: #1DD1A1;
                border: 1px solid #3A3A3A;
            }
        """
        )
        layout.addWidget(self.model_selector)

        # Bouton Clear
        btn_clear = QPushButton("Effacer")
        btn_clear.clicked.connect(self.clear_chat)
        btn_clear.setStyleSheet(
            """
            QPushButton {
                background: transparent;
                color: #999999;
                border: 1px solid #3A3A3A;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 12px;
            }
            QPushButton:hover {
                background: #2A2A2A;
                color: #FFFFFF;
                border: 1px solid #1DD1A1;
            }
        """
        )
        layout.addWidget(btn_clear)

        return header

    def _create_input_area(self) -> QFrame:
        """Crée la zone de saisie professionnelle"""
        container = QFrame()
        container.setStyleSheet(
            """
            QFrame {
                background: #252525;
                border-top: 1px solid #3A3A3A;
                padding: 12px;
            }
        """
        )

        layout = QHBoxLayout(container)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Input
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Posez votre question sur la paie...")
        self.input_field.returnPressed.connect(self._on_send)
        self.input_field.setStyleSheet(
            """
            QLineEdit {
                background: #2A2A2A;
                color: #FFFFFF;
                border: 2px solid #3A3A3A;
                border-radius: 8px;
                padding: 12px 16px;
                font-size: 13px;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QLineEdit:focus {
                border: 2px solid #1DD1A1;
                background: #1E1E1E;
            }
        """
        )
        layout.addWidget(self.input_field, 1)

        # Bouton Envoyer
        self.btn_send = QPushButton("Envoyer")
        self.btn_send.clicked.connect(self._on_send)
        self.btn_send.setStyleSheet(
            """
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1DD1A1, stop:1 #10B981);
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 12px 24px;
                font-size: 13px;
                font-weight: 600;
                min-width: 100px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #10B981, stop:1 #059669);
            }
            QPushButton:pressed {
                background: #059669;
            }
            QPushButton:disabled {
                background: #3A3A3A;
                color: #666666;
            }
        """
        )
        layout.addWidget(self.btn_send)

        return container

    def _load_api_key(self) -> str:
        """Charge la clé API"""
        # Variable d'environnement
        api_key = os.getenv("OPENAI_API_KEY", "")
        if api_key:
            return api_key

        # Fichier de config
        try:
            config_file = Path("config/openai_config.json")
            if config_file.exists():
                with open(config_file, "r", encoding="utf-8") as f:
                    return json.load(f).get("api_key", "")
        except Exception as _exc:
            pass

        return ""

    def _show_welcome(self):
        """Affiche le message de bienvenue"""
        if not self._api_key:
            self._add_system_message("⚠️ Clé API OpenAI non configurée")
            self._add_system_message(
                "Configurez votre clé dans config/openai_config.json"
            )
        else:
            self._add_system_message("✓ Assistant IA prêt")
            self._add_system_message("Posez vos questions sur les données de paie")

    def _on_send(self):
        """Envoie un message"""
        question = self.input_field.text().strip()
        if not question:
            return

        if not self._api_key:
            self._add_error("Clé API non configurée")
            return

        if not OPENAI_AVAILABLE:
            self._add_error("Module openai non installé : pip install openai")
            return

        # Afficher le message utilisateur
        self._add_message("Vous", question, is_user=True)
        self.input_field.clear()

        # Désactiver l'input
        self.input_field.setEnabled(False)
        self.btn_send.setEnabled(False)
        self.btn_send.setText("...")

        # Préparer les messages
        messages = [
            {
                "role": "system",
                "content": "Tu es un assistant spécialisé en analyse de paie. Réponds en français de manière claire et concise.",
            }
        ]
        messages.extend(self._conversation)
        messages.append({"role": "user", "content": question})

        # Modèle
        model_map = {"GPT-4": "gpt-4", "GPT-3.5": "gpt-3.5-turbo"}
        model = model_map[self.model_selector.currentText()]

        # Lancer le thread
        self._current_thread = OpenAIThread(self._api_key, messages, model)
        self._current_thread.responseReady.connect(self._on_response)
        self._current_thread.errorOccurred.connect(self._on_error)
        self._current_thread.finished.connect(self._on_finished)
        self._current_thread.start()

    @pyqtSlot(str)
    def _on_response(self, response: str):
        """Réponse reçue"""
        self._add_message("Assistant", response, is_user=False)
        self._conversation.append({"role": "assistant", "content": response})

    @pyqtSlot(str)
    def _on_error(self, error: str):
        """Erreur"""
        self._add_error(error)

    @pyqtSlot()
    def _on_finished(self):
        """Thread terminé"""
        self.input_field.setEnabled(True)
        self.btn_send.setEnabled(True)
        self.btn_send.setText("Envoyer")
        self.input_field.setFocus()

    def _add_message(self, sender: str, text: str, is_user: bool):
        """Ajoute un message"""
        color = "#1DD1A1" if is_user else "#60A5FA"
        bg_color = "#2A2A2A" if is_user else "#1E3A5F"

        html = f"""
        <div style="margin-bottom: 16px;">
            <div style="color: {color}; font-weight: 600; margin-bottom: 6px; font-size: 12px;">
                {sender}
            </div>
            <div style="background: {bg_color}; color: #E0E0E0; padding: 12px 16px; 
                        border-radius: 8px; line-height: 1.6; font-size: 13px;">
                {text}
            </div>
        </div>
        """

        self.messages_area.append(html)
        scrollbar = self.messages_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _add_system_message(self, text: str):
        """Message système"""
        html = f'<div style="color: #999999; font-size: 11px; margin: 8px 0; font-style: italic;">{text}</div>'
        self.messages_area.append(html)

    def _add_error(self, text: str):
        """Message d'erreur"""
        html = f'<div style="color: #EF4444; font-size: 12px; margin: 8px 0; font-weight: 600;">⚠️ {text}</div>'
        self.messages_area.append(html)

    def clear_chat(self):
        """Efface la conversation"""
        self.messages_area.clear()
        self._conversation.clear()
        self._show_welcome()
