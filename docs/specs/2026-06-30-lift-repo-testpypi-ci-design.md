# Lift tbctl: TestPyPI publishing, CI fix, and .envrc

## Goal

Modernise the repository's release and developer-setup tooling:

1. Publish `tbctl` to **TestPyPI** from CI.
2. Fix the broken CI lint/format step (still references the pre-rename `tb/` path).
3. Add a `.envrc` (direnv) that sets up the uv environment and enables the
   pre-commit hooks.

## Decisions

- **Build backend**: keep `hatchling`. It already bundles both `tbctl` and the
  gitignored, generated `generated/tb_client` into the wheel. Switching to
  `uv_build` would require relocating the generated client (it lives outside any
  single module root) or renaming every `tb_client` import — churn for no
  benefit.
- **Publish trigger**: on `v*` git tag push only.
- **Publish auth**: Trusted Publishing (OIDC) — no stored secrets.
- **Target index**: TestPyPI only (no production PyPI).

## Components

### 1. Build backend — no change

`pyproject.toml` keeps `hatchling` and the existing
`[tool.hatch.build.targets.wheel] packages = ["tbctl", "generated/tb_client"]`.

### 2. CI fix — `.github/workflows/ci.yml`

- The real breakage: the `lint-and-test` job lints and format-checks `tb/`,
  which no longer exists after the `tb → tbctl` rename. Change both commands to
  target `tbctl/ tests/`.
- Extend the workflow trigger to also fire on version tags so a tag run can both
  test and publish:

  ```yaml
  on:
    push:
      branches: [main]
      tags: ['v*']
    pull_request:
  ```

### 3. TestPyPI publishing — build once, then publish

Follow the PyPA-standard split: build artifacts in the test job, publish them in
a separate gated job.

- **`lint-and-test`** job: after `uv run pytest` passes, run `uv build` and
  upload the resulting `dist/` directory as a workflow artifact. The job already
  installs Java + openapi-generator and runs `./generate.sh`, which the build
  needs (the generated client must be present on disk to be bundled).
- **`publish-testpypi`** job:
  - `needs: lint-and-test`
  - runs only on tag pushes: `if: startsWith(github.ref, 'refs/tags/v')`
  - `permissions: { id-token: write }`
  - downloads the `dist/` artifact
  - calls `pypa/gh-action-pypi-publish` with
    `repository-url: https://test.pypi.org/legacy/` (OIDC Trusted Publishing,
    no `password`).

The `secret-scan` job is unchanged.

### 4. `.envrc` (direnv)

```bash
# Set up the uv-managed venv and keep it in sync with uv.lock.
watch_file uv.lock pyproject.toml
uv sync
source .venv/bin/activate
# Enable git pre-commit hooks.
pre-commit install --install-hooks
```

`uv sync` installs the dev group, which provides `pre-commit` on PATH.
`pre-commit install --install-hooks` is idempotent and safe to run on every
direnv load.

## Manual setup required (one-time, by the maintainer)

- On TestPyPI, register a **pending publisher** for project `tbctl`: owner/repo,
  workflow filename `ci.yml`, environment (if used) matching the job.
- Install `direnv` locally and run `direnv allow` after the `.envrc` lands.
- Bump `version` in `pyproject.toml` before each tag — TestPyPI rejects
  re-uploads of an existing version.

## Out of scope

- `uv_build` migration.
- Dependency changes.
- Production PyPI publishing.
- Automated version bumping.
