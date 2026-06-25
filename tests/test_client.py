import pytest

from tb.commands._client import parse_response, resolve_device_id


def test_parse_response_json():
    assert parse_response('{"a": 1}') == {"a": 1}


def test_parse_response_python_repr():
    assert parse_response("[{'key': 'temp', 'value': True}]") == [{"key": "temp", "value": True}]


def test_parse_response_already_parsed():
    value = [{"key": "temp"}]
    assert parse_response(value) is value


def test_resolve_device_id_uuid_passthrough():
    uuid = "11111111-2222-3333-4444-555555555555"
    assert resolve_device_id("default", uuid) == uuid


def test_resolve_device_id_name_lookup(monkeypatch):
    from unittest.mock import MagicMock

    found = MagicMock()
    found.id.id = "resolved-uuid"
    api = MagicMock()
    api.get_tenant_device.return_value = found
    monkeypatch.setattr("tb.commands._client.device_api", lambda profile: api)

    assert resolve_device_id("default", "OX1-UQEUBW") == "resolved-uuid"
    api.get_tenant_device.assert_called_once_with(device_name="OX1-UQEUBW")


def test_resolve_device_id_not_found(monkeypatch):
    from unittest.mock import MagicMock

    import typer

    api = MagicMock()
    api.get_tenant_device.return_value = None
    monkeypatch.setattr("tb.commands._client.device_api", lambda profile: api)

    with pytest.raises(typer.Exit):
        resolve_device_id("default", "missing")


def test_resolve_device_id_403_hint(monkeypatch, capsys):
    from unittest.mock import MagicMock

    import typer

    from tb_client.exceptions import ApiException

    api = MagicMock()
    api.get_tenant_device.side_effect = ApiException(status=403, reason="Forbidden")
    monkeypatch.setattr("tb.commands._client.device_api", lambda profile: api)

    with pytest.raises(typer.Exit):
        resolve_device_id("default", "OX1-UQEUBW")
    assert "pass the device UUID instead" in capsys.readouterr().err
