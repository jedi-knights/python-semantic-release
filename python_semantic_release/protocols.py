from typing import Protocol

from python_semantic_release.models import (
    Commit,
    Context,
    ParsedCommit,
    Release,
    ReleaseType,
)


class CommitParser(Protocol):
    def parse(self, commit: Commit) -> ParsedCommit: ...


class SemanticReleasePlugin(Protocol):
    def verify_conditions(self, context: Context) -> None: ...

    def analyze_commits(self, context: Context) -> ReleaseType | None: ...

    def verify_release(self, context: Context) -> None: ...

    def generate_notes(self, context: Context) -> str: ...

    def prepare(self, context: Context) -> None: ...

    def publish(self, context: Context) -> Release: ...

    def success(self, context: Context) -> None: ...

    def fail(self, context: Context, error: Exception) -> None: ...


class CommitAnalyzerPlugin(Protocol):
    def analyze_commits(self, context: Context) -> ReleaseType | None: ...


class ReleaseNotesPlugin(Protocol):
    def generate_notes(self, context: Context) -> str: ...


class ChangelogPlugin(Protocol):
    def prepare(self, context: Context) -> None: ...


class GitHubPlugin(Protocol):
    def verify_conditions(self, context: Context) -> None: ...

    def publish(self, context: Context) -> Release: ...

    def success(self, context: Context) -> None: ...

    def fail(self, context: Context, error: Exception) -> None: ...


class GitPlugin(Protocol):
    def prepare(self, context: Context) -> None: ...


class VersionPlugin(Protocol):
    def prepare(self, context: Context) -> None: ...
