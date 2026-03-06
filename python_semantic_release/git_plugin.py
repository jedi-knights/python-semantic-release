from dataclasses import dataclass
from fnmatch import fnmatch

from python_semantic_release.git_service import GitService
from python_semantic_release.models import Context, GitConfig


@dataclass
class GitPlugin:
    config: GitConfig
    git_service: GitService | None

    def __init__(
        self,
        config: GitConfig | None = None,
        git_service: GitService | None = None,
    ):
        self.config = config or GitConfig()
        self.git_service = git_service

    def prepare(self, context: Context) -> None:
        if not context.next_release:
            return

        if self.git_service is None:
            self.git_service = GitService(cwd=context.cwd)

        modified_files = self.git_service.get_modified_files()
        files_to_commit = self._match_assets(modified_files, self.config.assets)

        if not files_to_commit:
            return

        self.git_service.add_files(files_to_commit)

        commit_message = self._render_message(context)
        self.git_service.commit(commit_message)

    def _match_assets(
        self, modified_files: list[str], asset_patterns: list[str]
    ) -> list[str]:
        matched_files = set()

        for pattern in asset_patterns:
            for file in modified_files:
                if fnmatch(file, pattern):
                    matched_files.add(file)

        return sorted(matched_files)

    def _render_message(self, context: Context) -> str:
        if not context.next_release:
            return ""

        message = self.config.message
        message = message.replace(
            "${nextRelease.version}", context.next_release.version
        )
        message = message.replace(
            "${nextRelease.notes}", context.next_release.notes
        )
        message = message.replace(
            "${nextRelease.gitTag}", context.next_release.git_tag
        )

        return message
