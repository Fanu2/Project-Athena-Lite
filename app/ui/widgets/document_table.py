"""
Document Table Widget - displays documents in a table.
"""

import logging
from PySide6.QtCore import Qt, Signal, QAbstractTableModel, QModelIndex
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QPushButton, QHBoxLayout,
    QMessageBox, QFileDialog
)
from PySide6.QtGui import QColor

from app.models import Document

logger = logging.getLogger(__name__)


class DocumentTableWidget(QWidget):
    """Widget that displays documents in a table with action buttons."""

    document_selected = Signal(int)
    document_double_clicked = Signal(int)
    import_requested = Signal()
    delete_requested = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.documents: list[Document] = []
        self._setup_ui()

    def _setup_ui(self):
        """Create the widget UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Name", "Type", "Size", "Chunks", "Actions"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 4px;
            }
            QTableWidget::item:selected {
                background-color: #3498db;
                color: white;
            }
        """)
        self.table.itemDoubleClicked.connect(self._on_double_click)
        layout.addWidget(self.table)

        btn_layout = QHBoxLayout()
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.refresh)
        btn_layout.addWidget(self.refresh_btn)

        self.import_btn = QPushButton("Import")
        self.import_btn.clicked.connect(self._on_import)
        btn_layout.addWidget(self.import_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

    def refresh(self):
        """Refresh the table with current documents."""
        self.table.setRowCount(0)
        for i, doc in enumerate(self.documents):
            self.table.insertRow(i)
            self.table.setItem(i, 0, QTableWidgetItem(doc.original_filename or doc.filename))
            self.table.setItem(i, 1, QTableWidgetItem(doc.file_type or "unknown"))
            self.table.setItem(i, 2, QTableWidgetItem(f"{doc.file_size / 1024:.1f} KB"))
            # Show chunk count if available, otherwise "—"
            chunk_text = doc.chunk_count if doc.chunk_count else "—"
            self.table.setItem(i, 3, QTableWidgetItem(str(chunk_text)))
            action_item = QTableWidgetItem()
            action_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            self.table.setItem(i, 3, action_item)
            self.table.setCellWidget(i, 3, self._create_action_widget(doc))
            self.table.item(i, 0).setData(Qt.UserRole, doc.id)

    def _create_action_widget(self, doc: Document) -> QWidget:
        """Create a widget with action buttons for a document."""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(2, 0, 2, 0)

        view_btn = QPushButton("View")
        view_btn.setFixedWidth(50)
        view_btn.clicked.connect(lambda: self.document_selected.emit(doc.id))
        layout.addWidget(view_btn)

        delete_btn = QPushButton("Delete")
        delete_btn.setFixedWidth(50)
        delete_btn.setStyleSheet("background-color: #e74c3c; color: white;")
        delete_btn.clicked.connect(lambda: self.delete_requested.emit(doc.id))
        layout.addWidget(delete_btn)

        return widget

    def set_documents(self, documents: list[Document]):
        """Set the documents to display."""
        self.documents = documents
        self.refresh()

    def clear(self):
        """Clear all documents."""
        self.documents = []
        self.table.setRowCount(0)

    def get_document_by_id(self, doc_id: int) -> Document | None:
        """Get a document by its ID."""
        for doc in self.documents:
            if doc.id == doc_id:
                return doc
        return None

    def _on_double_click(self, item: QTableWidgetItem):
        """Handle double-click on a row."""
        doc_id = item.data(Qt.UserRole)
        if doc_id:
            self.document_double_clicked.emit(doc_id)

    def _on_import(self):
        """Handle import button click."""
        self.import_requested.emit()
