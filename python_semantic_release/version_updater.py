from dataclasses import dataclass
from pathlib import Path

import toml

from python_semantic_release.models import Context, VersionConfig


@dataclass
class VersionUpdater:
    config: VersionConfig

    def __init__(self, config: VersionConfig | None = None):
        self.config = config or VersionConfig()

    def prepare(self, context: Context) -> None:
        if not context.next_release:
            return

        version = context.next_release.version

        for version_file_spec in self.config.version_files:
            self._update_version_file(context.cwd, version_file_spec, version)

    def _update_version_file(
        self, cwd: Path, version_file_spec: str, version: str
    ) -> None:
        if ":" in version_file_spec:
            file_path, json_path = version_file_spec.split(":", 1)
            self._update_structured_file(cwd, file_path, json_path, version)
        else:
            self._update_plain_file(cwd, version_file_spec, version)

    def _update_plain_file(
        self, cwd: Path, file_path: str, version: str
    ) -> None:
        path = cwd / file_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"{version}\n")

    def _update_structured_file(
        self, cwd: Path, file_path: str, json_path: str, version: str
    ) -> None:
        path = cwd / file_path

        if file_path.endswith(".toml"):
            self._update_toml_file(path, json_path, version)
        else:
            raise ValueError(f"Unsupported structured file format: {file_path}")

    def _update_toml_file(
        self, path: Path, json_path: str, version: str
    ) -> None:
        if not path.exists():
            raise FileNotFoundError(f"TOML file not found: {path}")

        content = toml.load(path)

        keys = json_path.split(".")
        current = content
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]

        current[keys[-1]] = version

        with open(path, "w") as f:
            toml.dump(content, f)
