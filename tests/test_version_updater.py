import pytest
import toml

from python_semantic_release.models import Release, VersionConfig
from python_semantic_release.version.updater import VersionUpdater
from tests.conftest import make_context


@pytest.fixture
def updater() -> VersionUpdater:
    return VersionUpdater()


def _ctx_with_release(tmp_path, version="1.1.0"):
    ctx = make_context(tmp_path)
    ctx.next_release = Release(
        version=version, git_tag=f"v{version}", git_head="newsha"
    )
    return ctx


def test_prepare_no_next_release_is_noop(tmp_path, updater):
    ctx = make_context(tmp_path)
    ctx.next_release = None
    updater.prepare(ctx)  # should not raise


def test_prepare_writes_plain_version_file(tmp_path, updater):
    ctx = _ctx_with_release(tmp_path, "2.0.0")
    updater.config = VersionConfig(version_files=["VERSION"])
    updater.prepare(ctx)
    assert (tmp_path / "VERSION").read_text() == "2.0.0\n"


def test_prepare_creates_missing_version_file(tmp_path, updater):
    ctx = _ctx_with_release(tmp_path, "0.1.0")
    updater.config = VersionConfig(version_files=["VERSION"])
    updater.prepare(ctx)
    assert (tmp_path / "VERSION").exists()


def test_prepare_updates_toml_project_version(tmp_path, updater):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nversion = "0.0.1"\n')
    ctx = _ctx_with_release(tmp_path, "1.2.3")
    updater.config = VersionConfig(
        version_files=["pyproject.toml:project.version"]
    )
    updater.prepare(ctx)
    data = toml.load(pyproject)
    assert data["project"]["version"] == "1.2.3"


def test_prepare_updates_multiple_files(tmp_path, updater):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nversion = "0.0.1"\n')
    ctx = _ctx_with_release(tmp_path, "3.0.0")
    updater.config = VersionConfig(
        version_files=["VERSION", "pyproject.toml:project.version"]
    )
    updater.prepare(ctx)
    assert (tmp_path / "VERSION").read_text() == "3.0.0\n"
    assert toml.load(pyproject)["project"]["version"] == "3.0.0"


def test_update_toml_missing_file_raises(tmp_path, updater):
    ctx = _ctx_with_release(tmp_path, "1.0.0")
    updater.config = VersionConfig(
        version_files=["nonexistent.toml:project.version"]
    )
    with pytest.raises(FileNotFoundError):
        updater.prepare(ctx)


def test_update_unsupported_structured_file_raises(tmp_path, updater):
    ctx = _ctx_with_release(tmp_path, "1.0.0")
    updater.config = VersionConfig(version_files=["config.json:version"])
    with pytest.raises(ValueError, match="Unsupported"):
        updater.prepare(ctx)


def test_prepare_creates_nested_toml_keys(tmp_path, updater):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("[project]\n")
    ctx = _ctx_with_release(tmp_path, "1.0.0")
    updater.config = VersionConfig(
        version_files=["pyproject.toml:project.version"]
    )
    updater.prepare(ctx)
    data = toml.load(pyproject)
    assert data["project"]["version"] == "1.0.0"
