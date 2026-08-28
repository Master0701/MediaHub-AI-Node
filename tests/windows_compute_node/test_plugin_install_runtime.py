from __future__ import annotations

import hashlib
import json
import zipfile

import pytest

from windows_compute_node.plugins.installer import (
    PluginInstallError,
)
from windows_compute_node.service.api_server import (
    ComputeNodeAPI,
)


def make_package(
    root,
    *,
    version="1.0.0",
):
    package = (
        root / "test.mhaiplugin"
    )

    manifest = {
        "id": "test.runtime.plugin",
        "name": "Runtime Test",
        "version": version,
        "plugin_type": "ai_node",
        "entrypoint": "plugin.py",
    }

    code = """
def handler(payload):
    return {"ok": True}

def register(context):
    context["workers"].register(
        worker_id="test.runtime.worker",
        name="Runtime Worker",
        job_types=["test_runtime"],
        handler=handler,
        metadata={
            "plugin_id": context["plugin_id"],
        },
    )
"""

    with zipfile.ZipFile(
        package,
        "w",
        compression=zipfile.ZIP_DEFLATED,
    ) as archive:
        archive.writestr(
            "plugin.json",
            json.dumps(manifest),
        )
        archive.writestr(
            "plugin.py",
            code,
        )

    return package


def sha256(path):
    return hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


def test_install_and_runtime_reload(
    tmp_path,
):
    api = ComputeNodeAPI(
        tmp_path / "runtime"
    )

    package = make_package(
        tmp_path
    )

    result = api.install_plugin_package(
        package,
        expected_sha256=sha256(
            package
        ),
    )

    assert result["installed"] is True

    plugins = result["plugins"]

    runtime_plugin = next(
        item
        for item in plugins
        if item.get("plugin_id")
        == "test.runtime.plugin"
    )

    assert (
        runtime_plugin["loaded"]
        is True
    )

    workers = result["workers"]

    assert any(
        item.get("worker_id")
        == "test.runtime.worker"
        for item in workers
    )


def test_update_replaces_existing_plugin(
    tmp_path,
):
    api = ComputeNodeAPI(
        tmp_path / "runtime"
    )

    first = make_package(
        tmp_path,
        version="1.0.0",
    )

    api.install_plugin_package(
        first,
        expected_sha256=sha256(
            first
        ),
    )

    second = make_package(
        tmp_path,
        version="1.1.0",
    )

    result = api.install_plugin_package(
        second,
        expected_sha256=sha256(
            second
        ),
        replace=True,
    )

    assert result["installed"] is True

    runtime_plugin = next(
        item
        for item in result["plugins"]
        if item.get("plugin_id")
        == "test.runtime.plugin"
    )

    assert (
        runtime_plugin["version"]
        == "1.1.0"
    )


def test_wrong_sha256_is_rejected(
    tmp_path,
):
    api = ComputeNodeAPI(
        tmp_path / "runtime"
    )

    package = make_package(
        tmp_path
    )

    with pytest.raises(
        PluginInstallError
    ):
        api.install_plugin_package(
            package,
            expected_sha256=(
                "0" * 64
            ),
        )
