import os

from src.proxy_utils import normalize_proxy_environment


def test_normalizes_socks_scheme(monkeypatch):
    monkeypatch.setenv("ALL_PROXY", "socks://127.0.0.1:10808")
    normalize_proxy_environment()
    assert os.environ["ALL_PROXY"] == "socks5://127.0.0.1:10808"


def test_disable_proxy_clears_env(monkeypatch):
    monkeypatch.setenv("BOT_DISABLE_PROXY", "1")
    monkeypatch.setenv("ALL_PROXY", "socks://127.0.0.1:10808")
    monkeypatch.setenv("HTTP_PROXY", "http://127.0.0.1:8080")
    normalize_proxy_environment()
    assert "ALL_PROXY" not in os.environ
    assert "HTTP_PROXY" not in os.environ
