# Releasing

## Repository setup

Maintainers configure the repository for squash merges only. Require pull requests and the **CI** check on `main`, and do not bypass these rules for release PRs. Maintainers review changes before merging. For the initial single-maintainer setup, required approving review count is **0** because authors cannot approve their own PRs. This still requires a PR and passing CI, but does not require external approval. Increase the approval count when additional maintainers are available. Use the PR title as the squash commit subject. Enable Dependabot alerts and security updates in repository settings. Enable Actions permission to create pull requests. The default token permission can remain read-only: the release job explicitly requests only `contents`, `pull-requests`, `issues`, and `actions` write access. No personal access token, PyPI token, or paid service is required.

## Change and version policy

Use Conventional Commit titles, for example `feat: add profile previews`, `fix(hook): preserve existing hooks`, or `docs: explain setup`. CI passes title input through an environment variable, never interpolates it into shell code, and rejects multiline/control-character titles. Since merges are squash-only, individual development commits need not be conventional. An optional local history check is `python scripts/check_conventional.py --commits BASE..HEAD`.

The simple release-please manifest tracks the root package. `version.txt` is the packaging version source, initially `0.0.0`; the first public release is `0.1.0`. Release PRs update `version.txt`, `CHANGELOG.md`, and `.release-please-manifest.json` together. Features increment minor, fixes increment patch, and breaking changes increment minor before 1.0 and major after 1.0. Mark breaking subjects with `!` or use a `BREAKING CHANGE:` commit footer. Ordinary `docs`, `chore`, `ci`, and test-only changes do not create a release by themselves. Keep their titles conventional anyway. A deliberate promotion to 1.0 can use a reviewed commit with a `Release-As: 1.0.0` footer.

## Release flow

1. Merge an approved conventional PR into `main`.
2. The release workflow first runs unit tests, builds the wheel and sdist, installs the wheel in a temporary virtual environment, and smoke-tests both CLIs. Only after this succeeds does release-please create or update a release PR.
3. The workflow validates the generated PR's live title, repository, and base, then explicitly dispatches `ci.yml` at its head branch. This creates checks attached to that exact workflow head SHA. As of October 2026, token-created PR opened/synchronize/reopened events can create approval-required workflow runs. Explicit `workflow_dispatch` avoids depending on human workflow approval or a new PAT. Later branch updates require new checks, not stale checks from an older head.
4. Review the release PR, version, and changelog. Wait for the stable **CI** check to succeed on the current release head, then squash merge it. The workflow never automatically merges PRs.
5. On the merge push, validated release-please creates the tag and GitHub release. In the same workflow, a separate artifacts job checks out the exact reported release SHA, verifies the tag SHA and `version.txt`, reruns tests/build/install checks, verifies wheel and sdist metadata versions, and uploads both distributions plus `SHA256SUMS`. It does not depend on token-created tag/release events triggering another workflow. Nothing is published to PyPI.

CI runs Linux Python 3.11, 3.12, 3.13, and 3.14, plus macOS Python 3.14. The final **CI** job runs even when dependencies fail or are cancelled and accepts only explicit success from title validation, the full matrix, and the secret scan. There are no path filters. For ordinary manual CI dispatches, PR-title validation is intentionally inapplicable; release dispatches have their live PR titles validated by the release workflow before dispatch.

All third-party actions are pinned to full commit SHAs with version comments. Dependabot checks GitHub Actions and root Python build requirements weekly, grouping minor/patch updates and using `chore(deps)` subjects. Review action SHA changes and their upstream release before merging.

The required secret scan downloads the official Gitleaks **8.30.1** Linux x64 release archive, verifies its hard-coded SHA256 against the upstream release checksum, and scans full fetched Git history with redacted findings and default rules. No license token or paid action is used. There is no baseline or project allowlist. Dependabot does not update this binary pin: maintainers must update both `GITLEAKS_VERSION` and `GITLEAKS_SHA256` in `ci.yml` after verifying the official release and checksums. Download, checksum, or scan failure blocks **CI**.

## Local checks and recovery

```sh
python -m pip install -r requirements-dev.txt
python -m unittest discover -v
python -m build
TITLE='fix: example subject' python scripts/check_conventional.py
```

CLI smoke checks use a temporary `JCODE_HOME`, do not send Telegram messages, and install/uninstall only the temporary hook configuration. Dependency installation/build tooling needs package-index access, but the application smoke commands themselves need neither network nor credentials.

The workflows can be dispatched manually after they exist on the default branch. Dispatch the release workflow only on `main`; other refs are rejected by the validation job condition. If upload fails after the GitHub release has been created, rerun the failed artifacts job from the original run so its release outputs are retained. Starting a brand-new release workflow may have no new release outputs and therefore will not repair a previous upload. Upload is idempotent with `--clobber`. Compare downloaded assets against `SHA256SUMS`. These are integrity hashes, not signatures or provenance attestations.

Before first publication, audit the repository for sensitive data, confirm packaging includes `version.txt`, run the full matrix, and exercise one release PR in GitHub. Local validation cannot prove repository permissions, protected-branch settings, hosted-runner availability, approval policies, or real dispatch/release behavior. A GitHub release can briefly exist without assets while the artifacts job runs, or remain incomplete if that job fails. Never announce a release before its assets job succeeds.
