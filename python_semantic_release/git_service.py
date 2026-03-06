import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from python_semantic_release.models import Commit


@dataclass
class GitService:
    cwd: Path

    def get_commits(
        self, from_ref: str | None = None, to_ref: str = "HEAD"
    ) -> list[Commit]:
        range_spec = f"{from_ref}..{to_ref}" if from_ref else to_ref
        format_str = "%H%n%an%n%ae%n%at%n%s%n%b%n--END--"

        result = subprocess.run(
            ["git", "log", range_spec, f"--format={format_str}"],
            cwd=self.cwd,
            capture_output=True,
            text=True,
            check=True,
        )

        return self._parse_commits(result.stdout)

    def _parse_commits(self, output: str) -> list[Commit]:
        commits = []
        raw_commits = output.split("--END--\n")

        for raw in raw_commits:
            if not raw.strip():
                continue

            lines = raw.strip().split("\n")
            if len(lines) < 5:
                continue

            hash_val = lines[0]
            author_name = lines[1]
            author_email = lines[2]
            timestamp = int(lines[3])
            subject = lines[4]
            body = "\n".join(lines[5:]) if len(lines) > 5 else ""

            commits.append(
                Commit(
                    hash=hash_val,
                    message=subject,
                    author_name=author_name,
                    author_email=author_email,
                    date=datetime.fromtimestamp(timestamp),
                    body=body,
                )
            )

        return commits

    def get_last_tag(self, tag_pattern: str = "v*") -> str | None:
        try:
            result = subprocess.run(
                [
                    "git",
                    "tag",
                    "--list",
                    tag_pattern,
                    "--sort=-v:refname",
                ],
                cwd=self.cwd,
                capture_output=True,
                text=True,
                check=True,
            )
            tags = [tag for tag in result.stdout.strip().split("\n") if tag]
            return tags[0] if tags else None
        except subprocess.CalledProcessError:
            return None

    def tag_exists(self, tag: str) -> bool:
        result = subprocess.run(
            ["git", "tag", "-l", tag],
            cwd=self.cwd,
            capture_output=True,
            text=True,
            check=False,
        )
        return bool(result.stdout.strip())

    def delete_tag(self, tag: str, remote: bool = False) -> None:
        subprocess.run(
            ["git", "tag", "-d", tag],
            cwd=self.cwd,
            check=True,
        )
        if remote:
            subprocess.run(
                ["git", "push", "origin", f":refs/tags/{tag}"],
                cwd=self.cwd,
                check=False,
            )

    def create_tag(self, tag: str, message: str, force: bool = False) -> None:
        cmd = ["git", "tag", "-a", tag, "-m", message]
        if force:
            cmd.insert(2, "-f")
        subprocess.run(
            cmd,
            cwd=self.cwd,
            check=True,
        )

    def get_current_branch(self) -> str:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=self.cwd,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()

    def get_commit_sha(self, ref: str = "HEAD") -> str:
        result = subprocess.run(
            ["git", "rev-parse", ref],
            cwd=self.cwd,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()

    def add_files(self, files: list[str]) -> None:
        subprocess.run(
            ["git", "add", *files],
            cwd=self.cwd,
            check=True,
        )

    def commit(self, message: str) -> None:
        subprocess.run(
            ["git", "commit", "-m", message],
            cwd=self.cwd,
            check=True,
        )

    def push(
        self,
        remote: str = "origin",
        branch: str | None = None,
        tags: bool = False,
    ) -> None:
        cmd = ["git", "push", remote]
        if branch:
            cmd.append(branch)
        if tags:
            cmd.append("--tags")

        subprocess.run(cmd, cwd=self.cwd, check=True)

    def get_modified_files(self) -> list[str]:
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD"],
            cwd=self.cwd,
            capture_output=True,
            text=True,
            check=True,
        )
        return [f for f in result.stdout.strip().split("\n") if f]

    def get_repository_url(self) -> str:
        result = subprocess.run(
            ["git", "config", "--get", "remote.origin.url"],
            cwd=self.cwd,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
