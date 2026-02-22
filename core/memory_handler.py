"""
Phase-5 — Memory Handler
Manages persistent user context stored in a local JSON file.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Try to initialize ChromaDB for RAG, but don't crash if it fails
try:
    import chromadb
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False
    logger.warning("chromadb not installed. Document knowledge (RAG) will be disabled.")

DEFAULT_MEMORY_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "memory.json",
)
CHROMA_DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "chromadb",
)

# Template used when the memory file does not yet exist.
_DEFAULT_MEMORY: dict[str, Any] = {
    "user_name": "",
    "preferences": {},
    "conversation_history": [],
}


class MemoryHandler:
    """CRUD interface for the Phase-5 JSON memory store.

    Parameters
    ----------
    path : str
        Absolute path to the ``memory.json`` file.
    """

    def __init__(self, path: str = DEFAULT_MEMORY_PATH) -> None:
        self.path = path
        self._data: dict[str, Any] = {}
        self.load()

        # Initialize ChromaDB if available
        self.chroma_client = None
        self.chroma_collection = None
        if CHROMA_AVAILABLE:
            try:
                os.makedirs(CHROMA_DB_PATH, exist_ok=True)
                self.chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
                self.chroma_collection = self.chroma_client.get_or_create_collection(name="user_knowledge")
                logger.info("ChromaDB initialized for local RAG.")
            except Exception as e:
                logger.error(f"Failed to initialize ChromaDB: {e}")

    # ------------------------------------------------------------------
    # Load / Save
    # ------------------------------------------------------------------

    def load(self) -> dict[str, Any]:
        """Load the memory file from disk, creating it if absent."""
        if not os.path.exists(self.path):
            logger.info("Memory file not found — creating default at %s", self.path)
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            self._data = json.loads(json.dumps(_DEFAULT_MEMORY))  # deep copy
            self.save()
        else:
            try:
                with open(self.path, "r", encoding="utf-8") as fh:
                    self._data = json.load(fh)
            except (json.JSONDecodeError, OSError) as exc:
                logger.error("Failed to read memory file: %s", exc)
                self._data = json.loads(json.dumps(_DEFAULT_MEMORY))
        return self._data

    def save(self) -> None:
        """Persist the current memory to disk."""
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as fh:
            json.dump(self._data, fh, indent=2, ensure_ascii=False)
        logger.debug("Memory saved to %s", self.path)

    # ------------------------------------------------------------------
    # User name helpers
    # ------------------------------------------------------------------

    def get_user_name(self) -> str:
        """Return the stored user name (empty string if unset)."""
        return self._data.get("user_name", "")

    def set_user_name(self, name: str) -> None:
        """Update the user name and persist."""
        self._data["user_name"] = name
        self.save()

    # ------------------------------------------------------------------
    # Preferences
    # ------------------------------------------------------------------

    def get_preference(self, key: str, default: Any = None) -> Any:
        """Return a single preference value."""
        return self._data.get("preferences", {}).get(key, default)

    def set_preference(self, key: str, value: Any) -> None:
        """Set a preference and persist."""
        self._data.setdefault("preferences", {})[key] = value
        self.save()

    # ------------------------------------------------------------------
    # Conversation history
    # ------------------------------------------------------------------

    def add_to_history(self, role: str, content: str) -> None:
        """Append a message to conversation history.

        Parameters
        ----------
        role : str
            ``"user"`` or ``"assistant"``.
        content : str
            Message text.
        """
        self._data.setdefault("conversation_history", []).append(
            {"role": role, "content": content}
        )
        # Keep history bounded (last 50 exchanges)
        history = self._data["conversation_history"]
        if len(history) > 100:
            self._data["conversation_history"] = history[-100:]
        self.save()

    def get_history(self) -> list[dict[str, str]]:
        """Return the full conversation history list."""
        return self._data.get("conversation_history", [])

    # ------------------------------------------------------------------
    # Context string for AI system prompt
    # ------------------------------------------------------------------

    def get_context_string(self, rag_query: Optional[str] = None) -> str:
        """Build a plaintext summary that can be injected into the AI
        system prompt so the model is aware of stored user context.

        Returns
        -------
        str
            A human-readable context block, or empty string if nothing
            meaningful is stored.
        """
        parts: list[str] = []
        name = self.get_user_name()
        if name:
            parts.append(f"The user's name is {name}.")

        prefs = self._data.get("preferences", {})
        if prefs:
            pref_lines = [f"  - {k}: {v}" for k, v in prefs.items()]
            parts.append("User preferences:\n" + "\n".join(pref_lines))
            
        # Add RAG context if a query was provided
        if rag_query and CHROMA_AVAILABLE and self.chroma_collection:
            rag_context = self.query_knowledge(rag_query)
            if rag_context:
                parts.append(rag_context)

        # Include the last few messages for conversational continuity
        history = self.get_history()
        if history:
            recent = history[-6:]  # type: ignore[index]  # last 3 exchanges
            lines = [f"  {m['role'].capitalize()}: {m['content']}" for m in recent]
            parts.append("Recent conversation:\n" + "\n".join(lines))

        return "\n\n".join(parts)

    # ------------------------------------------------------------------
    # RAG / Document Knowledge
    # ------------------------------------------------------------------

    def ingest_document(self, content: str, source_name: str) -> str:
        """Add a document's text to the local vector database."""
        if not self.chroma_collection:
            return "⚠️ Knowledge base is currently offline or uninitialized."

        if not content.strip():
            return "⚠️ No content to index."

        try:
            # Very basic chunking (by paragraphs)
            paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
            if not paragraphs:
                return "⚠️ No valid text found in document."

            docs = []
            metadatas = []
            ids = []
            
            for i, chunk in enumerate(paragraphs):
                docs.append(chunk)
                metadatas.append({"source": source_name})
                ids.append(f"{source_name}_chunk_{i}")
                
            self.chroma_collection.add(
                documents=docs,
                metadatas=metadatas,
                ids=ids
            )
            return f"✅ Successfully added **{source_name}** to your local knowledge base. You can ask me about it anytime."
            
        except Exception as e:
            logger.error(f"Failed to ingest document into ChromaDB: {e}")
            return f"⚠️ Failed to add document to knowledge base: {e}"

    def query_knowledge(self, query: str, n_results: int = 3) -> str:
        """Query the vector database for relevant chunks."""
        if not self.chroma_collection:
            return ""

        try:
            results = self.chroma_collection.query(
                query_texts=[query],
                n_results=n_results
            )
            
            if not results or not results['documents'] or not results['documents'][0]:
                return ""
                
            snippets = []
            for doc, meta in zip(results['documents'][0], results['metadatas'][0]): # type: ignore
                source = meta.get("source", "Unknown") if meta else "Unknown" # type: ignore
                snippets.append(f"From {source}:\n{doc}")
                
            if snippets:
                 return "=== RELEVANT LOCAL KNOWLEDGE ===\n" + "\n\n".join(snippets) + "\n\n"
                 
            return ""
        except Exception as e:
            logger.error(f"Failed to query ChromaDB: {e}")
            return ""

    # ------------------------------------------------------------------
    # Name detection helper
    # ------------------------------------------------------------------

    @staticmethod
    def detect_name_in_message(message: str) -> Optional[str]:
        """Try to extract a name from messages like "My name is X".

        Returns the detected name or ``None``.
        """
        lower = message.lower().strip()
        prefixes = [
            "my name is ",
            "i'm ",
            "i am ",
            "call me ",
        ]
        for prefix in prefixes:
            if lower.startswith(prefix):
                name = message.strip()[len(prefix):].strip().rstrip(".!,")  # type: ignore[index]
                if name:
                    return name.title()
        return None
