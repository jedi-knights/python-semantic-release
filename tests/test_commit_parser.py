import pytest

from python_semantic_release.commit.parser import ConventionalCommitParser
from tests.conftest import make_commit


@pytest.fixture
def parser() -> ConventionalCommitParser:
    return ConventionalCommitParser()


def test_parse_feat_with_scope(parser):
    result = parser.parse(make_commit(message="feat(api): add endpoint"))
    assert result.type == "feat"
    assert result.scope == "api"
    assert result.subject == "add endpoint"
    assert result.breaking is False
    assert result.revert is False


def test_parse_fix_no_scope(parser):
    result = parser.parse(make_commit(message="fix: resolve null pointer bug"))
    assert result.type == "fix"
    assert result.scope is None
    assert result.subject == "resolve null pointer bug"


def test_parse_chore(parser):
    result = parser.parse(make_commit(message="chore: update deps"))
    assert result.type == "chore"
    assert result.breaking is False


def test_parse_breaking_exclamation_mark(parser):
    result = parser.parse(make_commit(message="feat!: redesign API"))
    assert result.type == "feat"
    assert result.breaking is True


def test_parse_breaking_exclamation_with_scope(parser):
    result = parser.parse(make_commit(message="feat(api)!: remove endpoint"))
    assert result.type == "feat"
    assert result.scope == "api"
    assert result.breaking is True


def test_parse_breaking_change_in_body(parser):
    result = parser.parse(
        make_commit(
            message="feat: new feature",
            body="BREAKING CHANGE: This breaks the API",
        )
    )
    assert result.breaking is True


def test_parse_breaking_change_hyphen_variant(parser):
    result = parser.parse(
        make_commit(
            message="fix: update handler",
            body="BREAKING-CHANGE: handler signature changed",
        )
    )
    assert result.breaking is True


def test_parse_breaking_exclamation_and_body(parser):
    result = parser.parse(
        make_commit(
            message="feat!: new thing",
            body="BREAKING CHANGE: details",
        )
    )
    assert result.breaking is True


def test_parse_non_breaking_has_false(parser):
    result = parser.parse(
        make_commit(message="fix: small fix", body="no breaking")
    )
    assert result.breaking is False


def test_parse_revert_commit(parser):
    result = parser.parse(make_commit(message='revert: "feat: add feature"'))
    assert result.revert is True


def test_parse_revert_colon_variant(parser):
    result = parser.parse(make_commit(message="revert: feat: add feature"))
    assert result.revert is True


def test_parse_non_revert_is_false(parser):
    result = parser.parse(make_commit(message="feat: add something"))
    assert result.revert is False


def test_parse_references_closes(parser):
    result = parser.parse(
        make_commit(message="fix: resolve issue", body="Closes #123")
    )
    assert len(result.references) == 1
    assert result.references[0]["issue"] == "123"


def test_parse_references_fixes(parser):
    result = parser.parse(make_commit(message="fix: patch", body="Fixes #456"))
    assert result.references[0]["issue"] == "456"


def test_parse_references_resolves(parser):
    result = parser.parse(
        make_commit(message="fix: patch", body="Resolves #789")
    )
    assert result.references[0]["issue"] == "789"


def test_parse_multiple_references(parser):
    result = parser.parse(
        make_commit(
            message="fix: resolve issue", body="Closes #123\nFixes #456"
        )
    )
    assert len(result.references) == 2
    issues = {r["issue"] for r in result.references}
    assert issues == {"123", "456"}


def test_parse_mentions(parser):
    result = parser.parse(
        make_commit(
            message="feat: new feature",
            body="Thanks @contributor1 and @contributor2",
        )
    )
    assert "contributor1" in result.mentions
    assert "contributor2" in result.mentions


def test_parse_no_mentions(parser):
    result = parser.parse(make_commit(message="fix: no one to thank"))
    assert result.mentions == []


def test_parse_non_conventional_commit(parser):
    result = parser.parse(make_commit(message="just a regular commit message"))
    assert result.type is None
    assert result.scope is None
    assert result.subject == "just a regular commit message"
    assert result.breaking is False


def test_parse_raw_commit_preserved(parser):
    commit = make_commit(hash="deadbeef", message="feat: something")
    result = parser.parse(commit)
    assert result.raw_commit is commit


def test_parse_empty_body_no_references(parser):
    result = parser.parse(make_commit(message="fix: something", body=""))
    assert result.references == []
    assert result.mentions == []


def test_reference_action_field(parser):
    result = parser.parse(
        make_commit(message="fix: resolve", body="Closes #10")
    )
    assert result.references[0]["action"] == "closes"
    assert result.references[0]["raw"].startswith("Closes")


def test_parse_perf_commit(parser):
    result = parser.parse(make_commit(message="perf(db): speed up query"))
    assert result.type == "perf"
    assert result.scope == "db"
