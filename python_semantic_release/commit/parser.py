import re
from dataclasses import dataclass
from typing import Any

from python_semantic_release.models import Commit, ParsedCommit


@dataclass
class ConventionalCommitParser:
    header_pattern: re.Pattern[str] = re.compile(
        r"^(?P<type>\w+)"
        r"(?:\((?P<scope>[^\)]+)\))?"
        r"(?P<breaking>!)?"
        r": "
        r"(?P<subject>.+)$"
    )
    breaking_pattern: re.Pattern[str] = re.compile(
        r"^BREAKING[- ]CHANGE:\s*(.+)", re.MULTILINE
    )
    reference_pattern: re.Pattern[str] = re.compile(
        r"(?:close[sd]?|fixe[sd]?|resolve[sd]?)\s+#(\d+)", re.IGNORECASE
    )
    mention_pattern: re.Pattern[str] = re.compile(r"@(\w+)")
    revert_pattern: re.Pattern[str] = re.compile(
        r'^revert:?\s+"?(.+)"?', re.IGNORECASE
    )

    def parse(self, commit: Commit) -> ParsedCommit:
        full_message = f"{commit.message}\n{commit.body}".strip()
        subject = commit.message
        body = commit.body

        is_revert = bool(self.revert_pattern.match(commit.message))
        if is_revert:
            revert_match = self.revert_pattern.match(commit.message)
            if revert_match:
                subject = revert_match.group(1)

        header_match = self.header_pattern.match(subject)

        if header_match:
            type_val = header_match.group("type")
            scope = header_match.group("scope")
            breaking_marker = header_match.group("breaking")
            subject_text = header_match.group("subject")
        else:
            type_val = None
            scope = None
            breaking_marker = None
            subject_text = subject

        breaking = bool(breaking_marker) or bool(
            self.breaking_pattern.search(full_message)
        )

        references = self._extract_references(full_message)
        mentions = self.mention_pattern.findall(full_message)

        return ParsedCommit(
            type=type_val,
            scope=scope,
            subject=subject_text,
            body=body,
            breaking=breaking,
            mentions=mentions,
            references=references,
            revert=is_revert,
            raw_commit=commit,
        )

    def _extract_references(self, message: str) -> list[dict[str, Any]]:
        references = []
        for match in self.reference_pattern.finditer(message):
            references.append(
                {
                    "issue": match.group(1),
                    "action": match.group(0).split()[0].lower(),
                    "raw": match.group(0),
                }
            )
        return references
