import re
import requests

URL_PATTERN = re.compile(r'https?://[^\s\)\]（）「」、。\n⚠️]+')


def check_urls(report: str) -> str:
    urls = list(set(URL_PATTERN.findall(report)))
    bad_urls: set[str] = set()
    for url in urls:
        try:
            resp = requests.head(url, allow_redirects=True, timeout=5)
            if resp.status_code >= 400:
                bad_urls.add(url)
        except Exception:
            bad_urls.add(url)

    if not bad_urls:
        return report

    def replacer(match: re.Match) -> str:
        u = match.group(0)
        return f"{u} ⚠️ URL要確認" if u in bad_urls else u

    return URL_PATTERN.sub(replacer, report)
