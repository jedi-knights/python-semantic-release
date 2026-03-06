import pytest

from python_semantic_release.commit.analyzer import (
    BreakingChangeRule,
    CommitAnalyzer,
    ReleaseRuleFactory,
    RevertRule,
    TypeReleaseRule,
)
from python_semantic_release.models import (
    CommitAnalyzerConfig,
    ReleaseRule,
    ReleaseType,
)
from tests.conftest import make_commit, make_context, make_parsed_commit

# --- TypeReleaseRule ---

def test_type_rule_matches_by_type():
    rule = TypeReleaseRule(ReleaseRule(type="feat", release="minor"))
    assert rule.matches(make_parsed_commit(type="feat")) is True


def test_type_rule_no_match_wrong_type():
    rule = TypeReleaseRule(ReleaseRule(type="feat", release="minor"))
    assert rule.matches(make_parsed_commit(type="fix")) is False


def test_type_rule_none_type_never_matches():
    rule = TypeReleaseRule(ReleaseRule(type=None, release="minor"))
    assert rule.matches(make_parsed_commit(type="feat")) is False


def test_type_rule_scope_filter_matches():
    rule = TypeReleaseRule(ReleaseRule(type="feat", scope="api", release="minor"))
    assert rule.matches(make_parsed_commit(type="feat", scope="api")) is True


def test_type_rule_scope_filter_excludes():
    rule = TypeReleaseRule(ReleaseRule(type="feat", scope="api", release="minor"))
    assert rule.matches(make_parsed_commit(type="feat", scope="db")) is False


def test_type_rule_scope_none_matches_any_scope():
    rule = TypeReleaseRule(ReleaseRule(type="feat", release="minor"))
    assert rule.matches(make_parsed_commit(type="feat", scope="anything")) is True


def test_type_rule_breaking_filter_true():
    rule = TypeReleaseRule(ReleaseRule(type="feat", breaking=True, release="major"))
    assert rule.matches(make_parsed_commit(type="feat", breaking=True)) is True
    assert rule.matches(make_parsed_commit(type="feat", breaking=False)) is False


def test_type_rule_breaking_filter_false():
    rule = TypeReleaseRule(ReleaseRule(type="fix", breaking=False, release="patch"))
    assert rule.matches(make_parsed_commit(type="fix", breaking=False)) is True
    assert rule.matches(make_parsed_commit(type="fix", breaking=True)) is False


def test_type_rule_revert_filter():
    rule = TypeReleaseRule(ReleaseRule(type="revert", revert=True, release="patch"))
    assert rule.matches(make_parsed_commit(type="revert", revert=True)) is True
    assert rule.matches(make_parsed_commit(type="revert", revert=False)) is False


def test_type_rule_get_release_type_minor():
    rule = TypeReleaseRule(ReleaseRule(type="feat", release="minor"))
    assert rule.get_release_type() == ReleaseType.MINOR


def test_type_rule_get_release_type_major():
    rule = TypeReleaseRule(ReleaseRule(type="feat", release="major"))
    assert rule.get_release_type() == ReleaseType.MAJOR


def test_type_rule_get_release_type_patch():
    rule = TypeReleaseRule(ReleaseRule(type="fix", release="patch"))
    assert rule.get_release_type() == ReleaseType.PATCH


def test_type_rule_get_release_type_none():
    rule = TypeReleaseRule(ReleaseRule(type="chore", release=None))
    assert rule.get_release_type() is None


# --- BreakingChangeRule ---

def test_breaking_rule_matches_breaking_commit():
    rule = BreakingChangeRule(ReleaseRule(breaking=True, release="major"))
    assert rule.matches(make_parsed_commit(breaking=True)) is True


def test_breaking_rule_no_match_non_breaking():
    rule = BreakingChangeRule(ReleaseRule(breaking=True, release="major"))
    assert rule.matches(make_parsed_commit(breaking=False)) is False


# --- RevertRule ---

def test_revert_rule_matches_revert_commit():
    rule = RevertRule(ReleaseRule(revert=True, release="patch"))
    assert rule.matches(make_parsed_commit(revert=True)) is True


def test_revert_rule_no_match_non_revert():
    rule = RevertRule(ReleaseRule(revert=True, release="patch"))
    assert rule.matches(make_parsed_commit(revert=False)) is False


# --- ReleaseRuleFactory ---

def test_factory_creates_breaking_rule():
    rule = ReleaseRuleFactory.create_strategy(
        ReleaseRule(breaking=True, release="major")
    )
    assert isinstance(rule, BreakingChangeRule)


def test_factory_creates_revert_rule():
    rule = ReleaseRuleFactory.create_strategy(
        ReleaseRule(revert=True, release="patch")
    )
    assert isinstance(rule, RevertRule)


def test_factory_creates_type_rule():
    rule = ReleaseRuleFactory.create_strategy(
        ReleaseRule(type="feat", release="minor")
    )
    assert isinstance(rule, TypeReleaseRule)


def test_factory_type_with_breaking_creates_type_rule():
    # breaking=True but type is set → TypeReleaseRule (not BreakingChangeRule)
    rule = ReleaseRuleFactory.create_strategy(
        ReleaseRule(type="feat", breaking=True, release="major")
    )
    assert isinstance(rule, TypeReleaseRule)


# --- CommitAnalyzer ---

@pytest.fixture
def analyzer() -> CommitAnalyzer:
    return CommitAnalyzer()


def test_analyze_empty_commits_returns_none(tmp_path, analyzer):
    ctx = make_context(tmp_path, commits=[])
    assert analyzer.analyze_commits(ctx) is None


def test_analyze_feat_returns_minor(tmp_path, analyzer):
    ctx = make_context(tmp_path, commits=[make_commit(message="feat: add x")])
    assert analyzer.analyze_commits(ctx) == ReleaseType.MINOR


def test_analyze_fix_returns_patch(tmp_path, analyzer):
    ctx = make_context(tmp_path, commits=[make_commit(message="fix: patch y")])
    assert analyzer.analyze_commits(ctx) == ReleaseType.PATCH


def test_analyze_perf_returns_patch(tmp_path, analyzer):
    ctx = make_context(tmp_path, commits=[make_commit(message="perf: faster")])
    assert analyzer.analyze_commits(ctx) == ReleaseType.PATCH


def test_analyze_breaking_body_returns_major(tmp_path, analyzer):
    ctx = make_context(
        tmp_path,
        commits=[
            make_commit(
                message="feat: new",
                body="BREAKING CHANGE: changed API",
            )
        ],
    )
    assert analyzer.analyze_commits(ctx) == ReleaseType.MAJOR


def test_analyze_breaking_exclamation_returns_major(tmp_path, analyzer):
    ctx = make_context(tmp_path, commits=[make_commit(message="feat!: breaking")])
    assert analyzer.analyze_commits(ctx) == ReleaseType.MAJOR


def test_analyze_chore_returns_none(tmp_path, analyzer):
    ctx = make_context(tmp_path, commits=[make_commit(message="chore: update")])
    assert analyzer.analyze_commits(ctx) is None


def test_analyze_docs_returns_none(tmp_path, analyzer):
    ctx = make_context(tmp_path, commits=[make_commit(message="docs: update")])
    assert analyzer.analyze_commits(ctx) is None


def test_analyze_highest_type_wins(tmp_path, analyzer):
    ctx = make_context(
        tmp_path,
        commits=[
            make_commit(message="fix: small fix"),
            make_commit(message="feat: new feature"),
        ],
    )
    assert analyzer.analyze_commits(ctx) == ReleaseType.MINOR


def test_analyze_major_beats_minor(tmp_path, analyzer):
    ctx = make_context(
        tmp_path,
        commits=[
            make_commit(message="feat: add stuff"),
            make_commit(message="feat!: breaking change"),
        ],
    )
    assert analyzer.analyze_commits(ctx) == ReleaseType.MAJOR


def test_analyze_custom_rules_prepended(tmp_path):
    config = CommitAnalyzerConfig(
        release_rules=[ReleaseRule(type="docs", release="patch")]
    )
    analyzer = CommitAnalyzer(config=config)
    ctx = make_context(tmp_path, commits=[make_commit(message="docs: update")])
    assert analyzer.analyze_commits(ctx) == ReleaseType.PATCH


def test_analyze_custom_rule_none_suppresses_commit(tmp_path):
    config = CommitAnalyzerConfig(
        release_rules=[ReleaseRule(type="feat", release=None)]
    )
    analyzer = CommitAnalyzer(config=config)
    ctx = make_context(tmp_path, commits=[make_commit(message="feat: add")])
    # custom feat→None rule fires first; since it matches, no further rules
    # are checked for this commit. release=None means no bump.
    assert analyzer.analyze_commits(ctx) is None


def test_analyze_revert_returns_patch(tmp_path, analyzer):
    ctx = make_context(
        tmp_path,
        commits=[make_commit(message='revert: "feat: something"')],
    )
    assert analyzer.analyze_commits(ctx) == ReleaseType.PATCH


def test_analyze_non_conventional_returns_none(tmp_path, analyzer):
    ctx = make_context(
        tmp_path, commits=[make_commit(message="just a regular commit")]
    )
    assert analyzer.analyze_commits(ctx) is None
