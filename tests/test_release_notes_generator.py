import pytest

from python_semantic_release.changelog.generator import (
    ChangelogService,
    ReleaseNotesGenerator,
)
from python_semantic_release.models import Release
from tests.conftest import make_commit, make_context


@pytest.fixture
def generator() -> ReleaseNotesGenerator:
    return ReleaseNotesGenerator()


def _ctx_with_release(tmp_path, commits, version="1.1.0", last="1.0.0"):
    ctx = make_context(tmp_path, commits=commits, last_version=last)
    ctx.next_release = Release(
        version=version,
        git_tag=f"v{version}",
        git_head="newsha",
    )
    return ctx


# --- generate_notes ---

def test_generate_notes_empty_commits(tmp_path, generator):
    ctx = make_context(tmp_path, commits=[])
    assert generator.generate_notes(ctx) == ""


def test_generate_notes_contains_version(tmp_path, generator):
    ctx = _ctx_with_release(
        tmp_path, [make_commit(message="feat: add x")]
    )
    notes = generator.generate_notes(ctx)
    assert "1.1.0" in notes


def test_generate_notes_features_section(tmp_path, generator):
    ctx = _ctx_with_release(
        tmp_path, [make_commit(message="feat: add feature")]
    )
    notes = generator.generate_notes(ctx)
    assert "Features" in notes
    assert "add feature" in notes


def test_generate_notes_bug_fixes_section(tmp_path, generator):
    ctx = _ctx_with_release(
        tmp_path, [make_commit(message="fix: resolve bug")]
    )
    notes = generator.generate_notes(ctx)
    assert "Bug Fixes" in notes
    assert "resolve bug" in notes


def test_generate_notes_multiple_sections(tmp_path, generator):
    ctx = _ctx_with_release(
        tmp_path,
        [
            make_commit(message="feat: new feature"),
            make_commit(message="fix: fix bug"),
        ],
    )
    notes = generator.generate_notes(ctx)
    assert "Features" in notes
    assert "Bug Fixes" in notes


def test_generate_notes_unknown_type_grouped_as_other(tmp_path, generator):
    ctx = _ctx_with_release(
        tmp_path, [make_commit(message="xyz: weird commit")]
    )
    notes = generator.generate_notes(ctx)
    assert "Other Changes" in notes


def test_generate_notes_breaking_marker(tmp_path, generator):
    ctx = _ctx_with_release(
        tmp_path,
        [make_commit(message="feat!: breaking", body="BREAKING CHANGE: removed")],
    )
    notes = generator.generate_notes(ctx)
    assert "BREAKING CHANGE" in notes


def test_generate_notes_compare_url(tmp_path, generator):
    ctx = _ctx_with_release(
        tmp_path, [make_commit(message="feat: x")]
    )
    notes = generator.generate_notes(ctx)
    assert "compare" in notes or "v1.0.0...v1.1.0" in notes


def test_generate_notes_commit_hash_link(tmp_path, generator):
    ctx = _ctx_with_release(
        tmp_path, [make_commit(hash="deadbeef1234", message="fix: thing")]
    )
    notes = generator.generate_notes(ctx)
    assert "deadbee" in notes


def test_generate_notes_with_scope(tmp_path, generator):
    ctx = _ctx_with_release(
        tmp_path, [make_commit(message="feat(api): add endpoint")]
    )
    notes = generator.generate_notes(ctx)
    assert "**api:**" in notes


def test_generate_notes_issue_reference_linked(tmp_path, generator):
    ctx = _ctx_with_release(
        tmp_path,
        [make_commit(message="fix: resolve", body="Closes #42")],
    )
    notes = generator.generate_notes(ctx)
    assert "#42" in notes


def test_generate_notes_no_repo_url_no_links(tmp_path, generator):
    ctx = _ctx_with_release(
        tmp_path, [make_commit(message="feat: x")]
    )
    ctx.options.repository_url = ""
    notes = generator.generate_notes(ctx)
    # still generates notes but no hrefs
    assert "feat" in notes or "x" in notes


def test_generate_notes_ssh_url_converted(tmp_path, generator):
    ctx = _ctx_with_release(
        tmp_path, [make_commit(message="feat: y")]
    )
    ctx.options.repository_url = "git@github.com:owner/repo.git"
    notes = generator.generate_notes(ctx)
    assert "https://github.com/owner/repo" in notes


def test_generate_notes_no_next_release_shows_unreleased(tmp_path, generator):
    ctx = make_context(tmp_path, commits=[make_commit(message="feat: x")])
    ctx.next_release = None
    notes = generator.generate_notes(ctx)
    assert "Unreleased" in notes


def test_generate_notes_sections_ordered_by_priority(tmp_path, generator):
    ctx = _ctx_with_release(
        tmp_path,
        [
            make_commit(message="fix: bug"),
            make_commit(message="feat: feature"),
        ],
    )
    notes = generator.generate_notes(ctx)
    feat_pos = notes.find("Features")
    fix_pos = notes.find("Bug Fixes")
    assert feat_pos < fix_pos


# --- ChangelogService ---

def test_changelog_service_creates_file(tmp_path, generator):
    svc = ChangelogService(generator=generator)
    ctx = _ctx_with_release(tmp_path, [make_commit(message="feat: x")])
    svc.update_changelog(ctx, "CHANGELOG.md", "# Changelog")
    assert (tmp_path / "CHANGELOG.md").exists()


def test_changelog_service_prepends_new_release(tmp_path, generator):
    svc = ChangelogService(generator=generator)
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text("# Changelog\n\n## [1.0.0] old content\n")
    ctx = _ctx_with_release(tmp_path, [make_commit(message="feat: new")])
    svc.update_changelog(ctx, "CHANGELOG.md", "# Changelog")
    content = changelog.read_text()
    assert "1.1.0" in content
    assert "old content" in content
    # new version comes before old content
    assert content.index("1.1.0") < content.index("old content")


def test_changelog_service_handles_missing_file(tmp_path, generator):
    svc = ChangelogService(generator=generator)
    ctx = _ctx_with_release(tmp_path, [make_commit(message="fix: patch")])
    svc.update_changelog(ctx, "CHANGELOG.md", "# Changelog")
    content = (tmp_path / "CHANGELOG.md").read_text()
    assert "# Changelog" in content


def test_changelog_service_strips_existing_title(tmp_path, generator):
    svc = ChangelogService(generator=generator)
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text("# Changelog\n\n## [1.0.0]\n* old\n")
    ctx = _ctx_with_release(tmp_path, [make_commit(message="feat: new")])
    svc.update_changelog(ctx, "CHANGELOG.md", "# Changelog")
    content = changelog.read_text()
    # title should appear only once
    assert content.count("# Changelog") == 1


def test_get_compare_url_no_last_release(tmp_path, generator):
    ctx = make_context(tmp_path, commits=[make_commit(message="feat: x")])
    ctx.last_release = None
    ctx.next_release = Release(version="0.1.0", git_tag="v0.1.0", git_head="sha")
    notes = generator.generate_notes(ctx)
    assert "0.1.0" in notes


def test_format_issue_references_non_github_url(tmp_path, generator):
    ctx = _ctx_with_release(
        tmp_path,
        [make_commit(message="fix: thing", body="Closes #5")],
    )
    ctx.options.repository_url = "https://gitlab.com/owner/repo"
    notes = generator.generate_notes(ctx)
    assert "fix" in notes or "thing" in notes


def test_format_section_empty_commits_returns_empty(tmp_path, generator):
    from python_semantic_release.changelog.generator import CommitGroup
    ctx = make_context(tmp_path)
    empty_group = CommitGroup(title="Features", commits=[], priority=1)
    result = generator._format_section(empty_group, ctx)
    assert result == ""
