# Releasing

Harness ships as one plugin with one version. Hosts cache an installed plugin by its version, and the marketplace installs the commit that a release tag names, so a version number always identifies the same content. Merging into `main` is not a release.

## What carries a version

- The plugin: skills, bundled scripts and manifests share one semantic version, `MAJOR.MINOR.PATCH`, written in `.claude-plugin/plugin.json`, `.codex-plugin/plugin.json` and `VERSION` in `scripts/harness.py`. `tests/test_distribution.py` checks that the three agree.
- Formats and the instruction block have their own versions: `harness-project-v1` for the environment descriptor, `harness-record-v1`, `harness-event-v1` and `harness-map-v1` for [execution records](records.md), and the `harness-block` markers in [host integration](host-integration.md). Helpers accept only the current format, so a format change that rejects existing data is also a major plugin release.
- Applications under `apps/` are not released yet and carry no version.

## Choosing the number

| Release | The change |
| --- | --- |
| Major | Requires users or their environments to act: a skill renamed or removed, a new format version, a helper command or option removed or changed incompatibly, or an instruction block users must update in their global file |
| Minor | Adds without breaking: a skill, a helper command or option, an optional file in the contract, or a new responsibility for an existing skill |
| Patch | Fixes or clarifies without changing what any skill is responsible for |
| None | Touches only repository documentation, tests, tooling or applications |

## Cutting a release

Feature work never changes the version. A release happens on request, from an up-to-date `main`:

1. Land `chore(release): vX.Y.Z` on `main`. It changes only the version in the three places and the copies that `python3 -B tools/build_dist.py` regenerates, and passes the [development checks](development.md).
2. Tag the resulting commit with an annotated tag and push it:

   ```bash
   git tag -a vX.Y.Z -m "Harness X.Y.Z: <one-line summary>" <commit>
   git push origin vX.Y.Z
   ```

3. Publish a GitHub Release for the tag with notes generated from the pull request titles since the previous tag (`gh release create vX.Y.Z --generate-notes --notes-start-tag <previous tag>`), edited so that a reader learns what changed and, for a major release, what users must do.
4. Point the `cekrause` marketplace at the new tag (`ref` in `.claude-plugin/marketplace.json` and `.agents/plugins/marketplace.json`) and update installations with each host's plugin commands, as [installation](install.md) describes.

A published tag never moves and is never deleted. A mistake in a release is fixed by the next patch release.
