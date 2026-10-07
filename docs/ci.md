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
tested on the PR head (`--match-head-commit`), and branch protection requires the PR branch
to be up to date with `main`.

## Branch protection on `main`

- PR required (0 approvals, so the auto-merge can proceed); no direct pushes, also for admins.
- Required checks: `test (py3.11)`, `test (py3.12)`, `test (py3.13)`; branch must be up to date.
- Linear history (squash merges only); no force pushes or deletion.

If a PR is behind `main`, the merge is refused: rebase it (or press "Update branch") and CI
re-runs. Renaming the `test` job or the Python matrix requires updating the required checks.

## Deploy and smoke check

Vercel's GitHub app deploys every PR as a preview and every merge to `main` to production.
[`.github/workflows/smoke.yml`](../.github/workflows/smoke.yml) runs on Vercel's
`deployment_status` event for **Production** only and checks `/api/health`, `/api/rank?top=3`,
and that `/` serves the page with a `Content-Security-Policy` header.

Previews are not curled: Vercel Deployment Protection puts preview and per-deployment URLs
behind a Vercel login (401), and we keep no bypass secret in GitHub. Open the preview link on
the PR while logged in to Vercel to check it.

The production URL defaults to `https://ine-name-score-for-dev-parents.vercel.app`; override it
with the repository variable `PRODUCTION_URL` if you add a custom domain.
