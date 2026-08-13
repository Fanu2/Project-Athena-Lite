"""
Settings Page - Application configuration settings.
"""

import logging
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QFormLayout,
    QLabel, QLineEdit, QPushButton, QSpinBox, QCheckBox,
    QMessageBox
)

from app.ui.widgets.window_geometry_options_widget import WindowGeometryOptionsWidget

logger = logging.getLogger(__name__)


class SettingsPage(QWidget):
    """Page for configuring application settings."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self._setup_ui()
        self._load_current_settings()

    def _setup_ui(self):
        """Setup settings page UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        header = QLabel("Settings")
        header.setStyleSheet("font-size: 18px; font-weight: bold; color: #2c3e50;")
        header.setAlignment(Qt.AlignCenter)
        layout.addWidget(header)

        layout.addStretch()

        self.window_geometry_widget = WindowGeometryOptionsWidget(self)
        self.window_geometry_widget.apply_requested.connect(self._on_window_geometry_apply)
        layout.addWidget(self.window_geometry_widget)

        layout.addStretch()

        save_btn = QPushButton("Apply Settings")
        save_btn.setDefault(True)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 10px 25px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #1c5980;
            }
        """)
        save_btn.clicked.connect(self._save_settings)
        layout.addWidget(save_btn)

        layout.addStretch()

    def _load_current_settings(self):
        """Load current settings from config."""
        if not self.parent_window or not self.parent_window.config:
            return

        config = self.parent_window.config

        window_config = {
            "width": config.window_width if hasattr(config, 'window_width') else 1200,
            "height": config.window_height if hasattr(config, 'window_height') else 800,
            "maximized": config.window_maximized if hasattr(config, 'window_maximized') else False,
        }

        self.window_geometry_widget.load_config(window_config)

    def _on_window_geometry_apply(self, config: dict):
        """Handle window geometry apply from widget."""
        if not self.parent_window or not self.parent_window.config:
            return

        if hasattr(self.parent_window.config, 'set_window_config'):
            self.parent_window.config.set_window_config(config)
        elif hasattr(self.parent_window.config, 'set'):
            self.parent_window.config.set("window_width", config.get("width", 1200))
            self.parent_window.config.set("window_height", config.get("height", 800))
            self.parent_window.config.set("window_maximized", config.get("maximized", False))

        QMessageBox.information(
            self,
            "Settings Applied",
            f"Window size: {config['width']} x {config['height']} px\n"
            f"Start maximized: {'Yes' if config['maximized'] else 'No'}"
        )

    def _save_settings(self):
        """Save all settings."""
        if not self.parent_window:
            QMessageBox.warning(self, "Error", "Parent window not available")
            return

        try:
            self._on_window_geometry_apply(
                self.window_geometry_widget._current_config
            )
            QMessageBox.information(self, "Settings Saved", "All settings have been saved.")
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")
            QMessageBox.warning(self, "Error", f"Failed to save settings: {e}")
