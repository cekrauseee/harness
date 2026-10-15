#!/usr/bin/env python3
"""Harness change map: consolidate Git facts, accepted run records and agent gap fills into map.json."""
from __future__ import annotations

import argparse
import fnmatch
import json
import os
from pathlib import Path
import posixpath
import re
import shutil
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
from harness import Error, atomic_write, fail, make_directory, probe, safe_path  # noqa: E402
from records import (PLAN_ID, Tree, commit, environment, git, read_events, report, resolve_symbol,  # noqa: E402
                     schema_errors, work_directory)

EXCLUDE = ["pnpm-lock.yaml", "package-lock.json", "yarn.lock", "Cargo.lock", "poetry.lock", "uv.lock", "go.sum",
           "*.min.js", "*.map"]
MAX_LINES = 3000
GROUP_ABOVE = 40
STATUS = {"A": "added", "M": "modified", "D": "deleted", "R": "renamed", "C": "copied", "T": "type-changed"}
HUNK = re.compile(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@ ?(.*)")
SCRIPT = (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".mts", ".cts")
EXTRACTORS = SCRIPT + (".py",)


# --- Git facts -------------------------------------------------------------------------------

def changes(repo, base, head):
    """{path: file fact} for base...head, renames keyed by their new path."""
    fields = git(repo, "diff", "-M", "--name-status", "-z", f"{base}...{head}").split("\0")
    files, index = {}, 0
    while index < len(fields) - 1:
        letter = fields[index][:1]
        if letter in "RC":
            previous, path, index = fields[index + 1], fields[index + 2], index + 3
            files[path] = {"status": STATUS[letter], "previous": previous}
        else:
            path, index = fields[index + 1], index + 2
            files[path] = {"status": STATUS.get(letter, "modified")}
    fields = git(repo, "diff", "-M", "--numstat", "-z", f"{base}...{head}").split("\0")
    index = 0
    while index < len(fields) - 1:
        added, deleted, path = fields[index].split("\t", 2)
        index += 1
        if not path:  # renames: counts, then old and new path as separate fields
            path, index = fields[index + 1], index + 2
        if path in files:
            files[path]["added"] = None if added == "-" else int(added)
            files[path]["deleted"] = None if deleted == "-" else int(deleted)
    for fact in files.values():
        fact.setdefault("added", 0)
        fact.setdefault("deleted", 0)
    return files


def hunks(diff):
    found, current = [], None
    for line in diff.split("\n"):
        match = HUNK.match(line)
        if match:
            old, new = int(match[1]), int(match[3])
            current = {"header": line, "context": match[5], "oldStart": old,
                       "oldLines": 1 if match[2] is None else int(match[2]), "newStart": new,
                       "newLines": 1 if match[4] is None else int(match[4]), "lines": [], "notes": [], "commits": []}
            found.append(current)
        elif current is not None and line[:1] in ("+", "-", " "):  # one file per diff: no headers after @@
            current["lines"].append(line)
    return found


def blame(repo, base, head, path, ranges=()):
    """{line at head: commit} for lines introduced in base..head."""
    arguments = ["blame", "--porcelain"] + [f"-L{start},{end}" for start, end in ranges] + [f"{base}..{head}", "--", path]
    owners, output = {}, git(repo, *arguments, check=False) or ""
    for line in output.split("\n"):
        parts = line.split(" ")
        if len(parts) >= 3 and re.fullmatch(r"[0-9a-f]{40,64}", parts[0]):
            owners[int(parts[2])] = parts[0]
    return owners


def code_payload(repo, base, head, files, exclude, max_lines, commits):
    tree, code = Tree(repo, head), {}
    for path, fact in files.items():
        if any(fnmatch.fnmatch(path, p) or fnmatch.fnmatch(posixpath.basename(path), p) for p in exclude):
            code[path] = {"omitted": "excluded"}
        elif fact["added"] is None:
            code[path] = {"omitted": "binary"}
        elif fact["status"] == "added":
            lines = (tree.text(path) or "").split("\n")
            if lines and lines[-1] == "":
                lines.pop()
            if len(lines) > max_lines:
                code[path] = {"omitted": "too-large"}
                continue
            owners = blame(repo, base, head, path)
            code[path] = {"lines": lines, "commits": sorted({c for c in owners.values() if c in commits})}
        else:
            paths = [fact["previous"], path] if "previous" in fact else [path]
            parsed = hunks(git(repo, "diff", "-M", "-U3", f"{base}...{head}", "--", *paths))
            if sum(len(h["lines"]) for h in parsed) > max_lines:
                code[path] = {"omitted": "too-large"}
                continue
            ranges = [(h["newStart"], h["newStart"] + h["newLines"] - 1) for h in parsed if h["newLines"]]
            owners = blame(repo, base, head, path, ranges) if ranges and fact["status"] != "deleted" else {}
            touching = None
            for hunk in parsed:
                line, found = hunk["newStart"], set()
                for text in hunk["lines"]:
                    if text[:1] == "+" and owners.get(line) in commits:
                        found.add(owners[line])
                    line += text[:1] != "-"
                if not found:  # deletions only: the commits that touched the file
                    if touching is None:
                        touching = set(git(repo, "log", "--format=%H", f"{base}..{head}", "--", *paths).split())
                    found = touching & set(commits)
                hunk["commits"] = sorted(found)
            code[path] = {"hunks": parsed}
    return code


def commit_messages(repo, base, head):
    output = git(repo, "log", "--format=%H%x00%s%x00%b%x1e", f"{base}..{head}")
    messages = {}
    for entry in output.split("\x1e"):
        parts = entry.strip("\n").split("\0")
        if len(parts) == 3:
            messages[parts[0]] = {"subject": parts[1], "body": parts[2].strip()}
    return messages


# --- Imports ---------------------------------------------------------------------------------

def imports(path, text):
    """Repository paths a file may import, as candidate lists, for Python and JavaScript/TypeScript."""
    folder = posixpath.dirname(path)
    if path.endswith(SCRIPT):
        found = []
        for target in re.findall(r"""(?:\bfrom\s*|\bimport\s*\(?\s*|\brequire\s*\(\s*)['"](\.{1,2}/[^'"]+)['"]""", text):
            stem = posixpath.normpath(posixpath.join(folder, target))
            bare = re.sub(r"\.(?:js|jsx|mjs|cjs)$", "", stem)
            found.append([stem] + [bare + s for s in SCRIPT] + [f"{bare}/index{s}" for s in SCRIPT])
        return found
    if path.endswith(".py"):
        found = []
        for dots, module, names in re.findall(r"^[ \t]*from[ \t]+(\.*)([\w.]*)[ \t]+import[ \t]+([\w \t,()*]+)", text, re.M):
            if dots:
                parts = folder.split("/") if folder else []
                root = parts[:len(parts) - len(dots) + 1] if len(dots) > 1 else parts
                base = "/".join(root + ([module.replace(".", "/")] if module else []))
            else:
                base = module.replace(".", "/")
            found.append([f"{base}.py", f"{base}/__init__.py"])
            for name in re.findall(r"\w+", names):
                found.append([f"{base}/{name}.py".lstrip("/")])
        for module in re.findall(r"^[ \t]*import[ \t]+([\w.]+)", text, re.M):
            base = module.replace(".", "/")
            found.append([f"{base}.py", f"{base}/__init__.py"])
        return found
    return []


# --- Plan ------------------------------------------------------------------------------------

def plan_tables(work_dir):
    """Ids in plan order and their table cells by lowercase header, from README and module files."""
    order, cells, title = [], {}, None
    for path in [work_dir / "README.md", *sorted((work_dir / "modules").glob("*.md"))]:
        if not path.is_file():
            continue
        header = None
        for line in safe_path(path).read_text(errors="replace").split("\n"):
            if title is None and line.startswith("# "):
                title = re.sub(r"^#\s+(?:Plan:\s*)?", "", line).strip()
                title = title[:1].upper() + title[1:]
            for identifier in PLAN_ID.findall(line):
                if identifier not in order:
                    order.append(identifier)
            row = [c.strip() for c in line.strip().strip("|").split("|")] if line.lstrip().startswith("|") else None
            if row is None:
                header = None
            elif all(re.fullmatch(r":?-{3,}:?", c) for c in row):
                continue
            elif PLAN_ID.fullmatch(row[0].strip("`")) and header:
                cells.setdefault(row[0].strip("`"), dict(zip(header, row)))
            else:
                header = [c.lower() for c in row]
    return order, cells, title


# --- Consolidation ---------------------------------------------------------------------------

def accepted_records(work_dir):
    """Accepted records in acceptance order, their runs, and record files never accepted."""
    accepted, usage, present = [], {}, set()
    fronts = work_dir / "fronts"
    for front_dir in sorted(fronts.iterdir()) if fronts.is_dir() else []:
        if not front_dir.is_dir():
            continue
        events, _ = read_events(safe_path(front_dir))
        for event in events:
            key = (front_dir.name, event.get("run"))
            for name, value in event.get("tokens", {}).items():
                usage.setdefault(key, {})[name] = usage.get(key, {}).get(name, 0) + value
            if event["kind"] == "accepted" and event.get("run"):
                accepted.append((event["ts"], front_dir.name, event["run"]))
        for path in (front_dir / "runs").glob("*.record.json"):
            present.add((front_dir.name, path.name[:-len(".record.json")]))
    loaded, seen = [], set()
    for stamp, front, run in sorted(accepted):
        path = safe_path(fronts / front / "runs" / f"{run}.record.json")
        try:
            record = json.loads(path.read_text())
        except (OSError, ValueError):
            record = None
        if record is None or schema_errors(record, "record.v1.json"):
            loaded.append((None, {"front": front, "run": run, "record": str(path.relative_to(work_dir))}))
            continue
        if (front, run) in seen:
            continue
        seen.add((front, run))
        entry = {"front": front, "run": run, "kind": record["kind"], "accepted": stamp,
                 "record": str(path.relative_to(work_dir))}
        for key in ("iteration", "host", "model"):
            if key in record:
                entry[key] = record[key]
        if usage.get((front, run)):
            entry["tokens"] = usage[(front, run)]
        loaded.append((record, entry))
    unaccepted = sorted(f"fronts/{f}/runs/{r}.record.json" for f, r in present - seen)
    return loaded, unaccepted


def build(repo, work_dir, base_ref, head_ref, exclude=EXCLUDE, max_lines=MAX_LINES):
    base, head = commit(repo, base_ref), commit(repo, head_ref)
    tree = Tree(repo, head)
    supplement_path = work_dir / "map" / "supplement.json"
    supplement = {"format": "harness-map-supplement-v1"}
    if supplement_path.is_file():
        try:
            supplement = json.loads(safe_path(supplement_path).read_text())
        except ValueError as exc:
            fail("invalid_supplement", "map/supplement.json is not valid JSON.", reason=str(exc))
        errors = schema_errors(supplement, "map.v1.json", "supplement")
        if errors:
            fail("invalid_supplement", "map/supplement.json does not match the supplement schema.", **report(errors))
    files = changes(repo, base, head)
    commits = commit_messages(repo, base, head)
    code = code_payload(repo, base, head, files, exclude, max_lines, commits)
    order, cells, plan_title = plan_tables(work_dir)
    loaded, unaccepted = accepted_records(work_dir)
    gaps = []

    def gap(kind, level="error", **details):
        gaps.append({"kind": kind, "level": level, **details})

    for record, entry in loaded:
        if record is None:
            gap("invalid_reference", record=entry["record"], problem="accepted record is missing or invalid")
    sources = [(r, e) for r, e in loaded if r is not None] + [(supplement, {"front": None, "run": None})]

    # Cards, roles, notes, edges: later records override earlier ones; the supplement overrides all.
    cards, roles, notes, authored = {}, {}, {}, {}
    attention, flows, tests, followups = {}, {}, {}, []
    for source, entry in sources:
        where = entry["record"] if entry.get("record") else "map/supplement.json"
        for card in source.get("cards", []):
            cards[card["id"]] = {k: card[k] for k in ("id", "layer", "group", "title", "summary", "files") if k in card}
        roles.update(source.get("files", {}))
        for note in source.get("notes", []):
            if note.get("replaces"):
                notes.pop((note["path"], note["replaces"]), None)
            notes[(note["path"], note["symbol"])] = {"path": note["path"], "symbol": note["symbol"], "text": note["text"], "from": where}
        for edge in source.get("edges", []):
            authored[(edge["from"], edge["to"])] = {"from": edge["from"], "to": edge["to"], "kind": "authored",
                                                    **({"label": edge["label"]} if "label" in edge else {})}
        for item in source.get("attention", []):
            attention.setdefault(item["id"], {}).update(item)
        for flow in source.get("flows", []):
            flows[flow["id"]] = dict(flow)
        for test in source.get("tests", []):
            tests.setdefault((test["path"], test["title"]), set()).update(test["ids"])
        for text in source.get("followups", []):
            followups.append({"text": text, **({"front": entry["front"], "run": entry["run"]} if entry["front"] else {})})

    def resolve_ref(ref, at):
        result = {"path": ref["path"]}
        text = tree.text(ref["path"])
        if text is None:
            gap("invalid_reference", at=at, path=ref["path"], problem="path does not exist at head")
        elif ref.get("symbol"):
            span = resolve_symbol(text, ref["path"], ref["symbol"])
            result["symbol"] = ref["symbol"]
            if span:
                result["start"], result["end"] = span
            else:
                gap("unresolved_anchor", at=at, path=ref["path"], symbol=ref["symbol"])
        if ref.get("note"):
            result["note"] = ref["note"]
        return result

    def resolve_test(ref, at):
        text = tree.text(ref["path"])
        if text is None or ref["title"] not in text:
            gap("invalid_reference", at=at, path=ref["path"], title=ref["title"], problem="test title not found at head")
            return None
        return {"path": ref["path"], "title": ref["title"], "line": text[:text.index(ref["title"])].count("\n") + 1}

    # Files and cards.
    card_list = list(cards.values())
    owners = {}
    for card in card_list:
        for path in card["files"]:
            owners.setdefault(path, []).append(card["id"])
            if path not in files:
                gap("invalid_reference", at=f"card {card['id']}", path=path, problem="file did not change in base...head")
    file_map = {}
    for path, fact in sorted(files.items()):
        file_map[path] = {**fact, "cards": owners.get(path, [])}
        if path in roles:
            file_map[path]["role"] = roles[path]
        if not owners.get(path) and code[path].get("omitted") != "excluded":
            gap("unassigned_file", path=path)
    for path in roles:
        if path not in files:
            gap("invalid_reference", at="files", path=path, problem="role for a file that did not change")

    # Notes resolved at head, attached to overlapping hunks.
    note_list = []
    for (path, symbol), note in notes.items():
        if path not in files:
            gap("invalid_reference", at=note["from"], path=path, problem="note on a file that did not change")
            continue
        span = resolve_symbol(tree.text(path), path, symbol)
        if not span:
            gap("unresolved_anchor", at=note["from"], path=path, symbol=symbol)
            continue
        note_list.append({"path": path, "symbol": symbol, "text": note["text"], "start": span[0], "end": span[1]})
    for index, note in enumerate(note_list):
        for hunk in code.get(note["path"], {}).get("hunks", []):
            if hunk["newLines"] and hunk["newStart"] <= note["end"] and note["start"] <= hunk["newStart"] + hunk["newLines"] - 1:
                hunk["notes"].append(index)

    # Edges: derived from imports, plus authored ones.
    card_ids = {c["id"] for c in card_list}
    edges = {}
    for card in card_list:
        for path in card["files"]:
            text = tree.text(path) if path in files and files[path]["status"] != "deleted" else None
            for candidates in imports(path, text or ""):
                target = next((c for c in candidates if c in owners), None)
                for other in owners.get(target, []):
                    if other != card["id"]:
                        edges.setdefault((card["id"], other), {"from": card["id"], "to": other, "kind": "import"})
    for key, edge in authored.items():
        if edge["from"] not in card_ids or edge["to"] not in card_ids:
            gap("invalid_reference", at="edges", edge=f"{edge['from']}->{edge['to']}", problem="edge names an unknown card")
        else:
            edges[key] = edge
    linked = {e["from"] for e in edges.values()} | {e["to"] for e in edges.values()}
    for card in card_list:
        if len(card_list) > 1 and card["id"] not in linked and any(not p.endswith(EXTRACTORS) for p in card["files"]):
            gap("isolated_card", "warning", card=card["id"])

    # Attention points and flows: plan order and metadata, then reports.
    declared = set(order)
    attention_list, flow_list = [], []
    for identifier in [i for i in order if i.startswith("ap-")] + sorted(i for i in attention if i not in declared):
        if identifier not in declared:
            gap("invalid_reference", at="attention", id=identifier, problem="id is not declared in the plan")
        meta, item = cells.get(identifier, {}), attention.get(identifier, {})
        # Display text is never derived from ids: a missing title shows the id and is a gap.
        result = {"id": identifier, "title": item.get("title") or identifier, "status": item.get("status", "unreported")}
        if not item.get("title"):
            gap("untitled", id=identifier)
        for key in ("category", "severity", "scenario", "handling", "proof", "owner"):
            value = item.get(key) or meta.get(key, "").strip("`")
            if key == "severity":
                value = value.lower() if value.lower() in ("critical", "high", "medium", "low") else ""
            if key == "proof":
                value = value.lower() if value.lower() in ("test", "qa", "review") else ""
            if value:
                result[key] = value[:2000]
        if item.get("residual"):
            result["residual"] = item["residual"]
        result["evidence"] = [resolve_ref(r, f"attention {identifier}") for r in item.get("evidence", [])]
        result["tests"] = [t for t in (resolve_test(r, f"attention {identifier}") for r in item.get("tests", [])) if t]
        result["qa"] = list(item.get("qa", []))
        paths = {r["path"] for r in result["evidence"]} | {t["path"] for t in result["tests"]}
        result["cards"] = list(item.get("cards") or sorted({c for p in paths for c in owners.get(p, [])}))
        if result["status"] == "unreported":
            gap("unreported_id", id=identifier)
        elif result["status"] in ("handled", "partial") and not result["evidence"] and not result["tests"]:
            gap("unevidenced_id", id=identifier)
        attention_list.append(result)
    for identifier in [i for i in order if i.startswith("fl-")] + sorted(i for i in flows if i not in declared):
        if identifier not in declared:
            gap("invalid_reference", at="flows", id=identifier, problem="id is not declared in the plan")
        meta, flow = cells.get(identifier, {}), flows.get(identifier, {})
        result = {"id": identifier, "title": flow.get("title") or identifier}
        if not flow.get("title"):
            gap("untitled", id=identifier)
        actor = flow.get("actor") or meta.get("actor", "")
        if actor:
            result["actor"] = actor[:80]
        for key in ("trigger", "outcome"):
            if meta.get(key):
                result[key] = meta[key][:2000]
        steps = []
        for number, step in enumerate(flow.get("steps", []), 1):
            at = f"flow {identifier} step {number}"
            resolved = {"actor": step["actor"], "do": step["do"], "expect": step["expect"],
                        "commands": list(step.get("commands", [])), "cards": list(step.get("cards", [])),
                        "code": [resolve_ref(r, at) for r in step.get("code", [])]}
            for key in ("title", "url"):
                if step.get(key):
                    resolved[key] = step[key]
            test = resolve_test(step["test"], at) if step.get("test") else None
            if test:
                resolved["test"] = test
            steps.append(resolved)
        result["steps"] = steps
        test = resolve_test(flow["test"], f"flow {identifier}") if flow.get("test") else None
        if test:
            result["test"] = test
        result["cards"] = list(dict.fromkeys(list(flow.get("cards", [])) + [c for s in steps for c in s["cards"]]))
        if not result["cards"]:
            # A flow nobody reported on yet still shows its path: the cards or groups named in the plan's Modules column.
            modules = {m.strip().strip("`") for m in meta.get("modules", "").split(",")}
            result["cards"] = [c["id"] for c in card_list if c["id"] in modules or c.get("group") in modules]
        if not steps:
            gap("unreported_id", id=identifier)
        flow_list.append(result)
    for item in attention_list + flow_list + [s for f in flow_list for s in f["steps"]]:
        for card in item["cards"]:
            if card not in card_ids:
                gap("invalid_reference", at=item.get("id", "flow step"), card=card, problem="unknown card")

    test_list = []
    for (path, title), ids in tests.items():
        resolved = resolve_test({"path": path, "title": title}, "tests")
        if resolved:
            test_list.append({**resolved, "ids": sorted(ids)})

    for card in card_list:
        card["attention"] = [a["id"] for a in attention_list if card["id"] in a["cards"]]
        card["flows"] = [f["id"] for f in flow_list if card["id"] in f["cards"]]

    # Layers and groups: declared in the supplement, otherwise derived from the cards.
    layers = list(supplement.get("layers", []))
    if not layers:
        layers = [{"id": i, "title": i} for i in dict.fromkeys(c["layer"] for c in card_list)]
        for layer in layers:
            gap("untitled", layer=layer["id"])
    for card in card_list:
        if card["layer"] not in {layer["id"] for layer in layers}:
            gap("invalid_reference", at=f"card {card['id']}", layer=card["layer"], problem="layer is not declared")
    groups = list(supplement.get("groups", []))
    for identifier in dict.fromkeys(c["group"] for c in card_list if c.get("group")):
        if identifier not in {g["id"] for g in groups}:
            groups.append({"id": identifier, "title": identifier})
            gap("untitled", group=identifier)
    if len(card_list) > GROUP_ABOVE:
        for card in card_list:
            if not card.get("group"):
                gap("ungrouped_card", card=card["id"])

    title = supplement.get("title") or plan_title
    if not title:
        gap("untitled", work=work_dir.name)
    view = {
        "format": "harness-map-v1",
        "title": title or work_dir.name,
        "work": work_dir.name,
        "source": {"repository": Path(probe(repo)[0]["root"]).name, "base": base, "head": head, "baseRef": base_ref,
                   "headRef": head_ref, "headDate": git(repo, "show", "-s", "--format=%cI", head).strip()},
        "layers": layers, "groups": groups, "cards": card_list,
        "edges": sorted(edges.values(), key=lambda e: (e["from"], e["to"])), "files": file_map,
        "notes": note_list, "commits": commits, "attention": attention_list, "flows": flow_list,
        "tests": test_list, "followups": followups, "runs": [e for r, e in loaded if r is not None], "code": code,
    }
    if supplement.get("subtitle"):
        view["subtitle"] = supplement["subtitle"]
    errors = schema_errors(view, "map.v1.json")
    if errors:
        fail("invalid_map", "The consolidated map does not match harness-map-v1.", **report(errors))
    return view, gaps, unaccepted


def publish(work_dir, view):
    folder = safe_path(work_dir / "map")
    target = folder / "map.json"
    content = (json.dumps(view, ensure_ascii=False, separators=(",", ":")) + "\n").encode()
    if target.is_file() and safe_path(target).read_bytes() == content:
        return target, False
    make_directory(folder)
    atomic_write(target, content)
    return target, True


# --- Viewer ----------------------------------------------------------------------------------

def view_command(folder, viewer):
    return f"HARNESS_MAP_DIR={folder} pnpm --dir {viewer or '<harness checkout>/apps/viewer'} dev"


def start_viewer(folder, viewer, wait=20.0):
    if not viewer:
        return {"started": False, "command": view_command(folder, None),
                "reason": "viewer location unknown; pass --viewer or set HARNESS_VIEWER"}
    viewer = Path(viewer).expanduser().resolve()
    if not (viewer / "package.json").is_file():
        fail("viewer_missing", "No viewer application at that path.", path=str(viewer))
    if not (viewer / "node_modules").is_dir():
        return {"started": False, "install": f"pnpm --dir {viewer} install --frozen-lockfile",
                "command": view_command(folder, viewer), "reason": "viewer dependencies are not installed"}
    if not shutil.which("pnpm"):
        return {"started": False, "command": view_command(folder, viewer), "reason": "pnpm is not available"}
    descriptor, name = tempfile.mkstemp(prefix="harness-viewer-", suffix=".log")
    os.close(descriptor)
    log = Path(name)
    with log.open("wb") as stream:
        process = subprocess.Popen(["pnpm", "dev"], cwd=viewer, stdin=subprocess.DEVNULL, stdout=stream,
                                   stderr=subprocess.STDOUT, start_new_session=True,
                                   env={**os.environ, "HARNESS_MAP_DIR": str(folder)})
    deadline, url = time.monotonic() + wait, None
    while time.monotonic() < deadline and process.poll() is None and not url:
        found = re.search(r"https?://(?:127\.0\.0\.1|localhost|\[::1\]):\d+/?", log.read_text(errors="replace"))
        url = found.group(0) if found else None
        time.sleep(0.2)
    if process.poll() is not None:
        return {"started": False, "log": str(log), "command": view_command(folder, viewer), "reason": "viewer exited"}
    return {"started": True, "pid": process.pid, "url": url, "log": str(log), "stop": f"kill {process.pid}"}


# --- Command line ----------------------------------------------------------------------------

def execute(args):
    folder = environment(args)
    work_dir = work_directory(folder, args["work"])
    if args["operation"] == "view":
        maps = safe_path(work_dir / "map")
        if not (maps / "map.json").is_file():
            fail("map_missing", "Build the map first.", folder=str(maps))
        return start_viewer(maps, args.get("viewer") or os.environ.get("HARNESS_VIEWER"))
    view, gaps, unaccepted = build(args["repo"], work_dir, args["base"], args["head"],
                                   EXCLUDE + (args.get("exclude") or []), args["max_lines"])
    target, changed = publish(work_dir, view)
    errors = [g for g in gaps if g["level"] == "error"]
    result = {"map": str(target), "changed": changed,
              "counts": {k: len(view[k]) for k in ("files", "cards", "edges", "notes", "attention", "flows", "tests")},
              "errors": len(errors), "warnings": len(gaps) - len(errors), "gaps": gaps[:40]}
    if len(gaps) > 40:
        result["more"] = len(gaps) - 40
    if unaccepted:
        result["unaccepted"] = unaccepted[:20]
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--home", help="Binding storage (HARNESS_HOME or ~/.harness)")
    commands = parser.add_subparsers(dest="operation", required=True)
    for name in ("build", "view"):
        command = commands.add_parser(name)
        group = command.add_mutually_exclusive_group(required=True)
        group.add_argument("--environment")
        group.add_argument("--project")
        command.add_argument("--work", required=True)
        if name == "build":
            command.add_argument("--repo", required=True, help="Checkout holding base and head")
            command.add_argument("--base", required=True)
            command.add_argument("--head", default="HEAD")
            command.add_argument("--exclude", nargs="*", help="Extra glob patterns whose code is omitted")
            command.add_argument("--max-lines", type=int, default=MAX_LINES)
        else:
            command.add_argument("--viewer", help="apps/viewer of a Harness checkout (or HARNESS_VIEWER)")
    args = vars(parser.parse_args(argv))
    try:
        result = execute(args)
    except Error as exc:
        print(json.dumps({"error": {"code": exc.code, "message": exc.message, "details": exc.details}}, ensure_ascii=False))
        return 1
    except OSError as exc:
        print(json.dumps({"error": {"code": "io_error", "message": "Inspect state before retrying.", "details": {"reason": str(exc)}}}))
        return 1
    print(json.dumps(result, ensure_ascii=False))
    return 1 if result.get("errors") else 0


if __name__ == "__main__":
    sys.exit(main())
