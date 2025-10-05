import os
from dataclasses import dataclass
from typing import Dict, List

@dataclass
class VectorDBConfig:
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dim: int = 384
    faiss_index_path: str = "embeddings/{user_id}/vector_store.faiss"
    faiss_metadata_path: str = "embeddings/{user_id}/vector_metadata.json"
    top_k_results: int = 50  # Extended from 50 to 200 if needed

@dataclass
class DataConfig:
    num_users: int = 5
    min_transactions: int = 100
    max_transactions: int = 300
    data_path: str = "data/transactions.json"
    max_limit: int = 200  # Extended limit

@dataclass
class LLMConfig:
    use_openai: bool = False
    openai_api_key: str = ""
    model_name: str = "gpt-3.5-turbo"
    max_tokens: int = 500

# Global configuration instances
VECTOR_DB_CONFIG = VectorDBConfig()
DATA_CONFIG = DataConfig()
LLM_CONFIG = LLMConfig()

def ensure_directories():
    """Create necessary directories for multi-user support"""
    os.makedirs("data", exist_ok=True)
    os.makedirs("embeddings", exist_ok=True)
    os.makedirs("api/routes", exist_ok=True)
    os.makedirs("charts", exist_ok=True)
    
    # Create user-specific directories
    for user_id in [f"user_{i}" for i in range(1, DATA_CONFIG.num_users + 1)]:
        os.makedirs(f"embeddings/{user_id}", exist_ok=True)