"""
API Client for Ollama - handles LLM chat and embedding generation.
"""

import json
import logging
from datetime import datetime
from pathlib import Path

import requests
import tiktoken

from app.config import AppConfig
from app.models import Document, Chunk, Episode, Message

logger = logging.getLogger(__name__)


class OllamaClient:
    """
    Client for communicating with Ollama API.
    Handles chat completions and embedding generation.
    """

    def __init__(self, config: AppConfig):
        self.config = config
        self.base_url = config.ollama_url.rstrip("/")
        self.session = requests.Session()
        self.session.timeout = 120  # generous timeout for LLM responses
        self.tokenizer = tiktoken.get_encoding("cl100k_base")

    def _request(self, endpoint: str, payload: dict) -> dict:
        """Make a POST request to Ollama API."""
        url = f"{self.base_url}/api/{endpoint}"
        logger.debug(f"Ollama API call: {endpoint}")
        response = self.session.post(url, json=payload)
        response.raise_for_status()
        return response.json()

    def chat(
        self,
        model: str,
        messages: list[dict],
        stream: bool = False,
        options: dict | None = None,
    ) -> dict:
        """
        Send a chat completion request.

        Args:
            model: Model name (e.g., "qwen2.5:1.5b")
            messages: List of message dicts with role/content
            stream: Whether to stream response
            options: Additional options (temperature, etc.)

        Returns:
            Response dict with 'response' field containing generated text
        """
        payload = {
            "model": model,
            "messages": messages,
            "stream": stream,
        }
        if options:
            payload["options"] = options

        result = self._request("chat", payload)
        return result

    def chat_stream(
        self,
        model: str,
        messages: list[dict],
        callback: callable,
        options: dict | None = None,
    ) -> str:
        """
        Stream a chat completion.

        Args:
            model: Model name
            messages: List of message dicts
            callback: Function to call with each chunk of text
            options: Additional options

        Returns:
            Full generated text
        """
        payload = {
            "model": model,
            "messages": messages,
            "stream": True,
        }
        if options:
            payload["options"] = options

        url = f"{self.base_url}/api/chat"
        response = self.session.post(url, json=payload, stream=True)
        response.raise_for_status()

        full_text = ""
        for line in response.iter_lines():
            if line:
                chunk = json.loads(line)
                if "error" in chunk:
                    raise Exception(chunk["error"])
                if chunk.get("message", {}).get("content"):
                    text = chunk["message"]["content"]
                    full_text += text
                    callback(text)

        return full_text

    def generate_embedding(
        self,
        model: str,
        text: str,
    ) -> list[float]:
        """
        Generate an embedding vector for text.

        Args:
            model: Embedding model name (e.g., "nomic-embed-text")
            text: Text to embed

        Returns:
            List of floats representing the embedding vector
        """
        payload = {
            "model": model,
            "prompt": text,
        }
        result = self._request("embeddings", payload)
        if "embedding" not in result:
            raise Exception("No embedding in response")
        return result["embedding"]

    def list_models(self) -> list[dict]:
        """List available models."""
        try:
            response = self.session.get(f"{self.base_url}/api/tags")
            response.raise_for_status()
            data = response.json()
            return data.get("models", [])
        except Exception as e:
            logger.warning(f"Failed to list models: {e}")
            return []

    def is_available(self) -> bool:
        """Check if Ollama is running."""
        try:
            response = self.session.get(f"{self.base_url}/api/tags")
            return response.status_code == 200
        except requests.exceptions.ConnectionError:
            return False


class EmbeddingProvider:
    """
    Embedding provider using Ollama's embedding models.

    Generates embeddings for text using nomic-embed-text
    or other embedding-capable models.
    """

    def __init__(self, client: OllamaClient, embedding_model: str):
        self.client = client
        self.embedding_model = embedding_model
        self._embed_cache: dict = {}

    def embed(self, text: str) -> list[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector as list of floats
        """
        if text in self._embed_cache:
            return self._embed_cache[text]

        embedding = self.client.generate_embedding(self.embedding_model, text)
        self._embed_cache[text] = embedding
        return embedding

    def embed_batch(
        self,
        texts: list[str],
        batch_size: int = 10,
    ) -> list[list[float]]:
        """
        Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed
            batch_size: Number of texts to process in parallel

        Returns:
            List of embedding vectors
        """
        embeddings = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            for text in batch:
                embeddings.append(self.embed(text))
        return embeddings

    def clear_cache(self):
        """Clear the embedding cache."""
        self._embed_cache.clear()


class LLMClient:
    """
    High-level LLM client for chat completions.

    Wraps OllamaClient with convenient methods for
    question answering and conversation management.
    """

    def __init__(self, config: AppConfig, client: OllamaClient):
        self.config = config
        self.client = client

    def answer(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> str:
        """
        Generate a response to a user prompt.

        Args:
            system_prompt: System prompt defining assistant behavior
            user_prompt: User's question or instruction
            model: Model name (uses config default if not specified)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Returns:
            Generated response text
        """
        model_name = model or self.config.ollama_model

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        options = {"temperature": temperature}
        if max_tokens:
            options["num_predict"] = max_tokens

        response = self.client.chat(model_name, messages, options=options)
        return response.get("response", "")

    def answer_with_history(
        self,
        system_prompt: str,
        conversation: list[dict],
        latest_user_message: str,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> str:
        """
        Generate a response using conversation history.

        Args:
            system_prompt: System prompt
            conversation: List of previous messages
            latest_user_message: Current user message
            model: Model name
            temperature: Sampling temperature
            max_tokens: Maximum tokens

        Returns:
            Generated response text
        """
        model_name = model or self.config.ollama_model

        messages = [
            {"role": "system", "content": system_prompt},
        ]
        messages.extend(conversation)
        messages.append({"role": "user", "content": latest_user_message})

        options = {"temperature": temperature}
        if max_tokens:
            options["num_predict"] = max_tokens

        response = self.client.chat(model_name, messages, options=options)
        return response.get("response", "")

    def count_tokens(self, text: str) -> int:
        """Count tokens in text using tiktoken."""
        return len(self.tokenizer.encode(text))


def create_ollama_client(config: AppConfig) -> OllamaClient:
    """Create and return an Ollama client."""
    return OllamaClient(config)


def create_embedding_provider(
    config: AppConfig,
    client: OllamaClient | None = None,
) -> EmbeddingProvider:
    """Create and return an embedding provider."""
    if client is None:
        client = create_ollama_client(config)
    return EmbeddingProvider(client, config.embedding_model)


def create_llm_client(
    config: AppConfig,
    client: OllamaClient | None = None,
) -> LLMClient:
    """Create and return an LLM client."""
    if client is None:
        client = create_ollama_client(config)
    return LLMClient(config, client)
