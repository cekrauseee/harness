#!/usr/bin/env python3
"""Harness execution records: validated front events, immutable run records and symbol anchors."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
from harness import Error, encoded, fail, locked, make_directory, safe_path, select, storage_root, sync_directory  # noqa: E402

SCHEMAS = Path(__file__).resolve().parent.parent / "schema"
SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
PLAN_ID = re.compile(r"(?<![\w-])(?:ap|fl)-[a-z0-9]+(?:-[a-z0-9]+)*(?!\w)")
MAX_ERRORS = 40
_schemas = {}


# --- JSON Schema subset used by schema/*.json -------------------------------------------------

def load_schema(name):
    if name not in _schemas:
        _schemas[name] = json.loads((SCHEMAS / name).read_text())
    return _schemas[name]


def _type_ok(value, expected):
    return any({
        "object": isinstance(value, dict), "array": isinstance(value, list), "string": isinstance(value, str),
        "boolean": isinstance(value, bool), "null": value is None,
        "integer": isinstance(value, int) and not isinstance(value, bool),
        "number": isinstance(value, (int, float)) and not isinstance(value, bool),
    }[name] for name in ([expected] if isinstance(expected, str) else expected))


def _check(value, rule, root, at, errors):
    if "$ref" in rule:
        target = root
        for part in rule["$ref"].lstrip("#/").split("/"):
            target = target[part]
        _check(value, target, root, at, errors)
    if "const" in rule and value != rule["const"]:
        errors.append({"at": at, "error": f"must be {json.dumps(rule['const'])}"})
    if "enum" in rule and value not in rule["enum"]:
        errors.append({"at": at, "error": "must be one of " + ", ".join(map(json.dumps, rule["enum"]))})
    if "type" in rule and not _type_ok(value, rule["type"]):
        errors.append({"at": at, "error": f"must be of type {rule['type']}"})
        return
    if isinstance(value, str):
        if len(value) < rule.get("minLength", 0):
            errors.append({"at": at, "error": f"must have at least {rule['minLength']} characters"})
        if "maxLength" in rule and len(value) > rule["maxLength"]:
            errors.append({"at": at, "error": f"must have at most {rule['maxLength']} characters"})
        pattern = rule.get("pattern")
        # Python's $ also matches before a final newline; ECMA-262 patterns do not.
        if pattern and (not re.search(pattern, value) or (pattern.endswith("$") and value.endswith("\n"))):
            errors.append({"at": at, "error": f"must match {pattern}"})
    if isinstance(value, (int, float)) and not isinstance(value, bool) and value < rule.get("minimum", value):
        errors.append({"at": at, "error": f"must be at least {rule['minimum']}"})
    if isinstance(value, list):
        if len(value) < rule.get("minItems", 0):
            errors.append({"at": at, "error": f"must have at least {rule['minItems']} items"})
        if "items" in rule:
            for index, item in enumerate(value):
                _check(item, rule["items"], root, f"{at}[{index}]", errors)
    if isinstance(value, dict):
        for key in rule.get("required", ()):
            if key not in value:
                errors.append({"at": at, "error": f"missing {key}"})
        properties, extra = rule.get("properties", {}), rule.get("additionalProperties", True)
        for key, item in value.items():
            where = f"{at}.{key}" if re.fullmatch(r"\w+", key) else f"{at}[{json.dumps(key)}]"
            if key in properties:
                _check(item, properties[key], root, where, errors)
            elif extra is False:
                errors.append({"at": where, "error": "is not allowed"})
            elif isinstance(extra, dict):
                _check(item, extra, root, where, errors)


def schema_errors(value, name, definition=None):
    """Validate against a schema file, or one of its $defs; returns [{at, error}]."""
    root = load_schema(name)
    errors = []
    _check(value, root["$defs"][definition] if definition else root, root, "$", errors)
    return errors


def report(errors):
    return {"errors": errors[:MAX_ERRORS], **({"more": len(errors) - MAX_ERRORS} if len(errors) > MAX_ERRORS else {})}


# --- Git -------------------------------------------------------------------------------------

def git(repo, *arguments, check=True):
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env["LC_ALL"] = "C"
    try:
        result = subprocess.run(["git", "-C", str(repo), "-c", "core.quotepath=off", *arguments], env=env,
                                capture_output=True, timeout=120)
    except (OSError, subprocess.TimeoutExpired) as exc:
        fail("git_unavailable", "Git could not run.", reason=str(exc))
    if check and result.returncode:
        fail("git_error", "Git command failed.", command=" ".join(arguments[:3]),
             reason=result.stderr.decode(errors="replace").strip()[:500])
    return result.stdout.decode(errors="replace") if result.returncode == 0 else None


def commit(repo, revision):
    value = git(repo, "rev-parse", "--verify", "--quiet", f"{revision}^{{commit}}", check=False)
    if not value:
        fail("unknown_revision", "Revision is not a commit in this repository.", revision=revision)
    return value.strip()


def changed_paths(repo, base, head):
    """Paths changed in base...head, renames reported by their new path."""
    return [p for p in git(repo, "diff", "-M", "--name-only", "-z", f"{base}...{head}").split("\0") if p]


class Tree:
    """Cached file contents at one revision."""

    def __init__(self, repo, revision):
        self.repo, self.revision, self.cache = repo, revision, {}

    def text(self, path):
        if path not in self.cache:
            self.cache[path] = git(self.repo, "cat-file", "blob", f"{self.revision}:{path}", check=False)
        return self.cache[path]


# --- Symbol anchors --------------------------------------------------------------------------

# Declaration patterns per language (top-level, nested member), the single source for symbol anchors.
# A symbol resolves like a Git funcname range: from its declaration to the next statement at the same
# or lower indentation, closing brackets and `end` included.
MODIFIERS = r"(?:(?:public|private|protected|static|readonly|async|override|abstract|declare|get|set)\s+)*"
DECLARATIONS = [
    ((".py", ".pyi"), r"(?:async\s+def|def|class)\s+{name}\b", r"(?:async\s+def|def|class)\s+{name}\b"),
    ((".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".mts", ".cts"),
     r"(?:export\s+)?(?:default\s+)?(?:declare\s+)?(?:abstract\s+)?(?:async\s+)?"
     r"(?:function\s*\*?|class|interface|type|enum|const|let|var|namespace)\s*{name}\b",
     MODIFIERS + r"(?:(?:function\s*\*?|const|let|var)\s+)?\*?#?{name}\s*[(<=:?!]"),
    ((".go",), r"(?:func(?:\s*\([^)]*\))?|type|var|const)\s+{name}\b", r"(?:func|type|var|const)\s+{name}\b"),
    ((".rs",), r"(?:pub(?:\([^)]*\))?\s+)?(?:async\s+)?(?:unsafe\s+)?(?:fn|struct|enum|trait|mod|type|const|static|union)\s+{name}\b"
     r"|impl(?:<[^>]*>)?\s+(?:[\w:<>, ]+\s+for\s+)?{name}\b",
     r"(?:pub(?:\([^)]*\))?\s+)?(?:async\s+)?(?:unsafe\s+)?(?:fn|const|type)\s+{name}\b"),
    ((".rb",), r"(?:def\s+(?:self\.)?|class\s+|module\s+){name}(?![\w?!])", r"(?:def\s+(?:self\.)?|class\s+|module\s+){name}(?![\w?!])"),
    ((".sh", ".bash", ".zsh"), r"(?:function\s+{name}\b|{name}\s*\(\s*\))", r"(?:function\s+{name}\b|{name}\s*\(\s*\))"),
]
# Other languages (Java, Kotlin, C#, Swift, C, PHP, SQL...): a line declaring the name before ( { = : < ;
GENERIC = (r"(?:[\w$@<>\[\],.*&:\"]+\s+)*?{name}\b(?=\s*[({{=:<;]|\s*$)",) * 2
HEADING = re.compile(r"(#{1,6})\s+(.*?)\s*#*\s*$")


def _patterns(path):
    suffix = Path(path).suffix.lower()
    return next((d[1:] for d in DECLARATIONS if suffix in d[0]), GENERIC)


def _indent(line):
    return len(line) - len(line.lstrip(" \t"))


def _block_end(lines, start, limit):
    """Last line (exclusive index) of the block declared at lines[start]."""
    depth, end = _indent(lines[start]), limit
    for index in range(start + 1, limit):
        stripped, indent = lines[index].strip(), _indent(lines[index])
        # A closer at the declaration's own level belongs to it; one further out closes the parent.
        if stripped and (indent < depth or indent == depth and not re.match(r"[})\]]|end\b", stripped)):
            end = index
            break
    while end > start + 1 and not lines[end - 1].strip():
        end -= 1
    return end


def resolve_symbol(text, path, symbol):
    """Return (start, end) 1-based inclusive line range of symbol in text, or None."""
    if text is None or not symbol:
        return None
    lines = text.split("\n")
    if Path(path).suffix.lower() in {".md", ".markdown"}:
        for index, line in enumerate(lines):
            match = HEADING.fullmatch(line)
            if match and match.group(2) == symbol.strip():
                level, end = len(match.group(1)), len(lines)
                for later in range(index + 1, len(lines)):
                    other = HEADING.fullmatch(lines[later])
                    if other and len(other.group(1)) <= level:
                        end = later
                        break
                while end > index + 1 and not lines[end - 1].strip():
                    end -= 1
                return index + 1, end
        return None
    top, member = _patterns(path)

    def find(parts, low, high, parent):
        # Try every declaration of a name: Rust's `struct Foo` precedes the `impl Foo` holding its methods.
        pattern = re.compile((top if parent is None else r"[ \t]+" + member).format(name=re.escape(parts[0])))
        for index in range(low, high):
            if pattern.match(lines[index]) and (parent is None or _indent(lines[index]) > parent):
                end = _block_end(lines, index, high)
                found = (index + 1, end) if len(parts) == 1 else find(parts[1:], index + 1, end, _indent(lines[index]))
                if found:
                    return found
        return None

    return find(symbol.split("."), 0, len(lines), None)


# --- Environment paths -----------------------------------------------------------------------

def environment(args):
    home = safe_path(storage_root(args.get("home") or os.environ.get("HARNESS_HOME", "~/.harness")))
    folder, _, _ = select(home, {"project": args.get("project"), "environment": args.get("environment")})
    return folder


def work_directory(folder, work):
    if not isinstance(work, str) or not SLUG.fullmatch(work):
        fail("invalid_input", "Use a readable lowercase work name with hyphens.")
    path = safe_path(folder / "work" / work)
    if not path.is_dir():
        fail("work_missing", "The work item does not exist; records belong to existing work.", work=work)
    return path


def front_directory(folder, work, front):
    if not isinstance(front, str) or not SLUG.fullmatch(front):
        fail("invalid_input", "Use a readable lowercase front name with hyphens.")
    return safe_path(work_directory(folder, work) / "fronts" / front)


def plan_ids(work_dir):
    """Attention point and flow ids in the plan and module files, by token scan."""
    found = set()
    for path in [work_dir / "README.md", *sorted((work_dir / "modules").glob("*.md"))]:
        if path.is_file():
            found.update(PLAN_ID.findall(safe_path(path).read_text(errors="replace")))
    return found


# --- Events ----------------------------------------------------------------------------------

def timestamp():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def append_event(folder, work, front, data):
    if not isinstance(data, dict):
        fail("invalid_input", "Event data must be a JSON object.")
    directory = front_directory(folder, work, front)
    event = {"format": "harness-event-v1", "ts": timestamp(), "work": work, "front": front}
    for key in ("format", "work", "front"):
        if key in data and data[key] != event[key]:
            fail("invalid_event", f"Event {key} does not match its location.", expected=event[key])
    event.update(data)
    errors = schema_errors(event, "event.v1.json")
    if errors:
        fail("invalid_event", "Event does not match harness-event-v1.", **report(errors))
    line = (json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n").encode()
    path = directory / "events.jsonl"
    with locked(directory):
        safe_path(path)
        descriptor = os.open(path, os.O_RDWR | os.O_APPEND | os.O_CREAT, 0o644)
        try:
            size = os.fstat(descriptor).st_size
            # A torn earlier line must not absorb this one.
            if size and os.pread(descriptor, 1, size - 1) != b"\n":
                line = b"\n" + line
            written = 0
            while written < len(line):
                written += os.write(descriptor, line[written:])
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    return {"file": str(path), "event": event}


def read_events(front_dir):
    """Valid events of a front in file order, and the count of unreadable lines."""
    path = safe_path(front_dir / "events.jsonl")
    events, invalid = [], 0
    if not path.is_file():
        return events, invalid
    for line in path.read_text(errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except ValueError:
            invalid += 1
            continue
        if schema_errors(event, "event.v1.json"):
            invalid += 1
        else:
            events.append(event)
    return events, invalid


# --- Run records -----------------------------------------------------------------------------

def complete(record, repo, base=None, head=None):
    """Fill the record's Git facts: full base and head SHAs and, when omitted, changed paths.

    An explicit head replaces a draft's earlier head and its changed paths."""
    if not isinstance(record, dict):
        fail("invalid_record", "Record must be a JSON object.")
    record = dict(record)
    record.setdefault("format", "harness-record-v1")
    if base or "base" in record:
        record["base"] = commit(repo, base or record["base"])
    if head:
        record.pop("changed", None)
    record["head"] = commit(repo, head or record.get("head") or "HEAD")
    if "base" in record and "changed" not in record:
        record["changed"] = changed_paths(repo, record["base"], record["head"])
    return record


def record_errors(folder, record, repo):
    """Schema, Git and plan checks; returns [{at, error}]."""
    errors = schema_errors(record, "record.v1.json")
    if errors:
        return errors
    try:
        work_dir = work_directory(folder, record["work"])
    except Error as exc:
        return [{"at": "$.work", "error": exc.message}]
    changed = set(changed_paths(repo, record["base"], record["head"]))
    tree = Tree(repo, record["head"])
    if set(record["changed"]) != changed:
        errors.append({"at": "$.changed", "error": "differs from git diff base...head",
                       "missing": sorted(changed - set(record["changed"]))[:10],
                       "extra": sorted(set(record["changed"]) - changed)[:10]})

    def changed_path(at, path):
        if path not in changed:
            errors.append({"at": at, "error": f"{path} did not change in base...head"})

    def code(at, ref):
        if tree.text(ref["path"]) is None:
            errors.append({"at": at + ".path", "error": f"{ref['path']} does not exist at head"})
        elif "symbol" in ref and not resolve_symbol(tree.text(ref["path"]), ref["path"], ref["symbol"]):
            errors.append({"at": at + ".symbol", "error": f"{ref['symbol']} not found in {ref['path']} at head"})

    def test(at, ref):
        text = tree.text(ref["path"])
        if text is None:
            errors.append({"at": at + ".path", "error": f"{ref['path']} does not exist at head"})
        elif ref["title"] not in text:
            errors.append({"at": at + ".title", "error": f"title not found in {ref['path']} at head"})

    for index, card in enumerate(record["cards"]):
        for position, path in enumerate(card["files"]):
            changed_path(f"$.cards[{index}].files[{position}]", path)
    for path in record["files"]:
        changed_path(f"$.files[{json.dumps(path)}]", path)
    for index, note in enumerate(record["notes"]):
        changed_path(f"$.notes[{index}].path", note["path"])
        code(f"$.notes[{index}]", note)
    for index, item in enumerate(record["attention"]):
        for position, ref in enumerate(item.get("evidence", [])):
            code(f"$.attention[{index}].evidence[{position}]", ref)
        for position, ref in enumerate(item.get("tests", [])):
            test(f"$.attention[{index}].tests[{position}]", ref)
    for index, flow in enumerate(record["flows"]):
        if "test" in flow:
            test(f"$.flows[{index}].test", flow["test"])
        for step_index, step in enumerate(flow["steps"]):
            at = f"$.flows[{index}].steps[{step_index}]"
            for position, ref in enumerate(step.get("code", [])):
                code(f"{at}.code[{position}]", ref)
            if "test" in step:
                test(f"{at}.test", step["test"])
    for index, item in enumerate(record["tests"]):
        test(f"$.tests[{index}]", item)

    declared = plan_ids(work_dir)
    used = [("$.owned", i) for i in record["owned"]] + [("$.attention", a["id"]) for a in record["attention"]]
    used += [("$.flows", f["id"]) for f in record["flows"]] + [("$.tests", i) for t in record["tests"] for i in t["ids"]]
    for at, identifier in used:
        if identifier not in declared:
            errors.append({"at": at, "error": f"{identifier} is not declared in the plan; add it there first"})
    reported = {a["id"] for a in record["attention"]} | {f["id"] for f in record["flows"]}
    for identifier in record["owned"]:
        if identifier not in reported:
            errors.append({"at": "$.owned", "error": f"{identifier} is owned but has no attention or flow entry"})
    for key in ("cards", "attention", "flows"):
        seen = [item["id"] for item in record[key]]
        for identifier in sorted({i for i in seen if seen.count(i) > 1}):
            errors.append({"at": f"$.{key}", "error": f"duplicate id {identifier}"})
    return errors


def record_path(folder, record):
    for key in ("work", "front", "run"):
        if not isinstance(record.get(key), str) or not SLUG.fullmatch(record[key]):
            fail("invalid_record", f"Record {key} must be a readable lowercase name with hyphens.")
    directory = front_directory(folder, record["work"], record["front"])
    return directory, safe_path(directory / "runs" / f"{record['run']}.record.json")


def write_record(folder, record, repo):
    directory, path = record_path(folder, record)
    errors = record_errors(folder, record, repo)
    if errors:
        fail("invalid_record", "Record failed validation; fix the listed problems and retry.", **report(errors))
    content = encoded(record)
    with locked(directory):
        if path.exists():
            if safe_path(path).read_bytes() == content:
                return {"file": str(path), "changed": False}
            fail("record_exists", "Records are immutable; deliver a correction under a new run id.", file=str(path))
        make_directory(path.parent)
        descriptor, temporary = tempfile.mkstemp(prefix=".harness-", dir=path.parent)
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            try:
                os.link(temporary, path)  # creates only if absent, even against writers without the lock
            except FileExistsError:
                fail("record_exists", "Records are immutable; deliver a correction under a new run id.", file=str(path))
            sync_directory(path.parent)
        finally:
            os.unlink(temporary)
    return {"file": str(path), "changed": True}


# --- Command line ----------------------------------------------------------------------------

def read_input(source):
    try:
        raw = sys.stdin.read() if source == "-" else Path(source).read_text()
        return json.loads(raw)
    except (OSError, ValueError) as exc:
        fail("invalid_input", "Input must be a readable JSON file, or '-' for stdin.", reason=str(exc))


def dirty(repo):
    return bool(git(repo, "status", "--porcelain", "--untracked-files=no"))


def execute(args):
    operation = args["operation"]
    if operation == "symbol":
        text = Tree(args["repo"], commit(args["repo"], args["rev"])).text(args["path"])
        if text is None:
            fail("path_missing", "Path does not exist at that revision.", path=args["path"])
        found = resolve_symbol(text, args["path"], args["symbol"])
        if not found:
            fail("symbol_unresolved", "No declaration of that symbol was found.", path=args["path"], symbol=args["symbol"])
        return {"path": args["path"], "symbol": args["symbol"], "start": found[0], "end": found[1]}
    folder = environment(args)
    if operation == "event":
        try:
            data = json.loads(args["data"])
        except ValueError as exc:
            fail("invalid_input", "Event data must be a JSON object.", reason=str(exc))
        return append_event(folder, args["work"], args["front"], data)
    record = complete(read_input(args["input"]), args["repo"], args.get("base"), args.get("head"))
    warnings = ["the checkout has uncommitted changes outside head"] if dirty(args["repo"]) else []
    if args["action"] == "validate":
        errors = record_errors(folder, record, args["repo"])
        result = {"valid": not errors, "head": record["head"], "changed": len(record.get("changed", [])), **report(errors)}
    else:
        result = write_record(folder, record, args["repo"])
    return {**result, **({"warnings": warnings} if warnings else {})}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--home", help="Binding storage (HARNESS_HOME or ~/.harness)")
    commands = parser.add_subparsers(dest="operation", required=True)

    def selector(command):
        group = command.add_mutually_exclusive_group(required=True)
        group.add_argument("--environment")
        group.add_argument("--project")

    event = commands.add_parser("event", help="Append one validated event to a front")
    selector(event)
    event.add_argument("--work", required=True)
    event.add_argument("--front", required=True)
    event.add_argument("--data", required=True, help="JSON object; format, ts, work and front are filled")
    record = commands.add_parser("record", help="Validate or write a run record")
    record.add_argument("action", choices=("validate", "write"))
    selector(record)
    record.add_argument("--input", required=True, help="Record JSON file, or '-' for stdin")
    record.add_argument("--repo", required=True, help="Checkout holding base and head")
    record.add_argument("--base")
    record.add_argument("--head")
    symbol = commands.add_parser("symbol", help="Resolve a symbol to its line range")
    symbol.add_argument("--repo", required=True)
    symbol.add_argument("--rev", default="HEAD")
    symbol.add_argument("--path", required=True)
    symbol.add_argument("--symbol", required=True)
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
    return 1 if result.get("valid") is False else 0


if __name__ == "__main__":
    sys.exit(main())
