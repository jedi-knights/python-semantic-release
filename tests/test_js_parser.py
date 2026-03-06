import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from python_semantic_release.config.js_parser import JSConfigParser


def _parser(tmp_path: Path, content: str = "") -> JSConfigParser:
    path = tmp_path / "release.config.js"
    path.write_text(content)
    return JSConfigParser(path)


# --- _read_js_file ---

def test_read_js_file_returns_content(tmp_path):
    parser = _parser(tmp_path, "module.exports = {};")
    assert "module.exports" in parser._read_js_file()


# --- _execute_js_to_json: CalledProcessError ---

def test_execute_js_raises_value_error_on_process_error(tmp_path):
    parser = _parser(tmp_path)
    err = subprocess.CalledProcessError(1, "node", stderr="syntax error")
    with patch("subprocess.run", side_effect=err):
        with pytest.raises(ValueError, match="Failed to parse JavaScript config"):
            parser._execute_js_to_json("bad js")


# --- _execute_js_to_json: FileNotFoundError → fallback ---

def test_execute_js_falls_back_when_node_missing(tmp_path):
    content = "module.exports = { branches: ['main'] };"
    parser = _parser(tmp_path, content)
    with patch("subprocess.run", side_effect=FileNotFoundError):
        result = parser._execute_js_to_json(content)
    import json
    data = json.loads(result)
    assert data["branches"] == ["main"]


# --- _extract_branches ---

def test_extract_branches_found(tmp_path):
    parser = _parser(tmp_path)
    result = parser._extract_branches("branches: ['main', 'develop']")
    assert result == ["main", "develop"]


def test_extract_branches_not_found(tmp_path):
    parser = _parser(tmp_path)
    assert parser._extract_branches("no branches here") is None


def test_extract_branches_single(tmp_path):
    parser = _parser(tmp_path)
    result = parser._extract_branches('branches: ["release"]')
    assert result == ["release"]


# --- _extract_simple_field ---

def test_extract_simple_field_found(tmp_path):
    parser = _parser(tmp_path)
    result = parser._extract_simple_field(
        "repositoryUrl: 'https://github.com/x/y'",
        r"repositoryUrl:\s*[\"'](.+?)[\"']",
    )
    assert result == "https://github.com/x/y"


def test_extract_simple_field_not_found(tmp_path):
    parser = _parser(tmp_path)
    assert parser._extract_simple_field("nothing", r"missing:\s*[\"'](.+?)[\"']") is None


# --- _parse_rule_release ---

def test_parse_rule_release_false_returns_none(tmp_path):
    parser = _parser(tmp_path)
    assert parser._parse_rule_release("false") is None


def test_parse_rule_release_minor(tmp_path):
    parser = _parser(tmp_path)
    assert parser._parse_rule_release("'minor'") == "minor"


def test_parse_rule_release_major_double_quotes(tmp_path):
    parser = _parser(tmp_path)
    assert parser._parse_rule_release('"major"') == "major"


# --- _extract_release_rules ---

def test_extract_release_rules_found(tmp_path):
    parser = _parser(tmp_path)
    js = "releaseRules: [{ type: 'feat', release: 'minor' }]"
    result = parser._extract_release_rules(js)
    assert result is not None
    assert result[0]["type"] == "feat"
    assert result[0]["release"] == "minor"


def test_extract_release_rules_with_false(tmp_path):
    parser = _parser(tmp_path)
    js = "releaseRules: [{ type: 'docs', release: false }]"
    result = parser._extract_release_rules(js)
    assert result is not None
    assert result[0]["release"] is None


def test_extract_release_rules_not_found(tmp_path):
    parser = _parser(tmp_path)
    assert parser._extract_release_rules("no rules here") is None


def test_extract_release_rules_empty_match(tmp_path):
    parser = _parser(tmp_path)
    assert parser._extract_release_rules("releaseRules: []") is None


# --- _extract_plugins ---

def test_extract_plugins_found(tmp_path):
    parser = _parser(tmp_path)
    js = "plugins: ['@semantic-release/changelog', '@semantic-release/github']"
    result = parser._extract_plugins(js)
    assert result is not None
    assert "changelog" in result
    assert "github" in result


def test_extract_plugins_not_found(tmp_path):
    parser = _parser(tmp_path)
    assert parser._extract_plugins("no plugins") is None


def test_extract_plugins_empty_match(tmp_path):
    parser = _parser(tmp_path)
    assert parser._extract_plugins("plugins: []") is None


# --- _fallback_parse ---

def test_fallback_parse_branches(tmp_path):
    parser = _parser(tmp_path)
    import json
    result = json.loads(parser._fallback_parse("module.exports = { branches: ['main'] };"))
    assert result["branches"] == ["main"]


def test_fallback_parse_simple_fields(tmp_path):
    parser = _parser(tmp_path)
    import json
    js = "module.exports = { repositoryUrl: 'https://github.com/x/y', preset: 'angular' };"
    result = json.loads(parser._fallback_parse(js))
    assert result["repositoryUrl"] == "https://github.com/x/y"
    assert result["preset"] == "angular"


def test_fallback_parse_release_rules(tmp_path):
    parser = _parser(tmp_path)
    import json
    js = "releaseRules: [{ type: 'feat', release: 'minor' }]"
    result = json.loads(parser._fallback_parse(js))
    assert "releaseRules" in result
    assert result["releaseRules"][0]["type"] == "feat"


def test_fallback_parse_plugins(tmp_path):
    parser = _parser(tmp_path)
    import json
    js = "plugins: ['@semantic-release/changelog']"
    result = json.loads(parser._fallback_parse(js))
    assert "plugins" in result


def test_fallback_parse_empty_js(tmp_path):
    parser = _parser(tmp_path)
    import json
    result = json.loads(parser._fallback_parse("module.exports = {};"))
    assert result == {}
