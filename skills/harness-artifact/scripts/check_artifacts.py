#!/usr/bin/env python3
"""Validate final HTML documentation artifacts and their catalog entries."""

from __future__ import annotations

import argparse
import json
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse


DOCTYPE = re.compile(r"^\s*<!doctype\s+html", re.IGNORECASE)
CSS_IMPORT = re.compile(r"@import\s+(?:url\()?\s*['\"]?([^'\")\s;]+)", re.IGNORECASE)
CSS_URL = re.compile(r"url\(\s*['\"]?([^'\")]+)", re.IGNORECASE)
NETWORK_API = re.compile(r"\b(?:fetch|XMLHttpRequest|WebSocket|EventSource)\s*(?:\(|\.)")


def is_external(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme.lower() in {"http", "https"} or value.startswith("//")


class ArtifactParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.lang = ""
        self.charset = False
        self.viewport = False
        self.main = False
        self.h1_count = 0
        self.title = ""
        self._in_title = False
        self._in_script = False
        self._in_style = False
        self.external: list[str] = []
        self.dependencies: list[str] = []
        self.script_parts: list[str] = []
        self.style_parts: list[str] = []
        self.images_without_alt = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key.lower(): value or "" for key, value in attrs}
        tag = tag.lower()
        if tag == "html":
            self.lang = values.get("lang", "")
        elif tag == "meta":
            self.charset |= bool(values.get("charset"))
            self.viewport |= values.get("name", "").lower() == "viewport"
        elif tag == "main":
            self.main = True
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

        attributes: list[str] = []
        if tag in {"script", "img", "iframe", "audio", "video", "source", "object", "embed"}:
            attributes.extend(("src", "data"))
        if tag == "link":
            attributes.append("href")
        for attribute in attributes:
            value = values.get(attribute, "").strip()
            if value and not value.startswith(("data:", "#")):
                (self.external if is_external(value) else self.dependencies).append(value)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "title":
            self._in_title = False
        elif tag.lower() == "script":
            self._in_script = False
        elif tag.lower() == "style":
            self._in_style = False

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title += data
        if self._in_script:
            self.script_parts.append(data)
        if self._in_style:
            self.style_parts.append(data)


def validate(path: Path, root: Path, index_text: str) -> list[str]:
    relative = path.relative_to(root).as_posix()
    text = path.read_text(encoding="utf-8")
    findings: list[str] = []
    if not DOCTYPE.search(text):
        findings.append(f"missing HTML doctype: {relative}")
    parser = ArtifactParser()
    try:
        parser.feed(text)
        parser.close()
    except Exception as error:
        return [f"HTML parse error: {relative}: {error}"]
    if parser.lang.lower() != "en":
        findings.append(f"language must be en: {relative}")
    if not parser.charset:
        findings.append(f"missing charset metadata: {relative}")
    if not parser.viewport:
        findings.append(f"missing viewport metadata: {relative}")
    if not parser.title.strip():
        findings.append(f"missing title: {relative}")
    if not parser.main:
        findings.append(f"missing main landmark: {relative}")
    if parser.h1_count != 1:
        findings.append(f"must contain one h1: {relative}")
    if parser.images_without_alt:
        findings.append(f"image missing alt text: {relative}")
    for dependency in parser.external:
        findings.append(f"external dependency: {relative} -> {dependency}")
    for dependency in parser.dependencies:
        findings.append(f"non-self-contained dependency: {relative} -> {dependency}")
    css = "\n".join(parser.style_parts)
    for dependency in CSS_IMPORT.findall(css) + CSS_URL.findall(css):
        if not dependency.strip().startswith(("data:", "#")):
            findings.append(f"CSS dependency: {relative} -> {dependency.strip()}")
    if NETWORK_API.search("\n".join(parser.script_parts)):
        findings.append(f"network API in artifact script: {relative}")
    if path.name not in index_text:
        findings.append(f"unindexed artifact: {relative}")
    return findings


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project_root", nargs="?", default=".")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args()

    root = Path(args.project_root).expanduser().resolve()
    artifact_dir = root / "docs" / "artifacts"
    index = artifact_dir / "index.md"
    issues: list[str] = []
    if not artifact_dir.is_dir():
        issues.append("missing: docs/artifacts")
    if not index.is_file():
        issues.append("missing: docs/artifacts/index.md")
    index_text = index.read_text(encoding="utf-8") if index.is_file() else ""
    if artifact_dir.is_dir():
        for path in sorted(artifact_dir.glob("*.html")):
            issues.extend(validate(path, root, index_text))
    issues = sorted(set(issues))

    if args.format == "json":
        print(json.dumps({"root": str(root), "issues": issues}, indent=2))
    elif issues:
        print("Issues:")
        for issue in issues:
            print(f"- {issue}")
    else:
        print("Artifacts OK")
    if issues:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
