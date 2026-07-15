#!/usr/bin/env python3
"""Check canonical project documentation and user-facing HTML artifacts."""

from __future__ import annotations

import argparse
import json
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse


REQUIRED = (
    "README.md",
    "docs/index.md",
    "docs/project.md",
    "docs/architecture.md",
    "docs/development.md",
    "docs/modules",
    "docs/artifacts",
    "docs/artifacts/index.md",
)
LIMITS = {
    "README.md": 120,
    "docs/index.md": 100,
    "docs/project.md": 220,
    "docs/architecture.md": 220,
    "docs/development.md": 220,
    "docs/artifacts/index.md": 160,
}
MARKDOWN_LINK = re.compile(r"(?<!!)\[[^]]+\]\(([^)]+)\)")
DOCTYPE = re.compile(r"^\s*<!doctype\s+html", re.IGNORECASE)
CSS_IMPORT = re.compile(r"@import\s+(?:url\()?\s*['\"]?([^'\")\s;]+)", re.IGNORECASE)
CSS_URL = re.compile(r"url\(\s*['\"]?([^'\")]+)", re.IGNORECASE)
NETWORK_API = re.compile(r"\b(?:fetch|XMLHttpRequest|WebSocket|EventSource)\s*(?:\(|\.)")


class ArtifactParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.lang = ""
        self.has_charset = False
        self.has_viewport = False
        self.has_main = False
        self.h1_count = 0
        self.title_parts: list[str] = []
        self._in_title = False
        self._in_script = False
        self._in_style = False
        self.external_dependencies: list[str] = []
        self.local_dependencies: list[str] = []
        self.script_parts: list[str] = []
        self.style_parts: list[str] = []
        self.images_without_alt = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key.lower(): value or "" for key, value in attrs}
        tag = tag.lower()
        if tag == "html":
            self.lang = values.get("lang", "")
        elif tag == "meta":
            self.has_charset |= bool(values.get("charset"))
            self.has_viewport |= values.get("name", "").lower() == "viewport"
        elif tag == "main":
            self.has_main = True
        elif tag == "h1":
            self.h1_count += 1
        elif tag == "title":
            self._in_title = True
        elif tag == "script":
            self._in_script = True
        elif tag == "style":
            self._in_style = True
        elif tag == "img" and "alt" not in values:
            self.images_without_alt += 1

        dependency_attributes: list[str] = []
        if tag in {"script", "img", "iframe", "audio", "video", "source", "object", "embed"}:
            dependency_attributes.extend(("src", "data"))
        if tag == "link":
            dependency_attributes.append("href")
        for attribute in dependency_attributes:
            value = values.get(attribute, "").strip()
            if value and not value.startswith(("data:", "#")):
                (self.external_dependencies if _is_external(value) else self.local_dependencies).append(value)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "title":
            self._in_title = False
        elif tag.lower() == "script":
            self._in_script = False
        elif tag.lower() == "style":
            self._in_style = False

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title_parts.append(data)
        if self._in_script:
            self.script_parts.append(data)
        if self._in_style:
            self.style_parts.append(data)


def _is_external(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme.lower() in {"http", "https", "//"} or value.startswith("//")


def _local_target(source: Path, raw: str) -> Path | None:
    target = raw.strip().split("#", 1)[0]
    if not target or target.startswith(("#", "mailto:", "tel:")):
        return None
    parsed = urlparse(target)
    if parsed.scheme or target.startswith("//"):
        return None
    return (source.parent / parsed.path).resolve()


def _artifact_issues(path: Path, root: Path) -> list[str]:
    relative = path.relative_to(root).as_posix()
    text = path.read_text(encoding="utf-8")
    findings: list[str] = []
    if not DOCTYPE.search(text):
        findings.append(f"artifact missing HTML doctype: {relative}")
    parser = ArtifactParser()
    try:
        parser.feed(text)
        parser.close()
    except Exception as error:
        return [f"artifact HTML parse error: {relative}: {error}"]
    if parser.lang.lower() != "en":
        findings.append(f"artifact language must be en: {relative}")
    if not parser.has_charset:
        findings.append(f"artifact missing charset metadata: {relative}")
    if not parser.has_viewport:
        findings.append(f"artifact missing viewport metadata: {relative}")
    if not "".join(parser.title_parts).strip():
        findings.append(f"artifact missing title: {relative}")
    if not parser.has_main:
        findings.append(f"artifact missing main landmark: {relative}")
    if parser.h1_count != 1:
        findings.append(f"artifact must contain one h1: {relative}")
    if parser.images_without_alt:
        findings.append(f"artifact image missing alt text: {relative}")
    for dependency in parser.external_dependencies:
        findings.append(f"artifact external dependency: {relative} -> {dependency}")
    for dependency in parser.local_dependencies:
        findings.append(f"artifact non-self-contained dependency: {relative} -> {dependency}")
    css = "\n".join(parser.style_parts)
    for dependency in CSS_IMPORT.findall(css) + CSS_URL.findall(css):
        if not dependency.strip().startswith(("data:", "#")):
            findings.append(f"artifact CSS dependency: {relative} -> {dependency.strip()}")
    if NETWORK_API.search("\n".join(parser.script_parts)):
        findings.append(f"artifact network API in script: {relative}")
    return findings


def check(root: Path) -> tuple[list[str], list[str]]:
    issues: list[str] = []
    warnings: list[str] = []
    for relative in REQUIRED:
        if not (root / relative).exists():
            issues.append(f"missing: {relative}")

    docs_root = root / "docs"
    docs_index = docs_root / "index.md"
    artifact_index = docs_root / "artifacts" / "index.md"
    docs_index_text = docs_index.read_text(encoding="utf-8") if docs_index.is_file() else ""
    artifact_index_text = artifact_index.read_text(encoding="utf-8") if artifact_index.is_file() else ""

    markdown_files: list[Path] = []
    if (root / "README.md").is_file():
        markdown_files.append(root / "README.md")
    if docs_root.is_dir():
        markdown_files.extend(sorted(docs_root.rglob("*.md")))

    for path in markdown_files:
        relative = path.relative_to(root).as_posix()
        text = path.read_text(encoding="utf-8")
        limit = LIMITS.get(relative, 180 if relative.startswith("docs/modules/") else 220)
        if len(text.splitlines()) > limit:
            warnings.append(f"oversized: {relative} exceeds {limit} lines")
        for raw in MARKDOWN_LINK.findall(text):
            target = _local_target(path, raw)
            if target is not None and not target.exists():
                issues.append(f"broken link: {relative} -> {raw}")

    if docs_root.is_dir():
        for path in sorted((docs_root / "modules").glob("*.md")) if (docs_root / "modules").is_dir() else []:
            route = path.relative_to(docs_root).as_posix()
            if route not in docs_index_text and path.name not in docs_index_text:
                warnings.append(f"unindexed module: docs/{route}")

    artifacts = sorted((docs_root / "artifacts").glob("*.html")) if (docs_root / "artifacts").is_dir() else []
    for path in artifacts:
        issues.extend(_artifact_issues(path, root))
        if path.name not in artifact_index_text:
            issues.append(f"unindexed artifact: docs/artifacts/{path.name}")

    return sorted(set(issues)), sorted(set(warnings))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project_root", nargs="?", default=".")
    parser.add_argument("--strict", action="store_true", help="Fail on warnings as well as issues.")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args()

    root = Path(args.project_root).expanduser().resolve()
    if not root.is_dir():
        raise SystemExit(f"Project root is not a directory: {root}")
    issues, warnings = check(root)

    if args.format == "json":
        print(json.dumps({"root": str(root), "issues": issues, "warnings": warnings}, indent=2))
    else:
        if issues:
            print("Issues:")
            for issue in issues:
                print(f"- {issue}")
        if warnings:
            print("Warnings:")
            for warning in warnings:
                print(f"- {warning}")
        if not issues and not warnings:
            print("Documentation OK")

    if issues or (args.strict and warnings):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
