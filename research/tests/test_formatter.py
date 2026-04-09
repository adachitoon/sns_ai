from unittest.mock import patch, MagicMock
import pytest
import requests as req
from research.formatter import check_urls


def test_check_urls_keeps_200_url():
    report = "詳細はこちら https://example.com/article を確認してください"

    def mock_head(url, allow_redirects=True, timeout=5):
        resp = MagicMock()
        resp.status_code = 200
        return resp

    with patch("research.formatter.requests.head", side_effect=mock_head):
        result = check_urls(report)

    assert "⚠️" not in result
    assert "https://example.com/article" in result


def test_check_urls_marks_404_url():
    report = "詳細はこちら https://example.com/broken を確認してください"

    def mock_head(url, allow_redirects=True, timeout=5):
        resp = MagicMock()
        resp.status_code = 404
        return resp

    with patch("research.formatter.requests.head", side_effect=mock_head):
        result = check_urls(report)

    assert "https://example.com/broken ⚠️ URL要確認" in result


def test_check_urls_marks_timeout_url():
    report = "詳細はこちら https://example.com/slow を確認してください"

    with patch("research.formatter.requests.head", side_effect=req.exceptions.Timeout):
        result = check_urls(report)

    assert "https://example.com/slow ⚠️ URL要確認" in result


def test_check_urls_handles_multiple_urls():
    report = "OK: https://good.com/page NG: https://bad.com/page"

    def mock_head(url, allow_redirects=True, timeout=5):
        resp = MagicMock()
        resp.status_code = 200 if "good" in url else 404
        return resp

    with patch("research.formatter.requests.head", side_effect=mock_head):
        result = check_urls(report)

    assert "https://good.com/page" in result
    assert "⚠️" not in result.split("https://good.com/page")[1].split("https://bad.com/page")[0]
    assert "https://bad.com/page ⚠️ URL要確認" in result
