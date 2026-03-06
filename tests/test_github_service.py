from unittest.mock import MagicMock

import pytest

from python_semantic_release.github_service import GitHubService


@pytest.fixture
def service() -> GitHubService:
    return GitHubService(token="test-token")


# --- _extract_repo_info ---

def test_extract_repo_info_https(service):
    owner, repo = service._extract_repo_info(
        "https://github.com/owner/repo.git"
    )
    assert owner == "owner"
    assert repo == "repo"


def test_extract_repo_info_ssh(service):
    owner, repo = service._extract_repo_info("git@github.com:owner/repo.git")
    assert owner == "owner"
    assert repo == "repo"


def test_extract_repo_info_https_no_git_suffix(service):
    owner, repo = service._extract_repo_info(
        "https://github.com/myorg/myrepo"
    )
    assert owner == "myorg"
    assert repo == "myrepo"


def test_extract_repo_info_invalid_raises(service):
    with pytest.raises(ValueError):
        service._extract_repo_info("not-a-url")


# --- get_issues_from_commits ---

def test_get_issues_from_commits_single(service):
    issues = service.get_issues_from_commits(["Closes #42"])
    assert issues == [42]


def test_get_issues_from_commits_multiple(service):
    issues = service.get_issues_from_commits(["Closes #1", "Fixes #2", "Resolves #3"])
    assert issues == [1, 2, 3]


def test_get_issues_from_commits_deduplicates(service):
    issues = service.get_issues_from_commits(["#5", "#5"])
    assert issues == [5]


def test_get_issues_from_commits_none_found(service):
    issues = service.get_issues_from_commits(["just a regular message"])
    assert issues == []


def test_get_issues_from_commits_sorted(service):
    issues = service.get_issues_from_commits(["#10", "#2", "#5"])
    assert issues == [2, 5, 10]


# --- session headers ---

def test_session_has_auth_header(service):
    assert "Authorization" in service.session.headers
    assert "test-token" in service.session.headers["Authorization"]


def test_session_has_accept_header(service):
    assert "Accept" in service.session.headers


# --- create_release (mocked) ---

def test_create_release_calls_correct_endpoint(service):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "id": 1, "upload_url": "https://uploads/assets{?name}", "html_url": "https://github.com/owner/repo/releases/1"
    }
    mock_resp.raise_for_status = MagicMock()
    service.session.post = MagicMock(return_value=mock_resp)

    result = service.create_release(
        "https://github.com/owner/repo",
        tag="v1.0.0",
        name="1.0.0",
        body="notes",
    )
    assert result["id"] == 1
    call_url = service.session.post.call_args[0][0]
    assert "owner/repo/releases" in call_url


def test_create_release_with_target_commitish(service):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"id": 2, "upload_url": "x", "html_url": "y"}
    mock_resp.raise_for_status = MagicMock()
    service.session.post = MagicMock(return_value=mock_resp)

    service.create_release(
        "https://github.com/owner/repo",
        tag="v1.0.0",
        name="1.0.0",
        body="notes",
        target_commitish="abc123",
    )
    payload = service.session.post.call_args[1]["json"]
    assert payload["target_commitish"] == "abc123"


# --- update_release (mocked) ---

def test_update_release_patches_draft(service):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"id": 1, "html_url": "url"}
    mock_resp.raise_for_status = MagicMock()
    service.session.patch = MagicMock(return_value=mock_resp)

    service.update_release("https://github.com/owner/repo", 1, draft=False)
    payload = service.session.patch.call_args[1]["json"]
    assert payload["draft"] is False


# --- comment_on_issue (mocked) ---

def test_comment_on_issue_posts_to_correct_url(service):
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    service.session.post = MagicMock(return_value=mock_resp)

    service.comment_on_issue("https://github.com/owner/repo", 5, "Great!")
    call_url = service.session.post.call_args[0][0]
    assert "issues/5/comments" in call_url


# --- add_labels_to_issue (mocked) ---

def test_add_labels_skips_empty_list(service):
    service.session.post = MagicMock()
    service.add_labels_to_issue("https://github.com/owner/repo", 1, [])
    service.session.post.assert_not_called()


def test_add_labels_posts_labels(service):
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    service.session.post = MagicMock(return_value=mock_resp)

    service.add_labels_to_issue(
        "https://github.com/owner/repo", 3, ["released"]
    )
    payload = service.session.post.call_args[1]["json"]
    assert "released" in payload["labels"]
