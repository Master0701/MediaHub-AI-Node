"""Regressionstests fuer deklarierte MediaHub_Tools-Abhaengigkeiten."""

import pytest

from app.plugins.errors import PluginManifestError
from app.plugins.manifest import PluginManifest


def base_manifest(required_tools):
    return {
        "id": "mediahub.smolvlm2",
        "name": "MediaHub SmolVLM2 Vision",
        "version": "0.1.1",
        "type": "model",
        "entrypoint": "plugin:SmolVLM2Plugin",
        "required_tools": required_tools,
    }


def test_structured_model_requirement_is_preserved():
    manifest = PluginManifest.from_dict(base_manifest([{
        "id": "smolvlm2-model",
        "version": "0.1.0",
        "source": "mediahub_tools",
        "required": True,
        "targets": ["raspberry_pi", "windows_compute"],
    }]))
    assert manifest.required_tools == ("smolvlm2-model",)
    tool = manifest.tool_requirements[0]
    assert tool.tool_id == "smolvlm2-model"
    assert tool.source == "mediahub_tools"
    assert tool.version == "0.1.0"
    assert tool.required is True
    assert tool.targets == ("raspberry_pi", "windows_compute")


def test_old_style_system_tool_still_works():
    manifest = PluginManifest.from_dict(base_manifest(["ffmpeg"]))
    assert manifest.required_tools == ("ffmpeg",)
    assert manifest.tool_requirements[0].source == "system"


@pytest.mark.parametrize("tools", [
    [{"source": "mediahub_tools"}],
    [{"id": "smolvlm2-model", "required": "yes"}],
    [{"id": "smolvlm2-model", "targets": "raspberry_pi"}],
    ["ffmpeg", "ffmpeg"],
    [42],
])
def test_bad_tool_declarations_are_rejected(tools):
    with pytest.raises(PluginManifestError):
        PluginManifest.from_dict(base_manifest(tools))
