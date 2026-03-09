import os

from dotenv import load_dotenv

load_dotenv()

# Try to import Tavily; fall back to mock results
try:
    from tavily import TavilyClient

    _tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY", ""))
    _tavily_available = True
except Exception:
    _tavily_available = False


def web_search(query: str, max_results: int = 3) -> dict:
    """
    Search the internet for information about a query.
    Use for: current events, restaurant recommendations, general facts,
    anything not in the agent's knowledge.
    """
    if not query.strip():
        return {"error": "Query cannot be empty."}

    if _tavily_available and os.getenv("TAVILY_API_KEY"):
        try:
            response = _tavily.search(query=query, max_results=max_results)
            results = [
                {
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "snippet": r.get("content", "")[:200],
                }
                for r in response.get("results", [])
            ]
            return {"query": query, "results_count": len(results), "results": results}
        except Exception as e:
            return {"error": f"Search failed: {str(e)}"}

    # Fallback mock results for demo purposes
    return {
        "query": query,
        "results_count": 2,
        "source": "mock",
        "results": [
            {
                "title": f"Top result for: {query}",
                "url": "https://example.com/result1",
                "snippet": f"This is a mock search result for '{query}'. Connect Tavily API for real results.",
            },
            {
                "title": f"Another result for: {query}",
                "url": "https://example.com/result2",
                "snippet": f"Second mock result for '{query}'. Useful for demo purposes.",
            },
        ],
    }
