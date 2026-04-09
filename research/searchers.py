import requests
from concurrent.futures import ThreadPoolExecutor
from research.grok_client import GrokClient

HN_BASE = "https://hacker-news.firebaseio.com/v0"
AI_KEYWORDS = {
    "ai", "llm", "gpt", "claude", "gemini", "mistral", "llama",
    "openai", "anthropic", "machine learning", "neural", "transformer",
    "chatgpt", "copilot", "diffusion", "multimodal",
}
REDDIT_HEADERS = {"User-Agent": "sns-ai-research-bot/1.0"}


def fetch_hn_stories() -> list[dict]:
    try:
        resp = requests.get(f"{HN_BASE}/topstories.json", timeout=10)
        resp.raise_for_status()
        story_ids = resp.json()[:50]
    except Exception:
        return []

    def _fetch_story(story_id: int) -> dict | None:
        for _ in range(3):
            try:
                r = requests.get(f"{HN_BASE}/item/{story_id}.json", timeout=5)
                r.raise_for_status()
                return r.json()
            except Exception:
                continue
        return None

    with ThreadPoolExecutor(max_workers=10) as executor:
        stories = list(executor.map(_fetch_story, story_ids))

    results = []
    for story in stories:
        if not story:
            continue
        title = story.get("title", "").lower()
        score = story.get("score", 0)
        comments = story.get("descendants", 0)
        if (score >= 100 or comments >= 30) and any(kw in title for kw in AI_KEYWORDS):
            results.append({
                "title": story.get("title", ""),
                "url": story.get("url", f"https://news.ycombinator.com/item?id={story['id']}"),
                "points": score,
                "comments": comments,
            })
    return results[:5]
