from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from python_semantic_release.git.service import GitService


@pytest.fixture
def service(tmp_path) -> GitService:
    return GitService(cwd=tmp_path)


# --- _parse_commits ---

def test_parse_commits_single(service):
    raw = (
        "abc123\n"
        "Dev One\n"
        "dev@example.com\n"
        "1705312200\n"
        "feat: add feature\n"
        "--END--\n"
    )
    commits = service._parse_commits(raw)
    assert len(commits) == 1
    assert commits[0].hash == "abc123"
    assert commits[0].message == "feat: add feature"
    assert commits[0].author_name == "Dev One"
    assert commits[0].author_email == "dev@example.com"


def test_parse_commits_with_body(service):
    raw = (
        "def456\n"
        "Author\n"
        "a@b.com\n"
        "1705312200\n"
        "fix: resolve bug\n"
        "This is the body\n"
        "--END--\n"
    )
    commits = service._parse_commits(raw)
    assert commits[0].body == "This is the body"


def test_parse_commits_multiple(service):
    raw = (
        "sha1\nA\na@b.com\n1705312200\nfeat: x\n--END--\n"
        "sha2\nB\nb@c.com\n1705312200\nfix: y\n--END--\n"
    )
    commits = service._parse_commits(raw)
    assert len(commits) == 2
    assert commits[0].hash == "sha1"
    assert commits[1].hash == "sha2"


def test_parse_commits_empty_output(service):
    assert service._parse_commits("") == []


def test_parse_commits_skips_short_entries(service):
    raw = "abc\nAuthor\n--END--\n"
    commits = service._parse_commits(raw)
    assert commits == []


def test_parse_commits_date_converted(service):
    ts = 1705312200
    raw = f"sha\nA\na@b.com\n{ts}\nfeat: x\n--END--\n"
    commits = service._parse_commits(raw)
    assert isinstance(commits[0].date, datetime)


# --- get_last_tag ---

def test_get_last_tag_returns_first(service):
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="v2.0.0\nv1.0.0\n", returncode=0)
        tag = service.get_last_tag()
    assert tag == "v2.0.0"


def test_get_last_tag_no_tags(service):
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="", returncode=0)
        tag = service.get_last_tag()
    assert tag is None


def test_get_last_tag_subprocess_error_returns_none(service):
    import subprocess
    with patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, "git")):
        tag = service.get_last_tag()
    assert tag is None


# --- tag_exists ---

def test_tag_exists_true(service):
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="v1.0.0\n")
        assert service.tag_exists("v1.0.0") is True


def test_tag_exists_false(service):
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="")
        assert service.tag_exists("v9.9.9") is False


# --- get_current_branch ---

def test_get_current_branch(service):
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="main\n")
        assert service.get_current_branch() == "main"


# --- get_commit_sha ---

def test_get_commit_sha_head(service):
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="deadbeef\n")
        assert service.get_commit_sha() == "deadbeef"


def test_get_commit_sha_ref(service):
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="abc123\n")
        assert service.get_commit_sha("v1.0.0") == "abc123"


# --- get_repository_url ---

def test_get_repository_url(service):
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            stdout="https://github.com/owner/repo.git\n"
        )
        assert service.get_repository_url() == "https://github.com/owner/repo.git"


# --- get_modified_files ---

def test_get_modified_files(service):
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="CHANGELOG.md\nVERSION\n")
        files = service.get_modified_files()
    assert files == ["CHANGELOG.md", "VERSION"]


def test_get_modified_files_empty(service):
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="")
        files = service.get_modified_files()
    assert files == []


# --- get_commits ---

def test_get_commits_calls_git_log(service):
    raw = "sha1\nAuthor\na@b.com\n1705312200\nfeat: x\n--END--\n"
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout=raw)
        commits = service.get_commits()
    assert len(commits) == 1
    assert commits[0].hash == "sha1"


def test_get_commits_with_from_ref(service):
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="")
        service.get_commits(from_ref="v1.0.0")
    cmd = mock_run.call_args[0][0]
    assert any("v1.0.0" in str(arg) for arg in cmd)


def test_get_commits_empty_returns_empty(service):
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="")
        commits = service.get_commits()
    assert commits == []


# --- create_tag ---

def test_create_tag_runs_git_tag(service):
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock()
        service.create_tag("v1.2.0", "Release 1.2.0")
    cmd = mock_run.call_args[0][0]
    assert "tag" in cmd
    assert "v1.2.0" in cmd


def test_create_tag_force_flag(service):
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock()
        service.create_tag("v1.2.0", "Release", force=True)
    cmd = mock_run.call_args[0][0]
    assert "-f" in cmd


# --- delete_tag ---

def test_delete_tag_local(service):
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock()
        service.delete_tag("v1.0.0")
    cmd = mock_run.call_args[0][0]
    assert "tag" in cmd
    assert "-d" in cmd


def test_delete_tag_with_remote(service):
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock()
        service.delete_tag("v1.0.0", remote=True)
    assert mock_run.call_count == 2
    remote_cmd = mock_run.call_args_list[1][0][0]
    assert "push" in remote_cmd


# --- add_files ---

def test_add_files_runs_git_add(service):
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock()
        service.add_files(["CHANGELOG.md", "VERSION"])
    cmd = mock_run.call_args[0][0]
    assert "add" in cmd
    assert "CHANGELOG.md" in cmd
    assert "VERSION" in cmd


# --- commit ---

def test_commit_runs_git_commit(service):
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock()
        service.commit("chore: release 1.1.0")
    cmd = mock_run.call_args[0][0]
    assert "commit" in cmd
    assert "chore: release 1.1.0" in cmd


# --- push ---

def test_push_default(service):
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock()
        service.push()
    cmd = mock_run.call_args[0][0]
    assert "push" in cmd
    assert "origin" in cmd


def test_push_with_tags(service):
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock()
        service.push(tags=True)
    cmd = mock_run.call_args[0][0]
    assert "--tags" in cmd


def test_push_with_branch(service):
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock()
        service.push(branch="main")
    cmd = mock_run.call_args[0][0]
    assert "main" in cmd
