import json
import re
from pathlib import Path
from typing import Any


class JSConfigParser:
    def __init__(self, config_path: Path):
        self.config_path = config_path

    def parse(self) -> dict[str, Any]:
        js_code = self._read_js_file()
        return json.loads(self._fallback_parse(js_code))

    def _read_js_file(self) -> str:
        with open(self.config_path) as f:
            return f.read()

    # --- regex parsing helpers ---

    def _extract_branches(self, js_code: str) -> list[str] | None:
        match = re.search(r"branches:\s*\[(.*?)\]", js_code, re.DOTALL)
        if not match:
            return None
        return [
            b.strip().strip('"').strip("'")
            for b in match.group(1).split(",")
            if b.strip()
        ]

    def _extract_simple_field(self, js_code: str, pattern: str) -> str | None:
        match = re.search(pattern, js_code)
        return match.group(1) if match else None

    def _parse_rule_release(self, raw: str) -> str | None:
        if raw == "false":
            return None
        return raw.strip('"').strip("'")

    def _extract_release_rules(
        self, js_code: str
    ) -> list[dict[str, Any]] | None:
        match = re.search(r"releaseRules:\s*\[(.*?)\]", js_code, re.DOTALL)
        if not match:
            return None
        pattern = (
            r'\{\s*type:\s*["\'](\w+)["\']'
            r',\s*release:\s*(false|["\'](?:major|minor|patch)["\'])\s*\}'
        )
        rules = [
            {
                "type": m.group(1),
                "release": self._parse_rule_release(m.group(2)),
            }
            for m in re.finditer(pattern, match.group(1))
        ]
        return rules or None

    def _extract_plugins(self, js_code: str) -> list[str] | None:
        match = re.search(r"plugins:\s*\[(.*?)\]", js_code, re.DOTALL)
        if not match:
            return None
        plugins = re.findall(
            r'["\']@semantic-release/([\w-]+)["\']', match.group(1)
        )
        return plugins or None

    _SIMPLE_FIELDS = [
        ("repositoryUrl", r'repositoryUrl:\s*["\'](.+?)["\']'),
        ("tagFormat", r'tagFormat:\s*["\'](.+?)["\']'),
        ("changelogFile", r'changelogFile:\s*["\'](.+?)["\']'),
        ("commitMessage", r'commitMessage:\s*["\'](.+?)["\']'),
        ("preset", r'preset:\s*["\'](.+?)["\']'),
    ]

    def _fallback_parse(self, js_code: str) -> str:
        config: dict[str, Any] = {}

        branches = self._extract_branches(js_code)
        if branches:
            config["branches"] = branches

        for key, pattern in self._SIMPLE_FIELDS:
            value = self._extract_simple_field(js_code, pattern)
            if value:
                config[key] = value

        rules = self._extract_release_rules(js_code)
        if rules:
            config["releaseRules"] = rules

        plugins = self._extract_plugins(js_code)
        if plugins:
            config["plugins"] = plugins

        return json.dumps(config, indent=2)
