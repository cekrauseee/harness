# Development

## Requirements

- Python 3.11 or later.
- Git.
- Node.js with `npx` for `skills.sh` discovery checks.
- GitHub CLI for publication.

Bundled runtime scripts use only the Python standard library.

## Validation

Run the full test suite:

```bash
python3 -m unittest discover -s tests -v
```

Validate skill metadata:

```bash
for skill in skills/*; do
  python3 /path/to/skill-creator/scripts/quick_validate.py "$skill"
done
```

Validate the Codex plugin manifest and skills discovery:

```bash
python3 /path/to/plugin-creator/scripts/validate_plugin.py .
npx skills add . --list
```

## Change rules

- Keep skills self-contained.
- Keep `SKILL.md` procedural and concise; move detailed standards to conditional references.
- Add tests for every deterministic script.
- Preserve atomic writes and fail-open adapters.
- Bump `DEFAULTS_VERSION` whenever managed charter, standards, aliases, or policies change.
- Do not add migration logic for the legacy Project Harness layout.
- Use Conventional Commits for all repository history.
