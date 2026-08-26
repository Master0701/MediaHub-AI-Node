from __future__ import annotations

import hashlib
import importlib.util
import zipfile
from pathlib import Path

import pytest

ROOT = (
    Path(__file__)
    .resolve()
    .parents[2]
)

FILE = (
    ROOT
    / "windows_compute_node"
    / "plugin_sources"
    / "speech_to_text"
    / "python_provisioner.py"
)


def load_module():
    spec = (
        importlib.util.spec_from_file_location(
            "speech_python_provisioner_test",
            FILE,
        )
    )

    module = (
        importlib.util.module_from_spec(
            spec
        )
    )

    assert spec.loader is not None

    spec.loader.exec_module(
        module
    )

    return module


def test_official_metadata():
    module = load_module()

    data = module.package_metadata()

    assert (
        data["version"]
        == "3.12.10"
    )

    assert (
        data["filename"]
        == (
            "python-3.12.10-"
            "embed-amd64.zip"
        )
    )

    assert (
        data["source"]
        == "python.org"
    )

    assert (
        data["changes_system_path"]
        is False
    )

    assert (
        data["changes_registry"]
        is False
    )


def test_official_url_allowed():
    module = load_module()

    module.validate_official_source()


def test_non_python_domain_rejected():
    module = load_module()

    with pytest.raises(
        module.PythonProvisionError
    ):
        module.validate_official_source(
            "https://example.com/"
            + module.PYTHON_FILENAME
        )


def test_http_rejected():
    module = load_module()

    with pytest.raises(
        module.PythonProvisionError
    ):
        module.validate_official_source(
            "http://www.python.org/"
            "ftp/python/3.12.10/"
            + module.PYTHON_FILENAME
        )


def test_file_hash(
    tmp_path,
):
    module = load_module()

    file = (
        tmp_path / "data.bin"
    )

    data = b"MediaHub"

    file.write_bytes(data)

    assert (
        module.file_hash(
            file,
            "md5",
        )
        == hashlib.md5(
            data
        ).hexdigest()
    )

    assert (
        module.file_hash(
            file,
            "sha256",
        )
        == hashlib.sha256(
            data
        ).hexdigest()
    )


def test_safe_extract(
    tmp_path,
):
    module = load_module()

    package = (
        tmp_path / "python.zip"
    )

    with zipfile.ZipFile(
        package,
        "w",
    ) as archive:
        archive.writestr(
            "python.exe",
            b"fake",
        )

        archive.writestr(
            "python312._pth",
            (
                "python312.zip\n"
                ".\n"
                "#import site\n"
            ),
        )

    target = (
        tmp_path / "runtime"
    )

    executable = (
        module.extract_package(
            package,
            target,
            verify=False,
        )
    )

    assert executable.is_file()

    pth = (
        target
        / "python312._pth"
    ).read_text(
        encoding="utf-8"
    )

    assert "import site" in pth
    assert "#import site" not in pth


def test_zip_traversal_rejected(
    tmp_path,
):
    module = load_module()

    package = (
        tmp_path / "evil.zip"
    )

    with zipfile.ZipFile(
        package,
        "w",
    ) as archive:
        archive.writestr(
            "python.exe",
            b"fake",
        )

        archive.writestr(
            "python312._pth",
            "import site\n",
        )

        archive.writestr(
            "../evil.txt",
            "bad",
        )

    with pytest.raises(
        module.PythonProvisionError
    ):
        module.extract_package(
            package,
            tmp_path / "runtime",
            verify=False,
        )


def test_private_root_contract(
    tmp_path,
    monkeypatch,
):
    module = load_module()

    monkeypatch.setenv(
        "MEDIAHUB_COMPUTE_RUNTIME",
        str(tmp_path),
    )

    root = (
        module.default_private_root()
    )

    assert (
        root
        == (
            tmp_path
            / "private_python"
            / "cpython-3.12.10-x64"
        )
    )
