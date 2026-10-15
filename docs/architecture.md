# Architecture

This repository holds three parts of Harness: the plugin that agents install, the file contract that the plugin writes, and the applications that read those files. The project environment under `HARNESS_HOME` is the source of truth; no part keeps its own copy of it. Codex and Claude Code run the agents: Harness gives them context, workflows and records, and renders what they produce, without becoming an agent runtime.

## Layout

```text
.claude-plugin/  .codex-plugin/   plugin manifests; the repository root is the plugin root
skills/<skill>/                   installed skills: SKILL.md and agents/ authored; scripts/, references/ and schema/ generated
src/                              canonical Python of the scripts bundled in skills
schema/                           JSON Schemas of the record, event and map formats
docs/                             canonical documentation; the contracts are also generated into skills
apps/<app>/                       local applications over environment files, never installed; today the change map viewer
scripts/build_dist.py             generator of the copies inside skills
tests/                            Python tests and the installation check
```

| Part | Paths | Reaches users as |
| --- | --- | --- |
| Plugin | manifests, `skills/`, `src/` | Installed skills, each with only the scripts and references it uses |
| Contract | [file context](file-context.md) (environment layout), [execution records](records.md) and `schema/` (JSON formats) | References and schemas generated into the skills that use them |
| Applications | `apps/` | A checkout of this repository; never installed |

The [helper API](helper-api.md) documents the plugin's environment commands; [development](development.md) covers checks and contribution.

## Boundaries

- The repository root is the plugin root. Hosts and the skills CLI install from it, so the manifests and `skills/` stay at the top level.
- Inside a skill only `SKILL.md` and `agents/openai.yaml` are authored. `scripts/build_dist.py` generates `scripts/`, `references/` and `schema/` from `src/`, `docs/` and `schema/`, selecting what each `SKILL.md` names and what those files import or link. Generated documents keep their relative links, so the canonical documents stay directly in `docs/`.
- An installed skill needs nothing outside its folder: Python 3.9+ standard library, Git and its generated copies.
- The contract is the only interface between the plugin and the applications. Every JSON document names its format and version (`harness-record-v1`, `harness-event-v1`, `harness-map-v1`).
- Applications depend on the contract, never on plugin code, and the plugin never depends on an application. A skill may start an application from a checkout, as the map skill's `view` does, but its output stays valid without it.
- Applications only read environment files. Each lives in `apps/<app>/` with its own toolchain, README and checks; Python tests never need Node.

## Direction

Harness is growing into a visual platform over environment files. New view types and applications join `apps/`: first more views in the viewer, then a local process that serves every environment under `HARNESS_HOME`, and later a cloud application that works as a graphical layer for operating local environments through a connection to the machine. Local files stay the source of truth; actions taken in an application would become files that agents read, as front files carry continuation today. None of this is implemented yet.

The plugin and the platform are expected to become separate repositories. Keeping the boundaries above makes that split a move of `apps/`, with `schema/` as the contract both sides share, not an untangling. Storing environments in a remote service is a separate question, with its requirements in [remote storage](remote-storage.md).
