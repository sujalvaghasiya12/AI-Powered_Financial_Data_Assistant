# services/summarizer_service.py
from typing import List, Dict, Optional, Any
from datetime import datetime
import statistics
import asyncio
import math

# Configurable thresholds
LARGE_TXN_THRESHOLD = 5000  # ₹ threshold for highlighting large txns
TOP_N_CATEGORIES = 5        # how many categories to include in breakdown

class SummarizerService:
    def __init__(self, vector_search_service):
        """
        vector_search_service must provide `semantic_search(query, top_k=?, filters=?)`
        It can be synchronous or asynchronous (this wrapper handles both).
        """
        self.vector_search = vector_search_service

    # ----------------------
    # Public entry point
    # ----------------------
    async def query_with_summary(self, query: str, filters: Optional[Dict] = None, top_k: int = 50, only_debits: bool = True) -> Dict[str, Any]:
        """
        Perform semantic search (sync/async aware) and return summarized results.

        Args:
            query: natural language query
            filters: structured filters (userId, date range, min_amount, category, ...)
            top_k: number of candidates to retrieve from semantic search before summarizing
            only_debits: if True, treat summaries as "spending" and consider only Debit transactions
        Returns:
            dict: { "search_results": [...], "summary": {...} }
        """
        transactions = await self._run_search(query, filters=filters, top_k=top_k)

        # Optionally filter to debits for spending-oriented summaries
        if only_debits:
            spending_txns = [t for t in transactions if str(t.get("type", "")).lower() == "debit"]
        else:
            spending_txns = transactions

        summary = self.summarize_results(spending_txns, query)
        return {"search_results": transactions, "summary": summary}

    # ----------------------
    # Wrapper to support sync/async vector_search
    # ----------------------
    async def _run_search(self, query: str, filters: Optional[Dict] = None, top_k: int = 50) -> List[Dict]:
        # vector_search.semantic_search may be sync or async; handle both.
        search_fn = getattr(self.vector_search, "semantic_search", None)
        if search_fn is None:
            raise RuntimeError("Underlying vector_search service has no 'semantic_search' method")

        # call appropriately
        if asyncio.iscoroutinefunction(search_fn):
            results = await search_fn(query=query, top_k=top_k, filters=filters)
        else:
            # run synchronous function in threadpool to avoid blocking event loop
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(None, lambda: search_fn(query=query, top_k=top_k, filters=filters))

        # Ensure results is a list
        if results is None:
            return []
        return list(results)

    # ----------------------
    # Summarization core
    # ----------------------
    def summarize_results(self, transactions: List[Dict], query: str) -> Dict[str, Any]:
        """
        Create a summary dict for the provided transactions.
        Assumes transactions are already filtered appropriately (e.g., debit-only if needed).
        """
        if not transactions:
            return {"query": query, "total_transactions": 0, "total_amount": 0.0, "average_amount": 0.0, "category_breakdown": {}, "monthly_summary": {}, "top_category": None, "insights": ["No transactions found."]}

        # Normalize amounts to floats
        for t in transactions:
            t['amount'] = float(t.get('amount', 0))

        total_amount = sum(t['amount'] for t in transactions)
        avg_amount = statistics.mean(t['amount'] for t in transactions) if transactions else 0.0

        # Category breakdown (sum amounts per category)
        categories: Dict[str, float] = {}
        for txn in transactions:
            cat = txn.get('category', 'Others') or 'Others'
            categories[cat] = categories.get(cat, 0.0) + txn['amount']

        # Top categories (sorted)
        sorted_cats = sorted(categories.items(), key=lambda x: x[1], reverse=True)
        top_categories = {k: round(v, 2) for k, v in sorted_cats[:TOP_N_CATEGORIES]}

        # Monthly summary (YYYY-MM => total)
        monthly_data: Dict[str, float] = {}
        for txn in transactions:
            date_str = txn.get('date', '')
            ym = self._safe_year_month(date_str)
            monthly_data[ym] = monthly_data.get(ym, 0.0) + txn['amount']

        # Insights
        insights = self._generate_insights(transactions, categories, total_amount)

        summary = {
            "query": query,
            "total_transactions": len(transactions),
            "total_amount": round(total_amount, 2),
            "average_amount": round(avg_amount, 2),
            "category_breakdown": top_categories,
            "monthly_summary": {k: round(v, 2) for k, v in monthly_data.items()},
            "top_category": sorted_cats[0][0] if sorted_cats else None,
            "insights": insights
        }
        return summary

    # ----------------------
    # Helpers
    # ----------------------
    def _generate_insights(self, transactions: List[Dict], categories: Dict[str, float], total_amount: float) -> List[str]:
        insights: List[str] = []
        if not transactions:
            return insights

        # Top category insight
        if categories:
            top_cat, top_amount = max(categories.items(), key=lambda x: x[1])
            pct = (top_amount / total_amount * 100) if total_amount > 0 else 0.0
            insights.append(f"Highest spending category: {top_cat} ({pct:.1f}% of total).")

        # Largest transaction insight
        max_txn = max(transactions, key=lambda t: t.get('amount', 0))
        if max_txn and max_txn.get('amount', 0) >= LARGE_TXN_THRESHOLD:
            desc = max_txn.get('description', 'unknown')
            amt = max_txn.get('amount', 0)
            date = max_txn.get('date', '')
            insights.append(f"Largest transaction: ₹{amt:.2f} on {date} — {desc}.")

        # Repeated merchant / frequent payer insight
        merchant_counts: Dict[str, int] = {}
        for t in transactions:
            m = (t.get('description') or '').lower()
            merchant_counts[m] = merchant_counts.get(m, 0) + 1
        most_common_merchant = max(merchant_counts.items(), key=lambda x: x[1])[0] if merchant_counts else None
        if most_common_merchant and merchant_counts[most_common_merchant] > 2:
            insights.append(f"Frequent payee: {most_common_merchant} ({merchant_counts[most_common_merchant]} transactions).")

        # Frequency insight
        if len(transactions) > 50:
            insights.append(f"High transaction volume: {len(transactions)} transactions in selection.")

        return insights

    def _safe_year_month(self, date_str: str) -> str:
        """
        Return 'YYYY-MM' for a date string, with fallbacks.
        Accepts ISO date (YYYY-MM-DD). If parsing fails, returns 'unknown'.
        """
        if not date_str or not isinstance(date_str, str):
            return "unknown"
        try:
            # Try ISO first
            dt = datetime.fromisoformat(date_str)
            return f"{dt.year:04d}-{dt.month:02d}"
        except Exception:
            # fallback: try substrings like 'YYYY-MM'
            if len(date_str) >= 7 and date_str[4] == '-' and date_str[7] in ['-', 'T', ' ']:
                return date_str[:7]
            # last resort
            return "unknown"
