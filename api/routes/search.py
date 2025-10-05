# api/routes/search.py
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

# These will be set by app.py after services initialize
embedding_service = None
vector_search_service = None
summarizer_service = None

@router.get("/search")
async def search_transactions(
    query: str = Query(..., description="Natural language query", min_length=1, max_length=200),
    top_k: Optional[int] = Query(5, ge=1, le=200)
):
    """Search transactions semantically and return top results.\n
       High amount transactions .\n
       Salary deposits this month .\n
       What are my top expenses last month. \n
       """""
    
    # Check if services are ready
    if not vector_search_service or not vector_search_service.is_loaded:
        raise HTTPException(
            status_code=503, 
            detail="Search services are not ready. Please try again later."
        )
    
    try:
        results = vector_search_service.semantic_search(query, top_k=top_k)
        
        # Generate summary if summarizer is available
        summary = None
        if summarizer_service:
            summary = summarizer_service.summarize_results(results, query)
        
        return {
            "query": query,
            "top_k": top_k,
            "results_found": len(results),
            "results": results,
            "summary": summary
        }
        
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

# @router.get("/health")
# async def health_check():
#     """Health check endpoint"""
#     services_ready = vector_search_service and vector_search_service.is_loaded
#     return {
#         "status": "ok" if services_ready else "initializing",
#         "services_ready": services_ready
#     }