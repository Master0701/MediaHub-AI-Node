from __future__ import annotations

from windows_compute_node.service.api_server import (
    ComputeNodeAPI,
)


def test_compute_node_api_initializes_runtime_plugins(
    tmp_path,
):
    runtime_dir = tmp_path / "runtime"

    api = ComputeNodeAPI(
        runtime_dir
    )

    assert api.runtime_dir == runtime_dir

    assert (
        api.plugin_loader.plugin_root
        == runtime_dir / "plugins"
    )

    assert isinstance(
        api.plugin_load_results,
        list,
    )
