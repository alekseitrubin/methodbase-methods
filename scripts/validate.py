#!/usr/bin/env python3
"""Validate the Methodbase Open Methods repository.

Usage:
    python3 scripts/validate.py [--root PATH]

Checks Agent Skill packages under skills/, the catalog, repository documents,
license notices and accidental credentials. Exits 0 when no errors are found,
1 when errors are found and 2 when the validator cannot run.

The validator never executes package content.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import stat
import sys
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from urllib.parse import unquote

try:
    import yaml
except ImportError:  # pragma: no cover - exercised only without PyYAML
    sys.stderr.write(
        "PyYAML is required: python3 -m pip install -r requirements.txt\n"
    )
    sys.exit(2)

KIB = 1024
MIB = 1024 * KIB

# Repository policy limits. Each is at most the corresponding Methodbase
# GitHub import limit (shown in the comment).
MAX_SKILLS = 20  # Methodbase: 20 discovered candidates per repository
MAX_PACKAGE_FILES = 30  # Methodbase: 100
MAX_FILE_BYTES = 512 * KIB  # Methodbase: 5 MiB
MAX_PACKAGE_BYTES = 2 * MIB  # Methodbase: 20 MiB
MAX_SKILL_MD_BYTES = 80 * KIB  # Methodbase: 80 KiB
MAX_BODY_BYTES = 64 * KIB  # Methodbase: 64 KiB
MAX_BODY_LINES = 500  # Agent Skills specification recommendation
MAX_FRONTMATTER_BYTES = 12 * KIB  # Methodbase: 12 KiB
MAX_PATH_BYTES = 240  # Methodbase: 240 UTF-8 bytes
MAX_PATH_SEGMENTS = 10  # Methodbase: ten segments
BODY_TOKEN_WARNING = 5000  # Agent Skills specification recommendation

MAX_NAME_CHARS = 64
MAX_DESCRIPTION_CHARS = 1024
MAX_COMPATIBILITY_CHARS = 500

SKILLS_DIR = "skills"
SKILL_FILE = "SKILL.md"
LICENSE_FILE = "LICENSE"
CATALOG_FILE = "catalog.json"
EVALUATIONS_DIR = "evaluations"

SPEC_FIELDS = {
    "name",
    "description",
    "license",
    "compatibility",
    "metadata",
    "allowed-tools",
}
REQUIRED_LICENSE = "MIT"
MATURITY_LEVELS = ("draft", "ready-for-review", "reviewed", "deprecated")
# Methodbase category set (PRODUCT_SPEC, "Provenance, taxonomy, and
# compatibility").
CATEGORIES = (
    "Software",
    "Data",
    "Finance",
    "Business",
    "Research",
    "Legal",
    "Marketing",
    "Design",
    "Science",
    "Other",
)
CATALOG_KEYS_REQUIRED = (
    "name",
    "title",
    "description",
    "category",
    "tags",
    "path",
    "version",
    "license",
    "maturity",
)
CATALOG_KEYS_OPTIONAL = ("review",)
REVIEW_KEYS = ("reviewer", "date", "scope")

PACKAGE_EXTENSIONS = {
    ".md",
    ".txt",
    ".csv",
    ".json",
    ".geojson",
    ".sql",
    ".yaml",
    ".yml",
}
TEXT_EXTENSIONS = PACKAGE_EXTENSIONS | {".py", ".cfg", ".toml", ".ini"}
TEXT_NAMES = {"LICENSE", ".gitignore"}
EXCLUDED_DIRS = {
    ".git",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
}

NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SEMVER_RE = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$"
)
TAG_RE = NAME_RE
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
SAFE_SEGMENT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
SCHEME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")
LICENSE_LIKE_RE = re.compile(r"^(licen[cs]e|copying)", re.IGNORECASE)
SPDX_RE = re.compile(r"SPDX-License-Identifier:\s*([^\s*]+)")

MIT_NOTICE_SENTENCES = (
    "Permission is hereby granted, free of charge, to any person obtaining a copy",
    "The above copyright notice and this permission notice shall be included in all",
    'THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR',
)
COPYRIGHT_RE = re.compile(r"^Copyright \(c\) \d{4}(?:-\d{4})? \S.*$", re.MULTILINE)

# Credential patterns. Each pattern is written so that its own source text
# does not match it.
SECRET_PATTERNS = (
    ("AWS access key ID", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b")),
    ("GitHub fine-grained token", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{50,}")),
    ("Slack token", re.compile(r"\bxox[abposr]-[A-Za-z0-9-]{10,}")),
    ("Google API key", re.compile(r"\bAIza[0-9A-Za-z_\-]{35}")),
    ("Stripe live key", re.compile(r"\b[rs]k_live_[0-9A-Za-z]{16,}")),
    ("Anthropic API key", re.compile(r"\bsk-ant-[A-Za-z0-9_\-]{20,}")),
    ("OpenAI-style API key", re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9]{32,}")),
    (
        "private key block",
        re.compile(r"-----BEGIN (?:[A-Z0-9]+ )*PRIVATE KEY-----"),
    ),
)
ASSIGNED_SECRET_RE = re.compile(
    r"(?i)\b(?:password|passwd|pwd|secret|api[_-]?key|access[_-]?token|"
    r"auth[_-]?token|client[_-]?secret)\b\s*[:=]\s*['\"]([^'\"\s]{6,})['\"]"
)
URI_PASSWORD_RE = re.compile(
    r"\b[a-zA-Z][a-zA-Z0-9+.-]*://[^\s:/@'\"<>]+:([^\s@/'\"]+)@"
)
PLACEHOLDER_RE = re.compile(
    r"^(?:<[^<>]+>|\$\{[^}]+\}|\$[A-Za-z_][A-Za-z0-9_]*|\*+|x+|\.\.\.)$"
    r"|example|changeme|placeholder|redacted|your[_-]",
    re.IGNORECASE,
)


@dataclass
class Report:
    errors: list[tuple[str, str]] = field(default_factory=list)
    warnings: list[tuple[str, str]] = field(default_factory=list)

    def error(self, where: str, message: str) -> None:
        self.errors.append((where, message))

    def warn(self, where: str, message: str) -> None:
        self.warnings.append((where, message))

    @property
    def ok(self) -> bool:
        return not self.errors


@dataclass
class SkillInfo:
    name: str
    directory: Path
    frontmatter: dict | None = None


# ---------------------------------------------------------------------------
# YAML frontmatter
# ---------------------------------------------------------------------------


class FrontmatterError(ValueError):
    pass


class _StrictLoader(yaml.SafeLoader):
    """Safe loader that rejects duplicate keys."""


def _construct_mapping(loader, node, deep=False):
    seen = set()
    for key_node, _value_node in node.value:
        if key_node.tag == "tag:yaml.org,2002:merge":
            raise yaml.constructor.ConstructorError(
                None, None, "merge keys ('<<') are not allowed", key_node.start_mark
            )
        key = loader.construct_object(key_node, deep=True)
        try:
            hash(key)
        except TypeError:
            raise yaml.constructor.ConstructorError(
                None, None, "mapping keys must be scalars", key_node.start_mark
            ) from None
        if key in seen:
            raise yaml.constructor.ConstructorError(
                None, None, f"duplicate key {key!r}", key_node.start_mark
            )
        seen.add(key)
    return yaml.SafeLoader.construct_mapping(loader, node, deep=deep)


_StrictLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_mapping
)


def split_frontmatter(text: str) -> tuple[str, str]:
    """Return (frontmatter_text, body). Raise FrontmatterError if absent."""
    if text.startswith("\ufeff"):
        raise FrontmatterError("file starts with a byte order mark")
    if "\r" in text:
        raise FrontmatterError("file uses CR or CRLF line endings; use LF")
    if not text.startswith("---\n"):
        raise FrontmatterError("file must start with a '---' frontmatter line")
    lines = text.split("\n")
    for index in range(1, len(lines)):
        if lines[index] == "---":
            frontmatter = "\n".join(lines[1:index])
            body = "\n".join(lines[index + 1 :])
            return frontmatter, body
    raise FrontmatterError("frontmatter is not closed by a '---' line")


def parse_frontmatter(frontmatter: str) -> dict:
    """Parse frontmatter as plain YAML data.

    Rejects anchors, aliases, explicit tags, merge keys and duplicate keys.
    """
    try:
        for event in yaml.parse(frontmatter, Loader=_StrictLoader):
            if isinstance(event, yaml.AliasEvent):
                raise FrontmatterError("YAML aliases are not allowed")
            if getattr(event, "anchor", None) is not None:
                raise FrontmatterError("YAML anchors are not allowed")
            if getattr(event, "tag", None) is not None:
                raise FrontmatterError(f"explicit YAML tags are not allowed: {event.tag}")
        data = yaml.load(frontmatter, Loader=_StrictLoader)  # noqa: S506 - strict safe loader
    except yaml.YAMLError as exc:
        raise FrontmatterError(f"invalid YAML: {exc}".replace("\n", " ")) from None
    if not isinstance(data, dict):
        raise FrontmatterError("frontmatter must be a YAML mapping")
    return data


def check_frontmatter(data: dict, directory_name: str, where: str, report: Report) -> None:
    unknown = sorted(str(k) for k in data if k not in SPEC_FIELDS)
    if unknown:
        report.error(
            where,
            "frontmatter fields not defined by the Agent Skills specification: "
            + ", ".join(unknown)
            + " (put repository values under 'metadata')",
        )

    name = data.get("name")
    if not isinstance(name, str) or not name:
        report.error(where, "'name' is required and must be a non-empty string")
    else:
        if len(name) > MAX_NAME_CHARS:
            report.error(where, f"'name' exceeds {MAX_NAME_CHARS} characters")
        if not NAME_RE.match(name):
            report.error(
                where,
                f"'name' {name!r} must use lowercase ASCII letters, digits and single "
                "hyphens, without leading or trailing hyphens",
            )
        if name != directory_name:
            report.error(
                where, f"'name' {name!r} does not match directory name {directory_name!r}"
            )

    description = data.get("description")
    if not isinstance(description, str) or not description.strip():
        report.error(where, "'description' is required and must be a non-empty string")
    elif len(description) > MAX_DESCRIPTION_CHARS:
        report.error(
            where,
            f"'description' has {len(description)} characters; maximum is "
            f"{MAX_DESCRIPTION_CHARS}",
        )

    license_value = data.get("license")
    if license_value != REQUIRED_LICENSE:
        report.error(
            where,
            f"'license' must be {REQUIRED_LICENSE!r} (repository policy); "
            f"found {license_value!r}",
        )

    if "compatibility" in data:
        compatibility = data["compatibility"]
        if not isinstance(compatibility, str) or not compatibility.strip():
            report.error(where, "'compatibility' must be a non-empty string")
        elif len(compatibility) > MAX_COMPATIBILITY_CHARS:
            report.error(
                where, f"'compatibility' exceeds {MAX_COMPATIBILITY_CHARS} characters"
            )

    if "allowed-tools" in data:
        report.error(
            where,
            "'allowed-tools' is not used in this repository: Methods must not "
            "pre-approve tool execution",
        )

    metadata = data.get("metadata")
    if not isinstance(metadata, dict):
        report.error(
            where, "'metadata' is required (repository policy) and must be a mapping"
        )
        return
    for key, value in metadata.items():
        if not isinstance(key, str) or not isinstance(value, str):
            report.error(
                where,
                f"'metadata' must map strings to strings; {key!r} has a "
                f"{type(value).__name__} value (quote it)",
            )
    version = metadata.get("version")
    if not isinstance(version, str) or not SEMVER_RE.match(version):
        report.error(where, "'metadata.version' must be a quoted semantic version")
    maturity = metadata.get("maturity")
    if maturity not in MATURITY_LEVELS:
        report.error(
            where,
            f"'metadata.maturity' must be one of {', '.join(MATURITY_LEVELS)}; "
            f"found {maturity!r}",
        )


# ---------------------------------------------------------------------------
# Markdown links
# ---------------------------------------------------------------------------

FENCE_RE = re.compile(r"^(\s{0,3})(`{3,}|~{3,})")
INLINE_CODE_RE = re.compile(r"(`+)(?:(?!\1).)+?\1")
INLINE_LINK_RE = re.compile(
    r"!?\[(?:[^\[\]]|\[[^\[\]]*\])*\]\(\s*(<[^>]*>|[^)\s]+)(?:\s+(?:\"[^\"]*\"|'[^']*'))?\s*\)"
)
REFERENCE_DEF_RE = re.compile(r"^\s{0,3}\[[^\]]+\]:\s*(<[^>]*>|\S+)")
AUTOLINK_RE = re.compile(r"<([A-Za-z][A-Za-z0-9+.-]*:[^\s<>]+)>")
HTML_ATTR_RE = re.compile(r"\b(?:href|src)\s*=\s*[\"']([^\"']+)[\"']", re.IGNORECASE)


def strip_code(markdown: str) -> list[str]:
    """Return lines with fenced code blocks and inline code removed."""
    result = []
    fence = None
    for line in markdown.split("\n"):
        match = FENCE_RE.match(line)
        if fence is None and match:
            fence = match.group(2)[0] * len(match.group(2))
            result.append("")
            continue
        if fence is not None:
            stripped = line.strip()
            if stripped.startswith(fence) and set(stripped) <= {fence[0]}:
                fence = None
            result.append("")
            continue
        result.append(INLINE_CODE_RE.sub("", line))
    return result


def extract_links(markdown: str) -> list[tuple[int, str]]:
    links = []
    for number, line in enumerate(strip_code(markdown), start=1):
        for regex in (INLINE_LINK_RE, AUTOLINK_RE, HTML_ATTR_RE):
            for match in regex.finditer(line):
                links.append((number, match.group(1)))
        match = REFERENCE_DEF_RE.match(line)
        if match:
            links.append((number, match.group(1)))
    cleaned = []
    for number, target in links:
        target = target.strip()
        if target.startswith("<") and target.endswith(">"):
            target = target[1:-1].strip()
        if target:
            cleaned.append((number, target))
    return cleaned


def check_links(
    md_path: Path,
    text: str,
    boundary: Path,
    root: Path,
    report: Report,
    boundary_label: str,
) -> set[Path]:
    """Check links in one Markdown file. Return resolved local targets."""
    targets: set[Path] = set()
    where_base = rel(md_path, root)
    for line, target in extract_links(text):
        where = f"{where_base}:{line}"
        if SCHEME_RE.match(target):
            scheme = target.split(":", 1)[0].lower()
            if scheme == "https":
                continue
            if scheme == "http":
                report.error(where, f"use https for external links: {target}")
            elif scheme == "mailto":
                continue
            else:
                report.error(where, f"unsupported link scheme {scheme!r}: {target}")
            continue
        if target.startswith("#"):
            continue
        path_part = unquote(target.split("#", 1)[0].split("?", 1)[0])
        if not path_part:
            continue
        if path_part.startswith("/") or "\\" in path_part:
            report.error(where, f"link must be a relative path: {target}")
            continue
        resolved = Path(os.path.normpath(md_path.parent / path_part))
        try:
            resolved.relative_to(boundary)
        except ValueError:
            report.error(where, f"link leaves the {boundary_label}: {target}")
            continue
        if not resolved.exists():
            report.error(where, f"broken relative link: {target}")
            continue
        targets.add(resolved)
    return targets


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def rel(path: Path, root: Path) -> str:
    try:
        return PurePosixPath(path.relative_to(root)).as_posix()
    except ValueError:
        return str(path)


def walk_repository(root: Path):
    """Yield (path, is_dir) for repository entries, excluding tool dirs."""
    for current, dirnames, filenames in os.walk(root, followlinks=False):
        dirnames[:] = sorted(d for d in dirnames if d not in EXCLUDED_DIRS)
        current_path = Path(current)
        for name in dirnames:
            yield current_path / name, True
        for name in sorted(filenames):
            yield current_path / name, False


def is_text_candidate(path: Path) -> bool:
    return path.suffix.lower() in TEXT_EXTENSIONS or path.name in TEXT_NAMES or (
        path.suffix == "" and path.name.isupper()
    )


def read_text(path: Path, report: Report, root: Path) -> str | None:
    try:
        return path.read_bytes().decode("utf-8")
    except UnicodeDecodeError:
        report.error(rel(path, root), "file is not valid UTF-8 text")
    except OSError as exc:
        report.error(rel(path, root), f"cannot read file: {exc}")
    return None


# ---------------------------------------------------------------------------
# License
# ---------------------------------------------------------------------------


def check_root_license(root: Path, report: Report) -> bytes | None:
    license_path = root / LICENSE_FILE
    if not license_path.is_file():
        report.error(LICENSE_FILE, "repository LICENSE is missing")
        return None
    data = license_path.read_bytes()
    text = data.decode("utf-8", errors="replace")
    if not text.startswith("MIT License"):
        report.error(LICENSE_FILE, "repository LICENSE must be the MIT License")
    for sentence in MIT_NOTICE_SENTENCES:
        if sentence not in text:
            report.error(LICENSE_FILE, f"MIT notice is incomplete; missing: {sentence!r}")
    if not COPYRIGHT_RE.search(text):
        report.error(LICENSE_FILE, "MIT notice has no 'Copyright (c) <year> <holder>' line")
    return data


# ---------------------------------------------------------------------------
# Skill packages
# ---------------------------------------------------------------------------


def check_path_safety(path: Path, root: Path, report: Report) -> bool:
    """Check one package entry. Return False if it must not be inspected."""
    where = rel(path, root)
    try:
        mode = os.lstat(path).st_mode
    except OSError as exc:
        report.error(where, f"cannot stat: {exc}")
        return False
    if stat.S_ISLNK(mode):
        report.error(where, "symlinks are not allowed in Skill packages")
        return False
    if not (stat.S_ISREG(mode) or stat.S_ISDIR(mode)):
        report.error(where, "special files are not allowed in Skill packages")
        return False
    if stat.S_ISREG(mode) and mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH):
        report.error(where, "executable files are not allowed in Skill packages")
    name = path.name
    if unicodedata.normalize("NFC", name) != name:
        report.error(where, "file name is not Unicode NFC-normalized")
    if not SAFE_SEGMENT_RE.match(name) or ".." in name:
        report.error(
            where,
            "unsafe file name: use ASCII letters, digits, '.', '_' and '-', "
            "not starting with '.' or '-'",
        )
    relative = rel(path, root)
    if len(relative.encode("utf-8")) > MAX_PATH_BYTES:
        report.error(where, f"path exceeds {MAX_PATH_BYTES} UTF-8 bytes")
    if len(PurePosixPath(relative).parts) > MAX_PATH_SEGMENTS:
        report.error(where, f"path exceeds {MAX_PATH_SEGMENTS} segments")
    return True


def check_skill_package(
    directory: Path, root: Path, root_license: bytes | None, report: Report
) -> SkillInfo:
    info = SkillInfo(name=directory.name, directory=directory)
    where_dir = rel(directory, root)

    if not SAFE_SEGMENT_RE.match(directory.name):
        report.error(where_dir, "unsafe Skill directory name")

    entries = sorted(os.listdir(directory))
    if SKILL_FILE not in entries:
        lowered = [e for e in entries if e.lower() == SKILL_FILE.lower()]
        if lowered:
            report.error(where_dir, f"found {lowered[0]!r}; the file must be named {SKILL_FILE}")
        else:
            report.error(where_dir, f"missing {SKILL_FILE}")
        return info
    if LICENSE_FILE not in entries:
        report.error(where_dir, "missing package-local LICENSE (complete MIT notice)")

    files: list[Path] = []
    seen_lower: dict[str, str] = {}
    for current, dirnames, filenames in os.walk(directory, followlinks=False):
        current_path = Path(current)
        safe_dirs = []
        for name in sorted(dirnames):
            path = current_path / name
            if check_path_safety(path, root, report):
                safe_dirs.append(name)
        dirnames[:] = safe_dirs
        if current_path != directory and not dirnames and not filenames:
            report.error(rel(current_path, root), "empty directory")
        for name in sorted(dirnames + filenames):
            key = rel(current_path / name, root).lower()
            if key in seen_lower:
                report.error(
                    rel(current_path / name, root),
                    f"path differs only by case from {seen_lower[key]}",
                )
            seen_lower[key] = rel(current_path / name, root)
        for name in sorted(filenames):
            path = current_path / name
            if not check_path_safety(path, root, report):
                continue
            files.append(path)

    total_bytes = 0
    for path in files:
        where = rel(path, root)
        size = path.stat().st_size
        total_bytes += size
        if size == 0:
            report.error(where, "empty file")
        if size > MAX_FILE_BYTES:
            report.error(where, f"file is {size} bytes; limit is {MAX_FILE_BYTES}")
        if path.name.lower() == SKILL_FILE.lower() and path.parent != directory:
            report.error(where, "nested Skill: SKILL.md is only allowed at the package root")
        if path.parent == directory and path.name in (SKILL_FILE, LICENSE_FILE):
            continue
        if LICENSE_LIKE_RE.match(path.name):
            report.error(where, "additional license files are not allowed; use the package LICENSE")
        elif path.suffix.lower() not in PACKAGE_EXTENSIONS:
            report.error(
                where,
                f"file type {path.suffix or '(none)'!r} is not allowed in packages; "
                f"allowed: {', '.join(sorted(PACKAGE_EXTENSIONS))}",
            )
    if len(files) > MAX_PACKAGE_FILES:
        report.error(where_dir, f"package has {len(files)} files; limit is {MAX_PACKAGE_FILES}")
    if total_bytes > MAX_PACKAGE_BYTES:
        report.error(where_dir, f"package is {total_bytes} bytes; limit is {MAX_PACKAGE_BYTES}")

    # License notice.
    license_path = directory / LICENSE_FILE
    if license_path.is_file() and root_license is not None:
        if license_path.read_bytes() != root_license:
            report.error(
                rel(license_path, root),
                "package LICENSE must be byte-identical to the repository LICENSE",
            )

    # Text checks: encoding, line endings, SPDX identifiers.
    texts: dict[Path, str] = {}
    for path in files:
        text = read_text(path, report, root)
        if text is None:
            continue
        texts[path] = text
        where = rel(path, root)
        if text.startswith("\ufeff"):
            report.error(where, "byte order mark is not allowed")
        if "\r" in text:
            report.error(where, "use LF line endings")
        for match in SPDX_RE.finditer(text):
            if match.group(1) != REQUIRED_LICENSE:
                report.error(where, f"conflicting SPDX license identifier {match.group(1)!r}")

    # SKILL.md.
    skill_path = directory / SKILL_FILE
    where_skill = rel(skill_path, root)
    skill_bytes = skill_path.stat().st_size
    if skill_bytes > MAX_SKILL_MD_BYTES:
        report.error(where_skill, f"SKILL.md is {skill_bytes} bytes; limit is {MAX_SKILL_MD_BYTES}")
    skill_text = texts.get(skill_path)
    if skill_text is None:
        return info
    try:
        frontmatter_text, body = split_frontmatter(skill_text)
    except FrontmatterError as exc:
        report.error(where_skill, str(exc))
        return info
    if len(frontmatter_text.encode("utf-8")) > MAX_FRONTMATTER_BYTES:
        report.error(where_skill, f"frontmatter exceeds {MAX_FRONTMATTER_BYTES} bytes")
    try:
        data = parse_frontmatter(frontmatter_text)
    except FrontmatterError as exc:
        report.error(where_skill, str(exc))
        return info
    info.frontmatter = data
    check_frontmatter(data, directory.name, where_skill, report)

    body_bytes = len(body.encode("utf-8"))
    if not body.strip():
        report.error(where_skill, "Markdown body is empty")
    if body_bytes > MAX_BODY_BYTES:
        report.error(where_skill, f"body is {body_bytes} bytes; limit is {MAX_BODY_BYTES}")
    body_lines = body.count("\n") + 1
    if body_lines > MAX_BODY_LINES:
        report.error(where_skill, f"body has {body_lines} lines; limit is {MAX_BODY_LINES}")
    estimated_tokens = len(body) // 4
    if estimated_tokens > BODY_TOKEN_WARNING:
        report.warn(
            where_skill,
            f"body is roughly {estimated_tokens} tokens; consider moving detail "
            "into linked reference files",
        )

    # Links in every Markdown file; orphans relative to SKILL.md.
    linked_from_skill: set[Path] = set()
    for path, text in texts.items():
        if path.suffix.lower() != ".md":
            continue
        targets = check_links(path, text, directory, root, report, "Skill package")
        if path == skill_path:
            linked_from_skill = targets
    for path in files:
        if path.parent == directory and path.name in (SKILL_FILE, LICENSE_FILE):
            continue
        if path not in linked_from_skill:
            report.error(
                rel(path, root),
                "file is not linked from SKILL.md (supporting files must be one link away)",
            )
    return info


def discover_skills(root: Path, report: Report) -> list[Path]:
    skills_root = root / SKILLS_DIR
    if not skills_root.is_dir():
        report.error(SKILLS_DIR, "skills directory is missing")
        return []
    if skills_root.is_symlink():
        report.error(SKILLS_DIR, "skills directory must not be a symlink")
        return []
    directories = []
    for entry in sorted(os.listdir(skills_root)):
        path = skills_root / entry
        if path.is_symlink():
            report.error(rel(path, root), "symlinks are not allowed under skills/")
        elif path.is_dir():
            directories.append(path)
        else:
            report.error(rel(path, root), "only Skill directories are allowed directly under skills/")
    if len(directories) > MAX_SKILLS:
        report.error(SKILLS_DIR, f"{len(directories)} Skills; limit is {MAX_SKILLS} per repository")
    return directories


def check_stray_skill_files(root: Path, report: Report) -> None:
    """SKILL.md may only exist at skills/<name>/SKILL.md."""
    for path, is_dir in walk_repository(root):
        if is_dir or path.name.lower() != SKILL_FILE.lower():
            continue
        parts = PurePosixPath(rel(path, root)).parts
        if len(parts) == 3 and parts[0] == SKILLS_DIR and parts[2] == SKILL_FILE:
            continue
        report.error(
            rel(path, root),
            "SKILL.md outside skills/<name>/ would be discovered as an unintended Skill",
        )


def check_duplicate_names(skills: list[SkillInfo], report: Report) -> None:
    seen: dict[str, str] = {}
    for skill in skills:
        candidates = {skill.name.lower()}
        if skill.frontmatter and isinstance(skill.frontmatter.get("name"), str):
            candidates.add(skill.frontmatter["name"].lower())
        for candidate in candidates:
            if candidate in seen and seen[candidate] != skill.name:
                report.error(
                    f"{SKILLS_DIR}/{skill.name}",
                    f"duplicate Skill name {candidate!r} (also {SKILLS_DIR}/{seen[candidate]})",
                )
            seen.setdefault(candidate, skill.name)


# ---------------------------------------------------------------------------
# Catalog
# ---------------------------------------------------------------------------


def _reject_duplicate_json_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate key {key!r}")
        result[key] = value
    return result


def check_catalog(root: Path, skills: list[SkillInfo], report: Report) -> None:
    path = root / CATALOG_FILE
    if not path.is_file():
        report.error(CATALOG_FILE, "catalog is missing")
        return
    try:
        catalog = json.loads(
            path.read_text(encoding="utf-8"), object_pairs_hook=_reject_duplicate_json_keys
        )
    except (ValueError, UnicodeDecodeError) as exc:
        report.error(CATALOG_FILE, f"invalid JSON: {exc}")
        return
    if not isinstance(catalog, dict):
        report.error(CATALOG_FILE, "catalog must be a JSON object")
        return
    unknown_top = sorted(set(catalog) - {"schema_version", "methods"})
    if unknown_top:
        report.error(CATALOG_FILE, f"unknown top-level keys: {', '.join(unknown_top)}")
    if catalog.get("schema_version") != 1:
        report.error(CATALOG_FILE, "'schema_version' must be 1")
    methods = catalog.get("methods")
    if not isinstance(methods, list):
        report.error(CATALOG_FILE, "'methods' must be a list")
        return

    by_name = {skill.name: skill for skill in skills}
    listed: list[str] = []
    for index, entry in enumerate(methods):
        where = f"{CATALOG_FILE}: methods[{index}]"
        if not isinstance(entry, dict):
            report.error(where, "entry must be an object")
            continue
        missing = [k for k in CATALOG_KEYS_REQUIRED if k not in entry]
        if missing:
            report.error(where, f"missing keys: {', '.join(missing)}")
        unknown = sorted(set(entry) - set(CATALOG_KEYS_REQUIRED) - set(CATALOG_KEYS_OPTIONAL))
        if unknown:
            report.error(where, f"unknown keys: {', '.join(unknown)}")
        name = entry.get("name")
        if not isinstance(name, str):
            report.error(where, "'name' must be a string")
            continue
        where = f"{CATALOG_FILE}: {name}"
        listed.append(name)

        title = entry.get("title")
        if not isinstance(title, str) or not title.strip() or len(title) > 120:
            report.error(where, "'title' must be a non-empty string of at most 120 characters")
        if entry.get("category") not in CATEGORIES:
            report.error(where, f"'category' must be one of {', '.join(CATEGORIES)}")
        tags = entry.get("tags")
        if (
            not isinstance(tags, list)
            or not 1 <= len(tags) <= 10
            or not all(isinstance(t, str) and TAG_RE.match(t) for t in tags)
            or len(set(tags)) != len(tags)
        ):
            report.error(where, "'tags' must be 1-10 unique lowercase hyphenated strings")
        if entry.get("path") != f"{SKILLS_DIR}/{name}":
            report.error(where, f"'path' must be '{SKILLS_DIR}/{name}'")
        if entry.get("maturity") not in MATURITY_LEVELS:
            report.error(where, f"'maturity' must be one of {', '.join(MATURITY_LEVELS)}")

        review = entry.get("review")
        if entry.get("maturity") == "reviewed":
            if not isinstance(review, dict) or set(review) != set(REVIEW_KEYS):
                report.error(
                    where,
                    "maturity 'reviewed' requires a 'review' object with "
                    + ", ".join(REVIEW_KEYS),
                )
            else:
                if not all(isinstance(review[k], str) and review[k].strip() for k in REVIEW_KEYS):
                    report.error(where, "'review' values must be non-empty strings")
                elif not DATE_RE.match(review["date"]):
                    report.error(where, "'review.date' must be YYYY-MM-DD")
        elif review is not None:
            report.error(where, "'review' is only allowed when maturity is 'reviewed'")

        skill = by_name.get(name)
        if skill is None:
            report.error(where, f"no Skill directory {SKILLS_DIR}/{name}")
            continue
        frontmatter = skill.frontmatter
        if not frontmatter:
            continue
        metadata = frontmatter.get("metadata") if isinstance(frontmatter.get("metadata"), dict) else {}
        expected = {
            "description": frontmatter.get("description"),
            "license": frontmatter.get("license"),
            "version": metadata.get("version"),
            "maturity": metadata.get("maturity"),
        }
        for key, value in expected.items():
            if entry.get(key) != value:
                report.error(where, f"'{key}' does not match SKILL.md frontmatter")

    for name in sorted(set(by_name) - set(listed)):
        report.error(CATALOG_FILE, f"Skill {SKILLS_DIR}/{name} has no catalog entry")
    duplicates = sorted({n for n in listed if listed.count(n) > 1})
    for name in duplicates:
        report.error(CATALOG_FILE, f"duplicate catalog entry {name!r}")
    if listed != sorted(listed):
        report.error(CATALOG_FILE, "catalog entries must be sorted by name")


# ---------------------------------------------------------------------------
# Repository documents and credentials
# ---------------------------------------------------------------------------


def check_repository_documents(root: Path, skills: list[SkillInfo], report: Report) -> None:
    documents = sorted(root.glob("*.md"))
    evaluations = root / EVALUATIONS_DIR
    if evaluations.is_dir():
        documents += sorted(evaluations.glob("*.md"))
    for path in documents:
        text = read_text(path, report, root)
        if text is not None:
            check_links(path, text, root, root, report, "repository")

    readme = root / "README.md"
    readme_text = readme.read_text(encoding="utf-8") if readme.is_file() else ""
    if not readme_text:
        report.error("README.md", "README is missing")
    for skill in skills:
        if f"{SKILLS_DIR}/{skill.name}/{SKILL_FILE}" not in readme_text:
            report.error("README.md", f"Available Methods does not link {SKILLS_DIR}/{skill.name}")
        metadata = (skill.frontmatter or {}).get("metadata")
        maturity = metadata.get("maturity") if isinstance(metadata, dict) else None
        if maturity in ("ready-for-review", "reviewed"):
            scenario = evaluations / f"{skill.name}.md"
            if not scenario.is_file():
                report.error(
                    rel(scenario, root),
                    f"maturity {maturity!r} requires an evaluation scenario",
                )


def find_secrets(text: str) -> list[tuple[int, str]]:
    findings = []
    for number, line in enumerate(text.split("\n"), start=1):
        for label, regex in SECRET_PATTERNS:
            if regex.search(line):
                findings.append((number, label))
        for regex, label in (
            (ASSIGNED_SECRET_RE, "hard-coded secret value"),
            (URI_PASSWORD_RE, "password in connection URI"),
        ):
            for match in regex.finditer(line):
                if not PLACEHOLDER_RE.search(match.group(1)):
                    findings.append((number, label))
    return findings


def check_credentials(root: Path, report: Report) -> None:
    for path, is_dir in walk_repository(root):
        if is_dir or path.is_symlink() or not is_text_candidate(path):
            continue
        try:
            if path.stat().st_size > 2 * MIB:
                continue
            text = path.read_bytes().decode("utf-8", errors="ignore")
        except OSError:
            continue
        for line, label in find_secrets(text):
            report.error(
                f"{rel(path, root)}:{line}",
                f"possible credential ({label}); use a placeholder such as <password>",
            )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def validate_repository(root: Path) -> Report:
    root = root.resolve()
    report = Report()
    root_license = check_root_license(root, report)
    skills = [
        check_skill_package(directory, root, root_license, report)
        for directory in discover_skills(root, report)
    ]
    check_stray_skill_files(root, report)
    check_duplicate_names(skills, report)
    check_catalog(root, skills, report)
    check_repository_documents(root, skills, report)
    check_credentials(root, report)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parent.parent,
        help="repository root (default: parent of scripts/)",
    )
    args = parser.parse_args(argv)
    if not args.root.is_dir():
        sys.stderr.write(f"not a directory: {args.root}\n")
        return 2

    report = validate_repository(args.root)
    for where, message in report.warnings:
        print(f"WARNING {where}: {message}")
    for where, message in report.errors:
        print(f"ERROR   {where}: {message}")
    skills_root = args.root / SKILLS_DIR
    count = len([p for p in skills_root.iterdir() if p.is_dir()]) if skills_root.is_dir() else 0
    status = "passed" if report.ok else "failed"
    print(
        f"Validation {status}: {count} Skill(s), "
        f"{len(report.errors)} error(s), {len(report.warnings)} warning(s)."
    )
    return 0 if report.ok else 1


if __name__ == "__main__":
    sys.exit(main())
