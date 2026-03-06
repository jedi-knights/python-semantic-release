from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime

from python_semantic_release.commit_parser import ConventionalCommitParser
from python_semantic_release.models import (
    Context,
    ParsedCommit,
    ReleaseNotesConfig,
)
from python_semantic_release.protocols import CommitParser


@dataclass
class CommitGroup:
    title: str
    commits: list[ParsedCommit]
    priority: int


@dataclass
class ReleaseNotesGenerator:
    config: ReleaseNotesConfig
    parser: CommitParser

    def __init__(
        self,
        config: ReleaseNotesConfig | None = None,
        parser: CommitParser | None = None,
    ):
        self.config = config or ReleaseNotesConfig()
        self.parser = parser or ConventionalCommitParser()

    def generate_notes(self, context: Context) -> str:
        if not context.commits:
            return ""

        parsed_commits = [
            self.parser.parse(commit) for commit in context.commits
        ]
        grouped = self._group_commits(parsed_commits)
        sections = self._format_sections(grouped, context)

        header = self._format_header(context)
        return f"{header}\n\n{sections}"

    def _format_header(self, context: Context) -> str:
        if context.next_release:
            version = context.next_release.version
            date = datetime.now().strftime("%Y-%m-%d")
            return f"## [{version}]({self._get_compare_url(context)}) ({date})"
        return "## Unreleased"

    def _get_compare_url(self, context: Context) -> str:
        if not context.last_release or not context.next_release:
            return ""

        repo_url = self._extract_repo_url(context.options.repository_url)
        if not repo_url:
            return ""

        return f"{repo_url}/compare/{context.last_release.git_tag}...{context.next_release.git_tag}"

    def _extract_repo_url(self, url: str) -> str:
        url = url.replace(".git", "")
        if url.startswith("git@github.com:"):
            url = url.replace("git@github.com:", "https://github.com/")
        elif url.startswith("https://github.com/"):
            pass
        else:
            return ""
        return url.rstrip("/")

    def _group_commits(
        self, commits: list[ParsedCommit]
    ) -> dict[str, CommitGroup]:
        type_config = {
            "feat": CommitGroup("Features", [], 1),
            "fix": CommitGroup("Bug Fixes", [], 2),
            "perf": CommitGroup("Performance Improvements", [], 3),
            "revert": CommitGroup("Reverts", [], 4),
            "docs": CommitGroup("Documentation", [], 5),
            "style": CommitGroup("Styles", [], 6),
            "refactor": CommitGroup("Code Refactoring", [], 7),
            "test": CommitGroup("Tests", [], 8),
            "build": CommitGroup("Build System", [], 9),
            "ci": CommitGroup("Continuous Integration", [], 10),
            "chore": CommitGroup("Chores", [], 11),
        }

        groups: dict[str, CommitGroup] = defaultdict(
            lambda: CommitGroup("Other Changes", [], 100)
        )

        for commit in commits:
            commit_type = commit.type or "other"
            if commit_type in type_config:
                groups[commit_type] = type_config[commit_type]
                groups[commit_type].commits.append(commit)
            else:
                groups["other"].commits.append(commit)

        return {k: v for k, v in groups.items() if v.commits}

    def _format_sections(
        self, groups: dict[str, CommitGroup], context: Context
    ) -> str:
        sorted_groups = sorted(groups.values(), key=lambda g: g.priority)

        sections = []
        for group in sorted_groups:
            section = self._format_section(group, context)
            if section:
                sections.append(section)

        return "\n\n".join(sections)

    def _format_section(self, group: CommitGroup, context: Context) -> str:
        if not group.commits:
            return ""

        lines = [f"### {group.title}\n"]

        for commit in group.commits:
            line = self._format_commit(commit, context)
            lines.append(line)

        return "\n".join(lines)

    def _format_commit(self, commit: ParsedCommit, context: Context) -> str:
        scope_str = f"**{commit.scope}:** " if commit.scope else ""
        breaking_str = "⚠ BREAKING CHANGE: " if commit.breaking else ""

        commit_link = self._get_commit_url(commit.raw_commit.hash, context)
        commit_ref = (
            f"([{commit.raw_commit.hash[:7]}]({commit_link}))"
            if commit_link
            else f"({commit.raw_commit.hash[:7]})"
        )

        issue_links = self._format_issue_references(commit.references, context)

        return f"* {breaking_str}{scope_str}{commit.subject} {commit_ref}{issue_links}"

    def _get_commit_url(self, commit_hash: str, context: Context) -> str:
        repo_url = self._extract_repo_url(context.options.repository_url)
        if not repo_url:
            return ""
        return f"{repo_url}/commit/{commit_hash}"

    def _format_issue_references(
        self, references: list[dict], context: Context
    ) -> str:
        if not references:
            return ""

        repo_url = self._extract_repo_url(context.options.repository_url)
        if not repo_url:
            return ""

        issue_links = []
        for ref in references:
            issue_num = ref["issue"]
            issue_url = f"{repo_url}/issues/{issue_num}"
            issue_links.append(f"[#{issue_num}]({issue_url})")

        return f", closes {', '.join(issue_links)}" if issue_links else ""


@dataclass
class ChangelogService:
    generator: ReleaseNotesGenerator

    def __init__(
        self,
        generator: ReleaseNotesGenerator | None = None,
    ):
        self.generator = generator or ReleaseNotesGenerator()

    def update_changelog(
        self, context: Context, changelog_file: str, title: str
    ) -> None:
        notes = self.generator.generate_notes(context)
        changelog_path = context.cwd / changelog_file

        existing_content = ""
        if changelog_path.exists():
            existing_content = changelog_path.read_text()

            if existing_content.startswith(title):
                existing_content = existing_content[len(title) :].lstrip()

        new_content = (
            f"{title}\n\n{notes}\n\n{existing_content}".rstrip() + "\n"
        )

        changelog_path.write_text(new_content)
