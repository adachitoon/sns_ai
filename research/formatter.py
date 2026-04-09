import re
import requests
from research.grok_client import GrokClient

URL_PATTERN = re.compile(r'https?://[^\s\)\]（）「」、。\n⚠️]+')


def check_urls(report: str) -> str:
    urls = list(set(URL_PATTERN.findall(report)))
    for url in urls:
        try:
            resp = requests.head(url, allow_redirects=True, timeout=5)
            if resp.status_code >= 400:
                report = report.replace(url, f"{url} ⚠️ URL要確認")
        except Exception:
            report = report.replace(url, f"{url} ⚠️ URL要確認")
    return report
