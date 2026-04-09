from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from dotenv import load_dotenv

from research.grok_client import GrokClient
from research.searchers import (
    fetch_x_posts,
    fetch_hn_stories,
    fetch_reddit_posts,
    fetch_product_hunt,
    fetch_google_trends,
)
from research.formatter import generate_report, check_urls

PROJECT_ROOT = Path(__file__).resolve().parents[1]

_FALLBACKS: dict = {
    "x_posts": [],
    "hn_stories": [],
    "reddit_posts": [],
    "product_hunt": [],
    "google_trends": {"rising_keywords": [], "related_rising": []},
}


def run_research() -> str:
    load_dotenv()

    grok_client = GrokClient()
    date = datetime.now().strftime("%Y.%m.%d")

    print("🔍 リサーチ開始...")

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {
            "x_posts": executor.submit(fetch_x_posts, grok_client),
            "hn_stories": executor.submit(fetch_hn_stories),
            "reddit_posts": executor.submit(fetch_reddit_posts),
            "product_hunt": executor.submit(fetch_product_hunt, grok_client),
            "google_trends": executor.submit(fetch_google_trends, grok_client),
        }
        results = {}
        for key, future in futures.items():
            try:
                results[key] = future.result()
                print(f"  ✅ {key}")
            except Exception as e:
                results[key] = _FALLBACKS[key]
                print(f"  ⚠️  {key} 取得失敗: {e}")

    results["date"] = date

    print("📝 レポート生成中...")
    report = generate_report(results, grok_client)

    print("🔗 URL疎通確認中...")
    report = check_urls(report)

    output_path = PROJECT_ROOT / "01_リサーチ" / f"{date}.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")

    url_warnings = report.count("⚠️ URL要確認")
    print(f"\n✅ レポート保存完了: {output_path}")
    if url_warnings > 0:
        print(f"⚠️  要確認URL: {url_warnings}件")

    return str(output_path)


if __name__ == "__main__":
    run_research()
