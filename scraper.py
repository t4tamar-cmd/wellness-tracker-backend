import os
import httpx
from typing import List, Dict

BRAVE_SEARCH_URL = "https://api.search.brave.com/res/v1/web/search"

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


def search_brave(query: str, api_key: str, max_results: int = 8) -> List[Dict]:
    headers = {
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
        "X-Subscription-Token": api_key,
    }
    params = {"q": query, "count": max_results}

    with httpx.Client(timeout=30) as client:
        response = client.get(BRAVE_SEARCH_URL, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()

    results = []
    for item in data.get("web", {}).get("results", []):
        results.append({
            "title": item.get("title", ""),
            "url": item.get("url", ""),
            "content": item.get("description", ""),
        })
    return results


def run_all_searches(api_key: str) -> List[Dict]:
    seen_urls = set()
    all_results = []

    for query in SEARCH_QUERIES:
        try:
            results = search_brave(query, api_key)
            for r in results:
                url = r["url"]
                if url not in seen_urls:
                    seen_urls.add(url)
                    all_results.append(r)
        except Exception as e:
            print(f"[scraper] Query '{query}' failed: {e}")

    return all_results
