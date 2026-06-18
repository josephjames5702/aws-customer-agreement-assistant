import os
import shutil
from typing import List, Dict, Any, Tuple
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
try:
    from langchain_core.documents import Document
except ImportError:
    from langchain.schema import Document

from app.config import settings
from app.utils.logger import logger

class VectorStoreManager:
    """Manages the local FAISS index building, loading, and searching."""

    def __init__(self):
        self.embeddings = HuggingFaceEmbeddings(
            model_name=settings.EMBEDDING_MODEL,
            cache_folder="data/embeddings_cache"
        )
        self.index_path = settings.VECTOR_DB_DIR
        self._db = None

    def exists(self) -> bool:
        """Checks if the FAISS index files exist on disk."""
        return (
            os.path.exists(self.index_path) and
            os.path.exists(os.path.join(self.index_path, "index.faiss")) and
            os.path.exists(os.path.join(self.index_path, "index.pkl"))
        )

    def load(self) -> bool:
        """Loads the index from disk if it exists."""
        if self.exists():
            logger.info("Loading existing FAISS index", extra={"index_path": self.index_path})
            self._db = FAISS.load_local(
                self.index_path,
                self.embeddings,
                allow_dangerous_deserialization=True
            )
            return True
        logger.info("No FAISS index found on disk.")
        return False

    def build_and_save(self, chunks: List[Dict[str, Any]], force: bool = False) -> int:
        """
        Builds the FAISS index from list of chunks and saves it to disk.
        Raises ValueError if index exists and force=False.
        """
        if self.exists() and not force:
            raise FileExistsError("FAISS index already exists. Use force=True to overwrite.")

        logger.info("Building FAISS index", extra={"chunk_count": len(chunks)})
        documents = [
            Document(page_content=chunk["text"], metadata=chunk["metadata"])
            for chunk in chunks
        ]
        
        # Build vector db
        self._db = FAISS.from_documents(documents, self.embeddings)
        
        # Save to disk
        if os.path.exists(self.index_path):
            shutil.rmtree(self.index_path)
        os.makedirs(self.index_path, exist_ok=True)
        self._db.save_local(self.index_path)
        logger.info("FAISS index saved to disk", extra={"index_path": self.index_path})
        return len(chunks)

    def similarity_search(self, query: str, k: int = 4) -> List[Tuple[Document, float]]:
        """
        Performs similarity search against the loaded index.
        Returns list of (Document, score) tuples.
        """
        if not self._db:
            # Try to load first
            if not self.load():
                raise RuntimeError("Vector database is not loaded or initialized.")
        
        # similarity_search_with_score returns L2 distance (lower is closer)
        # We convert it to a similarity score (cosine or normalized)
        results = self._db.similarity_search_with_score(query, k=k)
        return results
