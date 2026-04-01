"""Configuration loader with env var expansion and singleton access."""
from __future__ import annotations

import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml


_CONFIG_PATH = Path(__file__).parent.parent / "config.yaml"


def _expand_env_vars(value: Any) -> Any:
    """Recursively expand ${VAR} references in config values."""
    if isinstance(value, str):
        pattern = re.compile(r"\$\{([^}]+)\}")
        def replacer(match: re.Match) -> str:
            var_name = match.group(1)
            return os.environ.get(var_name, match.group(0))
        return pattern.sub(replacer, value)
    if isinstance(value, dict):
        return {k: _expand_env_vars(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_expand_env_vars(item) for item in value]
    return value


def _load_yaml(path: Path) -> dict:
    with open(path, "r") as f:
        return yaml.safe_load(f) or {}


class Config:
    """Wrapper around the raw YAML config dict with dot-path access helpers."""

    def __init__(self, data: dict) -> None:
        self._data = data

    def get(self, *keys: str, default: Any = None) -> Any:
        """Navigate nested keys: cfg.get('models', 'claude', 'model')."""
        node = self._data
        for key in keys:
            if not isinstance(node, dict):
                return default
            node = node.get(key, None)
            if node is None:
                return default
        return node

    def require(self, *keys: str) -> Any:
        val = self.get(*keys)
        if val is None:
            raise KeyError(f"Required config key missing: {'.'.join(keys)}")
        return val

    @property
    def server(self) -> dict:
        return self._data.get("server", {})

    @property
    def paths(self) -> dict:
        return self._data.get("paths", {})

    @property
    def database(self) -> dict:
        return self._data.get("database", {})

    @property
    def logging(self) -> dict:
        return self._data.get("logging", {})

    @property
    def downloader(self) -> dict:
        return self._data.get("downloader", {})

    @property
    def topic_defaults(self) -> dict:
        return self._data.get("topic_defaults", {})

    @property
    def parsing(self) -> dict:
        return self._data.get("parsing", {})

    @property
    def chunking(self) -> dict:
        return self._data.get("chunking", {})

    @property
    def retrieval(self) -> dict:
        return self._data.get("retrieval", {})

    @property
    def evaluation(self) -> dict:
        return self._data.get("evaluation", {})

    @property
    def models(self) -> dict:
        return self._data.get("models", {})

    @property
    def frontend(self) -> dict:
        return self._data.get("frontend", {})

    @property
    def document_sources(self) -> dict:
        return self._data.get("document_sources", {})

    def public_dict(self) -> dict:
        """Return config without secrets (API keys)."""
        import copy
        data = copy.deepcopy(self._data)
        for model_cfg in data.get("models", {}).values():
            model_cfg.pop("api_key", None)
        return data


@lru_cache(maxsize=1)
def get_config() -> Config:
    """Return the singleton Config instance."""
    raw = _load_yaml(_CONFIG_PATH)
    expanded = _expand_env_vars(raw)
    return Config(expanded)
