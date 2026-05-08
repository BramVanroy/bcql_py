from pathlib import Path

import pytest

from bcql_py.utils import get_blacklab_g4_grammar


class _DummyResponse:
    def __init__(self, text: str):
        self.text = text
        self.raise_for_status_called = False

    def raise_for_status(self):
        self.raise_for_status_called = True


def test_get_blacklab_g4_grammar_uses_tag_url(monkeypatch: pytest.MonkeyPatch):
    captured = {"url": None}
    response = _DummyResponse("grammar-tag")

    def fake_get(url: str):
        captured["url"] = url
        return response

    monkeypatch.setattr("bcql_py.utils.requests.get", fake_get)

    content = get_blacklab_g4_grammar(tag="v1.2.3")

    assert content == "grammar-tag"
    assert response.raise_for_status_called
    assert captured["url"] is not None
    assert "/BlackLab/v1.2.3/" in captured["url"]


def test_get_blacklab_g4_grammar_uses_branch_and_writes_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    captured = {"url": None}
    response = _DummyResponse("grammar-branch")

    def fake_get(url: str):
        captured["url"] = url
        return response

    monkeypatch.setattr("bcql_py.utils.requests.get", fake_get)

    output_path = tmp_path / "Bcql.g4"
    content = get_blacklab_g4_grammar(output_path=output_path, branch="main")

    assert content == "grammar-branch"
    assert response.raise_for_status_called
    assert captured["url"] is not None
    assert "/BlackLab/main/" in captured["url"]
    assert output_path.read_text(encoding="utf-8") == "grammar-branch"
