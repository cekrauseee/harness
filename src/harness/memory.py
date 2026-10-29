"""Capture and consolidated knowledge share record operations, not judgment."""

from __future__ import annotations

import datetime
import uuid

from .context import environment_id, search_records, write_record
from .files import identifier


def scope(home, environment=None, global_scope=False, actor=None):
    if global_scope:
        return "memory"
    env = environment_id(home, environment, actor)
    return f"environments/{env}/memory"


def capture(home, title, body, source, environment=None, global_scope=False, actor=None):
    home.ensure()
    prefix = scope(home, environment, global_scope, actor)
    key = (
        datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d")
        + "-"
        + uuid.uuid4().hex[:10]
    )
    text = f"# {title}\n\n{body}\n"
    if source:
        text += f"\n## Source\n\n{source}\n"
    return write_record(home, f"{prefix}/captures/{key}.md", text, actor=actor)


def put(home, name, content, expected=None, environment=None, global_scope=False, actor=None):
    home.ensure()
    identifier(name)
    prefix = scope(home, environment, global_scope, actor)
    return write_record(home, f"{prefix}/knowledge/{name}.md", content, expected, actor)


def search(
    home,
    query,
    environment=None,
    global_scope=False,
    captures=False,
    actor=None,
    limit=20,
    offset=0,
):
    prefix = scope(home, environment, global_scope, actor)
    return search_records(
        home, f"{prefix}/{'captures' if captures else 'knowledge'}", query, actor, limit, offset
    )
