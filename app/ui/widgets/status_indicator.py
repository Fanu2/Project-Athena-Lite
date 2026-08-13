"""
Status indicator widget for showing application state.
"""

import logging
from enum import Enum, auto

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QSizePolicy
from PySide6.QtGui import QColor, QPainter, QPen

logger = logging.getLogger(__name__)


class StatusState(Enum):
    """Application status states."""
    IDLE = auto()
    LOADING = auto()
    PROCESSING = auto()
    SUCCESS = auto()
    ERROR = auto()
    WARNING = auto()


class StatusIndicator(QWidget):
    """
    Visual indicator widget showing current application status.

    Displays a colored dot + text label indicating state.
    """

    state_changed = Signal(StatusState)

    def __init__(self, parent=None):
        super().__init__(parent)

        self._state = StatusState.IDLE
        self._label = "Ready"

        self._setup_ui()

    def _setup_ui(self):
        """Create the widget UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        layout.addStretch()

        self.label = QLabel("Ready")
        self.label.setStyleSheet("font-size: 12px; color: #555555;")
        layout.addWidget(self.label)

        self.setMinimumHeight(24)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def set_state(self, state: StatusState):
        """Set the status state and update display."""
        if self._state != state:
            self._state = state
            self.state_changed.emit(state)
            self._update_display()

    def _update_display(self):
        """Update the visual display based on current state."""
        colors = {
            StatusState.IDLE: "#95a5a6",
            StatusState.LOADING: "#3498db",
            StatusState.PROCESSING: "#f39c12",
            StatusState.SUCCESS: "#2ecc71",
            StatusState.ERROR: "#e74c3c",
            StatusState.WARNING: "#f39c12",
        }

        labels = {
            StatusState.IDLE: "Ready",
            StatusState.LOADING: "Loading...",
            StatusState.PROCESSING: "Processing...",
            StatusState.SUCCESS: "Success",
            StatusState.ERROR: "Error",
            StatusState.WARNING: "Warning",
        }

        color = colors.get(self._state, "#95a5a6")
        text = labels.get(self._state, "Ready")

        self.label.setText(text)
        self.label.setStyleSheet(f"font-size: 12px; color: {color};")

        self.update()

    def paintEvent(self, event):
        """Paint the colored indicator dot."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        colors = {
            StatusState.IDLE: QColor("#95a5a6"),
            StatusState.LOADING: QColor("#3498db"),
            StatusState.PROCESSING: QColor("#f39c12"),
            StatusState.SUCCESS: QColor("#2ecc71"),
            StatusState.ERROR: QColor("#e74c3c"),
            StatusState.WARNING: QColor("#f39c12"),
        }

        color = colors.get(self._state, QColor("#95a5a6"))

        painter.setPen(QPen(color, 2))
        painter.setBrush(color)

        radius = 8
        x = 12
        y = (self.height() - radius * 2) // 2 + radius

        painter.drawEllipse(x, y, radius * 2, radius * 2)
