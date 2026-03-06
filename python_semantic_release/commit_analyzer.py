from abc import ABC, abstractmethod
from dataclasses import dataclass

from python_semantic_release.commit_parser import ConventionalCommitParser
from python_semantic_release.models import (
    CommitAnalyzerConfig,
    Context,
    ParsedCommit,
    ReleaseRule,
    ReleaseType,
)
from python_semantic_release.protocols import CommitParser

_RELEASE_PRIORITY: dict[ReleaseType, int] = {
    ReleaseType.MAJOR: 3,
    ReleaseType.MINOR: 2,
    ReleaseType.PATCH: 1,
}

_RELEASE_MAP: dict[str, ReleaseType] = {
    "major": ReleaseType.MAJOR,
    "minor": ReleaseType.MINOR,
    "patch": ReleaseType.PATCH,
}


class ReleaseRuleStrategy(ABC):
    def __init__(self, rule: ReleaseRule):
        self.rule = rule

    @abstractmethod
    def matches(self, commit: ParsedCommit) -> bool:
        pass

    def get_release_type(self) -> ReleaseType | None:
        return _RELEASE_MAP.get(self.rule.release) if self.rule.release else None


class TypeReleaseRule(ReleaseRuleStrategy):
    def _scope_matches(self, commit: ParsedCommit) -> bool:
        return self.rule.scope is None or commit.scope == self.rule.scope

    def _breaking_matches(self, commit: ParsedCommit) -> bool:
        return self.rule.breaking is None or commit.breaking == self.rule.breaking

    def _revert_matches(self, commit: ParsedCommit) -> bool:
        return self.rule.revert is None or commit.revert == self.rule.revert

    def matches(self, commit: ParsedCommit) -> bool:
        if self.rule.type is None:
            return False
        return (
            commit.type == self.rule.type
            and self._scope_matches(commit)
            and self._breaking_matches(commit)
            and self._revert_matches(commit)
        )


class BreakingChangeRule(ReleaseRuleStrategy):
    def matches(self, commit: ParsedCommit) -> bool:
        return commit.breaking and self.rule.breaking is True


class RevertRule(ReleaseRuleStrategy):
    def matches(self, commit: ParsedCommit) -> bool:
        return commit.revert and self.rule.revert is True


@dataclass
class ReleaseRuleFactory:
    @staticmethod
    def create_strategy(rule: ReleaseRule) -> ReleaseRuleStrategy:
        if rule.breaking is True and rule.type is None:
            return BreakingChangeRule(rule)
        if rule.revert is True and rule.type is None:
            return RevertRule(rule)
        return TypeReleaseRule(rule)


@dataclass
class CommitAnalyzer:
    config: CommitAnalyzerConfig
    parser: CommitParser

    def __init__(
        self,
        config: CommitAnalyzerConfig | None = None,
        parser: CommitParser | None = None,
    ):
        self.config = config or CommitAnalyzerConfig()
        self.parser = parser or ConventionalCommitParser()
        self.rules = self._initialize_rules()

    def _initialize_rules(self) -> list[ReleaseRuleStrategy]:
        default_rules = [
            ReleaseRule(breaking=True, release="major"),
            ReleaseRule(revert=True, release="patch"),
            ReleaseRule(type="feat", release="minor"),
            ReleaseRule(type="fix", release="patch"),
            ReleaseRule(type="perf", release="patch"),
        ]
        all_rules = self.config.release_rules + default_rules
        return [ReleaseRuleFactory.create_strategy(r) for r in all_rules]

    def _get_release_type_for_commit(
        self, commit: ParsedCommit
    ) -> ReleaseType | None:
        for rule in self.rules:
            if rule.matches(commit):
                return rule.get_release_type()
        return None

    def _higher_priority(
        self, a: ReleaseType, b: ReleaseType
    ) -> ReleaseType:
        return a if _RELEASE_PRIORITY[a] > _RELEASE_PRIORITY[b] else b

    def analyze_commits(self, context: Context) -> ReleaseType | None:
        if not context.commits:
            return None

        highest: ReleaseType | None = None
        for commit in context.commits:
            parsed = self.parser.parse(commit)
            release_type = self._get_release_type_for_commit(parsed)
            if release_type is None:
                continue
            highest = (
                release_type
                if highest is None
                else self._higher_priority(release_type, highest)
            )
        return highest
