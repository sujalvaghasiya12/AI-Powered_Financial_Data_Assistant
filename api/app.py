# api/app.py
import sys
import os
from pathlib import Path
import json
import asyncio

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# Create FastAPI app instance FIRST
app = FastAPI(
    title="AI-Powered Financial Data Assistant API",
    description="AI-powered semantic search for financial transactions",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables for services - will be initialized in startup
embedding_service = None
vector_search = None
data_file = None

# Import router AFTER app creation
try:
    from api.routes.search import router as search_router
    app.include_router(search_router, prefix="/api/v1")
    print("✅ Router imported successfully")
except ImportError as e:
    print(f"❌ Router import failed: {e}")

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    global embedding_service, vector_search, data_file
    
    print("🚀 Starting Financial Data Assistant API...")
    
    try:
        # Import services inside startup to avoid circular imports
        from services.dataGenerator import generate_sample_data
        from services.vectorSearchService import VectorSearchService
        from services.embeddingService import EmbeddingService
        from config.dbConfig import ensure_directories, DATA_CONFIG
        
        # Initialize services
        embedding_service = EmbeddingService()
        vector_search = VectorSearchService(embedding_service)
        data_file = Path(DATA_CONFIG.data_path)
        
        # Ensure directories exist
        ensure_directories()
        
        # Load or generate data
        if not data_file.exists():
            print("📊 Generating sample transaction data...")
            transactions = generate_sample_data()
        else:
            print("📊 Loading existing transaction data...")
            with open(data_file, "r", encoding='utf-8') as f:
                transactions = json.load(f)
        print(f"✅ Loaded {len(transactions)} transactions")

        # Try to load existing FAISS index
        try:
            print("🔄 Loading FAISS index...")
            vector_search.load_index()
            print("✅ FAISS index loaded successfully")
        except Exception as e:
            print(f"🔨 Building new FAISS index: {e}")
            # Force rebuild by removing old files
            import shutil
            if os.path.exists("embeddings"):
                shutil.rmtree("embeddings")
            os.makedirs("embeddings", exist_ok=True)
            
            # Build new index
            vector_search.build_index(transactions)
            vector_search.save_index()
            print("✅ New FAISS index built and saved")

        print("✅ API startup completed successfully")
        
        # Update the search router with the initialized services
        update_search_router_services()

    except Exception as e:
        print(f"❌ Startup error: {e}")
        raise

def update_search_router_services():
    """Update the search router with initialized services"""
    try:
        from api.routes import search
        # Pass the initialized services to the search router
        search.embedding_service = embedding_service
        search.vector_search_service = vector_search
        search.summarizer_service = None  # Initialize if you have this
        
        if vector_search and embedding_service:
            from services.summarizerService import SummarizerService
            search.summarizer_service = SummarizerService(vector_search)
            
        print("✅ Search router services updated")
    except Exception as e:
        print(f"❌ Failed to update search router services: {e}")

# @app.get("/")
# async def root():
#     """Root endpoint - simple health check"""
#     services_ready = vector_search is not None and vector_search.is_loaded
#     return {
#         "message": "Financial Data Assistant API",
#         "status": "running" if services_ready else "initializing",
#         "services_ready": services_ready,
#         "endpoints": {
#             "search": "/api/v1/search",
#             "health": "/api/v1/health", 
#             "docs": "/docs"
#         }
#     }

# @app.get("/health")
# async def health_check():
#     """Health check endpoint"""
#     services_ready = vector_search is not None and vector_search.is_loaded
#     return {
#         "status": "healthy" if services_ready else "initializing",
#         "service": "Financial Data Assistant API",
#         "index_loaded": vector_search.is_loaded if vector_search else False,
#         "services_initialized": vector_search is not None
#     }

# @app.get("/rebuild-index")
# async def rebuild_index():
#     """Force rebuild of FAISS index"""
#     if not vector_search:
#         return {"error": "Vector search service not available"}
        
#     try:
#         if not data_file.exists():
#             return {"error": "Transaction data file not found"}
            
#         with open(data_file, "r", encoding='utf-8') as f:
#             transactions = json.load(f)

#         vector_search.build_index(transactions)
#         vector_search.save_index()
        
#         # Update services in router after rebuild
#         update_search_router_services()
        
#         return {
#             "message": "Index rebuilt successfully", 
#             "transactions_processed": len(transactions)
#         }
            
#     except Exception as e:
#         return {"error": f"Rebuild failed: {str(e)}"}

# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(
#         "api.app:app", 
#         host="0.0.0.0", 
#         port=8000, 
#         reload=True,
#         log_level="info"
#     )