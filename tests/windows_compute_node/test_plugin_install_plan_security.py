from __future__ import annotations

import hashlib
from unittest.mock import Mock

import pytest

from windows_compute_node.plugins.installer import PluginInstallError
from windows_compute_node.service.api_server import ComputeNodeAPI


def test_install_plan_security(tmp_path):
    api = ComputeNodeAPI(tmp_path / "runtime")
    installer = Mock(return_value={"installed": True})
    api.install_plugin_package = installer

    with pytest.raises(PluginInstallError):
        api.confirm_install_plan("0" * 32, "a" * 64)

    payload = b"mediahub-security-test"
    sha256 = hashlib.sha256(payload).hexdigest()

    api.plugin_installer.inspect_package = Mock(
        return_value={
            "id": "mediahub.security_test",
            "name": "Sicherheitstest",
            "version": "0.0.1",
            "runtime": {
                "dependencies": [],
                "isolated": True,
            },
            "dependencies": [],
        }
    )

    plan = api.create_install_plan(
        "security_test.mhaiplugin",
        payload,
        sha256,
        False,
    )
    plan_id = plan["plan_id"]

    with pytest.raises(PluginInstallError):
        api.confirm_install_plan(plan_id, "f" * 64)

    installer.assert_not_called()

    api.cancel_install_plan(plan_id)

    with pytest.raises(PluginInstallError):
        api.confirm_install_plan(plan_id, sha256)

    plan = api.create_install_plan(
        "security_test.mhaiplugin",
        payload,
        sha256,
        False,
    )
    plan_id = plan["plan_id"]

    result = api.confirm_install_plan(plan_id, sha256)

    assert result["installed"] is True
    installer.assert_called_once()

    with pytest.raises(PluginInstallError):
        api.confirm_install_plan(plan_id, sha256)

    installer.assert_called_once()
