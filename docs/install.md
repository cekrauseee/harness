# Installation

Choose one discovery route per host. Installing both the native plugin and standalone copies of its skills can expose duplicate entries. A new host session is the reliable boundary for discovering a changed inventory.

## Standalone skills

```bash
pnpx skills add cekrauseee/harness --skill '*' -g -a codex claude-code -y
```

Select only the desired host or skills when appropriate. Use `.` to install the current local checkout, including unpublished changes, rather than fetching the remote release. For Codex only:

```bash
pnpx skills add . --skill '*' -g -a codex -y
```

The CLI requires Node.js on `PATH`. `npx skills` is an alternative to `pnpx skills`. Each skill contains its own needed helper and references; it does not require its siblings or access to this repository after installation. This route installs the standalone skills; it does not register a native plugin or an MCP server.

## Native plugins

The repository includes `.codex-plugin/plugin.json` and `.claude-plugin/plugin.json`. Register the source using the host's supported plugin installation mechanism. In a marketplace manifest, point the plugin at its HTTPS Git URL with a `url` source rather than a `github` shorthand: Claude Code clones `github` sources over SSH, which fails on a machine without a GitHub SSH setup, while HTTPS works for this public repository on both hosts. The published [cekrause marketplace](https://github.com/cekrauseee/cekrause-marketplace) does this for Codex and Claude Code. For a Codex local marketplace, use the Plugin Creator flow to register the source and obtain the actual marketplace name, then install `harness@<marketplace-name>` with `codex plugin add`. The implicit personal marketplace and an explicitly registered marketplace have different setup requirements; do not add a fictitious marketplace or edit the host's cache manually.

For local plugin updates, preserve the semantic version prefix, apply the supported cachebuster helper, reinstall from the verified local marketplace and start a new chat to pick up the changes. Confirm that the selected marketplace actually points to the source being updated. A standalone skills installation is an alternative, not a prerequisite.

## Existing installations and data

Replacing older skills or plugins is a deliberate operation. Identify the installed discovery entries and their backing paths, preserve unrelated configuration and keep any helper paths still used by active chats available until those consumers finish. Removing an old skill from discovery and deleting its files need not happen at the same time.

Back up needed knowledge and continuations outside target repositories before converting old data. The new helper uses `HARNESS_HOME` (default `~/.harness`), a current-only descriptor and one environment per project. It does not modify or import Continuity data. A previous environment shared by several projects needs explicit allocation of knowledge and pending work; never infer that all its material belongs to whichever project is initialized first.

Bind the intended project with the `environment` skill and verify resolution from its relevant worktrees. Version 2 renamed every skill: remove the earlier `environment-*` and `workflows-*` entries from discovery when replacing them, and note that `close-work` is user-invoked. Transfer only the material needed for continued work, preserving active consumers and canonical sources. Leave unrelated environments untouched. Removing a legacy repository, changing a remote name, uninstalling a package and editing global instructions are separate actions with their corresponding authorization.

## Host behavior

Installing Harness does not rewrite AGENTS.md, CLAUDE.md or host settings. The recommended layout is one shared instruction file owned by the user, read by Codex through a symlink at `~/.codex/AGENTS.md` and imported by a thin `~/.claude/CLAUDE.md`; it carries the user's principles and practical choices, the versioned Harness block and one short section per host. [Host integration](../skills/environment/references/host-integration.md) holds the block, the host sections and the settings checklist; apply or update them only on request, preserving unrelated rules. Do not introduce hooks, broad context injection or a required sequence of skills.

Discovery metadata enables automatic selection; the global instruction requires selection by responsibility without making the user name skills. Neither installation nor that instruction guarantees every model invocation. Verify the installed inventory separately from observed selection and application. A successful CLI install alone does not establish behavioral reliability.
