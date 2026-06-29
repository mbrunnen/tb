import pytest


@pytest.fixture
def config_dir(tmp_path, monkeypatch):
    monkeypatch.setattr("tbctl.config.CONFIG_DIR", tmp_path)
    return tmp_path
