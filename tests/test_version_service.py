import pytest

from python_semantic_release.models import ReleaseType
from python_semantic_release.version.service import (
    SemanticVersion,
    VersionService,
)

# --- SemanticVersion.parse ---

def test_parse_simple_version():
    v = SemanticVersion.parse("1.2.3")
    assert v.major == 1
    assert v.minor == 2
    assert v.patch == 3


def test_parse_v_prefix():
    v = SemanticVersion.parse("v2.0.0")
    assert v.major == 2
    assert v.minor == 0
    assert v.patch == 0


def test_parse_prerelease():
    v = SemanticVersion.parse("1.0.0-alpha.1")
    assert v.prerelease == "alpha.1"
    assert v.major == 1


def test_parse_build_metadata():
    v = SemanticVersion.parse("1.0.0+build.123")
    assert v.build_metadata == "build.123"


def test_parse_prerelease_and_build():
    v = SemanticVersion.parse("1.0.0-beta.2+sha.deadbeef")
    assert v.prerelease == "beta.2"
    assert v.build_metadata == "sha.deadbeef"


def test_parse_invalid_raises():
    with pytest.raises(ValueError):
        SemanticVersion.parse("invalid")


def test_parse_missing_patch_raises():
    with pytest.raises(ValueError):
        SemanticVersion.parse("1.2")


def test_parse_zero_version():
    v = SemanticVersion.parse("0.0.0")
    assert v.major == 0
    assert v.minor == 0
    assert v.patch == 0


# --- SemanticVersion.__str__ ---

def test_str_simple():
    assert str(SemanticVersion(1, 2, 3)) == "1.2.3"


def test_str_with_prerelease():
    assert str(SemanticVersion(1, 0, 0, prerelease="rc.1")) == "1.0.0-rc.1"


def test_str_with_build_metadata():
    assert str(SemanticVersion(1, 0, 0, build_metadata="sha.abc")) == "1.0.0+sha.abc"


def test_str_with_prerelease_and_build():
    v = SemanticVersion(1, 0, 0, prerelease="alpha", build_metadata="001")
    assert str(v) == "1.0.0-alpha+001"


# --- SemanticVersion.bump ---

def test_bump_major():
    v = SemanticVersion(1, 2, 3)
    bumped = v.bump(ReleaseType.MAJOR)
    assert bumped.major == 2
    assert bumped.minor == 0
    assert bumped.patch == 0


def test_bump_minor():
    v = SemanticVersion(1, 2, 3)
    bumped = v.bump(ReleaseType.MINOR)
    assert bumped.major == 1
    assert bumped.minor == 3
    assert bumped.patch == 0


def test_bump_patch():
    v = SemanticVersion(1, 2, 3)
    bumped = v.bump(ReleaseType.PATCH)
    assert bumped.major == 1
    assert bumped.minor == 2
    assert bumped.patch == 4


def test_bump_major_resets_prerelease():
    v = SemanticVersion(1, 0, 0, prerelease="alpha")
    bumped = v.bump(ReleaseType.MAJOR)
    assert bumped.prerelease is None


def test_bump_zero_version_patch():
    v = SemanticVersion(0, 0, 0)
    bumped = v.bump(ReleaseType.PATCH)
    assert str(bumped) == "0.0.1"


# --- VersionService.calculate_next_version ---

@pytest.fixture
def service() -> VersionService:
    return VersionService()


def test_calculate_major(service):
    assert service.calculate_next_version("1.2.3", ReleaseType.MAJOR) == "2.0.0"


def test_calculate_minor(service):
    assert service.calculate_next_version("1.2.3", ReleaseType.MINOR) == "1.3.0"


def test_calculate_patch(service):
    assert service.calculate_next_version("1.2.3", ReleaseType.PATCH) == "1.2.4"


def test_calculate_first_major(service):
    assert service.calculate_next_version(None, ReleaseType.MAJOR) == "1.0.0"


def test_calculate_first_minor(service):
    assert service.calculate_next_version(None, ReleaseType.MINOR) == "0.1.0"


def test_calculate_first_patch(service):
    assert service.calculate_next_version(None, ReleaseType.PATCH) == "0.0.1"


def test_calculate_strips_v_prefix(service):
    assert service.calculate_next_version("v1.2.3", ReleaseType.PATCH) == "1.2.4"


# --- VersionService.update_version_file ---

def test_update_version_file_writes_content(tmp_path, service):
    path = tmp_path / "VERSION"
    service.update_version_file(path, "2.3.4")
    assert path.read_text() == "2.3.4\n"


def test_update_version_file_overwrites(tmp_path, service):
    path = tmp_path / "VERSION"
    path.write_text("1.0.0\n")
    service.update_version_file(path, "2.0.0")
    assert path.read_text() == "2.0.0\n"


# --- VersionService.get_current_version ---

def test_get_current_version(tmp_path, service):
    path = tmp_path / "VERSION"
    path.write_text("3.1.4\n")
    assert service.get_current_version(path) == "3.1.4"


def test_get_current_version_strips_whitespace(tmp_path, service):
    path = tmp_path / "VERSION"
    path.write_text("  2.0.0  \n")
    assert service.get_current_version(path) == "2.0.0"


def test_get_current_version_missing_file(tmp_path, service):
    path = tmp_path / "VERSION"
    assert service.get_current_version(path) is None


def test_get_current_version_empty_file(tmp_path, service):
    path = tmp_path / "VERSION"
    path.write_text("")
    assert service.get_current_version(path) is None
