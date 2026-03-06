import mimetypes
import re
from dataclasses import dataclass
from glob import glob
from pathlib import Path
from typing import Any

import requests

from python_semantic_release.models import (
    Context,
    GitHubConfig,
    Release,
)


@dataclass
class GitHubService:
    token: str
    base_url: str = "https://api.github.com"

    def __post_init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"token {self.token}",
                "Accept": "application/vnd.github.v3+json",
            }
        )

    def _extract_repo_info(self, url: str) -> tuple[str, str]:
        url = url.replace(".git", "")
        if url.startswith("git@github.com:"):
            url = url.replace("git@github.com:", "")
        elif url.startswith("https://github.com/"):
            url = url.replace("https://github.com/", "")

        parts = url.split("/")
        if len(parts) >= 2:
            return parts[0], parts[1]
        raise ValueError(f"Cannot extract repo info from URL: {url}")

    def create_release(
        self,
        repo_url: str,
        tag: str,
        name: str,
        body: str,
        draft: bool = True,
        target_commitish: str | None = None,
    ) -> dict[str, Any]:
        owner, repo = self._extract_repo_info(repo_url)
        url = f"{self.base_url}/repos/{owner}/{repo}/releases"

        data: dict[str, Any] = {
            "tag_name": tag,
            "name": name,
            "body": body,
            "draft": draft,
            "prerelease": False,
        }

        if target_commitish:
            data["target_commitish"] = target_commitish

        response = self.session.post(url, json=data)
        response.raise_for_status()
        return response.json()

    def update_release(
        self, repo_url: str, release_id: int, draft: bool = False
    ) -> dict[str, Any]:
        owner, repo = self._extract_repo_info(repo_url)
        url = f"{self.base_url}/repos/{owner}/{repo}/releases/{release_id}"

        data = {"draft": draft}

        response = self.session.patch(url, json=data)
        response.raise_for_status()
        return response.json()

    def upload_release_asset(
        self,
        upload_url: str,
        asset_path: Path,
        label: str,
    ) -> dict[str, Any]:
        upload_url = upload_url.split("{")[0]

        content_type, _ = mimetypes.guess_type(str(asset_path))
        if not content_type:
            content_type = "application/octet-stream"

        params = {"name": asset_path.name, "label": label}

        with open(asset_path, "rb") as f:
            headers = {
                "Content-Type": content_type,
                "Authorization": f"token {self.token}",
            }
            response = requests.post(
                upload_url,
                params=params,
                data=f,
                headers=headers,
            )
            response.raise_for_status()
            return response.json()

    def get_issues_from_commits(self, commits: list[str]) -> list[int]:
        issue_pattern = re.compile(r"#(\d+)")
        issues = set()

        for commit in commits:
            matches = issue_pattern.findall(commit)
            for match in matches:
                issues.add(int(match))

        return sorted(issues)

    def comment_on_issue(
        self, repo_url: str, issue_number: int, comment: str
    ) -> None:
        owner, repo = self._extract_repo_info(repo_url)
        url = f"{self.base_url}/repos/{owner}/{repo}/issues/{issue_number}/comments"

        data = {"body": comment}

        response = self.session.post(url, json=data)
        response.raise_for_status()

    def add_labels_to_issue(
        self, repo_url: str, issue_number: int, labels: list[str]
    ) -> None:
        if not labels:
            return

        owner, repo = self._extract_repo_info(repo_url)
        url = (
            f"{self.base_url}/repos/{owner}/{repo}/issues/{issue_number}/labels"
        )

        data = {"labels": labels}

        response = self.session.post(url, json=data)
        response.raise_for_status()


@dataclass
class GitHubPlugin:
    config: GitHubConfig
    service: GitHubService

    def __init__(
        self,
        config: GitHubConfig | None = None,
        token: str | None = None,
    ):
        self.config = config or GitHubConfig()
        if token is None:
            import os

            token = os.environ.get("GITHUB_TOKEN")
            if token is None:
                raise ValueError("GITHUB_TOKEN environment variable not set")

        self.service = GitHubService(token=token)

    def verify_conditions(self, context: Context) -> None:
        if not self.service.token:
            raise ValueError("GitHub token is required")

    def publish(self, context: Context) -> Release:
        if not context.next_release:
            raise ValueError("No release to publish")

        release_data = self.service.create_release(
            repo_url=context.options.repository_url,
            tag=context.next_release.git_tag,
            name=context.next_release.version,
            body=context.next_release.notes,
            draft=True,
            target_commitish=context.next_release.git_head,
        )

        release_id = release_data["id"]
        upload_url = release_data["upload_url"]
        html_url = release_data.get("html_url", "")

        self._upload_assets(context, upload_url)

        if not self.config.draft_release:
            updated_release = self.service.update_release(
                context.options.repository_url,
                release_id,
                draft=False,
            )
            html_url = updated_release.get("html_url", html_url)

        context.next_release.url = html_url
        return context.next_release

    def _upload_assets(self, context: Context, upload_url: str) -> None:
        for asset_config in self.config.assets:
            path_pattern = asset_config.get("path", "")
            label = asset_config.get("label", "")

            asset_paths = glob(str(context.cwd / path_pattern))

            for asset_path_str in asset_paths:
                asset_path = Path(asset_path_str)
                if asset_path.exists() and asset_path.is_file():
                    self.service.upload_release_asset(
                        upload_url,
                        asset_path,
                        label,
                    )

    def success(self, context: Context) -> None:
        if not context.next_release or not self.config.success_comment:
            return

        commit_messages = [c.message for c in context.commits]
        issues = self.service.get_issues_from_commits(commit_messages)

        comment = self._render_template(self.config.success_comment, context)

        for issue in issues:
            try:
                self.service.comment_on_issue(
                    context.options.repository_url,
                    issue,
                    comment,
                )

                if self.config.labels:
                    self.service.add_labels_to_issue(
                        context.options.repository_url,
                        issue,
                        self.config.labels,
                    )
            except Exception:
                pass

    def fail(self, context: Context, error: Exception) -> None:
        if not self.config.fail_comment:
            return

    def _render_template(self, template: str, context: Context) -> str:
        replacements = {}
        if context.next_release:
            replacements["${nextRelease.version}"] = (
                context.next_release.version
            )
            replacements["${nextRelease.gitTag}"] = context.next_release.git_tag

        result = template
        for key, value in replacements.items():
            result = result.replace(key, value)

        return result
