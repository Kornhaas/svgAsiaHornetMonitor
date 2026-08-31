# Quality and delivery policy

Every change is checked automatically on pushes and pull requests.

| Check | Purpose | Gate |
| --- | --- | --- |
| `uv lock --check` | The committed lockfile matches declared dependencies | Required |
| Ruff format + lint | Consistent formatting, import hygiene, and static Python defects | Required |
| Pytest + branch coverage | Regression protection and test visibility | Required; current minimum 40% |
| `uv audit` | Known vulnerable or adverse Python dependency versions | Required |
| CodeQL | Scheduled and pull-request static security analysis | GitHub Code Scanning alert review |
| Dependabot | Weekly dependency and GitHub Action update pull requests | Review promptly |

## Coverage plan

The first measured baseline is 42%. The 40% gate prevents regression while the project gains tests. Raise the threshold deliberately after each test-focused milestone:

1. 60% after camera lifecycle, event burst, updater success/failure, and startup configuration tests.
2. 80% after hardware adapters are isolated behind fakes and browser routes have complete behavior coverage.

Hardware access itself is verified on the Pi through the manual checklist in `docs/ai-collaboration.md`; unit tests use fakes and temporary directories rather than requiring a real webcam.

## GitHub repository settings

In GitHub, protect `main` after the first successful workflow runs: require the **Quality and tests** check before merging, require pull-request review when collaborators are added, and enable Dependabot alerts/security updates. Enable CodeQL default setup in **Settings → Advanced Security** if the repository plan exposes it; the repository also includes an explicit CodeQL workflow.
