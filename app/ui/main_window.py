"""
Main Window - Local AI Document Assistant

Responsibilities:
- Create main application window
- Initialize backend services
- Manage navigation
- Import and index documents
- Connect Chat UI with ChatService
- Display application status

Light Version:
Only exposes existing backend capabilities.
"""

import logging
from pathlib import Path

from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QStackedWidget,
    QFileDialog,
    QPushButton,
    QVBoxLayout,
    QLabel,
    QMessageBox,
)

from app.ui.widgets.navigation_widget import NavigationWidget
from app.ui.widgets.chat_widget import ChatWidget
from app.ui.widgets.document_table import DocumentTableWidget


logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(
        self,
        app,
        config,
        db,
        ollama_client,
        embedding_provider,
    ):
        super().__init__()

        self.app = app
        self.config = config
        self.db = db

        # AI components
        self.ollama_client = ollama_client
        self.llm_client = ollama_client
        self.embedding_provider = embedding_provider

        self.setWindowTitle(
            "Local AI Document Assistant"
        )

        self.resize(
            1200,
            750
        )

        self._create_services()
        self._setup_ui()


    def _create_services(self):
        """Create application services."""

        from app.services import (
            DocumentService,
            IndexingService,
            RetrievalService,
            ChatService,
        )

        self.document_service = DocumentService(
            self.config.documents_dir,
            self.db
        )

        self.indexing_service = IndexingService(
            self.db,
            self.embedding_provider,
            self.config
        )

        self.retrieval_service = RetrievalService(
            self.db,
            self.embedding_provider,
            self.config
        )

        self.chat_service = ChatService(
            self.db,
            self.llm_client,
            self.retrieval_service,
            self.config
        )


    def _setup_ui(self):
        """Create application pages."""

        container = QWidget()

        layout = QHBoxLayout(
            container
        )

        self.navigation = NavigationWidget()

        self.navigation.page_changed.connect(
            self.change_page
        )

        layout.addWidget(
            self.navigation
        )


        self.pages = QStackedWidget()


        self.document_page = DocumentPage(
            self
        )

        self.chat_page = ChatPage(
            self
        )

        self.settings_page = SettingsPage(
            self
        )


        self.pages.addWidget(
            self.document_page
        )

        self.pages.addWidget(
            self.chat_page
        )

        self.pages.addWidget(
            self.settings_page
        )


        layout.addWidget(
            self.pages
        )


        self.setCentralWidget(
            container
        )


    def change_page(
        self,
        index
    ):
        """Change visible page safely."""

        if 0 <= index < self.pages.count():
            self.pages.setCurrentIndex(index)



class DocumentPage(QWidget):
    """Document import and indexing page."""

    def __init__(
        self,
        parent
    ):
        super().__init__()

        self.parent_window = parent

        layout = QVBoxLayout(
            self
        )


        layout.addWidget(
            QLabel("Documents")
        )


        self.import_button = QPushButton(
            "Import Documents"
        )

        self.import_button.clicked.connect(
            self.import_documents
        )

        layout.addWidget(
            self.import_button
        )


        self.table = DocumentTableWidget()

        layout.addWidget(
            self.table
        )


    def import_documents(self):
        """Import files and index them."""

        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Documents"
        )


        for file in files:

            try:

                doc = self.parent_window.document_service.import_document(
                    Path(file)
                )


                self.parent_window.indexing_service.index_document(
                    doc,
                    force=True
                )


                logger.info(
                    "Indexed %s",
                    file
                )


            except Exception as e:

                logger.exception(e)

                QMessageBox.warning(
                    self,
                    "Import Error",
                    str(e)
                )



class ChatPage(QWidget):
    """Chat interface connected to ChatService."""

    def __init__(
        self,
        parent
    ):
        super().__init__()

        self.parent_window = parent

        # Store latest citations
        self.last_sources = []


        layout = QVBoxLayout(
            self
        )


        self.chat = ChatWidget()


        self.chat.message_sent.connect(
            self.send_message
        )


        layout.addWidget(
            self.chat
        )


    def send_message(
        self,
        text
    ):
        """Send question to RAG service."""

        try:

            self.chat.add_message(
                "user",
                text
            )


            result = self.parent_window.chat_service.answer(
                text
            )


            answer = result.get(
                "answer",
                ""
            )


            if not answer:
                answer = (
                    "I could not generate a response."
                )


            # Store sources BEFORE displaying
            self.last_sources = result.get(
                "sources",
                []
            )


            self.chat.add_message(
                "assistant",
                answer,
                sources=self.last_sources
            )


        except Exception as e:

            logger.exception(e)

            self.chat.add_message(
                "assistant",
                f"⚠ Error: {e}"
            )



class SettingsPage(QWidget):
    """Application status display."""

    def __init__(
        self,
        parent
    ):
        super().__init__()

        self.parent_window = parent


        layout = QVBoxLayout(
            self
        )


        layout.addWidget(
            QLabel("Settings")
        )


        status_box = QLabel()

        connected = (
            self.parent_window.ollama_client
            is not None
        )


        status = (
            "Connected"
            if connected
            else "Disconnected"
        )


        color = (
            "#27ae60"
            if connected
            else "#e74c3c"
        )


        status_box.setText(
            f"""
            <b>Ollama Status:</b>
            <font color="{color}">
            {status}
            </font>
            <br>
            <b>Chat Model:</b>
            {self.parent_window.config.ollama_model}
            <br>
            <b>Embedding Model:</b>
            {self.parent_window.config.embedding_model}
            """
        )


        status_box.setStyleSheet(
            """
            QLabel {
                padding: 10px;
                background: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 4px;
            }
            """
        )


        layout.addWidget(
            status_box
        )