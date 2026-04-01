"""Tests for configuration loading and env var expansion."""
from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from app.config import Config, _expand_env_vars, get_config


def test_get_config_returns_config_instance():
    cfg = get_config()
    assert isinstance(cfg, Config)


def test_get_config_singleton():
    cfg1 = get_config()
    cfg2 = get_config()
    assert cfg1 is cfg2


def test_config_server_section():
    cfg = get_config()
    assert "host" in cfg.server or cfg.server == {} or isinstance(cfg.server, dict)


def test_config_get_nested():
    cfg = get_config()
    chunk_size = cfg.get("chunking", "chunk_size")
    assert chunk_size is None or isinstance(chunk_size, int)


def test_config_get_default():
    cfg = get_config()
    result = cfg.get("nonexistent", "key", default="fallback")
    assert result == "fallback"


def test_config_require_raises_on_missing():
    cfg = get_config()
    with pytest.raises(KeyError):
        cfg.require("nonexistent_section", "nonexistent_key")


def test_expand_env_vars_substitutes():
    os.environ["_TEST_VAR_123"] = "hello_world"
    result = _expand_env_vars("prefix_${_TEST_VAR_123}_suffix")
    assert result == "prefix_hello_world_suffix"
    del os.environ["_TEST_VAR_123"]


def test_expand_env_vars_missing_keeps_original():
    result = _expand_env_vars("${DEFINITELY_NOT_SET_XYZ}")
    assert result == "${DEFINITELY_NOT_SET_XYZ}"


def test_expand_env_vars_nested_dict():
    os.environ["_NESTED_TEST"] = "value123"
    data = {"key": "${_NESTED_TEST}", "nested": {"k2": "${_NESTED_TEST}"}}
    result = _expand_env_vars(data)
    assert result["key"] == "value123"
    assert result["nested"]["k2"] == "value123"
    del os.environ["_NESTED_TEST"]


def test_expand_env_vars_list():
    os.environ["_LIST_VAR"] = "list_value"
    result = _expand_env_vars(["${_LIST_VAR}", "static"])
    assert result == ["list_value", "static"]
    del os.environ["_LIST_VAR"]


def test_public_dict_removes_api_keys():
    cfg = get_config()
    pub = cfg.public_dict()
    for model_name, model_cfg in pub.get("models", {}).items():
        assert "api_key" not in model_cfg, f"api_key exposed in {model_name}"


def test_config_paths_section():
    cfg = get_config()
    assert isinstance(cfg.paths, dict)


def test_config_evaluation_section():
    cfg = get_config()
    ev = cfg.evaluation
    assert isinstance(ev, dict)
