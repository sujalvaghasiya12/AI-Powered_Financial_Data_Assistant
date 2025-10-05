# services/vectorSearchService.py
import faiss
import numpy as np
import json
import os
from pathlib import Path
from typing import List, Dict, Optional

class VectorSearchService:
    def __init__(self, embedding_service):
        self.embedding_service = embedding_service
        self.index = None
        self.transactions = []
        self.is_loaded = False
        
        # Define paths
        self.faiss_index_path = "embeddings/vector_store.faiss"
        self.faiss_metadata_path = "embeddings/vector_metadata.json"
        
        # Ensure embeddings directory exists
        os.makedirs("embeddings", exist_ok=True)

    def build_index(self, transactions: List[Dict]):
        """Build FAISS index from transactions"""
        self.transactions = transactions
        
        try:
            print(f"🔄 Building FAISS index with {len(transactions)} transactions...")
            
            # FIX: Pass transaction dictionaries directly, not pre-processed texts
            embeddings = self.embedding_service.generate_embeddings(transactions, progress=True)
            
            # Validate embeddings
            if embeddings.shape[0] != len(transactions):
                raise ValueError(f"Embedding count mismatch: expected {len(transactions)}, got {embeddings.shape[0]}")
            
            # Create FAISS index (cosine similarity)
            self.index = faiss.IndexFlatIP(self.embedding_service.dimension)
            self.index.add(embeddings.astype('float32'))
            
            self.is_loaded = True
            print(f"✅ FAISS index built with {len(transactions)} vectors")
            
        except Exception as e:
            print(f"❌ Failed to build FAISS index: {e}")
            raise

    def save_index(self):
        """Save FAISS index using CORRECT method signature"""
        try:
            if self.index is None:
                raise ValueError("No index to save")
            
            # Save FAISS index
            faiss.write_index(self.index, self.faiss_index_path)
            
            # Save metadata separately
            metadata = {
                'transactions': self.transactions,
                'count': len(self.transactions)
            }
            with open(self.faiss_metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            
            print(f"✅ FAISS index saved to {self.faiss_index_path}")
            
        except Exception as e:
            print(f"❌ Failed to save FAISS index: {e}")
            raise

    def load_index(self):
        """Load FAISS index using CORRECT method signature"""
        try:
            if not os.path.exists(self.faiss_index_path):
                raise FileNotFoundError(f"FAISS index file not found: {self.faiss_index_path}")
            
            # Load FAISS index
            self.index = faiss.read_index(self.faiss_index_path)
            
            # Load metadata
            if os.path.exists(self.faiss_metadata_path):
                with open(self.faiss_metadata_path, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                self.transactions = metadata.get('transactions', [])
            
            self.is_loaded = True
            print(f"✅ FAISS index loaded from {self.faiss_index_path}")
            
        except FileNotFoundError:
            print("ℹ️ No existing FAISS index found")
            raise
        except Exception as e:
            print(f"❌ Error loading FAISS index: {e}")
            # Clean up corrupted files
            if os.path.exists(self.faiss_index_path):
                os.remove(self.faiss_index_path)
            if os.path.exists(self.faiss_metadata_path):
                os.remove(self.faiss_metadata_path)
            raise

    def semantic_search(self, query: str, top_k: int = 10, filters: Optional[Dict] = None):
        """Perform semantic search with optional filters"""
        if not self.is_loaded or self.index is None:
            raise ValueError("Index not built. Call build_index first.")
        
        # Generate query embedding
        query_embedding = self.embedding_service.generate_query_embedding(query)
        
        # Search in FAISS
        scores, indices = self.index.search(query_embedding, min(top_k * 3, len(self.transactions)))
        
        # Apply filters and format results
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < len(self.transactions):
                transaction = self.transactions[idx].copy()
                
                # Apply filters if provided
                if self._passes_filters(transaction, filters):
                    transaction['similarity_score'] = float(score)
                    results.append(transaction)
                
                if len(results) >= top_k:
                    break
        
        return results

    def _passes_filters(self, transaction: Dict, filters: Optional[Dict]) -> bool:
        """Check if transaction passes all filters"""
        if not filters:
            return True
        
        for key, value in filters.items():
            if key == 'min_amount' and transaction.get('amount', 0) < value:
                return False
            elif key == 'max_amount' and transaction.get('amount', 0) > value:
                return False
            elif key == 'type' and transaction.get('type') != value:
                return False
            elif key == 'category' and transaction.get('category') != value:
                return False
            elif key == 'user_id' and transaction.get('userId') != value:
                return False
            elif key == 'month' and not transaction.get('date', '').startswith(value):
                return False
            elif key == 'description_contains' and value.lower() not in transaction.get('description', '').lower():
                return False
        
        return True

    def get_index_info(self) -> Dict:
        """Get information about the current index"""
        return {
            'is_loaded': self.is_loaded,
            'transaction_count': len(self.transactions),
            'index_size': self.index.ntotal if self.index else 0,
            'index_dimension': self.index.d if self.index else 0
        }