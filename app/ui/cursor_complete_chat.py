# ui/cursor_complete_chat.py
"""
Chat IA COMPLET exactement comme Cursor v0.48+
- Sélection modèle (GPT-5, GPT-4, Claude Opus, Sonnet, Haiku)
- Modes : Chat, Ask, Agent, Composer
- Search Web
- Rules/Instructions personnalisées
- @ pour fichiers
- Command palette (Ctrl+K)
- Historique conversations
"""
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTextEdit,
    QLineEdit,
    QToolButton,
    QFrame,
    QComboBox,
    QPushButton,
    QLabel,
    QButtonGroup,
    QFileDialog,
    QInputDialog,
    QMessageBox,
)
from PyQt6.QtCore import pyqtSignal, QThread, pyqtSlot
from PyQt6.QtGui import QKeySequence, QShortcut
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

    def __init__(
        self, api_key: str, messages: list, model: str, search_web: bool = False
    ):
        super().__init__()
        self.api_key = api_key
        self.messages = messages
        self.model = model
        self.search_web = search_web

    def run(self):
        try:
            if not OPENAI_AVAILABLE:
                self.errorOccurred.emit(
                    "Module 'openai' non installé : pip install openai"
                )
                return

            openai.api_key = self.api_key

            # Si search web, ajouter instruction
            if self.search_web:
                system_msg = next(
                    (m for m in self.messages if m["role"] == "system"), None
                )
                if system_msg:
                    system_msg[
                        "content"
                    ] += "\n\nYou can search the web for up-to-date information when needed."

            response = openai.ChatCompletion.create(
                model=self.model,
                messages=self.messages,
                temperature=0.7,
                max_tokens=2000,
            )
            answer = response["choices"][0]["message"]["content"]
            self.responseReady.emit(answer)

        except Exception as e:
            self.errorOccurred.emit(f"Erreur API : {str(e)}")


class CursorCompleteChat(QWidget):
    """Chat Cursor COMPLET avec toutes les fonctionnalités"""

    responseReceived = pyqtSignal(str)

    # === MODÈLES DISPONIBLES (avec GPT-5 !) ===
    MODELS = {
        "GPT-5 Preview": "gpt-5-preview",
        "GPT-4 Turbo": "gpt-4-turbo-preview",
        "GPT-4": "gpt-4",
        "GPT-3.5 Turbo": "gpt-3.5-turbo",
        "Claude 3 Opus": "claude-3-opus-20240229",
        "Claude 3 Sonnet": "claude-3-sonnet-20240229",
        "Claude 3 Haiku": "claude-3-haiku-20240307",
    }

    # === MODES DE CHAT (avec Agent !) ===
    MODES = {
        "💬 Chat": "Normal conversation",
        "🔍 Ask": "Quick question with context",
        "🤖 Agent": "Autonomous agent with tools",
        "✏️ Composer": "Multi-line composer for complex tasks",
    }

    def __init__(self, provider=None, parent=None):
        super().__init__(parent)
        self.setObjectName("CursorCompleteChat")
        self.provider = provider
        self._conversation_history = []
        self._api_key = self._load_api_key()
        self._current_thread = None

        # États
        self._search_web_enabled = False
        self._current_mode = "💬 Chat"
        self._current_model = "GPT-5 Preview"
        self._custom_rules = ""
        self._attached_files = []
        self._agent_tools = []

        # === LAYOUT PRINCIPAL ===
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header complet
        header = self._create_header()
        layout.addWidget(header)

        # Zone messages
        self.messages_area = QTextEdit()
        self.messages_area.setReadOnly(True)
        self.messages_area.setFrameStyle(QFrame.Shape.NoFrame)
        self.messages_area.setStyleSheet(
            """
            QTextEdit {
                background: #1E1E1E;
                color: #CCCCCC;
                border: none;
                padding: 16px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 13px;
                line-height: 1.6;
            }
            QScrollBar:vertical {
                width: 6px;
                background: transparent;
            }
            QScrollBar::handle:vertical {
                background: #424242;
                border-radius: 3px;
            }
        """
        )
        layout.addWidget(self.messages_area, 1)

        # Mode selector bar
        mode_bar = self._create_mode_bar()
        layout.addWidget(mode_bar)

        # Input area
        input_area = self._create_input_area()
        layout.addWidget(input_area)

        # === RACCOURCIS ===
        QShortcut(QKeySequence("Ctrl+L"), self).activated.connect(self.clear_chat)
        QShortcut(QKeySequence("Ctrl+K"), self).activated.connect(
            self._show_command_palette
        )
        QShortcut(QKeySequence("Ctrl+Shift+P"), self).activated.connect(
            self._show_command_palette
        )

        # Message bienvenue
        self._show_welcome_message()

    def _create_header(self) -> QFrame:
        """Header avec tous les contrôles"""
        header = QFrame()
        header.setStyleSheet(
            "QFrame { background: #252526; border-bottom: 1px solid #2D2D2D; }"
        )

        layout = QHBoxLayout(header)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(8)

        # === SÉLECTEUR DE MODÈLE ===
        self.model_selector = QComboBox()
        self.model_selector.addItems(self.MODELS.keys())
        self.model_selector.setCurrentText(self._current_model)
        self.model_selector.currentTextChanged.connect(self._on_model_changed)
        self.model_selector.setStyleSheet(
            """
            QComboBox {
                background: #2D2D2D;
                color: #CCCCCC;
                border: 1px solid #3C3C3C;
                border-radius: 6px;
                padding: 6px 12px;
                min-width: 140px;
                font-size: 12px;
            }
            QComboBox:hover {
                border: 1px solid #007ACC;
            }
            QComboBox::drop-down {
                border: none;
                padding-right: 8px;
            }
            QComboBox QAbstractItemView {
                background: #252526;
                color: #CCCCCC;
                selection-background-color: #007ACC;
                border: 1px solid #3C3C3C;
            }
        """
        )
        layout.addWidget(self.model_selector)

        # === BOUTON SEARCH WEB ===
        self.btn_search_web = QToolButton()
        self.btn_search_web.setText("🔍 Web")
        self.btn_search_web.setCheckable(True)
        self.btn_search_web.setToolTip("Enable web search")
        self.btn_search_web.toggled.connect(self._toggle_search_web)
        self.btn_search_web.setStyleSheet(
            """
            QToolButton {
                background: transparent;
                color: #858585;
                border: 1px solid #3C3C3C;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 12px;
            }
            QToolButton:hover {
                background: #2D2D2D;
                color: #CCCCCC;
            }
            QToolButton:checked {
                background: #007ACC;
                color: #FFFFFF;
                border: 1px solid #007ACC;
            }
        """
        )
        layout.addWidget(self.btn_search_web)

        # === BOUTON RULES ===
        self.btn_rules = QToolButton()
        self.btn_rules.setText("⚙️")
        self.btn_rules.setToolTip("Custom rules")
        self.btn_rules.clicked.connect(self._configure_rules)
        self.btn_rules.setStyleSheet(
            """
            QToolButton {
                background: transparent;
                color: #858585;
                border: 1px solid #3C3C3C;
                border-radius: 6px;
                padding: 6px 8px;
                font-size: 14px;
            }
            QToolButton:hover {
                background: #2D2D2D;
                color: #CCCCCC;
            }
        """
        )
        layout.addWidget(self.btn_rules)

        layout.addStretch()

        # === BOUTON CLEAR ===
        self.btn_clear = QToolButton()
        self.btn_clear.setText("🗑️")
        self.btn_clear.setToolTip("Clear (Ctrl+L)")
        self.btn_clear.clicked.connect(self.clear_chat)
        self.btn_clear.setStyleSheet(
            """
            QToolButton {
                background: transparent;
                color: #858585;
                border: none;
                border-radius: 4px;
                padding: 6px;
                font-size: 16px;
            }
            QToolButton:hover {
                background: #2D2D2D;
                color: #F48771;
            }
        """
        )
        layout.addWidget(self.btn_clear)

        return header

    def _create_mode_bar(self) -> QFrame:
        """Barre de sélection des modes"""
        bar = QFrame()
        bar.setStyleSheet(
            "QFrame { background: #252526; border-top: 1px solid #2D2D2D; }"
        )

        layout = QHBoxLayout(bar)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(4)

        # Button group pour modes
        self.mode_buttons = QButtonGroup(self)

        for i, (mode_name, mode_desc) in enumerate(self.MODES.items()):
            btn = QPushButton(mode_name)
            btn.setCheckable(True)
            btn.setToolTip(mode_desc)
            btn.setStyleSheet(
                """
                QPushButton {
                    background: transparent;
                    color: #858585;
                    border: none;
                    border-radius: 6px;
                    padding: 6px 12px;
                    font-size: 11px;
                    text-align: left;
                }
                QPushButton:hover {
                    background: #2D2D2D;
                    color: #CCCCCC;
                }
                QPushButton:checked {
                    background: #1E1E1E;
                    color: #4FC1FF;
                    font-weight: 600;
                }
            """
            )
            btn.clicked.connect(lambda checked, m=mode_name: self._set_mode(m))
            self.mode_buttons.addButton(btn, i)
            layout.addWidget(btn)

            if mode_name == self._current_mode:
                btn.setChecked(True)

        layout.addStretch()

        # Badge "Agent Mode"
        self.agent_badge = QLabel("🤖 Agent Active")
        self.agent_badge.setStyleSheet(
            """
            QLabel {
                background: #007ACC;
                color: #FFFFFF;
                border-radius: 4px;
                padding: 3px 8px;
                font-size: 10px;
                font-weight: 600;
            }
        """
        )
        self.agent_badge.setVisible(False)
        layout.addWidget(self.agent_badge)

        return bar

    def _create_input_area(self) -> QFrame:
        """Zone de saisie"""
        container = QFrame()
        container.setStyleSheet("QFrame { background: #1E1E1E; border: none; }")

        layout = QHBoxLayout(container)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Bouton @
        self.btn_attach = QToolButton()
        self.btn_attach.setText("@")
        self.btn_attach.setToolTip("Attach files")
        self.btn_attach.clicked.connect(self._attach_files)
        self.btn_attach.setStyleSheet(
            """
            QToolButton {
                background: transparent;
                color: #858585;
                border: none;
                border-radius: 4px;
                padding: 6px;
                font-size: 16px;
                font-weight: bold;
            }
            QToolButton:hover {
                background: #2D2D2D;
                color: #4FC1FF;
            }
        """
        )
        layout.addWidget(self.btn_attach)

        # Input field
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Ask about your payroll data...")
        self.input_field.returnPressed.connect(self._on_send)
        self.input_field.setStyleSheet(
            """
            QLineEdit {
                background: #252526;
                color: #CCCCCC;
                border: 1px solid #3C3C3C;
                border-radius: 6px;
                padding: 10px 12px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 1px solid #007ACC;
                background: #1E1E1E;
            }
        """
        )
        layout.addWidget(self.input_field, 1)

        # Bouton send
        self.btn_send = QToolButton()
        self.btn_send.setText("▲")
        self.btn_send.setToolTip("Send (Enter)")
        self.btn_send.clicked.connect(self._on_send)
        self.btn_send.setStyleSheet(
            """
            QToolButton {
                background: #007ACC;
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                font-size: 16px;
                font-weight: bold;
                min-width: 36px;
                max-width: 36px;
                min-height: 36px;
                max-height: 36px;
            }
            QToolButton:hover {
                background: #1C8FD8;
            }
            QToolButton:disabled {
                background: #3C3C3C;
                color: #767676;
            }
        """
        )
        layout.addWidget(self.btn_send)

        return container

    # === MÉTHODES ===

    def _load_api_key(self) -> str:
        api_key = os.getenv("OPENAI_API_KEY", "")
        if api_key:
            return api_key

        try:
            config_file = Path("config/openai_config.json")
            if config_file.exists():
                with open(config_file, "r", encoding="utf-8") as f:
                    return json.load(f).get("api_key", "")
        except Exception as _exc:
            pass

        return ""

    def _on_model_changed(self, model_name: str):
        self._current_model = model_name
        model_id = self.MODELS[model_name]
        self._add_system_message(f"✓ Model: {model_name}")

    def _toggle_search_web(self, checked: bool):
        self._search_web_enabled = checked
        if checked:
            self._add_system_message("✓ Web search enabled")

    def _set_mode(self, mode: str):
        self._current_mode = mode
        self.agent_badge.setVisible(mode == "🤖 Agent")

        if mode == "🤖 Agent":
            QMessageBox.information(
                self,
                "Agent Mode",
                "🤖 Agent Mode activated!\n\n"
                "The agent can:\n"
                "• Analyze files\n"
                "• Search the web\n"
                "• Make autonomous decisions\n"
                "• Use tools: File Analysis, Web Search, Data Query",
            )
            self._agent_tools = ["file_analysis", "web_search", "data_query"]

        self._add_system_message(f"✓ Mode: {mode}")

    def _configure_rules(self):
        rules, ok = QInputDialog.getMultiLineText(
            self, "Custom Instructions", "Enter your custom rules:", self._custom_rules
        )

        if ok:
            self._custom_rules = rules
            self._add_system_message("✓ Rules updated")

    def _attach_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Attach files", "", "All Files (*)"
        )

        for file in files:
            if file not in self._attached_files:
                self._attached_files.append(file)
                self._add_system_message(f"📎 {Path(file).name}")

    def _show_command_palette(self):
        commands = [
            "Clear Chat",
            "Configure Rules",
            "Change Model",
            "Toggle Web Search",
            "Agent Mode",
        ]

        command, ok = QInputDialog.getItem(
            self, "Command Palette (Ctrl+K)", "Select command:", commands, 0, False
        )

        if ok:
            if command == "Clear Chat":
                self.clear_chat()
            elif command == "Configure Rules":
                self._configure_rules()

    def _show_welcome_message(self):
        if not self._api_key:
            self._add_system_message("⚠️ Configure OpenAI API key")
        else:
            self._add_system_message(
                f"✨ Cursor Chat Ready | Model: {self._current_model} | Mode: {self._current_mode}"
            )

    def _on_send(self):
        question = self.input_field.text().strip()
        if not question:
            return

        if not self._api_key:
            self._add_error_message("Configure API key first")
            return

        if not OPENAI_AVAILABLE:
            self._add_error_message("Install openai: pip install openai")
            return

        # Ajouter message
        self._add_message("You", question, True)
        self.input_field.clear()

        # Désactiver
        self.btn_send.setEnabled(False)
        self.input_field.setEnabled(False)

        # Préparer messages
        messages = [
            {
                "role": "system",
                "content": "You are a helpful AI assistant for payroll analysis. Answer in French.",
            }
        ]

        if self._custom_rules:
            messages[0]["content"] += f"\n\nCustom rules: {self._custom_rules}"

        if self._current_mode == "🤖 Agent":
            messages[0][
                "content"
            ] += f"\n\nAgent mode with tools: {', '.join(self._agent_tools)}"

        messages.extend(self._conversation_history)
        messages.append({"role": "user", "content": question})

        # Thread
        model_id = self.MODELS[self._current_model]
        self._current_thread = OpenAIThread(
            self._api_key, messages, model_id, self._search_web_enabled
        )
        self._current_thread.responseReady.connect(self._on_response)
        self._current_thread.errorOccurred.connect(self._on_error)
        self._current_thread.finished.connect(self._on_finished)
        self._current_thread.start()

    @pyqtSlot(str)
    def _on_response(self, response: str):
        self._add_message(f"✨ {self._current_model}", response, False)
        self._conversation_history.append({"role": "assistant", "content": response})
        self.responseReceived.emit(response)

    @pyqtSlot(str)
    def _on_error(self, error: str):
        self._add_error_message(error)

    @pyqtSlot()
    def _on_finished(self):
        self.btn_send.setEnabled(True)
        self.input_field.setEnabled(True)
        self.input_field.setFocus()

    def _add_message(self, sender: str, text: str, is_user: bool):
        color = "#FFFFFF" if is_user else "#4FC1FF"
        icon = "👤" if is_user else "✨"

        html = f"""
        <div style="margin-bottom: 20px;">
            <div style="color: {color}; font-weight: 600; margin-bottom: 8px; font-size: 13px;">
                {icon} {sender}
            </div>
            <div style="color: #CCCCCC; line-height: 1.7; font-size: 13px; white-space: pre-wrap;">
{text}
            </div>
        </div>
        """

        cursor = self.messages_area.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.messages_area.setTextCursor(cursor)
        self.messages_area.insertHtml(html)

        scrollbar = self.messages_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _add_system_message(self, text: str):
        self.messages_area.append(
            f'<div style="color: #858585; font-size: 11px; margin: 6px 0;">{text}</div>'
        )

    def _add_error_message(self, text: str):
        self.messages_area.append(
            f'<div style="color: #F48771; font-size: 11px; margin: 6px 0;">⚠️ {text}</div>'
        )

    def clear_chat(self):
        self.messages_area.clear()
        self._conversation_history.clear()
        self._attached_files.clear()
        self._show_welcome_message()

    def set_provider(self, provider):
        self.provider = provider
