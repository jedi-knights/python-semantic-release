import re
from dataclasses import dataclass
from pathlib import Path

from python_semantic_release.models import ReleaseType


@dataclass
class SemanticVersion:
    major: int
    minor: int
    patch: int
    prerelease: str | None = None
    build_metadata: str | None = None

    def __str__(self) -> str:
        version = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease:
            version += f"-{self.prerelease}"
        if self.build_metadata:
            version += f"+{self.build_metadata}"
        return version

    @classmethod
    def parse(cls, version_str: str) -> "SemanticVersion":
        pattern = re.compile(
            r"^v?(?P<major>\d+)"
            r"\.(?P<minor>\d+)"
            r"\.(?P<patch>\d+)"
            r"(?:-(?P<prerelease>[0-9A-Za-z\-\.]+))?"
            r"(?:\+(?P<build>[0-9A-Za-z\-\.]+))?$"
        )

        match = pattern.match(version_str)
        if not match:
            raise ValueError(f"Invalid semantic version: {version_str}")

        return cls(
            major=int(match.group("major")),
            minor=int(match.group("minor")),
            patch=int(match.group("patch")),
            prerelease=match.group("prerelease"),
            build_metadata=match.group("build"),
        )

    def bump(self, release_type: ReleaseType) -> "SemanticVersion":
        if release_type == ReleaseType.MAJOR:
            return SemanticVersion(
                major=self.major + 1,
                minor=0,
                patch=0,
            )
        elif release_type == ReleaseType.MINOR:
            return SemanticVersion(
                major=self.major,
                minor=self.minor + 1,
                patch=0,
            )
        elif release_type == ReleaseType.PATCH:
            return SemanticVersion(
                major=self.major,
                minor=self.minor,
                patch=self.patch + 1,
            )
        else:
            raise ValueError(f"Unknown release type: {release_type}")


@dataclass
class VersionService:
    def get_current_version(self, version_file: Path) -> str | None:
        if not version_file.exists():
            return None

        content = version_file.read_text().strip()
        return content if content else None

    def update_version_file(self, version_file: Path, version: str) -> None:
        version_file.write_text(f"{version}\n")

    def update_pyproject_toml(self, pyproject_path: Path, version: str) -> None:
        import toml

        content = toml.load(pyproject_path)
        content["project"]["version"] = version

        with open(pyproject_path, "w") as f:
            toml.dump(content, f)

    def calculate_next_version(
        self, current_version: str | None, release_type: ReleaseType
    ) -> str:
        if current_version is None:
            if release_type == ReleaseType.MAJOR:
                return "1.0.0"
            elif release_type == ReleaseType.MINOR:
                return "0.1.0"
            else:
                return "0.0.1"

        current = SemanticVersion.parse(current_version)
        next_version = current.bump(release_type)
        return str(next_version)
