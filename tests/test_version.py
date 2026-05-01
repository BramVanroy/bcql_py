import importlib
from importlib.metadata import PackageNotFoundError
from pathlib import Path

import pytest


_ROOT = Path(__file__).resolve().parents[1]


class TestPackageVersion:
    """Tests for package version retrieval and fallback behavior."""

    def test_package_version_falls_back_when_metadata_missing(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ):
        """The package should expose a safe fallback version when metadata is unavailable."""

        def _raise_package_not_found(_: str) -> str:
            raise PackageNotFoundError

        monkeypatch.setattr(
            "importlib.metadata.version", _raise_package_not_found
        )

        module_path = _ROOT / "src" / "bcql_py" / "__init__.py"
        spec = importlib.util.spec_from_file_location(
            "bcql_py_fallback_version_test", module_path
        )
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        assert module.__version__ == "0.0.0"
