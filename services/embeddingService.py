# services/embedding_service.py
from typing import List, Dict, Optional, Union
import numpy as np
from sentence_transformers import SentenceTransformer
from config.dbConfig import VECTOR_DB_CONFIG
import logging

logger = logging.getLogger("embedding_service")
DEFAULT_BATCH_SIZE = 128

class EmbeddingService:
    """
    EmbeddingService converts transactions and queries to L2-normalized float32
    embeddings suitable for FAISS (IndexFlatIP / inner-product as cosine).
    """

    def __init__(self, model_name: Optional[str] = None, batch_size: int = DEFAULT_BATCH_SIZE):
        """
        Args:
            model_name: optional override for the sentence-transformers model name.
            batch_size: number of texts to encode per batch.
        """
        self.model_name = model_name or VECTOR_DB_CONFIG.embedding_model
        self.dimension = VECTOR_DB_CONFIG.embedding_dim
        self.batch_size = batch_size

        try:
            logger.info(f"Loading embedding model: {self.model_name}")
            self.model = SentenceTransformer(self.model_name)
            logger.info("✅ Embedding model loaded successfully")
        except Exception as e:
            logger.exception(f"❌ Failed to load SentenceTransformer model '{self.model_name}': {e}")
            raise

    def create_embedding_text(self, transaction: Dict) -> str:
        """
        Create a canonical text representation of a transaction for embedding.
        
        Args:
            transaction: Dictionary containing transaction data
            
        Returns:
            Formatted text string for embedding
        """
        try:
            # Validate input type
            if not isinstance(transaction, dict):
                raise TypeError(f"Expected dict, got {type(transaction)}: {transaction}")
            
            # Extract fields with safe defaults
            txn_type = transaction.get("type", "Unknown")
            amount = transaction.get("amount", 0)
            date = transaction.get("date", "Unknown")
            description = transaction.get("description", "Unknown")
            category = transaction.get("category", "Others")
            method = transaction.get("method", "")
            user_id = transaction.get("userId", "")
            
            # Build parts safely
            parts = [
                f"{txn_type} of ₹{amount}",
                f"on {date}",
                f"for {description}",
                f"under {category} category"
            ]
            
            # Add optional fields if present
            if method:
                parts.append(f"via {method}")
            if user_id:
                parts.append(f"user {user_id}")
                
            return " ".join(parts) + "."
            
        except Exception as e:
            logger.error(f"Error creating embedding text for transaction: {transaction}, error: {e}")
            # Return a safe fallback
            return f"Transaction {transaction.get('id', 'unknown')}"

    def _encode_batch_local(self, texts: List[str]) -> np.ndarray:
        """Encode a batch using the local sentence-transformers model and return L2-normalized float32 array."""
        if self.model is None:
            raise RuntimeError("Local embedding model is not loaded.")
        
        embs = self.model.encode(
            texts,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True
        )
        return embs.astype('float32')

    def generate_embeddings(self, transactions: List[Dict], progress: bool = False) -> np.ndarray:
        """
        Generate L2-normalized embeddings for a list of transactions in batches.

        Args:
            transactions: List of transaction dictionaries
            progress: Whether to show progress
            
        Returns:
            numpy.ndarray shape (N, dimension) dtype float32
        """
        if not transactions:
            return np.zeros((0, self.dimension), dtype='float32')

        # Validate all inputs are dictionaries
        for i, txn in enumerate(transactions):
            if not isinstance(txn, dict):
                logger.error(f"Transaction at index {i} is not a dictionary: {type(txn)} - {txn}")
                raise TypeError(f"All transactions must be dictionaries. Found {type(txn)} at index {i}")

        # Create embedding texts
        texts = []
        for txn in transactions:
            try:
                text = self.create_embedding_text(txn)
                texts.append(text)
            except Exception as e:
                logger.warning(f"Failed to create embedding text for transaction: {txn}, error: {e}")
                # Use a fallback text
                texts.append(f"Transaction {txn.get('id', 'unknown')}")

        n = len(texts)
        if progress:
            logger.info(f"Generating embeddings for {n} transactions in batches of {self.batch_size}...")

        all_embs = []
        for i in range(0, n, self.batch_size):
            batch_texts = texts[i:i + self.batch_size]
            try:
                batch_embs = self._encode_batch_local(batch_texts)
                if batch_embs.shape[1] != self.dimension:
                    raise ValueError(f"Embedding dimension mismatch: got {batch_embs.shape[1]}, expected {self.dimension}.")
                all_embs.append(batch_embs)
            except Exception as e:
                logger.exception(f"Encoding batch failed at indices {i}-{i+len(batch_texts)}: {e}")
                raise

        embeddings = np.vstack(all_embs).astype('float32')
        if progress:
            logger.info("✅ Embeddings generation complete.")
        return embeddings

    def generate_query_embedding(self, query: str) -> np.ndarray:
        """
        Generate a single L2-normalized embedding for the query string.
        
        Args:
            query: Search query string
            
        Returns:
            numpy.ndarray shape (1, dimension) dtype float32
        """
        if not isinstance(query, str):
            raise TypeError(f"Query must be a string, got {type(query)}")

        emb = self.model.encode([query], convert_to_numpy=True, normalize_embeddings=True)
        emb = emb.astype('float32')
        
        if emb.ndim == 1:
            emb = emb.reshape(1, -1)
            
        if emb.shape[1] != self.dimension:
            raise ValueError(f"Query embedding dim {emb.shape[1]} != expected {self.dimension}")
            
        return emb

    def validate_embeddings(self, embeddings: np.ndarray, expected_count: int) -> bool:
        """
        Validate the generated embeddings.
        
        Args:
            embeddings: Generated embeddings array
            expected_count: Expected number of embeddings
            
        Returns:
            True if validation passes
        """
        if embeddings.shape[0] != expected_count:
            logger.error(f"Embedding count mismatch: expected {expected_count}, got {embeddings.shape[0]}")
            return False
            
        if embeddings.shape[1] != self.dimension:
            logger.error(f"Embedding dimension mismatch: expected {self.dimension}, got {embeddings.shape[1]}")
            return False
            
        if embeddings.dtype != np.float32:
            logger.error(f"Embedding dtype mismatch: expected float32, got {embeddings.dtype}")
            return False
            
        return True