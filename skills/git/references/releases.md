# Versioning and releases

## Project convention

Identify what is released: an application, package, service, or coordinated set of components. Preserve an established industry convention that fits its consumers and ecosystem. For a new convention, prefer [Semantic Versioning](https://semver.org/) when versions communicate compatibility; use a documented alternative such as [calendar versioning](https://calver.org/) when that better fits the product. Keep package versions, build identifiers, and deployment identifiers distinct and traceable.

Use `document` to maintain concise project guidance covering the release unit, version policy, publication destinations, required checks, and any required installation or activation. Reuse existing tooling and documentation locations. Choose the execution sequence for the task; these requirements do not prescribe a pipeline.

## Version choice

Judge changes against the public contract consumers rely on, including APIs, command behavior, configuration, and persisted formats. Under stable SemVer, incompatible changes require a major increment, compatible functionality or deprecation a minor increment, and compatible fixes a patch increment. Commit labels inform this assessment; verify the actual compatibility impact.

For pre-1.0 software, document how the project increments versions and communicates instability. Make migration needs explicit even while the public contract is unstable. Identify prereleases and their intended channel clearly. Preserve published version contents; corrections to released code or artifacts need a new version.

Update the release unit's version source and dependent manifests or generated metadata through the established tooling. Verify they agree before publication. Preserve independent component versions where the project uses them.

## Source and release identity

For each Git release, bind a version tag to the exact validated release commit. Verify the remote tag target. Create annotated tags for new releases, following established naming and signing requirements; preserve existing published tags. Git's [tag documentation](https://git-scm.com/docs/git-tag) distinguishes release annotations from temporary labels.

Publish an accessible release record with notes and links to its source and artifacts or deployment. Use the host's native release surface when available; otherwise use the project's versioned release history or distribution metadata with equivalent traceability. For example, [GitHub Releases](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases) provide a release entry associated with a tag. Check both the source marker and the release record rather than inferring one from the other.

Keep the validated source associated with the published artifact or deployment, using the project's immutable identifiers. Confirm that publishing the release does not select an unintended commit or rebuild from a different source revision.

## Publication and completion

Honor existing authorization for integration, publication, deployment, and installation. Prepare the reviewable release and checks before any remaining approval boundary. Use native publication mechanisms and existing automation where they satisfy the project contract.

Verify the published version, remote source marker, release notes, required artifacts, and distribution references. Complete any deployment or local activation included in the authorized outcome and check the version actually available to its consumer. Distinguish publication from deployment and installation; report any pending destination or action with its reason and next step.

When resuming publication, inspect what already exists and complete missing steps without republishing different contents under an existing version. Reconstruct missing release notes from the released source and available evidence; preserve original tags and be accurate about dates and what was verified. Use `clean` for integrated temporary delivery resources while retaining release history and artifacts still in use.
