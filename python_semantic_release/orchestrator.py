import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

from python_semantic_release.changelog.generator import (
    ChangelogService,
    ReleaseNotesGenerator,
)
from python_semantic_release.commit.analyzer import CommitAnalyzer
from python_semantic_release.git.plugin import GitPlugin
from python_semantic_release.git.service import GitService
from python_semantic_release.github.service import GitHubPlugin
from python_semantic_release.models import (
    Branch,
    ChangelogConfig,
    CommitAnalyzerConfig,
    Context,
    GitConfig,
    GitHubConfig,
    Options,
    Release,
    ReleaseNotesConfig,
    VersionConfig,
)
from python_semantic_release.version.service import VersionService
from python_semantic_release.version.updater import VersionUpdater


@dataclass
class SemanticReleaseConfig:
    commit_analyzer: CommitAnalyzerConfig = field(
        default_factory=CommitAnalyzerConfig
    )
    release_notes: ReleaseNotesConfig = field(
        default_factory=ReleaseNotesConfig
    )
    changelog: ChangelogConfig = field(default_factory=ChangelogConfig)
    github: GitHubConfig = field(default_factory=GitHubConfig)
    git: GitConfig = field(default_factory=GitConfig)
    version: VersionConfig = field(default_factory=VersionConfig)
    options: Options = field(default_factory=Options)


@dataclass
class SemanticReleaseOrchestrator:
    config: SemanticReleaseConfig
    cwd: Path
    git_service: GitService
    commit_analyzer: CommitAnalyzer
    notes_generator: ReleaseNotesGenerator
    changelog_service: ChangelogService
    version_service: VersionService
    version_updater: VersionUpdater
    git_plugin: GitPlugin
    github_plugin: GitHubPlugin | None

    def __init__(
        self,
        config: SemanticReleaseConfig | None = None,
        cwd: Path | None = None,
    ):
        self.config = config or SemanticReleaseConfig()
        self.cwd = cwd or Path.cwd()

        self.git_service = GitService(cwd=self.cwd)
        self.commit_analyzer = CommitAnalyzer(
            config=self.config.commit_analyzer
        )
        self.notes_generator = ReleaseNotesGenerator(
            config=self.config.release_notes
        )
        self.changelog_service = ChangelogService(
            generator=self.notes_generator
        )
        self.version_service = VersionService()
        self.version_updater = VersionUpdater(config=self.config.version)
        self.git_plugin = GitPlugin(
            config=self.config.git, git_service=self.git_service
        )

        if os.environ.get("GITHUB_TOKEN"):
            self.github_plugin = GitHubPlugin(
                config=self.config.github,
                token=os.environ.get("GITHUB_TOKEN"),
            )
        else:
            self.github_plugin = None

    def run(self) -> Release | None:
        context: Context | None = None
        try:
            self._log_step("Building release context")
            context = self._build_context()

            self._log_step("Verifying release conditions")
            self._verify_conditions(context)

            self._log_step("Analyzing commits")
            release_type = self.commit_analyzer.analyze_commits(context)
            if release_type is None:
                self._log_step("No release type determined")
                return None

            self._log_step(f"Calculating next version ({release_type})")
            context = self._calculate_next_release(context, release_type)

            self._log_step("Generating release notes")
            notes = self.notes_generator.generate_notes(context)
            if context.next_release:
                context.next_release.notes = notes

            self._log_step("Preparing release artifacts")
            self._prepare_release(context)

            self._log_step("Publishing release")
            published_release = self._publish_release(context)

            self._log_step("Finalizing release")
            self._handle_success(context)

            return published_release

        except Exception as e:
            self._handle_failure(context, e)
            raise

    def _log_step(self, message: str) -> None:
        print(f"  -> {message}", file=sys.stderr, flush=True)

    def _build_context(self) -> Context:
        branch_name = self.git_service.get_current_branch()
        last_tag = self.git_service.get_last_tag()
        commits = self.git_service.get_commits(from_ref=last_tag)

        last_release = None
        if last_tag:
            version = last_tag.lstrip("v")
            last_release = Release(
                version=version,
                git_tag=last_tag,
                git_head=self.git_service.get_commit_sha(last_tag),
            )

        repo_url = self.git_service.get_repository_url()
        self.config.options.repository_url = repo_url

        return Context(
            cwd=self.cwd,
            env=dict(os.environ),
            branch=Branch(name=branch_name),
            commits=commits,
            options=self.config.options,
            last_release=last_release,
        )

    def _verify_conditions(self, context: Context) -> None:
        if self.github_plugin:
            self.github_plugin.verify_conditions(context)

    def _calculate_next_release(
        self, context: Context, release_type
    ) -> Context:
        current_version = None
        if context.last_release:
            current_version = context.last_release.version

        next_version = self.version_service.calculate_next_version(
            current_version, release_type
        )

        tag_format = context.options.tag_format.replace(
            "${version}", next_version
        )
        git_head = self.git_service.get_commit_sha()

        context.next_release = Release(
            version=next_version,
            git_tag=tag_format,
            git_head=git_head,
            type=release_type,
        )

        return context

    def _prepare_release(self, context: Context) -> None:
        if context.options.dry_run:
            self._log_step("[dry-run] Skipping: version file updates")
            self._log_step("[dry-run] Skipping: changelog update")
            self._log_step("[dry-run] Skipping: git commit, tag, and push")
            return

        self.version_updater.prepare(context)

        self.changelog_service.update_changelog(
            context,
            self.config.changelog.changelog_file,
            self.config.changelog.changelog_title,
        )

        self.git_plugin.prepare(context)

        if context.next_release:
            context.next_release.git_head = self.git_service.get_commit_sha()

        self.git_service.push()

    def _publish_release(self, context: Context) -> Release | None:
        if context.options.dry_run:
            self._log_step("[dry-run] Skipping: GitHub release creation")
            return context.next_release

        if self.github_plugin and context.next_release:
            return self.github_plugin.publish(context)
        return context.next_release

    def _handle_success(self, context: Context) -> None:
        if context.options.dry_run:
            return

        if self.github_plugin:
            self.github_plugin.success(context)

    def _handle_failure(
        self, context: Context | None, error: Exception
    ) -> None:
        if self.github_plugin and context:
            self.github_plugin.fail(context, error)
