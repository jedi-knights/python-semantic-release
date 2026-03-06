from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from python_semantic_release.cli import (
    _default_config,
    _format_note_line,
    _load_config,
    _write_github_output,
    release,
)
from python_semantic_release.models import Release, ReleaseType
from python_semantic_release.orchestrator import SemanticReleaseConfig


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


# --- _default_config ---


def test_default_config_has_rules():
    config = _default_config()
    assert len(config.commit_analyzer.release_rules) > 0


def test_default_config_has_feat_rule():
    config = _default_config()
    types = [r.type for r in config.commit_analyzer.release_rules]
    assert "feat" in types


def test_default_config_has_fix_rule():
    config = _default_config()
    types = [r.type for r in config.commit_analyzer.release_rules]
    assert "fix" in types


# --- _load_config ---


def test_load_config_explicit_path(tmp_path):
    from ruamel.yaml import YAML

    cfg = tmp_path / ".releaserc.yaml"
    YAML().dump({"options": {"branches": ["release"]}}, cfg.open("w"))
    config = _load_config(cfg)
    assert config.options.branches == ["release"]


def test_load_config_auto_discovers_releaserc(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from ruamel.yaml import YAML

    cfg = tmp_path / ".releaserc.yaml"
    YAML().dump({"options": {"branches": ["develop"]}}, cfg.open("w"))
    config = _load_config(None)
    assert config.options.branches == ["develop"]


def test_load_config_falls_back_to_default_when_no_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config = _load_config(None)
    assert isinstance(config, SemanticReleaseConfig)
    assert len(config.commit_analyzer.release_rules) > 0


# --- _format_note_line ---


def test_format_note_line_feat_bullet():
    assert _format_note_line("* feat: add thing") == "    * feat: add thing"


def test_format_note_line_section_header():
    # Lines starting with # are filtered out (treated as markdown headings)
    result = _format_note_line("### Features")
    assert result is None


def test_format_note_line_plain_text():
    result = _format_note_line("some text")
    assert result == "    some text"


def test_format_note_line_empty_returns_none():
    assert _format_note_line("") is None


def test_format_note_line_whitespace_only_returns_none():
    assert _format_note_line("   ") is None


def test_format_note_line_hash_comment_returns_none():
    assert _format_note_line("## [1.0.0]") is None


# --- _write_github_output ---


def test_write_github_output_true(tmp_path):
    out = tmp_path / "output"
    out.write_text("")
    _write_github_output(str(out), True)
    assert "version_changed=true" in out.read_text()


def test_write_github_output_false(tmp_path):
    out = tmp_path / "output"
    out.write_text("")
    _write_github_output(str(out), False)
    assert "version_changed=false" in out.read_text()


def test_write_github_output_none_path_is_noop():
    _write_github_output(None, True)  # should not raise


def test_write_github_output_appends(tmp_path):
    out = tmp_path / "output"
    out.write_text("existing=data\n")
    _write_github_output(str(out), True)
    content = out.read_text()
    assert "existing=data" in content
    assert "version_changed=true" in content


# --- CLI: run command ---


def _make_mock_orchestrator(result=None):
    orch = MagicMock()
    orch.run.return_value = result
    orch.git_service.get_last_tag.return_value = "v1.0.0"
    return orch


def test_run_command_no_release(runner, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    mock_orch = _make_mock_orchestrator(result=None)
    with patch(
        "python_semantic_release.cli.SemanticReleaseOrchestrator",
        return_value=mock_orch,
    ):
        result = runner.invoke(release, ["run", "--no-ci"])
    assert result.exit_code == 0
    assert "No Release Needed" in result.output


def test_run_command_with_release(runner, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    mock_release = Release(
        version="1.1.0",
        git_tag="v1.1.0",
        git_head="newsha",
        type=ReleaseType.MINOR,
        notes="## [1.1.0]\n\n### Features\n\n* add thing",
    )
    mock_orch = _make_mock_orchestrator(result=mock_release)
    with patch(
        "python_semantic_release.cli.SemanticReleaseOrchestrator",
        return_value=mock_orch,
    ):
        result = runner.invoke(release, ["run", "--no-ci"])
    assert result.exit_code == 0
    assert "Release Published" in result.output
    assert "1.1.0" in result.output


def test_run_command_dry_run_flag(runner, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    mock_orch = _make_mock_orchestrator(result=None)
    captured_config = {}

    def capture_orch(config, cwd):
        captured_config["dry_run"] = config.options.dry_run
        return mock_orch

    with patch(
        "python_semantic_release.cli.SemanticReleaseOrchestrator",
        side_effect=capture_orch,
    ):
        runner.invoke(release, ["run", "--dry-run", "--no-ci"])
    assert captured_config["dry_run"] is True


def test_run_command_exception_exits_nonzero(runner, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    mock_orch = MagicMock()
    mock_orch.run.side_effect = RuntimeError("something went wrong")
    with patch(
        "python_semantic_release.cli.SemanticReleaseOrchestrator",
        return_value=mock_orch,
    ):
        result = runner.invoke(release, ["run", "--no-ci"])
    assert result.exit_code != 0


def test_run_command_writes_github_output_true(runner, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    output_file = tmp_path / "github_output"
    output_file.write_text("")
    monkeypatch.setenv("GITHUB_OUTPUT", str(output_file))
    mock_release = Release(
        version="2.0.0",
        git_tag="v2.0.0",
        git_head="sha",
        type=ReleaseType.MAJOR,
    )
    mock_orch = _make_mock_orchestrator(result=mock_release)
    with patch(
        "python_semantic_release.cli.SemanticReleaseOrchestrator",
        return_value=mock_orch,
    ):
        runner.invoke(release, ["run", "--no-ci"])
    assert "version_changed=true" in output_file.read_text()


def test_run_command_writes_github_output_false(runner, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    output_file = tmp_path / "github_output"
    output_file.write_text("")
    monkeypatch.setenv("GITHUB_OUTPUT", str(output_file))
    mock_orch = _make_mock_orchestrator(result=None)
    with patch(
        "python_semantic_release.cli.SemanticReleaseOrchestrator",
        return_value=mock_orch,
    ):
        runner.invoke(release, ["run", "--no-ci"])
    assert "version_changed=false" in output_file.read_text()


def test_run_version_bump_yes_shown(runner, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    mock_release = Release(
        version="1.1.0",
        git_tag="v1.1.0",
        git_head="sha",
        type=ReleaseType.PATCH,
    )
    mock_orch = _make_mock_orchestrator(result=mock_release)
    with patch(
        "python_semantic_release.cli.SemanticReleaseOrchestrator",
        return_value=mock_orch,
    ):
        result = runner.invoke(release, ["run", "--no-ci"])
    assert "Version bump: YES" in result.output


def test_run_version_bump_no_shown(runner, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    mock_orch = _make_mock_orchestrator(result=None)
    with patch(
        "python_semantic_release.cli.SemanticReleaseOrchestrator",
        return_value=mock_orch,
    ):
        result = runner.invoke(release, ["run", "--no-ci"])
    assert "Version bump: NO" in result.output


# --- CLI: convert command ---


def test_convert_command_succeeds(runner, tmp_path):
    js_file = tmp_path / "release.config.js"
    js_file.write_text("module.exports = { branches: ['main'] };")
    out_file = tmp_path / ".releaserc.yaml"
    result = runner.invoke(
        release,
        ["convert", "--input", str(js_file), "--output", str(out_file)],
    )
    assert result.exit_code == 0
    assert "Successfully converted" in result.output
    assert out_file.exists()


def test_convert_command_invalid_input_fails(runner, tmp_path):
    result = runner.invoke(
        release,
        ["convert", "--input", str(tmp_path / "nonexistent.js")],
    )
    assert result.exit_code != 0


def test_convert_command_with_release_rules(runner, tmp_path):
    js_file = tmp_path / "release.config.js"
    js_file.write_text(
        "module.exports = { branches: ['main'], releaseRules: [{ type: 'docs', release: 'patch' }] };"
    )
    out_file = tmp_path / ".releaserc.yaml"
    result = runner.invoke(
        release,
        ["convert", "--input", str(js_file), "--output", str(out_file)],
    )
    assert result.exit_code == 0
    assert "Release Rules" in result.output


def test_convert_command_exception_shows_error(runner, tmp_path):
    js_file = tmp_path / "release.config.js"
    js_file.write_text("module.exports = {};")
    with patch(
        "python_semantic_release.cli.ConfigConverter.convert_js_to_yaml",
        side_effect=RuntimeError("parse failed"),
    ):
        result = runner.invoke(
            release,
            ["convert", "--input", str(js_file)],
        )
    assert result.exit_code != 0
    assert "parse failed" in result.output


def test_run_initial_release_message(runner, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    mock_release = Release(
        version="0.1.0",
        git_tag="v0.1.0",
        git_head="sha",
        type=ReleaseType.MINOR,
    )
    mock_orch = _make_mock_orchestrator(result=mock_release)
    mock_orch.git_service.get_last_tag.return_value = None
    with patch(
        "python_semantic_release.cli.SemanticReleaseOrchestrator",
        return_value=mock_orch,
    ):
        result = runner.invoke(release, ["run", "--no-ci"])
    assert "initial release" in result.output


def test_run_release_with_url(runner, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    mock_release = Release(
        version="1.1.0",
        git_tag="v1.1.0",
        git_head="sha",
        type=ReleaseType.MINOR,
        url="https://github.com/owner/repo/releases/1",
    )
    mock_orch = _make_mock_orchestrator(result=mock_release)
    with patch(
        "python_semantic_release.cli.SemanticReleaseOrchestrator",
        return_value=mock_orch,
    ):
        result = runner.invoke(release, ["run", "--no-ci"])
    assert "https://github.com/owner/repo/releases/1" in result.output


def test_run_command_dry_run_shows_banner(runner, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    mock_orch = _make_mock_orchestrator(result=None)
    with patch(
        "python_semantic_release.cli.SemanticReleaseOrchestrator",
        return_value=mock_orch,
    ):
        result = runner.invoke(release, ["run", "--dry-run", "--no-ci"])
    assert "[DRY RUN]" in result.output


def test_run_command_dry_run_no_release_shows_prefix(
    runner, tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    mock_orch = _make_mock_orchestrator(result=None)
    with patch(
        "python_semantic_release.cli.SemanticReleaseOrchestrator",
        return_value=mock_orch,
    ):
        result = runner.invoke(release, ["run", "--dry-run", "--no-ci"])
    assert "[DRY RUN] No Release Needed" in result.output
    assert "[DRY RUN] Version bump: NO" in result.output


def test_run_command_dry_run_release_shows_prefix(
    runner, tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    mock_release = Release(
        version="1.1.0",
        git_tag="v1.1.0",
        git_head="sha",
        type=ReleaseType.MINOR,
    )
    mock_orch = _make_mock_orchestrator(result=mock_release)
    with patch(
        "python_semantic_release.cli.SemanticReleaseOrchestrator",
        return_value=mock_orch,
    ):
        result = runner.invoke(release, ["run", "--dry-run", "--no-ci"])
    assert "[DRY RUN] Release Published" in result.output
    assert "[DRY RUN] Version bump: YES" in result.output


def test_run_command_dry_run_skips_github_output(runner, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    output_file = tmp_path / "github_output"
    output_file.write_text("")
    monkeypatch.setenv("GITHUB_OUTPUT", str(output_file))
    mock_release = Release(
        version="1.1.0",
        git_tag="v1.1.0",
        git_head="sha",
        type=ReleaseType.MINOR,
    )
    mock_orch = _make_mock_orchestrator(result=mock_release)
    with patch(
        "python_semantic_release.cli.SemanticReleaseOrchestrator",
        return_value=mock_orch,
    ):
        runner.invoke(release, ["run", "--dry-run", "--no-ci"])
    assert output_file.read_text() == ""


def test_format_note_line_long_notes_truncated(runner, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    long_notes = "\n".join([f"* feat: item {i}" for i in range(25)])
    mock_release = Release(
        version="1.1.0",
        git_tag="v1.1.0",
        git_head="sha",
        type=ReleaseType.MINOR,
        notes=long_notes,
    )
    mock_orch = _make_mock_orchestrator(result=mock_release)
    with patch(
        "python_semantic_release.cli.SemanticReleaseOrchestrator",
        return_value=mock_orch,
    ):
        result = runner.invoke(release, ["run", "--no-ci"])
    assert "..." in result.output
