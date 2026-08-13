"""
Main Window - Local AI Document Assistant

Responsibilities:
- Create the main application window
- Initialize application services
- Manage navigation between pages
- Provide document import workflow
- Connect chat UI with ChatService
- Display application settings/status
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
    """
    Main application window.

    Owns:
    - database connection
    - AI clients
    - application services
    - UI pages
    """

    def __init__(
        self,
        app,
        config,
        db,
        ollama_client,
        embedding_provider,
    ):

        super().__init__()

        # Core application references
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

        # Create backend services before UI
        self._create_services()

        # Create application pages
        self._setup_ui()


    def _create_services(self):
        """
        Initialize application services.

        Services are shared by all UI pages.
        """

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
        """
        Build main window layout.

        Structure:

        Sidebar
            |
            +---- Documents
            +---- Chat
            +---- Settings

        Content Area
        """

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
        """
        Switch visible page.
        """

        self.pages.setCurrentIndex(
            index
        )



class DocumentPage(QWidget):
    """
    Document management page.

    Handles:
    - importing files
    - extracting text
    - indexing documents
    """

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
        """
        Import selected documents and index them.
        """

        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Documents"
        )


        for file in files:

            try:

                doc = (
                    self.parent_window
                    .document_service
                    .import_document(
                        Path(file)
                    )
                )


                # Index immediately after import
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
    """
    Chat interface page.

    Sends user questions to ChatService
    and displays answers.
    """

    def __init__(
        self,
        parent
    ):

        super().__init__()

        self.parent_window = parent

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
        """
        Handle user questions.
        """

        try:

            # Display user question
            self.chat.add_message(
                "user",
                text
            )


            result = (
                self.parent_window
                .chat_service
                .answer(text)
            )


            answer = result.get(
                "answer",
                ""
            )


            # Prevent blank assistant messages
            if not answer:
                answer = (
                    "I couldn't generate a response."
                )


            self.chat.add_message(
                "assistant",
                answer
            )


            # Store retrieved sources for future citation UI
            self.last_sources = result.get(
                "sources",
                []
            )


        except Exception as e:

            logger.exception(e)

            self.chat.add_message(
                "assistant",
                f"Error: {e}"
            )



class SettingsPage(QWidget):
    """
    Application status page.

    Displays:
    - Ollama connection state
    - active LLM model
    - embedding model
    """

    def __init__(
        self,
        parent
    ):

        super().__init__()

        # Required because status display reads parent services/config
        self.parent_window = parent


        layout = QVBoxLayout(
            self
        )


        layout.addWidget(
            QLabel(
                "Settings"
            )
        )


        status_box = QLabel()

        status_box.setStyleSheet("""
            QLabel {
                font-size: 14px;
                padding: 8px;
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 4px;
            }
        """)


        connected = (
            self.parent_window.ollama_client
            is not None
        )


        ollama_status = (
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
            {ollama_status}
            </font>
            <br>
            <b>Active Chat Model:</b>
            {self.parent_window.config.ollama_model}
            <br>
            <b>Embedding Model:</b>
            {self.parent_window.config.embedding_model}
            """
        )


        layout.addWidget(
            status_box
        )