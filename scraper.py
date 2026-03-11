import os
import httpx
from typing import List, Dict

TAVILY_API_URL = "https://api.tavily.com/search"

SEARCH_QUERIES = [
    "vitamin personalization app California startup",
    "wellness personalization app California",
    "personalized supplement company California",
    "AI wellness platform California startup",
    "health personalization app California",
    "custom nutrition app California",
    "personalized vitamin subscription California",
    "wellness tech startup California AI",
]


def search_tavily(query: str, api_key: str, max_results: int = 8) -> List[Dict]:
    payload = {
        "api_key": api_key,
        "query": query,
        "search_depth": "advanced",
        "include_answer": False,
        "include_raw_content": False,
        "max_results": max_results,
        "include_domains": [],
        "exclude_domains": [],
    }

    with httpx.Client(timeout=30) as client:
        response = client.post(TAVILY_API_URL, json=payload)
        response.raise_for_status()
        data = response.json()

    results = []
    for item in data.get("results", []):
        results.append({
            "title": item.get("title", ""),
            "url": item.get("url", ""),
            "content": item.get("content", ""),
        })
    return results


def run_all_searches(api_key: str) -> List[Dict]:
    seen_urls = set()
    all_results = []

    for query in SEARCH_QUERIES:
        try:
            results = search_tavily(query, api_key)
            for r in results:
                url = r["url"]
                if url not in seen_urls:
                    seen_urls.add(url)
                    all_results.append(r)
        except Exception as e:
            print(f"[scraper] Query '{query}' failed: {e}")

    return all_results
