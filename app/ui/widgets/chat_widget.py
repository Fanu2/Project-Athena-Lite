"""
Chat Widget - displays chat messages and input for AI conversations.
"""

import logging
from datetime import datetime

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTextEdit,
    QLineEdit,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QGroupBox,
)

from PySide6.QtGui import QFont

from app.models import Message


logger = logging.getLogger(__name__)


class ChatWidget(QWidget):
    """Widget for displaying chat messages and user input."""

    message_sent = Signal(str)
    conversation_selected = Signal(int)


    def __init__(self, parent=None):

        super().__init__(parent)

        self.messages = []
        self._current_conversation_id = None

        self._setup_ui()



    def _setup_ui(self):

        layout = QVBoxLayout(self)

        layout.setSpacing(10)


        header = QGroupBox("Chat")

        header_layout = QHBoxLayout(header)


        self.conversation_combo = QListWidget()

        self.conversation_combo.setMaximumWidth(180)

        self.conversation_combo.currentItemChanged.connect(
            self._on_conversation_changed
        )

        header_layout.addWidget(
            self.conversation_combo
        )


        new_chat_btn = QPushButton(
            "New Chat"
        )

        header_layout.addWidget(
            new_chat_btn
        )


        layout.addWidget(header)



        self.chat_display = QTextEdit()

        self.chat_display.setReadOnly(True)

        self.chat_display.setFont(
            QFont("Arial", 11)
        )

        layout.addWidget(
            self.chat_display
        )



        input_layout = QHBoxLayout()


        self.input_field = QLineEdit()

        self.input_field.setPlaceholderText(
            "Ask Athena..."
        )

        self.input_field.returnPressed.connect(
            self._on_send
        )


        input_layout.addWidget(
            self.input_field
        )



        self.send_button = QPushButton(
            "Send"
        )

        self.send_button.clicked.connect(
            self._on_send
        )


        input_layout.addWidget(
            self.send_button
        )


        layout.addLayout(
            input_layout
        )


        # keep chat area expandable
        layout.setStretch(
            1,
            1
        )


        # IMPORTANT:
        # input remains enabled
        self.input_field.setEnabled(True)

        self.input_field.setFocus()



    def set_messages(self, messages):

        self.messages = messages

        self._display_messages()



    def _display_messages(self):

        self.chat_display.clear()


        for msg in self.messages:

            role = msg.role.upper()

            content = msg.content


            timestamp = ""

            if msg.created_at:
                timestamp = msg.created_at.strftime(
                    "%H:%M:%S"
                )


            if timestamp:
                prefix = (
                    f"<b>[{timestamp}] {role}:</b> "
                )
            else:
                prefix = (
                    f"<b>{role}:</b> "
                )


            self.chat_display.append(
                prefix + content
            )



    def add_message(self, role, content=None):

        """
        Add message.

        Supports:
        add_message("assistant", "hello")
        add_message("hello")
        """

        if content is None:

            content = role

            role = "assistant"



        msg = Message(
            id=0,
            conversation_id=self._current_conversation_id or 0,
            role=role,
            content=content,
            tokens_used=0,
            created_at=datetime.now()
        )


        self.messages.append(msg)

        self._display_messages()



    def clear(self):

        self.messages = []

        self.chat_display.clear()



    def set_conversation_id(self, conv_id):

        self._current_conversation_id = conv_id



    def _on_send(self):

        text = self.input_field.text().strip()


        if text:

            self.message_sent.emit(
                text
            )

            self.input_field.clear()



    def set_conversation_list(self, conversations):

        self.conversation_combo.clear()


        for conv in conversations:

            item = QListWidgetItem(
                conv.get(
                    "title",
                    "Unknown"
                )
            )

            item.setData(
                Qt.UserRole,
                conv.get("id", 0)
            )


            self.conversation_combo.addItem(
                item
            )



    def _on_conversation_changed(
        self,
        current,
        previous
    ):

        if current:

            conv_id = current.data(
                Qt.UserRole
            )

            self.conversation_selected.emit(
                conv_id
            )