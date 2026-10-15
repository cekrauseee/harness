# Installation

Harness installs as a native plugin from the [cekrause marketplace](https://github.com/cekrauseee/cekrause-marketplace), through each host's own plugin commands. The marketplace pins the plugin to a release tag, so every installation of a version has the same content; [releasing](releasing.md) describes how versions and tags are made. A new host session is the reliable boundary for discovering a changed inventory.

## Install

Claude Code:

```bash
claude plugin marketplace add https://github.com/cekrauseee/cekrause-marketplace.git
claude plugin install harness@cekrause
```

Codex:

```bash
codex plugin marketplace add https://github.com/cekrauseee/cekrause-marketplace.git
codex plugin add harness@cekrause
```

`claude plugin list` and `codex plugin list` show the installed version. Each skill carries its own helper and references and needs neither its siblings nor this repository after installation. Viewing a change map is the exception: the [viewer](../apps/viewer/README.md) runs from a checkout of this repository and needs Node and pnpm.

## Update

Hosts cache an installed plugin by its version, and a release moves the marketplace to the new tag. Refresh the marketplace, update the plugin, then start a new chat:

- Claude Code: `claude plugin marketplace update cekrause`, then `claude plugin update harness@cekrause`.
- Codex: `codex plugin marketplace upgrade cekrause`, then `codex plugin add harness@cekrause`.

A marketplace registered from a local directory is read from that directory, so pull its checkout first; `codex plugin marketplace upgrade` refreshes only Git marketplaces. Confirm that the registered marketplace points to the source you expect, and never edit a host's plugin cache by hand.

## Other marketplaces

The plugin manifests are `.claude-plugin/plugin.json` and `.codex-plugin/plugin.json` at the repository root. A marketplace that lists Harness points at its HTTPS Git URL with a `url` source and a release tag as `ref`, rather than a `github` shorthand or a branch: Claude Code clones `github` sources over SSH, which fails on a machine without a GitHub SSH setup, while HTTPS works for this public repository on both hosts, and a tag gives every installation of a version the same content.

## Existing installations and data

Replacing older skills or plugins is a deliberate operation. Copies of the skills installed separately, for example with a skills CLI, duplicate the plugin's entries in discovery; remove them when switching to the plugin. Identify the installed discovery entries and their backing paths, preserve unrelated configuration and keep any helper paths still used by active chats available until those consumers finish. Removing an old skill from discovery and deleting its files need not happen at the same time.

Back up needed knowledge and continuations outside target repositories before converting old data. The new helper uses `HARNESS_HOME` (default `~/.harness`), a current-only descriptor and one environment per project. It does not modify or import Continuity data. A previous environment shared by several projects needs explicit allocation of knowledge and pending work; never infer that all its material belongs to whichever project is initialized first.

Bind the intended project with the `environment` skill and verify resolution from its relevant worktrees. Version 2 renamed every skill: remove the earlier `environment-*` and `workflows-*` entries from discovery when replacing them, and note that `close-work` is user-invoked. Transfer only the material needed for continued work, preserving active consumers and canonical sources. Leave unrelated environments untouched. Removing a legacy repository, changing a remote name, uninstalling a package and editing global instructions are separate actions with their corresponding authorization.

## Host behavior

Installing Harness does not rewrite AGENTS.md, CLAUDE.md or host settings. The recommended layout is one shared instruction file owned by the user, read by Codex through a symlink at `~/.codex/AGENTS.md` and imported by a thin `~/.claude/CLAUDE.md`; it carries the user's principles and practical choices, the versioned Harness block and one short section per host. [Host integration](host-integration.md) holds the block, the host sections and the settings checklist; apply or update them only on request, preserving unrelated rules. Do not introduce hooks, broad context injection or a required sequence of skills.

Discovery metadata enables automatic selection; the global instruction requires selection by responsibility without making the user name skills. Neither installation nor that instruction guarantees every model invocation. Verify the installed inventory separately from observed selection and application. A successful CLI install alone does not establish behavioral reliability.
