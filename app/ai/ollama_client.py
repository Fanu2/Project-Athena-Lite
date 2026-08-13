"""
Ollama client for LLM and embedding interactions.
Non-blocking version that handles timeouts gracefully.
"""

import base64
import json
import logging
import socket
from typing import Any, Optional
import requests

logger = logging.getLogger(__name__)


class OllamaError(Exception):
    """Exception raised for Ollama API errors."""
    pass


class OllamaClient:
    """
    Client for interacting with Ollama API.
    Handles: LLM chat completions, Embedding generation, Model management
    """

    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.timeout = 5  # Short timeout for availability checks

    def _request(self, endpoint: str, data: dict) -> dict:
        """Make a request to Ollama API."""
        url = f"{self.base_url}/api/{endpoint}"
        try:
            response = self.session.post(url, json=data, timeout=120)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            raise OllamaError(f"Request to {endpoint} timed out")
        except requests.exceptions.ConnectionError:
            raise OllamaError(f"Cannot connect to Ollama at {self.base_url}")
        except requests.exceptions.HTTPError as e:
            raise OllamaError(f"Ollama API error: {e.response.text}")
        except Exception as e:
            raise OllamaError(f"Request failed: {e}")

    def chat(
        self,
        model: str,
        messages: list[dict],
        stream: bool = False,
        options: Optional[dict] = None,
    ) -> dict:
        """Send a chat completion request."""
        payload: dict = {
            "model": model,
            "messages": messages,
            "stream": stream,
        }
        if options:
            payload["options"] = options

        result = self._request("chat", payload)
        if "error" in result:
            raise OllamaError(result["error"])
        return result

    def chat_stream(
        self,
        model: str,
        messages: list[dict],
        callback: callable,
        options: Optional[dict] = None,
    ) -> str:
        """Stream a chat completion."""
        payload: dict = {
            "model": model,
            "messages": messages,
            "stream": True,
        }
        if options:
            payload["options"] = options

        url = f"{self.base_url}/api/chat"
        try:
            response = self.session.post(url, json=payload, stream=True, timeout=120)
            response.raise_for_status()
            full_text = ""
            for line in response.iter_lines():
                if line:
                    try:
                        chunk = json.loads(line)
                        if "error" in chunk:
                            raise OllamaError(chunk["error"])
                        if chunk.get("message", {}).get("content"):
                            text = chunk["message"]["content"]
                            full_text += text
                            callback(text)
                    except json.JSONDecodeError:
                        continue
            return full_text
        except requests.exceptions.ConnectionError:
            raise OllamaError(f"Cannot connect to Ollama at {self.base_url}")
        except requests.exceptions.HTTPError as e:
            raise OllamaError(f"Ollama API error: {e.response.text}")

    def generate_embedding(
        self,
        model: str,
        text: str,
    ) -> list[float]:
        """Generate an embedding vector for text."""
        payload = {
            "model": model,
            "prompt": text,
        }
        result = self._request("embeddings", payload)
        if "embedding" not in result:
            raise OllamaError("No embedding in response")
        return result["embedding"]

    def list_models(self) -> list[dict]:
        """List available models."""
        try:
            response = self.session.get(f"{self.base_url}/api/tags", timeout=5)
            response.raise_for_status()
            data = response.json()
            return data.get("models", [])
        except requests.exceptions.ConnectionError:
            raise OllamaError(f"Cannot connect to Ollama at {self.base_url}")

    def is_available(self) -> bool:
        """Check if Ollama is running."""
        try:
            response = self.session.get(f"{self.base_url}/api/tags", timeout=2)
            return response.status_code == 200
        except requests.exceptions.ConnectionError:
            return False
        except Exception:
            return False


class EmbeddingProvider:
    """Embedding provider using Ollama."""

    def __init__(self, client: OllamaClient, model: str = "nomic-embed-text:latest"):
        self.client = client
        self.model = model

    def embed(self, text: str) -> list[float]:
        """Generate embedding for text."""
        return self.client.generate_embedding(self.model, text)

    def embed_batch(self, texts: list[str], batch_size: int = 10) -> list[list[float]]:
        """Generate embeddings for multiple texts."""
        embeddings = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            for text in batch:
                embeddings.append(self.embed(text))
        return embeddings


class MockEmbeddingProvider:
    """Mock embedding provider for testing/live without Ollama."""

    def __init__(self, dimension: int = 768):
        self.dimension = dimension
        import hashlib
        self._hash = hashlib.md5()

    def embed(self, text: str) -> list[float]:
        """Return deterministic mock embedding."""
        import hashlib
        h = hashlib.md5(text.encode()).hexdigest()
        # Repeat hash if needed to fill dimension
        result = []
        for i in range(self.dimension):
            idx = i % len(h)
            byte_val = int(h[idx:idx+2], 16) if idx + 1 < len(h) else int(h[idx], 16)
            result.append(byte_val / 255.0)
        return result

    def embed_batch(self, texts: list[str], batch_size: int = 10) -> list[list[float]]:
        """Generate mock embeddings for multiple texts."""
        return [self.embed(text) for text in texts]
