"""Focused tests for scripts/validate.py.

Fixture repositories are generated in temporary directories so that no
SKILL.md files exist in this repository outside skills/.

Run: python3 -m unittest discover -s tests -v
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("validate", REPO_ROOT / "scripts" / "validate.py")
validate = importlib.util.module_from_spec(_spec)
sys.modules["validate"] = validate
_spec.loader.exec_module(validate)

LICENSE_TEXT = (REPO_ROOT / "LICENSE").read_text(encoding="utf-8")

DESCRIPTION = (
    "Checks example widgets for defects using a repeatable procedure. Use when "
    "a user asks to inspect or validate example widgets."
)


def skill_md(
    name: str,
    *,
    description: str = DESCRIPTION,
    extra_frontmatter: str = "",
    metadata: str = '  version: "0.1.0"\n  maturity: draft\n',
    body: str = "# Example\n\nDo the work.\n",
) -> str:
    return (
        "---\n"
        f"name: {name}\n"
        f"description: {json.dumps(description)}\n"
        "license: MIT\n"
        f"{extra_frontmatter}"
        "metadata:\n"
        f"{metadata}"
        "---\n"
        f"{body}"
    )


class FixtureRepo:
    """A minimal valid repository in a temporary directory."""

    def __init__(self, test: unittest.TestCase):
        self._tmp = tempfile.TemporaryDirectory()
        test.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        (self.root / "LICENSE").write_text(LICENSE_TEXT, encoding="utf-8")
        (self.root / "skills").mkdir()
        self.catalog: dict = {"schema_version": 1, "methods": []}

    def add_skill(self, name: str, text: str | None = None, *, maturity: str = "draft") -> Path:
        directory = self.root / "skills" / name
        directory.mkdir(parents=True)
        (directory / "SKILL.md").write_text(text or skill_md(name), encoding="utf-8")
        (directory / "LICENSE").write_text(LICENSE_TEXT, encoding="utf-8")
        self.catalog["methods"].append(
            {
                "name": name,
                "title": name.replace("-", " ").title(),
                "description": DESCRIPTION,
                "category": "Data",
                "tags": ["example"],
                "path": f"skills/{name}",
                "version": "0.1.0",
                "license": "MIT",
                "maturity": maturity,
            }
        )
        return directory

    def write(self, relative: str, content: str | bytes) -> Path:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            path.write_bytes(content)
        else:
            path.write_text(content, encoding="utf-8")
        return path

    def finish(self) -> None:
        self.catalog["methods"].sort(key=lambda m: m["name"])
        (self.root / "catalog.json").write_text(json.dumps(self.catalog, indent=2), encoding="utf-8")
        lines = ["# Fixture", ""]
        for method in self.catalog["methods"]:
            lines.append(f"- [{method['name']}](skills/{method['name']}/SKILL.md)")
        (self.root / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    def validate(self) -> validate.Report:
        self.finish()
        return validate.validate_repository(self.root)


def messages(report: validate.Report) -> str:
    return "\n".join(f"{where}: {message}" for where, message in report.errors)


class ValidRepositoryTests(unittest.TestCase):
    def test_minimal_valid_repository_passes(self):
        repo = FixtureRepo(self)
        directory = repo.add_skill("widget-check")
        (directory / "references").mkdir()
        (directory / "references" / "details.md").write_text("# Details\n", encoding="utf-8")
        (directory / "SKILL.md").write_text(
            skill_md("widget-check", body="# Widget\n\nSee [details](references/details.md).\n"),
            encoding="utf-8",
        )
        report = repo.validate()
        self.assertTrue(report.ok, messages(report))

    def test_actual_repository_passes(self):
        report = validate.validate_repository(REPO_ROOT)
        self.assertTrue(report.ok, messages(report))

    def test_main_returns_nonzero_on_errors(self):
        repo = FixtureRepo(self)
        repo.add_skill("widget-check")
        repo.finish()
        os.remove(repo.root / "skills" / "widget-check" / "LICENSE")
        with open(os.devnull, "w") as devnull:
            stdout = sys.stdout
            sys.stdout = devnull
            try:
                code = validate.main(["--root", str(repo.root)])
            finally:
                sys.stdout = stdout
        self.assertEqual(code, 1)


class FrontmatterTests(unittest.TestCase):
    def assert_error(self, text: str, expected: str, name: str = "widget-check"):
        repo = FixtureRepo(self)
        repo.add_skill(name, text)
        report = repo.validate()
        self.assertFalse(report.ok, "expected validation to fail")
        self.assertIn(expected, messages(report))

    def test_missing_frontmatter(self):
        self.assert_error("# No frontmatter\n", "must start with a '---'")

    def test_unclosed_frontmatter(self):
        self.assert_error("---\nname: widget-check\n", "not closed")

    def test_malformed_yaml(self):
        self.assert_error("---\nname: [unclosed\n---\nBody\n", "invalid YAML")

    def test_duplicate_key(self):
        text = skill_md("widget-check", extra_frontmatter="name: widget-check\n")
        self.assert_error(text, "duplicate key")

    def test_alias_rejected(self):
        text = skill_md(
            "widget-check",
            metadata='  version: &v "0.1.0"\n  maturity: draft\n  other: *v\n',
        )
        self.assert_error(text, "anchors are not allowed")

    def test_explicit_tag_rejected(self):
        text = skill_md("widget-check", extra_frontmatter="compatibility: !!str generic\n")
        self.assert_error(text, "explicit YAML tags")

    def test_unknown_field(self):
        text = skill_md("widget-check", extra_frontmatter="author: someone\n")
        self.assert_error(text, "not defined by the Agent Skills specification: author")

    def test_allowed_tools_rejected(self):
        text = skill_md("widget-check", extra_frontmatter="allowed-tools: Bash\n")
        self.assert_error(text, "'allowed-tools' is not used")

    def test_name_mismatch(self):
        self.assert_error(skill_md("other-name"), "does not match directory name")

    def test_invalid_name_syntax(self):
        for bad in ("Widget-Check", "widget--check", "-widget", "widget-"):
            with self.subTest(name=bad):
                self.assert_error(skill_md(bad), "must use lowercase ASCII", name="widget-check")

    def test_name_too_long(self):
        name = "a" * 65
        self.assert_error(skill_md(name), "exceeds 64 characters", name=name)

    def test_missing_description(self):
        text = "---\nname: widget-check\nlicense: MIT\nmetadata:\n  version: \"0.1.0\"\n  maturity: draft\n---\nBody\n"
        self.assert_error(text, "'description' is required")

    def test_description_too_long(self):
        self.assert_error(skill_md("widget-check", description="x" * 1025), "maximum is 1024")

    def test_unquoted_version(self):
        text = skill_md("widget-check", metadata="  version: 0.1\n  maturity: draft\n")
        self.assert_error(text, "must map strings to strings")

    def test_invalid_maturity(self):
        text = skill_md("widget-check", metadata='  version: "0.1.0"\n  maturity: stable\n')
        self.assert_error(text, "'metadata.maturity' must be one of")

    def test_crlf_rejected(self):
        self.assert_error(skill_md("widget-check").replace("\n", "\r\n"), "line endings")

    def test_body_line_limit(self):
        body = "# Long\n" + "line\n" * 600
        self.assert_error(skill_md("widget-check", body=body), "lines; limit is 500")


class PackageTests(unittest.TestCase):
    def test_missing_skill_md(self):
        repo = FixtureRepo(self)
        repo.add_skill("widget-check")
        os.remove(repo.root / "skills" / "widget-check" / "SKILL.md")
        report = repo.validate()
        self.assertIn("missing SKILL.md", messages(report))

    def test_missing_package_license(self):
        repo = FixtureRepo(self)
        repo.add_skill("widget-check")
        os.remove(repo.root / "skills" / "widget-check" / "LICENSE")
        self.assertIn("missing package-local LICENSE", messages(repo.validate()))

    def test_modified_package_license(self):
        repo = FixtureRepo(self)
        directory = repo.add_skill("widget-check")
        (directory / "LICENSE").write_text(LICENSE_TEXT.replace("2026", "2020"), encoding="utf-8")
        self.assertIn("byte-identical", messages(repo.validate()))

    def test_incomplete_root_license(self):
        repo = FixtureRepo(self)
        repo.add_skill("widget-check")
        short = LICENSE_TEXT.split("THE SOFTWARE IS PROVIDED")[0]
        (repo.root / "LICENSE").write_text(short, encoding="utf-8")
        (repo.root / "skills" / "widget-check" / "LICENSE").write_text(short, encoding="utf-8")
        self.assertIn("MIT notice is incomplete", messages(repo.validate()))

    def test_conflicting_spdx_identifier(self):
        repo = FixtureRepo(self)
        directory = repo.add_skill("widget-check")
        (directory / "SKILL.md").write_text(
            skill_md("widget-check", body="# W\n\nSee [n](notes.md).\n"), encoding="utf-8"
        )
        repo.write("skills/widget-check/notes.md", "SPDX-License-Identifier: GPL-3.0-only\n")
        self.assertIn("conflicting SPDX", messages(repo.validate()))

    def test_broken_link(self):
        repo = FixtureRepo(self)
        repo.add_skill("widget-check", skill_md("widget-check", body="[x](references/missing.md)\n"))
        self.assertIn("broken relative link", messages(repo.validate()))

    def test_link_leaving_package(self):
        repo = FixtureRepo(self)
        repo.add_skill("widget-check", skill_md("widget-check", body="[x](../../README.md)\n"))
        self.assertIn("leaves the Skill package", messages(repo.validate()))

    def test_http_link_rejected(self):
        repo = FixtureRepo(self)
        repo.add_skill("widget-check", skill_md("widget-check", body="[x](http://example.org/)\n"))
        self.assertIn("use https", messages(repo.validate()))

    def test_links_in_code_are_ignored(self):
        repo = FixtureRepo(self)
        body = "Use `[x](missing.md)` literally.\n\n```\n[y](also-missing.md)\n```\n"
        repo.add_skill("widget-check", skill_md("widget-check", body=body))
        report = repo.validate()
        self.assertTrue(report.ok, messages(report))

    def test_orphan_file(self):
        repo = FixtureRepo(self)
        repo.add_skill("widget-check")
        repo.write("skills/widget-check/references/unused.md", "# Unused\n")
        self.assertIn("not linked from SKILL.md", messages(repo.validate()))

    def test_disallowed_file_type(self):
        repo = FixtureRepo(self)
        repo.add_skill("widget-check", skill_md("widget-check", body="[s](run.py)\n"))
        repo.write("skills/widget-check/run.py", "print('hi')\n")
        self.assertIn("is not allowed in packages", messages(repo.validate()))

    def test_executable_file(self):
        repo = FixtureRepo(self)
        repo.add_skill("widget-check", skill_md("widget-check", body="[n](notes.md)\n"))
        path = repo.write("skills/widget-check/notes.md", "# Notes\n")
        path.chmod(0o755)
        self.assertIn("executable files are not allowed", messages(repo.validate()))

    def test_hidden_file(self):
        repo = FixtureRepo(self)
        repo.add_skill("widget-check")
        repo.write("skills/widget-check/.env", "X=1\n")
        self.assertIn("unsafe file name", messages(repo.validate()))

    def test_empty_directory(self):
        repo = FixtureRepo(self)
        directory = repo.add_skill("widget-check")
        (directory / "examples").mkdir()
        self.assertIn("empty directory", messages(repo.validate()))

    @unittest.skipUnless(hasattr(os, "symlink"), "symlinks unsupported")
    def test_symlink_rejected(self):
        repo = FixtureRepo(self)
        directory = repo.add_skill("widget-check")
        try:
            os.symlink(repo.root / "LICENSE", directory / "linked.md")
        except OSError:
            self.skipTest("cannot create symlink")
        self.assertIn("symlinks are not allowed", messages(repo.validate()))

    def test_nested_skill(self):
        repo = FixtureRepo(self)
        repo.add_skill("widget-check", skill_md("widget-check", body="[n](inner/SKILL.md)\n"))
        repo.write("skills/widget-check/inner/SKILL.md", skill_md("inner"))
        self.assertIn("nested Skill", messages(repo.validate()))

    def test_stray_skill_file_outside_skills(self):
        repo = FixtureRepo(self)
        repo.add_skill("widget-check")
        repo.write("tests/fixtures/SKILL.md", skill_md("stray"))
        self.assertIn("would be discovered as an unintended Skill", messages(repo.validate()))

    def test_file_size_limit(self):
        repo = FixtureRepo(self)
        repo.add_skill("widget-check", skill_md("widget-check", body="[d](data.csv)\n"))
        repo.write("skills/widget-check/data.csv", "a\n" * (validate.MAX_FILE_BYTES // 2 + 1))
        self.assertIn("limit is", messages(repo.validate()))

    def test_file_count_limit(self):
        repo = FixtureRepo(self)
        count = validate.MAX_PACKAGE_FILES
        body = "\n".join(f"[f{i}](refs/f{i}.md)" for i in range(count)) + "\n"
        repo.add_skill("widget-check", skill_md("widget-check", body=body))
        for i in range(count):
            repo.write(f"skills/widget-check/refs/f{i}.md", f"# {i}\n")
        self.assertIn(f"limit is {count}", messages(repo.validate()))

    def test_skill_count_limit(self):
        repo = FixtureRepo(self)
        for i in range(validate.MAX_SKILLS + 1):
            repo.add_skill(f"widget-{i:02d}", skill_md(f"widget-{i:02d}"))
        self.assertIn("limit is 20 per repository", messages(repo.validate()))

    def test_file_directly_under_skills(self):
        repo = FixtureRepo(self)
        repo.add_skill("widget-check")
        repo.write("skills/notes.md", "# Notes\n")
        self.assertIn("only Skill directories", messages(repo.validate()))

    def test_duplicate_names(self):
        report = validate.Report()
        skills = [
            validate.SkillInfo("widget", Path("a"), {"name": "widget"}),
            validate.SkillInfo("Widget", Path("b"), {"name": "Widget"}),
        ]
        validate.check_duplicate_names(skills, report)
        self.assertIn("duplicate Skill name", messages(report))


class CatalogTests(unittest.TestCase):
    def test_missing_catalog_entry(self):
        repo = FixtureRepo(self)
        repo.add_skill("widget-check")
        repo.catalog["methods"].clear()
        self.assertIn("has no catalog entry", messages(repo.validate()))

    def test_catalog_entry_without_skill(self):
        repo = FixtureRepo(self)
        repo.add_skill("widget-check")
        extra = dict(repo.catalog["methods"][0], name="ghost-method", path="skills/ghost-method")
        repo.catalog["methods"].append(extra)
        self.assertIn("no Skill directory skills/ghost-method", messages(repo.validate()))

    def test_description_mismatch(self):
        repo = FixtureRepo(self)
        repo.add_skill("widget-check")
        repo.catalog["methods"][0]["description"] = "Different."
        self.assertIn("'description' does not match", messages(repo.validate()))

    def test_maturity_mismatch(self):
        repo = FixtureRepo(self)
        repo.add_skill("widget-check")
        repo.catalog["methods"][0]["maturity"] = "ready-for-review"
        self.assertIn("'maturity' does not match", messages(repo.validate()))

    def test_unknown_category_and_bad_tags(self):
        repo = FixtureRepo(self)
        repo.add_skill("widget-check")
        repo.catalog["methods"][0]["category"] = "Geospatial"
        repo.catalog["methods"][0]["tags"] = ["Bad Tag"]
        errors = messages(repo.validate())
        self.assertIn("'category' must be one of", errors)
        self.assertIn("'tags' must be", errors)

    def test_reviewed_requires_review_record(self):
        repo = FixtureRepo(self)
        text = skill_md("widget-check", metadata='  version: "0.1.0"\n  maturity: reviewed\n')
        repo.add_skill("widget-check", text, maturity="reviewed")
        repo.write("evaluations/widget-check.md", "# Scenario\n")
        self.assertIn("requires a 'review' object", messages(repo.validate()))

    def test_ready_for_review_requires_scenario(self):
        repo = FixtureRepo(self)
        text = skill_md("widget-check", metadata='  version: "0.1.0"\n  maturity: ready-for-review\n')
        repo.add_skill("widget-check", text, maturity="ready-for-review")
        self.assertIn("requires an evaluation scenario", messages(repo.validate()))

    def test_unsorted_catalog(self):
        repo = FixtureRepo(self)
        repo.add_skill("beta-check", skill_md("beta-check"))
        repo.add_skill("alpha-check", skill_md("alpha-check"))
        repo.finish()
        catalog = json.loads((repo.root / "catalog.json").read_text())
        catalog["methods"].reverse()
        (repo.root / "catalog.json").write_text(json.dumps(catalog), encoding="utf-8")
        report = validate.validate_repository(repo.root)
        self.assertIn("sorted by name", messages(report))

    def test_duplicate_json_key(self):
        repo = FixtureRepo(self)
        repo.add_skill("widget-check")
        repo.finish()
        (repo.root / "catalog.json").write_text(
            '{"schema_version": 1, "schema_version": 1, "methods": []}', encoding="utf-8"
        )
        report = validate.validate_repository(repo.root)
        self.assertIn("duplicate key", messages(report))

    def test_readme_must_list_skill(self):
        repo = FixtureRepo(self)
        repo.add_skill("widget-check")
        repo.finish()
        (repo.root / "README.md").write_text("# Fixture\n", encoding="utf-8")
        report = validate.validate_repository(repo.root)
        self.assertIn("does not link skills/widget-check", messages(report))


class CredentialTests(unittest.TestCase):
    # Secret-shaped strings are assembled at runtime so this file itself does
    # not contain them.
    AWS = "AKIA" + "ABCDEFGHIJKLMNOP"
    GITHUB = "ghp" + "_" + "a1B2" * 9
    PRIVATE_KEY = "-----BEGIN " + "RSA PRIVATE KEY-----"
    URI = "postgresql://analyst:" + "s3cretPass" + "@db.internal:5432/app"

    def test_detects_known_patterns(self):
        for sample in (self.AWS, self.GITHUB, self.PRIVATE_KEY, self.URI):
            with self.subTest(sample=sample[:8]):
                self.assertTrue(validate.find_secrets(f"value {sample} end"))

    def test_detects_assigned_secret(self):
        self.assertTrue(validate.find_secrets('password = "' + "hunter22x" + '"'))

    def test_placeholders_are_allowed(self):
        samples = (
            "postgresql://analyst:<password>@localhost:5432/app",
            "postgresql://analyst:${PGPASSWORD}@localhost/app",
            'password = "<password>"',
            'api_key: "YOUR_API_KEY"',
            "postgresql://localhost:5432/app",
        )
        for sample in samples:
            with self.subTest(sample=sample):
                self.assertEqual(validate.find_secrets(sample), [])

    def test_repository_scan_reports_location(self):
        repo = FixtureRepo(self)
        repo.add_skill("widget-check", skill_md("widget-check", body="[n](notes.md)\n"))
        repo.write("skills/widget-check/notes.md", f"# Notes\n\nkey {self.AWS}\n")
        errors = messages(repo.validate())
        self.assertIn("skills/widget-check/notes.md:3", errors)
        self.assertIn("possible credential", errors)


if __name__ == "__main__":
    unittest.main()
