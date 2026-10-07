# CI and auto-merge

Workflow: [`.github/workflows/ci.yml`](../.github/workflows/ci.yml).

| Trigger | Jobs |
|---|---|
| PR to `main` | `test` (Python 3.11 / 3.12 / 3.13: `uv sync --locked`, ruff, pytest) → `auto-merge` |
| Push to `main` | `test` |

`auto-merge` squash-merges the PR and deletes its branch once every `test` job is green.
It only runs for non-draft PRs opened from a branch of this repository: fork PRs are never
merged automatically. Open a PR as **draft** to keep it from merging.

Safety choices:

- Default token is read-only; only `auto-merge` gets `contents`/`pull-requests: write`.
- `--match-head-commit` makes the merge fail if a newer commit was pushed after the tested one.
- Actions are pinned to commit SHAs (version in a trailing comment).
- No PR-controlled text (title, body, branch name) reaches a shell command.

Note: merges made with `GITHUB_TOKEN` do not trigger new workflow runs, so there is no extra
`push` run on `main` after an auto-merge. That's fine: the merged code is exactly what was
tested on the PR head (`--match-head-commit`). The PR branch must be up to date with `main`
for that to hold; enable "Require branches to be up to date" in branch protection to enforce it.
