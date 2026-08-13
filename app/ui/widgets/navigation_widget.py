"""
Navigation Widget - sidebar navigation for switching between pages.
"""

import logging

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QPushButton,
    QLabel,
    QFrame,
)

from app.ui.widgets.status_indicator import StatusIndicator

logger = logging.getLogger(__name__)


class NavigationWidget(QWidget):
    """Sidebar navigation with page buttons and status indicator."""

    page_changed = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)

        self._current_page = 0
        self.page_buttons = []

        self._setup_ui()

    def _setup_ui(self):
        """Create the widget UI."""

        layout = QVBoxLayout(self)

        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        title = QLabel("Local AI Assistant")
        title.setObjectName("nav_title")
        title.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: #2c3e50;
                padding: 15px 10px 5px 10px;
            }
        """)

        layout.addWidget(title)

        line = QFrame()
        line.setFrameStyle(
            QFrame.HLine | QFrame.Sunken
        )

        layout.addWidget(line)

        pages = [
            ("Documents", 0),
            ("Chat", 1),
            ("Settings", 2),
        ]

        for text, index in pages:

            button = QPushButton(text)

            button.setCheckable(True)
            button.setFixedHeight(45)

            button.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    border: none;
                    border-left: 3px solid transparent;
                    padding: 10px 15px;
                    font-size: 14px;
                    color: #7f8c8d;
                    text-align: left;
                }

                QPushButton:hover {
                    background-color: #ecf0f1;
                    color: #2c3e50;
                }

                QPushButton:checked {
                    background-color: #3498db;
                    border-left: 3px solid #2980b9;
                    color: white;
                }
            """)

            button.clicked.connect(
                lambda checked=False, idx=index:
                self._on_page_clicked(idx)
            )

            layout.addWidget(button)

            self.page_buttons.append(
                (text, button)
            )

        # Push status to bottom
        layout.addStretch()

        self.status_indicator = StatusIndicator()

        layout.addWidget(
            self.status_indicator
        )

        # Default page
        if self.page_buttons:
            self.page_buttons[0][1].setChecked(True)


    def _on_page_clicked(self, index: int):
        """Handle page button click."""

        if self._current_page == index:
            return

        self._current_page = index

        for i, (_, button) in enumerate(self.page_buttons):
            button.setChecked(
                i == index
            )

        self.page_changed.emit(index)


    def set_current_page(self, index: int):
        """Set current page programmatically."""

        if not 0 <= index < len(self.page_buttons):
            return

        self._current_page = index

        for i, (_, button) in enumerate(self.page_buttons):
            button.setChecked(
                i == index
            )

        self.page_changed.emit(index)