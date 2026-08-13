"""
Window Geometry Options Widget.
Allows users to configure main window size and state.
"""

import logging
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLineEdit,
    QLabel, QPushButton, QSpinBox, QFormLayout, QCheckBox
)

logger = logging.getLogger(__name__)


class WindowGeometryOptionsWidget(QWidget):
    """Widget for configuring main window geometry."""

    apply_requested = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_config = {
            "width": 1200,
            "height": 800,
            "x": -1,
            "y": -1,
            "maximized": False,
        }
        self._setup_ui()

    def _setup_ui(self):
        """Create the widget UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        group = QGroupBox("Window Size")
        group_layout = QFormLayout(group)
        group_layout.setSpacing(8)

        self.width_input = QSpinBox()
        self.width_input.setRange(400, 4000)
        self.width_input.setValue(self._current_config["width"])
        self.width_input.setSuffix(" px")
        self.width_input.setToolTip("Width in pixels (400-4000)")
        group_layout.addRow("Width:", self.width_input)

        self.height_input = QSpinBox()
        self.height_input.setRange(300, 3000)
        self.height_input.setValue(self._current_config["height"])
        self.height_input.setSuffix(" px")
        self.height_input.setToolTip("Height in pixels (300-3000)")
        group_layout.addRow("Height:", self.height_input)

        layout.addWidget(group)

        state_group = QGroupBox("Window State")
        state_layout = QVBoxLayout(state_group)

        self.maximize_checkbox = QCheckBox("Start maximized")
        self.maximize_checkbox.setToolTip("Start the application in maximized state")
        state_layout.addWidget(self.maximize_checkbox)

        layout.addWidget(state_group)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        apply_btn = QPushButton("Apply")
        apply_btn.setDefault(True)
        apply_btn.clicked.connect(self._on_apply_clicked)
        btn_layout.addWidget(apply_btn)

        layout.addLayout(btn_layout)

    def load_config(self, config: dict):
        """Load configuration into the widget."""
        self._current_config = config
        self.width_input.setValue(config.get("width", 1200))
        self.height_input.setValue(config.get("height", 800))
        self.maximize_checkbox.setChecked(config.get("maximized", False))

    def _on_apply_clicked(self):
        """Handle apply button click."""
        config = {
            "width": self.width_input.value(),
            "height": self.height_input.value(),
            "maximized": self.maximize_checkbox.isChecked(),
        }
        self.apply_requested.emit(config)
