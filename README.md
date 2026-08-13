"""
Local AI Document Assistant

A privacy-focused, offline-first desktop application for document management and AI-powered question answering using local LLMs via Ollama.

## Features

- **Document Management**: Import and organize PDF, DOCX, TXT, and Markdown documents
- **AI-Powered Search**: Ask questions about your documents using RAG (Retrieval-Augmented Generation)
- **Local-First**: All data stored locally in SQLite database
- **Privacy-Focused**: No cloud dependencies; everything runs on your machine
- **Modern UI**: Clean PySide6 interface with document browser and chat interface

## System Requirements

- Python 3.11+
- Ollama (for LLM and embeddings): https://ollama.ai
- Windows, macOS, or Linux

## Installation

1. Clone or download this repository
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Install and start Ollama:
   - Download from https://ollama.ai
   - Pull required models:
     ```bash
     ollama pull qwen2.5:1.5b
     ollama pull nomic-embed-text
     ```
   - Start Ollama:
     ```bash
     ollama serve
     ```

## Configuration

The application stores configuration in `~/.local_ai_assistant/config.json`. You can customize:

- `ollama_base_url`: Ollama API endpoint (default: http://localhost:11434)
- `ollama_model`: Default LLM model (default: qwen2.5:1.5b)
- `embedding_model`: Embedding model (default: nomic-embed-text)
- `database_path`: SQLite database location
- `documents_dir`: Document storage directory
- `chunk_size`: Text chunk size for embeddings (default: 500)
- `chunk_overlap`: Chunk overlap for context continuity (default: 50)
- `max_chunks_per_query`: Maximum chunks to retrieve per query (default: 5)

## Usage

1. Start the application:

```bash
python main.py
```

2. Import documents using the "Import" button
3. Ask questions in the Chat tab
4. The AI will search your documents and provide answers with source citations

## Architecture

The application follows a layered architecture:

- **UI Layer** (PySide6): main_window.py, widgets/
- **Service Layer**: document_service.py, indexing_service.py, chat_service.py
- **AI Layer**: ollama_client.py, embedding_provider.py.py
- **Data Layer**: database.py (plain SQLite)

## Models

- `Document`: id, filename, original_filename, file_path, file_size, file_type, created_at, updated_at
- `Chunk`: id, document_id, chunk_index, text, embedding, page_number, created_at
- `Conversation`: id, title, created_at, updated_at
- `Message`: id, conversation_id, role, content, tokens_used, created_at
- `SourceCitation`: id, message_id, document_id, chunk_index, score, text_preview, page_number

## Database Schema

Tables:
- `documents`: Stores document metadata
- `chunks`: Stores text chunks with embeddings
- `conversations`: Stores chat conversations
- `messages`: Stores chat messages
- `source_citations`: Links answers to source chunks
- `settings`: Stores application settings

## License

MIT License - feel free to use and modify for your needs.

## Support

For issues or questions, please check:
1. Ollama is running and accessible
2. Required models are pulled (qwen2.5:1.5b, nomic-embed-text:latest)
3. Database path is writable
4. Document import supports: PDF, DOCX, TXT, Markdown
