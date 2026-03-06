from datetime import datetime
from pathlib import Path

import pytest

from python_semantic_release.models import (
    Branch,
    Commit,
    Context,
    Options,
    ParsedCommit,
    Release,
)


def make_commit(
    hash: str = "abc123",
    message: str = "feat: add feature",
    body: str = "",
    author_name: str = "Dev",
    author_email: str = "dev@example.com",
    date: datetime | None = None,
) -> Commit:
    return Commit(
        hash=hash,
        message=message,
        author_name=author_name,
        author_email=author_email,
        date=date or datetime(2024, 1, 15, 10, 0),
        body=body,
    )


def make_parsed_commit(
    type: str | None = "feat",
    scope: str | None = None,
    subject: str = "add feature",
    body: str = "",
    breaking: bool = False,
    revert: bool = False,
    mentions: list | None = None,
    references: list | None = None,
    raw_commit: Commit | None = None,
) -> ParsedCommit:
    return ParsedCommit(
        type=type,
        scope=scope,
        subject=subject,
        body=body,
        breaking=breaking,
        revert=revert,
        mentions=mentions or [],
        references=references or [],
        raw_commit=raw_commit or make_commit(),
    )


def make_context(
    tmp_path: Path,
    commits: list[Commit] | None = None,
    last_version: str = "1.0.0",
    repo_url: str = "https://github.com/test/repo",
) -> Context:
    return Context(
        cwd=tmp_path,
        env={},
        branch=Branch(name="main"),
        commits=commits if commits is not None else [make_commit()],
        options=Options(
            repository_url=repo_url,
            tag_format="v${version}",
        ),
        last_release=Release(
            version=last_version,
            git_tag=f"v{last_version}",
            git_head="oldsha",
        ),
    )


@pytest.fixture
def sample_commit() -> Commit:
    return make_commit(
        hash="abc123def456",
        message="feat(parser): add new parsing feature",
        body="This adds a new parsing feature\n\nBREAKING CHANGE: API changed",
    )


@pytest.fixture
def sample_commits() -> list[Commit]:
    return [
        make_commit(hash="abc123", message="feat: add new feature"),
        make_commit(hash="def456", message="fix: resolve bug"),
        make_commit(hash="ghi789", message="docs: update README"),
    ]


@pytest.fixture
def sample_context(tmp_path: Path, sample_commits: list[Commit]) -> Context:
    return make_context(tmp_path, commits=sample_commits)
